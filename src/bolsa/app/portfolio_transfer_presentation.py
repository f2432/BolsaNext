"""Read-only identities and descriptions for canonical two-phase transfers."""
from dataclasses import dataclass
from uuid import UUID

from bolsa.app.portfolio_format import ImportPreview, parse_portfolio
from bolsa.app.portfolio_presentation import import_report_text
from bolsa.domain.portfolio.values import PortfolioError

IMPORT_MODES = {
    "restore": ("Restaurar identidade do arquivo",
                "Mantém o UUID do arquivo. Cria a carteira se necessário; numa carteira compatível "
                "com o mesmo UUID acrescenta apenas versões em falta. Não substitui nem apaga histórico."),
    "complement": ("Complementar carteira selecionada",
                   "Acrescenta versões em falta à carteira selecionada. O UUID de destino deve coincidir "
                   "com o do arquivo. Duplicados são ignorados; conflitos não sobrescrevem dados."),
    "clone": ("Criar cópia independente",
              "Cria um novo UUID de carteira, preserva as versões históricas e regista a carteira do arquivo "
              "como origem. Alterações futuras ficam independentes da carteira original."),
}


@dataclass(frozen=True, slots=True)
class ImportDisplay:
    preview: ImportPreview
    mode: str
    source_uid: UUID | None = None
    source_name: str | None = None
    source_origin_uid: UUID | None = None
    destination_uid: UUID | None = None
    destination_name: str | None = None


def prepare_import_display(transfer, text, *, mode, destination=None):
    plan = transfer.preview(text, mode=mode,
                            destination_uid=destination.portfolio_uid if destination else None)
    try:
        source = parse_portfolio(text)
    except PortfolioError:
        source = None
    candidate = plan.candidate
    return ImportDisplay(plan, mode, source.portfolio_uid if source else None,
                         source.name if source else None, source.origin_portfolio_uid if source else None,
                         candidate.portfolio_uid if candidate else destination.portfolio_uid if destination else
                         source.portfolio_uid if source and mode == "restore" else None,
                         candidate.name if candidate else destination.name if destination else None)


def import_preview_text(display):
    plan = display.preview
    label, description = IMPORT_MODES[display.mode]
    return (f"Operação: {label}\n{description}\n\n"
            f"Arquivo — carteira: {display.source_name or 'Não identificada'}\n"
            f"UUID do arquivo: {display.source_uid or 'Não identificado'}\n"
            f"Origem registada no arquivo: {display.source_origin_uid or 'Sem origem registada'}\n"
            f"Destino — carteira: {display.destination_name or 'Não identificada'}\n"
            f"UUID de destino: {display.destination_uid or 'Não identificado'}\n"
            f"Versões a inserir: {plan.report.planned_insertions}\n"
            f"Duplicados a ignorar: {plan.report.ignored}\nConflitos: {plan.report.conflicts}\n"
            f"Registos rejeitados: {plan.report.rejected}\n\n" + import_report_text(plan.report))
