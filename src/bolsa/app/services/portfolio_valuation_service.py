from bolsa.app.ports.errors import MarketDataError
from bolsa.domain.portfolio.ledger import effective_versions
from bolsa.domain.portfolio.valuation import value_portfolio


class PortfolioValuationService:
    def __init__(self, repository, quote_provider, fx_provider):
        self.repository = repository
        self.quote_provider = quote_provider
        self.fx_provider = fx_provider

    def evaluate(self, portfolio_uid, **valuation_options):
        ledger = self.repository.load(portfolio_uid)
        instruments = {v.transaction.instrument.ticker: v.transaction.instrument for v in effective_versions(ledger)}
        quotes, rates = {}, {}
        for ticker, instrument in instruments.items():
            try:
                quotes[ticker] = self.quote_provider.get_quote(instrument)
                denomination = quotes[ticker].currency
                if denomination != ledger.portfolio.base_currency and denomination not in rates:
                    rates[denomination] = self.fx_provider.get_rate(denomination, ledger.portfolio.base_currency)
            except MarketDataError:
                continue
        return value_portfolio(ledger, quotes, rates, **valuation_options)
