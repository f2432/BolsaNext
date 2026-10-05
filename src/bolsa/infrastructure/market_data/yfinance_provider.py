from __future__ import annotations

from datetime import date
import logging

import pandas as pd
import yfinance as yf

from bolsa.domain.instruments import AssetType, Instrument

logger = logging.getLogger(__name__)

_CANONICAL_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


class YFinanceMarketDataProvider:
    """Adapter de dados de mercado baseado em yfinance.

    Política inicial:
    - OHLC é mantido sem auto-adjust;
    - Adj Close é preservado quando disponibilizado;
    - o índice é convertido para DatetimeIndex;
    - timestamps com timezone são convertidos para UTC e ficam timezone-naive;
    - linhas duplicadas são removidas, mantendo a última;
    - o resultado é ordenado por data.
    """

    def get_historical_data(
        self,
        instrument: Instrument,
        *,
        period: str = "1y",
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        kwargs: dict[str, object] = {
            "tickers": instrument.ticker,
            "interval": interval,
            "auto_adjust": False,
            "progress": False,
            "threads": False,
        }

        if start is not None or end is not None:
            if start is not None:
                kwargs["start"] = start.isoformat()
            if end is not None:
                kwargs["end"] = end.isoformat()
        else:
            kwargs["period"] = period

        logger.info(
            "A obter histórico de %s (period=%s, interval=%s)",
            instrument.ticker,
            period,
            interval,
        )

        data = yf.download(**kwargs)
        return self._normalise_history(data, instrument.ticker)

    def get_instrument_details(self, instrument: Instrument) -> Instrument:
        try:
            info = yf.Ticker(instrument.ticker).get_info() or {}
        except Exception:
            logger.exception(
                "Erro ao obter metadados de %s; serão usados os dados existentes.",
                instrument.ticker,
            )
            return instrument

        name = (
            info.get("longName")
            or info.get("shortName")
            or instrument.name
        )
        market = (
            info.get("fullExchangeName")
            or info.get("exchange")
            or instrument.market
        )
        currency = info.get("currency") or instrument.currency

        quote_type = str(info.get("quoteType") or "").upper()
        asset_type = {
            "EQUITY": AssetType.STOCK,
            "ETF": AssetType.ETF,
            "INDEX": AssetType.INDEX,
        }.get(quote_type, instrument.asset_type)

        try:
            return Instrument(
                ticker=instrument.ticker,
                name=name,
                market=market,
                currency=currency,
                asset_type=asset_type,
            )
        except ValueError:
            logger.warning(
                "Metadados inválidos recebidos para %s; serão mantidos os dados existentes.",
                instrument.ticker,
                exc_info=True,
            )
            return instrument

    def get_current_price(self, instrument: Instrument) -> float | None:
        try:
            ticker = yf.Ticker(instrument.ticker)

            try:
                price = ticker.fast_info.get("last_price")
                if price is not None:
                    return float(price)
            except Exception:
                logger.debug(
                    "fast_info indisponível para %s; a usar fallback.",
                    instrument.ticker,
                    exc_info=True,
                )

            history = ticker.history(period="1d", interval="1m", auto_adjust=False)
            if history is None or history.empty or "Close" not in history.columns:
                return None

            return float(history["Close"].dropna().iloc[-1])
        except Exception:
            logger.exception("Erro ao obter preço atual de %s", instrument.ticker)
            return None

    @staticmethod
    def _normalise_history(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if data is None or data.empty:
            return pd.DataFrame(columns=_CANONICAL_COLUMNS)

        result = data.copy()

        if isinstance(result.columns, pd.MultiIndex):
            # yfinance pode devolver (campo, ticker) para um único ativo.
            level_0 = result.columns.get_level_values(0)
            if set(_CANONICAL_COLUMNS).intersection(level_0):
                result.columns = level_0
            else:
                level_last = result.columns.get_level_values(-1)
                if ticker in level_last:
                    result = result.xs(ticker, axis=1, level=-1)

        result.index = pd.to_datetime(result.index)

        if isinstance(result.index, pd.DatetimeIndex) and result.index.tz is not None:
            result.index = result.index.tz_convert("UTC").tz_localize(None)

        result = result[~result.index.duplicated(keep="last")].sort_index()
        result.index.name = "Date"

        for column in _CANONICAL_COLUMNS:
            if column not in result.columns:
                result[column] = pd.NA

        result = result[_CANONICAL_COLUMNS]

        numeric_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        for column in numeric_columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

        return result
