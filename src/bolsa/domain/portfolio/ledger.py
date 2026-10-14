from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from enum import StrEnum
from uuid import UUID, uuid4

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.policy import PolicyParameters, PolicyVersion, validate_policy_history
from bolsa.domain.portfolio.values import (
    FINANCIAL_CONTEXT, LedgerConflictError, MoneyComponent, PortfolioError,
    currency_code, financial_decimal,
    ReportedSettlement,
    exact_product, exact_sum,
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
    reported_settlement: ReportedSettlement | None = None

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
        if self.reported_settlement is not None and not isinstance(self.reported_settlement, ReportedSettlement):
            raise PortfolioError("Invalid observed trade settlement")

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
    accounting_confirmed: bool = True


@dataclass(frozen=True, slots=True)
class SettlementDifference:
    transaction_uid: UUID
    ticker: str
    expected_cashflow_base: Decimal
    reported_cashflow_base: Decimal
    difference_base: Decimal


@dataclass(frozen=True, slots=True)
class ReplayResult:
    positions: tuple[Position, ...]
    warnings: tuple[str, ...]
    pending_reconciliation: tuple[SettlementDifference, ...] = ()

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
            if previous is not None and previous.trade is not None and version.trade is not None:
                observed = getattr(previous.trade, "reported_settlement", None)
                if observed is not None and getattr(version.trade, "reported_settlement", None) != observed:
                    raise PortfolioError("Confirmed observed settlement cannot be erased or changed by correction")
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
    purchase_costs = defaultdict(lambda: Decimal("0"))
    sale_proceeds = defaultdict(lambda: Decimal("0"))
    pending = []
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
                if net != exact_sum(gross, withholding.copy_negate(), charges.copy_negate()):
                    raise PortfolioError(f"Inconsistent manual dividend net: {event.transaction_uid}")
                if trade.reported_settlement is not None:
                    observed = trade.reported_settlement.in_base(base)
                    if observed != net:
                        pending.append(SettlementDifference(event.transaction_uid, ticker, net, observed, exact_sum(observed, net.copy_negate())))
                        current = replace(current, accounting_confirmed=False)
                positions[ticker] = replace(current, dividend_income=exact_sum(current.dividend_income, net))
                continue
            if isinstance(trade, Split):
                if current.quantity == 0:
                    raise PortfolioError(f"Split requires an open position: {event.transaction_uid}")
                q = exact_product(current.quantity, trade.factor)
                positions[ticker] = replace(current, quantity=q, average_cost=current.cost / q)
                continue
            quantity = trade.quantity
            gross = exact_product(quantity, trade.unit_price.amount, trade.unit_price.rate_to_base(base))
            fee = trade.commission.in_base(base)
            if trade.reported_settlement is not None:
                expected = exact_sum(gross, fee).copy_negate() if trade.kind is TradeType.BUY else exact_sum(gross, fee.copy_negate())
                observed = trade.reported_settlement.in_base(base)
                if observed != expected:
                    pending.append(SettlementDifference(event.transaction_uid, ticker, expected, observed, exact_sum(observed, expected.copy_negate())))
                    current = replace(current, accounting_confirmed=False)
            if trade.kind is TradeType.BUY:
                purchase_costs[ticker] = exact_sum(purchase_costs[ticker], gross, fee)
                q = exact_sum(current.quantity, quantity)
                cost = exact_sum(current.cost, gross, fee)
                positions[ticker] = Position(ticker, q, cost, cost / q, current.realized_pnl,
                                              current.dividend_income, current.accounting_confirmed)
            else:
                if quantity > current.quantity:
                    raise PortfolioError(f"Oversell: {event.transaction_uid} ({ticker})")
                q = exact_sum(current.quantity, quantity.copy_negate())
                assigned = current.cost if q == 0 else exact_product(quantity, current.average_cost)
                cost = Decimal("0") if q == 0 else exact_sum(current.cost, assigned.copy_negate())
                sale_proceeds[ticker] = exact_sum(sale_proceeds[ticker], gross, fee.copy_negate())
                # Cashflow conservation cancels repeating-average residues on
                # closure, including reopened positions. Never round to cents.
                realized = exact_sum(sale_proceeds[ticker], purchase_costs[ticker].copy_negate(), cost)
                positions[ticker] = Position(
                    ticker, q, cost, current.average_cost if q else Decimal("0"),
                    realized,
                    current.dividend_income,
                    current.accounting_confirmed,
                )
    return ReplayResult(tuple(positions[k] for k in sorted(positions)), tuple(warnings), tuple(pending))


@dataclass(frozen=True, slots=True)
class Portfolio:
    name: str
    base_currency: str
    portfolio_uid: UUID = field(default_factory=uuid4)
    versions: tuple[TransactionVersion, ...] = ()
    origin_portfolio_uid: UUID | None = None
    policies: tuple[PolicyVersion, ...] = ()

    def __post_init__(self):
        _uuid(self.portfolio_uid)
        if self.origin_portfolio_uid is not None:
            _uuid(self.origin_portfolio_uid)
            if self.origin_portfolio_uid == self.portfolio_uid:
                raise PortfolioError("Portfolio cannot clone itself")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 120:
            raise PortfolioError("Invalid portfolio name")
        object.__setattr__(self, "base_currency", currency_code(self.base_currency))
        if not isinstance(self.versions, tuple):
            raise PortfolioError("Ledger must be immutable")
        self.reconstruct()
        validate_policy_history(self.portfolio_uid, self.policies)

    @property
    def ledger_revision(self):
        return len(self.versions)

    @property
    def policy_revision(self):
        return len(self.policies)

    def add_policy(self, parameters: PolicyParameters, *, effective_at: datetime, reason: str,
                   expected_head: UUID | None, recorded_at: datetime | None = None):
        head = max(self.policies, key=lambda p: p.version_number) if self.policies else None
        if expected_head != (head.policy_version_uid if head else None):
            raise LedgerConflictError("Obsolete policy head")
        policy = PolicyVersion(self.portfolio_uid, parameters, self.policy_revision + 1,
                               expected_head, effective_at, reason,
                               recorded_at=recorded_at or datetime.now(timezone.utc))
        return replace(self, policies=self.policies + (policy,))

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
