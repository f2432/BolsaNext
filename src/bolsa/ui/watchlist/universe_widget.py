from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bolsa.app.services.universe_service import UniverseService
from bolsa.app.services.watchlist_service import WatchlistService


_UNIVERSE_LABELS = {
    "sp500": "S&P 500",
    "nasdaq100": "NASDAQ 100",
}


class UniverseWidget(QWidget):
    instrument_added = Signal(str)

    def __init__(
        self,
        universe_service: UniverseService,
        watchlist_service: WatchlistService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._universe_service = universe_service
        self._watchlist_service = watchlist_service

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Universo:"))

        self._combo = QComboBox()
        for code in self._universe_service.available():
            self._combo.addItem(_UNIVERSE_LABELS.get(code, code), code)
        controls.addWidget(self._combo)

        load_button = QPushButton("Carregar")
        load_button.clicked.connect(self._load_universe)
        controls.addWidget(load_button)

        add_button = QPushButton("Adicionar selecionado à Watchlist")
        add_button.clicked.connect(self._add_selected)
        controls.addWidget(add_button)

        controls.addStretch()
        layout.addLayout(controls)

        self._status = QLabel("Seleciona um universo e carrega os constituintes.")
        layout.addWidget(self._status)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Ticker", "Nome", "Mercado", "Moeda"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

    def _load_universe(self) -> None:
        code = self._combo.currentData()
        if not code:
            return

        self._status.setText("A carregar universo...")
        self._table.setRowCount(0)

        try:
            universe = self._universe_service.load(code)
        except Exception as exc:
            self._status.setText("Erro ao carregar universo.")
            QMessageBox.critical(self, "Universos", str(exc))
            return

        self._table.setRowCount(len(universe.instruments))
        for row_index, instrument in enumerate(universe.instruments):
            self._table.setItem(row_index, 0, QTableWidgetItem(instrument.ticker))
            self._table.setItem(row_index, 1, QTableWidgetItem(instrument.name or ""))
            self._table.setItem(row_index, 2, QTableWidgetItem(instrument.market or ""))
            self._table.setItem(row_index, 3, QTableWidgetItem(instrument.currency or ""))

        self._status.setText(
            f"{universe.name}: {len(universe.instruments)} instrumentos carregados."
        )

        if self._table.rowCount() > 0:
            self._table.selectRow(0)

    def _add_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Universos",
                "Seleciona primeiro um instrumento.",
            )
            return

        ticker = self._table.item(row, 0).text()
        name = self._table.item(row, 1).text() or None
        market = self._table.item(row, 2).text() or None
        currency = self._table.item(row, 3).text() or None

        try:
            self._watchlist_service.add_ticker(
                ticker,
                name=name,
                market=market,
                currency=currency,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Watchlist", str(exc))
            return

        self.instrument_added.emit(ticker)
        QMessageBox.information(
            self,
            "Watchlist",
            f"{ticker} adicionado à Watchlist.",
        )
