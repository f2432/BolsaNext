from sqlalchemy import Engine, event, inspect
import pytest

from bolsa.config import AppConfig
from bolsa.infrastructure.database import create_database_engine, ensure_database_schema
from bolsa.infrastructure.database.schema_migrations import _run_upgrade, get_database_revision


def test_failure_after_multiple_revision_ddl_preserves_original_schema_and_backup(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    _run_upgrade(config.database_path, "0004_manual_financial_events")
    engine = create_database_engine(config.database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO instruments (ticker, asset_type) VALUES ('TEST', 'stock')")
    engine.dispose()

    def fail_policy_trigger(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("CREATE TRIGGER portfolio_policies_no_update"):
            raise RuntimeError("Synthetic multi-revision migration failure")

    event.listen(Engine, "before_cursor_execute", fail_policy_trigger)
    try:
        with pytest.raises(RuntimeError, match="multi-revision"):
            ensure_database_schema(config)
    finally:
        event.remove(Engine, "before_cursor_execute", fail_policy_trigger)
    assert get_database_revision(config.database_path) == "0004_manual_financial_events"
    backups = list(config.backups_dir.glob("*.sqlite3"))
    assert len(backups) == 1 and get_database_revision(backups[0]) == "0004_manual_financial_events"
    engine = create_database_engine(config.database_url)
    try:
        inspector = inspect(engine)
        assert "portfolio_policies" not in inspector.get_table_names()
        assert "origin_portfolio_uid" not in {c["name"] for c in inspector.get_columns("portfolios")}
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT ticker FROM instruments").scalar() == "TEST"
            assert connection.exec_driver_sql("PRAGMA quick_check").scalar() == "ok"
    finally:
        engine.dispose()
