from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey.anchors import _extract_anchor_rows
from research_assistant.survey.artifact_lineage import (
    COVERAGE_FILES,
    ArtifactStateManager,
    semantic_item,
    workflow_blocker_source_id,
)
from research_assistant.survey.claim_review import (
    SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
    SURVEY_CLAIM_REVIEW_V3_SCHEMA,
    import_reviewed_claims,
    resolve_current_reviewed_claims,
)
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.hostile_review import (
    HOSTILE_REVIEW_NONCLAIMS,
    _hostile_blockers,
    refresh_final_packet_readiness,
    run_hostile_review_gate,
    validate_final_packet_readiness,
    validate_hostile_review_result,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.omission_review import import_reviewed_omissions
from research_assistant.survey.orchestrate import _final_artifact_statuses
from research_assistant.survey.review_decisions import REVIEW_DECISIONS_SCHEMA
from research_assistant.survey.reviewed_merge import merge_reviewed_evidence
from research_assistant.survey.reviewed_packet import (
    REVIEWED_FINAL_PACKET_NONCLAIMS,
    _add_opaque_input,
    _evidence_classifications,
    _validated_local_evidence_root,
    compose_reviewed_final_packet,
    validate_reviewed_final_packet,
)
from research_assistant.survey.source_safety_review import import_reviewed_source_safety
from research_assistant.survey.workflow_blocker_review import import_reviewed_workflow_blockers
from test_literature_survey_m16_phase8 import (
    _canonical_v2_mission,
    _import_complete_v2_reviews,
)


MISSION_ID = "44444444-4444-4444-8444-444444444444"
MISSION_NONCE = "404142434445464748494a4b4c4d4e4f"
ARTIFACT_NONCE = "505152535455565758595a5b5c5d5e5f"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_phase4_fixture(
    tmp_path: Path,
    *,
    blocked_frontiers: tuple[str, ...] = (),
    claim_support_classes: tuple[str, ...] = ("primary_technical_support",),
    local_artifact: str = "proof.txt",
    local_evidence_directory: str = "local_evidence",
    foreign_omission_source_ids: bool = False,
) -> dict[str, Path]:
    packet_dir = tmp_path / "packet"
    anchor_dir = tmp_path / "anchors"
    source_path = tmp_path / "source-records" / "paper-1.json"
    source = {
        "paper_id": "paper-1",
        "source_type": "arxiv_latex",
        "status": "available",
        "primary_for_audit": True,
        "provenance": {"arxiv_id": "0000.00004v1"},
        "sections": [{
            "title": "Method",
            "labels": ["sec-method"],
            "line": 10,
            "raw_latex": "The fixture method minimizes a checked objective.",
        }],
        "equations": [],
        "theorem_like_blocks": [],
        "citations": [],
        "bibliography": [],
        "references": [],
        "labels": [],
        "macros": [],
        "limitations": [],
    }
    _write_json(source_path, source)
    anchor = _extract_anchor_rows(
        paper_id="paper-1",
        source_path=source_path,
        record=source,
        max_anchors=8,
    )[0]
    anchor_payloads = {
        "source_anchor_inventory.json": {
            "schema_version": "ra-survey-source-anchor-inventory-v1",
            "status": "anchors_extracted",
            "topic": "Phase 4 replay fixture",
            "paper_ids": ["paper-1"],
            "anchor_count": 1,
            "anchors": [anchor],
            "raw_text_policy": {"raw_latex_included": False, "anchor_hashes_included": True},
            "not_concluded": ["technical claim support"],
        },
        "source_support.json": {
            "schema_version": "ra-survey-anchor-source-support-v1",
            "status": "source_anchors_available",
            "topic": "Phase 4 replay fixture",
            "papers": [{
                "paper_id": "paper-1",
                "source_status": "available",
                "source_record_path": str(source_path),
                "checked_anchors": [anchor["anchor_id"]],
                "checked_anchor_count": 1,
                "technical_claim_support": "not_supported_until_claim_mapping_review",
            }],
            "source_gap_rows": [],
            "not_concluded": ["technical claim support"],
        },
        "claim_support.json": {
            "schema_version": "ra-survey-anchor-claim-support-v1",
            "status": "anchors_extracted_no_supported_technical_claims",
            "claims": [],
            "blocked_claims": [],
        },
        "quarantine_register.json": {
            "schema_version": "ra-survey-anchor-quarantine-register-v1",
            "status": "fixture",
            "rows": [],
            "source_gap_rows": [],
        },
    }
    for name, payload in anchor_payloads.items():
        _write_json(anchor_dir / name, payload)

    input_paths = {
        "anchor_inventory": anchor_dir / "source_anchor_inventory.json",
        "anchor_source_support": anchor_dir / "source_support.json",
        "anchor_claim_support": anchor_dir / "claim_support.json",
        "quarantine_register": anchor_dir / "quarantine_register.json",
    }
    packet_payloads = {
        "candidate_ledger.json": {"schema_version": "candidate-v1", "included": []},
        "citation_map.json": {"schema_version": "citation-v1", "frontiers": []},
        "paper_classifications.json": {"schema_version": "classifications-v1", "classifications": []},
        "omission_risk.json": {"schema_version": "omission-v1", "risks": []},
        "claim_support.json": {
            "schema_version": "claims-v1",
            "claim_candidates": [{
                "claim_id": "claim-1",
                "status": "review_required",
                "claim_support_allowed": False,
                "paper_ids": ["paper-1"],
                "anchor_ids": [anchor["anchor_id"]],
            }],
        },
        "source_safety_status.json": {
            "schema_version": "safety-v1",
            "rows": [{
                "paper_id": "paper-1",
                "arxiv_id": "0000.00004v1",
                "safety_checked_clear": False,
                "claim_support_allowed": False,
            }],
        },
        "build_manifest.json": {
            "schema_version": "packet-v1",
            "input_paths": {role: str(path) for role, path in input_paths.items()},
            "input_sha256": {role: _sha256(path) for role, path in input_paths.items()},
            "workflow_state": {"blocked_reasons": ["no reviewed supported technical claim rows are present"]},
        },
    }
    for name, payload in packet_payloads.items():
        _write_json(packet_dir / name, payload)

    mission_root = tmp_path / "mission"
    mission_root.mkdir()
    mission = MissionStateManager(
        output_dir=mission_root,
        topic="Phase 4 replay fixture",
        seeds=["arxiv:0000.00004"],
        confirm_public_discovery=False,
        resume=False,
        force=False,
        now=lambda: "2026-07-11T00:00:00+00:00",
        nonce_factory=lambda: MISSION_NONCE,
        mission_id_factory=lambda: MISSION_ID,
    )
    mission.begin()
    committed = mission.commit(
        {
            "status": "ready_for_local_continuation",
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:00:00+00:00",
            "topic": "Phase 4 replay fixture",
            "seeds": ["arxiv:0000.00004"],
            "output_dir": str(mission_root),
            "phase_statuses": {
                "public_source_packet": {"exists": True, "path": str(packet_dir)},
                "source_anchors": {"exists": True, "path": str(anchor_dir)},
            },
        },
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "fixture",
            "mission_status": "ready_for_local_continuation",
            "action_id": "fixture",
        },
    )
    assert committed.current_pointer is not None
    local_evidence_root = mission_root / local_evidence_directory
    local_artifact_path = local_evidence_root / "proof.txt"
    if any(value in {"project_derivation", "implementation_evidence"} for value in claim_support_classes):
        candidate = Path(local_artifact)
        if not candidate.is_absolute() and all(part not in {"", ".", ".."} for part in candidate.parts):
            local_artifact_path = local_evidence_root / candidate
        local_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        local_artifact_path.write_text("checked local evidence\n")

    coverage_risks = [{
        "risk_id": "risk-1",
        "severity": "medium",
        "risk": "Fixture omission risk.",
        "status": "open",
        "literature_completeness_allowed": False,
    }]
    for direction in blocked_frontiers:
        coverage_risks.append({
            "risk_id": f"{direction}_snowball_frontier_blocked_or_empty",
            "severity": "high",
            "risk": f"{direction} frontier is blocked.",
            "status": "open",
            "literature_completeness_allowed": False,
        })
    coverage = {
        "backward_snowball.json": {
            "schema_version": "backward-v1",
            "status": "blocked_or_empty" if "backward" in blocked_frontiers else "present_metadata_only",
            "evidence_policy": {
                "metadata_relations_support_navigation": True,
                "metadata_relations_support_technical_claims": False,
                "metadata_relations_support_completeness_claims": False,
            },
            "what_is_not_concluded": ["literature completeness"],
        },
        "forward_snowball.json": {
            "schema_version": "forward-v1",
            "status": "blocked_or_empty" if "forward" in blocked_frontiers else "present_metadata_only",
            "evidence_policy": {
                "metadata_relations_support_navigation": True,
                "metadata_relations_support_technical_claims": False,
                "metadata_relations_support_completeness_claims": False,
            },
            "what_is_not_concluded": ["literature completeness"],
        },
        "citation_venue_metadata.json": {
            "schema_version": "citation-metadata-v1",
            "metadata_policy": {
                "citation_counts_are_coverage_signals_only": True,
                "metadata_supports_technical_claims": False,
            },
            "what_is_not_concluded": ["literature completeness"],
        },
        "omitted_paper_risks.json": {
            "schema_version": "omitted-v1",
            "status": "omission_risks_visible",
            "risks": coverage_risks,
            "review_policy": {"omission_visibility_is_not_literature_completeness": True},
            "what_is_not_concluded": ["literature completeness"],
        },
        "paper_classifications.json": {
            "schema_version": "coverage-classifications-v1",
            "classifications": [],
            "what_is_not_concluded": ["literature completeness"],
        },
    }
    assert set(coverage) == set(COVERAGE_FILES)

    claim_items = []
    for index, support_class in enumerate(claim_support_classes, start=1):
        semantic_fields = {
            "priority": "high",
            "status": "review_required",
            "claim_support_allowed": False,
        }
        if support_class == "primary_technical_support":
            semantic_fields.update({
                "paper_ids": ["paper-1"],
                "anchor_ids": [anchor["anchor_id"]],
            })
        claim_items.append(semantic_item(
            queue_type="claim_candidate",
            source_id=f"claim-{index}",
            semantic_fields=semantic_fields,
        ))
    review_items = [
        *claim_items,
        semantic_item(
            queue_type="source_safety",
            source_id="paper-1",
            semantic_fields={
                "priority": "high",
                "status": "blocked_pending_evidence",
                "paper_id": "paper-1",
                "arxiv_id": "0000.00004v1",
                "safety_checked_clear": False,
                "claim_support_allowed": False,
            },
        ),
        *[
            semantic_item(
                queue_type="omission_risk",
                source_id=(
                    f"foreign-{row['risk_id']}"
                    if foreign_omission_source_ids
                    else row["risk_id"]
                ),
                semantic_fields={
                    "priority": row["severity"],
                    "status": "blocked_pending_evidence",
                    "risk_id": row["risk_id"],
                    "severity": row["severity"],
                    "literature_completeness_allowed": False,
                },
            )
            for row in coverage_risks
        ],
    ]
    reason = "no reviewed supported technical claim rows are present"
    review_items.append(semantic_item(
        queue_type="workflow_blocker",
        source_id=workflow_blocker_source_id(reason),
        semantic_fields={
            "priority": "high",
            "status": "blocked_pending_evidence",
            "reason": reason,
            "resolution_class": "claim_review",
            "required_evidence_queue_type": "claim_candidate",
            "required_evidence_queue_item_ids": sorted(item["item_id"] for item in claim_items),
            "ready_for_prose": False,
        },
    ))
    review_items.sort(key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]))
    queue_payload = {
        "status": "review_required",
        "topic": "Phase 4 replay fixture",
        "items": review_items,
        "queue_counts": {},
        "allowed_item_statuses": ["review_required", "blocked_pending_evidence"],
        "forbidden_promotions": ["review does not create prose readiness"],
        "what_is_not_concluded": ["scientific correctness"],
    }
    selected = ArtifactStateManager(
        mission_root=mission_root,
        mission_id=committed.contract["mission_id"],
        mission_fingerprint=committed.contract["mission_fingerprint"],
        mission_anchor_generation_id=committed.current_pointer["generation_id"],
        nonce_factory=lambda: ARTIFACT_NONCE,
    ).compose_and_select(
        packet_dir=packet_dir,
        coverage_payloads=coverage,
        review_queue_payload=queue_payload,
    )
    queue = json.loads(selected.review_queue_path.read_text())
    items_by_type = {
        decision_type: [row for row in queue["items"] if row["queue_type"] == decision_type]
        for decision_type in ["claim_candidate", "source_safety", "omission_risk", "workflow_blocker"]
    }

    def envelope(decision_type: str, rows: list[dict]) -> dict:
        return {
            "schema_version": REVIEW_DECISIONS_SCHEMA,
            "decision_type": decision_type,
            "mission_id": queue["mission_id"],
            "mission_fingerprint": queue["mission_fingerprint"],
            "artifact_set_id": queue["artifact_set_id"],
            "queue_semantic_sha256": queue["queue_semantic_sha256"],
            "review_queue_sha256": _sha256(selected.review_queue_path),
            "decisions": rows,
        }

    decisions_dir = tmp_path / "decisions"
    claim_decisions = decisions_dir / "claims.json"
    claim_rows = []
    for index, (item, support_class) in enumerate(
        zip(items_by_type["claim_candidate"], claim_support_classes, strict=True),
        start=1,
    ):
        row = {
            "queue_item_id": item["item_id"],
            "claim_id": f"reviewed-claim-{index}",
            "claim_text": "The checked fixture evidence supports this bounded reviewed statement.",
            "review_status": "human_reviewed_passed",
            "support_class": support_class,
            "reviewer": "fixture-reviewer",
            "reviewed_at": "2026-07-11T00:00:00Z",
            "evidence_note": "Checked against the exact fixture evidence bytes.",
        }
        if support_class == "primary_technical_support":
            row.update({
                "paper_ids": ["paper-1"],
                "anchor_ids": [anchor["anchor_id"]],
            })
        elif support_class == "project_derivation":
            row.update({
                "derivation_id": f"derivation-{index}",
                "local_artifact": local_artifact,
                "local_artifact_sha256": _sha256(local_artifact_path),
                "derivation_note": "The artifact records the reviewed derivation steps.",
            })
        elif support_class == "implementation_evidence":
            row.update({
                "local_artifact": local_artifact,
                "local_artifact_sha256": _sha256(local_artifact_path),
            })
        else:
            raise AssertionError(f"unsupported fixture claim class: {support_class}")
        claim_rows.append(row)
    _write_json(claim_decisions, envelope("claim_candidate", claim_rows))
    assert import_reviewed_claims(
        review_queue_path=selected.review_queue_path,
        decisions_path=claim_decisions,
        output_dir=mission_root / "reviewed_claims",
    )["status"] == "reviewed_claims_complete"

    safety_decisions = decisions_dir / "safety.json"
    _write_json(safety_decisions, envelope("source_safety", [{
        "queue_item_id": items_by_type["source_safety"][0]["item_id"],
        "paper_id": "paper-1",
        "checked_status": "checked_clear",
        "evidence_type": "public_status_check",
        "evidence_source": "fixture status ledger",
        "reviewer": "fixture-reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
        "evidence_note": "Fixture-only checked-clear evidence.",
    }]))
    assert import_reviewed_source_safety(
        review_queue_path=selected.review_queue_path,
        decisions_path=safety_decisions,
        output_dir=mission_root / "reviewed_source_safety",
    )["status"] == "reviewed_source_safety_complete"

    omission_decisions = decisions_dir / "omissions.json"
    _write_json(omission_decisions, envelope("omission_risk", [{
        "queue_item_id": item["item_id"],
        "risk_id": item["risk_id"],
        "decision": "acceptable_omission",
        "reason": "Closed only for this bounded fixture scope.",
        "scope_basis": "The fixture explicitly records this current-scope boundary.",
        "reviewer": "fixture-reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
    } for item in items_by_type["omission_risk"]]))
    assert import_reviewed_omissions(
        review_queue_path=selected.review_queue_path,
        decisions_path=omission_decisions,
        output_dir=mission_root / "reviewed_omissions",
    )["status"] == "reviewed_omissions_complete"

    workflow_decisions = decisions_dir / "workflow.json"
    workflow_item = items_by_type["workflow_blocker"][0]
    _write_json(workflow_decisions, envelope("workflow_blocker", [{
        "queue_item_id": workflow_item["item_id"],
        "disposition": "resolved_by_reviewed_evidence",
        "evidence_queue_item_ids": workflow_item["required_evidence_queue_item_ids"],
        "rationale": "The exact current reviewed claim structurally addresses the aggregate blocker.",
        "reviewer": "fixture-reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
    }]))
    assert import_reviewed_workflow_blockers(
        review_queue_path=selected.review_queue_path,
        decisions_path=workflow_decisions,
        output_dir=mission_root / "reviewed_workflow_blockers",
    )["status"] == "reviewed_workflow_blockers_complete"

    sidecars = {
        "claim_candidate": mission_root / "reviewed_claims" / "reviewed_claims.json",
        "source_safety": mission_root / "reviewed_source_safety" / "reviewed_source_safety.json",
        "omission_risk": mission_root / "reviewed_omissions" / "reviewed_omission_risks.json",
        "workflow_blocker": mission_root / "reviewed_workflow_blockers" / "reviewed_workflow_blockers.json",
    }
    merge = merge_reviewed_evidence(
        review_queue_path=selected.review_queue_path,
        reviewed_claims_path=sidecars["claim_candidate"],
        reviewed_source_safety_path=sidecars["source_safety"],
        reviewed_omissions_path=sidecars["omission_risk"],
        reviewed_workflow_blockers_path=sidecars["workflow_blocker"],
        output_dir=mission_root / "reviewed_evidence",
    )
    assert merge["status"] == "blocked_invalid_review_artifacts"
    assert merge["blocked_reason"] == "legacy_evidence_authority"
    assert not (mission_root / "reviewed_evidence").exists()
    return {
        "mission_root": mission_root,
        "review_queue": selected.review_queue_path,
        "packet_dir": packet_dir,
        "anchor_dir": anchor_dir,
        "source_path": source_path,
        "local_evidence_root": local_evidence_root,
        "local_artifact_path": local_artifact_path,
        "reviewed_packet": mission_root / "reviewed_final_packet" / "reviewed_final_packet.json",
        "merge_result": merge,
    }


