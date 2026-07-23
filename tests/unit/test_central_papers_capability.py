from __future__ import annotations

import copy
from pathlib import Path

import pytest

from research_assistant.survey.central_papers_capability import (
    OBSERVATION_SCHEMA,
    OpenAlexArxivCentralPapersCapability,
    _source_observation,
    validate_observations,
)
from research_assistant.survey.central_papers import DEFAULT_BUDGET
from research_assistant.survey.topic_contract import build_topic_contract
from research_assistant.survey.mission_state import MissionStateError


def _candidate() -> dict:
    return {
        "paper_id": "arxiv:1234.5678",
        "title": "A Generic Method",
        "authors": ["Author, A"],
        "year": 2020,
        "identifiers": {"arxiv_id": "1234.5678", "doi": None, "openalex_id": "W1"},
        "identity_status": "resolved",
        "discovery_round": 0,
        "discovery_routes": ["broad_facets"],
        "discovery_origins": [],
        "citation_count": 10,
        "venue_metric_status": "not_available",
        "source": {
            "status": "source_blocked",
            "source_type": "not_available",
            "evidence_ref": "source:blocked",
            "sections": [],
            "bibliography": [],
        },
        "safety": {
            "status": "not_checked",
            "evidence_refs": [],
            "limitations": ["limited fixture check"],
        },
        "forward_citation_status": "not_available",
        "forward_citations": [],
        "limitations": ["fixture observation only"],
    }


def _observations() -> dict:
    return {
        "schema_version": OBSERVATION_SCHEMA,
        "topic_contract_sha256": "a" * 64,
        "capability_fingerprint": "b" * 64,
        "accessed_at": "2026-07-22T00:00:00+00:00",
        "discovery_status": "available",
        "provider_statuses": [{"provider": "fixture", "status": "available", "detail": "fixture"}],
        "candidates": [_candidate()],
        "budget_consumption": {"metadata_records": 1, "metadata_requests": 1, "source_attempts": 0, "source_bytes": 0},
        "limitations": ["fixture capability"],
        "benchmark_labels_consumed": False,
    }


def test_observation_contract_rejects_inference_fields_and_unknown_forward_status() -> None:
    value = _observations()
    value["candidates"][0]["topic_fit"] = "direct"
    with pytest.raises(MissionStateError, match="fields are not exact"):
        validate_observations(value)

    value = _observations()
    value["candidates"][0]["forward_citation_status"] = "checked"
    with pytest.raises(MissionStateError, match="unsupported"):
        validate_observations(value)


def test_source_normalization_deduplicates_bibliography_identity() -> None:
    entry = {"fields": {"doi": "10.1/example", "title": "Same"}}
    source = _source_observation({
        "status": "available",
        "source_type": "arxiv_latex",
        "sections": [{"title": "Method", "raw_latex": "We propose a method.", "labels": ["method"]}],
        "bibliography": [entry, copy.deepcopy(entry)],
    }, "arxiv:1234.5678")
    assert len(source["bibliography"]) == 1


def test_observation_contract_preserves_provider_unavailability_not_empty() -> None:
    value = _observations()
    value["candidates"][0]["forward_citation_status"] = "not_available"
    normalized = validate_observations(value)
    assert normalized["candidates"][0]["forward_citation_status"] == "not_available"


def test_candidate_recovers_arxiv_alias_when_canonical_identity_is_doi(tmp_path: Path) -> None:
    selected = _selected("W1", "Generic Topic")
    selected["display"] = "doi:10.1000/example"
    selected["identifier_evidence"] = [
        "arxiv:2401.00001", "doi:10.1000/example", "openalex:w1"
    ]
    candidate = OpenAlexArxivCentralPapersCapability(tmp_path)._candidate(
        selected, accessed_at="2026-07-23T00:00:00+00:00"
    )
    assert candidate["paper_id"] == "doi:10.1000/example"
    assert candidate["identifiers"]["arxiv_id"] == "2401.00001"


