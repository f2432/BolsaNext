from sqlalchemy import func, select

from bolsa.domain.instruments import Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistState
from bolsa.infrastructure.database import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from bolsa.infrastructure.database.models import (
    InstrumentModel,
    WatchlistItemModel,
)
from bolsa.infrastructure.repositories import SqlAlchemyWatchlistRepository


def test_watchlist_persists_and_reloads() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        initialize_database(engine)
        repository = SqlAlchemyWatchlistRepository(create_session_factory(engine))

        watchlist = Watchlist("Principal")
        watchlist.add(
            Instrument(
                ticker="AAPL",
                name="Apple Inc.",
                market="NASDAQ",
                currency="USD",
            ),
            state=WatchlistState.CANDIDATE,
        )

        repository.save(watchlist)
        loaded = repository.load("Principal")

        assert loaded is not None
        item = loaded.get("AAPL")
        assert item is not None
        assert item.instrument.name == "Apple Inc."
        assert item.instrument.market == "NASDAQ"
        assert item.instrument.currency == "USD"
        assert item.state == WatchlistState.CANDIDATE
    finally:
        engine.dispose()


def test_watchlist_repository_persists_removal() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        initialize_database(engine)
        session_factory = create_session_factory(engine)
        repository = SqlAlchemyWatchlistRepository(session_factory)

        watchlist = Watchlist("Principal")
        watchlist.add(Instrument("AAPL"))
        watchlist.add(Instrument("MSFT"))
        repository.save(watchlist)

        watchlist.remove("AAPL")
        repository.save(watchlist)

        loaded = repository.load("Principal")
        assert loaded is not None
        assert loaded.get("AAPL") is None
        assert loaded.get("MSFT") is not None

        with session_factory() as session:
            aapl = session.scalar(
                select(InstrumentModel).where(
                    InstrumentModel.ticker == "AAPL"
                )
            )
            item_count = session.scalar(
                select(func.count()).select_from(WatchlistItemModel)
            )

        assert aapl is not None
        assert item_count == 1
    finally:
        engine.dispose()
