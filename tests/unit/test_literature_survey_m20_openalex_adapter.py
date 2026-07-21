from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey.discovery_capability import (
    bind_normalized_payload,
    classify_frontier_attempt,
    classify_identity_outcome,
    compose_openalex_case_outcome,
    replay_accepted_body,
    write_accepted_body,
)
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes
from research_assistant.survey.openalex_adapter import (
    DESCRIPTOR_SCHEMA,
    FROZEN_SELECT,
    build_openalex_direct_descriptor,
    build_openalex_forward_descriptor,
    build_openalex_topic_descriptor,
    parse_openalex_direct_response,
    parse_openalex_forward_response,
    parse_openalex_topic_response,
    validate_openalex_descriptor,
)


TOPIC = "Neural Optimal Transport for generative modeling and inference"
WORK_ID = "W4387130479"
BINDING_A = "a" * 64
BINDING_B = "b" * 64


def _work(*, work_id: str = WORK_ID, lineage: list[object] | None = None, title: str = TOPIC) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": title,
        "authorships": [{"author": {"display_name": "Alice Example"}, "author_position": "first"}],
        "publication_year": 2022,
        "doi": "https://doi.org/10.1000/neural-ot",
        "cited_by_count": 12,
        "referenced_works": [] if lineage is None else lineage,
        "ids": {
            "openalex": f"https://openalex.org/{work_id}",
            "doi": "https://doi.org/10.1000/neural-ot",
        },
        "type": "article",
        "publication_date": "2022-01-01",
    }


def _list(results: list[object], *, count: int | None = None, cursor: str | None = None) -> bytes:
    payload = {
        "meta": {
            "count": len(results) if count is None else count,
            "db_response_time_ms": 3,
            "page": 1,
            "per_page": 10,
            "next_cursor": cursor,
            "groups_count": 0,
            "cost_usd": 0.0001,
        },
        "results": results,
        "group_by": [],
    }
    return canonical_json_bytes(payload)


def _identity_request(payload: dict, *, binding: str, body_sha: str) -> dict:
    payload_sha = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {
        "request_binding_sha256": binding,
        "provider": "openalex",
        "required": True,
        "status": "available",
        "envelope_complete": payload["identity_envelope_complete"],
        "cap_exceeded": payload["identity_cap_exceeded"],
        "body_sha256": body_sha,
        "normalized_payload_sha256": payload_sha,
        "records": payload["identity_records"],
        "malformed_row_sha256s": payload["malformed_row_sha256s"],
        "malformed_row_count": len(payload["malformed_row_sha256s"]),
    }


def test_descriptors_are_exact_non_executable_and_use_official_syntax() -> None:
    topic = build_openalex_topic_descriptor(TOPIC)
    direct = build_openalex_direct_descriptor(f"openalex:{WORK_ID}")
    forward = build_openalex_forward_descriptor(f"https://openalex.org/{WORK_ID}")
    assert topic == {
        "schema_version": DESCRIPTOR_SCHEMA,
        "provider": "openalex",
        "route_kind": "topic_list",
        "method": "GET",
        "host": "api.openalex.org",
        "path_segments": ["works"],
        "ordered_query_parameters": [
            ["search", TOPIC],
            ["per_page", "10"],
            ["select", FROZEN_SELECT],
        ],
        "api_key_requirement": "required_external_not_present",
        "response_role": "topic_identity",
    }
    assert direct["path_segments"] == ["works", WORK_ID]
    assert direct["ordered_query_parameters"] == [["select", FROZEN_SELECT]]
    assert forward["ordered_query_parameters"] == [
        ["filter", f"cites:{WORK_ID}"],
        ["per_page", "10"],
        ["sort", "-cited_by_count"],
        ["select", FROZEN_SELECT],
    ]
    forbidden = {"url", "headers", "cookies", "auth", "authorization", "secret", "api_key", "callback", "opener"}
    for descriptor in (topic, direct, forward):
        assert not forbidden & set(descriptor)
        assert all(name != "api_key" for name, _ in descriptor["ordered_query_parameters"])
        assert "per-page" not in json.dumps(descriptor)
        assert "cited_by_count:desc" not in json.dumps(descriptor)


