import pandas as pd

from bolsa.infrastructure.market_data.wikipedia_universe_provider import (
    WikipediaUniverseProvider,
)


def test_table_to_instruments_normalises_us_tickers() -> None:
    table = pd.DataFrame(
        {
            "Symbol": ["AAPL", "BRK.B", "AAPL"],
            "Security": ["Apple Inc.", "Berkshire Hathaway", "Apple Inc."],
        }
    )

    instruments = WikipediaUniverseProvider._table_to_instruments(
        table,
        symbol_columns=("Symbol", "Ticker"),
        name_columns=("Security", "Company"),
        market="US",
        currency="USD",
    )

    assert [item.ticker for item in instruments] == ["AAPL", "BRK-B"]
    assert instruments[0].name == "Apple Inc."
    assert instruments[0].currency == "USD"


def test_find_constituents_table_ignores_unrelated_tables() -> None:
    unrelated = pd.DataFrame({"Year": [2026], "Value": [1]})
    expected = pd.DataFrame({"Ticker": ["MSFT"], "Company": ["Microsoft"]})

    result = WikipediaUniverseProvider._find_constituents_table(
        [unrelated, expected],
        symbol_columns=("Ticker", "Symbol"),
        name_columns=("Company", "Security"),
    )

    assert result.equals(expected)
