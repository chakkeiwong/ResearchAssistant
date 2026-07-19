from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.artifact_lineage import validate_selected_review_queue
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.human_attestation import prepare_human_review_packet
from research_assistant.survey.m22_retained_reconciliation import compose_retained_production_mission
from research_assistant.survey.mission_state import MissionStateError


def _selected_queue(root: Path) -> tuple[Path, dict]:
    selected = compose_retained_production_mission(output_dir=root / "mission")
    queue = json.loads(selected.review_queue_path.read_text())
    return selected.review_queue_path, queue


def test_retained_reconciliation_preserves_accounting_and_prepares_unattested_packet(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    assert queue["schema_version"] == "ra-survey-public-source-review-queue-v2"
    assert queue["queue_counts"]["total"] == 73
    assert queue["queue_counts"]["by_type"] == {
        "claim_candidate": 7,
        "omission_risk": 58,
        "source_safety": 7,
        "workflow_blocker": 1,
    }
    coverage = queue_path.parent / "coverage"
    omitted = json.loads((coverage / "omitted_paper_risks.json").read_text())
    assert omitted["risk_reconciliation"] == {
        "candidate_count": 62,
        "identifier_free_units": 195,
        "nominated_count": 7,
        "parsed_source_count": 7,
        "anchor_count": 341,
    }
    forward = json.loads((coverage / "forward_snowball.json").read_text())
    assert forward["status"] == "unavailable_out_of_scope"
    assert forward["blocking"] is False
    assert len(json.loads((queue_path.parent.parent.parent.parent / "retained_evidence/anchor_inventory.json").read_text())["anchors"]) == 341
    source_root = queue_path.parent.parent.parent.parent / "retained_evidence" / "sources"
    source_records = [json.loads(path.read_text()) for path in source_root.glob("*.json")]
    assert source_records
    assert all(not Path(row["original_record_path"]).is_absolute() for row in source_records)
    seed = next(
        row for row in source_records if row["canonical_identifier"] == "arxiv:2201.12220v3"
    )
    assert seed["original_record_path"].endswith(
        "retained_evidence/sources/2201_12220v3.json"
    )
    packet = prepare_human_review_packet(review_queue_path=queue_path, output_dir=tmp_path / "packet")
    assert packet["status"] == "human_review_packet_prepared_unattested"
    assert packet["human_attested"] is False
    assert packet["ready_for_review_import"] is False


def test_retained_context_preserves_parse_gap_and_source_identities(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    context = load_v2_evidence_context(queue_path)
    assert len(context.source_identities) == 7
    assert len(context.unavailable_outcomes) == 1
    assert context.unavailable_outcomes[0]["candidate_id"] == "1412.6980"
    assert context.unavailable_outcomes[0]["code"] == "source_format_parse_gap"
    assert all(identity.source_record_path.startswith("retained_evidence/sources/") for identity in context.source_identities.values())
    assert all(identity.source_version.startswith("record-sha256:") for identity in context.source_identities.values())


def test_retained_queue_replay_rejects_tampered_accounting(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    selected = validate_selected_review_queue(queue_path)
    coverage_path = selected.coverage_dir / "omitted_paper_risks.json"
    payload = json.loads(coverage_path.read_text())
    payload["risk_reconciliation"]["identifier_free_units"] = 194
    coverage_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(MissionStateError):
        validate_selected_review_queue(queue_path)
