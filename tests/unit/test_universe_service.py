from datetime import datetime, timezone

from bolsa.app.services import UniverseService
from bolsa.domain.instruments import Instrument
from bolsa.domain.universes import Universe


class FakeUniverseProvider:
    def supported_universes(self):
        return ("sp500", "nasdaq100")

    def get_universe(self, code):
        return Universe(
            code=code,
            name="Teste",
            instruments=(Instrument("AAPL"),),
            source="https://example.test",
            retrieved_at=datetime.now(timezone.utc),
        )


def test_universe_service_lists_and_loads_universes() -> None:
    service = UniverseService(FakeUniverseProvider())

    assert service.available() == ("sp500", "nasdaq100")
    universe = service.load("sp500")
    assert universe.tickers == ("AAPL",)