def test_source_observation_accepts_bounded_pdf_sections() -> None:
    from research_assistant.survey.central_papers_capability import _source_observation

    value = _source_observation({
        "status": "available",
        "source_type": "oa_pdf_pdftotext",
        "sections": [{
            "anchor_id": "pdf:doi:10.1/x:section-0",
            "title": "Method",
            "text": "We propose a method.",
            "evidence_ref": "oa-pdf:doi:10.1/x:section-0",
        }],
        "bibliography": [],
    }, "doi:10.1/x")
    assert value["status"] == "available"
    assert value["source_type"] == "oa_pdf_pdftotext"
    assert value["sections"][0]["anchor_id"].startswith("pdf:")


def test_oa_pdf_section_truncation_is_utf8_byte_safe() -> None:
    from research_assistant.survey.oa_pdf_source import _utf8_prefix

    value = _utf8_prefix("é" * 100_000, 100_000)
    assert len(value.encode("utf-8")) <= 100_000


def _selected(openalex_id: str, title: str, *, references: list[str] | None = None) -> dict:
    return {
        "paper_key": f"openalex:{openalex_id.casefold()}",
        "display": f"openalex:{openalex_id.casefold()}",
        "identifier_evidence": [f"openalex:{openalex_id.casefold()}"],
        "title_evidence": [title],
        "descriptive": {
            "authors": ["Author"],
            "year": 2024,
            "openalex_id": openalex_id,
            "query_layers": ["broad_facets"],
            "identity_conflict": False,
            "citation_count": 1,
            "venue_metric": {"status": "not_available"},
            "referenced_works": references or [],
            "is_retracted": False,
        },
    }


def test_production_capability_expands_reference_and_citing_rounds(monkeypatch, tmp_path: Path) -> None:
    seed = _selected("W1", "Generic Topic Seed", references=["W2"])
    reference = _selected("W2", "Generic Topic Reference")
    citing = _selected("W3", "Generic Topic Citing Work")

    class Bootstrap:
        name = "fixture_bootstrap"
        version = "fixture-v1"

        def run(self, _mission):
            return {
                "outcome": "selected",
                "selected_candidates": [seed],
                "descriptive": {"budget_consumption": {"metadata_requests": 1, "provider_rows": 1}},
            }

    monkeypatch.setattr(
        "research_assistant.survey.central_papers_capability.OpenAlexTopicBootstrapCapability",
        Bootstrap,
    )
    monkeypatch.setattr(
        OpenAlexArxivCentralPapersCapability,
        "_forward",
        staticmethod(lambda openalex_id: (
            ("available", ["openalex:w3"], [citing])
            if openalex_id == "W1" else ("empty", [], [])
        )),
    )
    monkeypatch.setattr(
        OpenAlexArxivCentralPapersCapability,
        "_work",
        staticmethod(lambda openalex_id: reference if openalex_id == "w2" else None),
    )
    capability = OpenAlexArxivCentralPapersCapability(tmp_path / "cache")
    outcome = capability.collect(build_topic_contract("Generic topic"), DEFAULT_BUDGET)
    by_id = {candidate["paper_id"]: candidate for candidate in outcome["candidates"]}
    assert set(by_id) == {"openalex:w1", "openalex:w2", "openalex:w3"}
    assert by_id["openalex:w2"]["discovery_round"] == 1
    assert by_id["openalex:w2"]["discovery_origins"] == ["openalex:w1"]
    assert by_id["openalex:w2"]["discovery_routes"] == ["broad_facets", "metadata_reference_graph"]
    assert by_id["openalex:w3"]["discovery_routes"] == ["broad_facets", "forward_snowball"]
    assert outcome["budget_consumption"] == {
        "metadata_records": 3,
        "metadata_requests": 5,
        "source_attempts": 0,
        "source_bytes": 0,
    }
