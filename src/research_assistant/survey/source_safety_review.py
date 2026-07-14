from __future__ import annotations

import json
import secrets
import stat
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.evidence_semantics import (
    AuthorityConfig,
    AuthoritySnapshot,
    EvidenceContext,
    ImmutableAuthorityManager,
    canonical_semantic_bytes,
    load_v2_evidence_context,
    require_sha256,
    strict_string_list,
)
from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.review_decisions import (
    COMMON_SIDECAR_KEYS,
    atomic_write_json,
    common_sidecar_fields,
    load_bound_decision_envelope,
    normalize_required_text,
    normalize_reviewed_at,
    read_json_object_strict,
    require_exact_keys,
    utc_now_iso,
    validate_exact_decisions,
)
from research_assistant.survey.mission_state import canonical_json_bytes, pretty_json_bytes, sha256_bytes, sha256_file


SURVEY_REVIEWED_SOURCE_SAFETY_RESULT_SCHEMA_VERSION = "ra-survey-reviewed-source-safety-import-result-v2"
SURVEY_REVIEWED_SOURCE_SAFETY_SCHEMA_VERSION = "ra-survey-reviewed-source-safety-v2"
SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA = "ra-survey-source-safety-review-v3"
SURVEY_SOURCE_OBSERVATION_SET_SCHEMA = "ra-survey-source-status-observation-set-v1"
SURVEY_SOURCE_OBSERVATION_MANIFEST_SCHEMA = "ra-survey-source-observation-set-manifest-v1"
SURVEY_SOURCE_OBSERVATION_CURRENT_SCHEMA = "ra-survey-source-observation-current-v1"
SURVEY_REVIEWED_SOURCE_SAFETY_V3_SCHEMA = "ra-survey-reviewed-source-safety-v3"
SURVEY_SOURCE_DECISION_MANIFEST_SCHEMA = "ra-survey-source-decision-set-manifest-v1"
SURVEY_SOURCE_DECISION_CURRENT_SCHEMA = "ra-survey-source-decision-current-v1"

REVIEWED_SOURCE_SAFETY_NONCLAIMS = [
    "complete retraction safety",
    "version correctness at scale",
    "literature completeness",
    "final prose readiness",
    "live web coverage",
    "product readiness",
    "real-agent reliability",
    "scientific correctness",
]
SUPPORTED_CHECKED_STATUSES = {"checked_clear", "quarantined", "blocked"}
CHECKED_CLEAR_EVIDENCE_TYPES = {"public_status_check", "reviewed_primary_source_status"}
FORBIDDEN_EVIDENCE_TYPE_FRAGMENTS = {"metadata", "source_availability", "availability", "citation", "venue", "abstract"}
SOURCE_COMMON_INPUT_KEYS = {
    "queue_item_id",
    "paper_id",
    "checked_status",
    "evidence_type",
    "evidence_source",
    "reviewer",
    "reviewed_at",
    "evidence_note",
}
SOURCE_SIDECAR_KEYS = COMMON_SIDECAR_KEYS | {
    "source_safety",
    "rejected_source_safety",
    "coverage_errors",
    "accepted_source_safety_count",
    "rejected_source_safety_count",
    "checked_clear_count",
    "quarantined_count",
    "blocked_count",
}

SOURCE_OBSERVATION_NONCLAIMS = [
    "authenticated human review",
    "complete source safety",
    "claim truth",
    "literature completeness",
    "live reliability",
    "scientific correctness",
]
SOURCE_V3_ENVELOPE_KEYS = {
    "schema_version", "decision_type", "mission_id", "mission_fingerprint",
    "mission_anchor_generation_id", "artifact_set_id", "queue_semantic_sha256",
    "review_queue_sha256", "observation_set", "decisions",
}
SOURCE_OBSERVATION_SET_KEYS = {
    "schema_version", "mission_id", "mission_fingerprint",
    "mission_anchor_generation_id", "artifact_set_id", "queue_semantic_sha256",
    "review_queue_sha256", "source_intake_status_path", "source_intake_status_sha256",
    "source_intake_status_size_bytes", "source_outcome_ledger_path",
    "source_outcome_ledger_sha256", "source_outcome_ledger_size_bytes", "fixture_only",
    "observations", "what_is_not_concluded", "predecessor_observation_set_id",
    "predecessor_observation_set_manifest_sha256",
}
SOURCE_OBSERVATION_KEYS = {
    "observation_id", "observation_sha256", "queue_item_id",
    "stable_metadata_paper_id", "source_paper_id", "canonical_identifier", "aliases",
    "source_version", "source_record_path", "source_record_sha256",
    "source_record_size_bytes", "provider", "final_url", "status_source", "evidence_class", "observed_at",
    "checks_performed", "outcome", "notices", "fixture_only",
    "claim_support_allowed", "what_is_not_concluded",
}
SOURCE_NOTICE_KEYS = {"notice_type", "source", "observed_at", "detail"}
SOURCE_NOTICE_TYPES = {
    "retracted": "retraction",
    "withdrawn": "withdrawal",
    "expression_of_concern": "expression_of_concern",
    "major_erratum_or_corrigendum": "major_erratum_or_corrigendum",
    "version_conflict": "version_conflict",
    "quarantined": "quarantine",
}
SOURCE_EVIDENCE_CLASSES = {"recorded_status_check", "reviewed_primary_source_status"}
SOURCE_DECISION_COMMON_KEYS = {
    "queue_item_id", "stable_metadata_paper_id", "source_paper_id",
    "observation_set_id", "observation_set_manifest_sha256", "observation_id",
    "observation_sha256", "source_version", "reviewer_authority", "decision",
    "reviewer", "reviewed_at", "reason", "fixture_only",
}
SOURCE_V3_SIDECAR_KEYS = {
    "schema_version", "mission_id", "mission_fingerprint", "mission_anchor_generation_id",
    "artifact_set_id", "queue_semantic_sha256", "review_queue_sha256", "decision_set_id",
    "observation_set_id", "observation_set_manifest_sha256", "decisions_path",
    "decisions_sha256", "decisions_size_bytes", "status", "required_item_ids",
    "supplied_item_ids", "decision_coverage_complete", "source_safety",
    "rejected_source_safety", "coverage_errors", "accepted_source_safety_count",
    "rejected_source_safety_count", "checked_clear_count", "quarantined_count",
    "blocked_count", "ready_for_reviewed_packet", "ready_for_prose", "created_at",
    "what_is_not_concluded",
}
SOURCE_OUTCOMES = {
    "checked_clear_for_recorded_checks", "retracted", "withdrawn",
    "expression_of_concern", "major_erratum_or_corrigendum", "version_conflict",
    "quarantined",
}
SOURCE_CHECKS = [
    "expression_of_concern", "major_erratum_or_corrigendum", "retraction",
    "version_consistency", "withdrawal",
]
SOURCE_REVIEWER_AUTHORITIES = {
    "human_reviewed_status", "model_reviewed_advisory", "legacy_ambiguous_review",
    "rejected_or_blocked",
}

