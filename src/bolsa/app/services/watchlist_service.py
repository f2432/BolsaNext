from __future__ import annotations

from dataclasses import dataclass

from bolsa.app.ports.errors import MarketDataError
from bolsa.app.ports.repositories import WatchlistRepository
from bolsa.app.services.market_service import MarketService
from bolsa.domain.instruments import Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistState


@dataclass(frozen=True, slots=True)
class WatchlistRow:
    ticker: str
    name: str | None
    market: str | None
    currency: str | None
    state: WatchlistState
    price: float | None


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
        self._metadata_warnings: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return self._watchlist.name

    @property
    def metadata_warnings(self) -> tuple[str, ...]:
        return self._metadata_warnings

    def add_ticker(
        self,
        ticker: str,
        *,
        name: str | None = None,
        market: str | None = None,
        currency: str | None = None,
    ) -> None:
        instrument = Instrument(
            ticker=ticker,
            name=name,
            market=market,
            currency=currency,
        )
        self._watchlist.add(instrument)
        self._persist()

    def add_ticker_enriched(self, ticker: str) -> Instrument:
        base = Instrument(ticker=ticker)

        if self._watchlist.get(base.ticker) is not None:
            raise ValueError(f"{base.ticker} já existe na watchlist.")

        instrument = self._market_service.instrument_details(base)
        self._watchlist.add(instrument)
        self._persist()
        return instrument

    def refresh_metadata(self) -> list[WatchlistRow]:
        changed = False
        warnings: list[str] = []

        for item in self._watchlist.items:
            if (
                item.instrument.name
                and item.instrument.market
                and item.instrument.currency
            ):
                continue

            try:
                enriched = self._market_service.instrument_details(item.instrument)
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
        self._watchlist.remove(ticker)
        self._persist()

    def set_state(self, ticker: str, state: WatchlistState) -> None:
        self._watchlist.set_state(ticker, state)
        self._persist()

    def rows(self, *, refresh_prices: bool = False) -> list[WatchlistRow]:
        rows: list[WatchlistRow] = []
        for item in self._watchlist.items:
            price = (
                self._market_service.current_price(item.instrument)
                if refresh_prices
                else None
            )
            rows.append(
                WatchlistRow(
                    ticker=item.instrument.ticker,
                    name=item.instrument.name,
                    market=item.instrument.market,
                    currency=item.instrument.currency,
                    state=item.state,
                    price=price,
                )
            )
        return rows

    def _persist(self) -> None:
        if self._repository is not None:
            self._repository.save(self._watchlist)