def _v3_local_claim_envelope(
    queue_path: Path,
    *,
    support_class: str,
    local_artifact: Path,
) -> dict:
    context = load_v2_evidence_context(queue_path)
    queue_item = next(
        row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate"
    )
    role = {
        "project_derivation": "project_derivation_source",
        "implementation_evidence": "implementation_evidence_source",
    }[support_class]
    claim_type = {
        "project_derivation": "project_mathematical_derivation",
        "implementation_evidence": "implementation_behavior",
    }[support_class]
    dependencies = [
        {
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "canonical_identifier": identity.canonical_identifier,
            "source_version": identity.source_version,
            "source_record_sha256": identity.source_record_sha256,
            "dependency_role": role,
        }
        for identity in sorted(
            context.source_identities.values(),
            key=lambda row: row.source_paper_id,
        )
    ]
    relative = str(local_artifact.relative_to(context.mission_root))
    projection = {
        "schema_version": SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        "evidence_kind": support_class,
        "local_artifact": relative,
        "local_artifact_sha256": sha256_bytes(local_artifact.read_bytes()),
        "direct_source_paper_ids": sorted(
            dependency["source_paper_id"] for dependency in dependencies
        ),
        "referenced_manifest_ids": [],
    }
    manifest_id = f"dm-{sha256_bytes(canonical_json_bytes(projection))}"
    manifests = [{"manifest_id": manifest_id, **projection}]
    graph = {
        "schema_version": "ra-survey-claim-dependency-graph-v1",
        "root_dependency_manifest_id": manifest_id,
        "dependency_manifests": manifests,
        "source_dependencies": dependencies,
    }
    decision = {
        "queue_item_id": queue_item["item_id"],
        "claim_id": f"reviewed-{support_class}",
        "claim_text": "The exact mission-local fixture records this bounded project evidence.",
        "claim_type": claim_type,
        "support_class": support_class,
        "review_status": "human_reviewed_passed",
        "reviewer": "synthetic-fixture-reviewer",
        "reviewed_at": "2026-07-12T04:03:00Z",
        "evidence_note": "Synthetic fixture review for engineering state-transition tests only.",
        "fixture_only": True,
        "source_dependencies": dependencies,
        "dependency_manifests": manifests,
        "root_dependency_manifest_id": manifest_id,
        "dependency_graph_sha256": sha256_bytes(canonical_json_bytes(graph)),
    }
    if support_class == "project_derivation":
        decision["derivation_id"] = "derivation-1"
    return {
        "schema_version": SURVEY_CLAIM_REVIEW_V3_SCHEMA,
        "decision_type": "claim_candidate",
        **context.binding,
        "decisions": [decision],
    }


