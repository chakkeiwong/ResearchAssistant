from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path, PurePosixPath
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
from research_assistant.survey.mission_state import canonical_json_bytes, pretty_json_bytes, sha256_bytes, sha256_file
from research_assistant.survey.human_attestation import (
    CLAIM_V4_SCHEMA,
    export_human_receipt_archive,
    validate_human_receipt_archive,
    validate_human_receipt_decision,
)
from research_assistant.survey.review_decisions import (
    COMMON_SIDECAR_KEYS,
    ExactDecisionResult,
    atomic_write_json,
    common_sidecar_fields,
    load_bound_decision_envelope,
    normalize_required_text,
    normalize_reviewed_at,
    normalize_string_list,
    read_json_object_strict,
    require_exact_keys,
    require_lower_hex,
    utc_now_iso,
    validate_exact_decisions,
)
from research_assistant.survey.supervisor import validate_anchor_packet


SURVEY_REVIEWED_CLAIMS_RESULT_SCHEMA_VERSION = "ra-survey-reviewed-claim-import-result-v2"
SURVEY_REVIEWED_CLAIMS_SCHEMA_VERSION = "ra-survey-reviewed-claims-v2"
SURVEY_CLAIM_REVIEW_V3_SCHEMA = "ra-survey-claim-review-v3"
SURVEY_CLAIM_REVIEW_V4_SCHEMA = CLAIM_V4_SCHEMA
SURVEY_CLAIM_AUTHORITY_V4_SCHEMA = "ra-survey-claim-review-authority-v4"
SURVEY_REVIEWED_CLAIMS_V3_SCHEMA = "ra-survey-reviewed-claims-v3"
SURVEY_REVIEWED_CLAIMS_V4_SCHEMA = "ra-survey-reviewed-claims-v4"
SURVEY_CLAIM_DECISION_MANIFEST_SCHEMA = "ra-survey-claim-decision-set-manifest-v1"
SURVEY_CLAIM_DECISION_CURRENT_SCHEMA = "ra-survey-claim-decision-current-v1"
SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA = "ra-survey-claim-dependency-manifest-v1"

REVIEWED_CLAIM_NONCLAIMS = [
    "source safety",
    "literature completeness",
    "final prose readiness",
    "live web coverage",
    "product readiness",
    "real-agent reliability",
    "scientific correctness",
]

SUPPORTED_REVIEW_STATUSES = {
    "reviewed_passed",
    "human_reviewed_passed",
    "model_reviewed_passed",
}
SUPPORTED_CLAIM_CLASSES = {
    "primary_technical_support",
    "project_derivation",
    "implementation_evidence",
}
CLAIM_COMMON_INPUT_KEYS = {
    "queue_item_id",
    "claim_id",
    "claim_text",
    "review_status",
    "support_class",
    "reviewer",
    "reviewed_at",
    "evidence_note",
}
CLAIM_SIDECAR_KEYS = COMMON_SIDECAR_KEYS | {
    "claims",
    "rejected_claims",
    "coverage_errors",
    "accepted_claim_count",
    "rejected_claim_count",
}

CLAIM_V3_ENVELOPE_KEYS = {
    "schema_version", "decision_type", "mission_id", "mission_fingerprint",
    "mission_anchor_generation_id", "artifact_set_id", "queue_semantic_sha256",
    "review_queue_sha256", "decisions",
}
CLAIM_V4_AUTHORITY_ENVELOPE_KEYS = {
    "schema_version", "decision_type", "mission_id", "mission_fingerprint",
    "mission_anchor_generation_id", "artifact_set_id", "queue_semantic_sha256",
    "review_queue_sha256", "attested_decisions", "human_receipt_archive",
}
CLAIM_V3_COMMON_KEYS = {
    "queue_item_id", "claim_id", "claim_text", "claim_type", "support_class",
    "review_status", "reviewer", "reviewed_at", "evidence_note", "fixture_only",
}
CLAIM_V3_SUPPORT_KEYS = {
    "source_dependencies", "dependency_manifests", "root_dependency_manifest_id",
    "dependency_graph_sha256",
}
CLAIM_DEPENDENCY_KEYS = {
    "stable_metadata_paper_id", "source_paper_id", "canonical_identifier",
    "source_version", "source_record_sha256", "dependency_role",
}
CLAIM_DEPENDENCY_MANIFEST_KEYS = {
    "schema_version", "manifest_id", "evidence_kind", "local_artifact",
    "local_artifact_sha256", "direct_source_paper_ids", "referenced_manifest_ids",
}
CLAIM_SUPPORT_MATRIX = {
    "primary_technical_support": "paper_technical",
    "project_derivation": "project_mathematical_derivation",
    "implementation_evidence": "implementation_behavior",
}
CLAIM_NONSUPPORT_MATRIX = {
    "survey_context_only": "survey_context",
    "source_gap_blocker": "source_gap",
    "quarantined": "quarantine_explanation",
}
CLAIM_REVIEW_STATUSES = {
    "human_reviewed_passed", "model_reviewed_advisory", "rejected_or_blocked",
}
CLAIM_DEPENDENCY_ROLES = {
    "primary_technical_support": "primary_technical_source",
    "project_derivation": "project_derivation_source",
    "implementation_evidence": "implementation_evidence_source",
}
CLAIM_EVIDENCE_KINDS = {
    "primary_technical_support": "primary_technical_support",
    "project_derivation": "project_derivation",
    "implementation_evidence": "implementation_evidence",
}
CLAIM_V3_SIDECAR_KEYS = {
    "schema_version", "mission_id", "mission_fingerprint", "mission_anchor_generation_id",
    "artifact_set_id", "queue_semantic_sha256", "review_queue_sha256", "decision_set_id",
    "decisions_path", "decisions_sha256", "decisions_size_bytes", "status",
    "required_item_ids", "supplied_item_ids", "decision_coverage_complete", "claims",
    "rejected_claims", "coverage_errors", "accepted_claim_count", "rejected_claim_count",
    "ready_for_reviewed_packet", "ready_for_prose", "created_at", "what_is_not_concluded",
}
CLAIM_DECISION_CONFIG = AuthorityConfig(
    family="claim_decision",
    id_prefix="cd",
    sets_dir_name="decision_sets",
    current_name="DECISION_CURRENT",
    set_id_field="decision_set_id",
    current_manifest_field="decision_set_manifest_sha256",
    semantic_field="decision_set_semantic_sha256",
    manifest_name="decision_set_manifest.json",
    manifest_schema=SURVEY_CLAIM_DECISION_MANIFEST_SCHEMA,
    identity_schema="ra-survey-claim-decision-set-identity-v1",
    current_schema=SURVEY_CLAIM_DECISION_CURRENT_SCHEMA,
    predecessor_id_field="predecessor_decision_set_id",
    predecessor_manifest_field="predecessor_decision_set_manifest_sha256",
    artifacts={
        "reviewed_claim_decisions.json": "complete_decision_envelope",
        "reviewed_claims.json": "normalized_reviewed_claims",
    },
    identity_fields=frozenset({
        "mission_id", "mission_fingerprint", "mission_anchor_generation_id",
        "artifact_set_id", "queue_semantic_sha256", "review_queue_sha256",
        "decisions_sha256", "decisions_size_bytes", "normalized_claims_sha256",
        "predecessor_decision_set_id", "predecessor_decision_set_manifest_sha256",
    }),
    root_allowed_names=frozenset({"decision_sets", "DECISION_CURRENT"}),
)


