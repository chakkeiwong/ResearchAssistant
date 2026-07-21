from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable


ATTEMPT_SCHEMA = "ra-literature-survey-m20b4-attempt-invocation-v1"
REPLAY_SCHEMA = "ra-literature-survey-m20b4-offline-replay-v1"
RECONCILIATION_SCHEMA = "ra-literature-survey-m20b4-cross-artifact-reconciliation-v1"
CREDENTIAL_SCAN_SCHEMA = "ra-literature-survey-m20b4-credential-surface-scan-result-v1"
RUN_MANIFEST_SCHEMA = "ra-literature-survey-m20b4-run-manifest-v1"
SUPERVISOR_SCHEMA = "ra-literature-survey-m20-live-supervisor-v1"
NOT_ESTABLISHED = "not_established"
FROZEN_PACKET_FILE_SHA256 = "c3e250b05e2d11ac7c0281aeaa00b467a3b9e7eb90ee1da68d729dfdbfad77ce"
FROZEN_PACKET_CONTRACT_SHA256 = "475b15f8e3af79447608616232984744cedca53da59a90642754c5644213dfda"
FROZEN_PACKET_SCHEMA = "ra-literature-survey-m20b4-live-packet-v1"
FROZEN_PACKET_PATH = Path(
    "/home/chakwong/research-assistant/docs/validation/"
    "literature_survey_m20b3_identified_integration_2026-07-15/m20b4_live_packet.json"
)
FROZEN_LIVE_ROOT = Path(
    "/home/chakwong/research-assistant/docs/validation/"
    "literature_survey_m20b4_live_2026-07-15"
)
FROZEN_COMMAND = [
    "/tmp/research-assistant-m20b3-install-7283a00e/venv/bin/python",
    "-I",
    "-m",
    "research_assistant.survey.m20_live_supervisor",
    "--packet",
    str(FROZEN_PACKET_PATH),
    "--output-root",
    str(FROZEN_LIVE_ROOT),
    "--execute-approved-m20b4",
]
SUPERVISOR_CLASSIFICATIONS = {
    "completed",
    "worker_failed",
    "soft_timeout",
    "hard_timeout",
    "final_reap_timeout",
    "worker_start_failed",
    "supervisor_lifecycle_error",
    "cleanup_reap_indeterminate",
    "worker_artifact_invalid",
}
SIGNAL_VOCABULARY = {
    "SIGTERM",
    "SIGTERM_PID_FALLBACK",
    "SIGTERM_FAILED",
    "SIGKILL",
    "SIGKILL_PID_FALLBACK",
    "SIGKILL_FAILED",
}
TIME_CONSTANTS = {
    "soft_seconds": 367.0,
    "hard_seconds": 370.0,
    "final_reap_seconds": 372.0,
    "absolute_seconds": 373.0,
}
REPRESENTATION_CLASSES = [
    "raw_utf8",
    "percent_encoded",
    "plus_encoded",
    "json_escaped",
    "nested_json_escaped",
]
PROHIBITED_SURFACES = [
    "accepted_response_body",
    "application_log",
    "captured_stderr",
    "captured_stdout",
    "command_argument",
    "descriptor",
    "exception_crossing_boundary",
    "filename",
    "git_candidate",
    "ipc_value",
    "manifest",
    "result_artifact",
    "review_artifact",
    "serialized_value",
    "temporary_file",
]
SUPERVISOR_KEYS = {
    "schema_version",
    "classification",
    "packet_contract_sha256",
    "execution_commit",
    "route_manifest_sha256",
    "worker_returncode",
    "worker_reaped",
    "signals_sent",
    "elapsed_seconds",
    "soft_seconds",
    "hard_seconds",
    "final_reap_seconds",
    "absolute_seconds",
    "stdout_policy",
    "stderr_policy",
    "artifact_inventory",
    "manifest_published_last",
}
TOP_LEVEL_WORKER_FILES = {
    "accepted_body_inventory.json",
    "campaign_summary.json",
    "identity_outcomes.json",
    "replay_ledger.json",
    "request_ledger.json",
    "route_manifest.json",
}
ACCEPTED_BODY_PATH = re.compile(
    r"cases/(?:topic|arxiv_seed|openalex)/accepted_bodies/request-[0-9a-f]{64}\.body"
)


