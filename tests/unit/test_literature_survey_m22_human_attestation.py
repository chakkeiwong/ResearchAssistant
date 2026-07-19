from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.cli import main
from research_assistant.survey.artifact_lineage import (
    COVERAGE_FILES,
    ArtifactStateManager,
    semantic_item,
    workflow_blocker_source_id,
)
from research_assistant.survey.human_attestation import (
    DECISION_TYPES,
    REVIEW_ROLES,
    export_human_receipt_archive,
    prepare_human_review_packet,
    render_human_review_materials,
    validate_human_attestation,
    validate_human_attestation_receipt,
    validate_human_receipt_archive,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    pretty_json_bytes,
)
from research_assistant.survey.review_decisions import REVIEW_DECISIONS_SCHEMA


MISSION_ID = "77777777-7777-4777-8777-777777777777"
MISSION_NONCE = "101112131415161718191a1b1c1d1e1f"
ARTIFACT_NONCE = "202122232425262728292a2b2c2d2e2f"
REVIEWED_AT = "2026-07-18T09:00:00Z"
ATTESTED_AT = "2026-07-18T10:00:00Z"


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(value))


def _selected_queue(tmp_path: Path) -> tuple[Path, dict]:
    mission_root = tmp_path / "mission"
    mission_root.mkdir()
    manager = MissionStateManager(
        output_dir=mission_root,
        topic="M22 human attestation fixture",
        seeds=["arxiv:2201.12220v3"],
        confirm_public_discovery=False,
        resume=False,
        force=False,
        now=lambda: "2026-07-18T08:00:00Z",
        nonce_factory=lambda: MISSION_NONCE,
        mission_id_factory=lambda: MISSION_ID,
    )
    manager.begin()
    committed = manager.commit(
        {
            "status": "ready_for_local_continuation",
            "created_at": "2026-07-18T08:00:00Z",
            "updated_at": "2026-07-18T08:00:00Z",
            "topic": "M22 human attestation fixture",
            "seeds": ["arxiv:2201.12220v3"],
            "output_dir": str(mission_root),
        },
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "fixture",
            "mission_status": "ready_for_local_continuation",
            "action_id": "fixture",
        },
    )
    packet = mission_root / "packet"
    packet.mkdir()
    for name in (
        "candidate_ledger.json",
        "citation_map.json",
        "paper_classifications.json",
        "omission_risk.json",
        "claim_support.json",
        "source_safety_status.json",
        "build_manifest.json",
    ):
        (packet / name).write_bytes(canonical_json_bytes({"schema_version": "fixture-v1", "rows": []}))
    coverage = {
        name: {
            "schema_version": f"fixture-{name}-v1",
            "status": "fixture",
            "rows": [],
            "what_is_not_concluded": ["literature completeness"],
        }
        for name in COVERAGE_FILES
    }
    claim = semantic_item(
        queue_type="claim_candidate",
        source_id="claim-1",
        semantic_fields={"priority": "high", "status": "review_required"},
    )
    safety = semantic_item(
        queue_type="source_safety",
        source_id="paper-1",
        semantic_fields={"priority": "high", "status": "blocked_pending_evidence"},
    )
    omission = semantic_item(
        queue_type="omission_risk",
        source_id="risk-1",
        semantic_fields={"priority": "high", "status": "review_required"},
    )
    reason = "no reviewed supported technical claim rows are present"
    workflow = semantic_item(
        queue_type="workflow_blocker",
        source_id=workflow_blocker_source_id(reason),
        semantic_fields={
            "priority": "high",
            "status": "blocked_pending_evidence",
            "reason": reason,
            "resolution_class": "claim_review",
            "required_evidence_queue_type": "claim_candidate",
            "required_evidence_queue_item_ids": [claim["item_id"]],
            "ready_for_prose": False,
        },
    )
    items = sorted(
        [claim, safety, omission, workflow],
        key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]),
    )
    queue = {
        "status": "review_required",
        "topic": "M22 human attestation fixture",
        "items": items,
        "queue_counts": {
            "total": 4,
            "by_type": {decision_type: 1 for decision_type in DECISION_TYPES},
            "by_priority": {"high": 4},
            "by_status": {"blocked_pending_evidence": 2, "review_required": 2},
        },
        "allowed_item_statuses": ["review_required", "blocked_pending_evidence"],
        "forbidden_promotions": ["human-shaped metadata is not authentication"],
        "what_is_not_concluded": ["scientific correctness"],
    }
    selected = ArtifactStateManager(
        mission_root=mission_root,
        mission_id=committed.contract["mission_id"],
        mission_fingerprint=committed.contract["mission_fingerprint"],
        mission_anchor_generation_id=committed.current_pointer["generation_id"],
        nonce_factory=lambda: ARTIFACT_NONCE,
    ).compose_and_select(
        packet_dir=packet,
        coverage_payloads=coverage,
        review_queue_payload=queue,
    )
    return selected.review_queue_path, json.loads(selected.review_queue_path.read_text())


