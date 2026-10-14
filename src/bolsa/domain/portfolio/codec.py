from datetime import date, datetime
import json
from uuid import UUID

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.ledger import Trade, TradeType, TransactionVersion
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError

def encode_version_fields(version):
    values = dict(
        portfolio_uid=str(version.portfolio_uid), transaction_uid=str(version.transaction_uid),
        transaction_version_uid=str(version.transaction_version_uid),
        version_number=version.version_number,
        previous_version_uid=str(version.previous_version_uid) if version.previous_version_uid else None,
        recorded_at=version.recorded_at.isoformat(), reason=version.reason, author=version.author,
    )
    trade = version.trade
    if trade is not None:
        instrument = trade.instrument
        metadata = dict(
            instrument=dict(ticker=instrument.ticker, name=instrument.name, exchange=instrument.exchange,
                            currency=instrument.currency, asset_type=instrument.asset_type.value),
            executed_at=trade.executed_at.isoformat(),
            precision="instant" if isinstance(trade.executed_at, datetime) else "date",
            broker_sequence=trade.broker_sequence,
            settlement_date=trade.settlement_date.isoformat() if trade.settlement_date else None,
            notes=trade.notes, source=trade.source, account_ref=trade.account_ref,
            external_id=trade.external_id, original_facts=trade.original_facts,
        )
        values.update(ticker=instrument.ticker,
                      trade_metadata=json.dumps(metadata, sort_keys=True, separators=(",", ":")))
        if isinstance(trade, Trade):
            values.update(
                trade_kind=trade.kind.value, quantity=trade.quantity,
                price=trade.unit_price.amount, price_currency=trade.unit_price.currency,
                price_fx=trade.unit_price.historical_fx, commission=trade.commission.amount,
                commission_currency=trade.commission.currency, commission_fx=trade.commission.historical_fx,
            )
        elif isinstance(trade, Dividend):
            values["trade_kind"] = "DIVIDEND"
            for name in ("gross", "withholding", "charges", "net"):
                component = getattr(trade, name)
                values.update({name: component.amount, name + "_currency": component.currency,
                               name + "_fx": component.historical_fx})
        elif isinstance(trade, Split):
            values.update(trade_kind="ADJUSTMENT", split_factor=trade.factor,
                          adjustment_reason=trade.adjustment_reason)
    return values


def decode_version_fields(row):
    trade = None
    if row["trade_kind"] is not None:
        metadata = json.loads(row["trade_metadata"])
        instrument = metadata.pop("instrument")
        instrument["asset_type"] = AssetType(instrument["asset_type"])
        if instrument["ticker"] != row["ticker"]:
            raise PortfolioError("Inconsistent instrument snapshot")
        precision = metadata.pop("precision")
        if precision not in ("instant", "date"):
            raise PortfolioError("Unknown execution precision")
        metadata["executed_at"] = (
            datetime.fromisoformat(metadata["executed_at"]) if precision == "instant"
            else date.fromisoformat(metadata["executed_at"])
        )
        if metadata["settlement_date"]:
            metadata["settlement_date"] = date.fromisoformat(metadata["settlement_date"])
        metadata["original_facts"] = tuple(tuple(pair) for pair in metadata["original_facts"])
        if row["trade_kind"] in ("BUY", "SELL"):
            trade = Trade(
                Instrument(**instrument), TradeType(row["trade_kind"]), row["quantity"],
                MoneyComponent(row["price"], row["price_currency"], row["price_fx"]),
                MoneyComponent(row["commission"], row["commission_currency"], row["commission_fx"]),
                **metadata,
            )
        elif row["trade_kind"] == "DIVIDEND":
            components = {name: MoneyComponent(row[name], row[name + "_currency"], row[name + "_fx"])
                          for name in ("gross", "withholding", "charges", "net")}
            trade = Dividend(Instrument(**instrument), **components, **metadata)
        elif row["trade_kind"] == "ADJUSTMENT":
            trade = Split(Instrument(**instrument), row["split_factor"], row["adjustment_reason"], **metadata)
        else:
            raise PortfolioError("Unsupported persisted financial event")
    return TransactionVersion(
        UUID(row["portfolio_uid"]), UUID(row["transaction_uid"]), trade, row["version_number"],
        UUID(row["previous_version_uid"]) if row["previous_version_uid"] else None,
        UUID(row["transaction_version_uid"]), datetime.fromisoformat(row["recorded_at"]),
        row["reason"], row["author"],
    )


