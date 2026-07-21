from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.artifact_lineage import (
    ArtifactSetSnapshot,
    assert_public_write_path_allowed,
    validate_selected_review_queue,
    workflow_blocker_source_id,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
)


REVIEW_DECISIONS_SCHEMA = "ra-survey-review-decisions-v2"
DECISION_IDENTITY_SCHEMA = "ra-survey-normalized-decision-identity-v1"
SUPPORTED_DECISION_TYPES = {
    "claim_candidate",
    "source_safety",
    "omission_risk",
    "workflow_blocker",
}
WORKFLOW_BLOCKER_RESOLUTION_MAPPING = {
    "technical claims are still blocked pending reviewed claim-anchor mapping": (
        "claim_review", "claim_candidate",
    ),
    "no reviewed supported technical claim rows are present": (
        "claim_review", "claim_candidate",
    ),
    "retraction/version safety is not checked clear for all sourced papers": (
        "source_safety_review", "source_safety",
    ),
    "omission and reviewer-risk rows require review before claiming completeness": (
        "omission_review", "omission_risk",
    ),
}
DECISION_ENVELOPE_KEYS = {
    "schema_version",
    "decision_type",
    "mission_id",
    "mission_fingerprint",
    "artifact_set_id",
    "queue_semantic_sha256",
    "review_queue_sha256",
    "decisions",
}
COMMON_SIDECAR_KEYS = {
    "schema_version",
    "status",
    "created_at",
    "decision_type",
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
    "queue_semantic_sha256",
    "review_queue_path",
    "review_queue_sha256",
    "decisions_path",
    "decisions_sha256",
    "required_queue_item_ids",
    "supplied_queue_item_ids",
    "accepted_queue_item_ids",
    "decision_coverage_complete",
    "ready_for_reviewed_packet",
    "ready_for_prose",
    "what_is_not_concluded",
}


@dataclass(frozen=True)
class ReviewDecisionContext:
    snapshot: ArtifactSetSnapshot
    review_queue_path: Path
    review_queue: dict[str, Any]
    review_queue_sha256: str
    decision_type: str
    required_items: dict[str, dict[str, Any]]

    @property
    def required_item_ids(self) -> list[str]:
        return sorted(self.required_items)


@dataclass(frozen=True)
class ExactDecisionResult:
    required_item_ids: list[str]
    supplied_item_ids: list[str]
    accepted: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    coverage_errors: list[str]

    @property
    def accepted_item_ids(self) -> list[str]:
        return sorted(str(row["queue_item_id"]) for row in self.accepted)

    @property
    def complete(self) -> bool:
        return not self.rejected and not self.coverage_errors and self.accepted_item_ids == self.required_item_ids


DecisionValidator = Callable[[Any, dict[str, Any] | None, int], tuple[dict[str, Any], list[str]]]
ResultTransform = Callable[[ExactDecisionResult], ExactDecisionResult]
ExpectedSidecarFields = Callable[[ExactDecisionResult], dict[str, Any]]


def load_bound_decision_envelope(
    *,
    review_queue_path: Path,
    decisions_path: Path,
    decision_type: str,
) -> tuple[ReviewDecisionContext, dict[str, Any], list[Any], bytes]:
    if decision_type not in SUPPORTED_DECISION_TYPES:
        raise MissionStateError("invalid_decision_type", f"unsupported decision type: {decision_type}")
    context = load_selected_decision_context(
        review_queue_path=review_queue_path,
        decision_type=decision_type,
    )
    decisions, raw = read_json_object_strict(decisions_path, label="review decisions")
    rows = validate_bound_decision_envelope(context=context, decisions=decisions)
    return context, decisions, rows, raw


def validate_bound_decision_envelope(
    *,
    context: ReviewDecisionContext,
    decisions: dict[str, Any],
) -> list[Any]:
    require_exact_keys(decisions, DECISION_ENVELOPE_KEYS, "review decision envelope")
    if decisions["schema_version"] != REVIEW_DECISIONS_SCHEMA:
        raise MissionStateError("invalid_decision_schema", "review decision envelope schema is unsupported")
    if decisions["decision_type"] != context.decision_type:
        raise MissionStateError("wrong_decision_type", "review decision envelope has the wrong decision_type")

    expected = {
        "mission_id": context.review_queue.get("mission_id"),
        "mission_fingerprint": context.review_queue.get("mission_fingerprint"),
        "artifact_set_id": context.review_queue.get("artifact_set_id"),
        "queue_semantic_sha256": context.review_queue.get("queue_semantic_sha256"),
        "review_queue_sha256": context.review_queue_sha256,
    }
    for field, value in expected.items():
        if decisions.get(field) != value:
            code = "foreign_lineage" if field in {"mission_id", "mission_fingerprint"} else "stale_lineage"
            raise MissionStateError(code, f"review decision envelope {field} does not match the selected queue")
    rows = decisions.get("decisions")
    if not isinstance(rows, list):
        raise MissionStateError("invalid_decision_file", "review decision envelope decisions must be a list")

    return rows


