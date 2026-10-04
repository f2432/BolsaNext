from datetime import date

import pandas as pd
import pytest

from bolsa.app.services import MarketService
from bolsa.domain.instruments import Instrument


class FakeProvider:
    def get_historical_data(
        self,
        instrument,
        *,
        period="1y",
        interval="1d",
        start=None,
        end=None,
    ):
        return pd.DataFrame(
            {"Close": [100.0]},
            index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        )

    def get_current_price(self, instrument):
        return 123.45


def test_market_service_delegates_to_provider() -> None:
    service = MarketService(FakeProvider())
    instrument = Instrument("AAPL")

    history = service.history(instrument)
    price = service.current_price(instrument)

    assert float(history["Close"].iloc[0]) == 100.0
    assert price == 123.45


def test_market_service_rejects_invalid_date_range() -> None:
    service = MarketService(FakeProvider())
    instrument = Instrument("AAPL")

    with pytest.raises(ValueError):
        service.history(
            instrument,
            start=date(2026, 2, 1),
            end=date(2026, 1, 1),
        )
