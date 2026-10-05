from bolsa.ui.table_preferences import _settings_key


def test_table_header_settings_key_is_namespaced() -> None:
    assert _settings_key("watchlist/main") == "ui/table_headers/watchlist/main"
