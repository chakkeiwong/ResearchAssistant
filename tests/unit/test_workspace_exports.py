from __future__ import annotations

import json
from pathlib import Path

from research_assistant.adapters.workspace_exports import export_paper_context


def test_export_paper_context_filters_by_review_status(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True, exist_ok=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Approved Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
        'primary_source_type': 'arxiv_latex',
        'structured_source_status': 'available',
        'technical_audit': {
            'transport_definition': 'A transport map',
            'objective': '',
            'transformed_target': '',
            'claimed_results': ['Claim A'],
            'derived_results': [],
            'open_questions': [],
            'relevant_equations': [],
            'relevant_sections': ['Method'],
            'assumptions_for_reuse': [],
        },
    }))
    (summaries / 'paper_b.json').write_text(json.dumps({
        'id': 'paper_b',
        'title': 'Needs Review Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
    }))

    source_record = root / 'local_research' / 'papers' / 'source' / 'records'
    source_record.mkdir(parents=True, exist_ok=True)
    (source_record / 'paper_a.json').write_text(json.dumps({
        'paper_id': 'paper_a',
        'source_type': 'arxiv_latex',
        'status': 'available',
        'primary_for_audit': True,
        'artifact_root': str(root / 'local_research' / 'papers' / 'source' / 'arxiv' / 'paper_a'),
        'flattened_source_path': str(root / 'local_research' / 'papers' / 'source' / 'arxiv' / 'paper_a' / 'derived' / 'flattened.tex'),
        'sections': [{'title': 'Method', 'line': 10}],
        'equations': [{'labels': ['eq:target'], 'raw_latex': '\\begin{equation}x\\end{equation}'}],
        'theorem_like_blocks': [{'labels': ['thm:main']}],
        'labels': [{'key': 'eq:target'}],
        'citations': [{'keys': ['neal2011mcmc']}],
        'bibliography': [{'key': 'neal2011mcmc'}],
        'macros': [{'name': 'target'}],
        'provenance': {'arxiv_id': '2401.00001'},
        'limitations': [{'field': 'macros', 'status': 'requires_review'}],
    }))

    monkeypatch.chdir(root)
    out = export_paper_context(root / 'filtered.json', root=root, review_status='approved')
    payload = json.loads(out.read_text())

    assert [paper['id'] for paper in payload['papers']] == ['paper_a']
    assert payload['papers'][0]['technical_audit']['transport_definition'] == 'A transport map'
    assert payload['papers'][0]['technical_audit']['claimed_results'] == ['Claim A']
    assert payload['papers'][0]['technical_audit']['relevant_sections'] == ['Method']
    assert payload['papers'][0]['primary_source_type'] == 'arxiv_latex'
    assert payload['papers'][0]['source_extraction']['available'] is True
    assert payload['papers'][0]['source_extraction']['source_type'] == 'arxiv_latex'
    assert payload['papers'][0]['source_extraction']['sections'][0]['title'] == 'Method'
    assert payload['papers'][0]['source_extraction']['equations'][0]['labels'] == ['eq:target']
