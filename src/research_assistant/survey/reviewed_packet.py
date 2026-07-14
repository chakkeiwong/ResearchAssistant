from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from research_assistant.survey.anchors import _extract_anchor_rows
from research_assistant.survey.artifact_lineage import (
    COVERAGE_FILES,
    assert_public_write_path_allowed,
    validate_selected_coverage_dir,
    validate_selected_review_queue,
)
from research_assistant.survey.mission_state import (
    MISSION_CONTROL_SCHEMA,
    MissionStateError,
    pretty_json_bytes,
    validate_generation_ancestor_readonly,
)
from research_assistant.survey.omission_review import (
    OmissionDecisionSetSnapshot,
    resolve_current_reviewed_omissions,
)
from research_assistant.survey.claim_review import resolve_current_reviewed_claims
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.review_decisions import (
    normalize_reviewed_at,
    read_json_object_strict,
    utc_now_iso,
)
from research_assistant.survey.reviewed_merge import (
    DECISION_TYPES,
    SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION,
    validate_current_reviewed_sidecar,
    validate_reviewed_evidence_status,
)
from research_assistant.survey.source_safety_review import resolve_current_source_safety


SURVEY_REVIEWED_FINAL_PACKET_SCHEMA_VERSION = "ra-survey-reviewed-final-packet-v1"
SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION = "ra-survey-reviewed-final-packet-v2"
SURVEY_REVIEWED_FINAL_PACKET_RESULT_SCHEMA_VERSION = "ra-survey-reviewed-final-packet-result-v1"

PACKET_INPUT_FILES = {
    "candidate_ledger": "candidate_ledger.json",
    "citation_map": "citation_map.json",
    "paper_classifications": "paper_classifications.json",
    "omission_risk": "omission_risk.json",
    "claim_support": "claim_support.json",
    "source_safety_status": "source_safety_status.json",
    "build_manifest": "build_manifest.json",
}
ANCHOR_INPUT_FILES = {
    "anchor_inventory": "source_anchor_inventory.json",
    "anchor_source_support": "source_support.json",
    "anchor_claim_support": "claim_support.json",
    "quarantine_register": "quarantine_register.json",
}
SIDECAR_FILES = {
    "claim_candidate": ("reviewed_claims", "reviewed_claims.json"),
    "source_safety": ("reviewed_source_safety", "reviewed_source_safety.json"),
    "omission_risk": ("reviewed_omissions", "reviewed_omission_risks.json"),
    "workflow_blocker": ("reviewed_workflow_blockers", "reviewed_workflow_blockers.json"),
}
REVIEWED_FINAL_PACKET_NONCLAIMS = [
    "human or model review quality",
    "claim truth",
    "derivation correctness",
    "source safety in fact",
    "omission correctness",
    "literature completeness",
    "live web coverage",
    "final prose quality",
    "product readiness",
    "release readiness",
    "scientific correctness",
]
REVIEWED_FINAL_PACKET_KEYS = {
    "schema_version",
    "status",
    "created_at",
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
    "artifact_set_manifest_sha256",
    "queue_semantic_sha256",
    "review_queue_sha256",
    "input_artifacts",
    "review_queue",
    "original_packet",
    "selected_coverage",
    "reviewed_sections",
    "evidence_classifications",
    "decision_coverage",
    "omission_frontier_map",
    "readiness_inputs",
    "what_is_not_concluded",
}
REVIEWED_FINAL_PACKET_V2_KEYS = REVIEWED_FINAL_PACKET_KEYS | {"merge_diagnostics"}


