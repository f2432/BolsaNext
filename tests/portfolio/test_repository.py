from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError

from bolsa.domain.portfolio.models import TransactionVersion
from bolsa.domain.portfolio.money import LedgerError, StaleRevisionError, Money
from bolsa.domain.portfolio.ledger import replay
from bolsa.infrastructure.database.portfolio_tables import portfolios


def test_persistence_exact_and_sqlite_text(service, repository, trade):
    initial = service.create('S', 'EUR')
    tx = trade(quantity='.12345678', price='999999999999999999.12345678')
    updated = service.record(initial.portfolio.portfolio_uid, tx, expected_revision=0)
    loaded = repository.load(initial.portfolio.portfolio_uid)
    assert loaded == updated and replay(loaded) == replay(updated)
    with repository.engine.connect() as conn:
        assert conn.execute(text('SELECT typeof(quantity), quantity FROM portfolio_versions')).first() == ('text', '0.12345678')
        assert conn.execute(text("SELECT typeof(amount), amount FROM portfolio_components WHERE role='price'")).first() == ('text', '999999999999999999.12345678')
    with repository.engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(update(portfolios).values(base_currency='USD'))
        with pytest.raises(IntegrityError):
            conn.execute(text('DELETE FROM portfolio_versions'))
    assert repository.load(initial.portfolio.portfolio_uid) == loaded


def test_correction_and_void_atomic_if_future_sale_invalid(service, repository, trade):
    uid = service.create('S', 'EUR').portfolio.portfolio_uid
    buy = trade()
    ledger = service.record(uid, buy, expected_revision=0)
    original = ledger.versions[0]
    ledger = service.record(uid, trade('SELL', '8', day=1), expected_revision=1)
    with pytest.raises(LedgerError):
        service.revise(uid, replace(buy, quantity=Decimal(5)), expected_revision=2,
                       expected_head=original.transaction_version_uid, reason='fix')
    assert repository.load(uid) == ledger
    with pytest.raises(LedgerError):
        service.void(uid, buy.transaction_uid, expected_revision=2,
                     expected_head=original.transaction_version_uid, reason='void')
    assert repository.load(uid) == ledger
    changed = service.revise(uid, replace(buy, price=Money(Decimal('110'), 'EUR')),
                            expected_revision=2, expected_head=original.transaction_version_uid, reason='fix')
    assert replay(changed).positions[0].cost == Decimal('220')
    assert repository.load(uid) == changed


def test_concurrent_writers_one_stale(service, repository, trade):
    uid = service.create('S', 'EUR').portfolio.portfolio_uid
    def write(_):
        try:
            service.record(uid, trade(), expected_revision=0)
            return 'committed'
        except StaleRevisionError:
            return 'stale'
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(write, range(2))) == ['committed', 'stale']
    assert len(repository.load(uid).versions) == 1


def test_failure_mid_write_rolls_back_all(repository, service, trade, monkeypatch):
    uid = service.create('S', 'EUR').portfolio.portfolio_uid
    before = repository.load(uid)
    original = repository._insert_version
    calls = 0
    def fail(connection, portfolio_uid, version):
        nonlocal calls
        original(connection, portfolio_uid, version)
        calls += 1
        if calls == 2:
            raise RuntimeError('simulated storage failure')
    monkeypatch.setattr(repository, '_insert_version', fail)
    with pytest.raises(RuntimeError):
        repository.append(uid, (TransactionVersion(trade()), TransactionVersion(trade(day=1))), expected_revision=0)
    assert repository.load(uid) == before


def test_external_identity_collision_and_isolation(service, repository, trade):
    uid = service.create('S', 'EUR').portfolio.portfolio_uid
    tx = trade(source='synthetic', account_ref='test', external_id='001')
    ledger = service.record(uid, tx, expected_revision=0)
    with pytest.raises(LedgerError):
        service.record(uid, trade(source='synthetic', account_ref='test', external_id='001'), expected_revision=1)
    other = service.create('S', 'USD').portfolio.portfolio_uid
    assert repository.load(uid) == ledger and repository.load(other).portfolio.base_currency == 'USD'


def test_v02_upgrade_preserves_watchlist_and_backup(tmp_path):
    from bolsa.config import AppConfig, prepare_environment
    from bolsa.infrastructure.database.schema_migrations import _run_upgrade, get_database_revision
    from bolsa.infrastructure.database import ensure_database_schema, create_database_engine
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    _run_upgrade(config.database_path, '0002_market_to_exchange')
    engine = create_database_engine(config.database_url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO instruments(id,ticker,asset_type) VALUES(1,'TEST','stock')"))
        connection.execute(text("INSERT INTO watchlists(id,name) VALUES(1,'Synthetic')"))
        connection.execute(text("INSERT INTO watchlist_items(id,watchlist_id,instrument_id,state,notes) VALUES(1,1,1,'candidate','preserve')"))
    result = ensure_database_schema(config)
    assert result.backup_path.is_file()
    assert get_database_revision(result.backup_path) == '0002_market_to_exchange'
    with engine.connect() as connection:
        assert connection.execute(text('SELECT state,notes FROM watchlist_items')).first() == ('candidate', 'preserve')
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []
    engine.dispose()
