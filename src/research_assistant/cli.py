from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_assistant.adapters.workspace_exports import export_paper_context
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
    onboarding_report,
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
from research_assistant.individual_git_release import (
    classify_shareable_path,
    fixture_rehearsal,
    individual_git_release_gate,
    load_shareable_workspace_policy,
    record_local_validation_substitutes,
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
from research_assistant.summarize.claim_support import audit_claim
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
    if args.individual_git_release_action == 'validation-substitutes':
        return _print_json(record_local_validation_substitutes(root=root))
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
    if args.survey_action == "build":
        report = build_survey_evidence_packet(
            topic=args.topic,
            seeds=args.seed,
            output_dir=Path(args.out),
            mode=args.mode,
            force=args.force,
            replay_task=Path(args.replay_task) if getattr(args, "replay_task", None) else None,
            replay_responses_dir=Path(args.replay_responses_dir) if getattr(args, "replay_responses_dir", None) else None,
            public_metadata_providers=getattr(args, "public_metadata_provider", None),
            max_records=getattr(args, "max_records", 25),
        )
        _print_json(report)
        return 0 if report["status"] in {
            "created_skeleton",
            "partial",
            "offline_replay_fixture_complete",
            "metadata_only_packet",
        } else 1
    if args.survey_action == "anchors":
        report = build_source_anchor_packet(
            topic=args.topic,
            paper_ids=args.paper_id,
            output_dir=Path(args.out),
            force=args.force,
            max_anchors_per_paper=args.max_anchors_per_paper,
            root=Path(args.root) if args.root else None,
        )
        _print_json(report)
        return 0 if report["status"] in {"anchors_extracted", "source_gaps_or_no_anchors"} else 1
    if args.survey_action == "packet":
        report = compose_public_source_evidence_packet(
            topic=args.topic,
            output_dir=Path(args.out),
            metadata_dir=Path(args.metadata_dir),
            source_status_dir=Path(args.source_status_dir),
            anchor_dir=Path(args.anchor_dir),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] == "packet_composed_with_blockers" else 1
    if args.survey_action == "coverage-ledgers":
        report = compose_coverage_ledgers(
            topic=args.topic,
            packet_dir=Path(args.packet_dir),
            output_dir=Path(args.out),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] == "coverage_ledgers_composed" else 1
    if args.survey_action == "compose-reviewed-final-packet":
        report = compose_reviewed_final_packet(
            mission_root=Path(args.mission_root),
            review_queue_path=Path(args.review_queue),
            packet_dir=Path(args.packet_dir),
            anchor_dir=Path(args.anchor_dir),
            local_evidence_root=Path(args.local_evidence_root) if args.local_evidence_root else None,
            output_dir=Path(args.out),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] == "reviewed_final_packet_ready_for_hostile_review" else 1
    if args.survey_action == "hostile-review":
        report = run_hostile_review_gate(
            reviewed_final_packet_path=Path(args.reviewed_final_packet),
            mission_root=Path(args.mission_root),
            review_queue_path=Path(args.review_queue),
            packet_dir=Path(args.packet_dir),
            anchor_dir=Path(args.anchor_dir),
            local_evidence_root=Path(args.local_evidence_root) if args.local_evidence_root else None,
            output_dir=Path(args.out),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] in {
            "ready_for_reviewed_prose_within_recorded_scope",
            "blocked_for_reviewed_prose",
        } else 1
    if args.survey_action == "run-public-source-workflow":
        report = run_public_source_workflow(
            topic=args.topic,
            seeds=args.seed,
            output_dir=Path(args.out),
            run_safe_local=args.run_safe_local,
            confirm_public_discovery=args.confirm_public_discovery,
            resume=args.resume,
            force=args.force,
            metadata_dir=Path(args.metadata_dir) if args.metadata_dir else None,
            source_status_dir=Path(args.source_status_dir) if args.source_status_dir else None,
            anchor_dir=Path(args.anchor_dir) if args.anchor_dir else None,
            packet_dir=Path(args.packet_dir) if args.packet_dir else None,
            coverage_dir=Path(args.coverage_dir) if args.coverage_dir else None,
            reviewed_claims_dir=Path(args.reviewed_claims_dir) if args.reviewed_claims_dir else None,
            reviewed_source_safety_dir=Path(args.reviewed_source_safety_dir) if args.reviewed_source_safety_dir else None,
            reviewed_omissions_dir=Path(args.reviewed_omissions_dir) if args.reviewed_omissions_dir else None,
            reviewed_workflow_blockers_dir=Path(args.reviewed_workflow_blockers_dir) if args.reviewed_workflow_blockers_dir else None,
            reviewed_evidence_dir=Path(args.reviewed_evidence_dir) if args.reviewed_evidence_dir else None,
            local_evidence_root=Path(args.local_evidence_root) if args.local_evidence_root else None,
        )
        _print_json(report)
        return 0 if report["status"] in {"blocked_at_gate", "ready_for_local_continuation"} else 1
    if args.survey_action == "import-claim-review":
        report = import_reviewed_claims(
            review_queue_path=Path(args.review_queue),
            decisions_path=Path(args.decisions),
            output_dir=Path(args.out),
            force=args.force,
            human_attestation_receipt_path=(
                Path(args.human_attestation_receipt)
                if args.human_attestation_receipt else None
            ),
        )
        _print_json(report)
        return 0 if report["status"] == "reviewed_claims_complete" else 1
    if args.survey_action == "import-source-safety-review":
        report = import_reviewed_source_safety(
            review_queue_path=Path(args.review_queue),
            decisions_path=Path(args.decisions),
            output_dir=Path(args.out),
            force=args.force,
            human_attestation_receipt_path=(
                Path(args.human_attestation_receipt)
                if args.human_attestation_receipt else None
            ),
        )
        _print_json(report)
        return 0 if report["status"] == "reviewed_source_safety_complete" else 1
    if args.survey_action == "import-omission-review":
        report = import_reviewed_omissions(
            review_queue_path=Path(args.review_queue),
            decisions_path=Path(args.decisions),
            output_dir=Path(args.out),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] in {
            "reviewed_omissions_complete",
        } else 1
    if args.survey_action == "import-workflow-blocker-review":
        report = import_reviewed_workflow_blockers(
            review_queue_path=Path(args.review_queue),
            decisions_path=Path(args.decisions),
            output_dir=Path(args.out),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] == "reviewed_workflow_blockers_complete" else 1
    if args.survey_action == "merge-reviewed-evidence":
        report = merge_reviewed_evidence(
            review_queue_path=Path(args.review_queue),
            reviewed_claims_path=Path(args.reviewed_claims),
            reviewed_source_safety_path=Path(args.reviewed_source_safety),
            reviewed_omissions_path=Path(args.reviewed_omissions),
            reviewed_workflow_blockers_path=Path(args.reviewed_workflow_blockers),
            output_dir=Path(args.out),
            force=args.force,
        )
        _print_json(report)
        return 0 if report["status"] in {
            "reviewed_evidence_complete",
            "reviewed_evidence_blocked",
            "reviewed_evidence_blocked_unavailable_source_outcome",
        } else 1
    if args.survey_action == "prepare-human-review":
        try:
            report = prepare_human_review_packet(
                review_queue_path=Path(args.review_queue),
                output_dir=Path(args.out),
                force=args.force,
            )
        except MissionStateError as exc:
            report = _human_attestation_blocked(exc)
        _print_json(report)
        return 0 if report["status"] == "human_review_packet_prepared_unattested" else 1
    if args.survey_action == "render-human-review":
        try:
            report = render_human_review_materials(
                packet_path=Path(args.packet),
                output_dir=Path(args.out) if args.out else None,
                force=args.force,
            )
        except MissionStateError as exc:
            report = _human_attestation_blocked(exc)
        _print_json(report)
        return 0 if report["status"] == "human_review_materials_rendered" else 1
    if args.survey_action == "validate-human-attestation":
        try:
            report = validate_human_attestation(
                review_queue_path=Path(args.review_queue),
                packet_path=Path(args.packet),
                attestation_path=Path(args.attestation),
                decision_paths={
                    "claim_candidate": Path(args.claim_decisions),
                    "source_safety": Path(args.source_safety_decisions),
                    "omission_risk": Path(args.omission_decisions),
                    "workflow_blocker": Path(args.workflow_blocker_decisions),
                },
                output_dir=Path(args.out),
                force=args.force,
            )
        except MissionStateError as exc:
            report = _human_attestation_blocked(exc)
        _print_json(report)
        return 0 if report["status"] == "human_self_attestation_validated" else 1
    if args.survey_action == "qualitative-assessment":
        assessment = build_assessment(
            subject_id=args.subject_id,
            assessment_type=args.assessment_type,
            summary=args.summary,
            merits=args.merit,
            concerns=args.concern,
            uncertainties=args.uncertainty,
            evidence_refs=args.evidence_ref,
            next_action=args.next_action,
        )
        report = write_assessment(
            assessment=assessment,
            output_path=Path(args.out),
            force=args.force,
        )
        _print_json({**report, "assessment": assessment})
        return 0
    raise SystemExit(f"unknown survey action {args.survey_action}")


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
    if args.surveybench_action == "run":
        report = score_survey_task(
            Path(args.task).resolve(),
            Path(args.actual_dir).resolve() if args.actual_dir else None,
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-cli-result-v1",
                "status": report["status"],
                "task_id": report["task_id"],
                "report_path": _display_cli_path(Path(args.output)),
                "vetoes": report["vetoes"],
                "errors": report["errors"],
            }
        _print_json(report)
        return 0 if report["status"] == "passed" else 1
    if args.surveybench_action == "local-manifest":
        report = validate_local_manifest(Path(args.manifest).resolve())
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-local-manifest-cli-result-v1",
                "status": report["status"],
                "report_path": _display_cli_path(Path(args.output)),
                "issue_count": len(report["issues"]),
            }
        _print_json(report)
        return 0 if report["status"] == "passed" else 1
    if args.surveybench_action == "replay-call":
        result = replay_call(
            Path(args.task).resolve(),
            args.endpoint,
            Path(args.session).resolve(),
            request_id=args.request_id,
        )
        _print_json(result)
        return 0 if result["status"] in {"ok", "simulated_rate_limit"} else 1
    if args.surveybench_action == "replay-audit":
        report = validate_replay_fixture_interface(Path(args.task).resolve())
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-online-replay-audit-cli-result-v1",
                "status": report["status"],
                "task_id": report["task_id"],
                "report_path": _display_cli_path(Path(args.output)),
                "issue_count": report["issue_count"],
            }
        _print_json(report)
        return 0 if report["status"] == "passed" else 1
    if args.surveybench_action == "replay-transcript":
        report = build_replay_transcript(
            Path(args.task).resolve(),
            Path(args.session).resolve(),
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-online-replay-transcript-cli-result-v1",
                "status": "passed",
                "task_id": report["task_id"],
                "report_path": _display_cli_path(Path(args.output)),
                "event_count": report["event_count"],
                "summary": report["summary"],
            }
        _print_json(report)
        return 0
    if args.surveybench_action == "replay-score":
        report = score_replay_submission(
            Path(args.task).resolve(),
            Path(args.actual_dir).resolve(),
            Path(args.event_log).resolve(),
            Path(args.gold_dir).resolve(),
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-online-replay-score-cli-result-v1",
                "status": report["status"],
                "task_id": report["task_id"],
                "report_path": _display_cli_path(Path(args.output)),
                "vetoes": report["vetoes"],
                "errors": report["errors"],
            }
        _print_json(report)
        return 0 if report["status"] == "passed" else 1
    if args.surveybench_action == "score-prose":
        report = score_survey_prose(
            Path(args.task).resolve(),
            Path(args.actual_dir).resolve(),
            Path(args.event_log).resolve(),
            Path(args.gold_dir).resolve(),
            Path(args.prose).resolve(),
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-survey-prose-score-cli-result-v1",
                "status": report["status"],
                "task_id": report["task_id"],
                "report_path": _display_cli_path(Path(args.output)),
                "hard_gate_vetoes": report["hard_gate_vetoes"],
                "errors": report["errors"],
            }
        _print_json(report)
        return 0 if report["status"] == "passed" else 1
    if args.surveybench_action == "restricted-workspace":
        report = create_restricted_workspace(
            Path(args.repo_root).resolve(),
            Path(args.workspace).resolve(),
            force=args.force,
            profile=args.profile,
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-restricted-workspace-cli-result-v1",
                "status": report["status"],
                "profile_id": report["profile_id"],
                "task_id": report["task_id"],
                "workspace_root": report["workspace_root"],
                "report_path": _display_cli_path(Path(args.output)),
                "copied_file_count": report["copied_file_count"],
            }
        _print_json(report)
        return 0 if report["status"] == "passed" else 1
    if args.surveybench_action == "restricted-launcher-dry-run":
        report = build_restricted_launcher_dry_run(
            Path(args.workspace).resolve(),
            profile=args.profile,
            subject_agent=args.subject_agent,
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-restricted-launcher-dry-run-cli-result-v1",
                "status": report["status"],
                "dry_run": report["dry_run"],
                "subject_invoked": report["subject_invoked"],
                "profile_id": report["profile_id"],
                "task_id": report["task_id"],
                "workspace_root": report["workspace_root"],
                "report_path": _display_cli_path(Path(args.output)),
            }
        _print_json(report)
        return 0 if report["status"] == "prepared_not_launched" and report["subject_invoked"] is False else 1
    if args.surveybench_action == "subject-binding-preflight":
        report = build_subject_binding_preflight(
            Path(args.workspace).resolve(),
            profile=args.profile,
            subject_agent=args.subject_agent,
            model_id=args.model_id,
            permission_mode=args.permission_mode,
            subject_transport=args.subject_transport,
            representative_endpoint=args.representative_endpoint,
        )
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            report = {
                "schema_version": "ra-surveybench-subject-binding-preflight-cli-result-v1",
                "status": report["status"],
                "subject_invoked": report["subject_invoked"],
                "profile_id": report["profile_id"],
                "task_id": report["task_id"],
                "permission_mode": report["permission_mode"],
                "settings_path": report["settings_path"],
                "representative_probe_status": report["representative_probe"]["status"],
                "report_path": _display_cli_path(Path(args.output)),
                "issue_count": len(report["issues"]),
            }
        _print_json(report)
        return 0 if report["status"] == "passed" and report["subject_invoked"] is False else 1
    if args.surveybench_action == "launch-approval-packet":
        dry_run = json.loads(Path(args.launcher_dry_run).read_text())
        wrapper_command = json.loads(args.wrapper_command_json) if args.wrapper_command_json else args.wrapper_command
        if not wrapper_command:
            raise SystemExit("launch-approval-packet requires --wrapper-command-json or --wrapper-command")
        subject_binding_preflight = (
            json.loads(Path(args.subject_binding_preflight).read_text())
            if args.subject_binding_preflight
            else None
        )
        packet = build_launch_approval_packet(
            dry_run,
            subject_agent=args.subject_agent,
            model_id=args.model_id,
            subject_transport=args.subject_transport or (subject_binding_preflight or {}).get("subject_transport", "claude-code"),
            wrapper_command=wrapper_command,
            budget_cap=json.loads(args.budget_cap_json),
            transcript_path=Path(args.transcript_path).resolve(),
            denied_tool_capture_path=Path(args.denied_tool_capture_path).resolve(),
            cli_version=args.cli_version,
            subject_binding_preflight=subject_binding_preflight,
        )
        preflight = validate_launch_approval_packet(packet)
        report = {
            "schema_version": "ra-surveybench-launch-approval-packet-cli-result-v1",
            "status": preflight["status"],
            "packet_status": packet["status"],
            "subject_invoked": packet["subject_invoked"],
            "human_approval_granted": preflight["human_approval_granted"],
            "issue_count": len(preflight["issues"]),
            "issues": preflight["issues"],
        }
        if args.output:
            Path(args.output).write_text(json.dumps(packet, indent=2, sort_keys=True))
            report["report_path"] = _display_cli_path(Path(args.output))
        _print_json(report)
        return 0 if preflight["status"] == "passed" and packet["subject_invoked"] is False else 1
    if args.surveybench_action == "launch-enforcement-preflight":
        report = build_launch_enforcement_preflight(Path(args.approval_packet).resolve())
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True))
            summary = {
                "schema_version": "ra-surveybench-launch-enforcement-preflight-cli-result-v1",
                "status": report["status"],
                "subject_invoked": report["subject_invoked"],
                "approval_packet_status": report["approval_packet_status"],
                "human_approval_granted": report["human_approval_granted"],
                "report_path": _display_cli_path(Path(args.output)),
                "issue_count": len(report["issues"]),
            }
            _print_json(summary)
            return 0 if report["status"] == "passed" and report["subject_invoked"] is False else 1
        _print_json(report)
        return 0 if report["status"] == "passed" and report["subject_invoked"] is False else 1
    if args.surveybench_action == "next-action":
        report = surveybench_next_action(
            Path(args.task).resolve(),
            Path(args.session).resolve() if args.session else None,
            Path(args.actual_dir).resolve() if args.actual_dir else None,
        )
        scan = scan_subject_helper_payload(report)
        if scan["status"] != "passed":
            report["leak_scan"] = scan
            _print_json(report)
            return 1
        _print_json(report)
        return 0
    if args.surveybench_action == "packet-template":
        report = surveybench_packet_template(
            Path(args.task).resolve(),
            Path(args.output_dir).resolve() if args.output_dir else None,
            write_files=args.write_files,
        )
        scan = scan_subject_helper_payload(report)
        if scan["status"] != "passed":
            report["leak_scan"] = scan
            _print_json(report)
            return 1
        _print_json(report)
        return 0
    if args.surveybench_action == "packet-compose":
        report = surveybench_packet_compose(
            Path(args.task).resolve(),
            Path(args.output_dir).resolve(),
            session_dir=Path(args.session).resolve() if args.session else None,
            responses_dir=Path(args.responses_dir).resolve() if args.responses_dir else None,
            write_files=args.write_files,
        )
        scan = scan_subject_helper_payload(report)
        if scan["status"] != "passed":
            report["leak_scan"] = scan
            _print_json(report)
            return 1
        _print_json(report)
        return 0 if report["status"] == "ready" else 1
    if args.surveybench_action == "cluster-hints":
        report = surveybench_cluster_hints(
            Path(args.task).resolve(),
            Path(args.responses_dir).resolve() if args.responses_dir else None,
        )
        scan = scan_subject_helper_payload(report)
        if scan["status"] != "passed":
            report["leak_scan"] = scan
            _print_json(report)
            return 1
        _print_json(report)
        return 0 if report["status"] == "ready" else 1
    if args.surveybench_action == "ready-for-prose":
        report = surveybench_ready_for_prose(
            Path(args.task).resolve(),
            Path(args.actual_dir).resolve(),
            Path(args.session).resolve() if args.session else None,
        )
        scan = scan_subject_helper_payload(report)
        if scan["status"] != "passed":
            report["leak_scan"] = scan
            _print_json(report)
            return 1
        _print_json(report)
        return 0 if report["status"] == "ready" else 1
    if args.surveybench_action == "launch-record-template":
        report = surveybench_launch_record_template(Path(args.task).resolve())
        scan = scan_subject_helper_payload(report)
        if scan["status"] != "passed":
            report["leak_scan"] = scan
            _print_json(report)
            return 1
        _print_json(report)
        return 0
    raise SystemExit(f"unknown surveybench action {args.surveybench_action}")


