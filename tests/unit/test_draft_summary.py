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
