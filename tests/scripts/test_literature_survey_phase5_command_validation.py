from __future__ import annotations

from scripts.literature_survey_phase5_command_validation import run_validation


def test_phase5_command_validation_positive_and_negatives() -> None:
    result = run_validation()

    assert result["schema_version"] == "ra-literature-survey-phase5-command-validation-v1"
    assert result["status"] == "passed"
    assert result["positive"]["ready_status"] == "ready"
    assert result["positive"]["score_status"] == "passed"
    cases = {row["case_id"]: row for row in result["negative_cases"]}
    assert set(cases) == {
        "missing_backward_lineage_edge",
        "missing_source_status_row",
        "missing_classification_rows",
        "missing_supported_claim_anchor",
        "missing_omission_risks",
        "false_supported_dominance_claim",
    }
    assert all(row["expected_signal_observed"] for row in cases.values())
    assert cases["missing_classification_rows"]["ready_status"] == "blocked"
    assert cases["missing_classification_rows"]["score_status"] == "passed"
    assert cases["missing_supported_claim_anchor"]["ready_status"] == "blocked"
    assert "unsupported_technical_claim" in cases["missing_supported_claim_anchor"]["vetoes"]
    assert "forbidden_claim" in cases["false_supported_dominance_claim"]["vetoes"]
    assert result["hidden_gold_boundary"]["gold_used_only_for_scoring"] is True
    assert "product readiness" in result["what_is_not_concluded"]
