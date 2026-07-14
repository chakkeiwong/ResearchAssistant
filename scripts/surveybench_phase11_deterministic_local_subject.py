from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from research_assistant.benchmarks.replay import score_replay_submission
from research_assistant.benchmarks.surveybench_helpers import surveybench_packet_compose


WORKSPACE = Path("/tmp/research_assistant_surveybench_phase9_codex_probe_workspace")
TASK_REL = Path(
    "tests/fixtures/surveybench/online_replay/"
    "neural_ot_seed_ambiguity_partial_frontier_replay/"
    "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
)
RESPONSE_REL = TASK_REL.parent / "responses"
GOLD_DIR = (
    Path("/home/chakwong/research-assistant")
    / "tests/fixtures/surveybench/online_replay/"
    "neural_ot_seed_ambiguity_partial_frontier_replay/scorer_packet"
)
VALIDATION_DIR = Path(
    "/home/chakwong/research-assistant/"
    "docs/validation/surveybench_real_subject_trial_phase11_deterministic_local_subject_2026-07-06"
)
ENDPOINTS = (
    "search",
    "paper",
    "references",
    "citations",
    "adjacent",
    "download-status",
    "source-status",
    "source-anchors",
    "evidence-context",
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _run_replay_call(endpoint: str, session_dir: Path, capture_dir: Path) -> dict[str, object]:
    cmd = [
        sys.executable,
        "-m",
        "research_assistant.cli",
        "surveybench",
        "replay-call",
        "--task",
        str(WORKSPACE / TASK_REL),
        "--endpoint",
        endpoint,
        "--session",
        str(session_dir),
    ]
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONPATH": str(WORKSPACE / "src"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(WORKSPACE / ".ra_restricted_runtime" / "home"),
        "TMPDIR": str(WORKSPACE / ".ra_restricted_runtime" / "tmp"),
        "XDG_CACHE_HOME": str(WORKSPACE / ".ra_restricted_runtime" / "xdg-cache"),
        "XDG_CONFIG_HOME": str(WORKSPACE / ".ra_restricted_runtime" / "xdg-config"),
        "XDG_DATA_HOME": str(WORKSPACE / ".ra_restricted_runtime" / "xdg-data"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    started = time.time()
    completed = subprocess.run(
        cmd,
        cwd=WORKSPACE,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    ended = time.time()
    stdout_path = capture_dir / f"{endpoint}.stdout.json"
    stderr_path = capture_dir / f"{endpoint}.stderr.txt"
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    parsed = None
    parse_error = None
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except ValueError as exc:
            parse_error = str(exc)
    return {
        "endpoint": endpoint,
        "cmd": cmd,
        "cwd": str(WORKSPACE),
        "returncode": completed.returncode,
        "wall_time_seconds": round(ended - started, 3),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "parse_error": parse_error,
        "status": parsed.get("status") if isinstance(parsed, dict) else None,
        "event_log_path": parsed.get("event_log_path") if isinstance(parsed, dict) else None,
    }


def main() -> int:
    if not (WORKSPACE / ".ra_restricted_workspace_manifest.json").exists():
        raise SystemExit(f"restricted workspace manifest missing under {WORKSPACE}")

    session_dir = WORKSPACE / "phase11_local_subject_session"
    output_dir = WORKSPACE / "phase11_local_subject_packet"
    capture_dir = WORKSPACE / "governance" / "phase11_local_subject_replay_captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    endpoint_reports = [
        _run_replay_call(endpoint, session_dir=session_dir, capture_dir=capture_dir)
        for endpoint in ENDPOINTS
    ]
    _write_json(VALIDATION_DIR / "deterministic_subject_replay_report.json", {
        "schema_version": "ra-surveybench-phase11-deterministic-replay-report-v1",
        "workspace_root": str(WORKSPACE),
        "session_dir": str(session_dir),
        "output_dir": str(output_dir),
        "subject_kind": "deterministic_local_substitute",
        "endpoint_reports": endpoint_reports,
        "what_is_not_concluded": [
            "real model-agent quality",
            "live web coverage",
            "survey prose quality",
            "scientific correctness",
        ],
    })

    if any(row["returncode"] != 0 or row["status"] not in {"ok", "simulated_rate_limit"} for row in endpoint_reports):
        raise SystemExit(1)

    compose_report = surveybench_packet_compose(
        WORKSPACE / TASK_REL,
        output_dir,
        session_dir=session_dir,
        responses_dir=WORKSPACE / RESPONSE_REL,
        write_files=True,
    )
    _write_json(VALIDATION_DIR / "deterministic_subject_compose_report.json", compose_report)
    if compose_report["status"] != "ready":
        raise SystemExit(1)

    score_report = score_replay_submission(
        WORKSPACE / TASK_REL,
        output_dir,
        session_dir / "event_log.json",
        GOLD_DIR,
    )
    _write_json(VALIDATION_DIR / "deterministic_subject_score_report.json", score_report)
    result = {
        "schema_version": "ra-surveybench-phase11-deterministic-local-subject-result-v1",
        "status": "passed" if score_report["status"] == "passed" else "failed",
        "subject_kind": "deterministic_local_substitute",
        "workspace_root": str(WORKSPACE),
        "session_dir": str(session_dir),
        "output_dir": str(output_dir),
        "event_log_path": str(session_dir / "event_log.json"),
        "compose_report_path": str(VALIDATION_DIR / "deterministic_subject_compose_report.json"),
        "score_report_path": str(VALIDATION_DIR / "deterministic_subject_score_report.json"),
        "score_status": score_report["status"],
        "vetoes": score_report["vetoes"],
        "errors": score_report["errors"],
        "not_a_real_subject_trial": True,
        "what_is_not_concluded": [
            "Codex or Claude model quality",
            "real agent reliability",
            "live web/download robustness",
            "survey prose quality",
            "product readiness",
            "Neural OT scientific correctness",
        ],
    }
    _write_json(VALIDATION_DIR / "deterministic_local_subject_result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
