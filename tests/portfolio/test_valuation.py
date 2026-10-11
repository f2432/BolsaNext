from dataclasses import replace
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.models import Ledger, Portfolio, TransactionVersion
from bolsa.domain.portfolio.money import LedgerError, Money
from bolsa.domain.portfolio.valuation import Quote, FxRate, market_decimal, value_portfolio
from bolsa.infrastructure.market_data.portfolio_quotes import YFinanceFxRateProvider

NOW = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize("historical_currency", ["USD", "EUR", None])
def test_historical_and_current_fx_separate(trade, historical_currency):
    tx = replace(
        trade(quantity="1"),
        instrument=Instrument("TEST", currency=historical_currency),
        price=Money(Decimal(100), "USD", Decimal(".9")),
    )
    ledger = Ledger(Portfolio("S", "EUR"), (TransactionVersion(tx),))
    q = Quote("TEST", "USD", Decimal(110), NOW, "synthetic")
    r = FxRate("USD", "EUR", Decimal(".85"), NOW, "synthetic")
    valued = value_portfolio(ledger, {"TEST": q}, {"USD": r}, now=NOW)
    assert valued.total == Decimal("93.50") and valued.unrealized_pnl == Decimal("3.50")
    assert tx.price.fx_rate == Decimal(".9")
    assert tx.instrument.currency == historical_currency
    partial = value_portfolio(ledger, {"TEST": q}, {}, now=NOW)
    assert partial.total is partial.unrealized_pnl is None and partial.known_subtotal == 0


def test_current_asset_type_controls_valuation_and_sector_risk(trade):
    from bolsa.domain.portfolio.policy import InvestmentPolicy, evaluate_risk

    ledger = Ledger(Portfolio("S", "EUR"), (TransactionVersion(trade()),))
    quote = Quote("TEST", "EUR", Decimal(110), NOW, "synthetic", asset_type="etf")
    valued = value_portfolio(ledger, {"TEST": quote}, {}, now=NOW)
    risk = evaluate_risk(
        valued, policy=InvestmentPolicy(max_sector_weight=Decimal(".5")),
        sectors={"TEST": "Technology"},
    )
    assert valued.total == 1100
    assert risk.sector_weights == (("não determinado", Decimal(1)),)
    assert risk.alerts[0].state == "not_evaluable"
    unsupported = value_portfolio(
        ledger, {"TEST": replace(quote, asset_type="index")}, {}, now=NOW
    )
    assert unsupported.total is None and unsupported.positions[0].reason


def test_invalid_current_metadata_is_unavailable_without_mutating_ledger(
    service, repository, trade,
):
    from bolsa.app.ports.errors import MarketDataFormatError
    from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService
    from bolsa.infrastructure.market_data.portfolio_quotes import YFinancePortfolioQuoteProvider

    class Market:
        def get_instrument_details(self, instrument):
            return replace(instrument, currency=None)

        def get_historical_data(self, instrument, **kwargs):
            return pd.DataFrame({"Close": [110.0]}, index=pd.to_datetime([NOW], utc=True))

    provider = YFinancePortfolioQuoteProvider(Market())
    with pytest.raises(MarketDataFormatError):
        provider.get_quote(Instrument("TEST"))
    uid = service.create("S", "EUR").portfolio.portfolio_uid
    before = service.record(uid, trade(), expected_revision=0)
    result = PortfolioValuationService(repository, provider, None).evaluate(uid, now=NOW)
    assert result.total is None and result.positions[0].reason
    assert repository.load(uid) == before


