from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from bolsa.domain.portfolio.money import canonical
from bolsa.domain.portfolio.policy import InvestmentPolicy

FINANCIAL_FIELDS = ('max_instrument_weight','max_sector_weight','max_currency_weight','annualized_return_target')


def policy_dict(policy):
    data = asdict(policy)
    for key in FINANCIAL_FIELDS:
        value = getattr(policy,key)
        data[key] = canonical(value) if value is not None else None
    for key in ('recorded_at','effective_from'):
        data[key] = data[key].isoformat()
    return data


def policy_from(data):
    data = dict(data)
    for key in FINANCIAL_FIELDS:
        value = data[key]
        if value is not None and type(value) is not str:
            raise ValueError('Limite financeiro deve ser texto.')
        data[key] = Decimal(value) if value is not None else None
    for key in ('recorded_at','effective_from'):
        data[key] = datetime.fromisoformat(data[key])
    return InvestmentPolicy(**data)
