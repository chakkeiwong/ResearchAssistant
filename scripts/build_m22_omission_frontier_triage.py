#!/usr/bin/env python3
"""Build the corrected M22 omission-frontier triage from retained BibTeX."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research_assistant.survey.m20_arxiv_backward_worker import (
    extract_backward_reference_candidates,
)
from research_assistant.survey.omission_frontier_triage import (
    build_inspection_queue,
    classify_unused_candidates,
    validate_inspection_queue,
    validate_provisional_triage,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
M22B0_ROOT = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_north_star_m22b0_"
    "production_reconciliation_2026-07-18"
)
LEDGER_PATH = M22B0_ROOT / "packet/candidate_ledger.json"
BIBTEX_PATH = M22B0_ROOT / (
    "human_review_packet/source_reading/2201_12220v3/unpacked/references.bib"
)
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_north_star_m22_"
    "omission_frontier_triage_2026-07-19"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pretty(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def build_artifacts(*, output_root: Path) -> dict[str, object]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    retained = extract_backward_reference_candidates(BIBTEX_PATH)
    expected_all = {row["candidate_id"] for row in ledger["included"]}
    actual_all = {row["candidate_id"] for row in retained["candidates"]}
    deferred_ids = {
        row["candidate_id"]
        for row in ledger["included"]
        if row["nomination_status"] == "DEFERRED_RETAINED_AS_OMISSION_RISK"
    }
    if (
        retained["candidate_count"] != 62
        or expected_all != actual_all
        or len(deferred_ids) != 55
    ):
        raise RuntimeError("retained_candidate_accounting_mismatch")
    candidates = [
        row for row in retained["candidates"] if row["candidate_id"] in deferred_ids
    ]
    triage = classify_unused_candidates(candidates=candidates)
    validate_provisional_triage(triage, expected_ids=deferred_ids)
    queue = build_inspection_queue(triage)
    validate_inspection_queue(queue, triage=triage)
    old_by_id = {row["candidate_id"]: row for row in ledger["included"]}
    title_repairs = [{
        "candidate_id": row["candidate_id"],
        "old_title": old_by_id[row["candidate_id"]].get("title"),
        "corrected_title": row["title"],
    } for row in candidates if old_by_id[row["candidate_id"]].get("title") != row["title"]]
    manifest = {
        "schema_version": "ra-survey-omission-frontier-triage-build-v1",
        "status": "passed",
        "candidate_count": triage["candidate_count"],
        "nomination_count": queue["nomination_count"],
        "retained_bibtex_path": str(BIBTEX_PATH.relative_to(REPOSITORY_ROOT)),
        "retained_bibtex_sha256": _sha(BIBTEX_PATH),
        "production_ledger_path": str(LEDGER_PATH.relative_to(REPOSITORY_ROOT)),
        "production_ledger_sha256": _sha(LEDGER_PATH),
        "title_repair_count": len(title_repairs),
        "title_repairs": title_repairs,
        "claim_support_allowed": False,
        "ready_for_prose": False,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "provisional_classification.json").write_text(
        _pretty(triage), encoding="utf-8"
    )
    (output_root / "inspection_queue.json").write_text(
        _pretty(queue), encoding="utf-8"
    )
    (output_root / "build_manifest.json").write_text(
        _pretty(manifest), encoding="utf-8"
    )
    lines = [
        "# M22 Omission Frontier Triage",
        "",
        f"All `{triage['candidate_count']}` deferred identifier-bearing references replay from the retained BibTeX.",
        f"The balanced-field repair corrected `{len(title_repairs)}` truncated titles.",
        "Every group below is `TITLE_CONTEXT_PROVISIONAL`; none supports a technical claim.",
        "",
        "## Group Counts",
        "",
        "| Provisional group | Count |",
        "| --- | ---: |",
        *[f"| `{group}` | {count} |" for group, count in triage["group_counts"].items()],
        "",
        "## Five-Paper Inspection Queue",
        "",
        "| Position | Candidate | Provisional title | Rationale |",
        "| ---: | --- | --- | --- |",
        *[
            f"| {row['queue_position']} | `{row['candidate_id']}` | {row['title']} | {row['rationale']} |"
            for row in queue["rows"]
        ],
        "",
        "## Boundary",
        "",
        "Title grouping prioritizes primary-source reading only. It does not establish relevance, importance, publication safety, correctness, claim support, or literature completeness.",
        "",
    ]
    (output_root / "OMISSION_FRONTIER_TRIAGE.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    print(_pretty(build_artifacts(output_root=args.output_root.absolute())), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