def _phase4_fixture(
    tmp_path: Path,
    *,
    blocked_frontiers: tuple[str, ...] = (),
    claim_support_classes: tuple[str, ...] = ("primary_technical_support",),
    local_artifact: str = "proof.txt",
    local_evidence_directory: str = "local_evidence",
    foreign_omission_source_ids: bool = False,
) -> dict[str, Path]:
    del blocked_frontiers
    if foreign_omission_source_ids:
        raise ValueError("foreign omission joins are tested directly, not through canonical authority")
    if len(claim_support_classes) != 1:
        raise ValueError("canonical V2 fixture has exactly one claim-candidate queue item")

    monkeypatch = pytest.MonkeyPatch()
    try:
        mission_root, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    finally:
        monkeypatch.undo()

    local_evidence_root = mission_root / local_evidence_directory
    local_artifact_path = local_evidence_root / local_artifact
    support_class = claim_support_classes[0]
    if support_class in {"project_derivation", "implementation_evidence"}:
        local_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        local_artifact_path.write_text("checked local evidence\n")

    sidecars = _import_complete_v2_reviews(
        mission=mission_root,
        queue_path=queue_path,
        queue=queue,
        decisions_dir=tmp_path / "decisions",
    )
    if support_class in {"project_derivation", "implementation_evidence"}:
        claim_path = tmp_path / "decisions" / f"{support_class}.json"
        claim_path.write_bytes(pretty_json_bytes(_v3_local_claim_envelope(
            queue_path,
            support_class=support_class,
            local_artifact=local_artifact_path,
        )))
        result = import_reviewed_claims(
            review_queue_path=queue_path,
            decisions_path=claim_path,
            output_dir=mission_root / "reviewed_claims",
            force=True,
        )
        assert result["status"] == "reviewed_claims_complete"
        snapshot, _ = resolve_current_reviewed_claims(
            review_queue_path=queue_path,
            reviewed_claims_root=mission_root / "reviewed_claims",
        )
        sidecars["claim_candidate"] = snapshot.artifact_paths["reviewed_claims.json"]

    merge = merge_reviewed_evidence(
        review_queue_path=queue_path,
        reviewed_claims_path=sidecars["claim_candidate"],
        reviewed_source_safety_path=sidecars["source_safety"],
        reviewed_omissions_path=sidecars["omission_risk"],
        reviewed_workflow_blockers_path=sidecars["workflow_blocker"],
        output_dir=mission_root / "reviewed_evidence",
    )
    assert merge["status"] == "reviewed_evidence_complete", merge
    context = load_v2_evidence_context(queue_path)
    source_path = Path(next(iter(context.source_identities.values())).source_record_path)
    return {
        "mission_root": mission_root,
        "review_queue": queue_path,
        "packet_dir": mission_root / "public_source_packet",
        "anchor_dir": mission_root / "source_anchors",
        "source_path": source_path,
        "local_evidence_root": local_evidence_root,
        "local_artifact_path": local_artifact_path,
        "reviewed_packet": mission_root / "reviewed_final_packet" / "reviewed_final_packet.json",
    }


