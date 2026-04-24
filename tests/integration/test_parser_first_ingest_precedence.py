from __future__ import annotations

import json
from unittest.mock import patch

from research_assistant.ingest.metadata_resolve import merge_metadata
from research_assistant.ingest.identity_validate import validate_identity
from research_assistant.ingest.parser_orchestrator import reconcile_parsed_documents
from research_assistant.schemas.parsed_document import ParsedDocument
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


@patch('research_assistant.ingest.identity_validate.citation_neighborhood')
def test_semanticscholar_candidate_corroborates_without_replacing_parser_identity(mock_citation_neighborhood) -> None:
    mock_citation_neighborhood.return_value = {
        'paper_id': 'sem-123',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'status': 'empty',
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
        {'display_name': 'House price cycles in emerging economies', 'publication_year': 2015},
        {},
        {},
        openalex_candidates=[{'score': 0.38, 'title': 'House price cycles in emerging economies'}],
        semanticscholar_candidates=[
            {
                'source': 'semanticscholar',
                'source_id': 'sem-123',
                'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'authors': ['Berardino Palazzo', 'Ram Yamarthy'],
                'score': 1.0,
            }
        ],
        parser_hints=parser_hints,
    )
    metadata['identity_validation'] = validate_identity(metadata)

    rec = build_draft_summary('paper_credit', metadata, '')



def test_reconciled_parser_outputs_include_capability_limits() -> None:
    reconciled = reconcile_parsed_documents([
        ParsedDocument(
            parser_name='marker',
            parser_version='0.1',
            title_candidates=['Credit Risk and the Transmission of Interest Rate Shocks'],
            authors=['Berardino Palazzo', 'Ram Yamarthy'],
            section_headings=['Introduction', 'Method'],
            body_markdown='Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy',
            parse_status='ok',
        ),
        ParsedDocument(
            parser_name='pdftotext',
            parser_version='1.0',
            title_candidates=['Credit Risk and the Transmission of Interest Rate Shocks'],
            authors=['Berardino Palazzo'],
            section_headings=['Introduction'],
            body_text='Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo',
            parse_status='ok',
        ),
    ])

    marker_output = next(row for row in reconciled.parser_outputs if row['parser_name'] == 'marker')
    pdftotext_output = next(row for row in reconciled.parser_outputs if row['parser_name'] == 'pdftotext')

    assert marker_output['capabilities']['section_headings'] == 'partial'
    assert marker_output['capabilities']['equations'] == 'unreliable'
    assert marker_output['capabilities']['citations'] == 'unreliable'
    assert pdftotext_output['capabilities']['section_headings'] == 'partial'


