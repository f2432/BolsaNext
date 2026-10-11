from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fractions import Fraction
import json
import random

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from bolsa.config import AppConfig, prepare_environment
from bolsa.app.services.portfolio_transfer_service import (
    PortfolioTransferService,
    export_json,
    parse_json,
)
from bolsa.app.portfolio_forms import decimal_text
from bolsa.domain.portfolio.models import Portfolio, Ledger, TransactionVersion, uid
from bolsa.domain.portfolio.ledger import replay
from bolsa.domain.portfolio.money import Money, LedgerError, StaleRevisionError
from bolsa.infrastructure.database import ensure_database_schema, create_database_engine
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository


def test_concurrent_sells_and_corrections_one_commit(service, repository, trade):
    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    original = service.record(uid_, trade(), expected_revision=0)

    def sell(_):
        try:
            service.record(uid_, trade("SELL", "8", day=1), expected_revision=1)
            return "commit"
        except StaleRevisionError:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(sell, range(2))) == ["commit", "stale"]
    assert replay(repository.load(uid_)).positions[0].quantity == 2
    head = original.versions[0]

    def correct(_):
        try:
            service.revise(
                uid_,
                replace(head.transaction, price=Money(Decimal(110), "EUR")),
                expected_revision=2,
                expected_head=head.transaction_version_uid,
                reason="synthetic fix",
            )
            return "commit"
        except StaleRevisionError:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(correct, range(2))) == ["commit", "stale"]
    assert repository.load(uid_).revision == 3


def test_concurrent_import_plans_one_commit(service, repository, trade):
    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    ledger = service.record(uid_, trade(), expected_revision=0)
    incoming = replace(ledger, versions=ledger.versions + (TransactionVersion(trade(day=1)),))
    transfer = PortfolioTransferService(repository)
    plan = transfer.preview(export_json(incoming), mode="complement", target_uid=uid_)

    def confirm(_):
        try:
            transfer.confirm(plan)
            return "commit"
        except StaleRevisionError:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirm, range(2))) == ["commit", "stale"]
    assert len(repository.load(uid_).versions) == 2


def test_restore_into_empty_database_preserves_uuid_void_and_fx(
    service, repository, trade, tmp_path
):
    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    tx = trade(
        price="1.12345678",
        quantity=".125",
        source="synthetic",
        account_ref="test",
        external_id="001",
    )
    tx = replace(tx, price=Money(tx.price.amount, "USD", Decimal(".876543210123"), "1.12345678"))
    ledger = service.record(uid_, tx, expected_revision=0)
    ledger = service.void(
        uid_,
        tx.transaction_uid,
        expected_revision=1,
        expected_head=ledger.versions[0].transaction_version_uid,
        reason="cancel",
    )
    config = AppConfig(data_dir=tmp_path / "restore")
    prepare_environment(config)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    try:
        fresh = SqlAlchemyPortfolioRepository(engine)
        transfer = PortfolioTransferService(fresh)
        text_ = export_json(ledger)
        restored, report = transfer.confirm(transfer.preview(text_, mode="restore"))
        assert restored.portfolio == ledger.portfolio and restored.versions == ledger.versions
        assert replay(restored) == replay(ledger) and report.inserted == 2
        assert fresh.load(uid_) == restored
    finally:
        engine.dispose()


def test_json_v1_backward_compatibility_and_origin_timezone(trade):
    tx = replace(
        trade(),
        executed_at=datetime(2026, 1, 1, 13, tzinfo=timezone(timedelta(hours=1))),
        execution_timezone=None,
    )
    ledger = Ledger(Portfolio("S", "EUR"), (TransactionVersion(tx),))
    assert tx.executed_at.hour == 12 and tx.execution_timezone == "UTC+01:00"
    assert parse_json(export_json(ledger)).versions == ledger.versions
    data = json.loads(export_json(ledger))
    data["format_version"] = 1
    data.pop("policies")
    data["versions"][0]["transaction"].pop("execution_timezone")
    restored = parse_json(json.dumps(data))
    assert restored.versions[0].transaction.executed_at == tx.executed_at
    assert replay(restored) == replay(ledger)


def test_invalid_reference_chain_and_related_provenance(trade):
    tx = trade(related_transaction_uid=uid())
    with pytest.raises(LedgerError):
        replay(Ledger(Portfolio("S", "EUR"), (TransactionVersion(tx),)))
    first = TransactionVersion(trade())
    broken = TransactionVersion(first.transaction, 2, previous_version_uid=uid(), reason="broken")
    with pytest.raises(LedgerError):
        replay(Ledger(Portfolio("S", "EUR"), (first, broken)))


