from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from bolsa.config import AppConfig, prepare_environment
from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.models import Transaction, TransactionType
from bolsa.domain.portfolio.money import Money
from bolsa.infrastructure.database import ensure_database_schema, create_database_engine
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository
from bolsa.app.services.portfolio_service import PortfolioService


@pytest.fixture
def trade():
    def make(kind='BUY', quantity='10', price='100', fee='0', day=0, **kwargs):
        return Transaction(Instrument('TEST', currency='EUR'), TransactionType(kind),
            datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day),
            Decimal(quantity), Money(Decimal(price), 'EUR'), Money(Decimal(fee), 'EUR'), **kwargs)
    return make


@pytest.fixture
def repository(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    prepare_environment(config)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    yield SqlAlchemyPortfolioRepository(engine)
    engine.dispose()


@pytest.fixture
def service(repository):
    return PortfolioService(repository)
