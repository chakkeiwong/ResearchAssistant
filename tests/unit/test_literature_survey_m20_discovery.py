from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey.discovery_capability import (
    ACCEPTED_BODY_SCHEMA,
    BODY_REPLAY_SCHEMA,
    bind_normalized_payload,
    classify_frontier_attempt,
    classify_identity_outcome,
    compose_openalex_case_outcome,
    outcome_automaton_manifest,
    outcome_automaton_sha256,
    replay_accepted_body,
    validate_accepted_body_inventory,
    write_accepted_body,
)
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes


TOPIC = "Neural Optimal Transport for generative modeling and inference"
BINDING_A = "a" * 64
BINDING_B = "b" * 64
BODY_BYTES_A = b"directbody"
BODY_BYTES_B = b"forwardbod"
BODY_A = hashlib.sha256(BODY_BYTES_A).hexdigest()
BODY_B = hashlib.sha256(BODY_BYTES_B).hexdigest()
MALFORMED_A = "e" * 64


def _provider_row(provider: str, source_id: str) -> dict:
    if provider == "arxiv":
        return {
            "provider": "arxiv",
            "query_kind": "identity_resolution",
            "source_id": source_id,
            "primary_category": "cs.LG",
            "published": "2022-01-01",
        }
    return {
        "provider": "openalex",
        "query_kind": "identity_resolution",
        "source_id": source_id,
        "citation_count": 10,
        "publication_date": "2022-01-01",
        "work_type": "article",
    }


def _record(
    *,
    provider: str = "openalex",
    source_id: str = "W4387130479",
    key: str | None = None,
    title: str = "Neural Optimal Transport for generative modeling and inference",
    authors: list[str] | None = None,
    year: int = 2022,
    doi: str | None = "10.1000/neural-ot",
    arxiv_id: str | None = None,
    openalex_id: str | None = "W4387130479",
    topic_query: bool = False,
) -> dict:
    if provider == "arxiv":
        arxiv_id = arxiv_id or source_id
        openalex_id = None
    return {
        "record_key": key or f"{provider}-{source_id.casefold()}",
        "title": title,
        "authors": authors or ["Alice Example"],
        "year": year,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": openalex_id,
        "landing_page_url": (
            f"https://arxiv.org/abs/{arxiv_id}"
            if provider == "arxiv"
            else f"https://openalex.org/{openalex_id or source_id}"
        ),
        "citation_count": 10 if provider == "openalex" else None,
        "providers": [provider],
        "roles": ["seed"],
        "provider_records": [_provider_row(provider, source_id)],
        "referenced_works": [],
        "query_provenance": [{
            "provider": provider,
            "query_kind": "identity_resolution",
            "normalized_seed_key": TOPIC.casefold() if topic_query else None,
            "topic_query": topic_query,
        }],
    }


def _payload(
    *,
    identity_records: list[dict] | None = None,
    malformed: list[str] | None = None,
    identity_status: str = "observed",
    envelope_complete: bool = True,
    cap_exceeded: bool = False,
    frontier_targets: list[object] | None = None,
    frontier_status: str = "observed",
    reported_total: int | None = 0,
    continuation: bool = False,
) -> dict:
    return {
        "identity_view_status": identity_status,
        "identity_records": identity_records or [],
        "malformed_row_sha256s": malformed or [],
        "identity_envelope_complete": envelope_complete,
        "identity_cap_exceeded": cap_exceeded,
        "frontier_view_status": frontier_status,
        "frontier_target_ids": frontier_targets or [],
        "frontier_reported_total": reported_total,
        "frontier_continuation_visible": continuation,
    }


