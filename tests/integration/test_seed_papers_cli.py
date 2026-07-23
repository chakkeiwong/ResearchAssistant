from __future__ import annotations

import json
from pathlib import Path

from research_assistant import cli
from research_assistant.survey.seed_paper_providers import PROVIDER_BUNDLE_SCHEMA
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


def _bundle(topic: str) -> dict:
    doi = "10.5555/causal-iv"
    crossref_response = {
        "message": {
            "total-results": 1,
            "items": [{
                "DOI": doi,
                "title": ["Causal Inference with Instrumental Variables"],
                "author": [{"given": "Ada", "family": "Scholar"}],
                "published": {"date-parts": [[2020]]},
                "is-referenced-by-count": 42,
                "container-title": ["Methods"],
                "URL": f"https://doi.org/{doi}",
            }],
        }
    }
    unavailable = lambda provider: {
        "provider": provider,
        "status": "not_available",
        "requests": [{
            "route_id": "exact_high_citation",
            "purpose": "foundational_or_high_citation",
            "query": topic,
            "status": "not_available",
            "capped": False,
            "provider_total": None,
            "request_url": f"https://example.test/{provider}",
            "response": None,
            "detail": "fixture unavailable",
        }],
    }
    return {
        "schema_version": PROVIDER_BUNDLE_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(build_topic_contract(topic)),
        "accessed_at": "2026-07-22T00:00:00+00:00",
        "providers": [
            {
                "provider": "crossref",
                "status": "available",
                "requests": [{
                    "route_id": "exact_high_citation",
                    "purpose": "foundational_or_high_citation",
                    "query": topic,
                    "status": "available",
                    "capped": False,
                    "provider_total": 1,
                    "request_url": "https://example.test/crossref",
                    "response": crossref_response,
                    "detail": None,
                }],
            },
            unavailable("openalex"),
            unavailable("semantic_scholar"),
        ],
        "benchmark_labels_consumed": False,
    }


def test_seed_papers_cli_runs_offline_and_resumes(tmp_path: Path, capsys) -> None:
    topic = "Causal inference with instrumental variables"
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(_bundle(topic)), encoding="utf-8")
    output = tmp_path / "campaign"
    command = [
        "survey", "seed-papers", "--topic", topic, "--out", str(output),
        "--observation-bundle", str(bundle),
    ]
    assert cli.main(command) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["selected_paper_ids"] == ["doi:10.5555/causal-iv"]
    assert report["metadata_can_establish_centrality"] is False
    assert (output / "seed_manifest.json").is_file()

    assert cli.main([
        "survey", "seed-papers", "--topic", topic, "--out", str(output), "--resume",
    ]) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay == report
