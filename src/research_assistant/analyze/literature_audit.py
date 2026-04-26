from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.query.audit_notes import technical_audit_defaults
from research_assistant.query.citation_cache import citation_graph_path
from research_assistant.query.paper_lookup import get_paper_summary
from research_assistant.storage.file_store import FileStore


def literature_audit_proposal_path(root: Path | None, paper_id: str) -> Path:
    return get_paths(root).local_research / 'analysis' / 'literature_audit' / f'{paper_id}.json'


def _source_claims(source_extraction: dict[str, Any]) -> list[dict[str, Any]]:
    claims = []
    for block in source_extraction.get('theorem_like_blocks') or []:
        claims.append({
            'kind': block.get('environment', 'theorem_like_block'),
            'labels': block.get('labels') or [],
            'raw_latex': block.get('raw_latex'),
            'line': block.get('line'),
            'review_status': 'requires_human_review',
        })
    return claims


def _method_components(source_extraction: dict[str, Any]) -> dict[str, Any]:
    return {
        'relevant_sections': [
            {'title': section.get('title'), 'labels': section.get('labels') or [], 'line': section.get('line')}
            for section in source_extraction.get('sections') or []
        ],
        'relevant_equations': [
            {'labels': equation.get('labels') or [], 'raw_latex': equation.get('raw_latex'), 'line': equation.get('line')}
            for equation in source_extraction.get('equations') or []
        ],
        'requires_review': True,
    }


def _graph_context(root: Path | None, paper_id: str) -> dict[str, Any]:
    path = citation_graph_path(root, paper_id)
    if not path.exists():
        return {'available': False, 'graph_path': None}
    graph = FileStore(get_paths(root).local_research).read_json(path)
    return {
        'available': True,
        'graph_path': str(path),
        'status': graph.get('status'),
        'status_reason': graph.get('status_reason'),
        'summary': graph.get('summary') or {},
        'diagnostics': graph.get('diagnostics') or {},
    }


def propose_literature_audit(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    summary = get_paper_summary(paper_id, root=root)
    source_extraction = summary.get('source_extraction') or {}
    proposal = {
        'paper_id': paper_id,
        'proposal_id': f'{paper_id}:literature-audit:source-v1',
        'status': 'requires_human_review',
        'paper_claims': _source_claims(source_extraction),
        'method_components': _method_components(source_extraction),
        'assumptions': [],
        'open_questions': ['Review source-derived claims before accepting them as technical audit notes.'],
        'graph_context': _graph_context(root, paper_id),
        'limitations': [
            'This proposal is generated from machine-extracted source evidence and citation metadata.',
            'It must not be treated as a verified mathematical conclusion until reviewed.',
        ],
    }
    path = literature_audit_proposal_path(root, paper_id)
    FileStore(get_paths(root).local_research).write_json(path, proposal)
    return proposal


def show_literature_audit(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return FileStore(get_paths(root).local_research).read_json(literature_audit_proposal_path(root, paper_id))


def approve_literature_audit(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    proposal = show_literature_audit(paper_id, root=root)
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    summary_path = paths.summaries / f'{paper_id}.json'
    summary = store.read_json(summary_path)
    technical_audit = {**technical_audit_defaults(), **(summary.get('technical_audit') or {})}
    for claim in proposal.get('paper_claims') or []:
        raw_latex = (claim.get('raw_latex') or '').strip()
        if raw_latex and raw_latex not in technical_audit['claimed_results']:
            technical_audit['claimed_results'].append(raw_latex)
        for label in claim.get('labels') or []:
            if label not in technical_audit.get('relevant_theorems', []):
                technical_audit.setdefault('relevant_theorems', []).append(label)
    for equation in (proposal.get('method_components') or {}).get('relevant_equations') or []:
        for label in equation.get('labels') or []:
            if label not in technical_audit['relevant_equations']:
                technical_audit['relevant_equations'].append(label)
    provenance = {
        'proposal_id': proposal.get('proposal_id'),
        'status': 'accepted_from_proposal',
        'accepted_fields': ['claimed_results', 'relevant_equations', 'relevant_theorems'],
    }
    technical_audit.setdefault('proposal_provenance', []).append(provenance)
    summary['technical_audit'] = technical_audit
    store.write_json(summary_path, summary)
    proposal['status'] = 'accepted'
    store.write_json(literature_audit_proposal_path(root, paper_id), proposal)
    return {
        'paper_id': paper_id,
        'proposal_id': proposal.get('proposal_id'),
        'updated': True,
        'technical_audit': technical_audit,
        'proposal_status': proposal['status'],
    }
