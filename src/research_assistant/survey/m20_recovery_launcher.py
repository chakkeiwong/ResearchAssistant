from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


OUTER_INTENT_SCHEMA = "ra-literature-survey-m20-recovery-outer-intent-v1"
OUTER_SCHEMA = "ra-literature-survey-m20-recovery-outer-invocation-v2"


class M20RecoveryLauncherError(RuntimeError):
    pass


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    if (
        not path.is_absolute()
        or path.exists()
        or path.is_symlink()
        or not path.parent.is_dir()
        or path.parent.is_symlink()
    ):
        raise M20RecoveryLauncherError("outer_record_path_invalid")
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def run(
    *,
    packet_path: Path,
    output_root: Path,
    diagnostic_path: Path,
    intent_path: Path,
    outer_path: Path,
    fallback_path: Path,
    run_process: Any = subprocess.run,
) -> int:
    packet_file_sha256 = _sha_path(packet_path)
    command = [
        sys.executable,
        "-I",
        "-m",
        "research_assistant.survey.m20_live_supervisor",
        "--packet",
        str(packet_path),
        "--output-root",
        str(output_root),
        "--launch-diagnostic-path",
        str(diagnostic_path),
        "--execute-m20-recovery-campaign",
    ]
    intent = {
        "schema_version": OUTER_INTENT_SCHEMA,
        "packet_file_sha256": packet_file_sha256,
        "child_command": command,
        "credential_read_or_enumerated_by_launcher": False,
        "provider_activity": False,
        "cost_usd": "0.00",
        "privacy_state": "passed_closed_construction_before_child",
    }
    try:
        _atomic_write(intent_path, intent)
    except BaseException:
        return 3
    intent_sha256 = _sha_path(intent_path)
    child_outcome = "closed_exit"
    child_exit_code: int | str = "not_established"
    try:
        completed = run_process(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        child_exit_code = completed.returncode
    except BaseException:
        child_outcome = "launcher_child_error"
    record = {
        "schema_version": OUTER_SCHEMA,
        "packet_file_sha256": packet_file_sha256,
        "outer_intent_sha256": intent_sha256,
        "child_outcome": child_outcome,
        "child_exit_code": child_exit_code,
        "diagnostic_exists": diagnostic_path.is_file() and not diagnostic_path.is_symlink(),
        "live_root_exists": output_root.exists(),
        "supervisor_manifest_exists": (
            (output_root / "supervisor_manifest.json").is_file()
            and not (output_root / "supervisor_manifest.json").is_symlink()
        ),
        "credential_read_or_enumerated_by_launcher": False,
        "provider_activity": "not_established",
        "cost_usd": "not_established",
        "privacy_state": "not_established",
    }
    try:
        _atomic_write(outer_path, record)
    except BaseException:
        try:
            _atomic_write(fallback_path, record)
        except BaseException:
            return 3
    return child_exit_code if type(child_exit_code) is int else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--launch-diagnostic-path", type=Path, required=True)
    parser.add_argument("--outer-intent-path", type=Path, required=True)
    parser.add_argument("--outer-invocation-path", type=Path, required=True)
    parser.add_argument("--outer-invocation-fallback-path", type=Path, required=True)
    parser.add_argument("--execute-m20-recovery-campaign", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute_m20_recovery_campaign:
        return 3
    return run(
        packet_path=args.packet.resolve(strict=False),
        output_root=args.output_root.resolve(strict=False),
        diagnostic_path=args.launch_diagnostic_path.resolve(strict=False),
        intent_path=args.outer_intent_path.resolve(strict=False),
        outer_path=args.outer_invocation_path.resolve(strict=False),
        fallback_path=args.outer_invocation_fallback_path.resolve(strict=False),
    )


if __name__ == "__main__":
    raise SystemExit(main())
