from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from decimal import Decimal, localcontext

import pytest

from bolsa.domain.portfolio.models import Ledger, Portfolio, TransactionVersion
from bolsa.domain.portfolio.money import LedgerError, Money, decimal_input
from bolsa.domain.portfolio.ledger import replay, append_version, effective_versions


def ledger_of(*transactions):
    return Ledger(Portfolio("Synthetic", "EUR"), tuple(TransactionVersion(t) for t in transactions))


def test_approved_buy_reinforce_partial_sell(trade):
    ledger = ledger_of(
        trade(fee="5"), trade(price="120", fee="5", day=1), trade("SELL", "8", "130", "4", day=2)
    )
    p = replay(ledger).positions[0]
    assert (p.quantity, p.cost, p.average_cost, p.realized_pnl) == tuple(
        map(Decimal, ["12", "1326", "110.5", "152"])
    )
    assert replay(ledger) == replay(ledger)


def test_full_close_no_residue_and_reopen(trade):
    p = replay(
        ledger_of(
            trade(quantity="3", price="1"),
            trade("SELL", "1", "2", day=1),
            trade("SELL", "2", "2", day=2),
        )
    ).positions[0]
    assert p.quantity == p.cost == 0
    p = replay(
        ledger_of(
            trade(quantity="3", price="1"),
            trade("SELL", "3", "2", day=1),
            trade(quantity="0.125", price="7.25", day=2),
        )
    ).positions[0]
    assert p.average_cost == Decimal("7.25") and p.realized_pnl == 3


def test_retroactive_correction_recalculates(trade):
    buy = trade()
    ledger = ledger_of(buy, trade(price="120", day=1), trade("SELL", "5", "130", day=2))
    original = next(
        v for v in ledger.versions if v.transaction.transaction_uid == buy.transaction_uid
    )
    corrected = TransactionVersion(
        replace(buy, price=Money(Decimal("110"), "EUR")),
        2,
        previous_version_uid=original.transaction_version_uid,
        reason="Correction",
    )
    updated = append_version(ledger, corrected, expected_head=original.transaction_version_uid)
    p = replay(updated).positions[0]
    assert (p.average_cost, p.realized_pnl, p.quantity, p.cost) == tuple(
        map(Decimal, ["115", "75", "15", "1725"])
    )
    assert len(updated.versions) == 4 and len(effective_versions(updated)) == 3


def test_chain_void_terminal_and_no_branch(trade):
    original = TransactionVersion(trade())
    ledger = Ledger(Portfolio("S", "EUR"), (original,))
    v2 = TransactionVersion(
        original.transaction, 2, previous_version_uid=original.transaction_version_uid, reason="fix"
    )
    ledger = append_version(ledger, v2, expected_head=original.transaction_version_uid)
    v3 = TransactionVersion(
        v2.transaction,
        3,
        previous_version_uid=v2.transaction_version_uid,
        voided=True,
        reason="void",
    )
    ledger = append_version(ledger, v3, expected_head=v2.transaction_version_uid)
    assert not replay(ledger).positions and len(ledger.versions) == 3
    v4 = TransactionVersion(
        v3.transaction, 4, previous_version_uid=v3.transaction_version_uid, reason="restore"
    )
    with pytest.raises(LedgerError):
        append_version(ledger, v4, expected_head=v3.transaction_version_uid)
    with pytest.raises(LedgerError):
        append_version(ledger, v2, expected_head=v3.transaction_version_uid)


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "1e18", "0.000000001"])
def test_invalid_quantity(trade, value):
    with pytest.raises(LedgerError):
        trade(quantity=value)


@pytest.mark.parametrize("value", [1.0, "1", Decimal("-1"), Decimal("NaN")])
def test_financial_boundary_rejects_float_and_invalid(value):
    with pytest.raises(LedgerError):
        decimal_input(value)


def test_component_fx_and_observed_difference(trade):
    tx = replace(
        trade(quantity="1"),
        price=Money(Decimal("100"), "USD", Decimal(".9")),
        commission=Money(Decimal("2"), "GBP", Decimal("1.2")),
        observed_net=Money(Decimal("94"), "EUR", original_text="94.00"),
    )
    result = replay(ledger_of(tx))
    assert result.positions[0].cost == Decimal("92.4")
    assert result.pending_reconciliation == (tx.transaction_uid,)
    assert tx.observed_net.original_text == "94.00"
    with pytest.raises(LedgerError):
        replay(ledger_of(replace(tx, price=Money(Decimal("100"), "USD"))))
    with pytest.raises(LedgerError):
        replay(ledger_of(replace(tx, price=Money(Decimal("100"), "EUR", Decimal("2")))))


def test_context_is_local_50_digits_and_same_day_warning(trade):
    a, b = trade(quantity="3", price="1"), trade(quantity="4", price="1")
    with localcontext() as context:
        context.prec = 6
        result = replay(ledger_of(a, b))
        assert result.positions[0].average_cost == 1
        assert context.prec == 6
    assert result.warnings
    date_trade = replace(a, executed_at=date(2026, 1, 1), execution_timezone=None)
    assert replay(ledger_of(date_trade, b)).warnings
    with pytest.raises(LedgerError):
        replace(a, executed_at=datetime(2026, 1, 1))


def test_portfolio_currency_immutable():
    p = Portfolio("S", " eur ")
    assert p.base_currency == "EUR"
    with pytest.raises(FrozenInstanceError):
        p.base_currency = "USD"
    with pytest.raises(LedgerError):
        Portfolio("S", "XYZ")
    assert Portfolio("S", "USD").base_currency == "USD"


def test_oversell_rejected(trade):
    with pytest.raises(LedgerError, match="Venda excede"):
        replay(ledger_of(trade(), trade("SELL", "11", day=1)))
