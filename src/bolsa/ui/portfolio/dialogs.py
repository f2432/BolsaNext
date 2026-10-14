from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
)
from bolsa.app.portfolio_forms import form_values, form_errors, MONEY_FIELDS, utc_now
from bolsa.domain.portfolio.values import SUPPORTED_CURRENCIES

LABELS = {
    "price": "Preço unitário",
    "commission": "Comissão",
    "observed_net": "Movimento observado (+ crédito / − débito, opcional)",
    "gross": "Dividendo bruto",
    "withholding": "Retenção",
    "charges": "Outros encargos",
    "net": "Dividendo líquido",
}


class TransactionDialog(QDialog):
    def __init__(self, base_currency, previous=None, parent=None):
        super().__init__(parent)
        self.base_currency = base_currency
        self.previous = previous
        self.setWindowTitle("Corrigir operação" if previous else "Nova operação")
        self.resize(650, 680)
        layout = QVBoxLayout(self)
        instructions = QLabel(
            f"Moeda base: {base_currency}. Valores decimais sem separadores de milhares (vírgula ou ponto).\n"
            f"FX histórico = unidades de {base_currency} por 1 unidade da moeda da componente. "
            "Moedas iguais: não é necessário indicar uma taxa. Moedas diferentes: indica o câmbio efetivo histórico."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.form = QFormLayout(content)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.inputs = {}
        self.errors = {}
        self._combo("type", "Operação", [("Compra", "BUY"), ("Venda", "SELL"),
                                         ("Dividendo", "DIVIDEND"), ("Split", "ADJUSTMENT")])
        self._text("ticker", "Ticker")
        self._combo("asset_type", "Instrumento", [("Ação", "stock"), ("ETF", "etf")])
        self._combo(
            "instrument_currency", "Moeda de cotação", sorted(SUPPORTED_CURRENCIES), base_currency
        )
        self._text(
            "executed_at",
            "Execução (data ou ISO com fuso)",
            utc_now().isoformat(timespec="seconds"),
        )
        self._text("settled_on", "Liquidação (data opcional)")
        self._text("broker_sequence", "Sequência conhecida (opcional)")
        self._text("quantity", "Quantidade")
        for role in MONEY_FIELDS:
            self._text(
                role + "_amount", LABELS[role], "" if role in ("price", "observed_net") else "0"
            )
            self._combo(
                role + "_currency",
                "Moeda: " + LABELS[role],
                sorted(SUPPORTED_CURRENCIES),
                base_currency,
            )
            self._text(role + "_fx", "FX histórico: " + LABELS[role])
            self.inputs[role + "_currency"].currentTextChanged.connect(self._fx_fields)
            self.inputs[role + "_fx"].textChanged.connect(self._fx_fields)
        self._text("split_factor", "Fator do split (2 para 2:1)")
        self._text("adjustment_reason", "Motivo do split")
        self._text("source", "Origem externa (opcional)")
        self._text("account_ref", "Referência de conta (opcional)")
        self._text("external_id", "ID externo (opcional)")
        self._text("notes", "Notas")
        self._text("reason", "Motivo da correção")
        if previous is not None:
            for key, value in form_values(previous).items():
                widget = self.inputs[key]
                if isinstance(widget, QComboBox):
                    found = widget.findData(value)
                    widget.setCurrentIndex(found) if found >= 0 else widget.setCurrentText(value)
                else:
                    widget.setText(value)
        self.inputs["type"].currentTextChanged.connect(self._fields)
        self._fields()
        self._fx_fields()
        if previous:
            for key in ("source", "account_ref", "external_id"):
                self.inputs[key].setEnabled(False)
        self.form.setRowVisible(self.inputs["reason"], previous is not None)
        self.error_summary = QLabel()
        self.error_summary.setWordWrap(True)
        layout.addWidget(self.error_summary)
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                widget.editingFinished.connect(self.validate_fields)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Confirmar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        layout.addWidget(buttons)

    def _fx_fields(self, *_):
        for role in MONEY_FIELDS:
            if role + "_fx" not in self.inputs:
                continue
            original = self.inputs[role + "_currency"].currentText()
            field = self.inputs[role + "_fx"]
            same = original == self.base_currency
            field.setPlaceholderText("Não necessário (moedas iguais)" if same else
                                    f"Obrigatório: {self.base_currency} por 1 {original}")
            field.setToolTip(f"Unidades de {self.base_currency} por 1 unidade de {original}. " +
                             ("Deixa vazio ou indica 1." if same else "Usa a taxa histórica efetiva; não é obtida automaticamente."))
            # Keep every user-supplied value editable, including invalid identity
            # rates. Changing currency never clears or replaces existing input.
            field.setEnabled(not same or bool(field.text().strip()))

    def validate_fields(self):
        errors = form_errors(self.values(), self.base_currency, previous=self.previous)
        for key, label in self.errors.items():
            label.setText(errors.get(key, ""))
            self.form.setRowVisible(label, key in errors)
            self.inputs[key].setStyleSheet("border: 1px solid #b00020;" if key in errors else "")
        self.error_summary.setText(errors.get("_form", "Revê os campos assinalados antes de confirmar." if errors else ""))
        return not errors

    def accept(self):
        if self.validate_fields():
            super().accept()

    def _text(self, key, label, value=""):
        widget = QLineEdit(value)
        self.inputs[key] = widget
        self.form.addRow(label, widget)
        self._add_error(key)

    def _add_error(self, key):
        error = QLabel()
        error.setWordWrap(True)
        error.setStyleSheet("color: #b00020;")
        self.errors[key] = error
        self.form.addRow(error)
        self.form.setRowVisible(error, False)

    def _combo(self, key, label, values, current=None):
        widget = QComboBox()
        for value in values:
            if isinstance(value, tuple):
                widget.addItem(*value)
            else:
                widget.addItem(value)
        if current:
            widget.setCurrentText(current)
        self.inputs[key] = widget
        self.form.addRow(label, widget)
        self._add_error(key)

    def _fields(self, *_):
        for key, error in self.errors.items():
            self.form.setRowVisible(error, False)
            self.inputs[key].setStyleSheet("")
        kind = self.inputs["type"].currentData()
        roles = {
            "BUY": ("price", "commission", "observed_net"),
            "SELL": ("price", "commission", "observed_net"),
            "DIVIDEND": ("gross", "withholding", "charges", "net", "observed_net"),
            "ADJUSTMENT": (),
        }[kind]
        for role in MONEY_FIELDS:
            for suffix in ("_amount", "_currency", "_fx"):
                self.form.setRowVisible(self.inputs[role + suffix], role in roles)
        self.form.setRowVisible(self.inputs["quantity"], kind in ("BUY", "SELL"))
        for key in ("split_factor", "adjustment_reason"):
            self.form.setRowVisible(self.inputs[key], kind == "ADJUSTMENT")

    def values(self):
        return {
            key: (widget.currentData() or widget.currentText())
            if isinstance(widget, QComboBox)
            else widget.text()
            for key, widget in self.inputs.items()
        }
