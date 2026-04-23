from __future__ import annotations

import json
from pathlib import Path

from research_assistant.adapters.workspace_exports import export_paper_context


def test_export_paper_context_filters_by_review_status(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True, exist_ok=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Approved Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    (summaries / 'paper_b.json').write_text(json.dumps({
        'id': 'paper_b',
        'title': 'Needs Review Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
    }))

    monkeypatch.chdir(root)
    out = export_paper_context(root / 'filtered.json', root=root, review_status='approved')
    payload = json.loads(out.read_text())

    assert [paper['id'] for paper in payload['papers']] == ['paper_a']
