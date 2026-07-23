"""Deterministic bounded state for iterative central-candidate snowballing."""

from __future__ import annotations

from typing import Any

from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, sha256_bytes


SNOWBALL_ROUND_SCHEMA = "ra-survey-centrality-snowball-round-v1"


def _fail(message: str) -> None:
    raise MissionStateError("invalid_snowball_round", message)


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        _fail(f"{field} must be a list of nonempty strings")
    rows = sorted({" ".join(item.split()).casefold() for item in value})
    if len(rows) != len(value):
        _fail(f"{field} must contain unique values")
    return rows


def build_snowball_round(
    *,
    topic_contract_sha256: str,
    round_index: int,
    prior_paper_ids: list[str],
    observed_paper_ids: list[str],
    high_or_critical_open_risk_ids: list[str],
    required_roles_covered: bool,
    backward_status: str,
    forward_status: str,
    requests_used: int,
    max_requests: int,
    max_rounds: int,
) -> dict[str, Any]:
    if type(round_index) is not int or round_index < 1 or type(max_rounds) is not int or max_rounds < 1:
        _fail("round indexes must be positive integers")
    if type(requests_used) is not int or type(max_requests) is not int or not 0 <= requests_used <= max_requests:
        _fail("request budget is invalid")
    if type(required_roles_covered) is not bool:
        _fail("required_roles_covered must be boolean")
    if backward_status not in {"available", "empty", "not_available"} or forward_status not in {"available", "empty", "not_available"}:
        _fail("snowball provider status is unsupported")
    prior = _strings(prior_paper_ids, "prior_paper_ids")
    observed = _strings(observed_paper_ids, "observed_paper_ids")
    risks = _strings(high_or_critical_open_risk_ids, "high_or_critical_open_risk_ids")
    new_ids = sorted(set(observed) - set(prior))
    budget_exhausted = requests_used >= max_requests or round_index >= max_rounds
    if budget_exhausted:
        status, reason = "stopped_budget_exhausted", "request_or_round_budget_exhausted"
    elif not new_ids and risks:
        status, reason = "blocked_open_omission_risk", "no_novelty_with_open_high_or_critical_risk"
    elif not new_ids:
        status, reason = "stopped_no_novelty", "no_new_candidate_identity"
    elif required_roles_covered and not risks:
        status, reason = "stopped_scoped_coverage_satisfied", "required_roles_covered_without_open_high_or_critical_risk"
    else:
        status, reason = "continue", "new_candidates_or_open_coverage_work"
    payload = {
        "schema_version": SNOWBALL_ROUND_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256,
        "round_index": round_index,
        "prior_paper_ids": prior,
        "observed_paper_ids": observed,
        "new_paper_ids": new_ids,
        "high_or_critical_open_risk_ids": risks,
        "required_roles_covered": required_roles_covered,
        "backward_status": backward_status,
        "forward_status": forward_status,
        "requests_used": requests_used,
        "max_requests": max_requests,
        "max_rounds": max_rounds,
        "status": status,
        "reason": reason,
        "literature_completeness_claim_allowed": False,
    }
    payload["round_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    return payload


__all__ = ["SNOWBALL_ROUND_SCHEMA", "build_snowball_round"]
