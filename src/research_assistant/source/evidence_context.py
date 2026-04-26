from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.source.structured_source import source_record_path
from research_assistant.storage.file_store import FileStore


def _source_record(root: Path | None, paper_id: str) -> tuple[Path, dict[str, Any]]:
    paths = get_paths(root)
    path = source_record_path(paths.papers_source, paper_id)
    if not path.exists():
        raise ValueError(f'no structured source record for {paper_id}')
    return path, FileStore(paths.local_research).read_json(path)


def _find_labeled_block(record: dict[str, Any], label: str) -> tuple[str, dict[str, Any]] | None:
    for block_type, key in [('equation', 'equations'), ('theorem_like_block', 'theorem_like_blocks'), ('section', 'sections')]:
        # Sections inherit nested labels, so prefer the more specific evidence block when labels overlap.
        for block in record.get(key) or []:
            if label in (block.get('labels') or []):
                return block_type, block
    return None


def _containing_section(record: dict[str, Any], line: int | None) -> dict[str, Any] | None:
    if line is None:
        return None
    sections = sorted(record.get('sections') or [], key=lambda section: section.get('line') or 0)
    containing = None
    for section in sections:
        if (section.get('line') or 0) <= line:
            containing = section
        else:
            break
    return containing


def _macro_usage(record: dict[str, Any], raw_latex: str | None) -> list[dict[str, Any]]:
    text = raw_latex or ''
    usages = []
    for macro in record.get('macros') or []:
        name = macro.get('name')
        if name and f'\\{name}' in text:
            usages.append(macro)
    return usages


def evidence_context_for_label(paper_id: str, label: str, *, root: Path | None = None) -> dict[str, Any]:
    path, record = _source_record(root, paper_id)
    match = _find_labeled_block(record, label)
    if match is None:
        raise ValueError(f'no source evidence found for label {label}')
    block_type, block = match
    section = block if block_type == 'section' else _containing_section(record, block.get('line'))
    return {
        'paper_id': paper_id,
        'query': {'label': label},
        'record_path': str(path),
        'source_type': record.get('source_type'),
        'block_type': block_type,
        'block': block,
        'containing_section': section,
        'macro_usages': _macro_usage(record, block.get('raw_latex')),
        'references': [ref for ref in record.get('references') or [] if ref.get('key') == label],
        'limitations': record.get('limitations') or [],
        'provenance': record.get('provenance') or {},
    }


def evidence_context_for_citation(paper_id: str, citation_key: str, *, root: Path | None = None) -> dict[str, Any]:
    path, record = _source_record(root, paper_id)
    citations = [citation for citation in record.get('citations') or [] if citation_key in (citation.get('keys') or [])]
    bibliography = [entry for entry in record.get('bibliography') or [] if entry.get('key') == citation_key]
    if not citations and not bibliography:
        raise ValueError(f'no source evidence found for citation key {citation_key}')
    first_line = citations[0].get('line') if citations else None
    return {
        'paper_id': paper_id,
        'query': {'citation_key': citation_key},
        'record_path': str(path),
        'source_type': record.get('source_type'),
        'block_type': 'citation',
        'citations': citations,
        'bibliography': bibliography,
        'containing_section': _containing_section(record, first_line),
        'limitations': record.get('limitations') or [],
        'provenance': record.get('provenance') or {},
    }
