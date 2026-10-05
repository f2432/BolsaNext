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
from bolsa.domain.universes import Universe
from bolsa.ui.table_preferences import enable_table_header_persistence
from bolsa.ui.workers import FunctionThread


_UNIVERSE_LABELS = {
    "sp500": "S&P 500",
    "nasdaq100": "NASDAQ 100",
    "euronext100": "Euronext 100",
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
        self._load_thread: FunctionThread | None = None

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Universo:"))

        self._combo = QComboBox()
        for code in self._universe_service.available():
            self._combo.addItem(_UNIVERSE_LABELS.get(code, code), code)
        controls.addWidget(self._combo)

        self._load_button = QPushButton("Carregar")
        self._load_button.clicked.connect(self._load_universe)
        controls.addWidget(self._load_button)

        self._add_button = QPushButton("Adicionar selecionado à Watchlist")
        self._add_button.clicked.connect(self._add_selected)
        controls.addWidget(self._add_button)

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
        enable_table_header_persistence(self._table, "watchlist/universes")
        layout.addWidget(self._table)

    def _load_universe(self) -> None:
        code = self._combo.currentData()
        if not code or self._load_thread is not None:
            return

        self._status.setText("A carregar universo...")
        self._table.setRowCount(0)
        self._set_loading(True)

        thread = FunctionThread(self._universe_service.load, code)
        thread.result_ready.connect(self._render_universe)
        thread.failed.connect(self._load_failed)
        thread.finished.connect(self._load_finished)
        self._load_thread = thread
        thread.start()

    def _render_universe(self, universe: Universe) -> None:
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

    def _load_failed(self, message: str) -> None:
        self._status.setText("Erro ao carregar universo.")
        QMessageBox.critical(self, "Universos", message)

    def _load_finished(self) -> None:
        self._set_loading(False)
        if self._load_thread is not None:
            self._load_thread.deleteLater()
        self._load_thread = None

    def _set_loading(self, loading: bool) -> None:
        self._combo.setEnabled(not loading)
        self._load_button.setEnabled(not loading)
        self._add_button.setEnabled(not loading)

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
