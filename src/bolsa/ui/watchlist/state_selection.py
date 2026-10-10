"""Defensive conversion of user-selected watchlist states.

Kept free of Qt imports so its behavior is unit-testable headlessly.
"""

from bolsa.domain.watchlist import WatchlistState


def recognised_state(value: object) -> WatchlistState | None:
    if not isinstance(value, str):
        return None
    try:
        return WatchlistState(value)
    except ValueError:
        return None
