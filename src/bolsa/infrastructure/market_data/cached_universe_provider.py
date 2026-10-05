from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path

from bolsa.app.ports.errors import (
    UnsupportedUniverseError,
    UniverseFormatError,
    UniverseSourceUnavailableError,
)
from bolsa.app.ports.universe import (
    UniverseLoadResult,
    UniverseLoadStatus,
    UniverseProvider,
)
from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.universes import Universe

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _CachedSnapshot:
    universe: Universe
    saved_at: datetime


class CachedUniverseProvider:
    """Cache local em JSON para universos de mercado.

    Cache fresca é reutilizada diretamente. Cache expirada até ao limite
    stale_ttl pode ser usada como fallback explícito se a fonte estiver
    indisponível ou deixar de ser interpretável.
    """

    def __init__(
        self,
        source: UniverseProvider,
        cache_dir: Path,
        *,
        ttl: timedelta = timedelta(hours=24),
        stale_ttl: timedelta = timedelta(days=7),
    ) -> None:
        if stale_ttl < ttl:
            raise ValueError("stale_ttl não pode ser inferior a ttl.")

        self._source = source
        self._cache_dir = cache_dir
        self._ttl = ttl
        self._stale_ttl = stale_ttl
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def supported_universes(self) -> tuple[str, ...]:
        return self._source.supported_universes()

    def get_universe(self, code: str) -> UniverseLoadResult:
        key = code.strip().lower()
        if key not in self.supported_universes():
            raise UnsupportedUniverseError(code)

        snapshot = self._load_cache(key)
        now = datetime.now(timezone.utc)

        if snapshot is not None:
            age = now - snapshot.saved_at
            if age <= self._ttl:
                return UniverseLoadResult(
                    universe=snapshot.universe,
                    status=UniverseLoadStatus.FRESH_CACHE,
                    cached_at=snapshot.saved_at,
                )
        else:
            age = None

        try:
            result = self._source.get_universe(key)
        except (UniverseSourceUnavailableError, UniverseFormatError) as exc:
            if (
                snapshot is not None
                and age is not None
                and age <= self._stale_ttl
            ):
                if isinstance(exc, UniverseSourceUnavailableError):
                    warning = (
                        "Fonte temporariamente indisponível; "
                        "a usar dados em cache."
                    )
                else:
                    warning = (
                        "A fonte respondeu, mas o formato não pôde ser "
                        "interpretado; a usar dados em cache."
                    )

                logger.warning(
                    "A usar cache expirada do universo %s (%s).",
                    key,
                    exc,
                )
                return UniverseLoadResult(
                    universe=snapshot.universe,
                    status=UniverseLoadStatus.STALE_CACHE,
                    cached_at=snapshot.saved_at,
                    warning=warning,
                )
            raise

        self._save_cache(result.universe)
        return result

    def _cache_path(self, code: str) -> Path:
        return self._cache_dir / f"{code}.json"

    def _load_cache(self, code: str) -> _CachedSnapshot | None:
        path = self._cache_path(code)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            saved_at = datetime.fromisoformat(payload["saved_at"])
            if saved_at.tzinfo is None:
                saved_at = saved_at.replace(tzinfo=timezone.utc)

            instruments = tuple(
                Instrument(
                    ticker=item["ticker"],
                    name=item.get("name"),
                    market=item.get("market"),
                    currency=item.get("currency"),
                    asset_type=AssetType(item.get("asset_type", "stock")),
                )
                for item in payload["instruments"]
            )

            retrieved_at = datetime.fromisoformat(payload["retrieved_at"])
            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)

            universe = Universe(
                code=payload["code"],
                name=payload["name"],
                instruments=instruments,
                source=payload["source"],
                retrieved_at=retrieved_at,
            )
            return _CachedSnapshot(universe=universe, saved_at=saved_at)
        except Exception:
            logger.warning(
                "Cache do universo %s inválida; a fonte será consultada.",
                code,
                exc_info=True,
            )
            return None

    def _save_cache(self, universe: Universe) -> None:
        payload = {
            "code": universe.code,
            "name": universe.name,
            "source": universe.source,
            "retrieved_at": universe.retrieved_at.isoformat(),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "instruments": [
                {
                    "ticker": item.ticker,
                    "name": item.name,
                    "market": item.market,
                    "currency": item.currency,
                    "asset_type": item.asset_type.value,
                }
                for item in universe.instruments
            ],
        }

        path = self._cache_path(universe.code)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
