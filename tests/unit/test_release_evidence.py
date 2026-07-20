from __future__ import annotations

import hashlib
import json
from pathlib import Path

from research_assistant import __version__
from research_assistant.release_evidence import (
    RELEASE_ARTIFACT_MANIFEST_SCHEMA,
    RELEASE_GATE_COMMAND_NAMES,
    RELEASE_GATE_EVIDENCE_PATH,
    atomic_write_evidence,
    build_release_gate_evidence,
    release_source_fingerprint,
    validate_release_artifact_manifest,
    validate_release_gate_evidence,
)


def _release_tree(root: Path) -> None:
    (root / "src" / "research_assistant").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "docs").mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\n')
    (root / "src" / "research_assistant" / "module.py").write_text("VALUE = 1\n")
    (root / "scripts" / "check.sh").write_text("#!/usr/bin/env bash\n")
    (root / "tests" / "test_module.py").write_text("def test_value(): pass\n")


def _passing_commands() -> list[dict]:
    return [
        {"name": name, "command": ["run", name], "returncode": 0, "wall_time_seconds": 1.0}
        for name in RELEASE_GATE_COMMAND_NAMES
    ]


def test_release_source_fingerprint_changes_with_source_bytes(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    first = release_source_fingerprint(tmp_path)
    (tmp_path / "src" / "research_assistant" / "module.py").write_text("VALUE = 2\n")
    second = release_source_fingerprint(tmp_path)
    assert first.sha256 != second.sha256


def test_release_source_fingerprint_ignores_generated_bytecode(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    first = release_source_fingerprint(tmp_path)
    cache = tmp_path / "scripts" / "__pycache__"
    cache.mkdir()
    (cache / "check.cpython-311.pyc").write_bytes(b"generated")
    assert release_source_fingerprint(tmp_path) == first


def test_release_gate_evidence_validates_and_detects_stale_source(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    payload = build_release_gate_evidence(
        root=tmp_path,
        commands=_passing_commands(),
        python_version="3.11.14",
        started_at="2026-07-20T00:00:00+00:00",
        completed_at="2026-07-20T00:00:01+00:00",
        wall_time_seconds=1.0,
    )
    atomic_write_evidence(tmp_path / RELEASE_GATE_EVIDENCE_PATH, payload)
    assert validate_release_gate_evidence(tmp_path)["status"] == "passed"

    (tmp_path / "src" / "research_assistant" / "module.py").write_text("VALUE = 3\n")
    stale = validate_release_gate_evidence(tmp_path)
    assert stale["status"] == "blocked"
    assert any(issue["code"] == "release_gate_source_stale" for issue in stale["issues"])


def test_release_gate_evidence_missing_is_nonpassing(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    assert validate_release_gate_evidence(tmp_path)["status"] == "missing"


def test_release_gate_evidence_rejects_non_311_python(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    payload = build_release_gate_evidence(
        root=tmp_path,
        commands=_passing_commands(),
        python_version="3.12.1",
        started_at="2026-07-20T00:00:00+00:00",
        completed_at="2026-07-20T00:00:01+00:00",
        wall_time_seconds=1.0,
    )
    assert payload["status"] == "failed"
    atomic_write_evidence(tmp_path / RELEASE_GATE_EVIDENCE_PATH, payload)
    result = validate_release_gate_evidence(tmp_path)
    assert result["status"] == "blocked"
    assert any(issue["code"] == "release_gate_python_unsupported" for issue in result["issues"])


def test_release_gate_evidence_rejects_incomplete_command_set(tmp_path: Path) -> None:
    _release_tree(tmp_path)
    payload = build_release_gate_evidence(
        root=tmp_path,
        commands=[_passing_commands()[0]],
        python_version="3.11.14",
        started_at="2026-07-20T00:00:00+00:00",
        completed_at="2026-07-20T00:00:01+00:00",
        wall_time_seconds=1.0,
    )
    atomic_write_evidence(tmp_path / RELEASE_GATE_EVIDENCE_PATH, payload)
    result = validate_release_gate_evidence(tmp_path)
    assert result["status"] == "blocked"
    assert any(issue["code"] == "release_gate_evidence_commands_invalid" for issue in result["issues"])


def test_release_artifact_manifest_validates_hashes_and_required_packages(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    files = {
        f"research_assistant-{__version__}-py3-none-any.whl": b"wheel",
        f"research_assistant-{__version__}.tar.gz": b"sdist",
        "release_gate_evidence.json": b"evidence",
    }
    rows = []
    for name, raw in files.items():
        (dist / name).write_bytes(raw)
        rows.append({"filename": name, "path": str(dist / name), "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)})
    (dist / "release_artifacts_manifest.json").write_text(json.dumps({
        "schema_version": RELEASE_ARTIFACT_MANIFEST_SCHEMA,
        "created_at": "2026-07-20T00:00:00Z",
        "package_version": __version__,
        "dist_dir": str(dist),
        "artifact_count": len(rows),
        "artifacts": rows,
        "status": "ok",
        "warnings": [],
    }))
    assert validate_release_artifact_manifest(tmp_path)["status"] == "passed"
    (dist / f"research_assistant-{__version__}-py3-none-any.whl").write_bytes(b"changed")
    result = validate_release_artifact_manifest(tmp_path)
    assert result["status"] == "blocked"
    assert any(issue["code"] == "release_artifact_hash_or_size_mismatch" for issue in result["issues"])


def test_release_artifact_manifest_rejects_unlisted_or_malformed_artifacts(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in (
        f"research_assistant-{__version__}-py3-none-any.whl",
        f"research_assistant-{__version__}.tar.gz",
        "release_gate_evidence.json",
    ):
        (dist / name).write_bytes(name.encode())
    (dist / "unlisted.txt").write_text("not in manifest")
    (dist / "release_artifacts_manifest.json").write_text(json.dumps({
        "schema_version": RELEASE_ARTIFACT_MANIFEST_SCHEMA,
        "created_at": "2026-07-20T00:00:00Z",
        "package_version": __version__,
        "dist_dir": str(dist),
        "artifact_count": 3,
        "status": "ok",
        "warnings": [],
        "artifacts": [
            {"filename": "../escape.whl", "path": "ignored", "sha256": "0" * 64, "size": 1},
            {"filename": f"research_assistant-{__version__}.tar.gz", "path": "ignored", "sha256": None, "size": "bad"},
            {"filename": "release_gate_evidence.json", "path": "ignored", "sha256": "0" * 64, "size": 1},
        ],
    }))

    result = validate_release_artifact_manifest(tmp_path)

    assert result["status"] == "blocked"
    codes = {issue["code"] for issue in result["issues"]}
    assert "release_artifact_filename_invalid" in codes
    assert "release_artifact_row_fields_invalid" in codes
    assert "release_artifact_unlisted_file" in codes
    assert "release_artifact_wheel_missing" in codes
