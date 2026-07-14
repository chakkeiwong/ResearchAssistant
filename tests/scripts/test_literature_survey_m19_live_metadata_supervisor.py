from __future__ import annotations

import hashlib
import json
import os
import signal
import time
from copy import deepcopy
from pathlib import Path

import pytest

from research_assistant.survey import build as survey_build
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes
from scripts import literature_survey_m19_live_metadata_supervisor as supervisor


def _outcome(route: dict, *, status: str = "unavailable_transport_error") -> dict:
    topic_query = route["query_kind"] == "topic_search"
    return survey_build._m19_outcome(
        provider=route["provider"],
        query_kind=route["query_kind"],
        normalized_seed_key=None if topic_query else supervisor.SEED,
        topic_query=topic_query,
        request_index=route["request_index"],
        method="GET",
        scheme="https",
        hostname=route["hostname"],
        path=route["path"],
        query_keys=list(route["query"]),
        request_binding_sha256=route["request_binding_sha256"],
        status=status,
        error_class="transport" if status != "available" else None,
        error_code="dns_failure" if status != "available" else None,
        final_url=None if status != "available" else f"https://{route['hostname']}{route['path']}?x=ignored",
        observed_elapsed_seconds=0.25,
    )


def _manifest() -> dict:
    return supervisor.route_manifest("a" * 40)


def _fake_collection(*, outcome_sink, **kwargs):
    manifest = _manifest()
    rows = [_outcome(route) for route in manifest["routes"]]
    for row in rows:
        outcome_sink(row)
    statuses = [
        {
            "provider": row["provider"],
            "query_kind": row["query_kind"],
            "normalized_seed_key": row["normalized_seed_key"],
            "topic_query": row["topic_query"],
            "query_cap": 5 if row["query_kind"] == "seed_resolution" else 10,
            "status": "unavailable",
            "record_count": 0,
            "raw_response_saved": False,
        }
        for row in rows
    ]
    return {
        "status": "metadata_empty_or_unavailable",
        "fetched_at": "2026-07-14T00:00:00+00:00",
        "records": [],
        "provider_statuses": statuses,
        "raw_response_policy": {
            "raw_responses_saved": False,
            "privacy_scan": "not_applicable_raw_responses_not_saved",
            "reason": "M19 closed transport does not persist provider responses.",
        },
    }


def _invalid_frame_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    os.close(stdout_fd)
    os.close(stderr_fd)
    send.send_bytes(b'{"duplicate":1,"duplicate":2}')
    send.close()


def _output_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    os.write(stdout_fd, b"x" * (supervisor.STREAM_CAP + 1))
    os.close(stdout_fd)
    os.close(stderr_fd)
    send.close()


def _oversized_frame_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    os.close(stdout_fd)
    os.close(stderr_fd)
    send.send_bytes(b"x" * (supervisor.FRAME_CAP + 1))
    send.close()


def _extra_frame_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    os.close(stdout_fd)
    os.close(stderr_fd)
    raw = canonical_json_bytes({
        "schema_version": "ra-literature-survey-m19-worker-envelope-v1",
        "status": "worker_error", "build_result": None,
        "request_outcomes": [], "worker_error_code": "build_error",
    })
    send.send_bytes(raw)
    send.send_bytes(raw)
    send.close()


def _invalid_second_row_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    os.close(stdout_fd)
    os.close(stderr_fd)
    manifest = _manifest()
    first = _outcome(manifest["routes"][0])
    second = _outcome(manifest["routes"][1])
    second["request_index"] = 99
    send.send_bytes(canonical_json_bytes({
        "schema_version": "ra-literature-survey-m19-worker-envelope-v1",
        "status": "worker_error", "build_result": None,
        "request_outcomes": [first, second], "worker_error_code": "boundary_error",
    }))
    send.close()


