from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .operation_coordinator import WatchlistOperationCoordinator
    from .universe_widget import UniverseWidget
    from .widget import WatchlistWidget

__all__ = [
    "UniverseWidget",
    "WatchlistOperationCoordinator",
    "WatchlistWidget",
]


def __getattr__(name: str) -> Any:
    if name == "WatchlistOperationCoordinator":
        from .operation_coordinator import WatchlistOperationCoordinator

        return WatchlistOperationCoordinator

    if name == "UniverseWidget":
        from .universe_widget import UniverseWidget

        return UniverseWidget

    if name == "WatchlistWidget":
        from .widget import WatchlistWidget

        return WatchlistWidget

    raise AttributeError(name)
