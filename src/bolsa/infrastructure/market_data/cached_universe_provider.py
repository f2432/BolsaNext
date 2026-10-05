from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path

from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.universes import Universe
from bolsa.app.ports.universe import UniverseProvider

logger = logging.getLogger(__name__)


class CachedUniverseProvider:
    """Cache local em JSON para universos de mercado.

    O cache é apenas uma otimização. Quando está ausente, expirado ou
    corrompido, o provider de origem volta a ser consultado.
    """

    def __init__(
        self,
        source: UniverseProvider,
        cache_dir: Path,
        *,
        ttl: timedelta = timedelta(hours=24),
    ) -> None:
        self._source = source
        self._cache_dir = cache_dir
        self._ttl = ttl
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def supported_universes(self) -> tuple[str, ...]:
        return self._source.supported_universes()

    def get_universe(self, code: str) -> Universe:
        key = code.strip().lower()
        if key not in self.supported_universes():
            raise ValueError(f"Universo não suportado: {code}")

        cached = self._load_cache(key)
        if cached is not None:
            return cached

        universe = self._source.get_universe(key)
        self._save_cache(universe)
        return universe

    def _cache_path(self, code: str) -> Path:
        return self._cache_dir / f"{code}.json"

    def _load_cache(self, code: str) -> Universe | None:
        path = self._cache_path(code)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            saved_at = datetime.fromisoformat(payload["saved_at"])
            if saved_at.tzinfo is None:
                saved_at = saved_at.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) - saved_at > self._ttl:
                return None

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

            return Universe(
                code=payload["code"],
                name=payload["name"],
                instruments=instruments,
                source=payload["source"],
                retrieved_at=retrieved_at,
            )
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
