from __future__ import annotations

import json
import shutil
from pathlib import Path

from research_assistant.benchmarks.replay import replay_call
from research_assistant.benchmarks.surveybench_helpers import (
    REQUIRED_PACKET_FILES,
    scan_subject_helper_payload,
    surveybench_cluster_hints,
    surveybench_packet_compose,
    surveybench_launch_record_template,
    surveybench_next_action,
    surveybench_packet_template,
    surveybench_ready_for_prose,
    surveybench_visible_replay_packet,
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
TASK = REPLAY_FIXTURE / "neural_ot_seed_replay.task.json"
TRANSPORT_HMC_REPLAY_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "surveybench"
    / "online_replay"
    / "transport_hmc_dsge_replay"
)
TRANSPORT_HMC_TASK = TRANSPORT_HMC_REPLAY_FIXTURE / "transport_hmc_dsge_replay.task.json"


def _complete_event_log(tmp_path: Path) -> Path:
    session = tmp_path / "session"
    for endpoint in ["search", "references", "citations", "adjacent", "download-status", "source-anchors"]:
        replay_call(TASK, endpoint, session)
    return session


def _copy_visible_packet(tmp_path: Path) -> Path:
    actual = tmp_path / "actual"
    actual.mkdir()
    packet = surveybench_visible_replay_packet(
        TASK,
        responses_dir=REPLAY_FIXTURE / "responses",
    )["packet"]
    for filename, payload in packet.items():
        (actual / filename).write_text(json.dumps(payload, indent=2, sort_keys=True))
    return actual


def _assert_subject_helper_clean(payload: dict[str, object]) -> None:
    scan = scan_subject_helper_payload(payload)
    assert scan["status"] == "passed"
    text = json.dumps(payload, sort_keys=True).lower()
    assert "claim_laundering_hits" not in text
    assert "the replay seed is the central neural optimal transport method node" not in text
    assert "scorer_packet" not in text
    assert "expected_outputs" not in text
    assert "hidden_gold" not in text


def test_next_action_reports_missing_required_endpoint_without_gold() -> None:
    payload = surveybench_next_action(TASK)

    assert payload["schema_version"] == "ra-surveybench-helper-v1"
    assert payload["next_action"] == "call_replay_endpoint"
    assert payload["next_endpoint"] == "search"
    assert payload["missing_packet_files"] == list(REQUIRED_PACKET_FILES)
    _assert_subject_helper_clean(payload)


def test_next_action_moves_to_packet_files_after_required_calls(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)

    payload = surveybench_next_action(TASK, session_dir=session)

    assert payload["next_action"] == "write_packet_files"
    assert payload["next_endpoint"] is None
    assert payload["missing_required_endpoints"] == []
    _assert_subject_helper_clean(payload)


