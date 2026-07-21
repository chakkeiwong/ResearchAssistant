from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from research_assistant.benchmarks.replay import replay_call, score_replay_submission
from research_assistant.benchmarks.surveybench_helpers import surveybench_ready_for_prose
from research_assistant.survey.build import build_survey_evidence_packet


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay"
TASK_PATH = FIXTURE / "neural_ot_seed_replay.task.json"
RESPONSES_DIR = FIXTURE / "responses"
GOLD_DIR = FIXTURE / "scorer_packet"
VALIDATION_DIR = ROOT / "docs/validation/literature_survey_automation_phase5_offline_validation_2026-07-06"
POSITIVE_PACKET_DIR = VALIDATION_DIR / "positive_command_packet"
SESSION_DIR = VALIDATION_DIR / "session"
NEGATIVE_ROOT = VALIDATION_DIR / "negative_command_packets"
PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
)
SCORER_PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "claim_support.json",
    "omission_risk.json",
)


@dataclass(frozen=True)
class NegativeCase:
    case_id: str
    description: str
    mutate: Callable[[dict[str, Any]], None]
    expected_ready_status: str
    expected_score_status: str
    expect: Callable[[dict[str, Any], dict[str, Any]], tuple[bool, list[str]]]


def run_validation() -> dict[str, Any]:
    if VALIDATION_DIR.exists():
        shutil.rmtree(VALIDATION_DIR)
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    _build_positive_packet()
    _build_session()
    positive_ready = surveybench_ready_for_prose(TASK_PATH, POSITIVE_PACKET_DIR, session_dir=SESSION_DIR)
    positive_score = score_replay_submission(
        TASK_PATH,
        POSITIVE_PACKET_DIR,
        SESSION_DIR / "event_log.json",
        GOLD_DIR,
    )
    positive_score_path = POSITIVE_PACKET_DIR / "replay_score_report.json"
    positive_ready_path = POSITIVE_PACKET_DIR / "ready_for_prose_report.json"
    positive_score_path.write_text(json.dumps(positive_score, indent=2, sort_keys=True))
    positive_ready_path.write_text(json.dumps(positive_ready, indent=2, sort_keys=True))
    base_packet = _load_packet(POSITIVE_PACKET_DIR)
    cases = []
    for case in CASES:
        packet = copy.deepcopy(base_packet)
        case.mutate(packet)
        case_dir = NEGATIVE_ROOT / case.case_id
        _write_packet(case_dir, packet)
        ready = surveybench_ready_for_prose(TASK_PATH, case_dir, session_dir=SESSION_DIR)
        score = score_replay_submission(
            TASK_PATH,
            case_dir,
            SESSION_DIR / "event_log.json",
            GOLD_DIR,
        )
        ready_path = case_dir / "ready_for_prose_report.json"
        score_path = case_dir / "replay_score_report.json"
        ready_path.write_text(json.dumps(ready, indent=2, sort_keys=True))
        score_path.write_text(json.dumps(score, indent=2, sort_keys=True))
        ok, details = case.expect(ready, score)
        cases.append({
            "case_id": case.case_id,
            "description": case.description,
            "packet_dir": str(case_dir.relative_to(ROOT)),
            "ready_for_prose_report": str(ready_path.relative_to(ROOT)),
            "replay_score_report": str(score_path.relative_to(ROOT)),
            "ready_status": ready.get("status"),
            "score_status": score.get("status"),
            "vetoes": score.get("vetoes", []),
            "expected_ready_status": case.expected_ready_status,
            "expected_score_status": case.expected_score_status,
            "expected_signal_observed": ok,
            "details": details,
        })
    positive_ok = positive_ready.get("status") == "ready" and positive_score.get("status") == "passed"
    negatives_ok = all(row["expected_signal_observed"] for row in cases)
    result = {
        "schema_version": "ra-literature-survey-phase5-command-validation-v1",
        "status": "passed" if positive_ok and negatives_ok else "failed",
        "task_path": str(TASK_PATH.relative_to(ROOT)),
        "positive": {
            "packet_dir": str(POSITIVE_PACKET_DIR.relative_to(ROOT)),
            "ready_for_prose_report": str(positive_ready_path.relative_to(ROOT)),
            "replay_score_report": str(positive_score_path.relative_to(ROOT)),
            "ready_status": positive_ready.get("status"),
            "score_status": positive_score.get("status"),
            "vetoes": positive_score.get("vetoes", []),
        },
        "negative_cases": cases,
        "hidden_gold_boundary": {
            "gold_used_only_for_scoring": True,
            "command_generation_inputs": [
                str(TASK_PATH.relative_to(ROOT)),
                str(RESPONSES_DIR.relative_to(ROOT)),
            ],
            "gold_dir": str(GOLD_DIR.relative_to(ROOT)),
        },
        "what_is_not_concluded": [
            "live web coverage",
            "product readiness",
            "scientific correctness",
            "real-agent reliability",
            "survey prose quality",
        ],
    }
    result_path = VALIDATION_DIR / "phase5_command_validation_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def _build_positive_packet() -> None:
    result = build_survey_evidence_packet(
        topic="Neural Optimal Transport for generative modeling and inference",
        seeds=["arxiv:2201.12220v3"],
        output_dir=POSITIVE_PACKET_DIR,
        mode="offline-replay",
        force=True,
        replay_task=TASK_PATH,
        replay_responses_dir=RESPONSES_DIR,
    )
    if (
        result["status"] != "offline_replay_fixture_complete"
        or result["workflow_state"]["ready_for_writer"] is not False
        or result["workflow_state"]["ready_for_prose"] is not False
    ):
        raise RuntimeError(f"positive command packet did not remain diagnostic-only: {result}")


