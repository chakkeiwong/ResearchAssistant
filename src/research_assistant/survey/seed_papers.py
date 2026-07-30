"""Replayable multi-provider seed-paper candidate campaigns."""

from __future__ import annotations

import json
import re
import stat
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.discovery_quality import informative_tokens, normalized_title, parse_seed
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.seed_paper_providers import (
    GOOGLE_SCHOLAR_STATUS,
    PROVIDER_BUNDLE_SCHEMA,
    PROVIDER_BUNDLE_SCHEMA_V2,
    PROVIDER_OBSERVATIONS_SCHEMA_V2,
    SUPPORTED_PROVIDERS,
    collect_live_provider_bundle,
    collect_live_provider_bundle_v2,
    normalize_provider_bundle,
    validate_provider_bundle,
    validate_provider_bundle_v2,
)
from research_assistant.survey.topic_contract import (
    build_topic_contract,
    plan_discovery_routes,
    topic_contract_sha256,
    validate_topic_contract,
)
from research_assistant.survey.venue_metrics import (
    load_registry,
    metric_by_paper,
    metric_by_venue,
    unavailable_registry,
)


SEED_CAMPAIGN_SCHEMA = "ra-survey-seed-paper-campaign-v2"
SEED_REPORT_SCHEMA = "ra-survey-seed-paper-report-v2"
SEED_MANIFEST_SCHEMA = "ra-survey-seed-paper-manifest-v2"
SEED_CAMPAIGN_SCHEMA_V3 = "ra-survey-seed-paper-campaign-v3"
SEED_REPORT_SCHEMA_V3 = "ra-survey-seed-paper-report-v3"
SEED_MANIFEST_SCHEMA_V3 = "ra-survey-seed-paper-manifest-v3"
SEED_POLICY_VERSION = "multi-provider-role-facet-portfolio-v2"
SEED_POLICY_VERSION_V3 = "seed-authority-conservative-relevance-v3"
DEFAULT_MAX_SELECTED = 12
ROLE_ORDER = (
    "FOUNDATIONAL",
    "DIRECT_METHOD",
    "SURVEY_OR_TUTORIAL",
    "COMPETITOR",
    "EMPIRICAL_EXAMPLE",
    "BACKGROUND",
)
_TERMINAL_FILES = ("provider_bundle.json", "provider_observations.json", "seed_report.json")


def _fail(code: str, message: str) -> None:
    raise MissionStateError(code, message)


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            _fail("invalid_seed_campaign_artifact", f"{label} must be a regular non-symlink file")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError(
            "invalid_seed_campaign_artifact", f"{label} is not readable JSON"
        ) from exc
    if not isinstance(value, dict):
        _fail("invalid_seed_campaign_artifact", f"{label} must be an object")
    return value


def _write_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        _fail("seed_campaign_output_exists", f"refusing to replace existing artifact: {path}")
    atomic_write_bytes(path, pretty_json_bytes(value))


def _capability_fingerprint() -> str:
    return sha256_bytes(canonical_json_bytes({
        "policy": SEED_POLICY_VERSION,
        "providers": list(SUPPORTED_PROVIDERS),
        "google_scholar": GOOGLE_SCHOLAR_STATUS,
        "identity": "doi_arxiv_openalex_then_exact_title_author_year",
        "ranking": "role_facet_portfolio_with_provider_local_priority",
    }))


def normalize_seed_authorities(seeds: list[str] | None) -> list[str]:
    normalized = []
    for seed in seeds or []:
        if not isinstance(seed, str):
            _fail("invalid_seed_authority", "seed authorities must be text")
        lowered = seed.strip().casefold()
        if lowered.startswith("semantic_scholar:"):
            value = seed.split(":", 1)[1].strip()
            if not value or any(character.isspace() for character in value):
                _fail("invalid_seed_authority", f"invalid seed authority: {seed}")
            normalized.append(f"semantic_scholar:{value.casefold()}")
            continue
        if lowered.startswith("title:"):
            title = seed.split(":", 1)[1].strip()
            if not title:
                _fail("invalid_seed_authority", f"invalid seed authority: {seed}")
            normalized.append(f"title:{normalized_title(title)}")
            continue
        parsed = parse_seed(seed)
        if parsed["kind"] == "invalid":
            _fail("invalid_seed_authority", f"invalid seed authority: {seed}")
        if parsed["kind"] == "title":
            normalized.append(f"title:{parsed['value']}")
        else:
            normalized.append(parsed["value"].casefold())
    return sorted(set(normalized), key=str.casefold)


def build_seed_campaign(
    topic_contract: dict[str, Any], *, max_selected: int, seeds: list[str] | None = None
) -> dict[str, Any]:
    if type(max_selected) is not int or not 1 <= max_selected <= 50:
        _fail("invalid_seed_campaign", "max_selected must be an integer in [1, 50]")
    seed_authorities = normalize_seed_authorities(seeds)
    if len(seed_authorities) > max_selected:
        _fail("invalid_seed_campaign", "seed authority count cannot exceed max_selected")
    if seeds is not None:
        return {
            "schema_version": SEED_CAMPAIGN_SCHEMA_V3,
            "topic_contract_sha256": topic_contract_sha256(topic_contract),
            "route_plan_sha256": sha256_bytes(canonical_json_bytes(plan_discovery_routes(topic_contract))),
            "capability_fingerprint": sha256_bytes(canonical_json_bytes({
                "policy": SEED_POLICY_VERSION_V3,
                "providers": list(SUPPORTED_PROVIDERS),
                "identity": "seed_authority_then_conservative_nomination",
                "ranking": "relevance_class_then_metadata_tiebreak",
            })),
            "seed_authorities": seed_authorities,
            "max_selected": max_selected,
            "providers": list(SUPPORTED_PROVIDERS),
            "venue_registry_sha256": None,
            "ranking_policy": "seed_authority_then_relevance_class_then_metadata_tiebreak",
            "metadata_can_establish_centrality": False,
            "benchmark_labels_consumed": False,
        }
    return {
        "schema_version": SEED_CAMPAIGN_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(topic_contract),
        "route_plan_sha256": sha256_bytes(canonical_json_bytes(plan_discovery_routes(topic_contract))),
        "capability_fingerprint": _capability_fingerprint(),
        "max_selected": max_selected,
        "providers": list(SUPPORTED_PROVIDERS),
        "venue_registry_sha256": None,
        "ranking_policy": "facet_slots_then_role_slots_then_provider_local_priority",
        "metadata_can_establish_centrality": False,
        "benchmark_labels_consumed": False,
    }


