"""Immutable schema snapshot for the append-only ledger; restore backup to revert."""

from alembic import op
import sqlalchemy as sa

revision = "0003_portfolio_ledger"
down_revision = "0002_market_to_exchange"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolios",
        sa.Column("portfolio_uid", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("origin_portfolio_uid", sa.String(36)),
        sa.Column("ledger_revision", sa.Integer, nullable=False),
        sa.CheckConstraint("ledger_revision >= 0"),
    )
    op.create_table(
        "portfolio_versions",
        sa.Column(
            "portfolio_uid",
            sa.String(36),
            sa.ForeignKey("portfolios.portfolio_uid"),
            primary_key=True,
        ),
        sa.Column("transaction_version_uid", sa.String(36), primary_key=True),
        sa.Column("transaction_uid", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("previous_version_uid", sa.String(36)),
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("quantity", sa.Text, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.UniqueConstraint("portfolio_uid", "transaction_uid", "version_number"),
        sa.UniqueConstraint("portfolio_uid", "previous_version_uid"),
        sa.UniqueConstraint("portfolio_uid", "transaction_uid", "transaction_version_uid"),
        sa.ForeignKeyConstraint(
            ["portfolio_uid", "transaction_uid", "previous_version_uid"],
            [
                "portfolio_versions.portfolio_uid",
                "portfolio_versions.transaction_uid",
                "portfolio_versions.transaction_version_uid",
            ],
        ),
        sa.CheckConstraint("version_number >= 1"),
        sa.CheckConstraint(
            "(version_number = 1 AND previous_version_uid IS NULL) OR "
            "(version_number > 1 AND previous_version_uid IS NOT NULL)"
        ),
    )
    op.create_table(
        "portfolio_components",
        sa.Column("portfolio_uid", sa.String(36), primary_key=True),
        sa.Column("transaction_version_uid", sa.String(36), primary_key=True),
        sa.Column("role", sa.String(32), primary_key=True),
        sa.Column("amount", sa.Text, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", sa.Text),
        sa.Column("original_text", sa.Text),
        sa.ForeignKeyConstraint(
            ["portfolio_uid", "transaction_version_uid"],
            ["portfolio_versions.portfolio_uid", "portfolio_versions.transaction_version_uid"],
        ),
    )
    op.create_index(
        "ix_portfolio_transaction", "portfolio_versions", ["portfolio_uid", "transaction_uid"]
    )
    for table in ("portfolio_versions", "portfolio_components"):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'Ledger records are immutable'); END"
            )
    op.execute(
        "CREATE TRIGGER immutable_portfolio_currency BEFORE UPDATE OF base_currency ON portfolios "
        "WHEN NEW.base_currency != OLD.base_currency "
        "BEGIN SELECT RAISE(ABORT, 'Portfolio currency is immutable'); END"
    )


def downgrade():
    raise RuntimeError("Downgrade Portfolio recusado: restaurar backup SQLite validado.")
