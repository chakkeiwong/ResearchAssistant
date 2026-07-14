#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from research_assistant.benchmarks.surveybench import score_survey_task


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score an offline SurveyBench citation-map task."
    )
    parser.add_argument(
        "--fixture",
        required=True,
        type=Path,
        help="Path to a ra-surveybench-task-v1 JSON task file.",
    )
    parser.add_argument(
        "--actual-dir",
        type=Path,
        help="Optional directory containing candidate output files with expected artifact filenames.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    report = score_survey_task(args.fixture.resolve(), args.actual_dir.resolve() if args.actual_dir else None)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
