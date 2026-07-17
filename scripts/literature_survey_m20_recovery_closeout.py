from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable


PACKET_SCHEMA = "ra-literature-survey-m20-recovery-live-packet-v3"
DIAGNOSTIC_SCHEMA = "ra-literature-survey-m20-launch-diagnostic-v1"
OUTER_INTENT_SCHEMA = "ra-literature-survey-m20-recovery-outer-intent-v1"
OUTER_SCHEMA = "ra-literature-survey-m20-recovery-outer-invocation-v2"
SUPERVISOR_SCHEMA = "ra-literature-survey-m20-live-supervisor-v2"
CLOSEOUT_SCHEMA = "ra-literature-survey-m20-recovery-closeout-v1"
CAMPAIGN_STATE_SCHEMA = "ra-literature-survey-m20-recovery-campaign-state-v1"
NOT_ESTABLISHED = "not_established"
SIGNAL_VOCABULARY = {
    "SIGTERM", "SIGTERM_PID_FALLBACK", "SIGTERM_FAILED",
    "SIGKILL", "SIGKILL_PID_FALLBACK", "SIGKILL_FAILED",
}
TIME_CONSTANTS = {
    "soft_seconds": 367.0,
    "hard_seconds": 370.0,
    "final_reap_seconds": 372.0,
    "absolute_seconds": 373.0,
}
EXPECTED_WORKER_DIRECTORIES = {
    "cases",
    "cases/topic",
    "cases/topic/accepted_bodies",
    "cases/arxiv_seed",
    "cases/arxiv_seed/accepted_bodies",
    "cases/openalex",
    "cases/openalex/accepted_bodies",
}
PREFLIGHT_ERROR_CODES = {
    "duplicate_json_key", "nonfinite_json", "invalid_json", "packet_path_invalid",
    "packet_shape_invalid", "packet_fixed_contract_invalid", "packet_contract_hash_invalid",
    "packet_route_manifest_invalid", "packet_git_identity_invalid", "packet_repository_root_invalid",
    "packet_git_identity_mismatch", "packet_file_identity_invalid", "packet_file_bytes_invalid",
    "installed_member_manifest_invalid", "installed_member_root_invalid", "wheel_archive_invalid",
    "installed_member_path_invalid", "installed_member_bytes_invalid", "installed_member_coverage_invalid",
    "runtime_modules_invalid", "runtime_module_missing", "runtime_module_identity_invalid",
    "runtime_module_bytes_invalid", "packet_budget_invalid", "packet_nonclaims_invalid",
    "packet_forbidden_actions_invalid", "packet_output_root_invalid",
    "packet_launch_diagnostic_path_invalid", "packet_campaign_identity_invalid",
    "packet_campaign_state_invalid", "packet_command_invalid", "output_root_not_fresh",
    "output_parent_invalid", "launch_diagnostic_path_not_fresh", "launch_diagnostic_parent_invalid",
    "packet_outer_invocation_paths_invalid", "packet_outer_invocation_path_invalid",
    "packet_outer_invocation_fallback_path_invalid", "packet_outer_intent_invalid",
    "preflight_os_error",
    "preflight_unexpected_error",
}


