from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, discovery_budget
from research_assistant.survey.bootstrap import validate_bootstrap_outcome
from research_assistant.survey.topic_seed_discovery import (
    BudgetTracker,
    CandidateIdentityResolver,
    GENERIC_TOPIC_PROFILE,
    _fetch_openalex_topic,
    _topic_query_layers,
    rank_candidates,
)
from research_assistant.survey.topic_seed_strategy import load_strategy, validate_strategy
from research_assistant.survey.topic_seed_discovery import (
    OpenAlexPriorityBootstrapCapability,
    OpenAlexTopicBootstrapCapability,
)
from research_assistant.survey.venue_metrics import load_registry, validate_registry
from research_assistant.survey.venue_metrics import unavailable_registry


def _registry() -> dict:
    source = {"reference": "https://example.test/jcr-2025", "accessed_at": "2026-07-21T00:00:00+00:00"}
    return {
        "schema_version": "ra-survey-venue-metrics-registry-v1",
        "registry_id": "fixture-jcr-2025",
        "metric_name": "journal_impact_factor",
        "registry_source": source,
        "venues": [
            {
                "venue_key": "V1",
                "display_name": "Journal One",
                "status": "available",
                "metric_value": 20.0,
                "metric_year": 2025,
                "source": source,
            },
            {
                "venue_key": "V2",
                "display_name": "Journal Two",
                "status": "not_available",
                "metric_value": None,
                "metric_year": None,
                "source": source,
            },
        ],
        "paper_venues": [{"paper_key": "openalex:w1", "venue_key": "V1"}],
    }


def _work(identifier: str, title: str, citations: int, venue: str) -> dict:
    return {
        "id": f"https://openalex.org/{identifier}",
        "display_name": title,
        "authorships": [{"author": {"display_name": "Author"}}],
        "publication_year": 2024,
        "doi": None,
        "cited_by_count": citations,
        "ids": {"openalex": f"https://openalex.org/{identifier}"},
        "primary_location": {"source": {"id": f"https://openalex.org/{venue}", "display_name": venue}},
    }


def _arxiv_work(identifier: str, title: str, citations: int, venue: str) -> dict:
    row = _work(identifier, title, citations, venue)
    row["doi"] = "https://doi.org/10.1000/example"
    row["ids"]["arxiv"] = "https://arxiv.org/abs/2401.00001"
    return row


def test_registry_requires_explicit_metric_and_never_uses_zero_for_missing() -> None:
    registry = validate_registry(_registry())
    assert registry["venues"][1]["metric_value"] is None
    assert registry["venues"][1]["status"] == "not_available"


def test_registry_rejects_available_metric_without_year() -> None:
    value = _registry()
    value["venues"][0]["metric_year"] = None
    with pytest.raises(MissionStateError, match="metric_year"):
        validate_registry(value)


def test_registry_digest_requires_canonical_bytes(tmp_path: Path) -> None:
    path = tmp_path / "venue_metrics.json"
    path.write_bytes(json.dumps(_registry()).encode())
    with pytest.raises(MissionStateError, match="canonical"):
        load_registry(path)
    path.write_bytes(canonical_json_bytes(_registry()))
    loaded, digest = load_registry(path)
    assert loaded["registry_id"] == "fixture-jcr-2025"
    assert len(digest) == 64


def test_registry_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(canonical_json_bytes(_registry()))
    link = tmp_path / "registry.json"
    link.symlink_to(target)
    with pytest.raises(MissionStateError, match="symlink"):
        load_registry(link)


