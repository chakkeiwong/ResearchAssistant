from pathlib import Path

import pytest

from research_assistant.survey.campaign_process import (
    CAMPAIGN_PROCESS_SCHEMA,
    build_campaign_snapshot,
    build_process_plan,
    transition_state,
)
from research_assistant.survey.mission_state import MissionStateError


FIXTURE = Path("tests/fixtures/survey_campaign_process/baseline.json")


def _snapshot():
    import json

    return build_campaign_snapshot(json.loads(FIXTURE.read_text()))


def test_baseline_fixture_has_expected_canonical_shape() -> None:
    snapshot = _snapshot()
    assert snapshot.schema_version == CAMPAIGN_PROCESS_SCHEMA
    assert len(snapshot.papers) == 12
    assert len(snapshot.source_versions) == 5
    assert snapshot.selection_summary.substitution_count == 2
    assert snapshot.selection_summary.unreplaced_count == 7
    assert [row.paper_id for row in snapshot.papers] == sorted(row.paper_id for row in snapshot.papers)


def test_state_transitions_are_adjacent_only() -> None:
    assert transition_state("DISCOVERED", "IDENTITY_RESOLVED") == "IDENTITY_RESOLVED"
    with pytest.raises(MissionStateError, match="adjacent"):
        transition_state("DISCOVERED", "ACQUIRED")
    with pytest.raises(MissionStateError, match="blocked"):
        transition_state("SOURCE_BLOCKED", "ACQUIRED")


def test_process_plan_prioritizes_must_cite_then_declared_coverage_order() -> None:
    plan = build_process_plan(_snapshot())
    assert plan["status"] == "evidence_map_ready"
    assert plan["next_action"]["action_id"] == "resolve_must_cite_source"
    coverage_actions = [
        row for row in plan["candidate_actions"]
        if row["action_id"] == "resolve_coverage_gap"
    ]
    assert coverage_actions[0]["target_cell"] == "direct_product_or_card_recommendation"
    assert plan["coverage"]["gap_count"] >= 1
    assert plan["availability"]["evidence_count"] == 5
    assert plan["availability"]["access_or_omission_count"] == 7


def test_adjacent_finance_does_not_satisfy_direct_product_cell() -> None:
    coverage = build_process_plan(_snapshot())["coverage"]
    direct = next(row for row in coverage["cells"] if row["cell_id"] == "direct_product_or_card_recommendation")
    adjacent = next(row for row in coverage["cells"] if row["cell_id"] == "next_best_offer_or_financial_personalization")
    assert direct["status"] == "gap"
    assert adjacent["status"] == "covered"


def test_snapshot_rejects_unknown_cross_record_reference() -> None:
    import json

    value = json.loads(FIXTURE.read_text())
    value["claims"][0]["paper_id"] = "does-not-exist"
    with pytest.raises(MissionStateError, match="unknown paper reference"):
        build_campaign_snapshot(value)


def test_snapshot_is_order_independent() -> None:
    import json

    value = json.loads(FIXTURE.read_text())
    reversed_value = {**value, "papers": list(reversed(value["papers"])), "claims": list(reversed(value["claims"]))}
    assert build_campaign_snapshot(value).as_dict() == build_campaign_snapshot(reversed_value).as_dict()


def test_snapshot_rejects_undeclared_coverage_cell() -> None:
    import json

    value = json.loads(FIXTURE.read_text())
    value["papers"][0]["coverage_cells"] = ["hidden_domain_default"]
    with pytest.raises(MissionStateError, match="unknown coverage cells"):
        build_campaign_snapshot(value)


def test_snapshot_requires_unique_contiguous_coverage_priorities() -> None:
    import json

    value = json.loads(FIXTURE.read_text())
    value["coverage_requirements"][1]["priority"] = 1
    with pytest.raises(MissionStateError, match="ids and priorities must be unique"):
        build_campaign_snapshot(value)