def _hanging_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    signal.signal(signal.SIGTERM, lambda signum, frame: os._exit(143))
    os.close(stdout_fd)
    os.close(stderr_fd)
    send.send_bytes(canonical_json_bytes({
        "schema_version": "ra-literature-survey-m19-worker-envelope-v1",
        "status": "worker_error", "build_result": None,
        "request_outcomes": [], "worker_error_code": "build_error",
    }))
    while True:
        time.sleep(1)


def _term_ignoring_worker(send, public_root: str, stdout_fd: int, stderr_fd: int) -> None:
    os.setsid()
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.close(stdout_fd)
    os.close(stderr_fd)
    send.send_bytes(canonical_json_bytes({
        "schema_version": "ra-literature-survey-m19-worker-envelope-v1",
        "status": "worker_error", "build_result": None,
        "request_outcomes": [], "worker_error_code": "build_error",
    }))
    while True:
        time.sleep(1)


def test_route_manifest_exact_values_and_bindings() -> None:
    manifest = _manifest()
    assert set(manifest) == {
        "schema_version", "hardening_commit", "topic", "seed", "providers",
        "max_records", "user_agent", "routes", "request_cap", "byte_caps",
        "timeout_seconds", "whole_attempt_seconds", "redirect_cap", "retry_cap",
        "proxy_policy", "forbidden_headers",
    }
    assert manifest["providers"] == ["arxiv", "openalex"]
    assert manifest["request_cap"] == 4
    assert manifest["byte_caps"] == {"per_request": 2_000_000, "total": 8_000_000}
    assert manifest["forbidden_headers"] == supervisor.FORBIDDEN_HEADERS
    for row in manifest["routes"]:
        payload = {key: value for key, value in row.items() if key != "request_binding_sha256"}
        assert row["request_binding_sha256"] == hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def test_complete_ledger_and_closed_totals() -> None:
    manifest = _manifest()
    rows = [_outcome(route) for route in manifest["routes"]]
    ledger = supervisor.request_ledger(manifest, rows, "complete")
    assert ledger["status"] == "complete"
    assert ledger["totals"] == {
        "attempted_request_count": 4,
        "available_request_count": 0,
        "unavailable_request_count": 4,
        "boundary_invalid_request_count": 0,
        "accepted_payload_bytes": 0,
        "diagnostic_overflow_bytes": 0,
        "redirect_count": 0,
        "retry_count": 0,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_index", True),
        ("requested_port", True),
        ("configured_timeout_seconds", False),
        ("observed_elapsed_seconds", float("nan")),
        ("accepted_payload_bytes", 2_000_001),
        ("normalized_record_count", 11),
        ("raw_response_saved", True),
        ("sanitized_error_code", "raw secret exception"),
    ],
)
def test_request_row_mutations_are_rejected(field: str, value) -> None:
    manifest = _manifest()
    row = _outcome(manifest["routes"][0])
    row[field] = value
    with pytest.raises(MissionStateError, match="request|elapsed|cap"):
        supervisor.request_ledger(manifest, [row], "incomplete_worker_terminated")


def test_complete_ledger_requires_four_rows_and_no_boundary_invalidity() -> None:
    manifest = _manifest()
    rows = [_outcome(route) for route in manifest["routes"]]
    with pytest.raises(MissionStateError, match="row count"):
        supervisor.request_ledger(manifest, rows[:3], "complete")
    blocked = deepcopy(rows)
    blocked[0].update({
        "status": "blocked_invalid_request",
        "sanitized_error_class": "request_validation",
        "sanitized_error_code": "dispatch_cap_exceeded",
    })
    with pytest.raises(MissionStateError, match="boundary invalidity"):
        supervisor.request_ledger(manifest, blocked, "complete")


def test_closed_json_rejects_duplicate_keys_and_nonfinite() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        supervisor._loads_closed(b'{"x":1,"x":2}')
    with pytest.raises(ValueError):
        supervisor._loads_closed(b'{"x":NaN}')


