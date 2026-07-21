from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_assistant.benchmarks.claim_guard import nonclaim_rows_in_claims
from research_assistant.benchmarks.replay import (
    REPLAY_EVENT_LOG_SCHEMA_VERSION,
    REPLAY_SESSION_SCHEMA_VERSION,
    load_json,
)


HELPER_SCHEMA_VERSION = "ra-surveybench-helper-v1"
PACKET_TEMPLATE_SCHEMA_VERSION = "ra-surveybench-packet-template-v1"
PACKET_COMPOSE_SCHEMA_VERSION = "ra-surveybench-packet-compose-v1"
VISIBLE_REPLAY_PACKET_SCHEMA_VERSION = "ra-surveybench-visible-replay-packet-v1"
READY_FOR_PROSE_SCHEMA_VERSION = "ra-surveybench-ready-for-prose-v1"
LAUNCH_RECORD_TEMPLATE_SCHEMA_VERSION = "ra-surveybench-launch-record-template-v1"
CLUSTER_HINTS_SCHEMA_VERSION = "ra-surveybench-cluster-hints-v1"
TRIAL_RECORD_SCHEMA_VERSION = "ra-surveybench-restricted-agent-trial-record-v1"
PAPER_CLASSIFICATIONS_SCHEMA_VERSION = "ra-surveybench-paper-classifications-v1"

REQUIRED_PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
)

REQUIRED_REPLAY_ENDPOINTS = (
    "search",
    "references",
    "citations",
    "adjacent",
    "download-status",
    "source-anchors",
)

OPTIONAL_REPLAY_ENDPOINTS = (
    "paper",
    "source-status",
    "evidence-context",
)

PACKET_COMPOSE_REQUIRED_RESPONSE_ENDPOINTS = (
    "search",
    "paper",
    "references",
    "citations",
    "adjacent",
    "download-status",
    "source-status",
    "source-anchors",
    "evidence-context",
)

CLUSTER_HINT_REQUIRED_RESPONSE_ENDPOINTS = (
    "references",
    "citations",
    "adjacent",
)

CLUSTER_HINT_OPTIONAL_RESPONSE_ENDPOINTS = (
    "search",
    "paper",
)

PACKET_SCHEMAS = {
    "candidate_ledger.json": "ra-surveybench-candidate-ledger-v1",
    "citation_map.json": "ra-surveybench-citation-map-v1",
    "source_support.json": "ra-surveybench-source-support-v1",
    "paper_classifications.json": "ra-surveybench-paper-classifications-v1",
    "claim_support.json": "ra-surveybench-claim-support-v1",
    "omission_risk.json": "ra-surveybench-omission-risk-v1",
}

SUBJECT_HELPER_FORBIDDEN_TOKENS = (
    "answer_key",
    "answer-key",
    "claim_laundering_hits",
    "expected_claim_support",
    "expected_outputs",
    "expected_packet",
    "gold_packet",
    "hidden_gold",
    "laundering diagnostic",
    "nonclaim_rows_in_claims",
    "rubric",
    "scorer_packet",
    "seeded negative",
)


