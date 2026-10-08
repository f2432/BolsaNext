"""Baseline do schema V0.2.

Revision ID: 0001_v02_baseline
Revises:
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_v02_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("market", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_instruments_ticker",
        "instruments",
        ["ticker"],
        unique=True,
    )

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_watchlists_name",
        "watchlists",
        ["name"],
        unique=True,
    )

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("watchlist_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["watchlist_id"],
            ["watchlists.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "watchlist_id",
            "instrument_id",
            name="uq_watchlist_instrument",
        ),
    )
    op.create_index(
        "ix_watchlist_items_instrument_id",
        "watchlist_items",
        ["instrument_id"],
        unique=False,
    )
    op.create_index(
        "ix_watchlist_items_watchlist_id",
        "watchlist_items",
        ["watchlist_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_watchlist_items_watchlist_id",
        table_name="watchlist_items",
    )
    op.drop_index(
        "ix_watchlist_items_instrument_id",
        table_name="watchlist_items",
    )
    op.drop_table("watchlist_items")

    op.drop_index("ix_watchlists_name", table_name="watchlists")
    op.drop_table("watchlists")

    op.drop_index("ix_instruments_ticker", table_name="instruments")
    op.drop_table("instruments")
