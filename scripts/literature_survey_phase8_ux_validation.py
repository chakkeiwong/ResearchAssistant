from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATION_DIR = ROOT / "docs/validation/literature_survey_live_public_source_phase8_2026-07-07"
VALIDATION_DIR = Path(
    os.environ.get("RA_LITERATURE_SURVEY_PHASE8_VALIDATION_DIR", DEFAULT_VALIDATION_DIR)
).expanduser().resolve()
PHASE6_PACKET = ROOT / "docs/validation/literature_survey_live_public_source_phase6_2026-07-07"
PHASE2_METADATA = ROOT / "docs/validation/literature_survey_live_public_source_phase2_2026-07-07"
PHASE4_SOURCE_STATUS = ROOT / "docs/validation/literature_survey_live_public_source_phase4_2026-07-07"
PHASE5_ANCHORS = ROOT / "docs/validation/literature_survey_live_public_source_phase5_2026-07-07"


def run_validation() -> dict[str, Any]:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    phase6_manifest = json.loads((PHASE6_PACKET / "build_manifest.json").read_text())
    help_reports = {
        "survey_build_help": _help_report(["survey", "build", "--help"]),
        "survey_packet_help": _help_report(["survey", "packet", "--help"]),
        "survey_run_public_source_workflow_help": _help_report(["survey", "run-public-source-workflow", "--help"]),
        "survey_import_claim_review_help": _help_report(["survey", "import-claim-review", "--help"]),
        "survey_import_source_safety_review_help": _help_report(["survey", "import-source-safety-review", "--help"]),
        "survey_import_omission_review_help": _help_report(["survey", "import-omission-review", "--help"]),
        "survey_import_workflow_blocker_review_help": _help_report(
            ["survey", "import-workflow-blocker-review", "--help"]
        ),
        "survey_merge_reviewed_evidence_help": _help_report(["survey", "merge-reviewed-evidence", "--help"]),
        "survey_coverage_ledgers_help": _help_report(["survey", "coverage-ledgers", "--help"]),
        "survey_compose_reviewed_final_packet_help": _help_report(
            ["survey", "compose-reviewed-final-packet", "--help"]
        ),
        "survey_hostile_review_help": _help_report(["survey", "hostile-review", "--help"]),
    }
    workflow_reports = {
        "phase6_public_source_packet": _workflow_report(
            phase6_manifest.get("workflow_state"),
            expected_state="public_source_packet_blocked_for_prose",
            expected_ready_for_writer=True,
            expected_ready_for_prose=False,
            required_next_action="map proposed technical claims",
            required_approval="source/PDF/full-text",
        )
    }
    review_queue_report = _review_queue_report()
    single_confirmation_report = _single_confirmation_report()
    confirmed_source_scope_report = _confirmed_source_scope_report()
    claim_review_import_report = _claim_review_import_report()
    source_safety_import_report = _source_safety_import_report()
    omission_import_report = _omission_import_report()
    workflow_blocker_import_report = _workflow_blocker_import_report()
    reviewed_evidence_merge_report = _reviewed_evidence_merge_report()
    resume_orchestration_report = _resume_orchestration_report()
    coverage_ledgers_report = _coverage_ledgers_report()
    hostile_review_report = _hostile_review_report()
    issues = []
    for name, report in help_reports.items():
        if report["status"] != "passed":
            issues.append({"code": "help_boundary_missing", "name": name, "details": report["missing"]})
    for name, report in workflow_reports.items():
        if report["status"] != "passed":
            issues.append({"code": "workflow_state_invalid", "name": name, "details": report["issues"]})
    if review_queue_report["status"] != "passed":
        issues.append({"code": "review_queue_invalid", "name": "supervised_review_queue", "details": review_queue_report["issues"]})
    if single_confirmation_report["status"] != "passed":
        issues.append({
            "code": "single_confirmation_invalid",
            "name": "m15_single_public_discovery_confirmation",
            "details": single_confirmation_report["issues"],
        })
    if confirmed_source_scope_report["status"] != "passed":
        issues.append({
            "code": "confirmed_source_scope_invalid",
            "name": "m15_confirmed_source_scope",
            "details": confirmed_source_scope_report["issues"],
        })
    if claim_review_import_report["status"] != "passed":
        issues.append({
            "code": "claim_review_import_invalid",
            "name": "reviewed_claim_import",
            "details": claim_review_import_report["issues"],
        })
    if source_safety_import_report["status"] != "passed":
        issues.append({
            "code": "source_safety_import_invalid",
            "name": "reviewed_source_safety_import",
            "details": source_safety_import_report["issues"],
        })
    if omission_import_report["status"] != "passed":
        issues.append({
            "code": "omission_import_invalid",
            "name": "reviewed_omission_import",
            "details": omission_import_report["issues"],
        })
    if workflow_blocker_import_report["status"] != "passed":
        issues.append({
            "code": "workflow_blocker_import_invalid",
            "name": "reviewed_workflow_blocker_import",
            "details": workflow_blocker_import_report["issues"],
        })
    if reviewed_evidence_merge_report["status"] != "passed":
        issues.append({
            "code": "reviewed_evidence_merge_invalid",
            "name": "reviewed_evidence_merge",
            "details": reviewed_evidence_merge_report["issues"],
        })
    if resume_orchestration_report["status"] != "passed":
        issues.append({
            "code": "resume_orchestration_invalid",
            "name": "resume_orchestration",
            "details": resume_orchestration_report["issues"],
        })
    if coverage_ledgers_report["status"] != "passed":
        issues.append({
            "code": "coverage_ledgers_invalid",
            "name": "coverage_ledgers",
            "details": coverage_ledgers_report["issues"],
        })
    if hostile_review_report["status"] != "passed":
        issues.append({
            "code": "hostile_review_invalid",
            "name": "hostile_review",
            "details": hostile_review_report["issues"],
        })

    result = {
        "schema_version": "ra-literature-survey-live-public-source-phase8-ux-validation-v1",
        "status": "passed" if not issues else "failed",
        "help_reports": help_reports,
        "workflow_reports": workflow_reports,
        "review_queue_report": review_queue_report,
        "single_confirmation_report": single_confirmation_report,
        "confirmed_source_scope_report": confirmed_source_scope_report,
        "claim_review_import_report": claim_review_import_report,
        "source_safety_import_report": source_safety_import_report,
        "omission_import_report": omission_import_report,
        "workflow_blocker_import_report": workflow_blocker_import_report,
        "reviewed_evidence_merge_report": reviewed_evidence_merge_report,
        "resume_orchestration_report": resume_orchestration_report,
        "coverage_ledgers_report": coverage_ledgers_report,
        "hostile_review_report": hostile_review_report,
        "issues": issues,
        "boundary_contract": {
            "unsafe_modes_default": False,
            "hidden_live_or_download_action": False,
            "metadata_or_source_promoted_to_claim_support": False,
            "phase6_packet_promoted_to_final_prose": False,
        },
        "what_is_not_concluded": [
            "product readiness",
            "real-agent reliability",
            "scientific correctness",
            "literature completeness",
        ],
    }
    result_path = VALIDATION_DIR / "phase8_ux_validation_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def _help_report(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "research_assistant.cli", *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": "src"},
        check=False,
        capture_output=True,
        text=True,
    )
    text = completed.stdout + completed.stderr
    if args[:2] == ["survey", "build"]:
        required = ["metadata mode never fetches source/PDF/full text", "public-metadata"]
    elif args[:2] == ["survey", "packet"]:
        required = ["without upgrading blocked claims to prose readiness", "metadata-dir", "anchor-dir"]
    elif args[:2] == ["survey", "run-public-source-workflow"]:
        required = [
            "one public-discovery question",
            "--confirm-public-discovery",
            "does not allow credentials",
            "claim support from metadata",
            "final prose readiness",
        ]
    elif args[:2] == ["survey", "coverage-ledgers"]:
        required = ["without live expansion", "does not claim literature completeness", "backward_snowball.json"]
    elif args[:2] == ["survey", "compose-reviewed-final-packet"]:
        required = ["immutable packet", "does not establish prose readiness", "mission-root", "review-queue"]
    elif args[:2] == ["survey", "hostile-review"]:
        required = ["immutable reviewed final packet", "does not run live expansion", "reviewed-final-packet", "mission-root"]
    elif args[:2] == ["survey", "import-claim-review"]:
        required = ["does not run live lookup", "clear source safety", "mark final prose ready"]
    elif args[:2] == ["survey", "import-source-safety-review"]:
        required = ["does not run live lookup", "resolve omissions", "mark final prose ready"]
    elif args[:2] == ["survey", "import-omission-review"]:
        required = ["does not run live lookup", "claim literature completeness", "mark final prose ready"]
    elif args[:2] == ["survey", "import-workflow-blocker-review"]:
        required = ["does not run live lookup", "workflow blocker", "mark final prose ready"]
    else:
        required = ["sidecars", "provenance", "product/scientific readiness"]
    lowered = " ".join(text.lower().split())
    missing = [token for token in required if token.lower() not in lowered]
    return {
        "status": "passed" if completed.returncode == 0 and not missing else "failed",
        "args": args,
        "returncode": completed.returncode,
        "missing": missing,
    }