def test_adapter_module_has_no_network_environment_or_credential_imports() -> None:
    path = Path("src/research_assistant/survey/openalex_adapter.py")
    tree = ast.parse(path.read_text())
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported & {"urllib", "http", "socket", "ssl", "requests", "os", "subprocess"}
    source = path.read_text()
    assert "getenv" not in source
    assert "urlopen" not in source
    assert "requests." not in source


@pytest.mark.parametrize("builder,args", [
    (build_openalex_topic_descriptor, (TOPIC,)),
    (build_openalex_forward_descriptor, (WORK_ID,)),
])
def test_descriptor_rejects_cap_drift(builder, args) -> None:  # noqa: ANN001
    with pytest.raises(MissionStateError, match="frozen cap"):
        builder(*args, per_page=9)


def test_topic_descriptor_rejects_url_string() -> None:
    with pytest.raises(MissionStateError, match="cannot contain a URL"):
        build_openalex_topic_descriptor("https://example.org/research")


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "api_key",
        "legacy_sort",
        "bad_path",
        "empty_query",
        "topic_whitespace",
        "topic_url",
        "forward_url_id",
        "forward_lowercase",
    ],
)
def test_descriptor_validation_rejects_executable_or_stale_shapes(mutation: str) -> None:
    descriptor = (
        build_openalex_topic_descriptor(TOPIC)
        if mutation in {"topic_whitespace", "topic_url"}
        else build_openalex_forward_descriptor(WORK_ID)
    )
    if mutation == "extra":
        descriptor["headers"] = {}
    elif mutation == "api_key":
        descriptor["ordered_query_parameters"].append(["api_key", "secret"])
    elif mutation == "legacy_sort":
        descriptor["ordered_query_parameters"][2][1] = "cited_by_count:desc"
    elif mutation == "bad_path":
        descriptor["path_segments"] = ["works", "other"]
    elif mutation == "empty_query":
        descriptor["ordered_query_parameters"] = []
    elif mutation == "topic_whitespace":
        descriptor["ordered_query_parameters"][0][1] = f"  {TOPIC}  "
    elif mutation == "topic_url":
        descriptor["ordered_query_parameters"][0][1] = "https://example.org/research"
    elif mutation == "forward_url_id":
        descriptor["ordered_query_parameters"][0][1] = "cites:https://openalex.org/W4387130479"
    else:
        descriptor["ordered_query_parameters"][0][1] = "cites:w4387130479"
    with pytest.raises(MissionStateError):
        validate_openalex_descriptor(descriptor)


def test_topic_parser_emits_exact_identity_roles_and_provenance() -> None:
    payload = parse_openalex_topic_response(_list([_work()]), topic=TOPIC)
    assert payload["identity_view_status"] == "observed"
    assert payload["frontier_view_status"] == "not_applicable"
    assert payload["identity_cap_exceeded"] is False
    record = payload["identity_records"][0]
    assert record["roles"] == ["seed"]
    assert record["openalex_id"] == WORK_ID
    assert record["provider_records"][0]["query_kind"] == "identity_resolution"
    assert record["query_provenance"] == [{
        "provider": "openalex",
        "query_kind": "identity_resolution",
        "normalized_seed_key": TOPIC.casefold(),
        "topic_query": True,
    }]


def test_topic_parser_retains_canonical_malformed_row_evidence() -> None:
    malformed = _work(work_id="bad")
    payload = parse_openalex_topic_response(_list([malformed, malformed]), topic=TOPIC)
    expected = hashlib.sha256(canonical_json_bytes(malformed)).hexdigest()
    assert payload["identity_records"] == []
    assert payload["malformed_row_sha256s"] == [expected]


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("count", True),
        ("page", 2),
        ("per_page", 9),
        ("next_cursor", "cursor-without-remainder"),
        ("cost_usd", True),
    ],
)
def test_list_parser_rejects_strict_meta_conflicts(mutation: str, value: object) -> None:
    raw = json.loads(_list([_work()]))
    raw["meta"][mutation] = value
    with pytest.raises(MissionStateError):
        parse_openalex_topic_response(canonical_json_bytes(raw), topic=TOPIC)


