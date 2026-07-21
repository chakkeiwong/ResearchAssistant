from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import os
import platform
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.build import (
    PUBLIC_METADATA_OPENALEX_SELECT,
    PUBLIC_METADATA_PACKET_FILES,
    PUBLIC_METADATA_USER_AGENT,
    build_survey_evidence_packet,
    validate_public_metadata_v2_bundle,
)
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, pretty_json_bytes


TOPIC = "Neural Optimal Transport for generative modeling and inference"
SEED = "arxiv:2201.12220v3"
PROVIDERS = ["arxiv", "openalex"]
MAX_RECORDS = 10
LIVE_OUTPUT_ROOT = Path("docs/validation/literature_survey_m19_live_metadata_2026-07-14")
FRAME_CAP = 1_000_000
STREAM_CAP = 65_536
SOFT_SECONDS = 180.0
HARD_SECONDS = 185.0
WATCHDOG_TERM_SECONDS = 186.5
ABSOLUTE_SECONDS = 187.0
FORBIDDEN_HEADERS = ["authorization", "cookie", "from", "proxy-authorization", "referer", "x-api-key"]
NONCLAIMS = [
    "live provider behavior",
    "metadata quality",
    "north-star completion",
    "product readiness",
    "scientific correctness",
    "source support",
]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        text=True,
        timeout=5,
    ).stdout.strip()


def _route_rows() -> list[dict[str, Any]]:
    specifications = [
        (1, "arxiv", "seed_resolution", "export.arxiv.org", "/api/query", "application/atom+xml", {
            "id_list": "2201.12220v3", "max_results": "5", "sortBy": "relevance", "sortOrder": "descending", "start": "0",
        }),
        (2, "arxiv", "topic_search", "export.arxiv.org", "/api/query", "application/atom+xml", {
            "max_results": "10", "search_query": f"all:{TOPIC}", "sortBy": "relevance", "sortOrder": "descending", "start": "0",
        }),
        (3, "openalex", "seed_resolution", "api.openalex.org", "/works", "application/json", {
            "per-page": "5", "search": SEED, "select": PUBLIC_METADATA_OPENALEX_SELECT,
        }),
        (4, "openalex", "topic_search", "api.openalex.org", "/works", "application/json", {
            "per-page": "10", "search": TOPIC, "select": PUBLIC_METADATA_OPENALEX_SELECT,
        }),
    ]
    rows = []
    for index, provider, kind, host, path, accept, query in specifications:
        row = {
            "request_index": index, "provider": provider, "query_kind": kind,
            "method": "GET", "scheme": "https", "hostname": host, "port": 443,
            "path": path, "query": dict(sorted(query.items())),
            "headers": {"Accept": accept, "User-Agent": PUBLIC_METADATA_USER_AGENT},
        }
        row["request_binding_sha256"] = _sha(canonical_json_bytes(row))
        rows.append(row)
    return rows


def route_manifest(commit: str) -> dict[str, Any]:
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise MissionStateError("m19_invalid_commit", "hardening commit must be lowercase 40-hex")
    return {
        "schema_version": "ra-literature-survey-m19-route-manifest-v1",
        "hardening_commit": commit,
        "topic": TOPIC,
        "seed": SEED,
        "providers": PROVIDERS,
        "max_records": MAX_RECORDS,
        "user_agent": PUBLIC_METADATA_USER_AGENT,
        "routes": _route_rows(),
        "request_cap": 4,
        "byte_caps": {"per_request": 2_000_000, "total": 8_000_000},
        "timeout_seconds": 30,
        "whole_attempt_seconds": 187,
        "redirect_cap": 0,
        "retry_cap": 0,
        "proxy_policy": "disabled_explicit_proxy_handler_and_sanitized_environment",
        "forbidden_headers": FORBIDDEN_HEADERS,
    }


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(value) and value >= 0


