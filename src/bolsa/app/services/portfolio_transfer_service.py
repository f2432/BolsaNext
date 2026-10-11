import json
from dataclasses import asdict, dataclass, replace

from bolsa.app.portfolio_codec import version_dict, version_from
from bolsa.app.policy_codec import policy_dict, policy_from
from bolsa.domain.portfolio.policy import validate_policies
from bolsa.domain.portfolio.importing import ImportReport, ImportRejected, merge_ledger
from bolsa.domain.portfolio.models import Ledger, Portfolio, uid
from bolsa.domain.portfolio.ledger import replay

FORMAT_VERSION = 2
MAX_BYTES = 10 * 1024 * 1024
MAX_VERSIONS = 100000


@dataclass(frozen=True, slots=True)
class ImportPlan:
    incoming: Ledger
    expected_revision: int | None
    report: ImportReport
    mode: str


def export_json(ledger: Ledger) -> str:
    replay(ledger)
    data = {
        "format": "BolsaNextPortfolio",
        "format_version": FORMAT_VERSION,
        "portfolio": asdict(ledger.portfolio),
        "versions": [version_dict(v) for v in ledger.versions],
        "policies": [policy_dict(p) for p in ledger.policies],
    }
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Campo JSON repetido: {key}")
        result[key] = value
    return result


def parse_json(text: str) -> Ledger:
    try:
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Ficheiro ultrapassa 10 MiB.")
        data = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Número JSON inválido.")),
        )
        expected_fields = {"format", "format_version", "portfolio", "versions"}
        if data.get("format_version") == 2:
            expected_fields.add("policies")
        if set(data) != expected_fields:
            raise ValueError("Campos de topo não suportados.")
        if (
            data["format"] != "BolsaNextPortfolio"
            or type(data["format_version"]) is not int
            or data["format_version"] not in (1, FORMAT_VERSION)
        ):
            raise ValueError("Formato/versão não suportados.")
        if type(data["versions"]) is not list or len(data["versions"]) > MAX_VERSIONS:
            raise ValueError("Lista de versões inválida ou demasiado grande.")
        policy_versions = tuple(policy_from(p) for p in data.get("policies", []))
        validate_policies(policy_versions)
        ledger = Ledger(
            Portfolio(**data["portfolio"]),
            tuple(version_from(v) for v in data["versions"]),
            policies=policy_versions,
        )
        replay(ledger)
        return ledger
    except Exception as exc:
        raise ImportRejected(ImportReport(rejected=(f"JSON inválido: {exc}",))) from exc


class PortfolioTransferService:
    def __init__(self, repository):
        self.repository = repository

    def export(self, portfolio_uid):
        return export_json(self.repository.load(portfolio_uid))

    def preview(self, text: str, *, mode: str, target_uid: str | None = None) -> ImportPlan:
        incoming = parse_json(text)
        if mode == "clone":
            incoming = replace(
                incoming,
                portfolio=replace(
                    incoming.portfolio,
                    portfolio_uid=uid(),
                    origin_portfolio_uid=incoming.portfolio.portfolio_uid,
                ),
            )
        elif mode == "complement":
            if target_uid != incoming.portfolio.portfolio_uid:
                raise ImportRejected(
                    ImportReport(conflicts=("Destino não corresponde à identidade exportada.",))
                )
        elif mode != "restore":
            raise ImportRejected(
                ImportReport(rejected=("Modo não suportado; substituição destrutiva excluída.",))
            )
        portfolios = {p.portfolio_uid: p for p in self.repository.list_portfolios()}
        target = portfolios.get(incoming.portfolio.portfolio_uid)
        if target is not None:
            if mode != "complement":
                raise ImportRejected(
                    ImportReport(
                        conflicts=("UUID já existe; escolher importação complementar ou clone.",)
                    )
                )
            existing = self.repository.load(target.portfolio_uid)
            revision = existing.revision
        else:
            if mode == "complement":
                raise ImportRejected(ImportReport(rejected=("Carteira de destino inexistente.",)))
            existing, revision = Ledger(incoming.portfolio), None
        _, report = merge_ledger(existing, incoming)
        return ImportPlan(incoming, revision, report, mode)

    def confirm(self, plan: ImportPlan):
        # Adapter must repeat validation against the live revision under one transaction.
        return self.repository.import_ledger(
            plan.incoming, expected_revision=plan.expected_revision
        )
