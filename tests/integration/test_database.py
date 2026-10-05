from sqlalchemy import inspect

from bolsa.infrastructure.database import create_database_engine, initialize_database


def test_database_initialization_creates_initial_schema() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    initialize_database(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "instruments",
        "watchlists",
        "watchlist_items",
    }
