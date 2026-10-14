from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Mapping
from uuid import UUID

from bolsa.domain.portfolio.ledger import Portfolio
from bolsa.domain.portfolio.values import FINANCIAL_CONTEXT, PortfolioError, currency_code


def quote_decimal(value: Decimal) -> Decimal:
    """Current approximate quotes are not exact historical execution inputs."""
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise PortfolioError("Quote must be a positive finite Decimal")
    if value >= Decimal("1e18"):
        raise PortfolioError("Quote exceeds supported magnitude")
    return value


def _quote_time(value):
    if value is None or type(value) is date:
        return
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PortfolioError("Quote timestamp must be an aware instant, date, or unknown")


@dataclass(frozen=True, slots=True)
class PriceQuote:
    ticker: str
    currency: str
    price: Decimal
    quoted_at: date | datetime | None
    source: str

    def __post_init__(self):
        object.__setattr__(self, "currency", currency_code(self.currency))
        quote_decimal(self.price)
        _quote_time(self.quoted_at)
        if not self.ticker or not self.source.strip():
            raise PortfolioError("Quote identity/source required")


@dataclass(frozen=True, slots=True)
class FxQuote:
    source_currency: str
    base_currency: str
    rate: Decimal
    quoted_at: date | datetime | None
    source: str
    inverted: bool = False
    source_pair: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "source_currency", currency_code(self.source_currency))
        object.__setattr__(self, "base_currency", currency_code(self.base_currency))
        quote_decimal(self.rate)
        _quote_time(self.quoted_at)
        if self.source_currency == self.base_currency and self.rate != Decimal("1"):
            raise PortfolioError("Identity FX must equal one")
        if not self.source.strip():
            raise PortfolioError("FX source required")


class ValuationState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    STALE = "stale"
    UNRELIABLE_TIME = "unreliable_time"


@dataclass(frozen=True, slots=True)
class ValuedPosition:
    ticker: str
    state: ValuationState
    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    reason: str | None
    price_quote: PriceQuote | None
    fx_quote: FxQuote | None


@dataclass(frozen=True, slots=True)
class ValuationResult:
    base_currency: str
    positions: tuple[ValuedPosition, ...]
    known_market_subtotal: Decimal
    known_unrealized_subtotal: Decimal
    total_market_value: Decimal | None
    total_unrealized_pnl: Decimal | None
    realized_pnl: Decimal
    evaluated_at: datetime
    # P2 has no reliable exchange-session calendar; do not claim live/session freshness.
    freshness_policy: str = "elapsed_time_fallback"
    freshness_limit: timedelta = timedelta(hours=72)
    data_errors: tuple[str, ...] = ()
    portfolio_uid: UUID | None = None
    ledger_revision: int | None = None
    accounting_confirmed: bool = True

    @property
    def complete(self):
        return self.total_market_value is not None


def quote_freshness(quoted_at, now, max_age):
    if quoted_at is None:
        return ValuationState.UNRELIABLE_TIME, "Missing quote timestamp"
    if isinstance(quoted_at, datetime):
        instant = quoted_at.astimezone(timezone.utc)
    else:
        # Conservative age upper bound, not a fabricated quote timestamp.
        instant = datetime.combine(quoted_at, time.min, timezone.utc)
    age = now - instant
    if age < timedelta(0):
        return ValuationState.UNRELIABLE_TIME, "Quote timestamp is in the future"
    if age > max_age:
        return ValuationState.STALE, "Quote exceeds elapsed-time freshness limit"
    return ValuationState.AVAILABLE, None


def value_portfolio(portfolio: Portfolio, prices: Mapping[str, PriceQuote],
                    fx_rates: Mapping[tuple[str, str], FxQuote], *, now: datetime,
                    max_age: timedelta = timedelta(hours=72)) -> ValuationResult:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise PortfolioError("Valuation time must be timezone aware")
    if not isinstance(max_age, timedelta) or max_age <= timedelta(0):
        raise PortfolioError("Freshness limit must be positive")
    now = now.astimezone(timezone.utc)
    ledger = portfolio.reconstruct()
    rows = []
    subtotal = Decimal("0")
    pnl_subtotal = Decimal("0")
    realized = Decimal("0")
    pnl_complete = True
    with localcontext(FINANCIAL_CONTEXT):
        for position in ledger.positions:
            realized += position.realized_pnl
            if position.quantity == 0:
                continue
            price = prices.get(position.ticker)
            rate = None
            state, reason = ValuationState.MISSING, "Missing current price"
            if price is not None:
                if price.ticker != position.ticker:
                    raise PortfolioError("Price snapshot belongs to another instrument")
                state, reason = quote_freshness(price.quoted_at, now, max_age)
                if price.currency == portfolio.base_currency:
                    rate = FxQuote(price.currency, portfolio.base_currency, Decimal("1"), None, "identity")
                else:
                    rate = fx_rates.get((price.currency, portfolio.base_currency))
                    if rate is not None and (rate.source_currency, rate.base_currency) != (
                        price.currency, portfolio.base_currency
                    ):
                        raise PortfolioError("FX orientation does not match valuation")
                    if state is ValuationState.AVAILABLE:
                        if rate is None:
                            state, reason = ValuationState.MISSING, "Missing current FX"
                        else:
                            state, reason = quote_freshness(rate.quoted_at, now, max_age)
            value = pnl = None
            if state is ValuationState.AVAILABLE:
                value = position.quantity * price.price * rate.rate
                pnl = value - position.cost if position.accounting_confirmed else None
                subtotal += value
                if pnl is not None:
                    pnl_subtotal += pnl
                else:
                    pnl_complete = False
                    reason = "Historical accounting is pending settlement reconciliation"
            rows.append(ValuedPosition(position.ticker, state, value, pnl, reason, price, rate))
    complete = all(row.state is ValuationState.AVAILABLE for row in rows)
    return ValuationResult(
        portfolio.base_currency, tuple(rows), subtotal, pnl_subtotal,
        subtotal if complete else None, pnl_subtotal if complete and pnl_complete else None, realized, now,
        freshness_limit=max_age,
        portfolio_uid=portfolio.portfolio_uid, ledger_revision=portfolio.ledger_revision,
        accounting_confirmed=not ledger.pending_reconciliation,
    )
