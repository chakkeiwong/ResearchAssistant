from __future__ import annotations

import json
from pathlib import Path

from research_assistant.benchmarks.surveybench import score_survey_task


ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tests" / "fixtures" / "surveybench" / "tasks" / "neural_ot_seed_synthetic.task.json"
ANCHOR_INVENTORY = ROOT / "tests" / "fixtures" / "surveybench" / "neural_ot_seed" / "anchor_inventory.json"


def _load_expected_packet() -> dict[str, object]:
    task = json.loads(TASK.read_text())
    packet: dict[str, object] = {}
    for name, rel_path in task["expected_outputs"].items():
        packet[name] = json.loads((TASK.parent / rel_path).resolve().read_text())
    return packet


def _write_packet(tmp_path: Path, packet: dict[str, object]) -> Path:
    for name, payload in packet.items():
        source_path = Path(json.loads(TASK.read_text())["expected_outputs"][name])
        (tmp_path / source_path.name).write_text(json.dumps(payload, indent=2, sort_keys=True))
    return tmp_path


def test_surveybench_anchor_inventory_points_to_existing_markers() -> None:
    inventory = json.loads(ANCHOR_INVENTORY.read_text())
    assert inventory["schema_version"] == "ra-surveybench-anchor-inventory-v1"
    for row in inventory["anchors"]:
        artifact = ANCHOR_INVENTORY.parent / row["artifact_path"]
        assert artifact.exists()
        assert row["marker_text"] in artifact.read_text()


def test_survey_benchmark_scores_gold_fixture_as_structurally_ready() -> None:
    report = score_survey_task(TASK)
    assert report["schema_version"] == "ra-surveybench-report-v1"
    assert report["status"] == "passed"
    assert report["scores"]["citation_map"]["required_node_recall"]["score"] == 1.0
    assert report["scores"]["citation_map"]["required_edge_recall"]["score"] == 1.0
    assert report["scores"]["citation_map"]["required_cluster_recall"]["score"] == 1.0
    assert report["scores"]["candidate_ledger"]["duplicate_case_recall"]["score"] == 1.0
    assert report["scores"]["candidate_ledger"]["excluded_false_positive_recall"]["score"] == 1.0
    assert report["scores"]["source_support"]["checked_anchor_recall"]["score"] == 1.0
    assert report["scores"]["claim_support"]["supported_claim_anchor_recall"]["score"] == 1.0
    assert report["diagnostics"]["resolved_anchor_count"] >= 3
    assert report["scores"]["claim_support"]["forbidden_claim_flags"] == [
        "claim_forbidden_dominance"
    ]
    assert report["vetoes"] == []


