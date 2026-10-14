from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import event, inspect
from sqlalchemy.exc import IntegrityError, StatementError

from bolsa.app.services.portfolio_service import PortfolioService
from bolsa.config import AppConfig
from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.values import LedgerConflictError, MoneyComponent, PortfolioError
from bolsa.infrastructure.database import create_database_engine, ensure_database_schema
from bolsa.infrastructure.database.decimal_type import ExactDecimalText
from bolsa.infrastructure.database.schema_migrations import _run_alembic, _run_upgrade, get_database_revision
import bolsa.infrastructure.database.schema_migrations as schema_migrations
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository

D = Decimal


def buy(q="10", day=0, **kwargs):
    return Trade(Instrument("TEST"), TradeType.BUY, D(q), MoneyComponent(D("100.12345678"), "EUR"),
                 MoneyComponent(D("0.10000001"), "EUR"),
                 datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day), **kwargs)


@pytest.fixture
def store(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    try:
        repository = SqlAlchemyPortfolioRepository(engine)
        yield config, engine, repository, PortfolioService(repository)
    finally:
        engine.dispose()


def test_exact_round_trip_reopen_and_full_audit(store):
    config, engine, repository, service = store
    p = service.create("Synthetic", "EUR")
    p = service.record(p.portfolio_uid, buy(), expected_revision=0)
    first = p.versions[0]
    p = service.record(p.portfolio_uid, replace(buy("2", day=1), kind=TradeType.SELL), expected_revision=1)
    p = service.revise(p.portfolio_uid, first.transaction_uid, first.transaction_version_uid,
                       buy("11"), reason="Synthetic correction", expected_revision=2)
    assert repository.load(p.portfolio_uid).reconstruct() == p.reconstruct()
    assert set(repository.load(p.portfolio_uid).versions) == set(p.versions)
    engine.dispose()
    reopened = create_database_engine(config.database_url)
    try:
        loaded = SqlAlchemyPortfolioRepository(reopened).load(p.portfolio_uid)
        assert loaded.reconstruct() == p.reconstruct()
        assert loaded.ledger_revision == 3
    finally:
        reopened.dispose()
    with engine.connect() as connection:
        rows = connection.exec_driver_sql("SELECT price, typeof(price), quantity, typeof(quantity) "
                                          "FROM ledger_versions WHERE trade_kind = 'BUY'").all()
        assert rows == [("100.12345678", "text", "10", "text"), ("100.12345678", "text", "11", "text")]


def test_date_only_fx_source_facts_and_cancellation_survive(store):
    _, _, repository, service = store
    p = service.create("Synthetic", "EUR")
    t = replace(buy(), executed_at=date(2026, 1, 1),
                unit_price=MoneyComponent(D("10.12"), "USD", D("0.861234567891")),
                source="synthetic", account_ref="test", external_id="one",
                original_facts=(("original_amount", "101.200000"),))
    p = service.record(p.portfolio_uid, t, expected_revision=0)
    assert repository.load(p.portfolio_uid).versions[0].trade == t
    assert repository.load(p.portfolio_uid).reconstruct().warnings
    head = p.versions[0]
    p = service.revise(p.portfolio_uid, head.transaction_uid, head.transaction_version_uid,
                       None, reason="Synthetic cancellation", expected_revision=1)
    loaded = repository.load(p.portfolio_uid)
    assert loaded.reconstruct().positions == ()
    assert len(loaded.versions) == 2
    assert loaded.versions[0].trade == t


def test_invalid_retroactive_update_never_writes(store):
    _, _, repository, service = store
    p = service.create("Synthetic", "EUR")
    p = service.record(p.portfolio_uid, buy(), expected_revision=0)
    head = p.versions[0]
    p = service.record(p.portfolio_uid, replace(buy("8", day=1), kind=TradeType.SELL), expected_revision=1)
    for replacement in (buy("5"), None):
        with pytest.raises(PortfolioError, match="Oversell"):
            service.revise(p.portfolio_uid, head.transaction_uid, head.transaction_version_uid,
                           replacement, reason="Invalid", expected_revision=2)
    assert repository.load(p.portfolio_uid).reconstruct() == p.reconstruct()
    assert repository.load(p.portfolio_uid).ledger_revision == 2


def test_injected_mid_write_failure_rolls_back_instrument_events_and_revision(store):
    _, engine, repository, service = store
    original = service.create("Synthetic", "EUR")
    candidate = original.record(buy()).record(replace(buy(day=1), instrument=Instrument("SECOND")))
    inserted = 0

    def fail_second(connection, cursor, statement, parameters, context, executemany):
        nonlocal inserted
        if statement.startswith("INSERT INTO ledger_versions"):
            inserted += 1
            if inserted == 2:
                raise RuntimeError("Injected ledger failure")

    event.listen(engine, "before_cursor_execute", fail_second)
    try:
        with pytest.raises(RuntimeError, match="Injected"):
            repository.save(candidate, expected_revision=0)
    finally:
        event.remove(engine, "before_cursor_execute", fail_second)
    assert repository.load(original.portfolio_uid) == original
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM instruments").scalar() == 0
        assert connection.exec_driver_sql("SELECT count(*) FROM ledger_versions").scalar() == 0
    repository.save(candidate, expected_revision=0)
    assert repository.load(original.portfolio_uid).ledger_revision == 2


def test_concurrent_writers_only_one_observed_revision_commits(store):
    _, _, repository, service = store
    original = service.create("Synthetic", "EUR")
    candidate_a, candidate_b = original.record(buy()), original.record(buy("2"))
    barrier = Barrier(2)

    def save(candidate):
        barrier.wait(timeout=5)
        try:
            repository.save(candidate, expected_revision=0)
            return "committed"
        except LedgerConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, (candidate_a, candidate_b)))
    assert sorted(results) == ["committed", "conflict"]
    loaded = repository.load(original.portfolio_uid)
    assert loaded.ledger_revision == 1
    assert loaded.reconstruct().position("TEST").quantity in (D(2), D(10))


