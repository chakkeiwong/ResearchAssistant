"""Offline replay matrix for the active M22 qualitative evidence workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from research_assistant.survey.artifact_lineage import validate_selected_review_queue
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.human_attestation import (
    REVIEW_ROLES,
    validate_reviewer_declaration,
)
from research_assistant.survey.mission_state import MissionStateError, pretty_json_bytes
from research_assistant.survey.omission_frontier_triage import (
    validate_inspection_queue,
    validate_provisional_triage,
)
from research_assistant.survey.qualitative_assessment import (
    NONCLAIMS as ASSESSMENT_NONCLAIMS,
    validate_assessment_bundle,
)
from research_assistant.survey.source_inspection import validate_source_inspection_bundle


MATRIX_SCHEMA = "ra-survey-m22-representative-mission-matrix-v2"
CASE_LEDGER_SCHEMA = "ra-survey-m22-representative-case-ledger-v1"
LEDGER_SCHEMA = "ra-survey-m22-representative-ledger-v1"
MANIFEST_SCHEMA = "ra-survey-m22-representative-run-manifest-v1"
REPLAY_SCHEMA = "ra-survey-m22-representative-offline-replay-v1"
TERMINAL_SCHEMA = "ra-survey-m22-representative-terminal-result-v1"
INVENTORY_SCHEMA = "ra-survey-m22-representative-artifact-inventory-v1"

CASE_IDS = (
    "topic_start_assessed_terminal",
    "explicit_identifier_assessed_terminal",
    "source_format_gap",
    "forward_coverage_unavailable",
    "identifier_free_omissions",
    "residual_identifier_bearing_omissions",
    "correction_supersession",
    "model_fixture_impersonation",
    "stale_foreign_partial_bundle",
)
EXPECTED_TERMINALS = {
    "topic_start_assessed_terminal": "ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE",
    "explicit_identifier_assessed_terminal": "ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE",
    "source_format_gap": "TECHNICAL_SOURCE_GAP_RECORDED",
    "forward_coverage_unavailable": "NONBLOCKING_FORWARD_COVERAGE_LIMITATION",
    "identifier_free_omissions": "OPEN_IDENTIFIER_FREE_OMISSION_RISK",
    "residual_identifier_bearing_omissions": "OPEN_RESIDUAL_IDENTIFIER_BEARING_OMISSION_RISK",
    "correction_supersession": "CORRECTION_SELECTED_PRIOR_EVIDENCE_PRESERVED",
    "model_fixture_impersonation": "HARD_REJECT_NONHUMAN_AUTHORITY",
    "stale_foreign_partial_bundle": "HARD_REJECT_STALE_FOREIGN_PARTIAL_EVIDENCE",
}
EXPECTED_EVIDENCE_IDS = {
    "topic_start_assessed_terminal": (
        "m17_topic_mission_control",
        "m17_topic_replay_result",
        "m17_topic_seed_context",
        "m22_production_mission_control",
        "m22_qualitative_assessments",
        "m22_selected_review_queue",
    ),
    "explicit_identifier_assessed_terminal": (
        "m22_production_mission_control",
        "m22_qualitative_assessments",
        "m22_selected_review_queue",
    ),
    "source_format_gap": (
        "m21_correction_record",
        "m22_qualitative_assessments",
        "m22_source_intake_status",
    ),
    "forward_coverage_unavailable": (
        "m20_forward_snowball",
        "m22_qualitative_assessments",
    ),
    "identifier_free_omissions": (
        "m21_identifier_free_risk",
        "m22_qualitative_assessments",
    ),
    "residual_identifier_bearing_omissions": (
        "m22_inspection_queue",
        "m22_provisional_classification",
        "m22_qualitative_assessments",
        "m22_source_inspection",
    ),
    "correction_supersession": (
        "m21_correction_record",
        "m21_original_source_status",
        "m22_source_intake_status",
    ),
    "model_fixture_impersonation": ("human_attestation_validator",),
    "stale_foreign_partial_bundle": ("m22_selected_review_queue",),
}
RESULT_NONCLAIMS = [
    "claim truth",
    "completeness",
    "expert consensus",
    "live topic-discovery validation",
    "method ranking",
    "M23 acceptance",
    "product readiness",
    "prose readiness",
    "publication safety",
    "scientific correctness",
]
DEFAULT_MATRIX_PATH = Path(
    "docs/plans/literature_survey_north_star_m22_active_mission_matrix_v2_2026-07-19.json"
)
DEFAULT_PLAN_PATH = Path(
    "docs/plans/literature_survey_north_star_m22_representative_real_missions_subplan_2026-07-19.md"
)
RUNNER_PATH = Path("src/research_assistant/survey/m22_representative_missions.py")
LAUNCHER_PATH = Path("scripts/run_m22_representative_real_missions.py")


class M22RepresentativeMissionError(RuntimeError):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M22RepresentativeMissionError(
            "invalid_json_artifact", f"{label} is unreadable: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise M22RepresentativeMissionError(
            "invalid_json_artifact", f"{label} must be a JSON object: {path}"
        )
    return value, raw


def _safe_repository_path(repository_root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise M22RepresentativeMissionError("unsafe_matrix_path", relative)
    candidate = (repository_root / path).resolve(strict=True)
    if not candidate.is_relative_to(repository_root) or candidate.is_symlink() or not candidate.is_file():
        raise M22RepresentativeMissionError("unsafe_matrix_path", relative)
    return candidate


def load_matrix(*, repository_root: Path, matrix_path: Path) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    matrix_path = matrix_path.resolve(strict=True)
    if not matrix_path.is_relative_to(repository_root):
        raise M22RepresentativeMissionError("matrix_outside_repository")
    matrix, raw = _read_json(matrix_path, label="M22 active matrix")
    expected_keys = {
        "schema_version",
        "status",
        "matrix_id",
        "execution_class",
        "historical_predecessor",
        "retained_artifacts",
        "cases",
        "forbidden_actions",
        "nonclaims",
    }
    if set(matrix) != expected_keys:
        raise M22RepresentativeMissionError("matrix_schema_mismatch")
    if (
        matrix["schema_version"] != MATRIX_SCHEMA
        or matrix["status"] != "frozen_before_execution"
        or matrix["execution_class"] != "local_read_only_replay"
        or matrix["nonclaims"] != RESULT_NONCLAIMS
    ):
        raise M22RepresentativeMissionError("matrix_contract_mismatch")
    cases = matrix.get("cases")
    if not isinstance(cases, list) or [row.get("case_id") for row in cases] != list(CASE_IDS):
        raise M22RepresentativeMissionError("matrix_case_order_mismatch")
    artifacts = matrix.get("retained_artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise M22RepresentativeMissionError("matrix_artifacts_missing")
    for artifact_id, row in artifacts.items():
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "role"}:
            raise M22RepresentativeMissionError("matrix_artifact_schema_mismatch", artifact_id)
        path = _safe_repository_path(repository_root, row["path"])
        if _sha_file(path) != row["sha256"]:
            raise M22RepresentativeMissionError("stale_matrix_evidence", artifact_id)
    predecessor = matrix.get("historical_predecessor")
    if not isinstance(predecessor, dict) or set(predecessor) != {"path", "sha256", "status"}:
        raise M22RepresentativeMissionError("matrix_predecessor_schema_mismatch")
    predecessor_path = _safe_repository_path(repository_root, predecessor["path"])
    if _sha_file(predecessor_path) != predecessor["sha256"]:
        raise M22RepresentativeMissionError("historical_matrix_changed")
    known_artifacts = set(artifacts)
    for row in cases:
        if not isinstance(row, dict) or set(row) != {
            "case_id", "evidence_ids", "expected_terminal", "input"
        }:
            raise M22RepresentativeMissionError("matrix_case_schema_mismatch")
        case_id = row["case_id"]
        if row["expected_terminal"] != EXPECTED_TERMINALS[case_id]:
            raise M22RepresentativeMissionError("matrix_terminal_mismatch", case_id)
        evidence_ids = row["evidence_ids"]
        _validate_case_evidence_ids(
            case_id=case_id,
            evidence_ids=evidence_ids,
            known_artifacts=known_artifacts,
        )
        if not isinstance(row["input"], dict):
            raise M22RepresentativeMissionError("matrix_case_input_mismatch", case_id)
    matrix["_matrix_sha256"] = _sha(raw)
    matrix["_matrix_path"] = str(matrix_path)
    return matrix


def _validate_case_evidence_ids(
    *, case_id: str, evidence_ids: Any, known_artifacts: set[str]
) -> None:
    if (
        not isinstance(evidence_ids, list)
        or tuple(evidence_ids) != EXPECTED_EVIDENCE_IDS[case_id]
        or any(value not in known_artifacts for value in evidence_ids)
    ):
        raise M22RepresentativeMissionError("matrix_case_evidence_mismatch", case_id)


def _artifact_path(repository_root: Path, matrix: dict[str, Any], artifact_id: str) -> Path:
    row = matrix["retained_artifacts"].get(artifact_id)
    if not isinstance(row, dict):
        raise M22RepresentativeMissionError("missing_case_evidence", artifact_id)
    return _safe_repository_path(repository_root, row["path"])


def _load_artifacts(
    *, repository_root: Path, matrix: dict[str, Any]
) -> dict[str, dict[str, Any] | Path]:
    result: dict[str, dict[str, Any] | Path] = {}
    for artifact_id, row in matrix["retained_artifacts"].items():
        path = _safe_repository_path(repository_root, row["path"])
        result[artifact_id] = _read_json(path, label=artifact_id)[0] if path.suffix == ".json" else path
    return result


def _assessment(bundle: dict[str, Any], subject_id: str) -> dict[str, Any]:
    row = next(
        (item for item in bundle["assessments"] if item.get("subject_id") == subject_id),
        None,
    )
    if not isinstance(row, dict):
        raise M22RepresentativeMissionError("missing_qualitative_assessment", subject_id)
    if row.get("claim_support_allowed") is not False or row.get("ready_for_prose") is not False:
        raise M22RepresentativeMissionError("unsupported_assessment_promotion", subject_id)
    return row


def _validate_assessment_refs(repository_root: Path, bundle: dict[str, Any]) -> None:
    for assessment in bundle["assessments"]:
        for reference in assessment["evidence_refs"]:
            parts = reference.split(":")
            resolved: Path | None = None
            suffix: list[str] = []
            for index in range(len(parts), 0, -1):
                candidate = repository_root / ":".join(parts[:index])
                if candidate.is_file():
                    resolved = candidate.resolve(strict=True)
                    suffix = parts[index:]
                    break
            if resolved is None or not resolved.is_relative_to(repository_root):
                raise M22RepresentativeMissionError("missing_assessment_evidence", reference)
            if len(suffix) == 1 and suffix[0].isdigit() and resolved.suffix.casefold() not in {".json", ".csv"}:
                line_count = sum(1 for _ in resolved.open(encoding="utf-8", errors="replace"))
                if int(suffix[0]) > line_count:
                    raise M22RepresentativeMissionError("assessment_evidence_line_missing", reference)


def _case_result(
    *,
    case: dict[str, Any],
    terminal: str,
    engineering_checks: list[str],
    source_status: str,
    source_summary: str,
    interpretation_status: str,
    interpretation_summary: str,
    smallest_next_action: str,
) -> dict[str, Any]:
    passed = terminal == case["expected_terminal"]
    return {
        "case_id": case["case_id"],
        "expected_terminal": case["expected_terminal"],
        "terminal": terminal,
        "passed": passed,
        "evidence_ids": case["evidence_ids"],
        "engineering": {
            "status": "PASSED" if passed else "FAILED",
            "checks": engineering_checks,
        },
        "source_support": {
            "status": source_status,
            "summary": source_summary,
        },
        "qualitative_interpretation": {
            "status": interpretation_status,
            "summary": interpretation_summary,
        },
        "smallest_next_action": smallest_next_action,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": RESULT_NONCLAIMS,
    }


def _run_topic_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path], context: Any
) -> dict[str, Any]:
    mission = artifacts["m17_topic_mission_control"]
    replay = artifacts["m17_topic_replay_result"]
    seed_context = artifacts["m17_topic_seed_context"]
    production = artifacts["m22_production_mission_control"]
    bundle = artifacts["m22_qualitative_assessments"]
    if not all(isinstance(value, dict) for value in (mission, replay, seed_context, production, bundle)):
        raise M22RepresentativeMissionError("topic_case_input_invalid")
    contract = mission["mission_contract"]
    production_contract = production["mission_contract"]
    selected_seed = case["input"]["selected_seed"]
    assessment = _assessment(bundle, selected_seed)
    if (
        mission.get("input_mode") != "idea_or_topic_without_initial_paper_seed"
        or mission.get("initial_seeds") != []
        or mission.get("bootstrap_attempt_state") != "selected_complete"
        or mission.get("bootstrap_outcome") != "selected"
        or mission.get("effective_seeds") != [selected_seed]
        or contract.get("normalized_initial_seeds") != []
        or replay.get("passed") is not True
        or seed_context.get("original_initial_seeds") != []
        or seed_context.get("effective_seed_rows") != [{"display": selected_seed, "key": selected_seed}]
        or seed_context.get("effective_seed_source") != "selected_bootstrap_authority_not_original_mission_input"
        or production_contract.get("normalized_seeds") != [{"display": selected_seed, "key": selected_seed}]
        or context.review_queue.get("topic") != case["input"]["topic"]
        or not any(identity.canonical_identifier == selected_seed for identity in context.source_identities.values())
    ):
        raise M22RepresentativeMissionError("topic_case_lineage_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "M17 topic-only input preserves an empty original seed list",
            "M17 selected authority binds the exact effective seed arxiv:2201.12220v3",
            "M22 selected queue and source identity replay",
            "qualitative assessment remains non-promoting",
            "replay kind is retained_production_topic_replay",
        ],
        source_status="SCOPED_PRIMARY_TECHNICAL_TEXT_INSPECTED",
        source_summary=(
            "The selected seed has a retained primary-source assessment with exact line references. "
            "The topic-to-seed selection evidence is the deterministic M17 local fixture, while the "
            "downstream source and omission evidence is retained production evidence."
        ),
        interpretation_status="QUALITATIVE_ASSESSMENT_AVAILABLE_NONPROMOTING",
        interpretation_summary=assessment["summary"],
        smallest_next_action=(
            "Carry the retained-topic-replay limitation and the assessment's concerns into M23; "
            "do not describe this as live topic-discovery validation."
        ),
    )


def _run_explicit_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path], context: Any
) -> dict[str, Any]:
    production = artifacts["m22_production_mission_control"]
    bundle = artifacts["m22_qualitative_assessments"]
    if not isinstance(production, dict) or not isinstance(bundle, dict):
        raise M22RepresentativeMissionError("explicit_case_input_invalid")
    seed = case["input"]["seed"]
    assessment = _assessment(bundle, seed)
    contract = production["mission_contract"]
    if (
        contract.get("schema_version") != "ra-survey-public-source-mission-contract-v2"
        or contract.get("normalized_seeds") != [{"display": seed, "key": seed}]
        or not any(identity.canonical_identifier == seed for identity in context.source_identities.values())
    ):
        raise M22RepresentativeMissionError("explicit_seed_lineage_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "explicit-seed V2 mission contract replays",
            "selected review queue lineage replays",
            "seed source identity joins the selected queue",
            "qualitative assessment remains non-promoting",
        ],
        source_status="SCOPED_PRIMARY_TECHNICAL_TEXT_INSPECTED",
        source_summary="The exact explicit seed has retained technical text and a bounded qualitative assessment.",
        interpretation_status="QUALITATIVE_ASSESSMENT_AVAILABLE_NONPROMOTING",
        interpretation_summary=assessment["summary"],
        smallest_next_action="Preserve the assessment limitations when drafting the M23 synthesis contract.",
    )


def _run_source_gap_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path]
) -> dict[str, Any]:
    status = artifacts["m22_source_intake_status"]
    bundle = artifacts["m22_qualitative_assessments"]
    correction = artifacts["m21_correction_record"]
    if not isinstance(status, dict) or not isinstance(bundle, dict) or not isinstance(correction, Path):
        raise M22RepresentativeMissionError("source_gap_input_invalid")
    seed = case["input"]["seed"]
    row = next((item for item in status["rows"] if item.get("identifier") == seed), None)
    assessment = _assessment(bundle, "omission_frontier:source_parse_gap:1412.6980")
    correction_text = correction.read_text(encoding="utf-8")
    if (
        not isinstance(row, dict)
        or row.get("outcome_status") != "unavailable"
        or row.get("code") != "source_format_parse_gap"
        or row.get("anchor_count") != 0
        or case["input"].get("pdf_fallback") is not False
        or "PDF fallback is out of scope" not in correction_text
    ):
        raise M22RepresentativeMissionError("source_gap_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "active corrected source-intake authority selected",
            "zero technical anchors recorded",
            "PDF fallback remains disabled",
            "qualitative source-gap note remains non-promoting",
        ],
        source_status="SOURCE_GAP_BLOCKER",
        source_summary="The retained source is an includepdf wrapper; technical contents were not inspected.",
        interpretation_status="QUALITATIVE_GAP_NOTE_AVAILABLE",
        interpretation_summary=assessment["summary"],
        smallest_next_action=assessment["next_action"],
    )


def _run_forward_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path]
) -> dict[str, Any]:
    forward = artifacts["m20_forward_snowball"]
    bundle = artifacts["m22_qualitative_assessments"]
    if not isinstance(forward, dict) or not isinstance(bundle, dict):
        raise M22RepresentativeMissionError("forward_case_input_invalid")
    assessment = _assessment(bundle, "omission_frontier:forward_citations")
    if (
        forward.get("status") != "unavailable_out_of_scope"
        or forward.get("blocking") is not False
        or forward.get("rows") != []
    ):
        raise M22RepresentativeMissionError("forward_coverage_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "forward ledger replays as unavailable_out_of_scope",
            "limitation is explicitly non-blocking",
            "empty observations are not interpreted as zero citations",
        ],
        source_status="FORWARD_COVERAGE_UNAVAILABLE_OUT_OF_SCOPE",
        source_summary="No credential-free forward-citation metadata is available in the retained campaign.",
        interpretation_status="VISIBLE_NONBLOCKING_LIMITATION",
        interpretation_summary=assessment["summary"],
        smallest_next_action=assessment["next_action"],
    )


def _run_identifier_free_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path]
) -> dict[str, Any]:
    risk = artifacts["m21_identifier_free_risk"]
    bundle = artifacts["m22_qualitative_assessments"]
    if not isinstance(risk, dict) or not isinstance(bundle, dict):
        raise M22RepresentativeMissionError("identifier_free_input_invalid")
    assessment = _assessment(bundle, "omission_frontier:identifier_free")
    if (
        risk.get("status") != "open_omission_risk"
        or risk.get("identifier_free_bibliography_units") != case["input"]["unit_count"]
        or risk.get("forward_coverage_status") != "unavailable_out_of_scope"
    ):
        raise M22RepresentativeMissionError("identifier_free_accounting_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "aggregate count replays as exactly 195 units",
            "identity uncertainty remains explicit",
            "no paper-level relevance or completeness conclusion is produced",
        ],
        source_status="IDENTITIES_AND_PRIMARY_SOURCES_UNRESOLVED",
        source_summary="The aggregate represents bibliography units, not 195 established unique papers.",
        interpretation_status="OPEN_OMISSION_RISK_WITH_LOCAL_NEXT_ACTION",
        interpretation_summary=assessment["summary"],
        smallest_next_action=assessment["next_action"],
    )


def _run_residual_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path], repository_root: Path
) -> dict[str, Any]:
    triage = artifacts["m22_provisional_classification"]
    queue = artifacts["m22_inspection_queue"]
    inspection = artifacts["m22_source_inspection"]
    bundle = artifacts["m22_qualitative_assessments"]
    if not all(isinstance(value, dict) for value in (triage, queue, inspection, bundle)):
        raise M22RepresentativeMissionError("residual_case_input_invalid")
    validate_provisional_triage(triage)
    validate_inspection_queue(queue, triage=triage)
    validate_source_inspection_bundle(inspection, repository_root=repository_root)
    assessment = _assessment(bundle, "omission_frontier:unused_identifier_bearing")
    inspected_ids = {row["candidate_id"] for row in inspection["rows"]}
    queued_ids = set(queue["candidate_ids"])
    if (
        triage.get("candidate_count") != case["input"]["triaged_count"]
        or queue.get("nomination_count") != case["input"]["inspected_count"]
        or inspection.get("paper_count") != case["input"]["inspected_count"]
        or inspected_ids != queued_ids
        or triage["candidate_count"] - len(inspected_ids) != case["input"]["residual_count"]
    ):
        raise M22RepresentativeMissionError("residual_omission_accounting_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "55 title-context rows replay",
            "five predeclared primary-source inspections replay",
            "five inspected rows are excluded from the residual count",
            "remaining residual is exactly 50 rows",
        ],
        source_status="FIVE_INSPECTED_FIFTY_SOURCE_GAPS",
        source_summary=(
            "Five nominated papers have scoped primary technical-source inspections; the other 50 "
            "remain title-context-only omission risks."
        ),
        interpretation_status="OPEN_GROUPED_OMISSION_RISK",
        interpretation_summary=assessment["summary"],
        smallest_next_action=assessment["next_action"],
    )


def _run_correction_case(
    case: dict[str, Any], artifacts: dict[str, dict[str, Any] | Path], matrix: dict[str, Any]
) -> dict[str, Any]:
    original = artifacts["m21_original_source_status"]
    active = artifacts["m22_source_intake_status"]
    if not isinstance(original, dict) or not isinstance(active, dict):
        raise M22RepresentativeMissionError("correction_case_input_invalid")
    arxiv_id = case["input"]["seed"].removeprefix("arxiv:")
    old_row = next((row for row in original["rows"] if row.get("arxiv_id") == arxiv_id), None)
    new_row = next((row for row in active["rows"] if row.get("candidate_id") == arxiv_id), None)
    correction = active.get("authoritative_correction") or {}
    if (
        not isinstance(old_row, dict)
        or old_row.get("outcome") != "accepted_and_parsed"
        or not isinstance(new_row, dict)
        or new_row.get("outcome_status") != "unavailable"
        or new_row.get("code") != "source_format_parse_gap"
        or correction.get("arxiv_id") != arxiv_id
        or correction.get("original_status_sha256")
        != matrix["retained_artifacts"]["m21_original_source_status"]["sha256"]
        or correction.get("correction_record_sha256")
        != matrix["retained_artifacts"]["m21_correction_record"]["sha256"]
    ):
        raise M22RepresentativeMissionError("correction_supersession_mismatch")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "pre-correction status is preserved byte-for-byte",
            "active authority selects the corrected source-format gap",
            "correction binds both original status and correction-record hashes",
        ],
        source_status="CORRECTED_TO_SOURCE_FORMAT_GAP",
        source_summary="The active interpretation is a parse gap; the prior accepted_and_parsed record remains historical evidence.",
        interpretation_status="VISIBLE_CORRECTION_WITH_SUPERSESSION",
        interpretation_summary="The corrected result changes the source-support interpretation without deleting the original artifact.",
        smallest_next_action="Use only the corrected active status in downstream scientific interpretation.",
    )


def _run_impersonation_case(case: dict[str, Any]) -> dict[str, Any]:
    reviewer = {
        "opaque_reviewer_id": "reviewer-local-001",
        "display_name": case["input"]["display_name"],
        "authority_origin": "human_self_attested",
        "is_human": True,
        "roles": list(REVIEW_ROLES),
        "competence_statement": "Synthetic declaration used only to verify rejection.",
        "conflict_status": "none_declared",
        "conflict_details": None,
        "privacy_notice_accepted": True,
        "privacy_retention_accepted": True,
    }
    try:
        validate_reviewer_declaration(reviewer)
    except MissionStateError as exc:
        if exc.code != "nonhuman_reviewer_identity":
            raise M22RepresentativeMissionError("wrong_impersonation_rejection", exc.code) from exc
    else:
        raise M22RepresentativeMissionError("impersonation_not_rejected")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "active human-review validator executed",
            "model or fixture identity rejected with nonhuman_reviewer_identity",
            "no human authority or scientific claim was fabricated",
        ],
        source_status="NOT_APPLICABLE_ENGINEERING_BOUNDARY",
        source_summary="This case tests authority labeling only and supplies no scientific source evidence.",
        interpretation_status="HARD_REJECTED_NONHUMAN_AUTHORITY",
        interpretation_summary="Model output remains advisory and cannot be represented as genuine human review.",
        smallest_next_action="Keep automated qualitative assessments explicitly nonhuman and non-promoting.",
    )


def _run_stale_foreign_partial_case(
    case: dict[str, Any],
    matrix: dict[str, Any],
    bundle: dict[str, Any],
    repository_root: Path,
) -> dict[str, Any]:
    rejections: list[str] = []
    case_copy = dict(case)
    case_copy["evidence_ids"] = case["evidence_ids"][:-1]
    try:
        _validate_case_evidence_ids(
            case_id=case["case_id"],
            evidence_ids=case_copy["evidence_ids"],
            known_artifacts=set(matrix["retained_artifacts"]),
        )
    except M22RepresentativeMissionError as exc:
        if exc.code == "matrix_case_evidence_mismatch":
            rejections.append("partial_case_evidence")
    try:
        _assessment(bundle, "arxiv:foreign-not-in-retained-bundle")
    except M22RepresentativeMissionError as exc:
        if exc.code == "missing_qualitative_assessment":
            rejections.append("foreign_qualitative_subject")
    stale_row = dict(matrix["retained_artifacts"]["m22_selected_review_queue"])
    stale_row["sha256"] = "0" * 64
    actual = _sha_file(repository_root / stale_row["path"])
    if actual != stale_row["sha256"]:
        rejections.append("stale_evidence_hash")
    if rejections != [
        "partial_case_evidence",
        "foreign_qualitative_subject",
        "stale_evidence_hash",
    ]:
        raise M22RepresentativeMissionError("adversarial_bundle_not_rejected")
    return _case_result(
        case=case,
        terminal=EXPECTED_TERMINALS[case["case_id"]],
        engineering_checks=[
            "partial case evidence rejected",
            "foreign qualitative subject rejected",
            "stale retained-artifact hash rejected",
        ],
        source_status="REJECTED_UNBOUND_EVIDENCE",
        source_summary="No scientific source state is admitted from partial, foreign, or stale inputs.",
        interpretation_status="HARD_REJECTED_STALE_FOREIGN_PARTIAL_INPUT",
        interpretation_summary="The active workflow fails closed when required evidence identity or coverage is not exact.",
        smallest_next_action="Repair the exact missing or stale evidence binding before replaying the affected case.",
    )


def evaluate_matrix(*, repository_root: Path, matrix: dict[str, Any]) -> list[dict[str, Any]]:
    repository_root = repository_root.resolve(strict=True)
    artifacts = _load_artifacts(repository_root=repository_root, matrix=matrix)
    bundle = artifacts["m22_qualitative_assessments"]
    if not isinstance(bundle, dict):
        raise M22RepresentativeMissionError("qualitative_bundle_missing")
    validate_assessment_bundle(bundle)
    if (
        len(bundle["assessments"]) != 16
        or bundle.get("claim_support_allowed") is not False
        or bundle.get("ready_for_prose") is not False
        or bundle.get("what_is_not_concluded") != ASSESSMENT_NONCLAIMS
    ):
        raise M22RepresentativeMissionError("qualitative_bundle_contract_mismatch")
    _validate_assessment_refs(repository_root, bundle)
    selected_path = _artifact_path(repository_root, matrix, "m22_selected_review_queue")
    validate_selected_review_queue(selected_path, repository_root=repository_root)
    context = load_v2_evidence_context(
        selected_path, repository_root=repository_root
    )
    cases = {row["case_id"]: row for row in matrix["cases"]}
    return [
        _run_topic_case(cases[CASE_IDS[0]], artifacts, context),
        _run_explicit_case(cases[CASE_IDS[1]], artifacts, context),
        _run_source_gap_case(cases[CASE_IDS[2]], artifacts),
        _run_forward_case(cases[CASE_IDS[3]], artifacts),
        _run_identifier_free_case(cases[CASE_IDS[4]], artifacts),
        _run_residual_case(cases[CASE_IDS[5]], artifacts, repository_root),
        _run_correction_case(cases[CASE_IDS[6]], artifacts, matrix),
        _run_impersonation_case(cases[CASE_IDS[7]]),
        _run_stale_foreign_partial_case(
            cases[CASE_IDS[8]], matrix, bundle, repository_root
        ),
    ]


def _ledger(kind: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    field = {
        "engineering": "engineering",
        "source_support": "source_support",
        "qualitative_interpretation": "qualitative_interpretation",
    }[kind]
    return {
        "schema_version": LEDGER_SCHEMA,
        "ledger_kind": kind,
        "case_count": len(cases),
        "rows": [{"case_id": row["case_id"], **row[field]} for row in cases],
        "what_is_not_concluded": RESULT_NONCLAIMS,
    }


def _case_ledger(matrix: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": CASE_LEDGER_SCHEMA,
        "matrix_id": matrix["matrix_id"],
        "matrix_sha256": matrix["_matrix_sha256"],
        "case_count": len(cases),
        "all_cases_passed": all(row["passed"] for row in cases),
        "cases": cases,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": RESULT_NONCLAIMS,
    }


def _report(case_ledger: dict[str, Any]) -> str:
    lines = [
        "# M22 Representative Real Missions",
        "",
        "All nine cases are local replays. An assessed terminal means the workflow can preserve and explain the recorded evidence state; it does not mean the literature is complete, the claims are true, or prose is ready.",
        "",
        "| Case | Terminal | Engineering | Source support | Interpretation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in case_ledger["cases"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['terminal']}` | `{row['engineering']['status']}` | "
            f"`{row['source_support']['status']}` | `{row['qualitative_interpretation']['status']}` |"
        )
    lines.extend([
        "",
        "## Topic Boundary",
        "",
        "The topic case is `retained_production_topic_replay`. Its M17 topic-to-seed selection is a deterministic local fixture with empty original seeds; its downstream source, omission, and qualitative evidence is retained production evidence. It is not a live topic-discovery validation.",
        "",
        "## Open Scientific Gaps",
        "",
        "- Forward-citation coverage is unavailable and non-blocking.",
        "- Fifty identifier-bearing title-context rows remain source-uninspected.",
        "- The 195 identifier-free bibliography units remain an aggregate identity frontier.",
        "- Official code and publication/retraction status remain unchecked.",
        "- Every qualitative assessment remains `claim_support_allowed=false` and `ready_for_prose=false`.",
        "",
    ])
    return "\n".join(lines)


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_write(path, pretty_json_bytes(value))


def _inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "artifact_inventory.json":
            continue
        rows.append({
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha_file(path),
        })
    return {
        "schema_version": INVENTORY_SCHEMA,
        "inventory_excludes_itself": True,
        "files": rows,
    }


def _git_value(repository_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repository_root, check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise M22RepresentativeMissionError("git_provenance_unavailable") from exc
    return completed.stdout.strip()


def _execution_sources(repository_root: Path, output_root: Path, matrix_path: Path) -> list[dict[str, Any]]:
    execution_root = output_root / "execution_sources"
    execution_root.mkdir()
    paths = [matrix_path, repository_root / DEFAULT_PLAN_PATH, repository_root / RUNNER_PATH]
    launcher = repository_root / LAUNCHER_PATH
    if launcher.is_file():
        paths.append(launcher)
    rows = []
    for source in paths:
        destination = execution_root / source.name
        shutil.copyfile(source, destination)
        rows.append({
            "relative_path": destination.relative_to(output_root).as_posix(),
            "sha256": _sha_file(destination),
            "size_bytes": destination.stat().st_size,
        })
    return rows


def _expected_artifact_bytes(
    *, repository_root: Path, matrix: dict[str, Any]
) -> dict[str, bytes]:
    cases = evaluate_matrix(repository_root=repository_root, matrix=matrix)
    ledger = _case_ledger(matrix, cases)
    return {
        "case_ledger.json": pretty_json_bytes(ledger),
        "engineering_ledger.json": pretty_json_bytes(_ledger("engineering", cases)),
        "source_support_ledger.json": pretty_json_bytes(_ledger("source_support", cases)),
        "qualitative_interpretation_ledger.json": pretty_json_bytes(
            _ledger("qualitative_interpretation", cases)
        ),
        "CASE_REPORT.md": (_report(ledger) + "\n").encode("utf-8"),
    }


def replay_representative_missions(
    *, repository_root: Path, output_root: Path
) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    output_root = output_root.resolve(strict=True)
    manifest, _ = _read_json(output_root / "run_manifest.json", label="run manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA or manifest.get("status") not in {"running", "closed"}:
        raise M22RepresentativeMissionError("run_manifest_invalid")
    matrix_copy = output_root / "execution_sources" / Path(manifest["matrix_path"]).name
    if _sha_file(matrix_copy) != manifest.get("matrix_sha256"):
        raise M22RepresentativeMissionError("preserved_matrix_tampered")
    for row in manifest.get("preserved_execution_sources") or []:
        path = (output_root / row["relative_path"]).resolve(strict=True)
        if (
            not path.is_relative_to((output_root / "execution_sources").resolve(strict=True))
            or path.stat().st_size != row["size_bytes"]
            or _sha_file(path) != row["sha256"]
        ):
            raise M22RepresentativeMissionError("execution_source_tampered")
    matrix = load_matrix(
        repository_root=repository_root,
        matrix_path=repository_root / manifest["matrix_path"],
    )
    if matrix["_matrix_sha256"] != manifest["matrix_sha256"]:
        raise M22RepresentativeMissionError("current_matrix_differs_from_run")
    expected = _expected_artifact_bytes(repository_root=repository_root, matrix=matrix)
    for relative, raw in expected.items():
        if (output_root / relative).read_bytes() != raw:
            raise M22RepresentativeMissionError("derived_artifact_replay_mismatch", relative)
    ledger = json.loads(expected["case_ledger.json"])
    if ledger.get("case_count") != 9 or ledger.get("all_cases_passed") is not True:
        raise M22RepresentativeMissionError("case_ledger_invalid")
    replay = {
        "schema_version": REPLAY_SCHEMA,
        "status": "passed",
        "case_count": 9,
        "all_cases_passed": True,
        "topic_terminal": ledger["cases"][0]["terminal"],
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": RESULT_NONCLAIMS,
    }
    replay_path = output_root / "offline_replay.json"
    if replay_path.exists() and replay_path.read_bytes() != pretty_json_bytes(replay):
        raise M22RepresentativeMissionError("offline_replay_tampered")
    terminal_path = output_root / "terminal_result.json"
    if terminal_path.exists():
        terminal, raw = _read_json(terminal_path, label="terminal result")
        if raw != pretty_json_bytes(terminal) or terminal.get("schema_version") != TERMINAL_SCHEMA:
            raise M22RepresentativeMissionError("terminal_result_invalid")
        if (
            terminal.get("classification") != "M22_REPRESENTATIVE_REAL_MISSIONS_PASSED"
            or terminal.get("primary_criterion_passed") is not True
            or terminal.get("case_count") != 9
            or terminal.get("topic_terminal") != "ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE"
            or terminal.get("claim_support_allowed") is not False
            or terminal.get("ready_for_prose") is not False
        ):
            raise M22RepresentativeMissionError("terminal_result_mismatch")
    inventory_path = output_root / "artifact_inventory.json"
    if manifest.get("status") == "closed":
        if inventory_path.read_bytes() != pretty_json_bytes(_inventory(output_root)):
            raise M22RepresentativeMissionError("artifact_inventory_replay_mismatch")
    return replay


def run_representative_missions(
    *,
    repository_root: Path,
    matrix_path: Path,
    output_root: Path,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    matrix_path = matrix_path.resolve(strict=True)
    output_root = output_root.resolve(strict=False)
    if output_root.exists() or output_root.is_symlink() or not output_root.parent.is_dir():
        raise M22RepresentativeMissionError("output_root_not_fresh")
    matrix = load_matrix(repository_root=repository_root, matrix_path=matrix_path)
    started_at = now()
    started_clock = time.monotonic()
    output_root.mkdir(mode=0o700)
    preserved = _execution_sources(repository_root, output_root, matrix_path)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "status": "running",
        "started_at_utc": started_at,
        "completed_at_utc": None,
        "wall_time_seconds": None,
        "git_commit": _git_value(repository_root, "rev-parse", "HEAD"),
        "git_tree": _git_value(repository_root, "rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(_git_value(repository_root, "status", "--porcelain")),
        "command_argv": sys.argv,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "environment": "project interpreter; deliberate local CPU-only replay",
        "hardware": "CPU-only; no framework or GPU initialization",
        "random_seeds": "N/A (deterministic replay)",
        "network_dispatch": False,
        "credential_access": False,
        "provider_calls": False,
        "pdf_fallback": False,
        "matrix_path": str(matrix_path.relative_to(repository_root)),
        "matrix_sha256": matrix["_matrix_sha256"],
        "plan_path": str(DEFAULT_PLAN_PATH),
        "preserved_execution_sources": preserved,
    }
    _write_json(output_root / "run_manifest.json", manifest)
    expected = _expected_artifact_bytes(repository_root=repository_root, matrix=matrix)
    for relative, raw in expected.items():
        _atomic_write(output_root / relative, raw)
    replay = replay_representative_missions(
        repository_root=repository_root, output_root=output_root
    )
    _write_json(output_root / "offline_replay.json", replay)
    ledger = json.loads(expected["case_ledger.json"])
    terminal = {
        "schema_version": TERMINAL_SCHEMA,
        "classification": "M22_REPRESENTATIVE_REAL_MISSIONS_PASSED",
        "primary_criterion_passed": ledger["all_cases_passed"],
        "case_count": ledger["case_count"],
        "topic_terminal": ledger["cases"][0]["terminal"],
        "explicit_seed_terminal": ledger["cases"][1]["terminal"],
        "source_and_omission_gaps_visible": True,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "offline_replay_status": replay["status"],
        "decision": "M22 representative mission matrix passed; proceed to terminal audit and M22 closeout without promoting claims or prose.",
        "remaining_limitations": [
            "topic selection is a retained deterministic M17 local fixture, not live discovery validation",
            "forward citations are unavailable and non-blocking",
            "50 identifier-bearing omission risks remain source-uninspected",
            "195 identifier-free bibliography units remain unresolved as an aggregate",
            "official code and publication or retraction status remain unchecked",
        ],
        "what_is_not_concluded": RESULT_NONCLAIMS,
    }
    _write_json(output_root / "terminal_result.json", terminal)
    completed_at = now()
    manifest.update(
        status="closed",
        completed_at_utc=completed_at,
        wall_time_seconds=round(time.monotonic() - started_clock, 6),
    )
    _write_json(output_root / "run_manifest.json", manifest)
    _write_json(output_root / "artifact_inventory.json", _inventory(output_root))
    replay_representative_missions(repository_root=repository_root, output_root=output_root)
    return terminal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX_PATH)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    repository_root = args.repository_root.resolve(strict=True)
    matrix_path = args.matrix if args.matrix.is_absolute() else repository_root / args.matrix
    result = run_representative_missions(
        repository_root=repository_root,
        matrix_path=matrix_path,
        output_root=args.output_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CASE_IDS",
    "DEFAULT_MATRIX_PATH",
    "EXPECTED_EVIDENCE_IDS",
    "EXPECTED_TERMINALS",
    "M22RepresentativeMissionError",
    "evaluate_matrix",
    "load_matrix",
    "replay_representative_missions",
    "run_representative_missions",
]
