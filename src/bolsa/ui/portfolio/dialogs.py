from PySide6.QtWidgets import (QDialog,QFormLayout,QLineEdit,QComboBox,QDialogButtonBox,
                              QVBoxLayout,QLabel,QScrollArea,QWidget)
from bolsa.app.portfolio_forms import form_values
from bolsa.domain.portfolio.models import MONEY_FIELDS, utc_now
from bolsa.domain.portfolio.money import SUPPORTED_CURRENCIES

LABELS = {'price':'Preço unitário','commission':'Comissão','observed_net':'Líquido observado (opcional)',
          'gross':'Dividendo bruto','withholding':'Retenção','charges':'Outros encargos','net':'Dividendo líquido'}


class TransactionDialog(QDialog):
    def __init__(self,base_currency,previous=None,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Corrigir operação' if previous else 'Nova operação')
        self.resize(650,680)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Valores decimais sem separadores de milhares. FX = moeda base por unidade original.'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.form = QFormLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.inputs = {}
        self._combo('type','Operação',['BUY','SELL','DIVIDEND','ADJUSTMENT'])
        self._text('ticker','Ticker')
        self._combo('asset_type','Instrumento',[('Ação','stock'),('ETF','etf')])
        self._combo('instrument_currency','Moeda de cotação',sorted(SUPPORTED_CURRENCIES),base_currency)
        self._text('executed_at','Execução (data ou ISO com fuso)',utc_now().isoformat(timespec='seconds'))
        self._text('settled_on','Liquidação (data opcional)')
        self._text('broker_sequence','Sequência conhecida (opcional)')
        self._text('quantity','Quantidade')
        for role in MONEY_FIELDS:
            self._text(role+'_amount',LABELS[role],'' if role in ('price','observed_net') else '0')
            self._combo(role+'_currency','Moeda: '+LABELS[role],sorted(SUPPORTED_CURRENCIES),base_currency)
            self._text(role+'_fx','FX histórico: '+LABELS[role])
        self._text('split_factor','Fator do split (2 para 2:1)')
        self._text('adjustment_reason','Motivo do split')
        self._text('source','Origem externa (opcional)')
        self._text('account_ref','Referência de conta (opcional)')
        self._text('external_id','ID externo (opcional)')
        self._text('notes','Notas')
        self._text('reason','Motivo da correção')
        if previous is not None:
            for key,value in form_values(previous).items():
                widget = self.inputs[key]
                if isinstance(widget,QComboBox):
                    found = widget.findData(value)
                    widget.setCurrentIndex(found) if found >= 0 else widget.setCurrentText(value)
                else:
                    widget.setText(value)
        self.inputs['type'].currentTextChanged.connect(self._fields)
        self._fields()
        if previous:
            for key in ('source','account_ref','external_id'):
                self.inputs[key].setEnabled(False)
        self.form.setRowVisible(self.inputs['reason'],previous is not None)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _text(self,key,label,value=''):
        widget = QLineEdit(value)
        self.inputs[key] = widget
        self.form.addRow(label,widget)

    def _combo(self,key,label,values,current=None):
        widget = QComboBox()
        for value in values:
            if isinstance(value,tuple):
                widget.addItem(*value)
            else:
                widget.addItem(value)
        if current:
            widget.setCurrentText(current)
        self.inputs[key] = widget
        self.form.addRow(label,widget)

    def _fields(self,*_):
        kind = self.inputs['type'].currentText()
        roles = {'BUY':('price','commission','observed_net'),'SELL':('price','commission','observed_net'),
                 'DIVIDEND':('gross','withholding','charges','net','observed_net'),'ADJUSTMENT':()}[kind]
        for role in MONEY_FIELDS:
            for suffix in ('_amount','_currency','_fx'):
                self.form.setRowVisible(self.inputs[role+suffix],role in roles)
        self.form.setRowVisible(self.inputs['quantity'],kind in ('BUY','SELL'))
        for key in ('split_factor','adjustment_reason'):
            self.form.setRowVisible(self.inputs[key],kind == 'ADJUSTMENT')

    def values(self):
        return {key:(widget.currentData() or widget.currentText()) if isinstance(widget,QComboBox) else widget.text()
                for key,widget in self.inputs.items()}