def test_database_immutability_and_instrument_restrict(store):
    _, engine, repository, service = store
    p = service.create("Synthetic", "EUR")
    p = service.record(p.portfolio_uid, buy(), expected_revision=0)
    for sql in (
        "UPDATE portfolios SET base_currency = 'USD'",
        "UPDATE portfolios SET portfolio_uid = 'another'",
        "UPDATE ledger_versions SET price = '0'",
        "DELETE FROM ledger_versions",
        "DELETE FROM instruments",
        "DELETE FROM portfolios",
    ):
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.exec_driver_sql(sql)
    with pytest.raises(PortfolioError, match="currency"):
        repository.save(replace(p, base_currency="USD", versions=()), expected_revision=1)
    with pytest.raises(PortfolioError, match="removed or rewritten"):
        repository.save(replace(p, versions=()), expected_revision=1)
    assert repository.load(p.portfolio_uid).reconstruct() == p.reconstruct()


def test_database_chain_constraints_and_decimal_adapter(store):
    _, engine, repository, service = store
    p = service.create("Synthetic", "EUR")
    p = service.record(p.portfolio_uid, buy(), expected_revision=0)
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.exec_driver_sql("INSERT INTO ledger_versions SELECT * FROM ledger_versions")
    invalid = p.record(buy(day=1))
    # Verify the actual SQLAlchemy binding rejects financial float inputs.
    with pytest.raises(StatementError):
        with engine.begin() as connection:
            connection.execute(repository._versions.insert().values(
                portfolio_uid=str(p.portfolio_uid), transaction_version_uid=str(uuid4()),
                transaction_uid=str(uuid4()), version_number=1, recorded_at="synthetic",
                reason="", author="local", quantity=1.2,
            ))
    assert repository.load(p.portfolio_uid).ledger_revision == 1
    repository.save(invalid, expected_revision=1)
    adapter = ExactDecimalText()
    for malformed in (1.2, "NaN", "1.00", "bad"):
        with pytest.raises(PortfolioError):
            adapter.process_result_value(malformed, engine.dialect)


def test_synthetic_v02_upgrade_has_validated_backup_and_preserves_watchlist(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    _run_upgrade(config.database_path, "0002_market_to_exchange")
    engine = create_database_engine(config.database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("INSERT INTO instruments (ticker, asset_type) VALUES ('TEST', 'stock')")
            connection.exec_driver_sql("INSERT INTO watchlists (name) VALUES ('Synthetic')")
            connection.exec_driver_sql("INSERT INTO watchlist_items (watchlist_id, instrument_id, state, notes) "
                                      "VALUES (1, 1, 'idea', '')")
        result = ensure_database_schema(config)
        assert result.backup_path.is_file()
        assert get_database_revision(result.backup_path) == "0002_market_to_exchange"
        assert result.current_revision == "0006_portfolio_policies"
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA quick_check").scalar() == "ok"
            assert connection.exec_driver_sql("SELECT ticker FROM instruments").scalar() == "TEST"
            assert connection.exec_driver_sql("SELECT state FROM watchlist_items").scalar() == "idea"
        columns = {c["name"]: str(c["type"]) for c in inspect(engine).get_columns("ledger_versions")}
        assert columns["quantity"] == columns["price"] == columns["price_fx"] == "TEXT"
        repository = SqlAlchemyPortfolioRepository(engine)
        p = Portfolio("Synthetic", "EUR")
        repository.create(p)
        repository.save(p.record(buy()), expected_revision=0)
    finally:
        engine.dispose()


def test_stale_service_request_and_unknown_portfolio(store):
    _, _, repository, service = store
    p = service.create("Synthetic", "EUR")
    service.record(p.portfolio_uid, buy(), expected_revision=0)
    with pytest.raises(LedgerConflictError):
        service.record(p.portfolio_uid, buy(), expected_revision=0)
    with pytest.raises(PortfolioError):
        repository.load(uuid4())


def test_independent_currencies_survive_reopen(store):
    config, _, _, service = store
    eur = service.create("Same name", "EUR")
    usd = service.create("Same name", "USD")
    engine = create_database_engine(config.database_url)
    try:
        repository = SqlAlchemyPortfolioRepository(engine)
        assert repository.load(eur.portfolio_uid).base_currency == "EUR"
        assert repository.load(usd.portfolio_uid).base_currency == "USD"
    finally:
        engine.dispose()


def test_downgrade_refused_without_losing_financial_history(store):
    config, _, repository, service = store
    p = service.create("Synthetic", "EUR")
    p = service.record(p.portfolio_uid, buy(), expected_revision=0)
    with pytest.raises(RuntimeError, match="backup restore"):
        _run_alembic(config.database_path, command.downgrade, "0002_market_to_exchange")
    assert get_database_revision(config.database_path) == "0006_portfolio_policies"
    assert repository.load(p.portfolio_uid).reconstruct() == p.reconstruct()


def test_upgrade_does_not_start_when_backup_fails(tmp_path, monkeypatch):
    config = AppConfig(data_dir=tmp_path)
    _run_upgrade(config.database_path, "0002_market_to_exchange")

    def fail_backup(*args):
        raise RuntimeError("Synthetic backup failure")

    monkeypatch.setattr(schema_migrations, "create_validated_database_backup", fail_backup)
    with pytest.raises(RuntimeError, match="backup failure"):
        ensure_database_schema(config)
    assert get_database_revision(config.database_path) == "0002_market_to_exchange"
    engine = create_database_engine(config.database_url)
    try:
        assert "portfolios" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
