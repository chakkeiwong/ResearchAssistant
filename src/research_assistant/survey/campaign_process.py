"""Source-first planning primitives for literature survey campaigns.

The existing survey workflow owns durable mission state and review ledgers.
This module owns the smaller domain model used to decide what should happen
next.  It has no network, credential, PDF, or human-review side effects.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.source_selection import choose_preferred_source_version


CAMPAIGN_PROCESS_SCHEMA = "ra-survey-campaign-process-v2"
PROCESS_PLAN_SCHEMA = "ra-survey-process-plan-v2"
PAPER_STATES = (
    "DISCOVERED",
    "IDENTITY_RESOLVED",
    "SOURCE_RESOLVED",
    "ACQUIRED",
    "SAFETY_CHECKED",
    "INSPECTED",
    "CLAIM_MAPPED",
)
BLOCKED_PAPER_STATES = {"SOURCE_BLOCKED", "QUARANTINED", "OMITTED"}
_STATE_RANK = {state: index for index, state in enumerate(PAPER_STATES)}
_SUPPORTED_CLAIM_CLASSES = {
    "primary_technical_support",
    "project_derivation",
    "implementation_evidence",
}
_SUPPORTED_CLAIM_STATUSES = {"supported", "blocked", "rejected"}
_INSPECTION_STATUSES = {"not_started", "blocked", "inspected"}
_RISK_STATUSES = {"open", "partially_closed", "accepted", "closed"}


@dataclass(frozen=True, slots=True)
class PaperRecord:
    paper_id: str
    title: str
    state: str
    coverage_cells: tuple[str, ...]
    roles: tuple[str, ...]
    selected: bool
    source_required: bool
    citation_count: int | None


@dataclass(frozen=True, slots=True)
class SourceVersionRecord:
    source_id: str
    paper_id: str
    source_identifier: str
    version_relation: str
    version_date: str | None
    publication_date: str | None
    available: bool
    lawful: bool
    quarantined: bool
    metadata_conflict: bool


@dataclass(frozen=True, slots=True)
class InspectionRecord:
    inspection_id: str
    paper_id: str
    status: str
    technical_anchors: tuple[str, ...]
    inspected_sections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    claim_id: str
    paper_id: str
    support_class: str
    status: str
    source_sections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CitationRelation:
    relation_id: str
    citing_paper_id: str
    cited_paper_id: str
    direction: str


@dataclass(frozen=True, slots=True)
class OmissionRisk:
    risk_id: str
    paper_id: str | None
    category: str
    severity: str
    status: str
    must_cite: bool
    next_action: str


@dataclass(frozen=True, slots=True)
class SelectionSummary:
    selected_count: int
    retained_count: int
    substitution_count: int
    unreplaced_count: int


@dataclass(frozen=True, slots=True)
class CampaignSnapshot:
    topic: str
    coverage_requirements: tuple[CoverageRequirement, ...]
    papers: tuple[PaperRecord, ...]
    source_versions: tuple[SourceVersionRecord, ...]
    inspections: tuple[InspectionRecord, ...]
    claims: tuple[ClaimRecord, ...]
    citation_relations: tuple[CitationRelation, ...]
    omission_risks: tuple[OmissionRisk, ...]
    selection_summary: SelectionSummary

    @property
    def schema_version(self) -> str:
        return CAMPAIGN_PROCESS_SCHEMA

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "topic": self.topic,
            "coverage_requirements": [_asdict(row) for row in self.coverage_requirements],
            "papers": [_asdict(row) for row in self.papers],
            "source_versions": [_asdict(row) for row in self.source_versions],
            "inspections": [_asdict(row) for row in self.inspections],
            "claims": [_asdict(row) for row in self.claims],
            "citation_relations": [_asdict(row) for row in self.citation_relations],
            "omission_risks": [_asdict(row) for row in self.omission_risks],
            "selection_summary": _asdict(self.selection_summary),
        }


@dataclass(frozen=True, slots=True)
class CoverageRequirement:
    cell_id: str
    label: str
    priority: int
    direct_evidence_required: bool


def _asdict(value: Any) -> dict[str, Any]:
    result = asdict(value)
    for key, item in result.items():
        if isinstance(item, tuple):
            result[key] = list(item)
    return result


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise MissionStateError("invalid_campaign_record", f"{field} must be non-empty text")
    return " ".join(value.split())


def _text_list(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_campaign_record", f"{field} must be a list")
    values = tuple(sorted({_text(item, f"{field}[]").casefold() for item in value}))
    if not allow_empty and not values:
        raise MissionStateError("invalid_campaign_record", f"{field} must not be empty")
    return values


def _optional_date(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = _text(value, field)
    try:
        date.fromisoformat(text[:10])
    except ValueError as exc:
        raise MissionStateError("invalid_campaign_record", f"{field} must be ISO date") from exc
    return text


def _exact(row: Any, keys: set[str], field: str) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) != keys:
        raise MissionStateError("invalid_campaign_record", f"{field} fields are not exact")
    return row


def _coverage_requirement(row: Any) -> CoverageRequirement:
    value = _exact(
        row,
        {"cell_id", "label", "priority", "direct_evidence_required"},
        "coverage_requirement",
    )
    priority = value["priority"]
    if type(priority) is not int or priority <= 0:
        raise MissionStateError(
            "invalid_campaign_record",
            "coverage_requirement.priority must be a positive integer",
        )
    if type(value["direct_evidence_required"]) is not bool:
        raise MissionStateError(
            "invalid_campaign_record",
            "coverage_requirement.direct_evidence_required must be boolean",
        )
    return CoverageRequirement(
        cell_id=_text(value["cell_id"], "coverage_requirement.cell_id").casefold(),
        label=_text(value["label"], "coverage_requirement.label"),
        priority=priority,
        direct_evidence_required=value["direct_evidence_required"],
    )


def _paper(row: Any, coverage_ids: set[str]) -> PaperRecord:
    value = _exact(row, {"paper_id", "title", "state", "coverage_cells", "roles", "selected", "source_required", "citation_count"}, "paper")
    paper_id = _text(value["paper_id"], "paper.paper_id").casefold()
    state = _text(value["state"], "paper.state")
    if state not in {*PAPER_STATES, *BLOCKED_PAPER_STATES}:
        raise MissionStateError("invalid_campaign_record", f"unknown paper state: {state}")
    coverage_cells = _text_list(value["coverage_cells"], "paper.coverage_cells")
    unknown_cells = set(coverage_cells) - coverage_ids
    if unknown_cells:
        raise MissionStateError("invalid_campaign_record", f"unknown coverage cells: {sorted(unknown_cells)}")
    if type(value["selected"]) is not bool or type(value["source_required"]) is not bool:
        raise MissionStateError("invalid_campaign_record", "paper boolean fields are invalid")
    citation = value["citation_count"]
    if citation is not None and (type(citation) is not int or citation < 0):
        raise MissionStateError("invalid_campaign_record", "paper citation_count is invalid")
    return PaperRecord(
        paper_id=paper_id,
        title=_text(value["title"], "paper.title"),
        state=state,
        coverage_cells=coverage_cells,
        roles=_text_list(value["roles"], "paper.roles"),
        selected=value["selected"],
        source_required=value["source_required"],
        citation_count=citation,
    )


def _source_version(row: Any) -> SourceVersionRecord:
    value = _exact(row, {"source_id", "paper_id", "source_identifier", "version_relation", "version_date", "publication_date", "available", "lawful", "quarantined", "metadata_conflict"}, "source_version")
    flags = ("available", "lawful", "quarantined", "metadata_conflict")
    if any(type(value[key]) is not bool for key in flags):
        raise MissionStateError("invalid_campaign_record", "source version boolean fields are invalid")
    return SourceVersionRecord(
        source_id=_text(value["source_id"], "source_version.source_id").casefold(),
        paper_id=_text(value["paper_id"], "source_version.paper_id").casefold(),
        source_identifier=_text(value["source_identifier"], "source_version.source_identifier"),
        version_relation=_text(value["version_relation"], "source_version.version_relation").casefold(),
        version_date=_optional_date(value["version_date"], "source_version.version_date"),
        publication_date=_optional_date(value["publication_date"], "source_version.publication_date"),
        available=value["available"], lawful=value["lawful"],
        quarantined=value["quarantined"], metadata_conflict=value["metadata_conflict"],
    )


def _inspection(row: Any) -> InspectionRecord:
    value = _exact(row, {"inspection_id", "paper_id", "status", "technical_anchors", "inspected_sections"}, "inspection")
    status = _text(value["status"], "inspection.status").casefold()
    if status not in _INSPECTION_STATUSES:
        raise MissionStateError("invalid_campaign_record", f"unknown inspection status: {status}")
    return InspectionRecord(
        inspection_id=_text(value["inspection_id"], "inspection.inspection_id").casefold(),
        paper_id=_text(value["paper_id"], "inspection.paper_id").casefold(),
        status=status,
        technical_anchors=_text_list(value["technical_anchors"], "inspection.technical_anchors"),
        inspected_sections=_text_list(value["inspected_sections"], "inspection.inspected_sections"),
    )


def _claim(row: Any) -> ClaimRecord:
    value = _exact(row, {"claim_id", "paper_id", "support_class", "status", "source_sections"}, "claim")
    support_class = _text(value["support_class"], "claim.support_class").casefold()
    status = _text(value["status"], "claim.status").casefold()
    if support_class not in _SUPPORTED_CLAIM_CLASSES or status not in _SUPPORTED_CLAIM_STATUSES:
        raise MissionStateError("invalid_campaign_record", "claim support class or status is invalid")
    return ClaimRecord(
        claim_id=_text(value["claim_id"], "claim.claim_id").casefold(),
        paper_id=_text(value["paper_id"], "claim.paper_id").casefold(),
        support_class=support_class, status=status,
        source_sections=_text_list(value["source_sections"], "claim.source_sections"),
    )


def _relation(row: Any) -> CitationRelation:
    value = _exact(row, {"relation_id", "citing_paper_id", "cited_paper_id", "direction"}, "citation_relation")
    direction = _text(value["direction"], "citation_relation.direction").casefold()
    if direction not in {"backward", "forward"}:
        raise MissionStateError("invalid_campaign_record", "citation relation direction is invalid")
    return CitationRelation(
        relation_id=_text(value["relation_id"], "citation_relation.relation_id").casefold(),
        citing_paper_id=_text(value["citing_paper_id"], "citation_relation.citing_paper_id").casefold(),
        cited_paper_id=_text(value["cited_paper_id"], "citation_relation.cited_paper_id").casefold(),
        direction=direction,
    )


def _risk(row: Any) -> OmissionRisk:
    value = _exact(row, {"risk_id", "paper_id", "category", "severity", "status", "must_cite", "next_action"}, "omission_risk")
    severity = _text(value["severity"], "omission_risk.severity").casefold()
    status = _text(value["status"], "omission_risk.status").casefold()
    if severity not in {"informational", "low", "high", "critical"} or status not in _RISK_STATUSES:
        raise MissionStateError("invalid_campaign_record", "omission risk severity or status is invalid")
    if type(value["must_cite"]) is not bool:
        raise MissionStateError("invalid_campaign_record", "omission risk must_cite is invalid")
    return OmissionRisk(
        risk_id=_text(value["risk_id"], "omission_risk.risk_id").casefold(),
        paper_id=None if value["paper_id"] is None else _text(value["paper_id"], "omission_risk.paper_id").casefold(),
        category=_text(value["category"], "omission_risk.category").casefold(),
        severity=severity, status=status, must_cite=value["must_cite"],
        next_action=_text(value["next_action"], "omission_risk.next_action"),
    )


def _selection_summary(row: Any) -> SelectionSummary:
    value = _exact(row, {"selected_count", "retained_count", "substitution_count", "unreplaced_count"}, "selection_summary")
    counts = {}
    for field in value:
        count = value[field]
        if type(count) is not int or count < 0:
            raise MissionStateError("invalid_campaign_record", f"selection_summary.{field} must be a nonnegative integer")
        counts[field] = count
    return SelectionSummary(**counts)


def build_campaign_snapshot(value: dict[str, Any]) -> CampaignSnapshot:
    expected = {"schema_version", "topic", "coverage_requirements", "papers", "source_versions", "inspections", "claims", "citation_relations", "omission_risks", "selection_summary"}
    if not isinstance(value, dict) or set(value) != expected:
        raise MissionStateError("invalid_campaign_snapshot", "snapshot fields are not exact")
    if value["schema_version"] != CAMPAIGN_PROCESS_SCHEMA:
        raise MissionStateError("invalid_campaign_snapshot", "unsupported snapshot schema")
    collections = ("coverage_requirements", "papers", "source_versions", "inspections", "claims", "citation_relations", "omission_risks")
    if any(not isinstance(value[key], list) for key in collections):
        raise MissionStateError("invalid_campaign_snapshot", "snapshot collections must be lists")
    requirements = tuple(
        sorted(
            (_coverage_requirement(row) for row in value["coverage_requirements"]),
            key=lambda row: (row.priority, row.cell_id),
        )
    )
    if not requirements:
        raise MissionStateError("invalid_campaign_snapshot", "coverage_requirements must not be empty")
    coverage_ids = {row.cell_id for row in requirements}
    priorities = {row.priority for row in requirements}
    if len(coverage_ids) != len(requirements) or len(priorities) != len(requirements):
        raise MissionStateError("invalid_campaign_snapshot", "coverage requirement ids and priorities must be unique")
    if priorities != set(range(1, len(requirements) + 1)):
        raise MissionStateError("invalid_campaign_snapshot", "coverage requirement priorities must be contiguous from one")
    papers = tuple(sorted((_paper(row, coverage_ids) for row in value["papers"]), key=lambda row: row.paper_id))
    sources = tuple(sorted((_source_version(row) for row in value["source_versions"]), key=lambda row: row.source_id))
    inspections = tuple(sorted((_inspection(row) for row in value["inspections"]), key=lambda row: row.inspection_id))
    claims = tuple(sorted((_claim(row) for row in value["claims"]), key=lambda row: row.claim_id))
    relations = tuple(sorted((_relation(row) for row in value["citation_relations"]), key=lambda row: row.relation_id))
    risks = tuple(sorted((_risk(row) for row in value["omission_risks"]), key=lambda row: row.risk_id))
    selection_summary = _selection_summary(value["selection_summary"])
    paper_ids = {row.paper_id for row in papers}
    if len(paper_ids) != len(papers):
        raise MissionStateError("invalid_campaign_snapshot", "duplicate paper_id")
    if selection_summary.selected_count != sum(row.selected for row in papers):
        raise MissionStateError("invalid_campaign_snapshot", "selection_summary.selected_count disagrees with papers")
    if selection_summary.retained_count != sum(
        row.paper_id in {source.paper_id for source in sources if source.available and source.lawful and not source.quarantined and not source.metadata_conflict}
        for row in papers if row.selected
    ):
        raise MissionStateError("invalid_campaign_snapshot", "selection_summary.retained_count disagrees with available selected papers")
    if selection_summary.unreplaced_count != selection_summary.selected_count - selection_summary.retained_count:
        raise MissionStateError("invalid_campaign_snapshot", "selection_summary.unreplaced_count disagrees with selected/retained counts")
    if selection_summary.substitution_count > selection_summary.retained_count:
        raise MissionStateError("invalid_campaign_snapshot", "selection_summary.substitution_count exceeds retained count")
    for collection, label, field in ((sources, "source_id", "source_id"), (inspections, "inspection_id", "inspection_id"), (claims, "claim_id", "claim_id"), (relations, "relation_id", "relation_id"), (risks, "risk_id", "risk_id")):
        ids = [getattr(row, field) for row in collection]
        if len(ids) != len(set(ids)):
            raise MissionStateError("invalid_campaign_snapshot", f"duplicate {label}")
    source_by_paper: dict[str, list[SourceVersionRecord]] = {}
    for row in sources:
        source_by_paper.setdefault(row.paper_id, []).append(row)
    inspection_by_paper: dict[str, list[InspectionRecord]] = {}
    for row in inspections:
        inspection_by_paper.setdefault(row.paper_id, []).append(row)
    claims_by_paper: dict[str, list[ClaimRecord]] = {}
    for row in claims:
        claims_by_paper.setdefault(row.paper_id, []).append(row)
    for row in (*sources, *inspections, *claims, *relations, *risks):
        for field in ("paper_id", "citing_paper_id", "cited_paper_id"):
            if hasattr(row, field) and getattr(row, field) is not None and getattr(row, field) not in paper_ids:
                raise MissionStateError("invalid_campaign_snapshot", f"unknown paper reference: {getattr(row, field)}")
    for paper in papers:
        if paper.state in {"SOURCE_RESOLVED", "ACQUIRED", "SAFETY_CHECKED", "INSPECTED", "CLAIM_MAPPED"} and not source_by_paper.get(paper.paper_id):
            raise MissionStateError("invalid_campaign_snapshot", f"{paper.paper_id} requires a source version for state {paper.state}")
        if paper.state in {"INSPECTED", "CLAIM_MAPPED"} and not any(row.status == "inspected" for row in inspection_by_paper.get(paper.paper_id, [])):
            raise MissionStateError("invalid_campaign_snapshot", f"{paper.paper_id} requires an inspected record for state {paper.state}")
        if paper.state == "CLAIM_MAPPED" and not claims_by_paper.get(paper.paper_id):
            raise MissionStateError("invalid_campaign_snapshot", f"{paper.paper_id} requires a claim record for CLAIM_MAPPED")
    return CampaignSnapshot(
        topic=_text(value["topic"], "topic"), coverage_requirements=requirements,
        papers=papers, source_versions=sources,
        inspections=inspections, claims=claims, citation_relations=relations, omission_risks=risks,
        selection_summary=selection_summary,
    )


def load_campaign_snapshot(path: Path) -> CampaignSnapshot:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_campaign_snapshot", "snapshot is not readable JSON") from exc
    return build_campaign_snapshot(value)


def transition_state(current: str, target: str) -> str:
    current = _text(current, "current_state")
    target = _text(target, "target_state")
    if current not in PAPER_STATES or target not in PAPER_STATES:
        raise MissionStateError("invalid_paper_transition", "blocked states cannot be transitioned automatically")
    if _STATE_RANK[target] != _STATE_RANK[current] + 1:
        raise MissionStateError("invalid_paper_transition", f"only adjacent transitions are allowed: {current} -> {target}")
    return target


def _technical_ready(paper: PaperRecord, inspections: dict[str, InspectionRecord], claims: dict[str, list[ClaimRecord]]) -> bool:
    inspection = next((row for row in inspections.values() if row.paper_id == paper.paper_id), None)
    return bool(
        inspection and inspection.status == "inspected" and inspection.technical_anchors
        and any(row.status == "supported" and row.support_class in {"primary_technical_support", "project_derivation"} for row in claims.get(paper.paper_id, []))
    )


def build_coverage_report(snapshot: CampaignSnapshot) -> dict[str, Any]:
    inspections = {row.inspection_id: row for row in snapshot.inspections}
    claims: dict[str, list[ClaimRecord]] = {}
    for row in snapshot.claims:
        claims.setdefault(row.paper_id, []).append(row)
    rows = []
    for requirement in snapshot.coverage_requirements:
        matching = [row for row in snapshot.papers if requirement.cell_id in row.coverage_cells]
        supporting = [row.paper_id for row in matching if _technical_ready(row, inspections, claims)]
        candidates = [row.paper_id for row in matching if row.paper_id not in supporting]
        actionable = [row.paper_id for row in matching if row.paper_id not in supporting and row.state not in BLOCKED_PAPER_STATES]
        status = "covered" if supporting else "partially_covered" if actionable else "gap"
        rows.append({
            "cell_id": requirement.cell_id, "label": requirement.label,
            "priority": requirement.priority, "status": status,
            "supporting_paper_ids": sorted(supporting),
            "candidate_paper_ids": sorted(candidates),
            "direct_evidence_required": requirement.direct_evidence_required,
        })
    return {"schema_version": "ra-survey-coverage-preflight-v1", "topic": snapshot.topic, "cells": rows,
            "gap_count": sum(row["status"] == "gap" for row in rows),
            "partial_count": sum(row["status"] == "partially_covered" for row in rows),
            "what_is_not_concluded": ["literature completeness", "technical correctness", "scientific superiority"]}


def build_availability_preflight(snapshot: CampaignSnapshot) -> dict[str, Any]:
    versions: dict[str, list[dict[str, Any]]] = {}
    for row in snapshot.source_versions:
        versions.setdefault(row.paper_id, []).append({
            "identifier": row.source_identifier, "version_relation": row.version_relation,
            "version_date": row.version_date, "publication_date": row.publication_date, "available": row.available,
            "lawful": row.lawful, "quarantined": row.quarantined,
            "metadata_conflict": row.metadata_conflict, "source_id": row.source_id,
        })
    evidence, access = [], []
    selected_versions: dict[str, Any] = {}
    for paper in snapshot.papers:
        if not paper.source_required:
            continue
        try:
            choice = choose_preferred_source_version(
                versions.get(paper.paper_id, []),
                next((row["publication_date"] for row in versions.get(paper.paper_id, []) if row.get("publication_date")), None),
            )
        except ValueError:
            access.append({"paper_id": paper.paper_id, "title": paper.title, "reason": "no_lawful_available_source"})
            continue
        selected = choice["selected_version"]
        selected_versions[paper.paper_id] = choice
        evidence.append({"paper_id": paper.paper_id, "title": paper.title, "source_identifier": selected["identifier"], "reason": "lawful_available_source"})
    return {"schema_version": "ra-survey-availability-preflight-v1", "topic": snapshot.topic,
            "evidence_queue": sorted(evidence, key=lambda row: row["paper_id"]),
            "access_or_omission_queue": sorted(access, key=lambda row: row["paper_id"]),
            "selected_versions": selected_versions,
            "evidence_count": len(evidence), "access_or_omission_count": len(access),
            "source_availability_is_not_technical_claim_support": True}


def build_process_plan(snapshot: CampaignSnapshot) -> dict[str, Any]:
    coverage = build_coverage_report(snapshot)
    availability = build_availability_preflight(snapshot)
    actions: list[dict[str, Any]] = []
    gaps = [row for row in coverage["cells"] if row["status"] != "covered"]
    for row in sorted(gaps, key=lambda item: (item["priority"], item["cell_id"])):
        actions.append({
            "priority": row["priority"],
            "action_id": "resolve_coverage_gap",
            "target_cell": row["cell_id"],
            "reason": row["label"],
            "expected_artifact": "coverage_preflight.json",
            "stop_condition": "stop when one lawful, safety-cleared, technically inspected source supports the cell or the gap is explicitly accepted",
        })
    for row in snapshot.omission_risks:
        if row.must_cite and row.status in {"open", "partially_closed"}:
            actions.append({"priority": 1, "action_id": "resolve_must_cite_source", "target_id": row.paper_id or row.risk_id, "reason": row.next_action, "expected_artifact": "availability_preflight.json", "stop_condition": "stop when access, quarantine, or omission disposition is recorded"})
    if not actions:
        actions.append({"priority": len(snapshot.coverage_requirements) + 1, "action_id": "optional_venue_enrichment", "target_id": None, "reason": "all required coverage actions are currently satisfied", "expected_artifact": "venue_metrics_registry.json", "stop_condition": "stop when no dated lawful registry is available; keep metrics not_available"})
    actions.sort(key=lambda row: (row["priority"], row.get("target_cell") or "", row.get("target_id") or "", row["action_id"]))
    first = actions[0]
    status = "evidence_map_ready" if coverage["gap_count"] or coverage["partial_count"] else "scoped_review_candidate"
    return {"schema_version": PROCESS_PLAN_SCHEMA, "status": status, "topic": snapshot.topic,
            "snapshot_sha256": sha256_bytes(canonical_json_bytes(snapshot.as_dict())),
            "selection_summary": _asdict(snapshot.selection_summary),
            "coverage": coverage, "availability": availability, "next_action": first,
            "candidate_actions": actions, "what_is_not_concluded": ["literature completeness", "technical correctness", "scientific superiority", "topic centrality"]}


def write_process_plan(snapshot_path: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    snapshot = load_campaign_snapshot(snapshot_path)
    output_dir = output_dir.resolve()
    assert_public_write_path_allowed(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {"coverage_preflight.json": build_coverage_report(snapshot), "availability_preflight.json": build_availability_preflight(snapshot), "process_plan.json": build_process_plan(snapshot)}
    for name, payload in paths.items():
        path = output_dir / name
        if path.exists() and not force:
            raise MissionStateError("output_exists", f"refusing to overwrite {path}; use --force")
        atomic_write_bytes(path, pretty_json_bytes(payload))
    return {"schema_version": PROCESS_PLAN_SCHEMA, "status": "process_plan_written", "output_dir": str(output_dir), "artifacts": [str(output_dir / name) for name in paths]}


__all__ = [
    "CAMPAIGN_PROCESS_SCHEMA", "PROCESS_PLAN_SCHEMA", "PAPER_STATES", "BLOCKED_PAPER_STATES",
    "CampaignSnapshot", "ClaimRecord", "CitationRelation", "CoverageRequirement", "InspectionRecord",
    "OmissionRisk", "PaperRecord", "SelectionSummary", "SourceVersionRecord",
    "build_campaign_snapshot", "load_campaign_snapshot", "transition_state", "build_coverage_report",
    "build_availability_preflight", "build_process_plan", "write_process_plan",
]
