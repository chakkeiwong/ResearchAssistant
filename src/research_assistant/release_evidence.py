from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from research_assistant import __version__
from research_assistant.core_utils import atomic_write_bytes, canonical_json_bytes, sha256_bytes, utc_now_iso


RELEASE_GATE_EVIDENCE_SCHEMA = "research-assistant-release-gate-evidence-v1"
RELEASE_GATE_EVIDENCE_PATH = Path("dist/release_gate_evidence.json")
RELEASE_GATE_COMMAND_NAMES = (
    "static_checks",
    "fast_tests",
    "bounded_tests",
    "active_full_suite",
    "packaging_smoke",
    "build_release_artifacts",
    "clean_install_smoke",
    "release_smoke",
)
RELEASE_ARTIFACT_MANIFEST_SCHEMA = "individual-release-artifacts-v1"
RELEASE_ARTIFACT_MANIFEST_FIELDS = {
    "schema_version",
    "created_at",
    "package_version",
    "dist_dir",
    "artifact_count",
    "artifacts",
    "status",
    "warnings",
}

_ROOT_FILES = (
    "CHANGELOG.md",
    "CLAUDE.md",
    "README.md",
    "pyproject.toml",
)
_RELEASE_DOCS = (
    "docs/installation.md",
    "docs/known_limitations.md",
    "docs/maintainer_guide.md",
    "docs/platform_support.md",
    "docs/product_spec.md",
    "docs/quickstart.md",
    "docs/release_checklist.md",
    "docs/release_notes_0.1.0.md",
    "docs/release_readiness.md",
    "docs/release/publication_runbook.md",
    "docs/support.md",
    "docs/validation_scripts.md",
)
_CI_FILES = (".github/workflows/python-311-release.yml",)
_EXTENSIONLESS_RELEASE_SCRIPTS = {"ra-agent", "ra-dev", "ra-mcp-dev"}


@dataclass(frozen=True)
class SourceFingerprint:
    sha256: str
    file_count: int
    total_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha256": self.sha256,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
        }


def release_source_paths(root: Path) -> list[Path]:
    candidates: list[Path] = []
    candidates.extend(root / name for name in _ROOT_FILES)
    candidates.extend(root / name for name in _RELEASE_DOCS)
    candidates.extend(root / name for name in _CI_FILES)
    candidates.extend((root / "src").rglob("*.py"))
    candidates.extend(
        path
        for path in (root / "scripts").rglob("*")
        if path.is_file()
        and (path.suffix in {".py", ".sh"} or path.name in _EXTENSIONLESS_RELEASE_SCRIPTS)
    )
    candidates.extend((root / "tests").rglob("*.py"))
    return sorted(
        {path.resolve() for path in candidates if path.is_file()},
        key=lambda path: path.relative_to(root.resolve()).as_posix(),
    )


def release_source_fingerprint(root: Path) -> SourceFingerprint:
    release_root = root.resolve()
    digest = hashlib.sha256()
    total_bytes = 0
    paths = release_source_paths(release_root)
    for path in paths:
        relative = path.relative_to(release_root).as_posix()
        raw = path.read_bytes()
        total_bytes += len(raw)
        executable = bool(path.stat().st_mode & 0o111)
        row = {
            "path": relative,
            "size_bytes": len(raw),
            "sha256": sha256_bytes(raw),
            "executable": executable,
        }
        digest.update(canonical_json_bytes(row))
    return SourceFingerprint(
        sha256=digest.hexdigest(),
        file_count=len(paths),
        total_bytes=total_bytes,
    )


def build_release_gate_evidence(
    *,
    root: Path,
    commands: Iterable[dict[str, Any]],
    python_version: str,
    started_at: str,
    completed_at: str,
    wall_time_seconds: float,
) -> dict[str, Any]:
    command_rows = list(commands)
    passed = (
        bool(command_rows)
        and all(row.get("returncode") == 0 for row in command_rows)
        and _is_python_311(python_version)
    )
    return {
        "schema_version": RELEASE_GATE_EVIDENCE_SCHEMA,
        "status": "passed" if passed else "failed",
        "started_at": started_at,
        "completed_at": completed_at,
        "wall_time_seconds": round(wall_time_seconds, 6),
        "python_version": python_version,
        "artifact_paths": {"release_gate_evidence": str(RELEASE_GATE_EVIDENCE_PATH)},
        "source_fingerprint": release_source_fingerprint(root).to_dict(),
        "commands": command_rows,
        "what_is_not_concluded": [
            "native-Windows support",
            "shared or hosted deployment readiness",
            "scientific correctness or literature completeness",
            "PDF equation, citation, or abstract correctness",
        ],
    }


