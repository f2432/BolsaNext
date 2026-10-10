from __future__ import annotations

from importlib.metadata import version as installed_version
from pathlib import Path
import tomllib

import bolsa
from bolsa.infrastructure.market_data.wikipedia_universe_provider import (
    WikipediaUniverseProvider,
)
from bolsa.version import __version__, version_label


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_package_version_has_single_canonical_value() -> None:
    assert __version__ == "0.2.0"
    assert bolsa.__version__ == __version__


def test_installed_package_metadata_matches_canonical_version() -> None:
    assert installed_version("bolsanext") == __version__


def test_pyproject_reads_version_dynamically_from_canonical_module() -> None:
    pyproject = tomllib.loads(
        (_project_root() / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["dynamic"] == ["version"]
    assert "version" not in {
        key
        for key in pyproject["project"]
        if key != "dynamic"
    }
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "bolsa.version.__version__"
    }


def test_wikipedia_user_agent_uses_canonical_version() -> None:
    assert WikipediaUniverseProvider._USER_AGENT.startswith(
        f"BolsaNext/{__version__} "
    )
    assert "BolsaNext/0.1" not in WikipediaUniverseProvider._USER_AGENT


def test_ui_version_label_uses_canonical_version() -> None:
    assert version_label("Market Data") == f"V{__version__} — Market Data"

    window_source = (
        _project_root()
        / "src"
        / "bolsa"
        / "ui"
        / "main_window"
        / "window.py"
    ).read_text(encoding="utf-8")

    assert 'version_label("Market Data")' in window_source
    assert "V0.2 — Market Data" not in window_source
