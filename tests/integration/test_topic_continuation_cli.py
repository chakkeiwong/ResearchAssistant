from __future__ import annotations

import json
from pathlib import Path

from research_assistant.cli import main
from research_assistant.survey.orchestrate import run_public_source_workflow


def test_cli_continues_selected_topic_mission(tmp_path: Path, capsys) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    run_public_source_workflow(topic="A topic", seeds=None, output_dir=parent)

    # The CLI path is exercised with the deterministic unavailable boundary;
    # it must fail closed rather than invent a selected authority.
    code = main(["survey", "continue-topic", "--mission-root", str(parent), "--out", str(child)])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "topic_parent_not_selected"
