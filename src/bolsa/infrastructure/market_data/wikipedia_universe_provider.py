from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
import logging
from urllib.request import Request, urlopen

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

    _USER_AGENT = (
        "BolsaNext/0.1 "
        "(educational investment research; https://github.com/f2432/BolsaNext)"
    )

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
            "url": "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
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

    @classmethod
    def _read_tables(cls, url: str) -> list[pd.DataFrame]:
        """Obtém o HTML com User-Agent explícito e extrai as tabelas.

        Algumas páginas rejeitam pedidos HTTP com o User-Agent por defeito
        do Python/pandas. O download é feito separadamente para manter o
        comportamento previsível e permitir testes sem rede.
        """
        request = Request(
            url,
            headers={
                "User-Agent": cls._USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                html = response.read().decode("utf-8")
        except Exception as exc:
            raise RuntimeError(
                "Não foi possível obter os constituintes do universo. "
                "Verifica a ligação à Internet e tenta novamente."
            ) from exc

        return pd.read_html(StringIO(html))

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
