from __future__ import annotations

import hashlib
import json
import secrets
import urllib.parse
from pathlib import Path

import pytest

from research_assistant.survey.m20_live_worker import (
    ARXIV_SEED,
    OPENALEX_ID,
    TOPIC,
    M20WorkerError,
    M20ProviderUnavailable,
    route_manifest,
    route_manifest_sha256,
    run_matrix,
    validate_published_run,
    _arxiv_payload,
)
from research_assistant.survey.mission_state import canonical_json_bytes


def _atom(*, arxiv_id: str, title: str, doi: str | None = None, total: str = "1") -> bytes:
    doi_element = f"<arxiv:doi>{doi}</arxiv:doi>" if doi is not None else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>{total}</opensearch:totalResults>
  <entry><id>https://arxiv.org/abs/{arxiv_id}</id><title>{title}</title>
  <published>2022-01-01T00:00:00Z</published><author><name>Alice Example</name></author>
  <arxiv:primary_category term="cs.LG" />{doi_element}</entry>
</feed>'''.encode()


def _work(work_id: str = OPENALEX_ID, *, lineage: list[str] | None = None) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": TOPIC,
        "authorships": [{"author": {"display_name": "Alice Example"}}],
        "publication_year": 2022,
        "doi": "https://doi.org/10.1000/neural-ot",
        "cited_by_count": 7,
        "referenced_works": lineage or [],
        "ids": {
            "openalex": f"https://openalex.org/{work_id}",
            "doi": "https://doi.org/10.1000/neural-ot",
        },
        "type": "article",
        "publication_date": "2022-01-01",
    }


def _list(work_id: str, *, cost: float, lineage: list[str] | None = None) -> bytes:
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
        "results": [_work(work_id, lineage=lineage)],
        "group_by": [],
    })


def _run(tmp_path: Path, *, contradictory_topic_cost: bool = False):
    canary = f"M20B3_SYNTHETIC_{secrets.token_urlsafe(24)}+/\""
    arxiv_calls = []
    openalex_calls = []
    getter_calls = []

    def getter(name: str) -> str:
        getter_calls.append(name)
        return canary

    def arxiv_dispatch(descriptor):  # noqa: ANN001, ANN202
        arxiv_calls.append(descriptor["route_kind"])
        if descriptor["route_kind"] == "arxiv_topic":
            return _atom(arxiv_id="9999.00001v1", title=TOPIC)
        return _atom(arxiv_id=ARXIV_SEED, title="Neural Optimal Transport")

    def openalex_dispatch(request):  # noqa: ANN001, ANN202
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        assert query.pop("api_key") == [canary]
        openalex_calls.append((urllib.parse.urlsplit(request.full_url).path, query))
        if "search" in query:
            return _list(OPENALEX_ID, cost=0.002 if contradictory_topic_cost else 0.001)
        if urllib.parse.urlsplit(request.full_url).path.endswith(OPENALEX_ID):
            return canonical_json_bytes(_work(OPENALEX_ID, lineage=["https://openalex.org/W1"]))
        return _list("W2", cost=0.0001)

    root = (tmp_path / "run").resolve()
    summary = run_matrix(
        output_root=root,
        credential_getter=getter,
        arxiv_dispatch=arxiv_dispatch,
        openalex_dispatch=openalex_dispatch,
    )
    return root, summary, canary, arxiv_calls, openalex_calls, getter_calls


def _artifact(path: Path) -> dict:
    return json.loads(path.read_text())


def _rewrite(path: Path, value: dict) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _rewrite_blocked_after_dispatch(
    root: Path,
    *,
    error_code: str,
    block_code: str,
    observed_cost_usd: object,
) -> None:
    ledger = _artifact(root / "request_ledger.json")
    row = ledger["rows"][1]
    evidence = row["cost_evidence"]
    row["status"] = "boundary_invalid"
    row["error_code"] = error_code
    evidence["status"] = "blocked_after_dispatch"
    evidence["error_code"] = error_code
    evidence["observed_cost_usd"] = observed_cost_usd
    evidence["cost_state"] = "blocked"
    evidence["cost_block_code"] = block_code
    _rewrite(root / "request_ledger.json", ledger)

    summary = _artifact(root / "campaign_summary.json")
    summary["request_ledger_sha256"] = hashlib.sha256(canonical_json_bytes(ledger)).hexdigest()
    summary["cost_evidence"] = {
        key: evidence[key]
        for key in (
            "campaign_cost_cap_usd",
            "reserved_cost_usd",
            "reconciled_cost_usd",
            "dispatch_count",
            "cost_state",
            "cost_block_code",
            "allowance_accounting",
        )
    }
    _rewrite(root / "campaign_summary.json", summary)


def test_route_manifest_is_exact_five_request_credential_free_contract() -> None:
    manifest = route_manifest()
    assert manifest["request_cap"] == 5
    assert manifest["campaign_cost_cap_usd"] == "0.01"
    assert [row["descriptor"]["route_kind"] for row in manifest["routes"]] == [
        "arxiv_topic",
        "topic_list",
        "arxiv_seed",
        "direct_singleton",
        "forward_list",
    ]
    assert len({row["request_binding_sha256"] for row in manifest["routes"]}) == 5
    assert all(
        key != "api_key"
        for row in manifest["routes"]
        for key, _value in row["descriptor"]["ordered_query_parameters"]
    )
    assert not any("secret" in str(value).casefold() for value in manifest.values())
    assert len(route_manifest_sha256()) == 64


def test_synthetic_success_closes_five_requests_cost_and_replay(tmp_path: Path) -> None:
    root, summary, canary, arxiv_calls, openalex_calls, getter_calls = _run(tmp_path)
    assert arxiv_calls == ["arxiv_topic", "arxiv_seed"]
    assert len(openalex_calls) == 3
    assert getter_calls == ["OPENALEX_API_KEY"] * 3
    assert summary["status"] == "synthetic_complete"
    assert summary["topic_identity_outcome"] == "ambiguous"
    assert summary["explicit_arxiv_identity_outcome"] == "selected"
    assert summary["openalex_case"]["identity_outcome"] == "selected"
    assert summary["openalex_case"]["backward_frontier_outcome"] == "observed_results"
    assert summary["openalex_case"]["forward_frontier_outcome"] == "observed_results"
    assert summary["cost_evidence"]["reserved_cost_usd"] == "0.0011"
    assert summary["cost_evidence"]["reconciled_cost_usd"] == "0.0011"
    assert summary["accepted_body_inventory_count"] == 5
    assert summary["campaign_validity"] == "closed"
    assert summary["network_used"] is False
    assert summary["real_credential_accessed"] is False
    ledger = _artifact(root / "request_ledger.json")
    assert [row["status"] for row in ledger["rows"]] == ["available"] * 5
    assert _artifact(root / "accepted_body_inventory.json")["status"] == "passed"
    assert len(_artifact(root / "replay_ledger.json")["records"]) == 5
    assert _artifact(root / "identity_outcomes.json")["openalex_case"] == summary["openalex_case"]
    assert not any(canary.encode() in path.read_bytes() for path in root.rglob("*") if path.is_file())


def test_cost_contradiction_stops_later_dispatch_without_canary_persistence(tmp_path: Path) -> None:
    root, summary, canary, arxiv_calls, openalex_calls, getter_calls = _run(
        tmp_path,
        contradictory_topic_cost=True,
    )
    ledger = _artifact(root / "request_ledger.json")
    assert arxiv_calls == ["arxiv_topic"]
    assert len(openalex_calls) == 1
    assert getter_calls == ["OPENALEX_API_KEY"]
    assert [row["status"] for row in ledger["rows"]] == [
        "available",
        "boundary_invalid",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
    ]
    assert summary["cost_evidence"]["cost_state"] == "blocked"
    assert summary["explicit_arxiv_identity_outcome"] == "boundary_invalid"
    assert summary["openalex_case"]["global_status"] == "boundary_invalid"
    assert summary["campaign_validity"] == "boundary_invalid"
    assert not any(canary.encode() in path.read_bytes() for path in root.rglob("*") if path.is_file())


def test_parser_boundary_invalidity_stops_later_dispatch_and_retains_body(tmp_path: Path) -> None:
    root = (tmp_path / "run").resolve()
    calls = []
    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: "M20B3_SYNTHETIC_PARSE_CANARY",
        arxiv_dispatch=lambda descriptor: calls.append(descriptor["route_kind"]) or b"not xml",
        openalex_dispatch=lambda request: pytest.fail("OpenAlex must not dispatch after boundary invalidity"),
    )
    ledger = _artifact(root / "request_ledger.json")
    assert calls == ["arxiv_topic"]
    assert [row["status"] for row in ledger["rows"]] == [
        "boundary_invalid",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
    ]
    assert summary["topic_identity_outcome"] == "boundary_invalid"
    assert summary["explicit_arxiv_identity_outcome"] == "boundary_invalid"
    assert summary["openalex_case"]["global_status"] == "boundary_invalid"
    assert summary["campaign_validity"] == "boundary_invalid"
    assert len(_artifact(root / "replay_ledger.json")["records"]) == 0
    retained = list((root / "cases/topic/accepted_bodies").iterdir())
    assert len(retained) == 1 and retained[0].read_bytes() == b"not xml"


def test_expected_arxiv_unavailability_continues_but_programmer_error_stops(tmp_path: Path) -> None:
    unavailable_calls = []

    def unavailable(descriptor):  # noqa: ANN001, ANN202
        unavailable_calls.append(descriptor["route_kind"])
        raise M20ProviderUnavailable("synthetic_unavailable")

    canary = "M20B3_SYNTHETIC_UNAVAILABLE_CANARY"

    def openalex_dispatch(request):  # noqa: ANN001, ANN202
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        query.pop("api_key")
        if "search" in query:
            return _list(OPENALEX_ID, cost=0.001)
        if urllib.parse.urlsplit(request.full_url).path.endswith(OPENALEX_ID):
            return canonical_json_bytes(_work(OPENALEX_ID, lineage=[]))
        return _list("W2", cost=0.0001)

    root = (tmp_path / "unavailable").resolve()
    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: canary,
        arxiv_dispatch=unavailable,
        openalex_dispatch=openalex_dispatch,
    )
    assert unavailable_calls == ["arxiv_topic", "arxiv_seed"]
    assert summary["campaign_validity"] == "closed"
    assert [row["status"] for row in _artifact(root / "request_ledger.json")["rows"]] == [
        "unavailable", "available", "unavailable", "available", "available",
    ]

    programmer_root = (tmp_path / "programmer").resolve()
    programmer = run_matrix(
        output_root=programmer_root,
        credential_getter=lambda name: pytest.fail("credential lookup after boundary error"),
        arxiv_dispatch=lambda descriptor: (_ for _ in ()).throw(TypeError("programmer defect")),
        openalex_dispatch=lambda request: pytest.fail("dispatch after boundary error"),
    )
    assert programmer["campaign_validity"] == "boundary_invalid"
    assert [row["status"] for row in _artifact(programmer_root / "request_ledger.json")["rows"]] == [
        "boundary_invalid",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
        "not_dispatched_due_to_veto",
    ]


@pytest.mark.parametrize(
    "body",
    [
        b"<not-feed />",
        b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>',
        b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"><opensearch:totalResults>NaN</opensearch:totalResults></feed>',
    ],
)
def test_malformed_arxiv_envelope_or_identifier_is_boundary_invalid(
    tmp_path: Path, body: bytes
) -> None:
    root = (tmp_path / hashlib.sha256(body).hexdigest()).resolve()
    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: pytest.fail("credential lookup after malformed arXiv"),
        arxiv_dispatch=lambda descriptor: body,
        openalex_dispatch=lambda request: pytest.fail("dispatch after malformed arXiv"),
    )
    assert summary["campaign_validity"] == "boundary_invalid"
    assert _artifact(root / "request_ledger.json")["rows"][0]["status"] == "boundary_invalid"


def test_malformed_arxiv_identifier_is_excluded_with_row_disposition() -> None:
    payload = _arxiv_payload(
        _atom(arxiv_id="not-an-id", title=TOPIC),
        route_kind="arxiv_topic",
    )
    assert payload["identity_records"] == []
    assert len(payload["malformed_row_sha256s"]) == 1
    assert payload["identity_envelope_complete"] is True


def test_arxiv_total_smaller_than_returned_entries_is_boundary_invalid(tmp_path: Path) -> None:
    body = _atom(arxiv_id="9999.00001v1", title=TOPIC, total="0")
    root = (tmp_path / "contradictory_total").resolve()
    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: pytest.fail("credential lookup after contradictory arXiv envelope"),
        arxiv_dispatch=lambda descriptor: body,
        openalex_dispatch=lambda request: pytest.fail("dispatch after contradictory arXiv envelope"),
    )
    assert summary["campaign_validity"] == "boundary_invalid"
    assert _artifact(root / "request_ledger.json")["rows"][0]["status"] == "boundary_invalid"


def test_arxiv_cap_and_doi_identity_are_preserved(tmp_path: Path) -> None:
    canary = "M20B3_SYNTHETIC_DOI_CANARY"
    root = (tmp_path / "doi").resolve()

    def arxiv_dispatch(descriptor):  # noqa: ANN001, ANN202
        if descriptor["route_kind"] == "arxiv_topic":
            return _atom(
                arxiv_id="9999.00001v1",
                title=TOPIC,
                doi="10.1000/neural-ot",
                total="11",
            )
        return _atom(arxiv_id=ARXIV_SEED, title="Neural Optimal Transport")

    def openalex_dispatch(request):  # noqa: ANN001, ANN202
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        query.pop("api_key")
        if "search" in query:
            return _list(OPENALEX_ID, cost=0.001)
        if urllib.parse.urlsplit(request.full_url).path.endswith(OPENALEX_ID):
            return canonical_json_bytes(_work(OPENALEX_ID, lineage=[]))
        return _list("W2", cost=0.0001)

    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: canary,
        arxiv_dispatch=arxiv_dispatch,
        openalex_dispatch=openalex_dispatch,
    )
    outcomes = _artifact(root / "identity_outcomes.json")
    arxiv_state = next(
        row for row in outcomes["topic_bootstrap"]["request_states"] if row["provider"] == "arxiv"
    )
    assert arxiv_state["records"][0]["doi"] == "10.1000/neural-ot"
    assert summary["topic_identity_outcome"] == "capped"


def test_cross_provider_doi_equivalence_merges_topic_identity(tmp_path: Path) -> None:
    canary = "M20B3_SYNTHETIC_DOI_MERGE_CANARY"
    root = (tmp_path / "doi_merge").resolve()

    def openalex_dispatch(request):  # noqa: ANN001, ANN202
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        query.pop("api_key")
        if "search" in query:
            return _list(OPENALEX_ID, cost=0.001)
        if urllib.parse.urlsplit(request.full_url).path.endswith(OPENALEX_ID):
            return canonical_json_bytes(_work(OPENALEX_ID, lineage=[]))
        return _list("W2", cost=0.0001)

    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: canary,
        arxiv_dispatch=lambda descriptor: (
            _atom(
                arxiv_id="9999.00001v1",
                title=TOPIC,
                doi="10.1000/neural-ot",
            )
            if descriptor["route_kind"] == "arxiv_topic"
            else _atom(arxiv_id=ARXIV_SEED, title="Neural Optimal Transport")
        ),
        openalex_dispatch=openalex_dispatch,
    )
    assert summary["topic_identity_outcome"] == "selected"


def test_invalid_backward_view_vetoes_forward_before_dispatch(tmp_path: Path) -> None:
    canary = "M20B3_SYNTHETIC_BACKWARD_CANARY"
    calls = []
    root = (tmp_path / "backward").resolve()

    def openalex_dispatch(request):  # noqa: ANN001, ANN202
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        query.pop("api_key")
        calls.append(urllib.parse.urlsplit(request.full_url).path)
        if "search" in query:
            return _list(OPENALEX_ID, cost=0.001)
        work = _work(OPENALEX_ID, lineage=["not-an-openalex-id"])
        return canonical_json_bytes(work)

    summary = run_matrix(
        output_root=root,
        credential_getter=lambda name: canary,
        arxiv_dispatch=lambda descriptor: (
            _atom(arxiv_id="9999.00001v1", title=TOPIC)
            if descriptor["route_kind"] == "arxiv_topic"
            else _atom(arxiv_id=ARXIV_SEED, title="Neural Optimal Transport")
        ),
        openalex_dispatch=openalex_dispatch,
    )
    ledger = _artifact(root / "request_ledger.json")
    assert len(calls) == 2
    assert ledger["rows"][4]["status"] == "not_dispatched_due_to_veto"
    assert summary["openalex_case"]["backward_frontier_outcome"] == "boundary_invalid"
    assert summary["openalex_case"]["forward_frontier_outcome"] == "not_dispatched_due_to_veto"


def test_offline_validator_replays_closed_success_and_boundary_result(tmp_path: Path) -> None:
    root, _summary, _canary, _arxiv, _openalex, _getter = _run(tmp_path)
    replay = validate_published_run(root, execution_mode="synthetic")
    assert replay["campaign_validity"] == "closed"
    assert replay["selected_candidate_authority"] is True

    boundary_root = (tmp_path / "boundary").resolve()
    run_matrix(
        output_root=boundary_root,
        credential_getter=lambda name: pytest.fail("credential lookup after boundary invalidity"),
        arxiv_dispatch=lambda descriptor: b"not xml",
        openalex_dispatch=lambda request: pytest.fail("provider dispatch after boundary invalidity"),
    )
    replay = validate_published_run(boundary_root, execution_mode="synthetic")
    assert replay["campaign_validity"] == "boundary_invalid"
    assert replay["selected_candidate_authority"] is False
    assert replay["accepted_body_count"] == 1

    credential_root = (tmp_path / "invalid_credential").resolve()
    run_matrix(
        output_root=credential_root,
        credential_getter=lambda name: "",
        arxiv_dispatch=lambda descriptor: _atom(
            arxiv_id="9999.00001v1" if descriptor["route_kind"] == "arxiv_topic" else ARXIV_SEED,
            title=TOPIC if descriptor["route_kind"] == "arxiv_topic" else "Neural Optimal Transport",
        ),
        openalex_dispatch=lambda request: pytest.fail("invalid credential must not dispatch"),
    )
    invalid_credential = validate_published_run(credential_root, execution_mode="synthetic")
    assert invalid_credential["campaign_validity"] == "boundary_invalid"


@pytest.mark.parametrize(
    "mutation",
    [
        "raw_body", "inventory", "classifier", "accounting", "lookup_count",
        "zero_cost", "nan_cost", "dispatch_count", "invented_cost_status",
        "contradictory_cost_status", "row_cost_error_mismatch",
    ],
)
def test_offline_validator_rejects_cross_artifact_tampering(tmp_path: Path, mutation: str) -> None:
    root, _summary, _canary, _arxiv, _openalex, _getter = _run(tmp_path)
    if mutation == "raw_body":
        body = next((root / "cases/topic/accepted_bodies").iterdir())
        body.write_bytes(body.read_bytes() + b"tamper")
    elif mutation == "inventory":
        value = _artifact(root / "accepted_body_inventory.json")
        value["cases"][0]["inventory"]["record_count"] += 1
        _rewrite(root / "accepted_body_inventory.json", value)
    elif mutation == "classifier":
        value = _artifact(root / "identity_outcomes.json")
        value["topic_bootstrap"]["outcome"] = "empty"
        _rewrite(root / "identity_outcomes.json", value)
    elif mutation in {"accounting", "lookup_count"}:
        value = _artifact(root / "request_ledger.json")
        if mutation == "accounting":
            value["accepted_body_bytes"] += 1
        else:
            value["credential_interface_lookup_count"] += 1
        _rewrite(root / "request_ledger.json", value)
    else:
        value = _artifact(root / "request_ledger.json")
        cost = value["rows"][1]["cost_evidence"]
        if mutation == "zero_cost":
            cost["reserved_cost_usd"] = "0"
            cost["reconciled_cost_usd"] = "0"
            cost["dispatch_count"] = 0
        elif mutation == "nan_cost":
            cost["reserved_cost_usd"] = "NaN"
        elif mutation == "dispatch_count":
            cost["dispatch_count"] = 0
        elif mutation == "invented_cost_status":
            cost["status"] = "invented_non_dispatch_state"
        elif mutation == "contradictory_cost_status":
            cost["status"] = "blocked_before_dispatch"
            cost["error_code"] = "credential_lookup_failed"
        else:
            value["rows"][1]["status"] = "boundary_invalid"
            value["rows"][1]["error_code"] = "invented_row_cause"
        _rewrite(root / "request_ledger.json", value)
    with pytest.raises(M20WorkerError):
        validate_published_run(root, execution_mode="synthetic")


@pytest.mark.parametrize(
    "mutation",
    ["preflight_arbitrary_block", "before_open_with_block", "before_mismatched_block"],
)
def test_offline_validator_rejects_cost_state_automaton_tampering(
    tmp_path: Path, mutation: str
) -> None:
    root = (tmp_path / mutation).resolve()
    run_matrix(
        output_root=root,
        credential_getter=lambda name: "",
        arxiv_dispatch=lambda descriptor: _atom(
            arxiv_id="9999.00001v1" if descriptor["route_kind"] == "arxiv_topic" else ARXIV_SEED,
            title=TOPIC if descriptor["route_kind"] == "arxiv_topic" else "Neural Optimal Transport",
        ),
        openalex_dispatch=lambda request: pytest.fail("invalid credential must not dispatch"),
    )
    ledger = _artifact(root / "request_ledger.json")
    row = ledger["rows"][1]
    cost = row["cost_evidence"]
    if mutation == "preflight_arbitrary_block":
        row["error_code"] = "descriptor_or_cost_preflight_invalid"
        cost["status"] = "blocked_preflight"
        cost["error_code"] = "descriptor_or_cost_preflight_invalid"
        cost["cost_state"] = "blocked"
        cost["cost_block_code"] = "arbitrary_block"
    elif mutation == "before_open_with_block":
        cost["cost_block_code"] = "invalid_credential"
    else:
        row["error_code"] = "invalid_cost_state"
        cost["error_code"] = "invalid_cost_state"
        cost["credential_present"] = True
        cost["cost_state"] = "blocked"
        cost["cost_block_code"] = "different_block"
    _rewrite(root / "request_ledger.json", ledger)
    with pytest.raises(M20WorkerError):
        validate_published_run(root, execution_mode="synthetic")


@pytest.mark.parametrize(
    ("error_code", "block_code", "observed_cost_usd"),
    [
        ("dispatch_failed_closed", "dispatch_cost_unreconciled", None),
        ("response_type_invalid", "dispatch_cost_unreconciled", None),
        ("credential_echoed_in_response", "credential_echoed_in_response", None),
        ("response_cost_unreconciled", "response_cost_unreconciled", None),
        ("cost_contradiction", "cost_contradiction", "0.002"),
        ("cost_state_changed_during_dispatch", "cost_state_changed_during_dispatch", "0.002"),
        ("invalid_cost_state", "invalid_cost_state", "0"),
        ("invalid_dispatch_reservation", "invalid_dispatch_reservation", "999"),
        ("campaign_cost_cap_exceeded", "campaign_cost_cap_exceeded", "0.001"),
    ],
)
def test_offline_validator_accepts_exact_blocked_after_dispatch_observed_cost_automaton(
    tmp_path: Path,
    error_code: str,
    block_code: str,
    observed_cost_usd: object,
) -> None:
    root, _summary, _canary, _arxiv, _openalex, _getter = _run(
        tmp_path,
        contradictory_topic_cost=True,
    )
    _rewrite_blocked_after_dispatch(
        root,
        error_code=error_code,
        block_code=block_code,
        observed_cost_usd=observed_cost_usd,
    )
    assert validate_published_run(root, execution_mode="synthetic")["campaign_validity"] == "boundary_invalid"


@pytest.mark.parametrize(
    ("error_code", "block_code", "observed_cost_usd"),
    [
        ("dispatch_failed_closed", "dispatch_cost_unreconciled", "not-a-cost"),
        ("response_type_invalid", "dispatch_cost_unreconciled", "0.001"),
        ("credential_echoed_in_response", "credential_echoed_in_response", "0"),
        ("response_cost_unreconciled", "response_cost_unreconciled", "NaN"),
        ("cost_contradiction", "cost_contradiction", None),
        ("cost_contradiction", "cost_contradiction", "0.001"),
        ("cost_contradiction", "cost_contradiction", "Infinity"),
        ("cost_contradiction", "cost_contradiction", "-0.001"),
        ("cost_state_changed_during_dispatch", "cost_state_changed_during_dispatch", None),
        ("invalid_cost_state", "invalid_cost_state", "not-a-cost"),
        ("invalid_dispatch_reservation", "invalid_dispatch_reservation", "Infinity"),
        ("invalid_cost_state", "invalid_cost_state", "-0.001"),
        ("cost_state_changed_during_dispatch", "cost_state_changed_during_dispatch", "1e-3"),
        ("campaign_cost_cap_exceeded", "campaign_cost_cap_exceeded", "0.002"),
        ("campaign_cost_cap_exceeded", "campaign_cost_cap_exceeded", 0.001),
    ],
)
def test_offline_validator_rejects_digest_rebound_blocked_after_dispatch_observed_cost_tampering(
    tmp_path: Path,
    error_code: str,
    block_code: str,
    observed_cost_usd: object,
) -> None:
    root, _summary, _canary, _arxiv, _openalex, _getter = _run(
        tmp_path,
        contradictory_topic_cost=True,
    )
    _rewrite_blocked_after_dispatch(
        root,
        error_code=error_code,
        block_code=block_code,
        observed_cost_usd=observed_cost_usd,
    )
    with pytest.raises(M20WorkerError, match="published_cost_evidence_invalid"):
        validate_published_run(root, execution_mode="synthetic")


def test_existing_output_root_is_rejected_before_getter_or_dispatch(tmp_path: Path) -> None:
    root = (tmp_path / "run").resolve()
    root.mkdir()
    calls = []
    with pytest.raises(M20WorkerError, match="output_root_not_fresh"):
        run_matrix(
            output_root=root,
            credential_getter=lambda name: calls.append(name),
            arxiv_dispatch=lambda descriptor: calls.append(descriptor),
            openalex_dispatch=lambda request: calls.append(request),
        )
    assert calls == []


def test_worker_source_has_one_exact_environment_lookup_and_no_import_time_dispatch() -> None:
    source = Path("src/research_assistant/survey/m20_live_worker.py").read_text()
    assert source.count("os.environ.get(CREDENTIAL_INTERFACE)") == 1
    assert "os.environ[" not in source
    assert "os.getenv" not in source
