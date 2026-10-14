"""Independent immutable policy history; no mutation of financial events."""
from alembic import op
import sqlalchemy as sa

revision = "0006_portfolio_policies"
down_revision = "0005_portfolio_origin"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("portfolios", sa.Column("policy_revision", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "portfolio_policies",
        sa.Column("portfolio_uid", sa.Text(), sa.ForeignKey("portfolios.portfolio_uid", ondelete="RESTRICT"), primary_key=True),
        sa.Column("policy_version_uid", sa.Text(), primary_key=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("previous_version_uid", sa.Text()),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("portfolio_uid", "version_number", name="uq_policy_version"),
        sa.UniqueConstraint("portfolio_uid", "previous_version_uid", name="uq_policy_successor"),
        sa.ForeignKeyConstraint(["portfolio_uid", "previous_version_uid"],
                                ["portfolio_policies.portfolio_uid", "portfolio_policies.policy_version_uid"], ondelete="RESTRICT"),
        sa.CheckConstraint("version_number > 0", name="ck_policy_version"),
        sa.CheckConstraint("(version_number = 1 AND previous_version_uid IS NULL) OR "
                           "(version_number > 1 AND previous_version_uid IS NOT NULL)", name="ck_policy_predecessor"),
    )
    for action in ("UPDATE", "DELETE"):
        op.execute(f"CREATE TRIGGER portfolio_policies_no_{action.lower()} BEFORE {action} "
                   "ON portfolio_policies BEGIN SELECT RAISE(ABORT, 'policy history is append-only'); END")


def downgrade():
    raise RuntimeError("Policy history cannot be dropped; use an explicit validated backup restore")