def compose_reviewed_final_packet(
    *,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    local_evidence_root: Path | None = None,
    output_dir: Path,
    force: bool = False,
    now: Callable[[], str] = utc_now_iso,
    crash_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    mission_root = mission_root.absolute()
    output_dir = output_dir.absolute()
    expected_output = mission_root / "reviewed_final_packet"
    output_path = output_dir / "reviewed_final_packet.json"
    if output_dir != expected_output:
        return _blocked(
            "noncanonical_reviewed_packet_output",
            output_dir,
            [f"write the reviewed packet only to {expected_output}"],
        )
    try:
        load_v2_evidence_context(review_queue_path)
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    if output_path.exists() and not force:
        return _blocked("output_exists", output_dir, ["rerun with --force after inputs change"])
    try:
        payload = _build_reviewed_packet(
            mission_root=mission_root,
            review_queue_path=review_queue_path,
            packet_dir=packet_dir,
            anchor_dir=anchor_dir,
            local_evidence_root=local_evidence_root,
            created_at=now(),
        )
        _atomic_write_json(output_path, payload, crash_hook=crash_hook)
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    return {
        "schema_version": SURVEY_REVIEWED_FINAL_PACKET_RESULT_SCHEMA_VERSION,
        "status": "reviewed_final_packet_ready_for_hostile_review",
        "output_dir": str(output_dir),
        "reviewed_final_packet_path": str(output_path),
        "reviewed_final_packet_sha256": _sha256(output_path.read_bytes()),
        "ready_for_reviewed_packet": True,
        "ready_for_hostile_review": True,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_FINAL_PACKET_NONCLAIMS,
    }


def validate_reviewed_final_packet(
    *,
    path: Path,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    local_evidence_root: Path | None = None,
) -> dict[str, Any]:
    mission_root = mission_root.absolute()
    expected_path = mission_root / "reviewed_final_packet" / "reviewed_final_packet.json"
    supplied = path.absolute()
    if supplied != expected_path or supplied.is_symlink():
        raise MissionStateError(
            "noncanonical_reviewed_packet_path",
            "reviewed final packet must use the fixed mission-local path",
        )
    load_v2_evidence_context(review_queue_path)
    payload, raw = read_json_object_strict(supplied, label="reviewed final packet")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_reviewed_packet", "reviewed final packet bytes are not canonical")
    expected_keys = (
        REVIEWED_FINAL_PACKET_V2_KEYS
        if payload.get("schema_version") == SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION
        else REVIEWED_FINAL_PACKET_KEYS
    )
    if set(payload) != expected_keys:
        raise MissionStateError("invalid_reviewed_packet_schema", "reviewed final packet fields do not match exact schema")
    if payload.get("schema_version") not in {
        SURVEY_REVIEWED_FINAL_PACKET_SCHEMA_VERSION,
        SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION,
    }:
        raise MissionStateError("invalid_reviewed_packet_schema", "reviewed final packet schema is unsupported")
    expected = _build_reviewed_packet(
        mission_root=mission_root,
        review_queue_path=review_queue_path,
        packet_dir=packet_dir,
        anchor_dir=anchor_dir,
        local_evidence_root=local_evidence_root,
        created_at=payload.get("created_at"),
    )
    if payload != expected:
        raise MissionStateError(
            "invalid_reviewed_packet_replay",
            "reviewed final packet differs from current authoritative input replay",
        )
    return payload


def _build_reviewed_packet(
    *,
    mission_root: Path,
    review_queue_path: Path,
    packet_dir: Path,
    anchor_dir: Path,
    local_evidence_root: Path | None,
    created_at: Any,
) -> dict[str, Any]:
    created_at = normalize_reviewed_at(created_at)
    snapshot = validate_selected_review_queue(review_queue_path)
    coverage_snapshot = validate_selected_coverage_dir(snapshot.coverage_dir)
    _require_exact_directory(mission_root, snapshot.mission_root, label="mission root")
    if coverage_snapshot.artifact_set_id != snapshot.artifact_set_id:
        raise MissionStateError("stale_lineage", "selected queue and coverage use different artifact sets")

    mission_control = _validated_current_mission_control(snapshot)
    packet_dir = _require_phase_root(
        packet_dir,
        mission_control,
        phase="public_source_packet",
        label="original packet directory",
    )
    anchor_dir = _require_phase_root(
        anchor_dir,
        mission_control,
        phase="source_anchors",
        label="anchor directory",
    )

    inputs: dict[str, dict[str, Any]] = {}
    manifest_path = snapshot.set_dir / "artifact_set_manifest.json"
    manifest, manifest_raw = read_json_object_strict(manifest_path, label="selected artifact-set manifest")
    _add_input(inputs, "artifact_set_manifest", manifest_path, manifest, manifest_raw)

    queue, queue_raw = read_json_object_strict(snapshot.review_queue_path, label="selected review queue")
    _add_input(inputs, "review_queue", snapshot.review_queue_path, queue, queue_raw)

    original_packet: dict[str, dict[str, Any]] = {}
    selected_packet_digests = manifest.get("packet_input_digests")
    if not isinstance(selected_packet_digests, dict) or set(selected_packet_digests) != set(PACKET_INPUT_FILES):
        raise MissionStateError("invalid_packet_digest_map", "selected packet input digest map is incomplete")
    for role, name in sorted(PACKET_INPUT_FILES.items()):
        file_path = _regular_child(packet_dir, name, label=f"original packet {role}")
        payload, raw = _read_json_path(file_path, label=f"original packet {role}")
        expected_digest = selected_packet_digests.get(role)
        _require_digest_match(file_path, raw, expected_digest, label=f"original packet {role}")
        original_packet[role] = payload
        _add_input(inputs, f"original_packet.{role}", file_path, payload, raw)

    selected_coverage: dict[str, dict[str, Any]] = {}
    for name in sorted((*COVERAGE_FILES, "coverage_manifest.json")):
        file_path = _regular_child(snapshot.coverage_dir, name, label=f"selected coverage {name}")
        payload, raw = _read_json_path(file_path, label=f"selected coverage {name}")
        selected_coverage[name] = payload
        _add_input(inputs, f"selected_coverage.{name}", file_path, payload, raw)

    anchor_payloads = _validated_anchor_inputs(
        anchor_dir=anchor_dir,
        packet_manifest=original_packet["build_manifest"],
        inputs=inputs,
    )

    load_v2_evidence_context(snapshot.review_queue_path)
    v2_authority = True
    sidecar_paths = _current_sidecar_paths(
        mission_root=mission_root,
        review_queue_path=snapshot.review_queue_path,
        v2_authority=v2_authority,
    )
    sidecars: dict[str, dict[str, Any]] = {}
    for decision_type in DECISION_TYPES:
        sidecar_path = sidecar_paths[decision_type]
        payload = validate_current_reviewed_sidecar(
            review_queue_path=snapshot.review_queue_path,
            decision_type=decision_type,
            sidecar_path=sidecar_path,
        )
        _, raw = read_json_object_strict(sidecar_path, label=f"{decision_type} reviewed sidecar")
        sidecars[decision_type] = payload
        _add_input(inputs, f"reviewed_sidecar.{decision_type}", sidecar_path, payload, raw)
        decisions_path = Path(payload["decisions_path"])
        decisions, decisions_raw = read_json_object_strict(
            decisions_path,
            label=f"{decision_type} decision envelope",
        )
        _add_input(inputs, f"decision_envelope.{decision_type}", decisions_path, decisions, decisions_raw)

    merge_path = mission_root / "reviewed_evidence" / "reviewed_evidence_status.json"
    merge = validate_reviewed_evidence_status(
        path=merge_path,
        review_queue_path=snapshot.review_queue_path,
        sidecar_paths=sidecar_paths,
    )
    _, merge_raw = read_json_object_strict(merge_path, label="reviewed evidence merge")
    _add_input(inputs, "reviewed_evidence", merge_path, merge, merge_raw)
    merge_diagnostics: dict[str, dict[str, Any]] = {}
    if v2_authority:
        if merge.get("schema_version") != SURVEY_REVIEWED_EVIDENCE_V3_STATUS_SCHEMA_VERSION:
            raise MissionStateError("legacy_merge_cannot_authorize_v2", "canonical V2 packet requires V3 reviewed evidence")
        diagnostic_records = merge.get("merge_diagnostics")
        if not isinstance(diagnostic_records, dict) or set(diagnostic_records) != {
            "source_accounting",
            "source_outcomes",
        }:
            raise MissionStateError("invalid_merge_diagnostics", "V3 merge diagnostic binding is incomplete")
        for role, record in sorted(diagnostic_records.items()):
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "size_bytes"}:
                raise MissionStateError("invalid_merge_diagnostics", f"merge diagnostic {role} binding is invalid")
            diagnostic_path = _strict_regular_path(Path(record["path"]), label=f"merge diagnostic {role}")
            raw = diagnostic_path.read_bytes()
            if (
                diagnostic_path.parent != merge_path.parent
                or _sha256(raw) != record["sha256"]
                or len(raw) != record["size_bytes"]
            ):
                raise MissionStateError("stale_merge_diagnostic", f"merge diagnostic {role} differs from status binding")
            payload, replayed = _read_json_path(diagnostic_path, label=f"merge diagnostic {role}")
            if replayed != raw:
                raise MissionStateError("stale_merge_diagnostic", f"merge diagnostic {role} changed during replay")
            merge_diagnostics[role] = payload
            _add_input(inputs, f"merge_diagnostic.{role}", diagnostic_path, payload, raw)
    if (
        merge.get("status") == "reviewed_evidence_blocked_unavailable_source_outcome"
        or any(str(value).startswith("unavailable_source_outcome:") for value in merge.get("blockers") or [])
    ):
        raise MissionStateError(
            "unavailable_source_outcome",
            "an unavailable source-intake outcome is a nonconvertible packet-readiness veto",
        )
    if (
        merge.get("status") != "reviewed_evidence_complete"
        or merge.get("decision_coverage_complete") is not True
        or merge.get("ready_for_reviewed_packet") is not True
        or merge.get("ready_for_prose") is not False
        or merge.get("blockers") != []
    ):
        raise MissionStateError("reviewed_evidence_not_clear", "current reviewed evidence is not clear for packet composition")

    reviewed_sections = {
        "claims": [
            row
            for row in merge["reviewed_decisions"]["claim_candidate"]
            if row.get("claim_support_allowed") is True
        ],
        "source_safety": merge["reviewed_decisions"]["source_safety"],
        "omission_risks": merge["reviewed_decisions"]["omission_risk"],
        "workflow_blockers": merge["reviewed_decisions"]["workflow_blocker"],
    }
    evidence_classifications = _evidence_classifications(
        claims=reviewed_sections["claims"],
        anchor_payloads=anchor_payloads,
        local_evidence_root=local_evidence_root,
        mission_root=mission_root,
        inputs=inputs,
        v2_authority=v2_authority,
    )
    omission_map = _omission_frontier_map(
        queue=queue,
        selected_coverage=selected_coverage,
        reviewed_omissions=reviewed_sections["omission_risks"],
    )
    decision_coverage = {
        "required_queue_item_ids": merge["required_queue_item_ids"],
        "accepted_queue_item_ids_by_type": merge["accepted_queue_item_ids_by_type"],
        "decision_hashes_by_type": {
            decision_type: sorted(
                row["decision_sha256"]
                for row in merge["reviewed_decisions"][decision_type]
            )
            for decision_type in DECISION_TYPES
        },
        "decision_coverage_complete": True,
    }
    payload = {
        "schema_version": (
            SURVEY_REVIEWED_FINAL_PACKET_V2_SCHEMA_VERSION
            if v2_authority
            else SURVEY_REVIEWED_FINAL_PACKET_SCHEMA_VERSION
        ),
        "status": "ready_for_hostile_review",
        "created_at": created_at,
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "mission_anchor_generation_id": queue["mission_anchor_generation_id"],
        "artifact_set_id": queue["artifact_set_id"],
        "artifact_set_manifest_sha256": _sha256(manifest_raw),
        "queue_semantic_sha256": queue["queue_semantic_sha256"],
        "review_queue_sha256": _sha256(queue_raw),
        "input_artifacts": dict(sorted(inputs.items())),
        "review_queue": queue,
        "original_packet": original_packet,
        "selected_coverage": selected_coverage,
        "reviewed_sections": reviewed_sections,
        "evidence_classifications": evidence_classifications,
        "decision_coverage": decision_coverage,
        "omission_frontier_map": omission_map,
        "readiness_inputs": {
            "reviewed_evidence_sha256": _sha256(merge_raw),
            "reviewed_evidence_blockers": [],
            "ready_for_reviewed_packet": True,
            "ready_for_hostile_review": True,
            "ready_for_prose": False,
        },
        "what_is_not_concluded": REVIEWED_FINAL_PACKET_NONCLAIMS,
    }
    if v2_authority:
        payload["merge_diagnostics"] = merge_diagnostics
        payload["readiness_inputs"].update({
            "reviewed_source_outcome_blocker_count": merge_diagnostics["source_outcomes"]["blocker_count"],
            "reviewed_source_accounting_unsafe_dependency_count": merge_diagnostics["source_accounting"]["unsafe_dependency_count"],
            "reviewed_source_accounting_missing_dependency_count": merge_diagnostics["source_accounting"]["missing_dependency_count"],
            "reviewed_source_accounting_unused_included_source_count": merge_diagnostics["source_accounting"]["unused_included_source_count"],
            "reviewed_source_accounting_open_quarantine_risk_count": merge_diagnostics["source_accounting"]["open_quarantine_risk_count"],
        })
    return payload


