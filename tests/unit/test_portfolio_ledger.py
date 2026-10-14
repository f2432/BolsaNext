from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from uuid import UUID, uuid4
from time import perf_counter
import tracemalloc

import pytest

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.ledger import (
    Portfolio, Trade, TradeType, TransactionVersion, replay,
)
from bolsa.domain.portfolio.values import (
    LedgerConflictError, MoneyComponent, PortfolioError, decimal_text, financial_decimal,
)

D = Decimal
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def trade(q="10", p="100", fee="0", kind=TradeType.BUY, day=0, **kwargs):
    return Trade(Instrument("TEST"), kind, D(q), MoneyComponent(D(p), "EUR"),
                 MoneyComponent(D(fee), "EUR"), START + timedelta(days=day), **kwargs)


def test_approved_accounting_and_close_reopen():
    portfolio = Portfolio("Synthetic", "eur").record(trade(fee="5"))
    position = portfolio.reconstruct().position("TEST")
    assert (position.quantity, position.cost, position.average_cost) == (D(10), D(1005), D("100.5"))
    portfolio = portfolio.record(trade(p="120", fee="5", day=1))
    portfolio = portfolio.record(trade("8", "130", "4", TradeType.SELL, 2))
    position = portfolio.reconstruct().position("TEST")
    assert (position.quantity, position.cost, position.average_cost, position.realized_pnl) == (
        D(12), D(1326), D("110.5"), D(152)
    )
    portfolio = portfolio.record(trade("12", "100", "0", TradeType.SELL, 3))
    position = portfolio.reconstruct().position("TEST")
    assert (position.quantity, position.cost, position.average_cost) == (D(0), D(0), D(0))
    assert position.realized_pnl == D(26)
    portfolio = portfolio.record(trade("1", "50", day=4))
    assert portfolio.reconstruct().position("TEST").average_cost == D(50)
    assert portfolio.reconstruct().position("TEST").realized_pnl == D(26)


def test_retroactive_correction_and_terminal_cancellation():
    portfolio = Portfolio("Synthetic", "EUR").record(trade())
    first = portfolio.versions[0]
    portfolio = portfolio.record(trade(p="120", day=1)).record(trade("5", "130", kind=TradeType.SELL, day=2))
    corrected = portfolio.revise(first.transaction_uid, first.transaction_version_uid,
                                 trade(p="110"), reason="Correct entry")
    position = corrected.reconstruct().position("TEST")
    assert (position.average_cost, position.realized_pnl, position.quantity, position.cost) == (
        D(115), D(75), D(15), D(1725)
    )
    assert corrected.versions[0] == first
    with pytest.raises(LedgerConflictError):
        corrected.revise(first.transaction_uid, first.transaction_version_uid, trade(), reason="stale")
    last = corrected.versions[-1]
    cancelled = corrected.revise(first.transaction_uid, last.transaction_version_uid, None, reason="Cancel")
    assert cancelled.reconstruct().position("TEST").quantity == D(5)
    with pytest.raises(LedgerConflictError):
        cancelled.revise(first.transaction_uid, cancelled.versions[-1].transaction_version_uid,
                         trade(), reason="reactivate")


def test_invalid_retroactive_changes_preserve_original():
    portfolio = Portfolio("Synthetic", "EUR").record(trade())
    first = portfolio.versions[0]
    portfolio = portfolio.record(trade("8", kind=TradeType.SELL, day=1))
    before = portfolio.reconstruct()
    for replacement in (trade("5"), None):
        with pytest.raises(PortfolioError, match="Oversell"):
            portfolio.revise(first.transaction_uid, first.transaction_version_uid,
                             replacement, reason="Invalid")
    assert portfolio.reconstruct() == before
    assert portfolio.ledger_revision == 2


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1e18", "0.000000001", 1.0, 1, True, "junk"])
def test_invalid_decimal_inputs(value):
    with pytest.raises(PortfolioError):
        financial_decimal(value)


