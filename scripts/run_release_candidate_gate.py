#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_assistant.release_evidence import (  # noqa: E402
    RELEASE_GATE_EVIDENCE_PATH,
    RELEASE_GATE_COMMAND_NAMES,
    atomic_write_evidence,
    build_release_gate_evidence,
    utc_now_iso,
)


COMMANDS = (
    ("static_checks", ["scripts/run_static_checks.sh"]),
    ("fast_tests", ["scripts/run_fast_tests.sh"]),
    ("bounded_tests", ["scripts/run_bounded_tests.sh"]),
    ("active_full_suite", ["scripts/run_tests.sh"]),
    ("packaging_smoke", ["scripts/run_packaging_smoke.sh"]),
    ("build_release_artifacts", ["scripts/build_release_artifacts.sh"]),
    ("clean_install_smoke", ["scripts/run_clean_install_smoke.sh"]),
    ("release_smoke", ["scripts/run_release_smoke.sh"]),
)

assert tuple(name for name, _ in COMMANDS) == RELEASE_GATE_COMMAND_NAMES


def main() -> int:
    if sys.version_info[:2] != (3, 11):
        print(f"release gate requires Python 3.11.x, found {platform.python_version()}", file=sys.stderr)
        return 2
    started = time.monotonic()
    started_at = utc_now_iso()
    rows = []
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    for name, command in COMMANDS:
        command_started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, env=environment)
        rows.append({
            "name": name,
            "command": command,
            "returncode": completed.returncode,
            "wall_time_seconds": round(time.monotonic() - command_started, 6),
        })
        if completed.returncode != 0:
            break
    payload = build_release_gate_evidence(
        root=ROOT,
        commands=rows,
        python_version=platform.python_version(),
        started_at=started_at,
        completed_at=utc_now_iso(),
        wall_time_seconds=time.monotonic() - started,
    )
    output = ROOT / RELEASE_GATE_EVIDENCE_PATH
    atomic_write_evidence(output, payload)
    print(output)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
