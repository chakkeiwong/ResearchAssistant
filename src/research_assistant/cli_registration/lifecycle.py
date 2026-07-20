from __future__ import annotations

import argparse
from dataclasses import dataclass

from research_assistant.cli_registration.common import Handler, Subparsers


@dataclass(frozen=True, slots=True)
class LifecycleHandlers:
    init: Handler
    version: Handler
    config: Handler
    workspace: Handler
    backup: Handler
    doctor: Handler
    demo: Handler
    privacy: Handler
    release_report: Handler
    mcp: Handler
    repository_hygiene: Handler
    individual_git_release: Handler
    bounded_workflow: Handler
    performance: Handler
    parser_tool_matrix: Handler
    parser_benchmark_smoke: Handler
    arxiv_batch: Handler
    release_artifacts: Handler
    onboarding_report: Handler
    platform_status: Handler


def register_lifecycle_commands(sub: Subparsers, handlers: LifecycleHandlers) -> None:
    """Register local lifecycle, release, permission, and diagnostic commands."""
    init_cmd = sub.add_parser('init', help='Initialize an idempotent local research workspace')
    init_cmd.add_argument('--force', action='store_true', help='Regenerate safe default config without deleting data')
    init_cmd.set_defaults(func=handlers.init)

    version_cmd = sub.add_parser('version', help='Show package and workspace schema versions')
    version_cmd.set_defaults(func=handlers.version)

    config_cmd = sub.add_parser('config', help='Inspect and validate local release configuration')
    config_sub = config_cmd.add_subparsers(dest='config_action', required=True)
    config_show = config_sub.add_parser('show')
    config_show.set_defaults(func=handlers.config)
    config_set = config_sub.add_parser('set')
    config_set.add_argument('key')
    config_set.add_argument('value')
    config_set.set_defaults(func=handlers.config)
    config_validate = config_sub.add_parser('validate')
    config_validate.set_defaults(func=handlers.config)

    workspace_cmd = sub.add_parser('workspace', help='Validate, migrate, or repair a local workspace')
    workspace_sub = workspace_cmd.add_subparsers(dest='workspace_action', required=True)
    workspace_validate_cmd = workspace_sub.add_parser('validate')
    workspace_validate_cmd.set_defaults(func=handlers.workspace)
    workspace_migrate_cmd = workspace_sub.add_parser('migrate')
    workspace_migrate_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    workspace_migrate_cmd.set_defaults(func=handlers.workspace)
    workspace_repair_cmd = workspace_sub.add_parser('repair')
    workspace_repair_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    workspace_repair_cmd.set_defaults(func=handlers.workspace)
    workspace_merge_cmd = workspace_sub.add_parser('merge')
    workspace_merge_cmd.add_argument('--source', required=True)
    workspace_merge_cmd.add_argument('--target')
    workspace_merge_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    workspace_merge_cmd.add_argument('--apply', action='store_true')
    workspace_merge_cmd.add_argument('--confirm-merge', action='store_true')
    workspace_merge_cmd.set_defaults(func=handlers.workspace)
    workspace_rebuild_cmd = workspace_sub.add_parser('rebuild-derived')
    workspace_rebuild_cmd.set_defaults(func=handlers.workspace)

    backup_cmd = sub.add_parser('backup', help='Create, inspect, and dry-run restore local backups')
    backup_sub = backup_cmd.add_subparsers(dest='backup_action', required=True)
    backup_create = backup_sub.add_parser('create')
    backup_create.add_argument('--output')
    backup_create.set_defaults(func=handlers.backup)
    backup_inspect = backup_sub.add_parser('inspect')
    backup_inspect.add_argument('--path', required=True)
    backup_inspect.set_defaults(func=handlers.backup)
    backup_restore = backup_sub.add_parser('restore')
    backup_restore.add_argument('--path', required=True)
    backup_restore.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    backup_restore.add_argument('--target-root')
    backup_restore.add_argument('--confirm-restore', action='store_true')
    backup_restore.add_argument('--allow-overwrite', action='store_true')
    backup_restore.add_argument('--backup-current-first', action=argparse.BooleanOptionalAction, default=True)
    backup_restore.set_defaults(func=handlers.backup)

    doctor_cmd = sub.add_parser('doctor', help='Report individual-install readiness and optional tool status')
    doctor_cmd.add_argument('--matrix', action='store_true', help='Include full parser/tool workflow matrix')
    doctor_cmd.set_defaults(func=handlers.doctor)

    demo_cmd = sub.add_parser('demo', help='Create and run the isolated individual-release demo workflow')
    demo_sub = demo_cmd.add_subparsers(dest='demo_action', required=True)
    demo_setup_cmd = demo_sub.add_parser('setup')
    demo_setup_cmd.set_defaults(func=handlers.demo)
    demo_run_cmd = demo_sub.add_parser('run')
    demo_run_cmd.set_defaults(func=handlers.demo)
    demo_clean_cmd = demo_sub.add_parser('clean')
    demo_clean_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    demo_clean_cmd.add_argument('--force', action='store_true')
    demo_clean_cmd.set_defaults(func=handlers.demo)

    privacy_cmd = sub.add_parser('privacy', help='Show offline/provider privacy status')
    privacy_sub = privacy_cmd.add_subparsers(dest='privacy_action', required=True)
    privacy_status_cmd = privacy_sub.add_parser('status')
    privacy_status_cmd.set_defaults(func=handlers.privacy)

    release_report_cmd = sub.add_parser('release-report', help='Summarize individual release candidate readiness')
    release_report_cmd.add_argument('--output')
    release_report_cmd.set_defaults(func=handlers.release_report)

    mcp_cmd = sub.add_parser('mcp', help='Inspect local MCP permissions and bounded grants')
    mcp_sub = mcp_cmd.add_subparsers(dest='mcp_action', required=True)
    mcp_status = mcp_sub.add_parser('status')
    mcp_status.set_defaults(func=handlers.mcp)
    mcp_grant = mcp_sub.add_parser('grant')
    mcp_grant_sub = mcp_grant.add_subparsers(dest='grant_action', required=True)
    mcp_grant_arxiv = mcp_grant_sub.add_parser('arxiv-intake')
    mcp_grant_arxiv.add_argument('--plan-hash', required=True)
    mcp_grant_arxiv.add_argument('--operation', choices=['source_fetch', 'pdf_inbox_download', 'metadata_only'], default='source_fetch')
    mcp_grant_arxiv.add_argument('--destination', choices=['source', 'inbox'], default='source')
    mcp_grant_arxiv.add_argument('--max-papers', type=int, required=True)
    mcp_grant_arxiv.add_argument('--expires-hours', type=int, default=2)
    mcp_grant_arxiv.add_argument('--query')
    mcp_grant_arxiv.add_argument('--ids')
    mcp_grant_arxiv.add_argument('--skip-duplicates', action='store_true')
    mcp_grant_arxiv.set_defaults(func=handlers.mcp)
    mcp_grants = mcp_sub.add_parser('grants')
    mcp_grants_sub = mcp_grants.add_subparsers(dest='grants_action', required=True)
    mcp_grants_list = mcp_grants_sub.add_parser('list')
    mcp_grants_list.set_defaults(func=handlers.mcp)
    mcp_grants_show = mcp_grants_sub.add_parser('show')
    mcp_grants_show.add_argument('--grant-id', required=True)
    mcp_grants_show.set_defaults(func=handlers.mcp)
    mcp_audit = mcp_sub.add_parser('audit')
    mcp_audit_sub = mcp_audit.add_subparsers(dest='audit_action', required=True)
    mcp_audit_list = mcp_audit_sub.add_parser('list')
    mcp_audit_list.add_argument('--grant-id')
    mcp_audit_list.set_defaults(func=handlers.mcp)

    _register_repository_hygiene_commands(sub, handlers.repository_hygiene)
    _register_individual_git_release_commands(sub, handlers.individual_git_release)

    bounded_workflow_cmd = sub.add_parser('bounded-workflow', help='Write local timeout diagnostics for bounded workflow failures')
    bounded_sub = bounded_workflow_cmd.add_subparsers(dest='bounded_action', required=True)
    bounded_diagnostic = bounded_sub.add_parser('diagnostic')
    bounded_diagnostic.add_argument('--workflow', required=True)
    bounded_diagnostic.add_argument('--timeout-seconds', type=int, required=True)
    bounded_diagnostic.add_argument('--elapsed-seconds', type=float)
    bounded_diagnostic.set_defaults(func=handlers.bounded_workflow)

    performance_cmd = sub.add_parser('performance', help='Run bounded local performance smoke checks')
    performance_sub = performance_cmd.add_subparsers(dest='performance_action', required=True)
    performance_smoke_cmd = performance_sub.add_parser('smoke')
    performance_smoke_cmd.add_argument('--synthetic-count', type=int, default=25)
    performance_smoke_cmd.add_argument('--include-industrial-artifacts', action='store_true')
    performance_smoke_cmd.add_argument('--include-backup', action='store_true')
    performance_smoke_cmd.add_argument('--include-export', action='store_true')
    performance_smoke_cmd.add_argument('--timeout-seconds', type=int)
    performance_smoke_cmd.add_argument('--output')
    performance_smoke_cmd.set_defaults(func=handlers.performance)

    parser_matrix = sub.add_parser('parser-tool-matrix', help='Show optional parser/tool workflow readiness')
    parser_matrix.set_defaults(func=handlers.parser_tool_matrix)

    parser_benchmark = sub.add_parser('parser-benchmark-smoke', help='Run fixture-only parser benchmark smoke')
    parser_benchmark.set_defaults(func=handlers.parser_benchmark_smoke)


