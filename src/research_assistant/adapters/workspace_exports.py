from __future__ import annotations

import json
from pathlib import Path

from research_assistant.config import get_paths
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.source.structured_source import source_record_path
from research_assistant.storage.file_store import FileStore


def _technical_audit_defaults() -> dict:
    return {
        'transport_definition': '',
        'objective': '',
        'transformed_target': '',
        'claimed_results': [],
        'derived_results': [],
        'open_questions': [],
        'relevant_equations': [],
        'relevant_sections': [],
        'assumptions_for_reuse': [],
    }


def _source_export_payload(paper_id: str, store: FileStore, paths) -> dict:
    path = source_record_path(paths.papers_source, paper_id)
    if not path.exists():
        return {'available': False, 'record_path': None}
    record = store.read_json(path)
    return {
        'available': record.get('status') == 'available',
        'record_path': str(path),
        'source_type': record.get('source_type'),
        'status': record.get('status'),
        'primary_for_audit': record.get('primary_for_audit', False),
        'artifact_root': record.get('artifact_root'),
        'flattened_source_path': record.get('flattened_source_path'),
        'sections': record.get('sections') or [],
        'equations': record.get('equations') or [],
        'theorem_like_blocks': record.get('theorem_like_blocks') or [],
        'labels': record.get('labels') or [],
        'citations': record.get('citations') or [],
        'bibliography': record.get('bibliography') or [],
        'macros': record.get('macros') or [],
        'provenance': record.get('provenance') or {},
        'limitations': record.get('limitations') or [],
    }


def export_paper_context(output_path: Path | None = None, *, root: Path | None = None, review_status: str | None = None) -> Path:
    paths = get_paths(root)
    out = output_path or (paths.root / 'local_research' / 'paper_context.json')
    papers = []
    store = FileStore(paths.local_research)
    for p in sorted(paths.summaries.glob('*.json')):
        rec = PaperRecord.from_dict(store.read_json(p))
        if review_status and rec.review_status != review_status:
            continue
        paper = rec.to_dict()
        paper['technical_audit'] = {
            **_technical_audit_defaults(),
            **(paper.get('technical_audit') or {}),
        }
        paper['source_extraction'] = _source_export_payload(rec.id, store, paths)
        papers.append(paper)
    out.write_text(json.dumps({"papers": papers}, indent=2, sort_keys=True))
    return out