def cmd_release_artifacts(args: argparse.Namespace) -> int:
    if args.release_artifacts_action == 'manifest':
        return _print_json(release_artifacts_manifest(
            dist_dir=Path(args.dist_dir) if args.dist_dir else None,
        ))
    raise SystemExit(f'unknown release-artifacts action {args.release_artifacts_action}')


def _register_repository_hygiene_commands(sub: argparse._SubParsersAction) -> None:
    """Register Git-sharing hygiene commands without changing their public names."""
    repository_hygiene = sub.add_parser('repository-hygiene', help='Check whether a local workspace is safe to share through Git')
    repository_hygiene_sub = repository_hygiene.add_subparsers(dest='repository_hygiene_action', required=True)
    repository_hygiene_check_cmd = repository_hygiene_sub.add_parser('check')
    repository_hygiene_check_cmd.add_argument('--strict', action='store_true')
    repository_hygiene_check_cmd.set_defaults(func=cmd_repository_hygiene)
    repository_hygiene_policy_cmd = repository_hygiene_sub.add_parser('policy')
    repository_hygiene_policy_cmd.set_defaults(func=cmd_repository_hygiene)
    repository_hygiene_classify_cmd = repository_hygiene_sub.add_parser('classify')
    repository_hygiene_classify_cmd.add_argument('path')
    repository_hygiene_classify_cmd.set_defaults(func=cmd_repository_hygiene)


