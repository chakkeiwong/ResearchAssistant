"""Transfer a replay-valid seed portfolio into an explicit-seed mission."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.seed_papers import validate_seed_paper_campaign


SEED_HANDOFF_SCHEMA = "ra-survey-seed-continuation-handoff-v1"


def _fail(code: str, message: str) -> None:
    raise MissionStateError(code, message)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            _fail("invalid_seed_handoff", f"{label} must be a regular non-symlink file")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError(
            "invalid_seed_handoff", f"{label} is not readable JSON"
        ) from exc
    if not isinstance(value, dict):
        _fail("invalid_seed_handoff", f"{label} must be an object")
    return value


def _selected_portfolio(validated: dict[str, Any]) -> tuple[str, list[str]]:
    report = validated["report"]
    if report.get("status") != "seed_candidates_selected":
        _fail("seed_campaign_not_selected", "seed campaign has no selected candidate portfolio")
    selected_ids = report.get("selected_paper_ids")
    if (
        not isinstance(selected_ids, list)
        or not selected_ids
        or any(not isinstance(value, str) or not value.strip() for value in selected_ids)
        or len(set(selected_ids)) != len(selected_ids)
    ):
        _fail("invalid_seed_handoff", "selected paper IDs are missing or duplicated")
    selected_rows = {
        row.get("paper_id"): row
        for row in report.get("candidates", [])
        if isinstance(row, dict) and row.get("paper_id") in selected_ids
    }
    if set(selected_rows) != set(selected_ids):
        _fail("invalid_seed_handoff", "selected paper IDs do not have exact candidate rows")
    for paper_id in selected_ids:
        row = selected_rows[paper_id]
        if (
            row.get("identity_status") != "resolved"
            or row.get("safety_status") == "quarantined"
            or row.get("disposition") != "SELECTED_SEED_CANDIDATE"
        ):
            _fail(
                "invalid_seed_handoff",
                f"selected candidate is conflicted, quarantined, or not selected: {paper_id}",
            )
    topic = report.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        _fail("invalid_seed_handoff", "seed report has no topic")
    return topic, list(selected_ids)


def _parent_payload(root: Path, validated: dict[str, Any], selected_ids: list[str]) -> dict[str, Any]:
    return {
        "root": str(root),
        "topic_contract_sha256": validated["campaign"]["topic_contract_sha256"],
        "seed_campaign_sha256": sha256_bytes((root / "seed_campaign.json").read_bytes()),
        "seed_report_sha256": sha256_bytes((root / "seed_report.json").read_bytes()),
        "seed_manifest_sha256": sha256_bytes((root / "seed_manifest.json").read_bytes()),
        "selected_paper_ids": selected_ids,
    }


def _child_payload(child: Path, selected_ids: list[str]) -> dict[str, Any]:
    genesis = _read_json(child / ".mission_state" / "GENESIS", label="child mission GENESIS")
    control = _read_json(child / "mission_control.json", label="child mission control")
    action = _read_json(child / "next_action.json", label="child next action")
    normalized_seeds = genesis.get("normalized_seeds")
    child_seeds = (
        [row.get("display") for row in normalized_seeds]
        if isinstance(normalized_seeds, list)
        and all(isinstance(row, dict) for row in normalized_seeds)
        else None
    )
    if child_seeds != selected_ids:
        _fail("seed_handoff_child_drift", "child mission seeds differ from selected seed IDs")
    mission_id = control.get("mission_id")
    if not isinstance(mission_id, str) or action.get("mission_id") != mission_id:
        _fail("seed_handoff_child_drift", "child mission artifacts disagree on mission identity")
    return {
        "root": str(child),
        "mission_id": mission_id,
        "mission_fingerprint": control.get("mission_fingerprint"),
        "generation_id": control.get("generation_id"),
        "genesis_sha256": sha256_bytes((child / ".mission_state" / "GENESIS").read_bytes()),
        "mission_control_sha256": sha256_bytes((child / "mission_control.json").read_bytes()),
        "next_action_sha256": sha256_bytes((child / "next_action.json").read_bytes()),
        "result_status": control.get("status"),
    }


def _expected_handoff(
    *,
    parent: Path,
    child: Path,
    validated: dict[str, Any],
    selected_ids: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SEED_HANDOFF_SCHEMA,
        "parent": _parent_payload(parent, validated, selected_ids),
        "child": _child_payload(child, selected_ids),
        "selected_paper_ids": selected_ids,
        "handoff_boundary": (
            "metadata nominations transferred; source acquisition, source safety, technical "
            "inspection, snowballing, claim support, human review, and hostile review remain downstream"
        ),
        "what_is_not_concluded": [
            "canonical best paper",
            "literature completeness",
            "paper correctness",
            "publication readiness",
            "source availability or safety",
            "topic centrality",
            "universal topic recall",
        ],
    }


def continue_seed_paper_campaign(
    *,
    seed_campaign_root: Path,
    child_root: Path,
    venue_metrics_registry: Path | None = None,
) -> dict[str, Any]:
    """Create or validate an explicit-seed child from a completed campaign."""
    parent = seed_campaign_root.absolute().resolve()
    child = child_root.absolute().resolve()
    if parent == child or _is_within(child, parent) or _is_within(parent, child):
        _fail("seed_handoff_root_overlap", "seed campaign and child roots must be disjoint")
    validated = validate_seed_paper_campaign(
        parent,
        venue_metrics_registry=venue_metrics_registry,
    )
    topic, selected_ids = _selected_portfolio(validated)
    handoff_path = child / "seed_handoff.json"
    if child.exists() and any(child.iterdir()):
        if not handoff_path.is_file():
            _fail("seed_handoff_child_exists", "child output must be absent, empty, or a matching handoff")
        recorded = _read_json(handoff_path, label="seed handoff")
        expected = _expected_handoff(
            parent=parent,
            child=child,
            validated=validated,
            selected_ids=selected_ids,
        )
        if recorded != expected:
            _fail("seed_handoff_collision", "existing seed handoff is foreign, stale, or tampered")
        return {"status": "seed_handoff_reused", "output_dir": str(child), "handoff": recorded}

    from research_assistant.survey.orchestrate import run_public_source_workflow

    result = run_public_source_workflow(
        topic=topic,
        seeds=selected_ids,
        output_dir=child,
        run_safe_local=True,
        confirm_public_discovery=False,
        resume=False,
        force=False,
    )
    if result.get("status") not in {
        "ready_for_local_continuation",
        "blocked_at_gate",
        "terminal_blocked_source_intake",
    }:
        _fail("seed_handoff_child_not_created", f"child mission stopped unexpectedly: {result.get('status')}")
    handoff = _expected_handoff(
        parent=parent,
        child=child,
        validated=validated,
        selected_ids=selected_ids,
    )
    assert_public_write_path_allowed(handoff_path)
    if handoff_path.exists() or handoff_path.is_symlink():
        _fail("seed_handoff_collision", "seed handoff path was created concurrently")
    atomic_write_bytes(handoff_path, pretty_json_bytes(handoff))
    return {
        "status": "seed_handoff_written",
        "output_dir": str(child),
        "child_result": result,
        "handoff": handoff,
    }


__all__ = ["SEED_HANDOFF_SCHEMA", "continue_seed_paper_campaign"]
