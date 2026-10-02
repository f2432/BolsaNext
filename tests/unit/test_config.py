from pathlib import Path

from bolsa.config import AppConfig


def test_database_path_uses_data_directory() -> None:
    config = AppConfig(data_dir=Path("tmp-data"), database_name="test.sqlite3")

    assert config.database_path == Path("tmp-data/test.sqlite3")
    assert config.database_url.endswith("tmp-data/test.sqlite3")
