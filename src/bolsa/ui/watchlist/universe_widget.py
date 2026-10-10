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
from bolsa.app.services.watchlist_service import (
    UniverseInstrumentAddResult,
    WatchlistService,
)
from bolsa.domain.instruments import Instrument
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
        self._operation_thread: FunctionThread | None = None
        self._loaded_instruments: tuple[Instrument, ...] = ()
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

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Ticker", "Nome"])
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

    def _start_thread(
        self,
        thread: FunctionThread,
        *,
        result_handler,
        failure_handler,
    ) -> None:
        thread.result_ready.connect(result_handler)
        thread.failed.connect(failure_handler)
        thread.finished.connect(self._operation_finished)
        self._operation_thread = thread

        try:
            thread.start()
        except Exception:
            self._operation_thread = None
            self._coordinator.finish(self)
            thread.deleteLater()
            raise

    def _operation_finished(self) -> None:
        thread = self._operation_thread
        self._operation_thread = None
        self._coordinator.finish(self)
        if thread is not None:
            thread.deleteLater()

    def _load_universe(self) -> None:
        code = self._combo.currentData()
        if not code or self._operation_thread is not None:
            return

        label = f"A carregar {_UNIVERSE_LABELS.get(code, code)}..."
        if not self._coordinator.begin(self, label):
            return

        self._status.setText(label)
        self._loaded_instruments = ()
        self._table.setRowCount(0)

        thread = FunctionThread(self._universe_service.load, code)
        self._start_thread(
            thread,
            result_handler=self._render_universe,
            failure_handler=self._load_failed,
        )

    def _render_universe(self, result: UniverseLoadResult) -> None:
        universe = result.universe
        self._loaded_instruments = universe.instruments

        self._table.setRowCount(len(self._loaded_instruments))
        for row_index, instrument in enumerate(self._loaded_instruments):
            self._table.setItem(row_index, 0, QTableWidgetItem(instrument.ticker))
            self._table.setItem(row_index, 1, QTableWidgetItem(instrument.name or ""))

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
        self._loaded_instruments = ()
        self._status.setText("Erro ao carregar universo.")
        QMessageBox.critical(self, "Universos", message)

    def _add_selected(self) -> None:
        if self._coordinator.busy or self._operation_thread is not None:
            return

        row = self._table.currentRow()
        if row < 0 or row >= len(self._loaded_instruments):
            QMessageBox.information(
                self,
                "Universos",
                "Seleciona primeiro um instrumento.",
            )
            return

        instrument = self._loaded_instruments[row]
        label = f"A confirmar dados de {instrument.ticker}..."

        if not self._coordinator.begin(self, label):
            return

        self._status.setText(label)
        thread = FunctionThread(
            self._watchlist_service.add_universe_instrument,
            instrument,
        )
        self._start_thread(
            thread,
            result_handler=self._add_complete,
            failure_handler=self._add_failed,
        )

    def _add_complete(self, result: UniverseInstrumentAddResult) -> None:
        ticker = result.instrument.ticker
        self.instrument_added.emit(ticker)

        if result.provisional:
            self._status.setText(f"{ticker} adicionado com dados provisórios.")
            detail = (
                f"{ticker} foi adicionado com ticker e nome do universo. "
                "Bolsa, moeda e tipo ficam por confirmar pela fonte principal."
            )
            if result.warning:
                detail += f"\n\nMotivo: {result.warning}"
            QMessageBox.warning(self, "Watchlist", detail)
            return

        self._status.setText(f"{ticker} adicionado com dados confirmados.")
        QMessageBox.information(
            self,
            "Watchlist",
            f"{ticker} adicionado à Watchlist com dados confirmados.",
        )

    def _add_failed(self, message: str) -> None:
        self._status.setText("Não foi possível adicionar o ativo.")
        QMessageBox.warning(self, "Watchlist", message)
