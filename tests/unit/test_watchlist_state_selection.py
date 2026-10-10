import pytest

from bolsa.domain.watchlist import WatchlistState
from bolsa.ui.watchlist.state_selection import recognised_state


@pytest.mark.parametrize("state", list(WatchlistState))
def test_recognised_state_accepts_all_known_values(state: WatchlistState) -> None:
    assert recognised_state(state.value) == state


@pytest.mark.parametrize(
    "value", [None, -1, 0, "", "unknown", "UNKNOWN", "candidate-extra", [], {}],
)
def test_recognised_state_rejects_unrecognised_values(value: object) -> None:
    assert recognised_state(value) is None
