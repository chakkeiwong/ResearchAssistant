from __future__ import annotations

import json
from pathlib import Path

from scripts.literature_survey_benchmark_feedback_summary import (
    build_feedback_summary,
    run_summary,
    validate_summary,
)


def test_feedback_summary_reads_artifacts_and_selects_code_task(tmp_path: Path) -> None:
    _write_fixture_artifacts(tmp_path)

    result = run_summary(
        root=tmp_path,
        output_dir=tmp_path / "docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07",
        generated_at="2026-07-07T00:00:00Z",
    )

    assert result["schema_version"] == "ra-literature-survey-benchmark-feedback-summary-result-v1"
    assert result["status"] == "passed"
    assert result["finding_count"] == 12
    assert result["selected_next_task_count"] == 1
    assert result["disposition_counts"] == {
        "code_task": 9,
        "deferred_boundary": 1,
        "doc_task": 2,
    }
    summary = json.loads(Path(result["summary_path"]).read_text())
    findings = {row["finding_id"]: row for row in summary["findings"]}
    assert findings["LSBFL-001"]["status"] == "partial_supervised_review_queue"
    assert findings["LSBFL-002"]["status"] == "partial_reviewed_claim_import"
    assert findings["LSBFL-003"]["status"] == "partial_reviewed_source_safety_import"
    assert findings["LSBFL-004"]["status"] == "addressed_for_current_harness"
    assert findings["LSBFL-005"]["disposition"] == "doc_task"
    assert findings["LSBFL-005"]["status"] == "closed"
    assert findings["LSBFL-006"]["status"] == "addressed_for_current_modes"
    assert findings["LSBFL-007"]["status"] == "partial_reviewed_omission_import"
    assert findings["LSBFL-008"]["status"] == "partial_reviewed_evidence_merge"
    assert findings["LSBFL-009"]["status"] == "partial_resume_orchestration"
    assert findings["LSBFL-010"]["status"] == "partial_hostile_review_gate"
    assert findings["LSBFL-011"]["status"] == "closed"
    assert findings["LSBFL-012"]["status"] == "open_boundary"
    assert summary["selected_next_tasks"][0]["finding_ids"] == ["LSBFL-012"]
    assert "product readiness" in summary["what_is_not_concluded"]


def test_feedback_summary_validation_rejects_bad_disposition(tmp_path: Path) -> None:
    _write_fixture_artifacts(tmp_path)
    summary = build_feedback_summary(root=tmp_path, generated_at="2026-07-07T00:00:00Z")
    schema = json.loads(
        (
            tmp_path
            / "docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07/benchmark_findings_schema.json"
        ).read_text()
    )
    summary["findings"][0]["disposition"] = "benchmark_only"

    validation = validate_summary(summary, schema)

    assert validation["status"] == "failed"
    assert any("invalid disposition" in issue for issue in validation["issues"])


def test_feedback_summary_validation_requires_selected_next_task(tmp_path: Path) -> None:
    _write_fixture_artifacts(tmp_path)
    summary = build_feedback_summary(root=tmp_path, generated_at="2026-07-07T00:00:00Z")
    schema = json.loads(
        (
            tmp_path
            / "docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07/benchmark_findings_schema.json"
        ).read_text()
    )
    summary["selected_next_tasks"] = []

    validation = validate_summary(summary, schema)

    assert validation["status"] == "failed"
    assert "missing selected next task" in validation["issues"]