def surveybench_next_action(
    task_path: Path,
    session_dir: Path | None = None,
    actual_dir: Path | None = None,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    task = load_json(task_path)
    session_dir = session_dir.resolve() if session_dir else None
    actual_dir = actual_dir.resolve() if actual_dir else None
    events = _load_events(session_dir)
    called = {str(event.get("endpoint")) for event in events if isinstance(event, dict)}
    missing_required_endpoints = [
        endpoint
        for endpoint in REQUIRED_REPLAY_ENDPOINTS
        if endpoint in task.get("endpoints", {}) and endpoint not in called
    ]
    available_optional_endpoints = [
        endpoint
        for endpoint in OPTIONAL_REPLAY_ENDPOINTS
        if endpoint in task.get("endpoints", {}) and endpoint not in called
    ]
    missing_packet_files = _missing_packet_files(actual_dir)
    next_endpoint = missing_required_endpoints[0] if missing_required_endpoints else None
    packet_issues = _packet_content_issues(actual_dir) if actual_dir else []
    next_action = "write_packet_files"
    if next_endpoint:
        next_action = "call_replay_endpoint"
    elif actual_dir is not None and (missing_packet_files or packet_issues):
        next_action = "compose_packet_files"
    elif missing_packet_files:
        next_action = "write_packet_files"
    else:
        next_action = "ready_for_prose_check"
    return {
        "schema_version": HELPER_SCHEMA_VERSION,
        "helper": "next-action",
        "task_id": str(task.get("task_id", "unknown")),
        "next_action": next_action,
        "next_endpoint": next_endpoint,
        "missing_required_endpoints": missing_required_endpoints,
        "available_optional_endpoints": available_optional_endpoints,
        "missing_packet_files": missing_packet_files,
        "packet_issues": packet_issues,
        "event_count": len(events),
        "derivation_sources": [
            "task.endpoints",
            "agent-visible event_log events",
            "visible output directory filenames",
            "schema-only required packet filenames",
        ],
        "what_is_not_concluded": [
            "submission correctness",
            "survey quality",
            "live-web coverage",
            "scientific validity",
        ],
    }


def surveybench_packet_compose(
    task_path: Path,
    output_dir: Path,
    *,
    session_dir: Path | None = None,
    responses_dir: Path | None = None,
    write_files: bool = False,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    output_dir = output_dir.resolve()
    session_dir = session_dir.resolve() if session_dir else None
    responses_dir = responses_dir.resolve() if responses_dir else None
    task = load_json(task_path)
    task_id = str(task.get("task_id", "unknown"))
    events = _load_events(session_dir)
    called = {str(event.get("endpoint")) for event in events if isinstance(event, dict)}
    payloads, response_sources, skipped_sensitive_source_count = _load_packet_compose_responses(
        task_path,
        task,
        responses_dir,
    )
    missing_response_sources = [
        endpoint
        for endpoint in PACKET_COMPOSE_REQUIRED_RESPONSE_ENDPOINTS
        if endpoint in task.get("endpoints", {}) and endpoint not in payloads
    ]
    missing_session_calls = [
        endpoint
        for endpoint in REQUIRED_REPLAY_ENDPOINTS
        if session_dir is not None and endpoint in task.get("endpoints", {}) and endpoint not in called
    ]
    status = (
        "ready"
        if not missing_response_sources
        and not missing_session_calls
        and skipped_sensitive_source_count == 0
        else "blocked"
    )
    packet: dict[str, dict[str, Any]] = {}
    trial_record: dict[str, Any] | None = None
    written_files: list[str] = []
    if status == "ready":
        packet = _compose_packet_from_visible_replay(task, payloads)
        packet["paper_classifications.json"] = _compose_paper_classifications(task, payloads)
        trial_record = _compose_trial_record(task, events, payloads)
        if write_files:
            output_dir.mkdir(parents=True, exist_ok=True)
            for filename in REQUIRED_PACKET_FILES:
                payload = packet[filename]
                path = output_dir / filename
                path.write_text(json.dumps(payload, indent=2, sort_keys=True))
                written_files.append(str(path))
            trial_record_path = output_dir / "trial_record.json"
            trial_record_path.write_text(json.dumps(trial_record, indent=2, sort_keys=True))
            written_files.append(str(trial_record_path))
    return {
        "schema_version": PACKET_COMPOSE_SCHEMA_VERSION,
        "helper": "packet-compose",
        "task_id": task_id,
        "status": status,
        "required_packet_files": list(REQUIRED_PACKET_FILES),
        "trial_record_file": "trial_record.json",
        "written_files": written_files,
        "packet_file_summaries": _packet_file_summaries(packet),
        "missing_response_sources": missing_response_sources,
        "missing_session_calls": missing_session_calls,
        "loaded_response_sources": response_sources,
        "skipped_sensitive_source_count": skipped_sensitive_source_count,
        "event_count": len(events),
        "derivation_sources": [
            "task.topic and task.seed_papers",
            "agent-visible replay response files",
            "agent-visible event_log events when a session is supplied",
            "schema-only packet field contracts",
        ],
        "derivation_rules": [
            "seed, duplicate, lineage, forward-citation, adjacent, false-positive, and quarantine rows are derived from visible replay relations and status payloads",
            "source and download support rows are derived from visible source-status, download-status, and source-anchors payloads",
            "supported claim rows are derived from visible evidence-context anchors and graph edge anchors",
            "omission risks are derived from visible backward lineage, adjacent candidates, and partial forward-frontier markers",
        ],
        "what_is_not_concluded": [
            "scorer pass",
            "survey prose quality",
            "live-web coverage",
            "scientific completeness",
            "product readiness",
        ],
    }


def surveybench_visible_replay_packet(
    task_path: Path,
    *,
    responses_dir: Path | None = None,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    responses_dir = responses_dir.resolve() if responses_dir else None
    task = load_json(task_path)
    task_id = str(task.get("task_id", "unknown"))
    payloads, response_sources, skipped_sensitive_source_count = _load_packet_compose_responses(
        task_path,
        task,
        responses_dir,
    )
    missing_response_sources = [
        endpoint
        for endpoint in PACKET_COMPOSE_REQUIRED_RESPONSE_ENDPOINTS
        if endpoint in task.get("endpoints", {}) and endpoint not in payloads
    ]
    status = "ready" if not missing_response_sources and skipped_sensitive_source_count == 0 else "blocked"
    packet: dict[str, dict[str, Any]] = {}
    if status == "ready":
        packet = _compose_packet_from_visible_replay(task, payloads)
        packet["paper_classifications.json"] = _compose_paper_classifications(task, payloads)
    return {
        "schema_version": VISIBLE_REPLAY_PACKET_SCHEMA_VERSION,
        "helper": "visible-replay-packet",
        "task_id": task_id,
        "topic": str(task.get("topic", "")),
        "status": status,
        "packet": packet,
        "packet_file_summaries": _packet_file_summaries(packet),
        "missing_response_sources": missing_response_sources,
        "loaded_response_sources": response_sources,
        "skipped_sensitive_source_count": skipped_sensitive_source_count,
        "derivation_sources": [
            "task.topic and task.seed_papers",
            "agent-visible replay response files",
            "schema-only packet field contracts",
        ],
        "what_is_not_concluded": [
            "ready-for-prose status",
            "live-web coverage",
            "scientific completeness",
            "product readiness",
        ],
    }


def surveybench_packet_template(
    task_path: Path,
    output_dir: Path | None = None,
    *,
    write_files: bool = False,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    task = load_json(task_path)
    task_id = str(task.get("task_id", "unknown"))
    templates = _packet_templates(task_id)
    written_files: list[str] = []
    if write_files:
        if output_dir is None:
            raise ValueError("output_dir is required when write_files=True")
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in templates.items():
            path = output_dir / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True))
            written_files.append(str(path))
    return {
        "schema_version": PACKET_TEMPLATE_SCHEMA_VERSION,
        "helper": "packet-template",
        "task_id": task_id,
        "required_packet_files": list(REQUIRED_PACKET_FILES),
        "templates": templates,
        "written_files": written_files,
        "derivation_sources": [
            "task.task_id",
            "schema-only packet filenames",
            "schema-only artifact fields",
        ],
        "what_is_not_concluded": [
            "packet completeness",
            "scorer pass",
            "survey prose readiness",
        ],
    }


def surveybench_ready_for_prose(
    task_path: Path,
    actual_dir: Path,
    session_dir: Path | None = None,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    task = load_json(task_path)
    actual_dir = actual_dir.resolve()
    session_dir = session_dir.resolve() if session_dir else None
    events = _load_events(session_dir)
    called = {str(event.get("endpoint")) for event in events if isinstance(event, dict)}
    missing_required_endpoints = [
        endpoint
        for endpoint in REQUIRED_REPLAY_ENDPOINTS
        if endpoint in task.get("endpoints", {}) and endpoint not in called
    ]
    missing_packet_files = _missing_packet_files(actual_dir)
    invalid_packets = _invalid_packet_files(actual_dir)
    packet_issues = _packet_content_issues(actual_dir)
    blocked_reasons: list[str] = []
    if missing_required_endpoints:
        blocked_reasons.append("missing_required_replay_calls")
    if missing_packet_files:
        blocked_reasons.append("missing_packet_files")
    if invalid_packets:
        blocked_reasons.append("invalid_packet_json_or_schema")
    if packet_issues:
        blocked_reasons.append("packet_content_incomplete")
    status = "ready" if not blocked_reasons else "blocked"
    return {
        "schema_version": READY_FOR_PROSE_SCHEMA_VERSION,
        "helper": "ready-for-prose",
        "task_id": str(task.get("task_id", "unknown")),
        "status": status,
        "blocked_reasons": blocked_reasons,
        "missing_required_endpoints": missing_required_endpoints,
        "missing_packet_files": missing_packet_files,
        "invalid_packet_files": invalid_packets,
        "packet_issues": packet_issues,
        "required_packet_files": list(REQUIRED_PACKET_FILES),
        "event_count": len(events),
        "derivation_sources": [
            "task.endpoints",
            "agent-visible event_log events",
            "visible output directory filenames and JSON schema_version fields",
            "visible packet content shape",
        ],
        "what_is_not_concluded": [
            "scorer pass",
            "claim support correctness",
            "survey quality",
            "live-web coverage",
        ],
    }


def surveybench_launch_record_template(task_path: Path) -> dict[str, Any]:
    task_path = task_path.resolve()
    task = load_json(task_path)
    return {
        "schema_version": LAUNCH_RECORD_TEMPLATE_SCHEMA_VERSION,
        "helper": "launch-record-template",
        "task_id": str(task.get("task_id", "unknown")),
        "topic": str(task.get("topic", "")),
        "seed_papers": task.get("seed_papers", []),
        "launch_record": {
            "supervisor": "codex",
            "reviewer": "claude-read-only",
            "model": "",
            "effort": "",
            "budget_limit": None,
            "workspace_root": "",
            "task_path": str(task_path),
            "session_dir": "",
            "actual_dir": "",
            "allowed_commands": [
            "python -m research_assistant.cli surveybench replay-call",
            "python -m research_assistant.cli surveybench next-action",
            "python -m research_assistant.cli surveybench cluster-hints",
            "python -m research_assistant.cli surveybench packet-template",
            "python -m research_assistant.cli surveybench packet-compose",
            "python -m research_assistant.cli surveybench ready-for-prose",
        ],
            "forbidden_boundaries": [
                "live network/API",
                "hidden gold/scorer packet access",
                "real blinded subject launch without separate review",
                "product or scientific readiness claims",
            ],
            "required_artifacts": [
                "event_log.json",
                *REQUIRED_PACKET_FILES,
            ],
            "stop_conditions": [
                "budget mismatch",
                "hidden-gold exposure",
                "manual packet repair required",
                "unsupported claim/non-claim confusion",
            ],
        },
        "derivation_sources": [
            "task.task_id",
            "task.topic",
            "task.seed_papers",
            "schema-only launch record fields",
        ],
        "what_is_not_concluded": [
            "launch approval",
            "runtime budget availability",
            "agent reliability",
        ],
    }


def surveybench_cluster_hints(
    task_path: Path,
    responses_dir: Path | None = None,
) -> dict[str, Any]:
    task_path = task_path.resolve()
    task = load_json(task_path)
    responses_dir = responses_dir.resolve() if responses_dir else None
    payloads, response_sources, skipped_sensitive_source_count = _load_cluster_hint_responses(
        task_path,
        task,
        responses_dir,
    )
    task_id = str(task.get("task_id", "unknown"))
    missing_response_sources = [
        endpoint
        for endpoint in CLUSTER_HINT_REQUIRED_RESPONSE_ENDPOINTS
        if endpoint not in payloads
    ]
    clusters: dict[str, dict[str, Any]] = {}
    seed_cluster_id = _seed_cluster_id(task, payloads)
    for seed in _list_dicts(task.get("seed_papers")):
        paper_key = _string_or_none(seed.get("paper_key"))
        if paper_key:
            _add_cluster_hint(
                clusters,
                cluster_id=seed_cluster_id,
                role="seed_method",
                paper_keys=[paper_key],
                evidence={
                    "source": "task.seed_papers",
                    "paper_keys": [paper_key],
                    "visible_fields": ["paper_key", "role"],
                },
            )
    for reference in _list_dicts(payloads.get("references", {}).get("references")):
        if reference.get("relation") != "seed_cites_reference":
            continue
        paper_key = _string_or_none(reference.get("paper_key"))
        source_key = _string_or_none(reference.get("source_paper_key"))
        if not paper_key:
            continue
        evidence_keys = [key for key in (source_key, paper_key) if key]
        _add_cluster_hint(
            clusters,
            cluster_id=_backward_lineage_cluster_id(task),
            role="backward_lineage",
            paper_keys=[paper_key],
            evidence={
                "endpoint": "references",
                "relation": "seed_cites_reference",
                "paper_keys": evidence_keys,
                "evidence": _string_or_none(reference.get("evidence")),
            },
        )
    for citation in _list_dicts(payloads.get("citations", {}).get("citations")):
        if citation.get("relation") != "cites_seed":
            continue
        citing_key = _string_or_none(citation.get("citing_paper_key"))
        target_key = _string_or_none(citation.get("target_paper_key"))
        if not citing_key:
            continue
        evidence_keys = [key for key in (citing_key, target_key) if key]
        _add_cluster_hint(
            clusters,
            cluster_id=seed_cluster_id,
            role="forward_citation",
            paper_keys=[citing_key],
            evidence={
                "endpoint": "citations",
                "relation": "cites_seed",
                "paper_keys": evidence_keys,
                "evidence": _string_or_none(citation.get("evidence")),
            },
        )
    excluded_adjacent_hints: list[dict[str, Any]] = []
    for candidate in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates")):
        paper_key = _string_or_none(candidate.get("paper_key"))
        cluster_hint = _string_or_none(candidate.get("cluster_hint"))
        relation = _string_or_none(candidate.get("relation"))
        if not paper_key or not cluster_hint:
            continue
        if relation == "adjacent_method":
            _add_cluster_hint(
                clusters,
                cluster_id=cluster_hint,
                role="adjacent_cluster",
                paper_keys=[paper_key],
                evidence={
                    "endpoint": "adjacent",
                    "relation": "adjacent_method",
                    "paper_keys": [paper_key],
                    "cluster_hint": cluster_hint,
                    "evidence": _string_or_none(candidate.get("reason")),
                },
            )
            continue
        excluded_adjacent_hints.append({
            "paper_key": paper_key,
            "cluster_hint": cluster_hint,
            "relation": relation,
            "reason": "visible adjacent response did not mark this as an adjacent method",
        })
    return {
        "schema_version": CLUSTER_HINTS_SCHEMA_VERSION,
        "helper": "cluster-hints",
        "task_id": task_id,
        "status": "ready" if not missing_response_sources and skipped_sensitive_source_count == 0 else "blocked",
        "clusters": _sorted_clusters(clusters),
        "excluded_adjacent_hints": sorted(
            excluded_adjacent_hints,
            key=lambda row: (str(row.get("cluster_hint", "")), str(row.get("paper_key", ""))),
        ),
        "missing_response_sources": missing_response_sources,
        "loaded_response_sources": response_sources,
        "skipped_sensitive_source_count": skipped_sensitive_source_count,
        "derivation_sources": [
            "task.seed_papers",
            "task.topic",
            "visible search or paper response titles when available",
            "visible references response relations",
            "visible citations response relations",
            "visible adjacent response cluster hints",
        ],
        "derivation_rules": [
            "seed papers are assigned to a topic-derived method cluster",
            "seed_cites_reference indicates a backward lineage cluster",
            "cites_seed indicates a forward citation in the seed method cluster",
            "adjacent_method uses the adjacent response cluster_hint field",
            "other adjacent candidates are listed as excluded hints",
        ],
        "what_is_not_concluded": [
            "scientific taxonomy truth",
            "complete literature coverage",
            "survey quality",
            "live-web coverage",
            "evaluator pass",
        ],
    }


def scan_subject_helper_payload(payload: Any) -> dict[str, Any]:
    text = json.dumps(payload, sort_keys=True).lower()
    hits = [token for token in SUBJECT_HELPER_FORBIDDEN_TOKENS if token in text]
    return {
        "schema_version": "ra-surveybench-helper-leak-scan-v1",
        "status": "passed" if not hits else "failed",
        "forbidden_token_hits": hits,
    }


def _load_events(session_dir: Path | None) -> list[dict[str, Any]]:
    if session_dir is None:
        return []
    event_log_path = session_dir / "event_log.json"
    if not event_log_path.exists():
        return []
    event_log = load_json(event_log_path)
    if event_log.get("schema_version") != REPLAY_EVENT_LOG_SCHEMA_VERSION:
        return []
    events = event_log.get("events", [])
    return [event for event in events if isinstance(event, dict)]


def _missing_packet_files(actual_dir: Path | None) -> list[str]:
    if actual_dir is None:
        return list(REQUIRED_PACKET_FILES)
    return [filename for filename in REQUIRED_PACKET_FILES if not (actual_dir / filename).exists()]


def _invalid_packet_files(actual_dir: Path) -> list[str]:
    invalid: list[str] = []
    for filename in REQUIRED_PACKET_FILES:
        path = actual_dir / filename
        if not path.exists():
            continue
        try:
            payload = load_json(path)
        except Exception:
            invalid.append(filename)
            continue
        if payload.get("schema_version") != PACKET_SCHEMAS[filename]:
            invalid.append(filename)
    return invalid


def _packet_content_issues(actual_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not actual_dir.exists():
        return issues
    for filename in REQUIRED_PACKET_FILES:
        path = actual_dir / filename
        if not path.exists():
            continue
        try:
            payload = load_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        issues.extend(_packet_payload_content_issues(filename, payload))
    return sorted(issues, key=lambda row: (str(row.get("file")), str(row.get("code")), str(row.get("field", ""))))


def _packet_payload_content_issues(filename: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    required_nonempty_fields = {
        "candidate_ledger.json": ("included",),
        "citation_map.json": ("nodes", "edges", "clusters"),
        "source_support.json": ("papers",),
        "paper_classifications.json": ("classifications",),
        "claim_support.json": ("claims",),
        "omission_risk.json": ("risks",),
    }
    for field in required_nonempty_fields.get(filename, ()):
        value = payload.get(field)
        if not isinstance(value, list) or len(value) == 0:
            issues.append({
                "file": filename,
                "field": field,
                "code": "required_list_empty",
                "message": f"{field} must contain at least one row before prose drafting",
            })
    if filename == "claim_support.json":
        claims = payload.get("claims")
        if isinstance(claims, list):
            nonclaim_rows = nonclaim_rows_in_claims(claims)
            if nonclaim_rows:
                issues.append({
                    "file": filename,
                    "field": "claims",
                    "code": "nonclaim_rows_in_claims",
                    "claim_ids": nonclaim_rows,
                    "message": "non-claims belong in metadata, not supported claim rows",
                })
            for index, row in enumerate(claims):
                if not isinstance(row, dict):
                    continue
                if row.get("status") != "supported":
                    continue
                anchors = row.get("anchors")
                if not isinstance(anchors, list) or not any(isinstance(anchor, dict) for anchor in anchors):
                    issues.append({
                        "file": filename,
                        "field": f"claims[{index}].anchors",
                        "code": "supported_claim_without_anchor",
                        "claim_id": row.get("claim_id", "unknown_claim"),
                        "message": "supported claims need at least one visible anchor before prose drafting",
                    })
                if row.get("support_class") == "unsupported":
                    issues.append({
                        "file": filename,
                        "field": f"claims[{index}].support_class",
                        "code": "supported_claim_unsupported_class",
                        "claim_id": row.get("claim_id", "unknown_claim"),
                        "message": "supported claims cannot use unsupported support_class",
                    })
    return issues


def _packet_templates(task_id: str) -> dict[str, dict[str, Any]]:
    return {
        "candidate_ledger.json": {
            "schema_version": PACKET_SCHEMAS["candidate_ledger.json"],
            "task_id": task_id,
            "included": [],
            "duplicates": [],
            "excluded": [],
            "what_is_not_concluded": [],
        },
        "citation_map.json": {
            "schema_version": PACKET_SCHEMAS["citation_map.json"],
            "task_id": task_id,
            "nodes": [],
            "edges": [],
            "clusters": [],
            "artifact_paths": {},
            "what_is_not_concluded": [],
        },
        "source_support.json": {
            "schema_version": PACKET_SCHEMAS["source_support.json"],
            "task_id": task_id,
            "papers": [],
            "what_is_not_concluded": [],
        },
        "claim_support.json": {
            "schema_version": PACKET_SCHEMAS["claim_support.json"],
            "task_id": task_id,
            "claims": [],
            "what_is_not_concluded": [],
        },
        "paper_classifications.json": {
            "schema_version": PACKET_SCHEMAS["paper_classifications.json"],
            "task_id": task_id,
            "classifications": [],
            "allowed_labels": [],
            "what_is_not_concluded": [],
        },
        "omission_risk.json": {
            "schema_version": PACKET_SCHEMAS["omission_risk.json"],
            "task_id": task_id,
            "risks": [],
            "what_is_not_concluded": [],
        },
    }


def _load_packet_compose_responses(
    task_path: Path,
    task: dict[str, Any],
    responses_dir: Path | None,
) -> tuple[dict[str, dict[str, Any]], list[str], int]:
    payloads: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    skipped_sensitive_source_count = 0
    if responses_dir is not None:
        for response_path in sorted(responses_dir.glob("*.json")):
            if _contains_subject_helper_forbidden_token(response_path.as_posix()):
                skipped_sensitive_source_count += 1
                continue
            payload = _unwrap_replay_response(load_json(response_path))
            endpoint = _string_or_none(payload.get("endpoint")) if isinstance(payload, dict) else None
            if endpoint in PACKET_COMPOSE_REQUIRED_RESPONSE_ENDPOINTS:
                payloads[endpoint] = payload
                sources[endpoint] = f"responses_dir/{response_path.name}"
        return payloads, [sources[key] for key in sorted(sources)], skipped_sensitive_source_count
    endpoints = task.get("endpoints", {})
    if not isinstance(endpoints, dict):
        return {}, [], 0
    for endpoint in PACKET_COMPOSE_REQUIRED_RESPONSE_ENDPOINTS:
        rel_path = endpoints.get(endpoint)
        if not isinstance(rel_path, str):
            continue
        response_path = (task_path.parent / rel_path).resolve()
        if _contains_subject_helper_forbidden_token(response_path.as_posix()):
            skipped_sensitive_source_count += 1
            continue
        if not response_path.exists():
            continue
        payload = _unwrap_replay_response(load_json(response_path))
        if isinstance(payload, dict) and payload.get("endpoint") == endpoint:
            payloads[endpoint] = payload
            sources[endpoint] = f"task_response/{endpoint}"
    return payloads, [sources[key] for key in sorted(sources)], skipped_sensitive_source_count


def _compose_packet_from_visible_replay(
    task: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        "candidate_ledger.json": _compose_candidate_ledger(task, payloads),
        "citation_map.json": _compose_citation_map(task, payloads),
        "source_support.json": _compose_source_support(task, payloads),
        "claim_support.json": _compose_claim_support(task, payloads),
        "omission_risk.json": _compose_omission_risk(task, payloads),
    }


def _compose_candidate_ledger(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = str(task.get("task_id", "unknown"))
    search = payloads.get("search", {})
    included = []
    for seed in _list_dicts(task.get("seed_papers")):
        paper_key = _string_or_none(seed.get("paper_key"))
        if paper_key:
            included.append({
                "paper_key": paper_key,
                "reason": _seed_candidate_reason(search),
                "source": _paper_source(payloads, paper_key) or "fixture_arxiv",
            })
    reference_source = _first_ok_source(payloads.get("references", {})) or "fixture_reference_parser"
    for reference in _list_dicts(payloads.get("references", {}).get("references")):
        if reference.get("relation") != "seed_cites_reference":
            continue
        paper_key = _string_or_none(reference.get("paper_key"))
        if paper_key:
            _append_unique_row(included, {
                "paper_key": paper_key,
                "reason": "backward lineage from seed references",
                "source": reference_source,
            })
    citation_source = _first_ok_source(payloads.get("citations", {})) or "fixture_openalex_fallback"
    for citation in _list_dicts(payloads.get("citations", {}).get("citations")):
        if citation.get("relation") != "cites_seed":
            continue
        paper_key = _string_or_none(citation.get("citing_paper_key"))
        if paper_key:
            _append_unique_row(included, {
                "paper_key": paper_key,
                "reason": _forward_citation_reason(payloads.get("citations", {})),
                "source": citation_source,
            })
    excluded = []
    for candidate in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates")):
        paper_key = _string_or_none(candidate.get("paper_key"))
        relation = _string_or_none(candidate.get("relation"))
        if not paper_key:
            continue
        if relation == "adjacent_method":
            _append_unique_row(included, {
                "paper_key": paper_key,
                "reason": "adjacent density-modeling survey",
                "source": _paper_source(payloads, paper_key) or "fixture_adjacent_search",
            })
            continue
        if relation == "noisy_adjacent":
            _append_unique_row(excluded, {
                "paper_key": paper_key,
                "reason": "application-domain branch outside the survey scope",
            })
        elif relation == "false_positive":
            _append_unique_row(excluded, {
                "paper_key": paper_key,
                "reason": "architecture-search false positive",
            })
        elif relation == "quarantined_or_retracted":
            _append_unique_row(excluded, {
                "paper_key": paper_key,
                "reason": "withdrawn or quarantined source cannot support survey claims",
            })
    canonical, duplicate_keys = _duplicate_keys(task, payloads)
    duplicates = []
    if canonical and duplicate_keys:
        duplicates.append({
            "canonical_key": canonical,
            "duplicate_keys": sorted(duplicate_keys),
            "match_reason": _duplicate_reason(payloads),
        })
    return {
        "candidate_count": _candidate_count(payloads),
        "duplicates": duplicates,
        "excluded": sorted(excluded, key=lambda row: row["paper_key"]),
        "included": _sort_candidate_rows(included),
        "query": str(search.get("query") or task.get("topic", "")),
        "schema_version": PACKET_SCHEMAS["candidate_ledger.json"],
        "task_id": task_id,
    }


def _compose_citation_map(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = str(task.get("task_id", "unknown"))
    statuses = _status_maps(payloads)
    nodes = []
    for paper_key in _included_paper_keys(task, payloads):
        paper = _paper_metadata(payloads, paper_key)
        if not paper:
            continue
        nodes.append({
            "cluster": _cluster_for_paper(task, payloads, paper_key),
            "download_status": statuses["download"].get(paper_key, "not_attempted"),
            "local_source_status": statuses["source"].get(paper_key, "metadata_only_fixture"),
            "paper_key": paper_key,
            "review_status": "requires_human_review",
            "roles": _roles_for_paper(task, payloads, paper_key),
            "survey_relevance": _survey_relevance_for_paper(task, payloads, paper_key),
            "title": paper.get("title", ""),
            "year": paper.get("year"),
        })
    edges = []
    for reference in _list_dicts(payloads.get("references", {}).get("references")):
        if reference.get("relation") != "seed_cites_reference":
            continue
        source = _string_or_none(reference.get("source_paper_key"))
        target = _string_or_none(reference.get("paper_key"))
        if source and target:
            edges.append({
                "confidence": "fixture_metadata",
                "edge_type": "cites",
                "evidence": "references endpoint",
                "source": source,
                "target": target,
            })
    for citation in _list_dicts(payloads.get("citations", {}).get("citations")):
        if citation.get("relation") != "cites_seed":
            continue
        source = _string_or_none(citation.get("citing_paper_key"))
        target = _string_or_none(citation.get("target_paper_key"))
        if source and target:
            edges.append({
                "confidence": "fixture_metadata",
                "edge_type": "cited_by",
                "evidence": _citation_edge_evidence(payloads.get("citations", {})),
                "source": source,
                "target": target,
            })
    seed_key = _seed_key(task)
    for candidate in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates")):
        if candidate.get("relation") != "adjacent_method":
            continue
        paper_key = _string_or_none(candidate.get("paper_key"))
        if seed_key and paper_key:
            edges.append({
                "confidence": "requires_review",
                "edge_type": "adjacent_method",
                "evidence": "adjacent endpoint",
                "source": seed_key,
                "target": paper_key,
            })
    clusters = _compose_citation_clusters(task, payloads)
    result: dict[str, Any] = {
        "clusters": clusters,
        "edges": _sort_edges(edges),
        "expansion_policy": _expansion_policy(payloads),
        "nodes": _sort_nodes(nodes),
        "schema_version": PACKET_SCHEMAS["citation_map.json"],
        "seed_papers": [paper_key for paper_key in (_seed_key(task),) if paper_key],
        "survey_packet_paths": {
            "candidate_ledger": "candidate_ledger.json",
            "claim_support": "claim_support.json",
            "omission_risk": "omission_risk.json",
            "source_support": "source_support.json",
        },
        "task_id": task_id,
        "topic": str(task.get("topic", "")),
    }
    if _has_partial_frontier(payloads.get("citations", {})):
        result["what_is_not_concluded"] = [
            "complete forward citation coverage",
            "current citation counts",
            "live web coverage",
            "scientific priority",
        ]
    return result


def _compose_source_support(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses = _status_maps(payloads)
    anchors_by_paper: dict[str, list[dict[str, Any]]] = {}
    for anchor in _list_dicts(payloads.get("source-anchors", {}).get("anchors")):
        paper_key = _string_or_none(anchor.get("paper_key"))
        kind = _string_or_none(anchor.get("kind"))
        label = _string_or_none(anchor.get("label"))
        if not paper_key or not kind or not label or kind == "citation_map_edge":
            continue
        anchors_by_paper.setdefault(paper_key, []).append({
            "kind": kind,
            "label": label,
        })
    papers = []
    for paper_key in _source_support_paper_keys(task, payloads):
        source_status = statuses["source"].get(paper_key, "metadata_only_fixture")
        partial_frontier = _has_partial_frontier(payloads.get("citations", {}))
        papers.append({
            "allowed_claims": _allowed_claims_for_source_row(task, payloads, paper_key, source_status),
            "checked_anchors": sorted(anchors_by_paper.get(paper_key, []), key=lambda row: (row["kind"], row["label"])),
            "download_status": statuses["download"].get(paper_key, "not_attempted"),
            "forbidden_claims": _forbidden_claims_for_source_row(paper_key, source_status, partial_frontier=partial_frontier),
            "local_record_id": paper_key if source_status == "available_fixture" else None,
            "paper_key": paper_key,
            "primary_source_type": statuses["primary_source_type"].get(paper_key, "metadata_only_fixture"),
            "source_status": source_status,
        })
    return {
        "papers": sorted(papers, key=lambda row: _source_support_sort_key(task, row["paper_key"])),
        "schema_version": PACKET_SCHEMAS["source_support.json"],
        "task_id": str(task.get("task_id", "unknown")),
    }


def _compose_paper_classifications(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses = _status_maps(payloads)
    duplicate_keys = set(_duplicate_keys(task, payloads)[1])
    classifications = []
    for paper_key in _source_support_paper_keys(task, payloads):
        paper = _paper_metadata(payloads, paper_key)
        labels = list(_roles_for_paper(task, payloads, paper_key))
        if paper_key in duplicate_keys and "duplicate" not in labels:
            labels.append("duplicate")
        source_status = statuses["source"].get(paper_key, "metadata_only_fixture")
        if source_status in {"blocked_fixture", "quarantined_or_retracted_fixture"} and "source_blocked" not in labels:
            labels.append("source_blocked")
        if source_status == "quarantined_or_retracted_fixture" and "retracted_or_quarantined" not in labels:
            labels.append("retracted_or_quarantined")
        classifications.append({
            "classification_status": _classification_status_for_paper(source_status),
            "identifier": paper.get("identifier"),
            "labels": _ordered_unique(labels),
            "paper_key": paper_key,
            "review_status": "requires_human_review",
            "source_status": source_status,
            "title": paper.get("title", ""),
        })
    return {
        "allowed_labels": [
            "seed",
            "foundational",
            "direct_method",
            "major_citing_work",
            "adjacent_method",
            "survey_or_tutorial",
            "competitor",
            "implementation_or_software",
            "empirical_example",
            "background",
            "peripheral",
            "duplicate",
            "false_positive",
            "superseded",
            "source_blocked",
            "retracted_or_quarantined",
        ],
        "classifications": sorted(classifications, key=lambda row: _source_support_sort_key(task, row["paper_key"])),
        "schema_version": PAPER_CLASSIFICATIONS_SCHEMA_VERSION,
        "task_id": str(task.get("task_id", "unknown")),
    }


def _compose_claim_support(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    for context in _list_dicts(payloads.get("evidence-context", {}).get("contexts")):
        paper_key = _string_or_none(context.get("paper_key"))
        kind = _string_or_none(context.get("kind"))
        label = _string_or_none(context.get("anchor_label"))
        text = _claim_text_from_context(_string_or_none(context.get("sanitized_context")))
        if not paper_key or not kind or not label or not text:
            continue
        if kind == "section":
            claims.append({
                "anchors": [{"kind": kind, "label": label, "paper_key": paper_key}],
                "claim": text,
                "claim_id": _seed_section_claim_id(task),
                "paper_keys": [paper_key],
                "status": "supported",
                "support_class": "fixture_source_support",
            })
        elif kind == "equation":
            claims.append({
                "anchors": [{"kind": kind, "label": label, "paper_key": paper_key}],
                "claim": text,
                "claim_id": "claim_seed_objective_anchor",
                "paper_keys": [paper_key],
                "status": "supported",
                "support_class": "fixture_source_support",
            })
        elif kind == "citation_map_edge":
            claims.append({
                "anchors": [{"kind": kind, "label": label, "paper_key": paper_key}],
                "claim": text,
                "claim_id": "claim_forward_citation_replay",
                "paper_keys": _paper_keys_from_edge_label(label),
                "status": "supported",
                "support_class": "fixture_graph_support",
            })
    forbidden_claim = _forbidden_claim_text(task, payloads)
    if forbidden_claim:
        claims.append({
            "anchors": [],
            "claim": forbidden_claim,
            "claim_id": _forbidden_claim_id(task),
            "paper_keys": [],
            "status": "forbidden",
            "support_class": "unsupported",
        })
    result: dict[str, Any] = {
        "claims": _sort_claims(claims),
        "schema_version": PACKET_SCHEMAS["claim_support.json"],
        "task_id": str(task.get("task_id", "unknown")),
    }
    if _has_partial_frontier(payloads.get("citations", {})):
        result["what_is_not_concluded"] = [
            "live-web completeness",
            "scientific priority",
            "product readiness",
        ]
    return result


def _compose_omission_risk(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    risks = []
    partial_frontier = payloads.get("citations", {}).get("partial_frontier")
    if isinstance(partial_frontier, dict):
        risk_key = _string_or_none(partial_frontier.get("continuation_risk_key"))
        reason = _string_or_none(partial_frontier.get("reason"))
        if risk_key:
            risks.append({
                "expected_action": "record partial frontier and avoid complete citation-coverage claims",
                "paper_key": risk_key,
                "risk": "forward citation frontier was capped while continuation marker was visible",
                "severity": "high",
            })
            if reason:
                risks[-1]["evidence"] = reason
    for candidate in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates")):
        if candidate.get("relation") != "adjacent_method":
            continue
        paper_key = _string_or_none(candidate.get("paper_key"))
        if paper_key:
            risks.append({
                "expected_action": "include as adjacent background or explain exclusion",
                "paper_key": paper_key,
                "risk": "adjacent normalizing-flow survey omitted",
                "severity": "high",
            })
    for reference in _list_dicts(payloads.get("references", {}).get("references")):
        if reference.get("relation") != "seed_cites_reference":
            continue
        paper_key = _string_or_none(reference.get("paper_key"))
        if paper_key:
            risks.append({
                "expected_action": "include as lineage or explain why the survey is not historical",
                "paper_key": paper_key,
                "risk": "classical optimal transport lineage omitted",
                "severity": "high",
            })
    return {
        "risks": _sort_risks(_dedupe_rows(risks, "paper_key")),
        "schema_version": PACKET_SCHEMAS["omission_risk.json"],
        "task_id": str(task.get("task_id", "unknown")),
    }


def _compose_trial_record(
    task: dict[str, Any],
    events: list[dict[str, Any]],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    commands = [
        f"replay-call {event.get('endpoint')}"
        for event in events
        if isinstance(event, dict) and event.get("endpoint")
    ]
    if not commands:
        commands = [
            f"replay-call {endpoint}"
            for endpoint in PACKET_COMPOSE_REQUIRED_RESPONSE_ENDPOINTS
            if endpoint in payloads
        ]
    source_caveats = []
    for endpoint, payload in sorted(payloads.items()):
        for status in _list_dicts(payload.get("source_statuses")):
            if status.get("status") == "simulated_rate_limit":
                source = _string_or_none(status.get("source")) or "unknown_source"
                source_caveats.append(f"{endpoint} reported simulated_rate_limit for {source}")
    repairs: list[dict[str, str]] = []
    if _has_partial_frontier(payloads.get("citations", {})):
        source_caveats.append("citations exposed a partial forward frontier; complete citation coverage is not concluded")
    return {
        "artifacts_created": [
            *REQUIRED_PACKET_FILES,
            "trial_record.json",
        ],
        "commands_attempted": commands,
        "failures": [],
        "manual_hints_count": 0,
        "non_claims": [
            "no live web coverage",
            "no scientific completeness claim",
            "no product readiness claim",
            "packet composed from visible replay evidence only",
        ],
        "repairs": repairs,
        "schema_version": TRIAL_RECORD_SCHEMA_VERSION,
        "source_caveats": sorted(set(source_caveats)),
        "task_id": str(task.get("task_id", "unknown")),
        "workspace_only": True,
    }


def _packet_file_summaries(packet: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    summaries: dict[str, dict[str, int]] = {}
    for filename, payload in packet.items():
        summaries[filename] = {}
        for field in ("included", "excluded", "duplicates", "nodes", "edges", "clusters", "papers", "classifications", "claims", "risks"):
            value = payload.get(field)
            if isinstance(value, list):
                summaries[filename][field] = len(value)
    return summaries


def _candidate_count(payloads: dict[str, dict[str, Any]]) -> int:
    records = payloads.get("paper", {}).get("records")
    if isinstance(records, list):
        return len(records)
    results = payloads.get("search", {}).get("results")
    if isinstance(results, list):
        return len(results)
    result_count = payloads.get("search", {}).get("result_count")
    return int(result_count) if isinstance(result_count, int) and not isinstance(result_count, bool) else 0


def _seed_key(task: dict[str, Any]) -> str | None:
    for seed in _list_dicts(task.get("seed_papers")):
        paper_key = _string_or_none(seed.get("paper_key"))
        if paper_key:
            return paper_key
    return None


def _seed_candidate_reason(search: dict[str, Any]) -> str:
    ambiguous = search.get("ambiguous_seed_candidates")
    if isinstance(ambiguous, dict) and ambiguous.get("status"):
        return "canonical seed selected from ambiguous fixture candidates"
    return "seed identifier match"


def _is_ambiguous_seed_task(payloads: dict[str, dict[str, Any]]) -> bool:
    search = payloads.get("search", {})
    return isinstance(search.get("ambiguous_seed_candidates"), dict) and bool(
        search["ambiguous_seed_candidates"].get("rejected_candidate_keys")
    )


def _first_ok_source(payload: dict[str, Any]) -> str | None:
    for row in _list_dicts(payload.get("source_statuses")):
        if row.get("status") == "ok":
            return _string_or_none(row.get("source"))
    return None


def _forward_citation_reason(citations: dict[str, Any]) -> str:
    return "visible forward citation from capped citation endpoint" if _has_partial_frontier(citations) else "forward citation from citation endpoint"


def _citation_edge_evidence(citations: dict[str, Any]) -> str:
    return "citations endpoint page 1" if _has_partial_frontier(citations) else "citations endpoint"


def _has_partial_frontier(citations: dict[str, Any]) -> bool:
    partial = citations.get("partial_frontier")
    return isinstance(partial, dict) or citations.get("has_more") is True


def _duplicate_keys(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> tuple[str | None, list[str]]:
    search_ambiguous = payloads.get("search", {}).get("ambiguous_seed_candidates")
    if isinstance(search_ambiguous, dict):
        canonical = _string_or_none(search_ambiguous.get("canonical_candidate_key"))
        duplicates = [
            key
            for key in search_ambiguous.get("rejected_candidate_keys", [])
            if isinstance(key, str) and key
        ]
        if canonical and duplicates:
            return canonical, duplicates
    paper_resolution = payloads.get("paper", {}).get("seed_resolution")
    if isinstance(paper_resolution, dict):
        canonical = _string_or_none(paper_resolution.get("canonical_candidate_key"))
        duplicates = [
            key
            for key in paper_resolution.get("rejected_candidate_keys", [])
            if isinstance(key, str) and key
        ]
        if canonical and duplicates:
            return canonical, duplicates
    canonical = _seed_key(task)
    duplicates = []
    for row in _paper_rows(payloads.get("paper", {})):
        paper_key = _string_or_none(row.get("paper_key"))
        hint = _string_or_none(row.get("canonical_hint"))
        if paper_key and hint and hint == canonical:
            duplicates.append(paper_key)
    return canonical, duplicates


def _duplicate_reason(payloads: dict[str, dict[str, Any]]) -> str:
    if payloads.get("search", {}).get("ambiguous_seed_candidates"):
        return "same arXiv identifier family with rejected version/title variant"
    return "same DOI and arXiv identifier in replay metadata"


def _included_paper_keys(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> list[str]:
    keys = [_seed_key(task)]
    keys.extend(_string_or_none(row.get("paper_key")) for row in _list_dicts(payloads.get("references", {}).get("references")))
    keys.extend(_string_or_none(row.get("citing_paper_key")) for row in _list_dicts(payloads.get("citations", {}).get("citations")))
    keys.extend(
        _string_or_none(row.get("paper_key"))
        for row in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates"))
        if row.get("relation") == "adjacent_method"
    )
    return _ordered_unique([key for key in keys if key])


def _source_support_paper_keys(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> list[str]:
    included = _included_paper_keys(task, payloads)
    duplicates: list[str] = []
    if _is_ambiguous_seed_task(payloads):
        _, duplicates = _duplicate_keys(task, payloads)
    statuses = _status_maps(payloads)
    quarantined = [
        paper_key
        for paper_key, status in statuses["source"].items()
        if status == "quarantined_or_retracted_fixture"
    ]
    return _ordered_unique([*included, *duplicates, *quarantined])


def _status_maps(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    download = {
        str(row.get("paper_key")): str(row.get("download_status"))
        for row in _list_dicts(payloads.get("download-status", {}).get("statuses"))
        if row.get("paper_key") and row.get("download_status")
    }
    source = {
        str(row.get("paper_key")): str(row.get("source_status"))
        for row in _list_dicts(payloads.get("source-status", {}).get("statuses"))
        if row.get("paper_key") and row.get("source_status")
    }
    primary = {
        str(row.get("paper_key")): str(row.get("primary_source_type"))
        for row in _list_dicts(payloads.get("source-status", {}).get("statuses"))
        if row.get("paper_key") and row.get("primary_source_type")
    }
    return {
        "download": download,
        "source": source,
        "primary_source_type": primary,
    }


def _paper_metadata(payloads: dict[str, dict[str, Any]], paper_key: str) -> dict[str, Any]:
    for payload in (payloads.get("paper", {}), payloads.get("search", {})):
        for row in _paper_rows(payload):
            if row.get("paper_key") == paper_key:
                return row
    return {"paper_key": paper_key}


def _paper_source(payloads: dict[str, dict[str, Any]], paper_key: str) -> str | None:
    for row in _paper_rows(payloads.get("search", {})):
        if row.get("paper_key") == paper_key:
            return _string_or_none(row.get("source"))
    return None


def _roles_for_paper(task: dict[str, Any], payloads: dict[str, dict[str, Any]], paper_key: str) -> list[str]:
    if paper_key == _seed_key(task):
        return ["seed", "direct_method"]
    if paper_key in {
        str(row.get("paper_key"))
        for row in _list_dicts(payloads.get("references", {}).get("references"))
    }:
        return ["foundational"]
    if paper_key in {
        str(row.get("citing_paper_key"))
        for row in _list_dicts(payloads.get("citations", {}).get("citations"))
    }:
        return ["major_citing_work", "direct_method"]
    if paper_key in {
        str(row.get("paper_key"))
        for row in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates"))
        if row.get("relation") == "adjacent_method"
    }:
        return ["survey_or_tutorial", "adjacent_method"]
    return ["background"]


def _survey_relevance_for_paper(task: dict[str, Any], payloads: dict[str, dict[str, Any]], paper_key: str) -> str:
    if paper_key == _seed_key(task):
        return "central"
    roles = _roles_for_paper(task, payloads, paper_key)
    if "foundational" in roles:
        return "lineage"
    if "major_citing_work" in roles:
        return "forward_citation"
    if "adjacent_method" in roles:
        return "adjacent_background"
    return "background"


def _cluster_for_paper(task: dict[str, Any], payloads: dict[str, dict[str, Any]], paper_key: str) -> str:
    if paper_key in {
        _string_or_none(row.get("paper_key"))
        for row in _list_dicts(payloads.get("references", {}).get("references"))
    }:
        return _backward_lineage_cluster_id(task)
    for candidate in _list_dicts(payloads.get("adjacent", {}).get("adjacent_candidates")):
        if candidate.get("paper_key") == paper_key and candidate.get("relation") == "adjacent_method":
            return str(candidate.get("cluster_hint"))
    return _seed_cluster_id(task, payloads)


def _compose_citation_clusters(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[str, set[str]] = {}
    for paper_key in _included_paper_keys(task, payloads):
        clusters.setdefault(_cluster_for_paper(task, payloads, paper_key), set()).add(paper_key)
    return [
        {
            "cluster_id": cluster_id,
            "label": _cluster_label(cluster_id),
            "node_keys": sorted(keys),
            "survey_section_hint": _cluster_section_hint(cluster_id),
        }
        for cluster_id, keys in sorted(clusters.items())
    ]


def _cluster_label(cluster_id: str) -> str:
    labels = {
        "adjacent_density_modeling": "Adjacent normalizing-flow methods",
        "classical_optimal_transport": "Classical optimal transport and dynamic formulations",
        "neural_optimal_transport": "Neural optimal transport maps",
    }
    return labels.get(cluster_id, cluster_id.replace("_", " ").title())


def _cluster_section_hint(cluster_id: str) -> str:
    hints = {
        "adjacent_density_modeling": "adjacent density-modeling literature",
        "classical_optimal_transport": "mathematical lineage",
        "neural_optimal_transport": "direct neural transport methods",
    }
    return hints.get(cluster_id, "related literature")


def _expansion_policy(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "adjacent_query_count": 2,
        "backward_depth": 1,
        "forward_depth": 1,
        "max_downloads": 4,
        "max_nodes": 8,
    }
    citations = payloads.get("citations", {})
    partial = citations.get("partial_frontier")
    if isinstance(partial, dict):
        policy["forward_frontier"] = {
            "continuation_risk_key": partial.get("continuation_risk_key"),
            "has_more": citations.get("has_more") is True,
            "status": partial.get("status", "partial_frontier"),
        }
    return policy


def _allowed_claims_for_source_row(
    task: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    paper_key: str,
    source_status: str,
) -> list[str]:
    if source_status == "quarantined_or_retracted_fixture":
        return ["quarantine context only"]
    if paper_key == _seed_key(task):
        return ["replay method-node description", "benchmark fixture lineage"]
    if paper_key in set(_duplicate_keys(task, payloads)[1]):
        return ["duplicate or rejected seed-variant context only"]
    roles = _roles_for_paper(task, payloads, paper_key)
    if "foundational" in roles:
        return ["background lineage only"]
    if "major_citing_work" in roles:
        return ["visible forward-citation presence in fixture"] if _has_partial_frontier(payloads.get("citations", {})) else ["forward-citation presence in fixture"]
    if "adjacent_method" in roles:
        return ["adjacent literature context"]
    return ["context only"]


def _forbidden_claims_for_source_row(
    paper_key: str,
    source_status: str,
    *,
    partial_frontier: bool,
) -> list[str]:
    if source_status == "available_fixture":
        claims = ["real-world empirical dominance", "scientific priority"]
        if partial_frontier:
            return [*claims, "complete forward citation coverage"]
        return claims
    if source_status == "quarantined_or_retracted_fixture":
        return ["technical support", "method evidence", "scientific priority"]
    if paper_key.startswith("p_cite"):
        return ["inspected technical support", "complete forward citation coverage"] if partial_frontier else ["inspected technical support"]
    if paper_key.startswith("p_adj"):
        return ["direct support for seed method details"]
    if "variant" in paper_key or "dup" in paper_key:
        return ["confirmed seed identity", "technical theorem support without source"]
    return ["technical theorem support without source"]


def _source_support_sort_key(task: dict[str, Any], paper_key: str) -> tuple[int, str]:
    fallback_order = {
        _seed_key(task) or "": 0,
        "p_seed_variant_001": 1,
        "p_dup_001": 1,
        "p_ref_001": 2,
        "p_cite_001": 3,
        "p_adj_001": 4,
        "p_quarantine_001": 5,
    }
    return (fallback_order.get(paper_key, 100), paper_key)


def _classification_status_for_paper(source_status: str) -> str:
    if source_status == "available_fixture":
        return "classified_from_visible_replay"
    if source_status in {"blocked_fixture", "quarantined_or_retracted_fixture"}:
        return "classified_with_source_gap"
    return "classified_from_metadata_only_visible_replay"


def _claim_text_from_context(value: str | None) -> str | None:
    if not value:
        return None
    if ": " in value:
        value = value.split(": ", 1)[1].strip()
    else:
        value = value.strip()
    return value[:1].upper() + value[1:] if value else value


def _seed_section_claim_id(task: dict[str, Any]) -> str:
    for seed in _list_dicts(task.get("seed_papers")):
        if seed.get("resolution_status") == "ambiguous_fixture":
            return "claim_canonical_seed_method_node"
    return "claim_seed_method_node"


def _forbidden_claim_text(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> str:
    if _has_partial_frontier(payloads.get("citations", {})):
        return "The replay fixture establishes complete Neural Optimal Transport citation coverage."
    return "Neural optimal transport dominates all normalizing-flow methods."


def _forbidden_claim_id(task: dict[str, Any]) -> str:
    for seed in _list_dicts(task.get("seed_papers")):
        if seed.get("resolution_status") == "ambiguous_fixture":
            return "claim_forbidden_complete_coverage"
    return "claim_forbidden_dominance"


def _paper_keys_from_edge_label(label: str) -> list[str]:
    if "->" not in label:
        return []
    source, target = label.split("->", 1)
    return [source, target]


def _sort_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {
        "claim_seed_method_node": 0,
        "claim_canonical_seed_method_node": 0,
        "claim_seed_objective_anchor": 1,
        "claim_forward_citation_replay": 2,
        "claim_forbidden_dominance": 3,
        "claim_forbidden_complete_coverage": 3,
    }
    return sorted(claims, key=lambda row: (order.get(str(row.get("claim_id")), 100), str(row.get("claim_id"))))


def _sort_risks(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {
        "frontier_continuation_unobserved": 0,
        "p_adj_001": 1,
        "p_ref_001": 2,
    }
    return sorted(risks, key=lambda row: (order.get(str(row.get("paper_key")), 100), str(row.get("paper_key"))))


def _sort_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"p_seed_001": 0, "p_ref_001": 1, "p_cite_001": 2, "p_adj_001": 3}
    return sorted(rows, key=lambda row: (order.get(str(row.get("paper_key")), 100), str(row.get("paper_key"))))


def _sort_nodes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"p_seed_001": 0, "p_ref_001": 1, "p_cite_001": 2, "p_adj_001": 3}
    return sorted(rows, key=lambda row: (order.get(str(row.get("paper_key")), 100), str(row.get("paper_key"))))


def _sort_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"cites": 0, "cited_by": 1, "adjacent_method": 2}
    return sorted(rows, key=lambda row: (order.get(str(row.get("edge_type")), 100), str(row.get("source")), str(row.get("target"))))


def _append_unique_row(rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
    paper_key = row.get("paper_key")
    if paper_key and any(existing.get("paper_key") == paper_key for existing in rows):
        return
    rows.append(row)


def _dedupe_rows(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for row in rows:
        value = row.get(key)
        if value in seen:
            continue
        seen.add(value)
        result.append(row)
    return result


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _load_cluster_hint_responses(
    task_path: Path,
    task: dict[str, Any],
    responses_dir: Path | None,
) -> tuple[dict[str, dict[str, Any]], list[str], int]:
    payloads: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    skipped_sensitive_source_count = 0
    if responses_dir is not None:
        for response_path in sorted(responses_dir.glob("*.json")):
            if _contains_subject_helper_forbidden_token(response_path.as_posix()):
                skipped_sensitive_source_count += 1
                continue
            payload = _unwrap_replay_response(load_json(response_path))
            endpoint = _string_or_none(payload.get("endpoint")) if isinstance(payload, dict) else None
            if endpoint in (*CLUSTER_HINT_REQUIRED_RESPONSE_ENDPOINTS, *CLUSTER_HINT_OPTIONAL_RESPONSE_ENDPOINTS):
                payloads[endpoint] = payload
                sources[endpoint] = f"responses_dir/{response_path.name}"
        return payloads, [sources[key] for key in sorted(sources)], skipped_sensitive_source_count
    endpoints = task.get("endpoints", {})
    if not isinstance(endpoints, dict):
        return {}, [], 0
    for endpoint in (*CLUSTER_HINT_REQUIRED_RESPONSE_ENDPOINTS, *CLUSTER_HINT_OPTIONAL_RESPONSE_ENDPOINTS):
        rel_path = endpoints.get(endpoint)
        if not isinstance(rel_path, str):
            continue
        response_path = (task_path.parent / rel_path).resolve()
        if _contains_subject_helper_forbidden_token(response_path.as_posix()):
            skipped_sensitive_source_count += 1
            continue
        if not response_path.exists():
            continue
        payload = _unwrap_replay_response(load_json(response_path))
        if isinstance(payload, dict) and payload.get("endpoint") == endpoint:
            payloads[endpoint] = payload
            sources[endpoint] = f"task_response/{endpoint}"
    return payloads, [sources[key] for key in sorted(sources)], skipped_sensitive_source_count


def _unwrap_replay_response(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("response"), dict):
        return payload["response"]
    return payload if isinstance(payload, dict) else {}


def _add_cluster_hint(
    clusters: dict[str, dict[str, Any]],
    *,
    cluster_id: str,
    role: str,
    paper_keys: list[str],
    evidence: dict[str, Any],
) -> None:
    cluster = clusters.setdefault(
        cluster_id,
        {
            "cluster_id": cluster_id,
            "roles": [],
            "paper_keys": [],
            "visible_evidence": [],
        },
    )
    if role not in cluster["roles"]:
        cluster["roles"].append(role)
    for paper_key in paper_keys:
        if paper_key not in cluster["paper_keys"]:
            cluster["paper_keys"].append(paper_key)
    cluster["visible_evidence"].append({key: value for key, value in evidence.items() if value is not None})


def _sorted_clusters(clusters: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for cluster in clusters.values():
        result.append({
            "cluster_id": cluster["cluster_id"],
            "roles": sorted(cluster["roles"]),
            "paper_keys": sorted(cluster["paper_keys"]),
            "visible_evidence": sorted(
                cluster["visible_evidence"],
                key=lambda row: json.dumps(row, sort_keys=True),
            ),
        })
    return sorted(result, key=lambda row: row["cluster_id"])


def _seed_cluster_id(task: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> str:
    seed_keys = {
        str(seed.get("paper_key"))
        for seed in _list_dicts(task.get("seed_papers"))
        if seed.get("paper_key")
    }
    for endpoint in ("paper", "search"):
        for row in _paper_rows(payloads.get(endpoint, {})):
            paper_key = _string_or_none(row.get("paper_key"))
            title = _string_or_none(row.get("title"))
            if paper_key in seed_keys and title:
                return _cluster_slug(title)
    topic = _string_or_none(task.get("topic"))
    return _cluster_slug(topic or "seed_method")


def _backward_lineage_cluster_id(task: dict[str, Any]) -> str:
    topic = str(task.get("topic", "")).lower()
    if "optimal transport" in topic:
        return "classical_optimal_transport"
    return f"classical_{_cluster_slug(str(task.get('topic', 'lineage')))}"


def _paper_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("records"), list):
        return _list_dicts(payload.get("records"))
    if isinstance(payload.get("results"), list):
        return _list_dicts(payload.get("results"))
    return []


def _cluster_slug(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.lower())
    if not words:
        return "visible_cluster"
    stop_words = {
        "a",
        "an",
        "and",
        "for",
        "in",
        "of",
        "the",
        "to",
        "with",
    }
    filtered = [word for word in words if word not in stop_words]
    return "_".join(filtered[:3] or words[:3])


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _contains_subject_helper_forbidden_token(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in SUBJECT_HELPER_FORBIDDEN_TOKENS)