@pytest.mark.parametrize(
    ("count", "complete", "status"),
    [(0, True, "empty"), (1, True, "unexpected_output"), (65_536, True, "unexpected_output"), (65_537, True, "overflow")],
)
def test_stream_projection_exact_boundaries(count: int, complete: bool, status: str) -> None:
    state = {
        "count": count, "digest": hashlib.sha256(b"x" * count),
        "overflow": count > supervisor.STREAM_CAP, "complete": complete,
    }
    record = supervisor._stream_artifact(state)
    assert record["status"] == status
    assert record["observed_byte_count"] == count
    assert record["sha256"] == hashlib.sha256(b"x" * count).hexdigest()
    assert record["content_saved"] is False
    line = supervisor._stderr_line(record)
    assert line.endswith(b"content_saved=false\n")
    assert line.count(b"\n") == 1
    assert str(count).encode("ascii") in line


def test_root_inventory_rejects_symlink_and_unknown_directory(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "unknown").mkdir()
    with pytest.raises(MissionStateError, match="unknown directory"):
        supervisor.root_inventory(root)
    (root / "unknown").rmdir()
    (root / "link").symlink_to("target")
    with pytest.raises(MissionStateError, match="nonregular"):
        supervisor.root_inventory(root)


def test_fake_supervisor_run_publishes_summary_last_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(survey_build, "_collect_public_metadata_m19", _fake_collection)
    root = tmp_path / "fake_run"
    assert supervisor.run_supervised(root) == 0
    summary = json.loads((root / "hardening_summary.json").read_text())
    ledger = json.loads((root / "request_ledger.json").read_text())
    inventory = json.loads((root / "root_inventory.json").read_text())
    assert summary["status"] == "passed"
    assert summary["boundary_valid"] is True
    assert ledger["status"] == "complete"
    assert ledger["totals"]["attempted_request_count"] == 4
    assert "hardening_summary.json" not in {row["path"] for row in inventory["artifacts"]}
    assert "root_inventory.json" not in {row["path"] for row in inventory["artifacts"]}
    assert set(path.name for path in (root / "public_metadata").iterdir()) == set(survey_build.PUBLIC_METADATA_PACKET_FILES)


def test_invalid_ipc_retains_zero_row_invalid_ledger_and_no_summary(tmp_path: Path) -> None:
    root = tmp_path / "invalid"
    assert supervisor.run_supervised(root, worker_target=_invalid_frame_worker) == 1
    ledger = json.loads((root / "request_ledger.json").read_text())
    exit_record = json.loads((root / "logs/command_exit.json").read_text())
    assert ledger["status"] == "invalid_ledger"
    assert ledger["requests"] == []
    assert exit_record["normalized_exit_classification"] == "invalid_ipc"
    assert not (root / "hardening_summary.json").exists()


def test_stream_overflow_is_counted_hashed_and_cannot_publish_summary(tmp_path: Path) -> None:
    root = tmp_path / "overflow"
    assert supervisor.run_supervised(root, worker_target=_output_worker) == 1
    record = json.loads((root / "logs/stdout.json").read_text())
    assert record["status"] == "overflow"
    assert record["observed_byte_count"] == supervisor.STREAM_CAP + 1
    assert record["sha256"] == hashlib.sha256(b"x" * (supervisor.STREAM_CAP + 1)).hexdigest()
    assert record["content_saved"] is False
    assert not (root / "hardening_summary.json").exists()


@pytest.mark.parametrize("worker", [_oversized_frame_worker, _extra_frame_worker])
def test_oversized_or_extra_frames_are_invalid_ipc(worker, tmp_path: Path) -> None:
    root = tmp_path / worker.__name__
    assert supervisor.run_supervised(root, worker_target=worker) == 1
    ledger = json.loads((root / "request_ledger.json").read_text())
    assert ledger["status"] == "invalid_ledger"
    assert ledger["requests"] == []
    assert not (root / "hardening_summary.json").exists()


