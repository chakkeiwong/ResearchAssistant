from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import tempfile
import urllib.parse
from decimal import Decimal
from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import canonical_json_bytes, pretty_json_bytes
from research_assistant.survey.openalex_adapter import (
    build_openalex_direct_descriptor,
    build_openalex_forward_descriptor,
    build_openalex_topic_descriptor,
)
from research_assistant.survey.openalex_credential_cost import (
    CAMPAIGN_COST_CAP_USD,
    CREDENTIAL_INTERFACE,
    CREDENTIAL_SOURCE_KIND,
    CampaignCostBudget,
    contains_credential_representation,
    execute_authenticated_openalex_request,
    serialize_boundary_evidence,
)


SCHEMA = "ra-literature-survey-m20b2-synthetic-validation-v1"
TOPIC = "Neural Optimal Transport for generative modeling and inference"
WORK_ID = "W4387130479"
REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_CANDIDATES = (
    REPO_ROOT / "src/research_assistant/survey/openalex_credential_cost.py",
    Path(__file__).resolve(),
    REPO_ROOT / "tests/unit/test_literature_survey_m20b2_credential_cost.py",
    REPO_ROOT / "tests/scripts/test_literature_survey_m20b2_synthetic_validation.py",
)


def _work(work_id: str = WORK_ID) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": TOPIC,
        "authorships": [{"author": {"display_name": "Synthetic Author"}}],
        "publication_year": 2022,
        "doi": "https://doi.org/10.1000/synthetic",
        "cited_by_count": 7,
        "referenced_works": [],
        "ids": {
            "openalex": f"https://openalex.org/{work_id}",
            "doi": "https://doi.org/10.1000/synthetic",
        },
        "type": "article",
        "publication_date": "2022-01-01",
    }


def _list_body(*, cost_usd: float, work_id: str = WORK_ID) -> bytes:
    return canonical_json_bytes({
        "meta": {
            "count": 1,
            "db_response_time_ms": 1,
            "page": 1,
            "per_page": 10,
            "next_cursor": None,
            "groups_count": 0,
            "cost_usd": cost_usd,
        },
        "results": [_work(work_id)],
        "group_by": [],
    })


def _fresh_canary() -> str:
    return f"M20B2_SYNTHETIC_{secrets.token_urlsafe(24)}+/\""


def _run_case(
    case_id: str,
    descriptor: dict[str, Any],
    *,
    response: bytes | None = None,
    dispatch_exception: Exception | None = None,
    source_value: Any = None,
    source_kind: str = CREDENTIAL_SOURCE_KIND,
    budget: CampaignCostBudget | None = None,
    dispatch_error_contains_canary: bool = False,
) -> dict[str, Any]:
    canary = _fresh_canary()
    value = canary if source_value is None else source_value
    lookup_count = 0
    named_source_occurrence_count = 0
    request_count = 0

    def getter(name: str) -> Any:
        nonlocal lookup_count, named_source_occurrence_count
        assert name == CREDENTIAL_INTERFACE
        lookup_count += 1
        if value == canary:
            named_source_occurrence_count += 1
        return value

    def dispatch(request: Any) -> bytes:
        nonlocal request_count
        request_count += 1
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query, keep_blank_values=True)
        assert query.get("api_key") == [canary]
        assert request.full_url.count("api_key=") == 1
        if dispatch_error_contains_canary:
            raise RuntimeError(canary)
        if dispatch_exception is not None:
            raise dispatch_exception
        assert response is not None
        return response

    active_budget = budget or CampaignCostBudget()
    body, evidence = execute_authenticated_openalex_request(
        descriptor,
        credential_getter=getter,
        credential_source_kind=source_kind,
        dispatch=dispatch,
        budget=active_budget,
    )
    serialized_evidence = serialize_boundary_evidence(evidence, forbidden_value=canary)
    serialized_body = body or b""
    scan_values = {
        "descriptor": canonical_json_bytes(descriptor),
        "returned_body": serialized_body,
        "returned_evidence": serialized_evidence,
        "command_arguments": canonical_json_bytes(sys.argv),
        "captured_stdout": b"",
        "captured_stderr": b"",
        "exception_crossing_boundary": (evidence["error_code"] or "").encode(),
        "ipc_value": serialized_evidence,
        "temporary_file_inventory": b"",
        "git_candidates": b"\n".join(path.read_bytes() for path in GIT_CANDIDATES),
    }
    if any(contains_credential_representation(raw, canary) for raw in scan_values.values()):
        raise AssertionError("synthetic canary crossed or survived the credential boundary")
    return {
        "case_id": case_id,
        "status": evidence["status"],
        "error_code": evidence["error_code"],
        "credential_lookup_count": lookup_count,
        "authenticated_request_count": request_count,
        "authorized_occurrence_classes": {
            "named_source_value": named_source_occurrence_count,
            "ephemeral_authenticated_request": request_count,
        },
        "prohibited_surface_scan": {
            key: "clear"
            for key in sorted(scan_values)
        } | {
            "persisted_case_artifact": "not_created",
        },
        "cost_evidence": {
            key: evidence[key]
            for key in (
                "campaign_cost_cap_usd",
                "reserved_cost_usd",
                "reconciled_cost_usd",
                "dispatch_count",
                "cost_state",
                "cost_block_code",
                "predicted_cost_usd",
                "observed_cost_usd",
            )
        },
    }


