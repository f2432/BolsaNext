from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.policy import PolicyParameters, active_policy
from bolsa.domain.portfolio.reconciliation import ReconciliationState, reconcile
from bolsa.domain.portfolio.risk import AlertState, SectorClassification, evaluate_risk
from bolsa.domain.portfolio.valuation import PriceQuote, value_portfolio
from bolsa.domain.portfolio.values import LedgerConflictError, MoneyComponent, PortfolioError

D = Decimal
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
NOW = AT + timedelta(days=2)


def portfolio():
    t = Trade(Instrument("A"), TradeType.BUY, D(1), MoneyComponent(D(100), "EUR"),
              MoneyComponent(D(0), "EUR"), AT)
    return Portfolio("Synthetic", "EUR").record(t).record(replace(t, instrument=Instrument("B")))


def valuation(p, complete=True):
    prices = {"A": PriceQuote("A", "EUR", D(150), NOW, "synthetic")}
    if complete:
        prices["B"] = PriceQuote("B", "EUR", D(50), NOW, "synthetic")
    return value_portfolio(p, prices, {}, now=NOW)


def configured(p):
    return p.add_policy(PolicyParameters(D("0.5"), D("0.8"), D("1"), D("0.1")),
                        expected_head=None, effective_at=AT, recorded_at=AT, reason="Synthetic limits")


def test_descriptive_indicators_without_policy_have_no_invented_limits():
    p = portfolio()
    report = evaluate_risk(p, valuation(p), {"A": SectorClassification("Tech"), "B": SectorClassification("Energy")})
    assert dict(report.asset_weights) == {"A": D("0.75"), "B": D("0.25")}
    assert dict(report.sector_weights) == {"Energy": D("0.25"), "Tech": D("0.75")}
    assert dict(report.quote_currency_weights) == {"EUR": D(1)}
    assert report.alerts == () and report.policy_version_uid is None


def test_optional_policy_produces_informative_three_state_alerts():
    p = configured(portfolio())
    report = evaluate_risk(p, valuation(p), {"A": SectorClassification("Tech"), "B": SectorClassification("Energy")})
    alerts = {a.metric: a for a in report.alerts}
    assert alerts["asset_concentration"].state is AlertState.EXCEEDED
    assert alerts["sector_concentration"].state is AlertState.WITHIN_LIMIT
    assert alerts["quote_currency_concentration"].state is AlertState.WITHIN_LIMIT
    assert alerts["annual_return_target"].state is AlertState.NOT_EVALUABLE
    # Exceeded policy does not prevent financially valid buys or sales.
    assert p.record(replace(p.versions[0].trade, executed_at=NOW)).ledger_revision == 3


def test_incomplete_zero_and_obsolete_valuations_never_mark_compliance():
    p = configured(portfolio())
    for result in (valuation(p, False), replace(valuation(p), total_market_value=D(0)),
                   replace(valuation(p), ledger_revision=999),
                   replace(valuation(p), total_market_value=D(150))):
        report = evaluate_risk(p, result)
        assert all(a.state is AlertState.NOT_EVALUABLE for a in report.alerts)
        assert all(weight is None for _, weight in report.asset_weights)


def test_unknown_sector_and_etf_underlying_are_not_inferred():
    p = configured(portfolio())
    report = evaluate_risk(p, valuation(p), {"A": SectorClassification("Tech")})
    assert "not determined" in dict(report.sector_weights)
    assert next(a for a in report.alerts if a.metric == "sector_concentration").state is AlertState.NOT_EVALUABLE
    etf = replace(p.versions[0].trade, instrument=Instrument("A", asset_type=AssetType.ETF))
    root = Portfolio("Synthetic", "EUR").record(etf)
    quote = value_portfolio(root, {"A": PriceQuote("A", "EUR", D(100), NOW, "synthetic")}, {}, now=NOW)
    assert dict(evaluate_risk(root, quote, {"A": SectorClassification("Tech")}).sector_weights) == {"not determined": D(1)}
    assert dict(evaluate_risk(root, quote, {"A": SectorClassification("Tech", True)}).sector_weights) == {"Tech": D(1)}


def test_blank_or_unknown_sector_metadata_cannot_establish_compliance():
    p = configured(portfolio())
    for label in (" ", "UNKNOWN", "Não determinado", "N/A"):
        metadata = {ticker: SectorClassification(label) for ticker in ("A", "B")}
        report = evaluate_risk(p, valuation(p), metadata)
        sector = next(a for a in report.alerts if a.metric == "sector_concentration")
        assert sector.state is AlertState.NOT_EVALUABLE


def test_policy_versions_vigency_and_obsolete_head_preserve_history():
    p = configured(portfolio())
    first = p.policies[0]
    second = p.add_policy(PolicyParameters(D("0.9")), expected_head=first.policy_version_uid,
                          effective_at=NOW + timedelta(days=1), recorded_at=NOW, reason="Synthetic future limits")
    assert active_policy(second.policies, NOW) == first
    assert active_policy(second.policies, NOW + timedelta(days=2)) == second.policies[-1]
    assert second.versions == p.versions
    with pytest.raises(LedgerConflictError):
        second.add_policy(PolicyParameters(), expected_head=first.policy_version_uid,
                          effective_at=NOW, reason="Obsolete")
    with pytest.raises(PortfolioError):
        replace(second, policies=(first, replace(second.policies[-1], previous_version_uid=uuid4())))


@pytest.mark.parametrize("value", [D("-0.1"), D("1.1"), D("NaN"), D("Infinity"), 0.5])
def test_invalid_policy_limits_are_rejected(value):
    with pytest.raises(PortfolioError):
        PolicyParameters(max_asset_weight=value)


def test_policy_date_and_reason_are_explicit():
    p = portfolio()
    with pytest.raises(PortfolioError):
        p.add_policy(PolicyParameters(), expected_head=None, effective_at=datetime(2026, 1, 1), reason="Synthetic")
    with pytest.raises(PortfolioError):
        p.add_policy(PolicyParameters(), expected_head=None, effective_at=AT, reason="")


def test_internal_reconciliation_separates_discrepancy_and_insufficient_data():
    p = portfolio()
    before = p.reconstruct()
    assert reconcile(p, projection=before.positions).state is ReconciliationState.CONSISTENT
    damaged = (replace(before.positions[0], cost=D(999)), before.positions[1])
    report = reconcile(p, projection=damaged)
    assert report.state is ReconciliationState.DISCREPANCY and report.issues
    assert reconcile(p, valuation=valuation(p, False)).state is ReconciliationState.INFORMATION_INSUFFICIENT
    assert p.reconstruct() == before
    float_projection = (replace(before.positions[0], cost=100.0), before.positions[1])
    assert reconcile(p, projection=float_projection).state is ReconciliationState.DISCREPANCY