def register_release_utility_commands(sub: Subparsers, handlers: LifecycleHandlers) -> None:
    """Register intake and release utilities at their stable CLI position."""
    arxiv_batch = sub.add_parser('arxiv-batch', help='Plan and run bounded arXiv batch intake')
    arxiv_batch_sub = arxiv_batch.add_subparsers(dest='arxiv_batch_action', required=True)
    arxiv_batch_discover = arxiv_batch_sub.add_parser('discover')
    arxiv_batch_discover.add_argument('--query', required=True)
    arxiv_batch_discover.add_argument('--max-candidates', type=int, required=True)
    arxiv_batch_discover.add_argument('--timeout-seconds', type=int, default=30)
    arxiv_batch_discover.add_argument('--output-candidate-file', required=True)
    arxiv_batch_discover.set_defaults(func=handlers.arxiv_batch)
    arxiv_batch_plan = arxiv_batch_sub.add_parser('plan')
    arxiv_batch_plan.add_argument('--ids')
    arxiv_batch_plan.add_argument('--query')
    arxiv_batch_plan.add_argument('--candidate-file')
    arxiv_batch_plan.add_argument('--max-papers', type=int, required=True)
    arxiv_batch_plan.add_argument('--destination', choices=['source', 'inbox'], default='source')
    arxiv_batch_plan.add_argument('--operation', choices=['source_fetch', 'pdf_inbox_download', 'metadata_only'], default='source_fetch')
    arxiv_batch_plan.set_defaults(func=handlers.arxiv_batch)
    arxiv_batch_candidate = arxiv_batch_sub.add_parser('candidate-file')
    arxiv_batch_candidate_sub = arxiv_batch_candidate.add_subparsers(dest='candidate_file_action', required=True)
    arxiv_batch_candidate_inspect = arxiv_batch_candidate_sub.add_parser('inspect')
    arxiv_batch_candidate_inspect.add_argument('--path', required=True)
    arxiv_batch_candidate_inspect.set_defaults(func=handlers.arxiv_batch)
    arxiv_batch_run = arxiv_batch_sub.add_parser('run')
    arxiv_batch_run.add_argument('--grant-id', required=True)
    arxiv_batch_run.add_argument('--plan-hash', required=True)
    arxiv_batch_run.add_argument('--ids')
    arxiv_batch_run.add_argument('--candidate-file')
    arxiv_batch_run.add_argument('--plan-file')
    arxiv_batch_run.add_argument('--plan-file-sha256')
    arxiv_batch_run.set_defaults(func=handlers.arxiv_batch)
    arxiv_batch_pdf_run = arxiv_batch_sub.add_parser('pdf-run')
    arxiv_batch_pdf_run.add_argument('--grant-id', required=True)
    arxiv_batch_pdf_run.add_argument('--plan-hash', required=True)
    arxiv_batch_pdf_run.add_argument('--candidate-file', required=True)
    arxiv_batch_pdf_run.add_argument('--timeout-seconds', type=int, default=30)
    arxiv_batch_pdf_run.set_defaults(func=handlers.arxiv_batch)

    release_artifacts = sub.add_parser('release-artifacts', help='Inspect release artifact manifests')
    release_artifacts_sub = release_artifacts.add_subparsers(dest='release_artifacts_action', required=True)
    release_artifacts_manifest_cmd = release_artifacts_sub.add_parser('manifest')
    release_artifacts_manifest_cmd.add_argument('--dist-dir')
    release_artifacts_manifest_cmd.set_defaults(func=handlers.release_artifacts)

    onboarding_report_cmd = sub.add_parser('onboarding-report', help='Emit individual release onboarding checklist')
    onboarding_report_cmd.set_defaults(func=handlers.onboarding_report)

    platform_cmd = sub.add_parser('platform-status', help='Show local platform support status')
    platform_cmd.set_defaults(func=handlers.platform_status)


