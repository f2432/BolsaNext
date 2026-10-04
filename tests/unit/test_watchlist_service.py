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