def _compose(fixture: dict[str, Path], **kwargs) -> dict:
    return compose_reviewed_final_packet(
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
        output_dir=fixture["mission_root"] / "reviewed_final_packet",
        now=lambda: "2026-07-11T01:00:00Z",
        **kwargs,
    )


def _validate(fixture: dict[str, Path], **kwargs) -> dict:
    return validate_reviewed_final_packet(
        path=fixture["reviewed_packet"],
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
        **kwargs,
    )


def _hostile(fixture: dict[str, Path], **kwargs) -> dict:
    return run_hostile_review_gate(
        reviewed_final_packet_path=fixture["reviewed_packet"],
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
        output_dir=fixture["mission_root"] / "hostile_review",
        now=lambda: "2026-07-11T02:00:00Z",
        **kwargs,
    )


def _validate_hostile(fixture: dict[str, Path]) -> dict:
    return validate_hostile_review_result(
        path=fixture["mission_root"] / "hostile_review" / "hostile_review_result.json",
        reviewed_final_packet_path=fixture["reviewed_packet"],
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
    )


def _validate_readiness(fixture: dict[str, Path]) -> dict:
    return validate_final_packet_readiness(
        path=fixture["mission_root"] / "hostile_review" / "final_packet_readiness.json",
        hostile_review_result_path=fixture["mission_root"] / "hostile_review" / "hostile_review_result.json",
        reviewed_final_packet_path=fixture["reviewed_packet"],
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
    )


