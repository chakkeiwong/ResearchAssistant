from __future__ import annotations

import json
from pathlib import Path

from research_assistant.query.downloads import persist_download_proposal, propose_download


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
