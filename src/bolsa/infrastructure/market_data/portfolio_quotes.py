from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext

from bolsa.app.ports.errors import (
    MarketDataError,
    MarketDataFormatError,
    CurrentPriceUnavailableError,
)
from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.money import FINANCIAL_CONTEXT, currency
from bolsa.domain.portfolio.valuation import FxRate, Quote, market_decimal


def last_close(frame):
    if frame.empty or "Close" not in frame:
        raise CurrentPriceUnavailableError("portfolio")
    usable = frame["Close"].dropna()
    if usable.empty:
        raise CurrentPriceUnavailableError("portfolio")
    stamp = usable.index[-1]
    # Existing daily history normalizes timestamps to UTC. A daily bar provides
    # a session date, not an intraday execution timestamp.
    try:
        day = stamp.date()
        value = market_decimal(usable.iloc[-1])
    except Exception as exc:
        raise MarketDataFormatError("Fecho/data de sessão inválidos.") from exc
    return value, day


class YFinancePortfolioQuoteProvider:
    def __init__(self, market_data):
        self.market_data = market_data

    def get_quote(self, instrument):
        details = self.market_data.get_instrument_details(instrument)
        value, day = last_close(self.market_data.get_historical_data(details, period="5d"))
        return Quote(details.ticker, details.currency, value, day, "yfinance daily Close")


class YFinanceFxRateProvider:
    def __init__(self, market_data):
        self.market_data = market_data

    def get_rate(self, original_currency, base_currency, *, on: date | None = None):
        original, base = currency(original_currency), currency(base_currency)
        if original == base:
            return FxRate(original, base, Decimal(1), on or datetime.now(timezone.utc), "identity")
        inverted = (original, base) == ("USD", "EUR")
        ticker = "EURUSD=X" if inverted else f"{original}{base}=X"
        instrument = Instrument(ticker)
        try:
            if on is None:
                frame = self.market_data.get_historical_data(instrument, period="5d")
            else:
                # yfinance end is exclusive. Only prior/target sessions may be used.
                frame = self.market_data.get_historical_data(
                    instrument, start=on - timedelta(days=7), end=on + timedelta(days=1)
                )
            if on is not None:
                frame = frame.loc[[stamp.date() <= on for stamp in frame.index]]
            quote, day = last_close(frame)
            with localcontext(FINANCIAL_CONTEXT):
                rate = Decimal(1) / quote if inverted else quote
            return FxRate(
                original, base, rate, day, f"yfinance {ticker}" + (" inverted" if inverted else "")
            )
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataFormatError("Taxa FX inválida.") from exc
