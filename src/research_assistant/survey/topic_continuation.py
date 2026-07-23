"""Transfer a selected topic bootstrap into an isolated explicit-seed mission.

The parent topic mission and bootstrap authority remain authoritative.  This
module only validates that authority, creates a fresh child mission using the
selected identifiers, and records a provenance handoff.  It never performs
provider, source, PDF, claim, or review work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.mission_state import (
    TOPIC_INPUT_MODE,
    EXPLICIT_SEED_INPUT_MODE,
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.bootstrap import MissionBootstrapStore


TOPIC_HANDOFF_SCHEMA = "ra-survey-topic-continuation-handoff-v1"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_topic_handoff_input", f"{label} is not readable JSON") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_topic_handoff_input", f"{label} must be an object")
    return payload


def _parent_manager(parent_root: Path) -> MissionStateManager:
    genesis = _read_json(parent_root / ".mission_state" / "GENESIS", label="topic mission GENESIS")
    normalized_topic = genesis.get("normalized_topic")
    if not isinstance(normalized_topic, dict) or not isinstance(normalized_topic.get("display"), str):
        raise MissionStateError("invalid_topic_parent", "topic mission GENESIS lacks a normalized topic")
    budget = genesis.get("discovery_budget")
    if not isinstance(budget, dict) or not isinstance(budget.get("providers"), list) or not isinstance(budget.get("allowed_domains"), list):
        raise MissionStateError("invalid_topic_parent", "topic mission GENESIS lacks a discovery budget")
    if genesis.get("input_mode") != TOPIC_INPUT_MODE:
        raise MissionStateError("invalid_topic_parent", "continuation requires a topic-input mission")
    return MissionStateManager(
        output_dir=parent_root,
        topic=normalized_topic["display"],
        seeds=[],
        input_mode=TOPIC_INPUT_MODE,
        confirm_public_discovery=False,
        resume=True,
        force=False,
        discovery_providers=budget["providers"],
        discovery_allowed_domains=budget["allowed_domains"],
        aggregate_metadata_budget="max_metadata_requests" in budget,
    )


def _validate_parent(parent_root: Path) -> tuple[MissionStateManager, dict[str, Any], dict[str, Any], dict[str, Any]]:
    manager = _parent_manager(parent_root)
    snapshot = manager.begin()
    try:
        mission = snapshot.mission_control
        action = snapshot.next_action
        if not isinstance(mission, dict) or not isinstance(action, dict):
            raise MissionStateError("topic_parent_not_selected", "topic mission has no committed bootstrap generation")
        if mission.get("input_mode") != TOPIC_INPUT_MODE or mission.get("bootstrap_attempt_state") != "selected_complete" or mission.get("bootstrap_outcome") != "selected":
            raise MissionStateError("topic_parent_not_selected", "topic mission is not at a selected bootstrap boundary")
        authority = mission.get("bootstrap_authority")
        if not isinstance(authority, dict):
            raise MissionStateError("topic_parent_authority_missing", "selected topic mission lacks bootstrap authority")
        selected = MissionBootstrapStore.from_snapshot(manager=manager, snapshot=snapshot, now=lambda: "")
        observed = selected.validate_selected(expected_authority=authority)
        seeds = observed.get("effective_seeds")
        if not isinstance(seeds, list) or not seeds or any(not isinstance(seed, str) or not seed.strip() for seed in seeds):
            raise MissionStateError("topic_parent_seeds_missing", "selected bootstrap authority has no effective seeds")
        return manager, mission, action, {
            "authority": authority,
            "seeds": list(seeds),
            "selected_candidates": observed.get("selected_candidates", []),
            "parent_contract": snapshot.contract,
        }
    except Exception:
        manager.abort()
        raise


def _handoff_payload(
    *,
    parent_root: Path,
    child_root: Path,
    parent_mission: dict[str, Any],
    parent_action: dict[str, Any],
    parent_data: dict[str, Any],
    child_result: dict[str, Any],
    child_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    child_mission = child_result.get("mission_id")
    child_fingerprint = child_result.get("mission_fingerprint")
    child_generation = child_result.get("generation_id")
    if not all(isinstance(value, str) and value for value in (child_mission, child_fingerprint, child_generation)):
        raise MissionStateError("child_mission_state_missing", "child mission did not return bound mission identity")
    child_control = _read_json(child_root / "mission_control.json", label="child mission control")
    child_action = _read_json(child_root / "next_action.json", label="child next action")
    child_genesis = _read_json(child_root / ".mission_state" / "GENESIS", label="child mission GENESIS")
    if child_genesis.get("schema_version") not in {"ra-survey-public-source-genesis-anchor-v1", "ra-survey-public-source-genesis-v1"}:
        raise MissionStateError("child_mission_mode_mismatch", "continuation child has an unsupported mission contract")
    normalized_seeds = child_genesis.get("normalized_seeds")
    child_seed_values = [row.get("display") for row in normalized_seeds] if isinstance(normalized_seeds, list) and all(isinstance(row, dict) for row in normalized_seeds) else None
    if child_seed_values != parent_data["seeds"]:
        raise MissionStateError("child_seed_drift", "child mission seeds differ from selected parent seeds")
    if child_control.get("mission_id") != child_mission or child_action.get("mission_id") != child_mission:
        raise MissionStateError("child_mission_binding_mismatch", "child mission artifacts disagree with command result")
    payload = {
        "schema_version": TOPIC_HANDOFF_SCHEMA,
        "parent": {
            "root": str(parent_root),
            "mission_id": parent_mission["mission_id"],
            "mission_fingerprint": parent_mission["mission_fingerprint"],
            "generation_id": parent_mission["generation_id"],
            "mission_control_sha256": sha256_bytes(canonical_json_bytes(parent_mission)),
            "next_action_sha256": sha256_bytes(canonical_json_bytes(parent_action)),
            "bootstrap_authority": parent_data["authority"],
            "effective_seeds": parent_data["seeds"],
        },
        "child": {
            "root": str(child_root),
            "mission_id": child_mission,
            "mission_fingerprint": child_fingerprint,
            "generation_id": child_generation,
            "mission_control_sha256": sha256_bytes(canonical_json_bytes(child_control)),
            "next_action_sha256": sha256_bytes(canonical_json_bytes(child_action)),
            "result_status": child_result.get("status"),
        },
        "selected_candidates": parent_data["selected_candidates"],
        "effective_seeds": parent_data["seeds"],
        "handoff_boundary": "metadata nomination transferred; source, safety, technical inspection, snowballing, claims, human review, hostile review, and release remain downstream gates",
        "what_is_not_concluded": [
            "canonical seed-paper truth",
            "source availability or safety",
            "technical claim support",
            "literature completeness",
            "scientific correctness",
            "domain-specific suitability",
            "topic centrality",
            "publication readiness",
            "release approval",
        ],
    }
    if child_plan is not None:
        payload["child"]["mission_plan_sha256"] = sha256_bytes(canonical_json_bytes(child_plan))
    return payload


def _write_handoff(path: Path, payload: dict[str, Any]) -> str:
    assert_public_write_path_allowed(path)
    raw = pretty_json_bytes(payload)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or path.read_bytes() != raw:
            raise MissionStateError("topic_handoff_collision", "existing topic handoff differs from expected bytes")
        return "topic_handoff_reused"
    atomic_write_bytes(path, raw)
    return "topic_handoff_written"


def continue_topic_mission(*, parent_root: Path, child_root: Path) -> dict[str, Any]:
    """Create an isolated explicit-seed child from a selected topic mission."""
    parent = parent_root.absolute().resolve()
    child = child_root.absolute().resolve()
    if parent == child or _is_within(child, parent) or _is_within(parent, child):
        raise MissionStateError("topic_handoff_root_overlap", "parent and child mission roots must be disjoint")
    if child.exists() and any(child.iterdir()):
        existing = child / "topic_handoff.json"
        if existing.is_file():
            existing_parent_manager, parent_mission, parent_action, parent_data = _validate_parent(parent)
            existing_parent_manager.abort()
            payload = _read_json(existing, label="topic handoff")
            if payload.get("schema_version") != TOPIC_HANDOFF_SCHEMA or not isinstance(payload.get("parent"), dict) or not isinstance(payload.get("child"), dict):
                raise MissionStateError("topic_handoff_collision", "existing topic handoff is foreign or stale")
            parent_payload = payload.get("parent")
            child_payload = payload.get("child")
            child_control = _read_json(child / "mission_control.json", label="existing child mission control")
            child_action = _read_json(child / "next_action.json", label="existing child next action")
            child_genesis = _read_json(child / ".mission_state" / "GENESIS", label="existing child mission GENESIS")
            child_seed_rows = child_genesis.get("normalized_seeds")
            child_seed_values = [row.get("display") for row in child_seed_rows] if isinstance(child_seed_rows, list) and all(isinstance(row, dict) for row in child_seed_rows) else None
            if (
                payload.get("schema_version") != TOPIC_HANDOFF_SCHEMA
                or not isinstance(parent_payload, dict)
                or parent_payload.get("root") != str(parent)
                or parent_payload.get("mission_id") != parent_mission.get("mission_id")
                or parent_payload.get("mission_fingerprint") != parent_mission.get("mission_fingerprint")
                or parent_payload.get("generation_id") != parent_mission.get("generation_id")
                or parent_payload.get("mission_control_sha256") != sha256_bytes(canonical_json_bytes(parent_mission))
                or parent_payload.get("next_action_sha256") != sha256_bytes(canonical_json_bytes(parent_action))
                or payload.get("effective_seeds") != parent_data["seeds"]
                or child_seed_values != parent_data["seeds"]
                or not isinstance(child_payload, dict)
                or child_payload.get("root") != str(child)
                or child_payload.get("mission_id") != child_control.get("mission_id")
                or child_payload.get("mission_id") != child_action.get("mission_id")
                or child_payload.get("mission_control_sha256") != sha256_bytes(canonical_json_bytes(child_control))
                or child_payload.get("next_action_sha256") != sha256_bytes(canonical_json_bytes(child_action))
            ):
                raise MissionStateError("topic_handoff_collision", "existing topic handoff is foreign or stale")
            from research_assistant.survey.mission_plan import write_mission_plan_from_root

            write_mission_plan_from_root(mission_root=child)
            return {"status": "topic_handoff_reused", "output_dir": str(child), "handoff": payload}
        raise MissionStateError("child_output_exists", "child output must be absent or empty")
    parent_manager, parent_mission, parent_action, parent_data = _validate_parent(parent)
    parent_manager.abort()
    from research_assistant.survey.orchestrate import run_public_source_workflow

    result = run_public_source_workflow(
        topic=parent_mission["topic"],
        seeds=parent_data["seeds"],
        output_dir=child,
        run_safe_local=True,
        confirm_public_discovery=False,
        resume=False,
        force=False,
    )
    if result.get("status") not in {"ready_for_local_continuation", "blocked_at_gate", "terminal_blocked_source_intake"}:
        raise MissionStateError("child_mission_not_created", f"child mission stopped unexpectedly: {result.get('status')}")
    handoff = _handoff_payload(
        parent_root=parent,
        child_root=child,
        parent_mission=parent_mission,
        parent_action=parent_action,
        parent_data=parent_data,
        child_result=result,
        child_plan=None,
    )
    status = _write_handoff(child / "topic_handoff.json", handoff)
    from research_assistant.survey.mission_plan import write_mission_plan_from_root

    write_mission_plan_from_root(mission_root=child)
    return {"status": status, "output_dir": str(child), "child_result": result, "handoff": handoff}


__all__ = ["TOPIC_HANDOFF_SCHEMA", "continue_topic_mission"]
