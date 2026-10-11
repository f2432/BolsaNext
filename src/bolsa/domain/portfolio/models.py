from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.money import LedgerError, Money, currency, decimal_input


def uid() -> str:
    return str(uuid4())


def check_uid(value: str):
    try:
        if str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise LedgerError('UUID canónico inválido.') from exc


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TransactionType(StrEnum):
    BUY = 'BUY'
    SELL = 'SELL'


@dataclass(frozen=True, slots=True)
class Portfolio:
    name: str
    base_currency: str
    portfolio_uid: str = field(default_factory=uid)
    origin_portfolio_uid: str | None = None

    def __post_init__(self):
        if not self.name.strip() or len(self.name) > 120:
            raise LedgerError('Nome de carteira inválido.')
        object.__setattr__(self, 'base_currency', currency(self.base_currency))
        check_uid(self.portfolio_uid)
        if self.origin_portfolio_uid is not None:
            check_uid(self.origin_portfolio_uid)


@dataclass(frozen=True, slots=True)
class Transaction:
    instrument: Instrument
    type: TransactionType
    executed_at: date | datetime
    quantity: Decimal
    price: Money
    commission: Money
    transaction_uid: str = field(default_factory=uid)
    order_key: str = field(default_factory=uid)
    broker_sequence: int | None = None
    settled_on: date | None = None
    notes: str = ''
    source: str | None = None
    account_ref: str | None = None
    external_id: str | None = None
    observed_net: Money | None = None
    related_transaction_uid: str | None = None

    def __post_init__(self):
        check_uid(self.transaction_uid)
        check_uid(self.order_key)
        if self.related_transaction_uid is not None:
            check_uid(self.related_transaction_uid)
        if self.type not in (TransactionType.BUY, TransactionType.SELL):
            raise LedgerError('Tipo financeiro não suportado.')
        if self.instrument.asset_type not in ('stock', 'etf'):
            raise LedgerError('Portfolio aceita apenas ações e ETFs.')
        decimal_input(self.quantity, positive=True)
        decimal_input(self.price.amount, positive=True)
        if not isinstance(self.executed_at, date):
            raise LedgerError('Data de execução inválida.')
        if isinstance(self.executed_at, datetime):
            if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
                raise LedgerError('Instante sem fuso conhecido.')
            object.__setattr__(self, 'executed_at', self.executed_at.astimezone(timezone.utc))
        if self.broker_sequence is not None and (type(self.broker_sequence) is not int or self.broker_sequence < 0):
            raise LedgerError('Sequência da corretora inválida.')
        identity = (self.source, self.account_ref, self.external_id)
        if any(x is not None for x in identity) and not all(isinstance(x, str) and x.strip() for x in identity):
            raise LedgerError('Identidade externa deve conter origem, conta e ID.')

    @property
    def external_identity(self):
        return (self.source, self.account_ref, self.external_id) if self.source else None

    @property
    def execution_key(self):
        # Date-only facts retain their precision. Mixed precision is flagged by replay.
        stamp = self.executed_at.isoformat()
        if not isinstance(self.executed_at, datetime):
            stamp += 'T00:00:00+00:00'
        return (stamp, self.broker_sequence if self.broker_sequence is not None else -1, self.order_key)


@dataclass(frozen=True, slots=True)
class TransactionVersion:
    transaction: Transaction
    version_number: int = 1
    transaction_version_uid: str = field(default_factory=uid)
    previous_version_uid: str | None = None
    voided: bool = False
    reason: str = ''
    recorded_at: datetime = field(default_factory=utc_now)
    author: str = 'local'

    def __post_init__(self):
        check_uid(self.transaction_version_uid)
        if self.previous_version_uid is not None:
            check_uid(self.previous_version_uid)
        if type(self.version_number) is not int or self.version_number < 1:
            raise LedgerError('Número de versão inválido.')
        if (self.version_number == 1) != (self.previous_version_uid is None):
            raise LedgerError('Antecessor incompatível com versão.')
        if (self.version_number > 1 or self.voided) and not self.reason.strip():
            raise LedgerError('Motivo de correção/anulação obrigatório.')
        if self.voided and self.version_number == 1:
            raise LedgerError('Anulação exige versão anterior.')
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise LedgerError('Registo de auditoria exige fuso.')
        object.__setattr__(self, 'recorded_at', self.recorded_at.astimezone(timezone.utc))
        if not self.author.strip():
            raise LedgerError('Autoria local obrigatória.')


@dataclass(frozen=True, slots=True)
class Ledger:
    portfolio: Portfolio
    versions: tuple[TransactionVersion, ...] = ()
    revision: int = 0

    def __post_init__(self):
        object.__setattr__(self, 'versions', tuple(sorted(self.versions, key=lambda v: (v.transaction.transaction_uid, v.version_number))))
