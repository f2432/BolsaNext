from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from bolsa.app.portfolio_format import ImportState, PortfolioTransferService, export_portfolio, parse_portfolio
from bolsa.app.services.portfolio_service import PortfolioService
from bolsa.app.services.portfolio_analysis_service import PortfolioAnalysisService
from bolsa.config import AppConfig
from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.ledger import Trade, TradeType
from bolsa.domain.portfolio.policy import PolicyParameters
from bolsa.domain.portfolio.values import LedgerConflictError, MoneyComponent, ReportedSettlement, SignedMoneyComponent
from bolsa.domain.portfolio.valuation import PriceQuote, value_portfolio
from bolsa.domain.portfolio.events import Dividend
from bolsa.infrastructure.database import create_database_engine, ensure_database_schema
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository

D = Decimal
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    try:
        repository = SqlAlchemyPortfolioRepository(engine)
        yield engine, repository, PortfolioService(repository), PortfolioTransferService(repository)
    finally:
        engine.dispose()


def test_policy_versions_persist_without_altering_financial_ledger(store):
    engine, repository, service, _ = store
    p = service.create("Synthetic", "EUR")
    trade = Trade(Instrument("TEST"), TradeType.BUY, D(1), MoneyComponent(D(100), "EUR"),
                  MoneyComponent(D(0), "EUR"), AT)
    p = service.record(p.portfolio_uid, trade, expected_revision=0)
    original = p.versions
    p = service.change_policy(p.portfolio_uid, PolicyParameters(D("0.5")), expected_head=None,
                               effective_at=AT, reason="Synthetic policy")
    first = p.policies[0]
    p = service.change_policy(p.portfolio_uid, PolicyParameters(D("0.8")), expected_head=first.policy_version_uid,
                               effective_at=AT + timedelta(days=1), reason="Synthetic update")
    engine.dispose()
    loaded = repository.load(p.portfolio_uid)
    assert loaded.policies == p.policies and loaded.versions == original
    assert loaded.policy_revision == 2 and loaded.ledger_revision == 1
    with pytest.raises(LedgerConflictError):
        service.change_policy(p.portfolio_uid, PolicyParameters(), expected_head=first.policy_version_uid,
                               effective_at=AT + timedelta(days=2), reason="Obsolete")
    for sql in ("UPDATE portfolio_policies SET payload = '{}'", "DELETE FROM portfolio_policies"):
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.exec_driver_sql(sql)


def test_policies_export_restore_clone_and_old_v1_compatibility(store):
    _, repository, service, transfer = store
    p = service.create("Synthetic", "EUR")
    p = service.change_policy(p.portfolio_uid, PolicyParameters(D("0.12345678")), expected_head=None,
                               effective_at=AT, reason="Synthetic policy")
    assert parse_portfolio(export_portfolio(p)).policies == p.policies
    preview = transfer.preview(export_portfolio(p), mode="clone")
    assert transfer.confirm(preview).state is ImportState.COMPLETED
    loaded = repository.load(preview.candidate.portfolio_uid)
    assert loaded.policies[0].policy_version_uid == p.policies[0].policy_version_uid
    assert loaded.policies[0].parameters == p.policies[0].parameters
    old_v1 = json.loads(export_portfolio(service.create("Old format", "EUR")))
    old_v1.pop("policies")
    assert parse_portfolio(json.dumps(old_v1)).policies == ()


def test_policy_change_invalidates_import_preview_even_if_ledger_revision_is_unchanged(store):
    _, repository, service, transfer = store
    p = service.create("Synthetic", "EUR")
    preview = transfer.preview(export_portfolio(p))
    changed = service.change_policy(p.portfolio_uid, PolicyParameters(D("0.5")), expected_head=None,
                                     effective_at=AT, reason="Synthetic policy")
    result = transfer.confirm(preview)
    assert result.state is ImportState.REJECTED and result.inserted == 0
    assert repository.load(p.portfolio_uid).policies == changed.policies


