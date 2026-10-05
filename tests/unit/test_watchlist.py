import pytest

from bolsa.domain.instruments import Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistState


def test_watchlist_adds_and_updates_item() -> None:
    watchlist = Watchlist("Principal")
    watchlist.add(Instrument("aapl"))

    watchlist.set_state("AAPL", WatchlistState.ANALYSING)

    item = watchlist.get("aapl")
    assert item is not None
    assert item.instrument.ticker == "AAPL"
    assert item.state == WatchlistState.ANALYSING


def test_watchlist_rejects_duplicate_ticker() -> None:
    watchlist = Watchlist("Principal")
    watchlist.add(Instrument("AAPL"))

    with pytest.raises(ValueError):
        watchlist.add(Instrument("aapl"))


def test_watchlist_normalises_serialized_state_value() -> None:
    watchlist = Watchlist("Principal")
    watchlist.add(Instrument("AMD"))

    watchlist.set_state("AMD", "candidate")

    item = watchlist.get("AMD")
    assert item is not None
    assert item.state is WatchlistState.CANDIDATE