class RecoveryCloseoutError(RuntimeError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _loads(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise RecoveryCloseoutError("duplicate_json_key")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryCloseoutError("invalid_json") from exc


def _read_regular(path: Path, code: str) -> bytes:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RecoveryCloseoutError(code)
    return path.read_bytes()


def _validate_packet(
    path: Path,
    *,
    expected_file_sha256: str,
    expected_contract_sha256: str,
    live_root: Path,
    diagnostic_path: Path,
) -> dict[str, Any]:
    raw = _read_regular(path, "packet_path_invalid")
    if _sha(raw) != expected_file_sha256:
        raise RecoveryCloseoutError("packet_file_hash_invalid")
    packet = _loads(raw)
    if (
        not isinstance(packet, dict)
        or packet.get("schema_version") != PACKET_SCHEMA
        or packet.get("packet_contract_sha256") != expected_contract_sha256
        or packet.get("output_root") != str(live_root)
        or packet.get("launch_diagnostic_path") != str(diagnostic_path)
        or packet.get("credential_interface") != "OPENALEX_API_KEY"
    ):
        raise RecoveryCloseoutError("packet_contract_fields_invalid")
    unsigned = dict(packet)
    unsigned.pop("packet_contract_sha256", None)
    try:
        canonical = json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise RecoveryCloseoutError("packet_contract_json_invalid") from exc
    contract = _sha(canonical)
    if contract != expected_contract_sha256:
        raise RecoveryCloseoutError("packet_contract_hash_invalid")
    return packet


def _validate_outer(path: Path, *, packet_file_sha256: str) -> dict[str, Any]:
    value = _loads(_read_regular(path, "outer_invocation_missing"))
    keys = {
        "schema_version", "packet_file_sha256", "outer_intent_sha256",
        "child_outcome", "child_exit_code",
        "diagnostic_exists", "live_root_exists", "supervisor_manifest_exists",
        "credential_read_or_enumerated_by_launcher", "provider_activity",
        "cost_usd", "privacy_state",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value["schema_version"] != OUTER_SCHEMA
        or value["packet_file_sha256"] != packet_file_sha256
        or not isinstance(value["outer_intent_sha256"], str)
        or len(value["outer_intent_sha256"]) != 64
        or value["credential_read_or_enumerated_by_launcher"] is not False
        or value["provider_activity"] != NOT_ESTABLISHED
        or value["cost_usd"] != NOT_ESTABLISHED
        or value["privacy_state"] != NOT_ESTABLISHED
        or value["child_outcome"] not in {"closed_exit", "launcher_child_error"}
        or type(value["diagnostic_exists"]) is not bool
        or type(value["live_root_exists"]) is not bool
        or type(value["supervisor_manifest_exists"]) is not bool
        or (
            value["child_outcome"] == "closed_exit"
            and (type(value["child_exit_code"]) is not int or value["child_exit_code"] not in {0, 2})
        )
        or (
            value["child_outcome"] == "launcher_child_error"
            and value["child_exit_code"] != NOT_ESTABLISHED
        )
    ):
        raise RecoveryCloseoutError("outer_invocation_invalid")
    return value


def _validate_outer_intent(
    path: Path, *, packet_file_sha256: str, expected_command: list[str]
) -> dict[str, Any]:
    value = _loads(_read_regular(path, "outer_intent_missing"))
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema_version", "packet_file_sha256", "child_command",
            "credential_read_or_enumerated_by_launcher", "provider_activity",
            "cost_usd", "privacy_state",
        }
        or value["schema_version"] != OUTER_INTENT_SCHEMA
        or value["packet_file_sha256"] != packet_file_sha256
        or value["child_command"] != expected_command
        or value["credential_read_or_enumerated_by_launcher"] is not False
        or value["provider_activity"] is not False
        or value["cost_usd"] != "0.00"
        or value["privacy_state"] != "passed_closed_construction_before_child"
    ):
        raise RecoveryCloseoutError("outer_intent_invalid")
    return value


def _validate_diagnostic(path: Path, *, packet: dict[str, Any], live_root: Path) -> dict[str, Any]:
    value = _loads(_read_regular(path, "launch_diagnostic_missing"))
    keys = {
        "schema_version", "outcome", "exit_code", "error_code",
        "packet_contract_sha256", "preflight_completed",
        "credential_lookup_performed", "credential_available",
        "supervised_execution_started", "live_root_exists",
        "supervisor_manifest_exists", "provider_activity", "cost_usd",
        "privacy_state",
    }
    if not isinstance(value, dict) or set(value) != keys or value["schema_version"] != DIAGNOSTIC_SCHEMA:
        raise RecoveryCloseoutError("launch_diagnostic_schema_invalid")
    if type(value["exit_code"]) is not int or value["exit_code"] not in {0, 2}:
        raise RecoveryCloseoutError("launch_diagnostic_state_invalid")
    if (
        type(value["live_root_exists"]) is not bool
        or type(value["supervisor_manifest_exists"]) is not bool
        or value["live_root_exists"] is not live_root.exists()
    ):
        raise RecoveryCloseoutError("launch_diagnostic_state_invalid")
    expected_states = {
        "execution_flag_missing": (False, False, None, False, "execution_flag_missing"),
        "preflight_failed": (False, False, None, False, None),
        "credential_lookup_failed": (True, True, None, False, "credential_lookup_failed"),
        "credential_unavailable": (True, True, False, False, "credential_unavailable"),
        "supervisor_error": (True, True, True, True, "supervisor_error"),
        "supervised_execution_returned": (True, True, True, True, None),
    }
    expected = expected_states.get(value["outcome"])
    actual = (
        value["preflight_completed"],
        value["credential_lookup_performed"],
        value["credential_available"],
        value["supervised_execution_started"],
    )
    if expected is None or actual != expected[:4]:
        raise RecoveryCloseoutError("launch_diagnostic_transition_invalid")
    if expected[4] is not None and value["error_code"] != expected[4]:
        raise RecoveryCloseoutError("launch_diagnostic_error_code_invalid")
    if value["outcome"] == "preflight_failed" and (
        value["error_code"] not in PREFLIGHT_ERROR_CODES
    ):
        raise RecoveryCloseoutError("launch_diagnostic_error_code_invalid")
    if value["outcome"] == "supervised_execution_returned" and value["error_code"] is not None:
        raise RecoveryCloseoutError("launch_diagnostic_error_code_invalid")
    if value["privacy_state"] != NOT_ESTABLISHED:
        raise RecoveryCloseoutError("launch_diagnostic_privacy_overclaim")
    pre_execution = value["supervised_execution_started"] is False
    if pre_execution:
        if value["provider_activity"] is not False or value["cost_usd"] != "0.00":
            raise RecoveryCloseoutError("pre_execution_cost_state_invalid")
    elif value["provider_activity"] != NOT_ESTABLISHED or value["cost_usd"] != NOT_ESTABLISHED:
        raise RecoveryCloseoutError("supervised_diagnostic_overclaim")
    if value["preflight_completed"] is True:
        if value["packet_contract_sha256"] != packet["packet_contract_sha256"]:
            raise RecoveryCloseoutError("diagnostic_packet_binding_invalid")
    elif value["packet_contract_sha256"] != NOT_ESTABLISHED:
        raise RecoveryCloseoutError("diagnostic_preflight_binding_invalid")
    if value["outcome"] != "supervised_execution_returned" and value["exit_code"] != 2:
        raise RecoveryCloseoutError("launch_diagnostic_exit_invalid")
    if value["outcome"] == "supervised_execution_returned" and value["supervisor_manifest_exists"] is not True:
        raise RecoveryCloseoutError("launch_diagnostic_manifest_transition_invalid")
    if value["outcome"] != "supervised_execution_returned" and value["supervisor_manifest_exists"] is not False:
        raise RecoveryCloseoutError("launch_diagnostic_manifest_transition_invalid")
    return value


