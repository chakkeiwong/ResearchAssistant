from __future__ import annotations

import json
from pathlib import Path

from research_assistant.cli import main


def _write_summary(root: Path, paper_id: str = 'paper_a') -> None:
    summaries = root / 'local_research' / 'summaries'
    metadata = root / 'local_research' / 'metadata'
    source_records = root / 'local_research' / 'papers' / 'source' / 'records'
    summaries.mkdir(parents=True, exist_ok=True)
    metadata.mkdir(parents=True, exist_ok=True)
    source_records.mkdir(parents=True, exist_ok=True)
    (summaries / f'{paper_id}.json').write_text(json.dumps({
        'id': paper_id,
        'title': 'Industrial Audit Fixture',
        'authors': ['Ada Example'],
        'year': 2026,
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
        'technical_audit': {
            'claimed_results': [],
            'derived_results': [],
            'open_questions': [],
            'relevant_equations': [],
            'relevant_sections': [],
            'assumptions_for_reuse': [],
        },
    }))
    (metadata / f'{paper_id}.json').write_text(json.dumps({'identity_validation': {'status': 'fixture'}}))
    (source_records / f'{paper_id}.json').write_text(json.dumps({
        'paper_id': paper_id,
        'status': 'available',
        'source_type': 'fixture_latex',
        'primary_for_audit': True,
        'sections': [{'title': 'Method', 'labels': ['sec:method'], 'line': 7}],
        'equations': [{'labels': ['eq:target'], 'raw_latex': 'p(x)', 'line': 9}],
        'theorem_like_blocks': [{'labels': ['thm:main'], 'raw_latex': 'Theorem text'}],
        'labels': [{'key': 'sec:method'}, {'key': 'eq:target'}, {'key': 'thm:main'}],
        'citations': [],
        'bibliography': [],
        'macros': [],
        'provenance': {'fixture': True},
        'limitations': [],
    }))


def _json_out(capsys) -> dict | list:
    return json.loads(capsys.readouterr().out)


def test_industrial_phase_zero_paths_and_domain_templates(tmp_path: Path, capsys) -> None:
    rc = main(['--root', str(tmp_path), 'artifact-paths'])
    paths = _json_out(capsys)
    assert rc == 0
    assert paths['derivations'].endswith('local_research/analysis/derivations')
    assert paths['jobs'].endswith('local_research/jobs')

    rc = main(['--root', str(tmp_path), 'domain-templates', 'list'])
    templates = _json_out(capsys)
    assert rc == 0
    assert any(row['template_id'] == 'hmc_mcmc' for row in templates)

    rc = main(['--root', str(tmp_path), 'domain-templates', 'show', '--template-id', 'neural_transport_flows'])
    template = _json_out(capsys)
    assert rc == 0
    assert template['concepts']
    assert template['claims']
    assert template['checklist']
    assert template['concept_taxonomy']
    assert template['assumption_classes']
    assert template['notation_registry']
    assert template['method_families']