def _register_repository_hygiene_commands(sub: Subparsers, handler: Handler) -> None:
    repository_hygiene = sub.add_parser('repository-hygiene', help='Check whether a local workspace is safe to share through Git')
    repository_hygiene_sub = repository_hygiene.add_subparsers(dest='repository_hygiene_action', required=True)
    repository_hygiene_check_cmd = repository_hygiene_sub.add_parser('check')
    repository_hygiene_check_cmd.add_argument('--strict', action='store_true')
    repository_hygiene_check_cmd.set_defaults(func=handler)
    repository_hygiene_policy_cmd = repository_hygiene_sub.add_parser('policy')
    repository_hygiene_policy_cmd.set_defaults(func=handler)
    repository_hygiene_classify_cmd = repository_hygiene_sub.add_parser('classify')
    repository_hygiene_classify_cmd.add_argument('path')
    repository_hygiene_classify_cmd.set_defaults(func=handler)


def _register_individual_git_release_commands(sub: Subparsers, handler: Handler) -> None:
    individual_git_release_cmd = sub.add_parser('individual-git-release', help='Build the individual Git-sharing release gate')
    individual_git_release_sub = individual_git_release_cmd.add_subparsers(dest='individual_git_release_action', required=True)
    individual_git_release_gate_cmd = individual_git_release_sub.add_parser('gate-build')
    individual_git_release_gate_cmd.set_defaults(func=handler)
    individual_git_release_validation_record = individual_git_release_sub.add_parser('validation-record')
    individual_git_release_validation_record.add_argument('--validation-type', required=True)
    individual_git_release_validation_record.add_argument('--result', choices=['passed', 'warnings', 'blocked'], required=True)
    individual_git_release_validation_record.add_argument('--scope', default='local_machine')
    individual_git_release_validation_record.add_argument('--platform')
    individual_git_release_validation_record.add_argument('--python-version')
    individual_git_release_validation_record.add_argument('--install-method')
    individual_git_release_validation_record.add_argument('--command-summary')
    individual_git_release_validation_record.add_argument('--evidence-note')
    individual_git_release_validation_record.add_argument('--blocker', action='append')
    individual_git_release_validation_record.add_argument('--warning', action='append')
    individual_git_release_validation_record.set_defaults(func=handler)
    individual_git_release_validation_report = individual_git_release_sub.add_parser('validation-report')
    individual_git_release_validation_report.set_defaults(func=handler)
    individual_git_release_validation_substitutes = individual_git_release_sub.add_parser('validation-substitutes')
    individual_git_release_validation_substitutes.set_defaults(func=handler)
    individual_git_release_fixture = individual_git_release_sub.add_parser('fixture-rehearsal')
    individual_git_release_fixture.add_argument('--fixture-root')
    individual_git_release_fixture.add_argument('--include-blocker', action=argparse.BooleanOptionalAction, default=False)
    individual_git_release_fixture.add_argument('--apply-safe-subset', action=argparse.BooleanOptionalAction, default=True)
    individual_git_release_fixture.set_defaults(func=handler)
    individual_git_release_performance = individual_git_release_sub.add_parser('performance')
    individual_git_release_performance.add_argument('--tier', default='synthetic_git_100')
    individual_git_release_performance.add_argument('--synthetic-count', type=int, default=100)
    individual_git_release_performance.add_argument('--timeout-seconds', type=float)
    individual_git_release_performance.set_defaults(func=handler)