@pytest.mark.parametrize("missing", ["meta", "results", "group_by"])
def test_list_parser_rejects_missing_envelope_fields(missing: str) -> None:
    raw = json.loads(_list([]))
    del raw[missing]
    with pytest.raises(MissionStateError, match="keys are not exact"):
        parse_openalex_forward_response(canonical_json_bytes(raw))


@pytest.mark.parametrize("body", [b"\xff", b"not-json", b"[]"])
def test_parser_rejects_invalid_body_or_top_level(body: bytes) -> None:
    with pytest.raises(MissionStateError):
        parse_openalex_forward_response(body)


@pytest.mark.parametrize(
    "body",
    [
        b'{"meta":{},"meta":{},"results":[],"group_by":[]}',
        b'{"meta":{"count":NaN},"results":[],"group_by":[]}',
    ],
)
def test_parser_rejects_duplicate_keys_and_nonfinite_numbers(body: bytes) -> None:
    with pytest.raises(MissionStateError):
        parse_openalex_forward_response(body)


def test_parser_rejects_exponent_overflow_in_envelope_and_row() -> None:
    with pytest.raises(MissionStateError):
        parse_openalex_forward_response(
            b'{"meta":{"count":0,"db_response_time_ms":1,"page":1,"per_page":10,"next_cursor":null,"groups_count":0,"cost_usd":1e999},"results":[],"group_by":[]}'
        )
    raw = _list([_work()]).replace(b'"cited_by_count":12', b'"cited_by_count":1e999')
    with pytest.raises(MissionStateError):
        parse_openalex_topic_response(raw, topic=TOPIC)


def test_topic_and_forward_cap_continuation_mapping() -> None:
    topic = parse_openalex_topic_response(_list([_work()], count=12), topic=TOPIC)
    forward = parse_openalex_forward_response(_list([_work(work_id="W2")], count=12))
    assert topic["identity_cap_exceeded"] is True
    assert forward["frontier_reported_total"] == 12
    assert forward["frontier_continuation_visible"] is True
    assert forward["identity_view_status"] == "not_applicable"


def test_forward_parser_preserves_malformed_provider_index_as_null_target() -> None:
    payload = parse_openalex_forward_response(_list([_work(work_id="W2"), _work(work_id="bad"), _work(work_id="W3")]))
    assert payload["identity_records"] == []
    assert payload["malformed_row_sha256s"] == []
    assert payload["frontier_target_ids"] == ["W2", None, "W3"]


@pytest.mark.parametrize("field,value", [
    ("publication_year", True),
    ("cited_by_count", True),
    ("authorships", [{}]),
    ("ids", {"unknown": "x"}),
])
def test_work_parser_rejects_strict_selected_field_types(field: str, value: object) -> None:
    work = _work()
    work[field] = value
    payload = parse_openalex_topic_response(_list([work]), topic=TOPIC)
    assert payload["identity_records"] == []
    assert len(payload["malformed_row_sha256s"]) == 1


def test_ids_schema_rejects_undocumented_arxiv_alias_and_accepts_integer_mag() -> None:
    unsupported = _work()
    unsupported["ids"]["arxiv"] = "2201.12220"
    payload = parse_openalex_topic_response(_list([unsupported]), topic=TOPIC)
    assert payload["identity_records"] == []
    assert len(payload["malformed_row_sha256s"]) == 1

    supported = _work()
    supported["ids"]["mag"] = 123
    payload = parse_openalex_topic_response(_list([supported]), topic=TOPIC)
    assert payload["identity_records"][0]["arxiv_id"] is None


