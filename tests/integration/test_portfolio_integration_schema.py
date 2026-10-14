import sqlite3
from hashlib import sha256
from contextlib import closing
from pathlib import Path

import pytest

from bolsa.config import AppConfig
from bolsa.infrastructure.database import ensure_database_schema
from bolsa.infrastructure.database.schema_migrations import SchemaCompatibilityError, _alembic_config
from alembic.script import ScriptDirectory


def test_single_unchanged_published_migration_chain():
    # LF-normalized SHA256 of published dev bf30dcf; works in shallow CI clones.
    published = {
        "0001_v02_baseline.py": "ddd6f5fdcd6418a57fe93e285de413a8909a9d1c8907dfa1a7a02e05eb5bc05e",
        "0002_market_to_exchange.py": "c8dd0321ce4d82a6b24211b34ef931a82e080e47fbcb7d80cd5283f4b16b9160",
        "0003_portfolio_ledger.py": "9220544a1da9343e9abd29ea51a54e22655e4d5cec99e2fa37f8557c911d278d",
        "0004_manual_financial_events.py": "c461e4d394a74dc2a8ebb3445a0a10d353b3542c1fb611272826d40f6963438c",
        "0005_portfolio_origin.py": "36629296b1abd517bee62b39ca518bf887e647e3828e427c38c1336a80fd6194",
        "0006_portfolio_policies.py": "b17f5e5ecfe5f6cc19c9dee674d3c3b43d49d60babd531bcd7dc2d218888c34f",
    }
    directory = Path("src/bolsa/infrastructure/database/migrations/versions")
    for path in directory.glob("*.py"):
        if path.name != "__init__.py":
            assert sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == published[path.name]
    script = ScriptDirectory.from_config(_alembic_config())
    assert script.get_heads() == ["0006_portfolio_policies"]
    assert len(list(script.walk_revisions())) == 6


def test_foreign_0003_stamp_is_refused_without_changes(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(config.database_path)) as connection:
        connection.execute("CREATE TABLE alembic_version(version_num TEXT)")
        connection.execute("INSERT INTO alembic_version VALUES('0003_portfolio_ledger')")
        connection.execute("CREATE TABLE portfolio_components(amount TEXT)")
        connection.execute("INSERT INTO portfolio_components VALUES('123.45678901')")
        connection.execute("CREATE TABLE portfolio_versions(transaction_uid TEXT)")
        connection.commit()
    before = config.database_path.read_bytes()
    with pytest.raises(SchemaCompatibilityError, match="conversão explícita"):
        ensure_database_schema(config)
    assert config.database_path.read_bytes() == before
    assert list(config.backups_dir.glob("*.sqlite*")) == []
