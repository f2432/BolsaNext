from dataclasses import replace

from bolsa.app.ports.portfolio import PortfolioRepository
from bolsa.domain.portfolio.models import Portfolio, Transaction, TransactionVersion
from bolsa.domain.portfolio.money import LedgerError, StaleRevisionError


class PortfolioService:
    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def create(self, name: str, base_currency: str):
        return self.repository.create(Portfolio(name, base_currency))

    def record(self, portfolio_uid: str, transaction: Transaction, *, expected_revision: int):
        return self.repository.append(
            portfolio_uid, (TransactionVersion(transaction),), expected_revision=expected_revision
        )

    def revise(
        self,
        portfolio_uid: str,
        transaction: Transaction,
        *,
        expected_revision: int,
        expected_head: str,
        reason: str,
        void: bool = False,
    ):
        ledger = self.repository.load(portfolio_uid)
        if ledger.revision != expected_revision:
            raise StaleRevisionError("Revisão da carteira desatualizada.")
        chain = [
            v
            for v in ledger.versions
            if v.transaction.transaction_uid == transaction.transaction_uid
        ]
        if not chain:
            raise LedgerError("Operação inexistente.")
        head = max(chain, key=lambda v: v.version_number)
        if head.transaction_version_uid != expected_head or head.voided:
            raise StaleRevisionError("Versão já substituída ou anulada.")
        version = TransactionVersion(
            head.transaction if void else transaction,
            version_number=head.version_number + 1,
            previous_version_uid=expected_head,
            reason=reason,
            voided=void,
        )
        return self.repository.append(
            portfolio_uid, (version,), expected_revision=expected_revision
        )

    def void(self, portfolio_uid: str, transaction_uid: str, **kwargs):
        ledger = self.repository.load(portfolio_uid)
        matches = [v for v in ledger.versions if v.transaction.transaction_uid == transaction_uid]
        if not matches:
            raise LedgerError("Operação inexistente.")
        tx = max(matches, key=lambda v: v.version_number).transaction
        return self.revise(portfolio_uid, replace(tx), void=True, **kwargs)
