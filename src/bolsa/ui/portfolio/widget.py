"""Qt interaction only; accounting stays in Application/Domain.

Forms, two-phase transfer and paging adapted from feature 7d3e4f7.
"""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QInputDialog, QDialog, QFileDialog,
    QMessageBox, QFormLayout, QLineEdit, QDialogButtonBox,
)

from bolsa.app.portfolio_forms import transaction_from_form, decimal_text, utc_now
from bolsa.app.portfolio_format import export_portfolio, MAX_IMPORT_BYTES
from bolsa.app.portfolio_presentation import (
    money, quantity, average_price, percentage, state_label, message, quote_details,
    import_report_text, METRICS,
)
from bolsa.domain.portfolio.policy import PolicyParameters
from bolsa.domain.portfolio.values import SUPPORTED_CURRENCIES
from bolsa.ui.portfolio.dialogs import TransactionDialog
from bolsa.ui.workers import FunctionThread


class PortfolioWidget(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.dashboard = None
        self._worker = None
        self._page_number = 0
        self._pending_confirmation = False
        layout = QVBoxLayout(self)
        self.selector = QComboBox()
        self.selector.currentIndexChanged.connect(self._select)
        layout.addWidget(self.selector)
        bar = QHBoxLayout()
        self._buttons = []
        for label, callback in (
            ("Nova carteira", self._new_portfolio), ("Registar", self._record),
            ("Corrigir", self._correct), ("Anular", self._void),
            ("Valorizar", self._market), ("Exportar", self._export),
            ("Importar", self._import), ("Política", self._policy),
            ("Reconciliar", self._reconcile), ("Detalhe", self._details),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
            self._buttons.append(button)
        layout.addLayout(bar)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.positions = self._table(["Ticker", "Quantidade", "Custo", "Custo médio", "Realizado",
                                      "Dividendos", "Mercado", "Não realizado", "Estado contabilístico"])
        layout.addWidget(self.positions)
        self.history = self._table(["Execução", "Ticker", "Tipo", "Versão", "Estado", "UUID económico"])
        layout.addWidget(self.history)
        pager = QHBoxLayout()
        self.page_label = QLabel()
        pager.addWidget(self.page_label)
        for label, step in (("Anterior", -1), ("Seguinte", 1)):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, delta=step: self._page(delta))
            pager.addWidget(button)
        layout.addLayout(pager)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self._run(self.service.overview)

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return table

    @property
    def busy(self):
        return self._worker is not None or self._pending_confirmation

    def _run(self, function, callback=None):
        if self.busy:
            return
        self.status.setText("A processar…")
        self.selector.setEnabled(False)
        for button in self._buttons:
            button.setEnabled(False)
        self._worker = FunctionThread(function)
        self._worker.setParent(self)
        self._worker.result_ready.connect(callback or self._render)
        self._worker.failed.connect(self._show_error)
        self._worker.finished.connect(self._finished)
        self._worker.start()

    def _show_error(self, error):
        self.status.setText("Erro; operação não confirmada: " + message(error))
        self.status.setToolTip(error)

    def _finished(self):
        self._worker.deleteLater()
        self._worker = None
        self.selector.setEnabled(True)
        for button in self._buttons:
            button.setEnabled(True)

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)

    def _active(self):
        return self.dashboard.portfolio if self.dashboard else None

    def _select(self, *_):
        if not self.busy:
            self._page_number = 0
            uid = self.selector.currentData()
            self._run(lambda: self.service.overview(uid))

    @staticmethod
    def _row(table, cells, version=None, tooltip=""):
        row = table.rowCount()
        table.insertRow(row)
        for column, value in enumerate(cells):
            item = QTableWidgetItem("Indisponível" if value is None else str(value))
            item.setData(Qt.ItemDataRole.UserRole, version)
            item.setToolTip(tooltip)
            table.setItem(row, column, item)

    def _render(self, dashboard):
        self.dashboard = dashboard
        self.selector.blockSignals(True)
        self.selector.clear()
        for p in dashboard.portfolios:
            self.selector.addItem(f"{p.name} ({p.base_currency}) · {str(p.portfolio_uid)[:8]}", p.portfolio_uid)
        if dashboard.portfolio:
            self.selector.setCurrentIndex(self.selector.findData(dashboard.portfolio.portfolio_uid))
        self.selector.blockSignals(False)
        self.positions.setRowCount(0)
        self.history.setRowCount(0)
        portfolio = self._active()
        if portfolio is None:
            self.summary.setText("Sem carteiras. Cria uma carteira ou importa um arquivo canónico.")
            self.status.setText("")
            return
        valuation, analysis = dashboard.valuation, dashboard.analysis
        self.summary.setText(
            f"Moeda base: {portfolio.base_currency}. Mercado total: {money(valuation.total_market_value, portfolio.base_currency)}; "
            f"subtotal conhecido: {money(valuation.known_market_subtotal, portfolio.base_currency)}. "
            f"Resultado composto: {money(analysis.composite_result, portfolio.base_currency)}. "
            f"Reconciliação: {state_label(analysis.reconciliation.state)}. "
            "Cotações diárias aproximadas; limite de atualidade de 72 horas corridas.\n"
            + " | ".join(f"{METRICS.get(a.metric, 'Política')}: {state_label(a.state)} "
                         f"(atual: {percentage(a.actual)}; limite: {percentage(a.limit)})"
                         for a in analysis.risk.alerts)
        )
        valued = {p.ticker: p for p in valuation.positions}
        for position in portfolio.reconstruct().positions:
            current = valued.get(position.ticker)
            tooltip = quote_details(current)
            self._row(self.positions, [position.ticker, quantity(position.quantity), money(position.cost),
                      average_price(position.average_cost), money(position.realized_pnl), money(position.dividend_income),
                      money(current.market_value) if current else None, money(current.unrealized_pnl) if current else None,
                      "Confirmado" if position.accounting_confirmed else "Provisório / pendente"], tooltip=tooltip)
            for column, value in enumerate((position.quantity, position.cost, position.average_cost,
                                           position.realized_pnl, position.dividend_income), 1):
                self.positions.item(self.positions.rowCount() - 1, column).setToolTip(
                    tooltip + f"\nValor exato registado/derivado: {value}"
                )
        self._render_history()
        details = valuation.data_errors + analysis.reconciliation.issues + portfolio.reconstruct().warnings
        self.status.setText(" | ".join(message(text) for text in details))
        self.status.setToolTip("\n".join(details))

    def _render_history(self):
        portfolio = self._active()
        if portfolio is None:
            return
        heads = {}
        for version in sorted(portfolio.versions, key=lambda v: v.version_number):
            heads[version.transaction_uid] = version
        ordered = sorted(portfolio.versions, key=lambda v: (v.recorded_at, v.transaction_version_uid.hex))
        pages = max(1, (len(ordered) + 199) // 200)
        self._page_number = max(0, min(self._page_number, pages - 1))
        self.page_label.setText(f"Histórico: página {self._page_number + 1} de {pages} ({len(ordered)} versões)")
        self.history.setRowCount(0)
        for version in ordered[self._page_number * 200:(self._page_number + 1) * 200]:
            head = heads[version.transaction_uid]
            trade = version.trade
            state = "Anulada" if head.trade is None else "Eficaz" if head == version else "Substituída"
            self._row(self.history, [trade.executed_at.isoformat() if trade else "—",
                      trade.instrument.ticker if trade else "—",
                      transaction_from_kind(trade), version.version_number, state, version.transaction_uid], version)

    def _page(self, delta):
        self._page_number += delta
        self._render_history()

    def _selected(self):
        item = self.history.item(self.history.currentRow(), 0)
        if item is None or self._active() is None:
            return None
        version = item.data(Qt.ItemDataRole.UserRole)
        head = max((v for v in self._active().versions if v.transaction_uid == version.transaction_uid),
                   key=lambda v: v.version_number)
        if head != version or head.trade is None:
            self.status.setText("Só a versão eficaz pode ser corrigida ou anulada.")
            return None
        return version

    def _new_portfolio(self):
        name, ok = QInputDialog.getText(self, "Nova carteira", "Nome:")
        if not ok:
            return
        currencies = sorted(SUPPORTED_CURRENCIES)
        currency, ok = QInputDialog.getItem(self, "Moeda base", "Moeda imutável:", currencies,
                                           currencies.index("EUR"), False)
        if ok:
            self._run(lambda: self.service.overview(self.service.portfolio.create(name, currency).portfolio_uid))

    def _transaction(self, version=None):
        portfolio = self._active()
        if portfolio is None:
            return
        dialog = TransactionDialog(portfolio.base_currency, version.trade if version else None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        fields = dialog.values()

        def save():
            trade = transaction_from_form(fields, previous=version.trade if version else None)
            if version:
                self.service.portfolio.revise(portfolio.portfolio_uid, version.transaction_uid,
                    version.transaction_version_uid, trade, reason=fields["reason"],
                    expected_revision=portfolio.ledger_revision)
            else:
                self.service.portfolio.record(portfolio.portfolio_uid, trade,
                                              expected_revision=portfolio.ledger_revision)
            return self.service.overview(portfolio.portfolio_uid)
        self._run(save)

    def _record(self):
        self._transaction()

    def _correct(self):
        version = self._selected()
        if version:
            self._transaction(version)

    def _void(self):
        version, portfolio = self._selected(), self._active()
        if version is None:
            return
        reason, ok = QInputDialog.getText(self, "Anular", "Motivo (histórico preservado):")
        if ok:
            def save():
                self.service.portfolio.revise(portfolio.portfolio_uid, version.transaction_uid,
                    version.transaction_version_uid, None, reason=reason, expected_revision=portfolio.ledger_revision)
                return self.service.overview(portfolio.portfolio_uid)
            self._run(save)

    def _market(self):
        if self._active():
            uid = self._active().portfolio_uid
            self._run(lambda: self.service.overview(uid, market=True))

    def _export(self):
        if self._active() is None:
            return
        portfolio = self._active()
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", "carteira.json", "JSON (*.json)")
        if path:
            def write():
                text = export_portfolio(self.service.portfolio.load(portfolio.portfolio_uid))
                Path(path).write_text(text, encoding="utf-8")
                return self.service.overview(portfolio.portfolio_uid)
            self._run(write)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar", "", "JSON (*.json)")
        if not path:
            return
        choices = ["Restaurar", "Complementar carteira selecionada", "Criar cópia independente"]
        choice, ok = QInputDialog.getItem(self, "Importar", "Destino:", choices, 0, False)
        if not ok:
            return
        mode = ("restore", "complement", "clone")[choices.index(choice)]
        destination = self.selector.currentData() if mode == "complement" else None
        def preview():
            with Path(path).open("rb") as stream:
                text = stream.read(MAX_IMPORT_BYTES + 1)
            return self.service.transfer.preview(text, mode=mode, destination_uid=destination)
        self._run(preview, self._confirm_import)

    def _confirm_import(self, plan):
        self._pending_confirmation = True
        def ask():
            if self._worker is not None:
                QTimer.singleShot(10, ask)
                return
            self._pending_confirmation = False
            if plan.candidate is None:
                self.status.setText(import_report_text(plan.report))
                return
            candidate = plan.candidate
            response = QMessageBox.question(self, "Confirmar importação",
                f"{candidate.name} ({candidate.base_currency}) · {candidate.portfolio_uid}\n"
                f"Versões previstas: {plan.report.planned_insertions}; ignoradas: {plan.report.ignored}. Confirmar?")
            if response == QMessageBox.StandardButton.Yes:
                def apply():
                    report = self.service.transfer.confirm(plan)
                    return self.service.overview(candidate.portfolio_uid), report
                def complete(result):
                    self._render(result[0])
                    report = result[1]
                    self.status.setText(import_report_text(report))
                self._run(apply, complete)
        QTimer.singleShot(0, ask)

    def _policy(self):
        portfolio = self._active()
        if portfolio is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Política opcional — alertas informativos")
        form = QFormLayout(dialog)
        fields = {}
        previous = portfolio.policies[-1] if portfolio.policies else None
        for key, label in (("max_asset_weight", "Peso máximo ativo [0,1]"),
                           ("max_sector_weight", "Peso máximo setor [0,1]"),
                           ("max_quote_currency_weight", "Peso máximo moeda cotação [0,1]"),
                           ("annual_return_target", "Meta anual (apenas registo)")):
            value = getattr(previous.parameters, key) if previous else None
            fields[key] = QLineEdit(str(value) if value is not None else "")
            form.addRow(label, fields[key])
        effective, reason = QLineEdit(utc_now().isoformat()), QLineEdit()
        form.addRow("Vigência ISO com fuso", effective)
        form.addRow("Motivo obrigatório", reason)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            parameters = {key: field.text() for key, field in fields.items()}
            stamp, motivation = effective.text(), reason.text()
            def save():
                policy = PolicyParameters(**{key: decimal_text(value) if value.strip() else None
                                             for key, value in parameters.items()})
                self.service.portfolio.change_policy(portfolio.portfolio_uid, policy,
                    expected_head=previous.policy_version_uid if previous else None,
                    effective_at=datetime.fromisoformat(stamp), reason=motivation)
                return self.service.overview(portfolio.portfolio_uid)
            self._run(save)

    def _reconcile(self):
        if self._active():
            uid = self._active().portfolio_uid
            self._run(lambda: self.service.overview(uid))

    def _details(self):
        item = self.history.item(self.history.currentRow(), 0)
        if item:
            version = item.data(Qt.ItemDataRole.UserRole)
            QMessageBox.information(self, "Auditoria", f"UUID versão: {version.transaction_version_uid}\n"
                f"Registo: {version.recorded_at.isoformat()}\nAutor: {version.author}\nMotivo: {version.reason}\n"
                f"Factos completos: {version.trade}")


def transaction_from_kind(trade):
    if trade is None:
        return "ANULAÇÃO"
    return trade.kind.value if hasattr(trade, "kind") else "DIVIDEND" if hasattr(trade, "gross") else "SPLIT"
