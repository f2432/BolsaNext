"""Versioned canonical financial JSON, independent of databases and brokers."""
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
import json
from uuid import UUID, uuid4

from bolsa.app.ports.portfolio import PortfolioRepository
from bolsa.domain.portfolio.codec import decode_version_fields, encode_version_fields
from bolsa.domain.portfolio.ledger import Portfolio
from bolsa.domain.portfolio.policy import encode_policy, decode_policy
from bolsa.domain.portfolio.values import (
    PortfolioError, PortfolioNotFoundError, decimal_text, financial_decimal,
)

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_VERSIONS = 20000
_MONEY_FIELDS = {
    "quantity", "price", "price_fx", "commission", "commission_fx", "gross", "gross_fx",
    "withholding", "withholding_fx", "charges", "charges_fx", "net", "net_fx", "split_factor",
}
_NULLABLE = {
    "trade_kind", "ticker", "trade_metadata", "quantity", "price", "price_currency", "price_fx",
    "commission", "commission_currency", "commission_fx", "gross", "gross_currency", "gross_fx",
    "withholding", "withholding_currency", "withholding_fx", "charges", "charges_currency", "charges_fx",
    "net", "net_currency", "net_fx", "split_factor", "adjustment_reason",
}
_REQUIRED = {"portfolio_uid", "transaction_uid", "transaction_version_uid", "version_number",
             "previous_version_uid", "recorded_at", "reason", "author"}
_SECRET_FIELDS = {"api_key", "password", "passwd", "token", "access_token", "secret", "credentials", "authorization"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PortfolioError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _encode_version(version):
    if version.trade is not None and any(
        key.strip().lower() in _SECRET_FIELDS for key, _ in version.trade.original_facts
    ):
        raise PortfolioError("Credential fields cannot be exported; review original facts explicitly")
    fields = encode_version_fields(version)
    for key, value in fields.items():
        if isinstance(value, Decimal):
            fields[key] = decimal_text(value)
    if "trade_metadata" in fields:
        fields["trade_metadata"] = json.loads(fields["trade_metadata"])
    return fields


def _decode_version(fields):
    if not isinstance(fields, dict) or not _REQUIRED <= fields.keys() or fields.keys() - (_REQUIRED | _NULLABLE):
        raise PortfolioError("Unknown or missing version fields")
    row = dict.fromkeys(_NULLABLE)
    row.update(fields)
    for key in _MONEY_FIELDS:
        if row[key] is not None:
            if not isinstance(row[key], str):
                raise PortfolioError("Financial JSON values must be decimal strings")
            row[key] = financial_decimal(row[key], scale=12 if key.endswith("_fx") else 8)
    if row["trade_metadata"] is not None:
        if not isinstance(row["trade_metadata"], dict):
            raise PortfolioError("Event metadata must be an object")
        row["trade_metadata"] = json.dumps(row["trade_metadata"], separators=(",", ":"))
    version = decode_version_fields(row)
    canonical = _encode_version(version)
    if fields.keys() != canonical.keys():
        raise PortfolioError("Financial payload fields do not match the event type")
    return version


def export_portfolio(portfolio: Portfolio) -> str:
    portfolio.reconstruct()
    if len(portfolio.versions) + len(portfolio.policies) > MAX_IMPORT_VERSIONS:
        raise PortfolioError("Export exceeds version limit; no partial history exported")
    document = {
        "format_version": 1,
        "portfolio": dict(portfolio_uid=str(portfolio.portfolio_uid), name=portfolio.name,
                          base_currency=portfolio.base_currency,
                          origin_portfolio_uid=str(portfolio.origin_portfolio_uid) if portfolio.origin_portfolio_uid else None),
        "versions": [_encode_version(v) for v in sorted(
            portfolio.versions, key=lambda v: (v.transaction_uid.hex, v.version_number)
        )],
        "policies": [encode_policy(p) for p in sorted(portfolio.policies, key=lambda p: p.version_number)],
    }
    text = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise PortfolioError("Export exceeds size limit; no partial history exported")
    return text


def parse_portfolio(text: str | bytes) -> Portfolio:
    try:
        if not isinstance(text, (str, bytes)):
            raise PortfolioError("Import must be UTF-8 JSON text")
        if len(text.encode("utf-8") if isinstance(text, str) else text) > MAX_IMPORT_BYTES:
            raise PortfolioError("Import file exceeds size limit")
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_unique_object)
        if not isinstance(document, dict) or not {"format_version", "portfolio", "versions"} <= document.keys() or (
            document.keys() - {"format_version", "portfolio", "versions", "policies"}
        ):
            raise PortfolioError("Unknown canonical document fields")
        if type(document["format_version"]) is not int or document["format_version"] != 1:
            raise PortfolioError("Unsupported portfolio format version")
        header = document["portfolio"]
        if not isinstance(header, dict) or set(header) != {"portfolio_uid", "name", "base_currency", "origin_portfolio_uid"}:
            raise PortfolioError("Invalid portfolio header")
        raw_versions = document["versions"]
        raw_policies = document.get("policies", [])
        if not isinstance(raw_versions, list) or not isinstance(raw_policies, list) or len(raw_versions) + len(raw_policies) > MAX_IMPORT_VERSIONS:
            raise PortfolioError("Import exceeds version limit or is not a version list")
        versions = tuple(_decode_version(fields) for fields in raw_versions)
        return Portfolio(
            header["name"], header["base_currency"], UUID(header["portfolio_uid"]), versions,
            UUID(header["origin_portfolio_uid"]) if header["origin_portfolio_uid"] else None,
            tuple(decode_policy(p) for p in raw_policies),
        )
    except PortfolioError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
        raise PortfolioError(f"Invalid canonical portfolio: {type(exc).__name__}") from exc