def _workflow_report(
    workflow: Any,
    *,
    expected_state: str,
    expected_ready_for_writer: bool,
    expected_ready_for_prose: bool,
    required_next_action: str,
    required_approval: str,
) -> dict[str, Any]:
    issues = []
    if not isinstance(workflow, dict):
        issues.append("workflow_state missing or not an object")
        workflow = {}
    if workflow.get("state") != expected_state:
        issues.append(f"state={workflow.get('state')} expected={expected_state}")
    if workflow.get("ready_for_writer") is not expected_ready_for_writer:
        issues.append("ready_for_writer mismatch")
    if workflow.get("ready_for_prose") is not expected_ready_for_prose:
        issues.append("ready_for_prose mismatch")
    next_commands = [str(value) for value in workflow.get("safe_next_commands") or []]
    approvals = [str(value) for value in workflow.get("approval_required_for") or []]
    forbidden = [str(value) for value in workflow.get("forbidden_jumps") or []]
    if not any(required_next_action in value for value in next_commands):
        issues.append(f"missing next action containing {required_next_action}")
    if not any(required_approval in value for value in approvals):
        issues.append(f"missing approval requirement containing {required_approval}")
    if not any("metadata" in value and "technical claim support" in value for value in forbidden):
        issues.append("missing forbidden jump against metadata/source claim support")
    return {
        "status": "passed" if not issues else "failed",
        "state": workflow.get("state"),
        "ready_for_writer": workflow.get("ready_for_writer"),
        "ready_for_prose": workflow.get("ready_for_prose"),
        "issues": issues,
    }


def _review_queue_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-review-queue-") as tmp:
        mission_dir = Path(tmp) / "mission"
        workflow = _run_public_source_workflow(mission_dir)
        if workflow["returncode"] != 0:
            issues.append(f"command failed: {workflow['text'].strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}
        payload = json.loads(workflow["stdout"])
        review_queue_path = Path(payload.get("review_queue_path") or "")
        if not review_queue_path.is_file():
            issues.append("review_queue_path missing or does not exist")
            queue = {}
        else:
            queue = json.loads(review_queue_path.read_text())
        counts = queue.get("queue_counts") or {}
        by_type = counts.get("by_type") or {}
        for queue_type in ["claim_candidate", "source_safety", "omission_risk", "workflow_blocker"]:
            if by_type.get(queue_type, 0) <= 0:
                issues.append(f"missing queue type: {queue_type}")
        for item in queue.get("items") or []:
            if item.get("queue_type") == "claim_candidate" and item.get("claim_support_allowed") is not False:
                issues.append("claim candidate item allows claim support")
            if item.get("queue_type") == "source_safety" and item.get("safety_checked_clear") is not False:
                issues.append("source safety item is checked clear")
            if item.get("queue_type") == "omission_risk" and item.get("literature_completeness_allowed") is not False:
                issues.append("omission risk item allows completeness")
            if item.get("queue_type") == "workflow_blocker" and item.get("ready_for_prose") is not False:
                issues.append("workflow blocker item allows prose readiness")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": workflow["returncode"],
            "review_queue_counts": counts,
            "what_is_not_concluded": queue.get("what_is_not_concluded", []),
        }


