from __future__ import annotations

import copy
import json
import secrets
import threading
import urllib.parse
from decimal import Decimal
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import canonical_json_bytes
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
    CredentialCostBoundaryError,
    ROUTE_COST_USD,
    contains_credential_representation,
    execute_authenticated_openalex_request,
    serialize_boundary_evidence,
)


TOPIC = "Neural Optimal Transport for generative modeling and inference"
WORK_ID = "W4387130479"


def _canary() -> str:
    return f"M20B2_TEST_{secrets.token_urlsafe(24)}+/\""


def _work(work_id: str = WORK_ID) -> dict:
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


def _list_body(cost: object, *, work_id: str = WORK_ID) -> bytes:
    return canonical_json_bytes({
        "meta": {
            "count": 1,
            "db_response_time_ms": 1,
            "page": 1,
            "per_page": 10,
            "next_cursor": None,
            "groups_count": 0,
            "cost_usd": cost,
        },
        "results": [_work(work_id)],
        "group_by": [],
    })


def _execute(descriptor, *, canary: str, response: bytes, budget=None, source_kind=CREDENTIAL_SOURCE_KIND):  # noqa: ANN001
    lookups = []
    observations = []

    def getter(name: str) -> str:
        lookups.append(name)
        return canary

    def dispatch(request):  # noqa: ANN001, ANN202
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        observations.append({
            "api_key_matches": query.get("api_key") == [canary],
            "api_key_parameter_count": request.full_url.count("api_key="),
        })
        return response

    body, evidence = execute_authenticated_openalex_request(
        descriptor,
        credential_getter=getter,
        credential_source_kind=source_kind,
        dispatch=dispatch,
        budget=budget or CampaignCostBudget(),
    )
    return body, evidence, lookups, observations


def _assert_canary_absent(canary: str, *values: object) -> None:
    for value in values:
        if isinstance(value, bytes):
            assert canary.encode() not in value
        else:
            assert canary not in json.dumps(value, sort_keys=True, default=str)


def test_cost_schedule_and_human_cap_are_exact() -> None:
    assert CREDENTIAL_INTERFACE == "OPENALEX_API_KEY"
    assert CREDENTIAL_SOURCE_KIND == "environment"
    assert CAMPAIGN_COST_CAP_USD == Decimal("0.01")
    assert ROUTE_COST_USD == {
        "topic_list": Decimal("0.001"),
        "direct_singleton": Decimal("0"),
        "forward_list": Decimal("0.0001"),
    }
    assert sum(ROUTE_COST_USD.values(), Decimal("0")) == Decimal("0.0011")
    with pytest.raises(CredentialCostBoundaryError, match="campaign_cost_cap_differs"):
        CampaignCostBudget(cap_usd=Decimal("0.02"))


def test_descriptor_and_cost_preflight_precede_credential_lookup() -> None:
    descriptor = build_openalex_topic_descriptor(TOPIC)
    descriptor["ordered_query_parameters"].append(["api_key", "synthetic"])
    called = []
    body, evidence = execute_authenticated_openalex_request(
        descriptor,
        credential_getter=lambda name: called.append(name),
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(AssertionError(request)),
        budget=CampaignCostBudget(),
    )
    assert body is None
    assert evidence["status"] == "blocked_preflight"
    assert evidence["credential_present"] is False
    assert called == []

    budget = CampaignCostBudget()
    for _ in range(10):
        body, evidence, _, _ = _execute(
            build_openalex_topic_descriptor(TOPIC),
            canary=_canary(),
            response=_list_body(0.001),
            budget=budget,
        )
        assert body is not None
        assert evidence["status"] == "completed"
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: called.append(name),
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(AssertionError(request)),
        budget=budget,
    )
    assert body is None
    assert evidence["status"] == "blocked_preflight"
    assert called == []


