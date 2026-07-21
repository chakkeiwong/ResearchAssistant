from __future__ import annotations

import json
import shutil
from pathlib import Path

from research_assistant.cli import main

def test_cli_surveybench_run_success_and_output_file(tmp_path: Path, capsys) -> None:
    task = Path(__file__).resolve().parents[1] / 'fixtures' / 'surveybench' / 'tasks' / 'neural_ot_seed_synthetic.task.json'
    output = tmp_path / 'surveybench_report.json'

    rc = main(['surveybench', 'run', '--task', str(task), '--output', str(output)])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-cli-result-v1'
    assert payload['status'] == 'passed'
    assert payload['vetoes'] == []
    assert payload['report_path'] == f'redacted:{output.name}'
    report = json.loads(output.read_text())
    assert report['schema_version'] == 'ra-surveybench-report-v1'
    assert report['diagnostics']['resolved_anchor_count'] == 4


def test_cli_surveybench_run_propagates_anchor_veto(tmp_path: Path, capsys) -> None:
    task = Path(__file__).resolve().parents[1] / 'fixtures' / 'surveybench' / 'tasks' / 'neural_ot_seed_synthetic.task.json'
    expected = json.loads(task.read_text())['expected_outputs']
    actual_dir = tmp_path / 'actual'
    actual_dir.mkdir()
    for name, rel_path in expected.items():
        payload = json.loads((task.parent / rel_path).resolve().read_text())
        if name == 'claim_support':
            payload['claims'][0]['anchors'] = []
        (actual_dir / Path(rel_path).name).write_text(json.dumps(payload, indent=2, sort_keys=True))

    rc = main(['surveybench', 'run', '--task', str(task), '--actual-dir', str(actual_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'failed'
    assert 'missing_anchor' in payload['vetoes']


def test_cli_surveybench_local_manifest_success_and_failure(tmp_path: Path, capsys) -> None:
    fixture_root = Path(__file__).resolve().parents[1] / 'fixtures' / 'surveybench' / 'local_manifest'
    output = tmp_path / 'manifest_report.json'

    rc = main([
        'surveybench', 'local-manifest',
        '--manifest', str(fixture_root / 'redacted_manifest.valid.json'),
        '--output', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-local-manifest-cli-result-v1'
    assert payload['status'] == 'passed'
    assert payload['issue_count'] == 0
    assert json.loads(output.read_text())['schema_version'] == 'ra-surveybench-local-manifest-report-v1'

    rc = main([
        'surveybench', 'local-manifest',
        '--manifest', str(fixture_root / 'redacted_manifest.invalid.json'),
    ])
    failed = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert failed['status'] == 'failed'
    assert any(issue['code'] == 'private_path_leak' for issue in failed['issues'])


def test_cli_surveybench_replay_call_and_audit(tmp_path: Path, capsys) -> None:
    task = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_replay'
        / 'neural_ot_seed_replay.task.json'
    )
    session = tmp_path / 'replay_session'

    rc = main([
        'surveybench', 'replay-call',
        '--task', str(task),
        '--endpoint', 'references',
        '--session', str(session),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-online-replay-call-result-v1'
    assert payload['status'] == 'ok'
    assert payload['response']['endpoint'] == 'references'
    event_log = json.loads((session / 'event_log.json').read_text())
    assert event_log['schema_version'] == 'ra-surveybench-online-replay-event-log-v1'
    assert event_log['events'][0]['budget_after']['endpoint_calls'] == 23

    audit_output = tmp_path / 'replay_audit.json'
    rc = main([
        'surveybench', 'replay-audit',
        '--task', str(task),
        '--output', str(audit_output),
    ])
    audit = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert audit['schema_version'] == 'ra-surveybench-online-replay-audit-cli-result-v1'
    assert audit['status'] == 'passed'
    assert json.loads(audit_output.read_text())['issue_count'] == 0


def test_cli_surveybench_replay_call_blocks_unknown_endpoint(tmp_path: Path, capsys) -> None:
    task = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_replay'
        / 'neural_ot_seed_replay.task.json'
    )

    rc = main([
        'surveybench', 'replay-call',
        '--task', str(task),
        '--endpoint', 'not-a-real-endpoint',
        '--session', str(tmp_path / 'replay_session'),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked_unknown_endpoint'


def test_cli_surveybench_replay_transcript_writes_report(tmp_path: Path, capsys) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_ambiguity_partial_frontier_replay'
    )
    task = fixture / 'neural_ot_seed_ambiguity_partial_frontier_replay.task.json'
    session = tmp_path / 'session'
    for endpoint in ['search', 'citations', 'download-status', 'source-status']:
        rc = main([
            'surveybench', 'replay-call',
            '--task', str(task),
            '--endpoint', endpoint,
            '--session', str(session),
        ])
        assert rc == 0
        capsys.readouterr()
    output = tmp_path / 'transcript.json'

    rc = main([
        'surveybench', 'replay-transcript',
        '--task', str(task),
        '--session', str(session),
        '--output', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-online-replay-transcript-cli-result-v1'
    assert payload['status'] == 'passed'
    assert payload['event_count'] == 4
    assert payload['summary']['rate_limit_count'] == 1
    transcript = json.loads(output.read_text())
    assert transcript['schema_version'] == 'ra-surveybench-online-replay-transcript-v1'
    assert transcript['summary']['pagination_token_count'] == 1
    assert 'live-web robustness' in transcript['what_is_not_concluded']


def test_cli_surveybench_replay_score_success(tmp_path: Path, capsys) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_replay'
    )
    task = fixture / 'neural_ot_seed_replay.task.json'
    actual = tmp_path / 'actual'
    actual.mkdir()
    for path in (fixture / 'scorer_packet').glob('*.json'):
        shutil.copy(path, actual / path.name)
    session = tmp_path / 'session'
    for endpoint in ['search', 'references', 'citations', 'adjacent', 'download-status', 'source-anchors']:
        rc = main([
            'surveybench', 'replay-call',
            '--task', str(task),
            '--endpoint', endpoint,
            '--session', str(session),
        ])
        assert rc == 0
        capsys.readouterr()
    output = tmp_path / 'score_report.json'

    rc = main([
        'surveybench', 'replay-score',
        '--task', str(task),
        '--actual-dir', str(actual),
        '--event-log', str(session / 'event_log.json'),
        '--gold-dir', str(fixture / 'scorer_packet'),
        '--output', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-online-replay-score-cli-result-v1'
    assert payload['status'] == 'passed'
    assert payload['vetoes'] == []
    assert json.loads(output.read_text())['schema_version'] == 'ra-surveybench-online-replay-score-report-v1'


def test_cli_surveybench_stress_replay_audit_and_score_success(tmp_path: Path, capsys) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_ambiguity_partial_frontier_replay'
    )
    task = fixture / 'neural_ot_seed_ambiguity_partial_frontier_replay.task.json'

    rc = main(['surveybench', 'replay-audit', '--task', str(task)])
    audit = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert audit['status'] == 'passed'

    actual = tmp_path / 'actual'
    actual.mkdir()
    for path in (fixture / 'scorer_packet').glob('*.json'):
        shutil.copy(path, actual / path.name)
    session = tmp_path / 'session'
    for endpoint in ['search', 'references', 'citations', 'adjacent', 'download-status', 'source-anchors']:
        rc = main([
            'surveybench', 'replay-call',
            '--task', str(task),
            '--endpoint', endpoint,
            '--session', str(session),
        ])
        assert rc == 0
        capsys.readouterr()
    output = tmp_path / 'stress_score.json'

    rc = main([
        'surveybench', 'replay-score',
        '--task', str(task),
        '--actual-dir', str(actual),
        '--event-log', str(session / 'event_log.json'),
        '--gold-dir', str(fixture / 'scorer_packet'),
        '--output', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-online-replay-score-cli-result-v1'
    assert payload['status'] == 'passed'
    assert payload['vetoes'] == []
    assert json.loads(output.read_text())['schema_version'] == 'ra-surveybench-online-replay-score-report-v1'


def test_cli_surveybench_restricted_workspace(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / 'restricted_workspace'
    output = tmp_path / 'restricted_report.json'

    rc = main([
        'surveybench', 'restricted-workspace',
        '--repo-root', str(Path(__file__).resolve().parents[2]),
        '--workspace', str(workspace),
        '--output', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-restricted-workspace-cli-result-v1'
    assert payload['status'] == 'passed'
    assert payload['copied_file_count'] == 14
    report = json.loads(output.read_text())
    assert report['status'] == 'passed'
    assert (workspace / 'src' / 'research_assistant' / 'cli.py').exists()
    assert not (workspace / 'tests' / 'fixtures' / 'surveybench' / 'online_replay' / 'neural_ot_seed_replay' / 'scorer_packet').exists()


def test_cli_surveybench_stress_restricted_workspace_and_launcher_dry_run(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / 'stress_restricted_workspace'
    workspace_report = tmp_path / 'stress_restricted_report.json'
    launcher_report = tmp_path / 'stress_launcher_dry_run.json'

    rc = main([
        'surveybench', 'restricted-workspace',
        '--repo-root', str(Path(__file__).resolve().parents[2]),
        '--workspace', str(workspace),
        '--profile', 'stress',
        '--output', str(workspace_report),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'passed'
    assert payload['profile_id'] == 'neural_ot_seed_ambiguity_partial_frontier_replay'
    assert not (workspace / 'tests' / 'fixtures' / 'surveybench' / 'online_replay' / 'neural_ot_seed_ambiguity_partial_frontier_replay' / 'scorer_packet').exists()
    assert not (workspace / 'tests' / 'fixtures' / 'surveybench' / 'online_replay' / 'neural_ot_seed_ambiguity_partial_frontier_replay' / 'negative_packets').exists()

    rc = main([
        'surveybench', 'restricted-launcher-dry-run',
        '--workspace', str(workspace),
        '--profile', 'stress',
        '--subject-agent', 'claude-opus-not-launched',
        '--output', str(launcher_report),
    ])
    launch = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert launch['status'] == 'prepared_not_launched'
    assert launch['subject_invoked'] is False
    written = json.loads(launcher_report.read_text())
    assert written['dry_run'] is True
    assert written['repo_root_not_provided_to_subject'] is True
    assert written['profile_id'] == 'neural_ot_seed_ambiguity_partial_frontier_replay'

    subject_binding_report = tmp_path / 'stress_subject_binding_preflight.json'
    rc = main([
        'surveybench', 'subject-binding-preflight',
        '--workspace', str(workspace),
        '--profile', 'stress',
        '--subject-agent', 'claude-opus-subject',
        '--model-id', 'claude-opus-4-1',
        '--output', str(subject_binding_report),
    ])
    binding_summary = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert binding_summary['schema_version'] == 'ra-surveybench-subject-binding-preflight-cli-result-v1'
    assert binding_summary['status'] == 'passed'
    assert binding_summary['subject_invoked'] is False
    binding = json.loads(subject_binding_report.read_text())
    assert binding['permission_mode'] == 'dontAsk'
    assert binding['representative_probe']['status'] == 'passed'

    codex_subject_binding_report = tmp_path / 'codex_subject_binding_preflight.json'
    rc = main([
        'surveybench', 'subject-binding-preflight',
        '--workspace', str(workspace),
        '--profile', 'stress',
        '--subject-agent', 'codex-subject',
        '--model-id', 'gpt-5.3-codex',
        '--subject-transport', 'codex-exec',
        '--output', str(codex_subject_binding_report),
    ])
    codex_binding_summary = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert codex_binding_summary['schema_version'] == 'ra-surveybench-subject-binding-preflight-cli-result-v1'
    assert codex_binding_summary['status'] == 'passed'
    codex_binding = json.loads(codex_subject_binding_report.read_text())
    assert codex_binding['subject_transport'] == 'codex-exec'
    assert codex_binding['settings_path'] is None
    assert codex_binding['wrapper_command_template'][0:4] == ['codex', '--ask-for-approval', 'never', 'exec']
    assert '--ask-for-approval' in codex_binding['wrapper_command_template']
    assert 'never' in codex_binding['wrapper_command_template']
    assert '--output-last-message' in codex_binding['wrapper_command_template']

    approval_packet = tmp_path / 'stress_launch_approval_packet.json'
    rc = main([
        'surveybench', 'launch-approval-packet',
        '--launcher-dry-run', str(launcher_report),
        '--subject-agent', 'claude-opus-subject',
        '--model-id', 'claude-opus-4-1',
        '--subject-transport', 'claude-code',
        '--wrapper-command-json', json.dumps(binding['wrapper_command_template']),
        '--subject-binding-preflight', str(subject_binding_report),
        '--budget-cap-json', '{"wall_time_seconds": 1800, "max_turns": 1}',
        '--transcript-path', str(workspace / 'governance' / 'subject_transcript.jsonl'),
        '--denied-tool-capture-path', str(workspace / 'governance' / 'denied_tools.jsonl'),
        '--cli-version', 'claude-cli-test-version',
        '--output', str(approval_packet),
    ])
    approval = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert approval['schema_version'] == 'ra-surveybench-launch-approval-packet-cli-result-v1'
    assert approval['status'] == 'passed'
    assert approval['packet_status'] == 'pending_human_approval'
    assert approval['subject_invoked'] is False
    assert approval['human_approval_granted'] is False
    packet = json.loads(approval_packet.read_text())
    assert packet['schema_version'] == 'ra-surveybench-launch-approval-packet-v1'
    assert packet['human_launch_approval']['granted'] is False
    assert packet['subject_binding_preflight']['status'] == 'passed'

    enforcement_report = tmp_path / 'stress_launch_enforcement_preflight.json'
    rc = main([
        'surveybench', 'launch-enforcement-preflight',
        '--approval-packet', str(approval_packet),
        '--output', str(enforcement_report),
    ])
    enforcement = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert enforcement['schema_version'] == 'ra-surveybench-launch-enforcement-preflight-cli-result-v1'
    assert enforcement['status'] == 'passed'
    assert enforcement['subject_invoked'] is False
    written_enforcement = json.loads(enforcement_report.read_text())
    assert written_enforcement['supervisor_execution']['timeout_enforcement'] == 'python_subprocess_timeout_on_phase3_launch'
    assert written_enforcement['capture_contract']['denied_tool_capture_authoritative'] is False
    assert written_enforcement['subject_task_boundary']['subject_binding_preflight']['status'] == 'passed'
    assert written_enforcement['no_drift']['status'] == 'passed'


def test_cli_surveybench_helper_bundle_commands(tmp_path: Path, capsys) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_replay'
    )
    task = fixture / 'neural_ot_seed_replay.task.json'
    session = tmp_path / 'session'
    for endpoint in ['search', 'paper', 'references', 'citations', 'adjacent', 'download-status', 'source-status', 'source-anchors', 'evidence-context']:
        rc = main([
            'surveybench', 'replay-call',
            '--task', str(task),
            '--endpoint', endpoint,
            '--session', str(session),
        ])
        assert rc == 0
        capsys.readouterr()

    rc = main(['surveybench', 'next-action', '--task', str(task), '--session', str(session)])
    next_action = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert next_action['schema_version'] == 'ra-surveybench-helper-v1'
    assert next_action['next_action'] == 'write_packet_files'
    assert next_action['next_endpoint'] is None

    packet_dir = tmp_path / 'packet'
    rc = main([
        'surveybench', 'packet-template',
        '--task', str(task),
        '--output-dir', str(packet_dir),
        '--write-files',
    ])
    template = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert template['schema_version'] == 'ra-surveybench-packet-template-v1'
    assert (packet_dir / 'claim_support.json').exists()

    composed_dir = tmp_path / 'composed_packet'
    rc = main([
        'surveybench', 'packet-compose',
        '--task', str(task),
        '--output-dir', str(composed_dir),
        '--session', str(session),
        '--responses-dir', str(fixture / 'responses'),
        '--write-files',
    ])
    composed = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert composed['schema_version'] == 'ra-surveybench-packet-compose-v1'
    assert composed['status'] == 'ready'
    assert (composed_dir / 'trial_record.json').exists()

    rc = main([
        'surveybench', 'cluster-hints',
        '--task', str(task),
        '--responses-dir', str(fixture / 'responses'),
    ])
    cluster_hints = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert cluster_hints['schema_version'] == 'ra-surveybench-cluster-hints-v1'
    assert cluster_hints['status'] == 'ready'
    assert {row['cluster_id'] for row in cluster_hints['clusters']} == {
        'adjacent_density_modeling',
        'classical_optimal_transport',
        'neural_optimal_transport',
    }

    rc = main([
        'surveybench', 'ready-for-prose',
        '--task', str(task),
        '--actual-dir', str(packet_dir),
        '--session', str(session),
    ])
    readiness = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert readiness['schema_version'] == 'ra-surveybench-ready-for-prose-v1'
    assert readiness['status'] == 'blocked'
    assert 'packet_content_incomplete' in readiness['blocked_reasons']
    assert readiness['packet_issues']

    rc = main(['surveybench', 'launch-record-template', '--task', str(task)])
    launch_record = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert launch_record['schema_version'] == 'ra-surveybench-launch-record-template-v1'
    assert launch_record['launch_record']['supervisor'] == 'codex'


def test_cli_surveybench_score_prose_hard_gate(tmp_path: Path, capsys) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'transport_hmc_dsge_replay'
    )
    task = fixture / 'transport_hmc_dsge_replay.task.json'
    session = tmp_path / 'session'
    for endpoint in ['search', 'references', 'citations', 'adjacent', 'download-status', 'source-anchors']:
        rc = main([
            'surveybench', 'replay-call',
            '--task', str(task),
            '--endpoint', endpoint,
            '--session', str(session),
        ])
        assert rc == 0
        capsys.readouterr()
    actual = tmp_path / 'actual'
    actual.mkdir()
    for path in (fixture / 'scorer_packet').glob('*.json'):
        shutil.copy(path, actual / path.name)
    prose = tmp_path / 'survey_prose.json'
    prose.write_text(json.dumps({
        'schema_version': 'ra-surveybench-survey-prose-v1',
        'task_id': 'transport_hmc_dsge_replay',
        'claim_trace': [
            {
                'anchors': [
                    {
                        'kind': 'section',
                        'label': 'sec:transport-hmc-method',
                        'paper_key': 'thmc_seed_001',
                    }
                ],
                'claim': 'The synthetic seed is the central transport-assisted HMC method node for this benchmark task.',
                'claim_id': 'claim_transport_hmc_seed_method_node',
                'paper_keys': ['thmc_seed_001'],
                'status': 'supported',
                'support_class': 'fixture_source_support',
            },
            {
                'anchors': [
                    {
                        'kind': 'equation',
                        'label': 'eq:transport-map-jacobian',
                        'paper_key': 'thmc_seed_001',
                    },
                    {
                        'kind': 'algorithm',
                        'label': 'alg:transport-hmc-transition',
                        'paper_key': 'thmc_seed_001',
                    },
                ],
                'claim': 'The fixture exposes transport-map and HMC-transition anchors for claim-support testing.',
                'claim_id': 'claim_transport_hmc_anchor_support',
                'paper_keys': ['thmc_seed_001'],
                'status': 'supported',
                'support_class': 'fixture_source_support',
            },
            {
                'anchors': [
                    {
                        'kind': 'citation_map_edge',
                        'label': 'thmc_cite_001->thmc_seed_001',
                        'paper_key': 'thmc_cite_001',
                    }
                ],
                'claim': 'The replay citation surface marks thmc_cite_001 as citing the synthetic seed.',
                'claim_id': 'claim_transport_hmc_forward_citation',
                'paper_keys': ['thmc_cite_001', 'thmc_seed_001'],
                'status': 'supported',
                'support_class': 'fixture_graph_support',
            },
        ],
        'source_status_caveats': [
            {'paper_key': 'thmc_ref_001', 'caveat': 'metadata-only lineage context'},
            {'paper_key': 'thmc_ref_002', 'caveat': 'metadata-only lineage context'},
            {'paper_key': 'thmc_cite_001', 'caveat': 'metadata-only forward citation'},
            {'paper_key': 'thmc_adj_001', 'caveat': 'metadata-only adjacent context'},
            {'paper_key': 'thmc_proxy_001', 'caveat': 'proxy-only benchmark context'},
        ],
        'addressed_omission_risks': ['thmc_ref_001', 'thmc_ref_002', 'thmc_adj_001', 'thmc_proxy_001'],
        'what_is_not_concluded': [
            'live-web coverage is not concluded',
            'current citation counts are not concluded',
            'download reliability is not concluded',
            'survey completeness is not concluded',
            'product readiness is not concluded',
            'scientific correctness is not concluded',
        ],
    }, indent=2, sort_keys=True))
    output = tmp_path / 'score_prose_report.json'

    rc = main([
        'surveybench', 'score-prose',
        '--task', str(task),
        '--actual-dir', str(actual),
        '--event-log', str(session / 'event_log.json'),
        '--gold-dir', str(fixture / 'scorer_packet'),
        '--prose', str(prose),
        '--output', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-surveybench-survey-prose-score-cli-result-v1'
    assert payload['status'] == 'passed'
    report = json.loads(output.read_text())
    assert report['packet_gate']['status'] == 'passed'
    assert report['hard_gate_vetoes'] == []
