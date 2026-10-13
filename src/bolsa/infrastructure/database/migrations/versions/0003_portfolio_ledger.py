"""Add append-only Portfolio BUY/SELL ledger (P1)."""
from alembic import op
import sqlalchemy as sa

revision = "0003_portfolio_ledger"
down_revision = "0002_market_to_exchange"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolios",
        sa.Column("portfolio_uid", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("ledger_revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("ledger_revision >= 0", name="ck_portfolio_revision"),
        sa.CheckConstraint("length(base_currency) = 3", name="ck_portfolio_currency"),
    )
    op.create_table(
        "portfolio_versions",
        sa.Column("portfolio_uid", sa.Text(), sa.ForeignKey("portfolios.portfolio_uid", ondelete="RESTRICT"), primary_key=True),
        sa.Column("transaction_version_uid", sa.Text(), primary_key=True),
        sa.Column("transaction_uid", sa.Text(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("previous_version_uid", sa.Text()),
        sa.Column("recorded_at", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("trade_kind", sa.Text()),
        sa.Column("ticker", sa.String(32), sa.ForeignKey("instruments.ticker", ondelete="RESTRICT")),
        sa.Column("quantity", sa.Text()),
        sa.Column("price", sa.Text()),
        sa.Column("price_currency", sa.Text()),
        sa.Column("price_fx", sa.Text()),
        sa.Column("commission", sa.Text()),
        sa.Column("commission_currency", sa.Text()),
        sa.Column("commission_fx", sa.Text()),
        sa.Column("trade_metadata", sa.Text()),
        sa.UniqueConstraint("portfolio_uid", "transaction_uid", "version_number", name="uq_portfolio_economic_version"),
        sa.UniqueConstraint("portfolio_uid", "previous_version_uid", name="uq_portfolio_successor"),
        sa.UniqueConstraint("portfolio_uid", "transaction_uid", "transaction_version_uid", name="uq_portfolio_chain_reference"),
        sa.ForeignKeyConstraint(
            ["portfolio_uid", "transaction_uid", "previous_version_uid"],
            ["portfolio_versions.portfolio_uid", "portfolio_versions.transaction_uid", "portfolio_versions.transaction_version_uid"],
            ondelete="RESTRICT", name="fk_portfolio_predecessor",
        ),
        sa.CheckConstraint("version_number > 0", name="ck_portfolio_version"),
        sa.CheckConstraint(
            "(version_number = 1 AND previous_version_uid IS NULL AND trade_kind IS NOT NULL) OR "
            "(version_number > 1 AND previous_version_uid IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_portfolio_version_predecessor",
        ),
        sa.CheckConstraint(
            "(trade_kind IN ('BUY', 'SELL') AND ticker IS NOT NULL AND quantity IS NOT NULL "
            "AND price IS NOT NULL AND price_currency IS NOT NULL AND commission IS NOT NULL "
            "AND commission_currency IS NOT NULL AND trade_metadata IS NOT NULL) OR "
            "(trade_kind IS NULL AND ticker IS NULL AND quantity IS NULL AND price IS NULL "
            "AND price_currency IS NULL AND price_fx IS NULL AND commission IS NULL "
            "AND commission_currency IS NULL AND commission_fx IS NULL AND trade_metadata IS NULL)",
            name="ck_portfolio_payload",
        ),
        *[sa.CheckConstraint(f"{column} IS NULL OR typeof({column}) = 'text'",
                            name=f"ck_portfolio_text_{column}")
          for column in ("quantity", "price", "price_fx", "commission", "commission_fx")],
    )
    op.create_index("ix_portfolio_versions_ledger", "portfolio_versions", ["portfolio_uid", "transaction_uid", "version_number"])
    for action in ("UPDATE", "DELETE"):
        op.execute(f"CREATE TRIGGER portfolio_versions_no_{action.lower()} BEFORE {action} "
                   "ON portfolio_versions BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END")
    op.execute("CREATE TRIGGER portfolios_currency_immutable BEFORE UPDATE OF base_currency, portfolio_uid "
               "ON portfolios WHEN NEW.base_currency != OLD.base_currency OR NEW.portfolio_uid != OLD.portfolio_uid "
               "BEGIN SELECT RAISE(ABORT, 'portfolio identity/currency is immutable'); END")


def downgrade():
    raise RuntimeError("Financial history cannot be dropped; use an explicit validated backup restore")
