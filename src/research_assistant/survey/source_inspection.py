"""Validation for bounded primary-source inspection records."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.omission_frontier_triage import NOMINEES


SCHEMA_VERSION = "ra-survey-source-inspection-bundle-v1"
ROW_SCHEMA_VERSION = "ra-survey-source-inspection-v1"
SOURCE_ROLES = {
    "DIRECT_METHOD",
    "REGULARIZED_DIRECT_METHOD",
    "COMPARATOR_OR_FAILURE_ANALYSIS",
}
EXPECTED_TITLES = {
    "arxiv:1902.02934": "Mode Collapse and Regularity of Optimal Transportation Maps",
    "arxiv:1905.10812": "Regularity as Regularization: Smooth and Strongly Convex Brenier Potentials in Optimal Transport",
    "arxiv:1906.09691": "Adversarial Computation of Optimal Transport Maps",
    "arxiv:2102.02992": "Learning High Dimensional Wasserstein Geodesics",
    "arxiv:2205.15269": "Kernel Neural Optimal Transport",
}
SOURCE_ROOT = Path(
    "docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates"
)
EVIDENCE_REF_RE = re.compile(r"^(?P<path>.+):(?P<line>[1-9][0-9]*)$")
LIST_FIELDS = (
    "method_findings",
    "theory_findings",
    "evaluation_findings",
    "merits",
    "concerns",
    "unresolved_uncertainties",
    "allowed_source_descriptions",
    "forbidden_claims",
    "evidence_refs",
)


def validate_source_inspection_bundle(
    value: Any, *, repository_root: Path | None = None
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise MissionStateError("invalid_source_inspection", "inspection bundle schema is unsupported")
    rows = value.get("rows")
    if (
        not isinstance(rows, list)
        or value.get("paper_count") != len(rows)
        or [row.get("candidate_id") for row in rows] != list(NOMINEES)
        or value.get("claim_support_allowed") is not False
        or value.get("ready_for_prose") is not False
    ):
        raise MissionStateError("invalid_source_inspection", "inspection bundle boundary is invalid")
    for row in rows:
        _validate_row(row, repository_root=repository_root)
    return value


def _validate_row(row: Any, *, repository_root: Path | None) -> None:
    required = {
        "schema_version", "candidate_id", "title", "source_role",
        "source_status", "inspection_status", "source_support_status",
        "method_findings", "theory_findings", "evaluation_findings",
        "merits", "concerns", "unresolved_uncertainties",
        "allowed_source_descriptions", "forbidden_claims", "evidence_refs",
        "official_code_status", "publication_retraction_status",
        "forward_citation_status", "claim_support_allowed", "ready_for_prose",
        "next_action",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise MissionStateError("invalid_source_inspection", "inspection row fields are not exact")
    if (
        row["schema_version"] != ROW_SCHEMA_VERSION
        or row["source_role"] not in SOURCE_ROLES
        or row["source_status"] != "LOCAL_ARXIV_TECHNICAL_SOURCE_AVAILABLE"
        or row["inspection_status"] != "METHOD_THEORY_EVALUATION_LIMITATIONS_INSPECTED"
        or row["source_support_status"] != "PRIMARY_TECHNICAL_TEXT_INSPECTED"
        or row["official_code_status"] != "NOT_CHECKED"
        or row["publication_retraction_status"] != "NOT_CHECKED"
        or row["forward_citation_status"] != "UNAVAILABLE_OUT_OF_SCOPE_NONBLOCKING"
        or row["claim_support_allowed"] is not False
        or row["ready_for_prose"] is not False
        or row["title"] != EXPECTED_TITLES.get(row["candidate_id"])
    ):
        raise MissionStateError("invalid_source_inspection", "inspection row status is invalid")
    for field in ("candidate_id", "title", "next_action"):
        if not isinstance(row[field], str) or not row[field].strip():
            raise MissionStateError("invalid_source_inspection", f"{field} must be nonempty")
    for field in LIST_FIELDS:
        values = row[field]
        if not isinstance(values, list) or not values or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            raise MissionStateError("invalid_source_inspection", f"{field} must be a nonempty text list")
    if repository_root is not None:
        candidate_directory = row["candidate_id"].removeprefix("arxiv:").replace(".", "_")
        expected_source_root = (
            repository_root / SOURCE_ROOT / candidate_directory / "source_members"
        ).resolve(strict=True)
        for reference in row["evidence_refs"]:
            match = EVIDENCE_REF_RE.fullmatch(reference)
            if match is None:
                raise MissionStateError("invalid_source_inspection", "evidence reference must end in a line number")
            path = (repository_root / match.group("path")).resolve(strict=True)
            if not path.is_relative_to(repository_root.resolve(strict=True)):
                raise MissionStateError("invalid_source_inspection", "evidence reference escapes repository")
            if not path.is_relative_to(expected_source_root):
                raise MissionStateError("invalid_source_inspection", "evidence reference is not bound to its candidate source")
            line = int(match.group("line"))
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                if sum(1 for _ in handle) < line:
                    raise MissionStateError("invalid_source_inspection", "evidence line exceeds source length")


__all__ = [
    "EXPECTED_TITLES", "ROW_SCHEMA_VERSION", "SCHEMA_VERSION", "SOURCE_ROLES",
    "validate_source_inspection_bundle",
]