def _validate_supervisor(path: Path, *, packet: dict[str, Any]) -> dict[str, Any]:
    value = _loads(_read_regular(path, "supervisor_manifest_invalid"))
    keys = {
        "schema_version", "classification", "packet_contract_sha256",
        "lifecycle_stage",
        "execution_commit", "route_manifest_sha256", "worker_returncode",
        "worker_reaped", "signals_sent", "elapsed_seconds", "soft_seconds",
        "hard_seconds", "final_reap_seconds", "absolute_seconds",
        "stdout_policy", "stderr_policy", "artifact_inventory",
        "manifest_published_last",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value.get("schema_version") != SUPERVISOR_SCHEMA
        or value.get("packet_contract_sha256") != packet["packet_contract_sha256"]
        or value.get("execution_commit") != packet["execution_commit"]
        or value.get("route_manifest_sha256") != packet["route_manifest_sha256"]
        or value.get("manifest_published_last") is not True
        or value.get("stdout_policy") != "discarded_to_devnull"
        or value.get("stderr_policy") != "discarded_to_devnull"
        or type(value.get("elapsed_seconds")) not in {int, float}
        or isinstance(value.get("elapsed_seconds"), bool)
        or not math.isfinite(value.get("elapsed_seconds"))
        or value.get("elapsed_seconds") < 0
        or any(value.get(field) != expected for field, expected in TIME_CONSTANTS.items())
        or not isinstance(value.get("signals_sent"), list)
        or any(signal not in SIGNAL_VOCABULARY for signal in value.get("signals_sent", []))
        or not isinstance(value.get("artifact_inventory"), list)
        or value.get("classification") not in {
            "completed", "worker_failed", "soft_timeout", "hard_timeout",
            "final_reap_timeout", "worker_start_failed",
            "supervisor_lifecycle_error", "cleanup_reap_indeterminate",
            "worker_artifact_invalid",
        }
    ):
        raise RecoveryCloseoutError("supervisor_manifest_invalid")
    classification = value["classification"]
    lifecycle_stage = value["lifecycle_stage"]
    returncode = value["worker_returncode"]
    worker_reaped = value["worker_reaped"]
    signal_kinds = tuple(
        "TERM" if signal.startswith("SIGTERM") else "KILL"
        for signal in value["signals_sent"]
    )
    allowed_states = {
        "completed": {("artifact_validation", ())},
        "worker_failed": {("initial_wait", ())},
        "worker_start_failed": {("worker_spawn", ())},
        "worker_artifact_invalid": {("artifact_validation", ())},
        "soft_timeout": {("post_term_wait", ()), ("post_term_wait", ("TERM",))},
        "hard_timeout": {
            ("post_kill_wait", ()), ("post_kill_wait", ("TERM",)),
            ("post_kill_wait", ("KILL",)), ("post_kill_wait", ("TERM", "KILL")),
        },
        "final_reap_timeout": {
            ("cleanup_wait_after_final_reap_timeout", ()),
            ("cleanup_wait_after_final_reap_timeout", ("TERM",)),
            ("cleanup_wait_after_final_reap_timeout", ("KILL",)),
            ("cleanup_wait_after_final_reap_timeout", ("KILL", "KILL")),
            ("cleanup_wait_after_final_reap_timeout", ("TERM", "KILL")),
            ("cleanup_wait_after_final_reap_timeout", ("TERM", "KILL", "KILL")),
        },
        "supervisor_lifecycle_error": {
            ("initial_wait", ()), ("initial_wait", ("KILL",)),
            ("post_term_wait", ()), ("post_term_wait", ("TERM",)),
            ("post_term_wait", ("KILL",)), ("post_term_wait", ("TERM", "KILL")),
            ("post_kill_wait", ()), ("post_kill_wait", ("TERM",)),
            ("post_kill_wait", ("KILL",)), ("post_kill_wait", ("KILL", "KILL")),
            ("post_kill_wait", ("TERM", "KILL")),
            ("post_kill_wait", ("TERM", "KILL", "KILL")),
        },
        "cleanup_reap_indeterminate": {
            ("cleanup_wait_after_initial_wait", ()),
            ("cleanup_wait_after_initial_wait", ("KILL",)),
            ("cleanup_wait_after_post_term_wait", ()),
            ("cleanup_wait_after_post_term_wait", ("TERM",)),
            ("cleanup_wait_after_post_term_wait", ("KILL",)),
            ("cleanup_wait_after_post_term_wait", ("TERM", "KILL")),
            ("cleanup_wait_after_post_kill_wait", ()),
            ("cleanup_wait_after_post_kill_wait", ("TERM",)),
            ("cleanup_wait_after_post_kill_wait", ("KILL",)),
            ("cleanup_wait_after_post_kill_wait", ("KILL", "KILL")),
            ("cleanup_wait_after_post_kill_wait", ("TERM", "KILL")),
            ("cleanup_wait_after_post_kill_wait", ("TERM", "KILL", "KILL")),
            ("cleanup_wait_after_final_reap_timeout", ()),
            ("cleanup_wait_after_final_reap_timeout", ("TERM",)),
            ("cleanup_wait_after_final_reap_timeout", ("KILL",)),
            ("cleanup_wait_after_final_reap_timeout", ("KILL", "KILL")),
            ("cleanup_wait_after_final_reap_timeout", ("TERM", "KILL")),
            ("cleanup_wait_after_final_reap_timeout", ("TERM", "KILL", "KILL")),
        },
    }
    if (lifecycle_stage, signal_kinds) not in allowed_states[classification]:
        raise RecoveryCloseoutError("supervisor_signal_state_invalid")
    if classification == "worker_start_failed":
        process_valid = returncode is None and worker_reaped is None
    elif classification == "cleanup_reap_indeterminate":
        process_valid = returncode is None and worker_reaped is False
    else:
        process_valid = type(returncode) is int and worker_reaped is True
        if classification in {"completed", "worker_artifact_invalid"}:
            process_valid = process_valid and returncode == 0
        elif classification == "worker_failed":
            process_valid = process_valid and returncode != 0
    if not process_valid:
        raise RecoveryCloseoutError("supervisor_process_state_invalid")
    minimum_elapsed = {
        "soft_timeout": TIME_CONSTANTS["soft_seconds"],
        "hard_timeout": TIME_CONSTANTS["hard_seconds"],
        "final_reap_timeout": TIME_CONSTANTS["final_reap_seconds"],
    }.get(classification, 0.0)
    if lifecycle_stage == "post_term_wait":
        minimum_elapsed = max(minimum_elapsed, TIME_CONSTANTS["soft_seconds"])
    elif lifecycle_stage == "post_kill_wait":
        minimum_elapsed = max(minimum_elapsed, TIME_CONSTANTS["hard_seconds"])
    elif lifecycle_stage == "cleanup_wait_after_post_term_wait":
        minimum_elapsed = max(minimum_elapsed, TIME_CONSTANTS["soft_seconds"])
    elif lifecycle_stage == "cleanup_wait_after_post_kill_wait":
        minimum_elapsed = max(minimum_elapsed, TIME_CONSTANTS["hard_seconds"])
    elif lifecycle_stage == "cleanup_wait_after_final_reap_timeout":
        minimum_elapsed = max(minimum_elapsed, TIME_CONSTANTS["final_reap_seconds"])
    if value["elapsed_seconds"] < minimum_elapsed:
        raise RecoveryCloseoutError("supervisor_elapsed_state_invalid")
    if value["classification"] == "worker_start_failed" and (
        value["worker_returncode"] is not None
        or value["worker_reaped"] is not None
        or value["signals_sent"] != []
        or value["artifact_inventory"] != []
    ):
        raise RecoveryCloseoutError("worker_start_failed_state_invalid")
    if value["classification"] != "completed" and value["artifact_inventory"] != []:
        raise RecoveryCloseoutError("noncompleted_artifact_inventory_invalid")
    return value