def _payload_sha(payload: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _identity_request(
    binding: str,
    *,
    provider: str,
    payload: dict | None = None,
    body_sha: str = BODY_A,
    status: str = "available",
    required: bool = True,
) -> dict:
    available = status == "available"
    return {
        "request_binding_sha256": binding,
        "provider": provider,
        "required": required,
        "status": status,
        "envelope_complete": payload["identity_envelope_complete"] if available else True,
        "cap_exceeded": payload["identity_cap_exceeded"] if available else False,
        "body_sha256": body_sha if available else None,
        "normalized_payload_sha256": _payload_sha(payload) if available else None,
        "records": payload["identity_records"] if available else [],
        "malformed_row_sha256s": payload["malformed_row_sha256s"] if available else [],
        "malformed_row_count": len(payload["malformed_row_sha256s"]) if available else 0,
    }


def _body_record(binding: str, body_sha: str, payload: dict) -> dict:
    return {
        "schema_version": ACCEPTED_BODY_SCHEMA,
        "request_binding_sha256": binding,
        "relative_path": f"accepted_bodies/request-{binding}.body",
        "size_bytes": 10,
        "sha256": body_sha,
        "accepted_body_cap_bytes": 2_000_000,
        "content_kind": "public_metadata_response_body",
        "normalized_payload_sha256": _payload_sha(payload),
    }


def _replay(binding: str, body_sha: str, payload: dict) -> dict:
    return {
        "schema_version": BODY_REPLAY_SCHEMA,
        "status": "passed",
        "request_binding_sha256": binding,
        "accepted_body_sha256": body_sha,
        "normalized_payload_sha256": _payload_sha(payload),
        "normalized_payload": payload,
        "size_bytes": 10,
    }


def _identity_records_for(outcome: str) -> list[dict]:
    exact = _record()
    if outcome in {"selected", "capped"}:
        return [exact]
    if outcome == "ambiguous":
        return [
            exact,
            _record(
                source_id="W2",
                key="openalex-w2",
                doi="10.1000/other",
                openalex_id="W2",
                title="A different eligible work",
            ),
        ]
    return []


def _frontier_raw(outcome: str) -> tuple[list[object], int | None, bool, str, bool]:
    if outcome == "observed_results":
        return ["W1"], 1, False, "available", True
    if outcome == "empty_observed":
        return [], 0, False, "available", True
    if outcome == "capped":
        return [f"W{value}" for value in range(1, 12)], 11, False, "available", True
    if outcome == "boundary_invalid":
        return [], None, False, "available", False
    if outcome == "provider_unavailable":
        return [], None, False, "unavailable", True
    if outcome == "not_dispatched_due_to_veto":
        return [], None, False, "available", True
    return ["W1"], 1, False, "available", True


def _case_inputs(
    *,
    identity_outcome: str = "selected",
    backward_outcome: str | None = None,
    forward_outcome: str = "empty_observed",
) -> tuple[dict, dict, dict, list[dict], list[dict]]:
    if backward_outcome is None:
        backward_outcome = {
            "selected": "empty_observed",
            "unavailable": "provider_unavailable",
            "boundary_invalid": "not_dispatched_due_to_veto",
        }.get(identity_outcome, "not_observed")
    backward_targets, backward_total, backward_continuation, direct_status, backward_integrity = _frontier_raw(backward_outcome)
    records = _identity_records_for(identity_outcome)
    direct_payload = _payload(
        identity_records=records,
        cap_exceeded=identity_outcome == "capped",
        frontier_targets=backward_targets,
        frontier_status=("boundary_invalid" if backward_outcome == "boundary_invalid" else "observed"),
        reported_total=backward_total,
        continuation=backward_continuation,
    )
    if identity_outcome == "unavailable":
        direct_status = "unavailable"
    elif identity_outcome == "boundary_invalid":
        direct_status = "boundary_invalid"
    direct_request = _identity_request(
        BINDING_A,
        provider="openalex",
        payload=direct_payload,
        body_sha=BODY_A,
        status=direct_status,
    )
    identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="openalex:W4387130479",
        topic=None,
        request_states=[direct_request],
    )
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=BINDING_A,
        origin_body_sha256=(BODY_A if direct_status == "available" else None),
        origin_normalized_payload_sha256=(_payload_sha(direct_payload) if direct_status == "available" else None),
        request_status=direct_status,
        body_integrity_valid=backward_integrity,
        target_ids=backward_targets,
        reported_total=backward_total,
        continuation_visible=backward_continuation,
        origin_identity_outcome=identity["outcome"],
        dispatched=backward_outcome != "not_dispatched_due_to_veto",
        derived_from_identity_request=True,
    )

    forward_targets, forward_total, forward_continuation, forward_status, forward_integrity = _frontier_raw(forward_outcome)
    forward_dispatched = forward_outcome != "not_dispatched_due_to_veto"
    forward_payload = _payload(
        identity_status="not_applicable",
        frontier_targets=forward_targets,
        frontier_status=("boundary_invalid" if forward_outcome == "boundary_invalid" else "observed"),
        reported_total=forward_total,
        continuation=forward_continuation,
    )
    forward = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=BINDING_B,
        origin_body_sha256=(BODY_B if forward_status == "available" and forward_dispatched else None),
        origin_normalized_payload_sha256=(
            _payload_sha(forward_payload) if forward_status == "available" and forward_dispatched else None
        ),
        request_status=forward_status,
        body_integrity_valid=forward_integrity,
        target_ids=forward_targets,
        reported_total=forward_total,
        continuation_visible=forward_continuation,
        origin_identity_outcome=identity["outcome"],
        dispatched=forward_dispatched,
        derived_from_identity_request=False,
    )
    bodies: list[dict] = []
    replays: list[dict] = []
    if direct_status == "available":
        bodies.append(_body_record(BINDING_A, BODY_A, direct_payload))
        replays.append(_replay(BINDING_A, BODY_A, direct_payload))
    if forward_status == "available" and forward_dispatched:
        bodies.append(_body_record(BINDING_B, BODY_B, forward_payload))
        replays.append(_replay(BINDING_B, BODY_B, forward_payload))
    return identity, backward, forward, bodies, replays


def _write_body_root(root: Path, body_records: list[dict]) -> None:
    body_dir = root / "accepted_bodies"
    body_dir.mkdir(parents=True)
    body_bytes = {BODY_A: BODY_BYTES_A, BODY_B: BODY_BYTES_B}
    for record in body_records:
        (root / record["relative_path"]).write_bytes(body_bytes[record["sha256"]])


def _compose(
    inputs: tuple[dict, dict, dict, list[dict], list[dict]],
    tmp_path: Path,
) -> dict:
    identity, backward, forward, bodies, replays = inputs
    _write_body_root(tmp_path, bodies)
    return compose_openalex_case_outcome(
        identity=identity,
        backward=backward,
        forward=forward,
        accepted_body_root=tmp_path,
        accepted_body_records=bodies,
        replay_records=replays,
    )


