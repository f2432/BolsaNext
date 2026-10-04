from __future__ import annotations

from datetime import datetime, timezone
import logging

import pandas as pd

from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.universes import Universe

logger = logging.getLogger(__name__)


class WikipediaUniverseProvider:
    """Provider inicial de constituintes de índices através da Wikipedia.

    Nesta fase são suportados S&P 500 e NASDAQ 100. Os símbolos são
    normalizados para a convenção usada pelo Yahoo Finance, substituindo
    pontos por hífen em tickers norte-americanos (ex.: BRK.B -> BRK-B).
    """

    _SOURCES = {
        "sp500": {
            "name": "S&P 500",
            "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            "symbol_columns": ("Symbol", "Ticker"),
            "name_columns": ("Security", "Company"),
            "market": "US",
            "currency": "USD",
        },
        "nasdaq100": {
            "name": "NASDAQ 100",
            "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
            "symbol_columns": ("Ticker", "Symbol"),
            "name_columns": ("Company", "Security"),
            "market": "NASDAQ",
            "currency": "USD",
        },
    }

    def supported_universes(self) -> tuple[str, ...]:
        return tuple(self._SOURCES.keys())

    def get_universe(self, code: str) -> Universe:
        key = code.strip().lower()
        if key not in self._SOURCES:
            raise ValueError(f"Universo não suportado: {code}")

        config = self._SOURCES[key]
        logger.info("A obter universo %s", config["name"])
        tables = self._read_tables(config["url"])
        table = self._find_constituents_table(
            tables,
            symbol_columns=config["symbol_columns"],
            name_columns=config["name_columns"],
        )
        instruments = self._table_to_instruments(
            table,
            symbol_columns=config["symbol_columns"],
            name_columns=config["name_columns"],
            market=config["market"],
            currency=config["currency"],
        )

        return Universe(
            code=key,
            name=config["name"],
            instruments=tuple(instruments),
            source=config["url"],
            retrieved_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _read_tables(url: str) -> list[pd.DataFrame]:
        return pd.read_html(url)

    @staticmethod
    def _find_constituents_table(
        tables: list[pd.DataFrame],
        *,
        symbol_columns: tuple[str, ...],
        name_columns: tuple[str, ...],
    ) -> pd.DataFrame:
        for table in tables:
            columns = {str(column).strip() for column in table.columns}
            has_symbol = any(column in columns for column in symbol_columns)
            has_name = any(column in columns for column in name_columns)
            if has_symbol and has_name:
                return table

        raise ValueError("Não foi encontrada uma tabela de constituintes compatível.")

    @staticmethod
    def _table_to_instruments(
        table: pd.DataFrame,
        *,
        symbol_columns: tuple[str, ...],
        name_columns: tuple[str, ...],
        market: str,
        currency: str,
    ) -> list[Instrument]:
        symbol_column = next(
            column for column in symbol_columns if column in table.columns
        )
        name_column = next(
            column for column in name_columns if column in table.columns
        )

        instruments: list[Instrument] = []
        seen: set[str] = set()

        for _, row in table.iterrows():
            raw_symbol = str(row[symbol_column]).strip()
            if not raw_symbol or raw_symbol.lower() == "nan":
                continue

            ticker = raw_symbol.upper().replace(".", "-")
            if ticker in seen:
                continue

            raw_name = row[name_column]
            name = None if pd.isna(raw_name) else str(raw_name).strip()

            instruments.append(
                Instrument(
                    ticker=ticker,
                    name=name,
                    market=market,
                    currency=currency,
                    asset_type=AssetType.STOCK,
                )
            )
            seen.add(ticker)

        if not instruments:
            raise ValueError("O universo obtido não contém instrumentos válidos.")

        return instruments
