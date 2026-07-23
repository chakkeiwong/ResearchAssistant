from __future__ import annotations

import copy
import json
from pathlib import Path
import urllib.parse

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.seed_paper_providers import (
    PROVIDER_BUNDLE_SCHEMA,
    collect_live_provider_bundle,
    normalize_arxiv,
    normalize_provider_bundle,
    validate_provider_bundle,
)
from research_assistant.survey.seed_papers import (
    fuse_seed_candidates,
    run_seed_paper_campaign,
    validate_seed_paper_campaign,
)
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256
from research_assistant.survey.topic_contract import MAX_ROUTES, plan_discovery_routes
from research_assistant.survey.venue_metrics import VENUE_METRICS_SCHEMA, VENUE_METRIC_NAME


TOPIC = "Neural optimal transport"


def _openalex_item(
    work_id: str,
    title: str,
    *,
    doi: str | None,
    citations: int,
    year: int = 2022,
) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": title,
        "authorships": [{"author": {"display_name": "Alice Researcher"}}],
        "publication_year": year,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "cited_by_count": citations,
        "ids": {"openalex": f"https://openalex.org/{work_id}"},
        "primary_location": {"source": {"display_name": "Journal"}},
        "is_retracted": False,
    }


def _crossref_item(title: str, *, doi: str, citations: int, year: int = 2022) -> dict:
    return {
        "DOI": doi,
        "title": [title],
        "author": [{"given": "Alice", "family": "Researcher"}],
        "published": {"date-parts": [[year]]},
        "is-referenced-by-count": citations,
        "container-title": ["Journal"],
        "URL": f"https://doi.org/{doi}",
    }


def _semantic_item(
    paper_id: str,
    title: str,
    *,
    doi: str | None,
    citations: int,
    year: int = 2022,
) -> dict:
    external = {"DOI": doi} if doi else {}
    return {
        "paperId": paper_id,
        "title": title,
        "authors": [{"name": "Alice Researcher"}],
        "year": year,
        "citationCount": citations,
        "externalIds": external,
        "venue": "Journal",
        "url": f"https://www.semanticscholar.org/paper/{paper_id}",
    }


def _request(provider: str, response: dict | None, *, status: str = "available") -> dict:
    if provider == "openalex":
        total = response["meta"]["count"] if response is not None else None
    elif provider == "crossref":
        total = response["message"]["total-results"] if response is not None else None
    else:
        total = response["total"] if response is not None else None
    return {
        "route_id": "exact_high_citation",
        "purpose": "foundational_or_high_citation",
        "query": TOPIC,
        "status": status,
        "capped": status == "capped",
        "provider_total": total,
        "request_url": f"https://example.test/{provider}",
        "response": response,
        "detail": "fixture" if status == "not_available" else None,
    }


def _bundle() -> dict:
    contract = build_topic_contract(TOPIC)
    doi = "10.5555/neural-ot"
    title = "Neural Optimal Transport"
    openalex = {
        "meta": {"count": 2},
        "results": [
            _openalex_item("W1", title, doi=doi, citations=120),
            _openalex_item("W9", "Neural Machine Translation", doi=None, citations=5000),
        ],
    }
    crossref = {
        "message": {
            "total-results": 1,
            "items": [_crossref_item(title, doi=doi, citations=100)],
        }
    }
    semantic = {
        "total": 1,
        "data": [_semantic_item("S1", title, doi=doi, citations=140)],
    }
    return {
        "schema_version": PROVIDER_BUNDLE_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(contract),
        "accessed_at": "2026-07-22T00:00:00+00:00",
        "providers": [
            {"provider": "crossref", "status": "available", "requests": [_request("crossref", crossref)]},
            {"provider": "openalex", "status": "available", "requests": [_request("openalex", openalex)]},
            {"provider": "semantic_scholar", "status": "available", "requests": [_request("semantic_scholar", semantic)]},
        ],
        "benchmark_labels_consumed": False,
    }


