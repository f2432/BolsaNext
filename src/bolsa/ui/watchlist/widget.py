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
from bolsa.ui.workers import FunctionThread


_STATE_LABELS = {
    WatchlistState.IDEA: "Ideia",
    WatchlistState.ANALYSING: "Em análise",
    WatchlistState.CANDIDATE: "Candidato",
    WatchlistState.REJECTED: "Rejeitado",
    WatchlistState.REVIEW: "Em revisão",
}


class WatchlistWidget(QWidget):
    def __init__(self, service: WatchlistService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._price_thread: FunctionThread | None = None
        self._metadata_thread: FunctionThread | None = None
        self._add_thread: FunctionThread | None = None

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
            ["Ticker", "Nome", "Mercado", "Moeda", "Estado", "Preço atual", "Ações"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        enable_table_header_persistence(self._table, "watchlist/main")
        layout.addWidget(self._table)

        self._refresh_table()

    def _add_ticker(self) -> None:
        ticker = self._ticker_input.text().strip()
        if not ticker or self._add_thread is not None:
            return

        self._status.setText(f"A obter dados de {ticker.upper()}...")
        self._ticker_input.setEnabled(False)
        self._add_button.setEnabled(False)

        thread = FunctionThread(self._service.add_ticker_enriched, ticker)
        thread.result_ready.connect(self._manual_add_complete)
        thread.failed.connect(self._manual_add_failed)
        thread.finished.connect(self._manual_add_finished)
        self._add_thread = thread
        thread.start()

    def _manual_add_complete(self, instrument: Instrument) -> None:
        self._ticker_input.clear()
        self._refresh_table()
        self._status.setText(f"{instrument.ticker} adicionado.")

    def _manual_add_failed(self, message: str) -> None:
        self._status.setText("Não foi possível adicionar o ativo.")
        QMessageBox.warning(self, "Watchlist", message)

    def _manual_add_finished(self) -> None:
        self._ticker_input.setEnabled(True)
        self._add_button.setEnabled(True)
        if self._add_thread is not None:
            self._add_thread.deleteLater()
        self._add_thread = None
        self._ticker_input.setFocus()

    def refresh(self, *, refresh_prices: bool = False) -> None:
        if refresh_prices:
            self._start_price_refresh()
        else:
            self._refresh_table()

    def _start_metadata_refresh(self) -> None:
        if self._metadata_thread is not None:
            return

        self._status.setText("A atualizar dados dos ativos...")
        self._metadata_button.setEnabled(False)

        thread = FunctionThread(self._service.refresh_metadata)
        thread.result_ready.connect(self._metadata_refresh_complete)
        thread.failed.connect(self._metadata_refresh_failed)
        thread.finished.connect(self._metadata_refresh_finished)
        self._metadata_thread = thread
        thread.start()

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

    def _metadata_refresh_finished(self) -> None:
        self._metadata_button.setEnabled(True)
        if self._metadata_thread is not None:
            self._metadata_thread.deleteLater()
        self._metadata_thread = None

    def _start_price_refresh(self) -> None:
        if self._price_thread is not None:
            return

        self._status.setText("A atualizar preços...")
        self._refresh_button.setEnabled(False)

        thread = FunctionThread(self._service.rows, refresh_prices=True)
        thread.result_ready.connect(self._price_refresh_complete)
        thread.failed.connect(self._price_refresh_failed)
        thread.finished.connect(self._price_refresh_finished)
        self._price_thread = thread
        thread.start()

    def _price_refresh_complete(self, rows: list[WatchlistRow]) -> None:
        self._render_rows(rows)
        warnings = self._service.price_warnings

        if warnings:
            self._status.setText(
                f"Preços atualizados com {len(warnings)} aviso(s)."
            )
            QMessageBox.warning(
                self,
                "Watchlist",
                "Alguns preços não puderam ser atualizados:\n\n"
                + "\n".join(warnings),
            )
        else:
            self._status.setText("Preços atualizados.")

    def _price_refresh_failed(self, message: str) -> None:
        self._status.setText("Erro ao atualizar preços.")
        QMessageBox.warning(self, "Watchlist", message)

    def _price_refresh_finished(self) -> None:
        self._refresh_button.setEnabled(True)
        if self._price_thread is not None:
            self._price_thread.deleteLater()
        self._price_thread = None

    def _refresh_table(self) -> None:
        self._render_rows(self._service.rows())

    def _render_rows(self, rows: list[WatchlistRow]) -> None:
        self._table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            self._table.setItem(row_index, 0, QTableWidgetItem(row.ticker))
            self._table.setItem(row_index, 1, QTableWidgetItem(row.name or ""))
            self._table.setItem(row_index, 2, QTableWidgetItem(row.market or ""))
            self._table.setItem(row_index, 3, QTableWidgetItem(row.currency or ""))

            state_combo = QComboBox()
            for state, label in _STATE_LABELS.items():
                state_combo.addItem(label, state.value)
            state_combo.setCurrentIndex(state_combo.findData(row.state.value))
            state_combo.currentIndexChanged.connect(
                lambda _index, ticker=row.ticker, combo=state_combo: (
                    self._change_state(ticker, combo.currentData())
                )
            )
            self._table.setCellWidget(row_index, 4, state_combo)

            price_text = "—" if row.price is None else f"{row.price:.2f}"
            self._table.setItem(row_index, 5, QTableWidgetItem(price_text))

            remove_button = QPushButton("Remover")
            remove_button.clicked.connect(
                lambda _checked=False, ticker=row.ticker: self._remove_ticker(ticker)
            )
            self._table.setCellWidget(row_index, 6, remove_button)

    def _change_state(self, ticker: str, state: str) -> None:
        self._service.set_state(ticker, WatchlistState(state))

    def _remove_ticker(self, ticker: str) -> None:
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
