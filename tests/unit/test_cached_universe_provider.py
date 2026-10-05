from datetime import datetime, timedelta, timezone
import json

import pytest

from bolsa.app.ports.errors import (
    UniverseFormatError,
    UniverseSourceUnavailableError,
)
from bolsa.app.ports.universe import UniverseLoadResult, UniverseLoadStatus
from bolsa.domain.instruments import Instrument
from bolsa.domain.universes import Universe
from bolsa.infrastructure.market_data.cached_universe_provider import (
    CachedUniverseProvider,
)


class FakeUniverseProvider:
    def __init__(self):
        self.calls = 0
        self.error: Exception | None = None

    def supported_universes(self):
        return ("sp500",)

    def get_universe(self, code):
        self.calls += 1
        if self.error is not None:
            raise self.error

        universe = Universe(
            code=code,
            name="S&P 500",
            instruments=(Instrument("AAPL", name="Apple Inc.", currency="USD"),),
            source="https://example.test",
            retrieved_at=datetime.now(timezone.utc),
        )
        return UniverseLoadResult(
            universe=universe,
            status=UniverseLoadStatus.LIVE,
        )


def _set_cache_age(path, age: timedelta) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["saved_at"] = (datetime.now(timezone.utc) - age).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_universe_cache_reuses_fresh_data(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(hours=24),
    )

    first = provider.get_universe("sp500")
    second = provider.get_universe("sp500")

    assert first.status is UniverseLoadStatus.LIVE
    assert second.status is UniverseLoadStatus.FRESH_CACHE
    assert first.universe.tickers == ("AAPL",)
    assert second.universe.tickers == ("AAPL",)
    assert second.cached_at is not None
    assert source.calls == 1


def test_universe_cache_refreshes_when_expired(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(seconds=0),
    )

    provider.get_universe("sp500")
    provider.get_universe("sp500")

    assert source.calls == 2


def test_stale_cache_falls_back_when_source_unavailable(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(hours=24),
        stale_ttl=timedelta(days=7),
    )

    provider.get_universe("sp500")
    _set_cache_age(tmp_path / "sp500.json", timedelta(days=2))
    source.error = UniverseSourceUnavailableError("offline")

    result = provider.get_universe("sp500")

    assert result.status is UniverseLoadStatus.STALE_CACHE
    assert result.universe.tickers == ("AAPL",)
    assert result.cached_at is not None
    assert "temporariamente indisponível" in (result.warning or "")


def test_stale_cache_falls_back_when_source_format_changes(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(hours=24),
        stale_ttl=timedelta(days=7),
    )

    provider.get_universe("sp500")
    _set_cache_age(tmp_path / "sp500.json", timedelta(days=2))
    source.error = UniverseFormatError("changed")

    result = provider.get_universe("sp500")

    assert result.status is UniverseLoadStatus.STALE_CACHE
    assert "formato" in (result.warning or "")


def test_stale_cache_older_than_limit_does_not_hide_source_failure(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(
        source,
        tmp_path,
        ttl=timedelta(hours=24),
        stale_ttl=timedelta(days=7),
    )

    provider.get_universe("sp500")
    _set_cache_age(tmp_path / "sp500.json", timedelta(days=8))
    source.error = UniverseSourceUnavailableError("offline")

    with pytest.raises(UniverseSourceUnavailableError):
        provider.get_universe("sp500")


def test_stale_ttl_cannot_be_shorter_than_fresh_ttl(tmp_path) -> None:
    with pytest.raises(ValueError):
        CachedUniverseProvider(
            FakeUniverseProvider(),
            tmp_path,
            ttl=timedelta(days=2),
            stale_ttl=timedelta(days=1),
        )
