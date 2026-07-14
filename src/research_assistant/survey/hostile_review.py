from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.claim_review import (
    SUPPORTED_CLAIM_CLASSES,
    SUPPORTED_REVIEW_STATUSES,
)
from research_assistant.survey.mission_state import MissionStateError, pretty_json_bytes
from research_assistant.survey.review_decisions import (
    normalize_reviewed_at,
    read_json_object_strict,
    utc_now_iso,
)
from research_assistant.survey.reviewed_merge import DECISION_TYPES
from research_assistant.survey.reviewed_packet import (
    REVIEWED_FINAL_PACKET_NONCLAIMS,
    validate_reviewed_final_packet,
)


SURVEY_HOSTILE_REVIEW_RESULT_SCHEMA_VERSION = "ra-survey-hostile-review-result-v2"
SURVEY_HOSTILE_REVIEW_SCHEMA_VERSION = "ra-survey-hostile-review-v2"
SURVEY_FINAL_PACKET_READINESS_SCHEMA_VERSION = "ra-survey-final-packet-readiness-v2"

HOSTILE_REVIEW_NONCLAIMS = list(REVIEWED_FINAL_PACKET_NONCLAIMS)
HOSTILE_REVIEW_KEYS = {
    "schema_version",
    "status",
    "created_at",
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
    "queue_semantic_sha256",
    "reviewed_final_packet_path",
    "reviewed_final_packet_sha256",
    "reviewed_final_packet_size_bytes",
    "ready_for_hostile_review",
    "ready_for_prose",
    "readiness_classification",
    "blocker_count",
    "blockers",
    "warning_count",
    "warnings",
    "next_required_actions",
    "forbidden_claims",
    "what_is_not_concluded",
}
READINESS_VIEW_KEYS = {
    "schema_version",
    "status",
    "created_at",
    "ready_for_hostile_review",
    "ready_for_prose",
    "readiness_classification",
    "hostile_review_result_path",
    "hostile_review_result_sha256",
    "hostile_review_result_size_bytes",
    "blocker_count",
    "blockers",
    "warning_count",
    "warnings",
    "next_required_actions",
    "what_is_not_concluded",
}

_SECTION_BY_DECISION_TYPE = {
    "claim_candidate": "claims",
    "source_safety": "source_safety",
    "omission_risk": "omission_risks",
    "workflow_blocker": "workflow_blockers",
}


