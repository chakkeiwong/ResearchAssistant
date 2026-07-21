from __future__ import annotations

import json
from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest

from research_assistant.survey import build as survey_build
from research_assistant.survey.discovery_quality import (
    evaluate_discovery_quality,
    normalize_record,
    parse_seed,
)
from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.mission_state import MissionStateManager
from research_assistant.survey.source_intake import (
    MissionSourceCapability,
    SourceCapabilityResult,
    build_source_intake_metadata_authority,
    run_mission_source_intake,
    validate_mission_source_intake,
)
from research_assistant.survey.supervisor import validate_public_source_packet_inputs


TOPIC = "Neural Optimal Transport for generative modeling and inference"
SEED = "arxiv:2201.12220v3"


def _provider_row(
    provider: str,
    source_id: str,
    *,
    query_kind: str = "seed_resolution",
    citation_count: int | None = None,
) -> dict:
    if provider == "arxiv":
        return {
            "provider": "arxiv",
            "query_kind": query_kind,
            "source_id": source_id,
            "primary_category": "cs.LG",
            "published": "2022-01-01",
        }
    return {
        "provider": "openalex",
        "query_kind": query_kind,
        "source_id": source_id,
        "citation_count": citation_count,
        "publication_date": "2022-01-01",
        "work_type": "article",
    }


def _record(
    key: str,
    title: str,
    *,
    provider: str,
    source_id: str,
    seed_key: str | None = SEED,
    topic_query: bool = False,
    authors: list[str] | None = None,
    year: int | None = 2022,
    doi: str | None = None,
    arxiv_id: str | None = None,
    openalex_id: str | None = None,
    citation_count: int | None = None,
    roles: list[str] | None = None,
    referenced_works: list[str] | None = None,
) -> dict:
    return {
        "record_key": key,
        "title": title,
        "authors": authors or ["Alice Example"],
        "year": year,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": openalex_id,
        "landing_page_url": (
            f"https://arxiv.org/abs/{arxiv_id}"
            if arxiv_id
            else f"https://openalex.org/{openalex_id or source_id}"
        ),
        "citation_count": citation_count,
        "providers": [provider],
        "roles": roles or [],
        "provider_records": [
            _provider_row(
                provider,
                source_id,
                query_kind="topic_search" if topic_query else "seed_resolution",
                citation_count=citation_count,
            )
        ],
        "referenced_works": referenced_works or [],
        "query_provenance": [
            {
                "provider": provider,
                "query_kind": "topic_search" if topic_query else "seed_resolution",
                "normalized_seed_key": seed_key,
                "topic_query": topic_query,
            }
        ],
    }


def _seed_record(**overrides) -> dict:
    values = {
        "key": "arxiv-seed",
        "title": "Neural Optimal Transport",
        "provider": "arxiv",
        "source_id": "2201.12220v3",
        "arxiv_id": "2201.12220v3",
        "roles": ["seed"],
    }
    values.update(overrides)
    return _record(**values)


def _evaluate(records: list[dict], *, seeds: list[str] | None = None, max_records: int = 25) -> dict:
    return evaluate_discovery_quality(
        topic=TOPIC,
        seeds=seeds or [SEED],
        records=records,
        max_records=max_records,
    )


@pytest.mark.parametrize(
    ("seed", "kind", "value"),
    [
        ("arxiv:2201.12220v3", "arxiv_id", "arxiv:2201.12220v3"),
        ("https://arxiv.org/pdf/2201.12220v3.pdf", "arxiv_id", "arxiv:2201.12220v3"),
        ("doi:10.1000/ABC", "doi", "doi:10.1000/abc"),
        ("https://doi.org/10.1000/ABC", "doi", "doi:10.1000/abc"),
        ("openalex:W123", "openalex_id", "openalex:w123"),
        ("https://openalex.org/W123", "openalex_id", "openalex:w123"),
        ("Neural Optimal Transport", "title", "neural optimal transport"),
    ],
)
def test_seed_parser_closes_identifier_and_title_forms(seed: str, kind: str, value: str) -> None:
    parsed = parse_seed(seed)
    assert parsed["kind"] == kind
    assert parsed["value"] == value


def test_exact_arxiv_version_seed_resolves_against_family_alias() -> None:
    result = _evaluate([_seed_record()])
    resolution = result["identity_resolution"]["seed_resolutions"][0]
    assert result["status"] == "eligible"
    assert resolution["disposition"] == "resolved_exact_identifier"
    assert resolution["selected_identifier"] == "arxiv:2201.12220v3"


@pytest.mark.parametrize(
    ("seed", "expected_identifier"),
    [
        ("arxiv:2201.12220v3", "arxiv:2201.12220v3"),
        ("doi:10.1000/neural-ot", "doi:10.1000/neural-ot"),
        ("openalex:W123", "openalex:w123"),
    ],
)
def test_exact_mission_seed_identifier_wins_component_display(
    seed: str,
    expected_identifier: str,
) -> None:
    row = _seed_record(
        doi="10.1000/neural-ot",
        openalex_id="W123",
        seed_key=parse_seed(seed)["key"],
    )
    result = _evaluate([row], seeds=[seed])
    component = next(item for item in result["identity_resolution"]["components"] if item["paper_id"])

    assert result["status"] == "eligible"
    assert component["canonical_identifier"] == expected_identifier
    assert result["included"][0]["identifier"] == expected_identifier


