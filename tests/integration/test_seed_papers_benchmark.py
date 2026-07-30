from __future__ import annotations

import json
from pathlib import Path

from research_assistant.survey.seed_papers import run_seed_paper_campaign
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


ROOT = Path("tests/fixtures/seed_papers_benchmark")


def test_raw_provider_topic_retrieval_benchmark(tmp_path: Path) -> None:
    cases = json.loads((ROOT / "cases.json").read_text())
    bundles = json.loads((ROOT / "raw_bundles.json").read_text())
    for case_id in sorted(cases):
        case = cases[case_id]
        contract = build_topic_contract(
            case["topic"],
            required_facets=case.get("required_facets"),
            aliases=case.get("required_aliases"),
            exclusions=case.get("exclusions"),
            scope_note=case.get("scope_note"),
        )
        bundle_value = dict(bundles[case_id])
        bundle_value["topic_contract_sha256"] = topic_contract_sha256(contract)
        bundle = tmp_path / f"{case_id}.json"
        bundle.write_text(json.dumps(bundle_value))
        report = run_seed_paper_campaign(
            topic=case["topic"],
            output_dir=tmp_path / case_id,
            observation_bundle=bundle,
            required_facets=case.get("required_facets"),
            aliases=case.get("required_aliases"),
            exclusions=case.get("exclusions"),
            scope_note=case.get("scope_note"),
        )
        selected = set(report["selected_paper_ids"])
        assert set(case["must_find"]) <= selected, (case_id, report)
        assert not selected & set(case["must_reject"]), (case_id, report)
        assert set(case.get("required_facets", [])) <= set(report["facet_coverage"]), (case_id, report)
        assert set(case.get("required_roles", [])) <= set(report["role_coverage"]), (case_id, report)
        if case.get("expected_conflict"):
            conflict = next(row for row in report["candidates"] if row["paper_id"] == case["expected_conflict"])
            assert conflict["disposition"] == "BLOCKED_IDENTITY_CONFLICT"
        if case.get("expected_provider_gap"):
            assert any(row["status"] in {"not_available", "capped"} for row in report["provider_statuses"])
        assert report["benchmark_labels_consumed"] is False


def test_maliar_adversarial_repair_benchmark(tmp_path: Path) -> None:
    case = json.loads((ROOT / "maliar_adversarial.json").read_text())
    topic = case["topic"]
    seed = case["seed"]
    contract = build_topic_contract(
        topic,
        required_facets=case["required_facets"],
        aliases=case["aliases"],
        exclusions=case["exclusions"],
    )
    bundle = case["bundle"]
    bundle["topic_contract_sha256"] = topic_contract_sha256(contract)
    path = tmp_path / "maliar_adversarial.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    report = run_seed_paper_campaign(
        topic=topic,
        output_dir=tmp_path / "maliar_adversarial",
        observation_bundle=path,
        seeds=[seed],
        required_facets=contract["required_facets"],
        aliases=contract["aliases"],
        exclusions=contract["exclusions"],
    )
    assert report["selected_paper_ids"][0] == seed
    assert report["status"] == "seed_candidates_selected"
    assert set(case["must_find"]) <= set(report["selected_paper_ids"])
    assert not set(case["must_reject"]) & set(report["selected_paper_ids"])
    for paper_id in case["must_review_or_select"]:
        assert any(
            row["paper_id"] == paper_id
            and row["disposition"] in {"SELECTED_SEED_CANDIDATE", "REVIEW_REQUIRED_WEAK_MATCH"}
            for row in report["candidates"]
        )


def test_runtime_does_not_contain_evaluator_case_labels() -> None:
    runtime = (
        Path("src/research_assistant/survey/seed_paper_providers.py").read_text()
        + Path("src/research_assistant/survey/seed_papers.py").read_text()
    )
    for forbidden in ("causal_inference", "federated_privacy", "must_find", "must_reject", "raw_bundles"):
        assert forbidden not in runtime
