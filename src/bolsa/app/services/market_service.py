from __future__ import annotations

from datetime import date

import pandas as pd

from bolsa.app.ports.market_data import MarketDataProvider
from bolsa.domain.instruments import Instrument


class MarketService:
    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def history(
        self,
        instrument: Instrument,
        *,
        period: str = "1y",
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        if start is not None and end is not None and start >= end:
            raise ValueError("A data inicial deve ser anterior à data final.")

        return self._provider.get_historical_data(
            instrument,
            period=period,
            interval=interval,
            start=start,
            end=end,
        )

    def current_price(self, instrument: Instrument) -> float | None:
        return self._provider.get_current_price(instrument)

    def instrument_details(self, instrument: Instrument) -> Instrument:
        return self._provider.get_instrument_details(instrument)
