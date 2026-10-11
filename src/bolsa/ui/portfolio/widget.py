from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QInputDialog,
    QMessageBox,
    QFileDialog,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QTabWidget,
)

from bolsa.app.portfolio_forms import transaction_from_form, decimal_text
from bolsa.app.portfolio_presentation import amount_label, execution_label
from bolsa.app.services.portfolio_transfer_service import MAX_BYTES
from bolsa.domain.portfolio.models import utc_now
from bolsa.domain.portfolio.money import SUPPORTED_CURRENCIES
from bolsa.ui.portfolio.dialogs import TransactionDialog
from bolsa.ui.table_preferences import enable_table_header_persistence
from bolsa.ui.workers import FunctionThread


class PortfolioWidget(QWidget):
    def __init__(self, dashboard_service, default_base_currency="EUR", parent=None):
        super().__init__(parent)
        self.service = dashboard_service
        self.default_base_currency = default_base_currency
        self.dashboard = None
        self._thread = None
        self._controls = []
        self._history_page = 0
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.selector = QComboBox()
        row.addWidget(self.selector)
        self._controls.append(self.selector)
        self._button(row, "Nova carteira", self._new_portfolio)
        self._button(row, "Atualizar", self.refresh)
        self._button(row, "Valorizar", self._market)
        layout.addLayout(row)
        row = QHBoxLayout()
        self._button(row, "Nova operação", self._record)
        self._button(row, "Corrigir", self._correct)
        self._button(row, "Anular", self._void)
        self._button(row, "Exportar", self._export)
        self._button(row, "Importar / restaurar", self._import)
        self._button(row, "Política", self._policy)
        self._button(row, "Reconciliação", self._reconcile)
        layout.addLayout(row)
        self.status = QLabel("A carregar carteiras…")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        tables = QTabWidget()
        self.positions = self._table(
            [
                "Ticker",
                "Quantidade",
                "Custo base",
                "Média base",
                "PnL realizado",
                "Dividendos",
                "Mercado base",
                "PnL não realizado",
            ]
        )
        self.history = self._table(
            [
                "Execução",
                "Ticker",
                "Operação",
                "Quantidade / fator",
                "Versão",
                "Estado",
                "ID da operação",
            ]
        )
        tables.addTab(self.positions, "Posições")
        tables.addTab(self.history, "Histórico e auditoria")
        layout.addWidget(tables)
        paging = QHBoxLayout()
        self._button(paging, "Histórico anterior", lambda: self._page(-1))
        self.page_label = QLabel("")
        paging.addWidget(self.page_label)
        self._button(paging, "Histórico seguinte", lambda: self._page(1))
        layout.addLayout(paging)
        enable_table_header_persistence(self.positions, "portfolio/positions")
        enable_table_header_persistence(self.history, "portfolio/history")
        self.selector.currentIndexChanged.connect(lambda _: self.refresh())
        self.history.itemDoubleClicked.connect(lambda _: self._details())
        self.refresh()

    @property
    def busy(self):
        return self._thread is not None

    def _button(self, row, label, handler):
        button = QPushButton(label)
        button.clicked.connect(handler)
        row.addWidget(button)
        self._controls.append(button)

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        for index, label in enumerate(headers):
            table.setColumnWidth(index, max(110, len(label) * 8 + 24))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        return table

    def _run(self, task, done=None):
        if self.busy:
            return
        for control in self._controls:
            control.setEnabled(False)
        self.status.setText("A processar…")

        def execute():
            try:
                return task(), None
            except Exception as error:
                return None, error

        thread = FunctionThread(execute)
        self._thread = thread
        thread.result_ready.connect(lambda outcome: self._receive(outcome, done))
        thread.failed.connect(lambda error: self.status.setText(error))
        thread.finished.connect(self._finished)
        thread.start()

    def _receive(self, outcome, done):
        result, error = outcome
        if error is not None:
            report = getattr(error, "report", None)
            if report is not None:
                self.status.setText(
                    f"Importação rejeitada. Inseridos: 0; ignorados: {report.ignored}; "
                    f"conflitos: {len(report.conflicts)}; rejeitados: {len(report.rejected)}. {error}"
                )
            else:
                self.status.setText(str(error))
            return
        (done or self._render)(result)

    def _finished(self):
        thread = self._thread
        self._thread = None
        for control in self._controls:
            control.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

    def refresh(self):
        selected = self.selector.currentData()
        self._run(lambda: self.service.overview(selected))

    def _render(self, dashboard):
        self.dashboard = dashboard
        self.selector.blockSignals(True)
        self.selector.clear()
        for portfolio in dashboard.portfolios:
            self.selector.addItem(
                f"{portfolio.name} ({portfolio.base_currency})", portfolio.portfolio_uid
            )
        ledger = dashboard.ledger
        if ledger:
            self.selector.setCurrentIndex(self.selector.findData(ledger.portfolio.portfolio_uid))
        self.selector.blockSignals(False)
        self.positions.setRowCount(0)
        self.history.setRowCount(0)
        if ledger is None:
            self.summary.setText("Cria uma carteira para registar operações.")
            self.status.setText("Sem carteiras.")
            return
        currency = ledger.portfolio.base_currency
        reconciliation = dashboard.reconciliation
        warnings = len(reconciliation.discrepancies)
        state_label = {"consistent": "coerente", "pending": "pendente", "invalid": "inválida"}[
            reconciliation.state
        ]
        self.status.setText(
            f"Moeda base: {currency}. Revisão {ledger.revision}. Verificação: {state_label}. "
            + (f"{warnings} ocorrências para consultar." if warnings else "")
        )
        text = f"PnL realizado: {amount_label(dashboard.realized_total, currency)} {currency}. Dividendos líquidos: {amount_label(dashboard.dividends_total, currency)} {currency}."
        if reconciliation.state != "consistent":
            text += " Existem dados pendentes de reconciliação; resultados não definitivamente conciliados."
        valued = {p.ticker: p for p in dashboard.valuation.positions} if dashboard.valuation else {}
        if dashboard.valuation:
            v = dashboard.valuation
            text += (
                f" Mercado: {v.total} {currency}."
                if v.total is not None
                else f" Total de mercado indisponível. Subtotal conhecido: {v.known_subtotal} {currency}."
            )
        if dashboard.risk and dashboard.risk.alerts:
            metrics = {
                "instrument": "instrumento",
                "sector": "setor",
                "quote_currency": "moeda de cotação",
                "annualized_return": "meta anualizada",
            }
            states = {
                "within_limit": "dentro do limite",
                "exceeded": "ultrapassado",
                "not_evaluable": "não avaliável",
            }
            text += " Alertas: " + ", ".join(
                f"{metrics[a.metric]}/{a.subject}: {states[a.state]}" for a in dashboard.risk.alerts
            )
        self.summary.setText(text)
        for position in dashboard.replay.positions:
            quote = valued.get(position.ticker)
            cells = [
                position.ticker,
                position.quantity,
                amount_label(position.cost, currency),
                amount_label(position.average_cost, currency, average=True),
                amount_label(position.realized_pnl, currency),
                amount_label(position.dividends, currency),
                amount_label(quote.market_value, currency)
                if quote and quote.market_value is not None
                else "Indisponível",
                amount_label(quote.unrealized_pnl, currency)
                if quote and quote.unrealized_pnl is not None
                else "Indisponível",
            ]
            row = self.positions.rowCount()
            self.positions.insertRow(row)
            for col, value in enumerate(cells):
                item = QTableWidgetItem(str(value))
                if quote:
                    details = quote.reason
                    if quote.quote:
                        details += f" Cotação: {quote.quote.as_of}; {quote.quote.source}; {quote.quote.currency}."
                    if quote.fx:
                        details += f" FX: {quote.fx.rate}; {quote.fx.as_of}; {quote.fx.source}."
                    item.setToolTip(details)
                self.positions.setItem(row, col, item)
        self._render_history(ledger)

    def _page(self, delta):
        if self._active() is not None and not self.busy:
            self._history_page += delta
            self._render_history(self._active())

    def _render_history(self, ledger):
        heads = {}
        for version in ledger.versions:
            heads[version.transaction.transaction_uid] = version
        ordered = sorted(
            ledger.versions, key=lambda v: (v.transaction.execution_key, v.version_number)
        )
        pages = max(1, (len(ordered) + 199) // 200)
        self._history_page = max(0, min(self._history_page, pages - 1))
        self.page_label.setText(
            f"Histórico: página {self._history_page + 1} de {pages} ({len(ordered)} registos)"
        )
        self.history.setRowCount(0)
        for version in ordered[self._history_page * 200 : (self._history_page + 1) * 200]:
            tx = version.transaction
            head = heads[tx.transaction_uid]
            state = "Anulada" if head.voided else ("Eficaz" if version == head else "Substituída")
            cells = [
                execution_label(tx.executed_at),
                tx.instrument.ticker,
                tx.type.value,
                tx.split_factor if tx.split_factor is not None else tx.quantity,
                version.version_number,
                state,
                tx.transaction_uid,
            ]
            row = self.history.rowCount()
            self.history.insertRow(row)
            for col, value in enumerate(cells):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, version)
                self.history.setItem(row, col, item)

    def _active(self):
        return self.dashboard.ledger if self.dashboard and self.dashboard.ledger else None

    def _selected(self):
        item = self.history.item(self.history.currentRow(), 0)
        if item is None:
            self.status.setText("Seleciona uma operação no histórico.")
            return None
        version = item.data(Qt.ItemDataRole.UserRole)
        head = max(
            (
                v
                for v in self._active().versions
                if v.transaction.transaction_uid == version.transaction.transaction_uid
            ),
            key=lambda v: v.version_number,
        )
        if version != head or head.voided:
            self.status.setText("Só a versão eficaz pode ser corrigida ou anulada.")
            return None
        return version

    def _new_portfolio(self):
        name, ok = QInputDialog.getText(self, "Nova carteira", "Nome da carteira:")
        if not ok:
            return
        denominations = sorted(SUPPORTED_CURRENCIES)
        denomination, ok = QInputDialog.getItem(
            self,
            "Moeda base",
            "Moeda (imutável após criação):",
            denominations,
            denominations.index(self.default_base_currency)
            if self.default_base_currency in denominations
            else 0,
            False,
        )
        if ok:

            def create():
                saved = self.service.portfolio.create(name, denomination)
                return self.service.overview(saved.portfolio.portfolio_uid)

            self._run(create)

    def _transaction(self, version=None):
        ledger = self._active()
        if ledger is None:
            return
        dialog = TransactionDialog(
            ledger.portfolio.base_currency, version.transaction if version else None, self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        fields = dialog.values()

        def save():
            tx = transaction_from_form(fields, previous=version.transaction if version else None)
            if version:
                self.service.portfolio.revise(
                    ledger.portfolio.portfolio_uid,
                    tx,
                    expected_revision=ledger.revision,
                    expected_head=version.transaction_version_uid,
                    reason=fields["reason"],
                )
            else:
                self.service.portfolio.record(
                    ledger.portfolio.portfolio_uid, tx, expected_revision=ledger.revision
                )
            return self.service.overview(ledger.portfolio.portfolio_uid)

        self._run(save)

    def _record(self):
        self._transaction()

    def _correct(self):
        version = self._selected()
        if version:
            self._transaction(version)

    def _void(self):
        version = self._selected()
        ledger = self._active()
        if version is None:
            return
        reason, ok = QInputDialog.getText(
            self, "Anular operação", "Motivo (o registo original será conservado):"
        )
        if ok:

            def save():
                self.service.portfolio.void(
                    ledger.portfolio.portfolio_uid,
                    version.transaction.transaction_uid,
                    expected_revision=ledger.revision,
                    expected_head=version.transaction_version_uid,
                    reason=reason,
                )
                return self.service.overview(ledger.portfolio.portfolio_uid)

            self._run(save)

    def _market(self):
        ledger = self._active()
        if ledger:
            self._run(lambda: self.service.overview(ledger.portfolio.portfolio_uid, market=True))

    def _export(self):
        ledger = self._active()
        if ledger is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar carteira", "carteira.json", "JSON (*.json)"
        )
        if path:

            def write():
                Path(path).write_text(
                    self.service.transfer.export(ledger.portfolio.portfolio_uid), encoding="utf-8"
                )
                return self.service.overview(ledger.portfolio.portfolio_uid)

            self._run(write)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar carteira", "", "JSON (*.json)")
        if not path:
            return
        choices = [
            "Restaurar como carteira nova",
            "Importar para a carteira selecionada",
            "Criar cópia independente",
        ]
        choice, ok = QInputDialog.getItem(
            self, "Destino da importação", "Operação:", choices, 0, False
        )
        if not ok:
            return
        mode = ["restore", "complement", "clone"][choices.index(choice)]
        target = self.selector.currentData()

        def preview():
            if Path(path).stat().st_size > MAX_BYTES:
                raise ValueError("Ficheiro ultrapassa 10 MiB.")
            text = Path(path).read_text(encoding="utf-8")
            return self.service.transfer.preview(text, mode=mode, target_uid=target)

        self._run(preview, self._confirm_import)

    def _confirm_import(self, plan):
        # Queue confirmation until the preview worker has completed; no mutation yet.
        from PySide6.QtCore import QTimer

        def ask():
            if self.busy:
                QTimer.singleShot(10, ask)
                return
            p = plan.incoming.portfolio
            response = QMessageBox.question(
                self,
                "Confirmar importação",
                f"Carteira: {p.name} ({p.base_currency})\nRegistos novos: {plan.report.inserted}\n"
                f"Duplicados ignorados: {plan.report.ignored}\nConfirmar?",
            )
            if response == QMessageBox.StandardButton.Yes:

                def apply():
                    saved, report = self.service.transfer.confirm(plan)
                    return self.service.overview(saved.portfolio.portfolio_uid), report

                def complete(result):
                    self._render(result[0])
                    report = result[1]
                    self.status.setText(
                        f"Importação: {report.status}. Inseridos: {report.inserted}; ignorados: {report.ignored}."
                    )

                self._run(apply, complete)

        QTimer.singleShot(0, ask)

    def _policy(self):
        ledger = self._active()
        if ledger is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Política de investimento (opcional)")
        form = QFormLayout(dialog)
        form.addRow(QLabel("Limites entre 0 e 1; vazio = sem limite. Alertas informativos."))
        fields = {}
        previous = ledger.policies[-1] if ledger.policies else None
        labels = {
            "max_instrument_weight": "Peso máximo por instrumento",
            "max_sector_weight": "Peso máximo por setor",
            "max_currency_weight": "Peso máximo por moeda de cotação",
            "annualized_return_target": "Meta anualizada (apenas registo)",
        }
        for key, label in labels.items():
            value = getattr(previous, key) if previous else None
            fields[key] = QLineEdit(str(value) if value is not None else "")
            form.addRow(label, fields[key])
        notes = QLineEdit(previous.notes if previous else "")
        form.addRow("Notas da política", notes)
        start = QLineEdit(utc_now().isoformat(timespec="seconds"))
        form.addRow("Vigência (ISO com fuso)", start)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            parameters = {key: widget.text().strip() for key, widget in fields.items()}
            effective = start.text()
            policy_notes = notes.text()

            def save():
                from datetime import datetime

                args = {
                    key: decimal_text(value) if value else None for key, value in parameters.items()
                }
                self.service.policy.set_policy(
                    ledger.portfolio.portfolio_uid,
                    expected_revision=ledger.revision,
                    effective_from=datetime.fromisoformat(effective),
                    notes=policy_notes,
                    **args,
                )
                return self.service.overview(ledger.portfolio.portfolio_uid)

            self._run(save)

    def _reconcile(self):
        ledger = self._active()
        if ledger is None:
            return

        def show(dashboard):
            self._render(dashboard)
            report = dashboard.reconciliation
            states = {"consistent": "Coerente", "pending": "Pendente", "invalid": "Inválida"}
            QMessageBox.information(
                self,
                "Reconciliação interna",
                states[report.state]
                + "\n"
                + "\n".join(
                    f"{d.transaction_uid or 'carteira'}: {d.reason}" for d in report.discrepancies
                ),
            )

        self._run(lambda: self.service.overview(ledger.portfolio.portfolio_uid), show)

    def _details(self):
        item = self.history.item(self.history.currentRow(), 0)
        if item is None:
            return
        version = item.data(Qt.ItemDataRole.UserRole)
        tx = version.transaction
        fields = [
            f"Operação: {tx.transaction_uid}",
            f"Versão: {version.version_number}",
            f"Registo: {version.recorded_at.isoformat()}",
            f"Autor: {version.author}",
            f"Fuso de origem: {tx.execution_timezone or 'apenas data'}",
            f"Motivo: {version.reason}",
            f"Notas: {tx.notes}",
        ]
        from bolsa.domain.portfolio.models import MONEY_FIELDS

        for role in MONEY_FIELDS:
            money = getattr(tx, role)
            if money:
                fields.append(
                    f"{role}: {money.amount} {money.currency}; FX histórico: {money.fx_rate or 'identidade'}"
                )
        QMessageBox.information(self, "Detalhe e auditoria", "\n".join(fields))
