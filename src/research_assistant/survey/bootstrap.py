from __future__ import annotations

import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from research_assistant.survey.mission_state import (
    TOPIC_BOOTSTRAP_AUTHORITY_SCHEMA,
    TOPIC_INPUT_MODE,
    TOPIC_MISSION_CONTRACT_SCHEMA,
    MissionSnapshot,
    MissionStateError,
    MissionStateManager,
    _atomic_write_bytes,
    _fsync_directory,
    _read_json_exact,
    _require_exact_keys,
    _validate_generation_id,
    _validate_hex,
    _validate_positive_int,
    _validate_utc_timestamp,
    canonical_json_bytes,
    normalize_seeds,
    normalize_text,
    sha256_bytes,
    sha256_file,
)


BOOTSTRAP_REQUEST_SCHEMA = "ra-survey-topic-bootstrap-request-v1"
BOOTSTRAP_OUTCOME_SCHEMA = "ra-survey-topic-bootstrap-outcome-v1"
BOOTSTRAP_JOURNAL_SCHEMA = "ra-survey-topic-bootstrap-journal-v1"
BOOTSTRAP_SET_MANIFEST_SCHEMA = "ra-survey-topic-bootstrap-set-manifest-v1"
BOOTSTRAP_CURRENT_SCHEMA = "ra-survey-topic-bootstrap-current-v1"

REQUEST_ID_RE = re.compile(r"^br-[0-9a-f]{64}$")
SET_ID_RE = re.compile(r"^bs-[0-9a-f]{64}$")
SAFE_TEMP_RE = re.compile(r"^\.[A-Za-z0-9_.-]+\.[A-Za-z0-9_-]+\.tmp$")

JOURNAL_STATES = {"intent", "call_started", "result_recorded", "prepared", "selected"}
OUTCOMES = {"selected", "empty", "ambiguous", "unavailable", "capped"}
UNAVAILABLE_REASONS = {
    "production_capability_unavailable",
    "capability_reported_unavailable",
    "capability_failed_closed",
}
CAPPED_REASONS = {"candidate_cap_reached", "provider_result_cap_reached"}


class MissionBootstrapCapability(Protocol):
    name: str
    version: str

    def run(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class UnavailableBootstrapCapability:
    name: str = "m17_no_production_bootstrap_adapter"
    version: str = "1"

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
            "outcome": "unavailable",
            "selected_candidates": [],
            "candidates": [],
            "ambiguities": [],
            "reason": "production_capability_unavailable",
            "cap": None,
            "observed_count": 0,
            "descriptive": {"network_or_provider_called": False},
        }


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MissionStateError("invalid_bootstrap_schema", f"{field} must be a nonempty string")
    return value


def _string_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise MissionStateError("invalid_bootstrap_schema", f"{field} must be a list")
    if any(not isinstance(row, str) or not row for row in value):
        raise MissionStateError("invalid_bootstrap_schema", f"{field} must contain nonempty strings")
    if len(set(value)) != len(value) or value != sorted(value):
        raise MissionStateError("invalid_bootstrap_schema", f"{field} must be unique and sorted")
    return list(value)


def _validate_candidate(value: Any, field: str) -> dict[str, Any]:
    expected = {
        "paper_key",
        "display",
        "identifier_evidence",
        "title_evidence",
        "descriptive",
    }
    _require_exact_keys(value, expected, field)
    paper_key = normalize_text(value["paper_key"], field=f"{field}.paper_key")["key"]
    display = normalize_text(value["display"], field=f"{field}.display")["display"]
    identifiers = _string_list(value["identifier_evidence"], f"{field}.identifier_evidence")
    titles = _string_list(value["title_evidence"], f"{field}.title_evidence")
    if not identifiers and not titles:
        raise MissionStateError("invalid_bootstrap_candidate", "candidate must retain identifier or title evidence")
    if not isinstance(value["descriptive"], dict):
        raise MissionStateError("invalid_bootstrap_candidate", "candidate descriptive fields must be an object")
    canonical_json_bytes(value["descriptive"])
    return {
        "paper_key": paper_key,
        "display": display,
        "identifier_evidence": identifiers,
        "title_evidence": titles,
        "descriptive": dict(value["descriptive"]),
    }


def _validate_ambiguity(value: Any, field: str) -> dict[str, Any]:
    _require_exact_keys(value, {"kind", "paper_keys"}, field)
    kind = _nonempty_string(value["kind"], f"{field}.kind")
    paper_keys = _string_list(value["paper_keys"], f"{field}.paper_keys", nonempty=True)
    return {"kind": kind, "paper_keys": paper_keys}