def _validate_outcome(row: Any, route: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "request_index", "provider", "query_kind", "normalized_seed_key", "topic_query",
        "method", "scheme", "requested_hostname", "requested_port", "requested_path",
        "query_keys", "request_binding_sha256", "final_scheme", "final_hostname",
        "final_port", "final_path", "redirect_count", "retry_count",
        "configured_timeout_seconds", "observed_elapsed_seconds", "accepted_payload_bytes",
        "diagnostic_overflow_bytes", "normalized_record_count", "status",
        "sanitized_error_class", "sanitized_error_code", "raw_response_saved",
    }
    if not isinstance(row, dict) or set(row) != keys:
        raise MissionStateError("m19_invalid_ledger", "request outcome keys are not exact")
    expected_seed = SEED if route["query_kind"] == "seed_resolution" else None
    expected_topic = route["query_kind"] == "topic_search"
    fixed = {
        "request_index": route["request_index"], "provider": route["provider"],
        "query_kind": route["query_kind"], "normalized_seed_key": expected_seed,
        "topic_query": expected_topic, "method": "GET", "scheme": "https",
        "requested_hostname": route["hostname"], "requested_port": 443,
        "requested_path": route["path"], "query_keys": sorted(route["query"]),
        "request_binding_sha256": route["request_binding_sha256"],
        "redirect_count": 0, "retry_count": 0, "configured_timeout_seconds": 30,
        "raw_response_saved": False,
    }
    if any(
        row[key] != value or (value is not None and type(row[key]) is not type(value))
        for key, value in fixed.items()
    ):
        raise MissionStateError("m19_invalid_ledger", "request outcome differs from route")
    for key in ("accepted_payload_bytes", "diagnostic_overflow_bytes", "normalized_record_count"):
        if not _is_int(row[key]) or row[key] < 0:
            raise MissionStateError("m19_invalid_ledger", f"{key} must be a nonnegative integer")
    if not _is_number(row["observed_elapsed_seconds"]):
        raise MissionStateError("m19_invalid_ledger", "elapsed time must be finite and nonnegative")
    if row["accepted_payload_bytes"] > 2_000_000 or row["diagnostic_overflow_bytes"] > 1:
        raise MissionStateError("m19_invalid_ledger", "request byte cap exceeded")
    cap = 5 if route["query_kind"] == "seed_resolution" else 10
    if row["normalized_record_count"] > cap:
        raise MissionStateError("m19_invalid_ledger", "normalized record cap exceeded")
    status_pairs = {
        "available": {(None, None)},
        "unavailable_timeout": {("timeout", "socket_timeout")},
        "unavailable_redirect_rejected": {("redirect", f"http_{code}") for code in (301, 302, 303, 307, 308)},
        "unavailable_http_error": {("http", f"http_{code}") for code in (400, 401, 403, 404, 429, 500)} | {("http", "http_other")},
        "unavailable_transport_error": {("transport", code) for code in ("dns_failure", "tls_failure", "connection_failure", "other_transport_failure")},
        "unavailable_oversized": {("payload", "content_length_cap_exceeded"), ("payload", "stream_cap_exceeded")},
        "unavailable_malformed_response": {("parse", "malformed_json" if route["provider"] == "openalex" else "malformed_xml")},
        "blocked_invalid_request": {("request_validation", code) for code in (
            "invalid_method", "invalid_scheme", "invalid_host", "invalid_port", "invalid_path",
            "invalid_query_keys", "request_binding_mismatch", "userinfo_forbidden",
            "fragment_forbidden", "final_url_mismatch", "dispatch_cap_exceeded",
        )},
    }
    pair = (row["sanitized_error_class"], row["sanitized_error_code"])
    if row["status"] not in status_pairs or pair not in status_pairs[row["status"]]:
        raise MissionStateError("m19_invalid_ledger", "request status/error pairing is invalid")
    no_response = row["status"] in {"unavailable_timeout", "unavailable_transport_error", "blocked_invalid_request"}
    final_values = (row["final_scheme"], row["final_hostname"], row["final_port"], row["final_path"])
    expected_final = ("https", route["hostname"], 443, route["path"])
    if final_values != ((None, None, None, None) if no_response else expected_final) or (
        not no_response and not _is_int(row["final_port"])
    ):
        raise MissionStateError("m19_invalid_ledger", "final URL fields are incompatible")
    if row["status"] != "available" and row["normalized_record_count"] != 0:
        raise MissionStateError("m19_invalid_ledger", "unavailable request has normalized records")
    if row["status"] == "unavailable_oversized":
        expected_overflow = 1 if row["sanitized_error_code"] == "stream_cap_exceeded" else 0
        if row["diagnostic_overflow_bytes"] != expected_overflow or row["accepted_payload_bytes"] != 0:
            raise MissionStateError("m19_invalid_ledger", "oversized request byte fields are incompatible")
    elif row["diagnostic_overflow_bytes"] != 0:
        raise MissionStateError("m19_invalid_ledger", "non-overflow request has diagnostic overflow bytes")
    if row["status"] not in {"available", "unavailable_malformed_response"} and row["accepted_payload_bytes"] != 0:
        raise MissionStateError("m19_invalid_ledger", "request status cannot retain accepted payload bytes")
    return dict(row)


