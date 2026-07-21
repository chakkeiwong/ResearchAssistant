from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import socket
import stat
import tempfile
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from research_assistant.core_utils import (
    canonical_json_bytes as _canonical_json_bytes,
    sha256_bytes as _sha256_bytes,
    sha256_file as _sha256_file,
)


MISSION_CONTRACT_SCHEMA = "ra-survey-public-source-mission-contract-v2"
MISSION_FINGERPRINT_SCHEMA = "ra-survey-public-source-mission-fingerprint-v2"
MISSION_CONTROL_SCHEMA = "ra-survey-public-source-mission-control-v2"
GENESIS_SCHEMA = "ra-survey-public-source-genesis-anchor-v1"
TOPIC_MISSION_CONTRACT_SCHEMA = "ra-survey-public-source-mission-contract-v3"
TOPIC_MISSION_FINGERPRINT_SCHEMA = "ra-survey-public-source-mission-fingerprint-v3"
TOPIC_MISSION_CONTROL_SCHEMA = "ra-survey-public-source-mission-control-v3"
TOPIC_GENESIS_SCHEMA = "ra-survey-public-source-genesis-anchor-v2"
TOPIC_BOOTSTRAP_AUTHORITY_SCHEMA = "ra-survey-topic-bootstrap-authority-v1"
GENERATION_IDENTITY_SCHEMA = "ra-survey-public-source-generation-identity-v1"
GENERATION_MANIFEST_SCHEMA = "ra-survey-public-source-generation-manifest-v1"
TRANSACTION_SCHEMA = "ra-survey-public-source-generation-transaction-v1"
CURRENT_SCHEMA = "ra-survey-public-source-current-pointer-v1"
LOCK_SCHEMA = "ra-survey-public-source-mission-lock-v1"
MIGRATION_IDENTITY_SCHEMA = "ra-survey-public-source-v1-migration-identity-v1"
LEGACY_MISSION_SCHEMA = "ra-survey-public-source-mission-control-v1"

EXPLICIT_SEED_INPUT_MODE = "explicit_seed"
TOPIC_INPUT_MODE = "idea_or_topic_without_initial_paper_seed"
TOPIC_BOOTSTRAP_STATES = {
    "confirmation_required",
    "not_started",
    "intent",
    "call_started_indeterminate",
    "result_recorded",
    "prepared",
    "selected_complete",
}
TOPIC_BOOTSTRAP_OUTCOMES = {"selected", "empty", "ambiguous", "unavailable", "capped"}

MIGRATION_NAMESPACE = uuid.UUID("e1fda32d-7a7f-5cd0-880d-4a92c6b12f51")
LOCK_STALE_SECONDS = 300
DEFAULT_PROVIDERS = ("arxiv",)
DEFAULT_ALLOWED_DOMAINS = ("arxiv.org", "export.arxiv.org")
MAX_METADATA_RECORDS = 25
MAX_SOURCE_RECORDS = 5
MAX_BYTES_PER_SOURCE = 52_428_800

GENERATION_ID_RE = re.compile(r"^g[0-9]{8}-[0-9a-f]{16}$")
ATOMIC_TEMP_RE = re.compile(
    r"^\.(?:GENESIS|CURRENT|mission_control\.json|next_action\.json|"
    r"g[0-9]{8}-[0-9a-f]{16}\.json)\.[A-Za-z0-9_-]+\.tmp$"
)


class MissionStateError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return _canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise MissionStateError("invalid_canonical_json", str(exc)) from exc


