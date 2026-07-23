from research_assistant.survey.centrality_benchmark import evaluate_benchmark


def _assessment() -> dict:
    def row(paper_id: str, verdict: str, roles: list[str], *, vetoes=None, inspected=True):
        return {
            "paper_id": paper_id,
            "verdict": verdict,
            "roles": roles,
            "hard_vetoes": vetoes or [],
            "requirements": {"primary_source_inspected": inspected},
        }
    return {
        "schema_version": "ra-survey-centrality-assessment-v1",
        "topic_contract_sha256": "a" * 64,
        "assessments": [
            row("direct", "VALIDATED_CENTRAL", ["DIRECT_METHOD"]),
            row("foundation", "VALIDATED_CENTRAL", ["FOUNDATIONAL"]),
            row("off_topic", "REJECTED_OFF_TOPIC", ["BACKGROUND"], vetoes=["off_topic"]),
        ],
    }


def _case() -> dict:
    return {
        "schema_version": "ra-survey-centrality-benchmark-case-v1",
        "case_id": "case",
        "topic_contract_sha256": "a" * 64,
        "must_find": [
            {"paper_id": "direct", "required_role": "DIRECT_METHOD", "source_block_allowed": False},
            {"paper_id": "foundation", "required_role": "FOUNDATIONAL", "source_block_allowed": False},
        ],
        "must_reject": ["off_topic"],
        "required_roles": ["DIRECT_METHOD", "FOUNDATIONAL"],
        "review_provenance": ["review:fixture"],
        "what_is_not_concluded": ["literature completeness"],
    }


def test_exact_benchmark_gate_passes_without_rank_claim() -> None:
    result = evaluate_benchmark(_case(), _assessment())
    assert result["status"] == "passed"
    assert result["descriptive_ranking_used_for_pass"] is False
    assert result["ranking_statistically_supported"] is False


def test_benchmark_gate_fails_missed_positive_and_false_inclusion() -> None:
    assessment = _assessment()
    assessment["assessments"][0]["verdict"] = "VALIDATED_RELEVANT"
    assessment["assessments"][2]["verdict"] = "VALIDATED_CENTRAL"
    result = evaluate_benchmark(_case(), assessment)
    assert result["status"] == "failed"
    assert not result["must_find_results"][0]["passed"]
    assert not result["must_reject_results"][0]["passed"]
