import pandas as pd
import pytest

from bolsa.app.ports.errors import (
    UnsupportedUniverseError,
    UniverseFormatError,
    UniverseSourceUnavailableError,
)
from bolsa.app.ports.universe import UniverseLoadStatus
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
    )

    assert [item.ticker for item in instruments] == ["AAPL", "BRK-B"]
    assert instruments[0].name == "Apple Inc."
    assert instruments[0].exchange is None
    assert instruments[0].currency is None
    assert instruments[0].asset_type.value == "other"


def test_find_constituents_table_ignores_unrelated_tables() -> None:
    unrelated = pd.DataFrame({"Year": [2026], "Value": [1]})
    expected = pd.DataFrame({"Ticker": ["MSFT"], "Company": ["Microsoft"]})

    result = WikipediaUniverseProvider._find_constituents_table(
        [unrelated, expected],
        symbol_columns=("Ticker", "Symbol"),
        name_columns=("Company", "Security"),
    )

    assert result.equals(expected)


def test_find_constituents_table_raises_typed_format_error() -> None:
    unrelated = pd.DataFrame({"Year": [2026], "Value": [1]})

    with pytest.raises(UniverseFormatError, match="tabela"):
        WikipediaUniverseProvider._find_constituents_table(
            [unrelated],
            symbol_columns=("Ticker", "Symbol"),
            name_columns=("Company", "Security"),
        )


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


def test_read_tables_wraps_source_failure(monkeypatch) -> None:
    def fail_urlopen(*_args, **_kwargs):
        raise TimeoutError("offline")

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.wikipedia_universe_provider.urlopen",
        fail_urlopen,
    )

    with pytest.raises(UniverseSourceUnavailableError, match="fonte"):
        WikipediaUniverseProvider._read_tables("https://example.test")


def test_read_tables_wraps_parser_failure(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"<html>broken</html>"

    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.wikipedia_universe_provider.urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    monkeypatch.setattr(
        "bolsa.infrastructure.market_data.wikipedia_universe_provider.pd.read_html",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad table")),
    )

    with pytest.raises(UniverseFormatError, match="tabelas"):
        WikipediaUniverseProvider._read_tables("https://example.test")


def test_get_universe_rejects_unsupported_code() -> None:
    with pytest.raises(UnsupportedUniverseError, match="sp600"):
        WikipediaUniverseProvider().get_universe("sp600")


def test_get_universe_returns_live_result(monkeypatch) -> None:
    table = pd.DataFrame(
        {"Symbol": ["AAPL"], "Security": ["Apple Inc."]}
    )
    monkeypatch.setattr(
        WikipediaUniverseProvider,
        "_read_tables",
        classmethod(lambda cls, _url: [table]),
    )

    result = WikipediaUniverseProvider().get_universe("sp500")

    assert result.status is UniverseLoadStatus.LIVE
    assert result.universe.tickers == ("AAPL",)


def test_nasdaq_source_uses_constituents_page() -> None:
    source = WikipediaUniverseProvider._SOURCES["nasdaq100"]

    assert source["url"].endswith("List_of_NASDAQ-100_companies")
    assert source["symbol_columns"] == ("Ticker", "Symbol")
    assert source["name_columns"] == ("Company", "Security")


def test_euronext_tickers_keep_yahoo_suffixes() -> None:
    table = pd.DataFrame(
        {
            "Ticker": ["ASML.AS", "AIR.PA", "EQNR.OL"],
            "Name": ["ASML", "Airbus", "Equinor"],
            "Main listing": ["Amsterdam", "Paris", "Oslo"],
        }
    )

    instruments = WikipediaUniverseProvider._table_to_instruments(
        table,
        symbol_columns=("Ticker",),
        name_columns=("Name", "Company"),
        ticker_style="yahoo",
    )

    assert [item.ticker for item in instruments] == [
        "ASML.AS",
        "AIR.PA",
        "EQNR.OL",
    ]
    assert all(item.exchange is None for item in instruments)
    assert all(item.currency is None for item in instruments)
    assert all(item.asset_type.value == "other" for item in instruments)


def test_euronext100_is_supported() -> None:
    provider = WikipediaUniverseProvider()

    assert "euronext100" in provider.supported_universes()