def _register_individual_git_release_commands(sub: argparse._SubParsersAction) -> None:
    """Register the individual Git release gate commands as a stable CLI group."""
    individual_git_release_cmd = sub.add_parser('individual-git-release', help='Build the individual Git-sharing release gate')
    individual_git_release_sub = individual_git_release_cmd.add_subparsers(dest='individual_git_release_action', required=True)
    individual_git_release_gate_cmd = individual_git_release_sub.add_parser('gate-build')
    individual_git_release_gate_cmd.set_defaults(func=cmd_individual_git_release)
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
    individual_git_release_validation_record.set_defaults(func=cmd_individual_git_release)
    individual_git_release_validation_report = individual_git_release_sub.add_parser('validation-report')
    individual_git_release_validation_report.set_defaults(func=cmd_individual_git_release)
    individual_git_release_validation_substitutes = individual_git_release_sub.add_parser('validation-substitutes')
    individual_git_release_validation_substitutes.set_defaults(func=cmd_individual_git_release)
    individual_git_release_fixture = individual_git_release_sub.add_parser('fixture-rehearsal')
    individual_git_release_fixture.add_argument('--fixture-root')
    individual_git_release_fixture.add_argument('--include-blocker', action=argparse.BooleanOptionalAction, default=False)
    individual_git_release_fixture.add_argument('--apply-safe-subset', action=argparse.BooleanOptionalAction, default=True)
    individual_git_release_fixture.set_defaults(func=cmd_individual_git_release)
    individual_git_release_performance = individual_git_release_sub.add_parser('performance')
    individual_git_release_performance.add_argument('--tier', default='synthetic_git_100')
    individual_git_release_performance.add_argument('--synthetic-count', type=int, default=100)
    individual_git_release_performance.add_argument('--timeout-seconds', type=float)
    individual_git_release_performance.set_defaults(func=cmd_individual_git_release)


