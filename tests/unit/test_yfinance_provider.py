import pandas as pd
import pytest

from bolsa.app.ports.errors import (
    CurrentPriceUnavailableError,
    InstrumentNotFoundError,
    MarketDataFormatError,
    MarketDataUnavailableError,
)
from bolsa.domain.instruments import AssetType, Instrument
from bolsa.infrastructure.exchange_data.yfinance_provider import (
    YFinanceMarketDataProvider,
)


class _MetadataTicker:
    def __init__(self, currency: str, *, price: float | None = None):
        self._currency = currency
        self.fast_info = {"last_price": price}

    def get_info(self):
        return {
            "quoteType": "EQUITY",
            "currency": self._currency,
            "longName": "Test Instrument",
            "fullExchangeName": "Test Exchange",
        }


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


@pytest.mark.parametrize(
    ("raw_currency", "currency", "factor"),
    [
        ("GBp", "GBP", 0.01),
        ("GBX", "GBP", 0.01),
        ("ZAc", "ZAR", 0.01),
        ("ILA", "ILS", 0.01),
        ("USD", "USD", 1.0),
    ],
)
def test_quote_currency_conventions(
    raw_currency: str,
    currency: str,
    factor: float,
) -> None:
    convention = YFinanceMarketDataProvider._quote_convention_from_currency(
        raw_currency,
        ticker="TEST",
    )

    assert convention.raw_currency == raw_currency
    assert convention.currency == currency
    assert convention.price_factor == factor


@pytest.mark.parametrize("raw_currency", ["gbp", "US$", "PENCE", "", 123])
def test_quote_currency_rejects_unrecognised_conventions(raw_currency) -> None:
    with pytest.raises(MarketDataFormatError, match="moeda|Moeda"):
        YFinanceMarketDataProvider._quote_convention_from_currency(
            raw_currency,
            ticker="TEST",
        )


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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    provider = YFinanceMarketDataProvider()
    result = provider.get_instrument_details(Instrument("AMD"))

    assert result.ticker == "AMD"
    assert result.name == "Advanced Micro Devices, Inc."
    assert result.exchange == "NASDAQGS"
    assert result.currency == "USD"
    assert result.asset_type is AssetType.STOCK


def test_get_instrument_details_normalises_gbp_subunit(monkeypatch) -> None:
    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: _MetadataTicker("GBp"),
    )

    provider = YFinanceMarketDataProvider()
    result = provider.get_instrument_details(Instrument("VOD.L"))

    assert result.currency == "GBP"


def test_get_instrument_details_rejects_unknown_ticker(monkeypatch) -> None:
    class FakeTicker:
        def get_info(self):
            return {}

    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.download",
        fail_download,
    )

    with pytest.raises(MarketDataUnavailableError, match="histórico"):
        YFinanceMarketDataProvider().get_historical_data(
            Instrument("AAPL")
        )


def test_get_historical_data_rejects_malformed_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.download",
        lambda **_kwargs: ["unexpected"],
    )

    with pytest.raises(MarketDataFormatError, match="formato esperado"):
        YFinanceMarketDataProvider().get_historical_data(
            Instrument("AAPL")
        )


def test_get_historical_data_scales_price_columns_but_not_volume(monkeypatch) -> None:
    raw = pd.DataFrame(
        {
            "Open": [12300.0],
            "High": [12450.0],
            "Low": [12200.0],
            "Close": [12345.0],
            "Adj Close": [12340.0],
            "Volume": [987654],
        },
        index=pd.DatetimeIndex(["2026-01-02"]),
    )

    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.download",
        lambda **_kwargs: raw,
    )
    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: _MetadataTicker("GBp"),
    )

    result = YFinanceMarketDataProvider().get_historical_data(
        Instrument("VOD.L")
    )

    assert float(result.iloc[0]["Open"]) == pytest.approx(123.00)
    assert float(result.iloc[0]["High"]) == pytest.approx(124.50)
    assert float(result.iloc[0]["Low"]) == pytest.approx(122.00)
    assert float(result.iloc[0]["Close"]) == pytest.approx(123.45)
    assert float(result.iloc[0]["Adj Close"]) == pytest.approx(123.40)
    assert int(result.iloc[0]["Volume"]) == 987654


def test_get_current_price_uses_fast_info(monkeypatch) -> None:
    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: _MetadataTicker("USD", price=123.45),
    )

    price = YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))

    assert price == 123.45


def test_get_current_price_scales_gbp_subunit(monkeypatch) -> None:
    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: _MetadataTicker("GBp", price=12345.0),
    )

    price = YFinanceMarketDataProvider().get_current_price(Instrument("VOD.L"))

    assert price == pytest.approx(123.45)


def test_quote_convention_is_cached_per_ticker(monkeypatch) -> None:
    class FakeTicker:
        calls = 0
        fast_info = {"last_price": 12345.0}

        def get_info(self):
            type(self).calls += 1
            return {
                "quoteType": "EQUITY",
                "currency": "GBp",
            }

    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    provider = YFinanceMarketDataProvider()

    assert provider.get_current_price(Instrument("VOD.L")) == pytest.approx(123.45)
    assert provider.get_current_price(Instrument("VOD.L")) == pytest.approx(123.45)
    assert FakeTicker.calls == 1


def test_get_current_price_uses_history_fallback(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"last_price": None}

        def history(self, **_kwargs):
            return pd.DataFrame({"Close": [101.0, 102.5]})

        def get_info(self):
            return {"quoteType": "EQUITY", "currency": "USD"}

    monkeypatch.setattr(
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
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
        "bolsa.infrastructure.exchange_data.yfinance_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    with pytest.raises(MarketDataFormatError, match="Close"):
        YFinanceMarketDataProvider().get_current_price(Instrument("AAPL"))
