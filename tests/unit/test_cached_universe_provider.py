from datetime import datetime, timedelta, timezone

from bolsa.domain.instruments import Instrument
from bolsa.domain.universes import Universe
from bolsa.infrastructure.market_data.cached_universe_provider import (
    CachedUniverseProvider,
)


class FakeUniverseProvider:
    def __init__(self):
        self.calls = 0

    def supported_universes(self):
        return ("sp500",)

    def get_universe(self, code):
        self.calls += 1
        return Universe(
            code=code,
            name="S&P 500",
            instruments=(Instrument("AAPL", name="Apple Inc.", currency="USD"),),
            source="https://example.test",
            retrieved_at=datetime.now(timezone.utc),
        )


def test_universe_cache_reuses_fresh_data(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(hours=24),
    )

    first = provider.get_universe("sp500")
    second = provider.get_universe("sp500")

    assert first.tickers == ("AAPL",)
    assert second.tickers == ("AAPL",)
    assert source.calls == 1


def test_universe_cache_refreshes_when_expired(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(seconds=-1),
    )

    provider.get_universe("sp500")
    provider.get_universe("sp500")

    assert source.calls == 2