def validate_release_gate_evidence(root: Path) -> dict[str, Any]:
    release_root = root.resolve()
    path = release_root / RELEASE_GATE_EVIDENCE_PATH
    if not path.is_file():
        return {
            "status": "missing",
            "path": str(path),
            "source_matches": False,
            "issues": [{"code": "release_gate_evidence_missing"}],
        }
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "path": str(path),
            "source_matches": False,
            "issues": [{"code": "release_gate_evidence_invalid", "message": str(exc)}],
        }
    required = {
        "schema_version",
        "status",
        "started_at",
        "completed_at",
        "wall_time_seconds",
        "python_version",
        "artifact_paths",
        "source_fingerprint",
        "commands",
        "what_is_not_concluded",
    }
    issues = []
    if not isinstance(payload, dict) or set(payload) != required:
        issues.append({"code": "release_gate_evidence_schema_invalid"})
    elif payload.get("schema_version") != RELEASE_GATE_EVIDENCE_SCHEMA:
        issues.append({"code": "release_gate_evidence_schema_version_invalid"})
    commands = payload.get("commands") if isinstance(payload, dict) else None
    if not isinstance(commands, list) or not commands:
        issues.append({"code": "release_gate_evidence_commands_invalid"})
    else:
        observed_names = [row.get("name") for row in commands if isinstance(row, dict)]
        if observed_names != list(RELEASE_GATE_COMMAND_NAMES) or any(
            not _valid_command_row(row) for row in commands
        ):
            issues.append({
                "code": "release_gate_evidence_commands_invalid",
                "expected_names": list(RELEASE_GATE_COMMAND_NAMES),
                "observed_names": observed_names,
            })
        elif any(row["returncode"] != 0 for row in commands):
            issues.append({"code": "release_gate_command_failed"})
    if isinstance(payload, dict) and payload.get("artifact_paths") != {
        "release_gate_evidence": str(RELEASE_GATE_EVIDENCE_PATH)
    }:
        issues.append({"code": "release_gate_artifact_paths_invalid"})
    expected = release_source_fingerprint(release_root).to_dict()
    observed = payload.get("source_fingerprint") if isinstance(payload, dict) else None
    source_matches = observed == expected
    if not source_matches:
        issues.append({
            "code": "release_gate_source_stale",
            "expected": expected,
            "observed": observed,
        })
    if isinstance(payload, dict) and payload.get("status") != "passed":
        issues.append({"code": "release_gate_status_not_passed", "status": payload.get("status")})
    if isinstance(payload, dict) and not _is_python_311(payload.get("python_version")):
        issues.append({"code": "release_gate_python_unsupported", "python_version": payload.get("python_version")})
    return {
        "status": "passed" if not issues else "blocked",
        "path": str(path),
        "source_matches": source_matches,
        "issues": issues,
        "evidence": payload,
    }