def test_budget_state_is_read_only_and_invalid_internal_state_fails_closed() -> None:
    budget = CampaignCostBudget()
    with pytest.raises(AttributeError):
        budget.reserved_usd = Decimal("0.001")

    corruptions = [
        ("_reserved_usd", Decimal("-0.001")),
        ("_reserved_usd", Decimal("NaN")),
        ("_reserved_usd", Decimal("0.02")),
        ("_reserved_usd", "0"),
        ("_reconciled_usd", Decimal("0.001")),
        ("_cap_usd", Decimal("0.02")),
        ("_cap_usd", Decimal("NaN")),
        ("_dispatch_count", -1),
        ("_dispatch_count", True),
        ("_blocked", "yes"),
        ("_block_code", "orphan_code"),
        ("_dispatch_in_flight", "yes"),
        ("_version", -1),
    ]
    for field, value in corruptions:
        corrupted = CampaignCostBudget()
        object.__setattr__(corrupted, field, value)
        getter_calls = []
        dispatch_calls = []
        body, evidence = execute_authenticated_openalex_request(
            build_openalex_topic_descriptor(TOPIC),
            credential_getter=lambda name: getter_calls.append(name),
            credential_source_kind=CREDENTIAL_SOURCE_KIND,
            dispatch=lambda request: dispatch_calls.append(request),
            budget=corrupted,
        )
        assert body is None
        assert evidence["status"] == "blocked_preflight"
        assert evidence["error_code"] == "descriptor_or_cost_preflight_invalid"
        assert evidence["cost_state"] == "blocked"
        assert evidence["cost_block_code"] == "invalid_cost_state"
        assert getter_calls == []
        assert dispatch_calls == []


def test_invalid_budget_object_fails_closed_before_lookup() -> None:
    getter_calls = []
    dispatch_calls = []
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: getter_calls.append(name),
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: dispatch_calls.append(request),
        budget=object(),
    )
    assert body is None
    assert evidence["status"] == "blocked_preflight"
    assert evidence["error_code"] == "invalid_cost_budget"
    assert getter_calls == []
    assert dispatch_calls == []


def test_success_has_one_ephemeral_authenticated_request_and_safe_evidence() -> None:
    canary = _canary()
    descriptor = build_openalex_topic_descriptor(TOPIC)
    frozen = copy.deepcopy(descriptor)
    response = _list_body(0.001)
    body, evidence, lookups, observations = _execute(
        descriptor,
        canary=canary,
        response=response,
    )
    assert descriptor == frozen
    assert lookups == [CREDENTIAL_INTERFACE]
    assert observations == [{"api_key_matches": True, "api_key_parameter_count": 1}]
    assert body == response
    assert evidence["status"] == "completed"
    assert evidence["predicted_cost_usd"] == "0.001"
    assert evidence["observed_cost_usd"] == "0.001"
    assert evidence["credential_persisted"] is False
    assert evidence["authenticated_url_persisted"] is False
    _assert_canary_absent(canary, body, evidence)


@pytest.mark.parametrize("value", [None, "", " leading", "trailing ", "has space", "x\n", ["a", "b"], {"a": "b"}])
def test_invalid_or_ambiguous_credentials_fail_before_dispatch(value: object) -> None:
    calls = []
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: value,
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: calls.append(request),
        budget=CampaignCostBudget(),
    )
    assert body is None
    assert evidence["status"] == "blocked_before_dispatch"
    assert evidence["error_code"] in {"invalid_credential", "ambiguous_credential"}
    assert evidence["dispatch_count"] == 0
    assert calls == []


def test_wrong_source_fails_without_calling_getter() -> None:
    called = []
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: called.append(name),
        credential_source_kind="file",
        dispatch=lambda request: (_ for _ in ()).throw(AssertionError(request)),
        budget=CampaignCostBudget(),
    )
    assert body is None
    assert evidence["error_code"] == "wrong_credential_source"
    assert called == []


def test_lookup_and_dispatch_exceptions_never_cross_boundary() -> None:
    canary = _canary()
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: (_ for _ in ()).throw(RuntimeError(canary)),
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(AssertionError(request)),
        budget=CampaignCostBudget(),
    )
    assert body is None
    assert evidence["error_code"] == "credential_lookup_failed"
    _assert_canary_absent(canary, evidence)

    budget = CampaignCostBudget()
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: canary,
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(TimeoutError(canary)),
        budget=budget,
    )
    assert body is None
    assert evidence["error_code"] == "dispatch_failed_closed"
    assert evidence["cost_state"] == "blocked"
    assert evidence["cost_block_code"] == "dispatch_cost_unreconciled"
    _assert_canary_absent(canary, evidence)


def test_unreconciled_dispatch_poisoning_blocks_subsequent_lookup() -> None:
    canary = _canary()
    budget = CampaignCostBudget()
    execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: canary,
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(TimeoutError("closed")),
        budget=budget,
    )
    called = []
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_direct_descriptor(WORK_ID),
        credential_getter=lambda name: called.append(name),
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(AssertionError(request)),
        budget=budget,
    )
    assert body is None
    assert evidence["status"] == "blocked_preflight"
    assert called == []


