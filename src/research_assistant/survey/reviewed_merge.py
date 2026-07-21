from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from research_assistant.survey.claim_review import (
    CLAIM_SIDECAR_KEYS,
    SURVEY_REVIEWED_CLAIMS_SCHEMA_VERSION,
    _apply_claim_constraints,
    _validate_decision as _validate_claim_decision,
    claim_sidecar_expected_fields,
    resolve_current_reviewed_claims,
    selected_claim_human_receipt_archive,
)
from research_assistant.survey.evidence_semantics import EvidenceContext, load_v2_evidence_context
from research_assistant.survey.mission_state import MissionStateError, sha256_file
from research_assistant.survey.human_attestation import human_receipt_archive_bound_input
from research_assistant.survey.omission_review import (
    OMISSION_SIDECAR_KEYS,
    OmissionDecisionSetSnapshot,
    SURVEY_REVIEWED_OMISSION_SCHEMA_VERSION,
    _validate_decision as _validate_omission_decision,
    omission_sidecar_expected_fields,
    resolve_current_omission_sidecar_path,
    resolve_current_reviewed_omissions,
)
from research_assistant.survey.review_decisions import (
    atomic_write_json,
    load_selected_decision_context,
    pretty_json_bytes,
    read_json_object_strict,
    utc_now_iso,
    validate_sidecar_binding,
)
from research_assistant.survey.source_safety_review import (
    SOURCE_SIDECAR_KEYS,
    SURVEY_REVIEWED_SOURCE_SAFETY_SCHEMA_VERSION,
    _validate_decision as _validate_source_decision,
    resolve_current_source_safety,
    selected_source_human_receipt_archive,
    source_sidecar_expected_fields,
)
from research_assistant.survey.workflow_blocker_review import (
    SURVEY_REVIEWED_WORKFLOW_BLOCKERS_SCHEMA_VERSION,
    WORKFLOW_SIDECAR_KEYS,
    _validate_decision as _validate_workflow_decision,
    workflow_sidecar_expected_fields,
)


SURVEY_REVIEWED_EVIDENCE_MERGE_RESULT_SCHEMA_VERSION = "ra-survey-reviewed-evidence-merge-result-v2"
SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION = "ra-survey-reviewed-evidence-status-v2"
SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION = "ra-survey-reviewed-evidence-status-v3"
SURVEY_REVIEWED_SOURCE_OUTCOME_BLOCKERS_SCHEMA_VERSION = "ra-survey-reviewed-source-outcome-blockers-v1"
SURVEY_REVIEWED_SOURCE_ACCOUNTING_SCHEMA_VERSION = "ra-survey-reviewed-source-accounting-v1"

REVIEWED_EVIDENCE_MERGE_NONCLAIMS = [
    "human or model review quality",
    "claim truth",
    "source safety in fact",
    "omission correctness",
    "literature completeness",
    "final prose readiness",
    "product readiness",
    "real-agent reliability",
    "scientific correctness",
]
REVIEWED_EVIDENCE_KEYS = {
    "schema_version",
    "status",
    "created_at",
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
    "queue_semantic_sha256",
    "review_queue_path",
    "review_queue_sha256",
    "reviewed_sidecars",
    "required_queue_item_ids",
    "accepted_queue_item_ids_by_type",
    "reviewed_decisions",
    "decision_coverage_complete",
    "ready_for_reviewed_packet",
    "ready_for_prose",
    "blockers",
    "counts",
    "next_required_actions",
    "what_is_not_concluded",
}
REVIEWED_EVIDENCE_V3_KEYS = REVIEWED_EVIDENCE_KEYS | {"merge_diagnostics"}
DECISION_TYPES = ["claim_candidate", "source_safety", "omission_risk", "workflow_blocker"]
SIDECAR_CONFIGS = {
    "claim_candidate": {
        "schema": SURVEY_REVIEWED_CLAIMS_SCHEMA_VERSION,
        "keys": CLAIM_SIDECAR_KEYS,
        "decisions_field": "claims",
        "rejected_field": "rejected_claims",
        "validator": _validate_claim_decision,
        "expected_fields": claim_sidecar_expected_fields,
        "result_transform": _apply_claim_constraints,
    },
    "source_safety": {
        "schema": SURVEY_REVIEWED_SOURCE_SAFETY_SCHEMA_VERSION,
        "keys": SOURCE_SIDECAR_KEYS,
        "decisions_field": "source_safety",
        "rejected_field": "rejected_source_safety",
        "validator": _validate_source_decision,
        "expected_fields": source_sidecar_expected_fields,
    },
    "omission_risk": {
        "schema": SURVEY_REVIEWED_OMISSION_SCHEMA_VERSION,
        "keys": OMISSION_SIDECAR_KEYS,
        "decisions_field": "omission_risks",
        "rejected_field": "rejected_omission_risks",
        "validator": _validate_omission_decision,
        "expected_fields": omission_sidecar_expected_fields,
    },
    "workflow_blocker": {
        "schema": SURVEY_REVIEWED_WORKFLOW_BLOCKERS_SCHEMA_VERSION,
        "keys": WORKFLOW_SIDECAR_KEYS,
        "decisions_field": "workflow_blockers",
        "rejected_field": "rejected_workflow_blockers",
        "validator": _validate_workflow_decision,
        "expected_fields": workflow_sidecar_expected_fields,
    },
}


