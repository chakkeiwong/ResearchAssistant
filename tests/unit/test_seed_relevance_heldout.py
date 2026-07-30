from __future__ import annotations

import json
from pathlib import Path

from scripts.evaluate_seed_relevance_heldout import evaluate


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "seed_papers_benchmark" / "heldout_relevance.json"


def test_heldout_evaluation_is_descriptive_and_label_free_at_runtime() -> None:
    result = evaluate(FIXTURE)
    assert result["status"] == "descriptive_heldout_evaluation"
    assert result["case_count"] == 8
    assert set(result["confusion_matrix"]) == {"auto_select", "review", "reject"}
    assert result["benchmark_labels_consumed"] is False
    assert result["production_thresholds_changed"] is False
    assert result["what_is_not_concluded"]


def test_heldout_result_is_replayable() -> None:
    first = evaluate(FIXTURE)
    second = evaluate(FIXTURE)
    assert first == second


def test_production_does_not_embed_heldout_labels_or_case_ids() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/research_assistant").rglob("*.py")
    )
    assert "exact_graph_molecular" not in source
    assert "contaminated_metadata_dump" not in source
    assert "label_basis" not in source
