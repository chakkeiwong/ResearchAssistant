"""Canonical, topic-generic scope and discovery-route contracts."""

from __future__ import annotations

import re
from itertools import combinations
from typing import Any

from research_assistant.survey.discovery_quality import informative_tokens
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, normalize_text, sha256_bytes


TOPIC_CONTRACT_SCHEMA = "ra-survey-topic-contract-v1"
DISCOVERY_ROUTE_PLAN_SCHEMA = "ra-survey-discovery-route-plan-v1"
MAX_FACETS = 8
MAX_ALIASES = 16
MAX_EXCLUSIONS = 16
MAX_ROUTES = 12
_SPLIT = re.compile(r"\s+(?:and|for|in|with|using|via|versus|vs)\s+|\s*[:;/]\s*", re.IGNORECASE)


def _fail(message: str) -> None:
    raise MissionStateError("invalid_topic_contract", message)


def _text(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"{field} must be nonempty text")
    return " ".join(value.split())


def _text_list(value: Any, field: str, *, cap: int, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        _fail(f"{field} must be a list")
    rows = [_text(item, f"{field}[]") for item in value]
    normalized = sorted({str(item).casefold() for item in rows})
    if len(normalized) != len(rows):
        _fail(f"{field} must contain unique normalized values")
    if not allow_empty and not normalized:
        _fail(f"{field} must not be empty")
    if len(normalized) > cap:
        _fail(f"{field} exceeds its cardinality cap")
    return normalized


def _derived_facets(topic: str) -> list[str]:
    parts = [" ".join(part.split()).casefold() for part in _SPLIT.split(topic) if part.strip()]
    useful = [part for part in parts if informative_tokens(part)]
    if len(useful) <= 1:
        useful = [topic.casefold()]
    return sorted(dict.fromkeys(useful))[:MAX_FACETS]


def build_topic_contract(
    topic: str,
    *,
    required_facets: list[str] | None = None,
    optional_facets: list[str] | None = None,
    aliases: list[str] | None = None,
    exclusions: list[str] | None = None,
    scope_note: str | None = None,
) -> dict[str, Any]:
    display = normalize_text(topic, field="topic")["display"]
    required = _derived_facets(display) if required_facets is None else required_facets
    value = {
        "schema_version": TOPIC_CONTRACT_SCHEMA,
        "topic": display,
        "required_facets": required,
        "optional_facets": optional_facets or [],
        "aliases": aliases or [],
        "exclusions": exclusions or [],
        "scope_note": scope_note,
        "provenance": {
            "required_facets": "generic_clause_decomposition" if required_facets is None else "explicit_input",
            "optional_facets": "explicit_input" if optional_facets else "not_supplied",
            "aliases": "explicit_input" if aliases else "not_supplied",
            "exclusions": "explicit_input" if exclusions else "not_supplied",
        },
        "what_is_not_concluded": [
            "candidate centrality",
            "literature completeness",
            "scientific correctness",
            "topic recall",
        ],
    }
    return validate_topic_contract(value)


def validate_topic_contract(value: Any) -> dict[str, Any]:
    expected = {
        "schema_version", "topic", "required_facets", "optional_facets",
        "aliases", "exclusions", "scope_note", "provenance",
        "what_is_not_concluded",
    }
    if not isinstance(value, dict) or set(value) != expected:
        _fail("topic contract fields are not exact")
    if value["schema_version"] != TOPIC_CONTRACT_SCHEMA:
        _fail("topic contract schema is unsupported")
    topic = _text(value["topic"], "topic")
    required = _text_list(value["required_facets"], "required_facets", cap=MAX_FACETS, allow_empty=False)
    optional = _text_list(value["optional_facets"], "optional_facets", cap=MAX_FACETS)
    aliases = _text_list(value["aliases"], "aliases", cap=MAX_ALIASES)
    exclusions = _text_list(value["exclusions"], "exclusions", cap=MAX_EXCLUSIONS)
    if set(required) & set(exclusions) or set(optional) & set(exclusions) or set(aliases) & set(exclusions):
        _fail("included and excluded topic terms must not overlap")
    provenance = value["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "required_facets", "optional_facets", "aliases", "exclusions"
    }:
        _fail("topic contract provenance fields are not exact")
    normalized_provenance = {
        field: _text(provenance[field], f"provenance.{field}")
        for field in sorted(provenance)
    }
    nonclaims = _text_list(value["what_is_not_concluded"], "what_is_not_concluded", cap=16, allow_empty=False)
    return {
        "schema_version": TOPIC_CONTRACT_SCHEMA,
        "topic": topic,
        "required_facets": required,
        "optional_facets": optional,
        "aliases": aliases,
        "exclusions": exclusions,
        "scope_note": _text(value["scope_note"], "scope_note", nullable=True),
        "provenance": normalized_provenance,
        "what_is_not_concluded": nonclaims,
    }


def topic_contract_sha256(contract: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(validate_topic_contract(contract)))


def plan_discovery_routes(contract: dict[str, Any]) -> dict[str, Any]:
    contract = validate_topic_contract(contract)
    topic = contract["topic"]
    rows = [
        ("exact_high_citation", "foundational_or_high_citation", f"title.search:{topic}", "cited_by_count:desc"),
        ("exact_recent", "recent_follow_up", f"title.search:{topic}", "publication_date:desc"),
        ("survey_route", "survey_or_tutorial", f"default.search:{topic} survey", "cited_by_count:desc"),
        ("foundational_route", "foundational_or_high_citation", f"default.search:{topic} foundations", "cited_by_count:desc"),
        ("direct_method_route", "direct_method", f"default.search:{topic} method", "cited_by_count:desc"),
    ]
    facets = contract["required_facets"]
    pair_index = 0
    for left, right in combinations(facets, 2):
        if len(rows) >= MAX_ROUTES:
            break
        pair_index += 1
        rows.append((
            f"required_facet_pair_{pair_index}",
            "required_facet_pair",
            f"title.search:{left} {right}",
            "relevance_score:desc",
        ))
    for index, facet in enumerate(facets, start=1):
        if len(rows) >= MAX_ROUTES:
            break
        rows.append((
            f"required_facet_{index}",
            "required_facet",
            f"default.search:{facet}",
            "cited_by_count:desc",
        ))
    for index, alias in enumerate(contract["aliases"], start=1):
        if len(rows) >= MAX_ROUTES:
            break
        rows.append((f"alias_{index}", "alias_expansion", f"default.search:{alias}", "cited_by_count:desc"))
    routes = [
        {"kind": kind, "purpose": purpose, "priority": index, "filter": query_filter, "sort": sort}
        for index, (kind, purpose, query_filter, sort) in enumerate(rows, start=1)
    ]
    return {
        "schema_version": DISCOVERY_ROUTE_PLAN_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(contract),
        "routes": routes,
        "route_count": len(routes),
        "exclusions": contract["exclusions"],
        "what_is_not_concluded": ["candidate centrality", "literature completeness", "topic recall"],
    }


__all__ = [
    "DISCOVERY_ROUTE_PLAN_SCHEMA", "MAX_ROUTES", "TOPIC_CONTRACT_SCHEMA",
    "build_topic_contract", "plan_discovery_routes", "topic_contract_sha256",
    "validate_topic_contract",
]
