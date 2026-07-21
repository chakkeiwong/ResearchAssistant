from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SCHEMA = "ra-literature-survey-m20b1-documentation-supervisor-v1"
WORKER_SCRIPT = Path(__file__).with_name("literature_survey_m20b1_authentication_pricing_contract_fetch.py").resolve()
WORKER_SPEC = importlib.util.spec_from_file_location("m20b1_docs_worker", WORKER_SCRIPT)
if WORKER_SPEC is None or WORKER_SPEC.loader is None:
    raise RuntimeError("cannot load the reviewed M20B1 documentation worker")
WORKER = importlib.util.module_from_spec(WORKER_SPEC)
WORKER_SPEC.loader.exec_module(WORKER)
SOFT_SECONDS = 84.0
HARD_SECONDS = 87.0
FINAL_REAP_SECONDS = 89.0
ABSOLUTE_SECONDS = 90.0
OUTPUT_ROOT = Path("/home/chakwong/research-assistant/docs/validation/literature_survey_m20b1_authentication_pricing_contract_2026-07-14")


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
        temp.unlink()
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temp.exists():
            temp.unlink()


def _read_ledger(path: Path, *, supervisor_path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("status") != "reviewed_ready":
        raise ValueError("M20B1 ledger is not reviewed-ready")
    expected_command = [
        sys.executable,
        str(supervisor_path),
        "--ledger",
        str(path),
        "--output-root",
        str(OUTPUT_ROOT),
    ]
    if value.get("command") != expected_command:
        raise ValueError("M20B1 supervisor command differs")
    expected_worker = [
        sys.executable,
        str(WORKER_SCRIPT),
        "--ledger",
        str(path),
        "--output-root",
        str(OUTPUT_ROOT),
    ]
    if value.get("worker_command") != expected_worker:
        raise ValueError("M20B1 worker command differs")
    if value.get("supervisor_path") != str(supervisor_path) or value.get("supervisor_sha256") != sha256_path(supervisor_path):
        raise ValueError("M20B1 supervisor identity differs")
    return value


def _closed_supervisor_record(
    *,
    classification: str,
    returncode: int | None,
    worker_reaped: bool | None,
    signals_sent: list[str],
    worker_lifecycle_elapsed_seconds: float,
    artifact_replay_elapsed_seconds: float,
    prepublication_elapsed_seconds: float,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "classification": classification,
        "worker_returncode": returncode,
        "worker_reaped": worker_reaped,
        "signals_sent": signals_sent,
        "worker_lifecycle_elapsed_seconds": round(worker_lifecycle_elapsed_seconds, 6),
        "artifact_replay_elapsed_seconds": round(artifact_replay_elapsed_seconds, 6),
        "prepublication_elapsed_seconds": round(prepublication_elapsed_seconds, 6),
        "soft_seconds": SOFT_SECONDS,
        "hard_seconds": HARD_SECONDS,
        "final_reap_seconds": FINAL_REAP_SECONDS,
        "absolute_seconds": ABSOLUTE_SECONDS,
        "deadline_scope": "network_worker_lifecycle_only",
        "stdout_policy": "discarded_to_devnull",
        "stderr_policy": "discarded_to_devnull",
        "stream_content_saved": False,
    }


def _worker_artifacts_are_complete(output_root: Path, ledger: dict[str, Any]) -> bool:
    try:
        WORKER.validate_completed_artifacts(output_root, ledger)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False
    return True


def _remaining(clock: Any, deadline: float) -> float:
    return max(0.001, deadline - clock())


def _signal_worker(worker: Any, sig: signal.Signals, signals_sent: list[str]) -> bool:
    try:
        os.killpg(worker.pid, sig)
        signals_sent.append(sig.name)
        return True
    except ProcessLookupError:
        return True
    except OSError:
        try:
            worker.send_signal(sig)
            signals_sent.append(f"{sig.name}_PID_FALLBACK")
            return True
        except (OSError, ProcessLookupError):
            signals_sent.append(f"{sig.name}_FAILED")
            return False


def run_supervised(
    ledger: dict[str, Any],
    *,
    output_root: Path,
    popen_factory: Any = subprocess.Popen,
    clock: Any = time.monotonic,
) -> int:
    if output_root.exists() or output_root.is_symlink():
        return 2
    started = clock()
    soft_deadline = started + SOFT_SECONDS
    hard_deadline = started + HARD_SECONDS
    final_reap_deadline = started + FINAL_REAP_SECONDS
    absolute_deadline = started + ABSOLUTE_SECONDS
    worker = None
    signals_sent: list[str] = []
    classification = "worker_start_failed"
    try:
        try:
            worker = popen_factory(
                ledger["worker_command"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env={"CUDA_VISIBLE_DEVICES": "-1", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            worker.communicate(timeout=_remaining(clock, soft_deadline))
            classification = "completed" if worker.returncode == 0 else "worker_failed"
        except subprocess.TimeoutExpired:
            classification = "soft_timeout"
            if worker is None or not _signal_worker(worker, signal.SIGTERM, signals_sent):
                classification = "signal_failed"
            try:
                if worker is not None:
                    worker.communicate(timeout=_remaining(clock, hard_deadline))
            except subprocess.TimeoutExpired:
                classification = "hard_timeout"
                if worker is None or not _signal_worker(worker, signal.SIGKILL, signals_sent):
                    classification = "signal_failed"
                try:
                    if worker is not None:
                        worker.communicate(timeout=_remaining(clock, final_reap_deadline))
                except subprocess.TimeoutExpired:
                    classification = "final_reap_timeout"
        except (OSError, ValueError, subprocess.SubprocessError):
            classification = "worker_start_failed" if worker is None else "supervisor_lifecycle_error"
    finally:
        if worker is not None and worker.returncode is None:
            _signal_worker(worker, signal.SIGKILL, signals_sent)
            try:
                worker.wait(timeout=_remaining(clock, absolute_deadline))
            except (OSError, ValueError, subprocess.SubprocessError):
                classification = "cleanup_reap_indeterminate"
        worker_reaped = worker is not None and worker.returncode is not None
        worker_lifecycle_elapsed = max(0.0, clock() - started)
        if worker_lifecycle_elapsed > ABSOLUTE_SECONDS and worker_reaped:
            classification = "cleanup_overrun_after_worker_termination"
        if worker is not None and not worker_reaped:
            classification = "cleanup_reap_indeterminate"
        replay_started = clock()
        if classification == "completed" and not _worker_artifacts_are_complete(output_root, ledger):
            classification = "worker_artifact_invalid"
        artifact_replay_elapsed = max(0.0, clock() - replay_started)
        prepublication_elapsed = max(0.0, clock() - started)
        output_root.mkdir(parents=True, exist_ok=True)
        record = _closed_supervisor_record(
            classification=classification,
            returncode=worker.returncode if worker is not None else None,
            worker_reaped=worker_reaped if worker is not None else None,
            signals_sent=signals_sent,
            worker_lifecycle_elapsed_seconds=worker_lifecycle_elapsed,
            artifact_replay_elapsed_seconds=artifact_replay_elapsed,
            prepublication_elapsed_seconds=prepublication_elapsed,
        )
        _atomic_write(output_root / "supervisor_manifest.json", pretty_json_bytes(record))
    return 0 if classification == "completed" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    supervisor_path = Path(__file__).resolve()
    if args.output_root.resolve() != OUTPUT_ROOT.resolve():
        return 2
    try:
        ledger = _read_ledger(args.ledger, supervisor_path=supervisor_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        if not args.output_root.exists() and not args.output_root.is_symlink():
            args.output_root.mkdir(parents=True, exist_ok=False)
            record = _closed_supervisor_record(
                classification="preflight_invalid",
                returncode=None,
                worker_reaped=None,
                signals_sent=[],
                worker_lifecycle_elapsed_seconds=0.0,
                artifact_replay_elapsed_seconds=0.0,
                prepublication_elapsed_seconds=0.0,
            )
            _atomic_write(args.output_root / "supervisor_manifest.json", pretty_json_bytes(record))
        return 2
    return run_supervised(ledger, output_root=args.output_root)


if __name__ == "__main__":
    raise SystemExit(main())
