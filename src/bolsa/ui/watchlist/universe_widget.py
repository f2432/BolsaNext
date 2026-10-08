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

from bolsa.app.ports.universe import UniverseLoadResult, UniverseLoadStatus
from bolsa.app.services.universe_service import UniverseService
from bolsa.app.services.watchlist_service import WatchlistService
from bolsa.ui.table_preferences import enable_table_header_persistence
from bolsa.ui.watchlist.operation_coordinator import WatchlistOperationCoordinator
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
        coordinator: WatchlistOperationCoordinator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._universe_service = universe_service
        self._watchlist_service = watchlist_service
        self._coordinator = coordinator or WatchlistOperationCoordinator(self)
        self._load_thread: FunctionThread | None = None
        self._external_status_text: str | None = None

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

        self._coordinator.busy_changed.connect(self._on_busy_changed)

    def _on_busy_changed(
        self,
        busy: bool,
        label: str,
        owner: object,
    ) -> None:
        self._set_mutation_controls_enabled(not busy)

        if busy and owner is not self:
            self._external_status_text = self._status.text()
            self._status.setText(label)
        elif not busy and owner is not self and self._external_status_text is not None:
            self._status.setText(self._external_status_text)
            self._external_status_text = None

    def _set_mutation_controls_enabled(self, enabled: bool) -> None:
        self._combo.setEnabled(enabled)
        self._load_button.setEnabled(enabled)
        self._add_button.setEnabled(enabled)

    def _load_universe(self) -> None:
        code = self._combo.currentData()
        if not code or self._load_thread is not None:
            return

        label = f"A carregar {_UNIVERSE_LABELS.get(code, code)}..."
        if not self._coordinator.begin(self, label):
            return

        self._status.setText(label)
        self._table.setRowCount(0)

        thread = FunctionThread(self._universe_service.load, code)
        thread.result_ready.connect(self._render_universe)
        thread.failed.connect(self._load_failed)
        thread.finished.connect(self._load_finished)
        self._load_thread = thread

        try:
            thread.start()
        except Exception:
            self._load_thread = None
            self._coordinator.finish(self)
            thread.deleteLater()
            raise

    def _render_universe(self, result: UniverseLoadResult) -> None:
        universe = result.universe
        self._table.setRowCount(len(universe.instruments))
        for row_index, instrument in enumerate(universe.instruments):
            self._table.setItem(row_index, 0, QTableWidgetItem(instrument.ticker))
            self._table.setItem(row_index, 1, QTableWidgetItem(instrument.name or ""))
            self._table.setItem(row_index, 2, QTableWidgetItem(instrument.market or ""))
            self._table.setItem(row_index, 3, QTableWidgetItem(instrument.currency or ""))

        status = f"{universe.name}: {len(universe.instruments)} instrumentos carregados."

        if result.status is UniverseLoadStatus.FRESH_CACHE and result.cached_at is not None:
            status += (
                " Cache local de "
                + result.cached_at.astimezone().strftime("%d/%m/%Y %H:%M")
                + "."
            )
        elif result.status is UniverseLoadStatus.STALE_CACHE:
            if result.cached_at is not None:
                status += (
                    " Dados em cache de "
                    + result.cached_at.astimezone().strftime("%d/%m/%Y %H:%M")
                    + "."
                )
            if result.warning:
                status += " " + result.warning

        self._status.setText(status)

        if self._table.rowCount() > 0:
            self._table.selectRow(0)

    def _load_failed(self, message: str) -> None:
        self._status.setText("Erro ao carregar universo.")
        QMessageBox.critical(self, "Universos", message)

    def _load_finished(self) -> None:
        thread = self._load_thread
        self._load_thread = None
        self._coordinator.finish(self)
        if thread is not None:
            thread.deleteLater()

    def _add_selected(self) -> None:
        if self._coordinator.busy:
            return

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
