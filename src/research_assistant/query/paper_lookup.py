from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.schemas.audit_record import AuditRecord
from research_assistant.storage.file_store import FileStore


def find_paper(query: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    q = query.lower()
    results = []
    for path in sorted(paths.summaries.glob('*.json')):
        rec = PaperRecord.from_dict(store.read_json(path))
        hay = ' '.join([rec.id, rec.title, rec.abstract, rec.main_contribution]).lower()
        if q in hay:
            results.append({
                'paper_id': rec.id,
                'title': rec.title,
                'year': rec.year,
                'curation_status': rec.curation_status,
                'review_status': rec.review_status,
                'requires_manual_review': rec.requires_manual_review,
            })
    return results


def get_paper_summary(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    summary = store.read_json(paths.summaries / f'{paper_id}.json')
    metadata_path = paths.metadata / f'{paper_id}.json'
    metadata = store.read_json(metadata_path) if metadata_path.exists() else {}
    links = []
    for p in sorted(paths.links.glob('*.json')):
        data = store.read_json(p)
        if data.get('paper_id') == paper_id:
            links.append(data)
    return {'metadata': metadata, 'summary': summary, 'links': links}


def paper_code_links(paper_id: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    return get_paper_summary(paper_id, root=root)['links']


def claim_support_audit(claim: str, paper_ids: list[str], *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    summaries = []
    for paper_id in paper_ids:
        p = paths.summaries / f'{paper_id}.json'
        if p.exists():
            summaries.append(store.read_json(p))
    evidence = [s.get('main_contribution', '') for s in summaries if s.get('main_contribution')]
    classification = 'insufficient_evidence'
    if evidence:
        classification = 'background_only'
    return {
        'classification': classification,
        'evidence': evidence,
        'limitations': ['Current POC audit uses summary-level evidence only.'],
        'confidence': 'low',
    }
