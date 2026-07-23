from __future__ import annotations

import json
from pathlib import Path

from research_assistant import cli
from research_assistant.survey.central_papers_capability import OBSERVATION_SCHEMA
from research_assistant.survey.mission_state import canonical_json_bytes, pretty_json_bytes, sha256_bytes
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


def _bundle(path: Path, topic: str) -> None:
    contract = build_topic_contract(topic)
    value = {
        "schema_version": OBSERVATION_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(contract),
        "capability_fingerprint": "0" * 64,
        "accessed_at": "2026-07-22T00:00:00+00:00",
        "discovery_status": "available",
        "provider_statuses": [{"provider": "fixture", "status": "available", "detail": "offline"}],
        "candidates": [{
            "paper_id": "fixture:direct",
            "title": "Generic Topic Algorithm",
            "authors": ["Author, A"],
            "year": 2024,
            "identifiers": {"arxiv_id": None, "doi": None, "openalex_id": None},
            "identity_status": "resolved",
            "discovery_round": 0,
            "discovery_routes": ["broad_facets"],
            "discovery_origins": [],
            "citation_count": 1,
            "venue_metric_status": "not_available",
            "source": {
                "status": "available",
                "source_type": "fixture_structured_source",
                "evidence_ref": "source:fixture:direct",
                "sections": [{
                    "anchor_id": "section:method",
                    "title": "Method",
                    "text": "We propose an algorithm for the generic topic.",
                    "evidence_ref": "source:fixture:direct:method",
                }],
                "bibliography": [],
            },
            "safety": {
                "status": "no_issue_found",
                "evidence_refs": ["safety:fixture:direct"],
                "limitations": ["fixture check only"],
            },
            "forward_citation_status": "available",
            "forward_citations": ["fixture:citing"],
            "limitations": ["offline fixture"],
        }],
        "budget_consumption": {"metadata_records": 1, "metadata_requests": 1, "source_attempts": 0, "source_bytes": 0},
        "limitations": ["offline fixture capability"],
        "benchmark_labels_consumed": False,
    }
    path.write_bytes(pretty_json_bytes(value))
    value["capability_fingerprint"] = sha256_bytes(path.resolve().read_bytes())
    path.write_bytes(pretty_json_bytes(value))


def test_central_papers_cli_runs_topic_only_offline_campaign(tmp_path: Path, capsys) -> None:
    topic = "Generic topic"
    bundle = tmp_path / "observations.json"
    output = tmp_path / "campaign"
    _bundle(bundle, topic)
    assert cli.main([
        "survey", "central-papers", "--topic", topic, "--out", str(output),
        "--observation-bundle", str(bundle),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["dispositions"] == {"VALIDATED_CENTRAL": ["fixture:direct"]}
    assert printed["benchmark_labels_consumed"] is False
    assert (output / "campaign_manifest.json").is_file()