def test_accepted_body_round_trip_and_inventory_close_exactly(tmp_path: Path) -> None:
    payload = _payload(identity_records=[_record()])
    body = json.dumps(payload).encode()
    record = write_accepted_body(tmp_path, request_binding_sha256=BINDING_A, body=body)
    bound = bind_normalized_payload(record, payload)
    replay = replay_accepted_body(tmp_path, body_record=bound, parser=json.loads)
    assert replay["normalized_payload"] == payload
    assert validate_accepted_body_inventory(tmp_path, body_records=[bound])["record_count"] == 1

    write_accepted_body(tmp_path, request_binding_sha256=BINDING_B, body=b"extra")
    with pytest.raises(MissionStateError, match="inventory differs"):
        validate_accepted_body_inventory(tmp_path, body_records=[bound])


def test_accepted_body_is_exclusive_capped_and_replay_fail_closed(tmp_path: Path) -> None:
    write_accepted_body(tmp_path, request_binding_sha256=BINDING_A, body=b"one")
    with pytest.raises(MissionStateError, match="already exists"):
        write_accepted_body(tmp_path, request_binding_sha256=BINDING_A, body=b"two")
    with pytest.raises(MissionStateError, match="exceeds"):
        write_accepted_body(
            tmp_path,
            request_binding_sha256=BINDING_B,
            body=b"x" * 2_000_001,
        )
    with pytest.raises(MissionStateError, match="frozen per-request cap"):
        write_accepted_body(
            tmp_path,
            request_binding_sha256=BINDING_B,
            body=b"large",
            accepted_body_cap_bytes=3_000_000,
        )

    root = tmp_path / "other"
    root.mkdir()
    payload = _payload()
    record = write_accepted_body(root, request_binding_sha256=BINDING_A, body=b"body")
    with pytest.raises(MissionStateError, match="lacks normalized"):
        replay_accepted_body(root, body_record=record, parser=lambda _: payload)
    bound = bind_normalized_payload(record, payload)
    (root / record["relative_path"]).write_bytes(b"changed")
    with pytest.raises(MissionStateError, match="differs"):
        replay_accepted_body(root, body_record=bound, parser=lambda _: payload)


def test_identity_exact_openalex_requires_exact_identifier_and_topology() -> None:
    selected, *_ = _case_inputs()
    assert selected["outcome"] == "selected"
    assert selected["selected_identifier"] == "openalex:w4387130479"

    wrong_payload = _payload(identity_records=[_record(source_id="W2", openalex_id="W2")])
    wrong = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="W4387130479",
        topic=None,
        request_states=[_identity_request(BINDING_A, provider="openalex", payload=wrong_payload)],
    )
    assert wrong["outcome"] == "ambiguous"
    assert wrong["selected_candidate_id"] is None

    with pytest.raises(MissionStateError, match="provider topology"):
        classify_identity_outcome(
            case_kind="explicit_openalex",
            expected_identifier="W4387130479",
            topic=None,
            request_states=[_identity_request(BINDING_A, provider="arxiv", payload=_payload())],
        )


def test_identity_arxiv_family_merge_and_strong_alias_conflict() -> None:
    records = [
        _record(provider="arxiv", source_id="2201.12220v1", arxiv_id="2201.12220v1"),
        _record(provider="arxiv", source_id="2201.12220v3", key="arxiv-v3", arxiv_id="2201.12220v3"),
    ]
    payload = _payload(identity_records=records)
    selected = classify_identity_outcome(
        case_kind="explicit_arxiv_seed",
        expected_identifier="arxiv:2201.12220v3",
        topic=None,
        request_states=[_identity_request(BINDING_A, provider="arxiv", payload=payload)],
    )
    assert selected["outcome"] == "selected"
    assert selected["selected_identifier"] == "arxiv:2201.12220v3"

    newer_records = [
        *records,
        _record(provider="arxiv", source_id="2201.12220v4", key="arxiv-v4", arxiv_id="2201.12220v4"),
    ]
    newer_payload = _payload(identity_records=newer_records)
    newer = classify_identity_outcome(
        case_kind="explicit_arxiv_seed",
        expected_identifier="arxiv:2201.12220v3",
        topic=None,
        request_states=[_identity_request(BINDING_A, provider="arxiv", payload=newer_payload)],
    )
    assert newer["expected_identifier"] == "arxiv:2201.12220v3"
    assert newer["selected_identifier"] == "arxiv:2201.12220v4"

    conflict_records = [
        _record(provider="arxiv", source_id="2201.12220v3", arxiv_id="2201.12220v3"),
        _record(
            provider="arxiv",
            source_id="2201.12220v4",
            key="arxiv-conflict",
            arxiv_id="2201.12220v4",
            title="Unrelated filtering",
            authors=["Bob Other"],
        ),
    ]
    conflict_payload = _payload(identity_records=conflict_records)
    conflict = classify_identity_outcome(
        case_kind="explicit_arxiv_seed",
        expected_identifier="2201.12220v3",
        topic=None,
        request_states=[_identity_request(BINDING_A, provider="arxiv", payload=conflict_payload)],
    )
    assert conflict["outcome"] == "ambiguous"
    assert conflict["conflict_ids"]


