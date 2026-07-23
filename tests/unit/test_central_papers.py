from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from research_assistant.survey.central_papers import (
    DEFAULT_BUDGET,
    run_central_papers_campaign,
    validate_central_papers_campaign,
)
from research_assistant.survey.central_papers_capability import OBSERVATION_SCHEMA
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, sha256_bytes
from research_assistant.survey.topic_contract import topic_contract_sha256


def _candidate(paper_id: str, *, off_topic: bool = False, blocked: bool = False) -> dict:
    topic_text = "image particle effects" if off_topic else "generic topic method"
    sections = [] if blocked else [{
        "anchor_id": "section:method",
        "title": "Method",
        "text": f"We propose an algorithm for {topic_text}.",
        "evidence_ref": f"source:{paper_id}:method",
    }]
    return {
        "paper_id": paper_id,
        "title": "A Generic Topic Method" if not blocked else "A Generic Topic Benchmark",
        "authors": ["Author, A"],
        "year": 2020,
        "identifiers": {"arxiv_id": None, "doi": None, "openalex_id": None},
        "identity_status": "resolved",
        "discovery_round": 0,
        "discovery_routes": ["broad_facets"],
        "discovery_origins": [],
        "citation_count": 100_000 if off_topic else 1,
        "venue_metric_status": "not_available",
        "source": {
            "status": "source_blocked" if blocked else "available",
            "source_type": "fixture",
            "evidence_ref": f"source:{paper_id}",
            "sections": sections,
            "bibliography": [],
        },
        "safety": {
            "status": "not_checked" if blocked else "no_issue_found",
            "evidence_refs": [] if blocked else [f"safety:{paper_id}"],
            "limitations": ["fixture safety scope"],
        },
        "forward_citation_status": "not_available" if blocked else "available",
        "forward_citations": [] if blocked else [f"citing:{paper_id}"],
        "limitations": ["fixture observation"],
    }


@dataclass
class CountingCapability:
    rows: list[dict]
    calls: int = 0
    name: str = "counting_fixture"
    network_required: bool = False

    @property
    def fingerprint(self) -> str:
        return sha256_bytes(canonical_json_bytes({"name": self.name, "rows": self.rows}))

    def collect(self, topic_contract: dict, budget: dict[str, int]) -> dict:
        del budget
        self.calls += 1
        return {
            "schema_version": OBSERVATION_SCHEMA,
            "topic_contract_sha256": topic_contract_sha256(topic_contract),
            "capability_fingerprint": self.fingerprint,
            "accessed_at": "2026-07-22T00:00:00+00:00",
            "discovery_status": "available" if self.rows else "empty",
            "provider_statuses": [{"provider": "fixture", "status": "available" if self.rows else "empty", "detail": "fixture"}],
            "candidates": self.rows,
            "budget_consumption": {"metadata_records": len(self.rows), "metadata_requests": 1, "source_attempts": 0, "source_bytes": 0},
            "limitations": ["offline fixture capability"],
            "benchmark_labels_consumed": False,
        }


def test_campaign_writes_six_ledgers_replays_and_resume_does_not_recollect(tmp_path: Path) -> None:
    capability = CountingCapability([_candidate("direct")])
    root = tmp_path / "campaign"
    report = run_central_papers_campaign(topic="Generic topic", output_dir=root, capability=capability)
    assert capability.calls == 1
    assert report["dispositions"] == {"VALIDATED_CENTRAL": ["direct"]}
    assert len(list((root / "ledgers").glob("*.json"))) == 6
    assert validate_central_papers_campaign(root, expected_topic="Generic topic")["report"] == report
    replay = run_central_papers_campaign(
        topic="Generic topic", output_dir=root, capability=capability, resume=True
    )
    assert replay == report
    assert capability.calls == 1


def test_campaign_rejects_famous_inspected_off_topic_control(tmp_path: Path) -> None:
    capability = CountingCapability([_candidate("off-topic", off_topic=True)])
    report = run_central_papers_campaign(
        topic="Generic topic", output_dir=tmp_path / "campaign", capability=capability
    )
    assert report["dispositions"] == {"REJECTED_OFF_TOPIC": ["off-topic"]}


def test_introduction_only_claim_does_not_become_inspected_topic_fit(tmp_path: Path) -> None:
    candidate = _candidate("introduction-only")
    candidate["source"]["sections"][0].update({
        "anchor_id": "section:introduction",
        "title": "Introduction",
        "text": "We propose a method for the generic topic.",
    })
    report = run_central_papers_campaign(
        topic="Generic topic",
        output_dir=tmp_path / "introduction-only",
        capability=CountingCapability([candidate]),
    )
    assert report["dispositions"] == {"BLOCKED": ["introduction-only"]}


def test_campaign_preserves_source_block_and_empty_discovery(tmp_path: Path) -> None:
    blocked = CountingCapability([_candidate("blocked", blocked=True)])
    report = run_central_papers_campaign(
        topic="Generic topic", output_dir=tmp_path / "blocked", capability=blocked
    )
    assert report["dispositions"] == {"BLOCKED": ["blocked"]}

    empty = CountingCapability([])
    report = run_central_papers_campaign(
        topic="Generic topic", output_dir=tmp_path / "empty", capability=empty
    )
    assert report["dispositions"] == {}
    assert report["stop_reason"] == "discovery_empty"


def test_campaign_fails_closed_on_tamper_resume_mismatch_and_budget(tmp_path: Path) -> None:
    capability = CountingCapability([_candidate("direct")])
    root = tmp_path / "campaign"
    run_central_papers_campaign(topic="Generic topic", output_dir=root, capability=capability)
    assessment = json.loads((root / "centrality_assessment.json").read_text())
    assessment["status"] = "tampered"
    (root / "centrality_assessment.json").write_text(json.dumps(assessment))
    with pytest.raises(MissionStateError, match="artifact binding differs"):
        validate_central_papers_campaign(root)
    with pytest.raises(MissionStateError, match="resume topic"):
        run_central_papers_campaign(
            topic="Another topic", output_dir=root, capability=capability, resume=True
        )

    checkpoint_root = tmp_path / "checkpoint-tamper"
    run_central_papers_campaign(
        topic="Generic topic", output_dir=checkpoint_root, capability=capability
    )
    checkpoint_path = checkpoint_root / "rounds" / "round-000.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    checkpoint["stop_candidate"] = "tampered"
    checkpoint_path.write_text(json.dumps(checkpoint))
    with pytest.raises(MissionStateError, match="terminal artifact binding differs|evidence construction manifest differs|checkpoint"):
        validate_central_papers_campaign(checkpoint_root)

    small_budget = dict(DEFAULT_BUDGET)
    small_budget["max_candidates"] = 1
    too_many = CountingCapability([_candidate("one"), _candidate("two")])
    with pytest.raises(MissionStateError, match="candidate budget"):
        run_central_papers_campaign(
            topic="Generic topic",
            output_dir=tmp_path / "budget",
            capability=too_many,
            budget=small_budget,
        )


def test_live_capability_requires_explicit_confirmation(tmp_path: Path) -> None:
    with pytest.raises(MissionStateError, match="requires explicit confirmation"):
        run_central_papers_campaign(topic="Generic topic", output_dir=tmp_path / "live")
