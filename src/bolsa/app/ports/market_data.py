from __future__ import annotations

from datetime import date
from typing import Protocol

import pandas as pd

from bolsa.domain.instruments import Instrument


class MarketDataProvider(Protocol):
    """Contrato da Application para dados de mercado."""

    def get_historical_data(
        self,
        instrument: Instrument,
        *,
        period: str = "1y",
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """Devolve OHLCV normalizado e ordenado cronologicamente."""

    def get_current_price(self, instrument: Instrument) -> float | None:
        """Devolve o preço mais recente disponível, ou None."""

    def get_instrument_details(self, instrument: Instrument) -> Instrument:
        """Devolve o instrumento enriquecido com metadados disponíveis."""
