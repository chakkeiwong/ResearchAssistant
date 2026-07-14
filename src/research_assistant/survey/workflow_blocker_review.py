from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.review_decisions import (
    COMMON_SIDECAR_KEYS,
    atomic_write_json,
    common_sidecar_fields,
    load_bound_decision_envelope,
    normalize_required_text,
    normalize_reviewed_at,
    normalize_string_list,
    require_exact_keys,
    utc_now_iso,
    validate_exact_decisions,
)


SURVEY_REVIEWED_WORKFLOW_BLOCKERS_RESULT_SCHEMA_VERSION = "ra-survey-reviewed-workflow-blocker-import-result-v2"
SURVEY_REVIEWED_WORKFLOW_BLOCKERS_SCHEMA_VERSION = "ra-survey-reviewed-workflow-blockers-v2"
WORKFLOW_BLOCKER_NONCLAIMS = [
    "underlying evidence correctness",
    "literature completeness",
    "final prose readiness",
    "live web coverage",
    "product readiness",
    "scientific correctness",
]
WORKFLOW_SIDECAR_KEYS = COMMON_SIDECAR_KEYS | {
    "workflow_blockers",
    "rejected_workflow_blockers",
    "coverage_errors",
    "accepted_workflow_blocker_count",
    "rejected_workflow_blocker_count",
    "resolved_workflow_blocker_count",
    "open_workflow_blocker_count",
}


def import_reviewed_workflow_blockers(
    *, review_queue_path: Path, decisions_path: Path, output_dir: Path, force: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    output_path = output_dir / "reviewed_workflow_blockers.json"
    if output_path.exists() and not force:
        return _blocked("output_exists", output_dir, ["rerun with --force or choose a new --out directory"])
    try:
        context, _, rows, decisions_raw = load_bound_decision_envelope(
            review_queue_path=review_queue_path,
            decisions_path=decisions_path,
            decision_type="workflow_blocker",
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    result = validate_exact_decisions(context=context, rows=rows, validator=_validate_decision)
    resolved_count = sum(row["disposition"] == "resolved_by_reviewed_evidence" for row in result.accepted)
    open_count = sum(row["disposition"] == "remains_open" for row in result.accepted)
    payload = {
        "schema_version": SURVEY_REVIEWED_WORKFLOW_BLOCKERS_SCHEMA_VERSION,
        **common_sidecar_fields(
            context=context,
            decisions_path=decisions_path,
            decisions_raw=decisions_raw,
            result=result,
            created_at=utc_now_iso(),
        ),
        "workflow_blockers": result.accepted,
        "rejected_workflow_blockers": result.rejected,
        "coverage_errors": result.coverage_errors,
        **workflow_sidecar_expected_fields(result),
    }
    atomic_write_json(output_path, payload)
    return {
        "schema_version": SURVEY_REVIEWED_WORKFLOW_BLOCKERS_RESULT_SCHEMA_VERSION,
        "status": "reviewed_workflow_blockers_complete" if result.complete else "blocked_invalid_workflow_blocker_decisions",
        "output_dir": str(output_dir),
        "reviewed_workflow_blockers_path": str(output_path),
        "accepted_workflow_blocker_count": len(result.accepted),
        "rejected_workflow_blocker_count": len(result.rejected),
        "resolved_workflow_blocker_count": resolved_count,
        "open_workflow_blocker_count": open_count,
        "decision_coverage_complete": result.complete,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": WORKFLOW_BLOCKER_NONCLAIMS,
    }


def _validate_decision(row: Any, queue_item: dict[str, Any] | None, index: int) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(row, dict):
        return {}, [f"row {index} is not an object"]
    reasons: list[str] = []
    disposition = _text(row.get("disposition"), "disposition", reasons).lower()
    expected = {"queue_item_id", "disposition", "rationale", "reviewer", "reviewed_at"}
    if disposition == "resolved_by_reviewed_evidence":
        expected.add("evidence_queue_item_ids")
    elif disposition == "remains_open":
        expected.add("next_action")
    try:
        require_exact_keys(row, expected, f"workflow-blocker decision row {index}")
    except MissionStateError as exc:
        reasons.append(str(exc))
    rationale = _text(row.get("rationale"), "rationale", reasons)
    reviewer = _text(row.get("reviewer"), "reviewer", reasons)
    reviewed_at = _time(row.get("reviewed_at"), reasons)
    if disposition not in {"resolved_by_reviewed_evidence", "remains_open"}:
        reasons.append("disposition must be resolved_by_reviewed_evidence or remains_open")
    required_ids = sorted(queue_item.get("required_evidence_queue_item_ids") or []) if queue_item else []
    resolution_class = queue_item.get("resolution_class") if queue_item else None
    evidence_type = queue_item.get("required_evidence_queue_type") if queue_item else None
    evidence_ids: list[str] = []
    next_action = ""
    if disposition == "resolved_by_reviewed_evidence":
        try:
            evidence_ids = normalize_string_list(row.get("evidence_queue_item_ids"), field="evidence_queue_item_ids")
        except MissionStateError as exc:
            reasons.append(str(exc))
        if resolution_class == "upstream_repair_required" or evidence_type is None or not required_ids:
            reasons.append("upstream_repair_required blocker cannot be resolved by review evidence")
        if evidence_ids != required_ids:
            reasons.append("evidence_queue_item_ids must equal the workflow blocker's exact required evidence scope")
    elif disposition == "remains_open":
        next_action = _text(row.get("next_action"), "next_action", reasons)
    return {
        "disposition": disposition,
        "rationale": rationale,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "resolution_class": resolution_class,
        "required_evidence_queue_type": evidence_type,
        "required_evidence_queue_item_ids": required_ids,
        "evidence_queue_item_ids": evidence_ids,
        "next_action": next_action,
        "status": "reviewed_resolved_candidate" if disposition == "resolved_by_reviewed_evidence" else "open",
        "ready_for_prose": False,
    }, reasons


def workflow_sidecar_expected_fields(result: Any) -> dict[str, Any]:
    return {
        "status": (
            "reviewed_workflow_blockers_complete"
            if result.complete
            else "blocked_invalid_workflow_blocker_decisions"
        ),
        "accepted_workflow_blocker_count": len(result.accepted),
        "rejected_workflow_blocker_count": len(result.rejected),
        "resolved_workflow_blocker_count": sum(
            row["disposition"] == "resolved_by_reviewed_evidence" for row in result.accepted
        ),
        "open_workflow_blocker_count": sum(
            row["disposition"] == "remains_open" for row in result.accepted
        ),
        "what_is_not_concluded": WORKFLOW_BLOCKER_NONCLAIMS,
    }


def _text(value: Any, field: str, reasons: list[str]) -> str:
    try:
        return normalize_required_text(value, field=field)
    except MissionStateError as exc:
        reasons.append(str(exc)); return ""


def _time(value: Any, reasons: list[str]) -> str:
    try:
        return normalize_reviewed_at(value)
    except MissionStateError as exc:
        reasons.append(str(exc)); return ""


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_WORKFLOW_BLOCKERS_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": WORKFLOW_BLOCKER_NONCLAIMS,
    }


__all__ = [
    "SURVEY_REVIEWED_WORKFLOW_BLOCKERS_SCHEMA_VERSION",
    "WORKFLOW_BLOCKER_NONCLAIMS",
    "WORKFLOW_SIDECAR_KEYS",
    "_validate_decision",
    "import_reviewed_workflow_blockers",
    "workflow_sidecar_expected_fields",
]