def import_reviewed_claims(
    *,
    review_queue_path: Path,
    decisions_path: Path,
    output_dir: Path,
    force: bool = False,
    now: Callable[[], str] = utc_now_iso,
    nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
    crash_hook: Callable[[str], None] | None = None,
    human_attestation_receipt_path: Path | None = None,
) -> dict[str, Any]:
    try:
        envelope, raw = read_json_object_strict(decisions_path, label="claim decisions")
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir.absolute(), [str(exc)])
    if envelope.get("schema_version") in {SURVEY_CLAIM_REVIEW_V3_SCHEMA, SURVEY_CLAIM_REVIEW_V4_SCHEMA}:
        return _import_v3_claims(
            review_queue_path=review_queue_path,
            decisions_path=decisions_path,
            envelope=envelope,
            decisions_raw=raw,
            output_dir=output_dir,
            force=force,
            now=now,
            nonce_factory=nonce_factory,
            crash_hook=crash_hook,
            human_attestation_receipt_path=human_attestation_receipt_path,
        )
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        if exc.code != "legacy_evidence_authority":
            return _blocked(exc.code, output_dir.absolute(), [str(exc)])
    else:
        return _blocked(
            "legacy_claim_review_cannot_authorize_v2",
            output_dir.absolute(),
            ["submit an exact ra-survey-claim-review-v3 envelope"],
        )
    return _import_legacy_claims(
        review_queue_path=review_queue_path,
        decisions_path=decisions_path,
        output_dir=output_dir,
        force=force,
    )


def _import_legacy_claims(
    *, review_queue_path: Path, decisions_path: Path, output_dir: Path, force: bool,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    output_path = output_dir / "reviewed_claims.json"
    if output_path.exists() and not force:
        return _blocked("output_exists", output_dir, ["rerun with --force or choose a new --out directory"])
    try:
        context, _, rows, decisions_raw = load_bound_decision_envelope(
            review_queue_path=review_queue_path,
            decisions_path=decisions_path,
            decision_type="claim_candidate",
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])

    result = validate_exact_decisions(context=context, rows=rows, validator=_validate_decision)
    result = _apply_claim_constraints(result)

    status = "reviewed_claims_complete" if result.complete else "blocked_invalid_claim_decisions"
    payload = {
        "schema_version": SURVEY_REVIEWED_CLAIMS_SCHEMA_VERSION,
        **common_sidecar_fields(
            context=context,
            decisions_path=decisions_path,
            decisions_raw=decisions_raw,
            result=result,
            created_at=utc_now_iso(),
        ),
        "claims": result.accepted,
        "rejected_claims": result.rejected,
        "coverage_errors": result.coverage_errors,
        **claim_sidecar_expected_fields(result),
    }
    atomic_write_json(output_path, payload)
    return {
        "schema_version": SURVEY_REVIEWED_CLAIMS_RESULT_SCHEMA_VERSION,
        "status": status,
        "output_dir": str(output_dir),
        "reviewed_claims_path": str(output_path),
        "accepted_claim_count": len(result.accepted),
        "rejected_claim_count": len(result.rejected),
        "decision_coverage_complete": result.complete,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_CLAIM_NONCLAIMS,
    }


