from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.m20_arxiv_backward_worker import extract_backward_reference_candidates
from research_assistant.survey.omission_frontier_triage import (
    NOMINEES,
    build_inspection_queue,
    classify_unused_candidates,
    validate_inspection_queue,
    validate_provisional_triage,
)


ROOT = Path("docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18")


def _production_unused() -> list[dict]:
    ledger = json.loads((ROOT / "packet/candidate_ledger.json").read_text())
    deferred = {
        row["candidate_id"] for row in ledger["included"]
        if row["nomination_status"] == "DEFERRED_RETAINED_AS_OMISSION_RISK"
    }
    retained = extract_backward_reference_candidates(
        ROOT / "human_review_packet/source_reading/2201_12220v3/unpacked/references.bib"
    )
    return [row for row in retained["candidates"] if row["candidate_id"] in deferred]


def test_production_frontier_classifies_exact_55_without_promotion() -> None:
    candidates = _production_unused()
    triage = classify_unused_candidates(candidates=candidates)
    assert triage["candidate_count"] == 55
    assert sum(triage["group_counts"].values()) == 55
    assert triage["nominee_ids"] == list(NOMINEES)
    assert triage["title_only"] is True
    assert triage["claim_support_allowed"] is False
    assert triage["ready_for_prose"] is False
    assert all(row["classification_status"] == "TITLE_CONTEXT_PROVISIONAL" for row in triage["rows"])
    assert all(row["candidate_id"] in row["identifiers"] for row in triage["rows"])
    assert validate_provisional_triage(
        triage, expected_ids={row["candidate_id"] for row in candidates},
    ) == triage
    queue = build_inspection_queue(triage)
    assert queue["candidate_ids"] == list(NOMINEES)
    assert [row["queue_position"] for row in queue["rows"]] == [1, 2, 3, 4, 5]
    assert all(row["source_request_limit"] == 1 for row in queue["rows"])
    assert all(row["retry_limit"] == 0 for row in queue["rows"])
    assert validate_inspection_queue(queue, triage=triage) == queue
    geodesics = next(row for row in triage["rows"] if row["candidate_id"] == "arxiv:2102.02992")
    assert geodesics["title"] == "Learning High Dimensional Wasserstein Geodesics"
    assert geodesics["bibliography_key"] == "liu2021learning"


@pytest.mark.parametrize(("title", "group"), [
    ("Kernel Neural Optimal Transport", "DIRECT_OT_OR_GEOMETRY"),
    ("Fashion-MNIST: a novel image dataset", "APPLICATION_OR_DATASET"),
    ("How Well Do WGANs Learn?", "COMPARATOR_OR_FAILURE_ANALYSIS"),
    ("Variational inference with normalizing flows", "FOUNDATIONAL_COMPONENT"),
    ("Online learning with exponential weights in metric spaces", "PERIPHERAL_OR_BACKGROUND"),
])
def test_title_rules_are_deterministic_and_explicit(title: str, group: str) -> None:
    candidates = [{"candidate_id": nominee, "title": title} for nominee in NOMINEES]
    triage = classify_unused_candidates(candidates=candidates)
    assert {row["provisional_group"] for row in triage["rows"]} == {group}


def test_duplicate_or_missing_nominee_is_rejected() -> None:
    with pytest.raises(MissionStateError) as exc:
        classify_unused_candidates(candidates=[
            {"candidate_id": "arxiv:1902.02934", "title": "A"},
            {"candidate_id": "arxiv:1902.02934", "title": "B"},
        ])
    assert exc.value.code == "invalid_omission_candidate"
    with pytest.raises(MissionStateError) as exc:
        classify_unused_candidates(candidates=[
            {"candidate_id": "arxiv:1902.02934", "title": "Optimal transport map"},
        ])
    assert exc.value.code == "omission_nominee_missing"
