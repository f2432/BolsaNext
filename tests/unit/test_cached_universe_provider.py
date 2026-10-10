from datetime import datetime, timedelta, timezone
import json
import os

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
            instruments=(Instrument("AAPL", name="Apple Inc."),),
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



def test_old_cache_format_is_ignored_and_rebuilt(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(source, tmp_path)

    provider.get_universe("sp500")
    path = tmp_path / "sp500.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["format_version"] = 1
    payload["instruments"][0]["market"] = "US"
    payload["instruments"][0]["currency"] = "USD"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = provider.get_universe("sp500")

    assert source.calls == 2
    assert result.status is UniverseLoadStatus.LIVE
    assert result.universe.instruments[0].exchange is None
    assert result.universe.instruments[0].currency is None


def test_atomic_save_replaces_cache_without_temporary_files(tmp_path) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(source, tmp_path)
    provider.get_universe("sp500")
    cache_path = tmp_path / "sp500.json"

    provider._save_cache(source.get_universe("sp500").universe)

    assert json.loads(cache_path.read_text(encoding="utf-8"))["format_version"] == 2
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_save_preserves_previous_cache_when_replace_fails(tmp_path, monkeypatch) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(source, tmp_path)
    provider.get_universe("sp500")
    cache_path = tmp_path / "sp500.json"
    original = cache_path.read_bytes()

    def fail_replace(_src, _dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        provider._save_cache(source.get_universe("sp500").universe)

    assert cache_path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [cache_path]
    assert provider._load_cache("sp500") is not None


def test_atomic_save_preserves_previous_cache_when_write_fails(tmp_path, monkeypatch) -> None:
    source = FakeUniverseProvider()
    provider = CachedUniverseProvider(source, tmp_path)
    provider.get_universe("sp500")
    cache_path = tmp_path / "sp500.json"
    original = cache_path.read_bytes()

    import bolsa.infrastructure.market_data.cached_universe_provider as module

    def fail_dump(*_args, **_kwargs):
        raise OSError("simulated serialization failure")

    monkeypatch.setattr(module.json, "dumps", fail_dump)
    with pytest.raises(OSError, match="simulated serialization failure"):
        provider._save_cache(source.get_universe("sp500").universe)

    assert cache_path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [cache_path]