def test_identifier_conflict_blocks_global_seed_gate_and_intake_candidates() -> None:
    left = _seed_record()
    right = _seed_record(
        key="arxiv-conflict",
        title="Unrelated Bayesian Filtering",
        source_id="2201.12220v3",
        authors=["Bob Other"],
    )
    result = _evaluate([left, right])
    resolution = result["identity_resolution"]["seed_resolutions"][0]
    assert result["status"] == "blocked_seed_resolution"
    assert resolution["disposition"] == "identity_conflict"
    assert result["included"] == []
    assert result["selected_records"] == []


def test_title_seed_choices_are_scoped_to_its_query_provenance() -> None:
    title = "Neural Optimal Transport"
    scoped = _record(
        "openalex-seed",
        title,
        provider="openalex",
        source_id="W123",
        seed_key=title.casefold(),
        openalex_id="W123",
    )
    topic_only = _record(
        "openalex-topic-copy",
        title,
        provider="openalex",
        source_id="W999",
        seed_key=None,
        topic_query=True,
        openalex_id="W999",
    )
    result = _evaluate([scoped, topic_only], seeds=[title])
    resolution = result["identity_resolution"]["seed_resolutions"][0]
    assert result["status"] == "eligible"
    assert resolution["disposition"] == "resolved_unique_title"
    assert len(resolution["choices"]) == 1


def test_two_exact_title_choices_are_ambiguous_and_block_every_candidate() -> None:
    title = "Neural Optimal Transport"
    rows = [
        _record("oa-1", title, provider="openalex", source_id="W1", openalex_id="W1", seed_key=title.casefold()),
        _record("oa-2", title, provider="openalex", source_id="W2", openalex_id="W2", seed_key=title.casefold()),
    ]
    result = _evaluate(rows, seeds=[title])
    assert result["identity_resolution"]["seed_resolutions"][0]["disposition"] == "ambiguous_title"
    assert result["included"] == []


def test_high_margin_title_requires_three_seed_tokens() -> None:
    short_seed = "Neural Transport"
    row = _record(
        "oa-near",
        "Neural Transports",
        provider="openalex",
        source_id="W1",
        openalex_id="W1",
        seed_key=short_seed.casefold(),
    )
    result = _evaluate([row], seeds=[short_seed])
    assert result["identity_resolution"]["seed_resolutions"][0]["disposition"] == "ambiguous_title"
    assert result["status"] == "blocked_seed_resolution"


def test_multi_seed_gate_forbids_partial_intake() -> None:
    first = _seed_record()
    unresolved_title = "Transport Geometry Missing Work"
    result = _evaluate([first], seeds=[SEED, unresolved_title])
    rows = {row["normalized_seed_key"]: row for row in result["identity_resolution"]["seed_resolutions"]}
    assert rows[SEED]["disposition"] == "resolved_exact_identifier"
    assert rows[unresolved_title.casefold()]["disposition"] == "unresolved"
    assert result["status"] == "blocked_seed_resolution"
    assert result["included"] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("citation_count", True),
        ("citation_count", -1),
        ("citation_count", 1.5),
        ("year", False),
        ("year", 999),
        ("title", "---"),
    ],
)
def test_record_schema_rejects_malformed_scalar_types(field: str, value) -> None:
    row = _seed_record()
    row[field] = value
    with pytest.raises(MissionStateError) as error:
        normalize_record(row)
    assert error.value.code == "invalid_discovery_metadata"


def test_unknown_private_or_path_field_is_rejected() -> None:
    row = _seed_record()
    row["credential_path"] = "/secret"
    with pytest.raises(MissionStateError) as error:
        normalize_record(row)
    assert error.value.code == "invalid_discovery_metadata"


def test_compatible_arxiv_doi_openalex_rows_merge_independent_of_order() -> None:
    arxiv = _seed_record(doi="10.1000/neural-ot")
    openalex = _record(
        "openalex-seed",
        "Neural Optimal Transport",
        provider="openalex",
        source_id="W123",
        doi="10.1000/neural-ot",
        arxiv_id="2201.12220v1",
        openalex_id="W123",
        citation_count=42,
        roles=["seed"],
    )
    identities = []
    for rows in permutations([arxiv, openalex]):
        result = _evaluate(list(rows))
        components = [row for row in result["identity_resolution"]["components"] if row["paper_id"]]
        assert len(components) == 1
        identities.append(components[0]["paper_id"])
        assert components[0]["providers"] == ["arxiv", "openalex"]
    assert len(set(identities)) == 1


def test_mixed_arxiv_doi_component_allows_distant_publication_year() -> None:
    rows = [
        _seed_record(year=2019),
        _record(
            "bridge",
            "Neural Optimal Transport",
            provider="openalex",
            source_id="W123",
            year=2024,
            doi="10.1000/neural-ot",
            arxiv_id="2201.12220v3",
            openalex_id="W123",
            roles=["seed"],
        ),
        _record(
            "published",
            "Neural Optimal Transport",
            provider="openalex",
            source_id="W456",
            year=2024,
            doi="10.1000/neural-ot",
            openalex_id="W456",
            roles=["seed"],
        ),
    ]
    result = _evaluate(rows)
    component = next(row for row in result["identity_resolution"]["components"] if row["paper_id"])
    assert component["component_status"] == "eligible"
    assert component["years"] == [2019, 2024]