def test_survey_benchmark_vetoes_missing_citation_map(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    packet.pop("citation_map")
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "missing_citation_map" in report["vetoes"]
    assert "citation_map: missing output artifact" in report["errors"]


def test_survey_benchmark_vetoes_missing_required_edge(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    citation_map = packet["citation_map"]
    assert isinstance(citation_map, dict)
    citation_map["edges"] = citation_map["edges"][:-1]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "missing_required_edge" in report["vetoes"]
    missing = report["scores"]["citation_map"]["required_edge_recall"]["missing"]
    assert ["seed_neural_ot", "normalizing_flows_review", "adjacent_method"] in missing


def test_survey_benchmark_fails_missing_required_cluster(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    citation_map = packet["citation_map"]
    assert isinstance(citation_map, dict)
    citation_map["clusters"] = citation_map["clusters"][:-1]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    missing = report["scores"]["citation_map"]["required_cluster_recall"]["missing"]
    assert "adjacent_normalizing_flows" in missing


def test_survey_benchmark_fails_missing_required_candidate(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    candidate_ledger = packet["candidate_ledger"]
    assert isinstance(candidate_ledger, dict)
    candidate_ledger["included"] = candidate_ledger["included"][:-1]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    missing = report["scores"]["candidate_ledger"]["included_required_paper_recall"]["missing"]
    assert "normalizing_flows_review" in missing


def test_survey_benchmark_vetoes_forbidden_claim(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    claim_support = packet["claim_support"]
    assert isinstance(claim_support, dict)
    claim_support["claims"] = [
        {
            "anchors": [],
            "claim": "Neural optimal transport dominates all normalizing-flow methods.",
            "claim_id": "agent_forbidden_claim",
            "paper_keys": [],
            "status": "supported",
            "support_class": "fixture_source_support",
        }
    ]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "forbidden_claim" in report["vetoes"]
    assert report["scores"]["claim_support"]["forbidden_claim_hits"] == [
        "agent_forbidden_claim"
    ]


def test_survey_benchmark_vetoes_unsupported_nonforbidden_claim(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    claim_support = packet["claim_support"]
    assert isinstance(claim_support, dict)
    claim_support["claims"] = [
        {
            "anchors": [],
            "claim": "The synthetic method has a contraction proof in the fixture.",
            "claim_id": "agent_unsupported_claim",
            "paper_keys": ["seed_neural_ot"],
            "status": "unsupported",
            "support_class": "unsupported",
        }
    ]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["vetoes"]
    assert report["scores"]["claim_support"]["unsupported_nonforbidden_claims"] == [
        "agent_unsupported_claim"
    ]


def test_survey_benchmark_vetoes_nonclaim_inside_claim_rows(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    claim_support = packet["claim_support"]
    assert isinstance(claim_support, dict)
    claim_support["claims"].append({
        "anchors": [],
        "claim": "This offline fixture does not prove live-web completeness.",
        "claim_id": "nonclaim_live_web_completeness",
        "paper_keys": [],
        "status": "supported",
        "support_class": "fixture_source_support",
    })
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["vetoes"]
    assert report["scores"]["claim_support"]["nonclaim_rows_in_claims"] == [
        "nonclaim_live_web_completeness"
    ]


def test_survey_benchmark_accepts_nonclaim_metadata(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    claim_support = packet["claim_support"]
    assert isinstance(claim_support, dict)
    claim_support["what_is_not_concluded"] = [
        "live-web completeness",
        "scientific priority",
        "product readiness",
    ]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "passed"
    assert report["vetoes"] == []
    assert report["scores"]["claim_support"]["nonclaim_rows_in_claims"] == []
    assert report["scores"]["claim_support"]["claim_laundering_hits"] == []


def test_survey_benchmark_vetoes_claim_laundering_in_nonclaim_metadata(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    claim_support = packet["claim_support"]
    assert isinstance(claim_support, dict)
    first_claim = claim_support["claims"].pop(0)
    assert isinstance(first_claim, dict)
    claim_support["what_is_not_concluded"] = [first_claim["claim"]]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["vetoes"]
    assert report["scores"]["claim_support"]["claim_laundering_hits"] == [
        "$.what_is_not_concluded[0]"
    ]
    diagnostic_text = json.dumps(report["scores"]["claim_support"]["claim_laundering_hits"])
    assert "claim_seed_direct_method_role" not in diagnostic_text
    assert first_claim["claim"] not in diagnostic_text


def test_survey_benchmark_vetoes_missing_source_support_anchor(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    source_support = packet["source_support"]
    assert isinstance(source_support, dict)
    source_support["papers"][0]["checked_anchors"] = source_support["papers"][0]["checked_anchors"][:-1]
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "missing_anchor" in report["vetoes"]
    missing = report["scores"]["source_support"]["checked_anchor_recall"]["missing"]
    assert ["seed_neural_ot", "definition", "def:synthetic-map"] in missing


def test_survey_benchmark_vetoes_missing_supported_claim_anchor(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    claim_support = packet["claim_support"]
    assert isinstance(claim_support, dict)
    claim_support["claims"][0]["anchors"] = []
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert "missing_anchor" in report["vetoes"]
    missing = report["scores"]["claim_support"]["supported_claim_anchor_recall"]["missing"]
    assert ["seed_neural_ot", "section", "sec:synthetic-method"] in missing


def test_survey_benchmark_fails_missing_duplicate_and_false_positive_controls(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    candidate_ledger = packet["candidate_ledger"]
    assert isinstance(candidate_ledger, dict)
    candidate_ledger["duplicates"] = []
    candidate_ledger["excluded"] = []
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert report["scores"]["candidate_ledger"]["duplicate_case_recall"]["score"] == 0.0
    assert report["scores"]["candidate_ledger"]["excluded_false_positive_recall"]["score"] == 0.0


def test_survey_benchmark_fails_wrong_fixture_source_status(tmp_path: Path) -> None:
    packet = _load_expected_packet()
    source_support = packet["source_support"]
    assert isinstance(source_support, dict)
    source_support["papers"][0]["download_status"] = "not_attempted"
    actual_dir = _write_packet(tmp_path, packet)

    report = score_survey_task(TASK, actual_dir=actual_dir)

    assert report["status"] == "failed"
    assert report["scores"]["source_support"]["fixture_status_accuracy"]["score"] < 1.0
    mismatched = report["scores"]["source_support"]["fixture_status_accuracy"]["mismatched"]
    assert "seed_neural_ot:download_status" in mismatched