def test_topic_identity_derives_unique_high_margin_and_partial_provider_ambiguity() -> None:
    arxiv = _record(provider="arxiv", source_id="2201.12220v3", arxiv_id="2201.12220v3", topic_query=True)
    openalex = _record(topic_query=True)
    arxiv_payload = _payload(identity_records=[arxiv])
    openalex_payload = _payload(identity_records=[openalex])
    selected = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(BINDING_A, provider="arxiv", payload=arxiv_payload),
            _identity_request(BINDING_B, provider="openalex", payload=openalex_payload, body_sha=BODY_B),
        ],
    )
    assert selected["outcome"] == "selected"

    partial = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(BINDING_A, provider="arxiv", payload=arxiv_payload),
            _identity_request(BINDING_B, provider="openalex", status="unavailable"),
        ],
    )
    assert partial["outcome"] == "ambiguous"


def test_topic_predicate_excludes_unrelated_candidates_before_ambiguity() -> None:
    exact = _record(topic_query=True)
    unrelated = _record(
        source_id="W2",
        key="openalex-unrelated",
        title="Unrelated Bayesian filtering",
        doi="10.1000/unrelated",
        openalex_id="W2",
        topic_query=True,
    )
    arxiv_payload = _payload()
    openalex_payload = _payload(identity_records=[exact, unrelated])
    identity = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(BINDING_A, provider="arxiv", payload=arxiv_payload),
            _identity_request(BINDING_B, provider="openalex", payload=openalex_payload, body_sha=BODY_B),
        ],
    )
    assert identity["outcome"] == "selected"
    assert len(identity["excluded_candidate_ids"]) == 1
    assert identity["competing_candidate_ids"] == []


def test_topic_predicate_exact_precedes_near_and_low_margin_stays_ambiguous() -> None:
    exact = _record(topic_query=True)
    near = _record(
        source_id="W2",
        key="openalex-near",
        title=TOPIC + "s",
        doi="10.1000/near",
        openalex_id="W2",
        topic_query=True,
    )
    arxiv_payload = _payload()
    openalex_payload = _payload(identity_records=[exact, near])
    exact_result = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(BINDING_A, provider="arxiv", payload=arxiv_payload),
            _identity_request(BINDING_B, provider="openalex", payload=openalex_payload, body_sha=BODY_B),
        ],
    )
    assert exact_result["outcome"] == "selected"

    two_exact = deepcopy(exact)
    two_exact["record_key"] = "openalex-second-exact"
    two_exact["openalex_id"] = "W3"
    two_exact["doi"] = "10.1000/second-exact"
    two_exact["landing_page_url"] = "https://openalex.org/W3"
    two_exact["provider_records"][0]["source_id"] = "W3"
    ambiguous_payload = _payload(identity_records=[exact, two_exact])
    ambiguous = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(BINDING_A, provider="arxiv", payload=arxiv_payload),
            _identity_request(BINDING_B, provider="openalex", payload=ambiguous_payload, body_sha=BODY_B),
        ],
    )
    assert ambiguous["outcome"] == "ambiguous"
    assert len(ambiguous["competing_candidate_ids"]) == 2

    near_only = _record(
        source_id="W4",
        key="openalex-near-2",
        title=TOPIC + "x",
        doi="10.1000/near-2",
        openalex_id="W4",
        topic_query=True,
    )
    low_margin_payload = _payload(identity_records=[near, near_only])
    low_margin = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(BINDING_A, provider="arxiv", payload=arxiv_payload),
            _identity_request(BINDING_B, provider="openalex", payload=low_margin_payload, body_sha=BODY_B),
        ],
    )
    assert low_margin["outcome"] == "ambiguous"


@pytest.mark.parametrize("mutation", ["source_id", "query_kind", "navigation_role"])
def test_identity_records_bind_provider_source_and_identity_role(mutation: str) -> None:
    record = _record()
    if mutation == "source_id":
        record["provider_records"][0]["source_id"] = "W2"
    elif mutation == "query_kind":
        record["provider_records"][0]["query_kind"] = "citation_frontier"
        record["query_provenance"][0]["query_kind"] = "citation_frontier"
    else:
        record["roles"] = ["major_citing_work"]
    payload = _payload(identity_records=[record])
    with pytest.raises(MissionStateError):
        classify_identity_outcome(
            case_kind="explicit_openalex",
            expected_identifier="W4387130479",
            topic=None,
            request_states=[_identity_request(BINDING_A, provider="openalex", payload=payload)],
        )


def test_topic_identity_provenance_binds_exact_topic_key() -> None:
    record = _record(topic_query=True)
    record["query_provenance"][0]["normalized_seed_key"] = "a different topic"
    payload = _payload(identity_records=[record])
    with pytest.raises(MissionStateError, match="query role"):
        classify_identity_outcome(
            case_kind="topic_bootstrap",
            expected_identifier=None,
            topic=TOPIC,
            request_states=[
                _identity_request(BINDING_A, provider="arxiv", payload=_payload()),
                _identity_request(BINDING_B, provider="openalex", payload=payload, body_sha=BODY_B),
            ],
        )


