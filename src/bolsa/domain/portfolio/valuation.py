from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext

from bolsa.domain.portfolio.ledger import replay, effective_versions
from bolsa.domain.portfolio.money import FINANCIAL_CONTEXT, LedgerError, currency


def market_decimal(value) -> Decimal:
    """Explicit approximate market-data boundary; not a path for execution facts."""
    if isinstance(value, bool):
        raise LedgerError('Cotação inválida.')
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise LedgerError('Cotação inválida.') from exc
    if not result.is_finite() or result <= 0:
        raise LedgerError('Cotação deve ser positiva e finita.')
    return result


@dataclass(frozen=True, slots=True)
class Quote:
    ticker: str
    currency: str
    value: Decimal
    as_of: date | datetime
    source: str
    available: bool = True

    def __post_init__(self):
        object.__setattr__(self, 'currency', currency(self.currency))
        if not isinstance(self.value, Decimal):
            raise LedgerError('Converter preço explicitamente na fronteira de mercado.')
        market_decimal(self.value)
        validate_date(self.as_of)
        if not self.source.strip():
            raise LedgerError('Fonte de cotação obrigatória.')


@dataclass(frozen=True, slots=True)
class FxRate:
    original_currency: str
    base_currency: str
    rate: Decimal
    as_of: date | datetime
    source: str
    available: bool = True

    def __post_init__(self):
        object.__setattr__(self, 'original_currency', currency(self.original_currency))
        object.__setattr__(self, 'base_currency', currency(self.base_currency))
        if not isinstance(self.rate, Decimal):
            raise LedgerError('FX normalizado deve ser Decimal.')
        market_decimal(self.rate)
        validate_date(self.as_of)
        if self.original_currency == self.base_currency and self.rate != 1:
            raise LedgerError('FX de identidade inválido.')
        if not self.source.strip():
            raise LedgerError('Fonte FX obrigatória.')


def validate_date(value):
    if not isinstance(value, date) or isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
        raise LedgerError('Precisão temporal/fuso inválidos.')


def current(as_of, now: datetime, *, max_age: timedelta, last_session: date | None = None):
    validate_date(now)
    if max_age <= timedelta(0):
        raise LedgerError('Antiguidade máxima deve ser positiva.')
    observed_day = as_of.date() if isinstance(as_of, datetime) else as_of
    if observed_day > now.date() or isinstance(as_of, datetime) and as_of > now:
        return False
    if last_session is not None:
        return observed_day >= last_session
    # Date-only closes preserve source precision. Fallback compares calendar-day age,
    # not a fabricated execution timestamp. The display must retain that precision.
    age = now - as_of if isinstance(as_of, datetime) else timedelta(days=(now.date() - as_of).days)
    return age <= max_age


@dataclass(frozen=True, slots=True)
class ValuedPosition:
    ticker: str
    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    reason: str = ''
    quote: Quote | None = None
    fx: FxRate | None = None


@dataclass(frozen=True, slots=True)
class Valuation:
    positions: tuple[ValuedPosition, ...]
    known_subtotal: Decimal
    total: Decimal | None
    unrealized_pnl: Decimal | None
    reconciliation_pending: bool


def value_portfolio(ledger, quotes: dict[str, Quote], rates: dict[str, FxRate], *,
                    now: datetime | None = None, max_age: timedelta = timedelta(hours=72),
                    last_sessions: dict[str, date] | None = None) -> Valuation:
    now = now or datetime.now(timezone.utc)
    sessions = last_sessions or {}
    result = replay(ledger)
    instruments = {v.transaction.instrument.ticker: v.transaction.instrument for v in effective_versions(ledger)}
    values = []
    subtotal = Decimal(0)
    pnl = Decimal(0)
    complete = True
    with localcontext(FINANCIAL_CONTEXT):
        for pos in result.positions:
            if not pos.quantity:
                continue
            quote = quotes.get(pos.ticker)
            rate = None
            reason = ''
            instrument = instruments[pos.ticker]
            if quote is None or not quote.available:
                reason = 'Cotação indisponível'
            elif instrument.currency is None or quote.ticker != pos.ticker or quote.currency != instrument.currency:
                reason = 'Moeda/metadados da cotação incompatíveis ou desconhecidos'
            elif not current(quote.as_of, now, max_age=max_age, last_session=sessions.get(pos.ticker)):
                reason = 'Cotação desatualizada'
            elif quote.currency != ledger.portfolio.base_currency:
                rate = rates.get(quote.currency)
                if (rate is None or not rate.available or rate.original_currency != quote.currency
                    or rate.base_currency != ledger.portfolio.base_currency):
                    reason = 'FX indisponível ou incompatível'
                elif not current(rate.as_of, now, max_age=max_age, last_session=sessions.get('FX')):
                    reason = 'FX desatualizado'
            if reason:
                complete = False
                values.append(ValuedPosition(pos.ticker, None, None, reason, quote, rate))
            else:
                value = pos.quantity * quote.value * (rate.rate if rate else Decimal(1))
                unrealized = value - pos.cost
                subtotal += value
                pnl += unrealized
                values.append(ValuedPosition(pos.ticker, value, unrealized, quote=quote, fx=rate))
    return Valuation(tuple(values), subtotal, subtotal if complete else None, pnl if complete else None,
                     bool(result.pending_reconciliation))
