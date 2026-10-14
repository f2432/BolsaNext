from dataclasses import dataclass, replace
from datetime import datetime, timezone

from bolsa.app.ports.errors import MarketDataError
from bolsa.app.ports.portfolio import PortfolioRepository
from bolsa.app.ports.portfolio_quotes import PortfolioQuoteProvider
from bolsa.app.portfolio_format import PortfolioTransferService
from bolsa.app.services.portfolio_service import PortfolioService
from bolsa.app.services.portfolio_analysis_service import PortfolioAnalysisService, PortfolioAnalysis
from bolsa.domain.portfolio.valuation import ValuationResult
from bolsa.domain.portfolio.ledger import Portfolio, effective_versions
from bolsa.domain.portfolio.values import PortfolioError


@dataclass(frozen=True, slots=True)
class PortfolioDashboard:
    portfolios: tuple[Portfolio, ...]
    portfolio: Portfolio | None
    valuation: ValuationResult | None = None
    analysis: PortfolioAnalysis | None = None


class PortfolioDashboardService:
    def __init__(self, repository: PortfolioRepository, valuation_service,
                 quote_provider: PortfolioQuoteProvider):
        self.repository = repository
        self.portfolio = PortfolioService(repository)
        self.transfer = PortfolioTransferService(repository)
        self._valuation = valuation_service
        self._quotes = quote_provider

    def overview(self, portfolio_uid=None, *, market=False):
        portfolios = self.repository.list_portfolios()
        portfolio = next((p for p in portfolios if p.portfolio_uid == portfolio_uid), None)
        if portfolio is None and portfolio_uid is None and portfolios:
            portfolio = portfolios[0]
        if portfolio is None:
            return PortfolioDashboard(portfolios, None)
        prices, errors = {}, []
        if market:
            open_tickers = {p.ticker for p in portfolio.reconstruct().positions if p.quantity > 0}
            instruments = {v.trade.instrument.ticker: v.trade.instrument for v in effective_versions(
                portfolio.portfolio_uid, portfolio.versions
            )}
            for ticker in sorted(open_tickers):
                try:
                    prices[ticker] = self._quotes.get_quote(instruments[ticker])
                except (MarketDataError, PortfolioError) as exc:
                    errors.append(f"{ticker}: {exc}")
        valuation = self._valuation.evaluate(portfolio, prices, now=datetime.now(timezone.utc))
        valuation = replace(valuation, data_errors=valuation.data_errors + tuple(errors))
        # One immutable accounting snapshot throughout network requests and rendering.
        analysis = PortfolioAnalysisService.analyze_snapshot(portfolio, valuation)
        return PortfolioDashboard(portfolios, portfolio, valuation, analysis)
