from dataclasses import replace
from datetime import date
from decimal import Decimal, localcontext, ROUND_UP

import pytest

from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.models import (
    Ledger,
    Portfolio,
    Transaction,
    TransactionType,
    TransactionVersion,
)
from bolsa.domain.portfolio.money import LedgerError, Money, decimal_input, FINANCIAL_CONTEXT
from bolsa.domain.portfolio.ledger import replay


def dividend(**kwargs):
    fields = dict(
        instrument=Instrument("TEST", currency="EUR"),
        type=TransactionType.DIVIDEND,
        executed_at=date(2026, 1, 2),
        gross=Money(Decimal(50), "EUR"),
        withholding=Money(Decimal("7.5"), "EUR"),
        charges=Money(Decimal(1), "EUR"),
        net=Money(Decimal("41.5"), "EUR"),
    )
    fields.update(kwargs)
    return Transaction(**fields)


def split(**kwargs):
    fields = dict(
        instrument=Instrument("TEST"),
        type=TransactionType.ADJUSTMENT,
        executed_at=date(2026, 1, 3),
        split_factor=Decimal(2),
        adjustment_category="SPLIT",
        adjustment_reason="Synthetic 2:1 split",
    )
    fields.update(kwargs)
    return Transaction(**fields)


def test_dividend_split_then_sale_persist_reopen(service, repository, trade):
    uid = service.create("S", "EUR").portfolio.portfolio_uid
    ledger = service.record(uid, trade(), expected_revision=0)
    ledger = service.record(uid, dividend(), expected_revision=1)
    ledger = service.record(uid, split(), expected_revision=2)
    pos = replay(ledger).positions[0]
    assert (pos.quantity, pos.cost, pos.average_cost, pos.realized_pnl, pos.dividends) == tuple(
        map(Decimal, ["20", "1000", "50", "0", "41.5"])
    )
    ledger = service.record(uid, trade("SELL", "20", "60", day=3), expected_revision=3)
    pos = replay(repository.load(uid)).positions[0]
    assert pos.quantity == pos.cost == 0
    assert pos.realized_pnl == 200 and pos.dividends == Decimal("41.5")
    assert repository.load(uid) == ledger


def test_dividend_multi_currency_and_wrong_net():
    tx = dividend(
        gross=Money(Decimal(50), "USD", Decimal(".9")),
        withholding=Money(Decimal(2), "GBP", Decimal("1.2")),
        net=Money(Decimal("41.6"), "EUR"),
    )
    assert replay(Ledger(Portfolio("S", "EUR"), (TransactionVersion(tx),))).positions[
        0
    ].dividends == Decimal("41.6")
    with pytest.raises(LedgerError, match="líquido"):
        replay(
            Ledger(
                Portfolio("S", "EUR"),
                (TransactionVersion(replace(tx, net=Money(Decimal(50), "EUR"))),),
            )
        )


@pytest.mark.parametrize(
    "fields",
    [
        dict(adjustment_category="UNKNOWN"),
        dict(adjustment_reason=""),
        dict(split_factor=Decimal(0)),
        dict(quantity=Decimal(2)),
    ],
)
def test_invalid_adjustment(fields):
    with pytest.raises(LedgerError):
        split(**fields)


def test_split_requires_position():
    with pytest.raises(LedgerError, match="sem posição"):
        replay(Ledger(Portfolio("S", "EUR"), (TransactionVersion(split()),)))


def test_precision_scale_and_half_even():
    assert decimal_input(Decimal("999999999999999999.12345678"))
    assert decimal_input(Decimal(".123456789012"), scale=12, positive=True)
    with pytest.raises(LedgerError):
        Money(Decimal(1), "USD", Decimal(".1234567890123"))
    with localcontext(FINANCIAL_CONTEXT):
        assert Decimal("1.005").quantize(Decimal(".01")) == Decimal("1.00")
        assert Decimal("1.015").quantize(Decimal(".01")) == Decimal("1.02")


def test_repeating_average_and_full_close(trade):
    transactions = [
        trade(quantity="3", price="1"),
        trade(quantity="4", price="2", day=1),
        trade("SELL", "1", "3", day=2),
        trade("SELL", "6", "3", day=3),
    ]
    with localcontext() as ctx:
        ctx.prec = 5
        ctx.rounding = ROUND_UP
        result = replay(
            Ledger(Portfolio("S", "EUR"), tuple(TransactionVersion(tx) for tx in transactions))
        )
    pos = result.positions[0]
    assert pos.quantity == pos.cost == 0 and pos.realized_pnl == Decimal(10)


def test_reverse_split_is_exact(trade):
    ledger = Ledger(
        Portfolio("S", "EUR"),
        (TransactionVersion(trade()), TransactionVersion(split(split_factor=Decimal(".1")))),
    )
    pos = replay(ledger).positions[0]
    assert pos.quantity == 1 and pos.cost == 1000 and pos.average_cost == 1000
