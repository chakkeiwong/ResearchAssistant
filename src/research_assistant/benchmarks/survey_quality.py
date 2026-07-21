from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_assistant.benchmarks.replay import score_replay_submission

SURVEY_PROSE_SCHEMA_VERSION = "ra-surveybench-survey-prose-v1"
SURVEY_PROSE_SCORE_SCHEMA_VERSION = "ra-surveybench-survey-prose-score-v1"

HARD_GATE_EVIDENCE_PACKET_FAILED = "evidence_packet_failed"
HARD_GATE_PROSE_MISSING = "survey_prose_missing"
HARD_GATE_PROSE_SCHEMA_INVALID = "survey_prose_schema_invalid"
HARD_GATE_UNSUPPORTED_TECHNICAL_CLAIM = "unsupported_technical_claim"
HARD_GATE_SOURCE_STATUS_OVERCLAIM = "source_status_overclaim"
HARD_GATE_OMISSION_RISK_UNADDRESSED = "omission_risk_unaddressed"
HARD_GATE_METADATA_PROMOTED_TO_TRUTH = "metadata_promoted_to_truth_evidence"
HARD_GATE_MISSING_NONCLAIMS = "missing_nonclaims"

REQUIRED_NONCLAIMS = (
    "live-web coverage",
    "current citation counts",
    "download reliability",
    "survey completeness",
    "product readiness",
    "scientific correctness",
)

METADATA_TRUTH_TOKENS = (
    "citation_count",
    "venue_rank",
    "popularity",
    "leaderboard",
    "benchmark_proxy",
)


