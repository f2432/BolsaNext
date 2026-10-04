from __future__ import annotations

from typing import Protocol

from bolsa.domain.universes import Universe


class UniverseProvider(Protocol):
    def supported_universes(self) -> tuple[str, ...]:
        """Devolve os códigos dos universos disponíveis."""

    def get_universe(self, code: str) -> Universe:
        """Obtém e normaliza um universo de instrumentos."""
