from datetime import date, datetime
import json
from uuid import UUID

from sqlalchemy import Column, MetaData, Table, select, update

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.ledger import Portfolio, Trade, TradeType, TransactionVersion
from bolsa.domain.portfolio.values import LedgerConflictError, MoneyComponent, PortfolioError
from bolsa.infrastructure.database.decimal_type import ExactDecimalText


def _encode(version):
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
        values.update(
            trade_kind=trade.kind.value, ticker=instrument.ticker, quantity=trade.quantity,
            price=trade.unit_price.amount, price_currency=trade.unit_price.currency,
            price_fx=trade.unit_price.historical_fx, commission=trade.commission.amount,
            commission_currency=trade.commission.currency, commission_fx=trade.commission.historical_fx,
            trade_metadata=json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        )
    return values


def _decode(row):
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
        trade = Trade(
            Instrument(**instrument), TradeType(row["trade_kind"]), row["quantity"],
            MoneyComponent(row["price"], row["price_currency"], row["price_fx"]),
            MoneyComponent(row["commission"], row["commission_currency"], row["commission_fx"]),
            **metadata,
        )
    return TransactionVersion(
        UUID(row["portfolio_uid"]), UUID(row["transaction_uid"]), trade, row["version_number"],
        UUID(row["previous_version_uid"]) if row["previous_version_uid"] else None,
        UUID(row["transaction_version_uid"]), datetime.fromisoformat(row["recorded_at"]),
        row["reason"], row["author"],
    )


class SqlAlchemyPortfolioRepository:
    """Explicit SQLite transactions, connection per call, no personal-path discovery."""

    def __init__(self, engine):
        if engine.dialect.name != "sqlite":
            raise PortfolioError("P1 repository requires SQLite")
        self._engine = engine
        metadata = MetaData()
        self._portfolios = Table("portfolios", metadata, autoload_with=engine)
        self._versions = Table(
            "portfolio_versions", metadata,
            *(Column(name, ExactDecimalText()) for name in (
                "quantity", "price", "price_fx", "commission", "commission_fx"
            )), autoload_with=engine,
        )
        self._instruments = metadata.tables["instruments"]

    def _load(self, connection, uid):
        row = connection.execute(select(self._portfolios).where(
            self._portfolios.c.portfolio_uid == str(uid)
        )).mappings().one_or_none()
        if row is None:
            raise PortfolioError("Unknown portfolio")
        rows = connection.execute(select(self._versions).where(
            self._versions.c.portfolio_uid == str(uid)
        ).order_by(self._versions.c.transaction_uid, self._versions.c.version_number)).mappings()
        versions = tuple(_decode(version) for version in rows)
        if row["ledger_revision"] != len(versions):
            raise PortfolioError("Ledger revision does not match audit history")
        return Portfolio(row["name"], row["base_currency"], uid, versions)

    def load(self, portfolio_uid: UUID) -> Portfolio:
        with self._engine.connect() as connection:
            # SQLite's legacy driver mode does not start a snapshot for SELECT alone.
            connection.exec_driver_sql("BEGIN")
            return self._load(connection, portfolio_uid)

    def create(self, portfolio: Portfolio) -> None:
        if portfolio.versions:
            raise PortfolioError("Create an empty portfolio before appending ledger events")
        with self._engine.begin() as connection:
            connection.execute(self._portfolios.insert().values(
                portfolio_uid=str(portfolio.portfolio_uid), name=portfolio.name,
                base_currency=portfolio.base_currency, ledger_revision=0,
            ))

    def save(self, portfolio: Portfolio, *, expected_revision: int) -> None:
        if type(expected_revision) is not int or expected_revision < 0:
            raise LedgerConflictError("Invalid expected revision")
        with self._engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                current = self._load(connection, portfolio.portfolio_uid)
                if current.ledger_revision != expected_revision:
                    raise LedgerConflictError("Obsolete portfolio revision")
                if current.base_currency != portfolio.base_currency or current.name != portfolio.name:
                    raise PortfolioError("Portfolio identity/currency changes are not supported")
                prior = {v.transaction_version_uid: v for v in current.versions}
                proposed = {v.transaction_version_uid: v for v in portfolio.versions}
                if any(proposed.get(uid) != version for uid, version in prior.items()):
                    raise PortfolioError("Existing history cannot be removed or rewritten")
                portfolio.reconstruct()  # Validate entire candidate under the database write lock.
                appended = [v for v in portfolio.versions if v.transaction_version_uid not in prior]
                # Canonical predecessor order, independent of caller tuple order.
                appended.sort(key=lambda v: (v.transaction_uid.hex, v.version_number))
                for version in appended:
                    if version.trade is not None:
                        instrument = version.trade.instrument
                        exists = connection.execute(select(self._instruments.c.id).where(
                            self._instruments.c.ticker == instrument.ticker
                        )).first()
                        if exists is None:
                            connection.execute(self._instruments.insert().values(
                                ticker=instrument.ticker, name=instrument.name,
                                exchange=instrument.exchange, currency=instrument.currency,
                                asset_type=instrument.asset_type.value,
                            ))
                    connection.execute(self._versions.insert().values(**_encode(version)))
                changed = connection.execute(update(self._portfolios).where(
                    self._portfolios.c.portfolio_uid == str(portfolio.portfolio_uid),
                    self._portfolios.c.ledger_revision == expected_revision,
                ).values(ledger_revision=portfolio.ledger_revision)).rowcount
                if changed != 1:
                    raise LedgerConflictError("Concurrent ledger change")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