def load_selected_decision_context(
    *,
    review_queue_path: Path,
    decision_type: str,
) -> ReviewDecisionContext:
    if decision_type not in SUPPORTED_DECISION_TYPES:
        raise MissionStateError("invalid_decision_type", f"unsupported decision type: {decision_type}")
    snapshot = validate_selected_review_queue(review_queue_path)
    return decision_context_from_snapshot(snapshot=snapshot, decision_type=decision_type)


def decision_context_from_snapshot(
    *,
    snapshot: ArtifactSetSnapshot,
    decision_type: str,
) -> ReviewDecisionContext:
    if decision_type not in SUPPORTED_DECISION_TYPES:
        raise MissionStateError("invalid_decision_type", f"unsupported decision type: {decision_type}")
    selected_path = snapshot.review_queue_path
    queue, queue_raw = read_json_object_strict(selected_path, label="selected review queue")
    queue_items = queue.get("items")
    if not isinstance(queue_items, list) or any(not isinstance(item, dict) for item in queue_items):
        raise MissionStateError("invalid_queue_items", "selected review queue items must be objects")
    unsupported = sorted({
        str(item.get("queue_type") or "")
        for item in queue_items
        if item.get("queue_type") not in SUPPORTED_DECISION_TYPES
    })
    if unsupported:
        raise MissionStateError(
            "unsupported_queue_type",
            f"selected review queue contains unsupported item types: {', '.join(unsupported)}",
        )
    if any(not isinstance(item.get("item_id"), str) or not item["item_id"] for item in queue_items):
        raise MissionStateError("invalid_queue_items", "every selected queue item must have a nonempty item_id")
    validate_workflow_queue_semantics(queue_items)
    required_items = {
        str(item["item_id"]): item
        for item in queue_items
        if isinstance(item, dict) and item.get("queue_type") == decision_type and isinstance(item.get("item_id"), str)
    }
    return ReviewDecisionContext(
        snapshot=snapshot,
        review_queue_path=selected_path,
        review_queue=queue,
        review_queue_sha256=hashlib.sha256(queue_raw).hexdigest(),
        decision_type=decision_type,
        required_items=required_items,
    )


def workflow_blocker_resolution(reason: str) -> tuple[str, str | None]:
    return WORKFLOW_BLOCKER_RESOLUTION_MAPPING.get(
        reason,
        ("upstream_repair_required", None),
    )


def validate_workflow_queue_semantics(queue_items: list[dict[str, Any]]) -> None:
    item_ids_by_type = {
        decision_type: sorted(
            str(item["item_id"])
            for item in queue_items
            if item.get("queue_type") == decision_type
        )
        for decision_type in SUPPORTED_DECISION_TYPES - {"workflow_blocker"}
    }
    for item in queue_items:
        if item.get("queue_type") != "workflow_blocker":
            continue
        try:
            reason = normalize_required_text(item.get("reason"), field="workflow blocker reason")
        except MissionStateError as exc:
            raise MissionStateError("invalid_workflow_queue_semantics", str(exc)) from exc
        expected_class, expected_type = workflow_blocker_resolution(reason)
        expected_ids = item_ids_by_type.get(expected_type, []) if expected_type is not None else []
        if expected_type is not None and not expected_ids:
            expected_class, expected_type, expected_ids = "upstream_repair_required", None, []
        expected = {
            "source_id": workflow_blocker_source_id(reason),
            "resolution_class": expected_class,
            "required_evidence_queue_type": expected_type,
            "required_evidence_queue_item_ids": expected_ids,
        }
        for field, value in expected.items():
            if item.get(field) != value:
                raise MissionStateError(
                    "invalid_workflow_queue_semantics",
                    f"workflow blocker {item.get('item_id')} has non-normative {field}",
                )


