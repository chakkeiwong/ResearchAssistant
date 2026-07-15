from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from research_assistant.survey.discovery_quality import (
    normalize_doi,
    normalize_openalex_id,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    normalize_text,
)


DESCRIPTOR_SCHEMA = "ra-survey-m20-openalex-request-descriptor-v1"
FROZEN_SELECT_FIELDS = (
    "id",
    "display_name",
    "authorships",
    "publication_year",
    "doi",
    "cited_by_count",
    "referenced_works",
    "ids",
    "type",
    "publication_date",
)
FROZEN_SELECT = ",".join(FROZEN_SELECT_FIELDS)
LIST_CAP = 10
DESCRIPTOR_KEYS = {
    "schema_version",
    "provider",
    "route_kind",
    "method",
    "host",
    "path_segments",
    "ordered_query_parameters",
    "api_key_requirement",
    "response_role",
}
ROUTE_ROLES = {
    "topic_list": "topic_identity",
    "direct_singleton": "direct_identity_and_backward",
    "forward_list": "forward_frontier",
}
WORK_KEYS = set(FROZEN_SELECT_FIELDS)
IDS_KEYS = {"openalex", "doi", "mag", "pmid", "pmcid"}
META_KEYS = {
    "count",
    "db_response_time_ms",
    "page",
    "per_page",
    "next_cursor",
    "groups_count",
    "cost_usd",
}
LIST_RESPONSE_KEYS = {"meta", "results", "group_by"}
NORMALIZED_RESPONSE_KEYS = {
    "identity_view_status",
    "identity_records",
    "malformed_row_sha256s",
    "identity_envelope_complete",
    "identity_cap_exceeded",
    "frontier_view_status",
    "frontier_target_ids",
    "frontier_reported_total",
    "frontier_continuation_visible",
}
CANONICAL_OPENALEX_RESPONSE_ID = re.compile(r"^https://openalex\.org/(W[0-9]+)$")


def _fail(message: str) -> None:
    raise MissionStateError("m20_openalex_adapter_invalid", message)


def _exact_dict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _fail(f"{label} keys are not exact")
    return value


def _strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} is invalid")
    return value


def _nullable_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"{label} is invalid")
    return " ".join(value.split())


def _nonblank_string(value: Any, label: str) -> str:
    result = _nullable_string(value, label)
    if result is None:
        _fail(f"{label} is required")
    return result


def _strict_response_openalex_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or "\x00" in value:
        _fail(f"{label} is invalid")
    match = CANONICAL_OPENALEX_RESPONSE_ID.fullmatch(value)
    if match is None:
        _fail(f"{label} is not a canonical OpenAlex URL")
    return match.group(1)


def _descriptor(
    *,
    route_kind: str,
    path_segments: list[str],
    query: list[list[str]],
) -> dict[str, Any]:
    value = {
        "schema_version": DESCRIPTOR_SCHEMA,
        "provider": "openalex",
        "route_kind": route_kind,
        "method": "GET",
        "host": "api.openalex.org",
        "path_segments": path_segments,
        "ordered_query_parameters": query,
        "api_key_requirement": "required_external_not_present",
        "response_role": ROUTE_ROLES[route_kind],
    }
    return validate_openalex_descriptor(value)


def build_openalex_topic_descriptor(topic: str, *, per_page: int = LIST_CAP) -> dict[str, Any]:
    if per_page != LIST_CAP:
        _fail("topic list cap differs from the frozen cap")
    normalized = normalize_text(topic, field="topic")["display"]
    if "://" in normalized:
        _fail("topic descriptor cannot contain a URL")
    return _descriptor(
        route_kind="topic_list",
        path_segments=["works"],
        query=[
            ["search", normalized],
            ["per_page", str(LIST_CAP)],
            ["select", FROZEN_SELECT],
        ],
    )


def build_openalex_direct_descriptor(openalex_id: str) -> dict[str, Any]:
    normalized = normalize_openalex_id(openalex_id)
    if normalized is None:
        _fail("direct OpenAlex identifier is absent")
    return _descriptor(
        route_kind="direct_singleton",
        path_segments=["works", normalized],
        query=[["select", FROZEN_SELECT]],
    )


