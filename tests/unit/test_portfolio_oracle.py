"""Independent rational oracle: no production arithmetic/context used for expectations."""
from datetime import date, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from random import Random

import pytest

from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
from bolsa.domain.portfolio.values import MoneyComponent


def rational_replay(rows):
    quantity = cost = realized = Fraction(0)
    for kind, q, price, fee, fx in rows:
        q, price, fee, fx = map(Fraction, (q, price, fee, fx))
        if kind == "BUY":
            quantity += q
            cost += q * price * fx + fee
        else:
            assigned = cost * q / quantity
            quantity -= q
            cost -= assigned
            realized += q * price * fx - fee - assigned
    return quantity, cost, realized


def implemented_replay(rows):
    portfolio = Portfolio("Synthetic oracle", "EUR")
    for index, (kind, q, price, fee, fx) in enumerate(rows):
        portfolio = portfolio.record(Trade(
            Instrument("ORACLE", currency="USD"), TradeType(kind), Decimal(q),
            MoneyComponent(Decimal(price), "USD", Decimal(fx)),
            MoneyComponent(Decimal(fee), "EUR"), date(2020, 1, 1) + timedelta(days=index),
        ))
    return portfolio.reconstruct().position("ORACLE")


CASES = [
    [("BUY", "3", "1", "0", "1"), ("BUY", "1", "2", "0", "1"),
     ("SELL", "1", "3", "0", "1")],
    [("BUY", "0.125", "23.12345678", "0.07", "0.923456789012"),
     ("BUY", "0.375", "11.25", "0.01", "0.91"),
     ("SELL", "0.25", "30", "0.03", "0.94"),
     ("SELL", "0.25", "31", "0.02", "0.93")],
    [("BUY", "3", "1", "1", "1"), ("SELL", "1", "2", "0", "1"),
     ("SELL", "1", "2", "0", "1"), ("SELL", "1", "2", "0", "1")],
    [("BUY", "3", "1", "1", "1"), ("SELL", "3", "2", "0", "1"),
     ("BUY", "2", "5", "1", "1"), ("SELL", "2", "7", "1", "1")],
]


@pytest.mark.parametrize("rows", CASES)
def test_rational_financial_oracle(rows):
    expected = rational_replay(rows)
    actual = implemented_replay(rows)
    # Rational arithmetic is exact. For repeating open averages, bound the
    # documented 50-digit Decimal approximation independently at 40 digits.
    for observed, oracle in zip((actual.quantity, actual.cost, actual.realized_pnl), expected):
        assert abs(Fraction(observed) - oracle) <= Fraction(1, 10**40)
    if expected[0] == 0:
        assert actual.cost == actual.average_cost == 0
        assert Fraction(actual.realized_pnl) == expected[2]


def test_oracle_is_independent_of_ambient_context():
    with localcontext() as context:
        context.prec = 6
        actual = implemented_replay(CASES[1])
    assert Fraction(actual.realized_pnl) == rational_replay(CASES[1])[2]


def test_full_closure_conserves_exact_cashflows():
    rng = Random(20261014)
    for _ in range(100):
        quantity = rng.randrange(3, 20)
        rows = [("BUY", str(quantity), str(rng.randrange(1, 90)), "0.07", "0.923456789012")]
        for index in range(quantity):
            rows.append(("SELL", "1", str(index + 11), "0.03", "0.91"))
        actual = implemented_replay(rows)
        assert Fraction(actual.realized_pnl) == rational_replay(rows)[2]
