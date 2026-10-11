from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from bolsa.app.services.portfolio_transfer_service import PortfolioTransferService
from bolsa.app.services.portfolio_policy_service import PortfolioPolicyService
from bolsa.domain.portfolio.ledger import replay
from bolsa.domain.portfolio.money import FINANCIAL_CONTEXT
from bolsa.domain.portfolio.reconciliation import reconcile


@dataclass(frozen=True, slots=True)
class PortfolioDashboard:
    portfolios: tuple
    ledger: object | None
    replay: object | None
    reconciliation: object | None
    valuation: object | None = None
    risk: object | None = None
    realized_total: Decimal = Decimal(0)
    dividends_total: Decimal = Decimal(0)


class PortfolioDashboardService:
    def __init__(self, portfolio_service, valuation_service):
        self.portfolio = portfolio_service
        self.repository = portfolio_service.repository
        self.valuation = valuation_service
        self.transfer = PortfolioTransferService(self.repository)
        self.policy = PortfolioPolicyService(self.repository)

    def overview(self, portfolio_uid=None, *, market=False):
        portfolios = self.repository.list_portfolios()
        selected = next((p for p in portfolios if p.portfolio_uid == portfolio_uid), None)
        if selected is None:
            selected = portfolios[0] if portfolios else None
        if selected is None:
            return PortfolioDashboard(portfolios, None, None, None)
        ledger = self.repository.load(selected.portfolio_uid)
        financial = replay(ledger)
        valued = self.valuation.evaluate_ledger(ledger) if market else None
        risk = (
            self.policy.evaluate(ledger, valued, now=datetime.now(timezone.utc)) if valued else None
        )
        with localcontext(FINANCIAL_CONTEXT):
            realized = sum((p.realized_pnl for p in financial.positions), Decimal(0))
            dividends = sum((p.dividends for p in financial.positions), Decimal(0))
        return PortfolioDashboard(
            portfolios, ledger, financial, reconcile(ledger), valued, risk, realized, dividends
        )
