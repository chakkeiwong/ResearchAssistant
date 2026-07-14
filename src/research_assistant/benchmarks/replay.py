from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from research_assistant.benchmarks.claim_guard import (
    claim_laundering_hits,
    nonclaim_rows_in_claims,
)

REPLAY_TASK_SCHEMA_VERSION = "ra-surveybench-online-replay-task-v1"
REPLAY_RUBRIC_SCHEMA_VERSION = "ra-surveybench-online-replay-rubric-v1"
REPLAY_EVENT_LOG_SCHEMA_VERSION = "ra-surveybench-online-replay-event-log-v1"
REPLAY_SESSION_SCHEMA_VERSION = "ra-surveybench-online-replay-session-v1"
REPLAY_TRANSCRIPT_SCHEMA_VERSION = "ra-surveybench-online-replay-transcript-v1"
REPLAY_VALIDATION_REPORT_SCHEMA_VERSION = "ra-surveybench-online-replay-validation-report-v1"
REPLAY_SCORE_REPORT_SCHEMA_VERSION = "ra-surveybench-online-replay-score-report-v1"

REQUIRED_ENDPOINTS = (
    "search",
    "paper",
    "references",
    "citations",
    "adjacent",
    "download-status",
    "source-status",
    "source-anchors",
)

OPTIONAL_EVIDENCE_ENDPOINTS = ("evidence-context",)

REQUIRED_EVIDENCE_FIELDS = (
    "candidate_ledger",
    "citation_map",
    "source_support",
    "paper_classifications",
    "claim_support",
    "omission_risk",
    "budget_compliance",
)

REQUIRED_PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "claim_support.json",
    "omission_risk.json",
)

REQUIRED_WORKFLOW_ENDPOINTS = (
    "search",
    "references",
    "citations",
    "adjacent",
    "download-status",
    "source-anchors",
)

REQUIRED_BUDGET_COUNTERS = (
    "endpoint_calls",
    "returned_records",
    "paper_detail_calls",
    "source_anchor_calls",
    "submit_or_score_attempts",
)

RUBRIC_LIST_FIELDS_REQUIRED_NONEMPTY = (
    "classification_labels",
    "edge_types",
    "source_statuses",
    "download_statuses",
    "support_classes",
    "omission_risk_severities",
)

RUBRIC_LIST_FIELDS_REQUIRED = (
    "multi_label_fields",
    "exact_match_fields",
    "partial_credit_fields",
)

ALLOWED_EVIDENCE_FALLBACKS = {"insufficient_evidence", "out_of_scope"}

ALLOWED_EVENT_STATUSES = {
    "ok",
    "blocked_budget",
    "blocked_unknown_endpoint",
    "blocked_invalid_request",
    "simulated_rate_limit",
}

REPLAY_SCORE_VETO_MISSING_EVENT_LOG = "missing_event_log"
REPLAY_SCORE_VETO_INVALID_EVENT_LOG = "invalid_event_log"
REPLAY_SCORE_VETO_BUDGET_EXCEEDED = "budget_exceeded"
REPLAY_SCORE_VETO_MISSING_REQUIRED_CALL = "missing_required_call"
REPLAY_SCORE_VETO_PROSE_ONLY = "prose_only_submission"
REPLAY_SCORE_VETO_MISSING_PACKET_FILE = "missing_packet_file"
REPLAY_SCORE_VETO_MISSING_CITATION_MAP = "missing_citation_map"
REPLAY_SCORE_VETO_UNSUPPORTED_TECHNICAL_CLAIM = "unsupported_technical_claim"
REPLAY_SCORE_VETO_FORBIDDEN_CLAIM = "forbidden_claim"
REPLAY_SCORE_VETO_HIDDEN_ONLY_FIELD = "hidden_only_scored_field"
REPLAY_SCORE_VETO_UNTRUSTED_EVENT_LOG = "untrusted_event_log"
REPLAY_SCORE_VETO_GOLD_ACTUAL_OVERLAP = "gold_actual_overlap"

AGENT_VISIBLE_FORBIDDEN_KEYS = {
    "expected_outputs",
    "expected_output",
    "expected_packet",
    "expected_citation_map",
    "expected_candidate_ledger",
    "expected_source_support",
    "expected_claim_support",
    "expected_omission_risk",
    "hidden_gold",
    "gold_outputs",
    "gold_packet",
    "answer_key",
    "answer_keys",
    "scorer_only",
}

AGENT_VISIBLE_FORBIDDEN_VALUE_TOKENS = (
    "expected_outputs",
    "expected_citation_map",
    "expected_candidate_ledger",
    "expected_source_support",
    "expected_claim_support",
    "expected_omission_risk",
    "hidden_gold",
    "gold_packet",
    "answer_key",
)

SCORER_ONLY_ENDPOINT_NAMES = {
    "score",
    "scorer",
    "gold",
    "answer-key",
    "expected-outputs",
}

SUPPORTED_CLAIM_SUPPORT_CLASSES = {
    "fixture_source_support",
    "fixture_graph_support",
}


