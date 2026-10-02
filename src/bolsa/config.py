from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "BolsaNext"
    base_currency: str = "EUR"
    data_dir: Path = Path("data")
    database_name: str = "bolsanext.sqlite3"

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_name

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"


def load_config() -> AppConfig:
    config = AppConfig()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return config