def validate_exact_decisions(
    *,
    context: ReviewDecisionContext,
    rows: list[Any],
    validator: DecisionValidator,
) -> ExactDecisionResult:
    raw_ids: list[str] = []
    id_counts: dict[str, int] = {}
    rejected: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        item_id = ""
        if isinstance(row, dict):
            value = row.get("queue_item_id")
            item_id = value.strip() if isinstance(value, str) else ""
        if item_id:
            raw_ids.append(item_id)
            id_counts[item_id] = id_counts.get(item_id, 0) + 1

    duplicate_ids = sorted(item_id for item_id, count in id_counts.items() if count > 1)
    required = set(context.required_items)
    supplied = set(raw_ids)
    missing = sorted(required - supplied)
    unknown = sorted(supplied - required)
    coverage_errors: list[str] = []
    if missing:
        coverage_errors.append(f"missing queue_item_ids: {', '.join(missing)}")
    if unknown:
        coverage_errors.append(f"unknown or wrong-type queue_item_ids: {', '.join(unknown)}")
    if duplicate_ids:
        coverage_errors.append(f"duplicate queue_item_ids: {', '.join(duplicate_ids)}")
    if len(rows) != len(context.required_items):
        coverage_errors.append(
            f"decision row count {len(rows)} does not equal required {context.decision_type} item count {len(context.required_items)}"
        )

    for index, row in enumerate(rows, start=1):
        item_id = ""
        if isinstance(row, dict) and isinstance(row.get("queue_item_id"), str):
            item_id = row["queue_item_id"].strip()
        item = context.required_items.get(item_id)
        normalized, reasons = validator(row, item, index)
        if item_id in duplicate_ids:
            reasons = [*reasons, "queue_item_id is duplicated in the decision envelope"]
        if item_id and item is None:
            reasons = [*reasons, "queue_item_id does not reference the required decision type"]
        if reasons:
            rejected.append({
                "row_index": index,
                "queue_item_id": item_id or None,
                "reasons": sorted(set(reasons)),
            })
            continue
        normalized = dict(normalized)
        normalized["queue_item_id"] = item_id
        normalized["decision_sha256"] = decision_sha256(context.decision_type, normalized)
        accepted.append(normalized)

    accepted.sort(key=lambda row: str(row["queue_item_id"]))
    rejected.sort(key=lambda row: int(row["row_index"]))
    return ExactDecisionResult(
        required_item_ids=sorted(required),
        supplied_item_ids=sorted(supplied),
        accepted=accepted,
        rejected=rejected,
        coverage_errors=coverage_errors,
    )


