from datetime import datetime, timedelta
from dataclasses import replace
from typing import Mapping

from bolsa.app.ports.fx import FxRateError, FxRateProvider
from bolsa.domain.portfolio.ledger import Portfolio
from bolsa.domain.portfolio.valuation import PriceQuote, ValuationResult, value_portfolio


class PortfolioValuationService:
    def __init__(self, fx_provider: FxRateProvider):
        self._fx_provider = fx_provider

    def evaluate(self, portfolio: Portfolio, prices: Mapping[str, PriceQuote], *, now: datetime,
                 max_age: timedelta = timedelta(hours=72)) -> ValuationResult:
        rates = {}
        errors = []
        open_tickers = {p.ticker for p in portfolio.reconstruct().positions if p.quantity > 0}
        currencies = {quote.currency for ticker, quote in prices.items() if ticker in open_tickers}
        for currency in sorted(currencies):
            if currency == portfolio.base_currency:
                continue
            try:
                rates[(currency, portfolio.base_currency)] = self._fx_provider.get_rate(
                    currency, portfolio.base_currency,
                )
            except FxRateError as exc:
                # Missing data affects valuation only, never the historical ledger.
                errors.append(f"{currency}->{portfolio.base_currency}: {type(exc).__name__}: {exc}")
        result = value_portfolio(portfolio, prices, rates, now=now, max_age=max_age)
        return replace(result, data_errors=tuple(errors))
