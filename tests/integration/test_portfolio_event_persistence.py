from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Column, Engine, MetaData, Table, event
from sqlalchemy.exc import IntegrityError

from bolsa.app.services.portfolio_service import PortfolioService
from bolsa.config import AppConfig
from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError
from bolsa.infrastructure.database import create_database_engine, ensure_database_schema
from bolsa.infrastructure.database.decimal_type import ExactDecimalText
from bolsa.infrastructure.database.schema_migrations import _run_upgrade, get_database_revision
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository, _encode

D = Decimal
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
ASSET = Instrument("TEST")


def money(value):
    return MoneyComponent(D(value), "EUR")


def buy():
    return Trade(ASSET, TradeType.BUY, D(10), money("100"), money("0"), AT)


def dividend():
    return Dividend(ASSET, money("50"), money("7.5"), money("1"), money("41.5"), AT + timedelta(days=1))


def split():
    return Split(ASSET, D(2), "Synthetic forward split", AT + timedelta(days=2))


def _p1_database(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    _run_upgrade(config.database_path, "0003_portfolio_ledger")
    engine = create_database_engine(config.database_url)
    p = Portfolio("Synthetic", "EUR").record(buy())
    first = p.versions[0]
    p = p.revise(first.transaction_uid, first.transaction_version_uid,
                 replace(buy(), quantity=D(12)), reason="Synthetic correction")
    p = p.record(replace(buy(), kind=TradeType.SELL, quantity=D(2),
                         executed_at=AT + timedelta(days=1)))
    metadata = MetaData()
    old = Table("portfolio_versions", metadata,
                *(Column(name, ExactDecimalText()) for name in (
                    "quantity", "price", "price_fx", "commission", "commission_fx"
                )), autoload_with=engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO instruments (ticker, asset_type) VALUES ('TEST', 'stock')")
        connection.exec_driver_sql("INSERT INTO portfolios (portfolio_uid, name, base_currency, ledger_revision) "
                                  "VALUES (?, ?, ?, ?)",
                                  (str(p.portfolio_uid), p.name, p.base_currency, p.ledger_revision))
        for version in p.versions:
            connection.execute(old.insert().values(**_encode(version)))
    engine.dispose()
    return config, p


def test_p1_promotion_preserves_audit_then_manual_events_round_trip(tmp_path):
    config, original = _p1_database(tmp_path)
    result = ensure_database_schema(config)
    assert result.previous_revision == "0003_portfolio_ledger"
    assert result.current_revision == "0006_portfolio_policies"
    assert get_database_revision(result.backup_path) == "0003_portfolio_ledger"
    engine = create_database_engine(config.database_url)
    try:
        repository = SqlAlchemyPortfolioRepository(engine)
        loaded = repository.load(original.portfolio_uid)
        assert loaded.reconstruct() == original.reconstruct()
        assert set(loaded.versions) == set(original.versions)
        service = PortfolioService(repository)
        p = service.record(loaded.portfolio_uid, dividend(), expected_revision=3)
        p = service.record(p.portfolio_uid, split(), expected_revision=4)
        before = p.reconstruct()
        engine.dispose()
        assert repository.load(p.portfolio_uid).reconstruct() == before
        assert set(repository.load(p.portfolio_uid).versions) == set(p.versions)
        position = before.position("TEST")
        assert (position.quantity, position.cost, position.dividend_income) == (D(20), D(1000), D("41.5"))
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT count(*) FROM portfolio_versions").scalar() == 3
            assert connection.exec_driver_sql("SELECT count(*) FROM ledger_versions").scalar() == 5
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            assert connection.exec_driver_sql("SELECT gross, withholding, charges, net, typeof(net), quantity, price "
                                              "FROM ledger_versions WHERE trade_kind = 'DIVIDEND'").one() == (
                "50", "7.5", "1", "41.5", "text", None, None
            )
        for sql in (
            "INSERT INTO portfolio_versions SELECT * FROM portfolio_versions LIMIT 1",
            "UPDATE portfolio_versions SET reason = 'rewrite'", "DELETE FROM portfolio_versions",
            "UPDATE ledger_versions SET net = '0'", "DELETE FROM ledger_versions",
        ):
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.exec_driver_sql(sql)
    finally:
        engine.dispose()


def test_failed_promotion_rolls_back_entire_new_table_and_preserves_p1_backup(tmp_path):
    config, original = _p1_database(tmp_path)

    def fail_after_copy(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("CREATE TRIGGER ledger_versions_no_update"):
            raise RuntimeError("Synthetic promotion failure")

    event.listen(Engine, "before_cursor_execute", fail_after_copy)
    try:
        with pytest.raises(RuntimeError, match="promotion failure"):
            ensure_database_schema(config, now=AT)
    finally:
        event.remove(Engine, "before_cursor_execute", fail_after_copy)
    assert get_database_revision(config.database_path) == "0003_portfolio_ledger"
    backups = list(config.backups_dir.glob("*.sqlite3"))
    assert len(backups) == 1 and get_database_revision(backups[0]) == "0003_portfolio_ledger"
    engine = create_database_engine(config.database_url)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT count(*) FROM sqlite_master WHERE name='ledger_versions'").scalar() == 0
            assert connection.exec_driver_sql("SELECT count(*) FROM portfolio_versions").scalar() == original.ledger_revision
            assert connection.exec_driver_sql("PRAGMA quick_check").scalar() == "ok"
    finally:
        engine.dispose()
    ensure_database_schema(config, now=AT + timedelta(seconds=1))
    engine = create_database_engine(config.database_url)
    try:
        assert SqlAlchemyPortfolioRepository(engine).load(original.portfolio_uid).reconstruct() == original.reconstruct()
    finally:
        engine.dispose()


def test_event_corrections_and_invalid_dividend_preserve_persistent_ledger(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    try:
        repository = SqlAlchemyPortfolioRepository(engine)
        service = PortfolioService(repository)
        p = service.create("Synthetic", "EUR")
        p = service.record(p.portfolio_uid, buy(), expected_revision=0)
        p = service.record(p.portfolio_uid, dividend(), expected_revision=1)
        head = p.versions[-1]
        p = service.revise(p.portfolio_uid, head.transaction_uid, head.transaction_version_uid,
                           replace(dividend(), gross=money("60"), net=money("51.5")),
                           reason="Synthetic correction", expected_revision=2)
        loaded = repository.load(p.portfolio_uid)
        assert loaded.reconstruct().position("TEST").dividend_income == D("51.5")
        before = loaded.reconstruct()
        with pytest.raises(PortfolioError):
            service.record(p.portfolio_uid, replace(dividend(), net=money("99")), expected_revision=3)
        assert repository.load(p.portfolio_uid).reconstruct() == before
        head = next(v for v in p.versions if v.version_number == 2)
        p = service.revise(p.portfolio_uid, head.transaction_uid, head.transaction_version_uid, None,
                           reason="Synthetic cancellation", expected_revision=3)
        assert repository.load(p.portfolio_uid).reconstruct().position("TEST").dividend_income == D(0)
        assert len(repository.load(p.portfolio_uid).versions) == 4
    finally:
        engine.dispose()
