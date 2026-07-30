from __future__ import annotations

import copy
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.literature_survey_phase6_packet_validation import validate_packet_dir

PHASE6_PACKET_DIR = ROOT / "docs/validation/literature_survey_live_public_source_phase6_2026-07-07"
VALIDATION_DIR = ROOT / "docs/validation/literature_survey_live_public_source_phase7_2026-07-07"
NEGATIVE_ROOT = VALIDATION_DIR / "negative_packets"
PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
    "source_safety_status.json",
    "ready_for_prose.json",
    "survey_packet.md",
    "build_manifest.json",
)


@dataclass(frozen=True)
class NegativeCase:
    case_id: str
    description: str
    mutate: Callable[[dict[str, Any]], None]
    expected_signal: str
    target_invariant: str


def run_validation(*, validation_dir: Path = VALIDATION_DIR) -> dict[str, Any]:
    validation_dir = validation_dir.resolve()
    negative_root = validation_dir / "negative_packets"
    if validation_dir.exists():
        shutil.rmtree(validation_dir)
    validation_dir.mkdir(parents=True, exist_ok=True)
    negative_root.mkdir(parents=True, exist_ok=True)

    def display_path(path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    positive = validate_packet_dir(PHASE6_PACKET_DIR)
    positive_path = validation_dir / "positive_packet_validation.json"
    positive_path.write_text(json.dumps(positive, indent=2, sort_keys=True))

    base_packet = _load_packet(PHASE6_PACKET_DIR)
    negative_rows = []
    for case in CASES:
        packet = copy.deepcopy(base_packet)
        case.mutate(packet)
        case_dir = negative_root / case.case_id
        _write_packet(case_dir, packet)
        validation = validate_packet_dir(case_dir)
        validation_path = case_dir / "packet_validation.json"
        validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True))
        observed = _observed_signal(validation, case.expected_signal)
        negative_rows.append({
            "case_id": case.case_id,
            "description": case.description,
            "target_invariant": case.target_invariant,
            "packet_dir": display_path(case_dir),
            "validation_report": display_path(validation_path),
            "expected_signal": case.expected_signal,
            "expected_signal_observed": observed,
            "validation_status": validation.get("status"),
            "violations": validation.get("violations", []),
        })

    positive_ok = (
        positive.get("status") == "passed"
        and positive.get("packet_ready_for_writer") is True
        and positive.get("ready_for_prose") is False
        and positive.get("supported_claim_count") == 0
    )
    negatives_ok = all(row["expected_signal_observed"] for row in negative_rows)
    mutation_strength = _mutation_strength_report(negative_rows)
    result = {
        "schema_version": "ra-literature-survey-live-public-source-phase7-validation-v1",
        "status": "passed" if positive_ok and negatives_ok and mutation_strength["status"] == "passed" else "failed",
        "phase6_packet_dir": str(PHASE6_PACKET_DIR.relative_to(ROOT)),
        "positive": {
            "validation_report": display_path(positive_path),
            "status": positive.get("status"),
            "packet_ready_for_writer": positive.get("packet_ready_for_writer"),
            "ready_for_prose": positive.get("ready_for_prose"),
            "supported_claim_count": positive.get("supported_claim_count"),
            "violations": positive.get("violations", []),
        },
        "negative_cases": negative_rows,
        "mutation_strength": mutation_strength,
        "boundary_contract": {
            "hidden_gold_used": False,
            "external_model_or_api_used": False,
            "positive_pass_means_writer_packet_only": True,
            "positive_pass_means_final_prose_ready": False,
            "raw_artifacts_allowed": False,
        },
        "what_is_not_concluded": [
            "product readiness",
            "real-agent reliability",
            "scientific correctness",
            "literature completeness",
            "final survey prose quality",
        ],
    }
    result_path = validation_dir / "phase7_validation_harness_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def _load_packet(packet_dir: Path) -> dict[str, Any]:
    return {
        name: (
            json.loads((packet_dir / name).read_text())
            if name.endswith(".json")
            else (packet_dir / name).read_text()
        )
        for name in PACKET_FILES
    }


def _write_packet(packet_dir: Path, packet: dict[str, Any]) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in packet.items():
        if name.endswith(".json"):
            (packet_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))
        else:
            (packet_dir / name).write_text(str(payload))


def _observed_signal(validation: dict[str, Any], expected_signal: str) -> bool:
    return validation.get("status") == "failed" and any(
        expected_signal in str(violation)
        for violation in validation.get("violations", [])
    )


def _mutation_strength_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    observed = sum(1 for row in rows if row.get("expected_signal_observed") is True)
    unobserved = [
        row["case_id"] for row in rows
        if row.get("expected_signal_observed") is not True
    ]
    invariants = sorted({str(row.get("target_invariant")) for row in rows if row.get("target_invariant")})
    return {
        "status": "passed" if total > 0 and observed == total else "failed",
        "observed_negative_count": observed,
        "total_negative_count": total,
        "unobserved_case_ids": unobserved,
        "target_invariants": invariants,
        "minimum_required_invariants": [
            "citation_map_edges_visible",
            "source_support_present",
            "claim_support_not_promoted",
            "omission_risks_visible",
            "raw_private_artifacts_absent",
            "source_safety_present_and_blocking",
            "ready_for_prose_blockers_visible",
            "workflow_state_not_ready_for_prose",
            "manifest_consistent_with_safety",
        ],
    }


def _remove_citation_edges(packet: dict[str, Any]) -> None:
    packet["citation_map.json"]["edges"] = []


def _remove_source_support(packet: dict[str, Any]) -> None:
    packet.pop("source_support.json", None)


