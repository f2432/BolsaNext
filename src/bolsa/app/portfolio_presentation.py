"""Portuguese presentation only: formatted text never feeds financial inputs."""
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

UNAVAILABLE = "Indisponível"
SPACE = "\N{NO-BREAK SPACE}"
STATES = {
    "consistent": "Coerente", "discrepancy": "Discrepância",
    "information_insufficient": "Informação insuficiente",
    "preview": "Pré-visualização", "completed": "Concluída", "unchanged": "Sem alterações",
    "rejected": "Rejeitada", "available": "Disponível", "missing": "Em falta",
    "stale": "Desatualizado", "unreliable_time": "Data não fiável",
    "within_limit": "Dentro do limite", "exceeded": "Limite excedido",
    "not_evaluable": "Não avaliável",
}
METRICS = {
    "asset_concentration": "Concentração por ativo",
    "sector_concentration": "Concentração por setor",
    "quote_currency_concentration": "Concentração por moeda de cotação",
    "asset": "Concentração por ativo", "sector": "Concentração por setor",
    "quote_currency": "Concentração por moeda de cotação", "annual_return_target": "Meta anual",
    "max_asset_weight": "Concentração por ativo", "max_sector_weight": "Concentração por setor",
    "max_quote_currency_weight": "Concentração por moeda de cotação",
}
MESSAGES = {
    "Invalid canonical portfolio: JSONDecodeError": "O arquivo não contém JSON válido. Seleciona uma exportação canónica da carteira.",
    "Invalid canonical portfolio: UnicodeDecodeError": "O arquivo deve estar codificado em UTF-8.",
    "Current valuation is incomplete or does not match ledger revision":
        "A valorização está incompleta ou corresponde a outra revisão da carteira. Atualiza a valorização.",
    "Same-currency FX must equal one":
        "Quando a moeda é igual à moeda base, deixa a taxa FX vazia ou indica 1.",
    "Missing current price": "Falta a cotação atual.",
    "Missing current FX": "Falta a taxa de câmbio atual.",
    "Missing quote timestamp": "A cotação não tem uma data fiável.",
    "Quote timestamp is in the future": "A data da cotação está no futuro.",
    "Quote exceeds elapsed-time freshness limit": "A cotação ultrapassa o limite de atualidade.",
    "Historical accounting is pending settlement reconciliation":
        "A contabilidade está pendente de reconciliação da liquidação observada.",
    "Obsolete portfolio revision": "A carteira foi entretanto alterada. Atualiza-a antes de voltar a tentar.",
    "Obsolete or cancelled head": "A operação foi alterada ou anulada. Seleciona a versão eficaz atual.",
    "Obsolete policy head": "A política foi entretanto alterada. Atualiza a carteira.",
    "Obsolete policy revision": "A política foi entretanto alterada. Atualiza a carteira.",
    "Import transaction rolled back": "A importação falhou; todas as alterações foram desfeitas.",
    "Destination identity conflicts with canonical portfolio": "O UUID da carteira selecionada difere do UUID do arquivo.",
    "Complement requires an existing portfolio": "O complemento exige uma carteira já existente com o mesmo UUID.",
    "Portfolio header conflicts with immutable persisted identity": "O nome, moeda ou origem do arquivo são incompatíveis com a carteira existente.",
    "Import file exceeds size limit": "O arquivo ultrapassa o limite de 5 MiB.",
    "Confirmed observed settlement cannot be erased or changed by correction":
        "A liquidação observada confirmada deve ser preservada na correção.",
    "Execution price must be positive": "O preço de execução deve ser positivo.",
    "Execution instant must be timezone aware": "Indica o fuso horário do instante de execução.",
    "Audit instants must be timezone aware": "Indica o fuso horário do instante.",
    "Correction/cancellation requires a reason": "Indica o motivo da correção ou anulação.",
    "Only simple forward integer splits are supported": "O split exige um fator inteiro igual ou superior a 2.",
    "Incomplete source identity": "Preenche a referência de conta e o ID externo em conjunto.",
    "Negative financial value": "O valor não pode ser negativo.",
    "Financial scale exceeds supported precision": "O valor ultrapassa a precisão permitida.",
    "Invalid financial sign": "O valor deve ser positivo (ou zero nos campos que o permitem).",
    "Financial input exceeds magnitude or scale": "O valor excede a magnitude permitida ou o número de casas decimais (8; FX: 12).",
    "Financial inputs must be finite": "Indica um valor decimal finito.",
}
PREFIXES = {
    "Missing historical FX:": "Indica a taxa FX histórica (moeda base por unidade original):",
    "Oversell:": "A venda excede a quantidade disponível:",
    "Inconsistent manual dividend net:": "O líquido do dividendo não coincide com bruto menos retenção e encargos:",
    "Ambiguous execution order:": "A ordem temporal não é totalmente conhecida:",
    "Observed settlement difference pending:": "Diferença de liquidação observada pendente:",
    "Conflicting version identity:": "Conflito de identidade de versão:",
    "Conflicting policy version:": "Conflito de versão de política:",
    "Invalid canonical portfolio:": "O arquivo canónico é inválido:",
}


