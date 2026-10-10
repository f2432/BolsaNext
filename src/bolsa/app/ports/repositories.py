from __future__ import annotations

from typing import Protocol

from bolsa.domain.watchlist import Watchlist


class WatchlistRepository(Protocol):
    """Contrato de persistência usado pelo WatchlistService."""

    def load(self, name: str) -> Watchlist | None:
        ...

    def save(self, watchlist: Watchlist) -> None:
        ...
