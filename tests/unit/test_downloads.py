from __future__ import annotations

import json
from pathlib import Path

from research_assistant.query.downloads import list_download_proposals, persist_download_proposal, propose_download, show_download_proposal


def test_propose_download_uses_inbox_path(tmp_path: Path) -> None:
    proposal = propose_download(
        {
            'title': 'A Test Paper',
            'source': 'semanticscholar',
            'open_access_pdf_url': 'https://example.com/paper.pdf',
        },
        root=tmp_path,
    )
    assert proposal.proposed_name == 'a_test_paper.pdf'
    assert str(proposal.inbox_path).endswith('local_research/inbox/a_test_paper.pdf')


def test_propose_download_preserves_query_and_result(tmp_path: Path) -> None:
    result = {
        'title': 'A Test Paper',
        'source': 'semanticscholar',
        'open_access_pdf_url': 'https://example.com/paper.pdf',
    }
    proposal = propose_download(result, root=tmp_path, query='test query')
    data = proposal.to_dict()
    assert data['schema_version'] == 1
    assert data['query'] == 'test query'
    assert data['result'] == result
    assert data['duplicate_status'] == 'unique'
    assert data['duplicate_candidates'] == []


def test_propose_download_marks_existing_summary_duplicates(tmp_path: Path) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'A Test Paper',
        'authors': ['Alice Example'],
        'year': 2024,
        'doi': '10.123/test',
        'abstract': '',
        'main_contribution': '',
    }))
    result = {
        'title': 'A Test Paper',
        'source': 'semanticscholar',
        'doi': '10.123/test',
        'open_access_pdf_url': 'https://example.com/paper.pdf',
    }

    proposal = propose_download(result, root=tmp_path, query='test query')
    data = proposal.to_dict()

    assert data['duplicate_status'] == 'possible_duplicate'
    assert data['duplicate_candidates'][0]['paper_id'] == 'paper_a'
    assert set(data['duplicate_candidates'][0]['reasons']) == {'doi', 'title'}


def test_persist_download_proposal_writes_inbox_metadata(tmp_path: Path) -> None:
    result = {
        'title': 'A Test Paper',
        'source': 'semanticscholar',
        'open_access_pdf_url': 'https://example.com/paper.pdf',
    }
    proposal = propose_download(result, root=tmp_path, query='test query')

    path = persist_download_proposal(proposal, root=tmp_path)

    assert str(path).endswith('local_research/inbox/metadata/a_test_paper.proposal.json')
    data = json.loads(path.read_text())
    assert data['schema_version'] == 1
    assert data['query'] == 'test query'
    assert data['proposed_name'] == 'a_test_paper.pdf'
    assert data['result']['open_access_pdf_url'] == 'https://example.com/paper.pdf'


def test_list_and_show_download_proposals(tmp_path: Path) -> None:
    result = {
        'title': 'A Test Paper',
        'source': 'semanticscholar',
        'open_access_pdf_url': 'https://example.com/paper.pdf',
    }
    proposal = propose_download(result, root=tmp_path, query='test query')
    persist_download_proposal(proposal, root=tmp_path)

    rows = list_download_proposals(root=tmp_path, duplicate_status='unique')
    assert rows[0]['proposed_name'] == 'a_test_paper.pdf'
    assert rows[0]['duplicate_status'] == 'unique'
    assert rows[0]['duplicate_count'] == 0

    shown = show_download_proposal('a_test_paper.pdf', root=tmp_path)
    assert shown['query'] == 'test query'
    assert shown['result'] == result
    assert shown['duplicate_candidates'] == []
    assert shown['review_summary']['duplicate_status'] == 'unique'
    assert shown['review_summary']['duplicate_count'] == 0