def test_ranking_preserves_citation_and_venue_priority_views() -> None:
    result = rank_candidates(
        topic="reinforcement learning recommender",
        works=[
            _work("W1", "Reinforcement learning recommender systems", 5, "V1"),
            _work("W2", "Reinforcement learning recommender systems", 500, "V2"),
        ],
        registry=_registry(),
        metadata_accessed_at="2026-07-21T00:00:00+00:00",
    )
    by_key = {row["paper_key"]: row for row in result["candidates"]}
    assert by_key["openalex:w1"]["venue_metric"]["metric_value"] == 20.0
    assert by_key["openalex:w2"]["venue_metric"]["metric_value"] is None
    assert by_key["openalex:w2"]["citation_priority_rank"] == 1
    assert by_key["openalex:w1"]["venue_priority_rank"] == 1
    assert result["selected_keys"]


def test_empty_venue_registry_is_explicit_optional_enrichment() -> None:
    registry = unavailable_registry()
    assert registry["registry_id"] == "not_available"
    result = rank_candidates(
        topic="reinforcement learning recommender",
        works=[_work("W1", "Reinforcement learning recommender systems", 5, "V1")],
        registry=registry,
        metadata_accessed_at="2026-07-21T00:00:00+00:00",
    )
    row = result["candidates"][0]
    assert row["venue_metric"]["status"] == "not_available"
    assert row["citation_priority_rank"] == 1


def test_ranking_preserves_arxiv_alias_and_prefers_sourceable_tie() -> None:
    result = rank_candidates(
        topic="reinforcement learning recommender",
        works=[
            _work("W1", "Reinforcement learning recommender", 1000, "V1"),
            _arxiv_work("W2", "Reinforcement learning recommender", 10, "V1"),
        ],
        registry=unavailable_registry(),
        metadata_accessed_at="2026-07-23T00:00:00+00:00",
        selected_seed_cap=1,
    )
    selected = next(
        row for row in result["candidates"] if row["paper_key"] == result["selected_keys"][0]
    )
    assert selected["paper_key"] == "openalex:w2"
    assert "doi:10.1000/example" in selected["identifier_evidence"]
    assert "arxiv:2401.00001" in selected["identifier_evidence"]
    assert selected["source_availability_status"] == "arxiv_structured_source_candidate"


def test_priority_capability_returns_hash_bound_metadata_only_selection(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(canonical_json_bytes(_registry()))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit: int = -1) -> bytes:
            return canonical_json_bytes({
                "meta": {"count": 2},
                "results": [
                    _work("W1", "Reinforcement learning recommender systems", 5, "V1"),
                    _work("W2", "Reinforcement learning recommender systems", 500, "V2"),
                ],
            })

    def opener(_url: str, *, timeout: int):
        assert timeout == 30
        return Response()

    capability = OpenAlexPriorityBootstrapCapability(registry_path, opener=opener)
    result = capability.run({
        "normalized_topic": {"display": "reinforcement learning recommender"},
        "discovery_budget": {
            "providers": ["openalex"],
            "allowed_domains": ["api.openalex.org"],
            "max_metadata_requests": 24,
            "max_records_per_metadata_response": 25,
            "max_total_metadata_records": 600,
            "max_unique_candidates": 300,
            "max_bytes_per_metadata_response": 2_000_000,
            "max_total_metadata_bytes": 48_000_000,
            "max_total_source_bytes": 500 * 1024 * 1024,
            "max_pages_per_query": 2,
            "max_selected_seeds": 12,
        },
    })
    assert result["outcome"] == "selected"
    assert {row["paper_key"] for row in result["selected_candidates"]} == {
        "openalex:w1",
        "openalex:w2",
    }
    w1 = next(row for row in result["selected_candidates"] if row["paper_key"] == "openalex:w1")
    w2 = next(row for row in result["selected_candidates"] if row["paper_key"] == "openalex:w2")
    assert w1["descriptive"]["venue_metric"]["metric_value"] == 20.0
    assert w2["descriptive"]["venue_metric"]["metric_value"] is None
    assert w2["descriptive"]["citation_priority_rank"] == 1
    assert w1["descriptive"]["venue_priority_rank"] == 1
    assert result["descriptive"]["venue_registry_sha256"]
    assert [row["paper_key"] for row in result["selected_candidates"]] == sorted(
        row["paper_key"] for row in result["selected_candidates"]
    )
    assert OpenAlexTopicBootstrapCapability.name == "openalex_topic_seed_bootstrap"
    assert OpenAlexPriorityBootstrapCapability is OpenAlexTopicBootstrapCapability


