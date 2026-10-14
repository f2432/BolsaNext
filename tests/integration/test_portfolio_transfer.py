from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from uuid import uuid4

import pytest
from sqlalchemy import event

from bolsa.app.portfolio_format import (
    ImportState, PortfolioTransferService, export_portfolio, parse_portfolio,
)
import bolsa.app.portfolio_format as portfolio_format
from bolsa.config import AppConfig
from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError, PortfolioNotFoundError
from bolsa.infrastructure.database import create_database_engine, ensure_database_schema
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository

D = Decimal
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def synthetic_portfolio():
    asset = Instrument("TEST")
    def m(value):
        return MoneyComponent(D(value), "EUR")
    buy = Trade(asset, TradeType.BUY, D(10), m("100"), m("5"), AT)
    p = Portfolio("Synthetic", "EUR").record(buy)
    first = p.versions[0]
    p = p.revise(first.transaction_uid, first.transaction_version_uid,
                 replace(buy, quantity=D(12)), reason="Synthetic correction")
    p = p.record(Dividend(asset, m("50"), m("7.5"), m("1"), m("41.5"), AT + timedelta(days=1)))
    p = p.record(Split(asset, D(2), "Synthetic forward split", AT + timedelta(days=2)))
    p = p.record(replace(buy, kind=TradeType.SELL, quantity=D(3), executed_at=AT + timedelta(days=3)))
    last = p.versions[-1]
    return p.revise(last.transaction_uid, last.transaction_version_uid, None, reason="Synthetic cancellation")


@pytest.fixture
def store(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    try:
        repository = SqlAlchemyPortfolioRepository(engine)
        yield engine, repository, PortfolioTransferService(repository)
    finally:
        engine.dispose()


def test_export_parse_full_history_and_exact_financial_values():
    original = synthetic_portfolio()
    text = export_portfolio(original)
    loaded = parse_portfolio(text.encode("utf-8"))
    assert loaded.reconstruct() == original.reconstruct()
    assert set(loaded.versions) == set(original.versions)
    assert json.loads(text)["format_version"] == 1
    for version in json.loads(text)["versions"]:
        for field in ("quantity", "price", "commission", "gross", "net", "split_factor"):
            if field in version:
                assert isinstance(version[field], str)


def test_preview_is_read_only_confirm_restore_and_reimport_idempotent(store):
    engine, repository, service = store
    p = synthetic_portfolio()
    preview = service.preview(export_portfolio(p))
    assert preview.report.state is ImportState.PREVIEW
    assert preview.report.inserted == 0
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM portfolios").scalar() == 0
    report = service.confirm(preview)
    assert report.state is ImportState.COMPLETED and report.inserted == len(p.versions)
    assert repository.load(p.portfolio_uid).reconstruct() == p.reconstruct()
    second = service.confirm(service.preview(export_portfolio(p)))
    assert second.state is ImportState.UNCHANGED and second.inserted == 0
    assert second.ignored == len(p.versions)


def test_identical_economic_values_with_different_uuid_are_not_duplicates(store):
    _, repository, service = store
    p = synthetic_portfolio()
    buy = p.versions[0].trade
    p = p.record(buy).record(buy)
    result = service.confirm(service.preview(export_portfolio(p)))
    assert result.inserted == len(p.versions) and result.ignored == 0
    assert repository.load(p.portfolio_uid).reconstruct().position("TEST").quantity == D(64)


def test_complement_and_conflicting_identity_never_rewrite_existing(store):
    _, repository, service = store
    p = synthetic_portfolio()
    service.confirm(service.preview(export_portfolio(p)))
    extra = p.record(replace(p.versions[0].trade, executed_at=AT + timedelta(days=10)))
    preview = service.preview(export_portfolio(extra), mode="complement", destination_uid=p.portfolio_uid)
    result = service.confirm(preview)
    assert result.inserted == 1 and result.ignored == len(p.versions)
    loaded = repository.load(p.portfolio_uid)
    document = json.loads(export_portfolio(extra))
    document["versions"][0]["author"] = "Contradictory identity"
    rejected = service.preview(json.dumps(document), mode="complement", destination_uid=p.portfolio_uid)
    assert rejected.report.state is ImportState.REJECTED and rejected.report.conflicts == 1
    assert service.confirm(rejected).inserted == 0
    assert repository.load(p.portfolio_uid) == loaded


def test_same_economic_version_with_different_version_uuid_is_a_conflict(store):
    _, _, service = store
    p = Portfolio("Synthetic", "EUR").record(synthetic_portfolio().versions[0].trade)
    service.confirm(service.preview(export_portfolio(p)))
    doc = json.loads(export_portfolio(p))
    doc["versions"][0]["transaction_version_uid"] = str(uuid4())
    preview = service.preview(json.dumps(doc))
    assert preview.report.state is ImportState.REJECTED and preview.report.conflicts == 1


def test_clone_preserves_scoped_version_identity_and_evolves_independently(store):
    _, repository, service = store
    original = synthetic_portfolio()
    service.confirm(service.preview(export_portfolio(original)))
    preview = service.preview(export_portfolio(original), mode="clone")
    clone = preview.candidate
    assert clone.portfolio_uid != original.portfolio_uid
    assert clone.origin_portfolio_uid == original.portfolio_uid
    assert {v.transaction_version_uid for v in clone.versions} == {
        v.transaction_version_uid for v in original.versions
    }
    assert service.confirm(preview).state is ImportState.COMPLETED
    loaded = repository.load(clone.portfolio_uid)
    assert loaded.reconstruct() == original.reconstruct()
    changed = loaded.record(replace(loaded.versions[0].trade, executed_at=AT + timedelta(days=20)))
    repository.save(changed, expected_revision=loaded.ledger_revision)
    assert repository.load(original.portfolio_uid).reconstruct() == original.reconstruct()
    second = service.confirm(service.preview(export_portfolio(changed)))
    assert second.state is ImportState.UNCHANGED


def test_injected_import_failure_rolls_back_new_portfolio_instruments_and_all_events(store):
    engine, repository, service = store
    p = synthetic_portfolio()
    preview = service.preview(export_portfolio(p))
    count = 0

    def fail_second(connection, cursor, statement, parameters, context, executemany):
        nonlocal count
        if statement.startswith("INSERT INTO ledger_versions"):
            count += 1
            if count == 2:
                raise RuntimeError("Synthetic import failure")

    event.listen(engine, "before_cursor_execute", fail_second)
    try:
        report = service.confirm(preview)
    finally:
        event.remove(engine, "before_cursor_execute", fail_second)
    assert report.state is ImportState.REJECTED and report.inserted == 0
    with pytest.raises(PortfolioNotFoundError):
        repository.load(p.portfolio_uid)
    with engine.connect() as connection:
        for table in ("portfolios", "instruments", "ledger_versions"):
            assert connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar() == 0
    assert service.confirm(preview).state is ImportState.COMPLETED


def test_stale_preview_after_ledger_write_is_rejected_with_zero_insertions(store):
    _, repository, service = store
    p = synthetic_portfolio()
    service.confirm(service.preview(export_portfolio(p)))
    preview = service.preview(export_portfolio(p))
    loaded = repository.load(p.portfolio_uid)
    changed = loaded.record(replace(loaded.versions[0].trade, executed_at=AT + timedelta(days=20)))
    repository.save(changed, expected_revision=loaded.ledger_revision)
    report = service.confirm(preview)
    assert report.state is ImportState.REJECTED and report.inserted == 0
    assert repository.load(p.portfolio_uid).reconstruct() == changed.reconstruct()


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(format_version=2),
    lambda d: d.update(format_version=True),
    lambda d: d.update(script="do not execute"),
    lambda d: d["versions"][0].update(quantity=10.0),
    lambda d: d["versions"][0].update(quantity="NaN"),
    lambda d: d["versions"][0].update(portfolio_uid=str(uuid4())),
    lambda d: d["versions"][0].update(previous_version_uid=str(uuid4())),
    lambda d: d["versions"][0].update(net="1"),
    lambda d: d["portfolio"].update(password="forbidden field"),
])
def test_invalid_documents_are_rejected_before_writing(store, mutation):
    engine, _, service = store
    document = json.loads(export_portfolio(synthetic_portfolio()))
    mutation(document)
    preview = service.preview(json.dumps(document))
    assert preview.report.state is ImportState.REJECTED and preview.report.reasons
    assert service.confirm(preview).inserted == 0
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM portfolios").scalar() == 0


