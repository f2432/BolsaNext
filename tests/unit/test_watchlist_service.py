import pytest

from bolsa.app.ports.errors import (
    CurrentPriceUnavailableError,
    InstrumentNotFoundError,
)
from bolsa.app.services import MarketService
from bolsa.app.services.watchlist_service import WatchlistService
from bolsa.domain.instruments import Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistState


class FakeProvider:
    def get_historical_data(self, instrument, **kwargs):
        raise NotImplementedError

    def get_current_price(self, instrument):
        return 123.45

    def get_instrument_details(self, instrument):
        return Instrument(
            ticker=instrument.ticker,
            name="Advanced Micro Devices, Inc.",
            market="NASDAQ",
            currency="USD",
        )


class MissingInstrumentProvider(FakeProvider):
    def get_instrument_details(self, instrument):
        raise InstrumentNotFoundError(instrument.ticker)


class MissingPriceProvider(FakeProvider):
    def get_current_price(self, instrument):
        raise CurrentPriceUnavailableError(instrument.ticker)


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
    assert service.price_warnings == ()


def test_watchlist_service_keeps_rows_when_one_price_fails() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(MissingPriceProvider()),
    )
    service.add_ticker("aapl")

    rows = service.rows(refresh_prices=True)

    assert len(rows) == 1
    assert rows[0].ticker == "AAPL"
    assert rows[0].price is None
    assert len(service.price_warnings) == 1
    assert "cotação atual" in service.price_warnings[0]


def test_watchlist_service_enriches_manual_ticker() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(FakeProvider()),
    )

    instrument = service.add_ticker_enriched("amd")
    rows = service.rows()

    assert instrument.ticker == "AMD"
    assert instrument.name == "Advanced Micro Devices, Inc."
    assert rows[0].market == "NASDAQ"
    assert rows[0].currency == "USD"


def test_invalid_manual_ticker_is_not_added() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(MissingInstrumentProvider()),
    )

    with pytest.raises(InstrumentNotFoundError):
        service.add_ticker_enriched("INVALID")

    assert service.rows() == []


def test_watchlist_service_refreshes_missing_metadata() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(FakeProvider()),
    )
    service.add_ticker("AMD")

    rows = service.refresh_metadata()

    assert rows[0].name == "Advanced Micro Devices, Inc."
    assert rows[0].market == "NASDAQ"
    assert rows[0].currency == "USD"
    assert service.metadata_warnings == ()


def test_metadata_refresh_keeps_other_rows_when_one_ticker_fails() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(MissingInstrumentProvider()),
    )
    service.add_ticker("INVALID")

    rows = service.refresh_metadata()

    assert rows[0].ticker == "INVALID"
    assert len(service.metadata_warnings) == 1
    assert "INVALID" in service.metadata_warnings[0]


class FakeRepository:
    def __init__(self):
        self.saved = []

    def load(self, name):
        return None

    def save(self, watchlist):
        self.saved.append(
            [
                (
                    item.instrument.ticker,
                    item.instrument.name,
                    item.state,
                )
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
    service.set_state("AAPL", WatchlistState.CANDIDATE)
    service.remove_ticker("AAPL")

    assert len(repository.saved) == 3
    assert repository.saved[0][0][0] == "AAPL"
    assert repository.saved[1][0][2] == WatchlistState.CANDIDATE
    assert repository.saved[2] == []


def test_metadata_enrichment_is_persisted() -> None:
    repository = FakeRepository()
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(FakeProvider()),
        repository=repository,
    )

    service.add_ticker_enriched("AMD")

    assert repository.saved[-1][0][1] == "Advanced Micro Devices, Inc."
