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


def _artifact_family_payload(base: Path, store: FileStore, *, paper_id: str | None = None) -> list[dict]:
    rows = []
    for path in sorted(base.glob('*.json')):
        record = store.read_json(path)
        if paper_id is not None and record.get('paper_id') not in {paper_id, None}:
            continue
        record = dict(record)
        record['record_path'] = str(path)
        rows.append(record)
    return rows


def _review_metadata_payload(paper_id: str, store: FileStore, paths) -> dict:
    path = paths.review_metadata / f'{paper_id}.json'
    if not path.exists():
        return {'available': False, 'record_path': None}
    payload = store.read_json(path)
    payload['available'] = True
    payload['record_path'] = str(path)
    return payload


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
        paper['department_review_metadata'] = _review_metadata_payload(rec.id, store, paths)
        paper['industrial_artifacts'] = {
            'derivations': _artifact_family_payload(paths.derivations, store, paper_id=rec.id),
            'experiments': _artifact_family_payload(paths.experiments, store, paper_id=rec.id),
            'graph_reports': _artifact_family_payload(paths.graph_reports, store, paper_id=rec.id),
            'synthesis': _artifact_family_payload(paths.synthesis, store, paper_id=rec.id),
            'governance': _artifact_family_payload(paths.governance, store, paper_id=rec.id),
            'jobs': _artifact_family_payload(paths.jobs, store, paper_id=rec.id),
            'traceability': _artifact_family_payload(paths.traceability, store, paper_id=rec.id),
        }
        papers.append(paper)
    out.write_text(json.dumps({
        "papers": papers,
        "industrial_library_artifacts": {
            "benchmark_manifests": _artifact_family_payload(paths.benchmarks, store),
            "benchmark_runs": _artifact_family_payload(paths.benchmark_runs, store),
            "model_policies": _artifact_family_payload(paths.model_policies, store),
            "collaboration": _artifact_family_payload(paths.collaboration, store),
            "artifact_indices": _artifact_family_payload(paths.artifact_indices, store),
            "service_contracts": _artifact_family_payload(paths.service_contracts, store),
            "operations": _artifact_family_payload(paths.operations, store),
            "sops": _artifact_family_payload(paths.sops, store),
            "full_scale_planning": [
                artifact for artifact in _artifact_family_payload(paths.governance, store)
                if str(artifact.get("artifact_type") or "").startswith("industrial_full_scale_")
            ],
        },
        "dashboard_contract": {
            "schema_version": "industrial-platform-v1",
            "artifact_families": [
                "derivations",
                "experiments",
                "graph_reports",
                "synthesis",
                "governance",
                "jobs",
                "benchmark_manifests",
                "benchmark_runs",
                "traceability",
                "model_policies",
                "collaboration",
                "artifact_indices",
                "service_contracts",
                "operations",
                "sops",
                "full_scale_planning",
            ],
        },
    }, indent=2, sort_keys=True))
    return out
