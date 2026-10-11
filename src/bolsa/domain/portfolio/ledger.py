from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from bolsa.domain.portfolio.models import Ledger, TransactionType, TransactionVersion
from bolsa.domain.portfolio.money import FINANCIAL_CONTEXT, LedgerError, StaleRevisionError

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Position:
    ticker: str
    quantity: Decimal = ZERO
    cost: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    dividends: Decimal = ZERO

    @property
    def average_cost(self):
        with localcontext(FINANCIAL_CONTEXT):
            return self.cost / self.quantity if self.quantity else ZERO


@dataclass(frozen=True, slots=True)
class ReplayResult:
    positions: tuple[Position, ...]
    warnings: tuple[str, ...] = ()
    pending_reconciliation: tuple[str, ...] = ()


def effective_versions(ledger: Ledger) -> tuple[TransactionVersion, ...]:
    chains = {}
    version_ids = set()
    external_ids = {}
    for version in sorted(ledger.versions, key=lambda v: (v.transaction.transaction_uid, v.version_number)):
        tx = version.transaction
        if version.transaction_version_uid in version_ids:
            raise LedgerError('Identidade de versão duplicada.')
        version_ids.add(version.transaction_version_uid)
        previous = chains.get(tx.transaction_uid)
        if previous is None:
            if version.version_number != 1:
                raise LedgerError('Cadeia sem primeira versão.')
        elif (previous.voided or version.version_number != previous.version_number + 1
              or version.previous_version_uid != previous.transaction_version_uid):
            raise LedgerError('Cadeia ramificada, interrompida ou anulada.')
        if previous is not None:
            old = previous.transaction
            if (tx.order_key, tx.external_identity) != (old.order_key, old.external_identity):
                raise LedgerError('Ordem/identidade de origem imutáveis na correção.')
            if version.voided and tx != old:
                raise LedgerError('Anulação não pode alterar os factos financeiros.')
        if tx.external_identity is not None:
            owner = external_ids.setdefault(tx.external_identity, tx.transaction_uid)
            if owner != tx.transaction_uid:
                raise LedgerError('Colisão de identidade externa.')
        chains[tx.transaction_uid] = version
    active = [v for v in chains.values() if not v.voided]
    keys = [v.transaction.order_key for v in chains.values()]
    if len(set(keys)) != len(keys):
        raise LedgerError('Chave de ordem duplicada.')
    return tuple(sorted(active, key=lambda v: v.transaction.execution_key))


def replay(ledger: Ledger) -> ReplayResult:
    positions = {}
    warnings = []
    pending = []
    seen_dates = {}
    with localcontext(FINANCIAL_CONTEXT):
        for version in effective_versions(ledger):
            tx = version.transaction
            key = (tx.instrument.ticker, tx.executed_at.isoformat()[:10])
            same_day = seen_dates.setdefault(key, [])
            if any(t.executed_at == tx.executed_at and (t.broker_sequence is None or tx.broker_sequence is None)
                   or type(t.executed_at) is not type(tx.executed_at) for t in same_day):
                warnings.append(f'Ordem temporal ambígua: {tx.transaction_uid}')
            same_day.append(tx)
            pos = positions.get(tx.instrument.ticker, Position(tx.instrument.ticker))
            # Convert every monetary component separately, before arithmetic in base currency.
            gross = tx.quantity * tx.price.in_base(ledger.portfolio.base_currency)
            fee = tx.commission.in_base(ledger.portfolio.base_currency)
            derived_net = gross + fee if tx.type == TransactionType.BUY else gross - fee
            if tx.observed_net is not None and tx.observed_net.in_base(ledger.portfolio.base_currency) != derived_net:
                pending.append(tx.transaction_uid)
            if tx.type == TransactionType.BUY:
                pos = replace(pos, quantity=pos.quantity + tx.quantity, cost=pos.cost + derived_net)
            else:
                if tx.quantity > pos.quantity:
                    raise LedgerError(f'Venda excede quantidade disponível: {tx.transaction_uid}')
                allocated = pos.cost if tx.quantity == pos.quantity else tx.quantity * pos.cost / pos.quantity
                remaining = pos.quantity - tx.quantity
                pos = replace(pos, quantity=remaining, cost=pos.cost - allocated if remaining else ZERO,
                              realized_pnl=pos.realized_pnl + derived_net - allocated)
            positions[pos.ticker] = pos
    return ReplayResult(tuple(positions[k] for k in sorted(positions)), tuple(warnings), tuple(pending))


def append_version(ledger: Ledger, version: TransactionVersion, *, expected_head: str | None = None) -> Ledger:
    matches = [v for v in ledger.versions if v.transaction.transaction_uid == version.transaction.transaction_uid]
    head = max(matches, key=lambda v: v.version_number) if matches else None
    if (head.transaction_version_uid if head else None) != expected_head:
        raise StaleRevisionError('A operação foi entretanto alterada.')
    candidate = replace(ledger, versions=ledger.versions + (version,), revision=ledger.revision + 1)
    replay(candidate)
    return candidate