def _validated_current_mission_control(snapshot: Any) -> dict[str, Any]:
    ancestry = validate_generation_ancestor_readonly(
        output_dir=snapshot.mission_root,
        mission_id=snapshot.manifest["mission_id"],
        mission_fingerprint=snapshot.manifest["mission_fingerprint"],
        generation_id=snapshot.manifest["mission_anchor_generation_id"],
    )
    current_generation = ancestry["current_generation_id"]
    path = snapshot.mission_root / ".mission_state" / "generations" / current_generation / "mission_control.json"
    payload, raw = read_json_object_strict(path, label="current mission control")
    if raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_mission_control", "current mission control is not canonical pretty JSON")
    if payload.get("schema_version") != MISSION_CONTROL_SCHEMA:
        raise MissionStateError("invalid_mission_control_schema", "current mission control schema is unsupported")
    for field, expected in {
        "mission_id": snapshot.manifest["mission_id"],
        "mission_fingerprint": snapshot.manifest["mission_fingerprint"],
        "generation_id": current_generation,
    }.items():
        if payload.get(field) != expected:
            raise MissionStateError("foreign_lineage", f"current mission control {field} is not authoritative")
    return payload


def _require_phase_root(
    supplied: Path,
    mission_control: dict[str, Any],
    *,
    phase: str,
    label: str,
) -> Path:
    statuses = mission_control.get("phase_statuses")
    if not isinstance(statuses, dict) or not isinstance(statuses.get(phase), dict):
        raise MissionStateError("missing_phase_authority", f"current mission control does not record {phase}")
    value = statuses[phase].get("path")
    if not isinstance(value, str) or not value or not Path(value).is_absolute() or os.path.normpath(value) != value:
        raise MissionStateError("invalid_phase_authority", f"current mission control has invalid {phase} path")
    expected = Path(value)
    _require_exact_directory(supplied, expected, label=label)
    return expected