def test_priority_capability_runs_without_venue_registry() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit: int = -1) -> bytes:
            return canonical_json_bytes({
                "meta": {"count": 1},
                "results": [_work("W1", "Reinforcement learning recommender systems", 5, "V1")],
            })

    capability = OpenAlexPriorityBootstrapCapability(opener=lambda _url, *, timeout: Response())
    result = capability.run({
        "normalized_topic": {"display": "reinforcement learning recommender"},
        "discovery_budget": {
            "providers": ["openalex"],
            "allowed_domains": ["api.openalex.org"],
            "max_metadata_requests": 24,
            "max_records_per_metadata_response": 25,
            "max_total_metadata_records": 600,
            "max_unique_candidates": 300,
            "max_bytes_per_metadata_response": 2_000_000,
            "max_total_metadata_bytes": 48_000_000,
            "max_total_source_bytes": 500 * 1024 * 1024,
            "max_pages_per_query": 2,
            "max_selected_seeds": 12,
        },
    })
    assert result["outcome"] == "selected"
    assert result["descriptive"]["venue_registry_status"] == "not_available"
    assert result["descriptive"]["venue_registry_sha256"] is None


def test_generic_topic_capability_selects_from_generic_profile() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit: int = -1) -> bytes:
            return canonical_json_bytes({
                "meta": {"count": 1},
                "results": [_work("W1", "Neural Optimal Transport", 12, "V1")],
            })

    capability = OpenAlexTopicBootstrapCapability(opener=lambda _url, *, timeout: Response())
    result = capability.run({
        "normalized_topic": {"display": "Neural Optimal Transport"},
        "discovery_budget": {
            "providers": ["openalex"],
            "allowed_domains": ["api.openalex.org"],
            "max_metadata_requests": 24,
            "max_records_per_metadata_response": 25,
            "max_total_metadata_records": 600,
            "max_unique_candidates": 300,
            "max_bytes_per_metadata_response": 2_000_000,
            "max_total_metadata_bytes": 48_000_000,
            "max_total_source_bytes": 500 * 1024 * 1024,
            "max_pages_per_query": 2,
            "max_selected_seeds": 12,
        },
    })
    assert result["outcome"] == "selected"
    assert result["selected_candidates"][0]["descriptive"]["topic_profile"] == "generic_topic"
    assert result["descriptive"]["strategy_id"] == "generic_topic"
    assert result["descriptive"]["candidate_status"] == "metadata_nomination"
    assert result["descriptive"]["generic_topic_centrality_status"] == "not_validated"
    assert result["selected_candidates"][0]["descriptive"]["concept_groups"] == {
        "topic": ["neural", "optimal", "transport"]
    }


def test_capability_version_binds_generic_route_plan() -> None:
    version = OpenAlexTopicBootstrapCapability().version
    assert version.startswith("7+registry.not_available+generic.")
    route_digest = version.rsplit("+routes.", 1)[1]
    assert len(route_digest) == 12
    assert set(route_digest) <= set("0123456789abcdef")


def test_openalex_topic_fetch_binds_page_to_request_url() -> None:
    class Response:
        status = 200

        def __init__(self, url: str):
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self) -> str:
            return self.url

        def read(self, _limit: int = -1) -> bytes:
            return canonical_json_bytes({
                "meta": {"count": 26},
                "results": [{
                    "id": "https://openalex.org/W1",
                    "display_name": "Reinforcement learning recommender systems",
                    "authorships": [],
                    "publication_year": 2024,
                    "doi": None,
                    "cited_by_count": 1,
                    "ids": {},
                    "primary_location": {"source": None},
                }],
            })

    seen: list[str] = []

    def opener(url: str, *, timeout: int):
        assert timeout == 30
        seen.append(url)
        return Response(url)

    works, capped, url, provider_count, _ = _fetch_openalex_topic(
        "reinforcement learning recommender",
        opener=opener,
        query_layer={"kind": "fixture", "search": "reinforcement learning recommender"},
        page=2,
    )
    assert len(works) == 1
    assert capped is True
    assert provider_count == 26
    assert "page=2" in url
    assert seen == [url]


