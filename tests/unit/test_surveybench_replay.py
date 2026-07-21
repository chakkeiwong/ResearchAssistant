from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
from pathlib import Path

import pytest

from research_assistant.benchmarks.replay import (
    REPLAY_EVENT_LOG_SCHEMA_VERSION,
    REPLAY_RUBRIC_SCHEMA_VERSION,
    REPLAY_TASK_SCHEMA_VERSION,
    ReplayBenchmarkError,
    assert_replay_event_log_valid,
    assert_replay_task_valid,
    build_replay_transcript,
    replay_call,
    score_replay_submission,
    validate_replay_event_log_payload,
    validate_replay_fixture_interface,
    validate_replay_transcript_payload,
    validate_replay_task_payload,
)

ROOT = Path(__file__).resolve().parents[2]
REPLAY_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "surveybench"
    / "online_replay"
    / "neural_ot_seed_replay"
)
STRESS_REPLAY_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "surveybench"
    / "online_replay"
    / "neural_ot_seed_ambiguity_partial_frontier_replay"
)
TRANSPORT_HMC_REPLAY_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "surveybench"
    / "online_replay"
    / "transport_hmc_dsge_replay"
)


def _budget(endpoint_calls: int = 12) -> dict[str, int]:
    return {
        "endpoint_calls": endpoint_calls,
        "returned_records": 60,
        "paper_detail_calls": 10,
        "source_anchor_calls": 8,
        "submit_or_score_attempts": 2,
    }


def _valid_task() -> dict[str, object]:
    return {
        "schema_version": REPLAY_TASK_SCHEMA_VERSION,
        "task_id": "neural_ot_seed_replay",
        "topic": "Neural Optimal Transport for generative modeling and inference",
        "seed_papers": [
            {
                "paper_key": "korotin_2022_neural_optimal_transport",
                "identifier": "arxiv:2201.12220v3",
            }
        ],
        "endpoints": {
            "search": "responses/search.json",
            "paper": "responses/paper.json",
            "references": "responses/references.json",
            "citations": "responses/citations.json",
            "adjacent": "responses/adjacent.json",
            "download-status": "responses/download_status.json",
            "source-status": "responses/source_status.json",
            "source-anchors": "responses/source_anchors.json",
            "evidence-context": "responses/evidence_context.json",
        },
        "budget": _budget(),
        "evidence_channels": {
            "candidate_ledger": ["search", "paper"],
            "citation_map": ["search", "paper", "references", "citations", "adjacent"],
            "source_support": ["download-status", "source-status", "source-anchors"],
            "paper_classifications": ["paper", "references", "citations", "adjacent"],
            "claim_support": ["source-anchors", "evidence-context"],
            "omission_risk": ["search", "references", "citations", "adjacent"],
            "budget_compliance": ["event_log"],
        },
        "rubric": {
            "schema_version": REPLAY_RUBRIC_SCHEMA_VERSION,
            "classification_labels": [
                "seed",
                "foundational",
                "direct_method",
                "competitor",
                "survey_or_tutorial",
                "adjacent_method",
                "source_blocked",
            ],
            "edge_types": ["cites", "cited_by", "adjacent_method"],
            "source_statuses": ["available_fixture", "metadata_only_fixture", "blocked_fixture"],
            "download_statuses": ["downloaded_fixture", "not_attempted", "blocked_fixture"],
            "support_classes": [
                "fixture_source_support",
                "survey_context_only",
                "unsupported",
                "insufficient_evidence",
            ],
            "omission_risk_severities": ["low", "medium", "high"],
            "multi_label_fields": ["paper_classifications"],
            "exact_match_fields": ["required_edges", "source_statuses"],
            "partial_credit_fields": ["paper_classifications", "omission_risks"],
            "ambiguity": {"allow_insufficient_evidence": True},
        },
    }


def _valid_event_log() -> dict[str, object]:
    return {
        "schema_version": REPLAY_EVENT_LOG_SCHEMA_VERSION,
        "task_id": "neural_ot_seed_replay",
        "session_manifest": "session_manifest.json",
        "events": [
            {
                "sequence": 1,
                "endpoint": "search",
                "request_id": "req-search-1",
                "budget_before": _budget(endpoint_calls=12),
                "budget_after": _budget(endpoint_calls=11),
                "result_count": 5,
                "status": "ok",
                "agent_visible": True,
                "hidden_gold_accessed": False,
            }
        ],
    }


def _codes(report: dict[str, object]) -> set[str]:
    return {str(issue["code"]) for issue in report["issues"]}  # type: ignore[index]


def test_valid_replay_task_contract_passes() -> None:
    report = validate_replay_task_payload(_valid_task())

    assert report["schema_version"] == "ra-surveybench-online-replay-validation-report-v1"
    assert report["status"] == "passed"
    assert report["issues"] == []