def test_exact_limits_and_serialization_without_ambient_context():
    value = financial_decimal("999999999999999999.12345678")
    assert D(decimal_text(value)) == value
    assert decimal_text(D("1.2300")) == "1.23"
    assert decimal_text(D("-0.000")) == "0"
    with pytest.raises(PortfolioError):
        financial_decimal("0", positive=True)
    with pytest.raises(PortfolioError):
        MoneyComponent(D(1), "USD", D("0.1234567890123"))
    portfolio = Portfolio("Synthetic", "EUR").record(trade("3", "0.33333333"))
    with localcontext() as ctx:
        ctx.prec = 3
        assert portfolio.reconstruct().position("TEST").cost == D("0.99999999")


def test_fractional_and_periodic_mean_partial_sale_then_exact_close():
    portfolio = Portfolio("Synthetic", "EUR").record(trade("3", "1", "1"))
    average = portfolio.reconstruct().position("TEST").average_cost
    assert average == D("1." + "3" * 49)
    portfolio = portfolio.record(trade("0.5", "2", kind=TradeType.SELL, day=1))
    assert portfolio.reconstruct().position("TEST").average_cost == average
    portfolio = portfolio.record(trade("2.5", "2", kind=TradeType.SELL, day=2))
    position = portfolio.reconstruct().position("TEST")
    assert (position.quantity, position.cost, position.realized_pnl) == (D(0), D(0), D(2))


def test_currency_and_base_immutability():
    portfolio = Portfolio("Synthetic", " eur ")
    assert portfolio.base_currency == "EUR"
    with pytest.raises(FrozenInstanceError):
        portfolio.base_currency = "USD"
    for code in ("AAA", "", "EU"):
        with pytest.raises(PortfolioError):
            Portfolio("Synthetic", code)


def test_historical_fx_per_component_and_missing_fx():
    t = replace(trade(), unit_price=MoneyComponent(D(100), "USD", D("0.86")),
                commission=MoneyComponent(D(2), "GBP", D("1.2")))
    portfolio = Portfolio("Synthetic", "EUR").record(t)
    assert portfolio.reconstruct().position("TEST").cost == D("862.4")
    with pytest.raises(PortfolioError, match="Missing historical FX"):
        Portfolio("Synthetic", "EUR").record(replace(t, unit_price=MoneyComponent(D(100), "USD")))
    with pytest.raises(PortfolioError, match="equal one"):
        MoneyComponent(D(1), "EUR", D("0.9")).in_base("EUR")


def test_deterministic_execution_order_and_warning():
    portfolio = Portfolio("Synthetic", "EUR")
    buy = TransactionVersion(portfolio.portfolio_uid, UUID(int=1), trade())
    sell = TransactionVersion(portfolio.portfolio_uid, UUID(int=2), trade("1", kind=TradeType.SELL))
    a = replay(portfolio.portfolio_uid, "EUR", (buy, sell))
    assert a == replay(portfolio.portfolio_uid, "EUR", (sell, buy))
    assert a.warnings
    a = replay(portfolio.portfolio_uid, "EUR", (
        replace(buy, trade=replace(buy.trade, broker_sequence=1)),
        replace(sell, trade=replace(sell.trade, broker_sequence=2)),
    ))
    assert not a.warnings
    dated = Portfolio("Synthetic", "EUR").record(replace(trade(), executed_at=date(2026, 1, 1)))
    assert type(dated.versions[0].trade.executed_at) is date
    assert dated.reconstruct().warnings


def test_invalid_version_chains_and_audit_metadata():
    portfolio = Portfolio("Synthetic", "EUR").record(trade())
    first = portfolio.versions[0]
    successor = TransactionVersion(portfolio.portfolio_uid, first.transaction_uid, trade(),
                                   2, first.transaction_version_uid, reason="Correction")
    for versions in (
        (first, first), (successor,),
        (first, replace(successor, previous_version_uid=uuid4())),
        (replace(first, portfolio_uid=uuid4()),),
        (first, successor, replace(successor, transaction_version_uid=uuid4())),
    ):
        with pytest.raises(PortfolioError):
            replace(portfolio, versions=versions)
    with pytest.raises(PortfolioError):
        replace(successor, reason="")
    with pytest.raises(PortfolioError):
        replace(first, recorded_at=datetime(2026, 1, 1))