def build_openalex_forward_descriptor(openalex_id: str, *, per_page: int = LIST_CAP) -> dict[str, Any]:
    if per_page != LIST_CAP:
        _fail("forward list cap differs from the frozen cap")
    normalized = normalize_openalex_id(openalex_id)
    if normalized is None:
        _fail("forward OpenAlex identifier is absent")
    return _descriptor(
        route_kind="forward_list",
        path_segments=["works"],
        query=[
            ["filter", f"cites:{normalized}"],
            ["per_page", str(LIST_CAP)],
            ["sort", "-cited_by_count"],
            ["select", FROZEN_SELECT],
        ],
    )


def validate_openalex_descriptor(value: Any) -> dict[str, Any]:
    row = _exact_dict(value, DESCRIPTOR_KEYS, "OpenAlex descriptor")
    route = row["route_kind"]
    if (
        row["schema_version"] != DESCRIPTOR_SCHEMA
        or row["provider"] != "openalex"
        or route not in ROUTE_ROLES
        or row["method"] != "GET"
        or row["host"] != "api.openalex.org"
        or row["api_key_requirement"] != "required_external_not_present"
        or row["response_role"] != ROUTE_ROLES[route]
    ):
        _fail("OpenAlex descriptor constants are invalid")
    path = row["path_segments"]
    query = row["ordered_query_parameters"]
    if (
        not isinstance(path, list)
        or not path
        or any(not isinstance(item, str) or not item or "/" in item or "?" in item for item in path)
        or not isinstance(query, list)
        or any(
            not isinstance(item, list)
            or len(item) != 2
            or any(not isinstance(part, str) or not part or "\x00" in part for part in item)
            for item in query
        )
    ):
        _fail("OpenAlex descriptor path or query is invalid")
    if any(name == "api_key" for name, _ in query):
        _fail("OpenAlex descriptor contains a credential parameter")
    expected_path = ["works"]
    expected_query: list[list[str]]
    if route == "topic_list":
        if len(query) != 3:
            _fail("topic descriptor differs from the route contract")
        expected_query = [["search", query[0][1]], ["per_page", "10"], ["select", FROZEN_SELECT]]
        normalized_topic = normalize_text(query[0][1], field="topic")["display"]
        if query != expected_query or query[0][1] != normalized_topic or "://" in normalized_topic:
            _fail("topic descriptor differs from the route contract")
    elif route == "direct_singleton":
        if len(path) != 2 or path[0] != "works" or normalize_openalex_id(path[1]) != path[1]:
            _fail("direct descriptor path differs from the route contract")
        expected_path = path
        expected_query = [["select", FROZEN_SELECT]]
        if query != expected_query:
            _fail("direct descriptor query differs from the route contract")
    else:
        if len(query) != 4:
            _fail("forward descriptor differs from the route contract")
        expected_query = [
            ["filter", query[0][1]],
            ["per_page", "10"],
            ["sort", "-cited_by_count"],
            ["select", FROZEN_SELECT],
        ]
        if query != expected_query or not query[0][1].startswith("cites:"):
            _fail("forward descriptor differs from the route contract")
        filter_id = query[0][1].split(":", 1)[1]
        normalized_filter_id = normalize_openalex_id(filter_id)
        if normalized_filter_id is None or query[0][1] != f"cites:{normalized_filter_id}":
            _fail("forward descriptor filter identifier is invalid")
    if path != expected_path:
        _fail("OpenAlex descriptor path differs from the route contract")
    return {
        **row,
        "path_segments": list(path),
        "ordered_query_parameters": [list(item) for item in query],
    }