def test_replay_task_rejects_agent_visible_hidden_gold() -> None:
    task = _valid_task()
    task["expected_outputs"] = {"citation_map": "expected_citation_map.json"}
    task["hidden_gold"] = {"gold_packet": "hidden_gold/packet.json"}

    report = validate_replay_task_payload(task)

    assert report["status"] == "failed"
    codes = _codes(report)
    assert "agent_visible_gold_key" in codes
    assert "agent_visible_gold_value" in codes


def test_replay_task_requires_evidence_channel_for_each_scored_field() -> None:
    task = _valid_task()
    channels = task["evidence_channels"]
    assert isinstance(channels, dict)
    channels.pop("claim_support")

    report = validate_replay_task_payload(task)

    assert report["status"] == "failed"
    assert "missing_evidence_channel" in _codes(report)


def test_replay_task_rejects_unknown_evidence_endpoint() -> None:
    task = _valid_task()
    channels = task["evidence_channels"]
    assert isinstance(channels, dict)
    channels["omission_risk"] = ["live_google_scholar"]

    report = validate_replay_task_payload(task)

    assert report["status"] == "failed"
    assert "unknown_evidence_endpoint" in _codes(report)


def test_replay_task_allows_explicit_insufficient_evidence_fallback() -> None:
    task = _valid_task()
    channels = task["evidence_channels"]
    assert isinstance(channels, dict)
    channels["claim_support"] = {
        "status": "insufficient_evidence",
        "reason": "sanitized replay fixture does not expose source anchors",
    }

    report = validate_replay_task_payload(task)

    assert report["status"] == "passed"


def test_replay_task_rejects_incomplete_rubric() -> None:
    task = _valid_task()
    rubric = task["rubric"]
    assert isinstance(rubric, dict)
    rubric["classification_labels"] = []
    rubric["ambiguity"] = {"allow_insufficient_evidence": False}

    report = validate_replay_task_payload(task)

    assert report["status"] == "failed"
    codes = _codes(report)
    assert "field_empty" in codes
    assert "insufficient_evidence_not_allowed" in codes


def test_replay_task_rejects_scorer_endpoint_exposure() -> None:
    task = _valid_task()
    endpoints = task["endpoints"]
    assert isinstance(endpoints, dict)
    endpoints["score"] = "responses/score.json"

    report = validate_replay_task_payload(task)

    assert report["status"] == "failed"
    assert "scorer_endpoint_exposed" in _codes(report)


def test_valid_replay_event_log_contract_passes() -> None:
    report = validate_replay_event_log_payload(_valid_event_log(), expected_task_id="neural_ot_seed_replay")

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_replay_event_log_rejects_agent_visible_hidden_gold_access() -> None:
    event_log = _valid_event_log()
    events = event_log["events"]
    assert isinstance(events, list)
    event = events[0]
    assert isinstance(event, dict)
    event["hidden_gold_accessed"] = True

    report = validate_replay_event_log_payload(event_log)

    assert report["status"] == "failed"
    assert "agent_visible_hidden_gold_access" in _codes(report)


def test_replay_event_log_rejects_missing_budget_counter() -> None:
    event_log = _valid_event_log()
    events = event_log["events"]
    assert isinstance(events, list)
    event = events[0]
    assert isinstance(event, dict)
    budget_after = event["budget_after"]
    assert isinstance(budget_after, dict)
    budget_after.pop("returned_records")

    report = validate_replay_event_log_payload(event_log)

    assert report["status"] == "failed"
    assert "invalid_budget_counter" in _codes(report)


def test_replay_event_log_rejects_budget_counter_increase() -> None:
    event_log = _valid_event_log()
    events = event_log["events"]
    assert isinstance(events, list)
    event = events[0]
    assert isinstance(event, dict)
    event["budget_after"] = deepcopy(event["budget_before"])
    budget_after = event["budget_after"]
    assert isinstance(budget_after, dict)
    budget_after["endpoint_calls"] = 99

    report = validate_replay_event_log_payload(event_log)

    assert report["status"] == "failed"
    assert "budget_counter_increased" in _codes(report)


def test_assert_helpers_raise_on_invalid_payloads() -> None:
    task = _valid_task()
    task["budget"] = {}
    with pytest.raises(ReplayBenchmarkError):
        assert_replay_task_valid(task)

    event_log = _valid_event_log()
    event_log["task_id"] = "wrong"
    with pytest.raises(ReplayBenchmarkError):
        assert_replay_event_log_valid(event_log, expected_task_id="neural_ot_seed_replay")


