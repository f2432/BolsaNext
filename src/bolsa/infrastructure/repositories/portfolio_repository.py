from uuid import UUID

from sqlalchemy import Column, MetaData, Table, select, update

from bolsa.domain.portfolio.ledger import Portfolio
from bolsa.domain.portfolio.values import (
    LedgerConflictError, PortfolioError, PortfolioNotFoundError, PortfolioPersistenceError,
)
from bolsa.infrastructure.database.decimal_type import ExactDecimalText


from bolsa.domain.portfolio.codec import encode_version_fields as _encode, decode_version_fields as _decode

class SqlAlchemyPortfolioRepository:
    """Explicit SQLite transactions, connection per call, no personal-path discovery."""

    def __init__(self, engine):
        if engine.dialect.name != "sqlite":
            raise PortfolioError("P1 repository requires SQLite")
        self._engine = engine
        metadata = MetaData()
        self._portfolios = Table("portfolios", metadata, autoload_with=engine)
        self._versions = Table(
            "ledger_versions", metadata,
            *(Column(name, ExactDecimalText()) for name in (
                "quantity", "price", "price_fx", "commission", "commission_fx",
                "gross", "gross_fx", "withholding", "withholding_fx", "charges", "charges_fx",
                "net", "net_fx", "split_factor"
            )), autoload_with=engine,
        )
        self._instruments = metadata.tables["instruments"]

    def _load(self, connection, uid):
        row = connection.execute(select(self._portfolios).where(
            self._portfolios.c.portfolio_uid == str(uid)
        )).mappings().one_or_none()
        if row is None:
            raise PortfolioNotFoundError("Unknown portfolio")
        rows = connection.execute(select(self._versions).where(
            self._versions.c.portfolio_uid == str(uid)
        ).order_by(self._versions.c.transaction_uid, self._versions.c.version_number)).mappings()
        versions = tuple(_decode(version) for version in rows)
        if row["ledger_revision"] != len(versions):
            raise PortfolioError("Ledger revision does not match audit history")
        return Portfolio(row["name"], row["base_currency"], uid, versions,
                         UUID(row["origin_portfolio_uid"]) if row["origin_portfolio_uid"] else None)

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
                origin_portfolio_uid=str(portfolio.origin_portfolio_uid) if portfolio.origin_portfolio_uid else None,
            ))

    def save(self, portfolio: Portfolio, *, expected_revision: int) -> None:
        if type(expected_revision) is not int or expected_revision < 0:
            raise LedgerConflictError("Invalid expected revision")
        self._write(portfolio, expected_revision=expected_revision)

    def import_atomic(self, portfolio: Portfolio, *, expected_revision: int | None) -> None:
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
            raise LedgerConflictError("Invalid expected revision")
        try:
            self._write(portfolio, expected_revision=expected_revision)
        except PortfolioError:
            raise
        except Exception as exc:
            raise PortfolioPersistenceError("Import transaction rolled back") from exc

    def _write(self, portfolio: Portfolio, *, expected_revision: int | None) -> None:
        with self._engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                if expected_revision is None:
                    # Creation and all ledger inserts belong to the SAME transaction.
                    exists = connection.execute(select(self._portfolios.c.portfolio_uid).where(
                        self._portfolios.c.portfolio_uid == str(portfolio.portfolio_uid)
                    )).first()
                    if exists:
                        raise LedgerConflictError("Portfolio created after preview")
                    connection.execute(self._portfolios.insert().values(
                        portfolio_uid=str(portfolio.portfolio_uid), name=portfolio.name,
                        base_currency=portfolio.base_currency, ledger_revision=0,
                        origin_portfolio_uid=str(portfolio.origin_portfolio_uid) if portfolio.origin_portfolio_uid else None,
                    ))
                    expected_revision = 0
                current = self._load(connection, portfolio.portfolio_uid)
                if current.ledger_revision != expected_revision:
                    raise LedgerConflictError("Obsolete portfolio revision")
                if (current.base_currency, current.name, current.origin_portfolio_uid) != (
                    portfolio.base_currency, portfolio.name, portfolio.origin_portfolio_uid
                ):
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
