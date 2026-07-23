from __future__ import annotations

import json
from pathlib import Path

from research_assistant.cli import main
from research_assistant.survey.mission_state import pretty_json_bytes
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


def test_centrality_cli_writes_local_nonbenchmark_assessment(tmp_path: Path, capsys) -> None:
    contract = build_topic_contract("Neural Optimal Transport")
    evidence = {
        "schema_version": "ra-survey-centrality-evidence-v1",
        "topic_contract_sha256": topic_contract_sha256(contract),
        "candidates": [{
            "paper_id": "paper",
            "title": "Neural Optimal Transport",
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
            "citation_count": 1,
            "venue_metric_status": "not_available",
            "evidence_refs": ["source:paper:method"],
            "source_safety_evidence": ["metadata:openalex:is_retracted=false:2026-07-22"],
            "reviewer_provenance": ["review:cli-fixture"],
            "limitations": ["fixture evidence only"],
        }],
        "what_is_not_concluded": ["literature completeness"],
    }
    contract_path = tmp_path / "topic.json"
    evidence_path = tmp_path / "evidence.json"
    output = tmp_path / "assessment"
    contract_path.write_bytes(pretty_json_bytes(contract))
    evidence_path.write_bytes(pretty_json_bytes(evidence))

    code = main([
        "survey", "assess-centrality", "--topic-contract", str(contract_path),
        "--evidence", str(evidence_path), "--out", str(output),
    ])
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["status"] == "centrality_assessment_written"
    assessment = json.loads((output / "centrality_assessment.json").read_text())
    manifest = json.loads((output / "centrality_manifest.json").read_text())
    assert assessment["assessments"][0]["verdict"] == "VALIDATED_CENTRAL"
    assert manifest["benchmark_labels_consumed"] is False