def test_reviewed_packet_composes_and_replays_current_authority(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path, blocked_frontiers=("backward", "forward"))

    result = _compose(fixture)
    payload = _validate(fixture)

    assert result["status"] == "reviewed_final_packet_ready_for_hostile_review"
    assert result["ready_for_hostile_review"] is True
    assert result["ready_for_prose"] is False
    assert payload["status"] == "ready_for_hostile_review"
    assert payload["readiness_inputs"]["reviewed_evidence_blockers"] == []
    assert payload["readiness_inputs"]["ready_for_reviewed_packet"] is True
    assert payload["readiness_inputs"]["ready_for_hostile_review"] is True
    assert payload["readiness_inputs"]["ready_for_prose"] is False
    assert payload["readiness_inputs"]["reviewed_source_outcome_blocker_count"] == 0
    assert payload["readiness_inputs"]["reviewed_source_accounting_unsafe_dependency_count"] == 0
    assert payload["readiness_inputs"]["reviewed_source_accounting_missing_dependency_count"] == 0
    assert payload["readiness_inputs"]["reviewed_source_accounting_unused_included_source_count"] == 0
    assert payload["readiness_inputs"]["reviewed_source_accounting_open_quarantine_risk_count"] == 0
    assert len(payload["reviewed_sections"]["claims"]) == 1
    assert payload["reviewed_sections"]["claims"][0]["claim_id"] == "fixture-reviewed-claim"
    assert {row["direction"] for row in payload["omission_frontier_map"]} == {"backward", "forward"}
    assert all(row["reviewed_closed_for_current_scope"] for row in payload["omission_frontier_map"])
    assert payload["what_is_not_concluded"] == REVIEWED_FINAL_PACKET_NONCLAIMS


def test_legacy_v1_authority_cannot_merge_compose_or_replay_readiness(tmp_path: Path) -> None:
    fixture = _legacy_phase4_fixture(tmp_path, blocked_frontiers=("backward",))

    assert fixture["merge_result"]["blocked_reason"] == "legacy_evidence_authority"
    result = _compose(fixture)
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "legacy_evidence_authority"
    assert not fixture["reviewed_packet"].exists()

    fixture["reviewed_packet"].parent.mkdir()
    fixture["reviewed_packet"].write_bytes(pretty_json_bytes({
        "schema_version": "ra-survey-reviewed-final-packet-v1",
        "status": "ready_for_hostile_review",
    }))
    with pytest.raises(MissionStateError) as packet_error:
        _validate(fixture)
    assert packet_error.value.code == "legacy_evidence_authority"

    hostile = _hostile(fixture)
    assert hostile["status"] == "blocked"
    assert hostile["blocked_reason"] == "legacy_evidence_authority"
    assert not (fixture["mission_root"] / "hostile_review").exists()


def test_legacy_v1_final_artifact_residue_is_never_reported_ready(tmp_path: Path) -> None:
    fixture = _legacy_phase4_fixture(tmp_path)
    stale_payloads = {
        fixture["reviewed_packet"]: {
            "schema_version": "ra-survey-reviewed-final-packet-v1",
            "status": "ready_for_hostile_review",
        },
        fixture["mission_root"] / "hostile_review" / "hostile_review_result.json": {
            "schema_version": "ra-survey-hostile-review-result-v1",
            "status": "passed",
            "ready_for_hostile_review": True,
            "ready_for_prose": True,
        },
        fixture["mission_root"] / "hostile_review" / "final_packet_readiness.json": {
            "schema_version": "ra-survey-final-packet-readiness-v1",
            "status": "ready_for_prose",
            "ready_for_hostile_review": True,
            "ready_for_prose": True,
        },
    }
    for path, payload in stale_payloads.items():
        _write_json(path, payload)

    statuses = _final_artifact_statuses(
        output_dir=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
        local_evidence_root=fixture["local_evidence_root"],
    )

    assert statuses["reviewed_final_packet"]["exists"] is False
    assert statuses["reviewed_final_packet"]["lineage_status"] == "legacy_evidence_authority"
    assert statuses["hostile_review_result"]["exists"] is False
    assert statuses["hostile_review_result"]["lineage_status"] == "invalid_or_missing_reviewed_final_packet"
    assert statuses["final_packet_readiness"]["exists"] is False
    assert statuses["final_packet_readiness"]["lineage_status"] == "invalid_or_missing_hostile_review_result"
    assert all(
        status["ready_for_hostile_review"] is False and status["ready_for_prose"] is False
        for status in statuses.values()
    )


