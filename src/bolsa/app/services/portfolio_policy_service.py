from dataclasses import replace

from bolsa.domain.portfolio.policy import InvestmentPolicy, active_policy, evaluate_risk
from bolsa.domain.portfolio.money import StaleRevisionError


class PortfolioPolicyService:
    def __init__(self, repository):
        self.repository = repository

    def set_policy(self, portfolio_uid, *, expected_revision, **parameters):
        ledger = self.repository.load(portfolio_uid)
        if ledger.revision != expected_revision:
            raise StaleRevisionError("Revisão de política obsoleta.")
        previous = ledger.policies[-1] if ledger.policies else None
        policy = InvestmentPolicy(
            version_number=previous.version_number + 1 if previous else 1,
            previous_version_uid=previous.policy_version_uid if previous else None,
            **parameters,
        )
        incoming = replace(ledger, policies=ledger.policies + (policy,))
        saved, _ = self.repository.import_ledger(incoming, expected_revision=expected_revision)
        return saved

    def evaluate(self, ledger, valuation, *, now, sectors=None):
        return evaluate_risk(valuation, policy=active_policy(ledger.policies, now), sectors=sectors)
