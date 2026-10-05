from bolsa.app.services import MarketService
from bolsa.app.services.watchlist_service import WatchlistService
from bolsa.domain.watchlist import Watchlist


class FakeProvider:
    def get_historical_data(self, instrument, **kwargs):
        raise NotImplementedError

    def get_current_price(self, instrument):
        return 123.45


def test_watchlist_service_can_refresh_prices() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(FakeProvider()),
    )
    service.add_ticker("aapl")

    rows = service.rows(refresh_prices=True)

    assert len(rows) == 1
    assert rows[0].ticker == "AAPL"
    assert rows[0].price == 123.45


class FakeRepository:
    def __init__(self):
        self.saved = []

    def load(self, name):
        return None

    def save(self, watchlist):
        self.saved.append(
            [
                (item.instrument.ticker, item.state)
                for item in watchlist.items
            ]
        )


def test_watchlist_service_persists_mutations() -> None:
    repository = FakeRepository()
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(FakeProvider()),
        repository=repository,
    )

    service.add_ticker("AAPL")
    service.set_state("AAPL", __import__(
        "bolsa.domain.watchlist",
        fromlist=["WatchlistState"],
    ).WatchlistState.CANDIDATE)
    service.remove_ticker("AAPL")

    assert len(repository.saved) == 3
    assert repository.saved[0][0][0] == "AAPL"
    assert repository.saved[1][0][1].value == "candidate"
    assert repository.saved[2] == []
