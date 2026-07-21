from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_assistant.adapters.workspace_exports import export_paper_context
from research_assistant.cli_actions.survey import SurveyServices, execute_survey_action
from research_assistant.cli_actions.surveybench import SurveybenchServices, execute_surveybench_action
from research_assistant.cli_registration.lifecycle import (
    LifecycleHandlers,
    register_lifecycle_commands,
    register_release_utility_commands,
)
from research_assistant.cli_registration.industrial import IndustrialHandlers, register_industrial_commands
from research_assistant.cli_registration.library import LibraryHandlers, register_library_commands
from research_assistant.cli_registration.research import (
    ResearchHandlers,
    SourceInspectionHandlers,
    register_research_commands,
)
from research_assistant.cli_registration.survey import register_survey_commands
from research_assistant.cli_registration.surveybench import register_surveybench_commands
from research_assistant.benchmarks.local_manifest import validate_local_manifest
from research_assistant.benchmarks.replay import (
    build_replay_transcript,
    replay_call,
    score_replay_submission,
    validate_replay_fixture_interface,
)
from research_assistant.benchmarks.restricted_trial import (
    build_launch_approval_packet,
    build_launch_enforcement_preflight,
    build_restricted_launcher_dry_run,
    build_subject_binding_preflight,
    create_restricted_workspace,
    validate_launch_approval_packet,
)
from research_assistant.benchmarks.surveybench import score_survey_task
from research_assistant.benchmarks.surveybench_helpers import (
    scan_subject_helper_payload,
    surveybench_cluster_hints,
    surveybench_launch_record_template,
    surveybench_next_action,
    surveybench_packet_compose,
    surveybench_packet_template,
    surveybench_ready_for_prose,
)
from research_assistant.benchmarks.survey_quality import score_survey_prose
from research_assistant.adapters.mcp_permissions import (
    create_arxiv_batch_grant,
    list_mcp_audit_events,
    list_mcp_grants,
    mcp_permissions_status,
    read_mcp_grant,
)
from research_assistant.adapters.review_write import apply_review_write, cleanup_expired_proposals, propose_review_status, review_write_status
from research_assistant.analyze.literature_audit import approve_literature_audit, propose_literature_audit, show_literature_audit
from research_assistant.config import get_paths
from research_assistant.individual_release import (
    create_backup,
    demo_clean,
    demo_run,
    demo_setup,
    doctor,
    init_workspace,
    inspect_backup,
    parser_benchmark_smoke,
    parser_tool_matrix,
    performance_smoke,
    platform_status,
    privacy_status,
    record_timeout_diagnostic,
    release_artifacts_manifest,
    release_report,
    restore_backup,
    set_config_value,
    show_config,
    validate_config,
    version_payload,
    workspace_migrate,
    workspace_repair,
    workspace_validate,
)
from research_assistant.release_evidence import validate_release_artifact_manifest
from research_assistant.individual_git_release import (
    classify_shareable_path,
    fixture_rehearsal,
    individual_git_release_gate,
    load_shareable_workspace_policy,
    record_local_validations,
    representative_workspace_performance,
    repository_hygiene_check,
    validation_record,
    validation_report,
    workspace_merge,
    workspace_rebuild_derived,
)
from research_assistant.industrial.full_scale import (
    build_execution_readiness,
    build_phase_registry,
    build_usefulness_metrics,
    get_phase_contract,
    list_phase_contracts,
    show_phase_registry,
)
from research_assistant.industrial.release import (
    build_external_validation_report,
    build_industrial_release_gate,
    build_publication_check,
    build_release_definition,
    get_release_phase,
    list_release_phases,
    show_industrial_release_artifact,
    show_release_definition,
)
from research_assistant.industrial.platform import (
    IMPLEMENTATION_LINK_RELATIONSHIPS,
    add_derivation_comment,
    add_derivation_notation,
    artifact_paths,
    build_artifact_index,
    build_governance_record,
    build_graph_report,
    build_readiness_report,
    build_traceability_report,
    check_synthesis_policy,
    create_collaboration_workspace,
    create_benchmark_manifest,
    create_department_sop,
    create_derivation,
    create_experiment,
    create_job,
    create_model_policy,
    create_operations_policy,
    dashboard_export,
    enrich_graph_report,
    export_tool_contract,
    link_derivation_steps,
    link_claim_to_experiment,
    list_experiment_checklists,
    list_review_metadata,
    propose_synthesis,
    record_experiment_run,
    query_artifact_index,
    run_benchmark_manifest,
    set_review_metadata,
    show_artifact_index,
    show_benchmark_manifest,
    show_collaboration_workspace,
    show_department_sop,
    show_derivation,
    show_experiment,
    show_experiment_checklist,
    show_governance_record,
    show_graph_report,
    show_job,
    show_model_policy,
    show_operations_policy,
    show_readiness_report,
    show_review_metadata,
    show_synthesis,
    show_tool_contract,
    show_traceability_report,
    update_derivation,
    update_collaboration_workspace,
    validate_industrial_artifacts,
)
from research_assistant.ingest.source_manifest import canonical_paper_id, store_raw_source
from research_assistant.ingest.arxiv_batch import discover_arxiv_query_candidates, load_arxiv_candidate_file, plan_arxiv_batch_intake, run_arxiv_batch_intake
from research_assistant.ingest.pdf_batch_policy import run_pdf_batch_download
from research_assistant.ingest.pdf_extract import extract_pdf_text
from research_assistant.ingest.normalize_text import normalize_extracted_text
from research_assistant.ingest.metadata_resolve import resolve_metadata
from research_assistant.ingest.identity_validate import validate_identity
from research_assistant.ingest.filename_parse import parse_paper_filename
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.summarize.draft_summary import build_draft_summary
from research_assistant.storage.file_store import FileStore
from research_assistant.query import citation_graph
from research_assistant.query.paper_lookup import find_paper, get_paper_summary, claim_support_audit
from research_assistant.query.review import list_review_items, mark_review_status, show_review_item
from research_assistant.query.audit_notes import append_audit_note, link_audit_citation_key, link_audit_source_label, remove_audit_note, set_audit_note, show_audit_notes
from research_assistant.query.discovery import discover_papers_with_status
from research_assistant.query.downloads import download_to_inbox, list_download_proposals, persist_download_proposal, propose_download, show_download_proposal
from research_assistant.query.graph_inbox import propose_graph_node_download
from research_assistant.query.citation_graph import papers_cited_by, papers_citing
from research_assistant.query.citation_cache import build_citation_graph, export_citation_graph, show_citation_graph
from research_assistant.ingest.parser_orchestrator import parse_with_all, reconcile_parsed_documents
from research_assistant.ingest.parser_preflight import preflight_all
from research_assistant.schemas.artifact import stable_id
from research_assistant.schemas.domain_templates import get_domain_template, list_domain_templates
from research_assistant.source.arxiv_source import fetch_arxiv_structured_source
from research_assistant.source.structured_source import source_record_path
from research_assistant.source.evidence_context import evidence_context_for_citation, evidence_context_for_label
from research_assistant.survey.anchors import build_source_anchor_packet
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.build import build_survey_evidence_packet
from research_assistant.survey.claim_review import import_reviewed_claims
from research_assistant.survey.coverage_ledgers import compose_coverage_ledgers
from research_assistant.survey.hostile_review import run_hostile_review_gate
from research_assistant.survey.human_attestation import (
    prepare_human_review_packet,
    render_human_review_materials,
    validate_human_attestation,
)
from research_assistant.survey.omission_review import import_reviewed_omissions
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.packet import compose_public_source_evidence_packet
from research_assistant.survey.reviewed_merge import merge_reviewed_evidence
from research_assistant.survey.reviewed_packet import compose_reviewed_final_packet
from research_assistant.survey.source_safety_review import import_reviewed_source_safety
from research_assistant.survey.qualitative_assessment import build_assessment, write_assessment
from research_assistant.survey.workflow_blocker_review import import_reviewed_workflow_blockers
from research_assistant.survey.mission_state import MissionStateError


