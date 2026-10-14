from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
import pytest

from bolsa.app.portfolio_forms import transaction_from_form, form_values, decimal_text
from bolsa.app.ports.errors import MarketDataFormatError, MarketDataUnavailableError
from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.values import MoneyComponent, SignedMoneyComponent, PortfolioError
from bolsa.infrastructure.market_data.portfolio_quotes import YFinancePortfolioQuoteProvider


@pytest.mark.parametrize("text", ["NaN", "Infinity", "1,000.00", "text"])
def test_invalid_decimal_forms(text):
    with pytest.raises(PortfolioError):
        decimal_text(text)


@pytest.mark.parametrize("event", [
    Dividend(Instrument("SYN", currency="EUR"), MoneyComponent(Decimal("1"), "EUR"),
             MoneyComponent(Decimal("0"), "EUR"), MoneyComponent(Decimal("2"), "EUR"),
             SignedMoneyComponent(Decimal("-1"), "EUR"), date(2026, 1, 1)),
    Split(Instrument("SYN", currency="EUR"), Decimal("2"), "Synthetic split", date(2026, 1, 1)),
])
def test_event_form_roundtrip(event):
    assert transaction_from_form(form_values(event), previous=event) == event


class Market:
    def __init__(self, frame):
        self.frame = frame
    def get_instrument_details(self, instrument):
        return replace(instrument, currency="USD")
    def get_historical_data(self, *args, **kwargs):
        return self.frame


def test_quote_current_currency_and_session_precision():
    instrument = Instrument("SYN", currency="EUR")
    frame = pd.DataFrame({"Close": [12.1, 11.2]}, index=pd.to_datetime(["2026-01-02", "2026-01-01"]))
    quote = YFinancePortfolioQuoteProvider(Market(frame)).get_quote(instrument)
    assert quote.currency == "USD" and instrument.currency == "EUR"
    assert quote.price == Decimal("12.1") and type(quote.quoted_at) is date
    assert quote.quoted_at == date(2026, 1, 2)


@pytest.mark.parametrize("frame,error", [
    (pd.DataFrame(), MarketDataUnavailableError),
    (pd.DataFrame({"Open": [1]}, index=pd.to_datetime(["2026-01-01"])), MarketDataFormatError),
    (pd.DataFrame({"Close": [1]}, index=["2026-01-01"]), MarketDataFormatError),
    (pd.DataFrame({"Close": [float("nan")]}, index=pd.to_datetime(["2026-01-01"])), MarketDataFormatError),
    (pd.DataFrame({"Close": [True]}, index=pd.to_datetime(["2026-01-01"])), MarketDataFormatError),
])
def test_quote_invalid_sources(frame, error):
    with pytest.raises(error):
        YFinancePortfolioQuoteProvider(Market(frame)).get_quote(Instrument("SYN"))


def test_future_session_not_given_current_timestamp():
    from bolsa.domain.portfolio.valuation import quote_freshness, ValuationState
    from datetime import timedelta
    frame = pd.DataFrame({"Close": [1]}, index=pd.to_datetime(["2099-01-01"]))
    quote = YFinancePortfolioQuoteProvider(Market(frame)).get_quote(Instrument("SYN"))
    state, _ = quote_freshness(quote.quoted_at, datetime(2026, 1, 1, tzinfo=timezone.utc), timedelta(hours=72))
    assert state is ValuationState.UNRELIABLE_TIME