def run_hostile_review_gate(
    *,
    reviewed_final_packet_path: Path,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    output_dir: Path,
    local_evidence_root: Path | None = None,
    force: bool = False,
    now: Callable[[], str] = utc_now_iso,
    crash_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Replay the reviewed packet and write one authoritative hostile result.

    The readiness file written alongside the result is a digest-bound view. It
    can be deleted or regenerated without changing the authoritative verdict.
    """

    mission_root = mission_root.absolute()
    output_dir = output_dir.absolute()
    expected_output = mission_root / "hostile_review"
    hostile_path = output_dir / "hostile_review_result.json"
    readiness_path = output_dir / "final_packet_readiness.json"
    if output_dir != expected_output:
        return _blocked(
            "noncanonical_hostile_review_output",
            output_dir,
            [f"write hostile-review artifacts only to {expected_output}"],
        )

    try:
        packet = validate_reviewed_final_packet(
            path=reviewed_final_packet_path,
            mission_root=mission_root,
            review_queue_path=review_queue_path,
            packet_dir=packet_dir,
            anchor_dir=anchor_dir,
            local_evidence_root=local_evidence_root,
        )
        packet_raw = _read_canonical_packet(reviewed_final_packet_path, packet)
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])

    if (
        hostile_path.exists()
        or hostile_path.is_symlink()
        or readiness_path.exists()
        or readiness_path.is_symlink()
    ) and not force:
        return _blocked(
            "output_exists",
            output_dir,
            ["rerun with --force after inputs change or to regenerate the readiness view"],
        )

    try:
        payload = _build_hostile_result(
            packet=packet,
            packet_path=reviewed_final_packet_path.absolute(),
            packet_raw=packet_raw,
            created_at=now(),
        )
        _atomic_write_json(
            hostile_path,
            payload,
            label="hostile_result",
            crash_hook=crash_hook,
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])

    hostile_raw = hostile_path.read_bytes()
    readiness = _build_readiness_view(
        hostile=payload,
        hostile_path=hostile_path,
        hostile_raw=hostile_raw,
    )
    readiness_status = "written"
    readiness_warning: dict[str, str] | None = None
    try:
        _atomic_write_json(
            readiness_path,
            readiness,
            label="readiness_view",
            crash_hook=crash_hook,
        )
    except (MissionStateError, OSError) as exc:
        readiness_status = "regeneration_required"
        readiness_warning = {
            "code": exc.code if isinstance(exc, MissionStateError) else "readiness_view_write_failed",
            "message": str(exc),
            "repair_action": "regenerate final_packet_readiness.json from the validated hostile result",
        }

    return {
        "schema_version": SURVEY_HOSTILE_REVIEW_RESULT_SCHEMA_VERSION,
        "status": payload["status"],
        "output_dir": str(output_dir),
        "hostile_review_result_path": str(hostile_path),
        "hostile_review_result_sha256": _sha256(hostile_raw),
        "final_packet_readiness_path": str(readiness_path),
        "final_packet_readiness_status": readiness_status,
        "final_packet_readiness_warning": readiness_warning,
        "ready_for_hostile_review": True,
        "ready_for_prose": payload["ready_for_prose"],
        "readiness_classification": payload["readiness_classification"],
        "blocker_count": payload["blocker_count"],
        "warning_count": payload["warning_count"],
        "what_is_not_concluded": HOSTILE_REVIEW_NONCLAIMS,
    }


def validate_hostile_review_result(
    *,
    path: Path,
    reviewed_final_packet_path: Path,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    local_evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Replay an authoritative hostile result from current external inputs."""

    mission_root = mission_root.absolute()
    expected_path = mission_root / "hostile_review" / "hostile_review_result.json"
    supplied = path.absolute()
    if supplied != expected_path or supplied.is_symlink():
        raise MissionStateError(
            "noncanonical_hostile_review_path",
            "hostile review result must use the fixed mission-local path",
        )
    payload, raw = read_json_object_strict(supplied, label="hostile review result")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_hostile_review", "hostile review result bytes are not canonical")
    if set(payload) != HOSTILE_REVIEW_KEYS:
        raise MissionStateError("invalid_hostile_review_schema", "hostile review fields do not match exact schema")
    if payload.get("schema_version") != SURVEY_HOSTILE_REVIEW_SCHEMA_VERSION:
        raise MissionStateError("invalid_hostile_review_schema", "hostile review schema is unsupported")

    packet = validate_reviewed_final_packet(
        path=reviewed_final_packet_path,
        mission_root=mission_root,
        review_queue_path=review_queue_path,
        packet_dir=packet_dir,
        anchor_dir=anchor_dir,
        local_evidence_root=local_evidence_root,
    )
    packet_raw = _read_canonical_packet(reviewed_final_packet_path, packet)
    expected = _build_hostile_result(
        packet=packet,
        packet_path=reviewed_final_packet_path.absolute(),
        packet_raw=packet_raw,
        created_at=payload.get("created_at"),
    )
    if payload != expected:
        raise MissionStateError(
            "invalid_hostile_review_replay",
            "hostile review result differs from current reviewed-packet replay",
        )
    return payload


def validate_final_packet_readiness(
    *,
    path: Path,
    hostile_review_result_path: Path,
    reviewed_final_packet_path: Path,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    local_evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Validate the nonauthoritative readiness view against the hostile result."""

    mission_root = mission_root.absolute()
    expected_path = mission_root / "hostile_review" / "final_packet_readiness.json"
    supplied = path.absolute()
    if supplied != expected_path or supplied.is_symlink():
        raise MissionStateError(
            "noncanonical_readiness_view_path",
            "readiness view must use the fixed mission-local path",
        )
    payload, raw = read_json_object_strict(supplied, label="final packet readiness view")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_readiness_view", "readiness view bytes are not canonical")
    if set(payload) != READINESS_VIEW_KEYS:
        raise MissionStateError("invalid_readiness_view_schema", "readiness view fields do not match exact schema")
    if payload.get("schema_version") != SURVEY_FINAL_PACKET_READINESS_SCHEMA_VERSION:
        raise MissionStateError("invalid_readiness_view_schema", "readiness view schema is unsupported")

    hostile = validate_hostile_review_result(
        path=hostile_review_result_path,
        reviewed_final_packet_path=reviewed_final_packet_path,
        mission_root=mission_root,
        review_queue_path=review_queue_path,
        packet_dir=packet_dir,
        anchor_dir=anchor_dir,
        local_evidence_root=local_evidence_root,
    )
    hostile_raw = hostile_review_result_path.absolute().read_bytes()
    expected = _build_readiness_view(
        hostile=hostile,
        hostile_path=hostile_review_result_path.absolute(),
        hostile_raw=hostile_raw,
    )
    if payload != expected:
        raise MissionStateError(
            "invalid_readiness_view_replay",
            "readiness view differs from its authoritative hostile result",
        )
    return payload


def refresh_final_packet_readiness(
    *,
    hostile_review_result_path: Path,
    reviewed_final_packet_path: Path,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    local_evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Regenerate the disposable readiness view from a validated result."""

    hostile = validate_hostile_review_result(
        path=hostile_review_result_path,
        reviewed_final_packet_path=reviewed_final_packet_path,
        mission_root=mission_root,
        review_queue_path=review_queue_path,
        packet_dir=packet_dir,
        anchor_dir=anchor_dir,
        local_evidence_root=local_evidence_root,
    )
    hostile_path = hostile_review_result_path.absolute()
    hostile_raw = hostile_path.read_bytes()
    view_path = mission_root.absolute() / "hostile_review" / "final_packet_readiness.json"
    view = _build_readiness_view(
        hostile=hostile,
        hostile_path=hostile_path,
        hostile_raw=hostile_raw,
    )
    _atomic_write_json(view_path, view, label="readiness_view")
    return view


def _build_hostile_result(
    *,
    packet: dict[str, Any],
    packet_path: Path,
    packet_raw: bytes,
    created_at: Any,
) -> dict[str, Any]:
    created_at = normalize_reviewed_at(created_at)
    blockers = _hostile_blockers(packet)
    warnings = _hostile_warnings(packet)
    ready_for_prose = not blockers
    status = (
        "ready_for_reviewed_prose_within_recorded_scope"
        if ready_for_prose
        else "blocked_for_reviewed_prose"
    )
    classification = (
        "READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE"
        if ready_for_prose
        else "BLOCKED_FOR_REVIEWED_PROSE"
    )
    return {
        "schema_version": SURVEY_HOSTILE_REVIEW_SCHEMA_VERSION,
        "status": status,
        "created_at": created_at,
        "mission_id": packet["mission_id"],
        "mission_fingerprint": packet["mission_fingerprint"],
        "mission_anchor_generation_id": packet["mission_anchor_generation_id"],
        "artifact_set_id": packet["artifact_set_id"],
        "queue_semantic_sha256": packet["queue_semantic_sha256"],
        "reviewed_final_packet_path": str(packet_path),
        "reviewed_final_packet_sha256": _sha256(packet_raw),
        "reviewed_final_packet_size_bytes": len(packet_raw),
        "ready_for_hostile_review": True,
        "ready_for_prose": ready_for_prose,
        "readiness_classification": classification,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "warning_count": len(warnings),
        "warnings": warnings,
        "next_required_actions": (
            ["draft reviewed prose only within the recorded scope and preserve every nonclaim"]
            if ready_for_prose
            else sorted({row["repair_action"] for row in blockers})
        ),
        "forbidden_claims": [
            "literature completeness from current-scope omission closure",
            "technical support from metadata, citation counts, venue signals, or source availability",
            "source safety in fact from a reviewed status disposition",
            "scientific correctness, product readiness, or release readiness from this local gate",
        ],
        "what_is_not_concluded": HOSTILE_REVIEW_NONCLAIMS,
    }


def _hostile_blockers(packet: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []

    def add(code: str, message: str, repair_action: str) -> None:
        blockers.append({"code": code, "message": message, "repair_action": repair_action})

    readiness = packet.get("readiness_inputs") or {}
    if readiness.get("ready_for_reviewed_packet") is not True or readiness.get("ready_for_hostile_review") is not True:
        add("packet_not_hostile_ready", "packet is not eligible for hostile review", "recompose the current reviewed final packet")
    if readiness.get("ready_for_prose") is not False:
        add("early_prose_readiness", "packet asserted prose readiness before hostile review", "repair the reviewed-packet readiness boundary")
    if readiness.get("reviewed_evidence_blockers") != []:
        add("reviewed_evidence_blockers", "packet retains reviewed-evidence blockers", "resolve and remerge the current reviewed evidence")
    if not set(HOSTILE_REVIEW_NONCLAIMS).issubset(set(packet.get("what_is_not_concluded") or [])):
        add("missing_nonclaims", "packet omits required hostile-review nonclaims", "recompose the packet with all required nonclaims")

    coverage = packet.get("decision_coverage") or {}
    accepted = coverage.get("accepted_queue_item_ids_by_type")
    required = coverage.get("required_queue_item_ids")
    if coverage.get("decision_coverage_complete") is not True or not isinstance(accepted, dict) or not isinstance(required, list):
        add("incomplete_decision_coverage", "decision coverage is incomplete", "repair all four reviewed decision sidecars and rerun the merge")
    else:
        accepted_union = sorted(item for values in accepted.values() if isinstance(values, list) for item in values)
        if set(accepted) != set(DECISION_TYPES) or accepted_union != required or len(accepted_union) != len(set(accepted_union)):
            add("invalid_decision_union", "accepted decisions do not exactly cover the required queue union", "repair exact reviewed decision coverage")

    sections = packet.get("reviewed_sections") or {}
    classifications = packet.get("evidence_classifications")
    classification_by_hash: dict[str, dict[str, Any]] = {}
    if isinstance(classifications, list):
        for row in classifications:
            if isinstance(row, dict) and isinstance(row.get("decision_sha256"), str):
                classification_by_hash.setdefault(row["decision_sha256"], row)
    claims = sections.get("claims") if isinstance(sections, dict) else None
    if not isinstance(claims, list) or not claims:
        add("missing_reviewed_claim", "no reviewed supported claim is available", "import at least one exact support-allowed reviewed claim")
    else:
        if len(classification_by_hash) != len(classifications or []) or len(classification_by_hash) != len(claims):
            add("invalid_evidence_classification_union", "claim evidence classifications are not one-to-one", "recompose exact claim evidence classifications")
        for row in claims:
            decision_hash = row.get("decision_sha256")
            classification = classification_by_hash.get(decision_hash)
            support_class = row.get("support_class")
            if row.get("review_status") not in SUPPORTED_REVIEW_STATUSES or row.get("claim_support_allowed") is not True:
                add("unsafe_reviewed_claim", f"reviewed claim {row.get('claim_id')} is not support-allowed", "repair the reviewed claim decision")
            if support_class not in SUPPORTED_CLAIM_CLASSES or not isinstance(classification, dict) or classification.get("support_class") != support_class or classification.get("claim_id") != row.get("claim_id"):
                add("invalid_claim_evidence", f"reviewed claim {row.get('claim_id')} lacks its exact evidence classification", "repair and recompose the reviewed claim evidence binding")
                continue
            if support_class == "primary_technical_support":
                if not classification.get("bound_anchors") or classification.get("paper_ids") != row.get("paper_ids") or classification.get("anchor_ids") != row.get("anchor_ids"):
                    add("invalid_primary_support", f"reviewed claim {row.get('claim_id')} lacks exact bound anchors", "repair the primary-source anchor binding")
            else:
                if packet.get("schema_version") == "ra-survey-reviewed-final-packet-v2":
                    manifests = row.get("dependency_manifests") or []
                    root_manifest = next(
                        (
                            value for value in manifests
                            if isinstance(value, dict)
                            and value.get("manifest_id") == row.get("root_dependency_manifest_id")
                        ),
                        None,
                    )
                    expected_bound = sorted(
                        (
                            {
                                "manifest_id": value.get("manifest_id"),
                                "local_artifact": value.get("local_artifact"),
                                "local_artifact_sha256": value.get("local_artifact_sha256"),
                            }
                            for value in manifests
                            if isinstance(value, dict)
                        ),
                        key=lambda value: str(value["manifest_id"]),
                    )
                    if (
                        not isinstance(root_manifest, dict)
                        or classification.get("local_artifact") != root_manifest.get("local_artifact")
                        or classification.get("local_artifact_sha256") != root_manifest.get("local_artifact_sha256")
                        or classification.get("root_dependency_manifest_id") != row.get("root_dependency_manifest_id")
                        or classification.get("bound_local_artifacts") != expected_bound
                    ):
                        add("invalid_local_support", f"reviewed claim {row.get('claim_id')} lacks exact dependency-manifest artifact binding", "repair the local evidence binding")
                elif classification.get("local_artifact") != row.get("local_artifact") or classification.get("local_artifact_sha256") != row.get("local_artifact_sha256"):
                    add("invalid_local_support", f"reviewed claim {row.get('claim_id')} lacks exact local-artifact binding", "repair the local evidence binding")
            if row.get("ready_for_prose") is not False:
                add("early_claim_prose_readiness", f"reviewed claim {row.get('claim_id')} asserted early prose readiness", "repair the reviewed claim sidecar")

    v3_packet = packet.get("schema_version") == "ra-survey-reviewed-final-packet-v2"
    source_rows = sections.get("source_safety") if isinstance(sections, dict) else None
    source_scope_valid = isinstance(source_rows, list) and all(
        (
            row.get("decision") == "checked_clear"
            and row.get("reviewer_authority") == "human_reviewed_status"
            and row.get("claim_support_allowed") is True
        )
        if v3_packet
        else (
            row.get("checked_status") == "checked_clear"
            and row.get("claim_support_allowed") is True
        )
        for row in source_rows
    )
    if not source_scope_valid:
        add("source_safety_not_clear", "one or more selected sources are not reviewed checked-clear", "refresh reviewed source-safety decisions with exact checked-clear evidence")
    elif isinstance(claims, list):
        clear_paper_ids = {
            row.get("source_paper_id") if v3_packet else row.get("paper_id")
            for row in source_rows
        }
        dependency_paper_ids = {
            dependency.get("source_paper_id")
            for row in claims
            for dependency in row.get("source_dependencies") or []
        }
        primary_paper_ids = {
            paper_id
            for row in claims
            if row.get("support_class") == "primary_technical_support"
            for paper_id in row.get("paper_ids") or []
        }
        required_paper_ids = dependency_paper_ids if v3_packet else primary_paper_ids
        if (required_paper_ids != clear_paper_ids) if v3_packet else (not required_paper_ids.issubset(clear_paper_ids)):
            add("missing_claim_source_safety", "supported claim dependencies differ from the exact selected checked-clear source set", "refresh exact source accounting and reviewed claim dependencies")

    if v3_packet:
        accounting = ((packet.get("merge_diagnostics") or {}).get("source_accounting") or {})
        if (
            accounting.get("status") != "source_accounting_clear"
            or accounting.get("unsafe_dependency_count") != 0
            or accounting.get("missing_dependency_count") != 0
            or accounting.get("unused_included_source_count") != 0
            or accounting.get("open_quarantine_risk_count") != 0
        ):
            add("source_accounting_not_clear", "selected sources are not completely and safely accounted", "repair exact source dependencies, unused included sources, or open quarantine risks")

    omission_rows = sections.get("omission_risks") if isinstance(sections, dict) else None
    if not isinstance(omission_rows, list) or any(
        row.get("status") != "reviewed_closed_for_current_scope"
        or row.get("literature_completeness_allowed") is not False
        for row in omission_rows
    ):
        add("omission_not_closed", "one or more omission risks are not closed for the recorded scope", "refresh reviewed omission decisions without claiming completeness")

    workflow_rows = sections.get("workflow_blockers") if isinstance(sections, dict) else None
    if not isinstance(workflow_rows, list) or any(row.get("disposition") != "resolved_by_reviewed_evidence" for row in workflow_rows):
        add("workflow_blocker_open", "one or more workflow blockers remain unresolved", "refresh workflow-blocker decisions or repair their upstream evidence")

    selected = packet.get("selected_coverage") or {}
    risks = (selected.get("omitted_paper_risks.json") or {}).get("risks")
    reviewed_risk_ids = {row.get("risk_id") for row in omission_rows or [] if isinstance(row, dict)}
    if not isinstance(risks, list) or any(not isinstance(row, dict) or row.get("risk_id") not in reviewed_risk_ids for row in risks):
        add("unreviewed_coverage_risk", "selected coverage contains a risk without an exact reviewed disposition", "refresh exact omission-risk queue coverage and decisions")
    omission_policy = (selected.get("omitted_paper_risks.json") or {}).get("review_policy") or {}
    if omission_policy.get("omission_visibility_is_not_literature_completeness") is not True:
        add("unsafe_omission_policy", "coverage policy permits omission visibility to imply completeness", "repair the selected omission policy")
    metadata_policy = (selected.get("citation_venue_metadata.json") or {}).get("metadata_policy") or {}
    if metadata_policy.get("citation_counts_are_coverage_signals_only") is not True or metadata_policy.get("metadata_supports_technical_claims") is not False:
        add("unsafe_metadata_policy", "citation or venue metadata may be promoted beyond a coverage signal", "repair the selected citation and venue metadata policy")
    for direction in ("backward", "forward"):
        evidence_policy = (selected.get(f"{direction}_snowball.json") or {}).get("evidence_policy") or {}
        if (
            evidence_policy.get("metadata_relations_support_navigation") is not True
            or evidence_policy.get("metadata_relations_support_technical_claims") is not False
            or evidence_policy.get("metadata_relations_support_completeness_claims") is not False
        ):
            add("unsafe_snowball_policy", f"{direction} snowball metadata policy permits unsupported promotion", "repair the selected snowball evidence policy")

    frontier_map = packet.get("omission_frontier_map")
    blocked_frontiers = (selected.get("coverage_manifest.json") or {}).get("blocked_frontiers")
    if not isinstance(frontier_map, list) or not isinstance(blocked_frontiers, list):
        add("invalid_frontier_join", "blocked-frontier closure map is malformed", "repair the selected coverage frontier join")
    else:
        mapped = {row.get("direction") for row in frontier_map if isinstance(row, dict)}
        if mapped != set(blocked_frontiers) or any(row.get("reviewed_closed_for_current_scope") is not True for row in frontier_map if isinstance(row, dict)):
            add("open_frontier_join", "a blocked frontier lacks exact current-scope reviewed closure", "review the exact blocked-frontier omission risk")

    return sorted(blockers, key=lambda row: (row["code"], row["message"]))


def _hostile_warnings(packet: dict[str, Any]) -> list[dict[str, str]]:
    selected = packet["selected_coverage"]
    warnings: list[dict[str, str]] = []
    for row in packet["omission_frontier_map"]:
        warnings.append({
            "code": "frontier_closed_for_recorded_scope_only",
            "message": f"{row['direction']} snowball frontier remains blocked but has exact reviewed closure for this scope only",
        })
    if (selected["citation_venue_metadata.json"].get("record_count") or 0) == 0:
        warnings.append({"code": "empty_citation_metadata", "message": "citation and venue metadata ledger has no records"})
    if selected["paper_classifications.json"].get("classifications") == []:
        warnings.append({"code": "empty_paper_classifications", "message": "paper classifications ledger has no rows"})
    return sorted(warnings, key=lambda row: (row["code"], row["message"]))


def _build_readiness_view(
    *,
    hostile: dict[str, Any],
    hostile_path: Path,
    hostile_raw: bytes,
) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_FINAL_PACKET_READINESS_SCHEMA_VERSION,
        "status": hostile["status"],
        "created_at": hostile["created_at"],
        "ready_for_hostile_review": hostile["ready_for_hostile_review"],
        "ready_for_prose": hostile["ready_for_prose"],
        "readiness_classification": hostile["readiness_classification"],
        "hostile_review_result_path": str(hostile_path),
        "hostile_review_result_sha256": _sha256(hostile_raw),
        "hostile_review_result_size_bytes": len(hostile_raw),
        "blocker_count": hostile["blocker_count"],
        "blockers": hostile["blockers"],
        "warning_count": hostile["warning_count"],
        "warnings": hostile["warnings"],
        "next_required_actions": hostile["next_required_actions"],
        "what_is_not_concluded": hostile["what_is_not_concluded"],
    }


def _read_canonical_packet(path: Path, payload: dict[str, Any]) -> bytes:
    _, raw = read_json_object_strict(path, label="reviewed final packet")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_reviewed_packet", "reviewed final packet bytes are not canonical")
    return raw


def _atomic_write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    label: str,
    crash_hook: Callable[[str], None] | None = None,
) -> None:
    assert_public_write_path_allowed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = pretty_json_bytes(payload)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            if crash_hook:
                crash_hook(f"{label}:after_temp_write")
            handle.flush()
            os.fsync(handle.fileno())
        if crash_hook:
            crash_hook(f"{label}:after_temp_fsync")
        os.replace(temporary, path)
        replaced = True
        if crash_hook:
            crash_hook(f"{label}:after_replace")
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if crash_hook:
            crash_hook(f"{label}:after_parent_fsync")
    finally:
        if not replaced and temporary.exists():
            temporary.unlink()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_HOSTILE_REVIEW_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "ready_for_hostile_review": False,
        "ready_for_prose": False,
        "what_is_not_concluded": HOSTILE_REVIEW_NONCLAIMS,
    }


__all__ = [
    "HOSTILE_REVIEW_NONCLAIMS",
    "SURVEY_FINAL_PACKET_READINESS_SCHEMA_VERSION",
    "SURVEY_HOSTILE_REVIEW_RESULT_SCHEMA_VERSION",
    "SURVEY_HOSTILE_REVIEW_SCHEMA_VERSION",
    "refresh_final_packet_readiness",
    "run_hostile_review_gate",
    "validate_final_packet_readiness",
    "validate_hostile_review_result",
]
