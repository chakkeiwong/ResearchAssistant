from research_assistant.survey.snowball_round import build_snowball_round


def _round(**overrides):
    values = {
        "topic_contract_sha256": "a" * 64,
        "round_index": 1,
        "prior_paper_ids": ["a"],
        "observed_paper_ids": ["a", "b"],
        "high_or_critical_open_risk_ids": ["risk"],
        "required_roles_covered": False,
        "backward_status": "available",
        "forward_status": "not_available",
        "requests_used": 2,
        "max_requests": 10,
        "max_rounds": 3,
    }
    values.update(overrides)
    return build_snowball_round(**values)


def test_round_continues_for_new_candidates_or_open_work() -> None:
    result = _round()
    assert result["status"] == "continue"
    assert result["new_paper_ids"] == ["b"]
    assert result["literature_completeness_claim_allowed"] is False


def test_round_stops_for_no_novelty_without_claiming_completeness() -> None:
    result = _round(observed_paper_ids=["a"], high_or_critical_open_risk_ids=[])
    assert result["status"] == "stopped_no_novelty"
    assert result["literature_completeness_claim_allowed"] is False


def test_round_keeps_open_risk_visible_and_budget_has_precedence() -> None:
    blocked = _round(observed_paper_ids=["a"])
    assert blocked["status"] == "blocked_open_omission_risk"
    exhausted = _round(requests_used=10)
    assert exhausted["status"] == "stopped_budget_exhausted"
