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
    assert "JSONDecodeError" not in message("Invalid canonical portfolio: JSONDecodeError")


@pytest.mark.parametrize("mode", ["restore", "complement", "clone"])
def test_transfer_identity_and_explanation(mode):
    from bolsa.app.portfolio_format import PortfolioTransferService, export_portfolio
    from bolsa.app.portfolio_transfer_presentation import prepare_import_display, import_preview_text
    from bolsa.domain.portfolio.ledger import Portfolio
    from bolsa.domain.portfolio.values import PortfolioNotFoundError
    p = Portfolio("Synthetic", "EUR")
    class Repository:
        def load(self, uid):
            if uid == p.portfolio_uid:
                return p
            raise PortfolioNotFoundError("Unknown portfolio")
    transfer = PortfolioTransferService(Repository())
    display = prepare_import_display(transfer, export_portfolio(p), mode=mode,
                                     destination=p if mode == "complement" else None)
    assert display.source_uid == p.portfolio_uid
    assert (display.destination_uid != p.portfolio_uid) is (mode == "clone")
    text = import_preview_text(display)
    assert "None" not in text
    assert str(display.source_uid) in text and str(display.destination_uid) in text
    assert "Conflitos: 0" in text and "Duplicados a ignorar:" in text


def test_transfer_conflict_describes_both_identities_without_confirmation():
    from bolsa.app.portfolio_format import PortfolioTransferService, export_portfolio
    from bolsa.app.portfolio_transfer_presentation import prepare_import_display, import_preview_text
    from bolsa.domain.portfolio.ledger import Portfolio
    p, other = Portfolio("Synthetic", "EUR"), Portfolio("Other", "EUR")
    transfer = PortfolioTransferService(object())  # Destination mismatch precedes any DB access.
    display = prepare_import_display(transfer, export_portfolio(p), mode="complement", destination=other)
    assert display.preview.candidate is None
    text = import_preview_text(display)
    assert str(p.portfolio_uid) in text and str(other.portfolio_uid) in text
    assert "difere do UUID do arquivo" in text


def test_display_never_changes_canonical_json_or_ledger_values():
    from datetime import date
    from bolsa.app.portfolio_format import export_portfolio
    from bolsa.domain.instruments import Instrument
    from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
    from bolsa.domain.portfolio.values import MoneyComponent
    p = Portfolio("Synthetic", "EUR").record(Trade(Instrument("TEST"), TradeType.BUY, Decimal(".12345678"),
        MoneyComponent(Decimal("123.12345678"), "EUR"), MoneyComponent(Decimal(".00000001"), "EUR"),
        date(2026, 1, 1)))
    before = export_portfolio(p)
    position = p.reconstruct().positions[0]
    money(position.cost)
    quantity(position.quantity)
    average_price(position.average_cost)
    assert export_portfolio(p) == before
    assert '"price":"123.12345678"' in before