def test_identity_boundary_and_durable_labels_replay_from_request_evidence(tmp_path: Path) -> None:
    payload = _payload(identity_records=[_record()], envelope_complete=False)
    identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="W4387130479",
        topic=None,
        request_states=[_identity_request(BINDING_A, provider="openalex", payload=payload)],
    )
    assert identity["outcome"] == "boundary_invalid"
    assert identity["boundary_invalid_request_count"] == 1

    inputs = _case_inputs()
    forged = deepcopy(inputs[0])
    forged["outcome"] = "capped"
    forged["selected_candidate_id"] = None
    forged["selected_identifier"] = None
    with pytest.raises(MissionStateError, match="does not replay"):
        _compose((forged, *inputs[1:]), tmp_path)


def test_incomplete_available_identity_envelope_still_requires_exact_replay(tmp_path: Path) -> None:
    payload = _payload(identity_records=[_record()], envelope_complete=False)
    identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="W4387130479",
        topic=None,
        request_states=[_identity_request(BINDING_A, provider="openalex", payload=payload)],
    )
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=BINDING_A,
        origin_body_sha256=None,
        origin_normalized_payload_sha256=None,
        request_status="available",
        body_integrity_valid=True,
        target_ids=[],
        reported_total=None,
        continuation_visible=False,
        origin_identity_outcome="boundary_invalid",
        dispatched=False,
        derived_from_identity_request=True,
    )
    forward = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=BINDING_B,
        origin_body_sha256=None,
        origin_normalized_payload_sha256=None,
        request_status="available",
        body_integrity_valid=True,
        target_ids=[],
        reported_total=None,
        continuation_visible=False,
        origin_identity_outcome="boundary_invalid",
        dispatched=False,
    )
    bodies = [_body_record(BINDING_A, BODY_A, payload)]
    replays = [_replay(BINDING_A, BODY_A, payload)]
    _write_body_root(tmp_path, bodies)
    result = compose_openalex_case_outcome(
        identity=identity,
        backward=backward,
        forward=forward,
        accepted_body_root=tmp_path,
        accepted_body_records=bodies,
        replay_records=replays,
    )
    assert result["global_status"] == "boundary_invalid"
    with pytest.raises(MissionStateError, match="coverage is not exact"):
        compose_openalex_case_outcome(
            identity=identity,
            backward=backward,
            forward=forward,
            accepted_body_root=tmp_path,
            accepted_body_records=bodies,
            replay_records=[],
        )


def test_frontier_forward_is_independent_of_nonselected_identity(tmp_path: Path) -> None:
    result = _case_inputs(identity_outcome="empty", forward_outcome="observed_results")
    assert result[1]["outcome"] == "not_observed"
    assert result[2]["outcome"] == "observed_results"
    composed = _compose(result, tmp_path)
    assert composed["identity_outcome"] == "empty"
    assert composed["forward_frontier_outcome"] == "observed_results"
    assert composed["m21_candidate_authority"] is False


def test_frontier_lexical_cap_duplicate_and_unresolved_accounting(tmp_path: Path) -> None:
    targets = ["W9", "W2", "W2", *[f"W{value}" for value in range(20, 29)]]
    payload = _payload(identity_status="not_applicable", frontier_targets=targets, reported_total=len(targets) + 3, continuation=True)
    result = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=BINDING_B,
        origin_body_sha256=BODY_B,
        origin_normalized_payload_sha256=_payload_sha(payload),
        request_status="available",
        body_integrity_valid=True,
        target_ids=targets,
        reported_total=len(targets) + 3,
        continuation_visible=True,
        origin_identity_outcome="selected",
    )
    assert result["outcome"] == "capped"
    assert result["target_rows"][2]["disposition"] == "duplicate_target"
    assert result["summary"]["omitted_by_cap_target_count"] == 1
    assert [row["normalized_target_id"] for row in result["target_rows"] if row["disposition"] == "omitted_by_cap"] == ["W9"]

    unresolved = _case_inputs(identity_outcome="ambiguous", backward_outcome="not_observed")
    assert unresolved[1]["summary"]["identity_unresolved_target_count"] == 1
    assert _compose(unresolved, tmp_path)["backward_frontier_outcome"] == "not_observed"


def test_nonselected_backward_retains_duplicate_malformed_and_remainder(tmp_path: Path) -> None:
    identity, _, forward, bodies, replays = _case_inputs(
        identity_outcome="ambiguous",
        backward_outcome="not_observed",
    )
    targets = ["W1", "W1", "bad"]
    payload = deepcopy(replays[0]["normalized_payload"])
    payload["frontier_target_ids"] = targets
    payload["frontier_reported_total"] = 5
    payload_sha = _payload_sha(payload)
    identity_request = identity["request_states"][0]
    identity_request["normalized_payload_sha256"] = payload_sha
    identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="W4387130479",
        topic=None,
        request_states=[identity_request],
    )
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=BINDING_A,
        origin_body_sha256=BODY_A,
        origin_normalized_payload_sha256=payload_sha,
        request_status="available",
        body_integrity_valid=True,
        target_ids=targets,
        reported_total=5,
        continuation_visible=False,
        origin_identity_outcome="ambiguous",
        derived_from_identity_request=True,
    )
    bodies[0]["normalized_payload_sha256"] = payload_sha
    replays[0] = _replay(BINDING_A, BODY_A, payload)
    result = _compose((identity, backward, forward, bodies, replays), tmp_path)
    assert result["backward_frontier_outcome"] == "not_observed"
    assert [row["disposition"] for row in backward["target_rows"]] == [
        "not_admitted_identity_unresolved",
        "duplicate_target",
        "malformed_target",
    ]
    assert backward["summary"]["unobserved_provider_remainder_count"] == 2


