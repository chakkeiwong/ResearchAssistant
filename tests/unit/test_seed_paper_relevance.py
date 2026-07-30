from __future__ import annotations

import copy

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.seed_papers import build_seed_campaign, fuse_seed_candidates
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


TOPIC = "Neural DSGE solution methods for differentiable estimation"
MALIAR_DOI = "10.1016/j.jmoneco.2021.07.004"


def _record(
    provider_id: str,
    title: str,
    *,
    doi: str | None = None,
    abstract: str | None = None,
    citations: int = 0,
    route_purpose: str = "direct_method",
    year: int = 2021,
) -> dict:
    return {
        "provider": "crossref",
        "provider_id": provider_id,
        "title": title,
        "abstract": abstract,
        "concepts": [],
        "authors": ["Test Author"],
        "year": year,
        "publication_date": f"{year}-01-01",
        "identifiers": {
            "arxiv": None,
            "crossref": doi,
            "doi": doi,
            "openalex": None,
            "semantic_scholar": None,
        },
        "citation_count": citations,
        "venue": "Test Journal",
        "venue_key": None,
        "source_url": f"https://example.test/{provider_id}",
        "retraction_status": "not_checked",
        "route_ids": ["broad_topic_high_citation"],
        "route_purposes": [route_purpose],
        "provider_best_rank": 1,
    }


def _observations(contract: dict, records: list[dict]) -> dict:
    return {
        "schema_version": "ra-survey-seed-provider-observations-v2",
        "topic_contract_sha256": topic_contract_sha256(contract),
        "seed_authorities": ["doi:" + MALIAR_DOI],
        "accessed_at": "2026-07-29T00:00:00+00:00",
        "provider_statuses": [],
        "route_statuses": [],
        "records": records,
        "budget_consumption": {"metadata_requests": 1, "provider_rows": len(records), "unique_provider_records": len(records)},
        "limitations": [],
        "benchmark_labels_consumed": False,
    }


def _contract() -> dict:
    return build_topic_contract(
        TOPIC,
        required_facets=["neural DSGE solution methods", "differentiable estimation"],
        aliases=["deep learning for solving dynamic economic models"],
    )


def test_exact_seed_authority_precedes_topic_heuristics() -> None:
    contract = _contract()
    records = [
        _record(
            MALIAR_DOI,
            "Deep learning for solving dynamic economic models.",
            doi=MALIAR_DOI,
        ),
        _record(
            "noise",
            "Fractional Brownian Motions, Fractional Noises and Applications",
            abstract="A highly cited dynamic economic model reference list from 2021.",
            citations=8000,
        ),
    ]
    result = fuse_seed_candidates(
        contract,
        _observations(contract, records),
        max_selected=12,
        seeds=["doi:" + MALIAR_DOI],
    )
    assert result["selected_paper_ids"][0] == "doi:" + MALIAR_DOI
    seed = next(row for row in result["candidates"] if row["paper_id"] == "doi:" + MALIAR_DOI)
    noise = next(row for row in result["candidates"] if row["paper_id"] == "crossref:noise")
    assert seed["disposition"] == "SEED_AUTHORITY"
    assert noise["disposition"] != "SELECTED_SEED_CANDIDATE"


def test_year_and_generic_overlap_do_not_cover_compound_facet() -> None:
    contract = build_topic_contract(
        TOPIC,
        required_facets=["Maliar Maliar Winant 2021"],
    )
    records = [_record("noise", "Unrelated 2021 Method", abstract="dynamic economic model")]
    result = fuse_seed_candidates(contract, _observations(contract, records), max_selected=12, seeds=[])
    row = result["candidates"][0]
    assert row["topic_evidence"]["covered_facets"] == []
    assert row["disposition"] in {"NOT_SELECTED_TOPIC_MISMATCH", "REVIEW_REQUIRED_WEAK_MATCH"}


def test_route_purpose_does_not_create_semantic_role() -> None:
    contract = _contract()
    record = _record(
        "background",
        "Neural DSGE Notes",
        abstract=None,
        route_purpose="survey_or_tutorial",
    )
    result = fuse_seed_candidates(contract, _observations(contract, [record]), max_selected=12, seeds=[])
    row = result["candidates"][0]
    assert "SURVEY_OR_TUTORIAL" not in row["role_hypotheses"]


def test_selection_cap_is_not_a_fill_target() -> None:
    contract = _contract()
    records = [
        _record(
            "kase",
            "Estimating Nonlinear Heterogeneous Agents Models with Neural Networks",
            abstract="A neural solution and estimation method for nonlinear economic models.",
            doi="10.21033/wp-2022-26",
        ),
        _record(
            "weak",
            "Interpretation of Ill-Conditioned Equations",
            abstract="Parameter estimation and solution.",
            citations=50000,
        ),
    ]
    result = fuse_seed_candidates(contract, _observations(contract, records), max_selected=12, seeds=[])
    assert len(result["selected_paper_ids"]) < 12
    assert "crossref:weak" not in result["selected_paper_ids"]


