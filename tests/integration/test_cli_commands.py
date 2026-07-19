from __future__ import annotations

import io
import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import pytest

from research_assistant import cli
from research_assistant.cli import SURVEY_WRITE_OUTPUT_FIELDS, main
import research_assistant.survey.build as survey_build
import research_assistant.survey.orchestrate as orchestrate
from research_assistant.survey.anchors import build_source_anchor_packet
from research_assistant.survey.claim_review import (
    SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
    SURVEY_CLAIM_REVIEW_V3_SCHEMA,
)
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.review_decisions import decision_sha256
from research_assistant.survey.reviewed_merge import _workflow_blocker
from research_assistant.survey.source_intake import (
    MissionSourceCapability,
    SourceCapabilityResult,
)
from research_assistant.survey.source_safety_review import (
    SOURCE_CHECKS,
    SOURCE_OBSERVATION_NONCLAIMS,
    SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
    SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
    preview_source_observation_binding,
)
from research_assistant.ingest import metadata_resolve
from research_assistant.ingest.parser_preflight import ParserPreflight
from research_assistant.ingest.source_manifest import canonical_paper_id
from research_assistant.schemas.parsed_document import ParsedDocument


def test_cli_find_empty_store(tmp_path: Path, capsys) -> None:
    root = tmp_path
    (root / 'local_research' / 'summaries').mkdir(parents=True)
    rc = main(['--root', str(root), 'find', '--query', 'nothing'])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ''


def test_cli_help_includes_review_inbox_export_and_citation_commands(capsys) -> None:
    try:
        main(['surveybench', '--help'])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert 'replay-call' in captured.out
    assert 'packet-template' in captured.out
    assert 'packet-compose' in captured.out
    assert 'ready-for-prose' in captured.out
    assert 'cluster-hints' in captured.out
    assert 'surveybench' in captured.out


def test_cli_survey_safe_local_help_describes_bounded_supervisor_and_boundaries(capsys) -> None:
    with pytest.raises(SystemExit) as error:
        main(['survey', 'run-public-source-workflow', '--help'])
    assert error.value.code == 0
    output = ' '.join(capsys.readouterr().out.split())
    assert 'bounded typed local supervisor' in output
    assert 'every currently eligible deterministic stage' in output
    assert 'live/API/download' in output
    assert 'human-review' in output


