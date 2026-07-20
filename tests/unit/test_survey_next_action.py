from __future__ import annotations

from pathlib import Path

import pytest

from research_assistant.survey import orchestrate
from research_assistant.survey.next_action import (
    build_next_action,
    reviewed_evidence_blocker_commands,
)


FIXED_TIME = "2026-07-20T00:00:00+00:00"


def _status(path: str, *, exists: bool = True, **values) -> dict:
    return {"required_path": path, "exists": exists, **values}


def _direct_next_action(**overrides):
    values = {
        "gate": {
            "gate_id": "public_metadata",
            "status": "confirmation_required",
            "approval_required": True,
            "required_artifact": "public_metadata",
        },
        "output_dir": Path("/tmp/mission"),
        "topic": "Neural Optimal Transport",
        "seeds": ["arxiv:2201.12220v3"],
        "packet_dir": Path("/tmp/mission/packet"),
        "review_queue": None,
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "anchor_dir": None,
        "local_evidence_root": None,
        "public_discovery_confirmation": {"confirmed": False},
        "artifact_initialization_required": False,
        "created_at": FIXED_TIME,
        "schema_version": orchestrate.SURVEY_NEXT_ACTION_SCHEMA_VERSION,
        "nonclaims": orchestrate.ORCHESTRATION_NONCLAIMS,
        "public_discovery_max_metadata_records": orchestrate.PUBLIC_DISCOVERY_MAX_METADATA_RECORDS,
    }
    values.update(overrides)
    return build_next_action(**values)


def test_orchestration_wrapper_matches_pure_builder(monkeypatch) -> None:
    monkeypatch.setattr(orchestrate, "_utc_now_iso", lambda: FIXED_TIME)
    kwargs = {
        "gate": {
            "gate_id": "public_metadata",
            "status": "confirmation_required",
            "approval_required": True,
            "required_artifact": "public_metadata",
        },
        "output_dir": Path("/tmp/mission"),
        "topic": "Neural Optimal Transport",
        "seeds": ["arxiv:2201.12220v3"],
        "packet_dir": Path("/tmp/mission/packet"),
        "review_queue": None,
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "anchor_dir": None,
        "local_evidence_root": None,
        "public_discovery_confirmation": {"confirmed": False},
    }

    wrapped = orchestrate._next_action(**kwargs)
    direct = _direct_next_action(**kwargs)

    assert wrapped == direct
    assert wrapped["created_at"] == FIXED_TIME
    assert wrapped["action_id"] == "public_metadata"
    assert "--public-metadata-provider arxiv" in wrapped["safe_next_commands"][0]
    assert "openalex" not in wrapped["safe_next_commands"][0].casefold()


def test_review_progression_stops_at_first_incomplete_authority() -> None:
    reviewed = {
        "reviewed_claims": _status("claims.json", exists=True, decision_coverage_complete=True),
        "reviewed_source_safety": _status("source.json", exists=False),
        "reviewed_omissions": _status("omissions.json", exists=False),
        "reviewed_workflow_blockers": _status("workflow.json", exists=False),
        "reviewed_evidence": _status("merged.json", exists=False),
    }
    result = _direct_next_action(
        gate={
            "gate_id": "claim_safety_omission_review",
            "status": "review_required",
            "approval_required": False,
            "required_artifact": "review_queue.json",
        },
        review_queue={"path": "review_queue.json"},
        reviewed_artifacts=reviewed,
        coverage_artifacts={"coverage": _status("coverage.json")},
    )

    assert result["action_id"] == "import_reviewed_source_safety"
    assert result["status"] == "blocked_pending_reviewed_source_safety"
    assert result["required_artifacts"] == ["source.json"]


def test_merge_repair_command_always_binds_workflow_blockers() -> None:
    commands = reviewed_evidence_blocker_commands(
        blockers=["workflow blocker remains open"],
        review_queue_path="review_queue.json",
        output_dir=Path("/tmp/mission"),
        claims_path="claims.json",
        source_safety_path="source.json",
        omissions_path="omissions.json",
        workflow_blockers_path="workflow.json",
    )

    assert commands[-1].count("--reviewed-workflow-blockers workflow.json") == 1
    assert commands[-1].endswith("--out /tmp/mission/reviewed_evidence --force")


def test_artifact_initialization_precedes_review_queue_requirements() -> None:
    result = _direct_next_action(
        gate={
            "gate_id": "claim_safety_omission_review",
            "status": "review_required",
            "approval_required": False,
            "required_artifact": "review_queue.json",
        },
        artifact_initialization_required=True,
    )

    assert result["action_id"] == "resume_to_initialize_artifact_state"
    assert result["mission_status"] == "ready_for_local_continuation"
    assert result["required_artifacts"] == [".artifact_state/GENESIS", ".artifact_state/CURRENT"]


