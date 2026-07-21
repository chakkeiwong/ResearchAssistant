from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.omission_frontier_triage import NOMINEES
from research_assistant.survey.source_inspection import validate_source_inspection_bundle
from scripts.build_m22_omission_source_inspection import build_bundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_five_source_inspections_are_exact_grounded_and_nonpromoting() -> None:
    bundle = build_bundle()
    assert [row["candidate_id"] for row in bundle["rows"]] == list(NOMINEES)
    assert bundle["paper_count"] == 5
    assert bundle["claim_support_allowed"] is False
    assert bundle["ready_for_prose"] is False
    assert all(row["source_support_status"] == "PRIMARY_TECHNICAL_TEXT_INSPECTED" for row in bundle["rows"])
    assert all(row["official_code_status"] == "NOT_CHECKED" for row in bundle["rows"])
    assert validate_source_inspection_bundle(bundle, repository_root=REPOSITORY_ROOT) == bundle


def test_source_inspection_rejects_promotion_or_missing_evidence() -> None:
    bundle = build_bundle()
    promoted = deepcopy(bundle)
    promoted["rows"][0]["ready_for_prose"] = True
    with pytest.raises(MissionStateError, match="inspection row status is invalid"):
        validate_source_inspection_bundle(promoted, repository_root=REPOSITORY_ROOT)

    missing = deepcopy(bundle)
    missing["rows"][0]["evidence_refs"] = ["docs/missing.tex:1"]
    with pytest.raises(FileNotFoundError):
        validate_source_inspection_bundle(missing, repository_root=REPOSITORY_ROOT)


def test_source_inspection_rejects_cross_candidate_evidence_or_title_drift() -> None:
    bundle = build_bundle()
    crossed = deepcopy(bundle)
    crossed["rows"][0]["evidence_refs"] = crossed["rows"][1]["evidence_refs"]
    with pytest.raises(MissionStateError, match="not bound to its candidate source"):
        validate_source_inspection_bundle(crossed, repository_root=REPOSITORY_ROOT)

    renamed = deepcopy(bundle)
    renamed["rows"][0]["title"] = "A different title"
    with pytest.raises(MissionStateError, match="inspection row status is invalid"):
        validate_source_inspection_bundle(renamed, repository_root=REPOSITORY_ROOT)