def test_non_family_distant_year_component_is_visible_conflict_without_paper_id() -> None:
    rows = [
        _record("old", "Neural Optimal Transport", provider="openalex", source_id="W1", year=2010, openalex_id="W1"),
        _record("new", "Neural Optimal Transport", provider="openalex", source_id="W1", year=2024, openalex_id="W1"),
    ]
    result = _evaluate(rows)
    component = result["identity_resolution"]["components"][0]
    assert component["component_status"] == "identity_conflict"
    assert component["paper_id"] is None
    assert {row["code"] for row in component["reasons"]} == {"year_conflict"}


def test_strong_alias_title_conflict_has_no_paper_id() -> None:
    rows = [
        _record("doi-a", "Neural Optimal Transport", provider="openalex", source_id="W1", doi="10.1000/shared", openalex_id="W1"),
        _record("doi-b", "Unrelated Filtering", provider="openalex", source_id="W2", doi="10.1000/shared", openalex_id="W2"),
    ]
    result = _evaluate(rows, seeds=["doi:10.1000/shared"])
    conflict = result["identity_resolution"]["components"][0]
    assert conflict["component_status"] == "identity_conflict"
    assert conflict["paper_id"] is None
    assert conflict["conflict_id"].startswith("dq_conflict_")


def test_title_only_possible_duplicates_have_distinct_stable_ids() -> None:
    rows = [
        _record("title-a", "Neural Optimal Transport", provider="openalex", source_id="W1", openalex_id=None),
        _record("title-b", "Neural Optimal Transport", provider="openalex", source_id="W2", openalex_id=None),
    ]
    result = _evaluate(rows, seeds=["Neural Optimal Transport"])
    components = [row for row in result["identity_resolution"]["components"] if row["paper_id"]]
    assert len({row["paper_id"] for row in components}) == 2
    assert result["identity_resolution"]["possible_duplicates"]


def test_exact_source_duplicate_collapses_and_retains_duplicate_evidence() -> None:
    first = _seed_record()
    second = deepcopy(first)
    result = _evaluate([first, second])
    assert len([row for row in result["identity_resolution"]["components"] if row["paper_id"]]) == 1
    assert result["identity_resolution"]["exact_duplicates"] == [
        {
            "source_identities": [["arxiv", "2201.12220v3", "arxiv-seed"]],
            "record_key": "arxiv-seed",
            "reason": "exact_source_identity_and_metadata",
        }
    ]


def test_multi_provider_duplicate_has_one_visible_input_row_disposition() -> None:
    first = _seed_record(
        doi="10.1000/neural-ot",
        openalex_id="W123",
    )
    first["providers"] = ["arxiv", "openalex"]
    first["provider_records"].append(
        _provider_row("openalex", "W123", citation_count=None)
    )
    first["query_provenance"].append(
        {
            "provider": "openalex",
            "query_kind": "seed_resolution",
            "normalized_seed_key": SEED,
            "topic_query": False,
        }
    )
    second = deepcopy(first)
    result = _evaluate([first, second])

    assert len(result["identity_resolution"]["exact_duplicates"]) == 1
    duplicate = result["identity_resolution"]["exact_duplicates"][0]
    assert duplicate["source_identities"] == [
        ["arxiv", "2201.12220v3", "arxiv-seed"],
        ["openalex", "w123", "arxiv-seed"],
    ]


def test_record_provider_list_must_equal_provider_record_coverage() -> None:
    row = _seed_record()
    row["providers"] = ["arxiv", "openalex"]

    with pytest.raises(MissionStateError) as error:
        normalize_record(row)

    assert error.value.code == "invalid_discovery_metadata"
    assert "providers differ from provider-record coverage" in str(error.value)


def test_provider_record_routes_must_equal_query_provenance() -> None:
    row = _seed_record()
    row["provider_records"].append(
        _provider_row("arxiv", "2201.12220v3", query_kind="topic_search")
    )

    with pytest.raises(MissionStateError) as error:
        normalize_record(row)

    assert error.value.code == "invalid_discovery_metadata"
    assert "provider-record routes differ from query provenance" in str(error.value)


def test_duplicate_routing_merges_working_roles_without_mutating_input_evidence() -> None:
    seed_route = _seed_record()
    topic_route = deepcopy(seed_route)
    topic_route["roles"] = ["adjacent_method"]
    topic_route["provider_records"][0]["query_kind"] = "topic_search"
    topic_route["query_provenance"] = [
        {
            "provider": "arxiv",
            "query_kind": "topic_search",
            "normalized_seed_key": None,
            "topic_query": True,
        }
    ]

    result = _evaluate([seed_route, topic_route])

    input_roles = [row["roles"] for row in result["identity_resolution"]["input_records"]]
    assert input_roles == [["seed"], ["adjacent_method"]]
    component = next(row for row in result["identity_resolution"]["components"] if row["paper_id"])
    assert component["roles"] == ["adjacent_method", "seed"]
    assert len(component["rows"][0]["query_provenance"]) == 2


def test_same_source_identity_with_changed_metadata_fails_closed() -> None:
    first = _seed_record()
    second = deepcopy(first)
    second["year"] = 2023
    with pytest.raises(MissionStateError) as error:
        _evaluate([first, second])
    assert error.value.code == "source_identity_conflict"


