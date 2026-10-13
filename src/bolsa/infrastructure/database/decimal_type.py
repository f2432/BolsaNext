from decimal import Decimal

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from bolsa.domain.portfolio.values import PortfolioError, decimal_text


class ExactDecimalText(TypeDecorator):
    """SQLite financial boundary: exact decimal text, never REAL or float."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else decimal_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, str):
            raise PortfolioError("Non-text financial value in database")
        try:
            number = Decimal(value)
        except ArithmeticError as exc:
            raise PortfolioError("Invalid stored decimal") from exc
        if decimal_text(number) != value:
            raise PortfolioError("Non-canonical stored decimal")
        return number
