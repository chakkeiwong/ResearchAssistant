"""Concise, source-grounded scholarly assessment notes.

This is the active M22 review representation. It records what is promising,
what may fail or overreach, and what remains unknown without pretending that a
reviewer's judgment is a calibrated probability. Hard provenance and source
gates remain separate and authoritative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import MissionStateError, pretty_json_bytes


ASSESSMENT_SCHEMA = "ra-survey-qualitative-assessment-v1"
ASSESSMENT_BUNDLE_SCHEMA = "ra-survey-qualitative-assessment-bundle-v1"
ASSESSMENT_TYPES = ("paper", "claim", "omission")
NONCLAIMS = [
    "claim truth",
    "scientific correctness",
    "literature completeness",
    "reviewer competence",
    "source safety in fact",
    "claim support authorization",
    "prose readiness",
]
LIST_FIELDS = ("merits", "concerns", "uncertainties", "evidence_refs")
MAX_ITEMS = 8
MAX_ITEM_LENGTH = 500
MAX_SUMMARY_LENGTH = 1200


def build_assessment(
    *,
    subject_id: str,
    assessment_type: str,
    summary: str,
    merits: list[str],
    concerns: list[str],
    uncertainties: list[str],
    evidence_refs: list[str],
    next_action: str,
) -> dict[str, Any]:
    """Build one concise assessment without promoting evidence."""
    payload: dict[str, Any] = {
        "schema_version": ASSESSMENT_SCHEMA,
        "subject_id": subject_id,
        "assessment_type": assessment_type,
        "summary": summary,
        "merits": merits,
        "concerns": concerns,
        "uncertainties": uncertainties,
        "evidence_refs": evidence_refs,
        "next_action": next_action,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    return validate_assessment(payload)


def validate_assessment(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MissionStateError("invalid_qualitative_assessment", "assessment must be an object")
    required = {
        "schema_version", "subject_id", "assessment_type", "summary",
        *LIST_FIELDS, "next_action", "claim_support_allowed", "ready_for_prose",
        "what_is_not_concluded",
    }
    if set(value) != required:
        raise MissionStateError("invalid_qualitative_assessment", "assessment fields are not exact")
    if value["schema_version"] != ASSESSMENT_SCHEMA:
        raise MissionStateError("invalid_qualitative_assessment", "assessment schema is unsupported")
    if not isinstance(value["subject_id"], str) or not value["subject_id"].strip():
        raise MissionStateError("invalid_assessment_subject", "subject_id must be nonempty")
    if value["assessment_type"] not in ASSESSMENT_TYPES:
        raise MissionStateError("invalid_assessment_type", "assessment_type must be paper, claim, or omission")
    _require_text(value["summary"], "summary", maximum=MAX_SUMMARY_LENGTH)
    _require_text(value["next_action"], "next_action", maximum=MAX_ITEM_LENGTH)
    for field in LIST_FIELDS:
        _require_text_list(value[field], field)
    if value["claim_support_allowed"] is not False or value["ready_for_prose"] is not False:
        raise MissionStateError("invalid_assessment_promotion", "qualitative notes cannot promote claims or prose")
    if value["what_is_not_concluded"] != NONCLAIMS:
        raise MissionStateError("invalid_assessment_nonclaims", "assessment nonclaims are fixed")
    return value


def write_assessment(*, assessment: dict[str, Any], output_path: Path, force: bool = False) -> dict[str, Any]:
    validate_assessment(assessment)
    output_path = output_path.absolute()
    if output_path.exists() and not force:
        raise MissionStateError("output_exists", f"assessment already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pretty_json_bytes(assessment))
    return {
        "schema_version": "ra-survey-qualitative-assessment-write-result-v1",
        "status": "qualitative_assessment_written",
        "path": str(output_path),
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }


def build_assessment_bundle(
    *, topic: str, source_scope: str, assessments: list[dict[str, Any]],
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "schema_version": ASSESSMENT_BUNDLE_SCHEMA,
        "topic": topic,
        "source_scope": source_scope,
        "assessments": assessments,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    return validate_assessment_bundle(bundle)


def validate_assessment_bundle(value: Any) -> dict[str, Any]:
    required = {
        "schema_version", "topic", "source_scope", "assessments",
        "claim_support_allowed", "ready_for_prose", "what_is_not_concluded",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise MissionStateError("invalid_qualitative_bundle", "assessment bundle fields are not exact")
    if value["schema_version"] != ASSESSMENT_BUNDLE_SCHEMA:
        raise MissionStateError("invalid_qualitative_bundle", "assessment bundle schema is unsupported")
    _require_text(value["topic"], "topic", maximum=MAX_SUMMARY_LENGTH)
    _require_text(value["source_scope"], "source_scope", maximum=MAX_SUMMARY_LENGTH)
    assessments = value["assessments"]
    if not isinstance(assessments, list) or not assessments:
        raise MissionStateError("invalid_qualitative_bundle", "assessments must be nonempty")
    validated = [validate_assessment(row) for row in assessments]
    subject_ids = [row["subject_id"] for row in validated]
    if len(subject_ids) != len(set(subject_ids)):
        raise MissionStateError("invalid_qualitative_bundle", "assessment subject_ids must be unique")
    if value["claim_support_allowed"] is not False or value["ready_for_prose"] is not False:
        raise MissionStateError("invalid_assessment_promotion", "qualitative bundles cannot promote claims or prose")
    if value["what_is_not_concluded"] != NONCLAIMS:
        raise MissionStateError("invalid_assessment_nonclaims", "assessment nonclaims are fixed")
    return value


def write_assessment_bundle(*, bundle: dict[str, Any], output_path: Path, force: bool = False) -> dict[str, Any]:
    validate_assessment_bundle(bundle)
    output_path = output_path.absolute()
    if output_path.exists() and not force:
        raise MissionStateError("output_exists", f"assessment bundle already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pretty_json_bytes(bundle))
    return {
        "schema_version": "ra-survey-qualitative-assessment-bundle-write-result-v1",
        "status": "qualitative_assessment_bundle_written",
        "path": str(output_path),
        "assessment_count": len(bundle["assessments"]),
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }


def _require_text(value: Any, field: str, *, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise MissionStateError("invalid_assessment_text", f"{field} must be nonempty and at most {maximum} characters")


def _require_text_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
        raise MissionStateError("invalid_assessment_list", f"{field} must contain 1-{MAX_ITEMS} items")
    for item in value:
        _require_text(item, field, maximum=MAX_ITEM_LENGTH)


__all__ = [
    "ASSESSMENT_SCHEMA",
    "ASSESSMENT_BUNDLE_SCHEMA",
    "ASSESSMENT_TYPES",
    "NONCLAIMS",
    "build_assessment",
    "build_assessment_bundle",
    "validate_assessment",
    "validate_assessment_bundle",
    "write_assessment",
    "write_assessment_bundle",
]
