from __future__ import annotations

from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import inspect

from bolsa.config import AppConfig, prepare_environment
from bolsa.infrastructure.database import (
    BASELINE_REVISION,
    SchemaCompatibilityError,
    SchemaMigrationStatus,
    SchemaRevisionError,
    create_database_engine,
    ensure_database_schema,
    get_database_revision,
    get_schema_head_revision,
    validate_sqlite_database,
)
import bolsa.infrastructure.database.schema_migrations as schema_migrations


def _legacy_v02_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE instruments (
                id INTEGER NOT NULL,
                ticker VARCHAR(32) NOT NULL,
                name VARCHAR(255),
                market VARCHAR(64),
                currency VARCHAR(3),
                asset_type VARCHAR(32) NOT NULL,
                PRIMARY KEY (id)
            );
            CREATE UNIQUE INDEX ix_instruments_ticker
                ON instruments (ticker);

            CREATE TABLE watchlists (
                id INTEGER NOT NULL,
                name VARCHAR(120) NOT NULL,
                PRIMARY KEY (id)
            );
            CREATE UNIQUE INDEX ix_watchlists_name
                ON watchlists (name);

            CREATE TABLE watchlist_items (
                id INTEGER NOT NULL,
                watchlist_id INTEGER NOT NULL,
                instrument_id INTEGER NOT NULL,
                state VARCHAR(32) NOT NULL,
                notes TEXT NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_watchlist_instrument
                    UNIQUE (watchlist_id, instrument_id),
                FOREIGN KEY(instrument_id)
                    REFERENCES instruments (id) ON DELETE CASCADE,
                FOREIGN KEY(watchlist_id)
                    REFERENCES watchlists (id) ON DELETE CASCADE
            );
            CREATE INDEX ix_watchlist_items_instrument_id
                ON watchlist_items (instrument_id);
            CREATE INDEX ix_watchlist_items_watchlist_id
                ON watchlist_items (watchlist_id);

            INSERT INTO instruments
                (id, ticker, name, market, currency, asset_type)
            VALUES
                (1, 'AAPL', 'Apple Inc.', 'US', 'USD', 'stock');

            INSERT INTO watchlists (id, name)
            VALUES (1, 'Principal');

            INSERT INTO watchlist_items
                (id, watchlist_id, instrument_id, state, notes)
            VALUES
                (1, 1, 1, 'candidate', '');
            """
        )
        connection.commit()


def _legacy_value(path: Path) -> tuple[str, str]:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(
            """
            SELECT instruments.ticker, watchlist_items.state
            FROM watchlist_items
            JOIN instruments
              ON instruments.id = watchlist_items.instrument_id
            WHERE watchlist_items.id = 1
            """
        ).fetchone()


def test_new_database_is_created_at_head(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)

    result = ensure_database_schema(config)

    assert result.status is SchemaMigrationStatus.CREATED
    assert result.backup_path is None
    assert result.current_revision == get_schema_head_revision()
    assert get_database_revision(config.database_path) == result.current_revision

    engine = create_database_engine(config.database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version",
            "instruments",
            "watchlists",
            "watchlist_items",
        }
    finally:
        engine.dispose()


def test_empty_existing_database_is_created_at_head(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    config.database_path.touch()

    result = ensure_database_schema(config)

    assert result.status is SchemaMigrationStatus.CREATED
    assert get_database_revision(config.database_path) == result.head_revision


def test_legacy_v02_is_validated_backed_up_and_stamped(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    _legacy_v02_database(config.database_path)

    result = ensure_database_schema(
        config,
        now=datetime(2026, 10, 8, 2, 0, 0),
    )

    assert result.status is SchemaMigrationStatus.STAMPED_BASELINE
    assert result.current_revision == BASELINE_REVISION
    assert result.backup_path == (
        config.backups_dir
        / "bolsanext_before_migration_0001_v02_baseline_20261008_020000.sqlite3"
    )
    assert result.backup_path.is_file()
    assert _legacy_value(config.database_path) == ("AAPL", "candidate")
    assert _legacy_value(result.backup_path) == ("AAPL", "candidate")
    assert get_database_revision(config.database_path) == BASELINE_REVISION
    validate_sqlite_database(config.database_path)
    validate_sqlite_database(result.backup_path)


def test_database_already_at_head_is_not_backed_up_again(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)

    ensure_database_schema(config)
    before = list(config.backups_dir.glob("*.sqlite3"))

    result = ensure_database_schema(config)

    after = list(config.backups_dir.glob("*.sqlite3"))
    assert result.status is SchemaMigrationStatus.CURRENT
    assert before == after


def test_incompatible_unversioned_schema_is_rejected(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)

    with closing(sqlite3.connect(config.database_path)) as connection:
        connection.execute("CREATE TABLE unexpected (id INTEGER PRIMARY KEY)")
        connection.commit()

    with pytest.raises(SchemaCompatibilityError):
        ensure_database_schema(config)

    assert get_database_revision(config.database_path) is None
    assert list(config.backups_dir.glob("*.sqlite3")) == []


def test_unknown_revision_is_rejected_without_new_backup(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    ensure_database_schema(config)

    with closing(sqlite3.connect(config.database_path)) as connection:
        connection.execute(
            "UPDATE alembic_version SET version_num = ?",
            ("9999_future_revision",),
        )
        connection.commit()

    before = list(config.backups_dir.glob("*.sqlite3"))

    with pytest.raises(SchemaRevisionError):
        ensure_database_schema(config)

    assert list(config.backups_dir.glob("*.sqlite3")) == before


def test_stamp_failure_preserves_original_and_backup(
    tmp_path,
    monkeypatch,
) -> None:
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    _legacy_v02_database(config.database_path)

    def fail_stamp(_path, _revision):
        raise RuntimeError("simulated stamp failure")

    monkeypatch.setattr(schema_migrations, "_run_stamp", fail_stamp)

    with pytest.raises(RuntimeError, match="simulated"):
        ensure_database_schema(
            config,
            now=datetime(2026, 10, 8, 2, 30, 0),
        )

    backup = (
        config.backups_dir
        / "bolsanext_before_migration_0001_v02_baseline_20261008_023000.sqlite3"
    )
    assert backup.is_file()
    assert _legacy_value(config.database_path) == ("AAPL", "candidate")
    assert _legacy_value(backup) == ("AAPL", "candidate")
    validate_sqlite_database(config.database_path)
    validate_sqlite_database(backup)


def test_runtime_database_code_does_not_use_create_all() -> None:
    database_dir = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "bolsa"
        / "infrastructure"
        / "database"
    )

    offenders = []
    for path in database_dir.rglob("*.py"):
        if "create_all(" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)

    assert offenders == []
