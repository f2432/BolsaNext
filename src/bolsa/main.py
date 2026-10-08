from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from bolsa.app.services import MarketService, UniverseService, WatchlistService
from bolsa.config import load_config, prepare_environment
from bolsa.domain.watchlist import Watchlist
from bolsa.infrastructure.database import (
    LegacyDatabaseMigrationRequiredError,
    SchemaMigrationError,
    create_database_engine,
    create_session_factory,
    ensure_database_location_ready,
    ensure_database_schema,
)
from bolsa.infrastructure.market_data import (
    CachedUniverseProvider,
    WikipediaUniverseProvider,
    YFinanceMarketDataProvider,
)
from bolsa.infrastructure.repositories import SqlAlchemyWatchlistRepository
from bolsa.logging_config import configure_logging
from bolsa.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    config = load_config()

    try:
        ensure_database_location_ready(config)
    except LegacyDatabaseMigrationRequiredError as exc:
        logger.error("%s", exc)
        print(str(exc), file=sys.stderr)
        return 2

    prepare_environment(config)

    try:
        schema_result = ensure_database_schema(config)
    except SchemaMigrationError as exc:
        logger.error("Falha ao validar/migrar schema: %s", exc)
        print(f"Erro de schema: {exc}", file=sys.stderr)
        return 3

    if schema_result.backup_path is not None:
        logger.info(
            "Schema atualizado para %s; backup preservado em %s",
            schema_result.current_revision,
            schema_result.backup_path,
        )

    engine = create_database_engine(config.database_url)

    try:
        session_factory = create_session_factory(engine)

        watchlist_repository = SqlAlchemyWatchlistRepository(session_factory)
        watchlist = watchlist_repository.load("Principal") or Watchlist("Principal")

        market_service = MarketService(YFinanceMarketDataProvider())
        universe_service = UniverseService(
            CachedUniverseProvider(
                WikipediaUniverseProvider(),
                config.cache_dir / "universes",
            )
        )
        watchlist_service = WatchlistService(
            watchlist,
            market_service,
            repository=watchlist_repository,
        )

        logger.info(
            "A iniciar %s com dados em %s (schema %s)",
            config.app_name,
            config.data_dir,
            schema_result.current_revision,
        )

        app = QApplication(sys.argv)
        window = MainWindow(
            config.app_name,
            watchlist_service=watchlist_service,
            universe_service=universe_service,
        )
        window.show()

        return app.exec()
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
