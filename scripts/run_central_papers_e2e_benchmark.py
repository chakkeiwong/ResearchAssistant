#!/usr/bin/env python3
"""Run the evaluator-owned topic-input central-paper benchmark offline."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.central_papers import run_central_papers_campaign
from research_assistant.survey.centrality_benchmark import evaluate_benchmark
from research_assistant.survey.mission_state import canonical_json_bytes, sha256_bytes


CASES = {
    "federated_privacy": "Federated learning and privacy",
    "neural_optimal_transport": "Neural optimal transport",
    "particle_filtering": "Particle filtering for nonlinear state-space models",
}
FIXTURE_ROOT = Path("tests/fixtures/central_papers_e2e")


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def run(output_root: Path) -> dict:
    output_root.mkdir(parents=True, exist_ok=False)
    rows = []
    for case_id, topic in CASES.items():
        fixture = FIXTURE_ROOT / case_id
        campaign_root = output_root / case_id
        report = run_central_papers_campaign(
            topic=topic,
            output_dir=campaign_root,
            observation_bundle=fixture / "observations.json",
        )
        assessment = _load(campaign_root / "centrality_assessment.json")
        result = evaluate_benchmark(_load(fixture / "case.json"), assessment)
        rows.append({
            "case_id": case_id,
            "topic": topic,
            "campaign": {
                "dispositions": report["dispositions"],
                "stop_reason": report["stop_reason"],
                "snowball_status": report["snowball_status"],
                "uncovered_roles": report["uncovered_roles"],
                "budget_consumption": report["budget_consumption"],
                "benchmark_labels_consumed": report["benchmark_labels_consumed"],
            },
            "evaluation": result,
            "fixture_sha256": {
                name: sha256_bytes((fixture / name).read_bytes())
                for name in ("case.json", "observations.json")
            },
        })
    passed = all(row["evaluation"]["status"] == "passed" for row in rows)
    payload = {
        "schema_version": "ra-survey-central-papers-e2e-benchmark-result-v1",
        "status": "passed" if passed else "failed",
        "environment": {"python": "3.11", "platform": "linux", "cuda_visible_devices": "-1"},
        "cases": rows,
        "summary": {
            "case_count": len(rows),
            "passed_case_count": sum(row["evaluation"]["status"] == "passed" for row in rows),
            "must_find_count": sum(len(row["evaluation"]["must_find_results"]) for row in rows),
            "must_reject_count": sum(len(row["evaluation"]["must_reject_results"]) for row in rows),
            "forbidden_promotion_count": sum(len(row["evaluation"]["forbidden_promotions"]) for row in rows),
        },
        "inference_status": {
            "hard_veto_screen": "supported_within_three_evaluator_owned_cases",
            "statistically_supported_ranking": False,
            "descriptive_only": ["budget consumption", "citation metadata", "stop reason"],
            "default_readiness": "bounded_local_campaign_only",
            "next_evidence_needed": "more unrelated externally reviewed topics and broader source providers",
        },
        "what_is_not_concluded": [
            "literature completeness", "paper claim correctness",
            "performance on unreviewed topics", "provider reliability",
            "publication readiness", "universal topic recall",
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
        output_root = Path(args.output_root)
        result = run(output_root)
    else:
        with tempfile.TemporaryDirectory(prefix="ra-central-papers-e2e-") as temporary:
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