def _single_confirmation_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-m15-single-confirmation-") as tmp:
        mission_dir = Path(tmp) / "mission"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "run-public-source-workflow",
                "--topic",
                "Neural Optimal Transport for generative modeling and inference",
                "--seed",
                "arxiv:2201.12220v3",
                "--out",
                str(mission_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        text = completed.stdout + completed.stderr
        if completed.returncode != 0:
            issues.append(f"command failed: {text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": completed.returncode}
        payload = json.loads(completed.stdout)
        mission_path = Path(payload.get("mission_control_path") or "")
        next_action_path = Path(payload.get("next_action_path") or "")
        mission = json.loads(mission_path.read_text()) if mission_path.exists() else {}
        next_action = json.loads(next_action_path.read_text()) if next_action_path.exists() else {}
        confirmation = payload.get("public_discovery_confirmation") or {}
        next_confirmation = next_action.get("public_discovery_confirmation") or {}
        forbidden = mission.get("forbidden_actions") or []
        safe_next_commands = next_action.get("safe_next_commands") or []

        if confirmation.get("schema_version") != "ra-survey-public-discovery-confirmation-v1":
            issues.append("missing public discovery confirmation schema")
        if confirmation.get("confirmed") is not False:
            issues.append("unconfirmed path should record confirmed=false")
        if confirmation.get("status") != "confirmation_required":
            issues.append("unconfirmed path should require confirmation")
        if confirmation.get("question") != "Do you want RA to search public web/archive sources for this idea or paper?":
            issues.append("confirmation question text changed or missing")
        if next_confirmation != confirmation:
            issues.append("next_action does not preserve the same confirmation object")
        if payload.get("next_gate", {}).get("status") != "public_discovery_confirmation_or_existing_artifact_required":
            issues.append("missing public discovery confirmation gate")
        if next_action.get("approval_required") is not True:
            issues.append("unconfirmed public discovery gate should require the single approval")
        if not any("ask once" in command and "public web/archive" in command for command in safe_next_commands):
            issues.append("safe next commands do not ask once for public discovery")
        if not any("do not run public discovery before public_discovery_confirmation.confirmed is true" in action for action in forbidden):
            issues.append("mission forbidden actions do not forbid implicit public discovery")
        if mission.get("phase_statuses", {}).get("public_metadata", {}).get("exists") is not False:
            issues.append("unconfirmed workflow should not create public metadata")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "confirmation_status": confirmation.get("status"),
            "confirmed": confirmation.get("confirmed"),
            "gate_status": payload.get("next_gate", {}).get("status"),
            "mission_status": payload.get("status"),
            "what_is_not_concluded": payload.get("what_is_not_concluded", []),
        }


def _confirmed_source_scope_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-m15-confirmed-source-") as tmp:
        mission_dir = Path(tmp) / "mission"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "run-public-source-workflow",
                "--topic",
                "Neural Optimal Transport for generative modeling and inference",
                "--seed",
                "arxiv:2201.12220v3",
                "--out",
                str(mission_dir),
                "--metadata-dir",
                str(PHASE2_METADATA),
                "--confirm-public-discovery",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        text = completed.stdout + completed.stderr
        if completed.returncode != 0:
            issues.append(f"command failed: {text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": completed.returncode}
        payload = json.loads(completed.stdout)
        mission_path = Path(payload.get("mission_control_path") or "")
        next_action_path = Path(payload.get("next_action_path") or "")
        mission = json.loads(mission_path.read_text()) if mission_path.exists() else {}
        next_action = json.loads(next_action_path.read_text()) if next_action_path.exists() else {}
        confirmation = payload.get("public_discovery_confirmation") or {}
        gate = payload.get("next_gate") or {}
        safe_next_commands = next_action.get("safe_next_commands") or []
        actions = mission.get("actions") or []

        if confirmation.get("confirmed") is not True:
            issues.append("confirmed path should record confirmed=true")
        if gate.get("gate_id") != "source_intake":
            issues.append(f"expected source_intake gate, got {gate.get('gate_id')}")
        if gate.get("status") != "blocked_missing_public_source_intake_artifact":
            issues.append(f"unexpected source_intake status: {gate.get('status')}")
        if gate.get("approval_required") is not False:
            issues.append("source/status artifact blocker should not request a second ordinary approval")
        if gate.get("covered_by_public_discovery") is not True:
            issues.append("source/status artifact blocker is not marked covered by public discovery")
        if gate.get("implementation_or_artifact_blocker") is not True:
            issues.append("source/status gate should remain an implementation/artifact blocker")
        if not any("do not request a second ordinary public source/archive approval" in command for command in safe_next_commands):
            issues.append("safe next commands do not forbid a second ordinary source/archive approval")
        if any(action.get("action") == "survey_build_public_metadata" for action in actions):
            issues.append("metadata-dir path should reuse the existing metadata artifact instead of rerunning discovery")
        if mission.get("phase_statuses", {}).get("public_metadata", {}).get("exists") is not True:
            issues.append("confirmed workflow did not see existing public metadata")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "confirmed": confirmation.get("confirmed"),
            "gate_status": gate.get("status"),
            "approval_required": gate.get("approval_required"),
            "covered_by_public_discovery": gate.get("covered_by_public_discovery"),
            "implementation_or_artifact_blocker": gate.get("implementation_or_artifact_blocker"),
            "what_is_not_concluded": payload.get("what_is_not_concluded", []),
        }


