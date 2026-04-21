from __future__ import annotations

from research_assistant.ingest.metadata_resolve import merge_metadata, resolve_metadata


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