def merge_reviewed_evidence(
    *,
    review_queue_path: Path,
    reviewed_claims_path: Path,
    reviewed_source_safety_path: Path,
    reviewed_omissions_path: Path,
    reviewed_workflow_blockers_path: Path,
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        if exc.code == "legacy_evidence_authority":
            return _blocked_invalid(
                "legacy_evidence_authority",
                output_dir.absolute(),
                [
                    "migrate the selected coverage and claim/source review authority to the canonical V2/V3 path",
                    "legacy review artifacts remain parseable but cannot create a new clear merge",
                ],
            )
        return _blocked_invalid(exc.code, output_dir.absolute(), [str(exc)])
    else:
        return _merge_v3_reviewed_evidence(
            review_queue_path=review_queue_path,
            reviewed_claims_path=reviewed_claims_path,
            reviewed_source_safety_path=reviewed_source_safety_path,
            reviewed_omissions_path=reviewed_omissions_path,
            reviewed_workflow_blockers_path=reviewed_workflow_blockers_path,
            output_dir=output_dir,
            force=force,
        )


def validate_current_reviewed_sidecar(
    *,
    review_queue_path: Path,
    decision_type: str,
    sidecar_path: Path,
) -> dict[str, Any]:
    if decision_type not in SIDECAR_CONFIGS:
        raise MissionStateError("invalid_decision_type", f"unsupported reviewed sidecar type: {decision_type}")
    context = load_selected_decision_context(
        review_queue_path=review_queue_path,
        decision_type=decision_type,
    )
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        if exc.code != "legacy_evidence_authority":
            raise
    else:
        if decision_type == "claim_candidate":
            _, payload = resolve_current_reviewed_claims(
                review_queue_path=review_queue_path,
                reviewed_claims_root=_authority_root(sidecar_path, "decision_sets"),
                supplied_sidecar_path=sidecar_path,
            )
            return payload
        if decision_type == "source_safety":
            _, _, payload = resolve_current_source_safety(
                review_queue_path=review_queue_path,
                reviewed_source_safety_root=_authority_root(sidecar_path, "decision_sets"),
                supplied_sidecar_path=sidecar_path,
            )
            return payload
    if decision_type == "omission_risk":
        sidecar_path = resolve_current_omission_sidecar_path(
            review_queue_path=review_queue_path,
            sidecar_path=sidecar_path,
        )
    config = SIDECAR_CONFIGS[decision_type]
    payload, _ = validate_sidecar_binding(
        path=sidecar_path,
        context=context,
        expected_schema=config["schema"],
        expected_keys=config["keys"],
        decisions_field=config["decisions_field"],
        rejected_field=config["rejected_field"],
        validator=config["validator"],
        expected_fields=config["expected_fields"],
        result_transform=config.get("result_transform"),
    )
    return payload


def validate_reviewed_evidence_status(
    *,
    path: Path,
    review_queue_path: Path,
    sidecar_paths: dict[str, Path],
) -> dict[str, Any]:
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        if exc.code != "legacy_evidence_authority":
            raise
    else:
        return _validate_v3_reviewed_evidence_status(
            path=path,
            review_queue_path=review_queue_path,
            sidecar_paths=sidecar_paths,
        )
    if set(sidecar_paths) != set(DECISION_TYPES):
        raise MissionStateError(
            "invalid_reviewed_sidecar_set",
            "reviewed evidence validation requires exactly the four current sidecar paths",
        )
    payload, raw = read_json_object_strict(path, label="reviewed evidence status")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_reviewed_evidence", "reviewed evidence status is not canonical")
    if set(payload) != REVIEWED_EVIDENCE_KEYS:
        raise MissionStateError("invalid_reviewed_evidence_schema", "reviewed evidence status fields do not match exact schema")
    if payload.get("schema_version") != SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION:
        raise MissionStateError("invalid_reviewed_evidence_schema", "reviewed evidence status schema is unsupported")
    contexts = {
        decision_type: load_selected_decision_context(
            review_queue_path=review_queue_path,
            decision_type=decision_type,
        )
        for decision_type in DECISION_TYPES
    }
    absolute_paths = {
        decision_type: sidecar_paths[decision_type].absolute()
        for decision_type in DECISION_TYPES
    }
    absolute_paths["omission_risk"] = resolve_current_omission_sidecar_path(
        review_queue_path=review_queue_path,
        sidecar_path=absolute_paths["omission_risk"],
    )
    sidecars, sidecar_raw = _validate_sidecars(
        contexts=contexts,
        sidecar_paths=absolute_paths,
    )
    _require_complete_sidecars(sidecars)
    exact_union = _validate_exact_union(contexts, sidecars)
    claim_rows = sidecars["claim_candidate"]["claims"]
    safety_rows = sidecars["source_safety"]["source_safety"]
    omission_rows = sidecars["omission_risk"]["omission_risks"]
    workflow_rows = sidecars["workflow_blocker"]["workflow_blockers"]
    blockers = _outcome_blockers(
        contexts=contexts,
        claim_rows=claim_rows,
        safety_rows=safety_rows,
        omission_rows=omission_rows,
        workflow_rows=workflow_rows,
    )
    expected = _reviewed_evidence_payload(
        contexts=contexts,
        sidecar_paths=absolute_paths,
        sidecar_raw=sidecar_raw,
        exact_union=exact_union,
        claim_rows=claim_rows,
        safety_rows=safety_rows,
        omission_rows=omission_rows,
        workflow_rows=workflow_rows,
        blockers=blockers,
        created_at=payload.get("created_at"),
    )
    if payload != expected:
        raise MissionStateError(
            "invalid_reviewed_evidence_replay",
            "reviewed evidence status differs from current sidecar replay",
        )
    return payload


def _merge_v3_reviewed_evidence(
    *,
    review_queue_path: Path,
    reviewed_claims_path: Path,
    reviewed_source_safety_path: Path,
    reviewed_omissions_path: Path,
    reviewed_workflow_blockers_path: Path,
    output_dir: Path,
    force: bool,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    status_path = output_dir / "reviewed_evidence_status.json"
    source_blockers_path = output_dir / "reviewed_source_outcome_blockers.json"
    accounting_path = output_dir / "reviewed_source_accounting.json"
    if status_path.exists() and not force:
        return _blocked("output_exists", output_dir, ["rerun with --force after current authority changes"])
    try:
        state = _replay_v3_merge_inputs(
            review_queue_path=review_queue_path,
            sidecar_paths={
                "claim_candidate": reviewed_claims_path,
                "source_safety": reviewed_source_safety_path,
                "omission_risk": reviewed_omissions_path,
                "workflow_blocker": reviewed_workflow_blockers_path,
            },
        )
        source_diagnostic = _source_outcome_blocker_payload(state["evidence_context"])
        accounting_diagnostic = _source_accounting_payload(state)
        blockers = _v3_outcome_blockers(
            state=state,
            source_diagnostic=source_diagnostic,
            accounting_diagnostic=accounting_diagnostic,
        )
        atomic_write_json(source_blockers_path, source_diagnostic)
        atomic_write_json(accounting_path, accounting_diagnostic)
        diagnostic_raw = {
            "source_accounting": accounting_path.read_bytes(),
            "source_outcomes": source_blockers_path.read_bytes(),
        }
        payload = _v3_reviewed_evidence_payload(
            state=state,
            diagnostic_paths={
                "source_accounting": accounting_path,
                "source_outcomes": source_blockers_path,
            },
            diagnostic_raw=diagnostic_raw,
            blockers=blockers,
            created_at=utc_now_iso(),
        )
        atomic_write_json(status_path, payload)
    except MissionStateError as exc:
        return _blocked_invalid(exc.code, output_dir, [str(exc)])
    return {
        "schema_version": SURVEY_REVIEWED_EVIDENCE_MERGE_RESULT_SCHEMA_VERSION,
        "status": payload["status"],
        "output_dir": str(output_dir),
        "reviewed_evidence_status_path": str(status_path),
        "decision_coverage_complete": True,
        "ready_for_reviewed_packet": payload["ready_for_reviewed_packet"],
        "ready_for_prose": False,
        "blocker_count": len(blockers),
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


def _validate_v3_reviewed_evidence_status(
    *,
    path: Path,
    review_queue_path: Path,
    sidecar_paths: dict[str, Path],
) -> dict[str, Any]:
    if set(sidecar_paths) != set(DECISION_TYPES):
        raise MissionStateError(
            "invalid_reviewed_sidecar_set",
            "reviewed evidence validation requires exactly four current sidecars",
        )
    payload, raw = read_json_object_strict(path, label="V3 reviewed evidence status")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_reviewed_evidence", "V3 reviewed evidence is not canonical")
    if set(payload) != REVIEWED_EVIDENCE_V3_KEYS or payload.get("schema_version") != SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION:
        raise MissionStateError("invalid_reviewed_evidence_schema", "V3 reviewed evidence fields are not exact")
    state = _replay_v3_merge_inputs(
        review_queue_path=review_queue_path,
        sidecar_paths=sidecar_paths,
    )
    merge_root = path.absolute().parent
    source_path = merge_root / "reviewed_source_outcome_blockers.json"
    accounting_path = merge_root / "reviewed_source_accounting.json"
    source_payload, source_raw = read_json_object_strict(source_path, label="reviewed source outcome blockers")
    accounting_payload, accounting_raw = read_json_object_strict(accounting_path, label="reviewed source accounting")
    expected_source = _source_outcome_blocker_payload(state["evidence_context"])
    expected_accounting = _source_accounting_payload(state)
    if source_raw != pretty_json_bytes(source_payload) or source_payload != expected_source:
        raise MissionStateError("invalid_source_outcome_blocker_replay", "source-outcome diagnostic differs from current intake")
    if accounting_raw != pretty_json_bytes(accounting_payload) or accounting_payload != expected_accounting:
        raise MissionStateError("invalid_source_accounting_replay", "source accounting differs from current selectors")
    blockers = _v3_outcome_blockers(
        state=state,
        source_diagnostic=source_payload,
        accounting_diagnostic=accounting_payload,
    )
    expected = _v3_reviewed_evidence_payload(
        state=state,
        diagnostic_paths={"source_accounting": accounting_path, "source_outcomes": source_path},
        diagnostic_raw={"source_accounting": accounting_raw, "source_outcomes": source_raw},
        blockers=blockers,
        created_at=payload.get("created_at"),
    )
    if payload != expected:
        raise MissionStateError("invalid_reviewed_evidence_replay", "V3 merge differs from current authority replay")
    return payload


def _replay_v3_merge_inputs(
    *,
    review_queue_path: Path,
    sidecar_paths: dict[str, Path],
) -> dict[str, Any]:
    evidence_context = load_v2_evidence_context(review_queue_path)
    contexts = {
        decision_type: load_selected_decision_context(
            review_queue_path=review_queue_path,
            decision_type=decision_type,
        )
        for decision_type in DECISION_TYPES
    }
    claim_snapshot, claims = resolve_current_reviewed_claims(
        review_queue_path=review_queue_path,
        reviewed_claims_root=_authority_root(sidecar_paths["claim_candidate"], "decision_sets"),
        supplied_sidecar_path=sidecar_paths["claim_candidate"],
    )
    observation_snapshot, source_snapshot, source_safety = resolve_current_source_safety(
        review_queue_path=review_queue_path,
        reviewed_source_safety_root=_authority_root(sidecar_paths["source_safety"], "decision_sets"),
        supplied_sidecar_path=sidecar_paths["source_safety"],
    )
    omission_selected = resolve_current_reviewed_omissions(
        review_queue_path=review_queue_path,
        reviewed_omissions_root=_authority_root(sidecar_paths["omission_risk"], "decision_sets"),
        supplied_sidecar_path=sidecar_paths["omission_risk"],
    )
    if not isinstance(omission_selected, OmissionDecisionSetSnapshot):
        raise MissionStateError("legacy_omission_review_cannot_authorize_v2", "V2 merge requires a selected omission decision set")
    omission_config = SIDECAR_CONFIGS["omission_risk"]
    omissions, omission_raw = validate_sidecar_binding(
        path=omission_selected.sidecar_path,
        context=contexts["omission_risk"],
        expected_schema=omission_config["schema"],
        expected_keys=omission_config["keys"],
        decisions_field=omission_config["decisions_field"],
        rejected_field=omission_config["rejected_field"],
        validator=omission_config["validator"],
        expected_fields=omission_config["expected_fields"],
    )
    workflow_config = SIDECAR_CONFIGS["workflow_blocker"]
    workflow_path = sidecar_paths["workflow_blocker"].absolute()
    workflow, workflow_raw = validate_sidecar_binding(
        path=workflow_path,
        context=contexts["workflow_blocker"],
        expected_schema=workflow_config["schema"],
        expected_keys=workflow_config["keys"],
        decisions_field=workflow_config["decisions_field"],
        rejected_field=workflow_config["rejected_field"],
        validator=workflow_config["validator"],
        expected_fields=workflow_config["expected_fields"],
    )
    claim_receipt = selected_claim_human_receipt_archive(claim_snapshot)
    source_receipt = selected_source_human_receipt_archive(source_snapshot)
    if (claim_receipt is None) != (source_receipt is None):
        raise MissionStateError(
            "mixed_human_review_authority",
            "claim and source authority must use the same fixture or human-receipt mode",
        )
    if claim_receipt is not None:
        if claim_receipt != source_receipt:
            raise MissionStateError(
                "mixed_human_review_receipt",
                "claim and source authority embed different human receipts",
            )
        _, attested_omission_raw = human_receipt_archive_bound_input(
            claim_receipt,
            name="omission_risk_decisions.json",
        )
        _, attested_workflow_raw = human_receipt_archive_bound_input(
            claim_receipt,
            name="workflow_blocker_decisions.json",
        )
        if omission_selected.decisions_path.read_bytes() != attested_omission_raw:
            raise MissionStateError(
                "mixed_human_review_receipt",
                "selected omission decisions differ from the human receipt transaction",
            )
        workflow_decisions_path = Path(workflow["decisions_path"])
        if workflow_decisions_path.read_bytes() != attested_workflow_raw:
            raise MissionStateError(
                "mixed_human_review_receipt",
                "selected workflow decisions differ from the human receipt transaction",
            )
    sidecars = {
        "claim_candidate": claims,
        "source_safety": source_safety,
        "omission_risk": omissions,
        "workflow_blocker": workflow,
    }
    _require_complete_sidecars(sidecars)
    exact_union = _validate_v3_exact_union(contexts, sidecars)
    selected_paths = {
        "claim_candidate": claim_snapshot.artifact_paths["reviewed_claims.json"],
        "source_safety": source_snapshot.artifact_paths["reviewed_source_safety.json"],
        "omission_risk": omission_selected.sidecar_path,
        "workflow_blocker": workflow_path,
    }
    return {
        "evidence_context": evidence_context,
        "contexts": contexts,
        "sidecars": sidecars,
        "sidecar_paths": selected_paths,
        "sidecar_raw": {
            "claim_candidate": selected_paths["claim_candidate"].read_bytes(),
            "source_safety": selected_paths["source_safety"].read_bytes(),
            "omission_risk": omission_raw,
            "workflow_blocker": workflow_raw,
        },
        "claim_snapshot": claim_snapshot,
        "observation_snapshot": observation_snapshot,
        "source_snapshot": source_snapshot,
        "omission_snapshot": omission_selected,
        "exact_union": exact_union,
    }


def _validate_v3_exact_union(
    contexts: dict[str, Any],
    sidecars: dict[str, dict[str, Any]],
) -> list[str]:
    rows = {
        "claim_candidate": sidecars["claim_candidate"]["claims"],
        "source_safety": sidecars["source_safety"]["source_safety"],
        "omission_risk": sidecars["omission_risk"]["omission_risks"],
        "workflow_blocker": sidecars["workflow_blocker"]["workflow_blockers"],
    }
    required_all = sorted(str(item["item_id"]) for item in contexts["claim_candidate"].review_queue["items"])
    accepted_all = [row["queue_item_id"] for decision_type in DECISION_TYPES for row in rows[decision_type]]
    if sorted(accepted_all) != required_all or len(accepted_all) != len(set(accepted_all)):
        raise MissionStateError("invalid_review_coverage", "V3 reviewed decisions do not exactly partition the queue")
    hashes = [row["decision_sha256"] for decision_type in DECISION_TYPES for row in rows[decision_type]]
    if len(hashes) != len(set(hashes)):
        raise MissionStateError("duplicate_review_decision", "V3 normalized decision hashes are not unique")
    return required_all


def _source_outcome_blocker_payload(context: EvidenceContext) -> dict[str, Any]:
    status = context.validated_source_intake["status"]
    status_path = context.mission_root / "source_intake" / "phase4_source_intake_status.json"
    status_raw = status_path.read_bytes()
    ledger_path = Path(status["outcome_ledger_path"])
    ledger_raw = ledger_path.read_bytes()
    blockers = [
        {
            "blocker_code": "unavailable_source_outcome",
            "candidate_id": row["candidate_id"],
            "canonical_identifier": row["identifier"],
            "source_paper_id": row["paper_id"],
            "outcome_status": row["outcome_status"],
            "outcome_code": row["code"],
            "candidate_index": row["candidate_index"],
            "claim_support_allowed": False,
        }
        for row in context.unavailable_outcomes
    ]
    return {
        "schema_version": SURVEY_REVIEWED_SOURCE_OUTCOME_BLOCKERS_SCHEMA_VERSION,
        "mission_id": context.binding["mission_id"],
        "mission_fingerprint": context.binding["mission_fingerprint"],
        "mission_anchor_generation_id": context.binding["mission_anchor_generation_id"],
        "artifact_set_id": context.binding["artifact_set_id"],
        "source_intake_status_path": str(status_path),
        "source_intake_status_sha256": hashlib.sha256(status_raw).hexdigest(),
        "source_intake_status_size_bytes": len(status_raw),
        "source_outcome_ledger_path": str(ledger_path),
        "source_outcome_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
        "source_outcome_ledger_size_bytes": len(ledger_raw),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "status": "blocked_unavailable_source_outcome" if blockers else "clear_no_unavailable_source_outcomes",
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


def _source_tuple_from_identity(identity: Any) -> dict[str, Any]:
    return {
        "stable_metadata_paper_id": identity.stable_metadata_paper_id,
        "source_paper_id": identity.source_paper_id,
        "canonical_identifier": identity.canonical_identifier,
        "source_version": identity.source_version,
        "source_record_sha256": identity.source_record_sha256,
    }


def _source_tuple_from_dependency(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stable_metadata_paper_id": row["stable_metadata_paper_id"],
        "source_paper_id": row["source_paper_id"],
        "canonical_identifier": row["canonical_identifier"],
        "source_version": row["source_version"],
        "source_record_sha256": row["source_record_sha256"],
    }


def _source_tuple_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        row["stable_metadata_paper_id"],
        row["source_paper_id"],
        row["canonical_identifier"],
        row["source_version"],
        row["source_record_sha256"],
    )


def _frontier_observation_map(context: EvidenceContext) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    for name in ("backward_snowball.json", "forward_snowball.json"):
        payload, _ = read_json_object_strict(
            context.selected_artifact_set.coverage_dir / name,
            label=f"selected {name}",
        )
        for row in payload.get("observations") or []:
            if not isinstance(row, dict) or not isinstance(row.get("observation_id"), str):
                raise MissionStateError("invalid_source_accounting", "selected frontier observation is invalid")
            if row["observation_id"] in observations:
                raise MissionStateError("invalid_source_accounting", "selected frontier observation is duplicated")
            observations[row["observation_id"]] = row
    return observations


def _source_accounting_payload(state: dict[str, Any]) -> dict[str, Any]:
    context: EvidenceContext = state["evidence_context"]
    safety_rows = state["sidecars"]["source_safety"]["source_safety"]
    safety_by_item = {row["queue_item_id"]: row for row in safety_rows}
    if set(safety_by_item) != set(context.source_identities):
        raise MissionStateError("incomplete_source_decisions", "source accounting requires the complete observation/queue universe")
    selected_sources = []
    selected_by_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for item_id, identity in sorted(context.source_identities.items()):
        source = safety_by_item[item_id]
        source_tuple = _source_tuple_from_identity(identity)
        key = _source_tuple_key(source_tuple)
        if key in selected_by_key:
            raise MissionStateError("duplicate_selected_source", "selected source identities are not unique")
        row = {
            **source_tuple,
            "queue_item_id": item_id,
            "source_observation_id": source["observation_id"],
            "source_observation_sha256": source["observation_sha256"],
            "source_decision_sha256": source["decision_sha256"],
            "source_reviewer_authority": source["reviewer_authority"],
            "source_observation_outcome": source["observation_outcome"],
            "source_decision": source["decision"],
            "claim_support_allowed": source["claim_support_allowed"],
        }
        selected_by_key[key] = row
        selected_sources.append(row)

    dependencies_by_key: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for claim in state["sidecars"]["claim_candidate"]["claims"]:
        if claim.get("claim_support_allowed") is not True:
            continue
        for dependency in claim.get("source_dependencies") or []:
            source_tuple = _source_tuple_from_dependency(dependency)
            dependencies_by_key.setdefault(_source_tuple_key(source_tuple), []).append({
                **source_tuple,
                "claim_queue_item_id": claim["queue_item_id"],
                "claim_id": claim["claim_id"],
                "claim_decision_sha256": claim["decision_sha256"],
                "dependency_role": dependency["dependency_role"],
            })
    dependency_sources = [
        {**dict(zip(
            ("stable_metadata_paper_id", "source_paper_id", "canonical_identifier", "source_version", "source_record_sha256"),
            key,
        )), "claim_dependencies": sorted(rows, key=lambda row: (row["claim_queue_item_id"], row["claim_id"]))}
        for key, rows in sorted(dependencies_by_key.items())
    ]

    accounted_sources = []
    for key in sorted(set(selected_by_key) & set(dependencies_by_key)):
        source = selected_by_key[key]
        safe = (
            source["source_decision"] == "checked_clear"
            and source["source_reviewer_authority"] == "human_reviewed_status"
            and source["claim_support_allowed"] is True
        )
        accounted_sources.append({
            **source,
            "claim_dependencies": sorted(
                dependencies_by_key[key],
                key=lambda row: (row["claim_queue_item_id"], row["claim_id"]),
            ),
            "accounting_result": "accounted_checked_clear" if safe else "unsafe_claim_dependency",
        })
    missing_dependencies = [
        {
            "blocker_code": "missing_selected_source_dependency",
            **row,
            "claim_support_allowed": False,
        }
        for row in dependency_sources
        if _source_tuple_key(row) not in selected_by_key
    ]
    omission_rows = state["sidecars"]["omission_risk"]["omission_risks"]
    omission_by_item = {row["queue_item_id"]: row for row in omission_rows}
    unused_sources = []
    for key in sorted(set(selected_by_key) - set(dependencies_by_key)):
        source = selected_by_key[key]
        matching_omissions = sorted(
            row["queue_item_id"]
            for row in omission_rows
            if row.get("stable_metadata_paper_id") == source["stable_metadata_paper_id"]
            and row.get("source_paper_id") == source["source_paper_id"]
        )
        unused_sources.append({
            "blocker_code": "unused_included_source",
            **source,
            "matching_omission_queue_item_ids": matching_omissions,
            "claim_support_allowed": False,
        })

    observations = _frontier_observation_map(context)
    open_quarantine_risks = []
    for queue_item in sorted(
        (
            row for row in context.review_queue.get("items") or []
            if row.get("queue_type") == "omission_risk"
            and row.get("machine_disposition") == "quarantine"
        ),
        key=lambda row: row["item_id"],
    ):
        omission = omission_by_item.get(queue_item["item_id"])
        observation = observations.get(queue_item.get("risk_source_id"))
        if omission is None or observation is None:
            raise MissionStateError("invalid_source_accounting", "quarantine risk lacks exact current observation or decision")
        exact_matches = sorted(
            (
                _source_tuple_from_identity(identity)
                for identity in context.source_identities.values()
                if identity.stable_metadata_paper_id == observation.get("target_paper_id")
            ),
            key=_source_tuple_key,
        )
        open_quarantine_risks.append({
            "blocker_code": "open_quarantine_risk",
            "queue_item_id": queue_item["item_id"],
            "risk_id": queue_item["risk_id"],
            "risk_source_type": queue_item["risk_source_type"],
            "risk_source_id": queue_item["risk_source_id"],
            "source_artifact_sha256": queue_item["source_artifact_sha256"],
            "machine_disposition": "quarantine",
            "candidate_observation": observation,
            "omission_decision": omission["decision"],
            "omission_decision_sha256": omission["decision_sha256"],
            "omission_status": omission["status"],
            "source_identity_matches": exact_matches,
            "source_identity_match_count": len(exact_matches),
            "closure_authorized": False,
            "claim_support_allowed": False,
            "literature_completeness_allowed": False,
        })
    unsafe_count = sum(row["accounting_result"] != "accounted_checked_clear" for row in accounted_sources)
    clear = not missing_dependencies and not unused_sources and not open_quarantine_risks and unsafe_count == 0
    return {
        "schema_version": SURVEY_REVIEWED_SOURCE_ACCOUNTING_SCHEMA_VERSION,
        **context.binding,
        "claim_decision_set_id": state["claim_snapshot"].set_id,
        "claim_decision_set_manifest_sha256": sha256_file(state["claim_snapshot"].manifest_path),
        "source_observation_set_id": state["observation_snapshot"].set_id,
        "source_observation_set_manifest_sha256": sha256_file(state["observation_snapshot"].manifest_path),
        "source_decision_set_id": state["source_snapshot"].set_id,
        "source_decision_set_manifest_sha256": sha256_file(state["source_snapshot"].manifest_path),
        "omission_decision_set_id": state["omission_snapshot"].decision_set_id,
        "omission_decision_set_manifest_sha256": sha256_file(
            state["omission_snapshot"].set_dir / "decision_set_manifest.json"
        ),
        "selected_sources": selected_sources,
        "support_dependencies": dependency_sources,
        "accounted_sources": accounted_sources,
        "missing_dependencies": missing_dependencies,
        "unused_included_sources": unused_sources,
        "open_quarantine_risks": open_quarantine_risks,
        "selected_source_count": len(selected_sources),
        "support_dependency_count": len(dependency_sources),
        "accounted_source_count": len(accounted_sources),
        "unsafe_dependency_count": unsafe_count,
        "missing_dependency_count": len(missing_dependencies),
        "unused_included_source_count": len(unused_sources),
        "open_quarantine_risk_count": len(open_quarantine_risks),
        "status": "source_accounting_clear" if clear else "blocked_source_accounting",
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


def _v3_outcome_blockers(
    *,
    state: dict[str, Any],
    source_diagnostic: dict[str, Any],
    accounting_diagnostic: dict[str, Any],
) -> list[str]:
    claim_rows = state["sidecars"]["claim_candidate"]["claims"]
    safety_rows = state["sidecars"]["source_safety"]["source_safety"]
    omission_rows = state["sidecars"]["omission_risk"]["omission_risks"]
    workflow_rows = state["sidecars"]["workflow_blocker"]["workflow_blockers"]
    blockers = [
        f"unavailable_source_outcome: {row['candidate_id']}"
        for row in source_diagnostic["blockers"]
    ]
    for claim in claim_rows:
        if claim.get("claim_support_allowed") is not True:
            blockers.append(f"claim is not support-allowed: {claim['queue_item_id']}")
    for row in accounting_diagnostic["accounted_sources"]:
        if row["accounting_result"] != "accounted_checked_clear":
            blockers.append(f"unsafe_claim_dependency: {row['source_paper_id']}")
    for row in accounting_diagnostic["missing_dependencies"]:
        blockers.append(f"missing_selected_source_dependency: {row['source_paper_id']}")
    for row in accounting_diagnostic["unused_included_sources"]:
        blockers.append(f"unused_included_source: {row['source_paper_id']}")
        if (
            row["source_decision"] != "checked_clear"
            or row["source_reviewer_authority"] != "human_reviewed_status"
            or row["claim_support_allowed"] is not False
        ):
            blockers.append(f"source_authority_not_checked_clear: {row['queue_item_id']}")
    for row in accounting_diagnostic["open_quarantine_risks"]:
        blockers.append(f"open_quarantine_risk: {row['queue_item_id']}")
    for omission in omission_rows:
        if omission.get("status") != "reviewed_closed_for_current_scope":
            blockers.append(f"omission decision remains open: {omission['queue_item_id']}")
    decisions_by_type = {
        "claim_candidate": {row["queue_item_id"]: row for row in claim_rows},
        "source_safety": {row["queue_item_id"]: row for row in safety_rows},
        "omission_risk": {row["queue_item_id"]: row for row in omission_rows},
    }
    for workflow in workflow_rows:
        blocker = _v3_workflow_blocker(
            workflow,
            state["contexts"]["workflow_blocker"].required_items,
            decisions_by_type,
            set(),
        )
        if blocker:
            blockers.append(blocker)
    return sorted(set(blockers))


def _v3_workflow_blocker(
    row: dict[str, Any],
    queue_items: dict[str, dict[str, Any]],
    decisions_by_type: dict[str, dict[str, dict[str, Any]]],
    closed_omission_ids: set[str],
) -> str | None:
    item_id = row["queue_item_id"]
    item = queue_items[item_id]
    required_ids = sorted(item.get("required_evidence_queue_item_ids") or [])
    required_type = item.get("required_evidence_queue_type")
    if row.get("required_evidence_queue_item_ids") != required_ids or row.get("required_evidence_queue_type") != required_type:
        raise MissionStateError("invalid_workflow_resolution", f"workflow decision scope differs from queue item: {item_id}")
    if row.get("disposition") == "remains_open":
        return f"workflow blocker remains open: {item_id}"
    evidence_ids = sorted(row.get("evidence_queue_item_ids") or [])
    if evidence_ids != required_ids or not required_ids or required_type not in decisions_by_type:
        raise MissionStateError("invalid_workflow_resolution", f"workflow decision lacks exact current evidence: {item_id}")
    evidence = decisions_by_type[required_type]
    if any(evidence_id not in evidence for evidence_id in required_ids):
        raise MissionStateError("invalid_workflow_resolution", f"workflow evidence is missing: {item_id}")
    if required_type == "claim_candidate" and any(evidence[value].get("claim_support_allowed") is not True for value in required_ids):
        return f"workflow claim evidence is not support-allowed: {item_id}"
    if required_type == "source_safety" and any(evidence[value].get("decision") != "checked_clear" for value in required_ids):
        return f"workflow source evidence is not checked clear: {item_id}"
    if required_type == "omission_risk" and any(
        evidence[value].get("status") != "reviewed_closed_for_current_scope" and value not in closed_omission_ids
        for value in required_ids
    ):
        return f"workflow omission evidence is not closed: {item_id}"
    return None


def _v3_reviewed_evidence_payload(
    *,
    state: dict[str, Any],
    diagnostic_paths: dict[str, Path],
    diagnostic_raw: dict[str, bytes],
    blockers: list[str],
    created_at: Any,
) -> dict[str, Any]:
    from research_assistant.survey.review_decisions import normalize_reviewed_at

    created_at = normalize_reviewed_at(created_at)
    context: EvidenceContext = state["evidence_context"]
    sidecars = state["sidecars"]
    rows = {
        "claim_candidate": sidecars["claim_candidate"]["claims"],
        "source_safety": sidecars["source_safety"]["source_safety"],
        "omission_risk": sidecars["omission_risk"]["omission_risks"],
        "workflow_blocker": sidecars["workflow_blocker"]["workflow_blockers"],
    }
    unavailable = any(value.startswith("unavailable_source_outcome:") for value in blockers)
    ready = not blockers
    return {
        "schema_version": SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION,
        "status": (
            "reviewed_evidence_complete"
            if ready
            else "reviewed_evidence_blocked_unavailable_source_outcome"
            if unavailable
            else "reviewed_evidence_blocked"
        ),
        "created_at": created_at,
        **{key: context.binding[key] for key in (
            "mission_id", "mission_fingerprint", "mission_anchor_generation_id",
            "artifact_set_id", "queue_semantic_sha256",
        )},
        "review_queue_path": str(context.review_queue_path),
        "review_queue_sha256": context.review_queue_sha256,
        "reviewed_sidecars": {
            decision_type: {
                "path": str(state["sidecar_paths"][decision_type]),
                "sha256": hashlib.sha256(state["sidecar_raw"][decision_type]).hexdigest(),
            }
            for decision_type in DECISION_TYPES
        },
        "merge_diagnostics": {
            role: {
                "path": str(diagnostic_paths[role]),
                "sha256": hashlib.sha256(diagnostic_raw[role]).hexdigest(),
                "size_bytes": len(diagnostic_raw[role]),
            }
            for role in sorted(diagnostic_paths)
        },
        "required_queue_item_ids": state["exact_union"],
        "accepted_queue_item_ids_by_type": {
            decision_type: sorted(row["queue_item_id"] for row in rows[decision_type])
            for decision_type in DECISION_TYPES
        },
        "reviewed_decisions": rows,
        "decision_coverage_complete": True,
        "ready_for_reviewed_packet": ready,
        "ready_for_prose": False,
        "blockers": blockers,
        "counts": {
            "queue_total": len(state["exact_union"]),
            **{decision_type: len(rows[decision_type]) for decision_type in DECISION_TYPES},
        },
        "next_required_actions": (
            ["compose the coherent reviewed final packet before hostile review or prose readiness"]
            if ready
            else ["repair the exact current source, omission, dependency, or workflow blockers and remerge"]
        ),
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


def _authority_root(path: Path, sets_dir_name: str) -> Path:
    supplied = path.absolute()
    if supplied.parent.parent.name == sets_dir_name:
        return supplied.parent.parent.parent
    return supplied.parent


def _validate_sidecars(
    *,
    contexts: dict[str, Any],
    sidecar_paths: dict[str, Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    sidecars: dict[str, dict[str, Any]] = {}
    raw_by_type: dict[str, bytes] = {}
    for decision_type in DECISION_TYPES:
        if decision_type not in sidecar_paths:
            raise MissionStateError("missing_review_artifact", f"missing current {decision_type} reviewed sidecar path")
        config = SIDECAR_CONFIGS[decision_type]
        payload, raw = validate_sidecar_binding(
            path=sidecar_paths[decision_type],
            context=contexts[decision_type],
            expected_schema=config["schema"],
            expected_keys=config["keys"],
            decisions_field=config["decisions_field"],
            rejected_field=config["rejected_field"],
            validator=config["validator"],
            expected_fields=config["expected_fields"],
            result_transform=config.get("result_transform"),
        )
        sidecars[decision_type] = payload
        raw_by_type[decision_type] = raw
    return sidecars, raw_by_type


def _outcome_blockers(
    *,
    contexts: dict[str, Any],
    claim_rows: list[dict[str, Any]],
    safety_rows: list[dict[str, Any]],
    omission_rows: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
) -> list[str]:
    decisions_by_type = {
        "claim_candidate": {row["queue_item_id"]: row for row in claim_rows},
        "source_safety": {row["queue_item_id"]: row for row in safety_rows},
        "omission_risk": {row["queue_item_id"]: row for row in omission_rows},
    }
    blockers: list[str] = []
    for row in safety_rows:
        if row.get("checked_status") != "checked_clear":
            blockers.append(f"source-safety decision remains {row.get('checked_status')}: {row['queue_item_id']}")
    for row in omission_rows:
        if row.get("status") != "reviewed_closed_for_current_scope":
            blockers.append(f"omission decision remains open: {row['queue_item_id']}")
    for row in workflow_rows:
        blocker = _workflow_blocker(row, contexts["workflow_blocker"].required_items, decisions_by_type)
        if blocker:
            blockers.append(blocker)
    return sorted(set(blockers))


def _reviewed_evidence_payload(
    *,
    contexts: dict[str, Any],
    sidecar_paths: dict[str, Path],
    sidecar_raw: dict[str, bytes],
    exact_union: list[str],
    claim_rows: list[dict[str, Any]],
    safety_rows: list[dict[str, Any]],
    omission_rows: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
    blockers: list[str],
    created_at: Any,
) -> dict[str, Any]:
    from research_assistant.survey.review_decisions import normalize_reviewed_at

    normalized_created_at = normalize_reviewed_at(created_at)
    if created_at != normalized_created_at:
        raise MissionStateError("invalid_reviewed_evidence", "reviewed evidence created_at must be normalized UTC")
    queue_context = contexts["claim_candidate"]
    rows_by_type = {
        "claim_candidate": claim_rows,
        "source_safety": safety_rows,
        "omission_risk": omission_rows,
        "workflow_blocker": workflow_rows,
    }
    ready_for_reviewed_packet = not blockers
    return {
        "schema_version": SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
        "status": "reviewed_evidence_complete" if ready_for_reviewed_packet else "reviewed_evidence_blocked",
        "created_at": normalized_created_at,
        "mission_id": queue_context.review_queue["mission_id"],
        "mission_fingerprint": queue_context.review_queue["mission_fingerprint"],
        "mission_anchor_generation_id": queue_context.review_queue["mission_anchor_generation_id"],
        "artifact_set_id": queue_context.review_queue["artifact_set_id"],
        "queue_semantic_sha256": queue_context.review_queue["queue_semantic_sha256"],
        "review_queue_path": str(queue_context.review_queue_path),
        "review_queue_sha256": queue_context.review_queue_sha256,
        "reviewed_sidecars": {
            decision_type: {
                "path": str(sidecar_paths[decision_type]),
                "sha256": hashlib.sha256(sidecar_raw[decision_type]).hexdigest(),
            }
            for decision_type in DECISION_TYPES
        },
        "required_queue_item_ids": exact_union,
        "accepted_queue_item_ids_by_type": {
            decision_type: sorted(row["queue_item_id"] for row in rows_by_type[decision_type])
            for decision_type in DECISION_TYPES
        },
        "reviewed_decisions": rows_by_type,
        "decision_coverage_complete": True,
        "ready_for_reviewed_packet": ready_for_reviewed_packet,
        "ready_for_prose": False,
        "blockers": blockers,
        "counts": {
            "queue_total": len(exact_union),
            **{decision_type: len(rows_by_type[decision_type]) for decision_type in DECISION_TYPES},
        },
        "next_required_actions": (
            ["compose the coherent reviewed final packet before hostile review or prose readiness"]
            if ready_for_reviewed_packet
            else ["repair the listed open or blocked outcomes, rebuild changed upstream queue semantics when required, and re-review"]
        ),
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


def _require_complete_sidecars(sidecars: dict[str, dict[str, Any]]) -> None:
    for decision_type, payload in sidecars.items():
        if payload.get("decision_coverage_complete") is not True:
            raise MissionStateError("invalid_review_coverage", f"{decision_type} sidecar is not exactly complete")


def _validate_exact_union(
    contexts: dict[str, Any],
    sidecars: dict[str, dict[str, Any]],
) -> list[str]:
    queue_items = contexts["claim_candidate"].review_queue.get("items") or []
    required_all = sorted(str(item["item_id"]) for item in queue_items)
    if len(required_all) != len(set(required_all)):
        raise MissionStateError("invalid_queue_items", "selected review queue item IDs are not unique")
    accepted_lists = [payload["accepted_queue_item_ids"] for payload in sidecars.values()]
    accepted_all = [item_id for values in accepted_lists for item_id in values]
    if len(accepted_all) != len(set(accepted_all)):
        raise MissionStateError("duplicate_review_decision", "accepted sidecar item-ID sets overlap")
    if sorted(accepted_all) != required_all:
        raise MissionStateError("invalid_review_coverage", "four-way accepted decision union differs from selected queue")
    hashes = [
        row["decision_sha256"]
        for decision_type, payload in sidecars.items()
        for row in payload[_decision_field(decision_type)]
    ]
    if len(hashes) != len(set(hashes)):
        raise MissionStateError("duplicate_review_decision", "normalized decision hashes are not unique")
    return required_all


def _decision_field(decision_type: str) -> str:
    return {
        "claim_candidate": "claims",
        "source_safety": "source_safety",
        "omission_risk": "omission_risks",
        "workflow_blocker": "workflow_blockers",
    }[decision_type]


def _workflow_blocker(
    row: dict[str, Any],
    queue_items: dict[str, dict[str, Any]],
    decisions_by_type: dict[str, dict[str, dict[str, Any]]],
) -> str | None:
    item_id = row["queue_item_id"]
    item = queue_items[item_id]
    required_ids = sorted(item.get("required_evidence_queue_item_ids") or [])
    required_type = item.get("required_evidence_queue_type")
    if row.get("required_evidence_queue_item_ids") != required_ids or row.get("required_evidence_queue_type") != required_type:
        raise MissionStateError("invalid_workflow_resolution", f"workflow decision scope differs from queue item: {item_id}")
    if row.get("disposition") == "remains_open":
        return f"workflow blocker remains open: {item_id}"
    evidence_ids = sorted(row.get("evidence_queue_item_ids") or [])
    if evidence_ids != required_ids or not required_ids or required_type not in decisions_by_type:
        raise MissionStateError("invalid_workflow_resolution", f"workflow decision does not cite its exact resolvable evidence: {item_id}")
    evidence = decisions_by_type[required_type]
    if any(evidence_id not in evidence for evidence_id in required_ids):
        raise MissionStateError("invalid_workflow_resolution", f"workflow evidence is missing current decisions: {item_id}")
    if required_type == "claim_candidate" and any(evidence[evidence_id].get("claim_support_allowed") is not True for evidence_id in required_ids):
        return f"workflow claim evidence is not support-allowed: {item_id}"
    if required_type == "source_safety" and any(evidence[evidence_id].get("checked_status") != "checked_clear" for evidence_id in required_ids):
        return f"workflow source-safety evidence is not checked clear: {item_id}"
    if required_type == "omission_risk" and any(evidence[evidence_id].get("status") != "reviewed_closed_for_current_scope" for evidence_id in required_ids):
        return f"workflow omission evidence is not closed: {item_id}"
    return None


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_EVIDENCE_MERGE_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


def _blocked_invalid(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_EVIDENCE_MERGE_RESULT_SCHEMA_VERSION,
        "status": "blocked_invalid_review_artifacts",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_EVIDENCE_MERGE_NONCLAIMS,
    }


__all__ = [
    "DECISION_TYPES",
    "REVIEWED_EVIDENCE_KEYS",
    "REVIEWED_EVIDENCE_V3_KEYS",
    "SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION",
    "SURVEY_REVIEWED_SOURCE_ACCOUNTING_SCHEMA_VERSION",
    "SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION",
    "merge_reviewed_evidence",
    "validate_current_reviewed_sidecar",
    "validate_reviewed_evidence_status",
]
