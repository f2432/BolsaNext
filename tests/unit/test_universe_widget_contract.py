from pathlib import Path


def test_universe_widget_keeps_instrument_objects_instead_of_rebuilding_rows() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "bolsa"
        / "ui"
        / "watchlist"
        / "universe_widget.py"
    ).read_text(encoding="utf-8")

    assert "self._loaded_instruments = universe.instruments" in source
    assert "instrument = self._loaded_instruments[row]" in source
    assert "self._table.item(row" not in source
    assert 'setHorizontalHeaderLabels(["Ticker", "Nome"])' in source
