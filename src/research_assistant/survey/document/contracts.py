from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


EVIDENCE_SCHEMA = "ra.scholarly_document_evidence.v1"
CONTRACT_SCHEMA = "ra.scholarly_document_contract.v1"
PLAN_SCHEMA = "ra.scholarly_document_plan.v1"
STATUS_SCHEMA = "ra.scholarly_document_status.v1"


class DocumentInputError(ValueError):
    """Raised when a document input cannot support safe planning."""


@dataclass(frozen=True, slots=True)
class DocumentContract:
    reader: str
    purpose: str
    motivation: str
    answer_target: str
    claim_boundary: str
    nonclaims: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Paper:
    paper_id: str
    title: str
    role: str
    source_status: str
    safety_status: str


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    text: str
    support_class: str
    allowed: bool
    anchor_ids: tuple[str, ...]
    paper_ids: tuple[str, ...]
    mechanism: str


@dataclass(frozen=True, slots=True)
class Anchor:
    anchor_id: str
    paper_id: str
    location: str
    permitted_use: str


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    bundle_id: str
    topic: str
    authority_class: str
    contract: DocumentContract
    papers: tuple[Paper, ...]
    claims: tuple[Claim, ...]
    anchors: tuple[Anchor, ...]
    omissions: tuple[Mapping[str, Any], ...]
    nonclaims: tuple[str, ...]


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentInputError(f"{label} must be a non-empty string")
    return value.strip()


