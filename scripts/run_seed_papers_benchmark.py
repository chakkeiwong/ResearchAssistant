#!/usr/bin/env python3
"""Run the raw-provider seed-paper retrieval benchmark offline."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from research_assistant.core_utils import atomic_write_bytes, canonical_json_bytes, sha256_bytes
from research_assistant.survey.seed_papers import run_seed_paper_campaign, validate_seed_paper_campaign
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


ROOT = Path("tests/fixtures/seed_papers_benchmark")


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def run(output_root: Path) -> dict:
    cases = _load(ROOT / "cases.json")
    bundles = _load(ROOT / "raw_bundles.json")
    output_root.mkdir(parents=True, exist_ok=False)
    rows = []
    for case_id in sorted(cases):
        case = cases[case_id]
        contract = build_topic_contract(
            case["topic"],
            required_facets=case.get("required_facets"),
            aliases=case.get("required_aliases"),
            exclusions=case.get("exclusions"),
            scope_note=case.get("scope_note"),
        )
        bundle = dict(bundles[case_id])
        bundle["topic_contract_sha256"] = topic_contract_sha256(contract)
        bundle_path = output_root / f"{case_id}.bundle.json"
        bundle_path.write_bytes(canonical_json_bytes(bundle))
        campaign_root = output_root / case_id
        report = run_seed_paper_campaign(
            topic=case["topic"],
            output_dir=campaign_root,
            observation_bundle=bundle_path,
            required_facets=case.get("required_facets"),
            aliases=case.get("required_aliases"),
            exclusions=case.get("exclusions"),
            scope_note=case.get("scope_note"),
        )
        selected = set(report["selected_paper_ids"])
        must_find = set(case["must_find"])
        must_reject = set(case["must_reject"])
        forbidden = sorted(selected & must_reject)
        missing = sorted(must_find - selected)
        missing_facets = sorted(set(case.get("required_facets", [])) - set(report["facet_coverage"]))
        missing_roles = sorted(set(case.get("required_roles", [])) - set(report["role_coverage"]))
        conflict_observed = any(
            row["paper_id"] == case.get("expected_conflict")
            and row["disposition"] == "BLOCKED_IDENTITY_CONFLICT"
            for row in report["candidates"]
        ) if case.get("expected_conflict") else None
        provider_gap_observed = any(
            row["status"] in {"not_available", "capped"}
            for row in report["provider_statuses"]
        )
        replay_identical = validate_seed_paper_campaign(campaign_root)["report"] == report
        case_passed = (
            not missing
            and not forbidden
            and not missing_facets
            and not missing_roles
            and conflict_observed is not False
            and (not case.get("expected_provider_gap") or provider_gap_observed)
            and replay_identical
            and report["benchmark_labels_consumed"] is False
        )
        rows.append({
            "case_id": case_id,
            "topic": case["topic"],
            "status": "passed" if case_passed else "failed",
            "selected_paper_ids": report["selected_paper_ids"],
            "must_find": sorted(must_find),
            "must_reject": sorted(must_reject),
            "missing_must_find": missing,
            "forbidden_selected": forbidden,
            "provider_statuses": report["provider_statuses"],
            "coverage_gaps": report["coverage_gaps"],
            "facet_coverage": report["facet_coverage"],
            "role_coverage": report["role_coverage"],
            "uncovered_facets": report["uncovered_facets"],
            "uncovered_roles": report["uncovered_roles"],
            "missing_required_facets": missing_facets,
            "missing_required_roles": missing_roles,
            "expected_conflict": case.get("expected_conflict"),
            "conflict_observed": conflict_observed,
            "expected_provider_gap": case.get("expected_provider_gap", False),
            "provider_gap_observed": provider_gap_observed,
            "replay_identical": replay_identical,
            "benchmark_labels_consumed": report["benchmark_labels_consumed"],
            "bundle_sha256": sha256_bytes(bundle_path.read_bytes()),
        })
    payload = {
        "schema_version": "ra-survey-seed-paper-benchmark-result-v2",
        "status": "passed" if all(row["status"] == "passed" for row in rows) else "failed",
        "environment": {"python": "3.11", "platform": "linux", "cuda_visible_devices": "-1"},
        "cases": rows,
        "summary": {
            "case_count": len(rows),
            "passed_case_count": sum(row["status"] == "passed" for row in rows),
            "must_find_count": sum(len(row["must_find"]) for row in rows),
            "missing_must_find_count": sum(len(row["missing_must_find"]) for row in rows),
            "forbidden_selected_count": sum(len(row["forbidden_selected"]) for row in rows),
            "facet_gap_count": sum(len(row["missing_required_facets"]) for row in rows),
            "role_gap_count": sum(len(row["missing_required_roles"]) for row in rows),
        },
        "inference_status": {
            "retrieval_gate": f"supported_within_{len(rows)}_raw_provider_fixture_cases",
            "ranking_statistically_supported": False,
            "centrality_validated": False,
            "next_evidence_needed": "externally curated live-corpus recall and primary-source inspection",
        },
        "what_is_not_concluded": [
            "literature completeness", "canonical best paper", "paper correctness",
            "provider reliability", "universal topic recall", "centrality",
        ],
    }
    payload["result_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root")
    parser.add_argument("--result-path")
    args = parser.parse_args()
    if args.output_root:
        result = run(Path(args.output_root))
    else:
        with tempfile.TemporaryDirectory(prefix="ra-seed-papers-benchmark-") as temporary:
            result = run(Path(temporary) / "campaigns")
    if args.result_path:
        atomic_write_bytes(
            Path(args.result_path),
            (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("ascii"),
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
