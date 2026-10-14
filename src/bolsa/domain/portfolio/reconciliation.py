from dataclasses import dataclass
from enum import StrEnum
from decimal import Decimal

from bolsa.domain.portfolio.ledger import Portfolio, Position, effective_versions
from bolsa.domain.portfolio.valuation import ValuationResult
from bolsa.domain.portfolio.values import PortfolioError


class ReconciliationState(StrEnum):
    CONSISTENT = "consistent"
    DISCREPANCY = "discrepancy"
    INFORMATION_INSUFFICIENT = "information_insufficient"


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    state: ReconciliationState
    version_count: int
    effective_operation_count: int
    issues: tuple[str, ...]


def reconcile(portfolio: Portfolio, *, projection: tuple[Position, ...] | None = None,
              valuation: ValuationResult | None = None) -> ReconciliationReport:
    """Compare derived data to replay; never repair or interpret broker facts."""
    try:
        result = portfolio.reconstruct()
        effective = len(effective_versions(portfolio.portfolio_uid, portfolio.versions))
    except PortfolioError as exc:
        return ReconciliationReport(ReconciliationState.DISCREPANCY, len(portfolio.versions), 0, (str(exc),))
    issues = []
    if projection is not None:
        if any(not isinstance(p, Position) for p in projection):
            return ReconciliationReport(ReconciliationState.DISCREPANCY, len(portfolio.versions), effective,
                                        ("Invalid projection object",))
        expected = {p.ticker: p for p in result.positions}
        supplied = {p.ticker: p for p in projection}
        if len(supplied) != len(projection):
            issues.append("Duplicate projection instruments")
        for ticker in sorted(expected.keys() | supplied.keys()):
            if expected.get(ticker) != supplied.get(ticker):
                issues.append(f"Projection differs from ledger replay: {ticker}")
            if ticker in supplied:
                for field in ("quantity", "cost", "average_cost", "realized_pnl", "dividend_income"):
                    value = getattr(supplied[ticker], field)
                    if not isinstance(value, Decimal) or not value.is_finite():
                        issues.append(f"Invalid financial projection field: {ticker}.{field}")
    if issues:
        return ReconciliationReport(ReconciliationState.DISCREPANCY, len(portfolio.versions), effective, tuple(issues))
    if result.pending_reconciliation:
        return ReconciliationReport(ReconciliationState.INFORMATION_INSUFFICIENT, len(portfolio.versions), effective,
                                    tuple(f"Observed settlement difference pending: {p.transaction_uid} "
                                          f"{p.difference_base} {portfolio.base_currency}" for p in result.pending_reconciliation))
    if valuation is not None and (not valuation.complete or valuation.portfolio_uid != portfolio.portfolio_uid or
                                  valuation.ledger_revision != portfolio.ledger_revision or
                                  valuation.base_currency != portfolio.base_currency):
        return ReconciliationReport(ReconciliationState.INFORMATION_INSUFFICIENT, len(portfolio.versions), effective,
                                    ("Current valuation is incomplete or does not match ledger revision",))
    return ReconciliationReport(ReconciliationState.CONSISTENT, len(portfolio.versions), effective, ())