def pretty_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise MissionStateError("invalid_pretty_json", str(exc)) from exc
    return (text + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return _sha256_bytes(value)


def sha256_file(path: Path) -> str:
    return _sha256_file(path)


def normalize_text(value: str, *, field: str) -> dict[str, str]:
    if not isinstance(value, str):
        raise MissionStateError("invalid_normalized_text", f"{field} must be a string")
    display = " ".join(unicodedata.normalize("NFKC", value).split())
    if not display:
        raise MissionStateError("invalid_normalized_text", f"{field} must not be empty")
    return {"display": display, "key": display.casefold()}


def normalize_seeds(values: list[str]) -> list[dict[str, str]]:
    if not isinstance(values, list):
        raise MissionStateError("invalid_seeds", "seeds must be a list")
    by_key: dict[str, dict[str, str]] = {}
    for index, value in enumerate(values):
        normalized = normalize_text(value, field=f"seeds[{index}]")
        existing = by_key.get(normalized["key"])
        if existing and existing["display"] != normalized["display"]:
            # Equivalent representations are safe for a new request. Persisted
            # display conflicts are checked separately during resume.
            continue
        by_key.setdefault(normalized["key"], normalized)
    if not by_key:
        raise MissionStateError("invalid_seeds", "at least one nonempty seed is required")
    return [by_key[key] for key in sorted(by_key)]


def discovery_budget(output_dir: Path) -> dict[str, Any]:
    return {
        "providers": list(DEFAULT_PROVIDERS),
        "allowed_domains": list(DEFAULT_ALLOWED_DOMAINS),
        "max_metadata_records": MAX_METADATA_RECORDS,
        "max_source_records": MAX_SOURCE_RECORDS,
        "max_bytes_per_source": MAX_BYTES_PER_SOURCE,
        "write_root": str(output_dir.resolve()),
    }


def validate_budget(value: Any) -> dict[str, Any]:
    required = {
        "providers",
        "allowed_domains",
        "max_metadata_records",
        "max_source_records",
        "max_bytes_per_source",
        "write_root",
    }
    _require_exact_keys(value, required, "discovery_budget")
    providers = _validate_lowercase_list(value["providers"], "providers")
    domains = _validate_lowercase_list(value["allowed_domains"], "allowed_domains")
    numeric_caps = {
        "max_metadata_records": MAX_METADATA_RECORDS,
        "max_source_records": MAX_SOURCE_RECORDS,
        "max_bytes_per_source": MAX_BYTES_PER_SOURCE,
    }
    result: dict[str, Any] = {"providers": providers, "allowed_domains": domains}
    for field, hard_cap in numeric_caps.items():
        number = value[field]
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0 or number > hard_cap:
            raise MissionStateError("invalid_budget", f"{field} must be an integer in [1, {hard_cap}]")
        result[field] = number
    write_root = value["write_root"]
    if not isinstance(write_root, str) or not write_root:
        raise MissionStateError("invalid_budget", "write_root must be a nonempty string")
    result["write_root"] = str(Path(write_root).resolve())
    return result


def mission_fingerprint(
    normalized_topic: dict[str, str],
    normalized_seeds: list[dict[str, str]],
    budget: dict[str, Any],
) -> str:
    payload = {
        "schema_version": MISSION_FINGERPRINT_SCHEMA,
        "normalized_topic_key": normalized_topic["key"],
        "normalized_seed_keys": [row["key"] for row in normalized_seeds],
        "discovery_budget": budget,
    }
    return sha256_bytes(canonical_json_bytes(payload))


def topic_mission_fingerprint(
    normalized_topic: dict[str, str],
    budget: dict[str, Any],
) -> str:
    payload = {
        "schema_version": TOPIC_MISSION_FINGERPRINT_SCHEMA,
        "input_mode": TOPIC_INPUT_MODE,
        "normalized_topic_key": normalized_topic["key"],
        "normalized_initial_seed_keys": [],
        "discovery_budget": budget,
    }
    return sha256_bytes(canonical_json_bytes(payload))


def mission_input_view(contract: dict[str, Any]) -> dict[str, Any]:
    schema = contract.get("schema_version") if isinstance(contract, dict) else None
    if schema == MISSION_CONTRACT_SCHEMA:
        topic = _validate_normalized(contract.get("normalized_topic"), "normalized_topic")
        seeds = _validate_normalized_seeds(contract.get("normalized_seeds"))
        return {
            "input_mode": EXPLICIT_SEED_INPUT_MODE,
            "normalized_topic": topic,
            "normalized_initial_seed_rows": seeds,
        }
    if schema == TOPIC_MISSION_CONTRACT_SCHEMA:
        topic = _validate_normalized(contract.get("normalized_topic"), "normalized_topic")
        if contract.get("input_mode") != TOPIC_INPUT_MODE:
            raise MissionStateError("invalid_input_mode", "topic mission contract has an invalid input mode")
        seeds = contract.get("normalized_initial_seeds")
        if seeds != []:
            raise MissionStateError("invalid_seeds", "topic mission contract must preserve an empty initial seed list")
        return {
            "input_mode": TOPIC_INPUT_MODE,
            "normalized_topic": topic,
            "normalized_initial_seed_rows": [],
        }
    raise MissionStateError("unsupported_mission_contract", "mission contract schema is unsupported")


def generation_identity(
    *,
    mission_id: str,
    fingerprint: str,
    generation: int,
    parent_generation_id: str | None,
    transaction_nonce: str,
) -> tuple[str, str]:
    payload = {
        "schema_version": GENERATION_IDENTITY_SCHEMA,
        "mission_id": mission_id,
        "mission_fingerprint": fingerprint,
        "generation": generation,
        "parent_generation_id": parent_generation_id,
        "transaction_nonce": transaction_nonce,
    }
    digest = sha256_bytes(canonical_json_bytes(payload))
    return f"g{generation:08d}-{digest[:16]}", digest


def migrated_mission_id(
    normalized_topic: dict[str, str],
    normalized_seeds: list[dict[str, str]],
    budget: dict[str, Any],
) -> str:
    payload = {
        "schema_version": MIGRATION_IDENTITY_SCHEMA,
        "normalized_topic_key": normalized_topic["key"],
        "normalized_seed_keys": [row["key"] for row in normalized_seeds],
        "discovery_budget": budget,
        "write_root": budget["write_root"],
    }
    return str(uuid.uuid5(MIGRATION_NAMESPACE, canonical_json_bytes(payload).decode("ascii")))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require_exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise MissionStateError("invalid_schema", f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise MissionStateError(
            "invalid_schema",
            f"{label} fields do not match the schema",
            details={"missing": sorted(expected - actual), "unknown": sorted(actual - expected)},
        )


def _validate_lowercase_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise MissionStateError("invalid_budget", f"{field} must be a nonempty list")
    if any(not isinstance(row, str) or not row or row != row.lower() for row in value):
        raise MissionStateError("invalid_budget", f"{field} must contain nonempty lowercase strings")
    if len(set(value)) != len(value) or value != sorted(value):
        raise MissionStateError("invalid_budget", f"{field} must be unique and sorted")
    return list(value)


def _validate_uuid(value: Any, *, version: int | None = None) -> str:
    if not isinstance(value, str):
        raise MissionStateError("invalid_mission_id", "mission_id must be a string")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise MissionStateError("invalid_mission_id", "mission_id must be a UUID") from exc
    if str(parsed) != value or (version is not None and parsed.version != version):
        raise MissionStateError("invalid_mission_id", "mission_id is not canonical or has the wrong version")
    return value


def _validate_utc_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MissionStateError("invalid_timestamp", f"{field} must be a nonempty UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissionStateError("invalid_timestamp", f"{field} is not RFC3339-compatible") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise MissionStateError("invalid_timestamp", f"{field} must include a UTC offset")
    return value


def _validate_hex(value: Any, length: int, field: str) -> str:
    if not isinstance(value, str) or len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise MissionStateError("invalid_schema", f"{field} must be {length} lowercase hex characters")
    return value


def _validate_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MissionStateError("invalid_schema", f"{field} must be a positive integer")
    return value


def _validate_generation_id(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or GENERATION_ID_RE.fullmatch(value) is None:
        raise MissionStateError("invalid_generation_id", f"{field} is not a canonical generation ID")
    return value


def _validate_migration(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    expected = {"source_schema", "source_file_sha256", "migrated_at", "authority_invented"}
    _require_exact_keys(value, expected, "migration")
    if value["source_schema"] != LEGACY_MISSION_SCHEMA:
        raise MissionStateError("invalid_migration", "migration source schema is unsupported")
    _validate_hex(value["source_file_sha256"], 64, "migration source_file_sha256")
    _validate_utc_timestamp(value["migrated_at"], "migration migrated_at")
    if value["authority_invented"] is not False:
        raise MissionStateError("invalid_migration", "migration must not invent authority")
    return dict(value)


def _validate_normalized(value: Any, field: str) -> dict[str, str]:
    _require_exact_keys(value, {"display", "key"}, field)
    expected = normalize_text(value["display"], field=f"{field}.display")
    if expected != value:
        raise MissionStateError("invalid_normalization", f"{field} is not canonically normalized")
    return dict(value)


def _validate_normalized_seeds(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise MissionStateError("invalid_seeds", "normalized_seeds must be a nonempty list")
    rows = [_validate_normalized(row, f"normalized_seeds[{index}]") for index, row in enumerate(value)]
    keys = [row["key"] for row in rows]
    if keys != sorted(set(keys)):
        raise MissionStateError("invalid_seeds", "normalized_seeds must be unique and key-sorted")
    return rows


def _validate_confirmation(value: Any) -> dict[str, Any]:
    _require_exact_keys(value, {"confirmed", "confirmed_at", "confirmation_source"}, "confirmation")
    if not isinstance(value["confirmed"], bool):
        raise MissionStateError("invalid_confirmation", "confirmed must be Boolean")
    if value["confirmed"]:
        if not isinstance(value["confirmed_at"], str) or not value["confirmed_at"]:
            raise MissionStateError("invalid_confirmation", "confirmed_at is required when confirmed")
        _validate_utc_timestamp(value["confirmed_at"], "confirmation confirmed_at")
        if value["confirmation_source"] not in {"cli", "explicit_v1_record"}:
            raise MissionStateError("invalid_confirmation", "confirmation_source is invalid")
    elif value["confirmed_at"] is not None or value["confirmation_source"] is not None:
        raise MissionStateError("invalid_confirmation", "unconfirmed state cannot have confirmation metadata")
    return dict(value)


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise MissionStateError("invalid_artifact_path", "relative_path must be a nonempty string")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise MissionStateError("invalid_artifact_path", f"unsafe relative path: {value}")
    return value


def _validate_artifact_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise MissionStateError("invalid_artifact_rows", "artifact rows must be objects")
    relative_paths = [row.get("relative_path") for row in value]
    if any(not isinstance(path, str) for path in relative_paths) or relative_paths != sorted(relative_paths):
        raise MissionStateError("invalid_artifact_rows", "artifact rows must be path-sorted")
    seen: set[str] = set()
    for row in value:
        _require_exact_keys(row, {"relative_path", "schema_version", "sha256", "size_bytes", "role"}, "artifact row")
        relative = _safe_relative_path(row["relative_path"])
        if relative in seen:
            raise MissionStateError("duplicate_artifact_path", f"duplicate artifact path: {relative}")
        seen.add(relative)
        if not isinstance(row["schema_version"], str) or not row["schema_version"]:
            raise MissionStateError("invalid_artifact_row", "artifact schema_version must be a nonempty string")
        if not isinstance(row["role"], str) or not row["role"]:
            raise MissionStateError("invalid_artifact_row", "artifact role must be a nonempty string")
        _validate_hex(row["sha256"], 64, "artifact sha256")
        if isinstance(row["size_bytes"], bool) or not isinstance(row["size_bytes"], int) or row["size_bytes"] < 0:
            raise MissionStateError("invalid_artifact_row", "artifact size_bytes must be a nonnegative integer")
    return [dict(row) for row in value]


def _regular_file_beneath(directory: Path, relative: str) -> Path:
    root = directory.resolve()
    candidate = directory
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        candidate = candidate / part
        try:
            mode = candidate.lstat().st_mode
        except OSError as exc:
            raise MissionStateError("invalid_artifact_file", f"artifact is missing or unsafe: {relative}") from exc
        if stat.S_ISLNK(mode):
            raise MissionStateError("invalid_artifact_file", f"artifact is missing or unsafe: {relative}")
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise MissionStateError("invalid_artifact_file", f"artifact parent is not a directory: {relative}")
        if index == len(parts) - 1 and not stat.S_ISREG(mode):
            raise MissionStateError("invalid_artifact_file", f"artifact is missing or unsafe: {relative}")
    try:
        candidate.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise MissionStateError("invalid_artifact_file", f"artifact escapes generation directory: {relative}") from exc
    return candidate


def _is_atomic_temp_name(value: str) -> bool:
    return ATOMIC_TEMP_RE.fullmatch(value) is not None


def _is_safe_atomic_temp(path: Path) -> bool:
    if not _is_atomic_temp_name(path.name):
        return False
    if not stat.S_ISREG(path.lstat().st_mode):
        raise MissionStateError("unsafe_atomic_temp", f"atomic temp path is not a regular file: {path}")
    return True


def _atomic_write_bytes(path: Path, value: bytes, *, crash_hook: Callable[[str], None] | None = None, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    completed = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            if crash_hook:
                crash_hook(f"{label}:after_temp_write")
            handle.flush()
            os.fsync(handle.fileno())
        if crash_hook:
            crash_hook(f"{label}:after_temp_fsync")
        os.replace(temporary, path)
        if crash_hook:
            crash_hook(f"{label}:after_replace")
        _fsync_directory(path.parent)
        if crash_hook:
            crash_hook(f"{label}:after_directory_fsync")
        completed = True
    finally:
        # Failure residue is deliberately retained for crash diagnosis. Readers
        # ignore only exact regular-file temp names in declared state locations.
        if completed and temporary.exists():
            temporary.unlink()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_json_exact(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
            raise MissionStateError("unsafe_json_path", f"{label} is not a regular file: {path}")
        raw = path.read_bytes()
    except MissionStateError:
        raise
    except OSError as exc:
        raise MissionStateError("mission_state_read_failed", f"cannot read {label}: {path}") from exc
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_json", f"invalid JSON in {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_schema", f"{label} must contain a JSON object")
    return payload, raw


class MissionLock:
    def __init__(
        self,
        mission_dir: Path,
        *,
        stale_seconds: int = LOCK_STALE_SECONDS,
        reclaim_observed_hook: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.mission_dir = mission_dir.resolve()
        self.path = self.mission_dir / ".mission.lock"
        self.reclaim_path = self.mission_dir / ".mission.lock.reclaim"
        self.stale_seconds = stale_seconds
        self.reclaim_observed_hook = reclaim_observed_hook
        self.owner_token = secrets.token_hex(16)
        self._held = False

    def acquire(self) -> None:
        self.mission_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._create_lock()
            return
        except FileExistsError:
            pass
        observed = self._read_lock()
        if not self._is_stale(observed):
            raise MissionStateError("mission_locked", "mission is locked by a live or unverifiable owner", details=observed)
        if self.reclaim_observed_hook:
            self.reclaim_observed_hook(dict(observed))
        try:
            reclaim_fd = os.open(
                self.reclaim_path,
                os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
        except OSError as exc:
            raise MissionStateError("mission_lock_reclaim_unsafe", "cannot safely open the reclaim mutex") from exc
        try:
            try:
                fcntl.flock(reclaim_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise MissionStateError("mission_lock_reclaim_busy", "another process is reclaiming the lock") from exc
            current = self._read_lock()
            if current.get("owner_token") != observed.get("owner_token") or not self._is_stale(current):
                raise MissionStateError("mission_locked", "mission lock changed while reclaiming", details=current)
            self.path.unlink()
            _fsync_directory(self.mission_dir)
            try:
                self._create_lock()
            except FileExistsError as exc:
                raise MissionStateError("mission_locked", "another process acquired the mission lock") from exc
        finally:
            try:
                fcntl.flock(reclaim_fd, fcntl.LOCK_UN)
            finally:
                os.close(reclaim_fd)

    def release(self) -> None:
        if not self._held:
            return
        current = self._read_lock()
        if current.get("owner_token") != self.owner_token:
            raise MissionStateError("mission_lock_not_owner", "cannot release a lock owned by another transaction")
        self.path.unlink()
        _fsync_directory(self.mission_dir)
        self._held = False

    def _create_lock(self) -> None:
        payload = {
            "schema_version": LOCK_SCHEMA,
            "owner_token": self.owner_token,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "acquired_at": _utc_now(),
            "acquired_epoch": time.time(),
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(self.path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(canonical_json_bytes(payload))
                handle.flush()
                os.fsync(handle.fileno())
            _fsync_directory(self.mission_dir)
        except Exception:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            raise
        self._held = True

    def _read_lock(self) -> dict[str, Any]:
        payload, raw = _read_json_exact(self.path, label="mission lock")
        expected = {"schema_version", "owner_token", "pid", "hostname", "acquired_at", "acquired_epoch"}
        _require_exact_keys(payload, expected, "mission lock")
        if payload["schema_version"] != LOCK_SCHEMA:
            raise MissionStateError("invalid_mission_lock", "unsupported mission lock schema")
        if canonical_json_bytes(payload) != raw:
            raise MissionStateError("invalid_mission_lock", "mission lock bytes are not canonical")
        _validate_hex(payload["owner_token"], 32, "mission lock owner_token")
        if isinstance(payload["pid"], bool) or not isinstance(payload["pid"], int) or payload["pid"] <= 0:
            raise MissionStateError("invalid_mission_lock", "mission lock PID must be a positive integer")
        if not isinstance(payload["hostname"], str) or not payload["hostname"]:
            raise MissionStateError("invalid_mission_lock", "mission lock hostname must be a nonempty string")
        _validate_utc_timestamp(payload["acquired_at"], "mission lock acquired_at")
        epoch = payload["acquired_epoch"]
        if isinstance(epoch, bool) or not isinstance(epoch, (int, float)) or not math.isfinite(epoch):
            raise MissionStateError("invalid_mission_lock", "mission lock epoch must be finite")
        return payload

    def _is_stale(self, payload: dict[str, Any]) -> bool:
        epoch = payload.get("acquired_epoch")
        pid = payload.get("pid")
        if isinstance(epoch, bool) or not isinstance(epoch, (int, float)):
            return False
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            return False
        if payload.get("hostname") != socket.gethostname() or time.time() - float(epoch) <= self.stale_seconds:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except (PermissionError, OSError):
            return False
        return False


@dataclass
class MissionSnapshot:
    contract: dict[str, Any]
    mission_control: dict[str, Any] | None
    next_action: dict[str, Any] | None
    current_pointer: dict[str, Any] | None
    recovery: dict[str, Any]


class MissionStateManager:
    def __init__(
        self,
        *,
        output_dir: Path,
        topic: str,
        seeds: list[str],
        confirm_public_discovery: bool,
        resume: bool,
        force: bool,
        input_mode: str = EXPLICIT_SEED_INPUT_MODE,
        now: Callable[[], str] = _utc_now,
        nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
        mission_id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
        crash_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.output_dir = output_dir.resolve()
        self.normalized_topic = normalize_text(topic, field="topic")
        if input_mode == EXPLICIT_SEED_INPUT_MODE:
            self.normalized_seeds = normalize_seeds(seeds)
        elif input_mode == TOPIC_INPUT_MODE:
            if seeds != []:
                raise MissionStateError("invalid_seeds", "topic input mode requires an exact empty initial seed list")
            self.normalized_seeds = []
        else:
            raise MissionStateError("invalid_input_mode", "mission input mode is unsupported")
        self.input_mode = input_mode
        self.budget = discovery_budget(self.output_dir)
        self.request_fingerprint = (
            mission_fingerprint(self.normalized_topic, self.normalized_seeds, self.budget)
            if input_mode == EXPLICIT_SEED_INPUT_MODE
            else topic_mission_fingerprint(self.normalized_topic, self.budget)
        )
        self.confirm_requested = bool(confirm_public_discovery)
        self.resume = resume
        self.force = force
        self.now = now
        self.nonce_factory = nonce_factory
        self.mission_id_factory = mission_id_factory
        self.crash_hook = crash_hook
        self.lock = MissionLock(self.output_dir)
        self.state_dir = self.output_dir / ".mission_state"
        self.generations_dir = self.state_dir / "generations"
        self.transactions_dir = self.state_dir / "transactions"
        self.genesis_path = self.state_dir / "GENESIS"
        self.current_path = self.state_dir / "CURRENT"
        self.snapshot: MissionSnapshot | None = None
        self.confirmation_transitioned = False

    def begin(self) -> MissionSnapshot:
        if self.force and self.resume:
            raise MissionStateError("force_resume_conflict", "--force and --resume cannot be combined")
        self.lock.acquire()
        try:
            snapshot = self._load_or_create_snapshot()
            self.snapshot = snapshot
            return snapshot
        except Exception:
            self.lock.release()
            raise

    def commit(self, mission_control: dict[str, Any], next_action: dict[str, Any]) -> MissionSnapshot:
        if self.snapshot is None:
            raise MissionStateError("mission_transaction_not_started", "begin() must be called before commit()")
        try:
            committed = self._commit_generation(mission_control, next_action)
            self.snapshot = committed
            return committed
        finally:
            self.lock.release()

    def checkpoint(self, mission_control: dict[str, Any], next_action: dict[str, Any]) -> MissionSnapshot:
        """Persist one generation while retaining this transaction's mission lock."""
        if self.snapshot is None:
            raise MissionStateError("mission_transaction_not_started", "begin() must be called before checkpoint")
        if not self.lock._held:
            raise MissionStateError("mission_lock_not_held", "checkpoint requires the active mission lock")
        committed = self._commit_generation(mission_control, next_action)
        self.snapshot = committed
        return committed

    def checkpoint_confirmation(self) -> MissionSnapshot:
        if self.snapshot is None:
            raise MissionStateError("mission_transaction_not_started", "begin() must be called before checkpoint")
        if not self.confirmation_transitioned:
            return self.snapshot
        confirmation = self.snapshot.contract["public_discovery_confirmation"]
        if self.snapshot.current_pointer is None:
            if self.input_mode == TOPIC_INPUT_MODE:
                mission_control = self._topic_checkpoint_mission_control()
            else:
                mission_control = {
                    "status": "ready_for_local_continuation",
                    "created_at": self.snapshot.contract["created_at"],
                    "updated_at": self.now(),
                    "topic": self.snapshot.contract["normalized_topic"]["display"],
                    "seeds": [row["display"] for row in self.snapshot.contract["normalized_seeds"]],
                    "output_dir": str(self.output_dir),
                }
            next_action: dict[str, Any] = {"schema_version": "ra-survey-public-source-next-action-v1"}
        else:
            mission_control = dict(self.snapshot.mission_control or {})
            next_action = dict(self.snapshot.next_action or {})
        public_confirmation = dict(mission_control.get("public_discovery_confirmation") or {})
        public_confirmation.update({
            "confirmed": True,
            "status": "confirmed",
            "confirmed_at": confirmation["confirmed_at"],
            "confirmation_source": confirmation["confirmation_source"],
        })
        mission_control["public_discovery_confirmation"] = public_confirmation
        if self.input_mode == TOPIC_INPUT_MODE:
            mission_control["bootstrap_attempt_state"] = "not_started"
            mission_control["bootstrap_outcome"] = None
            mission_control["bootstrap_authority"] = None
            mission_control["effective_seeds"] = []
        next_action.update({
            "schema_version": next_action.get("schema_version") or "ra-survey-public-source-next-action-v1",
            "status": "confirmation_recorded_pending_workflow_resume",
            "mission_status": "ready_for_local_continuation",
            "action_id": "resume_confirmed_public_discovery",
        })
        committed = self._commit_generation(mission_control, next_action)
        self.snapshot = committed
        self.confirmation_transitioned = False
        return committed

    def _topic_checkpoint_mission_control(self) -> dict[str, Any]:
        assert self.snapshot is not None
        contract = self.snapshot.contract
        return {
            "status": "ready_for_local_continuation",
            "created_at": contract["created_at"],
            "updated_at": self.now(),
            "topic": contract["normalized_topic"]["display"],
            "seeds": [],
            "input_mode": TOPIC_INPUT_MODE,
            "initial_seeds": [],
            "effective_seeds": [],
            "bootstrap_attempt_state": "not_started",
            "bootstrap_outcome": None,
            "bootstrap_authority": None,
            "output_dir": str(self.output_dir),
            "resume": self.resume,
            "phase_statuses": {},
            "reviewed_artifacts": {},
            "coverage_artifacts": {},
            "final_artifacts": {},
            "source_intake_metadata_authority": None,
            "public_discovery_confirmation": {},
            "actions": [],
            "next_gate": {},
            "next_action_path": str(self.output_dir / "next_action.json"),
            "next_action": {},
            "workflow_state": None,
            "artifact_state": None,
            "review_queue_path": None,
            "review_queue_counts": None,
            "review_queue_reused": None,
            "safe_next_commands": [],
            "forbidden_actions": [],
            "what_is_not_concluded": [],
            "local_supervisor": None,
        }

    def abort(self) -> None:
        self.lock.release()

    def assert_generation_ancestor(self, generation_id: str) -> None:
        if self.snapshot is None or self.snapshot.current_pointer is None:
            raise MissionStateError("missing_mission_generation", "a committed mission generation is required")
        _validate_generation_id(generation_id, "artifact anchor generation_id")
        genesis, raw = self._validate_genesis()
        transactions = self._validated_transactions(genesis, sha256_bytes(raw))
        cursor: str | None = self.snapshot.current_pointer["generation_id"]
        while cursor is not None:
            if cursor == generation_id:
                return
            transaction = transactions.get(cursor)
            if transaction is None:
                break
            cursor = transaction["payload"]["parent_generation_id"]
        raise MissionStateError("artifact_anchor_not_ancestor", "artifact-state anchor is not on active mission ancestry")

    def _load_or_create_snapshot(self) -> MissionSnapshot:
        self._validate_state_container_paths()
        current_exists = self.current_path.exists()
        genesis_exists = self.genesis_path.exists()
        legacy_path = self.output_dir / "mission_control.json"
        v2_paths = self._v2_child_paths()
        state_exists = current_exists or genesis_exists or legacy_path.exists() or bool(v2_paths)

        if state_exists and self.force:
            raise MissionStateError("force_existing_output", "--force cannot overwrite existing mission state")
        if state_exists and not self.resume:
            raise MissionStateError("mission_control_exists", "existing mission state requires --resume")
        if not state_exists and self.resume:
            raise MissionStateError("resume_missing_mission", "--resume requires existing mission state")

        if not state_exists:
            other_entries: list[str] = []
            for path in self.output_dir.iterdir():
                if path.name in {".mission.lock", ".mission.lock.reclaim"}:
                    continue
                if _is_safe_atomic_temp(path):
                    continue
                if path.name == ".mission_state" and not v2_paths:
                    continue
                other_entries.append(path.name)
            if other_entries:
                if self.force:
                    raise MissionStateError("force_existing_output", "--force cannot overwrite a nonempty mission directory")
                raise MissionStateError("mission_control_missing_in_nonempty_output", "nonempty output has no valid mission state")

        self._ensure_state_directories()

        if current_exists:
            if not genesis_exists:
                raise MissionStateError("missing_genesis_anchor", "CURRENT exists without GENESIS")
            return self._load_current_snapshot()

        if genesis_exists:
            genesis, genesis_raw = self._validate_genesis()
            self._assert_request_matches_genesis(genesis)
            recovery = self._validate_interrupted_genesis(genesis, sha256_bytes(genesis_raw))
            contract = self._contract_from_genesis(genesis, recovery=recovery)
            contract = self._merge_confirmation(contract)
            return MissionSnapshot(contract, None, None, None, recovery)

        if v2_paths:
            raise MissionStateError("partial_v2_without_genesis", "V2 state exists without GENESIS", details={"paths": v2_paths})

        if legacy_path.exists():
            return self._migrate_legacy(legacy_path)

        return self._create_new_snapshot()

    def _ensure_state_directories(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.generations_dir.mkdir(parents=True, exist_ok=True)
        self.transactions_dir.mkdir(parents=True, exist_ok=True)
        _fsync_directory(self.output_dir)

    def _validate_state_container_paths(self) -> None:
        for path in (self.state_dir, self.generations_dir, self.transactions_dir):
            if path.exists() or path.is_symlink():
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                    raise MissionStateError("unsafe_mission_state_container", f"unsafe state container: {path}")
        if self.state_dir.is_dir():
            for path in self.state_dir.iterdir():
                if _is_safe_atomic_temp(path):
                    continue
                if path.name in {"generations", "transactions", "bootstrap"}:
                    if stat.S_ISLNK(path.lstat().st_mode) or not path.is_dir():
                        raise MissionStateError("unsafe_mission_state_container", f"unsafe state container: {path}")
                    continue
                if path.name in {"GENESIS", "CURRENT"}:
                    if not stat.S_ISREG(path.lstat().st_mode):
                        raise MissionStateError("unsafe_json_path", f"unsafe mission state file: {path}")
                    continue
                raise MissionStateError("unexpected_mission_state_path", f"unexpected state-root path: {path.name}")

    def _create_new_snapshot(self) -> MissionSnapshot:
        mission_id = _validate_uuid(self.mission_id_factory(), version=4)
        created_at = self.now()
        confirmation = {
            "confirmed": self.confirm_requested,
            "confirmed_at": created_at if self.confirm_requested else None,
            "confirmation_source": "cli" if self.confirm_requested else None,
        }
        if self.input_mode == TOPIC_INPUT_MODE:
            genesis = {
                "schema_version": TOPIC_GENESIS_SCHEMA,
                "mission_id": mission_id,
                "mission_fingerprint": self.request_fingerprint,
                "input_mode": TOPIC_INPUT_MODE,
                "normalized_topic": self.normalized_topic,
                "normalized_initial_seeds": [],
                "discovery_budget": self.budget,
                "public_discovery_confirmation": confirmation,
                "created_at": created_at,
                "migration": None,
            }
            self.confirmation_transitioned = self.confirm_requested
        else:
            genesis = {
                "schema_version": GENESIS_SCHEMA,
                "mission_id": mission_id,
                "mission_fingerprint": self.request_fingerprint,
                "normalized_topic": self.normalized_topic,
                "normalized_seeds": self.normalized_seeds,
                "discovery_budget": self.budget,
                "public_discovery_confirmation": confirmation,
                "created_at": created_at,
                "migration": None,
            }
        _atomic_write_bytes(self.genesis_path, canonical_json_bytes(genesis), crash_hook=self.crash_hook, label="genesis")
        recovery = {"state": "brand_new", "orphans": [], "orphan_temp_files": self._orphan_temp_paths()}
        contract = self._contract_from_genesis(genesis, recovery=recovery)
        return MissionSnapshot(contract, None, None, None, recovery)

    def _migrate_legacy(self, path: Path) -> MissionSnapshot:
        if self.input_mode != EXPLICIT_SEED_INPUT_MODE:
            raise MissionStateError("legacy_identity_mismatch", "legacy missions cannot migrate to topic input mode")
        payload, raw = _read_json_exact(path, label="legacy mission")
        if payload.get("schema_version") != LEGACY_MISSION_SCHEMA:
            raise MissionStateError("unsupported_legacy_schema", "legacy mission schema is not supported")
        topic = normalize_text(payload.get("topic"), field="legacy topic")
        seeds = normalize_seeds(payload.get("seeds"))
        if topic["key"] != self.normalized_topic["key"] or [row["key"] for row in seeds] != [row["key"] for row in self.normalized_seeds]:
            raise MissionStateError("legacy_identity_mismatch", "legacy topic or seeds do not match the request")
        for field in ("discovery_budget", "providers", "allowed_domains", "max_metadata_records", "max_source_records", "max_bytes_per_source"):
            if field in payload:
                raise MissionStateError("ambiguous_legacy_scope", f"legacy {field} is not supported for authority-preserving migration")
        confirmation_payload = payload.get("public_discovery_confirmation")
        confirmed = False
        if confirmation_payload is not None:
            if not isinstance(confirmation_payload, dict) or not isinstance(confirmation_payload.get("confirmed"), bool):
                raise MissionStateError("ambiguous_legacy_confirmation", "legacy confirmation must contain a Boolean confirmed field")
            if set(confirmation_payload) != {"confirmed"}:
                raise MissionStateError(
                    "ambiguous_legacy_scope",
                    "legacy confirmation contains unsupported authority or scope fields",
                )
            confirmed = confirmation_payload["confirmed"]
        created_at = self.now()
        genesis = {
            "schema_version": GENESIS_SCHEMA,
            "mission_id": migrated_mission_id(self.normalized_topic, self.normalized_seeds, self.budget),
            "mission_fingerprint": self.request_fingerprint,
            "normalized_topic": self.normalized_topic,
            "normalized_seeds": self.normalized_seeds,
            "discovery_budget": self.budget,
            "public_discovery_confirmation": {
                "confirmed": confirmed,
                "confirmed_at": created_at if confirmed else None,
                "confirmation_source": "explicit_v1_record" if confirmed else None,
            },
            "created_at": created_at,
            "migration": {
                "source_schema": LEGACY_MISSION_SCHEMA,
                "source_file_sha256": sha256_bytes(raw),
                "migrated_at": created_at,
                "authority_invented": False,
            },
        }
        _atomic_write_bytes(self.genesis_path, canonical_json_bytes(genesis), crash_hook=self.crash_hook, label="genesis")
        contract = self._contract_from_genesis(genesis, recovery={"state": "supported_v1", "orphans": []})
        contract = self._merge_confirmation(contract)
        return MissionSnapshot(contract, payload, payload.get("next_action"), None, {"state": "supported_v1", "orphans": []})

    def _load_current_snapshot(self) -> MissionSnapshot:
        genesis, _ = self._validate_genesis()
        self._assert_request_matches_genesis(genesis)
        pointer, pointer_raw = _read_json_exact(self.current_path, label="CURRENT")
        _require_exact_keys(pointer, {"schema_version", "generation_id", "generation_manifest_sha256"}, "CURRENT")
        if pointer["schema_version"] != CURRENT_SCHEMA:
            raise MissionStateError("invalid_current_pointer", "unsupported CURRENT schema")
        if canonical_json_bytes(pointer) != pointer_raw:
            raise MissionStateError("noncanonical_current_pointer", "CURRENT bytes are not canonical")
        _validate_hex(pointer["generation_manifest_sha256"], 64, "generation_manifest_sha256")
        generation_dir = self._generation_dir(pointer["generation_id"])
        manifest, manifest_raw = _read_json_exact(generation_dir / "generation_manifest.json", label="generation manifest")
        if sha256_bytes(manifest_raw) != pointer["generation_manifest_sha256"]:
            raise MissionStateError("current_manifest_hash_mismatch", "CURRENT manifest digest does not match")
        self._validate_generation_manifest(
            manifest,
            generation_dir,
            expected_generation_id=pointer["generation_id"],
            expected_genesis_digest=sha256_file(self.genesis_path),
        )
        mission_control, _ = _read_json_exact(generation_dir / "mission_control.json", label="mission control")
        next_action, _ = _read_json_exact(generation_dir / "next_action.json", label="next action")
        contract = self._validate_contract(mission_control.get("mission_contract"))
        self._assert_request_matches_contract(contract)
        self._validate_contract_against_genesis(contract, genesis)
        self._validate_current_payload_bindings(mission_control, next_action, contract, pointer, manifest)
        contract = self._merge_confirmation(contract)
        recovery = self._validate_later_orphans(genesis, pointer)
        recovery["current_pointer_sha256"] = sha256_bytes(pointer_raw)
        self._repair_mirrors(mission_control, next_action)
        return MissionSnapshot(contract, mission_control, next_action, pointer, recovery)

    def _commit_generation(self, mission_control: dict[str, Any], next_action: dict[str, Any]) -> MissionSnapshot:
        prior = self.snapshot
        assert prior is not None
        prior_contract = prior.contract
        generation = int(prior_contract.get("generation") or 0) + 1 if prior.current_pointer else 1
        parent = prior_contract.get("lineage", {}).get("generation_id") if prior.current_pointer else None
        nonce = _validate_hex(self.nonce_factory(), 32, "transaction_nonce")
        generation_id, _ = generation_identity(
            mission_id=prior_contract["mission_id"],
            fingerprint=prior_contract["mission_fingerprint"],
            generation=generation,
            parent_generation_id=parent,
            transaction_nonce=nonce,
        )
        genesis_raw = self.genesis_path.read_bytes()
        genesis_digest = sha256_bytes(genesis_raw)
        transaction_base = {
            "schema_version": TRANSACTION_SCHEMA,
            "status": "intent",
            "generation_id": generation_id,
            "mission_id": prior_contract["mission_id"],
            "mission_fingerprint": prior_contract["mission_fingerprint"],
            "generation": generation,
            "parent_generation_id": parent,
            "transaction_nonce": nonce,
            "genesis_anchor_sha256": genesis_digest,
            "owner_token": self.lock.owner_token,
            "created_at": self.now(),
            "generation_manifest_sha256": None,
            "intent_sha256": None,
        }
        transaction_path = self.transactions_dir / f"{generation_id}.json"
        staging_dir = self.generations_dir / f".staging-{generation_id}"
        final_dir = self.generations_dir / generation_id
        if transaction_path.exists() or transaction_path.is_symlink() or staging_dir.exists() or final_dir.exists():
            raise MissionStateError("generation_collision", "generation path already exists")
        intent_bytes = canonical_json_bytes(transaction_base)
        intent_digest = sha256_bytes(intent_bytes)
        _atomic_write_bytes(transaction_path, intent_bytes, crash_hook=self.crash_hook, label="transaction_intent")

        staging_dir.mkdir(mode=0o700)
        if self.crash_hook:
            self.crash_hook("generation:after_staging_mkdir")
        _fsync_directory(self.generations_dir)
        if self.crash_hook:
            self.crash_hook("generation:after_staging_parent_fsync")

        contract = dict(prior_contract)
        contract["generation"] = generation
        contract["updated_at"] = self.now()
        contract["lineage"] = {
            "generation_id": generation_id,
            "transaction_nonce": nonce,
            "parent_generation_id": parent,
            "mission_contract_sha256": "",
            "artifacts": [],
        }
        contract_digest = self._contract_digest(contract)
        contract["lineage"]["mission_contract_sha256"] = contract_digest

        mission_schema = (
            TOPIC_MISSION_CONTROL_SCHEMA
            if prior_contract["schema_version"] == TOPIC_MISSION_CONTRACT_SCHEMA
            else MISSION_CONTROL_SCHEMA
        )
        mission_payload = dict(mission_control)
        mission_payload["schema_version"] = mission_schema
        mission_payload["mission_contract"] = contract
        mission_payload["mission_id"] = contract["mission_id"]
        mission_payload["mission_fingerprint"] = contract["mission_fingerprint"]
        mission_payload["generation_id"] = generation_id
        next_payload = dict(next_action)
        next_payload["mission_id"] = contract["mission_id"]
        next_payload["mission_fingerprint"] = contract["mission_fingerprint"]
        next_payload["generation_id"] = generation_id
        mission_payload["next_action"] = next_payload

        mission_bytes = pretty_json_bytes(mission_payload)
        next_bytes = pretty_json_bytes(next_payload)
        self._write_staging_file(staging_dir / "mission_control.json", mission_bytes, "mission_control")
        self._write_staging_file(staging_dir / "next_action.json", next_bytes, "next_action")
        artifact_rows = [
            self._artifact_row("mission_control.json", mission_schema, mission_bytes, "mission_control"),
            self._artifact_row("next_action.json", str(next_payload.get("schema_version") or "unknown"), next_bytes, "next_action"),
        ]

        manifest = {
            "schema_version": GENERATION_MANIFEST_SCHEMA,
            "generation_id": generation_id,
            "mission_id": contract["mission_id"],
            "mission_fingerprint": contract["mission_fingerprint"],
            "generation": generation,
            "parent_generation_id": parent,
            "transaction_nonce": nonce,
            "genesis_anchor_sha256": genesis_digest,
            "mission_contract_sha256": contract["lineage"]["mission_contract_sha256"],
            "artifacts": artifact_rows,
        }
        manifest_bytes = canonical_json_bytes(manifest)
        self._write_staging_file(staging_dir / "generation_manifest.json", manifest_bytes, "generation_manifest")
        _fsync_directory(staging_dir)
        if self.crash_hook:
            self.crash_hook("generation:after_staging_fsync")
        manifest_digest = sha256_bytes(manifest_bytes)
        prepared = dict(transaction_base)
        prepared["status"] = "prepared"
        prepared["generation_manifest_sha256"] = manifest_digest
        prepared["intent_sha256"] = intent_digest
        _atomic_write_bytes(transaction_path, canonical_json_bytes(prepared), crash_hook=self.crash_hook, label="transaction_prepared")

        os.rename(staging_dir, final_dir)
        if self.crash_hook:
            self.crash_hook("generation:after_final_rename")
        _fsync_directory(self.generations_dir)
        if self.crash_hook:
            self.crash_hook("generation:after_generations_fsync")
        pointer = {
            "schema_version": CURRENT_SCHEMA,
            "generation_id": generation_id,
            "generation_manifest_sha256": manifest_digest,
        }
        _atomic_write_bytes(self.current_path, canonical_json_bytes(pointer), crash_hook=self.crash_hook, label="current")
        committed = dict(prepared)
        committed["status"] = "committed"
        _atomic_write_bytes(transaction_path, canonical_json_bytes(committed), crash_hook=self.crash_hook, label="transaction_committed")
        _atomic_write_bytes(self.output_dir / "mission_control.json", mission_bytes, crash_hook=self.crash_hook, label="mission_mirror")
        _atomic_write_bytes(self.output_dir / "next_action.json", next_bytes, crash_hook=self.crash_hook, label="next_action_mirror")
        return MissionSnapshot(contract, mission_payload, next_payload, pointer, {"state": "committed", "orphans": prior.recovery.get("orphans", [])})

    def _write_staging_file(self, path: Path, value: bytes, label: str) -> None:
        with path.open("wb") as handle:
            handle.write(value)
            if self.crash_hook:
                self.crash_hook(f"generation:{label}:after_write")
            handle.flush()
            os.fsync(handle.fileno())
        if self.crash_hook:
            self.crash_hook(f"generation:{label}:after_fsync")

    def _artifact_row(self, path: str, schema: str, value: bytes, role: str) -> dict[str, Any]:
        return {
            "relative_path": _safe_relative_path(path),
            "schema_version": schema,
            "sha256": sha256_bytes(value),
            "size_bytes": len(value),
            "role": role,
        }

    def _contract_digest(self, contract: dict[str, Any]) -> str:
        value = dict(contract)
        value.pop("updated_at", None)
        value.pop("lineage", None)
        return sha256_bytes(canonical_json_bytes(value))

    def _contract_from_genesis(self, genesis: dict[str, Any], *, recovery: dict[str, Any]) -> dict[str, Any]:
        if genesis["schema_version"] == TOPIC_GENESIS_SCHEMA:
            return {
                "schema_version": TOPIC_MISSION_CONTRACT_SCHEMA,
                "mission_id": genesis["mission_id"],
                "mission_fingerprint": genesis["mission_fingerprint"],
                "input_mode": genesis["input_mode"],
                "generation": 0,
                "lineage": {
                    "generation_id": None,
                    "transaction_nonce": None,
                    "parent_generation_id": None,
                    "mission_contract_sha256": None,
                    "artifacts": [],
                },
                "normalized_topic": genesis["normalized_topic"],
                "normalized_initial_seeds": [],
                "discovery_budget": genesis["discovery_budget"],
                "public_discovery_confirmation": genesis["public_discovery_confirmation"],
                "created_at": genesis["created_at"],
                "updated_at": genesis["created_at"],
                "migration": None,
            }
        return {
            "schema_version": MISSION_CONTRACT_SCHEMA,
            "mission_id": genesis["mission_id"],
            "mission_fingerprint": genesis["mission_fingerprint"],
            "generation": 0,
            "lineage": {
                "generation_id": None,
                "transaction_nonce": None,
                "parent_generation_id": None,
                "mission_contract_sha256": None,
                "artifacts": [],
            },
            "normalized_topic": genesis["normalized_topic"],
            "normalized_seeds": genesis["normalized_seeds"],
            "discovery_budget": genesis["discovery_budget"],
            "public_discovery_confirmation": genesis["public_discovery_confirmation"],
            "created_at": genesis["created_at"],
            "updated_at": genesis["created_at"],
            "migration": genesis["migration"],
        }

    def _validate_contract(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict) and value.get("schema_version") == TOPIC_MISSION_CONTRACT_SCHEMA:
            return self._validate_topic_contract(value)
        expected = {
            "schema_version",
            "mission_id",
            "mission_fingerprint",
            "generation",
            "lineage",
            "normalized_topic",
            "normalized_seeds",
            "discovery_budget",
            "public_discovery_confirmation",
            "created_at",
            "updated_at",
            "migration",
        }
        _require_exact_keys(value, expected, "mission_contract")
        if value["schema_version"] != MISSION_CONTRACT_SCHEMA:
            raise MissionStateError("unsupported_mission_contract", "mission contract schema is unsupported")
        _validate_uuid(value["mission_id"])
        _validate_hex(value["mission_fingerprint"], 64, "mission_fingerprint")
        _validate_positive_int(value["generation"], "generation")
        topic = _validate_normalized(value["normalized_topic"], "normalized_topic")
        seeds = _validate_normalized_seeds(value["normalized_seeds"])
        budget = validate_budget(value["discovery_budget"])
        if mission_fingerprint(topic, seeds, budget) != value["mission_fingerprint"]:
            raise MissionStateError("mission_fingerprint_mismatch", "mission fingerprint does not match invariant inputs")
        _validate_confirmation(value["public_discovery_confirmation"])
        _validate_utc_timestamp(value["created_at"], "mission contract created_at")
        _validate_utc_timestamp(value["updated_at"], "mission contract updated_at")
        migration = _validate_migration(value["migration"])
        if migration is None:
            _validate_uuid(value["mission_id"], version=4)
        elif value["mission_id"] != migrated_mission_id(topic, seeds, budget):
            raise MissionStateError("migrated_mission_id_mismatch", "contract mission ID is not the deterministic UUIDv5")
        self._validate_contract_lineage(value["lineage"], value)
        return dict(value)

    def _validate_topic_contract(self, value: dict[str, Any]) -> dict[str, Any]:
        expected = {
            "schema_version",
            "mission_id",
            "mission_fingerprint",
            "input_mode",
            "generation",
            "lineage",
            "normalized_topic",
            "normalized_initial_seeds",
            "discovery_budget",
            "public_discovery_confirmation",
            "created_at",
            "updated_at",
            "migration",
        }
        _require_exact_keys(value, expected, "topic mission_contract")
        if value["input_mode"] != TOPIC_INPUT_MODE or value["normalized_initial_seeds"] != []:
            raise MissionStateError("invalid_input_mode", "topic mission contract input fields are invalid")
        _validate_uuid(value["mission_id"], version=4)
        _validate_hex(value["mission_fingerprint"], 64, "mission_fingerprint")
        _validate_positive_int(value["generation"], "generation")
        topic = _validate_normalized(value["normalized_topic"], "normalized_topic")
        budget = validate_budget(value["discovery_budget"])
        if topic_mission_fingerprint(topic, budget) != value["mission_fingerprint"]:
            raise MissionStateError("mission_fingerprint_mismatch", "topic mission fingerprint does not match invariant inputs")
        _validate_confirmation(value["public_discovery_confirmation"])
        _validate_utc_timestamp(value["created_at"], "mission contract created_at")
        _validate_utc_timestamp(value["updated_at"], "mission contract updated_at")
        if value["migration"] is not None:
            raise MissionStateError("invalid_migration", "topic mission contracts do not support migration")
        self._validate_contract_lineage(value["lineage"], value)
        return dict(value)

    def _validate_contract_lineage(self, value: Any, contract: dict[str, Any]) -> None:
        expected = {
            "generation_id",
            "transaction_nonce",
            "parent_generation_id",
            "mission_contract_sha256",
            "artifacts",
        }
        _require_exact_keys(value, expected, "mission contract lineage")
        _validate_generation_id(value["generation_id"], "lineage generation_id")
        _validate_generation_id(value["parent_generation_id"], "lineage parent_generation_id", nullable=True)
        expected_id, _ = generation_identity(
            mission_id=contract["mission_id"],
            fingerprint=contract["mission_fingerprint"],
            generation=contract["generation"],
            parent_generation_id=value["parent_generation_id"],
            transaction_nonce=_validate_hex(value["transaction_nonce"], 32, "transaction_nonce"),
        )
        if value["generation_id"] != expected_id:
            raise MissionStateError("contract_generation_identity_mismatch", "contract lineage generation ID is invalid")
        _validate_hex(value["mission_contract_sha256"], 64, "mission_contract_sha256")
        if value["mission_contract_sha256"] != self._contract_digest(contract):
            raise MissionStateError("contract_digest_mismatch", "mission contract digest is invalid")
        _validate_artifact_rows(value["artifacts"])

    def _validate_current_payload_bindings(
        self,
        mission_control: dict[str, Any],
        next_action: dict[str, Any],
        contract: dict[str, Any],
        pointer: dict[str, Any],
        manifest: dict[str, Any],
    ) -> None:
        generation_id = pointer["generation_id"]
        expected_mission_schema = (
            TOPIC_MISSION_CONTROL_SCHEMA
            if contract["schema_version"] == TOPIC_MISSION_CONTRACT_SCHEMA
            else MISSION_CONTROL_SCHEMA
        )
        if mission_control.get("schema_version") != expected_mission_schema:
            raise MissionStateError("invalid_mission_control_schema", "mission control schema is unsupported")
        mission_row = next(
            (row for row in manifest.get("artifacts", []) if row.get("relative_path") == "mission_control.json"),
            None,
        )
        if not isinstance(mission_row, dict) or mission_row.get("schema_version") != expected_mission_schema:
            raise MissionStateError("mission_control_artifact_schema_mismatch", "generation manifest records the wrong mission-control schema")
        if expected_mission_schema == TOPIC_MISSION_CONTROL_SCHEMA:
            self._validate_topic_mission_control(mission_control)
        for field, expected in {
            "mission_id": contract["mission_id"],
            "mission_fingerprint": contract["mission_fingerprint"],
            "generation_id": generation_id,
        }.items():
            if mission_control.get(field) != expected or next_action.get(field) != expected:
                raise MissionStateError("generation_payload_binding_mismatch", f"{field} is not bound to the current generation")
        if mission_control.get("next_action") != next_action:
            raise MissionStateError("next_action_mirror_mismatch", "embedded and standalone next-action payloads differ")
        if manifest["mission_id"] != contract["mission_id"] or manifest["mission_fingerprint"] != contract["mission_fingerprint"]:
            raise MissionStateError("manifest_mission_binding_mismatch", "manifest mission identity does not match contract")
        if manifest["mission_contract_sha256"] != contract["lineage"]["mission_contract_sha256"]:
            raise MissionStateError("manifest_contract_digest_mismatch", "manifest contract digest does not match contract")
        if manifest["generation"] != contract["generation"] or manifest["parent_generation_id"] != contract["lineage"]["parent_generation_id"]:
            raise MissionStateError("manifest_generation_binding_mismatch", "manifest generation lineage does not match contract")
        if manifest["transaction_nonce"] != contract["lineage"]["transaction_nonce"]:
            raise MissionStateError("manifest_nonce_mismatch", "manifest nonce does not match contract")

    def _validate_topic_mission_control(self, value: dict[str, Any]) -> None:
        expected = {
            "schema_version", "status", "created_at", "updated_at", "topic", "seeds",
            "input_mode", "initial_seeds", "effective_seeds", "bootstrap_attempt_state",
            "bootstrap_outcome", "bootstrap_authority", "output_dir", "resume",
            "phase_statuses", "reviewed_artifacts", "coverage_artifacts", "final_artifacts",
            "source_intake_metadata_authority", "public_discovery_confirmation", "actions",
            "next_gate", "next_action_path", "next_action", "workflow_state", "artifact_state",
            "review_queue_path", "review_queue_counts", "review_queue_reused", "safe_next_commands",
            "forbidden_actions", "what_is_not_concluded", "local_supervisor", "mission_contract",
            "mission_id", "mission_fingerprint", "generation_id",
        }
        _require_exact_keys(value, expected, "topic mission control")
        if value["schema_version"] != TOPIC_MISSION_CONTROL_SCHEMA or value["input_mode"] != TOPIC_INPUT_MODE:
            raise MissionStateError("invalid_mission_control_schema", "topic mission control schema or input mode is invalid")
        if value["seeds"] != [] or value["initial_seeds"] != []:
            raise MissionStateError("invalid_seeds", "topic mission control original seed lists must remain empty")
        for field in ("status", "topic", "output_dir", "next_action_path"):
            if not isinstance(value[field], str) or not value[field]:
                raise MissionStateError("invalid_mission_control_schema", f"topic mission control {field} must be nonempty")
        for field in (
            "phase_statuses", "reviewed_artifacts", "coverage_artifacts", "final_artifacts",
            "public_discovery_confirmation", "next_gate", "next_action",
        ):
            if not isinstance(value[field], dict):
                raise MissionStateError("invalid_mission_control_schema", f"topic mission control {field} must be an object")
        for field in ("actions", "safe_next_commands", "forbidden_actions", "what_is_not_concluded"):
            if not isinstance(value[field], list):
                raise MissionStateError("invalid_mission_control_schema", f"topic mission control {field} must be a list")
        if not isinstance(value["resume"], bool):
            raise MissionStateError("invalid_mission_control_schema", "topic mission control resume must be Boolean")
        state = value["bootstrap_attempt_state"]
        outcome = value["bootstrap_outcome"]
        authority = value["bootstrap_authority"]
        effective = value["effective_seeds"]
        if state not in TOPIC_BOOTSTRAP_STATES:
            raise MissionStateError("invalid_bootstrap_state", "topic mission control bootstrap state is invalid")
        if outcome is not None and outcome not in TOPIC_BOOTSTRAP_OUTCOMES:
            raise MissionStateError("invalid_bootstrap_outcome", "topic mission control bootstrap outcome is invalid")
        if not isinstance(effective, list) or any(not isinstance(row, str) or not row for row in effective):
            raise MissionStateError("invalid_effective_seeds", "effective_seeds must contain nonempty strings")
        authoritative_selected = state == "selected_complete" and outcome == "selected"
        if authoritative_selected:
            self._validate_bootstrap_authority(authority, effective)
        elif authority is not None or effective != []:
            raise MissionStateError("premature_bootstrap_authority", "bootstrap authority is exposed before selected completion")
        if state == "selected_complete" and outcome is None:
            raise MissionStateError("invalid_bootstrap_outcome", "selected_complete requires a closed outcome")
        if state in {"confirmation_required", "not_started", "intent", "call_started_indeterminate", "result_recorded"} and outcome is not None:
            raise MissionStateError("premature_bootstrap_outcome", "bootstrap outcome is exposed before preparation")
        if state == "prepared" and outcome is None:
            raise MissionStateError("invalid_bootstrap_outcome", "prepared bootstrap state requires a closed outcome")
        confirmation = value["public_discovery_confirmation"]
        confirmed = confirmation.get("confirmed")
        if not isinstance(confirmed, bool):
            raise MissionStateError("invalid_confirmation", "topic mission control confirmation must expose a Boolean confirmed field")
        if state == "confirmation_required" and confirmed:
            raise MissionStateError("invalid_confirmation_transition", "confirmation-required bootstrap state cannot be confirmed")
        if state != "confirmation_required" and not confirmed:
            raise MissionStateError("public_discovery_confirmation_required", "bootstrap state cannot advance before confirmation")

    def _validate_bootstrap_authority(self, value: Any, effective_seeds: list[str]) -> None:
        expected = {
            "schema_version", "set_id", "manifest_sha256", "request_id", "request_sha256",
            "capability_name", "capability_version", "confirmed_generation_id",
            "effective_normalized_seed_keys",
        }
        _require_exact_keys(value, expected, "bootstrap authority")
        if value["schema_version"] != TOPIC_BOOTSTRAP_AUTHORITY_SCHEMA:
            raise MissionStateError("invalid_bootstrap_authority", "bootstrap authority schema is invalid")
        for field in ("set_id", "request_id", "capability_name", "capability_version"):
            if not isinstance(value[field], str) or not value[field]:
                raise MissionStateError("invalid_bootstrap_authority", f"{field} must be nonempty")
        for field in ("manifest_sha256", "request_sha256"):
            _validate_hex(value[field], 64, field)
        _validate_generation_id(value["confirmed_generation_id"], "confirmed_generation_id")
        keys = value["effective_normalized_seed_keys"]
        normalized = normalize_seeds(effective_seeds)
        if keys != [row["key"] for row in normalized] or effective_seeds != [row["display"] for row in normalized]:
            raise MissionStateError("invalid_bootstrap_authority", "effective seeds do not match bootstrap authority")

    def _validate_genesis(self) -> tuple[dict[str, Any], bytes]:
        payload, raw = _read_json_exact(self.genesis_path, label="GENESIS")
        if payload.get("schema_version") == TOPIC_GENESIS_SCHEMA:
            return self._validate_topic_genesis(payload, raw)
        expected = {
            "schema_version",
            "mission_id",
            "mission_fingerprint",
            "normalized_topic",
            "normalized_seeds",
            "discovery_budget",
            "public_discovery_confirmation",
            "created_at",
            "migration",
        }
        _require_exact_keys(payload, expected, "GENESIS")
        if payload["schema_version"] != GENESIS_SCHEMA:
            raise MissionStateError("unsupported_genesis_schema", "GENESIS schema is unsupported")
        _validate_uuid(payload["mission_id"])
        topic = _validate_normalized(payload["normalized_topic"], "GENESIS.normalized_topic")
        seeds = _validate_normalized_seeds(payload["normalized_seeds"])
        budget = validate_budget(payload["discovery_budget"])
        if mission_fingerprint(topic, seeds, budget) != payload["mission_fingerprint"]:
            raise MissionStateError("genesis_fingerprint_mismatch", "GENESIS fingerprint does not match inputs")
        _validate_confirmation(payload["public_discovery_confirmation"])
        _validate_utc_timestamp(payload["created_at"], "GENESIS created_at")
        migration = _validate_migration(payload["migration"])
        if migration is None:
            _validate_uuid(payload["mission_id"], version=4)
        else:
            expected_migrated_id = migrated_mission_id(topic, seeds, budget)
            if payload["mission_id"] != expected_migrated_id:
                raise MissionStateError("migrated_mission_id_mismatch", "migrated mission ID is not the deterministic UUIDv5")
        if canonical_json_bytes(payload) != raw:
            raise MissionStateError("noncanonical_genesis", "GENESIS bytes are not canonical")
        return payload, raw

    def _validate_topic_genesis(self, payload: dict[str, Any], raw: bytes) -> tuple[dict[str, Any], bytes]:
        expected = {
            "schema_version",
            "mission_id",
            "mission_fingerprint",
            "input_mode",
            "normalized_topic",
            "normalized_initial_seeds",
            "discovery_budget",
            "public_discovery_confirmation",
            "created_at",
            "migration",
        }
        _require_exact_keys(payload, expected, "topic GENESIS")
        if payload["input_mode"] != TOPIC_INPUT_MODE or payload["normalized_initial_seeds"] != []:
            raise MissionStateError("invalid_input_mode", "topic GENESIS input fields are invalid")
        _validate_uuid(payload["mission_id"], version=4)
        topic = _validate_normalized(payload["normalized_topic"], "GENESIS.normalized_topic")
        budget = validate_budget(payload["discovery_budget"])
        if topic_mission_fingerprint(topic, budget) != payload["mission_fingerprint"]:
            raise MissionStateError("genesis_fingerprint_mismatch", "topic GENESIS fingerprint does not match inputs")
        _validate_confirmation(payload["public_discovery_confirmation"])
        _validate_utc_timestamp(payload["created_at"], "GENESIS created_at")
        if payload["migration"] is not None:
            raise MissionStateError("invalid_migration", "topic GENESIS does not support migration")
        if canonical_json_bytes(payload) != raw:
            raise MissionStateError("noncanonical_genesis", "GENESIS bytes are not canonical")
        return payload, raw

    def _assert_request_matches_genesis(self, genesis: dict[str, Any]) -> None:
        expected_schema = TOPIC_GENESIS_SCHEMA if self.input_mode == TOPIC_INPUT_MODE else GENESIS_SCHEMA
        if genesis["schema_version"] != expected_schema or genesis["mission_fingerprint"] != self.request_fingerprint:
            raise MissionStateError("mission_identity_mismatch", "topic, seeds, budget, or output root changed")

    def _assert_request_matches_contract(self, contract: dict[str, Any]) -> None:
        expected_schema = TOPIC_MISSION_CONTRACT_SCHEMA if self.input_mode == TOPIC_INPUT_MODE else MISSION_CONTRACT_SCHEMA
        if contract["schema_version"] != expected_schema or contract["mission_fingerprint"] != self.request_fingerprint:
            raise MissionStateError("mission_identity_mismatch", "topic, seeds, budget, or output root changed")

    def _validate_contract_against_genesis(self, contract: dict[str, Any], genesis: dict[str, Any]) -> None:
        topic_family = genesis["schema_version"] == TOPIC_GENESIS_SCHEMA
        expected_contract_schema = TOPIC_MISSION_CONTRACT_SCHEMA if topic_family else MISSION_CONTRACT_SCHEMA
        if contract["schema_version"] != expected_contract_schema:
            raise MissionStateError("contract_genesis_schema_mismatch", "mission contract family differs from GENESIS")
        fields = (
            "mission_id",
            "mission_fingerprint",
            "normalized_topic",
            "discovery_budget",
            "created_at",
            "migration",
        ) + (("input_mode", "normalized_initial_seeds") if topic_family else ("normalized_seeds",))
        for field in fields:
            if contract[field] != genesis[field]:
                raise MissionStateError("contract_genesis_mismatch", f"mission contract {field} differs from GENESIS")
        initial = genesis["public_discovery_confirmation"]
        current = contract["public_discovery_confirmation"]
        if initial["confirmed"] and current != initial:
            raise MissionStateError("confirmation_downgrade", "confirmed GENESIS authority cannot change")
        if not initial["confirmed"] and not current["confirmed"] and current != initial:
            raise MissionStateError("invalid_confirmation_transition", "unconfirmed contract differs from GENESIS")

    def _merge_confirmation(self, contract: dict[str, Any]) -> dict[str, Any]:
        result = dict(contract)
        confirmation = dict(result["public_discovery_confirmation"])
        if self.confirm_requested and not confirmation["confirmed"]:
            confirmation = {"confirmed": True, "confirmed_at": self.now(), "confirmation_source": "cli"}
            self.confirmation_transitioned = True
        result["public_discovery_confirmation"] = confirmation
        return result

    def _repair_mirrors(self, mission_control: dict[str, Any], next_action: dict[str, Any]) -> None:
        mirrors = [
            (self.output_dir / "mission_control.json", pretty_json_bytes(mission_control), "mission_mirror_repair"),
            (self.output_dir / "next_action.json", pretty_json_bytes(next_action), "next_action_mirror_repair"),
        ]
        for path, expected, label in mirrors:
            if not path.exists() or path.read_bytes() != expected:
                _atomic_write_bytes(path, expected, crash_hook=self.crash_hook, label=label)

    def _generation_dir(self, generation_id: Any) -> Path:
        _validate_generation_id(generation_id, "generation_id")
        unresolved = self.generations_dir / generation_id
        if unresolved.is_symlink() or not unresolved.is_dir():
            raise MissionStateError("invalid_generation_path", "generation path is missing or unsafe")
        path = unresolved.resolve()
        if path.parent != self.generations_dir.resolve():
            raise MissionStateError("invalid_generation_id", "generation_id escapes generations directory")
        return path

    def _validate_generation_manifest(
        self,
        manifest: dict[str, Any],
        directory: Path,
        *,
        expected_generation_id: str,
        expected_genesis_digest: str,
    ) -> None:
        expected = {
            "schema_version",
            "generation_id",
            "mission_id",
            "mission_fingerprint",
            "generation",
            "parent_generation_id",
            "transaction_nonce",
            "genesis_anchor_sha256",
            "mission_contract_sha256",
            "artifacts",
        }
        _require_exact_keys(manifest, expected, "generation manifest")
        if manifest["schema_version"] != GENERATION_MANIFEST_SCHEMA or manifest["generation_id"] != expected_generation_id:
            raise MissionStateError("invalid_generation_manifest", "manifest schema or generation ID is invalid")
        _validate_generation_id(manifest["generation_id"], "manifest generation_id")
        _validate_generation_id(manifest["parent_generation_id"], "manifest parent_generation_id", nullable=True)
        _validate_uuid(manifest["mission_id"])
        _validate_hex(manifest["mission_fingerprint"], 64, "manifest mission_fingerprint")
        _validate_hex(manifest["transaction_nonce"], 32, "manifest transaction_nonce")
        _validate_hex(manifest["genesis_anchor_sha256"], 64, "manifest genesis_anchor_sha256")
        _validate_hex(manifest["mission_contract_sha256"], 64, "manifest mission_contract_sha256")
        if manifest["genesis_anchor_sha256"] != expected_genesis_digest:
            raise MissionStateError("manifest_genesis_binding_mismatch", "manifest does not bind to the active GENESIS")
        _validate_positive_int(manifest["generation"], "manifest generation")
        expected_id, _ = generation_identity(
            mission_id=manifest["mission_id"],
            fingerprint=manifest["mission_fingerprint"],
            generation=manifest["generation"],
            parent_generation_id=manifest["parent_generation_id"],
            transaction_nonce=manifest["transaction_nonce"],
        )
        if expected_id != expected_generation_id:
            raise MissionStateError("generation_identity_mismatch", "generation ID does not match identity inputs")
        rows = _validate_artifact_rows(manifest["artifacts"])
        for row in rows:
            relative = row["relative_path"]
            path = _regular_file_beneath(directory, relative)
            if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
                raise MissionStateError("artifact_digest_mismatch", f"artifact digest or size mismatch: {relative}")
        expected_files = {"generation_manifest.json", *(row["relative_path"] for row in rows)}
        actual_files: set[str] = set()
        expected_directories = {
            parent.as_posix()
            for relative in expected_files
            for parent in PurePosixPath(relative).parents
            if parent.as_posix() != "."
        }
        actual_directories: set[str] = set()
        for path in directory.rglob("*"):
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise MissionStateError("unsafe_generation_path", f"unsafe generation path: {path}")
            if stat.S_ISREG(mode):
                actual_files.add(path.relative_to(directory).as_posix())
            elif stat.S_ISDIR(mode):
                actual_directories.add(path.relative_to(directory).as_posix())
        if actual_files != expected_files or actual_directories != expected_directories:
            raise MissionStateError("unexpected_generation_files", "generation directory contains unexpected or missing paths")

    def _validate_interrupted_genesis(self, genesis: dict[str, Any], genesis_digest: str) -> dict[str, Any]:
        transactions = self._scan_regular_json_files(self.transactions_dir)
        generation_names = self._generation_paths()
        accounted: set[str] = set()
        orphans: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for path, transaction in transactions:
            expected = {
                "schema_version",
                "status",
                "generation_id",
                "mission_id",
                "mission_fingerprint",
                "generation",
                "parent_generation_id",
                "transaction_nonce",
                "genesis_anchor_sha256",
                "owner_token",
                "created_at",
                "generation_manifest_sha256",
                "intent_sha256",
            }
            _require_exact_keys(transaction, expected, "transaction record")
            if transaction["schema_version"] != TRANSACTION_SCHEMA or transaction["status"] not in {"intent", "prepared"}:
                raise MissionStateError("invalid_interrupted_transaction", "interrupted transaction schema or status is invalid")
            _validate_generation_id(transaction["generation_id"], "transaction generation_id")
            _validate_generation_id(transaction["parent_generation_id"], "transaction parent_generation_id", nullable=True)
            _validate_positive_int(transaction["generation"], "transaction generation")
            _validate_uuid(transaction["mission_id"])
            _validate_hex(transaction["mission_fingerprint"], 64, "transaction mission_fingerprint")
            _validate_hex(transaction["transaction_nonce"], 32, "transaction nonce")
            _validate_hex(transaction["genesis_anchor_sha256"], 64, "transaction genesis digest")
            _validate_hex(transaction["owner_token"], 32, "transaction owner token")
            _validate_utc_timestamp(transaction["created_at"], "transaction created_at")
            if transaction["mission_id"] != genesis["mission_id"] or transaction["mission_fingerprint"] != genesis["mission_fingerprint"]:
                raise MissionStateError("foreign_interrupted_transaction", "interrupted transaction belongs to another mission")
            if transaction["genesis_anchor_sha256"] != genesis_digest or transaction["generation"] != 1 or transaction["parent_generation_id"] is not None:
                raise MissionStateError("invalid_interrupted_transaction", "interrupted transaction is not a genesis transaction")
            generation_id, _ = generation_identity(
                mission_id=transaction["mission_id"],
                fingerprint=transaction["mission_fingerprint"],
                generation=1,
                parent_generation_id=None,
                transaction_nonce=transaction["transaction_nonce"],
            )
            if generation_id != transaction["generation_id"] or path.stem != generation_id or generation_id in seen_ids:
                raise MissionStateError("invalid_interrupted_transaction", "interrupted transaction ID is invalid or duplicate")
            seen_ids.add(generation_id)
            staging = self.generations_dir / f".staging-{generation_id}"
            final = self.generations_dir / generation_id
            existing = [candidate for candidate in (staging, final) if candidate.exists()]
            if transaction["status"] == "intent":
                if (
                    final.exists()
                    or len(existing) > 1
                    or transaction["generation_manifest_sha256"] is not None
                    or transaction["intent_sha256"] is not None
                ):
                    raise MissionStateError("invalid_interrupted_intent", "intent transaction has invalid generation state")
                if staging.exists():
                    self._validate_partial_staging(staging)
            else:
                if len(existing) != 1 or not isinstance(transaction["generation_manifest_sha256"], str):
                    raise MissionStateError("invalid_interrupted_prepared", "prepared transaction must have exactly one generation directory")
                _validate_hex(transaction["generation_manifest_sha256"], 64, "transaction manifest digest")
                self._validate_intent_binding(transaction)
                manifest, raw = _read_json_exact(existing[0] / "generation_manifest.json", label="orphan generation manifest")
                if canonical_json_bytes(manifest) != raw:
                    raise MissionStateError("noncanonical_generation_manifest", "orphan generation manifest is not canonical")
                if sha256_bytes(raw) != transaction["generation_manifest_sha256"]:
                    raise MissionStateError("orphan_manifest_hash_mismatch", "orphan manifest digest does not match transaction")
                self._validate_generation_manifest(
                    manifest,
                    existing[0],
                    expected_generation_id=generation_id,
                    expected_genesis_digest=genesis_digest,
                )
                if manifest["mission_id"] != transaction["mission_id"] or manifest["mission_fingerprint"] != transaction["mission_fingerprint"]:
                    raise MissionStateError("orphan_manifest_mission_mismatch", "orphan manifest mission does not match transaction")
                if manifest["generation"] != transaction["generation"] or manifest["parent_generation_id"] != transaction["parent_generation_id"]:
                    raise MissionStateError("orphan_manifest_lineage_mismatch", "orphan manifest lineage does not match transaction")
                if manifest["transaction_nonce"] != transaction["transaction_nonce"] or manifest["genesis_anchor_sha256"] != genesis_digest:
                    raise MissionStateError("orphan_manifest_transaction_mismatch", "orphan manifest does not match transaction")
            for candidate in existing:
                accounted.add(candidate.name)
            orphans.append({"generation_id": generation_id, "status": transaction["status"], "paths": [candidate.name for candidate in existing]})
        actual = set(generation_names)
        if actual != accounted:
            raise MissionStateError("unjournaled_generation_state", "generation directory is not exhaustively journaled", details={"unexpected": sorted(actual - accounted), "missing": sorted(accounted - actual)})
        return {
            "state": "interrupted_genesis" if orphans else "genesis_uncommitted",
            "orphans": orphans,
            "orphan_temp_files": self._orphan_temp_paths(),
        }

    def _validate_later_orphans(
        self,
        genesis: dict[str, Any],
        pointer: dict[str, Any],
        *,
        reconcile: bool = True,
    ) -> dict[str, Any]:
        genesis_digest = sha256_file(self.genesis_path)
        transactions = self._validated_transactions(genesis, genesis_digest)
        generation_paths = self._generation_paths()

        current_id = pointer["generation_id"]
        authoritative: dict[str, int] = {}
        cursor: str | None = current_id
        expected_generation: int | None = None
        while cursor is not None:
            if cursor in authoritative:
                raise MissionStateError("generation_ancestry_cycle", "generation ancestry contains a cycle")
            transaction = transactions.get(cursor)
            if transaction is None:
                raise MissionStateError("missing_generation_transaction", f"missing transaction for authoritative generation: {cursor}")
            payload = transaction["payload"]
            if payload["status"] not in {"prepared", "committed"}:
                raise MissionStateError("invalid_authoritative_transaction", "authoritative transaction must be prepared or committed")
            final = self.generations_dir / cursor
            staging = self.generations_dir / f".staging-{cursor}"
            if not final.is_dir() or staging.exists():
                raise MissionStateError("invalid_authoritative_generation_path", "authoritative generation must have one final directory")
            manifest = self._validate_prepared_generation(payload, final, genesis_digest)
            if expected_generation is None:
                expected_generation = payload["generation"]
                if payload["generation_manifest_sha256"] != pointer["generation_manifest_sha256"]:
                    raise MissionStateError("current_transaction_manifest_mismatch", "CURRENT and transaction manifest digests differ")
            if payload["generation"] != expected_generation:
                raise MissionStateError("generation_ancestry_gap", "generation ancestry is not contiguous")
            if manifest["parent_generation_id"] != payload["parent_generation_id"]:
                raise MissionStateError("generation_ancestry_mismatch", "manifest and transaction parent differ")
            authoritative[cursor] = payload["generation"]
            cursor = payload["parent_generation_id"]
            expected_generation -= 1
        if expected_generation != 0:
            raise MissionStateError("generation_ancestry_missing_root", "generation ancestry does not terminate at generation 1")

        orphans: list[dict[str, Any]] = []
        accounted_paths: set[str] = set()
        reconciliation: tuple[Path, dict[str, Any]] | None = None
        for generation_id, transaction in transactions.items():
            payload = transaction["payload"]
            final = self.generations_dir / generation_id
            staging = self.generations_dir / f".staging-{generation_id}"
            existing = [path for path in (staging, final) if path.exists()]
            accounted_paths.update(path.name for path in existing)
            if generation_id in authoritative:
                if payload["status"] == "prepared":
                    if generation_id != current_id:
                        raise MissionStateError("prepared_authoritative_ancestor", "only CURRENT may have a prepared journal")
                    committed = dict(payload)
                    committed["status"] = "committed"
                    reconciliation = (transaction["path"], committed)
                continue
            if payload["status"] == "committed":
                raise MissionStateError("unreferenced_committed_generation", "committed generation is not on CURRENT ancestry")
            parent = payload["parent_generation_id"]
            if payload["generation"] == 1:
                if parent is not None:
                    raise MissionStateError("invalid_orphan_parent", "generation-1 orphan must have null parent")
            elif parent not in authoritative or authoritative[parent] != payload["generation"] - 1:
                raise MissionStateError("invalid_orphan_parent", "orphan parent is not the preceding authoritative generation")
            if payload["status"] == "intent":
                if final.exists() or len(existing) > 1 or payload["generation_manifest_sha256"] is not None:
                    raise MissionStateError("invalid_interrupted_intent", "intent transaction has invalid generation state")
                if staging.exists():
                    self._validate_partial_staging(staging)
            else:
                if len(existing) != 1:
                    raise MissionStateError("invalid_interrupted_prepared", "prepared orphan must have exactly one directory")
                self._validate_prepared_generation(payload, existing[0], genesis_digest)
            orphans.append({"generation_id": generation_id, "status": payload["status"], "paths": [path.name for path in existing]})

        if set(generation_paths) != accounted_paths:
            raise MissionStateError(
                "unjournaled_generation_state",
                "generation directories are not exhaustively journaled",
                details={"unexpected": sorted(set(generation_paths) - accounted_paths)},
            )
        if reconciliation is not None and reconcile:
            path, committed = reconciliation
            _atomic_write_bytes(
                path,
                canonical_json_bytes(committed),
                crash_hook=self.crash_hook,
                label="reconcile_current_transaction",
            )
        return {
            "state": "current_v2",
            "orphans": sorted(orphans, key=lambda row: row["generation_id"]),
            "orphan_temp_files": self._orphan_temp_paths(),
        }
    def _validated_transactions(self, genesis: dict[str, Any], genesis_digest: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for path, payload in self._scan_regular_json_files(self.transactions_dir):
            expected = {
                "schema_version",
                "status",
                "generation_id",
                "mission_id",
                "mission_fingerprint",
                "generation",
                "parent_generation_id",
                "transaction_nonce",
                "genesis_anchor_sha256",
                "owner_token",
                "created_at",
                "generation_manifest_sha256",
                "intent_sha256",
            }
            _require_exact_keys(payload, expected, "transaction record")
            if payload["schema_version"] != TRANSACTION_SCHEMA or payload["status"] not in {"intent", "prepared", "committed"}:
                raise MissionStateError("invalid_transaction", "transaction schema or status is invalid")
            _validate_generation_id(payload["generation_id"], "transaction generation_id")
            _validate_generation_id(payload["parent_generation_id"], "transaction parent_generation_id", nullable=True)
            _validate_uuid(payload["mission_id"])
            _validate_hex(payload["mission_fingerprint"], 64, "transaction mission_fingerprint")
            if payload["mission_id"] != genesis["mission_id"] or payload["mission_fingerprint"] != genesis["mission_fingerprint"]:
                raise MissionStateError("foreign_transaction", "transaction belongs to another mission")
            if payload["genesis_anchor_sha256"] != genesis_digest:
                raise MissionStateError("transaction_genesis_mismatch", "transaction does not bind to active GENESIS")
            _validate_positive_int(payload["generation"], "transaction generation")
            _validate_hex(payload["transaction_nonce"], 32, "transaction nonce")
            _validate_hex(payload["owner_token"], 32, "transaction owner token")
            _validate_utc_timestamp(payload["created_at"], "transaction created_at")
            expected_id, _ = generation_identity(
                mission_id=payload["mission_id"],
                fingerprint=payload["mission_fingerprint"],
                generation=payload["generation"],
                parent_generation_id=payload["parent_generation_id"],
                transaction_nonce=payload["transaction_nonce"],
            )
            if payload["generation_id"] != expected_id or path.stem != expected_id or expected_id in result:
                raise MissionStateError("invalid_transaction_identity", "transaction identity is invalid or duplicate")
            if payload["status"] == "intent":
                if payload["generation_manifest_sha256"] is not None or payload["intent_sha256"] is not None:
                    raise MissionStateError("invalid_transaction", "intent must not have a manifest digest")
            else:
                _validate_hex(payload["generation_manifest_sha256"], 64, "transaction manifest digest")
                self._validate_intent_binding(payload)
            result[expected_id] = {"path": path, "payload": payload}
        return result

    def _validate_intent_binding(self, transaction: dict[str, Any]) -> None:
        _validate_hex(transaction["intent_sha256"], 64, "transaction intent digest")
        intent = dict(transaction)
        intent["status"] = "intent"
        intent["generation_manifest_sha256"] = None
        intent["intent_sha256"] = None
        if sha256_bytes(canonical_json_bytes(intent)) != transaction["intent_sha256"]:
            raise MissionStateError("transaction_intent_mismatch", "prepared transaction does not bind to its exact intent identity")

    def _validate_prepared_generation(
        self,
        transaction: dict[str, Any],
        directory: Path,
        genesis_digest: str,
    ) -> dict[str, Any]:
        manifest, raw = _read_json_exact(directory / "generation_manifest.json", label="generation manifest")
        if canonical_json_bytes(manifest) != raw:
            raise MissionStateError("noncanonical_generation_manifest", "generation manifest bytes are not canonical")
        if sha256_bytes(raw) != transaction["generation_manifest_sha256"]:
            raise MissionStateError("generation_manifest_hash_mismatch", "transaction manifest digest does not match")
        if manifest["mission_id"] != transaction["mission_id"] or manifest["mission_fingerprint"] != transaction["mission_fingerprint"]:
            raise MissionStateError("generation_manifest_mission_mismatch", "manifest mission does not match transaction")
        if manifest["generation"] != transaction["generation"] or manifest["parent_generation_id"] != transaction["parent_generation_id"]:
            raise MissionStateError("generation_manifest_lineage_mismatch", "manifest lineage does not match transaction")
        if manifest["transaction_nonce"] != transaction["transaction_nonce"]:
            raise MissionStateError("generation_manifest_nonce_mismatch", "manifest nonce does not match transaction")
        self._validate_generation_manifest(
            manifest,
            directory,
            expected_generation_id=transaction["generation_id"],
            expected_genesis_digest=genesis_digest,
        )
        return manifest

    def _validate_partial_staging(self, directory: Path) -> None:
        allowed = {"mission_control.json", "next_action.json", "generation_manifest.json"}
        for path in directory.rglob("*"):
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise MissionStateError("unsafe_partial_staging", f"unsafe partial staging path: {path}")
            relative = path.relative_to(directory).as_posix()
            if relative not in allowed:
                raise MissionStateError("unexpected_partial_staging_file", f"unexpected partial staging file: {relative}")

    def _generation_paths(self) -> list[str]:
        result: list[str] = []
        for path in self.generations_dir.iterdir():
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise MissionStateError("unsafe_generation_path", f"unsafe generation entry: {path.name}")
            result.append(path.name)
        return result

    def _scan_regular_json_files(self, directory: Path) -> list[tuple[Path, dict[str, Any]]]:
        result: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(directory.iterdir()):
            if _is_safe_atomic_temp(path):
                continue
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or path.suffix != ".json":
                raise MissionStateError("unexpected_mission_state_path", f"unexpected transaction path: {path.name}")
            payload, raw = _read_json_exact(path, label="transaction record")
            if canonical_json_bytes(payload) != raw:
                raise MissionStateError("noncanonical_transaction", f"transaction record is not canonical: {path.name}")
            result.append((path, payload))
        return result

    def _v2_child_paths(self) -> list[str]:
        if not self.state_dir.exists():
            return []
        allowed_empty = {"generations", "transactions"}
        paths = []
        for path in self.state_dir.iterdir():
            if _is_safe_atomic_temp(path):
                continue
            if path.name in allowed_empty and path.is_dir() and not any(path.iterdir()):
                continue
            paths.append(path.name)
        return sorted(paths)

    def _orphan_temp_paths(self) -> list[str]:
        result: list[str] = []
        for directory in (self.output_dir, self.state_dir, self.transactions_dir):
            if not directory.is_dir():
                continue
            for path in directory.iterdir():
                if _is_safe_atomic_temp(path):
                    result.append(path.relative_to(self.output_dir).as_posix())
        return sorted(result)


def validate_generation_ancestor_readonly(
    *,
    output_dir: Path,
    mission_id: str,
    mission_fingerprint: str,
    generation_id: str,
) -> dict[str, Any]:
    """Validate a mission anchor without lock acquisition or mirror repair."""
    manager = MissionStateManager(
        output_dir=output_dir,
        topic="read-only mission validation",
        seeds=["read-only validation seed"],
        confirm_public_discovery=False,
        resume=True,
        force=False,
    )
    manager._validate_state_container_paths()
    genesis, genesis_raw = manager._validate_genesis()
    if genesis["mission_id"] != mission_id or genesis["mission_fingerprint"] != mission_fingerprint:
        raise MissionStateError("foreign_lineage", "artifact identity differs from mission-state GENESIS")
    _validate_generation_id(generation_id, "artifact anchor generation_id")

    pointer, pointer_raw = _read_json_exact(manager.current_path, label="CURRENT")
    _require_exact_keys(pointer, {"schema_version", "generation_id", "generation_manifest_sha256"}, "CURRENT")
    if pointer["schema_version"] != CURRENT_SCHEMA or canonical_json_bytes(pointer) != pointer_raw:
        raise MissionStateError("invalid_current_pointer", "mission CURRENT is unsupported or noncanonical")
    _validate_hex(pointer["generation_manifest_sha256"], 64, "generation_manifest_sha256")

    current_dir = manager._generation_dir(pointer["generation_id"])
    manifest, manifest_raw = _read_json_exact(current_dir / "generation_manifest.json", label="generation manifest")
    if sha256_bytes(manifest_raw) != pointer["generation_manifest_sha256"]:
        raise MissionStateError("current_manifest_hash_mismatch", "mission CURRENT manifest digest differs")
    genesis_digest = sha256_bytes(genesis_raw)
    manager._validate_generation_manifest(
        manifest,
        current_dir,
        expected_generation_id=pointer["generation_id"],
        expected_genesis_digest=genesis_digest,
    )
    mission_control, _ = _read_json_exact(current_dir / "mission_control.json", label="mission control")
    next_action, _ = _read_json_exact(current_dir / "next_action.json", label="next action")
    contract = manager._validate_contract(mission_control.get("mission_contract"))
    manager._validate_contract_against_genesis(contract, genesis)
    manager._validate_current_payload_bindings(mission_control, next_action, contract, pointer, manifest)
    manager._validate_later_orphans(genesis, pointer, reconcile=False)

    transactions = manager._validated_transactions(genesis, genesis_digest)
    cursor: str | None = pointer["generation_id"]
    while cursor is not None:
        if cursor == generation_id:
            return {
                "mission_id": mission_id,
                "mission_fingerprint": mission_fingerprint,
                "current_generation_id": pointer["generation_id"],
                "anchor_generation_id": generation_id,
            }
        transaction = transactions.get(cursor)
        if transaction is None:
            break
        cursor = transaction["payload"]["parent_generation_id"]
    raise MissionStateError("artifact_anchor_not_ancestor", "artifact anchor is not on active mission ancestry")


def validate_generation_binding_readonly(
    *,
    output_dir: Path,
    mission_id: str,
    mission_fingerprint: str,
    generation_id: str,
    metadata_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reopen one immutable active-ancestry generation and return exact bindings."""
    ancestry = validate_generation_ancestor_readonly(
        output_dir=output_dir,
        mission_id=mission_id,
        mission_fingerprint=mission_fingerprint,
        generation_id=generation_id,
    )
    manager = MissionStateManager(
        output_dir=output_dir,
        topic="read-only generation binding validation",
        seeds=["read-only generation binding seed"],
        confirm_public_discovery=False,
        resume=True,
        force=False,
    )
    manager._validate_state_container_paths()
    genesis, genesis_raw = manager._validate_genesis()
    genesis_digest = sha256_bytes(genesis_raw)
    transactions = manager._validated_transactions(genesis, genesis_digest)
    transaction = transactions.get(generation_id)
    if transaction is None or transaction["payload"]["status"] not in {"prepared", "committed"}:
        raise MissionStateError("invalid_generation_binding", "generation binding is not committed on active ancestry")
    generation_dir = manager._generation_dir(generation_id)
    manifest = manager._validate_prepared_generation(transaction["payload"], generation_dir, genesis_digest)
    mission_control, mission_raw = _read_json_exact(generation_dir / "mission_control.json", label="mission control")
    next_action, next_raw = _read_json_exact(generation_dir / "next_action.json", label="next action")
    if mission_raw != pretty_json_bytes(mission_control) or next_raw != pretty_json_bytes(next_action):
        raise MissionStateError("noncanonical_generation_payload", "generation payload bytes are not canonical pretty JSON")
    contract = manager._validate_contract(mission_control.get("mission_contract"))
    manager._validate_contract_against_genesis(contract, genesis)
    manager._validate_current_payload_bindings(
        mission_control,
        next_action,
        contract,
        {"generation_id": generation_id},
        manifest,
    )
    recorded_authority = mission_control.get("source_intake_metadata_authority")
    if recorded_authority != next_action.get("source_intake_metadata_authority"):
        raise MissionStateError(
            "metadata_authority_payload_mismatch",
            "mission-control and next-action metadata authority objects differ",
        )
    if metadata_authority is not None and recorded_authority != metadata_authority:
        raise MissionStateError(
            "metadata_authority_binding_mismatch",
            "generation metadata authority differs from the expected authority",
        )
    authority_digest = (
        sha256_bytes(canonical_json_bytes(recorded_authority))
        if isinstance(recorded_authority, dict)
        else None
    )
    return {
        **ancestry,
        "mission_contract": contract,
        "mission_contract_sha256": contract["lineage"]["mission_contract_sha256"],
        "mission_control": mission_control,
        "mission_control_sha256": sha256_bytes(mission_raw),
        "mission_control_size_bytes": len(mission_raw),
        "next_action": next_action,
        "next_action_sha256": sha256_bytes(next_raw),
        "next_action_size_bytes": len(next_raw),
        "generation_manifest": manifest,
        "generation_manifest_sha256": transaction["payload"]["generation_manifest_sha256"],
        "metadata_authority": recorded_authority,
        "metadata_authority_sha256": authority_digest,
    }


__all__ = [
    "CURRENT_SCHEMA",
    "GENESIS_SCHEMA",
    "GENERATION_IDENTITY_SCHEMA",
    "GENERATION_MANIFEST_SCHEMA",
    "LEGACY_MISSION_SCHEMA",
    "MISSION_CONTRACT_SCHEMA",
    "MISSION_CONTROL_SCHEMA",
    "MissionLock",
    "MissionSnapshot",
    "MissionStateError",
    "MissionStateManager",
    "canonical_json_bytes",
    "discovery_budget",
    "generation_identity",
    "migrated_mission_id",
    "mission_fingerprint",
    "normalize_seeds",
    "normalize_text",
    "validate_budget",
    "validate_generation_ancestor_readonly",
    "validate_generation_binding_readonly",
]
