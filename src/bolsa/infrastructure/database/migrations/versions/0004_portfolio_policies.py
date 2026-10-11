"""Immutable schema snapshot for optional policy history."""

from alembic import op
import sqlalchemy as sa

revision = "0004_portfolio_policies"
down_revision = "0003_portfolio_ledger"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolio_policies",
        sa.Column(
            "portfolio_uid",
            sa.String(36),
            sa.ForeignKey("portfolios.portfolio_uid"),
            primary_key=True,
        ),
        sa.Column("policy_version_uid", sa.String(36), primary_key=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("previous_version_uid", sa.String(36)),
        sa.Column("payload", sa.Text, nullable=False),
        sa.UniqueConstraint("portfolio_uid", "version_number"),
        sa.UniqueConstraint("portfolio_uid", "previous_version_uid"),
        sa.ForeignKeyConstraint(
            ["portfolio_uid", "previous_version_uid"],
            ["portfolio_policies.portfolio_uid", "portfolio_policies.policy_version_uid"],
        ),
    )
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER immutable_portfolio_policies_{action.lower()} BEFORE {action} ON portfolio_policies "
            "BEGIN SELECT RAISE(ABORT, 'Policy history is immutable'); END"
        )


def downgrade():
    raise RuntimeError("Restaurar backup validado; não eliminar história de políticas.")