@pytest.mark.parametrize("change", [
    {"quantity": D(0)}, {"quantity": D(-1)}, {"executed_at": datetime(2026, 1, 1)},
    {"broker_sequence": -1}, {"kind": "SELL"}, {"account_ref": "account"},
    {"instrument": Instrument("TEST", asset_type=AssetType.INDEX)},
    {"unit_price": MoneyComponent(D(0), "EUR")},
])
def test_trade_validation(change):
    with pytest.raises(PortfolioError):
        replace(trade(), **change)


def test_portfolios_and_instruments_are_isolated():
    eur = Portfolio("Same name", "EUR").record(trade())
    usd = Portfolio("Same name", "USD").record(replace(
        trade(), unit_price=MoneyComponent(D(50), "USD"), commission=MoneyComponent(D(0), "USD")
    ))
    eur = eur.record(replace(trade("1", "2", day=1), instrument=Instrument("OTHER")))
    assert eur.reconstruct().position("TEST").cost == D(1000)
    assert eur.reconstruct().position("OTHER").cost == D(2)
    assert usd.reconstruct().position("TEST").cost == D(500)


def test_duplicate_external_identity_rejected_but_equal_trades_allowed():
    portfolio = Portfolio("Synthetic", "EUR").record(trade())
    assert portfolio.record(trade()).reconstruct().position("TEST").quantity == D(20)
    t = trade(source="synthetic", account_ref="test", external_id="event")
    portfolio = portfolio.record(t)
    with pytest.raises(PortfolioError, match="external identity"):
        portfolio.record(t)
    with pytest.raises(LedgerConflictError):
        portfolio.record(trade(), transaction_uid=portfolio.versions[0].transaction_uid)


def test_cancelled_external_identity_still_belongs_to_original_economic_event():
    p = Portfolio("Synthetic", "EUR").record(trade(
        source="synthetic", account_ref="test", external_id="one"
    ))
    head = p.versions[0]
    p = p.revise(head.transaction_uid, head.transaction_version_uid, None, reason="Cancel")
    with pytest.raises(PortfolioError, match="external identity"):
        p.record(head.trade)


def test_terminal_audit_chain_cannot_be_revived_by_reconstruction():
    p = Portfolio("Synthetic", "EUR").record(trade())
    first = p.versions[0]
    cancelled = p.revise(first.transaction_uid, first.transaction_version_uid, None, reason="Cancel")
    successor = TransactionVersion(p.portfolio_uid, first.transaction_uid, trade(), 3,
                                   cancelled.versions[-1].transaction_version_uid, reason="Revive")
    with pytest.raises(PortfolioError, match="terminal"):
        replace(cancelled, versions=cancelled.versions + (successor,))


def test_high_magnitude_fx_applies_after_execution_gross():
    t = replace(trade("999999999999999999.12345678"),
                unit_price=MoneyComponent(D("987654321987654321.12345678"), "USD", D("0.123456789012")))
    p = Portfolio("Synthetic", "EUR").record(t)
    with localcontext() as context:
        # Full finite product must preserve digits beyond the division context.
        context.prec = 100
        expected = t.quantity * t.unit_price.amount * t.unit_price.historical_fx
    assert p.reconstruct().position("TEST").cost == expected


def test_long_ledger_replay_is_exact_and_order_independent():
    uid = UUID(int=1)
    versions = tuple(TransactionVersion(
        uid, UUID(int=i + 1),
        replace(trade("1" if i % 2 == 0 else "0.5", "3" if i % 2 == 0 else "4",
                      kind=TradeType.BUY if i % 2 == 0 else TradeType.SELL),
                executed_at=START + timedelta(seconds=i)),
        transaction_version_uid=UUID(int=i + 20000), recorded_at=START,
    ) for i in range(10000))
    tracemalloc.start()
    start = perf_counter()
    result = replay(uid, "EUR", versions)
    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result == replay(uid, "EUR", tuple(reversed(versions)))
    position = result.position("TEST")
    assert (position.quantity, position.cost, position.average_cost, position.realized_pnl) == (
        D(2500), D(7500), D(3), D(2500)
    )
    print(f"Replay 10000 events: {elapsed:.3f}s; peak replay allocations {peak / 1024 / 1024:.2f} MiB")
