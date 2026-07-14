from __future__ import annotations

from scripts.literature_survey_phase7_validation_harness import run_validation


def test_phase7_validation_harness_positive_and_negatives() -> None:
    result = run_validation()

    assert result["schema_version"] == "ra-literature-survey-live-public-source-phase7-validation-v1"
    assert result["status"] == "passed"
    assert result["positive"]["status"] == "passed"
    assert result["positive"]["packet_ready_for_writer"] is True
    assert result["positive"]["ready_for_prose"] is False
    assert result["positive"]["supported_claim_count"] == 0
    cases = {row["case_id"]: row for row in result["negative_cases"]}
    assert set(cases) == {
        "missing_citation_edges",
        "missing_source_support",
        "unsupported_claim_row",
        "claim_candidate_promoted",
        "missing_omission_risks",
        "raw_private_artifact_leak",
        "missing_safety_status",
        "missing_safety_rows",
        "safety_gate_falsely_cleared",
        "manifest_safety_count_drift",
        "ready_for_prose_weakened",
        "workflow_state_falsely_ready",
    }
    assert all(row["expected_signal_observed"] for row in cases.values())
    assert result["mutation_strength"]["status"] == "passed"
    assert result["mutation_strength"]["observed_negative_count"] == len(cases)
    assert result["mutation_strength"]["unobserved_case_ids"] == []
    assert set(result["mutation_strength"]["minimum_required_invariants"]).issubset(
        set(result["mutation_strength"]["target_invariants"])
    )
    assert result["boundary_contract"]["hidden_gold_used"] is False
    assert result["boundary_contract"]["external_model_or_api_used"] is False
    assert result["boundary_contract"]["positive_pass_means_final_prose_ready"] is False
    assert "product readiness" in result["what_is_not_concluded"]
