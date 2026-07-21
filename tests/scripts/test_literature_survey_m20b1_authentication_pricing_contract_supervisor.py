from __future__ import annotations

import importlib.util
import json
import subprocess
from email.message import Message
from pathlib import Path


SCRIPT = Path("scripts/literature_survey_m20b1_authentication_pricing_contract_supervisor.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20b1_docs_supervisor", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class Process:
    def __init__(self, *, outcomes, returncode: int = 0, pid: int = 123, clock: Clock | None = None) -> None:  # noqa: ANN001
        self.outcomes = list(outcomes)
        self.returncode = returncode
        self.pid = pid
        self.calls = []
        self.clock = clock

    def communicate(self, timeout):  # noqa: ANN001
        self.calls.append(timeout)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            if self.clock is not None:
                self.clock.advance(timeout)
            raise outcome
        return outcome

    def send_signal(self, sig) -> None:  # noqa: ANN001
        self.returncode = -int(sig)

    def wait(self, timeout=None):  # noqa: ANN001
        self.calls.append(("wait", timeout))
        if self.returncode is None:
            self.returncode = -9
        return self.returncode


class CleanupTimeoutProcess(Process):
    def wait(self, timeout=None):  # noqa: ANN001
        self.calls.append(("wait", timeout))
        if self.clock is not None:
            self.clock.advance(timeout or 0.0)
        raise subprocess.TimeoutExpired("worker", timeout)


def _ledger(tmp_path: Path) -> tuple[dict, Path]:
    output = tmp_path / "out"
    return {
        "campaign_id": "literature-survey-m20b1-auth-pricing-20260714-v1",
        "worker_command": ["worker"],
        "requests": [dict(row) for row in MODULE.WORKER.EXPECTED_REQUESTS],
    }, output


class Response:
    def __init__(self, body: bytes, *, url: str) -> None:
        self.body = body
        self.offset = 0
        self.url = url
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.headers["Content-Length"] = str(len(body))

    def read(self, size: int = -1) -> bytes:
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self.url

    def getcode(self) -> int:
        return self.status

    def close(self) -> None:
        pass


class Opener:
    def __init__(self, responses) -> None:  # noqa: ANN001
        self.responses = list(responses)

    def open(self, request, timeout):  # noqa: ANN001, ANN201
        return self.responses.pop(0)


def _write_worker_artifacts(output: Path, *, campaign_id: str) -> None:
    ledger = {
        "campaign_id": campaign_id,
        "requests": [dict(row) for row in MODULE.WORKER.EXPECTED_REQUESTS],
    }
    MODULE.WORKER.execute(
        ledger,
        output_root=output,
        opener=Opener([
            Response(b"auth", url=ledger["requests"][0]["url"]),
            Response(b"rate", url=ledger["requests"][1]["url"]),
        ]),
    )


def test_completed_worker_writes_closed_supervisor_manifest(tmp_path: Path) -> None:
    ledger, output = _ledger(tmp_path)
    process = Process(outcomes=[(b"ok", b"")])

    def factory(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        _write_worker_artifacts(output, campaign_id=ledger["campaign_id"])
        return process

    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=factory) == 0
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "completed"
    assert record["worker_returncode"] == 0
    assert record["worker_reaped"] is True
    assert record["deadline_scope"] == "network_worker_lifecycle_only"
    assert record["stdout_policy"] == "discarded_to_devnull"
    assert record["stderr_policy"] == "discarded_to_devnull"
    assert record["stream_content_saved"] is False


def test_soft_timeout_terminates_group_and_closes_manifest(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger, output = _ledger(tmp_path)
    clock = Clock()
    process = Process(outcomes=[subprocess.TimeoutExpired("worker", 1), (b"", b"")], returncode=-15, clock=clock)
    signals = []
    monkeypatch.setattr(MODULE.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=lambda *a, **k: process, clock=clock) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "soft_timeout"
    assert record["signals_sent"] == ["SIGTERM"]
    assert len(signals) == 1
    assert 0 < process.calls[0] <= MODULE.SOFT_SECONDS
    assert 0 < process.calls[1] <= MODULE.HARD_SECONDS - MODULE.SOFT_SECONDS


def test_hard_timeout_kills_group_and_closes_manifest(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger, output = _ledger(tmp_path)
    clock = Clock()
    process = Process(
        outcomes=[subprocess.TimeoutExpired("worker", 1), subprocess.TimeoutExpired("worker", 1), (b"", b"")],
        returncode=-9,
        clock=clock,
    )
    signals = []
    monkeypatch.setattr(MODULE.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=lambda *a, **k: process, clock=clock) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "hard_timeout"
    assert record["signals_sent"] == ["SIGTERM", "SIGKILL"]
    assert len(signals) == 2
    assert 0 < process.calls[2] <= MODULE.FINAL_REAP_SECONDS - MODULE.HARD_SECONDS


def test_existing_output_prevents_worker_start(tmp_path: Path) -> None:
    ledger, output = _ledger(tmp_path)
    output.mkdir()
    called = []
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=lambda *a, **k: called.append(True)) == 2
    assert called == []


def test_zero_exit_without_complete_worker_artifacts_is_closed_failure(tmp_path: Path) -> None:
    ledger, output = _ledger(tmp_path)
    process = Process(outcomes=[(b"ok", b"")])
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=lambda *a, **k: process) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "worker_artifact_invalid"


def test_spawn_failure_still_writes_supervisor_manifest(tmp_path: Path) -> None:
    ledger, output = _ledger(tmp_path)

    def fail(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise OSError("spawn failed")

    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=fail) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "worker_start_failed"
    assert record["worker_returncode"] is None


def test_signal_failure_falls_back_to_pid_and_closes_manifest(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger, output = _ledger(tmp_path)
    clock = Clock()
    process = Process(outcomes=[subprocess.TimeoutExpired("worker", 1), (b"", b"")], returncode=-15, clock=clock)
    monkeypatch.setattr(MODULE.os, "killpg", lambda pid, sig: (_ for _ in ()).throw(OSError("group failure")))
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=lambda *a, **k: process, clock=clock) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "soft_timeout"
    assert record["signals_sent"] == ["SIGTERM_PID_FALLBACK"]


def test_cleanup_reap_indeterminate_never_uses_unbounded_wait(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger, output = _ledger(tmp_path)
    clock = Clock()
    process = CleanupTimeoutProcess(
        outcomes=[subprocess.TimeoutExpired("worker", 1), subprocess.TimeoutExpired("worker", 1), subprocess.TimeoutExpired("worker", 1)],
        returncode=None,
        clock=clock,
    )
    monkeypatch.setattr(MODULE.os, "killpg", lambda pid, sig: None)
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=lambda *a, **k: process, clock=clock) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "cleanup_reap_indeterminate"
    assert record["worker_reaped"] is False
    assert process.returncode is None
    assert all(call != ("wait", None) for call in process.calls)
    assert record["worker_lifecycle_elapsed_seconds"] <= MODULE.ABSOLUTE_SECONDS + 0.01


def test_artifact_replay_duration_is_separate_from_worker_deadline(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger, output = _ledger(tmp_path)
    clock = Clock()
    process = Process(outcomes=[(b"", b"")], clock=clock)

    def factory(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        _write_worker_artifacts(output, campaign_id=ledger["campaign_id"])
        return process

    original = MODULE._worker_artifacts_are_complete

    def replay(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        clock.advance(2.5)
        return original(*args, **kwargs)

    monkeypatch.setattr(MODULE, "_worker_artifacts_are_complete", replay)
    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=factory, clock=clock) == 0
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["worker_lifecycle_elapsed_seconds"] == 0.0
    assert record["artifact_replay_elapsed_seconds"] == 2.5
    assert record["prepublication_elapsed_seconds"] == 2.5


def test_preflight_invalid_main_writes_manifest(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    output = tmp_path / "real-output"
    ledger = tmp_path / "invalid.json"
    ledger.write_text("{}")
    monkeypatch.setattr(MODULE, "OUTPUT_ROOT", output)
    assert MODULE.main(["--ledger", str(ledger), "--output-root", str(output)]) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "preflight_invalid"


def test_exact_worker_artifact_tamper_blocks_supervisor_success(tmp_path: Path) -> None:
    ledger, output = _ledger(tmp_path)
    process = Process(outcomes=[(b"", b"")])

    def factory(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        _write_worker_artifacts(output, campaign_id=ledger["campaign_id"])
        (output / "raw/01_openalex_authentication_pricing.html").write_bytes(b"tampered")
        return process

    assert MODULE.run_supervised(ledger, output_root=output, popen_factory=factory) == 2
    record = json.loads((output / "supervisor_manifest.json").read_text())
    assert record["classification"] == "worker_artifact_invalid"
