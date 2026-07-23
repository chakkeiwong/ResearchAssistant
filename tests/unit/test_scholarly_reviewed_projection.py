from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey.document.contracts import DocumentInputError, load_contract, load_evidence
from research_assistant.survey.document.projection import project_reviewed_packet


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _packet() -> dict:
    return {
        "schema_version": "ra-survey-reviewed-final-packet-v2",
        "mission_id": "mission-1",
        "readiness_inputs": {"ready_for_hostile_review": True},
        "review_queue": {"topic": "Generic reviewed topic"},
        "original_packet": {
            "candidate_ledger": {
                "included": [{"paper_id": "paper-a", "title": "Reviewed Method"}]
            }
        },
        "reviewed_sections": {
            "claims": [{
                "claim_id": "claim-a",
                "claim_text": "The reviewed method uses an explicit constrained update.",
                "claim_type": "paper_technical",
                "support_class": "primary_technical_support",
                "claim_support_allowed": True,
                "decision_sha256": "1" * 64,
                "paper_ids": ["paper-a"],
                "anchor_ids": ["anchor-a"],
            }],
            "omission_risks": [],
        },
        "evidence_classifications": [{
            "claim_id": "claim-a",
            "decision_sha256": "1" * 64,
            "support_class": "primary_technical_support",
            "paper_ids": ["paper-a"],
            "anchor_ids": ["anchor-a"],
            "bound_anchors": [{"anchor_id": "anchor-a", "paper_id": "paper-a"}],
        }],
        "what_is_not_concluded": ["literature completeness", "publication readiness"],
    }


def test_reviewed_projection_requires_exact_hostile_pass(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    hostile_path = tmp_path / "hostile.json"
    _write(packet_path, _packet())
    hostile = {
        "schema_version": "ra-survey-hostile-review-v2",
        "status": "ready_for_reviewed_prose_within_recorded_scope",
        "ready_for_prose": True,
        "blocker_count": 0,
        "reviewed_final_packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
    }
    _write(hostile_path, hostile)
    result = project_reviewed_packet(
        packet_path=packet_path,
        hostile_review_path=hostile_path,
        output_dir=tmp_path / "projection",
    )
    contract = load_contract(Path(result["contract_path"]))
    evidence = load_evidence(Path(result["evidence_path"]), contract)
    assert evidence.authority_class == "reviewed_primary"
    assert evidence.claims[0].support_class == "PRIMARY_TECHNICAL_SUPPORT"


def test_reviewed_projection_rejects_blocked_or_stale_hostile_result(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    hostile_path = tmp_path / "hostile.json"
    _write(packet_path, _packet())
    _write(hostile_path, {
        "schema_version": "ra-survey-hostile-review-v2",
        "status": "blocked_for_reviewed_prose",
        "ready_for_prose": False,
        "blocker_count": 1,
        "reviewed_final_packet_sha256": "0" * 64,
    })
    with pytest.raises(DocumentInputError, match="does not authorize"):
        project_reviewed_packet(
            packet_path=packet_path,
            hostile_review_path=hostile_path,
            output_dir=tmp_path / "projection",
        )
