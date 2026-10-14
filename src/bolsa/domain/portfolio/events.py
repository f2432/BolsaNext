from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from bolsa.domain.instruments.instrument import AssetType, Instrument
from bolsa.domain.portfolio.values import MoneyComponent, PortfolioError, financial_decimal


def _validate_metadata(event):
    if not isinstance(event.instrument, Instrument) or event.instrument.asset_type not in (
        AssetType.STOCK, AssetType.ETF
    ) or not isinstance(event.instrument.asset_type, AssetType):
        raise PortfolioError("Only stocks and ETFs are supported")
    if isinstance(event.executed_at, datetime):
        if event.executed_at.tzinfo is None or event.executed_at.utcoffset() is None:
            raise PortfolioError("Execution instant must be timezone aware")
    elif type(event.executed_at) is not date:
        raise PortfolioError("Execution must have a date or aware instant")
    if event.broker_sequence is not None and (
        type(event.broker_sequence) is not int or event.broker_sequence < 0
    ):
        raise PortfolioError("Invalid broker sequence")
    if event.settlement_date is not None and type(event.settlement_date) is not date:
        raise PortfolioError("Settlement must be a date")
    if not isinstance(event.source, str) or not event.source.strip() or (
        bool(event.account_ref) != bool(event.external_id)
    ):
        raise PortfolioError("Incomplete source identity")
    if not isinstance(event.original_facts, tuple) or any(
        not isinstance(pair, tuple) or len(pair) != 2 or
        any(not isinstance(v, str) for v in pair) for pair in event.original_facts
    ):
        raise PortfolioError("Original facts must be immutable text pairs")


def _execution_key(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.combine(value, datetime.min.time(), timezone.utc)


@dataclass(frozen=True, slots=True)
class Dividend:
    instrument: Instrument
    gross: MoneyComponent
    withholding: MoneyComponent
    charges: MoneyComponent
    net: MoneyComponent
    executed_at: date | datetime
    broker_sequence: int | None = None
    settlement_date: date | None = None
    notes: str = ""
    source: str = "manual"
    account_ref: str | None = None
    external_id: str | None = None
    original_facts: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        _validate_metadata(self)
        if any(not isinstance(component, MoneyComponent) for component in (
            self.gross, self.withholding, self.charges, self.net
        )):
            raise PortfolioError("Dividend components must be monetary values")
        if self.gross.amount <= 0:
            raise PortfolioError("Gross dividend must be positive")

    @property
    def execution_key(self):
        return _execution_key(self.executed_at)


@dataclass(frozen=True, slots=True)
class Split:
    instrument: Instrument
    factor: Decimal
    adjustment_reason: str
    executed_at: date | datetime
    broker_sequence: int | None = None
    settlement_date: date | None = None
    notes: str = ""
    source: str = "manual"
    account_ref: str | None = None
    external_id: str | None = None
    original_facts: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        _validate_metadata(self)
        object.__setattr__(self, "factor", financial_decimal(self.factor))
        if self.factor < 2 or self.factor != self.factor.to_integral_value():
            raise PortfolioError("Only simple forward integer splits are supported")
        if not isinstance(self.adjustment_reason, str) or not self.adjustment_reason.strip():
            raise PortfolioError("Split requires an adjustment reason")

    @property
    def execution_key(self):
        return _execution_key(self.executed_at)