def test_homonymous_authors_are_stably_deduplicated_for_downstream_schema() -> None:
    work = _work()
    work["authorships"] = [
        {"author": {"display_name": "Alex Lee"}},
        {"author": {"display_name": "Alex Lee"}},
        {"author": {"display_name": "Sam Kim"}},
    ]
    payload = parse_openalex_topic_response(_list([work]), topic=TOPIC)
    assert payload["identity_records"][0]["authors"] == ["Alex Lee", "Sam Kim"]


def test_direct_parser_requires_exact_requested_identity() -> None:
    with pytest.raises(MissionStateError, match="differs from the request"):
        parse_openalex_direct_response(canonical_json_bytes(_work(work_id="W2")), expected_openalex_id=WORK_ID)


def test_direct_parser_decouples_identity_from_malformed_backward_lineage_and_replays(tmp_path: Path) -> None:
    body = canonical_json_bytes(_work(lineage=[
        "https://openalex.org/W1",
        "bad",
        "https://openalex.org/W1",
        "https://openalex.org/W2",
    ]))
    payload = parse_openalex_direct_response(body, expected_openalex_id=WORK_ID)
    assert payload["identity_view_status"] == "observed"
    assert payload["frontier_view_status"] == "boundary_invalid"
    assert payload["identity_records"][0]["referenced_works"] == ["W1", "W2"]
    assert payload["frontier_target_ids"] == [
        "https://openalex.org/W1",
        "bad",
        "https://openalex.org/W1",
        "https://openalex.org/W2",
    ]

    body_record = write_accepted_body(tmp_path, request_binding_sha256=BINDING_A, body=body)
    bound = bind_normalized_payload(body_record, payload)
    replay = replay_accepted_body(
        tmp_path,
        body_record=bound,
        parser=lambda raw: parse_openalex_direct_response(raw, expected_openalex_id=WORK_ID),
    )
    identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier=WORK_ID,
        topic=None,
        request_states=[_identity_request(payload, binding=BINDING_A, body_sha=bound["sha256"])],
    )
    assert identity["outcome"] == "selected"
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=BINDING_A,
        origin_body_sha256=bound["sha256"],
        origin_normalized_payload_sha256=bound["normalized_payload_sha256"],
        request_status="boundary_invalid",
        body_integrity_valid=True,
        target_ids=payload["frontier_target_ids"],
        reported_total=payload["frontier_reported_total"],
        continuation_visible=False,
        origin_identity_outcome=identity["outcome"],
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
        origin_identity_outcome=identity["outcome"],
        dispatched=False,
    )
    result = compose_openalex_case_outcome(
        identity=identity,
        backward=backward,
        forward=forward,
        accepted_body_root=tmp_path,
        accepted_body_records=[bound],
        replay_records=[replay],
    )
    assert result["identity_outcome"] == "selected"
    assert result["backward_frontier_outcome"] == "boundary_invalid"
    assert result["global_status"] == "boundary_invalid"
    assert [row["disposition"] for row in backward["target_rows"]] == [
        "not_admitted_boundary_invalid",
        "malformed_target",
        "duplicate_target",
        "not_admitted_boundary_invalid",
    ]


def test_topic_parser_integrates_with_identity_classifier() -> None:
    body = _list([_work()])
    payload = parse_openalex_topic_response(body, topic=TOPIC)
    body_sha = hashlib.sha256(body).hexdigest()
    outcome = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            {
                **_identity_request(payload, binding=BINDING_A, body_sha=body_sha),
                "provider": "openalex",
            },
            {
                "request_binding_sha256": BINDING_B,
                "provider": "arxiv",
                "required": True,
                "status": "unavailable",
                "envelope_complete": True,
                "cap_exceeded": False,
                "body_sha256": None,
                "normalized_payload_sha256": None,
                "records": [],
                "malformed_row_sha256s": [],
                "malformed_row_count": 0,
            },
        ],
    )
    assert outcome["outcome"] == "ambiguous"


