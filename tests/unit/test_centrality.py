from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research_assistant.survey.centrality import (
    assess_centrality,
    validate_centrality_evidence,
    validate_centrality_output,
    write_centrality_assessment,
)
from research_assistant.survey.mission_state import MissionStateError, pretty_json_bytes
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


def _candidate(
    paper_id: str,
    *,
    topic_fit: str = "direct",
    roles: list[str] | None = None,
    citation_count: int | None = 10,
) -> dict:
    return {
        "paper_id": paper_id,
        "title": paper_id,
        "identity_status": "resolved",
        "source_status": "inspected",
        "source_safety": "clear",
        "topic_fit": topic_fit,
        "roles": roles or ["DIRECT_METHOD"],
        "inspected_anchors": [f"source:{paper_id}:method"],
        "discovery_routes": ["broad_facets", "exact_high_citation"],
        "backward_mentions": [],
        "forward_citations": ["openalex:citing-work"],
        "survey_mentions": [],
        "omission_risk_status": "none",
        "citation_count": citation_count,
        "venue_metric_status": "not_available",
        "evidence_refs": [f"source:{paper_id}:method"],
        "source_safety_evidence": ["metadata:openalex:is_retracted=false:2026-07-22"],
        "reviewer_provenance": ["review:test-fixture"],
        "limitations": ["fixture evidence only"],
    }


def _evidence(contract: dict, rows: list[dict]) -> dict:
    return {
        "schema_version": "ra-survey-centrality-evidence-v1",
        "topic_contract_sha256": topic_contract_sha256(contract),
        "candidates": sorted(rows, key=lambda row: row["paper_id"]),
        "what_is_not_concluded": ["literature completeness", "paper claim correctness"],
    }


def test_centrality_truth_table_and_proxy_nonpromotion() -> None:
    contract = build_topic_contract("A generic topic")
    central = _candidate("central", citation_count=1)
    off_topic = _candidate("famous_off_topic", topic_fit="off_topic", citation_count=100_000)
    peripheral = _candidate("peripheral", topic_fit="peripheral", roles=["PERIPHERAL"], citation_count=50_000)
    result = assess_centrality(contract, _evidence(contract, [central, off_topic, peripheral]))
    verdicts = {row["paper_id"]: row["verdict"] for row in result["assessments"]}
    assert verdicts == {
        "central": "VALIDATED_CENTRAL",
        "famous_off_topic": "REJECTED_OFF_TOPIC",
        "peripheral": "PERIPHERAL",
    }
    assert result["metadata_priority_can_promote"] is False


@pytest.mark.parametrize(
    ("mutation", "verdict"),
    [
        ({"identity_status": "conflict"}, "BLOCKED"),
        ({"source_status": "metadata_only", "inspected_anchors": []}, "BLOCKED"),
        ({"source_safety": "quarantined", "roles": ["RETRACTED_OR_QUARANTINED"]}, "QUARANTINED"),
        ({"discovery_routes": ["only_one"]}, "VALIDATED_CENTRAL"),
        ({"forward_citations": []}, "VALIDATED_RELEVANT"),
    ],
)
def test_centrality_vetoes_and_independent_signal(mutation: dict, verdict: str) -> None:
    contract = build_topic_contract("A generic topic")
    row = _candidate("candidate")
    row.update(mutation)
    result = assess_centrality(contract, _evidence(contract, [row]))
    assert result["assessments"][0]["verdict"] == verdict


def test_centrality_evidence_rejects_foreign_contract_and_unknown_fields() -> None:
    contract = build_topic_contract("A generic topic")
    value = _evidence(contract, [_candidate("candidate")])
    value["topic_contract_sha256"] = "0" * 64
    with pytest.raises(MissionStateError, match="different topic contract"):
        validate_centrality_evidence(value, expected_contract_sha256=topic_contract_sha256(contract))
    value = _evidence(contract, [_candidate("candidate")])
    value["candidates"][0]["unknown"] = True
    with pytest.raises(MissionStateError, match="fields are not exact"):
        validate_centrality_evidence(value)


def test_metadata_only_off_topic_nomination_remains_blocked() -> None:
    contract = build_topic_contract("A generic topic")
    row = _candidate("uninspected", topic_fit="off_topic", citation_count=100_000)
    row.update({"source_status": "metadata_only", "source_safety": "not_checked", "inspected_anchors": []})
    result = assess_centrality(contract, _evidence(contract, [row]))
    assert result["assessments"][0]["verdict"] == "BLOCKED"


def test_multiple_metadata_routes_cannot_promote_centrality() -> None:
    contract = build_topic_contract("A generic topic")
    row = _candidate("route-only")
    row["forward_citations"] = []
    row["discovery_routes"] = ["broad_facets", "exact_high_citation", "survey_route"]
    result = assess_centrality(contract, _evidence(contract, [row]))
    assessment = result["assessments"][0]
    assert assessment["verdict"] == "VALIDATED_RELEVANT"
    assert assessment["diagnostics"]["discovery_routes_are_explanatory_only"] is True


def test_checked_statuses_require_safety_and_reviewer_provenance() -> None:
    contract = build_topic_contract("A generic topic")
    row = _candidate("missing-provenance")
    row["source_safety_evidence"] = []
    with pytest.raises(MissionStateError, match="source_safety_evidence is required"):
        assess_centrality(contract, _evidence(contract, [row]))

    row = _candidate("missing-reviewer")
    row["reviewer_provenance"] = []
    with pytest.raises(MissionStateError, match="reviewer_provenance must not be empty"):
        assess_centrality(contract, _evidence(contract, [row]))


def test_persisted_centrality_output_replays_and_rejects_tampering(tmp_path: Path) -> None:
    contract = build_topic_contract("A generic topic")
    contract_path = tmp_path / "topic.json"
    evidence_path = tmp_path / "evidence.json"
    output = tmp_path / "centrality"
    contract_path.write_bytes(pretty_json_bytes(contract))
    evidence_path.write_bytes(pretty_json_bytes(_evidence(contract, [_candidate("candidate")])))
    write_centrality_assessment(
        topic_contract_path=contract_path,
        evidence_path=evidence_path,
        output_dir=output,
    )
    replayed = validate_centrality_output(output, expected_topic="A generic topic")
    assert replayed["assessment"]["counts"]["VALIDATED_CENTRAL"] == 1

    assessment_path = output / "centrality_assessment.json"
    tampered = json.loads(assessment_path.read_text())
    tampered["counts"]["VALIDATED_CENTRAL"] = 2
    assessment_path.write_bytes(pretty_json_bytes(tampered))
    with pytest.raises(MissionStateError, match="differs from replayed evidence"):
        validate_centrality_output(output)


def test_persisted_centrality_output_rejects_foreign_topic(tmp_path: Path) -> None:
    contract = build_topic_contract("A generic topic")
    contract_path = tmp_path / "topic.json"
    evidence_path = tmp_path / "evidence.json"
    output = tmp_path / "centrality"
    contract_path.write_bytes(pretty_json_bytes(contract))
    evidence_path.write_bytes(pretty_json_bytes(_evidence(contract, [_candidate("candidate")])))
    write_centrality_assessment(
        topic_contract_path=contract_path,
        evidence_path=evidence_path,
        output_dir=output,
    )
    with pytest.raises(MissionStateError, match="different topic"):
        validate_centrality_output(output, expected_topic="Another topic")