class ReplayBenchmarkError(ValueError):
    """Raised when an online-replay benchmark artifact is invalid."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ReplayBenchmarkError(f"{path}: invalid JSON: {exc}") from exc


def validate_replay_task(path: Path) -> dict[str, Any]:
    return validate_replay_task_payload(load_json(path), artifact_path=path)


def replay_call(
    task_path: Path,
    endpoint: str,
    session_dir: Path,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    session_dir.mkdir(parents=True, exist_ok=True)
    task = load_json(task_path)
    task_report = validate_replay_task_payload(task, artifact_path=task_path)
    if task_report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(task_report["issues"]))
    if endpoint not in task["endpoints"]:
        return _blocked_response(
            task_path,
            task,
            endpoint,
            request_id or f"{endpoint}-invalid",
            session_dir,
            "blocked_unknown_endpoint",
            f"unknown replay endpoint {endpoint!r}",
        )
    response_rel = task["endpoints"][endpoint]
    if not isinstance(response_rel, str):
        raise ReplayBenchmarkError("Phase 3 replay-call supports path-string endpoints only")
    response_path = (task_path.parent / response_rel).resolve()
    response = load_json(response_path)
    with _event_log_lock(session_dir):
        _ensure_session_manifest(task_path, task, session_dir)
        budget_before = _current_budget(task, session_dir)
        cost = _endpoint_cost(endpoint, response)
        if _would_exceed_budget(budget_before, cost):
            return _blocked_response(
                task_path,
                task,
                endpoint,
                request_id or _response_request_id(response, endpoint),
                session_dir,
                "blocked_budget",
                "replay budget exhausted for requested endpoint",
                result_count=0,
                lock_held=True,
            )
        budget_after = _subtract_budget(budget_before, cost)
        event = _event(
            task_id=str(task["task_id"]),
            endpoint=endpoint,
            request_id=request_id or _response_request_id(response, endpoint),
            session_dir=session_dir,
            budget_before=budget_before,
            budget_after=budget_after,
            result_count=_response_result_count(response),
            status=_event_status(response),
        )
        _append_event(session_dir, str(task["task_id"]), event)
    return {
        "schema_version": "ra-surveybench-online-replay-call-result-v1",
        "status": event["status"],
        "task_id": task["task_id"],
        "endpoint": endpoint,
        "request_id": event["request_id"],
        "budget_before": budget_before,
        "budget_after": budget_after,
        "event_log_path": str(_event_log_path(session_dir)),
        "response": response,
    }


def validate_replay_fixture_interface(task_path: Path) -> dict[str, Any]:
    task_path = task_path.resolve()
    task = load_json(task_path)
    issues: list[dict[str, Any]] = []
    task_report = validate_replay_task_payload(task, artifact_path=task_path)
    issues.extend(task_report["issues"])
    endpoints = task.get("endpoints", {})
    if isinstance(endpoints, dict):
        for endpoint, rel_path in endpoints.items():
            path = task_path.parent / str(rel_path)
            if not path.exists():
                issues.append(_issue(
                    "endpoint_file_missing",
                    f"endpoint file missing for {endpoint!r}",
                    f"$.endpoints.{endpoint}",
                ))
                continue
            payload = load_json(path)
            if isinstance(payload, dict):
                if payload.get("endpoint") != endpoint:
                    issues.append(_issue(
                        "endpoint_name_mismatch",
                        f"endpoint payload does not match {endpoint!r}",
                        f"$.endpoints.{endpoint}",
                    ))
                _find_agent_visible_leaks(payload, f"response:{endpoint}", issues)
            else:
                issues.append(_issue(
                    "endpoint_payload_not_object",
                    "endpoint payload must be a JSON object",
                    f"$.endpoints.{endpoint}",
                ))
    return _report(_string_value(task.get("task_id"), "unknown"), task_path, issues)


def build_replay_transcript(task_path: Path, session_dir: Path) -> dict[str, Any]:
    task_path = task_path.resolve()
    session_dir = session_dir.resolve()
    task = load_json(task_path)
    task_report = validate_replay_task_payload(task, artifact_path=task_path)
    if task_report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(task_report["issues"]))
    session_report = validate_replay_session(session_dir, task_path)
    if session_report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(session_report["issues"]))
    event_log = load_json(_event_log_path(session_dir))
    event_report = validate_replay_event_log_payload(
        event_log,
        expected_task_id=str(task["task_id"]),
    )
    if event_report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(event_report["issues"]))

    events = [event for event in event_log.get("events", []) if isinstance(event, dict)]
    transcript_events = []
    for event in events:
        endpoint = str(event.get("endpoint", ""))
        response = _response_for_transcript(task_path, task, endpoint)
        transcript_events.append(_transcript_event(event, response))
    transcript = {
        "schema_version": REPLAY_TRANSCRIPT_SCHEMA_VERSION,
        "task_id": task["task_id"],
        "task_path": str(task_path),
        "session_dir": str(session_dir),
        "event_log_path": str(_event_log_path(session_dir)),
        "event_count": len(transcript_events),
        "events": transcript_events,
        "summary": _transcript_summary(transcript_events),
        "what_is_not_concluded": [
            "live API quality",
            "live-web robustness",
            "current citation counts",
            "download reliability",
            "survey completeness",
            "product readiness",
            "scientific correctness",
        ],
    }
    report = validate_replay_transcript_payload(transcript, expected_task_id=str(task["task_id"]))
    if report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(report["issues"]))
    return transcript


def validate_replay_transcript_payload(
    payload: Any,
    expected_task_id: str | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        issues.append(_issue("artifact_not_object", "transcript must be a JSON object", "$"))
        return _report("unknown", None, issues)
    task_id = _string_value(payload.get("task_id"), "unknown")
    if expected_task_id and task_id != expected_task_id:
        issues.append(_issue("wrong_task_id", f"expected task_id {expected_task_id!r}", "$.task_id"))
    if payload.get("schema_version") != REPLAY_TRANSCRIPT_SCHEMA_VERSION:
        issues.append(_issue(
            "wrong_schema_version",
            f"expected schema_version {REPLAY_TRANSCRIPT_SCHEMA_VERSION!r}",
            "$.schema_version",
        ))
    events = payload.get("events")
    if not isinstance(events, list):
        issues.append(_issue("events_not_list", "events must be a list", "$.events"))
    else:
        for index, event in enumerate(events):
            _validate_transcript_event(event, f"$.events[{index}]", issues)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        issues.append(_issue("summary_not_object", "summary must be an object", "$.summary"))
    else:
        for field in ("event_count", "rate_limit_count", "pagination_token_count", "source_blocker_count"):
            value = summary.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                issues.append(_issue(
                    "invalid_summary_count",
                    f"{field} must be a non-negative integer",
                    f"$.summary.{field}",
                ))
    return _report(task_id, None, issues)


def score_replay_submission(
    task_path: Path,
    actual_dir: Path,
    event_log_path: Path,
    gold_dir: Path,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    actual_dir = actual_dir.resolve()
    event_log_path = event_log_path.resolve()
    gold_dir = gold_dir.resolve()
    task = load_json(task_path)
    task_id = _string_value(task.get("task_id"), "unknown")
    errors: list[str] = []
    vetoes: list[str] = []

    task_report = validate_replay_task_payload(task, artifact_path=task_path)
    if task_report["status"] != "passed":
        vetoes.append(REPLAY_SCORE_VETO_HIDDEN_ONLY_FIELD)
        errors.extend(_issue_to_error(issue) for issue in task_report["issues"])

    if _paths_overlap(actual_dir, gold_dir):
        vetoes.append(REPLAY_SCORE_VETO_GOLD_ACTUAL_OVERLAP)
        errors.append(f"actual_dir must be separate from gold_dir: {actual_dir} overlaps {gold_dir}")

    gold_packet = _load_packet_dir(gold_dir, errors, required=True, prefix="gold")
    actual_packet = _load_packet_dir(actual_dir, errors, required=False, prefix="actual")
    if actual_packet.get("citation_map") is None:
        vetoes.append(REPLAY_SCORE_VETO_MISSING_CITATION_MAP)
    missing_files = [
        filename
        for filename in REQUIRED_PACKET_FILES
        if (actual_dir / filename).exists() is False
    ]
    if missing_files:
        vetoes.append(REPLAY_SCORE_VETO_MISSING_PACKET_FILE)
    if missing_files and _looks_prose_only(actual_dir):
        vetoes.append(REPLAY_SCORE_VETO_PROSE_ONLY)

    event_log = None
    if not event_log_path.exists():
        vetoes.append(REPLAY_SCORE_VETO_MISSING_EVENT_LOG)
        errors.append(f"event log missing: {event_log_path}")
    else:
        try:
            session_report = validate_replay_session(event_log_path.parent, task_path)
            if session_report["status"] != "passed":
                vetoes.append(REPLAY_SCORE_VETO_UNTRUSTED_EVENT_LOG)
                errors.extend(_issue_to_error(issue) for issue in session_report["issues"])
            event_log = load_json(event_log_path)
            log_report = validate_replay_event_log_payload(event_log, expected_task_id=task_id)
            if log_report["status"] != "passed":
                vetoes.append(REPLAY_SCORE_VETO_INVALID_EVENT_LOG)
                errors.extend(_issue_to_error(issue) for issue in log_report["issues"])
        except ReplayBenchmarkError as exc:
            vetoes.append(REPLAY_SCORE_VETO_INVALID_EVENT_LOG)
            errors.append(str(exc))

    event_scores = _score_event_log(event_log, vetoes)
    packet_scores = _score_packet(actual_packet, gold_packet, vetoes)
    metric_split = _score_metric_split(actual_packet, gold_packet)

    primary_scores = [
        event_scores["required_call_recall"]["score"],
        packet_scores["citation_map"]["node_recall"]["score"],
        packet_scores["citation_map"]["edge_recall"]["score"],
        packet_scores["citation_map"]["cluster_recall"]["score"],
        packet_scores["candidate_ledger"]["included_recall"]["score"],
        packet_scores["candidate_ledger"]["duplicate_recall"]["score"],
        packet_scores["candidate_ledger"]["excluded_recall"]["score"],
        packet_scores["source_support"]["status_accuracy"]["score"],
        packet_scores["source_support"]["anchor_recall"]["score"],
        packet_scores["claim_support"]["supported_claim_anchor_recall"]["score"],
        packet_scores["omission_risk"]["high_severity_recall"]["score"],
    ]
    status = "passed" if all(score == 1.0 for score in primary_scores) and not errors and not vetoes else "failed"
    return {
        "schema_version": REPLAY_SCORE_REPORT_SCHEMA_VERSION,
        "task_id": task_id,
        "status": status,
        "task_path": str(task_path),
        "actual_dir": str(actual_dir),
        "event_log_path": str(event_log_path),
        "gold_dir": str(gold_dir),
        "scores": {
            "event_log": event_scores,
            **packet_scores,
        },
        "vetoes": sorted(set(vetoes)),
        "errors": errors,
        "diagnostics": {
            "required_packet_files": list(REQUIRED_PACKET_FILES),
            "required_workflow_endpoints": list(REQUIRED_WORKFLOW_ENDPOINTS),
            "metric_split": metric_split,
            "what_is_not_concluded": [
                "live web coverage",
                "real Neural OT completeness",
                "survey prose quality",
                "scientific priority",
                "production readiness",
            ],
        },
    }


def validate_replay_task_payload(
    payload: Any,
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        issues.append(_issue("artifact_not_object", "replay task must be a JSON object", "$"))
        return _report("unknown", artifact_path, issues)

    task_id = _string_value(payload.get("task_id"), "unknown")
    if payload.get("schema_version") != REPLAY_TASK_SCHEMA_VERSION:
        issues.append(_issue(
            "wrong_schema_version",
            f"expected schema_version {REPLAY_TASK_SCHEMA_VERSION!r}",
            "$.schema_version",
        ))
    _require_nonempty_string(payload, "task_id", "$", issues)
    _require_nonempty_string(payload, "topic", "$", issues)
    _validate_seed_papers(payload.get("seed_papers"), issues)
    endpoints = _validate_endpoints(payload.get("endpoints"), issues)
    _validate_budget(payload.get("budget"), "$.budget", issues)
    _validate_evidence_channels(payload.get("evidence_channels"), endpoints, issues)
    _validate_rubric(payload.get("rubric"), issues)
    _find_agent_visible_leaks(payload, "$", issues)
    return _report(task_id, artifact_path, issues)


def validate_replay_event_log_payload(
    payload: Any,
    expected_task_id: str | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        issues.append(_issue("artifact_not_object", "event log must be a JSON object", "$"))
        return _report("unknown", None, issues)
    task_id = _string_value(payload.get("task_id"), "unknown")
    if expected_task_id and task_id != expected_task_id:
        issues.append(_issue(
            "wrong_task_id",
            f"expected task_id {expected_task_id!r}",
            "$.task_id",
        ))
    if payload.get("schema_version") != REPLAY_EVENT_LOG_SCHEMA_VERSION:
        issues.append(_issue(
            "wrong_schema_version",
            f"expected schema_version {REPLAY_EVENT_LOG_SCHEMA_VERSION!r}",
            "$.schema_version",
        ))
    if payload.get("session_manifest") != "session_manifest.json":
        issues.append(_issue(
            "missing_session_manifest_reference",
            "event log must reference session_manifest.json",
            "$.session_manifest",
        ))
    events = payload.get("events")
    if not isinstance(events, list):
        issues.append(_issue("events_not_list", "events must be a list", "$.events"))
    else:
        for index, event in enumerate(events):
            _validate_event(event, f"$.events[{index}]", issues)
    return _report(task_id, None, issues)


def assert_replay_task_valid(payload: dict[str, Any]) -> None:
    report = validate_replay_task_payload(payload)
    if report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(report["issues"]))


def assert_replay_event_log_valid(payload: dict[str, Any], expected_task_id: str | None = None) -> None:
    report = validate_replay_event_log_payload(payload, expected_task_id=expected_task_id)
    if report["status"] != "passed":
        raise ReplayBenchmarkError(_format_issues(report["issues"]))


def validate_replay_session(session_dir: Path, task_path: Path) -> dict[str, Any]:
    session_dir = session_dir.resolve()
    task_path = task_path.resolve()
    issues: list[dict[str, Any]] = []
    manifest_path = _session_manifest_path(session_dir)
    if not manifest_path.exists():
        issues.append(_issue(
            "missing_session_manifest",
            "trusted replay session manifest is missing",
            "$.session_manifest",
        ))
        return _report("unknown", manifest_path, issues)
    manifest = load_json(manifest_path)
    task = load_json(task_path)
    task_id = _string_value(task.get("task_id"), "unknown")
    if manifest.get("schema_version") != REPLAY_SESSION_SCHEMA_VERSION:
        issues.append(_issue(
            "wrong_session_schema_version",
            f"expected schema_version {REPLAY_SESSION_SCHEMA_VERSION!r}",
            "$.schema_version",
        ))
    if manifest.get("task_id") != task_id:
        issues.append(_issue("session_task_mismatch", "session task_id does not match task", "$.task_id"))
    if manifest.get("task_sha256") != _sha256_file(task_path):
        issues.append(_issue("session_task_hash_mismatch", "session task hash does not match task", "$.task_sha256"))
    if manifest.get("generated_by") != "research_assistant.benchmarks.replay.replay_call":
        issues.append(_issue(
            "untrusted_session_generator",
            "session manifest was not generated by replay_call",
            "$.generated_by",
        ))
    return _report(task_id, manifest_path, issues)


def _load_packet_dir(
    packet_dir: Path,
    errors: list[str],
    *,
    required: bool,
    prefix: str,
) -> dict[str, Any]:
    packet: dict[str, Any] = {}
    for filename in REQUIRED_PACKET_FILES:
        key = filename.removesuffix(".json")
        path = packet_dir / filename
        if not path.exists():
            packet[key] = None
            if required:
                errors.append(f"{prefix} packet missing {filename}: {path}")
            continue
        try:
            packet[key] = load_json(path)
        except ReplayBenchmarkError as exc:
            packet[key] = None
            errors.append(str(exc))
    return packet


def _score_event_log(event_log: dict[str, Any] | None, vetoes: list[str]) -> dict[str, Any]:
    if not isinstance(event_log, dict):
        return {
            "required_call_recall": _score_set(set(REQUIRED_WORKFLOW_ENDPOINTS), set()),
            "event_count": 0,
            "blocked_budget_count": 0,
            "hidden_gold_access_count": 0,
        }
    events = [event for event in event_log.get("events", []) if isinstance(event, dict)]
    endpoints = {str(event.get("endpoint")) for event in events}
    call_recall = _score_set(set(REQUIRED_WORKFLOW_ENDPOINTS), endpoints)
    if call_recall["missing"]:
        vetoes.append(REPLAY_SCORE_VETO_MISSING_REQUIRED_CALL)
    blocked_budget_count = sum(1 for event in events if event.get("status") == "blocked_budget")
    if blocked_budget_count:
        vetoes.append(REPLAY_SCORE_VETO_BUDGET_EXCEEDED)
    hidden_gold_count = sum(1 for event in events if event.get("hidden_gold_accessed") is True)
    if hidden_gold_count:
        vetoes.append(REPLAY_SCORE_VETO_INVALID_EVENT_LOG)
    return {
        "required_call_recall": call_recall,
        "event_count": len(events),
        "blocked_budget_count": blocked_budget_count,
        "hidden_gold_access_count": hidden_gold_count,
        "final_budget": events[-1].get("budget_after") if events else None,
    }


def _score_packet(
    actual_packet: dict[str, Any],
    gold_packet: dict[str, Any],
    vetoes: list[str],
) -> dict[str, Any]:
    return {
        "candidate_ledger": _score_candidate_ledger(
            actual_packet.get("candidate_ledger"),
            gold_packet.get("candidate_ledger"),
        ),
        "citation_map": _score_citation_map(
            actual_packet.get("citation_map"),
            gold_packet.get("citation_map"),
        ),
        "source_support": _score_source_support(
            actual_packet.get("source_support"),
            gold_packet.get("source_support"),
        ),
        "claim_support": _score_claim_support(
            actual_packet.get("claim_support"),
            gold_packet.get("claim_support"),
            vetoes,
        ),
        "omission_risk": _score_omission_risk(
            actual_packet.get("omission_risk"),
            gold_packet.get("omission_risk"),
        ),
    }


def _score_candidate_ledger(actual: Any, gold: Any) -> dict[str, Any]:
    actual = actual if isinstance(actual, dict) else {}
    gold = gold if isinstance(gold, dict) else {}
    return {
        "included_recall": _score_set(_included_keys(gold), _included_keys(actual)),
        "duplicate_recall": _score_set(_duplicate_pairs(gold), _duplicate_pairs(actual)),
        "excluded_recall": _score_set(_excluded_keys(gold), _excluded_keys(actual)),
    }


def _score_citation_map(actual: Any, gold: Any) -> dict[str, Any]:
    actual = actual if isinstance(actual, dict) else {}
    gold = gold if isinstance(gold, dict) else {}
    return {
        "node_recall": _score_set(_node_keys(gold), _node_keys(actual)),
        "edge_recall": _score_set(_edge_keys(gold), _edge_keys(actual)),
        "cluster_recall": _score_set(_cluster_keys(gold), _cluster_keys(actual)),
    }


def _score_source_support(actual: Any, gold: Any) -> dict[str, Any]:
    actual_rows = _paper_key_map(actual.get("papers", []) if isinstance(actual, dict) else [])
    gold_rows = _paper_key_map(gold.get("papers", []) if isinstance(gold, dict) else [])
    status_expected = {
        (paper_key, str(row.get("source_status")), str(row.get("download_status")))
        for paper_key, row in gold_rows.items()
    }
    status_actual = {
        (paper_key, str(row.get("source_status")), str(row.get("download_status")))
        for paper_key, row in actual_rows.items()
    }
    anchor_expected = _source_anchor_keys(gold_rows)
    anchor_actual = _source_anchor_keys(actual_rows)
    return {
        "paper_recall": _score_set(set(gold_rows), set(actual_rows)),
        "status_accuracy": _score_set(status_expected, status_actual),
        "anchor_recall": _score_set(anchor_expected, anchor_actual),
    }


def _score_claim_support(actual: Any, gold: Any, vetoes: list[str]) -> dict[str, Any]:
    actual_claims = actual.get("claims", []) if isinstance(actual, dict) else []
    gold_claims = gold.get("claims", []) if isinstance(gold, dict) else []
    actual_supported = _supported_claim_anchor_keys(actual_claims)
    gold_supported = _supported_claim_anchor_keys(gold_claims)
    unsupported = []
    forbidden_hits = []
    nonclaim_rows = nonclaim_rows_in_claims(actual_claims)
    laundering_hits = claim_laundering_hits(actual, gold_claims)
    for row in actual_claims:
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("claim_id", "unknown_claim"))
        status = str(row.get("status", ""))
        support_class = str(row.get("support_class", ""))
        if status == "forbidden":
            continue
        if support_class == "unsupported" or status in {"unsupported", "source_gap"}:
            unsupported.append(claim_id)
        elif status == "supported":
            anchors = row.get("anchors", [])
            has_anchor = isinstance(anchors, list) and any(isinstance(anchor, dict) for anchor in anchors)
            if support_class not in SUPPORTED_CLAIM_SUPPORT_CLASSES or not has_anchor:
                unsupported.append(claim_id)
        if "dominates all normalizing-flow methods" in str(row.get("claim", "")).lower() and status != "forbidden":
            forbidden_hits.append(claim_id)
    if unsupported or nonclaim_rows or laundering_hits:
        vetoes.append(REPLAY_SCORE_VETO_UNSUPPORTED_TECHNICAL_CLAIM)
    if forbidden_hits:
        vetoes.append(REPLAY_SCORE_VETO_FORBIDDEN_CLAIM)
    return {
        "supported_claim_anchor_recall": _score_set(gold_supported, actual_supported),
        "unsupported_nonforbidden_claims": sorted(unsupported),
        "forbidden_claim_hits": sorted(forbidden_hits),
        "nonclaim_rows_in_claims": nonclaim_rows,
        "claim_laundering_hits": laundering_hits,
        "claim_count": len(actual_claims),
    }


def _score_omission_risk(actual: Any, gold: Any) -> dict[str, Any]:
    actual = actual if isinstance(actual, dict) else {}
    gold = gold if isinstance(gold, dict) else {}
    return {
        "high_severity_recall": _score_set(
            _high_severity_risk_keys(gold),
            _high_severity_risk_keys(actual),
        )
    }


def _score_metric_split(actual_packet: dict[str, Any], gold_packet: dict[str, Any]) -> dict[str, Any]:
    actual_citation_map = actual_packet.get("citation_map")
    gold_citation_map = gold_packet.get("citation_map")
    actual_candidate_ledger = actual_packet.get("candidate_ledger")
    gold_candidate_ledger = gold_packet.get("candidate_ledger")
    actual_source_support = actual_packet.get("source_support")
    gold_source_support = gold_packet.get("source_support")
    actual_omission_risk = actual_packet.get("omission_risk")
    gold_omission_risk = gold_packet.get("omission_risk")
    return {
        "citation_map_layers": _score_citation_map_layers(actual_citation_map, gold_citation_map),
        "seed_identity": {
            "duplicate_recall": _score_set(
                _duplicate_pairs(gold_candidate_ledger if isinstance(gold_candidate_ledger, dict) else {}),
                _duplicate_pairs(actual_candidate_ledger if isinstance(actual_candidate_ledger, dict) else {}),
            )
        },
        "frontier": {
            "partial_frontier_omission_recall": _score_set(
                _frontier_risk_keys(gold_omission_risk if isinstance(gold_omission_risk, dict) else {}),
                _frontier_risk_keys(actual_omission_risk if isinstance(actual_omission_risk, dict) else {}),
            )
        },
        "source_depth": _score_source_depth_layers(actual_source_support, gold_source_support),
        "proxy_metric_boundaries": [
            "typed fixture recall is not proof of survey completeness",
            "source-depth status is not proof of technical inspection unless checked anchors are present",
            "offline fixture diagnostics are not live-web coverage or current citation counts",
        ],
    }


def _score_citation_map_layers(actual: Any, gold: Any) -> dict[str, Any]:
    actual = actual if isinstance(actual, dict) else {}
    gold = gold if isinstance(gold, dict) else {}
    return {
        "backward_lineage_edge_recall": _score_set(
            _typed_edge_keys(gold, "cites"),
            _typed_edge_keys(actual, "cites"),
        ),
        "forward_citation_edge_recall": _score_set(
            _typed_edge_keys(gold, "cited_by"),
            _typed_edge_keys(actual, "cited_by"),
        ),
        "adjacent_method_edge_recall": _score_set(
            _typed_edge_keys(gold, "adjacent_method"),
            _typed_edge_keys(actual, "adjacent_method"),
        ),
        "backward_lineage_cluster_recall": _score_set(
            _cluster_keys_containing(gold, "classical"),
            _cluster_keys_containing(actual, "classical"),
        ),
        "forward_method_cluster_recall": _score_set(
            _cluster_keys_containing(gold, "neural"),
            _cluster_keys_containing(actual, "neural"),
        ),
        "adjacent_cluster_recall": _score_set(
            _cluster_keys_containing(gold, "adjacent"),
            _cluster_keys_containing(actual, "adjacent"),
        ),
    }


def _score_source_depth_layers(actual: Any, gold: Any) -> dict[str, Any]:
    actual_rows = _paper_key_map(actual.get("papers", []) if isinstance(actual, dict) else [])
    gold_rows = _paper_key_map(gold.get("papers", []) if isinstance(gold, dict) else [])
    expected_levels = _source_depth_level_keys(gold_rows)
    actual_levels = _source_depth_level_keys(actual_rows)
    return {
        "source_depth_status_accuracy": _score_set(expected_levels, actual_levels),
        "checked_anchor_paper_recall": _score_set(
            _papers_with_checked_anchors(gold_rows),
            _papers_with_checked_anchors(actual_rows),
        ),
        "metadata_or_blocked_without_anchor_count": _metadata_or_blocked_without_anchor_count(actual_rows),
    }


def _typed_edge_keys(payload: dict[str, Any], edge_type: str) -> set[tuple[str, str, str]]:
    return {
        (str(row.get("source")), str(row.get("target")), str(row.get("edge_type")))
        for row in payload.get("edges", [])
        if isinstance(row, dict)
        and row.get("source")
        and row.get("target")
        and str(row.get("edge_type")) == edge_type
    }


def _cluster_keys_containing(payload: dict[str, Any], token: str) -> set[str]:
    return {
        str(row.get("cluster_id"))
        for row in payload.get("clusters", [])
        if isinstance(row, dict)
        and row.get("cluster_id")
        and token in str(row.get("cluster_id")).lower()
    }


def _frontier_risk_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("paper_key"))
        for row in payload.get("risks", [])
        if isinstance(row, dict)
        and row.get("paper_key")
        and (
            "frontier" in str(row.get("paper_key", "")).lower()
            or "frontier" in str(row.get("risk", "")).lower()
            or "continuation" in str(row.get("risk", "")).lower()
        )
    }


def _source_depth_level_keys(rows: dict[str, dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (paper_key, _source_depth_level(row))
        for paper_key, row in rows.items()
    }


def _source_depth_level(row: dict[str, Any]) -> str:
    source_status = str(row.get("source_status", ""))
    download_status = str(row.get("download_status", ""))
    checked_anchors = row.get("checked_anchors", [])
    if source_status in {"metadata_only_fixture", "blocked_fixture"} or download_status == "blocked_fixture":
        return "metadata_or_blocked"
    if isinstance(checked_anchors, list) and checked_anchors:
        return "checked_anchor_available"
    if download_status == "downloaded_fixture":
        return "downloaded_unchecked"
    return "source_gap_or_unchecked"


def _papers_with_checked_anchors(rows: dict[str, dict[str, Any]]) -> set[str]:
    return {
        paper_key
        for paper_key, row in rows.items()
        if isinstance(row.get("checked_anchors"), list) and row["checked_anchors"]
    }


def _metadata_or_blocked_without_anchor_count(rows: dict[str, dict[str, Any]]) -> int:
    count = 0
    for row in rows.values():
        source_status = str(row.get("source_status", ""))
        download_status = str(row.get("download_status", ""))
        checked_anchors = row.get("checked_anchors", [])
        if source_status in {"metadata_only_fixture", "blocked_fixture"} or download_status == "blocked_fixture":
            if not isinstance(checked_anchors, list) or not checked_anchors:
                count += 1
    return count


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


def _included_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("paper_key"))
        for row in payload.get("included", [])
        if isinstance(row, dict) and row.get("paper_key")
    }


def _excluded_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("paper_key"))
        for row in payload.get("excluded", [])
        if isinstance(row, dict) and row.get("paper_key")
    }


def _duplicate_pairs(payload: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in payload.get("duplicates", []):
        if not isinstance(row, dict):
            continue
        canonical = str(row.get("canonical_key", ""))
        for duplicate in row.get("duplicate_keys", []):
            if canonical and duplicate:
                pairs.add((canonical, str(duplicate)))
    return pairs


def _node_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("paper_key"))
        for row in payload.get("nodes", [])
        if isinstance(row, dict) and row.get("paper_key")
    }


def _edge_keys(payload: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (str(row.get("source")), str(row.get("target")), str(row.get("edge_type")))
        for row in payload.get("edges", [])
        if isinstance(row, dict) and row.get("source") and row.get("target") and row.get("edge_type")
    }


def _cluster_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("cluster_id"))
        for row in payload.get("clusters", [])
        if isinstance(row, dict) and row.get("cluster_id")
    }


def _paper_key_map(rows: list[Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("paper_key")): row
        for row in rows
        if isinstance(row, dict) and row.get("paper_key")
    }


def _source_anchor_keys(rows: dict[str, dict[str, Any]]) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for paper_key, row in rows.items():
        for anchor in row.get("checked_anchors", []):
            if isinstance(anchor, dict):
                keys.add((paper_key, str(anchor.get("kind")), str(anchor.get("label"))))
    return keys


def _supported_claim_anchor_keys(claims: list[Any]) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for row in claims:
        if not isinstance(row, dict):
            continue
        if row.get("status") != "supported":
            continue
        for anchor in row.get("anchors", []):
            if isinstance(anchor, dict):
                keys.add((
                    str(anchor.get("paper_key")),
                    str(anchor.get("kind")),
                    str(anchor.get("label")),
                ))
    return keys


def _high_severity_risk_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("paper_key"))
        for row in payload.get("risks", [])
        if isinstance(row, dict)
        and row.get("paper_key")
        and str(row.get("severity", "")).lower() == "high"
    }


def _looks_prose_only(actual_dir: Path) -> bool:
    prose_extensions = {".md", ".txt", ".rst"}
    has_prose = any(path.suffix.lower() in prose_extensions for path in actual_dir.glob("*"))
    has_required_json = any((actual_dir / filename).exists() for filename in REQUIRED_PACKET_FILES)
    return has_prose and not has_required_json


def _issue_to_error(issue: dict[str, Any]) -> str:
    return f"{issue.get('code')} at {issue.get('path')}: {issue.get('message')}"


def _blocked_response(
    task_path: Path,
    task: dict[str, Any],
    endpoint: str,
    request_id: str,
    session_dir: Path,
    status: str,
    message: str,
    *,
    result_count: int = 0,
    lock_held: bool = False,
) -> dict[str, Any]:
    if lock_held:
        _ensure_session_manifest(task_path, task, session_dir)
        budget_before = _current_budget(task, session_dir)
        event = _event(
            task_id=str(task["task_id"]),
            endpoint=endpoint,
            request_id=request_id,
            session_dir=session_dir,
            budget_before=budget_before,
            budget_after=budget_before,
            result_count=result_count,
            status=status,
        )
        _append_event(session_dir, str(task["task_id"]), event)
    else:
        with _event_log_lock(session_dir):
            _ensure_session_manifest(task_path, task, session_dir)
            budget_before = _current_budget(task, session_dir)
            event = _event(
                task_id=str(task["task_id"]),
                endpoint=endpoint,
                request_id=request_id,
                session_dir=session_dir,
                budget_before=budget_before,
                budget_after=budget_before,
                result_count=result_count,
                status=status,
            )
            _append_event(session_dir, str(task["task_id"]), event)
    return {
        "schema_version": "ra-surveybench-online-replay-call-result-v1",
        "status": status,
        "task_id": task["task_id"],
        "endpoint": endpoint,
        "request_id": request_id,
        "budget_before": budget_before,
        "budget_after": budget_before,
        "event_log_path": str(_event_log_path(session_dir)),
        "response": {
            "schema_version": "ra-surveybench-online-replay-response-v1",
            "task_id": task["task_id"],
            "endpoint": endpoint,
            "request_id": request_id,
            "status": status,
            "message": message,
        },
    }


def _event(
    *,
    task_id: str,
    endpoint: str,
    request_id: str,
    session_dir: Path,
    budget_before: dict[str, int],
    budget_after: dict[str, int],
    result_count: int,
    status: str,
) -> dict[str, Any]:
    return {
        "sequence": _next_sequence(session_dir),
        "task_id": task_id,
        "endpoint": endpoint,
        "request_id": request_id,
        "budget_before": budget_before,
        "budget_after": budget_after,
        "result_count": result_count,
        "status": status,
        "agent_visible": True,
        "hidden_gold_accessed": False,
    }


def _event_log_path(session_dir: Path) -> Path:
    return session_dir / "event_log.json"


def _session_manifest_path(session_dir: Path) -> Path:
    return session_dir / "session_manifest.json"


def _ensure_session_manifest(task_path: Path, task: dict[str, Any], session_dir: Path) -> None:
    manifest_path = _session_manifest_path(session_dir)
    manifest = {
        "schema_version": REPLAY_SESSION_SCHEMA_VERSION,
        "task_id": task["task_id"],
        "task_sha256": _sha256_file(task_path),
        "generated_by": "research_assistant.benchmarks.replay.replay_call",
    }
    if manifest_path.exists():
        report = validate_replay_session(session_dir, task_path)
        if report["status"] != "passed":
            raise ReplayBenchmarkError(_format_issues(report["issues"]))
        return
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))


@contextmanager
def _event_log_lock(session_dir: Path):
    session_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = session_dir / ".event_log.lock"
    deadline = time.monotonic() + 5.0
    while True:
        try:
            lock_dir.mkdir()
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise ReplayBenchmarkError(f"timed out waiting for event log lock: {lock_dir}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock_dir.rmdir()
        except FileNotFoundError:
            pass


def _load_event_log(session_dir: Path, task_id: str) -> dict[str, Any]:
    path = _event_log_path(session_dir)
    if not path.exists():
        return {
            "schema_version": REPLAY_EVENT_LOG_SCHEMA_VERSION,
            "task_id": task_id,
            "session_manifest": "session_manifest.json",
            "events": [],
        }
    payload = load_json(path)
    assert_replay_event_log_valid(payload, expected_task_id=task_id)
    return payload


def _append_event(session_dir: Path, task_id: str, event: dict[str, Any]) -> None:
    log = _load_event_log(session_dir, task_id)
    log["events"].append(event)
    assert_replay_event_log_valid(log, expected_task_id=task_id)
    _event_log_path(session_dir).write_text(json.dumps(log, indent=2, sort_keys=True))


def _next_sequence(session_dir: Path) -> int:
    path = _event_log_path(session_dir)
    if not path.exists():
        return 1
    payload = load_json(path)
    events = payload.get("events", [])
    if not isinstance(events, list):
        return 1
    return len(events) + 1


def _current_budget(task: dict[str, Any], session_dir: Path) -> dict[str, int]:
    budget = {counter: int(task["budget"][counter]) for counter in REQUIRED_BUDGET_COUNTERS}
    log_path = _event_log_path(session_dir)
    if not log_path.exists():
        return budget
    log = load_json(log_path)
    assert_replay_event_log_valid(log, expected_task_id=str(task["task_id"]))
    events = log.get("events", [])
    if not events:
        return budget
    last = events[-1]
    if not isinstance(last, dict) or not isinstance(last.get("budget_after"), dict):
        return budget
    return {counter: int(last["budget_after"][counter]) for counter in REQUIRED_BUDGET_COUNTERS}


def _endpoint_cost(endpoint: str, response: dict[str, Any]) -> dict[str, int]:
    cost = {counter: 0 for counter in REQUIRED_BUDGET_COUNTERS}
    cost["endpoint_calls"] = 1
    cost["returned_records"] = _response_result_count(response)
    if endpoint == "paper":
        cost["paper_detail_calls"] = cost["returned_records"]
    if endpoint in {"source-anchors", "evidence-context"}:
        cost["source_anchor_calls"] = cost["returned_records"]
    return cost


def _would_exceed_budget(budget: dict[str, int], cost: dict[str, int]) -> bool:
    return any(budget[counter] - cost[counter] < 0 for counter in REQUIRED_BUDGET_COUNTERS)


def _subtract_budget(budget: dict[str, int], cost: dict[str, int]) -> dict[str, int]:
    return {counter: budget[counter] - cost[counter] for counter in REQUIRED_BUDGET_COUNTERS}


def _response_result_count(response: dict[str, Any]) -> int:
    if isinstance(response.get("result_count"), int):
        return int(response["result_count"])
    for key in ("results", "records", "references", "citations", "adjacent_candidates", "statuses", "anchors", "contexts"):
        value = response.get(key)
        if isinstance(value, list):
            return len(value)
    return 1


def _response_request_id(response: dict[str, Any], endpoint: str) -> str:
    request_id = response.get("request_id")
    if isinstance(request_id, str) and request_id:
        return request_id
    return f"{endpoint}-request"


def _event_status(response: dict[str, Any]) -> str:
    statuses = response.get("source_statuses")
    if isinstance(statuses, list):
        for status in statuses:
            if isinstance(status, dict) and status.get("status") == "simulated_rate_limit":
                return "simulated_rate_limit"
    return "ok"


def _response_for_transcript(task_path: Path, task: dict[str, Any], endpoint: str) -> dict[str, Any] | None:
    response_rel = task.get("endpoints", {}).get(endpoint)
    if not isinstance(response_rel, str):
        return None
    response_path = (task_path.parent / response_rel).resolve()
    if not response_path.exists():
        return None
    response = load_json(response_path)
    return response if isinstance(response, dict) else None


def _transcript_event(event: dict[str, Any], response: dict[str, Any] | None) -> dict[str, Any]:
    endpoint = str(event.get("endpoint", ""))
    response = response if isinstance(response, dict) else {}
    source_statuses = _transcript_source_statuses(response)
    blockers = [
        status
        for status in source_statuses
        if str(status.get("status", "")).lower() in {
            "simulated_rate_limit",
            "blocked_fixture",
            "unavailable",
            "not_attempted",
            "quarantined_or_retracted_fixture",
        }
    ]
    return {
        "sequence": event.get("sequence"),
        "endpoint": endpoint,
        "request_id": event.get("request_id"),
        "status": event.get("status"),
        "result_count": event.get("result_count"),
        "budget_before": event.get("budget_before"),
        "budget_after": event.get("budget_after"),
        "response_request_id": response.get("request_id"),
        "response_status": response.get("status", "ok"),
        "response_result_count": _response_result_count(response) if response else 0,
        "pagination": _transcript_pagination(response),
        "source_statuses": source_statuses,
        "source_blockers": blockers,
        "provenance": _transcript_provenance(endpoint, response),
        "scorer_inputs": {
            "endpoint": endpoint,
            "event_status": event.get("status"),
            "budget_after": event.get("budget_after"),
            "result_count": event.get("result_count"),
        },
    }


def _transcript_pagination(response: dict[str, Any]) -> dict[str, Any]:
    partial_frontier = response.get("partial_frontier")
    return {
        "has_more": response.get("has_more") is True,
        "next_page_token": response.get("next_page_token"),
        "returned_records_cap": response.get("returned_records_cap"),
        "partial_frontier": partial_frontier if isinstance(partial_frontier, dict) else None,
    }


def _transcript_source_statuses(response: dict[str, Any]) -> list[dict[str, Any]]:
    statuses = response.get("source_statuses")
    if isinstance(statuses, list):
        return [status for status in statuses if isinstance(status, dict)]
    statuses = response.get("statuses")
    if isinstance(statuses, list):
        rows = []
        for status in statuses:
            if isinstance(status, dict):
                rows.append({
                    "source": status.get("paper_key", "fixture_status"),
                    "status": status.get("source_status") or status.get("download_status") or "ok",
                    "reason": status.get("reason"),
                })
        return rows
    return []


def _transcript_provenance(endpoint: str, response: dict[str, Any]) -> dict[str, Any]:
    provenance = {
        "endpoint": endpoint,
        "request_id": response.get("request_id"),
        "response_schema_version": response.get("schema_version"),
    }
    if response.get("endpoint"):
        provenance["response_endpoint"] = response.get("endpoint")
    return provenance


def _transcript_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "event_count": len(events),
        "rate_limit_count": sum(1 for event in events if event.get("status") == "simulated_rate_limit"),
        "pagination_token_count": sum(
            1
            for event in events
            if isinstance(event.get("pagination"), dict)
            and event["pagination"].get("next_page_token")
        ),
        "source_blocker_count": sum(
            len(event.get("source_blockers", []))
            for event in events
            if isinstance(event.get("source_blockers"), list)
        ),
        "endpoints": [
            str(event.get("endpoint"))
            for event in events
            if event.get("endpoint")
        ],
    }


def _paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    return first == second or first in second.parents or second in first.parents


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_seed_papers(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, list) or not value:
        issues.append(_issue("missing_seed_papers", "seed_papers must be a non-empty list", "$.seed_papers"))
        return
    for index, seed in enumerate(value):
        path = f"$.seed_papers[{index}]"
        if not isinstance(seed, dict):
            issues.append(_issue("seed_not_object", "seed paper must be an object", path))
            continue
        if not seed.get("paper_key") and not seed.get("identifier"):
            issues.append(_issue(
                "seed_missing_identity",
                "seed paper must include paper_key or identifier",
                path,
            ))


def _validate_endpoints(value: Any, issues: list[dict[str, Any]]) -> set[str]:
    if not isinstance(value, dict):
        issues.append(_issue("endpoints_not_object", "endpoints must be an object", "$.endpoints"))
        return set()
    endpoint_names = {str(name) for name in value}
    missing = sorted(set(REQUIRED_ENDPOINTS) - endpoint_names)
    if missing:
        issues.append(_issue(
            "missing_required_endpoint",
            f"missing required endpoints: {missing}",
            "$.endpoints",
        ))
    leaked_names = sorted(endpoint_names & SCORER_ONLY_ENDPOINT_NAMES)
    if leaked_names:
        issues.append(_issue(
            "scorer_endpoint_exposed",
            f"agent-visible endpoints include scorer-only names: {leaked_names}",
            "$.endpoints",
        ))
    for name, spec in value.items():
        path = f"$.endpoints.{name}"
        if not isinstance(name, str) or not name:
            issues.append(_issue("invalid_endpoint_name", "endpoint names must be non-empty strings", path))
        if isinstance(spec, str):
            if not spec.strip():
                issues.append(_issue("empty_endpoint_spec", "endpoint path must be non-empty", path))
        elif isinstance(spec, dict):
            if not spec.get("response_path") and not spec.get("responses"):
                issues.append(_issue(
                    "endpoint_missing_response",
                    "endpoint object must include response_path or responses",
                    path,
                ))
        else:
            issues.append(_issue(
                "invalid_endpoint_spec",
                "endpoint spec must be a path string or response object",
                path,
            ))
    return endpoint_names


def _validate_budget(value: Any, path: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("budget_not_object", "budget must be an object", path))
        return
    for counter in REQUIRED_BUDGET_COUNTERS:
        current_path = f"{path}.{counter}"
        amount = value.get(counter)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            issues.append(_issue(
                "invalid_budget_counter",
                f"{counter} must be a non-negative integer",
                current_path,
            ))


def _validate_evidence_channels(
    value: Any,
    endpoints: set[str],
    issues: list[dict[str, Any]],
) -> None:
    if not isinstance(value, dict):
        issues.append(_issue(
            "evidence_channels_not_object",
            "evidence_channels must be an object",
            "$.evidence_channels",
        ))
        return
    allowed_channels = endpoints | set(OPTIONAL_EVIDENCE_ENDPOINTS) | {"event_log"}
    for field in REQUIRED_EVIDENCE_FIELDS:
        channel = value.get(field)
        path = f"$.evidence_channels.{field}"
        if channel is None:
            issues.append(_issue(
                "missing_evidence_channel",
                f"{field} must map to visible evidence or a fallback",
                path,
            ))
            continue
        if isinstance(channel, list):
            if not channel:
                issues.append(_issue("empty_evidence_channel", "evidence channel list must be non-empty", path))
                continue
            unknown = sorted(str(name) for name in channel if str(name) not in allowed_channels)
            if unknown:
                issues.append(_issue(
                    "unknown_evidence_endpoint",
                    f"unknown evidence endpoints: {unknown}",
                    path,
                ))
        elif isinstance(channel, dict):
            status = channel.get("status")
            if status not in ALLOWED_EVIDENCE_FALLBACKS:
                issues.append(_issue(
                    "invalid_evidence_fallback",
                    f"fallback status must be one of {sorted(ALLOWED_EVIDENCE_FALLBACKS)}",
                    path,
                ))
            if not channel.get("reason"):
                issues.append(_issue(
                    "missing_evidence_fallback_reason",
                    "fallback evidence channel must include a reason",
                    path,
                ))
        else:
            issues.append(_issue(
                "invalid_evidence_channel",
                "evidence channel must be a list or fallback object",
                path,
            ))


def _validate_rubric(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("rubric_not_object", "rubric must be an object", "$.rubric"))
        return
    if value.get("schema_version") != REPLAY_RUBRIC_SCHEMA_VERSION:
        issues.append(_issue(
            "wrong_rubric_schema_version",
            f"expected rubric schema_version {REPLAY_RUBRIC_SCHEMA_VERSION!r}",
            "$.rubric.schema_version",
        ))
    for field in RUBRIC_LIST_FIELDS_REQUIRED_NONEMPTY:
        _validate_string_list(value.get(field), f"$.rubric.{field}", issues, allow_empty=False)
    for field in RUBRIC_LIST_FIELDS_REQUIRED:
        _validate_string_list(value.get(field), f"$.rubric.{field}", issues, allow_empty=True)
    ambiguity = value.get("ambiguity")
    if not isinstance(ambiguity, dict):
        issues.append(_issue("ambiguity_not_object", "rubric.ambiguity must be an object", "$.rubric.ambiguity"))
    elif ambiguity.get("allow_insufficient_evidence") is not True:
        issues.append(_issue(
            "insufficient_evidence_not_allowed",
            "rubric must explicitly allow insufficient_evidence",
            "$.rubric.ambiguity.allow_insufficient_evidence",
        ))


def _validate_event(event: Any, path: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(event, dict):
        issues.append(_issue("event_not_object", "event must be an object", path))
        return
    for field in ("sequence", "result_count"):
        value = event.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            issues.append(_issue(
                "invalid_event_integer",
                f"{field} must be a non-negative integer",
                f"{path}.{field}",
            ))
    for field in ("endpoint", "request_id"):
        _require_nonempty_string(event, field, path, issues)
    status = event.get("status")
    if status not in ALLOWED_EVENT_STATUSES:
        issues.append(_issue(
            "invalid_event_status",
            f"status must be one of {sorted(ALLOWED_EVENT_STATUSES)}",
            f"{path}.status",
        ))
    if not isinstance(event.get("agent_visible"), bool):
        issues.append(_issue("invalid_agent_visible", "agent_visible must be a boolean", f"{path}.agent_visible"))
    if not isinstance(event.get("hidden_gold_accessed"), bool):
        issues.append(_issue(
            "invalid_hidden_gold_accessed",
            "hidden_gold_accessed must be a boolean",
            f"{path}.hidden_gold_accessed",
        ))
    elif event.get("agent_visible") is True and event.get("hidden_gold_accessed") is True:
        issues.append(_issue(
            "agent_visible_hidden_gold_access",
            "agent-visible replay events must not access hidden gold",
            f"{path}.hidden_gold_accessed",
        ))
    before = event.get("budget_before")
    after = event.get("budget_after")
    _validate_budget(before, f"{path}.budget_before", issues)
    _validate_budget(after, f"{path}.budget_after", issues)
    if isinstance(before, dict) and isinstance(after, dict):
        for counter in REQUIRED_BUDGET_COUNTERS:
            before_value = before.get(counter)
            after_value = after.get(counter)
            if isinstance(before_value, int) and isinstance(after_value, int) and after_value > before_value:
                issues.append(_issue(
                    "budget_counter_increased",
                    f"{counter} increased from {before_value} to {after_value}",
                    f"{path}.budget_after.{counter}",
                ))


def _validate_transcript_event(event: Any, path: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(event, dict):
        issues.append(_issue("event_not_object", "transcript event must be an object", path))
        return
    for field in ("sequence", "result_count", "response_result_count"):
        value = event.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            issues.append(_issue(
                "invalid_event_integer",
                f"{field} must be a non-negative integer",
                f"{path}.{field}",
            ))
    for field in ("endpoint", "request_id", "status"):
        _require_nonempty_string(event, field, path, issues)
    if not isinstance(event.get("budget_before"), dict):
        issues.append(_issue("budget_before_not_object", "budget_before must be an object", f"{path}.budget_before"))
    if not isinstance(event.get("budget_after"), dict):
        issues.append(_issue("budget_after_not_object", "budget_after must be an object", f"{path}.budget_after"))
    if not isinstance(event.get("pagination"), dict):
        issues.append(_issue("pagination_not_object", "pagination must be an object", f"{path}.pagination"))
    if not isinstance(event.get("source_statuses"), list):
        issues.append(_issue("source_statuses_not_list", "source_statuses must be a list", f"{path}.source_statuses"))
    if not isinstance(event.get("source_blockers"), list):
        issues.append(_issue("source_blockers_not_list", "source_blockers must be a list", f"{path}.source_blockers"))
    if not isinstance(event.get("provenance"), dict):
        issues.append(_issue("provenance_not_object", "provenance must be an object", f"{path}.provenance"))
    scorer_inputs = event.get("scorer_inputs")
    if not isinstance(scorer_inputs, dict):
        issues.append(_issue("scorer_inputs_not_object", "scorer_inputs must be an object", f"{path}.scorer_inputs"))
    elif scorer_inputs.get("endpoint") != event.get("endpoint"):
        issues.append(_issue(
            "scorer_endpoint_mismatch",
            "scorer_inputs endpoint must match transcript endpoint",
            f"{path}.scorer_inputs.endpoint",
        ))


def _validate_string_list(
    value: Any,
    path: str,
    issues: list[dict[str, Any]],
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(value, list):
        issues.append(_issue("field_not_list", "field must be a list", path))
        return
    if not value and not allow_empty:
        issues.append(_issue("field_empty", "field must be non-empty", path))
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(_issue(
                "invalid_string_list_item",
                "list items must be non-empty strings",
                f"{path}[{index}]",
            ))


def _find_agent_visible_leaks(value: Any, path: str, issues: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_lower = str(key).lower()
            if key_lower in AGENT_VISIBLE_FORBIDDEN_KEYS or key_lower.startswith("expected_"):
                issues.append(_issue(
                    "agent_visible_gold_key",
                    f"agent-visible replay task contains scorer-only key {key!r}",
                    child_path,
                ))
            _find_agent_visible_leaks(child, child_path, issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _find_agent_visible_leaks(child, f"{path}[{index}]", issues)
    elif isinstance(value, str):
        lower = value.lower()
        for token in AGENT_VISIBLE_FORBIDDEN_VALUE_TOKENS:
            if token in lower:
                issues.append(_issue(
                    "agent_visible_gold_value",
                    f"agent-visible replay task contains scorer-only token {token!r}",
                    path,
                ))
                break


def _require_nonempty_string(
    payload: dict[str, Any],
    field: str,
    parent_path: str,
    issues: list[dict[str, Any]],
) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(_issue(
            "missing_string_field",
            f"{field} must be a non-empty string",
            f"{parent_path}.{field}",
        ))


def _issue(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def _report(task_id: str, artifact_path: Path | None, issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": REPLAY_VALIDATION_REPORT_SCHEMA_VERSION,
        "task_id": task_id,
        "artifact_path": str(artifact_path) if artifact_path else None,
        "status": "passed" if not issues else "failed",
        "issue_count": len(issues),
        "issues": issues,
        "what_is_not_concluded": [
            "fixture realism",
            "CLI endpoint behavior",
            "scoring correctness",
            "live web coverage",
            "survey quality",
        ],
    }


def _format_issues(issues: list[dict[str, Any]]) -> str:
    return "; ".join(f"{issue['code']} at {issue['path']}: {issue['message']}" for issue in issues)


def _string_value(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback
