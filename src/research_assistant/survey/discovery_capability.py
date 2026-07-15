from __future__ import annotations

import hashlib
import os
import stat
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.discovery_quality import (
    evaluate_discovery_quality,
    arxiv_version,
    informative_tokens,
    normalize_arxiv_id,
    normalize_openalex_id,
    normalized_title,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    normalize_text,
)


ACCEPTED_BODY_SCHEMA = "ra-survey-m20-accepted-body-v1"
BODY_REPLAY_SCHEMA = "ra-survey-m20-body-replay-v2"
IDENTITY_OUTCOME_SCHEMA = "ra-survey-m20-identity-outcome-v3"
FRONTIER_OUTCOME_SCHEMA = "ra-survey-m20-frontier-outcome-v2"
CASE_OUTCOME_SCHEMA = "ra-survey-m20-case-outcome-v3"
AUTOMATON_SCHEMA = "ra-survey-m20-outcome-automaton-v3"

IDENTITY_OUTCOMES = {
    "selected",
    "empty",
    "ambiguous",
    "unavailable",
    "capped",
    "boundary_invalid",
}
FRONTIER_OUTCOMES = {
    "observed_results",
    "empty_observed",
    "provider_unavailable",
    "capped",
    "not_observed",
    "boundary_invalid",
    "not_dispatched_due_to_veto",
}
REQUEST_STATUSES = {"available", "unavailable", "boundary_invalid"}
CASE_KINDS = {"topic_bootstrap", "explicit_arxiv_seed", "explicit_openalex"}
BODY_RECORD_KEYS = {
    "schema_version",
    "request_binding_sha256",
    "relative_path",
    "size_bytes",
    "sha256",
    "accepted_body_cap_bytes",
    "content_kind",
    "normalized_payload_sha256",
}
IDENTITY_REQUEST_KEYS = {
    "request_binding_sha256",
    "provider",
    "required",
    "status",
    "envelope_complete",
    "cap_exceeded",
    "body_sha256",
    "normalized_payload_sha256",
    "records",
    "malformed_row_sha256s",
    "malformed_row_count",
}
IDENTITY_OUTCOME_KEYS = {
    "schema_version",
    "case_kind",
    "expected_identifier",
    "topic",
    "outcome",
    "selected_candidate_id",
    "selected_identifier",
    "request_states",
    "request_bindings",
    "matching_candidate_ids",
    "competing_candidate_ids",
    "excluded_candidate_ids",
    "conflict_ids",
    "available_request_count",
    "unavailable_request_count",
    "boundary_invalid_request_count",
    "cap_evidence_count",
    "malformed_row_count",
    "identity_evidence_sha256",
}
FRONTIER_OUTCOME_KEYS = {
    "schema_version",
    "direction",
    "origin_request_binding_sha256",
    "origin_body_sha256",
    "origin_normalized_payload_sha256",
    "outcome",
    "target_rows",
    "summary",
    "attempt_risk_id",
    "global_veto",
}
FRONTIER_SUMMARY_KEYS = {
    "returned_target_count",
    "unique_valid_target_count",
    "admitted_target_count",
    "omitted_by_cap_target_count",
    "identity_unresolved_target_count",
    "unobserved_provider_remainder_count",
    "reported_total",
    "continuation_visible",
}
TARGET_ROW_KEYS = {
    "provider_list_index",
    "normalized_target_id",
    "duplicate_of_provider_list_index",
    "origin_body_sha256",
    "disposition",
}
TARGET_DISPOSITIONS = {
    "admitted",
    "omitted_by_cap",
    "duplicate_target",
    "malformed_target",
    "not_admitted_identity_unresolved",
    "not_admitted_boundary_invalid",
}
IDENTITY_PROVIDERS = {"arxiv", "openalex"}
FRONTIER_TARGET_CAP = 10
ACCEPTED_BODY_CAP_BYTES = 2_000_000
TOTAL_ACCEPTED_BODY_CAP_BYTES = 10_000_000
NORMALIZED_RESPONSE_KEYS = {
    "identity_view_status",
    "identity_records",
    "malformed_row_sha256s",
    "identity_envelope_complete",
    "identity_cap_exceeded",
    "frontier_view_status",
    "frontier_target_ids",
    "frontier_reported_total",
    "frontier_continuation_visible",
}


