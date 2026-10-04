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


def test_read_tables_uses_explicit_user_agent(monkeypatch) -> None:
    html = """
    <table>
      <tr><th>Symbol</th><th>Security</th></tr>
      <tr><td>AAPL</td><td>Apple Inc.</td></tr>
    </table>
    """

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return html.encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["user_agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.wikipedia_universe_provider.urlopen",
        fake_urlopen,
    )

    tables = WikipediaUniverseProvider._read_tables("https://example.test")

    assert captured["user_agent"] == WikipediaUniverseProvider._USER_AGENT
    assert captured["timeout"] == 20
    assert tables[0].iloc[0]["Symbol"] == "AAPL"


def test_nasdaq_source_uses_constituents_page() -> None:
    source = WikipediaUniverseProvider._SOURCES["nasdaq100"]

    assert source["url"].endswith("List_of_NASDAQ-100_companies")
    assert source["symbol_columns"] == ("Ticker", "Symbol")
    assert source["name_columns"] == ("Company", "Security")