@pytest.mark.parametrize(
    ("incomplete_name", "expected_action", "expected_command"),
    [
        (
            "reviewed_claims",
            "import_reviewed_claims",
            "review claim_candidates, then run: ra survey import-claim-review --review-queue review_queue.json --decisions <reviewed_claim_decisions.json> --out /tmp/mission/reviewed_claims",
        ),
        (
            "reviewed_source_safety",
            "import_reviewed_source_safety",
            "ra survey import-source-safety-review --review-queue review_queue.json --decisions <reviewed_source_safety_decisions.json> --out /tmp/mission/reviewed_source_safety",
        ),
        (
            "reviewed_omissions",
            "import_reviewed_omissions",
            "ra survey import-omission-review --review-queue review_queue.json --decisions <reviewed_omission_decisions.json> --out /tmp/mission/reviewed_omissions",
        ),
        (
            "reviewed_workflow_blockers",
            "import_reviewed_workflow_blockers",
            "ra survey import-workflow-blocker-review --review-queue review_queue.json --decisions <reviewed_workflow_blocker_decisions.json> --out /tmp/mission/reviewed_workflow_blockers",
        ),
    ],
)
def test_review_import_steps_preserve_order_and_exact_commands(
    incomplete_name: str,
    expected_action: str,
    expected_command: str,
) -> None:
    artifact_names = (
        "reviewed_claims",
        "reviewed_source_safety",
        "reviewed_omissions",
        "reviewed_workflow_blockers",
    )
    reviewed = {
        name: _status(f"{name}.json", exists=True, decision_coverage_complete=True)
        for name in artifact_names
    }
    reviewed[incomplete_name]["decision_coverage_complete"] = False
    reviewed["reviewed_evidence"] = _status("merged.json", exists=False)

    result = _direct_next_action(
        gate={
            "gate_id": "claim_safety_omission_review",
            "status": "review_required",
            "approval_required": False,
            "required_artifact": "review_queue.json",
        },
        review_queue={"path": "review_queue.json"},
        reviewed_artifacts=reviewed,
        coverage_artifacts={"coverage": _status("coverage.json")},
    )

    assert result["action_id"] == expected_action
    assert result["safe_next_commands"] == [expected_command]
    assert result["required_artifacts"] == [f"{incomplete_name}.json"]


@pytest.mark.parametrize(
    ("packet", "hostile", "readiness", "expected_action"),
    [
        (
            _status("packet.json", exists=False, present=False),
            _status("hostile.json", exists=False, present=False),
            _status("readiness.json", exists=False, present=False),
            "compose_reviewed_final_packet",
        ),
        (
            _status("packet.json", exists=True, present=True),
            _status("hostile.json", exists=False, present=False),
            _status("readiness.json", exists=False, present=False),
            "run_hostile_review",
        ),
        (
            _status("packet.json", exists=True, present=True),
            _status(
                "hostile.json",
                exists=True,
                present=True,
                ready_for_prose=True,
                readiness_classification="READY",
            ),
            _status("readiness.json", exists=True, present=True),
            "phase5_executing_supervisor_handoff",
        ),
    ],
)
def test_final_review_progression_is_explicit(
    packet: dict,
    hostile: dict,
    readiness: dict,
    expected_action: str,
) -> None:
    reviewed = {
        "reviewed_claims": _status("claims.json", decision_coverage_complete=True),
        "reviewed_source_safety": _status("source.json", decision_coverage_complete=True),
        "reviewed_omissions": _status("omissions.json", decision_coverage_complete=True),
        "reviewed_workflow_blockers": _status("workflow.json", decision_coverage_complete=True),
        "reviewed_evidence": _status("merged.json", ready_for_reviewed_packet=True, blockers=[]),
    }

    result = _direct_next_action(
        gate={
            "gate_id": "claim_safety_omission_review",
            "status": "review_required",
            "approval_required": False,
            "required_artifact": "review_queue.json",
        },
        review_queue={"path": "review_queue.json"},
        reviewed_artifacts=reviewed,
        coverage_artifacts={"coverage": _status("coverage.json")},
        final_artifacts={
            "reviewed_final_packet": packet,
            "hostile_review_result": hostile,
            "final_packet_readiness": readiness,
        },
        anchor_dir=Path("/tmp/mission/anchors"),
    )

    assert result["action_id"] == expected_action
