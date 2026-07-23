"""Read-only product workflow projection for a survey mission.

The mission state, source ledgers, and review artifacts remain authoritative in
their owning modules.  This module only projects their current state into one
deterministic operator view; it never performs discovery, download, parsing,
review, or claim promotion.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.mission_state import (
    EXPLICIT_SEED_INPUT_MODE,
    MissionStateError,
    TOPIC_INPUT_MODE,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)


MISSION_PLAN_SCHEMA = "ra-survey-mission-plan-v2"
_STAGES = (
    ("discovery", "Nominate or accept paper identities"),
    ("identity_resolution", "Resolve duplicate and conflicting identities"),
    ("source_resolution", "Resolve a lawful source version"),
    ("source_safety", "Check retraction, version, and source safety"),
    ("technical_inspection", "Inspect technical sections and anchors"),
    ("backward_snowball", "Classify relevant references from seed sources"),
    ("forward_snowball", "Record citing works when an allowed source exists"),
    ("centrality_assessment", "Classify source-evaluated candidate centrality"),
    ("claim_mapping", "Map claims to checked source anchors or derivations"),
    ("human_review", "Resolve the explicit review queues"),
    ("hostile_review", "Run the final omission and claim gate"),
    ("release_export", "Export or publish only after release boundaries"),
)
_NONCLAIMS = [
    "literature completeness",
    "canonical seed-paper truth",
    "citation-provider recall",
    "technical correctness",
    "domain-specific suitability or compliance",
    "publication readiness",
    "autonomous expert judgment",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MissionStateError("invalid_mission_plan_input", f"{field} must be an object")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise MissionStateError("invalid_mission_plan_input", f"{field} must be nonempty text")
    return value


def _path_status(phase: Any, *, default: str = "pending") -> str:
    if not isinstance(phase, dict):
        return default
    if phase.get("resolution_blocked") is True:
        return "blocked"
    if phase.get("exists") is True:
        return "complete"
    return default


def _phase(phase_id: str, label: str, status: str, *, gate: str, artifacts: list[str],
           action: str, boundary: str, evidence: str) -> dict[str, Any]:
    return {
        "stage_id": phase_id,
        "label": label,
        "status": status,
        "gate": gate,
        "required_artifacts": sorted(set(artifacts)),
        "next_action": action,
        "boundary": boundary,
        "evidence": evidence,
        "technical_claim_support": status == "complete" and phase_id in {"technical_inspection", "claim_mapping"},
    }


def _review_status(value: Any, *, key: str) -> tuple[str, list[str]]:
    if not isinstance(value, dict):
        return "pending", []
    statuses = [row for row in value.values() if isinstance(row, dict)]
    if not statuses:
        return "pending", []
    if any(row.get("authority_invalid") or row.get("lineage_status") not in {None, "current_lineage"} for row in statuses):
        return "blocked", [f"{key} contains stale or invalid authority"]
    if all(row.get("exists") is True for row in statuses):
        return "complete", []
    return "review_required", [f"{key} decisions remain incomplete"]


def build_mission_plan(
    mission_control: dict[str, Any],
    next_action: dict[str, Any],
    *,
    created_at: str | None = None,
    centrality_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical, side-effect-free workflow projection."""
    mission = _require_object(mission_control, "mission_control")
    action = _require_object(next_action, "next_action")
    if mission.get("input_mode") is None:
        if isinstance(mission.get("seeds"), list):
            mission = {**mission, "input_mode": EXPLICIT_SEED_INPUT_MODE}
        else:
            raise MissionStateError("invalid_mission_plan_input", "mission_control.input_mode must be nonempty text")
    if mission.get("effective_seeds") is None and isinstance(mission.get("seeds"), list):
        mission = {**mission, "effective_seeds": list(mission["seeds"])}
    for field in ("schema_version", "mission_id", "mission_fingerprint", "generation_id", "status", "topic", "input_mode"):
        _required_text(mission.get(field), f"mission_control.{field}")
    for field in ("mission_id", "mission_fingerprint", "generation_id", "action_id", "status"):
        _required_text(action.get(field), f"next_action.{field}")
    for field in ("mission_id", "mission_fingerprint", "generation_id"):
        if mission[field] != action[field]:
            raise MissionStateError("mission_plan_binding_mismatch", f"{field} differs between mission control and next action")
    if mission["input_mode"] not in {TOPIC_INPUT_MODE, EXPLICIT_SEED_INPUT_MODE}:
        raise MissionStateError("invalid_mission_plan_input", "mission input mode is unsupported")
    phases = mission.get("phase_statuses")
    if not isinstance(phases, dict):
        raise MissionStateError("invalid_mission_plan_input", "mission_control.phase_statuses must be an object")
    confirmation = mission.get("public_discovery_confirmation")
    if not isinstance(confirmation, dict) or type(confirmation.get("confirmed")) is not bool:
        raise MissionStateError("invalid_mission_plan_input", "public discovery confirmation is invalid")

    topic_mode = mission["input_mode"] == TOPIC_INPUT_MODE
    bootstrap_state = mission.get("bootstrap_attempt_state") if topic_mode else "explicit_seed"
    bootstrap_outcome = mission.get("bootstrap_outcome") if topic_mode else "accepted"
    effective_seeds = mission.get("effective_seeds") if topic_mode else mission.get("seeds")
    if not isinstance(effective_seeds, list) or any(not isinstance(seed, str) or not seed for seed in effective_seeds):
        raise MissionStateError("invalid_mission_plan_input", "mission seed projection is invalid")

    discovery_status = "complete" if (not topic_mode and effective_seeds) else (
        "complete" if bootstrap_state == "selected_complete" and bootstrap_outcome == "selected" else
        "blocked" if bootstrap_state == "selected_complete" else "pending"
    )
    identity_status = "complete" if discovery_status == "complete" and not topic_mode else (
        "review_required" if discovery_status == "complete" else discovery_status
    )
    source_status = _path_status(phases.get("source_intake"), default="pending")
    anchor_status = _path_status(phases.get("source_anchors"), default="pending")
    packet_status = _path_status(phases.get("public_source_packet"), default="pending")
    coverage = mission.get("coverage_artifacts") or {}
    backward_status = _path_status(coverage.get("backward_snowball"), default="pending")
    forward_status = _path_status(coverage.get("forward_snowball"), default="pending")
    centrality_counts = {verdict: 0 for verdict in (
        "BLOCKED", "PERIPHERAL", "QUARANTINED", "REJECTED_OFF_TOPIC",
        "VALIDATED_CENTRAL", "VALIDATED_RELEVANT",
    )}
    if centrality_assessment is None:
        centrality_status = "pending"
        centrality_evidence = "no validated centrality assessment"
    else:
        if centrality_assessment.get("schema_version") != "ra-survey-centrality-assessment-v1":
            raise MissionStateError(
                "invalid_mission_plan_input", "centrality assessment schema is unsupported"
            )
        if centrality_assessment.get("topic") != mission["topic"]:
            raise MissionStateError(
                "mission_plan_binding_mismatch", "centrality assessment belongs to a different topic"
            )
        counts = centrality_assessment.get("counts")
        if not isinstance(counts, dict) or set(counts) != set(centrality_counts):
            raise MissionStateError(
                "invalid_mission_plan_input", "centrality assessment counts are invalid"
            )
        if any(type(value) is not int or value < 0 for value in counts.values()):
            raise MissionStateError(
                "invalid_mission_plan_input", "centrality assessment counts are invalid"
            )
        centrality_counts = dict(counts)
        centrality_status = "complete" if counts["VALIDATED_CENTRAL"] else "blocked"
        centrality_evidence = "; ".join(
            f"{verdict}={counts[verdict]}" for verdict in sorted(counts)
        )
    reviewed = mission.get("reviewed_artifacts") or {}
    review_status, review_blockers = _review_status(reviewed, key="review queues")
    final = mission.get("final_artifacts") or {}
    hostile_status = _path_status(final.get("hostile_review_result"), default="pending")
    if hostile_status == "complete" and final.get("hostile_review_result", {}).get("ready_for_prose") is not True:
        hostile_status = "blocked"
    claims_status = "complete" if packet_status == "complete" and review_status == "complete" else "pending"
    release_status = "blocked"
    stages = [
        _phase("discovery", _STAGES[0][1], discovery_status, gate="topic_bootstrap_or_explicit_seed", artifacts=["mission_control.json", "next_action.json"], action="inspect nominated identities" if discovery_status == "complete" else action.get("action_id", "confirm_public_discovery"), boundary="metadata nomination only" if topic_mode else "user-supplied identity", evidence=f"bootstrap={bootstrap_state}; outcome={bootstrap_outcome}"),
        _phase("identity_resolution", _STAGES[1][1], identity_status, gate="identity_review", artifacts=["offline_skeleton/candidate_ledger.json"] if topic_mode else ["offline_skeleton/candidate_ledger.json"], action=("run survey continue-topic into a fresh child mission" if topic_mode and identity_status == "review_required" else "review duplicate/conflict and source identity decisions"), boundary="identity is not relevance or technical evidence", evidence="effective seed authority" if topic_mode else "explicit seed list"),
        _phase("source_resolution", _STAGES[2][1], source_status, gate="source_intake", artifacts=["source_intake/phase4_source_intake_status.json"], action="start bounded source intake" if not topic_mode else "start an explicit-seed source mission from the selected authority", boundary="topic bootstrap does not silently become source authority", evidence="source intake status"),
        _phase("source_safety", _STAGES[3][1], "complete" if review_status == "complete" else "review_required", gate="source_safety_review", artifacts=["reviewed_source_safety/reviewed_source_safety.json"], action="resolve source safety decisions", boundary="availability is not safety", evidence="reviewed source-safety sidecar"),
        _phase("technical_inspection", _STAGES[4][1], anchor_status, gate="source_anchors", artifacts=["source_anchors/source_anchor_inventory.json"], action="inspect technical sections, equations, algorithms, tables, and appendices", boundary="anchors support only inspected source text", evidence="source-anchor inventory"),
        _phase("backward_snowball", _STAGES[5][1], backward_status, gate="coverage_ledgers", artifacts=["coverage_ledgers/backward_snowball.json"], action="classify relevant references from inspected seeds", boundary="no backward completeness claim", evidence="backward snowball ledger"),
        _phase("forward_snowball", _STAGES[6][1], forward_status, gate="coverage_ledgers", artifacts=["coverage_ledgers/forward_snowball.json"], action="record citing works or preserve the provider-unavailable blocker", boundary="unavailable forward coverage is not zero", evidence="forward snowball ledger"),
        _phase("centrality_assessment", _STAGES[7][1], centrality_status, gate="source_grounded_centrality", artifacts=["centrality/centrality_assessment.json", "centrality/centrality_manifest.json"], action=("continue source inspection and snowballing, then run survey assess-centrality" if centrality_status == "pending" else "repair evidence blockers or nominate and inspect additional candidates"), boundary="metadata rank, citation count, venue metric, and source availability cannot promote centrality", evidence=centrality_evidence),
        _phase("claim_mapping", _STAGES[8][1], claims_status, gate="claim_support", artifacts=["claim_support.json", "reviewed_claims/reviewed_claims.json"], action="map each important claim to an inspected anchor or derivation", boundary="metadata and venue signals cannot support technical claims", evidence="claim-support ledger"),
        _phase("human_review", _STAGES[9][1], review_status, gate="review_queues", artifacts=["reviewed_claims/reviewed_claims.json", "reviewed_source_safety/reviewed_source_safety.json", "reviewed_omissions/reviewed_omission_risks.json", "reviewed_workflow_blockers/reviewed_workflow_blockers.json"], action="resolve explicit review decisions", boundary="machine output does not attest for a human", evidence="; ".join(review_blockers) if review_blockers else "reviewed sidecars"),
        _phase("hostile_review", _STAGES[10][1], hostile_status, gate="hostile_review", artifacts=["reviewed_final_packet/reviewed_final_packet.json", "hostile_review/hostile_review_result.json"], action="run or repair hostile review", boundary="hostile review is scoped readiness, not completeness", evidence="hostile review result"),
        _phase("release_export", _STAGES[11][1], release_status, gate="release_owner_and_ci", artifacts=["dist/release_gate_evidence.json"], action="run final release gate, CI, and obtain release-owner approval", boundary="tag/publication is an external boundary", evidence="release-readiness documentation"),
    ]
    complete = {"complete"}
    current = next((row for row in stages if row["status"] not in complete), stages[-1])
    plan = {
        "schema_version": MISSION_PLAN_SCHEMA,
        "created_at": created_at or _utc_now(),
        "mission_id": mission["mission_id"],
        "mission_fingerprint": mission["mission_fingerprint"],
        "generation_id": mission["generation_id"],
        "topic": mission["topic"],
        "input_mode": mission["input_mode"],
        "effective_seed_count": len(effective_seeds),
        "centrality": {
            "status": centrality_status,
            "validated_central_candidate_count": centrality_counts["VALIDATED_CENTRAL"],
            "counts": centrality_counts,
            "metadata_nomination_is_validated_centrality": False,
        },
        "mission_status": mission["status"],
        "mission_next_action": action["action_id"],
        "current_stage": current["stage_id"],
        "next_action": current["next_action"],
        "stages": stages,
        "what_is_not_concluded": [
            *_NONCLAIMS,
            *([] if centrality_status == "complete" else ["topic centrality"]),
        ],
    }
    plan["mission_control_sha256"] = sha256_bytes(canonical_json_bytes(mission))
    plan["next_action_sha256"] = sha256_bytes(canonical_json_bytes(action))
    return plan