def _validate_completed_inventory(root: Path, rows: Any) -> None:
    if not isinstance(rows, list) or not rows:
        raise RecoveryCloseoutError("completed_artifact_inventory_invalid")
    expected_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "size_bytes", "sha256"}:
            raise RecoveryCloseoutError("completed_artifact_inventory_invalid")
        relative = row["path"]
        if (
            not isinstance(relative, str)
            or not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or relative in expected_paths
        ):
            raise RecoveryCloseoutError("completed_artifact_inventory_invalid")
        path = root / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_nlink != 1
            or isinstance(row["size_bytes"], bool)
            or row["size_bytes"] != path.stat().st_size
            or row["sha256"] != _sha(path.read_bytes())
        ):
            raise RecoveryCloseoutError("completed_artifact_inventory_mismatch")
        expected_paths.add(relative)
    actual_paths: set[str] = set()
    actual_directories: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise RecoveryCloseoutError("completed_artifact_topology_invalid")
        if path.is_file():
            if path.stat().st_nlink != 1:
                raise RecoveryCloseoutError("completed_artifact_topology_invalid")
            actual_paths.add(path.relative_to(root).as_posix())
        else:
            actual_directories.add(path.relative_to(root).as_posix())
    if actual_paths != expected_paths | {"supervisor_manifest.json"}:
        raise RecoveryCloseoutError("completed_artifact_set_mismatch")
    if actual_directories != EXPECTED_WORKER_DIRECTORIES:
        raise RecoveryCloseoutError("completed_artifact_directory_set_mismatch")


