"""Text input parsing belongs to Application, never to Qt financial code."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from bolsa.domain.instruments import Instrument, AssetType
from bolsa.domain.portfolio.models import Transaction, TransactionType, MONEY_FIELDS
from bolsa.domain.portfolio.money import Money, LedgerError


def decimal_text(text):
    value = text.strip()
    if ',' in value and '.' in value:
        raise LedgerError('Não usar separadores de milhares nos valores.')
    try:
        return Decimal(value.replace(',','.'))
    except InvalidOperation as exc:
        raise LedgerError('Número decimal inválido.') from exc


def transaction_from_form(fields, *, previous=None):
    kind = TransactionType(fields['type'])
    stamp = fields['executed_at'].strip()
    executed = datetime.fromisoformat(stamp) if 'T' in stamp or ' ' in stamp else date.fromisoformat(stamp)
    instrument = Instrument(fields['ticker'], currency=fields['instrument_currency'],
                            asset_type=AssetType(fields['asset_type']))
    kwargs = dict(instrument=instrument,type=kind,executed_at=executed,notes=fields.get('notes',''))
    if fields.get('settled_on','').strip():
        kwargs['settled_on'] = date.fromisoformat(fields['settled_on'])
    if fields.get('broker_sequence','').strip():
        kwargs['broker_sequence'] = int(fields['broker_sequence'])
    kwargs.update({key:fields.get(key,'').strip() or None for key in ('source','account_ref','external_id')})
    applicable = ('price','commission') if kind in (TransactionType.BUY,TransactionType.SELL) else (
        ('gross','withholding','charges','net') if kind == TransactionType.DIVIDEND else ())
    if kind != TransactionType.ADJUSTMENT and fields.get('observed_net_amount','').strip():
        applicable += ('observed_net',)
    for role in applicable:
        fx = fields.get(role+'_fx','').strip()
        kwargs[role] = Money(decimal_text(fields[role+'_amount']),fields[role+'_currency'],
                             decimal_text(fx) if fx else None)
    if kind in (TransactionType.BUY,TransactionType.SELL):
        kwargs['quantity'] = decimal_text(fields['quantity'])
    elif kind == TransactionType.ADJUSTMENT:
        kwargs.update(adjustment_category='SPLIT',split_factor=decimal_text(fields['split_factor']),
                      adjustment_reason=fields['adjustment_reason'])
    if previous is not None:
        kwargs.update(transaction_uid=previous.transaction_uid,order_key=previous.order_key,
                      related_transaction_uid=previous.related_transaction_uid)
    return Transaction(**kwargs)


def form_values(transaction):
    result = {key:str(getattr(transaction,key) or '') for key in
              ('ticker','instrument_currency') if hasattr(transaction,key)}
    result.update(type=transaction.type.value,ticker=transaction.instrument.ticker,
                  instrument_currency=transaction.instrument.currency or '',asset_type=transaction.instrument.asset_type.value,
                  executed_at=transaction.executed_at.isoformat(),quantity=str(transaction.quantity),notes=transaction.notes,
                  split_factor=str(transaction.split_factor) if transaction.split_factor else '',
                  adjustment_reason=transaction.adjustment_reason,source=transaction.source or '',
                  account_ref=transaction.account_ref or '',external_id=transaction.external_id or '',
                  broker_sequence=str(transaction.broker_sequence) if transaction.broker_sequence is not None else '',
                  settled_on=transaction.settled_on.isoformat() if transaction.settled_on else '')
    for role in MONEY_FIELDS:
        money = getattr(transaction,role)
        result[role+'_amount'] = str(money.amount) if money else ''
        result[role+'_currency'] = money.currency if money else ''
        result[role+'_fx'] = str(money.fx_rate) if money and money.fx_rate is not None else ''
    return result