SOURCE_OBSERVATION_CONFIG = AuthorityConfig(
    family="source_observation",
    id_prefix="ss",
    sets_dir_name="observation_sets",
    current_name="OBSERVATION_CURRENT",
    set_id_field="observation_set_id",
    current_manifest_field="observation_set_manifest_sha256",
    semantic_field="observation_set_semantic_sha256",
    manifest_name="observation_set_manifest.json",
    manifest_schema=SURVEY_SOURCE_OBSERVATION_MANIFEST_SCHEMA,
    identity_schema="ra-survey-source-observation-set-identity-v1",
    current_schema=SURVEY_SOURCE_OBSERVATION_CURRENT_SCHEMA,
    predecessor_id_field="predecessor_observation_set_id",
    predecessor_manifest_field="predecessor_observation_set_manifest_sha256",
    artifacts={"status_observations.json": "complete_status_observations"},
    identity_fields=frozenset({
        "mission_id", "mission_fingerprint", "mission_anchor_generation_id",
        "artifact_set_id", "queue_semantic_sha256", "review_queue_sha256",
        "source_intake_status_path", "source_intake_status_sha256",
        "source_intake_status_size_bytes", "source_outcome_ledger_path",
        "source_outcome_ledger_sha256", "source_outcome_ledger_size_bytes",
        "source_record_digests", "observations_sha256", "fixture_only",
        "what_is_not_concluded", "predecessor_observation_set_id",
        "predecessor_observation_set_manifest_sha256",
    }),
    root_allowed_names=frozenset({
        "observation_sets", "decision_sets", "OBSERVATION_CURRENT", "DECISION_CURRENT",
    }),
)
SOURCE_DECISION_CONFIG = AuthorityConfig(
    family="source_decision",
    id_prefix="sd",
    sets_dir_name="decision_sets",
    current_name="DECISION_CURRENT",
    set_id_field="decision_set_id",
    current_manifest_field="decision_set_manifest_sha256",
    semantic_field="decision_set_semantic_sha256",
    manifest_name="decision_set_manifest.json",
    manifest_schema=SURVEY_SOURCE_DECISION_MANIFEST_SCHEMA,
    identity_schema="ra-survey-source-decision-set-identity-v1",
    current_schema=SURVEY_SOURCE_DECISION_CURRENT_SCHEMA,
    predecessor_id_field="predecessor_decision_set_id",
    predecessor_manifest_field="predecessor_decision_set_manifest_sha256",
    artifacts={
        "reviewed_source_safety_decisions.json": "complete_decision_envelope",
        "reviewed_source_safety.json": "normalized_reviewed_source_safety",
    },
    identity_fields=frozenset({
        "mission_id", "mission_fingerprint", "mission_anchor_generation_id",
        "artifact_set_id", "queue_semantic_sha256", "review_queue_sha256",
        "observation_set_id", "observation_set_manifest_sha256", "decisions_sha256",
        "decisions_size_bytes", "normalized_source_safety_sha256",
        "predecessor_decision_set_id", "predecessor_decision_set_manifest_sha256",
    }),
    root_allowed_names=frozenset({
        "observation_sets", "decision_sets", "OBSERVATION_CURRENT", "DECISION_CURRENT",
    }),
)


def import_reviewed_source_safety(
    *, review_queue_path: Path, decisions_path: Path, output_dir: Path, force: bool = False,
    now: Callable[[], str] = utc_now_iso,
    nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
    crash_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    try:
        envelope, raw = read_json_object_strict(decisions_path, label="source-safety decisions")
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir.absolute(), [str(exc)])
    if envelope.get("schema_version") == SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA:
        return _import_v3_source_safety(
            review_queue_path=review_queue_path,
            decisions_path=decisions_path,
            envelope=envelope,
            decisions_raw=raw,
            output_dir=output_dir,
            force=force,
            now=now,
            nonce_factory=nonce_factory,
            crash_hook=crash_hook,
        )
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        if exc.code != "legacy_evidence_authority":
            return _blocked(exc.code, output_dir.absolute(), [str(exc)])
    else:
        return _blocked(
            "legacy_source_review_cannot_authorize_v2",
            output_dir.absolute(),
            ["submit an exact ra-survey-source-safety-review-v3 envelope"],
        )
    return _import_legacy_source_safety(
        review_queue_path=review_queue_path,
        decisions_path=decisions_path,
        output_dir=output_dir,
        force=force,
    )


