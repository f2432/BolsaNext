from datetime import date
from typing import Protocol

from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.valuation import FxRate, Quote


class FxRateProvider(Protocol):
    def get_rate(
        self, original_currency: str, base_currency: str, *, on: date | None = None
    ) -> FxRate: ...


class PortfolioQuoteProvider(Protocol):
    def get_quote(self, instrument: Instrument) -> Quote: ...