def number(value: Decimal | None, *, places=2, minimum=None, grouping=True):
    if value is None:
        return UNAVAILABLE
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("Presentation requires finite Decimal")
    with localcontext() as context:
        context.prec = max(50, len(value.as_tuple().digits), value.adjusted() + places + 3)
        rounded = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    if rounded == 0:
        rounded = rounded.copy_abs()
    text = format(rounded, f",.{places}f" if grouping else f".{places}f")
    if minimum is not None and places > minimum:
        whole, decimals = text.split(".")
        decimals = decimals.rstrip("0").ljust(minimum, "0")
        text = whole + ("." + decimals if decimals else "")
    return text.replace(",", SPACE).replace(".", ",")


def money(value, currency=None):
    label = number(value)
    return label + (f" {currency}" if currency and value is not None else "")


def quantity(value):
    return number(value, places=8, minimum=0)


def average_price(value):
    if value is not None and value != 0 and value.copy_abs() < Decimal("0.00000001"):
        # Scientific presentation preserves significance for tiny split-derived
        # averages without displaying dozens of zeroes or a fictitious zero.
        with localcontext() as context:
            context.prec = 4
            text = format(+value, ".3E")
        coefficient, exponent = text.split("E")
        return coefficient.replace(".", ",") + " × 10^" + str(int(exponent))
    return number(value, places=8, minimum=2)


def fx_rate(value):
    return number(value, places=12, minimum=0)


def percentage(value):
    if value is None:
        return UNAVAILABLE
    with localcontext() as context:
        context.prec = max(50, len(value.as_tuple().digits) + 3)
        percent = value * Decimal("100")
    return number(percent) + " %"


def state_label(state):
    return STATES.get(state, "Estado não reconhecido")


def message(text):
    if text is None:
        return ""
    if text in MESSAGES:
        return MESSAGES[text]
    for original, translated in MESSAGES.items():
        if original in text:
            return text.replace(original, translated)
    for prefix, translated in PREFIXES.items():
        if text.startswith(prefix):
            return translated + text[len(prefix):]
    # Details remain accessible in tooltips; don't expose unknown internal errors.
    if text and (text[0].isascii() and any(word in text for word in (
        "Invalid", "must", "requires", "Missing", "conflict", "JSON", "exceeds", "Obsolete",
    ))):
        return "Não foi possível validar os dados. Consulta o detalhe e revê os campos."
    return text


def quote_details(row):
    if row is None:
        return "Sem valorização atual."
    parts = [state_label(row.state), message(row.reason)]
    if row.price_quote:
        p = row.price_quote
        parts.append(f"Preço: {average_price(p.price)} {p.currency}; data: {p.quoted_at or 'desconhecida'}; fonte: {p.source}")
    if row.fx_quote:
        r = row.fx_quote
        parts.append(f"FX: {fx_rate(r.rate)} {r.base_currency}/{r.source_currency}; data: {r.quoted_at or 'identidade monetária'}; fonte: {r.source}")
    return "\n".join(part for part in parts if part)


def import_report_text(report):
    return (f"Importação: {state_label(report.state)}. Inseridos: {report.inserted}; "
            f"duplicados ignorados: {report.ignored}; conflitos: {report.conflicts}; "
            f"rejeições: {report.rejected}. " + " | ".join(message(r) for r in report.reasons))


def version_details(version):
    from bolsa.app.portfolio_forms import form_values, MONEY_FIELDS
    if version.trade is None:
        return "Anulação auditável; os factos financeiros permanecem nas versões anteriores."
    trade = version.trade
    fields = form_values(trade)
    parts = [f"UUID económico: {version.transaction_uid}", f"Instrumento: {trade.instrument.ticker}",
             f"Execução original: {fields['executed_at']}", f"Notas: {trade.notes or 'Sem notas'}"]
    for role in MONEY_FIELDS:
        if fields[role + "_amount"]:
            label = {"price": "Preço unitário", "commission": "Comissão", "observed_net": "Movimento observado",
                     "gross": "Bruto", "withholding": "Retenção", "charges": "Encargos", "net": "Líquido"}[role]
            parts.append(f"{label}: {fields[role + '_amount'].replace('.', ',')} {fields[role + '_currency']}; "
                         f"FX histórico: {fields[role + '_fx'].replace('.', ',') or 'não indicado (identidade monetária se moedas iguais)'}")
    if fields["quantity"]:
        parts.append("Quantidade: " + quantity(trade.quantity))
    if fields["split_factor"]:
        parts.append("Fator split: " + quantity(trade.factor))
        parts.append("Motivo split: " + trade.adjustment_reason)
    for label, value in (("Origem", trade.source), ("Referência de conta", trade.account_ref), ("ID externo", trade.external_id)):
        parts.append(f"{label}: {value or 'Não indicado'}")
    parts.extend(f"Facto original — {key}: {value}" for key, value in trade.original_facts)
    return "\n".join(parts)
