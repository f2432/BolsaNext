from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from bolsa.domain.instruments import Instrument


class WatchlistState(StrEnum):
    IDEA = "idea"
    ANALYSING = "analysing"
    CANDIDATE = "candidate"
    REJECTED = "rejected"
    REVIEW = "review"


@dataclass(slots=True)
class WatchlistItem:
    instrument: Instrument
    state: WatchlistState = WatchlistState.IDEA
    notes: str = ""


@dataclass(slots=True)
class Watchlist:
    name: str
    items: list[WatchlistItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("O nome da watchlist não pode estar vazio.")

    def add(
        self,
        instrument: Instrument,
        *,
        state: WatchlistState = WatchlistState.IDEA,
        notes: str = "",
    ) -> WatchlistItem:
        if self.get(instrument.ticker) is not None:
            raise ValueError(f"{instrument.ticker} já existe na watchlist.")

        item = WatchlistItem(
            instrument=instrument,
            state=state,
            notes=notes.strip(),
        )
        self.items.append(item)
        return item

    def remove(self, ticker: str) -> None:
        ticker = ticker.strip().upper()
        item = self.get(ticker)
        if item is None:
            raise KeyError(ticker)
        self.items.remove(item)

    def get(self, ticker: str) -> WatchlistItem | None:
        ticker = ticker.strip().upper()
        return next(
            (item for item in self.items if item.instrument.ticker == ticker),
            None,
        )

    def set_state(self, ticker: str, state: WatchlistState) -> None:
        item = self.get(ticker)
        if item is None:
            raise KeyError(ticker)
        item.state = state
