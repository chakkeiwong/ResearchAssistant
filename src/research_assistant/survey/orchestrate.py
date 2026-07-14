from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_assistant.survey.bootstrap import (
    MissionBootstrapCapability,
    MissionBootstrapStore,
    UnavailableBootstrapCapability,
)

from research_assistant.survey.anchors import build_source_anchor_packet
from research_assistant.survey.build import (
    build_bootstrap_effective_seed_skeleton,
    build_survey_evidence_packet,
    validate_public_metadata_v2_bundle,
)
from research_assistant.survey.artifact_lineage import (
    PACKET_COVERAGE_FILES,
    PACKET_QUEUE_FILES,
    ArtifactStateManager,
    classify_review_queue_digest,
    normalized_identity_text,
    read_packet_json,
    read_artifact_genesis,
    semantic_item,
    sha256_file,
    validate_semantic_items,
    workflow_blocker_source_id,
)
from research_assistant.survey.coverage_ledgers import build_coverage_payloads
from research_assistant.survey.discovery_quality import (
    PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION,
)
from research_assistant.survey.hostile_review import (
    HOSTILE_REVIEW_KEYS,
    SURVEY_HOSTILE_REVIEW_SCHEMA_VERSION,
    refresh_final_packet_readiness,
    run_hostile_review_gate,
    validate_final_packet_readiness,
    validate_hostile_review_result,
)
from research_assistant.survey.mission_state import (
    EXPLICIT_SEED_INPUT_MODE,
    MISSION_CONTROL_SCHEMA,
    TOPIC_INPUT_MODE,
    TOPIC_MISSION_CONTROL_SCHEMA,
    MissionSnapshot,
    MissionStateError,
    MissionStateManager,
    mission_input_view,
)
from research_assistant.survey.omission_review import (
    OmissionDecisionSetSnapshot,
    resolve_current_omission_sidecar_path,
    resolve_current_reviewed_omissions,
)
from research_assistant.survey.claim_review import resolve_current_reviewed_claims
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.reviewed_merge import (
    REVIEWED_EVIDENCE_KEYS,
    REVIEWED_EVIDENCE_V3_KEYS,
    SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
    SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION,
    merge_reviewed_evidence,
    validate_current_reviewed_sidecar,
    validate_reviewed_evidence_status,
)
from research_assistant.survey.reviewed_packet import (
    REVIEWED_FINAL_PACKET_KEYS,
    REVIEWED_FINAL_PACKET_V2_KEYS,
    SURVEY_REVIEWED_FINAL_PACKET_SCHEMA_VERSION,
    SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION,
    compose_reviewed_final_packet,
    validate_reviewed_final_packet,
)
from research_assistant.survey.source_safety_review import resolve_current_source_safety
from research_assistant.survey.review_decisions import workflow_blocker_resolution
from research_assistant.survey.packet import compose_public_source_evidence_packet
from research_assistant.survey.source_intake import (
    MissionSourceCapability,
    build_source_intake_metadata_authority,
    run_mission_source_intake,
    validate_mission_source_intake,
)
from research_assistant.survey.supervisor import (
    LOCAL_SUPERVISOR_SCHEMA_VERSION,
    MAX_LOCAL_TRANSITIONS,
    classify_repairable_json,
    observation_sha256,
    preflight_mission_output,
    validate_anchor_packet,
    validate_offline_skeleton,
    validate_public_source_packet,
    validate_public_source_packet_inputs,
    validate_source_intake_for_context,
    validate_supervisor_artifact_root,
    validate_supervisor_read_root,
)


SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION = "ra-survey-public-source-orchestration-result-v1"
TOPIC_SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION = "ra-survey-public-source-orchestration-result-v3"
SURVEY_MISSION_CONTROL_SCHEMA_VERSION = MISSION_CONTROL_SCHEMA
SURVEY_REVIEW_QUEUE_SCHEMA_VERSION = "ra-survey-public-source-review-queue-v2"
SURVEY_NEXT_ACTION_SCHEMA_VERSION = "ra-survey-public-source-next-action-v1"
SURVEY_PUBLIC_DISCOVERY_CONFIRMATION_SCHEMA_VERSION = "ra-survey-public-discovery-confirmation-v1"

ORCHESTRATION_NONCLAIMS = [
    "live web coverage",
    "literature completeness",
    "survey completeness",
    "source/PDF/full-text download completion",
    "retraction/version safety",
    "technical claim support",
    "final prose readiness",
    "product readiness",
    "scientific correctness",
]

PUBLIC_DISCOVERY_DEFAULT_PROVIDERS = ["openalex", "arxiv"]
PUBLIC_DISCOVERY_ALLOWED_DOMAINS = ["api.openalex.org", "export.arxiv.org", "arxiv.org"]
PUBLIC_DISCOVERY_MAX_METADATA_RECORDS = 25


