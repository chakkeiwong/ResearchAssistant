#!/usr/bin/env python3
"""Run a bounded live-provider transport smoke for seed discovery.

This command makes public metadata requests. It tests transport and response
schema health only; it is not a retrieval-recall or centrality benchmark.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from research_assistant.core_utils import atomic_write_bytes, canonical_json_bytes, sha256_bytes
from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.seed_paper_providers import (
    SUPPORTED_PROVIDERS,
    collect_live_provider_bundle,
)
from research_assistant.survey.seed_papers import run_seed_paper_campaign
from research_assistant.survey.topic_contract import build_topic_contract, plan_discovery_routes


SCHEMA_VERSION = "ra-survey-seed-paper-live-smoke-result-v1"
HOSTS = ["api.crossref.org", "api.openalex.org", "api.semanticscholar.org"]


def run(
    *,
    topic: str,
    required_facets: list[str] | None = None,
    aliases: list[str] | None = None,
    exclusions: list[str] | None = None,
    scope_note: str | None = None,
    output_root: Path,
    max_records_per_response: int = 5,
    max_response_bytes: int = 1_000_000,
    max_total_bytes: int = 8_000_000,
    opener: Any = None,
) -> dict[str, Any]:
    contract = build_topic_contract(
        topic,
        required_facets=required_facets,
        aliases=aliases,
        exclusions=exclusions,
        scope_note=scope_note,
    )
    route_count = plan_discovery_routes(contract)["route_count"]
    max_requests = route_count * len(SUPPORTED_PROVIDERS)
    max_total_records = max_requests * max_records_per_response
    budgets = {
        "max_requests": max_requests,
        "max_records_per_response": max_records_per_response,
        "max_total_records": max_total_records,
        "max_response_bytes": max_response_bytes,
        "max_total_bytes": max_total_bytes,
    }
    started = time.monotonic()
    try:
        bundle = collect_live_provider_bundle(
            contract,
            max_requests=max_requests,
            max_records_per_response=max_records_per_response,
            max_total_records=max_total_records,
            max_response_bytes=max_response_bytes,
            max_total_bytes=max_total_bytes,
            opener=opener,
        )
    except MissionStateError as exc:
        output_root.mkdir(parents=True, exist_ok=False)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "transport_smoke_failed",
            "topic": contract["topic"],
            "providers": list(SUPPORTED_PROVIDERS),
            "hosts": HOSTS,
            "budgets": budgets,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "provider_statuses": [],
            "route_statuses": [],
            "budget_consumption": None,
            "response_schema_valid": False,
            "failure_class": exc.code,
            "selected_count": 0,
            "coverage_gaps": [str(exc)],
            "bundle_sha256": None,
            "what_is_not_concluded": [
                "canonical best paper", "literature completeness", "paper correctness",
                "provider recall", "retrieval recall", "topic centrality",
            ],
        }
        payload["result_sha256"] = sha256_bytes(canonical_json_bytes(payload))
        atomic_write_bytes(
            output_root / "live_smoke_result.json",
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii"),
        )
        return payload
    elapsed = round(time.monotonic() - started, 6)
    output_root.mkdir(parents=True, exist_ok=False)
    bundle_path = output_root / "provider_bundle.json"
    atomic_write_bytes(bundle_path, canonical_json_bytes(bundle))
    report = run_seed_paper_campaign(
        topic=topic,
        output_dir=output_root / "campaign",
        observation_bundle=bundle_path,
        required_facets=required_facets,
        aliases=aliases,
        exclusions=exclusions,
        scope_note=scope_note,
    )
    provider_statuses = report["provider_statuses"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "transport_smoke_passed"
            if any(row["status"] in {"available", "empty", "capped"} for row in provider_statuses)
            else "transport_smoke_blocked_all_providers"
        ),
        "topic": contract["topic"],
        "providers": list(SUPPORTED_PROVIDERS),
        "hosts": HOSTS,
        "budgets": budgets,
        "elapsed_seconds": elapsed,
        "provider_statuses": provider_statuses,
        "route_statuses": report["route_statuses"],
        "budget_consumption": report["budget_consumption"],
        "response_schema_valid": True,
        "selected_count": report["selected_count"],
        "coverage_gaps": report["coverage_gaps"],
        "bundle_sha256": sha256_bytes(bundle_path.read_bytes()),
        "what_is_not_concluded": [
            "canonical best paper",
            "literature completeness",
            "paper correctness",
            "provider recall",
            "retrieval recall",
            "topic centrality",
        ],
    }
    payload["result_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    atomic_write_bytes(
        output_root / "live_smoke_result.json",
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii"),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--required-facet", action="append")
    parser.add_argument("--alias", action="append")
    parser.add_argument("--exclude", action="append")
    parser.add_argument("--scope-note")
    parser.add_argument("--output-root")
    parser.add_argument("--result-path")
    parser.add_argument("--max-records-per-response", type=int, default=5)
    parser.add_argument(
        "--confirm-public-discovery",
        action="store_true",
        help="Confirm bounded public requests to the three recorded provider hosts",
    )
    args = parser.parse_args()
    if not args.confirm_public_discovery:
        parser.error("live provider smoke requires --confirm-public-discovery")
    if args.output_root:
        result = run(
            topic=args.topic,
            required_facets=args.required_facet,
            aliases=args.alias,
            exclusions=args.exclude,
            scope_note=args.scope_note,
            output_root=Path(args.output_root),
            max_records_per_response=args.max_records_per_response,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="ra-seed-live-smoke-") as temporary:
            result = run(
                topic=args.topic,
                required_facets=args.required_facet,
                aliases=args.alias,
                exclusions=args.exclude,
                scope_note=args.scope_note,
                output_root=Path(temporary) / "smoke",
                max_records_per_response=args.max_records_per_response,
            )
    if args.result_path:
        atomic_write_bytes(
            Path(args.result_path),
            (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("ascii"),
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "transport_smoke_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
