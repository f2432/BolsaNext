from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from bolsa.app.services import MarketService, UniverseService, WatchlistService
from bolsa.config import load_config
from bolsa.domain.watchlist import Watchlist
from bolsa.infrastructure.database import create_database_engine, initialize_database
from bolsa.infrastructure.market_data import (
    WikipediaUniverseProvider,
    YFinanceMarketDataProvider,
)
from bolsa.logging_config import configure_logging
from bolsa.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    config = load_config()

    engine = create_database_engine(config.database_url)
    initialize_database(engine)

    market_service = MarketService(YFinanceMarketDataProvider())
    universe_service = UniverseService(WikipediaUniverseProvider())
    watchlist_service = WatchlistService(
        Watchlist("Principal"),
        market_service,
    )

    logger.info("A iniciar %s", config.app_name)

    app = QApplication(sys.argv)
    window = MainWindow(
        config.app_name,
        watchlist_service=watchlist_service,
        universe_service=universe_service,
    )
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
