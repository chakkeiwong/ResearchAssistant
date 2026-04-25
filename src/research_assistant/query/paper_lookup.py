from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.schemas.audit_record import AuditRecord
from research_assistant.storage.file_store import FileStore
from research_assistant.source.structured_source import source_record_path


def find_paper(
    query: str,
    *,
    root: Path | None = None,
    review_status: str | None = None,
    author: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    q = query.lower()
    author_filter = author.lower() if author else None
    results = []
    for path in sorted(paths.summaries.glob('*.json')):
        rec = PaperRecord.from_dict(store.read_json(path))
        if review_status and rec.review_status != review_status:
            continue
        if year is not None and rec.year != year:
            continue
        if author_filter and not any(author_filter in a.lower() for a in rec.authors):
            continue
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


def _extraction_payload(paper_id: str, metadata: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    extracted_text_path = paths.papers_extracted / f'{paper_id}.txt'
    parser_hints = metadata.get('parser_hints') or {}
    parser_outputs = parser_hints.get('parser_outputs') or []
    limitations = [
        {
            'field': 'equations',
            'status': 'unreliable',
            'note': 'Equations are not yet reliably extracted as structured output.',
        },
        {
            'field': 'citations',
            'status': 'unreliable',
            'note': 'PDF citation extraction is not yet reliable enough to trust as structured output.',
        },
    ]
    warnings = []
    if parser_hints.get('parse_confidence') == 'low':
        warnings.append('parser confidence is low')
    warnings.extend(parser_hints.get('disagreements') or [])
    return {
        'extracted_text_path': str(extracted_text_path) if extracted_text_path.exists() else None,
        'extracted_text_available': extracted_text_path.exists(),
        'consensus_section_headings': parser_hints.get('consensus_section_headings') or [],
        'parser_reconciliation': {
            'parse_confidence': parser_hints.get('parse_confidence', 'low'),
            'requires_manual_review': parser_hints.get('requires_manual_review', True),
            'parser_agreement': parser_hints.get('parser_agreement') or {},
            'disagreements': parser_hints.get('disagreements') or [],
            'parser_outputs_used': [
                {
                    'parser_name': output.get('parser_name'),
                    'parse_status': output.get('parse_status'),
                    'parser_version': output.get('parser_version'),
                    'section_headings': output.get('section_headings') or [],
                    'diagnostics': output.get('diagnostics') or {},
                    'capabilities': output.get('capabilities') or {
                        'section_headings': 'unknown',
                        'equations': 'unknown',
                        'citations': 'unknown',
                    },
                }
                for output in parser_outputs
            ],
        },
        'warnings': warnings,
        'limitations': limitations,
    }


def _source_extraction_payload(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    path = source_record_path(paths.papers_source, paper_id)
    if not path.exists():
        # Absence of source is explicit so callers do not confuse PDF fallback with source-derived evidence.
        return {
            'available': False,
            'primary_source': 'pdf_parser',
            'record_path': None,
            'limitations': [{'field': 'source', 'status': 'unavailable', 'note': 'No structured source artifact is stored for this paper.'}],
        }
    record = FileStore(paths.local_research).read_json(path)
    return {
        'available': record.get('status') == 'available',
        'primary_source': record.get('source_type') if record.get('primary_for_audit') else 'pdf_parser',
        'record_path': str(path),
        'source_type': record.get('source_type'),
        'status': record.get('status'),
        'primary_for_audit': record.get('primary_for_audit', False),
        'artifact_root': record.get('artifact_root'),
        'original_source_path': record.get('original_source_path'),
        'flattened_source_path': record.get('flattened_source_path'),
        'section_count': len(record.get('sections') or []),
        'equation_count': len(record.get('equations') or []),
        'theorem_like_block_count': len(record.get('theorem_like_blocks') or []),
        'citation_count': len(record.get('citations') or []),
        'bibliography_count': len(record.get('bibliography') or []),
        'macro_count': len(record.get('macros') or []),
        'sections': record.get('sections') or [],
        'equations': record.get('equations') or [],
        'theorem_like_blocks': record.get('theorem_like_blocks') or [],
        'labels': record.get('labels') or [],
        'citations': record.get('citations') or [],
        'bibliography': record.get('bibliography') or [],
        'macros': record.get('macros') or [],
        'provenance': record.get('provenance') or {},
        'diagnostics': record.get('diagnostics') or {},
        'limitations': record.get('limitations') or [],
    }


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
    review = {
        'review_status': summary.get('review_status', 'needs_review'),
        'requires_manual_review': summary.get('requires_manual_review', True),
        'review_summary': summary.get('review_summary', {}),
        'provenance': summary.get('provenance', {}),
        'identity_validation': metadata.get('identity_validation', {}),
        'metadata_source_statuses': metadata.get('source_statuses', []),
    }
    extraction = _extraction_payload(paper_id, metadata, root=paths.root)
    source_extraction = _source_extraction_payload(paper_id, root=paths.root)
    # Machine-extracted source evidence stays separate from human-reviewed technical conclusions.
    technical_audit = summary.get('technical_audit') or {
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
    return {
        'review': review,
        'source_extraction': source_extraction,
        'extraction': extraction,
        'pdf_extraction': extraction,
        'technical_audit': technical_audit,
        'metadata': metadata,
        'summary': summary,
        'links': links,
    }


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
