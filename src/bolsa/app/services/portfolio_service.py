from uuid import UUID
from datetime import datetime

from bolsa.app.ports.portfolio import PortfolioRepository
from bolsa.domain.portfolio.ledger import Portfolio, Trade
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.policy import PolicyParameters
from bolsa.domain.portfolio.values import LedgerConflictError


class PortfolioService:
    def __init__(self, repository: PortfolioRepository):
        self._repository = repository

    def create(self, name: str, base_currency: str) -> Portfolio:
        portfolio = Portfolio(name, base_currency)
        self._repository.create(portfolio)
        return portfolio

    def load(self, portfolio_uid: UUID) -> Portfolio:
        return self._repository.load(portfolio_uid)

    def change_policy(self, portfolio_uid: UUID, parameters: PolicyParameters, *,
                      expected_head: UUID | None, effective_at: datetime, reason: str) -> Portfolio:
        current = self.load(portfolio_uid)
        candidate = current.add_policy(parameters, expected_head=expected_head,
                                       effective_at=effective_at, reason=reason)
        self._repository.save(candidate, expected_revision=current.ledger_revision,
                              expected_policy_revision=current.policy_revision)
        return candidate

    def _expected(self, portfolio_uid, expected_revision):
        portfolio = self.load(portfolio_uid)
        if portfolio.ledger_revision != expected_revision:
            raise LedgerConflictError("Obsolete portfolio revision")
        return portfolio

    def record(self, portfolio_uid: UUID, trade: Trade | Dividend | Split, *, expected_revision: int) -> Portfolio:
        portfolio = self._expected(portfolio_uid, expected_revision).record(trade)
        self._repository.save(portfolio, expected_revision=expected_revision)
        return portfolio

    def revise(self, portfolio_uid: UUID, transaction_uid: UUID, expected_head: UUID,
               trade: Trade | Dividend | Split | None, *, reason: str, expected_revision: int) -> Portfolio:
        portfolio = self._expected(portfolio_uid, expected_revision).revise(
            transaction_uid, expected_head, trade, reason=reason,
        )
        self._repository.save(portfolio, expected_revision=expected_revision)
        return portfolio