@pytest.mark.parametrize(
    "bad_id",
    [
        "W1",
        "https://evil.example/W1",
        "http://openalex.org/W1",
        "https://user@openalex.org/W1",
        "https://openalex.org:443/W1",
        "https://openalex.org/w1",
        "https://openalex.org/W1/",
        "https://openalex.org/W1?x=1",
        "https://openalex.org/W1#x",
        "https://openalex.org/works/W1",
    ],
)
def test_provider_response_ids_require_exact_canonical_openalex_url(bad_id: str) -> None:
    work = _work()
    work["id"] = bad_id
    work["ids"]["openalex"] = bad_id
    payload = parse_openalex_topic_response(_list([work]), topic=TOPIC)
    assert payload["identity_records"] == []
    assert len(payload["malformed_row_sha256s"]) == 1


@pytest.mark.parametrize(
    "bad_lineage",
    [
        "W2",
        "https://evil.example/W2",
        "http://openalex.org/W2",
        "https://openalex.org/w2",
        "https://openalex.org/W2?x=1",
    ],
)
def test_provider_lineage_ids_require_exact_canonical_openalex_url(bad_lineage: str) -> None:
    payload = parse_openalex_direct_response(
        canonical_json_bytes(_work(lineage=[bad_lineage])),
        expected_openalex_id=WORK_ID,
    )
    assert payload["identity_records"][0]["openalex_id"] == WORK_ID
    assert payload["identity_records"][0]["referenced_works"] == []
    assert payload["frontier_view_status"] == "boundary_invalid"
    assert payload["frontier_target_ids"] == [bad_lineage]


def test_provider_ids_openalex_requires_canonical_url_even_when_top_level_is_valid() -> None:
    work = _work()
    work["ids"]["openalex"] = WORK_ID
    payload = parse_openalex_topic_response(_list([work]), topic=TOPIC)
    assert payload["identity_records"] == []
    assert len(payload["malformed_row_sha256s"]) == 1


def test_topic_accepted_body_replay_integrates_with_identity_classifier(tmp_path: Path) -> None:
    body = _list([_work()])
    payload = parse_openalex_topic_response(body, topic=TOPIC)
    record = write_accepted_body(tmp_path, request_binding_sha256=BINDING_A, body=body)
    bound = bind_normalized_payload(record, payload)
    replay = replay_accepted_body(
        tmp_path,
        body_record=bound,
        parser=lambda raw: parse_openalex_topic_response(raw, topic=TOPIC),
    )
    outcome = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=[
            _identity_request(payload, binding=BINDING_A, body_sha=bound["sha256"]),
            {
                "request_binding_sha256": BINDING_B,
                "provider": "arxiv",
                "required": True,
                "status": "unavailable",
                "envelope_complete": True,
                "cap_exceeded": False,
                "body_sha256": None,
                "normalized_payload_sha256": None,
                "records": [],
                "malformed_row_sha256s": [],
                "malformed_row_count": 0,
            },
        ],
    )
    assert replay["normalized_payload"] == payload
    assert outcome["outcome"] == "ambiguous"


def test_forward_accepted_body_replay_classifies_cap_and_malformed_targets(tmp_path: Path) -> None:
    body = _list([_work(work_id="W2"), _work(work_id="bad"), _work(work_id="W3")], count=12)
    payload = parse_openalex_forward_response(body)
    record = write_accepted_body(tmp_path, request_binding_sha256=BINDING_B, body=body)
    bound = bind_normalized_payload(record, payload)
    replay = replay_accepted_body(
        tmp_path,
        body_record=bound,
        parser=parse_openalex_forward_response,
    )
    frontier = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=BINDING_B,
        origin_body_sha256=bound["sha256"],
        origin_normalized_payload_sha256=bound["normalized_payload_sha256"],
        request_status="available",
        body_integrity_valid=True,
        target_ids=payload["frontier_target_ids"],
        reported_total=payload["frontier_reported_total"],
        continuation_visible=payload["frontier_continuation_visible"],
        origin_identity_outcome="selected",
    )
    assert replay["normalized_payload"] == payload
    assert frontier["outcome"] == "capped"
    assert frontier["summary"]["unobserved_provider_remainder_count"] == 9
    assert [row["disposition"] for row in frontier["target_rows"]] == [
        "admitted",
        "malformed_target",
        "admitted",
    ]
