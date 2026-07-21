from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SURVEY_PUBLIC_SOURCE_PACKET_RESULT_SCHEMA_VERSION = "ra-survey-public-source-packet-result-v1"
SURVEY_PUBLIC_SOURCE_PACKET_MANIFEST_SCHEMA_VERSION = "ra-survey-public-source-packet-manifest-v1"
SURVEY_PUBLIC_SOURCE_READY_SCHEMA_VERSION = "ra-survey-public-source-ready-for-prose-v1"
SURVEY_PUBLIC_SOURCE_WORKFLOW_STATE_SCHEMA_VERSION = "ra-survey-public-source-workflow-state-v1"
SURVEY_PUBLIC_SOURCE_SAFETY_STATUS_SCHEMA_VERSION = "ra-survey-public-source-safety-status-v1"
MISSION_SOURCE_INTAKE_V2_SCHEMA_VERSION = "ra-survey-mission-source-intake-v2"

PUBLIC_SOURCE_PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
    "source_safety_status.json",
    "ready_for_prose.json",
    "survey_packet.md",
    "build_manifest.json",
)

REQUIRED_INPUT_FILES = {
    "metadata_candidate_ledger": ("metadata_dir", "candidate_ledger.json"),
    "metadata_citation_map": ("metadata_dir", "citation_map.json"),
    "metadata_source_support": ("metadata_dir", "source_support.json"),
    "metadata_paper_classifications": ("metadata_dir", "paper_classifications.json"),
    "metadata_omission_risk": ("metadata_dir", "omission_risk.json"),
    "source_intake_status": ("source_status_dir", "phase4_source_intake_status.json"),
    "anchor_inventory": ("anchor_dir", "source_anchor_inventory.json"),
    "anchor_source_support": ("anchor_dir", "source_support.json"),
    "anchor_claim_support": ("anchor_dir", "claim_support.json"),
    "quarantine_register": ("anchor_dir", "quarantine_register.json"),
}

TECHNICAL_CLAIM_BLOCKER = (
    "technical claims require explicit claim rows mapped to checked source anchor ids "
    "and a completed review; metadata, citation counts, and source availability are not support"
)

PUBLIC_SOURCE_PACKET_NONCLAIMS = [
    "final survey prose quality",
    "literature completeness",
    "scientific correctness",
    "technical claim support",
    "retraction/version safety",
    "product readiness",
]

SUPPORTED_REVIEW_STATUSES = {
    "reviewed",
    "reviewed_passed",
    "human_reviewed",
    "human_reviewed_passed",
    "model_reviewed_passed",
}
SAFETY_CLEAR_STATUSES = {"checked_clear"}
SAFETY_BLOCKING_STATUSES = {
    "not_checked",
    "not_checked_phase5",
    "withdrawn_or_blocked",
    "retracted_or_blocked",
    "version_mismatch",
    "erratum_or_notice_found",
    "quarantined",
    "unknown",
}


