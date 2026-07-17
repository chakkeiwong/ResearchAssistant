from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.m20_live_worker import (
    M20WorkerError,
    PER_REQUEST_BODY_CAP,
    REQUEST_CAP,
    SOCKET_TIMEOUT_SECONDS,
    TOTAL_BODY_CAP,
    WHOLE_ATTEMPT_SECONDS,
    route_manifest,
    route_manifest_sha256,
    validate_published_run,
)
from research_assistant.survey.mission_state import canonical_json_bytes, pretty_json_bytes
from research_assistant.survey.openalex_credential_cost import (
    CAMPAIGN_COST_CAP_USD,
    CREDENTIAL_INTERFACE,
    contains_credential_representation,
)


PACKET_SCHEMA = "ra-literature-survey-m20-recovery-live-packet-v3"
SUPERVISOR_SCHEMA = "ra-literature-survey-m20-live-supervisor-v2"
LAUNCH_DIAGNOSTIC_SCHEMA = "ra-literature-survey-m20-launch-diagnostic-v1"
OUTER_INTENT_SCHEMA = "ra-literature-survey-m20-recovery-outer-intent-v1"
SOFT_SECONDS = float(WHOLE_ATTEMPT_SECONDS)
HARD_SECONDS = SOFT_SECONDS + 3.0
FINAL_REAP_SECONDS = HARD_SECONDS + 2.0
ABSOLUTE_SECONDS = FINAL_REAP_SECONDS + 1.0
ARTIFACT_BYTE_CAP = TOTAL_BODY_CAP + 2_000_000
PACKET_KEYS = {
    "schema_version",
    "status",
    "packet_contract_sha256",
    "execution_commit",
    "execution_tree",
    "repository_root",
    "wheel",
    "installed_member_manifest",
    "runtime_modules",
    "route_manifest",
    "route_manifest_sha256",
    "output_root",
    "launch_diagnostic_path",
    "outer_intent_path",
    "outer_invocation_path",
    "outer_invocation_fallback_path",
    "campaign_id",
    "campaign_attempt_id",
    "campaign_state",
    "command",
    "request_budget",
    "credential_interface",
    "network_scope",
    "one_attempt_rule",
    "nonclaims",
    "forbidden_actions",
}
RUNTIME_MODULE_NAMES = {
    "research_assistant.survey.discovery_capability",
    "research_assistant.survey.m20_live_supervisor",
    "research_assistant.survey.m20_live_worker",
    "research_assistant.survey.m20_recovery_launcher",
    "research_assistant.survey.openalex_adapter",
    "research_assistant.survey.openalex_credential_cost",
}
TOP_LEVEL_WORKER_FILES = {
    "accepted_body_inventory.json",
    "campaign_summary.json",
    "identity_outcomes.json",
    "replay_ledger.json",
    "request_ledger.json",
    "route_manifest.json",
}
CASE_DIRECTORIES = {
    "cases",
    "cases/topic",
    "cases/topic/accepted_bodies",
    "cases/arxiv_seed",
    "cases/arxiv_seed/accepted_bodies",
    "cases/openalex",
    "cases/openalex/accepted_bodies",
}


