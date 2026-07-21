from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    normalize_seeds,
    normalize_text,
)


IDENTITY_RESOLUTION_SCHEMA_VERSION = "ra-survey-identity-resolution-v1"
RELEVANCE_RANKING_SCHEMA_VERSION = "ra-survey-relevance-ranking-v1"
PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION = "ra-survey-public-metadata-candidate-ledger-v2"

ALLOWED_PROVIDERS = {"arxiv", "openalex"}
ALLOWED_ROLES = {
    "seed",
    "direct_method",
    "adjacent_method",
    "major_citing_work",
    "backward_lineage_candidate",
}
DIRECT_ROLES = {"direct_method"}
NAVIGATION_ROLES = {"adjacent_method", "major_citing_work", "backward_lineage_candidate"}
STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "method",
    "methods",
    "paper",
    "study",
    "the",
    "this",
    "using",
    "via",
    "with",
}
ARXIV_ID_RE = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v(\d+))?$", re.IGNORECASE)
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
OPENALEX_RE = re.compile(r"^W\d+$", re.IGNORECASE)

TOP_LEVEL_KEYS = {
    "record_key",
    "title",
    "authors",
    "year",
    "doi",
    "arxiv_id",
    "openalex_id",
    "landing_page_url",
    "citation_count",
    "providers",
    "roles",
    "provider_records",
    "referenced_works",
    "query_provenance",
}
ARXIV_PROVIDER_KEYS = {
    "provider",
    "query_kind",
    "source_id",
    "primary_category",
    "published",
}
OPENALEX_PROVIDER_KEYS = {
    "provider",
    "query_kind",
    "source_id",
    "citation_count",
    "publication_date",
    "work_type",
}
QUERY_PROVENANCE_KEYS = {"provider", "query_kind", "normalized_seed_key", "topic_query"}


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise MissionStateError(code, message)


def _exact_dict(value: Any, keys: set[str], *, label: str) -> dict[str, Any]:
    _require(isinstance(value, dict) and set(value) == keys, "invalid_discovery_metadata", f"{label} keys are not exact")
    return value


def _clean_string(value: Any, *, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    _require(isinstance(value, str) and bool(value.strip()) and "\x00" not in value, "invalid_discovery_metadata", f"{label} is invalid")
    return " ".join(value.split())


def _clean_strings(value: Any, *, label: str, allow_empty: bool = True) -> list[str]:
    _require(isinstance(value, list), "invalid_discovery_metadata", f"{label} must be a list")
    cleaned = [_clean_string(row, label=f"{label}[]") for row in value]
    _require(allow_empty or bool(cleaned), "invalid_discovery_metadata", f"{label} must not be empty")
    _require(len(cleaned) == len(set(cleaned)), "invalid_discovery_metadata", f"{label} contains duplicates")
    return list(cleaned)


def normalized_title(value: str) -> str:
    display = unicodedata.normalize("NFKC", value).casefold()
    normalized = " ".join(re.findall(r"[a-z0-9]+", display))
    _require(bool(normalized), "invalid_discovery_metadata", "title is blank after normalization")
    return normalized


def informative_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                token
                for token in re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", value).casefold())
                if len(token) >= 3 and token not in STOPWORDS
            }
        )
    )


def _surname(authors: list[str]) -> str | None:
    if not authors:
        return None
    parts = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", authors[0]).casefold())
    return parts[-1] if parts else None


def normalize_arxiv_id(value: Any) -> str | None:
    if value is None:
        return None
    _require(isinstance(value, str) and "\x00" not in value, "invalid_discovery_metadata", "arXiv identifier is invalid")
    text = value.strip()
    lowered = text.casefold()
    if lowered.startswith("arxiv:"):
        text = text.split(":", 1)[1].strip()
    elif "arxiv.org/abs/" in lowered or "arxiv.org/pdf/" in lowered:
        text = text.rstrip("/").rsplit("/", 1)[-1].removesuffix(".pdf")
    _require(bool(ARXIV_ID_RE.fullmatch(text)), "invalid_discovery_metadata", "arXiv identifier is invalid")
    return text.casefold()


def arxiv_family(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"v\d+$", "", value.casefold())


