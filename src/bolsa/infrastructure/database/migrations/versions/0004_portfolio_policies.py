"""Optional immutable investment-policy history."""
from alembic import op
from bolsa.infrastructure.database.policy_tables import policies

revision = '0004_portfolio_policies'
down_revision = '0003_portfolio_ledger'
branch_labels = None
depends_on = None


def upgrade():
    policies.create(op.get_bind())
    for action in ('UPDATE','DELETE'):
        op.execute(f"CREATE TRIGGER immutable_portfolio_policies_{action.lower()} BEFORE {action} ON portfolio_policies "
                   "BEGIN SELECT RAISE(ABORT, 'Policy history is immutable'); END")


def downgrade():
    raise RuntimeError('Restaurar backup validado; não eliminar história de políticas.')