def request_ledger(manifest: dict[str, Any], rows: list[Any], status: str) -> dict[str, Any]:
    if status not in {"complete", "incomplete_worker_terminated", "invalid_ledger"}:
        raise MissionStateError("m19_invalid_ledger", "unknown ledger status")
    if len(rows) > 4:
        raise MissionStateError("m19_invalid_ledger", "ledger row count is incompatible")
    validated = [_validate_outcome(row, manifest["routes"][index]) for index, row in enumerate(rows)]
    if status == "complete" and len(validated) != 4:
        raise MissionStateError("m19_invalid_ledger", "ledger row count is incompatible")
    available = sum(row["status"] == "available" for row in validated)
    boundary = sum(row["status"] == "blocked_invalid_request" for row in validated)
    unavailable = len(validated) - available - boundary
    if status == "complete" and boundary:
        raise MissionStateError("m19_invalid_ledger", "complete ledger contains boundary invalidity")
    accepted = sum(row["accepted_payload_bytes"] for row in validated)
    if accepted > 8_000_000:
        raise MissionStateError("m19_invalid_ledger", "aggregate payload cap exceeded")
    manifest_hash = _sha(canonical_json_bytes(manifest))
    return {
        "schema_version": "ra-literature-survey-m19-request-ledger-v1",
        "status": status,
        "scope": {
            "hardening_commit": manifest["hardening_commit"], "route_manifest_sha256": manifest_hash,
            "topic": TOPIC, "seed": SEED, "providers": PROVIDERS, "max_records": 10,
            "request_cap": 4, "accepted_payload_cap_per_request": 2_000_000,
            "accepted_payload_cap_total": 8_000_000, "diagnostic_overflow_cap_per_request": 1,
            "socket_timeout_seconds": 30, "whole_attempt_seconds": 187,
            "redirect_cap": 0, "retry_cap": 0,
            "proxy_policy": "disabled_explicit_proxy_handler_and_sanitized_environment",
        },
        "requests": validated,
        "totals": {
            "attempted_request_count": len(validated), "available_request_count": available,
            "unavailable_request_count": unavailable, "boundary_invalid_request_count": boundary,
            "accepted_payload_bytes": accepted,
            "diagnostic_overflow_bytes": sum(row["diagnostic_overflow_bytes"] for row in validated),
            "redirect_count": 0, "retry_count": 0,
        },
        "raw_response_policy": {
            "raw_responses_saved": False, "raw_response_artifact_count": 0,
            "sanitization": "closed_codes_no_query_values_headers_or_exception_text",
        },
    }


def _route_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return canonical_json_bytes(manifest)