def test_packet_compose_writes_visible_packet_and_trial_record(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    output_dir = tmp_path / "composed_packet"

    payload = surveybench_packet_compose(
        TASK,
        output_dir,
        session_dir=session,
        responses_dir=REPLAY_FIXTURE / "responses",
        write_files=True,
    )

    assert payload["schema_version"] == "ra-surveybench-packet-compose-v1"
    assert payload["status"] == "ready"
    assert sorted(path.name for path in output_dir.glob("*.json")) == sorted(list(REQUIRED_PACKET_FILES) + ["trial_record.json"])
    candidate_ledger = json.loads((output_dir / "candidate_ledger.json").read_text())
    citation_map = json.loads((output_dir / "citation_map.json").read_text())
    source_support = json.loads((output_dir / "source_support.json").read_text())
    paper_classifications = json.loads((output_dir / "paper_classifications.json").read_text())
    claim_support = json.loads((output_dir / "claim_support.json").read_text())
    omission_risk = json.loads((output_dir / "omission_risk.json").read_text())
    trial_record = json.loads((output_dir / "trial_record.json").read_text())

    assert candidate_ledger["candidate_count"] == 7
    assert candidate_ledger["duplicates"][0]["canonical_key"] == "p_seed_001"
    assert {row["paper_key"] for row in candidate_ledger["excluded"]} == {"p_noise_001", "p_noise_002"}
    assert citation_map["edges"][1]["edge_type"] == "cited_by"
    assert "what_is_not_concluded" not in citation_map
    assert source_support["papers"][-1]["paper_key"] == "p_adj_001"
    assert any("major_citing_work" in row["labels"] for row in paper_classifications["classifications"])
    assert claim_support["claims"][-1]["claim_id"] == "claim_forbidden_dominance"
    assert omission_risk["risks"][0]["paper_key"] == "p_adj_001"
    assert trial_record["schema_version"] == "ra-surveybench-restricted-agent-trial-record-v1"
    assert trial_record["artifacts_created"] == [
        "candidate_ledger.json",
        "citation_map.json",
        "source_support.json",
        "paper_classifications.json",
        "claim_support.json",
        "omission_risk.json",
        "trial_record.json",
    ]
    assert trial_record["workspace_only"] is True
    _assert_subject_helper_clean(payload)


def test_visible_replay_packet_emits_classifications_and_typed_packet() -> None:
    payload = surveybench_visible_replay_packet(
        TASK,
        responses_dir=REPLAY_FIXTURE / "responses",
    )

    assert payload["schema_version"] == "ra-surveybench-visible-replay-packet-v1"
    assert payload["status"] == "ready"
    packet = payload["packet"]
    assert "paper_classifications.json" in packet
    classifications = packet["paper_classifications.json"]
    assert classifications["schema_version"] == "ra-surveybench-paper-classifications-v1"
    assert any("seed" in row["labels"] for row in classifications["classifications"])
    assert any("major_citing_work" in row["labels"] for row in classifications["classifications"])
    assert payload["packet_file_summaries"]["paper_classifications.json"]["classifications"] >= 1
    assert scan_subject_helper_payload(payload)["status"] == "passed"


def test_ready_for_prose_blocks_supported_claim_without_anchor_in_visible_packet(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    actual = _copy_visible_packet(tmp_path)
    claim_path = actual / "claim_support.json"
    claim_support = json.loads(claim_path.read_text())
    for row in claim_support["claims"]:
        if row["status"] == "supported":
            row["anchors"] = []
            break
    claim_path.write_text(json.dumps(claim_support, indent=2, sort_keys=True))

    payload = surveybench_ready_for_prose(TASK, actual, session_dir=session)

    assert payload["status"] == "blocked"
    assert "packet_content_incomplete" in payload["blocked_reasons"]
    assert any(issue["code"] == "supported_claim_without_anchor" for issue in payload["packet_issues"])


def test_ready_for_prose_blocks_missing_omission_risk_rows_in_visible_packet(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    actual = _copy_visible_packet(tmp_path)
    omission_path = actual / "omission_risk.json"
    omission_risk = json.loads(omission_path.read_text())
    omission_risk["risks"] = []
    omission_path.write_text(json.dumps(omission_risk, indent=2, sort_keys=True))

    payload = surveybench_ready_for_prose(TASK, actual, session_dir=session)

    assert payload["status"] == "blocked"
    assert "packet_content_incomplete" in payload["blocked_reasons"]
    assert any(issue["field"] == "risks" and issue["code"] == "required_list_empty" for issue in payload["packet_issues"])


def test_ready_for_prose_blocks_missing_classification_rows_in_visible_packet(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    actual = _copy_visible_packet(tmp_path)
    classifications_path = actual / "paper_classifications.json"
    classifications = json.loads(classifications_path.read_text())
    classifications["classifications"] = []
    classifications_path.write_text(json.dumps(classifications, indent=2, sort_keys=True))

    payload = surveybench_ready_for_prose(TASK, actual, session_dir=session)

    assert payload["status"] == "blocked"
    assert "packet_content_incomplete" in payload["blocked_reasons"]
    assert any(
        issue["file"] == "paper_classifications.json"
        and issue["field"] == "classifications"
        and issue["code"] == "required_list_empty"
        for issue in payload["packet_issues"]
    )


def test_packet_template_emits_schema_only_skeletons_and_writes_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "packet"

    payload = surveybench_packet_template(TASK, output_dir=output_dir, write_files=True)

    assert payload["schema_version"] == "ra-surveybench-packet-template-v1"
    assert sorted(path.name for path in output_dir.glob("*.json")) == sorted(REQUIRED_PACKET_FILES)
    claim_template = json.loads((output_dir / "claim_support.json").read_text())
    classification_template = json.loads((output_dir / "paper_classifications.json").read_text())
    assert claim_template["claims"] == []
    assert classification_template["classifications"] == []
    assert claim_template["what_is_not_concluded"] == []
    _assert_subject_helper_clean(payload)


def test_ready_for_prose_blocks_until_calls_and_packets_exist(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()

    payload = surveybench_ready_for_prose(TASK, actual)

    assert payload["status"] == "blocked"
    assert "missing_required_replay_calls" in payload["blocked_reasons"]
    assert "missing_packet_files" in payload["blocked_reasons"]
    _assert_subject_helper_clean(payload)


def test_ready_for_prose_blocks_empty_packet_templates(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    actual = tmp_path / "actual"
    surveybench_packet_template(TASK, output_dir=actual, write_files=True)

    payload = surveybench_ready_for_prose(TASK, actual, session_dir=session)

    assert payload["status"] == "blocked"
    assert "packet_content_incomplete" in payload["blocked_reasons"]
    issues = {(row["file"], row["field"], row["code"]) for row in payload["packet_issues"]}
    assert ("candidate_ledger.json", "included", "required_list_empty") in issues
    assert ("citation_map.json", "nodes", "required_list_empty") in issues
    assert ("paper_classifications.json", "classifications", "required_list_empty") in issues
    assert ("claim_support.json", "claims", "required_list_empty") in issues
    _assert_subject_helper_clean(payload)


def test_ready_for_prose_blocks_supported_claim_without_anchor(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    actual = _copy_visible_packet(tmp_path)
    claim_path = actual / "claim_support.json"
    claim_support = json.loads(claim_path.read_text())
    claim_support["claims"].append({
        "anchors": [],
        "claim": "The fixture proves a live-web literature result.",
        "claim_id": "unsupported_live_web_claim",
        "paper_keys": ["p_seed_001"],
        "status": "supported",
        "support_class": "fixture_source_support",
    })
    claim_path.write_text(json.dumps(claim_support, indent=2, sort_keys=True))

    payload = surveybench_ready_for_prose(TASK, actual, session_dir=session)

    assert payload["status"] == "blocked"
    assert "packet_content_incomplete" in payload["blocked_reasons"]
    assert {
        "file": "claim_support.json",
        "field": "claims[4].anchors",
        "code": "supported_claim_without_anchor",
        "claim_id": "unsupported_live_web_claim",
        "message": "supported claims need at least one visible anchor before prose drafting",
    } in payload["packet_issues"]
    _assert_subject_helper_clean(payload)


def test_ready_for_prose_passes_visible_artifact_completeness(tmp_path: Path) -> None:
    session = _complete_event_log(tmp_path)
    actual = _copy_visible_packet(tmp_path)

    payload = surveybench_ready_for_prose(TASK, actual, session_dir=session)

    assert payload["status"] == "ready"
    assert payload["blocked_reasons"] == []
    assert payload["missing_packet_files"] == []
    assert payload["packet_issues"] == []
    _assert_subject_helper_clean(payload)


def test_ready_for_prose_passes_transport_hmc_packet_completeness(tmp_path: Path) -> None:
    session = tmp_path / "session"
    for endpoint in ["search", "references", "citations", "adjacent", "download-status", "source-anchors"]:
        replay_call(TRANSPORT_HMC_TASK, endpoint, session)
    actual = tmp_path / "actual"
    actual.mkdir()
    packet = surveybench_visible_replay_packet(
        TRANSPORT_HMC_TASK,
        responses_dir=TRANSPORT_HMC_REPLAY_FIXTURE / "responses",
    )["packet"]
    for filename, payload in packet.items():
        (actual / filename).write_text(json.dumps(payload, indent=2, sort_keys=True))

    payload = surveybench_ready_for_prose(TRANSPORT_HMC_TASK, actual, session_dir=session)

    assert payload["status"] == "ready"
    assert payload["blocked_reasons"] == []
    assert payload["packet_issues"] == []
    _assert_subject_helper_clean(payload)


def test_launch_record_template_is_boundary_scaffold_not_launch_approval() -> None:
    payload = surveybench_launch_record_template(TASK)

    assert payload["schema_version"] == "ra-surveybench-launch-record-template-v1"
    assert payload["launch_record"]["supervisor"] == "codex"
    assert "python -m research_assistant.cli surveybench cluster-hints" in payload["launch_record"]["allowed_commands"]
    assert "launch approval" in payload["what_is_not_concluded"]
    _assert_subject_helper_clean(payload)


def test_cluster_hints_derives_visible_cluster_ids_without_gold() -> None:
    payload = surveybench_cluster_hints(TASK)

    assert payload["schema_version"] == "ra-surveybench-cluster-hints-v1"
    assert payload["status"] == "ready"
    clusters = {cluster["cluster_id"]: cluster for cluster in payload["clusters"]}
    assert set(clusters) == {
        "adjacent_density_modeling",
        "classical_optimal_transport",
        "neural_optimal_transport",
    }
    assert clusters["neural_optimal_transport"]["paper_keys"] == ["p_cite_001", "p_seed_001"]
    assert clusters["classical_optimal_transport"]["paper_keys"] == ["p_ref_001"]
    assert clusters["adjacent_density_modeling"]["paper_keys"] == ["p_adj_001"]
    assert payload["missing_response_sources"] == []
    _assert_subject_helper_clean(payload)


def test_cluster_hints_excludes_noisy_adjacent_candidates() -> None:
    payload = surveybench_cluster_hints(TASK)

    excluded = {
        row["paper_key"]: row
        for row in payload["excluded_adjacent_hints"]
    }
    assert excluded["p_noise_001"]["relation"] == "noisy_adjacent"
    assert excluded["p_noise_002"]["relation"] == "false_positive"
    assert all("p_noise" not in paper_key for cluster in payload["clusters"] for paper_key in cluster["paper_keys"])
    _assert_subject_helper_clean(payload)


def test_cluster_hints_reads_call_result_wrappers_from_visible_response_dir(tmp_path: Path) -> None:
    response_dir = tmp_path / "responses"
    response_dir.mkdir()
    for endpoint in ["references", "citations", "adjacent"]:
        result = replay_call(TASK, endpoint, tmp_path / "session")
        (response_dir / f"{endpoint}.json").write_text(json.dumps(result, indent=2, sort_keys=True))

    payload = surveybench_cluster_hints(TASK, responses_dir=response_dir)

    assert payload["status"] == "ready"
    clusters = {cluster["cluster_id"]: cluster for cluster in payload["clusters"]}
    assert "classical_optimal_transport" in clusters
    assert "neural_optimal_transport" in clusters
    assert "adjacent_density_modeling" in clusters
    _assert_subject_helper_clean(payload)


def test_cluster_hints_blocks_when_required_visible_responses_are_missing(tmp_path: Path) -> None:
    response_dir = tmp_path / "responses"
    response_dir.mkdir()
    shutil.copy(REPLAY_FIXTURE / "responses" / "references.json", response_dir / "references.json")

    payload = surveybench_cluster_hints(TASK, responses_dir=response_dir)

    assert payload["status"] == "blocked"
    assert payload["missing_response_sources"] == ["citations", "adjacent"]
    _assert_subject_helper_clean(payload)


def test_cluster_hints_ignores_task_rubric_cluster_looking_text(tmp_path: Path) -> None:
    task = json.loads(TASK.read_text())
    task["rubric"] = {
        "cluster_hint": "misleading_evaluator_only_cluster",
        "notes": "This visible test value must not drive subject helper output.",
    }
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task, indent=2, sort_keys=True))

    payload = surveybench_cluster_hints(task_path, responses_dir=REPLAY_FIXTURE / "responses")

    cluster_ids = {cluster["cluster_id"] for cluster in payload["clusters"]}
    assert "misleading_evaluator_only_cluster" not in cluster_ids
    assert cluster_ids == {
        "adjacent_density_modeling",
        "classical_optimal_transport",
        "neural_optimal_transport",
    }
    _assert_subject_helper_clean(payload)


def test_subject_helper_scan_rejects_gold_derived_diagnostics() -> None:
    payload = {
        "schema_version": "ra-surveybench-helper-v1",
        "claim_laundering_hits": ["$.what_is_not_concluded[0]"],
    }

    scan = scan_subject_helper_payload(payload)

    assert scan["status"] == "failed"
    assert "claim_laundering_hits" in scan["forbidden_token_hits"]