SURVEY_WRITE_OUTPUT_FIELDS = {
    "build": ("out",),
    "anchors": ("out",),
    "packet": ("out",),
    "coverage-ledgers": ("out",),
    "compose-reviewed-final-packet": ("out",),
    "hostile-review": ("out",),
    "run-public-source-workflow": ("out",),
    "import-claim-review": ("out",),
    "import-source-safety-review": ("out",),
    "import-omission-review": ("out",),
    "import-workflow-blocker-review": ("out",),
    "merge-reviewed-evidence": ("out",),
    "prepare-human-review": ("out",),
    "render-human-review": ("out",),
    "validate-human-attestation": ("out",),
    "qualitative-assessment": ("out",),
}


def cmd_ingest(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    source = args.pdf or (f'arxiv:{args.arxiv_id}' if args.arxiv_id else args.query)
    if not source:
        raise SystemExit('ingest requires --pdf, --query, or --arxiv-id')
    paper_id = canonical_paper_id(source)
    text = ''
    filename_hints = None
    parser_hints = None
    structured_source = None
    if args.arxiv_id:
        structured_source = fetch_arxiv_structured_source(args.arxiv_id, root=paths.root, paper_id=paper_id)
    if args.pdf:
        raw_path = store_raw_source(args.pdf, paths.papers_raw, paper_id)
        text = normalize_extracted_text(extract_pdf_text(raw_path))
        paths.papers_extracted.mkdir(parents=True, exist_ok=True)
        (paths.papers_extracted / f'{paper_id}.txt').write_text(text)
        filename_hints = parse_paper_filename(args.pdf).__dict__
        parsed_outputs = parse_with_all(raw_path)
        reconciled = reconcile_parsed_documents(parsed_outputs)
        parser_hints = {
            'consensus_title': reconciled.consensus_title,
            'consensus_authors': reconciled.consensus_authors,
            'consensus_abstract': reconciled.consensus_abstract,
            'consensus_section_headings': reconciled.consensus_section_headings,
            'parse_confidence': reconciled.parse_confidence,
            'requires_manual_review': reconciled.requires_manual_review,
            'parser_agreement': reconciled.parser_agreement,
            'disagreements': reconciled.disagreements,
            'parser_outputs': reconciled.parser_outputs,
        }
    metadata = resolve_metadata(args.query or source, arxiv_id=args.arxiv_id, extracted_text=text, filename_hints=filename_hints, parser_hints=parser_hints)
    if structured_source is not None:
        metadata['structured_source'] = {
            'paper_id': structured_source.paper_id,
            'source_type': structured_source.source_type,
            'status': structured_source.status,
            'primary_for_audit': structured_source.primary_for_audit,
            'record_path': str(source_record_path(paths.papers_source, paper_id)),
        }
        metadata.setdefault('source_statuses', []).extend(structured_source.provenance.get('source_statuses', []))
    metadata['identity_validation'] = validate_identity(metadata)
    summary = build_draft_summary(paper_id, metadata, text)
    store = FileStore(paths.local_research)
    store.write_json(paths.metadata / f'{paper_id}.json', metadata)
    store.write_json(paths.summaries / f'{paper_id}.json', summary.to_dict())
    print(paper_id)
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    for rec in find_paper(args.query, root=paths.root, review_status=args.review_status, author=args.author, year=args.year):
        print(f"{rec['paper_id']}\t{rec['year']}\t{rec['review_status']}\t{rec['title']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    result = get_paper_summary(args.paper_id, root=paths.root)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_export_context(args: argparse.Namespace) -> int:
    out = export_paper_context(
        Path(args.output) if args.output else None,
        root=Path(args.root) if args.root else None,
        review_status=args.review_status,
    )
    print(out)
    return 0


def cmd_review_list(args: argparse.Namespace) -> int:
    import json
    rows = list_review_items(root=Path(args.root) if args.root else None, status=args.status)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    for row in rows:
        print(f"{row['paper_id']}\t{row['year']}\t{row['review_status']}\t{row['title']}")
    return 0


def cmd_review_show(args: argparse.Namespace) -> int:
    import json
    payload = show_review_item(args.paper_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_review_mark(args: argparse.Namespace) -> int:
    import json
    payload = mark_review_status(args.paper_id, args.status, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_link_add(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    link = LinkRecord(
        id=stable_id('link', args.paper_id, args.source_ref or '', args.target, args.relationship),
        paper_id=args.paper_id,
        target_type=args.target_type,
        target=args.target,
        relationship=args.relationship,
        source_type=args.source_type,
        source_ref=args.source_ref,
        target_ref=args.target_ref,
        evidence_refs=[],
        limitations=['Link requires review before it is treated as an implementation claim.'],
        review_status='requires_human_review' if args.relationship in IMPLEMENTATION_LINK_RELATIONSHIPS else 'draft',
    )
    FileStore(paths.local_research).write_json(paths.links / f'{link.id}.json', link.to_dict())
    print(link.id)
    return 0


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _display_cli_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd()))
    except ValueError:
        return f"redacted:{resolved.name}"


def cmd_init(args: argparse.Namespace) -> int:
    return _print_json(init_workspace(root=Path(args.root) if args.root else None, force=args.force))


def cmd_version(args: argparse.Namespace) -> int:
    return _print_json(version_payload())


def cmd_config(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.config_action == 'show':
        return _print_json(show_config(root=root))
    if args.config_action == 'set':
        return _print_json(set_config_value(args.key, args.value, root=root))
    if args.config_action == 'validate':
        return _print_json(validate_config(root=root))
    raise SystemExit(f'unknown config action {args.config_action}')


def cmd_workspace(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.workspace_action == 'validate':
        return _print_json(workspace_validate(root=root))
    if args.workspace_action == 'migrate':
        return _print_json(workspace_migrate(root=root, dry_run=args.dry_run))
    if args.workspace_action == 'repair':
        return _print_json(workspace_repair(root=root, dry_run=args.dry_run))
    if args.workspace_action == 'merge':
        return _print_json(workspace_merge(
            source=Path(args.source),
            target=Path(args.target) if args.target else (root or Path.cwd()),
            dry_run=False if args.apply else args.dry_run,
            apply=args.apply,
            confirm_merge=args.confirm_merge,
        ))
    if args.workspace_action == 'rebuild-derived':
        return _print_json(workspace_rebuild_derived(root=root))
    raise SystemExit(f'unknown workspace action {args.workspace_action}')


def cmd_backup(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.backup_action == 'create':
        return _print_json(create_backup(root=root, output=Path(args.output) if args.output else None))
    if args.backup_action == 'inspect':
        return _print_json(inspect_backup(Path(args.path)))
    if args.backup_action == 'restore':
        return _print_json(restore_backup(
            Path(args.path),
            root=Path(args.target_root) if args.target_root else root,
            dry_run=args.dry_run,
            confirm_restore=args.confirm_restore,
            allow_overwrite=args.allow_overwrite,
            backup_current_first=args.backup_current_first,
        ))
    raise SystemExit(f'unknown backup action {args.backup_action}')


def cmd_doctor(args: argparse.Namespace) -> int:
    return _print_json(doctor(root=Path(args.root) if args.root else None, include_matrix=args.matrix))


def cmd_demo(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.demo_action == 'setup':
        return _print_json(demo_setup(root=root))
    if args.demo_action == 'run':
        return _print_json(demo_run(root=root))
    if args.demo_action == 'clean':
        return _print_json(demo_clean(root=root, dry_run=args.dry_run, force=args.force))
    raise SystemExit(f'unknown demo action {args.demo_action}')


def cmd_privacy(args: argparse.Namespace) -> int:
    if args.privacy_action == 'status':
        return _print_json(privacy_status(root=Path(args.root) if args.root else None))
    raise SystemExit(f'unknown privacy action {args.privacy_action}')


def cmd_release_report(args: argparse.Namespace) -> int:
    return _print_json(release_report(
        root=Path(args.root) if args.root else None,
        output=Path(args.output) if args.output else None,
    ))


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def cmd_mcp(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.mcp_action == "status":
        return _print_json(mcp_permissions_status(root=root))
    if args.mcp_action == "grant":
        if args.grant_action == "arxiv-intake":
            return _print_json(create_arxiv_batch_grant(
                plan_hash=args.plan_hash,
                operation=args.operation,
                destination=args.destination,
                max_papers=args.max_papers,
                expires_hours=args.expires_hours,
                root=root,
                query=args.query,
                arxiv_ids=_split_csv(args.ids),
                duplicate_policy="skip_existing" if args.skip_duplicates else "report_duplicates",
            ))
        raise SystemExit(f"unknown mcp grant action {args.grant_action}")
    if args.mcp_action == "grants":
        if args.grants_action == "list":
            return _print_json(list_mcp_grants(root=root))
        if args.grants_action == "show":
            return _print_json(read_mcp_grant(args.grant_id, root=root))
        raise SystemExit(f"unknown mcp grants action {args.grants_action}")
    if args.mcp_action == "audit":
        if args.audit_action == "list":
            return _print_json(list_mcp_audit_events(root=root, grant_id=args.grant_id))
        raise SystemExit(f"unknown mcp audit action {args.audit_action}")
    raise SystemExit(f"unknown mcp action {args.mcp_action}")


def cmd_arxiv_batch(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.arxiv_batch_action == "discover":
        return _print_json(discover_arxiv_query_candidates(
            query=args.query,
            max_candidates=args.max_candidates,
            output_candidate_file=Path(args.output_candidate_file),
            timeout_seconds=args.timeout_seconds,
            root=root,
        ))
    if args.arxiv_batch_action == "plan":
        return _print_json(plan_arxiv_batch_intake(
            query=args.query,
            arxiv_ids=_split_csv(args.ids),
            max_papers=args.max_papers,
            candidate_file=Path(args.candidate_file) if args.candidate_file else None,
            destination=args.destination,
            operation=args.operation,
            root=root,
        ))
    if args.arxiv_batch_action == "candidate-file":
        if args.candidate_file_action == "inspect":
            return _print_json(load_arxiv_candidate_file(Path(args.path)))
        raise SystemExit(f"unknown arxiv-batch candidate-file action {args.candidate_file_action}")
    if args.arxiv_batch_action == "run":
        return _print_json(run_arxiv_batch_intake(
            grant_id=args.grant_id,
            plan_hash=args.plan_hash,
            arxiv_ids=_split_csv(args.ids),
            candidate_file=Path(args.candidate_file) if args.candidate_file else None,
            plan_file=Path(args.plan_file) if args.plan_file else None,
            plan_file_sha256=args.plan_file_sha256,
            root=root,
        ))
    if args.arxiv_batch_action == "pdf-run":
        candidate_result = load_arxiv_candidate_file(Path(args.candidate_file))
        if candidate_result["status"] != "ok":
            return _print_json({
                "status": "blocked",
                "grant_id": args.grant_id,
                "plan_hash": args.plan_hash,
                "issues": candidate_result["issues"],
            })
        return _print_json(run_pdf_batch_download(
            grant_id=args.grant_id,
            plan_hash=args.plan_hash,
            candidates=candidate_result["payload"]["candidates"],
            candidate_file=Path(args.candidate_file),
            root=root,
            timeout_seconds=args.timeout_seconds,
        ))
    raise SystemExit(f"unknown arxiv-batch action {args.arxiv_batch_action}")


def cmd_review_write(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.review_write_action == "status":
        return _print_json(review_write_status(root=root))
    if args.review_write_action == "propose-status":
        return _print_json(propose_review_status(
            paper_id=args.paper_id,
            status=args.status,
            root=root,
            expires_minutes=args.expires_minutes,
        ))
    if args.review_write_action == "apply":
        return _print_json(apply_review_write(confirmation_id=args.confirmation_id, root=root))
    if args.review_write_action == "cleanup-expired":
        return _print_json(cleanup_expired_proposals(root=root, apply=args.apply))
    raise SystemExit(f"unknown review-write action {args.review_write_action}")


def cmd_repository_hygiene(args: argparse.Namespace) -> int:
    if args.repository_hygiene_action == 'check':
        return _print_json(repository_hygiene_check(root=Path(args.root) if args.root else None, strict=args.strict))
    if args.repository_hygiene_action == 'policy':
        return _print_json(load_shareable_workspace_policy())
    if args.repository_hygiene_action == 'classify':
        return _print_json(classify_shareable_path(args.path))
    raise SystemExit(f'unknown repository-hygiene action {args.repository_hygiene_action}')


def cmd_individual_git_release(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.individual_git_release_action == 'gate-build':
        return _print_json(individual_git_release_gate(root=root))
    if args.individual_git_release_action == 'validation-record':
        return _print_json(validation_record(
            validation_type=args.validation_type,
            result=args.result,
            platform=args.platform or '',
            python_version=args.python_version or '',
            install_method=args.install_method or '',
            command_summary=args.command_summary or '',
            scope=args.scope,
            evidence_note=args.evidence_note or '',
            blocker=args.blocker or [],
            warning=args.warning or [],
            root=root,
        ))
    if args.individual_git_release_action == 'validation-report':
        return _print_json(validation_report(root=root))
    if args.individual_git_release_action == 'validation-local':
        return _print_json(record_local_validations(root=root))
    if args.individual_git_release_action == 'fixture-rehearsal':
        return _print_json(fixture_rehearsal(
            root=root,
            fixture_root=Path(args.fixture_root) if args.fixture_root else None,
            include_blocker=args.include_blocker,
            apply_safe_subset=args.apply_safe_subset,
        ))
    if args.individual_git_release_action == 'performance':
        return _print_json(representative_workspace_performance(
            root=root,
            tier=args.tier,
            synthetic_count=args.synthetic_count,
            timeout_seconds=args.timeout_seconds,
        ))
    raise SystemExit(f'unknown individual-git-release action {args.individual_git_release_action}')


def cmd_bounded_workflow(args: argparse.Namespace) -> int:
    if args.bounded_action == 'diagnostic':
        return _print_json(record_timeout_diagnostic(
            workflow=args.workflow,
            timeout_seconds=args.timeout_seconds,
            elapsed_seconds=args.elapsed_seconds,
            root=Path(args.root) if args.root else None,
        ))
    raise SystemExit(f'unknown bounded-workflow action {args.bounded_action}')


def cmd_performance(args: argparse.Namespace) -> int:
    if args.performance_action == 'smoke':
        return _print_json(performance_smoke(
            root=Path(args.root) if args.root else None,
            synthetic_count=args.synthetic_count,
            include_industrial_artifacts=args.include_industrial_artifacts,
            include_backup=args.include_backup,
            include_export=args.include_export,
            timeout_seconds=args.timeout_seconds,
            output=Path(args.output) if args.output else None,
        ))
    raise SystemExit(f'unknown performance action {args.performance_action}')


def cmd_parser_tool_matrix(args: argparse.Namespace) -> int:
    return _print_json(parser_tool_matrix(root=Path(args.root) if args.root else None))


def cmd_parser_benchmark_smoke(args: argparse.Namespace) -> int:
    return _print_json(parser_benchmark_smoke(root=Path(args.root) if args.root else None))


def cmd_survey(args: argparse.Namespace) -> int:
    try:
        _guard_survey_write_paths(args)
    except MissionStateError as exc:
        _print_json({
            "schema_version": "ra-survey-protected-output-result-v1",
            "status": "blocked",
            "blocked_reason": exc.code,
            "next_required_actions": [str(exc)],
            "what_is_not_concluded": [
                "literature completeness",
                "technical claim support",
                "final prose readiness",
                "product readiness",
                "scientific correctness",
            ],
        })
        return 1
    return execute_survey_action(
        args,
        SurveyServices(
            print_json=_print_json,
            human_attestation_blocked=_human_attestation_blocked,
            build_survey_evidence_packet=build_survey_evidence_packet,
            build_source_anchor_packet=build_source_anchor_packet,
            compose_public_source_evidence_packet=compose_public_source_evidence_packet,
            compose_coverage_ledgers=compose_coverage_ledgers,
            compose_reviewed_final_packet=compose_reviewed_final_packet,
            run_hostile_review_gate=run_hostile_review_gate,
            run_public_source_workflow=run_public_source_workflow,
            import_reviewed_claims=import_reviewed_claims,
            import_reviewed_source_safety=import_reviewed_source_safety,
            import_reviewed_omissions=import_reviewed_omissions,
            import_reviewed_workflow_blockers=import_reviewed_workflow_blockers,
            merge_reviewed_evidence=merge_reviewed_evidence,
            prepare_human_review_packet=prepare_human_review_packet,
            render_human_review_materials=render_human_review_materials,
            validate_human_attestation=validate_human_attestation,
            build_assessment=build_assessment,
            write_assessment=write_assessment,
        ),
    )


def _guard_survey_write_paths(args: argparse.Namespace) -> None:
    fields = SURVEY_WRITE_OUTPUT_FIELDS.get(args.survey_action)
    if fields is None:
        raise MissionStateError(
            "unclassified_survey_writer",
            f"survey action has no protected-output classification: {args.survey_action}",
        )
    for field in fields:
        value = getattr(args, field, None)
        if value:
            assert_public_write_path_allowed(Path(value))
    if args.survey_action == "run-public-source-workflow":
        metadata_dir = getattr(args, "metadata_dir", None)
        if metadata_dir:
            assert_public_write_path_allowed(Path(metadata_dir))


def _human_attestation_blocked(exc: MissionStateError) -> dict[str, Any]:
    return {
        "schema_version": "ra-survey-human-attestation-blocked-result-v1",
        "status": "blocked",
        "blocked_reason": exc.code,
        "next_required_actions": [str(exc)],
        "ready_for_review_import": False,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": [
            "human identity proof",
            "review quality",
            "decision correctness",
            "claim truth",
            "literature completeness",
            "scientific correctness",
        ],
    }


def cmd_surveybench(args: argparse.Namespace) -> int:
    return execute_surveybench_action(
        args,
        SurveybenchServices(
            print_json=_print_json,
            display_path=_display_cli_path,
            score_survey_task=score_survey_task,
            validate_local_manifest=validate_local_manifest,
            replay_call=replay_call,
            validate_replay_fixture_interface=validate_replay_fixture_interface,
            build_replay_transcript=build_replay_transcript,
            score_replay_submission=score_replay_submission,
            score_survey_prose=score_survey_prose,
            create_restricted_workspace=create_restricted_workspace,
            build_restricted_launcher_dry_run=build_restricted_launcher_dry_run,
            build_subject_binding_preflight=build_subject_binding_preflight,
            build_launch_approval_packet=build_launch_approval_packet,
            validate_launch_approval_packet=validate_launch_approval_packet,
            build_launch_enforcement_preflight=build_launch_enforcement_preflight,
            surveybench_next_action=surveybench_next_action,
            surveybench_packet_template=surveybench_packet_template,
            surveybench_packet_compose=surveybench_packet_compose,
            surveybench_cluster_hints=surveybench_cluster_hints,
            surveybench_ready_for_prose=surveybench_ready_for_prose,
            surveybench_launch_record_template=surveybench_launch_record_template,
            scan_subject_helper_payload=scan_subject_helper_payload,
        ),
    )


def cmd_release_artifacts(args: argparse.Namespace) -> int:
    if args.release_artifacts_action == 'manifest':
        return _print_json(release_artifacts_manifest(
            dist_dir=Path(args.dist_dir) if args.dist_dir else None,
        ))
    if args.release_artifacts_action == 'validate':
        return _print_json(validate_release_artifact_manifest(
            Path(args.release_root) if args.release_root else Path.cwd(),
        ))
    raise SystemExit(f'unknown release-artifacts action {args.release_artifacts_action}')


def cmd_platform_status(args: argparse.Namespace) -> int:
    return _print_json(platform_status(root=Path(args.root) if args.root else None))


def cmd_artifact_paths(args: argparse.Namespace) -> int:
    return _print_json(artifact_paths(root=Path(args.root) if args.root else None))


def cmd_industrial_validate(args: argparse.Namespace) -> int:
    return _print_json(validate_industrial_artifacts(root=Path(args.root) if args.root else None))


def cmd_domain_templates(args: argparse.Namespace) -> int:
    if args.template_action == 'list':
        return _print_json(list_domain_templates())
    if args.template_action == 'show':
        return _print_json(get_domain_template(args.template_id))
    raise SystemExit(f'unknown domain-template action {args.template_action}')


def cmd_derivation(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.derivation_action == 'create':
        return _print_json(create_derivation(args.paper_id, title=args.title, template_id=args.template_id, root=root))
    if args.derivation_action == 'show':
        return _print_json(show_derivation(args.artifact_id, root=root))
    if args.derivation_action == 'append':
        return _print_json(update_derivation(args.artifact_id, args.field, args.value, root=root))
    if args.derivation_action == 'notation':
        return _print_json(add_derivation_notation(args.artifact_id, args.symbol, args.meaning, root=root))
    if args.derivation_action == 'link-steps':
        return _print_json(link_derivation_steps(args.artifact_id, args.step_id, args.depends_on, root=root))
    if args.derivation_action == 'comment':
        return _print_json(add_derivation_comment(args.artifact_id, args.target_id, args.comment, reviewer=args.reviewer or '', root=root))
    raise SystemExit(f'unknown derivation action {args.derivation_action}')


def cmd_experiment(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.experiment_action == 'checklists':
        return _print_json(list_experiment_checklists())
    if args.experiment_action == 'checklist-show':
        return _print_json(show_experiment_checklist(args.template_id))
    if args.experiment_action == 'create':
        return _print_json(create_experiment(args.paper_id, claim_id=args.claim_id, checklist_id=args.checklist_id, root=root))
    if args.experiment_action == 'show':
        return _print_json(show_experiment(args.artifact_id, root=root))
    if args.experiment_action == 'link-claim':
        return _print_json(link_claim_to_experiment(args.paper_id, claim_id=args.claim_id, experiment_id=args.experiment_id, root=root))
    if args.experiment_action == 'record-run':
        return _print_json(record_experiment_run(
            args.artifact_id,
            run_label=args.run_label,
            seed=args.seed,
            environment=args.environment,
            diagnostics=args.diagnostic or [],
            result_summary=args.result_summary or '',
            acceptance_status=args.acceptance_status,
            dataset_hash=args.dataset_hash or '',
            model_hash=args.model_hash or '',
            root=root,
        ))
    raise SystemExit(f'unknown experiment action {args.experiment_action}')


def cmd_graph_report(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.graph_report_action == 'build':
        return _print_json(build_graph_report(args.paper_id, root=root))
    if args.graph_report_action == 'show':
        return _print_json(show_graph_report(args.artifact_id, root=root))
    if args.graph_report_action == 'enrich':
        return _print_json(enrich_graph_report(args.artifact_id, root=root))
    raise SystemExit(f'unknown graph-report action {args.graph_report_action}')


def cmd_review_meta(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.review_meta_action == 'show':
        return _print_json(show_review_metadata(args.paper_id, root=root))
    if args.review_meta_action == 'set':
        return _print_json(set_review_metadata(args.paper_id, field=args.field, value=args.value, root=root))
    if args.review_meta_action == 'list':
        return _print_json(list_review_metadata(root=root))
    raise SystemExit(f'unknown review-meta action {args.review_meta_action}')


def cmd_benchmark_manifest(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.benchmark_action == 'create':
        return _print_json(create_benchmark_manifest(args.manifest_id, family=args.family, fixture_paths=args.fixture, root=root))
    if args.benchmark_action == 'show':
        return _print_json(show_benchmark_manifest(args.manifest_id, root=root))
    if args.benchmark_action == 'run':
        return _print_json(run_benchmark_manifest(args.manifest_id, root=root))
    raise SystemExit(f'unknown benchmark-manifest action {args.benchmark_action}')


def cmd_synthesis(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.synthesis_action == 'propose':
        return _print_json(propose_synthesis(args.paper_id, kind=args.kind, root=root))
    if args.synthesis_action == 'show':
        return _print_json(show_synthesis(args.artifact_id, root=root))
    raise SystemExit(f'unknown synthesis action {args.synthesis_action}')


def cmd_governance(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.governance_action == 'build':
        return _print_json(build_governance_record(args.paper_id, root=root))
    if args.governance_action == 'show':
        return _print_json(show_governance_record(args.artifact_id, root=root))
    raise SystemExit(f'unknown governance action {args.governance_action}')


def cmd_job(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.job_action == 'create':
        return _print_json(create_job(job_type=args.job_type, paper_id=args.paper_id, root=root))
    if args.job_action == 'show':
        return _print_json(show_job(args.artifact_id, root=root))
    raise SystemExit(f'unknown job action {args.job_action}')


def cmd_dashboard_export(args: argparse.Namespace) -> int:
    output = dashboard_export(Path(args.output) if args.output else None, root=Path(args.root) if args.root else None)
    print(output)
    return 0


def cmd_traceability(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.traceability_action == 'build':
        return _print_json(build_traceability_report(args.paper_id, root=root))
    if args.traceability_action == 'show':
        return _print_json(show_traceability_report(args.artifact_id, root=root))
    raise SystemExit(f'unknown traceability action {args.traceability_action}')


def cmd_model_policy(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.model_policy_action == 'create':
        return _print_json(create_model_policy(args.policy_id, root=root))
    if args.model_policy_action == 'show':
        return _print_json(show_model_policy(args.policy_id, root=root))
    if args.model_policy_action == 'check-synthesis':
        return _print_json(check_synthesis_policy(args.policy_id, root=root))
    raise SystemExit(f'unknown model-policy action {args.model_policy_action}')


def cmd_collaboration(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.collaboration_action == 'create':
        return _print_json(create_collaboration_workspace(args.workspace_id, root=root))
    if args.collaboration_action == 'show':
        return _print_json(show_collaboration_workspace(args.workspace_id, root=root))
    if args.collaboration_action == 'update':
        return _print_json(update_collaboration_workspace(args.workspace_id, action=args.action, value=args.value, target=args.target or '', root=root))
    raise SystemExit(f'unknown collaboration action {args.collaboration_action}')


def cmd_artifact_index(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.artifact_index_action == 'build':
        return _print_json(build_artifact_index(args.index_id, root=root))
    if args.artifact_index_action == 'show':
        return _print_json(show_artifact_index(args.index_id, root=root))
    if args.artifact_index_action == 'query':
        return _print_json(query_artifact_index(args.index_id, family=args.family, paper_id=args.paper_id, root=root))
    raise SystemExit(f'unknown artifact-index action {args.artifact_index_action}')


def cmd_industrial_readiness(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.readiness_action == 'build':
        return _print_json(build_readiness_report(args.report_id, root=root))
    if args.readiness_action == 'show':
        return _print_json(show_readiness_report(args.report_id, root=root))
    raise SystemExit(f'unknown industrial-readiness action {args.readiness_action}')


def cmd_full_scale_plan(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.full_scale_action == 'phases':
        return _print_json(list_phase_contracts())
    if args.full_scale_action == 'phase-show':
        return _print_json(get_phase_contract(args.phase_id))
    if args.full_scale_action == 'registry-build':
        return _print_json(build_phase_registry(root=root))
    if args.full_scale_action == 'registry-show':
        return _print_json(show_phase_registry(root=root))
    if args.full_scale_action == 'usefulness-build':
        return _print_json(build_usefulness_metrics(root=root))
    if args.full_scale_action == 'readiness-build':
        return _print_json(build_execution_readiness(root=root))
    raise SystemExit(f'unknown full-scale-plan action {args.full_scale_action}')


def cmd_industrial_release(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.industrial_release_action == 'phases':
        return _print_json(list_release_phases())
    if args.industrial_release_action == 'phase-show':
        return _print_json(get_release_phase(args.phase_id))
    if args.industrial_release_action == 'definition-build':
        return _print_json(build_release_definition(root=root))
    if args.industrial_release_action == 'definition-show':
        return _print_json(show_release_definition(root=root))
    if args.industrial_release_action == 'external-validation-build':
        return _print_json(build_external_validation_report(
            root=root,
            validation_dir=Path(args.validation_dir) if args.validation_dir else None,
        ))
    if args.industrial_release_action == 'publication-check':
        return _print_json(build_publication_check(root=root))
    if args.industrial_release_action == 'gate-build':
        return _print_json(build_industrial_release_gate(root=root))
    if args.industrial_release_action == 'show':
        return _print_json(show_industrial_release_artifact(args.artifact_id, root=root))
    raise SystemExit(f'unknown industrial-release action {args.industrial_release_action}')


def cmd_tool_contract(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.tool_contract_action == 'export':
        return _print_json(export_tool_contract(args.contract_id, root=root))
    if args.tool_contract_action == 'show':
        return _print_json(show_tool_contract(args.contract_id, root=root))
    raise SystemExit(f'unknown tool-contract action {args.tool_contract_action}')


def cmd_operations_policy(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.operations_action == 'create':
        return _print_json(create_operations_policy(args.policy_id, root=root))
    if args.operations_action == 'show':
        return _print_json(show_operations_policy(args.policy_id, root=root))
    raise SystemExit(f'unknown operations-policy action {args.operations_action}')


def cmd_sop(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.sop_action == 'create':
        return _print_json(create_department_sop(args.sop_id, root=root))
    if args.sop_action == 'show':
        return _print_json(show_department_sop(args.sop_id, root=root))
    raise SystemExit(f'unknown sop action {args.sop_action}')


def cmd_audit_claim(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    claim = args.claim or Path(args.claim_file).read_text()
    result = claim_support_audit(claim, args.papers or [], root=paths.root)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_audit_note(args: argparse.Namespace) -> int:
    import json
    root = Path(args.root) if args.root else None
    if args.audit_action == 'show':
        payload = show_audit_notes(args.paper_id, root=root)
    elif args.audit_action == 'set':
        payload = set_audit_note(args.paper_id, args.field, args.value, root=root)
    elif args.audit_action == 'append':
        payload = append_audit_note(args.paper_id, args.field, args.value, root=root)
    elif args.audit_action == 'remove':
        payload = remove_audit_note(args.paper_id, args.field, args.value, root=root)
    elif args.audit_action == 'link-section':
        payload = link_audit_source_label(args.paper_id, args.label, kind='section', root=root)
    elif args.audit_action == 'link-equation':
        payload = link_audit_source_label(args.paper_id, args.label, kind='equation', root=root)
    elif args.audit_action == 'link-theorem':
        payload = link_audit_source_label(args.paper_id, args.label, kind='theorem', root=root)
    elif args.audit_action == 'link-citation':
        payload = link_audit_citation_key(args.paper_id, args.citation_key, root=root)
    else:
        raise SystemExit(f'unknown audit-note action {args.audit_action}')
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    import json
    payload = discover_papers_with_status(args.query, per_page=args.limit)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _download_failure_reason(discovery_payload: dict) -> str:
    if discovery_payload.get('status') == 'unavailable':
        return 'discovery unavailable'
    if discovery_payload.get('status') == 'empty':
        return 'discovery returned no open access candidates'
    if discovery_payload.get('results'):
        return 'no open access pdf found'
    return 'no open access pdf found'


def cmd_download_paper(args: argparse.Namespace) -> int:
    import json
    payload = discover_papers_with_status(args.query, per_page=args.limit)
    results = payload['results']
    downloadable = [r for r in results if r.get('open_access_pdf_url')]
    if not downloadable:
        print(json.dumps({
            'query': args.query,
            'downloaded': False,
            'reason': _download_failure_reason(payload),
            'discovery': payload,
        }, indent=2, sort_keys=True))
        return 0
    chosen = downloadable[0]
    proposal = propose_download(chosen, root=Path(args.root) if args.root else None, query=args.query)
    downloaded_path = download_to_inbox(chosen['open_access_pdf_url'], filename_hint=proposal.proposed_name.removesuffix('.pdf'), root=Path(args.root) if args.root else None)
    proposal_path = persist_download_proposal(proposal, root=Path(args.root) if args.root else None)
    print(json.dumps({
        'query': args.query,
        'downloaded': True,
        'discovery': payload,
        'result': chosen,
        'proposal': proposal.to_dict(),
        'proposal_path': str(proposal_path),
        'downloaded_path': str(downloaded_path),
    }, indent=2, sort_keys=True))
    return 0


def cmd_papers_citing(args: argparse.Namespace) -> int:
    import json
    results = papers_citing(args.paper_id, limit=args.limit)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_papers_cited_by(args: argparse.Namespace) -> int:
    import json
    results = papers_cited_by(args.paper_id, limit=args.limit)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_citation_neighborhood(args: argparse.Namespace) -> int:
    import json
    results = citation_graph.citation_neighborhood(args.paper_id, limit=args.limit)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_citation_graph_build(args: argparse.Namespace) -> int:
    import json
    payload = build_citation_graph(args.paper_id, root=Path(args.root) if args.root else None, depth=args.depth, limit=args.limit, refresh=args.refresh)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_citation_graph_show(args: argparse.Namespace) -> int:
    import json
    payload = show_citation_graph(args.paper_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_citation_graph_export(args: argparse.Namespace) -> int:
    output = export_citation_graph(args.paper_id, Path(args.output), root=Path(args.root) if args.root else None)
    print(output)
    return 0


def cmd_graph_node_download_proposal(args: argparse.Namespace) -> int:
    import json
    payload = propose_graph_node_download(args.paper_id, args.node_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_inbox_list(args: argparse.Namespace) -> int:
    import json
    rows = list_download_proposals(root=Path(args.root) if args.root else None, duplicate_status=args.duplicate_status)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    for row in rows:
        print(f"{row['proposed_name']}\t{row.get('duplicate_status', 'unknown')}\t{row.get('duplicate_count', 0)}\t{row['source']}\t{row['title']}")
    return 0


def cmd_inbox_show(args: argparse.Namespace) -> int:
    import json
    payload = show_download_proposal(args.proposed_name, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_literature_audit_propose(args: argparse.Namespace) -> int:
    import json
    payload = propose_literature_audit(args.paper_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_literature_audit_show(args: argparse.Namespace) -> int:
    import json
    payload = show_literature_audit(args.paper_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_literature_audit_approve(args: argparse.Namespace) -> int:
    import json
    payload = approve_literature_audit(args.paper_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_parse_pdf(args: argparse.Namespace) -> int:
    import json
    outputs = parse_with_all(Path(args.pdf).expanduser())
    reconciled = reconcile_parsed_documents(outputs)
    print(json.dumps(reconciled.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_parser_preflight(args: argparse.Namespace) -> int:
    import json
    checks = [c.to_dict() for c in preflight_all()]
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0


def cmd_evidence_context(args: argparse.Namespace) -> int:
    import json
    root = Path(args.root) if args.root else None
    if args.label:
        payload = evidence_context_for_label(args.paper_id, args.label, root=root)
    elif args.citation_key:
        payload = evidence_context_for_citation(args.paper_id, args.citation_key, root=root)
    else:
        raise SystemExit('evidence-context requires --label or --citation-key')
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_source_fetch(args: argparse.Namespace) -> int:
    import json
    paths = get_paths(Path(args.root) if args.root else None)
    source = args.paper_id or f'arxiv:{args.arxiv_id}'
    paper_id = args.paper_id or canonical_paper_id(source)
    record = fetch_arxiv_structured_source(args.arxiv_id, root=paths.root, paper_id=paper_id)
    print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_source_show(args: argparse.Namespace) -> int:
    import json
    paths = get_paths(Path(args.root) if args.root else None)
    store = FileStore(paths.local_research)
    payload = store.read_json(source_record_path(paths.papers_source, args.paper_id))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _source_record(args: argparse.Namespace) -> dict:
    # Source subcommands are intentionally thin views over the stored JSON audit artifact.
    paths = get_paths(Path(args.root) if args.root else None)
    return FileStore(paths.local_research).read_json(source_record_path(paths.papers_source, args.paper_id))


def cmd_source_sections(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('sections') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_equations(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('equations') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_theorems(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('theorem_like_blocks') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_citations(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('citations') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_bibliography(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('bibliography') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_macros(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('macros') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_labels(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('labels') or [], indent=2, sort_keys=True))
    return 0


def cmd_source_refs(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_record(args).get('references') or [], indent=2, sort_keys=True))
    return 0


def _source_block_by_label(record: dict, key: str, label: str) -> dict:
    for block in record.get(key) or []:
        if label in (block.get('labels') or []):
            return block
    raise SystemExit(f'no {key} block with label {label}')


def cmd_source_section(args: argparse.Namespace) -> int:
    import json
    if not args.title and not args.label:
        raise SystemExit('source-section requires --title or --label')
    record = _source_record(args)
    for section in record.get('sections') or []:
        if section.get('title') == args.title or args.label in (section.get('labels') or []):
            print(json.dumps(section, indent=2, sort_keys=True))
            return 0
    raise SystemExit('no section matched the requested title or label')


def cmd_source_equation(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_block_by_label(_source_record(args), 'equations', args.label), indent=2, sort_keys=True))
    return 0


def cmd_source_theorem(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(_source_block_by_label(_source_record(args), 'theorem_like_blocks', args.label), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='ra')
    parser.add_argument('--root', help='Research assistant project root')
    sub = parser.add_subparsers(dest='cmd', required=True)
    lifecycle_handlers = LifecycleHandlers(
        init=cmd_init,
        version=cmd_version,
        config=cmd_config,
        workspace=cmd_workspace,
        backup=cmd_backup,
        doctor=cmd_doctor,
        demo=cmd_demo,
        privacy=cmd_privacy,
        release_report=cmd_release_report,
        mcp=cmd_mcp,
        repository_hygiene=cmd_repository_hygiene,
        individual_git_release=cmd_individual_git_release,
        bounded_workflow=cmd_bounded_workflow,
        performance=cmd_performance,
        parser_tool_matrix=cmd_parser_tool_matrix,
        parser_benchmark_smoke=cmd_parser_benchmark_smoke,
        arxiv_batch=cmd_arxiv_batch,
        release_artifacts=cmd_release_artifacts,
        platform_status=cmd_platform_status,
    )
    register_lifecycle_commands(sub, lifecycle_handlers)

    register_survey_commands(sub, cmd_survey)
    register_surveybench_commands(sub, cmd_surveybench)
    register_release_utility_commands(sub, lifecycle_handlers)

    register_library_commands(
        sub,
        LibraryHandlers(
            ingest=cmd_ingest,
            find=cmd_find,
            show=cmd_show,
            export_context=cmd_export_context,
            review_list=cmd_review_list,
            review_show=cmd_review_show,
            review_mark=cmd_review_mark,
            review_write=cmd_review_write,
            link_add=cmd_link_add,
        ),
    )

    register_industrial_commands(
        sub,
        IndustrialHandlers(
            artifact_paths=cmd_artifact_paths,
            industrial_validate=cmd_industrial_validate,
            domain_templates=cmd_domain_templates,
            derivation=cmd_derivation,
            experiment=cmd_experiment,
            graph_report=cmd_graph_report,
            review_meta=cmd_review_meta,
            benchmark_manifest=cmd_benchmark_manifest,
            synthesis=cmd_synthesis,
            governance=cmd_governance,
            job=cmd_job,
            dashboard_export=cmd_dashboard_export,
            traceability=cmd_traceability,
            model_policy=cmd_model_policy,
            collaboration=cmd_collaboration,
            artifact_index=cmd_artifact_index,
            industrial_readiness=cmd_industrial_readiness,
            full_scale_plan=cmd_full_scale_plan,
            industrial_release=cmd_industrial_release,
            tool_contract=cmd_tool_contract,
            operations_policy=cmd_operations_policy,
            sop=cmd_sop,
        ),
    )

    register_research_commands(
        sub,
        ResearchHandlers(
            audit_claim=cmd_audit_claim,
            audit_note=cmd_audit_note,
            discover=cmd_discover,
            download_paper=cmd_download_paper,
            papers_citing=cmd_papers_citing,
            papers_cited_by=cmd_papers_cited_by,
            citation_neighborhood=cmd_citation_neighborhood,
            citation_graph_build=cmd_citation_graph_build,
            citation_graph_show=cmd_citation_graph_show,
            citation_graph_export=cmd_citation_graph_export,
            graph_node_download_proposal=cmd_graph_node_download_proposal,
            inbox_list=cmd_inbox_list,
            inbox_show=cmd_inbox_show,
            literature_audit_propose=cmd_literature_audit_propose,
            literature_audit_show=cmd_literature_audit_show,
            literature_audit_approve=cmd_literature_audit_approve,
            parse_pdf=cmd_parse_pdf,
            parser_preflight=cmd_parser_preflight,
            evidence_context=cmd_evidence_context,
            source_inspection=SourceInspectionHandlers(
                source_fetch=cmd_source_fetch,
                source_show=cmd_source_show,
                source_sections=cmd_source_sections,
                source_equations=cmd_source_equations,
                source_theorems=cmd_source_theorems,
                source_citations=cmd_source_citations,
                source_bibliography=cmd_source_bibliography,
                source_macros=cmd_source_macros,
                source_labels=cmd_source_labels,
                source_section=cmd_source_section,
                source_refs=cmd_source_refs,
                source_equation=cmd_source_equation,
                source_theorem=cmd_source_theorem,
            ),
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