def run_public_source_workflow(
    *,
    topic: str,
    seeds: list[str] | None,
    output_dir: Path,
    run_safe_local: bool = False,
    confirm_public_discovery: bool = False,
    resume: bool = False,
    force: bool = False,
    metadata_dir: Path | None = None,
    source_status_dir: Path | None = None,
    anchor_dir: Path | None = None,
    packet_dir: Path | None = None,
    coverage_dir: Path | None = None,
    reviewed_claims_dir: Path | None = None,
    reviewed_source_safety_dir: Path | None = None,
    reviewed_omissions_dir: Path | None = None,
    reviewed_workflow_blockers_dir: Path | None = None,
    reviewed_evidence_dir: Path | None = None,
    local_evidence_root: Path | None = None,
    source_capability: MissionSourceCapability | None = None,
    bootstrap_capability: MissionBootstrapCapability | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    manager: MissionStateManager | None = None
    input_mode = TOPIC_INPUT_MODE if seeds is None else EXPLICIT_SEED_INPUT_MODE
    initial_seeds = [] if seeds is None else seeds
    try:
        manager = MissionStateManager(
            output_dir=output_dir,
            topic=topic,
            seeds=initial_seeds,
            input_mode=input_mode,
            confirm_public_discovery=confirm_public_discovery,
            resume=resume,
            force=force,
        )
        snapshot = manager.begin()
        snapshot = manager.checkpoint_confirmation()
        if input_mode == TOPIC_INPUT_MODE:
            return _run_topic_bootstrap_locked(
                manager=manager,
                snapshot=snapshot,
                output_dir=output_dir,
                resume=resume,
                bootstrap_capability=bootstrap_capability,
            )
        if run_safe_local:
            return _run_safe_local_supervisor(
                manager=manager,
                snapshot=snapshot,
                output_dir=output_dir,
                resume=resume,
                metadata_dir=metadata_dir,
                source_status_dir=source_status_dir,
                anchor_dir=anchor_dir,
                packet_dir=packet_dir,
                coverage_dir=coverage_dir,
                reviewed_claims_dir=reviewed_claims_dir,
                reviewed_source_safety_dir=reviewed_source_safety_dir,
                reviewed_omissions_dir=reviewed_omissions_dir,
                reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
                reviewed_evidence_dir=reviewed_evidence_dir,
                local_evidence_root=local_evidence_root,
                source_capability=source_capability,
            )
        return _run_public_source_workflow_locked(
            manager=manager,
            snapshot=snapshot,
            output_dir=output_dir,
            run_safe_local=run_safe_local,
            resume=resume,
            force=force,
            metadata_dir=metadata_dir,
            source_status_dir=source_status_dir,
            anchor_dir=anchor_dir,
            packet_dir=packet_dir,
            coverage_dir=coverage_dir,
            reviewed_claims_dir=reviewed_claims_dir,
            reviewed_source_safety_dir=reviewed_source_safety_dir,
            reviewed_omissions_dir=reviewed_omissions_dir,
            reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
            reviewed_evidence_dir=reviewed_evidence_dir,
            local_evidence_root=local_evidence_root,
            observation_only=False,
        )
    except MissionStateError as exc:
        if manager is not None:
            manager.abort()
        if input_mode == TOPIC_INPUT_MODE:
            return _blocked_topic_result(
                reason=exc.code,
                topic=topic,
                output_dir=output_dir,
                details=exc.details or None,
            )
        return _blocked(
            exc.code,
            output_dir,
            [str(exc)],
            details=exc.details or None,
        )
    except Exception:
        if manager is not None:
            manager.abort()
        raise


def _blocked_topic_result(
    *,
    reason: str,
    topic: str,
    output_dir: Path,
    details: dict[str, Any] | None,
) -> dict[str, Any]:
    confirmation = _public_discovery_confirmation(
        output_dir=output_dir,
        confirmation={"confirmed": False, "confirmed_at": None, "confirmation_source": None},
    )
    next_action = {
        "schema_version": SURVEY_NEXT_ACTION_SCHEMA_VERSION,
        "created_at": _utc_now_iso(),
        "gate_id": "topic_bootstrap",
        "approval_required": False,
        "safe_next_commands": ["repair the exact invalid mission/bootstrap artifact before retrying"],
        "blockers": [{"code": reason, "details": details}],
        "required_artifacts": ["valid topic mission and bootstrap authority"],
        "public_discovery_confirmation": confirmation,
        "forbidden_actions": [
            "do not retry a possibly invoked bootstrap capability",
            "do not adopt corrupt, stale, foreign, or partial bootstrap evidence",
            "do not run provider, source, PDF, full-text, or downstream actions while blocked",
        ],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
        "action_id": "terminal_blocked_invalid_topic_mission",
        "status": "blocked_invalid_topic_mission",
        "mission_status": "blocked",
        "summary": f"Topic mission validation failed closed: {reason}.",
    }
    return {
        "schema_version": TOPIC_SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "topic": topic if isinstance(topic, str) else "",
        "seed_count": 0,
        "input_mode": TOPIC_INPUT_MODE,
        "initial_seeds": [],
        "effective_seeds": [],
        "effective_seed_count": 0,
        "bootstrap_attempt_state": "not_started",
        "bootstrap_outcome": None,
        "bootstrap_authority": None,
        "output_dir": str(output_dir),
        "mission_control_path": str(output_dir / "mission_control.json"),
        "next_action_path": str(output_dir / "next_action.json"),
        "mission_id": None,
        "mission_fingerprint": None,
        "generation_id": None,
        "artifact_paths": {},
        "next_gate": {"gate_id": "topic_bootstrap", "status": "blocked_invalid_topic_mission", "approval_required": False},
        "next_action": next_action,
        "public_discovery_confirmation": confirmation,
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "artifact_state": None,
        "phase_statuses": {},
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "safe_next_commands": next_action["safe_next_commands"],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
        "local_supervisor": None,
    }


def _topic_next_action(
    *,
    output_dir: Path,
    confirmation: dict[str, Any],
    bootstrap: dict[str, Any],
) -> dict[str, Any]:
    state = bootstrap["attempt_state"]
    outcome = bootstrap["outcome"]
    if not confirmation["confirmed"]:
        action_id = "confirm_public_discovery"
        status = "confirmation_required"
        mission_status = "blocked_at_gate"
        summary = "Record the one mission-bound public-discovery confirmation before topic bootstrap."
        required = ["public_discovery_confirmation"]
    elif state == "call_started_indeterminate":
        action_id = "terminal_blocked_bootstrap_call_indeterminate"
        status = action_id
        mission_status = "blocked_at_gate"
        summary = "The bootstrap capability may have run; ordinary resume cannot retry this request."
        required = ["separately reviewed explicit retry transition"]
    elif outcome in {"empty", "ambiguous", "unavailable", "capped"}:
        action_id = f"terminal_blocked_bootstrap_{outcome}"
        status = action_id
        mission_status = "blocked_at_gate"
        summary = f"Topic bootstrap closed honestly with outcome: {outcome}."
        required = [f"future reviewed bootstrap repair for {outcome}"]
    elif state == "selected_complete" and outcome == "selected":
        action_id = "topic_bootstrap_selected_local_continuation"
        status = "ready_for_local_continuation"
        mission_status = "ready_for_local_continuation"
        summary = "A validated bootstrap set is selected; derived effective seeds are locally authoritative."
        required = ["validated effective-seed downstream continuation"]
    else:
        action_id = "resume_topic_bootstrap"
        status = "ready_for_topic_bootstrap"
        mission_status = "ready_for_local_continuation"
        summary = "Resume the deterministic topic-bootstrap transaction under the held mission lock."
        required = ["bootstrap attempt"]
    return {
        "schema_version": SURVEY_NEXT_ACTION_SCHEMA_VERSION,
        "created_at": _utc_now_iso(),
        "gate_id": "topic_bootstrap",
        "approval_required": not confirmation["confirmed"],
        "safe_next_commands": [
            "rerun run-public-source-workflow with the same topic and output root, --resume, and the required confirmation if not already recorded"
        ],
        "blockers": [] if mission_status == "ready_for_local_continuation" else [action_id],
        "required_artifacts": required,
        "public_discovery_confirmation": confirmation,
        "forbidden_actions": [
            "do not treat the topic as a paper seed",
            "do not retry an indeterminate bootstrap call on ordinary resume",
            "do not run provider, source, PDF, full-text, model-worker, or network actions in M17",
            "do not expose prepared bootstrap evidence as effective seed authority",
        ],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
        "action_id": action_id,
        "status": status,
        "mission_status": mission_status,
        "summary": summary,
    }


def _topic_mission_control_payload(
    *,
    snapshot: MissionSnapshot,
    output_dir: Path,
    resume: bool,
    confirmation: dict[str, Any],
    bootstrap: dict[str, Any],
    next_action: dict[str, Any],
    actions: list[dict[str, Any]],
    phase_statuses: dict[str, Any],
) -> dict[str, Any]:
    view = mission_input_view(snapshot.contract)
    return {
        "schema_version": TOPIC_MISSION_CONTROL_SCHEMA,
        "status": next_action["mission_status"],
        "created_at": snapshot.contract["created_at"],
        "updated_at": _utc_now_iso(),
        "topic": view["normalized_topic"]["display"],
        "seeds": [],
        "input_mode": TOPIC_INPUT_MODE,
        "initial_seeds": [],
        "effective_seeds": bootstrap["effective_seeds"],
        "bootstrap_attempt_state": bootstrap["attempt_state"],
        "bootstrap_outcome": bootstrap["outcome"],
        "bootstrap_authority": bootstrap["authority"],
        "output_dir": str(output_dir),
        "resume": resume,
        "phase_statuses": phase_statuses,
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "source_intake_metadata_authority": None,
        "public_discovery_confirmation": confirmation,
        "actions": actions,
        "next_gate": {
            "gate_id": "topic_bootstrap",
            "status": next_action["status"],
            "approval_required": next_action["approval_required"],
        },
        "next_action_path": str(output_dir / "next_action.json"),
        "next_action": next_action,
        "workflow_state": None,
        "artifact_state": None,
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "safe_next_commands": next_action["safe_next_commands"],
        "forbidden_actions": next_action["forbidden_actions"],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
        "local_supervisor": None,
    }


def _topic_workflow_result(mission_control: dict[str, Any], next_action: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": TOPIC_SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION,
        "status": mission_control["status"],
        "topic": mission_control["topic"],
        "seed_count": 0,
        "input_mode": TOPIC_INPUT_MODE,
        "initial_seeds": [],
        "effective_seeds": mission_control["effective_seeds"],
        "effective_seed_count": len(mission_control["effective_seeds"]),
        "bootstrap_attempt_state": mission_control["bootstrap_attempt_state"],
        "bootstrap_outcome": mission_control["bootstrap_outcome"],
        "bootstrap_authority": mission_control["bootstrap_authority"],
        "output_dir": mission_control["output_dir"],
        "mission_control_path": str(Path(mission_control["output_dir"]) / "mission_control.json"),
        "next_action_path": str(Path(mission_control["output_dir"]) / "next_action.json"),
        "mission_id": mission_control["mission_id"],
        "mission_fingerprint": mission_control["mission_fingerprint"],
        "generation_id": mission_control["generation_id"],
        "artifact_paths": {
            "mission_control.json": str(Path(mission_control["output_dir"]) / "mission_control.json"),
            "next_action.json": str(Path(mission_control["output_dir"]) / "next_action.json"),
            **(
                {"bootstrap_effective_seed_skeleton": str(Path(mission_control["output_dir"]) / "offline_skeleton")}
                if mission_control["phase_statuses"].get("offline_skeleton", {}).get("exists")
                else {}
            ),
        },
        "next_gate": mission_control["next_gate"],
        "next_action": next_action,
        "public_discovery_confirmation": mission_control["public_discovery_confirmation"],
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "artifact_state": None,
        "phase_statuses": mission_control["phase_statuses"],
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "safe_next_commands": mission_control["safe_next_commands"],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
        "local_supervisor": None,
    }


def _run_topic_bootstrap_locked(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
    resume: bool,
    bootstrap_capability: MissionBootstrapCapability | None,
) -> dict[str, Any]:
    confirmation = _public_discovery_confirmation(
        output_dir=output_dir,
        confirmation=snapshot.contract["public_discovery_confirmation"],
    )
    if not confirmation["confirmed"]:
        bootstrap = {
            "attempt_state": "confirmation_required",
            "outcome": None,
            "effective_seeds": [],
            "authority": None,
            "request_id": None,
            "set_dir": None,
        }
    else:
        capability = bootstrap_capability or UnavailableBootstrapCapability()
        store = MissionBootstrapStore.from_snapshot(
            manager=manager,
            snapshot=snapshot,
            now=_utc_now_iso,
        )
        try:
            bootstrap = store.advance(capability)
        except MissionStateError as exc:
            if exc.code != "bootstrap_call_indeterminate":
                raise
            bootstrap = store.observe()
    actions = [{
        "action": "topic_bootstrap",
        "status": bootstrap["attempt_state"],
        "outcome": bootstrap["outcome"],
        "network_or_provider_called": False,
        "source_pdf_full_text_attempted": False,
    }]
    phase_statuses: dict[str, Any] = {}
    if bootstrap["attempt_state"] == "selected_complete" and bootstrap["outcome"] == "selected":
        build_result = build_bootstrap_effective_seed_skeleton(
            manager=manager,
            snapshot=snapshot,
            output_dir=output_dir / "offline_skeleton",
            bootstrap_authority=bootstrap["authority"],
        )
        actions.append({
            "action": "build_bootstrap_effective_seed_skeleton",
            "status": build_result["status"],
            "output_dir": build_result["output_dir"],
            "bootstrap_authority": bootstrap["authority"],
            "network_or_provider_called": False,
            "source_pdf_full_text_attempted": False,
        })
        phase_statuses["offline_skeleton"] = {
            "exists": True,
            "status": "available_bootstrap_effective_seed_skeleton",
            "path": build_result["output_dir"],
            "required_file": "bootstrap_effective_seed_context.json",
        }
    current = snapshot.mission_control
    if (
        isinstance(current, dict)
        and current.get("schema_version") == TOPIC_MISSION_CONTROL_SCHEMA
        and current.get("bootstrap_attempt_state") == bootstrap["attempt_state"]
        and current.get("bootstrap_outcome") == bootstrap["outcome"]
        and current.get("bootstrap_authority") == bootstrap["authority"]
        and current.get("effective_seeds") == bootstrap["effective_seeds"]
        and current.get("public_discovery_confirmation") == confirmation
        and current.get("phase_statuses") == phase_statuses
        and isinstance(snapshot.next_action, dict)
    ):
        manager.abort()
        return _topic_workflow_result(current, snapshot.next_action)
    next_action = _topic_next_action(
        output_dir=output_dir,
        confirmation=confirmation,
        bootstrap=bootstrap,
    )
    mission_control = _topic_mission_control_payload(
        snapshot=snapshot,
        output_dir=output_dir,
        resume=resume,
        confirmation=confirmation,
        bootstrap=bootstrap,
        next_action=next_action,
        actions=actions,
        phase_statuses=phase_statuses,
    )
    committed = manager.commit(mission_control, next_action)
    return _topic_workflow_result(
        committed.mission_control or mission_control,
        committed.next_action or next_action,
    )


def _run_public_source_workflow_locked(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
    run_safe_local: bool,
    resume: bool,
    force: bool,
    metadata_dir: Path | None,
    source_status_dir: Path | None,
    anchor_dir: Path | None,
    packet_dir: Path | None,
    coverage_dir: Path | None,
    reviewed_claims_dir: Path | None,
    reviewed_source_safety_dir: Path | None,
    reviewed_omissions_dir: Path | None,
    reviewed_workflow_blockers_dir: Path | None,
    reviewed_evidence_dir: Path | None,
    local_evidence_root: Path | None,
    observation_only: bool = False,
) -> dict[str, Any]:
    contract = snapshot.contract
    topic = contract["normalized_topic"]["display"]
    seeds = [row["display"] for row in contract["normalized_seeds"]]
    mission_control_path = output_dir / "mission_control.json"
    next_action_path = output_dir / "next_action.json"
    skeleton_dir = output_dir / "offline_skeleton"
    packet_dir = (packet_dir or output_dir / "public_source_packet").resolve()

    if not observation_only:
        output_dir.mkdir(parents=True, exist_ok=True)
    actions: list[dict[str, Any]] = []
    artifact_paths: dict[str, str] = {
        "mission_control.json": str(mission_control_path),
        "next_action.json": str(next_action_path),
    }
    public_discovery_confirmation = _public_discovery_confirmation(
        output_dir=output_dir,
        confirmation=contract["public_discovery_confirmation"],
    )

    skeleton_status = _artifact_status(skeleton_dir, "build_manifest.json")
    if run_safe_local and not skeleton_status["exists"]:
        build_result = build_survey_evidence_packet(
            topic=topic,
            seeds=seeds,
            output_dir=skeleton_dir,
            mode="offline-skeleton",
            force=force,
        )
        actions.append({
            "action": "survey_build_offline_skeleton",
            "status": build_result.get("status"),
            "output_dir": str(skeleton_dir),
            "safe_local": True,
            "live_or_download_action": False,
        })
        skeleton_status = _artifact_status(skeleton_dir, "build_manifest.json")
    else:
        actions.append({
            "action": "survey_build_offline_skeleton",
            "status": "available" if skeleton_status["exists"] else "not_run",
            "output_dir": str(skeleton_dir),
            "safe_local": True,
            "live_or_download_action": False,
        })

    if skeleton_status["exists"]:
        artifact_paths["offline_skeleton_manifest"] = str(skeleton_dir / "build_manifest.json")
        workflow_state = _read_json_if_exists(skeleton_dir / "workflow_state.json")
    else:
        workflow_state = None

    effective_metadata_dir = (metadata_dir or output_dir / "public_metadata").resolve()
    metadata_required_file = _metadata_required_file(
        effective_metadata_dir,
        canonical_root=(output_dir / "public_metadata").resolve(),
    )
    metadata_status = _phase_status(effective_metadata_dir, metadata_required_file)
    if (
        public_discovery_confirmation["confirmed"]
        and not metadata_status["exists"]
        and not observation_only
    ):
        from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed

        assert_public_write_path_allowed(effective_metadata_dir)
        write_root = Path(contract["discovery_budget"]["write_root"]).resolve()
        if not _path_is_within(effective_metadata_dir, write_root):
            raise MissionStateError(
                "public_metadata_write_outside_mission_root",
                "public metadata provider output must resolve inside the persisted mission write root",
                details={
                    "requested_metadata_dir": str(effective_metadata_dir),
                    "write_root": str(write_root),
                },
            )
        build_result = build_survey_evidence_packet(
            topic=topic,
            seeds=seeds,
            output_dir=effective_metadata_dir,
            mode="public-metadata",
            force=force,
            public_metadata_providers=PUBLIC_DISCOVERY_DEFAULT_PROVIDERS,
            max_records=PUBLIC_DISCOVERY_MAX_METADATA_RECORDS,
        )
        actions.append({
            "action": "survey_build_public_metadata",
            "status": build_result.get("status"),
            "output_dir": str(effective_metadata_dir),
            "safe_local": False,
            "live_or_download_action": True,
            "public_discovery_confirmed": True,
            "source_pdf_full_text_attempted": False,
            "credentialed_access": False,
            "technical_claim_support_created": False,
        })
        metadata_status = _phase_status(effective_metadata_dir, "build_manifest.json")
        if metadata_status["exists"]:
            artifact_paths["public_metadata_manifest"] = str(effective_metadata_dir / "build_manifest.json")
        else:
            public_discovery_confirmation["status"] = "confirmed_but_metadata_unavailable"
            public_discovery_confirmation["last_attempt"] = {
                "action": "survey_build_public_metadata",
                "status": build_result.get("status"),
                "output_dir": str(effective_metadata_dir),
                "provider_statuses": build_result.get("provider_statuses"),
                "what_is_not_concluded": build_result.get("what_is_not_concluded"),
            }
    elif metadata_status["exists"]:
        artifact_paths["public_metadata_manifest"] = str(effective_metadata_dir / "build_manifest.json")
    if metadata_status["exists"] and metadata_status["required_file"] == "build_manifest.json":
        metadata_manifest = _read_json_if_exists(effective_metadata_dir / "build_manifest.json")
        has_v2_discriminator = any(
            (effective_metadata_dir / name).exists()
            or (effective_metadata_dir / name).is_symlink()
            for name in ("identity_resolution.json", "relevance_ranking.json")
        )
        metadata_candidate = _read_json_if_exists(
            effective_metadata_dir / "candidate_ledger.json"
        )
        if has_v2_discriminator or (
            isinstance(metadata_manifest, dict)
            and metadata_manifest.get("schema_version")
            == "ra-survey-public-metadata-build-manifest-v2"
        ) or (
            isinstance(metadata_candidate, dict)
            and metadata_candidate.get("schema_version")
            == PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION
        ):
            validated_metadata = validate_public_metadata_v2_bundle(
                topic=topic,
                seeds=seeds,
                output_dir=effective_metadata_dir,
                providers=contract["discovery_budget"]["providers"],
                max_records=contract["discovery_budget"]["max_metadata_records"],
            )
            metadata_status["bundle_status"] = validated_metadata["quality_status"]
            if validated_metadata["quality_status"] != "eligible":
                metadata_status["resolution_blocked"] = True
    source_status = _phase_status(source_status_dir, "phase4_source_intake_status.json")
    anchor_status = _phase_status(anchor_dir, "source_anchor_inventory.json")
    packet_status = _artifact_status(packet_dir, "build_manifest.json")

    phase_statuses = {
        "offline_skeleton": skeleton_status,
        "public_metadata": metadata_status,
        "source_intake": source_status,
        "source_anchors": anchor_status,
        "public_source_packet": packet_status,
    }
    if packet_status["exists"]:
        artifact_paths["public_source_packet_manifest"] = str(packet_dir / "build_manifest.json")
        packet_manifest = _read_json_if_exists(packet_dir / "build_manifest.json") or {}
        workflow_state = packet_manifest.get("workflow_state") or workflow_state
    else:
        packet_manifest = {}

    gate = _next_gate(
        phase_statuses,
        public_discovery_confirmed=public_discovery_confirmation["confirmed"],
    )
    review_queue = None
    artifact_state: dict[str, Any] | None = None
    artifact_initialization_required = packet_status["exists"] and snapshot.current_pointer is None
    if packet_status["exists"]:
        _validate_artifact_packet_inputs(packet_dir)
        if observation_only:
            selected = None
            if snapshot.current_pointer is not None:
                selected = _load_current_artifact_set_readonly(
                    manager=manager,
                    snapshot=snapshot,
                    output_dir=output_dir,
                )
            if selected is None or not _selected_packet_inputs_are_current(selected, packet_dir):
                artifact_initialization_required = True
            else:
                artifact_initialization_required = False
                if coverage_dir is not None:
                    supplied_coverage = coverage_dir.absolute()
                    if (
                        supplied_coverage.is_symlink()
                        or supplied_coverage != selected.coverage_dir.absolute()
                        or supplied_coverage.resolve() != selected.coverage_dir.resolve()
                    ):
                        raise MissionStateError(
                            "stale_lineage",
                            "--coverage-dir is not the coverage directory selected by artifact-state CURRENT",
                        )
                queue_payload = _read_json_if_exists(selected.review_queue_path) or {}
                review_queue = _review_queue_summary(selected, queue_payload, reused=True)
                artifact_state = _artifact_state_summary(selected)
                artifact_paths["review_queue.json"] = review_queue["path"]
                artifact_paths["coverage_dir"] = str(selected.coverage_dir)
                coverage_dir = selected.coverage_dir
        elif not artifact_initialization_required:
            if coverage_dir is not None:
                expected_coverage = _selected_coverage_path_if_present(output_dir)
                supplied_coverage = coverage_dir.absolute()
                if (
                    expected_coverage is None
                    or supplied_coverage.is_symlink()
                    or supplied_coverage != expected_coverage.absolute()
                    or supplied_coverage.resolve() != expected_coverage.resolve()
                ):
                    raise MissionStateError(
                        "stale_lineage",
                        "--coverage-dir is not the coverage directory selected by artifact-state CURRENT",
                    )
            artifact_snapshot, reused = _compose_authoritative_artifact_set(
                manager=manager,
                snapshot=snapshot,
                output_dir=output_dir,
                topic=topic,
                packet_dir=packet_dir,
                packet_manifest=packet_manifest,
            )
            queue_payload = _read_json_if_exists(artifact_snapshot.review_queue_path) or {}
            review_queue = _review_queue_summary(artifact_snapshot, queue_payload, reused=reused)
            artifact_state = _artifact_state_summary(artifact_snapshot)
            artifact_paths["review_queue.json"] = review_queue["path"]
            artifact_paths["coverage_dir"] = str(artifact_snapshot.coverage_dir)
            coverage_dir = artifact_snapshot.coverage_dir
    reviewed_artifacts = _reviewed_artifact_statuses(
        output_dir=output_dir,
        reviewed_claims_dir=reviewed_claims_dir,
        reviewed_source_safety_dir=reviewed_source_safety_dir,
        reviewed_omissions_dir=reviewed_omissions_dir,
        reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
        reviewed_evidence_dir=reviewed_evidence_dir,
        review_queue_path=Path(review_queue["path"]) if review_queue else None,
    )
    coverage_artifacts = _coverage_artifact_statuses(output_dir=output_dir, coverage_dir=coverage_dir)
    final_artifacts = _final_artifact_statuses(
        output_dir=output_dir,
        review_queue_path=Path(review_queue["path"]) if review_queue else None,
        packet_dir=packet_dir,
        anchor_dir=Path(anchor_status["path"]) if anchor_status["exists"] else None,
        local_evidence_root=local_evidence_root,
    )
    for name, status in reviewed_artifacts.items():
        if status["exists"]:
            artifact_paths[f"{name}_path"] = status["required_path"]
    for name, status in coverage_artifacts.items():
        if status["exists"]:
            artifact_paths[f"{name}_path"] = status["required_path"]
    for name, status in final_artifacts.items():
        if status["exists"]:
            artifact_paths[f"{name}_path"] = status["required_path"]
    next_action = _next_action(
        gate=gate,
        output_dir=output_dir,
        topic=topic,
        seeds=seeds,
        packet_dir=packet_dir,
        review_queue=review_queue,
        reviewed_artifacts=reviewed_artifacts,
        coverage_artifacts=coverage_artifacts,
        final_artifacts=final_artifacts,
        anchor_dir=Path(anchor_status["path"]) if anchor_status["exists"] else None,
        local_evidence_root=local_evidence_root,
        public_discovery_confirmation=public_discovery_confirmation,
        artifact_initialization_required=artifact_initialization_required,
    )
    if observation_only and next_action.get("action_id") == "resume_to_initialize_artifact_state":
        next_action = {
            **next_action,
            "action_id": "initialize_artifact_state",
            "status": "ready_to_initialize_artifact_state",
            "summary": "Compose and atomically select the current coverage-before-review artifact set under the held mission lock.",
            "safe_next_commands": ["typed local artifact-state initialization; command strings are not executed"],
        }
    mission_control = {
        "schema_version": SURVEY_MISSION_CONTROL_SCHEMA_VERSION,
        "status": next_action["mission_status"],
        "created_at": contract["created_at"],
        "updated_at": _utc_now_iso(),
        "topic": topic,
        "seeds": seeds,
        "output_dir": str(output_dir),
        "resume": resume,
        "phase_statuses": phase_statuses,
        "reviewed_artifacts": reviewed_artifacts,
        "coverage_artifacts": coverage_artifacts,
        "final_artifacts": final_artifacts,
        "public_discovery_confirmation": public_discovery_confirmation,
        "actions": actions,
        "next_gate": gate,
        "next_action_path": str(next_action_path),
        "next_action": next_action,
        "workflow_state": workflow_state,
        "artifact_state": artifact_state,
        "review_queue_path": review_queue["path"] if review_queue else None,
        "review_queue_counts": review_queue["queue_counts"] if review_queue else None,
        "review_queue_reused": review_queue["reused_existing"] if review_queue else None,
        "safe_next_commands": next_action["safe_next_commands"],
        "forbidden_actions": [
            "do not run public discovery before public_discovery_confirmation.confirmed is true",
            "do not treat metadata, source availability, or anchor availability as technical claim support",
            "do not mark retraction/version safety checked_clear without explicit public-status or reviewed local evidence",
            "do not claim final prose readiness while ready_for_prose is false",
            "do not use credentials, private databases, paid model workers, hidden evaluator material, unbounded crawling, or outputs outside the mission directory without separate explicit approval",
        ],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }
    if observation_only:
        return _workflow_result(
            mission_control=mission_control,
            next_action=next_action,
            topic=topic,
            seeds=seeds,
            output_dir=output_dir,
            artifact_paths=artifact_paths,
            gate=gate,
            public_discovery_confirmation=public_discovery_confirmation,
            review_queue=review_queue,
            artifact_state=artifact_state,
            phase_statuses=phase_statuses,
            reviewed_artifacts=reviewed_artifacts,
            coverage_artifacts=coverage_artifacts,
            final_artifacts=final_artifacts,
            include_private_payloads=True,
        )
    committed = manager.commit(mission_control, next_action)
    committed_mission = committed.mission_control or mission_control
    committed_next_action = committed.next_action or next_action
    return _workflow_result(
        mission_control=committed_mission,
        next_action=committed_next_action,
        topic=topic,
        seeds=seeds,
        output_dir=output_dir,
        artifact_paths=artifact_paths,
        gate=gate,
        public_discovery_confirmation=public_discovery_confirmation,
        review_queue=review_queue,
        artifact_state=artifact_state,
        phase_statuses=phase_statuses,
        reviewed_artifacts=reviewed_artifacts,
        coverage_artifacts=coverage_artifacts,
        final_artifacts=final_artifacts,
        include_private_payloads=False,
    )


def _workflow_result(
    *,
    mission_control: dict[str, Any],
    next_action: dict[str, Any],
    topic: str,
    seeds: list[str],
    output_dir: Path,
    artifact_paths: dict[str, str],
    gate: dict[str, Any],
    public_discovery_confirmation: dict[str, Any],
    review_queue: dict[str, Any] | None,
    artifact_state: dict[str, Any] | None,
    phase_statuses: dict[str, dict[str, Any]],
    reviewed_artifacts: dict[str, dict[str, Any]],
    coverage_artifacts: dict[str, dict[str, Any]],
    final_artifacts: dict[str, dict[str, Any]],
    include_private_payloads: bool,
) -> dict[str, Any]:
    result = {
        "schema_version": SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION,
        "status": mission_control["status"],
        "topic": topic,
        "seed_count": len(seeds),
        "output_dir": str(output_dir),
        "mission_control_path": str(output_dir / "mission_control.json"),
        "next_action_path": str(output_dir / "next_action.json"),
        "mission_id": mission_control.get("mission_id"),
        "mission_fingerprint": mission_control.get("mission_fingerprint"),
        "generation_id": mission_control.get("generation_id"),
        "artifact_paths": artifact_paths,
        "next_gate": gate,
        "next_action": next_action,
        "public_discovery_confirmation": public_discovery_confirmation,
        "review_queue_path": review_queue["path"] if review_queue else None,
        "review_queue_counts": review_queue["queue_counts"] if review_queue else None,
        "review_queue_reused": review_queue["reused_existing"] if review_queue else None,
        "artifact_state": artifact_state,
        "phase_statuses": phase_statuses,
        "reviewed_artifacts": reviewed_artifacts,
        "coverage_artifacts": coverage_artifacts,
        "final_artifacts": final_artifacts,
        "safe_next_commands": mission_control["safe_next_commands"],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }
    if include_private_payloads:
        result["_mission_control_payload"] = mission_control
        result["_next_action_payload"] = next_action
    return result


def _run_safe_local_supervisor(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
    resume: bool,
    metadata_dir: Path | None,
    source_status_dir: Path | None,
    anchor_dir: Path | None,
    packet_dir: Path | None,
    coverage_dir: Path | None,
    reviewed_claims_dir: Path | None,
    reviewed_source_safety_dir: Path | None,
    reviewed_omissions_dir: Path | None,
    reviewed_workflow_blockers_dir: Path | None,
    reviewed_evidence_dir: Path | None,
    local_evidence_root: Path | None,
    source_capability: MissionSourceCapability | None,
) -> dict[str, Any]:
    reviewed_roots = {
        "reviewed_claims": (reviewed_claims_dir, output_dir / "reviewed_claims"),
        "reviewed_source_safety": (reviewed_source_safety_dir, output_dir / "reviewed_source_safety"),
        "reviewed_omissions": (reviewed_omissions_dir, output_dir / "reviewed_omissions"),
        "reviewed_workflow_blockers": (
            reviewed_workflow_blockers_dir,
            output_dir / "reviewed_workflow_blockers",
        ),
        "reviewed_evidence": (reviewed_evidence_dir, output_dir / "reviewed_evidence"),
    }
    for label, (supplied_root, canonical_root) in reviewed_roots.items():
        if supplied_root is not None and supplied_root.absolute() != canonical_root.absolute():
            observation = _observation_from_snapshot(
                manager,
                output_dir,
                code=f"noncanonical_safe_local_{label}_root",
            )
            return _finish_supervisor(
                manager=manager,
                observation=observation,
                history=[],
                terminal_status="terminal_blocked_invalid_artifact",
                terminal_action_id="terminal_blocked_invalid_artifact",
                terminal_reason=f"noncanonical_safe_local_{label}_root",
            )
    roots = {
        "metadata": (metadata_dir or output_dir / "public_metadata").absolute(),
        "source_status": (source_status_dir or output_dir / "source_intake").absolute(),
        "anchor": (anchor_dir or output_dir / "source_anchors").absolute(),
        "packet": (packet_dir or output_dir / "public_source_packet").absolute(),
    }
    supplied = {
        "anchor": anchor_dir is not None,
        "packet": packet_dir is not None,
    }
    history: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_snapshot = snapshot

    while True:
        try:
            observation = _supervisor_observe(
                manager=manager,
                snapshot=current_snapshot,
                output_dir=output_dir,
                resume=resume,
                roots=roots,
                supplied=supplied,
                coverage_dir=coverage_dir,
                reviewed_claims_dir=reviewed_claims_dir,
                reviewed_source_safety_dir=reviewed_source_safety_dir,
                reviewed_omissions_dir=reviewed_omissions_dir,
                reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
                reviewed_evidence_dir=reviewed_evidence_dir,
                local_evidence_root=local_evidence_root,
            )
        except MissionStateError as exc:
            observation = _observation_from_snapshot(manager, output_dir, code=exc.code)
            return _finish_supervisor(
                manager=manager,
                observation=observation,
                history=history,
                terminal_status="terminal_blocked_invalid_artifact",
                terminal_action_id="terminal_blocked_invalid_artifact",
                terminal_reason=exc.code,
            )

        signature = observation_sha256(observation)
        classification = _classify_supervisor_observation(
            observation,
            snapshot=current_snapshot,
            output_dir=output_dir,
            roots=roots,
            supplied=supplied,
            source_capability=source_capability,
        )
        if classification["dispatch_class"] == "terminal":
            return _finish_supervisor(
                manager=manager,
                observation=observation,
                history=history,
                terminal_status=classification["terminal_status"],
                terminal_action_id=classification["terminal_action_id"],
                terminal_reason=classification["reason"],
            )
        if len(history) >= MAX_LOCAL_TRANSITIONS:
            return _finish_supervisor(
                manager=manager,
                observation=observation,
                history=history,
                terminal_status="terminal_blocked_transition_limit",
                terminal_action_id="terminal_blocked_transition_limit",
                terminal_reason="maximum_typed_stage_dispatches_reached",
            )

        mission_payload = observation.pop("_mission_control_payload")
        next_payload = observation.pop("_next_action_payload")
        if classification["action_id"] == "source_intake":
            authority = build_source_intake_metadata_authority(
                mission_root=output_dir,
                metadata_root=roots["metadata"],
                snapshot=current_snapshot,
            )
            mission_payload["source_intake_metadata_authority"] = authority
            next_payload["source_intake_metadata_authority"] = authority
            mission_payload["next_action"] = next_payload
        current_snapshot = manager.checkpoint(mission_payload, next_payload)
        stage_id = classification["action_id"]
        row = {
            "transition_index": len(history),
            "observed_action_id": observation["next_action"]["action_id"],
            "pre_dispatch_observation_sha256": signature,
            "dispatch_class": classification["dispatch_class"],
            "stage_id": stage_id,
            "stage_result": None,
            "post_dispatch_outcome": None,
        }
        try:
            stage_result = _dispatch_safe_local_stage(
                action_id=stage_id,
                manager=manager,
                snapshot=current_snapshot,
                observation=observation,
                output_dir=output_dir,
                roots=roots,
                local_evidence_root=local_evidence_root,
                source_capability=source_capability,
            )
            _validate_stage_result_outputs(stage_result, output_dir=output_dir)
        except Exception as exc:
            row["stage_result"] = {
                "schema_version": None,
                "status": "exception",
                "exception_class": type(exc).__name__,
                "error_code": exc.code if isinstance(exc, MissionStateError) else "unexpected_stage_exception",
                "required_output_paths": classification.get("required_output_paths", []),
            }
            history.append(row)
            try:
                post = _supervisor_observe(
                    manager=manager,
                    snapshot=current_snapshot,
                    output_dir=output_dir,
                    resume=True,
                    roots=roots,
                    supplied=supplied,
                    coverage_dir=coverage_dir,
                    reviewed_claims_dir=reviewed_claims_dir,
                    reviewed_source_safety_dir=reviewed_source_safety_dir,
                    reviewed_omissions_dir=reviewed_omissions_dir,
                    reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
                    reviewed_evidence_dir=reviewed_evidence_dir,
                    local_evidence_root=local_evidence_root,
                )
            except MissionStateError as observation_error:
                row["post_dispatch_outcome"] = "stage_failed"
                return _finish_supervisor(
                    manager=manager,
                    observation=observation,
                    history=history,
                    terminal_status="terminal_blocked_invalid_artifact",
                    terminal_action_id="terminal_blocked_invalid_artifact",
                    terminal_reason=observation_error.code,
                )
            except Exception:
                manager.abort()
                return _blocked(
                    "supervisor_reobservation_failed",
                    output_dir,
                    ["safe post-exception observation failed; the last pre-stage generation remains authoritative"],
                )
            row["post_dispatch_outcome"] = "stage_failed"
            return _finish_supervisor(
                manager=manager,
                observation=post,
                history=history,
                terminal_status="terminal_blocked_stage_failure",
                terminal_action_id="terminal_blocked_stage_failure",
                terminal_reason=row["stage_result"]["error_code"],
            )

        row["stage_result"] = stage_result
        if stage_result.get("status") == "optional_readiness_refresh_failed":
            row["post_dispatch_outcome"] = "stage_failed"
            history.append(row)
            hostile = observation["final_artifacts"]["hostile_review_result"]
            ready = hostile.get("ready_for_prose") is True
            return _finish_supervisor(
                manager=manager,
                observation=observation,
                history=history,
                terminal_status=(
                    "terminal_ready_for_reviewed_prose_within_recorded_scope"
                    if ready
                    else "terminal_blocked_hostile_review"
                ),
                terminal_action_id=(
                    "terminal_ready_for_reviewed_prose"
                    if ready
                    else "terminal_blocked_hostile_review"
                ),
                terminal_reason="optional_readiness_view_regeneration_failed_authority_unchanged",
            )

        history.append(row)
        try:
            post = _supervisor_observe(
                manager=manager,
                snapshot=current_snapshot,
                output_dir=output_dir,
                resume=True,
                roots=roots,
                supplied=supplied,
                coverage_dir=coverage_dir,
                reviewed_claims_dir=reviewed_claims_dir,
                reviewed_source_safety_dir=reviewed_source_safety_dir,
                reviewed_omissions_dir=reviewed_omissions_dir,
                reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
                reviewed_evidence_dir=reviewed_evidence_dir,
                local_evidence_root=local_evidence_root,
            )
        except MissionStateError as exc:
            row["post_dispatch_outcome"] = "stage_failed"
            return _finish_supervisor(
                manager=manager,
                observation=observation,
                history=history,
                terminal_status="terminal_blocked_invalid_artifact",
                terminal_action_id="terminal_blocked_invalid_artifact",
                terminal_reason=exc.code,
            )
        except Exception:
            manager.abort()
            return _blocked(
                "supervisor_reobservation_failed",
                output_dir,
                ["safe post-stage observation failed; the last pre-stage generation remains authoritative"],
            )
        post_signature = observation_sha256(post)
        if post_signature == signature:
            row["post_dispatch_outcome"] = "no_progress"
            return _finish_supervisor(
                manager=manager,
                observation=post,
                history=history,
                terminal_status="terminal_blocked_no_progress",
                terminal_action_id="terminal_blocked_no_progress",
                terminal_reason="typed_stage_did_not_change_normalized_observation",
            )
        if post_signature in seen:
            row["post_dispatch_outcome"] = "cycle"
            return _finish_supervisor(
                manager=manager,
                observation=post,
                history=history,
                terminal_status="terminal_blocked_cycle",
                terminal_action_id="terminal_blocked_cycle",
                terminal_reason="normalized_observation_cycle_detected",
            )
        row["post_dispatch_outcome"] = "progress"
        seen.add(signature)
        current_snapshot = manager.snapshot or current_snapshot


def _supervisor_observe(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
    resume: bool,
    roots: dict[str, Path],
    supplied: dict[str, bool],
    coverage_dir: Path | None,
    reviewed_claims_dir: Path | None,
    reviewed_source_safety_dir: Path | None,
    reviewed_omissions_dir: Path | None,
    reviewed_workflow_blockers_dir: Path | None,
    reviewed_evidence_dir: Path | None,
    local_evidence_root: Path | None,
) -> dict[str, Any]:
    for name, root in roots.items():
        validate_supervisor_read_root(root, label=f"{name} read")
    canonical_status = output_dir / "source_intake" / "phase4_source_intake_status.json"
    if roots["source_status"] == output_dir / "source_intake" and (
        canonical_status.exists() or canonical_status.is_symlink()
    ):
        validate_mission_source_intake(
            mission_root=output_dir,
            snapshot=snapshot,
            status_path=canonical_status,
        )
    skeleton = output_dir / "offline_skeleton"
    if skeleton.exists() or skeleton.is_symlink():
        validate_offline_skeleton(skeleton)
    if roots["anchor"].exists() or roots["anchor"].is_symlink():
        validate_anchor_packet(
            roots["anchor"],
            source_status_path=roots["source_status"] / "phase4_source_intake_status.json",
            expected_topic=snapshot.contract["normalized_topic"]["display"],
            mission_root=output_dir,
            mission_snapshot=snapshot,
        )
    if roots["packet"].exists() or roots["packet"].is_symlink():
        validate_public_source_packet(
            roots["packet"],
            metadata_dir=roots["metadata"],
            source_status_dir=roots["source_status"],
            anchor_dir=roots["anchor"],
            mission_root=output_dir,
            mission_snapshot=snapshot,
        )
    validate_supervisor_artifact_root(
        output_dir / "reviewed_evidence",
        allowed_files={
            "reviewed_evidence_status.json",
            "reviewed_source_outcome_blockers.json",
            "reviewed_source_accounting.json",
        },
        label="reviewed evidence",
    )
    validate_supervisor_artifact_root(
        output_dir / "reviewed_final_packet",
        allowed_files={"reviewed_final_packet.json"},
        label="reviewed final packet",
    )
    validate_supervisor_artifact_root(
        output_dir / "hostile_review",
        allowed_files={"hostile_review_result.json", "final_packet_readiness.json"},
        label="hostile review",
    )
    observation = _run_public_source_workflow_locked(
        manager=manager,
        snapshot=snapshot,
        output_dir=output_dir,
        run_safe_local=False,
        resume=resume,
        force=False,
        metadata_dir=roots["metadata"],
        source_status_dir=roots["source_status"],
        anchor_dir=roots["anchor"],
        packet_dir=roots["packet"],
        coverage_dir=coverage_dir,
        reviewed_claims_dir=reviewed_claims_dir,
        reviewed_source_safety_dir=reviewed_source_safety_dir,
        reviewed_omissions_dir=reviewed_omissions_dir,
        reviewed_workflow_blockers_dir=reviewed_workflow_blockers_dir,
        reviewed_evidence_dir=reviewed_evidence_dir,
        local_evidence_root=local_evidence_root,
        observation_only=True,
    )
    observation["mission_id"] = snapshot.contract["mission_id"]
    observation["mission_fingerprint"] = snapshot.contract["mission_fingerprint"]
    if observation["phase_statuses"]["offline_skeleton"]["exists"] is not True:
        observation["next_action"] = {
            **observation["next_action"],
            "action_id": "build_offline_skeleton",
            "status": "ready_for_offline_skeleton",
            "mission_status": "ready_for_local_continuation",
            "summary": "Create the deterministic offline skeleton before stopping at an external boundary.",
            "safe_next_commands": ["typed local offline-skeleton stage; command strings are not executed"],
        }
        observation["_next_action_payload"] = observation["next_action"]
        observation["_mission_control_payload"]["status"] = "ready_for_local_continuation"
        observation["_mission_control_payload"]["next_action"] = observation["next_action"]
        observation["_mission_control_payload"]["safe_next_commands"] = observation["next_action"]["safe_next_commands"]
    return observation


def _classify_supervisor_observation(
    observation: dict[str, Any],
    *,
    snapshot: MissionSnapshot,
    output_dir: Path,
    roots: dict[str, Path],
    supplied: dict[str, bool],
    source_capability: MissionSourceCapability | None,
) -> dict[str, Any]:
    action = observation["next_action"]["action_id"]
    local = {
        "build_offline_skeleton": "local_writer",
        "source_anchors": "local_writer",
        "public_source_packet": "local_writer",
        "initialize_artifact_state": "lineage_writer",
        "merge_reviewed_evidence": "local_writer",
        "compose_reviewed_final_packet": "local_writer",
        "run_hostile_review": "local_writer",
        "refresh_final_packet_readiness": "local_writer",
    }
    if action == "source_anchors" and supplied["anchor"]:
        return _terminal_classification("terminal_blocked_invalid_artifact", action, "supplied_anchor_root_is_read_only_and_missing")
    if action == "source_anchors":
        try:
            source_authority = validate_source_intake_for_context(
                roots["source_status"] / "phase4_source_intake_status.json",
                mission_root=output_dir,
                mission_snapshot=snapshot,
            )
        except MissionStateError as exc:
            return _terminal_classification("terminal_blocked_source_intake", action, exc.code)
        if not source_authority["paper_ids"]:
            return _terminal_classification(
                "terminal_blocked_source_intake",
                "source_intake",
                "source_intake_has_no_available_records",
            )
    if action == "public_source_packet" and supplied["packet"]:
        return _terminal_classification("terminal_blocked_invalid_artifact", action, "supplied_packet_root_is_read_only_and_missing")
    if action == "public_source_packet":
        try:
            validate_public_source_packet_inputs(
                metadata_dir=roots["metadata"],
                source_status_dir=roots["source_status"],
                anchor_dir=roots["anchor"],
                mission_root=output_dir,
                mission_snapshot=snapshot,
            )
        except MissionStateError as exc:
            return _terminal_classification("terminal_blocked_invalid_artifact", action, exc.code)

    if action == "merge_reviewed_evidence":
        merge_path = output_dir / "reviewed_evidence" / "reviewed_evidence_status.json"
        shape = _classify_reviewed_evidence_shape(merge_path)
        if shape == "replay_candidate":
            action = "repair_reviewed_evidence"
        elif shape == "terminal_invalid":
            return _terminal_classification("terminal_blocked_invalid_artifact", action, "reviewed_evidence_shape_is_not_repairable")
    elif action == "repair_reviewed_final_packet":
        shape = _classify_reviewed_packet_shape(
            output_dir / "reviewed_final_packet" / "reviewed_final_packet.json"
        )
        if shape != "replay_candidate":
            return _terminal_classification("terminal_blocked_invalid_artifact", action, "reviewed_packet_shape_is_not_repairable")
    elif action == "repair_hostile_review_result":
        shape = classify_repairable_json(
            output_dir / "hostile_review" / "hostile_review_result.json",
            expected_schema=SURVEY_HOSTILE_REVIEW_SCHEMA_VERSION,
            expected_keys=HOSTILE_REVIEW_KEYS,
        )
        if shape != "replay_candidate":
            return _terminal_classification("terminal_blocked_invalid_artifact", action, "hostile_result_shape_is_not_repairable")
    elif action == "run_hostile_review":
        hostile = observation["final_artifacts"]["hostile_review_result"]
        readiness = observation["final_artifacts"]["final_packet_readiness"]
        if not hostile.get("present") and readiness.get("present"):
            return _terminal_classification("terminal_blocked_invalid_artifact", action, "orphan_readiness_view_is_partial_residue")
    elif action == "phase5_executing_supervisor_handoff":
        hostile = observation["final_artifacts"]["hostile_review_result"]
        readiness = observation["final_artifacts"]["final_packet_readiness"]
        if hostile.get("exists") and not readiness.get("exists"):
            action = "refresh_final_packet_readiness"
        elif hostile.get("ready_for_prose") is True:
            return _terminal_classification(
                "terminal_ready_for_reviewed_prose_within_recorded_scope",
                "terminal_ready_for_reviewed_prose",
                "authoritative_hostile_result_is_clear_within_recorded_scope",
            )
        else:
            return _terminal_classification(
                "terminal_blocked_hostile_review",
                "terminal_blocked_hostile_review",
                "authoritative_hostile_result_has_blockers",
            )

    if action in set(local) | {
        "repair_reviewed_evidence",
        "repair_reviewed_final_packet",
        "repair_hostile_review_result",
    }:
        return {
            "dispatch_class": local.get(action, "local_writer"),
            "action_id": action,
            "required_output_paths": list(observation["next_action"].get("required_artifacts") or []),
        }
    if action == "invalid_reviewed_authority":
        invalid = observation["next_action"].get("invalid_authorities") or []
        reason = invalid[0].get("code") if invalid and isinstance(invalid[0], dict) else None
        return _terminal_classification(
            "terminal_blocked_invalid_artifact",
            action,
            reason or "selected_reviewed_authority_is_invalid",
        )
    if action == "public_metadata":
        metadata_root = roots["metadata"]
        if metadata_root.exists() and any(metadata_root.iterdir()):
            return _terminal_classification(
                "terminal_blocked_invalid_artifact",
                action,
                "partial_public_metadata_v2_residue",
            )
        confirmed = observation["public_discovery_confirmation"].get("confirmed") is True
        return _terminal_classification(
            (
                "terminal_blocked_external_or_future_phase"
                if confirmed
                else "terminal_blocked_public_discovery_confirmation"
            ),
            action,
            "provider_metadata_is_not_a_phase5_local_action",
        )
    if action == "public_metadata_resolution":
        return _terminal_classification(
            "terminal_blocked_source_intake",
            action,
            "source_metadata_seed_resolution_blocked",
        )
    if action == "source_intake":
        confirmed = observation["public_discovery_confirmation"].get("confirmed") is True
        canonical_metadata = roots["metadata"] == output_dir / "public_metadata"
        canonical_status = roots["source_status"] == output_dir / "source_intake"
        if confirmed and canonical_metadata and canonical_status:
            try:
                build_source_intake_metadata_authority(
                    mission_root=output_dir,
                    metadata_root=roots["metadata"],
                    snapshot=snapshot,
                )
            except MissionStateError as exc:
                return _terminal_classification(
                    "terminal_blocked_source_intake",
                    action,
                    exc.code,
                )
        if confirmed and source_capability is not None and canonical_metadata and canonical_status:
            return {
                "dispatch_class": "local_writer",
                "action_id": action,
                "required_output_paths": [
                    str(output_dir / "source_intake" / "source_intake_outcomes.json"),
                    str(output_dir / "source_intake" / "phase4_source_intake_status.json"),
                ],
            }
        return _terminal_classification(
            "terminal_blocked_source_intake",
            action,
            (
                "confirmed_external_source_capability_required"
                if confirmed and source_capability is None
                else "canonical_mission_source_intake_required"
                if confirmed
                else "source_intake_confirmation_required"
            ),
        )
    if action.startswith("import_reviewed_") or action in {"create_review_queue"}:
        return _terminal_classification("terminal_blocked_human_review", action, "explicit_review_input_is_required")
    if action == "resolve_reviewed_evidence_blockers":
        return _terminal_classification("terminal_blocked_reviewed_evidence", action, "reviewed_evidence_has_open_outcomes")
    if action in {"repair_authoritative_coverage"}:
        return _terminal_classification("terminal_blocked_invalid_artifact", action, "selected_authoritative_coverage_is_invalid")
    return _terminal_classification("terminal_blocked_external_or_future_phase", action, "action_is_not_in_the_phase5_registry")


def _terminal_classification(status: str, action_id: str, reason: str) -> dict[str, Any]:
    return {
        "dispatch_class": "terminal",
        "terminal_status": status,
        "terminal_action_id": action_id,
        "reason": reason,
    }


def _dispatch_safe_local_stage(
    *,
    action_id: str,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    observation: dict[str, Any],
    output_dir: Path,
    roots: dict[str, Path],
    local_evidence_root: Path | None,
    source_capability: MissionSourceCapability | None,
) -> dict[str, Any]:
    topic = snapshot.contract["normalized_topic"]["display"]
    seeds = [row["display"] for row in snapshot.contract["normalized_seeds"]]
    if action_id == "build_offline_skeleton":
        target = preflight_mission_output(output_dir, output_dir / "offline_skeleton", name="offline_skeleton")
        result = build_survey_evidence_packet(topic=topic, seeds=seeds, output_dir=target, mode="offline-skeleton")
        if result.get("status") != "created_skeleton":
            raise MissionStateError("offline_skeleton_stage_failed", "offline skeleton writer did not report success")
        validate_offline_skeleton(target)
        return _stage_result(result, [Path(path) for path in result["artifact_paths"].values()])
    if action_id == "source_intake":
        if source_capability is None:
            raise MissionStateError(
                "source_capability_missing",
                "source intake dispatch requires an injected fixture capability",
            )
        result = run_mission_source_intake(
            mission_root=output_dir,
            metadata_root=roots["metadata"],
            snapshot=snapshot,
            capability=source_capability,
        )
        return result
    if action_id == "source_anchors":
        authority = validate_source_intake_for_context(
            roots["source_status"] / "phase4_source_intake_status.json",
            mission_root=output_dir,
            mission_snapshot=snapshot,
        )
        target = preflight_mission_output(output_dir, output_dir / "source_anchors", name="source_anchors")
        result = build_source_anchor_packet(
            paper_ids=authority["paper_ids"],
            output_dir=target,
            topic=topic,
            root=authority["project_root"],
        )
        if result.get("status") not in {"anchors_extracted", "source_gaps_or_no_anchors"}:
            raise MissionStateError("source_anchor_stage_failed", "source anchor writer did not report success")
        validate_anchor_packet(
            target,
            source_status_path=roots["source_status"] / "phase4_source_intake_status.json",
            expected_topic=topic,
            mission_root=output_dir,
            mission_snapshot=snapshot,
        )
        return _stage_result(result, [Path(path) for path in result["artifact_paths"].values()])
    if action_id == "public_source_packet":
        validate_public_source_packet_inputs(
            metadata_dir=roots["metadata"],
            source_status_dir=roots["source_status"],
            anchor_dir=roots["anchor"],
            mission_root=output_dir,
            mission_snapshot=snapshot,
        )
        target = preflight_mission_output(output_dir, output_dir / "public_source_packet", name="public_source_packet")
        result = compose_public_source_evidence_packet(
            topic=topic,
            output_dir=target,
            metadata_dir=roots["metadata"],
            source_status_dir=roots["source_status"],
            anchor_dir=roots["anchor"],
            _mission_v2_authority=True,
        )
        if result.get("status") != "packet_composed_with_blockers":
            raise MissionStateError("public_source_packet_stage_failed", "packet writer did not report success")
        validate_public_source_packet(
            target,
            metadata_dir=roots["metadata"],
            source_status_dir=roots["source_status"],
            anchor_dir=roots["anchor"],
            mission_root=output_dir,
            mission_snapshot=snapshot,
        )
        return _stage_result(result, [Path(path) for path in result["artifact_paths"].values()])
    if action_id == "initialize_artifact_state":
        packet_manifest = _read_json_if_exists(roots["packet"] / "build_manifest.json") or {}
        selected, reused = _compose_authoritative_artifact_set(
            manager=manager,
            snapshot=snapshot,
            output_dir=output_dir,
            topic=topic,
            packet_dir=roots["packet"],
            packet_manifest=packet_manifest,
        )
        if not _selected_packet_inputs_are_current(selected, roots["packet"]):
            raise MissionStateError("artifact_state_stage_failed", "selected artifact set does not bind current packet")
        return {
            "schema_version": "ra-survey-artifact-state-stage-result-v1",
            "status": "selected",
            "artifact_set_id": selected.artifact_set_id,
            "reused_existing": reused,
            "required_output_paths": [str(selected.review_queue_path), str(selected.coverage_dir)],
        }
    if action_id in {"merge_reviewed_evidence", "repair_reviewed_evidence"}:
        target = preflight_mission_output(output_dir, output_dir / "reviewed_evidence", name="reviewed_evidence")
        queue_path = Path(observation["review_queue_path"])
        selected_paths = _selected_review_sidecar_paths(
            output_dir=output_dir,
            review_queue_path=queue_path,
        )
        result = merge_reviewed_evidence(
            review_queue_path=queue_path,
            reviewed_claims_path=selected_paths["claim_candidate"],
            reviewed_source_safety_path=selected_paths["source_safety"],
            reviewed_omissions_path=selected_paths["omission_risk"],
            reviewed_workflow_blockers_path=selected_paths["workflow_blocker"],
            output_dir=target,
            force=action_id == "repair_reviewed_evidence",
        )
        if result.get("status") not in {
            "reviewed_evidence_complete",
            "reviewed_evidence_blocked",
            "reviewed_evidence_blocked_unavailable_source_outcome",
        }:
            raise MissionStateError("reviewed_merge_stage_failed", "reviewed merge writer did not report a complete result")
        validate_reviewed_evidence_status(
            path=target / "reviewed_evidence_status.json",
            review_queue_path=queue_path,
            sidecar_paths=selected_paths,
        )
        required_outputs = [target / "reviewed_evidence_status.json"]
        if (target / "reviewed_source_outcome_blockers.json").is_file():
            required_outputs.extend([
                target / "reviewed_source_outcome_blockers.json",
                target / "reviewed_source_accounting.json",
            ])
        return _stage_result(result, required_outputs)
    if action_id in {"compose_reviewed_final_packet", "repair_reviewed_final_packet"}:
        target = preflight_mission_output(output_dir, output_dir / "reviewed_final_packet", name="reviewed_final_packet")
        result = compose_reviewed_final_packet(
            mission_root=output_dir,
            review_queue_path=Path(observation["review_queue_path"]),
            packet_dir=roots["packet"],
            anchor_dir=roots["anchor"],
            local_evidence_root=local_evidence_root,
            output_dir=target,
            force=action_id == "repair_reviewed_final_packet",
        )
        if result.get("status") != "reviewed_final_packet_ready_for_hostile_review":
            raise MissionStateError("reviewed_packet_stage_failed", "reviewed packet writer did not report success")
        validate_reviewed_final_packet(
            path=target / "reviewed_final_packet.json",
            mission_root=output_dir,
            review_queue_path=Path(observation["review_queue_path"]),
            packet_dir=roots["packet"],
            anchor_dir=roots["anchor"],
            local_evidence_root=local_evidence_root,
        )
        return _stage_result(result, [target / "reviewed_final_packet.json"])
    if action_id in {"run_hostile_review", "repair_hostile_review_result"}:
        target = preflight_mission_output(output_dir, output_dir / "hostile_review", name="hostile_review")
        result = run_hostile_review_gate(
            reviewed_final_packet_path=output_dir / "reviewed_final_packet" / "reviewed_final_packet.json",
            mission_root=output_dir,
            review_queue_path=Path(observation["review_queue_path"]),
            packet_dir=roots["packet"],
            anchor_dir=roots["anchor"],
            local_evidence_root=local_evidence_root,
            output_dir=target,
            force=action_id == "repair_hostile_review_result",
        )
        if result.get("status") not in {"ready_for_reviewed_prose_within_recorded_scope", "blocked_for_reviewed_prose"}:
            raise MissionStateError("hostile_review_stage_failed", "hostile review writer did not report an authoritative result")
        validate_hostile_review_result(
            path=target / "hostile_review_result.json",
            reviewed_final_packet_path=output_dir / "reviewed_final_packet" / "reviewed_final_packet.json",
            mission_root=output_dir,
            review_queue_path=Path(observation["review_queue_path"]),
            packet_dir=roots["packet"],
            anchor_dir=roots["anchor"],
            local_evidence_root=local_evidence_root,
        )
        return _stage_result(result, [target / "hostile_review_result.json"])
    if action_id == "refresh_final_packet_readiness":
        hostile_path = output_dir / "hostile_review" / "hostile_review_result.json"
        authoritative_before = hostile_path.read_bytes()
        try:
            result = refresh_final_packet_readiness(
                hostile_review_result_path=hostile_path,
                reviewed_final_packet_path=output_dir / "reviewed_final_packet" / "reviewed_final_packet.json",
                mission_root=output_dir,
                review_queue_path=Path(observation["review_queue_path"]),
                packet_dir=roots["packet"],
                anchor_dir=roots["anchor"],
                local_evidence_root=local_evidence_root,
            )
        except Exception as exc:
            if hostile_path.read_bytes() != authoritative_before:
                raise MissionStateError("hostile_authority_mutated", "readiness refresh changed authoritative hostile bytes") from exc
            return {
                "schema_version": "ra-survey-readiness-refresh-stage-result-v1",
                "status": "optional_readiness_refresh_failed",
                "exception_class": type(exc).__name__,
                "error_code": exc.code if isinstance(exc, MissionStateError) else "readiness_refresh_exception",
                "required_output_paths": [str(output_dir / "hostile_review" / "final_packet_readiness.json")],
            }
        if hostile_path.read_bytes() != authoritative_before:
            raise MissionStateError("hostile_authority_mutated", "readiness refresh changed authoritative hostile bytes")
        validate_final_packet_readiness(
            path=output_dir / "hostile_review" / "final_packet_readiness.json",
            hostile_review_result_path=hostile_path,
            reviewed_final_packet_path=output_dir / "reviewed_final_packet" / "reviewed_final_packet.json",
            mission_root=output_dir,
            review_queue_path=Path(observation["review_queue_path"]),
            packet_dir=roots["packet"],
            anchor_dir=roots["anchor"],
            local_evidence_root=local_evidence_root,
        )
        return {
            "schema_version": "ra-survey-readiness-refresh-stage-result-v1",
            "status": "refreshed",
            "required_output_paths": [str(output_dir / "hostile_review" / "final_packet_readiness.json")],
            "readiness_classification": result.get("readiness_classification"),
        }
    raise MissionStateError("unknown_supervisor_action", f"action is not dispatchable: {action_id}")


def _stage_result(result: dict[str, Any], paths: list[Path]) -> dict[str, Any]:
    return {
        "schema_version": result.get("schema_version"),
        "status": result.get("status"),
        "required_output_paths": [str(path) for path in paths],
    }


def _validate_stage_result_outputs(stage_result: dict[str, Any], *, output_dir: Path) -> None:
    if stage_result.get("status") == "optional_readiness_refresh_failed":
        return
    paths = stage_result.get("required_output_paths")
    if not isinstance(paths, list) or not paths or any(not isinstance(value, str) or not value for value in paths):
        raise MissionStateError(
            "missing_supervisor_stage_outputs",
            "typed stage did not declare its required output paths",
        )
    mission_root = output_dir.absolute()
    for value in paths:
        path = Path(value)
        if not path.is_absolute():
            raise MissionStateError("invalid_supervisor_stage_output", "typed stage output path is not absolute")
        try:
            path.absolute().relative_to(mission_root)
        except ValueError as exc:
            raise MissionStateError("outside_supervisor_stage_output", "typed stage output is outside the mission root") from exc
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise MissionStateError(
                "missing_supervisor_stage_output",
                "typed stage reported success without a required regular output",
            )


def _finish_supervisor(
    *,
    manager: MissionStateManager,
    observation: dict[str, Any],
    history: list[dict[str, Any]],
    terminal_status: str,
    terminal_action_id: str,
    terminal_reason: str,
) -> dict[str, Any]:
    mission_payload = observation.pop("_mission_control_payload", None)
    next_payload = observation.pop("_next_action_payload", None)
    if mission_payload is None or next_payload is None:
        fallback = _observation_from_snapshot(manager, Path(observation["output_dir"]), code=terminal_reason)
        mission_payload = fallback.pop("_mission_control_payload")
        next_payload = fallback.pop("_next_action_payload")
        observation = fallback
    hostile = observation.get("final_artifacts", {}).get("hostile_review_result", {})
    ready = terminal_status == "terminal_ready_for_reviewed_prose_within_recorded_scope"
    supervisor = {
        "schema_version": LOCAL_SUPERVISOR_SCHEMA_VERSION,
        "status": terminal_status,
        "transition_count": len(history),
        "max_transitions": MAX_LOCAL_TRANSITIONS,
        "observation_sha256": observation_sha256(observation),
        "transition_history": history,
        "terminal_action_id": terminal_action_id,
        "terminal_reason": terminal_reason,
        "ready_for_prose": ready,
        "readiness_classification": (
            hostile.get("readiness_classification") if ready or terminal_status == "terminal_blocked_hostile_review" else None
        ),
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }
    next_payload = {
        **next_payload,
        "action_id": terminal_action_id,
        "status": terminal_status,
        "mission_status": "ready_for_local_continuation" if ready else "blocked_at_gate",
        "summary": terminal_reason,
        "safe_next_commands": [] if terminal_action_id.startswith("terminal_") else next_payload.get("safe_next_commands", []),
        "ready_for_prose": ready,
        "readiness_classification": supervisor["readiness_classification"],
    }
    mission_payload = {
        **mission_payload,
        "status": next_payload["mission_status"],
        "next_action": next_payload,
        "safe_next_commands": next_payload["safe_next_commands"],
        "local_supervisor": supervisor,
    }
    for transition in history:
        if transition.get("stage_id") != "build_offline_skeleton":
            continue
        for action in mission_payload.get("actions") or []:
            if action.get("action") == "survey_build_offline_skeleton":
                action["status"] = transition.get("stage_result", {}).get("status")
    committed = manager.commit(mission_payload, next_payload)
    public = dict(observation)
    public.update({
        "status": (committed.mission_control or mission_payload)["status"],
        "mission_id": committed.contract["mission_id"],
        "mission_fingerprint": committed.contract["mission_fingerprint"],
        "generation_id": committed.current_pointer["generation_id"] if committed.current_pointer else None,
        "next_action": committed.next_action or next_payload,
        "safe_next_commands": (committed.next_action or next_payload).get("safe_next_commands", []),
        "local_supervisor": supervisor,
    })
    return public


def _observation_from_snapshot(manager: MissionStateManager, output_dir: Path, *, code: str) -> dict[str, Any]:
    snapshot = manager.snapshot
    assert snapshot is not None
    mission = dict(snapshot.mission_control or {
        "status": "blocked_at_gate",
        "created_at": snapshot.contract["created_at"],
        "updated_at": _utc_now_iso(),
        "topic": snapshot.contract["normalized_topic"]["display"],
        "seeds": [row["display"] for row in snapshot.contract["normalized_seeds"]],
        "output_dir": str(output_dir),
        "phase_statuses": {},
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "public_discovery_confirmation": _public_discovery_confirmation(
            output_dir=output_dir,
            confirmation=snapshot.contract["public_discovery_confirmation"],
        ),
        "actions": [],
        "next_gate": {"gate_id": "invalid_artifact", "status": code},
        "workflow_state": None,
        "artifact_state": None,
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "safe_next_commands": [],
        "forbidden_actions": [],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    })
    next_action = dict(snapshot.next_action or {
        "schema_version": SURVEY_NEXT_ACTION_SCHEMA_VERSION,
        "created_at": _utc_now_iso(),
        "gate_id": "invalid_artifact",
        "approval_required": False,
        "safe_next_commands": [],
        "blockers": [code],
        "required_artifacts": [],
        "public_discovery_confirmation": mission["public_discovery_confirmation"],
        "forbidden_actions": [],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    })
    observation = {
        "schema_version": SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION,
        "status": mission.get("status", "blocked_at_gate"),
        "topic": mission.get("topic"),
        "seed_count": len(mission.get("seeds") or []),
        "output_dir": str(output_dir),
        "mission_control_path": str(output_dir / "mission_control.json"),
        "next_action_path": str(output_dir / "next_action.json"),
        "mission_id": snapshot.contract["mission_id"],
        "mission_fingerprint": snapshot.contract["mission_fingerprint"],
        "generation_id": snapshot.current_pointer.get("generation_id") if snapshot.current_pointer else None,
        "artifact_paths": {},
        "next_gate": mission.get("next_gate", {}),
        "next_action": next_action,
        "public_discovery_confirmation": mission.get("public_discovery_confirmation", {}),
        "review_queue_path": mission.get("review_queue_path"),
        "review_queue_counts": mission.get("review_queue_counts"),
        "review_queue_reused": mission.get("review_queue_reused"),
        "artifact_state": mission.get("artifact_state"),
        "phase_statuses": mission.get("phase_statuses", {}),
        "reviewed_artifacts": mission.get("reviewed_artifacts", {}),
        "coverage_artifacts": mission.get("coverage_artifacts", {}),
        "final_artifacts": mission.get("final_artifacts", {}),
        "safe_next_commands": mission.get("safe_next_commands", []),
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
        "_mission_control_payload": mission,
        "_next_action_payload": next_action,
    }
    return observation


def _phase_status(path: Path | None, required_file: str) -> dict[str, Any]:
    if path is None:
        return {
            "exists": False,
            "path": None,
            "required_file": required_file,
            "reason": "not_provided",
        }
    return _artifact_status(path.resolve(), required_file)


def _metadata_required_file(path: Path, *, canonical_root: Path) -> str:
    if path == canonical_root:
        return "build_manifest.json"
    if any(
        (path / name).exists() or (path / name).is_symlink()
        for name in ("identity_resolution.json", "relevance_ranking.json")
    ):
        return "build_manifest.json"
    return "candidate_ledger.json"


def _artifact_status(path: Path, required_file: str) -> dict[str, Any]:
    required_path = path / required_file
    return {
        "exists": required_path.exists(),
        "path": str(path),
        "required_file": required_file,
        "required_path": str(required_path),
    }


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _public_discovery_confirmation(*, output_dir: Path, confirmation: dict[str, Any]) -> dict[str, Any]:
    confirmed = confirmation["confirmed"]
    return {
        "schema_version": SURVEY_PUBLIC_DISCOVERY_CONFIRMATION_SCHEMA_VERSION,
        "confirmed": confirmed,
        "status": "confirmed" if confirmed else "confirmation_required",
        "confirmed_at": confirmation["confirmed_at"],
        "confirmation_source": confirmation["confirmation_source"],
        "question": "Do you want RA to search public web/archive sources for this idea or paper?",
        "scope": {
            "allowed_actions": [
                "local_cache_lookup",
                "bounded_public_web_api_metadata",
                "public_archive_search",
                "public_source_status_lookup",
                "capped_public_source_pdf_full_text_retrieval",
            ],
            "providers": PUBLIC_DISCOVERY_DEFAULT_PROVIDERS,
            "allowed_domains": PUBLIC_DISCOVERY_ALLOWED_DOMAINS,
            "caps": {
                "max_metadata_records": PUBLIC_DISCOVERY_MAX_METADATA_RECORDS,
                "write_root": str(output_dir),
            },
            "output_dir": str(output_dir),
            "raw_response_policy": "save normalized metadata only unless a later bounded source artifact explicitly permits more",
        },
        "forbidden_actions": [
            "credentials",
            "private_databases",
            "paid_model_worker_trials",
            "hidden_evaluator_material",
            "unbounded_crawling",
            "writes_outside_mission_output",
            "technical_claim_support_from_metadata_or_source_availability",
            "final_prose_readiness_from_discovery_alone",
        ],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }


def _next_gate(
    phase_statuses: dict[str, dict[str, Any]],
    *,
    public_discovery_confirmed: bool = False,
) -> dict[str, Any]:
    if not phase_statuses["public_metadata"]["exists"]:
        return {
            "gate_id": "public_metadata",
            "status": "public_discovery_confirmation_or_existing_artifact_required",
            "approval_required": True,
            "approval_scope": "single mission public-discovery confirmation; no credentials, private databases, paid model workers, hidden evaluator material, unbounded crawling, or claim support",
            "required_artifact": "build_manifest.json",
        }
    if phase_statuses["public_metadata"].get("resolution_blocked") is True:
        return {
            "gate_id": "public_metadata_resolution",
            "status": "blocked_seed_resolution",
            "approval_required": False,
            "implementation_or_artifact_blocker": True,
            "approval_scope": "inspect the committed identity-resolution choices; no source capability may run",
            "required_artifact": "identity_resolution.json",
        }
    if not phase_statuses["source_intake"]["exists"]:
        if public_discovery_confirmed:
            return {
                "gate_id": "source_intake",
                "status": "blocked_missing_public_source_intake_artifact",
                "approval_required": False,
                "covered_by_public_discovery": True,
                "implementation_or_artifact_blocker": True,
                "approval_scope": "covered by the mission public-discovery confirmation; concrete source/status artifact is still required",
                "required_artifact": "phase4_source_intake_status.json",
            }
        return {
            "gate_id": "source_intake",
            "status": "approval_or_existing_artifact_required",
            "approval_required": True,
            "covered_by_public_discovery": False,
            "implementation_or_artifact_blocker": False,
            "approval_scope": "exact candidate source_fetch only; no PDF, credentials, broad web search, or changed candidate set",
            "required_artifact": "phase4_source_intake_status.json",
        }
    if not phase_statuses["source_anchors"]["exists"]:
        return {
            "gate_id": "source_anchors",
            "status": "local_artifact_required",
            "approval_required": False,
            "approval_scope": "local structured source records only",
            "required_artifact": "source_anchor_inventory.json",
        }
    if not phase_statuses["public_source_packet"]["exists"]:
        return {
            "gate_id": "public_source_packet",
            "status": "local_artifact_required",
            "approval_required": False,
            "approval_scope": "local ledger composition only",
            "required_artifact": "build_manifest.json",
        }
    return {
        "gate_id": "claim_safety_omission_review",
        "status": "review_required",
        "approval_required": True,
        "approval_scope": "claim review, source safety checks, and omission-risk resolution remain explicit gates",
        "required_artifact": "ready_for_prose.json",
    }


def _reviewed_artifact_statuses(
    *,
    output_dir: Path,
    reviewed_claims_dir: Path | None,
    reviewed_source_safety_dir: Path | None,
    reviewed_omissions_dir: Path | None,
    reviewed_workflow_blockers_dir: Path | None,
    reviewed_evidence_dir: Path | None,
    review_queue_path: Path | None,
) -> dict[str, dict[str, Any]]:
    required_paths = {
        "claim_candidate": output_dir / "reviewed_claims" / "reviewed_claims.json",
        "source_safety": output_dir / "reviewed_source_safety" / "reviewed_source_safety.json",
        "omission_risk": output_dir / "reviewed_omissions" / "reviewed_omission_risks.json",
        "workflow_blocker": output_dir / "reviewed_workflow_blockers" / "reviewed_workflow_blockers.json",
    }
    provided_dirs = {
        "claim_candidate": reviewed_claims_dir,
        "source_safety": reviewed_source_safety_dir,
        "omission_risk": reviewed_omissions_dir,
        "workflow_blocker": reviewed_workflow_blockers_dir,
    }
    selection_errors: dict[str, MissionStateError] = {}
    v2_authority = False
    if review_queue_path is not None:
        try:
            load_v2_evidence_context(review_queue_path)
        except MissionStateError as exc:
            if exc.code != "legacy_evidence_authority":
                selection_errors = {
                    decision_type: exc
                    for decision_type in ("claim_candidate", "source_safety", "omission_risk")
                }
        else:
            v2_authority = True
        if not selection_errors:
            selected, selection_errors = _resolve_selected_review_sidecar_paths(
                output_dir=output_dir,
                review_queue_path=review_queue_path,
                v2_authority=v2_authority,
            )
            required_paths.update(selected)
        if v2_authority:
            for decision_type in ("claim_candidate", "source_safety", "omission_risk"):
                provided_dirs[decision_type] = None
    statuses = {
        "reviewed_claims": _reviewed_artifact_status(
            provided_dirs["claim_candidate"],
            required_paths["claim_candidate"].parent,
            required_paths["claim_candidate"].name,
            review_queue_path,
            decision_type="claim_candidate",
        ),
        "reviewed_source_safety": _reviewed_artifact_status(
            provided_dirs["source_safety"],
            required_paths["source_safety"].parent,
            required_paths["source_safety"].name,
            review_queue_path,
            decision_type="source_safety",
        ),
        "reviewed_omissions": _reviewed_artifact_status(
            provided_dirs["omission_risk"],
            required_paths["omission_risk"].parent,
            required_paths["omission_risk"].name,
            review_queue_path,
            decision_type="omission_risk",
        ),
        "reviewed_workflow_blockers": _reviewed_artifact_status(
            provided_dirs["workflow_blocker"],
            required_paths["workflow_blocker"].parent,
            required_paths["workflow_blocker"].name,
            review_queue_path,
            decision_type="workflow_blocker",
        ),
        "reviewed_evidence": _reviewed_artifact_status(
            reviewed_evidence_dir,
            output_dir / "reviewed_evidence",
            "reviewed_evidence_status.json",
            review_queue_path,
            strict_merge=True,
        ),
    }
    status_key_by_decision_type = {
        "claim_candidate": "reviewed_claims",
        "source_safety": "reviewed_source_safety",
        "omission_risk": "reviewed_omissions",
    }
    for decision_type, selection_error in selection_errors.items():
        key = status_key_by_decision_type[decision_type]
        reimportable_lineage = (
            v2_authority
            and selection_error.code in {"stale_lineage", "foreign_lineage"}
        )
        statuses[key].update({
            "exists": False,
            "authority_invalid": not reimportable_lineage,
            "payload_status": "invalid_or_stale_review_selector",
            "lineage_status": selection_error.code,
            "ready_for_reviewed_packet": False,
            "ready_for_prose": False,
            "blockers": [str(selection_error)],
        })
    merged = statuses["reviewed_evidence"]
    if merged.get("exists") is True and review_queue_path is not None:
        sidecar_paths = {
            "claim_candidate": Path(statuses["reviewed_claims"]["required_path"]),
            "source_safety": Path(statuses["reviewed_source_safety"]["required_path"]),
            "omission_risk": Path(statuses["reviewed_omissions"]["required_path"]),
            "workflow_blocker": Path(statuses["reviewed_workflow_blockers"]["required_path"]),
        }
        try:
            payload = validate_reviewed_evidence_status(
                path=Path(merged["required_path"]),
                review_queue_path=review_queue_path,
                sidecar_paths=sidecar_paths,
            )
        except MissionStateError as exc:
            merged.update({
                "exists": False,
                "payload_status": "invalid_or_stale_reviewed_evidence",
                "lineage_status": exc.code,
                "ready_for_reviewed_packet": False,
                "ready_for_prose": False,
                "blockers": [str(exc)],
            })
        else:
            _update_reviewed_status_from_payload(merged, payload)
            merged["lineage_status"] = "current_lineage"
    return statuses


def _coverage_artifact_statuses(
    *,
    output_dir: Path,
    coverage_dir: Path | None,
) -> dict[str, dict[str, Any]]:
    base_dir = (coverage_dir or output_dir / "coverage_ledgers").resolve()
    return {
        "coverage_manifest": _artifact_status(base_dir, "coverage_manifest.json"),
        "backward_snowball": _artifact_status(base_dir, "backward_snowball.json"),
        "forward_snowball": _artifact_status(base_dir, "forward_snowball.json"),
        "citation_venue_metadata": _artifact_status(base_dir, "citation_venue_metadata.json"),
        "paper_classifications": _artifact_status(base_dir, "paper_classifications.json"),
        "omitted_paper_risks": _artifact_status(base_dir, "omitted_paper_risks.json"),
    }


def _final_artifact_statuses(
    *,
    output_dir: Path,
    review_queue_path: Path | None,
    packet_dir: Path,
    anchor_dir: Path | None,
    local_evidence_root: Path | None,
) -> dict[str, dict[str, Any]]:
    packet_path = output_dir / "reviewed_final_packet" / "reviewed_final_packet.json"
    hostile_path = output_dir / "hostile_review" / "hostile_review_result.json"
    readiness_path = output_dir / "hostile_review" / "final_packet_readiness.json"
    statuses = {
        "reviewed_final_packet": _final_artifact_base(packet_path),
        "hostile_review_result": _final_artifact_base(hostile_path),
        "final_packet_readiness": _final_artifact_base(readiness_path),
    }
    if review_queue_path is None or anchor_dir is None:
        return statuses

    packet_status = statuses["reviewed_final_packet"]
    if packet_status["present"]:
        try:
            packet = validate_reviewed_final_packet(
                path=packet_path,
                mission_root=output_dir,
                review_queue_path=review_queue_path,
                packet_dir=packet_dir,
                anchor_dir=anchor_dir,
                local_evidence_root=local_evidence_root,
            )
        except MissionStateError as exc:
            _mark_final_invalid(packet_status, exc)
        else:
            packet_status.update({
                "exists": True,
                "payload_status": packet["status"],
                "lineage_status": "current_lineage",
                "ready_for_hostile_review": packet["readiness_inputs"]["ready_for_hostile_review"],
                "ready_for_prose": False,
            })

    hostile_status = statuses["hostile_review_result"]
    if hostile_status["present"]:
        if not packet_status["exists"]:
            hostile_status.update({
                "exists": False,
                "lineage_status": "invalid_or_missing_reviewed_final_packet",
                "blockers": ["authoritative hostile result cannot replay without a current reviewed final packet"],
                "ready_for_prose": False,
            })
        else:
            try:
                hostile = validate_hostile_review_result(
                    path=hostile_path,
                    reviewed_final_packet_path=packet_path,
                    mission_root=output_dir,
                    review_queue_path=review_queue_path,
                    packet_dir=packet_dir,
                    anchor_dir=anchor_dir,
                    local_evidence_root=local_evidence_root,
                )
            except MissionStateError as exc:
                _mark_final_invalid(hostile_status, exc)
            else:
                hostile_status.update({
                    "exists": True,
                    "payload_status": hostile["status"],
                    "lineage_status": "current_lineage",
                    "ready_for_hostile_review": True,
                    "ready_for_prose": hostile["ready_for_prose"],
                    "readiness_classification": hostile["readiness_classification"],
                    "blockers": list(hostile["blockers"]),
                    "warnings": list(hostile["warnings"]),
                })

    readiness_status = statuses["final_packet_readiness"]
    if readiness_status["present"]:
        if not hostile_status["exists"]:
            readiness_status.update({
                "exists": False,
                "lineage_status": "invalid_or_missing_hostile_review_result",
                "blockers": ["readiness view is nonauthoritative and lacks a current hostile result"],
                "ready_for_prose": False,
            })
        else:
            try:
                readiness = validate_final_packet_readiness(
                    path=readiness_path,
                    hostile_review_result_path=hostile_path,
                    reviewed_final_packet_path=packet_path,
                    mission_root=output_dir,
                    review_queue_path=review_queue_path,
                    packet_dir=packet_dir,
                    anchor_dir=anchor_dir,
                    local_evidence_root=local_evidence_root,
                )
            except MissionStateError as exc:
                _mark_final_invalid(readiness_status, exc)
                readiness_status["regenerable_view"] = True
            else:
                readiness_status.update({
                    "exists": True,
                    "payload_status": readiness["status"],
                    "lineage_status": "current_lineage",
                    "ready_for_hostile_review": readiness["ready_for_hostile_review"],
                    "ready_for_prose": readiness["ready_for_prose"],
                    "regenerable_view": True,
                })
    elif hostile_status["exists"]:
        readiness_status["regenerable_view"] = True
    return statuses


def _final_artifact_base(path: Path) -> dict[str, Any]:
    present = path.exists() or path.is_symlink()
    return {
        "exists": False,
        "present": present,
        "path": str(path.parent),
        "required_file": path.name,
        "required_path": str(path),
        "discovery": "default_mission_subdir",
        "ready_for_hostile_review": False,
        "ready_for_prose": False,
        "blockers": [],
    }


def _mark_final_invalid(status: dict[str, Any], error: MissionStateError) -> None:
    status.update({
        "exists": False,
        "payload_status": "invalid_or_stale",
        "lineage_status": error.code,
        "ready_for_hostile_review": False,
        "ready_for_prose": False,
        "blockers": [str(error)],
    })


def _reviewed_artifact_status(
    provided_dir: Path | None,
    default_dir: Path,
    required_file: str,
    review_queue_path: Path | None,
    decision_type: str | None = None,
    strict_merge: bool = False,
) -> dict[str, Any]:
    artifact_dir = (provided_dir or default_dir).absolute()
    required_path = artifact_dir / required_file
    status: dict[str, Any] = {
        "exists": required_path.exists() or required_path.is_symlink(),
        "path": str(artifact_dir),
        "required_file": required_file,
        "required_path": str(required_path),
        "discovery": "provided" if provided_dir else "default_mission_subdir",
    }
    if status["exists"] and decision_type is not None and review_queue_path is not None:
        try:
            payload = validate_current_reviewed_sidecar(
                review_queue_path=review_queue_path,
                decision_type=decision_type,
                sidecar_path=required_path,
            )
        except MissionStateError as exc:
            status.update({
                "exists": False,
                "payload_status": "invalid_or_stale_review_sidecar",
                "lineage_status": exc.code,
                "ready_for_reviewed_packet": False,
                "ready_for_prose": False,
                "blockers": [str(exc)],
            })
        else:
            _update_reviewed_status_from_payload(status, payload)
            status["lineage_status"] = "current_lineage"
    elif status["exists"] and not strict_merge:
        payload = _read_json_if_exists(required_path)
        if payload is None:
            status.update({
                "exists": False,
                "payload_status": "invalid_json",
                "ready_for_reviewed_packet": False,
                "ready_for_prose": False,
                "blockers": ["artifact exists but is not valid JSON"],
            })
        else:
            _update_reviewed_status_from_payload(status, payload)
            if review_queue_path is not None:
                actual = payload.get("review_queue_sha256")
                status["lineage_status"] = classify_review_queue_digest(review_queue_path, actual)
                if status["lineage_status"] != "current_lineage":
                    status["exists"] = False
                    status["ready_for_reviewed_packet"] = False
                    status["ready_for_prose"] = False
                    status["blockers"] = [
                        *status.get("blockers", []),
                        f"{required_file} is {status['lineage_status']} for the selected review queue",
                    ]
    elif status["exists"] and strict_merge:
        status.update({
            "payload_status": "pending_strict_reviewed_evidence_validation",
            "ready_for_reviewed_packet": False,
            "ready_for_prose": False,
            "blockers": [],
        })
    return status


def _selected_review_sidecar_paths(
    *,
    output_dir: Path,
    review_queue_path: Path,
) -> dict[str, Path]:
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        if exc.code != "legacy_evidence_authority":
            raise
        v2_authority = False
    else:
        v2_authority = True
    paths, errors = _resolve_selected_review_sidecar_paths(
        output_dir=output_dir,
        review_queue_path=review_queue_path,
        v2_authority=v2_authority,
    )
    for decision_type in ("claim_candidate", "source_safety", "omission_risk"):
        if decision_type in errors:
            raise errors[decision_type]
    return paths


def _resolve_selected_review_sidecar_paths(
    *,
    output_dir: Path,
    review_queue_path: Path,
    v2_authority: bool,
) -> tuple[dict[str, Path], dict[str, MissionStateError]]:
    paths = {
        "claim_candidate": output_dir / "reviewed_claims" / "reviewed_claims.json",
        "source_safety": output_dir / "reviewed_source_safety" / "reviewed_source_safety.json",
        "omission_risk": output_dir / "reviewed_omissions" / "reviewed_omission_risks.json",
        "workflow_blocker": output_dir / "reviewed_workflow_blockers" / "reviewed_workflow_blockers.json",
    }
    errors: dict[str, MissionStateError] = {}
    if v2_authority:
        claim_root = output_dir / "reviewed_claims"
        if claim_root.exists() or claim_root.is_symlink():
            try:
                claim, _ = resolve_current_reviewed_claims(
                    review_queue_path=review_queue_path,
                    reviewed_claims_root=claim_root,
                )
            except MissionStateError as exc:
                errors["claim_candidate"] = exc
            else:
                paths["claim_candidate"] = claim.artifact_paths["reviewed_claims.json"]

        source_root = output_dir / "reviewed_source_safety"
        if source_root.exists() or source_root.is_symlink():
            try:
                _, source, _ = resolve_current_source_safety(
                    review_queue_path=review_queue_path,
                    reviewed_source_safety_root=source_root,
                )
            except MissionStateError as exc:
                errors["source_safety"] = exc
            else:
                paths["source_safety"] = source.artifact_paths["reviewed_source_safety.json"]

        omission_root = output_dir / "reviewed_omissions"
        if omission_root.exists() or omission_root.is_symlink():
            try:
                selected_omissions = resolve_current_reviewed_omissions(
                    review_queue_path=review_queue_path,
                    reviewed_omissions_root=omission_root,
                )
            except MissionStateError as exc:
                errors["omission_risk"] = exc
            else:
                paths["omission_risk"] = (
                    selected_omissions.sidecar_path
                    if isinstance(selected_omissions, OmissionDecisionSetSnapshot)
                    else selected_omissions
                )
    else:
        selected_omissions = resolve_current_reviewed_omissions(
            review_queue_path=review_queue_path,
            reviewed_omissions_root=output_dir / "reviewed_omissions",
        )
        paths["omission_risk"] = (
            selected_omissions.sidecar_path
            if isinstance(selected_omissions, OmissionDecisionSetSnapshot)
            else selected_omissions
        )
    return paths, errors


def _classify_reviewed_evidence_shape(path: Path) -> str:
    payload = _read_json_if_exists(path)
    if payload is None:
        return classify_repairable_json(
            path,
            expected_schema=SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
            expected_keys=REVIEWED_EVIDENCE_KEYS,
        )
    if payload.get("schema_version") == SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION:
        return classify_repairable_json(
            path,
            expected_schema=SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION,
            expected_keys=REVIEWED_EVIDENCE_V3_KEYS,
        )
    return classify_repairable_json(
        path,
        expected_schema=SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
        expected_keys=REVIEWED_EVIDENCE_KEYS,
    )


def _classify_reviewed_packet_shape(path: Path) -> str:
    payload = _read_json_if_exists(path)
    if payload is not None and payload.get("schema_version") == SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION:
        return classify_repairable_json(
            path,
            expected_schema=SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION,
            expected_keys=REVIEWED_FINAL_PACKET_V2_KEYS,
        )
    return classify_repairable_json(
        path,
        expected_schema=SURVEY_REVIEWED_FINAL_PACKET_SCHEMA_VERSION,
        expected_keys=REVIEWED_FINAL_PACKET_KEYS,
    )


def _update_reviewed_status_from_payload(status: dict[str, Any], payload: dict[str, Any]) -> None:
    status.update({
        "schema_version": payload.get("schema_version"),
        "payload_status": payload.get("status"),
        "ready_for_prose": payload.get("ready_for_prose"),
        "ready_for_reviewed_packet": payload.get("ready_for_reviewed_packet"),
        "decision_coverage_complete": payload.get("decision_coverage_complete"),
        "review_queue_sha256": payload.get("review_queue_sha256"),
        "counts": payload.get("counts"),
        "blockers": list(payload.get("blockers") or []),
        "next_required_actions": list(payload.get("next_required_actions") or []),
    })
    for field in [
        "accepted_claim_count",
        "accepted_source_safety_count",
        "accepted_omission_count",
        "accepted_workflow_blocker_count",
        "open_omission_count",
        "rejected_claim_count",
        "rejected_source_safety_count",
        "rejected_omission_count",
        "rejected_workflow_blocker_count",
        "open_workflow_blocker_count",
    ]:
        if field in payload:
            status[field] = payload[field]


def _next_action(
    *,
    gate: dict[str, Any],
    output_dir: Path,
    topic: str,
    seeds: list[str],
    packet_dir: Path,
    review_queue: dict[str, Any] | None,
    reviewed_artifacts: dict[str, dict[str, Any]],
    coverage_artifacts: dict[str, dict[str, Any]],
    final_artifacts: dict[str, dict[str, Any]],
    anchor_dir: Path | None,
    local_evidence_root: Path | None,
    public_discovery_confirmation: dict[str, Any],
    artifact_initialization_required: bool = False,
) -> dict[str, Any]:
    created_at = _utc_now_iso()
    base = {
        "schema_version": SURVEY_NEXT_ACTION_SCHEMA_VERSION,
        "created_at": created_at,
        "gate_id": gate["gate_id"],
        "approval_required": bool(gate.get("approval_required")),
        "safe_next_commands": _safe_next_commands(gate, output_dir, topic, seeds),
        "blockers": [],
        "required_artifacts": [],
        "public_discovery_confirmation": public_discovery_confirmation,
        "forbidden_actions": [
            "do not run live/API/source/PDF/download/credential actions implicitly",
            "do not run public discovery before public_discovery_confirmation.confirmed is true",
            "do not treat reviewed sidecar discovery as final prose readiness",
            "do not hide reviewed-evidence blockers",
            "do not use credentials, private databases, paid model workers, hidden evaluator material, unbounded crawling, or outputs outside the mission directory without separate explicit approval",
        ],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }
    if gate["gate_id"] != "claim_safety_omission_review":
        return {
            **base,
            "action_id": gate["gate_id"],
            "status": gate["status"],
            "mission_status": (
                "blocked_at_gate"
                if gate["approval_required"] or gate.get("implementation_or_artifact_blocker")
                else "ready_for_local_continuation"
            ),
            "summary": _gate_summary(gate),
            "required_artifacts": [gate["required_artifact"]],
        }

    if artifact_initialization_required:
        return {
            **base,
            "action_id": "resume_to_initialize_artifact_state",
            "status": "ready_to_initialize_artifact_state",
            "mission_status": "ready_for_local_continuation",
            "summary": "Resume this committed mission to compose coverage before the unified review queue and atomically select the immutable artifact set.",
            "safe_next_commands": [
                "rerun run-public-source-workflow with the same mission identity and --resume; no live/API/source/PDF action is required"
            ],
            "required_artifacts": [".artifact_state/GENESIS", ".artifact_state/CURRENT"],
        }

    if not review_queue:
        return {
            **base,
            "action_id": "create_review_queue",
            "status": "blocked_missing_review_queue",
            "mission_status": "blocked_at_gate",
            "summary": "Create review_queue.json from the public-source packet before importing reviewed sidecars.",
            "required_artifacts": ["review_queue.json"],
        }

    review_queue_path = review_queue["path"]
    claims = reviewed_artifacts["reviewed_claims"]
    source_safety = reviewed_artifacts["reviewed_source_safety"]
    omissions = reviewed_artifacts["reviewed_omissions"]
    workflow_blockers = reviewed_artifacts["reviewed_workflow_blockers"]
    merged = reviewed_artifacts["reviewed_evidence"]
    coverage_complete = all(status.get("exists") is True for status in coverage_artifacts.values())

    if not coverage_complete:
        return {
            **base,
            "action_id": "repair_authoritative_coverage",
            "status": "blocked_missing_authoritative_coverage",
            "mission_status": "blocked_at_gate",
            "summary": "The selected immutable artifact set does not expose a complete validated coverage directory.",
            "required_artifacts": [status["required_path"] for status in coverage_artifacts.values()],
        }

    invalid_authorities = [
        {
            "family": family,
            "code": status.get("lineage_status"),
            "required_path": status["required_path"],
            "blockers": list(status.get("blockers") or []),
        }
        for family, status in (
            ("claim_candidate", claims),
            ("source_safety", source_safety),
            ("omission_risk", omissions),
        )
        if status.get("authority_invalid") is True
    ]
    if invalid_authorities:
        return {
            **base,
            "action_id": "invalid_reviewed_authority",
            "status": "blocked_invalid_reviewed_authority",
            "mission_status": "blocked_at_gate",
            "summary": "A selected immutable reviewed authority is missing, corrupt, stale, or otherwise invalid.",
            "safe_next_commands": [],
            "blockers": [
                blocker
                for authority in invalid_authorities
                for blocker in authority["blockers"]
            ],
            "required_artifacts": [authority["required_path"] for authority in invalid_authorities],
            "invalid_authorities": invalid_authorities,
        }

    if not claims["exists"] or claims.get("decision_coverage_complete") is not True:
        command = (
            "review claim_candidates, then run: "
            "ra survey import-claim-review "
            f"--review-queue {review_queue_path} "
            "--decisions <reviewed_claim_decisions.json> "
            f"--out {output_dir / 'reviewed_claims'}"
        )
        return {
            **base,
            "action_id": "import_reviewed_claims",
            "status": "blocked_pending_reviewed_claims",
            "mission_status": "blocked_at_gate",
            "summary": "Import reviewed claim decisions linked to claim_candidate queue items.",
            "safe_next_commands": [command],
            "required_artifacts": [claims["required_path"]],
        }
    if not source_safety["exists"] or source_safety.get("decision_coverage_complete") is not True:
        command = (
            "ra survey import-source-safety-review "
            f"--review-queue {review_queue_path} "
            "--decisions <reviewed_source_safety_decisions.json> "
            f"--out {output_dir / 'reviewed_source_safety'}"
        )
        return {
            **base,
            "action_id": "import_reviewed_source_safety",
            "status": "blocked_pending_reviewed_source_safety",
            "mission_status": "blocked_at_gate",
            "summary": "Import reviewed source-safety decisions; source availability alone is not safety evidence.",
            "safe_next_commands": [command],
            "required_artifacts": [source_safety["required_path"]],
        }
    if not omissions["exists"] or omissions.get("decision_coverage_complete") is not True:
        command = (
            "ra survey import-omission-review "
            f"--review-queue {review_queue_path} "
            "--decisions <reviewed_omission_decisions.json> "
            f"--out {output_dir / 'reviewed_omissions'}"
        )
        return {
            **base,
            "action_id": "import_reviewed_omissions",
            "status": "blocked_pending_reviewed_omissions",
            "mission_status": "blocked_at_gate",
            "summary": "Import reviewed omission-risk decisions without claiming literature completeness.",
            "safe_next_commands": [command],
            "required_artifacts": [omissions["required_path"]],
        }
    if not workflow_blockers["exists"] or workflow_blockers.get("decision_coverage_complete") is not True:
        command = (
            "ra survey import-workflow-blocker-review "
            f"--review-queue {review_queue_path} "
            "--decisions <reviewed_workflow_blocker_decisions.json> "
            f"--out {output_dir / 'reviewed_workflow_blockers'}"
        )
        return {
            **base,
            "action_id": "import_reviewed_workflow_blockers",
            "status": "blocked_pending_reviewed_workflow_blockers",
            "mission_status": "blocked_at_gate",
            "summary": "Import one exact disposition for every workflow blocker; upstream-only blockers must remain open.",
            "safe_next_commands": [command],
            "required_artifacts": [workflow_blockers["required_path"]],
        }
    if not merged["exists"]:
        command = (
            "ra survey merge-reviewed-evidence "
            f"--review-queue {review_queue_path} "
            f"--reviewed-claims {claims['required_path']} "
            f"--reviewed-source-safety {source_safety['required_path']} "
            f"--reviewed-omissions {omissions['required_path']} "
            f"--reviewed-workflow-blockers {workflow_blockers['required_path']} "
            f"--out {output_dir / 'reviewed_evidence'}"
        )
        return {
            **base,
            "action_id": "merge_reviewed_evidence",
            "status": "blocked_pending_reviewed_evidence_merge",
            "mission_status": "blocked_at_gate",
            "summary": "Merge reviewed sidecars and preserve blockers before any readiness decision.",
            "safe_next_commands": [command],
            "required_artifacts": [merged["required_path"]],
        }

    blockers = list(merged.get("blockers") or [])
    if merged.get("ready_for_reviewed_packet") is not True or blockers:
        return {
            **base,
            "action_id": "resolve_reviewed_evidence_blockers",
            "status": "blocked_by_reviewed_evidence_merge",
            "mission_status": "blocked_at_gate",
            "summary": "Resolve current reviewed-evidence outcome blockers; exact decision coverage alone is not packet or prose readiness.",
            "safe_next_commands": _reviewed_evidence_blocker_commands(
                blockers=blockers,
                review_queue_path=review_queue_path,
                output_dir=output_dir,
                claims_path=claims["required_path"],
                source_safety_path=source_safety["required_path"],
                omissions_path=omissions["required_path"],
                workflow_blockers_path=workflow_blockers["required_path"],
            ),
            "blockers": blockers,
            "required_artifacts": [merged["required_path"]],
        }
    if merged.get("ready_for_reviewed_packet") is True and not blockers:
        packet_status = final_artifacts["reviewed_final_packet"]
        hostile_status = final_artifacts["hostile_review_result"]
        readiness_status = final_artifacts["final_packet_readiness"]
        local_argument = (
            f" --local-evidence-root {local_evidence_root.absolute()}"
            if local_evidence_root is not None
            else ""
        )
        packet_command = (
            "ra survey compose-reviewed-final-packet "
            f"--mission-root {output_dir} "
            f"--review-queue {review_queue_path} "
            f"--packet-dir {packet_dir} "
            f"--anchor-dir {anchor_dir}"
            f"{local_argument} "
            f"--out {output_dir / 'reviewed_final_packet'}"
        )
        hostile_command = (
            "ra survey hostile-review "
            f"--reviewed-final-packet {packet_status['required_path']} "
            f"--mission-root {output_dir} "
            f"--review-queue {review_queue_path} "
            f"--packet-dir {packet_dir} "
            f"--anchor-dir {anchor_dir}"
            f"{local_argument} "
            f"--out {output_dir / 'hostile_review'}"
        )
        if not packet_status["exists"]:
            if packet_status["present"]:
                return {
                    **base,
                    "action_id": "repair_reviewed_final_packet",
                    "status": "blocked_invalid_reviewed_final_packet",
                    "mission_status": "blocked_at_gate",
                    "summary": "The reviewed final packet exists but does not replay from current external mission authority.",
                    "safe_next_commands": [f"{packet_command} --force"],
                    "blockers": list(packet_status.get("blockers") or []),
                    "required_artifacts": [packet_status["required_path"]],
                }
            return {
                **base,
                "action_id": "compose_reviewed_final_packet",
                "status": "ready_for_reviewed_packet_composition",
                "mission_status": "ready_for_local_continuation",
                "summary": "Exact reviewed evidence is clear; compose the immutable reviewed final packet before hostile review or prose readiness.",
                "safe_next_commands": [packet_command],
                "required_artifacts": [merged["required_path"], packet_status["required_path"]],
            }
        if hostile_status["exists"]:
            safe_commands: list[str] = []
            summary = "The authoritative hostile result is current; hand off its bounded state to the Phase 5 executing supervisor."
            if not readiness_status["exists"]:
                safe_commands.append("regenerate final_packet_readiness.json from the validated hostile result; this view is not authority")
                summary += " The optional readiness view is missing or stale and may be regenerated without changing authority."
            return {
                **base,
                "action_id": "phase5_executing_supervisor_handoff",
                "status": "ready_for_phase5_supervisor",
                "mission_status": "ready_for_local_continuation",
                "summary": summary,
                "safe_next_commands": safe_commands,
                "ready_for_hostile_review": True,
                "ready_for_prose": hostile_status["ready_for_prose"],
                "readiness_classification": hostile_status.get("readiness_classification"),
                "blockers": list(hostile_status.get("blockers") or []),
                "required_artifacts": [packet_status["required_path"], hostile_status["required_path"]],
            }
        if hostile_status["present"]:
            return {
                **base,
                "action_id": "repair_hostile_review_result",
                "status": "blocked_invalid_hostile_review_result",
                "mission_status": "blocked_at_gate",
                "summary": "The hostile result exists but does not replay from current external mission authority.",
                "safe_next_commands": [f"{hostile_command} --force"],
                "blockers": list(hostile_status.get("blockers") or []),
                "required_artifacts": [hostile_status["required_path"]],
            }
        if packet_status["exists"]:
            command = f"{hostile_command} --force" if readiness_status["present"] else hostile_command
            return {
                **base,
                "action_id": "run_hostile_review",
                "status": "ready_for_hostile_review",
                "mission_status": "ready_for_local_continuation",
                "summary": "The reviewed final packet is current; run packet-only hostile review before any prose-readiness claim.",
                "safe_next_commands": [command],
                "ready_for_hostile_review": True,
                "ready_for_prose": False,
                "required_artifacts": [packet_status["required_path"], hostile_status["required_path"]],
            }
    return {
        **base,
        "action_id": "resolve_reviewed_evidence_blockers",
        "status": "blocked_by_reviewed_evidence_merge",
        "mission_status": "blocked_at_gate",
        "summary": "Resolve the blockers listed in reviewed_evidence_status.json, refresh the relevant sidecars, then rerun merge-reviewed-evidence.",
        "safe_next_commands": _reviewed_evidence_blocker_commands(
            blockers=blockers,
            review_queue_path=review_queue_path,
            output_dir=output_dir,
            claims_path=claims["required_path"],
            source_safety_path=source_safety["required_path"],
            omissions_path=omissions["required_path"],
        ),
        "blockers": blockers,
        "required_artifacts": [merged["required_path"]],
    }


def _gate_summary(gate: dict[str, Any]) -> str:
    if gate["gate_id"] == "public_metadata":
        return "Public discovery is not confirmed yet. Ask the user once whether RA should search public web/archive sources, or provide a manifest-committed metadata bundle."
    if gate["gate_id"] == "public_metadata_resolution":
        return "The committed V2 metadata bundle has an unresolved, ambiguous, invalid, or conflicting seed; inspect identity_resolution.json before any source intake."
    if gate["gate_id"] == "source_intake":
        if gate.get("covered_by_public_discovery"):
            return (
                "Public source/status lookup is covered by the mission public-discovery confirmation, "
                "but this workflow still needs phase4_source_intake_status.json from a bounded source-status implementation or existing artifact."
            )
        return "Source-intake status is missing; prepare an exact source_fetch approval packet or provide the approved artifact."
    if gate["gate_id"] == "source_anchors":
        return "Source anchors are missing; run local anchor extraction from already-approved structured source records."
    if gate["gate_id"] == "public_source_packet":
        return "The public-source packet is missing; compose it from local metadata, source-status, and anchor artifacts."
    return "Continue the supervised workflow from the current gate."


def _reviewed_evidence_blocker_commands(
    *,
    blockers: list[str],
    review_queue_path: str,
    output_dir: Path,
    claims_path: str,
    source_safety_path: str,
    omissions_path: str,
    workflow_blockers_path: str,
) -> list[str]:
    commands = []
    if any("omission" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_omission_risks.json so open omission risks are inspected, expanded, or explicitly closed for scope"
        )
    if any("source-safety" in blocker.lower() or "checked_clear" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_source_safety.json so every required source-safety row has reviewed checked_clear, blocked, or quarantine evidence"
        )
    if any("claim" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_claims.json so every supported claim row has reviewed technical support and provenance"
        )
    if any("workflow" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_workflow_blockers.json with exact current evidence scopes or keep upstream-only blockers open"
        )
    commands.append(
        "ra survey merge-reviewed-evidence "
        f"--review-queue {review_queue_path} "
        f"--reviewed-claims {claims_path} "
        f"--reviewed-source-safety {source_safety_path} "
        f"--reviewed-omissions {omissions_path} "
        f"--reviewed-workflow-blockers {workflow_blockers_path} "
        f"--out {output_dir / 'reviewed_evidence'} --force"
    )
    return commands


def _safe_next_commands(
    gate: dict[str, Any],
    output_dir: Path,
    topic: str,
    seeds: list[str],
) -> list[str]:
    quoted_topic = json.dumps(topic)
    first_seed = seeds[0] if seeds else "<seed>"
    if gate["gate_id"] == "public_metadata":
        return [
            (
                "ask once: Do you want RA to search public web/archive sources for this idea? "
                "If yes, rerun this workflow with --confirm-public-discovery. "
                f"Planned bounded metadata command: ra survey build --topic {quoted_topic} --seed {first_seed} "
                f"--out {output_dir / 'public_metadata'} --mode public-metadata "
                f"--public-metadata-provider openalex --public-metadata-provider arxiv --max-records {PUBLIC_DISCOVERY_MAX_METADATA_RECORDS}"
            )
        ]
    if gate["gate_id"] == "public_metadata_resolution":
        return [
            "inspect identity_resolution.json and preserve every unresolved, ambiguous, invalid, or conflicting seed choice; do not invoke source intake"
        ]
    if gate["gate_id"] == "source_intake":
        if gate.get("covered_by_public_discovery"):
            return [
                "continue within the recorded public-discovery scope by providing or implementing bounded phase4_source_intake_status.json; do not request a second ordinary public source/archive approval"
            ]
        return ["prepare an exact source_fetch approval packet from the public metadata candidate ledger"]
    if gate["gate_id"] == "source_anchors":
        return ["run ra survey anchors for the approved local structured source paper ids"]
    if gate["gate_id"] == "public_source_packet":
        return ["run ra survey packet with the metadata, source-status, and anchor directories"]
    return [
        "review claim_candidates and map only reviewed claims to source anchors",
        "run approved retraction/version/erratum checks before marking safety checked_clear",
        "resolve omission risks or record explicit omission reasons",
    ]


def _compose_authoritative_artifact_set(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
    topic: str,
    packet_dir: Path,
    packet_manifest: dict[str, Any],
) -> tuple[Any, bool]:
    if snapshot.current_pointer is None:
        raise MissionStateError(
            "missing_mission_generation",
            "artifact-state initialization requires a committed mission generation",
        )
    genesis = read_artifact_genesis(output_dir)
    anchor_generation_id = (
        genesis["mission_anchor_generation_id"]
        if genesis is not None
        else snapshot.current_pointer["generation_id"]
    )
    manager.assert_generation_ancestor(anchor_generation_id)
    artifact_manager = ArtifactStateManager(
        mission_root=output_dir,
        mission_id=snapshot.contract["mission_id"],
        mission_fingerprint=snapshot.contract["mission_fingerprint"],
        mission_anchor_generation_id=anchor_generation_id,
    )
    existing_sets = {
        path.resolve()
        for path in artifact_manager.sets_dir.iterdir()
        if artifact_manager.sets_dir.is_dir() and path.is_dir() and not path.name.startswith(".staging-")
    } if artifact_manager.sets_dir.is_dir() else set()
    canonical_source_status = output_dir / "source_intake" / "phase4_source_intake_status.json"
    validated_source_intake = None
    if canonical_source_status.exists() or canonical_source_status.is_symlink():
        validated_source_intake = validate_mission_source_intake(
            mission_root=output_dir,
            snapshot=snapshot,
            status_path=canonical_source_status,
        )
    coverage_payloads = build_coverage_payloads(
        topic=topic,
        packet_dir=packet_dir,
        validated_source_intake=validated_source_intake,
        mission_anchor_generation_id=anchor_generation_id,
    )
    queue_payload = _build_review_queue_payload(
        topic=topic,
        packet_dir=packet_dir,
        packet_manifest=packet_manifest,
        coverage_payloads=coverage_payloads,
    )
    selected = artifact_manager.compose_and_select(
        packet_dir=packet_dir,
        coverage_payloads=coverage_payloads,
        review_queue_payload=queue_payload,
    )
    return selected, selected.set_dir.resolve() in existing_sets


def _load_current_artifact_set_readonly(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
) -> Any | None:
    if snapshot.current_pointer is None:
        return None
    genesis = read_artifact_genesis(output_dir)
    if genesis is None:
        return None
    anchor_generation_id = genesis["mission_anchor_generation_id"]
    manager.assert_generation_ancestor(anchor_generation_id)
    artifact_manager = ArtifactStateManager(
        mission_root=output_dir,
        mission_id=snapshot.contract["mission_id"],
        mission_fingerprint=snapshot.contract["mission_fingerprint"],
        mission_anchor_generation_id=anchor_generation_id,
    )
    return artifact_manager.load_current(required=False)


def _selected_packet_inputs_are_current(selected: Any, packet_dir: Path) -> bool:
    names = {**PACKET_COVERAGE_FILES, **PACKET_QUEUE_FILES}
    actual: dict[str, dict[str, Any]] = {}
    try:
        for role, name in sorted(names.items()):
            path = packet_dir.resolve() / name
            actual[role] = {
                "relative_path": name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
    except (OSError, MissionStateError):
        return False
    return selected.manifest.get("packet_input_digests") == actual


def _review_queue_summary(selected: Any, queue_payload: dict[str, Any], *, reused: bool) -> dict[str, Any]:
    return {
        "path": str(selected.review_queue_path),
        "queue_counts": queue_payload.get("queue_counts"),
        "reused_existing": reused,
        "artifact_set_id": selected.artifact_set_id,
        "queue_semantic_sha256": queue_payload.get("queue_semantic_sha256"),
    }


def _artifact_state_summary(selected: Any) -> dict[str, Any]:
    return {
        "status": "selected",
        "artifact_set_id": selected.artifact_set_id,
        "mission_anchor_generation_id": selected.manifest["mission_anchor_generation_id"],
        "review_queue_path": str(selected.review_queue_path),
        "coverage_dir": str(selected.coverage_dir),
        "recovery": selected.recovery,
    }


def _selected_coverage_path_if_present(output_dir: Path) -> Path | None:
    genesis = read_artifact_genesis(output_dir)
    if genesis is None:
        return None
    manager = ArtifactStateManager(
        mission_root=output_dir,
        mission_id=genesis["mission_id"],
        mission_fingerprint=genesis["mission_fingerprint"],
        mission_anchor_generation_id=genesis["mission_anchor_generation_id"],
    )
    selected = manager.load_current(required=False)
    return selected.coverage_dir.resolve() if selected is not None else None


def _build_review_queue_payload(
    *,
    topic: str,
    packet_dir: Path,
    packet_manifest: dict[str, Any],
    coverage_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    input_paths = {
        "claim_support": packet_dir / "claim_support.json",
        "source_safety_status": packet_dir / "source_safety_status.json",
        "build_manifest": packet_dir / "build_manifest.json",
    }
    claim_support = read_packet_json(packet_dir, "claim_support.json", label="claim support")
    source_safety = read_packet_json(packet_dir, "source_safety_status.json", label="source safety status")
    packet_manifest = read_packet_json(packet_dir, "build_manifest.json", label="packet build manifest")
    omission_risk = coverage_payloads.get("omitted_paper_risks.json")
    if not isinstance(claim_support, dict) or not isinstance(source_safety, dict) or not isinstance(omission_risk, dict):
        raise MissionStateError("invalid_review_queue_input", "unified queue inputs must be valid JSON objects")
    workflow_state = packet_manifest.get("workflow_state") or {}

    review_items: list[dict[str, Any]] = []
    review_items.extend(_claim_candidate_items(claim_support))
    review_items.extend(_source_safety_items(source_safety))
    review_items.extend(_omission_risk_items(omission_risk))
    review_items = validate_semantic_items(sorted(
        review_items,
        key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]),
    ))
    items = [*review_items, *_workflow_blocker_items(workflow_state, review_items)]
    items = validate_semantic_items(sorted(
        items,
        key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]),
    ))

    queue_counts = {
        "total": len(items),
        "by_type": _count_items(items, "queue_type"),
        "by_priority": _count_items(items, "priority"),
        "by_status": _count_items(items, "status"),
    }
    return {
        "status": "review_required",
        "topic": topic,
        "queue_counts": queue_counts,
        "items": items,
        "allowed_item_statuses": [
            "review_required",
            "blocked_pending_evidence",
            "blocked_pending_approval",
        ],
        "forbidden_promotions": [
            "claim candidates are not supported claims",
            "source availability is not source-safety evidence",
            "omission-risk visibility is not literature completeness",
            "workflow blockers cannot be cleared by queue creation",
            "review_queue creation cannot mark ready_for_prose true",
        ],
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }


