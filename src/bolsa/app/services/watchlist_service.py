from __future__ import annotations

from dataclasses import dataclass

from bolsa.app.services.market_service import MarketService
from bolsa.domain.instruments import Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistState


@dataclass(frozen=True, slots=True)
class WatchlistRow:
    ticker: str
    name: str | None
    state: WatchlistState
    price: float | None


class WatchlistService:
    def __init__(self, watchlist: Watchlist, market_service: MarketService) -> None:
        self._watchlist = watchlist
        self._market_service = market_service

    @property
    def name(self) -> str:
        return self._watchlist.name

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

    def remove_ticker(self, ticker: str) -> None:
        self._watchlist.remove(ticker)

    def set_state(self, ticker: str, state: WatchlistState) -> None:
        self._watchlist.set_state(ticker, state)

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
                    state=item.state,
                    price=price,
                )
            )
        return rows
