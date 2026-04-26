from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_assistant.adapters.workspace_exports import export_paper_context
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
    performance_smoke,
    privacy_status,
    record_timeout_diagnostic,
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
from research_assistant.industrial.full_scale import (
    build_execution_readiness,
    build_phase_registry,
    build_usefulness_metrics,
    get_phase_contract,
    list_phase_contracts,
    show_phase_registry,
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
    raise SystemExit(f'unknown workspace action {args.workspace_action}')


def cmd_backup(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    if args.backup_action == 'create':
        return _print_json(create_backup(root=root, output=Path(args.output) if args.output else None))
    if args.backup_action == 'inspect':
        return _print_json(inspect_backup(Path(args.path)))
    if args.backup_action == 'restore':
        return _print_json(restore_backup(Path(args.path), root=root, dry_run=args.dry_run))
    raise SystemExit(f'unknown backup action {args.backup_action}')


def cmd_doctor(args: argparse.Namespace) -> int:
    return _print_json(doctor(root=Path(args.root) if args.root else None))


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
        ))
    raise SystemExit(f'unknown performance action {args.performance_action}')


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
    backup_restore.set_defaults(func=cmd_backup)

    doctor_cmd = sub.add_parser('doctor', help='Report individual-install readiness and optional tool status')
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
    performance_smoke_cmd.set_defaults(func=cmd_performance)

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
