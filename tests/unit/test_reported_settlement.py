from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from bolsa.app.portfolio_format import export_portfolio, parse_portfolio
from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.events import Dividend
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.reconciliation import ReconciliationState, reconcile
from bolsa.domain.portfolio.valuation import PriceQuote, value_portfolio
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError, ReportedSettlement

D = Decimal
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def trade():
    return Trade(Instrument("TEST"), TradeType.BUY, D(10), MoneyComponent(D(100), "EUR"),
                 MoneyComponent(D(5), "EUR"), AT,
                 reported_settlement=ReportedSettlement(D(-1006), "EUR"),
                 original_facts=(("raw_cashflow", "-1006.0000"),))


def test_observed_cashflow_difference_preserved_without_automatic_fee_or_pnl():
    p = Portfolio("Synthetic", "EUR").record(trade())
    replay = p.reconstruct()
    position = replay.position("TEST")
    assert position.cost == D(1005) and position.realized_pnl == D(0)
    assert not position.accounting_confirmed
    difference = replay.pending_reconciliation[0]
    assert (difference.expected_cashflow_base, difference.reported_cashflow_base, difference.difference_base) == (
        D(-1005), D(-1006), D(-1)
    )
    assert reconcile(p).state is ReconciliationState.INFORMATION_INSUFFICIENT
    assert parse_portfolio(export_portfolio(p)).reconstruct() == replay
    assert parse_portfolio(export_portfolio(p)).versions[0].trade.original_facts == trade().original_facts


def test_pending_cost_cannot_produce_definitive_unrealized_pnl():
    p = Portfolio("Synthetic", "EUR").record(trade())
    result = value_portfolio(p, {"TEST": PriceQuote("TEST", "EUR", D(110), AT, "synthetic")}, {}, now=AT)
    assert result.total_market_value == D(1100)
    assert result.total_unrealized_pnl is None and not result.accounting_confirmed
    assert result.positions[0].unrealized_pnl is None and result.positions[0].reason


def test_explicit_component_correction_resolves_difference_and_preserves_original():
    p = Portfolio("Synthetic", "EUR").record(trade())
    original = p.versions[0]
    fixed = replace(trade(), commission=MoneyComponent(D(6), "EUR"))
    p = p.revise(original.transaction_uid, original.transaction_version_uid, fixed,
                 reason="Synthetic fee explicitly confirmed; no automatic classification")
    assert p.versions[0] == original
    assert not p.reconstruct().pending_reconciliation
    assert p.reconstruct().position("TEST").accounting_confirmed
    assert p.reconstruct().position("TEST").cost == D(1006)


def test_correction_cannot_hide_or_rewrite_confirmed_observed_cashflow():
    p = Portfolio("Synthetic", "EUR").record(trade())
    head = p.versions[0]
    for payload in (replace(trade(), reported_settlement=None),
                    replace(trade(), reported_settlement=ReportedSettlement(D(-1005), "EUR"))):
        with pytest.raises(PortfolioError, match="cannot be erased"):
            p.revise(head.transaction_uid, head.transaction_version_uid, payload, reason="Attempt to hide discrepancy")
    assert p.reconstruct().pending_reconciliation[0].reported_cashflow_base == D(-1006)


def test_reported_settlement_fx_is_independent_and_exactly_portable():
    t = replace(trade(), unit_price=MoneyComponent(D(100), "USD", D("0.9")),
                reported_settlement=ReportedSettlement("-1006", "USD", "0.91"))
    p = Portfolio("Synthetic", "EUR").record(t)
    loaded = parse_portfolio(export_portfolio(p))
    assert loaded.reconstruct() == p.reconstruct()
    assert loaded.versions[0].trade.reported_settlement.historical_fx == D("0.91")
    with pytest.raises(PortfolioError, match="Missing historical FX"):
        Portfolio("Synthetic", "EUR").record(replace(t, reported_settlement=ReportedSettlement(D(-1006), "USD")))


def test_dividend_observed_net_difference_is_pending_not_a_hidden_adjustment():
    def m(value):
        return MoneyComponent(D(value), "EUR")
    event = Dividend(Instrument("TEST"), m(50), m("7.5"), m(1), m("41.5"), AT,
                     reported_settlement=ReportedSettlement(D(42), "EUR"))
    p = Portfolio("Synthetic", "EUR").record(event)
    assert p.reconstruct().position("TEST").dividend_income == D("41.5")
    assert p.reconstruct().pending_reconciliation[0].difference_base == D("0.5")
    assert reconcile(p).state is ReconciliationState.INFORMATION_INSUFFICIENT


@pytest.mark.parametrize("value", [1.2, D("NaN"), D("Infinity"), "-0.000000001"])
def test_reported_settlement_validates_exact_signed_inputs(value):
    with pytest.raises(PortfolioError):
        ReportedSettlement(value, "EUR")
