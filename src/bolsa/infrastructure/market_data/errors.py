"""Compatibilidade: os erros canónicos vivem em bolsa.app.ports.errors."""

from bolsa.app.ports.errors import (
    CurrentPriceUnavailableError,
    ExternalDataError,
    InstrumentNotFoundError,
    MarketDataError,
    MarketDataFormatError,
    MarketDataUnavailableError,
    UnsupportedUniverseError,
    UniverseError,
    UniverseFormatError,
    UniverseSourceUnavailableError,
)

__all__ = [
    "CurrentPriceUnavailableError",
    "ExternalDataError",
    "InstrumentNotFoundError",
    "MarketDataError",
    "MarketDataFormatError",
    "MarketDataUnavailableError",
    "UnsupportedUniverseError",
    "UniverseError",
    "UniverseFormatError",
    "UniverseSourceUnavailableError",
]