def test_online_replay_fixture_task_validates() -> None:
    task_path = REPLAY_FIXTURE / "neural_ot_seed_replay.task.json"
    task = json.loads(task_path.read_text())

    report = validate_replay_task_payload(task, artifact_path=task_path)

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_online_replay_fixture_endpoint_paths_exist_and_match_task() -> None:
    task = json.loads((REPLAY_FIXTURE / "neural_ot_seed_replay.task.json").read_text())
    endpoints = task["endpoints"]
    assert isinstance(endpoints, dict)

    for endpoint_name, rel_path in endpoints.items():
        path = REPLAY_FIXTURE / str(rel_path)
        assert path.exists(), endpoint_name
        payload = json.loads(path.read_text())
        assert payload["schema_version"] == "ra-surveybench-online-replay-response-v1"
        assert payload["task_id"] == "neural_ot_seed_replay"
        assert payload["endpoint"] == endpoint_name


def test_online_replay_fixture_agent_visible_files_do_not_leak_scorer_packet() -> None:
    visible_files = [
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        *sorted((REPLAY_FIXTURE / "responses").glob("*.json")),
    ]
    forbidden = [
        "expected_outputs",
        "expected_citation_map",
        "expected_claim_support",
        "expected_source_support",
        "expected_omission_risk",
        "hidden_gold",
        "gold_packet",
        "answer_key",
        "scorer_packet",
    ]

    for path in visible_files:
        text = path.read_text().lower()
        assert all(token not in text for token in forbidden), path


def test_online_replay_fixture_scorer_packet_is_separate_from_agent_visible_task() -> None:
    task = json.loads((REPLAY_FIXTURE / "neural_ot_seed_replay.task.json").read_text())
    endpoint_paths = {REPLAY_FIXTURE / str(rel_path) for rel_path in task["endpoints"].values()}
    scorer_paths = set((REPLAY_FIXTURE / "scorer_packet").glob("*.json"))

    assert scorer_paths
    assert endpoint_paths.isdisjoint(scorer_paths)


def test_replay_call_returns_response_and_appends_event_log(tmp_path: Path) -> None:
    task_path = REPLAY_FIXTURE / "neural_ot_seed_replay.task.json"

    result = replay_call(task_path, "search", tmp_path)

    assert result["schema_version"] == "ra-surveybench-online-replay-call-result-v1"
    assert result["status"] == "simulated_rate_limit"
    assert result["response"]["endpoint"] == "search"
    event_log = json.loads((tmp_path / "event_log.json").read_text())
    assert_replay_event_log_valid(event_log, expected_task_id="neural_ot_seed_replay")
    assert event_log["events"][0]["endpoint"] == "search"
    assert event_log["events"][0]["hidden_gold_accessed"] is False
    assert event_log["events"][0]["budget_after"]["endpoint_calls"] == 23


def test_replay_call_blocks_over_budget_and_logs_block(tmp_path: Path) -> None:
    task = _valid_task()
    task["budget"] = _budget(endpoint_calls=0)
    task_path = tmp_path / "tiny_budget.task.json"
    task_path.write_text(json.dumps(task, indent=2, sort_keys=True))
    responses = tmp_path / "responses"
    responses.mkdir()
    (responses / "search.json").write_text(json.dumps({
        "schema_version": "ra-surveybench-online-replay-response-v1",
        "task_id": "neural_ot_seed_replay",
        "endpoint": "search",
        "request_id": "tiny-budget-search",
        "results": [],
    }))

    result = replay_call(task_path, "search", tmp_path / "session")

    assert result["status"] == "blocked_budget"
    event_log = json.loads((tmp_path / "session" / "event_log.json").read_text())
    assert event_log["events"][0]["status"] == "blocked_budget"
    assert event_log["events"][0]["budget_before"] == event_log["events"][0]["budget_after"]


def test_replay_fixture_interface_audit_passes() -> None:
    report = validate_replay_fixture_interface(REPLAY_FIXTURE / "neural_ot_seed_replay.task.json")

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_replay_call_serializes_concurrent_event_log_writes(tmp_path: Path) -> None:
    task_path = REPLAY_FIXTURE / "neural_ot_seed_replay.task.json"
    endpoints = ["references", "citations", "adjacent", "download-status"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda endpoint: replay_call(task_path, endpoint, tmp_path), endpoints))

    assert {result["endpoint"] for result in results} == set(endpoints)
    event_log = json.loads((tmp_path / "event_log.json").read_text())
    assert_replay_event_log_valid(event_log, expected_task_id="neural_ot_seed_replay")
    assert len(event_log["events"]) == 4
    assert sorted(event["sequence"] for event in event_log["events"]) == [1, 2, 3, 4]


def _copy_scorer_packet(tmp_path: Path) -> Path:
    actual_dir = tmp_path / "actual"
    actual_dir.mkdir()
    for path in (REPLAY_FIXTURE / "scorer_packet").glob("*.json"):
        shutil.copy(path, actual_dir / path.name)
    return actual_dir