def compose_public_source_evidence_packet(
    *,
    topic: str,
    output_dir: Path,
    metadata_dir: Path,
    source_status_dir: Path,
    anchor_dir: Path,
    force: bool = False,
    _mission_v2_authority: bool = False,
) -> dict[str, Any]:
    topic = topic.strip()
    if not topic:
        return _blocked(
            "empty_topic",
            "public-source packet composition requires a non-empty topic",
            output_dir,
            next_required_actions=["provide a non-empty --topic value and rerun"],
        )

    source_status_path = source_status_dir.resolve() / "phase4_source_intake_status.json"
    if _source_status_schema(source_status_path) == MISSION_SOURCE_INTAKE_V2_SCHEMA_VERSION:
        if _mission_v2_authority is not True:
            return _blocked(
                "mission_v2_source_intake_requires_supervisor_authority",
                "mission V2 source intake can be composed only by the lock-held mission supervisor",
                output_dir,
                next_required_actions=[
                    "resume the mission with run-public-source-workflow --run-safe-local so current V2 ancestry is revalidated"
                ],
            )

    output_dir = output_dir.resolve()
    existing = [output_dir / name for name in PUBLIC_SOURCE_PACKET_FILES if (output_dir / name).exists()]
    if existing and not force:
        return {
            "schema_version": SURVEY_PUBLIC_SOURCE_PACKET_RESULT_SCHEMA_VERSION,
            "status": "blocked",
            "blocked_reason": "output_exists",
            "message": "output directory already contains public-source packet artifacts",
            "output_dir": str(output_dir),
            "existing_artifacts": [str(path) for path in existing],
            "next_required_actions": ["rerun with --force or choose a new --out directory"],
            "what_is_not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
        }

    input_paths = _resolve_input_paths(
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
    )
    missing = [name for name, path in input_paths.items() if not path.exists()]
    if missing:
        return _blocked(
            "missing_required_input",
            "public-source packet composition requires all prior-phase ledgers",
            output_dir,
            next_required_actions=[
                f"provide {name}: {input_paths[name]}" for name in missing
            ],
            details={"missing_inputs": {name: str(input_paths[name]) for name in missing}},
        )

    inputs = {name: _read_json(path) for name, path in input_paths.items()}
    if not (inputs["metadata_omission_risk"].get("risks") or inputs["metadata_omission_risk"].get("metadata_only_papers")):
        return _blocked(
            "missing_omission_risk_rows",
            "omission risks must be visible before composing the writer packet",
            output_dir,
            next_required_actions=["refresh omission_risk.json with risks or explicit metadata-only omission rows"],
        )

    unsupported_claims = _unsupported_claim_rows(inputs["anchor_claim_support"])
    if unsupported_claims:
        return _blocked(
            "unsupported_claim_rows",
            "claim_support.json contains claim rows that are not reviewed anchor-mapped support",
            output_dir,
            next_required_actions=[
                "move unsupported claim rows to blocked_claims, or map them to anchor ids and complete review"
            ],
            details={"unsupported_claims": unsupported_claims},
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    composed = _composed_payloads(topic=topic, inputs=inputs, input_paths=input_paths, output_dir=output_dir)
    for name, payload in composed.items():
        if name.endswith(".json"):
            (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))
        else:
            (output_dir / name).write_text(str(payload))

    manifest = composed["build_manifest.json"]
    ready = composed["ready_for_prose.json"]
    return {
        "schema_version": SURVEY_PUBLIC_SOURCE_PACKET_RESULT_SCHEMA_VERSION,
        "status": "packet_composed_with_blockers",
        "topic": topic,
        "output_dir": str(output_dir),
        "artifact_paths": manifest["artifact_paths"],
        "packet_ready_for_writer": ready["packet_ready_for_writer"],
        "ready_for_prose": ready["ready_for_prose"],
        "ready_blockers": ready["blockers"],
        "anchor_count": manifest["anchor_count"],
        "supported_claim_count": manifest["supported_claim_count"],
        "blocked_claim_count": manifest["blocked_claim_count"],
        "source_gap_count": manifest["source_gap_count"],
        "source_safety_status": manifest["source_safety_status"],
        "source_safety_blocker_count": manifest["source_safety_blocker_count"],
        "what_is_not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }


def _resolve_input_paths(*, metadata_dir: Path, source_status_dir: Path, anchor_dir: Path) -> dict[str, Path]:
    roots = {
        "metadata_dir": metadata_dir.resolve(),
        "source_status_dir": source_status_dir.resolve(),
        "anchor_dir": anchor_dir.resolve(),
    }
    return {
        name: roots[root_name] / file_name
        for name, (root_name, file_name) in REQUIRED_INPUT_FILES.items()
    }


def _source_status_schema(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload.get("schema_version") if isinstance(payload, dict) else None


def _composed_payloads(
    *,
    topic: str,
    inputs: dict[str, dict[str, Any]],
    input_paths: dict[str, Path],
    output_dir: Path,
) -> dict[str, Any]:
    anchors = inputs["anchor_inventory"].get("anchors") or []
    anchor_source_support = inputs["anchor_source_support"]
    anchor_claim_support = inputs["anchor_claim_support"]
    source_intake_status = inputs["source_intake_status"]
    source_gap_rows = anchor_source_support.get("source_gap_rows") or []
    blocked_claims = anchor_claim_support.get("blocked_claims") or []
    supported_claims = anchor_claim_support.get("claims") or []
    source_safety_status = _compose_source_safety_status(
        topic=topic,
        quarantine_register=inputs["quarantine_register"],
        source_support=anchor_source_support,
    )
    omission_risk = _compose_omission_risk(inputs["metadata_omission_risk"], anchor_claim_support)

    ready = _ready_for_prose_report(
        topic=topic,
        anchors=anchors,
        source_gap_rows=source_gap_rows,
        blocked_claims=blocked_claims,
        supported_claims=supported_claims,
        omission_risk=omission_risk,
        source_safety_status=source_safety_status,
    )
    source_support = _compose_source_support(
        topic=topic,
        metadata_source_support=inputs["metadata_source_support"],
        source_intake_status=source_intake_status,
        anchor_source_support=anchor_source_support,
    )
    claim_support = _compose_claim_support(
        topic=topic,
        anchor_claim_support=anchor_claim_support,
        anchors=anchors,
    )
    candidate_ledger = _compose_candidate_ledger(
        topic=topic,
        metadata_candidate_ledger=inputs["metadata_candidate_ledger"],
        source_support=source_support,
    )
    citation_map = _compose_citation_map(topic=topic, metadata_citation_map=inputs["metadata_citation_map"])
    paper_classifications = _compose_paper_classifications(
        topic=topic,
        metadata_paper_classifications=inputs["metadata_paper_classifications"],
        source_support=source_support,
    )

    artifact_paths = {name: str(output_dir / name) for name in PUBLIC_SOURCE_PACKET_FILES}
    manifest = {
        "schema_version": SURVEY_PUBLIC_SOURCE_PACKET_MANIFEST_SCHEMA_VERSION,
        "status": "created",
        "created_at": _utc_now_iso(),
        "topic": topic,
        "input_paths": {name: str(path) for name, path in input_paths.items()},
        "input_sha256": {name: _file_sha256(path) for name, path in input_paths.items()},
        "artifact_paths": artifact_paths,
        "anchor_count": len(anchors),
        "source_gap_count": len(source_gap_rows),
        "supported_claim_count": len(supported_claims),
        "blocked_claim_count": len(blocked_claims),
        "source_safety_status": source_safety_status["status"],
        "source_safety_blocker_count": source_safety_status["blocking_count"],
        "ready_for_prose": ready["ready_for_prose"],
        "packet_ready_for_writer": ready["packet_ready_for_writer"],
        "workflow_state": _workflow_state_from_ready(ready),
        "privacy_and_raw_artifact_policy": {
            "raw_source_copied_to_packet": False,
            "raw_latex_included": False,
            "raw_pdf_or_full_text_included": False,
            "reason": "Phase 6 writes ledgers, pointers, hashes, and source-record paths only; raw source remains in local_research.",
        },
        "next_required_actions": ready["next_required_actions"],
        "what_is_not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }
    survey_packet = _survey_packet_markdown(
        topic=topic,
        candidate_ledger=candidate_ledger,
        citation_map=citation_map,
        source_support=source_support,
        paper_classifications=paper_classifications,
        claim_support=claim_support,
        omission_risk=omission_risk,
        source_safety_status=source_safety_status,
        anchor_inventory=inputs["anchor_inventory"],
        quarantine_register=inputs["quarantine_register"],
        ready=ready,
    )
    return {
        "candidate_ledger.json": candidate_ledger,
        "citation_map.json": citation_map,
        "source_support.json": source_support,
        "paper_classifications.json": paper_classifications,
        "claim_support.json": claim_support,
        "omission_risk.json": omission_risk,
        "source_safety_status.json": source_safety_status,
        "ready_for_prose.json": ready,
        "survey_packet.md": survey_packet,
        "build_manifest.json": manifest,
    }


def _compose_candidate_ledger(
    *,
    topic: str,
    metadata_candidate_ledger: dict[str, Any],
    source_support: dict[str, Any],
) -> dict[str, Any]:
    source_by_arxiv = {
        str(row.get("arxiv_id")): row
        for row in source_support.get("papers") or []
        if row.get("arxiv_id")
    }
    included = []
    for row in metadata_candidate_ledger.get("included") or []:
        merged = dict(row)
        arxiv_id = _arxiv_id_from_identifier(str(row.get("identifier") or ""))
        if arxiv_id and arxiv_id in source_by_arxiv:
            support = source_by_arxiv[arxiv_id]
            merged["source_status"] = support.get("source_status")
            merged["source_paper_id"] = support.get("paper_id")
            merged["checked_anchor_count"] = support.get("checked_anchor_count", 0)
            merged["technical_claim_support"] = support.get("technical_claim_support")
        else:
            merged.setdefault("source_status", "metadata_only_or_not_selected_for_phase4")
            merged.setdefault("checked_anchor_count", 0)
            merged.setdefault("technical_claim_support", "not_supported")
        included.append(merged)
    return {
        "schema_version": "ra-survey-public-source-candidate-ledger-v1",
        "status": "metadata_with_public_source_overlay",
        "topic": topic,
        "candidate_count": len(included),
        "included": included,
        "duplicates": metadata_candidate_ledger.get("duplicates") or [],
        "excluded": metadata_candidate_ledger.get("excluded") or [],
        "source_overlay_policy": {
            "source_status_may_support_availability_claims": True,
            "source_status_may_support_technical_claims": False,
            "metadata_may_support_technical_claims": False,
        },
        "next_required_actions": [
            "inspect source anchors and map proposed claims explicitly before drafting technical prose",
            "expand or reject metadata-only candidates before claiming literature completeness",
        ],
    }


def _compose_citation_map(*, topic: str, metadata_citation_map: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ra-survey-public-source-citation-map-v1",
        "status": "metadata_citation_map_with_source_boundary",
        "topic": topic,
        "nodes": metadata_citation_map.get("nodes") or [],
        "edges": metadata_citation_map.get("edges") or [],
        "clusters": metadata_citation_map.get("clusters") or [],
        "frontiers": metadata_citation_map.get("frontiers") or [],
        "source_boundary": {
            "citation_edges_are_metadata_only": True,
            "citation_edges_support_coverage_navigation": True,
            "citation_edges_support_technical_claims": False,
        },
        "next_required_actions": metadata_citation_map.get("next_required_actions") or [
            "source-check selected backward, forward, and adjacent candidates"
        ],
    }


def _compose_source_support(
    *,
    topic: str,
    metadata_source_support: dict[str, Any],
    source_intake_status: dict[str, Any],
    anchor_source_support: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "ra-survey-public-source-support-v1",
        "status": "public_source_overlay_available",
        "topic": topic,
        "metadata_layer": {
            "status": metadata_source_support.get("status"),
            "papers": metadata_source_support.get("papers") or [],
        },
        "source_intake": {
            "status": source_intake_status.get("status"),
            "operation": source_intake_status.get("operation"),
            "destination": source_intake_status.get("destination"),
            "attempted_count": source_intake_status.get("attempted_count"),
            "fetched_count": source_intake_status.get("fetched_count"),
            "skipped_duplicates": source_intake_status.get("skipped_duplicates") or [],
            "failures": source_intake_status.get("failures") or [],
            "approved_candidate_ids": source_intake_status.get("approved_candidate_ids") or [],
            "raw_artifact_policy": source_intake_status.get("raw_artifact_policy") or {},
        },
        "papers": anchor_source_support.get("papers") or [],
        "source_gap_rows": anchor_source_support.get("source_gap_rows") or [],
        "claim_support_policy": {
            "source_availability_support_allowed_for_technical_claims": False,
            "anchor_availability_support_allowed_for_technical_claims": False,
        },
        "source_safety_status": {
            "status": "separate_source_safety_status_json_required",
            "artifact": "source_safety_status.json",
            "source_availability_safety_allowed": False,
        },
        "not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }


def _compose_source_safety_status(
    *,
    topic: str,
    quarantine_register: dict[str, Any],
    source_support: dict[str, Any],
) -> dict[str, Any]:
    source_rows_by_paper_id = {
        str(row.get("paper_id")): row
        for row in source_support.get("papers") or []
        if row.get("paper_id")
    }
    rows_by_paper_id: dict[str, dict[str, Any]] = {}
    for row in quarantine_register.get("rows") or []:
        paper_id = str(row.get("paper_id") or "").strip()
        if not paper_id:
            continue
        source_row = source_rows_by_paper_id.get(paper_id) or {}
        status = str(row.get("retraction_or_version_status") or "not_checked").strip() or "not_checked"
        normalized = _normalize_safety_status(status)
        rows_by_paper_id[paper_id] = {
            "paper_id": paper_id,
            "arxiv_id": row.get("arxiv_id") or source_row.get("arxiv_id"),
            "source_status": row.get("source_status") or source_row.get("source_status"),
            "retraction_or_version_status": normalized,
            "original_status": status,
            "claim_support_allowed": normalized in SAFETY_CLEAR_STATUSES and row.get("claim_support_allowed") is not False,
            "evidence_contract": "only explicit public status checks or human-reviewed local records may set checked_clear",
            "next_action": _safety_next_action(normalized),
        }

    for row in source_support.get("papers") or []:
        paper_id = str(row.get("paper_id") or "").strip()
        if not paper_id or paper_id in rows_by_paper_id:
            continue
        rows_by_paper_id[paper_id] = {
            "paper_id": paper_id,
            "arxiv_id": row.get("arxiv_id"),
            "source_status": row.get("source_status"),
            "retraction_or_version_status": "not_checked",
            "original_status": None,
            "claim_support_allowed": False,
            "evidence_contract": "source availability does not imply retraction, withdrawal, erratum, or version safety",
            "next_action": "run approved retraction, withdrawal, erratum, and version checks",
        }

    rows = sorted(rows_by_paper_id.values(), key=lambda row: str(row.get("paper_id")))
    blocking_rows = [
        row for row in rows
        if str(row.get("retraction_or_version_status")) not in SAFETY_CLEAR_STATUSES
    ]
    return {
        "schema_version": SURVEY_PUBLIC_SOURCE_SAFETY_STATUS_SCHEMA_VERSION,
        "status": "checked_clear" if rows and not blocking_rows else "blocked_or_not_checked",
        "topic": topic,
        "rows": rows,
        "checked_clear_count": len(rows) - len(blocking_rows),
        "blocking_count": len(blocking_rows),
        "blocking_paper_ids": [str(row.get("paper_id")) for row in blocking_rows],
        "safety_policy": {
            "metadata_only_safety_allowed": False,
            "source_availability_safety_allowed": False,
            "unchecked_safety_allows_claim_support": False,
            "required_clear_status": "checked_clear",
        },
        "next_required_actions": [
            "run approved retraction, withdrawal, erratum, and version checks for every sourced paper",
            "record checked_clear only with explicit status evidence",
            "keep claim support blocked for any withdrawn, quarantined, mismatched-version, notice-bearing, or unchecked paper",
        ],
        "not_concluded": [
            "retraction safety",
            "version correctness",
            "erratum absence",
            "technical claim support",
            "final prose readiness",
        ],
    }


def _normalize_safety_status(status: str) -> str:
    normalized = status.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in SAFETY_CLEAR_STATUSES:
        return normalized
    if normalized in SAFETY_BLOCKING_STATUSES:
        return normalized
    if "withdraw" in normalized:
        return "withdrawn_or_blocked"
    if "retract" in normalized:
        return "retracted_or_blocked"
    if "version" in normalized and "mismatch" in normalized:
        return "version_mismatch"
    if "errat" in normalized or "notice" in normalized:
        return "erratum_or_notice_found"
    if "quarantine" in normalized:
        return "quarantined"
    if "not_checked" in normalized or "unchecked" in normalized:
        return "not_checked"
    return "unknown"


def _safety_next_action(status: str) -> str:
    if status in SAFETY_CLEAR_STATUSES:
        return "retain explicit checked-clear evidence with the packet"
    if status == "version_mismatch":
        return "resolve the canonical paper version before using anchors or claims"
    if status in {"withdrawn_or_blocked", "retracted_or_blocked", "quarantined"}:
        return "quarantine this paper and remove it from claim-support candidates"
    if status == "erratum_or_notice_found":
        return "inspect the notice and update claim mapping before using this paper"
    return "run approved retraction, withdrawal, erratum, and version checks"


def _compose_paper_classifications(
    *,
    topic: str,
    metadata_paper_classifications: dict[str, Any],
    source_support: dict[str, Any],
) -> dict[str, Any]:
    classifications = []
    for row in metadata_paper_classifications.get("classifications") or []:
        merged = dict(row)
        merged["classification_status"] = "metadata_preliminary_source_boundary_preserved"
        merged["claim_support_allowed"] = False
        classifications.append(merged)
    sourced_paper_ids = {row.get("paper_id") for row in source_support.get("papers") or []}
    return {
        "schema_version": "ra-survey-public-source-paper-classifications-v1",
        "status": "preliminary_classifications_with_source_boundary",
        "topic": topic,
        "allowed_labels": metadata_paper_classifications.get("allowed_labels") or [],
        "classifications": classifications,
        "source_record_paper_ids": sorted(str(value) for value in sourced_paper_ids if value),
        "classification_policy": {
            "metadata_classifications_are_preliminary": True,
            "classification_does_not_imply_claim_support": True,
        },
    }


def _compose_claim_support(
    *,
    topic: str,
    anchor_claim_support: dict[str, Any],
    anchors: list[dict[str, Any]],
) -> dict[str, Any]:
    claims = anchor_claim_support.get("claims") or []
    claim_candidates = _claim_candidates_from_anchors(anchors)
    return {
        "schema_version": "ra-survey-public-source-claim-support-v1",
        "status": "no_supported_technical_claims" if not claims else "reviewed_claim_rows_present",
        "topic": topic,
        "claims": claims,
        "claim_candidates": claim_candidates,
        "blocked_claims": anchor_claim_support.get("blocked_claims") or [],
        "claim_support_policy": {
            **(anchor_claim_support.get("claim_support_policy") or {}),
            "metadata_only_support_allowed_for_technical_claims": False,
            "source_availability_support_allowed_for_technical_claims": False,
            "unreviewed_anchor_support_allowed_for_technical_claims": False,
            "claim_candidates_are_not_supported_claims": True,
            "phase6_claim_gate": TECHNICAL_CLAIM_BLOCKER,
        },
        "not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }


def _claim_candidates_from_anchors(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for index, anchor in enumerate(anchors, start=1):
        anchor_id = str(anchor.get("anchor_id") or "").strip()
        paper_id = str(anchor.get("paper_id") or "").strip()
        if not anchor_id or not paper_id:
            continue
        candidates.append({
            "claim_id": f"candidate_claim_{index:03d}",
            "status": "review_required",
            "support_class": "anchor_candidate_not_support",
            "paper_ids": [paper_id],
            "anchor_ids": [anchor_id],
            "anchor_type": anchor.get("anchor_type"),
            "anchor_role": anchor.get("role"),
            "anchor_title": anchor.get("title"),
            "review_status": anchor.get("review_status") or "requires_review",
            "claim_support_allowed": False,
            "reason": "source anchor is available, but no reviewed claim text has been mapped to it",
            "next_action": "write a precise claim, inspect the source record, map exact anchor ids, and complete review before support",
        })
    return candidates


def _compose_omission_risk(
    metadata_omission_risk: dict[str, Any],
    anchor_claim_support: dict[str, Any],
) -> dict[str, Any]:
    risks = [dict(row) for row in metadata_omission_risk.get("risks") or []]
    if not anchor_claim_support.get("claims"):
        risks.append({
            "risk_id": "no_reviewed_supported_claims",
            "severity": "high",
            "status": "blocked",
            "reason": "Phase 6 has source anchors but no reviewed claim-support rows.",
            "next_action": "map proposed technical claims to anchor ids and review before prose drafting",
        })
    risks.append({
        "risk_id": "retraction_version_status_not_checked",
        "severity": "high",
        "status": "blocked",
        "reason": "Phase 5 quarantine ledger records retraction/version safety as not checked.",
        "next_action": "run retraction, withdrawal, erratum, and version checks before using papers as support",
    })
    return {
        "schema_version": "ra-survey-public-source-omission-risk-v1",
        "status": "omission_and_safety_risks_visible",
        "topic": metadata_omission_risk.get("topic"),
        "risks": risks,
        "metadata_only_papers": metadata_omission_risk.get("metadata_only_papers") or [],
        "provider_statuses": metadata_omission_risk.get("provider_statuses") or [],
        "not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }


def _ready_for_prose_report(
    *,
    topic: str,
    anchors: list[dict[str, Any]],
    source_gap_rows: list[dict[str, Any]],
    blocked_claims: list[dict[str, Any]],
    supported_claims: list[dict[str, Any]],
    omission_risk: dict[str, Any],
    source_safety_status: dict[str, Any],
) -> dict[str, Any]:
    blockers = []
    if not anchors:
        blockers.append("no checked source anchors are available")
    if source_gap_rows:
        blockers.append("one or more selected papers remain source gaps")
    if blocked_claims:
        blockers.append("technical claims are still blocked pending reviewed claim-anchor mapping")
    if not supported_claims:
        blockers.append("no reviewed supported technical claim rows are present")
    if source_safety_status.get("status") != "checked_clear":
        blockers.append("retraction/version safety is not checked clear for all sourced papers")
    if omission_risk.get("risks"):
        blockers.append("omission and reviewer-risk rows require review before claiming completeness")

    return {
        "schema_version": SURVEY_PUBLIC_SOURCE_READY_SCHEMA_VERSION,
        "status": "blocked_for_prose" if blockers else "ready_for_prose",
        "topic": topic,
        "packet_ready_for_writer": bool(anchors),
        "ready_for_prose": not blockers,
        "blockers": blockers,
        "allowed_writer_actions": [
            "inspect candidate ledgers and citation-map frontiers",
            "inspect source anchors by id/path/hash",
            "draft an outline or evidence request list that preserves blockers",
        ],
        "forbidden_writer_actions": [
            "write final survey prose that presents blocked claims as supported",
            "treat metadata-only citation edges as technical evidence",
            "treat source availability or anchor availability as claim support",
            "claim literature completeness before omission risks are resolved",
        ],
        "next_required_actions": [
            "map proposed technical claims to anchor ids and review them",
            "run retraction/version checks",
            "resolve high omission risks or record explicit omission reasons",
        ],
        "what_is_not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }


def _workflow_state_from_ready(ready: dict[str, Any]) -> dict[str, Any]:
    forbidden_jumps = list(ready.get("forbidden_writer_actions") or [])
    if not any("technical claim support" in str(item) for item in forbidden_jumps):
        forbidden_jumps.append("do not treat metadata, citation counts, source availability, or anchor availability as technical claim support")
    return {
        "schema_version": SURVEY_PUBLIC_SOURCE_WORKFLOW_STATE_SCHEMA_VERSION,
        "state": "public_source_packet_blocked_for_prose"
        if not ready.get("ready_for_prose")
        else "public_source_packet_ready_for_prose",
        "ready_for_writer": bool(ready.get("packet_ready_for_writer")),
        "ready_for_prose": bool(ready.get("ready_for_prose")),
        "safe_next_commands": [
            "inspect source_anchor_inventory.json and source_support.json",
            "map proposed technical claims to anchor ids and review them",
            "run retraction/version checks",
            "resolve omission risks or record explicit omission reasons",
            "rerun ra survey packet after claim, safety, or omission ledgers are updated",
        ],
        "approval_required_for": [
            "additional source/PDF/full-text downloads",
            "private or credentialed database use",
            "treating reviewed claim rows as final survey prose",
        ],
        "blocked_reasons": ready.get("blockers") or [],
        "forbidden_jumps": forbidden_jumps,
    }


def _survey_packet_markdown(
    *,
    topic: str,
    candidate_ledger: dict[str, Any],
    citation_map: dict[str, Any],
    source_support: dict[str, Any],
    paper_classifications: dict[str, Any],
    claim_support: dict[str, Any],
    omission_risk: dict[str, Any],
    source_safety_status: dict[str, Any],
    anchor_inventory: dict[str, Any],
    quarantine_register: dict[str, Any],
    ready: dict[str, Any],
) -> str:
    lines = [
        f"# Public-Source Literature Survey Evidence Packet: {topic}",
        "",
        f"Packet status: `{ready['status']}`",
        f"Packet ready for writer: `{str(ready['packet_ready_for_writer']).lower()}`",
        f"Ready for final prose: `{str(ready['ready_for_prose']).lower()}`",
        "",
        "## Non-Claims",
    ]
    lines.extend(f"- {item}" for item in PUBLIC_SOURCE_PACKET_NONCLAIMS)
    lines.extend([
        "",
        "## Citation Map",
        f"- Nodes: {len(citation_map.get('nodes') or [])}",
        f"- Edges: {len(citation_map.get('edges') or [])}",
        f"- Clusters: {len(citation_map.get('clusters') or [])}",
        "- Citation edges are metadata-only coverage/navigation signals, not technical support.",
        "",
        "## Candidate Ledger",
        f"- Candidates: {candidate_ledger.get('candidate_count', 0)}",
    ])
    for row in (candidate_ledger.get("included") or [])[:10]:
        lines.append(
            f"- `{row.get('paper_key')}` {row.get('title') or row.get('identifier')}: "
            f"source `{row.get('source_status')}`, anchors `{row.get('checked_anchor_count', 0)}`"
        )
    lines.extend([
        "",
        "## Source Support",
        f"- Source intake status: `{(source_support.get('source_intake') or {}).get('status')}`",
        f"- Fetched source count: `{(source_support.get('source_intake') or {}).get('fetched_count')}`",
        f"- Source gaps: `{len(source_support.get('source_gap_rows') or [])}`",
    ])
    for row in source_support.get("papers") or []:
        lines.append(
            f"- `{row.get('paper_id')}` arXiv `{row.get('arxiv_id')}`: "
            f"{row.get('checked_anchor_count', 0)} checked anchor candidates; "
            f"technical support `{row.get('technical_claim_support')}`"
        )
    lines.extend([
        "",
        "## Paper Classifications",
        f"- Classification rows: {len(paper_classifications.get('classifications') or [])}",
        "- Classifications remain preliminary and do not imply claim support.",
        "",
        "## Source Anchors",
        f"- Anchor count: {anchor_inventory.get('anchor_count', 0)}",
        "- Raw LaTeX/full text is not included in this packet; inspect local source records by path and hash.",
    ])
    for row in (anchor_inventory.get("anchors") or [])[:12]:
        lines.append(
            f"- `{row.get('paper_id')}` `{row.get('anchor_id')}` "
            f"({row.get('anchor_type')}, role `{row.get('role')}`): "
            f"claim status `{row.get('claim_support_status')}`"
        )
    lines.extend([
        "",
        "## Claim Support",
        f"- Supported claim rows: {len(claim_support.get('claims') or [])}",
        f"- Review-required claim candidates: {len(claim_support.get('claim_candidates') or [])}",
        f"- Blocked claim rows: {len(claim_support.get('blocked_claims') or [])}",
        f"- Phase 6 gate: {TECHNICAL_CLAIM_BLOCKER}.",
    ])
    for row in (claim_support.get("claim_candidates") or [])[:12]:
        lines.append(
            f"- Candidate `{row.get('claim_id')}` from `{row.get('paper_ids', ['unknown'])[0]}` "
            f"anchor `{row.get('anchor_ids', ['unknown'])[0]}`: status `{row.get('status')}`, "
            f"claim support allowed `{str(row.get('claim_support_allowed')).lower()}`"
        )
    for row in claim_support.get("blocked_claims") or []:
        lines.append(f"- Blocked `{row.get('claim_id')}`: {row.get('reason')}")
    lines.extend([
        "",
        "## Quarantine And Version Safety",
        f"- Register status: `{quarantine_register.get('status')}`",
        f"- Packet safety status: `{source_safety_status.get('status')}`",
        f"- Blocking safety rows: `{source_safety_status.get('blocking_count')}`",
    ])
    for row in source_safety_status.get("rows") or []:
        lines.append(
            f"- `{row.get('paper_id')}` normalized safety `{row.get('retraction_or_version_status')}`, "
            f"claim support allowed `{str(row.get('claim_support_allowed')).lower()}`"
        )
    for row in quarantine_register.get("rows") or []:
        lines.append(
            f"- `{row.get('paper_id')}` retraction/version `{row.get('retraction_or_version_status')}`, "
            f"claim support allowed `{str(row.get('claim_support_allowed')).lower()}`"
        )
    lines.extend([
        "",
        "## Omission Risks",
    ])
    for row in omission_risk.get("risks") or []:
        lines.append(
            f"- `{row.get('risk_id')}` ({row.get('severity', 'unknown')}): "
            f"{_risk_text(row)}"
        )
    lines.extend([
        "",
        "## Ready-For-Prose Blockers",
    ])
    lines.extend(f"- {item}" for item in ready.get("blockers") or ["none"])
    lines.extend([
        "",
        "## Next Required Actions",
    ])
    lines.extend(f"- {item}" for item in ready.get("next_required_actions") or [])
    lines.append("")
    return "\n".join(lines)


def _unsupported_claim_rows(claim_support: dict[str, Any]) -> list[dict[str, Any]]:
    unsupported = []
    for row in claim_support.get("claims") or []:
        anchor_ids = _claim_anchor_ids(row)
        review_status = str(row.get("review_status") or row.get("status") or "").strip().lower()
        support_class = str(row.get("support_class") or row.get("support") or "").strip().lower()
        if not anchor_ids or review_status not in SUPPORTED_REVIEW_STATUSES:
            unsupported.append({
                "claim_id": row.get("claim_id"),
                "reason": "claim row lacks reviewed anchor mapping",
                "anchor_count": len(anchor_ids),
                "review_status": review_status or None,
                "support_class": support_class or None,
            })
            continue
        if "metadata" in support_class or "source_availability" in support_class:
            unsupported.append({
                "claim_id": row.get("claim_id"),
                "reason": "metadata/source availability cannot support technical claims",
                "anchor_count": len(anchor_ids),
                "review_status": review_status,
                "support_class": support_class,
            })
    return unsupported


def _claim_anchor_ids(row: dict[str, Any]) -> list[str]:
    for key in ("anchor_ids", "anchors", "source_anchors", "supporting_anchors"):
        value = row.get(key)
        if not value:
            continue
        if isinstance(value, list):
            ids = []
            for item in value:
                if isinstance(item, str):
                    ids.append(item)
                elif isinstance(item, dict) and item.get("anchor_id"):
                    ids.append(str(item["anchor_id"]))
            return [item for item in ids if item]
        if isinstance(value, str):
            return [value]
    return []


def _risk_text(row: dict[str, Any]) -> str:
    return str(
        row.get("reason")
        or row.get("risk")
        or row.get("note")
        or row.get("expected_action")
        or "risk recorded without narrative"
    )


def _arxiv_id_from_identifier(identifier: str) -> str | None:
    value = identifier.strip()
    if value.lower().startswith("arxiv:"):
        return value.split(":", 1)[1]
    if "arxiv.org/abs/" in value:
        return value.rstrip("/").rsplit("/", 1)[-1]
    if value[:4].isdigit() and "." in value:
        return value
    return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _blocked(
    reason: str,
    message: str,
    output_dir: Path,
    *,
    next_required_actions: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SURVEY_PUBLIC_SOURCE_PACKET_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "message": message,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": PUBLIC_SOURCE_PACKET_NONCLAIMS,
    }
    if details:
        payload["details"] = details
    return payload
