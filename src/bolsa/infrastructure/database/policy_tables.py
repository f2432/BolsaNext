from sqlalchemy import Table, Column, String, Integer, Text, ForeignKey, UniqueConstraint, ForeignKeyConstraint

from bolsa.infrastructure.database.base import Base
from bolsa.infrastructure.database.portfolio_tables import portfolios  # noqa: F401

policies = Table('portfolio_policies',Base.metadata,
    Column('portfolio_uid',String(36),ForeignKey('portfolios.portfolio_uid'),primary_key=True),
    Column('policy_version_uid',String(36),primary_key=True),
    Column('version_number',Integer,nullable=False),
    Column('previous_version_uid',String(36)),
    Column('payload',Text,nullable=False),
    UniqueConstraint('portfolio_uid','version_number'),
    UniqueConstraint('portfolio_uid','previous_version_uid'),
    ForeignKeyConstraint(['portfolio_uid','previous_version_uid'],
                         ['portfolio_policies.portfolio_uid','portfolio_policies.policy_version_uid']))