def test_duplicate_keys_malformed_utf8_and_resource_limits_are_rejected(monkeypatch):
    for text in ('{"format_version":1,"format_version":1}', "not json", b"\xff"):
        with pytest.raises(PortfolioError):
            parse_portfolio(text)
    text = export_portfolio(synthetic_portfolio())
    monkeypatch.setattr(portfolio_format, "MAX_IMPORT_BYTES", 10)
    with pytest.raises(PortfolioError, match="size limit"):
        parse_portfolio(text)
    monkeypatch.setattr(portfolio_format, "MAX_IMPORT_BYTES", 5 * 1024 * 1024)
    monkeypatch.setattr(portfolio_format, "MAX_IMPORT_VERSIONS", 1)
    with pytest.raises(PortfolioError, match="version limit"):
        parse_portfolio(text)


def test_export_refuses_credentials_in_original_facts_without_deleting_them():
    p = synthetic_portfolio()
    t = replace(p.versions[0].trade, original_facts=(("password", "synthetic placeholder"),))
    protected = Portfolio("Synthetic", "EUR").record(t)
    with pytest.raises(PortfolioError, match="Credential fields"):
        export_portfolio(protected)
    assert protected.versions[0].trade.original_facts == t.original_facts


def test_currency_destination_conflict_complement_absence_and_duplicate_names(store):
    _, repository, service = store
    p = synthetic_portfolio()
    service.confirm(service.preview(export_portfolio(p)))
    changed_currency = replace(p, base_currency="USD", versions=())
    assert service.preview(export_portfolio(changed_currency)).report.conflicts == 1
    assert service.preview(export_portfolio(p), destination_uid=uuid4()).report.state is ImportState.REJECTED
    absent = Portfolio("Synthetic", "EUR")
    assert service.preview(export_portfolio(absent), mode="complement").report.state is ImportState.REJECTED
    assert service.confirm(service.preview(export_portfolio(absent))).state is ImportState.COMPLETED
    assert repository.load(absent.portfolio_uid).name == repository.load(p.portfolio_uid).name


def test_confirm_counts_actual_candidate_versions_instead_of_trusting_report(store):
    _, _, service = store
    p = synthetic_portfolio()
    preview = service.preview(export_portfolio(p))
    forged = replace(preview, report=replace(preview.report, planned_insertions=999))
    result = service.confirm(forged)
    assert result.inserted == len(p.versions)


def test_export_resource_limits_are_explicit_without_partial_output(monkeypatch):
    p = synthetic_portfolio()
    monkeypatch.setattr(portfolio_format, "MAX_IMPORT_VERSIONS", 1)
    with pytest.raises(PortfolioError, match="version limit"):
        export_portfolio(p)
    monkeypatch.setattr(portfolio_format, "MAX_IMPORT_VERSIONS", 20000)
    monkeypatch.setattr(portfolio_format, "MAX_IMPORT_BYTES", 10)
    with pytest.raises(PortfolioError, match="size limit"):
        export_portfolio(p)