def test_import_policy_failure_rolls_back_portfolio_and_ledger_together(store):
    engine, repository, service, transfer = store
    p = service.create("Synthetic", "EUR")
    p = service.change_policy(p.portfolio_uid, PolicyParameters(D("0.5")), expected_head=None,
                               effective_at=AT, reason="Synthetic policy")
    preview = transfer.preview(export_portfolio(p), mode="clone")

    def fail_policy(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO portfolio_policies"):
            raise RuntimeError("Synthetic policy insertion failure")

    event.listen(engine, "before_cursor_execute", fail_policy)
    try:
        result = transfer.confirm(preview)
    finally:
        event.remove(engine, "before_cursor_execute", fail_policy)
    assert result.state is ImportState.REJECTED and result.inserted == 0
    with pytest.raises(ValueError):
        repository.load(preview.candidate.portfolio_uid)
    assert repository.load(p.portfolio_uid).policies == p.policies


def test_policy_updates_are_isolated_between_portfolios(store):
    _, repository, service, _ = store
    a = service.create("Same name", "EUR")
    b = service.create("Same name", "USD")
    service.change_policy(a.portfolio_uid, PolicyParameters(D("0.3")), expected_head=None,
                           effective_at=AT, reason="Synthetic policy")
    assert repository.load(b.portfolio_uid).policies == ()
    assert repository.load(a.portfolio_uid).policies[0].parameters.max_asset_weight == D("0.3")


def test_signed_annual_target_is_portable_but_never_calculated(store):
    _, _, service, _ = store
    p = service.create("Synthetic", "EUR")
    p = service.change_policy(p.portfolio_uid, PolicyParameters(annual_return_target=D("-0.1")),
                               expected_head=None, effective_at=AT, reason="Synthetic signed target")
    assert parse_portfolio(export_portfolio(p)).policies[0].parameters.annual_return_target == D("-0.1")


def test_analysis_compound_result_separates_dividends_and_pnl_and_missing_data(store):
    _, repository, service, _ = store
    p = service.create("Synthetic", "EUR")
    trade = Trade(Instrument("TEST"), TradeType.BUY, D(1), MoneyComponent(D(100), "EUR"),
                  MoneyComponent(D(0), "EUR"), AT)
    p = service.record(p.portfolio_uid, trade, expected_revision=0)
    dividend = Dividend(trade.instrument, MoneyComponent(D(10), "EUR"), MoneyComponent(D(1), "EUR"),
                         MoneyComponent(D(0), "EUR"), MoneyComponent(D(9), "EUR"), AT + timedelta(days=1))
    p = service.record(p.portfolio_uid, dividend, expected_revision=1)
    prices = {"TEST": PriceQuote("TEST", "EUR", D(110), AT + timedelta(days=2), "synthetic")}
    valuation = value_portfolio(p, prices, {}, now=AT + timedelta(days=2))
    analysis = PortfolioAnalysisService(repository).analyze(p.portfolio_uid, valuation)
    assert (analysis.realized_pnl, analysis.dividend_income, analysis.unrealized_pnl, analysis.composite_result) == (
        D(0), D(9), D(10), D(19)
    )
    missing = value_portfolio(p, {}, {}, now=AT + timedelta(days=2))
    analysis = PortfolioAnalysisService(repository).analyze(p.portfolio_uid, missing)
    assert analysis.unrealized_pnl is analysis.composite_result is None
    assert analysis.dividend_income == D(9)


def test_observed_settlement_pending_status_survives_database_reopen_and_clone(store):
    engine, repository, service, transfer = store
    p = service.create("Synthetic", "EUR")
    t = Trade(Instrument("TEST"), TradeType.BUY, D(1), MoneyComponent(D(100), "EUR"),
              MoneyComponent(D(0), "EUR"), AT,
              reported_settlement=ReportedSettlement("-101.0000", "EUR"),
              original_facts=(("reported_cashflow_raw", "-101.0000"),))
    p = service.record(p.portfolio_uid, t, expected_revision=0)
    engine.dispose()
    loaded = repository.load(p.portfolio_uid)
    assert loaded.reconstruct().pending_reconciliation[0].difference_base == D(-1)
    assert loaded.versions[0].trade.original_facts == t.original_facts
    prices = {"TEST": PriceQuote("TEST", "EUR", D(110), AT, "synthetic")}
    valuation = value_portfolio(loaded, prices, {}, now=AT)
    analysis = PortfolioAnalysisService(repository).analyze(p.portfolio_uid, valuation)
    assert not analysis.accounting_confirmed and analysis.composite_result is None
    preview = transfer.preview(export_portfolio(loaded), mode="clone")
    assert transfer.confirm(preview).state is ImportState.COMPLETED
    assert repository.load(preview.candidate.portfolio_uid).reconstruct() == loaded.reconstruct()


def test_negative_dividend_net_is_exactly_persistent_and_portable(store):
    engine, repository, service, _ = store
    p = service.create("Synthetic", "EUR")
    event = Dividend(Instrument("TEST"), MoneyComponent(D(50), "EUR"), MoneyComponent(D("7.5"), "EUR"),
                     MoneyComponent(D(60), "EUR"), SignedMoneyComponent(D("-17.5"), "EUR"), AT)
    p = service.record(p.portfolio_uid, event, expected_revision=0)
    engine.dispose()
    loaded = repository.load(p.portfolio_uid)
    assert loaded.reconstruct().position("TEST").dividend_income == D("-17.5")
    assert parse_portfolio(export_portfolio(loaded)).reconstruct() == loaded.reconstruct()
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT net, typeof(net) FROM ledger_versions").one() == ("-17.5", "text")
