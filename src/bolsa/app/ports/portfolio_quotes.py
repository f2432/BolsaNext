from typing import Protocol

from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.valuation import PriceQuote


class PortfolioQuoteProvider(Protocol):
    def get_quote(self, instrument: Instrument) -> PriceQuote: ...