def test_getter_budget_mutation_fails_closed_before_dispatch() -> None:
    canary = _canary()
    budget = CampaignCostBudget()
    dispatched = []

    def getter(name: str) -> str:
        assert name == CREDENTIAL_INTERFACE
        budget.block("synthetic_reentrant_change")
        return canary

    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=getter,
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: dispatched.append(request),
        budget=budget,
    )
    assert body is None
    assert dispatched == []
    assert evidence["status"] == "blocked_before_dispatch"
    assert evidence["error_code"] == "cost_state_changed_after_credential_lookup"
    assert evidence["cost_block_code"] == "cost_state_changed_after_credential_lookup"
    _assert_canary_absent(canary, evidence)


def test_under_cap_reentrant_and_concurrent_getter_mutations_fail_closed() -> None:
    for concurrent in (False, True):
        canary = _canary()
        budget = CampaignCostBudget()
        dispatched = []

        def mutate_budget() -> None:
            nested = budget.prepare_reservation("forward_list")
            budget.mark_dispatched(nested)

        def getter(name: str) -> str:
            assert name == CREDENTIAL_INTERFACE
            if concurrent:
                thread = threading.Thread(target=mutate_budget)
                thread.start()
                thread.join()
            else:
                mutate_budget()
            return canary

        body, evidence = execute_authenticated_openalex_request(
            build_openalex_topic_descriptor(TOPIC),
            credential_getter=getter,
            credential_source_kind=CREDENTIAL_SOURCE_KIND,
            dispatch=lambda request: dispatched.append(request),
            budget=budget,
        )
        assert body is None
        assert dispatched == []
        assert evidence["status"] == "blocked_before_dispatch"
        assert evidence["error_code"] == "cost_state_changed_after_credential_lookup"
        assert evidence["cost_state"] == "blocked"
        _assert_canary_absent(canary, evidence)


def test_dispatcher_budget_mutation_blocks_reconciliation_and_future_lookup() -> None:
    canary = _canary()
    budget = CampaignCostBudget()

    def dispatch(request):  # noqa: ANN001, ANN202
        object.__setattr__(budget, "_version", budget._version + 1)
        return _list_body(0.001)

    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: canary,
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=dispatch,
        budget=budget,
    )
    assert body is None
    assert evidence["status"] == "blocked_after_dispatch"
    assert evidence["error_code"] == "cost_state_changed_during_dispatch"
    assert evidence["cost_state"] == "blocked"

    lookup_calls = []
    body, evidence = execute_authenticated_openalex_request(
        build_openalex_direct_descriptor(WORK_ID),
        credential_getter=lambda name: lookup_calls.append(name),
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=lambda request: (_ for _ in ()).throw(AssertionError(request)),
        budget=budget,
    )
    assert body is None
    assert evidence["status"] == "blocked_preflight"
    assert lookup_calls == []
    _assert_canary_absent(canary, evidence)


def test_reservation_commit_and_dispatch_entry_have_no_concurrent_unlock_gap() -> None:
    canary = _canary()
    budget = CampaignCostBudget()
    mutation_started = threading.Event()
    mutation_finished = threading.Event()
    mutation_finished_during_dispatch = []
    mutation_thread = None

    def mutate() -> None:
        mutation_started.set()
        budget.block("concurrent_dispatch_mutation")
        mutation_finished.set()

    def dispatch(request):  # noqa: ANN001, ANN202
        nonlocal mutation_thread
        mutation_thread = threading.Thread(target=mutate)
        mutation_thread.start()
        assert mutation_started.wait(timeout=1)
        mutation_finished_during_dispatch.append(mutation_finished.wait(timeout=0.05))
        return _list_body(0.001)

    body, evidence = execute_authenticated_openalex_request(
        build_openalex_topic_descriptor(TOPIC),
        credential_getter=lambda name: canary,
        credential_source_kind=CREDENTIAL_SOURCE_KIND,
        dispatch=dispatch,
        budget=budget,
    )
    assert mutation_thread is not None
    mutation_thread.join(timeout=1)
    assert mutation_finished.is_set()
    assert mutation_finished_during_dispatch == [False]
    assert body == _list_body(0.001)
    assert evidence["status"] == "completed"
    assert evidence["cost_state"] == "open"
    assert evidence["error_code"] is None
    assert budget.blocked is True
    assert budget.block_code == "concurrent_dispatch_mutation"
    _assert_canary_absent(canary, evidence)