def _claim_review_import_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-claim-review-") as tmp:
        mission_dir = Path(tmp) / "mission"
        workflow = _run_public_source_workflow(mission_dir)
        if workflow["returncode"] != 0:
            issues.append(f"workflow command failed: {workflow['text'].strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        payload = json.loads(workflow["stdout"])
        review_queue_path = Path(payload.get("review_queue_path") or "")
        if not review_queue_path.exists():
            issues.append("review_queue_path missing or does not exist")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        queue = json.loads(review_queue_path.read_text())
        claim_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "claim_candidate"]
        if not claim_items:
            issues.append("no claim_candidate item available for local import smoke")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        decisions_path = Path(tmp) / "reviewed_claim_decisions.json"
        import_dir = Path(tmp) / "reviewed_claims"
        decisions_path.write_text(json.dumps(_bound_review_decisions(
            review_queue_path,
            queue,
            "claim_candidate",
            [
                {
                    "queue_item_id": item["item_id"],
                    "claim_id": f"phase8_local_reviewed_claim_{index:03d}",
                    "claim_text": "The checked source anchor is relevant to the method discussion.",
                    "paper_ids": item.get("paper_ids") or [],
                    "anchor_ids": item.get("anchor_ids") or [],
                    "review_status": "human_reviewed_passed",
                    "support_class": "primary_technical_support",
                    "reviewer": "phase8-local-validator",
                    "reviewed_at": "2026-07-10T00:00:00Z",
                    "evidence_note": "Local validation of reviewed-claim import plumbing; not a scientific claim.",
                }
                for index, item in enumerate(claim_items, start=1)
            ],
        ), indent=2, sort_keys=True))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "import-claim-review",
                "--review-queue",
                str(review_queue_path),
                "--decisions",
                str(decisions_path),
                "--out",
                str(import_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        text = completed.stdout + completed.stderr
        if completed.returncode != 0:
            issues.append(f"import command failed: {text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": completed.returncode}
        import_payload = json.loads(completed.stdout)
        reviewed_claims_path = Path(import_payload.get("reviewed_claims_path") or "")
        if not reviewed_claims_path.exists():
            issues.append("reviewed_claims_path missing or does not exist")
            reviewed_claims = {}
        else:
            reviewed_claims = json.loads(reviewed_claims_path.read_text())
        claims = reviewed_claims.get("claims") or []
        first_claim = claims[0] if claims else {}
        if reviewed_claims.get("accepted_claim_count") != len(claim_items):
            issues.append("accepted_claim_count should equal the selected claim-item count")
        if reviewed_claims.get("rejected_claim_count") != 0:
            issues.append("rejected_claim_count should be 0")
        if reviewed_claims.get("decision_coverage_complete") is not True:
            issues.append("reviewed claim import did not establish exact decision coverage")
        if reviewed_claims.get("ready_for_prose") is not False:
            issues.append("reviewed claim import promoted ready_for_prose")
        if first_claim.get("claim_support_allowed") is not True:
            issues.append("accepted claim did not allow claim support")
        if first_claim.get("source_safety_required") is not True:
            issues.append("accepted claim did not preserve source safety requirement")
        if first_claim.get("omission_review_required") is not True:
            issues.append("accepted claim did not preserve omission review requirement")
        if first_claim.get("ready_for_prose") is not False:
            issues.append("accepted claim promoted prose readiness")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "accepted_claim_count": reviewed_claims.get("accepted_claim_count"),
            "rejected_claim_count": reviewed_claims.get("rejected_claim_count"),
            "decision_coverage_complete": reviewed_claims.get("decision_coverage_complete"),
            "ready_for_prose": reviewed_claims.get("ready_for_prose"),
            "source_safety_required": first_claim.get("source_safety_required"),
            "omission_review_required": first_claim.get("omission_review_required"),
            "what_is_not_concluded": reviewed_claims.get("what_is_not_concluded", []),
        }


def _source_safety_import_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-source-safety-") as tmp:
        mission_dir = Path(tmp) / "mission"
        workflow = _run_public_source_workflow(mission_dir)
        if workflow["returncode"] != 0:
            issues.append(f"workflow command failed: {workflow['text'].strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        payload = json.loads(workflow["stdout"])
        review_queue_path = Path(payload.get("review_queue_path") or "")
        if not review_queue_path.exists():
            issues.append("review_queue_path missing or does not exist")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        queue = json.loads(review_queue_path.read_text())
        safety_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "source_safety"]
        if not safety_items:
            issues.append("no source_safety item available for local import smoke")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        decisions_path = Path(tmp) / "reviewed_source_safety_decisions.json"
        import_dir = Path(tmp) / "reviewed_source_safety"
        decisions_path.write_text(json.dumps(_bound_review_decisions(
            review_queue_path,
            queue,
            "source_safety",
            [
                {
                    "queue_item_id": item["item_id"],
                    "paper_id": item["paper_id"],
                    "checked_status": "checked_clear",
                    "evidence_type": "public_status_check",
                    "evidence_source": "phase8-local-public-status-ledger",
                    "reviewer": "phase8-local-validator",
                    "reviewed_at": "2026-07-10T00:00:00Z",
                    "evidence_note": "Local validation of source-safety import plumbing; not a live status claim.",
                }
                for item in safety_items
            ],
        ), indent=2, sort_keys=True))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "import-source-safety-review",
                "--review-queue",
                str(review_queue_path),
                "--decisions",
                str(decisions_path),
                "--out",
                str(import_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        text = completed.stdout + completed.stderr
        if completed.returncode != 0:
            issues.append(f"import command failed: {text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": completed.returncode}
        import_payload = json.loads(completed.stdout)
        reviewed_source_safety_path = Path(import_payload.get("reviewed_source_safety_path") or "")
        if not reviewed_source_safety_path.exists():
            issues.append("reviewed_source_safety_path missing or does not exist")
            reviewed_source_safety = {}
        else:
            reviewed_source_safety = json.loads(reviewed_source_safety_path.read_text())
        rows = reviewed_source_safety.get("source_safety") or []
        first_row = rows[0] if rows else {}
        if reviewed_source_safety.get("accepted_source_safety_count") != len(safety_items):
            issues.append("accepted_source_safety_count should equal the selected source-safety-item count")
        if reviewed_source_safety.get("rejected_source_safety_count") != 0:
            issues.append("rejected_source_safety_count should be 0")
        if reviewed_source_safety.get("decision_coverage_complete") is not True:
            issues.append("source-safety import did not establish exact decision coverage")
        if reviewed_source_safety.get("ready_for_prose") is not False:
            issues.append("source-safety import promoted ready_for_prose")
        if first_row.get("safety_checked_clear") is not True:
            issues.append("accepted source-safety row was not checked clear")
        if first_row.get("ready_for_prose") is not False:
            issues.append("accepted source-safety row promoted prose readiness")
        if first_row.get("omission_review_required") is not True:
            issues.append("accepted source-safety row did not preserve omission review requirement")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "accepted_source_safety_count": reviewed_source_safety.get("accepted_source_safety_count"),
            "rejected_source_safety_count": reviewed_source_safety.get("rejected_source_safety_count"),
            "decision_coverage_complete": reviewed_source_safety.get("decision_coverage_complete"),
            "checked_clear_count": reviewed_source_safety.get("checked_clear_count"),
            "ready_for_prose": reviewed_source_safety.get("ready_for_prose"),
            "omission_review_required": first_row.get("omission_review_required"),
            "what_is_not_concluded": reviewed_source_safety.get("what_is_not_concluded", []),
        }


