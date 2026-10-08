from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
import logging
from urllib.request import Request, urlopen

import pandas as pd

from bolsa.app.ports.errors import (
    UnsupportedUniverseError,
    UniverseFormatError,
    UniverseSourceUnavailableError,
)
from bolsa.app.ports.universe import UniverseLoadResult, UniverseLoadStatus
from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.universes import Universe
from bolsa.version import __version__

logger = logging.getLogger(__name__)


class WikipediaUniverseProvider:
    """Provider de composição de universos através da Wikipedia.

    A Wikipedia é autoridade apenas para composição do universo e pode fornecer
    ticker e nome provisório. Exchange, moeda e tipo canónico pertencem à fonte
    principal de Market Data.
    """

    _USER_AGENT = (
        f"BolsaNext/{__version__} "
        "(educational investment research; https://github.com/f2432/BolsaNext)"
    )

    _SOURCES = {
        "sp500": {
            "name": "S&P 500",
            "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            "symbol_columns": ("Symbol", "Ticker"),
            "name_columns": ("Security", "Company"),
            "ticker_style": "us",
        },
        "nasdaq100": {
            "name": "NASDAQ 100",
            "url": "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
            "symbol_columns": ("Ticker", "Symbol"),
            "name_columns": ("Company", "Security"),
            "ticker_style": "us",
        },
        "euronext100": {
            "name": "Euronext 100",
            "url": "https://en.wikipedia.org/wiki/Euronext_100",
            "symbol_columns": ("Ticker",),
            "name_columns": ("Name", "Company"),
            "ticker_style": "yahoo",
        },
    }

    def supported_universes(self) -> tuple[str, ...]:
        return tuple(self._SOURCES.keys())

    def get_universe(self, code: str) -> UniverseLoadResult:
        key = code.strip().lower()
        if key not in self._SOURCES:
            raise UnsupportedUniverseError(code)

        config = self._SOURCES[key]
        logger.info("A obter universo %s", config["name"])

        try:
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
                ticker_style=config.get("ticker_style", "us"),
            )
        except (
            UnsupportedUniverseError,
            UniverseSourceUnavailableError,
            UniverseFormatError,
        ):
            raise
        except Exception as exc:
            raise UniverseFormatError(
                f"Não foi possível interpretar os constituintes de {config['name']}."
            ) from exc

        universe = Universe(
            code=key,
            name=config["name"],
            instruments=tuple(instruments),
            source=config["url"],
            retrieved_at=datetime.now(timezone.utc),
        )

        return UniverseLoadResult(
            universe=universe,
            status=UniverseLoadStatus.LIVE,
        )

    @classmethod
    def _read_tables(cls, url: str) -> list[pd.DataFrame]:
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
            raise UniverseSourceUnavailableError(
                "Não foi possível contactar a fonte do universo. "
                "Verifica a ligação à Internet e tenta novamente."
            ) from exc

        try:
            return pd.read_html(StringIO(html))
        except Exception as exc:
            raise UniverseFormatError(
                "A fonte respondeu, mas as tabelas não puderam ser interpretadas."
            ) from exc

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

        raise UniverseFormatError(
            "A fonte respondeu, mas não foi encontrada uma tabela de "
            "constituintes compatível."
        )

    @staticmethod
    def _table_to_instruments(
        table: pd.DataFrame,
        *,
        symbol_columns: tuple[str, ...],
        name_columns: tuple[str, ...],
        ticker_style: str = "us",
    ) -> list[Instrument]:
        symbol_column = next(
            (column for column in symbol_columns if column in table.columns),
            None,
        )
        name_column = next(
            (column for column in name_columns if column in table.columns),
            None,
        )

        if symbol_column is None or name_column is None:
            raise UniverseFormatError(
                "A tabela de constituintes não contém as colunas esperadas."
            )

        instruments: list[Instrument] = []
        seen: set[str] = set()

        try:
            for _, row in table.iterrows():
                raw_symbol = str(row[symbol_column]).strip()
                if not raw_symbol or raw_symbol.lower() == "nan":
                    continue

                ticker = raw_symbol.upper()
                if ticker_style == "us":
                    ticker = ticker.replace(".", "-")

                if ticker in seen:
                    continue

                raw_name = row[name_column]
                name = None if pd.isna(raw_name) else str(raw_name).strip()

                instruments.append(
                    Instrument(
                        ticker=ticker,
                        name=name,
                        exchange=None,
                        currency=None,
                        asset_type=AssetType.OTHER,
                    )
                )
                seen.add(ticker)
        except UniverseFormatError:
            raise
        except Exception as exc:
            raise UniverseFormatError(
                "A tabela de constituintes contém dados que não puderam ser interpretados."
            ) from exc

        if not instruments:
            raise UniverseFormatError(
                "A fonte respondeu, mas o universo não contém instrumentos válidos."
            )

        return instruments