def _completed_cost(root: Path) -> tuple[str, bool, str, str | None]:
    summary = _loads(_read_regular(root / "campaign_summary.json", "campaign_summary_missing"))
    evidence = summary.get("cost_evidence") if isinstance(summary, dict) else None
    if not isinstance(evidence, dict):
        raise RecoveryCloseoutError("cost_evidence_invalid")
    reserved_raw = evidence.get("reserved_cost_usd")
    reconciled_raw = evidence.get("reconciled_cost_usd")
    state = evidence.get("cost_state")
    block_code = evidence.get("cost_block_code")
    try:
        reserved = Decimal(reserved_raw)
        reconciled = Decimal(reconciled_raw)
    except (InvalidOperation, TypeError) as exc:
        raise RecoveryCloseoutError("cost_evidence_invalid") from exc
    if (
        not isinstance(reserved_raw, str)
        or not isinstance(reconciled_raw, str)
        or not reserved.is_finite()
        or not reconciled.is_finite()
        or min(reserved, reconciled) < 0
        or reconciled > reserved
        or state not in {"open", "blocked"}
        or (state == "open" and (reserved != reconciled or block_code is not None))
        or (state == "blocked" and not isinstance(block_code, str))
    ):
        raise RecoveryCloseoutError("cost_evidence_invalid")
    return reconciled_raw, reserved == reconciled, state, block_code


def _validate_campaign_state(packet: dict[str, Any]) -> tuple[dict[str, Any], str]:
    binding = packet.get("campaign_state")
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise RecoveryCloseoutError("campaign_state_binding_invalid")
    path = Path(binding["path"])
    raw = _read_regular(path, "campaign_state_path_invalid")
    if _sha(raw) != binding["sha256"]:
        raise RecoveryCloseoutError("campaign_state_hash_invalid")
    state = _loads(raw)
    if not isinstance(state, dict) or set(state) != {
        "schema_version", "campaign_id", "attempts_completed",
        "provider_launches_used", "cost_cap_usd", "reconciled_cost_usd",
        "remaining_cost_usd", "next_attempt_id", "next_attempt_allowed",
        "continuation_veto", "predecessor_campaign_state_sha256",
    }:
        raise RecoveryCloseoutError("campaign_state_schema_invalid")
    try:
        cap = Decimal(state["cost_cap_usd"])
        reconciled = Decimal(state["reconciled_cost_usd"])
        remaining = Decimal(state["remaining_cost_usd"])
    except (InvalidOperation, TypeError) as exc:
        raise RecoveryCloseoutError("campaign_state_cost_invalid") from exc
    if (
        state["schema_version"] != CAMPAIGN_STATE_SCHEMA
        or state["campaign_id"] != packet.get("campaign_id")
        or state["next_attempt_id"] != packet.get("campaign_attempt_id")
        or type(state["attempts_completed"]) is not int
        or type(state["provider_launches_used"]) is not int
        or type(state["next_attempt_allowed"]) is not bool
        or type(state["continuation_veto"]) is not bool
        or state["next_attempt_allowed"] is not True
        or state["continuation_veto"] is not False
        or min(state["attempts_completed"], state["provider_launches_used"]) < 0
        or state["provider_launches_used"] != state["attempts_completed"]
        or state["attempts_completed"] not in {0, 1}
        or state["next_attempt_id"] != f"attempt-{state['attempts_completed'] + 1:02d}"
        or (
            state["attempts_completed"] == 0
            and state["predecessor_campaign_state_sha256"] is not None
        )
        or (
            state["attempts_completed"] > 0
            and (
                not isinstance(state["predecessor_campaign_state_sha256"], str)
                or len(state["predecessor_campaign_state_sha256"]) != 64
            )
        )
        or state["provider_launches_used"] > 2
        or not cap.is_finite()
        or not reconciled.is_finite()
        or not remaining.is_finite()
        or cap != Decimal("0.01")
        or min(reconciled, remaining) < 0
        or reconciled + remaining != cap
    ):
        raise RecoveryCloseoutError("campaign_state_invalid")
    return state, binding["sha256"]


