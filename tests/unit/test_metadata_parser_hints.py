from __future__ import annotations

from unittest.mock import patch

from research_assistant.ingest.metadata_resolve import merge_metadata, resolve_metadata, choose_best_semanticscholar_result


def test_merge_metadata_preserves_parser_hints() -> None:
    parser_hints = {
        'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
        'parse_confidence': 'medium',
    }
    metadata = merge_metadata(
        'Credit Risk and the Transmission of Interest Rate Shocks Palazzo',
        {'display_name': 'Wrong Paper'},
        {},
        {},
        openalex_candidates=[{'score': 0.3, 'title': 'Wrong Paper'}],
        parser_hints=parser_hints,
    )
    assert metadata['parser_hints'] == parser_hints
    assert metadata['provenance']['parser_consensus'] == 'parse confidence medium'


def test_merge_metadata_preserves_identity_validation_payload() -> None:
    metadata = merge_metadata(
        'Credit Risk and the Transmission of Interest Rate Shocks Palazzo',
        {'display_name': 'Wrong Paper'},
        {},
        {},
        openalex_candidates=[{'score': 0.3, 'title': 'Wrong Paper'}],
        parser_hints={'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks', 'parse_confidence': 'medium'},
    )
    metadata['identity_validation'] = {
        'status': 'conflict',
        'confidence': 'medium',
        'requires_manual_review': True,
        'notes': ['external metadata disagrees with parser consensus'],
    }

    assert metadata['parser_hints']['consensus_title'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert metadata['identity_validation']['status'] == 'conflict'
    assert metadata['identity_validation']['requires_manual_review'] is True


@patch('research_assistant.query.discovery.discover_semanticscholar')
def test_choose_best_semanticscholar_result_scores_candidates_against_parser_hints(mock_discover_semanticscholar) -> None:
    mock_discover_semanticscholar.return_value = [
        {
            'source': 'semanticscholar',
            'source_id': 'sem-123',
            'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'year': 2020,
            'doi': '10.9999/example',
        },
        {
            'source': 'semanticscholar',
            'source_id': 'sem-456',
            'title': 'Different Paper',
            'authors': ['Someone Else'],
            'year': 2019,
            'doi': '10.9999/other',
        },
    ]

    best, candidates = choose_best_semanticscholar_result(
        'Credit Risk and the Transmission of Interest Rate Shocks',
        parser_hints={
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
        },
    )

    assert best['source_id'] == 'sem-123'
    assert candidates[0]['source'] == 'semanticscholar'
    assert candidates[0]['score'] >= candidates[1]['score']


def test_merge_metadata_preserves_semanticscholar_candidates() -> None:
    metadata = merge_metadata(
        'Credit Risk and the Transmission of Interest Rate Shocks',
        {'display_name': 'Credit Risk and the Transmission of Interest Rate Shocks'},
        {},
        {},
        openalex_candidates=[{'score': 0.95, 'title': 'Credit Risk and the Transmission of Interest Rate Shocks'}],
        semanticscholar_candidates=[{'source': 'semanticscholar', 'source_id': 'sem-123', 'title': 'Credit Risk and the Transmission of Interest Rate Shocks', 'score': 0.98}],
        parser_hints={'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks', 'parse_confidence': 'medium'},
    )

    assert metadata['semanticscholar_candidates'][0]['source'] == 'semanticscholar'
    assert metadata['semanticscholar_candidates'][0]['source_id'] == 'sem-123'
