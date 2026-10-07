from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
import uuid

from bolsa.config import AppConfig


class DataLocationError(RuntimeError):
    """Erro base para validação/migração da localização dos dados."""


class LegacyDatabaseMigrationRequiredError(DataLocationError):
    def __init__(self, source: Path, destination: Path) -> None:
        self.source = source
        self.destination = destination
        super().__init__(
            "Existe uma base antiga no repositório e a nova localização ainda "
            "não tem base de dados. A migração deve ser executada explicitamente.\n"
            f"Origem: {source}\n"
            f"Destino: {destination}\n"
            "Executa primeiro: python -m bolsa.tools.migrate_data_dir"
        )


@dataclass(frozen=True, slots=True)
class DataLocationMigrationPlan:
    source: Path
    destination: Path
    backup: Path


@dataclass(frozen=True, slots=True)
class DataLocationMigrationResult:
    source: Path
    destination: Path
    backup: Path


def _find_repository_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


def legacy_database_path(database_name: str = "bolsanext.sqlite3") -> Path:
    repository_root = _find_repository_root()
    if repository_root is None:
        return Path.cwd() / "data" / database_name
    return repository_root / "data" / database_name


def ensure_database_location_ready(
    config: AppConfig,
    *,
    legacy_path: Path | None = None,
) -> None:
    if config.data_dir_is_override:
        return

    source = legacy_path or legacy_database_path(config.database_name)
    destination = config.database_path

    try:
        same_path = source.resolve() == destination.resolve()
    except OSError:
        same_path = source == destination

    if not same_path and source.exists() and not destination.exists():
        raise LegacyDatabaseMigrationRequiredError(source, destination)


def build_data_location_migration_plan(
    config: AppConfig,
    *,
    source: Path | None = None,
    now: datetime | None = None,
) -> DataLocationMigrationPlan:
    source_path = source or legacy_database_path(config.database_name)
    timestamp = (now or datetime.now().astimezone()).strftime("%Y%m%d_%H%M%S")
    backup_name = (
        f"{Path(config.database_name).stem}_before_move_{timestamp}.sqlite3"
    )

    return DataLocationMigrationPlan(
        source=source_path,
        destination=config.database_path,
        backup=config.backups_dir / backup_name,
    )


def validate_sqlite_database(path: Path) -> None:
    if not path.is_file():
        raise DataLocationError(f"A base SQLite não existe: {path}")

    if path.stat().st_size <= 0:
        raise DataLocationError(f"A base SQLite está vazia: {path}")

    uri = f"file:{path.resolve().as_posix()}?mode=ro"

    try:
        with sqlite3.connect(uri, uri=True) as connection:
            row = connection.execute("PRAGMA quick_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise DataLocationError(
            f"Não foi possível abrir/validar a base SQLite: {path}"
        ) from exc

    if row is None or row[0] != "ok":
        detail = "sem resultado" if row is None else str(row[0])
        raise DataLocationError(
            f"PRAGMA quick_check falhou em {path}: {detail}"
        )


def _sqlite_backup_atomic(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"O destino já existe: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(
        f".{target.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        source_uri = f"file:{source.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source_connection:
            with sqlite3.connect(temp) as target_connection:
                source_connection.backup(target_connection)

        validate_sqlite_database(temp)
        temp.replace(target)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def execute_data_location_migration(
    plan: DataLocationMigrationPlan,
) -> DataLocationMigrationResult:
    if plan.destination.exists():
        raise FileExistsError(
            "A nova localização já contém uma base. "
            f"Nada foi substituído: {plan.destination}"
        )

    if plan.backup.exists():
        raise FileExistsError(
            f"O ficheiro de backup já existe: {plan.backup}"
        )

    validate_sqlite_database(plan.source)

    _sqlite_backup_atomic(plan.source, plan.backup)
    validate_sqlite_database(plan.backup)

    _sqlite_backup_atomic(plan.backup, plan.destination)
    validate_sqlite_database(plan.destination)

    return DataLocationMigrationResult(
        source=plan.source,
        destination=plan.destination,
        backup=plan.backup,
    )
