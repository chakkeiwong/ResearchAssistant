from __future__ import annotations

from pathlib import Path

import pytest

from research_assistant.survey.centrality import write_centrality_assessment
from research_assistant.survey.mission_plan import build_mission_plan, write_mission_plan_from_root
from research_assistant.survey.mission_state import MissionStateError, TOPIC_INPUT_MODE
from research_assistant.survey.mission_state import pretty_json_bytes
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


def _state(*, topic: bool = True, status: str = "ready_for_local_continuation") -> tuple[dict, dict]:
    mission_id = "11111111-1111-4111-8111-111111111111"
    fingerprint = "a" * 64
    generation = "g00000001-1111111111111111"
    mission = {
        "schema_version": "ra-survey-public-source-mission-control-v3" if topic else "ra-survey-public-source-mission-control-v2",
        "mission_id": mission_id,
        "mission_fingerprint": fingerprint,
        "generation_id": generation,
        "status": status,
        "topic": "A topic",
        "input_mode": TOPIC_INPUT_MODE if topic else "explicit_seed",
        "phase_statuses": {
            "source_intake": {"exists": False},
            "source_anchors": {"exists": False},
            "public_source_packet": {"exists": False},
        },
        "coverage_artifacts": {},
        "reviewed_artifacts": {},
        "final_artifacts": {},
        "public_discovery_confirmation": {"confirmed": True},
        "bootstrap_attempt_state": "selected_complete" if topic else "explicit_seed",
        "bootstrap_outcome": "selected" if topic else "accepted",
        "effective_seeds": ["arxiv:2401.00001"] if topic else ["arxiv:2401.00001"],
        "seeds": [] if topic else ["arxiv:2401.00001"],
    }
    action = {
        "mission_id": mission_id,
        "mission_fingerprint": fingerprint,
        "generation_id": generation,
        "action_id": "topic_bootstrap_selected_local_continuation" if topic else "source_intake",
        "status": "ready_for_local_continuation",
    }
    return mission, action


def test_topic_plan_preserves_metadata_boundary_and_prioritizes_identity() -> None:
    plan = build_mission_plan(*_state())
    assert plan["current_stage"] == "identity_resolution"
    assert plan["effective_seed_count"] == 1
    assert plan["stages"][0]["technical_claim_support"] is False
    assert "technical correctness" in plan["what_is_not_concluded"]
    assert plan["centrality"]["status"] == "pending"
    assert plan["centrality"]["metadata_nomination_is_validated_centrality"] is False


def test_explicit_plan_starts_at_source_resolution() -> None:
    mission, action = _state(topic=False)
    plan = build_mission_plan(mission, action)
    assert plan["current_stage"] == "source_resolution"
    assert plan["stages"][0]["status"] == "complete"


def test_plan_rejects_mismatched_authority() -> None:
    mission, action = _state()
    action["generation_id"] = "g00000001-2222222222222222"
    with pytest.raises(MissionStateError, match="generation_id"):
        build_mission_plan(mission, action)


def test_plan_from_existing_topic_mission_is_replayable(tmp_path: Path) -> None:
    source = tmp_path / "mission"
    run_public_source_workflow(topic="A topic", seeds=["arxiv:2401.00001"], output_dir=source, run_safe_local=True)
    result = write_mission_plan_from_root(mission_root=source)
    assert result["status"] in {"mission_plan_written", "mission_plan_reused"}
    assert result["plan"]["schema_version"] == "ra-survey-mission-plan-v2"
    assert result["plan"]["mission_id"]


def test_plan_projects_validated_centrality_without_gating_source_inspection(tmp_path: Path) -> None:
    source = tmp_path / "mission"
    run_public_source_workflow(
        topic="A topic",
        seeds=["arxiv:2401.00001"],
        output_dir=source,
        run_safe_local=True,
    )
    contract = build_topic_contract("A topic")
    evidence = {
        "schema_version": "ra-survey-centrality-evidence-v1",
        "topic_contract_sha256": topic_contract_sha256(contract),
        "candidates": [{
            "paper_id": "arxiv:2401.00001",
            "title": "A topic",
            "identity_status": "resolved",
            "source_status": "inspected",
            "source_safety": "clear",
            "topic_fit": "direct",
            "roles": ["DIRECT_METHOD"],
            "inspected_anchors": ["source:paper:method"],
            "discovery_routes": ["broad_facets", "exact_high_citation"],
            "backward_mentions": [],
            "forward_citations": ["openalex:citing-work"],
            "survey_mentions": [],
            "omission_risk_status": "none",
            "citation_count": None,
            "venue_metric_status": "not_available",
            "evidence_refs": ["source:paper:method"],
            "source_safety_evidence": ["metadata:openalex:is_retracted=false:2026-07-22"],
            "reviewer_provenance": ["review:mission-fixture"],
            "limitations": ["fixture evidence only"],
        }],
        "what_is_not_concluded": ["literature completeness"],
    }
    contract_path = source / "topic_contract.json"
    evidence_path = source / "centrality_evidence.json"
    contract_path.write_bytes(pretty_json_bytes(contract))
    evidence_path.write_bytes(pretty_json_bytes(evidence))
    write_centrality_assessment(
        topic_contract_path=contract_path,
        evidence_path=evidence_path,
        output_dir=source / "centrality",
    )

    result = write_mission_plan_from_root(mission_root=source)
    assert result["plan"]["current_stage"] == "source_resolution"
    assert result["plan"]["centrality"]["status"] == "complete"
    assert result["plan"]["centrality"]["validated_central_candidate_count"] == 1
    stage = next(
        row for row in result["plan"]["stages"]
        if row["stage_id"] == "centrality_assessment"
    )
    assert stage["status"] == "complete"