def _write_fixture_artifacts(root: Path) -> None:
    feedback_dir = root / "docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    (feedback_dir / "benchmark_findings_schema.json").write_text(json.dumps({
        "schema_version": "ra-literature-survey-benchmark-feedback-schema-v1",
        "required_top_level_fields": [
            "schema_version",
            "mission_id",
            "generated_at",
            "source_artifacts",
            "findings",
            "selected_next_tasks",
            "what_is_not_concluded",
        ],
        "finding_required_fields": [
            "finding_id",
            "source_artifact",
            "summary",
            "severity",
            "affected_surface",
            "disposition",
            "recommended_task",
            "rerun_checks",
            "status",
            "not_concluded",
        ],
        "allowed_severity": ["high", "medium", "low"],
        "allowed_disposition": ["code_task", "doc_task", "deferred_boundary", "wont_fix"],
        "allowed_status": [
            "selected_for_phase2",
            "selected_for_phase5",
            "addressed_for_current_harness",
            "addressed_for_current_modes",
            "partial_claim_candidate_surface",
            "partial_local_safety_surface",
            "partial_supervised_review_queue",
            "partial_supervised_orchestration",
            "partial_reviewed_claim_import",
            "partial_reviewed_source_safety_import",
            "partial_reviewed_omission_import",
            "partial_reviewed_evidence_merge",
            "partial_resume_orchestration",
            "partial_coverage_ledgers",
            "partial_hostile_review_gate",
            "queued_for_claim_review",
            "queued_for_source_safety_review",
            "queued_for_omission_review",
            "queued_for_reviewed_evidence_merge",
            "queued_for_resume_orchestration",
            "queued_for_coverage_ledgers",
            "queued_for_mission_cleanup",
            "open",
            "open_boundary",
            "closed",
            "blocked",
        ],
    }))

    phase6_dir = root / "docs/validation/literature_survey_live_public_source_phase6_2026-07-07"
    phase6_dir.mkdir(parents=True, exist_ok=True)
    (phase6_dir / "build_manifest.json").write_text(json.dumps({
        "ready_for_prose": False,
        "supported_claim_count": 0,
        "what_is_not_concluded": ["retraction/version safety", "product readiness"],
    }))
    (phase6_dir / "claim_support.json").write_text(json.dumps({
        "claims": [],
        "claim_candidates": [
            {
                "claim_id": "candidate_claim_001",
                "status": "review_required",
                "claim_support_allowed": False,
                "support_class": "anchor_candidate_not_support",
            }
        ],
    }))
    (phase6_dir / "source_safety_status.json").write_text(json.dumps({
        "status": "blocked_or_not_checked",
        "blocking_count": 1,
        "rows": [
            {
                "paper_id": "paper_arxiv_2201_1a5af737",
                "retraction_or_version_status": "not_checked_phase5",
                "claim_support_allowed": False,
            }
        ],
    }))
    (phase6_dir / "omission_risk.json").write_text(json.dumps({
        "status": "omission_and_safety_risks_visible",
        "risks": [
            {
                "risk_id": "source_text_not_inspected",
                "severity": "high",
                "risk": "No source text was inspected.",
                "expected_action": "inspect sources before prose drafting",
            }
        ],
    }))

    phase7_dir = root / "docs/validation/literature_survey_live_public_source_phase7_2026-07-07"
    phase7_dir.mkdir(parents=True, exist_ok=True)
    (phase7_dir / "phase7_validation_harness_result.json").write_text(json.dumps({
        "status": "passed",
        "mutation_strength": {
            "status": "passed",
            "unobserved_case_ids": [],
        },
        "negative_cases": [
            {
                "case_id": "ready_for_prose_weakened",
                "expected_signal_observed": True,
            }
        ],
    }))

    phase8_dir = root / "docs/validation/literature_survey_live_public_source_phase8_2026-07-07"
    phase8_dir.mkdir(parents=True, exist_ok=True)
    (phase8_dir / "phase8_ux_validation_result.json").write_text(json.dumps({
        "status": "passed",
        "help_reports": {
            "survey_run_public_source_workflow_help": {
                "status": "passed",
                "missing": [],
                "returncode": 0,
            }
        },
        "workflow_reports": {
            "phase6_public_source_packet": {
                "status": "passed",
                "ready_for_prose": False,
                "ready_for_writer": True,
            }
        },
        "review_queue_report": {
            "status": "passed",
            "review_queue_counts": {
                "by_type": {
                    "claim_candidate": 1,
                    "source_safety": 1,
                    "omission_risk": 1,
                    "workflow_blocker": 1,
                }
            },
        },
        "claim_review_import_report": {
            "status": "passed",
            "accepted_claim_count": 1,
            "rejected_claim_count": 0,
            "ready_for_prose": False,
            "source_safety_required": True,
            "omission_review_required": True,
        },
        "source_safety_import_report": {
            "status": "passed",
            "accepted_source_safety_count": 1,
            "rejected_source_safety_count": 0,
            "checked_clear_count": 1,
            "ready_for_prose": False,
            "source_safety_complete": False,
            "omission_review_required": True,
        },
        "omission_import_report": {
            "status": "passed",
            "accepted_omission_count": 1,
            "rejected_omission_count": 0,
            "open_omission_count": 1,
            "ready_for_prose": False,
            "literature_completeness_allowed": False,
        },
        "reviewed_evidence_merge_report": {
            "status": "passed",
            "ready_for_prose": False,
            "blocker_count": 1,
            "has_open_omission_blocker": True,
        },
        "resume_orchestration_report": {
            "status": "passed",
            "action_id": "compose_coverage_ledgers",
            "review_queue_reused": True,
            "ready_for_prose": False,
        },
        "coverage_ledgers_report": {
            "status": "passed",
            "ready_for_prose": False,
            "omitted_risk_count": 1,
            "requires_live_metadata_or_source_expansion": True,
        },
        "hostile_review_report": {
            "status": "passed",
            "ready_for_prose": False,
            "blocker_count": 1,
        },
    }))

    plans_dir = root / "docs/plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    (plans_dir / "literature_survey_live_public_source_phase9_closeout_result_2026-07-07.md").write_text(
        "\n".join([
            "## Status",
            "`PASSED`",
            "topic + seed workflow is current capability.",
            "One command does not yet orchestrate all phases.",
            "Retraction, withdrawal, erratum, and version checks remain undone.",
            "Autonomous single-command completion remains unconcluded.",
            "Phase 7 blocked on weakened-blocker detector gap; repair applied.",
            "VERDICT: AGREE",
        ])
    )
    (plans_dir / "literature_survey_goal_execution_phase7_mission_cleanup_result_2026-07-10.md").write_text(
        "\n".join([
            "## Status",
            "`PASSED_LOCAL_GOAL_COMPLETE_BLOCKED_FOR_PROSE`",
            "Final prose readiness remains blocked.",
        ])
    )
