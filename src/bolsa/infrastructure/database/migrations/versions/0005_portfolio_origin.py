"""Preserve portable clone provenance without requiring the source in this database."""
from alembic import op
import sqlalchemy as sa

revision = "0005_portfolio_origin"
down_revision = "0004_manual_financial_events"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("portfolios", sa.Column("origin_portfolio_uid", sa.Text(), nullable=True))
    op.execute("CREATE TRIGGER portfolios_origin_immutable BEFORE UPDATE OF origin_portfolio_uid "
               "ON portfolios WHEN NEW.origin_portfolio_uid IS NOT OLD.origin_portfolio_uid "
               "BEGIN SELECT RAISE(ABORT, 'portfolio origin is immutable'); END")


def downgrade():
    raise RuntimeError("Financial provenance cannot be dropped; use an explicit validated backup restore")
