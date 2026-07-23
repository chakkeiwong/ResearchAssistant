from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.cli import main
from research_assistant.survey.orchestrate import run_public_source_workflow


def test_mission_plan_cli_writes_bound_read_only_view(tmp_path: Path, capsys) -> None:
    source = tmp_path / "mission"
    run_public_source_workflow(topic="A topic", seeds=["arxiv:2401.00001"], output_dir=source, run_safe_local=True)
    output = source / "mission_plan.json"
    code = main(["survey", "mission-plan", "--mission-root", str(source)])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] in {"mission_plan_written", "mission_plan_reused"}
    plan = json.loads(output.read_text())
    assert plan["mission_id"] == payload["plan"]["mission_id"]
    assert plan["current_stage"] == "source_resolution"
