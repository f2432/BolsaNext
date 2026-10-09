from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock

from bolsa.app.ports.errors import (
    InstrumentNotFoundError,
    MarketDataError,
)
from bolsa.app.ports.repositories import WatchlistRepository
from bolsa.app.services.market_service import MarketService
from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistState


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    price: float
    obtained_at: datetime


@dataclass(frozen=True, slots=True)
class WatchlistRow:
    ticker: str
    name: str | None
    exchange: str | None
    currency: str | None
    state: WatchlistState
    price: float | None
    price_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UniverseInstrumentAddResult:
    instrument: Instrument
    provisional: bool
    warning: str | None = None


class WatchlistService:
    def __init__(
        self,
        watchlist: Watchlist,
        market_service: MarketService,
        repository: WatchlistRepository | None = None,
    ) -> None:
        self._watchlist = watchlist
        self._market_service = market_service
        self._repository = repository
        self._lock = RLock()
        self._price_cache: dict[str, PriceSnapshot] = {}
        self._metadata_warnings: tuple[str, ...] = ()
        self._price_warnings: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        with self._lock:
            return self._watchlist.name

    @property
    def metadata_warnings(self) -> tuple[str, ...]:
        with self._lock:
            return self._metadata_warnings

    @property
    def price_warnings(self) -> tuple[str, ...]:
        with self._lock:
            return self._price_warnings

    def add_ticker(
        self,
        ticker: str,
        *,
        name: str | None = None,
        exchange: str | None = None,
        currency: str | None = None,
    ) -> None:
        with self._lock:
            instrument = Instrument(
                ticker=ticker,
                name=name,
                exchange=exchange,
                currency=currency,
            )
            self._watchlist.add(instrument)
            self._persist()

    def add_ticker_enriched(self, ticker: str) -> Instrument:
        with self._lock:
            base = Instrument(ticker=ticker)

            if self._watchlist.get(base.ticker) is not None:
                raise ValueError(f"{base.ticker} já existe na watchlist.")

            instrument = self._market_service.instrument_details(base)
            self._watchlist.add(instrument)
            self._persist()
            return instrument

    def add_universe_instrument(
        self,
        instrument: Instrument,
    ) -> UniverseInstrumentAddResult:
        with self._lock:
            provisional = Instrument(
                ticker=instrument.ticker,
                name=instrument.name,
                exchange=None,
                currency=None,
                asset_type=AssetType.OTHER,
            )

            if self._watchlist.get(provisional.ticker) is not None:
                raise ValueError(
                    f"{provisional.ticker} já existe na watchlist."
                )

            try:
                chosen = self._market_service.instrument_details(provisional)
            except InstrumentNotFoundError:
                raise
            except MarketDataError as exc:
                chosen = provisional
                result = UniverseInstrumentAddResult(
                    instrument=chosen,
                    provisional=True,
                    warning=str(exc),
                )
            else:
                result = UniverseInstrumentAddResult(
                    instrument=chosen,
                    provisional=False,
                )

            self._watchlist.add(chosen)
            self._persist()
            return result

    def refresh_metadata(self) -> list[WatchlistRow]:
        with self._lock:
            changed = False
            warnings: list[str] = []

            for item in self._watchlist.items:
                try:
                    enriched = self._market_service.instrument_details(
                        item.instrument
                    )
                except MarketDataError as exc:
                    warnings.append(f"{item.instrument.ticker}: {exc}")
                    continue

                if enriched != item.instrument:
                    item.instrument = enriched
                    changed = True

            self._metadata_warnings = tuple(warnings)

            if changed:
                self._persist()

            return self.rows()

    def remove_ticker(self, ticker: str) -> None:
        with self._lock:
            canonical_ticker = self._watchlist.get(ticker)
            self._watchlist.remove(ticker)
            self._persist()
            if canonical_ticker is not None:
                self._price_cache.pop(canonical_ticker.instrument.ticker, None)

    def set_state(self, ticker: str, state: WatchlistState) -> None:
        with self._lock:
            self._watchlist.set_state(ticker, state)
            self._persist()

    def rows(self, *, refresh_prices: bool = False) -> list[WatchlistRow]:
        with self._lock:
            warnings: list[str] = []
            rows: list[WatchlistRow] = []

            for item in self._watchlist.items:
                ticker = item.instrument.ticker
                snapshot = self._price_cache.get(ticker)

                if refresh_prices:
                    try:
                        price = self._market_service.current_price(
                            item.instrument
                        )
                        snapshot = PriceSnapshot(
                            price=price,
                            obtained_at=datetime.now(timezone.utc),
                        )
                        self._price_cache[ticker] = snapshot
                    except MarketDataError as exc:
                        warnings.append(f"{item.instrument.ticker}: {exc}")

                rows.append(
                    WatchlistRow(
                        ticker=item.instrument.ticker,
                        name=item.instrument.name,
                        exchange=item.instrument.exchange,
                        currency=item.instrument.currency,
                        state=item.state,
                        price=snapshot.price if snapshot is not None else None,
                        price_updated_at=(
                            snapshot.obtained_at if snapshot is not None else None
                        ),
                    )
                )

            if refresh_prices:
                self._price_warnings = tuple(warnings)

            return rows

    def _persist(self) -> None:
        if self._repository is not None:
            self._repository.save(self._watchlist)
