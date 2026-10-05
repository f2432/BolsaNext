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


def test_instrument_accepts_common_yahoo_ticker_characters() -> None:
    assert Instrument("^GSPC").ticker == "^GSPC"
    assert Instrument("BRK-B").ticker == "BRK-B"
    assert Instrument("EURUSD=X").ticker == "EURUSD=X"
    assert Instrument("ASML.AS").ticker == "ASML.AS"


def test_instrument_rejects_empty_ticker() -> None:
    with pytest.raises(ValueError):
        Instrument(ticker="  ")


def test_instrument_rejects_spaces_and_unsupported_characters() -> None:
    with pytest.raises(ValueError, match="espaços"):
        Instrument(ticker="AAPL TEST")

    with pytest.raises(ValueError, match="caracteres"):
        Instrument(ticker="AAPL@")


def test_instrument_rejects_invalid_currency() -> None:
    with pytest.raises(ValueError):
        Instrument(ticker="AAPL", currency="US")