def _import_legacy_source_safety(
    *, review_queue_path: Path, decisions_path: Path, output_dir: Path, force: bool,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    output_path = output_dir / "reviewed_source_safety.json"
    if output_path.exists() and not force:
        return _blocked("output_exists", output_dir, ["rerun with --force or choose a new --out directory"])
    try:
        context, _, rows, decisions_raw = load_bound_decision_envelope(
            review_queue_path=review_queue_path,
            decisions_path=decisions_path,
            decision_type="source_safety",
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    result = validate_exact_decisions(context=context, rows=rows, validator=_validate_decision)
    checked_clear_count = sum(row["checked_status"] == "checked_clear" for row in result.accepted)
    quarantined_count = sum(row["checked_status"] == "quarantined" for row in result.accepted)
    blocked_count = sum(row["checked_status"] == "blocked" for row in result.accepted)
    payload = {
        "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_SCHEMA_VERSION,
        **common_sidecar_fields(
            context=context,
            decisions_path=decisions_path,
            decisions_raw=decisions_raw,
            result=result,
            created_at=utc_now_iso(),
        ),
        "source_safety": result.accepted,
        "rejected_source_safety": result.rejected,
        "coverage_errors": result.coverage_errors,
        **source_sidecar_expected_fields(result),
    }
    atomic_write_json(output_path, payload)
    return {
        "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_RESULT_SCHEMA_VERSION,
        "status": "reviewed_source_safety_complete" if result.complete else "blocked_invalid_source_safety_decisions",
        "output_dir": str(output_dir),
        "reviewed_source_safety_path": str(output_path),
        "accepted_source_safety_count": len(result.accepted),
        "rejected_source_safety_count": len(result.rejected),
        "checked_clear_count": checked_clear_count,
        "quarantined_count": quarantined_count,
        "blocked_count": blocked_count,
        "decision_coverage_complete": result.complete,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_SOURCE_SAFETY_NONCLAIMS,
    }


def _import_v3_source_safety(
    *,
    review_queue_path: Path,
    decisions_path: Path,
    envelope: dict[str, Any],
    decisions_raw: bytes,
    output_dir: Path,
    force: bool,
    now: Callable[[], str],
    nonce_factory: Callable[[], str],
    crash_hook: Callable[[str], None] | None,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    try:
        if decisions_raw != pretty_json_bytes(envelope):
            raise MissionStateError("noncanonical_source_review", "V3 source review must be canonical pretty JSON")
        context = load_v2_evidence_context(review_queue_path)
        require_exact_keys(envelope, SOURCE_V3_ENVELOPE_KEYS, "V3 source-safety envelope")
        if envelope.get("decision_type") != "source_safety":
            raise MissionStateError("wrong_decision_type", "V3 source review has the wrong decision type")
        _require_binding(envelope, context)

        observation_manager = ImmutableAuthorityManager(
            root=output_dir,
            config=SOURCE_OBSERVATION_CONFIG,
            nonce_factory=nonce_factory,
            crash_hook=crash_hook,
        )
        selected_observation = observation_manager.load_predecessor_for_update()
        observation_set = _validate_observation_set(
            envelope.get("observation_set"),
            context=context,
            selected=selected_observation,
        )
        observation_raw = pretty_json_bytes(observation_set)
        observation_identity = _observation_identity(observation_set, context)
        observation_set_id, observation_manifest = observation_manager.preview(
            identity_fields=observation_identity,
            artifacts={"status_observations.json": observation_raw},
        )
        observation_manifest_sha256 = sha256_bytes(canonical_json_bytes(observation_manifest))
        rows = _validate_v3_source_decisions(
            envelope.get("decisions"),
            context=context,
            observation_set=observation_set,
            observation_set_id=observation_set_id,
            observation_manifest_sha256=observation_manifest_sha256,
        )
        required_ids = sorted(context.source_identities)
        supplied_ids = sorted(row["queue_item_id"] for row in rows)
        semantic_payload = _source_semantic_payload(
            context=context,
            observation_set_id=observation_set_id,
            observation_manifest_sha256=observation_manifest_sha256,
            rows=rows,
            required_ids=required_ids,
            supplied_ids=supplied_ids,
        )
        normalized_hash = sha256_bytes(canonical_semantic_bytes(
            _source_normalized_projection(context=context, semantic=semantic_payload)
        ))
        decision_manager = ImmutableAuthorityManager(
            root=output_dir,
            config=SOURCE_DECISION_CONFIG,
            nonce_factory=nonce_factory,
            crash_hook=crash_hook,
        )
        selected_decision = decision_manager.load_predecessor_for_update()
        exact_replay = selected_decision is not None and all([
            selected_decision.manifest.get("observation_set_id") == observation_set_id,
            selected_decision.manifest.get("observation_set_manifest_sha256") == observation_manifest_sha256,
            selected_decision.manifest.get("decisions_sha256") == sha256_bytes(decisions_raw),
            selected_decision.manifest.get("decisions_size_bytes") == len(decisions_raw),
            selected_decision.manifest.get("normalized_source_safety_sha256") == normalized_hash,
        ])
        predecessor_id = (
            selected_decision.manifest["predecessor_decision_set_id"]
            if exact_replay
            else selected_decision.set_id
            if selected_decision is not None
            else None
        )
        predecessor_hash = (
            selected_decision.manifest["predecessor_decision_set_manifest_sha256"]
            if exact_replay
            else sha256_file(selected_decision.set_dir / SOURCE_DECISION_CONFIG.manifest_name)
            if selected_decision is not None
            else None
        )
        decision_identity = {
            **context.binding,
            "observation_set_id": observation_set_id,
            "observation_set_manifest_sha256": observation_manifest_sha256,
            "decisions_sha256": sha256_bytes(decisions_raw),
            "decisions_size_bytes": len(decisions_raw),
            "normalized_source_safety_sha256": normalized_hash,
            "predecessor_decision_set_id": predecessor_id,
            "predecessor_decision_set_manifest_sha256": predecessor_hash,
        }
        decision_set_id, _ = decision_manager.preview(
            identity_fields=decision_identity,
            artifacts={
                "reviewed_source_safety_decisions.json": decisions_raw,
                "reviewed_source_safety.json": b"",
            },
        )
        sidecar_without_created_at = {
            "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_V3_SCHEMA,
            **context.binding,
            "decision_set_id": decision_set_id,
            "observation_set_id": observation_set_id,
            "observation_set_manifest_sha256": observation_manifest_sha256,
            "decisions_path": str(
                decision_manager.sets_dir / decision_set_id / "reviewed_source_safety_decisions.json"
            ),
            "decisions_sha256": sha256_bytes(decisions_raw),
            "decisions_size_bytes": len(decisions_raw),
            **semantic_payload,
        }
        created_at = decision_manager.preserve_staged_created_at(
            set_id=decision_set_id,
            artifact_name="reviewed_source_safety.json",
            expected_without_created_at=sidecar_without_created_at,
            fallback=now(),
        )
        sidecar = {**sidecar_without_created_at, "created_at": created_at}
        require_exact_keys(sidecar, SOURCE_V3_SIDECAR_KEYS, "V3 reviewed source-safety sidecar")
        sidecar_raw = pretty_json_bytes(sidecar)
        observation_snapshot = observation_manager.compose_and_select(
            identity_fields=observation_identity,
            artifacts={"status_observations.json": observation_raw},
            force=force,
        )
        if (
            observation_snapshot.set_id != observation_set_id
            or sha256_file(observation_snapshot.set_dir / SOURCE_OBSERVATION_CONFIG.manifest_name)
            != observation_manifest_sha256
        ):
            raise MissionStateError("source_observation_selection_mismatch", "selected observation set differs from review")
        decision_snapshot = decision_manager.compose_and_select(
            identity_fields=decision_identity,
            artifacts={
                "reviewed_source_safety_decisions.json": decisions_raw,
                "reviewed_source_safety.json": sidecar_raw,
            },
            force=force,
        )
        _validate_v3_selected_source_authority(
            context=context,
            observation_snapshot=observation_snapshot,
            decision_snapshot=decision_snapshot,
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    return {
        "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_RESULT_SCHEMA_VERSION,
        "status": "reviewed_source_safety_complete",
        "output_dir": str(output_dir),
        "reviewed_source_safety_path": str(decision_snapshot.artifact_paths["reviewed_source_safety.json"]),
        "observation_set_id": observation_snapshot.set_id,
        "decision_set_id": decision_snapshot.set_id,
        "accepted_source_safety_count": len(rows),
        "rejected_source_safety_count": 0,
        "checked_clear_count": sum(row["decision"] == "checked_clear" for row in rows),
        "quarantined_count": sum(row["decision"] == "quarantined" for row in rows),
        "blocked_count": sum(row["decision"] == "blocked" for row in rows),
        "decision_coverage_complete": True,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_SOURCE_SAFETY_NONCLAIMS,
    }


def resolve_current_source_safety(
    *,
    review_queue_path: Path,
    reviewed_source_safety_root: Path,
    supplied_sidecar_path: Path | None = None,
) -> tuple[AuthoritySnapshot, AuthoritySnapshot, dict[str, Any]]:
    context = load_v2_evidence_context(review_queue_path)
    root = reviewed_source_safety_root.absolute()
    observation_manager = ImmutableAuthorityManager(root=root, config=SOURCE_OBSERVATION_CONFIG)
    decision_manager = ImmutableAuthorityManager(root=root, config=SOURCE_DECISION_CONFIG)
    observation = observation_manager.load_current(required=True)
    decision = decision_manager.load_current(required=True)
    assert observation is not None and decision is not None
    sidecar = _validate_v3_selected_source_authority(
        context=context,
        observation_snapshot=observation,
        decision_snapshot=decision,
    )
    selected_path = decision.artifact_paths["reviewed_source_safety.json"]
    if supplied_sidecar_path is not None:
        supplied = supplied_sidecar_path.absolute()
        if (
            supplied.is_symlink()
            or supplied != selected_path.absolute()
            or supplied.resolve() != selected_path.resolve()
        ):
            raise MissionStateError(
                "stale_source_decision_selector",
                "supplied source-safety sidecar is not selected by DECISION_CURRENT",
            )
    return observation, decision, sidecar


def preview_source_observation_binding(
    *,
    review_queue_path: Path,
    observation_set: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    context = load_v2_evidence_context(review_queue_path)
    manager = ImmutableAuthorityManager(root=output_dir.absolute(), config=SOURCE_OBSERVATION_CONFIG)
    selected = manager.load_predecessor_for_update()
    normalized = _validate_observation_set(
        observation_set,
        context=context,
        selected=selected,
    )
    raw = pretty_json_bytes(normalized)
    set_id, manifest = manager.preview(
        identity_fields=_observation_identity(normalized, context),
        artifacts={"status_observations.json": raw},
    )
    return {
        "observation_set_id": set_id,
        "observation_set_manifest_sha256": sha256_bytes(canonical_json_bytes(manifest)),
    }


def resolve_current_source_safety_sidecar_path(
    *, review_queue_path: Path, sidecar_path: Path,
) -> Path:
    supplied = sidecar_path.absolute()
    root = supplied.parent.parent.parent if supplied.parent.parent.name == "decision_sets" else supplied.parent
    _, decision, _ = resolve_current_source_safety(
        review_queue_path=review_queue_path,
        reviewed_source_safety_root=root,
        supplied_sidecar_path=supplied,
    )
    return decision.artifact_paths["reviewed_source_safety.json"]


def _require_binding(value: dict[str, Any], context: EvidenceContext) -> None:
    for field, expected in context.binding.items():
        if value.get(field) != expected:
            code = "foreign_lineage" if field in {"mission_id", "mission_fingerprint"} else "stale_lineage"
            raise MissionStateError(code, f"V3 source review {field} differs from selected authority")


def _validate_observation_set(
    value: Any,
    *,
    context: EvidenceContext,
    selected: AuthoritySnapshot | None,
) -> dict[str, Any]:
    require_exact_keys(value, SOURCE_OBSERVATION_SET_KEYS, "source observation set")
    result = dict(value)
    if result.get("schema_version") != SURVEY_SOURCE_OBSERVATION_SET_SCHEMA:
        raise MissionStateError("invalid_source_observation_schema", "source observation-set schema is unsupported")
    _require_binding(result, context)
    status = context.validated_source_intake["status"]
    status_raw = context.validated_source_intake["status_bytes"]
    ledger_path = Path(status["outcome_ledger_path"])
    ledger_raw = ledger_path.read_bytes()
    expected_source_binding = {
        "source_intake_status_path": str(context.mission_root / "source_intake" / "phase4_source_intake_status.json"),
        "source_intake_status_sha256": sha256_bytes(status_raw),
        "source_intake_status_size_bytes": len(status_raw),
        "source_outcome_ledger_path": str(ledger_path),
        "source_outcome_ledger_sha256": sha256_bytes(ledger_raw),
        "source_outcome_ledger_size_bytes": len(ledger_raw),
    }
    for field, expected in expected_source_binding.items():
        if result.get(field) != expected:
            raise MissionStateError("stale_source_observation", f"source observation set differs on {field}")
    if result.get("fixture_only") is not True:
        raise MissionStateError("invalid_source_observation", "Phase 9 source observations must disclose fixture_only=true")
    if result.get("what_is_not_concluded") != SOURCE_OBSERVATION_NONCLAIMS:
        raise MissionStateError("invalid_source_observation", "source observation nonclaims differ")
    predecessor_id = result.get("predecessor_observation_set_id")
    predecessor_hash = result.get("predecessor_observation_set_manifest_sha256")
    if (predecessor_id is None) != (predecessor_hash is None):
        raise MissionStateError("invalid_source_observation_predecessor", "observation predecessor pair is partial")
    if predecessor_id is not None:
        if not isinstance(predecessor_id, str) or not predecessor_id.startswith("ss-"):
            raise MissionStateError("invalid_source_observation_predecessor", "observation predecessor ID is invalid")
        require_sha256(predecessor_hash, field="predecessor_observation_set_manifest_sha256")
    rows = result.get("observations")
    if not isinstance(rows, list):
        raise MissionStateError("invalid_source_observations", "source observations must be a list")
    normalized = [_validate_observation(row, context=context) for row in rows]
    expected_ids = sorted(context.source_identities)
    supplied_ids = [row["queue_item_id"] for row in normalized]
    if normalized != sorted(normalized, key=lambda row: row["queue_item_id"]):
        raise MissionStateError("unsorted_source_observations", "source observations must be queue-item sorted")
    if supplied_ids != expected_ids or len(supplied_ids) != len(set(supplied_ids)):
        raise MissionStateError("incomplete_source_observations", "source observations do not exactly cover source-safety queue items")
    result["observations"] = normalized
    return result


def _validate_observation(value: Any, *, context: EvidenceContext) -> dict[str, Any]:
    require_exact_keys(value, SOURCE_OBSERVATION_KEYS, "source observation")
    row = dict(value)
    item_id = normalize_required_text(row.get("queue_item_id"), field="queue_item_id")
    identity = context.source_identities.get(item_id)
    if identity is None:
        raise MissionStateError("foreign_source_observation", "source observation names a foreign queue item")
    expected_identity = asdict(identity)
    expected_identity.pop("queue_item_id")
    for field, expected in expected_identity.items():
        if row.get(field) != expected:
            raise MissionStateError("source_observation_identity_mismatch", f"source observation differs on {field}")
    status_source = normalize_required_text(row.get("status_source"), field="status_source")
    evidence_class = normalize_required_text(row.get("evidence_class"), field="evidence_class")
    if evidence_class not in SOURCE_EVIDENCE_CLASSES or any(
        fragment in evidence_class.casefold()
        for fragment in FORBIDDEN_EVIDENCE_TYPE_FRAGMENTS
    ):
        raise MissionStateError("invalid_source_observation_evidence", "source evidence class cannot authorize from metadata or availability")
    observed_at = normalize_reviewed_at(row.get("observed_at"))
    checks = strict_string_list(row.get("checks_performed"), field="checks_performed")
    outcome = normalize_required_text(row.get("outcome"), field="outcome")
    if outcome not in SOURCE_OUTCOMES:
        raise MissionStateError("invalid_source_observation_outcome", "source observation outcome is not closed")
    notices = _validate_notices(row.get("notices"), outcome=outcome)
    if outcome == "checked_clear_for_recorded_checks":
        if checks != SOURCE_CHECKS or notices:
            raise MissionStateError("invalid_checked_clear_observation", "checked-clear requires the exact check set and no notices")
    elif not notices:
        raise MissionStateError("missing_source_notice", "nonclear source outcome requires a matching notice")
    if row.get("fixture_only") is not True or row.get("claim_support_allowed") is not False:
        raise MissionStateError("false_source_observation_authority", "source observation cannot itself authorize claim support")
    if row.get("what_is_not_concluded") != SOURCE_OBSERVATION_NONCLAIMS:
        raise MissionStateError("invalid_source_observation", "source observation nonclaims differ")
    semantic = {
        "schema_version": "ra-survey-source-status-observation-identity-v1",
        "queue_item_id": item_id,
        **expected_identity,
        "status_source": status_source,
        "evidence_class": evidence_class,
        "observed_at": observed_at,
        "checks_performed": checks,
        "outcome": outcome,
        "notices": notices,
        "fixture_only": True,
        "claim_support_allowed": False,
        "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
    }
    digest = sha256_bytes(canonical_json_bytes(semantic))
    if row.get("observation_sha256") != digest or row.get("observation_id") != f"so-{digest}":
        raise MissionStateError("invalid_source_observation_identity", "source observation ID or hash differs")
    return {
        "observation_id": f"so-{digest}",
        "observation_sha256": digest,
        **{key: value for key, value in semantic.items() if key != "schema_version"},
    }


def _validate_notices(value: Any, *, outcome: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_source_notices", "source notices must be a list")
    notices: list[dict[str, Any]] = []
    for notice in value:
        require_exact_keys(notice, SOURCE_NOTICE_KEYS, "source notice")
        normalized = {
            "notice_type": normalize_required_text(notice.get("notice_type"), field="notice_type"),
            "source": normalize_required_text(notice.get("source"), field="notice source"),
            "observed_at": normalize_reviewed_at(notice.get("observed_at")),
            "detail": normalize_required_text(notice.get("detail"), field="notice detail"),
        }
        notices.append(normalized)
    if notices != sorted(notices, key=canonical_json_bytes) or len({canonical_json_bytes(row) for row in notices}) != len(notices):
        raise MissionStateError("invalid_source_notices", "source notices must be canonical-sorted and unique")
    expected_type = SOURCE_NOTICE_TYPES.get(outcome)
    if expected_type is not None and any(row["notice_type"] != expected_type for row in notices):
        raise MissionStateError("source_notice_mismatch", "source notice type does not match outcome")
    return notices


def _observation_identity(value: dict[str, Any], context: EvidenceContext) -> dict[str, Any]:
    source_record_digests = [
        {
            "queue_item_id": identity.queue_item_id,
            "source_paper_id": identity.source_paper_id,
            "source_version": identity.source_version,
            "source_record_sha256": identity.source_record_sha256,
            "source_record_size_bytes": identity.source_record_size_bytes,
        }
        for identity in sorted(context.source_identities.values(), key=lambda item: item.queue_item_id)
    ]
    return {
        **context.binding,
        "source_intake_status_path": value["source_intake_status_path"],
        "source_intake_status_sha256": value["source_intake_status_sha256"],
        "source_intake_status_size_bytes": value["source_intake_status_size_bytes"],
        "source_outcome_ledger_path": value["source_outcome_ledger_path"],
        "source_outcome_ledger_sha256": value["source_outcome_ledger_sha256"],
        "source_outcome_ledger_size_bytes": value["source_outcome_ledger_size_bytes"],
        "source_record_digests": source_record_digests,
        "observations_sha256": sha256_bytes(canonical_semantic_bytes(value["observations"])),
        "fixture_only": True,
        "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        "predecessor_observation_set_id": value["predecessor_observation_set_id"],
        "predecessor_observation_set_manifest_sha256": value["predecessor_observation_set_manifest_sha256"],
    }


def _validate_v3_source_decisions(
    value: Any,
    *,
    context: EvidenceContext,
    observation_set: dict[str, Any],
    observation_set_id: str,
    observation_manifest_sha256: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_source_decisions", "source decisions must be a list")
    observations = {row["queue_item_id"]: row for row in observation_set["observations"]}
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict):
            raise MissionStateError("invalid_source_decisions", f"source decision row {index} is not an object")
        decision = normalize_required_text(raw.get("decision"), field="decision")
        expected_keys = set(SOURCE_DECISION_COMMON_KEYS)
        if decision == "blocked":
            expected_keys.add("next_action")
        require_exact_keys(raw, expected_keys, f"source decision row {index}")
        item_id = normalize_required_text(raw.get("queue_item_id"), field="queue_item_id")
        identity = context.source_identities.get(item_id)
        observation = observations.get(item_id)
        if identity is None or observation is None:
            raise MissionStateError("foreign_source_decision", "source decision names a foreign observation")
        exact = {
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "observation_set_id": observation_set_id,
            "observation_set_manifest_sha256": observation_manifest_sha256,
            "observation_id": observation["observation_id"],
            "observation_sha256": observation["observation_sha256"],
            "source_version": identity.source_version,
        }
        for field, expected in exact.items():
            if raw.get(field) != expected:
                raise MissionStateError("source_decision_binding_mismatch", f"source decision differs on {field}")
        reviewer_authority = normalize_required_text(raw.get("reviewer_authority"), field="reviewer_authority")
        if reviewer_authority not in SOURCE_REVIEWER_AUTHORITIES:
            raise MissionStateError("invalid_source_reviewer_authority", "source reviewer authority is not closed")
        if decision not in {"checked_clear", "quarantined", "blocked"}:
            raise MissionStateError("invalid_source_decision", "source decision is not closed")
        observation_outcome = observation["outcome"]
        if decision == "checked_clear" and (
            reviewer_authority != "human_reviewed_status"
            or observation_outcome != "checked_clear_for_recorded_checks"
        ):
            raise MissionStateError("unauthorized_checked_clear", "checked-clear requires human-shaped authority and an exact clear observation")
        if decision == "quarantined" and (
            reviewer_authority != "human_reviewed_status"
            or observation_outcome == "checked_clear_for_recorded_checks"
        ):
            raise MissionStateError("invalid_source_quarantine", "quarantine requires human-shaped authority and a nonclear observation")
        if reviewer_authority != "human_reviewed_status" and decision != "blocked":
            raise MissionStateError("unauthorized_source_promotion", "model, legacy, or rejected authority must remain blocked")
        fixture_only = raw.get("fixture_only")
        if fixture_only is not True:
            raise MissionStateError("invalid_source_decision", "synthetic Phase 9 decisions must disclose fixture_only=true")
        normalized_row = {
            "queue_item_id": item_id,
            **exact,
            "reviewer_authority": reviewer_authority,
            "decision": decision,
            "reviewer": normalize_required_text(raw.get("reviewer"), field="reviewer"),
            "reviewed_at": normalize_reviewed_at(raw.get("reviewed_at")),
            "reason": normalize_required_text(raw.get("reason"), field="reason"),
            **({"next_action": normalize_required_text(raw.get("next_action"), field="next_action")} if decision == "blocked" else {}),
            "fixture_only": True,
            "observation_outcome": observation_outcome,
            "safety_checked_clear": decision == "checked_clear",
            "claim_support_allowed": decision == "checked_clear",
            "omission_review_required": decision != "checked_clear",
            "ready_for_prose": False,
            "what_is_not_concluded": REVIEWED_SOURCE_SAFETY_NONCLAIMS,
        }
        digest = sha256_bytes(canonical_json_bytes({
            "schema_version": "ra-survey-normalized-source-decision-identity-v1",
            "decision": normalized_row,
        }))
        normalized.append({**normalized_row, "decision_sha256": digest})
    normalized.sort(key=lambda row: row["queue_item_id"])
    ids = [row["queue_item_id"] for row in normalized]
    required = sorted(context.source_identities)
    if ids != required or len(ids) != len(set(ids)) or len(value) != len(required):
        raise MissionStateError("incomplete_source_decisions", "source decisions do not exactly cover source-safety observations")
    return normalized


def _source_semantic_payload(
    *,
    context: EvidenceContext,
    observation_set_id: str,
    observation_manifest_sha256: str,
    rows: list[dict[str, Any]],
    required_ids: list[str],
    supplied_ids: list[str],
) -> dict[str, Any]:
    return {
        "status": "reviewed_source_safety_complete",
        "required_item_ids": required_ids,
        "supplied_item_ids": supplied_ids,
        "decision_coverage_complete": required_ids == supplied_ids,
        "source_safety": rows,
        "rejected_source_safety": [],
        "coverage_errors": [],
        "accepted_source_safety_count": len(rows),
        "rejected_source_safety_count": 0,
        "checked_clear_count": sum(row["decision"] == "checked_clear" for row in rows),
        "quarantined_count": sum(row["decision"] == "quarantined" for row in rows),
        "blocked_count": sum(row["decision"] == "blocked" for row in rows),
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_SOURCE_SAFETY_NONCLAIMS,
    }


def _source_normalized_projection(
    *, context: EvidenceContext, semantic: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_V3_SCHEMA,
        **context.binding,
        **semantic,
    }


def _validate_v3_selected_source_authority(
    *,
    context: EvidenceContext,
    observation_snapshot: AuthoritySnapshot,
    decision_snapshot: AuthoritySnapshot,
) -> dict[str, Any]:
    observation_payload, observation_raw = read_json_object_strict(
        observation_snapshot.artifact_paths["status_observations.json"],
        label="selected source observations",
    )
    if observation_raw != pretty_json_bytes(observation_payload):
        raise MissionStateError("noncanonical_source_observations", "selected source observations are noncanonical")
    replayed_observation = _validate_observation_set(
        observation_payload,
        context=context,
        selected=observation_snapshot,
    )
    observation_identity = _observation_identity(replayed_observation, context)
    observation_manager = ImmutableAuthorityManager(
        root=observation_snapshot.set_dir.parent.parent,
        config=SOURCE_OBSERVATION_CONFIG,
    )
    expected_observation_id, expected_observation_manifest = observation_manager.preview(
        identity_fields=observation_identity,
        artifacts={"status_observations.json": observation_raw},
    )
    if (
        expected_observation_id != observation_snapshot.set_id
        or expected_observation_manifest != observation_snapshot.manifest
    ):
        raise MissionStateError("invalid_source_observation_replay", "selected observation authority does not replay")
    envelope, envelope_raw = read_json_object_strict(
        decision_snapshot.artifact_paths["reviewed_source_safety_decisions.json"],
        label="selected source review envelope",
    )
    if envelope_raw != pretty_json_bytes(envelope):
        raise MissionStateError("noncanonical_source_review", "selected source review envelope is noncanonical")
    require_exact_keys(envelope, SOURCE_V3_ENVELOPE_KEYS, "selected source review envelope")
    _require_binding(envelope, context)
    if envelope.get("observation_set") != replayed_observation:
        raise MissionStateError("mixed_source_authority", "selected decision envelope embeds another observation set")
    observation_manifest_hash = sha256_file(observation_snapshot.set_dir / SOURCE_OBSERVATION_CONFIG.manifest_name)
    rows = _validate_v3_source_decisions(
        envelope.get("decisions"),
        context=context,
        observation_set=replayed_observation,
        observation_set_id=observation_snapshot.set_id,
        observation_manifest_sha256=observation_manifest_hash,
    )
    sidecar, sidecar_raw = read_json_object_strict(
        decision_snapshot.artifact_paths["reviewed_source_safety.json"],
        label="selected reviewed source safety",
    )
    if sidecar_raw != pretty_json_bytes(sidecar):
        raise MissionStateError("noncanonical_source_sidecar", "selected source sidecar is noncanonical")
    require_exact_keys(sidecar, SOURCE_V3_SIDECAR_KEYS, "selected reviewed source safety")
    semantic = _source_semantic_payload(
        context=context,
        observation_set_id=observation_snapshot.set_id,
        observation_manifest_sha256=observation_manifest_hash,
        rows=rows,
        required_ids=sorted(context.source_identities),
        supplied_ids=sorted(row["queue_item_id"] for row in rows),
    )
    expected_sidecar = {
        "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_V3_SCHEMA,
        **context.binding,
        "decision_set_id": decision_snapshot.set_id,
        "observation_set_id": observation_snapshot.set_id,
        "observation_set_manifest_sha256": observation_manifest_hash,
        "decisions_path": str(decision_snapshot.artifact_paths["reviewed_source_safety_decisions.json"]),
        "decisions_sha256": sha256_bytes(envelope_raw),
        "decisions_size_bytes": len(envelope_raw),
        **semantic,
        "created_at": normalize_reviewed_at(sidecar.get("created_at")),
    }
    if sidecar != expected_sidecar:
        raise MissionStateError("invalid_source_sidecar_replay", "selected source sidecar differs from envelope replay")
    normalized_hash = sha256_bytes(canonical_semantic_bytes(
        _source_normalized_projection(context=context, semantic=semantic)
    ))
    expected_identity = {
        **context.binding,
        "observation_set_id": observation_snapshot.set_id,
        "observation_set_manifest_sha256": observation_manifest_hash,
        "decisions_sha256": sha256_bytes(envelope_raw),
        "decisions_size_bytes": len(envelope_raw),
        "normalized_source_safety_sha256": normalized_hash,
        "predecessor_decision_set_id": decision_snapshot.manifest["predecessor_decision_set_id"],
        "predecessor_decision_set_manifest_sha256": decision_snapshot.manifest["predecessor_decision_set_manifest_sha256"],
    }
    decision_manager = ImmutableAuthorityManager(
        root=decision_snapshot.set_dir.parent.parent,
        config=SOURCE_DECISION_CONFIG,
    )
    expected_id, expected_manifest = decision_manager.preview(
        identity_fields=expected_identity,
        artifacts={
            "reviewed_source_safety_decisions.json": envelope_raw,
            "reviewed_source_safety.json": sidecar_raw,
        },
    )
    if expected_id != decision_snapshot.set_id or expected_manifest != decision_snapshot.manifest:
        raise MissionStateError("invalid_source_decision_replay", "selected source decision authority does not replay")
    return sidecar


def _validate_decision(row: Any, queue_item: dict[str, Any] | None, index: int) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(row, dict):
        return {}, [f"row {index} is not an object"]
    reasons: list[str] = []
    checked_status = _text(row.get("checked_status"), "checked_status", reasons).lower()
    expected = set(SOURCE_COMMON_INPUT_KEYS)
    if checked_status in {"quarantined", "blocked"}:
        expected |= {"reason", "next_action"}
    try:
        require_exact_keys(row, expected, f"source-safety decision row {index}")
    except MissionStateError as exc:
        reasons.append(str(exc))
    paper_id = _text(row.get("paper_id"), "paper_id", reasons)
    evidence_type = _text(row.get("evidence_type"), "evidence_type", reasons).lower()
    evidence_source = _text(row.get("evidence_source"), "evidence_source", reasons)
    reviewer = _text(row.get("reviewer"), "reviewer", reasons)
    reviewed_at = _time(row.get("reviewed_at"), reasons)
    evidence_note = _text(row.get("evidence_note"), "evidence_note", reasons)
    if checked_status not in SUPPORTED_CHECKED_STATUSES:
        reasons.append("checked_status must be checked_clear, quarantined, or blocked")
    if any(fragment in evidence_type for fragment in FORBIDDEN_EVIDENCE_TYPE_FRAGMENTS):
        reasons.append("evidence_type cannot be metadata, source availability, citation, venue, abstract, or context-only")
    if checked_status == "checked_clear" and evidence_type not in CHECKED_CLEAR_EVIDENCE_TYPES:
        reasons.append("checked_clear requires public_status_check or reviewed_primary_source_status evidence")
    if queue_item is not None:
        if paper_id != str(queue_item.get("paper_id") or ""):
            reasons.append("paper_id must match the referenced source_safety queue item")
        if queue_item.get("safety_checked_clear") is not False or queue_item.get("claim_support_allowed") is not False:
            reasons.append("referenced source_safety queue item must start blocked and unchecked")
    normalized = {
        "paper_id": paper_id,
        "arxiv_id": queue_item.get("arxiv_id") if queue_item else None,
        "checked_status": checked_status,
        "evidence_type": evidence_type,
        "evidence_source": evidence_source,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "evidence_note": evidence_note,
        "reason": _text(row.get("reason"), "reason", reasons) if checked_status in {"quarantined", "blocked"} else "",
        "next_action": _text(row.get("next_action"), "next_action", reasons) if checked_status in {"quarantined", "blocked"} else "",
        "safety_checked_clear": checked_status == "checked_clear",
        "claim_support_allowed": checked_status == "checked_clear",
        "omission_review_required": True,
        "ready_for_prose": False,
    }
    return normalized, reasons


def source_sidecar_expected_fields(result: Any) -> dict[str, Any]:
    return {
        "status": "reviewed_source_safety_complete" if result.complete else "blocked_invalid_source_safety_decisions",
        "accepted_source_safety_count": len(result.accepted),
        "rejected_source_safety_count": len(result.rejected),
        "checked_clear_count": sum(row["checked_status"] == "checked_clear" for row in result.accepted),
        "quarantined_count": sum(row["checked_status"] == "quarantined" for row in result.accepted),
        "blocked_count": sum(row["checked_status"] == "blocked" for row in result.accepted),
        "what_is_not_concluded": REVIEWED_SOURCE_SAFETY_NONCLAIMS,
    }


def _text(value: Any, field: str, reasons: list[str]) -> str:
    try:
        return normalize_required_text(value, field=field)
    except MissionStateError as exc:
        reasons.append(str(exc)); return ""


def _time(value: Any, reasons: list[str]) -> str:
    try:
        return normalize_reviewed_at(value)
    except MissionStateError as exc:
        reasons.append(str(exc)); return ""


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_SOURCE_SAFETY_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": REVIEWED_SOURCE_SAFETY_NONCLAIMS,
    }


__all__ = [
    "REVIEWED_SOURCE_SAFETY_NONCLAIMS",
    "SOURCE_CHECKS",
    "SOURCE_DECISION_CONFIG",
    "SOURCE_OBSERVATION_NONCLAIMS",
    "SOURCE_OBSERVATION_CONFIG",
    "SOURCE_SIDECAR_KEYS",
    "SURVEY_REVIEWED_SOURCE_SAFETY_V3_SCHEMA",
    "SURVEY_REVIEWED_SOURCE_SAFETY_SCHEMA_VERSION",
    "SURVEY_SOURCE_OBSERVATION_SET_SCHEMA",
    "SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA",
    "_validate_decision",
    "import_reviewed_source_safety",
    "preview_source_observation_binding",
    "resolve_current_source_safety",
    "resolve_current_source_safety_sidecar_path",
    "source_sidecar_expected_fields",
]
