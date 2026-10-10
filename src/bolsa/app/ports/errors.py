from __future__ import annotations


class ExternalDataError(RuntimeError):
    """Erro base previsível ao obter ou interpretar dados externos."""


class MarketDataError(ExternalDataError):
    """Erro base previsível exposto pelo contrato de market data."""


class InstrumentNotFoundError(MarketDataError):
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"Não foi possível encontrar o ticker {ticker} no fornecedor de dados."
        )


class MarketDataUnavailableError(MarketDataError):
    """O fornecedor de dados não respondeu ou não pôde ser consultado."""


class CurrentPriceUnavailableError(MarketDataError):
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"Não existe uma cotação atual utilizável para {ticker} neste momento."
        )


class MarketDataFormatError(MarketDataError):
    """O fornecedor respondeu, mas os dados não têm o formato esperado."""


class UniverseError(ExternalDataError):
    """Erro base previsível associado a uma fonte de universos."""


class UnsupportedUniverseError(UniverseError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Universo não suportado: {code}")


class UniverseSourceUnavailableError(UniverseError):
    """A fonte do universo não respondeu ou não pôde ser consultada."""


class UniverseFormatError(UniverseError):
    """A fonte respondeu, mas o conteúdo do universo não pôde ser interpretado."""
