from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

import pandas as pd
import yfinance as yf

from bolsa.app.ports.errors import (
    CurrentPriceUnavailableError,
    InstrumentNotFoundError,
    MarketDataError,
    MarketDataFormatError,
    MarketDataUnavailableError,
)
from bolsa.domain.instruments import AssetType, Instrument

logger = logging.getLogger(__name__)

_CANONICAL_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
_PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close"]
_METADATA_KEYS = {
    "quoteType",
    "longName",
    "shortName",
    "exchange",
    "fullExchangeName",
    "currency",
}

_SUBUNIT_CURRENCIES: dict[str, tuple[str, float]] = {
    "GBp": ("GBP", 0.01),
    "GBX": ("GBP", 0.01),
    "ZAc": ("ZAR", 0.01),
    "ILA": ("ILS", 0.01),
}


@dataclass(frozen=True, slots=True)
class _QuoteConvention:
    raw_currency: str
    currency: str
    price_factor: float


class YFinanceMarketDataProvider:
    """Adapter de dados de mercado baseado em yfinance."""

    def __init__(self) -> None:
        self._quote_conventions: dict[str, _QuoteConvention] = {}

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

        try:
            data = yf.download(**kwargs)
        except Exception as exc:
            logger.exception("Erro ao obter histórico de %s", instrument.ticker)
            raise MarketDataUnavailableError(
                f"Não foi possível obter o histórico de {instrument.ticker}. "
                "Tenta novamente."
            ) from exc

        try:
            result = self._normalise_history(data, instrument.ticker)
            if result.empty:
                return result

            convention = self._get_quote_convention(instrument)
            return self._apply_price_factor(result, convention.price_factor)
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataFormatError(
                f"O histórico de {instrument.ticker} não tem o formato esperado."
            ) from exc

    def get_instrument_details(self, instrument: Instrument) -> Instrument:
        try:
            info = yf.Ticker(instrument.ticker).get_info() or {}
        except Exception as exc:
            logger.exception("Erro ao obter metadados de %s", instrument.ticker)
            raise MarketDataUnavailableError(
                f"Não foi possível consultar os dados de {instrument.ticker}. "
                "Tenta novamente."
            ) from exc

        if not isinstance(info, dict):
            raise MarketDataFormatError(
                f"Os metadados de {instrument.ticker} não têm o formato esperado."
            )

        if not self._has_instrument_metadata(info):
            raise InstrumentNotFoundError(instrument.ticker)

        convention = self._quote_convention_from_info(info, instrument.ticker)
        self._quote_conventions[instrument.ticker] = convention

        name = info.get("longName") or info.get("shortName") or instrument.name
        market = (
            info.get("fullExchangeName")
            or info.get("exchange")
            or instrument.market
        )

        quote_type = str(info.get("quoteType") or "").upper()
        asset_type = {
            "EQUITY": AssetType.STOCK,
            "ETF": AssetType.ETF,
            "INDEX": AssetType.INDEX,
        }.get(quote_type, instrument.asset_type)

        return Instrument(
            ticker=instrument.ticker,
            name=name,
            market=market,
            currency=convention.currency,
            asset_type=asset_type,
        )

    def get_current_price(self, instrument: Instrument) -> float:
        ticker = yf.Ticker(instrument.ticker)

        try:
            try:
                price = ticker.fast_info.get("last_price")
                if price is not None:
                    convention = self._get_quote_convention(
                        instrument,
                        ticker=ticker,
                    )
                    return float(price) * convention.price_factor
            except MarketDataError:
                raise
            except Exception:
                logger.debug(
                    "fast_info indisponível para %s; a usar fallback.",
                    instrument.ticker,
                    exc_info=True,
                )

            try:
                history = ticker.history(
                    period="1d",
                    interval="1m",
                    auto_adjust=False,
                )
            except Exception as exc:
                raise MarketDataUnavailableError(
                    f"Não foi possível obter a cotação atual de {instrument.ticker}. "
                    "Tenta novamente."
                ) from exc

            if history is None or (
                isinstance(history, pd.DataFrame) and history.empty
            ):
                self._raise_for_missing_current_price(ticker, instrument)

            if not isinstance(history, pd.DataFrame):
                raise MarketDataFormatError(
                    f"A cotação atual de {instrument.ticker} não tem o formato esperado."
                )

            if "Close" not in history.columns:
                raise MarketDataFormatError(
                    f"A cotação atual de {instrument.ticker} não contém a coluna Close."
                )

            close = history["Close"].dropna()
            if close.empty:
                self._raise_for_missing_current_price(ticker, instrument)

            try:
                raw_price = float(close.iloc[-1])
            except (TypeError, ValueError) as exc:
                raise MarketDataFormatError(
                    f"A cotação atual de {instrument.ticker} não é numérica."
                ) from exc

            convention = self._get_quote_convention(
                instrument,
                ticker=ticker,
            )
            return raw_price * convention.price_factor
        except MarketDataError:
            raise
        except Exception as exc:
            logger.exception("Erro inesperado ao obter preço atual de %s", instrument.ticker)
            raise MarketDataUnavailableError(
                f"Não foi possível obter a cotação atual de {instrument.ticker}. "
                "Tenta novamente."
            ) from exc

    def _get_quote_convention(
        self,
        instrument: Instrument,
        *,
        ticker: object | None = None,
    ) -> _QuoteConvention:
        cached = self._quote_conventions.get(instrument.ticker)
        if cached is not None:
            return cached

        yahoo_ticker = ticker or yf.Ticker(instrument.ticker)

        try:
            info = yahoo_ticker.get_info() or {}
        except Exception as exc:
            raise MarketDataUnavailableError(
                f"Não foi possível obter a moeda de cotação de {instrument.ticker}. "
                "Tenta novamente."
            ) from exc

        if not isinstance(info, dict):
            raise MarketDataFormatError(
                f"Os metadados de {instrument.ticker} não têm o formato esperado."
            )

        if not self._has_instrument_metadata(info):
            raise InstrumentNotFoundError(instrument.ticker)

        convention = self._quote_convention_from_info(info, instrument.ticker)
        self._quote_conventions[instrument.ticker] = convention
        return convention

    @staticmethod
    def _quote_convention_from_info(
        info: dict[str, object],
        ticker: str,
    ) -> _QuoteConvention:
        raw_currency = info.get("currency")
        if raw_currency is None:
            raise MarketDataFormatError(
                f"O fornecedor não indicou a moeda de cotação de {ticker}."
            )

        return YFinanceMarketDataProvider._quote_convention_from_currency(
            raw_currency,
            ticker=ticker,
        )

    @staticmethod
    def _quote_convention_from_currency(
        value: object,
        *,
        ticker: str,
    ) -> _QuoteConvention:
        if not isinstance(value, str):
            raise MarketDataFormatError(
                f"A moeda de cotação de {ticker} não tem o formato esperado."
            )

        raw_currency = value.strip()
        if not raw_currency:
            raise MarketDataFormatError(
                f"O fornecedor devolveu uma moeda de cotação vazia para {ticker}."
            )

        subunit = _SUBUNIT_CURRENCIES.get(raw_currency)
        if subunit is not None:
            currency, factor = subunit
            return _QuoteConvention(
                raw_currency=raw_currency,
                currency=currency,
                price_factor=factor,
            )

        if (
            len(raw_currency) == 3
            and raw_currency.isalpha()
            and raw_currency == raw_currency.upper()
        ):
            return _QuoteConvention(
                raw_currency=raw_currency,
                currency=raw_currency,
                price_factor=1.0,
            )

        raise MarketDataFormatError(
            f"Moeda de cotação não reconhecida para {ticker}: {raw_currency!r}."
        )

    def _raise_for_missing_current_price(
        self,
        ticker: object,
        instrument: Instrument,
    ) -> None:
        try:
            info = ticker.get_info() or {}
        except Exception as exc:
            raise MarketDataUnavailableError(
                f"Não foi possível confirmar o instrumento {instrument.ticker}. "
                "Tenta novamente."
            ) from exc

        if not isinstance(info, dict):
            raise MarketDataFormatError(
                f"Os metadados de {instrument.ticker} não têm o formato esperado."
            )

        if not self._has_instrument_metadata(info):
            raise InstrumentNotFoundError(instrument.ticker)

        if info.get("currency") is not None:
            convention = self._quote_convention_from_info(info, instrument.ticker)
            self._quote_conventions[instrument.ticker] = convention

        raise CurrentPriceUnavailableError(instrument.ticker)

    @staticmethod
    def _has_instrument_metadata(info: dict[str, object]) -> bool:
        return any(info.get(key) not in (None, "") for key in _METADATA_KEYS)

    @staticmethod
    def _empty_history() -> pd.DataFrame:
        return pd.DataFrame(
            index=pd.DatetimeIndex([], name="Date"),
            columns=_CANONICAL_COLUMNS,
        )

    @staticmethod
    def _apply_price_factor(
        data: pd.DataFrame,
        factor: float,
    ) -> pd.DataFrame:
        if factor == 1.0:
            return data

        result = data.copy()
        for column in _PRICE_COLUMNS:
            result[column] = result[column] * factor
        return result

    @staticmethod
    def _normalise_history(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if data is None:
            return YFinanceMarketDataProvider._empty_history()

        if not isinstance(data, pd.DataFrame):
            raise MarketDataFormatError(
                f"O histórico de {ticker} não tem o formato esperado."
            )

        if data.empty:
            return YFinanceMarketDataProvider._empty_history()

        result = data.copy()

        if isinstance(result.columns, pd.MultiIndex):
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

        for column in _CANONICAL_COLUMNS:
            result[column] = pd.to_numeric(result[column], errors="coerce")

        return result