def score_survey_prose(
    task_path: Path,
    actual_dir: Path,
    event_log_path: Path,
    gold_dir: Path,
    prose_path: Path,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    actual_dir = actual_dir.resolve()
    event_log_path = event_log_path.resolve()
    gold_dir = gold_dir.resolve()
    prose_path = prose_path.resolve()
    packet_report = score_replay_submission(task_path, actual_dir, event_log_path, gold_dir)
    hard_gate_vetoes: list[str] = []
    errors: list[str] = []
    if packet_report["status"] != "passed":
        hard_gate_vetoes.append(HARD_GATE_EVIDENCE_PACKET_FAILED)
        return _report(
            task_id=str(packet_report.get("task_id", "unknown")),
            prose_path=prose_path,
            packet_report=packet_report,
            hard_gate_vetoes=hard_gate_vetoes,
            errors=errors,
            primary_scores=_blocked_primary_scores(),
            claim_trace=[],
            source_status_caveats=[],
            addressed_omission_risks=[],
            nonclaims=[],
        )
    if not prose_path.exists():
        hard_gate_vetoes.append(HARD_GATE_PROSE_MISSING)
        errors.append(f"survey prose annotation missing: {prose_path}")
        return _report(
            task_id=str(packet_report.get("task_id", "unknown")),
            prose_path=prose_path,
            packet_report=packet_report,
            hard_gate_vetoes=hard_gate_vetoes,
            errors=errors,
            primary_scores=_blocked_primary_scores(),
            claim_trace=[],
            source_status_caveats=[],
            addressed_omission_risks=[],
            nonclaims=[],
        )
    try:
        prose = json.loads(prose_path.read_text())
    except json.JSONDecodeError as exc:
        hard_gate_vetoes.append(HARD_GATE_PROSE_SCHEMA_INVALID)
        errors.append(f"{prose_path}: invalid JSON: {exc}")
        return _report(
            task_id=str(packet_report.get("task_id", "unknown")),
            prose_path=prose_path,
            packet_report=packet_report,
            hard_gate_vetoes=hard_gate_vetoes,
            errors=errors,
            primary_scores=_blocked_primary_scores(),
            claim_trace=[],
            source_status_caveats=[],
            addressed_omission_risks=[],
            nonclaims=[],
        )

    if not isinstance(prose, dict) or prose.get("schema_version") != SURVEY_PROSE_SCHEMA_VERSION:
        hard_gate_vetoes.append(HARD_GATE_PROSE_SCHEMA_INVALID)
        errors.append(f"{prose_path}: expected schema_version {SURVEY_PROSE_SCHEMA_VERSION!r}")
        prose = prose if isinstance(prose, dict) else {}

    packet = _load_packet(actual_dir)
    claim_trace = _list_dicts(prose.get("claim_trace"))
    source_status_caveats = _list_dicts(prose.get("source_status_caveats"))
    addressed_omission_risks = [str(value) for value in prose.get("addressed_omission_risks", [])]
    nonclaims = [str(value) for value in prose.get("what_is_not_concluded", [])]

    claim_score = _score_claim_trace(packet, claim_trace, hard_gate_vetoes)
    caveat_score = _score_source_status_caveats(packet, source_status_caveats, hard_gate_vetoes)
    omission_score = _score_omission_risks(packet, addressed_omission_risks, hard_gate_vetoes)
    nonclaim_score = _score_nonclaims(nonclaims, hard_gate_vetoes)

    if _metadata_promoted_to_truth(claim_trace):
        hard_gate_vetoes.append(HARD_GATE_METADATA_PROMOTED_TO_TRUTH)

    primary_scores = {
        "required_claim_recall": claim_score,
        "source_status_caveat_recall": caveat_score,
        "omission_risk_recall": omission_score,
        "nonclaim_recall": nonclaim_score,
    }
    return _report(
        task_id=str(packet_report.get("task_id", "unknown")),
        prose_path=prose_path,
        packet_report=packet_report,
        hard_gate_vetoes=hard_gate_vetoes,
        errors=errors,
        primary_scores=primary_scores,
        claim_trace=claim_trace,
        source_status_caveats=source_status_caveats,
        addressed_omission_risks=addressed_omission_risks,
        nonclaims=nonclaims,
    )


def _report(
    *,
    task_id: str,
    prose_path: Path,
    packet_report: dict[str, Any],
    hard_gate_vetoes: list[str],
    errors: list[str],
    primary_scores: dict[str, dict[str, Any]],
    claim_trace: list[dict[str, Any]],
    source_status_caveats: list[dict[str, Any]],
    addressed_omission_risks: list[str],
    nonclaims: list[str],
) -> dict[str, Any]:
    status = "passed" if not hard_gate_vetoes and not errors and all(
        score.get("score") == 1.0
        for score in primary_scores.values()
    ) else "failed"
    return {
        "schema_version": SURVEY_PROSE_SCORE_SCHEMA_VERSION,
        "task_id": task_id,
        "status": status,
        "prose_path": str(prose_path),
        "packet_gate": {
            "status": packet_report["status"],
            "vetoes": packet_report["vetoes"],
            "errors": packet_report["errors"],
        },
        "hard_gate_vetoes": sorted(set(hard_gate_vetoes)),
        "errors": errors,
        "primary_scores": primary_scores,
        "claim_trace": claim_trace,
        "source_status_caveats": source_status_caveats,
        "addressed_omission_risks": addressed_omission_risks,
        "what_is_not_concluded": [
            "survey prose score does not prove scientific correctness",
            "survey prose score does not prove literature completeness",
            "survey prose score does not prove live-web coverage",
            "survey prose score does not certify product readiness",
        ],
    }


def _load_packet(actual_dir: Path) -> dict[str, Any]:
    packet: dict[str, Any] = {}
    for filename in (
        "candidate_ledger.json",
        "citation_map.json",
        "source_support.json",
        "claim_support.json",
        "omission_risk.json",
    ):
        path = actual_dir / filename
        try:
            packet[filename.removesuffix(".json")] = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            packet[filename.removesuffix(".json")] = {}
    return packet


def _blocked_primary_scores() -> dict[str, dict[str, Any]]:
    return {
        "required_claim_recall": _score_set(set(), set()),
        "source_status_caveat_recall": _score_set(set(), set()),
        "omission_risk_recall": _score_set(set(), set()),
        "nonclaim_recall": _score_set(set(REQUIRED_NONCLAIMS), set()),
    }


def _score_claim_trace(
    packet: dict[str, Any],
    claim_trace: list[dict[str, Any]],
    vetoes: list[str],
) -> dict[str, Any]:
    expected = {
        str(row.get("claim_id"))
        for row in _list_dicts(packet.get("claim_support", {}).get("claims"))
        if row.get("status") == "supported"
    }
    actual = {
        str(row.get("claim_id"))
        for row in claim_trace
        if row.get("status") == "supported"
    }
    unsupported = [
        str(row.get("claim_id", "unknown_claim"))
        for row in claim_trace
        if row.get("status") == "supported"
        and str(row.get("support_class")) not in {"fixture_source_support", "fixture_graph_support"}
    ]
    support_rows = {
        str(row.get("claim_id")): row
        for row in _list_dicts(packet.get("claim_support", {}).get("claims"))
    }
    for row in claim_trace:
        if row.get("status") != "supported":
            continue
        claim_id = str(row.get("claim_id"))
        support_row = support_rows.get(claim_id)
        if support_row is None:
            unsupported.append(claim_id)
            continue
        expected_anchors = {
            _anchor_key(anchor)
            for anchor in _list_dicts(support_row.get("anchors"))
        }
        actual_anchors = {
            _anchor_key(anchor)
            for anchor in _list_dicts(row.get("anchors"))
        }
        if not expected_anchors or not expected_anchors.issubset(actual_anchors):
            unsupported.append(claim_id)
    if unsupported:
        vetoes.append(HARD_GATE_UNSUPPORTED_TECHNICAL_CLAIM)
    score = _score_set(expected, actual)
    if score["missing"]:
        vetoes.append(HARD_GATE_UNSUPPORTED_TECHNICAL_CLAIM)
    score["unsupported_claim_ids"] = sorted(set(unsupported))
    return score


def _score_source_status_caveats(
    packet: dict[str, Any],
    source_status_caveats: list[dict[str, Any]],
    vetoes: list[str],
) -> dict[str, Any]:
    expected = {
        str(row.get("paper_key"))
        for row in _list_dicts(packet.get("source_support", {}).get("papers"))
        if str(row.get("source_status")) != "available_fixture"
        or str(row.get("download_status")) != "downloaded_fixture"
    }
    actual = {
        str(row.get("paper_key"))
        for row in source_status_caveats
        if row.get("paper_key")
    }
    score = _score_set(expected, actual)
    if score["missing"]:
        vetoes.append(HARD_GATE_SOURCE_STATUS_OVERCLAIM)
    return score


def _score_omission_risks(
    packet: dict[str, Any],
    addressed_omission_risks: list[str],
    vetoes: list[str],
) -> dict[str, Any]:
    expected = {
        str(row.get("paper_key"))
        for row in _list_dicts(packet.get("omission_risk", {}).get("risks"))
        if str(row.get("severity", "")).lower() == "high"
    }
    actual = set(addressed_omission_risks)
    score = _score_set(expected, actual)
    if score["missing"]:
        vetoes.append(HARD_GATE_OMISSION_RISK_UNADDRESSED)
    return score


def _score_nonclaims(nonclaims: list[str], vetoes: list[str]) -> dict[str, Any]:
    normalized = {_norm(value) for value in nonclaims}
    actual = {
        required
        for required in REQUIRED_NONCLAIMS
        if any(required in value for value in normalized)
    }
    score = _score_set(set(REQUIRED_NONCLAIMS), actual)
    if score["missing"]:
        vetoes.append(HARD_GATE_MISSING_NONCLAIMS)
    return score


def _metadata_promoted_to_truth(claim_trace: list[dict[str, Any]]) -> bool:
    for row in claim_trace:
        if row.get("status") != "supported":
            continue
        support_class = str(row.get("support_class", ""))
        claim_text = _norm(str(row.get("claim", "")))
        if support_class in METADATA_TRUTH_TOKENS:
            return True
        if any(token in claim_text for token in METADATA_TRUTH_TOKENS):
            return True
    return False


def _anchor_key(anchor: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(anchor.get("paper_key", "")),
        str(anchor.get("kind", "")),
        str(anchor.get("label", "")),
    )


def _score_set(expected: set[Any], actual: set[Any]) -> dict[str, Any]:
    matched = expected & actual
    missing = expected - actual
    extra = actual - expected
    return {
        "matched": len(matched),
        "expected": len(expected),
        "actual": len(actual),
        "score": len(matched) / len(expected) if expected else 1.0,
        "missing": _report_values(sorted(missing)),
        "extra": _report_values(sorted(extra)),
    }


def _report_values(values: list[Any]) -> list[Any]:
    return [list(value) if isinstance(value, tuple) else value for value in values]


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _norm(value: str) -> str:
    return " ".join(value.lower().strip().split())
