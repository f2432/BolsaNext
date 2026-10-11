"""Exact, data-only wire representation shared by storage and portability."""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal

from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.portfolio.models import (
    MONEY_FIELDS,
    Transaction,
    TransactionType,
    TransactionVersion,
)
from bolsa.domain.portfolio.money import Money, canonical


def money_dict(money: Money) -> dict:
    return {
        "amount": canonical(money.amount),
        "currency": money.currency,
        "fx_rate": canonical(money.fx_rate) if money.fx_rate is not None else None,
        "original_text": money.original_text,
    }


def money_from(data: dict) -> Money:
    if set(data) != {"amount", "currency", "fx_rate", "original_text"}:
        raise ValueError("Campos monetários não suportados.")
    if type(data["amount"]) is not str or (
        data["fx_rate"] is not None and type(data["fx_rate"]) is not str
    ):
        raise ValueError("Valores financeiros JSON devem ser texto.")
    return Money(
        Decimal(data["amount"]),
        data["currency"],
        Decimal(data["fx_rate"]) if data["fx_rate"] is not None else None,
        data["original_text"],
    )


def version_dict(version: TransactionVersion) -> dict:
    tx = version.transaction
    data = asdict(tx)
    data["quantity"] = canonical(tx.quantity)
    data["split_factor"] = canonical(tx.split_factor) if tx.split_factor is not None else None
    for key in MONEY_FIELDS:
        money = getattr(tx, key)
        data[key] = money_dict(money) if money is not None else None
    data["executed_at"] = tx.executed_at.isoformat()
    data["execution_precision"] = "instant" if isinstance(tx.executed_at, datetime) else "date"
    data["settled_on"] = tx.settled_on.isoformat() if tx.settled_on else None
    return {
        "transaction": data,
        "version_number": version.version_number,
        "transaction_version_uid": version.transaction_version_uid,
        "previous_version_uid": version.previous_version_uid,
        "voided": version.voided,
        "reason": version.reason,
        "recorded_at": version.recorded_at.isoformat(),
        "author": version.author,
    }


def version_from(data: dict) -> TransactionVersion:
    fields = dict(data)
    tx = dict(fields.pop("transaction"))
    # v1/v2 archives written before origin-timezone preservation remain readable.
    tx.setdefault("execution_timezone", None)
    instrument = dict(tx["instrument"])
    instrument["asset_type"] = AssetType(instrument["asset_type"])
    tx["instrument"] = Instrument(**instrument)
    tx["type"] = TransactionType(tx["type"])
    precision = tx.pop("execution_precision")
    if precision not in ("date", "instant"):
        raise ValueError("Precisão temporal inválida.")
    tx["executed_at"] = (datetime.fromisoformat if precision == "instant" else date.fromisoformat)(
        tx["executed_at"]
    )
    tx["settled_on"] = date.fromisoformat(tx["settled_on"]) if tx["settled_on"] else None
    if type(tx["quantity"]) is not str:
        raise ValueError("Quantidade JSON deve ser texto.")
    tx["quantity"] = Decimal(tx["quantity"])
    if tx["split_factor"] is not None:
        if type(tx["split_factor"]) is not str:
            raise ValueError("Fator de split deve ser texto.")
        tx["split_factor"] = Decimal(tx["split_factor"])
    for key in MONEY_FIELDS:
        tx[key] = money_from(tx[key]) if tx[key] is not None else None
    if type(fields["voided"]) is not bool:
        raise ValueError("Estado de anulação inválido.")
    fields["recorded_at"] = datetime.fromisoformat(fields["recorded_at"])
    return TransactionVersion(transaction=Transaction(**tx), **fields)
