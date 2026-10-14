from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from enum import StrEnum
from uuid import UUID, uuid4

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.values import (
    FINANCIAL_CONTEXT, LedgerConflictError, MoneyComponent, PortfolioError,
    currency_code, financial_decimal,
)


def _uuid(value):
    if not isinstance(value, UUID):
        raise PortfolioError("Ledger identities must be UUID")


def _instant(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PortfolioError("Audit instants must be timezone aware")
    return value.astimezone(timezone.utc)


class TradeType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Trade:
    instrument: Instrument
    kind: TradeType
    quantity: Decimal
    unit_price: MoneyComponent
    commission: MoneyComponent
    executed_at: date | datetime
    broker_sequence: int | None = None
    settlement_date: date | None = None
    notes: str = ""
    # Preserve source facts, independently of calculated cost/proceeds.
    source: str = "manual"
    account_ref: str | None = None
    external_id: str | None = None
    original_facts: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.instrument, Instrument) or not isinstance(self.instrument.asset_type, AssetType) or self.instrument.asset_type not in (
            AssetType.STOCK, AssetType.ETF
        ):
            raise PortfolioError("Only stocks and ETFs are supported")
        if not isinstance(self.kind, TradeType):
            raise PortfolioError("Unsupported trade type")
        object.__setattr__(self, "quantity", financial_decimal(self.quantity, positive=True))
        if not isinstance(self.unit_price, MoneyComponent) or self.unit_price.amount <= 0:
            raise PortfolioError("Execution price must be positive")
        if not isinstance(self.commission, MoneyComponent):
            raise PortfolioError("Commission must be a monetary component")
        if isinstance(self.executed_at, datetime):
            _instant(self.executed_at)  # Keep original timezone, canonicalize only the order key.
        elif not isinstance(self.executed_at, date):
            raise PortfolioError("Execution must have a date or aware instant")
        if self.broker_sequence is not None and (
            type(self.broker_sequence) is not int or self.broker_sequence < 0
        ):
            raise PortfolioError("Invalid broker sequence")
        if self.settlement_date is not None and type(self.settlement_date) is not date:
            raise PortfolioError("Settlement must be a date")
        if not self.source.strip() or bool(self.account_ref) != bool(self.external_id):
            raise PortfolioError("Incomplete source identity")
        if not isinstance(self.original_facts, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 or
            any(not isinstance(v, str) for v in pair) for pair in self.original_facts
        ):
            raise PortfolioError("Original facts must be immutable text pairs")

    @property
    def execution_key(self):
        if isinstance(self.executed_at, datetime):
            return _instant(self.executed_at)
        # A sorting bucket only, never presented as a known execution instant.
        return datetime.combine(self.executed_at, datetime.min.time(), timezone.utc)


@dataclass(frozen=True, slots=True)
class TransactionVersion:
    portfolio_uid: UUID
    transaction_uid: UUID
    trade: Trade | Dividend | Split | None
    version_number: int = 1
    previous_version_uid: UUID | None = None
    transaction_version_uid: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    author: str = "local"

    def __post_init__(self):
        for uid in (self.portfolio_uid, self.transaction_uid, self.transaction_version_uid):
            _uuid(uid)
        if self.previous_version_uid is not None:
            _uuid(self.previous_version_uid)
        if type(self.version_number) is not int or self.version_number < 1:
            raise PortfolioError("Invalid version number")
        if (self.version_number == 1) != (self.previous_version_uid is None):
            raise PortfolioError("Invalid predecessor")
        if self.version_number > 1 and not self.reason.strip():
            raise PortfolioError("Correction/cancellation requires a reason")
        if self.trade is None and self.version_number == 1:
            raise PortfolioError("Cannot cancel a nonexistent operation")
        if self.trade is not None and not isinstance(self.trade, (Trade, Dividend, Split)):
            raise PortfolioError("Invalid trade payload")
        object.__setattr__(self, "recorded_at", _instant(self.recorded_at))
        if not self.author.strip():
            raise PortfolioError("Audit author is required")


@dataclass(frozen=True, slots=True)
class Position:
    ticker: str
    quantity: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    average_cost: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    dividend_income: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class ReplayResult:
    positions: tuple[Position, ...]
    warnings: tuple[str, ...]

    def position(self, ticker: str) -> Position:
        return next((p for p in self.positions if p.ticker == ticker), Position(ticker))


def effective_versions(portfolio_uid, versions):
    chains = defaultdict(list)
    seen = set()
    external_owners = {}
    for version in versions:
        if not isinstance(version, TransactionVersion) or version.portfolio_uid != portfolio_uid:
            raise PortfolioError("Version belongs to another portfolio")
        if version.transaction_version_uid in seen:
            raise PortfolioError("Duplicate version UUID")
        seen.add(version.transaction_version_uid)
        if version.trade is not None and version.trade.external_id:
            trade = version.trade
            key = (trade.source, trade.account_ref, trade.external_id)
            owner = external_owners.setdefault(key, version.transaction_uid)
            if owner != version.transaction_uid:
                raise PortfolioError("Duplicate external identity in audit history")
        chains[version.transaction_uid].append(version)
    effective = []
    for chain in chains.values():
        chain.sort(key=lambda v: v.version_number)
        previous = None
        for number, version in enumerate(chain, 1):
            if version.version_number != number or version.previous_version_uid != (
                previous.transaction_version_uid if previous else None
            ):
                raise PortfolioError("Broken or branched version chain")
            if previous is not None and (
                previous.trade is None or version.recorded_at < previous.recorded_at
            ):
                raise PortfolioError("Cancelled operation is terminal; audit order must be monotonic")
            previous = version
        if chain[-1].trade is not None:
            effective.append(chain[-1])
    return effective


