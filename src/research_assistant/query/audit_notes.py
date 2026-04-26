from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.source.structured_source import source_record_path
from research_assistant.storage.file_store import FileStore

SCALAR_AUDIT_FIELDS = {'transport_definition', 'objective', 'transformed_target'}
LIST_AUDIT_FIELDS = {
    'claimed_results',
    'derived_results',
    'open_questions',
    'relevant_equations',
    'relevant_theorems',
    'relevant_citations',
    'relevant_sections',
    'assumptions_for_reuse',
}
def technical_audit_defaults() -> dict[str, Any]:
    return {
        'transport_definition': '',
        'objective': '',
        'transformed_target': '',
        'claimed_results': [],
        'derived_results': [],
        'open_questions': [],
        'relevant_equations': [],
        'relevant_theorems': [],
        'relevant_citations': [],
        'relevant_sections': [],
        'assumptions_for_reuse': [],
        'proposal_provenance': [],
    }


def _summary_path(root: Path | None, paper_id: str) -> Path:
    return get_paths(root).summaries / f'{paper_id}.json'


def _load_summary(root: Path | None, paper_id: str) -> tuple[FileStore, Path, dict[str, Any]]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    path = _summary_path(root, paper_id)
    summary = store.read_json(path)
    summary['technical_audit'] = {**technical_audit_defaults(), **(summary.get('technical_audit') or {})}
    return store, path, summary


def _audit_response(paper_id: str, summary: dict[str, Any], *, updated: bool, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        'paper_id': paper_id,
        'updated': updated,
        'technical_audit': summary['technical_audit'],
        'warnings': warnings or [],
    }


def show_audit_notes(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    _, _, summary = _load_summary(root, paper_id)
    return _audit_response(paper_id, summary, updated=False)


def set_audit_note(paper_id: str, field: str, value: str, *, root: Path | None = None) -> dict[str, Any]:
    if field not in SCALAR_AUDIT_FIELDS:
        raise ValueError(f'audit-note set field must be one of {sorted(SCALAR_AUDIT_FIELDS)}')
    store, path, summary = _load_summary(root, paper_id)
    summary['technical_audit'][field] = value
    store.write_json(path, summary)
    return _audit_response(paper_id, summary, updated=True)


def append_audit_note(paper_id: str, field: str, value: str, *, root: Path | None = None) -> dict[str, Any]:
    if field not in LIST_AUDIT_FIELDS:
        raise ValueError(f'audit-note append field must be one of {sorted(LIST_AUDIT_FIELDS)}')
    store, path, summary = _load_summary(root, paper_id)
    values = list(summary['technical_audit'].get(field) or [])
    if value not in values:
        values.append(value)
    summary['technical_audit'][field] = values
    store.write_json(path, summary)
    return _audit_response(paper_id, summary, updated=True)


def _source_record(root: Path | None, paper_id: str) -> dict[str, Any] | None:
    paths = get_paths(root)
    path = source_record_path(paths.papers_source, paper_id)
    if not path.exists():
        return None
    return FileStore(paths.local_research).read_json(path)


def _label_exists(record: dict[str, Any], key: str, label: str) -> bool:
    return any(label in (block.get('labels') or []) for block in record.get(key) or [])


def link_audit_source_label(paper_id: str, label: str, *, kind: str, root: Path | None = None) -> dict[str, Any]:
    if kind not in {'section', 'equation', 'theorem'}:
        raise ValueError('audit-note source label kind must be section, equation, or theorem')
    warnings = []
    record = _source_record(root, paper_id)
    if record is not None:
        key = {'section': 'sections', 'equation': 'equations', 'theorem': 'theorem_like_blocks'}[kind]
        if not _label_exists(record, key, label):
            raise ValueError(f'no structured-source {kind} label {label}')
    else:
        warnings.append('no structured source record found; label was not validated')
    field = {'section': 'relevant_sections', 'equation': 'relevant_equations', 'theorem': 'relevant_theorems'}[kind]
    response = append_audit_note(paper_id, field, label, root=root)
    response['warnings'].extend(warnings)
    return response


def link_audit_citation_key(paper_id: str, citation_key: str, *, root: Path | None = None) -> dict[str, Any]:
    warnings = []
    record = _source_record(root, paper_id)
    if record is not None:
        in_citations = any(citation_key in (citation.get('keys') or []) for citation in record.get('citations') or [])
        in_bibliography = any(citation_key == entry.get('key') for entry in record.get('bibliography') or [])
        if not in_citations and not in_bibliography:
            raise ValueError(f'no structured-source citation key {citation_key}')
    else:
        warnings.append('no structured source record found; citation key was not validated')
    response = append_audit_note(paper_id, 'relevant_citations', citation_key, root=root)
    response['warnings'].extend(warnings)
    return response


def remove_audit_note(paper_id: str, field: str, value: str, *, root: Path | None = None) -> dict[str, Any]:
    if field not in LIST_AUDIT_FIELDS:
        raise ValueError(f'audit-note remove field must be one of {sorted(LIST_AUDIT_FIELDS)}')
    store, path, summary = _load_summary(root, paper_id)
    values = [item for item in list(summary['technical_audit'].get(field) or []) if item != value]
    summary['technical_audit'][field] = values
    store.write_json(path, summary)
    return _audit_response(paper_id, summary, updated=True)