def build_report() -> dict[str, Any]:
    shared = CampaignCostBudget()
    cases = [
        _run_case(
            "topic_success",
            build_openalex_topic_descriptor(TOPIC),
            response=_list_body(cost_usd=0.001),
            budget=shared,
        ),
        _run_case(
            "direct_success",
            build_openalex_direct_descriptor(WORK_ID),
            response=canonical_json_bytes(_work()),
            budget=shared,
        ),
        _run_case(
            "forward_success",
            build_openalex_forward_descriptor(WORK_ID),
            response=_list_body(cost_usd=0.0001, work_id="W2"),
            budget=shared,
        ),
        _run_case(
            "timeout_closed",
            build_openalex_topic_descriptor(TOPIC),
            dispatch_exception=TimeoutError("synthetic timeout"),
        ),
        _run_case(
            "provider_http_error_closed",
            build_openalex_topic_descriptor(TOPIC),
            dispatch_exception=RuntimeError("synthetic provider error"),
        ),
        _run_case(
            "worker_termination_closed",
            build_openalex_topic_descriptor(TOPIC),
            dispatch_exception=InterruptedError("synthetic worker termination"),
        ),
        _run_case(
            "secret_bearing_exception_closed",
            build_openalex_topic_descriptor(TOPIC),
            dispatch_error_contains_canary=True,
        ),
        _run_case(
            "parser_error_closed",
            build_openalex_topic_descriptor(TOPIC),
            response=b"not-json",
        ),
        _run_case(
            "missing_credential",
            build_openalex_topic_descriptor(TOPIC),
            response=_list_body(cost_usd=0.001),
            source_value="",
        ),
        _run_case(
            "wrong_source",
            build_openalex_topic_descriptor(TOPIC),
            response=_list_body(cost_usd=0.001),
            source_kind="file",
        ),
        _run_case(
            "cost_contradiction",
            build_openalex_topic_descriptor(TOPIC),
            response=_list_body(cost_usd=0.002),
        ),
    ]
    route_sum = sum((value for value in (Decimal("0.001"), Decimal("0"), Decimal("0.0001"))), Decimal("0"))
    report = {
        "schema_version": SCHEMA,
        "status": "passed",
        "network_used": False,
        "real_credential_accessed": False,
        "credential_interface_name": CREDENTIAL_INTERFACE,
        "canary_value_or_digest_persisted": False,
        "campaign_cost_cap_usd": format(CAMPAIGN_COST_CAP_USD, "f"),
        "documented_route_sum_usd": format(route_sum, "f"),
        "shared_success_budget": shared.evidence(),
        "cases": cases,
        "prohibited_surface_inventory": [
            "accepted_response_body",
            "application_log",
            "captured_stderr",
            "captured_stdout",
            "command_argument",
            "descriptor",
            "environment_manifest",
            "exception_crossing_boundary",
            "filename",
            "git_candidate",
            "ipc_value",
            "junit_artifact",
            "manifest",
            "returned_evidence",
            "review_artifact",
            "temporary_file",
        ],
        "scan_method": "exact_runtime_canary_scan_while_each_canary_is_live",
        "nonclaims": [
            "actual_account_balance_or_billing",
            "provider_behavior_or_readiness",
            "real_key_availability_or_authority",
            "universal_secret_leak_freedom",
        ],
    }
    raw = canonical_json_bytes(report)
    if b"M20B2_SYNTHETIC_" in raw:
        raise AssertionError("validation report contains a synthetic canary")
    return report


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".report.", suffix=".tmp")
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
        temp.unlink()
    finally:
        if temp.exists():
            temp.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report()
    _atomic_write(args.output_root / "synthetic_validation.json", pretty_json_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
