from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07"

PHASE6_MANIFEST = Path("docs/validation/literature_survey_live_public_source_phase6_2026-07-07/build_manifest.json")
PHASE6_CLAIM_SUPPORT = Path("docs/validation/literature_survey_live_public_source_phase6_2026-07-07/claim_support.json")
PHASE6_SOURCE_SAFETY = Path("docs/validation/literature_survey_live_public_source_phase6_2026-07-07/source_safety_status.json")
PHASE6_OMISSION_RISK = Path("docs/validation/literature_survey_live_public_source_phase6_2026-07-07/omission_risk.json")
PHASE7_RESULT = Path("docs/validation/literature_survey_live_public_source_phase7_2026-07-07/phase7_validation_harness_result.json")
PHASE8_RESULT = Path("docs/validation/literature_survey_live_public_source_phase8_2026-07-07/phase8_ux_validation_result.json")
PHASE9_CLOSEOUT = Path("docs/plans/literature_survey_live_public_source_phase9_closeout_result_2026-07-07.md")
PHASE7_GOAL_CLEANUP = Path("docs/plans/literature_survey_goal_execution_phase7_mission_cleanup_result_2026-07-10.md")

MISSION_ID = "literature_survey_automation_one_command"
SUMMARY_SCHEMA_VERSION = "ra-literature-survey-benchmark-feedback-findings-v1"
RESULT_SCHEMA_VERSION = "ra-literature-survey-benchmark-feedback-summary-result-v1"
NONCLAIMS = [
    "product readiness",
    "literature completeness",
    "live web coverage",
    "real-agent reliability",
    "scientific correctness",
    "final prose readiness",
]


