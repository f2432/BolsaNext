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
from bolsa.ui.watchlist import (
    UniverseWidget,
    WatchlistOperationCoordinator,
    WatchlistWidget,
)
from bolsa.version import version_label


class MainWindow(QMainWindow):
    def __init__(
        self,
        app_name: str = "BolsaNext",
        watchlist_service: WatchlistService | None = None,
        universe_service: UniverseService | None = None,
        portfolio_dashboard_service=None,
        default_base_currency: str = "EUR",
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
            operation_coordinator = WatchlistOperationCoordinator(self)
            watchlist_widget = WatchlistWidget(
                watchlist_service,
                coordinator=operation_coordinator,
            )
            watchlist_area.addTab(watchlist_widget, "A minha Watchlist")

            if universe_service is not None:
                universe_widget = UniverseWidget(
                    universe_service,
                    watchlist_service,
                    coordinator=operation_coordinator,
                )
                universe_widget.instrument_added.connect(
                    lambda _ticker: watchlist_widget.refresh()
                )
                watchlist_area.addTab(universe_widget, "Universos")

            watchlist_area.currentChanged.connect(
                lambda index: watchlist_widget.refresh() if index == 0 else None
            )
            tabs.addTab(watchlist_area, "Watchlist")

        self.portfolio_widget = None
        if portfolio_dashboard_service is None:
            tabs.addTab(self._placeholder("Carteira"), "Carteira")
        else:
            from bolsa.ui.portfolio.widget import PortfolioWidget
            self.portfolio_widget = PortfolioWidget(portfolio_dashboard_service,default_base_currency)
            tabs.addTab(self.portfolio_widget,"Carteira")
        tabs.addTab(self._placeholder("Análise"), "Análise")
        tabs.addTab(self._placeholder("Backtesting"), "Backtesting")
        tabs.addTab(self._placeholder("IA"), "IA")

        self.setCentralWidget(tabs)

        status = QStatusBar()
        status.showMessage(version_label("Portfolio em desenvolvimento") if portfolio_dashboard_service else version_label("Market Data"))
        self.setStatusBar(status)

    @staticmethod
    def _placeholder(title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(f"{title}\n\nMódulo em preparação.")
        layout.addWidget(label)
        layout.addStretch()
        return widget

    def closeEvent(self,event):
        if self.portfolio_widget is not None and self.portfolio_widget.busy:
            self.statusBar().showMessage("Aguarda o fim da operação de carteira antes de fechar.")
            event.ignore()
            return
        super().closeEvent(event)
