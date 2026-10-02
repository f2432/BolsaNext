from sqlalchemy import inspect

from bolsa.infrastructure.database import create_database_engine, initialize_database


def test_database_initialization_with_in_memory_sqlite() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    initialize_database(engine)

    inspector = inspect(engine)
    assert inspector.get_table_names() == []