def _strings(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise DocumentInputError(f"{label} must be a non-empty string list")
    result = tuple(_nonempty(item, f"{label} item") for item in value)
    return result


def _schema(value: Any, expected: str, label: str) -> None:
    if value != expected:
        raise DocumentInputError(f"{label} must use schema {expected}")


def load_contract(path: Path) -> DocumentContract:
    payload = _read_object(path, "document contract")
    _schema(payload.get("schema_version"), CONTRACT_SCHEMA, "document contract")
    return DocumentContract(
        reader=_nonempty(payload.get("reader"), "reader"),
        purpose=_nonempty(payload.get("purpose"), "purpose"),
        motivation=_nonempty(payload.get("motivation"), "motivation"),
        answer_target=_nonempty(payload.get("answer_target"), "answer_target"),
        claim_boundary=_nonempty(payload.get("claim_boundary"), "claim_boundary"),
        nonclaims=_strings(payload.get("nonclaims"), "nonclaims"),
    )


def load_evidence(path: Path, contract: DocumentContract) -> EvidenceBundle:
    payload = _read_object(path, "evidence bundle")
    _schema(payload.get("schema_version"), EVIDENCE_SCHEMA, "evidence bundle")
    bundle_id = _nonempty(payload.get("bundle_id"), "bundle_id")
    topic = _nonempty(payload.get("topic"), "topic")
    authority_class = _nonempty(payload.get("authority_class", "reviewed_primary"), "authority_class")
    if authority_class not in {"reviewed_primary", "source_attributed"}:
        raise DocumentInputError("authority_class must be reviewed_primary or source_attributed")
    papers_raw = payload.get("papers")
    claims_raw = payload.get("claims")
    anchors_raw = payload.get("anchors")
    if not isinstance(papers_raw, list) or not isinstance(claims_raw, list) or not isinstance(anchors_raw, list):
        raise DocumentInputError("papers, claims, and anchors must be lists")
    papers = tuple(
        Paper(
            paper_id=_nonempty(row.get("paper_id"), "paper_id"),
            title=_nonempty(row.get("title"), "paper title"),
            role=_nonempty(row.get("role"), "paper role"),
            source_status=_nonempty(row.get("source_status"), "source_status"),
            safety_status=_nonempty(row.get("safety_status"), "safety_status"),
        )
        for row in _objects(papers_raw, "papers")
    )
    anchors = tuple(
        Anchor(
            anchor_id=_nonempty(row.get("anchor_id"), "anchor_id"),
            paper_id=_nonempty(row.get("paper_id"), "anchor paper_id"),
            location=_nonempty(row.get("location"), "anchor location"),
            permitted_use=_nonempty(row.get("permitted_use"), "anchor permitted_use"),
        )
        for row in _objects(anchors_raw, "anchors")
    )
    paper_ids = {paper.paper_id for paper in papers}
    anchor_ids = {anchor.anchor_id for anchor in anchors}
    if len(paper_ids) != len(papers) or len(anchor_ids) != len(anchors):
        raise DocumentInputError("paper_id and anchor_id values must be unique")
    paper_by_id = {paper.paper_id: paper for paper in papers}
    anchor_by_id = {anchor.anchor_id: anchor for anchor in anchors}
    if any(anchor.paper_id not in paper_ids for anchor in anchors):
        raise DocumentInputError("every anchor must reference a known paper")
    claims: list[Claim] = []
    for row in _objects(claims_raw, "claims"):
        claim = Claim(
            claim_id=_nonempty(row.get("claim_id"), "claim_id"),
            text=_nonempty(row.get("text"), "claim text"),
            support_class=_nonempty(row.get("support_class"), "support_class"),
            allowed=row.get("allowed") is True,
            anchor_ids=_strings(row.get("anchor_ids"), "claim anchor_ids", allow_empty=True),
            paper_ids=_strings(row.get("paper_ids"), "claim paper_ids", allow_empty=True),
            mechanism=_nonempty(row.get("mechanism"), "claim mechanism"),
        )
        expected_support = (
            "PRIMARY_TECHNICAL_SUPPORT"
            if authority_class == "reviewed_primary"
            else "SOURCE_ATTRIBUTED_STATEMENT"
        )
        if claim.allowed and claim.support_class != expected_support:
            raise DocumentInputError(
                f"allowed claim {claim.claim_id} does not match {authority_class} support authority"
            )
        if claim.allowed and not claim.anchor_ids:
            raise DocumentInputError(f"allowed claim {claim.claim_id} has no source anchors")
        if set(claim.anchor_ids) - anchor_ids or set(claim.paper_ids) - paper_ids:
            raise DocumentInputError(f"claim {claim.claim_id} references an unknown paper or anchor")
        if claim.allowed:
            for paper_id in claim.paper_ids:
                paper = paper_by_id[paper_id]
                allowed_source_statuses = {"available"} if authority_class == "reviewed_primary" else {"inspected"}
                if paper.source_status not in allowed_source_statuses or paper.safety_status != "checked_clear":
                    raise DocumentInputError(f"claim {claim.claim_id} uses unavailable or unsafe paper {paper_id}")
            for anchor_id in claim.anchor_ids:
                anchor = anchor_by_id[anchor_id]
                expected_use = (
                    "technical_claim_support"
                    if authority_class == "reviewed_primary"
                    else "source_attributed_statement"
                )
                if anchor.paper_id not in claim.paper_ids or anchor.permitted_use != expected_use:
                    raise DocumentInputError(f"claim {claim.claim_id} uses an invalid or nontechnical anchor {anchor_id}")
        claims.append(claim)
    if not claims:
        raise DocumentInputError("evidence bundle requires at least one claim")
    if len({claim.claim_id for claim in claims}) != len(claims):
        raise DocumentInputError("claim_id values must be unique")
    nonclaims = tuple(dict.fromkeys((*contract.nonclaims, *_strings(payload.get("nonclaims", []), "nonclaims", allow_empty=True))))
    omissions = tuple(_objects(payload.get("omissions", []), "omissions"))
    return EvidenceBundle(
        bundle_id=bundle_id,
        topic=topic,
        authority_class=authority_class,
        contract=contract,
        papers=papers,
        claims=tuple(claims),
        anchors=anchors,
        omissions=omissions,
        nonclaims=nonclaims,
    )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise DocumentInputError(f"{label} must be a regular non-symlink file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DocumentInputError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DocumentInputError(f"{label} must be a JSON object")
    return payload


def _objects(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise DocumentInputError(f"{label} must be a list of objects")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