def test_sql_constraints_independent_of_service(service, repository, trade):
    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    service.record(uid_, trade(), expected_revision=0)
    with repository.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN")
        row = connection.execute(text("SELECT * FROM portfolio_versions")).mappings().first()
        fields = dict(row)
        fields["transaction_version_uid"] = uid()
        sql = text(
            "INSERT INTO portfolio_versions ("
            + ",".join(fields)
            + ") VALUES ("
            + ",".join(":" + k for k in fields)
            + ")"
        )
        with pytest.raises(IntegrityError):
            connection.execute(sql, fields)
        fields["portfolio_uid"] = uid()
        with pytest.raises(IntegrityError):
            connection.execute(sql, fields)
        connection.rollback()


@pytest.mark.parametrize("currency", ["XYZ", "EURO", "", None])
def test_invalid_default_currency_never_falls_back(currency):
    with pytest.raises((LedgerError, AttributeError)):
        AppConfig(default_base_currency=currency)


@pytest.mark.parametrize("value", [1.25, "bad"])
def test_money_requires_exact_decimal(value):
    with pytest.raises(LedgerError):
        Money(value, "EUR")


@pytest.mark.parametrize(
    "fields",
    [
        dict(quantity=Decimal("-1")),
        dict(observed_net="bad"),
        dict(type="BUY"),
        dict(notes=123),
        dict(broker_sequence=True),
        dict(external_id="partial"),
    ],
)
def test_invalid_fact_types(trade, fields):
    with pytest.raises(LedgerError):
        replace(trade(), **fields)


def test_decimal_text_accepts_portuguese_comma_without_float():
    assert decimal_text("0,12345678") == Decimal(".12345678")
    with pytest.raises(LedgerError):
        decimal_text("1.234,56")


def test_deterministic_randomized_roundtrip_with_independent_cashflow_oracle(trade):
    rng = random.Random(2432)
    transactions = []
    quantity = 0
    buys, proceeds = Fraction(0), Fraction(0)
    for day in range(150):
        price = Decimal(rng.randint(1, 10000)) / Decimal(100)
        fee = Decimal(rng.randint(0, 20)) / Decimal(100)
        if quantity == 0 or rng.random() < 0.6:
            q = rng.randint(1, 10)
            transactions.append(trade(quantity=str(q), price=str(price), fee=str(fee), day=day))
            buys += Fraction(q) * Fraction(price) + Fraction(fee)
            quantity += q
        else:
            q = rng.randint(1, quantity)
            transactions.append(trade("SELL", str(q), str(price), str(fee), day=day))
            proceeds += Fraction(q) * Fraction(price) - Fraction(fee)
            quantity -= q
    if quantity:
        transactions.append(trade("SELL", str(quantity), "100", day=151))
        proceeds += Fraction(quantity * 100)
    ledger = Ledger(Portfolio("S", "EUR"), tuple(TransactionVersion(tx) for tx in transactions))
    restored = parse_json(export_json(ledger))
    result = replay(restored).positions[0]
    assert result.quantity == result.cost == 0
    expected = proceeds - buys
    assert result.realized_pnl == Decimal(expected.numerator) / Decimal(expected.denominator)
    assert replay(restored) == replay(ledger)


def test_internal_ledger_migration_backup_failure_blocks_upgrade(tmp_path, monkeypatch):
    import bolsa.infrastructure.database.schema_migrations as migrations

    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    migrations._run_upgrade(config.database_path, "0002_market_to_exchange")

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic backup failure")

    monkeypatch.setattr(migrations, "create_validated_database_backup", fail)
    with pytest.raises(RuntimeError, match="backup failure"):
        ensure_database_schema(config)
    assert migrations.get_database_revision(config.database_path) == "0002_market_to_exchange"
    engine = create_database_engine(config.database_url)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT name FROM sqlite_master WHERE name='portfolios'")
            ).first()
            is None
        )
    engine.dispose()


def test_unknown_extra_financial_component_detected(service, repository, trade):
    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    ledger = service.record(uid_, trade(), expected_revision=0)
    with repository.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO portfolio_components(portfolio_uid,transaction_version_uid,role,amount,currency) "
                "VALUES(:p,:v,:r,:a,:c)"
            ),
            dict(p=uid_, v=ledger.versions[0].transaction_version_uid, r="unknown", a="1", c="EUR"),
        )
    with pytest.raises(LedgerError, match="desconhecida"):
        repository.load(uid_)


def test_full_replay_10000_events_and_early_correction(trade):
    versions = tuple(
        TransactionVersion(trade(quantity="1", price="0.12345678", day=i)) for i in range(10000)
    )
    ledger = Ledger(Portfolio("S", "EUR"), versions)
    result = replay(ledger)
    assert result.positions[0].quantity == 10000 and result.positions[0].cost == Decimal(
        "1234.5678"
    )
    original = versions[0]
    correction = TransactionVersion(
        replace(original.transaction, quantity=Decimal(2)),
        2,
        previous_version_uid=original.transaction_version_uid,
        reason="synthetic earliest correction",
    )
    corrected = replace(ledger, versions=ledger.versions + (correction,))
    assert replay(corrected).positions[0].quantity == 10001
    assert replay(ledger) == result


