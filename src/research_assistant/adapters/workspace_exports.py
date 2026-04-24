from __future__ import annotations

import json
from pathlib import Path

from research_assistant.config import get_paths
from research_assistant.schemas.paper_record import PaperRecord
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
        papers.append(paper)
    out.write_text(json.dumps({"papers": papers}, indent=2, sort_keys=True))
    return out