def test_invalid_envelope_retains_only_validated_prefix(tmp_path: Path) -> None:
    root = tmp_path / "prefix"
    assert supervisor.run_supervised(root, worker_target=_invalid_second_row_worker) == 1
    ledger = json.loads((root / "request_ledger.json").read_text())
    assert ledger["status"] == "invalid_ledger"
    assert [row["request_index"] for row in ledger["requests"]] == [1]
    assert ledger["totals"]["attempted_request_count"] == 1


def test_existing_and_symlink_roots_are_preflight_blocked(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    assert supervisor.run_supervised(existing, worker_target=_invalid_frame_worker) == 2
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    assert supervisor.run_supervised(link, worker_target=_invalid_frame_worker) == 2


def test_symlink_ancestor_is_preflight_blocked(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(MissionStateError, match="ancestor"):
        supervisor._preflight_absent_root(link / "child" / "run")


def test_missing_parent_is_preflight_blocked(tmp_path: Path) -> None:
    with pytest.raises(MissionStateError, match="parent"):
        supervisor._preflight_absent_root(tmp_path / "missing" / "run")


def test_atomic_publication_never_overwrites_racing_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "result.json"
    original_link = os.link

    def racing_link(source, destination):
        Path(destination).write_bytes(b"racer")
        return original_link(source, destination)

    monkeypatch.setattr(supervisor.os, "link", racing_link)
    with pytest.raises(MissionStateError, match="appeared during publication"):
        supervisor._atomic_write(target, b"ours")
    assert target.read_bytes() == b"racer"
    residue = list(tmp_path.glob(".result.json.*.tmp"))
    assert len(residue) == 1
    assert residue[0].read_bytes() == b"ours"


def test_soft_and_hard_worker_deadlines_are_classified(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_git",
        lambda *args: "a" * 40 if args == ("rev-parse", "HEAD") else "main",
    )
    monkeypatch.setattr(supervisor, "SOFT_SECONDS", 1.00)
    monkeypatch.setattr(supervisor, "HARD_SECONDS", 1.50)
    monkeypatch.setattr(supervisor, "WATCHDOG_TERM_SECONDS", 1.70)
    monkeypatch.setattr(supervisor, "ABSOLUTE_SECONDS", 1.90)
    soft = tmp_path / "soft"
    assert supervisor.run_supervised(soft, worker_target=_hanging_worker) == 1
    soft_exit = json.loads((soft / "logs/command_exit.json").read_text())
    assert soft_exit["normalized_exit_classification"] == "supervisor_soft_timeout"
    assert soft_exit["signals_sent"] == ["SIGTERM"]
    hard = tmp_path / "hard"
    assert supervisor.run_supervised(hard, worker_target=_term_ignoring_worker) == 1
    hard_exit = json.loads((hard / "logs/command_exit.json").read_text())
    assert hard_exit["normalized_exit_classification"] == "supervisor_hard_kill"
    assert hard_exit["signals_sent"] == ["SIGTERM", "SIGKILL"]


def test_watchdog_signals_group_worker_pid_and_supervisor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Value:
        def __init__(self, value):
            self.value = value

    class Event:
        def wait(self, timeout):
            return False

    calls = []
    monkeypatch.setattr(supervisor.os, "setsid", lambda: None)
    monkeypatch.setattr(supervisor.os, "killpg", lambda pid, sig: calls.append(("group", pid, sig)))
    monkeypatch.setattr(supervisor.os, "kill", lambda pid, sig: calls.append(("pid", pid, sig)))
    now = supervisor.time.monotonic()
    supervisor._watchdog(11, Value(22), Value(33), Event(), now, now)
    assert calls == [
        ("group", 33, signal.SIGTERM), ("pid", 22, signal.SIGTERM), ("pid", 11, signal.SIGTERM),
        ("group", 33, signal.SIGKILL), ("pid", 22, signal.SIGKILL), ("pid", 11, signal.SIGKILL),
    ]