def _installed_replay(packet: dict[str, Any], root: Path) -> dict[str, Any]:
    modules = packet.get("runtime_modules")
    required = {
        "research_assistant.survey.discovery_capability",
        "research_assistant.survey.m20_live_worker",
        "research_assistant.survey.m20_live_supervisor",
        "research_assistant.survey.m20_recovery_launcher",
        "research_assistant.survey.openalex_adapter",
        "research_assistant.survey.openalex_credential_cost",
    }
    if not isinstance(modules, dict) or set(modules) != required:
        raise RecoveryCloseoutError("replay_module_binding_invalid")
    for name in required:
        binding = modules[name]
        if not isinstance(binding, dict) or set(binding) != {"origin", "sha256"}:
            raise RecoveryCloseoutError("replay_module_binding_invalid")
        origin = Path(binding["origin"])
        if _sha(_read_regular(origin, "replay_module_origin_invalid")) != binding["sha256"]:
            raise RecoveryCloseoutError("replay_module_hash_invalid")
    interpreter = Path(packet["command"][0])
    worker_origin = Path(modules["research_assistant.survey.m20_live_worker"]["origin"])
    site_packages = worker_origin.parents[2]
    install_environment_root = site_packages.parents[2]
    if (
        not interpreter.is_absolute()
        or not interpreter.is_file()
        or interpreter.parent.parent != install_environment_root
    ):
        raise RecoveryCloseoutError("replay_interpreter_invalid")
    expected_modules = {name: modules[name] for name in sorted(required)}
    code = "\n".join([
        "import hashlib, importlib, json",
        "from pathlib import Path",
        f"expected = json.loads({json.dumps(json.dumps(expected_modules, sort_keys=True))})",
        "observed = {}",
        "for name in sorted(expected):",
        "    module = importlib.import_module(name)",
        "    origin = str(Path(module.__file__).resolve())",
        "    digest = hashlib.sha256(Path(origin).read_bytes()).hexdigest()",
        "    observed[name] = {'origin': origin, 'sha256': digest}",
        "from research_assistant.survey.m20_live_worker import validate_published_run",
        f"validation = validate_published_run(Path({str(root)!r}), execution_mode='live')",
        "print(json.dumps({'runtime_modules': observed, 'validation': validation}, sort_keys=True))",
    ])
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-c", code],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            env={"CUDA_VISIBLE_DEVICES": "-1", "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RecoveryCloseoutError("installed_replay_failed") from exc
    value = _loads(completed.stdout.encode())
    if (
        not isinstance(value, dict)
        or set(value) != {"runtime_modules", "validation"}
        or value["runtime_modules"] != expected_modules
        or not isinstance(value["validation"], dict)
        or value["validation"].get("status") != "passed"
    ):
        raise RecoveryCloseoutError("installed_replay_invalid")
    return value["validation"]


