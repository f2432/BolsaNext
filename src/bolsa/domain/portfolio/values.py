from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext


class PortfolioError(ValueError):
    """An invalid financial value or ledger operation."""


class LedgerConflictError(PortfolioError):
    """The expected ledger revision or transaction head is obsolete."""


FINANCIAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
# Initial supported ISO 4217 currencies; extend deliberately, never infer from FX availability.
SUPPORTED_CURRENCIES = frozenset(
    "EUR USD GBP CHF JPY CAD AUD NZD SEK NOK DKK PLN CZK HKD SGD ZAR ILS".split()
)


def currency_code(value: str) -> str:
    if not isinstance(value, str) or value.strip().upper() not in SUPPORTED_CURRENCIES:
        raise PortfolioError(f"Unsupported currency: {value!r}")
    return value.strip().upper()


def financial_decimal(value: Decimal | str, *, scale: int = 8, positive: bool = False) -> Decimal:
    """Exact inputs only. Scale overflow is rejected, never rounded."""
    if not isinstance(value, (Decimal, str)):
        raise PortfolioError("Financial inputs must be Decimal or decimal text")
    try:
        number = Decimal(value)
    except ArithmeticError as exc:
        raise PortfolioError("Invalid decimal text") from exc
    if not number.is_finite():
        raise PortfolioError("Financial inputs must be finite")
    if number < 0 or (positive and number == 0):
        raise PortfolioError("Invalid financial sign")
    if number >= Decimal("1e18") or number.as_tuple().exponent < -scale:
        raise PortfolioError("Financial input exceeds magnitude or scale")
    return number


def decimal_text(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise PortfolioError("Only finite Decimal can be serialized")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if value == 0 else text


@dataclass(frozen=True, slots=True)
class MoneyComponent:
    amount: Decimal
    currency: str
    # Units of portfolio base currency per unit of this component's currency.
    historical_fx: Decimal | None = None

    def __post_init__(self):
        object.__setattr__(self, "amount", financial_decimal(self.amount))
        object.__setattr__(self, "currency", currency_code(self.currency))
        if self.historical_fx is not None:
            object.__setattr__(self, "historical_fx", financial_decimal(
                self.historical_fx, scale=12, positive=True
            ))

    def rate_to_base(self, base_currency: str) -> Decimal:
        base = currency_code(base_currency)
        if self.currency == base:
            if self.historical_fx not in (None, Decimal("1")):
                raise PortfolioError("Same-currency FX must equal one")
            rate = Decimal("1")
        else:
            if self.historical_fx is None:
                raise PortfolioError(f"Missing historical FX: {self.currency} -> {base}")
            rate = self.historical_fx
        return rate

    def in_base(self, base_currency: str) -> Decimal:
        with localcontext(FINANCIAL_CONTEXT):
            return self.amount * self.rate_to_base(base_currency)
