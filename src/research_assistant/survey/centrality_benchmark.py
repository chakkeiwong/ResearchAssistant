"""Evaluator-owned exact gate for generic centrality benchmark cases."""

from __future__ import annotations

from typing import Any

from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, sha256_bytes


BENCHMARK_CASE_SCHEMA = "ra-survey-centrality-benchmark-case-v1"
BENCHMARK_RESULT_SCHEMA = "ra-survey-centrality-benchmark-result-v1"


def _fail(message: str) -> None:
    raise MissionStateError("invalid_centrality_benchmark", message)


def evaluate_benchmark(case: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    expected = {"schema_version", "case_id", "topic_contract_sha256", "must_find", "must_reject", "required_roles", "review_provenance", "what_is_not_concluded"}
    if not isinstance(case, dict) or set(case) != expected or case.get("schema_version") != BENCHMARK_CASE_SCHEMA:
        _fail("benchmark case fields or schema are invalid")
    if assessment.get("schema_version") != "ra-survey-centrality-assessment-v1":
        _fail("assessment schema is unsupported")
    if assessment.get("topic_contract_sha256") != case.get("topic_contract_sha256"):
        _fail("benchmark case and assessment topic contracts differ")
    rows = assessment.get("assessments")
    if not isinstance(rows, list):
        _fail("assessment rows are invalid")
    by_id = {row.get("paper_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != len(rows):
        _fail("assessment paper IDs are invalid or duplicated")
    must_find_results = []
    for expected_row in case["must_find"]:
        if not isinstance(expected_row, dict) or set(expected_row) != {"paper_id", "required_role", "source_block_allowed"}:
            _fail("must_find row is invalid")
        row = by_id.get(expected_row["paper_id"])
        verdict = row.get("verdict") if row else None
        role_ok = bool(row and expected_row["required_role"] in row.get("roles", []))
        pass_status = bool(
            row and role_ok and (
                verdict == "VALIDATED_CENTRAL"
                or (expected_row["source_block_allowed"] is True and verdict == "BLOCKED")
            )
        )
        must_find_results.append({**expected_row, "observed_verdict": verdict, "role_present": role_ok, "passed": pass_status})
    must_reject_results = []
    allowed_rejects = {"PERIPHERAL", "QUARANTINED", "REJECTED_OFF_TOPIC"}
    for paper_id in case["must_reject"]:
        row = by_id.get(paper_id)
        verdict = row.get("verdict") if row else None
        must_reject_results.append({"paper_id": paper_id, "observed_verdict": verdict, "passed": verdict in allowed_rejects})
    forbidden = [
        row["paper_id"] for row in rows
        if row.get("verdict") == "VALIDATED_CENTRAL" and (
            row.get("hard_vetoes") or not row.get("requirements", {}).get("primary_source_inspected")
        )
    ]
    role_status = {
        role: any(row["passed"] and row["required_role"] == role for row in must_find_results)
        for role in sorted(case["required_roles"])
    }
    passed = (
        all(row["passed"] for row in must_find_results)
        and all(row["passed"] for row in must_reject_results)
        and all(role_status.values())
        and not forbidden
    )
    payload = {
        "schema_version": BENCHMARK_RESULT_SCHEMA,
        "case_id": case["case_id"],
        "status": "passed" if passed else "failed",
        "must_find_results": must_find_results,
        "must_reject_results": must_reject_results,
        "required_role_status": role_status,
        "forbidden_promotions": sorted(forbidden),
        "ranking_statistically_supported": False,
        "descriptive_ranking_used_for_pass": False,
        "what_is_not_concluded": ["literature completeness", "performance on unreviewed topics", "paper claim correctness"],
    }
    payload["result_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    return payload


__all__ = ["BENCHMARK_CASE_SCHEMA", "BENCHMARK_RESULT_SCHEMA", "evaluate_benchmark"]