def test_stable_identity_ignores_order_and_citation_count() -> None:
    seed = _seed_record(doi="10.1000/neural-ot")
    alternate = _record(
        "oa-seed",
        "Neural Optimal Transport",
        provider="openalex",
        source_id="W1",
        doi="10.1000/neural-ot",
        arxiv_id="2201.12220v1",
        openalex_id="W1",
        citation_count=1,
        roles=["seed"],
    )
    first = _evaluate([seed, alternate])
    alternate["citation_count"] = 9999
    alternate["provider_records"][0]["citation_count"] = 9999
    second = _evaluate([alternate, seed])
    first_id = next(row["paper_id"] for row in first["identity_resolution"]["components"] if row["paper_id"])
    second_id = next(row["paper_id"] for row in second["identity_resolution"]["components"] if row["paper_id"])
    assert first_id == second_id


def test_relevance_beats_high_citation_noise_and_keeps_exclusion_visible() -> None:
    seed = _seed_record()
    relevant = _record(
        "relevant",
        "Neural Transport Generative Inference",
        provider="openalex",
        source_id="W2",
        seed_key=None,
        topic_query=True,
        openalex_id="W2",
        citation_count=1,
        roles=["adjacent_method"],
    )
    noise = _record(
        "noise",
        "Fractional Brownian Motion Applications",
        provider="openalex",
        source_id="W3",
        seed_key=None,
        topic_query=True,
        openalex_id="W3",
        citation_count=1_000_000,
        roles=["adjacent_method"],
    )
    result = _evaluate([seed, noise, relevant])
    titles = [row["title"] for row in result["included"]]
    assert "Neural Transport Generative Inference" in titles
    assert "Fractional Brownian Motion Applications" not in titles
    excluded = {row["paper_key"]: row["disposition"] for row in result["excluded"] if row["paper_key"]}
    noise_id = next(row["paper_id"] for row in result["identity_resolution"]["components"] if row.get("title") == noise["title"])
    assert excluded[noise_id] == "irrelevant_excluded"


def test_direct_role_requires_one_token_and_navigation_role_requires_two() -> None:
    rows = [
        _seed_record(),
        _record("direct-zero", "Fractional Brownian", provider="openalex", source_id="W1", seed_key=None, topic_query=True, openalex_id="W1", roles=["direct_method"]),
        _record("direct-one", "Neural Fractional", provider="openalex", source_id="W2", seed_key=None, topic_query=True, openalex_id="W2", roles=["direct_method"]),
        _record("nav-one", "Neural Fractional", provider="openalex", source_id="W3", seed_key=None, topic_query=True, openalex_id="W3", roles=["major_citing_work"]),
        _record("nav-two", "Neural Transport Fractional", provider="openalex", source_id="W4", seed_key=None, topic_query=True, openalex_id="W4", roles=["major_citing_work"]),
    ]
    result = _evaluate(rows)
    by_title = {
        component.get("title"): next(
            row["disposition"] for row in result["relevance_ranking"]["rows"] if row["paper_id"] == component.get("paper_id")
        )
        for component in result["identity_resolution"]["components"]
        if component.get("paper_id")
    }
    assert by_title["Fractional Brownian"] == "irrelevant_excluded"
    assert by_title["Neural Fractional"] in {"direct_topic_match", "weak_match_review_required"}
    nav_one_id = next(row["paper_id"] for row in result["identity_resolution"]["components"] if row.get("title") == "Neural Fractional" and "major_citing_work" in row.get("roles", []))
    nav_one = next(row for row in result["relevance_ranking"]["rows"] if row["paper_id"] == nav_one_id)
    assert nav_one["disposition"] == "weak_match_review_required"
    assert by_title["Neural Transport Fractional"] == "adjacent_match"


def test_cap_applies_after_relevance_and_keeps_rows_visible() -> None:
    rows = [
        _seed_record(),
        *[
            _record(
                f"adj-{index}",
                f"Neural Transport Candidate {index}",
                provider="openalex",
                source_id=f"W{index + 10}",
                seed_key=None,
                topic_query=True,
                openalex_id=f"W{index + 10}",
                roles=["adjacent_method"],
            )
            for index in range(3)
        ],
    ]
    result = _evaluate(rows, max_records=2)
    assert len(result["included"]) == 2
    cap_rows = [row for row in result["excluded"] if row["disposition"] == "excluded_by_cap_after_relevance"]
    assert len(cap_rows) == 2
    ranked = [row for row in result["relevance_ranking"]["rows"] if row["pre_cap_rank"] is not None]
    assert sorted(row["pre_cap_rank"] for row in ranked) == [1, 2, 3, 4]
    assert all(row["final_rank"] is None for row in ranked if row["pre_cap_rank"] > 2)


def test_citation_tiebreak_is_confined_to_equal_relevance_stratum() -> None:
    rows = [
        _seed_record(),
        _record(
            "direct",
            "Neural Fractional",
            provider="openalex",
            source_id="W1",
            seed_key=None,
            topic_query=True,
            openalex_id="W1",
            citation_count=1,
            roles=["direct_method"],
        ),
        _record(
            "adj-high",
            "Neural Transport High",
            provider="openalex",
            source_id="W2",
            seed_key=None,
            topic_query=True,
            openalex_id="W2",
            citation_count=10_000,
        ),
        _record(
            "adj-low",
            "Neural Transport Low",
            provider="openalex",
            source_id="W3",
            seed_key=None,
            topic_query=True,
            openalex_id="W3",
            citation_count=2,
        ),
        _record(
            "adj-missing",
            "Neural Transport Missing",
            provider="openalex",
            source_id="W4",
            seed_key=None,
            topic_query=True,
            openalex_id="W4",
            citation_count=None,
        ),
    ]
    result = _evaluate(rows)
    ranked = sorted(
        (row for row in result["relevance_ranking"]["rows"] if row["pre_cap_rank"] is not None),
        key=lambda row: row["pre_cap_rank"],
    )
    title_by_id = {
        component["paper_id"]: component["title"]
        for component in result["identity_resolution"]["components"]
        if component["paper_id"]
    }
    titles = [title_by_id[row["paper_id"]] for row in ranked]

    assert titles[0] == "Neural Optimal Transport"
    assert titles[1] == "Neural Fractional"
    assert titles[2:] == [
        "Neural Transport High",
        "Neural Transport Low",
        "Neural Transport Missing",
    ]