def _omission_import_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-omission-") as tmp:
        mission_dir = Path(tmp) / "mission"
        workflow = _run_public_source_workflow(mission_dir)
        if workflow["returncode"] != 0:
            issues.append(f"workflow command failed: {workflow['text'].strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        payload = json.loads(workflow["stdout"])
        review_queue_path = Path(payload.get("review_queue_path") or "")
        if not review_queue_path.exists():
            issues.append("review_queue_path missing or does not exist")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        queue = json.loads(review_queue_path.read_text())
        omission_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "omission_risk"]
        if not omission_items:
            issues.append("no omission_risk item available for local import smoke")
            return {"status": "failed", "issues": issues, "returncode": workflow["returncode"]}

        decisions_path = Path(tmp) / "reviewed_omission_decisions.json"
        import_dir = Path(tmp) / "reviewed_omissions"
        decisions_path.write_text(json.dumps(_bound_review_decisions(
            review_queue_path,
            queue,
            "omission_risk",
            [
                {
                    "queue_item_id": item["item_id"],
                    "risk_id": item["risk_id"],
                    "decision": "must_inspect",
                    "reason": "Local validation keeps omission risk open for source-aware review.",
                    "next_action": "Inspect or justify this omission before prose readiness.",
                    "reviewer": "phase8-local-validator",
                    "reviewed_at": "2026-07-10T00:00:00Z",
                }
                for item in omission_items
            ],
        ), indent=2, sort_keys=True))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "import-omission-review",
                "--review-queue",
                str(review_queue_path),
                "--decisions",
                str(decisions_path),
                "--out",
                str(import_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        text = completed.stdout + completed.stderr
        if completed.returncode != 0:
            issues.append(f"import command failed: {text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": completed.returncode}
        import_payload = json.loads(completed.stdout)
        reviewed_omission_path = Path(import_payload.get("reviewed_omission_risks_path") or "")
        if not reviewed_omission_path.exists():
            issues.append("reviewed_omission_risks_path missing or does not exist")
            reviewed_omissions = {}
        else:
            reviewed_omissions = json.loads(reviewed_omission_path.read_text())
        rows = reviewed_omissions.get("omission_risks") or []
        first_row = rows[0] if rows else {}
        if reviewed_omissions.get("accepted_omission_count") != len(omission_items):
            issues.append("accepted_omission_count should equal the selected omission-item count")
        if reviewed_omissions.get("rejected_omission_count") != 0:
            issues.append("rejected_omission_count should be 0")
        if reviewed_omissions.get("decision_coverage_complete") is not True:
            issues.append("omission import did not establish exact decision coverage")
        if reviewed_omissions.get("ready_for_prose") is not False:
            issues.append("omission import promoted ready_for_prose")
        if reviewed_omissions.get("literature_completeness_allowed") is not False:
            issues.append("omission import claimed literature completeness")
        if first_row.get("literature_completeness_allowed") is not False:
            issues.append("accepted omission row allowed literature completeness")
        if first_row.get("ready_for_prose") is not False:
            issues.append("accepted omission row promoted prose readiness")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "accepted_omission_count": reviewed_omissions.get("accepted_omission_count"),
            "rejected_omission_count": reviewed_omissions.get("rejected_omission_count"),
            "decision_coverage_complete": reviewed_omissions.get("decision_coverage_complete"),
            "open_omission_count": reviewed_omissions.get("open_omission_count"),
            "ready_for_prose": reviewed_omissions.get("ready_for_prose"),
            "literature_completeness_allowed": reviewed_omissions.get("literature_completeness_allowed"),
            "what_is_not_concluded": reviewed_omissions.get("what_is_not_concluded", []),
        }


def _reviewed_evidence_merge_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-merge-") as tmp:
        sidecars = _build_review_sidecars(Path(tmp), issues)
        if not sidecars:
            return {"status": "failed", "issues": issues, "returncode": 1}

        merge_dir = Path(tmp) / "reviewed_evidence_merge"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "merge-reviewed-evidence",
                "--review-queue",
                str(sidecars["review_queue"]),
                "--reviewed-claims",
                str(sidecars["reviewed_claims"]),
                "--reviewed-source-safety",
                str(sidecars["reviewed_source_safety"]),
                "--reviewed-omissions",
                str(sidecars["reviewed_omissions"]),
                "--reviewed-workflow-blockers",
                str(sidecars["reviewed_workflow_blockers"]),
                "--out",
                str(merge_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        merge_payload = _require_legacy_authority_veto(
            completed,
            label="merge",
            forbidden_paths=[merge_dir],
            readiness_fields=["ready_for_reviewed_packet", "ready_for_prose"],
            issues=issues,
        )
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "validation_mode": "legacy_authority_promotion_veto",
            "blocked_reason": merge_payload.get("blocked_reason"),
            "legacy_authority_rejected": merge_payload.get("blocked_reason") == "legacy_evidence_authority",
            "merge_artifact_written": merge_dir.exists() or merge_dir.is_symlink(),
            "ready_for_reviewed_packet": merge_payload.get("ready_for_reviewed_packet"),
            "ready_for_prose": merge_payload.get("ready_for_prose"),
            "what_is_not_concluded": merge_payload.get("what_is_not_concluded", []),
        }


def _workflow_blocker_import_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-workflow-review-") as tmp:
        sidecars = _build_review_sidecars(Path(tmp), issues)
        if not sidecars:
            return {"status": "failed", "issues": issues, "returncode": 1}
        queue = json.loads(sidecars["review_queue"].read_text())
        reviewed = json.loads(sidecars["reviewed_workflow_blockers"].read_text())
        workflow_items = [
            item for item in queue.get("items") or []
            if item.get("queue_type") == "workflow_blocker"
        ]
        if reviewed.get("accepted_workflow_blocker_count") != len(workflow_items):
            issues.append("accepted workflow-blocker count differs from the selected queue")
        if reviewed.get("rejected_workflow_blocker_count") != 0:
            issues.append("workflow-blocker import unexpectedly rejected a fixture decision")
        if reviewed.get("decision_coverage_complete") is not True:
            issues.append("workflow-blocker import did not establish exact decision coverage")
        if reviewed.get("ready_for_reviewed_packet") is not False:
            issues.append("workflow-blocker importer claimed reviewed-packet readiness")
        if reviewed.get("ready_for_prose") is not False:
            issues.append("workflow-blocker importer claimed prose readiness")
        upstream_count = sum(
            item.get("resolution_class") == "upstream_repair_required"
            for item in workflow_items
        )
        if reviewed.get("open_workflow_blocker_count") != upstream_count:
            issues.append("upstream-only workflow blockers were not preserved as open")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": 0,
            "accepted_workflow_blocker_count": reviewed.get("accepted_workflow_blocker_count"),
            "rejected_workflow_blocker_count": reviewed.get("rejected_workflow_blocker_count"),
            "open_workflow_blocker_count": reviewed.get("open_workflow_blocker_count"),
            "decision_coverage_complete": reviewed.get("decision_coverage_complete"),
            "ready_for_reviewed_packet": reviewed.get("ready_for_reviewed_packet"),
            "ready_for_prose": reviewed.get("ready_for_prose"),
            "what_is_not_concluded": reviewed.get("what_is_not_concluded", []),
        }


