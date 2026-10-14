"""Current daily snapshots; reviewed adaptation of feature 7d3e4f7."""
from datetime import date, datetime

import pandas as pd

from bolsa.app.ports.errors import MarketDataFormatError, MarketDataUnavailableError
from bolsa.app.ports.fx import FxRateFormatError
from bolsa.domain.portfolio.valuation import PriceQuote
from bolsa.domain.portfolio.values import PortfolioError
from bolsa.infrastructure.market_data.fx_provider import approximate_market_decimal


class YFinancePortfolioQuoteProvider:
    def __init__(self, market_provider):
        self._provider = market_provider

    def get_quote(self, instrument):
        # Current metadata is authoritative for current quote denomination;
        # it never overwrites the historical execution snapshot in the ledger.
        details = self._provider.get_instrument_details(instrument)
        history = self._provider.get_historical_data(details, period="1mo", interval="1d")
        if not isinstance(history, pd.DataFrame):
            raise MarketDataFormatError("Histórico de cotação inválido.")
        if history.empty:
            raise MarketDataUnavailableError("Sem sessões de cotação.")
        if "Close" not in history or not history.index.is_unique:
            raise MarketDataFormatError("Fecho ou datas inválidos.")
        history = history.sort_index()
        stamp = history.index[-1]
        if isinstance(stamp, datetime):
            stamp = stamp.date()
        if type(stamp) is not date:
            raise MarketDataFormatError("Sem data de sessão fiável.")
        try:
            return PriceQuote(details.ticker, details.currency,
                              approximate_market_decimal(history.iloc[-1]["Close"]), stamp,
                              "Yahoo daily Close (aproximado)")
        except (FxRateFormatError, PortfolioError, TypeError, ValueError) as exc:
            raise MarketDataFormatError("Preço/moeda de cotação atual inválido.") from exc