def _decode_json(body: bytes) -> Any:
    if not isinstance(body, bytes):
        _fail("OpenAlex body must be bytes")
    try:
        text = body.decode("utf-8")
        def exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    _fail("OpenAlex JSON contains a duplicate object key")
                result[key] = value
            return result

        def finite_float(value: str) -> float:
            parsed = float(value)
            if not math.isfinite(parsed):
                _fail("OpenAlex JSON contains a non-finite number")
            return parsed

        return json.loads(
            text,
            object_pairs_hook=exact_object,
            parse_constant=lambda _: _fail("OpenAlex JSON contains a non-finite number"),
            parse_float=finite_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("m20_openalex_adapter_invalid", "OpenAlex body is not valid UTF-8 JSON") from exc


def _normalize_ids(value: Any, *, openalex_id: str, top_level_doi: Any) -> str | None:
    if not isinstance(value, dict) or not set(value) <= IDS_KEYS:
        _fail("OpenAlex ids object is invalid")
    for key, item in value.items():
        if key == "mag":
            if item is not None and (type(item) is not int or item < 0):
                _fail("OpenAlex MAG identifier is invalid")
        elif item is not None and (not isinstance(item, str) or not item.strip()):
            _fail("OpenAlex ids value is invalid")
    observed_openalex = value.get("openalex")
    if observed_openalex is not None and _strict_response_openalex_id(
        observed_openalex,
        "OpenAlex ids.openalex",
    ) != openalex_id:
        _fail("OpenAlex ids object conflicts with the top-level identifier")
    try:
        top_doi = normalize_doi(top_level_doi)
        ids_doi = normalize_doi(value.get("doi"))
    except MissionStateError as exc:
        raise MissionStateError("m20_openalex_adapter_invalid", "OpenAlex external identifier is invalid") from exc
    if top_doi is not None and ids_doi is not None and top_doi != ids_doi:
        _fail("OpenAlex DOI fields conflict")
    return top_doi or ids_doi


def _normalize_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        _fail("OpenAlex authorships must be a list")
    authors = []
    for item in value:
        if not isinstance(item, dict):
            _fail("OpenAlex authorship is invalid")
        author = item.get("author")
        if not isinstance(author, dict):
            _fail("OpenAlex authorship author is invalid")
        authors.append(_nonblank_string(author.get("display_name"), "OpenAlex author display name"))
    return list(dict.fromkeys(authors))


def _normalize_lineage(value: Any, *, strict: bool) -> tuple[list[Any], list[str], bool]:
    if not isinstance(value, list):
        _fail("OpenAlex referenced_works must be a list")
    raw = list(value)
    normalized: list[str] = []
    invalid = False
    for item in raw:
        try:
            target = _strict_response_openalex_id(item, "OpenAlex referenced work")
        except MissionStateError:
            target = None
        if target is None:
            invalid = True
        else:
            normalized.append(target)
    if strict and invalid:
        _fail("OpenAlex referenced_works contains an invalid identifier")
    return raw, sorted(set(normalized)), invalid


def _normalize_work(
    value: Any,
    *,
    role: str,
    topic: str | None,
    expected_openalex_id: str | None,
    strict_lineage: bool,
) -> tuple[dict[str, Any], list[Any], bool]:
    row = _exact_dict(value, WORK_KEYS, "OpenAlex selected work")
    openalex_id = _strict_response_openalex_id(row["id"], "OpenAlex work identifier")
    if expected_openalex_id is not None and openalex_id != expected_openalex_id:
        _fail("OpenAlex work identifier differs from the request")
    title = _nonblank_string(row["display_name"], "OpenAlex display_name")
    authors = _normalize_authors(row["authorships"])
    year = row["publication_year"]
    if year is not None and (type(year) is not int or not 1000 <= year <= 3000):
        _fail("OpenAlex publication_year is invalid")
    citations = row["cited_by_count"]
    if citations is not None and (type(citations) is not int or citations < 0):
        _fail("OpenAlex cited_by_count is invalid")
    doi = _normalize_ids(row["ids"], openalex_id=openalex_id, top_level_doi=row["doi"])
    work_type = _nullable_string(row["type"], "OpenAlex type")
    publication_date = _nullable_string(row["publication_date"], "OpenAlex publication_date")
    raw_lineage, valid_lineage, invalid_lineage = _normalize_lineage(
        row["referenced_works"],
        strict=strict_lineage,
    )
    topic_query = topic is not None
    seed_key = normalize_text(topic, field="topic")["key"] if topic_query else None
    record = {
        "record_key": f"openalex:{openalex_id.casefold()}",
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi,
        "arxiv_id": None,
        "openalex_id": openalex_id,
        "landing_page_url": f"https://openalex.org/{openalex_id}",
        "citation_count": citations,
        "providers": ["openalex"],
        "roles": [role],
        "provider_records": [{
            "provider": "openalex",
            "query_kind": "identity_resolution",
            "source_id": openalex_id,
            "citation_count": citations,
            "publication_date": publication_date,
            "work_type": work_type,
        }],
        "referenced_works": valid_lineage,
        "query_provenance": [{
            "provider": "openalex",
            "query_kind": "identity_resolution",
            "normalized_seed_key": seed_key,
            "topic_query": topic_query,
        }],
    }
    return record, raw_lineage, invalid_lineage


def _validate_list_envelope(value: Any) -> tuple[dict[str, Any], list[Any], bool]:
    row = _exact_dict(value, LIST_RESPONSE_KEYS, "OpenAlex list response")
    meta = _exact_dict(row["meta"], META_KEYS, "OpenAlex list meta")
    results = row["results"]
    if not isinstance(results, list) or len(results) > LIST_CAP or not isinstance(row["group_by"], list):
        _fail("OpenAlex list arrays are invalid")
    count = _strict_int(meta["count"], "OpenAlex meta.count")
    _strict_int(meta["db_response_time_ms"], "OpenAlex meta.db_response_time_ms")
    page = _strict_int(meta["page"], "OpenAlex meta.page", minimum=1)
    per_page = _strict_int(meta["per_page"], "OpenAlex meta.per_page", minimum=1)
    _strict_int(meta["groups_count"], "OpenAlex meta.groups_count")
    cost = meta["cost_usd"]
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
        _fail("OpenAlex meta.cost_usd is invalid")
    cursor = meta["next_cursor"]
    if cursor is not None and (not isinstance(cursor, str) or not cursor.strip()):
        _fail("OpenAlex meta.next_cursor is invalid")
    if count < len(results) or page != 1 or per_page != LIST_CAP:
        _fail("OpenAlex list meta conflicts with the request or results")
    if cursor is not None and count <= len(results):
        _fail("OpenAlex cursor contradicts the result count")
    continuation = count > len(results) or count > LIST_CAP or cursor is not None
    return meta, list(results), continuation


def _empty_payload() -> dict[str, Any]:
    return {
        "identity_view_status": "not_applicable",
        "identity_records": [],
        "malformed_row_sha256s": [],
        "identity_envelope_complete": True,
        "identity_cap_exceeded": False,
        "frontier_view_status": "not_applicable",
        "frontier_target_ids": [],
        "frontier_reported_total": None,
        "frontier_continuation_visible": False,
    }


def parse_openalex_topic_response(body: bytes, *, topic: str) -> dict[str, Any]:
    meta, results, continuation = _validate_list_envelope(_decode_json(body))
    records = []
    malformed = []
    for raw in results:
        try:
            record, _, _ = _normalize_work(
                raw,
                role="seed",
                topic=topic,
                expected_openalex_id=None,
                strict_lineage=True,
            )
            records.append(record)
        except MissionStateError:
            try:
                malformed.append(hashlib.sha256(canonical_json_bytes(raw)).hexdigest())
            except (TypeError, ValueError) as exc:
                raise MissionStateError(
                    "m20_openalex_adapter_invalid",
                    "OpenAlex malformed row is not canonically serializable",
                ) from exc
    return {
        **_empty_payload(),
        "identity_view_status": "observed",
        "identity_records": records,
        "malformed_row_sha256s": sorted(set(malformed)),
        "identity_cap_exceeded": continuation or meta["count"] > len(results),
    }


def parse_openalex_direct_response(body: bytes, *, expected_openalex_id: str) -> dict[str, Any]:
    expected = normalize_openalex_id(expected_openalex_id)
    if expected is None:
        _fail("expected direct OpenAlex identifier is absent")
    record, raw_lineage, invalid_lineage = _normalize_work(
        _decode_json(body),
        role="direct_method",
        topic=None,
        expected_openalex_id=expected,
        strict_lineage=False,
    )
    return {
        **_empty_payload(),
        "identity_view_status": "observed",
        "identity_records": [record],
        "frontier_view_status": "boundary_invalid" if invalid_lineage else "observed",
        "frontier_target_ids": raw_lineage,
        "frontier_reported_total": len(raw_lineage),
    }


def parse_openalex_forward_response(body: bytes) -> dict[str, Any]:
    meta, results, continuation = _validate_list_envelope(_decode_json(body))
    targets: list[str | None] = []
    for raw in results:
        try:
            record, _, _ = _normalize_work(
                raw,
                role="direct_method",
                topic=None,
                expected_openalex_id=None,
                strict_lineage=True,
            )
            targets.append(record["openalex_id"])
        except MissionStateError:
            targets.append(None)
    return {
        **_empty_payload(),
        "frontier_view_status": "observed",
        "frontier_target_ids": targets,
        "frontier_reported_total": meta["count"],
        "frontier_continuation_visible": continuation,
    }


__all__ = [
    "DESCRIPTOR_SCHEMA",
    "FROZEN_SELECT",
    "FROZEN_SELECT_FIELDS",
    "LIST_CAP",
    "build_openalex_direct_descriptor",
    "build_openalex_forward_descriptor",
    "build_openalex_topic_descriptor",
    "parse_openalex_direct_response",
    "parse_openalex_forward_response",
    "parse_openalex_topic_response",
    "validate_openalex_descriptor",
]