def _add_unsupported_claim(packet: dict[str, Any]) -> None:
    packet["claim_support.json"]["claims"].append({
        "claim_id": "negative_metadata_supported_claim",
        "status": "supported",
        "support_class": "metadata_only",
        "claim": "Metadata alone supports a technical method claim.",
    })


def _promote_claim_candidate(packet: dict[str, Any]) -> None:
    candidate = packet["claim_support.json"]["claim_candidates"][0]
    candidate["status"] = "supported"
    candidate["review_status"] = "reviewed_passed"
    candidate["support_class"] = "primary_technical_support"
    candidate["claim_support_allowed"] = True


def _remove_omission_risks(packet: dict[str, Any]) -> None:
    packet["omission_risk.json"]["risks"] = []
    packet["omission_risk.json"]["metadata_only_papers"] = []


def _add_raw_private_leak(packet: dict[str, Any]) -> None:
    packet["source_support.json"]["raw_latex"] = r"\\begin{equation}secret\\end{equation}"


def _falsely_clear_safety_gate(packet: dict[str, Any]) -> None:
    packet["source_safety_status.json"]["status"] = "checked_clear"
    packet["source_safety_status.json"]["blocking_count"] = 0
    packet["source_safety_status.json"]["blocking_paper_ids"] = []
    for row in packet["source_safety_status.json"].get("rows") or []:
        row["retraction_or_version_status"] = "checked_clear"


def _remove_safety_status(packet: dict[str, Any]) -> None:
    packet.pop("source_safety_status.json", None)


def _remove_safety_rows(packet: dict[str, Any]) -> None:
    packet["source_safety_status.json"]["rows"] = []
    packet["source_safety_status.json"]["blocking_paper_ids"] = []


def _drift_manifest_safety_count(packet: dict[str, Any]) -> None:
    packet["build_manifest.json"]["source_safety_blocker_count"] = 0


def _weaken_ready_blockers(packet: dict[str, Any]) -> None:
    packet["ready_for_prose.json"]["blockers"] = []


def _falsely_ready_workflow_state(packet: dict[str, Any]) -> None:
    workflow_state = packet["build_manifest.json"]["workflow_state"]
    workflow_state["ready_for_prose"] = True
    workflow_state["state"] = "public_source_packet_ready_for_prose"
    workflow_state["blocked_reasons"] = []


CASES = (
    NegativeCase(
        case_id="missing_citation_edges",
        description="Remove all citation-map edges.",
        mutate=_remove_citation_edges,
        expected_signal="citation_map edges must not be empty",
        target_invariant="citation_map_edges_visible",
    ),
    NegativeCase(
        case_id="missing_source_support",
        description="Remove required source-support ledger.",
        mutate=_remove_source_support,
        expected_signal="missing_files",
        target_invariant="source_support_present",
    ),
    NegativeCase(
        case_id="unsupported_claim_row",
        description="Add a metadata-only supported technical claim row.",
        mutate=_add_unsupported_claim,
        expected_signal="claim_support must not contain supported claim rows",
        target_invariant="claim_support_not_promoted",
    ),
    NegativeCase(
        case_id="claim_candidate_promoted",
        description="Promote a review-required claim candidate into apparent support.",
        mutate=_promote_claim_candidate,
        expected_signal="claim_candidates[0] must remain review_required",
        target_invariant="claim_support_not_promoted",
    ),
    NegativeCase(
        case_id="missing_omission_risks",
        description="Remove omission-risk and metadata-only paper rows.",
        mutate=_remove_omission_risks,
        expected_signal="omission_risk must retain risks or metadata-only paper rows",
        target_invariant="omission_risks_visible",
    ),
    NegativeCase(
        case_id="raw_private_artifact_leak",
        description="Add a forbidden raw LaTeX key to a packet JSON artifact.",
        mutate=_add_raw_private_leak,
        expected_signal="forbidden raw/private keys",
        target_invariant="raw_private_artifacts_absent",
    ),
    NegativeCase(
        case_id="missing_safety_status",
        description="Remove the source-safety status artifact.",
        mutate=_remove_safety_status,
        expected_signal="missing_files",
        target_invariant="source_safety_present_and_blocking",
    ),
    NegativeCase(
        case_id="missing_safety_rows",
        description="Keep the safety artifact but remove all sourced-paper safety rows.",
        mutate=_remove_safety_rows,
        expected_signal="source_safety_status must include one row per sourced paper",
        target_invariant="source_safety_present_and_blocking",
    ),
    NegativeCase(
        case_id="safety_gate_falsely_cleared",
        description="Mark source safety checked clear without explicit Phase 6 safety evidence.",
        mutate=_falsely_clear_safety_gate,
        expected_signal="source_safety_status must not be checked_clear",
        target_invariant="source_safety_present_and_blocking",
    ),
    NegativeCase(
        case_id="manifest_safety_count_drift",
        description="Make the manifest safety blocker count disagree with the safety ledger.",
        mutate=_drift_manifest_safety_count,
        expected_signal="source_safety_status row count must match manifest source_safety_blocker_count",
        target_invariant="manifest_consistent_with_safety",
    ),
    NegativeCase(
        case_id="ready_for_prose_weakened",
        description="Remove required ready-for-prose blockers while leaving ready_for_prose false.",
        mutate=_weaken_ready_blockers,
        expected_signal="ready_for_prose blockers missing required blocker",
        target_invariant="ready_for_prose_blockers_visible",
    ),
    NegativeCase(
        case_id="workflow_state_falsely_ready",
        description="Mark workflow state ready for prose while packet ledgers remain blocked.",
        mutate=_falsely_ready_workflow_state,
        expected_signal="workflow_state ready_for_prose must remain false",
        target_invariant="workflow_state_not_ready_for_prose",
    ),
)


def main() -> int:
    result = run_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
