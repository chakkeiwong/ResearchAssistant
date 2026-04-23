from __future__ import annotations

from unittest.mock import patch

from research_assistant.ingest.identity_validate import validate_identity


def test_validate_identity_marks_agreement_with_parser_consensus() -> None:
    metadata = {
        'openalex': {
            'display_name': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'publication_year': 2020,
            'authorships': [
                {'author': {'display_name': 'Berardino Palazzo'}},
                {'author': {'display_name': 'Ram Yamarthy'}},
            ],
            'doi': 'https://doi.org/10.9999/example',
            'id': 'https://openalex.org/W123',
        },
        'crossref': {},
        'crossref_candidates': [],
        'openalex_candidates': [
            {
                'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'score': 0.95,
                'year': 2020,
                'source': 'openalex',
                'source_id': 'https://openalex.org/W123',
            }
        ],
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
        },
    }

    rec = validate_identity(metadata)

    assert rec['status'] == 'validated'
    assert rec['confidence'] == 'medium'
    assert rec['requires_manual_review'] is False
    assert rec['best_discovery_match']['title'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert rec['citation_neighborhood']['status'] == 'skipped'


def test_validate_identity_marks_conflict_when_parser_is_strong_and_metadata_disagrees() -> None:
    metadata = {
        'openalex': {
            'display_name': 'House price cycles in emerging economies',
            'publication_year': 2015,
            'authorships': [
                {'author': {'display_name': 'Alessio Ciarlone'}},
            ],
        },
        'crossref': {},
        'crossref_candidates': [],
        'openalex_candidates': [
            {
                'title': 'House price cycles in emerging economies',
                'score': 0.38,
                'year': 2015,
                'source': 'openalex',
            }
        ],
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
        },
    }

    rec = validate_identity(metadata)

    assert rec['status'] == 'conflict'
    assert rec['confidence'] == 'medium'
    assert rec['requires_manual_review'] is True
    assert rec['best_discovery_match']['title'] == 'House price cycles in emerging economies'
    assert rec['citation_neighborhood']['status'] == 'skipped'


def test_validate_identity_returns_insufficient_evidence_without_parser_title() -> None:
    metadata = {
        'openalex': {},
        'crossref': {},
        'openalex_candidates': [],
        'crossref_candidates': [],
        'parser_hints': {
            'consensus_authors': ['Alice Example'],
            'parse_confidence': 'medium',
        },
    }

    rec = validate_identity(metadata)

    assert rec['status'] == 'insufficient_evidence'
    assert rec['candidate_scores'] == []
    assert rec['notes'] == ['no parser consensus title available']


@patch('research_assistant.ingest.identity_validate.citation_neighborhood')
def test_validate_identity_marks_citation_neighborhood_corroborated(mock_citation_neighborhood) -> None:
    mock_citation_neighborhood.return_value = {
        'paper_id': 'sem-123',
        'citing': [{'title': 'Follow-on Paper', 'authors': ['Alice Example'], 'year': 2022, 'source_id': 'sem-456'}],
        'cited': [{'title': 'Prior Paper', 'authors': ['Bob Example'], 'year': 2018, 'source_id': 'sem-789'}],
        'citing_count': 1,
        'cited_count': 1,
        'status': 'available',
    }
    metadata = {
        'openalex': {},
        'crossref': {},
        'openalex_candidates': [
            {
                'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'source': 'semanticscholar',
                'source_id': 'sem-123',
                'authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            }
        ],
        'crossref_candidates': [],
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
        },
    }

    rec = validate_identity(metadata)

    assert rec['status'] == 'validated'
    assert rec['citation_neighborhood']['status'] == 'corroborated'
    assert rec['citation_neighborhood']['candidate_paper_id'] == 'sem-123'
    assert rec['citation_neighborhood']['citing_count'] == 1
    assert rec['citation_neighborhood']['cited_count'] == 1


@patch('research_assistant.ingest.identity_validate.citation_neighborhood')
def test_validate_identity_marks_citation_neighborhood_unavailable(mock_citation_neighborhood) -> None:
    mock_citation_neighborhood.return_value = {
        'paper_id': 'sem-123',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'status': 'unavailable',
    }
    metadata = {
        'openalex': {},
        'crossref': {},
        'openalex_candidates': [
            {
                'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'source': 'semanticscholar',
                'source_id': 'sem-123',
                'authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            }
        ],
        'crossref_candidates': [],
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
        },
    }

    rec = validate_identity(metadata)

    assert rec['status'] == 'validated'
    assert rec['citation_neighborhood']['status'] == 'unavailable'


@patch('research_assistant.ingest.identity_validate.citation_neighborhood')
def test_validate_identity_prefers_semanticscholar_candidates_for_citation_validation(mock_citation_neighborhood) -> None:
    mock_citation_neighborhood.return_value = {
        'paper_id': 'sem-123',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'status': 'empty',
    }
    metadata = {
        'openalex': {
            'display_name': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'publication_year': 2020,
            'authorships': [
                {'author': {'display_name': 'Berardino Palazzo'}},
                {'author': {'display_name': 'Ram Yamarthy'}},
            ],
        },
        'crossref': {},
        'semanticscholar_candidates': [
            {
                'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'source': 'semanticscholar',
                'source_id': 'sem-123',
                'authors': ['Berardino Palazzo', 'Ram Yamarthy'],
                'score': 0.99,
            }
        ],
        'openalex_candidates': [
            {
                'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'source': 'openalex',
                'source_id': 'https://openalex.org/W123',
                'authors': ['Berardino Palazzo', 'Ram Yamarthy'],
                'score': 0.95,
            }
        ],
        'crossref_candidates': [],
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
        },
    }

    rec = validate_identity(metadata)

    assert rec['best_discovery_match']['source'] == 'semanticscholar'
    assert rec['best_discovery_match']['source_id'] == 'sem-123'
    assert rec['citation_neighborhood']['status'] == 'inconclusive'
    mock_citation_neighborhood.assert_called_once_with('sem-123')
