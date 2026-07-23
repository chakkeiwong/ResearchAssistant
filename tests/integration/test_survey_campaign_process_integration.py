import json
from pathlib import Path

from research_assistant.survey.campaign_process import write_process_plan


def test_baseline_fixture_writes_bounded_process_artifacts(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/survey_campaign_process/baseline.json")
    result = write_process_plan(fixture, tmp_path)
    assert result["status"] == "process_plan_written"
    plan = json.loads((tmp_path / "process_plan.json").read_text())
    coverage = json.loads((tmp_path / "coverage_preflight.json").read_text())
    availability = json.loads((tmp_path / "availability_preflight.json").read_text())
    assert plan["next_action"]["action_id"] == "resolve_must_cite_source"
    assert plan["selection_summary"] == {
        "selected_count": 12,
        "retained_count": 5,
        "substitution_count": 2,
        "unreplaced_count": 7,
    }
    assert coverage["gap_count"] >= 1
    assert availability["access_or_omission_count"] == 7
