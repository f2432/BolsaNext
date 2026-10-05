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

from bolsa.app.services.watchlist_service import WatchlistService
from bolsa.domain.watchlist import WatchlistState


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

        layout = QVBoxLayout(self)

        title = QLabel(f"Watchlist: {service.name}")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Ticker, por exemplo AAPL")
        self._ticker_input.returnPressed.connect(self._add_ticker)
        controls.addWidget(self._ticker_input)

        add_button = QPushButton("Adicionar")
        add_button.clicked.connect(self._add_ticker)
        controls.addWidget(add_button)

        refresh_button = QPushButton("Atualizar preços")
        refresh_button.clicked.connect(lambda: self._refresh_table(refresh_prices=True))
        controls.addWidget(refresh_button)

        layout.addLayout(controls)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Ticker", "Nome", "Estado", "Preço atual", "Ações"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        self._refresh_table()

    def _add_ticker(self) -> None:
        ticker = self._ticker_input.text().strip()
        if not ticker:
            return

        try:
            self._service.add_ticker(ticker)
        except ValueError as exc:
            QMessageBox.warning(self, "Watchlist", str(exc))
            return

        self._ticker_input.clear()
        self._refresh_table()

    def refresh(self, *, refresh_prices: bool = False) -> None:
        self._refresh_table(refresh_prices=refresh_prices)

    def _refresh_table(self, *, refresh_prices: bool = False) -> None:
        rows = self._service.rows(refresh_prices=refresh_prices)
        self._table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            self._table.setItem(row_index, 0, QTableWidgetItem(row.ticker))
            self._table.setItem(
                row_index,
                1,
                QTableWidgetItem(row.name or ""),
            )

            state_combo = QComboBox()
            for state, label in _STATE_LABELS.items():
                state_combo.addItem(label, state.value)
            state_combo.setCurrentIndex(state_combo.findData(row.state.value))
            state_combo.currentIndexChanged.connect(
                lambda _index, ticker=row.ticker, combo=state_combo: (
                    self._change_state(ticker, combo.currentData())
                )
            )
            self._table.setCellWidget(row_index, 2, state_combo)

            price_text = "—" if row.price is None else f"{row.price:.2f}"
            self._table.setItem(
                row_index,
                3,
                QTableWidgetItem(price_text),
            )

            remove_button = QPushButton("Remover")
            remove_button.clicked.connect(
                lambda _checked=False, ticker=row.ticker: self._remove_ticker(ticker)
            )
            self._table.setCellWidget(row_index, 4, remove_button)

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