def test_derivation_experiment_synthesis_governance_and_export_cycle(tmp_path: Path, capsys) -> None:
    _write_summary(tmp_path)

    rc = main([
        '--root', str(tmp_path), 'derivation', 'create',
        '--paper-id', 'paper_a',
        '--title', 'Target preservation worksheet',
        '--template-id', 'neural_transport_flows',
    ])
    derivation = _json_out(capsys)
    assert rc == 0
    assert derivation['artifact_type'] == 'derivation_worksheet'
    assert derivation['requires_human_review'] is True
    assert derivation['accepted_into_technical_audit'] is False

    rc = main([
        '--root', str(tmp_path), 'derivation', 'append',
        '--artifact-id', derivation['artifact_id'],
        '--field', 'paper_claims',
        '--value', 'The map preserves the target after correction.',
    ])
    derivation = _json_out(capsys)
    assert rc == 0
    assert derivation['paper_claims'][0]['review_status'] == 'requires_human_review'

    claim_id = derivation['paper_claims'][0]['id']

    rc = main([
        '--root', str(tmp_path), 'derivation', 'notation',
        '--artifact-id', derivation['artifact_id'],
        '--symbol', 'T',
        '--meaning', 'transport map',
    ])
    derivation = _json_out(capsys)
    assert rc == 0
    assert derivation['notation_registry']['T']['review_status'] == 'requires_human_review'

    rc = main([
        '--root', str(tmp_path), 'derivation', 'link-steps',
        '--artifact-id', derivation['artifact_id'],
        '--step-id', claim_id,
        '--depends-on', 'assumption_support',
    ])
    derivation = _json_out(capsys)
    assert rc == 0
    assert derivation['step_dependencies'][0]['depends_on'] == 'assumption_support'

    rc = main([
        '--root', str(tmp_path), 'derivation', 'comment',
        '--artifact-id', derivation['artifact_id'],
        '--target-id', claim_id,
        '--comment', 'Check the Jacobian convention.',
        '--reviewer', 'reviewer_a',
    ])
    derivation = _json_out(capsys)
    assert rc == 0
    assert derivation['reviewer_comments'][0]['reviewer'] == 'reviewer_a'

    rc = main([
        '--root', str(tmp_path), 'experiment', 'create',
        '--paper-id', 'paper_a',
        '--claim-id', claim_id,
        '--checklist-id', 'gradient_checks',
    ])
    experiment = _json_out(capsys)
    assert rc == 0
    assert experiment['claim_id'] == claim_id
    assert experiment['checklist']
    assert experiment['requires_human_review'] is True

    rc = main([
        '--root', str(tmp_path), 'experiment', 'record-run',
        '--artifact-id', experiment['artifact_id'],
        '--run-label', 'local-smoke',
        '--seed', '123',
        '--environment', 'pytest-fixture',
        '--diagnostic', 'finite difference agrees',
        '--result-summary', 'smoke run only',
        '--dataset-hash', 'datahash',
        '--model-hash', 'modelhash',
    ])
    experiment = _json_out(capsys)
    assert rc == 0
    assert experiment['result_records'][0]['seed'] == '123'
    assert experiment['result_records'][0]['review_status'] == 'requires_human_review'

    rc = main([
        '--root', str(tmp_path), 'experiment', 'link-claim',
        '--paper-id', 'paper_a',
        '--claim-id', claim_id,
        '--experiment-id', experiment['artifact_id'],
    ])
    link = _json_out(capsys)
    assert rc == 0
    assert link['relationship'] == 'claim-to-experiment'
    assert link['review_status'] == 'requires_human_review'

    rc = main([
        '--root', str(tmp_path), 'synthesis', 'propose',
        '--paper-id', 'paper_a',
        '--kind', 'assumptions_matrix',
    ])
    synthesis = _json_out(capsys)
    assert rc == 0
    assert synthesis['artifact_type'] == 'synthesis_proposal'
    assert synthesis['evidence_refs']
    assert synthesis['accepted_into_technical_audit'] is False

    rc = main(['--root', str(tmp_path), 'governance', 'build', '--paper-id', 'paper_a'])
    governance = _json_out(capsys)
    assert rc == 0
    assert governance['offline_safe'] is True
    assert governance['provider_model_policy']['live_model_calls_allowed'] is False
    assert 'summary' in governance['artifact_hashes']

    rc = main(['--root', str(tmp_path), 'model-policy', 'create', '--policy-id', 'default_llm_policy'])
    model_policy = _json_out(capsys)
    assert rc == 0
    assert model_policy['live_model_calls_allowed'] is False

    rc = main(['--root', str(tmp_path), 'model-policy', 'check-synthesis', '--policy-id', 'default_llm_policy'])
    policy_check = _json_out(capsys)
    assert rc == 0
    assert policy_check['status'] == 'blocked'

    out = tmp_path / 'context.json'
    rc = main(['--root', str(tmp_path), 'export-context', '--output', str(out)])
    assert rc == 0
    capsys.readouterr()
    exported = json.loads(out.read_text())
    artifacts = exported['papers'][0]['industrial_artifacts']
    assert artifacts['derivations'][0]['artifact_id'] == derivation['artifact_id']
    assert artifacts['experiments'][0]['artifact_id'] == experiment['artifact_id']
    assert artifacts['synthesis'][0]['artifact_id'] == synthesis['artifact_id']
    assert artifacts['governance'][0]['artifact_id'] == governance['artifact_id']
    assert exported['industrial_library_artifacts']['model_policies'][0]['artifact_id'] == 'default_llm_policy'
    assert exported['papers'][0]['technical_audit']['claimed_results'] == []
    assert 'benchmark_manifests' in exported['industrial_library_artifacts']


