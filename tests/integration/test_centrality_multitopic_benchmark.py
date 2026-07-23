from __future__ import annotations

import json
from pathlib import Path

from research_assistant.survey.centrality import assess_centrality
from research_assistant.survey.centrality_benchmark import evaluate_benchmark


ROOT = Path("tests/fixtures/centrality_benchmark")
CASES = ("neural_optimal_transport", "particle_filtering", "federated_privacy")


def test_multitopic_source_grounded_benchmark_passes_exact_gate() -> None:
    results = []
    for case_id in CASES:
        root = ROOT / case_id
        contract = json.loads((root / "topic_contract.json").read_text())
        evidence = json.loads((root / "evidence.json").read_text())
        case = json.loads((root / "case.json").read_text())
        assessment = assess_centrality(contract, evidence)
        result = evaluate_benchmark(case, assessment)
        assert result["status"] == "passed", result
        assert result["forbidden_promotions"] == []
        assert all(row["passed"] for row in result["must_reject_results"])
        results.append(result)
    assert {result["case_id"] for result in results} == set(CASES)


def test_runtime_centrality_modules_do_not_reference_benchmark_labels() -> None:
    runtime_files = [
        Path("src/research_assistant/survey/centrality.py"),
        Path("src/research_assistant/survey/topic_contract.py"),
        Path("src/research_assistant/survey/snowball_round.py"),
    ]
    forbidden = [*CASES, "tests/fixtures", "centrality_benchmark"]
    for path in runtime_files:
        text = path.read_text()
        assert not any(value in text for value in forbidden), (path, forbidden)