def replay(portfolio_uid: UUID, base_currency: str, versions) -> ReplayResult:
    base = currency_code(base_currency)
    events = effective_versions(portfolio_uid, versions)
    events.sort(key=lambda v: (
        v.trade.execution_key,
        v.trade.broker_sequence if v.trade.broker_sequence is not None else -1,
        v.transaction_uid.hex,
    ))
    groups = defaultdict(list)
    external = set()
    for event in events:
        trade = event.trade
        groups[(trade.instrument.ticker, trade.execution_key.date())].append(event)
        if trade.external_id:
            key = (trade.source, trade.account_ref, trade.external_id)
            if key in external:
                raise PortfolioError("Duplicate external identity")
            external.add(key)
    warnings = []
    for group in groups.values():
        date_only = any(type(e.trade.executed_at) is date for e in group)
        instants = [e.trade.execution_key for e in group]
        sequences = [e.trade.broker_sequence for e in group]
        if date_only or (len(set(instants)) != len(instants) and (
            None in sequences or len(set(sequences)) != len(sequences)
        )):
            warnings.append(f"Ambiguous execution order: {group[0].trade.instrument.ticker} "
                            f"{instants[0].date()}")
    positions = {}
    with localcontext(FINANCIAL_CONTEXT):
        for event in events:
            trade = event.trade
            ticker = trade.instrument.ticker
            current = positions.get(ticker, Position(ticker))
            if isinstance(trade, Dividend):
                gross = trade.gross.in_base(base)
                withholding = trade.withholding.in_base(base)
                charges = trade.charges.in_base(base)
                net = trade.net.in_base(base)
                if net != gross - withholding - charges:
                    raise PortfolioError(f"Inconsistent manual dividend net: {event.transaction_uid}")
                positions[ticker] = replace(current, dividend_income=current.dividend_income + net)
                continue
            if isinstance(trade, Split):
                if current.quantity == 0:
                    raise PortfolioError(f"Split requires an open position: {event.transaction_uid}")
                q = current.quantity * trade.factor
                positions[ticker] = replace(current, quantity=q, average_cost=current.cost / q)
                continue
            quantity = trade.quantity
            gross = quantity * trade.unit_price.amount * trade.unit_price.rate_to_base(base)
            fee = trade.commission.in_base(base)
            if trade.kind is TradeType.BUY:
                q = current.quantity + quantity
                cost = current.cost + gross + fee
                positions[ticker] = Position(ticker, q, cost, cost / q, current.realized_pnl,
                                              current.dividend_income)
            else:
                if quantity > current.quantity:
                    raise PortfolioError(f"Oversell: {event.transaction_uid} ({ticker})")
                q = current.quantity - quantity
                assigned = current.cost if q == 0 else quantity * current.average_cost
                cost = Decimal("0") if q == 0 else current.cost - assigned
                positions[ticker] = Position(
                    ticker, q, cost, current.average_cost if q else Decimal("0"),
                    current.realized_pnl + gross - fee - assigned,
                    current.dividend_income,
                )
    return ReplayResult(tuple(positions[k] for k in sorted(positions)), tuple(warnings))


@dataclass(frozen=True, slots=True)
class Portfolio:
    name: str
    base_currency: str
    portfolio_uid: UUID = field(default_factory=uuid4)
    versions: tuple[TransactionVersion, ...] = ()

    def __post_init__(self):
        _uuid(self.portfolio_uid)
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 120:
            raise PortfolioError("Invalid portfolio name")
        object.__setattr__(self, "base_currency", currency_code(self.base_currency))
        if not isinstance(self.versions, tuple):
            raise PortfolioError("Ledger must be immutable")
        self.reconstruct()

    @property
    def ledger_revision(self):
        return len(self.versions)

    def reconstruct(self):
        return replay(self.portfolio_uid, self.base_currency, self.versions)

    def record(self, trade: Trade | Dividend | Split, *, transaction_uid: UUID | None = None):
        uid = transaction_uid or uuid4()
        if any(v.transaction_uid == uid for v in self.versions):
            raise LedgerConflictError("Economic identity already exists")
        version = TransactionVersion(self.portfolio_uid, uid, trade)
        return replace(self, versions=self.versions + (version,))

    def revise(self, transaction_uid: UUID, expected_head: UUID, trade: Trade | Dividend | Split | None,
               *, reason: str):
        chain = [v for v in self.versions if v.transaction_uid == transaction_uid]
        if not chain:
            raise LedgerConflictError("Unknown economic identity")
        head = max(chain, key=lambda v: v.version_number)
        if head.transaction_version_uid != expected_head or head.trade is None:
            raise LedgerConflictError("Obsolete or cancelled head")
        version = TransactionVersion(
            self.portfolio_uid, transaction_uid, trade, head.version_number + 1,
            head.transaction_version_uid, reason=reason,
        )
        return replace(self, versions=self.versions + (version,))