def test_quote_adapter_uses_fresh_currency_and_type():
    from bolsa.domain.instruments import AssetType
    from bolsa.infrastructure.market_data.portfolio_quotes import YFinancePortfolioQuoteProvider

    class Market:
        def get_instrument_details(self, instrument):
            return replace(instrument, currency="USD", asset_type=AssetType.ETF)

        def get_historical_data(self, instrument, **kwargs):
            assert instrument.currency == "USD" and instrument.asset_type == AssetType.ETF
            return pd.DataFrame({"Close": [110.0]}, index=pd.to_datetime([NOW], utc=True))

    historical = Instrument("TEST", currency="EUR")
    quote = YFinancePortfolioQuoteProvider(Market()).get_quote(historical)
    assert quote.currency == "USD" and quote.asset_type == AssetType.ETF
    assert historical.currency == "EUR" and historical.asset_type == AssetType.STOCK


def test_stale_future_calendar_and_identity(trade):
    ledger = Ledger(Portfolio("S", "EUR"), (TransactionVersion(trade()),))
    q = Quote("TEST", "EUR", Decimal(110), date(2026, 1, 1), "synthetic")
    assert value_portfolio(ledger, {"TEST": q}, {}, now=NOW).total is None
    valued = value_portfolio(
        ledger, {"TEST": q}, {}, now=NOW, last_sessions={"TEST": date(2026, 1, 1)}
    )
    assert valued.total == 1100  # reliable session calendar allows a holiday gap
    assert (
        value_portfolio(
            ledger, {"TEST": replace(q, as_of=NOW + timedelta(seconds=1))}, {}, now=NOW
        ).total
        is None
    )
    assert (
        value_portfolio(
            ledger, {"TEST": replace(q, as_of=NOW - timedelta(hours=72))}, {}, now=NOW
        ).total
        == 1100
    )
    assert (
        value_portfolio(
            ledger, {"TEST": replace(q, as_of=NOW - timedelta(hours=73))}, {}, now=NOW
        ).total
        is None
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, -1, True])
def test_market_boundary_invalid(value):
    with pytest.raises(LedgerError):
        market_decimal(value)


def test_market_float_conversion_is_explicit():
    assert market_decimal(0.1) == Decimal(".1")
    with pytest.raises(LedgerError):
        Quote("TEST", "EUR", 0.1, NOW, "synthetic")


def test_fx_provider_direction_historical_and_no_lookahead():
    class Market:
        calls = []

        def get_historical_data(self, instrument, **kwargs):
            self.calls.append((instrument.ticker, kwargs))
            return pd.DataFrame(
                {"Close": [1.25, 2.0]}, index=pd.to_datetime(["2026-01-02", "2026-01-06"], utc=True)
            )

    market = Market()
    provider = YFinanceFxRateProvider(market)
    r = provider.get_rate("USD", "EUR", on=date(2026, 1, 5))
    assert r.rate == Decimal(".8") and r.as_of == date(2026, 1, 2)
    assert market.calls[0][0] == "EURUSD=X"
    assert provider.get_rate("EUR", "USD", on=date(2026, 1, 5)).rate == Decimal("1.25")
    count = len(market.calls)
    assert provider.get_rate("EUR", "EUR").rate == 1 and len(market.calls) == count


def test_provider_failure_never_mutates_history(service, repository, trade):
    from bolsa.app.ports.errors import MarketDataUnavailableError
    from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService

    uid = service.create("S", "EUR").portfolio.portfolio_uid
    before = service.record(uid, trade(), expected_revision=0)

    class Missing:
        def get_quote(self, instrument):
            raise MarketDataUnavailableError("synthetic missing")

    result = PortfolioValuationService(repository, Missing(), None).evaluate(uid, now=NOW)
    assert result.total is None and result.positions[0].reason
    assert repository.load(uid) == before


def test_date_only_fallback_is_conservative_unless_calendar_available(trade):
    ledger = Ledger(Portfolio("S", "EUR"), (TransactionVersion(trade()),))
    friday = Quote("TEST", "EUR", Decimal(110), date(2026, 1, 2), "synthetic daily close")
    assert value_portfolio(ledger, {"TEST": friday}, {}, now=NOW).total is None
    assert (
        value_portfolio(
            ledger, {"TEST": friday}, {}, now=NOW, last_sessions={"TEST": date(2026, 1, 2)}
        ).total
        == 1100
    )
