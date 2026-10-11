from decimal import Decimal

from sqlalchemy import (Column, Integer, String, Text, Table, ForeignKey, ForeignKeyConstraint,
                        UniqueConstraint, CheckConstraint)
from sqlalchemy.types import TypeDecorator

from bolsa.domain.portfolio.money import canonical
from bolsa.infrastructure.database.base import Base


class DecimalText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return canonical(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


portfolios = Table('portfolios', Base.metadata,
    Column('portfolio_uid', String(36), primary_key=True),
    Column('name', String(120), nullable=False),
    Column('base_currency', String(3), nullable=False),
    Column('origin_portfolio_uid', String(36)),
    Column('ledger_revision', Integer, nullable=False, default=0),
    CheckConstraint('ledger_revision >= 0'))

versions = Table('portfolio_versions', Base.metadata,
    Column('portfolio_uid', String(36), ForeignKey('portfolios.portfolio_uid'), primary_key=True),
    Column('transaction_version_uid', String(36), primary_key=True),
    Column('transaction_uid', String(36), nullable=False),
    Column('version_number', Integer, nullable=False),
    Column('previous_version_uid', String(36)),
    Column('instrument_id', Integer, ForeignKey('instruments.id'), nullable=False),
    Column('quantity', DecimalText(), nullable=False),
    Column('payload', Text, nullable=False),
    UniqueConstraint('portfolio_uid', 'transaction_uid', 'version_number'),
    UniqueConstraint('portfolio_uid', 'previous_version_uid'),
    UniqueConstraint('portfolio_uid', 'transaction_uid', 'transaction_version_uid'),
    ForeignKeyConstraint(['portfolio_uid', 'transaction_uid', 'previous_version_uid'],
                         ['portfolio_versions.portfolio_uid', 'portfolio_versions.transaction_uid',
                          'portfolio_versions.transaction_version_uid']),
    CheckConstraint('version_number >= 1'),
    CheckConstraint('(version_number = 1 AND previous_version_uid IS NULL) OR '
                    '(version_number > 1 AND previous_version_uid IS NOT NULL)'))

components = Table('portfolio_components', Base.metadata,
    Column('portfolio_uid', String(36), primary_key=True),
    Column('transaction_version_uid', String(36), primary_key=True),
    Column('role', String(32), primary_key=True),
    Column('amount', DecimalText(), nullable=False),
    Column('currency', String(3), nullable=False),
    Column('fx_rate', DecimalText()),
    Column('original_text', Text),
    ForeignKeyConstraint(['portfolio_uid', 'transaction_version_uid'],
                         ['portfolio_versions.portfolio_uid', 'portfolio_versions.transaction_version_uid']))