def test_contaminated_abstract_cannot_supply_relevance() -> None:
    contract = _contract()
    contaminated = "References Cited By Cross Ref Google Scholar " + "neural DSGE solution estimation " * 600
    record = _record("contaminated", "Fractional Brownian Motion", abstract=contaminated, citations=9000)
    result = fuse_seed_candidates(contract, _observations(contract, [record]), max_selected=12, seeds=[])
    row = result["candidates"][0]
    assert row["abstract_quality"]["usable_for_relevance"] is False
    assert row["disposition"] != "SELECTED_SEED_CANDIDATE"


def test_citations_cannot_upgrade_weak_relevance() -> None:
    contract = _contract()
    strong = _record(
        "strong",
        "Sequential solution for DSGE models with deep neural networks",
        abstract="A neural DSGE solution method.",
        citations=1,
    )
    weak = _record(
        "weak",
        "General Parameter Estimation",
        abstract="A solution method.",
        citations=1_000_000,
    )
    result = fuse_seed_candidates(contract, _observations(contract, [weak, strong]), max_selected=1, seeds=[])
    assert result["selected_paper_ids"] == ["crossref:strong"]


def test_exact_title_authority_resolves_only_when_unique() -> None:
    contract = _contract()
    title = "Deep learning for solving dynamic economic models"
    unique = fuse_seed_candidates(
        contract,
        _observations(contract, [_record("one", title, doi=MALIAR_DOI)]),
        max_selected=12,
        seeds=[f"title:{title}"],
    )
    assert unique["seed_authority_ids"] == ["doi:" + MALIAR_DOI]
    assert unique["unresolved_seed_authorities"] == []

    ambiguous = fuse_seed_candidates(
        contract,
        _observations(contract, [
            _record("one", title, doi=MALIAR_DOI, year=2021),
            _record("two", title, doi="10.5555/different", year=2024),
        ]),
        max_selected=12,
        seeds=[f"title:{title}"],
    )
    assert ambiguous["seed_authority_ids"] == []
    assert ambiguous["unresolved_seed_authorities"] == [{
        "seed": "title:deep learning for solving dynamic economic models",
        "match_count": 2,
    }]


def test_clean_long_abstract_remains_available_as_evidence() -> None:
    contract = _contract()
    abstract = "neural DSGE solution differentiable estimation " * 150
    result = fuse_seed_candidates(
        contract,
        _observations(contract, [_record("long", "A neural DSGE solver", abstract=abstract)]),
        max_selected=12,
        seeds=[],
    )
    row = result["candidates"][0]
    assert row["abstract_quality"] == {
        "status": "usable",
        "word_count": 750,
        "character_count": len(abstract),
        "sha256": row["abstract_quality"]["sha256"],
        "usable_for_relevance": True,
    }
    assert len(row["abstract_quality"]["sha256"]) == 64
    assert row["topic_evidence"]["relevance_class"] == "strong_direct"


def test_year_and_route_metadata_cannot_change_relevance_or_roles() -> None:
    contract = _contract()
    baseline = _record(
        "invariant",
        "Sequential solution for DSGE models with deep neural networks",
        abstract="A neural DSGE solution method.",
        year=2021,
        route_purpose="direct_method",
    )
    changed = {**baseline, "year": 2024, "publication_date": "2024-01-01"}
    changed["route_purposes"] = ["survey_or_tutorial"]
    first = fuse_seed_candidates(
        contract, _observations(contract, [baseline]), max_selected=12, seeds=[]
    )["candidates"][0]
    second = fuse_seed_candidates(
        contract, _observations(contract, [changed]), max_selected=12, seeds=[]
    )["candidates"][0]
    assert first["topic_evidence"] == second["topic_evidence"]
    assert first["role_hypotheses"] == second["role_hypotheses"]


def test_duplicate_provider_record_cannot_create_relevance_or_selection() -> None:
    contract = _contract()
    weak = _record(
        "weak", "General Parameter Estimation", abstract="A solution method.",
        citations=1_000_000,
    )
    duplicate = copy.deepcopy(weak)
    baseline = fuse_seed_candidates(
        contract, _observations(contract, [weak]), max_selected=12, seeds=[]
    )
    repeated = fuse_seed_candidates(
        contract, _observations(contract, [weak, duplicate]), max_selected=12, seeds=[]
    )
    assert repeated["selected_paper_ids"] == baseline["selected_paper_ids"] == []
    assert repeated["candidates"][0]["topic_evidence"] == baseline["candidates"][0]["topic_evidence"]
    assert repeated["candidates"][0]["provider_count"] == baseline["candidates"][0]["provider_count"] == 1


def test_seed_authorities_cannot_exceed_selection_cap() -> None:
    with pytest.raises(MissionStateError, match="cannot exceed max_selected"):
        build_seed_campaign(
            _contract(),
            max_selected=1,
            seeds=["doi:10.5555/one", "doi:10.5555/two"],
        )
