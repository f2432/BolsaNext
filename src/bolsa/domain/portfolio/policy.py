from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from bolsa.domain.portfolio.values import PortfolioError, decimal_text, financial_decimal


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PortfolioError("Policy dates must be timezone aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class PolicyParameters:
    max_asset_weight: Decimal | None = None
    max_sector_weight: Decimal | None = None
    max_quote_currency_weight: Decimal | None = None
    annual_return_target: Decimal | None = None

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if value is None:
                continue
            if name == "annual_return_target":
                if not isinstance(value, (Decimal, str)):
                    raise PortfolioError("Policy targets require exact decimal text or Decimal")
                try:
                    raw = Decimal(value)
                except ArithmeticError as exc:
                    raise PortfolioError("Invalid target decimal") from exc
                magnitude = financial_decimal(raw.copy_abs())
                number = magnitude.copy_negate() if raw.is_signed() else magnitude
            else:
                number = financial_decimal(value)
            if name != "annual_return_target" and number > 1:
                raise PortfolioError("Concentration limits must be fractions in [0,1]")
            object.__setattr__(self, name, number)


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    portfolio_uid: UUID
    parameters: PolicyParameters
    version_number: int
    previous_version_uid: UUID | None
    effective_at: datetime
    reason: str
    policy_version_uid: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if any(not isinstance(uid, UUID) for uid in (self.portfolio_uid, self.policy_version_uid)):
            raise PortfolioError("Policy identities must be UUID")
        if self.previous_version_uid is not None and not isinstance(self.previous_version_uid, UUID):
            raise PortfolioError("Invalid policy predecessor")
        if not isinstance(self.parameters, PolicyParameters) or type(self.version_number) is not int or self.version_number < 1:
            raise PortfolioError("Invalid policy version")
        if (self.version_number == 1) != (self.previous_version_uid is None):
            raise PortfolioError("Invalid policy version predecessor")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise PortfolioError("Policy change requires a reason")
        object.__setattr__(self, "effective_at", _aware(self.effective_at))
        object.__setattr__(self, "recorded_at", _aware(self.recorded_at))


def validate_policy_history(portfolio_uid, policies):
    if not isinstance(policies, tuple):
        raise PortfolioError("Policy history must be immutable")
    if any(not isinstance(p, PolicyVersion) for p in policies):
        raise PortfolioError("Invalid policy history entries")
    previous = None
    seen = set()
    for number, policy in enumerate(sorted(policies, key=lambda p: p.version_number), 1):
        if not isinstance(policy, PolicyVersion) or policy.portfolio_uid != portfolio_uid:
            raise PortfolioError("Policy belongs to another portfolio")
        if policy.policy_version_uid in seen or policy.version_number != number or policy.previous_version_uid != (
            previous.policy_version_uid if previous else None
        ):
            raise PortfolioError("Broken or branched policy history")
        if previous and (policy.effective_at < previous.effective_at or policy.recorded_at < previous.recorded_at):
            raise PortfolioError("Policy dates must be monotonic")
        seen.add(policy.policy_version_uid)
        previous = policy


def active_policy(policies, at: datetime):
    at = _aware(at)
    eligible = [p for p in policies if p.effective_at <= at and p.recorded_at <= at]
    return max(eligible, key=lambda p: p.version_number) if eligible else None


def encode_policy(policy):
    return dict(
        portfolio_uid=str(policy.portfolio_uid), policy_version_uid=str(policy.policy_version_uid),
        version_number=policy.version_number,
        previous_version_uid=str(policy.previous_version_uid) if policy.previous_version_uid else None,
        effective_at=policy.effective_at.isoformat(), recorded_at=policy.recorded_at.isoformat(), reason=policy.reason,
        parameters={name: decimal_text(value) if value is not None else None
                    for name, value in ((name, getattr(policy.parameters, name)) for name in PolicyParameters.__dataclass_fields__)},
    )


def decode_policy(data):
    if not isinstance(data, dict) or set(data) != {
        "portfolio_uid", "policy_version_uid", "version_number", "previous_version_uid",
        "effective_at", "recorded_at", "reason", "parameters"
    } or not isinstance(data["parameters"], dict) or set(data["parameters"]) != set(PolicyParameters.__dataclass_fields__):
        raise PortfolioError("Invalid policy fields")
    params = {}
    for name, value in data["parameters"].items():
        if value is not None and not isinstance(value, str):
            raise PortfolioError("Policy financial parameters must be decimal strings")
        params[name] = value
    return PolicyVersion(
        UUID(data["portfolio_uid"]), PolicyParameters(**params), data["version_number"],
        UUID(data["previous_version_uid"]) if data["previous_version_uid"] else None,
        datetime.fromisoformat(data["effective_at"]), data["reason"], UUID(data["policy_version_uid"]),
        datetime.fromisoformat(data["recorded_at"]),
    )