def test_raw_bundle_fuses_doi_and_keeps_provider_citations_separate() -> None:
    bundle = validate_provider_bundle(_bundle())
    observations = normalize_provider_bundle(bundle)
    result = fuse_seed_candidates(build_topic_contract(TOPIC), observations, max_selected=12)
    assert result["selected_paper_ids"] == ["doi:10.5555/neural-ot"]
    selected = result["candidates"][0]
    assert selected["provider_count"] == 3
    assert [row["citation_count"] for row in selected["provider_priority"]] == [100, 120, 140]
    assert selected["metadata_can_establish_centrality"] is False
    off_topic = next(row for row in result["candidates"] if row["paper_id"] == "openalex:w9")
    assert off_topic["disposition"] == "NOT_SELECTED_TOPIC_MISMATCH"


def test_arxiv_normalization_preserves_old_and_new_identifier_families() -> None:
    assert normalize_arxiv("https://arxiv.org/abs/hep-th/9901001v2") == "hep-th/9901001"
    assert normalize_arxiv("https://arxiv.org/pdf/2201.12220v3.pdf") == "2201.12220"


def test_identity_conflict_is_visible_and_cannot_be_selected() -> None:
    bundle = _bundle()
    semantic_item = bundle["providers"][2]["requests"][0]["response"]["data"][0]
    semantic_item["title"] = "Unrelated Quantum Chemistry"
    observations = normalize_provider_bundle(validate_provider_bundle(bundle))
    result = fuse_seed_candidates(build_topic_contract(TOPIC), observations, max_selected=12)
    conflicted = next(row for row in result["candidates"] if row["paper_id"] == "doi:10.5555/neural-ot")
    assert conflicted["identity_status"] == "conflict"
    assert conflicted["disposition"] == "BLOCKED_IDENTITY_CONFLICT"
    assert "title_mismatch" in conflicted["identity_conflict_reasons"]


def test_bundle_rejects_evaluator_labels_and_preserves_unavailable() -> None:
    value = _bundle()
    value["must_find"] = ["doi:10.5555/neural-ot"]
    with pytest.raises(MissionStateError, match="fields are not exact"):
        validate_provider_bundle(value)

    value = _bundle()
    value["providers"][2] = {
        "provider": "semantic_scholar",
        "status": "not_available",
        "requests": [_request("semantic_scholar", None, status="not_available")],
    }
    observations = normalize_provider_bundle(validate_provider_bundle(value))
    assert observations["provider_statuses"][2] == {
        "provider": "semantic_scholar",
        "status": "not_available",
    }
    assert observations["route_statuses"][2]["status"] == "not_available"

    value = _bundle()
    value["providers"][0]["status"] = "empty"
    with pytest.raises(MissionStateError, match="differs from its request rows"):
        validate_provider_bundle(value)

    value = _bundle()
    value["providers"][0]["requests"][0]["status"] = "capped"
    with pytest.raises(MissionStateError, match="capped state is inconsistent"):
        validate_provider_bundle(value)


def test_repeated_provider_identity_conflict_fails_closed() -> None:
    value = _bundle()
    duplicate = copy.deepcopy(value["providers"][1]["requests"][0])
    duplicate["route_id"] = "survey_route"
    duplicate["purpose"] = "survey_or_tutorial"
    duplicate["response"]["results"][0]["display_name"] = "Conflicting Title"
    value["providers"][1]["requests"].append(duplicate)
    observations = validate_provider_bundle(value)
    with pytest.raises(MissionStateError, match="conflicting identity metadata"):
        normalize_provider_bundle(observations)


