"""Compatibilidade: o contrato canónico vive em bolsa.app.ports.universe."""

from bolsa.app.ports.universe import (
    UniverseLoadResult,
    UniverseLoadStatus,
    UniverseProvider,
)

__all__ = ["UniverseLoadResult", "UniverseLoadStatus", "UniverseProvider"]