def validate_bootstrap_outcome(value: Any) -> dict[str, Any]:
    expected = {
        "schema_version",
        "outcome",
        "selected_candidates",
        "candidates",
        "ambiguities",
        "reason",
        "cap",
        "observed_count",
        "descriptive",
    }
    _require_exact_keys(value, expected, "bootstrap outcome")
    if value["schema_version"] != BOOTSTRAP_OUTCOME_SCHEMA or value["outcome"] not in OUTCOMES:
        raise MissionStateError("invalid_bootstrap_outcome", "bootstrap outcome schema or disposition is invalid")
    selected = [
        _validate_candidate(row, f"selected_candidates[{index}]")
        for index, row in enumerate(value["selected_candidates"])
    ] if isinstance(value["selected_candidates"], list) else None
    candidates = [
        _validate_candidate(row, f"candidates[{index}]")
        for index, row in enumerate(value["candidates"])
    ] if isinstance(value["candidates"], list) else None
    ambiguities = [
        _validate_ambiguity(row, f"ambiguities[{index}]")
        for index, row in enumerate(value["ambiguities"])
    ] if isinstance(value["ambiguities"], list) else None
    if selected is None or candidates is None or ambiguities is None:
        raise MissionStateError("invalid_bootstrap_outcome", "bootstrap candidate and ambiguity fields must be lists")
    for label, rows in (("selected_candidates", selected), ("candidates", candidates)):
        keys = [row["paper_key"] for row in rows]
        if keys != sorted(set(keys)):
            raise MissionStateError("invalid_bootstrap_outcome", f"{label} must be unique and paper-key-sorted")
    if not isinstance(value["observed_count"], int) or isinstance(value["observed_count"], bool) or value["observed_count"] < 0:
        raise MissionStateError("invalid_bootstrap_outcome", "observed_count must be a nonnegative integer")
    if not isinstance(value["descriptive"], dict):
        raise MissionStateError("invalid_bootstrap_outcome", "descriptive must be an object")
    canonical_json_bytes(value["descriptive"])

    outcome = value["outcome"]
    reason = value["reason"]
    cap = value["cap"]
    observed = value["observed_count"]
    if outcome == "selected":
        if not selected or ambiguities or reason is not None or cap is not None:
            raise MissionStateError("invalid_bootstrap_outcome", "selected outcome has incompatible fields")
        normalized = normalize_seeds([row["display"] for row in selected])
        if [row["display"] for row in selected] != [row["display"] for row in normalized]:
            raise MissionStateError("invalid_bootstrap_outcome", "selected candidates must be effective-seed sorted")
        if observed < len(selected):
            raise MissionStateError("invalid_bootstrap_outcome", "selected outcome observed_count is too small")
    elif outcome == "empty":
        if selected or candidates or ambiguities or reason is not None or cap is not None or observed != 0:
            raise MissionStateError("invalid_bootstrap_outcome", "empty outcome has incompatible fields")
    elif outcome == "ambiguous":
        if selected or not candidates or not ambiguities or reason is not None or cap is not None or observed < len(candidates):
            raise MissionStateError("invalid_bootstrap_outcome", "ambiguous outcome has incompatible fields")
        known = {row["paper_key"] for row in candidates}
        if any(not set(row["paper_keys"]).issubset(known) for row in ambiguities):
            raise MissionStateError("invalid_bootstrap_outcome", "ambiguity references an unknown candidate")
    elif outcome == "unavailable":
        if selected or candidates or ambiguities or reason not in UNAVAILABLE_REASONS or cap is not None or observed != 0:
            raise MissionStateError("invalid_bootstrap_outcome", "unavailable outcome has incompatible fields")
    else:
        if selected or ambiguities or reason not in CAPPED_REASONS:
            raise MissionStateError("invalid_bootstrap_outcome", "capped outcome has incompatible fields")
        if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0 or observed <= cap:
            raise MissionStateError("invalid_bootstrap_outcome", "capped outcome requires observed_count above a positive cap")

    return {
        "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
        "outcome": outcome,
        "selected_candidates": selected,
        "candidates": candidates,
        "ambiguities": ambiguities,
        "reason": reason,
        "cap": cap,
        "observed_count": observed,
        "descriptive": dict(value["descriptive"]),
    }