class M20SupervisorError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _is_git_object_id(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _loads_closed(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise M20SupervisorError("duplicate_json_key")
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(M20SupervisorError("nonfinite_json")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M20SupervisorError("invalid_json") from exc


def packet_contract_sha256(packet: dict[str, Any]) -> str:
    unsigned = dict(packet)
    unsigned.pop("packet_contract_sha256", None)
    return _sha(canonical_json_bytes(unsigned))


def _atomic_write(path: Path, raw: bytes) -> None:
    if (
        not path.parent.is_dir()
        or path.parent.is_symlink()
        or path.parent.resolve(strict=True) != path.parent
        or path.exists()
        or path.is_symlink()
    ):
        raise M20SupervisorError("publication_path_invalid")
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def _preflight_absent_root(root: Path) -> None:
    if not root.is_absolute() or root.exists() or root.is_symlink():
        raise M20SupervisorError("output_root_not_fresh")
    if not root.parent.is_dir() or root.parent.is_symlink() or root.parent.resolve(strict=True) != root.parent:
        raise M20SupervisorError("output_parent_invalid")


def _validate_launch_diagnostic_path(path: Path) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise M20SupervisorError("launch_diagnostic_path_not_fresh")
    if not path.parent.is_dir() or path.parent.is_symlink() or path.parent.resolve(strict=True) != path.parent:
        raise M20SupervisorError("launch_diagnostic_parent_invalid")


def _validate_fresh_record_path(path: Path, *, code: str) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise M20SupervisorError(code)
    if not path.parent.is_dir() or path.parent.is_symlink() or path.parent.resolve(strict=True) != path.parent:
        raise M20SupervisorError(code)


def _validate_outer_intent(path: Path, *, packet_path: Path, expected_command: list[str]) -> None:
    try:
        value = _loads_closed(path.read_bytes())
    except (OSError, M20SupervisorError) as exc:
        raise M20SupervisorError("packet_outer_intent_invalid") from exc
    if (
        not path.is_absolute()
        or not path.is_file()
        or path.is_symlink()
        or not isinstance(value, dict)
        or set(value) != {
            "schema_version",
            "packet_file_sha256",
            "child_command",
            "credential_read_or_enumerated_by_launcher",
            "provider_activity",
            "cost_usd",
            "privacy_state",
        }
        or value["schema_version"] != OUTER_INTENT_SCHEMA
        or value["packet_file_sha256"] != _sha_path(packet_path)
        or value["child_command"] != expected_command
        or value["credential_read_or_enumerated_by_launcher"] is not False
        or value["provider_activity"] is not False
        or value["cost_usd"] != "0.00"
        or value["privacy_state"] != "passed_closed_construction_before_child"
        or not path.parent.is_dir()
        or path.parent.is_symlink()
        or path.parent.resolve(strict=True) != path.parent
    ):
        raise M20SupervisorError("packet_outer_intent_invalid")


def _validate_campaign_state(path: Path, *, packet: dict[str, Any]) -> None:
    try:
        state = _loads_closed(path.read_bytes())
        cap = Decimal(state["cost_cap_usd"])
        reconciled = Decimal(state["reconciled_cost_usd"])
        remaining = Decimal(state["remaining_cost_usd"])
    except (OSError, KeyError, TypeError, InvalidOperation, M20SupervisorError) as exc:
        raise M20SupervisorError("packet_campaign_state_invalid") from exc
    completed = state.get("attempts_completed")
    predecessor = state.get("predecessor_campaign_state_sha256")
    if (
        not isinstance(state, dict)
        or set(state) != {
            "schema_version", "campaign_id", "attempts_completed",
            "provider_launches_used", "cost_cap_usd", "reconciled_cost_usd",
            "remaining_cost_usd", "next_attempt_id", "next_attempt_allowed",
            "continuation_veto", "predecessor_campaign_state_sha256",
        }
        or state["schema_version"] != "ra-literature-survey-m20-recovery-campaign-state-v1"
        or state["campaign_id"] != packet["campaign_id"]
        or state["next_attempt_id"] != packet["campaign_attempt_id"]
        or type(completed) is not int
        or type(state["provider_launches_used"]) is not int
        or state["provider_launches_used"] != completed
        or completed not in {0, 1}
        or state["next_attempt_id"] != f"attempt-{completed + 1:02d}"
        or state["next_attempt_allowed"] is not True
        or state["continuation_veto"] is not False
        or (completed == 0 and predecessor is not None)
        or (completed == 1 and not _is_sha256(predecessor))
        or not cap.is_finite()
        or not reconciled.is_finite()
        or not remaining.is_finite()
        or cap != CAMPAIGN_COST_CAP_USD
        or min(reconciled, remaining) < 0
        or reconciled + remaining != cap
    ):
        raise M20SupervisorError("packet_campaign_state_invalid")
def _validate_existing_root(root: Path) -> None:
    if not root.is_absolute() or not root.is_dir() or root.is_symlink() or root.resolve(strict=True) != root:
        raise M20SupervisorError("output_root_invalid")


def _git_identity(repository_root: Path) -> tuple[str, str]:
    def read(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["/usr/bin/git", "-c", "core.fsmonitor=false", *args],
                cwd=repository_root,
                env={"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"},
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise M20SupervisorError("git_identity_unavailable") from exc
        return completed.stdout.strip()

    return read("rev-parse", "HEAD"), read("rev-parse", "HEAD^{tree}")


def _validate_installed_members(
    manifest_path: Path,
    *,
    wheel_path: Path,
    wheel_sha256: str,
) -> dict[str, str]:
    manifest = _loads_closed(manifest_path.read_bytes())
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "status", "wheel_sha256", "install_root", "members",
    }:
        raise M20SupervisorError("installed_member_manifest_invalid")
    if (
        manifest["schema_version"] != "ra-literature-survey-m20b3-installed-member-manifest-v1"
        or manifest["status"] != "passed"
        or manifest["wheel_sha256"] != wheel_sha256
    ):
        raise M20SupervisorError("installed_member_manifest_invalid")
    install_root = Path(manifest["install_root"])
    if not install_root.is_absolute() or not install_root.is_dir() or install_root.is_symlink():
        raise M20SupervisorError("installed_member_root_invalid")
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            wheel_members = {
                info.filename: archive.read(info.filename)
                for info in archive.infolist()
                if not info.is_dir()
            }
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise M20SupervisorError("wheel_archive_invalid") from exc
    rows = manifest["members"]
    if not isinstance(rows, list) or len(rows) != len(wheel_members):
        raise M20SupervisorError("installed_member_manifest_invalid")
    installed: dict[str, str] = {}
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "wheel_path", "installed_path", "size_bytes", "sha256",
        }:
            raise M20SupervisorError("installed_member_manifest_invalid")
        wheel_member = row["wheel_path"]
        if (
            not isinstance(wheel_member, str)
            or not wheel_member
            or wheel_member.startswith("/")
            or ".." in Path(wheel_member).parts
            or wheel_member in seen
            or wheel_member not in wheel_members
        ):
            raise M20SupervisorError("installed_member_path_invalid")
        seen.add(wheel_member)
        installed_path = Path(row["installed_path"])
        expected_path = install_root / wheel_member
        if (
            not installed_path.is_absolute()
            or installed_path != expected_path
            or not installed_path.is_file()
            or installed_path.is_symlink()
        ):
            raise M20SupervisorError("installed_member_path_invalid")
        raw = installed_path.read_bytes()
        expected_raw = wheel_members[wheel_member]
        if (
            type(row["size_bytes"]) is not int
            or row["size_bytes"] != len(raw)
            or row["size_bytes"] != len(expected_raw)
            or not _is_sha256(row["sha256"])
            or row["sha256"] != _sha(raw)
            or raw != expected_raw
        ):
            raise M20SupervisorError("installed_member_bytes_invalid")
        installed[str(installed_path)] = row["sha256"]
    if seen != set(wheel_members):
        raise M20SupervisorError("installed_member_coverage_invalid")
    return installed


def _validate_runtime_modules(runtime_modules: Any, *, installed_members: dict[str, str]) -> None:
    if not isinstance(runtime_modules, dict) or set(runtime_modules) != RUNTIME_MODULE_NAMES:
        raise M20SupervisorError("runtime_modules_invalid")
    for module_name, expected in sorted(runtime_modules.items()):
        if not isinstance(module_name, str) or not isinstance(expected, dict) or set(expected) != {"origin", "sha256"}:
            raise M20SupervisorError("runtime_modules_invalid")
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            raise M20SupervisorError("runtime_module_missing")
        origin = Path(spec.origin).resolve(strict=True)
        if str(origin) != expected["origin"] or not _is_sha256(expected["sha256"]):
            raise M20SupervisorError("runtime_module_identity_invalid")
        if (
            _sha_path(origin) != expected["sha256"]
            or installed_members.get(str(origin)) != expected["sha256"]
        ):
            raise M20SupervisorError("runtime_module_bytes_invalid")


def validate_packet(
    packet: Any,
    *,
    packet_path: Path,
    output_root: Path,
    launch_diagnostic_path: Path,
    git_identity: Callable[[Path], tuple[str, str]] = _git_identity,
) -> dict[str, Any]:
    if not isinstance(packet, dict) or set(packet) != PACKET_KEYS:
        raise M20SupervisorError("packet_shape_invalid")
    fixed = {
        "schema_version": PACKET_SCHEMA,
        "status": "reviewed_m20_recovery_campaign_pending_external_authority",
        "credential_interface": CREDENTIAL_INTERFACE,
        "route_manifest_sha256": route_manifest_sha256(),
        "one_attempt_rule": "campaign_attempt_subject_to_plan_budget_and_repair_rules",
        "network_scope": ["api.openalex.org:443", "export.arxiv.org:443"],
    }
    if any(packet.get(key) != value for key, value in fixed.items()):
        raise M20SupervisorError("packet_fixed_contract_invalid")
    if not _is_sha256(packet["packet_contract_sha256"]) or packet_contract_sha256(packet) != packet["packet_contract_sha256"]:
        raise M20SupervisorError("packet_contract_hash_invalid")
    if packet["route_manifest"] != route_manifest():
        raise M20SupervisorError("packet_route_manifest_invalid")
    if not all(_is_git_object_id(packet[field]) for field in ("execution_commit", "execution_tree")):
        raise M20SupervisorError("packet_git_identity_invalid")
    repository_root = Path(packet["repository_root"])
    if not repository_root.is_absolute() or repository_root.resolve(strict=True) != repository_root:
        raise M20SupervisorError("packet_repository_root_invalid")
    if git_identity(repository_root) != (packet["execution_commit"], packet["execution_tree"]):
        raise M20SupervisorError("packet_git_identity_mismatch")
    for field in ("wheel", "installed_member_manifest"):
        value = packet[field]
        if not isinstance(value, dict) or set(value) != {"path", "sha256"} or not _is_sha256(value["sha256"]):
            raise M20SupervisorError("packet_file_identity_invalid")
        path = Path(value["path"])
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or _sha_path(path) != value["sha256"]:
            raise M20SupervisorError("packet_file_bytes_invalid")
    installed_members = _validate_installed_members(
        Path(packet["installed_member_manifest"]["path"]),
        wheel_path=Path(packet["wheel"]["path"]),
        wheel_sha256=packet["wheel"]["sha256"],
    )
    _validate_runtime_modules(packet["runtime_modules"], installed_members=installed_members)
    budget = packet["request_budget"]
    expected_budget = {
        "request_cap": REQUEST_CAP,
        "per_request_body_cap_bytes": PER_REQUEST_BODY_CAP,
        "total_body_cap_bytes": TOTAL_BODY_CAP,
        "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
        "whole_attempt_seconds": WHOLE_ATTEMPT_SECONDS,
        "campaign_cost_cap_usd": format(CAMPAIGN_COST_CAP_USD, "f"),
        "redirect_cap": 0,
        "retry_cap": 0,
        "proxy_policy": "disabled",
    }
    if budget != expected_budget:
        raise M20SupervisorError("packet_budget_invalid")
    if not isinstance(packet["nonclaims"], list) or not packet["nonclaims"]:
        raise M20SupervisorError("packet_nonclaims_invalid")
    if not isinstance(packet["forbidden_actions"], list) or not packet["forbidden_actions"]:
        raise M20SupervisorError("packet_forbidden_actions_invalid")
    if packet["output_root"] != str(output_root):
        raise M20SupervisorError("packet_output_root_invalid")
    if packet["launch_diagnostic_path"] != str(launch_diagnostic_path):
        raise M20SupervisorError("packet_launch_diagnostic_path_invalid")
    if (
        packet["campaign_id"] != "m20-recovery-2026-07-17"
        or packet["campaign_attempt_id"] not in {"attempt-01", "attempt-02"}
    ):
        raise M20SupervisorError("packet_campaign_identity_invalid")
    campaign_state = packet["campaign_state"]
    if (
        not isinstance(campaign_state, dict)
        or set(campaign_state) != {"path", "sha256"}
        or not _is_sha256(campaign_state.get("sha256"))
    ):
        raise M20SupervisorError("packet_campaign_state_invalid")
    campaign_state_path = Path(campaign_state["path"])
    if (
        not campaign_state_path.is_absolute()
        or not campaign_state_path.is_file()
        or campaign_state_path.is_symlink()
        or _sha_path(campaign_state_path) != campaign_state["sha256"]
    ):
        raise M20SupervisorError("packet_campaign_state_invalid")
    _validate_campaign_state(campaign_state_path, packet=packet)
    child_command = [
        sys.executable,
        "-I",
        "-m",
        "research_assistant.survey.m20_live_supervisor",
        "--packet",
        str(packet_path),
        "--output-root",
        str(output_root),
        "--launch-diagnostic-path",
        str(launch_diagnostic_path),
        "--execute-m20-recovery-campaign",
    ]
    expected_command = [
        sys.executable,
        "-I",
        "-m",
        "research_assistant.survey.m20_recovery_launcher",
        "--packet",
        str(packet_path),
        "--output-root",
        str(output_root),
        "--launch-diagnostic-path",
        str(launch_diagnostic_path),
        "--outer-intent-path",
        packet["outer_intent_path"],
        "--outer-invocation-path",
        packet["outer_invocation_path"],
        "--outer-invocation-fallback-path",
        packet["outer_invocation_fallback_path"],
        "--execute-m20-recovery-campaign",
    ]
    if packet["command"] != expected_command:
        raise M20SupervisorError("packet_command_invalid")
    _preflight_absent_root(output_root)
    _validate_launch_diagnostic_path(launch_diagnostic_path)
    intent_path = Path(packet["outer_intent_path"])
    outer_path = Path(packet["outer_invocation_path"])
    fallback_path = Path(packet["outer_invocation_fallback_path"])
    if len({intent_path, outer_path, fallback_path}) != 3:
        raise M20SupervisorError("packet_outer_invocation_paths_invalid")
    _validate_outer_intent(intent_path, packet_path=packet_path, expected_command=child_command)
    _validate_fresh_record_path(outer_path, code="packet_outer_invocation_path_invalid")
    _validate_fresh_record_path(fallback_path, code="packet_outer_invocation_fallback_path_invalid")
    return dict(packet)


def load_and_preflight_packet(
    packet_path: Path,
    *,
    output_root: Path,
    launch_diagnostic_path: Path,
    git_identity: Callable[[Path], tuple[str, str]] = _git_identity,
) -> dict[str, Any]:
    if not packet_path.is_absolute() or not packet_path.is_file() or packet_path.is_symlink():
        raise M20SupervisorError("packet_path_invalid")
    return validate_packet(
        _loads_closed(packet_path.read_bytes()),
        packet_path=packet_path,
        output_root=output_root,
        launch_diagnostic_path=launch_diagnostic_path,
        git_identity=git_identity,
    )


def _signal_worker(worker: Any, sig: signal.Signals, signals_sent: list[str]) -> None:
    try:
        os.killpg(worker.pid, sig)
        signals_sent.append(sig.name)
    except ProcessLookupError:
        return
    except OSError:
        try:
            worker.send_signal(sig)
            signals_sent.append(f"{sig.name}_PID_FALLBACK")
        except (OSError, ProcessLookupError):
            signals_sent.append(f"{sig.name}_FAILED")


def _remaining(clock: Callable[[], float], deadline: float) -> float:
    return max(0.001, deadline - clock())


def _artifact_inventory(root: Path, credential: str) -> list[dict[str, Any]]:
    _validate_existing_root(root)
    artifacts = []
    observed_directories: set[str] = set()
    total_bytes = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            observed_directories.add(relative)
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise M20SupervisorError("artifact_topology_invalid")
        allowed = relative in TOP_LEVEL_WORKER_FILES or (
            relative.startswith("cases/")
            and "/accepted_bodies/request-" in relative
            and relative.endswith(".body")
        )
        if not allowed:
            raise M20SupervisorError("artifact_path_unexpected")
        raw = path.read_bytes()
        total_bytes += len(raw)
        if contains_credential_representation(raw, credential):
            path.unlink()
            raise M20SupervisorError("credential_in_generated_artifact")
        if total_bytes > ARTIFACT_BYTE_CAP:
            raise M20SupervisorError("artifact_boundary_invalid")
        artifacts.append({"path": relative, "size_bytes": len(raw), "sha256": _sha(raw)})
    if observed_directories != CASE_DIRECTORIES:
        raise M20SupervisorError("artifact_directories_invalid")
    if not TOP_LEVEL_WORKER_FILES <= {row["path"] for row in artifacts}:
        raise M20SupervisorError("artifact_set_incomplete")
    return artifacts


def validate_worker_artifacts(root: Path, *, credential: str) -> list[dict[str, Any]]:
    artifacts = _artifact_inventory(root, credential)
    validate_published_run(root, execution_mode="live")
    values = {
        name: _loads_closed((root / name).read_bytes())
        for name in TOP_LEVEL_WORKER_FILES
    }
    if values["route_manifest.json"] != route_manifest():
        raise M20SupervisorError("worker_route_manifest_invalid")
    ledger = values["request_ledger.json"]
    summary = values["campaign_summary.json"]
    expected_routes = route_manifest()["routes"]
    if (
        not isinstance(ledger, dict)
        or ledger.get("execution_mode") != "live"
        or ledger.get("network_used") is not True
        or not isinstance(ledger.get("rows"), list)
        or len(ledger["rows"]) != REQUEST_CAP
        or [row.get("request_index") for row in ledger["rows"]] != list(range(1, REQUEST_CAP + 1))
        or any(
            row.get("request_binding_sha256") != route["request_binding_sha256"]
            or row.get("provider") != route["descriptor"]["provider"]
            or row.get("route_kind") != route["descriptor"]["route_kind"]
            for row, route in zip(ledger["rows"], expected_routes)
        )
    ):
        raise M20SupervisorError("worker_ledger_invalid")
    if (
        not isinstance(summary, dict)
        or summary.get("status") != "live_complete"
        or summary.get("execution_mode") != "live"
        or summary.get("network_used") is not True
        or summary.get("route_manifest_sha256") != route_manifest_sha256()
        or summary.get("request_ledger_sha256") != _sha(canonical_json_bytes(ledger))
        or summary.get("campaign_validity") not in {"closed", "boundary_invalid"}
        or summary.get("network_used") is not ledger.get("network_used")
        or summary.get("real_credential_accessed") is not ledger.get("real_credential_accessed")
    ):
        raise M20SupervisorError("worker_summary_invalid")
    digest_bindings = {
        "accepted_body_inventory_sha256": "accepted_body_inventory.json",
        "replay_ledger_sha256": "replay_ledger.json",
        "identity_outcomes_sha256": "identity_outcomes.json",
    }
    if any(summary.get(field) != _sha(canonical_json_bytes(values[name])) for field, name in digest_bindings.items()):
        raise M20SupervisorError("worker_evidence_binding_invalid")
    cost = summary.get("cost_evidence")
    try:
        cap = Decimal(cost["campaign_cost_cap_usd"])
        reserved = Decimal(cost["reserved_cost_usd"])
        reconciled = Decimal(cost["reconciled_cost_usd"])
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise M20SupervisorError("worker_cost_evidence_invalid") from exc
    if (
        cap != CAMPAIGN_COST_CAP_USD
        or min(reserved, reconciled) < 0
        or reconciled > reserved
        or reserved > cap
        or (cost.get("cost_state") == "open" and reserved != reconciled)
        or cost.get("cost_state") not in {"open", "blocked"}
    ):
        raise M20SupervisorError("worker_cost_evidence_invalid")
    return artifacts


def _scrub_partial_root(root: Path) -> None:
    _validate_existing_root(root)
    for path in list(root.iterdir()):
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            raise M20SupervisorError("partial_artifact_topology_invalid")


def _supervisor_record(
    *,
    packet: dict[str, Any],
    classification: str,
    lifecycle_stage: str,
    returncode: int | None,
    worker_reaped: bool | None,
    signals_sent: list[str],
    elapsed_seconds: float,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SUPERVISOR_SCHEMA,
        "classification": classification,
        "lifecycle_stage": lifecycle_stage,
        "packet_contract_sha256": packet["packet_contract_sha256"],
        "execution_commit": packet["execution_commit"],
        "route_manifest_sha256": packet["route_manifest_sha256"],
        "worker_returncode": returncode,
        "worker_reaped": worker_reaped,
        "signals_sent": signals_sent,
        "elapsed_seconds": round(elapsed_seconds, 6),
        "soft_seconds": SOFT_SECONDS,
        "hard_seconds": HARD_SECONDS,
        "final_reap_seconds": FINAL_REAP_SECONDS,
        "absolute_seconds": ABSOLUTE_SECONDS,
        "stdout_policy": "discarded_to_devnull",
        "stderr_policy": "discarded_to_devnull",
        "artifact_inventory": artifacts,
        "manifest_published_last": True,
    }


def run_supervised(
    packet: dict[str, Any],
    *,
    credential: str,
    popen_factory: Any = subprocess.Popen,
    clock: Callable[[], float] = time.monotonic,
) -> int:
    if not isinstance(credential, str) or not credential:
        raise M20SupervisorError("credential_unavailable")
    output_root = Path(packet["output_root"])
    _preflight_absent_root(output_root)
    command = [
        sys.executable,
        "-I",
        "-m",
        "research_assistant.survey.m20_live_worker",
        "--output-root",
        str(output_root),
    ]
    started = clock()
    worker = None
    signals_sent: list[str] = []
    classification = "worker_start_failed"
    lifecycle_stage = "worker_spawn"
    artifacts: list[dict[str, Any]] = []
    soft_deadline = started + SOFT_SECONDS
    hard_deadline = started + HARD_SECONDS
    final_reap_deadline = started + FINAL_REAP_SECONDS
    absolute_deadline = started + ABSOLUTE_SECONDS
    try:
        try:
            worker = popen_factory(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env={
                    CREDENTIAL_INTERFACE: credential,
                    "CUDA_VISIBLE_DEVICES": "-1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            lifecycle_stage = "initial_wait"
            worker.communicate(timeout=_remaining(clock, soft_deadline))
            classification = "completed" if worker.returncode == 0 else "worker_failed"
        except subprocess.TimeoutExpired:
            classification = "soft_timeout"
            if worker is not None:
                _signal_worker(worker, signal.SIGTERM, signals_sent)
                try:
                    lifecycle_stage = "post_term_wait"
                    worker.communicate(timeout=_remaining(clock, hard_deadline))
                except subprocess.TimeoutExpired:
                    classification = "hard_timeout"
                    _signal_worker(worker, signal.SIGKILL, signals_sent)
                    try:
                        lifecycle_stage = "post_kill_wait"
                        worker.communicate(timeout=_remaining(clock, final_reap_deadline))
                    except subprocess.TimeoutExpired:
                        classification = "final_reap_timeout"
                        lifecycle_stage = "final_reap_timeout"
                    except (OSError, ValueError, subprocess.SubprocessError):
                        classification = "supervisor_lifecycle_error"
                except (OSError, ValueError, subprocess.SubprocessError):
                    classification = "supervisor_lifecycle_error"
        except (OSError, ValueError, subprocess.SubprocessError):
            classification = "worker_start_failed" if worker is None else "supervisor_lifecycle_error"
    finally:
        if worker is not None and worker.returncode is None:
            _signal_worker(worker, signal.SIGKILL, signals_sent)
            try:
                prior_stage = lifecycle_stage
                lifecycle_stage = f"cleanup_wait_after_{prior_stage}"
                worker.wait(timeout=_remaining(clock, absolute_deadline))
            except (OSError, ValueError, subprocess.SubprocessError):
                classification = "cleanup_reap_indeterminate"
            else:
                if classification == "supervisor_lifecycle_error":
                    lifecycle_stage = prior_stage
        worker_reaped = worker is not None and worker.returncode is not None
        if worker is not None and not worker_reaped:
            classification = "cleanup_reap_indeterminate"
        if classification == "completed":
            try:
                lifecycle_stage = "artifact_validation"
                artifacts = validate_worker_artifacts(output_root, credential=credential)
            except (OSError, M20SupervisorError, M20WorkerError):
                classification = "worker_artifact_invalid"
        if not output_root.exists():
            output_root.mkdir(mode=0o700)
        _validate_existing_root(output_root)
        if classification != "completed":
            _scrub_partial_root(output_root)
        elapsed = max(0.0, clock() - started)
        record = _supervisor_record(
            packet=packet,
            classification=classification,
            lifecycle_stage=lifecycle_stage,
            returncode=worker.returncode if worker is not None else None,
            worker_reaped=worker_reaped if worker is not None else None,
            signals_sent=signals_sent,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
        )
        _atomic_write(output_root / "supervisor_manifest.json", pretty_json_bytes(record))
    return 0 if classification == "completed" else 2


def _environment_credential() -> str | None:
    return os.environ.get(CREDENTIAL_INTERFACE)


def _publish_launch_diagnostic(
    path: Path,
    *,
    outcome: str,
    exit_code: int,
    packet: dict[str, Any] | None = None,
    error_code: str | None = None,
    credential_lookup_performed: bool,
    credential_available: bool | None,
    supervised_execution_started: bool,
    output_root: Path,
) -> None:
    _validate_launch_diagnostic_path(path)
    manifest_path = output_root / "supervisor_manifest.json"
    record = {
        "schema_version": LAUNCH_DIAGNOSTIC_SCHEMA,
        "outcome": outcome,
        "exit_code": exit_code,
        "error_code": error_code,
        "packet_contract_sha256": (
            packet["packet_contract_sha256"] if packet is not None else "not_established"
        ),
        "preflight_completed": packet is not None,
        "credential_lookup_performed": credential_lookup_performed,
        "credential_available": credential_available,
        "supervised_execution_started": supervised_execution_started,
        "live_root_exists": output_root.exists(),
        "supervisor_manifest_exists": manifest_path.is_file() and not manifest_path.is_symlink(),
        "provider_activity": "not_established" if supervised_execution_started else False,
        "cost_usd": "not_established" if supervised_execution_started else "0.00",
        "privacy_state": "not_established",
    }
    _atomic_write(path, pretty_json_bytes(record))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--launch-diagnostic-path", type=Path, required=True)
    parser.add_argument("--execute-m20-recovery-campaign", action="store_true")
    args = parser.parse_args(argv)
    packet_path = args.packet.resolve(strict=False)
    output_root = args.output_root.resolve(strict=False)
    diagnostic_path = args.launch_diagnostic_path.resolve(strict=False)
    packet = None
    if not args.execute_m20_recovery_campaign:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="execution_flag_missing",
            exit_code=2,
            error_code="execution_flag_missing",
            credential_lookup_performed=False,
            credential_available=None,
            supervised_execution_started=False,
            output_root=output_root,
        )
        return 2
    try:
        packet = load_and_preflight_packet(
            packet_path,
            output_root=output_root,
            launch_diagnostic_path=diagnostic_path,
        )
    except M20SupervisorError as exc:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="preflight_failed",
            exit_code=2,
            error_code=exc.code,
            credential_lookup_performed=False,
            credential_available=None,
            supervised_execution_started=False,
            output_root=output_root,
        )
        return 2
    except OSError:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="preflight_failed",
            exit_code=2,
            error_code="preflight_os_error",
            credential_lookup_performed=False,
            credential_available=None,
            supervised_execution_started=False,
            output_root=output_root,
        )
        return 2
    except Exception:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="preflight_failed",
            exit_code=2,
            error_code="preflight_unexpected_error",
            credential_lookup_performed=False,
            credential_available=None,
            supervised_execution_started=False,
            output_root=output_root,
        )
        return 2
    try:
        credential = _environment_credential()
    except Exception:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="credential_lookup_failed",
            exit_code=2,
            packet=packet,
            error_code="credential_lookup_failed",
            credential_lookup_performed=True,
            credential_available=None,
            supervised_execution_started=False,
            output_root=output_root,
        )
        return 2
    if credential is None:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="credential_unavailable",
            exit_code=2,
            packet=packet,
            error_code="credential_unavailable",
            credential_lookup_performed=True,
            credential_available=False,
            supervised_execution_started=False,
            output_root=output_root,
        )
        return 2
    try:
        exit_code = run_supervised(packet, credential=credential)
    except Exception:
        _publish_launch_diagnostic(
            diagnostic_path,
            outcome="supervisor_error",
            exit_code=2,
            packet=packet,
            error_code="supervisor_error",
            credential_lookup_performed=True,
            credential_available=True,
            supervised_execution_started=True,
            output_root=output_root,
        )
        return 2
    _publish_launch_diagnostic(
        diagnostic_path,
        outcome="supervised_execution_returned",
        exit_code=exit_code,
        packet=packet,
        credential_lookup_performed=True,
        credential_available=True,
        supervised_execution_started=True,
        output_root=output_root,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "M20SupervisorError",
    "load_and_preflight_packet",
    "packet_contract_sha256",
    "run_supervised",
    "validate_packet",
    "validate_worker_artifacts",
]
