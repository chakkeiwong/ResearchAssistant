from __future__ import annotations

import json
from pathlib import Path

from research_assistant.benchmarks.surveybench import score_survey_task


ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tests" / "fixtures" / "surveybench" / "tasks" / "neural_ot_seed_synthetic.task.json"
PROMPT_PACKET = ROOT / "docs" / "validation" / "surveybench_agent_trial_prompt_packet_2026-06-28.md"
OUTPUT_DIR = ROOT / "tests" / "fixtures" / "surveybench" / "agent_trial" / "neural_ot_seed_codex_style_output"


def test_agent_trial_prompt_packet_is_offline_and_cli_scored() -> None:
    text = PROMPT_PACKET.read_text()
    assert "PYTHONPATH=src python -m research_assistant.cli surveybench run" in text
    assert "live web search" in text
    assert "Do not write survey prose" in text
    assert "<OUTPUT_DIR>" in text


def test_agent_trial_output_scores_as_machine_checkable_packet() -> None:
    expected_files = {
        "expected_citation_map.json",
        "expected_candidate_ledger.json",
        "expected_source_support.json",
        "expected_claim_support.json",
        "expected_omission_risk.json",
    }
    assert expected_files <= {path.name for path in OUTPUT_DIR.glob("*.json")}

    report = score_survey_task(TASK, actual_dir=OUTPUT_DIR)

    assert report["schema_version"] == "ra-surveybench-report-v1"
    assert report["status"] == "passed"
    assert report["vetoes"] == []
    assert report["errors"] == []
    assert json.loads((OUTPUT_DIR / "expected_citation_map.json").read_text())["schema_version"] == "ra-surveybench-citation-map-v1"
