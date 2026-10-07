from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

import pytest

from bolsa.config import AppConfig
from bolsa.infrastructure.database import (
    DataLocationError,
    LegacyDatabaseMigrationRequiredError,
    build_data_location_migration_plan,
    ensure_database_location_ready,
    execute_data_location_migration,
    validate_sqlite_database,
)


def _create_source_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO sample (value) VALUES (?)",
            ("preserved",),
        )
        connection.commit()


def _read_value(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT value FROM sample WHERE id = 1"
        ).fetchone()[0]


def test_pending_legacy_database_blocks_silent_blank_database(tmp_path) -> None:
    source = tmp_path / "repo" / "data" / "bolsanext.sqlite3"
    destination = tmp_path / "user-data" / "bolsanext.sqlite3"
    _create_source_database(source)

    config = AppConfig(data_dir=destination.parent)

    with pytest.raises(LegacyDatabaseMigrationRequiredError):
        ensure_database_location_ready(config, legacy_path=source)

    assert not destination.exists()


def test_override_data_directory_does_not_require_legacy_migration(tmp_path) -> None:
    source = tmp_path / "repo" / "data" / "bolsanext.sqlite3"
    _create_source_database(source)

    config = AppConfig(
        data_dir=tmp_path / "explicit",
        data_dir_is_override=True,
    )

    ensure_database_location_ready(config, legacy_path=source)


def test_data_location_migration_preserves_source_backup_and_destination(
    tmp_path,
) -> None:
    source = tmp_path / "repo" / "data" / "bolsanext.sqlite3"
    _create_source_database(source)

    config = AppConfig(data_dir=tmp_path / "user-data")
    plan = build_data_location_migration_plan(
        config,
        source=source,
        now=datetime(2026, 10, 8, 0, 30, 0),
    )

    result = execute_data_location_migration(plan)

    assert result.source == source
    assert result.destination == config.database_path
    assert result.backup == (
        config.backups_dir / "bolsanext_before_move_20261008_003000.sqlite3"
    )

    assert source.is_file()
    assert result.backup.is_file()
    assert result.destination.is_file()

    validate_sqlite_database(source)
    validate_sqlite_database(result.backup)
    validate_sqlite_database(result.destination)

    assert _read_value(source) == "preserved"
    assert _read_value(result.backup) == "preserved"
    assert _read_value(result.destination) == "preserved"


def test_existing_destination_blocks_migration_without_overwrite(tmp_path) -> None:
    source = tmp_path / "repo" / "data" / "bolsanext.sqlite3"
    _create_source_database(source)

    config = AppConfig(data_dir=tmp_path / "user-data")
    config.data_dir.mkdir(parents=True)
    _create_source_database(config.database_path)

    plan = build_data_location_migration_plan(
        config,
        source=source,
        now=datetime(2026, 10, 8, 0, 30, 0),
    )

    with pytest.raises(FileExistsError, match="já contém uma base"):
        execute_data_location_migration(plan)

    assert not plan.backup.exists()
    assert _read_value(source) == "preserved"
    assert _read_value(config.database_path) == "preserved"


def test_invalid_source_database_is_rejected_before_backup(tmp_path) -> None:
    source = tmp_path / "repo" / "data" / "bolsanext.sqlite3"
    source.parent.mkdir(parents=True)
    source.write_text("not sqlite", encoding="utf-8")

    config = AppConfig(data_dir=tmp_path / "user-data")
    plan = build_data_location_migration_plan(
        config,
        source=source,
        now=datetime(2026, 10, 8, 0, 30, 0),
    )

    with pytest.raises(DataLocationError):
        execute_data_location_migration(plan)

    assert not plan.backup.exists()
    assert not plan.destination.exists()
