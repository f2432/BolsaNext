from decimal import localcontext
from bolsa.domain.portfolio.money import FINANCIAL_CONTEXT


def amount_label(value, currency, *, average=False):
    """Presentation only; never re-used as a financial input."""
    decimals = 8 if average else (0 if currency in ("JPY", "KRW") else 2)
    with localcontext(FINANCIAL_CONTEXT):
        text = format(value, f".{decimals}f")
    return text.rstrip("0").rstrip(".") if average else text


def execution_label(value):
    from datetime import datetime

    return value.astimezone().isoformat() if isinstance(value, datetime) else value.isoformat()