def test_priority_capability_stops_at_aggregate_record_budget() -> None:
    class Response:
        status = 200

        def __init__(self, url: str):
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self) -> str:
            return self.url

        def read(self, _limit: int = -1) -> bytes:
            query = dict(
                urllib.parse.parse_qsl(urllib.parse.urlparse(self.url).query)
            )
            result_cap = int(query["per-page"])
            offset = 0 if result_cap == 2 else 2
            return canonical_json_bytes({
                "meta": {"count": 100},
                "results": [
                    _work(
                        f"W{offset + index + 1}",
                        "Reinforcement learning recommender systems",
                        100 - offset - index,
                        "V1",
                    )
                    for index in range(result_cap)
                ],
            })

    seen: list[str] = []

    def opener(url: str, *, timeout: int):
        assert timeout == 30
        seen.append(url)
        return Response(url)

    budget = discovery_budget(
        Path("/tmp/topic-seed-record-budget"),
        providers=["openalex"],
        allowed_domains=["api.openalex.org"],
        aggregate_metadata=True,
    )
    budget.update({
        "max_metadata_records": 2,
        "max_records_per_metadata_response": 2,
        "max_total_metadata_records": 3,
        "max_unique_candidates": 3,
    })
    result = OpenAlexTopicBootstrapCapability(opener=opener).run({
        "normalized_topic": {"display": "reinforcement learning recommender"},
        "discovery_budget": budget,
    })

    assert result["outcome"] == "selected"
    assert result["descriptive"]["budget_consumption"]["provider_rows"] == 3
    assert len(seen) == 2
    assert "per-page=2" in seen[0]
    assert "per-page=1" in seen[1]
    assert any(
        row["status"] == "not_dispatched_due_to_budget"
        for row in result["descriptive"]["query_layers"]
    )


def test_rl_finance_regression_strategy_requires_its_declared_title_groups() -> None:
    registry = _registry()
    works = [
        {
            **_work("W1", "A Survey of Machine Learning Methods", 1000, "V1"),
            "_topic_query_layers": ["rl_recommender"],
            "_fully_observed_query_layers": ["rl_recommender"],
        },
        {
            **_work("W2", "Reinforcement Learning based Recommender Systems", 10, "V1"),
            "_topic_query_layers": ["rl_recommender"],
            "_fully_observed_query_layers": ["rl_recommender"],
        },
        {
            **_work("W3", "Reinforcement Learning based Recommender Systems", 5000, "V1"),
            "_topic_query_layers": ["rl_recommender"],
            "_fully_observed_query_layers": [],
        },
    ]
    result = rank_candidates(
        topic="Reinforcement learning for recommender systems in financial products and credit cards",
        works=works,
        registry=registry,
        metadata_accessed_at="2026-07-21T00:00:00+00:00",
        query_strategy=load_strategy(
            Path("tests/fixtures/topic_seed_strategies/rl_financial_recommender.json")
        ),
    )
    rows = {row["paper_key"]: row for row in result["candidates"]}
    assert "openalex:w1" not in rows
    assert rows["openalex:w2"]["eligibility_reason"] == "required_strategy_title_groups"
    assert rows["openalex:w3"]["eligibility_reason"] == "required_strategy_title_groups"
    assert result["selected_keys"] == ["openalex:w3", "openalex:w2"]


