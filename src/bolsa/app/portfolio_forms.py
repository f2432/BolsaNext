"""Text parsing for Portfolio forms, adapted from feature 7d3e4f7."""
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.ledger import Trade, TradeType
from bolsa.domain.portfolio.values import (
    MoneyComponent, SignedMoneyComponent, ReportedSettlement, PortfolioError,
)

MONEY_FIELDS = ("price", "commission", "observed_net", "gross", "withholding", "charges", "net")


def utc_now():
    return datetime.now(timezone.utc)


def decimal_text(text):
    value = text.strip()
    if "," in value and "." in value:
        raise PortfolioError("Não usar separadores de milhares.")
    try:
        result = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise PortfolioError("Número decimal inválido.") from exc
    if not result.is_finite():
        raise PortfolioError("Número decimal finito obrigatório.")
    return result


def transaction_from_form(fields, *, previous=None):
    kind = fields["type"]
    stamp = fields["executed_at"].strip()
    executed = datetime.fromisoformat(stamp) if "T" in stamp or " " in stamp else date.fromisoformat(stamp)
    instrument = Instrument(fields["ticker"], currency=fields["instrument_currency"],
                            asset_type=AssetType(fields["asset_type"]))
    if previous is not None and instrument.ticker == previous.instrument.ticker:
        instrument = replace(previous.instrument, currency=instrument.currency, asset_type=instrument.asset_type)
    kwargs = dict(instrument=instrument, executed_at=executed, notes=fields.get("notes", ""),
                  source=fields.get("source", "").strip() or "manual",
                  account_ref=fields.get("account_ref", "").strip() or None,
                  external_id=fields.get("external_id", "").strip() or None)
    if previous is not None:
        kwargs["original_facts"] = previous.original_facts
    if fields.get("settled_on", "").strip():
        kwargs["settlement_date"] = date.fromisoformat(fields["settled_on"])
    if fields.get("broker_sequence", "").strip():
        kwargs["broker_sequence"] = int(fields["broker_sequence"])

    def money(role, cls=MoneyComponent):
        fx = fields.get(role + "_fx", "").strip()
        return cls(decimal_text(fields[role + "_amount"]), fields[role + "_currency"],
                   decimal_text(fx) if fx else None)

    if fields.get("observed_net_amount", "").strip() and kind != "ADJUSTMENT":
        kwargs["reported_settlement"] = money("observed_net", ReportedSettlement)
    if kind in ("BUY", "SELL"):
        return Trade(kind=TradeType(kind), quantity=decimal_text(fields["quantity"]),
                     unit_price=money("price"), commission=money("commission"), **kwargs)
    if kind == "DIVIDEND":
        return Dividend(gross=money("gross"), withholding=money("withholding"),
                        charges=money("charges"), net=money("net", SignedMoneyComponent), **kwargs)
    if kind == "ADJUSTMENT":
        return Split(factor=decimal_text(fields["split_factor"]),
                     adjustment_reason=fields["adjustment_reason"], **kwargs)
    raise PortfolioError("Operação não suportada.")


def form_values(transaction):
    result = dict(type=transaction.kind.value if isinstance(transaction, Trade) else
                  "DIVIDEND" if isinstance(transaction, Dividend) else "ADJUSTMENT",
                  ticker=transaction.instrument.ticker, instrument_currency=transaction.instrument.currency or "",
                  asset_type=transaction.instrument.asset_type.value,
                  executed_at=transaction.executed_at.isoformat(), notes=transaction.notes,
                  quantity=str(transaction.quantity) if isinstance(transaction, Trade) else "",
                  split_factor=str(transaction.factor) if isinstance(transaction, Split) else "",
                  adjustment_reason=transaction.adjustment_reason if isinstance(transaction, Split) else "",
                  source=transaction.source, account_ref=transaction.account_ref or "",
                  external_id=transaction.external_id or "",
                  broker_sequence=str(transaction.broker_sequence) if transaction.broker_sequence is not None else "",
                  settled_on=transaction.settlement_date.isoformat() if transaction.settlement_date else "")
    for role in MONEY_FIELDS:
        attribute = {"price": "unit_price", "observed_net": "reported_settlement"}.get(role, role)
        component = getattr(transaction, attribute, None)
        result[role + "_amount"] = str(component.amount) if component else ""
        result[role + "_currency"] = component.currency if component else ""
        result[role + "_fx"] = str(component.historical_fx) if component and component.historical_fx is not None else ""
    return result