class ImportState(StrEnum):
    PREVIEW = "preview"
    COMPLETED = "completed"
    UNCHANGED = "unchanged"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ImportReport:
    state: ImportState
    planned_insertions: int = 0
    inserted: int = 0
    ignored: int = 0
    conflicts: int = 0
    rejected: int = 0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ImportPreview:
    candidate: Portfolio | None
    expected_revision: int | None
    report: ImportReport
    expected_policy_revision: int | None = None


class PortfolioTransferService:
    def __init__(self, repository: PortfolioRepository):
        self._repository = repository

    def preview(self, text: str | bytes, *, mode: str = "restore",
                destination_uid: UUID | None = None) -> ImportPreview:
        try:
            incoming = parse_portfolio(text)
            if mode not in ("restore", "complement", "clone"):
                raise PortfolioError("Unknown import mode")
            if mode == "clone":
                if destination_uid is not None:
                    raise PortfolioError("Clone must create a new independent portfolio")
                original_uid = incoming.portfolio_uid
                new_uid = uuid4()
                incoming = replace(incoming, portfolio_uid=new_uid, origin_portfolio_uid=original_uid,
                                   versions=tuple(replace(v, portfolio_uid=new_uid) for v in incoming.versions),
                                   policies=tuple(replace(p, portfolio_uid=new_uid) for p in incoming.policies))
            elif destination_uid is not None and destination_uid != incoming.portfolio_uid:
                raise PortfolioError("Destination identity conflicts with canonical portfolio")
            try:
                current = self._repository.load(incoming.portfolio_uid)
            except PortfolioNotFoundError:
                if mode == "complement":
                    raise PortfolioError("Complement requires an existing portfolio")
                current = None
            if current is None:
                return ImportPreview(incoming, None, ImportReport(
                    ImportState.PREVIEW, planned_insertions=len(incoming.versions) + len(incoming.policies)
                ))
            if (current.name, current.base_currency, current.origin_portfolio_uid) != (
                incoming.name, incoming.base_currency, incoming.origin_portfolio_uid
            ):
                return ImportPreview(None, current.ledger_revision, ImportReport(
                    ImportState.REJECTED, conflicts=1,
                    reasons=("Portfolio header conflicts with immutable persisted identity",)
                ))
            known = {v.transaction_version_uid: v for v in current.versions}
            economic_versions = {(v.transaction_uid, v.version_number): v for v in current.versions}
            added = []
            ignored = conflicts = 0
            reasons = []
            for version in incoming.versions:
                existing = known.get(version.transaction_version_uid)
                if existing == version:
                    ignored += 1
                elif existing is not None or (version.transaction_uid, version.version_number) in economic_versions:
                    conflicts += 1
                    reasons.append(f"Conflicting version identity: {version.transaction_version_uid}")
                else:
                    added.append(version)
            known_policies = {p.policy_version_uid: p for p in current.policies}
            policy_numbers = {p.version_number: p for p in current.policies}
            added_policies = []
            for policy in incoming.policies:
                existing = known_policies.get(policy.policy_version_uid)
                if existing == policy:
                    ignored += 1
                elif existing is not None or policy.version_number in policy_numbers:
                    conflicts += 1
                    reasons.append(f"Conflicting policy version: {policy.policy_version_uid}")
                else:
                    added_policies.append(policy)
            if conflicts:
                return ImportPreview(None, current.ledger_revision, ImportReport(
                    ImportState.REJECTED, ignored=ignored, conflicts=conflicts, reasons=tuple(reasons)
                ))
            candidate = replace(current, versions=current.versions + tuple(added),
                                policies=current.policies + tuple(added_policies))
            return ImportPreview(candidate, current.ledger_revision, ImportReport(
                ImportState.PREVIEW, planned_insertions=len(added) + len(added_policies), ignored=ignored
            ), current.policy_revision)
        except PortfolioError as exc:
            return ImportPreview(None, None, ImportReport(
                ImportState.REJECTED, rejected=1, reasons=(str(exc),)
            ))

    def confirm(self, preview: ImportPreview) -> ImportReport:
        if preview.candidate is None or preview.report.state is not ImportState.PREVIEW:
            return preview.report
        try:
            self._repository.import_atomic(preview.candidate, expected_revision=preview.expected_revision,
                                           expected_policy_revision=preview.expected_policy_revision)
        except PortfolioError as exc:
            return replace(preview.report, state=ImportState.REJECTED, inserted=0,
                           rejected=1, reasons=(str(exc),))
        confirmed_count = (preview.candidate.ledger_revision - (preview.expected_revision or 0) +
                           preview.candidate.policy_revision - (preview.expected_policy_revision or 0))
        return replace(preview.report, state=ImportState.COMPLETED if (
            confirmed_count or preview.expected_revision is None
        ) else ImportState.UNCHANGED, planned_insertions=confirmed_count, inserted=confirmed_count)
