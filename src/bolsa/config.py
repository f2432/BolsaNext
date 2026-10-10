from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from platformdirs import user_data_path

_DATA_DIR_ENV = "BOLSANEXT_DATA_DIR"


def _system_data_dir() -> Path:
    return Path(
        user_data_path(
            appname="BolsaNext",
            appauthor=False,
            roaming=False,
            ensure_exists=False,
        )
    )


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "BolsaNext"
    default_base_currency: str = "EUR"
    data_dir: Path = field(default_factory=_system_data_dir)
    database_name: str = "bolsanext.sqlite3"
    data_dir_is_override: bool = False

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_name

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"


def load_config() -> AppConfig:
    override = os.environ.get(_DATA_DIR_ENV)
    if override:
        return AppConfig(
            data_dir=Path(override).expanduser().resolve(),
            data_dir_is_override=True,
        )

    return AppConfig(data_dir=_system_data_dir())


def prepare_environment(config: AppConfig) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    config.backups_dir.mkdir(parents=True, exist_ok=True)
