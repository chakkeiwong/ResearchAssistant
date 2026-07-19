"""Provisional title triage for the M22 unused bibliography frontier."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from research_assistant.survey.mission_state import MissionStateError


SCHEMA_VERSION = "ra-survey-omission-frontier-triage-v1"
QUEUE_SCHEMA_VERSION = "ra-survey-omission-frontier-inspection-queue-v1"
PROVISIONAL_STATUS = "TITLE_CONTEXT_PROVISIONAL"
GROUPS = (
    "DIRECT_OT_OR_GEOMETRY",
    "FOUNDATIONAL_COMPONENT",
    "COMPARATOR_OR_FAILURE_ANALYSIS",
    "APPLICATION_OR_DATASET",
    "PERIPHERAL_OR_BACKGROUND",
)
NOMINEES = (
    "arxiv:1902.02934",
    "arxiv:1905.10812",
    "arxiv:1906.09691",
    "arxiv:2102.02992",
    "arxiv:2205.15269",
)
NOMINEE_RATIONALES = {
    "arxiv:1902.02934": "direct title signal about failure and regularity of optimal transportation maps",
    "arxiv:1905.10812": "direct title signal about Brenier-potential regularity and optimal transport",
    "arxiv:1906.09691": "direct title signal about adversarial computation of optimal transport maps",
    "arxiv:2102.02992": "direct title signal about learned high-dimensional Wasserstein geodesics",
    "arxiv:2205.15269": "direct title signal about a kernel neural optimal-transport method",
}

DIRECT_PATTERNS = (
    r"optimal transport", r"transportation map", r"transport maps?",
    r"wasserstein", r"brenier", r"barycenter", r"functionals on the space of probabilities",
)
APPLICATION_PATTERNS = (
    r"dataset", r"image", r"color transfer", r"style transfer", r"domain adaptation",
    r"data augmentation", r"fruit recognition",
)
COMPARATOR_PATTERNS = (
    r"gan", r"adversarial", r"mode collapse", r"density estimation",
    r"convergence", r"stabiliz", r"regularization", r"cramer distance",
)
FOUNDATIONAL_PATTERNS = (
    r"normalizing flows?", r"invertible", r"variational inference",
    r"stein variational", r"optimal control", r"convex potential flows?",
)


def classify_unused_candidates(*, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        title = candidate.get("title")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen:
            raise MissionStateError("invalid_omission_candidate", "candidate ids must be nonempty and unique")
        if not isinstance(title, str) or not title.strip():
            raise MissionStateError("invalid_omission_candidate", "unused candidates require a title")
        identifiers = candidate.get("identifiers", [candidate_id])
        bibliography_key = candidate.get("bibliography_key")
        source_member = candidate.get("source_member")
        if (
            not isinstance(identifiers, list)
            or not identifiers
            or any(not isinstance(value, str) or not value for value in identifiers)
            or candidate_id not in identifiers
            or (bibliography_key is not None and not isinstance(bibliography_key, str))
            or (source_member is not None and not isinstance(source_member, str))
        ):
            raise MissionStateError("invalid_omission_candidate", "candidate bibliography provenance is invalid")
        seen.add(candidate_id)
        group, signals = _classify_title(title)
        rows.append({
            "candidate_id": candidate_id,
            "identifiers": identifiers,
            "bibliography_key": bibliography_key,
            "title": title,
            "source_member": source_member,
            "provisional_group": group,
            "classification_status": PROVISIONAL_STATUS,
            "title_signals": signals,
            "source_status": "SOURCE_NOT_INSPECTED",
            "technical_claim_support": "not_supported",
            "next_action": "inspect_primary_source_if_nominated_else_retain_grouped_omission_risk",
            "what_is_not_concluded": [
                "candidate relevance in fact", "technical role", "importance",
                "claim support", "publication safety", "literature completeness",
            ],
        })
    rows.sort(key=lambda row: row["candidate_id"])
    ids = {row["candidate_id"] for row in rows}
    missing_nominees = [candidate_id for candidate_id in NOMINEES if candidate_id not in ids]
    if missing_nominees:
        raise MissionStateError("omission_nominee_missing", f"nominees missing from frontier: {missing_nominees}")
    counts = Counter(row["provisional_group"] for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "complete_provisional_title_context_triage",
        "candidate_count": len(rows),
        "group_counts": {group: counts.get(group, 0) for group in GROUPS},
        "nominee_ids": list(NOMINEES),
        "rows": rows,
        "title_only": True,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": [
            "scholarly classification", "technical relevance", "importance",
            "claim support", "publication safety", "literature completeness",
        ],
    }


def validate_provisional_triage(value: Any, *, expected_ids: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise MissionStateError("invalid_omission_triage", "triage schema is unsupported")
    rows = value.get("rows")
    if not isinstance(rows, list) or value.get("candidate_count") != len(rows):
        raise MissionStateError("invalid_omission_triage", "triage row count is invalid")
    rebuilt = classify_unused_candidates(candidates=[
        {
            "candidate_id": row.get("candidate_id"),
            "identifiers": row.get("identifiers"),
            "bibliography_key": row.get("bibliography_key"),
            "title": row.get("title"),
            "source_member": row.get("source_member"),
        }
        for row in rows
    ])
    if value != rebuilt:
        raise MissionStateError("invalid_omission_triage", "triage does not replay from candidate ids and titles")
    if expected_ids is not None and {row["candidate_id"] for row in rows} != expected_ids:
        raise MissionStateError("invalid_omission_triage", "triage candidate set differs from expected frontier")
    return value


def build_inspection_queue(triage: dict[str, Any]) -> dict[str, Any]:
    validate_provisional_triage(triage)
    by_id = {row["candidate_id"]: row for row in triage["rows"]}
    rows = [{
        "queue_position": index,
        "candidate_id": candidate_id,
        "arxiv_id": candidate_id.removeprefix("arxiv:"),
        "title": by_id[candidate_id]["title"],
        "provisional_group": by_id[candidate_id]["provisional_group"],
        "selection_basis": "bounded_direct_title_context_omission_risk",
        "rationale": NOMINEE_RATIONALES[candidate_id],
        "source_request_limit": 1,
        "retry_limit": 0,
        "technical_claim_support": "not_supported_before_primary_source_inspection",
    } for index, candidate_id in enumerate(NOMINEES, start=1)]
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "status": "ready_for_bounded_primary_source_intake",
        "nomination_count": len(rows),
        "candidate_ids": list(NOMINEES),
        "rows": rows,
        "selection_is_ranking": False,
        "claim_support_allowed": False,
        "what_is_not_concluded": [
            "importance ranking", "technical relevance in fact", "claim support",
            "publication safety", "literature completeness",
        ],
    }


def validate_inspection_queue(value: Any, *, triage: dict[str, Any]) -> dict[str, Any]:
    expected = build_inspection_queue(triage)
    if value != expected:
        raise MissionStateError("invalid_omission_inspection_queue", "inspection queue does not replay from triage")
    return value


def _classify_title(title: str) -> tuple[str, list[str]]:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
    for group, patterns in (
        ("DIRECT_OT_OR_GEOMETRY", DIRECT_PATTERNS),
        ("APPLICATION_OR_DATASET", APPLICATION_PATTERNS),
        ("COMPARATOR_OR_FAILURE_ANALYSIS", COMPARATOR_PATTERNS),
        ("FOUNDATIONAL_COMPONENT", FOUNDATIONAL_PATTERNS),
    ):
        signals = [pattern for pattern in patterns if re.search(pattern, normalized)]
        if signals:
            return group, signals
    return "PERIPHERAL_OR_BACKGROUND", ["no_direct_title_signal"]


__all__ = [
    "GROUPS", "NOMINEES", "NOMINEE_RATIONALES", "PROVISIONAL_STATUS",
    "QUEUE_SCHEMA_VERSION", "SCHEMA_VERSION", "build_inspection_queue",
    "classify_unused_candidates", "validate_inspection_queue",
    "validate_provisional_triage",
]
