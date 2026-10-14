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


def test_audit_details_keep_full_precision_and_original_facts():
    from datetime import date
    from bolsa.app.portfolio_presentation import version_details
    from bolsa.domain.instruments import Instrument
    from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType
    from bolsa.domain.portfolio.values import MoneyComponent
    p = Portfolio("Synthetic", "EUR").record(Trade(Instrument("TEST"), TradeType.BUY, Decimal(".12345678"),
        MoneyComponent(Decimal("123.12345678"), "USD", Decimal(".912345678912")),
        MoneyComponent(Decimal(".00000001"), "EUR"), date(2026, 1, 1),
        original_facts=(("documento", "sintético"),)))
    head = p.versions[0]
    text = version_details(head)
    assert str(head.transaction_uid) in text
    assert "123,12345678 USD" in text and "0,912345678912" in text
    assert "documento: sintético" in text and "None" not in text
    cancelled = p.revise(head.transaction_uid, head.transaction_version_uid, None, reason="Synthetic")
    assert "versões anteriores" in version_details(cancelled.versions[-1])


def test_quote_details_keep_currency_source_and_date_without_repr():
    from datetime import date
    from bolsa.app.portfolio_presentation import quote_details
    from bolsa.domain.portfolio.valuation import PriceQuote, FxQuote, ValuedPosition, ValuationState
    row = ValuedPosition("TEST", ValuationState.AVAILABLE, Decimal("10"), Decimal("1"), None,
                        PriceQuote("TEST", "USD", Decimal("10.12345678"), date(2026, 1, 1), "synthetic"),
                        FxQuote("USD", "EUR", Decimal(".912345678912"), date(2026, 1, 1), "synthetic"))
    text = quote_details(row)
    assert "10,12345678 USD" in text and "0,912345678912 EUR/USD" in text
    assert "2026-01-01" in text and "synthetic" in text
    assert "None" not in text and "Decimal(" not in text
    assert quote_details(None) == "Sem valorização atual."


def test_invalid_presentation_input_rejected_and_unknown_state_not_exposed():
    with pytest.raises(ValueError):
        money(1.2)
    with pytest.raises(ValueError):
        money(Decimal("NaN"))
    assert state_label("future_internal_state") == "Estado não reconhecido"
    assert message("Invalid decimal text") == "Não foi possível validar os dados. Consulta o detalhe e revê os campos."


def test_field_validation_rejects_scale_and_negative_fx_before_save():
    from bolsa.app.portfolio_forms import form_values, form_errors
    from bolsa.domain.portfolio.events import Split
    from bolsa.domain.instruments import Instrument
    from datetime import date
    fields = form_values(Split(Instrument("TEST", currency="EUR"), Decimal("2"), "Synthetic", date(2026, 1, 1)))
    fields["split_factor"] = "1.5"
    assert "split_factor" in form_errors(fields, "EUR")
    fields.update(type="BUY", quantity=".123456789", price_amount="1", price_currency="USD",
                  price_fx="-1", commission_amount="0", commission_currency="EUR", commission_fx="",
                  broker_sequence="-1", external_id="solo")
    errors = form_errors(fields, "EUR")
    assert {"quantity", "price_fx", "broker_sequence", "external_id"} <= errors.keys()
