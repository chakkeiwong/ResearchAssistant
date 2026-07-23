from __future__ import annotations

from research_assistant.survey.source_selection import (
    build_source_selection_ledger,
    choose_preferred_source_version,
    select_available_sources,
)


def _candidate(key: str, stratum: str, rank: int) -> dict:
    return {
        "candidate_id": key,
        "paper_key": key,
        "stratum": stratum,
        "combined_nomination_rank": rank,
        "title": key,
    }


def test_available_selected_candidates_are_retained_without_substitution() -> None:
    result = select_available_sources(
        [_candidate("a", "direct_finance", 1)],
        [_candidate("a", "direct_finance", 1), _candidate("b", "direct_finance", 2)],
        {"a": {"outcome_status": "available"}, "b": {"outcome_status": "available"}},
    )
    assert [row["candidate_id"] for row in result["retained_selected"]] == ["a"]
    assert result["substitutions"] == []


def test_unavailable_selected_uses_same_stratum_replacement_first() -> None:
    result = select_available_sources(
        [_candidate("a", "direct_finance", 1)],
        [_candidate("a", "direct_finance", 1), _candidate("b", "direct_finance", 2), _candidate("c", "generic_rl", 3)],
        {"a": {"outcome_status": "unavailable"}, "b": {"outcome_status": "available"}, "c": {"outcome_status": "available"}},
    )
    assert [row["candidate_id"] for row in result["retained_selected"]] == ["b"]
    assert result["substitutions"][0]["fallback"] == "same_stratum"


def test_unavailable_selected_uses_ranked_fallback_when_no_purpose_is_shared() -> None:
    result = select_available_sources(
        [_candidate("a", "direct_finance", 1)],
        [_candidate("a", "direct_finance", 1), _candidate("b", "generic_rl", 2)],
        {"a": {"outcome_status": "unavailable"}, "b": {"outcome_status": "available"}},
    )
    assert result["substitutions"][0]["fallback"] == "ranked_fallback"
    assert result["unreplaced_unavailable"] == []


def test_source_replacement_order_is_deterministic() -> None:
    selected = [_candidate("missing", "direct_finance", 1)]
    lower = _candidate("lower", "direct_finance", 3)
    higher = _candidate("higher", "direct_finance", 2)
    outcomes = {
        "missing": "unavailable",
        "lower": "available",
        "higher": "available",
    }
    forward = select_available_sources(selected, [*selected, lower, higher], outcomes)
    reversed_input = select_available_sources(selected, [*selected, higher, lower], outcomes)
    assert forward["substitutions"] == reversed_input["substitutions"]
    assert forward["substitutions"][0]["replacement_candidate_key"] == "higher"


def test_unavailable_selected_without_replacement_remains_visible() -> None:
    result = select_available_sources(
        [_candidate("a", "direct_finance", 1)],
        [_candidate("a", "direct_finance", 1)],
        {"a": {"outcome_status": "unavailable", "reason": "403"}},
    )
    assert result["retained_selected"] == []
    assert result["unreplaced_unavailable"] == ["a"]
    assert result["unavailable_selected"][0]["availability"]["reason"] == "403"


def test_substitution_does_not_reuse_an_already_retained_source() -> None:
    result = select_available_sources(
        [_candidate("a", "direct_finance", 1), _candidate("missing", "direct_finance", 2)],
        [
            _candidate("a", "direct_finance", 1),
            _candidate("missing", "direct_finance", 2),
            _candidate("alias", "direct_finance", 3),
            _candidate("unique", "direct_finance", 4),
        ],
        {
            "a": {"outcome_status": "available", "source_identifier": "arxiv:1v2"},
            "missing": {"outcome_status": "unavailable"},
            "alias": {"outcome_status": "available", "source_identifier": "arxiv:1v2"},
            "unique": {"outcome_status": "available", "source_identifier": "arxiv:2v1"},
        },
    )
    assert [row["candidate_id"] for row in result["retained_selected"]] == ["a", "unique"]
    assert result["substitutions"][0]["replacement_candidate_key"] == "unique"


def test_source_version_selection_prefers_relation_then_latest_date() -> None:
    result = choose_preferred_source_version(
        [
            {"identifier": "preprint-v3", "version_relation": "author_preprint", "version_date": "2025-01-01", "available": True},
            {"identifier": "published", "version_relation": "published", "version_date": "2024-06-01", "available": True},
            {"identifier": "published-old", "version_relation": "published", "version_date": "2024-01-01", "available": True},
        ],
        publication_date="2024-06-15",
    )
    assert result["selected_version"]["identifier"] == "published"


def test_source_version_selection_prefers_publication_date_proximity_within_relation() -> None:
    result = choose_preferred_source_version(
        [
            {"identifier": "near", "version_relation": "preprint", "version_date": "2024-06-14", "available": True},
            {"identifier": "latest", "version_relation": "preprint", "version_date": "2025-01-01", "available": True},
        ],
        publication_date="2024-06-15",
    )
    assert result["selected_version"]["identifier"] == "near"
    assert result["publication_date_mismatch"] is True


def test_source_version_selection_falls_back_to_latest_lawful_preprint() -> None:
    result = choose_preferred_source_version(
        [
            {"identifier": "closed", "version_relation": "published", "version_date": "2024-06-01", "available": False},
            {"identifier": "v1", "version_relation": "preprint", "version_date": "2023-01-01", "available": True},
            {"identifier": "v2", "version_relation": "preprint", "version_date": "2024-01-01", "available": True},
        ],
        publication_date="2024-06-15",
    )
    assert result["selected_version"]["identifier"] == "v2"
    assert result["alternate_versions"][0]["identifier"] == "v1"


def test_source_version_selection_prefers_accepted_manuscript_over_preprint() -> None:
    result = choose_preferred_source_version(
        [
            {"identifier": "preprint", "version_relation": "author_preprint", "available": True},
            {"identifier": "accepted", "version_relation": "accepted_manuscript", "available": True},
        ]
    )
    assert result["selected_version"]["identifier"] == "accepted"


def test_source_version_selection_is_deterministic_on_ties() -> None:
    versions = [
        {"identifier": "b", "version_relation": "preprint", "version_date": "2024-01-01", "available": True},
        {"identifier": "a", "version_relation": "preprint", "version_date": "2024-01-01", "available": True},
    ]
    assert choose_preferred_source_version(versions)["selected_version"]["identifier"] == "a"


def test_source_version_selection_does_not_silently_resolve_metadata_conflict() -> None:
    result = choose_preferred_source_version(
        [
            {"identifier": "conflicted", "version_relation": "published", "available": True, "metadata_conflict": True},
            {"identifier": "clear", "version_relation": "accepted_manuscript", "available": True},
        ]
    )
    assert result["selected_version"]["identifier"] == "clear"
    assert result["alternate_versions"][0]["identifier"] == "conflicted"


def test_reconciliation_ledger_is_explicitly_non_claim_support() -> None:
    result = build_source_selection_ledger(
        topic="RL finance",
        selected_candidates=[_candidate("a", "direct_finance", 1)],
        eligible_candidates=[_candidate("a", "direct_finance", 1), _candidate("b", "direct_finance", 2)],
        availability_outcomes={"a": "unavailable", "b": "available"},
    )
    assert result["schema_version"] == "ra-survey-source-selection-reconciliation-v1"
    assert result["substitutions"][0]["replacement_candidate_key"] == "b"
    assert result["source_availability_is_not_technical_claim_support"] is True
