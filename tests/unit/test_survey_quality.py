from __future__ import annotations

import json
import shutil
from pathlib import Path

from research_assistant.benchmarks.replay import replay_call
from research_assistant.benchmarks.survey_quality import score_survey_prose


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "surveybench" / "online_replay" / "transport_hmc_dsge_replay"
TASK = FIXTURE / "transport_hmc_dsge_replay.task.json"


def _copy_packet(tmp_path: Path, *, source: Path | None = None) -> Path:
    actual = tmp_path / "actual"
    actual.mkdir()
    packet_source = source or FIXTURE / "scorer_packet"
    for path in packet_source.glob("*.json"):
        shutil.copy(path, actual / path.name)
    return actual


def _event_log(tmp_path: Path) -> Path:
    session = tmp_path / "session"
    for endpoint in ["search", "references", "citations", "adjacent", "download-status", "source-anchors"]:
        replay_call(TASK, endpoint, session)
    return session / "event_log.json"


def _positive_prose() -> dict[str, object]:
    return {
        "schema_version": "ra-surveybench-survey-prose-v1",
        "task_id": "transport_hmc_dsge_replay",
        "claim_trace": [
            {
                "anchors": [
                    {
                        "kind": "section",
                        "label": "sec:transport-hmc-method",
                        "paper_key": "thmc_seed_001",
                    }
                ],
                "claim": "The synthetic seed is the central transport-assisted HMC method node for this benchmark task.",
                "claim_id": "claim_transport_hmc_seed_method_node",
                "paper_keys": ["thmc_seed_001"],
                "status": "supported",
                "support_class": "fixture_source_support",
            },
            {
                "anchors": [
                    {
                        "kind": "equation",
                        "label": "eq:transport-map-jacobian",
                        "paper_key": "thmc_seed_001",
                    },
                    {
                        "kind": "algorithm",
                        "label": "alg:transport-hmc-transition",
                        "paper_key": "thmc_seed_001",
                    },
                ],
                "claim": "The fixture exposes transport-map and HMC-transition anchors for claim-support testing.",
                "claim_id": "claim_transport_hmc_anchor_support",
                "paper_keys": ["thmc_seed_001"],
                "status": "supported",
                "support_class": "fixture_source_support",
            },
            {
                "anchors": [
                    {
                        "kind": "citation_map_edge",
                        "label": "thmc_cite_001->thmc_seed_001",
                        "paper_key": "thmc_cite_001",
                    }
                ],
                "claim": "The replay citation surface marks thmc_cite_001 as citing the synthetic seed.",
                "claim_id": "claim_transport_hmc_forward_citation",
                "paper_keys": ["thmc_cite_001", "thmc_seed_001"],
                "status": "supported",
                "support_class": "fixture_graph_support",
            },
        ],
        "source_status_caveats": [
            {"paper_key": "thmc_ref_001", "caveat": "metadata-only lineage context"},
            {"paper_key": "thmc_ref_002", "caveat": "metadata-only lineage context"},
            {"paper_key": "thmc_cite_001", "caveat": "metadata-only forward citation"},
            {"paper_key": "thmc_adj_001", "caveat": "metadata-only adjacent context"},
            {"paper_key": "thmc_proxy_001", "caveat": "proxy-only benchmark context"},
        ],
        "addressed_omission_risks": [
            "thmc_ref_001",
            "thmc_ref_002",
            "thmc_adj_001",
            "thmc_proxy_001",
        ],
        "what_is_not_concluded": [
            "live-web coverage is not concluded",
            "current citation counts are not concluded",
            "download reliability is not concluded",
            "survey completeness is not concluded",
            "product readiness is not concluded",
            "scientific correctness is not concluded",
        ],
        "prose_quality": {
            "readability": "clear",
            "organization": "claim trace first",
        },
    }