def decision_sha256(decision_type: str, normalized: dict[str, Any]) -> str:
    payload = {
        "schema_version": DECISION_IDENTITY_SCHEMA,
        "decision_type": decision_type,
        "decision": {key: value for key, value in normalized.items() if key != "decision_sha256"},
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def common_sidecar_fields(
    *,
    context: ReviewDecisionContext,
    decisions_path: Path,
    decisions_raw: bytes,
    result: ExactDecisionResult,
    created_at: str,
) -> dict[str, Any]:
    return {
        "created_at": created_at,
        "decision_type": context.decision_type,
        "mission_id": context.review_queue["mission_id"],
        "mission_fingerprint": context.review_queue["mission_fingerprint"],
        "mission_anchor_generation_id": context.review_queue["mission_anchor_generation_id"],
        "artifact_set_id": context.review_queue["artifact_set_id"],
        "queue_semantic_sha256": context.review_queue["queue_semantic_sha256"],
        "review_queue_path": str(context.review_queue_path),
        "review_queue_sha256": context.review_queue_sha256,
        "decisions_path": str(decisions_path.absolute()),
        "decisions_sha256": hashlib.sha256(decisions_raw).hexdigest(),
        "required_queue_item_ids": result.required_item_ids,
        "supplied_queue_item_ids": result.supplied_item_ids,
        "accepted_queue_item_ids": result.accepted_item_ids,
        "decision_coverage_complete": result.complete,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
    }


def validate_sidecar_binding(
    *,
    path: Path,
    context: ReviewDecisionContext,
    expected_schema: str,
    expected_keys: set[str],
    decisions_field: str,
    rejected_field: str,
    validator: DecisionValidator,
    expected_fields: ExpectedSidecarFields,
    result_transform: ResultTransform | None = None,
) -> tuple[dict[str, Any], bytes]:
    payload, raw = read_json_object_strict(path, label=context.decision_type + " reviewed sidecar")
    require_exact_keys(payload, expected_keys, context.decision_type + " reviewed sidecar")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_review_sidecar", f"{context.decision_type} sidecar is not canonical")
    if payload.get("schema_version") != expected_schema or payload.get("decision_type") != context.decision_type:
        raise MissionStateError("invalid_review_sidecar_schema", f"{context.decision_type} sidecar schema/type is unsupported")
    try:
        normalized_created_at = normalize_reviewed_at(payload.get("created_at"))
    except MissionStateError as exc:
        raise MissionStateError("invalid_review_sidecar", f"{context.decision_type} sidecar created_at is invalid") from exc
    if payload.get("created_at") != normalized_created_at:
        raise MissionStateError("noncanonical_review_sidecar", f"{context.decision_type} sidecar created_at is not normalized UTC")
    expected_binding = {
        "mission_id": context.review_queue["mission_id"],
        "mission_fingerprint": context.review_queue["mission_fingerprint"],
        "mission_anchor_generation_id": context.review_queue["mission_anchor_generation_id"],
        "artifact_set_id": context.review_queue["artifact_set_id"],
        "queue_semantic_sha256": context.review_queue["queue_semantic_sha256"],
        "review_queue_sha256": context.review_queue_sha256,
        "review_queue_path": str(context.review_queue_path),
    }
    for field, value in expected_binding.items():
        if payload.get(field) != value:
            raise MissionStateError("stale_lineage", f"{context.decision_type} sidecar {field} is not current")
    decisions_path_value = payload.get("decisions_path")
    if (
        not isinstance(decisions_path_value, str)
        or not decisions_path_value
        or not Path(decisions_path_value).is_absolute()
        or os.path.normpath(decisions_path_value) != decisions_path_value
    ):
        raise MissionStateError("invalid_review_sidecar", f"{context.decision_type} decisions_path must be normalized and absolute")
    decisions_path = Path(decisions_path_value)
    envelope, decisions_raw = read_json_object_strict(
        decisions_path,
        label=context.decision_type + " review decisions",
    )
    if payload.get("decisions_sha256") != hashlib.sha256(decisions_raw).hexdigest():
        raise MissionStateError("stale_review_decisions", f"{context.decision_type} decision-envelope bytes changed after import")
    rows = validate_bound_decision_envelope(context=context, decisions=envelope)
    result = validate_exact_decisions(context=context, rows=rows, validator=validator)
    if result_transform is not None:
        result = result_transform(result)

    required_ids = strict_sorted_unique_strings(payload.get("required_queue_item_ids"), "required_queue_item_ids")
    supplied_ids = strict_sorted_unique_strings(payload.get("supplied_queue_item_ids"), "supplied_queue_item_ids")
    accepted_ids = strict_sorted_unique_strings(payload.get("accepted_queue_item_ids"), "accepted_queue_item_ids")
    expected_common = {
        "decisions_path": str(decisions_path),
        "decisions_sha256": hashlib.sha256(decisions_raw).hexdigest(),
        "required_queue_item_ids": result.required_item_ids,
        "supplied_queue_item_ids": result.supplied_item_ids,
        "accepted_queue_item_ids": result.accepted_item_ids,
        "decision_coverage_complete": result.complete,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        decisions_field: result.accepted,
        rejected_field: result.rejected,
        "coverage_errors": result.coverage_errors,
    }
    for field, value in {**expected_common, **expected_fields(result)}.items():
        if payload.get(field) != value:
            raise MissionStateError(
                "invalid_review_sidecar_replay",
                f"{context.decision_type} sidecar {field} differs from replayed review decisions",
            )
    if required_ids != context.required_item_ids:
        raise MissionStateError("invalid_review_coverage", f"{context.decision_type} required ID set differs from queue")
    decisions = payload.get(decisions_field)
    rejections = payload.get(rejected_field)
    if not isinstance(decisions, list) or any(not isinstance(row, dict) for row in decisions):
        raise MissionStateError("invalid_review_sidecar", f"{decisions_field} must be an object list")
    if not isinstance(rejections, list) or any(not isinstance(row, dict) for row in rejections):
        raise MissionStateError("invalid_review_sidecar", f"{rejected_field} must be an object list")
    actual_ids = sorted(str(row.get("queue_item_id") or "") for row in decisions)
    if any(not value for value in actual_ids) or actual_ids != accepted_ids:
        raise MissionStateError("invalid_review_coverage", f"{context.decision_type} accepted rows do not match accepted IDs")
    hashes: set[str] = set()
    for row in decisions:
        expected_hash = decision_sha256(context.decision_type, row)
        if row.get("decision_sha256") != expected_hash or expected_hash in hashes:
            raise MissionStateError("invalid_decision_hash", f"{context.decision_type} decision hash is invalid or duplicated")
        hashes.add(expected_hash)
    complete = payload.get("decision_coverage_complete") is True
    computed_complete = not rejections and required_ids == supplied_ids == accepted_ids
    if complete != computed_complete:
        raise MissionStateError("invalid_review_coverage", f"{context.decision_type} coverage flag is inconsistent")
    if payload.get("ready_for_reviewed_packet") is not False or payload.get("ready_for_prose") is not False:
        raise MissionStateError("false_readiness", f"{context.decision_type} importer cannot emit readiness")
    return payload, raw


def normalize_required_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise MissionStateError("invalid_decision_text", f"{field} must be a string")
    normalized_unicode = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(char) == "Cc" for char in normalized_unicode):
        raise MissionStateError("invalid_decision_text", f"{field} must not contain control characters")
    normalized = " ".join(normalized_unicode.split())
    if not normalized:
        raise MissionStateError("invalid_decision_text", f"{field} must not be empty")
    return normalized


