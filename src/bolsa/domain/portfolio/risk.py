from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Mapping
from uuid import UUID

from bolsa.domain.instruments.instrument import AssetType
from bolsa.domain.portfolio.ledger import Portfolio, effective_versions
from bolsa.domain.portfolio.policy import active_policy
from bolsa.domain.portfolio.valuation import ValuationResult, ValuationState
from bolsa.domain.portfolio.values import FINANCIAL_CONTEXT, PortfolioError, exact_sum


class AlertState(StrEnum):
    WITHIN_LIMIT = "within_limit"
    EXCEEDED = "exceeded"
    NOT_EVALUABLE = "not_evaluable"


@dataclass(frozen=True, slots=True)
class SectorClassification:
    label: str | None = None
    underlying_exposure_confirmed: bool = False

    def __post_init__(self):
        if self.label is not None and not isinstance(self.label, str):
            raise PortfolioError("Sector label must be text or unknown")
        if self.label is not None:
            label = self.label.strip()
            if label.casefold() in {"", "unknown", "not determined", "não determinado", "n/a", "none"}:
                label = None
            object.__setattr__(self, "label", label)
        if type(self.underlying_exposure_confirmed) is not bool:
            raise PortfolioError("Underlying exposure confirmation must be explicit")


@dataclass(frozen=True, slots=True)
class PolicyAlert:
    metric: str
    state: AlertState
    limit: Decimal
    actual: Decimal | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RiskReport:
    asset_weights: tuple[tuple[str, Decimal | None], ...]
    sector_weights: tuple[tuple[str, Decimal | None], ...]
    quote_currency_weights: tuple[tuple[str, Decimal | None], ...]
    alerts: tuple[PolicyAlert, ...]
    policy_version_uid: UUID | None
    reason: str | None
    currency_exposure_label: str = "quote currency; not underlying economic FX exposure"


def evaluate_risk(portfolio: Portfolio, valuation: ValuationResult,
                  sectors: Mapping[str, SectorClassification] | None = None) -> RiskReport:
    sectors = sectors or {}
    open_positions = {p.ticker for p in portfolio.reconstruct().positions if p.quantity > 0}
    rows = {p.ticker: p for p in valuation.positions}
    current = (valuation.portfolio_uid == portfolio.portfolio_uid and
               valuation.ledger_revision == portfolio.ledger_revision and
               valuation.base_currency == portfolio.base_currency and set(rows) == open_positions and
               len(rows) == len(valuation.positions))
    complete = current and isinstance(valuation.total_market_value, Decimal) and (
        valuation.total_market_value.is_finite() and valuation.total_market_value > 0
    ) and all(p.state is ValuationState.AVAILABLE and isinstance(p.market_value, Decimal) and
              p.market_value.is_finite() and p.market_value > 0 and p.price_quote is not None for p in rows.values())
    if complete:
        with localcontext(FINANCIAL_CONTEXT):
            complete = exact_sum(*(p.market_value for p in rows.values())) == valuation.total_market_value
    reason = None if complete else "A positive complete valuation of the current ledger is required"
    assets = {ticker: None for ticker in open_positions}
    sector_weights = {}
    currency_weights = {}
    sector_complete = True
    kinds = {}
    for event in sorted(effective_versions(portfolio.portfolio_uid, portfolio.versions),
                        key=lambda v: (v.trade.execution_key, v.transaction_uid.hex)):
        kinds[event.trade.instrument.ticker] = event.trade.instrument.asset_type
    with localcontext(FINANCIAL_CONTEXT):
        for ticker in sorted(open_positions):
            row = rows.get(ticker)
            classification = sectors.get(ticker, SectorClassification())
            sector = classification.label
            if not sector or (kinds[ticker] is AssetType.ETF and not classification.underlying_exposure_confirmed):
                sector = "not determined"
                sector_complete = False
            currency = row.price_quote.currency if row and row.price_quote else "not determined"
            weight = row.market_value / valuation.total_market_value if complete else None
            assets[ticker] = weight
            for mapping, key in ((sector_weights, sector), (currency_weights, currency)):
                mapping[key] = mapping.get(key, Decimal("0")) + weight if complete else None
    policy = active_policy(portfolio.policies, valuation.evaluated_at)
    alerts = []
    if policy is not None:
        params = policy.parameters
        metrics = (
            ("asset_concentration", params.max_asset_weight, assets, complete),
            ("sector_concentration", params.max_sector_weight, sector_weights, complete and sector_complete),
            ("quote_currency_concentration", params.max_quote_currency_weight, currency_weights, complete),
        )
        for name, limit, mapping, evaluable in metrics:
            if limit is None:
                continue
            actual = max(mapping.values()) if evaluable and mapping else None
            state = AlertState.NOT_EVALUABLE if actual is None else (
                AlertState.WITHIN_LIMIT if actual <= limit else AlertState.EXCEEDED
            )
            alerts.append(PolicyAlert(name, state, limit, actual,
                                      None if actual is not None else reason or "Sector exposure is not determined"))
        if params.annual_return_target is not None:
            alerts.append(PolicyAlert("annual_return_target", AlertState.NOT_EVALUABLE,
                                      params.annual_return_target, None, "Annual return methodology is not approved"))
    return RiskReport(tuple(sorted(assets.items())), tuple(sorted(sector_weights.items())),
                      tuple(sorted(currency_weights.items())), tuple(alerts),
                      policy.policy_version_uid if policy else None, reason)