def test_packet_contained_path_edit_cannot_redirect_replay(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["status"] == "reviewed_final_packet_ready_for_hostile_review"
    payload = json.loads(fixture["reviewed_packet"].read_text())
    payload["input_artifacts"]["reviewed_evidence"]["path"] = str(tmp_path / "alternate.json")
    _write_json(fixture["reviewed_packet"], payload)

    with pytest.raises(MissionStateError) as error:
        _validate(fixture)
    assert error.value.code == "invalid_reviewed_packet_replay"


def test_selected_packet_or_anchor_byte_change_invalidates_packet(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["status"] == "reviewed_final_packet_ready_for_hostile_review"
    candidate = fixture["packet_dir"] / "candidate_ledger.json"
    original = candidate.read_bytes()
    candidate.write_bytes(original + b" ")

    with pytest.raises(MissionStateError) as packet_error:
        _validate(fixture)
    assert packet_error.value.code in {"corrupt_selected_lineage", "artifact_digest_mismatch"}

    candidate.write_bytes(original)
    anchor_inventory = fixture["anchor_dir"] / "source_anchor_inventory.json"
    anchor_inventory.write_bytes(anchor_inventory.read_bytes() + b" ")
    with pytest.raises(MissionStateError) as anchor_error:
        _validate(fixture)
    assert anchor_error.value.code == "anchor_hash_mismatch"


def test_source_record_change_invalidates_reconstructed_anchor(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["status"] == "reviewed_final_packet_ready_for_hostile_review"
    source = json.loads(fixture["source_path"].read_text())
    source["sections"][0]["raw_latex"] = "Changed source bytes and anchor content."
    _write_json(fixture["source_path"], source)

    with pytest.raises(MissionStateError) as error:
        _validate(fixture)
    assert error.value.code == "source_record_digest_mismatch"


@pytest.mark.parametrize(
    "checkpoint",
    [
        "reviewed_packet:after_temp_write",
        "reviewed_packet:after_temp_fsync",
        "reviewed_packet:after_replace",
        "reviewed_packet:after_parent_fsync",
    ],
)
def test_no_force_preserves_packet_and_failed_forced_rebuild_preserves_old_or_new_file(
    tmp_path: Path,
    checkpoint: str,
) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["status"] == "reviewed_final_packet_ready_for_hostile_review"
    before = fixture["reviewed_packet"].read_bytes()

    blocked = _compose(fixture)
    assert blocked["blocked_reason"] == "output_exists"
    assert fixture["reviewed_packet"].read_bytes() == before

    def crash(label: str) -> None:
        if label == checkpoint:
            raise RuntimeError(label)

    with pytest.raises(RuntimeError):
        compose_reviewed_final_packet(
            mission_root=fixture["mission_root"],
            review_queue_path=fixture["review_queue"],
            packet_dir=fixture["packet_dir"],
            anchor_dir=fixture["anchor_dir"],
            output_dir=fixture["mission_root"] / "reviewed_final_packet",
            force=True,
            now=lambda: "2026-07-11T01:30:00Z",
            crash_hook=crash,
        )
    after = fixture["reviewed_packet"].read_bytes()
    assert json.loads(after)["created_at"] in {"2026-07-11T01:00:00Z", "2026-07-11T01:30:00Z"}
    assert json.loads(after)["status"] == "ready_for_hostile_review"
    assert list(fixture["reviewed_packet"].parent.glob(".*.tmp")) == []


def test_local_evidence_root_rejects_state_subtrees_and_shared_binding_is_idempotent(tmp_path: Path) -> None:
    mission_root = tmp_path / "mission"
    shared_root = mission_root / "local_evidence"
    shared_root.mkdir(parents=True)
    shared = shared_root / "proof.txt"
    shared.write_text("checked local evidence")

    assert _validated_local_evidence_root(shared_root, mission_root) == shared_root
    for protected in [mission_root, mission_root / ".artifact_state", mission_root / ".mission_state"]:
        nested = protected / "nested" if protected != mission_root else protected
        nested.mkdir(parents=True, exist_ok=True)
        with pytest.raises(MissionStateError) as error:
            _validated_local_evidence_root(nested, mission_root)
        assert error.value.code == "unsafe_local_evidence_root"
    aliased = shared_root / ".." / ".artifact_state"
    with pytest.raises(MissionStateError) as alias_error:
        _validated_local_evidence_root(aliased, mission_root)
    assert alias_error.value.code == "unsafe_local_evidence_root"

    inputs: dict[str, dict] = {}
    raw = shared.read_bytes()
    _add_opaque_input(inputs, "local_evidence.proof.txt", shared, raw)
    _add_opaque_input(inputs, "local_evidence.proof.txt", shared, raw)
    assert list(inputs) == ["local_evidence.proof.txt"]
    with pytest.raises(MissionStateError) as conflict:
        _add_opaque_input(inputs, "local_evidence.proof.txt", shared, raw + b"changed")
    assert conflict.value.code == "duplicate_input_role"


@pytest.mark.parametrize("support_class", ["project_derivation", "implementation_evidence"])
def test_local_evidence_support_classes_compose_and_replay_one_shared_artifact(
    tmp_path: Path,
    support_class: str,
) -> None:
    fixture = _phase4_fixture(
        tmp_path,
        claim_support_classes=(support_class,),
    )

    result = _compose(fixture, local_evidence_root=fixture["local_evidence_root"])
    packet = _validate(fixture, local_evidence_root=fixture["local_evidence_root"])

    assert result["status"] == "reviewed_final_packet_ready_for_hostile_review"
    assert [row["support_class"] for row in packet["evidence_classifications"]] == [support_class]
    if support_class == "project_derivation":
        assert packet["evidence_classifications"][0]["derivation_id"] == "derivation-1"
    else:
        assert "derivation_id" not in packet["evidence_classifications"][0]
    assert [role for role in packet["input_artifacts"] if role.startswith("local_evidence.")] == [
        "local_evidence.local_evidence/proof.txt"
    ]


def test_local_evidence_missing_root_and_changed_bytes_block_composition(tmp_path: Path) -> None:
    missing = _phase4_fixture(tmp_path / "missing", claim_support_classes=("project_derivation",))
    result = _compose(missing)
    assert result["blocked_reason"] == "missing_local_evidence_root"
    assert not missing["reviewed_packet"].exists()

    changed = _phase4_fixture(tmp_path / "changed", claim_support_classes=("implementation_evidence",))
    changed["local_artifact_path"].write_text("changed after review\n")
    result = _compose(changed, local_evidence_root=changed["local_evidence_root"])
    assert result["blocked_reason"] == "dependency_local_artifact_digest_mismatch"
    assert not changed["reviewed_packet"].exists()


def test_local_evidence_parent_symlink_blocks_end_to_end(tmp_path: Path) -> None:
    fixture = _phase4_fixture(
        tmp_path,
        claim_support_classes=("implementation_evidence",),
        local_artifact="linked/proof.txt",
    )
    fixture["local_artifact_path"].unlink()
    fixture["local_artifact_path"].parent.rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "proof.txt").write_text("checked local evidence\n")
    fixture["local_artifact_path"].parent.symlink_to(outside, target_is_directory=True)

    result = _compose(fixture, local_evidence_root=fixture["local_evidence_root"])

    assert result["blocked_reason"] == "unsafe_dependency_local_artifact"
    assert not fixture["reviewed_packet"].exists()


def test_local_evidence_protected_root_alias_blocks_end_to_end(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path, claim_support_classes=("project_derivation",))
    alias = fixture["local_evidence_root"] / ".." / ".artifact_state"

    result = _compose(fixture, local_evidence_root=alias)

    assert result["blocked_reason"] == "unsafe_local_evidence_root"
    assert not fixture["reviewed_packet"].exists()


@pytest.mark.parametrize(
    ("directory", "artifact"),
    [
        ("reviewed_final_packet", "reviewed_final_packet.json"),
        ("hostile_review", "hostile_review_result.json"),
        ("hostile_review", "final_packet_readiness.json"),
    ],
)
def test_local_evidence_cannot_alias_phase4_outputs_even_with_force(
    tmp_path: Path,
    directory: str,
    artifact: str,
) -> None:
    fixture = _phase4_fixture(
        tmp_path,
        claim_support_classes=("implementation_evidence",),
        local_artifact=artifact,
        local_evidence_directory=directory,
    )
    before = fixture["local_artifact_path"].read_bytes()

    result = _compose(
        fixture,
        local_evidence_root=fixture["local_evidence_root"],
        force=True,
    )

    assert result["blocked_reason"] == "unsafe_local_evidence_root"
    assert fixture["local_artifact_path"].read_bytes() == before


def test_project_derivation_field_and_artifact_bytes_are_replayed(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path, claim_support_classes=("project_derivation",))
    assert _compose(fixture, local_evidence_root=fixture["local_evidence_root"])["ready_for_hostile_review"] is True
    packet = json.loads(fixture["reviewed_packet"].read_text())
    packet["evidence_classifications"][0]["derivation_id"] = "foreign-derivation"
    _write_json(fixture["reviewed_packet"], packet)

    with pytest.raises(MissionStateError) as field_error:
        _validate(fixture, local_evidence_root=fixture["local_evidence_root"])
    assert field_error.value.code == "invalid_reviewed_packet_replay"

    assert _compose(
        fixture,
        local_evidence_root=fixture["local_evidence_root"],
        force=True,
    )["ready_for_hostile_review"] is True
    fixture["local_artifact_path"].write_text("tampered after packet composition\n")
    with pytest.raises(MissionStateError) as byte_error:
        _validate(fixture, local_evidence_root=fixture["local_evidence_root"])
    assert byte_error.value.code == "dependency_local_artifact_digest_mismatch"


def test_structured_source_cache_never_rebinds_one_record_to_another_paper(tmp_path: Path) -> None:
    source_path = tmp_path / "shared-source.json"
    source = {
        "paper_id": "paper-1",
        "status": "available",
        "sections": [
            {"title": "Method", "labels": ["sec-one"], "line": 10, "raw_latex": "First."},
            {"title": "Method", "labels": ["sec-two"], "line": 20, "raw_latex": "Second."},
        ],
        "equations": [],
        "theorem_like_blocks": [],
    }
    _write_json(source_path, source)
    paper_one = _extract_anchor_rows(paper_id="paper-1", source_path=source_path, record=source, max_anchors=8)[0]
    paper_two = _extract_anchor_rows(paper_id="paper-2", source_path=source_path, record=source, max_anchors=8)[1]
    anchors = {
        "anchor_inventory": {"anchors": [paper_one, paper_two]},
        "anchor_source_support": {
            "papers": [
                {"paper_id": "paper-1", "source_record_path": str(source_path), "checked_anchors": [paper_one["anchor_id"]]},
                {"paper_id": "paper-2", "source_record_path": str(source_path), "checked_anchors": [paper_two["anchor_id"]]},
            ]
        },
    }
    claims = [{
        "claim_id": "shared-source-claim",
        "decision_sha256": "a" * 64,
        "support_class": "primary_technical_support",
        "paper_ids": ["paper-1", "paper-2"],
        "anchor_ids": [paper_one["anchor_id"], paper_two["anchor_id"]],
    }]

    with pytest.raises(MissionStateError) as error:
        _evidence_classifications(
            claims=claims,
            anchor_payloads=anchors,
            local_evidence_root=None,
            mission_root=tmp_path,
            inputs={},
            v2_authority=False,
        )
    assert error.value.code == "invalid_source_record"


def test_hostile_review_replays_packet_and_emits_scope_limited_readiness(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path, blocked_frontiers=("backward", "forward"))
    assert _compose(fixture)["ready_for_hostile_review"] is True

    result = _hostile(fixture)
    hostile = _validate_hostile(fixture)
    readiness = _validate_readiness(fixture)

    assert result["status"] == "ready_for_reviewed_prose_within_recorded_scope"
    assert result["readiness_classification"] == "READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE"
    assert result["ready_for_prose"] is True
    assert hostile["blockers"] == []
    assert {row["code"] for row in hostile["warnings"]} >= {"frontier_closed_for_recorded_scope_only"}
    assert hostile["what_is_not_concluded"] == HOSTILE_REVIEW_NONCLAIMS
    assert readiness["hostile_review_result_sha256"] == result["hostile_review_result_sha256"]
    assert readiness["ready_for_prose"] is True


def test_hostile_blockers_independently_veto_unsafe_snowball_policy_and_missing_claim_safety(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["ready_for_hostile_review"] is True
    packet = _validate(fixture)

    packet["selected_coverage"]["backward_snowball.json"]["evidence_policy"] = {
        "metadata_relations_support_navigation": True,
        "metadata_relations_support_technical_claims": True,
        "metadata_relations_support_completeness_claims": False,
    }
    packet["reviewed_sections"]["source_safety"][0]["source_paper_id"] = "different-paper"

    assert {row["code"] for row in _hostile_blockers(packet)} >= {
        "unsafe_snowball_policy",
        "missing_claim_source_safety",
    }


def test_readiness_view_tamper_cannot_override_result_and_is_regenerated(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["ready_for_hostile_review"] is True
    assert _hostile(fixture)["ready_for_prose"] is True
    authoritative_before = (fixture["mission_root"] / "hostile_review" / "hostile_review_result.json").read_bytes()
    view_path = fixture["mission_root"] / "hostile_review" / "final_packet_readiness.json"
    view = json.loads(view_path.read_text())
    view["ready_for_prose"] = False
    _write_json(view_path, view)

    with pytest.raises(MissionStateError) as error:
        _validate_readiness(fixture)
    assert error.value.code == "invalid_readiness_view_replay"
    assert _validate_hostile(fixture)["ready_for_prose"] is True

    refreshed = refresh_final_packet_readiness(
        hostile_review_result_path=fixture["mission_root"] / "hostile_review" / "hostile_review_result.json",
        reviewed_final_packet_path=fixture["reviewed_packet"],
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
    )
    assert refreshed["ready_for_prose"] is True
    assert _validate_readiness(fixture) == refreshed
    assert (fixture["mission_root"] / "hostile_review" / "hostile_review_result.json").read_bytes() == authoritative_before


def test_readiness_view_write_failure_preserves_authoritative_success(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["ready_for_hostile_review"] is True
    hostile_dir = fixture["mission_root"] / "hostile_review"
    hostile_dir.mkdir()
    outside = tmp_path / "outside-readiness.json"
    outside.write_text("do not replace\n")
    readiness_path = hostile_dir / "final_packet_readiness.json"
    readiness_path.symlink_to(outside)

    blocked = _hostile(fixture)
    assert blocked["blocked_reason"] == "output_exists"
    assert not (hostile_dir / "hostile_review_result.json").exists()

    result = _hostile(fixture, force=True)

    assert result["status"] == "ready_for_reviewed_prose_within_recorded_scope"
    assert result["ready_for_prose"] is True
    assert result["final_packet_readiness_status"] == "regeneration_required"
    assert result["final_packet_readiness_warning"]["code"] == "unsafe_public_write_path"
    assert outside.read_text() == "do not replace\n"
    assert readiness_path.is_symlink()
    assert _validate_hostile(fixture)["ready_for_prose"] is True


def test_hostile_review_rejects_raw_merge_and_invalid_packet_without_output(tmp_path: Path) -> None:
    fixture = _phase4_fixture(tmp_path)
    merge_path = fixture["mission_root"] / "reviewed_evidence" / "reviewed_evidence_status.json"

    result = run_hostile_review_gate(
        reviewed_final_packet_path=merge_path,
        mission_root=fixture["mission_root"],
        review_queue_path=fixture["review_queue"],
        packet_dir=fixture["packet_dir"],
        anchor_dir=fixture["anchor_dir"],
        output_dir=fixture["mission_root"] / "hostile_review",
    )
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "noncanonical_reviewed_packet_path"
    assert not (fixture["mission_root"] / "hostile_review").exists()

    assert _compose(fixture)["ready_for_hostile_review"] is True
    packet = json.loads(fixture["reviewed_packet"].read_text())
    packet["readiness_inputs"]["ready_for_prose"] = True
    _write_json(fixture["reviewed_packet"], packet)
    result = _hostile(fixture)
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "invalid_reviewed_packet_replay"
    assert not (fixture["mission_root"] / "hostile_review").exists()


@pytest.mark.parametrize(
    "checkpoint",
    [
        "hostile_result:after_temp_write",
        "hostile_result:after_temp_fsync",
        "hostile_result:after_replace",
        "hostile_result:after_parent_fsync",
    ],
)
def test_hostile_no_force_and_crash_preserve_authoritative_result(
    tmp_path: Path,
    checkpoint: str,
) -> None:
    fixture = _phase4_fixture(tmp_path)
    assert _compose(fixture)["ready_for_hostile_review"] is True
    assert _hostile(fixture)["ready_for_prose"] is True
    hostile_path = fixture["mission_root"] / "hostile_review" / "hostile_review_result.json"
    readiness_path = fixture["mission_root"] / "hostile_review" / "final_packet_readiness.json"
    hostile_before = hostile_path.read_bytes()
    readiness_before = readiness_path.read_bytes()

    blocked = _hostile(fixture)
    assert blocked["blocked_reason"] == "output_exists"
    assert hostile_path.read_bytes() == hostile_before
    assert readiness_path.read_bytes() == readiness_before

    def crash(label: str) -> None:
        if label == checkpoint:
            raise RuntimeError(label)

    with pytest.raises(RuntimeError):
        run_hostile_review_gate(
            reviewed_final_packet_path=fixture["reviewed_packet"],
            mission_root=fixture["mission_root"],
            review_queue_path=fixture["review_queue"],
            packet_dir=fixture["packet_dir"],
            anchor_dir=fixture["anchor_dir"],
            output_dir=fixture["mission_root"] / "hostile_review",
            force=True,
            now=lambda: "2026-07-11T02:30:00Z",
            crash_hook=crash,
        )
    hostile_after = hostile_path.read_bytes()
    assert json.loads(hostile_after)["created_at"] in {"2026-07-11T02:00:00Z", "2026-07-11T02:30:00Z"}
    assert json.loads(hostile_after)["ready_for_hostile_review"] is True
    assert readiness_path.read_bytes() == readiness_before
    assert list(hostile_path.parent.glob(".*.tmp")) == []