def write_mission_plan(*, mission_control: dict[str, Any], next_action: dict[str, Any], output_path: Path, force: bool = False, topic_handoff: dict[str, Any] | None = None, centrality_assessment: dict[str, Any] | None = None) -> dict[str, Any]:
    output_path = output_path.absolute()
    assert_public_write_path_allowed(output_path)
    plan = build_mission_plan(
        mission_control,
        next_action,
        centrality_assessment=centrality_assessment,
    )
    if topic_handoff is not None:
        plan["topic_handoff"] = topic_handoff
    payload = pretty_json_bytes(plan)
    if output_path.exists() or output_path.is_symlink():
        if output_path.is_symlink():
            raise MissionStateError("mission_plan_exists", "mission plan exists with different bytes")
        if output_path.read_bytes() == payload:
            return {"schema_version": MISSION_PLAN_SCHEMA, "status": "mission_plan_reused", "output_path": str(output_path), "plan": plan}
        if not force:
            raise MissionStateError("mission_plan_exists", "mission plan exists with different bytes")
        atomic_write_bytes(output_path, payload)
        return {"schema_version": MISSION_PLAN_SCHEMA, "status": "mission_plan_written", "output_path": str(output_path), "plan": plan}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(output_path, payload)
    return {"schema_version": MISSION_PLAN_SCHEMA, "status": "mission_plan_written", "output_path": str(output_path), "plan": plan}


