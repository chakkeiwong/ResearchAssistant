from __future__ import annotations

import json
from pathlib import Path

from research_assistant import cli
from research_assistant.survey.seed_papers import run_seed_paper_campaign


FIXTURES = Path("tests/fixtures/seed_papers_benchmark")


def test_cli_continues_replay_valid_seed_campaign(tmp_path: Path, capsys) -> None:
    cases = json.loads((FIXTURES / "cases.json").read_text())
    bundles = json.loads((FIXTURES / "raw_bundles.json").read_text())
    case = cases["causal_inference"]
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(bundles["causal_inference"]))
    parent = tmp_path / "campaign"
    run_seed_paper_campaign(
        topic=case["topic"], output_dir=parent, observation_bundle=bundle
    )
    child = tmp_path / "child"

    assert cli.main([
        "survey", "continue-seeds", "--seed-campaign", str(parent),
        "--out", str(child),
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "seed_handoff_written"
    assert result["handoff"]["selected_paper_ids"] == ["doi:10.1000/causal-iv"]


def test_cli_seed_topic_controls_are_bound_to_campaign(tmp_path: Path, capsys) -> None:
    topic = "Causal inference with instrumental variables"
    bundles = json.loads((FIXTURES / "raw_bundles.json").read_text())
    bundle_value = bundles["causal_inference"]
    from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256

    contract = build_topic_contract(
        topic,
        required_facets=["causal inference", "instrumental variables"],
        aliases=["IV estimation"],
        exclusions=["matching methods"],
        scope_note="Methods using instruments for causal identification.",
    )
    bundle_value["topic_contract_sha256"] = topic_contract_sha256(contract)
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(bundle_value))
    output = tmp_path / "campaign"
    command = [
        "survey", "seed-papers", "--topic", topic, "--out", str(output),
        "--observation-bundle", str(bundle),
        "--required-facet", "causal inference",
        "--required-facet", "instrumental variables",
        "--alias", "IV estimation",
        "--exclude", "matching methods",
        "--scope-note", "Methods using instruments for causal identification.",
    ]
    assert cli.main(command) == 0
    capsys.readouterr()
    recorded = json.loads((output / "topic_contract.json").read_text())
    assert recorded == contract
