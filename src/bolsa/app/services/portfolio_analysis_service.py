from dataclasses import dataclass
from decimal import Decimal, localcontext
from uuid import UUID

from bolsa.app.ports.portfolio import PortfolioRepository
from bolsa.domain.portfolio.ledger import Portfolio
from bolsa.domain.portfolio.reconciliation import ReconciliationReport, reconcile
from bolsa.domain.portfolio.risk import RiskReport, evaluate_risk
from bolsa.domain.portfolio.valuation import ValuationResult
from bolsa.domain.portfolio.values import FINANCIAL_CONTEXT, exact_sum


@dataclass(frozen=True, slots=True)
class PortfolioAnalysis:
    portfolio: Portfolio
    reconciliation: ReconciliationReport
    risk: RiskReport
    realized_pnl: Decimal
    dividend_income: Decimal
    unrealized_pnl: Decimal | None
    composite_result: Decimal | None
    accounting_confirmed: bool


class PortfolioAnalysisService:
    def __init__(self, repository: PortfolioRepository):
        self._repository = repository

    def analyze(self, portfolio_uid: UUID, valuation: ValuationResult, *, sectors=None) -> PortfolioAnalysis:
        portfolio = self._repository.load(portfolio_uid)
        return self.analyze_snapshot(portfolio, valuation, sectors=sectors)

    @staticmethod
    def analyze_snapshot(portfolio: Portfolio, valuation: ValuationResult, *, sectors=None) -> PortfolioAnalysis:
        portfolio_uid = portfolio.portfolio_uid
        report = reconcile(portfolio, valuation=valuation)
        risk = evaluate_risk(portfolio, valuation, sectors)
        current = (valuation.portfolio_uid == portfolio_uid and valuation.ledger_revision == portfolio.ledger_revision
                   and valuation.base_currency == portfolio.base_currency and valuation.complete
                   and valuation.accounting_confirmed and not portfolio.reconstruct().pending_reconciliation)
        with localcontext(FINANCIAL_CONTEXT):
            positions = portfolio.reconstruct().positions
            realized = exact_sum(*(p.realized_pnl for p in positions))
            dividends = exact_sum(*(p.dividend_income for p in positions))
            unrealized = valuation.total_unrealized_pnl if current else None
            composite = exact_sum(realized, dividends, unrealized) if unrealized is not None else None
        return PortfolioAnalysis(portfolio, report, risk, realized, dividends, unrealized, composite,
                                 not portfolio.reconstruct().pending_reconciliation)
