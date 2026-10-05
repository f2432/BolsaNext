from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from bolsa.infrastructure.database.base import Base


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    # Import registers all ORM mappings in Base.metadata before create_all.
    from bolsa.infrastructure.database import models  # noqa: F401

    Base.metadata.create_all(engine)
