from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QSettings

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTableWidget


_ORGANIZATION = "BolsaNext"
_APPLICATION = "BolsaNext"


def restore_table_header(table: "QTableWidget", key: str) -> None:
    """Restaura larguras e restante estado do cabeçalho da tabela."""
    settings = QSettings(_ORGANIZATION, _APPLICATION)
    value = settings.value(_settings_key(key))

    if isinstance(value, QByteArray):
        table.horizontalHeader().restoreState(value)


def enable_table_header_persistence(table: "QTableWidget", key: str) -> None:
    """Restaura o cabeçalho e passa a guardar alterações futuras."""
    restore_table_header(table, key)

    header = table.horizontalHeader()

    def save_state(*_args: object) -> None:
        settings = QSettings(_ORGANIZATION, _APPLICATION)
        settings.setValue(_settings_key(key), header.saveState())

    header.sectionResized.connect(save_state)
    header.sectionMoved.connect(save_state)


def _settings_key(key: str) -> str:
    return f"ui/table_headers/{key}"
