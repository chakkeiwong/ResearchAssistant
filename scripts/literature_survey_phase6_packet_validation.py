from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


RAW_FORBIDDEN_KEYS = {
    "raw_latex",
    "raw_full_text",
    "pdf_bytes",
    "source_tarball_bytes",
    "api_key",
    "token",
    "secret",
}
REQUIRED_READY_BLOCKER_SUBSTRINGS = (
    "technical claims are still blocked",
    "no reviewed supported technical claim rows",
    "retraction/version safety is not checked clear",
    "omission and reviewer-risk rows require review",
)


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("usage: literature_survey_phase6_packet_validation.py <phase6_packet_dir>", file=sys.stderr)
        return 2
    report = validate_packet_dir(Path(args[0]))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


def validate_packet_dir(packet_dir: Path) -> dict[str, Any]:
    required = [
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
    ]
    missing = [name for name in required if not (packet_dir / name).exists()]
    if missing:
        return {
            "status": "failed",
            "reason": "missing_files",
            "packet_dir": str(packet_dir),
            "missing": missing,
            "violations": [f"missing_files: {', '.join(missing)}"],
        }

    payloads = {name: json.loads((packet_dir / name).read_text()) for name in required if name.endswith(".json")}
    violations: list[str] = []
    claim_support = payloads["claim_support.json"]
    ready = payloads["ready_for_prose.json"]
    manifest = payloads["build_manifest.json"]
    citation_map = payloads["citation_map.json"]
    omission_risk = payloads["omission_risk.json"]
    source_safety_status = payloads["source_safety_status.json"]

    if claim_support.get("claims"):
        violations.append("claim_support must not contain supported claim rows; Phase 6 expected blocked claims only")
    for index, row in enumerate(claim_support.get("claim_candidates") or []):
        if row.get("status") != "review_required":
            violations.append(f"claim_candidates[{index}] must remain review_required")
        review_status = str(row.get("review_status") or "").lower()
        if "requires" not in review_status or "review" not in review_status:
            violations.append(f"claim_candidates[{index}] review_status must remain requires_review")
        if row.get("claim_support_allowed") is not False:
            violations.append(f"claim_candidates[{index}] must not allow claim support")
        if "not_support" not in str(row.get("support_class") or ""):
            violations.append(f"claim_candidates[{index}] support_class must mark candidate as not support")
    if manifest.get("ready_for_prose") is not False:
        violations.append("manifest ready_for_prose must remain false until packet gates are clear")
    workflow_state = manifest.get("workflow_state") or {}
    if workflow_state.get("ready_for_prose") is not False:
        violations.append("workflow_state ready_for_prose must remain false until packet gates are clear")
    if workflow_state.get("state") == "public_source_packet_ready_for_prose":
        violations.append("workflow_state must not mark public-source packet ready for prose while Phase 6 gates are blocked")
    if not workflow_state.get("blocked_reasons"):
        violations.append("workflow_state must retain blocked reasons while packet gates are blocked")
    if not citation_map.get("edges"):
        violations.append("citation_map edges must not be empty")
    if not (omission_risk.get("risks") or omission_risk.get("metadata_only_papers")):
        violations.append("omission_risk must retain risks or metadata-only paper rows")
    safety_rows = source_safety_status.get("rows") or []
    if not safety_rows:
        violations.append("source_safety_status must include one row per sourced paper")
    if len(safety_rows) != manifest.get("source_safety_blocker_count"):
        violations.append("source_safety_status row count must match manifest source_safety_blocker_count in Phase 6")
    if source_safety_status.get("status") == "checked_clear":
        violations.append("source_safety_status must not be checked_clear in Phase 6 without explicit safety evidence")
    if source_safety_status.get("blocking_count", 0) <= 0:
        violations.append("source_safety_status must retain blocking rows until safety checks are explicit")
    for index, row in enumerate(safety_rows):
        if row.get("retraction_or_version_status") == "checked_clear":
            violations.append(f"source_safety_status.rows[{index}] must not be checked_clear in Phase 6 fixture")
        if row.get("claim_support_allowed") is not False:
            violations.append(f"source_safety_status.rows[{index}] must not allow claim support before safety is clear")
    if ready.get("ready_for_prose") is not False:
        violations.append("ready_for_prose must be false until reviewed claim rows and safety checks exist")
    if ready.get("packet_ready_for_writer") is not True:
        violations.append("packet_ready_for_writer should be true when anchors are packaged")
    blockers = [str(item) for item in ready.get("blockers") or []]
    for required in REQUIRED_READY_BLOCKER_SUBSTRINGS:
        if not any(required in blocker for blocker in blockers):
            violations.append(f"ready_for_prose blockers missing required blocker: {required}")
    if manifest.get("privacy_and_raw_artifact_policy", {}).get("raw_source_copied_to_packet") is not False:
        violations.append("manifest must state raw source was not copied to the packet")
    if manifest.get("source_safety_status") != source_safety_status.get("status"):
        violations.append("manifest source_safety_status must match source_safety_status.json")
    if manifest.get("source_safety_blocker_count") != source_safety_status.get("blocking_count"):
        violations.append("manifest source_safety_blocker_count must match source_safety_status.json")
    if _contains_forbidden_raw_keys(payloads):
        violations.append("JSON packet includes forbidden raw/private keys")

    survey_packet = (packet_dir / "survey_packet.md").read_text()
    required_text = [
        "Ready for final prose: `false`",
        "Citation edges are metadata-only coverage/navigation signals, not technical support.",
        "technical claims require explicit claim rows mapped to checked source anchor ids",
        "Review-required claim candidates:",
        "Packet safety status:",
    ]
    for text in required_text:
        if text not in survey_packet:
            violations.append(f"survey_packet.md is missing required boundary text: {text}")

    report = {
        "status": "passed" if not violations else "failed",
        "packet_dir": str(packet_dir),
        "ready_for_prose": ready.get("ready_for_prose"),
        "packet_ready_for_writer": ready.get("packet_ready_for_writer"),
        "anchor_count": manifest.get("anchor_count"),
        "supported_claim_count": manifest.get("supported_claim_count"),
        "blocked_claim_count": manifest.get("blocked_claim_count"),
        "source_safety_status": source_safety_status.get("status"),
        "source_safety_blocker_count": source_safety_status.get("blocking_count"),
        "violations": violations,
    }
    return report


def _contains_forbidden_raw_keys(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in RAW_FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_raw_keys(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_raw_keys(child) for child in value)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