def test_seed_count_above_metadata_cap_fails_before_record_processing() -> None:
    with pytest.raises(MissionStateError) as error:
        evaluate_discovery_quality(topic=TOPIC, seeds=["One", "Two"], records=[{"not": "valid"}], max_records=1)
    assert error.value.code == "seed_count_exceeds_metadata_cap"


def test_boolean_metadata_cap_blocks_before_provider_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def forbidden_collect(**kwargs):
        calls.append(kwargs)
        raise AssertionError("Boolean max_records must block before provider collection")

    monkeypatch.setattr(survey_build, "_collect_public_metadata", forbidden_collect)
    result = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=tmp_path / "public_metadata",
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=True,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "public_metadata_max_records_out_of_bounds"
    assert calls == []


@pytest.mark.parametrize(
    ("providers", "reason"),
    [
        ([], "missing_public_metadata_provider"),
        ([None], "invalid_public_metadata_provider"),
        (["arxiv\x00foreign"], "invalid_public_metadata_provider"),
    ],
)
def test_invalid_explicit_provider_list_blocks_before_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    providers: list,
    reason: str,
) -> None:
    calls = []

    def forbidden_collect(**kwargs):
        calls.append(kwargs)
        raise AssertionError("invalid providers must block before collection")

    monkeypatch.setattr(survey_build, "_collect_public_metadata", forbidden_collect)
    result = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=tmp_path / "public_metadata",
        mode="public-metadata",
        public_metadata_providers=providers,
        max_records=25,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == reason
    assert calls == []


def test_v2_builder_commits_reuses_and_rejects_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "public_metadata"
    collection = {
        "status": "metadata_collected",
        "fetched_at": "2026-07-12T00:00:00+00:00",
        "records": [_seed_record(roles=[])],
        "provider_statuses": [
            {
                "provider": "arxiv",
                "query_kind": "seed_resolution",
                "normalized_seed_key": SEED,
                "topic_query": False,
                "query_cap": 5,
                "status": "available",
                "record_count": 1,
                "raw_response_saved": False,
            },
            {
                "provider": "arxiv",
                "query_kind": "topic_search",
                "normalized_seed_key": None,
                "topic_query": True,
                "query_cap": 12,
                "status": "available",
                "record_count": 0,
                "raw_response_saved": False,
            },
        ],
        "raw_response_policy": {
            "raw_responses_saved": False,
            "privacy_scan": "not_applicable_raw_responses_not_saved",
            "reason": "fixture-only Phase 7 test",
        },
    }
    calls = []

    def collect(**kwargs):
        calls.append(kwargs)
        return deepcopy(collection)

    monkeypatch.setattr(survey_build, "_collect_public_metadata", collect)
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=output,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )

    assert created["status"] == "metadata_only_packet"
    assert created["reused_existing"] is False
    assert len(calls) == 1
    assert {path.name for path in output.iterdir()} == set(survey_build.PUBLIC_METADATA_PACKET_FILES)
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    candidate = json.loads(before["candidate_ledger.json"])
    assert candidate["included"][0]["roles"] == ["seed"]

    def forbidden_collect(**kwargs):
        raise AssertionError(f"complete V2 reuse called provider collector: {kwargs}")

    monkeypatch.setattr(survey_build, "_collect_public_metadata", forbidden_collect)
    reused = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=output,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    assert reused["status"] == "metadata_only_packet"
    assert reused["reused_existing"] is True
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}

    relevance_path = output / "relevance_ranking.json"
    relevance = json.loads(relevance_path.read_bytes())
    relevance["rows"][0]["reason"] = "tampered"
    relevance_path.write_bytes(survey_build.pretty_json_bytes(relevance))
    blocked = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=output,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    assert blocked["status"] == "blocked"
    assert blocked["blocked_reason"] == "stale_public_metadata_v2"


def test_v2_builder_rejects_symlinked_root_before_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    output = tmp_path / "public_metadata"
    output.symlink_to(target, target_is_directory=True)
    calls = []

    def forbidden_collect(**kwargs):
        calls.append(kwargs)
        raise AssertionError("unsafe output root must block before provider collection")

    monkeypatch.setattr(survey_build, "_collect_public_metadata", forbidden_collect)
    result = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=output,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "unsafe_public_write_path"
    assert calls == []
    assert list(target.iterdir()) == []