def test_public_query_layers_do_not_auto_select_a_domain_fixture() -> None:
    topic = "Reinforcement learning for recommender systems in financial products and credit cards"
    profile, layers = _topic_query_layers(topic)
    assert profile == GENERIC_TOPIC_PROFILE
    assert [row["kind"] for row in layers] == [
        "exact_high_citation", "exact_recent", "survey_route",
        "foundational_route", "direct_method_route", "required_facet_pair_1",
        "required_facet_pair_2", "required_facet_pair_3", "required_facet_pair_4",
        "required_facet_pair_5", "required_facet_pair_6", "required_facet_1",
    ]
    assert layers[0]["filter"] == f"title.search:{topic}"
    assert layers[1]["filter"] == f"title.search:{topic}"
    assert all(
        row["filter"].startswith(("default.search:", "title.search:"))
        for row in layers[2:]
    )
    assert layers[5]["filter"] == "title.search:credit cards financial products"
    assert {row["purpose"] for row in layers} == {
        "foundational_or_high_citation", "recent_follow_up", "direct_method",
        "required_facet", "required_facet_pair", "survey_or_tutorial",
    }


def test_generic_topic_query_layers_are_profile_driven() -> None:
    profile, layers = _topic_query_layers("Neural Optimal Transport")
    assert profile == GENERIC_TOPIC_PROFILE
    assert [row["kind"] for row in layers] == [
        "exact_high_citation", "exact_recent", "survey_route",
        "foundational_route", "direct_method_route", "required_facet_1",
    ]
    assert layers[0]["filter"] == "title.search:Neural Optimal Transport"
    assert layers[2]["filter"] == "default.search:Neural Optimal Transport survey"


@pytest.mark.parametrize(
    ("topic", "central_title", "off_topic_title"),
    [
        ("Neural Optimal Transport", "Neural Optimal Transport for Maps", "Attention Is All You Need"),
        ("Particle Filtering Nonlinear State Space Models", "Particle Filtering for Nonlinear State Space Models", "Deep Residual Learning for Image Recognition"),
        ("Federated Learning Privacy", "Privacy in Federated Learning", "ImageNet Classification with Deep Convolutional Networks"),
    ],
)
def test_generic_nomination_is_topic_driven_and_rejects_high_citation_off_topic_controls(
    topic: str,
    central_title: str,
    off_topic_title: str,
) -> None:
    result = rank_candidates(
        topic=topic,
        works=[
            _work("W1", central_title, 10, "V1"),
            _work("W2", off_topic_title, 100_000, "V2"),
        ],
        registry=unavailable_registry(),
        metadata_accessed_at="2026-07-22T00:00:00+00:00",
        query_strategy=load_strategy(),
    )
    assert result["selected_keys"] == ["openalex:w1"]
    assert {row["paper_key"] for row in result["candidates"]} == {"openalex:w1"}


def test_aggregate_budget_tracks_exact_boundary_and_rejects_overflow(tmp_path: Path) -> None:
    budget = discovery_budget(
        tmp_path,
        providers=["openalex"],
        allowed_domains=["api.openalex.org"],
        aggregate_metadata=True,
    )
    tracker = BudgetTracker(budget)
    for _ in range(budget["max_metadata_requests"]):
        tracker.before_request()
        tracker.consume(returned_count=25, response_bytes=100)
    assert tracker.snapshot() == {
        "metadata_requests": 24,
        "provider_rows": 600,
        "response_bytes": 2400,
    }
    with pytest.raises(MissionStateError, match="request budget"):
        tracker.before_request()


def test_budget_rejects_aggregate_record_and_byte_overflow(tmp_path: Path) -> None:
    budget = discovery_budget(
        tmp_path,
        providers=["openalex"],
        allowed_domains=["api.openalex.org"],
        aggregate_metadata=True,
    )
    tracker = BudgetTracker(budget)
    tracker.before_request()
    with pytest.raises(MissionStateError, match="record cap"):
        tracker.consume(returned_count=26, response_bytes=1)
    tracker = BudgetTracker(budget)
    tracker.before_request()
    with pytest.raises(MissionStateError, match="byte cap"):
        tracker.consume(returned_count=1, response_bytes=2_000_001)