def _loads_closed(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def validate_envelope(envelope: Any, manifest: dict[str, Any], public_root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str]:
    keys = {"schema_version", "status", "build_result", "request_outcomes", "worker_error_code"}
    if not isinstance(envelope, dict) or set(envelope) != keys or envelope["schema_version"] != "ra-literature-survey-m19-worker-envelope-v1":
        raise MissionStateError("m19_invalid_ipc", "worker envelope is not closed")
    if not isinstance(envelope["request_outcomes"], list) or len(envelope["request_outcomes"]) > 4:
        raise MissionStateError("m19_invalid_ipc", "worker request outcomes are invalid")
    rows = []
    for index, row in enumerate(envelope["request_outcomes"]):
        try:
            rows.append(_validate_outcome(row, manifest["routes"][index]))
        except MissionStateError as exc:
            raise MissionStateError(
                "m19_invalid_ipc", "worker request outcome is invalid",
                details={"validated_prefix": rows},
            ) from exc
    if envelope["status"] == "worker_error":
        if envelope["build_result"] is not None or envelope["worker_error_code"] not in {"boundary_error", "build_error", "serialization_error"}:
            raise MissionStateError("m19_invalid_ipc", "worker error envelope is inconsistent")
        ledger_status = "invalid_ledger" if envelope["worker_error_code"] == "boundary_error" else "incomplete_worker_terminated"
        return None, rows, ledger_status
    if envelope["status"] != "complete" or envelope["worker_error_code"] is not None or len(rows) != 4:
        raise MissionStateError(
            "m19_invalid_ipc", "complete worker envelope is inconsistent",
            details={"validated_prefix": rows},
        )
    result = envelope["build_result"]
    result_keys = {
        "schema_version", "status", "mode", "topic", "seed_count", "record_count", "providers",
        "max_records", "output_dir", "artifact_paths", "workflow_state_path", "provider_statuses",
        "next_required_actions", "what_is_not_concluded", "reused_existing",
    }
    if not isinstance(result, dict) or set(result) != result_keys:
        raise MissionStateError("m19_invalid_ipc", "build result keys are not exact", details={"validated_prefix": rows})
    fixed = {
        "schema_version": "ra-survey-build-cli-result-v1", "mode": "public-metadata", "topic": TOPIC,
        "seed_count": 1, "providers": PROVIDERS, "max_records": 10,
        "output_dir": str(public_root), "workflow_state_path": str(public_root / "workflow_state.json"),
        "reused_existing": False,
    }
    if any(result.get(key) != value for key, value in fixed.items()) or result.get("status") not in {"metadata_only_packet", "metadata_resolution_blocked"}:
        raise MissionStateError("m19_invalid_ipc", "build result differs from scope", details={"validated_prefix": rows})
    expected_paths = {name: str(public_root / name) for name in PUBLIC_METADATA_PACKET_FILES}
    if result.get("artifact_paths") != expected_paths or not _is_int(result.get("record_count")) or not 0 <= result["record_count"] <= 10:
        raise MissionStateError("m19_invalid_ipc", "build result artifacts/count are invalid", details={"validated_prefix": rows})
    statuses = result.get("provider_statuses")
    if not isinstance(statuses, list) or len(statuses) != 4:
        raise MissionStateError("m19_invalid_ipc", "provider statuses are incomplete", details={"validated_prefix": rows})
    for index, (provider_status, row) in enumerate(zip(statuses, rows)):
        expected = {
            "provider": row["provider"], "query_kind": row["query_kind"],
            "normalized_seed_key": row["normalized_seed_key"], "topic_query": row["topic_query"],
            "query_cap": 5 if row["query_kind"] == "seed_resolution" else 10,
            "status": "available" if row["status"] == "available" else "unavailable",
            "record_count": row["normalized_record_count"], "raw_response_saved": False,
        }
        if provider_status != expected:
            raise MissionStateError(
                "m19_invalid_ipc", f"provider status {index} disagrees with request outcome",
                details={"validated_prefix": rows},
            )
    for field in ("next_required_actions", "what_is_not_concluded"):
        if not isinstance(result[field], list) or not result[field] or any(not isinstance(value, str) or not value for value in result[field]):
            raise MissionStateError("m19_invalid_ipc", f"build result {field} is invalid", details={"validated_prefix": rows})
    validate_public_metadata_v2_bundle(topic=TOPIC, seeds=[SEED], output_dir=public_root, providers=PROVIDERS, max_records=10)
    disk_manifest = json.loads((public_root / "build_manifest.json").read_bytes())
    if disk_manifest.get("record_count") != result["record_count"]:
        raise MissionStateError("m19_invalid_ipc", "build result count disagrees with manifest", details={"validated_prefix": rows})
    return result, rows, "complete"


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise MissionStateError("m19_conflicting_output", f"output exists: {path.name}")
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        except FileExistsError as exc:
            raise MissionStateError("m19_conflicting_output", f"output appeared during publication: {path.name}") from exc
        temp.unlink()
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        raise


def _preflight_absent_root(root: Path) -> None:
    root = root.absolute()
    if root.exists() or root.is_symlink():
        raise MissionStateError("m19_conflicting_output", "output root must be absent")
    if not root.parent.exists() or not root.parent.is_dir():
        raise MissionStateError("m19_unsafe_output_ancestor", "output ancestor parent must be an existing regular directory")
    current = root.parent
    while True:
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise MissionStateError("m19_unsafe_output_ancestor", "output root has a symlink or non-directory ancestor")
        if current.parent == current:
            break
        current = current.parent


def _environment_manifest(commit: str) -> dict[str, Any]:
    return {
        "schema_version": "ra-literature-survey-m19-environment-v1",
        "python_version": platform.python_version(), "os": platform.platform(),
        "git_commit": commit, "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "conda_environment": os.environ.get("CONDA_DEFAULT_ENV"),
        "cuda_visible_devices": "-1", "python_dont_write_bytecode": "1",
        "git_optional_locks": "0", "python_pycacheprefix_present": False,
        "pythonpath_present": False, "proxy_variables_present": False,
        "credential_variables_present": False,
    }


def _stream_record(status: str, count: int, digest: str, complete: bool) -> dict[str, Any]:
    return {
        "schema_version": "ra-literature-survey-m19-stdout-v1", "status": status,
        "observed_byte_count": count, "capture_cap_bytes": STREAM_CAP,
        "overflowed": count > STREAM_CAP, "stream_complete": complete,
        "sha256": digest, "digest_scope": "observed_bytes_until_eof_or_absolute_cutoff",
        "content_saved": False,
    }


def _stderr_line(record: dict[str, Any]) -> bytes:
    return (
        f"status={record['status']} observed_bytes={record['observed_byte_count']} "
        f"capture_cap_bytes=65536 overflowed={str(record['overflowed']).lower()} "
        f"stream_complete={str(record['stream_complete']).lower()} sha256={record['sha256']} "
        "digest_scope=observed_bytes_until_eof_or_absolute_cutoff content_saved=false\n"
    ).encode("ascii")


def root_inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative in {"root_inventory.json", "hardening_summary.json"}:
            continue
        if path.is_dir():
            if relative not in {"logs", "public_metadata"}:
                raise MissionStateError("m19_invalid_inventory", "inventory found an unknown directory")
            continue
        if path.is_symlink() or not path.is_file():
            raise MissionStateError("m19_invalid_inventory", "inventory found a nonregular artifact")
        raw = path.read_bytes()
        rows.append({"path": relative, "kind": "regular_file", "size_bytes": len(raw), "sha256": _sha(raw)})
    return {
        "schema_version": "ra-literature-survey-m19-root-inventory-v1",
        "hash_scope": "all_regular_files_before_inventory_excluding_inventory_and_summary",
        "artifact_count": len(rows), "tree_sha256": _sha(canonical_json_bytes(rows)), "artifacts": rows,
    }


def _watchdog(supervisor_pid: int, worker_pid: Any, worker_pgid: Any, finished: Any, term_at: float, kill_at: float) -> None:
    os.setsid()
    if finished.wait(max(0.0, term_at - time.monotonic())):
        return
    for is_group, pid in ((True, worker_pgid.value), (False, worker_pid.value), (False, supervisor_pid)):
        if pid:
            try:
                (os.killpg if is_group else os.kill)(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    if finished.wait(max(0.0, kill_at - time.monotonic())):
        return
    for is_group, pid in ((True, worker_pgid.value), (False, worker_pid.value), (False, supervisor_pid)):
        if pid:
            try:
                (os.killpg if is_group else os.kill)(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def _sanitize_worker_environment() -> None:
    for key in list(os.environ):
        lowered = key.lower()
        if lowered in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"} or any(
            token in lowered for token in ("token", "secret", "password", "api_key", "apikey", "credential")
        ) or key in {"PYTHONPATH", "PYTHONPYCACHEPREFIX"}:
            os.environ.pop(key, None)
    os.environ.update({"CUDA_VISIBLE_DEVICES": "-1", "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"})


def _real_worker(send: Any, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    os.set_blocking(stdout_fd, True)
    os.set_blocking(stderr_fd, True)
    os.dup2(stdout_fd, 1)
    os.dup2(stderr_fd, 2)
    os.close(stdout_fd)
    os.close(stderr_fd)
    _sanitize_worker_environment()
    outcomes = []
    try:
        result = build_survey_evidence_packet(
            topic=TOPIC, seeds=[SEED], output_dir=Path(public_root), mode="public-metadata",
            public_metadata_providers=PROVIDERS, max_records=10,
            _request_outcome_sink=outcomes.append,
        )
        envelope = {
            "schema_version": "ra-literature-survey-m19-worker-envelope-v1", "status": "complete",
            "build_result": {key: value for key, value in result.items() if key != "workflow_state"},
            "request_outcomes": outcomes, "worker_error_code": None,
        }
    except MissionStateError:
        envelope = {
            "schema_version": "ra-literature-survey-m19-worker-envelope-v1", "status": "worker_error",
            "build_result": None, "request_outcomes": outcomes, "worker_error_code": "boundary_error",
        }
    except Exception:
        envelope = {
            "schema_version": "ra-literature-survey-m19-worker-envelope-v1", "status": "worker_error",
            "build_result": None, "request_outcomes": outcomes, "worker_error_code": "build_error",
        }
    raw = canonical_json_bytes(envelope)
    if len(raw) > FRAME_CAP:
        raw = canonical_json_bytes({
            "schema_version": "ra-literature-survey-m19-worker-envelope-v1", "status": "worker_error",
            "build_result": None, "request_outcomes": outcomes, "worker_error_code": "serialization_error",
        })
    send.send_bytes(raw)
    send.close()


def _drain_streams(
    selector: selectors.BaseSelector,
    states: dict[int, dict[str, Any]],
    worker_pgid: int | None,
    *,
    wait_seconds: float,
) -> bool:
    overflow_started = False
    for key, _ in selector.select(max(0.0, min(wait_seconds, 0.25))):
        descriptor = key.fd
        state = states[descriptor]
        try:
            raw = os.read(descriptor, STREAM_CAP)
        except BlockingIOError:
            continue
        if not raw:
            state["complete"] = True
            selector.unregister(descriptor)
            os.close(descriptor)
            continue
        state["count"] += len(raw)
        state["digest"].update(raw)
        if state["count"] > STREAM_CAP and not state["overflow"]:
            state["overflow"] = True
            overflow_started = True
            if worker_pgid:
                try:
                    os.killpg(worker_pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    os.kill(worker_pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
    return overflow_started


def _stream_artifact(state: dict[str, Any]) -> dict[str, Any]:
    count = state["count"]
    status = "empty" if count == 0 else "overflow" if state["overflow"] else "unexpected_output"
    return _stream_record(status, count, state["digest"].hexdigest(), state["complete"])


def _command_exit(
    *,
    worker_pid: int | None,
    worker_pgid: int | None,
    exit_code: int | None,
    signals: list[str],
    wall: float,
    classification: str,
) -> dict[str, Any]:
    return {
        "schema_version": "ra-literature-survey-m19-command-exit-v1",
        "status": "complete" if classification == "completed" else "incomplete",
        "worker_started": worker_pid is not None,
        "worker_pid": worker_pid,
        "worker_pgid": worker_pgid,
        "soft_termination_initiated": "SIGTERM" in signals,
        "hard_kill_initiated": "SIGKILL" in signals,
        "signals_sent": signals,
        "worker_exit_code": exit_code,
        "total_wall_time_seconds": wall,
        "normalized_exit_classification": classification,
    }


def run_supervised(
    root: Path,
    *,
    worker_target: Callable[..., None] = _real_worker,
) -> int:
    entry = time.monotonic()
    context = multiprocessing.get_context("fork")
    finished = context.Event()
    worker_pid_shared = context.Value("q", 0)
    worker_pgid_shared = context.Value("q", 0)
    watchdog = context.Process(
        target=_watchdog,
        args=(os.getpid(), worker_pid_shared, worker_pgid_shared, finished,
              entry + WATCHDOG_TERM_SECONDS, entry + ABSOLUTE_SECONDS),
        name="m19-watchdog",
    )
    watchdog.start()
    worker: multiprocessing.Process | None = None
    receive = None
    selector = selectors.DefaultSelector()
    stream_states: dict[int, dict[str, Any]] = {}
    signals: list[str] = []
    classification = "worker_start_failed"
    envelope = None
    manifest = None
    ledger = None
    try:
        root = root.absolute()
        try:
            _preflight_absent_root(root)
        except MissionStateError:
            return 2
        commit = _git("rev-parse", "HEAD")
        manifest = route_manifest(commit)
        root.mkdir(parents=True, exist_ok=False)
        _atomic_write(root / "route_manifest.json", _route_manifest_bytes(manifest))
        _atomic_write(root / "environment_manifest.json", pretty_json_bytes(_environment_manifest(commit)))
        receive, send = context.Pipe(duplex=False)
        stdout_read, stdout_write = os.pipe()
        stderr_read, stderr_write = os.pipe()
        for descriptor, name in ((stdout_read, "stdout"), (stderr_read, "stderr")):
            os.set_blocking(descriptor, False)
            selector.register(descriptor, selectors.EVENT_READ)
            stream_states[descriptor] = {
                "name": name, "count": 0, "digest": hashlib.sha256(),
                "overflow": False, "complete": False,
            }
        worker = context.Process(
            target=worker_target,
            args=(send, str(root / "public_metadata"), stdout_write, stderr_write),
            name="m19-metadata-worker",
        )
        worker.start()
        worker_pid_shared.value = worker.pid or 0
        worker_pgid_shared.value = worker.pid or 0
        send.close()
        os.close(stdout_write)
        os.close(stderr_write)
        frame_received = False
        eof_received = False
        overflow_terminated = False
        while time.monotonic() < entry + HARD_SECONDS:
            now = time.monotonic()
            overflow_terminated |= _drain_streams(
                selector, stream_states, worker.pid, wait_seconds=entry + HARD_SECONDS - now
            )
            if not frame_received and receive.poll(0):
                try:
                    raw = receive.recv_bytes(FRAME_CAP + 1)
                except (EOFError, OSError):
                    classification = "invalid_ipc"
                    break
                if len(raw) > FRAME_CAP:
                    classification = "invalid_ipc"
                    break
                try:
                    envelope = _loads_closed(raw)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    classification = "invalid_ipc"
                    break
                frame_received = True
            elif frame_received and receive.poll(0):
                try:
                    receive.recv_bytes(FRAME_CAP + 1)
                except EOFError:
                    eof_received = True
                except OSError:
                    classification = "invalid_ipc"
                    break
                else:
                    classification = "invalid_ipc"
                    break
            if worker.exitcode is not None and frame_received:
                if not eof_received:
                    try:
                        receive.recv_bytes(FRAME_CAP + 1)
                    except EOFError:
                        eof_received = True
                    except OSError:
                        classification = "invalid_ipc"
                        break
                    else:
                        classification = "invalid_ipc"
                        break
                if not selector.get_map():
                    break
            if now >= entry + SOFT_SECONDS and worker.is_alive() and "SIGTERM" not in signals:
                try:
                    os.killpg(worker.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    os.kill(worker.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                signals.append("SIGTERM")
            if not worker.is_alive() and not selector.get_map():
                break
        if worker.is_alive():
            if "SIGTERM" not in signals:
                try:
                    os.killpg(worker.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    os.kill(worker.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                signals.append("SIGTERM")
            remaining = max(0.0, entry + HARD_SECONDS - time.monotonic())
            worker.join(remaining)
        if worker.is_alive():
            try:
                os.killpg(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.kill(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            signals.append("SIGKILL")
        worker.join(max(0.0, entry + WATCHDOG_TERM_SECONDS - time.monotonic()))
        for descriptor in list(selector.get_map()):
            _drain_streams(selector, stream_states, worker.pid, wait_seconds=0)
        stdout_state = next(state for state in stream_states.values() if state["name"] == "stdout")
        stderr_state = next(state for state in stream_states.values() if state["name"] == "stderr")
        stdout_record = _stream_artifact(stdout_state)
        stderr_record = _stream_artifact(stderr_state)
        if classification == "invalid_ipc":
            pass
        elif signals == ["SIGTERM", "SIGKILL"]:
            classification = "supervisor_hard_kill"
        elif signals == ["SIGTERM"] and not overflow_terminated:
            classification = "supervisor_soft_timeout"
        elif stdout_record["status"] != "empty" or stderr_record["status"] != "empty":
            classification = "unexpected_worker_output"
        elif envelope is None or not eof_received:
            classification = "invalid_ipc"
        elif worker.exitcode != 0:
            classification = "worker_error"
        else:
            try:
                _, rows, ledger_status = validate_envelope(envelope, manifest, root / "public_metadata")
                ledger = request_ledger(manifest, rows, ledger_status)
                classification = "completed" if ledger_status == "complete" else "worker_error"
            except MissionStateError as exc:
                prefix = exc.details.get("validated_prefix", [])
                ledger = request_ledger(manifest, prefix, "invalid_ledger")
                classification = "invalid_ipc"
            except (ValueError, UnicodeDecodeError):
                classification = "invalid_ipc"
        wall = min(max(0.0, time.monotonic() - entry), ABSOLUTE_SECONDS)
        exit_record = _command_exit(
            worker_pid=worker.pid, worker_pgid=worker.pid, exit_code=worker.exitcode,
            signals=signals, wall=wall, classification=classification,
        )
        _atomic_write(root / "logs/stdout.json", pretty_json_bytes(stdout_record))
        _atomic_write(root / "logs/stderr.log", _stderr_line(stderr_record))
        _atomic_write(root / "logs/command_exit.json", pretty_json_bytes(exit_record))
        if ledger is None and classification == "invalid_ipc":
            ledger = request_ledger(manifest, [], "invalid_ledger")
        elif ledger is None and classification in {
            "worker_error", "supervisor_soft_timeout", "supervisor_hard_kill",
            "unexpected_worker_output",
        }:
            ledger = request_ledger(manifest, [], "incomplete_worker_terminated")
        if ledger is not None:
            _atomic_write(root / "request_ledger.json", pretty_json_bytes(ledger))
        if classification != "completed":
            return 1
        inventory = root_inventory(root)
        _atomic_write(root / "root_inventory.json", pretty_json_bytes(inventory))
        hashes = {
            "route_manifest_sha256": _sha((root / "route_manifest.json").read_bytes()),
            "request_ledger_sha256": _sha((root / "request_ledger.json").read_bytes()),
            "command_exit_sha256": _sha((root / "logs/command_exit.json").read_bytes()),
            "environment_manifest_sha256": _sha((root / "environment_manifest.json").read_bytes()),
            "root_inventory_sha256": _sha((root / "root_inventory.json").read_bytes()),
            "public_metadata_manifest_sha256": _sha((root / "public_metadata/build_manifest.json").read_bytes()),
        }
        summary = {
            "schema_version": "ra-literature-survey-m19-hardening-summary-v1",
            "status": "passed", "boundary_valid": True, "hardening_commit": commit,
            **hashes, "what_is_not_concluded": NONCLAIMS,
        }
        _atomic_write(root / "hardening_summary.json", pretty_json_bytes(summary))
        finished.set()
        watchdog.join(max(0.0, entry + ABSOLUTE_SECONDS - time.monotonic()))
        return 0
    finally:
        if receive is not None:
            receive.close()
        for descriptor in list(selector.get_map()):
            try:
                selector.unregister(descriptor)
                os.close(descriptor)
            except OSError:
                pass
        selector.close()
        if worker is not None and worker.is_alive():
            try:
                os.killpg(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.kill(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            worker.join(0.5)
        if not finished.is_set() and time.monotonic() < entry + WATCHDOG_TERM_SECONDS:
            finished.set()
        watchdog.join(max(0.0, min(1.0, entry + ABSOLUTE_SECONDS - time.monotonic())))


def main() -> int:
    # The live entry point intentionally has no arbitrary command arguments.
    if len(sys.argv) != 1:
        return 2
    return run_supervised(LIVE_OUTPUT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
