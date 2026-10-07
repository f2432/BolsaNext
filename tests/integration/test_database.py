import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from bolsa.infrastructure.database import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from bolsa.infrastructure.database.models import (
    InstrumentModel,
    WatchlistItemModel,
    WatchlistModel,
)


def test_database_initialization_creates_initial_schema() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        initialize_database(engine)

        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {
            "instruments",
            "watchlists",
            "watchlist_items",
        }
    finally:
        engine.dispose()


def test_sqlite_engine_enables_foreign_keys_and_busy_timeout() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            foreign_keys = connection.exec_driver_sql(
                "PRAGMA foreign_keys"
            ).scalar_one()
            busy_timeout = connection.exec_driver_sql(
                "PRAGMA busy_timeout"
            ).scalar_one()

        assert foreign_keys == 1
        assert busy_timeout == 5000
    finally:
        engine.dispose()


def test_sqlite_rejects_invalid_foreign_keys() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        initialize_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            session.add(
                WatchlistItemModel(
                    watchlist_id=999,
                    instrument_id=999,
                    state="idea",
                    notes="",
                )
            )

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()

        with session_factory() as session:
            count = session.scalar(
                select(func.count()).select_from(WatchlistItemModel)
            )
            assert count == 0
    finally:
        engine.dispose()


def test_sqlite_on_delete_cascade_removes_watchlist_items_only() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        initialize_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            instrument = InstrumentModel(
                ticker="AAPL",
                name="Apple Inc.",
                market="NASDAQ",
                currency="USD",
                asset_type="stock",
            )
            watchlist = WatchlistModel(name="Principal")
            session.add_all([instrument, watchlist])
            session.flush()

            item = WatchlistItemModel(
                watchlist_id=watchlist.id,
                instrument_id=instrument.id,
                state="idea",
                notes="",
            )
            session.add(item)
            session.commit()
            watchlist_id = watchlist.id

        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM watchlists WHERE id = :id"),
                {"id": watchlist_id},
            )

        with session_factory() as session:
            item_count = session.scalar(
                select(func.count()).select_from(WatchlistItemModel)
            )
            instrument_count = session.scalar(
                select(func.count()).select_from(InstrumentModel)
            )

        assert item_count == 0
        assert instrument_count == 1
    finally:
        engine.dispose()
