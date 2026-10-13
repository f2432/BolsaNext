from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pandas as pd
import pytest

from bolsa.app.ports.errors import MarketDataUnavailableError
from bolsa.app.ports.fx import FxRateFormatError, FxRateUnavailableError
from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService
from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.valuation import (
    FxQuote, PriceQuote, ValuationState, value_portfolio,
)
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError
from bolsa.infrastructure.market_data.fx_provider import (
    YFinanceFxRateProvider, approximate_market_decimal,
)

D = Decimal
NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def portfolio():
    t = Trade(Instrument("TEST", currency="USD"), TradeType.BUY, D(1),
              MoneyComponent(D(100), "USD", D("0.90")), MoneyComponent(D(0), "EUR"),
              NOW - timedelta(days=10))
    return Portfolio("Synthetic", "EUR").record(t)


def price(ticker="TEST", currency="USD", value="110", age=timedelta(0)):
    return PriceQuote(ticker, currency, D(value), NOW - age, "synthetic")


def fx(source="USD", base="EUR", value="0.85", age=timedelta(0)):
    return FxQuote(source, base, D(value), NOW - age, "synthetic")


def test_approved_current_fx_example_preserves_historical_cost():
    p = portfolio()
    before = p.reconstruct()
    result = value_portfolio(p, {"TEST": price()}, {("USD", "EUR"): fx()}, now=NOW)
    assert result.complete
    assert result.total_market_value == D("93.50")
    assert result.total_unrealized_pnl == D("3.50")
    assert p.reconstruct() == before
    assert p.versions[0].trade.unit_price.historical_fx == D("0.90")
    with localcontext() as context:
        context.prec = 3
        assert value_portfolio(p, {"TEST": price()}, {("USD", "EUR"): fx()}, now=NOW) == result


@pytest.mark.parametrize("quotes,rates,state", [
    ({}, {}, ValuationState.MISSING),
    ({"TEST": price()}, {}, ValuationState.MISSING),
    ({"TEST": price(age=timedelta(hours=73))}, {("USD", "EUR"): fx()}, ValuationState.STALE),
    ({"TEST": price()}, {("USD", "EUR"): fx(age=timedelta(hours=73))}, ValuationState.STALE),
    ({"TEST": replace(price(), quoted_at=None)}, {("USD", "EUR"): fx()}, ValuationState.UNRELIABLE_TIME),
    ({"TEST": price()}, {("USD", "EUR"): replace(fx(), quoted_at=None)}, ValuationState.UNRELIABLE_TIME),
    ({"TEST": price(age=timedelta(seconds=-1))}, {("USD", "EUR"): fx()}, ValuationState.UNRELIABLE_TIME),
])
def test_missing_stale_unknown_and_future_data_never_produce_totals(quotes, rates, state):
    p = portfolio()
    result = value_portfolio(p, quotes, rates, now=NOW)
    assert not result.complete
    assert result.total_market_value is None
    assert result.total_unrealized_pnl is None
    assert result.known_market_subtotal == D(0)
    assert result.positions[0].state is state
    assert result.positions[0].reason
    assert result.positions[0].market_value is None


def test_known_subtotal_is_not_consolidated_total_or_pnl():
    p = portfolio()
    p = p.record(replace(p.versions[0].trade, instrument=Instrument("SECOND")))
    result = value_portfolio(p, {"TEST": price()}, {("USD", "EUR"): fx()}, now=NOW)
    assert result.known_market_subtotal == D("93.50")
    assert result.known_unrealized_subtotal == D("3.50")
    assert result.total_market_value is result.total_unrealized_pnl is None


def test_identity_fx_no_provider_call_and_closed_positions_need_no_quotes():
    class ForbiddenProvider:
        def get_rate(self, *args):
            raise AssertionError("Provider must not be called")

    p = portfolio()
    service = PortfolioValuationService(ForbiddenProvider())
    result = service.evaluate(p, {"TEST": price(currency="EUR", value="95")}, now=NOW)
    assert result.total_market_value == D(95)
    assert result.positions[0].fx_quote.rate == D(1)
    p = p.record(replace(p.versions[0].trade, kind=TradeType.SELL,
                         executed_at=NOW - timedelta(days=1)))
    result = service.evaluate(p, {"TEST": price()}, now=NOW)
    assert result.complete and result.total_market_value == D(0)
    assert result.total_unrealized_pnl == D(0)
    assert result.realized_pnl == D(0)


def test_empty_portfolio_has_zero_totals():
    result = value_portfolio(Portfolio("Empty", "EUR"), {}, {}, now=NOW)
    assert result.complete and result.total_market_value == D(0)


def test_freshness_72h_boundary_and_configurable_limit():
    p = portfolio()
    quote = price(age=timedelta(hours=72))
    result = value_portfolio(p, {"TEST": quote}, {("USD", "EUR"): fx()}, now=NOW)
    assert result.complete
    result = value_portfolio(p, {"TEST": quote}, {("USD", "EUR"): fx()}, now=NOW,
                             max_age=timedelta(hours=24))
    assert not result.complete
    assert result.freshness_policy == "elapsed_time_fallback"


def test_date_only_is_preserved_and_uses_conservative_age():
    quote = replace(price(), quoted_at=date(2026, 10, 11))
    result = value_portfolio(portfolio(), {"TEST": quote}, {("USD", "EUR"): fx()}, now=NOW)
    assert result.complete and type(result.positions[0].price_quote.quoted_at) is date
    result = value_portfolio(portfolio(), {"TEST": quote}, {("USD", "EUR"): fx()}, now=NOW,
                             max_age=timedelta(hours=48))
    assert not result.complete


