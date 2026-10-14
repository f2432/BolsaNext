"""Promote retained P1 history to a ledger supporting manual financial events."""
from alembic import op
import sqlalchemy as sa

revision = "0004_manual_financial_events"
down_revision = "0003_portfolio_ledger"
branch_labels = None
depends_on = None

_OLD_COLUMNS = (
    "portfolio_uid", "transaction_version_uid", "transaction_uid", "version_number",
    "previous_version_uid", "recorded_at", "reason", "author", "trade_kind", "ticker",
    "quantity", "price", "price_currency", "price_fx", "commission", "commission_currency",
    "commission_fx", "trade_metadata",
)
_AMOUNTS = ("quantity", "price", "price_fx", "commission", "commission_fx",
            "gross", "gross_fx", "withholding", "withholding_fx", "charges", "charges_fx",
            "net", "net_fx", "split_factor")
_FINANCIAL_COLUMNS = ("quantity", "price", "price_currency", "price_fx", "commission",
                      "commission_currency", "commission_fx", "gross", "gross_currency", "gross_fx",
                      "withholding", "withholding_currency", "withholding_fx", "charges", "charges_currency",
                      "charges_fx", "net", "net_currency", "net_fx", "split_factor", "adjustment_reason")


def upgrade():
    bind = op.get_bind()
    # SQLite legacy mode does not automatically transact DDL. Keep the entire promotion atomic.
    if not bind.connection.driver_connection.in_transaction:
        bind.exec_driver_sql("BEGIN IMMEDIATE")
    actual = {column["name"] for column in sa.inspect(bind).get_columns("portfolio_versions")}
    if actual != set(_OLD_COLUMNS):
        raise RuntimeError("P1 schema does not match the supported promotion contract")
    columns = [
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
        sa.Column("trade_metadata", sa.Text()),
        *(sa.Column(name, sa.Text()) for name in _FINANCIAL_COLUMNS),
    ]
    common = "ticker IS NOT NULL AND trade_metadata IS NOT NULL"
    trade = (common + " AND trade_kind IN ('BUY','SELL') AND quantity IS NOT NULL AND price IS NOT NULL "
             "AND price_currency IS NOT NULL AND commission IS NOT NULL AND commission_currency IS NOT NULL "
             "AND gross IS NULL AND withholding IS NULL AND charges IS NULL AND net IS NULL AND split_factor IS NULL")
    dividend = (common + " AND trade_kind = 'DIVIDEND' AND quantity IS NULL AND price IS NULL AND commission IS NULL "
                "AND gross IS NOT NULL AND gross_currency IS NOT NULL AND withholding IS NOT NULL "
                "AND withholding_currency IS NOT NULL AND charges IS NOT NULL AND charges_currency IS NOT NULL "
                "AND net IS NOT NULL AND net_currency IS NOT NULL AND split_factor IS NULL")
    split = (common + " AND trade_kind = 'ADJUSTMENT' AND split_factor IS NOT NULL AND adjustment_reason IS NOT NULL "
             "AND length(trim(adjustment_reason)) > 0 AND quantity IS NULL AND price IS NULL AND commission IS NULL "
             "AND gross IS NULL AND withholding IS NULL AND charges IS NULL AND net IS NULL")
    dividend_fields = ("gross", "gross_currency", "gross_fx", "withholding", "withholding_currency",
                       "withholding_fx", "charges", "charges_currency", "charges_fx", "net", "net_currency", "net_fx")
    trade_fields = ("quantity", "price", "price_currency", "price_fx", "commission", "commission_currency", "commission_fx")
    trade += " AND " + " AND ".join(f"{name} IS NULL" for name in (*dividend_fields, "adjustment_reason"))
    dividend += " AND " + " AND ".join(f"{name} IS NULL" for name in (*trade_fields, "adjustment_reason"))
    split += " AND " + " AND ".join(f"{name} IS NULL" for name in (*trade_fields, *dividend_fields))
    cancelled = " AND ".join(f"{name} IS NULL" for name in (
        "trade_kind", "ticker", "trade_metadata", *_FINANCIAL_COLUMNS
    ))
    op.create_table(
        "ledger_versions", *columns,
        sa.UniqueConstraint("portfolio_uid", "transaction_uid", "version_number", name="uq_ledger_economic_version"),
        sa.UniqueConstraint("portfolio_uid", "previous_version_uid", name="uq_ledger_successor"),
        sa.UniqueConstraint("portfolio_uid", "transaction_uid", "transaction_version_uid", name="uq_ledger_chain_reference"),
        sa.ForeignKeyConstraint(
            ["portfolio_uid", "transaction_uid", "previous_version_uid"],
            ["ledger_versions.portfolio_uid", "ledger_versions.transaction_uid", "ledger_versions.transaction_version_uid"],
            ondelete="RESTRICT", name="fk_ledger_predecessor",
        ),
        sa.CheckConstraint("version_number > 0", name="ck_ledger_version"),
        sa.CheckConstraint(
            "(version_number = 1 AND previous_version_uid IS NULL AND trade_kind IS NOT NULL) OR "
            "(version_number > 1 AND previous_version_uid IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_ledger_version_predecessor",
        ),
        sa.CheckConstraint(f"({trade}) OR ({dividend}) OR ({split}) OR ({cancelled})", name="ck_ledger_payload"),
        *[sa.CheckConstraint(f"{name} IS NULL OR typeof({name}) = 'text'", name=f"ck_ledger_text_{name}")
          for name in _AMOUNTS],
    )
    op.create_index("ix_ledger_versions_ledger", "ledger_versions", ["portfolio_uid", "transaction_uid", "version_number"])
    names = ", ".join(_OLD_COLUMNS)
    op.execute(f"INSERT INTO ledger_versions ({names}) SELECT {names} FROM portfolio_versions "
               "ORDER BY portfolio_uid, transaction_uid, version_number")
    old_count = bind.exec_driver_sql("SELECT count(*) FROM portfolio_versions").scalar()
    new_count = bind.exec_driver_sql("SELECT count(*) FROM ledger_versions").scalar()
    if old_count != new_count or bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Ledger promotion failed integrity/count validation")
    for action in ("UPDATE", "DELETE"):
        op.execute(f"CREATE TRIGGER ledger_versions_no_{action.lower()} BEFORE {action} "
                   "ON ledger_versions BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END")
    op.execute("CREATE TRIGGER portfolio_versions_retired BEFORE INSERT ON portfolio_versions "
               "BEGIN SELECT RAISE(ABORT, 'P1 history retained; append to ledger_versions'); END")


def downgrade():
    raise RuntimeError("Financial history cannot be dropped; use an explicit validated backup restore")
