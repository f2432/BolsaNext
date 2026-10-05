import pandas as pd

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
    assert float(result.loc[pd.Timestamp("2026-01-02 00:00:00"), "Close"]) == 11.0


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
