from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import re
import sqlite3

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.script.revision import RangeNotAncestorError, ResolutionError
from sqlalchemy import inspect

from bolsa.config import AppConfig
from bolsa.infrastructure.database.data_location import (
    create_validated_database_backup,
    validate_sqlite_database,
)
from bolsa.infrastructure.database.session import create_database_engine

BASELINE_REVISION = "0001_v02_baseline"


class SchemaMigrationError(RuntimeError):
    """Erro base do mecanismo de evolução do schema."""


class SchemaCompatibilityError(SchemaMigrationError):
    """A estrutura da base não corresponde a um schema conhecido."""


class SchemaRevisionError(SchemaMigrationError):
    """A revisão Alembic da base não é suportada por este código."""


class SchemaMigrationStatus(StrEnum):
    CREATED = "created"
    STAMPED_BASELINE = "stamped_baseline"
    CURRENT = "current"
    UPGRADED = "upgraded"


@dataclass(frozen=True, slots=True)
class SchemaMigrationResult:
    status: SchemaMigrationStatus
    previous_revision: str | None
    current_revision: str
    head_revision: str
    backup_path: Path | None = None


_EXPECTED_TABLES = {
    "instruments",
    "watchlists",
    "watchlist_items",
}

_EXPECTED_COLUMNS: dict[str, dict[str, str]] = {
    "instruments": {
        "id": "INTEGER",
        "ticker": "VARCHAR(32)",
        "name": "VARCHAR(255)",
        "market": "VARCHAR(64)",
        "currency": "VARCHAR(3)",
        "asset_type": "VARCHAR(32)",
    },
    "watchlists": {
        "id": "INTEGER",
        "name": "VARCHAR(120)",
    },
    "watchlist_items": {
        "id": "INTEGER",
        "watchlist_id": "INTEGER",
        "instrument_id": "INTEGER",
        "state": "VARCHAR(32)",
        "notes": "TEXT",
    },
}

_EXPECTED_PRIMARY_KEYS = {
    "instruments": {"id"},
    "watchlists": {"id"},
    "watchlist_items": {"id"},
}

_REQUIRED_NON_NULL = {
    "instruments": {"ticker", "asset_type"},
    "watchlists": {"name"},
    "watchlist_items": {
        "watchlist_id",
        "instrument_id",
        "state",
        "notes",
    },
}


def _migrations_dir() -> Path:
    return Path(__file__).with_name("migrations")


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(_migrations_dir()))
    return config


def get_schema_head_revision() -> str:
    try:
        head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    except Exception as exc:
        raise SchemaRevisionError(
            "Não foi possível determinar a revisão Alembic atual do código."
        ) from exc

    if head is None:
        raise SchemaRevisionError("O projeto não contém uma revisão Alembic head.")
    return head


def _read_revision(path: Path) -> tuple[bool, str | None]:
    if not path.exists() or path.stat().st_size == 0:
        return False, None

    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='alembic_version'"
        ).fetchone()

        if exists is None:
            return False, None

        rows = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()

    if len(rows) != 1 or not rows[0][0]:
        raise SchemaRevisionError(
            "A tabela alembic_version existe, mas não contém uma revisão válida."
        )

    return True, str(rows[0][0])


def get_database_revision(path: Path) -> str | None:
    has_table, revision = _read_revision(path)
    if not has_table:
        return None
    return revision


def _run_alembic(path: Path, operation, revision: str) -> None:
    engine = create_database_engine(
        f"sqlite:///{path.resolve().as_posix()}"
    )
    try:
        with engine.connect() as connection:
            config = _alembic_config()
            config.attributes["connection"] = connection
            operation(config, revision)
    finally:
        engine.dispose()


def _run_upgrade(path: Path, revision: str = "head") -> None:
    _run_alembic(path, command.upgrade, revision)


def _run_stamp(path: Path, revision: str) -> None:
    _run_alembic(path, command.stamp, revision)


def _safe_revision_fragment(revision: str) -> str:
    fragment = re.sub(r"[^A-Za-z0-9_.-]+", "_", revision)
    return fragment[:80] or "unknown"


def _migration_backup_path(
    config: AppConfig,
    target_revision: str,
    *,
    now: datetime | None = None,
) -> Path:
    timestamp = (now or datetime.now().astimezone()).strftime("%Y%m%d_%H%M%S")
    target = _safe_revision_fragment(target_revision)
    stem = Path(config.database_name).stem
    return (
        config.backups_dir
        / f"{stem}_before_migration_{target}_{timestamp}.sqlite3"
    )


def _unique_column_sets(inspector, table: str) -> set[frozenset[str]]:
    result: set[frozenset[str]] = set()

    for constraint in inspector.get_unique_constraints(table):
        columns = constraint.get("column_names") or []
        if columns:
            result.add(frozenset(columns))

    for index in inspector.get_indexes(table):
        if index.get("unique"):
            columns = index.get("column_names") or []
            if columns:
                result.add(frozenset(columns))

    return result


