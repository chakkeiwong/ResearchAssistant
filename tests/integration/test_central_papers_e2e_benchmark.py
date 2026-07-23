from __future__ import annotations

import json
from pathlib import Path

from research_assistant.survey.central_papers import run_central_papers_campaign
from research_assistant.survey.centrality_benchmark import evaluate_benchmark


ROOT = Path("tests/fixtures/central_papers_e2e")
CASES = {
    "federated_privacy": "Federated learning and privacy",
    "neural_optimal_transport": "Neural optimal transport",
    "particle_filtering": "Particle filtering for nonlinear state-space models",
}


def test_topic_input_campaign_passes_three_source_grounded_cases(tmp_path: Path) -> None:
    results = []
    for case_id, topic in CASES.items():
        fixture = ROOT / case_id
        output = tmp_path / case_id
        report = run_central_papers_campaign(
            topic=topic,
            output_dir=output,
            observation_bundle=fixture / "observations.json",
        )
        assessment = json.loads((output / "centrality_assessment.json").read_text())
        case = json.loads((fixture / "case.json").read_text())
        result = evaluate_benchmark(case, assessment)
        assert result["status"] == "passed", {"report": report, "result": result}
        assert result["forbidden_promotions"] == []
        assert report["benchmark_labels_consumed"] is False
        results.append(result)
    assert {result["case_id"] for result in results} == {
        "federated_privacy_topic_input",
        "neural_optimal_transport_topic_input",
        "particle_filtering_topic_input",
    }


def test_runtime_and_observation_fixtures_do_not_contain_evaluator_labels() -> None:
    runtime_files = [
        Path("src/research_assistant/survey/central_papers.py"),
        Path("src/research_assistant/survey/central_papers_capability.py"),
        Path("src/research_assistant/survey/central_papers_evidence.py"),
        Path("src/research_assistant/survey/central_papers_observations.py"),
    ]
    forbidden_runtime = [*CASES, "tests/fixtures", "must_find", "must_reject"]
    for path in runtime_files:
        text = path.read_text()
        assert not any(value in text for value in forbidden_runtime), path

    forbidden_observation_fields = {
        "case_id", "must_find", "must_reject", "required_role", "required_roles",
        "roles", "topic_fit", "verdict", "centrality",
    }
    for path in ROOT.glob("*/observations.json"):
        value = json.loads(path.read_text())
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                assert not (set(current) & forbidden_observation_fields), path
                stack.extend(current.values())
            elif isinstance(current, list):
                stack.extend(current)
