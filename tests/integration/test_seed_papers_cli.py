from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant import cli
from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.seed_paper_providers import (
    PROVIDER_BUNDLE_SCHEMA,
    PROVIDER_BUNDLE_SCHEMA_V2,
)
from research_assistant.survey.seed_papers import (
    SEED_CAMPAIGN_SCHEMA_V3,
    SEED_MANIFEST_SCHEMA_V3,
    SEED_REPORT_SCHEMA_V3,
    validate_seed_paper_campaign,
)
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


def _bundle_v2(topic: str, *, seed: str, include_seed: bool = True) -> dict:
    doi = seed.removeprefix("doi:")
    exact_response = {
        "message": {
            "DOI": doi,
            "title": ["Deep learning for solving dynamic economic models"],
            "author": [{"given": "Lilia", "family": "Maliar"}],
            "published": {"date-parts": [[2021]]},
            "is-referenced-by-count": 100,
            "container-title": ["Journal of Monetary Economics"],
            "URL": f"https://doi.org/{doi}",
        }
    }

    def failed(provider: str) -> dict:
        return {
            "provider": provider,
            "status": "http_failed",
            "requests": [{
                "route_id": "seed_doi_1",
                "purpose": "seed_authority",
                "query": seed,
                "endpoint_kind": "exact_identifier",
                "status": "http_failed",
                "capped": False,
                "provider_total": None,
                "request_url": (
                    f"https://api.openalex.org/works?filter=doi:{doi}"
                    if provider == "openalex"
                    else f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
                ),
                "response": None,
                "detail": None,
                "diagnostic": {"category": "http_failed", "http_status": 404},
            }],
        }

    crossref_request = {
        "route_id": "seed_doi_1",
        "purpose": "seed_authority",
        "query": seed,
        "endpoint_kind": "exact_identifier",
        "status": "available" if include_seed else "empty",
        "capped": False,
        "provider_total": 1 if include_seed else 0,
        "request_url": f"https://api.crossref.org/works/{doi}",
        "response": exact_response if include_seed else {"message": {"total-results": 0, "items": []}},
        "detail": None,
        "diagnostic": None,
    }
    return {
        "schema_version": PROVIDER_BUNDLE_SCHEMA_V2,
        "topic_contract_sha256": topic_contract_sha256(build_topic_contract(topic)),
        "seed_authorities": [seed],
        "accessed_at": "2026-07-29T00:00:00+00:00",
        "providers": [
            {
                "provider": "crossref",
                "status": "available" if include_seed else "empty",
                "requests": [crossref_request],
            },
            failed("openalex"),
            failed("semantic_scholar"),
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


def test_seed_papers_cli_binds_v3_seed_and_replays(tmp_path: Path, capsys) -> None:
    topic = "Neural DSGE solution methods"
    seed = "doi:10.1016/j.jmoneco.2021.07.004"
    bundle = tmp_path / "bundle-v2.json"
    bundle.write_text(json.dumps(_bundle_v2(topic, seed=seed)), encoding="utf-8")
    output = tmp_path / "campaign-v3"
    command = [
        "survey", "seed-papers", "--topic", topic, "--seed", seed,
        "--out", str(output), "--observation-bundle", str(bundle),
    ]
    assert cli.main(command) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == SEED_REPORT_SCHEMA_V3
    assert report["status"] == "seed_candidates_selected"
    assert report["seed_authorities"] == [seed]
    assert report["seed_authority_ids"] == [seed]
    assert report["selected_paper_ids"] == [seed]
    campaign = json.loads((output / "seed_campaign.json").read_text())
    manifest = json.loads((output / "seed_manifest.json").read_text())
    assert campaign["schema_version"] == SEED_CAMPAIGN_SCHEMA_V3
    assert manifest["schema_version"] == SEED_MANIFEST_SCHEMA_V3

    assert cli.main([
        "survey", "seed-papers", "--topic", topic, "--seed", seed,
        "--out", str(output), "--resume",
    ]) == 0
    assert json.loads(capsys.readouterr().out) == report
    with pytest.raises(MissionStateError, match="seed report differs from replay"):
        recorded = json.loads((output / "seed_report.json").read_text())
        recorded["selected_count"] = 99
        (output / "seed_report.json").write_text(json.dumps(recorded))
        validate_seed_paper_campaign(output)


def test_unresolved_asserted_seed_blocks_instead_of_filling_quota(
    tmp_path: Path, capsys
) -> None:
    topic = "Neural DSGE solution methods"
    seed = "doi:10.1016/j.jmoneco.2021.07.004"
    bundle = tmp_path / "empty-v2.json"
    bundle.write_text(
        json.dumps(_bundle_v2(topic, seed=seed, include_seed=False)),
        encoding="utf-8",
    )
    output = tmp_path / "blocked-v3"
    assert cli.main([
        "survey", "seed-papers", "--topic", topic, "--seed", seed,
        "--out", str(output), "--observation-bundle", str(bundle),
    ]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked_unresolved_seed_authority"
    assert report["selected_count"] == 0
    assert report["unresolved_seed_authorities"] == [{"match_count": 0, "seed": seed}]
    assert validate_seed_paper_campaign(output)["report"] == report
