from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey import m21_candidate_context_triage as triage


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000/"
    "candidate_classifications.json"
)
EVIDENCE = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000/"
    "combined_evidence.json"
)
SOURCE = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000/"
    "accepted_bodies/arxiv-source.body"
)
RECORD = REPOSITORY_ROOT / (
    "local_research/papers/source/records/paper_arxiv_2201_1a5af737.json"
)


def _build() -> dict[str, dict]:
    return triage.build_candidate_context_triage(
        candidate_path=CANDIDATES,
        evidence_path=EVIDENCE,
        structured_record_path=RECORD,
        retained_source_path=SOURCE,
    )


def test_real_inputs_have_exact_accounting_and_nonpromotion() -> None:
    outputs = _build()
    result = outputs["candidate_context_triage.json"]
    rows = result["rows"]

    assert result["candidate_count"] == len(rows) == 62
    assert len({row["candidate_id"] for row in rows}) == 62
    assert sum(result["state_counts"].values()) == 62
    assert all(row["scholarly_classification"] == "NOT_CHECKED" for row in rows)
    assert all(row["support_status"] == "SOURCE_GAP_BLOCKER" for row in rows)
    assert all(row["heuristic_only"] is True for row in rows)
    assert all("raw" not in key for row in rows for key in row)


def test_locations_are_bounded_source_pointers_without_raw_context() -> None:
    rows = _build()["candidate_context_triage.json"]["rows"]
    locations = [location for row in rows for location in row["citation_locations"]]

    assert locations
    assert all(location["line"] > 0 for location in locations)
    assert all(
        set(location)
        == {
            "line",
            "citation_command",
            "section_title",
            "section_labels",
            "context_role_signals",
            "matched_signal_tokens",
        }
        for location in locations
    )


def test_selection_is_bounded_stratified_and_accounts_for_every_candidate() -> None:
    outputs = _build()
    triage_rows = outputs["candidate_context_triage.json"]["rows"]
    selection = outputs["primary_source_selection.json"]
    rows = selection["selection_rows"]

    assert 0 < selection["nomination_count"] <= 12
    assert len(rows) == 62
    assert {row["candidate_id"] for row in rows} == {
        row["candidate_id"] for row in triage_rows
    }
    assert all(row["reasons"] for row in rows)
    assert all(row["scholarly_classification"] == "NOT_CHECKED" for row in rows)
    assert all(row["support_status"] == "SOURCE_GAP_BLOCKER" for row in rows)
    observed_states = {
        row["heuristic_context_state"] for row in triage_rows
    }
    nominated_states = {
        row["heuristic_context_state"]
        for row in rows
        if row["nomination_status"] == "NOMINATED_FOR_PRIMARY_SOURCE_INSPECTION"
    }
    assert observed_states - {triage.NOT_LOCATED} <= nominated_states
    assert all(
        row["citation_occurrence_count"] > 0
        for row in rows
        if row["nomination_status"] == "NOMINATED_FOR_PRIMARY_SOURCE_INSPECTION"
    )
    assert all(
        row["nomination_status"] == "DEFERRED_RETAINED_AS_OMISSION_RISK"
        for row in rows
        if row["heuristic_context_state"] == triage.NOT_LOCATED
    )


def test_real_join_exposes_unused_identifier_bearing_bibliography_entries() -> None:
    outputs = _build()
    result = outputs["candidate_context_triage.json"]
    selection = outputs["primary_source_selection.json"]

    assert result["state_counts"][triage.NOT_LOCATED] == 55
    assert sum(
        row["citation_occurrence_count"] > 0 for row in result["rows"]
    ) == 7
    assert selection["nomination_count"] == 7


def test_identifier_free_and_forward_limitations_remain_explicit() -> None:
    risk = _build()["identifier_free_risk.json"]

    assert risk["identifier_free_bibliography_units"] == 195
    assert risk["forward_coverage_status"] == "unavailable_out_of_scope"
    assert risk["forward_coverage_blocking"] is False
    assert "zero_forward_citations" in risk["nonclaims"]


def test_build_is_deterministic() -> None:
    assert _build() == _build()


def test_rejects_duplicate_candidate_identity(tmp_path: Path) -> None:
    payload = json.loads(CANDIDATES.read_text())
    payload["rows"][1]["candidate_id"] = payload["rows"][0]["candidate_id"]
    candidate_path = tmp_path / "candidates.json"
    candidate_path.write_text(json.dumps(payload))

    with pytest.raises(triage.M21CandidateContextError, match="candidate_row_invalid"):
        triage.build_candidate_context_triage(
            candidate_path=candidate_path,
            evidence_path=EVIDENCE,
            structured_record_path=RECORD,
            retained_source_path=SOURCE,
        )


def test_rejects_source_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source.body"
    source.write_bytes(b"tampered")

    with pytest.raises(triage.M21CandidateContextError, match="source_hash_mismatch"):
        triage.build_candidate_context_triage(
            candidate_path=CANDIDATES,
            evidence_path=EVIDENCE,
            structured_record_path=RECORD,
            retained_source_path=source,
        )


def test_writer_uses_fresh_root_and_inventory_replays(tmp_path: Path) -> None:
    root = tmp_path / "fresh"
    result = triage.write_candidate_context_triage(
        candidate_path=CANDIDATES,
        evidence_path=EVIDENCE,
        structured_record_path=RECORD,
        retained_source_path=SOURCE,
        output_root=root,
    )

    assert result["status"] == "passed"
    assert result["candidate_count"] == 62
    manifest = json.loads((root / "run_manifest.json").read_text())
    assert manifest["network_used"] is False
    assert manifest["credential_interface"] is False
    inventory = json.loads((root / "artifact_inventory.json").read_text())
    assert len(inventory["files"]) == 4
    for row in inventory["files"]:
        path = root / row["relative_path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]

    with pytest.raises(triage.M21CandidateContextError, match="output_root_not_fresh"):
        triage.write_candidate_context_triage(
            candidate_path=CANDIDATES,
            evidence_path=EVIDENCE,
            structured_record_path=RECORD,
            retained_source_path=SOURCE,
            output_root=root,
        )


def test_nomination_cap_is_fail_closed() -> None:
    with pytest.raises(triage.M21CandidateContextError, match="nomination_cap_invalid"):
        triage.build_candidate_context_triage(
            candidate_path=CANDIDATES,
            evidence_path=EVIDENCE,
            structured_record_path=RECORD,
            retained_source_path=SOURCE,
            max_nominations=13,
        )
