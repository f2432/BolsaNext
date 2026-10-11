# ruff: noqa: E402
# Qt environment and availability must be checked before importing GUI modules.
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from datetime import datetime,timezone
from decimal import Decimal
import time

import pytest
QtWidgets = pytest.importorskip('PySide6.QtWidgets',exc_type=ImportError)
from PySide6.QtWidgets import QApplication,QDialog,QMessageBox
from PySide6.QtTest import QTest

from bolsa.app.services.portfolio_dashboard_service import PortfolioDashboardService
from bolsa.app.services.portfolio_valuation_service import PortfolioValuationService
from bolsa.app.portfolio_forms import form_values
from bolsa.domain.portfolio.valuation import Quote
from bolsa.ui.portfolio.widget import PortfolioWidget
from bolsa.ui.main_window.window import MainWindow
import bolsa.ui.portfolio.widget as gui


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dashboard_service(service,repository):
    class Quotes:
        def get_quote(self,instrument):
            return Quote(instrument.ticker,instrument.currency,Decimal(110),datetime.now(timezone.utc),'synthetic')
    return PortfolioDashboardService(service,PortfolioValuationService(repository,Quotes(),None))


def finish(widget,app, *, predicate=None):
    deadline = time.monotonic()+5
    while time.monotonic() < deadline:
        app.processEvents()
        if not widget.busy and (predicate is None or predicate()):
            return
        QTest.qWait(5)
    pytest.fail('Portfolio GUI worker did not finish')


def test_widget_creation_record_valuation_export_import(qt_app,dashboard_service,trade,monkeypatch,tmp_path):
    widget = PortfolioWidget(dashboard_service)
    finish(widget,qt_app)
    assert widget.dashboard.ledger is None
    monkeypatch.setattr(gui.QInputDialog,'getText',lambda *a,**k:('Synthetic',True))
    monkeypatch.setattr(gui.QInputDialog,'getItem',lambda *a,**k:('EUR',True))
    widget._new_portfolio()
    finish(widget,qt_app)
    assert widget.dashboard.ledger.portfolio.name == 'Synthetic'
    tx = trade()
    class Dialog:
        def __init__(self,*a): pass
        def exec(self): return QDialog.DialogCode.Accepted
        def values(self): return form_values(tx)
    monkeypatch.setattr(gui,'TransactionDialog',Dialog)
    widget._record()
    finish(widget,qt_app)
    assert widget.positions.rowCount() == widget.history.rowCount() == 1
    assert widget.positions.item(0,2).text() == '1000.00'
    widget._market()
    finish(widget,qt_app)
    assert widget.dashboard.valuation.total == 1100 and widget.dashboard.valuation.unrealized_pnl == 100
    path = tmp_path/'synthetic.json'
    monkeypatch.setattr(gui.QFileDialog,'getSaveFileName',lambda *a: (str(path),'JSON'))
    widget._export()
    finish(widget,qt_app)
    assert path.exists()
    plan = dashboard_service.transfer.preview(path.read_text(),mode='clone')
    monkeypatch.setattr(gui.QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Yes)
    original_uid = widget.dashboard.ledger.portfolio.portfolio_uid
    widget._confirm_import(plan)
    finish(widget,qt_app,predicate=lambda:widget.dashboard.ledger.portfolio.portfolio_uid != original_uid)
    assert widget.selector.count() == 2 and 'Importação' in widget.status.text()
    widget.close()


def test_correction_void_ui_and_source_controls(qt_app,dashboard_service,trade,monkeypatch):
    uid = dashboard_service.portfolio.create('S','EUR').portfolio.portfolio_uid
    initial = dashboard_service.portfolio.record(uid,trade(),expected_revision=0)
    widget = PortfolioWidget(dashboard_service)
    finish(widget,qt_app)
    widget.history.setCurrentCell(0,0)
    selected = widget._selected()
    assert selected == initial.versions[0]
    monkeypatch.setattr(gui.QInputDialog,'getText',lambda *a,**k:('Synthetic cancellation',True))
    widget._void()
    finish(widget,qt_app)
    assert widget.history.rowCount() == 2 and widget.positions.rowCount() == 0
    widget.history.setCurrentCell(1,0)
    assert widget._selected() is None
    widget.close()


def test_dialog_roundtrip_dynamic_fields(qt_app,trade):
    from bolsa.ui.portfolio.dialogs import TransactionDialog
    from bolsa.app.portfolio_forms import transaction_from_form
    tx = trade()
    dialog = TransactionDialog('EUR',tx)
    parsed = transaction_from_form(dialog.values(),previous=tx)
    assert parsed == tx
    assert not dialog.inputs['source'].isEnabled()
    dialog.inputs['type'].setCurrentText('DIVIDEND')
    assert dialog.form.isRowVisible(dialog.inputs['gross_amount'])
    assert not dialog.form.isRowVisible(dialog.inputs['quantity'])
    dialog.close()


def test_main_window_portfolio_tab(qt_app,dashboard_service):
    window = MainWindow(portfolio_dashboard_service=dashboard_service)
    finish(window.portfolio_widget,qt_app)
    tabs = window.centralWidget()
    assert any(tabs.tabText(i) == 'Carteira' for i in range(tabs.count()))
    assert 'Portfolio' in window.statusBar().currentMessage()
    window.close()
