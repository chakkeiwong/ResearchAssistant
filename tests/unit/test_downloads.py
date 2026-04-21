from __future__ import annotations

from pathlib import Path

from research_assistant.query.downloads import propose_download


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
