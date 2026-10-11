from dataclasses import dataclass, replace

from bolsa.domain.portfolio.ledger import effective_versions, replay
from bolsa.domain.portfolio.models import Ledger
from bolsa.domain.portfolio.money import LedgerError


@dataclass(frozen=True, slots=True)
class ImportReport:
    inserted: int = 0
    ignored: int = 0
    conflicts: tuple[str, ...] = ()
    rejected: tuple[str, ...] = ()
    status: str = "preview"


class ImportRejected(LedgerError):
    def __init__(self, report: ImportReport):
        self.report = replace(report, inserted=0, status="rejected_rollback")
        super().__init__("; ".join(report.conflicts + report.rejected) or "Importação rejeitada.")


def merge_ledger(existing: Ledger, incoming: Ledger):
    if (
        existing.portfolio.portfolio_uid != incoming.portfolio.portfolio_uid
        or existing.portfolio.base_currency != incoming.portfolio.base_currency
    ):
        raise ImportRejected(
            ImportReport(conflicts=("Identidade/moeda da carteira incompatível.",))
        )
    versions = list(existing.versions)
    by_id = {v.transaction_version_uid: v for v in versions}
    by_number = {(v.transaction.transaction_uid, v.version_number): v for v in versions}
    external = {
        v.transaction.external_identity: v
        for v in effective_versions(existing)
        if v.transaction.external_identity
    }
    inserted = ignored = 0
    conflicts = []
    for version in incoming.versions:
        tx = version.transaction
        stored = by_id.get(version.transaction_version_uid) or by_number.get(
            (tx.transaction_uid, version.version_number)
        )
        if stored is not None:
            if stored == version:
                ignored += 1
            else:
                conflicts.append(
                    f"Identidade com conteúdo divergente: {tx.transaction_uid}/{version.version_number}"
                )
            continue
        counterpart = external.get(tx.external_identity) if tx.external_identity else None
        if (
            counterpart is not None
            and counterpart.transaction.transaction_uid != tx.transaction_uid
        ):
            # Proof by external identity is sufficient for an equivalent initial execution.
            # Divergent/versioned audit chains require explicit resolution, never overwrite.
            a = replace(
                tx,
                transaction_uid=counterpart.transaction.transaction_uid,
                order_key=counterpart.transaction.order_key,
            )
            if (
                version.version_number == counterpart.version_number == 1
                and not version.voided
                and a == counterpart.transaction
            ):
                ignored += 1
            else:
                conflicts.append(f"Identidade externa contraditória: {tx.external_identity}")
            continue
        versions.append(version)
        by_id[version.transaction_version_uid] = version
        by_number[(tx.transaction_uid, version.version_number)] = version
        if tx.external_identity and version.version_number == 1:
            external[tx.external_identity] = version
        inserted += 1
    if conflicts:
        raise ImportRejected(ImportReport(ignored=ignored, conflicts=tuple(conflicts)))
    from bolsa.domain.portfolio.policy import validate_policies

    policies = list(existing.policies)
    policy_numbers = {p.version_number: p for p in policies}
    for policy in incoming.policies:
        previous = policy_numbers.get(policy.version_number)
        if previous is not None:
            if previous != policy:
                raise ImportRejected(ImportReport(conflicts=("Conflito de versão de política.",)))
            ignored += 1
        else:
            policies.append(policy)
            inserted += 1
    try:
        validate_policies(policies)
    except LedgerError as exc:
        raise ImportRejected(ImportReport(rejected=(str(exc),))) from exc
    candidate = replace(
        existing,
        versions=tuple(versions),
        policies=tuple(policies),
        revision=existing.revision + inserted,
    )
    try:
        replay(candidate)
    except LedgerError as exc:
        raise ImportRejected(ImportReport(ignored=ignored, rejected=(str(exc),))) from exc
    return candidate, ImportReport(inserted, ignored)
