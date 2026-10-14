from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from bolsa.domain.instruments.instrument import Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError

D = Decimal
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
ASSET = Instrument("TEST")


def money(value, currency="EUR", fx=None):
    return MoneyComponent(D(value), currency, D(fx) if fx else None)


def buy():
    return Trade(ASSET, TradeType.BUY, D(10), money("100"), money("0"), AT)


def dividend(net="41.50"):
    return Dividend(ASSET, money("50"), money("7.5"), money("1"), money(net), AT + timedelta(days=1))


def split(factor="2", reason="Synthetic 2:1 split"):
    return Split(ASSET, D(factor), reason, AT + timedelta(days=2))


def test_approved_dividend_and_split_preserve_accounting():
    p = Portfolio("Synthetic", "EUR").record(buy()).record(dividend()).record(split())
    position = p.reconstruct().position("TEST")
    assert (position.quantity, position.cost, position.average_cost, position.realized_pnl,
            position.dividend_income) == (D(20), D(1000), D(50), D(0), D("41.50"))
    p = p.record(replace(buy(), kind=TradeType.SELL, quantity=D(20),
                         executed_at=AT + timedelta(days=3)))
    position = p.reconstruct().position("TEST")
    assert (position.quantity, position.cost, position.realized_pnl, position.dividend_income) == (
        D(0), D(0), D(1000), D("41.50")
    )
    p = p.record(replace(buy(), executed_at=AT + timedelta(days=4)))
    assert p.reconstruct().position("TEST").dividend_income == D("41.50")


def test_dividend_has_no_fictitious_quantity_or_execution_price():
    event = dividend()
    assert not hasattr(event, "quantity") and not hasattr(event, "unit_price")
    p = Portfolio("Synthetic", "EUR").record(event)
    position = p.reconstruct().position("TEST")
    assert position.quantity == position.cost == D(0)
    assert position.dividend_income == D("41.50")


def test_dividend_components_convert_individually():
    event = Dividend(ASSET, money("100", "USD", "0.9"), money("5", "GBP", "1.2"),
                     money("1", "EUR"), money("83", "EUR"), AT)
    p = Portfolio("Synthetic", "EUR").record(event)
    assert p.reconstruct().position("TEST").dividend_income == D(83)
    with pytest.raises(PortfolioError, match="Missing historical FX"):
        Portfolio("Synthetic", "EUR").record(replace(event, withholding=money("5", "GBP")))


def test_manual_dividend_mismatch_or_negative_derived_net_rejected_without_mutation():
    p = Portfolio("Synthetic", "EUR").record(buy())
    for event in (dividend("42"), replace(dividend(), withholding=money("100"))):
        with pytest.raises(PortfolioError, match="dividend net"):
            p.record(event)
    assert len(p.versions) == 1
    assert p.reconstruct().position("TEST").dividend_income == D(0)


def test_correction_cancellation_reconstruct_dividends_without_double_counting():
    p = Portfolio("Synthetic", "EUR").record(dividend())
    first = p.versions[0]
    corrected_event = replace(dividend(), gross=money("60"), net=money("51.5"))
    p = p.revise(first.transaction_uid, first.transaction_version_uid, corrected_event, reason="Correct")
    assert p.reconstruct().position("TEST").dividend_income == D("51.5")
    head = p.versions[-1]
    p = p.revise(first.transaction_uid, head.transaction_version_uid, None, reason="Cancel")
    assert p.reconstruct().positions == () and len(p.versions) == 3


def test_split_cancellation_invalidating_sale_is_rejected_atomically():
    p = Portfolio("Synthetic", "EUR").record(buy()).record(split())
    split_head = p.versions[-1]
    p = p.record(replace(buy(), kind=TradeType.SELL, quantity=D(15), executed_at=AT + timedelta(days=3)))
    before = p.reconstruct()
    with pytest.raises(PortfolioError, match="Oversell"):
        p.revise(split_head.transaction_uid, split_head.transaction_version_uid, None, reason="Cancel")
    assert p.reconstruct() == before


@pytest.mark.parametrize("factor", ["0", "-1", "1", "0.5", "2.5", "NaN", "Infinity"])
def test_only_approved_simple_splits_are_accepted(factor):
    with pytest.raises(PortfolioError):
        split(factor)


def test_split_reason_and_open_position_required():
    with pytest.raises(PortfolioError):
        split(reason=" ")
    with pytest.raises(PortfolioError, match="open position"):
        Portfolio("Synthetic", "EUR").record(split())


def test_split_fractional_quantity_preserves_cost():
    p = Portfolio("Synthetic", "EUR").record(replace(buy(), quantity=D("0.5"))).record(split("3"))
    position = p.reconstruct().position("TEST")
    assert position.quantity == D("1.5") and position.cost == D(50)
    assert position.realized_pnl == D(0)


def test_dividend_net_zero_is_valid_and_no_profit_is_invented():
    event = replace(dividend("0"), withholding=money("49"))
    p = Portfolio("Synthetic", "EUR").record(event)
    assert p.reconstruct().position("TEST").dividend_income == D(0)
