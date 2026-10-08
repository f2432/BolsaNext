from __future__ import annotations

from bolsa.ui.watchlist.operation_coordinator import WatchlistOperationCoordinator


def test_coordinator_accepts_only_one_operation_at_a_time() -> None:
    coordinator = WatchlistOperationCoordinator()
    owner_a = object()
    owner_b = object()

    assert coordinator.begin(owner_a, "Operação A") is True
    assert coordinator.busy is True
    assert coordinator.label == "Operação A"
    assert coordinator.owner is owner_a

    assert coordinator.begin(owner_b, "Operação B") is False
    assert coordinator.owner is owner_a
    assert coordinator.label == "Operação A"


def test_coordinator_only_owner_can_finish_operation() -> None:
    coordinator = WatchlistOperationCoordinator()
    owner_a = object()
    owner_b = object()

    coordinator.begin(owner_a, "Operação A")
    coordinator.finish(owner_b)

    assert coordinator.busy is True
    assert coordinator.owner is owner_a

    coordinator.finish(owner_a)

    assert coordinator.busy is False
    assert coordinator.owner is None
    assert coordinator.label == ""


def test_coordinator_emits_busy_and_idle_states() -> None:
    coordinator = WatchlistOperationCoordinator()
    owner = object()
    events = []

    coordinator.busy_changed.connect(
        lambda busy, label, signal_owner: events.append(
            (busy, label, signal_owner)
        )
    )

    coordinator.begin(owner, "A atualizar preços...")
    coordinator.finish(owner)

    assert events == [
        (True, "A atualizar preços...", owner),
        (False, "", owner),
    ]