def _import_v3_claims(
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
    human_attestation_receipt_path: Path | None,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    try:
        if decisions_raw != pretty_json_bytes(envelope):
            raise MissionStateError("noncanonical_claim_review", "V3 claim review must be canonical pretty JSON")
        human_mode = envelope.get("schema_version") == SURVEY_CLAIM_REVIEW_V4_SCHEMA
        if human_mode != (human_attestation_receipt_path is not None):
            raise MissionStateError(
                "missing_human_attestation_receipt" if human_mode else "receipt_not_allowed_for_fixture_authority",
                "V4 human claim review requires one receipt; V3 fixture review does not accept one",
            )
        context = load_v2_evidence_context(review_queue_path)
        require_exact_keys(envelope, CLAIM_V3_ENVELOPE_KEYS, "V3/V4 claim-review envelope")
        if envelope.get("decision_type") != "claim_candidate":
            raise MissionStateError("wrong_decision_type", "V3 claim review has the wrong decision type")
        _require_claim_binding(envelope, context)
        rows = _validate_v3_claim_rows(
            envelope.get("decisions"), context=context, human_attested=human_mode,
        )
        authority_envelope = envelope
        if human_mode:
            assert human_attestation_receipt_path is not None
            archive = export_human_receipt_archive(human_attestation_receipt_path)
            receipt = validate_human_receipt_archive(archive)
            validate_human_receipt_decision(
                receipt=receipt,
                decision_type="claim_candidate",
                decisions_raw=decisions_raw,
                expected_binding=context.binding,
            )
            authority_envelope = {
                "schema_version": SURVEY_CLAIM_AUTHORITY_V4_SCHEMA,
                "decision_type": "claim_candidate",
                **context.binding,
                "attested_decisions": envelope,
                "human_receipt_archive": archive,
            }
        authority_raw = pretty_json_bytes(authority_envelope)
        required_ids = sorted(
            item["item_id"]
            for item in context.review_queue.get("items") or []
            if item.get("queue_type") == "claim_candidate"
        )
        supplied_ids = sorted(row["queue_item_id"] for row in rows)
        semantic = _claim_semantic_payload(
            rows=rows,
            required_ids=required_ids,
            supplied_ids=supplied_ids,
        )
        normalized_hash = sha256_bytes(canonical_semantic_bytes(
            _claim_normalized_projection(context=context, semantic=semantic)
        ))
        manager = ImmutableAuthorityManager(
            root=output_dir,
            config=CLAIM_DECISION_CONFIG,
            nonce_factory=nonce_factory,
            crash_hook=crash_hook,
        )
        selected = manager.load_predecessor_for_update()
        exact_replay = selected is not None and all([
            selected.manifest.get("decisions_sha256") == sha256_bytes(authority_raw),
            selected.manifest.get("decisions_size_bytes") == len(authority_raw),
            selected.manifest.get("normalized_claims_sha256") == normalized_hash,
        ])
        predecessor_id = (
            selected.manifest["predecessor_decision_set_id"]
            if exact_replay
            else selected.set_id
            if selected is not None
            else None
        )
        predecessor_hash = (
            selected.manifest["predecessor_decision_set_manifest_sha256"]
            if exact_replay
            else sha256_file(selected.set_dir / CLAIM_DECISION_CONFIG.manifest_name)
            if selected is not None
            else None
        )
        identity = {
            **context.binding,
            "decisions_sha256": sha256_bytes(authority_raw),
            "decisions_size_bytes": len(authority_raw),
            "normalized_claims_sha256": normalized_hash,
            "predecessor_decision_set_id": predecessor_id,
            "predecessor_decision_set_manifest_sha256": predecessor_hash,
        }
        decision_set_id, _ = manager.preview(
            identity_fields=identity,
            artifacts={
                "reviewed_claim_decisions.json": authority_raw,
                "reviewed_claims.json": b"",
            },
        )
        sidecar_without_created_at = {
            "schema_version": (
                SURVEY_REVIEWED_CLAIMS_V4_SCHEMA if human_mode else SURVEY_REVIEWED_CLAIMS_V3_SCHEMA
            ),
            **context.binding,
            "decision_set_id": decision_set_id,
            "decisions_path": str(manager.sets_dir / decision_set_id / "reviewed_claim_decisions.json"),
            "decisions_sha256": sha256_bytes(authority_raw),
            "decisions_size_bytes": len(authority_raw),
            **semantic,
        }
        created_at = manager.preserve_staged_created_at(
            set_id=decision_set_id,
            artifact_name="reviewed_claims.json",
            expected_without_created_at=sidecar_without_created_at,
            fallback=now(),
        )
        sidecar = {**sidecar_without_created_at, "created_at": created_at}
        require_exact_keys(sidecar, CLAIM_V3_SIDECAR_KEYS, "V3 reviewed-claims sidecar")
        snapshot = manager.compose_and_select(
            identity_fields=identity,
            artifacts={
                "reviewed_claim_decisions.json": authority_raw,
                "reviewed_claims.json": pretty_json_bytes(sidecar),
            },
            force=force,
        )
        validated = _validate_v3_selected_claim_authority(context=context, snapshot=snapshot)
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    return {
        "schema_version": SURVEY_REVIEWED_CLAIMS_RESULT_SCHEMA_VERSION,
        "status": "reviewed_claims_complete",
        "output_dir": str(output_dir),
        "reviewed_claims_path": str(snapshot.artifact_paths["reviewed_claims.json"]),
        "decision_set_id": snapshot.set_id,
        "accepted_claim_count": len(validated["claims"]),
        "rejected_claim_count": 0,
        "decision_coverage_complete": True,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_CLAIM_NONCLAIMS,
    }


def resolve_current_reviewed_claims(
    *,
    review_queue_path: Path,
    reviewed_claims_root: Path,
    supplied_sidecar_path: Path | None = None,
) -> tuple[AuthoritySnapshot, dict[str, Any]]:
    context = load_v2_evidence_context(review_queue_path)
    manager = ImmutableAuthorityManager(root=reviewed_claims_root.absolute(), config=CLAIM_DECISION_CONFIG)
    snapshot = manager.load_current(required=True)
    assert snapshot is not None
    sidecar = _validate_v3_selected_claim_authority(context=context, snapshot=snapshot)
    selected_path = snapshot.artifact_paths["reviewed_claims.json"]
    if supplied_sidecar_path is not None:
        supplied = supplied_sidecar_path.absolute()
        if (
            supplied.is_symlink()
            or supplied != selected_path.absolute()
            or supplied.resolve() != selected_path.resolve()
        ):
            raise MissionStateError(
                "stale_claim_decision_selector",
                "supplied reviewed-claims sidecar is not selected by DECISION_CURRENT",
            )
    return snapshot, sidecar


def resolve_current_reviewed_claims_sidecar_path(
    *, review_queue_path: Path, sidecar_path: Path,
) -> Path:
    supplied = sidecar_path.absolute()
    root = supplied.parent.parent.parent if supplied.parent.parent.name == "decision_sets" else supplied.parent
    snapshot, _ = resolve_current_reviewed_claims(
        review_queue_path=review_queue_path,
        reviewed_claims_root=root,
        supplied_sidecar_path=supplied,
    )
    return snapshot.artifact_paths["reviewed_claims.json"]


def selected_claim_human_receipt_archive(snapshot: AuthoritySnapshot) -> dict[str, Any] | None:
    envelope, _ = read_json_object_strict(
        snapshot.artifact_paths["reviewed_claim_decisions.json"],
        label="selected claim review envelope",
    )
    if envelope.get("schema_version") == SURVEY_CLAIM_AUTHORITY_V4_SCHEMA:
        archive = envelope.get("human_receipt_archive")
        validate_human_receipt_archive(archive)
        return archive
    return None


def _require_claim_binding(value: dict[str, Any], context: EvidenceContext) -> None:
    for field, expected in context.binding.items():
        if value.get(field) != expected:
            code = "foreign_lineage" if field in {"mission_id", "mission_fingerprint"} else "stale_lineage"
            raise MissionStateError(code, f"V3 claim review {field} differs from selected authority")


def _validate_v3_claim_rows(
    value: Any, *, context: EvidenceContext, human_attested: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_claim_decisions", "claim decisions must be a list")
    queue_items = {
        item["item_id"]: item
        for item in context.review_queue.get("items") or []
        if item.get("queue_type") == "claim_candidate"
    }
    normalized = [
        _validate_v3_claim_row(
            row,
            queue_item=queue_items.get(row.get("queue_item_id")) if isinstance(row, dict) else None,
            context=context,
            index=index,
            human_attested=human_attested,
        )
        for index, row in enumerate(value, start=1)
    ]
    normalized.sort(key=lambda row: row["queue_item_id"])
    required = sorted(queue_items)
    supplied = [row["queue_item_id"] for row in normalized]
    claim_ids = [row["claim_id"] for row in normalized]
    if supplied != required or len(supplied) != len(set(supplied)) or len(value) != len(required):
        raise MissionStateError("incomplete_claim_decisions", "claim decisions do not exactly cover claim-candidate queue items")
    if len(claim_ids) != len(set(claim_ids)):
        raise MissionStateError("duplicate_claim_id", "claim decision IDs must be unique")
    return normalized


def _validate_v3_claim_row(
    value: Any,
    *,
    queue_item: dict[str, Any] | None,
    context: EvidenceContext,
    index: int,
    human_attested: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MissionStateError("invalid_claim_decision", f"claim decision row {index} is not an object")
    support_class = normalize_required_text(value.get("support_class"), field="support_class")
    supporting = support_class in CLAIM_SUPPORT_MATRIX
    expected_keys = set(CLAIM_V3_COMMON_KEYS)
    if supporting:
        expected_keys |= CLAIM_V3_SUPPORT_KEYS
        if support_class == "primary_technical_support":
            expected_keys |= {"paper_ids", "anchor_ids"}
        elif support_class == "project_derivation":
            expected_keys.add("derivation_id")
    elif support_class in CLAIM_NONSUPPORT_MATRIX:
        expected_keys |= {"reason", "next_action"}
    require_exact_keys(value, expected_keys, f"V3 claim decision row {index}")
    item_id = normalize_required_text(value.get("queue_item_id"), field="queue_item_id")
    if queue_item is None:
        raise MissionStateError("foreign_claim_decision", "claim decision names a foreign queue item")
    claim_type = normalize_required_text(value.get("claim_type"), field="claim_type")
    expected_type = (CLAIM_SUPPORT_MATRIX if supporting else CLAIM_NONSUPPORT_MATRIX).get(support_class)
    if claim_type != expected_type:
        raise MissionStateError("invalid_claim_support_matrix", "claim type and support class are incompatible")
    review_status = normalize_required_text(value.get("review_status"), field="review_status")
    if review_status not in CLAIM_REVIEW_STATUSES:
        raise MissionStateError("invalid_claim_reviewer_authority", "claim review status is not closed")
    if value.get("fixture_only") is not (not human_attested):
        raise MissionStateError(
            "invalid_claim_decision",
            "V3 decisions require fixture_only=true and receipt-bound V4 decisions require fixture_only=false",
        )
    base: dict[str, Any] = {
        "queue_item_id": item_id,
        "claim_id": normalize_required_text(value.get("claim_id"), field="claim_id"),
        "claim_text": normalize_required_text(value.get("claim_text"), field="claim_text"),
        "claim_type": claim_type,
        "support_class": support_class,
        "review_status": review_status,
        "reviewer": normalize_required_text(value.get("reviewer"), field="reviewer"),
        "reviewed_at": normalize_reviewed_at(value.get("reviewed_at")),
        "evidence_note": normalize_required_text(value.get("evidence_note"), field="evidence_note"),
        "fixture_only": not human_attested,
    }
    if supporting:
        graph = _validate_dependency_graph(value, support_class=support_class, context=context)
        graph_source_paper_ids = graph.pop("graph_source_paper_ids")
        base.update(graph)
        if support_class == "primary_technical_support":
            paper_ids = strict_string_list(value.get("paper_ids"), field="paper_ids")
            anchor_ids = strict_string_list(value.get("anchor_ids"), field="anchor_ids")
            queue_papers = set(queue_item.get("paper_ids") or [])
            queue_anchors = set(queue_item.get("anchor_ids") or [])
            if not set(paper_ids).issubset(queue_papers) or not set(anchor_ids).issubset(queue_anchors):
                raise MissionStateError("foreign_claim_anchor", "claim papers or anchors exceed the queue item")
            _validate_current_anchors(
                context=context,
                paper_ids=paper_ids,
                anchor_ids=anchor_ids,
            )
            if sorted(graph_source_paper_ids) != paper_ids:
                raise MissionStateError("claim_dependency_closure_mismatch", "primary paper IDs differ from dependency closure")
            base.update({"paper_ids": paper_ids, "anchor_ids": anchor_ids})
        elif support_class == "project_derivation":
            base["derivation_id"] = normalize_required_text(value.get("derivation_id"), field="derivation_id")
    else:
        base.update({
            "reason": normalize_required_text(value.get("reason"), field="reason"),
            "next_action": normalize_required_text(value.get("next_action"), field="next_action"),
        })
    base.update({
        "claim_support_allowed": supporting and review_status == "human_reviewed_passed",
        "source_safety_required": supporting,
        "omission_review_required": supporting,
        "ready_for_prose": False,
    })
    digest = sha256_bytes(canonical_json_bytes({
        "schema_version": "ra-survey-normalized-claim-decision-identity-v1",
        "decision": base,
    }))
    return {**base, "decision_sha256": digest}


def _validate_dependency_graph(
    value: dict[str, Any],
    *,
    support_class: str,
    context: EvidenceContext,
) -> dict[str, Any]:
    dependencies_raw = value.get("source_dependencies")
    manifests_raw = value.get("dependency_manifests")
    if not isinstance(dependencies_raw, list) or not isinstance(manifests_raw, list):
        raise MissionStateError("invalid_claim_dependency_graph", "dependency declarations must be lists")
    dependencies = [
        _validate_source_dependency(row, support_class=support_class, context=context)
        for row in dependencies_raw
    ]
    if dependencies != sorted(dependencies, key=lambda row: row["source_paper_id"]):
        raise MissionStateError("unsorted_claim_dependencies", "source dependencies must be source-paper sorted")
    paper_ids = [row["source_paper_id"] for row in dependencies]
    if len(paper_ids) != len(set(paper_ids)):
        raise MissionStateError("duplicate_claim_dependency", "source dependencies must be unique")

    manifests = [
        _validate_dependency_manifest(row, support_class=support_class, context=context)
        for row in manifests_raw
    ]
    if manifests != sorted(manifests, key=lambda row: row["manifest_id"]):
        raise MissionStateError("unsorted_dependency_manifests", "dependency manifests must be ID sorted")
    by_id = {row["manifest_id"]: row for row in manifests}
    if len(by_id) != len(manifests):
        raise MissionStateError("duplicate_dependency_manifest", "dependency manifest IDs must be unique")
    root_id = normalize_required_text(value.get("root_dependency_manifest_id"), field="root_dependency_manifest_id")
    if root_id not in by_id:
        raise MissionStateError("missing_dependency_root", "dependency root manifest is absent")
    nullable_manifest_ids = {
        row["manifest_id"]
        for row in manifests
        if row["local_artifact"] is None
    }
    if nullable_manifest_ids - {root_id}:
        raise MissionStateError(
            "missing_dependency_local_artifact",
            "only the primary technical root manifest may omit local artifact bytes",
        )
    referenced = [target for row in manifests for target in row["referenced_manifest_ids"]]
    if any(target not in by_id for target in referenced):
        raise MissionStateError("missing_dependency_manifest", "dependency graph names a missing manifest")
    if len(referenced) != len(set(referenced)):
        raise MissionStateError("duplicate_dependency_edge", "dependency manifests must be referenced exactly once")
    unreachable = set(by_id) - _reachable_manifest_ids(root_id, by_id)
    if unreachable:
        raise MissionStateError("foreign_dependency_manifest", "dependency graph contains unreachable manifests")
    graph_sources = sorted({
        paper_id
        for manifest_id in _reachable_manifest_ids(root_id, by_id)
        for paper_id in by_id[manifest_id]["direct_source_paper_ids"]
    })
    if graph_sources != paper_ids:
        raise MissionStateError("claim_dependency_closure_mismatch", "graph-derived source closure differs from declarations")
    graph_projection = {
        "schema_version": "ra-survey-claim-dependency-graph-v1",
        "root_dependency_manifest_id": root_id,
        "dependency_manifests": manifests,
        "source_dependencies": dependencies,
    }
    graph_sha = sha256_bytes(canonical_json_bytes(graph_projection))
    if value.get("dependency_graph_sha256") != graph_sha:
        raise MissionStateError("claim_dependency_graph_digest_mismatch", "dependency graph digest differs")
    return {
        "source_dependencies": dependencies,
        "dependency_manifests": manifests,
        "root_dependency_manifest_id": root_id,
        "dependency_graph_sha256": graph_sha,
        "graph_source_paper_ids": graph_sources,
    }


def _validate_source_dependency(
    value: Any,
    *,
    support_class: str,
    context: EvidenceContext,
) -> dict[str, Any]:
    require_exact_keys(value, CLAIM_DEPENDENCY_KEYS, "claim source dependency")
    source_paper_id = normalize_required_text(value.get("source_paper_id"), field="source_paper_id")
    matching = [identity for identity in context.source_identities.values() if identity.source_paper_id == source_paper_id]
    if len(matching) != 1:
        raise MissionStateError("foreign_claim_dependency", "claim dependency lacks one current source identity")
    identity = matching[0]
    expected = {
        "stable_metadata_paper_id": identity.stable_metadata_paper_id,
        "source_paper_id": identity.source_paper_id,
        "canonical_identifier": identity.canonical_identifier,
        "source_version": identity.source_version,
        "source_record_sha256": identity.source_record_sha256,
        "dependency_role": CLAIM_DEPENDENCY_ROLES[support_class],
    }
    if value != expected:
        raise MissionStateError("stale_claim_dependency", "claim dependency differs from current source identity")
    return expected


def _validate_dependency_manifest(
    value: Any,
    *,
    support_class: str,
    context: EvidenceContext,
) -> dict[str, Any]:
    require_exact_keys(value, CLAIM_DEPENDENCY_MANIFEST_KEYS, "claim dependency manifest")
    row = dict(value)
    if row.get("schema_version") != SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA:
        raise MissionStateError("invalid_dependency_manifest_schema", "claim dependency manifest schema is unsupported")
    evidence_kind = normalize_required_text(row.get("evidence_kind"), field="evidence_kind")
    if evidence_kind != CLAIM_EVIDENCE_KINDS[support_class]:
        raise MissionStateError("invalid_dependency_evidence_kind", "dependency evidence kind differs from support class")
    direct = strict_string_list(
        row.get("direct_source_paper_ids"),
        field="direct_source_paper_ids",
        allow_empty=True,
    )
    refs = strict_string_list(
        row.get("referenced_manifest_ids"),
        field="referenced_manifest_ids",
        allow_empty=True,
    )
    local_value = row.get("local_artifact")
    local_hash = row.get("local_artifact_sha256")
    if local_value is None:
        if support_class != "primary_technical_support" or local_hash is not None:
            raise MissionStateError("missing_dependency_local_artifact", "only a primary-paper root may omit local artifact bytes")
        local_path = None
        normalized_hash = None
    else:
        local_relative = _normalized_mission_relative_path(local_value)
        local_path = _regular_mission_file(context.mission_root, local_relative)
        normalized_hash = require_sha256(local_hash, field="local_artifact_sha256")
        if sha256_file(local_path) != normalized_hash:
            raise MissionStateError("dependency_local_artifact_digest_mismatch", "dependency local artifact bytes changed")
    projection = {
        "schema_version": SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        "evidence_kind": evidence_kind,
        "local_artifact": None if local_path is None else str(local_path.relative_to(context.mission_root)),
        "local_artifact_sha256": normalized_hash,
        "direct_source_paper_ids": direct,
        "referenced_manifest_ids": refs,
    }
    manifest_id = f"dm-{sha256_bytes(canonical_json_bytes(projection))}"
    if row.get("manifest_id") != manifest_id:
        raise MissionStateError("invalid_dependency_manifest_id", "dependency manifest ID differs from content")
    return {"manifest_id": manifest_id, **projection}


def _reachable_manifest_ids(
    root_id: str,
    by_id: dict[str, dict[str, Any]],
) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(manifest_id: str) -> None:
        if manifest_id in visiting:
            raise MissionStateError("cyclic_dependency_graph", "dependency graph contains a cycle")
        if manifest_id in visited:
            return
        visiting.add(manifest_id)
        for target in by_id[manifest_id]["referenced_manifest_ids"]:
            visit(target)
        visiting.remove(manifest_id)
        visited.add(manifest_id)

    visit(root_id)
    return visited


def _normalized_mission_relative_path(value: Any) -> PurePosixPath:
    text = normalize_required_text(value, field="local_artifact")
    path = PurePosixPath(text)
    if path.is_absolute() or text != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise MissionStateError("invalid_dependency_local_artifact", "local artifact must be normalized mission-relative path")
    return path


def _regular_mission_file(root: Path, relative: PurePosixPath) -> Path:
    path = root
    for index, part in enumerate(relative.parts):
        path = path / part
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise MissionStateError(
                "missing_dependency_local_artifact",
                f"local dependency artifact is missing: {relative}",
            ) from exc
        if stat.S_ISLNK(mode):
            raise MissionStateError(
                "unsafe_dependency_local_artifact",
                "local dependency artifact path contains a symlink",
            )
        leaf = index == len(relative.parts) - 1
        if (leaf and not stat.S_ISREG(mode)) or (not leaf and not stat.S_ISDIR(mode)):
            raise MissionStateError(
                "unsafe_dependency_local_artifact",
                "local dependency artifact path has an invalid component",
            )
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise MissionStateError("escaped_dependency_local_artifact", "local dependency artifact escapes mission root") from exc
    return resolved


def _validate_current_anchors(
    *,
    context: EvidenceContext,
    paper_ids: list[str],
    anchor_ids: list[str],
) -> None:
    retained_status_path = context.mission_root / "source_intake" / "phase4_source_intake_status.json"
    try:
        retained_status, _ = read_json_object_strict(
            retained_status_path,
            label="mission source-intake status",
        )
    except MissionStateError:
        retained_status = {}
    if retained_status.get("schema_version") == "ra-survey-retained-source-intake-v1":
        from research_assistant.survey.m22_retained_reconciliation import (
            validate_retained_claim_anchors,
        )

        validate_retained_claim_anchors(
            context=context,
            paper_ids=paper_ids,
            anchor_ids=anchor_ids,
        )
        return
    anchor_dir = context.mission_root / "source_anchors"
    validate_anchor_packet(
        anchor_dir,
        source_status_path=context.mission_root / "source_intake" / "phase4_source_intake_status.json",
        expected_topic=context.mission_snapshot.contract["normalized_topic"]["display"],
        mission_root=context.mission_root,
        mission_snapshot=context.mission_snapshot,
    )
    inventory, raw = read_json_object_strict(anchor_dir / "source_anchor_inventory.json", label="source anchor inventory")
    if raw != json_pretty_bytes_without_required_newline(inventory):
        raise MissionStateError("noncanonical_anchor_inventory", "source anchor inventory bytes are noncanonical")
    rows = inventory.get("anchors")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise MissionStateError("invalid_anchor_inventory", "source anchor inventory rows are invalid")
    by_pair = {(row.get("paper_id"), row.get("anchor_id")): row for row in rows}
    for paper_id in paper_ids:
        if not any((paper_id, anchor_id) in by_pair for anchor_id in anchor_ids):
            raise MissionStateError("missing_current_claim_anchor", "each primary paper must own a current reviewed anchor")
    if any(not any((paper_id, anchor_id) in by_pair for paper_id in paper_ids) for anchor_id in anchor_ids):
        raise MissionStateError("foreign_claim_anchor", "claim anchor does not belong to a declared paper")


def json_pretty_bytes_without_required_newline(value: Any) -> bytes:
    # Legacy anchor writers omit the trailing newline; supervisor replay validates the same bytes.
    import json

    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8")


def _claim_semantic_payload(
    *,
    rows: list[dict[str, Any]],
    required_ids: list[str],
    supplied_ids: list[str],
) -> dict[str, Any]:
    return {
        "status": "reviewed_claims_complete",
        "required_item_ids": required_ids,
        "supplied_item_ids": supplied_ids,
        "decision_coverage_complete": required_ids == supplied_ids,
        "claims": rows,
        "rejected_claims": [],
        "coverage_errors": [],
        "accepted_claim_count": len(rows),
        "rejected_claim_count": 0,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_CLAIM_NONCLAIMS,
    }


def _claim_normalized_projection(
    *, context: EvidenceContext, semantic: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": (
            SURVEY_REVIEWED_CLAIMS_V4_SCHEMA
            if any(row.get("fixture_only") is False for row in semantic.get("claims", []))
            else SURVEY_REVIEWED_CLAIMS_V3_SCHEMA
        ),
        **context.binding,
        **semantic,
    }


def _validate_v3_selected_claim_authority(
    *, context: EvidenceContext, snapshot: AuthoritySnapshot,
) -> dict[str, Any]:
    envelope, envelope_raw = read_json_object_strict(
        snapshot.artifact_paths["reviewed_claim_decisions.json"],
        label="selected claim review envelope",
    )
    if envelope_raw != pretty_json_bytes(envelope):
        raise MissionStateError("noncanonical_claim_review", "selected claim review envelope is noncanonical")
    human_mode = envelope.get("schema_version") == SURVEY_CLAIM_AUTHORITY_V4_SCHEMA
    if human_mode:
        require_exact_keys(envelope, CLAIM_V4_AUTHORITY_ENVELOPE_KEYS, "selected human claim authority")
        _require_claim_binding(envelope, context)
        attested = envelope.get("attested_decisions")
        if not isinstance(attested, dict):
            raise MissionStateError("invalid_human_claim_authority", "attested claim decisions are missing")
        attested_raw = pretty_json_bytes(attested)
        require_exact_keys(attested, CLAIM_V3_ENVELOPE_KEYS, "attested V4 claim-review envelope")
        if attested.get("schema_version") != SURVEY_CLAIM_REVIEW_V4_SCHEMA:
            raise MissionStateError("invalid_claim_review_schema", "attested claim review schema is unsupported")
        _require_claim_binding(attested, context)
        receipt = validate_human_receipt_archive(envelope.get("human_receipt_archive"))
        validate_human_receipt_decision(
            receipt=receipt,
            decision_type="claim_candidate",
            decisions_raw=attested_raw,
            expected_binding=context.binding,
        )
        review_envelope = attested
    else:
        require_exact_keys(envelope, CLAIM_V3_ENVELOPE_KEYS, "selected claim-review envelope")
        if envelope.get("schema_version") != SURVEY_CLAIM_REVIEW_V3_SCHEMA:
            raise MissionStateError("invalid_claim_review_schema", "selected claim review envelope is unsupported")
        _require_claim_binding(envelope, context)
        review_envelope = envelope
    if envelope.get("decision_type") != "claim_candidate":
        raise MissionStateError("invalid_claim_review_schema", "selected claim review envelope has the wrong type")
    rows = _validate_v3_claim_rows(
        review_envelope.get("decisions"), context=context, human_attested=human_mode,
    )
    required_ids = sorted(
        item["item_id"]
        for item in context.review_queue.get("items") or []
        if item.get("queue_type") == "claim_candidate"
    )
    supplied_ids = sorted(row["queue_item_id"] for row in rows)
    semantic = _claim_semantic_payload(
        rows=rows,
        required_ids=required_ids,
        supplied_ids=supplied_ids,
    )
    sidecar, sidecar_raw = read_json_object_strict(
        snapshot.artifact_paths["reviewed_claims.json"],
        label="selected reviewed claims",
    )
    if sidecar_raw != pretty_json_bytes(sidecar):
        raise MissionStateError("noncanonical_claim_sidecar", "selected claim sidecar is noncanonical")
    require_exact_keys(sidecar, CLAIM_V3_SIDECAR_KEYS, "selected reviewed claims")
    expected_sidecar = {
        "schema_version": (
            SURVEY_REVIEWED_CLAIMS_V4_SCHEMA if human_mode else SURVEY_REVIEWED_CLAIMS_V3_SCHEMA
        ),
        **context.binding,
        "decision_set_id": snapshot.set_id,
        "decisions_path": str(snapshot.artifact_paths["reviewed_claim_decisions.json"]),
        "decisions_sha256": sha256_bytes(envelope_raw),
        "decisions_size_bytes": len(envelope_raw),
        **semantic,
        "created_at": normalize_reviewed_at(sidecar.get("created_at")),
    }
    if sidecar != expected_sidecar:
        raise MissionStateError("invalid_claim_sidecar_replay", "selected claim sidecar differs from envelope replay")
    normalized_hash = sha256_bytes(canonical_semantic_bytes(
        _claim_normalized_projection(context=context, semantic=semantic)
    ))
    identity = {
        **context.binding,
        "decisions_sha256": sha256_bytes(envelope_raw),
        "decisions_size_bytes": len(envelope_raw),
        "normalized_claims_sha256": normalized_hash,
        "predecessor_decision_set_id": snapshot.manifest["predecessor_decision_set_id"],
        "predecessor_decision_set_manifest_sha256": snapshot.manifest["predecessor_decision_set_manifest_sha256"],
    }
    manager = ImmutableAuthorityManager(root=snapshot.set_dir.parent.parent, config=CLAIM_DECISION_CONFIG)
    expected_id, expected_manifest = manager.preview(
        identity_fields=identity,
        artifacts={
            "reviewed_claim_decisions.json": envelope_raw,
            "reviewed_claims.json": sidecar_raw,
        },
    )
    if expected_id != snapshot.set_id or expected_manifest != snapshot.manifest:
        raise MissionStateError("invalid_claim_decision_replay", "selected claim authority does not replay")
    return sidecar


def _validate_decision(
    row: Any,
    queue_item: dict[str, Any] | None,
    index: int,
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(row, dict):
        return {}, [f"row {index} is not an object"]
    reasons: list[str] = []
    support_class = _text(row.get("support_class"), "support_class", reasons)
    expected_keys = set(CLAIM_COMMON_INPUT_KEYS)
    if support_class == "primary_technical_support":
        expected_keys |= {"paper_ids", "anchor_ids"}
    elif support_class == "project_derivation":
        expected_keys |= {"derivation_id", "local_artifact", "local_artifact_sha256", "derivation_note"}
    elif support_class == "implementation_evidence":
        expected_keys |= {"local_artifact", "local_artifact_sha256"}
    try:
        require_exact_keys(row, expected_keys, f"claim decision row {index}")
    except MissionStateError as exc:
        reasons.append(str(exc))

    claim_id = _text(row.get("claim_id"), "claim_id", reasons)
    claim_text = _text(row.get("claim_text"), "claim_text", reasons)
    review_status = _text(row.get("review_status"), "review_status", reasons).lower()
    reviewer = _text(row.get("reviewer"), "reviewer", reasons)
    reviewed_at = _time(row.get("reviewed_at"), reasons)
    evidence_note = _text(row.get("evidence_note"), "evidence_note", reasons)
    if support_class not in SUPPORTED_CLAIM_CLASSES:
        reasons.append("support_class must be primary_technical_support, project_derivation, or implementation_evidence")
    if review_status not in SUPPORTED_REVIEW_STATUSES:
        reasons.append("review_status must be a reviewed-pass status")

    normalized: dict[str, Any] = {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "review_status": review_status,
        "support_class": support_class,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "evidence_note": evidence_note,
        "claim_support_allowed": True,
        "source_safety_required": True,
        "omission_review_required": True,
        "ready_for_prose": False,
    }
    if support_class == "primary_technical_support":
        paper_ids = _strings(row.get("paper_ids"), "paper_ids", reasons)
        anchor_ids = _strings(row.get("anchor_ids"), "anchor_ids", reasons)
        normalized.update({"paper_ids": paper_ids, "anchor_ids": anchor_ids})
        if queue_item is not None:
            if not set(paper_ids).issubset(set(queue_item.get("paper_ids") or [])):
                reasons.append("paper_ids must be drawn from the referenced queue item")
            if not set(anchor_ids).issubset(set(queue_item.get("anchor_ids") or [])):
                reasons.append("anchor_ids must be drawn from the referenced queue item")
    elif support_class == "project_derivation":
        normalized.update({
            "derivation_id": _text(row.get("derivation_id"), "derivation_id", reasons),
            "local_artifact": _text(row.get("local_artifact"), "local_artifact", reasons),
            "local_artifact_sha256": _hex(row.get("local_artifact_sha256"), "local_artifact_sha256", reasons),
            "derivation_note": _text(row.get("derivation_note"), "derivation_note", reasons),
        })
    elif support_class == "implementation_evidence":
        normalized.update({
            "local_artifact": _text(row.get("local_artifact"), "local_artifact", reasons),
            "local_artifact_sha256": _hex(row.get("local_artifact_sha256"), "local_artifact_sha256", reasons),
        })
    if queue_item is not None and queue_item.get("claim_support_allowed") is not False:
        reasons.append("referenced claim_candidate queue item must not already allow claim support")
    return normalized, reasons


def _text(value: Any, field: str, reasons: list[str]) -> str:
    try:
        return normalize_required_text(value, field=field)
    except MissionStateError as exc:
        reasons.append(str(exc))
        return ""


def _time(value: Any, reasons: list[str]) -> str:
    try:
        return normalize_reviewed_at(value)
    except MissionStateError as exc:
        reasons.append(str(exc))
        return ""


def _strings(value: Any, field: str, reasons: list[str]) -> list[str]:
    try:
        return normalize_string_list(value, field=field)
    except MissionStateError as exc:
        reasons.append(str(exc))
        return []


def _hex(value: Any, field: str, reasons: list[str]) -> str:
    try:
        return require_lower_hex(value, field=field)
    except MissionStateError as exc:
        reasons.append(str(exc))
        return ""


def _duplicates(values: list[str]) -> list[str]:
    counts = {value: values.count(value) for value in set(values) if value}
    return sorted(value for value, count in counts.items() if count > 1)


def _apply_claim_constraints(result: ExactDecisionResult) -> ExactDecisionResult:
    duplicate_claim_ids = _duplicates([str(row.get("claim_id") or "") for row in result.accepted])
    if not duplicate_claim_ids:
        return result
    return ExactDecisionResult(
        required_item_ids=result.required_item_ids,
        supplied_item_ids=result.supplied_item_ids,
        accepted=result.accepted,
        rejected=result.rejected,
        coverage_errors=[
            *result.coverage_errors,
            f"duplicate claim_ids: {', '.join(duplicate_claim_ids)}",
        ],
    )


def claim_sidecar_expected_fields(result: ExactDecisionResult) -> dict[str, Any]:
    return {
        "status": "reviewed_claims_complete" if result.complete else "blocked_invalid_claim_decisions",
        "accepted_claim_count": len(result.accepted),
        "rejected_claim_count": len(result.rejected),
        "what_is_not_concluded": REVIEWED_CLAIM_NONCLAIMS,
    }


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_CLAIMS_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": REVIEWED_CLAIM_NONCLAIMS,
    }


__all__ = [
    "CLAIM_DEPENDENCY_ROLES",
    "CLAIM_DECISION_CONFIG",
    "CLAIM_EVIDENCE_KINDS",
    "CLAIM_SIDECAR_KEYS",
    "REVIEWED_CLAIM_NONCLAIMS",
    "SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA",
    "SURVEY_CLAIM_REVIEW_V3_SCHEMA",
    "SURVEY_CLAIM_REVIEW_V4_SCHEMA",
    "SURVEY_REVIEWED_CLAIMS_V3_SCHEMA",
    "SURVEY_REVIEWED_CLAIMS_V4_SCHEMA",
    "SURVEY_REVIEWED_CLAIMS_SCHEMA_VERSION",
    "_apply_claim_constraints",
    "_validate_decision",
    "claim_sidecar_expected_fields",
    "import_reviewed_claims",
    "selected_claim_human_receipt_archive",
]
