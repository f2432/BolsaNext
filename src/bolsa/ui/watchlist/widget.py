from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bolsa.app.services.watchlist_service import WatchlistRow, WatchlistService
from bolsa.domain.instruments import Instrument
from bolsa.domain.watchlist import WatchlistState
from bolsa.ui.table_preferences import enable_table_header_persistence
from bolsa.ui.watchlist.operation_coordinator import WatchlistOperationCoordinator
from bolsa.ui.workers import FunctionThread


_STATE_LABELS = {
    WatchlistState.IDEA: "Ideia",
    WatchlistState.ANALYSING: "Em análise",
    WatchlistState.CANDIDATE: "Candidato",
    WatchlistState.REJECTED: "Rejeitado",
    WatchlistState.REVIEW: "Em revisão",
}


class WatchlistWidget(QWidget):
    def __init__(
        self,
        service: WatchlistService,
        coordinator: WatchlistOperationCoordinator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._coordinator = coordinator or WatchlistOperationCoordinator(self)
        self._operation_thread: FunctionThread | None = None
        self._external_status_text: str | None = None
        self._last_price_warnings: tuple[str, ...] = ()

        layout = QVBoxLayout(self)

        title = QLabel(f"Watchlist: {service.name}")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Ticker, por exemplo AAPL")
        self._ticker_input.returnPressed.connect(self._add_ticker)
        controls.addWidget(self._ticker_input)

        self._add_button = QPushButton("Adicionar")
        self._add_button.clicked.connect(self._add_ticker)
        controls.addWidget(self._add_button)

        self._metadata_button = QPushButton("Atualizar dados")
        self._metadata_button.clicked.connect(self._start_metadata_refresh)
        controls.addWidget(self._metadata_button)

        self._refresh_button = QPushButton("Atualizar preços")
        self._refresh_button.clicked.connect(self._start_price_refresh)
        controls.addWidget(self._refresh_button)

        layout.addLayout(controls)

        self._status = QLabel("")
        layout.addWidget(self._status)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Ticker", "Nome", "Bolsa", "Moeda", "Estado", "Preço atual", "Ações"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        enable_table_header_persistence(self._table, "watchlist/main")
        layout.addWidget(self._table)

        self._coordinator.busy_changed.connect(self._on_busy_changed)
        self._refresh_table()

    def _begin_operation(self, label: str) -> bool:
        if self._operation_thread is not None:
            return False
        return self._coordinator.begin(self, label)

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

        self._ticker_input.setFocus()

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
        self._ticker_input.setEnabled(enabled)
        self._add_button.setEnabled(enabled)
        self._metadata_button.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)

        for row in range(self._table.rowCount()):
            for column in (4, 6):
                widget = self._table.cellWidget(row, column)
                if widget is not None:
                    widget.setEnabled(enabled)

    def _add_ticker(self) -> None:
        ticker = self._ticker_input.text().strip()
        if not ticker:
            return

        label = f"A obter dados de {ticker.upper()}..."
        if not self._begin_operation(label):
            return

        self._status.setText(label)
        thread = FunctionThread(self._service.add_ticker_enriched, ticker)
        self._start_thread(
            thread,
            result_handler=self._manual_add_complete,
            failure_handler=self._manual_add_failed,
        )

    def _manual_add_complete(self, instrument: Instrument) -> None:
        self._ticker_input.clear()
        self._refresh_table()
        self._status.setText(f"{instrument.ticker} adicionado.")

    def _manual_add_failed(self, message: str) -> None:
        self._status.setText("Não foi possível adicionar o ativo.")
        QMessageBox.warning(self, "Watchlist", message)

    def refresh(self, *, refresh_prices: bool = False) -> None:
        if refresh_prices:
            self._start_price_refresh()
        else:
            self._refresh_table()

    def _start_metadata_refresh(self) -> None:
        label = "A atualizar dados dos ativos..."
        if not self._begin_operation(label):
            return

        self._status.setText(label)
        thread = FunctionThread(self._service.refresh_metadata)
        self._start_thread(
            thread,
            result_handler=self._metadata_refresh_complete,
            failure_handler=self._metadata_refresh_failed,
        )

    def _metadata_refresh_complete(self, rows: list[WatchlistRow]) -> None:
        self._render_rows(rows)
        warnings = self._service.metadata_warnings

        if warnings:
            self._status.setText(
                f"Dados atualizados com {len(warnings)} aviso(s)."
            )
            QMessageBox.warning(
                self,
                "Watchlist",
                "Alguns metadados não puderam ser atualizados:\n\n"
                + "\n".join(warnings),
            )
        else:
            self._status.setText("Dados dos ativos atualizados.")

    def _metadata_refresh_failed(self, message: str) -> None:
        self._status.setText("Erro ao atualizar dados dos ativos.")
        QMessageBox.warning(self, "Watchlist", message)

    def _start_price_refresh(self) -> None:
        label = "A atualizar preços..."
        if not self._begin_operation(label):
            return

        self._status.setText(label)
        thread = FunctionThread(self._service.rows, refresh_prices=True)
        self._start_thread(
            thread,
            result_handler=self._price_refresh_complete,
            failure_handler=self._price_refresh_failed,
        )

    def _price_refresh_complete(self, rows: list[WatchlistRow]) -> None:
        self._render_rows(rows)
        warnings = self._service.price_warnings
        self._last_price_warnings = warnings
        updated = [row.price_updated_at for row in rows if row.price_updated_at is not None]
        time_label = max(updated).astimezone().strftime("%H:%M") if updated else None

        if warnings:
            self._status.setText(
                f"Atualização concluída às {time_label}, com {len(warnings)} aviso(s). "
                "Último preço conhecido mantido quando disponível."
                if time_label else f"Atualização com {len(warnings)} aviso(s); sem preços disponíveis."
            )
            QMessageBox.warning(
                self,
                "Watchlist",
                "Alguns preços não puderam ser atualizados:\n\n"
                + "\n".join(warnings),
            )
        else:
            self._status.setText(
                f"Preços atualizados às {time_label}." if time_label
                else "Sem preços disponíveis."
            )

    def _price_refresh_failed(self, message: str) -> None:
        self._status.setText("Erro ao atualizar preços.")
        QMessageBox.warning(self, "Watchlist", message)

    def _refresh_table(self) -> None:
        rows = self._service.rows()
        self._render_rows(rows)
        timestamps = [row.price_updated_at for row in rows if row.price_updated_at is not None]
        if timestamps:
            time_label = max(timestamps).astimezone().strftime("%H:%M")
            self._status.setText(f"Preços em memória · última atualização às {time_label}.")

    def _render_rows(self, rows: list[WatchlistRow]) -> None:
        self._table.setRowCount(len(rows))
        controls_enabled = not self._coordinator.busy

        for row_index, row in enumerate(rows):
            self._table.setItem(row_index, 0, QTableWidgetItem(row.ticker))
            self._table.setItem(row_index, 1, QTableWidgetItem(row.name or ""))
            self._table.setItem(row_index, 2, QTableWidgetItem(row.exchange or ""))
            self._table.setItem(row_index, 3, QTableWidgetItem(row.currency or ""))

            state_combo = QComboBox()
            for state, label in _STATE_LABELS.items():
                state_combo.addItem(label, state.value)
            state_combo.setCurrentIndex(state_combo.findData(row.state.value))
            state_combo.setEnabled(controls_enabled)
            state_combo.currentIndexChanged.connect(
                lambda _index, ticker=row.ticker, combo=state_combo: (
                    self._change_state(ticker, combo.currentData())
                )
            )
            self._table.setCellWidget(row_index, 4, state_combo)

            price_text = "—" if row.price is None else f"{row.price:.2f}"
            self._table.setItem(row_index, 5, QTableWidgetItem(price_text))

            remove_button = QPushButton("Remover")
            remove_button.setEnabled(controls_enabled)
            remove_button.clicked.connect(
                lambda _checked=False, ticker=row.ticker: self._remove_ticker(ticker)
            )
            self._table.setCellWidget(row_index, 6, remove_button)

    def _change_state(self, ticker: str, state: str) -> None:
        if self._coordinator.busy:
            return
        self._service.set_state(ticker, WatchlistState(state))

    def _remove_ticker(self, ticker: str) -> None:
        if self._coordinator.busy:
            return

        answer = QMessageBox.question(
            self,
            "Remover da Watchlist",
            f"Remover {ticker} da Watchlist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._service.remove_ticker(ticker)
        self._refresh_table()