def _copy_packet(fixture: Path, tmp_path: Path) -> Path:
    actual_dir = tmp_path / "actual"
    actual_dir.mkdir()
    for path in (fixture / "scorer_packet").glob("*.json"):
        shutil.copy(path, actual_dir / path.name)
    return actual_dir


def _complete_event_log(tmp_path: Path) -> Path:
    session = tmp_path / "session"
    task_path = REPLAY_FIXTURE / "neural_ot_seed_replay.task.json"
    for endpoint in ["search", "references", "citations", "adjacent", "download-status", "source-anchors"]:
        replay_call(task_path, endpoint, session)
    return session / "event_log.json"


def _complete_event_log_for_fixture(fixture: Path, task_name: str, tmp_path: Path) -> Path:
    session = tmp_path / "session"
    task_path = fixture / task_name
    for endpoint in ["search", "references", "citations", "adjacent", "download-status", "source-anchors"]:
        replay_call(task_path, endpoint, session)
    return session / "event_log.json"


def _assert_intended_stress_failure(report: dict[str, object]) -> None:
    vetoes = set(report["vetoes"])  # type: ignore[arg-type]
    assert report["status"] == "failed"
    assert "missing_event_log" not in vetoes
    assert "invalid_event_log" not in vetoes
    assert "untrusted_event_log" not in vetoes
    assert "gold_actual_overlap" not in vetoes
    assert "missing_packet_file" not in vetoes


