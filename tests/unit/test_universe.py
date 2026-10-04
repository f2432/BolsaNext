from datetime import datetime, timezone

from bolsa.domain.instruments import Instrument
from bolsa.domain.universes import Universe


def test_universe_exposes_tickers() -> None:
    universe = Universe(
        code=" SP500 ",
        name=" S&P 500 ",
        instruments=(Instrument("AAPL"), Instrument("MSFT")),
        source="https://example.test",
        retrieved_at=datetime.now(timezone.utc),
    )

    assert universe.code == "sp500"
    assert universe.name == "S&P 500"
    assert universe.tickers == ("AAPL", "MSFT")