def _validate_baseline_schema(path: Path) -> None:
    engine = create_database_engine(
        f"sqlite:///{path.resolve().as_posix()}"
    )
    try:
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())
        if actual_tables != _EXPECTED_TABLES:
            raise SchemaCompatibilityError(
                "A base sem Alembic não corresponde à baseline V0.2. "
                f"Tabelas encontradas: {sorted(actual_tables)}"
            )

        for table, expected_columns in _EXPECTED_COLUMNS.items():
            columns = {
                column["name"]: column
                for column in inspector.get_columns(table)
            }
            if set(columns) != set(expected_columns):
                raise SchemaCompatibilityError(
                    f"Colunas incompatíveis na tabela {table}: "
                    f"{sorted(columns)}"
                )

            for name, expected_type in expected_columns.items():
                actual_type = str(columns[name]["type"]).upper()
                if actual_type != expected_type:
                    raise SchemaCompatibilityError(
                        f"Tipo incompatível em {table}.{name}: "
                        f"{actual_type} != {expected_type}"
                    )

            for name in _REQUIRED_NON_NULL[table]:
                if columns[name].get("nullable", True):
                    raise SchemaCompatibilityError(
                        f"A coluna {table}.{name} devia ser NOT NULL."
                    )

            primary_key = set(
                inspector.get_pk_constraint(table).get(
                    "constrained_columns"
                ) or []
            )
            if primary_key != _EXPECTED_PRIMARY_KEYS[table]:
                raise SchemaCompatibilityError(
                    f"Primary key incompatível em {table}: "
                    f"{sorted(primary_key)}"
                )

        instrument_unique = _unique_column_sets(
            inspector,
            "instruments",
        )
        if frozenset({"ticker"}) not in instrument_unique:
            raise SchemaCompatibilityError(
                "A baseline V0.2 exige unicidade de instruments.ticker."
            )

        watchlist_unique = _unique_column_sets(
            inspector,
            "watchlists",
        )
        if frozenset({"name"}) not in watchlist_unique:
            raise SchemaCompatibilityError(
                "A baseline V0.2 exige unicidade de watchlists.name."
            )

        item_unique = _unique_column_sets(
            inspector,
            "watchlist_items",
        )
        if frozenset({"watchlist_id", "instrument_id"}) not in item_unique:
            raise SchemaCompatibilityError(
                "A baseline V0.2 exige unicidade por watchlist/instrument."
            )

        foreign_keys = inspector.get_foreign_keys("watchlist_items")
        expected_fks = {
            (
                ("watchlist_id",),
                "watchlists",
                ("id",),
                "CASCADE",
            ),
            (
                ("instrument_id",),
                "instruments",
                ("id",),
                "CASCADE",
            ),
        }
        actual_fks = {
            (
                tuple(fk.get("constrained_columns") or []),
                str(fk.get("referred_table") or ""),
                tuple(fk.get("referred_columns") or []),
                str((fk.get("options") or {}).get("ondelete") or "").upper(),
            )
            for fk in foreign_keys
        }

        if actual_fks != expected_fks:
            raise SchemaCompatibilityError(
                "Foreign keys da baseline V0.2 não correspondem ao esperado."
            )
    finally:
        engine.dispose()


def _assert_revision_can_upgrade(current: str, head: str) -> None:
    script = ScriptDirectory.from_config(_alembic_config())

    try:
        script.get_revision(current)
        list(script.iterate_revisions(head, current))
    except (ResolutionError, RangeNotAncestorError) as exc:
        raise SchemaRevisionError(
            f"A revisão da base {current!r} não pertence ao caminho "
            f"de migração suportado até {head!r}."
        ) from exc
    except Exception as exc:
        raise SchemaRevisionError(
            f"Não foi possível validar a revisão {current!r}."
        ) from exc


def _validate_revision(path: Path, expected: str) -> None:
    validate_sqlite_database(path)
    current = get_database_revision(path)
    if current != expected:
        raise SchemaRevisionError(
            f"A base ficou na revisão {current!r}; esperava-se {expected!r}."
        )


def ensure_database_schema(
    config: AppConfig,
    *,
    now: datetime | None = None,
) -> SchemaMigrationResult:
    """Garante que a base está no head conhecido, com backup quando necessário."""

    path = config.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    config.backups_dir.mkdir(parents=True, exist_ok=True)

    head = get_schema_head_revision()

    if not path.exists() or path.stat().st_size == 0:
        previous = None
        _run_upgrade(path, "head")
        _validate_revision(path, head)
        return SchemaMigrationResult(
            status=SchemaMigrationStatus.CREATED,
            previous_revision=previous,
            current_revision=head,
            head_revision=head,
        )

    validate_sqlite_database(path)
    has_version_table, current = _read_revision(path)

    if not has_version_table:
        _validate_baseline_schema(path)

        backup = _migration_backup_path(
            config,
            BASELINE_REVISION,
            now=now,
        )
        create_validated_database_backup(path, backup)

        _run_stamp(path, BASELINE_REVISION)

        if head != BASELINE_REVISION:
            _assert_revision_can_upgrade(BASELINE_REVISION, head)
            _run_upgrade(path, "head")
            status = SchemaMigrationStatus.UPGRADED
        else:
            status = SchemaMigrationStatus.STAMPED_BASELINE

        _validate_revision(path, head)
        return SchemaMigrationResult(
            status=status,
            previous_revision=None,
            current_revision=head,
            head_revision=head,
            backup_path=backup,
        )

    if current is None:
        raise SchemaRevisionError(
            "A base contém alembic_version sem uma revisão válida."
        )

    if current == head:
        return SchemaMigrationResult(
            status=SchemaMigrationStatus.CURRENT,
            previous_revision=current,
            current_revision=current,
            head_revision=head,
        )

    _assert_revision_can_upgrade(current, head)

    backup = _migration_backup_path(
        config,
        head,
        now=now,
    )
    create_validated_database_backup(path, backup)

    _run_upgrade(path, "head")
    _validate_revision(path, head)

    return SchemaMigrationResult(
        status=SchemaMigrationStatus.UPGRADED,
        previous_revision=current,
        current_revision=head,
        head_revision=head,
        backup_path=backup,
    )
