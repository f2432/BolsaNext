from dataclasses import dataclass
from decimal import localcontext

from bolsa.domain.portfolio.ledger import replay, effective_versions
from bolsa.domain.portfolio.money import LedgerError, FINANCIAL_CONTEXT


@dataclass(frozen=True, slots=True)
class Discrepancy:
    transaction_uid: str | None
    kind: str
    reason: str


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    state: str
    discrepancies: tuple[Discrepancy, ...]


def reconcile(ledger):
    try:
        result = replay(ledger)
    except LedgerError as exc:
        return ReconciliationReport('invalid',(Discrepancy(None,'integrity',str(exc)),))
    discrepancies = [Discrepancy(None,'temporal_ambiguity',w) for w in result.warnings]
    with localcontext(FINANCIAL_CONTEXT):
        for version in effective_versions(ledger):
            tx = version.transaction
            if tx.transaction_uid in result.pending_reconciliation:
                discrepancies.append(Discrepancy(tx.transaction_uid,'observed_difference',
                    'Montante observado difere do reconstruído; origem preservada, sem classificação automática.'))
    return ReconciliationReport('pending' if discrepancies else 'consistent',tuple(discrepancies))
