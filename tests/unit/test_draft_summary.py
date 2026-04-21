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
    assert rec.identity_source == 'parser_consensus'
    assert 'openalex_candidates' in rec.candidate_metadata_sources
