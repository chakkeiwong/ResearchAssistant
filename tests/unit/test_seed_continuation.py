from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.seed_continuation import (
    SEED_HANDOFF_SCHEMA,
    continue_seed_paper_campaign,
)
from research_assistant.survey.seed_papers import run_seed_paper_campaign


FIXTURES = Path("tests/fixtures/seed_papers_benchmark")


def _campaign(tmp_path: Path) -> Path:
    cases = json.loads((FIXTURES / "cases.json").read_text())
    bundles = json.loads((FIXTURES / "raw_bundles.json").read_text())
    case = cases["causal_inference"]
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(bundles["causal_inference"]))
    root = tmp_path / "campaign"
    run_seed_paper_campaign(
        topic=case["topic"],
        output_dir=root,
        observation_bundle=bundle,
    )
    return root


def test_seed_campaign_handoff_is_exact_and_idempotent(tmp_path: Path) -> None:
    parent = _campaign(tmp_path)
    child = tmp_path / "child"
    first = continue_seed_paper_campaign(seed_campaign_root=parent, child_root=child)
    assert first["status"] == "seed_handoff_written"
    assert first["handoff"]["schema_version"] == SEED_HANDOFF_SCHEMA
    assert first["handoff"]["selected_paper_ids"] == ["doi:10.1000/causal-iv"]
    assert first["child_result"]["status"] == "blocked_at_gate"
    genesis = json.loads((child / ".mission_state" / "GENESIS").read_text())
    assert genesis["normalized_seeds"] == [{
        "display": "doi:10.1000/causal-iv", "key": "doi:10.1000/causal-iv"
    }]
    second = continue_seed_paper_campaign(seed_campaign_root=parent, child_root=child)
    assert second["status"] == "seed_handoff_reused"


def test_seed_handoff_rejects_parent_and_child_tampering(tmp_path: Path) -> None:
    parent = _campaign(tmp_path)
    child = tmp_path / "child"
    continue_seed_paper_campaign(seed_campaign_root=parent, child_root=child)
    control = json.loads((child / "mission_control.json").read_text())
    control["status"] = "tampered"
    (child / "mission_control.json").write_text(json.dumps(control))
    with pytest.raises(MissionStateError, match="foreign, stale, or tampered"):
        continue_seed_paper_campaign(seed_campaign_root=parent, child_root=child)

    report = json.loads((parent / "seed_report.json").read_text())
    report["topic"] = "another topic"
    (parent / "seed_report.json").write_text(json.dumps(report))
    with pytest.raises(MissionStateError, match="differs from replay"):
        continue_seed_paper_campaign(
            seed_campaign_root=parent,
            child_root=tmp_path / "other-child",
        )


def test_seed_handoff_rejects_overlapping_or_foreign_child(tmp_path: Path) -> None:
    parent = _campaign(tmp_path)
    with pytest.raises(MissionStateError, match="must be disjoint"):
        continue_seed_paper_campaign(
            seed_campaign_root=parent,
            child_root=parent / "child",
        )
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "unrelated.txt").write_text("not a mission")
    with pytest.raises(MissionStateError, match="child output"):
        continue_seed_paper_campaign(seed_campaign_root=parent, child_root=foreign)
