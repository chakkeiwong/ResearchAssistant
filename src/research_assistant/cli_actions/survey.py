from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from research_assistant.survey.mission_state import MissionStateError


Report = dict[str, Any]
ActionHandler = Callable[[argparse.Namespace, "SurveyServices"], int]


@dataclass(frozen=True, slots=True)
class SurveyServices:
    print_json: Callable[[dict | list], int]
    human_attestation_blocked: Callable[[MissionStateError], Report]
    build_survey_evidence_packet: Callable[..., Report]
    build_source_anchor_packet: Callable[..., Report]
    compose_public_source_evidence_packet: Callable[..., Report]
    compose_coverage_ledgers: Callable[..., Report]
    compose_reviewed_final_packet: Callable[..., Report]
    run_hostile_review_gate: Callable[..., Report]
    run_public_source_workflow: Callable[..., Report]
    import_reviewed_claims: Callable[..., Report]
    import_reviewed_source_safety: Callable[..., Report]
    import_reviewed_omissions: Callable[..., Report]
    import_reviewed_workflow_blockers: Callable[..., Report]
    merge_reviewed_evidence: Callable[..., Report]
    prepare_human_review_packet: Callable[..., Report]
    render_human_review_materials: Callable[..., Report]
    validate_human_attestation: Callable[..., Report]
    build_assessment: Callable[..., Report]
    write_assessment: Callable[..., Report]


def execute_survey_action(args: argparse.Namespace, services: SurveyServices) -> int:
    """Execute one registered survey action through an explicit dispatch table."""
    try:
        handler = SURVEY_ACTION_HANDLERS[args.survey_action]
    except KeyError as exc:
        raise SystemExit(f"unknown survey action {args.survey_action}") from exc
    return handler(args, services)


def _emit_status(report: Report, services: SurveyServices, accepted: set[str]) -> int:
    services.print_json(report)
    return 0 if report["status"] in accepted else 1