def normalize_optional_text(value: Any, *, field: str) -> str:
    if value is None or value == "":
        return ""
    return normalize_required_text(value, field=field)


def normalize_reviewed_at(value: Any) -> str:
    text = normalize_required_text(value, field="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as exc:
        raise MissionStateError("invalid_reviewed_at", "reviewed_at must be an ISO-8601 instant") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MissionStateError("invalid_reviewed_at", "reviewed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_string_list(value: Any, *, field: str, required: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_decision_list", f"{field} must be a list")
    result = [normalize_required_text(item, field=field) for item in value]
    if len(result) != len(set(result)):
        raise MissionStateError("invalid_decision_list", f"{field} must not contain duplicates")
    if required and not result:
        raise MissionStateError("invalid_decision_list", f"{field} must not be empty")
    return sorted(result)


def require_lower_hex(value: Any, *, field: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise MissionStateError("invalid_decision_hash", f"{field} must be {length} lowercase hex characters")
    return value


def strict_sorted_unique_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise MissionStateError("invalid_review_sidecar", f"{field} must be a nonempty-string list")
    if value != sorted(set(value)):
        raise MissionStateError("invalid_review_sidecar", f"{field} must be sorted and unique")
    return list(value)


def read_json_object_strict(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    absolute = path.absolute()
    _validate_existing_path(absolute, label=label, leaf_directory=False)
    try:
        raw = absolute.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_json", f"cannot read valid JSON for {label}: {absolute}") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_schema", f"{label} must be a JSON object")
    return payload, raw


def sha256_strict_file(path: Path, *, label: str) -> str:
    absolute = path.absolute()
    _validate_existing_path(absolute, label=label, leaf_directory=False)
    return hashlib.sha256(absolute.read_bytes()).hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    absolute = path.absolute()
    assert_public_write_path_allowed(absolute)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    _validate_existing_path(absolute.parent, label="review output directory", leaf_directory=True)
    value = pretty_json_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{absolute.name}.", suffix=".tmp", dir=absolute.parent)
    temporary = Path(temporary_name)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, absolute)
        replaced = True
        directory = os.open(absolute.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if not replaced and temporary.exists():
            temporary.unlink()


def require_exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise MissionStateError("invalid_schema", f"{label} fields do not match exact schema")


def _validate_existing_path(path: Path, *, label: str, leaf_directory: bool) -> None:
    current = Path(path.anchor)
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise MissionStateError("missing_review_artifact", f"{label} is missing: {path}") from exc
        if stat.S_ISLNK(mode):
            raise MissionStateError("unsafe_review_artifact", f"{label} contains a symlink: {current}")
        is_leaf = index == len(parts) - 1
        if is_leaf and leaf_directory and not stat.S_ISDIR(mode):
            raise MissionStateError("unsafe_review_artifact", f"{label} is not a directory: {path}")
        if is_leaf and not leaf_directory and not stat.S_ISREG(mode):
            raise MissionStateError("unsafe_review_artifact", f"{label} is not a regular file: {path}")
        if not is_leaf and not stat.S_ISDIR(mode):
            raise MissionStateError("unsafe_review_artifact", f"{label} parent is not a directory: {current}")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "COMMON_SIDECAR_KEYS",
    "DECISION_ENVELOPE_KEYS",
    "ExactDecisionResult",
    "REVIEW_DECISIONS_SCHEMA",
    "ReviewDecisionContext",
    "atomic_write_json",
    "common_sidecar_fields",
    "decision_context_from_snapshot",
    "decision_sha256",
    "load_bound_decision_envelope",
    "load_selected_decision_context",
    "normalize_optional_text",
    "normalize_required_text",
    "normalize_reviewed_at",
    "normalize_string_list",
    "read_json_object_strict",
    "require_exact_keys",
    "require_lower_hex",
    "sha256_strict_file",
    "strict_sorted_unique_strings",
    "utc_now_iso",
    "validate_exact_decisions",
    "validate_bound_decision_envelope",
    "validate_sidecar_binding",
    "validate_workflow_queue_semantics",
    "workflow_blocker_resolution",
]
