from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, localcontext

from bolsa.domain.portfolio.models import uid, check_uid, utc_now
from bolsa.domain.portfolio.money import LedgerError, FINANCIAL_CONTEXT, decimal_input


@dataclass(frozen=True, slots=True)
class InvestmentPolicy:
    version_number: int = 1
    policy_version_uid: str = field(default_factory=uid)
    previous_version_uid: str | None = None
    effective_from: datetime = field(default_factory=utc_now)
    recorded_at: datetime = field(default_factory=utc_now)
    max_instrument_weight: Decimal | None = None
    max_sector_weight: Decimal | None = None
    max_currency_weight: Decimal | None = None
    annualized_return_target: Decimal | None = None
    notes: str = ""

    def __post_init__(self):
        check_uid(self.policy_version_uid)
        if not isinstance(self.notes, str) or len(self.notes) > 10000:
            raise LedgerError("Notas da política inválidas.")
        if self.previous_version_uid is not None:
            check_uid(self.previous_version_uid)
        if type(self.version_number) is not int or self.version_number < 1:
            raise LedgerError("Versão de política inválida.")
        if (self.version_number == 1) != (self.previous_version_uid is None):
            raise LedgerError("Cadeia de política inválida.")
        for stamp in (self.effective_from, self.recorded_at):
            if not isinstance(stamp, datetime) or stamp.tzinfo is None or stamp.utcoffset() is None:
                raise LedgerError("Política exige instante com fuso.")
        for limit in (self.max_instrument_weight, self.max_sector_weight, self.max_currency_weight):
            if limit is not None and (decimal_input(limit) > 1):
                raise LedgerError("Limite de concentração deve estar entre 0 e 1.")
        if self.annualized_return_target is not None:
            decimal_input(self.annualized_return_target)


def validate_policies(policies):
    previous = None
    ids = set()
    for policy in sorted(policies, key=lambda p: p.version_number):
        if policy.policy_version_uid in ids:
            raise LedgerError("Identidade de política duplicada.")
        ids.add(policy.policy_version_uid)
        if previous is None:
            if policy.version_number != 1:
                raise LedgerError("Política sem origem.")
        elif (
            policy.version_number != previous.version_number + 1
            or policy.previous_version_uid != previous.policy_version_uid
            or policy.effective_from < previous.effective_from
        ):
            raise LedgerError("Política ramificada/obsoleta ou vigência retroativa.")
        previous = policy


def active_policy(policies, now):
    validate_policies(policies)
    eligible = [p for p in policies if p.effective_from <= now]
    return max(eligible, key=lambda p: p.version_number) if eligible else None


@dataclass(frozen=True, slots=True)
class Alert:
    metric: str
    subject: str
    state: str
    value: Decimal | None
    limit: Decimal | None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class RiskReport:
    instrument_weights: tuple[tuple[str, Decimal], ...] | None
    sector_weights: tuple[tuple[str, Decimal], ...] | None
    quote_currency_weights: tuple[tuple[str, Decimal], ...] | None
    alerts: tuple[Alert, ...]


def evaluate_risk(valuation, *, policy=None, sectors=None):
    sectors = sectors or {}
    if valuation.total is None or valuation.total <= 0:
        alerts = tuple(
            Alert(
                metric,
                "carteira",
                "not_evaluable",
                None,
                limit,
                "Total completo positivo indisponível",
            )
            for metric, limit in _limits(policy)
            if limit is not None
        )
        if policy is not None and policy.annualized_return_target is not None:
            alerts += (
                Alert(
                    "annualized_return",
                    "carteira",
                    "not_evaluable",
                    None,
                    policy.annualized_return_target,
                    "Metodologia anualizada ainda não aprovada",
                ),
            )
        return RiskReport(None, None, None, alerts)
    instruments, sector_values, currencies = {}, {}, {}
    unknown_sector = False
    with localcontext(FINANCIAL_CONTEXT):
        for position in valuation.positions:
            weight = position.market_value / valuation.total
            instruments[position.ticker] = weight
            denomination = position.quote.currency
            currencies[denomination] = currencies.get(denomination, Decimal(0)) + weight
            # No approved look-through composition model exists for ETFs in V0.3.
            sector = sectors.get(position.ticker) if position.asset_type == "stock" else None
            if not sector:
                unknown_sector = True
                sector = "não determinado"
            sector_values[sector] = sector_values.get(sector, Decimal(0)) + weight
    alerts = []
    groups = {"instrument": instruments, "sector": sector_values, "quote_currency": currencies}
    for metric, limit in _limits(policy):
        if limit is None:
            continue
        if metric == "sector" and unknown_sector:
            alerts.append(
                Alert(
                    metric,
                    "carteira",
                    "not_evaluable",
                    None,
                    limit,
                    "Setor/ETF subjacente não determinado",
                )
            )
        else:
            for subject, value in sorted(groups[metric].items()):
                alerts.append(
                    Alert(
                        metric,
                        subject,
                        "exceeded" if value > limit else "within_limit",
                        value,
                        limit,
                    )
                )
    if policy is not None and policy.annualized_return_target is not None:
        alerts.append(
            Alert(
                "annualized_return",
                "carteira",
                "not_evaluable",
                None,
                policy.annualized_return_target,
                "Metodologia anualizada ainda não aprovada",
            )
        )
    return RiskReport(
        tuple(sorted(instruments.items())),
        tuple(sorted(sector_values.items())),
        tuple(sorted(currencies.items())),
        tuple(alerts),
    )


def _limits(policy):
    if policy is None:
        return ()
    return (
        ("instrument", policy.max_instrument_weight),
        ("sector", policy.max_sector_weight),
        ("quote_currency", policy.max_currency_weight),
    )