def _resume_orchestration_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-resume-") as tmp:
        sidecars = _build_review_sidecars(Path(tmp), issues)
        if not sidecars:
            return {"status": "failed", "issues": issues, "returncode": 1}

        merge_dir = sidecars["mission_dir"] / "reviewed_evidence"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "merge-reviewed-evidence",
                "--review-queue",
                str(sidecars["review_queue"]),
                "--reviewed-claims",
                str(sidecars["reviewed_claims"]),
                "--reviewed-source-safety",
                str(sidecars["reviewed_source_safety"]),
                "--reviewed-omissions",
                str(sidecars["reviewed_omissions"]),
                "--reviewed-workflow-blockers",
                str(sidecars["reviewed_workflow_blockers"]),
                "--out",
                str(merge_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        merge_payload = _require_legacy_authority_veto(
            completed,
            label="resume preflight merge",
            forbidden_paths=[merge_dir],
            readiness_fields=["ready_for_reviewed_packet", "ready_for_prose"],
            issues=issues,
        )

        resume = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "run-public-source-workflow",
                "--topic",
                "Neural Optimal Transport for generative modeling and inference",
                "--seed",
                "arxiv:2201.12220v3",
                "--out",
                str(sidecars["mission_dir"]),
                "--metadata-dir",
                str(PHASE2_METADATA),
                "--source-status-dir",
                str(PHASE4_SOURCE_STATUS),
                "--anchor-dir",
                str(PHASE5_ANCHORS),
                "--packet-dir",
                str(PHASE6_PACKET),
                "--resume",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        resume_text = resume.stdout + resume.stderr
        if resume.returncode != 0:
            issues.append(f"resume command failed: {resume_text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": resume.returncode}
        payload = json.loads(resume.stdout)
        mission_path = Path(payload.get("mission_control_path") or "")
        next_action_path = Path(payload.get("next_action_path") or "")
        mission = json.loads(mission_path.read_text()) if mission_path.exists() else {}
        next_action = json.loads(next_action_path.read_text()) if next_action_path.exists() else {}
        reviewed_artifacts = mission.get("reviewed_artifacts") or {}
        if payload.get("review_queue_reused") is not True:
            issues.append("resume did not reuse existing review_queue.json")
        if next_action.get("action_id") != "merge_reviewed_evidence":
            issues.append(f"unexpected next action: {next_action.get('action_id')}")
        if merge_dir.exists() or merge_dir.is_symlink():
            issues.append("resume observed a reviewed-evidence descendant after the legacy-authority veto")
        if not all((reviewed_artifacts.get(name) or {}).get("exists") is True for name in [
            "reviewed_claims",
            "reviewed_source_safety",
            "reviewed_omissions",
            "reviewed_workflow_blockers",
        ]):
            issues.append("resume did not preserve all diagnostic legacy review sidecars")
        if (reviewed_artifacts.get("reviewed_evidence") or {}).get("exists") is not False:
            issues.append("resume treated a legacy reviewed-evidence descendant as present")
        if not any("merge-reviewed-evidence" in command for command in next_action.get("safe_next_commands") or []):
            issues.append("resume next action missing the explicit merge command that will enforce the legacy veto")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": resume.returncode,
            "validation_mode": "legacy_authority_promotion_veto",
            "blocked_reason": merge_payload.get("blocked_reason"),
            "legacy_authority_rejected": merge_payload.get("blocked_reason") == "legacy_evidence_authority",
            "action_id": next_action.get("action_id"),
            "next_action_status": next_action.get("status"),
            "review_queue_reused": payload.get("review_queue_reused"),
            "merge_artifact_written": merge_dir.exists() or merge_dir.is_symlink(),
            "ready_for_reviewed_packet": merge_payload.get("ready_for_reviewed_packet"),
            "ready_for_prose": merge_payload.get("ready_for_prose"),
            "what_is_not_concluded": next_action.get("what_is_not_concluded", []),
        }


def _coverage_ledgers_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-coverage-") as tmp:
        output = Path(tmp) / "coverage_ledgers"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "coverage-ledgers",
                "--topic",
                "Neural Optimal Transport for generative modeling and inference",
                "--packet-dir",
                str(PHASE6_PACKET),
                "--out",
                str(output),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        text = completed.stdout + completed.stderr
        if completed.returncode != 0:
            issues.append(f"coverage-ledgers command failed: {text.strip()[:500]}")
            return {"status": "failed", "issues": issues, "returncode": completed.returncode}
        payload = json.loads(completed.stdout)
        manifest_path = output / "coverage_manifest.json"
        backward_path = output / "backward_snowball.json"
        forward_path = output / "forward_snowball.json"
        omitted_path = output / "omitted_paper_risks.json"
        citation_path = output / "citation_venue_metadata.json"
        for path in [manifest_path, backward_path, forward_path, omitted_path, citation_path]:
            if not path.exists():
                issues.append(f"missing coverage artifact: {path.name}")
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        backward = json.loads(backward_path.read_text()) if backward_path.exists() else {}
        forward = json.loads(forward_path.read_text()) if forward_path.exists() else {}
        omitted = json.loads(omitted_path.read_text()) if omitted_path.exists() else {}
        citation = json.loads(citation_path.read_text()) if citation_path.exists() else {}
        if payload.get("ready_for_prose") is not False:
            issues.append("coverage ledgers promoted ready_for_prose")
        if backward.get("evidence_policy", {}).get("metadata_relations_support_technical_claims") is not False:
            issues.append("backward ledger allows metadata technical support")
        if forward.get("evidence_policy", {}).get("metadata_relations_support_completeness_claims") is not False:
            issues.append("forward ledger allows metadata completeness support")
        if citation.get("metadata_policy", {}).get("citation_counts_are_coverage_signals_only") is not True:
            issues.append("citation metadata policy does not mark citation counts as coverage signals")
        if omitted.get("review_policy", {}).get("omission_visibility_is_not_literature_completeness") is not True:
            issues.append("omitted risk policy allows completeness from visibility")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": completed.returncode,
            "backward_status": manifest.get("backward_status"),
            "forward_status": manifest.get("forward_status"),
            "omitted_risk_count": manifest.get("omitted_risk_count"),
            "requires_live_metadata_or_source_expansion": manifest.get("requires_live_metadata_or_source_expansion"),
            "ready_for_prose": manifest.get("ready_for_prose"),
            "what_is_not_concluded": manifest.get("what_is_not_concluded", []),
        }