def test_repeated_provider_record_merges_richer_optional_evidence() -> None:
    value = _bundle()
    first = value["providers"][1]["requests"][0]
    first["response"]["results"][0]["concepts"] = [{"display_name": "Transport"}]
    duplicate = copy.deepcopy(first)
    duplicate["route_id"] = "survey_route"
    duplicate["purpose"] = "survey_or_tutorial"
    duplicate["response"]["results"][0]["abstract_inverted_index"] = {
        "neural": [0], "optimal": [1], "transport": [2], "survey": [3]
    }
    duplicate["response"]["results"][0]["concepts"] = [{"display_name": "Neural methods"}]
    value["providers"][1]["requests"].append(duplicate)
    value["providers"][1]["requests"].sort(key=lambda row: row["route_id"])

    observations = normalize_provider_bundle(validate_provider_bundle(value))
    record = next(row for row in observations["records"] if row["provider_id"] == "W1")
    assert record["abstract"] == "neural optimal transport survey"
    assert record["concepts"] == ["Neural methods", "Transport"]
    assert record["route_purposes"] == ["foundational_or_high_citation", "survey_or_tutorial"]


def test_campaign_replays_and_detects_tampering(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    campaign = tmp_path / "campaign"
    report = run_seed_paper_campaign(
        topic=TOPIC,
        output_dir=campaign,
        observation_bundle=bundle_path,
    )
    assert report["status"] == "seed_candidates_selected"
    assert run_seed_paper_campaign(topic=TOPIC, output_dir=campaign, resume=True) == report
    assert validate_seed_paper_campaign(campaign, expected_topic=TOPIC)["report"] == report

    with pytest.raises(MissionStateError, match="selection cap differ"):
        run_seed_paper_campaign(topic=TOPIC, output_dir=campaign, resume=True, max_selected=2)

    recorded = json.loads((campaign / "seed_report.json").read_text())
    recorded["selected_count"] = 99
    (campaign / "seed_report.json").write_text(json.dumps(recorded), encoding="utf-8")
    with pytest.raises(MissionStateError, match="differs from replay"):
        validate_seed_paper_campaign(campaign, expected_topic=TOPIC)


def test_campaign_requires_confirmation_for_live_provider_calls(tmp_path: Path) -> None:
    with pytest.raises(MissionStateError, match="explicit confirmation"):
        run_seed_paper_campaign(topic=TOPIC, output_dir=tmp_path / "campaign")


def test_abstract_concept_evidence_and_explicit_exclusion_are_separate() -> None:
    value = _bundle()
    openalex = value["providers"][1]["requests"][0]["response"]["results"]
    openalex[0]["display_name"] = "A learned transport map"
    value["providers"][0]["requests"][0]["response"]["message"]["items"][0]["title"] = ["A learned transport map"]
    value["providers"][2]["requests"][0]["response"]["data"][0]["title"] = "A learned transport map"
    openalex[0]["abstract_inverted_index"] = {
        "neural": [0], "optimal": [1], "transport": [2], "method": [3]
    }
    openalex[0]["concepts"] = [{"display_name": "Optimal transport"}]
    observations = normalize_provider_bundle(validate_provider_bundle(value))
    result = fuse_seed_candidates(build_topic_contract(TOPIC), observations, max_selected=12)
    selected = next(row for row in result["candidates"] if row["paper_id"] == "doi:10.5555/neural-ot")
    assert "abstract" in selected["topic_evidence"]["evidence_sources"]
    assert "concepts" in selected["topic_evidence"]["evidence_sources"]

    excluded_contract = build_topic_contract(TOPIC, exclusions=["learned transport map"])
    value["topic_contract_sha256"] = topic_contract_sha256(excluded_contract)
    excluded_observations = normalize_provider_bundle(validate_provider_bundle(value))
    excluded = fuse_seed_candidates(excluded_contract, excluded_observations, max_selected=12)
    blocked = next(row for row in excluded["candidates"] if row["paper_id"] == "doi:10.5555/neural-ot")
    assert blocked["disposition"] == "NOT_SELECTED_TOPIC_MISMATCH"
    assert blocked["topic_evidence"]["matched_exclusions"] == ["learned transport map"]


def test_routes_cover_roles_facets_aliases_and_fail_when_cap_is_impossible() -> None:
    contract = build_topic_contract(
        "Learning for recommendations",
        required_facets=["learning", "recommendations"],
        aliases=["recommender systems", "personalization"],
    )
    plan = plan_discovery_routes(contract)
    assert plan["route_count"] == 10
    assert {row["purpose"] for row in plan["routes"]} >= {
        "required_facet", "alias_expansion", "survey_or_tutorial",
        "foundational_or_high_citation", "direct_method", "recent_follow_up",
    }
    assert plan["route_count"] <= MAX_ROUTES
    broad = plan_discovery_routes(build_topic_contract(
        "A broad topic",
        required_facets=[f"facet {index}" for index in range(8)],
    ))
    assert broad["route_count"] == MAX_ROUTES


def test_venue_registry_enrichment_requires_same_registry_on_replay(tmp_path: Path) -> None:
    registry_value = {
        "schema_version": VENUE_METRICS_SCHEMA,
        "registry_id": "fixture-2026",
        "metric_name": VENUE_METRIC_NAME,
        "registry_source": {
            "reference": "fixture registry",
            "accessed_at": "2026-07-22T00:00:00+00:00",
        },
        "venues": [{
            "venue_key": "https://openalex.org/S1",
            "display_name": "Journal",
            "status": "available",
            "metric_value": 9.5,
            "metric_year": 2025,
            "source": {
                "reference": "fixture metric",
                "accessed_at": "2026-07-22T00:00:00+00:00",
            },
        }],
        "paper_venues": [],
    }
    value = _bundle()
    value["providers"][1]["requests"][0]["response"]["results"][0]["primary_location"]["source"]["id"] = "https://openalex.org/S1"
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(value), encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_bytes(json.dumps(registry_value, sort_keys=True, separators=(",", ":")).encode())
    campaign = tmp_path / "campaign"
    report = run_seed_paper_campaign(
        topic=TOPIC,
        output_dir=campaign,
        observation_bundle=bundle_path,
        venue_metrics_registry=registry,
    )
    selected = next(row for row in report["candidates"] if row["disposition"] == "SELECTED_SEED_CANDIDATE")
    assert selected["venue_metric"]["metric_value"] == 9.5
    assert validate_seed_paper_campaign(
        campaign, venue_metrics_registry=registry
    )["report"] == report
    with pytest.raises(MissionStateError, match="requires the original registry"):
        validate_seed_paper_campaign(campaign)
    changed = dict(registry_value)
    changed["registry_id"] = "fixture-changed"
    changed_path = tmp_path / "changed.json"
    changed_path.write_bytes(json.dumps(changed, sort_keys=True, separators=(",", ":")).encode())
    with pytest.raises(MissionStateError, match="digest differs"):
        validate_seed_paper_campaign(campaign, venue_metrics_registry=changed_path)


def test_live_collector_uses_exact_three_provider_hosts_and_budgets() -> None:
    observed_urls: list[str] = []

    class Response:
        status = 200

        def __init__(self, url: str):
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self):
            return self.url

        def read(self, _limit: int):
            if "openalex.org" in self.url:
                value = {"meta": {"count": 0}, "results": []}
            elif "crossref.org" in self.url:
                value = {"message": {"total-results": 0, "items": []}}
            else:
                value = {"total": 0, "data": []}
            return json.dumps(value).encode()

    def opener(url: str, *, timeout: int):
        assert timeout == 30
        observed_urls.append(url)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=opener, max_records_per_response=5
    )
    assert [row["provider"] for row in bundle["providers"]] == [
        "crossref", "openalex", "semantic_scholar",
    ]
    assert {urllib.parse.urlparse(url).hostname for url in observed_urls} == {
        "api.crossref.org", "api.openalex.org", "api.semanticscholar.org",
    }
    assert len(observed_urls) == 18