def _build(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.build_survey_evidence_packet(
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
    return _emit_status(
        report,
        services,
        {"created_skeleton", "partial", "offline_replay_fixture_complete", "metadata_only_packet"},
    )


def _anchors(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.build_source_anchor_packet(
        topic=args.topic,
        paper_ids=args.paper_id,
        output_dir=Path(args.out),
        force=args.force,
        max_anchors_per_paper=args.max_anchors_per_paper,
        root=Path(args.root) if args.root else None,
    )
    return _emit_status(report, services, {"anchors_extracted", "source_gaps_or_no_anchors"})


def _packet(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.compose_public_source_evidence_packet(
        topic=args.topic,
        output_dir=Path(args.out),
        metadata_dir=Path(args.metadata_dir),
        source_status_dir=Path(args.source_status_dir),
        anchor_dir=Path(args.anchor_dir),
        force=args.force,
    )
    return _emit_status(report, services, {"packet_composed_with_blockers"})


def _coverage_ledgers(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.compose_coverage_ledgers(
        topic=args.topic,
        packet_dir=Path(args.packet_dir),
        output_dir=Path(args.out),
        force=args.force,
    )
    return _emit_status(report, services, {"coverage_ledgers_composed"})


def _compose_reviewed_final_packet(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.compose_reviewed_final_packet(
        mission_root=Path(args.mission_root),
        review_queue_path=Path(args.review_queue),
        packet_dir=Path(args.packet_dir),
        anchor_dir=Path(args.anchor_dir),
        local_evidence_root=Path(args.local_evidence_root) if args.local_evidence_root else None,
        output_dir=Path(args.out),
        force=args.force,
    )
    return _emit_status(report, services, {"reviewed_final_packet_ready_for_hostile_review"})


def _hostile_review(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.run_hostile_review_gate(
        reviewed_final_packet_path=Path(args.reviewed_final_packet),
        mission_root=Path(args.mission_root),
        review_queue_path=Path(args.review_queue),
        packet_dir=Path(args.packet_dir),
        anchor_dir=Path(args.anchor_dir),
        local_evidence_root=Path(args.local_evidence_root) if args.local_evidence_root else None,
        output_dir=Path(args.out),
        force=args.force,
    )
    return _emit_status(
        report,
        services,
        {"ready_for_reviewed_prose_within_recorded_scope", "blocked_for_reviewed_prose"},
    )


def _run_public_source_workflow(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.run_public_source_workflow(
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
        reviewed_workflow_blockers_dir=(
            Path(args.reviewed_workflow_blockers_dir)
            if args.reviewed_workflow_blockers_dir else None
        ),
        reviewed_evidence_dir=Path(args.reviewed_evidence_dir) if args.reviewed_evidence_dir else None,
        local_evidence_root=Path(args.local_evidence_root) if args.local_evidence_root else None,
    )
    return _emit_status(report, services, {"blocked_at_gate", "ready_for_local_continuation"})


def _import_claim_review(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.import_reviewed_claims(
        review_queue_path=Path(args.review_queue),
        decisions_path=Path(args.decisions),
        output_dir=Path(args.out),
        force=args.force,
        human_attestation_receipt_path=(
            Path(args.human_attestation_receipt) if args.human_attestation_receipt else None
        ),
    )
    return _emit_status(report, services, {"reviewed_claims_complete"})


def _import_source_safety_review(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.import_reviewed_source_safety(
        review_queue_path=Path(args.review_queue),
        decisions_path=Path(args.decisions),
        output_dir=Path(args.out),
        force=args.force,
        human_attestation_receipt_path=(
            Path(args.human_attestation_receipt) if args.human_attestation_receipt else None
        ),
    )
    return _emit_status(report, services, {"reviewed_source_safety_complete"})


def _import_omission_review(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.import_reviewed_omissions(
        review_queue_path=Path(args.review_queue),
        decisions_path=Path(args.decisions),
        output_dir=Path(args.out),
        force=args.force,
    )
    return _emit_status(report, services, {"reviewed_omissions_complete"})


def _import_workflow_blocker_review(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.import_reviewed_workflow_blockers(
        review_queue_path=Path(args.review_queue),
        decisions_path=Path(args.decisions),
        output_dir=Path(args.out),
        force=args.force,
    )
    return _emit_status(report, services, {"reviewed_workflow_blockers_complete"})


def _merge_reviewed_evidence(args: argparse.Namespace, services: SurveyServices) -> int:
    report = services.merge_reviewed_evidence(
        review_queue_path=Path(args.review_queue),
        reviewed_claims_path=Path(args.reviewed_claims),
        reviewed_source_safety_path=Path(args.reviewed_source_safety),
        reviewed_omissions_path=Path(args.reviewed_omissions),
        reviewed_workflow_blockers_path=Path(args.reviewed_workflow_blockers),
        output_dir=Path(args.out),
        force=args.force,
    )
    return _emit_status(
        report,
        services,
        {
            "reviewed_evidence_complete",
            "reviewed_evidence_blocked",
            "reviewed_evidence_blocked_unavailable_source_outcome",
        },
    )


def _prepare_human_review(args: argparse.Namespace, services: SurveyServices) -> int:
    try:
        report = services.prepare_human_review_packet(
            review_queue_path=Path(args.review_queue),
            output_dir=Path(args.out),
            force=args.force,
        )
    except MissionStateError as exc:
        report = services.human_attestation_blocked(exc)
    return _emit_status(report, services, {"human_review_packet_prepared_unattested"})


def _render_human_review(args: argparse.Namespace, services: SurveyServices) -> int:
    try:
        report = services.render_human_review_materials(
            packet_path=Path(args.packet),
            output_dir=Path(args.out) if args.out else None,
            force=args.force,
        )
    except MissionStateError as exc:
        report = services.human_attestation_blocked(exc)
    return _emit_status(report, services, {"human_review_materials_rendered"})


def _validate_human_attestation(args: argparse.Namespace, services: SurveyServices) -> int:
    try:
        report = services.validate_human_attestation(
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
        report = services.human_attestation_blocked(exc)
    return _emit_status(report, services, {"human_self_attestation_validated"})


def _qualitative_assessment(args: argparse.Namespace, services: SurveyServices) -> int:
    assessment = services.build_assessment(
        subject_id=args.subject_id,
        assessment_type=args.assessment_type,
        summary=args.summary,
        merits=args.merit,
        concerns=args.concern,
        uncertainties=args.uncertainty,
        evidence_refs=args.evidence_ref,
        next_action=args.next_action,
    )
    report = services.write_assessment(
        assessment=assessment,
        output_path=Path(args.out),
        force=args.force,
    )
    services.print_json({**report, "assessment": assessment})
    return 0


SURVEY_ACTION_HANDLERS: Mapping[str, ActionHandler] = MappingProxyType({
    "build": _build,
    "anchors": _anchors,
    "packet": _packet,
    "coverage-ledgers": _coverage_ledgers,
    "compose-reviewed-final-packet": _compose_reviewed_final_packet,
    "hostile-review": _hostile_review,
    "run-public-source-workflow": _run_public_source_workflow,
    "import-claim-review": _import_claim_review,
    "import-source-safety-review": _import_source_safety_review,
    "import-omission-review": _import_omission_review,
    "import-workflow-blocker-review": _import_workflow_blocker_review,
    "merge-reviewed-evidence": _merge_reviewed_evidence,
    "prepare-human-review": _prepare_human_review,
    "validate-human-attestation": _validate_human_attestation,
    "render-human-review": _render_human_review,
    "qualitative-assessment": _qualitative_assessment,
})