def test_graph_review_benchmark_link_and_job_scaffolds(tmp_path: Path, capsys) -> None:
    _write_summary(tmp_path)
    graph_dir = tmp_path / 'local_research' / 'graphs' / 'citations'
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / 'paper_a.json').write_text(json.dumps({
        'seed_paper_id': 'paper_a',
        'nodes': {
            'paper_a': {'title': 'Seed'},
            'doi:10.1/example': {'title': 'Neighbor', 'doi': '10.1/example'},
            'openalex:W1': {'title': 'Neighbor', 'doi': '10.1/example'},
        },
        'edges': [{'source': 'doi:10.1/example', 'target': 'paper_a', 'direction': 'citing'}],
        'diagnostics': {'node_count': 3},
    }))

    rc = main(['--root', str(tmp_path), 'graph-report', 'build', '--paper-id', 'paper_a'])
    graph_report = _json_out(capsys)
    assert rc == 0
    assert graph_report['node_dedup_diagnostics']['duplicate_identifiers']
    assert graph_report['citation_intents'][0]['intent'] == 'unknown'

    rc = main(['--root', str(tmp_path), 'graph-report', 'enrich', '--artifact-id', graph_report['artifact_id']])
    graph_report = _json_out(capsys)
    assert rc == 0
    assert graph_report['graph_analytics']['review_status'] == 'requires_human_review'
    assert graph_report['citation_intents'][0]['intent_candidates']

    rc = main([
        '--root', str(tmp_path), 'review-meta', 'set',
        '--paper-id', 'paper_a',
        '--field', 'owner',
        '--value', 'math-finance',
    ])
    review_meta = _json_out(capsys)
    assert rc == 0
    assert review_meta['owner'] == 'math-finance'
    assert review_meta['review_history']

    rc = main([
        '--root', str(tmp_path), 'benchmark-manifest', 'create',
        '--manifest-id', 'synthetic_family',
        '--family', 'synthetic',
        '--fixture', str(Path.cwd() / 'tests/fixtures/benchmark_papers/synthetic/synthetic_transport_simple.expected.json'),
    ])
    manifest = _json_out(capsys)
    assert rc == 0
    assert manifest['artifact_type'] == 'benchmark_manifest'

    rc = main(['--root', str(tmp_path), 'benchmark-manifest', 'run', '--manifest-id', 'synthetic_family'])
    run = _json_out(capsys)
    assert rc == 0
    assert run['status'] == 'passed'
    assert 'missing_expected_fields' in run['results'][0]['limitation_taxonomy']
    assert run['results'][0]['quality_scores']['title']['status'] == 'passed'

    rc = main([
        '--root', str(tmp_path), 'link-add',
        '--paper-id', 'paper_a',
        '--relationship', 'equation-to-code',
        '--target-type', 'code_file',
        '--target', 'src/example.py',
        '--source-type', 'equation',
        '--source-ref', 'eq:target',
        '--target-ref', 'src/example.py:10',
    ])
    link_id = capsys.readouterr().out.strip()
    assert rc == 0
    link_path = tmp_path / 'local_research' / 'links' / f'{link_id}.json'
    link_payload = json.loads(link_path.read_text())
    assert link_payload['review_status'] == 'requires_human_review'
    assert link_payload['source_ref'] == 'eq:target'

    rc = main(['--root', str(tmp_path), 'traceability', 'build', '--paper-id', 'paper_a'])
    traceability = _json_out(capsys)
    assert rc == 0
    assert traceability['coverage']['equation-to-code']['count'] == 1
    assert traceability['requires_human_review'] is True

    rc = main(['--root', str(tmp_path), 'job', 'create', '--job-type', 'dashboard-refresh', '--paper-id', 'paper_a'])
    job = _json_out(capsys)
    assert rc == 0
    assert job['artifact_type'] == 'job_status'
    assert job['status'] == 'queued'

    rc = main(['--root', str(tmp_path), 'collaboration', 'create', '--workspace-id', 'dept_workspace'])
    collaboration = _json_out(capsys)
    assert rc == 0
    assert collaboration['artifact_type'] == 'department_collaboration_workspace'

    rc = main([
        '--root', str(tmp_path), 'collaboration', 'update',
        '--workspace-id', 'dept_workspace',
        '--action', 'assign',
        '--target', 'paper_a',
        '--value', 'reviewer_a',
    ])
    collaboration = _json_out(capsys)
    assert rc == 0
    assert collaboration['event_history'][0]['action'] == 'assign'

    rc = main(['--root', str(tmp_path), 'operations-policy', 'create'])
    operations = _json_out(capsys)
    assert rc == 0
    assert operations['offline_safe'] is True
    assert operations['network_authorized'] is False

    rc = main(['--root', str(tmp_path), 'sop', 'create'])
    sop = _json_out(capsys)
    assert rc == 0
    assert 'paper_approval' in sop['sections']
    assert sop['requires_human_review'] is True

    rc = main(['--root', str(tmp_path), 'tool-contract', 'export'])
    contract = _json_out(capsys)
    assert rc == 0
    assert contract['commands']
    assert 'trust_boundary' in contract

    rc = main(['--root', str(tmp_path), 'artifact-index', 'build'])
    index = _json_out(capsys)
    assert rc == 0
    assert index['inventory']['traceability']['count'] == 1
    assert index['inventory']['collaboration']['count'] == 1

    out = tmp_path / 'dashboard.json'
    rc = main(['--root', str(tmp_path), 'dashboard-export', '--output', str(out)])
    assert rc == 0
    capsys.readouterr()
    dashboard = json.loads(out.read_text())
    assert dashboard['counts']['jobs'] == 1
    assert dashboard['counts']['traceability'] == 1
    assert dashboard['counts']['collaboration'] == 1
    assert dashboard['schema_version'] == 'industrial-platform-v1'
    assert dashboard['artifact_paths']['graph_reports'].endswith('citation_graph_reports')


