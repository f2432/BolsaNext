from decimal import Decimal, localcontext

import pytest

from bolsa.app.portfolio_presentation import (
    money, quantity, average_price, fx_rate, percentage, message, state_label,
)


def test_pt_pt_formats_without_changing_values():
    value = Decimal("1234.56789012345678901234567890123456789")
    original = value.as_tuple()
    assert money(value, "EUR") == "1\N{NO-BREAK SPACE}234,57 EUR"
    assert quantity(Decimal(".12345678")) == "0,12345678"
    assert quantity(Decimal("10.00000000")) == "10"
    assert average_price(Decimal(".12345678")) == "0,12345678"
    assert average_price(Decimal("10")) == "10,00"
    assert fx_rate(Decimal(".923456789012")) == "0,923456789012"
    assert percentage(Decimal(".123456")) == "12,35 %"
    assert value.as_tuple() == original
    assert average_price(Decimal(".00000000000123456")) == "1,235 × 10^-12"


def test_large_magnitude_and_context_do_not_change_rounding():
    with localcontext() as context:
        context.prec = 3
        assert money(Decimal("1234567890123456789012345678901234567890.125")) == (
            "1\N{NO-BREAK SPACE}234\N{NO-BREAK SPACE}567\N{NO-BREAK SPACE}890\N{NO-BREAK SPACE}123"
            "\N{NO-BREAK SPACE}456\N{NO-BREAK SPACE}789\N{NO-BREAK SPACE}012\N{NO-BREAK SPACE}345"
            "\N{NO-BREAK SPACE}678\N{NO-BREAK SPACE}901\N{NO-BREAK SPACE}234\N{NO-BREAK SPACE}567"
            "\N{NO-BREAK SPACE}890,12"
        )
        assert money(Decimal("-0.001")) == "0,00"


@pytest.mark.parametrize("formatter", [money, quantity, average_price, fx_rate, percentage])
def test_missing_values_are_explicit(formatter):
    assert formatter(None) == "Indisponível"


@pytest.mark.parametrize("code,label", [("information_insufficient", "Informação insuficiente"),
                                        ("completed", "Concluída"), ("exceeded", "Limite excedido")])
def test_internal_states_only_translated_for_display(code, label):
    assert state_label(code) == label


def test_named_errors_translated_with_identifiers_preserved():
    assert message("Same-currency FX must equal one") == (
        "Quando a moeda é igual à moeda base, deixa a taxa FX vazia ou indica 1."
    )
    assert "Atualiza a valorização" in message("Current valuation is incomplete or does not match ledger revision")
    assert message("Conflicting version identity: abc") == "Conflito de identidade de versão: abc"
    assert message(None) == ""
