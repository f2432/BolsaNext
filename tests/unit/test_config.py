from pathlib import Path

from bolsa.config import AppConfig, load_config, prepare_environment


def test_database_path_uses_data_directory() -> None:
    config = AppConfig(data_dir=Path("tmp-data"), database_name="test.sqlite3")

    assert config.database_path == Path("tmp-data/test.sqlite3")
    assert config.database_url.endswith("tmp-data/test.sqlite3")


def test_load_config_uses_platform_data_directory_without_creating_it(
    monkeypatch,
    tmp_path,
) -> None:
    expected = tmp_path / "system-data"
    monkeypatch.delenv("BOLSANEXT_DATA_DIR", raising=False)
    monkeypatch.setattr(
        "bolsa.config.user_data_path",
        lambda **_kwargs: expected,
    )

    config = load_config()

    assert config.data_dir == expected
    assert config.data_dir_is_override is False
    assert config.default_base_currency == "EUR"
    assert not expected.exists()


def test_load_config_honours_explicit_data_dir_override(
    monkeypatch,
    tmp_path,
) -> None:
    override = tmp_path / "override"
    monkeypatch.setenv("BOLSANEXT_DATA_DIR", str(override))

    config = load_config()

    assert config.data_dir == override.resolve()
    assert config.data_dir_is_override is True
    assert not override.exists()


def test_prepare_environment_creates_only_runtime_directories(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path / "data")

    prepare_environment(config)

    assert config.data_dir.is_dir()
    assert config.cache_dir.is_dir()
    assert config.backups_dir.is_dir()
    assert not config.database_path.exists()