class CloseoutError(RuntimeError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _loads_closed(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise CloseoutError("duplicate_json_key")
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(CloseoutError("nonfinite_json")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloseoutError("invalid_json") from exc


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CloseoutError("invalid_launch_time") from exc
    if parsed.tzinfo is None:
        raise CloseoutError("launch_time_timezone_required")
    return parsed


def _validate_packet(packet_path: Path, live_root: Path) -> tuple[dict[str, Any], str]:
    if (
        packet_path != FROZEN_PACKET_PATH
        or live_root != FROZEN_LIVE_ROOT
        or not packet_path.is_absolute()
        or not packet_path.is_file()
        or packet_path.is_symlink()
    ):
        raise CloseoutError("packet_path_invalid")
    packet_raw = packet_path.read_bytes()
    packet_file_sha256 = _sha(packet_raw)
    if packet_file_sha256 != FROZEN_PACKET_FILE_SHA256:
        raise CloseoutError("frozen_packet_file_hash_invalid")
    packet = _loads_closed(packet_raw)
    if (
        not isinstance(packet, dict)
        or packet.get("schema_version") != FROZEN_PACKET_SCHEMA
        or packet.get("packet_contract_sha256") != FROZEN_PACKET_CONTRACT_SHA256
        or packet.get("credential_interface") != "OPENALEX_API_KEY"
        or packet.get("output_root") != str(live_root)
        or packet.get("command") != FROZEN_COMMAND
    ):
        raise CloseoutError("packet_live_root_mismatch")
    try:
        from research_assistant.survey.m20_live_supervisor import packet_contract_sha256
    except ImportError as exc:
        raise CloseoutError("installed_supervisor_unavailable") from exc
    if packet_contract_sha256(packet) != FROZEN_PACKET_CONTRACT_SHA256:
        raise CloseoutError("packet_contract_invalid")
    return packet, packet_file_sha256


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return Decimal(str(value)).is_finite()
    except InvalidOperation:
        return False


def _valid_signal_sequence(classification: str, signals: list[str]) -> bool:
    if any(value not in SIGNAL_VOCABULARY for value in signals):
        return False
    kinds = tuple("TERM" if value.startswith("SIGTERM") else "KILL" for value in signals)
    if classification in {"completed", "worker_failed", "worker_start_failed", "worker_artifact_invalid"}:
        return kinds == ()
    if classification == "soft_timeout":
        return kinds in {(), ("TERM",)}
    if classification == "hard_timeout":
        return kinds in {(), ("TERM",), ("KILL",), ("TERM", "KILL")}
    if classification == "final_reap_timeout":
        return kinds in {
            (),
            ("TERM",),
            ("KILL",),
            ("KILL", "KILL"),
            ("TERM", "KILL"),
            ("TERM", "KILL", "KILL"),
        }
    if classification == "supervisor_lifecycle_error":
        return kinds in {(), ("KILL",)}
    if classification == "cleanup_reap_indeterminate":
        return kinds in {
            (),
            ("TERM",),
            ("KILL",),
            ("KILL", "KILL"),
            ("TERM", "KILL"),
            ("TERM", "KILL", "KILL"),
        }
    return False


def _valid_inventory_rows(rows: list[Any]) -> bool:
    observed_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "size_bytes", "sha256"}:
            return False
        path = row["path"]
        size = row["size_bytes"]
        digest = row["sha256"]
        if (
            not isinstance(path, str)
            or path in observed_paths
            or (path not in TOP_LEVEL_WORKER_FILES and ACCEPTED_BODY_PATH.fullmatch(path) is None)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            return False
        observed_paths.add(path)
    return True


def _valid_process_state(value: dict[str, Any]) -> bool:
    classification = value["classification"]
    returncode = value["worker_returncode"]
    reaped = value["worker_reaped"]
    if classification == "worker_start_failed":
        return returncode is None and reaped is None
    if classification == "cleanup_reap_indeterminate":
        return returncode is None and reaped is False
    if isinstance(returncode, bool) or not isinstance(returncode, int) or reaped is not True:
        return False
    if classification in {"completed", "worker_artifact_invalid"}:
        return returncode == 0
    if classification == "worker_failed":
        return returncode != 0
    return classification in {
        "soft_timeout",
        "hard_timeout",
        "final_reap_timeout",
        "supervisor_lifecycle_error",
    }


def _validate_supervisor(
    path: Path,
    *,
    packet: dict[str, Any],
) -> dict[str, Any]:
    value = _loads_closed(path.read_bytes())
    if not isinstance(value, dict) or set(value) != SUPERVISOR_KEYS:
        raise CloseoutError("supervisor_manifest_schema_invalid")
    if (
        value["schema_version"] != SUPERVISOR_SCHEMA
        or value["packet_contract_sha256"] != packet["packet_contract_sha256"]
        or value["execution_commit"] != packet["execution_commit"]
        or value["route_manifest_sha256"] != packet["route_manifest_sha256"]
        or value["manifest_published_last"] is not True
        or value["stdout_policy"] != "discarded_to_devnull"
        or value["stderr_policy"] != "discarded_to_devnull"
        or value["classification"] not in SUPERVISOR_CLASSIFICATIONS
        or not isinstance(value["signals_sent"], list)
        or not all(isinstance(row, str) for row in value["signals_sent"])
        or not _valid_signal_sequence(value["classification"], value["signals_sent"])
        or not _valid_process_state(value)
        or not _is_number(value["elapsed_seconds"])
        or value["elapsed_seconds"] < 0
        or any(value[field] != expected for field, expected in TIME_CONSTANTS.items())
        or not isinstance(value["artifact_inventory"], list)
        or not _valid_inventory_rows(value["artifact_inventory"])
    ):
        raise CloseoutError("supervisor_manifest_invalid")
    if value["classification"] != "completed" and value["artifact_inventory"]:
        raise CloseoutError("noncompleted_artifact_inventory_invalid")
    if value["classification"] == "completed" and not value["artifact_inventory"]:
        raise CloseoutError("completed_artifact_inventory_empty")
    return value


def _inventory_reconciliation(live_root: Path, rows: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    observed = []
    for row in rows:
        if set(row) != {"path", "size_bytes", "sha256"}:
            raise CloseoutError("artifact_inventory_row_invalid")
        relative = row["path"]
        if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
            raise CloseoutError("artifact_inventory_path_invalid")
        path = live_root / relative
        if not path.is_file() or path.is_symlink():
            raise CloseoutError("inventoried_artifact_missing")
        actual = {"path": relative, "size_bytes": path.stat().st_size, "sha256": _sha_path(path)}
        observed.append(actual)
    actual_files = set()
    for path in live_root.rglob("*"):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise CloseoutError("live_artifact_topology_invalid")
        if path.is_file():
            actual_files.add(path.relative_to(live_root).as_posix())
    expected_files = {row["path"] for row in rows} | {"supervisor_manifest.json"}
    return observed == rows and actual_files == expected_files, observed


def _write_artifacts(result_root: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    if result_root.exists() or result_root.is_symlink():
        raise FileExistsError(result_root)
    result_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{result_root.name}.", dir=result_root.parent))
    try:
        for name, value in artifacts.items():
            (temporary / name).write_bytes(_pretty_bytes(value))
        temporary.rename(result_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def build_closeout(
    *,
    packet_path: Path,
    live_root: Path,
    result_root: Path,
    launch_started_at: str,
    launch_ended_at: str,
    exit_code: int | None,
    outcome_indeterminate: bool,
    plan_file: Path,
    terminal_result_file: Path,
    replay_validator: Callable[[Path], dict[str, Any]] | None = None,
    packet_validator: Callable[[Path, Path], tuple[dict[str, Any], str]] = _validate_packet,
) -> dict[str, dict[str, Any]]:
    started = _parse_time(launch_started_at)
    ended = _parse_time(launch_ended_at)
    if ended < started:
        raise CloseoutError("launch_time_order_invalid")
    if outcome_indeterminate == (exit_code is not None):
        raise CloseoutError("exactly_one_launch_outcome_required")
    if not live_root.is_absolute() or not result_root.is_absolute():
        raise CloseoutError("absolute_root_required")
    if live_root == result_root or live_root in result_root.parents or result_root in live_root.parents:
        raise CloseoutError("live_result_root_overlap")
    packet, packet_file_sha256 = packet_validator(packet_path, live_root)
    supervisor_path = live_root / "supervisor_manifest.json"
    supervisor_exists = supervisor_path.is_file() and not supervisor_path.is_symlink()
    live_root_exists = live_root.exists()
    supervisor = None
    supervisor_validation = "not_present"
    if supervisor_exists:
        try:
            supervisor = _validate_supervisor(supervisor_path, packet=packet)
            supervisor_validation = "passed"
        except (CloseoutError, OSError):
            supervisor_validation = "failed_closed"

    exit_consistent: bool | str = NOT_ESTABLISHED
    if exit_code is not None and supervisor is not None:
        expected_exit = 0 if supervisor["classification"] == "completed" else 2
        exit_consistent = exit_code == expected_exit
        if not exit_consistent:
            supervisor = None
            supervisor_validation = "exit_manifest_contradiction"

    if outcome_indeterminate:
        branch = "invocation_outcome_indeterminate"
        supervisor = None
    elif supervisor is not None:
        branch = "completed" if supervisor["classification"] == "completed" else "manifest_noncompleted"
    elif live_root_exists or exit_code == 0:
        branch = "invocation_outcome_indeterminate"
    else:
        branch = "early_supervisor_exit_no_manifest"

    attempt = {
        "schema_version": ATTEMPT_SCHEMA,
        "status": branch,
        "attempt_consumed": True,
        "packet_file_sha256": packet_file_sha256,
        "packet_contract_sha256": packet["packet_contract_sha256"],
        "execution_commit": packet["execution_commit"],
        "execution_tree": packet["execution_tree"],
        "command": packet["command"],
        "command_contains_credential_value": False,
        "launch_started_at": launch_started_at,
        "launch_ended_at": launch_ended_at,
        "wall_time_seconds": round((ended - started).total_seconds(), 6),
        "tool_session_outcome": "indeterminate" if outcome_indeterminate else "closed_exit",
        "exit_code": exit_code if exit_code is not None else NOT_ESTABLISHED,
        "live_root_exists": live_root_exists,
        "supervisor_manifest_exists": supervisor_exists,
        "supervisor_manifest_validation": supervisor_validation,
        "exit_manifest_consistent": exit_consistent,
        "retry_or_rerun_authority": False,
    }

    replay: dict[str, Any] = {
        "schema_version": REPLAY_SCHEMA,
        "status": NOT_ESTABLISHED,
        "reason": branch,
        "execution_mode": "live",
        "validation_result": NOT_ESTABLISHED,
    }
    reconciliation: dict[str, Any] = {
        "schema_version": RECONCILIATION_SCHEMA,
        "status": NOT_ESTABLISHED,
        "reason": branch,
        "packet_contract_match": NOT_ESTABLISHED,
        "execution_identity_match": NOT_ESTABLISHED,
        "supervisor_classification": NOT_ESTABLISHED,
        "worker_reaped": NOT_ESTABLISHED,
        "artifact_inventory_match": NOT_ESTABLISHED,
        "artifact_inventory": NOT_ESTABLISHED,
        "request_dispositions_closed": NOT_ESTABLISHED,
        "identity_frontier_outcomes_closed": NOT_ESTABLISHED,
        "cost_reconciliation_closed": NOT_ESTABLISHED,
    }
    credential_scan: dict[str, Any] = {
        "schema_version": CREDENTIAL_SCAN_SCHEMA,
        "status": NOT_ESTABLISHED,
        "reason": branch,
        "credential_value_or_digest_persisted": NOT_ESTABLISHED,
        "credential_reacquired_post_run": False,
        "representation_classes": REPRESENTATION_CLASSES,
        "prohibited_surfaces": PROHIBITED_SURFACES,
        "scanned_file_count": NOT_ESTABLISHED,
        "worker_artifact_persisted_match_count": NOT_ESTABLISHED,
        "supervisor_manifest_secret_free_by_closed_construction": NOT_ESTABLISHED,
        "limitations": [
            "enumerated_application_surfaces_only",
            "os_process_swap_core_tls_and_provider_logs_not_checked",
            "universal_secret_leak_freedom_not_established",
        ],
    }

    if supervisor is not None:
        reconciliation.update({
            "status": "closed_supervisor_only",
            "reason": "supervisor_manifest_valid",
            "packet_contract_match": True,
            "execution_identity_match": True,
            "supervisor_classification": supervisor["classification"],
            "worker_reaped": supervisor["worker_reaped"],
        })
        if branch == "manifest_noncompleted":
            credential_scan["supervisor_manifest_secret_free_by_closed_construction"] = True
    if branch == "completed":
        try:
            inventory_match, observed_inventory = _inventory_reconciliation(
                live_root, supervisor["artifact_inventory"]
            )
            if not inventory_match:
                raise CloseoutError("artifact_inventory_mismatch")
            if replay_validator is None:
                from research_assistant.survey.m20_live_worker import validate_published_run

                replay_validator = lambda root: validate_published_run(root, execution_mode="live")
            validation_result = replay_validator(live_root)
            replay.update({
                "status": "passed",
                "reason": "installed_offline_replay",
                "validation_result": validation_result,
            })
            reconciliation.update({
                "status": "passed",
                "reason": "completed_artifacts_reconciled",
                "artifact_inventory_match": True,
                "artifact_inventory": observed_inventory,
                "request_dispositions_closed": True,
                "identity_frontier_outcomes_closed": True,
                "cost_reconciliation_closed": True,
            })
            credential_scan.update({
                "status": "established_zero_matches",
                "reason": "installed_supervisor_completed_after_in_memory_artifact_scan_and_reconciliation",
                "credential_value_or_digest_persisted": False,
                "scanned_file_count": len(supervisor["artifact_inventory"]),
                "worker_artifact_persisted_match_count": 0,
                "supervisor_manifest_secret_free_by_closed_construction": True,
            })
        except (CloseoutError, ImportError, OSError, RuntimeError, TypeError, ValueError):
            replay.update({
                "status": "failed_closed",
                "reason": "completed_offline_replay_or_inventory_invalid",
                "validation_result": NOT_ESTABLISHED,
            })
            reconciliation.update({
                "status": "failed_closed",
                "reason": "completed_offline_replay_or_inventory_invalid",
            })

    run_manifest = {
        "schema_version": RUN_MANIFEST_SCHEMA,
        "status": branch,
        "git_commit": packet["execution_commit"],
        "git_tree": packet["execution_tree"],
        "command": packet["command"],
        "python": packet["command"][0],
        "environment": {
            "cpu_only": True,
            "cuda_visible_devices": "-1",
            "credential_interface": packet["credential_interface"],
            "credential_value_persisted": credential_scan["credential_value_or_digest_persisted"],
            "network_scope": packet["network_scope"],
        },
        "data_version": f"metadata_provider_query_date_{started.astimezone(timezone.utc).date().isoformat()}",
        "packet_freeze_date": "2026-07-15",
        "random_seeds": "N/A",
        "wall_time_seconds": attempt["wall_time_seconds"],
        "live_root": str(live_root),
        "result_root": str(result_root),
        "plan_file": str(plan_file),
        "terminal_result_file": str(terminal_result_file),
        "terminal_result_status": NOT_ESTABLISHED,
        "prelaunch_focused_checks": "recorded_in_terminal_result_not_this_immutable_closeout",
        "attempt_invocation_record": "attempt_invocation_record.json",
        "offline_replay": "offline_replay.json",
        "cross_artifact_reconciliation": "cross_artifact_reconciliation.json",
        "credential_surface_scan_result": "credential_surface_scan_result.json",
        "retry_or_rerun_authority": False,
        "nonclaims": packet["nonclaims"],
    }
    artifacts = {
        "attempt_invocation_record.json": attempt,
        "offline_replay.json": replay,
        "cross_artifact_reconciliation.json": reconciliation,
        "credential_surface_scan_result.json": credential_scan,
        "run_manifest.json": run_manifest,
    }
    _write_artifacts(result_root, artifacts)
    return artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--launch-started-at", required=True)
    parser.add_argument("--launch-ended-at", required=True)
    outcome = parser.add_mutually_exclusive_group(required=True)
    outcome.add_argument("--exit-code", type=int)
    outcome.add_argument("--outcome-indeterminate", action="store_true")
    parser.add_argument("--plan-file", type=Path, required=True)
    parser.add_argument("--terminal-result-file", type=Path, required=True)
    args = parser.parse_args(argv)
    build_closeout(
        packet_path=args.packet.resolve(strict=False),
        live_root=args.live_root.resolve(strict=False),
        result_root=args.result_root.resolve(strict=False),
        launch_started_at=args.launch_started_at,
        launch_ended_at=args.launch_ended_at,
        exit_code=args.exit_code,
        outcome_indeterminate=args.outcome_indeterminate,
        plan_file=args.plan_file.resolve(strict=False),
        terminal_result_file=args.terminal_result_file.resolve(strict=False),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