def test_provider_exception_and_malformed_rows_become_closed_unavailable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raising_query(**kwargs):
        raise RuntimeError(f"fixture provider failure: {kwargs}")

    def malformed_search(query, **kwargs):
        return {
            "records": [{"unknown": "row"}],
            "status": {"status": "available"},
        }

    monkeypatch.setattr(survey_build, "_arxiv_metadata_query", raising_query)
    monkeypatch.setattr(survey_build, "_openalex_metadata_search", malformed_search)
    collection = survey_build._collect_public_metadata(
        topic=TOPIC,
        seeds=[SEED],
        providers=["arxiv", "openalex"],
        max_records=25,
        fetched_at="2026-07-12T00:00:00+00:00",
    )

    assert collection["records"] == []
    assert len(collection["provider_statuses"]) == 4
    assert all(row["status"] == "unavailable" for row in collection["provider_statuses"])
    assert all(row["record_count"] == 0 for row in collection["provider_statuses"])


def test_v2_reuse_rejects_provider_count_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "public_metadata"
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])]),
    )
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=output,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    assert created["status"] == "metadata_only_packet"
    manifest_path = output / "build_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["provider_statuses"][0]["record_count"] = 0
    manifest_path.write_bytes(survey_build.pretty_json_bytes(manifest))
    blocked = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=output,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )

    assert blocked["status"] == "blocked"
    assert blocked["blocked_reason"] == "invalid_public_metadata_v2"


def _mission_collection(
    *,
    records: list[dict],
    seed_key: str = SEED,
    providers: tuple[str, ...] = ("arxiv", "openalex"),
) -> dict:
    statuses = []
    for provider in providers:
        statuses.extend(
            [
                {
                    "provider": provider,
                    "query_kind": "seed_resolution",
                    "normalized_seed_key": seed_key,
                    "topic_query": False,
                    "query_cap": 5,
                    "status": "available",
                    "record_count": sum(
                        provider in row["providers"]
                        and any(
                            provenance["normalized_seed_key"] == seed_key
                            for provenance in row["query_provenance"]
                        )
                        for row in records
                    ),
                    "raw_response_saved": False,
                },
                {
                    "provider": provider,
                    "query_kind": "topic_search",
                    "normalized_seed_key": None,
                    "topic_query": True,
                    "query_cap": 12,
                    "status": "available",
                    "record_count": 0,
                    "raw_response_saved": False,
                },
            ]
        )
    return {
        "status": "metadata_collected" if records else "metadata_empty_or_unavailable",
        "fetched_at": "2026-07-12T00:00:00+00:00",
        "records": records,
        "provider_statuses": statuses,
        "raw_response_policy": {
            "raw_responses_saved": False,
            "privacy_scan": "not_applicable_raw_responses_not_saved",
            "reason": "fixture-only Phase 7 mission test",
        },
    }


def _available_fixture_source(request) -> SourceCapabilityResult:
    final_url = "https://arxiv.org/abs/2201.12220v3"
    record = {
        "paper_id": request.paper_id,
        "source_type": "arxiv_latex",
        "status": "available",
        "primary_for_audit": True,
        "artifact_root": None,
        "original_source_path": None,
        "flattened_source_path": None,
        "sections": [
            {
                "level": 1,
                "command": "section",
                "title": "Method",
                "line": 1,
                "labels": ["sec:method"],
                "raw_latex": "Fixture source text for downstream replay only.",
            }
        ],
        "equations": [],
        "theorem_like_blocks": [],
        "labels": [],
        "references": [],
        "citations": [],
        "bibliography": [],
        "macros": [],
        "provenance": {
            "arxiv_id": "2201.12220v3",
            "identifier": request.identifier,
            "provider": "arxiv",
            "final_url": final_url,
            "fixture_only": True,
        },
        "diagnostics": {"fixture_only": True, "section_count": 1},
        "limitations": [
            {
                "field": "source",
                "status": "fixture_only",
                "note": "No live source transport was run.",
            }
        ],
    }
    return SourceCapabilityResult(
        candidate_id=request.candidate_id,
        identifier=request.identifier,
        outcome_status="available",
        code="available",
        provider="arxiv",
        final_url=final_url,
        structured_record=record,
        byte_count=len(survey_build.pretty_json_bytes(record)),
    )


def _checkpoint_v2_authority(
    mission: Path,
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MissionStateManager, object, Path, dict]:
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[SEED],
        confirm_public_discovery=True,
        resume=False,
        force=False,
    )
    initial = manager.begin()
    metadata = mission / "public_metadata"
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])], providers=("arxiv",)),
    )
    result = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    assert result["status"] == "metadata_only_packet"
    authority = build_source_intake_metadata_authority(
        mission_root=mission,
        metadata_root=metadata,
        snapshot=initial,
    )
    next_action = {
        "schema_version": "ra-survey-public-source-next-action-v1",
        "status": "ready_for_source_intake",
        "mission_status": "ready_for_local_continuation",
        "action_id": "source_intake",
        "source_intake_metadata_authority": authority,
    }
    snapshot = manager.checkpoint(
        {
            "status": "ready_for_local_continuation",
            "topic": TOPIC,
            "seeds": [SEED],
            "output_dir": str(mission),
            "source_intake_metadata_authority": authority,
        },
        next_action,
    )
    return manager, snapshot, metadata, authority