def build_closeout(
    *,
    packet_path: Path,
    expected_packet_file_sha256: str,
    expected_packet_contract_sha256: str,
    live_root: Path,
    diagnostic_path: Path,
    intent_path: Path,
    outer_path: Path,
    fallback_path: Path,
    result_root: Path,
    replay_validator: Callable[[Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if result_root.exists() or result_root.is_symlink():
        raise RecoveryCloseoutError("result_root_not_fresh")
    packet = _validate_packet(
        packet_path,
        expected_file_sha256=expected_packet_file_sha256,
        expected_contract_sha256=expected_packet_contract_sha256,
        live_root=live_root,
        diagnostic_path=diagnostic_path,
    )
    if (
        packet.get("outer_intent_path") != str(intent_path)
        or packet.get("outer_invocation_path") != str(outer_path)
        or packet.get("outer_invocation_fallback_path") != str(fallback_path)
    ):
        raise RecoveryCloseoutError("outer_invocation_packet_binding_invalid")
    expected_child_command = [
        packet["command"][0], "-I", "-m",
        "research_assistant.survey.m20_live_supervisor",
        "--packet", str(packet_path),
        "--output-root", str(live_root),
        "--launch-diagnostic-path", str(diagnostic_path),
        "--execute-m20-recovery-campaign",
    ]
    _validate_outer_intent(
        intent_path,
        packet_file_sha256=expected_packet_file_sha256,
        expected_command=expected_child_command,
    )
    primary_exists = outer_path.is_file() and not outer_path.is_symlink()
    fallback_exists = fallback_path.is_file() and not fallback_path.is_symlink()
    if primary_exists == fallback_exists:
        raise RecoveryCloseoutError("exactly_one_outer_invocation_required")
    outer_record_path = outer_path if primary_exists else fallback_path
    outer = _validate_outer(outer_record_path, packet_file_sha256=expected_packet_file_sha256)
    if outer["outer_intent_sha256"] != _sha(intent_path.read_bytes()):
        raise RecoveryCloseoutError("outer_intent_terminal_binding_invalid")
    campaign_state, predecessor_campaign_state_sha256 = _validate_campaign_state(packet)
    diagnostic = _validate_diagnostic(diagnostic_path, packet=packet, live_root=live_root)
    manifest_path = live_root / "supervisor_manifest.json"
    manifest_exists = manifest_path.is_file() and not manifest_path.is_symlink()
    if diagnostic["supervisor_manifest_exists"] is not manifest_exists:
        raise RecoveryCloseoutError("diagnostic_manifest_presence_invalid")
    if (
        outer["child_outcome"] != "closed_exit"
        or outer["child_exit_code"] != diagnostic["exit_code"]
        or outer["diagnostic_exists"] is not True
        or outer["live_root_exists"] is not live_root.exists()
        or outer["supervisor_manifest_exists"] is not manifest_exists
    ):
        raise RecoveryCloseoutError("outer_diagnostic_reconciliation_invalid")

    classification: str = diagnostic["outcome"]
    provider_activity: bool | str = diagnostic["provider_activity"]
    cost_usd: str = diagnostic["cost_usd"]
    cost_reconciled = provider_activity is False
    cost_state: str | None = "open" if provider_activity is False else None
    cost_block_code: str | None = None
    replay_status = NOT_ESTABLISHED
    campaign_validity = NOT_ESTABLISHED
    privacy_state = diagnostic["privacy_state"]
    retry_eligible = False
    if manifest_exists:
        supervisor = _validate_supervisor(manifest_path, packet=packet)
        classification = supervisor["classification"]
        expected_exit_code = 0 if classification == "completed" else 2
        if diagnostic["exit_code"] != expected_exit_code:
            raise RecoveryCloseoutError("supervisor_exit_classification_invalid")
        if classification == "worker_start_failed":
            provider_activity = False
            cost_usd = "0.00"
            cost_reconciled = True
            cost_state = "open"
            privacy_state = "passed_closed_construction_no_worker_artifacts"
            retry_eligible = True
        elif classification == "completed":
            try:
                _validate_completed_inventory(live_root, supervisor["artifact_inventory"])
                if replay_validator is None:
                    replay_validator = lambda root: _installed_replay(packet, root)
                replay_result = replay_validator(live_root)
                campaign_validity = replay_result["campaign_validity"]
                cost_usd, cost_reconciled, cost_state, cost_block_code = _completed_cost(live_root)
                provider_activity = True
                replay_status = "passed"
                privacy_state = "passed_enumerated_retained_artifacts"
            except Exception:
                replay_status = "failed_closed"
                campaign_validity = NOT_ESTABLISHED
                cost_usd = NOT_ESTABLISHED
                cost_reconciled = False
                cost_state = None
                cost_block_code = None
                privacy_state = NOT_ESTABLISHED
    elif diagnostic["supervised_execution_started"] is False:
        retry_eligible = diagnostic["outcome"] in {
            "preflight_failed", "credential_lookup_failed", "credential_unavailable",
        }
        privacy_state = "passed_closed_construction_no_worker_artifacts"

    continuation_veto = (
        diagnostic["supervised_execution_started"] is True
        and not (classification == "worker_start_failed" or replay_status == "passed")
    ) or not cost_reconciled
    if continuation_veto:
        retry_eligible = False

    try:
        predecessor_cost = Decimal(campaign_state["reconciled_cost_usd"])
        current_cost = Decimal(cost_usd) if cost_reconciled else Decimal("NaN")
    except (InvalidOperation, TypeError):
        current_cost = Decimal("NaN")
        predecessor_cost = Decimal(campaign_state["reconciled_cost_usd"])
    cumulative_cost = predecessor_cost + current_cost if current_cost.is_finite() else None
    launches_used = campaign_state["provider_launches_used"] + 1
    attempts_completed = campaign_state["attempts_completed"] + 1
    if cumulative_cost is None or cumulative_cost > Decimal(campaign_state["cost_cap_usd"]):
        continuation_veto = True
        retry_eligible = False
    next_attempt_allowed = retry_eligible and launches_used < 2 and not continuation_veto
    next_campaign_state = {
        "schema_version": CAMPAIGN_STATE_SCHEMA,
        "campaign_id": packet["campaign_id"],
        "attempts_completed": attempts_completed,
        "provider_launches_used": launches_used,
        "cost_cap_usd": campaign_state["cost_cap_usd"],
        "reconciled_cost_usd": (
            format(cumulative_cost, "f") if cumulative_cost is not None else NOT_ESTABLISHED
        ),
        "remaining_cost_usd": (
            format(Decimal(campaign_state["cost_cap_usd"]) - cumulative_cost, "f")
            if cumulative_cost is not None else NOT_ESTABLISHED
        ),
        "next_attempt_id": "attempt-02" if next_attempt_allowed else None,
        "next_attempt_allowed": next_attempt_allowed,
        "continuation_veto": continuation_veto,
        "predecessor_campaign_state_sha256": predecessor_campaign_state_sha256,
    }

    record = {
        "schema_version": CLOSEOUT_SCHEMA,
        "status": (
            "passed"
            if replay_status == "passed"
            and campaign_validity == "closed"
            and cost_reconciled
            and privacy_state == "passed_enumerated_retained_artifacts"
            else "boundary_outcome"
            if replay_status == "passed" and campaign_validity == "boundary_invalid" and cost_reconciled
            else "stopped"
        ),
        "attempt_executed": True,
        "packet_file_sha256": expected_packet_file_sha256,
        "packet_contract_sha256": expected_packet_contract_sha256,
        "execution_commit": packet["execution_commit"],
        "diagnostic_sha256": _sha(diagnostic_path.read_bytes()),
        "outer_invocation_sha256": _sha(outer_record_path.read_bytes()),
        "outer_intent_sha256": _sha(intent_path.read_bytes()),
        "classification": classification,
        "exit_code": diagnostic["exit_code"],
        "supervisor_manifest_exists": manifest_exists,
        "provider_activity": provider_activity,
        "cost_usd": cost_usd,
        "cost_reconciled": cost_reconciled,
        "cost_state": cost_state if cost_state is not None else NOT_ESTABLISHED,
        "cost_block_code": cost_block_code,
        "replay_status": replay_status,
        "campaign_validity": campaign_validity,
        "m20_primary_criterion_passed": (
            replay_status == "passed"
            and campaign_validity == "closed"
            and cost_reconciled
            and privacy_state == "passed_enumerated_retained_artifacts"
        ),
        "privacy_state": privacy_state,
        "retry_eligible_under_unchanged_campaign": retry_eligible,
        "continuation_veto": continuation_veto,
        "next_campaign_state": next_campaign_state,
        "nonclaims": [
            "provider_reliability", "literature_completeness", "source_support",
            "scientific_correctness", "product_readiness", "north_star_completion",
        ],
    }
    result_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{result_root.name}.", dir=result_root.parent))
    try:
        (temporary / "recovery_closeout.json").write_text(
            json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        )
        (temporary / "next_campaign_state.json").write_text(
            json.dumps(next_campaign_state, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        )
        temporary.rename(result_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--packet-file-sha256", required=True)
    parser.add_argument("--packet-contract-sha256", required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    parser.add_argument("--launch-diagnostic", type=Path, required=True)
    parser.add_argument("--outer-intent", type=Path, required=True)
    parser.add_argument("--outer-invocation", type=Path, required=True)
    parser.add_argument("--outer-invocation-fallback", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    args = parser.parse_args(argv)
    build_closeout(
        packet_path=args.packet.resolve(strict=False),
        expected_packet_file_sha256=args.packet_file_sha256,
        expected_packet_contract_sha256=args.packet_contract_sha256,
        live_root=args.live_root.resolve(strict=False),
        diagnostic_path=args.launch_diagnostic.resolve(strict=False),
        intent_path=args.outer_intent.resolve(strict=False),
        outer_path=args.outer_invocation.resolve(strict=False),
        fallback_path=args.outer_invocation_fallback.resolve(strict=False),
        result_root=args.result_root.resolve(strict=False),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
