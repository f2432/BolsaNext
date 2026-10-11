from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

FINANCIAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
# Explicit supported ISO 4217 subset. Extend deliberately, not by accepting any three letters.
SUPPORTED_CURRENCIES = frozenset('EUR USD GBP CHF CAD AUD NZD JPY CNY HKD SGD SEK NOK DKK PLN CZK HUF BRL INR ZAR MXN KRW TRY ILS'.split())


class LedgerError(ValueError):
    """Identifiable financial validation failure."""


class StaleRevisionError(LedgerError):
    pass


def currency(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in SUPPORTED_CURRENCIES:
        raise LedgerError(f'Moeda não suportada: {value}')
    return normalized


def decimal_input(value: Decimal, *, scale: int = 8, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise LedgerError('Valor financeiro deve ser Decimal finito.')
    if value < 0 or (positive and value == 0):
        raise LedgerError('Sinal financeiro inválido.')
    if value >= Decimal('1e18') or value.as_tuple().exponent < -scale:
        raise LedgerError('Magnitude ou escala financeira excedida.')
    return value


def canonical(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise LedgerError('Decimal finito obrigatório.')
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str
    fx_rate: Decimal | None = None
    original_text: str | None = None

    def __post_init__(self):
        decimal_input(self.amount)
        object.__setattr__(self, 'currency', currency(self.currency))
        if self.fx_rate is not None:
            decimal_input(self.fx_rate, scale=12, positive=True)

    def in_base(self, base: str) -> Decimal:
        if self.currency == base:
            if self.fx_rate not in (None, Decimal(1)):
                raise LedgerError('FX de identidade deve ser 1.')
            return self.amount
        if self.fx_rate is None:
            raise LedgerError(f'FX histórico ausente: {self.currency} → {base}')
        with localcontext(FINANCIAL_CONTEXT):
            return self.amount * self.fx_rate