def _hostile_review_report() -> dict[str, Any]:
    issues = []
    with tempfile.TemporaryDirectory(prefix="ra-survey-phase8-hostile-") as tmp:
        tmp_dir = Path(tmp)
        sidecars = _build_review_sidecars(tmp_dir, issues, close_omissions=True)
        if not sidecars:
            return {"status": "failed", "issues": issues, "returncode": 1}
        merge_dir = sidecars["mission_dir"] / "reviewed_evidence"
        reviewed_packet_dir = sidecars["mission_dir"] / "reviewed_final_packet"
        hostile_dir = sidecars["mission_dir"] / "hostile_review"
        merge = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "merge-reviewed-evidence",
                "--review-queue",
                str(sidecars["review_queue"]),
                "--reviewed-claims",
                str(sidecars["reviewed_claims"]),
                "--reviewed-source-safety",
                str(sidecars["reviewed_source_safety"]),
                "--reviewed-omissions",
                str(sidecars["reviewed_omissions"]),
                "--reviewed-workflow-blockers",
                str(sidecars["reviewed_workflow_blockers"]),
                "--out",
                str(merge_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        merge_payload = _require_legacy_authority_veto(
            merge,
            label="hostile preflight merge",
            forbidden_paths=[merge_dir],
            readiness_fields=["ready_for_reviewed_packet", "ready_for_prose"],
            issues=issues,
        )
        reviewed_packet = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "compose-reviewed-final-packet",
                "--mission-root",
                str(sidecars["mission_dir"]),
                "--review-queue",
                str(sidecars["review_queue"]),
                "--packet-dir",
                str(PHASE6_PACKET),
                "--anchor-dir",
                str(PHASE5_ANCHORS),
                "--out",
                str(reviewed_packet_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        reviewed_packet_payload = _require_legacy_authority_veto(
            reviewed_packet,
            label="reviewed packet",
            forbidden_paths=[reviewed_packet_dir],
            readiness_fields=["ready_for_reviewed_packet", "ready_for_hostile_review", "ready_for_prose"],
            issues=issues,
        )
        hostile = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_assistant.cli",
                "survey",
                "hostile-review",
                "--reviewed-final-packet",
                str(reviewed_packet_dir / "reviewed_final_packet.json"),
                "--mission-root",
                str(sidecars["mission_dir"]),
                "--review-queue",
                str(sidecars["review_queue"]),
                "--packet-dir",
                str(PHASE6_PACKET),
                "--anchor-dir",
                str(PHASE5_ANCHORS),
                "--out",
                str(hostile_dir),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            check=False,
            capture_output=True,
            text=True,
        )
        payload = _require_legacy_authority_veto(
            hostile,
            label="hostile review",
            forbidden_paths=[hostile_dir],
            readiness_fields=["ready_for_hostile_review", "ready_for_prose"],
            issues=issues,
        )
        result_path = hostile_dir / "hostile_review_result.json"
        readiness_path = hostile_dir / "final_packet_readiness.json"
        if result_path.exists() or result_path.is_symlink() or readiness_path.exists() or readiness_path.is_symlink():
            issues.append("legacy authority produced hostile-result or readiness residue")
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "returncode": hostile.returncode,
            "validation_mode": "legacy_authority_promotion_veto",
            "blocked_reason": payload.get("blocked_reason"),
            "legacy_authority_rejected": all(
                value.get("blocked_reason") == "legacy_evidence_authority"
                for value in (merge_payload, reviewed_packet_payload, payload)
            ),
            "merge_artifact_written": merge_dir.exists() or merge_dir.is_symlink(),
            "reviewed_packet_written": reviewed_packet_dir.exists() or reviewed_packet_dir.is_symlink(),
            "hostile_artifact_written": hostile_dir.exists() or hostile_dir.is_symlink(),
            "ready_for_hostile_review": payload.get("ready_for_hostile_review"),
            "ready_for_prose": payload.get("ready_for_prose"),
            "what_is_not_concluded": payload.get("what_is_not_concluded", []),
        }