@dataclass
class _DisjointSet:
    parents: list[int]

    @classmethod
    def create(cls, size: int) -> _DisjointSet:
        return cls(list(range(size)))

    def find(self, value: int) -> int:
        while self.parents[value] != value:
            self.parents[value] = self.parents[self.parents[value]]
            value = self.parents[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parents[max(left_root, right_root)] = min(left_root, right_root)


def _author_key(authors: list[str]) -> str | None:
    if not authors:
        return None
    tokens = re.findall(r"[a-z0-9]+", authors[0].casefold())
    return tokens[-1] if tokens else None


def _title_similarity(left: str, right: str) -> float:
    left_tokens = set(informative_tokens(left))
    right_tokens = set(informative_tokens(right))
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def _identity_components(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    sets = _DisjointSet.create(len(records))
    by_alias: dict[tuple[str, str], int] = {}
    for index, record in enumerate(records):
        for field in ("doi", "arxiv", "openalex"):
            value = record["identifiers"][field]
            if not value:
                continue
            alias = (field, value.casefold())
            if alias in by_alias:
                sets.union(index, by_alias[alias])
            else:
                by_alias[alias] = index
    fallback: dict[tuple[str, str, int], int] = {}
    for index, record in enumerate(records):
        year = record["year"]
        author = _author_key(record["authors"])
        if year is None or author is None:
            continue
        key = (normalized_title(record["title"]), author, year)
        if key in fallback:
            sets.union(index, fallback[key])
        else:
            fallback[key] = index
    components: dict[int, list[dict[str, Any]]] = {}
    for index, record in enumerate(records):
        components.setdefault(sets.find(index), []).append(record)
    return [components[key] for key in sorted(components)]


def _canonical_id(identifiers: dict[str, list[str]], records: list[dict[str, Any]]) -> str:
    for field in ("doi", "arxiv", "openalex", "semantic_scholar", "crossref"):
        values = identifiers[field]
        if values:
            return f"{field}:{values[0].casefold()}"
    first = records[0]
    return f"{first['provider']}:{first['provider_id'].casefold()}"


def _topic_evidence(
    topic_contract: dict[str, Any],
    title: str,
    abstract: str | None,
    concepts: list[str],
) -> dict[str, Any]:
    title_tokens = set(informative_tokens(title))
    abstract_tokens = set(informative_tokens(abstract or ""))
    concept_tokens = set(informative_tokens(" ".join(concepts)))
    topic_tokens = set(informative_tokens(topic_contract["topic"]))
    alias_tokens = {
        alias: set(informative_tokens(alias)) for alias in topic_contract["aliases"]
    }
    matched_by_source = {
        "title": sorted(title_tokens & topic_tokens),
        "abstract": sorted(abstract_tokens & topic_tokens),
        "concepts": sorted(concept_tokens & topic_tokens),
    }
    matched = sorted(set().union(*matched_by_source.values()))
    matched_aliases = [
        alias for alias, tokens in alias_tokens.items()
        if tokens and any(tokens <= source for source in (title_tokens, abstract_tokens, concept_tokens))
    ]
    facet_matches = []
    for facet in topic_contract["required_facets"]:
        tokens = set(informative_tokens(facet))
        sources = {
            "title": sorted(tokens & title_tokens),
            "abstract": sorted(tokens & abstract_tokens),
            "concepts": sorted(tokens & concept_tokens),
        }
        overlap = sorted(set().union(*sources.values()))
        facet_matches.append({
            "facet": facet,
            "matched_tokens": overlap,
            "matched": bool(overlap),
            "evidence_sources": [name for name, values in sources.items() if values],
        })
    minimum = min(2, len(topic_tokens))
    covered_facets = [row["facet"] for row in facet_matches if row["matched"]]
    corpus_tokens = title_tokens | abstract_tokens | concept_tokens
    matched_exclusions = [
        exclusion for exclusion in topic_contract["exclusions"]
        if (tokens := set(informative_tokens(exclusion))) and tokens <= corpus_tokens
    ]
    eligible = (
        bool(covered_facets)
        and (len(matched) >= minimum or bool(matched_aliases))
        and not matched_exclusions
    )
    return {
        "evidence_sources": [name for name, values in matched_by_source.items() if values],
        "matched_tokens_by_source": matched_by_source,
        "matched_topic_tokens": matched,
        "matched_topic_token_count": len(matched),
        "matched_aliases": matched_aliases,
        "matched_exclusions": matched_exclusions,
        "covered_facets": covered_facets,
        "required_facet_matches": facet_matches,
        "eligible": eligible,
        "eligibility_reason": (
            "at_least_one_facet_and_minimum_topic_tokens"
            if eligible and not matched_aliases
            else "at_least_one_facet_and_controlled_alias"
            if eligible
            else "matched_explicit_exclusion"
            if matched_exclusions
            else "insufficient_metadata_topic_evidence"
        ),
    }


_GENERIC_RELEVANCE_TOKENS = {
    "analysis", "approach", "dynamic", "economic", "estimation", "learning",
    "method", "methods", "model", "models", "parameter", "solution", "system",
    "systems", "using", "year",
}


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token for token in informative_tokens(value)
        if not token.isdigit() and token not in _GENERIC_RELEVANCE_TOKENS
    }


def _abstract_quality(abstract: str | None) -> dict[str, Any]:
    if not abstract:
        return {
            "status": "absent", "word_count": 0, "character_count": 0,
            "sha256": None, "usable_for_relevance": False,
        }
    words = abstract.split()
    lowered = abstract.casefold()
    markers = sum(marker in lowered for marker in ("references", "cited by", "cross ref", "google scholar"))
    contaminated = len(words) > 1200 or (len(words) > 300 and markers >= 2)
    return {
        "status": "contaminated" if contaminated else "usable",
        "word_count": len(words),
        "character_count": len(abstract),
        "sha256": sha256_bytes(abstract.encode("utf-8")),
        "usable_for_relevance": not contaminated,
    }


def _topic_evidence_v3(
    topic_contract: dict[str, Any],
    title: str,
    abstract: str | None,
    concepts: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    quality = _abstract_quality(abstract)
    usable_abstract = abstract if quality["usable_for_relevance"] else ""
    sources = {
        "title": _meaningful_tokens(title),
        "abstract": _meaningful_tokens(usable_abstract),
        "concepts": _meaningful_tokens(" ".join(concepts)),
    }
    topic_tokens = _meaningful_tokens(topic_contract["topic"])
    matched_by_source = {
        name: sorted(tokens & topic_tokens) for name, tokens in sources.items()
    }
    matched = sorted(set().union(*matched_by_source.values()))
    normalized_sources = {
        name: normalized_title(value)
        for name, value in {
            "title": title,
            "abstract": usable_abstract,
            "concepts": " ".join(concepts),
        }.items()
        if value
    }
    matched_aliases = []
    for alias in topic_contract["aliases"]:
        alias_key = normalized_title(alias)
        if any(alias_key in source for source in normalized_sources.values()):
            matched_aliases.append(alias)
    facet_matches = []
    for facet in topic_contract["required_facets"]:
        tokens = _meaningful_tokens(facet)
        overlap_by_source = {
            name: sorted(tokens & source_tokens) for name, source_tokens in sources.items()
        }
        overlap = sorted(set().union(*overlap_by_source.values()))
        exact_phrase = normalized_title(facet) in normalized_sources.get("title", "")
        required_count = max(2, min(3, len(tokens))) if tokens else 2
        strong = exact_phrase or len(overlap) >= required_count
        facet_matches.append({
            "facet": facet,
            "matched_tokens": overlap,
            "matched": strong,
            "evidence_class": "exact_title_phrase" if exact_phrase else "strong_multi_anchor" if strong else "weak_overlap" if overlap else "none",
            "evidence_sources": [name for name, values in overlap_by_source.items() if values],
        })
    covered_facets = [row["facet"] for row in facet_matches if row["matched"]]
    corpus_key = " ".join(normalized_sources.values())
    matched_exclusions = [
        exclusion for exclusion in topic_contract["exclusions"]
        if normalized_title(exclusion) in corpus_key
    ]
    title_match_count = len(sources["title"] & topic_tokens)
    corroborated = title_match_count >= 1 and len(matched) >= 2
    strong_topic = bool(matched_aliases) or title_match_count >= 2 or corroborated
    weak_topic = bool(matched) or any(row["matched_tokens"] for row in facet_matches)
    if matched_exclusions:
        relevance_class = "excluded"
    elif strong_topic and covered_facets:
        relevance_class = "strong_direct"
    elif weak_topic:
        relevance_class = "weak_review"
    else:
        relevance_class = "insufficient"
    return ({
        "evidence_sources": [name for name, values in matched_by_source.items() if values],
        "matched_tokens_by_source": matched_by_source,
        "matched_topic_tokens": matched,
        "matched_topic_token_count": len(matched),
        "matched_aliases": matched_aliases,
        "matched_exclusions": matched_exclusions,
        "covered_facets": covered_facets,
        "required_facet_matches": facet_matches,
        "relevance_class": relevance_class,
        "eligible": relevance_class == "strong_direct",
        "eligibility_reason": relevance_class,
    }, quality)


def _role_hypotheses(
    title: str,
    abstract: str | None,
    concepts: list[str],
    purposes: list[str],
) -> list[str]:
    corpus = " ".join([title, abstract or "", *concepts]).casefold()
    roles: set[str] = set()
    if any(token in corpus for token in ("survey", "tutorial", "review")) or "survey_or_tutorial" in purposes:
        roles.add("SURVEY_OR_TUTORIAL")
    if any(token in corpus for token in ("benchmark", "comparison", "baseline", "competitive")) or "competitor" in purposes:
        roles.add("COMPETITOR")
    if any(token in corpus for token in ("application", "case study", "experiment", "dataset")):
        roles.add("EMPIRICAL_EXAMPLE")
    if any(token in corpus for token in ("foundational", "foundation", "seminal", "fundamental")):
        roles.add("FOUNDATIONAL")
    if any(token in corpus for token in ("we propose", "we introduce", "we present", "algorithm", "method")) or "direct_method" in purposes:
        roles.add("DIRECT_METHOD")
    if not roles:
        roles.add("BACKGROUND")
    return sorted(roles, key=lambda role: (ROLE_ORDER.index(role), role))


def _role_hypotheses_v3(title: str, abstract: str | None, concepts: list[str]) -> list[str]:
    corpus = " ".join([title, abstract or "", *concepts]).casefold()
    roles: set[str] = set()
    if any(token in corpus for token in ("survey", "tutorial", "review of")):
        roles.add("SURVEY_OR_TUTORIAL")
    if any(token in corpus for token in ("benchmark", "comparison", "compared with", "competitor")):
        roles.add("COMPETITOR")
    if any(token in corpus for token in ("application", "case study", "experiment", "dataset")):
        roles.add("EMPIRICAL_EXAMPLE")
    if any(token in corpus for token in ("foundational", "seminal", "fundamental")):
        roles.add("FOUNDATIONAL")
    if any(token in corpus for token in ("we propose", "we introduce", "we develop", "algorithm")):
        roles.add("DIRECT_METHOD")
    if not roles:
        roles.add("BACKGROUND")
    return sorted(roles, key=lambda role: (ROLE_ORDER.index(role), role))


def _fused_candidate(
    component: list[dict[str, Any]], topic_contract: dict[str, Any], *, conservative: bool = False
) -> dict[str, Any]:
    component.sort(key=lambda row: (row["provider"], row["provider_best_rank"], row["provider_id"]))
    identifiers = {
        field: sorted({
            value for record in component
            if (value := record["identifiers"][field]) is not None
        }, key=str.casefold)
        for field in ("arxiv", "crossref", "doi", "openalex", "semantic_scholar")
    }
    title = sorted(
        (record["title"] for record in component),
        key=lambda value: (-len(informative_tokens(value)), value.casefold()),
    )[0]
    abstracts = sorted(
        {record["abstract"] for record in component if record.get("abstract")},
        key=str.casefold,
    )
    abstract = abstracts[0] if abstracts else None
    concepts = sorted(
        {concept for record in component for concept in record.get("concepts", [])},
        key=str.casefold,
    )
    title_conflict = any(_title_similarity(title, record["title"]) < 0.50 for record in component)
    strong_conflict = any(len(identifiers[field]) > 1 for field in ("doi", "arxiv", "openalex"))
    years = sorted({record["year"] for record in component if record["year"] is not None})
    publication_dates = sorted({
        record["publication_date"]
        for record in component
        if record.get("publication_date")
    })
    year_conflict = bool(years and years[-1] - years[0] > 2)
    identity_status = "conflict" if title_conflict or strong_conflict or year_conflict else "resolved"
    providers = sorted({record["provider"] for record in component})
    retraction_statuses = {record["retraction_status"] for record in component}
    if "retracted" in retraction_statuses:
        safety_status = "quarantined"
    elif "not_retracted" in retraction_statuses:
        safety_status = "no_issue_found_in_declared_checks"
    else:
        safety_status = "not_checked"
    provider_priority = [
        {
            "provider": record["provider"],
            "provider_best_rank": record["provider_best_rank"],
            "citation_count": record["citation_count"],
            "year": record["year"],
            "publication_date": record.get("publication_date"),
        }
        for record in component
    ]
    provider_priority.sort(key=lambda row: row["provider"])
    if conservative:
        topic_evidence, abstract_quality = _topic_evidence_v3(topic_contract, title, abstract, concepts)
        role_hypotheses = _role_hypotheses_v3(
            title,
            abstract if abstract_quality["usable_for_relevance"] else None,
            concepts,
        )
    else:
        topic_evidence = _topic_evidence(topic_contract, title, abstract, concepts)
        role_hypotheses = _role_hypotheses(
            title,
            abstract,
            concepts,
            sorted({purpose for record in component for purpose in record["route_purposes"]}),
        )
    candidate = {
        "paper_id": _canonical_id(identifiers, component),
        "title": title,
        "abstract": abstract,
        "concepts": concepts,
        "authors": sorted({author for record in component for author in record["authors"]}),
        "year": years[-1] if years else None,
        "publication_date": publication_dates[-1] if publication_dates else None,
        "identifiers": identifiers,
        "identity_status": identity_status,
        "identity_conflict_reasons": sorted(
            reason for reason, present in (
                ("title_mismatch", title_conflict),
                ("strong_identifier_conflict", strong_conflict),
                ("publication_year_conflict", year_conflict),
            ) if present
        ),
        "providers": providers,
        "provider_count": len(providers),
        "provider_priority": provider_priority,
        "query_routes": sorted({route for record in component for route in record["route_ids"]}),
        "query_purposes": sorted({purpose for record in component for purpose in record["route_purposes"]}),
        "source_urls": sorted({record["source_url"] for record in component}),
        "venue_keys": sorted({
            record["venue_key"] for record in component if record.get("venue_key")
        }),
        "topic_evidence": topic_evidence,
        "role_hypotheses": role_hypotheses,
        "role_hypothesis_status": "unverified_metadata_hypothesis",
        "source_status": "not_inspected",
        "safety_status": safety_status,
        "metadata_can_establish_centrality": False,
    }
    if conservative:
        candidate["abstract_quality"] = abstract_quality
    return candidate


def fuse_seed_candidates(
    topic_contract: dict[str, Any],
    observations: dict[str, Any],
    *,
    max_selected: int,
    venue_registry: dict[str, Any] | None = None,
    seeds: list[str] | None = None,
) -> dict[str, Any]:
    conservative = observations.get("schema_version") == PROVIDER_OBSERVATIONS_SCHEMA_V2 or seeds is not None
    if observations.get("schema_version") not in {"ra-survey-seed-provider-observations-v1", PROVIDER_OBSERVATIONS_SCHEMA_V2}:
        _fail("invalid_seed_provider_observations", "provider observation schema is unsupported")
    if observations.get("topic_contract_sha256") != topic_contract_sha256(topic_contract):
        _fail("invalid_seed_provider_observations", "provider observations belong to another topic")
    candidates = [
        _fused_candidate(component, topic_contract, conservative=conservative)
        for component in _identity_components(observations["records"])
    ]
    registry = venue_registry or unavailable_registry()
    paper_metrics = metric_by_paper(registry)
    venue_metrics = metric_by_venue(registry)
    try:
        access_year = datetime.fromisoformat(
            observations["accessed_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc).year
    except (KeyError, TypeError, ValueError) as exc:
        raise MissionStateError(
            "invalid_seed_provider_observations",
            "provider observations accessed_at must be timezone-aware ISO-8601",
        ) from exc
    for row in candidates:
        metric = paper_metrics.get(row["paper_id"])
        if metric is None:
            for venue_key in row["venue_keys"]:
                metric = venue_metrics.get(venue_key.casefold())
                if metric is not None:
                    break
        row["venue_metric"] = metric or {
            "status": "not_available",
            "metric_value": None,
            "metric_year": None,
            "display_name": None,
        }
        row["recency_years"] = max(0, access_year - row["year"]) if row["year"] else None
        row["provider_age_normalized_citations"] = [
            {
                "provider": item["provider"],
                "citations_per_year": (
                    item["citation_count"] / max(1, access_year - item["year"] + 1)
                    if item["citation_count"] is not None and item.get("year") else None
                ),
            }
            for item in row["provider_priority"]
        ]

    if conservative:
        return _fuse_seed_candidates_v3(
            candidates,
            seeds=normalize_seed_authorities(seeds if seeds is not None else observations.get("seed_authorities", [])),
            max_selected=max_selected,
            required_facets=topic_contract["required_facets"],
        )

    def priority(
        row: dict[str, Any],
        covered_facets: set[str],
        covered_roles: set[str],
    ) -> tuple[Any, ...]:
        best_rank = min(item["provider_best_rank"] for item in row["provider_priority"])
        age_rate = max(
            (item["citations_per_year"] or 0 for item in row["provider_age_normalized_citations"]),
            default=0,
        )
        return (
            -len(set(row["topic_evidence"]["covered_facets"]) - covered_facets),
            -len(set(row["role_hypotheses"]) - covered_roles),
            -row["topic_evidence"]["matched_topic_token_count"],
            -row["provider_count"],
            -(row["venue_metric"].get("metric_value") or 0),
            -age_rate,
            -(row["year"] or 0),
            best_rank,
            -len(row["query_purposes"]),
            row["title"].casefold(),
            row["paper_id"],
        )

    eligible = [
        row for row in candidates
        if row["identity_status"] == "resolved"
        and row["safety_status"] != "quarantined"
        and row["topic_evidence"]["eligible"]
    ]
    selected: list[dict[str, Any]] = []
    remaining = list(eligible)
    covered_facets: set[str] = set()
    covered_roles: set[str] = set()
    selection_reasons: dict[str, list[str]] = {}

    def select(row: dict[str, Any], reason: str) -> None:
        selected.append(row)
        remaining.remove(row)
        selection_reasons.setdefault(row["paper_id"], []).append(reason)
        covered_facets.update(row["topic_evidence"]["covered_facets"])
        covered_roles.update(row["role_hypotheses"])

    for facet in topic_contract["required_facets"]:
        if len(selected) >= max_selected:
            break
        if facet in covered_facets:
            continue
        choices = [row for row in remaining if facet in row["topic_evidence"]["covered_facets"]]
        if choices:
            select(min(choices, key=lambda row: priority(row, covered_facets, covered_roles)), f"facet:{facet}")
    for role in ROLE_ORDER:
        if len(selected) >= max_selected:
            break
        if role in covered_roles:
            continue
        choices = [
            row for row in remaining
            if role in row["role_hypotheses"]
            and set(topic_contract["required_facets"])
            <= set(row["topic_evidence"]["covered_facets"])
        ]
        if choices:
            select(min(choices, key=lambda row: priority(row, covered_facets, covered_roles)), f"role:{role}")
    required_facets = set(topic_contract["required_facets"])
    fill_candidates = [
        row for row in remaining
        if required_facets <= set(row["topic_evidence"]["covered_facets"])
        or row["provider_count"] >= 2
    ]
    while fill_candidates and len(selected) < max_selected:
        select(
            min(fill_candidates, key=lambda row: priority(row, covered_facets, covered_roles)),
            "bounded_priority_fill",
        )
        fill_candidates = [row for row in fill_candidates if row in remaining]
    selected_ids = {row["paper_id"] for row in selected}
    for row in candidates:
        if row["safety_status"] == "quarantined":
            disposition = "QUARANTINED"
        elif row["identity_status"] != "resolved":
            disposition = "BLOCKED_IDENTITY_CONFLICT"
        elif not row["topic_evidence"]["eligible"]:
            disposition = "NOT_SELECTED_TOPIC_MISMATCH"
        elif row["paper_id"] in selected_ids:
            disposition = "SELECTED_SEED_CANDIDATE"
        else:
            disposition = "NOT_SELECTED_CAP"
        row["disposition"] = disposition
        row["selection_reasons"] = sorted(selection_reasons.get(row["paper_id"], []))
    candidates.sort(key=lambda row: (
        row["disposition"] != "SELECTED_SEED_CANDIDATE",
        priority(row, covered_facets, covered_roles),
    ))
    return {
        "candidates": candidates,
        "selected_paper_ids": [
            row["paper_id"] for row in candidates
            if row["disposition"] == "SELECTED_SEED_CANDIDATE"
        ],
        "facet_coverage": sorted(covered_facets),
        "role_coverage": sorted(
            covered_roles, key=lambda role: (ROLE_ORDER.index(role), role)
        ),
        "uncovered_facets": sorted(set(topic_contract["required_facets"]) - covered_facets),
        "uncovered_roles": [role for role in ROLE_ORDER if role not in covered_roles],
    }


def _candidate_seed_aliases(row: dict[str, Any]) -> set[str]:
    aliases = {row["paper_id"].casefold(), f"title:{normalized_title(row['title'])}"}
    for field in ("doi", "arxiv", "openalex", "semantic_scholar", "crossref"):
        aliases.update(f"{field}:{value.casefold()}" for value in row["identifiers"].get(field, []))
    return aliases


def _fuse_seed_candidates_v3(
    candidates: list[dict[str, Any]], *, seeds: list[str], max_selected: int,
    required_facets: list[str],
) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    authority_ids: set[str] = set()
    authority_order: dict[str, int] = {}
    unresolved = []
    for seed in seeds:
        matches = [row for row in candidates if seed.casefold() in _candidate_seed_aliases(row)]
        if len(matches) != 1:
            unresolved.append({"seed": seed, "match_count": len(matches)})
            continue
        row = matches[0]
        if row["identity_status"] != "resolved" or row["safety_status"] == "quarantined":
            unresolved.append({"seed": seed, "match_count": 1, "reason": "identity_or_safety_block"})
            continue
        if row["paper_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["paper_id"])
            authority_ids.add(row["paper_id"])
            authority_order[row["paper_id"]] = len(authority_order)

    class_rank = {"strong_direct": 0, "weak_review": 1, "insufficient": 2, "excluded": 3}

    def priority(row: dict[str, Any]) -> tuple[Any, ...]:
        age_rate = max((item["citations_per_year"] or 0 for item in row["provider_age_normalized_citations"]), default=0)
        best_rank = min(item["provider_best_rank"] for item in row["provider_priority"])
        return (
            class_rank[row["topic_evidence"]["relevance_class"]],
            -len(row["topic_evidence"]["covered_facets"]),
            -row["topic_evidence"]["matched_topic_token_count"],
            -row["provider_count"],
            -age_rate,
            best_rank,
            row["title"].casefold(),
            row["paper_id"],
        )

    eligible = [
        row for row in candidates
        if row["paper_id"] not in selected_ids
        and row["identity_status"] == "resolved"
        and row["safety_status"] != "quarantined"
        and row["topic_evidence"]["relevance_class"] == "strong_direct"
    ]
    for row in sorted(eligible, key=priority):
        if len(selected) >= max_selected:
            break
        selected.append(row)
        selected_ids.add(row["paper_id"])

    for row in candidates:
        if row["safety_status"] == "quarantined":
            disposition = "QUARANTINED"
        elif row["identity_status"] != "resolved":
            disposition = "BLOCKED_IDENTITY_CONFLICT"
        elif row["paper_id"] in authority_ids:
            disposition = "SEED_AUTHORITY"
        elif row["paper_id"] in selected_ids:
            disposition = "SELECTED_SEED_CANDIDATE"
        elif row["topic_evidence"]["relevance_class"] == "weak_review":
            disposition = "REVIEW_REQUIRED_WEAK_MATCH"
        elif row["topic_evidence"]["relevance_class"] == "excluded":
            disposition = "NOT_SELECTED_EXCLUDED"
        else:
            disposition = "NOT_SELECTED_TOPIC_MISMATCH"
        row["disposition"] = disposition
        row["selection_reasons"] = ["seed_authority"] if disposition == "SEED_AUTHORITY" else ["strong_relevance"] if disposition == "SELECTED_SEED_CANDIDATE" else []
    candidates.sort(key=lambda row: (
        {"SEED_AUTHORITY": 0, "SELECTED_SEED_CANDIDATE": 1, "REVIEW_REQUIRED_WEAK_MATCH": 2}.get(row["disposition"], 3),
        authority_order.get(row["paper_id"], len(authority_order)),
        priority(row),
    ))
    covered_facets = sorted({facet for row in selected for facet in row["topic_evidence"]["covered_facets"]})
    covered_roles = {role for row in selected for role in row["role_hypotheses"]}
    return {
        "candidates": candidates,
        "selected_paper_ids": [row["paper_id"] for row in candidates if row["disposition"] in {"SEED_AUTHORITY", "SELECTED_SEED_CANDIDATE"}],
        "seed_authority_ids": [row["paper_id"] for row in candidates if row["disposition"] == "SEED_AUTHORITY"],
        "unresolved_seed_authorities": unresolved,
        "facet_coverage": covered_facets,
        "role_coverage": sorted(covered_roles, key=lambda role: (ROLE_ORDER.index(role), role)),
        "uncovered_facets": sorted(set(required_facets) - set(covered_facets)),
        "uncovered_roles": [role for role in ROLE_ORDER if role not in covered_roles],
    }


def _report(
    topic_contract: dict[str, Any],
    campaign: dict[str, Any],
    observations: dict[str, Any],
    fused: dict[str, Any],
) -> dict[str, Any]:
    repaired = campaign["schema_version"] == SEED_CAMPAIGN_SCHEMA_V3
    statuses = {row["provider"]: row["status"] for row in observations["provider_statuses"]}
    selected = fused["selected_paper_ids"]
    unresolved = fused.get("unresolved_seed_authorities", [])
    if unresolved:
        status = "blocked_unresolved_seed_authority"
    elif selected:
        status = "seed_candidates_selected"
    elif statuses and all(
        value in {
            "not_available", "rate_limited", "transport_failed", "http_failed",
            "skipped_after_provider_veto", "unsupported_exact_route",
        }
        for value in statuses.values()
    ):
        status = "blocked_all_providers_unavailable"
    else:
        status = "blocked_no_eligible_seed_candidate"
    gaps = [
        f"provider {provider} is {provider_status}"
        for provider, provider_status in sorted(statuses.items())
        if provider_status not in {"available", "empty"}
    ]
    gaps.extend(
        f"provider {row['provider']} route {row['route_id']} is {row['status']}"
        for row in observations["route_statuses"]
        if row["status"] not in {"available", "empty"}
    )
    if GOOGLE_SCHOLAR_STATUS:
        gaps.append("Google Scholar is unavailable as an automated route because it has no supported public API")
    result = {
        "schema_version": SEED_REPORT_SCHEMA_V3 if repaired else SEED_REPORT_SCHEMA,
        "status": status,
        "topic": topic_contract["topic"],
        "topic_contract_sha256": campaign["topic_contract_sha256"],
        "selected_paper_ids": selected,
        "selected_count": len(selected),
        "candidate_count": len(fused["candidates"]),
        "candidates": fused["candidates"],
        "facet_coverage": fused["facet_coverage"],
        "role_coverage": fused["role_coverage"],
        "uncovered_facets": fused["uncovered_facets"],
        "uncovered_roles": fused["uncovered_roles"],
        "provider_statuses": observations["provider_statuses"],
        "route_statuses": observations["route_statuses"],
        "budget_consumption": observations["budget_consumption"],
        "coverage_gaps": sorted(gaps),
        "next_required_actions": [
            "inspect primary technical sources before treating a nomination as topic-central",
            "run backward and forward snowballing and record important omissions",
            "resolve identity, source-safety, and provider gaps shown in this report",
        ],
        "what_is_not_concluded": [
            "canonical best paper",
            "literature completeness",
            "paper correctness",
            "source safety beyond declared checks",
            "statistically supported ranking",
            "topic centrality",
            "universal topic recall",
        ],
        "metadata_can_establish_centrality": False,
        "benchmark_labels_consumed": False,
    }
    if repaired:
        result.update({
            "seed_authorities": campaign["seed_authorities"],
            "seed_authority_ids": fused["seed_authority_ids"],
            "unresolved_seed_authorities": unresolved,
            "selection_policy": campaign["ranking_policy"],
        })
    return result


def _manifest(root: Path, campaign: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": (
            SEED_MANIFEST_SCHEMA_V3
            if campaign["schema_version"] == SEED_CAMPAIGN_SCHEMA_V3
            else SEED_MANIFEST_SCHEMA
        ),
        "topic_contract_sha256": campaign["topic_contract_sha256"],
        "seed_campaign_sha256": sha256_bytes(canonical_json_bytes(campaign)),
        "artifact_sha256": {
            filename: sha256_bytes((root / filename).read_bytes())
            for filename in _TERMINAL_FILES
        },
        "benchmark_labels_consumed": False,
    }


def _validated_bundle(
    value: dict[str, Any], *, expected_topic_contract_sha256: str
) -> dict[str, Any]:
    schema = value.get("schema_version")
    if schema == PROVIDER_BUNDLE_SCHEMA:
        return validate_provider_bundle(
            value, expected_topic_contract_sha256=expected_topic_contract_sha256
        )
    if schema == PROVIDER_BUNDLE_SCHEMA_V2:
        return validate_provider_bundle_v2(
            value, expected_topic_contract_sha256=expected_topic_contract_sha256
        )
    _fail("invalid_seed_provider_bundle", "provider bundle schema is unsupported")
    raise AssertionError


def run_seed_paper_campaign(
    *,
    topic: str,
    output_dir: Path,
    confirm_public_discovery: bool = False,
    resume: bool = False,
    observation_bundle: Path | None = None,
    max_selected: int = DEFAULT_MAX_SELECTED,
    venue_metrics_registry: Path | None = None,
    required_facets: list[str] | None = None,
    aliases: list[str] | None = None,
    exclusions: list[str] | None = None,
    scope_note: str | None = None,
    seeds: list[str] | None = None,
) -> dict[str, Any]:
    """Run or replay a bounded multi-provider seed-candidate campaign."""
    assert_public_write_path_allowed(output_dir)
    root = output_dir.absolute()
    topic_contract = build_topic_contract(
        topic,
        required_facets=required_facets,
        aliases=aliases,
        exclusions=exclusions,
        scope_note=scope_note,
    )
    if venue_metrics_registry is None:
        venue_registry = unavailable_registry()
        venue_registry_sha256 = None
    else:
        venue_registry, venue_registry_sha256 = load_registry(venue_metrics_registry)
    if resume:
        if observation_bundle is not None:
            _fail("seed_campaign_resume_mismatch", "resume cannot replace the recorded provider bundle")
        replay = validate_seed_paper_campaign(
            root,
            expected_topic=topic,
            venue_metrics_registry=venue_metrics_registry,
        )
        controls_supplied = any(
            value is not None
            for value in (required_facets, aliases, exclusions, scope_note)
        )
        replay_seeds = replay["campaign"].get("seed_authorities", [])
        if (
            replay["campaign"]["max_selected"] != max_selected
            or (seeds is not None and normalize_seed_authorities(seeds) != replay_seeds)
            or (
                controls_supplied
                and replay["campaign"]["topic_contract_sha256"] != topic_contract_sha256(topic_contract)
            )
        ):
            _fail(
                "seed_campaign_resume_mismatch",
                "resume topic controls or selection cap differ from campaign",
            )
        return replay["report"]
    if root.exists():
        if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
            _fail("seed_campaign_output_exists", "fresh seed campaign output must be absent or empty")
    root.mkdir(parents=True, exist_ok=True)
    if observation_bundle is None:
        if not confirm_public_discovery:
            _fail("public_discovery_not_confirmed", "live seed discovery requires explicit confirmation")
        normalized_seeds = normalize_seed_authorities(seeds)
        campaign = build_seed_campaign(
            topic_contract, max_selected=max_selected, seeds=normalized_seeds
        )
        bundle = collect_live_provider_bundle_v2(
            topic_contract, seeds=campaign["seed_authorities"]
        )
    else:
        bundle = _validated_bundle(
            _load(observation_bundle.resolve(strict=True), "seed provider observation bundle"),
            expected_topic_contract_sha256=topic_contract_sha256(topic_contract),
        )
        if bundle["schema_version"] == PROVIDER_BUNDLE_SCHEMA:
            if seeds is not None:
                _fail(
                    "invalid_seed_provider_bundle",
                    "legacy provider bundles cannot bind seed authorities",
                )
            campaign = build_seed_campaign(topic_contract, max_selected=max_selected)
        else:
            normalized_seeds = normalize_seed_authorities(seeds)
            if seeds is not None and normalized_seeds != bundle["seed_authorities"]:
                _fail("invalid_seed_provider_bundle", "provider bundle seed authorities differ")
            campaign = build_seed_campaign(
                topic_contract,
                max_selected=max_selected,
                seeds=bundle["seed_authorities"],
            )
    campaign["venue_registry_sha256"] = venue_registry_sha256
    observations = normalize_provider_bundle(bundle)
    fused = fuse_seed_candidates(
        topic_contract,
        observations,
        max_selected=max_selected,
        venue_registry=venue_registry,
        seeds=campaign.get("seed_authorities") if campaign["schema_version"] == SEED_CAMPAIGN_SCHEMA_V3 else None,
    )
    report = _report(topic_contract, campaign, observations, fused)
    _write_new(root / "topic_contract.json", topic_contract)
    _write_new(root / "seed_campaign.json", campaign)
    _write_new(root / "provider_bundle.json", bundle)
    _write_new(root / "provider_observations.json", observations)
    _write_new(root / "seed_report.json", report)
    manifest = _manifest(root, campaign)
    _write_new(root / "seed_manifest.json", manifest)
    return report


def validate_seed_paper_campaign(
    output_dir: Path,
    *,
    expected_topic: str | None = None,
    venue_metrics_registry: Path | None = None,
) -> dict[str, Any]:
    root = output_dir.absolute()
    topic_contract = _load(root / "topic_contract.json", "topic contract")
    topic = validate_topic_contract(topic_contract)
    if topic != topic_contract:
        _fail("invalid_seed_campaign_artifact", "topic contract is not canonical")
    if expected_topic is not None and topic_contract["topic"] != build_topic_contract(expected_topic)["topic"]:
        _fail("seed_campaign_resume_mismatch", "resume topic differs from campaign")
    campaign = _load(root / "seed_campaign.json", "seed campaign")
    schema = campaign.get("schema_version")
    if schema == SEED_CAMPAIGN_SCHEMA:
        expected_campaign = build_seed_campaign(
            topic_contract, max_selected=campaign.get("max_selected")
        )
        expected_bundle_schema = PROVIDER_BUNDLE_SCHEMA
        replay_seeds = None
    elif schema == SEED_CAMPAIGN_SCHEMA_V3:
        expected_campaign = build_seed_campaign(
            topic_contract,
            max_selected=campaign.get("max_selected"),
            seeds=campaign.get("seed_authorities"),
        )
        expected_bundle_schema = PROVIDER_BUNDLE_SCHEMA_V2
        replay_seeds = expected_campaign["seed_authorities"]
    else:
        _fail("invalid_seed_campaign_artifact", "seed campaign schema is unsupported")
    expected_campaign["venue_registry_sha256"] = campaign.get("venue_registry_sha256")
    if campaign != expected_campaign:
        _fail("invalid_seed_campaign_artifact", "seed campaign contract differs from replay")
    bundle = _validated_bundle(
        _load(root / "provider_bundle.json", "provider bundle"),
        expected_topic_contract_sha256=campaign["topic_contract_sha256"],
    )
    if bundle["schema_version"] != expected_bundle_schema:
        _fail("invalid_seed_campaign_artifact", "campaign and provider bundle schemas differ")
    if replay_seeds is not None and bundle["seed_authorities"] != replay_seeds:
        _fail("invalid_seed_campaign_artifact", "campaign and provider seed authorities differ")
    observations = normalize_provider_bundle(bundle)
    recorded_observations = _load(root / "provider_observations.json", "provider observations")
    if observations != recorded_observations:
        _fail("invalid_seed_campaign_artifact", "provider observations differ from replay")
    recorded_registry_sha256 = campaign["venue_registry_sha256"]
    if recorded_registry_sha256 is None:
        if venue_metrics_registry is not None:
            _fail(
                "invalid_seed_campaign_artifact",
                "campaign did not use a venue registry but replay supplied one",
            )
        venue_registry = unavailable_registry()
    else:
        if venue_metrics_registry is None:
            _fail(
                "invalid_seed_campaign_artifact",
                "replay of venue-enriched seed campaign requires the original registry",
            )
        venue_registry, observed_registry_sha256 = load_registry(venue_metrics_registry)
        if observed_registry_sha256 != recorded_registry_sha256:
            _fail(
                "invalid_seed_campaign_artifact",
                "venue registry digest differs from the recorded campaign",
            )
    fused = fuse_seed_candidates(
        topic_contract,
        observations,
        max_selected=campaign["max_selected"],
        venue_registry=venue_registry,
        seeds=replay_seeds,
    )
    report = _report(topic_contract, campaign, observations, fused)
    if report != _load(root / "seed_report.json", "seed report"):
        _fail("invalid_seed_campaign_artifact", "seed report differs from replay")
    manifest = _load(root / "seed_manifest.json", "seed manifest")
    expected_manifest = _manifest(root, campaign)
    if manifest != expected_manifest:
        _fail("invalid_seed_campaign_artifact", "seed manifest differs from replay")
    return {"campaign": campaign, "report": report, "manifest": manifest}


__all__ = [
    "DEFAULT_MAX_SELECTED", "SEED_CAMPAIGN_SCHEMA", "SEED_MANIFEST_SCHEMA",
    "SEED_REPORT_SCHEMA", "SEED_CAMPAIGN_SCHEMA_V3", "SEED_MANIFEST_SCHEMA_V3",
    "SEED_REPORT_SCHEMA_V3", "build_seed_campaign", "fuse_seed_candidates",
    "normalize_seed_authorities",
    "run_seed_paper_campaign", "validate_seed_paper_campaign",
]
