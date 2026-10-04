from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bolsa.domain.instruments import Instrument


@dataclass(frozen=True, slots=True)
class Universe:
    code: str
    name: str
    instruments: tuple[Instrument, ...]
    source: str
    retrieved_at: datetime

    def __post_init__(self) -> None:
        code = self.code.strip().lower()
        name = self.name.strip()
        source = self.source.strip()

        if not code:
            raise ValueError("O código do universo não pode estar vazio.")
        if not name:
            raise ValueError("O nome do universo não pode estar vazio.")
        if not source:
            raise ValueError("A fonte do universo não pode estar vazia.")

        object.__setattr__(self, "code", code)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "source", source)

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(instrument.ticker for instrument in self.instruments)