def _validate_artifact_packet_inputs(packet_dir: Path) -> None:
    for name in [
        "candidate_ledger.json",
        "citation_map.json",
        "paper_classifications.json",
        "omission_risk.json",
        "claim_support.json",
        "source_safety_status.json",
        "build_manifest.json",
    ]:
        read_packet_json(packet_dir, name, label=name)


def _claim_candidate_items(claim_support: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for row in claim_support.get("claim_candidates") or []:
        if not isinstance(row, dict):
            raise MissionStateError("invalid_claim_candidate", "claim candidates must be objects")
        source_id = normalized_identity_text(row.get("claim_id"), field="claim_id")
        items.append(semantic_item(
            queue_type="claim_candidate",
            source_id=source_id,
            semantic_fields={
            "priority": _claim_priority(row),
            "status": "review_required",
            "input_status": row.get("status"),
            "claim_support_allowed": False,
            "support_class": row.get("support_class", "anchor_candidate_not_support"),
            "anchor_ids": sorted(set(row.get("anchor_ids") or [])),
            "paper_ids": sorted(set(row.get("paper_ids") or [])),
            "title_or_anchor": row.get("anchor_title"),
            "action_required": row.get("next_action") or "review the candidate and map a precise claim before support",
            "non_promotion_reason": "source anchors and claim candidates are not supported technical claims",
            },
        ))
    return items


def _source_safety_items(source_safety: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for row in source_safety.get("rows") or []:
        if not isinstance(row, dict):
            raise MissionStateError("invalid_source_safety", "source-safety rows must be objects")
        source_id = normalized_identity_text(
            row.get("paper_id") or row.get("arxiv_id"),
            field="source-safety paper_id or arxiv_id",
        )
        items.append(semantic_item(
            queue_type="source_safety",
            source_id=source_id,
            semantic_fields={
            "priority": "high",
            "status": "blocked_pending_evidence",
            "paper_id": row.get("paper_id"),
            "arxiv_id": row.get("arxiv_id"),
            "input_status": row.get("retraction_or_version_status") or row.get("original_status"),
            "safety_checked_clear": False,
            "claim_support_allowed": False,
            "action_required": row.get("next_action") or "run approved status checks or import reviewed safety evidence",
            "evidence_contract": row.get("evidence_contract"),
            "non_promotion_reason": "source availability is not retraction, withdrawal, erratum, or version safety evidence",
            },
        ))
    return items


def _omission_risk_items(omission_risk: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    v2 = omission_risk.get("schema_version") == "ra-survey-omitted-paper-risks-v2"
    seen_sources: set[tuple[str, str]] = set()
    for row in omission_risk.get("risks") or []:
        if not isinstance(row, dict):
            raise MissionStateError("invalid_omission_risk", "omission risks must be objects")
        source_id = normalized_identity_text(row.get("risk_id"), field="risk_id")
        v2_fields: dict[str, Any] = {}
        if v2:
            risk_source_type = normalized_identity_text(
                row.get("risk_source_type"),
                field="risk_source_type",
            )
            risk_source_id = normalized_identity_text(
                row.get("risk_source_id"),
                field="risk_source_id",
            )
            source_key = (risk_source_type, risk_source_id)
            if source_key in seen_sources:
                raise MissionStateError("duplicate_omission_risk_source", "V2 risks must be one-to-one with sources")
            seen_sources.add(source_key)
            machine_disposition = row.get("machine_disposition")
            if machine_disposition not in {
                "inspect_next",
                "omit_with_reason",
                "quarantine",
                "blocked_source_or_frontier",
            }:
                raise MissionStateError("invalid_omission_risk", "V2 risk machine disposition is invalid")
            source_digest = row.get("source_artifact_sha256")
            if (
                not isinstance(source_digest, str)
                or len(source_digest) != 64
                or any(char not in "0123456789abcdef" for char in source_digest)
            ):
                raise MissionStateError("invalid_omission_risk", "V2 risk source digest is invalid")
            v2_fields = {
                "coverage_schema_version": omission_risk["schema_version"],
                "machine_disposition": machine_disposition,
                "risk_source_type": risk_source_type,
                "risk_source_id": risk_source_id,
                "source_artifact_sha256": source_digest,
            }
        items.append(semantic_item(
            queue_type="omission_risk",
            source_id=source_id,
            semantic_fields={
            "priority": _severity_priority(row.get("severity")),
            "status": "blocked_pending_evidence",
            "risk_id": source_id,
            "severity": row.get("severity"),
            "reason": row.get("reason") or row.get("risk"),
            "action_required": row.get("next_action") or row.get("expected_action") or "inspect, justify omission, expand, or keep blocked",
            **v2_fields,
            "literature_completeness_allowed": False,
            "non_promotion_reason": "omission-risk visibility is not literature completeness",
            },
        ))
    return items


def _workflow_blocker_items(
    workflow_state: dict[str, Any],
    review_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items = []
    blocker_ids: dict[str, str] = {}
    for raw_reason in workflow_state.get("blocked_reasons") or []:
        reason = normalized_identity_text(raw_reason, field="workflow blocker")
        source_id = workflow_blocker_source_id(reason)
        prior = blocker_ids.get(source_id)
        if prior == reason:
            continue
        if prior is not None:
            raise MissionStateError("workflow_blocker_id_collision", "distinct workflow blockers share one semantic ID")
        blocker_ids[source_id] = reason
        resolution_class, evidence_type = workflow_blocker_resolution(reason)
        evidence_ids = sorted(
            str(item["item_id"])
            for item in review_items
            if evidence_type is not None and item["queue_type"] == evidence_type
        )
        if evidence_type is not None and not evidence_ids:
            resolution_class = "upstream_repair_required"
            evidence_type = None
        items.append(semantic_item(
            queue_type="workflow_blocker",
            source_id=source_id,
            semantic_fields={
            "priority": "high",
            "status": "blocked_pending_evidence",
            "reason": reason,
            "resolution_class": resolution_class,
            "required_evidence_queue_type": evidence_type,
            "required_evidence_queue_item_ids": evidence_ids,
            "ready_for_prose": False,
            "action_required": "clear the underlying blocker with explicit reviewed evidence before prose readiness",
            "non_promotion_reason": "workflow blockers cannot be cleared by queue creation",
            },
        ))
    return items


def _claim_priority(row: dict[str, Any]) -> str:
    role = str(row.get("anchor_role") or "")
    if "theory" in role or "method" in role:
        return "high"
    return "medium"


def _severity_priority(value: Any) -> str:
    severity = str(value or "").lower()
    if severity in {"high", "medium", "low"}:
        return severity
    return "medium"


def _count_items(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _blocked(
    reason: str,
    output_dir: Path,
    next_required_actions: list[str],
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SURVEY_ORCHESTRATION_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": ORCHESTRATION_NONCLAIMS,
    }
    if details:
        payload["details"] = details
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
