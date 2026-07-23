from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.bootstrap import BOOTSTRAP_OUTCOME_SCHEMA
from research_assistant.survey.discovery_quality import (
    informative_tokens,
    normalize_doi,
    normalize_openalex_id,
    normalized_title,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    normalize_text,
    sha256_bytes,
)
from research_assistant.survey.topic_seed_strategy import (
    GENERIC_STRATEGY_FILE,
    QueryPlanner,
    QueryStrategy,
    load_strategy,
)
from research_assistant.survey.topic_contract import build_topic_contract, plan_discovery_routes
from research_assistant.survey.venue_metrics import (
    load_registry,
    metric_by_paper,
    metric_by_venue,
    unavailable_registry,
)


RANKING_POLICY = "topic_seed_priority_v3_budgeted_strata"
TOPIC_RESULT_CAP = 25
SELECTED_SEED_CAP = 12
RELEVANCE_MINIMUM_MATCHED_TOKENS = 1
GENERIC_TOPIC_PROFILE = "generic_topic"
OPENALEX_SELECT = ",".join((
    "id",
    "display_name",
    "authorships",
    "publication_year",
    "doi",
    "cited_by_count",
    "ids",
    "primary_location",
    "best_oa_location",
    "open_access",
    "referenced_works",
    "is_retracted",
))


def _fail(code: str, message: str) -> None:
    raise MissionStateError(code, message)


@dataclass
class BudgetTracker:
    budget: dict[str, Any]
    request_count: int = 0
    provider_row_count: int = 0
    response_bytes: int = 0

    def before_request(self) -> None:
        if self.request_count >= self.budget["max_metadata_requests"]:
            _fail("topic_seed_request_budget_exceeded", "metadata request budget is exhausted")
        self.request_count += 1

    def consume(self, *, returned_count: int, response_bytes: int) -> dict[str, int]:
        if returned_count > self.budget["max_records_per_metadata_response"]:
            _fail("topic_seed_record_cap_exceeded", "metadata response record cap is exceeded")
        if response_bytes > self.budget["max_bytes_per_metadata_response"]:
            _fail("topic_seed_response_cap_exceeded", "metadata response byte cap is exceeded")
        if self.provider_row_count + returned_count > self.budget["max_total_metadata_records"]:
            _fail("topic_seed_total_record_budget_exceeded", "aggregate metadata record budget is exceeded")
        if self.response_bytes + response_bytes > self.budget["max_total_metadata_bytes"]:
            _fail("topic_seed_total_byte_budget_exceeded", "aggregate metadata byte budget is exceeded")
        self.provider_row_count += returned_count
        self.response_bytes += response_bytes
        return self.snapshot()

    def snapshot(self) -> dict[str, int]:
        return {
            "metadata_requests": self.request_count,
            "provider_rows": self.provider_row_count,
            "response_bytes": self.response_bytes,
        }


