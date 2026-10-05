from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class FunctionThread(QThread):
    """Executa uma função fora da thread da interface Qt."""

    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._function = function
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._function(*self._args, **self._kwargs)
        except Exception as exc:
            logger.exception("Erro numa operação assíncrona da interface.")
            self.failed.emit(str(exc))
            return

        self.result_ready.emit(result)