def test_v2_authority_binds_all_artifacts_through_intake_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata, authority = _checkpoint_v2_authority(
        mission,
        monkeypatch=monkeypatch,
    )
    calls = []

    def metadata_only(request):
        calls.append(request.candidate_id)
        return SourceCapabilityResult(
            candidate_id=request.candidate_id,
            identifier=request.identifier,
            outcome_status="metadata_only",
            code="metadata_only",
            provider=request.providers[0],
        )

    try:
        result = run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(metadata_only),
        )
        replay = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()

    assert authority["schema_version"] == "ra-survey-source-intake-metadata-authority-v2"
    assert [row["name"] for row in authority["artifact_rows"]] == sorted(
        survey_build.PUBLIC_METADATA_PACKET_FILES
    )
    assert result["status"] == "completed_with_outcomes"
    assert calls == [authority["candidate_ledger_path"] and replay["outcomes"][0]["candidate_id"]]
    assert replay["outcomes"][0]["outcome_status"] == "metadata_only"


def test_v2_authority_accepts_roleless_relevance_inclusion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = tmp_path / "mission"
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[SEED],
        confirm_public_discovery=True,
        resume=False,
        force=False,
    )
    snapshot = manager.begin()
    relevant = _record(
        "arxiv-relevant",
        "Neural Transport Candidate",
        provider="arxiv",
        source_id="2401.00001",
        seed_key=None,
        topic_query=True,
        arxiv_id="2401.00001",
        roles=[],
    )
    relevant["provider_records"][0]["query_kind"] = "topic_search"
    collection = _mission_collection(
        records=[_seed_record(roles=[]), relevant],
        providers=("arxiv",),
    )
    collection["provider_statuses"][1]["record_count"] = 1
    monkeypatch.setattr(survey_build, "_collect_public_metadata", lambda **_: collection)
    metadata = mission / "public_metadata"
    built = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    try:
        authority = build_source_intake_metadata_authority(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
        )
    finally:
        manager.abort()

    candidate = json.loads((metadata / "candidate_ledger.json").read_bytes())
    assert built["status"] == "metadata_only_packet"
    assert candidate["candidate_count"] == 2
    assert candidate["included"][1]["roles"] == []
    assert authority["candidate_count"] == 2


def test_blocked_v2_seed_gate_performs_zero_intake_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = tmp_path / "mission"
    missing_seed = "Missing Transport Seed"
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[missing_seed],
        confirm_public_discovery=True,
        resume=False,
        force=False,
    )
    initial = manager.begin()
    metadata = mission / "public_metadata"
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(
            records=[],
            seed_key=missing_seed.casefold(),
            providers=("arxiv",),
        ),
    )
    built = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[missing_seed],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    snapshot = manager.checkpoint(
        {"status": "ready_for_local_continuation", "topic": TOPIC, "seeds": [missing_seed]},
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "ready_for_source_intake",
            "mission_status": "ready_for_local_continuation",
            "action_id": "source_intake",
        },
    )
    calls = []

    def forbidden(request):
        calls.append(request)
        raise AssertionError("blocked V2 must not invoke intake capability")

    try:
        with pytest.raises(MissionStateError) as error:
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(forbidden),
            )
    finally:
        manager.abort()

    assert built["status"] == "metadata_resolution_blocked"
    assert error.value.code == "source_metadata_seed_resolution_blocked"
    assert calls == []
    assert not (mission / "source_intake").exists()


def test_v2_discriminator_forbids_candidate_schema_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = tmp_path / "mission"
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[SEED],
        confirm_public_discovery=True,
        resume=False,
        force=False,
    )
    snapshot = manager.begin()
    metadata = mission / "public_metadata"
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])]),
    )
    survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    candidate_path = metadata / "candidate_ledger.json"
    candidate = json.loads(candidate_path.read_bytes())
    candidate["schema_version"] = "ra-survey-candidate-ledger-v1"
    candidate_path.write_bytes(survey_build.pretty_json_bytes(candidate))
    try:
        with pytest.raises(MissionStateError) as error:
            build_source_intake_metadata_authority(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
            )
    finally:
        manager.abort()

    assert error.value.code == "stale_public_metadata_v2"


def test_orchestrator_rejects_manifestless_v2_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from research_assistant.survey.orchestrate import run_public_source_workflow

    mission = tmp_path / "mission"
    first = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])]),
    )
    metadata = mission / "public_metadata"
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    assert created["status"] == "metadata_only_packet"
    (metadata / "build_manifest.json").unlink()

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
    )

    assert result["local_supervisor"]["status"] == "terminal_blocked_invalid_artifact"
    assert result["local_supervisor"]["terminal_reason"] == "partial_public_metadata_v2_residue"
    assert not (mission / "source_intake").exists()


def test_ordinary_orchestrator_semantically_replays_committed_v2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from research_assistant.survey.orchestrate import run_public_source_workflow

    mission = tmp_path / "mission"
    run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
    )
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])]),
    )
    metadata = mission / "public_metadata"
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    assert created["status"] == "metadata_only_packet"

    relevance_path = metadata / "relevance_ranking.json"
    relevance = json.loads(relevance_path.read_bytes())
    relevance["rows"][0]["reason"] = "tampered"
    relevance_path.write_bytes(survey_build.pretty_json_bytes(relevance))

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "stale_public_metadata_v2"
    assert not (mission / "source_intake").exists()


def test_ordinary_orchestrator_candidate_schema_forbids_v2_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from research_assistant.survey.orchestrate import run_public_source_workflow

    mission = tmp_path / "mission"
    run_public_source_workflow(topic=TOPIC, seeds=[SEED], output_dir=mission)
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])]),
    )
    metadata = mission / "public_metadata"
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    assert created["status"] == "metadata_only_packet"

    (metadata / "identity_resolution.json").unlink()
    (metadata / "relevance_ranking.json").unlink()
    manifest_path = metadata / "build_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["schema_version"] = "ra-survey-public-metadata-build-manifest-v1"
    manifest_path.write_bytes(survey_build.pretty_json_bytes(manifest))

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "incomplete_public_metadata_v2"
    assert not (mission / "source_intake").exists()


