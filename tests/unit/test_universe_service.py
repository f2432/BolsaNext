from datetime import datetime, timezone

from bolsa.app.ports.universe import UniverseLoadResult, UniverseLoadStatus
from bolsa.app.services import UniverseService
from bolsa.domain.instruments import Instrument
from bolsa.domain.universes import Universe


class FakeUniverseProvider:
    def supported_universes(self):
        return ("sp500", "nasdaq100")

    def get_universe(self, code):
        universe = Universe(
            code=code,
            name="Teste",
            instruments=(Instrument("AAPL"),),
            source="https://example.test",
            retrieved_at=datetime.now(timezone.utc),
        )
        return UniverseLoadResult(
            universe=universe,
            status=UniverseLoadStatus.LIVE,
        )


def test_universe_service_lists_and_loads_universes() -> None:
    service = UniverseService(FakeUniverseProvider())

    assert service.available() == ("sp500", "nasdaq100")
    result = service.load("sp500")

    assert result.status is UniverseLoadStatus.LIVE
    assert result.universe.tickers == ("AAPL",)
