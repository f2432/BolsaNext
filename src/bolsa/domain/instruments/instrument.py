from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssetType(StrEnum):
    STOCK = "stock"
    ETF = "etf"
    INDEX = "index"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Instrument:
    ticker: str
    name: str | None = None
    market: str | None = None
    currency: str | None = None
    asset_type: AssetType = AssetType.STOCK

    def __post_init__(self) -> None:
        ticker = self.ticker.strip().upper()
        if not ticker:
            raise ValueError("O ticker não pode estar vazio.")
        if any(char.isspace() for char in ticker):
            raise ValueError("O ticker não pode conter espaços.")

        object.__setattr__(self, "ticker", ticker)

        if self.currency is not None:
            currency = self.currency.strip().upper()
            if len(currency) != 3 or not currency.isalpha():
                raise ValueError("A moeda deve usar um código ISO de 3 letras.")
            object.__setattr__(self, "currency", currency)

        if self.market is not None:
            object.__setattr__(self, "market", self.market.strip().upper() or None)

        if self.name is not None:
            object.__setattr__(self, "name", self.name.strip() or None)
