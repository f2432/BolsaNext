from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bolsa.app.services.universe_service import UniverseService
from bolsa.app.services.watchlist_service import WatchlistService
from bolsa.ui.watchlist import UniverseWidget, WatchlistWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        app_name: str = "BolsaNext",
        watchlist_service: WatchlistService | None = None,
        universe_service: UniverseService | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(app_name)
        self.resize(1200, 800)

        tabs = QTabWidget()
        tabs.addTab(self._placeholder("Resumo"), "Resumo")

        if watchlist_service is None:
            tabs.addTab(self._placeholder("Watchlist"), "Watchlist")
        else:
            watchlist_area = QTabWidget()
            watchlist_area.addTab(WatchlistWidget(watchlist_service), "A minha Watchlist")
            if universe_service is not None:
                watchlist_area.addTab(
                    UniverseWidget(universe_service, watchlist_service),
                    "Universos",
                )
            tabs.addTab(watchlist_area, "Watchlist")

        tabs.addTab(self._placeholder("Carteira"), "Carteira")
        tabs.addTab(self._placeholder("Análise"), "Análise")
        tabs.addTab(self._placeholder("Backtesting"), "Backtesting")
        tabs.addTab(self._placeholder("IA"), "IA")

        self.setCentralWidget(tabs)

        status = QStatusBar()
        status.showMessage("V0.2 — Market Data")
        self.setStatusBar(status)

    @staticmethod
    def _placeholder(title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(f"{title}\n\nMódulo em preparação.")
        layout.addWidget(label)
        layout.addStretch()
        return widget
