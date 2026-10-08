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
from bolsa.version import version_label


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
            watchlist_widget = WatchlistWidget(watchlist_service)
            watchlist_area.addTab(watchlist_widget, "A minha Watchlist")

            if universe_service is not None:
                universe_widget = UniverseWidget(universe_service, watchlist_service)
                universe_widget.instrument_added.connect(
                    lambda _ticker: watchlist_widget.refresh()
                )
                watchlist_area.addTab(universe_widget, "Universos")

            watchlist_area.currentChanged.connect(
                lambda index: watchlist_widget.refresh() if index == 0 else None
            )
            tabs.addTab(watchlist_area, "Watchlist")

        tabs.addTab(self._placeholder("Carteira"), "Carteira")
        tabs.addTab(self._placeholder("Análise"), "Análise")
        tabs.addTab(self._placeholder("Backtesting"), "Backtesting")
        tabs.addTab(self._placeholder("IA"), "IA")

        self.setCentralWidget(tabs)

        status = QStatusBar()
        status.showMessage(version_label("Market Data"))
        self.setStatusBar(status)

    @staticmethod
    def _placeholder(title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(f"{title}\n\nMódulo em preparação.")
        layout.addWidget(label)
        layout.addStretch()
        return widget