def cmd_onboarding_report(args: argparse.Namespace) -> int:
    return _print_json(onboarding_report())


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

    init_cmd = sub.add_parser('init', help='Initialize an idempotent local research workspace')
    init_cmd.add_argument('--force', action='store_true', help='Regenerate safe default config without deleting data')
    init_cmd.set_defaults(func=cmd_init)

    version_cmd = sub.add_parser('version', help='Show package and workspace schema versions')
    version_cmd.set_defaults(func=cmd_version)

    config_cmd = sub.add_parser('config', help='Inspect and validate local release configuration')
    config_sub = config_cmd.add_subparsers(dest='config_action', required=True)
    config_show = config_sub.add_parser('show')
    config_show.set_defaults(func=cmd_config)
    config_set = config_sub.add_parser('set')
    config_set.add_argument('key')
    config_set.add_argument('value')
    config_set.set_defaults(func=cmd_config)
    config_validate = config_sub.add_parser('validate')
    config_validate.set_defaults(func=cmd_config)

    workspace_cmd = sub.add_parser('workspace', help='Validate, migrate, or repair a local workspace')
    workspace_sub = workspace_cmd.add_subparsers(dest='workspace_action', required=True)
    workspace_validate_cmd = workspace_sub.add_parser('validate')
    workspace_validate_cmd.set_defaults(func=cmd_workspace)
    workspace_migrate_cmd = workspace_sub.add_parser('migrate')
    workspace_migrate_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    workspace_migrate_cmd.set_defaults(func=cmd_workspace)
    workspace_repair_cmd = workspace_sub.add_parser('repair')
    workspace_repair_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    workspace_repair_cmd.set_defaults(func=cmd_workspace)
    workspace_merge_cmd = workspace_sub.add_parser('merge')
    workspace_merge_cmd.add_argument('--source', required=True)
    workspace_merge_cmd.add_argument('--target')
    workspace_merge_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    workspace_merge_cmd.add_argument('--apply', action='store_true')
    workspace_merge_cmd.add_argument('--confirm-merge', action='store_true')
    workspace_merge_cmd.set_defaults(func=cmd_workspace)
    workspace_rebuild_cmd = workspace_sub.add_parser('rebuild-derived')
    workspace_rebuild_cmd.set_defaults(func=cmd_workspace)

    backup_cmd = sub.add_parser('backup', help='Create, inspect, and dry-run restore local backups')
    backup_sub = backup_cmd.add_subparsers(dest='backup_action', required=True)
    backup_create = backup_sub.add_parser('create')
    backup_create.add_argument('--output')
    backup_create.set_defaults(func=cmd_backup)
    backup_inspect = backup_sub.add_parser('inspect')
    backup_inspect.add_argument('--path', required=True)
    backup_inspect.set_defaults(func=cmd_backup)
    backup_restore = backup_sub.add_parser('restore')
    backup_restore.add_argument('--path', required=True)
    backup_restore.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    backup_restore.add_argument('--target-root')
    backup_restore.add_argument('--confirm-restore', action='store_true')
    backup_restore.add_argument('--allow-overwrite', action='store_true')
    backup_restore.add_argument('--backup-current-first', action=argparse.BooleanOptionalAction, default=True)
    backup_restore.set_defaults(func=cmd_backup)

    doctor_cmd = sub.add_parser('doctor', help='Report individual-install readiness and optional tool status')
    doctor_cmd.add_argument('--matrix', action='store_true', help='Include full parser/tool workflow matrix')
    doctor_cmd.set_defaults(func=cmd_doctor)

    demo_cmd = sub.add_parser('demo', help='Create and run the isolated individual-release demo workflow')
    demo_sub = demo_cmd.add_subparsers(dest='demo_action', required=True)
    demo_setup_cmd = demo_sub.add_parser('setup')
    demo_setup_cmd.set_defaults(func=cmd_demo)
    demo_run_cmd = demo_sub.add_parser('run')
    demo_run_cmd.set_defaults(func=cmd_demo)
    demo_clean_cmd = demo_sub.add_parser('clean')
    demo_clean_cmd.add_argument('--dry-run', action=argparse.BooleanOptionalAction, default=True)
    demo_clean_cmd.add_argument('--force', action='store_true')
    demo_clean_cmd.set_defaults(func=cmd_demo)

    privacy_cmd = sub.add_parser('privacy', help='Show offline/provider privacy status')
    privacy_sub = privacy_cmd.add_subparsers(dest='privacy_action', required=True)
    privacy_status_cmd = privacy_sub.add_parser('status')
    privacy_status_cmd.set_defaults(func=cmd_privacy)

    release_report_cmd = sub.add_parser('release-report', help='Summarize individual release candidate readiness')
    release_report_cmd.add_argument('--output')
    release_report_cmd.set_defaults(func=cmd_release_report)

    mcp_cmd = sub.add_parser('mcp', help='Inspect local MCP permissions and bounded grants')
    mcp_sub = mcp_cmd.add_subparsers(dest='mcp_action', required=True)
    mcp_status = mcp_sub.add_parser('status')
    mcp_status.set_defaults(func=cmd_mcp)
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
    mcp_grant_arxiv.set_defaults(func=cmd_mcp)
    mcp_grants = mcp_sub.add_parser('grants')
    mcp_grants_sub = mcp_grants.add_subparsers(dest='grants_action', required=True)
    mcp_grants_list = mcp_grants_sub.add_parser('list')
    mcp_grants_list.set_defaults(func=cmd_mcp)
    mcp_grants_show = mcp_grants_sub.add_parser('show')
    mcp_grants_show.add_argument('--grant-id', required=True)
    mcp_grants_show.set_defaults(func=cmd_mcp)
    mcp_audit = mcp_sub.add_parser('audit')
    mcp_audit_sub = mcp_audit.add_subparsers(dest='audit_action', required=True)
    mcp_audit_list = mcp_audit_sub.add_parser('list')
    mcp_audit_list.add_argument('--grant-id')
    mcp_audit_list.set_defaults(func=cmd_mcp)

    _register_repository_hygiene_commands(sub)
    _register_individual_git_release_commands(sub)

    bounded_workflow_cmd = sub.add_parser('bounded-workflow', help='Write local timeout diagnostics for bounded workflow failures')
    bounded_sub = bounded_workflow_cmd.add_subparsers(dest='bounded_action', required=True)
    bounded_diagnostic = bounded_sub.add_parser('diagnostic')
    bounded_diagnostic.add_argument('--workflow', required=True)
    bounded_diagnostic.add_argument('--timeout-seconds', type=int, required=True)
    bounded_diagnostic.add_argument('--elapsed-seconds', type=float)
    bounded_diagnostic.set_defaults(func=cmd_bounded_workflow)

    performance_cmd = sub.add_parser('performance', help='Run bounded local performance smoke checks')
    performance_sub = performance_cmd.add_subparsers(dest='performance_action', required=True)
    performance_smoke_cmd = performance_sub.add_parser('smoke')
    performance_smoke_cmd.add_argument('--synthetic-count', type=int, default=25)
    performance_smoke_cmd.add_argument('--include-industrial-artifacts', action='store_true')
    performance_smoke_cmd.add_argument('--include-backup', action='store_true')
    performance_smoke_cmd.add_argument('--include-export', action='store_true')
    performance_smoke_cmd.add_argument('--timeout-seconds', type=int)
    performance_smoke_cmd.add_argument('--output')
    performance_smoke_cmd.set_defaults(func=cmd_performance)

    parser_matrix = sub.add_parser('parser-tool-matrix', help='Show optional parser/tool workflow readiness')
    parser_matrix.set_defaults(func=cmd_parser_tool_matrix)

    parser_benchmark = sub.add_parser('parser-benchmark-smoke', help='Run fixture-only parser benchmark smoke')
    parser_benchmark.set_defaults(func=cmd_parser_benchmark_smoke)

    survey = sub.add_parser('survey', help='Build literature-survey evidence packets')
    survey_sub = survey.add_subparsers(dest='survey_action', required=True)
    survey_build = survey_sub.add_parser(
        'build',
        help='Build a topic+seed survey evidence packet; metadata mode never fetches source/PDF/full text',
        description='Build a topic+seed survey evidence packet. Public metadata mode never fetches source/PDF/full text.',
    )
    survey_build.add_argument('--topic', required=True)
    survey_build.add_argument('--seed', action='append', required=True, help='Seed paper identifier; repeat for multiple seeds')
    survey_build.add_argument('--out', required=True, help='Output directory for the evidence packet')
    survey_build.add_argument(
        '--mode',
        default='offline-skeleton',
        choices=['offline-skeleton', 'offline-replay', 'public-metadata'],
        help='offline-skeleton writes a planning packet; offline-replay uses fixture evidence; public-metadata uses bounded public metadata only',
    )
    survey_build.add_argument('--replay-task', help='Visible replay task JSON for offline-replay mode')
    survey_build.add_argument('--replay-responses-dir', help='Visible replay responses directory for offline-replay mode')
    survey_build.add_argument(
        '--public-metadata-provider',
        action='append',
        choices=['openalex', 'arxiv'],
        help='Public metadata provider for public-metadata mode; repeat to include both OpenAlex and arXiv',
    )
    survey_build.add_argument('--max-records', type=int, default=25, help='Maximum public metadata records; capped at 25')
    survey_build.add_argument('--force', action='store_true')
    survey_build.set_defaults(func=cmd_survey)
    survey_anchors = survey_sub.add_parser('anchors', help='Extract checked source-anchor ledgers from local structured source records')
    survey_anchors.add_argument('--paper-id', action='append', required=True, help='Local structured source paper id; repeat for multiple papers')
    survey_anchors.add_argument('--out', required=True, help='Output directory for source-anchor ledgers')
    survey_anchors.add_argument('--topic')
    survey_anchors.add_argument('--max-anchors-per-paper', type=int, default=24)
    survey_anchors.add_argument('--force', action='store_true')
    survey_anchors.set_defaults(func=cmd_survey)
    survey_packet = survey_sub.add_parser(
        'packet',
        help='Compose a public-source writer packet from prior-phase ledgers without upgrading blocked claims to prose readiness',
        description='Compose a public-source writer packet from prior-phase ledgers without upgrading blocked claims to prose readiness.',
    )
    survey_packet.add_argument('--topic', required=True)
    survey_packet.add_argument('--out', required=True, help='Output directory for the public-source evidence packet')
    survey_packet.add_argument('--metadata-dir', required=True, help='Directory containing public metadata ledgers')
    survey_packet.add_argument('--source-status-dir', required=True, help='Directory containing Phase 4 source intake status')
    survey_packet.add_argument('--anchor-dir', required=True, help='Directory containing Phase 5 source-anchor ledgers')
    survey_packet.add_argument('--force', action='store_true')
    survey_packet.set_defaults(func=cmd_survey)
    survey_coverage = survey_sub.add_parser(
        'coverage-ledgers',
        help='Compose local coverage and snowballing ledgers from existing packet artifacts without live expansion',
        description='Compose backward_snowball.json, forward_snowball.json, citation_venue_metadata.json, paper_classifications.json, and omitted_paper_risks.json from existing local packet artifacts. This does not run live metadata/source expansion and does not claim literature completeness.',
    )
    survey_coverage.add_argument('--topic', required=True)
    survey_coverage.add_argument('--packet-dir', required=True, help='Existing public-source packet directory; command runs without live expansion')
    survey_coverage.add_argument('--out', required=True, help='Output directory for coverage and snowballing ledgers')
    survey_coverage.add_argument('--force', action='store_true')
    survey_coverage.set_defaults(func=cmd_survey)
    survey_reviewed_packet = survey_sub.add_parser(
        'compose-reviewed-final-packet',
        help='Compose the current immutable reviewed packet for hostile review',
        description='Replay the current selected queue, packet, coverage, four reviewed sidecars, merge, and exact claim evidence into one immutable packet. This does not establish prose readiness, literature completeness, or scientific correctness.',
    )
    survey_reviewed_packet.add_argument('--mission-root', required=True, help='Current mission root; external replay authority')
    survey_reviewed_packet.add_argument('--review-queue', required=True, help='Current selected V2 review_queue.json')
    survey_reviewed_packet.add_argument('--packet-dir', required=True, help='Original packet directory recorded by current mission control')
    survey_reviewed_packet.add_argument('--anchor-dir', required=True, help='Anchor directory recorded by current mission control')
    survey_reviewed_packet.add_argument('--local-evidence-root', help='Mission-local evidence root required only for reviewed project-derivation or implementation-evidence claims')
    survey_reviewed_packet.add_argument('--out', required=True, help='Must be <mission-root>/reviewed_final_packet')
    survey_reviewed_packet.add_argument('--force', action='store_true')
    survey_reviewed_packet.set_defaults(func=cmd_survey)
    survey_hostile = survey_sub.add_parser(
        'hostile-review',
        help='Gate reviewed-scope prose readiness from one replay-valid reviewed packet',
        description='Replay the immutable reviewed final packet against current external mission authority and write one authoritative hostile result plus a digest-bound readiness view. This does not run live expansion or establish literature completeness, product readiness, or scientific correctness.',
    )
    survey_hostile.add_argument('--reviewed-final-packet', required=True, help='Fixed mission-local reviewed_final_packet.json; raw reviewed_evidence_status.json is not accepted')
    survey_hostile.add_argument('--mission-root', required=True, help='Current mission root; external replay authority')
    survey_hostile.add_argument('--review-queue', required=True, help='Current selected V2 review_queue.json')
    survey_hostile.add_argument('--packet-dir', required=True, help='Original packet directory recorded by current mission control')
    survey_hostile.add_argument('--anchor-dir', required=True, help='Anchor directory recorded by current mission control')
    survey_hostile.add_argument('--local-evidence-root', help='Mission-local evidence root required only for reviewed project-derivation or implementation-evidence claims')
    survey_hostile.add_argument('--out', required=True, help='Output directory for hostile_review_result.json and final_packet_readiness.json')
    survey_hostile.add_argument('--force', action='store_true')
    survey_hostile.set_defaults(func=cmd_survey)
    survey_run = survey_sub.add_parser(
        'run-public-source-workflow',
        help='Supervise the public-source survey workflow with one public-discovery confirmation',
        description='Supervise the public-source survey workflow from a topic alone or from topic+seed. Topic-only mode records a mission-bound bootstrap outcome without fabricating a paper seed. --confirm-public-discovery records the durable mission confirmation; it does not allow credentials, private databases, paid model workers, hidden evaluator material, unbounded crawling, claim support from metadata, or final prose readiness.',
    )
    survey_run.add_argument('--topic', required=True)
    survey_run.add_argument('--seed', action='append', default=None, help='Optional seed paper identifier; repeat for multiple seeds. Omission selects topic-only bootstrap mode; an explicit empty value remains invalid.')
    survey_run.add_argument('--out', required=True, help='Output directory for mission_control.json and local orchestration artifacts')
    survey_run.add_argument(
        '--run-safe-local',
        action='store_true',
        help=(
            'Run the bounded typed local supervisor through every currently eligible deterministic stage; '
            'stops before live/API/download, source transport, or human-review actions'
        ),
    )
    survey_run.add_argument('--confirm-public-discovery', action='store_true', help='Record the single mission confirmation for bounded public discovery and run implemented bounded discovery steps such as public metadata')
    survey_run.add_argument('--resume', action='store_true', help='Reuse existing local mission artifacts and discover reviewed sidecars without regenerating review_queue.json or running live/API/download actions')
    survey_run.add_argument('--metadata-dir', help='Existing public metadata ledger directory, if already approved and available')
    survey_run.add_argument('--source-status-dir', help='Existing Phase 4 source intake status directory, if already approved and available')
    survey_run.add_argument('--anchor-dir', help='Existing Phase 5 source-anchor directory, if already available')
    survey_run.add_argument('--packet-dir', help='Existing or intended public-source packet directory')
    survey_run.add_argument('--coverage-dir', help='Existing coverage-ledger directory for local resume discovery')
    survey_run.add_argument('--reviewed-claims-dir', help='Existing reviewed_claims.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-source-safety-dir', help='Existing reviewed_source_safety.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-omissions-dir', help='Existing reviewed_omission_risks.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-workflow-blockers-dir', help='Existing reviewed_workflow_blockers.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-evidence-dir', help='Existing reviewed_evidence_status.json merge directory for local resume discovery')
    survey_run.add_argument('--local-evidence-root', help='Mission-local root used only to replay reviewed project-derivation or implementation-evidence claims')
    survey_run.add_argument('--force', action='store_true')
    survey_run.set_defaults(func=cmd_survey)
    survey_claim_review = survey_sub.add_parser(
        'import-claim-review',
        help='Validate reviewed claim decisions from review_queue.json without marking prose or source safety ready',
        description='Import reviewed claim decisions from a local review_queue.json sidecar. This validates reviewed anchor-mapped claim rows but does not run live lookup, clear source safety, resolve omissions, or mark final prose ready.',
    )
    survey_claim_review.add_argument('--review-queue', required=True, help='Path to review_queue.json from run-public-source-workflow')
    survey_claim_review.add_argument('--decisions', required=True, help='JSON file containing reviewed claim decisions')
    survey_claim_review.add_argument('--out', required=True, help='Output directory for reviewed_claims.json')
    survey_claim_review.add_argument('--human-attestation-receipt', help='Validated M22 human receipt for a V4 human decision envelope')
    survey_claim_review.add_argument('--force', action='store_true')
    survey_claim_review.set_defaults(func=cmd_survey)
    survey_source_safety_review = survey_sub.add_parser(
        'import-source-safety-review',
        help='Validate reviewed source-safety decisions without marking final prose ready',
        description='Import reviewed source-safety decisions from a local review_queue.json sidecar. This validates evidence-bearing source-safety rows but does not run live lookup, resolve omissions, merge claims, or mark final prose ready.',
    )
    survey_source_safety_review.add_argument('--review-queue', required=True, help='Path to review_queue.json from run-public-source-workflow')
    survey_source_safety_review.add_argument('--decisions', required=True, help='JSON file containing reviewed source-safety decisions')
    survey_source_safety_review.add_argument('--out', required=True, help='Output directory for reviewed_source_safety.json')
    survey_source_safety_review.add_argument('--human-attestation-receipt', help='Validated M22 human receipt for a V4 human decision envelope')
    survey_source_safety_review.add_argument('--force', action='store_true')
    survey_source_safety_review.set_defaults(func=cmd_survey)
    survey_omission_review = survey_sub.add_parser(
        'import-omission-review',
        help='Validate reviewed omission-risk decisions without claiming literature completeness',
        description='Import reviewed omission-risk decisions from a local review_queue.json sidecar. This validates rationale-bearing omission rows but does not run live lookup, merge claims, clear source safety, claim literature completeness, or mark final prose ready.',
    )
    survey_omission_review.add_argument('--review-queue', required=True, help='Path to review_queue.json from run-public-source-workflow')
    survey_omission_review.add_argument('--decisions', required=True, help='JSON file containing reviewed omission-risk decisions')
    survey_omission_review.add_argument('--out', required=True, help='Output directory for reviewed_omission_risks.json')
    survey_omission_review.add_argument('--force', action='store_true')
    survey_omission_review.set_defaults(func=cmd_survey)
    survey_workflow_blocker_review = survey_sub.add_parser(
        'import-workflow-blocker-review',
        help='Validate exact workflow-blocker dispositions without clearing upstream or prose gates',
        description='Import decisions for every current workflow_blocker queue item. Review-resolvable blockers require the exact embedded current evidence scope; upstream-only blockers must remain open. This does not run live lookup or mark final prose ready.',
    )
    survey_workflow_blocker_review.add_argument('--review-queue', required=True, help='Path to the selected review_queue.json')
    survey_workflow_blocker_review.add_argument('--decisions', required=True, help='Bound V2 JSON decision envelope for workflow blockers')
    survey_workflow_blocker_review.add_argument('--out', required=True, help='Output directory for reviewed_workflow_blockers.json')
    survey_workflow_blocker_review.add_argument('--force', action='store_true')
    survey_workflow_blocker_review.set_defaults(func=cmd_survey)
    survey_merge_reviewed = survey_sub.add_parser(
        'merge-reviewed-evidence',
        help='Merge reviewed sidecars into exact readiness or blocker status',
        description='Merge exact reviewed claim, source-safety, omission, and workflow-blocker sidecars with selected-queue provenance. This does not run live lookup, emit final prose readiness, or establish product/scientific readiness.',
    )
    survey_merge_reviewed.add_argument('--review-queue', required=True, help='Path to review_queue.json used by all sidecars')
    survey_merge_reviewed.add_argument('--reviewed-claims', required=True, help='Path to reviewed_claims.json')
    survey_merge_reviewed.add_argument('--reviewed-source-safety', required=True, help='Path to reviewed_source_safety.json')
    survey_merge_reviewed.add_argument('--reviewed-omissions', required=True, help='Path to reviewed_omission_risks.json')
    survey_merge_reviewed.add_argument('--reviewed-workflow-blockers', required=True, help='Path to reviewed_workflow_blockers.json')
    survey_merge_reviewed.add_argument('--out', required=True, help='Output directory for reviewed_evidence_status.json')
    survey_merge_reviewed.add_argument('--force', action='store_true')
    survey_merge_reviewed.set_defaults(func=cmd_survey)
    survey_prepare_human = survey_sub.add_parser(
        "prepare-human-review",
        help="Prepare an exact non-attesting operator packet for the selected review queue",
        description="Write the exact machine review packet, an explicitly incomplete self-attestation template, and plain-language Markdown/CSV review materials. This performs no review, makes no network call, and cannot mark evidence or prose ready.",
    )
    survey_prepare_human.add_argument("--review-queue", required=True, help="Current selected review_queue.json")
    survey_prepare_human.add_argument("--out", required=True, help="Fresh output directory for the packet and unattested template")
    survey_prepare_human.add_argument("--force", action="store_true")
    survey_prepare_human.set_defaults(func=cmd_survey)
    survey_validate_human = survey_sub.add_parser(
        "validate-human-attestation",
        help="Bind a completed human self-attestation to four exact decision files",
        description="Validate a real person's self-attestation, current queue lineage, exact four-type decision coverage, reviewer consistency, privacy/conflict declarations, and file hashes. Decision semantics remain subject to the existing import commands; this is not identity proof or prose readiness.",
    )
    survey_validate_human.add_argument("--review-queue", required=True)
    survey_validate_human.add_argument("--packet", required=True)
    survey_validate_human.add_argument("--attestation", required=True)
    survey_validate_human.add_argument("--claim-decisions", required=True)
    survey_validate_human.add_argument("--source-safety-decisions", required=True)
    survey_validate_human.add_argument("--omission-decisions", required=True)
    survey_validate_human.add_argument("--workflow-blocker-decisions", required=True)
    survey_validate_human.add_argument("--out", required=True)
    survey_validate_human.add_argument("--force", action="store_true")
    survey_validate_human.set_defaults(func=cmd_survey)
    survey_render_human = survey_sub.add_parser(
        "render-human-review",
        help="Render plain-language worksheets for an existing exact review packet",
        description="Render reviewer-facing Markdown/CSV materials from the current packet without changing packet JSON, queue lineage, or packet hashes.",
    )
    survey_render_human.add_argument("--packet", required=True, help="Existing human_review_packet.json")
    survey_render_human.add_argument("--out", help="Output directory; defaults to the packet directory")
    survey_render_human.add_argument("--force", action="store_true")
    survey_render_human.set_defaults(func=cmd_survey)
    survey_qualitative = survey_sub.add_parser(
        "qualitative-assessment",
        help="Write a concise source-grounded merits/concerns/uncertainties assessment",
        description="Record a bounded qualitative assessment. This is the active M22 scholarly review representation; it never clears provenance, source-safety, claim-support, or prose gates.",
    )
    survey_qualitative.add_argument("--subject-id", required=True)
    survey_qualitative.add_argument("--assessment-type", required=True, choices=["paper", "claim", "omission"])
    survey_qualitative.add_argument("--summary", required=True)
    survey_qualitative.add_argument("--merit", action="append", required=True)
    survey_qualitative.add_argument("--concern", action="append", required=True)
    survey_qualitative.add_argument("--uncertainty", action="append", required=True)
    survey_qualitative.add_argument("--evidence-ref", action="append", required=True)
    survey_qualitative.add_argument("--next-action", required=True)
    survey_qualitative.add_argument("--out", required=True, help="Output JSON assessment path")
    survey_qualitative.add_argument("--force", action="store_true")
    survey_qualitative.set_defaults(func=cmd_survey)

    surveybench = sub.add_parser('surveybench', help='Run offline synthetic and online-replay SurveyBench fixtures')
    surveybench_sub = surveybench.add_subparsers(dest='surveybench_action', required=True)
    surveybench_run = surveybench_sub.add_parser('run', help='Run an offline SurveyBench task and emit JSON')
    surveybench_run.add_argument('--task', required=True)
    surveybench_run.add_argument('--actual-dir')
    surveybench_run.add_argument('--output')
    surveybench_run.set_defaults(func=cmd_surveybench)
    surveybench_manifest = surveybench_sub.add_parser('local-manifest', help='Validate a redacted local SurveyBench manifest')
    surveybench_manifest.add_argument('--manifest', required=True)
    surveybench_manifest.add_argument('--output')
    surveybench_manifest.set_defaults(func=cmd_surveybench)
    surveybench_replay_call = surveybench_sub.add_parser('replay-call', help='Call an offline online-replay endpoint and append a budgeted event log')
    surveybench_replay_call.add_argument('--task', required=True)
    surveybench_replay_call.add_argument('--endpoint', required=True)
    surveybench_replay_call.add_argument('--session', required=True)
    surveybench_replay_call.add_argument('--request-id')
    surveybench_replay_call.set_defaults(func=cmd_surveybench)
    surveybench_replay_audit = surveybench_sub.add_parser('replay-audit', help='Audit an online-replay fixture for interface and leakage issues')
    surveybench_replay_audit.add_argument('--task', required=True)
    surveybench_replay_audit.add_argument('--output')
    surveybench_replay_audit.set_defaults(func=cmd_surveybench)
    surveybench_replay_transcript = surveybench_sub.add_parser('replay-transcript', help='Build an offline replay transcript from a trusted session event log')
    surveybench_replay_transcript.add_argument('--task', required=True)
    surveybench_replay_transcript.add_argument('--session', required=True)
    surveybench_replay_transcript.add_argument('--output')
    surveybench_replay_transcript.set_defaults(func=cmd_surveybench)
    surveybench_replay_score = surveybench_sub.add_parser('replay-score', help='Score an online-replay submission packet against hidden fixture gold and an event log')
    surveybench_replay_score.add_argument('--task', required=True)
    surveybench_replay_score.add_argument('--actual-dir', required=True)
    surveybench_replay_score.add_argument('--event-log', required=True)
    surveybench_replay_score.add_argument('--gold-dir', required=True)
    surveybench_replay_score.add_argument('--output')
    surveybench_replay_score.set_defaults(func=cmd_surveybench)
    surveybench_score_prose = surveybench_sub.add_parser('score-prose', help='Score survey prose annotations after replay evidence-packet hard gates')
    surveybench_score_prose.add_argument('--task', required=True)
    surveybench_score_prose.add_argument('--actual-dir', required=True)
    surveybench_score_prose.add_argument('--event-log', required=True)
    surveybench_score_prose.add_argument('--gold-dir', required=True)
    surveybench_score_prose.add_argument('--prose', required=True)
    surveybench_score_prose.add_argument('--output')
    surveybench_score_prose.set_defaults(func=cmd_surveybench)
    surveybench_restricted_workspace = surveybench_sub.add_parser('restricted-workspace', help='Create a restricted SurveyBench replay-call workspace')
    surveybench_restricted_workspace.add_argument('--repo-root', default='.')
    surveybench_restricted_workspace.add_argument('--workspace', required=True)
    surveybench_restricted_workspace.add_argument('--profile', default='default')
    surveybench_restricted_workspace.add_argument('--output')
    surveybench_restricted_workspace.add_argument('--force', action='store_true')
    surveybench_restricted_workspace.set_defaults(func=cmd_surveybench)
    surveybench_restricted_launcher = surveybench_sub.add_parser('restricted-launcher-dry-run', help='Create a restricted SurveyBench launcher dry-run record without launching a subject')
    surveybench_restricted_launcher.add_argument('--workspace', required=True)
    surveybench_restricted_launcher.add_argument('--profile', default='default')
    surveybench_restricted_launcher.add_argument('--subject-agent', default='<unlaunched-subject-agent>')
    surveybench_restricted_launcher.add_argument('--output')
    surveybench_restricted_launcher.set_defaults(func=cmd_surveybench)
    surveybench_subject_binding = surveybench_sub.add_parser('subject-binding-preflight', help='Build a no-launch Claude subject permission binding preflight')
    surveybench_subject_binding.add_argument('--workspace', required=True)
    surveybench_subject_binding.add_argument('--profile', default='default')
    surveybench_subject_binding.add_argument('--subject-agent', default='claude-code-sonnet-subject')
    surveybench_subject_binding.add_argument('--model-id', default='claude-sonnet-4-6')
    surveybench_subject_binding.add_argument('--permission-mode', default='dontAsk')
    surveybench_subject_binding.add_argument('--subject-transport', default='claude-code')
    surveybench_subject_binding.add_argument('--representative-endpoint', default='search')
    surveybench_subject_binding.add_argument('--output')
    surveybench_subject_binding.set_defaults(func=cmd_surveybench)
    surveybench_launch_approval = surveybench_sub.add_parser('launch-approval-packet', help='Build and preflight a real-subject approval packet without launching')
    surveybench_launch_approval.add_argument('--launcher-dry-run', required=True)
    surveybench_launch_approval.add_argument('--subject-agent', required=True)
    surveybench_launch_approval.add_argument('--model-id', required=True)
    surveybench_launch_approval.add_argument('--subject-transport')
    surveybench_launch_approval.add_argument('--wrapper-command', nargs='+')
    surveybench_launch_approval.add_argument('--wrapper-command-json')
    surveybench_launch_approval.add_argument('--subject-binding-preflight')
    surveybench_launch_approval.add_argument('--budget-cap-json', required=True)
    surveybench_launch_approval.add_argument('--transcript-path', required=True)
    surveybench_launch_approval.add_argument('--denied-tool-capture-path', required=True)
    surveybench_launch_approval.add_argument('--cli-version', required=True)
    surveybench_launch_approval.add_argument('--output')
    surveybench_launch_approval.set_defaults(func=cmd_surveybench)
    surveybench_launch_enforcement = surveybench_sub.add_parser('launch-enforcement-preflight', help='Build launch enforcement/no-drift preflight without launching')
    surveybench_launch_enforcement.add_argument('--approval-packet', required=True)
    surveybench_launch_enforcement.add_argument('--output')
    surveybench_launch_enforcement.set_defaults(func=cmd_surveybench)
    surveybench_next_action = surveybench_sub.add_parser('next-action', help='Emit the next structured SurveyBench replay action from visible task/session/output state')
    surveybench_next_action.add_argument('--task', required=True)
    surveybench_next_action.add_argument('--session')
    surveybench_next_action.add_argument('--actual-dir')
    surveybench_next_action.set_defaults(func=cmd_surveybench)
    surveybench_packet_template = surveybench_sub.add_parser('packet-template', help='Emit schema-only SurveyBench packet skeletons')
    surveybench_packet_template.add_argument('--task', required=True)
    surveybench_packet_template.add_argument('--output-dir')
    surveybench_packet_template.add_argument('--write-files', action='store_true')
    surveybench_packet_template.set_defaults(func=cmd_surveybench)
    surveybench_packet_compose = surveybench_sub.add_parser('packet-compose', help='Compose a visible SurveyBench evidence packet from replay evidence')
    surveybench_packet_compose.add_argument('--task', required=True)
    surveybench_packet_compose.add_argument('--output-dir', required=True)
    surveybench_packet_compose.add_argument('--session')
    surveybench_packet_compose.add_argument('--responses-dir')
    surveybench_packet_compose.add_argument('--write-files', action='store_true')
    surveybench_packet_compose.set_defaults(func=cmd_surveybench)
    surveybench_cluster_hints = surveybench_sub.add_parser('cluster-hints', help='Emit visible replay-derived SurveyBench cluster guidance')
    surveybench_cluster_hints.add_argument('--task', required=True)
    surveybench_cluster_hints.add_argument('--responses-dir')
    surveybench_cluster_hints.set_defaults(func=cmd_surveybench)
    surveybench_ready = surveybench_sub.add_parser('ready-for-prose', help='Check whether visible replay artifacts are ready for survey prose drafting')
    surveybench_ready.add_argument('--task', required=True)
    surveybench_ready.add_argument('--actual-dir', required=True)
    surveybench_ready.add_argument('--session')
    surveybench_ready.set_defaults(func=cmd_surveybench)
    surveybench_launch_record = surveybench_sub.add_parser('launch-record-template', help='Emit a schema-only blinded rerun launch record template')
    surveybench_launch_record.add_argument('--task', required=True)
    surveybench_launch_record.set_defaults(func=cmd_surveybench)

    arxiv_batch = sub.add_parser('arxiv-batch', help='Plan and run bounded arXiv batch intake')
    arxiv_batch_sub = arxiv_batch.add_subparsers(dest='arxiv_batch_action', required=True)
    arxiv_batch_discover = arxiv_batch_sub.add_parser('discover')
    arxiv_batch_discover.add_argument('--query', required=True)
    arxiv_batch_discover.add_argument('--max-candidates', type=int, required=True)
    arxiv_batch_discover.add_argument('--timeout-seconds', type=int, default=30)
    arxiv_batch_discover.add_argument('--output-candidate-file', required=True)
    arxiv_batch_discover.set_defaults(func=cmd_arxiv_batch)
    arxiv_batch_plan = arxiv_batch_sub.add_parser('plan')
    arxiv_batch_plan.add_argument('--ids')
    arxiv_batch_plan.add_argument('--query')
    arxiv_batch_plan.add_argument('--candidate-file')
    arxiv_batch_plan.add_argument('--max-papers', type=int, required=True)
    arxiv_batch_plan.add_argument('--destination', choices=['source', 'inbox'], default='source')
    arxiv_batch_plan.add_argument('--operation', choices=['source_fetch', 'pdf_inbox_download', 'metadata_only'], default='source_fetch')
    arxiv_batch_plan.set_defaults(func=cmd_arxiv_batch)
    arxiv_batch_candidate = arxiv_batch_sub.add_parser('candidate-file')
    arxiv_batch_candidate_sub = arxiv_batch_candidate.add_subparsers(dest='candidate_file_action', required=True)
    arxiv_batch_candidate_inspect = arxiv_batch_candidate_sub.add_parser('inspect')
    arxiv_batch_candidate_inspect.add_argument('--path', required=True)
    arxiv_batch_candidate_inspect.set_defaults(func=cmd_arxiv_batch)
    arxiv_batch_run = arxiv_batch_sub.add_parser('run')
    arxiv_batch_run.add_argument('--grant-id', required=True)
    arxiv_batch_run.add_argument('--plan-hash', required=True)
    arxiv_batch_run.add_argument('--ids')
    arxiv_batch_run.add_argument('--candidate-file')
    arxiv_batch_run.add_argument('--plan-file')
    arxiv_batch_run.add_argument('--plan-file-sha256')
    arxiv_batch_run.set_defaults(func=cmd_arxiv_batch)
    arxiv_batch_pdf_run = arxiv_batch_sub.add_parser('pdf-run')
    arxiv_batch_pdf_run.add_argument('--grant-id', required=True)
    arxiv_batch_pdf_run.add_argument('--plan-hash', required=True)
    arxiv_batch_pdf_run.add_argument('--candidate-file', required=True)
    arxiv_batch_pdf_run.add_argument('--timeout-seconds', type=int, default=30)
    arxiv_batch_pdf_run.set_defaults(func=cmd_arxiv_batch)

    release_artifacts = sub.add_parser('release-artifacts', help='Inspect release artifact manifests')
    release_artifacts_sub = release_artifacts.add_subparsers(dest='release_artifacts_action', required=True)
    release_artifacts_manifest_cmd = release_artifacts_sub.add_parser('manifest')
    release_artifacts_manifest_cmd.add_argument('--dist-dir')
    release_artifacts_manifest_cmd.set_defaults(func=cmd_release_artifacts)

    onboarding_report_cmd = sub.add_parser('onboarding-report', help='Emit individual release onboarding checklist')
    onboarding_report_cmd.set_defaults(func=cmd_onboarding_report)

    platform_cmd = sub.add_parser('platform-status', help='Show local platform support status')
    platform_cmd.set_defaults(func=cmd_platform_status)

    ingest = sub.add_parser('ingest')
    ingest.add_argument('--pdf')
    ingest.add_argument('--query')
    ingest.add_argument('--arxiv-id')
    ingest.set_defaults(func=cmd_ingest)

    find = sub.add_parser('find')
    find.add_argument('--query', required=True)
    find.add_argument('--review-status')
    find.add_argument('--author')
    find.add_argument('--year', type=int)
    find.set_defaults(func=cmd_find)

    show = sub.add_parser('show')
    show.add_argument('--paper-id', required=True)
    show.set_defaults(func=cmd_show)

    export_context = sub.add_parser('export-context')
    export_context.add_argument('--output')
    export_context.add_argument('--review-status')
    export_context.set_defaults(func=cmd_export_context)

    review_list = sub.add_parser('review-list')
    review_list.add_argument('--status')
    review_list.add_argument('--json', action='store_true')
    review_list.set_defaults(func=cmd_review_list)

    review_show = sub.add_parser('review-show')
    review_show.add_argument('--paper-id', required=True)
    review_show.set_defaults(func=cmd_review_show)

    review_mark = sub.add_parser('review-mark')
    review_mark.add_argument('--paper-id', required=True)
    review_mark.add_argument('--status', required=True)
    review_mark.set_defaults(func=cmd_review_mark)

    review_write = sub.add_parser('review-write', help='Prototype explicit confirmation flow for review-state writes')
    review_write_sub = review_write.add_subparsers(dest='review_write_action', required=True)
    review_write_status_cmd = review_write_sub.add_parser('status')
    review_write_status_cmd.set_defaults(func=cmd_review_write)
    review_write_propose = review_write_sub.add_parser('propose-status')
    review_write_propose.add_argument('--paper-id', required=True)
    review_write_propose.add_argument('--status', required=True)
    review_write_propose.add_argument('--expires-minutes', type=int, default=30)
    review_write_propose.set_defaults(func=cmd_review_write)
    review_write_apply = review_write_sub.add_parser('apply')
    review_write_apply.add_argument('--confirmation-id', required=True)
    review_write_apply.set_defaults(func=cmd_review_write)
    review_write_cleanup = review_write_sub.add_parser('cleanup-expired')
    review_write_cleanup.add_argument('--apply', action='store_true')
    review_write_cleanup.set_defaults(func=cmd_review_write)

    link = sub.add_parser('link-add')
    link.add_argument('--paper-id', required=True)
    link.add_argument('--target', required=True)
    link.add_argument('--relationship', required=True)
    link.add_argument('--target-type', default='code_file')
    link.add_argument('--source-type', default='paper')
    link.add_argument('--source-ref')
    link.add_argument('--target-ref')
    link.set_defaults(func=cmd_link_add)

    artifact_paths_cmd = sub.add_parser('artifact-paths')
    artifact_paths_cmd.set_defaults(func=cmd_artifact_paths)

    industrial_validate = sub.add_parser('industrial-validate')
    industrial_validate.set_defaults(func=cmd_industrial_validate)

    domain_templates = sub.add_parser('domain-templates')
    domain_templates_sub = domain_templates.add_subparsers(dest='template_action', required=True)
    domain_templates_list = domain_templates_sub.add_parser('list')
    domain_templates_list.set_defaults(func=cmd_domain_templates)
    domain_templates_show = domain_templates_sub.add_parser('show')
    domain_templates_show.add_argument('--template-id', required=True)
    domain_templates_show.set_defaults(func=cmd_domain_templates)

    derivation = sub.add_parser('derivation')
    derivation_sub = derivation.add_subparsers(dest='derivation_action', required=True)
    derivation_create = derivation_sub.add_parser('create')
    derivation_create.add_argument('--paper-id', required=True)
    derivation_create.add_argument('--title', required=True)
    derivation_create.add_argument('--template-id')
    derivation_create.set_defaults(func=cmd_derivation)
    derivation_show = derivation_sub.add_parser('show')
    derivation_show.add_argument('--artifact-id', required=True)
    derivation_show.set_defaults(func=cmd_derivation)
    derivation_append = derivation_sub.add_parser('append')
    derivation_append.add_argument('--artifact-id', required=True)
    derivation_append.add_argument('--field', required=True)
    derivation_append.add_argument('--value', required=True)
    derivation_append.set_defaults(func=cmd_derivation)
    derivation_notation = derivation_sub.add_parser('notation')
    derivation_notation.add_argument('--artifact-id', required=True)
    derivation_notation.add_argument('--symbol', required=True)
    derivation_notation.add_argument('--meaning', required=True)
    derivation_notation.set_defaults(func=cmd_derivation)
    derivation_link_steps = derivation_sub.add_parser('link-steps')
    derivation_link_steps.add_argument('--artifact-id', required=True)
    derivation_link_steps.add_argument('--step-id', required=True)
    derivation_link_steps.add_argument('--depends-on', required=True)
    derivation_link_steps.set_defaults(func=cmd_derivation)
    derivation_comment = derivation_sub.add_parser('comment')
    derivation_comment.add_argument('--artifact-id', required=True)
    derivation_comment.add_argument('--target-id', required=True)
    derivation_comment.add_argument('--comment', required=True)
    derivation_comment.add_argument('--reviewer')
    derivation_comment.set_defaults(func=cmd_derivation)

    experiment = sub.add_parser('experiment')
    experiment_sub = experiment.add_subparsers(dest='experiment_action', required=True)
    experiment_checklists = experiment_sub.add_parser('checklists')
    experiment_checklists.set_defaults(func=cmd_experiment)
    experiment_checklist_show = experiment_sub.add_parser('checklist-show')
    experiment_checklist_show.add_argument('--template-id', required=True)
    experiment_checklist_show.set_defaults(func=cmd_experiment)
    experiment_create = experiment_sub.add_parser('create')
    experiment_create.add_argument('--paper-id', required=True)
    experiment_create.add_argument('--claim-id', required=True)
    experiment_create.add_argument('--checklist-id', required=True)
    experiment_create.set_defaults(func=cmd_experiment)
    experiment_show = experiment_sub.add_parser('show')
    experiment_show.add_argument('--artifact-id', required=True)
    experiment_show.set_defaults(func=cmd_experiment)
    experiment_link = experiment_sub.add_parser('link-claim')
    experiment_link.add_argument('--paper-id', required=True)
    experiment_link.add_argument('--claim-id', required=True)
    experiment_link.add_argument('--experiment-id', required=True)
    experiment_link.set_defaults(func=cmd_experiment)
    experiment_run = experiment_sub.add_parser('record-run')
    experiment_run.add_argument('--artifact-id', required=True)
    experiment_run.add_argument('--run-label', required=True)
    experiment_run.add_argument('--seed', required=True)
    experiment_run.add_argument('--environment', required=True)
    experiment_run.add_argument('--diagnostic', action='append', default=[])
    experiment_run.add_argument('--result-summary')
    experiment_run.add_argument('--acceptance-status', default='requires_review')
    experiment_run.add_argument('--dataset-hash')
    experiment_run.add_argument('--model-hash')
    experiment_run.set_defaults(func=cmd_experiment)

    graph_report = sub.add_parser('graph-report')
    graph_report_sub = graph_report.add_subparsers(dest='graph_report_action', required=True)
    graph_report_build = graph_report_sub.add_parser('build')
    graph_report_build.add_argument('--paper-id', required=True)
    graph_report_build.set_defaults(func=cmd_graph_report)
    graph_report_show = graph_report_sub.add_parser('show')
    graph_report_show.add_argument('--artifact-id', required=True)
    graph_report_show.set_defaults(func=cmd_graph_report)
    graph_report_enrich = graph_report_sub.add_parser('enrich')
    graph_report_enrich.add_argument('--artifact-id', required=True)
    graph_report_enrich.set_defaults(func=cmd_graph_report)

    review_meta = sub.add_parser('review-meta')
    review_meta_sub = review_meta.add_subparsers(dest='review_meta_action', required=True)
    review_meta_show = review_meta_sub.add_parser('show')
    review_meta_show.add_argument('--paper-id', required=True)
    review_meta_show.set_defaults(func=cmd_review_meta)
    review_meta_set = review_meta_sub.add_parser('set')
    review_meta_set.add_argument('--paper-id', required=True)
    review_meta_set.add_argument('--field', required=True)
    review_meta_set.add_argument('--value', required=True)
    review_meta_set.set_defaults(func=cmd_review_meta)
    review_meta_list = review_meta_sub.add_parser('list')
    review_meta_list.set_defaults(func=cmd_review_meta)

    benchmark_manifest = sub.add_parser('benchmark-manifest')
    benchmark_sub = benchmark_manifest.add_subparsers(dest='benchmark_action', required=True)
    benchmark_create = benchmark_sub.add_parser('create')
    benchmark_create.add_argument('--manifest-id', required=True)
    benchmark_create.add_argument('--family', required=True)
    benchmark_create.add_argument('--fixture', action='append', default=[])
    benchmark_create.set_defaults(func=cmd_benchmark_manifest)
    benchmark_show = benchmark_sub.add_parser('show')
    benchmark_show.add_argument('--manifest-id', required=True)
    benchmark_show.set_defaults(func=cmd_benchmark_manifest)
    benchmark_run = benchmark_sub.add_parser('run')
    benchmark_run.add_argument('--manifest-id', required=True)
    benchmark_run.set_defaults(func=cmd_benchmark_manifest)

    synthesis = sub.add_parser('synthesis')
    synthesis_sub = synthesis.add_subparsers(dest='synthesis_action', required=True)
    synthesis_propose = synthesis_sub.add_parser('propose')
    synthesis_propose.add_argument('--paper-id', required=True)
    synthesis_propose.add_argument('--kind', required=True)
    synthesis_propose.set_defaults(func=cmd_synthesis)
    synthesis_show = synthesis_sub.add_parser('show')
    synthesis_show.add_argument('--artifact-id', required=True)
    synthesis_show.set_defaults(func=cmd_synthesis)

    governance = sub.add_parser('governance')
    governance_sub = governance.add_subparsers(dest='governance_action', required=True)
    governance_build = governance_sub.add_parser('build')
    governance_build.add_argument('--paper-id', required=True)
    governance_build.set_defaults(func=cmd_governance)
    governance_show = governance_sub.add_parser('show')
    governance_show.add_argument('--artifact-id', required=True)
    governance_show.set_defaults(func=cmd_governance)

    job = sub.add_parser('job')
    job_sub = job.add_subparsers(dest='job_action', required=True)
    job_create = job_sub.add_parser('create')
    job_create.add_argument('--job-type', required=True)
    job_create.add_argument('--paper-id')
    job_create.set_defaults(func=cmd_job)
    job_show = job_sub.add_parser('show')
    job_show.add_argument('--artifact-id', required=True)
    job_show.set_defaults(func=cmd_job)

    dashboard_export_cmd = sub.add_parser('dashboard-export')
    dashboard_export_cmd.add_argument('--output')
    dashboard_export_cmd.set_defaults(func=cmd_dashboard_export)

    traceability = sub.add_parser('traceability')
    traceability_sub = traceability.add_subparsers(dest='traceability_action', required=True)
    traceability_build = traceability_sub.add_parser('build')
    traceability_build.add_argument('--paper-id', required=True)
    traceability_build.set_defaults(func=cmd_traceability)
    traceability_show = traceability_sub.add_parser('show')
    traceability_show.add_argument('--artifact-id', required=True)
    traceability_show.set_defaults(func=cmd_traceability)

    model_policy = sub.add_parser('model-policy')
    model_policy_sub = model_policy.add_subparsers(dest='model_policy_action', required=True)
    model_policy_create = model_policy_sub.add_parser('create')
    model_policy_create.add_argument('--policy-id', required=True)
    model_policy_create.set_defaults(func=cmd_model_policy)
    model_policy_show = model_policy_sub.add_parser('show')
    model_policy_show.add_argument('--policy-id', required=True)
    model_policy_show.set_defaults(func=cmd_model_policy)
    model_policy_check = model_policy_sub.add_parser('check-synthesis')
    model_policy_check.add_argument('--policy-id', required=True)
    model_policy_check.set_defaults(func=cmd_model_policy)

    collaboration = sub.add_parser('collaboration')
    collaboration_sub = collaboration.add_subparsers(dest='collaboration_action', required=True)
    collaboration_create = collaboration_sub.add_parser('create')
    collaboration_create.add_argument('--workspace-id', required=True)
    collaboration_create.set_defaults(func=cmd_collaboration)
    collaboration_show = collaboration_sub.add_parser('show')
    collaboration_show.add_argument('--workspace-id', required=True)
    collaboration_show.set_defaults(func=cmd_collaboration)
    collaboration_update = collaboration_sub.add_parser('update')
    collaboration_update.add_argument('--workspace-id', required=True)
    collaboration_update.add_argument('--action', required=True)
    collaboration_update.add_argument('--value', required=True)
    collaboration_update.add_argument('--target')
    collaboration_update.set_defaults(func=cmd_collaboration)

    artifact_index = sub.add_parser('artifact-index')
    artifact_index_sub = artifact_index.add_subparsers(dest='artifact_index_action', required=True)
    artifact_index_build = artifact_index_sub.add_parser('build')
    artifact_index_build.add_argument('--index-id', default='local_artifact_index')
    artifact_index_build.set_defaults(func=cmd_artifact_index)
    artifact_index_show = artifact_index_sub.add_parser('show')
    artifact_index_show.add_argument('--index-id', required=True)
    artifact_index_show.set_defaults(func=cmd_artifact_index)
    artifact_index_query = artifact_index_sub.add_parser('query')
    artifact_index_query.add_argument('--index-id', default='local_artifact_index')
    artifact_index_query.add_argument('--family')
    artifact_index_query.add_argument('--paper-id')
    artifact_index_query.set_defaults(func=cmd_artifact_index)

    industrial_readiness = sub.add_parser('industrial-readiness')
    readiness_sub = industrial_readiness.add_subparsers(dest='readiness_action', required=True)
    readiness_build = readiness_sub.add_parser('build')
    readiness_build.add_argument('--report-id', default='industrial_readiness')
    readiness_build.set_defaults(func=cmd_industrial_readiness)
    readiness_show = readiness_sub.add_parser('show')
    readiness_show.add_argument('--report-id', required=True)
    readiness_show.set_defaults(func=cmd_industrial_readiness)

    full_scale_plan = sub.add_parser('full-scale-plan')
    full_scale_sub = full_scale_plan.add_subparsers(dest='full_scale_action', required=True)
    full_scale_phases = full_scale_sub.add_parser('phases')
    full_scale_phases.set_defaults(func=cmd_full_scale_plan)
    full_scale_phase_show = full_scale_sub.add_parser('phase-show')
    full_scale_phase_show.add_argument('--phase-id', required=True)
    full_scale_phase_show.set_defaults(func=cmd_full_scale_plan)
    full_scale_registry_build = full_scale_sub.add_parser('registry-build')
    full_scale_registry_build.set_defaults(func=cmd_full_scale_plan)
    full_scale_registry_show = full_scale_sub.add_parser('registry-show')
    full_scale_registry_show.set_defaults(func=cmd_full_scale_plan)
    full_scale_usefulness = full_scale_sub.add_parser('usefulness-build')
    full_scale_usefulness.set_defaults(func=cmd_full_scale_plan)
    full_scale_readiness = full_scale_sub.add_parser('readiness-build')
    full_scale_readiness.set_defaults(func=cmd_full_scale_plan)

    industrial_release = sub.add_parser('industrial-release')
    industrial_release_sub = industrial_release.add_subparsers(dest='industrial_release_action', required=True)
    industrial_release_phases = industrial_release_sub.add_parser('phases')
    industrial_release_phases.set_defaults(func=cmd_industrial_release)
    industrial_release_phase_show = industrial_release_sub.add_parser('phase-show')
    industrial_release_phase_show.add_argument('--phase-id', required=True)
    industrial_release_phase_show.set_defaults(func=cmd_industrial_release)
    industrial_release_definition_build = industrial_release_sub.add_parser('definition-build')
    industrial_release_definition_build.set_defaults(func=cmd_industrial_release)
    industrial_release_definition_show = industrial_release_sub.add_parser('definition-show')
    industrial_release_definition_show.set_defaults(func=cmd_industrial_release)
    industrial_release_external = industrial_release_sub.add_parser('external-validation-build')
    industrial_release_external.add_argument('--validation-dir')
    industrial_release_external.set_defaults(func=cmd_industrial_release)
    industrial_release_publication = industrial_release_sub.add_parser('publication-check')
    industrial_release_publication.set_defaults(func=cmd_industrial_release)
    industrial_release_gate = industrial_release_sub.add_parser('gate-build')
    industrial_release_gate.set_defaults(func=cmd_industrial_release)
    industrial_release_show = industrial_release_sub.add_parser('show')
    industrial_release_show.add_argument('--artifact-id', required=True)
    industrial_release_show.set_defaults(func=cmd_industrial_release)

    tool_contract = sub.add_parser('tool-contract')
    tool_contract_sub = tool_contract.add_subparsers(dest='tool_contract_action', required=True)
    tool_contract_export = tool_contract_sub.add_parser('export')
    tool_contract_export.add_argument('--contract-id', default='local_tool_contract')
    tool_contract_export.set_defaults(func=cmd_tool_contract)
    tool_contract_show = tool_contract_sub.add_parser('show')
    tool_contract_show.add_argument('--contract-id', required=True)
    tool_contract_show.set_defaults(func=cmd_tool_contract)

    operations_policy = sub.add_parser('operations-policy')
    operations_sub = operations_policy.add_subparsers(dest='operations_action', required=True)
    operations_create = operations_sub.add_parser('create')
    operations_create.add_argument('--policy-id', default='department_operations_policy')
    operations_create.set_defaults(func=cmd_operations_policy)
    operations_show = operations_sub.add_parser('show')
    operations_show.add_argument('--policy-id', required=True)
    operations_show.set_defaults(func=cmd_operations_policy)

    sop = sub.add_parser('sop')
    sop_sub = sop.add_subparsers(dest='sop_action', required=True)
    sop_create = sop_sub.add_parser('create')
    sop_create.add_argument('--sop-id', default='department_research_sop')
    sop_create.set_defaults(func=cmd_sop)
    sop_show = sop_sub.add_parser('show')
    sop_show.add_argument('--sop-id', required=True)
    sop_show.set_defaults(func=cmd_sop)

    audit = sub.add_parser('audit-claim')
    audit.add_argument('--claim')
    audit.add_argument('--claim-file')
    audit.add_argument('--papers', nargs='*')
    audit.set_defaults(func=cmd_audit_claim)

    audit_note = sub.add_parser('audit-note')
    audit_note_sub = audit_note.add_subparsers(dest='audit_action', required=True)

    audit_note_show = audit_note_sub.add_parser('show')
    audit_note_show.add_argument('--paper-id', required=True)
    audit_note_show.set_defaults(func=cmd_audit_note)

    audit_note_set = audit_note_sub.add_parser('set')
    audit_note_set.add_argument('--paper-id', required=True)
    audit_note_set.add_argument('--field', required=True)
    audit_note_set.add_argument('--value', required=True)
    audit_note_set.set_defaults(func=cmd_audit_note)

    audit_note_append = audit_note_sub.add_parser('append')
    audit_note_append.add_argument('--paper-id', required=True)
    audit_note_append.add_argument('--field', required=True)
    audit_note_append.add_argument('--value', required=True)
    audit_note_append.set_defaults(func=cmd_audit_note)

    audit_note_remove = audit_note_sub.add_parser('remove')
    audit_note_remove.add_argument('--paper-id', required=True)
    audit_note_remove.add_argument('--field', required=True)
    audit_note_remove.add_argument('--value', required=True)
    audit_note_remove.set_defaults(func=cmd_audit_note)

    audit_note_link_section = audit_note_sub.add_parser('link-section')
    audit_note_link_section.add_argument('--paper-id', required=True)
    audit_note_link_section.add_argument('--label', required=True)
    audit_note_link_section.set_defaults(func=cmd_audit_note)

    audit_note_link_equation = audit_note_sub.add_parser('link-equation')
    audit_note_link_equation.add_argument('--paper-id', required=True)
    audit_note_link_equation.add_argument('--label', required=True)
    audit_note_link_equation.set_defaults(func=cmd_audit_note)

    audit_note_link_theorem = audit_note_sub.add_parser('link-theorem')
    audit_note_link_theorem.add_argument('--paper-id', required=True)
    audit_note_link_theorem.add_argument('--label', required=True)
    audit_note_link_theorem.set_defaults(func=cmd_audit_note)

    audit_note_link_citation = audit_note_sub.add_parser('link-citation')
    audit_note_link_citation.add_argument('--paper-id', required=True)
    audit_note_link_citation.add_argument('--citation-key', required=True)
    audit_note_link_citation.set_defaults(func=cmd_audit_note)

    discover = sub.add_parser('discover')
    discover.add_argument('--query', required=True)
    discover.add_argument('--limit', type=int, default=10)
    discover.set_defaults(func=cmd_discover)

    download_paper = sub.add_parser('download-paper')
    download_paper.add_argument('--query', required=True)
    download_paper.add_argument('--limit', type=int, default=10)
    download_paper.set_defaults(func=cmd_download_paper)

    papers_citing_cmd = sub.add_parser('papers-citing')
    papers_citing_cmd.add_argument('--paper-id', required=True)
    papers_citing_cmd.add_argument('--limit', type=int, default=10)
    papers_citing_cmd.set_defaults(func=cmd_papers_citing)

    papers_cited_by_cmd = sub.add_parser('papers-cited-by')
    papers_cited_by_cmd.add_argument('--paper-id', required=True)
    papers_cited_by_cmd.add_argument('--limit', type=int, default=10)
    papers_cited_by_cmd.set_defaults(func=cmd_papers_cited_by)

    citation_neighborhood_cmd = sub.add_parser('citation-neighborhood')
    citation_neighborhood_cmd.add_argument('--paper-id', required=True)
    citation_neighborhood_cmd.add_argument('--limit', type=int, default=5)
    citation_neighborhood_cmd.set_defaults(func=cmd_citation_neighborhood)

    citation_graph_build = sub.add_parser('citation-graph-build')
    citation_graph_build.add_argument('--paper-id', required=True)
    citation_graph_build.add_argument('--depth', type=int, default=1)
    citation_graph_build.add_argument('--limit', type=int, default=5)
    citation_graph_build.add_argument('--refresh', action='store_true')
    citation_graph_build.set_defaults(func=cmd_citation_graph_build)

    citation_graph_show = sub.add_parser('citation-graph-show')
    citation_graph_show.add_argument('--paper-id', required=True)
    citation_graph_show.set_defaults(func=cmd_citation_graph_show)

    citation_graph_export = sub.add_parser('citation-graph-export')
    citation_graph_export.add_argument('--paper-id', required=True)
    citation_graph_export.add_argument('--output', required=True)
    citation_graph_export.set_defaults(func=cmd_citation_graph_export)

    graph_node_download = sub.add_parser('graph-node-download-proposal')
    graph_node_download.add_argument('--paper-id', required=True)
    graph_node_download.add_argument('--node-id', required=True)
    graph_node_download.set_defaults(func=cmd_graph_node_download_proposal)

    inbox_list = sub.add_parser('inbox-list')
    inbox_list.add_argument('--duplicate-status')
    inbox_list.add_argument('--json', action='store_true')
    inbox_list.set_defaults(func=cmd_inbox_list)

    inbox_show = sub.add_parser('inbox-show')
    inbox_show.add_argument('--proposed-name', required=True)
    inbox_show.set_defaults(func=cmd_inbox_show)

    literature_audit_propose = sub.add_parser('literature-audit-propose')
    literature_audit_propose.add_argument('--paper-id', required=True)
    literature_audit_propose.set_defaults(func=cmd_literature_audit_propose)

    literature_audit_show = sub.add_parser('literature-audit-show')
    literature_audit_show.add_argument('--paper-id', required=True)
    literature_audit_show.set_defaults(func=cmd_literature_audit_show)

    literature_audit_approve = sub.add_parser('literature-audit-approve')
    literature_audit_approve.add_argument('--paper-id', required=True)
    literature_audit_approve.set_defaults(func=cmd_literature_audit_approve)

    parse_pdf = sub.add_parser('parse-pdf')
    parse_pdf.add_argument('--pdf', required=True)
    parse_pdf.set_defaults(func=cmd_parse_pdf)

    parser_preflight = sub.add_parser('parser-preflight')
    parser_preflight.set_defaults(func=cmd_parser_preflight)

    evidence_context = sub.add_parser('evidence-context')
    evidence_context.add_argument('--paper-id', required=True)
    evidence_context.add_argument('--label')
    evidence_context.add_argument('--citation-key')
    evidence_context.set_defaults(func=cmd_evidence_context)

    source_fetch = sub.add_parser('source-fetch')
    source_fetch.add_argument('--arxiv-id', required=True)
    source_fetch.add_argument('--paper-id')
    source_fetch.set_defaults(func=cmd_source_fetch)

    source_show = sub.add_parser('source-show')
    source_show.add_argument('--paper-id', required=True)
    source_show.set_defaults(func=cmd_source_show)

    source_sections = sub.add_parser('source-sections')
    source_sections.add_argument('--paper-id', required=True)
    source_sections.set_defaults(func=cmd_source_sections)

    source_equations = sub.add_parser('source-equations')
    source_equations.add_argument('--paper-id', required=True)
    source_equations.set_defaults(func=cmd_source_equations)

    source_theorems = sub.add_parser('source-theorems')
    source_theorems.add_argument('--paper-id', required=True)
    source_theorems.set_defaults(func=cmd_source_theorems)

    source_citations = sub.add_parser('source-citations')
    source_citations.add_argument('--paper-id', required=True)
    source_citations.set_defaults(func=cmd_source_citations)

    source_bibliography = sub.add_parser('source-bibliography')
    source_bibliography.add_argument('--paper-id', required=True)
    source_bibliography.set_defaults(func=cmd_source_bibliography)

    source_macros = sub.add_parser('source-macros')
    source_macros.add_argument('--paper-id', required=True)
    source_macros.set_defaults(func=cmd_source_macros)

    source_labels = sub.add_parser('source-labels')
    source_labels.add_argument('--paper-id', required=True)
    source_labels.set_defaults(func=cmd_source_labels)

    source_section = sub.add_parser('source-section')
    source_section.add_argument('--paper-id', required=True)
    source_section.add_argument('--title')
    source_section.add_argument('--label')
    source_section.set_defaults(func=cmd_source_section)

    source_refs = sub.add_parser('source-refs')
    source_refs.add_argument('--paper-id', required=True)
    source_refs.set_defaults(func=cmd_source_refs)

    source_equation = sub.add_parser('source-equation')
    source_equation.add_argument('--paper-id', required=True)
    source_equation.add_argument('--label', required=True)
    source_equation.set_defaults(func=cmd_source_equation)

    source_theorem = sub.add_parser('source-theorem')
    source_theorem.add_argument('--paper-id', required=True)
    source_theorem.add_argument('--label', required=True)
    source_theorem.set_defaults(func=cmd_source_theorem)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
