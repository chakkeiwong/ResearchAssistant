from __future__ import annotations

import json
from pathlib import Path

from research_assistant.config import get_paths
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.storage.file_store import FileStore


def export_paper_context(output_path: Path | None = None) -> Path:
    paths = get_paths()
    out = output_path or (paths.root / 'local_research' / 'paper_context.json')
    papers = []
    store = FileStore(paths.local_research)
    for p in sorted(paths.summaries.glob('*.json')):
        papers.append(store.read_json(p))
    out.write_text(json.dumps({"papers": papers}, indent=2, sort_keys=True))
    return out
