from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import RLock

from bolsa.app.ports.errors import MarketDataError
from bolsa.app.ports.portfolio import PortfolioRepository
from bolsa.app.ports.portfolio_quotes import PortfolioQuoteProvider
from bolsa.app.portfolio_format import PortfolioTransferService
from bolsa.app.services.portfolio_service import PortfolioService
from bolsa.app.services.portfolio_analysis_service import PortfolioAnalysisService, PortfolioAnalysis
from bolsa.domain.portfolio.valuation import ValuationResult
from bolsa.domain.portfolio.ledger import Portfolio, effective_versions
from bolsa.domain.portfolio.values import PortfolioError
from bolsa.domain.portfolio.reconciliation import reconcile


@dataclass(frozen=True, slots=True)
class PortfolioDashboard:
    portfolios: tuple[Portfolio, ...]
    portfolio: Portfolio | None
    valuation: ValuationResult | None = None
    analysis: PortfolioAnalysis | None = None


class PortfolioDashboardService:
    def __init__(self, repository: PortfolioRepository, valuation_service,
                 quote_provider: PortfolioQuoteProvider, *, clock=None):
        self.repository = repository
        self.portfolio = PortfolioService(repository)
        self.transfer = PortfolioTransferService(repository)
        self._valuation = valuation_service
        self._quotes = quote_provider
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        # Session-only source snapshots, never authoritative ledger/projection data.
        self._snapshots = {}
        self._snapshot_lock = RLock()

    def _snapshot(self, portfolio):
        with self._snapshot_lock:
            snapshot = self._snapshots.get(portfolio.portfolio_uid)
            if snapshot is not None and (snapshot.ledger_revision, snapshot.base_currency) != (
                portfolio.ledger_revision, portfolio.base_currency
            ):
                # A stale reader must not delete a newer concurrent snapshot.
                if snapshot.ledger_revision <= portfolio.ledger_revision:
                    self._snapshots.pop(portfolio.portfolio_uid)
                return None
            return snapshot

    def _remember(self, portfolio, valuation):
        with self._snapshot_lock:
            current = self._snapshots.get(valuation.portfolio_uid)
            if current is None or valuation.ledger_revision > current.ledger_revision or (
                valuation.ledger_revision == current.ledger_revision and
                valuation.evaluated_at >= current.evaluated_at and
                (valuation.complete or not current.complete or not self._valuation.revalue(
                    portfolio, current, now=valuation.evaluated_at
                ).complete)
            ):
                self._snapshots[valuation.portfolio_uid] = valuation

    def overview(self, portfolio_uid=None, *, market=False):
        portfolios = self.repository.list_portfolios()
        portfolio = next((p for p in portfolios if p.portfolio_uid == portfolio_uid), None)
        if portfolio is None and portfolio_uid is None and portfolios:
            portfolio = portfolios[0]
        if portfolio is None:
            return PortfolioDashboard(portfolios, None)
        snapshot = self._snapshot(portfolio)
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
        now = self._clock()
        if market:
            valuation = self._valuation.evaluate(portfolio, prices, now=now)
        elif snapshot is not None:
            valuation = self._valuation.revalue(portfolio, snapshot, now=now)
        else:
            # No quotes means no FX request either. This path is strictly offline.
            valuation = self._valuation.evaluate(portfolio, {}, now=now)
        valuation = replace(valuation, data_errors=valuation.data_errors + tuple(errors))
        if market:
            self._remember(portfolio, valuation)
        # One immutable accounting snapshot throughout network requests and rendering.
        analysis = PortfolioAnalysisService.analyze_snapshot(portfolio, valuation)
        return PortfolioDashboard(portfolios, portfolio, valuation, analysis)

    def reconcile(self, portfolio_uid):
        """Accounting integrity is independent of Yahoo and market completeness."""
        dashboard = self.overview(portfolio_uid)
        if dashboard.portfolio is None:
            return dashboard
        analysis = replace(dashboard.analysis, reconciliation=reconcile(dashboard.portfolio))
        return replace(dashboard, analysis=analysis)
