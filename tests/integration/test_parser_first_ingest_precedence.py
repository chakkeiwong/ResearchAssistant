from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.metadata_resolve import merge_metadata
from research_assistant.summarize.draft_summary import build_draft_summary


def test_parser_consensus_controls_canonical_summary_when_metadata_is_weak() -> None:
    wrong_openalex = {
        'display_name': 'House price cycles in emerging economies',
        'publication_year': 2015,
        'authorships': [{'author': {'display_name': 'Alessio Ciarlone'}}],
        'abstract_inverted_index': {'House': [0], 'price': [1], 'cycles': [2]},
        'id': 'https://openalex.org/W2138717870',
        'doi': 'https://doi.org/10.1108/sef-11-2013-0170',
    }
    parser_hints = {
        'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
        'parse_confidence': 'medium',
        'parser_outputs': [
            {
                'parser_name': 'marker',
                'body_markdown': 'Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy',
            }
        ],
    }
    metadata = merge_metadata(
        'Credit Risk and the Transmission of Interest Rate Shocks Palazzo',
        wrong_openalex,
        {},
        {},
        openalex_candidates=[{'score': 0.38, 'title': wrong_openalex['display_name']}],
        parser_hints=parser_hints,
    )
    rec = build_draft_summary('paper_credit', metadata, '')
    assert rec.title == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert rec.authors == ['Berardino Palazzo', 'Ram Yamarthy']
    assert rec.provenance['title'] == 'parser_consensus'
    assert rec.provenance['authors'] == 'parser_consensus'
    assert rec.metadata_confidence == 'low'