def test_actual_migration_ddl_failure_rolls_back_schema_and_revision(tmp_path, monkeypatch):
    import bolsa.infrastructure.database.schema_migrations as migrations
    from alembic import op

    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    migrations._run_upgrade(config.database_path, "0002_market_to_exchange")
    original = op.create_table

    def fail_table(name, *args, **kwargs):
        if name == "portfolio_components":
            raise RuntimeError("synthetic mid-DDL failure")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(op, "create_table", fail_table)
    with pytest.raises(RuntimeError, match="mid-DDL"):
        ensure_database_schema(config)
    assert migrations.get_database_revision(config.database_path) == "0002_market_to_exchange"
    engine = create_database_engine(config.database_url)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT name FROM sqlite_master WHERE name LIKE 'portfolio%'")
            ).all()
            == []
        )
    assert len(list(config.backups_dir.glob("*.sqlite3"))) == 1
    engine.dispose()


def test_policy_write_failure_after_ledger_import_rolls_back_everything(service, repository, trade):
    from sqlalchemy import event
    from bolsa.app.services.portfolio_policy_service import PortfolioPolicyService
    from bolsa.domain.portfolio.importing import ImportRejected

    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    service.record(uid_, trade(), expected_revision=0)
    ledger = PortfolioPolicyService(repository).set_policy(
        uid_, expected_revision=1, max_instrument_weight=Decimal(".7")
    )
    transfer = PortfolioTransferService(repository)
    plan = transfer.preview(export_json(ledger), mode="clone")

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO portfolio_policies"):
            raise RuntimeError("synthetic policy-write failure")

    event.listen(repository.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(ImportRejected) as exc:
            transfer.confirm(plan)
        assert exc.value.report.inserted == 0
    finally:
        event.remove(repository.engine, "before_cursor_execute", fail)
    assert len(repository.list_portfolios()) == 1 and repository.load(uid_) == ledger


def test_dashboard_consistent_snapshot_reports_realized_dividends_and_fx(
    service, repository, trade
):
    from bolsa.app.services.portfolio_dashboard_service import PortfolioDashboardService
    from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService
    from bolsa.domain.portfolio.valuation import Quote, FxRate
    from bolsa.domain.instruments import Instrument
    from test_dividends_adjustments import dividend

    uid_ = service.create("S", "EUR").portfolio.portfolio_uid
    transaction = replace(
        trade(quantity="1"),
        instrument=Instrument("TEST", currency="USD"),
        price=Money(Decimal(100), "USD", Decimal(".9")),
    )
    ledger = service.record(uid_, transaction, expected_revision=0)
    service.record(uid_, dividend(instrument=transaction.instrument), expected_revision=1)

    class Market:
        def get_quote(self, instrument):
            return Quote(
                instrument.ticker, "USD", Decimal(110), datetime.now(timezone.utc), "synthetic"
            )

        def get_rate(self, original, base):
            return FxRate(original, base, Decimal(".85"), datetime.now(timezone.utc), "synthetic")

    provider = Market()
    dashboard = PortfolioDashboardService(
        service, PortfolioValuationService(repository, provider, provider)
    ).overview(uid_, market=True)
    assert dashboard.valuation.total == Decimal(
        "93.5"
    ) and dashboard.valuation.unrealized_pnl == Decimal("3.5")
    assert dashboard.realized_total == 0 and dashboard.dividends_total == Decimal("41.5")
    assert (
        next(
            v.transaction
            for v in dashboard.ledger.versions
            if v.transaction.transaction_uid == transaction.transaction_uid
        ).price.fx_rate
        == ledger.versions[0].transaction.price.fx_rate
    )


@pytest.mark.parametrize("original", [{"invalid": "object"}, 1.25])
def test_origin_financial_text_is_not_a_float_or_object(original):
    with pytest.raises(LedgerError, match="textual"):
        Money(Decimal(1), "EUR", original_text=original)


@pytest.mark.parametrize("flag", ["false", 1])
def test_audit_void_flag_must_be_boolean(trade, flag):
    with pytest.raises(LedgerError, match="booleano"):
        TransactionVersion(trade(), voided=flag)


def test_policy_and_audit_notes_are_typed_text_before_import(trade):
    from bolsa.domain.portfolio.policy import InvestmentPolicy

    with pytest.raises(LedgerError):
        InvestmentPolicy(notes={"invalid": "object"})
    with pytest.raises(LedgerError):
        TransactionVersion(trade(), reason=["invalid"])
