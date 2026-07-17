from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from research_assistant.survey import m20_recovery_launcher as launcher


def _args(tmp_path: Path) -> dict:
    packet = (tmp_path / "packet.json").resolve()
    packet.write_text("{}")
    return {
        "packet_path": packet,
        "output_root": (tmp_path / "live").resolve(),
        "diagnostic_path": (tmp_path / "diagnostic.json").resolve(),
        "intent_path": (tmp_path / "outer-intent.json").resolve(),
        "outer_path": (tmp_path / "outer.json").resolve(),
        "fallback_path": (tmp_path / "outer-fallback.json").resolve(),
    }


def test_closed_child_writes_primary_outer_record(tmp_path: Path) -> None:
    args = _args(tmp_path)
    assert launcher.run(**args, run_process=lambda *a, **k: SimpleNamespace(returncode=2)) == 2
    record = json.loads(args["outer_path"].read_text())
    assert record["child_outcome"] == "closed_exit"
    assert record["child_exit_code"] == 2
    assert record["credential_read_or_enumerated_by_launcher"] is False
    assert record["outer_intent_sha256"] == launcher._sha_path(args["intent_path"])
    assert not args["fallback_path"].exists()


def test_intent_publication_failure_prevents_child_launch(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    called = False

    def child(*_args, **_kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(
        launcher,
        "_atomic_write",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("synthetic intent failure")),
    )
    assert launcher.run(**args, run_process=child) == 3
    assert called is False
    assert not args["outer_path"].exists()
    assert not args["fallback_path"].exists()


def test_primary_publication_failure_writes_independent_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    args = _args(tmp_path)
    real_write = launcher._atomic_write

    def write(path: Path, value: dict) -> None:
        if path == args["outer_path"]:
            raise OSError("synthetic primary failure")
        real_write(path, value)

    monkeypatch.setattr(launcher, "_atomic_write", write)
    assert launcher.run(**args, run_process=lambda *a, **k: SimpleNamespace(returncode=2)) == 2
    assert not args["outer_path"].exists()
    assert json.loads(args["fallback_path"].read_text())["child_exit_code"] == 2


def test_both_terminal_publications_failing_leave_intent_hard_stop(
    monkeypatch, tmp_path: Path
) -> None:
    args = _args(tmp_path)
    real_write = launcher._atomic_write

    def write(path: Path, value: dict) -> None:
        if path in {args["outer_path"], args["fallback_path"]}:
            raise OSError("synthetic terminal failure")
        real_write(path, value)

    monkeypatch.setattr(launcher, "_atomic_write", write)
    assert launcher.run(**args, run_process=lambda *a, **k: SimpleNamespace(returncode=2)) == 3
    assert args["intent_path"].is_file()
    assert not args["outer_path"].exists()
    assert not args["fallback_path"].exists()


def test_child_exception_is_bounded_without_exception_text(tmp_path: Path) -> None:
    args = _args(tmp_path)

    def fail(*a, **k):
        raise RuntimeError("sensitive child exception")

    assert launcher.run(**args, run_process=fail) == 3
    raw = args["outer_path"].read_bytes()
    assert b"sensitive child exception" not in raw
    assert json.loads(raw)["child_outcome"] == "launcher_child_error"


def test_launcher_source_does_not_read_or_enumerate_environment() -> None:
    source = Path("src/research_assistant/survey/m20_recovery_launcher.py").read_text()
    assert "os.environ" not in source
    assert "os.getenv" not in source
