from __future__ import annotations

from pathlib import Path

from research_assistant.query.review import list_review_items, mark_review_status, show_review_item


def _write_summary(root: Path, paper_id: str, review_status: str = 'needs_review') -> None:
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True, exist_ok=True)
    (summaries / f'{paper_id}.json').write_text(
        '{'
        f'"id": "{paper_id}", '
        '"title": "A Test Paper", '
        '"authors": ["Alice Example"], '
        '"year": 2024, '
        '"abstract": "", '
        '"main_contribution": "Test contribution", '
        '"curation_status": "draft", '
        '"metadata_confidence": "low", '
        '"identity_source": "parser_consensus", '
        f'"review_status": "{review_status}", '
        '"review_summary": {"status": "needs_review", "warnings": ["metadata confidence is low"]}, '
        '"requires_manual_review": true, '
        '"candidate_metadata_sources": {}, '
        '"merge_notes": ["note"], '
        '"provenance": {"title": "parser_consensus"}'
        '}'
    )


def test_list_review_items_filters_by_status(tmp_path: Path) -> None:
    _write_summary(tmp_path, 'paper_a', 'needs_review')
    _write_summary(tmp_path, 'paper_b', 'approved')
    rows = list_review_items(root=tmp_path, status='needs_review')
    assert [row['paper_id'] for row in rows] == ['paper_a']


def test_show_review_item_exposes_review_metadata(tmp_path: Path) -> None:
    _write_summary(tmp_path, 'paper_a')
    payload = show_review_item('paper_a', root=tmp_path)
    assert payload['review_status'] == 'needs_review'
    assert payload['provenance']['title'] == 'parser_consensus'
    assert payload['merge_notes'] == ['note']


def test_mark_review_status_preserves_provenance(tmp_path: Path) -> None:
    _write_summary(tmp_path, 'paper_a')
    updated = mark_review_status('paper_a', 'approved', root=tmp_path)
    assert updated['review_status'] == 'approved'
    assert updated['requires_manual_review'] is False
    assert updated['review_summary']['status'] == 'approved'
    assert updated['provenance']['title'] == 'parser_consensus'
