from dataclasses import replace
from decimal import Decimal
import json

import pytest

from bolsa.app.services.portfolio_transfer_service import PortfolioTransferService, export_json, parse_json
from bolsa.domain.portfolio.importing import ImportRejected
from bolsa.domain.portfolio.ledger import replay
from bolsa.domain.portfolio.models import TransactionVersion, uid
from bolsa.domain.portfolio.money import Money, StaleRevisionError


def test_complete_roundtrip_clone_idempotency(service, repository, trade):
    from test_dividends_adjustments import dividend, split
    transfer = PortfolioTransferService(repository)
    source_uid = service.create('Synthetic','EUR').portfolio.portfolio_uid
    buy = trade()
    initial = service.record(source_uid,buy,expected_revision=0)
    head = initial.versions[0].transaction_version_uid
    ledger = service.revise(source_uid,replace(buy, price=Money(Decimal('110'),'EUR')),
                            expected_head=head,expected_revision=1,reason='correct')
    ledger = service.record(source_uid,dividend(),expected_revision=2)
    ledger = service.record(source_uid,split(),expected_revision=3)
    exported = transfer.export(source_uid)
    assert parse_json(exported).versions == ledger.versions
    plan = transfer.preview(exported,mode='clone')
    assert len(repository.list_portfolios()) == 1
    cloned, report = transfer.confirm(plan)
    assert report.inserted == 4 and report.status == 'completed'
    assert cloned.portfolio.origin_portfolio_uid == source_uid
    assert cloned.versions == ledger.versions and replay(cloned) == replay(ledger)
    clone_export = transfer.export(cloned.portfolio.portfolio_uid)
    plan = transfer.preview(clone_export,mode='complement',target_uid=cloned.portfolio.portfolio_uid)
    assert plan.report.ignored == 4
    same, report = transfer.confirm(plan)
    assert same == cloned and report.inserted == 0 and report.status == 'no_changes'
    assert repository.load(source_uid) == ledger


def test_conflict_and_financially_identical_legitimate_operations(service, repository, trade):
    transfer = PortfolioTransferService(repository)
    uid_ = service.create('S','EUR').portfolio.portfolio_uid
    ledger = service.record(uid_,trade(),expected_revision=0)
    extra = TransactionVersion(replace(ledger.versions[0].transaction,transaction_uid=uid(),order_key=uid()))
    incoming = replace(ledger,versions=ledger.versions+(extra,))
    plan = transfer.preview(export_json(incoming),mode='complement',target_uid=uid_)
    merged, report = transfer.confirm(plan)
    assert report.inserted == 1 and report.ignored == 1 and replay(merged).positions[0].quantity == 20
    conflicting = replace(merged,versions=(replace(merged.versions[0],reason='contradictory audit'),)+merged.versions[1:])
    with pytest.raises(ImportRejected) as exc:
        transfer.preview(export_json(conflicting),mode='complement',target_uid=uid_)
    assert exc.value.report.conflicts and exc.value.report.inserted == 0
    assert repository.load(uid_) == merged


def test_stale_preview_and_failure_mid_import_roll_back(service, repository, trade, monkeypatch):
    transfer = PortfolioTransferService(repository)
    uid_ = service.create('S','EUR').portfolio.portfolio_uid
    ledger = service.record(uid_,trade(),expected_revision=0)
    plan = transfer.preview(export_json(ledger),mode='complement',target_uid=uid_)
    changed = service.record(uid_,trade(day=1),expected_revision=1)
    with pytest.raises(StaleRevisionError):
        transfer.confirm(plan)
    assert repository.load(uid_) == changed
    clone_plan = transfer.preview(export_json(changed),mode='clone')
    original = repository._insert_version
    calls = 0
    def fail(*args):
        nonlocal calls
        original(*args)
        calls += 1
        if calls == 2:
            raise RuntimeError('synthetic import failure')
    monkeypatch.setattr(repository,'_insert_version',fail)
    with pytest.raises(ImportRejected) as exc:
        transfer.confirm(clone_plan)
    assert exc.value.report.inserted == 0 and exc.value.report.status == 'rejected_rollback'
    assert len(repository.list_portfolios()) == 1 and repository.load(uid_) == changed


@pytest.mark.parametrize('text',['{}','not json','{"format_version":1,"format_version":1}',
                               '{"format": NaN}'])
def test_invalid_json(text):
    with pytest.raises(ImportRejected):
        parse_json(text)


def test_json_financial_numbers_and_unknown_version_rejected(service, repository, trade):
    uid_ = service.create('S','EUR').portfolio.portfolio_uid
    ledger = service.record(uid_,trade(),expected_revision=0)
    data = json.loads(export_json(ledger))
    data['versions'][0]['transaction']['price']['amount'] = 100.0
    with pytest.raises(ImportRejected):
        parse_json(json.dumps(data))
    data = json.loads(export_json(ledger))
    data['format_version'] = 99
    with pytest.raises(ImportRejected):
        parse_json(json.dumps(data))
    transfer = PortfolioTransferService(repository)
    with pytest.raises(ImportRejected):
        transfer.preview(export_json(ledger),mode='restore')
    with pytest.raises(ImportRejected):
        transfer.preview(export_json(ledger),mode='replace')


def test_proven_external_duplicate_and_divergence(service, repository, trade):
    transfer = PortfolioTransferService(repository)
    uid_ = service.create('S','EUR').portfolio.portfolio_uid
    tx = trade(source='synthetic',account_ref='test',external_id='001')
    ledger = service.record(uid_,tx,expected_revision=0)
    equivalent = TransactionVersion(replace(tx,transaction_uid=uid(),order_key=uid()))
    incoming = replace(ledger,versions=(equivalent,))
    plan = transfer.preview(export_json(incoming),mode='complement',target_uid=uid_)
    _, report = transfer.confirm(plan)
    assert report.ignored == 1 and report.inserted == 0
    incoming = replace(incoming,versions=(replace(equivalent,transaction=replace(equivalent.transaction,quantity=Decimal(3))),))
    with pytest.raises(ImportRejected):
        transfer.preview(export_json(incoming),mode='complement',target_uid=uid_)