def run_summary(
    *,
    root: Path = ROOT,
    output_dir: Path = OUTPUT_DIR,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build and write the benchmark-feedback finding summary."""

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_feedback_summary(
        root=root,
        generated_at=generated_at or _utc_now_iso(),
    )
    schema = _load_schema(root)
    validation = validate_summary(summary, schema)
    summary_path = output_dir / "benchmark_findings.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))

    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": "passed" if validation["status"] == "passed" else "failed",
        "summary_path": str(summary_path),
        "finding_count": len(summary["findings"]),
        "selected_next_task_count": len(summary["selected_next_tasks"]),
        "disposition_counts": _count_by(summary["findings"], "disposition"),
        "severity_counts": _count_by(summary["findings"], "severity"),
        "validation": validation,
        "selected_next_tasks": summary["selected_next_tasks"],
        "what_is_not_concluded": NONCLAIMS,
    }
    return result


def build_feedback_summary(*, root: Path, generated_at: str) -> dict[str, Any]:
    phase6 = _read_json(root / PHASE6_MANIFEST)
    claim_support = _read_json(root / PHASE6_CLAIM_SUPPORT)
    source_safety = _read_json(root / PHASE6_SOURCE_SAFETY)
    omission_risk = _read_json(root / PHASE6_OMISSION_RISK)
    phase7 = _read_json(root / PHASE7_RESULT)
    phase8 = _read_json(root / PHASE8_RESULT)
    phase9 = _read_text(root / PHASE9_CLOSEOUT)
    goal_cleanup = _read_text_if_exists(root / PHASE7_GOAL_CLEANUP)

    findings = [
        _finding_one_command_orchestration(phase8, phase9),
        _finding_claim_anchor_gap(phase6, claim_support, phase8),
        _finding_retraction_version_gap(phase9, phase6, source_safety, phase8),
        _finding_negative_signal_guard(phase7, phase9),
        _finding_phase9_status_consistency(phase9),
        _finding_workflow_state_artifact_gap(phase8, phase9),
        _finding_omission_review_gap(omission_risk, phase8),
        _finding_reviewed_evidence_merge_gap(phase8),
        _finding_resume_orchestration_gap(phase8),
        _finding_coverage_ledgers_gap(phase8),
        _finding_mission_control_cleanup_gap(phase8, goal_cleanup),
        _finding_approval_bound_blocker(phase8, goal_cleanup),
    ]
    resume_report = phase8.get("resume_orchestration_report") or {}
    coverage_report = phase8.get("coverage_ledgers_report") or {}
    hostile_report = phase8.get("hostile_review_report") or {}
    cleanup_closed = "PASSED_LOCAL_GOAL_COMPLETE_BLOCKED_FOR_PROSE" in goal_cleanup
    next_task = (
        {
            "finding_ids": ["LSBFL-012"],
            "phase": "Approval-bound blocker",
            "task": "Resolve the actual survey blockers: import reviewed decisions that close reviewed-evidence/omission gaps, or request explicit bounded live metadata/source approval for blocked snowball frontiers.",
        }
        if cleanup_closed
        else
        {
            "finding_ids": ["LSBFL-011"],
            "phase": "Next local product slice",
            "task": "Align mission control, milestones, execution ledgers, and benchmark feedback with the actual local-only capability and remaining approval-bound blockers.",
        }
        if hostile_report.get("status") == "passed"
        else
        {
            "finding_ids": ["LSBFL-010"],
            "phase": "Next local product slice",
            "task": "Add a hostile review/final readiness gate that consumes reviewed evidence and coverage ledgers, emits exact blockers, and refuses prose readiness while coverage or omission risks remain open.",
        }
        if coverage_report.get("status") == "passed"
        else
        {
            "finding_ids": ["LSBFL-005", "LSBFL-006", "LSBFL-007"],
            "phase": "Next local product slice",
            "task": "Add explicit coverage and snowballing ledger surfacing for backward, forward, adjacent, classification, metadata, and omission-risk review gates; stop for approval if live metadata/source expansion is required.",
        }
        if resume_report.get("status") == "passed"
        else {
            "finding_ids": ["LSBFL-009"],
            "phase": "Next local product slice",
            "task": "Extend run-public-source-workflow resume orchestration so it detects reviewed sidecars and merge status, then emits exact next_action guidance.",
        }
    )
    selected_next_tasks = [
        next_task
    ]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "mission_id": MISSION_ID,
        "generated_at": generated_at,
        "source_artifacts": [
            str(PHASE9_CLOSEOUT),
            str(PHASE6_MANIFEST),
            str(PHASE6_CLAIM_SUPPORT),
            str(PHASE6_SOURCE_SAFETY),
            str(PHASE6_OMISSION_RISK),
            str(PHASE7_RESULT),
            str(PHASE8_RESULT),
            str(PHASE7_GOAL_CLEANUP),
        ],
        "findings": findings,
        "selected_next_tasks": selected_next_tasks,
        "what_is_not_concluded": NONCLAIMS,
    }


def validate_summary(summary: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in schema["required_top_level_fields"]:
        if field not in summary:
            issues.append(f"missing top-level field: {field}")

    allowed_severity = set(schema["allowed_severity"])
    allowed_disposition = set(schema["allowed_disposition"])
    allowed_status = set(schema["allowed_status"])
    finding_ids = set()
    for index, row in enumerate(summary.get("findings") or []):
        finding_id = row.get("finding_id", f"index:{index}")
        if finding_id in finding_ids:
            issues.append(f"duplicate finding_id: {finding_id}")
        finding_ids.add(finding_id)
        for field in schema["finding_required_fields"]:
            if field not in row:
                issues.append(f"{finding_id} missing field: {field}")
        if row.get("severity") not in allowed_severity:
            issues.append(f"{finding_id} invalid severity: {row.get('severity')}")
        if row.get("disposition") not in allowed_disposition:
            issues.append(f"{finding_id} invalid disposition: {row.get('disposition')}")
        if row.get("status") not in allowed_status:
            issues.append(f"{finding_id} invalid status: {row.get('status')}")
        if not row.get("rerun_checks"):
            issues.append(f"{finding_id} missing rerun checks")

    selected_ids = {
        finding_id
        for task in summary.get("selected_next_tasks") or []
        for finding_id in task.get("finding_ids", [])
    }
    missing_selected = sorted(selected_ids - finding_ids)
    for finding_id in missing_selected:
        issues.append(f"selected task references unknown finding: {finding_id}")
    if not summary.get("selected_next_tasks"):
        issues.append("missing selected next task")
    if not any(row.get("disposition") == "code_task" for row in summary.get("findings") or []):
        issues.append("no code_task findings")

    return {
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


def _finding_one_command_orchestration(phase8: dict[str, Any], phase9: str) -> dict[str, Any]:
    evidence = _contains_all(phase9, ["One command does not yet orchestrate", "topic + seed"])
    help_report = (phase8.get("help_reports") or {}).get("survey_run_public_source_workflow_help") or {}
    supervised_command_visible = help_report.get("status") == "passed"
    review_queue = phase8.get("review_queue_report") or {}
    review_queue_visible = review_queue.get("status") == "passed"
    return {
        "finding_id": "LSBFL-001",
        "source_artifact": str(PHASE8_RESULT),
        "summary": "A supervised orchestration command and local review queue are now visible and tested, but they still stop at explicit approval/review gates instead of autonomously completing public metadata, source intake, anchors, packet composition, and claim review.",
        "severity": "high",
        "affected_surface": "ra survey run-public-source-workflow",
        "disposition": "code_task",
        "recommended_task": "Use the review queue as the handoff for claim-review and safety-review import lanes without hiding live metadata/source/safety approvals.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'survey_build or survey_packet or survey_anchors or run_public_source_workflow' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
        ],
        "status": "partial_supervised_review_queue" if evidence and supervised_command_visible and review_queue_visible else "partial_supervised_orchestration",
        "not_concluded": [
            "product readiness",
            "autonomous end-to-end live/source workflow",
            "final prose readiness",
        ],
    }


def _finding_claim_anchor_gap(
    phase6: dict[str, Any],
    claim_support: dict[str, Any],
    phase8: dict[str, Any],
) -> dict[str, Any]:
    ready = phase6.get("ready_for_prose")
    supported_claim_count = phase6.get("supported_claim_count")
    evidence = ready is False and supported_claim_count == 0
    claim_candidates = claim_support.get("claim_candidates") or []
    candidate_surface_exists = bool(claim_candidates) and all(
        row.get("status") == "review_required" and row.get("claim_support_allowed") is False
        for row in claim_candidates
    )
    import_report = phase8.get("claim_review_import_report") or {}
    import_surface_passed = (
        import_report.get("status") == "passed"
        and import_report.get("accepted_claim_count") == 1
        and import_report.get("ready_for_prose") is False
        and import_report.get("source_safety_required") is True
        and import_report.get("omission_review_required") is True
    )
    return {
        "finding_id": "LSBFL-002",
        "source_artifact": str(PHASE8_RESULT if import_surface_passed else PHASE6_CLAIM_SUPPORT),
        "summary": "Reviewed-claim import is now visible as a local sidecar path, but the packet remains not prose-ready because reviewed claims do not clear source-safety or omission gates.",
        "severity": "high",
        "affected_surface": "ra survey import-claim-review",
        "disposition": "code_task",
        "recommended_task": "Keep reviewed claims as an auditable sidecar until source-safety and omission-review lanes can be imported with explicit evidence.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'import_claim_review or run_public_source_workflow or survey_packet' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. pytest tests/scripts/test_literature_survey_phase7_validation_harness.py -q",
        ],
        "status": "partial_reviewed_claim_import" if evidence and candidate_surface_exists and import_surface_passed else "queued_for_claim_review" if evidence and candidate_surface_exists else "open",
        "not_concluded": [
            "technical claim support",
            "final prose readiness",
            "scientific correctness",
        ],
    }


def _finding_retraction_version_gap(
    phase9: str,
    phase6: dict[str, Any],
    source_safety: dict[str, Any],
    phase8: dict[str, Any],
) -> dict[str, Any]:
    phase6_nonclaims = " ".join(str(row) for row in phase6.get("what_is_not_concluded", []))
    evidence = "Retraction, withdrawal, erratum, and version checks remain undone" in phase9 or "retraction/version safety" in phase6_nonclaims
    local_surface_exists = (
        source_safety.get("status") == "blocked_or_not_checked"
        and source_safety.get("blocking_count", 0) > 0
        and bool(source_safety.get("rows"))
    )
    source_safety_import = phase8.get("source_safety_import_report") or {}
    import_surface_passed = (
        source_safety_import.get("status") == "passed"
        and source_safety_import.get("accepted_source_safety_count") == 1
        and source_safety_import.get("ready_for_prose") is False
        and source_safety_import.get("source_safety_complete") is False
        and source_safety_import.get("omission_review_required") is True
    )
    return {
        "finding_id": "LSBFL-003",
        "source_artifact": str(PHASE8_RESULT if import_surface_passed else PHASE6_SOURCE_SAFETY),
        "summary": "Reviewed source-safety import is now visible as a local sidecar path, but it does not resolve omissions, merge claims, or prove complete retraction/version coverage.",
        "severity": "high",
        "affected_surface": "ra survey import-source-safety-review",
        "disposition": "code_task",
        "recommended_task": "Keep source-safety decisions as an auditable sidecar until omission review and reviewed-evidence merge gates exist.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'source_safety_review or run_public_source_workflow or survey_packet' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. pytest tests/scripts/test_literature_survey_phase7_validation_harness.py -q",
            "python scripts/literature_survey_phase6_packet_validation.py docs/validation/literature_survey_live_public_source_phase6_2026-07-07",
        ],
        "status": "partial_reviewed_source_safety_import" if evidence and local_surface_exists and import_surface_passed else "queued_for_source_safety_review" if evidence and local_surface_exists else "open",
        "not_concluded": [
            "retraction safety",
            "version correctness",
            "source safety",
        ],
    }


def _finding_negative_signal_guard(phase7: dict[str, Any], phase9: str) -> dict[str, Any]:
    cases = {row.get("case_id"): row for row in phase7.get("negative_cases", [])}
    weakened = cases.get("ready_for_prose_weakened") or {}
    mutation_strength = phase7.get("mutation_strength") or {}
    evidence = (
        weakened.get("expected_signal_observed") is True
        and mutation_strength.get("status") == "passed"
        and not mutation_strength.get("unobserved_case_ids")
    )
    review_trail_mentions_repair = "weakened-blocker detector gap" in phase9
    return {
        "finding_id": "LSBFL-004",
        "source_artifact": str(PHASE7_RESULT),
        "summary": "The weakened-blocker negative case required repair; current harness now records mutation-strength coverage and expected-signal observation.",
        "severity": "medium",
        "affected_surface": "validation harness",
        "disposition": "code_task",
        "recommended_task": "Keep mutation-strength coverage explicit in the summarizer and require expected signal observation.",
        "rerun_checks": [
            "PYTHONPATH=src:. pytest tests/scripts/test_literature_survey_phase7_validation_harness.py -q",
        ],
        "status": "addressed_for_current_harness" if evidence and review_trail_mentions_repair else "blocked",
        "not_concluded": [
            "real-agent reliability",
            "complete negative-case coverage",
        ],
    }


def _finding_phase9_status_consistency(phase9: str) -> dict[str, Any]:
    stale = "`PASSED_PENDING_FINAL_REVIEW`" in phase9 and "VERDICT: AGREE" in phase9
    return {
        "finding_id": "LSBFL-005",
        "source_artifact": str(PHASE9_CLOSEOUT),
        "summary": "Status says PASSED_PENDING_FINAL_REVIEW although final review body records agreement.",
        "severity": "low",
        "affected_surface": "plan and result docs",
        "disposition": "doc_task",
        "recommended_task": "Patch stale status or record why it remains pending.",
        "rerun_checks": [
            "text consistency check in the feedback summarizer",
        ],
        "status": "open" if stale else "closed",
        "not_concluded": [
            "new product capability",
        ],
    }


def _finding_workflow_state_artifact_gap(phase8: dict[str, Any], phase9: str) -> dict[str, Any]:
    phase8_passed = phase8.get("status") == "passed"
    still_not_autonomous = "Autonomous single-command completion" in phase9 or "One command does not yet orchestrate" in phase9
    packet_report = (phase8.get("workflow_reports") or {}).get("phase6_public_source_packet") or {}
    workflow_state_available = packet_report.get("status") == "passed"
    return {
        "finding_id": "LSBFL-006",
        "source_artifact": str(PHASE8_RESULT),
        "summary": "Workflow-state guidance exists for the current modes validated by Phase 8, but it does not establish autonomous one-command completion.",
        "severity": "medium",
        "affected_surface": "ra survey build",
        "disposition": "code_task",
        "recommended_task": "Keep workflow-state checks in the UX harness while extending the supervised command surface.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'survey_build or survey_packet or survey_anchors' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
        ],
        "status": "addressed_for_current_modes" if phase8_passed and still_not_autonomous and workflow_state_available else "open",
        "not_concluded": [
            "autonomous one-command completion",
            "hidden approval bypass",
        ],
    }


def _finding_omission_review_gap(omission_risk: dict[str, Any], phase8: dict[str, Any]) -> dict[str, Any]:
    risks = omission_risk.get("risks") or []
    review_queue = phase8.get("review_queue_report") or {}
    by_type = (review_queue.get("review_queue_counts") or {}).get("by_type") or {}
    omission_queue_visible = by_type.get("omission_risk", 0) > 0
    risk_surface_exists = omission_risk.get("status") == "omission_and_safety_risks_visible" and bool(risks)
    omission_import = phase8.get("omission_import_report") or {}
    import_surface_passed = (
        omission_import.get("status") == "passed"
        and omission_import.get("accepted_omission_count") == 1
        and omission_import.get("ready_for_prose") is False
        and omission_import.get("literature_completeness_allowed") is False
    )
    return {
        "finding_id": "LSBFL-007",
        "source_artifact": str(PHASE8_RESULT if import_surface_passed else PHASE6_OMISSION_RISK),
        "summary": "Reviewed omission-risk import is now visible as a local sidecar path, but it does not merge claims, clear source safety, or prove literature completeness.",
        "severity": "high",
        "affected_surface": "ra survey import-omission-review",
        "disposition": "code_task",
        "recommended_task": "Keep omission decisions as an auditable sidecar until a reviewed-evidence merge gate can combine all sidecars safely.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'omission_review or run_public_source_workflow or survey_packet' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py",
        ],
        "status": "partial_reviewed_omission_import" if risk_surface_exists and omission_queue_visible and import_surface_passed else "queued_for_omission_review" if risk_surface_exists and omission_queue_visible else "open",
        "not_concluded": [
            "literature completeness",
            "omission acceptability",
            "final prose readiness",
        ],
    }


def _finding_reviewed_evidence_merge_gap(phase8: dict[str, Any]) -> dict[str, Any]:
    claim_import = phase8.get("claim_review_import_report") or {}
    safety_import = phase8.get("source_safety_import_report") or {}
    omission_import = phase8.get("omission_import_report") or {}
    sidecars_visible = (
        claim_import.get("status") == "passed"
        and safety_import.get("status") == "passed"
        and omission_import.get("status") == "passed"
    )
    merge_report = phase8.get("reviewed_evidence_merge_report") or {}
    merge_surface_passed = (
        merge_report.get("status") == "passed"
        and merge_report.get("ready_for_prose") is False
        and merge_report.get("has_open_omission_blocker") is True
    )
    return {
        "finding_id": "LSBFL-008",
        "source_artifact": str(PHASE8_RESULT),
        "summary": "Reviewed evidence merge is now visible as a local blocker-preserving gate, but the supervised workflow does not yet discover sidecars and resume from merge status.",
        "severity": "high",
        "affected_surface": "ra survey merge-reviewed-evidence",
        "disposition": "code_task",
        "recommended_task": "Keep merge status as an auditable readiness/blocker sidecar until run-public-source-workflow can discover it and guide the next action.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'merge_reviewed_evidence or import_claim_review or source_safety_review or omission_review' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py",
        ],
        "status": "partial_reviewed_evidence_merge" if sidecars_visible and merge_surface_passed else "queued_for_reviewed_evidence_merge" if sidecars_visible else "open",
        "not_concluded": [
            "final prose readiness",
            "product readiness",
            "scientific correctness",
        ],
    }


def _finding_resume_orchestration_gap(phase8: dict[str, Any]) -> dict[str, Any]:
    merge_report = phase8.get("reviewed_evidence_merge_report") or {}
    merge_surface_passed = merge_report.get("status") == "passed"
    resume_report = phase8.get("resume_orchestration_report") or {}
    resume_surface_passed = (
        resume_report.get("status") == "passed"
        and resume_report.get("action_id") == "compose_coverage_ledgers"
        and resume_report.get("review_queue_reused") is True
        and resume_report.get("ready_for_prose") is False
    )
    return {
        "finding_id": "LSBFL-009",
        "source_artifact": str(PHASE8_RESULT),
        "summary": "run-public-source-workflow now discovers reviewed sidecars and merge status during resume, preserves reviewed-evidence blockers, and emits next_action guidance, but it still stops short of coverage/snowballing completion and hostile review.",
        "severity": "high",
        "affected_surface": "ra survey run-public-source-workflow",
        "disposition": "code_task",
        "recommended_task": "Use resume orchestration as the control point for the next coverage/snowballing ledger slice without hiding live metadata/source approval gates.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'run_public_source_workflow or merge_reviewed_evidence' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py",
        ],
        "status": "partial_resume_orchestration" if resume_surface_passed else "queued_for_resume_orchestration" if merge_surface_passed else "open",
        "not_concluded": [
            "autonomous end-to-end workflow",
            "hidden approval bypass",
            "product readiness",
        ],
    }


def _finding_coverage_ledgers_gap(phase8: dict[str, Any]) -> dict[str, Any]:
    coverage = phase8.get("coverage_ledgers_report") or {}
    hostile = phase8.get("hostile_review_report") or {}
    coverage_passed = (
        coverage.get("status") == "passed"
        and coverage.get("ready_for_prose") is False
        and coverage.get("omitted_risk_count", 0) > 0
    )
    hostile_passed = (
        hostile.get("status") == "passed"
        and hostile.get("ready_for_prose") is False
        and hostile.get("blocker_count", 0) > 0
    )
    return {
        "finding_id": "LSBFL-010",
        "source_artifact": str(PHASE8_RESULT),
        "summary": "Coverage and snowballing ledgers are now composed locally from existing packet artifacts with metadata-only and omission-risk boundaries, but hostile review/final readiness still needs to consume them.",
        "severity": "high",
        "affected_surface": "ra survey coverage-ledgers",
        "disposition": "code_task",
        "recommended_task": "Add a hostile review/final readiness gate that combines reviewed_evidence_status.json and coverage ledgers before any prose-ready decision.",
        "rerun_checks": [
            "PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k 'coverage_ledgers or run_public_source_workflow' -q",
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py",
        ],
        "status": "partial_hostile_review_gate" if hostile_passed else "partial_coverage_ledgers" if coverage_passed else "queued_for_coverage_ledgers",
        "not_concluded": [
            "literature completeness",
            "final prose readiness",
            "product readiness",
        ],
    }


def _finding_mission_control_cleanup_gap(phase8: dict[str, Any], goal_cleanup: str) -> dict[str, Any]:
    hostile = phase8.get("hostile_review_report") or {}
    hostile_passed = hostile.get("status") == "passed"
    cleanup_closed = "PASSED_LOCAL_GOAL_COMPLETE_BLOCKED_FOR_PROSE" in goal_cleanup
    return {
        "finding_id": "LSBFL-011",
        "source_artifact": str(PHASE7_GOAL_CLEANUP if cleanup_closed else PHASE8_RESULT),
        "summary": "The local workflow now exposes reviewed sidecars, coverage ledgers, and a hostile review blocker gate, so mission control and milestones need final alignment with actual capability and approval-bound blockers.",
        "severity": "medium",
        "affected_surface": "mission control and milestones",
        "disposition": "doc_task",
        "recommended_task": "Patch mission control, milestone JSON, and execution ledgers so future agents see the single-command capability and remaining approval-bound blockers accurately.",
        "rerun_checks": [
            "python -m json.tool docs/plans/literature_survey_automation_milestones.json",
            "git diff --check",
            "PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py",
        ],
        "status": "closed" if cleanup_closed else "queued_for_mission_cleanup" if hostile_passed else "open",
        "not_concluded": [
            "product readiness",
            "literature completeness",
            "scientific correctness",
        ],
    }


def _finding_approval_bound_blocker(phase8: dict[str, Any], goal_cleanup: str) -> dict[str, Any]:
    hostile = phase8.get("hostile_review_report") or {}
    coverage = phase8.get("coverage_ledgers_report") or {}
    cleanup_closed = "PASSED_LOCAL_GOAL_COMPLETE_BLOCKED_FOR_PROSE" in goal_cleanup
    boundary_active = (
        cleanup_closed
        and hostile.get("ready_for_prose") is False
        and coverage.get("requires_live_metadata_or_source_expansion") is True
    )
    return {
        "finding_id": "LSBFL-012",
        "source_artifact": str(PHASE7_GOAL_CLEANUP),
        "summary": "Local execution is complete through hostile-review blocker reporting; remaining progress requires reviewed blocker-closing evidence or explicit bounded metadata/source expansion approval.",
        "severity": "high",
        "affected_surface": "survey evidence blockers",
        "disposition": "deferred_boundary",
        "recommended_task": "Import reviewed decisions that close open omission/reviewed-evidence blockers, or request exact bounded live metadata/source approval for blocked snowball frontiers.",
        "rerun_checks": [
            "python scripts/literature_survey_phase8_ux_validation.py",
            "PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py",
        ],
        "status": "open_boundary" if boundary_active else "open",
        "not_concluded": [
            "final prose readiness",
            "literature completeness",
            "product readiness",
            "scientific correctness",
        ],
    }


def _load_schema(root: Path) -> dict[str, Any]:
    return _read_json(root / "docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07/benchmark_findings_schema.json")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact missing: {path}")
    return json.loads(path.read_text())


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"required artifact missing: {path}")
    return path.read_text()


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text()


def _contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    try:
        result = run_summary()
    except Exception as exc:  # pragma: no cover - command-line failure path
        result = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "status": "failed",
            "error": str(exc),
            "what_is_not_concluded": NONCLAIMS,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