def _decision_paths(tmp_path: Path, queue_path: Path, queue: dict, *, reviewer: str = "Human Reviewer") -> dict[str, Path]:
    result: dict[str, Path] = {}
    queue_hash = hashlib.sha256(queue_path.read_bytes()).hexdigest()
    for decision_type in DECISION_TYPES:
        item = next(row for row in queue["items"] if row["queue_type"] == decision_type)
        path = tmp_path / "decisions" / f"{decision_type}.json"
        _write_json(path, {
            "schema_version": REVIEW_DECISIONS_SCHEMA,
            "decision_type": decision_type,
            "mission_id": queue["mission_id"],
            "mission_fingerprint": queue["mission_fingerprint"],
            "artifact_set_id": queue["artifact_set_id"],
            "queue_semantic_sha256": queue["queue_semantic_sha256"],
            "review_queue_sha256": queue_hash,
            "decisions": [{
                "queue_item_id": item["item_id"],
                "reviewer": reviewer,
                "reviewed_at": REVIEWED_AT,
            }],
        })
        result[decision_type] = path
    return result


def _completed_attestation(packet_dir: Path, *, display_name: str = "Human Reviewer") -> dict:
    template = json.loads((packet_dir / "human_attestation_template.json").read_text())
    template.update(status="completed_human_self_attestation", attested_at=ATTESTED_AT)
    template["reviewer"].update({
        "opaque_reviewer_id": "reviewer-local-001",
        "display_name": display_name,
        "authority_origin": "human_self_attested",
        "is_human": True,
        "roles": list(REVIEW_ROLES),
        "competence_statement": "I am competent to review the declared bounded evidence and will record uncertainty explicitly.",
        "conflict_status": "none_declared",
        "conflict_details": None,
        "privacy_notice_accepted": True,
        "privacy_retention_accepted": True,
    })
    template["declarations"] = {
        "decisions_are_my_own": True,
        "evidence_inspected": True,
        "limitations_understood": True,
        "model_output_is_not_human_judgment": True,
    }
    return template


def _valid_bundle(tmp_path: Path) -> tuple[Path, dict, Path, Path, dict[str, Path]]:
    queue_path, queue = _selected_queue(tmp_path)
    packet_dir = tmp_path / "human-packet"
    prepared = prepare_human_review_packet(
        review_queue_path=queue_path,
        output_dir=packet_dir,
        now=lambda: "2026-07-18T08:30:00Z",
    )
    assert prepared["status"] == "human_review_packet_prepared_unattested"
    attestation_path = tmp_path / "completed-attestation.json"
    _write_json(attestation_path, _completed_attestation(packet_dir))
    decisions = _decision_paths(tmp_path, queue_path, queue)
    return queue_path, queue, packet_dir, attestation_path, decisions


