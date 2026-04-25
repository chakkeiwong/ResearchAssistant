from __future__ import annotations

from research_assistant.summarize.draft_summary import build_draft_summary


def test_arxiv_authors_take_precedence() -> None:
    metadata = {
        'openalex': {
            'display_name': 'Deep Learning Hamiltonian Monte Carlo',
            'publication_year': 2021,
            'authorships': [
                {'author': {'display_name': 'Xiao-Yong Jin'}},
                {'author': {'display_name': 'Xiao-Yong Jin'}},
                {'author': {'display_name': 'Xiao-Yong Jin'}},
            ],
        },
        'crossref': {},
        'arxiv': {
            'arxiv_id': '2105.03418',
            'title': 'Deep Learning Hamiltonian Monte Carlo',
            'authors': ['Sam Foreman', 'Xiao-Yong Jin', 'James C. Osborn'],
            'abstract': 'Test abstract'
        },
        'metadata_confidence': 'high',
        'merge_notes': [],
        'provenance': {'arxiv': 'exact arxiv id supplied'}
    }
    rec = build_draft_summary('paper_x', metadata, '')
    assert rec.authors == ['Sam Foreman', 'Xiao-Yong Jin', 'James C. Osborn']
    assert rec.provenance['authors'] == 'arxiv'


def test_parser_consensus_overrides_weak_metadata() -> None:
    metadata = {
        'openalex': {
            'display_name': 'House price cycles in emerging economies',
            'publication_year': 2015,
            'authorships': [
                {'author': {'display_name': 'Alessio Ciarlone'}},
            ],
            'abstract_inverted_index': {'House': [0], 'price': [1], 'cycles': [2]},
            'id': 'https://openalex.org/W2138717870',
            'doi': 'https://doi.org/10.1108/sef-11-2013-0170',
        },
        'crossref': {},
        'crossref_candidates': [{'title': 'Credit risk and the transmission of interest rate shocks', 'score': 0.87}],
        'openalex_candidates': [{'title': 'House price cycles in emerging economies', 'score': 0.38}],
        'arxiv': {},
        'metadata_confidence': 'low',
        'merge_notes': ['openalex top candidate has weak similarity; manual review recommended'],
        'provenance': {'openalex': 'best candidate score 0.382'},
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
            'parser_outputs': [
                {'body_markdown': 'Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy\nThe Office of Financial Research working paper ...'}
            ],
        },
    }
    rec = build_draft_summary('paper_credit', metadata, '')
    assert rec.title == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert rec.authors == ['Berardino Palazzo', 'Ram Yamarthy']
    assert rec.provenance['title'] == 'parser_consensus'
    assert rec.provenance['authors'] == 'parser_consensus'
    assert rec.requires_manual_review is True
    assert rec.review_status == 'needs_review'
    assert rec.review_summary['metadata_confidence'] == 'low'
    assert rec.identity_source == 'parser_consensus'
    assert 'openalex_candidates' in rec.candidate_metadata_sources
    assert 'semanticscholar_candidates' in rec.candidate_metadata_sources


def test_parser_consensus_stays_canonical_when_identity_validation_conflicts() -> None:
    metadata = {
        'openalex': {
            'display_name': 'House price cycles in emerging economies',
            'publication_year': 2015,
            'authorships': [
                {'author': {'display_name': 'Alessio Ciarlone'}},
            ],
        },
        'crossref': {},
        'arxiv': {},
        'metadata_confidence': 'low',
        'merge_notes': ['openalex top candidate has weak similarity; manual review recommended'],
        'provenance': {'openalex': 'best candidate score 0.382'},
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
            'parser_outputs': [
                {'body_markdown': 'Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy'}
            ],
        },
        'identity_validation': {
            'status': 'conflict',
            'confidence': 'medium',
            'requires_manual_review': True,
            'citation_neighborhood': {
                'status': 'skipped',
                'reason': 'candidate not validated by title',
            },
            'notes': ['discovery candidate disagrees with parser consensus'],
        },
    }

    rec = build_draft_summary('paper_credit', metadata, '')

    assert rec.title == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert rec.authors == ['Berardino Palazzo', 'Ram Yamarthy']
    assert rec.identity_source == 'parser_consensus'
    assert rec.requires_manual_review is True
    assert rec.review_status == 'conflict'
    assert 'identity validation is conflict' in rec.review_summary['warnings']
    assert rec.provenance['identity_validation'] == 'conflict'
    assert rec.provenance['citation_neighborhood'] == 'skipped'
    assert 'identity validation: conflict' in rec.merge_notes
    assert 'citation neighborhood: skipped' in rec.merge_notes
    assert 'discovery candidate disagrees with parser consensus' in rec.merge_notes


def test_summary_surfaces_citation_neighborhood_status() -> None:
    metadata = {
        'openalex': {},
        'crossref': {},
        'arxiv': {},
        'metadata_confidence': 'low',
        'merge_notes': [],
        'provenance': {},
        'parser_hints': {
            'consensus_title': 'Credit Risk and the Transmission of Interest Rate Shocks',
            'consensus_authors': ['Berardino Palazzo', 'Ram Yamarthy'],
            'parse_confidence': 'medium',
            'parser_outputs': [
                {'body_markdown': 'Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy'}
            ],
        },
        'identity_validation': {
            'status': 'validated',
            'confidence': 'medium',
            'requires_manual_review': False,
            'citation_neighborhood': {
                'status': 'corroborated',
                'candidate_paper_id': 'sem-123',
            },
            'notes': ['external metadata title agrees with parser consensus'],
        },
    }

    rec = build_draft_summary('paper_credit', metadata, '')



def test_summary_initializes_audit_fields() -> None:
    rec = build_draft_summary('paper_credit', {'openalex': {}, 'crossref': {}, 'arxiv': {}}, '')

    assert rec.technical_audit['transport_definition'] == ''
    assert rec.technical_audit['objective'] == ''
    assert rec.technical_audit['transformed_target'] == ''
    assert rec.technical_audit['claimed_results'] == []
    assert rec.technical_audit['derived_results'] == []
    assert rec.technical_audit['open_questions'] == []
    assert rec.technical_audit['relevant_equations'] == []
    assert rec.technical_audit['relevant_sections'] == []
    assert rec.technical_audit['assumptions_for_reuse'] == []


def test_summary_records_structured_source_status() -> None:
    metadata = {
        'openalex': {},
        'crossref': {},
        'arxiv': {
            'arxiv_id': '2401.00001',
            'title': 'Structured Source HMC',
            'authors': ['Alice Example'],
            'abstract': 'Source-first abstract.',
        },
        'metadata_confidence': 'high',
        'structured_source': {
            'source_type': 'arxiv_latex',
            'status': 'available',
            'primary_for_audit': True,
            'record_path': '/tmp/source-record.json',
        },
    }

    rec = build_draft_summary('paper_source', metadata, '')

    assert rec.primary_source_type == 'arxiv_latex'
    assert rec.structured_source_status == 'available'
    assert rec.structured_source_record_path == '/tmp/source-record.json'
