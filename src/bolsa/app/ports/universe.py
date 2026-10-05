from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from bolsa.domain.universes import Universe


class UniverseLoadStatus(StrEnum):
    LIVE = "live"
    FRESH_CACHE = "fresh_cache"
    STALE_CACHE = "stale_cache"


@dataclass(frozen=True, slots=True)
class UniverseLoadResult:
    universe: Universe
    status: UniverseLoadStatus
    cached_at: datetime | None = None
    warning: str | None = None


class UniverseProvider(Protocol):
    """Contrato da Application para fontes de universos."""

    def supported_universes(self) -> tuple[str, ...]:
        """Devolve os códigos dos universos disponíveis."""

    def get_universe(self, code: str) -> UniverseLoadResult:
        """Obtém um universo e informa a proveniência/frescura do resultado."""
