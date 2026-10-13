from typing import Protocol

from bolsa.app.ports.errors import ExternalDataError
from bolsa.domain.portfolio.valuation import FxQuote


class FxRateError(ExternalDataError):
    """FX data could not be obtained or normalized."""


class FxRateUnavailableError(FxRateError):
    pass


class FxRateFormatError(FxRateError):
    pass


class FxRateProvider(Protocol):
    def get_rate(self, source_currency: str, base_currency: str) -> FxQuote: ...
