from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from research_assistant.survey.seed_papers import fuse_seed_candidates
from research_assistant.survey.topic_contract import build_topic_contract, topic_contract_sha256


SCHEMA = "research-assistant-seed-relevance-heldout-result-v1"
OBSERVATIONS_SCHEMA = "ra-survey-seed-provider-observations-v2"


def _record(case: dict[str, Any], index: int) -> dict[str, Any]:
    abstract = case.get("abstract")
    if abstract and case.get("abstract_repeat"):
        abstract = abstract * int(case["abstract_repeat"])
    provider_id = f"heldout-{case['case_id']}"
    return {
        "provider": "crossref",
        "provider_id": provider_id,
        "title": case["title"],
        "abstract": abstract,
        "concepts": [],
        "authors": [f"Heldout Author {index}"],
        "year": 2024,
        "publication_date": "2024-01-01",
        "identifiers": {
            "arxiv": None,
            "crossref": None,
            "doi": None,
            "openalex": None,
            "semantic_scholar": None,
        },
        "citation_count": 0,
        "venue": "Heldout Fixture Journal",
        "venue_key": None,
        "source_url": f"https://example.test/{provider_id}",
        "retraction_status": "not_checked",
        "route_ids": ["heldout_metadata_route"],
        "route_purposes": ["broad_topic"],
        "provider_best_rank": index,
    }


def _observations(contract: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": OBSERVATIONS_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(contract),
        "seed_authorities": [],
        "accessed_at": "2026-07-30T00:00:00+00:00",
        "provider_statuses": [{"provider": "crossref", "status": "available"}],
        "route_statuses": [{"provider": "crossref", "route_id": "heldout_metadata_route", "status": "available"}],
        "records": records,
        "budget_consumption": {"metadata_requests": 1, "provider_rows": len(records), "unique_provider_records": len(records)},
        "limitations": ["heldout fixture metadata only"],
        "benchmark_labels_consumed": False,
    }


def _observed_class(disposition: str) -> str:
    if disposition == "SELECTED_SEED_CANDIDATE":
        return "auto_select"
    if disposition == "REVIEW_REQUIRED_WEAK_MATCH":
        return "review"
    return "reject"


def evaluate(fixture_path: Path) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    contract = build_topic_contract(
        fixture["topic"],
        required_facets=fixture["required_facets"],
        aliases=fixture["aliases"],
        scope_note="Held-out metadata routing evaluation; not a scientific relevance verdict.",
    )
    cases = fixture["cases"]
    records = [_record(case, index) for index, case in enumerate(cases)]
    fused = fuse_seed_candidates(
        contract,
        _observations(contract, records),
        max_selected=len(cases),
        seeds=[],
    )
    by_id = {row["title"]: row for row in fused["candidates"]}
    rows = []
    confusion: Counter[tuple[str, str]] = Counter()
    for case in cases:
        observed = by_id[case["title"]]
        observed_class = _observed_class(observed["disposition"])
        expected = case["label"]
        confusion[(expected, observed_class)] += 1
        rows.append({
            "case_id": case["case_id"],
            "expected_class": expected,
            "observed_class": observed_class,
            "disposition": observed["disposition"],
            "relevance_class": observed["topic_evidence"].get("relevance_class"),
            "covered_facets": observed["topic_evidence"].get("covered_facets", []),
            "abstract_quality": observed.get("abstract_quality"),
            "label_basis": case["label_basis"],
            "match": expected == observed_class,
        })
    labels = ["auto_select", "review", "reject"]
    matrix = {
        expected: {observed: confusion[(expected, observed)] for observed in labels}
        for expected in labels
    }
    correct = sum(row["match"] for row in rows)
    return {
        "schema_version": SCHEMA,
        "fixture_schema_version": fixture["schema_version"],
        "status": "descriptive_heldout_evaluation",
        "topic": contract["topic"],
        "case_count": len(rows),
        "correct_count": correct,
        "accuracy_descriptive_only": correct / len(rows) if rows else None,
        "confusion_matrix": matrix,
        "cases": rows,
        "benchmark_labels_consumed": False,
        "production_thresholds_changed": False,
        "what_is_not_concluded": [
            "universal relevance precision or recall",
            "literature completeness",
            "technical source correctness",
            "scientific importance or centrality",
            "provider live reliability",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.fixture.resolve(strict=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "case_count", "correct_count", "accuracy_descriptive_only")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
