from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


WORKSPACE = Path("/tmp/research_assistant_surveybench_phase9_codex_probe_workspace")
GOVERNANCE = WORKSPACE / "governance"


def main() -> int:
    GOVERNANCE.mkdir(parents=True, exist_ok=True)
    stdout_path = GOVERNANCE / "codex_phase10_probe_stdout.jsonl"
    stderr_path = GOVERNANCE / "codex_phase10_probe_stderr.txt"
    exit_path = GOVERNANCE / "codex_phase10_probe_exit_status.json"
    last_message_path = GOVERNANCE / "codex_subject_last_message.md"

    prompt = (
        "This is a bounded SurveyBench Phase 10 transport probe only. "
        "Do not run tools. Do not browse. Do not read or write files. "
        "Do not perform the SurveyBench task. Reply exactly: CODEX_PHASE10_PROBE_OK"
    )
    cmd = [
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "workspace-write",
        "--cd",
        str(WORKSPACE),
        "--skip-git-repo-check",
        "--json",
        "--model",
        "gpt-5.3-codex",
        "--output-last-message",
        str(last_message_path),
        prompt,
    ]
    started = time.time()
    try:
        completed = subprocess.run(
            cmd,
            cwd=WORKSPACE,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
        timeout = False
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timeout = True
        returncode = None
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    ended = time.time()

    stdout_path.write_text(stdout)
    stderr_path.write_text(stderr)
    exit_record = {
        "schema_version": "ra-surveybench-phase10-codex-probe-exit-v1",
        "cmd": cmd,
        "cwd": str(WORKSPACE),
        "returncode": returncode,
        "timeout": timeout,
        "started_unix": started,
        "ended_unix": ended,
        "wall_time_seconds": round(ended - started, 3),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "last_message_path": str(last_message_path),
        "last_message_exists": last_message_path.exists(),
        "last_message_text": last_message_path.read_text() if last_message_path.exists() else None,
    }
    exit_path.write_text(json.dumps(exit_record, indent=2, sort_keys=True))
    print(json.dumps(exit_record, indent=2, sort_keys=True))
    return 0 if returncode == 0 and not timeout else 1


if __name__ == "__main__":
    raise SystemExit(main())
