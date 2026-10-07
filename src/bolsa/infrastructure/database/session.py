from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from bolsa.infrastructure.database.base import Base

_SQLITE_BUSY_TIMEOUT_MS = 5000


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    engine = create_engine(database_url, echo=echo)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.execute(
                    f"PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}"
                )
            finally:
                cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    # Import registers all ORM mappings in Base.metadata before create_all.
    from bolsa.infrastructure.database import models  # noqa: F401

    Base.metadata.create_all(engine)