def test_frontier_cap_is_frozen_and_all_malformed_composes_as_boundary(tmp_path: Path) -> None:
    payload = _payload(identity_status="not_applicable", frontier_targets=["W1"])
    with pytest.raises(MissionStateError, match="frozen cap"):
        classify_frontier_attempt(
            direction="forward",
            origin_request_binding_sha256=BINDING_B,
            origin_body_sha256=BODY_B,
            origin_normalized_payload_sha256=_payload_sha(payload),
            request_status="available",
            body_integrity_valid=True,
            target_ids=["W1"],
            reported_total=1,
            continuation_visible=False,
            origin_identity_outcome="selected",
            target_cap=1,
        )
    identity, backward, _, bodies, replays = _case_inputs(
        identity_outcome="selected",
        backward_outcome="empty_observed",
    )
    malformed_payload = _payload(
        identity_status="not_applicable",
        frontier_targets=["bad"],
        frontier_status="boundary_invalid",
        reported_total=1,
    )
    malformed_forward = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=BINDING_B,
        origin_body_sha256=BODY_B,
        origin_normalized_payload_sha256=_payload_sha(malformed_payload),
        request_status="available",
        body_integrity_valid=True,
        target_ids=["bad"],
        reported_total=1,
        continuation_visible=False,
        origin_identity_outcome="selected",
    )
    bodies[-1] = _body_record(BINDING_B, BODY_B, malformed_payload)
    replays[-1] = _replay(BINDING_B, BODY_B, malformed_payload)
    _write_body_root(tmp_path, bodies)
    result = compose_openalex_case_outcome(
        identity=identity,
        backward=backward,
        forward=malformed_forward,
        accepted_body_root=tmp_path,
        accepted_body_records=bodies,
        replay_records=replays,
    )
    assert result["global_status"] == "boundary_invalid"


def test_mixed_valid_and_malformed_backward_targets_preserve_identity_and_veto(tmp_path: Path) -> None:
    identity, _, forward, bodies, replays = _case_inputs(
        identity_outcome="selected",
        backward_outcome="empty_observed",
        forward_outcome="not_dispatched_due_to_veto",
    )
    payload = deepcopy(replays[0]["normalized_payload"])
    payload["frontier_view_status"] = "boundary_invalid"
    payload["frontier_target_ids"] = ["W1", "bad", "W1", "W2"]
    payload["frontier_reported_total"] = 4
    payload_sha = _payload_sha(payload)
    identity["request_states"][0]["normalized_payload_sha256"] = payload_sha
    identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="W4387130479",
        topic=None,
        request_states=identity["request_states"],
    )
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=BINDING_A,
        origin_body_sha256=BODY_A,
        origin_normalized_payload_sha256=payload_sha,
        request_status="boundary_invalid",
        body_integrity_valid=True,
        target_ids=payload["frontier_target_ids"],
        reported_total=4,
        continuation_visible=False,
        origin_identity_outcome="selected",
        derived_from_identity_request=True,
    )
    bodies[0]["normalized_payload_sha256"] = payload_sha
    replays[0] = _replay(BINDING_A, BODY_A, payload)
    result = _compose((identity, backward, forward, bodies, replays), tmp_path)
    assert result["identity_outcome"] == "selected"
    assert result["backward_frontier_outcome"] == "boundary_invalid"
    assert result["global_status"] == "boundary_invalid"
    assert [row["disposition"] for row in backward["target_rows"]] == [
        "not_admitted_boundary_invalid",
        "malformed_target",
        "duplicate_target",
        "not_admitted_boundary_invalid",
    ]


@pytest.mark.parametrize(
    "mutation",
    ["different_duplicate", "valid_as_malformed", "lexical_swap", "risk_substitution"],
)
def test_composition_rejects_forged_frontier_dispositions_and_risks(
    mutation: str,
    tmp_path: Path,
) -> None:
    if mutation in {"different_duplicate", "valid_as_malformed"}:
        inputs = list(_case_inputs(backward_outcome="observed_results"))
        backward = inputs[1]
        row = deepcopy(backward["target_rows"][0])
        if mutation == "different_duplicate":
            row.update({"provider_list_index": 1, "normalized_target_id": "W2", "duplicate_of_provider_list_index": 0, "disposition": "duplicate_target"})
        else:
            row["disposition"] = "malformed_target"
        backward["target_rows"].append(row)
        backward["summary"]["returned_target_count"] += 1
        if mutation == "different_duplicate":
            backward["summary"]["unique_valid_target_count"] += 1
    elif mutation == "lexical_swap":
        inputs = list(_case_inputs(forward_outcome="capped"))
        forward = inputs[2]
        admitted = next(row for row in forward["target_rows"] if row["normalized_target_id"] == "W1")
        omitted = next(row for row in forward["target_rows"] if row["disposition"] == "omitted_by_cap")
        admitted["disposition"], omitted["disposition"] = omitted["disposition"], admitted["disposition"]
    else:
        inputs = list(_case_inputs(forward_outcome="empty_observed"))
        inputs[2]["attempt_risk_id"] = "or-" + "f" * 64
    with pytest.raises(MissionStateError):
        _compose(tuple(inputs), tmp_path)


