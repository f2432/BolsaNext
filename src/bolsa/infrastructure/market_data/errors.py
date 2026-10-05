from __future__ import annotations


class MarketDataError(RuntimeError):
    """Erro base para falhas previsíveis na infraestrutura de market data."""


class InstrumentNotFoundError(MarketDataError):
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"Não foi possível encontrar o ticker {ticker} no fornecedor de dados."
        )


class MarketDataUnavailableError(MarketDataError):
    """O fornecedor de dados não respondeu ou não pôde ser consultado."""