def test_industrial_validation_index_readiness_and_dashboard(tmp_path: Path, capsys) -> None:
    _write_summary(tmp_path)

    rc = main([
        '--root', str(tmp_path), 'derivation', 'create',
        '--paper-id', 'paper_a',
        '--title', 'Industrial validation worksheet',
    ])
    derivation = _json_out(capsys)
    assert rc == 0

    rc = main([
        '--root', str(tmp_path), 'derivation', 'append',
        '--artifact-id', derivation['artifact_id'],
        '--field', 'paper_claims',
        '--value', 'The estimator is stable.',
    ])
    derivation = _json_out(capsys)
    claim_id = derivation['paper_claims'][0]['id']
    assert derivation['dependency_validation']['status'] == 'ready_for_review'

    rc = main([
        '--root', str(tmp_path), 'derivation', 'link-steps',
        '--artifact-id', derivation['artifact_id'],
        '--step-id', claim_id,
        '--depends-on', 'missing_assumption_id',
    ])
    derivation = _json_out(capsys)
    assert rc == 0
    assert derivation['dependency_validation']['status'] == 'blocked'
    assert derivation['dependency_validation']['blocker_count'] == 1

    rc = main([
        '--root', str(tmp_path), 'experiment', 'create',
        '--paper-id', 'paper_a',
        '--claim-id', claim_id,
        '--checklist-id', 'simulation_recovery',
    ])
    experiment = _json_out(capsys)
    assert rc == 0

    rc = main([
        '--root', str(tmp_path), 'experiment', 'record-run',
        '--artifact-id', experiment['artifact_id'],
        '--run-label', 'missing-hashes',
        '--seed', '7',
        '--environment', 'pytest-fixture',
    ])
    experiment = _json_out(capsys)
    assert rc == 0
    evidence = experiment['reproducibility_evidence']
    assert evidence['status'] == 'blocked'
    assert 'dataset_hash' in evidence['run_scores'][0]['missing_fields']

    existing_code = tmp_path / 'src' / 'example.py'
    existing_code.parent.mkdir(parents=True)
    existing_code.write_text('def example():\n    return True\n')
    rc = main([
        '--root', str(tmp_path), 'link-add',
        '--paper-id', 'paper_a',
        '--relationship', 'equation-to-code',
        '--target-type', 'code_file',
        '--target', 'src/example.py',
        '--source-type', 'equation',
        '--source-ref', 'eq:target',
    ])
    assert rc == 0
    capsys.readouterr()
    rc = main([
        '--root', str(tmp_path), 'link-add',
        '--paper-id', 'paper_a',
        '--relationship', 'theorem-assumption-to-test',
        '--target-type', 'test_file',
        '--target', 'tests/missing_test.py',
        '--source-type', 'theorem',
        '--source-ref', 'thm:main',
    ])
    assert rc == 0
    capsys.readouterr()

    rc = main(['--root', str(tmp_path), 'traceability', 'build', '--paper-id', 'paper_a'])
    traceability = _json_out(capsys)
    assert rc == 0
    assert traceability['coverage']['equation-to-code']['existing_target_count'] == 1
    assert traceability['target_health']['missing_target_count'] == 1
    assert traceability['target_health']['status'] == 'blocked'

    incomplete_fixture = tmp_path / 'incomplete.expected.json'
    incomplete_fixture.write_text(json.dumps({'title': 'Only Title'}))
    rc = main([
        '--root', str(tmp_path), 'benchmark-manifest', 'create',
        '--manifest-id', 'incomplete_family',
        '--family', 'synthetic',
        '--fixture', str(incomplete_fixture),
    ])
    manifest = _json_out(capsys)
    assert rc == 0
    assert manifest['artifact_id'] == 'incomplete_family'

    rc = main(['--root', str(tmp_path), 'benchmark-manifest', 'run', '--manifest-id', 'incomplete_family'])
    benchmark_run = _json_out(capsys)
    assert rc == 0
    assert benchmark_run['status'] == 'failed'
    assert 'insufficient_score' in benchmark_run['results'][0]['limitation_taxonomy']

    rc = main(['--root', str(tmp_path), 'model-policy', 'create', '--policy-id', 'default_llm_policy'])
    policy = _json_out(capsys)
    assert rc == 0
    assert policy['live_model_calls_allowed'] is False

    rc = main(['--root', str(tmp_path), 'governance', 'build', '--paper-id', 'paper_a'])
    governance = _json_out(capsys)
    assert rc == 0
    assert governance['offline_safe'] is True

    rc = main(['--root', str(tmp_path), 'sop', 'create'])
    sop = _json_out(capsys)
    assert rc == 0
    assert sop['sections']['benchmark_gates']

    invalid_dir = tmp_path / 'local_research' / 'analysis' / 'synthesis'
    invalid_dir.mkdir(parents=True, exist_ok=True)
    (invalid_dir / 'invalid.json').write_text(json.dumps({
        'schema_version': 'old',
        'artifact_id': 'invalid',
        'artifact_type': 'synthesis_proposal',
        'paper_id': 'paper_a',
        'created_at': '2026-04-27T00:00:00+00:00',
        'provenance': {},
        'review_status': 'approved',
        'requires_human_review': False,
        'limitations': [],
        'accepted_into_technical_audit': True,
    }))
    (invalid_dir / 'malformed.json').write_text('{not-json')

    rc = main(['--root', str(tmp_path), 'industrial-validate'])
    validation = _json_out(capsys)
    assert rc == 0
    assert validation['status'] == 'blocked'
    assert validation['issue_counts']['blockers'] >= 1
    issue_codes = {issue['code'] for record in validation['records'] for issue in record['issues']}
    assert 'invalid_json' in issue_codes

    rc = main(['--root', str(tmp_path), 'artifact-index', 'build'])
    index = _json_out(capsys)
    assert rc == 0
    assert index['validation_summary']['status'] == 'blocked'
    assert index['migration_needed'] is True
    assert index['schema_versions']['unreadable'] == 1

    rc = main([
        '--root', str(tmp_path), 'artifact-index', 'query',
        '--family', 'derivations',
        '--paper-id', 'paper_a',
    ])
    query = _json_out(capsys)
    assert rc == 0
    assert query['count'] == 1
    assert query['records'][0]['artifact_id'] == derivation['artifact_id']

    rc = main(['--root', str(tmp_path), 'industrial-readiness', 'build'])
    readiness = _json_out(capsys)
    assert rc == 0
    assert readiness['status'] == 'blocked'
    blocker_codes = {row['code'] for row in readiness['blockers']}
    assert 'artifact_validation_blockers' in blocker_codes
    assert 'derivation_dependency_blockers' in blocker_codes
    assert 'experiment_reproducibility_blockers' in blocker_codes
    assert 'failed_benchmark_runs' in blocker_codes
    assert 'traceability_missing_targets' in blocker_codes
    assert readiness['sop_gate_report']['status'] in {'ready_for_review', 'warnings'}
    assert readiness['next_actions']

    out = tmp_path / 'dashboard_readiness.json'
    rc = main(['--root', str(tmp_path), 'dashboard-export', '--output', str(out)])
    assert rc == 0
    capsys.readouterr()
    dashboard = json.loads(out.read_text())
    assert dashboard['validation_summary']['status'] == 'blocked'
    assert dashboard['readiness_summary']['status'] == 'blocked'
    assert dashboard['next_actions']