def test_response_echo_parser_error_and_cost_contradiction_fail_closed() -> None:
    canary = _canary()
    for response, expected_block in [
        (canonical_json_bytes({"echo": canary}), "credential_echoed_in_response"),
        (b"not-json", "response_cost_unreconciled"),
        (_list_body(0.002), "cost_contradiction"),
    ]:
        budget = CampaignCostBudget()
        body, evidence, _, _ = _execute(
            build_openalex_topic_descriptor(TOPIC),
            canary=canary,
            response=response,
            budget=budget,
        )
        assert body is None
        assert evidence["status"] == "blocked_after_dispatch"
        assert evidence["cost_block_code"] == expected_block
        _assert_canary_absent(canary, evidence)


@pytest.mark.parametrize("representation", ["raw", "percent", "form", "json"])
def test_encoded_credential_echoes_are_rejected(representation: str) -> None:
    canary = _canary()
    values = {
        "raw": canary,
        "percent": urllib.parse.quote(canary, safe=""),
        "form": urllib.parse.quote_plus(canary, safe=""),
        "json": json.dumps(canary, ensure_ascii=True)[1:-1],
    }
    work = _work()
    work["display_name"] = values[representation]
    response = canonical_json_bytes({
        "meta": {
            "count": 1,
            "db_response_time_ms": 1,
            "page": 1,
            "per_page": 10,
            "next_cursor": None,
            "groups_count": 0,
            "cost_usd": 0.001,
        },
        "results": [work],
        "group_by": [],
    })
    body, evidence, _, observations = _execute(
        build_openalex_topic_descriptor(TOPIC),
        canary=canary,
        response=response,
    )
    assert body is None
    assert observations == [{"api_key_matches": True, "api_key_parameter_count": 1}]
    assert evidence["error_code"] == "credential_echoed_in_response"
    assert evidence["cost_block_code"] == "credential_echoed_in_response"
    _assert_canary_absent(canary, evidence)


def test_exact_three_route_campaign_reconciles_to_documented_usage() -> None:
    budget = CampaignCostBudget()
    cases = [
        (build_openalex_topic_descriptor(TOPIC), _list_body(0.001)),
        (build_openalex_direct_descriptor(WORK_ID), canonical_json_bytes(_work())),
        (build_openalex_forward_descriptor(WORK_ID), _list_body(0.0001, work_id="W2")),
    ]
    for descriptor, response in cases:
        body, evidence, _, _ = _execute(
            descriptor,
            canary=_canary(),
            response=response,
            budget=budget,
        )
        assert body == response
        assert evidence["status"] == "completed"
    assert budget.dispatch_count == 3
    assert budget.reserved_usd == Decimal("0.0011")
    assert budget.reconciled_usd == Decimal("0.0011")
    assert budget.blocked is False


def test_boundary_module_has_no_real_environment_or_network_access() -> None:
    source = Path("src/research_assistant/survey/openalex_credential_cost.py").read_text()
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "urlopen" not in source
    assert ".open(request" not in source
    assert "requests." not in source
    assert "api.openalex.org" not in source


def test_ipc_serialization_accepts_closed_evidence_and_rejects_canary_candidate() -> None:
    canary = _canary()
    _, evidence, _, _ = _execute(
        build_openalex_topic_descriptor(TOPIC),
        canary=canary,
        response=_list_body(0.001),
    )
    raw = serialize_boundary_evidence(evidence, forbidden_value=canary)
    assert canary.encode() not in raw
    assert json.loads(raw)["status"] == "completed"
    representations = {
        "raw": canary,
        "percent": urllib.parse.quote(canary, safe=""),
        "form": urllib.parse.quote_plus(canary, safe=""),
        "json": json.dumps(canary, ensure_ascii=True)[1:-1],
    }
    representations["nested_json"] = json.dumps(
        representations["json"],
        ensure_ascii=True,
    )[1:-1]
    for representation in representations.values():
        with pytest.raises(CredentialCostBoundaryError, match="credential_in_ipc_candidate"):
            serialize_boundary_evidence({"unsafe": representation}, forbidden_value=canary)
        assert contains_credential_representation(
            representation.encode("utf-8"),
            canary,
        )
    with pytest.raises(CredentialCostBoundaryError, match="evidence_serialization_failed"):
        serialize_boundary_evidence({"unsafe": object()}, forbidden_value=canary)