def test_cli_survey_build_writes_honest_skeleton(tmp_path: Path, capsys) -> None:
    output = tmp_path / 'neural_ot_packet'

    rc = main([
        'survey',
        'build',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-survey-build-cli-result-v1'
    assert payload['status'] == 'created_skeleton'
    assert payload['seed_count'] == 1
    assert 'scientific correctness' in payload['what_is_not_concluded']
    for name in [
        'candidate_ledger.json',
        'citation_map.json',
        'source_support.json',
        'paper_classifications.json',
        'claim_support.json',
        'omission_risk.json',
        'workflow_state.json',
        'survey_packet.md',
        'build_manifest.json',
    ]:
        assert (output / name).exists()

    citation_map = json.loads((output / 'citation_map.json').read_text())
    assert citation_map['status'] == 'skeleton_pending_citation_expansion'
    assert citation_map['edges'] == []
    source_support = json.loads((output / 'source_support.json').read_text())
    assert source_support['papers'][0]['source_status'] == 'pending_lookup'
    paper_classifications = json.loads((output / 'paper_classifications.json').read_text())
    assert paper_classifications['classifications'][0]['labels'] == ['seed']
    assert 'seed' in paper_classifications['allowed_labels']
    assert 'major_citing_work' in paper_classifications['allowed_labels']
    claim_support = json.loads((output / 'claim_support.json').read_text())
    assert claim_support['status'] == 'skeleton_no_supported_claims_yet'
    assert claim_support['claims'] == []
    manifest = json.loads((output / 'build_manifest.json').read_text())
    assert manifest['workflow_state']['state'] == 'skeleton_created'
    assert manifest['workflow_state']['ready_for_writer'] is False
    assert manifest['workflow_state']['ready_for_prose'] is False
    assert any('public-metadata' in command for command in manifest['workflow_state']['safe_next_commands'])
    assert any('source/PDF/full-text' in item for item in manifest['workflow_state']['approval_required_for'])
    workflow_state = json.loads((output / 'workflow_state.json').read_text())
    assert workflow_state == manifest['workflow_state']
    assert payload['workflow_state'] == workflow_state
    assert payload['workflow_state_path'] == str(output / 'workflow_state.json')

    rc = main([
        'survey',
        'build',
        '--topic',
        'Neural Optimal Transport',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
    ])
    blocked = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert blocked['status'] == 'blocked'
    assert blocked['blocked_reason'] == 'output_exists'
    assert blocked['schema_version'] == 'ra-survey-build-cli-result-v1'
    assert blocked['message'] == 'output directory already contains survey-build artifacts'
    assert blocked['next_required_actions'] == ['rerun with --force or choose a new --out directory']
    assert 'scientific correctness' in blocked['what_is_not_concluded']


def test_cli_survey_build_public_metadata_keeps_nonclaim_boundaries(tmp_path: Path, capsys, monkeypatch) -> None:
    output = tmp_path / 'neural_ot_public_metadata_packet'

    def fake_collect_public_metadata(*, topic: str, seeds: list[str], providers: list[str], max_records: int, fetched_at: str) -> dict:
        assert providers == ['arxiv', 'openalex']
        assert max_records == 25
        return {
            'status': 'metadata_collected',
            'fetched_at': fetched_at,
            'provider_statuses': [
                {
                    'provider': 'arxiv', 'query_kind': 'seed_resolution',
                    'normalized_seed_key': 'arxiv:2201.12220v3', 'topic_query': False,
                    'query_cap': 5, 'status': 'available', 'record_count': 1,
                    'raw_response_saved': False,
                },
                {
                    'provider': 'arxiv', 'query_kind': 'topic_search',
                    'normalized_seed_key': None, 'topic_query': True,
                    'query_cap': 12, 'status': 'available', 'record_count': 0,
                    'raw_response_saved': False,
                },
                {
                    'provider': 'openalex', 'query_kind': 'seed_resolution',
                    'normalized_seed_key': 'arxiv:2201.12220v3', 'topic_query': False,
                    'query_cap': 5, 'status': 'available', 'record_count': 1,
                    'raw_response_saved': False,
                },
                {
                    'provider': 'openalex', 'query_kind': 'topic_search',
                    'normalized_seed_key': None, 'topic_query': True,
                    'query_cap': 12, 'status': 'available', 'record_count': 1,
                    'raw_response_saved': False,
                },
            ],
            'raw_response_policy': {
                'raw_responses_saved': False,
                'privacy_scan': 'not_applicable_raw_responses_not_saved',
                'reason': 'test fixture',
            },
            'records': [
                {
                    'record_key': 'arxiv:2201.12220v3',
                    'title': 'Neural Optimal Transport',
                    'authors': ['Alice Example'],
                    'year': 2022,
                    'doi': None,
                    'arxiv_id': '2201.12220v3',
                    'openalex_id': 'https://openalex.org/W123',
                    'landing_page_url': 'https://arxiv.org/abs/2201.12220v3',
                    'citation_count': 42,
                    'providers': ['openalex', 'arxiv'],
                    'roles': [],
                    'provider_records': [
                        {
                            'provider': 'arxiv', 'query_kind': 'seed_resolution',
                            'source_id': '2201.12220v3', 'primary_category': 'cs.LG',
                            'published': '2022-01-01',
                        },
                        {
                            'provider': 'openalex', 'query_kind': 'seed_resolution',
                            'source_id': 'https://openalex.org/W123', 'citation_count': 42,
                            'publication_date': '2022-01-01', 'work_type': 'article',
                        },
                    ],
                    'referenced_works': ['https://openalex.org/W456'],
                    'query_provenance': [
                        {
                            'provider': 'arxiv', 'query_kind': 'seed_resolution',
                            'normalized_seed_key': 'arxiv:2201.12220v3',
                            'topic_query': False,
                        },
                        {
                            'provider': 'openalex', 'query_kind': 'seed_resolution',
                            'normalized_seed_key': 'arxiv:2201.12220v3',
                            'topic_query': False,
                        },
                    ],
                },
                {
                    'record_key': 'openalex:w456',
                    'title': 'Neural Transport Later Work',
                    'authors': ['Bob Example'],
                    'year': 2024,
                    'doi': None,
                    'arxiv_id': None,
                    'openalex_id': 'https://openalex.org/W456',
                    'landing_page_url': 'https://openalex.org/W456',
                    'citation_count': 7,
                    'providers': ['openalex'],
                    'roles': ['major_citing_work'],
                    'provider_records': [{
                        'provider': 'openalex', 'query_kind': 'topic_search',
                        'source_id': 'https://openalex.org/W456', 'citation_count': 7,
                        'publication_date': '2024-01-01', 'work_type': 'article',
                    }],
                    'referenced_works': [],
                    'query_provenance': [{
                        'provider': 'openalex', 'query_kind': 'topic_search',
                        'normalized_seed_key': None, 'topic_query': True,
                    }],
                },
            ],
        }

    monkeypatch.setattr('research_assistant.survey.build._collect_public_metadata', fake_collect_public_metadata)

    rc = main([
        'survey',
        'build',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
        '--mode',
        'public-metadata',
        '--public-metadata-provider',
        'openalex',
        '--public-metadata-provider',
        'arxiv',
        '--max-records',
        '25',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'metadata_only_packet'
    assert payload['mode'] == 'public-metadata'
    assert payload['record_count'] == 2
    assert (output / 'metadata_provenance.json').exists()
    source_support = json.loads((output / 'source_support.json').read_text())
    assert source_support['status'] == 'metadata_only_no_sources_inspected'
    assert all(row['download_status'] == 'source_not_attempted' for row in source_support['papers'])
    assert all(row['checked_anchors'] == [] for row in source_support['papers'])
    claim_support = json.loads((output / 'claim_support.json').read_text())
    assert claim_support['status'] == 'metadata_only_no_supported_technical_claims'
    assert claim_support['claims'] == []
    assert claim_support['claim_support_policy']['metadata_only_support_allowed_for_technical_claims'] is False
    citation_map = json.loads((output / 'citation_map.json').read_text())
    assert citation_map['expansion_policy']['max_downloads'] == 0
    assert citation_map['nodes'][0]['citation_count_policy'] == 'coverage_signal_only'
    provenance = json.loads((output / 'metadata_provenance.json').read_text())
    assert provenance['download_or_source_intake']['attempted'] is False
    assert provenance['raw_response_policy']['raw_responses_saved'] is False
    manifest = json.loads((output / 'build_manifest.json').read_text())
    assert manifest['schema_version'] == 'ra-survey-public-metadata-build-manifest-v2'
    assert manifest['workflow_state']['state'] == 'metadata_only_public_v2'
    assert manifest['workflow_state']['ready_for_writer'] is True
    assert manifest['workflow_state']['ready_for_prose'] is False
    assert any('capability-gated mission source intake' in command for command in manifest['workflow_state']['safe_next_commands'])
    assert any('source_fetch' in item for item in manifest['workflow_state']['approval_required_for'])
    workflow_state = json.loads((output / 'workflow_state.json').read_text())
    assert workflow_state == manifest['workflow_state']
    assert payload['workflow_state'] == workflow_state
    assert payload['workflow_state_path'] == str(output / 'workflow_state.json')
    survey_packet = (output / 'survey_packet.md').read_text()
    assert 'No PDF, source, or full-text download was attempted' in survey_packet
    assert 'cannot support technical claims' in survey_packet


def test_cli_survey_anchors_extracts_source_anchors_without_claim_support(tmp_path: Path, capsys) -> None:
    source_record = tmp_path / 'local_research' / 'papers' / 'source' / 'records' / 'paper_phase5_source.json'
    source_record.parent.mkdir(parents=True)
    source_record.write_text(json.dumps({
        'paper_id': 'paper_phase5_source',
        'source_type': 'arxiv_latex',
        'status': 'available',
        'primary_for_audit': True,
        'provenance': {'arxiv_id': '2401.00001v1'},
        'sections': [
            {
                'title': 'Introduction',
                'labels': ['sec:intro'],
                'line': 10,
                'raw_latex': 'We introduce the scope.',
            },
            {
                'title': 'Method',
                'labels': ['sec:method', 'eq:objective', 'thm:bound'],
                'line': 20,
                'raw_latex': 'The method minimizes an objective.',
            },
        ],
        'equations': [
            {
                'environment': 'equation',
                'labels': ['eq:objective'],
                'line': 24,
                'raw_latex': r'\\begin{equation}\\label{eq:objective} J(\\theta)=0\\end{equation}',
            }
        ],
        'theorem_like_blocks': [
            {
                'environment': 'theorem',
                'labels': ['thm:bound'],
                'line': 30,
                'raw_latex': r'\\begin{theorem}\\label{thm:bound} Bound holds.\\end{theorem}',
            }
        ],
        'citations': [],
        'bibliography': [],
        'references': [],
        'labels': [],
        'macros': [],
        'limitations': [{'field': 'macros', 'status': 'requires_review'}],
    }))
    output = tmp_path / 'anchors'

    rc = main([
        '--root',
        str(tmp_path),
        'survey',
        'anchors',
        '--topic',
        'Phase 5 source anchors',
        '--paper-id',
        'paper_phase5_source',
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'anchors_extracted'
    assert payload['anchor_count'] >= 3
    inventory = json.loads((output / 'source_anchor_inventory.json').read_text())
    assert inventory['raw_text_policy']['raw_latex_included'] is False
    assert {row['anchor_type'] for row in inventory['anchors']} >= {'section', 'equation', 'theorem_like_block'}
    assert all(row['raw_latex_included'] is False for row in inventory['anchors'])
    assert all('raw_latex' not in row for row in inventory['anchors'])
    source_support = json.loads((output / 'source_support.json').read_text())
    assert source_support['papers'][0]['technical_claim_support'] == 'not_supported_until_claim_mapping_review'
    claim_support = json.loads((output / 'claim_support.json').read_text())
    assert claim_support['claims'] == []
    assert claim_support['blocked_claims'][0]['status'] == 'blocked'
    assert claim_support['claim_support_policy']['metadata_only_support_allowed_for_technical_claims'] is False
    assert claim_support['claim_support_policy']['source_availability_support_allowed_for_technical_claims'] is False


def test_cli_survey_anchors_missing_source_is_source_gap_not_claim_support(tmp_path: Path, capsys) -> None:
    output = tmp_path / 'anchors_source_gap'

    rc = main([
        '--root',
        str(tmp_path),
        'survey',
        'anchors',
        '--paper-id',
        'p_meta_001',
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'source_gaps_or_no_anchors'
    assert payload['source_gap_count'] == 1
    source_support = json.loads((output / 'source_support.json').read_text())
    assert source_support['source_gap_rows'][0]['paper_id'] == 'p_meta_001'
    assert source_support['papers'][0]['technical_claim_support'] == 'source_gap'
    claim_support = json.loads((output / 'claim_support.json').read_text())
    assert claim_support['claims'] == []
    assert claim_support['blocked_claims'][0]['support_class'] == 'source_gap_pending_claim_mapping'


def _write_public_source_packet_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    topic = 'Neural Optimal Transport for generative modeling and inference'
    metadata_dir = tmp_path / 'phase2'
    source_status_dir = tmp_path / 'phase4'
    anchor_dir = tmp_path / 'phase5'
    metadata_dir.mkdir()
    source_status_dir.mkdir()
    anchor_dir.mkdir()

    source_record_path = (
        tmp_path / 'local_research' / 'papers' / 'source' / 'records'
        / 'paper_arxiv_2201_1a5af737.json'
    )
    source_record_path.parent.mkdir(parents=True)
    source_record = {
        'paper_id': 'paper_arxiv_2201_1a5af737',
        'source_type': 'arxiv_latex',
        'status': 'available',
        'primary_for_audit': True,
        'provenance': {'arxiv_id': '2201.12220v3'},
        'sections': [{
            'title': 'Method',
            'labels': ['sec-method'],
            'line': 20,
            'raw_latex': 'The checked source contains the Neural Optimal Transport method section.',
        }],
        'equations': [],
        'theorem_like_blocks': [],
        'citations': [],
        'bibliography': [],
        'references': [],
        'labels': [],
        'macros': [],
        'limitations': [],
    }
    source_record_path.write_text(json.dumps(source_record, indent=2, sort_keys=True) + '\n')
    (metadata_dir / 'candidate_ledger.json').write_text(json.dumps({
        'schema_version': 'ra-survey-candidate-ledger-v1',
        'status': 'metadata_only_public',
        'topic': topic,
        'candidate_count': 2,
        'max_records': 25,
        'included': [
            {
                'paper_key': 'p_meta_001',
                'identifier': 'arxiv:2201.12220v3',
                'title': 'Neural Optimal Transport',
                'roles': ['seed'],
                'metadata_only': True,
            },
            {
                'paper_key': 'p_meta_002',
                'identifier': 'doi:10.example/adjacent',
                'title': 'Adjacent Transport Method',
                'roles': ['adjacent_method'],
                'metadata_only': True,
            },
        ],
        'duplicates': [],
        'excluded': [],
        'provider_statuses': [],
        'raw_response_policy': {'raw_provider_responses_saved': False},
        'next_required_actions': ['inspect primary sources'],
    }))
    (metadata_dir / 'citation_map.json').write_text(json.dumps({
        'schema_version': 'ra-survey-citation-map-v1',
        'status': 'metadata_only_public_partial',
        'topic': topic,
        'seed_papers': ['p_meta_001'],
        'expansion_policy': {
            'backward_depth': 1,
            'forward_depth': 1,
            'adjacent_query_count': 1,
            'max_nodes': 25,
            'max_downloads': 0,
            'download_or_source_intake_allowed': False,
        },
        'nodes': [
            {'paper_key': 'p_meta_001', 'layer': 'seed'},
            {'paper_key': 'p_meta_002', 'layer': 'adjacent'},
        ],
        'edges': [
            {
                'source': 'p_meta_001',
                'target': 'p_meta_002',
                'relation': 'adjacent_topic_candidate_metadata',
                'evidence_class': 'metadata_only_public',
            }
        ],
        'clusters': [{'cluster_id': 'adjacent_topic_metadata', 'members': ['p_meta_002']}],
        'frontiers': [{'frontier_id': 'adjacent', 'status': 'present_metadata_only'}],
        'survey_packet_paths': {
            'candidate_ledger': 'candidate_ledger.json',
            'source_support': 'source_support.json',
            'paper_classifications': 'paper_classifications.json',
            'claim_support': 'claim_support.json',
            'omission_risk': 'omission_risk.json',
            'metadata_provenance': 'metadata_provenance.json',
        },
        'next_required_actions': ['verify metadata relations'],
    }))
    (metadata_dir / 'source_support.json').write_text(json.dumps({
        'schema_version': 'ra-survey-source-support-v1',
        'status': 'metadata_only_no_sources_inspected',
        'topic': topic,
        'papers': [{'paper_key': 'p_meta_001', 'download_status': 'source_not_attempted'}],
        'next_required_actions': ['inspect primary sources'],
    }))
    (metadata_dir / 'paper_classifications.json').write_text(json.dumps({
        'schema_version': 'ra-survey-paper-classifications-v1',
        'status': 'metadata_only_preliminary',
        'topic': topic,
        'allowed_labels': ['seed', 'adjacent_method'],
        'classifications': [
            {
                'paper_key': 'p_meta_001',
                'identifier': 'arxiv:2201.12220v3',
                'labels': ['seed'],
                'claim_support_allowed': False,
            }
        ],
    }))
    (metadata_dir / 'omission_risk.json').write_text(json.dumps({
        'schema_version': 'ra-survey-omission-risk-v1',
        'status': 'metadata_only_partial_frontier',
        'topic': topic,
        'risks': [
            {
                'risk_id': 'metadata_relations_unverified',
                'severity': 'medium',
                'reason': 'metadata-only citation relations are unverified by source inspection',
            }
        ],
        'metadata_only_papers': ['p_meta_002'],
        'provider_statuses': [],
    }))
    (source_status_dir / 'phase4_source_intake_status.json').write_text(json.dumps({
        'schema_version': 'literature-survey-live-public-source-phase4-status-v1',
        'status': 'completed',
        'operation': 'source_fetch',
        'destination': 'source',
        'attempted_count': 1,
        'fetched_count': 1,
        'approved_candidate_ids': ['2201.12220v3'],
        'skipped_duplicates': [],
        'failures': [],
        'raw_artifact_policy': {'raw_source_copied_to_docs': False},
        'source_support': [{
            'paper_id': 'paper_arxiv_2201_1a5af737',
            'source_record_path': str(source_record_path),
            'source_record_sha256': hashlib.sha256(source_record_path.read_bytes()).hexdigest(),
        }],
    }))
    anchor_result = build_source_anchor_packet(
        paper_ids=['paper_arxiv_2201_1a5af737'],
        output_dir=anchor_dir,
        topic=topic,
        root=tmp_path,
    )
    assert anchor_result['status'] == 'anchors_extracted'
    return metadata_dir, source_status_dir, anchor_dir


def _snapshot_tree(root: Path) -> dict[str, tuple[str, bytes | None]]:
    return {
        str(path.relative_to(root)): (
            'symlink' if path.is_symlink() else 'dir' if path.is_dir() else 'file',
            path.read_bytes() if path.is_file() and not path.is_symlink() else None,
        )
        for path in sorted(root.rglob('*'))
    }


def _initialize_selected_review_queue(
    *,
    capsys,
    mission_dir: Path,
    metadata_dir: Path,
    source_status_dir: Path,
    anchor_dir: Path,
    packet_dir: Path,
) -> tuple[dict, dict]:
    command = [
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(mission_dir),
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--packet-dir',
        str(packet_dir),
    ]
    assert main(command) == 0
    initial = json.loads(capsys.readouterr().out)
    assert initial['review_queue_path'] is None
    assert initial['next_action']['action_id'] == 'resume_to_initialize_artifact_state'
    assert not (mission_dir / '.artifact_state').exists()

    assert main([*command, '--resume']) == 0
    selected = json.loads(capsys.readouterr().out)
    queue_path = Path(selected['review_queue_path'])
    assert queue_path.is_file()
    return selected, json.loads(queue_path.read_text())


def _queue_item_id(queue: dict, queue_type: str, source_id: str | None = None) -> str:
    matches = [
        item
        for item in queue['items']
        if item['queue_type'] == queue_type
        and (source_id is None or item['source_id'] == source_id)
    ]
    assert len(matches) == 1
    return matches[0]['item_id']


def _bound_review_decisions(
    review_queue_path: Path,
    queue: dict,
    decision_type: str,
    decisions: list[dict],
) -> dict:
    return {
        'schema_version': 'ra-survey-review-decisions-v2',
        'decision_type': decision_type,
        'mission_id': queue['mission_id'],
        'mission_fingerprint': queue['mission_fingerprint'],
        'artifact_set_id': queue['artifact_set_id'],
        'queue_semantic_sha256': queue['queue_semantic_sha256'],
        'review_queue_sha256': hashlib.sha256(review_queue_path.read_bytes()).hexdigest(),
        'decisions': decisions,
    }


def _registered_survey_actions() -> set[str]:
    parser = cli.build_parser()
    top_level = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    survey = top_level.choices['survey']
    survey_actions = next(
        action
        for action in survey._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return set(survey_actions.choices)


def test_survey_writer_guard_table_covers_every_registered_action(tmp_path: Path) -> None:
    actions = _registered_survey_actions()
    assert set(SURVEY_WRITE_OUTPUT_FIELDS) == actions
    protected = tmp_path / 'mission' / '.artifact_state' / 'sets' / 'orphan' / 'output'
    for action in sorted(actions):
        args = argparse.Namespace(survey_action=action, out=str(protected), metadata_dir=None)
        try:
            cli._guard_survey_write_paths(args)
        except MissionStateError as exc:
            assert exc.code == 'protected_artifact_state_write'
        else:
            raise AssertionError(f'{action} did not reject a protected output path')


def test_workflow_metadata_target_rejects_protected_root_before_mission_write(tmp_path: Path, capsys) -> None:
    mission_dir = tmp_path / 'mission'
    protected = mission_dir / '.artifact_state' / 'metadata'
    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Protected path test',
        '--seed',
        'arxiv:0000.00000',
        '--out',
        str(mission_dir),
        '--metadata-dir',
        str(protected),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload['blocked_reason'] == 'protected_artifact_state_write'
    assert not mission_dir.exists()


def test_cli_survey_packet_composes_public_source_packet_with_blockers(tmp_path: Path, capsys) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    output = tmp_path / 'phase6_packet'

    rc = main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-survey-public-source-packet-result-v1'
    assert payload['status'] == 'packet_composed_with_blockers'
    assert payload['packet_ready_for_writer'] is True
    assert payload['ready_for_prose'] is False
    assert payload['supported_claim_count'] == 0
    assert payload['blocked_claim_count'] == 1
    for name in [
        'candidate_ledger.json',
        'citation_map.json',
        'source_support.json',
        'paper_classifications.json',
        'claim_support.json',
        'omission_risk.json',
        'source_safety_status.json',
        'ready_for_prose.json',
        'survey_packet.md',
        'build_manifest.json',
    ]:
        assert (output / name).exists()

    candidate_ledger = json.loads((output / 'candidate_ledger.json').read_text())
    assert candidate_ledger['included'][0]['source_status'] == 'available'
    assert candidate_ledger['included'][0]['technical_claim_support'] == 'not_supported_until_claim_mapping_review'
    claim_support = json.loads((output / 'claim_support.json').read_text())
    assert claim_support['claims'] == []
    assert claim_support['claim_candidates'][0]['status'] == 'review_required'
    assert claim_support['claim_candidates'][0]['support_class'] == 'anchor_candidate_not_support'
    assert claim_support['claim_candidates'][0]['anchor_ids'] == ['section:sec-method']
    assert claim_support['claim_candidates'][0]['claim_support_allowed'] is False
    assert claim_support['claim_support_policy']['unreviewed_anchor_support_allowed_for_technical_claims'] is False
    assert claim_support['claim_support_policy']['claim_candidates_are_not_supported_claims'] is True
    safety_status = json.loads((output / 'source_safety_status.json').read_text())
    assert safety_status['status'] == 'blocked_or_not_checked'
    assert safety_status['blocking_count'] == 1
    assert safety_status['rows'][0]['retraction_or_version_status'] == 'not_checked_phase5'
    assert safety_status['rows'][0]['claim_support_allowed'] is False
    assert safety_status['safety_policy']['source_availability_safety_allowed'] is False
    ready = json.loads((output / 'ready_for_prose.json').read_text())
    assert 'no reviewed supported technical claim rows are present' in ready['blockers']
    assert 'retraction/version safety is not checked clear for all sourced papers' in ready['blockers']
    manifest = json.loads((output / 'build_manifest.json').read_text())
    assert manifest['source_safety_status'] == 'blocked_or_not_checked'
    assert manifest['source_safety_blocker_count'] == 1
    assert manifest['workflow_state']['state'] == 'public_source_packet_blocked_for_prose'
    assert manifest['workflow_state']['ready_for_writer'] is True
    assert manifest['workflow_state']['ready_for_prose'] is False
    assert any('map proposed technical claims' in command for command in manifest['workflow_state']['safe_next_commands'])
    survey_packet = (output / 'survey_packet.md').read_text()
    assert 'Ready for final prose: `false`' in survey_packet
    assert 'Citation edges are metadata-only coverage/navigation signals, not technical support.' in survey_packet
    assert 'Review-required claim candidates: 1' in survey_packet
    assert 'Packet safety status: `blocked_or_not_checked`' in survey_packet
    assert 'claim support allowed `false`' in survey_packet


def test_cli_survey_packet_blocks_unsupported_claim_rows(tmp_path: Path, capsys) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    claim_support_path = anchor_dir / 'claim_support.json'
    claim_support = json.loads(claim_support_path.read_text())
    claim_support['claims'] = [
        {
            'claim_id': 'claim_unsafely_supported',
            'status': 'supported',
            'support_class': 'metadata_only',
            'claim': 'Neural Optimal Transport is the best method.',
        }
    ]
    claim_support_path.write_text(json.dumps(claim_support))

    rc = main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(tmp_path / 'blocked_packet'),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked'
    assert payload['blocked_reason'] == 'unsupported_claim_rows'
    assert payload['details']['unsupported_claims'][0]['claim_id'] == 'claim_unsafely_supported'


def test_cli_survey_run_public_source_workflow_stops_at_public_metadata_gate(tmp_path: Path, capsys) -> None:
    output = tmp_path / 'mission'

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-survey-public-source-orchestration-result-v1'
    assert payload['status'] == 'blocked_at_gate'
    assert payload['next_gate']['gate_id'] == 'public_metadata'
    assert payload['next_gate']['approval_required'] is True
    assert 'single mission public-discovery confirmation' in payload['next_gate']['approval_scope']
    confirmation = payload['public_discovery_confirmation']
    assert confirmation['confirmed'] is False
    assert confirmation['question'] == 'Do you want RA to search public web/archive sources for this idea or paper?'
    assert confirmation['scope']['providers'] == ['arxiv']
    assert confirmation['scope']['allowed_domains'] == ['arxiv.org', 'export.arxiv.org']
    assert confirmation['scope']['caps']['max_metadata_records'] == 25
    assert 'capped_public_arxiv_source_package_retrieval' in confirmation['scope']['allowed_actions']
    assert 'technical_claim_support_from_metadata_or_source_availability' in confirmation['forbidden_actions']
    assert (output / 'mission_control.json').exists()
    mission = json.loads((output / 'mission_control.json').read_text())
    assert mission['phase_statuses']['offline_skeleton']['exists'] is False
    assert mission['phase_statuses']['public_metadata']['exists'] is False
    assert mission['public_discovery_confirmation'] == confirmation
    assert any('ask once: Do you want RA to search public web/archive sources' in command for command in mission['safe_next_commands'])
    assert all('openalex' not in command.casefold() for command in mission['safe_next_commands'])
    assert any('--public-metadata-provider arxiv' in command for command in mission['safe_next_commands'])
    assert any('do not run public discovery before public_discovery_confirmation.confirmed is true' in action for action in mission['forbidden_actions'])
    assert 'scientific correctness' in mission['what_is_not_concluded']


def test_cli_survey_run_public_source_workflow_can_create_safe_local_skeleton(tmp_path: Path, capsys) -> None:
    output = tmp_path / 'mission_with_skeleton'

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
        '--run-safe-local',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'blocked_at_gate'
    assert payload['next_gate']['gate_id'] == 'public_metadata'
    assert (output / 'offline_skeleton' / 'build_manifest.json').exists()
    assert (output / 'offline_skeleton' / 'workflow_state.json').exists()
    mission = json.loads((output / 'mission_control.json').read_text())
    assert mission['phase_statuses']['offline_skeleton']['exists'] is True
    assert mission['actions'][0]['status'] == 'created_skeleton'
    assert mission['actions'][0]['live_or_download_action'] is False
    assert mission['workflow_state']['ready_for_prose'] is False


def test_cli_survey_run_public_source_workflow_confirmed_discovery_runs_metadata_once(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    output = tmp_path / 'mission_confirmed_discovery'

    def fake_collect_public_metadata(*, topic: str, seeds: list[str], providers: list[str], max_records: int, fetched_at: str) -> dict:
        assert topic == 'Neural Optimal Transport for generative modeling and inference'
        assert seeds == ['arxiv:2201.12220v3']
        assert providers == ['arxiv']
        assert max_records == 25
        return {
            'status': 'metadata_collected',
            'fetched_at': fetched_at,
            'provider_statuses': [
                {
                    'provider': 'arxiv', 'query_kind': 'seed_resolution',
                    'normalized_seed_key': 'arxiv:2201.12220v3', 'topic_query': False,
                    'query_cap': 5, 'status': 'available', 'record_count': 1,
                    'raw_response_saved': False,
                },
                {
                    'provider': 'arxiv', 'query_kind': 'topic_search',
                    'normalized_seed_key': None, 'topic_query': True,
                    'query_cap': 12, 'status': 'available', 'record_count': 0,
                    'raw_response_saved': False,
                },
            ],
            'raw_response_policy': {
                'raw_responses_saved': False,
                'privacy_scan': 'not_applicable_raw_responses_not_saved',
                'reason': 'test fixture',
            },
            'records': [
                {
                    'record_key': 'arxiv:2201.12220v3',
                    'title': 'Neural Optimal Transport',
                    'authors': ['Alice Example'],
                    'year': 2022,
                    'doi': None,
                    'arxiv_id': '2201.12220v3',
                    'openalex_id': None,
                    'landing_page_url': 'https://arxiv.org/abs/2201.12220v3',
                    'citation_count': None,
                    'providers': ['arxiv'],
                    'roles': [],
                    'provider_records': [
                        {
                            'provider': 'arxiv', 'query_kind': 'seed_resolution',
                            'source_id': '2201.12220v3', 'primary_category': 'cs.LG',
                            'published': '2022-01-01',
                        },
                    ],
                    'referenced_works': [],
                    'query_provenance': [
                        {
                            'provider': 'arxiv', 'query_kind': 'seed_resolution',
                            'normalized_seed_key': 'arxiv:2201.12220v3',
                            'topic_query': False,
                        },
                    ],
                },
            ],
        }

    monkeypatch.setattr('research_assistant.survey.build._collect_public_metadata', fake_collect_public_metadata)

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
        '--confirm-public-discovery',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'blocked_at_gate'
    assert payload['public_discovery_confirmation']['confirmed'] is True
    assert payload['next_gate']['gate_id'] == 'source_intake'
    assert payload['next_gate']['approval_required'] is False
    assert payload['next_gate']['covered_by_public_discovery'] is True
    assert payload['next_gate']['implementation_or_artifact_blocker'] is True
    assert 'mission public-discovery confirmation' in payload['next_gate']['approval_scope']
    assert any('do not request a second ordinary public source/archive approval' in command for command in payload['safe_next_commands'])
    assert 'public_metadata_manifest' in payload['artifact_paths']
    assert (output / 'public_metadata' / 'candidate_ledger.json').exists()
    assert (output / 'public_metadata' / 'metadata_provenance.json').exists()
    mission = json.loads((output / 'mission_control.json').read_text())
    assert mission['public_discovery_confirmation']['confirmed'] is True
    assert mission['phase_statuses']['public_metadata']['exists'] is True
    assert mission['phase_statuses']['source_intake']['exists'] is False
    assert mission['next_action']['status'] == 'blocked_missing_public_source_intake_artifact'
    assert mission['next_action']['mission_status'] == 'blocked_at_gate'
    assert mission['actions'][1]['action'] == 'survey_build_public_metadata'
    assert mission['actions'][1]['public_discovery_confirmed'] is True
    assert mission['actions'][1]['source_pdf_full_text_attempted'] is False
    assert mission['actions'][1]['technical_claim_support_created'] is False
    source_support = json.loads((output / 'public_metadata' / 'source_support.json').read_text())
    assert source_support['status'] == 'metadata_only_no_sources_inspected'
    claim_support = json.loads((output / 'public_metadata' / 'claim_support.json').read_text())
    assert claim_support['claim_support_policy']['metadata_only_support_allowed_for_technical_claims'] is False
    assert 'technical claim support' in mission['what_is_not_concluded']


def test_cli_survey_run_public_source_workflow_recognizes_existing_ledgers(tmp_path: Path, capsys) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    rc = main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ])
    assert rc == 0
    capsys.readouterr()

    output = tmp_path / 'mission_with_ledgers'
    payload, review_queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=output,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )

    assert payload['status'] == 'blocked_at_gate'
    assert payload['next_gate']['gate_id'] == 'claim_safety_omission_review'
    assert payload['next_gate']['approval_required'] is True
    assert Path(payload['review_queue_path']).parent.parent.parent.parent == output
    assert payload['review_queue_counts']['by_type']['claim_candidate'] == 1
    assert payload['review_queue_counts']['by_type']['source_safety'] == 1
    assert payload['review_queue_counts']['by_type']['omission_risk'] == 5
    assert payload['review_queue_counts']['by_type']['workflow_blocker'] == 4
    mission = json.loads((output / 'mission_control.json').read_text())
    assert mission['phase_statuses']['public_metadata']['exists'] is True
    assert mission['phase_statuses']['source_intake']['exists'] is True
    assert mission['phase_statuses']['source_anchors']['exists'] is True
    assert mission['phase_statuses']['public_source_packet']['exists'] is True
    assert mission['review_queue_path'] == payload['review_queue_path']
    assert mission['review_queue_counts'] == payload['review_queue_counts']
    assert any('review claim_candidates' in command for command in mission['safe_next_commands'])
    assert any('claim support' in action for action in mission['forbidden_actions'])
    assert review_queue['schema_version'] == 'ra-survey-public-source-review-queue-v2'
    assert review_queue['status'] == 'review_required'
    assert review_queue['queue_counts'] == payload['review_queue_counts']
    assert set(review_queue['packet_input_digests']) == {
        'build_manifest',
        'claim_support',
        'source_safety_status',
    }
    assert review_queue['coverage_lineage_sha256']
    assert review_queue['queue_semantic_sha256']
    assert review_queue['artifact_set_id'] == payload['artifact_state']['artifact_set_id']
    assert set(review_queue['allowed_item_statuses']) == {
        'review_required',
        'blocked_pending_evidence',
        'blocked_pending_approval',
    }
    items_by_type = {}
    for item in review_queue['items']:
        items_by_type.setdefault(item['queue_type'], []).append(item)
    assert items_by_type['claim_candidate'][0]['status'] == 'review_required'
    assert items_by_type['claim_candidate'][0]['claim_support_allowed'] is False
    assert items_by_type['claim_candidate'][0]['support_class'] == 'anchor_candidate_not_support'
    assert items_by_type['source_safety'][0]['status'] == 'blocked_pending_evidence'
    assert items_by_type['source_safety'][0]['safety_checked_clear'] is False
    assert items_by_type['source_safety'][0]['claim_support_allowed'] is False
    assert all(item['literature_completeness_allowed'] is False for item in items_by_type['omission_risk'])
    assert {item['source_id'] for item in items_by_type['omission_risk']} >= {
        'metadata_relations_unverified',
        'backward_snowball_frontier_blocked_or_empty',
        'forward_snowball_frontier_blocked_or_empty',
    }
    assert all(item['ready_for_prose'] is False for item in items_by_type['workflow_blocker'])
    assert 'technical claim support' in review_queue['what_is_not_concluded']


def test_workflow_rejects_symlinked_packet_member_before_artifact_initialization(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()
    claim_path = packet_dir / 'claim_support.json'
    external = tmp_path / 'external_claim_support.json'
    external.write_bytes(claim_path.read_bytes())
    claim_path.unlink()
    claim_path.symlink_to(external)

    mission_dir = tmp_path / 'symlinked_packet_mission'
    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(mission_dir),
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--packet-dir',
        str(packet_dir),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload['blocked_reason'] == 'unsafe_artifact_path'
    assert not (mission_dir / '.artifact_state').exists()


def test_cli_survey_import_claim_review_writes_sidecar_without_prose_promotion(tmp_path: Path, capsys) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    rc = main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ])
    assert rc == 0
    capsys.readouterr()

    mission_dir = tmp_path / 'mission_with_queue'
    queue_payload, queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=mission_dir,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )
    review_queue_path = Path(queue_payload['review_queue_path'])
    claim_item_id = _queue_item_id(queue, 'claim_candidate')
    decisions = tmp_path / 'review_decisions.json'
    decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        'claim_candidate',
        [
            {
                'queue_item_id': claim_item_id,
                'claim_id': 'reviewed_claim_001',
                'claim_text': 'The source contains a method section relevant to Neural Optimal Transport.',
                'paper_ids': ['paper_arxiv_2201_1a5af737'],
                'anchor_ids': ['section:sec-method'],
                'review_status': 'human_reviewed_passed',
                'support_class': 'primary_technical_support',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Checked the local source anchor for this fixture.',
            }
        ],
    )))
    output = tmp_path / 'reviewed_claim_import'

    rc = main([
        'survey',
        'import-claim-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(decisions),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'reviewed_claims_complete'
    assert payload['accepted_claim_count'] == 1
    assert payload['rejected_claim_count'] == 0
    assert payload['ready_for_prose'] is False
    assert payload['decision_coverage_complete'] is True
    assert payload['ready_for_reviewed_packet'] is False
    reviewed = json.loads((output / 'reviewed_claims.json').read_text())
    assert reviewed['claims'][0]['claim_support_allowed'] is True
    assert reviewed['claims'][0]['ready_for_prose'] is False
    assert reviewed['claims'][0]['source_safety_required'] is True
    assert reviewed['claims'][0]['omission_review_required'] is True
    assert reviewed['ready_for_prose'] is False
    assert 'source safety' in reviewed['what_is_not_concluded']
    assert json.loads((packet_dir / 'ready_for_prose.json').read_text())['ready_for_prose'] is False


def test_cli_survey_import_claim_review_rejects_unsafe_support(tmp_path: Path, capsys) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()
    mission_dir = tmp_path / 'mission_with_queue'
    queue_payload, queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=mission_dir,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )
    claim_item_id = _queue_item_id(queue, 'claim_candidate')
    decisions = tmp_path / 'unsafe_review_decisions.json'
    decisions.write_text(json.dumps(_bound_review_decisions(
        Path(queue_payload['review_queue_path']),
        queue,
        'claim_candidate',
        [
            {
                'queue_item_id': claim_item_id,
                'claim_id': 'bad_metadata_claim',
                'claim_text': 'Metadata proves the method is best.',
                'paper_ids': ['paper_arxiv_2201_1a5af737'],
                'anchor_ids': ['section:sec-method'],
                'review_status': 'human_reviewed_passed',
                'support_class': 'metadata_only',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Unsafe metadata-only support.',
            },
            {
                'queue_item_id': 'missing_queue_item',
                'claim_id': 'bad_unknown_queue',
                'claim_text': 'Unknown queue item.',
                'paper_ids': ['paper_arxiv_2201_1a5af737'],
                'anchor_ids': ['section:sec-method'],
                'review_status': 'human_reviewed_passed',
                'support_class': 'primary_technical_support',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Unknown queue item.',
            },
            {
                'queue_item_id': claim_item_id,
                'claim_id': 'bad_missing_anchor',
                'claim_text': 'Missing anchor.',
                'paper_ids': ['paper_arxiv_2201_1a5af737'],
                'anchor_ids': [],
                'review_status': 'human_reviewed_passed',
                'support_class': 'primary_technical_support',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Missing anchor.',
            },
            {
                'queue_item_id': claim_item_id,
                'claim_id': 'ambiguous_nonpass_status',
                'claim_text': 'A bare review status must not enable claim support.',
                'paper_ids': ['paper_arxiv_2201_1a5af737'],
                'anchor_ids': ['section:sec-method'],
                'review_status': 'human_reviewed',
                'support_class': 'primary_technical_support',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'No explicit pass status was supplied.',
            },
        ],
    )))
    output = tmp_path / 'unsafe_reviewed_claim_import'

    rc = main([
        'survey',
        'import-claim-review',
        '--review-queue',
        queue_payload['review_queue_path'],
        '--decisions',
        str(decisions),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked_invalid_claim_decisions'
    assert payload['accepted_claim_count'] == 0
    assert payload['rejected_claim_count'] == 4
    reviewed = json.loads((output / 'reviewed_claims.json').read_text())
    reasons = [reason for row in reviewed['rejected_claims'] for reason in row['reasons']]
    assert 'support_class must be primary_technical_support, project_derivation, or implementation_evidence' in reasons
    assert 'queue_item_id does not reference the required decision type' in reasons
    assert 'anchor_ids must not be empty' in reasons
    assert 'review_status must be a reviewed-pass status' in reasons
    assert reviewed['decision_coverage_complete'] is False


def test_cli_survey_import_source_safety_review_writes_sidecar_without_prose_promotion(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()

    mission_dir = tmp_path / 'mission_with_queue'
    queue_payload, queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=mission_dir,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )
    review_queue_path = Path(queue_payload['review_queue_path'])
    source_safety_item_id = _queue_item_id(queue, 'source_safety')
    decisions = tmp_path / 'source_safety_decisions.json'
    decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        'source_safety',
        [
            {
                'queue_item_id': source_safety_item_id,
                'paper_id': 'paper_arxiv_2201_1a5af737',
                'checked_status': 'checked_clear',
                'evidence_type': 'public_status_check',
                'evidence_source': 'local-test-public-status-ledger',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Fixture-level reviewed status check for import plumbing only.',
            }
        ],
    )))
    output = tmp_path / 'reviewed_source_safety_import'

    rc = main([
        'survey',
        'import-source-safety-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(decisions),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'reviewed_source_safety_complete'
    assert payload['accepted_source_safety_count'] == 1
    assert payload['rejected_source_safety_count'] == 0
    assert payload['checked_clear_count'] == 1
    assert payload['ready_for_prose'] is False
    assert payload['decision_coverage_complete'] is True
    assert payload['ready_for_reviewed_packet'] is False
    reviewed = json.loads((output / 'reviewed_source_safety.json').read_text())
    assert reviewed['source_safety'][0]['safety_checked_clear'] is True
    assert reviewed['source_safety'][0]['claim_support_allowed'] is True
    assert reviewed['source_safety'][0]['ready_for_prose'] is False
    assert reviewed['source_safety'][0]['omission_review_required'] is True
    assert reviewed['ready_for_prose'] is False
    assert reviewed['decision_coverage_complete'] is True
    assert 'final prose readiness' in reviewed['what_is_not_concluded']
    assert json.loads((packet_dir / 'ready_for_prose.json').read_text())['ready_for_prose'] is False


def test_cli_survey_import_source_safety_review_rejects_unsafe_safety(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()
    mission_dir = tmp_path / 'mission_with_queue'
    queue_payload, queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=mission_dir,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )
    source_safety_item_id = _queue_item_id(queue, 'source_safety')
    decisions = tmp_path / 'unsafe_source_safety_decisions.json'
    decisions.write_text(json.dumps(_bound_review_decisions(
        Path(queue_payload['review_queue_path']),
        queue,
        'source_safety',
        [
            {
                'queue_item_id': source_safety_item_id,
                'paper_id': 'paper_arxiv_2201_1a5af737',
                'checked_status': 'checked_clear',
                'evidence_type': 'metadata_only',
                'evidence_source': 'metadata fixture',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Unsafe metadata-only safety.',
            },
            {
                'queue_item_id': 'missing_source_safety_item',
                'paper_id': 'paper_arxiv_2201_1a5af737',
                'checked_status': 'checked_clear',
                'evidence_type': 'public_status_check',
                'evidence_source': 'local-test-public-status-ledger',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Unknown queue item.',
            },
            {
                'queue_item_id': source_safety_item_id,
                'paper_id': 'paper_arxiv_wrong',
                'checked_status': 'blocked',
                'evidence_type': 'public_status_check',
                'evidence_source': 'local-test-public-status-ledger',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
                'evidence_note': 'Wrong paper id.',
                'reason': 'Wrong paper id remains blocked.',
                'next_action': 'Correct the paper id and rerun review.',
            },
        ],
    )))
    output = tmp_path / 'unsafe_reviewed_source_safety_import'

    rc = main([
        'survey',
        'import-source-safety-review',
        '--review-queue',
        queue_payload['review_queue_path'],
        '--decisions',
        str(decisions),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked_invalid_source_safety_decisions'
    assert payload['accepted_source_safety_count'] == 0
    assert payload['rejected_source_safety_count'] == 3
    reviewed = json.loads((output / 'reviewed_source_safety.json').read_text())
    reasons = [reason for row in reviewed['rejected_source_safety'] for reason in row['reasons']]
    assert 'evidence_type cannot be metadata, source availability, citation, venue, abstract, or context-only' in reasons
    assert 'checked_clear requires public_status_check or reviewed_primary_source_status evidence' in reasons
    assert 'queue_item_id does not reference the required decision type' in reasons
    assert 'paper_id must match the referenced source_safety queue item' in reasons


def test_cli_survey_import_omission_review_writes_sidecar_without_completeness_promotion(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()

    mission_dir = tmp_path / 'mission_with_queue'
    queue_payload, queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=mission_dir,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )
    review_queue_path = Path(queue_payload['review_queue_path'])
    omission_items = [item for item in queue['items'] if item['queue_type'] == 'omission_risk']
    decisions = tmp_path / 'omission_review_decisions.json'
    decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        'omission_risk',
        [
            {
                'queue_item_id': item['item_id'],
                'risk_id': item['risk_id'],
                'decision': 'must_inspect',
                'reason': 'Metadata relations remain unverified and need source-aware review.',
                'next_action': 'Inspect source references before final prose.',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            }
            for item in omission_items
        ]
    )))
    output = tmp_path / 'reviewed_omission_import'

    rc = main([
        'survey',
        'import-omission-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(decisions),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'reviewed_omissions_complete'
    assert payload['accepted_omission_count'] == len(omission_items)
    assert payload['rejected_omission_count'] == 0
    assert payload['open_omission_count'] == len(omission_items)
    assert payload['decision_coverage_complete'] is True
    assert payload['literature_completeness_allowed'] is False
    assert payload['ready_for_prose'] is False
    reviewed = json.loads((output / 'reviewed_omission_risks.json').read_text())
    assert reviewed['omission_risks'][0]['status'] == 'open'
    assert reviewed['omission_risks'][0]['literature_completeness_allowed'] is False
    assert reviewed['omission_risks'][0]['ready_for_prose'] is False
    assert reviewed['literature_completeness_allowed'] is False
    assert reviewed['ready_for_prose'] is False
    assert 'literature completeness' in reviewed['what_is_not_concluded']
    assert json.loads((packet_dir / 'ready_for_prose.json').read_text())['ready_for_prose'] is False


def test_cli_survey_import_omission_review_rejects_unsafe_omissions(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()
    mission_dir = tmp_path / 'mission_with_queue'
    queue_payload, queue = _initialize_selected_review_queue(
        capsys=capsys,
        mission_dir=mission_dir,
        metadata_dir=metadata_dir,
        source_status_dir=source_status_dir,
        anchor_dir=anchor_dir,
        packet_dir=packet_dir,
    )
    omission_items = [item for item in queue['items'] if item['queue_type'] == 'omission_risk']
    omission_item_id = _queue_item_id(queue, 'omission_risk', 'metadata_relations_unverified')
    decisions = tmp_path / 'unsafe_omission_review_decisions.json'
    decisions.write_text(json.dumps(_bound_review_decisions(
        Path(queue_payload['review_queue_path']),
        queue,
        'omission_risk',
        [
            {
                'queue_item_id': omission_item_id,
                'risk_id': 'metadata_relations_unverified',
                'decision': 'must_inspect',
                'reason': 'Needs source-aware review.',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            },
            {
                'queue_item_id': 'missing_omission_item',
                'risk_id': 'metadata_relations_unverified',
                'decision': 'acceptable_omission',
                'reason': 'Unknown queue item.',
                'scope_basis': 'Fixture scope.',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            },
            {
                'queue_item_id': omission_item_id,
                'risk_id': 'wrong_risk',
                'decision': 'out_of_scope',
                'reason': 'Wrong risk id.',
                'scope_basis': 'Fixture scope.',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            },
        ],
    )))
    output = tmp_path / 'unsafe_reviewed_omission_import'

    rc = main([
        'survey',
        'import-omission-review',
        '--review-queue',
        queue_payload['review_queue_path'],
        '--decisions',
        str(decisions),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked_invalid_omission_decisions'
    assert payload['accepted_omission_count'] == 0
    assert payload['rejected_omission_count'] == 3
    reviewed = json.loads((output / 'reviewed_omission_risks.json').read_text())
    reasons = [reason for row in reviewed['rejected_omission_risks'] for reason in row['reasons']]
    assert 'omission decision row 1 fields do not match exact schema' in reasons
    assert 'queue_item_id does not reference the required decision type' in reasons
    assert 'risk_id must match the referenced omission_risk queue item' in reasons


def test_cli_survey_merge_reviewed_evidence_blocks_until_all_gates_clear(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    output = tmp_path / 'reviewed_evidence_merge'

    rc = main([
        'survey',
        'merge-reviewed-evidence',
        '--review-queue',
        str(sidecars['review_queue']),
        '--reviewed-claims',
        str(sidecars['reviewed_claims']),
        '--reviewed-source-safety',
        str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions',
        str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers',
        str(sidecars['reviewed_workflow_blockers']),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'reviewed_evidence_blocked'
    assert payload['decision_coverage_complete'] is True
    assert payload['ready_for_reviewed_packet'] is False
    assert payload['ready_for_prose'] is False
    assert payload['blocker_count'] >= 1
    merged = json.loads((output / 'reviewed_evidence_status.json').read_text())
    assert merged['ready_for_prose'] is False
    assert any('omission decision remains open' in blocker for blocker in merged['blockers'])
    assert merged['counts']['claim_candidate'] == 1
    assert merged['counts']['source_safety'] == 1
    assert merged['counts']['omission_risk'] == sum(
        item['queue_type'] == 'omission_risk' for item in json.loads(sidecars['review_queue'].read_text())['items']
    )
    assert merged['counts']['workflow_blocker'] == sum(
        item['queue_type'] == 'workflow_blocker' for item in json.loads(sidecars['review_queue'].read_text())['items']
    )
    assert 'product readiness' in merged['what_is_not_concluded']


def test_cli_survey_merge_unavailable_source_veto_is_valid_blocked_result(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, 'merge_reviewed_evidence', lambda **_: {
        'schema_version': 'ra-survey-reviewed-evidence-merge-result-v1',
        'status': 'reviewed_evidence_blocked_unavailable_source_outcome',
        'decision_coverage_complete': True,
        'ready_for_reviewed_packet': False,
        'ready_for_prose': False,
        'blocker_count': 1,
        'what_is_not_concluded': ['source safety in fact'],
    })

    rc = main([
        'survey',
        'merge-reviewed-evidence',
        '--review-queue', str(tmp_path / 'queue.json'),
        '--reviewed-claims', str(tmp_path / 'claims.json'),
        '--reviewed-source-safety', str(tmp_path / 'source.json'),
        '--reviewed-omissions', str(tmp_path / 'omissions.json'),
        '--reviewed-workflow-blockers', str(tmp_path / 'workflow.json'),
        '--out', str(tmp_path / 'reviewed_evidence'),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'reviewed_evidence_blocked_unavailable_source_outcome'
    assert payload['ready_for_reviewed_packet'] is False
    assert payload['ready_for_prose'] is False


def test_cli_survey_merge_reviewed_evidence_rejects_stale_sidecar(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    stale_claims = json.loads(sidecars['reviewed_claims'].read_text())
    stale_claims['review_queue_sha256'] = '0' * 64
    stale_claims_path = tmp_path / 'stale_reviewed_claims.json'
    stale_claims_path.write_text(json.dumps(stale_claims, indent=2, sort_keys=True) + '\n')
    output = tmp_path / 'stale_reviewed_evidence_merge'

    rc = main([
        'survey',
        'merge-reviewed-evidence',
        '--review-queue',
        str(sidecars['review_queue']),
        '--reviewed-claims',
        str(stale_claims_path),
        '--reviewed-source-safety',
        str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions',
        str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers',
        str(sidecars['reviewed_workflow_blockers']),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked_invalid_review_artifacts'
    assert payload['blocked_reason'] == 'unexpected_claim_decision_path'
    assert not output.exists()


def test_cli_survey_merge_rejects_rehashed_sidecar_outcome_rewrite(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    forged = json.loads(sidecars['reviewed_omissions'].read_text())
    row = forged['omission_risks'][0]
    assert row['status'] == 'open'
    row.update({
        'decision': 'acceptable_omission',
        'next_action': '',
        'scope_basis': 'Forged current-scope closure.',
        'status': 'reviewed_closed_for_current_scope',
    })
    row['decision_sha256'] = decision_sha256('omission_risk', row)
    forged['open_omission_count'] -= 1
    forged['closed_omission_count'] += 1
    forged_path = tmp_path / 'forged_reviewed_omissions.json'
    forged_path.write_text(json.dumps(forged, indent=2, sort_keys=True) + '\n')
    output = tmp_path / 'forged_reviewed_evidence_merge'

    rc = main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(forged_path),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['status'] == 'blocked_invalid_review_artifacts'
    assert payload['blocked_reason'] == 'unexpected_omission_decision_path'
    assert not output.exists()


def test_cli_survey_exact_four_type_merge_is_ready_only_for_reviewed_packet(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    output = tmp_path / 'complete_reviewed_evidence_merge'

    rc = main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'reviewed_evidence_complete'
    assert payload['decision_coverage_complete'] is True
    assert payload['ready_for_reviewed_packet'] is True
    assert payload['ready_for_prose'] is False
    merged = json.loads((output / 'reviewed_evidence_status.json').read_text())
    queue = json.loads(sidecars['review_queue'].read_text())
    assert merged['required_queue_item_ids'] == sorted(item['item_id'] for item in queue['items'])
    assert sum(merged['counts'][name] for name in [
        'claim_candidate', 'source_safety', 'omission_risk', 'workflow_blocker'
    ]) == merged['counts']['queue_total']
    assert merged['blockers'] == []
    assert merged['ready_for_prose'] is False
    assert 'scientific correctness' in merged['what_is_not_concluded']


@pytest.mark.parametrize('checked_status', ['quarantined', 'blocked'])
def test_cli_survey_merge_keeps_nonclear_source_outcomes_blocked(
    tmp_path: Path,
    capsys,
    checked_status: str,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    decisions_path = tmp_path / f'{checked_status}-source-review-v3.json'
    decisions_path.write_bytes(pretty_json_bytes(_canonical_v3_source_envelope(
        sidecars['review_queue'],
        sidecars['reviewed_source_safety_root'],
        observation_outcome=(
            'quarantined' if checked_status == 'quarantined'
            else 'checked_clear_for_recorded_checks'
        ),
        decision=checked_status,
    )))

    assert main([
        'survey', 'import-source-safety-review',
        '--review-queue', str(sidecars['review_queue']),
        '--decisions', str(decisions_path),
        '--out', str(sidecars['reviewed_source_safety_root']),
        '--force',
    ]) == 0
    imported = json.loads(capsys.readouterr().out)
    sidecars['reviewed_source_safety'] = Path(imported['reviewed_source_safety_path'])
    assert imported[f'{checked_status}_count'] == 1

    output = tmp_path / f'{checked_status}_source_merge'
    assert main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(output),
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    merged = json.loads((output / 'reviewed_evidence_status.json').read_text())

    assert result['status'] == 'reviewed_evidence_blocked'
    assert result['ready_for_reviewed_packet'] is False
    assert result['ready_for_prose'] is False
    assert any('unsafe_claim_dependency:' in blocker for blocker in merged['blockers'])


def test_cli_survey_merge_keeps_accepted_open_workflow_disposition_blocked(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    decisions_path = tmp_path / 'open-workflow-review.json'
    envelope = json.loads(sidecars['workflow_decisions'].read_text())
    decision = next(
        row for row in envelope['decisions']
        if row['disposition'] == 'resolved_by_reviewed_evidence'
    )
    decision['disposition'] = 'remains_open'
    decision.pop('evidence_queue_item_ids')
    decision['next_action'] = 'Keep the aggregate workflow blocker open for explicit repair.'
    decisions_path.write_bytes(pretty_json_bytes(envelope))

    assert main([
        'survey', 'import-workflow-blocker-review',
        '--review-queue', str(sidecars['review_queue']),
        '--decisions', str(decisions_path),
        '--out', str(sidecars['reviewed_workflow_blockers'].parent),
        '--force',
    ]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported['open_workflow_blocker_count'] >= 1

    output = tmp_path / 'open_workflow_merge'
    assert main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(output),
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    merged = json.loads((output / 'reviewed_evidence_status.json').read_text())

    assert result['status'] == 'reviewed_evidence_blocked'
    assert result['ready_for_reviewed_packet'] is False
    assert result['ready_for_prose'] is False
    assert any('workflow blocker remains open' in blocker for blocker in merged['blockers'])


def test_cli_survey_exact_review_retry_and_merge_no_force_preserve_existing_output_bytes(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    claim_sidecar = json.loads(sidecars['reviewed_claims'].read_text())
    original_claim_bytes = sidecars['reviewed_claims'].read_bytes()

    assert main([
        'survey', 'import-claim-review',
        '--review-queue', str(sidecars['review_queue']),
        '--decisions', claim_sidecar['decisions_path'],
        '--out', str(sidecars['reviewed_claims_root']),
    ]) == 0
    import_result = json.loads(capsys.readouterr().out)
    assert import_result['status'] == 'reviewed_claims_complete'
    assert Path(import_result['reviewed_claims_path']) == sidecars['reviewed_claims']
    assert sidecars['reviewed_claims'].read_bytes() == original_claim_bytes

    merge_dir = tmp_path / 'no_force_merge'
    merge_command = [
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(merge_dir),
    ]
    assert main(merge_command) == 0
    capsys.readouterr()
    merge_path = merge_dir / 'reviewed_evidence_status.json'
    original_merge_bytes = merge_path.read_bytes()

    assert main(merge_command) == 1
    merge_result = json.loads(capsys.readouterr().out)
    assert merge_result['blocked_reason'] == 'output_exists'
    assert merge_path.read_bytes() == original_merge_bytes


def test_resume_invalidates_ready_merge_after_current_sidecar_refresh(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'
    assert main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(merge_dir),
    ]) == 0
    merged = json.loads(capsys.readouterr().out)
    assert merged['ready_for_reviewed_packet'] is True

    decisions_path = tmp_path / 'open-omission-review.json'
    decisions = json.loads(sidecars['omission_decisions'].read_text())
    for row in decisions['decisions']:
        row['decision'] = 'must_inspect'
        row['next_action'] = 'Inspect source references before reviewed-packet composition.'
        row.pop('scope_basis')
    decisions_path.write_bytes(pretty_json_bytes(decisions))
    assert main([
        'survey', 'import-omission-review',
        '--review-queue', str(sidecars['review_queue']),
        '--decisions', str(decisions_path),
        '--out', str(sidecars['reviewed_omissions_root']),
        '--force',
    ]) == 0
    refreshed = json.loads(capsys.readouterr().out)
    assert refreshed['open_omission_count'] > 0

    rc = main([
        'survey', 'run-public-source-workflow',
        '--topic', 'Neural Optimal Transport for generative modeling and inference',
        '--seed', 'arxiv:2201.12220v3',
        '--out', str(sidecars['mission_dir']),
        '--metadata-dir', str(sidecars['metadata_dir']),
        '--source-status-dir', str(sidecars['source_status_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['next_action']['action_id'] == 'merge_reviewed_evidence'
    assert payload['next_action']['status'] == 'blocked_pending_reviewed_evidence_merge'
    assert payload['next_action']['action_id'] != 'compose_reviewed_final_packet'
    mission = json.loads((sidecars['mission_dir'] / 'mission_control.json').read_text())
    merge_status = mission['reviewed_artifacts']['reviewed_evidence']
    assert merge_status['exists'] is False
    assert merge_status['ready_for_reviewed_packet'] is False
    assert merge_status['lineage_status'] == 'invalid_source_accounting_replay'


def test_resume_rejects_symlinked_reviewed_evidence_without_following_it(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'
    merge_dir.mkdir()
    (merge_dir / 'reviewed_evidence_status.json').symlink_to(sidecars['reviewed_claims'])

    rc = main([
        'survey', 'run-public-source-workflow',
        '--topic', 'Neural Optimal Transport for generative modeling and inference',
        '--seed', 'arxiv:2201.12220v3',
        '--out', str(sidecars['mission_dir']),
        '--metadata-dir', str(sidecars['metadata_dir']),
        '--source-status-dir', str(sidecars['source_status_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['next_action']['action_id'] == 'merge_reviewed_evidence'
    assert payload['next_action']['action_id'] != 'compose_reviewed_final_packet'
    mission = json.loads((sidecars['mission_dir'] / 'mission_control.json').read_text())
    merge_status = mission['reviewed_artifacts']['reviewed_evidence']
    assert merge_status['exists'] is False
    assert merge_status['lineage_status'] == 'unsafe_review_artifact'
    assert merge_status['ready_for_reviewed_packet'] is False
    assert merge_status['ready_for_prose'] is False


@pytest.mark.parametrize('attack', ['subset', 'superset', 'replacement'])
def test_cli_survey_workflow_review_rejects_inexact_same_type_evidence_scope(
    tmp_path: Path,
    capsys,
    attack: str,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    queue = json.loads(sidecars['review_queue'].read_text())
    payload = json.loads(sidecars['workflow_decisions'].read_text())
    target = next(
        row for row in payload['decisions']
        if row['disposition'] == 'resolved_by_reviewed_evidence'
        and len(row['evidence_queue_item_ids']) >= 1
    )
    required = list(target['evidence_queue_item_ids'])
    same_type = next(
        item['required_evidence_queue_type']
        for item in queue['items']
        if item['item_id'] == target['queue_item_id']
    )
    other_current = [
        item['item_id'] for item in queue['items']
        if item['queue_type'] == same_type and item['item_id'] not in required
    ]
    if attack == 'subset':
        target['evidence_queue_item_ids'] = []
    elif attack == 'superset':
        target['evidence_queue_item_ids'] = [*required, 'claim_candidate-' + 'f' * 24]
    else:
        target['evidence_queue_item_ids'] = other_current or ['claim_candidate-' + 'e' * 24]
    decisions = tmp_path / f'workflow-{attack}.json'
    decisions.write_text(json.dumps(payload))
    output = tmp_path / f'workflow-{attack}-out'

    rc = main([
        'survey', 'import-workflow-blocker-review',
        '--review-queue', str(sidecars['review_queue']),
        '--decisions', str(decisions),
        '--out', str(output),
    ])
    result = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert result['status'] == 'blocked_invalid_workflow_blocker_decisions'
    sidecar = json.loads((output / 'reviewed_workflow_blockers.json').read_text())
    assert sidecar['decision_coverage_complete'] is False
    assert any(
        "exact required evidence scope" in reason
        for rejected in sidecar['rejected_workflow_blockers']
        for reason in rejected['reasons']
    )
    assert sidecar['ready_for_reviewed_packet'] is False
    assert sidecar['ready_for_prose'] is False


@pytest.mark.parametrize('attack', ['subset', 'superset', 'replacement'])
def test_merge_workflow_revalidation_rejects_inexact_same_type_scope(
    tmp_path: Path,
    capsys,
    attack: str,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    queue = json.loads(sidecars['review_queue'].read_text())
    workflow = json.loads(sidecars['reviewed_workflow_blockers'].read_text())
    target = next(
        row for row in workflow['workflow_blockers']
        if row['disposition'] == 'resolved_by_reviewed_evidence'
        and row['required_evidence_queue_item_ids']
    )
    queue_items = {item['item_id']: item for item in queue['items'] if item['queue_type'] == 'workflow_blocker'}
    required = list(target['required_evidence_queue_item_ids'])
    decisions_by_type = {
        'claim_candidate': {
            row['queue_item_id']: row
            for row in json.loads(sidecars['reviewed_claims'].read_text())['claims']
        },
        'source_safety': {
            row['queue_item_id']: row
            for row in json.loads(sidecars['reviewed_source_safety'].read_text())['source_safety']
        },
        'omission_risk': {
            row['queue_item_id']: row
            for row in json.loads(sidecars['reviewed_omissions'].read_text())['omission_risks']
        },
    }
    if attack == 'subset':
        target['evidence_queue_item_ids'] = required[:-1]
    elif attack == 'superset':
        target['evidence_queue_item_ids'] = [*required, 'unknown-' + 'f' * 24]
    else:
        target['evidence_queue_item_ids'] = ['replacement-' + 'e' * 24 for _ in required]

    with pytest.raises(MissionStateError) as error:
        _workflow_blocker(target, queue_items, decisions_by_type)
    assert error.value.code == 'invalid_workflow_resolution'


def test_cli_survey_run_public_source_workflow_resumes_reviewed_evidence_state(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'

    rc = main([
        'survey',
        'merge-reviewed-evidence',
        '--review-queue',
        str(sidecars['review_queue']),
        '--reviewed-claims',
        str(sidecars['reviewed_claims']),
        '--reviewed-source-safety',
        str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions',
        str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers',
        str(sidecars['reviewed_workflow_blockers']),
        '--out',
        str(merge_dir),
    ])
    assert rc == 0
    capsys.readouterr()

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(sidecars['mission_dir']),
        '--metadata-dir',
        str(sidecars['metadata_dir']),
        '--source-status-dir',
        str(sidecars['source_status_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'blocked_at_gate'
    assert payload['review_queue_reused'] is True
    assert payload['next_action']['action_id'] == 'resolve_reviewed_evidence_blockers'
    assert payload['next_action']['status'] == 'blocked_by_reviewed_evidence_merge'
    assert any('omission decision remains open' in blocker for blocker in payload['next_action']['blockers'])
    assert payload['next_action_path'] == str(sidecars['mission_dir'] / 'next_action.json')
    mission = json.loads((sidecars['mission_dir'] / 'mission_control.json').read_text())
    assert mission['resume'] is True
    assert mission['review_queue_reused'] is True
    assert mission['reviewed_artifacts']['reviewed_claims']['exists'] is True
    assert mission['reviewed_artifacts']['reviewed_source_safety']['exists'] is True
    assert mission['reviewed_artifacts']['reviewed_omissions']['exists'] is True
    assert mission['reviewed_artifacts']['reviewed_workflow_blockers']['exists'] is True
    assert mission['reviewed_artifacts']['reviewed_evidence']['exists'] is True
    assert mission['reviewed_artifacts']['reviewed_evidence']['ready_for_prose'] is False
    next_action = json.loads((sidecars['mission_dir'] / 'next_action.json').read_text())
    assert next_action == mission['next_action']
    assert any('merge-reviewed-evidence' in command for command in next_action['safe_next_commands'])
    assert any('do not run live/API/source/PDF/download' in action for action in next_action['forbidden_actions'])


def test_cli_survey_coverage_ledgers_composes_local_snowballing_ledgers(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_dir, source_status_dir, anchor_dir = _write_public_source_packet_fixture(tmp_path)
    packet_dir = tmp_path / 'phase6_packet'
    assert main([
        'survey',
        'packet',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--metadata-dir',
        str(metadata_dir),
        '--source-status-dir',
        str(source_status_dir),
        '--anchor-dir',
        str(anchor_dir),
        '--out',
        str(packet_dir),
    ]) == 0
    capsys.readouterr()
    output = tmp_path / 'coverage_ledgers'

    rc = main([
        'survey',
        'coverage-ledgers',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--packet-dir',
        str(packet_dir),
        '--out',
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-survey-coverage-ledger-result-v1'
    assert payload['status'] == 'coverage_ledgers_composed'
    assert payload['ready_for_prose'] is False
    for name in [
        'backward_snowball.json',
        'forward_snowball.json',
        'citation_venue_metadata.json',
        'paper_classifications.json',
        'omitted_paper_risks.json',
        'coverage_manifest.json',
    ]:
        assert (output / name).exists()
    backward = json.loads((output / 'backward_snowball.json').read_text())
    forward = json.loads((output / 'forward_snowball.json').read_text())
    citation_metadata = json.loads((output / 'citation_venue_metadata.json').read_text())
    omitted = json.loads((output / 'omitted_paper_risks.json').read_text())
    manifest = json.loads((output / 'coverage_manifest.json').read_text())
    assert backward['evidence_policy']['metadata_relations_support_technical_claims'] is False
    assert forward['evidence_policy']['metadata_relations_support_completeness_claims'] is False
    assert citation_metadata['metadata_policy']['citation_counts_are_coverage_signals_only'] is True
    assert citation_metadata['metadata_policy']['metadata_supports_technical_claims'] is False
    assert omitted['review_policy']['omission_visibility_is_not_literature_completeness'] is True
    assert manifest['ready_for_prose'] is False
    assert 'literature completeness' in manifest['what_is_not_concluded']


def test_cli_survey_composes_reviewed_packet_then_runs_packet_only_hostile_review(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'
    reviewed_packet_dir = sidecars['mission_dir'] / 'reviewed_final_packet'
    hostile_dir = sidecars['mission_dir'] / 'hostile_review'

    assert main([
        'survey',
        'merge-reviewed-evidence',
        '--review-queue',
        str(sidecars['review_queue']),
        '--reviewed-claims',
        str(sidecars['reviewed_claims']),
        '--reviewed-source-safety',
        str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions',
        str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers',
        str(sidecars['reviewed_workflow_blockers']),
        '--out',
        str(merge_dir),
    ]) == 0
    capsys.readouterr()
    rc = main([
        'survey',
        'compose-reviewed-final-packet',
        '--mission-root',
        str(sidecars['mission_dir']),
        '--review-queue',
        str(sidecars['review_queue']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--out',
        str(reviewed_packet_dir),
    ])
    composed = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert composed['schema_version'] == 'ra-survey-reviewed-final-packet-result-v1'
    assert composed['status'] == 'reviewed_final_packet_ready_for_hostile_review'
    assert composed['ready_for_hostile_review'] is True
    assert composed['ready_for_prose'] is False

    rc = main([
        'survey',
        'hostile-review',
        '--reviewed-final-packet',
        str(reviewed_packet_dir / 'reviewed_final_packet.json'),
        '--mission-root',
        str(sidecars['mission_dir']),
        '--review-queue',
        str(sidecars['review_queue']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--out',
        str(hostile_dir),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['schema_version'] == 'ra-survey-hostile-review-result-v2'
    assert payload['status'] == 'ready_for_reviewed_prose_within_recorded_scope'
    assert payload['ready_for_prose'] is True
    assert payload['blocker_count'] == 0
    hostile = json.loads((hostile_dir / 'hostile_review_result.json').read_text())
    readiness = json.loads((hostile_dir / 'final_packet_readiness.json').read_text())
    assert hostile['schema_version'] == 'ra-survey-hostile-review-v2'
    assert hostile['ready_for_prose'] is True
    assert readiness['ready_for_prose'] is True
    assert readiness['hostile_review_result_sha256'] == hashlib.sha256(
        (hostile_dir / 'hostile_review_result.json').read_bytes()
    ).hexdigest()
    assert hostile['reviewed_final_packet_sha256'] == composed['reviewed_final_packet_sha256']
    assert any('metadata' in claim for claim in hostile['forbidden_claims'])
    assert 'scientific correctness' in readiness['what_is_not_concluded']

    with pytest.raises(SystemExit):
        main([
            'survey', 'hostile-review',
            '--reviewed-final-packet', str(reviewed_packet_dir / 'reviewed_final_packet.json'),
            '--mission-root', str(sidecars['mission_dir']),
            '--review-queue', str(sidecars['review_queue']),
            '--packet-dir', str(sidecars['packet_dir']),
            '--anchor-dir', str(sidecars['anchor_dir']),
            '--reviewed-evidence', str(merge_dir / 'reviewed_evidence_status.json'),
            '--out', str(hostile_dir),
        ])
    assert 'unrecognized arguments: --reviewed-evidence' in capsys.readouterr().err


def test_orchestration_discovers_phase4_artifacts_and_hands_off_to_phase5(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'
    reviewed_packet_dir = sidecars['mission_dir'] / 'reviewed_final_packet'
    hostile_dir = sidecars['mission_dir'] / 'hostile_review'
    assert main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(merge_dir),
    ]) == 0
    capsys.readouterr()

    resume = [
        'survey', 'run-public-source-workflow',
        '--topic', 'Neural Optimal Transport for generative modeling and inference',
        '--seed', 'arxiv:2201.12220v3',
        '--out', str(sidecars['mission_dir']),
        '--metadata-dir', str(sidecars['metadata_dir']),
        '--source-status-dir', str(sidecars['source_status_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--resume',
    ]
    assert main(resume) == 0
    before_packet = json.loads(capsys.readouterr().out)
    assert before_packet['next_action']['action_id'] == 'compose_reviewed_final_packet'
    compose_command = before_packet['next_action']['safe_next_commands'][0]
    assert '--mission-root' in compose_command
    assert '--review-queue' in compose_command
    assert not reviewed_packet_dir.exists()

    assert main([
        'survey', 'compose-reviewed-final-packet',
        '--mission-root', str(sidecars['mission_dir']),
        '--review-queue', str(sidecars['review_queue']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--out', str(reviewed_packet_dir),
    ]) == 0
    capsys.readouterr()

    assert main(resume) == 0
    before_hostile = json.loads(capsys.readouterr().out)
    assert before_hostile['next_action']['action_id'] == 'run_hostile_review'
    assert before_hostile['next_action']['ready_for_hostile_review'] is True
    assert before_hostile['next_action']['ready_for_prose'] is False
    assert before_hostile['artifact_paths']['reviewed_final_packet_path'] == str(
        reviewed_packet_dir / 'reviewed_final_packet.json'
    )
    assert not hostile_dir.exists()

    assert main([
        'survey', 'hostile-review',
        '--reviewed-final-packet', str(reviewed_packet_dir / 'reviewed_final_packet.json'),
        '--mission-root', str(sidecars['mission_dir']),
        '--review-queue', str(sidecars['review_queue']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--out', str(hostile_dir),
    ]) == 0
    capsys.readouterr()

    assert main(resume) == 0
    handoff = json.loads(capsys.readouterr().out)
    assert handoff['next_action']['action_id'] == 'phase5_executing_supervisor_handoff'
    assert handoff['next_action']['status'] == 'ready_for_phase5_supervisor'
    assert handoff['next_action']['ready_for_prose'] is True
    assert handoff['next_action']['readiness_classification'] == 'READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE'
    assert handoff['artifact_paths']['hostile_review_result_path'] == str(
        hostile_dir / 'hostile_review_result.json'
    )
    assert handoff['next_action']['safe_next_commands'] == []


def test_orchestration_repairs_packet_before_hostile_and_forces_orphan_view_recovery(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'
    reviewed_packet_dir = sidecars['mission_dir'] / 'reviewed_final_packet'
    hostile_dir = sidecars['mission_dir'] / 'hostile_review'
    assert main([
        'survey', 'merge-reviewed-evidence',
        '--review-queue', str(sidecars['review_queue']),
        '--reviewed-claims', str(sidecars['reviewed_claims']),
        '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions', str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
        '--out', str(merge_dir),
    ]) == 0
    capsys.readouterr()
    assert main([
        'survey', 'compose-reviewed-final-packet',
        '--mission-root', str(sidecars['mission_dir']),
        '--review-queue', str(sidecars['review_queue']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--out', str(reviewed_packet_dir),
    ]) == 0
    capsys.readouterr()

    resume = [
        'survey', 'run-public-source-workflow',
        '--topic', 'Neural Optimal Transport for generative modeling and inference',
        '--seed', 'arxiv:2201.12220v3',
        '--out', str(sidecars['mission_dir']),
        '--metadata-dir', str(sidecars['metadata_dir']),
        '--source-status-dir', str(sidecars['source_status_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--resume',
    ]

    hostile_dir.mkdir()
    (hostile_dir / 'final_packet_readiness.json').write_text('{}\n')
    assert main(resume) == 0
    orphan = json.loads(capsys.readouterr().out)
    assert orphan['next_action']['action_id'] == 'run_hostile_review'
    assert orphan['next_action']['safe_next_commands'][0].endswith(' --force')

    assert main([
        'survey', 'hostile-review',
        '--reviewed-final-packet', str(reviewed_packet_dir / 'reviewed_final_packet.json'),
        '--mission-root', str(sidecars['mission_dir']),
        '--review-queue', str(sidecars['review_queue']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--out', str(hostile_dir),
        '--force',
    ]) == 0
    capsys.readouterr()
    packet = json.loads((reviewed_packet_dir / 'reviewed_final_packet.json').read_text())
    packet['readiness_inputs']['ready_for_prose'] = True
    (reviewed_packet_dir / 'reviewed_final_packet.json').write_text(
        json.dumps(packet, indent=2, sort_keys=True) + '\n'
    )

    assert main(resume) == 0
    invalid = json.loads(capsys.readouterr().out)
    assert invalid['next_action']['action_id'] == 'repair_reviewed_final_packet'
    repair = invalid['next_action']['safe_next_commands'][0]
    assert 'compose-reviewed-final-packet' in repair
    assert 'hostile-review' not in repair
    assert repair.endswith(' --force')


def test_cli_survey_run_public_source_workflow_hands_off_to_hostile_review_after_coverage(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    merge_dir = sidecars['mission_dir'] / 'reviewed_evidence'
    coverage_dir = sidecars['coverage_dir']

    assert main([
        'survey',
        'merge-reviewed-evidence',
        '--review-queue',
        str(sidecars['review_queue']),
        '--reviewed-claims',
        str(sidecars['reviewed_claims']),
        '--reviewed-source-safety',
        str(sidecars['reviewed_source_safety']),
        '--reviewed-omissions',
        str(sidecars['reviewed_omissions']),
        '--reviewed-workflow-blockers',
        str(sidecars['reviewed_workflow_blockers']),
        '--out',
        str(merge_dir),
    ]) == 0
    capsys.readouterr()
    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(sidecars['mission_dir']),
        '--metadata-dir',
        str(sidecars['metadata_dir']),
        '--source-status-dir',
        str(sidecars['source_status_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['next_action']['action_id'] == 'resolve_reviewed_evidence_blockers'
    assert payload['next_action']['status'] == 'blocked_by_reviewed_evidence_merge'
    assert not any('hostile-review' in command for command in payload['next_action']['safe_next_commands'])
    assert any('omission decision remains open' in blocker for blocker in payload['next_action']['blockers'])


_CANONICAL_CLI_TOPIC = 'Neural Optimal Transport for generative modeling and inference'
_CANONICAL_CLI_SEED = 'arxiv:2201.12220v3'


def _canonical_cli_metadata_collection(
    *,
    topic: str,
    seeds: list[str],
    providers: list[str],
    max_records: int,
    fetched_at: str,
) -> dict:
    assert topic == _CANONICAL_CLI_TOPIC
    assert seeds == [_CANONICAL_CLI_SEED]
    assert providers == ['arxiv']
    assert max_records == 25
    provider_statuses = []
    for provider in ('arxiv',):
        provider_statuses.extend([
            {
                'provider': provider,
                'query_kind': 'seed_resolution',
                'normalized_seed_key': _CANONICAL_CLI_SEED,
                'topic_query': False,
                'query_cap': 5,
                'status': 'available',
                'record_count': 1,
                'raw_response_saved': False,
            },
            {
                'provider': provider,
                'query_kind': 'topic_search',
                'normalized_seed_key': None,
                'topic_query': True,
                'query_cap': 12,
                'status': 'available',
                'record_count': 0,
                'raw_response_saved': False,
            },
        ])
    return {
        'status': 'metadata_collected',
        'fetched_at': fetched_at,
        'provider_statuses': provider_statuses,
        'raw_response_policy': {
            'raw_responses_saved': False,
            'privacy_scan': 'not_applicable_raw_responses_not_saved',
            'reason': 'fixture-only canonical CLI mission',
        },
        'records': [{
            'record_key': _CANONICAL_CLI_SEED,
            'title': 'Neural Optimal Transport',
            'authors': ['Alice Example'],
            'year': 2022,
            'doi': None,
            'arxiv_id': '2201.12220v3',
            'openalex_id': None,
            'landing_page_url': 'https://arxiv.org/abs/2201.12220v3',
            'citation_count': None,
            'providers': ['arxiv'],
            'roles': [],
            'provider_records': [
                {
                    'provider': 'arxiv',
                    'query_kind': 'seed_resolution',
                    'source_id': '2201.12220v3',
                    'primary_category': 'cs.LG',
                    'published': '2022-01-01',
                },
            ],
            'referenced_works': [],
            'query_provenance': [
                {
                    'provider': 'arxiv',
                    'query_kind': 'seed_resolution',
                    'normalized_seed_key': _CANONICAL_CLI_SEED,
                    'topic_query': False,
                },
            ],
        }],
    }


def _canonical_cli_source(request) -> SourceCapabilityResult:
    final_url = f"https://arxiv.org/abs/{request.identifier.split(':', 1)[1]}"
    record = {
        'paper_id': request.paper_id,
        'source_type': 'arxiv_latex',
        'status': 'available',
        'primary_for_audit': True,
        'artifact_root': None,
        'original_source_path': None,
        'flattened_source_path': None,
        'sections': [{
            'level': 1,
            'command': 'section',
            'title': 'Method',
            'line': 1,
            'labels': ['sec-method'],
            'raw_latex': 'Fixture-only Neural Optimal Transport method section.',
        }],
        'equations': [],
        'theorem_like_blocks': [],
        'labels': [],
        'references': [],
        'citations': [],
        'bibliography': [],
        'macros': [],
        'provenance': {
            'arxiv_id': '2201.12220v3',
            'identifier': request.identifier,
            'provider': 'arxiv',
            'final_url': final_url,
            'fixture_only': True,
        },
        'diagnostics': {
            'source_bytes': 0,
            'section_count': 1,
            'equation_count': 0,
            'theorem_like_block_count': 0,
            'fixture_only': True,
        },
        'limitations': [{
            'field': 'source',
            'status': 'fixture_only',
            'note': 'No live source transport was run.',
        }],
    }
    return SourceCapabilityResult(
        candidate_id=request.candidate_id,
        identifier=request.identifier,
        outcome_status='available',
        code='available',
        provider='arxiv',
        final_url=final_url,
        structured_record=record,
        byte_count=len(pretty_json_bytes(record)),
    )


def _canonical_v3_claim_envelope(review_queue_path: Path) -> dict:
    context = load_v2_evidence_context(review_queue_path)
    item = next(
        row for row in context.review_queue['items']
        if row['queue_type'] == 'claim_candidate'
    )
    dependencies = [
        {
            'stable_metadata_paper_id': identity.stable_metadata_paper_id,
            'source_paper_id': identity.source_paper_id,
            'canonical_identifier': identity.canonical_identifier,
            'source_version': identity.source_version,
            'source_record_sha256': identity.source_record_sha256,
            'dependency_role': 'primary_technical_source',
        }
        for identity in sorted(
            context.source_identities.values(),
            key=lambda row: row.source_paper_id,
        )
        if identity.source_paper_id in item['paper_ids']
    ]
    projection = {
        'schema_version': SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        'evidence_kind': 'primary_technical_support',
        'local_artifact': None,
        'local_artifact_sha256': None,
        'direct_source_paper_ids': sorted(row['source_paper_id'] for row in dependencies),
        'referenced_manifest_ids': [],
    }
    manifest_id = f"dm-{sha256_bytes(canonical_json_bytes(projection))}"
    manifests = [{'manifest_id': manifest_id, **projection}]
    graph = {
        'schema_version': 'ra-survey-claim-dependency-graph-v1',
        'root_dependency_manifest_id': manifest_id,
        'dependency_manifests': manifests,
        'source_dependencies': dependencies,
    }
    return {
        'schema_version': SURVEY_CLAIM_REVIEW_V3_SCHEMA,
        'decision_type': 'claim_candidate',
        **context.binding,
        'decisions': [{
            'queue_item_id': item['item_id'],
            'claim_id': 'fixture-reviewed-technical-claim',
            'claim_text': 'The exact fixture source contains the recorded Method section.',
            'claim_type': 'paper_technical',
            'support_class': 'primary_technical_support',
            'review_status': 'human_reviewed_passed',
            'reviewer': 'synthetic-fixture-reviewer',
            'reviewed_at': '2026-07-12T04:03:00Z',
            'evidence_note': 'Synthetic fixture review for engineering state-transition tests only.',
            'fixture_only': True,
            'source_dependencies': dependencies,
            'dependency_manifests': manifests,
            'root_dependency_manifest_id': manifest_id,
            'dependency_graph_sha256': sha256_bytes(canonical_json_bytes(graph)),
            'paper_ids': item['paper_ids'],
            'anchor_ids': item['anchor_ids'],
        }],
    }


def _canonical_v3_source_envelope(
    review_queue_path: Path,
    output_dir: Path,
    *,
    observation_outcome: str = 'checked_clear_for_recorded_checks',
    decision: str = 'checked_clear',
) -> dict:
    context = load_v2_evidence_context(review_queue_path)
    status = context.validated_source_intake['status']
    status_raw = context.validated_source_intake['status_bytes']
    ledger_path = Path(status['outcome_ledger_path'])
    observations = []
    for item_id, identity in sorted(context.source_identities.items()):
        notices = []
        if observation_outcome == 'quarantined':
            notices = [{
                'notice_type': 'quarantine',
                'source': 'synthetic fixture status registry',
                'observed_at': '2026-07-12T04:00:00Z',
                'detail': 'Synthetic quarantine notice for engineering state-transition tests only.',
            }]
        semantic = {
            'schema_version': 'ra-survey-source-status-observation-identity-v1',
            'queue_item_id': item_id,
            'stable_metadata_paper_id': identity.stable_metadata_paper_id,
            'source_paper_id': identity.source_paper_id,
            'canonical_identifier': identity.canonical_identifier,
            'aliases': identity.aliases,
            'source_version': identity.source_version,
            'source_record_path': identity.source_record_path,
            'source_record_sha256': identity.source_record_sha256,
            'source_record_size_bytes': identity.source_record_size_bytes,
            'provider': identity.provider,
            'final_url': identity.final_url,
            'status_source': 'synthetic fixture status registry',
            'evidence_class': 'recorded_status_check',
            'observed_at': '2026-07-12T04:00:00Z',
            'checks_performed': SOURCE_CHECKS,
            'outcome': observation_outcome,
            'notices': notices,
            'fixture_only': True,
            'claim_support_allowed': False,
            'what_is_not_concluded': SOURCE_OBSERVATION_NONCLAIMS,
        }
        digest = sha256_bytes(canonical_json_bytes(semantic))
        observations.append({
            'observation_id': f'so-{digest}',
            'observation_sha256': digest,
            **{key: value for key, value in semantic.items() if key != 'schema_version'},
        })
    current_path = output_dir / 'OBSERVATION_CURRENT'
    current = json.loads(current_path.read_text()) if current_path.exists() else None
    observation_set = {
        'schema_version': SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
        **context.binding,
        'source_intake_status_path': str(
            context.mission_root / 'source_intake' / 'phase4_source_intake_status.json'
        ),
        'source_intake_status_sha256': sha256_bytes(status_raw),
        'source_intake_status_size_bytes': len(status_raw),
        'source_outcome_ledger_path': str(ledger_path),
        'source_outcome_ledger_sha256': sha256_bytes(ledger_path.read_bytes()),
        'source_outcome_ledger_size_bytes': ledger_path.stat().st_size,
        'fixture_only': True,
        'observations': observations,
        'what_is_not_concluded': SOURCE_OBSERVATION_NONCLAIMS,
        'predecessor_observation_set_id': (
            current['observation_set_id'] if current is not None else None
        ),
        'predecessor_observation_set_manifest_sha256': (
            current['observation_set_manifest_sha256'] if current is not None else None
        ),
    }
    binding = preview_source_observation_binding(
        review_queue_path=review_queue_path,
        observation_set=observation_set,
        output_dir=output_dir,
    )
    by_item = {row['queue_item_id']: row for row in observations}
    decisions = []
    for item_id, identity in sorted(context.source_identities.items()):
        observation = by_item[item_id]
        row = {
            'queue_item_id': item_id,
            'stable_metadata_paper_id': identity.stable_metadata_paper_id,
            'source_paper_id': identity.source_paper_id,
            'observation_set_id': binding['observation_set_id'],
            'observation_set_manifest_sha256': binding['observation_set_manifest_sha256'],
            'observation_id': observation['observation_id'],
            'observation_sha256': observation['observation_sha256'],
            'source_version': identity.source_version,
            'reviewer_authority': 'human_reviewed_status',
            'decision': decision,
            'reviewer': 'synthetic-fixture-reviewer',
            'reviewed_at': '2026-07-12T04:01:00Z',
            'reason': 'Synthetic fixture decision for engineering state-transition tests only.',
            'fixture_only': True,
        }
        if decision == 'blocked':
            row['next_action'] = 'Resolve the source-safety outcome before packet composition.'
        decisions.append(row)
    return {
        'schema_version': SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
        'decision_type': 'source_safety',
        **context.binding,
        'observation_set': observation_set,
        'decisions': decisions,
    }


def _write_reviewed_sidecar_fixture(
    tmp_path: Path,
    capsys,
    *,
    close_omissions: bool = False,
) -> dict[str, Path]:
    mission_dir = tmp_path / 'mission_with_queue'
    first = orchestrate.run_public_source_workflow(
        topic=_CANONICAL_CLI_TOPIC,
        seeds=[_CANONICAL_CLI_SEED],
        output_dir=mission_dir,
        run_safe_local=True,
    )
    assert first['local_supervisor']['status'] == 'terminal_blocked_public_discovery_confirmation'

    patcher = pytest.MonkeyPatch()
    patcher.setattr(survey_build, '_collect_public_metadata', _canonical_cli_metadata_collection)
    try:
        built = survey_build.build_survey_evidence_packet(
            topic=_CANONICAL_CLI_TOPIC,
            seeds=[_CANONICAL_CLI_SEED],
            output_dir=mission_dir / 'public_metadata',
            mode='public-metadata',
            public_metadata_providers=['arxiv'],
            max_records=25,
        )
    finally:
        patcher.undo()
    assert built['status'] == 'metadata_only_packet'

    selected = orchestrate.run_public_source_workflow(
        topic=_CANONICAL_CLI_TOPIC,
        seeds=[_CANONICAL_CLI_SEED],
        output_dir=mission_dir,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(_canonical_cli_source),
    )
    assert selected['local_supervisor']['status'] == 'terminal_blocked_human_review'
    review_queue_path = Path(selected['review_queue_path'])
    queue = json.loads(review_queue_path.read_text())
    metadata_dir = mission_dir / 'public_metadata'
    source_status_dir = mission_dir / 'source_intake'
    anchor_dir = mission_dir / 'source_anchors'
    packet_dir = mission_dir / 'public_source_packet'
    omission_items = [item for item in queue['items'] if item['queue_type'] == 'omission_risk']
    workflow_items = [item for item in queue['items'] if item['queue_type'] == 'workflow_blocker']

    claim_decisions = tmp_path / 'merge_claim_decisions.json'
    claim_decisions.write_bytes(pretty_json_bytes(_canonical_v3_claim_envelope(review_queue_path)))
    reviewed_claims_dir = mission_dir / 'reviewed_claims'
    assert main([
        'survey',
        'import-claim-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(claim_decisions),
        '--out',
        str(reviewed_claims_dir),
    ]) == 0
    claim_import = json.loads(capsys.readouterr().out)

    safety_decisions = tmp_path / 'merge_source_safety_decisions.json'
    reviewed_safety_dir = mission_dir / 'reviewed_source_safety'
    safety_decisions.write_bytes(pretty_json_bytes(_canonical_v3_source_envelope(
        review_queue_path,
        reviewed_safety_dir,
    )))
    assert main([
        'survey',
        'import-source-safety-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(safety_decisions),
        '--out',
        str(reviewed_safety_dir),
    ]) == 0
    source_import = json.loads(capsys.readouterr().out)

    omission_decisions = tmp_path / 'merge_omission_decisions.json'
    omission_decisions.write_bytes(pretty_json_bytes(_bound_review_decisions(
        review_queue_path,
        queue,
        'omission_risk',
        [
            {
                'queue_item_id': item['item_id'],
                'risk_id': item['risk_id'],
                'decision': 'acceptable_omission' if close_omissions else 'must_inspect',
                'reason': 'Fixture decision is explicit for the current bounded scope.',
                **(
                    {'scope_basis': 'Closed only for this synthetic local fixture scope.'}
                    if close_omissions
                    else {'next_action': 'Inspect source references before final prose.'}
                ),
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            }
            for item in omission_items
        ]
    )))
    reviewed_omissions_dir = mission_dir / 'reviewed_omissions'
    assert main([
        'survey',
        'import-omission-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(omission_decisions),
        '--out',
        str(reviewed_omissions_dir),
    ]) == 0
    omission_import = json.loads(capsys.readouterr().out)

    workflow_decisions = tmp_path / 'merge_workflow_blocker_decisions.json'
    workflow_decisions.write_bytes(pretty_json_bytes(_bound_review_decisions(
        review_queue_path,
        queue,
        'workflow_blocker',
        [
            {
                'queue_item_id': item['item_id'],
                'disposition': 'resolved_by_reviewed_evidence',
                'evidence_queue_item_ids': item['required_evidence_queue_item_ids'],
                'rationale': 'The exact current fixture review decisions address this aggregate blocker structurally.',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            }
            if item['resolution_class'] != 'upstream_repair_required'
            else {
                'queue_item_id': item['item_id'],
                'disposition': 'remains_open',
                'rationale': 'This blocker requires an upstream artifact repair.',
                'next_action': 'Repair the named upstream artifact and rebuild the selected queue.',
                'reviewer': 'local-test-reviewer',
                'reviewed_at': '2026-07-10T00:00:00Z',
            }
            for item in workflow_items
        ],
    )))
    reviewed_workflow_dir = mission_dir / 'reviewed_workflow_blockers'
    assert main([
        'survey',
        'import-workflow-blocker-review',
        '--review-queue',
        str(review_queue_path),
        '--decisions',
        str(workflow_decisions),
        '--out',
        str(reviewed_workflow_dir),
    ]) == 0
    capsys.readouterr()
    return {
        'metadata_dir': metadata_dir,
        'source_status_dir': source_status_dir,
        'anchor_dir': anchor_dir,
        'packet_dir': packet_dir,
        'mission_dir': mission_dir,
        'review_queue': review_queue_path,
        'coverage_dir': review_queue_path.parent / 'coverage',
        'reviewed_claims': Path(claim_import['reviewed_claims_path']),
        'reviewed_claims_root': reviewed_claims_dir,
        'reviewed_source_safety': Path(source_import['reviewed_source_safety_path']),
        'reviewed_source_safety_root': reviewed_safety_dir,
        'reviewed_omissions': Path(omission_import['reviewed_omission_risks_path']),
        'reviewed_omissions_root': reviewed_omissions_dir,
        'reviewed_workflow_blockers': reviewed_workflow_dir / 'reviewed_workflow_blockers.json',
        'claim_decisions': claim_decisions,
        'source_safety_decisions': safety_decisions,
        'omission_decisions': omission_decisions,
        'workflow_decisions': workflow_decisions,
    }


def _run_safe_local_command(sidecars: dict[str, Path]) -> list[str]:
    return [
        'survey', 'run-public-source-workflow',
        '--topic', 'Neural Optimal Transport for generative modeling and inference',
        '--seed', 'arxiv:2201.12220v3',
        '--out', str(sidecars['mission_dir']),
        '--metadata-dir', str(sidecars['metadata_dir']),
        '--source-status-dir', str(sidecars['source_status_dir']),
        '--anchor-dir', str(sidecars['anchor_dir']),
        '--packet-dir', str(sidecars['packet_dir']),
        '--resume',
        '--run-safe-local',
    ]


def _write_late_stage_fixture(tmp_path: Path, capsys, *, through: str) -> dict[str, Path]:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    mission = sidecars['mission_dir']
    merge_dir = mission / 'reviewed_evidence'
    reviewed_packet_dir = mission / 'reviewed_final_packet'
    hostile_dir = mission / 'hostile_review'
    if through in {'merge', 'packet', 'hostile'}:
        assert main([
            'survey', 'merge-reviewed-evidence',
            '--review-queue', str(sidecars['review_queue']),
            '--reviewed-claims', str(sidecars['reviewed_claims']),
            '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
            '--reviewed-omissions', str(sidecars['reviewed_omissions']),
            '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
            '--out', str(merge_dir),
        ]) == 0
        capsys.readouterr()
    if through in {'packet', 'hostile'}:
        assert main([
            'survey', 'compose-reviewed-final-packet',
            '--mission-root', str(mission),
            '--review-queue', str(sidecars['review_queue']),
            '--packet-dir', str(sidecars['packet_dir']),
            '--anchor-dir', str(sidecars['anchor_dir']),
            '--out', str(reviewed_packet_dir),
        ]) == 0
        capsys.readouterr()
    if through == 'hostile':
        assert main([
            'survey', 'hostile-review',
            '--reviewed-final-packet', str(reviewed_packet_dir / 'reviewed_final_packet.json'),
            '--mission-root', str(mission),
            '--review-queue', str(sidecars['review_queue']),
            '--packet-dir', str(sidecars['packet_dir']),
            '--anchor-dir', str(sidecars['anchor_dir']),
            '--out', str(hostile_dir),
        ]) == 0
        capsys.readouterr()
    return sidecars


def test_safe_local_supervisor_executes_merge_packet_hostile_and_terminal(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    mission = sidecars['mission_dir']
    external_roots = [
        sidecars['metadata_dir'], sidecars['source_status_dir'],
        sidecars['anchor_dir'], sidecars['packet_dir'],
    ]
    external_before = {root: _snapshot_tree(root) for root in external_roots}

    rc = main(_run_safe_local_command(sidecars))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    supervisor = payload['local_supervisor']
    assert supervisor['status'] == 'terminal_ready_for_reviewed_prose_within_recorded_scope'
    assert supervisor['terminal_action_id'] == 'terminal_ready_for_reviewed_prose'
    assert supervisor['ready_for_prose'] is True
    assert supervisor['readiness_classification'] == 'READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE'
    assert [row['stage_id'] for row in supervisor['transition_history']] == [
        'merge_reviewed_evidence',
        'compose_reviewed_final_packet',
        'run_hostile_review',
    ]
    assert all(row['post_dispatch_outcome'] == 'progress' for row in supervisor['transition_history'])
    assert (mission / 'reviewed_evidence' / 'reviewed_evidence_status.json').is_file()
    assert (mission / 'reviewed_final_packet' / 'reviewed_final_packet.json').is_file()
    assert (mission / 'hostile_review' / 'hostile_review_result.json').is_file()
    assert (mission / 'hostile_review' / 'final_packet_readiness.json').is_file()
    persisted = json.loads((mission / 'mission_control.json').read_text())
    assert persisted['local_supervisor'] == supervisor
    assert persisted['next_action']['action_id'] == 'terminal_ready_for_reviewed_prose'
    assert persisted['next_action']['ready_for_prose'] is True
    assert {root: _snapshot_tree(root) for root in external_roots} == external_before

    authoritative = {
        path: path.read_bytes()
        for path in [
            mission / 'reviewed_evidence' / 'reviewed_evidence_status.json',
            mission / 'reviewed_final_packet' / 'reviewed_final_packet.json',
            mission / 'hostile_review' / 'hostile_review_result.json',
            mission / 'hostile_review' / 'final_packet_readiness.json',
        ]
    }
    rc = main(_run_safe_local_command(sidecars))
    resumed = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert resumed['local_supervisor']['status'] == supervisor['status']
    assert resumed['local_supervisor']['transition_history'] == []
    assert {path: path.read_bytes() for path in authoritative} == authoritative
    assert {root: _snapshot_tree(root) for root in external_roots} == external_before


def test_safe_local_rejects_noncanonical_supplied_reviewed_root_before_merge(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    external = tmp_path / 'external_reviewed_claims'
    external.mkdir()
    shutil.copy2(sidecars['reviewed_claims'], external / 'reviewed_claims.json')

    def forbidden(*args, **kwargs):
        raise AssertionError('noncanonical supplied reviewed root reached merge dispatch')

    monkeypatch.setattr(orchestrate, 'merge_reviewed_evidence', forbidden)
    command = _run_safe_local_command(sidecars) + ['--reviewed-claims-dir', str(external)]
    assert main(command) == 0
    payload = json.loads(capsys.readouterr().out)
    supervisor = payload['local_supervisor']
    assert supervisor['status'] == 'terminal_blocked_invalid_artifact'
    assert supervisor['terminal_reason'] == 'noncanonical_safe_local_reviewed_claims_root'
    assert supervisor['transition_history'] == []
    assert not (sidecars['mission_dir'] / 'reviewed_evidence').exists()


@pytest.mark.parametrize('view_state', ['missing', 'tampered'])
def test_safe_local_supervisor_refreshes_only_optional_readiness_view(
    tmp_path: Path,
    capsys,
    view_state: str,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    assert main(_run_safe_local_command(sidecars)) == 0
    capsys.readouterr()
    hostile = sidecars['mission_dir'] / 'hostile_review' / 'hostile_review_result.json'
    readiness = sidecars['mission_dir'] / 'hostile_review' / 'final_packet_readiness.json'
    hostile_before = hostile.read_bytes()
    if view_state == 'missing':
        readiness.unlink()
    else:
        payload = json.loads(readiness.read_text())
        payload['ready_for_prose'] = False
        readiness.write_text(json.dumps(payload, indent=2, sort_keys=True))

    assert main(_run_safe_local_command(sidecars)) == 0
    refreshed = json.loads(capsys.readouterr().out)
    supervisor = refreshed['local_supervisor']
    assert supervisor['status'] == 'terminal_ready_for_reviewed_prose_within_recorded_scope'
    assert [row['stage_id'] for row in supervisor['transition_history']] == ['refresh_final_packet_readiness']
    assert supervisor['transition_history'][0]['stage_result']['status'] == 'refreshed'
    assert hostile.read_bytes() == hostile_before
    assert json.loads(readiness.read_text())['hostile_review_result_sha256'] == hashlib.sha256(hostile_before).hexdigest()


def test_safe_local_readiness_refresh_failure_preserves_authoritative_terminal(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    assert main(_run_safe_local_command(sidecars)) == 0
    capsys.readouterr()
    hostile = sidecars['mission_dir'] / 'hostile_review' / 'hostile_review_result.json'
    readiness = sidecars['mission_dir'] / 'hostile_review' / 'final_packet_readiness.json'
    hostile_before = hostile.read_bytes()
    readiness.unlink()

    def fail_refresh(**kwargs):
        raise OSError('injected optional-view failure')

    monkeypatch.setattr('research_assistant.survey.orchestrate.refresh_final_packet_readiness', fail_refresh)
    assert main(_run_safe_local_command(sidecars)) == 0
    result = json.loads(capsys.readouterr().out)
    supervisor = result['local_supervisor']
    assert supervisor['status'] == 'terminal_ready_for_reviewed_prose_within_recorded_scope'
    assert supervisor['terminal_reason'] == 'optional_readiness_view_regeneration_failed_authority_unchanged'
    assert supervisor['transition_history'][0]['stage_result']['status'] == 'optional_readiness_refresh_failed'
    assert supervisor['transition_history'][0]['stage_result']['error_code'] == 'readiness_refresh_exception'
    assert hostile.read_bytes() == hostile_before
    assert not readiness.exists()


def test_safe_local_supervisor_reports_replay_valid_blocked_hostile_terminal(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    blocker = {
        'code': 'fixture_material_blocker',
        'message': 'The bounded hostile fixture veto remains open.',
        'repair_action': 'repair the bounded hostile fixture input',
    }
    monkeypatch.setattr('research_assistant.survey.hostile_review._hostile_blockers', lambda packet: [blocker])

    assert main(_run_safe_local_command(sidecars)) == 0
    result = json.loads(capsys.readouterr().out)
    supervisor = result['local_supervisor']
    assert supervisor['status'] == 'terminal_blocked_hostile_review'
    assert supervisor['terminal_action_id'] == 'terminal_blocked_hostile_review'
    assert supervisor['ready_for_prose'] is False
    assert supervisor['readiness_classification'] == 'BLOCKED_FOR_REVIEWED_PROSE'
    assert [row['stage_id'] for row in supervisor['transition_history']][-1] == 'run_hostile_review'
    hostile = json.loads((sidecars['mission_dir'] / 'hostile_review' / 'hostile_review_result.json').read_text())
    assert hostile['blockers'] == [blocker]
    assert hostile['ready_for_prose'] is False
    hostile_path = sidecars['mission_dir'] / 'hostile_review' / 'hostile_review_result.json'
    readiness_path = sidecars['mission_dir'] / 'hostile_review' / 'final_packet_readiness.json'
    authoritative_before = hostile_path.read_bytes()
    view_before = readiness_path.read_bytes()

    assert main(_run_safe_local_command(sidecars)) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed['local_supervisor']['status'] == 'terminal_blocked_hostile_review'
    assert resumed['local_supervisor']['transition_history'] == []
    assert hostile_path.read_bytes() == authoritative_before
    assert readiness_path.read_bytes() == view_before

    readiness_path.unlink()

    def fail_refresh(**kwargs):
        raise OSError('injected blocked optional-view failure')

    monkeypatch.setattr('research_assistant.survey.orchestrate.refresh_final_packet_readiness', fail_refresh)
    assert main(_run_safe_local_command(sidecars)) == 0
    failed_refresh = json.loads(capsys.readouterr().out)
    assert failed_refresh['local_supervisor']['status'] == 'terminal_blocked_hostile_review'
    assert failed_refresh['local_supervisor']['ready_for_prose'] is False
    assert failed_refresh['local_supervisor']['terminal_reason'] == (
        'optional_readiness_view_regeneration_failed_authority_unchanged'
    )
    assert failed_refresh['local_supervisor']['transition_history'][0]['stage_result']['status'] == (
        'optional_readiness_refresh_failed'
    )
    assert hostile_path.read_bytes() == authoritative_before


@pytest.mark.parametrize(
    'shape',
    [
        'replay_stale', 'malformed', 'noncanonical', 'wrong_schema', 'wrong_keys',
        'symlink', 'nonregular', 'empty_root', 'stray',
    ],
)
def test_safe_local_reviewed_merge_repair_state_matrix(
    tmp_path: Path,
    capsys,
    monkeypatch,
    shape: str,
) -> None:
    sidecars = _write_late_stage_fixture(tmp_path, capsys, through='merge')
    path = sidecars['mission_dir'] / 'reviewed_evidence' / 'reviewed_evidence_status.json'
    original = json.loads(path.read_text())
    if shape == 'replay_stale':
        original['review_queue_sha256'] = '0' * 64
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'malformed':
        path.write_text('{')
    elif shape == 'noncanonical':
        path.write_text(json.dumps(original))
    elif shape == 'wrong_schema':
        original['schema_version'] = 'wrong'
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'wrong_keys':
        original['extra'] = True
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'symlink':
        path.unlink()
        outside = tmp_path / 'outside-merge.json'
        outside.write_bytes(pretty_json_bytes(original))
        path.symlink_to(outside)
    elif shape == 'nonregular':
        path.unlink()
        path.mkdir()
    elif shape == 'empty_root':
        path.unlink()
    else:
        (path.parent / 'stray.txt').write_text('partial residue')

    calls: list[bool] = []
    real_merge = orchestrate.merge_reviewed_evidence

    def wrapped_merge(**kwargs):
        calls.append(kwargs['force'])
        return real_merge(**kwargs)

    monkeypatch.setattr('research_assistant.survey.orchestrate.merge_reviewed_evidence', wrapped_merge)
    assert main(_run_safe_local_command(sidecars)) == 0
    result = json.loads(capsys.readouterr().out)
    if shape in {'replay_stale', 'empty_root'}:
        assert calls == ([True] if shape == 'replay_stale' else [False])
        expected_stage = 'repair_reviewed_evidence' if shape == 'replay_stale' else 'merge_reviewed_evidence'
        assert expected_stage in [row['stage_id'] for row in result['local_supervisor']['transition_history']]
        assert result['local_supervisor']['status'] == 'terminal_ready_for_reviewed_prose_within_recorded_scope'
    else:
        assert calls == []
        assert result['local_supervisor']['status'] == 'terminal_blocked_invalid_artifact'


@pytest.mark.parametrize(
    'shape',
    [
        'replay_stale', 'malformed', 'noncanonical', 'wrong_schema', 'wrong_keys',
        'symlink', 'nonregular', 'empty_root', 'stray',
    ],
)
def test_safe_local_reviewed_packet_repair_state_matrix(
    tmp_path: Path,
    capsys,
    monkeypatch,
    shape: str,
) -> None:
    sidecars = _write_late_stage_fixture(tmp_path, capsys, through='packet')
    path = sidecars['mission_dir'] / 'reviewed_final_packet' / 'reviewed_final_packet.json'
    original = json.loads(path.read_text())
    if shape == 'replay_stale':
        original['review_queue_sha256'] = '0' * 64
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'malformed':
        path.write_text('{')
    elif shape == 'noncanonical':
        path.write_text(json.dumps(original))
    elif shape == 'wrong_schema':
        original['schema_version'] = 'wrong'
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'wrong_keys':
        original['extra'] = True
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'symlink':
        path.unlink()
        outside = tmp_path / 'outside-packet.json'
        outside.write_bytes(pretty_json_bytes(original))
        path.symlink_to(outside)
    elif shape == 'nonregular':
        path.unlink()
        path.mkdir()
    elif shape == 'empty_root':
        path.unlink()
    else:
        (path.parent / 'stray.txt').write_text('partial residue')

    calls: list[bool] = []
    real_compose = orchestrate.compose_reviewed_final_packet

    def wrapped_compose(**kwargs):
        calls.append(kwargs['force'])
        return real_compose(**kwargs)

    monkeypatch.setattr('research_assistant.survey.orchestrate.compose_reviewed_final_packet', wrapped_compose)
    assert main(_run_safe_local_command(sidecars)) == 0
    result = json.loads(capsys.readouterr().out)
    if shape == 'replay_stale':
        assert calls == [True]
        assert 'repair_reviewed_final_packet' in [
            row['stage_id'] for row in result['local_supervisor']['transition_history']
        ]
        assert result['local_supervisor']['status'] == 'terminal_ready_for_reviewed_prose_within_recorded_scope'
    else:
        assert calls == []
        assert result['local_supervisor']['status'] == 'terminal_blocked_invalid_artifact'


@pytest.mark.parametrize(
    'shape',
    [
        'replay_stale', 'malformed', 'noncanonical', 'wrong_schema', 'wrong_keys',
        'symlink', 'nonregular', 'empty_root', 'stray',
    ],
)
def test_safe_local_hostile_result_repair_state_matrix(
    tmp_path: Path,
    capsys,
    monkeypatch,
    shape: str,
) -> None:
    sidecars = _write_late_stage_fixture(tmp_path, capsys, through='hostile')
    hostile_dir = sidecars['mission_dir'] / 'hostile_review'
    path = hostile_dir / 'hostile_review_result.json'
    readiness = hostile_dir / 'final_packet_readiness.json'
    readiness.unlink()
    original = json.loads(path.read_text())
    if shape == 'replay_stale':
        original['reviewed_final_packet_sha256'] = '0' * 64
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'malformed':
        path.write_text('{')
    elif shape == 'noncanonical':
        path.write_text(json.dumps(original))
    elif shape == 'wrong_schema':
        original['schema_version'] = 'wrong'
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'wrong_keys':
        original['extra'] = True
        path.write_bytes(pretty_json_bytes(original))
    elif shape == 'symlink':
        path.unlink()
        outside = tmp_path / 'outside-hostile.json'
        outside.write_bytes(pretty_json_bytes(original))
        path.symlink_to(outside)
    elif shape == 'nonregular':
        path.unlink()
        path.mkdir()
    elif shape == 'empty_root':
        path.unlink()
    else:
        (path.parent / 'stray.txt').write_text('partial residue')

    calls: list[bool] = []
    real_hostile = orchestrate.run_hostile_review_gate

    def wrapped_hostile(**kwargs):
        calls.append(kwargs['force'])
        return real_hostile(**kwargs)

    monkeypatch.setattr('research_assistant.survey.orchestrate.run_hostile_review_gate', wrapped_hostile)
    assert main(_run_safe_local_command(sidecars)) == 0
    result = json.loads(capsys.readouterr().out)
    if shape == 'replay_stale':
        assert calls == [True]
        assert 'repair_hostile_review_result' in [
            row['stage_id'] for row in result['local_supervisor']['transition_history']
        ]
        assert result['local_supervisor']['status'] == 'terminal_ready_for_reviewed_prose_within_recorded_scope'
    else:
        assert calls == []
        assert result['local_supervisor']['status'] == 'terminal_blocked_invalid_artifact'


@pytest.mark.parametrize(
    ('missing_key', 'terminal_status', 'terminal_action', 'terminal_reason'),
    [
        (
            'reviewed_claims',
            'terminal_blocked_invalid_artifact',
            'invalid_reviewed_authority',
            'unexpected_claim_decision_set_path',
        ),
        (
            'reviewed_source_safety',
            'terminal_blocked_invalid_artifact',
            'invalid_reviewed_authority',
            'unexpected_source_decision_set_path',
        ),
        (
            'reviewed_omissions',
            'terminal_blocked_invalid_artifact',
            'invalid_reviewed_authority',
            'missing_omission_decision_artifact',
        ),
        (
            'reviewed_workflow_blockers',
            'terminal_blocked_human_review',
            'import_reviewed_workflow_blockers',
            'explicit_review_input_is_required',
        ),
    ],
)
def test_safe_local_missing_each_review_sidecar_stops_without_dispatch(
    tmp_path: Path,
    capsys,
    monkeypatch,
    missing_key: str,
    terminal_status: str,
    terminal_action: str,
    terminal_reason: str,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=True)
    removed = sidecars[missing_key]
    removed_bytes = removed.read_bytes()
    removed.unlink()
    preserved = {
        path: path.read_bytes()
        for key, path in sidecars.items()
        if key.startswith('reviewed_') and key != missing_key and path.is_file()
    }

    def forbidden(*args, **kwargs):
        raise AssertionError('human-review terminal reached a local product writer')

    monkeypatch.setattr('research_assistant.survey.orchestrate.merge_reviewed_evidence', forbidden)
    monkeypatch.setattr('research_assistant.survey.orchestrate.compose_reviewed_final_packet', forbidden)
    monkeypatch.setattr('research_assistant.survey.orchestrate.run_hostile_review_gate', forbidden)
    assert main(_run_safe_local_command(sidecars)) == 0
    first = json.loads(capsys.readouterr().out)
    assert first['local_supervisor']['status'] == terminal_status
    assert first['local_supervisor']['terminal_action_id'] == terminal_action
    assert first['local_supervisor']['terminal_reason'] == terminal_reason
    for family in ('reviewed_claims', 'reviewed_source_safety', 'reviewed_omissions'):
        if family != missing_key:
            assert first['reviewed_artifacts'][family]['exists'] is True
            assert first['reviewed_artifacts'][family]['lineage_status'] == 'current_lineage'
    assert {path: path.read_bytes() for path in preserved} == preserved

    assert main(_run_safe_local_command(sidecars)) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed['local_supervisor']['status'] == terminal_status
    assert resumed['local_supervisor']['terminal_action_id'] == terminal_action
    assert resumed['local_supervisor']['terminal_reason'] == terminal_reason
    assert resumed['local_supervisor']['transition_history'] == []
    assert {path: path.read_bytes() for path in preserved} == preserved
    assert not removed.exists()
    assert removed_bytes


def test_safe_local_open_reviewed_blockers_stop_before_packet_and_are_idempotent(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys, close_omissions=False)

    def forbidden(*args, **kwargs):
        raise AssertionError('open reviewed blockers reached packet or hostile writer')

    monkeypatch.setattr('research_assistant.survey.orchestrate.compose_reviewed_final_packet', forbidden)
    monkeypatch.setattr('research_assistant.survey.orchestrate.run_hostile_review_gate', forbidden)
    assert main(_run_safe_local_command(sidecars)) == 0
    first = json.loads(capsys.readouterr().out)
    supervisor = first['local_supervisor']
    assert supervisor['status'] == 'terminal_blocked_reviewed_evidence'
    assert supervisor['terminal_action_id'] == 'resolve_reviewed_evidence_blockers'
    assert 'merge_reviewed_evidence' in [row['stage_id'] for row in supervisor['transition_history']]
    merge_path = sidecars['mission_dir'] / 'reviewed_evidence' / 'reviewed_evidence_status.json'
    merge_before = merge_path.read_bytes()
    assert not (sidecars['mission_dir'] / 'reviewed_final_packet').exists()
    assert not (sidecars['mission_dir'] / 'hostile_review').exists()

    assert main(_run_safe_local_command(sidecars)) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed['local_supervisor']['status'] == 'terminal_blocked_reviewed_evidence'
    assert resumed['local_supervisor']['transition_history'] == []
    assert merge_path.read_bytes() == merge_before


def test_upstream_packet_change_selects_new_set_and_retains_stale_decisions(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    old_queue = sidecars['review_queue']
    old_set = old_queue.parent
    decision_bytes = {
        name: sidecars[name].read_bytes()
        for name in [
            'reviewed_claims',
            'reviewed_source_safety',
            'reviewed_omissions',
            'reviewed_workflow_blockers',
        ]
    }
    claim_path = sidecars['packet_dir'] / 'claim_support.json'
    claim_payload = json.loads(claim_path.read_text())
    claim_payload['claim_candidates'][0]['next_action'] = 'Review the changed claim semantics.'
    claim_path.write_text(json.dumps(claim_payload, indent=2, sort_keys=True))

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(sidecars['mission_dir']),
        '--metadata-dir',
        str(sidecars['metadata_dir']),
        '--source-status-dir',
        str(sidecars['source_status_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    new_queue = Path(payload['review_queue_path'])
    assert new_queue != old_queue
    assert old_set.exists()
    assert payload['next_action']['action_id'] == 'import_reviewed_claims'
    mission = json.loads((sidecars['mission_dir'] / 'mission_control.json').read_text())
    for name, before in decision_bytes.items():
        assert sidecars[name].read_bytes() == before
        assert mission['reviewed_artifacts'][name]['lineage_status'] == 'stale_lineage'
        assert mission['reviewed_artifacts'][name]['exists'] is False


def test_stale_coverage_argument_blocks_before_current_selection_mutation(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    current_path = sidecars['mission_dir'] / '.artifact_state' / 'CURRENT'
    current_before = current_path.read_bytes()
    claim_path = sidecars['packet_dir'] / 'claim_support.json'
    claim_payload = json.loads(claim_path.read_text())
    claim_payload['claim_candidates'][0]['next_action'] = 'Changed semantics that would select a new set.'
    claim_path.write_text(json.dumps(claim_payload, indent=2, sort_keys=True))
    legacy_coverage = sidecars['mission_dir'] / 'coverage_ledgers'

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(sidecars['mission_dir']),
        '--metadata-dir',
        str(sidecars['metadata_dir']),
        '--source-status-dir',
        str(sidecars['source_status_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--coverage-dir',
        str(legacy_coverage),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['blocked_reason'] == 'stale_lineage'
    assert current_path.read_bytes() == current_before


def test_coverage_symlink_alias_blocks_before_current_selection_mutation(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    current_path = sidecars['mission_dir'] / '.artifact_state' / 'CURRENT'
    current_before = current_path.read_bytes()
    alias = sidecars['mission_dir'] / 'coverage-alias'
    alias.symlink_to(sidecars['coverage_dir'], target_is_directory=True)

    rc = main([
        'survey',
        'run-public-source-workflow',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(sidecars['mission_dir']),
        '--metadata-dir',
        str(sidecars['metadata_dir']),
        '--source-status-dir',
        str(sidecars['source_status_dir']),
        '--anchor-dir',
        str(sidecars['anchor_dir']),
        '--packet-dir',
        str(sidecars['packet_dir']),
        '--coverage-dir',
        str(alias),
        '--resume',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload['blocked_reason'] == 'stale_lineage'
    assert current_path.read_bytes() == current_before


def test_direct_review_consumers_reject_selected_path_symlink_aliases_without_output(
    tmp_path: Path,
    capsys,
) -> None:
    sidecars = _write_reviewed_sidecar_fixture(tmp_path, capsys)
    queue_alias = sidecars['mission_dir'] / 'review-queue-alias.json'
    queue_alias.symlink_to(sidecars['review_queue'])
    decisions = tmp_path / 'unused-decisions.json'
    decisions.write_text('{}')

    cases = [
        (
            'claim-import',
            [
                'survey', 'import-claim-review', '--review-queue', str(queue_alias),
                '--decisions', str(decisions),
            ],
        ),
        (
            'source-safety-import',
            [
                'survey', 'import-source-safety-review', '--review-queue', str(queue_alias),
                '--decisions', str(decisions),
            ],
        ),
        (
            'omission-import',
            [
                'survey', 'import-omission-review', '--review-queue', str(queue_alias),
                '--decisions', str(decisions),
            ],
        ),
        (
            'workflow-blocker-import',
            [
                'survey', 'import-workflow-blocker-review', '--review-queue', str(queue_alias),
                '--decisions', str(decisions),
            ],
        ),
        (
            'reviewed-merge',
            [
                'survey', 'merge-reviewed-evidence', '--review-queue', str(queue_alias),
                '--reviewed-claims', str(sidecars['reviewed_claims']),
                '--reviewed-source-safety', str(sidecars['reviewed_source_safety']),
                '--reviewed-omissions', str(sidecars['reviewed_omissions']),
                '--reviewed-workflow-blockers', str(sidecars['reviewed_workflow_blockers']),
            ],
        ),
    ]

    for name, arguments in cases:
        output = tmp_path / f'alias-rejection-{name}'
        rc = main([*arguments, '--out', str(output)])
        payload = json.loads(capsys.readouterr().out)

        assert rc == 1
        assert payload['blocked_reason'] == 'stale_lineage'
        assert not output.exists()


def test_cli_survey_build_public_metadata_emits_typed_citation_layers(tmp_path: Path, capsys, monkeypatch) -> None:
    output = tmp_path / 'typed_public_metadata_packet'

    arxiv_seed_record = {
        'record_key': 'arxiv:2201.12220v3',
        'title': 'Neural Optimal Transport',
        'authors': ['Alice Example'],
        'year': 2022,
        'doi': None,
        'arxiv_id': '2201.12220v3',
        'openalex_id': None,
        'landing_page_url': 'https://arxiv.org/abs/2201.12220v3',
        'citation_count': None,
        'providers': ['arxiv'],
        'roles': [],
        'provider_records': [{
            'provider': 'arxiv', 'query_kind': 'seed_resolution',
            'source_id': '2201.12220v3', 'primary_category': 'cs.LG',
            'published': '2022-01-01',
        }],
        'referenced_works': ['https://openalex.org/W001'],
    }
    openalex_seed_record = {
        'record_key': 'openalex:w123',
        'title': 'Neural Optimal Transport',
        'authors': ['Alice Example'],
        'year': 2022,
        'doi': None,
        'arxiv_id': '2201.12220v3',
        'openalex_id': 'https://openalex.org/W123',
        'landing_page_url': 'https://openalex.org/W123',
        'citation_count': 42,
        'providers': ['openalex'],
        'roles': [],
        'provider_records': [{
            'provider': 'openalex', 'query_kind': 'seed_resolution',
            'source_id': 'https://openalex.org/W123', 'citation_count': 42,
            'publication_date': '2022-01-01', 'work_type': 'article',
        }],
        'referenced_works': ['https://openalex.org/W001'],
    }
    backward_record = {
        'record_key': 'openalex:w001',
        'title': 'Neural Transport Reference Method',
        'authors': ['Bob Example'],
        'year': 2020,
        'doi': None,
        'arxiv_id': None,
        'openalex_id': 'https://openalex.org/W001',
        'landing_page_url': 'https://openalex.org/W001',
        'citation_count': 7,
        'providers': ['openalex'],
        'roles': ['backward_lineage_candidate'],
        'provider_records': [{
            'provider': 'openalex', 'query_kind': 'topic_search',
            'source_id': 'https://openalex.org/W001', 'citation_count': 7,
            'publication_date': '2020-01-01', 'work_type': 'article',
        }],
        'referenced_works': [],
    }
    adjacent_record = {
        'record_key': 'openalex:w789',
        'title': 'Neural Transport Adjacent Method',
        'authors': ['Carol Example'],
        'year': 2023,
        'doi': None,
        'arxiv_id': None,
        'openalex_id': 'https://openalex.org/W789',
        'landing_page_url': 'https://openalex.org/W789',
        'citation_count': 5,
        'providers': ['openalex'],
        'roles': [],
        'provider_records': [{
            'provider': 'openalex', 'query_kind': 'topic_search',
            'source_id': 'https://openalex.org/W789', 'citation_count': 5,
            'publication_date': '2023-01-01', 'work_type': 'article',
        }],
        'referenced_works': [],
    }

    def fake_arxiv_metadata_query(*, search_query=None, id_list=None, max_results: int, query_kind: str) -> dict:
        records = [dict(arxiv_seed_record)] if id_list else []
        return {
            'records': records,
            'status': {'provider': 'arxiv', 'query_kind': query_kind, 'status': 'available', 'record_count': len(records), 'raw_response_saved': False},
        }

    def fake_openalex_metadata_search(query: str, *, per_page: int, query_kind: str) -> dict:
        if query_kind == 'seed_resolution':
            records = [dict(openalex_seed_record)]
        else:
            records = [dict(backward_record), dict(adjacent_record)]
        return {
            'records': records,
            'status': {'provider': 'openalex', 'query_kind': query_kind, 'status': 'available', 'record_count': len(records), 'raw_response_saved': False},
        }

    forward_calls = []

    def fake_openalex_cited_by(openalex_id: str, *, per_page: int, query_kind: str) -> dict:
        forward_calls.append((openalex_id, per_page, query_kind))
        raise AssertionError('Phase 7 must not perform per-seed forward-citation queries')

    monkeypatch.setattr('research_assistant.survey.build._arxiv_metadata_query', fake_arxiv_metadata_query)
    monkeypatch.setattr('research_assistant.survey.build._openalex_metadata_search', fake_openalex_metadata_search)
    monkeypatch.setattr('research_assistant.survey.build._openalex_cited_by', fake_openalex_cited_by)

    rc = main([
        'survey',
        'build',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
        '--mode',
        'public-metadata',
        '--public-metadata-provider',
        'openalex',
        '--public-metadata-provider',
        'arxiv',
        '--max-records',
        '25',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'metadata_only_packet'
    citation_map = json.loads((output / 'citation_map.json').read_text())
    layers = {row['layer'] for row in citation_map['nodes']}
    assert {'seed', 'backward', 'adjacent'} <= layers
    assert 'forward' not in layers
    relations = {row['relation'] for row in citation_map['edges']}
    assert 'backward_reference_metadata' in relations
    assert 'adjacent_topic_candidate_metadata' in relations
    assert 'forward_citation_metadata' not in relations
    assert forward_calls == []
    assert all(row['evidence_class'].startswith('metadata_only_public') for row in citation_map['edges'])
    assert all(row['metadata_relation_status'] == 'provider_metadata_unverified_by_source' for row in citation_map['nodes'])
    frontiers = {row['frontier_id']: row for row in citation_map['frontiers']}
    assert frontiers['seed']['status'] == 'present_metadata_only'
    assert frontiers['forward']['status'] == 'blocked_or_empty'
    assert frontiers['backward']['status'] == 'present_metadata_only'
    assert frontiers['adjacent']['status'] == 'present_metadata_only'
    assert all(row['claim_support_allowed'] is False for row in frontiers.values())
    omission_risk = json.loads((output / 'omission_risk.json').read_text())
    risk_ids = {row['risk_id'] for row in omission_risk['risks']}
    assert 'metadata_relations_unverified' in risk_ids
    assert 'forward_citation_frontier_blocked_or_empty' in risk_ids
    assert 'backward_lineage_frontier_blocked_or_empty' not in risk_ids
    source_support = json.loads((output / 'source_support.json').read_text())
    assert all(row['download_status'] == 'source_not_attempted' for row in source_support['papers'])
    claim_support = json.loads((output / 'claim_support.json').read_text())
    assert claim_support['claims'] == []


def test_cli_survey_build_offline_replay_writes_partial_packet(tmp_path: Path, capsys) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / 'fixtures'
        / 'surveybench'
        / 'online_replay'
        / 'neural_ot_seed_replay'
    )
    task = fixture / 'neural_ot_seed_replay.task.json'
    output = tmp_path / 'neural_ot_replay_packet'

    rc = main([
        'survey',
        'build',
        '--topic',
        'Neural Optimal Transport for generative modeling and inference',
        '--seed',
        'arxiv:2201.12220v3',
        '--out',
        str(output),
        '--mode',
        'offline-replay',
        '--replay-task',
        str(task),
        '--replay-responses-dir',
        str(fixture / 'responses'),
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'offline_replay_fixture_complete'
    assert payload['mode'] == 'offline-replay'
    assert payload['schema_version'] == 'ra-survey-build-cli-result-v1'
    manifest = json.loads((output / 'build_manifest.json').read_text())
    assert manifest['workflow_state']['state'] == 'offline_replay_diagnostic_complete'
    assert manifest['workflow_state']['ready_for_writer'] is False
    assert manifest['workflow_state']['ready_for_prose'] is False
    workflow_state = json.loads((output / 'workflow_state.json').read_text())
    assert workflow_state == manifest['workflow_state']
    assert payload['workflow_state'] == workflow_state
    assert payload['workflow_state_path'] == str(output / 'workflow_state.json')
    citation_map = json.loads((output / 'citation_map.json').read_text())
    assert len(citation_map['edges']) >= 3
    assert len(citation_map['clusters']) >= 1
    paper_classifications = json.loads((output / 'paper_classifications.json').read_text())
    assert paper_classifications['schema_version'] == 'ra-surveybench-paper-classifications-v1'
    assert any('major_citing_work' in row['labels'] for row in paper_classifications['classifications'])
    survey_packet = (output / 'survey_packet.md').read_text()
    assert 'OFFLINE_REPLAY_FIXTURE_COMPLETE' in survey_packet
    assert '## Paper Classifications' in survey_packet
    assert '`p_cite_001`: major_citing_work, direct_method' in survey_packet
    assert '## Source Gaps And Forbidden Uses' in survey_packet
    assert '`p_ref_001`: source `metadata_only_fixture`' in survey_packet
    assert 'technical theorem support without source' in survey_packet
    assert '## Claim Support Anchors' in survey_packet
    assert '`claim_seed_method_node`: `p_seed_001:section:sec:replay-method`' in survey_packet
    assert '## Blocked Or Unsupported Claims' in survey_packet
    assert '`claim_forbidden_dominance`: `unsupported`' in survey_packet
    assert '## Omission Risks' in survey_packet
    assert '`p_adj_001` (high)' in survey_packet


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


def test_cli_mcp_grant_and_audit_foundation(tmp_path: Path, capsys) -> None:
    rc = main([
        '--root', str(tmp_path),
        'mcp', 'grant', 'arxiv-intake',
        '--plan-hash', 'plan_fixture_hash',
        '--operation', 'source_fetch',
        '--destination', 'source',
        '--max-papers', '2',
        '--expires-hours', '2',
        '--ids', '2401.00001,2401.00002',
        '--skip-duplicates',
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload['status'] == 'created'
    grant = payload['grant']
    assert grant['mode'] == 'arxiv_batch_intake'
    assert grant['plan_hash'] == 'plan_fixture_hash'
    assert grant['destination'] == 'source'
    assert grant['max_papers'] == 2
    assert grant['arxiv_ids'] == ['2401.00001', '2401.00002']
    assert grant['review_policy'] == 'review_material_only'
    assert 'arxiv.org' in grant['allowed_domains']
    assert (tmp_path / 'local_research' / 'governance' / 'mcp' / 'grants' / f"{grant['grant_id']}.json").exists()

    rc = main(['--root', str(tmp_path), 'mcp', 'grants', 'list'])
    grants = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert grants[0]['grant_id'] == grant['grant_id']

    rc = main(['--root', str(tmp_path), 'mcp', 'grants', 'show', '--grant-id', grant['grant_id']])
    shown = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown['grant_id'] == grant['grant_id']

    rc = main(['--root', str(tmp_path), 'mcp', 'audit', 'list', '--grant-id', grant['grant_id']])
    audit = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit[0]['event_type'] == 'grant_created'


def test_cli_mcp_grant_rejects_unbounded_batch(tmp_path: Path, capsys) -> None:
    rc = main([
        '--root', str(tmp_path),
        'mcp', 'grant', 'arxiv-intake',
        '--plan-hash', 'plan_fixture_hash',
        '--max-papers', '1',
        '--ids', '2401.00001,2401.00002',
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload['status'] == 'blocked'
    assert payload['issues'][0]['code'] == 'max_papers_exceeded'


def test_cli_review_write_propose_apply_and_conflict(tmp_path: Path, capsys) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    paper_id = 'paper_review_write'
    summary_path = summaries / f'{paper_id}.json'
    summary_path.write_text(json.dumps({
        'id': paper_id,
        'title': 'Review Write Paper',
        'authors': ['Ada Example'],
        'year': 2026,
        'abstract': '',
        'main_contribution': 'Review write fixture',
        'review_status': 'needs_review',
        'requires_manual_review': True,
        'review_summary': {'status': 'needs_review'},
    }))

    rc = main(['--root', str(tmp_path), 'review-write', 'propose-status', '--paper-id', paper_id, '--status', 'approved'])
    proposed = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert proposed['status'] == 'proposed'
    confirmation_id = proposed['proposal']['confirmation_id']
    assert proposed['proposal']['old_value'] == 'needs_review'
    assert proposed['proposal']['new_value'] == 'approved'
    assert proposed['proposal']['mcp_exposure'] == 'not_exposed'

    rc = main(['--root', str(tmp_path), 'review-write', 'apply', '--confirmation-id', confirmation_id])
    applied = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert applied['status'] == 'applied'
    updated = json.loads(summary_path.read_text())
    assert updated['review_status'] == 'approved'
    assert updated['requires_manual_review'] is False

    rc = main(['--root', str(tmp_path), 'review-write', 'propose-status', '--paper-id', paper_id, '--status', 'rejected'])
    proposed = json.loads(capsys.readouterr().out)
    assert rc == 0
    confirmation_id = proposed['proposal']['confirmation_id']
    changed = json.loads(summary_path.read_text())
    changed['main_contribution'] = 'changed after proposal'
    summary_path.write_text(json.dumps(changed))

    rc = main(['--root', str(tmp_path), 'review-write', 'apply', '--confirmation-id', confirmation_id])
    blocked = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert blocked['status'] == 'blocked'
    assert any(issue['code'] == 'target_changed' for issue in blocked['issues'])

    rc = main(['--root', str(tmp_path), 'review-write', 'status'])
    status = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert status['mcp_exposed'] is False
    assert status['proposal_counts']['applied'] == 1
    assert status['proposal_counts']['pending'] == 1


def test_cli_review_write_creates_distinct_repeated_proposals(tmp_path: Path, capsys) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    paper_id = 'paper_repeated_review_write'
    (summaries / f'{paper_id}.json').write_text(json.dumps({
        'id': paper_id,
        'title': 'Repeated Review Write Paper',
        'authors': ['Ada Example'],
        'year': 2026,
        'abstract': '',
        'main_contribution': 'Review write fixture',
        'review_status': 'needs_review',
        'requires_manual_review': True,
        'review_summary': {'status': 'needs_review'},
    }))

    rc = main(['--root', str(tmp_path), 'review-write', 'propose-status', '--paper-id', paper_id, '--status', 'approved'])
    first = json.loads(capsys.readouterr().out)
    rc2 = main(['--root', str(tmp_path), 'review-write', 'propose-status', '--paper-id', paper_id, '--status', 'approved'])
    second = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert rc2 == 0
    assert first['proposal']['confirmation_id'] != second['proposal']['confirmation_id']
    assert first['proposal']['confirmation_nonce'] != second['proposal']['confirmation_nonce']
    assert Path(first['proposal_path']).exists()
    assert Path(second['proposal_path']).exists()


def test_cli_review_write_rejects_invalid_expiry(tmp_path: Path, capsys) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    paper_id = 'paper_invalid_expiry'
    (summaries / f'{paper_id}.json').write_text(json.dumps({
        'id': paper_id,
        'title': 'Invalid Expiry Paper',
        'authors': [],
        'year': 2026,
        'review_status': 'needs_review',
    }))

    rc = main([
        '--root', str(tmp_path),
        'review-write', 'propose-status',
        '--paper-id', paper_id,
        '--status', 'approved',
        '--expires-minutes', '0',
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'blocked'
    assert payload['issues'][0]['code'] == 'invalid_expiry'


def test_cli_review_write_cleanup_expired_is_dry_run_by_default(tmp_path: Path, capsys) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    paper_id = 'paper_expired_cleanup'
    (summaries / f'{paper_id}.json').write_text(json.dumps({
        'id': paper_id,
        'title': 'Expired Cleanup Paper',
        'authors': [],
        'year': 2026,
        'review_status': 'needs_review',
    }))

    rc = main([
        '--root', str(tmp_path),
        'review-write', 'propose-status',
        '--paper-id', paper_id,
        '--status', 'approved',
        '--expires-minutes', '1',
    ])
    proposed = json.loads(capsys.readouterr().out)
    proposal_path = Path(proposed['proposal_path'])
    proposal = json.loads(proposal_path.read_text())
    proposal['expires_at'] = '2000-01-01T00:00:00+00:00'
    proposal_path.write_text(json.dumps(proposal))

    rc = main(['--root', str(tmp_path), 'review-write', 'cleanup-expired'])
    dry_run = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert dry_run['status'] == 'dry_run'
    assert dry_run['expired_count'] == 1
    assert proposal_path.exists()

    rc = main(['--root', str(tmp_path), 'review-write', 'cleanup-expired', '--apply'])
    cleaned = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert cleaned['status'] == 'cleaned'
    assert cleaned['expired_count'] == 1
    assert not proposal_path.exists()


def test_cli_find_reports_review_status(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'authors': ['Berardino Palazzo'],
        'year': 2020,
        'abstract': '',
        'main_contribution': 'Credit transmission result',
        'curation_status': 'draft',
        'metadata_confidence': 'low',
        'identity_source': 'parser_consensus',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review', 'warnings': ['metadata confidence is low']},
        'requires_manual_review': True,
        'candidate_metadata_sources': {},
        'merge_notes': [],
        'provenance': {},
    }))

    rc = main(['--root', str(root), 'find', '--query', 'credit'])
    captured = capsys.readouterr()

    assert rc == 0
    assert 'paper_a\t2020\tneeds_review\tCredit Risk and the Transmission of Interest Rate Shocks' in captured.out


def test_cli_find_applies_review_author_and_year_filters(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'authors': ['Berardino Palazzo'],
        'year': 2020,
        'abstract': '',
        'main_contribution': 'Credit transmission result',
        'review_status': 'approved',
    }))
    (summaries / 'paper_b.json').write_text(json.dumps({
        'id': 'paper_b',
        'title': 'Another Credit Paper',
        'authors': ['Alice Example'],
        'year': 2021,
        'abstract': '',
        'main_contribution': 'Credit follow-up',
        'review_status': 'needs_review',
    }))

    rc = main([
        '--root', str(root), 'find', '--query', 'credit', '--review-status', 'approved', '--author', 'palazzo', '--year', '2020'
    ])
    captured = capsys.readouterr()

    assert rc == 0
    assert 'paper_a\t2020\tapproved\tCredit Risk and the Transmission of Interest Rate Shocks' in captured.out
    assert 'paper_b' not in captured.out


def test_cli_show_foregrounds_review_and_identity_validation(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    metadata_dir = root / 'local_research' / 'metadata'
    extracted_dir = root / 'local_research' / 'papers' / 'extracted'
    summaries.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    extracted_dir.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Approved Paper',
        'authors': ['Alice Example'],
        'year': 2020,
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
        'review_summary': {'status': 'approved', 'warnings': []},
        'requires_manual_review': False,
        'provenance': {'title': 'parser_consensus'},
    }))
    (metadata_dir / 'paper_a.json').write_text(json.dumps({
        'identity_validation': {'status': 'validated', 'requires_manual_review': False},
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'available', 'result_count': 1},
        ],
    }))

    rc = main(['--root', str(root), 'show', '--paper-id', 'paper_a'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['review']['review_status'] == 'approved'
    assert payload['review']['requires_manual_review'] is False
    assert payload['review']['provenance']['title'] == 'parser_consensus'
    assert payload['review']['identity_validation']['status'] == 'validated'
    assert payload['review']['metadata_source_statuses'][0]['source'] == 'semanticscholar'
    assert payload['review']['metadata_source_statuses'][0]['code'] == 429
    assert payload['summary']['id'] == 'paper_a'
    assert payload['extraction']['extracted_text_available'] is False
    assert payload['extraction']['consensus_section_headings'] == []
    assert payload['extraction']['parser_reconciliation']['parse_confidence'] == 'low'
    assert payload['extraction']['limitations'][0]['field'] == 'equations'
    assert payload['extraction']['limitations'][1]['field'] == 'citations'
    assert payload['technical_audit']['transport_definition'] == ''
    assert payload['technical_audit']['claimed_results'] == []


def test_cli_show_surfaces_extraction_artifacts_and_parser_reconciliation(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    metadata_dir = root / 'local_research' / 'metadata'
    extracted_dir = root / 'local_research' / 'papers' / 'extracted'
    summaries.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    extracted_dir.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Parser First Paper',
        'authors': ['Alice Example'],
        'year': 2024,
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review', 'warnings': ['parser confidence is low']},
        'requires_manual_review': True,
        'provenance': {'title': 'parser_consensus'},
    }))
    (metadata_dir / 'paper_a.json').write_text(json.dumps({
        'identity_validation': {'status': 'validated', 'requires_manual_review': False},
        'parser_hints': {
            'consensus_section_headings': ['Introduction', 'Method', 'Experiments'],
            'parse_confidence': 'medium',
            'requires_manual_review': True,
            'parser_agreement': {'title': 'strong', 'authors': 'partial'},
            'disagreements': ['author list differs across parsers'],
            'parser_outputs': [
                {
                    'parser_name': 'pdftotext',
                    'parser_version': '1.0',
                    'parse_status': 'partial',
                    'section_headings': ['Introduction'],
                    'diagnostics': {'available': True},
                    'body_text': 'text',
                    'capabilities': {
                        'section_headings': 'partial',
                        'equations': 'unreliable',
                        'citations': 'unreliable',
                    },
                },
                {
                    'parser_name': 'marker',
                    'parser_version': '0.1',
                    'parse_status': 'success',
                    'section_headings': ['Introduction', 'Method'],
                    'diagnostics': {'available': True},
                    'body_markdown': '# Introduction',
                    'capabilities': {
                        'section_headings': 'partial',
                        'equations': 'unreliable',
                        'citations': 'unreliable',
                    },
                },
            ],
        },
    }))
    extracted_path = extracted_dir / 'paper_a.txt'
    extracted_path.write_text('Extracted text')

    rc = main(['--root', str(root), 'show', '--paper-id', 'paper_a'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['extraction']['extracted_text_available'] is True
    assert payload['extraction']['extracted_text_path'] == str(extracted_path)
    assert payload['extraction']['consensus_section_headings'] == ['Introduction', 'Method', 'Experiments']
    assert payload['extraction']['parser_reconciliation']['parse_confidence'] == 'medium'
    assert payload['extraction']['parser_reconciliation']['requires_manual_review'] is True
    assert payload['extraction']['parser_reconciliation']['parser_agreement']['title'] == 'strong'
    assert payload['extraction']['parser_reconciliation']['disagreements'] == ['author list differs across parsers']
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][0]['parser_name'] == 'pdftotext'
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][0]['capabilities']['equations'] == 'unreliable'
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][1]['parse_status'] == 'success'
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][1]['capabilities']['citations'] == 'unreliable'
    assert payload['extraction']['warnings'] == ['author list differs across parsers']
    assert payload['extraction']['limitations'][0]['status'] == 'unreliable'
    assert payload['extraction']['limitations'][1]['status'] == 'unreliable'
    assert payload['technical_audit']['relevant_sections'] == []
    assert payload['technical_audit']['assumptions_for_reuse'] == []


def test_cli_review_commands_update_status(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'authors': ['Berardino Palazzo'],
        'year': 2020,
        'abstract': '',
        'main_contribution': 'Credit transmission result',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review'},
        'requires_manual_review': True,
        'candidate_metadata_sources': {},
        'merge_notes': ['manual review recommended'],
        'provenance': {'title': 'parser_consensus'},
    }))

    rc = main(['--root', str(root), 'review-list'])
    listed = capsys.readouterr()
    assert rc == 0
    assert 'paper_a\t2020\tneeds_review' in listed.out

    rc = main(['--root', str(root), 'review-show', '--paper-id', 'paper_a'])
    shown = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown['provenance']['title'] == 'parser_consensus'
    assert shown['summary']['technical_audit']['transport_definition'] == ''
    assert shown['summary']['technical_audit']['claimed_results'] == []

    rc = main(['--root', str(root), 'review-mark', '--paper-id', 'paper_a', '--status', 'approved'])
    marked = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert marked['review_status'] == 'approved'
    assert marked['requires_manual_review'] is False


def test_cli_export_context_writes_filtered_payload(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Approved Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    (summaries / 'paper_b.json').write_text(json.dumps({
        'id': 'paper_b',
        'title': 'Needs Review Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
    }))
    output = root / 'approved_context.json'

    rc = main(['--root', str(root), 'export-context', '--output', str(output), '--review-status', 'approved'])
    captured = capsys.readouterr()
    payload = json.loads(output.read_text())

    assert rc == 0
    assert captured.out.strip() == str(output)
    assert [paper['id'] for paper in payload['papers']] == ['paper_a']
    assert payload['papers'][0]['technical_audit']['transport_definition'] == ''
    assert payload['papers'][0]['technical_audit']['relevant_sections'] == []


def test_cli_ingest_palazzo_uses_parser_consensus(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(metadata_resolve, '_fetch_json', lambda url: {'results': [], 'message': {'items': []}})
    monkeypatch.setattr(metadata_resolve, 'choose_best_semanticscholar_result', lambda *args, **kwargs: ({}, []))
    monkeypatch.setattr(cli, 'extract_pdf_text', lambda raw_path: 'Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy')
    monkeypatch.setattr(cli, 'parse_with_all', lambda raw_path: [
        ParsedDocument(
            parser_name='fixture_parser_a',
            parser_version='1.0',
            title_candidates=['Credit Risk and the Transmission of Interest Rate Shocks'],
            authors=['Berardino Palazzo', 'Ram Yamarthy'],
            section_headings=['Introduction'],
            body_markdown='Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy',
            parse_status='ok',
        ),
        ParsedDocument(
            parser_name='fixture_parser_b',
            parser_version='1.0',
            title_candidates=['Credit Risk and the Transmission of Interest Rate Shocks'],
            authors=['Berardino Palazzo', 'Ram Yamarthy'],
            section_headings=['Introduction'],
            body_markdown='Credit Risk and the Transmission of Interest Rate Shocks\nBerardino Palazzo\nRam Yamarthy',
            parse_status='ok',
        ),
    ])

    pdf = tmp_path / 'fixtures' / 'credit_risk_transmission_palazzo.pdf'
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b'%PDF-1.4\n% sanitized parser-consensus fixture\n')
    query = 'Credit Risk and the Transmission of Interest Rate Shocks Palazzo'
    rc = main(['--root', str(tmp_path), 'ingest', '--pdf', str(pdf), '--query', query])
    captured = capsys.readouterr()
    paper_id = canonical_paper_id(str(pdf))

    assert rc == 0
    assert captured.out.strip() == paper_id

    metadata = json.loads((tmp_path / 'local_research' / 'metadata' / f'{paper_id}.json').read_text())
    summary = json.loads((tmp_path / 'local_research' / 'summaries' / f'{paper_id}.json').read_text())

    assert metadata['parser_hints']['consensus_title'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert metadata['parser_hints']['consensus_authors'] == ['Berardino Palazzo', 'Ram Yamarthy']
    assert summary['title'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert summary['authors'] == ['Berardino Palazzo', 'Ram Yamarthy']
    assert summary['identity_source'] == 'parser_consensus'
    assert summary['requires_manual_review'] is True


def test_cli_parse_pdf_reports_parser_capability_limits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'parse_with_all', lambda pdf_path: [
        ParsedDocument(
            parser_name='marker',
            parser_version='0.1',
            title_candidates=['Parser Capability Paper'],
            authors=['Alice Example'],
            section_headings=['Introduction'],
            body_markdown='Parser Capability Paper\nAlice Example',
            parse_status='ok',
        )
    ])

    rc = main(['parse-pdf', '--pdf', '/tmp/example.pdf'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['parser_outputs'][0]['parser_name'] == 'marker'
    assert payload['parser_outputs'][0]['capabilities']['section_headings'] == 'partial'
    assert payload['parser_outputs'][0]['capabilities']['equations'] == 'unreliable'
    assert payload['parser_outputs'][0]['capabilities']['citations'] == 'unreliable'


def test_cli_parser_preflight_reports_capability_limits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'preflight_all', lambda: [
        ParserPreflight(
            'pdftotext',
            False,
            'unavailable',
            ['pdftotext not found in PATH'],
            {
                'command': 'pdftotext',
                'capabilities': {
                    'section_headings': 'partial',
                    'equations': 'unreliable',
                    'citations': 'unreliable',
                },
            },
        )
    ])

    rc = main(['parser-preflight'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload[0]['parser_name'] == 'pdftotext'
    assert payload[0]['details']['capabilities']['section_headings'] == 'partial'
    assert payload[0]['details']['capabilities']['equations'] == 'unreliable'
    assert payload[0]['details']['capabilities']['citations'] == 'unreliable'

def test_cli_discover_reports_degraded_source_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'empty',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })

    rc = main(['discover', '--query', 'transport maps'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'empty'
    assert payload['results'] == []
    assert payload['source_statuses'][0]['source'] == 'semanticscholar'
    assert payload['source_statuses'][0]['code'] == 429


def test_cli_citation_neighborhood_reports_ranked_summary(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli.citation_graph, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'available',
        'citing': [],
        'cited': [],
        'citing_count': 1,
        'cited_count': 1,
        'summary': {
            'top_citing': [
                {
                    'source_id': 'citing-1',
                    'title': 'Useful Citing Paper',
                    'authors': ['Alice Example'],
                    'year': 2025,
                    'citation_count': 7,
                    'influential_citation_count': 1,
                    'open_access_pdf_url': 'https://example.com/citing.pdf',
                    'ranking_score': 20,
                }
            ],
            'top_cited': [
                {
                    'source_id': 'cited-1',
                    'title': 'Useful Cited Paper',
                    'authors': ['Bob Example'],
                    'year': 2020,
                    'citation_count': 12,
                    'influential_citation_count': 3,
                    'open_access_pdf_url': None,
                    'ranking_score': 21,
                }
            ],
        },
    })

    rc = main(['citation-neighborhood', '--paper-id', 'seed-paper'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['paper_id'] == 'seed-paper'
    assert payload['summary']['top_citing'][0]['source_id'] == 'citing-1'
    assert payload['summary']['top_cited'][0]['source_id'] == 'cited-1'

    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Downloadable Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'available',
        'results': [
            {
                'source': 'semanticscholar',
                'title': 'Downloadable Paper',
                'open_access_pdf_url': 'https://example.com/paper.pdf',
            }
        ],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'available', 'result_count': 1},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })
    monkeypatch.setattr(cli, 'download_to_inbox', lambda pdf_url, filename_hint, root=None: Path(root) / 'local_research' / 'inbox' / f'{filename_hint}.pdf')

    rc = main(['--root', str(tmp_path), 'download-paper', '--query', 'downloadable'])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload['downloaded'] is True
    assert payload['discovery']['status'] == 'available'
    assert payload['proposal']['proposed_name'] == 'downloadable_paper.pdf'
    assert payload['proposal']['schema_version'] == 1
    assert payload['proposal']['query'] == 'downloadable'
    assert payload['proposal']['duplicate_status'] == 'possible_duplicate'
    assert payload['proposal']['duplicate_candidates'][0]['paper_id'] == 'paper_a'
    proposal_path = Path(payload['proposal_path'])
    assert proposal_path.exists()
    persisted = json.loads(proposal_path.read_text())
    assert persisted['schema_version'] == 1
    assert persisted['query'] == 'downloadable'
    assert persisted['proposed_name'] == 'downloadable_paper.pdf'
    assert persisted['duplicate_status'] == 'possible_duplicate'
    assert persisted['result']['open_access_pdf_url'] == 'https://example.com/paper.pdf'


def test_cli_download_paper_reports_discovery_unavailable(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'unavailable',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'unavailable', 'result_count': 0},
        ],
    })

    rc = main(['download-paper', '--query', 'transport maps'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['downloaded'] is False
    assert payload['reason'] == 'discovery unavailable'
    assert payload['discovery']['status'] == 'unavailable'
    assert payload['discovery']['source_statuses'][0]['code'] == 429


def test_cli_download_paper_reports_empty_discovery_without_silent_oa_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'empty',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })

    rc = main(['download-paper', '--query', 'transport maps'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['downloaded'] is False
    assert payload['reason'] == 'discovery returned no open access candidates'
    assert payload['discovery']['status'] == 'empty'
    assert payload['discovery']['source_statuses'][0]['code'] == 429


def test_cli_download_paper_reports_results_without_open_access_pdf(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'available',
        'results': [
            {'source': 'semanticscholar', 'title': 'Closed Paper', 'open_access_pdf_url': None},
        ],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'available', 'result_count': 1},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })

    rc = main(['download-paper', '--query', 'closed paper'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['downloaded'] is False
    assert payload['reason'] == 'no open access pdf found'
    assert payload['discovery']['status'] == 'available'
    assert payload['discovery']['results'][0]['title'] == 'Closed Paper'


def test_cli_inbox_commands_show_persisted_proposals(tmp_path: Path, monkeypatch, capsys) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Downloadable Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'available',
        'results': [
            {
                'source': 'semanticscholar',
                'title': 'Downloadable Paper',
                'open_access_pdf_url': 'https://example.com/paper.pdf',
            }
        ],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'available', 'result_count': 1},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })
    monkeypatch.setattr(cli, 'download_to_inbox', lambda pdf_url, filename_hint, root=None: Path(root) / 'local_research' / 'inbox' / f'{filename_hint}.pdf')
    main(['--root', str(tmp_path), 'download-paper', '--query', 'downloadable'])
    capsys.readouterr()

    rc = main(['--root', str(tmp_path), 'inbox-list', '--duplicate-status', 'unique'])
    listed = capsys.readouterr()
    assert rc == 0
    assert listed.out == ''

    rc = main(['--root', str(tmp_path), 'inbox-list', '--duplicate-status', 'possible_duplicate'])
    listed = capsys.readouterr()
    assert rc == 0
    assert 'downloadable_paper.pdf	possible_duplicate	1	semanticscholar	Downloadable Paper' in listed.out

    rc = main(['--root', str(tmp_path), 'inbox-show', '--proposed-name', 'downloadable_paper.pdf'])
    shown = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown['query'] == 'downloadable'
    assert shown['proposed_name'] == 'downloadable_paper.pdf'
    assert shown['duplicate_status'] == 'possible_duplicate'
    assert shown['duplicate_candidates'][0]['paper_id'] == 'paper_a'
    assert shown['review_summary']['duplicate_status'] == 'possible_duplicate'
    assert shown['review_summary']['duplicate_count'] == 1
    assert shown['review_summary']['matched_paper_ids'] == ['paper_a']


def test_cli_audit_workflow_stays_usable_when_citation_enrichment_is_unavailable(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    metadata_dir = root / 'local_research' / 'metadata'
    extracted_dir = root / 'local_research' / 'papers' / 'extracted'
    summaries.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    extracted_dir.mkdir(parents=True)

    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Audit Seed Paper',
        'authors': ['Alice Example'],
        'year': 2024,
        'abstract': '',
        'main_contribution': 'A contribution worth checking carefully.',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review', 'warnings': ['parser confidence is low']},
        'requires_manual_review': True,
        'provenance': {'title': 'parser_consensus'},
    }))
    (metadata_dir / 'paper_a.json').write_text(json.dumps({
        'identity_validation': {
            'status': 'validated',
            'requires_manual_review': False,
            'citation_neighborhood': {'status': 'unavailable'},
        },
        'parser_hints': {
            'consensus_section_headings': ['Introduction', 'Model', 'Conclusion'],
            'parse_confidence': 'medium',
            'requires_manual_review': True,
            'parser_agreement': {'title': 'strong'},
            'disagreements': ['affiliation lines differ across parsers'],
            'parser_outputs': [
                {
                    'parser_name': 'pdftotext',
                    'parser_version': '1.0',
                    'parse_status': 'partial',
                    'section_headings': ['Introduction', 'Model'],
                    'diagnostics': {'available': True},
                }
            ],
        },
    }))
    (extracted_dir / 'paper_a.txt').write_text('Technical text for audit workflow')

    rc = main(['--root', str(root), 'show', '--paper-id', 'paper_a'])
    show_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert show_payload['review']['identity_validation']['citation_neighborhood']['status'] == 'unavailable'
    assert show_payload['extraction']['extracted_text_available'] is True
    assert show_payload['extraction']['parser_reconciliation']['disagreements'] == ['affiliation lines differ across parsers']

    monkeypatch.setattr(cli.citation_graph, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'empty',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'source_statuses': [
            {'endpoint': 'citations', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'endpoint': 'references', 'status': 'available', 'result_count': 0},
        ],
        'summary': {'top_citing': [], 'top_cited': []},
    })
    rc = main(['--root', str(root), 'citation-neighborhood', '--paper-id', 'paper_a'])
    citation_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert citation_payload['status'] == 'empty'
    assert citation_payload['source_statuses'][0]['endpoint'] == 'citations'
    assert citation_payload['source_statuses'][0]['code'] == 429
    assert citation_payload['summary']['top_citing'] == []
    assert citation_payload['summary']['top_cited'] == []

    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'empty',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })
    rc = main(['--root', str(root), 'download-paper', '--query', 'audit seed paper'])
    download_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert download_payload['downloaded'] is False
    assert download_payload['reason'] == 'discovery returned no open access candidates'
    assert download_payload['discovery']['status'] == 'empty'
    assert download_payload['discovery']['source_statuses'][0]['code'] == 429

    rc = main(['--root', str(root), 'review-mark', '--paper-id', 'paper_a', '--status', 'approved'])
    review_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert review_payload['review_status'] == 'approved'
    assert review_payload['requires_manual_review'] is False

    export_path = root / 'approved_context.json'
    rc = main(['--root', str(root), 'export-context', '--output', str(export_path), '--review-status', 'approved'])
    exported = json.loads(export_path.read_text())


def test_cli_local_ingest_audit_scenario_preserves_trust_checkpoints(tmp_path: Path, monkeypatch, capsys) -> None:
    pdf = tmp_path / 'neural_transport_hmc.pdf'
    pdf.write_bytes(b'%PDF-1.4 synthetic')
    paper_id = canonical_paper_id(str(pdf))

    monkeypatch.setattr(cli, 'extract_pdf_text', lambda raw_path: 'Neural Transport HMC\nAlice Example\n1 Introduction\n2 Method')
    monkeypatch.setattr(cli, 'parse_with_all', lambda raw_path: [
        ParsedDocument(
            parser_name='marker',
            parser_version='0.1',
            title_candidates=['Neural Transport HMC'],
            authors=['Alice Example'],
            section_headings=['Introduction', 'Method'],
            body_markdown='Neural Transport HMC\nAlice Example\n# Introduction\n# Method',
            parse_status='ok',
        ),
        ParsedDocument(
            parser_name='pdftotext',
            parser_version='1.0',
            title_candidates=['Neural Transport HMC'],
            authors=['Alice Example'],
            section_headings=['Introduction'],
            body_text='Neural Transport HMC\nAlice Example\nIntroduction',
            parse_status='ok',
        ),
    ])

    def fake_resolve_metadata(query, *, arxiv_id=None, extracted_text='', filename_hints=None, parser_hints=None):
        return {
            'title': parser_hints['consensus_title'],
            'authors': parser_hints['consensus_authors'],
            'abstract': 'Synthetic abstract for a local-first audit scenario.',
            'year': 2024,
            'parser_hints': parser_hints,
            'provenance': {'title': 'parser_consensus', 'authors': 'parser_consensus'},
        }

    monkeypatch.setattr(cli, 'resolve_metadata', fake_resolve_metadata)
    monkeypatch.setattr(cli, 'validate_identity', lambda metadata: {'status': 'validated', 'requires_manual_review': False})

    rc = main(['--root', str(tmp_path), 'ingest', '--pdf', str(pdf), '--query', 'Neural Transport HMC'])
    assert rc == 0
    assert capsys.readouterr().out.strip() == paper_id

    rc = main(['--root', str(tmp_path), 'show', '--paper-id', paper_id])
    show_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert show_payload['extraction']['extracted_text_available'] is True
    assert show_payload['extraction']['consensus_section_headings'] == ['Introduction']
    assert show_payload['extraction']['parser_reconciliation']['parse_confidence'] == 'medium'
    assert show_payload['extraction']['parser_reconciliation']['parser_outputs_used'][0]['capabilities']['equations'] == 'unreliable'
    assert show_payload['technical_audit']['transport_definition'] == ''

    summary_path = tmp_path / 'local_research' / 'summaries' / f'{paper_id}.json'
    summary = json.loads(summary_path.read_text())
    summary['technical_audit']['transport_definition'] = 'Map z to theta before HMC proposal generation.'
    summary['technical_audit']['objective'] = 'Improve posterior geometry without changing the exact MH target.'
    summary['technical_audit']['relevant_sections'] = ['Method']
    summary_path.write_text(json.dumps(summary))

    monkeypatch.setattr(cli.citation_graph, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'unavailable',
        'status_reason': 'all citation endpoints are unavailable',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'source_statuses': [
            {'endpoint': 'citations', 'status': 'unavailable', 'code': 429, 'reason': 'rate limited', 'result_count': 0},
            {'endpoint': 'references', 'status': 'unavailable', 'code': 429, 'reason': 'rate limited', 'result_count': 0},
        ],
        'diagnostics': {
            'unavailable_endpoints': ['citations', 'references'],
            'available_empty_endpoints': [],
            'failure_reasons': [
                {'endpoint': 'citations', 'code': 429, 'reason': 'rate limited'},
                {'endpoint': 'references', 'code': 429, 'reason': 'rate limited'},
            ],
        },
        'summary': {'top_citing': [], 'top_cited': []},
    })
    rc = main(['--root', str(tmp_path), 'citation-neighborhood', '--paper-id', paper_id])
    citation_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert citation_payload['status'] == 'unavailable'
    assert citation_payload['status_reason'] == 'all citation endpoints are unavailable'
    assert citation_payload['diagnostics']['unavailable_endpoints'] == ['citations', 'references']
    assert [row['status'] for row in citation_payload['source_statuses']] == ['unavailable', 'unavailable']

    monkeypatch.setattr(cli.citation_graph, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'available',
        'status_reason': 'citation data returned from at least one endpoint',
        'citing': [
            {
                'source': 'semanticscholar',
                'source_id': 'citing-1',
                'title': 'Useful Citing Paper',
                'authors': ['Reader Example'],
                'year': 2025,
                'citation_count': 8,
                'open_access_pdf_url': 'https://example.com/citing.pdf',
                'provenance': {'source': 'mock'},
            }
        ],
        'cited': [],
        'citing_count': 1,
        'cited_count': 0,
        'source_statuses': [
            {'endpoint': 'citations', 'status': 'available', 'result_count': 1},
            {'endpoint': 'references', 'status': 'available', 'result_count': 0},
        ],
        'diagnostics': {'unavailable_endpoints': [], 'available_empty_endpoints': ['references'], 'failure_reasons': []},
        'summary': {'top_citing': [{'source_id': 'citing-1', 'title': 'Useful Citing Paper'}], 'top_cited': []},
    })
    rc = main(['--root', str(tmp_path), 'citation-graph-build', '--paper-id', paper_id, '--depth', '2', '--refresh'])
    graph_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert graph_payload['seed_paper_id'] == paper_id
    assert graph_payload['edges'][0]['source'] == 'semanticscholar:citing-1'
    assert graph_payload['edges'][0]['target'] == paper_id
    assert graph_payload['diagnostics']['available_empty_endpoints'] == ['references']
    assert graph_payload['depth'] == 2
    assert graph_payload['diagnostics']['node_count'] >= 2

    rc = main(['--root', str(tmp_path), 'citation-graph-show', '--paper-id', paper_id])
    shown_graph = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown_graph['nodes']['semanticscholar:citing-1']['title'] == 'Useful Citing Paper'

    graph_export = tmp_path / 'graph.json'
    rc = main(['--root', str(tmp_path), 'citation-graph-export', '--paper-id', paper_id, '--output', str(graph_export)])
    assert rc == 0
    capsys.readouterr()
    assert json.loads(graph_export.read_text())['edges'][0]['direction'] == 'citing'

    rc = main(['--root', str(tmp_path), 'graph-node-download-proposal', '--paper-id', paper_id, '--node-id', 'semanticscholar:citing-1'])
    graph_download = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert graph_download['proposal']['proposed_name'] == 'useful_citing_paper.pdf'
    assert graph_download['proposal']['result']['provenance']['node_id'] == 'semanticscholar:citing-1'

    rc = main(['--root', str(tmp_path), 'literature-audit-propose', '--paper-id', paper_id])
    proposal_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert proposal_payload['status'] == 'requires_human_review'
    assert proposal_payload['paper_claims'] == []
    assert proposal_payload['graph_context']['available'] is True
    assert 'verified mathematical conclusion' in proposal_payload['limitations'][1]

    rc = main(['--root', str(tmp_path), 'literature-audit-show', '--paper-id', paper_id])
    shown_proposal = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown_proposal['proposal_id'].endswith('source-v1')

    rc = main(['--root', str(tmp_path), 'review-mark', '--paper-id', paper_id, '--status', 'approved'])
    review_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert review_payload['review_status'] == 'approved'

    export_path = tmp_path / 'approved_context.json'
    rc = main(['--root', str(tmp_path), 'export-context', '--output', str(export_path), '--review-status', 'approved'])
    exported = json.loads(export_path.read_text())
    assert rc == 0
    assert exported['papers'][0]['id'] == paper_id
    assert exported['papers'][0]['technical_audit']['transport_definition'] == 'Map z to theta before HMC proposal generation.'
    assert exported['papers'][0]['technical_audit']['objective'] == 'Improve posterior geometry without changing the exact MH target.'
    assert exported['papers'][0]['technical_audit']['relevant_sections'] == ['Method']


def test_cli_source_fetch_show_and_ingest_expose_structured_source(tmp_path: Path, monkeypatch, capsys) -> None:
    fixture = Path(__file__).resolve().parents[1] / 'fixtures' / 'latex_sources' / 'multi_file'

    def source_tarball() -> bytes:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            for path in sorted(fixture.rglob('*')):
                if path.is_file():
                    archive.add(path, arcname=str(path.relative_to(fixture)))
        return buffer.getvalue()

    def fake_download(arxiv_id: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_tarball())
        return destination

    monkeypatch.setattr('research_assistant.source.arxiv_source.download_arxiv_source', fake_download)
    monkeypatch.setattr(cli, 'fetch_arxiv_structured_source', __import__('research_assistant.source.arxiv_source', fromlist=['fetch_arxiv_structured_source']).fetch_arxiv_structured_source)
    monkeypatch.setattr(cli, 'resolve_metadata', lambda query, *, arxiv_id=None, extracted_text='', filename_hints=None, parser_hints=None: {
        'arxiv': {
            'arxiv_id': arxiv_id,
            'title': 'Structured Source HMC',
            'authors': ['Alice Example'],
            'abstract': 'We study source-first extraction.',
        },
        'metadata_confidence': 'high',
        'source_statuses': [{'source': 'arxiv', 'status': 'available', 'result_count': 1}],
        'provenance': {'arxiv': 'exact arxiv id supplied'},
    })
    monkeypatch.setattr(cli, 'validate_identity', lambda metadata: {'status': 'validated', 'requires_manual_review': False})

    rc = main(['--root', str(tmp_path), 'source-fetch', '--arxiv-id', '2401.00001', '--paper-id', 'paper_source_first'])
    fetched = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert fetched['status'] == 'available'
    assert fetched['primary_for_audit'] is True
    assert fetched['sections'][1]['title'] == 'Method'

    rc = main(['--root', str(tmp_path), 'source-show', '--paper-id', 'paper_source_first'])
    shown_source = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown_source['equations'][0]['labels'] == ['eq:target']

    rc = main(['--root', str(tmp_path), 'source-sections', '--paper-id', 'paper_source_first'])
    sections = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert [section['title'] for section in sections] == ['Introduction', 'Method']

    rc = main(['--root', str(tmp_path), 'source-section', '--paper-id', 'paper_source_first', '--label', 'sec:method'])
    method_section = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert method_section['title'] == 'Method'
    assert 'transformed target' in method_section['raw_latex']

    try:
        main(['--root', str(tmp_path), 'source-section', '--paper-id', 'paper_source_first'])
    except SystemExit as exc:
        assert str(exc) == 'source-section requires --title or --label'
    else:
        raise AssertionError('source-section without selector should fail')

    rc = main(['--root', str(tmp_path), 'source-equations', '--paper-id', 'paper_source_first'])
    equations = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert equations[0]['labels'] == ['eq:target']

    rc = main(['--root', str(tmp_path), 'source-equation', '--paper-id', 'paper_source_first', '--label', 'eq:target'])
    equation = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert equation['labels'] == ['eq:target']
    assert 'exp(-U' in equation['raw_latex']

    rc = main(['--root', str(tmp_path), 'source-theorems', '--paper-id', 'paper_source_first'])
    theorems = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert theorems[0]['labels'] == ['thm:exact']

    rc = main(['--root', str(tmp_path), 'source-theorem', '--paper-id', 'paper_source_first', '--label', 'thm:exact'])
    theorem = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert theorem['labels'] == ['thm:exact']
    assert 'preserves the target' in theorem['raw_latex']

    rc = main(['--root', str(tmp_path), 'source-citations', '--paper-id', 'paper_source_first'])
    citations = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert citations[0]['keys'] == ['neal2011mcmc']

    rc = main(['--root', str(tmp_path), 'source-bibliography', '--paper-id', 'paper_source_first'])
    bibliography = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert bibliography[0]['key'] == 'neal2011mcmc'

    rc = main(['--root', str(tmp_path), 'source-macros', '--paper-id', 'paper_source_first'])
    macros = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert macros[0]['name'] == 'target'

    rc = main(['--root', str(tmp_path), 'source-labels', '--paper-id', 'paper_source_first'])
    labels = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert {label['key'] for label in labels} >= {'sec:intro', 'sec:method', 'eq:target', 'thm:exact'}

    rc = main(['--root', str(tmp_path), 'source-refs', '--paper-id', 'paper_source_first'])
    refs = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert {ref['key'] for ref in refs} >= {'sec:method', 'eq:target'}

    paper_id = canonical_paper_id('arxiv:2401.00001')
    rc = main(['--root', str(tmp_path), 'ingest', '--arxiv-id', '2401.00001', '--query', 'Structured Source HMC'])
    assert rc == 0
    assert capsys.readouterr().out.strip() == paper_id

    rc = main(['--root', str(tmp_path), 'show', '--paper-id', paper_id])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload['source_extraction']['available'] is True
    assert payload['source_extraction']['primary_source'] == 'arxiv_latex'
    assert payload['source_extraction']['section_count'] == 2
    assert payload['source_extraction']['equation_count'] == 1
    assert payload['source_extraction']['theorem_like_block_count'] == 1
    assert payload['pdf_extraction']['extracted_text_available'] is False
    assert payload['technical_audit']['transport_definition'] == ''
    assert payload['metadata']['structured_source']['primary_for_audit'] is True

    rc = main(['--root', str(tmp_path), 'audit-note', 'show', '--paper-id', paper_id])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['objective'] == ''

    rc = main(['--root', str(tmp_path), 'audit-note', 'set', '--paper-id', paper_id, '--field', 'objective', '--value', 'Preserve exact HMC correction while improving geometry.'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['updated'] is True
    assert audit_payload['technical_audit']['objective'] == 'Preserve exact HMC correction while improving geometry.'

    rc = main(['--root', str(tmp_path), 'audit-note', 'append', '--paper-id', paper_id, '--field', 'claimed_results', '--value', 'Source extraction preserves the target.'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['claimed_results'] == ['Source extraction preserves the target.']

    rc = main(['--root', str(tmp_path), 'audit-note', 'link-section', '--paper-id', paper_id, '--label', 'sec:method'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['relevant_sections'] == ['sec:method']

    rc = main(['--root', str(tmp_path), 'audit-note', 'link-equation', '--paper-id', paper_id, '--label', 'eq:target'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['relevant_equations'] == ['eq:target']

    rc = main(['--root', str(tmp_path), 'audit-note', 'link-theorem', '--paper-id', paper_id, '--label', 'thm:exact'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['relevant_theorems'] == ['thm:exact']

    rc = main(['--root', str(tmp_path), 'audit-note', 'link-citation', '--paper-id', paper_id, '--citation-key', 'neal2011mcmc'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['relevant_citations'] == ['neal2011mcmc']

    rc = main(['--root', str(tmp_path), 'audit-note', 'remove', '--paper-id', paper_id, '--field', 'claimed_results', '--value', 'Source extraction preserves the target.'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['claimed_results'] == []

    rc = main(['--root', str(tmp_path), 'audit-note', 'append', '--paper-id', paper_id, '--field', 'claimed_results', '--value', 'Source extraction preserves the target.'])
    audit_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert audit_payload['technical_audit']['claimed_results'] == ['Source extraction preserves the target.']

    rc = main(['--root', str(tmp_path), 'evidence-context', '--paper-id', paper_id, '--label', 'eq:target'])
    evidence_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert evidence_payload['block_type'] == 'equation'
    assert evidence_payload['containing_section']['labels'] == ['sec:method', 'eq:target', 'thm:exact']
    assert evidence_payload['macro_usages'][0]['name'] == 'target'
    assert 'exp(-U' in evidence_payload['block']['raw_latex']

    rc = main(['--root', str(tmp_path), 'evidence-context', '--paper-id', paper_id, '--citation-key', 'neal2011mcmc'])
    citation_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert citation_payload['block_type'] == 'citation'
    assert citation_payload['citations'][0]['keys'] == ['neal2011mcmc']
    assert citation_payload['bibliography'][0]['key'] == 'neal2011mcmc'

    rc = main(['--root', str(tmp_path), 'review-show', '--paper-id', paper_id])
    review_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert review_payload['summary']['technical_audit']['objective'] == 'Preserve exact HMC correction while improving geometry.'
    assert review_payload['summary']['technical_audit']['relevant_sections'] == ['sec:method']

    rc = main(['--root', str(tmp_path), 'literature-audit-propose', '--paper-id', paper_id])
    proposal_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert proposal_payload['paper_claims'][0]['labels'] == ['thm:exact']
    assert proposal_payload['method_components']['relevant_equations'][0]['labels'] == ['eq:target']
    assert proposal_payload['graph_context']['available'] is False

    rc = main(['--root', str(tmp_path), 'literature-audit-show', '--paper-id', paper_id])
    shown_proposal = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown_proposal['limitations'][0].startswith('This proposal is generated')

    rc = main(['--root', str(tmp_path), 'literature-audit-approve', '--paper-id', paper_id])
    approved_proposal = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert approved_proposal['proposal_status'] == 'accepted'
    assert approved_proposal['technical_audit']['relevant_theorems'] == ['thm:exact']
    assert approved_proposal['technical_audit']['proposal_provenance'][0]['proposal_id'].endswith('source-v1')

    export_path = tmp_path / 'source_context.json'
    rc = main(['--root', str(tmp_path), 'export-context', '--output', str(export_path)])
    exported = json.loads(export_path.read_text())
    assert rc == 0
    assert exported['papers'][0]['technical_audit']['claimed_results'][0] == 'Source extraction preserves the target.'
    assert 'thm:exact' in exported['papers'][0]['technical_audit']['relevant_theorems']
    assert exported['papers'][0]['technical_audit']['relevant_equations'] == ['eq:target']