def test_ordinary_orchestrator_bounds_invalid_utf8_v2_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from research_assistant.survey.orchestrate import run_public_source_workflow

    mission = tmp_path / "mission"
    run_public_source_workflow(topic=TOPIC, seeds=[SEED], output_dir=mission)
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records=[_seed_record(roles=[])]),
    )
    metadata = mission / "public_metadata"
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    assert created["status"] == "metadata_only_packet"
    (metadata / "build_manifest.json").write_bytes(b"\xff\xfe")

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "invalid_public_metadata_v2"
    assert not (mission / "source_intake").exists()


def test_orchestrator_blocks_unresolved_v2_before_capability_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from research_assistant.survey.orchestrate import run_public_source_workflow

    mission = tmp_path / "mission"
    missing_seed = "Missing Transport Seed"
    first = run_public_source_workflow(
        topic=TOPIC,
        seeds=[missing_seed],
        output_dir=mission,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(
            records=[],
            seed_key=missing_seed.casefold(),
            providers=("arxiv",),
        ),
    )
    metadata = mission / "public_metadata"
    created = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[missing_seed],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    assert created["status"] == "metadata_resolution_blocked"
    observed = run_public_source_workflow(
        topic=TOPIC,
        seeds=[missing_seed],
        output_dir=mission,
        resume=True,
    )
    assert observed["next_gate"]["gate_id"] == "public_metadata_resolution"
    assert observed["next_action"]["action_id"] == "public_metadata_resolution"
    calls = []

    def forbidden(request):
        calls.append(request)
        raise AssertionError("unresolved V2 must not invoke capability")

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[missing_seed],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(forbidden),
    )

    assert result["local_supervisor"]["status"] == "terminal_blocked_source_intake"
    assert result["local_supervisor"]["terminal_reason"] == "source_metadata_seed_resolution_blocked"
    assert calls == []
    assert not (mission / "source_intake").exists()


def test_title_seed_v2_runs_intake_anchors_packet_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from research_assistant.survey.orchestrate import run_public_source_workflow

    mission = tmp_path / "mission"
    title_seed = "Neural Optimal Transport"
    first = run_public_source_workflow(
        topic=TOPIC,
        seeds=[title_seed],
        output_dir=mission,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    seed_record = _seed_record(roles=[])
    seed_record["query_provenance"] = [
        {
            "provider": "arxiv",
            "query_kind": "seed_resolution",
            "normalized_seed_key": title_seed.casefold(),
            "topic_query": False,
        }
    ]
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(
            records=[seed_record],
            seed_key=title_seed.casefold(),
            providers=("arxiv",),
        ),
    )
    metadata = mission / "public_metadata"
    built = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[title_seed],
        output_dir=metadata,
        mode="public-metadata",
        public_metadata_providers=["arxiv"],
        max_records=25,
    )
    assert built["status"] == "metadata_only_packet"
    resolution = json.loads((metadata / "identity_resolution.json").read_bytes())
    stable_id = resolution["seed_resolutions"][0]["selected_paper_id"]
    calls = []

    def available(request):
        calls.append(request.candidate_id)
        return _available_fixture_source(request)

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[title_seed],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(available),
    )
    packet = mission / "public_source_packet"
    packet_before = {path.name: path.read_bytes() for path in packet.iterdir()}

    replayed = run_public_source_workflow(
        topic=TOPIC,
        seeds=[title_seed],
        output_dir=mission,
        resume=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(available),
    )

    assert calls == [stable_id]
    assert result["local_supervisor"]["status"] == "terminal_blocked_human_review"
    assert [row["stage_id"] for row in result["local_supervisor"]["transition_history"]][:3] == [
        "source_intake",
        "source_anchors",
        "public_source_packet",
    ]
    assert replayed["local_supervisor"]["status"] == "terminal_blocked_human_review"
    assert packet_before == {path.name: path.read_bytes() for path in packet.iterdir()}
    candidate = json.loads((packet / "candidate_ledger.json").read_bytes())
    assert candidate["included"][0]["paper_key"] == stable_id
    assert (
        candidate["included"][0]["technical_claim_support"]
        == "not_supported_until_claim_mapping_review"
    )

    alternate_metadata = mission / "alternate_metadata"
    alternate_metadata.mkdir()
    for name in (
        "candidate_ledger.json",
        "citation_map.json",
        "source_support.json",
        "paper_classifications.json",
        "omission_risk.json",
    ):
        (alternate_metadata / name).write_bytes((metadata / name).read_bytes())
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[title_seed],
        confirm_public_discovery=False,
        resume=True,
        force=False,
    )
    snapshot = manager.begin()
    try:
        with pytest.raises(MissionStateError) as error:
            validate_public_source_packet_inputs(
                metadata_dir=alternate_metadata,
                source_status_dir=mission / "source_intake",
                anchor_dir=mission / "source_anchors",
                mission_root=mission,
                mission_snapshot=snapshot,
            )
    finally:
        manager.abort()
    assert error.value.code == "packet_v2_metadata_authority_mismatch"