def _validated_anchor_inputs(
    *,
    anchor_dir: Path,
    packet_manifest: dict[str, Any],
    inputs: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    hashes = packet_manifest.get("input_sha256")
    paths = packet_manifest.get("input_paths")
    if not isinstance(hashes, dict) or not isinstance(paths, dict):
        raise MissionStateError("invalid_packet_manifest", "selected packet manifest lacks input hash/path authority")
    result: dict[str, dict[str, Any]] = {}
    for role, name in sorted(ANCHOR_INPUT_FILES.items()):
        file_path = _regular_child(anchor_dir, name, label=f"anchor input {role}")
        if paths.get(role) != str(file_path):
            raise MissionStateError("anchor_path_mismatch", f"selected packet {role} path differs from current anchor root")
        payload, raw = _read_json_path(file_path, label=f"anchor input {role}")
        if hashes.get(role) != _sha256(raw):
            raise MissionStateError("anchor_hash_mismatch", f"selected packet {role} hash differs from current anchor bytes")
        result[role] = payload
        _add_input(inputs, f"anchor.{role}", file_path, payload, raw)
    return result


def _evidence_classifications(
    *,
    claims: list[dict[str, Any]],
    anchor_payloads: dict[str, dict[str, Any]],
    local_evidence_root: Path | None,
    mission_root: Path,
    inputs: dict[str, dict[str, Any]],
    v2_authority: bool,
) -> list[dict[str, Any]]:
    inventory_rows = anchor_payloads["anchor_inventory"].get("anchors")
    support_rows = anchor_payloads["anchor_source_support"].get("papers")
    if not isinstance(inventory_rows, list) or any(not isinstance(row, dict) for row in inventory_rows):
        raise MissionStateError("invalid_anchor_inventory", "anchor inventory rows must be objects")
    if not isinstance(support_rows, list) or any(not isinstance(row, dict) for row in support_rows):
        raise MissionStateError("invalid_anchor_support", "anchor source-support rows must be objects")
    result: list[dict[str, Any]] = []
    source_cache: dict[tuple[str, str], tuple[dict[str, Any], bytes, Path]] = {}
    for claim in claims:
        support_class = claim.get("support_class")
        base = {
            "claim_id": claim["claim_id"],
            "decision_sha256": claim["decision_sha256"],
            "support_class": support_class,
        }
        if support_class == "primary_technical_support":
            paper_ids = list(claim.get("paper_ids") or [])
            anchor_ids = list(claim.get("anchor_ids") or [])
            bound: list[dict[str, Any]] = []
            seen_papers: set[str] = set()
            for anchor_id in anchor_ids:
                matches = [
                    row for row in inventory_rows
                    if row.get("anchor_id") == anchor_id and row.get("paper_id") in paper_ids
                ]
                if len(matches) != 1:
                    raise MissionStateError("invalid_claim_anchor_binding", f"claim anchor {anchor_id} is not unique and current")
                anchor = matches[0]
                paper_id = str(anchor["paper_id"])
                source_support = [row for row in support_rows if row.get("paper_id") == paper_id]
                if len(source_support) != 1 or anchor_id not in (source_support[0].get("checked_anchors") or []):
                    raise MissionStateError("invalid_claim_anchor_binding", f"claim anchor {anchor_id} lacks exact source support")
                source_path_value = anchor.get("source_record_path")
                if not isinstance(source_path_value, str) or not Path(source_path_value).is_absolute() or os.path.normpath(source_path_value) != source_path_value:
                    raise MissionStateError("invalid_source_record_path", f"claim anchor {anchor_id} has invalid source record path")
                if source_support[0].get("source_record_path") != source_path_value:
                    raise MissionStateError("invalid_claim_anchor_binding", f"claim anchor {anchor_id} source paths disagree")
                cache_key = (source_path_value, paper_id)
                if cache_key not in source_cache:
                    source_path = _strict_regular_path(Path(source_path_value), label=f"source record {paper_id}")
                    source, source_raw = _read_json_path(source_path, label=f"source record {paper_id}")
                    if source.get("status") != "available" or source.get("paper_id") != paper_id:
                        raise MissionStateError("invalid_source_record", f"source record for {paper_id} is not available/current")
                    source_cache[cache_key] = (source, source_raw, source_path)
                    _add_input(inputs, f"source_record.{paper_id}", source_path, source, source_raw)
                source, source_raw, source_path = source_cache[cache_key]
                if source.get("status") != "available" or source.get("paper_id") != paper_id:
                    raise MissionStateError("invalid_source_record", f"source record for {paper_id} is not available/current")
                reconstructed = _extract_anchor_rows(
                    paper_id=paper_id,
                    source_path=source_path,
                    record=source,
                    max_anchors=max(1, sum(len(source.get(key) or []) for key in ("sections", "equations", "theorem_like_blocks"))),
                )
                exact = [row for row in reconstructed if row.get("anchor_id") == anchor_id]
                if len(exact) != 1 or exact[0] != anchor:
                    raise MissionStateError("anchor_content_mismatch", f"claim anchor {anchor_id} differs from source reconstruction")
                seen_papers.add(paper_id)
                bound.append({
                    "anchor_id": anchor_id,
                    "paper_id": paper_id,
                    "raw_latex_sha256": anchor.get("raw_latex_sha256"),
                    "raw_latex_bytes": anchor.get("raw_latex_bytes"),
                    "source_record_sha256": _sha256(source_raw),
                })
            if seen_papers != set(paper_ids):
                raise MissionStateError("invalid_claim_anchor_binding", "every cited paper must own a cited current anchor")
            result.append({**base, "paper_ids": paper_ids, "anchor_ids": anchor_ids, "bound_anchors": bound})
        elif support_class in {"project_derivation", "implementation_evidence"}:
            root = _validated_local_evidence_root(local_evidence_root, mission_root)
            if v2_authority:
                manifests = claim.get("dependency_manifests")
                if not isinstance(manifests, list) or not manifests:
                    raise MissionStateError("missing_dependency_local_artifact", "V2 local support requires dependency manifests")
                bound_artifacts = []
                for manifest in manifests:
                    if not isinstance(manifest, dict):
                        raise MissionStateError("invalid_dependency_manifest", "local dependency manifest is invalid")
                    relative = _safe_relative_path(manifest.get("local_artifact"), label="local_artifact")
                    artifact = _regular_child(mission_root, relative, label="local evidence artifact")
                    if not _is_beneath(artifact, root):
                        raise MissionStateError("unsafe_local_evidence_root", "dependency local artifact is outside --local-evidence-root")
                    raw = artifact.read_bytes()
                    if _sha256(raw) != manifest.get("local_artifact_sha256"):
                        raise MissionStateError("local_evidence_hash_mismatch", "dependency local artifact hash differs from reviewed decision")
                    role = f"local_evidence.{relative}"
                    _add_opaque_input(inputs, role, artifact, raw)
                    bound_artifacts.append({
                        "manifest_id": manifest["manifest_id"],
                        "local_artifact": relative,
                        "local_artifact_sha256": _sha256(raw),
                    })
                by_id = {row["manifest_id"]: row for row in bound_artifacts}
                root_id = claim.get("root_dependency_manifest_id")
                if root_id not in by_id:
                    raise MissionStateError("missing_dependency_root", "local dependency root lacks bound artifact bytes")
                row = {
                    **base,
                    "root_dependency_manifest_id": root_id,
                    "bound_local_artifacts": sorted(bound_artifacts, key=lambda value: value["manifest_id"]),
                    "local_artifact": by_id[root_id]["local_artifact"],
                    "local_artifact_sha256": by_id[root_id]["local_artifact_sha256"],
                }
            else:
                relative = _safe_relative_path(claim.get("local_artifact"), label="local_artifact")
                artifact = _regular_child(root, relative, label="local evidence artifact")
                raw = artifact.read_bytes()
                if _sha256(raw) != claim.get("local_artifact_sha256"):
                    raise MissionStateError("local_evidence_hash_mismatch", "local evidence differs from reviewed decision")
                _add_opaque_input(inputs, f"local_evidence.{relative}", artifact, raw)
                row = {
                    **base,
                    "local_artifact": relative,
                    "local_artifact_sha256": _sha256(raw),
                }
            if support_class == "project_derivation":
                row["derivation_id"] = claim["derivation_id"]
            result.append(row)
        else:
            raise MissionStateError("invalid_claim_support_class", f"unsupported reviewed support class: {support_class}")
    return sorted(result, key=lambda row: (row["claim_id"], row["decision_sha256"]))


def _omission_frontier_map(
    *,
    queue: dict[str, Any],
    selected_coverage: dict[str, dict[str, Any]],
    reviewed_omissions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    omitted_rows = selected_coverage["omitted_paper_risks.json"].get("risks")
    if not isinstance(omitted_rows, list) or any(not isinstance(row, dict) for row in omitted_rows):
        raise MissionStateError("invalid_omission_coverage", "selected omitted-paper risks must be objects")
    risk_ids = [row.get("risk_id") for row in omitted_rows]
    if any(not isinstance(value, str) or not value for value in risk_ids) or len(risk_ids) != len(set(risk_ids)):
        raise MissionStateError("invalid_omission_coverage", "selected coverage risk IDs must be unique nonempty strings")
    queue_rows = [row for row in queue.get("items") or [] if row.get("queue_type") == "omission_risk"]
    queue_by_risk: dict[str, list[dict[str, Any]]] = {}
    for row in queue_rows:
        risk_id = str(row.get("risk_id") or "")
        if row.get("source_id") != risk_id:
            raise MissionStateError(
                "invalid_omission_join",
                "omission queue source_id must equal its exact risk_id",
            )
        queue_by_risk.setdefault(risk_id, []).append(row)
    reviewed_by_risk: dict[str, list[dict[str, Any]]] = {}
    for row in reviewed_omissions:
        reviewed_by_risk.setdefault(str(row.get("risk_id") or ""), []).append(row)
    if set(risk_ids) != set(queue_by_risk) or set(risk_ids) != set(reviewed_by_risk):
        raise MissionStateError("invalid_omission_join", "coverage, queue, and reviewed omission risk-ID sets differ")
    for risk_id in risk_ids:
        if len(queue_by_risk[risk_id]) != 1 or len(reviewed_by_risk[risk_id]) != 1:
            raise MissionStateError("invalid_omission_join", f"omission risk {risk_id} is not one-to-one")
        if reviewed_by_risk[risk_id][0].get("queue_item_id") != queue_by_risk[risk_id][0].get("item_id"):
            raise MissionStateError("invalid_omission_join", f"omission risk {risk_id} queue binding differs")
    if selected_coverage["omitted_paper_risks.json"].get("schema_version") == "ra-survey-omitted-paper-risks-v2":
        coverage_by_risk = {row["risk_id"]: row for row in omitted_rows}
        fields = (
            "machine_disposition",
            "risk_source_type",
            "risk_source_id",
            "source_artifact_sha256",
        )
        for risk_id in risk_ids:
            coverage_row = coverage_by_risk[risk_id]
            queue_row = queue_by_risk[risk_id][0]
            reviewed_row = reviewed_by_risk[risk_id][0]
            for field in fields:
                if queue_row.get(field) != coverage_row.get(field) or reviewed_row.get(field) != coverage_row.get(field):
                    raise MissionStateError(
                        "invalid_omission_join",
                        f"V2 omission risk {risk_id} differs on {field}",
                    )

    manifest = selected_coverage["coverage_manifest.json"]
    blocked = manifest.get("blocked_frontiers")
    if not isinstance(blocked, list) or blocked != sorted(set(blocked)) or any(value not in {"backward", "forward"} for value in blocked):
        raise MissionStateError("invalid_frontier_map", "selected blocked-frontier directions are invalid")
    result: list[dict[str, Any]] = []
    for direction in blocked:
        ledger = selected_coverage[f"{direction}_snowball.json"]
        if not str(ledger.get("status") or "").startswith("blocked"):
            raise MissionStateError("invalid_frontier_map", f"{direction} is listed blocked but its ledger is not blocked")
        if ledger.get("schema_version") == "ra-survey-backward-snowball-v2" or ledger.get("schema_version") == "ra-survey-forward-snowball-v2":
            attempts = ledger.get("attempts")
            if not isinstance(attempts, list):
                raise MissionStateError("invalid_frontier_map", f"{direction} V2 attempts are invalid")
            attempt_risks = [
                (row.get("frontier_attempt_id"), row.get("derived_attempt_risk_id"))
                for row in attempts
                if isinstance(row, dict) and row.get("attempt_status") != "observed_results"
            ]
            if not attempt_risks or any(
                not isinstance(attempt_id, str) or not isinstance(risk_id, str)
                for attempt_id, risk_id in attempt_risks
            ):
                raise MissionStateError("invalid_frontier_map", f"blocked {direction} V2 frontier lacks exact attempt risks")
        else:
            attempt_risks = [(None, f"{direction}_snowball_frontier_blocked_or_empty")]
        for attempt_id, risk_id in attempt_risks:
            if risk_id not in queue_by_risk:
                raise MissionStateError("invalid_frontier_map", f"blocked {direction} frontier lacks its exact omission risk")
            queue_row = queue_by_risk[risk_id][0]
            decision = reviewed_by_risk[risk_id][0]
            effective_closed = decision["status"] == "reviewed_closed_for_current_scope"
            if attempt_id is not None and (
                queue_row.get("risk_source_type") != "frontier_attempt"
                or queue_row.get("risk_source_id") != attempt_id
                or decision.get("risk_source_type") != "frontier_attempt"
                or decision.get("risk_source_id") != attempt_id
            ):
                raise MissionStateError("invalid_frontier_map", f"V2 frontier risk {risk_id} source binding differs")
            mapped = {
                "direction": direction,
                "risk_id": risk_id,
                "queue_item_id": queue_row["item_id"],
                "decision_sha256": decision["decision_sha256"],
                "decision_status": decision["status"],
                "reviewed_closed_for_current_scope": effective_closed,
            }
            if attempt_id is not None:
                mapped["frontier_attempt_id"] = attempt_id
            result.append(mapped)
    for direction in {"backward", "forward"} - set(blocked):
        ledger = selected_coverage[f"{direction}_snowball.json"]
        if str(ledger.get("status") or "").startswith("blocked"):
            raise MissionStateError("invalid_frontier_map", f"blocked {direction} ledger is absent from selected manifest")
    return result


def _fixed_sidecar_paths(mission_root: Path) -> dict[str, Path]:
    return {
        decision_type: mission_root / directory / name
        for decision_type, (directory, name) in SIDECAR_FILES.items()
    }


def _current_sidecar_paths(
    *,
    mission_root: Path,
    review_queue_path: Path,
    v2_authority: bool,
) -> dict[str, Path]:
    paths = _fixed_sidecar_paths(mission_root)
    if v2_authority:
        claim_snapshot, _ = resolve_current_reviewed_claims(
            review_queue_path=review_queue_path,
            reviewed_claims_root=mission_root / "reviewed_claims",
        )
        _, source_snapshot, _ = resolve_current_source_safety(
            review_queue_path=review_queue_path,
            reviewed_source_safety_root=mission_root / "reviewed_source_safety",
        )
        paths["claim_candidate"] = claim_snapshot.artifact_paths["reviewed_claims.json"]
        paths["source_safety"] = source_snapshot.artifact_paths["reviewed_source_safety.json"]
    selected_omissions = resolve_current_reviewed_omissions(
        review_queue_path=review_queue_path,
        reviewed_omissions_root=mission_root / "reviewed_omissions",
    )
    paths["omission_risk"] = (
        selected_omissions.sidecar_path
        if isinstance(selected_omissions, OmissionDecisionSetSnapshot)
        else selected_omissions
    )
    return paths


def _validated_local_evidence_root(root: Path | None, mission_root: Path) -> Path:
    if root is None:
        raise MissionStateError("missing_local_evidence_root", "reviewed local evidence requires --local-evidence-root")
    absolute = root.absolute()
    if os.path.normpath(str(absolute)) != str(absolute):
        raise MissionStateError(
            "unsafe_local_evidence_root",
            "local evidence root must not contain lexical path aliases",
        )
    root = _strict_directory(absolute, label="local evidence root")
    protected = [
        mission_root / ".artifact_state",
        mission_root / ".mission_state",
        mission_root / "reviewed_final_packet",
        mission_root / "hostile_review",
    ]
    if (
        root == mission_root
        or any(root == path or _is_beneath(root, path) for path in protected)
        or not _is_beneath(root, mission_root)
    ):
        raise MissionStateError("unsafe_local_evidence_root", "local evidence root must be a nonprotected mission child")
    return root


def _require_exact_directory(supplied: Path, expected: Path, *, label: str) -> None:
    supplied_absolute = supplied.absolute()
    expected_absolute = expected.absolute()
    if supplied_absolute != expected_absolute:
        raise MissionStateError("path_authority_mismatch", f"{label} differs from external authority")
    _strict_directory(supplied_absolute, label=label)


def _strict_directory(path: Path, *, label: str) -> Path:
    path = path.absolute()
    _validate_path_shape(path, leaf_directory=True, label=label)
    return path


def _strict_regular_path(path: Path, *, label: str) -> Path:
    path = path.absolute()
    _validate_path_shape(path, leaf_directory=False, label=label)
    return path


def _regular_child(root: Path, relative: str, *, label: str) -> Path:
    relative = _safe_relative_path(relative, label=label)
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    candidate = _strict_regular_path(candidate, label=label)
    if not _is_beneath(candidate, root):
        raise MissionStateError("unsafe_artifact_path", f"{label} escapes its authority root")
    return candidate


def _safe_relative_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise MissionStateError("invalid_artifact_path", f"{label} must be a nonempty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise MissionStateError("invalid_artifact_path", f"{label} is not a normalized safe relative path")
    return value


def _validate_path_shape(path: Path, *, leaf_directory: bool, label: str) -> None:
    current = Path(path.anchor)
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise MissionStateError("missing_artifact", f"{label} is missing: {path}") from exc
        if stat.S_ISLNK(mode):
            raise MissionStateError("unsafe_artifact_path", f"{label} contains a symlink: {current}")
        leaf = index == len(parts) - 1
        if leaf and leaf_directory and not stat.S_ISDIR(mode):
            raise MissionStateError("unsafe_artifact_path", f"{label} is not a directory")
        if leaf and not leaf_directory and not stat.S_ISREG(mode):
            raise MissionStateError("unsafe_artifact_path", f"{label} is not a regular file")
        if not leaf and not stat.S_ISDIR(mode):
            raise MissionStateError("unsafe_artifact_path", f"{label} parent is not a directory: {current}")


def _read_json_path(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_json", f"cannot read valid JSON for {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_schema", f"{label} must contain a JSON object")
    return payload, raw


def _require_digest_match(path: Path, raw: bytes, expected: Any, *, label: str) -> None:
    if not isinstance(expected, dict) or set(expected) != {"relative_path", "sha256", "size_bytes"}:
        raise MissionStateError("invalid_artifact_digest", f"{label} digest authority is malformed")
    if expected["relative_path"] != path.name or expected["sha256"] != _sha256(raw) or expected["size_bytes"] != len(raw):
        raise MissionStateError("artifact_digest_mismatch", f"{label} differs from selected bytes")


def _add_input(
    inputs: dict[str, dict[str, Any]],
    role: str,
    path: Path,
    payload: dict[str, Any],
    raw: bytes,
) -> None:
    if role in inputs:
        raise MissionStateError("duplicate_input_role", f"duplicate reviewed-packet input role: {role}")
    inputs[role] = {
        "role": role,
        "path": str(path.absolute()),
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
        "schema_version": str(payload.get("schema_version") or "unversioned-json-object"),
    }


def _add_opaque_input(inputs: dict[str, dict[str, Any]], role: str, path: Path, raw: bytes) -> None:
    value = {
        "role": role,
        "path": str(path.absolute()),
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
        "schema_version": "opaque-local-evidence-v1",
    }
    existing = inputs.get(role)
    if existing is not None:
        if existing != value:
            raise MissionStateError("duplicate_input_role", f"conflicting reviewed-packet input role: {role}")
        return
    inputs[role] = value


def _atomic_write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    crash_hook: Callable[[str], None] | None = None,
) -> None:
    assert_public_write_path_allowed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _strict_directory(path.parent, label="reviewed-packet output directory")
    value = pretty_json_bytes(payload)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            if crash_hook:
                crash_hook("reviewed_packet:after_temp_write")
            handle.flush()
            os.fsync(handle.fileno())
        if crash_hook:
            crash_hook("reviewed_packet:after_temp_fsync")
        os.replace(temporary, path)
        replaced = True
        if crash_hook:
            crash_hook("reviewed_packet:after_replace")
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if crash_hook:
            crash_hook("reviewed_packet:after_parent_fsync")
    finally:
        if not replaced and temporary.exists():
            temporary.unlink()


def _is_beneath(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
    except ValueError:
        return False
    return True


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_FINAL_PACKET_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "ready_for_reviewed_packet": False,
        "ready_for_hostile_review": False,
        "ready_for_prose": False,
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": REVIEWED_FINAL_PACKET_NONCLAIMS,
    }


__all__ = [
    "REVIEWED_FINAL_PACKET_NONCLAIMS",
    "SURVEY_REVIEWED_FINAL_PACKET_SCHEMA_VERSION",
    "compose_reviewed_final_packet",
    "validate_reviewed_final_packet",
]