def test_mismatched_instrument_or_fx_orientation_is_rejected():
    with pytest.raises(PortfolioError, match="instrument"):
        value_portfolio(portfolio(), {"TEST": price(ticker="OTHER")}, {}, now=NOW)
    with pytest.raises(PortfolioError, match="orientation"):
        value_portfolio(portfolio(), {"TEST": price()}, {("USD", "EUR"): fx("EUR", "USD")}, now=NOW)


@pytest.mark.parametrize("value", [D(0), D(-1), D("NaN"), D("Infinity"), 1.2, D("1e18")])
def test_invalid_current_values_are_rejected(value):
    with pytest.raises(PortfolioError):
        replace(price(), price=value)
    with pytest.raises(PortfolioError):
        replace(fx(), rate=value)


def test_invalid_time_and_identity_rate_are_rejected():
    with pytest.raises(PortfolioError):
        replace(price(), quoted_at=datetime(2026, 1, 1))
    with pytest.raises(PortfolioError):
        fx("EUR", "EUR", "2")
    with pytest.raises(PortfolioError):
        value_portfolio(portfolio(), {}, {}, now=datetime(2026, 1, 1))
    with pytest.raises(PortfolioError):
        value_portfolio(portfolio(), {}, {}, now=NOW, max_age=timedelta(0))


class FakeMarket:
    def __init__(self, data=None, failure=None):
        self.data = data
        self.failure = failure
        self.calls = []

    def get_historical_data(self, instrument, **kwargs):
        self.calls.append((instrument.ticker, kwargs))
        if self.failure:
            raise self.failure
        return self.data


def history(values=(1.25,)):
    return pd.DataFrame({"Close": values}, index=pd.date_range("2026-10-10", periods=len(values)))


def test_yahoo_fx_orientation_inversion_and_identity():
    market = FakeMarket(history())
    provider = YFinanceFxRateProvider(market)
    direct = provider.get_rate("EUR", "USD")
    inverse = provider.get_rate("USD", "EUR")
    assert direct.rate == D("1.25")
    assert inverse.rate == D("0.8") and inverse.inverted
    assert inverse.source_pair == "EURUSD=X"
    assert inverse.quoted_at == date(2026, 10, 10)
    assert provider.get_rate("EUR", "EUR").rate == D(1)
    assert len(market.calls) == 2
    assert market.calls[0][1] == {"period": "1mo", "interval": "1d"}


def test_fx_inversion_is_derived_at_50_digits_without_rounding_to_input_scale():
    quote = YFinanceFxRateProvider(FakeMarket(history((3.0,)))).get_rate("USD", "EUR")
    assert quote.rate == D("0." + "3" * 50)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf"), True, "1.25"])
def test_invalid_market_float_boundary(value):
    with pytest.raises(FxRateFormatError):
        approximate_market_decimal(value)


def test_float_boundary_uses_text_not_binary_decimal_constructor():
    assert approximate_market_decimal(0.1) == D("0.1")


@pytest.mark.parametrize("data", [
    pd.DataFrame({"Open": [1.0]}, index=pd.date_range("2026-10-10", periods=1)),
    pd.DataFrame({"Close": [1.0]}, index=["unknown date"]),
    pd.DataFrame({"Close": [1.0, 2.0]}, index=[date(2026, 10, 10)] * 2),
])
def test_malformed_fx_history_is_typed(data):
    with pytest.raises(FxRateFormatError):
        YFinanceFxRateProvider(FakeMarket(data)).get_rate("USD", "EUR")


def test_unknown_fx_currency_and_unexpected_payload_are_typed():
    provider = YFinanceFxRateProvider(FakeMarket(None))
    with pytest.raises(FxRateFormatError):
        provider.get_rate("USD", "EUR")
    with pytest.raises(FxRateFormatError):
        provider.get_rate("AAA", "EUR")


def test_empty_unavailable_fx_and_service_recovery_preserve_ledger():
    for market in (FakeMarket(pd.DataFrame()), FakeMarket(failure=MarketDataUnavailableError("synthetic"))):
        with pytest.raises(FxRateUnavailableError):
            YFinanceFxRateProvider(market).get_rate("USD", "EUR")
    provider = YFinanceFxRateProvider(FakeMarket(failure=MarketDataUnavailableError("synthetic")))
    p = portfolio()
    result = PortfolioValuationService(provider).evaluate(p, {"TEST": price()}, now=NOW)
    assert not result.complete and result.positions[0].state is ValuationState.MISSING
    assert result.data_errors and "FxRateUnavailableError" in result.data_errors[0]
    assert p.reconstruct().position("TEST").cost == D(90)
    provider._market_provider = FakeMarket(history((1.25,)))
    result = PortfolioValuationService(provider).evaluate(p, {"TEST": price()}, now=NOW,
                                                         max_age=timedelta(days=4))
    assert result.complete and result.total_market_value == D(88)
    assert not result.data_errors


def test_service_fetches_one_fx_for_shared_currency():
    class Provider:
        calls = 0
        def get_rate(self, source, base):
            self.calls += 1
            return fx(source, base)

    p = portfolio()
    p = p.record(replace(p.versions[0].trade, instrument=Instrument("SECOND")))
    provider = Provider()
    result = PortfolioValuationService(provider).evaluate(
        p, {"TEST": price(), "SECOND": price(ticker="SECOND")}, now=NOW,
    )
    assert result.total_market_value == D(187)
    assert provider.calls == 1
