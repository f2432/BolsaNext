from typing import Protocol

from bolsa.domain.portfolio.models import Ledger, Portfolio, TransactionVersion


class PortfolioRepository(Protocol):
    def create(self, portfolio: Portfolio) -> Ledger: ...
    def list_portfolios(self) -> tuple[Portfolio, ...]: ...
    def load(self, portfolio_uid: str) -> Ledger: ...
    def append(
        self,
        portfolio_uid: str,
        versions: tuple[TransactionVersion, ...],
        *,
        expected_revision: int,
    ) -> Ledger: ...

    def import_ledger(self, incoming: Ledger, *, expected_revision: int | None): ...
