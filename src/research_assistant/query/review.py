from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.query.audit_notes import technical_audit_defaults
from research_assistant.storage.file_store import FileStore

VALID_REVIEW_STATUSES = {'approved', 'needs_review', 'rejected'}


def _summary_paths(root: Path | None = None) -> list[Path]:
    paths = get_paths(root)
    return sorted(paths.summaries.glob('*.json'))


def _summary_with_defaults(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        **summary,
        'technical_audit': {
            **technical_audit_defaults(),
            **(summary.get('technical_audit') or {}),
        },
    }


def list_review_items(*, root: Path | None = None, status: str | None = None) -> list[dict[str, Any]]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    rows = []
    for path in _summary_paths(root):
        rec = PaperRecord.from_dict(store.read_json(path))
        if status and rec.review_status != status:
            continue
        rows.append({
            'paper_id': rec.id,
            'title': rec.title,
            'year': rec.year,
            'review_status': rec.review_status,
            'requires_manual_review': rec.requires_manual_review,
            'metadata_confidence': rec.metadata_confidence,
            'identity_source': rec.identity_source,
            'warnings': rec.review_summary.get('warnings', []),
        })
    return rows


def show_review_item(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    summary = _summary_with_defaults(store.read_json(paths.summaries / f'{paper_id}.json'))
    return {
        'paper_id': paper_id,
        'review_status': summary.get('review_status', 'needs_review'),
        'requires_manual_review': summary.get('requires_manual_review', True),
        'review_summary': summary.get('review_summary', {}),
        'candidate_metadata_sources': summary.get('candidate_metadata_sources', {}),
        'merge_notes': summary.get('merge_notes', []),
        'provenance': summary.get('provenance', {}),
        'summary': summary,
    }


def mark_review_status(paper_id: str, status: str, *, root: Path | None = None) -> dict[str, Any]:
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f'review status must be one of {sorted(VALID_REVIEW_STATUSES)}')
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    summary_path = paths.summaries / f'{paper_id}.json'
    data = _summary_with_defaults(store.read_json(summary_path))
    data['review_status'] = status
    data['requires_manual_review'] = status != 'approved'
    review_summary = dict(data.get('review_summary') or {})
    review_summary['status'] = status
    data['review_summary'] = review_summary
    store.write_json(summary_path, data)
    return data