def _fail(code: str, message: str) -> None:
    raise MissionStateError(code, message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _require_sha256(value: Any, field: str) -> str:
    if not _is_sha256(value):
        _fail("m20_invalid_digest", f"{field} must be lowercase SHA-256")
    return value


def _require_exact_dict(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _fail("m20_invalid_schema", f"{field} keys are not exact")
    return value


def _require_string_list(value: Any, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or value != sorted(set(value))
    ):
        _fail("m20_invalid_schema", f"{field} must be unique and sorted")
    return list(value)


def _validate_root(root: Path) -> Path:
    if not isinstance(root, Path) or not root.is_absolute():
        _fail("m20_invalid_body_root", "accepted-body root must be absolute")
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        _fail("m20_invalid_body_root", "accepted-body root must already exist")
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
        _fail("m20_invalid_body_root", "accepted-body root must be a regular directory")
    if root.resolve(strict=True) != root:
        _fail("m20_invalid_body_root", "accepted-body root must be canonical")
    return root


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_accepted_body(
    root: Path,
    *,
    request_binding_sha256: str,
    body: bytes,
    accepted_body_cap_bytes: int = ACCEPTED_BODY_CAP_BYTES,
) -> dict[str, Any]:
    """Write one accepted public-metadata body once, before parser promotion."""

    root = _validate_root(root)
    binding = _require_sha256(request_binding_sha256, "request binding")
    if accepted_body_cap_bytes != ACCEPTED_BODY_CAP_BYTES:
        _fail("m20_invalid_body_cap", "accepted-body cap differs from the frozen per-request cap")
    if not isinstance(body, bytes):
        _fail("m20_invalid_body", "accepted body must be bytes")
    if len(body) > accepted_body_cap_bytes:
        _fail("m20_body_cap_exceeded", "accepted body exceeds its byte cap")

    body_dir = root / "accepted_bodies"
    try:
        body_dir.mkdir(mode=0o700)
        _fsync_directory(root)
    except FileExistsError:
        body_stat = body_dir.lstat()
        if not stat.S_ISDIR(body_stat.st_mode) or stat.S_ISLNK(body_stat.st_mode):
            _fail("m20_invalid_body_root", "accepted-body directory is not regular")
    if body_dir.resolve(strict=True) != body_dir:
        _fail("m20_invalid_body_root", "accepted-body directory must be canonical")

    relative = Path("accepted_bodies") / f"request-{binding}.body"
    path = root / relative
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _fail("m20_body_exists", "accepted body already exists")
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    file_stat = path.lstat()
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
        _fail("m20_invalid_body_artifact", "accepted body must be a single-link regular file")
    _fsync_directory(body_dir)
    return {
        "schema_version": ACCEPTED_BODY_SCHEMA,
        "request_binding_sha256": binding,
        "relative_path": relative.as_posix(),
        "size_bytes": len(body),
        "sha256": _sha256(body),
        "accepted_body_cap_bytes": accepted_body_cap_bytes,
        "content_kind": "public_metadata_response_body",
        "normalized_payload_sha256": None,
    }


def bind_normalized_payload(
    body_record: dict[str, Any],
    normalized_payload: Any,
) -> dict[str, Any]:
    record = _validate_body_record(body_record, allow_unbound=True)
    if record["normalized_payload_sha256"] is not None:
        _fail("m20_body_already_bound", "accepted body already has a normalized binding")
    normalized = _validate_normalized_response(normalized_payload)
    return {
        **record,
        "normalized_payload_sha256": _sha256(canonical_json_bytes(normalized)),
    }


def _validate_body_record(
    value: Any,
    *,
    allow_unbound: bool = False,
) -> dict[str, Any]:
    row = _require_exact_dict(value, BODY_RECORD_KEYS, "accepted-body record")
    if row["schema_version"] != ACCEPTED_BODY_SCHEMA:
        _fail("m20_invalid_body_record", "accepted-body schema is invalid")
    _require_sha256(row["request_binding_sha256"], "request binding")
    _require_sha256(row["sha256"], "accepted body")
    normalized = row["normalized_payload_sha256"]
    if normalized is None:
        if not allow_unbound:
            _fail("m20_unbound_body_record", "accepted body lacks normalized binding")
    else:
        _require_sha256(normalized, "normalized payload")
    expected_path = f"accepted_bodies/request-{row['request_binding_sha256']}.body"
    if row["relative_path"] != expected_path:
        _fail("m20_invalid_body_record", "accepted-body path differs from request binding")
    if (
        type(row["size_bytes"]) is not int
        or row["size_bytes"] < 0
        or type(row["accepted_body_cap_bytes"]) is not int
        or row["accepted_body_cap_bytes"] != ACCEPTED_BODY_CAP_BYTES
        or row["size_bytes"] > row["accepted_body_cap_bytes"]
        or row["content_kind"] != "public_metadata_response_body"
    ):
        _fail("m20_invalid_body_record", "accepted-body size or kind is invalid")
    return dict(row)


def replay_accepted_body(
    root: Path,
    *,
    body_record: dict[str, Any],
    parser: Callable[[bytes], Any],
) -> dict[str, Any]:
    root = _validate_root(root)
    record = _validate_body_record(body_record)
    path = root / record["relative_path"]
    try:
        file_stat = path.lstat()
    except FileNotFoundError:
        _fail("m20_body_missing", "accepted body is missing")
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or stat.S_ISLNK(file_stat.st_mode)
        or file_stat.st_nlink != 1
        or path.resolve(strict=True).parent != (root / "accepted_bodies")
    ):
        _fail("m20_invalid_body_artifact", "accepted body is not a confined regular file")
    raw = path.read_bytes()
    if len(raw) != record["size_bytes"] or len(raw) > record["accepted_body_cap_bytes"]:
        _fail("m20_body_replay_mismatch", "accepted-body size differs from its record")
    if _sha256(raw) != record["sha256"]:
        _fail("m20_body_replay_mismatch", "accepted-body digest differs from its record")
    try:
        normalized = parser(raw)
        normalized = _validate_normalized_response(normalized)
        normalized_sha256 = _sha256(canonical_json_bytes(normalized))
    except MissionStateError:
        raise
    except Exception as exc:
        raise MissionStateError(
            "m20_body_parser_failure",
            "accepted-body parser failed during replay",
        ) from exc
    if normalized_sha256 != record["normalized_payload_sha256"]:
        _fail("m20_normalized_replay_mismatch", "normalized payload differs on replay")
    return {
        "schema_version": BODY_REPLAY_SCHEMA,
        "status": "passed",
        "request_binding_sha256": record["request_binding_sha256"],
        "accepted_body_sha256": record["sha256"],
        "normalized_payload_sha256": normalized_sha256,
        "normalized_payload": normalized,
        "size_bytes": len(raw),
    }


def _validate_normalized_response(value: Any) -> dict[str, Any]:
    row = _require_exact_dict(value, NORMALIZED_RESPONSE_KEYS, "normalized provider response")
    if row["identity_view_status"] not in {"observed", "not_applicable"}:
        _fail("m20_invalid_normalized_response", "normalized identity view status is invalid")
    if row["frontier_view_status"] not in {"observed", "boundary_invalid", "not_applicable"}:
        _fail("m20_invalid_normalized_response", "normalized frontier view status is invalid")
    if not isinstance(row["identity_records"], list) or not isinstance(row["frontier_target_ids"], list):
        _fail("m20_invalid_normalized_response", "normalized provider response lists are invalid")
    if type(row["identity_envelope_complete"]) is not bool or type(row["identity_cap_exceeded"]) is not bool:
        _fail("m20_invalid_normalized_response", "normalized identity flags are invalid")
    malformed = _require_string_list(row["malformed_row_sha256s"], "normalized malformed row digests")
    if any(not _is_sha256(value) for value in malformed):
        _fail("m20_invalid_normalized_response", "normalized malformed row evidence is invalid")
    reported_total = row["frontier_reported_total"]
    if reported_total is not None and (type(reported_total) is not int or reported_total < 0):
        _fail("m20_invalid_normalized_response", "normalized frontier total is invalid")
    if type(row["frontier_continuation_visible"]) is not bool:
        _fail("m20_invalid_normalized_response", "normalized frontier continuation flag is invalid")
    if row["identity_view_status"] == "not_applicable" and (
        row["identity_records"]
        or malformed
        or not row["identity_envelope_complete"]
        or row["identity_cap_exceeded"]
    ):
        _fail("m20_invalid_normalized_response", "inapplicable identity view contains evidence")
    if row["frontier_view_status"] == "not_applicable" and (
        row["frontier_target_ids"]
        or reported_total is not None
        or row["frontier_continuation_visible"]
    ):
        _fail("m20_invalid_normalized_response", "inapplicable frontier view contains evidence")
    return {
        **row,
        "identity_records": list(row["identity_records"]),
        "malformed_row_sha256s": malformed,
        "frontier_target_ids": list(row["frontier_target_ids"]),
    }


def validate_accepted_body_inventory(
    root: Path,
    *,
    body_records: list[dict[str, Any]],
) -> dict[str, Any]:
    root = _validate_root(root)
    if not isinstance(body_records, list):
        _fail("m20_invalid_body_inventory", "accepted-body records must be a list")
    records = [_validate_body_record(row, allow_unbound=True) for row in body_records]
    expected = {row["relative_path"]: row for row in records}
    if len(expected) != len(records):
        _fail("m20_invalid_body_inventory", "accepted-body records are not unique")
    if sum(row["size_bytes"] for row in records) > TOTAL_ACCEPTED_BODY_CAP_BYTES:
        _fail("m20_invalid_body_inventory", "accepted-body inventory exceeds the frozen total cap")
    body_dir = root / "accepted_bodies"
    if not body_dir.exists():
        actual: set[str] = set()
    else:
        if body_dir.resolve(strict=True) != body_dir or not body_dir.is_dir():
            _fail("m20_invalid_body_inventory", "accepted-body directory is unsafe")
        actual = {
            path.relative_to(root).as_posix()
            for path in body_dir.iterdir()
        }
    if actual != set(expected):
        _fail("m20_invalid_body_inventory", "accepted-body inventory differs from its records")
    for relative, record in expected.items():
        path = root / relative
        file_stat = path.lstat()
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
            _fail("m20_invalid_body_inventory", "accepted-body inventory contains an unsafe file")
        raw = path.read_bytes()
        if len(raw) != record["size_bytes"] or _sha256(raw) != record["sha256"]:
            _fail("m20_invalid_body_inventory", "accepted-body inventory bytes differ")
    return {
        "schema_version": "ra-survey-m20-accepted-body-inventory-v1",
        "status": "passed",
        "record_count": len(records),
        "request_bindings": sorted(row["request_binding_sha256"] for row in records),
        "records": sorted(records, key=canonical_json_bytes),
    }


def classify_identity_outcome(
    *,
    case_kind: str,
    expected_identifier: str | None,
    topic: str | None,
    request_states: list[dict[str, Any]],
) -> dict[str, Any]:
    if case_kind not in CASE_KINDS:
        _fail("m20_invalid_identity_case", "identity case kind is not closed")
    if not isinstance(request_states, list) or not request_states:
        _fail("m20_invalid_identity_state", "identity requests must be a nonempty list")
    normalized_expected = _normalize_expected_identifier(case_kind, expected_identifier)
    normalized_topic = _normalize_topic(case_kind, topic)
    rows = [
        _validate_identity_request(
            row,
            case_kind=case_kind,
            topic=normalized_topic,
        )
        for row in request_states
    ]
    if any(not row["required"] for row in rows):
        _fail("m20_invalid_identity_state", "current M20 identity requests must all be required")
    bindings = [row["request_binding_sha256"] for row in rows]
    if bindings != sorted(set(bindings)):
        _fail("m20_invalid_identity_state", "identity request bindings must be unique and sorted")
    providers = [row["provider"] for row in rows]
    expected_providers = {
        "explicit_arxiv_seed": ["arxiv"],
        "explicit_openalex": ["openalex"],
        "topic_bootstrap": ["arxiv", "openalex"],
    }[case_kind]
    if sorted(providers) != expected_providers:
        _fail("m20_invalid_identity_state", "identity provider topology is invalid")

    boundary_rows = [
        row for row in rows
        if row["status"] == "boundary_invalid" or not row["envelope_complete"]
    ]
    boundary = bool(boundary_rows)
    capped = any(row["cap_exceeded"] for row in rows)
    available = [
        row for row in rows
        if row["status"] == "available" and row["envelope_complete"]
    ]
    unavailable = [row for row in rows if row["status"] == "unavailable"]
    records = [record for row in available for record in row["records"]]
    evidence = _derive_identity_evidence(
        case_kind=case_kind,
        expected_identifier=normalized_expected,
        topic=normalized_topic,
        records=records,
    )
    matching = evidence["matching_candidate_ids"]
    competing = evidence["competing_candidate_ids"]
    excluded = evidence["excluded_candidate_ids"]
    conflicts = evidence["conflict_ids"]

    selected: str | None = None
    selected_identifier: str | None = None
    if boundary:
        outcome = "boundary_invalid"
    elif capped:
        outcome = "capped"
    elif len(unavailable) == len(rows):
        outcome = "unavailable"
    elif not matching and not competing and not conflicts:
        outcome = "empty"
    elif case_kind == "topic_bootstrap" and unavailable:
        outcome = "ambiguous"
    elif len(matching) == 1 and not competing and not conflicts:
        outcome = "selected"
        selected = matching[0]
        selected_identifier = evidence["selected_identifier"]
    else:
        outcome = "ambiguous"
    result = {
        "schema_version": IDENTITY_OUTCOME_SCHEMA,
        "case_kind": case_kind,
        "expected_identifier": normalized_expected,
        "topic": normalized_topic,
        "outcome": outcome,
        "selected_candidate_id": selected,
        "selected_identifier": selected_identifier,
        "request_states": rows,
        "request_bindings": bindings,
        "matching_candidate_ids": matching,
        "competing_candidate_ids": competing,
        "excluded_candidate_ids": excluded,
        "conflict_ids": conflicts,
        "available_request_count": len(available),
        "unavailable_request_count": len(unavailable),
        "boundary_invalid_request_count": len(boundary_rows),
        "cap_evidence_count": sum(1 for row in rows if row["cap_exceeded"]),
        "malformed_row_count": sum(row["malformed_row_count"] for row in rows),
        "identity_evidence_sha256": evidence["identity_evidence_sha256"],
    }
    return result


def _normalize_expected_identifier(case_kind: str, value: Any) -> str | None:
    if case_kind == "topic_bootstrap":
        if value is not None:
            _fail("m20_invalid_identity_state", "topic identity cannot have an expected identifier")
        return None
    if value is None:
        _fail("m20_invalid_identity_state", "explicit identity requires an expected identifier")
    try:
        if case_kind == "explicit_arxiv_seed":
            normalized = normalize_arxiv_id(value)
            return f"arxiv:{normalized}" if normalized is not None else None
        normalized = normalize_openalex_id(value)
        return f"openalex:{normalized.casefold()}" if normalized is not None else None
    except MissionStateError as exc:
        raise MissionStateError("m20_invalid_identity_state", "expected identifier is invalid") from exc


def _normalize_topic(case_kind: str, value: Any) -> str | None:
    if case_kind != "topic_bootstrap":
        if value is not None:
            _fail("m20_invalid_identity_state", "explicit identity cannot have a topic predicate")
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail("m20_invalid_identity_state", "topic predicate is invalid")
    return " ".join(value.split())


def _derive_identity_evidence(
    *,
    case_kind: str,
    expected_identifier: str | None,
    topic: str | None,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    seed = expected_identifier if expected_identifier is not None else topic
    assert seed is not None
    try:
        quality = evaluate_discovery_quality(
            topic=topic or seed,
            seeds=[seed],
            records=records,
            max_records=max(1, len(records)),
        )
    except MissionStateError as exc:
        raise MissionStateError("m20_invalid_identity_state", "identity record evidence is invalid") from exc
    resolution = quality["identity_resolution"]["seed_resolutions"][0]
    components = quality["identity_resolution"]["components"]
    eligible_ids = sorted(
        component["paper_id"]
        for component in components
        if component["component_status"] == "eligible"
    )
    conflicts = sorted(
        component["conflict_id"]
        for component in components
        if component["component_status"] == "identity_conflict"
    )
    selected = resolution["selected_paper_id"]
    eligible_by_id = {
        component["paper_id"]: component
        for component in components
        if component["component_status"] == "eligible"
    }
    if case_kind == "topic_bootstrap":
        assert topic is not None
        topic_key = normalized_title(topic)
        informative_count = len(informative_tokens(topic))
        scores = {
            paper_id: round(
                SequenceMatcher(None, topic_key, component["title_key"]).ratio(),
                12,
            )
            for paper_id, component in eligible_by_id.items()
        }
        exact = sorted(
            paper_id
            for paper_id, component in eligible_by_id.items()
            if component["title_key"] == topic_key
        )
        qualifying: list[str]
        if len(exact) == 1:
            selected = exact[0]
            qualifying = exact
        elif len(exact) > 1:
            selected = None
            qualifying = exact
        elif scores:
            ranked = sorted(scores, key=lambda paper_id: (-scores[paper_id], paper_id))
            top_id = ranked[0]
            runner_up = max(
                (score for paper_id, score in scores.items() if paper_id != top_id),
                default=0.0,
            )
            selected = (
                top_id
                if scores[top_id] >= 0.96
                and informative_count >= 3
                and scores[top_id] - runner_up >= 0.08
                else None
            )
            qualifying = [top_id] if selected is not None else [
                paper_id
                for paper_id in ranked
                if scores[paper_id] >= 0.96
            ]
        else:
            selected = None
            qualifying = []
        matching = [selected] if selected is not None else []
        competing = qualifying if selected is None else []
        excluded = sorted(set(eligible_ids) - set(qualifying))
    else:
        matching = [selected] if selected is not None else []
        competing = [candidate for candidate in eligible_ids if candidate != selected]
        excluded = []
    selected_identifier = resolution["selected_identifier"]
    if case_kind == "explicit_arxiv_seed" and selected is not None:
        observed = eligible_by_id[selected]["arxiv_ids"]
        if observed:
            canonical_arxiv = max(observed, key=lambda value: (arxiv_version(value), value))
            selected_identifier = f"arxiv:{canonical_arxiv}"
    evidence_payload = {
        "case_kind": case_kind,
        "expected_identifier": expected_identifier,
        "topic": topic,
        "input_records": quality["identity_resolution"]["input_records"],
        "components": components,
        "exact_duplicates": quality["identity_resolution"]["exact_duplicates"],
        "possible_duplicates": quality["identity_resolution"]["possible_duplicates"],
        "resolution": resolution,
    }
    return {
        "matching_candidate_ids": matching,
        "competing_candidate_ids": competing,
        "excluded_candidate_ids": excluded,
        "conflict_ids": conflicts,
        "selected_identifier": selected_identifier,
        "identity_evidence_sha256": _sha256(canonical_json_bytes(evidence_payload)),
    }


def _validate_identity_request(
    value: Any,
    *,
    case_kind: str,
    topic: str | None,
) -> dict[str, Any]:
    row = _require_exact_dict(value, IDENTITY_REQUEST_KEYS, "identity request state")
    _require_sha256(row["request_binding_sha256"], "identity request binding")
    if row["provider"] not in IDENTITY_PROVIDERS:
        _fail("m20_invalid_identity_state", "identity provider is invalid")
    if type(row["required"]) is not bool or type(row["envelope_complete"]) is not bool:
        _fail("m20_invalid_identity_state", "identity booleans are invalid")
    if row["status"] not in REQUEST_STATUSES or type(row["cap_exceeded"]) is not bool:
        _fail("m20_invalid_identity_state", "identity request status is invalid")
    if type(row["malformed_row_count"]) is not int or row["malformed_row_count"] < 0:
        _fail("m20_invalid_identity_state", "malformed row count is invalid")
    malformed = _require_string_list(row["malformed_row_sha256s"], "malformed row digests")
    if any(not _is_sha256(value) for value in malformed) or row["malformed_row_count"] != len(malformed):
        _fail("m20_invalid_identity_state", "malformed row evidence is invalid")
    body_sha = row["body_sha256"]
    payload_sha = row["normalized_payload_sha256"]
    if body_sha is not None:
        _require_sha256(body_sha, "identity body")
    if payload_sha is not None:
        _require_sha256(payload_sha, "identity normalized payload")
    if not isinstance(row["records"], list):
        _fail("m20_invalid_identity_state", "identity records must be a list")
    expected_topic_flag = case_kind == "topic_bootstrap"
    expected_topic_key = (
        normalize_text(topic, field="topic")["key"]
        if topic is not None
        else None
    )
    for record in row["records"]:
        if not isinstance(record, dict) or record.get("providers") != [row["provider"]]:
            _fail("m20_invalid_identity_state", "identity record provider differs from its request")
        provider_records = record.get("provider_records")
        provenance = record.get("query_provenance")
        if (
            not isinstance(provider_records, list)
            or not provider_records
            or any(not isinstance(item, dict) for item in provider_records)
            or any(item.get("provider") != row["provider"] for item in provider_records)
            or any(item.get("query_kind") != "identity_resolution" for item in provider_records)
            or
            not isinstance(provenance, list)
            or not provenance
            or any(item.get("topic_query") is not expected_topic_flag for item in provenance if isinstance(item, dict))
            or any(not isinstance(item, dict) for item in provenance)
            or any(item.get("provider") != row["provider"] for item in provenance)
            or any(item.get("query_kind") != "identity_resolution" for item in provenance)
            or any(
                item.get("normalized_seed_key") != expected_topic_key
                for item in provenance
            )
        ):
            _fail("m20_invalid_identity_state", "identity record query role differs from its case")
        roles = record.get("roles")
        if (
            not isinstance(roles, list)
            or not roles
            or not set(roles) <= {"seed", "direct_method"}
        ):
            _fail("m20_invalid_identity_state", "navigation record cannot enter identity evidence")
        if row["provider"] == "openalex":
            try:
                top_level_id = normalize_openalex_id(record.get("openalex_id"))
                source_ids = {
                    normalize_openalex_id(item.get("source_id"))
                    for item in provider_records
                }
            except MissionStateError as exc:
                raise MissionStateError("m20_invalid_identity_state", "OpenAlex identity source is invalid") from exc
        else:
            try:
                top_level_id = normalize_arxiv_id(record.get("arxiv_id"))
                source_ids = {
                    normalize_arxiv_id(item.get("source_id"))
                    for item in provider_records
                }
            except MissionStateError as exc:
                raise MissionStateError("m20_invalid_identity_state", "arXiv identity source is invalid") from exc
        if top_level_id is None or source_ids != {top_level_id}:
            _fail("m20_invalid_identity_state", "identity record source differs from its top-level identifier")
    if row["status"] == "available":
        if body_sha is None or payload_sha is None:
            _fail("m20_invalid_identity_state", "available identity request lacks body bindings")
    elif row["status"] == "unavailable" and (
        body_sha is not None or payload_sha is not None or row["records"]
    ):
        _fail("m20_invalid_identity_state", "non-available identity request has response content")
    elif row["status"] == "boundary_invalid" and (
        payload_sha is not None or row["records"]
    ):
        _fail("m20_invalid_identity_state", "boundary-invalid identity cannot carry normalized content")
    if row["status"] != "available" and row["cap_exceeded"]:
        _fail("m20_invalid_identity_state", "non-available identity request cannot be capped")
    return dict(row)


def classify_frontier_attempt(
    *,
    direction: str,
    origin_request_binding_sha256: str,
    origin_body_sha256: str | None,
    origin_normalized_payload_sha256: str | None,
    request_status: str,
    body_integrity_valid: bool,
    target_ids: list[Any],
    reported_total: int | None,
    continuation_visible: bool,
    origin_identity_outcome: str,
    dispatched: bool = True,
    derived_from_identity_request: bool = False,
    target_cap: int = FRONTIER_TARGET_CAP,
) -> dict[str, Any]:
    if direction not in {"backward", "forward"}:
        _fail("m20_invalid_frontier_state", "frontier direction is not closed")
    binding = _require_sha256(origin_request_binding_sha256, "frontier origin request")
    if request_status not in REQUEST_STATUSES:
        _fail("m20_invalid_frontier_state", "frontier request status is invalid")
    if type(body_integrity_valid) is not bool or type(continuation_visible) is not bool or type(dispatched) is not bool:
        _fail("m20_invalid_frontier_state", "frontier state booleans are invalid")
    if origin_identity_outcome not in IDENTITY_OUTCOMES:
        _fail("m20_invalid_frontier_state", "origin identity outcome is invalid")
    if not isinstance(target_ids, list):
        _fail("m20_invalid_frontier_state", "frontier targets must be a list")
    if reported_total is not None and (type(reported_total) is not int or reported_total < 0):
        _fail("m20_invalid_frontier_state", "reported total is invalid")
    if target_cap != FRONTIER_TARGET_CAP:
        _fail("m20_invalid_frontier_state", "frontier target cap differs from the frozen cap")
    if origin_body_sha256 is not None:
        _require_sha256(origin_body_sha256, "frontier origin body")
    if origin_normalized_payload_sha256 is not None:
        _require_sha256(origin_normalized_payload_sha256, "frontier normalized payload")
    boundary_input = request_status == "boundary_invalid" or not body_integrity_valid
    if origin_body_sha256 is None and origin_normalized_payload_sha256 is not None:
        _fail("m20_invalid_frontier_state", "frontier payload binding lacks a body")
    if origin_body_sha256 is not None and origin_normalized_payload_sha256 is None and not boundary_input:
        _fail("m20_invalid_frontier_state", "valid frontier body lacks a payload binding")

    if not dispatched or (derived_from_identity_request and origin_identity_outcome == "boundary_invalid"):
        if target_ids or reported_total is not None or continuation_visible:
            _fail("m20_invalid_frontier_state", "undispatched frontier has observed content")
        return _frontier_result(
            direction=direction,
            binding=binding,
            body_sha256=origin_body_sha256,
            normalized_payload_sha256=origin_normalized_payload_sha256,
            outcome="not_dispatched_due_to_veto",
            target_rows=[],
            unique_valid_count=0,
            admitted_count=0,
            omitted_by_cap_count=0,
            remainder_count=None,
            reported_total=None,
            continuation_visible=False,
            attempt_risk=None,
            global_veto=False,
        )

    if request_status == "available" and origin_body_sha256 is None:
        _fail("m20_invalid_frontier_state", "available frontier requires an origin body")
    if request_status == "unavailable" and origin_body_sha256 is not None:
        _fail("m20_invalid_frontier_state", "unavailable frontier cannot have an origin body")

    if request_status == "boundary_invalid" or not body_integrity_valid:
        normalized_rows = _normalize_frontier_targets(target_ids)
        first_index: dict[str, int] = {}
        boundary_rows = []
        for row in normalized_rows:
            target = row["normalized_target_id"]
            if target is None:
                disposition = "malformed_target"
            elif target in first_index:
                disposition = "duplicate_target"
            else:
                first_index[target] = row["provider_list_index"]
                disposition = "not_admitted_boundary_invalid"
            boundary_rows.append({
                **row,
                "origin_body_sha256": origin_body_sha256,
                "disposition": disposition,
            })
        return _frontier_result(
            direction=direction,
            binding=binding,
            body_sha256=origin_body_sha256,
            normalized_payload_sha256=origin_normalized_payload_sha256,
            outcome="boundary_invalid",
            target_rows=boundary_rows,
            unique_valid_count=len({
                row["normalized_target_id"]
                for row in normalized_rows
                if row["normalized_target_id"] is not None
            }),
            admitted_count=0,
            omitted_by_cap_count=0,
            remainder_count=(None if reported_total is None else reported_total - len(target_ids)),
            reported_total=reported_total,
            continuation_visible=continuation_visible,
            attempt_risk=None,
            global_veto=True,
        )
    if request_status == "unavailable":
        if target_ids or reported_total is not None or continuation_visible:
            _fail("m20_invalid_frontier_state", "unavailable frontier has observed content")
        return _frontier_result(
            direction=direction,
            binding=binding,
            body_sha256=None,
            normalized_payload_sha256=None,
            outcome="provider_unavailable",
            target_rows=[],
            unique_valid_count=0,
            admitted_count=0,
            omitted_by_cap_count=0,
            remainder_count=None,
            reported_total=None,
            continuation_visible=False,
            attempt_risk=_attempt_risk(binding, direction, "provider_unavailable"),
            global_veto=False,
        )

    normalized_rows = _normalize_frontier_targets(target_ids)
    unique_valid = sorted({row["normalized_target_id"] for row in normalized_rows if row["normalized_target_id"]})
    if reported_total is not None and reported_total < len(target_ids):
        _fail("m20_invalid_frontier_state", "reported total is smaller than returned target count")
    if target_ids and not unique_valid:
        malformed_rows = [
            {
                **row,
                "origin_body_sha256": origin_body_sha256,
                "disposition": "malformed_target",
            }
            for row in normalized_rows
        ]
        return _frontier_result(
            direction=direction,
            binding=binding,
            body_sha256=origin_body_sha256,
            normalized_payload_sha256=origin_normalized_payload_sha256,
            outcome="boundary_invalid",
            target_rows=malformed_rows,
            unique_valid_count=0,
            admitted_count=0,
            omitted_by_cap_count=0,
            remainder_count=(None if reported_total is None else reported_total - len(target_ids)),
            reported_total=reported_total,
            continuation_visible=continuation_visible,
            attempt_risk=None,
            global_veto=True,
        )

    remainder = None if reported_total is None else reported_total - len(target_ids)
    if derived_from_identity_request and origin_identity_outcome != "selected":
        rows = []
        for row in normalized_rows:
            target = row["normalized_target_id"]
            if target is None:
                disposition = "malformed_target"
            elif row["duplicate_of_provider_list_index"] is not None:
                disposition = "duplicate_target"
            else:
                disposition = "not_admitted_identity_unresolved"
            rows.append({
                **row,
                "origin_body_sha256": origin_body_sha256,
                "disposition": disposition,
            })
        return _frontier_result(
            direction=direction,
            binding=binding,
            body_sha256=origin_body_sha256,
            normalized_payload_sha256=origin_normalized_payload_sha256,
            outcome="not_observed",
            target_rows=rows,
            unique_valid_count=len(unique_valid),
            admitted_count=0,
            omitted_by_cap_count=0,
            identity_unresolved_count=len(unique_valid),
            remainder_count=remainder,
            reported_total=reported_total,
            continuation_visible=continuation_visible,
            attempt_risk=_attempt_risk(binding, direction, "origin_identity_not_selected"),
            global_veto=False,
        )

    admitted = set(unique_valid[:FRONTIER_TARGET_CAP])
    first_index: dict[str, int] = {}
    rows = []
    for row in normalized_rows:
        target = row["normalized_target_id"]
        if target is None:
            disposition = "malformed_target"
        elif target in first_index:
            disposition = "duplicate_target"
        else:
            first_index[target] = row["provider_list_index"]
            disposition = "admitted" if target in admitted else "omitted_by_cap"
        rows.append({
            **row,
            "origin_body_sha256": origin_body_sha256,
            "disposition": disposition,
        })

    omitted = max(0, len(unique_valid) - len(admitted))
    capped = omitted > 0 or bool(remainder) or continuation_visible
    if capped:
        outcome = "capped"
    elif unique_valid:
        outcome = "observed_results"
    else:
        outcome = "empty_observed"
    risk = None
    if outcome == "empty_observed":
        risk = _attempt_risk(binding, direction, "empty_observed")
    elif outcome == "capped" and not admitted:
        risk = _attempt_risk(binding, direction, "capped_no_observed_targets")
    return _frontier_result(
        direction=direction,
        binding=binding,
        body_sha256=origin_body_sha256,
        normalized_payload_sha256=origin_normalized_payload_sha256,
        outcome=outcome,
        target_rows=rows,
        unique_valid_count=len(unique_valid),
        admitted_count=len(admitted),
        omitted_by_cap_count=omitted,
        identity_unresolved_count=0,
        remainder_count=remainder,
        reported_total=reported_total,
        continuation_visible=continuation_visible,
        attempt_risk=risk,
        global_veto=False,
    )


def _normalize_frontier_targets(target_ids: list[Any]) -> list[dict[str, Any]]:
    rows = []
    first_index: dict[str, int] = {}
    for index, value in enumerate(target_ids):
        normalized = None
        if isinstance(value, str):
            try:
                normalized = normalize_openalex_id(value)
            except MissionStateError:
                normalized = None
        duplicate_of = first_index.get(normalized) if normalized is not None else None
        if normalized is not None and duplicate_of is None:
            first_index[normalized] = index
        rows.append({
            "provider_list_index": index,
            "normalized_target_id": normalized,
            "duplicate_of_provider_list_index": duplicate_of,
        })
    return rows


def _attempt_risk(binding: str, direction: str, reason: str) -> str:
    return "or-" + _sha256(canonical_json_bytes({
        "schema_version": "ra-survey-m20-attempt-risk-identity-v1",
        "origin_request_binding_sha256": binding,
        "direction": direction,
        "reason": reason,
    }))


def _frontier_result(
    *,
    direction: str,
    binding: str,
    body_sha256: str | None,
    normalized_payload_sha256: str | None,
    outcome: str,
    target_rows: list[dict[str, Any]],
    unique_valid_count: int,
    admitted_count: int,
    omitted_by_cap_count: int | None = None,
    identity_unresolved_count: int = 0,
    remainder_count: int | None,
    reported_total: int | None,
    continuation_visible: bool,
    attempt_risk: str | None,
    global_veto: bool,
) -> dict[str, Any]:
    return {
        "schema_version": FRONTIER_OUTCOME_SCHEMA,
        "direction": direction,
        "origin_request_binding_sha256": binding,
        "origin_body_sha256": body_sha256,
        "origin_normalized_payload_sha256": normalized_payload_sha256,
        "outcome": outcome,
        "target_rows": target_rows,
        "summary": {
            "returned_target_count": len(target_rows),
            "unique_valid_target_count": unique_valid_count,
            "admitted_target_count": admitted_count,
            "omitted_by_cap_target_count": (
                0 if omitted_by_cap_count is None else omitted_by_cap_count
            ),
            "identity_unresolved_target_count": identity_unresolved_count,
            "unobserved_provider_remainder_count": remainder_count,
            "reported_total": reported_total,
            "continuation_visible": continuation_visible,
        },
        "attempt_risk_id": attempt_risk,
        "global_veto": global_veto,
    }


def compose_openalex_case_outcome(
    *,
    identity: dict[str, Any],
    backward: dict[str, Any],
    forward: dict[str, Any],
    accepted_body_root: Path,
    accepted_body_records: list[dict[str, Any]],
    replay_records: list[dict[str, Any]],
) -> dict[str, Any]:
    identity = _validate_identity_outcome(identity)
    backward = _validate_frontier_outcome(backward, expected_direction="backward")
    forward = _validate_frontier_outcome(forward, expected_direction="forward")
    if identity["case_kind"] != "explicit_openalex":
        _fail("m20_invalid_case_tuple", "OpenAlex case requires explicit identity")
    inventory = validate_accepted_body_inventory(
        accepted_body_root,
        body_records=accepted_body_records,
    )
    replay_coverage = _validate_replay_coverage(
        identity=identity,
        backward=backward,
        forward=forward,
        accepted_body_records=accepted_body_records,
        replay_records=replay_records,
    )

    identity_outcome = identity["outcome"]
    backward_outcome = backward["outcome"]
    forward_outcome = forward["outcome"]
    if backward["origin_request_binding_sha256"] not in identity["request_bindings"]:
        _fail("m20_invalid_case_tuple", "backward frontier is not bound to an identity request")
    if forward["origin_request_binding_sha256"] in identity["request_bindings"]:
        _fail("m20_invalid_case_tuple", "forward frontier must bind its own request")
    tuple_value = (identity_outcome, backward_outcome, forward_outcome)
    if tuple_value not in _permitted_openalex_tuples():
        _fail("m20_invalid_case_tuple", "OpenAlex identity/frontier tuple is not permitted")

    global_status = (
        "boundary_invalid"
        if identity_outcome == "boundary_invalid"
        or backward["global_veto"]
        or forward["global_veto"]
        else "closed"
    )
    return {
        "schema_version": CASE_OUTCOME_SCHEMA,
        "global_status": global_status,
        "identity_outcome": identity_outcome,
        "backward_frontier_outcome": backward_outcome,
        "forward_frontier_outcome": forward_outcome,
        "accepted_body_inventory_sha256": _sha256(canonical_json_bytes(inventory)),
        "accepted_body_replay_passed": not replay_coverage["retained_unreplayed_bindings"],
        "accepted_body_replay_bindings": replay_coverage["replayed_bindings"],
        "accepted_body_retained_unreplayed_bindings": replay_coverage["retained_unreplayed_bindings"],
        "m21_candidate_authority": (
            global_status == "closed"
            and identity_outcome == "selected"
            and not replay_coverage["retained_unreplayed_bindings"]
        ),
    }


def _validate_replay_coverage(
    *,
    identity: dict[str, Any],
    backward: dict[str, Any],
    forward: dict[str, Any],
    accepted_body_records: Any,
    replay_records: Any,
) -> dict[str, list[str]]:
    if not isinstance(accepted_body_records, list) or not isinstance(replay_records, list):
        _fail("m20_invalid_replay_coverage", "replay coverage rows must be lists")
    bodies = [_validate_body_record(row, allow_unbound=True) for row in accepted_body_records]
    body_by_binding = {row["request_binding_sha256"]: row for row in bodies}
    if len(body_by_binding) != len(bodies):
        _fail("m20_invalid_replay_coverage", "accepted-body request bindings are not unique")
    replays = [_validate_replay_record(row) for row in replay_records]
    replay_by_binding = {row["request_binding_sha256"]: row for row in replays}
    if len(replay_by_binding) != len(replays):
        _fail("m20_invalid_replay_coverage", "replay request bindings are not unique")

    required: dict[str, tuple[str, str]] = {}
    retained_without_replay: set[str] = set()
    for request in identity["request_states"]:
        if request["status"] == "available":
            required[request["request_binding_sha256"]] = (
                request["body_sha256"],
                request["normalized_payload_sha256"],
            )
        elif request["body_sha256"] is not None:
            binding = request["request_binding_sha256"]
            body = body_by_binding.get(binding)
            if body is None or body["sha256"] != request["body_sha256"]:
                _fail("m20_invalid_replay_coverage", "boundary identity body lacks inventory binding")
            retained_without_replay.add(binding)
    for frontier in (backward, forward):
        if frontier["origin_body_sha256"] is not None:
            binding = frontier["origin_request_binding_sha256"]
            body_sha = frontier["origin_body_sha256"]
            if binding in required and required[binding][0] != body_sha:
                _fail("m20_invalid_replay_coverage", "backward body differs from direct identity body")
            if binding in required and required[binding][1] != frontier["origin_normalized_payload_sha256"]:
                _fail("m20_invalid_replay_coverage", "backward payload differs from direct identity payload")
            if binding not in required:
                body = body_by_binding.get(binding)
                if body is None or body["sha256"] != body_sha:
                    _fail("m20_invalid_replay_coverage", "frontier body lacks accepted-body binding")
                if frontier["origin_normalized_payload_sha256"] is not None:
                    required[binding] = (
                        body_sha,
                        frontier["origin_normalized_payload_sha256"],
                    )
                else:
                    retained_without_replay.add(binding)
    if set(body_by_binding) != {
        *required,
        *retained_without_replay,
    } or set(replay_by_binding) != set(required):
        _fail("m20_invalid_replay_coverage", "accepted-body inventory or replay coverage is not exact")
    for binding, (body_sha, payload_sha) in required.items():
        body = body_by_binding[binding]
        replay = replay_by_binding[binding]
        if (
            body["sha256"] != body_sha
            or body["normalized_payload_sha256"] != payload_sha
            or replay["accepted_body_sha256"] != body_sha
            or replay["normalized_payload_sha256"] != payload_sha
            or replay["size_bytes"] != body["size_bytes"]
        ):
            _fail("m20_invalid_replay_coverage", "body and replay bindings differ")
    for request in identity["request_states"]:
        if request["status"] != "available":
            continue
        replay_payload = replay_by_binding[request["request_binding_sha256"]]["normalized_payload"]
        if (
            replay_payload["identity_view_status"] != "observed"
            or
            replay_payload["identity_records"] != request["records"]
            or replay_payload["malformed_row_sha256s"] != request["malformed_row_sha256s"]
            or replay_payload["identity_envelope_complete"] != request["envelope_complete"]
            or replay_payload["identity_cap_exceeded"] != request["cap_exceeded"]
        ):
            _fail("m20_invalid_replay_coverage", "identity request differs from replayed response")
    for frontier in (backward, forward):
        binding = frontier["origin_request_binding_sha256"]
        if frontier["origin_body_sha256"] is None or frontier["origin_normalized_payload_sha256"] is None:
            continue
        if binding not in replay_by_binding:
            _fail("m20_invalid_replay_coverage", "frontier payload lacks replay coverage")
        replay_payload = replay_by_binding[binding]["normalized_payload"]
        expected_frontier_status = (
            "boundary_invalid"
            if frontier["outcome"] == "boundary_invalid"
            else "observed"
        )
        if replay_payload["frontier_view_status"] != expected_frontier_status:
            _fail("m20_invalid_replay_coverage", "frontier replay lacks an applicable view")
        replay_targets = _normalize_frontier_targets(replay_payload["frontier_target_ids"])
        replay_signature = [
            (
                row["provider_list_index"],
                row["normalized_target_id"],
                row["duplicate_of_provider_list_index"],
            )
            for row in replay_targets
        ]
        frontier_signature = [
            (
                row["provider_list_index"],
                row["normalized_target_id"],
                row["duplicate_of_provider_list_index"],
            )
            for row in frontier["target_rows"]
        ]
        if (
            replay_signature != frontier_signature
            or replay_payload["frontier_reported_total"] != frontier["summary"]["reported_total"]
            or replay_payload["frontier_continuation_visible"] != frontier["summary"]["continuation_visible"]
        ):
            _fail("m20_invalid_replay_coverage", "frontier outcome differs from replayed response")
    return {
        "replayed_bindings": sorted(required),
        "retained_unreplayed_bindings": sorted(retained_without_replay),
    }


def _validate_replay_record(value: Any) -> dict[str, Any]:
    keys = {
        "schema_version",
        "status",
        "request_binding_sha256",
        "accepted_body_sha256",
        "normalized_payload_sha256",
        "normalized_payload",
        "size_bytes",
    }
    row = _require_exact_dict(value, keys, "body replay record")
    if row["schema_version"] != BODY_REPLAY_SCHEMA or row["status"] != "passed":
        _fail("m20_invalid_replay_coverage", "body replay status is invalid")
    for field in ("request_binding_sha256", "accepted_body_sha256", "normalized_payload_sha256"):
        _require_sha256(row[field], field)
    normalized = _validate_normalized_response(row["normalized_payload"])
    if _sha256(canonical_json_bytes(normalized)) != row["normalized_payload_sha256"]:
        _fail("m20_invalid_replay_coverage", "body replay normalized payload hash is invalid")
    if type(row["size_bytes"]) is not int or row["size_bytes"] < 0:
        _fail("m20_invalid_replay_coverage", "body replay size is invalid")
    return {**row, "normalized_payload": normalized}


def outcome_automaton_manifest() -> dict[str, Any]:
    return {
        "schema_version": AUTOMATON_SCHEMA,
        "identity_outcomes": sorted(IDENTITY_OUTCOMES),
        "frontier_outcomes": sorted(FRONTIER_OUTCOMES),
        "identity_precedence": [
            "boundary_invalid",
            "capped",
            "all_required_unavailable",
            "available_empty",
            "topic_partial_provider_ambiguous",
            "unique_nonconflicting_match_selected",
            "ambiguous",
        ],
        "identity_equivalence": {
            "strong_aliases": ["normalized_doi", "normalized_openalex_id", "normalized_arxiv_version_family"],
            "candidate_classes_disjoint": True,
            "provider_topology": {
                "explicit_arxiv_seed": ["arxiv"],
                "explicit_openalex": ["openalex"],
                "topic_bootstrap": ["arxiv", "openalex"],
            },
            "identity_query_kind": "identity_resolution",
            "topic_predicate": {
                "unique_exact_title_precedes_approximate": True,
                "similarity_minimum": 0.96,
                "informative_query_token_minimum": 3,
                "runner_up_margin_minimum": 0.08,
            },
            "arxiv_family_canonical_version": "highest_observed",
            "topic_order_never_selects": True,
            "forward_rows_never_enter_identity_candidates": True,
        },
        "accepted_body_policy": {
            "per_request_cap_bytes": ACCEPTED_BODY_CAP_BYTES,
            "total_cap_bytes": TOTAL_ACCEPTED_BODY_CAP_BYTES,
            "exact_inventory_required": True,
            "replay_status_must_match_frontier_outcome": True,
        },
        "frontier_policy": {
            "outcome_unit": "frontier_attempt",
            "origin_request_binding_required": True,
            "target_order": "lexical_normalized_openalex_id",
            "target_cap": FRONTIER_TARGET_CAP,
            "target_dispositions": sorted(TARGET_DISPOSITIONS),
            "duplicate_rows_retained": True,
            "malformed_rows_retained": True,
            "unobserved_remainder_retained": True,
            "boundary_invalid_targets": {
                "preserve_every_provider_index": True,
                "valid_unique_disposition": "not_admitted_boundary_invalid",
                "duplicate_disposition": "duplicate_target",
                "malformed_disposition": "malformed_target",
                "admitted_target_count": 0,
            },
        },
        "composition": {
            "axes": ["identity_outcome", "backward_frontier_outcome", "forward_frontier_outcome"],
            "identity_boundary_suppresses": ["backward", "forward"],
            "backward_boundary_suppresses": ["forward"],
            "any_boundary_invalid_is_global_veto": True,
            "frontier_outcomes_never_overwrite_identity": True,
            "m21_authority_requires": ["closed_global_status", "selected_identity", "accepted_body_replay_passed"],
            "permitted_openalex_tuples": [list(row) for row in sorted(_permitted_openalex_tuples())],
        },
    }


def _permitted_openalex_tuples() -> set[tuple[str, str, str]]:
    observed_forward = {
        "observed_results",
        "empty_observed",
        "provider_unavailable",
        "capped",
        "boundary_invalid",
    }
    result = {
        ("boundary_invalid", "not_dispatched_due_to_veto", "not_dispatched_due_to_veto"),
        ("selected", "boundary_invalid", "not_dispatched_due_to_veto"),
        ("empty", "boundary_invalid", "not_dispatched_due_to_veto"),
        ("ambiguous", "boundary_invalid", "not_dispatched_due_to_veto"),
        ("capped", "boundary_invalid", "not_dispatched_due_to_veto"),
    }
    for backward in {"observed_results", "empty_observed", "capped"}:
        for forward in observed_forward:
            result.add(("selected", backward, forward))
    for forward in observed_forward:
        result.add(("unavailable", "provider_unavailable", forward))
        for identity in {"empty", "ambiguous", "capped"}:
            result.add((identity, "not_observed", forward))
    return result


def _validate_identity_outcome(value: Any) -> dict[str, Any]:
    row = _require_exact_dict(value, IDENTITY_OUTCOME_KEYS, "identity outcome")
    if row["schema_version"] != IDENTITY_OUTCOME_SCHEMA or row["case_kind"] not in CASE_KINDS:
        _fail("m20_invalid_identity_outcome", "identity outcome schema or case is invalid")
    if row["outcome"] not in IDENTITY_OUTCOMES:
        _fail("m20_invalid_identity_outcome", "identity outcome is invalid")
    rebuilt = classify_identity_outcome(
        case_kind=row["case_kind"],
        expected_identifier=row["expected_identifier"],
        topic=row["topic"],
        request_states=row["request_states"],
    )
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(row):
        _fail("m20_invalid_identity_outcome", "identity outcome does not replay from request evidence")
    return rebuilt


def _validate_frontier_outcome(
    value: Any,
    *,
    expected_direction: str,
) -> dict[str, Any]:
    row = _require_exact_dict(value, FRONTIER_OUTCOME_KEYS, "frontier outcome")
    if (
        row["schema_version"] != FRONTIER_OUTCOME_SCHEMA
        or row["direction"] != expected_direction
        or row["outcome"] not in FRONTIER_OUTCOMES
    ):
        _fail("m20_invalid_frontier_outcome", "frontier outcome schema, direction, or state is invalid")
    _require_sha256(row["origin_request_binding_sha256"], "frontier origin request")
    body_sha = row["origin_body_sha256"]
    payload_sha = row["origin_normalized_payload_sha256"]
    if body_sha is not None:
        _require_sha256(body_sha, "frontier origin body")
    if payload_sha is not None:
        _require_sha256(payload_sha, "frontier normalized payload")
    if body_sha is None and payload_sha is not None:
        _fail("m20_invalid_frontier_outcome", "frontier payload provenance lacks a body")
    if body_sha is not None and payload_sha is None and row["outcome"] != "boundary_invalid":
        _fail("m20_invalid_frontier_outcome", "valid frontier body lacks payload provenance")
    if type(row["global_veto"]) is not bool:
        _fail("m20_invalid_frontier_outcome", "frontier veto flag is invalid")
    summary = _require_exact_dict(row["summary"], FRONTIER_SUMMARY_KEYS, "frontier summary")
    for field, number in summary.items():
        if field == "continuation_visible":
            if type(number) is not bool:
                _fail("m20_invalid_frontier_outcome", "frontier continuation flag is invalid")
            continue
        if number is not None and (type(number) is not int or number < 0):
            _fail("m20_invalid_frontier_outcome", f"frontier summary {field} is invalid")
    if not isinstance(row["target_rows"], list):
        _fail("m20_invalid_frontier_outcome", "frontier target rows must be a list")
    targets = []
    first_index: dict[str, int] = {}
    for index, value_row in enumerate(row["target_rows"]):
        target = _require_exact_dict(value_row, TARGET_ROW_KEYS, f"target_rows[{index}]")
        if target["provider_list_index"] != index:
            _fail("m20_invalid_frontier_outcome", "frontier provider indices are not complete")
        normalized = target["normalized_target_id"]
        if normalized is not None:
            try:
                if normalize_openalex_id(normalized) != normalized:
                    _fail("m20_invalid_frontier_outcome", "frontier target is not normalized")
            except MissionStateError as exc:
                raise MissionStateError("m20_invalid_frontier_outcome", "frontier target is invalid") from exc
        duplicate = target["duplicate_of_provider_list_index"]
        if duplicate is not None and (type(duplicate) is not int or not 0 <= duplicate < index):
            _fail("m20_invalid_frontier_outcome", "frontier duplicate index is invalid")
        if target["origin_body_sha256"] != body_sha or target["disposition"] not in TARGET_DISPOSITIONS:
            _fail("m20_invalid_frontier_outcome", "frontier target provenance or disposition is invalid")
        expected_duplicate = first_index.get(normalized) if normalized is not None else None
        if normalized is not None and expected_duplicate is None:
            first_index[normalized] = index
        if duplicate != expected_duplicate:
            _fail("m20_invalid_frontier_outcome", "frontier duplicate provenance is invalid")
        if normalized is None and target["disposition"] != "malformed_target":
            _fail("m20_invalid_frontier_outcome", "malformed target disposition is invalid")
        if normalized is not None and target["disposition"] == "malformed_target":
            _fail("m20_invalid_frontier_outcome", "valid target cannot be marked malformed")
        if duplicate is not None and target["disposition"] != "duplicate_target":
            _fail("m20_invalid_frontier_outcome", "duplicate target disposition is invalid")
        if target["disposition"] == "duplicate_target" and duplicate is None:
            _fail("m20_invalid_frontier_outcome", "duplicate disposition lacks a source row")
        targets.append(dict(target))
    if summary["returned_target_count"] != len(targets):
        _fail("m20_invalid_frontier_outcome", "frontier returned-target count is invalid")
    unique_valid = {
        target["normalized_target_id"]
        for target in targets
        if target["normalized_target_id"] is not None
    }
    admitted = {
        target["normalized_target_id"]
        for target in targets
        if target["disposition"] == "admitted"
    }
    omitted_by_cap = {
        target["normalized_target_id"]
        for target in targets
        if target["disposition"] == "omitted_by_cap"
    }
    identity_unresolved = {
        target["normalized_target_id"]
        for target in targets
        if target["disposition"] == "not_admitted_identity_unresolved"
    }
    if (
        summary["unique_valid_target_count"] != len(unique_valid)
        or summary["admitted_target_count"] != len(admitted)
        or summary["omitted_by_cap_target_count"] != len(omitted_by_cap)
        or summary["identity_unresolved_target_count"] != len(identity_unresolved)
        or admitted & (omitted_by_cap | identity_unresolved)
        or omitted_by_cap & identity_unresolved
    ):
        _fail("m20_invalid_frontier_outcome", "frontier target counts do not reconcile")
    reported_total = summary["reported_total"]
    expected_remainder = None if reported_total is None else reported_total - len(targets)
    if expected_remainder is not None and expected_remainder < 0:
        _fail("m20_invalid_frontier_outcome", "frontier reported total is too small")
    if summary["unobserved_provider_remainder_count"] != expected_remainder:
        _fail("m20_invalid_frontier_outcome", "frontier remainder does not reconcile")
    risk = row["attempt_risk_id"]
    if risk is not None and (not isinstance(risk, str) or not risk.startswith("or-") or not _is_sha256(risk[3:])):
        _fail("m20_invalid_frontier_outcome", "frontier attempt risk is invalid")
    has_observation = summary["admitted_target_count"] > 0
    if row["outcome"] in {"boundary_invalid", "not_dispatched_due_to_veto"}:
        if has_observation or risk is not None:
            _fail("m20_invalid_frontier_outcome", "boundary or suppressed frontier cannot carry observations or risk")
    elif has_observation == (risk is not None):
        _fail("m20_invalid_frontier_outcome", "closed frontier attempt must have observations xor one risk")
    if row["outcome"] == "boundary_invalid" and not row["global_veto"]:
        _fail("m20_invalid_frontier_outcome", "frontier boundary invalidity must veto globally")
    if row["outcome"] != "boundary_invalid" and row["global_veto"]:
        _fail("m20_invalid_frontier_outcome", "non-boundary frontier cannot veto globally")
    body_required = row["outcome"] in {
        "observed_results",
        "empty_observed",
        "capped",
        "not_observed",
    }
    body_forbidden = row["outcome"] in {
        "provider_unavailable",
        "not_dispatched_due_to_veto",
    }
    if (body_required and body_sha is None) or (body_forbidden and body_sha is not None):
        _fail("m20_invalid_frontier_outcome", "frontier body provenance is incompatible with its outcome")
    if row["outcome"] == "empty_observed" and (
        targets or summary["unique_valid_target_count"] != 0
    ):
        _fail("m20_invalid_frontier_outcome", "empty frontier contains target rows")
    if row["outcome"] == "observed_results" and summary["admitted_target_count"] == 0:
        _fail("m20_invalid_frontier_outcome", "observed frontier has no admitted target")
    lexical = sorted(unique_valid)
    expected_admitted = set(lexical[:FRONTIER_TARGET_CAP])
    if row["outcome"] not in {"not_observed", "boundary_invalid", "not_dispatched_due_to_veto", "provider_unavailable"}:
        if admitted != expected_admitted or omitted_by_cap != set(lexical[FRONTIER_TARGET_CAP:]):
            _fail("m20_invalid_frontier_outcome", "frontier lexical cap dispositions are invalid")
    if row["outcome"] == "not_observed" and (
        admitted or omitted_by_cap or identity_unresolved != unique_valid
    ):
        _fail("m20_invalid_frontier_outcome", "not-observed frontier dispositions are invalid")
    if row["outcome"] in {"provider_unavailable", "not_dispatched_due_to_veto"} and (
        targets
        or summary["reported_total"] is not None
        or summary["continuation_visible"]
    ):
        _fail("m20_invalid_frontier_outcome", "non-observed frontier contains provider content")
    capped_evidence = (
        summary["omitted_by_cap_target_count"] > 0
        or bool(summary["unobserved_provider_remainder_count"])
        or summary["continuation_visible"]
    )
    if row["outcome"] not in {"boundary_invalid", "not_observed"} and (
        (row["outcome"] == "capped") != capped_evidence
    ):
        _fail("m20_invalid_frontier_outcome", "frontier capped state lacks exact evidence")
    if row["outcome"] == "boundary_invalid":
        boundary_valid = {
            target["normalized_target_id"]
            for target in targets
            if target["normalized_target_id"] is not None
            and target["duplicate_of_provider_list_index"] is None
        }
        observed_boundary_valid = {
            target["normalized_target_id"]
            for target in targets
            if target["disposition"] == "not_admitted_boundary_invalid"
        }
        if boundary_valid != observed_boundary_valid or any(
            target["disposition"] in {
                "admitted",
                "omitted_by_cap",
                "not_admitted_identity_unresolved",
            }
            for target in targets
        ):
            _fail("m20_invalid_frontier_outcome", "boundary frontier target dispositions are invalid")
    risk_reason = {
        "empty_observed": "empty_observed",
        "provider_unavailable": "provider_unavailable",
        "not_observed": "origin_identity_not_selected",
    }.get(row["outcome"])
    if row["outcome"] == "capped" and not admitted:
        risk_reason = "capped_no_observed_targets"
    expected_risk = (
        _attempt_risk(row["origin_request_binding_sha256"], row["direction"], risk_reason)
        if risk_reason is not None
        else None
    )
    if risk != expected_risk:
        _fail("m20_invalid_frontier_outcome", "frontier attempt risk binding is invalid")
    return {**row, "target_rows": targets, "summary": dict(summary)}


def outcome_automaton_sha256() -> str:
    return _sha256(canonical_json_bytes(outcome_automaton_manifest()))


__all__ = [
    "ACCEPTED_BODY_SCHEMA",
    "AUTOMATON_SCHEMA",
    "BODY_REPLAY_SCHEMA",
    "CASE_OUTCOME_SCHEMA",
    "FRONTIER_OUTCOME_SCHEMA",
    "IDENTITY_OUTCOME_SCHEMA",
    "bind_normalized_payload",
    "classify_frontier_attempt",
    "classify_identity_outcome",
    "compose_openalex_case_outcome",
    "outcome_automaton_manifest",
    "outcome_automaton_sha256",
    "replay_accepted_body",
    "validate_accepted_body_inventory",
    "write_accepted_body",
]
