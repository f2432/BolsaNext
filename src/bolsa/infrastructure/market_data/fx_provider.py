from datetime import date, datetime
from decimal import Decimal, localcontext
import math
from numbers import Real

import pandas as pd

from bolsa.app.ports.errors import MarketDataError
from bolsa.app.ports.fx import FxRateFormatError, FxRateUnavailableError
from bolsa.app.ports.market_data import MarketDataProvider
from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.valuation import FxQuote, quote_decimal
from bolsa.domain.portfolio.values import FINANCIAL_CONTEXT, PortfolioError, currency_code


def approximate_market_decimal(value) -> Decimal:
    """Explicit float-to-Decimal boundary; cannot restore lost provider precision."""
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise FxRateFormatError("Market quote is not numeric")
    try:
        if not math.isfinite(value):
            raise PortfolioError("Non-finite market quote")
        return quote_decimal(Decimal(str(value)))
    except (PortfolioError, ArithmeticError, ValueError) as exc:
        raise FxRateFormatError("Invalid approximate market quote") from exc


class YFinanceFxRateProvider:
    """Daily session Close via the Yahoo MarketData port; no real network in tests."""

    def __init__(self, market_provider: MarketDataProvider):
        self._market_provider = market_provider

    def get_rate(self, source_currency: str, base_currency: str) -> FxQuote:
        try:
            original = currency_code(source_currency)
            base = currency_code(base_currency)
        except PortfolioError as exc:
            raise FxRateFormatError(str(exc)) from exc
        if original == base:
            return FxQuote(original, base, Decimal("1"), None, "identity")
        # EURUSD is USD per EUR. For USD -> EUR, invert explicitly.
        inverted = (original, base) == ("USD", "EUR")
        pair = "EURUSD=X" if inverted else f"{original}{base}=X"
        instrument = Instrument(pair, asset_type=AssetType.OTHER)
        try:
            history = self._market_provider.get_historical_data(instrument, period="1mo", interval="1d")
        except MarketDataError as exc:
            raise FxRateUnavailableError(f"FX source unavailable for {pair}") from exc
        try:
            if not isinstance(history, pd.DataFrame):
                raise FxRateFormatError("FX history is not a DataFrame")
            if history.empty:
                raise FxRateUnavailableError(f"No FX sessions for {pair}")
            if "Close" not in history.columns or not history.index.is_unique:
                raise FxRateFormatError("Invalid FX history structure")
            history = history.sort_index()
            row = history.iloc[-1]
            # float(...) is not used here; preserve explicit provider-to-text conversion.
            quote = approximate_market_decimal(row["Close"])
            stamp = history.index[-1]
            if isinstance(stamp, datetime):
                session_date = stamp.date()
            elif type(stamp) is date:
                session_date = stamp
            else:
                raise FxRateFormatError("FX history lacks a reliable session date")
            with localcontext(FINANCIAL_CONTEXT):
                rate = Decimal("1") / quote if inverted else quote
            return FxQuote(original, base, rate, session_date, "Yahoo daily Close", inverted, pair)
        except (FxRateUnavailableError, FxRateFormatError):
            raise
        except (PortfolioError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
            raise FxRateFormatError(f"Invalid FX data for {pair}") from exc