def _build_session() -> None:
    for endpoint in ("search", "references", "citations", "adjacent", "download-status", "source-anchors"):
        replay_call(TASK_PATH, endpoint, SESSION_DIR)


def _load_packet(packet_dir: Path) -> dict[str, Any]:
    return {
        filename: json.loads((packet_dir / filename).read_text())
        for filename in PACKET_FILES
    }


def _write_packet(packet_dir: Path, packet: dict[str, Any]) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in packet.items():
        (packet_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True))
    source_manifest = POSITIVE_PACKET_DIR / "build_manifest.json"
    source_packet = POSITIVE_PACKET_DIR / "survey_packet.md"
    if source_manifest.exists():
        shutil.copy(source_manifest, packet_dir / "build_manifest.json")
    if source_packet.exists():
        shutil.copy(source_packet, packet_dir / "survey_packet.md")


def _score_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        value = value[key]
    return value


def _expect_score_metric_below_one(path: tuple[str, ...]) -> Callable[[dict[str, Any], dict[str, Any]], tuple[bool, list[str]]]:
    def check(ready: dict[str, Any], score: dict[str, Any]) -> tuple[bool, list[str]]:
        value = _score_value(score, path)
        ok = score.get("status") == "failed" and isinstance(value, (int, float)) and value < 1.0
        return ok, [
            f"ready_status={ready.get('status')}",
            f"score_status={score.get('status')}",
            f"{'.'.join(path)}={value}",
        ]

    return check


def _expect_ready_issue(code: str, file_name: str) -> Callable[[dict[str, Any], dict[str, Any]], tuple[bool, list[str]]]:
    def check(ready: dict[str, Any], score: dict[str, Any]) -> tuple[bool, list[str]]:
        issues = ready.get("packet_issues", [])
        found = any(
            isinstance(issue, dict)
            and issue.get("code") == code
            and issue.get("file") == file_name
            for issue in issues
        )
        return ready.get("status") == "blocked" and found, [
            f"ready_status={ready.get('status')}",
            f"score_status={score.get('status')}",
            f"issue_codes={[issue.get('code') for issue in issues if isinstance(issue, dict)]}",
        ]

    return check