def test_composition_requires_exact_body_replay_coverage_and_shared_direct_body(tmp_path: Path) -> None:
    inputs = list(_case_inputs(backward_outcome="observed_results", forward_outcome="observed_results"))
    result = _compose(tuple(inputs), tmp_path / "pass")
    assert result["schema_version"] == "ra-survey-m20-case-outcome-v3"
    assert result["accepted_body_replay_bindings"] == [BINDING_A, BINDING_B]
    assert result["m21_candidate_authority"] is True

    missing = deepcopy(inputs)
    missing[4] = missing[4][:-1]
    with pytest.raises(MissionStateError, match="coverage is not exact"):
        _compose(tuple(missing), tmp_path / "missing")

    unrelated = deepcopy(inputs)
    unrelated[1]["origin_body_sha256"] = "f" * 64
    for row in unrelated[1]["target_rows"]:
        row["origin_body_sha256"] = "f" * 64
    with pytest.raises(MissionStateError, match="differs from direct identity body"):
        _compose(tuple(unrelated), tmp_path / "unrelated")


@pytest.mark.parametrize("mutation", ["missing", "extra", "tampered"])
def test_final_authority_requires_exact_on_disk_body_inventory(
    mutation: str,
    tmp_path: Path,
) -> None:
    inputs = _case_inputs(backward_outcome="observed_results")
    identity, backward, forward, bodies, replays = inputs
    _write_body_root(tmp_path, bodies)
    if mutation == "missing":
        (tmp_path / bodies[0]["relative_path"]).unlink()
    elif mutation == "extra":
        (tmp_path / "accepted_bodies" / "extra.body").write_bytes(b"extra")
    else:
        (tmp_path / bodies[0]["relative_path"]).write_bytes(b"tamperedxx")
    with pytest.raises(MissionStateError):
        compose_openalex_case_outcome(
            identity=identity,
            backward=backward,
            forward=forward,
            accepted_body_root=tmp_path,
            accepted_body_records=bodies,
            replay_records=replays,
        )


def test_inventory_rejects_forged_per_body_and_aggregate_caps(tmp_path: Path) -> None:
    first = _body_record(BINDING_A, BODY_A, _payload())
    first["accepted_body_cap_bytes"] = 3_000_000
    with pytest.raises(MissionStateError, match="size or kind"):
        validate_accepted_body_inventory(tmp_path, body_records=[first])

    records = []
    for index in range(6):
        binding = f"{index + 1:064x}"
        records.append({
            **_body_record(binding, BODY_A, _payload()),
            "size_bytes": 2_000_000,
        })
    with pytest.raises(MissionStateError, match="frozen total cap"):
        validate_accepted_body_inventory(tmp_path, body_records=records)


@pytest.mark.parametrize("direction", ["backward", "forward"])
def test_boundary_invalid_replay_view_cannot_be_relabelled_observed(
    direction: str,
    tmp_path: Path,
) -> None:
    inputs = list(_case_inputs())
    index = 0 if direction == "backward" else 1
    replay = inputs[4][index]
    replay["normalized_payload"]["frontier_view_status"] = "boundary_invalid"
    digest = _payload_sha(replay["normalized_payload"])
    replay["normalized_payload_sha256"] = digest
    inputs[3][index]["normalized_payload_sha256"] = digest
    if direction == "backward":
        inputs[0]["request_states"][0]["normalized_payload_sha256"] = digest
        inputs[0] = classify_identity_outcome(
            case_kind="explicit_openalex",
            expected_identifier="W4387130479",
            topic=None,
            request_states=inputs[0]["request_states"],
        )
        inputs[1]["origin_normalized_payload_sha256"] = digest
    else:
        inputs[2]["origin_normalized_payload_sha256"] = digest
    with pytest.raises(MissionStateError, match="applicable view"):
        _compose(tuple(inputs), tmp_path)


def test_replay_payload_cannot_be_replaced_by_matching_shape_only(tmp_path: Path) -> None:
    inputs = list(_case_inputs(backward_outcome="observed_results"))
    forged = deepcopy(inputs)
    forged[4][0]["normalized_payload"]["frontier_target_ids"] = ["W2"]
    forged[4][0]["normalized_payload_sha256"] = _payload_sha(forged[4][0]["normalized_payload"])
    forged[3][0]["normalized_payload_sha256"] = forged[4][0]["normalized_payload_sha256"]
    forged[0]["request_states"][0]["normalized_payload_sha256"] = forged[4][0]["normalized_payload_sha256"]
    forged[0] = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier="W4387130479",
        topic=None,
        request_states=forged[0]["request_states"],
    )
    forged[1]["origin_normalized_payload_sha256"] = forged[4][0]["normalized_payload_sha256"]
    with pytest.raises(MissionStateError, match="frontier outcome differs"):
        _compose(tuple(forged), tmp_path)