class CandidateIdentityResolver:
    def resolve(self, works: list[Any]) -> tuple[list[Any], list[dict[str, Any]], list[dict[str, Any]]]:
        merged: list[Any] = []
        by_key: dict[str, dict[str, Any]] = {}
        duplicates: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        for work in works:
            if not isinstance(work, dict):
                merged.append(work)
                continue
            key = self._key(work)
            existing = by_key.get(key)
            if existing is None:
                existing = dict(work)
                by_key[key] = existing
                merged.append(existing)
                continue
            if self._intrinsic(existing) != self._intrinsic(work):
                existing["_identity_conflict"] = True
                conflicts.append({
                    "identity_key": key,
                    "openalex_ids": sorted({str(existing.get("id")), str(work.get("id"))}),
                    "reason": "canonical_identity_metadata_conflict",
                })
                continue
            for field in ("_topic_query_layers", "_fully_observed_query_layers", "_topic_query_purposes"):
                values = set(existing.get(field, [])) | set(work.get(field, []))
                existing[field] = sorted(value for value in values if isinstance(value, str))
            observations = {
                value for value in (
                    existing.get("cited_by_count"),
                    work.get("cited_by_count"),
                    *(existing.get("_citation_count_observations", [])),
                )
                if type(value) is int and value >= 0
            }
            existing["_citation_count_observations"] = sorted(observations)
            existing["cited_by_count"] = max(observations) if observations else None
            duplicates.append({
                "identity_key": key,
                "retained_openalex_id": str(existing.get("id")),
                "duplicate_openalex_id": str(work.get("id")),
                "reason": "canonical_identity_duplicate",
            })
        possible = self._possible_duplicates([row for row in merged if isinstance(row, dict)])
        duplicates.extend(possible)
        return merged, sorted(duplicates, key=lambda row: (row["identity_key"], row.get("duplicate_openalex_id", ""))), sorted(
            conflicts, key=lambda row: (row["identity_key"], row["openalex_ids"])
        )

    @staticmethod
    def _key(work: dict[str, Any]) -> str:
        try:
            doi = normalize_doi(work.get("doi"))
        except MissionStateError:
            doi = None
        if doi:
            return f"doi:{doi}"
        ids = work.get("ids")
        if isinstance(ids, dict):
            arxiv = ids.get("arxiv")
            if isinstance(arxiv, str) and arxiv.strip():
                return f"arxiv:{arxiv.rstrip('/').rsplit('/', 1)[-1].removesuffix('.pdf').casefold()}"
        raw_id = work.get("id")
        return f"openalex:{str(raw_id).rstrip('/').rsplit('/', 1)[-1].casefold()}"

    @staticmethod
    def _intrinsic(work: dict[str, Any]) -> tuple[Any, ...]:
        title = work.get("display_name")
        return (
            normalized_title(title) if isinstance(title, str) and title.strip() else None,
            work.get("publication_year"),
        )

    @classmethod
    def _possible_duplicates(cls, works: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_fallback: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for work in works:
            title = work.get("display_name")
            authorships = work.get("authorships")
            year = work.get("publication_year")
            if not isinstance(title, str) or not title.strip() or not isinstance(authorships, list) or not authorships or type(year) is not int:
                continue
            author = authorships[0].get("author") if isinstance(authorships[0], dict) else None
            name = author.get("display_name") if isinstance(author, dict) else None
            if not isinstance(name, str) or not name.strip():
                continue
            key = (normalized_title(title), " ".join(name.casefold().split()), year)
            by_fallback.setdefault(key, []).append(work)
        rows = []
        for key, group in sorted(by_fallback.items()):
            if len(group) <= 1:
                continue
            rows.append({
                "identity_key": f"title:{key[0]}|author:{key[1]}|year:{key[2]}",
                "openalex_ids": sorted(str(row.get("id")) for row in group),
                "reason": "possible_title_author_year_duplicate_without_strong_alias",
            })
        return rows


def _strict_json(raw: bytes) -> Any:
    def object_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail("invalid_topic_seed_response", f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_hook,
            parse_constant=lambda value: _fail("invalid_topic_seed_response", f"non-finite JSON value: {value}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_topic_seed_response", "OpenAlex response is not valid UTF-8 JSON") from exc


def _venue_identity(work: dict[str, Any]) -> tuple[str | None, str | None]:
    location = work.get("primary_location")
    if not isinstance(location, dict):
        return None, None
    source = location.get("source")
    if not isinstance(source, dict):
        return None, None
    raw_id = source.get("id")
    display = source.get("display_name")
    venue_key = None
    if isinstance(raw_id, str) and raw_id.strip():
        venue_key = raw_id.rstrip("/").rsplit("/", 1)[-1].casefold()
    if not isinstance(display, str) or not display.strip():
        display = None
    return venue_key, None if display is None else " ".join(display.split())


def _canonical_identifier(work: dict[str, Any], openalex_id: str) -> str:
    doi = work.get("doi")
    if isinstance(doi, str) and doi.strip():
        text = doi.strip().casefold()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        if text.startswith("10."):
            return f"doi:{text}"
    ids = work.get("ids")
    if isinstance(ids, dict):
        arxiv = ids.get("arxiv")
        if isinstance(arxiv, str) and arxiv.strip():
            value = arxiv.rstrip("/").rsplit("/", 1)[-1].removesuffix(".pdf")
            return f"arxiv:{value.casefold()}"
    return f"openalex:{openalex_id.casefold()}"


def _identifier_evidence(work: dict[str, Any], openalex_id: str) -> list[str]:
    evidence = {
        _canonical_identifier(work, openalex_id),
        f"openalex:{openalex_id.casefold()}",
    }
    doi = work.get("doi")
    if isinstance(doi, str) and doi.strip():
        normalized = doi.strip().casefold()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        if normalized.startswith("10."):
            evidence.add(f"doi:{normalized}")
    ids = work.get("ids")
    if isinstance(ids, dict):
        arxiv = ids.get("arxiv")
        if isinstance(arxiv, str) and arxiv.strip():
            value = arxiv.rstrip("/").rsplit("/", 1)[-1].removesuffix(".pdf")
            evidence.add(f"arxiv:{value.casefold()}")
    return sorted(evidence)


def _candidate(
    work: Any,
    *,
    topic_tokens: set[str],
    topic_profile: str | None,
    required_topic_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any] | None:
    if not isinstance(work, dict):
        return None
    try:
        openalex_id = normalize_openalex_id(work.get("id"))
    except MissionStateError:
        return None
    title = work.get("display_name")
    if openalex_id is None or not isinstance(title, str) or not title.strip():
        return None
    title = " ".join(title.split())
    citations = work.get("cited_by_count")
    if citations is not None and (type(citations) is not int or citations < 0):
        return None
    year = work.get("publication_year")
    if year is not None and (type(year) is not int or not 1000 <= year <= 3000):
        return None
    authorships = work.get("authorships")
    if not isinstance(authorships, list):
        return None
    authors = []
    for authorship in authorships:
        author = authorship.get("author") if isinstance(authorship, dict) else None
        name = author.get("display_name") if isinstance(author, dict) else None
        if isinstance(name, str) and name.strip():
            authors.append(" ".join(name.split()))
    matched = sorted(set(informative_tokens(title)) & topic_tokens)
    title_tokens = set(informative_tokens(title))
    concept_groups: dict[str, list[str]] = {}
    for group, phrases in required_topic_groups.items():
        evidence: set[str] = set()
        for phrase in phrases:
            if phrase == "{topic}":
                evidence.update(title_tokens & topic_tokens)
            elif set(informative_tokens(phrase)) <= title_tokens:
                evidence.add(phrase)
        concept_groups[group] = sorted(evidence)
    venue_key, venue_display = _venue_identity(work)
    best_oa_location = work.get("best_oa_location")
    open_access_pdf_url = None
    if isinstance(best_oa_location, dict):
        candidate_url = best_oa_location.get("pdf_url")
        if isinstance(candidate_url, str) and candidate_url.startswith("https://"):
            open_access_pdf_url = candidate_url
    references = work.get("referenced_works")
    if not isinstance(references, list):
        references = []
    references = sorted({
        value.rstrip("/").rsplit("/", 1)[-1]
        for value in references
        if isinstance(value, str) and value.startswith("https://openalex.org/W")
    })
    is_retracted = work.get("is_retracted")
    if is_retracted is not None and type(is_retracted) is not bool:
        is_retracted = None
    identifier = _canonical_identifier(work, openalex_id)
    identifier_evidence = _identifier_evidence(work, openalex_id)
    source_availability_status = (
        "arxiv_structured_source_candidate"
        if any(value.startswith("arxiv:") for value in identifier_evidence)
        else "oa_pdf_candidate"
        if open_access_pdf_url
        else "not_available"
    )
    return {
        "paper_key": f"openalex:{openalex_id.casefold()}",
        "display": identifier,
        "identifier_evidence": identifier_evidence,
        "title_evidence": [title],
        "title": title,
        "authors": sorted(set(authors)),
        "year": year,
        "openalex_id": openalex_id,
        "citation_count": citations,
        "matched_tokens": matched,
        "matched_count": len(matched),
        "concept_groups": concept_groups,
        "topic_profile": topic_profile,
        "query_layers": sorted({
            str(value) for value in work.get("_topic_query_layers", [])
            if isinstance(value, str) and value
        }),
        "query_purposes": sorted({
            str(value) for value in work.get("_topic_query_purposes", [])
            if isinstance(value, str) and value
        }),
        "fully_observed_query_layer": bool(
            set(work.get("_topic_query_layers", []))
            & set(work.get("_fully_observed_query_layers", []))
        ),
        "identity_conflict": work.get("_identity_conflict") is True,
        "venue_key": venue_key,
        "venue_display": venue_display,
        "open_access_pdf_url": open_access_pdf_url,
        "source_availability_status": source_availability_status,
        "referenced_works": references,
        "is_retracted": is_retracted,
    }


def _priority_tiers(candidates: list[dict[str, Any]]) -> None:
    citation_values = sorted(
        (row["citation_count"] for row in candidates if row["citation_count"] is not None),
        reverse=True,
    )
    venue_values = sorted(
        (
            row["venue_metric"]["metric_value"]
            for row in candidates
            if row["venue_metric"]["status"] == "available"
        ),
        reverse=True,
    )

    def tier(value: float | int | None, values: list[float | int]) -> str:
        if value is None:
            return "not_available"
        rank = values.index(value) + 1
        share = rank / max(1, len(values))
        if share <= 0.10:
            return "top_10_percent_observed"
        if share <= 0.25:
            return "top_25_percent_observed"
        if share <= 0.50:
            return "top_50_percent_observed"
        return "lower_50_percent_observed"

    for row in candidates:
        row["citation_priority_tier"] = tier(row["citation_count"], citation_values)
        metric = row["venue_metric"]
        row["venue_priority_tier"] = tier(
            metric["metric_value"] if metric["status"] == "available" else None,
            venue_values,
        )


def rank_candidates(
    *,
    topic: str,
    works: list[Any],
    registry: dict[str, Any],
    metadata_accessed_at: str,
    query_strategy: QueryStrategy | None = None,
    selected_seed_cap: int = SELECTED_SEED_CAP,
) -> dict[str, Any]:
    topic_tokens = set(informative_tokens(normalize_text(topic, field="topic")["display"]))
    by_paper = metric_by_paper(registry)
    by_venue = metric_by_venue(registry)
    merged_works, identity_duplicates, identity_conflicts = CandidateIdentityResolver().resolve(works)
    strategy = query_strategy or load_strategy(GENERIC_STRATEGY_FILE)
    candidates = [
        row for work in merged_works
        if (
            row := _candidate(
                work,
                topic_tokens=topic_tokens,
                topic_profile=strategy.profile_id,
                required_topic_groups=strategy.required_topic_groups,
            )
        ) is not None
    ]
    by_key: dict[str, dict[str, Any]] = {}
    for row in candidates:
        by_key.setdefault(row["paper_key"], row)
    candidates = list(by_key.values())
    for row in candidates:
        metric = by_paper.get(row["paper_key"])
        if metric is None and row["venue_key"] is not None:
            metric = by_venue.get(row["venue_key"])
        if metric is None:
            metric = {
                "venue_key": row["venue_key"],
                "display_name": row["venue_display"],
                "status": "not_available",
                "metric_value": None,
                "metric_year": None,
                "source": registry["registry_source"],
            }
        row["venue_metric"] = metric
        row["metadata_accessed_at"] = metadata_accessed_at
    if strategy.eligibility_policy == "all_required_topic_groups":
        eligible = [
            row for row in candidates
            if all(row["concept_groups"].values())
        ]
        for row in candidates:
            if row not in eligible:
                row["eligibility_reason"] = "missing_required_strategy_title_groups"
            else:
                row["eligibility_reason"] = "required_strategy_title_groups"
    elif strategy.eligibility_policy == "minimum_topic_token_match":
        eligible = [row for row in candidates if row["matched_count"] >= RELEVANCE_MINIMUM_MATCHED_TOKENS]
        for row in candidates:
            row["eligibility_reason"] = (
                "minimum_topic_token_match"
                if row in eligible else "no_topic_token_match"
            )
    else:  # Validated QueryStrategy objects cannot reach this branch.
        _fail("invalid_topic_query_strategy", "unsupported eligibility policy")
    _priority_tiers(eligible)

    def citation_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            -row["matched_count"],
            row["source_availability_status"] == "not_available",
            row["citation_count"] is None,
            -(row["citation_count"] or 0),
            row["title"].casefold(),
            row["paper_key"],
        )

    def venue_key(row: dict[str, Any]) -> tuple[Any, ...]:
        metric = row["venue_metric"]
        return (
            -row["matched_count"],
            row["source_availability_status"] == "not_available",
            metric["status"] != "available",
            -(metric["metric_value"] or 0),
            row["title"].casefold(),
            row["paper_key"],
        )

    citation_ranked = sorted(eligible, key=citation_key)
    venue_ranked = sorted(eligible, key=venue_key)
    citation_rank = {row["paper_key"]: rank for rank, row in enumerate(citation_ranked, start=1)}
    venue_rank = {row["paper_key"]: rank for rank, row in enumerate(venue_ranked, start=1)}
    selection_eligible = [row for row in eligible if not row["identity_conflict"]]
    selection_citation_ranked = sorted(selection_eligible, key=citation_key)
    selection_venue_ranked = sorted(selection_eligible, key=venue_key)
    selected_keys: list[str] = []
    purpose_order = tuple(dict.fromkeys(layer.purpose for layer in strategy.strata))
    for purpose in purpose_order:
        nominee = next((row for row in selection_citation_ranked if purpose in row["query_purposes"]), None)
        if nominee is not None and nominee["paper_key"] not in selected_keys:
            selected_keys.append(nominee["paper_key"])
        if len(selected_keys) >= selected_seed_cap:
            break
    for left, right in zip(selection_citation_ranked, selection_venue_ranked, strict=True):
        for row in (left, right):
            if row["paper_key"] not in selected_keys:
                selected_keys.append(row["paper_key"])
            if len(selected_keys) >= selected_seed_cap:
                break
        if len(selected_keys) >= selected_seed_cap:
            break
    for row in eligible:
        row["citation_priority_rank"] = citation_rank[row["paper_key"]]
        row["venue_priority_rank"] = venue_rank[row["paper_key"]]
        row["combined_nomination_rank"] = selected_keys.index(row["paper_key"]) + 1 if row["paper_key"] in selected_keys else None
    eligible.sort(key=lambda row: (
        row["combined_nomination_rank"] is None,
        row["combined_nomination_rank"] or math.inf,
        min(row["citation_priority_rank"], row["venue_priority_rank"]),
        row["paper_key"],
    ))
    return {
        "candidates": eligible,
        "selected_keys": selected_keys,
        "observed_count": len(candidates),
        "eligible_count": len(eligible),
        "excluded_count": len(candidates) - len(eligible),
        "selection_eligible_count": len(selection_eligible),
        "identity_duplicates": identity_duplicates,
        "identity_conflicts": identity_conflicts,
    }


def _fetch_openalex_topic(
    topic: str,
    *,
    opener: Callable[..., Any],
    query_layer: dict[str, str] | None = None,
    page: int = 1,
    result_cap: int = TOPIC_RESULT_CAP,
) -> tuple[list[Any], bool, str, int, int]:
    if type(page) is not int or page < 1:
        _fail("topic_seed_page_invalid", "OpenAlex topic page must be a positive integer")
    if type(result_cap) is not int or not 1 <= result_cap <= TOPIC_RESULT_CAP:
        _fail("topic_seed_record_cap_invalid", "OpenAlex topic result cap is invalid")
    if query_layer is None:
        query_layer = {"kind": "topic_search", "search": topic}
    params = {
        "per-page": str(result_cap),
        "page": str(page),
        "sort": "cited_by_count:desc",
        "select": OPENALEX_SELECT,
    }
    params["sort"] = query_layer.get("sort", "cited_by_count:desc")
    if "filter" in query_layer:
        params["filter"] = query_layer["filter"]
    else:
        params["search"] = query_layer["search"]
    url = f"https://api.openalex.org/works?{urllib.parse.urlencode(params)}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.openalex.org":
        _fail("topic_seed_endpoint_forbidden", "topic bootstrap endpoint is not the exact OpenAlex HTTPS host")
    with opener(url, timeout=30) as response:
        status = getattr(response, "status", None)
        if status is not None and (type(status) is not int or not 200 <= status <= 299):
            _fail("topic_seed_provider_status", f"OpenAlex returned HTTP status {status}")
        final_url = getattr(response, "geturl", lambda: url)()
        if final_url != url:
            _fail("topic_seed_redirect_forbidden", "OpenAlex topic request redirected")
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        _fail("topic_seed_response_cap_exceeded", "OpenAlex response exceeds 2 MiB")
    value = _strict_json(raw)
    if not isinstance(value, dict) or set(value) - {"meta", "results", "group_by"}:
        _fail("invalid_topic_seed_response", "OpenAlex response envelope is invalid")
    results = value.get("results")
    meta = value.get("meta")
    if not isinstance(results, list) or len(results) > result_cap or not isinstance(meta, dict):
        _fail("invalid_topic_seed_response", "OpenAlex result or meta shape is invalid")
    count = meta.get("count")
    if type(count) is not int or count < len(results):
        _fail("invalid_topic_seed_response", "OpenAlex result count is invalid")
    return results, count > len(results), url, count, len(raw)


def _topic_query_layers(topic: str) -> tuple[str, list[dict[str, Any]]]:
    contract = build_topic_contract(topic)
    route_plan = plan_discovery_routes(contract)
    return GENERIC_TOPIC_PROFILE, route_plan["routes"]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        _fail("topic_seed_redirect_forbidden", "OpenAlex topic request redirected")
        return None


def _open_openalex(url: str, *, timeout: int) -> Any:
    opener = urllib.request.build_opener(_NoRedirectHandler())
    return opener.open(url, timeout=timeout)


@dataclass(frozen=True)
class OpenAlexTopicBootstrapCapability:
    venue_metrics_path: Path | None = None
    opener: Callable[..., Any] = _open_openalex
    name: str = "openalex_topic_seed_bootstrap"

    @property
    def version(self) -> str:
        digest = None
        if self.venue_metrics_path is not None:
            _, digest = load_registry(self.venue_metrics_path)
        generic_strategy = load_strategy(GENERIC_STRATEGY_FILE)
        route_plan = plan_discovery_routes(build_topic_contract("generic scholarly topic"))
        route_digest = sha256_bytes(canonical_json_bytes(route_plan))[:12]
        registry_part = digest[:16] if digest else "not_available"
        return (
            f"7+registry.{registry_part}+generic.{generic_strategy.sha256[:8]}"
            f"+routes.{route_digest}"
        )

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        budget = request.get("discovery_budget")
        if not isinstance(budget, dict) or "openalex" not in budget.get("providers", []) or "api.openalex.org" not in budget.get("allowed_domains", []):
            _fail("topic_seed_scope_mismatch", "mission budget does not authorize OpenAlex topic bootstrap")
        if self.venue_metrics_path is None:
            registry = unavailable_registry()
            registry_sha256 = None
            venue_registry_status = "not_available"
        else:
            registry, registry_sha256 = load_registry(self.venue_metrics_path)
            venue_registry_status = "available"
        topic = request["normalized_topic"]["display"]
        accessed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        topic_profile, query_layers = _topic_query_layers(topic)
        required_budget_fields = {
            "max_metadata_requests",
            "max_records_per_metadata_response",
            "max_total_metadata_records",
            "max_unique_candidates",
            "max_bytes_per_metadata_response",
            "max_total_metadata_bytes",
            "max_total_source_bytes",
            "max_pages_per_query",
            "max_selected_seeds",
        }
        if not required_budget_fields <= set(budget):
            _fail("topic_seed_aggregate_budget_required", "priority bootstrap requires aggregate metadata caps")
        tracker = BudgetTracker(budget)
        combined_works: list[Any] = []
        layer_records: list[dict[str, Any]] = []
        successful_layers = 0
        pending_layers = list(query_layers)
        for page in range(1, budget["max_pages_per_query"] + 1):
            next_pending: list[dict[str, Any]] = []
            for index, query_layer in enumerate(pending_layers):
                remaining_records = (
                    budget["max_total_metadata_records"] - tracker.provider_row_count
                )
                if (
                    tracker.request_count >= budget["max_metadata_requests"]
                    or remaining_records <= 0
                ):
                    for remaining in pending_layers[index:]:
                        layer_records.append({
                            "kind": remaining["kind"],
                            "purpose": remaining.get("purpose"),
                            "filter": remaining.get("filter"),
                            "search": remaining.get("search"),
                            "sort": remaining.get("sort", "cited_by_count:desc"),
                            "page": page,
                            "status": "not_dispatched_due_to_budget",
                            "provider_count": None,
                            "returned_count": 0,
                            "response_bytes": 0,
                            "capped": False,
                        })
                    break
                try:
                    tracker.before_request()
                    works, capped, request_url, provider_count, response_bytes = _fetch_openalex_topic(
                        topic,
                        opener=self.opener,
                        query_layer=query_layer,
                        page=page,
                        result_cap=min(
                            budget["max_records_per_metadata_response"],
                            remaining_records,
                        ),
                    )
                    consumption = tracker.consume(returned_count=len(works), response_bytes=response_bytes)
                except MissionStateError:
                    raise
                except Exception as exc:
                    layer_records.append({
                        "kind": query_layer["kind"],
                        "purpose": query_layer.get("purpose"),
                        "filter": query_layer.get("filter"),
                        "search": query_layer.get("search"),
                        "sort": query_layer.get("sort", "cited_by_count:desc"),
                        "page": page,
                        "status": "unavailable",
                        "error_type": type(exc).__name__,
                        "provider_count": None,
                        "returned_count": 0,
                        "response_bytes": 0,
                        "capped": False,
                    })
                    continue
                successful_layers += 1
                for work in works:
                    if isinstance(work, dict):
                        annotated = dict(work)
                        prior_layers = annotated.get("_topic_query_layers", [])
                        annotated["_topic_query_layers"] = sorted({
                            *(
                                value for value in prior_layers
                                if isinstance(prior_layers, list) and isinstance(value, str)
                            ),
                            query_layer["kind"],
                        })
                        annotated["_fully_observed_query_layers"] = sorted({
                            *(
                                value for value in annotated.get("_fully_observed_query_layers", [])
                                if isinstance(annotated.get("_fully_observed_query_layers", []), list)
                                and isinstance(value, str)
                            ),
                            *(() if capped else (query_layer["kind"],)),
                        })
                        annotated["_topic_query_purposes"] = sorted({
                            *(
                                value for value in annotated.get("_topic_query_purposes", [])
                                if isinstance(annotated.get("_topic_query_purposes", []), list)
                                and isinstance(value, str)
                            ),
                            query_layer.get("purpose", "generic_topic"),
                        })
                        combined_works.append(annotated)
                layer_records.append({
                    "kind": query_layer["kind"],
                    "purpose": query_layer.get("purpose"),
                    "filter": query_layer.get("filter"),
                    "search": query_layer.get("search"),
                    "sort": query_layer.get("sort", "cited_by_count:desc"),
                    "page": page,
                    "request_url": request_url,
                    "status": "capped" if capped else "complete",
                    "provider_count": provider_count,
                    "returned_count": len(works),
                    "response_bytes": response_bytes,
                    "consumption_after_request": consumption,
                    "capped": capped,
                })
                if capped and page < budget["max_pages_per_query"]:
                    next_pending.append(query_layer)
            pending_layers = next_pending
            if not pending_layers or tracker.request_count >= budget["max_metadata_requests"]:
                if tracker.request_count >= budget["max_metadata_requests"] and pending_layers:
                    for remaining in pending_layers:
                        layer_records.append({
                            "kind": remaining["kind"],
                            "purpose": remaining.get("purpose"),
                            "filter": remaining.get("filter"),
                            "search": remaining.get("search"),
                            "sort": remaining.get("sort", "cited_by_count:desc"),
                            "page": page + 1,
                            "status": "not_dispatched_due_to_budget",
                            "provider_count": None,
                            "returned_count": 0,
                            "response_bytes": 0,
                            "capped": False,
                        })
                break
        if successful_layers == 0:
            return {
                "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
                "outcome": "unavailable",
                "selected_candidates": [],
                "candidates": [],
                "ambiguities": [],
                "reason": "capability_reported_unavailable",
                "cap": None,
                "observed_count": 0,
                "descriptive": {
                    "network_or_provider_called": True,
                    "provider": "openalex",
                    "ranking_policy": RANKING_POLICY,
                    "venue_registry_sha256": registry_sha256,
                    "venue_registry_status": venue_registry_status,
                    "query_layers": layer_records,
                    "budget_caps": {field: budget[field] for field in sorted(required_budget_fields)},
                    "budget_consumption": tracker.snapshot(),
                    "candidate_status": "metadata_nomination",
                    "generic_topic_centrality_status": "not_validated",
                    "what_is_not_concluded": [
                        "technical correctness",
                        "topic centrality",
                        "literature completeness",
                        "scientific superiority",
                    ],
                },
            }
        ranked = rank_candidates(
            topic=topic,
            works=combined_works,
            registry=registry,
            metadata_accessed_at=accessed_at,
            query_strategy=load_strategy(GENERIC_STRATEGY_FILE),
            selected_seed_cap=budget["max_selected_seeds"],
        )
        observed_count = ranked["observed_count"]
        candidate_frontier_cap = budget["max_unique_candidates"]
        candidate_frontier_capped = observed_count > candidate_frontier_cap
        if candidate_frontier_capped:
            # A broad query may return more metadata nominees than the bounded
            # source campaign can inspect. Keep the deterministic priority
            # frontier and record the omitted tail instead of aborting with no
            # usable candidates.
            ranked["candidates"] = ranked["candidates"][:candidate_frontier_cap]
            retained_keys = {row["paper_key"] for row in ranked["candidates"]}
            ranked["selected_keys"] = [
                key for key in ranked["selected_keys"] if key in retained_keys
            ]
        projected = []
        for row in ranked["candidates"]:
            projected.append({
                "paper_key": row["paper_key"],
                "display": row["display"],
                "identifier_evidence": row["identifier_evidence"],
                "title_evidence": row["title_evidence"],
                "descriptive": {
                    "authors": row["authors"],
                    "year": row["year"],
                    "openalex_id": row["openalex_id"],
                    "topic_matched_tokens": row["matched_tokens"],
                    "concept_groups": row["concept_groups"],
                    "topic_profile": row["topic_profile"],
                    "eligibility_reason": row["eligibility_reason"],
                    "query_layers": row["query_layers"],
                    "query_purposes": row["query_purposes"],
                    "identity_conflict": row["identity_conflict"],
                    "citation_count": row["citation_count"],
                    "citation_count_source": "openalex",
                    "citation_metadata_accessed_at": accessed_at,
                    "citation_priority_rank": row["citation_priority_rank"],
                    "citation_priority_tier": row["citation_priority_tier"],
                    "venue_key": row["venue_key"],
                    "venue_display": row["venue_display"],
                    "venue_metric": row["venue_metric"],
                    "open_access_pdf_url": row["open_access_pdf_url"],
                    "source_availability_status": row["source_availability_status"],
                    "referenced_works": row["referenced_works"],
                    "is_retracted": row["is_retracted"],
                    "venue_priority_rank": row["venue_priority_rank"],
                    "venue_priority_tier": row["venue_priority_tier"],
                    "combined_nomination_rank": row["combined_nomination_rank"],
                    "ranking_policy": RANKING_POLICY,
                    "metadata_only": True,
                    "citation_and_venue_are_priority_signals_only": True,
                },
            })
        by_key = {row["paper_key"]: row for row in projected}
        selected = sorted(
            (by_key[key] for key in ranked["selected_keys"]),
            key=lambda row: row["paper_key"],
        )
        candidates = sorted(projected, key=lambda row: row["paper_key"])
        descriptive = {
            "network_or_provider_called": True,
            "provider": "openalex",
            "query_layers": layer_records,
            "strategy_id": load_strategy(GENERIC_STRATEGY_FILE).profile_id,
            "strategy_version": load_strategy(GENERIC_STRATEGY_FILE).profile_version,
            "strategy_sha256": load_strategy(GENERIC_STRATEGY_FILE).sha256,
            "budget_caps": {field: budget[field] for field in sorted(required_budget_fields)},
            "budget_consumption": tracker.snapshot(),
            "identity_duplicates": ranked["identity_duplicates"],
            "identity_conflicts": ranked["identity_conflicts"],
            "metadata_accessed_at": accessed_at,
            "topic_profile": topic_profile,
            "ranking_policy": RANKING_POLICY,
            "citation_count_role": "priority_signal_only",
            "venue_metric_role": "priority_signal_only",
            "venue_registry_id": registry["registry_id"],
            "venue_registry_sha256": registry_sha256,
            "venue_registry_status": venue_registry_status,
            "query_cap": TOPIC_RESULT_CAP,
            "selected_cap": budget["max_selected_seeds"],
            "observed_candidate_count": observed_count,
            "candidate_frontier_cap": candidate_frontier_cap,
            "candidate_frontier_capped": candidate_frontier_capped,
            "provider_reported_more_than_cap": any(row["capped"] for row in layer_records),
            "eligible_count": ranked["eligible_count"],
            "excluded_count": ranked["excluded_count"],
            "selection_eligible_count": ranked["selection_eligible_count"],
            "candidate_status": "metadata_nomination",
            "generic_topic_centrality_status": "not_validated",
            "what_is_not_concluded": [
                "technical correctness",
                "substantive relevance truth",
                "literature completeness",
                "scientific superiority",
            ],
        }
        if not candidates:
            return {
                "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
                "outcome": "empty",
                "selected_candidates": [],
                "candidates": [],
                "ambiguities": [],
                "reason": None,
                "cap": None,
                "observed_count": 0,
                "descriptive": descriptive,
            }
        if not ranked["selected_keys"]:
            return {
                "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
                "outcome": "capped",
                "selected_candidates": [],
                "candidates": candidates,
                "ambiguities": [],
                "reason": "provider_result_cap_reached",
                "cap": TOPIC_RESULT_CAP,
                "observed_count": max(
                    TOPIC_RESULT_CAP + 1,
                    max((row["provider_count"] or 0) for row in layer_records),
                ),
                "descriptive": descriptive,
            }
        return {
            "schema_version": BOOTSTRAP_OUTCOME_SCHEMA,
            "outcome": "selected",
            "selected_candidates": selected,
            "candidates": candidates,
            "ambiguities": [],
            "reason": None,
            "cap": None,
            "observed_count": observed_count,
            "descriptive": descriptive,
        }


__all__ = [
    "OPENALEX_SELECT",
    "OpenAlexTopicBootstrapCapability",
    "OpenAlexPriorityBootstrapCapability",
    "RANKING_POLICY",
    "SELECTED_SEED_CAP",
    "TOPIC_RESULT_CAP",
    "GENERIC_TOPIC_PROFILE",
    "rank_candidates",
]

# Compatibility name for historical RL/finance fixtures.  The capability is
# now topic-neutral; the RL profile is selected by the declarative strategy.
OpenAlexPriorityBootstrapCapability = OpenAlexTopicBootstrapCapability