def validate_release_artifact_manifest(root: Path) -> dict[str, Any]:
    """Validate generated artifact hashes and filenames without trusting paths."""
    release_root = root.resolve()
    manifest_path = release_root / "dist" / "release_artifacts_manifest.json"
    if not manifest_path.is_file():
        return {
            "status": "missing",
            "path": str(manifest_path),
            "issues": [{"code": "release_artifact_manifest_missing"}],
        }
    try:
        payload = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked",
            "path": str(manifest_path),
            "issues": [{"code": "release_artifact_manifest_invalid", "message": str(exc)}],
        }
    issues: list[dict[str, Any]] = []
    if (
        not isinstance(payload, dict)
        or set(payload) != RELEASE_ARTIFACT_MANIFEST_FIELDS
        or payload.get("schema_version") != RELEASE_ARTIFACT_MANIFEST_SCHEMA
    ):
        issues.append({"code": "release_artifact_manifest_schema_invalid"})
        artifacts: list[Any] = []
    else:
        if isinstance(payload.get("artifacts"), list):
            artifacts = payload["artifacts"]
        else:
            artifacts = []
            issues.append({"code": "release_artifact_manifest_artifacts_invalid"})
        if payload.get("package_version") != __version__:
            issues.append({
                "code": "release_artifact_manifest_version_invalid",
                "expected": __version__,
                "observed": payload.get("package_version"),
            })
        if payload.get("status") != "ok":
            issues.append({"code": "release_artifact_manifest_status_invalid", "status": payload.get("status")})
        if not isinstance(payload.get("created_at"), str) or not isinstance(payload.get("dist_dir"), str):
            issues.append({"code": "release_artifact_manifest_metadata_invalid"})
        if payload.get("warnings") != []:
            issues.append({"code": "release_artifact_manifest_warnings_invalid"})
        if payload.get("artifact_count") != len(artifacts):
            issues.append({"code": "release_artifact_manifest_count_invalid"})
    filenames: list[str] = []
    for row in artifacts:
        if not isinstance(row, dict) or set(row) != {"filename", "path", "sha256", "size"}:
            issues.append({"code": "release_artifact_manifest_row_invalid"})
            continue
        filename = row["filename"]
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in {".", ".."}
        ):
            issues.append({"code": "release_artifact_filename_invalid", "filename": filename})
            continue
        filenames.append(filename)
        if (
            not isinstance(row["path"], str)
            or Path(row["path"]).name != filename
            or not isinstance(row["sha256"], str)
            or len(row["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in row["sha256"])
            or not isinstance(row["size"], int)
            or isinstance(row["size"], bool)
            or row["size"] < 0
        ):
            issues.append({"code": "release_artifact_row_fields_invalid", "filename": filename})
            continue
        artifact_path = manifest_path.parent / filename
        try:
            artifact_path.resolve().relative_to(manifest_path.parent.resolve())
        except ValueError:
            issues.append({"code": "release_artifact_path_escape", "filename": filename})
            continue
        if not artifact_path.is_file():
            issues.append({"code": "release_artifact_missing", "filename": filename})
            continue
        try:
            raw = artifact_path.read_bytes()
        except OSError as exc:
            issues.append({"code": "release_artifact_unreadable", "filename": filename, "message": str(exc)})
            continue
        if row["size"] != len(raw) or row["sha256"] != sha256_bytes(raw):
            issues.append({"code": "release_artifact_hash_or_size_mismatch", "filename": filename})
    if len(filenames) != len(set(filenames)):
        issues.append({"code": "release_artifact_manifest_duplicate_filename"})
    actual_filenames = {
        path.name
        for path in manifest_path.parent.iterdir()
        if path.is_file() and path.name != manifest_path.name
    }
    listed_filenames = set(filenames)
    for filename in sorted(actual_filenames - listed_filenames):
        issues.append({"code": "release_artifact_unlisted_file", "filename": filename})
    package_files = [name for name in filenames if name.endswith((".whl", ".tar.gz"))]
    wheel_files = [name for name in package_files if name.endswith(".whl")]
    sdist_files = [name for name in package_files if name.endswith(".tar.gz")]
    if not wheel_files:
        issues.append({"code": "release_artifact_wheel_missing"})
    elif len(wheel_files) != 1:
        issues.append({"code": "release_artifact_wheel_count_invalid", "count": len(wheel_files)})
    if not sdist_files:
        issues.append({"code": "release_artifact_sdist_missing"})
    elif len(sdist_files) != 1:
        issues.append({"code": "release_artifact_sdist_count_invalid", "count": len(sdist_files)})
    if not any(name.startswith(f"research_assistant-{__version__}-") and name.endswith(".whl") for name in package_files):
        issues.append({"code": "release_artifact_wheel_version_invalid", "expected": __version__})
    if f"research_assistant-{__version__}.tar.gz" not in package_files:
        issues.append({"code": "release_artifact_sdist_version_invalid", "expected": __version__})
    allowed_files = {
        "release_gate_evidence.json",
        f"research_assistant-{__version__}.tar.gz",
        *(
            name
            for name in filenames
            if name.startswith(f"research_assistant-{__version__}-") and name.endswith(".whl")
        ),
    }
    for filename in sorted(set(filenames) - allowed_files):
        issues.append({"code": "release_artifact_unexpected_file", "filename": filename})
    evidence = release_root / RELEASE_GATE_EVIDENCE_PATH
    if evidence.is_file() and "release_gate_evidence.json" not in filenames:
        issues.append({"code": "release_artifact_evidence_missing_from_manifest"})
    return {
        "status": "passed" if not issues else "blocked",
        "path": str(manifest_path),
        "issues": issues,
        "artifact_count": len(artifacts),
        "filenames": filenames,
    }


def atomic_write_evidence(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_bytes(path, canonical_json_bytes(payload) + b"\n")


def _canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _is_python_311(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split(".")
    return len(parts) >= 2 and parts[:2] == ["3", "11"]


def _valid_command_row(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "name",
        "command",
        "returncode",
        "wall_time_seconds",
    }:
        return False
    command = value["command"]
    wall_time = value["wall_time_seconds"]
    return (
        isinstance(value["name"], str)
        and isinstance(command, list)
        and bool(command)
        and all(isinstance(part, str) and part for part in command)
        and isinstance(value["returncode"], int)
        and not isinstance(value["returncode"], bool)
        and isinstance(wall_time, (int, float))
        and not isinstance(wall_time, bool)
        and wall_time >= 0
    )