def test_pre_normalization_boundary_body_is_inventory_bound_without_replay(tmp_path: Path) -> None:
    identity, backward, _, bodies, replays = _case_inputs()
    boundary = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=BINDING_B,
        origin_body_sha256=BODY_B,
        origin_normalized_payload_sha256=None,
        request_status="available",
        body_integrity_valid=False,
        target_ids=[],
        reported_total=0,
        continuation_visible=False,
        origin_identity_outcome="selected",
    )
    unbound = _body_record(BINDING_B, BODY_B, _payload(identity_status="not_applicable"))
    unbound["normalized_payload_sha256"] = None
    bodies[-1] = unbound
    replays = [row for row in replays if row["request_binding_sha256"] != BINDING_B]
    _write_body_root(tmp_path, bodies)
    result = compose_openalex_case_outcome(
        identity=identity,
        backward=backward,
        forward=boundary,
        accepted_body_root=tmp_path,
        accepted_body_records=bodies,
        replay_records=replays,
    )
    assert result["global_status"] == "boundary_invalid"
    assert result["accepted_body_replay_passed"] is False
    assert result["accepted_body_replay_bindings"] == [BINDING_A]
    assert result["accepted_body_retained_unreplayed_bindings"] == [BINDING_B]


@pytest.mark.parametrize(
    ("identity_state", "backward_state", "forward_state"),
    [tuple(row) for row in outcome_automaton_manifest()["composition"]["permitted_openalex_tuples"]],
)
def test_every_permitted_automaton_row_closes_from_producers(
    identity_state: str,
    backward_state: str,
    forward_state: str,
    tmp_path: Path,
) -> None:
    result = _compose(_case_inputs(
        identity_outcome=identity_state,
        backward_outcome=backward_state,
        forward_outcome=forward_state,
    ), tmp_path)
    assert (
        result["identity_outcome"],
        result["backward_frontier_outcome"],
        result["forward_frontier_outcome"],
    ) == (identity_state, backward_state, forward_state)


def test_full_automaton_cartesian_space_is_permitted_or_rejected(tmp_path: Path) -> None:
    manifest = outcome_automaton_manifest()
    identity_states = manifest["identity_outcomes"]
    frontier_states = manifest["frontier_outcomes"]
    permitted = {
        tuple(row)
        for row in manifest["composition"]["permitted_openalex_tuples"]
    }
    observed_permitted: set[tuple[str, str, str]] = set()
    observed_rejected: set[tuple[str, str, str]] = set()

    for identity_state in identity_states:
        valid_inputs = _case_inputs(identity_outcome=identity_state)
        for backward_state in frontier_states:
            for forward_state in frontier_states:
                state = (identity_state, backward_state, forward_state)
                case_root = tmp_path / "-".join(state)
                if state in permitted:
                    result = _compose(_case_inputs(
                        identity_outcome=identity_state,
                        backward_outcome=backward_state,
                        forward_outcome=forward_state,
                    ), case_root)
                    assert (
                        result["identity_outcome"],
                        result["backward_frontier_outcome"],
                        result["forward_frontier_outcome"],
                    ) == state
                    observed_permitted.add(state)
                    continue

                inputs = list(valid_inputs)
                inputs[0] = dict(inputs[0], outcome=identity_state)
                inputs[1] = dict(inputs[1], outcome=backward_state)
                inputs[2] = dict(inputs[2], outcome=forward_state)
                with pytest.raises(MissionStateError):
                    _compose(tuple(inputs), case_root)
                observed_rejected.add(state)

    assert observed_permitted == permitted
    assert len(observed_permitted) == 40
    assert len(observed_rejected) == 254


def test_automaton_manifest_is_canonical_role_separated_and_complete() -> None:
    manifest = outcome_automaton_manifest()
    assert manifest["schema_version"] == "ra-survey-m20-outcome-automaton-v3"
    assert manifest["frontier_policy"]["target_cap"] == 10
    assert manifest["identity_equivalence"]["forward_rows_never_enter_identity_candidates"] is True
    assert manifest["frontier_policy"]["target_dispositions"] == sorted({
        "admitted",
        "omitted_by_cap",
        "duplicate_target",
        "malformed_target",
        "not_admitted_identity_unresolved",
        "not_admitted_boundary_invalid",
    })
    assert manifest["frontier_policy"]["boundary_invalid_targets"] == {
        "preserve_every_provider_index": True,
        "valid_unique_disposition": "not_admitted_boundary_invalid",
        "duplicate_disposition": "duplicate_target",
        "malformed_disposition": "malformed_target",
        "admitted_target_count": 0,
    }
    allowed = {tuple(row) for row in manifest["composition"]["permitted_openalex_tuples"]}
    assert len(allowed) == 40
    assert outcome_automaton_sha256() == "a1f3d6126de27880ebb9804dcb075091b9694fc9b8d36f005e327b29bdefc0b7"

    representative = {
        ("selected", "observed_results", "observed_results"),
        ("selected", "empty_observed", "provider_unavailable"),
        ("selected", "capped", "boundary_invalid"),
        ("empty", "not_observed", "observed_results"),
        ("ambiguous", "not_observed", "empty_observed"),
        ("capped", "not_observed", "capped"),
        ("unavailable", "provider_unavailable", "provider_unavailable"),
        ("boundary_invalid", "not_dispatched_due_to_veto", "not_dispatched_due_to_veto"),
    }
    assert representative <= allowed