def test_replay_score_passes_gold_equivalent_packet_with_valid_event_log(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["schema_version"] == "ra-surveybench-online-replay-score-report-v1"
    assert report["status"] == "passed"
    assert report["vetoes"] == []
    assert report["scores"]["event_log"]["required_call_recall"]["score"] == 1.0


def test_replay_score_vetoes_missing_event_log(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        tmp_path / "missing_event_log.json",
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "missing_event_log" in report["vetoes"]


def test_replay_score_vetoes_missing_required_call(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    session = tmp_path / "session"
    replay_call(REPLAY_FIXTURE / "neural_ot_seed_replay.task.json", "search", session)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        session / "event_log.json",
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "missing_required_call" in report["vetoes"]


def test_replay_score_vetoes_budget_block_event(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    event_log = _complete_event_log(tmp_path)
    log = json.loads(event_log.read_text())
    log["events"].append({
        **log["events"][-1],
        "sequence": len(log["events"]) + 1,
        "endpoint": "search",
        "request_id": "forced-block",
        "status": "blocked_budget",
    })
    event_log.write_text(json.dumps(log, indent=2, sort_keys=True))

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "budget_exceeded" in report["vetoes"]


def test_replay_score_vetoes_prose_only_submission(tmp_path: Path) -> None:
    actual_dir = tmp_path / "actual"
    actual_dir.mkdir()
    (actual_dir / "survey.md").write_text("A nice paragraph without structured ledgers.")
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "prose_only_submission" in report["vetoes"]
    assert "missing_packet_file" in report["vetoes"]


def test_replay_score_vetoes_unsupported_claim(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    claim_path = actual_dir / "claim_support.json"
    claim_support = json.loads(claim_path.read_text())
    claim_support["claims"].append({
        "anchors": [],
        "claim": "The replay fixture proves a real convergence theorem.",
        "claim_id": "unsupported_real_theorem",
        "paper_keys": ["p_seed_001"],
        "status": "unsupported",
        "support_class": "unsupported",
    })
    claim_path.write_text(json.dumps(claim_support, indent=2, sort_keys=True))
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["vetoes"]


def test_replay_score_vetoes_nonclaim_inside_claim_rows(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    claim_path = actual_dir / "claim_support.json"
    claim_support = json.loads(claim_path.read_text())
    claim_support["claims"].append({
        "anchors": [],
        "claim": "This replay fixture does not prove live-web completeness.",
        "claim_id": "nonclaim_live_web_completeness",
        "paper_keys": [],
        "status": "supported",
        "support_class": "fixture_source_support",
    })
    claim_path.write_text(json.dumps(claim_support, indent=2, sort_keys=True))
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["vetoes"]
    assert report["scores"]["claim_support"]["nonclaim_rows_in_claims"] == [
        "nonclaim_live_web_completeness"
    ]


def test_replay_score_accepts_nonclaim_metadata(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    claim_path = actual_dir / "claim_support.json"
    claim_support = json.loads(claim_path.read_text())
    claim_support["what_is_not_concluded"] = [
        "live-web completeness",
        "scientific priority",
        "product readiness",
    ]
    claim_path.write_text(json.dumps(claim_support, indent=2, sort_keys=True))
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "passed"
    assert report["vetoes"] == []
    assert report["scores"]["claim_support"]["nonclaim_rows_in_claims"] == []
    assert report["scores"]["claim_support"]["claim_laundering_hits"] == []


def test_replay_score_vetoes_claim_laundering_in_nonclaim_metadata(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    claim_path = actual_dir / "claim_support.json"
    claim_support = json.loads(claim_path.read_text())
    first_claim = claim_support["claims"].pop(0)
    claim_support["what_is_not_concluded"] = [first_claim["claim"]]
    claim_path.write_text(json.dumps(claim_support, indent=2, sort_keys=True))
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "unsupported_technical_claim" in report["vetoes"]
    assert report["scores"]["claim_support"]["claim_laundering_hits"] == [
        "$.what_is_not_concluded[0]"
    ]
    diagnostic_text = json.dumps(report["scores"]["claim_support"]["claim_laundering_hits"])
    assert "claim_seed_method_node" not in diagnostic_text
    assert first_claim["claim"] not in diagnostic_text


def test_replay_score_rejects_untrusted_handwritten_event_log(tmp_path: Path) -> None:
    actual_dir = _copy_scorer_packet(tmp_path)
    event_log = tmp_path / "event_log.json"
    event_log.write_text(json.dumps(_valid_event_log(), indent=2, sort_keys=True))

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        actual_dir,
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "untrusted_event_log" in report["vetoes"]


def test_replay_score_rejects_actual_dir_overlapping_gold_dir(tmp_path: Path) -> None:
    event_log = _complete_event_log(tmp_path)

    report = score_replay_submission(
        REPLAY_FIXTURE / "neural_ot_seed_replay.task.json",
        REPLAY_FIXTURE / "scorer_packet",
        event_log,
        REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["status"] == "failed"
    assert "gold_actual_overlap" in report["vetoes"]


def test_stress_replay_fixture_task_validates() -> None:
    task_path = STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
    task = json.loads(task_path.read_text())

    report = validate_replay_task_payload(task, artifact_path=task_path)

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_stress_replay_fixture_interface_audit_passes() -> None:
    report = validate_replay_fixture_interface(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
    )

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_stress_replay_fixture_exposes_ambiguity_and_partial_frontier_signals() -> None:
    search = json.loads((STRESS_REPLAY_FIXTURE / "responses" / "search.json").read_text())
    paper = json.loads((STRESS_REPLAY_FIXTURE / "responses" / "paper.json").read_text())
    citations = json.loads((STRESS_REPLAY_FIXTURE / "responses" / "citations.json").read_text())

    assert search["ambiguous_seed_candidates"]["status"] == "ambiguous_fixture"
    assert search["ambiguous_seed_candidates"]["canonical_candidate_key"] == "p_seed_001"
    assert search["ambiguous_seed_candidates"]["rejected_candidate_keys"] == ["p_seed_variant_001"]
    assert paper["seed_resolution"]["seed_resolution_status"] == "ambiguous_fixture"
    assert citations["has_more"] is True
    assert citations["next_page_token"] == "fixture-page-2-not-returned"
    assert citations["partial_frontier"]["status"] == "partial_frontier"
    assert citations["returned_records_cap"] == 1


def test_stress_replay_fixture_agent_visible_files_do_not_leak_scorer_packet() -> None:
    visible_files = [
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        *sorted((STRESS_REPLAY_FIXTURE / "responses").glob("*.json")),
    ]
    forbidden = [
        "expected_outputs",
        "expected_citation_map",
        "expected_claim_support",
        "expected_source_support",
        "expected_omission_risk",
        "hidden_gold",
        "gold_packet",
        "answer_key",
        "scorer_packet",
    ]

    for path in visible_files:
        text = path.read_text().lower()
        assert all(token not in text for token in forbidden), path


def test_stress_replay_fixture_scorer_packet_is_separate_from_agent_visible_task() -> None:
    task = json.loads(
        (STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json").read_text()
    )
    endpoint_paths = {STRESS_REPLAY_FIXTURE / str(rel_path) for rel_path in task["endpoints"].values()}
    scorer_paths = set((STRESS_REPLAY_FIXTURE / "scorer_packet").glob("*.json"))

    assert scorer_paths
    assert endpoint_paths.isdisjoint(scorer_paths)


def test_stress_replay_fixture_agent_visible_boundary_excludes_negative_packets() -> None:
    task = json.loads(
        (STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json").read_text()
    )
    endpoint_paths = {STRESS_REPLAY_FIXTURE / str(rel_path) for rel_path in task["endpoints"].values()}
    negative_paths = set((STRESS_REPLAY_FIXTURE / "negative_packets").glob("*/*.json"))

    assert negative_paths
    assert endpoint_paths.isdisjoint(negative_paths)
    assert not any("negative_packets" in str(rel_path) for rel_path in task["endpoints"].values())


def test_stress_replay_transcript_preserves_online_like_states(tmp_path: Path) -> None:
    task_path = STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
    session = tmp_path / "session"
    for endpoint in ["search", "citations", "download-status", "source-status"]:
        replay_call(task_path, endpoint, session)

    transcript = build_replay_transcript(task_path, session)
    report = validate_replay_transcript_payload(
        transcript,
        expected_task_id="neural_ot_seed_ambiguity_partial_frontier_replay",
    )

    assert report["status"] == "passed"
    assert transcript["schema_version"] == "ra-surveybench-online-replay-transcript-v1"
    assert transcript["summary"]["event_count"] == 4
    assert transcript["summary"]["rate_limit_count"] == 1
    assert transcript["summary"]["pagination_token_count"] == 1
    assert transcript["summary"]["source_blocker_count"] >= 3

    by_endpoint = {event["endpoint"]: event for event in transcript["events"]}
    assert by_endpoint["search"]["status"] == "simulated_rate_limit"
    assert by_endpoint["search"]["source_blockers"][0]["source"] == "fixture_semantic_scholar"
    assert by_endpoint["citations"]["pagination"]["has_more"] is True
    assert by_endpoint["citations"]["pagination"]["next_page_token"] == "fixture-page-2-not-returned"
    assert by_endpoint["citations"]["pagination"]["partial_frontier"]["status"] == "partial_frontier"
    assert by_endpoint["download-status"]["source_blockers"]
    assert by_endpoint["source-status"]["provenance"]["response_endpoint"] == "source-status"
    assert "live-web robustness" in transcript["what_is_not_concluded"]


def test_replay_transcript_requires_trusted_session(tmp_path: Path) -> None:
    task_path = STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
    session = tmp_path / "session"
    session.mkdir()
    (session / "event_log.json").write_text(json.dumps(_valid_event_log(), indent=2, sort_keys=True))

    with pytest.raises(ReplayBenchmarkError):
        build_replay_transcript(task_path, session)


def test_stress_replay_score_passes_gold_equivalent_packet_with_valid_event_log(tmp_path: Path) -> None:
    actual_dir = _copy_packet(STRESS_REPLAY_FIXTURE, tmp_path)
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        actual_dir,
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["schema_version"] == "ra-surveybench-online-replay-score-report-v1"
    assert report["status"] == "passed"
    assert report["vetoes"] == []
    assert report["scores"]["event_log"]["required_call_recall"]["score"] == 1.0
    metric_split = report["diagnostics"]["metric_split"]
    assert metric_split["citation_map_layers"]["backward_lineage_edge_recall"]["score"] == 1.0
    assert metric_split["citation_map_layers"]["forward_citation_edge_recall"]["score"] == 1.0
    assert metric_split["citation_map_layers"]["adjacent_method_edge_recall"]["score"] == 1.0
    assert metric_split["seed_identity"]["duplicate_recall"]["score"] == 1.0
    assert metric_split["frontier"]["partial_frontier_omission_recall"]["score"] == 1.0
    assert metric_split["source_depth"]["checked_anchor_paper_recall"]["score"] == 1.0
    assert "live-web coverage" in metric_split["proxy_metric_boundaries"][2]


def test_stress_replay_wrong_seed_negative_fails_for_duplicate_resolution(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "wrong_seed_confirmed",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    duplicate_score = report["scores"]["candidate_ledger"]["duplicate_recall"]
    assert duplicate_score["score"] == 0.0
    assert ["p_seed_001", "p_seed_variant_001"] in duplicate_score["missing"]
    metric_split = report["diagnostics"]["metric_split"]
    seed_identity = metric_split["seed_identity"]["duplicate_recall"]
    assert seed_identity["score"] == 0.0
    assert ["p_seed_001", "p_seed_variant_001"] in seed_identity["missing"]
    assert metric_split["frontier"]["partial_frontier_omission_recall"]["score"] == 1.0


def test_stress_replay_false_completeness_negative_fails_for_missing_frontier_risk(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "false_completeness",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    omission_score = report["scores"]["omission_risk"]["high_severity_recall"]
    assert omission_score["score"] < 1.0
    assert "frontier_continuation_unobserved" in omission_score["missing"]
    metric_split = report["diagnostics"]["metric_split"]
    frontier_score = metric_split["frontier"]["partial_frontier_omission_recall"]
    assert frontier_score["score"] == 0.0
    assert "frontier_continuation_unobserved" in frontier_score["missing"]
    assert metric_split["seed_identity"]["duplicate_recall"]["score"] == 1.0


def test_stress_replay_metadata_only_claim_support_negative_fails_for_source_depth(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "metadata_only_claim_support",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    assert "unsupported_technical_claim" in report["vetoes"]
    assert report["scores"]["citation_map"]["node_recall"]["score"] == 1.0
    assert report["scores"]["candidate_ledger"]["included_recall"]["score"] == 1.0

    source_score = report["scores"]["source_support"]["anchor_recall"]
    assert source_score["score"] < 1.0
    assert ["p_seed_001", "section", "sec:replay-method"] in source_score["missing"]
    assert ["p_seed_001", "equation", "eq:replay-transport-objective"] in source_score["missing"]

    claim_score = report["scores"]["claim_support"]["supported_claim_anchor_recall"]
    assert claim_score["score"] < 1.0
    assert ["p_seed_001", "section", "sec:replay-method"] in claim_score["missing"]
    assert ["p_seed_001", "equation", "eq:replay-transport-objective"] in claim_score["missing"]

    metric_split = report["diagnostics"]["metric_split"]
    source_depth = metric_split["source_depth"]
    assert source_depth["checked_anchor_paper_recall"]["score"] == 0.0
    assert "p_seed_001" in source_depth["checked_anchor_paper_recall"]["missing"]
    assert source_depth["metadata_or_blocked_without_anchor_count"] >= 4
    assert metric_split["seed_identity"]["duplicate_recall"]["score"] == 1.0
    assert metric_split["frontier"]["partial_frontier_omission_recall"]["score"] == 1.0


def test_stress_replay_unavailable_pdf_negative_fails_for_blocked_source_status(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "unavailable_pdf_or_source_blocked",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    status_score = report["scores"]["source_support"]["status_accuracy"]
    assert status_score["score"] < 1.0
    assert ["p_cite_001", "metadata_only_fixture", "blocked_fixture"] in status_score["missing"]
    assert ["p_cite_001", "blocked_fixture", "blocked_fixture"] in status_score["extra"]
    anchor_score = report["scores"]["source_support"]["anchor_recall"]
    assert ["p_cite_001", "section", "sec:blocked-source"] in anchor_score["extra"]
    assert report["diagnostics"]["metric_split"]["frontier"]["partial_frontier_omission_recall"]["score"] == 1.0


def test_stress_replay_quarantine_negative_fails_for_quarantine_exclusion_and_anchors(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "quarantine_or_retraction_marker",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    included_score = report["scores"]["candidate_ledger"]["included_recall"]
    excluded_score = report["scores"]["candidate_ledger"]["excluded_recall"]
    assert "p_quarantine_001" in included_score["extra"]
    assert "p_quarantine_001" in excluded_score["missing"]
    claim_score = report["scores"]["claim_support"]["supported_claim_anchor_recall"]
    assert ["p_seed_001", "section", "sec:replay-method"] in claim_score["missing"]
    assert ["p_quarantine_001", "section", "sec:withdrawn-claim"] in claim_score["extra"]
    source_anchor_score = report["scores"]["source_support"]["anchor_recall"]
    assert ["p_quarantine_001", "section", "sec:withdrawn-claim"] in source_anchor_score["extra"]


def test_stress_replay_conflicting_metadata_negative_fails_for_duplicate_resolution(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "conflicting_metadata_sources",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    duplicate_score = report["scores"]["candidate_ledger"]["duplicate_recall"]
    assert duplicate_score["score"] == 0.0
    assert ["p_seed_001", "p_seed_variant_001"] in duplicate_score["missing"]
    assert ["p_seed_variant_001", "p_seed_001"] in duplicate_score["extra"]
    included_score = report["scores"]["candidate_ledger"]["included_recall"]
    assert "p_conflict_001" in included_score["extra"]
    assert report["diagnostics"]["metric_split"]["frontier"]["partial_frontier_omission_recall"]["score"] == 1.0


def test_stress_replay_proxy_promotion_negative_vetoes_unsupported_proxy_claims(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        STRESS_REPLAY_FIXTURE,
        "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json",
        STRESS_REPLAY_FIXTURE / "negative_packets" / "domain_specific_proxy_promotion",
        event_log,
        STRESS_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    assert "unsupported_technical_claim" in report["vetoes"]
    unsupported = report["scores"]["claim_support"]["unsupported_nonforbidden_claims"]
    assert unsupported == [
        "claim_proxy_objective_anchor",
        "claim_proxy_ranked_seed_method_node",
    ]
    claim_score = report["scores"]["claim_support"]["supported_claim_anchor_recall"]
    assert ["p_seed_001", "section", "sec:replay-method"] in claim_score["missing"]
    assert ["p_seed_001", "equation", "eq:replay-transport-objective"] in claim_score["missing"]


def test_transport_hmc_fixture_task_validates() -> None:
    task_path = TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json"
    task = json.loads(task_path.read_text())

    report = validate_replay_task_payload(task, artifact_path=task_path)

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_transport_hmc_fixture_interface_audit_passes() -> None:
    report = validate_replay_fixture_interface(
        TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json"
    )

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_transport_hmc_fixture_agent_visible_boundary_excludes_hidden_packets() -> None:
    task = json.loads((TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json").read_text())
    endpoint_paths = {TRANSPORT_HMC_REPLAY_FIXTURE / str(rel_path) for rel_path in task["endpoints"].values()}
    scorer_paths = set((TRANSPORT_HMC_REPLAY_FIXTURE / "scorer_packet").glob("*.json"))
    negative_paths = set((TRANSPORT_HMC_REPLAY_FIXTURE / "negative_packets").glob("*/*.json"))

    assert scorer_paths
    assert negative_paths
    assert endpoint_paths.isdisjoint(scorer_paths)
    assert endpoint_paths.isdisjoint(negative_paths)
    assert not any("scorer_packet" in str(rel_path) for rel_path in task["endpoints"].values())
    assert not any("negative_packets" in str(rel_path) for rel_path in task["endpoints"].values())


def test_transport_hmc_fixture_agent_visible_files_do_not_leak_hidden_packet_names() -> None:
    visible_files = [
        TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json",
        *sorted((TRANSPORT_HMC_REPLAY_FIXTURE / "responses").glob("*.json")),
    ]
    forbidden = [
        "expected_outputs",
        "expected_citation_map",
        "expected_claim_support",
        "expected_source_support",
        "expected_omission_risk",
        "hidden_gold",
        "gold_packet",
        "answer_key",
        "scorer_packet",
        "negative_packets",
    ]

    for path in visible_files:
        text = path.read_text().lower()
        assert all(token not in text for token in forbidden), path


def test_transport_hmc_replay_score_passes_gold_equivalent_packet(tmp_path: Path) -> None:
    actual_dir = _copy_packet(TRANSPORT_HMC_REPLAY_FIXTURE, tmp_path)
    event_log = _complete_event_log_for_fixture(
        TRANSPORT_HMC_REPLAY_FIXTURE,
        "transport_hmc_dsge_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json",
        actual_dir,
        event_log,
        TRANSPORT_HMC_REPLAY_FIXTURE / "scorer_packet",
    )

    assert report["schema_version"] == "ra-surveybench-online-replay-score-report-v1"
    assert report["status"] == "passed"
    assert report["vetoes"] == []
    metric_split = report["diagnostics"]["metric_split"]
    assert metric_split["citation_map_layers"]["backward_lineage_edge_recall"]["score"] == 1.0
    assert metric_split["citation_map_layers"]["forward_citation_edge_recall"]["score"] == 1.0
    assert metric_split["citation_map_layers"]["adjacent_method_edge_recall"]["score"] == 1.0
    assert metric_split["source_depth"]["checked_anchor_paper_recall"]["score"] == 1.0
    assert "live-web coverage" in metric_split["proxy_metric_boundaries"][2]


def test_transport_hmc_proxy_promotion_negative_vetoes_unsupported_claim(tmp_path: Path) -> None:
    event_log = _complete_event_log_for_fixture(
        TRANSPORT_HMC_REPLAY_FIXTURE,
        "transport_hmc_dsge_replay.task.json",
        tmp_path,
    )

    report = score_replay_submission(
        TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json",
        TRANSPORT_HMC_REPLAY_FIXTURE / "negative_packets" / "proxy_benchmark_promotion",
        event_log,
        TRANSPORT_HMC_REPLAY_FIXTURE / "scorer_packet",
    )

    _assert_intended_stress_failure(report)
    assert "unsupported_technical_claim" in report["vetoes"]
    unsupported = report["scores"]["claim_support"]["unsupported_nonforbidden_claims"]
    assert unsupported == ["claim_proxy_default_sampler_support"]
    included_score = report["scores"]["candidate_ledger"]["included_recall"]
    excluded_score = report["scores"]["candidate_ledger"]["excluded_recall"]
    assert "thmc_proxy_001" in included_score["extra"]
    assert "thmc_proxy_001" in excluded_score["missing"]
    claim_score = report["scores"]["claim_support"]["supported_claim_anchor_recall"]
    assert ["thmc_seed_001", "equation", "eq:transport-map-jacobian"] in claim_score["missing"]
    assert ["thmc_seed_001", "algorithm", "alg:transport-hmc-transition"] in claim_score["missing"]
    assert ["thmc_proxy_001", "benchmark_table", "tab:wall-clock-scores"] in claim_score["extra"]
    source_score = report["scores"]["source_support"]["anchor_recall"]
    assert ["thmc_proxy_001", "benchmark_table", "tab:wall-clock-scores"] in source_score["extra"]
