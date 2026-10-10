from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from bolsa.domain.instruments import AssetType, Instrument
from bolsa.domain.watchlist import Watchlist, WatchlistItem, WatchlistState
from bolsa.infrastructure.database.models import (
    InstrumentModel,
    WatchlistItemModel,
    WatchlistModel,
)


class SqlAlchemyWatchlistRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def load(self, name: str) -> Watchlist | None:
        with self._session_factory() as session:
            stmt = (
                select(WatchlistModel)
                .where(WatchlistModel.name == name)
                .options(
                    selectinload(WatchlistModel.items).selectinload(
                        WatchlistItemModel.instrument
                    )
                )
            )
            model = session.scalar(stmt)
            if model is None:
                return None

            items = [
                WatchlistItem(
                    instrument=Instrument(
                        ticker=item.instrument.ticker,
                        name=item.instrument.name,
                        exchange=item.instrument.exchange,
                        currency=item.instrument.currency,
                        asset_type=AssetType(item.instrument.asset_type),
                    ),
                    state=WatchlistState(item.state),
                    notes=item.notes or "",
                )
                for item in model.items
            ]
            return Watchlist(name=model.name, items=items)

    def save(self, watchlist: Watchlist) -> None:
        with self._session_factory() as session:
            try:
                model = session.scalar(
                    select(WatchlistModel)
                    .where(WatchlistModel.name == watchlist.name)
                    .options(selectinload(WatchlistModel.items))
                )
                if model is None:
                    model = WatchlistModel(name=watchlist.name)
                    session.add(model)
                    session.flush()

                existing_items = {
                    item.instrument_id: item
                    for item in model.items
                }
                desired_instrument_ids: set[int] = set()

                for domain_item in watchlist.items:
                    instrument_model = session.scalar(
                        select(InstrumentModel).where(
                            InstrumentModel.ticker == domain_item.instrument.ticker
                        )
                    )
                    if instrument_model is None:
                        instrument_model = InstrumentModel(
                            ticker=domain_item.instrument.ticker,
                            name=domain_item.instrument.name,
                            exchange=domain_item.instrument.exchange,
                            currency=domain_item.instrument.currency,
                            asset_type=domain_item.instrument.asset_type.value,
                        )
                        session.add(instrument_model)
                        session.flush()
                    else:
                        if domain_item.instrument.name:
                            instrument_model.name = domain_item.instrument.name
                        instrument_model.exchange = domain_item.instrument.exchange
                        instrument_model.currency = domain_item.instrument.currency
                        instrument_model.asset_type = domain_item.instrument.asset_type.value

                    desired_instrument_ids.add(instrument_model.id)
                    item_model = existing_items.get(instrument_model.id)

                    if item_model is None:
                        item_model = WatchlistItemModel(
                            watchlist_id=model.id,
                            instrument_id=instrument_model.id,
                        )
                        session.add(item_model)

                    item_model.state = WatchlistState(domain_item.state).value
                    item_model.notes = domain_item.notes

                for item_model in list(model.items):
                    if item_model.instrument_id not in desired_instrument_ids:
                        session.delete(item_model)

                session.commit()
            except Exception:
                session.rollback()
                raise
