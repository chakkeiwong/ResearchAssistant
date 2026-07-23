from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.topic_continuation import TOPIC_HANDOFF_SCHEMA, continue_topic_mission


class FixtureCapability:
    name = "fixture_topic_capability"
    version = "1"

    def run(self, request: dict) -> dict:
        return {
            "schema_version": "ra-survey-topic-bootstrap-outcome-v1",
            "outcome": "selected",
            "selected_candidates": [{
                "paper_key": "arxiv:2401.00001",
                "display": "arxiv:2401.00001",
                "identifier_evidence": ["arxiv:2401.00001"],
                "title_evidence": ["Fixture paper"],
                "descriptive": {"citation_count": 10},
            }],
            "candidates": [],
            "ambiguities": [],
            "reason": None,
            "cap": None,
            "observed_count": 1,
            "descriptive": {"fixture": True},
        }


def _selected_topic(root: Path) -> None:
    run_public_source_workflow(topic="A topic", seeds=None, output_dir=root)
    run_public_source_workflow(
        topic="A topic",
        seeds=None,
        output_dir=root,
        resume=True,
        confirm_public_discovery=True,
        bootstrap_capability=FixtureCapability(),
    )


def test_continuation_transfers_selected_seeds_and_is_idempotent(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    _selected_topic(parent)

    first = continue_topic_mission(parent_root=parent, child_root=child)
    assert first["status"] == "topic_handoff_written"
    assert first["child_result"]["status"] == "blocked_at_gate"
    assert first["handoff"]["schema_version"] == TOPIC_HANDOFF_SCHEMA
    assert first["handoff"]["parent"]["root"] == str(parent)
    assert first["handoff"]["effective_seeds"] == ["arxiv:2401.00001"]
    child_genesis = json.loads((child / ".mission_state" / "GENESIS").read_text())
    assert child_genesis["normalized_seeds"] == [{"display": "arxiv:2401.00001", "key": "arxiv:2401.00001"}]
    child_plan = json.loads((child / "mission_plan.json").read_text())
    assert child_plan["topic_handoff"]["parent_mission_id"] == first["handoff"]["parent"]["mission_id"]

    second = continue_topic_mission(parent_root=parent, child_root=child)
    assert second["status"] == "topic_handoff_reused"


def test_continuation_rejects_unselected_topic_mission(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    run_public_source_workflow(topic="A topic", seeds=None, output_dir=parent)
    with pytest.raises(MissionStateError, match="selected bootstrap"):
        continue_topic_mission(parent_root=parent, child_root=tmp_path / "child")


def test_continuation_rejects_foreign_existing_handoff(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    _selected_topic(parent)
    child.mkdir()
    (child / "topic_handoff.json").write_text(json.dumps({"schema_version": TOPIC_HANDOFF_SCHEMA}))
    with pytest.raises(MissionStateError, match="foreign or stale"):
        continue_topic_mission(parent_root=parent, child_root=child)


def test_continuation_rejects_stale_existing_handoff(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    _selected_topic(parent)
    continue_topic_mission(parent_root=parent, child_root=child)
    handoff_path = child / "topic_handoff.json"
    payload = json.loads(handoff_path.read_text())
    payload["parent"]["generation_id"] = "g00000001-0000000000000000"
    handoff_path.write_text(json.dumps(payload, sort_keys=True))
    with pytest.raises(MissionStateError, match="foreign or stale"):
        continue_topic_mission(parent_root=parent, child_root=child)


def test_continuation_rejects_child_artifact_drift_on_reuse(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    _selected_topic(parent)
    continue_topic_mission(parent_root=parent, child_root=child)
    control = json.loads((child / "mission_control.json").read_text())
    control["status"] = "tampered"
    (child / "mission_control.json").write_text(json.dumps(control, sort_keys=True))
    with pytest.raises(MissionStateError, match="foreign or stale"):
        continue_topic_mission(parent_root=parent, child_root=child)
