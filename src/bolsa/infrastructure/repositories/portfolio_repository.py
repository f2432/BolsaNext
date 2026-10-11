import json

from sqlalchemy import select, insert, update

from bolsa.app.portfolio_codec import version_dict, version_from, money_dict
from bolsa.domain.portfolio.ledger import append_version, replay
from bolsa.domain.portfolio.models import MONEY_FIELDS, Ledger, Portfolio
from bolsa.domain.portfolio.money import Money, LedgerError, StaleRevisionError, canonical
from bolsa.infrastructure.database.models import InstrumentModel
from bolsa.infrastructure.database.portfolio_tables import portfolios, versions, components


class SqlAlchemyPortfolioRepository:
    """A new connection per operation; BEGIN IMMEDIATE serializes SQLite writers."""
    def __init__(self, engine):
        if engine.dialect.name != 'sqlite':
            raise ValueError('Portfolio adapter requires SQLite.')
        self.engine = engine

    def create(self, portfolio):
        with self.engine.begin() as connection:
            connection.execute(insert(portfolios).values(
                portfolio_uid=portfolio.portfolio_uid, name=portfolio.name,
                base_currency=portfolio.base_currency, origin_portfolio_uid=portfolio.origin_portfolio_uid,
                ledger_revision=0))
        return Ledger(portfolio)

    def list_portfolios(self):
        with self.engine.connect() as connection:
            return tuple(Portfolio(r.name, r.base_currency, r.portfolio_uid, r.origin_portfolio_uid)
                         for r in connection.execute(select(portfolios).order_by(portfolios.c.name, portfolios.c.portfolio_uid)))

    def _load(self, connection, portfolio_uid):
        row = connection.execute(select(portfolios).where(portfolios.c.portfolio_uid == portfolio_uid)).first()
        if row is None:
            raise LedgerError('Carteira inexistente.')
        portfolio = Portfolio(row.name, row.base_currency, row.portfolio_uid, row.origin_portfolio_uid)
        revision = row.ledger_revision
        result = []
        money_rows = connection.execute(select(components).where(components.c.portfolio_uid == portfolio_uid)).all()
        monetary = {}
        for component in money_rows:
            monetary.setdefault(component.transaction_version_uid, {})[component.role] = money_dict(
                Money(component.amount, component.currency, component.fx_rate, component.original_text))
        rows = connection.execute(select(versions).where(versions.c.portfolio_uid == portfolio_uid)
                                  .order_by(versions.c.transaction_uid, versions.c.version_number))
        for row in rows:
            data = json.loads(row.payload)
            data['transaction']['quantity'] = canonical(row.quantity)
            for role in MONEY_FIELDS:
                data['transaction'][role] = monetary.get(row.transaction_version_uid, {}).get(role)
            version = version_from(data)
            if (version.transaction.transaction_uid, version.transaction_version_uid, version.version_number,
                version.previous_version_uid) != (row.transaction_uid, row.transaction_version_uid,
                                                  row.version_number, row.previous_version_uid):
                raise LedgerError('Metadados do ledger inconsistentes.')
            result.append(version)
        return Ledger(portfolio, tuple(result), revision)

    def load(self, portfolio_uid):
        with self.engine.connect() as connection:
            # Explicit read transaction ensures metadata and components share one SQLite snapshot.
            connection.exec_driver_sql('BEGIN')
            ledger = self._load(connection, portfolio_uid)
            replay(ledger)
            return ledger

    def _insert_version(self, connection, portfolio_uid, version):
        tx = version.transaction
        model = InstrumentModel.__table__
        instrument_id = connection.execute(select(model.c.id).where(model.c.ticker == tx.instrument.ticker)).scalar_one_or_none()
        if instrument_id is None:
            instrument_id = connection.execute(insert(model).values(ticker=tx.instrument.ticker,
                name=tx.instrument.name, exchange=tx.instrument.exchange, currency=tx.instrument.currency,
                asset_type=tx.instrument.asset_type)).inserted_primary_key[0]
        data = version_dict(version)
        data['transaction'].pop('quantity')
        for role in MONEY_FIELDS:
            data['transaction'].pop(role)
        connection.execute(insert(versions).values(portfolio_uid=portfolio_uid,
            transaction_version_uid=version.transaction_version_uid, transaction_uid=tx.transaction_uid,
            version_number=version.version_number, previous_version_uid=version.previous_version_uid,
            instrument_id=instrument_id, quantity=tx.quantity,
            payload=json.dumps(data, sort_keys=True, separators=(',', ':'))))
        for role in MONEY_FIELDS:
            money = getattr(tx, role)
            if money is not None:
                connection.execute(insert(components).values(portfolio_uid=portfolio_uid,
                    transaction_version_uid=version.transaction_version_uid, role=role,
                    amount=money.amount, currency=money.currency, fx_rate=money.fx_rate,
                    original_text=money.original_text))

    def append(self, portfolio_uid, new_versions, *, expected_revision):
        with self.engine.connect() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            try:
                ledger = self._load(connection, portfolio_uid)
                if ledger.revision != expected_revision:
                    raise StaleRevisionError('Revisão da carteira desatualizada.')
                if not new_versions:
                    return ledger
                for version in new_versions:
                    ledger = append_version(ledger, version, expected_head=version.previous_version_uid)
                    self._insert_version(connection, portfolio_uid, version)
                connection.execute(update(portfolios).where(portfolios.c.portfolio_uid == portfolio_uid)
                                   .values(ledger_revision=ledger.revision))
                connection.commit()
                return ledger
            except BaseException:
                connection.rollback()
                raise

    def import_ledger(self, incoming, *, expected_revision):
        from dataclasses import replace
        from bolsa.domain.portfolio.importing import merge_ledger, ImportRejected, ImportReport
        portfolio = incoming.portfolio
        with self.engine.connect() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            try:
                exists = connection.execute(select(portfolios.c.portfolio_uid)
                                            .where(portfolios.c.portfolio_uid == portfolio.portfolio_uid)).first()
                if expected_revision is None:
                    if exists:
                        raise StaleRevisionError('A carteira surgiu depois da pré-visualização.')
                    existing = Ledger(portfolio)
                else:
                    if not exists:
                        raise StaleRevisionError('Carteira de destino inexistente.')
                    existing = self._load(connection, portfolio.portfolio_uid)
                    if existing.revision != expected_revision:
                        raise StaleRevisionError('Importação obsoleta; repetir pré-visualização.')
                candidate, report = merge_ledger(existing, incoming)
                if not exists:
                    connection.execute(insert(portfolios).values(portfolio_uid=portfolio.portfolio_uid,
                        name=portfolio.name, base_currency=portfolio.base_currency,
                        origin_portfolio_uid=portfolio.origin_portfolio_uid, ledger_revision=0))
                stored_ids = {v.transaction_version_uid for v in existing.versions}
                for version in candidate.versions:
                    if version.transaction_version_uid not in stored_ids:
                        self._insert_version(connection, portfolio.portfolio_uid, version)
                connection.execute(update(portfolios).where(portfolios.c.portfolio_uid == portfolio.portfolio_uid)
                                   .values(ledger_revision=candidate.revision))
                connection.commit()
                return candidate, replace(report, status='completed' if report.inserted else 'no_changes')
            except (StaleRevisionError, ImportRejected):
                connection.rollback()
                raise
            except Exception as exc:
                connection.rollback()
                raise ImportRejected(ImportReport(rejected=(f'Falha de escrita: {exc}',))) from exc