def _build_review_sidecars(
    tmp_dir: Path,
    issues: list[str],
    *,
    close_omissions: bool = False,
) -> dict[str, Path] | None:
    mission_dir = tmp_dir / "mission"
    workflow = _run_public_source_workflow(mission_dir)
    if workflow["returncode"] != 0:
        issues.append(f"workflow command failed: {workflow['text'].strip()[:500]}")
        return None
    payload = json.loads(workflow["stdout"])
    review_queue_path = Path(payload.get("review_queue_path") or "")
    if not review_queue_path.exists():
        issues.append("review_queue_path missing or does not exist")
        return None
    queue = json.loads(review_queue_path.read_text())
    claim_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "claim_candidate"]
    safety_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "source_safety"]
    omission_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "omission_risk"]
    workflow_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "workflow_blocker"]
    if not (claim_items and safety_items and omission_items and workflow_items):
        issues.append("review queue missing claim, source-safety, omission, or workflow-blocker item")
        return None

    claim_decisions = tmp_dir / "merge_claim_decisions.json"
    claim_decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        "claim_candidate",
        [
            {
                "queue_item_id": item["item_id"],
                "claim_id": f"phase8_merge_claim_{index:03d}",
                "claim_text": "The checked source anchor is relevant to the method discussion.",
                "paper_ids": item.get("paper_ids") or [],
                "anchor_ids": item.get("anchor_ids") or [],
                "review_status": "human_reviewed_passed",
                "support_class": "primary_technical_support",
                "reviewer": "phase8-local-validator",
                "reviewed_at": "2026-07-10T00:00:00Z",
                "evidence_note": "Local validation of merge plumbing; not a scientific claim.",
            }
            for index, item in enumerate(claim_items, start=1)
        ],
    ), indent=2, sort_keys=True))
    claim_dir = mission_dir / "reviewed_claims"
    if _run_import_command([
        "import-claim-review",
        "--review-queue",
        str(review_queue_path),
        "--decisions",
        str(claim_decisions),
        "--out",
        str(claim_dir),
    ], issues) != 0:
        return None

    safety_decisions = tmp_dir / "merge_safety_decisions.json"
    safety_decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        "source_safety",
        [
            {
                "queue_item_id": item["item_id"],
                "paper_id": item["paper_id"],
                "checked_status": "checked_clear",
                "evidence_type": "public_status_check",
                "evidence_source": "phase8-local-public-status-ledger",
                "reviewer": "phase8-local-validator",
                "reviewed_at": "2026-07-10T00:00:00Z",
                "evidence_note": "Local validation of merge plumbing; not a live status claim.",
            }
            for item in safety_items
        ],
    ), indent=2, sort_keys=True))
    safety_dir = mission_dir / "reviewed_source_safety"
    if _run_import_command([
        "import-source-safety-review",
        "--review-queue",
        str(review_queue_path),
        "--decisions",
        str(safety_decisions),
        "--out",
        str(safety_dir),
    ], issues) != 0:
        return None

    omission_decisions = tmp_dir / "merge_omission_decisions.json"
    omission_decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        "omission_risk",
        [
            {
                "queue_item_id": item["item_id"],
                "risk_id": item["risk_id"],
                "decision": "acceptable_omission" if close_omissions else "must_inspect",
                "reason": "Local validation records an explicit bounded-scope omission decision.",
                **(
                    {"scope_basis": "Closed only for this local UX replay scope."}
                    if close_omissions
                    else {"next_action": "Inspect or justify this omission before prose readiness."}
                ),
                "reviewer": "phase8-local-validator",
                "reviewed_at": "2026-07-10T00:00:00Z",
            }
            for item in omission_items
        ],
    ), indent=2, sort_keys=True))
    omission_dir = mission_dir / "reviewed_omissions"
    if _run_import_command([
        "import-omission-review",
        "--review-queue",
        str(review_queue_path),
        "--decisions",
        str(omission_decisions),
        "--out",
        str(omission_dir),
    ], issues) != 0:
        return None

    workflow_decisions = tmp_dir / "merge_workflow_blocker_decisions.json"
    workflow_decisions.write_text(json.dumps(_bound_review_decisions(
        review_queue_path,
        queue,
        "workflow_blocker",
        [
            {
                "queue_item_id": item["item_id"],
                "disposition": "resolved_by_reviewed_evidence",
                "evidence_queue_item_ids": item["required_evidence_queue_item_ids"],
                "rationale": "The exact current fixture review decisions address this aggregate blocker structurally.",
                "reviewer": "phase8-local-validator",
                "reviewed_at": "2026-07-10T00:00:00Z",
            }
            if item["resolution_class"] != "upstream_repair_required"
            else {
                "queue_item_id": item["item_id"],
                "disposition": "remains_open",
                "rationale": "This blocker requires an upstream artifact repair.",
                "next_action": "Repair the named upstream artifact and rebuild the selected queue.",
                "reviewer": "phase8-local-validator",
                "reviewed_at": "2026-07-10T00:00:00Z",
            }
            for item in workflow_items
        ],
    ), indent=2, sort_keys=True))
    workflow_dir = mission_dir / "reviewed_workflow_blockers"
    if _run_import_command([
        "import-workflow-blocker-review",
        "--review-queue",
        str(review_queue_path),
        "--decisions",
        str(workflow_decisions),
        "--out",
        str(workflow_dir),
    ], issues) != 0:
        return None

    return {
        "mission_dir": mission_dir,
        "review_queue": review_queue_path,
        "coverage_dir": review_queue_path.parent / "coverage",
        "reviewed_claims": claim_dir / "reviewed_claims.json",
        "reviewed_source_safety": safety_dir / "reviewed_source_safety.json",
        "reviewed_omissions": omission_dir / "reviewed_omission_risks.json",
        "reviewed_workflow_blockers": workflow_dir / "reviewed_workflow_blockers.json",
    }


def _bound_review_decisions(
    review_queue_path: Path,
    queue: dict[str, Any],
    decision_type: str,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "ra-survey-review-decisions-v2",
        "decision_type": decision_type,
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "artifact_set_id": queue["artifact_set_id"],
        "queue_semantic_sha256": queue["queue_semantic_sha256"],
        "review_queue_sha256": hashlib.sha256(review_queue_path.read_bytes()).hexdigest(),
        "decisions": decisions,
    }


def _run_import_command(args: list[str], issues: list[str]) -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "research_assistant.cli", "survey", *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": "src"},
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        issues.append(f"{args[0]} failed: {(completed.stdout + completed.stderr).strip()[:500]}")
    return completed.returncode


def _run_public_source_workflow(mission_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "research_assistant.cli",
        "survey",
        "run-public-source-workflow",
        "--topic",
        "Neural Optimal Transport for generative modeling and inference",
        "--seed",
        "arxiv:2201.12220v3",
        "--out",
        str(mission_dir),
        "--metadata-dir",
        str(PHASE2_METADATA),
        "--source-status-dir",
        str(PHASE4_SOURCE_STATUS),
        "--anchor-dir",
        str(PHASE5_ANCHORS),
        "--packet-dir",
        str(PHASE6_PACKET),
    ]
    completed = _run_cli(command)
    if completed.returncode == 0:
        payload = json.loads(completed.stdout)
        if (payload.get("next_action") or {}).get("action_id") == "resume_to_initialize_artifact_state":
            completed = _run_cli([*command, "--resume"])
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "text": completed.stdout + completed.stderr,
    }


def _run_cli(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": "src"},
        check=False,
        capture_output=True,
        text=True,
    )


def _require_legacy_authority_veto(
    completed: subprocess.CompletedProcess[str],
    *,
    label: str,
    forbidden_paths: list[Path],
    readiness_fields: list[str],
    issues: list[str],
) -> dict[str, Any]:
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        issues.append(f"{label} did not emit JSON: {(completed.stdout + completed.stderr).strip()[:500]}")
        payload = {}
    if completed.returncode != 1:
        issues.append(f"{label} returncode={completed.returncode}; expected the explicit legacy-authority veto")
    if payload.get("blocked_reason") != "legacy_evidence_authority":
        issues.append(f"{label} blocked_reason={payload.get('blocked_reason')}; expected legacy_evidence_authority")
    for field in readiness_fields:
        if payload.get(field) is not False:
            issues.append(f"{label} {field} must remain false")
    for path in forbidden_paths:
        if path.exists() or path.is_symlink():
            issues.append(f"{label} wrote forbidden descendant: {path}")
    return payload


def main() -> int:
    result = run_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