def _write_prose(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "survey_prose.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def test_survey_quality_passes_after_packet_gate_and_grounded_prose(tmp_path: Path) -> None:
    actual = _copy_packet(tmp_path)
    prose = _write_prose(tmp_path, _positive_prose())

    report = score_survey_prose(TASK, actual, _event_log(tmp_path), FIXTURE / "scorer_packet", prose)

    assert report["schema_version"] == "ra-surveybench-survey-prose-score-v1"
    assert report["status"] == "passed"
    assert report["packet_gate"]["status"] == "passed"
    assert report["hard_gate_vetoes"] == []
    assert report["primary_scores"]["required_claim_recall"]["score"] == 1.0
    assert report["primary_scores"]["source_status_caveat_recall"]["score"] == 1.0
    assert report["primary_scores"]["omission_risk_recall"]["score"] == 1.0


def test_survey_quality_blocks_when_packet_gate_fails(tmp_path: Path) -> None:
    actual = _copy_packet(tmp_path, source=FIXTURE / "negative_packets" / "proxy_benchmark_promotion")
    prose = _write_prose(tmp_path, _positive_prose())

    report = score_survey_prose(TASK, actual, _event_log(tmp_path), FIXTURE / "scorer_packet", prose)

    assert report["status"] == "failed"
    assert report["packet_gate"]["status"] == "failed"
    assert report["hard_gate_vetoes"] == ["evidence_packet_failed"]


def test_survey_quality_rejects_unsupported_prose_claim(tmp_path: Path) -> None:
    actual = _copy_packet(tmp_path)
    payload = _positive_prose()
    claim_trace = payload["claim_trace"]
    assert isinstance(claim_trace, list)
    claim_trace.append({
        "anchors": [],
        "claim": "Benchmark proxy scores prove the default sampler choice.",
        "claim_id": "claim_proxy_default_sampler_support",
        "paper_keys": ["thmc_proxy_001"],
        "status": "supported",
        "support_class": "benchmark_proxy",
    })
    prose = _write_prose(tmp_path, payload)

    report = score_survey_prose(TASK, actual, _event_log(tmp_path), FIXTURE / "scorer_packet", prose)

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["hard_gate_vetoes"]
    assert "metadata_promoted_to_truth_evidence" in report["hard_gate_vetoes"]
    assert "claim_proxy_default_sampler_support" in report["primary_scores"]["required_claim_recall"]["unsupported_claim_ids"]


def test_survey_quality_rejects_missing_source_caveat_and_omission(tmp_path: Path) -> None:
    actual = _copy_packet(tmp_path)
    payload = _positive_prose()
    payload["source_status_caveats"] = [
        {"paper_key": "thmc_ref_001", "caveat": "metadata-only lineage context"}
    ]
    payload["addressed_omission_risks"] = ["thmc_ref_001"]
    prose = _write_prose(tmp_path, payload)

    report = score_survey_prose(TASK, actual, _event_log(tmp_path), FIXTURE / "scorer_packet", prose)

    assert report["status"] == "failed"
    assert "source_status_overclaim" in report["hard_gate_vetoes"]
    assert "omission_risk_unaddressed" in report["hard_gate_vetoes"]
    assert "thmc_proxy_001" in report["primary_scores"]["source_status_caveat_recall"]["missing"]
    assert "thmc_proxy_001" in report["primary_scores"]["omission_risk_recall"]["missing"]


def test_survey_quality_rejects_missing_nonclaims(tmp_path: Path) -> None:
    actual = _copy_packet(tmp_path)
    payload = _positive_prose()
    payload["what_is_not_concluded"] = ["live-web coverage is not concluded"]
    prose = _write_prose(tmp_path, payload)

    report = score_survey_prose(TASK, actual, _event_log(tmp_path), FIXTURE / "scorer_packet", prose)

    assert report["status"] == "failed"
    assert "missing_nonclaims" in report["hard_gate_vetoes"]
    assert "product readiness" in report["primary_scores"]["nonclaim_recall"]["missing"]
