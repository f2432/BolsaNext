from __future__ import annotations

from bolsa.app.ports.universe import UniverseLoadResult, UniverseProvider


class UniverseService:
    def __init__(self, provider: UniverseProvider) -> None:
        self._provider = provider

    def available(self) -> tuple[str, ...]:
        return self._provider.supported_universes()

    def load(self, code: str) -> UniverseLoadResult:
        return self._provider.get_universe(code)
