import pytest

from bolsa.domain.instruments import AssetType, Instrument


def test_instrument_normalises_ticker_currency_and_market() -> None:
    instrument = Instrument(
        ticker=" aapl ",
        name=" Apple Inc. ",
        market=" nasdaq ",
        currency=" usd ",
        asset_type=AssetType.STOCK,
    )

    assert instrument.ticker == "AAPL"
    assert instrument.name == "Apple Inc."
    assert instrument.market == "NASDAQ"
    assert instrument.currency == "USD"


def test_instrument_rejects_empty_ticker() -> None:
    with pytest.raises(ValueError):
        Instrument(ticker="  ")


def test_instrument_rejects_invalid_currency() -> None:
    with pytest.raises(ValueError):
        Instrument(ticker="AAPL", currency="US")
