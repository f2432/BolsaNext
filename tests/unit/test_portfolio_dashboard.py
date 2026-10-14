"""Offline dashboard regressions: clock and providers are fully synthetic."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from bolsa.app.ports.errors import MarketDataUnavailableError
from bolsa.app.services.portfolio_dashboard_service import PortfolioDashboardService
from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService
from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.policy import PolicyParameters
from bolsa.domain.portfolio.valuation import PriceQuote, FxQuote
from bolsa.domain.portfolio.values import MoneyComponent, ReportedSettlement


class Clock:
    now = datetime(2026, 5, 1, 12, tzinfo=timezone.utc)
    def __call__(self):
        return self.now


class Repository:
    def __init__(self, p):
        self.portfolios = {p.portfolio_uid: p}
    def list_portfolios(self):
        return tuple(self.portfolios.values())


class Quotes:
    def __init__(self, clock):
        self.calls = 0
        self.stamp = clock.now
        self.fail = False
    def get_quote(self, instrument):
        self.calls += 1
        if self.fail:
            raise MarketDataUnavailableError("synthetic offline")
        return PriceQuote(instrument.ticker, instrument.currency, Decimal("110"), self.stamp, "synthetic")


class Fx:
    def __init__(self, clock):
        self.calls = 0
        self.stamp = clock.now
    def get_rate(self, source, base):
        self.calls += 1
        return FxQuote(source, base, Decimal(".95"), self.stamp, "synthetic")


def sample(currency="EUR", **kwargs):
    trade = Trade(Instrument("TEST", currency=currency), TradeType.BUY, Decimal("10"),
                  MoneyComponent(Decimal("100"), currency, Decimal(".9") if currency != "EUR" else None),
                  MoneyComponent(Decimal("0"), "EUR"), date(2026, 1, 1), **kwargs)
    return Portfolio("Synthetic", "EUR").record(trade)


def setup(p):
    clock = Clock()
    quotes, fx = Quotes(clock), Fx(clock)
    repo = Repository(p)
    service = PortfolioDashboardService(repo, PortfolioValuationService(fx), quotes, clock=clock)
    return service, repo, clock, quotes, fx


def test_reconcile_preserves_fresh_valuation_risk_and_sources_without_network():
    p = sample("USD")
    p = p.add_policy(PolicyParameters(max_asset_weight=Decimal(".5")), expected_head=None,
                     effective_at=Clock.now, recorded_at=Clock.now, reason="Synthetic")
    service, _, clock, quotes, fx = setup(p)
    first = service.overview(p.portfolio_uid, market=True)
    clock.now += timedelta(hours=1)
    quotes.fail = True
    result = service.reconcile(p.portfolio_uid)
    assert result.valuation.total_market_value == first.valuation.total_market_value == 1045
    assert result.analysis.risk == first.analysis.risk
    assert result.analysis.composite_result == first.analysis.composite_result
    assert result.analysis.reconciliation.state == "consistent"
    assert result.valuation.evaluated_at == clock.now
    assert result.valuation.positions[0].price_quote == first.valuation.positions[0].price_quote
    assert result.valuation.positions[0].fx_quote == first.valuation.positions[0].fx_quote
    assert (quotes.calls, fx.calls) == (1, 1)


@pytest.mark.parametrize("component", ["price", "fx"])
def test_expired_price_or_fx_disables_market_risk_but_not_accounting(component):
    p = sample("USD")
    service, _, clock, quotes, fx = setup(p)
    if component == "price":
        quotes.stamp -= timedelta(hours=71)
    else:
        fx.stamp -= timedelta(hours=71)
    assert service.overview(p.portfolio_uid, market=True).valuation.complete
    clock.now += timedelta(hours=2)
    result = service.reconcile(p.portfolio_uid)
    assert result.valuation.total_market_value is None
    assert result.valuation.positions[0].state == "stale"
    assert result.analysis.risk.asset_weights == (("TEST", None),)
    assert result.analysis.reconciliation.state == "consistent"
    assert result.analysis.composite_result is None
    assert (quotes.calls, fx.calls) == (1, 1)


def test_freshness_boundary_and_clock_reversal_do_not_invent_quote_times():
    p = sample()
    service, _, clock, quotes, fx = setup(p)
    first = service.overview(p.portfolio_uid, market=True)
    clock.now += timedelta(hours=72)
    assert service.reconcile(p.portfolio_uid).valuation.complete
    clock.now += timedelta(microseconds=1)
    assert not service.reconcile(p.portfolio_uid).valuation.complete
    clock.now = first.valuation.evaluated_at - timedelta(seconds=1)
    future = service.reconcile(p.portfolio_uid)
    assert not future.valuation.complete
    assert future.valuation.positions[0].state == "unreliable_time"
    assert future.valuation.positions[0].price_quote.quoted_at == quotes.stamp
    assert (quotes.calls, fx.calls) == (1, 0)


@pytest.mark.parametrize("stamp", [None, date(2026, 4, 28), datetime(2026, 5, 2, tzinfo=timezone.utc)])
def test_missing_stale_date_only_or_future_quotes_never_become_current(stamp):
    p = sample()
    service, _, _, quotes, fx = setup(p)
    quotes.stamp = stamp
    assert not service.overview(p.portfolio_uid, market=True).valuation.complete
    result = service.reconcile(p.portfolio_uid)
    assert not result.valuation.complete
    assert result.analysis.reconciliation.state == "consistent"
    assert result.valuation.positions[0].price_quote.quoted_at == stamp
    assert (quotes.calls, fx.calls) == (1, 0)


@pytest.mark.parametrize("change", ["buy", "sell", "correction", "cancellation", "dividend", "split"])
def test_financial_changes_invalidate_snapshots_before_offline_reconcile(change):
    p = sample()
    service, repo, _, quotes, fx = setup(p)
    service.overview(p.portfolio_uid, market=True)
    head = p.versions[0]
    if change == "buy":
        p = p.record(replace(head.trade, executed_at=date(2026, 1, 2)))
    elif change == "sell":
        p = p.record(replace(head.trade, kind=TradeType.SELL, quantity=Decimal("1"), executed_at=date(2026, 1, 2)))
    elif change == "correction":
        p = p.revise(head.transaction_uid, head.transaction_version_uid,
                     replace(head.trade, quantity=Decimal("11")), reason="Synthetic")
    elif change == "cancellation":
        p = p.revise(head.transaction_uid, head.transaction_version_uid, None, reason="Synthetic")
    elif change == "dividend":
        def money(amount):
            return MoneyComponent(Decimal(amount), "EUR")
        p = p.record(Dividend(head.trade.instrument, money("10"), money("2"), money("0"),
                              money("8"), date(2026, 1, 2)))
    else:
        p = p.record(Split(head.trade.instrument, Decimal("2"), "Synthetic", date(2026, 1, 2)))
    repo.portfolios[p.portfolio_uid] = p
    result = service.reconcile(p.portfolio_uid)
    assert result.portfolio == p
    assert result.valuation.ledger_revision == p.ledger_revision
    assert result.valuation.total_market_value == (0 if change == "cancellation" else None)
    assert result.analysis.reconciliation.state == "consistent"
    assert (quotes.calls, fx.calls) == (1, 0)
    refreshed = service.overview(p.portfolio_uid, market=True)
    assert refreshed.valuation.complete
    assert quotes.calls == (1 if change == "cancellation" else 2)


def test_policy_change_and_future_activation_recompute_risk_without_network():
    p = sample()
    service, repo, clock, quotes, fx = setup(p)
    first = service.overview(p.portfolio_uid, market=True)
    p = p.add_policy(PolicyParameters(max_asset_weight=Decimal(".5")), expected_head=None,
                     effective_at=clock.now + timedelta(hours=1), recorded_at=clock.now, reason="Synthetic")
    repo.portfolios[p.portfolio_uid] = p
    assert not service.reconcile(p.portfolio_uid).analysis.risk.alerts
    clock.now += timedelta(hours=1)
    result = service.reconcile(p.portfolio_uid)
    assert result.valuation.total_market_value == first.valuation.total_market_value
    assert result.analysis.risk.alerts[0].state == "exceeded"
    assert result.analysis.risk.policy_version_uid == p.policies[0].policy_version_uid
    assert (quotes.calls, fx.calls) == (1, 0)


def test_offline_accounting_and_pending_settlement_are_not_market_errors():
    p = sample(reported_settlement=ReportedSettlement(Decimal("-999"), "EUR"))
    service, _, _, quotes, fx = setup(p)
    quotes.fail = True
    result = service.reconcile(p.portfolio_uid)
    assert result.analysis.reconciliation.state == "information_insufficient"
    assert "Observed settlement difference" in result.analysis.reconciliation.issues[0]
    assert (quotes.calls, fx.calls) == (0, 0)
    service.overview(p.portfolio_uid, market=True)
    repeated = service.reconcile(p.portfolio_uid)
    assert repeated.valuation.total_market_value is None
    assert "synthetic offline" in repeated.valuation.data_errors[0]
    assert (quotes.calls, fx.calls) == (1, 0)


def test_last_valid_snapshot_survives_failed_refresh_with_original_freshness():
    p = sample()
    service, _, clock, quotes, fx = setup(p)
    first = service.overview(p.portfolio_uid, market=True)
    quotes.fail = True
    assert not service.overview(p.portfolio_uid, market=True).valuation.complete
    result = service.reconcile(p.portfolio_uid)
    assert result.valuation.total_market_value == first.valuation.total_market_value
    assert result.valuation.positions[0].price_quote.quoted_at == first.valuation.positions[0].price_quote.quoted_at
    clock.now += timedelta(hours=73)
    assert not service.reconcile(p.portfolio_uid).valuation.complete
    assert (quotes.calls, fx.calls) == (2, 0)


def test_snapshots_are_scoped_to_portfolio_and_explicit_revalue_rejects_other_revision():
    from bolsa.domain.portfolio.values import PortfolioError
    p = sample()
    service, repo, clock, quotes, fx = setup(p)
    first = service.overview(p.portfolio_uid, market=True)
    other = sample()
    repo.portfolios[other.portfolio_uid] = other
    assert not service.reconcile(other.portfolio_uid).valuation.complete
    with pytest.raises(PortfolioError, match="revision"):
        service._valuation.revalue(other, first.valuation, now=clock.now)
    assert service.reconcile(p.portfolio_uid).valuation.complete
    assert (quotes.calls, fx.calls) == (1, 0)


def test_partial_refresh_replaces_expired_full_snapshot_without_losing_known_subtotal():
    p = sample()
    p = p.record(replace(p.versions[0].trade, instrument=Instrument("OTHER", currency="EUR")))
    service, _, clock, quotes, fx = setup(p)
    assert service.overview(p.portfolio_uid, market=True).valuation.total_market_value == 2200
    clock.now += timedelta(hours=73)
    quotes.stamp = clock.now
    original = quotes.get_quote
    def partial(instrument):
        if instrument.ticker == "OTHER":
            quotes.calls += 1
            raise MarketDataUnavailableError("synthetic partial")
        return original(instrument)
    quotes.get_quote = partial
    refreshed = service.overview(p.portfolio_uid, market=True)
    assert refreshed.valuation.total_market_value is None
    assert refreshed.valuation.known_market_subtotal == 1100
    reconciled = service.reconcile(p.portfolio_uid)
    assert reconciled.valuation.total_market_value is None
    assert reconciled.valuation.known_market_subtotal == 1100
    assert "synthetic partial" in reconciled.valuation.data_errors[0]
    assert (quotes.calls, fx.calls) == (4, 0)


def test_late_old_reader_cannot_replace_or_delete_newer_revision_snapshot():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    p = sample()
    service, repo, clock, _, fx = setup(p)
    started, release = Event(), Event()
    class RacingQuotes:
        calls = 0
        def get_quote(self, instrument):
            self.calls += 1
            if self.calls == 1:
                started.set()
                if not release.wait(5):
                    raise RuntimeError("Synthetic reader timeout")
                price = Decimal("110")
            else:
                price = Decimal("120")
            return PriceQuote(instrument.ticker, "EUR", price, clock.now, "synthetic")
    quotes = RacingQuotes()
    service._quotes = quotes
    with ThreadPoolExecutor(max_workers=1) as executor:
        delayed = executor.submit(service.overview, p.portfolio_uid, market=True)
        try:
            assert started.wait(5)
            newer = p.record(replace(p.versions[0].trade, executed_at=date(2026, 1, 2)))
            repo.portfolios[p.portfolio_uid] = newer
            assert service.overview(p.portfolio_uid, market=True).valuation.total_market_value == 2400
        finally:
            release.set()
        assert delayed.result(timeout=5).valuation.total_market_value == 1100
    # Model another reader whose SQLite read snapshot predates the newer commit.
    original_list = repo.list_portfolios
    repo.list_portfolios = lambda: (p,)
    assert service.reconcile(p.portfolio_uid).valuation.total_market_value is None
    repo.list_portfolios = original_list
    assert service.reconcile(p.portfolio_uid).valuation.total_market_value == 2400
    assert (quotes.calls, fx.calls) == (2, 0)
