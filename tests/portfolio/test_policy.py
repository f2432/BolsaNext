from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from bolsa.app.services.portfolio_policy_service import PortfolioPolicyService
from bolsa.app.services.portfolio_transfer_service import PortfolioTransferService, parse_json
from bolsa.domain.portfolio.valuation import Quote, value_portfolio
from bolsa.domain.portfolio.policy import active_policy, evaluate_risk
from bolsa.domain.portfolio.reconciliation import reconcile
from bolsa.domain.portfolio.money import Money

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def test_optional_versioned_policy_preserved_by_clone(service, repository, trade):
    policy_service = PortfolioPolicyService(repository)
    uid = service.create("S", "EUR").portfolio.portfolio_uid
    ledger = service.record(uid, trade(), expected_revision=0)
    assert active_policy(ledger.policies, NOW) is None
    ledger = policy_service.set_policy(
        uid, expected_revision=1, effective_from=NOW, max_instrument_weight=Decimal(".5")
    )
    ledger = policy_service.set_policy(
        uid,
        expected_revision=2,
        effective_from=NOW + timedelta(days=1),
        max_instrument_weight=Decimal(".7"),
    )
    assert len(ledger.policies) == 2 and repository.load(uid).policies == ledger.policies
    assert active_policy(ledger.policies, NOW).max_instrument_weight == Decimal(".5")
    transfer = PortfolioTransferService(repository)
    text = transfer.export(uid)
    assert parse_json(text).policies == ledger.policies
    clone, _ = transfer.confirm(transfer.preview(text, mode="clone"))
    assert clone.policies == ledger.policies


def test_risk_complete_denominator_and_missing_sector(service, repository, trade):
    uid = service.create("S", "EUR").portfolio.portfolio_uid
    ledger = service.record(uid, trade(), expected_revision=0)
    ledger = PortfolioPolicyService(repository).set_policy(
        uid,
        expected_revision=1,
        effective_from=NOW,
        max_instrument_weight=Decimal(".5"),
        max_sector_weight=Decimal(".8"),
        max_currency_weight=Decimal(1),
        annualized_return_target=Decimal(".1"),
    )
    quote = Quote("TEST", "EUR", Decimal(110), NOW, "synthetic")
    valuation = value_portfolio(ledger, {"TEST": quote}, {}, now=NOW)
    policy = active_policy(ledger.policies, NOW)
    report = evaluate_risk(valuation, policy=policy)
    assert report.instrument_weights == (("TEST", Decimal(1)),)
    states = {a.metric: a.state for a in report.alerts}
    assert states == {
        "instrument": "exceeded",
        "sector": "not_evaluable",
        "quote_currency": "within_limit",
        "annualized_return": "not_evaluable",
    }
    unknown = value_portfolio(ledger, {}, {}, now=NOW)
    report = evaluate_risk(unknown, policy=policy)
    assert report.instrument_weights is None and all(
        a.state == "not_evaluable" for a in report.alerts
    )
    assert evaluate_risk(valuation).alerts == ()
    # Informational breach does not block valid subsequent purchases.
    service.record(uid, trade(day=1), expected_revision=2)


def test_internal_reconciliation_observed_difference(service, repository, trade):
    uid = service.create("S", "EUR").portfolio.portfolio_uid
    ledger = service.record(
        uid, trade(observed_net=Money(Decimal(999), "EUR")), expected_revision=0
    )
    report = reconcile(ledger)
    assert report.state == "pending" and report.discrepancies[0].kind == "observed_difference"
    assert repository.load(uid) == ledger
    corrupt = replace(ledger, versions=(replace(ledger.versions[0], transaction=trade("SELL")),))
    assert reconcile(corrupt).state == "invalid"


def test_etf_sector_is_not_inferred_from_a_single_metadata_label(trade):
    from bolsa.domain.instruments import Instrument, AssetType
    from bolsa.domain.portfolio.models import Ledger, Portfolio, TransactionVersion
    from bolsa.domain.portfolio.policy import InvestmentPolicy

    transaction = replace(
        trade(), instrument=Instrument("TEST", currency="EUR", asset_type=AssetType.ETF)
    )
    ledger = Ledger(Portfolio("S", "EUR"), (TransactionVersion(transaction),))
    valued = value_portfolio(
        ledger, {"TEST": Quote("TEST", "EUR", Decimal(110), NOW, "synthetic")}, {}, now=NOW
    )
    risk = evaluate_risk(
        valued,
        policy=InvestmentPolicy(max_sector_weight=Decimal(".5")),
        sectors={"TEST": "Technology"},
    )
    assert risk.sector_weights == (("não determinado", Decimal(1)),)
    assert risk.alerts[0].state == "not_evaluable"
