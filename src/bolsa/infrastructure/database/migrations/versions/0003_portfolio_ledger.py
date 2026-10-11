"""Append-only Portfolio ledger. Restore a validated backup instead of downgrading."""
from alembic import op

from bolsa.infrastructure.database.portfolio_tables import portfolios, versions, components

revision = '0003_portfolio_ledger'
down_revision = '0002_market_to_exchange'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for table in (portfolios, versions, components):
        table.create(bind)
    op.create_index('ix_portfolio_transaction', 'portfolio_versions', ['portfolio_uid', 'transaction_uid'])
    for table in ('portfolio_versions', 'portfolio_components'):
        for action in ('UPDATE', 'DELETE'):
            op.execute(f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} "
                       "BEGIN SELECT RAISE(ABORT, 'Ledger records are immutable'); END")
    op.execute("CREATE TRIGGER immutable_portfolio_currency BEFORE UPDATE OF base_currency ON portfolios "
               "WHEN NEW.base_currency != OLD.base_currency "
               "BEGIN SELECT RAISE(ABORT, 'Portfolio currency is immutable'); END")


def downgrade():
    raise RuntimeError('Downgrade Portfolio recusado: restaurar backup SQLite validado.')
