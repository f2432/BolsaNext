from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class WatchlistOperationCoordinator(QObject):
    """Coordena uma única operação assíncrona de Watchlist/UI de cada vez."""

    busy_changed = Signal(bool, str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._label = ""
        self._owner: object | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def label(self) -> str:
        return self._label

    @property
    def owner(self) -> object | None:
        return self._owner

    def begin(self, owner: object, label: str) -> bool:
        if self._busy:
            return False

        self._busy = True
        self._label = label
        self._owner = owner
        self.busy_changed.emit(True, label, owner)
        return True

    def finish(self, owner: object) -> None:
        if not self._busy or self._owner is not owner:
            return

        previous_owner = self._owner
        self._busy = False
        self._label = ""
        self._owner = None
        self.busy_changed.emit(False, "", previous_owner)