def test_prepare_packet_is_exact_and_explicitly_unattested(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    output = tmp_path / "packet"

    result = prepare_human_review_packet(
        review_queue_path=queue_path,
        output_dir=output,
        now=lambda: "2026-07-18T08:30:00Z",
    )

    packet = json.loads((output / "human_review_packet.json").read_text())
    template = json.loads((output / "human_attestation_template.json").read_text())
    assert result["human_attested"] is False
    assert result["ready_for_review_import"] is False
    assert packet["status"] == "human_review_required_unattested"
    assert packet["required_decision_types"] == list(DECISION_TYPES)
    assert {key: len(value) for key, value in packet["items_by_type"].items()} == {
        decision_type: 1 for decision_type in DECISION_TYPES
    }
    assert packet["mission_id"] == queue["mission_id"]
    assert template["status"] == "unattested_template"
    assert template["reviewer"]["is_human"] is None
    assert all(value is None for value in template["declarations"].values())

    guide = (output / "REVIEW_START_HERE.md").read_text()
    claim_rows = (output / "claim_review_worksheet.csv").read_text().splitlines()
    safety_rows = (output / "source_safety_worksheet.csv").read_text().splitlines()
    omission_rows = (output / "omission_review_worksheet.csv").read_text().splitlines()
    qualitative_rows = (output / "qualitative_assessment_worksheet.csv").read_text().splitlines()
    assert "machine-compatibility artifacts" in guide
    assert "system-generated qualitative assessment" in guide
    assert "not expected to fill 73 binary rows" in guide
    assert "Forward-citation coverage is permanently unavailable" in guide
    assert "The packet SHA-256 is" in guide
    assert hashlib.sha256((output / "human_review_packet.json").read_bytes()).hexdigest() in guide
    assert len(claim_rows) == 2
    assert len(safety_rows) == 2
    assert len(omission_rows) == 2
    assert len(qualitative_rows) >= 2
    assert "merits" in qualitative_rows[0]
    assert "concerns" in qualitative_rows[0]
    assert "uncertainties" in qualitative_rows[0]
    assert "evidence_refs" in qualitative_rows[0]
    assert "overstatement_probability" not in qualitative_rows[0]
    assert not (output / "scored_assessment_worksheet.csv").exists()
    assert (output / "workflow_blocker_worksheet.md").is_file()
    assert (output / "human_attestation_worksheet.md").is_file()


def test_render_materials_is_additive_and_preserves_packet_digest(tmp_path: Path) -> None:
    queue_path, _, packet_dir, _, _ = _valid_bundle(tmp_path)
    packet_path = packet_dir / "human_review_packet.json"
    before = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    output = tmp_path / "rendered"
    result = render_human_review_materials(packet_path=packet_path, output_dir=output)
    assert result["status"] == "human_review_materials_rendered"
    assert result["packet_sha256"] == before
    assert hashlib.sha256(packet_path.read_bytes()).hexdigest() == before
    assert (output / "REVIEW_START_HERE.md").is_file()
    assert queue_path.is_file()


def test_complete_self_attestation_binds_four_exact_files_and_replays(tmp_path: Path) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    output = tmp_path / "receipt"

    result = validate_human_attestation(
        review_queue_path=queue_path,
        packet_path=packet_dir / "human_review_packet.json",
        attestation_path=attestation_path,
        decision_paths=decisions,
        output_dir=output,
        now=lambda: "2026-07-18T10:30:00Z",
    )
    receipt = validate_human_attestation_receipt(output / "human_attestation_receipt.json")

    assert result["status"] == "human_self_attestation_validated"
    assert result["ready_for_review_import"] is True
    assert result["ready_for_reviewed_packet"] is False
    assert receipt["decision_coverage_complete"] is True
    assert [row["decision_type"] for row in receipt["decision_files"]] == list(DECISION_TYPES)
    assert receipt["decision_semantics_status"] == "deferred_to_existing_review_importers"
    assert receipt["reviewer"]["privacy_minimized"] is True


@pytest.mark.parametrize("identity", ["Codex", "Claude reviewer", "fixture-reviewer", "Automated Reviewer"])
def test_model_fixture_or_automation_identity_cannot_attest(tmp_path: Path, identity: str) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    attestation = json.loads(attestation_path.read_text())
    attestation["reviewer"]["display_name"] = identity
    _write_json(attestation_path, attestation)

    with pytest.raises(MissionStateError, match="cannot attest"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "receipt",
        )


def test_partial_stale_and_reviewer_mismatched_decisions_fail_closed(tmp_path: Path) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    partial = dict(decisions)
    partial.pop("workflow_blocker")
    with pytest.raises(MissionStateError, match="exactly four"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=partial,
            output_dir=tmp_path / "partial",
        )

    claim = json.loads(decisions["claim_candidate"].read_text())
    claim["review_queue_sha256"] = "0" * 64
    _write_json(decisions["claim_candidate"], claim)
    with pytest.raises(MissionStateError, match="queue hash differs"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "stale",
        )

    claim["review_queue_sha256"] = hashlib.sha256(queue_path.read_bytes()).hexdigest()
    claim["decisions"][0]["reviewer"] = "Different Human"
    _write_json(decisions["claim_candidate"], claim)
    with pytest.raises(MissionStateError, match="reviewer differs"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "mismatch",
        )


def test_privacy_conflict_and_fixture_decisions_fail_closed(tmp_path: Path) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    attestation = json.loads(attestation_path.read_text())
    attestation["reviewer"]["privacy_notice_accepted"] = False
    _write_json(attestation_path, attestation)
    with pytest.raises(MissionStateError, match="privacy"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "privacy",
        )

    attestation = _completed_attestation(packet_dir)
    attestation["reviewer"].update(conflict_status="disclosed", conflict_details="")
    _write_json(attestation_path, attestation)
    with pytest.raises(MissionStateError, match="must not be empty"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "conflict",
        )

    _write_json(attestation_path, _completed_attestation(packet_dir))
    omission = json.loads(decisions["omission_risk"].read_text())
    omission["decisions"][0]["fixture_only"] = True
    _write_json(decisions["omission_risk"], omission)
    with pytest.raises(MissionStateError, match="fixture-only"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "fixture",
        )


@pytest.mark.parametrize(
    ("decision_type", "field"),
    [
        ("claim_candidate", "review_status"),
        ("source_safety", "reviewer_authority"),
    ],
)
def test_model_advisory_decision_cannot_receive_human_receipt(
    tmp_path: Path,
    decision_type: str,
    field: str,
) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    payload = json.loads(decisions[decision_type].read_text())
    payload["decisions"][0][field] = "model_reviewed_advisory"
    _write_json(decisions[decision_type], payload)

    with pytest.raises(MissionStateError, match="model advisory"):
        validate_human_attestation(
            review_queue_path=queue_path,
            packet_path=packet_dir / "human_review_packet.json",
            attestation_path=attestation_path,
            decision_paths=decisions,
            output_dir=tmp_path / "model-advisory",
        )


def test_receipt_replay_rejects_bound_input_tampering(tmp_path: Path) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    output = tmp_path / "receipt"
    validate_human_attestation(
        review_queue_path=queue_path,
        packet_path=packet_dir / "human_review_packet.json",
        attestation_path=attestation_path,
        decision_paths=decisions,
        output_dir=output,
    )
    bound = output / "bound_inputs" / "claim_candidate_decisions.json"
    bound.write_bytes(bound.read_bytes() + b"\n")

    with pytest.raises(MissionStateError, match="differs from receipt"):
        validate_human_attestation_receipt(output / "human_attestation_receipt.json")


def test_receipt_replay_rejects_rehashed_false_human_declaration(tmp_path: Path) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    output = tmp_path / "receipt"
    validate_human_attestation(
        review_queue_path=queue_path,
        packet_path=packet_dir / "human_review_packet.json",
        attestation_path=attestation_path,
        decision_paths=decisions,
        output_dir=output,
    )
    attestation_bound = output / "bound_inputs" / "human_attestation.json"
    attestation = json.loads(attestation_bound.read_text())
    attestation["reviewer"]["is_human"] = False
    _write_json(attestation_bound, attestation)
    receipt_path = output / "human_attestation_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    raw = attestation_bound.read_bytes()
    bound_row = next(row for row in receipt["bound_inputs"] if row["name"] == "human_attestation.json")
    bound_row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    receipt["attestation_sha256"] = hashlib.sha256(raw).hexdigest()
    identity = {key: value for key, value in receipt.items() if key != "receipt_id"}
    receipt["receipt_id"] = "ha-" + hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    _write_json(receipt_path, receipt)

    with pytest.raises(MissionStateError, match="self-attest as human"):
        validate_human_attestation_receipt(receipt_path)


def test_embedded_receipt_archive_rejects_bound_input_tampering(tmp_path: Path) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    output = tmp_path / "receipt"
    validate_human_attestation(
        review_queue_path=queue_path,
        packet_path=packet_dir / "human_review_packet.json",
        attestation_path=attestation_path,
        decision_paths=decisions,
        output_dir=output,
    )
    archive = export_human_receipt_archive(output / "human_attestation_receipt.json")
    claim = next(
        row for row in archive["bound_inputs"]
        if row["name"] == "claim_candidate_decisions.json"
    )
    claim["base64"] = "e30K"

    with pytest.raises(MissionStateError, match="differs from receipt"):
        validate_human_receipt_archive(archive)


def test_cli_prepares_nonattesting_packet(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    queue_path, _ = _selected_queue(tmp_path)
    output = tmp_path / "cli-packet"

    code = main([
        "survey",
        "prepare-human-review",
        "--review-queue",
        str(queue_path),
        "--out",
        str(output),
    ])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "human_review_packet_prepared_unattested"
    assert (output / "human_attestation_template.json").is_file()


def test_cli_invalid_attestation_returns_structured_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    queue_path, _, packet_dir, attestation_path, decisions = _valid_bundle(tmp_path)
    attestation = json.loads(attestation_path.read_text())
    attestation["reviewer"]["is_human"] = False
    _write_json(attestation_path, attestation)

    code = main([
        "survey",
        "validate-human-attestation",
        "--review-queue", str(queue_path),
        "--packet", str(packet_dir / "human_review_packet.json"),
        "--attestation", str(attestation_path),
        "--claim-decisions", str(decisions["claim_candidate"]),
        "--source-safety-decisions", str(decisions["source_safety"]),
        "--omission-decisions", str(decisions["omission_risk"]),
        "--workflow-blocker-decisions", str(decisions["workflow_blocker"]),
        "--out", str(tmp_path / "blocked-receipt"),
    ])

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "nonhuman_reviewer_authority"
    assert payload["ready_for_review_import"] is False
