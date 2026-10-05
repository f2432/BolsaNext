import pandas as pd
import pytest

from bolsa.app.ports.errors import (
    CurrentPriceUnavailableError,
    InstrumentNotFoundError,
    MarketDataFormatError,
    MarketDataUnavailableError,
)
from bolsa.domain.instruments import AssetType, Instrument
from bolsa.infrastructure.market_data.yfinance_provider import (
    YFinanceMarketDataProvider,
)


def test_normalise_history_orders_deduplicates_and_adds_columns() -> None:
    index = pd.DatetimeIndex(
        ["2026-01-03", "2026-01-02", "2026-01-02"],
        tz="Europe/Lisbon",
    )
    data = pd.DataFrame(
        {
            "Open": [11, 10, 10.5],
            "High": [12, 11, 11.5],
            "Low": [10, 9, 9.5],
            "Close": [11.5, 10.5, 11.0],
            "Volume": [120, 100, 110],
        },
        index=index,
    )

    result = YFinanceMarketDataProvider._normalise_history(data, "TEST")

    assert result.index.is_monotonic_increasing
    assert result.index.tz is None
    assert len(result) == 2
    assert list(result.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
    ]
    assert result["Adj Close"].isna().all()
    assert float(result.loc[pd.Timestamp("2026-01-02 00:00:00"), "Close"]) == 11.0


def test_normalise_history_converts_timezone_to_utc_naive() -> None:
    data = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.DatetimeIndex(["2026-01-02 09:30"], tz="America/New_York"),
    )

    result = YFinanceMarketDataProvider._normalise_history(data, "TEST")

    assert result.index.tz is None
    assert result.index[0] == pd.Timestamp("2026-01-02 14:30:00")


def test_normalise_empty_history_keeps_canonical_schema() -> None:
    result = YFinanceMarketDataProvider._normalise_history(
        pd.DataFrame(),
        "TEST",
    )

    assert result.empty
    assert result.index.name == "Date"
    assert list(result.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
    ]


def test_get_instrument_details_maps_yahoo_metadata(monkeypatch) -> None:
    class FakeTicker:
        def get_info(self):
            return {
                "longName": "Advanced Micro Devices, Inc.",
                "fullExchangeName": "NasdaqGS",
                "currency": "USD",
                "quoteType": "EQUITY",
            }

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    provider = YFinanceMarketDataProvider()
    result = provider.get_instrument_details(Instrument("AMD"))

    assert result.ticker == "AMD"
    assert result.name == "Advanced Micro Devices, Inc."
    assert result.market == "NASDAQGS"
    assert result.currency == "USD"
    assert result.asset_type is AssetType.STOCK


def test_get_instrument_details_rejects_unknown_ticker(monkeypatch) -> None:
    class FakeTicker:
        def get_info(self):
            return {}

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(InstrumentNotFoundError, match="INVALID"):
        YFinanceMarketDataProvider().get_instrument_details(
            Instrument("INVALID")
        )


def test_get_instrument_details_distinguishes_provider_failure(monkeypatch) -> None:
    class FakeTicker:
        def get_info(self):
            raise ConnectionError("offline")

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(MarketDataUnavailableError, match="Tenta novamente"):
        YFinanceMarketDataProvider().get_instrument_details(
            Instrument("AAPL")
        )


def test_get_instrument_details_rejects_malformed_metadata(monkeypatch) -> None:
    class FakeTicker:
        def get_info(self):
            return ["unexpected"]

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(MarketDataFormatError, match="formato esperado"):
        YFinanceMarketDataProvider().get_instrument_details(
            Instrument("AAPL")
        )


def test_get_historical_data_wraps_provider_failure(monkeypatch) -> None:
    def fail_download(**_kwargs):
        raise ConnectionError("offline")

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.download",
        fail_download,
    )

    with pytest.raises(MarketDataUnavailableError, match="histórico"):
        YFinanceMarketDataProvider().get_historical_data(
            Instrument("AAPL")
        )


def test_get_historical_data_rejects_malformed_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.download",
        lambda **_kwargs: ["unexpected"],
    )

    with pytest.raises(MarketDataFormatError, match="formato esperado"):
        YFinanceMarketDataProvider().get_historical_data(
            Instrument("AAPL")
        )


def test_get_current_price_uses_fast_info(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": 123.45}

        def history(self, **_kwargs):
            raise AssertionError("history não devia ser consultado")

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    price = YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))

    assert price == 123.45


def test_get_current_price_uses_history_fallback(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": None}

        def history(self, **_kwargs):
            return pd.DataFrame({"Close": [101.0, 102.5]})

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    price = YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))

    assert price == 102.5


def test_get_current_price_distinguishes_no_quote(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": None}

        def history(self, **_kwargs):
            return pd.DataFrame()

        def get_info(self):
            return {"quoteType": "EQUITY", "currency": "USD"}

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(CurrentPriceUnavailableError, match="cotação atual"):
        YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))


def test_get_current_price_distinguishes_unknown_ticker(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": None}

        def history(self, **_kwargs):
            return pd.DataFrame()

        def get_info(self):
            return {}

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(InstrumentNotFoundError, match="INVALID"):
        YFinanceMarketDataProvider().get_current_price(Instrument("INVALID"))


def test_get_current_price_distinguishes_provider_failure(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": None}

        def history(self, **_kwargs):
            raise ConnectionError("offline")

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(MarketDataUnavailableError, match="Tenta novamente"):
        YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))


def test_get_current_price_rejects_malformed_response(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": None}

        def history(self, **_kwargs):
            return pd.DataFrame({"Open": [100.0]})

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(MarketDataFormatError, match="Close"):
        YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))