def _expect_veto(veto: str) -> Callable[[dict[str, Any], dict[str, Any]], tuple[bool, list[str]]]:
    def check(ready: dict[str, Any], score: dict[str, Any]) -> tuple[bool, list[str]]:
        vetoes = score.get("vetoes", [])
        return score.get("status") == "failed" and veto in vetoes, [
            f"ready_status={ready.get('status')}",
            f"score_status={score.get('status')}",
            f"vetoes={vetoes}",
        ]

    return check


def _remove_backward_lineage_edge(packet: dict[str, Any]) -> None:
    citation_map = packet["citation_map.json"]
    citation_map["edges"] = [
        row for row in citation_map.get("edges", []) if row.get("edge_type") != "cites"
    ]


def _remove_source_status_row(packet: dict[str, Any]) -> None:
    source_support = packet["source_support.json"]
    source_support["papers"] = [
        row for row in source_support.get("papers", []) if row.get("paper_key") != "p_ref_001"
    ]


def _remove_classifications(packet: dict[str, Any]) -> None:
    packet["paper_classifications.json"]["classifications"] = []


def _strip_supported_claim_anchor(packet: dict[str, Any]) -> None:
    for row in packet["claim_support.json"].get("claims", []):
        if row.get("status") == "supported":
            row["anchors"] = []
            return


def _remove_omission_risks(packet: dict[str, Any]) -> None:
    packet["omission_risk.json"]["risks"] = []


def _add_false_supported_dominance_claim(packet: dict[str, Any]) -> None:
    packet["claim_support.json"]["claims"].append({
        "anchors": [{"kind": "section", "label": "sec:replay-method", "paper_key": "p_seed_001"}],
        "claim": "Neural optimal transport dominates all normalizing-flow methods.",
        "claim_id": "negative_supported_dominance",
        "paper_keys": ["p_seed_001"],
        "status": "supported",
        "support_class": "fixture_source_support",
    })


CASES = (
    NegativeCase(
        case_id="missing_backward_lineage_edge",
        description="Remove the seed-to-reference citation edge.",
        mutate=_remove_backward_lineage_edge,
        expected_ready_status="ready",
        expected_score_status="failed",
        expect=_expect_score_metric_below_one(("scores", "citation_map", "edge_recall", "score")),
    ),
    NegativeCase(
        case_id="missing_source_status_row",
        description="Remove one source-support row.",
        mutate=_remove_source_status_row,
        expected_ready_status="ready",
        expected_score_status="failed",
        expect=_expect_score_metric_below_one(("scores", "source_support", "status_accuracy", "score")),
    ),
    NegativeCase(
        case_id="missing_classification_rows",
        description="Remove all paper classifications.",
        mutate=_remove_classifications,
        expected_ready_status="blocked",
        expected_score_status="passed",
        expect=_expect_ready_issue("required_list_empty", "paper_classifications.json"),
    ),
    NegativeCase(
        case_id="missing_supported_claim_anchor",
        description="Strip anchors from a supported claim.",
        mutate=_strip_supported_claim_anchor,
        expected_ready_status="blocked",
        expected_score_status="failed",
        expect=_expect_veto("unsupported_technical_claim"),
    ),
    NegativeCase(
        case_id="missing_omission_risks",
        description="Remove omission-risk rows.",
        mutate=_remove_omission_risks,
        expected_ready_status="blocked",
        expected_score_status="failed",
        expect=_expect_ready_issue("required_list_empty", "omission_risk.json"),
    ),
    NegativeCase(
        case_id="false_supported_dominance_claim",
        description="Add a supported forbidden dominance claim.",
        mutate=_add_false_supported_dominance_claim,
        expected_ready_status="ready",
        expected_score_status="failed",
        expect=_expect_veto("forbidden_claim"),
    ),
)


def main() -> int:
    result = run_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