@dataclass
class MissionBootstrapStore:
    manager: MissionStateManager
    snapshot: MissionSnapshot
    now: Callable[[], str]
    crash_at: str | None = None

    @classmethod
    def from_snapshot(
        cls,
        *,
        manager: MissionStateManager,
        snapshot: MissionSnapshot,
        now: Callable[[], str],
        crash_at: str | None = None,
    ) -> "MissionBootstrapStore":
        if not manager.lock._held:
            raise MissionStateError("mission_lock_not_held", "bootstrap store requires the active mission lock")
        contract = snapshot.contract
        if contract.get("schema_version") != TOPIC_MISSION_CONTRACT_SCHEMA or contract.get("input_mode") != TOPIC_INPUT_MODE:
            raise MissionStateError("invalid_input_mode", "bootstrap store requires a topic-input mission")
        if snapshot.current_pointer is None:
            raise MissionStateError("missing_confirmed_generation", "bootstrap store requires a committed confirmed generation")
        confirmation = contract.get("public_discovery_confirmation")
        if not isinstance(confirmation, dict) or not confirmation.get("confirmed"):
            raise MissionStateError("public_discovery_confirmation_required", "bootstrap capability requires durable confirmation")
        manager.assert_generation_ancestor(snapshot.current_pointer["generation_id"])
        store = cls(manager=manager, snapshot=snapshot, now=now, crash_at=crash_at)
        store._validate_root(create=True)
        store.observe()
        return store

    @property
    def root(self) -> Path:
        return self.manager.state_dir / "bootstrap"

    @property
    def transactions_dir(self) -> Path:
        return self.root / "transactions"

    @property
    def results_dir(self) -> Path:
        return self.root / "results"

    @property
    def sets_dir(self) -> Path:
        return self.root / "sets"

    @property
    def history_dir(self) -> Path:
        return self.root / "history"

    @property
    def current_path(self) -> Path:
        return self.root / "CURRENT"

    def _crash_hook(self, label: str) -> None:
        if label == self.crash_at:
            raise RuntimeError(f"injected crash at {label}")

    def _crash(self, label: str) -> None:
        self._crash_hook(label)

    def _atomic(self, path: Path, value: bytes, label: str) -> None:
        _atomic_write_bytes(path, value, crash_hook=self._crash_hook, label=label)

    def _validate_root(self, *, create: bool) -> None:
        directories = (self.root, self.transactions_dir, self.results_dir, self.sets_dir, self.history_dir)
        for path in directories:
            if path.exists() or path.is_symlink():
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                    raise MissionStateError("unsafe_bootstrap_path", f"bootstrap container is unsafe: {path}")
            elif create:
                path.mkdir(mode=0o700)
                _fsync_directory(path.parent)
        allowed_root = {"transactions", "results", "sets", "history", "CURRENT"}
        for path in self.root.iterdir():
            if path.name not in allowed_root and not self._safe_temp(path):
                raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap root path: {path.name}")
        if self.current_path.exists() or self.current_path.is_symlink():
            if stat.S_ISLNK(self.current_path.lstat().st_mode) or not stat.S_ISREG(self.current_path.lstat().st_mode):
                raise MissionStateError("unsafe_bootstrap_path", "bootstrap CURRENT is not a regular file")
        for directory, suffix in ((self.transactions_dir, ".json"), (self.results_dir, ".json")):
            for path in directory.iterdir():
                if self._safe_temp(path):
                    continue
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or path.suffix != suffix:
                    raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap file: {path}")
        for path in self.sets_dir.iterdir():
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap set path: {path}")
            if not (SET_ID_RE.fullmatch(path.name) or path.name.startswith(".staging-bs-")):
                raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap set directory: {path.name}")
        for path in self.history_dir.iterdir():
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode) or REQUEST_ID_RE.fullmatch(path.name) is None:
                raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap history path: {path.name}")

    def _safe_temp(self, path: Path) -> bool:
        if SAFE_TEMP_RE.fullmatch(path.name) is None:
            return False
        if not stat.S_ISREG(path.lstat().st_mode):
            raise MissionStateError("unsafe_bootstrap_path", f"bootstrap temp is not regular: {path}")
        return True

    def _scan_transactions(self) -> list[tuple[Path, dict[str, Any]]]:
        self._reconcile_history_mirror()
        rows = []
        for path in sorted(self.transactions_dir.iterdir()):
            if self._safe_temp(path):
                continue
            if stat.S_ISLNK(path.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode) or path.suffix != ".json":
                raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap transaction: {path.name}")
            payload, raw = _read_json_exact(path, label="bootstrap journal")
            if canonical_json_bytes(payload) != raw:
                raise MissionStateError("noncanonical_bootstrap_journal", "bootstrap journal is not canonical")
            self._validate_journal(payload, path)
            rows.append((path, payload))
        return rows

    def _history_rows(self) -> list[dict[str, Any]]:
        request_dirs = sorted(self.history_dir.iterdir())
        if len(request_dirs) > 1:
            raise MissionStateError("multiple_bootstrap_attempts", "M17 permits exactly one immutable bootstrap attempt history")
        if not request_dirs:
            return []
        directory = request_dirs[0]
        by_status: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.iterdir()):
            if self._safe_temp(path):
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or path.suffix != ".json":
                raise MissionStateError("unexpected_bootstrap_path", f"unexpected bootstrap history row: {path.name}")
            payload, raw = _read_json_exact(path, label="bootstrap history")
            if canonical_json_bytes(payload) != raw:
                raise MissionStateError("noncanonical_bootstrap_journal", "bootstrap history row is not canonical")
            status = payload.get("status")
            if status not in JOURNAL_STATES or path.name != f"{status}.json" or status in by_status:
                raise MissionStateError("invalid_bootstrap_history", "bootstrap history filename or status is invalid")
            self._validate_journal(payload, self.transactions_dir / f"{payload.get('request_id')}.json")
            if payload["request_id"] != directory.name:
                raise MissionStateError("invalid_bootstrap_history", "bootstrap history belongs to another request")
            by_status[status] = payload
        order = ["intent", "call_started", "result_recorded", "prepared", "selected"]
        statuses = [status for status in order if status in by_status]
        if statuses != order[: len(statuses)]:
            raise MissionStateError("invalid_bootstrap_history", "bootstrap history has a lifecycle gap")
        rows = [by_status[status] for status in statuses]
        for index, payload in enumerate(rows):
            expected_prior = None if index == 0 else sha256_bytes(canonical_json_bytes(rows[index - 1]))
            if payload["prior_status_sha256"] != expected_prior:
                raise MissionStateError("bootstrap_history_chain_mismatch", "bootstrap history prior-status digest differs")
        return rows

    def _reconcile_history_mirror(self) -> None:
        history = self._history_rows()
        mirrors = [
            path for path in self.transactions_dir.iterdir()
            if not self._safe_temp(path)
        ]
        if len(mirrors) > 1:
            raise MissionStateError("multiple_bootstrap_attempts", "M17 permits exactly one bootstrap journal mirror")
        if not history:
            if mirrors:
                raise MissionStateError("bootstrap_history_missing", "bootstrap journal has no immutable history")
            return
        latest = history[-1]
        expected_path = self.transactions_dir / f"{latest['request_id']}.json"
        if mirrors and mirrors[0] != expected_path:
            raise MissionStateError("foreign_bootstrap_journal", "bootstrap journal mirror belongs to another request")
        expected_raw = canonical_json_bytes(latest)
        if not expected_path.exists():
            self._crash("bootstrap_reconcile:before_mirror")
            self._atomic(expected_path, expected_raw, "bootstrap_history_reconcile")
            self._crash("bootstrap_reconcile:after_mirror")
            return
        payload, raw = _read_json_exact(expected_path, label="bootstrap journal mirror")
        if raw == expected_raw:
            return
        matching_history = next(
            (row for row in history if canonical_json_bytes(row) == raw),
            None,
        )
        if matching_history is None:
            raise MissionStateError("bootstrap_journal_history_mismatch", "bootstrap journal mirror is not an immutable history row")
        if history.index(matching_history) != len(history) - 2:
            raise MissionStateError("bootstrap_journal_history_mismatch", "bootstrap journal mirror lags by more than one transition")
        self._crash("bootstrap_reconcile:before_mirror")
        self._atomic(expected_path, expected_raw, "bootstrap_history_reconcile")
        self._crash("bootstrap_reconcile:after_mirror")

    def _install_history(self, value: dict[str, Any]) -> None:
        request_id = value["request_id"]
        directory = self.history_dir / request_id
        if directory.exists() or directory.is_symlink():
            if stat.S_ISLNK(directory.lstat().st_mode) or not stat.S_ISDIR(directory.lstat().st_mode):
                raise MissionStateError("unsafe_bootstrap_path", "bootstrap history request directory is unsafe")
        else:
            directory.mkdir(mode=0o700)
            _fsync_directory(self.history_dir)
        path = directory / f"{value['status']}.json"
        raw = canonical_json_bytes(value)
        if path.exists() or path.is_symlink():
            if stat.S_ISLNK(path.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode) or path.read_bytes() != raw:
                raise MissionStateError("bootstrap_history_collision", "immutable bootstrap history differs")
            return
        descriptor, temp_name = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
        temporary = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, path)
            _fsync_directory(directory)
        except FileExistsError as exc:
            raise MissionStateError("bootstrap_history_collision", "immutable bootstrap history appeared concurrently") from exc
        finally:
            temporary.unlink(missing_ok=True)
            _fsync_directory(directory)

    def _record_journal(self, path: Path, value: dict[str, Any], label: str) -> None:
        self._install_history(value)
        self._crash(f"{label}:after_history_fsync")
        self._atomic(path, canonical_json_bytes(value), label)

    def _request(self, capability: MissionBootstrapCapability) -> dict[str, Any]:
        name = _nonempty_string(getattr(capability, "name", None), "capability name")
        version = _nonempty_string(getattr(capability, "version", None), "capability version")
        contract = self.snapshot.contract
        confirmation = contract["public_discovery_confirmation"]
        base = {
            "schema_version": BOOTSTRAP_REQUEST_SCHEMA,
            "mission_id": contract["mission_id"],
            "mission_fingerprint": contract["mission_fingerprint"],
            "confirmed_generation_id": self.snapshot.current_pointer["generation_id"],
            "input_mode": TOPIC_INPUT_MODE,
            "normalized_topic": contract["normalized_topic"],
            "discovery_budget": contract["discovery_budget"],
            "output_root": str(self.manager.output_dir),
            "confirmation": {
                "confirmed_at": confirmation["confirmed_at"],
                "confirmation_source": confirmation["confirmation_source"],
            },
            "capability_name": name,
            "capability_version": version,
        }
        digest = sha256_bytes(canonical_json_bytes(base))
        return {**base, "request_id": f"br-{digest}", "request_sha256": digest}

    def _validate_request(self, value: Any) -> dict[str, Any]:
        expected = {
            "schema_version", "request_id", "request_sha256", "mission_id", "mission_fingerprint",
            "confirmed_generation_id", "input_mode", "normalized_topic", "discovery_budget", "output_root",
            "confirmation", "capability_name", "capability_version",
        }
        _require_exact_keys(value, expected, "bootstrap request")
        if value["schema_version"] != BOOTSTRAP_REQUEST_SCHEMA or value["input_mode"] != TOPIC_INPUT_MODE:
            raise MissionStateError("invalid_bootstrap_request", "bootstrap request schema or input mode is invalid")
        if not isinstance(value["request_id"], str) or REQUEST_ID_RE.fullmatch(value["request_id"]) is None:
            raise MissionStateError("invalid_bootstrap_request", "bootstrap request ID is invalid")
        _validate_hex(value["request_sha256"], 64, "request_sha256")
        projection = dict(value)
        projection.pop("request_id")
        projection.pop("request_sha256")
        digest = sha256_bytes(canonical_json_bytes(projection))
        if value["request_id"] != f"br-{digest}" or value["request_sha256"] != digest:
            raise MissionStateError("invalid_bootstrap_request", "bootstrap request digest is invalid")
        return dict(value)

    def _new_journal(self, request: dict[str, Any]) -> dict[str, Any]:
        timestamp = self.now()
        _validate_utc_timestamp(timestamp, "bootstrap timestamp")
        return {
            "schema_version": BOOTSTRAP_JOURNAL_SCHEMA,
            "status": "intent",
            "request": request,
            "request_id": request["request_id"],
            "request_sha256": request["request_sha256"],
            "mission_id": request["mission_id"],
            "mission_fingerprint": request["mission_fingerprint"],
            "confirmed_generation_id": request["confirmed_generation_id"],
            "capability_name": request["capability_name"],
            "capability_version": request["capability_version"],
            "created_at": timestamp,
            "updated_at": timestamp,
            "result_sha256": None,
            "set_id": None,
            "manifest_sha256": None,
            "prior_status_sha256": None,
        }

    def _validate_journal(self, value: Any, path: Path) -> dict[str, Any]:
        expected = {
            "schema_version", "status", "request", "request_id", "request_sha256", "mission_id",
            "mission_fingerprint", "confirmed_generation_id", "capability_name", "capability_version",
            "created_at", "updated_at", "result_sha256", "set_id", "manifest_sha256",
            "prior_status_sha256",
        }
        _require_exact_keys(value, expected, "bootstrap journal")
        if value["schema_version"] != BOOTSTRAP_JOURNAL_SCHEMA or value["status"] not in JOURNAL_STATES:
            raise MissionStateError("invalid_bootstrap_journal", "bootstrap journal schema or status is invalid")
        request = self._validate_request(value["request"])
        for field in ("request_id", "request_sha256", "mission_id", "mission_fingerprint", "confirmed_generation_id", "capability_name", "capability_version"):
            if value[field] != request[field]:
                raise MissionStateError("invalid_bootstrap_journal", f"bootstrap journal {field} does not match request")
        if path.stem != value["request_id"]:
            raise MissionStateError("invalid_bootstrap_journal", "bootstrap journal filename does not match request")
        _validate_utc_timestamp(value["created_at"], "bootstrap journal created_at")
        _validate_utc_timestamp(value["updated_at"], "bootstrap journal updated_at")
        status = value["status"]
        if status in {"intent", "call_started"}:
            if any(value[field] is not None for field in ("result_sha256", "set_id", "manifest_sha256")):
                raise MissionStateError("invalid_bootstrap_journal", "early bootstrap journal has result authority")
        else:
            _validate_hex(value["result_sha256"], 64, "result_sha256")
        if status in {"prepared", "selected"}:
            if not isinstance(value["set_id"], str) or SET_ID_RE.fullmatch(value["set_id"]) is None:
                raise MissionStateError("invalid_bootstrap_journal", "prepared bootstrap set ID is invalid")
            _validate_hex(value["manifest_sha256"], 64, "manifest_sha256")
        elif value["set_id"] is not None or value["manifest_sha256"] is not None:
            raise MissionStateError("invalid_bootstrap_journal", "bootstrap set authority is premature")
        if status == "intent":
            if value["prior_status_sha256"] is not None:
                raise MissionStateError("invalid_bootstrap_journal", "intent has a prior status digest")
        else:
            _validate_hex(value["prior_status_sha256"], 64, "prior_status_sha256")
        self._assert_journal_binding(value)
        return dict(value)

    def _assert_journal_binding(self, journal: dict[str, Any]) -> None:
        request = journal["request"]
        contract = self.snapshot.contract
        confirmation = contract["public_discovery_confirmation"]
        expected = {
            "mission_id": contract["mission_id"],
            "mission_fingerprint": contract["mission_fingerprint"],
            "input_mode": TOPIC_INPUT_MODE,
            "normalized_topic": contract["normalized_topic"],
            "discovery_budget": contract["discovery_budget"],
            "output_root": str(self.manager.output_dir),
            "confirmation": {
                "confirmed_at": confirmation["confirmed_at"],
                "confirmation_source": confirmation["confirmation_source"],
            },
        }
        for field, expected_value in expected.items():
            if request[field] != expected_value:
                raise MissionStateError("foreign_bootstrap_journal", f"bootstrap request {field} differs from the active mission")
        self.manager.assert_generation_ancestor(request["confirmed_generation_id"])

    def _transition(self, path: Path, prior: dict[str, Any], status: str, **updates: Any) -> dict[str, Any]:
        if status not in JOURNAL_STATES:
            raise MissionStateError("invalid_bootstrap_transition", "unknown bootstrap transition")
        result = dict(prior)
        result.update(updates)
        result["status"] = status
        result["updated_at"] = self.now()
        result["prior_status_sha256"] = sha256_bytes(canonical_json_bytes(prior))
        self._record_journal(path, result, f"bootstrap_{status}")
        return result

    def _result_path(self, request_id: str) -> Path:
        return self.results_dir / f"{request_id}.json"

    def _read_result(self, journal: dict[str, Any]) -> dict[str, Any]:
        path = self._result_path(journal["request_id"])
        payload, raw = _read_json_exact(path, label="bootstrap result")
        if canonical_json_bytes(payload) != raw or sha256_bytes(raw) != journal["result_sha256"]:
            raise MissionStateError("bootstrap_result_digest_mismatch", "bootstrap result bytes do not match journal")
        return validate_bootstrap_outcome(payload)

    def _write_result(self, request: dict[str, Any], outcome: dict[str, Any]) -> str:
        path = self._result_path(request["request_id"])
        raw = canonical_json_bytes(outcome)
        if path.exists() or path.is_symlink():
            if stat.S_ISLNK(path.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode) or path.read_bytes() != raw:
                raise MissionStateError("bootstrap_result_collision", "existing bootstrap result differs")
        else:
            self._atomic(path, raw, "bootstrap_result")
        return sha256_bytes(raw)

    def _set_values(self, journal: dict[str, Any], outcome: dict[str, Any]) -> tuple[str, dict[str, Any], bytes, bytes]:
        outcome_bytes = canonical_json_bytes(outcome)
        identity = {
            "schema_version": BOOTSTRAP_SET_MANIFEST_SCHEMA,
            "request_id": journal["request_id"],
            "request_sha256": journal["request_sha256"],
            "result_sha256": journal["result_sha256"],
            "mission_id": journal["mission_id"],
            "mission_fingerprint": journal["mission_fingerprint"],
            "confirmed_generation_id": journal["confirmed_generation_id"],
            "capability_name": journal["capability_name"],
            "capability_version": journal["capability_version"],
        }
        set_digest = sha256_bytes(canonical_json_bytes(identity))
        set_id = f"bs-{set_digest}"
        effective_rows = normalize_seeds([row["display"] for row in outcome["selected_candidates"]]) if outcome["outcome"] == "selected" else []
        manifest = {
            **identity,
            "set_id": set_id,
            "outcome": outcome["outcome"],
            "effective_seed_rows": effective_rows,
            "artifacts": [
                {
                    "relative_path": "outcome.json",
                    "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
                    "sha256": sha256_bytes(outcome_bytes),
                    "size_bytes": len(outcome_bytes),
                }
            ],
        }
        manifest_bytes = canonical_json_bytes(manifest)
        return set_id, manifest, outcome_bytes, manifest_bytes

    def _prepare(self, journal_path: Path, journal: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
        set_id, _, outcome_bytes, manifest_bytes = self._set_values(journal, outcome)
        staging = self.sets_dir / f".staging-{set_id}"
        final = self.sets_dir / set_id
        if final.exists() or final.is_symlink():
            self._validate_set(final, expected_journal=journal)
        else:
            if staging.exists() or staging.is_symlink():
                if stat.S_ISLNK(staging.lstat().st_mode) or not stat.S_ISDIR(staging.lstat().st_mode):
                    raise MissionStateError("unsafe_bootstrap_set", "bootstrap staging set is unsafe")
            else:
                staging.mkdir(mode=0o700)
                _fsync_directory(self.sets_dir)
            actual_staging_names = {path.name for path in staging.iterdir()}
            if not actual_staging_names.issubset({"outcome.json", "manifest.json"}):
                raise MissionStateError("unexpected_bootstrap_set_files", "bootstrap staging set has unexpected members")
            if any(path.is_symlink() or not path.is_file() for path in staging.iterdir()):
                raise MissionStateError("unsafe_bootstrap_set", "bootstrap staging set member is unsafe")
            members = ((staging / "outcome.json", outcome_bytes), (staging / "manifest.json", manifest_bytes))
            for path, raw in members:
                self._crash(f"bootstrap_set:{path.name}:before_write")
                if path.exists() or path.is_symlink():
                    if stat.S_ISLNK(path.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode) or path.read_bytes() != raw:
                        raise MissionStateError("bootstrap_set_collision", "partial bootstrap set differs from expected bytes")
                else:
                    with path.open("xb") as handle:
                        handle.write(raw)
                        self._crash(f"bootstrap_set:{path.name}:after_write")
                        handle.flush()
                        os.fsync(handle.fileno())
                self._crash(f"bootstrap_set:{path.name}:after_fsync")
            self._crash("bootstrap_set:before_staging_fsync")
            _fsync_directory(staging)
            self._crash("bootstrap_set:after_staging_fsync")
            self._crash("bootstrap_set:before_final_rename")
            os.rename(staging, final)
            self._crash("bootstrap_set:after_final_rename")
            _fsync_directory(self.sets_dir)
            self._crash("bootstrap_set:after_parent_fsync")
        manifest_sha = sha256_file(final / "manifest.json")
        prepared = self._transition(
            journal_path,
            journal,
            "prepared",
            set_id=set_id,
            manifest_sha256=manifest_sha,
        )
        self._crash("bootstrap:after_prepared")
        return prepared

    def _validate_set(self, directory: Path, *, expected_journal: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if directory.is_symlink() or not directory.is_dir() or SET_ID_RE.fullmatch(directory.name) is None:
            raise MissionStateError("unsafe_bootstrap_set", "bootstrap set directory is unsafe")
        actual_names = sorted(path.name for path in directory.iterdir())
        if actual_names != ["manifest.json", "outcome.json"]:
            raise MissionStateError("unexpected_bootstrap_set_files", "bootstrap set has unexpected members")
        for path in directory.iterdir():
            if stat.S_ISLNK(path.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode):
                raise MissionStateError("unsafe_bootstrap_set", "bootstrap set member is unsafe")
        manifest, manifest_raw = _read_json_exact(directory / "manifest.json", label="bootstrap manifest")
        outcome, outcome_raw = _read_json_exact(directory / "outcome.json", label="bootstrap outcome")
        expected_keys = {
            "schema_version", "set_id", "request_id", "request_sha256", "result_sha256", "mission_id",
            "mission_fingerprint", "confirmed_generation_id", "capability_name", "capability_version",
            "outcome", "effective_seed_rows", "artifacts",
        }
        _require_exact_keys(manifest, expected_keys, "bootstrap manifest")
        if canonical_json_bytes(manifest) != manifest_raw or canonical_json_bytes(outcome) != outcome_raw:
            raise MissionStateError("noncanonical_bootstrap_set", "bootstrap set bytes are not canonical")
        validated_outcome = validate_bootstrap_outcome(outcome)
        if manifest["schema_version"] != BOOTSTRAP_SET_MANIFEST_SCHEMA or manifest["set_id"] != directory.name:
            raise MissionStateError("invalid_bootstrap_manifest", "bootstrap manifest identity is invalid")
        for field in ("request_id", "request_sha256", "result_sha256", "mission_id", "mission_fingerprint", "confirmed_generation_id", "capability_name", "capability_version"):
            if manifest[field] != expected_journal[field]:
                raise MissionStateError("foreign_bootstrap_set", f"bootstrap manifest {field} differs from journal")
        if manifest["outcome"] != validated_outcome["outcome"]:
            raise MissionStateError("invalid_bootstrap_manifest", "bootstrap manifest outcome differs")
        effective_rows = normalize_seeds([row["display"] for row in validated_outcome["selected_candidates"]]) if validated_outcome["outcome"] == "selected" else []
        if manifest["effective_seed_rows"] != effective_rows:
            raise MissionStateError("invalid_bootstrap_manifest", "bootstrap effective seed rows differ")
        expected_artifact = {
            "relative_path": "outcome.json",
            "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
            "sha256": sha256_bytes(outcome_raw),
            "size_bytes": len(outcome_raw),
        }
        if manifest["artifacts"] != [expected_artifact] or manifest["result_sha256"] != sha256_bytes(outcome_raw):
            raise MissionStateError("bootstrap_artifact_digest_mismatch", "bootstrap outcome digest differs")
        identity = {key: manifest[key] for key in (
            "schema_version", "request_id", "request_sha256", "result_sha256", "mission_id",
            "mission_fingerprint", "confirmed_generation_id", "capability_name", "capability_version",
        )}
        if manifest["set_id"] != f"bs-{sha256_bytes(canonical_json_bytes(identity))}":
            raise MissionStateError("invalid_bootstrap_manifest", "bootstrap set ID digest is invalid")
        return manifest, validated_outcome

    def _select(self, journal_path: Path, journal: dict[str, Any]) -> dict[str, Any]:
        directory = self.sets_dir / journal["set_id"]
        self._validate_set(directory, expected_journal=journal)
        pointer = {
            "schema_version": BOOTSTRAP_CURRENT_SCHEMA,
            "set_id": journal["set_id"],
            "manifest_sha256": journal["manifest_sha256"],
        }
        raw = canonical_json_bytes(pointer)
        if self.current_path.exists() or self.current_path.is_symlink():
            if stat.S_ISLNK(self.current_path.lstat().st_mode) or not stat.S_ISREG(self.current_path.lstat().st_mode) or self.current_path.read_bytes() != raw:
                raise MissionStateError("bootstrap_current_conflict", "bootstrap CURRENT differs from prepared set")
        else:
            self._crash("bootstrap:before_pointer_selection")
            self._atomic(self.current_path, raw, "bootstrap_current")
        self._crash("bootstrap:after_pointer_selection")
        return self._transition(journal_path, journal, "selected")

    def _read_current(self) -> tuple[dict[str, Any], bytes] | None:
        if not self.current_path.exists():
            return None
        pointer, raw = _read_json_exact(self.current_path, label="bootstrap CURRENT")
        _require_exact_keys(pointer, {"schema_version", "set_id", "manifest_sha256"}, "bootstrap CURRENT")
        if pointer["schema_version"] != BOOTSTRAP_CURRENT_SCHEMA or canonical_json_bytes(pointer) != raw:
            raise MissionStateError("invalid_bootstrap_current", "bootstrap CURRENT is invalid or noncanonical")
        if not isinstance(pointer["set_id"], str) or SET_ID_RE.fullmatch(pointer["set_id"]) is None:
            raise MissionStateError("invalid_bootstrap_current", "bootstrap CURRENT set ID is invalid")
        _validate_hex(pointer["manifest_sha256"], 64, "manifest_sha256")
        return pointer, raw

    def _projection(self, journal: dict[str, Any]) -> dict[str, Any]:
        if journal["status"] == "call_started":
            return {
                "attempt_state": "call_started_indeterminate",
                "outcome": None,
                "effective_seeds": [],
                "selected_candidates": [],
                "authority": None,
                "request_id": journal["request_id"],
                "set_dir": None,
            }
        outcome = self._read_result(journal) if journal["status"] in {"result_recorded", "prepared", "selected"} else None
        if journal["status"] == "prepared":
            directory = self.sets_dir / journal["set_id"]
            manifest, set_outcome = self._validate_set(directory, expected_journal=journal)
            if sha256_file(directory / "manifest.json") != journal["manifest_sha256"]:
                raise MissionStateError("bootstrap_manifest_digest_mismatch", "prepared bootstrap manifest digest differs")
            if set_outcome != outcome or manifest["outcome"] != outcome["outcome"]:
                raise MissionStateError("bootstrap_prepared_outcome_mismatch", "prepared set and recorded outcome differ")
        if journal["status"] == "selected":
            pointer_entry = self._read_current()
            if pointer_entry is None:
                raise MissionStateError("missing_bootstrap_current", "selected bootstrap journal has no CURRENT")
            pointer, _ = pointer_entry
            if pointer["set_id"] != journal["set_id"] or pointer["manifest_sha256"] != journal["manifest_sha256"]:
                raise MissionStateError("bootstrap_current_mismatch", "bootstrap CURRENT and selected journal differ")
            directory = self.sets_dir / journal["set_id"]
            manifest, outcome = self._validate_set(directory, expected_journal=journal)
            if sha256_file(directory / "manifest.json") != journal["manifest_sha256"]:
                raise MissionStateError("bootstrap_manifest_digest_mismatch", "selected bootstrap manifest digest differs")
            effective = [row["display"] for row in manifest["effective_seed_rows"]]
            authority = None
            if outcome["outcome"] == "selected":
                authority = {
                    "schema_version": TOPIC_BOOTSTRAP_AUTHORITY_SCHEMA,
                    "set_id": journal["set_id"],
                    "manifest_sha256": journal["manifest_sha256"],
                    "request_id": journal["request_id"],
                    "request_sha256": journal["request_sha256"],
                    "capability_name": journal["capability_name"],
                    "capability_version": journal["capability_version"],
                    "confirmed_generation_id": journal["confirmed_generation_id"],
                    "effective_normalized_seed_keys": [row["key"] for row in manifest["effective_seed_rows"]],
                }
            return {
                "attempt_state": "selected_complete",
                "outcome": outcome["outcome"],
                "effective_seeds": effective,
                "selected_candidates": outcome["selected_candidates"],
                "authority": authority,
                "request_id": journal["request_id"],
                "set_dir": str(directory),
            }
        state = journal["status"]
        return {
            "attempt_state": state,
            "outcome": outcome["outcome"] if state == "prepared" and outcome else None,
            "effective_seeds": [],
            "selected_candidates": [],
            "authority": None,
            "request_id": journal["request_id"],
            "set_dir": str(self.sets_dir / journal["set_id"]) if journal.get("set_id") else None,
        }

    def observe(self) -> dict[str, Any]:
        self._validate_root(create=False)
        transactions = self._scan_transactions()
        if len(transactions) > 1:
            raise MissionStateError("multiple_bootstrap_attempts", "M17 permits exactly one immutable bootstrap attempt")
        if not transactions:
            unexpected = {
                "results": [path.name for path in self.results_dir.iterdir() if not self._safe_temp(path)],
                "sets": [path.name for path in self.sets_dir.iterdir()],
                "history": [path.name for path in self.history_dir.iterdir()],
            }
            if any(unexpected.values()) or self._read_current() is not None:
                raise MissionStateError(
                    "orphan_bootstrap_evidence",
                    "bootstrap evidence exists without a journaled attempt",
                    details=unexpected,
                )
            return {
                "attempt_state": "not_started",
                "outcome": None,
                "effective_seeds": [],
                "selected_candidates": [],
                "authority": None,
                "request_id": None,
                "set_dir": None,
            }
        _, journal = transactions[0]
        self._validate_attempt_paths(journal)
        pointer_entry = self._read_current()
        if pointer_entry is not None and journal["status"] not in {"prepared", "selected"}:
            raise MissionStateError("premature_bootstrap_current", "bootstrap CURRENT exists before preparation")
        return self._projection(journal)

    def _validate_attempt_paths(self, journal: dict[str, Any]) -> None:
        has_recorded_result = journal["status"] in {"result_recorded", "prepared", "selected"}
        expected_result_name = f"{journal['request_id']}.json"
        expected_result_names = {expected_result_name} if has_recorded_result else set()
        actual_result_names = {path.name for path in self.results_dir.iterdir() if not self._safe_temp(path)}
        if journal["status"] == "call_started" and actual_result_names in (set(), {expected_result_name}):
            expected_result_names = actual_result_names
        if actual_result_names != expected_result_names:
            raise MissionStateError("orphan_bootstrap_result", "bootstrap result files are not exhaustively journaled")

        entries = [path for path in self.sets_dir.iterdir()]
        if not has_recorded_result:
            if entries:
                raise MissionStateError("orphan_bootstrap_set", "bootstrap set exists before a recorded result")
            if self._read_current() is not None:
                raise MissionStateError("premature_bootstrap_current", "bootstrap CURRENT exists before preparation")
            return
        outcome = self._read_result(journal)
        set_id, _, _, _ = self._set_values(journal, outcome)
        expected_final = self.sets_dir / set_id
        expected_staging = self.sets_dir / f".staging-{set_id}"
        actual_paths = set(entries)
        if journal["status"] == "result_recorded":
            allowed = {expected_final, expected_staging}
            if not actual_paths.issubset(allowed) or len(actual_paths) > 1:
                raise MissionStateError("orphan_bootstrap_set", "result-recorded bootstrap set residue is ambiguous or foreign")
        else:
            if actual_paths != {expected_final}:
                raise MissionStateError("orphan_bootstrap_set", "prepared bootstrap set is missing, partial, or foreign")
            if journal["set_id"] != set_id:
                raise MissionStateError("bootstrap_set_identity_mismatch", "journal set ID differs from recorded result")
        pointer = self._read_current()
        if journal["status"] in {"result_recorded", "prepared"} and pointer is not None:
            if journal["status"] != "prepared" or pointer[0]["set_id"] != set_id or pointer[0]["manifest_sha256"] != journal["manifest_sha256"]:
                raise MissionStateError("premature_bootstrap_current", "bootstrap CURRENT exists before an exact prepared selection")
        if journal["status"] == "selected" and pointer is None:
            raise MissionStateError("missing_bootstrap_current", "selected bootstrap journal has no CURRENT")

    def validate_selected(self, expected_authority: dict[str, Any] | None = None) -> dict[str, Any]:
        selected = self.observe()
        if selected["attempt_state"] != "selected_complete" or selected["outcome"] != "selected":
            raise MissionStateError("bootstrap_selection_required", "a validated selected bootstrap set is required")
        if expected_authority is not None and selected["authority"] != expected_authority:
            raise MissionStateError("stale_bootstrap_authority", "expected bootstrap authority is not current")
        return selected

    def advance(self, capability: MissionBootstrapCapability) -> dict[str, Any]:
        self._validate_root(create=False)
        transactions = self._scan_transactions()
        if len(transactions) > 1:
            raise MissionStateError("multiple_bootstrap_attempts", "M17 permits exactly one immutable bootstrap attempt")
        if not transactions:
            if self._read_current() is not None:
                raise MissionStateError("orphan_bootstrap_current", "bootstrap CURRENT exists without a journal")
            request = self._request(capability)
            journal = self._new_journal(request)
            journal_path = self.transactions_dir / f"{request['request_id']}.json"
            self._crash("bootstrap:before_intent")
            self._record_journal(journal_path, journal, "bootstrap_intent")
            self._crash("bootstrap:after_intent")
        else:
            journal_path, journal = transactions[0]
            self._validate_attempt_paths(journal)
            if journal["status"] != "selected":
                requested = self._request(capability)
                recorded = journal["request"]
                invariant_fields = {
                    "schema_version", "mission_id", "mission_fingerprint", "input_mode",
                    "normalized_topic", "discovery_budget", "output_root", "confirmation",
                    "capability_name", "capability_version",
                }
                if any(requested[field] != recorded[field] for field in invariant_fields):
                    raise MissionStateError("bootstrap_capability_mismatch", "ordinary resume cannot change bootstrap capability identity")
                self.manager.assert_generation_ancestor(recorded["confirmed_generation_id"])

        while True:
            if journal["status"] == "intent":
                self._crash("bootstrap:before_call_started")
                journal = self._transition(journal_path, journal, "call_started")
                self._crash("bootstrap:after_call_started")
                try:
                    returned = capability.run(dict(journal["request"]))
                    self._crash("bootstrap:after_capability_return")
                    outcome = validate_bootstrap_outcome(returned)
                except MissionStateError as exc:
                    raise MissionStateError(
                        "bootstrap_call_indeterminate",
                        "bootstrap capability returned an invalid closed outcome; ordinary resume cannot retry",
                        details={"request_id": journal["request_id"], "cause": exc.code},
                    ) from exc
                except Exception as exc:
                    raise MissionStateError(
                        "bootstrap_call_indeterminate",
                        "bootstrap capability may have run; ordinary resume cannot retry",
                        details={"request_id": journal["request_id"], "cause": type(exc).__name__},
                    ) from exc
                result_sha = self._write_result(journal["request"], outcome)
                journal = self._transition(journal_path, journal, "result_recorded", result_sha256=result_sha)
                self._crash("bootstrap:after_result_recorded")
                continue
            if journal["status"] == "call_started":
                raise MissionStateError(
                    "bootstrap_call_indeterminate",
                    "bootstrap capability may have run; ordinary resume cannot retry",
                    details={"request_id": journal["request_id"]},
                )
            if journal["status"] == "result_recorded":
                outcome = self._read_result(journal)
                journal = self._prepare(journal_path, journal, outcome)
                continue
            if journal["status"] == "prepared":
                pointer_entry = self._read_current()
                if pointer_entry is not None:
                    pointer, _ = pointer_entry
                    if pointer["set_id"] != journal["set_id"] or pointer["manifest_sha256"] != journal["manifest_sha256"]:
                        raise MissionStateError("bootstrap_current_mismatch", "bootstrap CURRENT differs from prepared journal")
                    self._crash("bootstrap:before_selected_reconciliation")
                    journal = self._transition(journal_path, journal, "selected")
                    self._crash("bootstrap:after_selected_reconciliation")
                else:
                    journal = self._select(journal_path, journal)
                continue
            return self._projection(journal)