def arxiv_version(value: str | None) -> int:
    if value is None:
        return 0
    match = re.search(r"v(\d+)$", value.casefold())
    return int(match.group(1)) if match else 0


def normalize_doi(value: Any) -> str | None:
    if value is None:
        return None
    _require(isinstance(value, str) and "\x00" not in value, "invalid_discovery_metadata", "DOI is invalid")
    text = value.strip().casefold()
    for prefix in ("doi:", "https://doi.org/", "http://doi.org/"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    _require(bool(DOI_RE.fullmatch(text)), "invalid_discovery_metadata", "DOI is invalid")
    return text


def normalize_openalex_id(value: Any) -> str | None:
    if value is None:
        return None
    _require(isinstance(value, str) and "\x00" not in value, "invalid_discovery_metadata", "OpenAlex identifier is invalid")
    text = value.strip().rstrip("/").rsplit("/", 1)[-1].upper()
    if text.casefold().startswith("openalex:"):
        text = text.split(":", 1)[1].upper()
    _require(bool(OPENALEX_RE.fullmatch(text)), "invalid_discovery_metadata", "OpenAlex identifier is invalid")
    return text


def parse_seed(value: str) -> dict[str, str]:
    normalized = normalize_text(value, field="seed")
    raw = normalized["display"]
    lowered = raw.casefold()
    try:
        if lowered.startswith("arxiv:") or "arxiv.org/abs/" in lowered or "arxiv.org/pdf/" in lowered or ARXIV_ID_RE.fullmatch(raw):
            parsed = normalize_arxiv_id(raw)
            assert parsed is not None
            return {**normalized, "kind": "arxiv_id", "value": f"arxiv:{parsed}"}
        if lowered.startswith("doi:") or "doi.org/" in lowered or DOI_RE.fullmatch(raw):
            parsed = normalize_doi(raw)
            assert parsed is not None
            return {**normalized, "kind": "doi", "value": f"doi:{parsed}"}
        if lowered.startswith("openalex:") or "openalex.org/" in lowered or OPENALEX_RE.fullmatch(raw):
            parsed = normalize_openalex_id(raw)
            assert parsed is not None
            return {**normalized, "kind": "openalex_id", "value": f"openalex:{parsed.casefold()}"}
    except MissionStateError:
        return {**normalized, "kind": "invalid", "value": raw}
    return {**normalized, "kind": "title", "value": normalized_title(raw)}


def normalize_record(value: Any) -> dict[str, Any]:
    row = _exact_dict(value, TOP_LEVEL_KEYS, label="metadata record")
    title = _clean_string(row["title"], label="title")
    assert title is not None
    title_key = normalized_title(title)
    authors = _clean_strings(row["authors"], label="authors")
    year = row["year"]
    _require(year is None or (type(year) is int and 1000 <= year <= 3000), "invalid_discovery_metadata", "year is invalid")
    citation = row["citation_count"]
    _require(citation is None or (type(citation) is int and citation >= 0), "invalid_discovery_metadata", "citation count is invalid")
    doi = normalize_doi(row["doi"])
    arxiv_id = normalize_arxiv_id(row["arxiv_id"])
    openalex_id = normalize_openalex_id(row["openalex_id"])
    landing = _clean_string(row["landing_page_url"], label="landing URL", nullable=True)
    record_key = _clean_string(row["record_key"], label="record key")
    assert record_key is not None
    providers = [item.casefold() for item in _clean_strings(row["providers"], label="providers", allow_empty=False)]
    roles = [item.casefold() for item in _clean_strings(row["roles"], label="roles")]
    _require(set(providers) <= ALLOWED_PROVIDERS, "invalid_discovery_metadata", "provider is not closed")
    _require(set(roles) <= ALLOWED_ROLES, "invalid_discovery_metadata", "role is not closed")

    provider_rows = row["provider_records"]
    _require(isinstance(provider_rows, list) and bool(provider_rows), "invalid_discovery_metadata", "provider records are invalid")
    normalized_provider_rows: list[dict[str, Any]] = []
    source_identities: list[tuple[str, str, str]] = []
    for index, provider_value in enumerate(provider_rows):
        _require(isinstance(provider_value, dict), "invalid_discovery_metadata", "provider record is invalid")
        provider = provider_value.get("provider")
        if provider == "arxiv":
            provider_row = _exact_dict(provider_value, ARXIV_PROVIDER_KEYS, label=f"provider_records[{index}]")
            source_id = normalize_arxiv_id(provider_row["source_id"])
            assert source_id is not None
            normalized_row = {
                "provider": "arxiv",
                "query_kind": _clean_string(provider_row["query_kind"], label="arxiv query kind"),
                "source_id": source_id,
                "primary_category": _clean_string(provider_row["primary_category"], label="primary category", nullable=True),
                "published": _clean_string(provider_row["published"], label="published", nullable=True),
            }
        elif provider == "openalex":
            provider_row = _exact_dict(provider_value, OPENALEX_PROVIDER_KEYS, label=f"provider_records[{index}]")
            source_id = normalize_openalex_id(provider_row["source_id"])
            assert source_id is not None
            provider_citation = provider_row["citation_count"]
            _require(provider_citation is None or (type(provider_citation) is int and provider_citation >= 0), "invalid_discovery_metadata", "provider citation is invalid")
            normalized_row = {
                "provider": "openalex",
                "query_kind": _clean_string(provider_row["query_kind"], label="OpenAlex query kind"),
                "source_id": source_id,
                "citation_count": provider_citation,
                "publication_date": _clean_string(provider_row["publication_date"], label="publication date", nullable=True),
                "work_type": _clean_string(provider_row["work_type"], label="work type", nullable=True),
            }
        else:
            raise MissionStateError("invalid_discovery_metadata", "provider record provider is not closed")
        normalized_provider_rows.append(normalized_row)
        source_identities.append((normalized_row["provider"], normalized_row["source_id"].casefold(), record_key.casefold()))
    _require(
        set(providers) == {provider_row["provider"] for provider_row in normalized_provider_rows},
        "invalid_discovery_metadata",
        "providers differ from provider-record coverage",
    )

    referenced = [normalize_openalex_id(item) for item in row["referenced_works"]]
    _require(all(referenced), "invalid_discovery_metadata", "referenced works are invalid")
    referenced_values = sorted(set(item for item in referenced if item is not None))

    provenance_rows = row["query_provenance"]
    _require(isinstance(provenance_rows, list) and bool(provenance_rows), "invalid_discovery_metadata", "query provenance is invalid")
    normalized_provenance: list[dict[str, Any]] = []
    for index, provenance_value in enumerate(provenance_rows):
        provenance = _exact_dict(provenance_value, QUERY_PROVENANCE_KEYS, label=f"query_provenance[{index}]")
        provider = _clean_string(provenance["provider"], label="query provider")
        query_kind = _clean_string(provenance["query_kind"], label="query kind")
        seed_key = provenance["normalized_seed_key"]
        _require(seed_key is None or (isinstance(seed_key, str) and bool(seed_key) and "\x00" not in seed_key), "invalid_discovery_metadata", "query seed key is invalid")
        _require(type(provenance["topic_query"]) is bool, "invalid_discovery_metadata", "topic query flag is invalid")
        _require(provider in ALLOWED_PROVIDERS, "invalid_discovery_metadata", "query provider is not closed")
        normalized_provenance.append({
            "provider": provider,
            "query_kind": query_kind,
            "normalized_seed_key": seed_key,
            "topic_query": provenance["topic_query"],
        })
    _require(
        {
            (row["provider"], row["query_kind"])
            for row in normalized_provider_rows
        }
        == {
            (row["provider"], row["query_kind"])
            for row in normalized_provenance
        },
        "invalid_discovery_metadata",
        "provider-record routes differ from query provenance",
    )

    result = {
        "record_key": record_key,
        "title": title,
        "title_key": title_key,
        "authors": authors,
        "first_author_surname": _surname(authors),
        "year": year,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "arxiv_family": arxiv_family(arxiv_id),
        "openalex_id": openalex_id,
        "landing_page_url": landing,
        "citation_count": citation,
        "providers": sorted(set(providers)),
        "roles": sorted(set(roles)),
        "provider_records": sorted(normalized_provider_rows, key=lambda item: canonical_json_bytes(item)),
        "referenced_works": referenced_values,
        "query_provenance": sorted(normalized_provenance, key=lambda item: canonical_json_bytes(item)),
        "source_identities": sorted(set(source_identities)),
    }
    return result


def _non_provenance(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row
        for key, row in value.items()
        if key
        not in {
            "providers",
            "roles",
            "provider_records",
            "query_provenance",
            "source_identities",
        }
    }


def _replay_record(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_key": value["record_key"],
        "title": value["title"],
        "authors": value["authors"],
        "year": value["year"],
        "doi": value["doi"],
        "arxiv_id": value["arxiv_id"],
        "openalex_id": value["openalex_id"],
        "landing_page_url": value["landing_page_url"],
        "citation_count": value["citation_count"],
        "providers": value["providers"],
        "roles": value["roles"],
        "provider_records": value["provider_records"],
        "referenced_works": value["referenced_works"],
        "query_provenance": value["query_provenance"],
    }


def _strong_aliases(row: dict[str, Any]) -> tuple[str, ...]:
    aliases = []
    if row["doi"]:
        aliases.append(f"doi:{row['doi']}")
    if row["arxiv_family"]:
        aliases.append(f"arxiv:{row['arxiv_family']}")
    if row["openalex_id"]:
        aliases.append(f"openalex:{row['openalex_id'].casefold()}")
    return tuple(sorted(aliases))


def _digest(prefix: str, payload: dict[str, Any]) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _title_jaccard(left: str, right: str) -> float:
    left_tokens = set(informative_tokens(left))
    right_tokens = set(informative_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _deduplicate_rows(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(records, key=lambda item: canonical_json_bytes(item))
    parent = list(range(len(ordered)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    first_by_identity: dict[tuple[str, str, str], int] = {}
    duplicate_rows: list[dict[str, Any]] = []
    for index, row in enumerate(ordered):
        duplicate_identities: list[list[str]] = []
        for identity in row["source_identities"]:
            previous = first_by_identity.get(identity)
            if previous is None:
                first_by_identity[identity] = index
                continue
            union(index, previous)
            duplicate_identities.append(list(identity))
        if duplicate_identities:
            duplicate_rows.append({
                "source_identities": sorted(duplicate_identities),
                "record_key": row["record_key"],
                "reason": "exact_source_identity_and_metadata",
            })

    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(ordered):
        groups[find(index)].append(row)

    merged_rows: list[dict[str, Any]] = []
    for root in sorted(groups):
        group = groups[root]
        intrinsic = _non_provenance(group[0])
        if any(_non_provenance(row) != intrinsic for row in group[1:]):
            raise MissionStateError("source_identity_conflict", "same source identity has differing metadata")
        merged_rows.append({
            **group[0],
            "providers": sorted({value for row in group for value in row["providers"]}),
            "roles": sorted({value for row in group for value in row["roles"]}),
            "provider_records": sorted(
                {
                    canonical_json_bytes(value): value
                    for row in group
                    for value in row["provider_records"]
                }.values(),
                key=canonical_json_bytes,
            ),
            "query_provenance": sorted(
                {
                    canonical_json_bytes(value): value
                    for row in group
                    for value in row["query_provenance"]
                }.values(),
                key=canonical_json_bytes,
            ),
            "source_identities": sorted(
                {tuple(value) for row in group for value in row["source_identities"]}
            ),
        })
    return merged_rows, sorted(duplicate_rows, key=lambda item: canonical_json_bytes(item))


def _components(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    aliases_by_index = [set(_strong_aliases(row)) for row in records]
    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    seen: dict[str, int] = {}
    for index, aliases in enumerate(aliases_by_index):
        for alias in sorted(aliases):
            if alias in seen:
                union(index, seen[alias])
            else:
                seen[alias] = index
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(records):
        grouped[find(index)].append(row)
    return [sorted(group, key=lambda item: canonical_json_bytes(item)) for _, group in sorted(grouped.items())]


def _component_reasons(component: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    dois = sorted({row["doi"] for row in component if row["doi"]})
    families = sorted({row["arxiv_family"] for row in component if row["arxiv_family"]})
    if len(dois) > 1:
        reasons.append({"code": "multiple_doi", "values": dois})
    if len(families) > 1:
        reasons.append({"code": "multiple_arxiv_family", "values": families})
    for left_index, left in enumerate(component):
        for right_index in range(left_index + 1, len(component)):
            right = component[right_index]
            if left["title_key"] != right["title_key"] and _title_jaccard(left["title"], right["title"]) < 0.80:
                reasons.append({"code": "title_conflict", "pair": [left["record_key"], right["record_key"]]})
            if left["first_author_surname"] and right["first_author_surname"] and left["first_author_surname"] != right["first_author_surname"]:
                reasons.append({"code": "author_conflict", "pair": [left["record_key"], right["record_key"]]})
    family_anchored = len(families) == 1 and len(dois) <= 1
    if not family_anchored:
        for left_index, left in enumerate(component):
            for right_index in range(left_index + 1, len(component)):
                right = component[right_index]
                if left["year"] is not None and right["year"] is not None and abs(left["year"] - right["year"]) > 1:
                    reasons.append({"code": "year_conflict", "pair": [left["record_key"], right["record_key"]]})
    return sorted(reasons, key=lambda item: canonical_json_bytes(item))


def _aggregate_component(component: list[dict[str, Any]]) -> dict[str, Any]:
    aliases = sorted({alias for row in component for alias in _strong_aliases(row)})
    reasons = _component_reasons(component)
    if reasons:
        payload = {"identity_kind": "conflict", "rows": component, "reasons": reasons}
        return {
            "component_status": "identity_conflict",
            "conflict_id": _digest("dq_conflict_", payload),
            "paper_id": None,
            "canonical_identifier": None,
            "aliases": aliases,
            "rows": component,
            "reasons": reasons,
        }
    source_identities = sorted({tuple(identity) for row in component for identity in row["source_identities"]})
    if aliases:
        identity_payload = {"identity_kind": "strong_aliases", "aliases": aliases}
    else:
        first = component[0]
        identity_payload = {
            "identity_kind": "source_identity_fallback",
            "title": first["title_key"],
            "first_author_surname": first["first_author_surname"],
            "year": first["year"],
            "source_identities": [list(value) for value in source_identities],
        }
    paper_id = _digest("p_dq_", identity_payload)
    dois = sorted({row["doi"] for row in component if row["doi"]})
    arxiv_ids = sorted({row["arxiv_id"] for row in component if row["arxiv_id"]}, key=lambda value: (arxiv_version(value), value))
    openalex_ids = sorted({row["openalex_id"] for row in component if row["openalex_id"]})
    canonical_identifier = (
        f"doi:{dois[0]}"
        if dois
        else f"arxiv:{arxiv_ids[-1]}"
        if arxiv_ids
        else f"openalex:{openalex_ids[0].casefold()}"
        if openalex_ids
        else f"title:{component[0]['title_key']}"
    )
    return {
        "component_status": "eligible",
        "conflict_id": None,
        "paper_id": paper_id,
        "canonical_identifier": canonical_identifier,
        "aliases": aliases,
        "title": component[0]["title"],
        "title_key": component[0]["title_key"],
        "authors": sorted({author for row in component for author in row["authors"]}),
        "first_author_surname": component[0]["first_author_surname"],
        "years": sorted({row["year"] for row in component if row["year"] is not None}),
        "doi": dois[0] if dois else None,
        "arxiv_ids": arxiv_ids,
        "openalex_ids": openalex_ids,
        "citation_count": max((row["citation_count"] for row in component if row["citation_count"] is not None), default=None),
        "providers": sorted({provider for row in component for provider in row["providers"]}),
        "roles": sorted({role for row in component for role in row["roles"]}),
        "normalized_seed_keys": sorted(
            {
                provenance["normalized_seed_key"]
                for row in component
                for provenance in row["query_provenance"]
                if provenance["normalized_seed_key"] is not None
            }
        ),
        "referenced_works": sorted({value for row in component for value in row["referenced_works"]}),
        "source_identities": [list(value) for value in source_identities],
        "rows": component,
        "reasons": [],
    }


def _possible_duplicates(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [row for row in components if row["component_status"] == "eligible"]
    duplicates = []
    for left_index, left in enumerate(eligible):
        for right_index in range(left_index + 1, len(eligible)):
            right = eligible[right_index]
            if set(left["aliases"]) & set(right["aliases"]):
                continue
            left_years = left["years"]
            right_years = right["years"]
            if (
                left["title_key"] == right["title_key"]
                and left["first_author_surname"] is not None
                and left["first_author_surname"] == right["first_author_surname"]
                and left_years
                and right_years
                and min(abs(a - b) for a in left_years for b in right_years) <= 1
            ):
                duplicates.append({
                    "paper_ids": sorted([left["paper_id"], right["paper_id"]]),
                    "reason": "exact_title_author_compatible_year_without_strong_alias",
                })
    return sorted(duplicates, key=lambda item: canonical_json_bytes(item))


def _seed_choices(seed: dict[str, str], components: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in components if row["component_status"] == "eligible"]
    conflicts = [row for row in components if row["component_status"] == "identity_conflict"]
    if seed["kind"] == "invalid":
        return {"choices": [], "method": "none", "disposition": "invalid_seed", "selected_paper_id": None, "selected_identifier": None}
    if seed["kind"] != "title":
        identifier_aliases = {seed["value"]}
        if seed["kind"] == "arxiv_id":
            identifier_aliases.add(f"arxiv:{arxiv_family(seed['value'].split(':', 1)[1])}")
        exact = [row for row in eligible if identifier_aliases & set(row["aliases"])]
        conflict_matches = [row for row in conflicts if identifier_aliases & set(row["aliases"])]
        choices = sorted([row["paper_id"] for row in exact])
        if conflict_matches or len(exact) > 1:
            disposition = "identity_conflict"
            selected = None
        elif len(exact) == 1:
            disposition = "resolved_exact_identifier"
            selected = exact[0]
        else:
            disposition = "unresolved"
            selected = None
        return {
            "choices": choices,
            "method": "exact_identifier" if selected else "none",
            "disposition": disposition,
            "selected_paper_id": selected["paper_id"] if selected else None,
            "selected_identifier": seed["value"] if selected else None,
        }
    scoped = [row for row in eligible if seed["key"] in row["normalized_seed_keys"]]
    scored = sorted(
        [
            {
                "paper_id": row["paper_id"],
                "identifier": row["canonical_identifier"],
                "title_key": row["title_key"],
                "similarity": round(SequenceMatcher(None, seed["value"], row["title_key"]).ratio(), 12),
            }
            for row in scoped
        ],
        key=lambda item: (-item["similarity"], item["paper_id"]),
    )
    exact = [row for row in scored if row["title_key"] == seed["value"]]
    selected = None
    disposition = "unresolved"
    method = "none"
    if len(exact) == 1:
        selected = exact[0]
        disposition = "resolved_unique_title"
        method = "exact_title"
    elif len(exact) > 1:
        disposition = "ambiguous_title"
    elif scored:
        runner_up = scored[1]["similarity"] if len(scored) > 1 else 0.0
        top = scored[0]
        if (
            top["similarity"] >= 0.96
            and len(informative_tokens(seed["display"])) >= 3
            and top["similarity"] - runner_up >= 0.08
        ):
            selected = top
            disposition = "resolved_unique_title"
            method = "high_margin_title"
        elif top["similarity"] >= 0.96:
            disposition = "ambiguous_title"
    return {
        "choices": scored,
        "method": method,
        "disposition": disposition,
        "selected_paper_id": selected["paper_id"] if selected else None,
        "selected_identifier": selected["identifier"] if selected else None,
    }


def evaluate_discovery_quality(
    *,
    topic: str,
    seeds: list[str],
    records: list[dict[str, Any]],
    max_records: int,
) -> dict[str, Any]:
    normalized_topic = normalize_text(topic, field="topic")
    normalized_seeds = normalize_seeds(seeds)
    _require(type(max_records) is int and max_records > 0, "invalid_discovery_budget", "max_records is invalid")
    _require(len(normalized_seeds) <= max_records, "seed_count_exceeds_metadata_cap", "seed count exceeds metadata cap")
    normalized_records = [normalize_record(row) for row in records]
    unique_records, exact_duplicates = _deduplicate_rows(normalized_records)
    components = [_aggregate_component(group) for group in _components(unique_records)]
    components = sorted(components, key=lambda item: item.get("paper_id") or item["conflict_id"])
    paper_ids = [row["paper_id"] for row in components if row["paper_id"] is not None]
    _require(len(paper_ids) == len(set(paper_ids)), "identity_id_collision", "eligible paper IDs are not unique")

    seed_rows = []
    for seed_value in normalized_seeds:
        parsed = parse_seed(seed_value["display"])
        resolution = _seed_choices(parsed, components)
        seed_rows.append({
            "normalized_seed_key": seed_value["key"],
            "display": seed_value["display"],
            "kind": parsed["kind"],
            "normalized_value": parsed["value"],
            **resolution,
        })
    exact_seed_identifiers: dict[str, list[str]] = defaultdict(list)
    for row in seed_rows:
        if row["disposition"] == "resolved_exact_identifier" and row["selected_paper_id"]:
            exact_seed_identifiers[row["selected_paper_id"]].append(row["selected_identifier"])
    for component in components:
        paper_id = component.get("paper_id")
        if paper_id in exact_seed_identifiers:
            component["canonical_identifier"] = exact_seed_identifiers[paper_id][0]
    component_by_id = {row["paper_id"]: row for row in components if row["paper_id"]}
    for row in seed_rows:
        if row["disposition"] == "resolved_unique_title" and row["selected_paper_id"]:
            row["selected_identifier"] = component_by_id[row["selected_paper_id"]]["canonical_identifier"]
    resolved_dispositions = {"resolved_exact_identifier", "resolved_unique_title"}
    seed_gate = (
        len(seed_rows) == len(normalized_seeds)
        and {row["normalized_seed_key"] for row in seed_rows} == {row["key"] for row in normalized_seeds}
        and all(row["disposition"] in resolved_dispositions and row["selected_paper_id"] for row in seed_rows)
    )
    selected_seed_ids = {row["selected_paper_id"] for row in seed_rows if row["selected_paper_id"]}
    query_tokens = set(informative_tokens(normalized_topic["display"]))
    for component in components:
        if component.get("paper_id") in selected_seed_ids:
            query_tokens.update(informative_tokens(component["title"]))

    relevance_rows: list[dict[str, Any]] = []
    for component in components:
        if component["component_status"] == "identity_conflict":
            relevance_rows.append({
                "paper_id": None,
                "conflict_id": component["conflict_id"],
                "disposition": "identity_conflict_excluded",
                "included": False,
                "matched_tokens": [],
                "matched_count": 0,
                "query_token_count": len(query_tokens),
                "citation_count": None,
                "pre_cap_rank": None,
                "final_rank": None,
                "reason": "identity_conflict",
            })
            continue
        paper_id = component["paper_id"]
        matched = sorted(set(informative_tokens(component["title"])) & query_tokens)
        is_seed = paper_id in selected_seed_ids
        direct = bool(set(component["roles"]) & DIRECT_ROLES)
        if is_seed:
            disposition = "seed_authority"
            included = seed_gate
        elif direct and matched:
            disposition = "direct_topic_match"
            included = seed_gate
        elif len(matched) >= 2:
            disposition = "adjacent_match"
            included = seed_gate
        elif len(matched) == 1:
            disposition = "weak_match_review_required"
            included = False
        else:
            disposition = "irrelevant_excluded"
            included = False
        relevance_rows.append({
            "paper_id": paper_id,
            "conflict_id": None,
            "disposition": disposition,
            "included": included,
            "matched_tokens": matched,
            "matched_count": len(matched),
            "query_token_count": len(query_tokens),
            "citation_count": component["citation_count"],
            "pre_cap_rank": None,
            "final_rank": None,
            "reason": disposition,
        })

    class_order = {"seed_authority": 0, "direct_topic_match": 1, "adjacent_match": 2}
    includable = [row for row in relevance_rows if row["included"]]

    def rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
        component = component_by_id[row["paper_id"]]
        citation = row["citation_count"]
        citation_missing = citation is None
        query_count = row["query_token_count"] or 1
        return (
            class_order[row["disposition"]],
            -row["matched_count"],
            -row["matched_count"],
            query_count,
            citation_missing,
            -(citation if citation is not None else 0),
            component["title_key"],
            component["canonical_identifier"],
        )

    ranked = sorted(includable, key=rank_key)
    for rank, row in enumerate(ranked, start=1):
        row["pre_cap_rank"] = rank
    kept_ids = {row["paper_id"] for row in ranked[:max_records]}
    for rank, row in enumerate(ranked[:max_records], start=1):
        row["final_rank"] = rank
    for row in ranked[max_records:]:
        row["included"] = False
        row["disposition"] = "excluded_by_cap_after_relevance"
        row["reason"] = "metadata_cap_after_relevance"
    selected = [component_by_id[row["paper_id"]] for row in ranked if row["paper_id"] in kept_ids]

    possible_duplicates = _possible_duplicates(components)
    included_rows = [
        {
            "paper_key": component["paper_id"],
            "identifier": component["canonical_identifier"],
            "title": component["title"],
            "authors": component["authors"],
            "year": component["years"][-1] if component["years"] else None,
            "roles": sorted(set(component["roles"]) | ({"seed"} if component["paper_id"] in selected_seed_ids else set())),
            "providers": component["providers"],
            "citation_count": component["citation_count"],
            "citation_count_policy": "coverage_signal_only",
            "reason": next(row["disposition"] for row in relevance_rows if row["paper_id"] == component["paper_id"]),
            "metadata_only": True,
        }
        for component in selected
    ]
    excluded_rows = [
        {
            "paper_key": row["paper_id"],
            "conflict_id": row["conflict_id"],
            "disposition": row["disposition"],
            "reason": row["reason"],
        }
        for row in relevance_rows
        if not row["included"]
    ]
    identity_ledger = {
        "schema_version": IDENTITY_RESOLUTION_SCHEMA_VERSION,
        "status": "resolved" if seed_gate else "blocked_seed_resolution",
        "topic": normalized_topic["display"],
        "normalized_seed_keys": [row["key"] for row in normalized_seeds],
        "input_records": sorted(
            [_replay_record(row) for row in normalized_records],
            key=canonical_json_bytes,
        ),
        "seed_resolutions": seed_rows,
        "components": components,
        "exact_duplicates": exact_duplicates,
        "possible_duplicates": possible_duplicates,
        "seed_gate_passed": seed_gate,
        "what_is_not_concluded": ["identity truth", "source safety", "literature completeness"],
    }
    relevance_ledger = {
        "schema_version": RELEVANCE_RANKING_SCHEMA_VERSION,
        "status": "ranked" if seed_gate else "blocked_seed_resolution",
        "topic": normalized_topic["display"],
        "query_tokens": sorted(query_tokens),
        "rows": relevance_rows,
        "included_paper_ids": [row["paper_key"] for row in included_rows],
        "policy": {
            "citation_count_role": "equal_relevance_stratum_tiebreak_only",
            "metadata_supports_technical_claims": False,
            "ranking_establishes_recall_or_completeness": False,
        },
        "what_is_not_concluded": ["substantive relevance truth", "recall", "literature completeness"],
    }
    return {
        "status": "eligible" if seed_gate else "blocked_seed_resolution",
        "identity_resolution": identity_ledger,
        "relevance_ranking": relevance_ledger,
        "included": included_rows,
        "excluded": excluded_rows,
        "duplicates": [*exact_duplicates, *possible_duplicates],
        "selected_records": selected,
        "record_key_to_paper_id": {
            row["record_key"]: component["paper_id"]
            for component in selected
            for row in component["rows"]
        },
    }


__all__ = [
    "IDENTITY_RESOLUTION_SCHEMA_VERSION",
    "PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION",
    "RELEVANCE_RANKING_SCHEMA_VERSION",
    "evaluate_discovery_quality",
    "informative_tokens",
    "normalize_record",
    "parse_seed",
]
