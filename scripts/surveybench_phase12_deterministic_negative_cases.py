from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from research_assistant.benchmarks.replay import score_replay_submission


WORKSPACE = Path("/tmp/research_assistant_surveybench_phase9_codex_probe_workspace")
BASE_PACKET_DIR = WORKSPACE / "phase11_local_subject_packet"
SESSION_DIR = WORKSPACE / "phase11_local_subject_session"
TASK_PATH = WORKSPACE / (
    "tests/fixtures/surveybench/online_replay/"
    "neural_ot_seed_ambiguity_partial_frontier_replay/"
    "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
)
GOLD_DIR = (
    Path("/home/chakwong/research-assistant")
    / "tests/fixtures/surveybench/online_replay/"
    "neural_ot_seed_ambiguity_partial_frontier_replay/scorer_packet"
)
VALIDATION_DIR = Path(
    "/home/chakwong/research-assistant/"
    "docs/validation/surveybench_real_subject_trial_phase12_deterministic_negative_cases_2026-07-06"
)
PACKET_FILES = (
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
    expect: Callable[[dict[str, Any]], tuple[bool, list[str]]]


def _load_packet(packet_dir: Path) -> dict[str, Any]:
    return {
        Path(name).stem: json.loads((packet_dir / name).read_text())
        for name in PACKET_FILES
    }


def _write_packet(packet_dir: Path, packet: dict[str, Any]) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    for name in PACKET_FILES:
        (packet_dir / name).write_text(
            json.dumps(packet[Path(name).stem], indent=2, sort_keys=True)
        )
    source_record = BASE_PACKET_DIR / "trial_record.json"
    if source_record.exists():
        shutil.copy(source_record, packet_dir / "trial_record.json")


def _score(packet_dir: Path) -> dict[str, Any]:
    return score_replay_submission(
        TASK_PATH,
        packet_dir,
        SESSION_DIR / "event_log.json",
        GOLD_DIR,
    )


def _score_value(report: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = report
    for key in path:
        value = value[key]
    return value


def _expect_failed_metric(path: tuple[str, ...]) -> Callable[[dict[str, Any]], tuple[bool, list[str]]]:
    def check(report: dict[str, Any]) -> tuple[bool, list[str]]:
        score = _score_value(report, path)
        ok = report["status"] == "failed" and isinstance(score, (int, float)) and score < 1.0
        return ok, [f"{'.'.join(path)}={score}", f"status={report['status']}"]

    return check


def _expect_veto(veto: str, detail_path: tuple[str, ...] | None = None) -> Callable[[dict[str, Any]], tuple[bool, list[str]]]:
    def check(report: dict[str, Any]) -> tuple[bool, list[str]]:
        vetoes = report.get("vetoes", [])
        details = [f"vetoes={vetoes}", f"status={report.get('status')}"]
        if detail_path is not None:
            details.append(f"{'.'.join(detail_path)}={_score_value(report, detail_path)}")
        return report.get("status") == "failed" and veto in vetoes, details

    return check


def _remove_forward_citation_edge(packet: dict[str, Any]) -> None:
    citation_map = packet["citation_map"]
    citation_map["edges"] = [
        row for row in citation_map["edges"] if row.get("edge_type") != "cited_by"
    ]


def _remove_adjacent_cluster(packet: dict[str, Any]) -> None:
    citation_map = packet["citation_map"]
    citation_map["clusters"] = [
        row for row in citation_map["clusters"] if row.get("cluster_id") != "adjacent_density_modeling"
    ]
    citation_map["nodes"] = [
        row for row in citation_map["nodes"] if row.get("paper_key") != "p_adj_001"
    ]
    citation_map["edges"] = [
        row for row in citation_map["edges"] if row.get("target") != "p_adj_001" and row.get("source") != "p_adj_001"
    ]


def _omit_frontier_risk(packet: dict[str, Any]) -> None:
    omission = packet["omission_risk"]
    omission["risks"] = [
        row for row in omission["risks"] if row.get("paper_key") != "frontier_continuation_unobserved"
    ]


def _mark_blocked_source_as_downloaded(packet: dict[str, Any]) -> None:
    for row in packet["source_support"]["papers"]:
        if row.get("paper_key") == "p_cite_001":
            row["download_status"] = "downloaded_fixture"
            row["source_status"] = "available_fixture"
            row["checked_anchors"] = [{"kind": "section", "label": "fake:unchecked-source"}]


def _metadata_only_claim_support(packet: dict[str, Any]) -> None:
    for row in packet["claim_support"]["claims"]:
        if row.get("claim_id") == "claim_forward_citation_replay":
            row["support_class"] = "fixture_metadata_only"
            row["anchors"] = []


def _false_completeness_claim(packet: dict[str, Any]) -> None:
    packet["claim_support"]["claims"].append({
        "claim_id": "negative_false_complete_coverage",
        "claim": "Neural optimal transport dominates all normalizing-flow methods.",
        "paper_keys": ["p_seed_001"],
        "status": "supported",
        "support_class": "fixture_source_support",
        "anchors": [{"paper_key": "p_seed_001", "kind": "section", "label": "sec:replay-method"}],
    })


CASES = (
    NegativeCase(
        case_id="omit_forward_citation_edge",
        description="Remove the forward citation edge from the citation map.",
        mutate=_remove_forward_citation_edge,
        expect=_expect_failed_metric(("scores", "citation_map", "edge_recall", "score")),
    ),
    NegativeCase(
        case_id="omit_adjacent_cluster",
        description="Remove the adjacent method node, edge, and cluster.",
        mutate=_remove_adjacent_cluster,
        expect=_expect_failed_metric(("diagnostics", "metric_split", "citation_map_layers", "adjacent_cluster_recall", "score")),
    ),
    NegativeCase(
        case_id="omit_forward_frontier_risk",
        description="Remove the high-severity partial forward-frontier omission risk.",
        mutate=_omit_frontier_risk,
        expect=_expect_failed_metric(("diagnostics", "metric_split", "frontier", "partial_frontier_omission_recall", "score")),
    ),
    NegativeCase(
        case_id="overclaim_blocked_source_status",
        description="Mark a blocked metadata-only citation source as downloaded and checked.",
        mutate=_mark_blocked_source_as_downloaded,
        expect=_expect_failed_metric(("scores", "source_support", "status_accuracy", "score")),
    ),
    NegativeCase(
        case_id="metadata_only_claim_support",
        description="Strip anchors and downgrade a supported graph claim to metadata-only support.",
        mutate=_metadata_only_claim_support,
        expect=_expect_veto(
            "unsupported_technical_claim",
            ("scores", "claim_support", "unsupported_nonforbidden_claims"),
        ),
    ),
    NegativeCase(
        case_id="false_completeness_claim",
        description="Add a supported dominance/completeness-style forbidden claim.",
        mutate=_false_completeness_claim,
        expect=_expect_veto(
            "forbidden_claim",
            ("scores", "claim_support", "forbidden_claim_hits"),
        ),
    ),
)


def main() -> int:
    if not BASE_PACKET_DIR.exists():
        raise SystemExit(f"Phase 11 packet missing: {BASE_PACKET_DIR}")
    if not (SESSION_DIR / "event_log.json").exists():
        raise SystemExit(f"Phase 11 event log missing: {SESSION_DIR / 'event_log.json'}")
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    base_packet = _load_packet(BASE_PACKET_DIR)
    rows: list[dict[str, Any]] = []
    for case in CASES:
        packet = copy.deepcopy(base_packet)
        case.mutate(packet)
        case_dir = VALIDATION_DIR / "packets" / case.case_id
        _write_packet(case_dir, packet)
        report = _score(case_dir)
        report_path = VALIDATION_DIR / f"{case.case_id}_score_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True))
        ok, details = case.expect(report)
        rows.append({
            "case_id": case.case_id,
            "description": case.description,
            "packet_dir": str(case_dir),
            "score_report_path": str(report_path),
            "expected_signal_observed": ok,
            "score_status": report.get("status"),
            "vetoes": report.get("vetoes", []),
            "details": details,
        })
    result = {
        "schema_version": "ra-surveybench-phase12-deterministic-negative-case-result-v1",
        "status": "passed" if all(row["expected_signal_observed"] for row in rows) else "failed",
        "baseline_packet_dir": str(BASE_PACKET_DIR),
        "event_log_path": str(SESSION_DIR / "event_log.json"),
        "case_count": len(rows),
        "cases": rows,
        "not_a_real_subject_trial": True,
        "what_is_not_concluded": [
            "real model-agent reliability",
            "live web coverage",
            "survey prose quality",
            "scientific correctness",
            "product readiness",
        ],
    }
    result_path = VALIDATION_DIR / "deterministic_negative_case_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
