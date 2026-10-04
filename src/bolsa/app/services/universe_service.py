from __future__ import annotations

from bolsa.domain.universes import Universe
from bolsa.infrastructure.market_data.universe_provider import UniverseProvider


class UniverseService:
    def __init__(self, provider: UniverseProvider) -> None:
        self._provider = provider

    def available(self) -> tuple[str, ...]:
        return self._provider.supported_universes()

    def load(self, code: str) -> Universe:
        return self._provider.get_universe(code)
