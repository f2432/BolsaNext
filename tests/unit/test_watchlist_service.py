from threading import Event, Thread

import pytest

from bolsa.app.ports.errors import (
    CurrentPriceUnavailableError,
    InstrumentNotFoundError,
    MarketDataUnavailableError,
)
from bolsa.app.services import MarketService
from bolsa.app.services.watchlist_service import WatchlistService
from bolsa.domain.instruments import AssetType, Instrument
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
            exchange="NASDAQ",
            currency="USD",
            asset_type=AssetType.STOCK,
        )


class MissingInstrumentProvider(FakeProvider):
    def get_instrument_details(self, instrument):
        raise InstrumentNotFoundError(instrument.ticker)


class UnavailableMetadataProvider(FakeProvider):
    def get_instrument_details(self, instrument):
        raise MarketDataUnavailableError("offline")


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
    assert rows[0].exchange == "NASDAQ"
    assert rows[0].currency == "USD"


def test_invalid_manual_ticker_is_not_added() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(MissingInstrumentProvider()),
    )

    with pytest.raises(InstrumentNotFoundError):
        service.add_ticker_enriched("INVALID")

    assert service.rows() == []


def test_universe_instrument_prefers_yahoo_metadata() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(FakeProvider()),
    )

    result = service.add_universe_instrument(
        Instrument(
            "AMD",
            name="Nome provisório",
            exchange="US",
            currency="EUR",
            asset_type=AssetType.OTHER,
        )
    )

    rows = service.rows()
    assert result.provisional is False
    assert result.instrument.name == "Advanced Micro Devices, Inc."
    assert result.instrument.exchange == "NASDAQ"
    assert result.instrument.currency == "USD"
    assert rows[0].exchange == "NASDAQ"
    assert rows[0].currency == "USD"


def test_universe_instrument_falls_back_to_safe_provisional_metadata() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(UnavailableMetadataProvider()),
    )

    result = service.add_universe_instrument(
        Instrument(
            "AMD",
            name="Nome do universo",
            exchange="US",
            currency="EUR",
            asset_type=AssetType.STOCK,
        )
    )

    assert result.provisional is True
    assert result.warning == "offline"
    assert result.instrument.name == "Nome do universo"
    assert result.instrument.exchange is None
    assert result.instrument.currency is None
    assert result.instrument.asset_type is AssetType.OTHER


def test_universe_instrument_not_found_is_not_added() -> None:
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(MissingInstrumentProvider()),
    )

    with pytest.raises(InstrumentNotFoundError):
        service.add_universe_instrument(
            Instrument("INVALID", name="Provisório", asset_type=AssetType.OTHER)
        )

    assert service.rows() == []


def test_refresh_metadata_always_returns_to_primary_source() -> None:
    class CountingProvider(FakeProvider):
        def __init__(self):
            self.calls = 0

        def get_instrument_details(self, instrument):
            self.calls += 1
            return super().get_instrument_details(instrument)

    provider = CountingProvider()
    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(provider),
    )
    service.add_ticker(
        "AMD",
        name="Nome antigo",
        exchange="US",
        currency="EUR",
    )

    rows = service.refresh_metadata()

    assert provider.calls == 1
    assert rows[0].name == "Advanced Micro Devices, Inc."
    assert rows[0].exchange == "NASDAQ"
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


def test_watchlist_service_serializes_concurrent_access() -> None:
    provider_started = Event()
    release_provider = Event()
    remove_attempted = Event()
    remove_finished = Event()
    errors: list[BaseException] = []

    class BlockingProvider(FakeProvider):
        def get_instrument_details(self, instrument):
            provider_started.set()
            if not release_provider.wait(timeout=2):
                raise TimeoutError("provider test timeout")
            return Instrument(
                ticker=instrument.ticker,
                name="Apple Inc.",
                exchange="NASDAQ",
                currency="USD",
            )

    service = WatchlistService(
        Watchlist("Principal"),
        MarketService(BlockingProvider()),
    )
    service.add_ticker("AAPL")

    def refresh_metadata() -> None:
        try:
            service.refresh_metadata()
        except BaseException as exc:
            errors.append(exc)

    def remove_ticker() -> None:
        try:
            remove_attempted.set()
            service.remove_ticker("AAPL")
            remove_finished.set()
        except BaseException as exc:
            errors.append(exc)

    refresh_thread = Thread(target=refresh_metadata)
    remove_thread = Thread(target=remove_ticker)

    refresh_thread.start()
    assert provider_started.wait(timeout=1)

    remove_thread.start()
    assert remove_attempted.wait(timeout=1)
    assert not remove_finished.wait(timeout=0.1)

    release_provider.set()
    refresh_thread.join(timeout=2)
    remove_thread.join(timeout=2)

    assert not refresh_thread.is_alive()
    assert not remove_thread.is_alive()
    assert errors == []
    assert remove_finished.is_set()
    assert service.rows() == []
