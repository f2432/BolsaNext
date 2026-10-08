"""Rename instrument market to exchange.

Revision ID: 0002_market_to_exchange
Revises: 0001_v02_baseline
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_market_to_exchange"
down_revision = "0001_v02_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "instruments",
        "market",
        new_column_name="exchange",
        existing_type=sa.String(length=64),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "instruments",
        "exchange",
        new_column_name="market",
        existing_type=sa.String(length=64),
        existing_nullable=True,
    )