def write_mission_plan_from_root(*, mission_root: Path, output_path: Path | None = None) -> dict[str, Any]:
    """Replay the active mission state and write its read-only product plan."""
    from research_assistant.survey.mission_state import MissionStateManager, TOPIC_INPUT_MODE

    root = mission_root.absolute()
    genesis_path = root / ".mission_state" / "GENESIS"
    try:
        genesis = json.loads(genesis_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_mission_plan_root", "mission GENESIS is not readable JSON") from exc
    normalized_topic = _require_object(genesis.get("normalized_topic"), "GENESIS.normalized_topic")
    topic = _required_text(normalized_topic.get("display"), "GENESIS.normalized_topic.display")
    input_mode = genesis.get("input_mode")
    if input_mode is None and "normalized_seeds" in genesis:
        input_mode = EXPLICIT_SEED_INPUT_MODE
    input_mode = _required_text(input_mode, "GENESIS.input_mode")
    if input_mode == TOPIC_INPUT_MODE:
        seeds: list[str] = []
    else:
        normalized_seeds = genesis.get("normalized_seeds")
        if not isinstance(normalized_seeds, list):
            raise MissionStateError("invalid_mission_plan_root", "GENESIS.normalized_seeds is invalid")
        seeds = [_required_text(row.get("display"), "GENESIS.normalized_seeds[].display") for row in normalized_seeds if isinstance(row, dict)]
        if len(seeds) != len(normalized_seeds):
            raise MissionStateError("invalid_mission_plan_root", "GENESIS.normalized_seeds contains an invalid row")
    budget = _require_object(genesis.get("discovery_budget"), "GENESIS.discovery_budget")
    providers = budget.get("providers")
    domains = budget.get("allowed_domains")
    if not isinstance(providers, list) or not isinstance(domains, list):
        raise MissionStateError("invalid_mission_plan_root", "GENESIS discovery budget lacks provider scope")
    manager = MissionStateManager(
        output_dir=root,
        topic=topic,
        seeds=seeds,
        input_mode=input_mode,
        confirm_public_discovery=False,
        resume=True,
        force=False,
        discovery_providers=providers,
        discovery_allowed_domains=domains,
        aggregate_metadata_budget="max_metadata_requests" in budget,
    )
    try:
        snapshot = manager.begin()
        if snapshot.mission_control is None or snapshot.next_action is None:
            raise MissionStateError("mission_plan_state_missing", "mission has no committed mission-control generation")
        mission_control = dict(snapshot.mission_control)
        # Explicit mission-control v2 predates the input-mode field; derive
        # the view from the validated GENESIS contract without changing
        # the authoritative artifact.
        mission_control.setdefault("input_mode", input_mode)
        if input_mode == TOPIC_INPUT_MODE:
            mission_control.setdefault("effective_seeds", mission_control.get("effective_seeds", []))
        else:
            mission_control.setdefault("seeds", seeds)
            mission_control.setdefault("effective_seeds", seeds)
        handoff_path = root / "topic_handoff.json"
        if handoff_path.is_file():
            try:
                handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MissionStateError("invalid_topic_handoff", "child mission topic handoff is not readable JSON") from exc
            if not isinstance(handoff, dict) or handoff.get("schema_version") != "ra-survey-topic-continuation-handoff-v1":
                raise MissionStateError("invalid_topic_handoff", "child mission topic handoff schema is unsupported")
            child = handoff.get("child")
            if not isinstance(child, dict) or child.get("root") != str(root) or child.get("mission_id") != mission_control["mission_id"]:
                raise MissionStateError("invalid_topic_handoff", "child mission topic handoff binding is stale or foreign")
            topic_handoff = {
                "path": str(handoff_path),
                "sha256": sha256_bytes(canonical_json_bytes(handoff)),
                "parent_mission_id": handoff.get("parent", {}).get("mission_id"),
                "effective_seed_count": len(handoff.get("effective_seeds") or []),
            }
        else:
            topic_handoff = None
        centrality_root = root / "centrality"
        if centrality_root.exists() or centrality_root.is_symlink():
            from research_assistant.survey.centrality import validate_centrality_output

            centrality = validate_centrality_output(
                centrality_root,
                expected_topic=topic,
            )["assessment"]
        else:
            centrality = None
        target = (output_path or root / "mission_plan.json").absolute()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise MissionStateError("mission_plan_write_outside_root", "mission plan output must be beneath the mission root") from exc
        return write_mission_plan(
            mission_control=mission_control,
            next_action=snapshot.next_action,
            output_path=target,
            force=True,
            topic_handoff=topic_handoff,
            centrality_assessment=centrality,
        )
    finally:
        manager.abort()


__all__ = ["MISSION_PLAN_SCHEMA", "build_mission_plan", "write_mission_plan", "write_mission_plan_from_root"]
