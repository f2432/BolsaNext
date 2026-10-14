# ruff: noqa: E402
"""Offscreen synthetic workflows adapted from feature GUI tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
import time

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QLineEdit
from PySide6.QtCore import QTimer, QCoreApplication, QEvent
from PySide6.QtTest import QTest

from bolsa.app.portfolio_forms import form_values, transaction_from_form
from bolsa.app.services.portfolio_dashboard_service import PortfolioDashboardService
from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService
from bolsa.config import AppConfig
from bolsa.domain.instruments import Instrument
from bolsa.domain.portfolio.ledger import Trade, TradeType, TransactionVersion, Portfolio
from bolsa.domain.portfolio.events import Dividend, Split
from bolsa.domain.portfolio.valuation import PriceQuote
from bolsa.domain.portfolio.values import MoneyComponent, ReportedSettlement, SignedMoneyComponent
from bolsa.infrastructure.database import ensure_database_schema, create_database_engine
from bolsa.infrastructure.repositories.portfolio_repository import SqlAlchemyPortfolioRepository
from bolsa.ui.portfolio.widget import PortfolioWidget
from bolsa.ui.portfolio.dialogs import TransactionDialog
from bolsa.ui.main_window.window import MainWindow
import bolsa.ui.portfolio.widget as gui


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def dispose_qt_widgets(app):
    yield
    # close() only hides Qt windows. Drain deferred deletion while the single
    # session QApplication is alive, before Python destroys ownership wrappers.
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@pytest.fixture
def dashboard(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    ensure_database_schema(config)
    engine = create_database_engine(config.database_url)
    repository = SqlAlchemyPortfolioRepository(engine)
    class Quotes:
        def get_quote(self, instrument):
            return PriceQuote(instrument.ticker, "EUR", Decimal("110"), datetime.now(timezone.utc), "synthetic")
    class Fx:
        def get_rate(self, *args):
            pytest.fail("Same-currency positions must not request FX")
    yield PortfolioDashboardService(repository, PortfolioValuationService(Fx()), Quotes())
    engine.dispose()


def trade():
    return Trade(Instrument("TEST", currency="EUR"), TradeType.BUY, Decimal("10"),
                 MoneyComponent(Decimal("100"), "EUR"), MoneyComponent(Decimal("0"), "EUR"),
                 date(2026, 1, 1), original_facts=(("document", "synthetic"),))


def finish(widget, app, predicate=None):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        app.processEvents()
        if not widget.busy and (predicate is None or predicate()):
            return
        QTest.qWait(5)
    pytest.fail("Portfolio worker did not finish")


def fake_dialog(monkeypatch, fields):
    class Dialog:
        def __init__(self, *args):
            pass
        def exec(self):
            return QDialog.DialogCode.Accepted
        def values(self):
            return fields
    monkeypatch.setattr(gui, "TransactionDialog", Dialog)


def test_create_record_value_export_clone(app, dashboard, monkeypatch, tmp_path):
    widget = PortfolioWidget(dashboard)
    finish(widget, app)
    assert widget._active() is None
    monkeypatch.setattr(gui.QInputDialog, "getText", lambda *a, **k: ("Synthetic", True))
    monkeypatch.setattr(gui.QInputDialog, "getItem", lambda *a, **k: ("EUR", True))
    widget._new_portfolio()
    finish(widget, app)
    original = widget._active().portfolio_uid
    fake_dialog(monkeypatch, form_values(trade()))
    widget._record()
    finish(widget, app)
    assert widget.positions.item(0, 2).text() == "1\N{NO-BREAK SPACE}000,00"
    widget._market()
    finish(widget, app)
    assert widget.dashboard.valuation.total_market_value == 1100
    assert widget.dashboard.analysis.composite_result == 100
    path = tmp_path / "synthetic.json"
    monkeypatch.setattr(gui.QFileDialog, "getSaveFileName", lambda *a: (str(path), "JSON"))
    widget._export()
    finish(widget, app)
    monkeypatch.setattr(gui.QFileDialog, "getOpenFileName", lambda *a: (str(path), "JSON"))
    monkeypatch.setattr(gui.QInputDialog, "getItem", lambda *a, **k: ("Criar cópia independente", True))
    monkeypatch.setattr(gui.QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)
    widget._import()
    finish(widget, app, lambda: widget._active().portfolio_uid != original)
    assert widget.selector.count() == 2
    assert widget._active().origin_portfolio_uid == original
    assert "Inseridos: 1" in widget.status.text()
    widget.close()


def test_correction_cancellation_and_error(app, dashboard, monkeypatch):
    p = dashboard.portfolio.create("Synthetic", "EUR")
    dashboard.portfolio.record(p.portfolio_uid, trade(), expected_revision=0)
    widget = PortfolioWidget(dashboard)
    finish(widget, app)
    widget.history.setCurrentCell(0, 0)
    fields = form_values(replace(trade(), unit_price=MoneyComponent(Decimal("101"), "EUR")))
    fields["reason"] = "Synthetic correction"
    fake_dialog(monkeypatch, fields)
    widget._correct()
    finish(widget, app)
    assert widget.positions.item(0, 2).text() == "1\N{NO-BREAK SPACE}010,00"
    assert widget._active().versions[-1].trade.original_facts == trade().original_facts
    widget.history.setCurrentCell(1, 0)
    monkeypatch.setattr(gui.QInputDialog, "getText", lambda *a, **k: ("Synthetic cancellation", True))
    widget._void()
    finish(widget, app)
    assert widget.positions.rowCount() == 0 and widget.history.rowCount() == 3
    widget.history.setCurrentCell(2, 0)
    assert widget._selected() is None
    def failure():
        raise ValueError("synthetic failure")
    widget._run(failure)
    finish(widget, app)
    assert "synthetic failure" in widget.status.text()
    widget.close()


def test_policy_form_and_reconciliation(app, dashboard):
    p = dashboard.portfolio.create("Synthetic", "EUR")
    dashboard.portfolio.record(p.portfolio_uid, trade(), expected_revision=0)
    widget = PortfolioWidget(dashboard)
    finish(widget, app)
    def approve():
        dialog = QApplication.activeModalWidget()
        fields = dialog.findChildren(QLineEdit)
        fields[0].setText(".5")
        fields[-1].setText("Synthetic limit")
        dialog.accept()
    QTimer.singleShot(0, approve)
    widget._policy()
    finish(widget, app)
    assert widget._active().policies[0].parameters.max_asset_weight == Decimal(".5")
    widget._market()
    finish(widget, app)
    assert widget.dashboard.analysis.risk.alerts[0].state == "exceeded"
    widget._reconcile()
    finish(widget, app)
    assert widget._active().ledger_revision == 1
    widget.close()


def test_form_roundtrip_signed_settlement(app):
    tx = replace(trade(), reported_settlement=ReportedSettlement(Decimal("-1000"), "EUR"))
    dialog = TransactionDialog("EUR", tx)
    assert transaction_from_form(dialog.values(), previous=tx) == tx
    assert not dialog.inputs["source"].isEnabled()
    dialog.inputs["type"].setCurrentText("DIVIDEND")
    assert dialog.form.isRowVisible(dialog.inputs["net_amount"])
    assert not dialog.form.isRowVisible(dialog.inputs["quantity"])
    dialog.close()


def test_paging_main_window_and_close_guard(app, dashboard):
    p = dashboard.portfolio.create("Synthetic", "EUR")
    versions = tuple(TransactionVersion(p.portfolio_uid, uuid4(), trade()) for _ in range(205))
    dashboard.repository.save(Portfolio(p.name, p.base_currency, p.portfolio_uid, versions), expected_revision=0)
    window = MainWindow(portfolio_dashboard_service=dashboard)
    widget = window.portfolio_widget
    finish(widget, app)
    assert widget.history.rowCount() == 200
    widget._page(1)
    assert widget.history.rowCount() == 5 and len(widget._active().versions) == 205
    assert "Portfolio" in window.statusBar().currentMessage()
    window.show()
    widget._pending_confirmation = True
    assert not window.close()
    widget._pending_confirmation = False
    assert window.close()


def test_rejected_import_never_asks_confirmation(app, dashboard, monkeypatch):
    widget = PortfolioWidget(dashboard)
    finish(widget, app)
    monkeypatch.setattr(gui.QMessageBox, "question", lambda *a: pytest.fail("Rejected preview cannot confirm"))
    widget._run(lambda: dashboard.transfer.preview(b"invalid"), widget._confirm_import)
    finish(widget, app)
    assert "Inseridos: 0" in widget.status.text()
    assert dashboard.repository.list_portfolios() == ()
    widget.close()


def test_dashboard_keeps_snapshot_when_writer_changes_during_quote(dashboard):
    p = dashboard.portfolio.create("Synthetic", "EUR")
    initial = dashboard.portfolio.record(p.portfolio_uid, trade(), expected_revision=0)
    class ConcurrentQuotes:
        def get_quote(self, instrument):
            dashboard.portfolio.record(p.portfolio_uid, trade(), expected_revision=1)
            return PriceQuote(instrument.ticker, "EUR", Decimal("110"), datetime.now(timezone.utc), "synthetic")
    dashboard._quotes = ConcurrentQuotes()
    result = dashboard.overview(p.portfolio_uid, market=True)
    assert result.portfolio == initial
    assert result.valuation.ledger_revision == result.analysis.portfolio.ledger_revision == 1
    assert result.valuation.total_market_value == 1100
    assert dashboard.repository.load(p.portfolio_uid).ledger_revision == 2


def test_gui_dividend_split_and_sell_keep_components_separate(app, dashboard, monkeypatch):
    p = dashboard.portfolio.create("Synthetic", "EUR")
    dashboard.portfolio.record(p.portfolio_uid, trade(), expected_revision=0)
    widget = PortfolioWidget(dashboard)
    finish(widget, app)
    def money(value):
        return MoneyComponent(Decimal(value), "EUR")
    dividend = Dividend(trade().instrument, money("1"), money("0"), money("2"),
                        SignedMoneyComponent(Decimal("-1"), "EUR"), date(2026, 1, 2))
    split = Split(trade().instrument, Decimal("2"), "Synthetic split", date(2026, 1, 3))
    sell = replace(trade(), kind=TradeType.SELL, quantity=Decimal("20"), executed_at=date(2026, 1, 4))
    for tx in (dividend, split, sell):
        fake_dialog(monkeypatch, form_values(tx))
        widget._record()
        finish(widget, app)
    position = widget._active().reconstruct().position("TEST")
    assert position.quantity == position.cost == 0
    assert position.dividend_income == -1 and position.realized_pnl == 1000
    assert widget.history.rowCount() == 4
    widget.close()


def test_stale_gui_revision_is_rejected_without_overwriting(app, dashboard, monkeypatch):
    p = dashboard.portfolio.create("Synthetic", "EUR")
    widget = PortfolioWidget(dashboard)
    finish(widget, app)
    dashboard.portfolio.record(p.portfolio_uid, trade(), expected_revision=0)
    fake_dialog(monkeypatch, form_values(trade()))
    widget._record()
    finish(widget, app)
    assert "entretanto alterada" in widget.status.text()
    assert dashboard.repository.load(p.portfolio_uid).ledger_revision == 1
    widget.close()