def test_aggregate_budget_binds_candidate_and_source_byte_caps(tmp_path: Path) -> None:
    budget = discovery_budget(
        tmp_path,
        providers=["openalex"],
        allowed_domains=["api.openalex.org"],
        aggregate_metadata=True,
    )
    assert budget["max_unique_candidates"] == 300
    assert budget["max_total_source_bytes"] == 500 * 1024 * 1024


def test_priority_capability_caps_unique_candidate_frontier(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(canonical_json_bytes(_registry()))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit: int = -1) -> bytes:
            return canonical_json_bytes({
                "meta": {"count": 2},
                "results": [
                    _work("W1", "Reinforcement learning recommender systems", 5, "V1"),
                    _work("W2", "Reinforcement learning recommender systems", 4, "V2"),
                ],
            })

    capability = OpenAlexPriorityBootstrapCapability(
        registry_path,
        opener=lambda _url, *, timeout: Response(),
    )
    budget = discovery_budget(
        tmp_path,
        providers=["openalex"],
        allowed_domains=["api.openalex.org"],
        aggregate_metadata=True,
    )
    budget["max_unique_candidates"] = 1
    result = capability.run({
        "normalized_topic": {"display": "reinforcement learning recommender"},
        "discovery_budget": budget,
    })
    assert result["outcome"] == "selected"
    assert result["observed_count"] == 2
    assert len(result["candidates"]) == 1
    assert result["descriptive"]["candidate_frontier_capped"] is True
    assert result["descriptive"]["candidate_frontier_cap"] == 1


def test_identity_resolver_merges_doi_duplicates_and_retains_provenance() -> None:
    first = {**_work("W1", "RL Recommender", 10, "V1"), "doi": "https://doi.org/10.1000/test"}
    second = {**_work("W2", "RL Recommender", 20, "V1"), "doi": "doi:10.1000/test"}
    first["_topic_query_layers"] = ["a"]
    second["_topic_query_layers"] = ["b"]
    merged, duplicates, conflicts = CandidateIdentityResolver().resolve([first, second])
    assert len(merged) == 1
    assert merged[0]["_topic_query_layers"] == ["a", "b"]
    assert len(duplicates) == 1
    assert conflicts == []


def test_strategy_validation_rejects_unknown_fields() -> None:
    with pytest.raises(MissionStateError, match="fields are not exact"):
        validate_strategy({"profile_id": "x"})


def test_strategy_validation_rejects_non_lowercase_group_identifiers() -> None:
    value = json.loads(
        Path("src/research_assistant/survey/strategies/generic_topic.json").read_text()
    )
    value["required_topic_groups"] = {"Topic": ["{topic}"]}
    with pytest.raises(MissionStateError, match="lowercase identifiers"):
        validate_strategy(value)


def test_selected_outcome_allows_paper_key_order_independent_of_seed_display_order() -> None:
    rows = [
        {
            "paper_key": "openalex:w1",
            "display": "doi:10.1000/z",
            "identifier_evidence": ["openalex:w1"],
            "title_evidence": ["First"],
            "descriptive": {},
        },
        {
            "paper_key": "openalex:w2",
            "display": "doi:10.1000/a",
            "identifier_evidence": ["openalex:w2"],
            "title_evidence": ["Second"],
            "descriptive": {},
        },
    ]
    value = validate_bootstrap_outcome({
        "schema_version": "ra-survey-topic-bootstrap-outcome-v1",
        "outcome": "selected",
        "selected_candidates": rows,
        "candidates": rows,
        "ambiguities": [],
        "reason": None,
        "cap": None,
        "observed_count": 2,
        "descriptive": {},
    })
    assert [row["paper_key"] for row in value["selected_candidates"]] == ["openalex:w1", "openalex:w2"]
