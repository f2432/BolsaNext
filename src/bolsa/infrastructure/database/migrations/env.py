from __future__ import annotations

from alembic import context

from bolsa.infrastructure.database.base import Base
import bolsa.infrastructure.database.models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    raise RuntimeError(
        "As migrations do BolsaNext são executadas com uma ligação explícita."
    )


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is None:
        raise RuntimeError(
            "A configuração Alembic não recebeu uma ligação à base de dados."
        )

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
