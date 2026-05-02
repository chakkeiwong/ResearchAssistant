from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import io
import json
import os
import platform
import shutil
import sys
import tarfile
import time
import tomllib

from research_assistant import __version__
from research_assistant.config import AppPaths, get_paths
from research_assistant.industrial.platform import (
    build_artifact_index,
    build_governance_record,
    build_readiness_report,
    build_traceability_report,
    create_derivation,
    create_experiment,
    create_model_policy,
    link_claim_to_experiment,
    record_experiment_run,
    update_derivation,
    validate_industrial_artifacts,
)
from research_assistant.schemas.artifact import SCHEMA_VERSION, base_artifact, stable_id
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.storage.file_store import FileStore

CONFIG_SCHEMA_VERSION = "individual-release-config-v1"
WORKSPACE_SCHEMA_VERSION = "individual-release-workspace-v1"
BACKUP_MANIFEST_NAME = "research_assistant_backup_manifest.json"
DEMO_PAPER_ID = "demo_transport_paper"
RELEASE_REPORT_SCHEMA_VERSION = "individual-release-report-v2"
BACKUP_SCHEMA_VERSION = "individual-release-backup-v1"

CONFIG_KEYS = {
    "workspace_root",
    "default_timeout_seconds",
    "offline_mode",
    "parser_preferences",
    "export_directory",
    "providers",
    "validation_tier",
    "schema_version",
}

OPTIONAL_TOOLS = ["pdftotext", "markitdown", "marker_single", "magic-pdf"]
BENCHMARK_EXPECTED_FIELDS = [
    "title",
    "authors",
    "year",
    "abstract",
    "section_headings",
    "equations",
    "theorem_like_blocks",
    "citations",
]

RELEASE_DOCS = [
    "docs/installation.md",
    "docs/quickstart.md",
    "docs/workflows/individual_research_workflow.md",
    "docs/workflows/git_sharing_workflow.md",
    "docs/workflows/git_sharing_walkthrough.md",
    "docs/troubleshooting.md",
    "docs/privacy.md",
    "docs/release_checklist.md",
    "docs/onboarding_trial.md",
    "docs/known_limitations.md",
    "docs/platform_support.md",
    "docs/support.md",
    "docs/release_notes_0.1.0.md",
    "docs/release_notes_template.md",
    ".github/ISSUE_TEMPLATE/individual_release_bug.md",
]

RELEASE_SCRIPTS = [
    "scripts/run_fast_tests.sh",
    "scripts/run_bounded_tests.sh",
    "scripts/run_release_smoke.sh",
    "scripts/run_packaging_smoke.sh",
    "scripts/run_clean_install_smoke.sh",
    "scripts/build_release_artifacts.sh",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True))


def config_dir(root: Path | None = None) -> Path:
    return get_paths(root).root / ".research-assistant"


def config_path(root: Path | None = None) -> Path:
    return config_dir(root) / "config.json"


def demo_marker_path(root: Path | None = None) -> Path:
    return config_dir(root) / "demo.json"


def default_config(root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "workspace_root": str(paths.root),
        "default_timeout_seconds": 300,
        "offline_mode": True,
        "parser_preferences": {
            "prefer_structured_source": True,
            "pdf_fallback_enabled": True,
        },
        "export_directory": str(paths.exports),
        "providers": {
            "enabled": False,
            "allowed": [],
            "notes": "Live providers and LLM calls are disabled by default.",
        },
        "validation_tier": "bounded",
    }


def _workspace_dirs(paths: AppPaths) -> list[Path]:
    return [
        paths.local_research,
        paths.analysis,
        paths.papers_raw,
        paths.papers_extracted,
        paths.papers_source,
        paths.papers_source / "records",
        paths.metadata,
        paths.summaries,
        paths.links,
        paths.reviews,
        paths.review_metadata,
        paths.indices,
        paths.caches,
        paths.derivations,
        paths.experiments,
        paths.graph_reports,
        paths.benchmarks,
        paths.benchmark_runs,
        paths.synthesis,
        paths.governance,
        paths.jobs,
        paths.exports,
        paths.traceability,
        paths.model_policies,
        paths.collaboration,
        paths.artifact_indices,
        paths.service_contracts,
        paths.operations,
        paths.sops,
        paths.exports / "backups",
    ]


def init_workspace(*, root: Path | None = None, force: bool = False) -> dict[str, Any]:
    paths = get_paths(root)
    created_dirs = []
    for directory in _workspace_dirs(paths):
        existed = directory.exists()
        directory.mkdir(parents=True, exist_ok=True)
        if not existed:
            created_dirs.append(str(directory))

    config_dir(root).mkdir(parents=True, exist_ok=True)
    cfg_path = config_path(root)
    wrote_config = False
    config_existed = cfg_path.exists()
    if force or not config_existed:
        atomic_write_json(cfg_path, default_config(root))
        wrote_config = True

    return {
        "status": "initialized" if created_dirs or wrote_config else "already_initialized",
        "workspace_root": str(paths.root),
        "local_research": str(paths.local_research),
        "config_path": str(cfg_path),
        "created_directories": created_dirs,
        "config_written": wrote_config,
        "config_existed": config_existed,
        "offline_mode": True,
        "next_recommended_command": "ra doctor",
        "destructive": False,
    }


def load_config(*, root: Path | None = None) -> dict[str, Any]:
    path = config_path(root)
    if not path.exists():
        payload = default_config(root)
        payload["_config_exists"] = False
        payload["_config_path"] = str(path)
        return payload
    payload = json.loads(path.read_text())
    payload["_config_exists"] = True
    payload["_config_path"] = str(path)
    return payload


def validate_config(*, root: Path | None = None) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    try:
        cfg = load_config(root=root)
    except json.JSONDecodeError as exc:
        return {
            "status": "blocked",
            "config_path": str(config_path(root)),
            "issues": [{"severity": "blocker", "code": "invalid_json", "message": str(exc)}],
        }

    if not cfg.get("_config_exists"):
        issues.append({"severity": "warning", "code": "config_missing", "message": "run ra init to create a local config"})
    unknown = sorted(set(cfg) - CONFIG_KEYS - {"_config_exists", "_config_path"})
    if unknown:
        issues.append({"severity": "warning", "code": "unknown_config_keys", "keys": unknown})
    if cfg.get("schema_version") != CONFIG_SCHEMA_VERSION:
        issues.append({"severity": "warning", "code": "config_schema_mismatch", "expected": CONFIG_SCHEMA_VERSION, "found": cfg.get("schema_version")})
    timeout = cfg.get("default_timeout_seconds")
    if not isinstance(timeout, int) or timeout <= 0:
        issues.append({"severity": "blocker", "code": "invalid_timeout", "message": "default_timeout_seconds must be a positive integer"})
    if cfg.get("offline_mode") is not True:
        issues.append({"severity": "warning", "code": "offline_mode_disabled", "message": "offline_mode should remain true for the individual release"})
    providers = cfg.get("providers")
    if not isinstance(providers, dict):
        issues.append({"severity": "blocker", "code": "invalid_providers", "message": "providers must be an object"})
    elif providers.get("enabled") is True:
        issues.append({"severity": "warning", "code": "providers_enabled", "message": "providers are expected to be disabled by default"})

    blocker_count = len([issue for issue in issues if issue["severity"] == "blocker"])
    warning_count = len([issue for issue in issues if issue["severity"] == "warning"])
    return {
        "status": "blocked" if blocker_count else ("warnings" if warning_count else "ok"),
        "config_path": cfg.get("_config_path"),
        "config_exists": cfg.get("_config_exists"),
        "issues": issues,
    }


def show_config(*, root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(root=root)
    validation = validate_config(root=root)
    return {
        "config_path": cfg.pop("_config_path"),
        "config_exists": cfg.pop("_config_exists"),
        "config": cfg,
        "validation": validation,
    }


def _parse_config_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def set_config_value(key: str, value: str, *, root: Path | None = None) -> dict[str, Any]:
    if key not in CONFIG_KEYS and key != "providers.enabled":
        raise ValueError(f"unknown config key {key}")
    init_workspace(root=root)
    path = config_path(root)
    cfg = json.loads(path.read_text())
    parsed = _parse_config_value(value)
    if key == "providers.enabled":
        cfg.setdefault("providers", {})["enabled"] = parsed
    else:
        cfg[key] = parsed
    atomic_write_json(path, cfg)
    return show_config(root=root)


def version_payload() -> dict[str, Any]:
    return {
        "package": "research-assistant",
        "version": __version__,
        "python": platform.python_version(),
        "workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "industrial_artifact_schema_version": SCHEMA_VERSION,
    }


def version_consistency(*, release_root: Path | None = None) -> dict[str, Any]:
    root = release_root or _release_material_root()
    issues: list[dict[str, Any]] = []
    pyproject_path = root / "pyproject.toml"
    changelog_path = root / "CHANGELOG.md"
    pyproject_version = None
    script_entry = None
    if pyproject_path.exists():
        try:
            pyproject = tomllib.loads(pyproject_path.read_text())
            pyproject_version = pyproject.get("project", {}).get("version")
            script_entry = pyproject.get("project", {}).get("scripts", {}).get("ra")
        except tomllib.TOMLDecodeError as exc:
            issues.append({"severity": "blocker", "code": "pyproject_unreadable", "message": str(exc)})
        if pyproject_version != __version__:
            issues.append({"severity": "blocker", "code": "version_mismatch", "pyproject": pyproject_version, "package": __version__})
        if script_entry != "research_assistant.cli:main":
            issues.append({"severity": "blocker", "code": "ra_entrypoint_missing", "entry": script_entry})
    else:
        issues.append({
            "severity": "warning",
            "code": "pyproject_not_available",
            "message": "pyproject.toml is not available from this installed-package context; package version is reported from the installed module.",
        })
    changelog_text = changelog_path.read_text() if changelog_path.exists() else ""
    if f"## {__version__}" not in changelog_text:
        issues.append({"severity": "warning", "code": "changelog_missing_version", "version": __version__})
    blocker_count = len([issue for issue in issues if issue["severity"] == "blocker"])
    warning_count = len([issue for issue in issues if issue["severity"] == "warning"])
    return {
        "status": "blocked" if blocker_count else ("warnings" if warning_count else "ok"),
        "package_version": __version__,
        "pyproject_version": pyproject_version,
        "ra_entrypoint": script_entry,
        "changelog_has_version": f"## {__version__}" in changelog_text,
        "release_material_root": str(root),
        "issues": issues,
    }


def workspace_validate(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    missing_dirs = [str(path) for path in _workspace_dirs(paths) if not path.exists()]
    config_validation = validate_config(root=root)
    industrial_validation = validate_industrial_artifacts(root=paths.root)
    issues: list[dict[str, Any]] = []
    if missing_dirs:
        issues.append({"severity": "warning", "code": "missing_directories", "paths": missing_dirs})
    if config_validation["status"] == "blocked":
        issues.append({"severity": "blocker", "code": "config_blocked", "details": config_validation["issues"]})
    elif config_validation["status"] == "warnings":
        issues.append({"severity": "warning", "code": "config_warnings", "details": config_validation["issues"]})
    if industrial_validation["issue_counts"]["blockers"]:
        issues.append({"severity": "blocker", "code": "industrial_artifact_blockers", "count": industrial_validation["issue_counts"]["blockers"]})
    if industrial_validation["issue_counts"]["warnings"]:
        issues.append({"severity": "warning", "code": "industrial_artifact_warnings", "count": industrial_validation["issue_counts"]["warnings"]})
    blocker_count = len([issue for issue in issues if issue["severity"] == "blocker"])
    warning_count = len([issue for issue in issues if issue["severity"] == "warning"])
    return {
        "status": "blocked" if blocker_count else ("warnings" if warning_count else "ok"),
        "workspace_root": str(paths.root),
        "workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
        "missing_directories": missing_dirs,
        "config_validation": config_validation,
        "industrial_validation_summary": {
            "status": industrial_validation["status"],
            "issue_counts": industrial_validation["issue_counts"],
        },
        "issues": issues,
    }


def workspace_migrate(*, root: Path | None = None, dry_run: bool = True) -> dict[str, Any]:
    validation = workspace_validate(root=root)
    return {
        "status": "dry_run_complete" if dry_run else "blocked",
        "dry_run": dry_run,
        "current_workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
        "target_workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
        "migration_needed": False,
        "backup_required": False,
        "workspace_validation_status": validation["status"],
        "planned_actions": [],
        "manual_review_items": validation["issues"],
        "message": "No workspace migration is currently required.",
    }


def workspace_repair(*, root: Path | None = None, dry_run: bool = True) -> dict[str, Any]:
    paths = get_paths(root)
    missing = [path for path in _workspace_dirs(paths) if not path.exists()]
    if not dry_run:
        for path in missing:
            path.mkdir(parents=True, exist_ok=True)
    return {
        "status": "dry_run_complete" if dry_run else "repaired",
        "dry_run": dry_run,
        "missing_directories": [str(path) for path in missing],
        "created_directories": [] if dry_run else [str(path) for path in missing],
        "destructive": False,
    }


def record_timeout_diagnostic(
    *,
    workflow: str,
    timeout_seconds: int,
    root: Path | None = None,
    elapsed_seconds: float | None = None,
) -> dict[str, Any]:
    paths = get_paths(root)
    artifact_id = stable_id("timeout", workflow, timeout_seconds, utc_now_iso())
    payload = {
        **base_artifact(
            artifact_type="bounded_workflow_diagnostic",
            artifact_id=artifact_id,
            provenance={"created_by": "ra bounded-workflow diagnostic"},
            limitations=["Diagnostic records timeout metadata; it does not retry or certify workflow completion."],
        ),
        "workflow": workflow,
        "status": "timed_out",
        "timeout_seconds": timeout_seconds,
        "elapsed_seconds": elapsed_seconds if elapsed_seconds is not None else timeout_seconds,
        "suggested_next_step": "rerun with a smaller fixture or inspect optional parser/tool availability with ra doctor",
        "progress_events": [
            {"event": "started", "workflow": workflow},
            {"event": "timed_out", "timeout_seconds": timeout_seconds},
        ],
    }
    FileStore(paths.local_research).write_json(paths.jobs / f"{artifact_id}.json", payload)
    return payload


def performance_smoke(
    *,
    root: Path | None = None,
    synthetic_count: int = 25,
    include_industrial_artifacts: bool = False,
    include_backup: bool = False,
    include_export: bool = False,
    timeout_seconds: int | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    paths = get_paths(root)
    init_workspace(root=paths.root)
    if synthetic_count < 0:
        raise ValueError("synthetic_count must be non-negative")
    store = FileStore(paths.local_research)
    created = 0
    progress_events = [{"event": "start", "synthetic_count": synthetic_count}]
    start_total = time.monotonic()
    for idx in range(synthetic_count):
        if timeout_seconds is not None and time.monotonic() - start_total > timeout_seconds:
            diagnostic = record_timeout_diagnostic(
                workflow="performance-smoke",
                timeout_seconds=timeout_seconds,
                elapsed_seconds=time.monotonic() - start_total,
                root=paths.root,
            )
            return {
                "status": "blocked",
                "reason": "timeout",
                "timeout_diagnostic_id": diagnostic["artifact_id"],
                "progress_events": progress_events,
                "requires_human_review": True,
            }
        paper_id = f"synthetic_personal_corpus_{idx:04d}"
        path = paths.summaries / f"{paper_id}.json"
        if not path.exists():
            store.write_json(path, {
                "id": paper_id,
                "title": f"Synthetic Personal Corpus Paper {idx}",
                "authors": ["Release Smoke"],
                "year": 2026,
                "abstract": "Synthetic local record for bounded personal-corpus release smoke.",
                "main_contribution": "",
                "review_status": "needs_review",
                "technical_audit": {},
                "provenance": {"synthetic_release_smoke": "true"},
            })
            store.write_json(paths.metadata / f"{paper_id}.json", {
                "identity_validation": {"status": "synthetic_fixture"},
                "synthetic_release_smoke": True,
            })
            store.write_json(paths.papers_source / "records" / f"{paper_id}.json", {
                "paper_id": paper_id,
                "status": "synthetic_fixture",
                "source_type": "synthetic",
                "primary_for_audit": False,
                "sections": [{"title": "Synthetic Method", "labels": [f"sec:synthetic:{idx}"]}],
                "equations": [{"labels": [f"eq:synthetic:{idx}"], "raw_latex": "x_i"}],
                "theorem_like_blocks": [],
                "labels": [{"key": f"sec:synthetic:{idx}"}, {"key": f"eq:synthetic:{idx}"}],
                "citations": [],
                "bibliography": [],
                "macros": [],
                "provenance": {"synthetic_release_smoke": True},
                "limitations": ["Synthetic record for release performance smoke."],
            })
            if include_industrial_artifacts:
                derivation = create_derivation(paper_id, title="Synthetic release worksheet", root=paths.root)
                derivation = update_derivation(derivation["artifact_id"], "paper_claims", "Synthetic claim for release smoke.", root=paths.root)
                claim_id = derivation["paper_claims"][0]["id"]
                experiment = create_experiment(paper_id, claim_id=claim_id, checklist_id="gradient_checks", root=paths.root)
                record_experiment_run(
                    experiment["artifact_id"],
                    run_label="synthetic-smoke",
                    seed=str(idx),
                    environment="synthetic-local",
                    diagnostics=["synthetic diagnostic"],
                    result_summary="Synthetic run evidence.",
                    acceptance_status="requires_review",
                    dataset_hash=f"synthetic-data-{idx}",
                    model_hash=f"synthetic-model-{idx}",
                    root=paths.root,
                )
            created += 1
    progress_events.append({"event": "records_ready", "created_records": created})

    start = datetime.now(timezone.utc)
    validation = workspace_validate(root=paths.root)
    validation_elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    index_elapsed = None
    export_elapsed = None
    backup_elapsed = None
    backup_size = None
    index_payload = None
    export_path = None
    backup_payload = None

    index_start = time.monotonic()
    index_payload = build_artifact_index("release_performance_smoke_index", root=paths.root)
    index_elapsed = time.monotonic() - index_start
    progress_events.append({"event": "artifact_index_built", "elapsed_seconds": round(index_elapsed, 6)})

    if include_export:
        from research_assistant.adapters.workspace_exports import export_paper_context

        export_path = paths.exports / "release_performance_context.json"
        export_start = time.monotonic()
        export_paper_context(export_path, root=paths.root)
        export_elapsed = time.monotonic() - export_start
        progress_events.append({"event": "context_exported", "elapsed_seconds": round(export_elapsed, 6)})

    if include_backup:
        backup_start = time.monotonic()
        backup_payload = create_backup(root=paths.root)
        backup_elapsed = time.monotonic() - backup_start
        backup_size = Path(backup_payload["backup_path"]).stat().st_size
        progress_events.append({"event": "backup_created", "elapsed_seconds": round(backup_elapsed, 6)})

    warning_threshold_seconds = max(1.0, synthetic_count * 0.05)
    warnings = []
    if validation_elapsed > warning_threshold_seconds:
        warnings.append({"code": "validation_slow", "elapsed_seconds": round(validation_elapsed, 6)})
    if include_backup and backup_elapsed is not None and backup_elapsed > max(2.0, synthetic_count * 0.05):
        warnings.append({"code": "backup_slow", "elapsed_seconds": round(backup_elapsed, 6)})
    payload = {
        "status": "warnings" if warnings else "ok",
        "workspace_root": str(paths.root),
        "synthetic_count": synthetic_count,
        "created_records": created,
        "include_industrial_artifacts": include_industrial_artifacts,
        "include_backup": include_backup,
        "include_export": include_export,
        "validation_status": validation["status"],
        "validation_elapsed_seconds": round(validation_elapsed, 6),
        "artifact_index_elapsed_seconds": round(index_elapsed, 6) if index_elapsed is not None else None,
        "artifact_index_id": index_payload["artifact_id"] if index_payload else None,
        "export_elapsed_seconds": round(export_elapsed, 6) if export_elapsed is not None else None,
        "export_path": str(export_path) if export_path else None,
        "backup_elapsed_seconds": round(backup_elapsed, 6) if backup_elapsed is not None else None,
        "backup_path": backup_payload["backup_path"] if backup_payload else None,
        "backup_size_bytes": backup_size,
        "warning_threshold_seconds": warning_threshold_seconds,
        "warnings": warnings,
        "progress_events": progress_events,
        "requires_human_review": True,
        "limitations": ["Synthetic corpus smoke checks local validation overhead, not real search/index performance."],
    }
    if output is not None:
        atomic_write_json(output, payload)
    report = {
        **base_artifact(
            artifact_type="release_performance_smoke_report",
            artifact_id=stable_id("performance_smoke", synthetic_count, include_industrial_artifacts, include_backup, include_export),
            provenance={"created_by": "ra performance smoke"},
            limitations=payload["limitations"],
        ),
        **payload,
    }
    FileStore(paths.local_research).write_json(paths.jobs / f"{report['artifact_id']}.json", report)
    payload["report_artifact_id"] = report["artifact_id"]
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_files(root: Path, output: Path) -> list[Path]:
    files = []
    backup_dir = get_paths(root).exports / "backups"
    for base in [root / "local_research", root / ".research-assistant"]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.resolve() != output.resolve() and backup_dir not in path.parents:
                files.append(path)
    return files


def create_backup(*, root: Path | None = None, output: Path | None = None) -> dict[str, Any]:
    init_workspace(root=root)
    paths = get_paths(root)
    backup_dir = paths.exports / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    out = output or (backup_dir / f"research_assistant_backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.tar.gz")
    out.parent.mkdir(parents=True, exist_ok=True)
    files = _backup_files(paths.root, out)
    manifest = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "created_at": utc_now_iso(),
        "workspace_root": str(paths.root),
        "package_version": __version__,
        "file_count": len(files),
        "files": [
            {"path": str(path.relative_to(paths.root)), "sha256": _sha256(path), "size": path.stat().st_size}
            for path in files
        ],
    }
    with tarfile.open(out, "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=str(path.relative_to(paths.root)))
        data = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        info = tarfile.TarInfo(BACKUP_MANIFEST_NAME)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return {
        "status": "created",
        "backup_path": str(out),
        "manifest": manifest,
        "destructive": False,
    }


def _validate_backup_members(path: Path) -> tuple[list[tarfile.TarInfo], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
    for member in members:
        name = member.name
        if name.startswith("/") or Path(name).is_absolute() or ".." in Path(name).parts:
            issues.append({"severity": "blocker", "code": "unsafe_archive_path", "path": name})
        if not (name == BACKUP_MANIFEST_NAME or name.startswith("local_research/") or name.startswith(".research-assistant/")):
            issues.append({"severity": "blocker", "code": "unexpected_archive_path", "path": name})
    return members, issues


def inspect_backup(path: Path) -> dict[str, Any]:
    try:
        members, issues = _validate_backup_members(path)
        with tarfile.open(path, "r:gz") as archive:
            try:
                member = archive.getmember(BACKUP_MANIFEST_NAME)
            except KeyError:
                return {"status": "blocked", "backup_path": str(path), "issues": [{"severity": "blocker", "code": "manifest_missing"}] + issues}
            extracted = archive.extractfile(member)
            if extracted is None:
                return {"status": "blocked", "backup_path": str(path), "issues": [{"severity": "blocker", "code": "manifest_unreadable"}] + issues}
            manifest = json.loads(extracted.read().decode("utf-8"))
            file_rows = manifest.get("files", [])
            for row in file_rows:
                row_path = row.get("path")
                if not row_path:
                    issues.append({"severity": "blocker", "code": "manifest_file_path_missing"})
                    continue
                if row_path.startswith("/") or Path(row_path).is_absolute() or ".." in Path(row_path).parts:
                    issues.append({"severity": "blocker", "code": "unsafe_manifest_path", "path": row_path})
                    continue
                try:
                    file_member = archive.getmember(row_path)
                except KeyError:
                    issues.append({"severity": "blocker", "code": "manifest_file_missing", "path": row_path})
                    continue
                extracted_file = archive.extractfile(file_member)
                if extracted_file is None:
                    issues.append({"severity": "blocker", "code": "manifest_file_unreadable", "path": row_path})
                    continue
                digest = hashlib.sha256(extracted_file.read()).hexdigest()
                if row.get("sha256") and digest != row.get("sha256"):
                    issues.append({"severity": "blocker", "code": "hash_mismatch", "path": row_path})
    except (tarfile.TarError, OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "backup_path": str(path), "issues": [{"severity": "blocker", "code": "backup_unreadable", "message": str(exc)}]}
    blocker_count = len([issue for issue in issues if issue["severity"] == "blocker"])
    return {
        "status": "blocked" if blocker_count else "ok",
        "backup_path": str(path),
        "manifest": manifest,
        "member_count": len(members),
        "issues": issues,
    }


def _target_has_restore_conflicts(root: Path, manifest: dict[str, Any]) -> list[str]:
    return [
        row["path"] for row in manifest.get("files", [])
        if (root / row["path"]).exists()
    ]


def restore_backup(
    path: Path,
    *,
    root: Path | None = None,
    dry_run: bool = True,
    confirm_restore: bool = False,
    allow_overwrite: bool = False,
    backup_current_first: bool = True,
) -> dict[str, Any]:
    """Restore a local backup only after explicit safety checks.

    Restore is intentionally dry-run by default. A real restore needs an
    explicit confirmation, and overwrites need an additional opt-in so release
    users cannot accidentally replace a research workspace while inspecting a
    backup archive.
    """
    inspection = inspect_backup(path)
    if inspection["status"] != "ok":
        return inspection
    paths = get_paths(root)
    manifest = inspection["manifest"]
    would_overwrite = _target_has_restore_conflicts(paths.root, manifest)
    base_report = {
        "dry_run": dry_run,
        "backup_path": str(path),
        "restore_root": str(paths.root),
        "file_count": manifest.get("file_count", 0),
        "would_overwrite_count": len(would_overwrite),
        "would_overwrite": would_overwrite[:50],
        "allow_overwrite": allow_overwrite,
        "confirm_restore": confirm_restore,
    }
    if dry_run:
        return {**base_report, "status": "dry_run_complete", "message": "Dry-run only; pass --no-dry-run --confirm-restore to restore."}
    if not confirm_restore:
        return {**base_report, "status": "blocked", "issues": [{"severity": "blocker", "code": "restore_confirmation_required"}]}
    if would_overwrite and not allow_overwrite:
        return {**base_report, "status": "blocked", "issues": [{"severity": "blocker", "code": "overwrite_not_allowed", "count": len(would_overwrite)}]}

    safety_backup = None
    if would_overwrite and backup_current_first:
        safety_backup = create_backup(root=paths.root)["backup_path"]

    restored = []
    skipped = []
    with tarfile.open(path, "r:gz") as archive:
        for row in manifest.get("files", []):
            rel_path = row["path"]
            target = paths.root / rel_path
            if target.exists() and not allow_overwrite:
                skipped.append(rel_path)
                continue
            member = archive.getmember(rel_path)
            extracted = archive.extractfile(member)
            if extracted is None:
                skipped.append(rel_path)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            data = extracted.read()
            tmp = target.with_name(f".{target.name}.restore-tmp")
            with tmp.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(target)
            restored.append(rel_path)

    post_restore_init = init_workspace(root=paths.root)
    report = {
        **base_report,
        "status": "restored",
        "restored_file_count": len(restored),
        "skipped_file_count": len(skipped),
        "overwritten_file_count": len(would_overwrite),
        "safety_backup_path": safety_backup,
        "restored_files": restored[:50],
        "skipped_files": skipped[:50],
        "hash_validation_status": inspection["status"],
        "post_restore_workspace_init": post_restore_init,
        "warnings": [],
    }
    report_path = paths.exports / "restore_reports" / f"restore_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    atomic_write_json(report_path, report)
    report["restore_report_path"] = str(report_path)
    return report


def _optional_tool_status() -> list[dict[str, Any]]:
    return [
        {"tool": tool, "available": shutil.which(tool) is not None, "required": False}
        for tool in OPTIONAL_TOOLS
    ]


def _tool_map(tools: list[dict[str, Any]]) -> dict[str, bool]:
    return {row["tool"]: bool(row["available"]) for row in tools}


def workflow_readiness(*, root: Path | None = None, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    release_root = _release_material_root()
    tool_rows = tools or _optional_tool_status()
    available = _tool_map(tool_rows)

    def row(name: str, required: list[str], optional: list[str], limitations: list[str]) -> dict[str, Any]:
        missing_required = [tool for tool in required if not available.get(tool)]
        missing_optional = [tool for tool in optional if not available.get(tool)]
        status = "blocked" if missing_required else ("warnings" if missing_optional else "ok")
        return {
            "workflow": name,
            "status": status,
            "required_tools": required,
            "optional_tools": optional,
            "available_tools": [tool for tool in required + optional if available.get(tool)],
            "missing_tools": missing_required + missing_optional,
            "suggested_fix": "install missing required tools" if missing_required else ("optional tools can improve extraction quality" if missing_optional else ""),
            "limitations": limitations,
        }

    benchmark_fixtures = sorted((release_root / "tests" / "fixtures" / "benchmark_papers" / "synthetic").glob("*.expected.json"))
    return {
        "core_local_lifecycle": row("core_local_lifecycle", [], [], ["Uses local JSON files only."]),
        "demo_workflow": row("demo_workflow", [], [], ["Demo evidence remains review material."]),
        "metadata_only_ingest": row("metadata_only_ingest", [], [], ["Network discovery remains an explicit separate workflow."]),
        "pdf_text_ingest": row("pdf_text_ingest", ["pdftotext"], ["markitdown", "marker_single", "magic-pdf"], ["PDF extraction quality depends on local tools and source PDF quality."]),
        "structured_source_inspection": row("structured_source_inspection", [], [], ["Live arXiv fetch is explicit; stored source inspection is local."]),
        "parser_benchmark_smoke": {
            **row("parser_benchmark_smoke", [], OPTIONAL_TOOLS, ["Fixture smoke checks expected metadata presence, not full parser correctness."]),
            "fixture_count": len(benchmark_fixtures),
            "fixture_status": "ok" if benchmark_fixtures else "warnings",
        },
    }


def parser_tool_matrix(*, root: Path | None = None) -> dict[str, Any]:
    tools = _optional_tool_status()
    return {
        "status": "ok",
        "optional_tools": tools,
        "workflow_readiness": workflow_readiness(root=root, tools=tools),
        "privacy": privacy_status(root=root),
        "limitations": ["Tool matrix reports availability and workflow fit; it does not certify parser accuracy."],
    }


def parser_benchmark_smoke(*, root: Path | None = None) -> dict[str, Any]:
    release_root = _release_material_root()
    fixture_dir = release_root / "tests" / "fixtures" / "benchmark_papers" / "synthetic"
    rows = []
    for path in sorted(fixture_dir.glob("*.expected.json")):
        try:
            expected = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            rows.append({"fixture": str(path), "status": "blocked", "issues": [{"code": "invalid_json", "message": str(exc)}]})
            continue
        missing = [field for field in BENCHMARK_EXPECTED_FIELDS if not expected.get(field)]
        score = (len(BENCHMARK_EXPECTED_FIELDS) - len(missing)) / len(BENCHMARK_EXPECTED_FIELDS)
        rows.append({
            "fixture": str(path),
            "status": "passed" if score >= 0.60 else "warnings",
            "quality_score": round(score, 3),
            "missing_expected_fields": missing,
            "limitations": ["Expected fixture completeness only; parser-vs-ground-truth scoring is future work."],
        })
    blockers = [row for row in rows if row["status"] == "blocked"]
    warnings = [row for row in rows if row["status"] == "warnings"]
    if not rows:
        warnings.append({"code": "parser_benchmark_fixtures_missing", "fixture_dir": str(fixture_dir)})
    return {
        "status": "blocked" if blockers else ("warnings" if warnings else "ok"),
        "fixture_count": len(rows),
        "fixtures": rows,
        "warnings": warnings,
        "requires_human_review": True,
    }


def platform_status(*, root: Path | None = None) -> dict[str, Any]:
    system = platform.system()
    release = platform.release()
    release_lower = release.lower()
    is_wsl = system == "Linux" and ("microsoft" in release_lower or "wsl" in release_lower)
    if is_wsl:
        support_tier = "tier_1_linux_wsl"
    elif system == "Linux":
        support_tier = "tier_1_linux"
    elif system == "Darwin":
        support_tier = "tier_2_macos"
    elif system == "Windows":
        support_tier = "tier_3_windows_native_untested"
    else:
        support_tier = "untested"
    return {
        "status": "warnings" if support_tier in {"tier_3_windows_native_untested", "untested"} else "ok",
        "system": system,
        "release": release,
        "machine": platform.machine(),
        "is_wsl": is_wsl,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "support_tier": support_tier,
        "posix_shell_scripts": system in {"Linux", "Darwin"} or is_wsl,
        "workspace_root": str(get_paths(root).root),
        "limitations": ["Platform status is local detection; cross-platform release signoff still requires manual validation."],
    }


def doctor(*, root: Path | None = None, include_matrix: bool = False) -> dict[str, Any]:
    cfg = load_config(root=root)
    validation = workspace_validate(root=root)
    tools = _optional_tool_status()
    warnings = []
    if validation["status"] != "ok":
        warnings.append("workspace has validation warnings or blockers")
    if cfg.get("providers", {}).get("enabled") is True:
        warnings.append("providers are enabled; individual release defaults expect providers disabled")
    payload = {
        "status": "warnings" if warnings else "ok",
        "package_version": __version__,
        "python": platform.python_version(),
        "platform": platform_status(root=root),
        "workspace_root": str(get_paths(root).root),
        "workspace_status": validation["status"],
        "default_timeout_seconds": cfg.get("default_timeout_seconds"),
        "offline_mode": cfg.get("offline_mode") is True,
        "providers_enabled": cfg.get("providers", {}).get("enabled") is True,
        "optional_tools": tools,
        "workflow_readiness": workflow_readiness(root=root, tools=tools),
        "warnings": warnings,
        "suggested_next_commands": ["ra init", "ra demo setup", "ra demo run"],
    }
    if include_matrix:
        payload["parser_tool_matrix"] = parser_tool_matrix(root=root)
    return payload


def privacy_status(*, root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(root=root)
    providers_enabled = cfg.get("providers", {}).get("enabled") is True
    offline_mode = cfg.get("offline_mode") is True
    return {
        "status": "ok" if offline_mode and not providers_enabled else "warning",
        "offline_mode": offline_mode,
        "providers_enabled": providers_enabled,
        "network_required_for_default_workflows": False,
        "live_llm_calls_enabled": False,
        "default_policy": "No default individual-release workflow sends papers or notes to external providers.",
        "requires_human_review": True,
    }


def _write_demo_fixture(root: Path) -> None:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    store.write_json(paths.summaries / f"{DEMO_PAPER_ID}.json", {
        "id": DEMO_PAPER_ID,
        "title": "Demo Transport Map Paper",
        "authors": ["Ada Demo"],
        "year": 2026,
        "abstract": "Fixture paper for the individual release demo.",
        "main_contribution": "Demonstrates local derivation, experiment, traceability, and readiness workflows.",
        "review_status": "needs_review",
        "technical_audit": {
            "claimed_results": [],
            "derived_results": [],
            "open_questions": [],
            "relevant_equations": [],
            "relevant_sections": [],
            "assumptions_for_reuse": [],
        },
    })
    store.write_json(paths.metadata / f"{DEMO_PAPER_ID}.json", {"identity_validation": {"status": "fixture"}})
    store.write_json(paths.papers_source / "records" / f"{DEMO_PAPER_ID}.json", {
        "paper_id": DEMO_PAPER_ID,
        "status": "available",
        "source_type": "fixture_latex",
        "primary_for_audit": True,
        "sections": [{"title": "Method", "labels": ["sec:method"], "line": 7}],
        "equations": [{"labels": ["eq:target"], "raw_latex": "p(x)", "line": 9}],
        "theorem_like_blocks": [{"labels": ["thm:main"], "raw_latex": "Theorem text"}],
        "labels": [{"key": "sec:method"}, {"key": "eq:target"}, {"key": "thm:main"}],
        "citations": [],
        "bibliography": [],
        "macros": [],
        "provenance": {"fixture": True},
        "limitations": [],
    })
    code_dir = root / "demo_code"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "transport_demo.py").write_text("def transport_log_density(x):\n    return -0.5 * x * x\n")


def _workspace_has_user_data(root: Path) -> bool:
    local_research = get_paths(root).local_research
    if not local_research.exists():
        return False
    return any(path.is_file() for path in local_research.rglob("*"))


def demo_setup(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    marker_path = demo_marker_path(paths.root)
    if _workspace_has_user_data(paths.root) and not marker_path.exists():
        return {
            "status": "blocked",
            "reason": "workspace contains existing files and is not marked as a demo workspace",
            "workspace_root": str(paths.root),
            "suggested_next_step": "run demo commands with --root pointing at a fresh demo directory",
        }
    init_payload = init_workspace(root=paths.root)
    _write_demo_fixture(paths.root)
    marker = {
        "demo_workspace": True,
        "created_at": utc_now_iso(),
        "paper_id": DEMO_PAPER_ID,
        "safe_to_clean_with_demo_command": True,
    }
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True))
    return {
        "status": "ready",
        "workspace_root": str(paths.root),
        "paper_id": DEMO_PAPER_ID,
        "init": init_payload,
        "next_recommended_command": "ra demo run",
    }


def demo_run(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    if not (paths.summaries / f"{DEMO_PAPER_ID}.json").exists():
        setup = demo_setup(root=paths.root)
        if setup.get("status") == "blocked":
            return setup
    derivation = create_derivation(DEMO_PAPER_ID, title="Demo target preservation worksheet", template_id="neural_transport_flows", root=paths.root)
    derivation = update_derivation(derivation["artifact_id"], "paper_claims", "The demo map preserves a Gaussian target up to review.", root=paths.root)
    claim_id = derivation["paper_claims"][0]["id"]
    experiment = create_experiment(DEMO_PAPER_ID, claim_id=claim_id, checklist_id="gradient_checks", root=paths.root)
    experiment = record_experiment_run(
        experiment["artifact_id"],
        run_label="demo-smoke",
        seed="0",
        environment="local-demo",
        diagnostics=["fixture diagnostic"],
        result_summary="Demo run records reproducibility evidence only.",
        acceptance_status="requires_review",
        dataset_hash="demo-data",
        model_hash="demo-model",
        root=paths.root,
    )
    link_claim_to_experiment(DEMO_PAPER_ID, claim_id=claim_id, experiment_id=experiment["artifact_id"], root=paths.root)
    link = LinkRecord(
        id=stable_id("link", DEMO_PAPER_ID, "eq:target", "demo_code/transport_demo.py", "equation-to-code"),
        paper_id=DEMO_PAPER_ID,
        target_type="code_file",
        target="demo_code/transport_demo.py",
        relationship="equation-to-code",
        source_type="equation",
        source_ref="eq:target",
        target_ref="demo_code/transport_demo.py:1",
        evidence_refs=[],
        limitations=["Demo link requires review before it is treated as an implementation claim."],
        review_status="requires_human_review",
    )
    FileStore(paths.local_research).write_json(paths.links / f"{link.id}.json", link.to_dict())
    traceability = build_traceability_report(DEMO_PAPER_ID, root=paths.root)
    governance = build_governance_record(DEMO_PAPER_ID, root=paths.root)
    model_policy = create_model_policy("individual_release_default_policy", root=paths.root)
    readiness = build_readiness_report("individual_release_demo_readiness", root=paths.root)
    backup = create_backup(root=paths.root)
    return {
        "status": "completed",
        "paper_id": DEMO_PAPER_ID,
        "derivation_id": derivation["artifact_id"],
        "experiment_id": experiment["artifact_id"],
        "traceability_id": traceability["artifact_id"],
        "governance_id": governance["artifact_id"],
        "model_policy_id": model_policy["artifact_id"],
        "readiness_status": readiness["status"],
        "backup_path": backup["backup_path"],
        "requires_human_review": True,
    }


def demo_clean(*, root: Path | None = None, dry_run: bool = True, force: bool = False) -> dict[str, Any]:
    paths = get_paths(root)
    marker_path = demo_marker_path(paths.root)
    if not marker_path.exists():
        return {"status": "blocked", "reason": "demo marker not found", "dry_run": dry_run}
    marker = json.loads(marker_path.read_text())
    if marker.get("demo_workspace") is not True:
        return {"status": "blocked", "reason": "workspace is not marked as a demo workspace", "dry_run": dry_run}
    targets = [paths.local_research, config_dir(paths.root), paths.root / "demo_code"]
    if dry_run or not force:
        return {
            "status": "dry_run_complete",
            "dry_run": True,
            "would_remove": [str(path) for path in targets if path.exists()],
            "message": "Pass --force without --dry-run to remove only this marked demo workspace.",
        }
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
    return {"status": "cleaned", "dry_run": False, "removed": [str(path) for path in targets]}


def _release_material_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "docs" / "installation.md").exists():
        return cwd
    return Path(__file__).resolve().parents[2]


def release_artifacts_manifest(*, dist_dir: Path | None = None, release_root: Path | None = None) -> dict[str, Any]:
    root = release_root or _release_material_root()
    dist = dist_dir or (root / "dist")
    artifacts = []
    for path in sorted(dist.glob("*")) if dist.exists() else []:
        if path.is_file() and path.name != "release_artifacts_manifest.json":
            artifacts.append({
                "filename": path.name,
                "path": str(path),
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            })
    payload = {
        "schema_version": "individual-release-artifacts-v1",
        "created_at": utc_now_iso(),
        "package_version": __version__,
        "dist_dir": str(dist),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "status": "ok" if artifacts else "warnings",
        "warnings": [] if artifacts else [{"code": "no_release_artifacts_built"}],
    }
    if dist.exists():
        atomic_write_json(dist / "release_artifacts_manifest.json", payload)
    return payload


def onboarding_report(*, release_root: Path | None = None) -> dict[str, Any]:
    root = release_root or _release_material_root()
    checklist = [
        "install package",
        "run ra --help",
        "run ra version",
        "initialize workspace",
        "run doctor",
        "run demo setup",
        "run demo run",
        "inspect release report",
        "create backup",
        "inspect backup",
        "restore backup dry-run",
        "run privacy status",
        "optional local PDF ingest",
    ]
    return {
        "status": "ready_for_trial" if (root / "docs" / "onboarding_trial.md").exists() else "warnings",
        "checklist": checklist,
        "doc_path": str(root / "docs" / "onboarding_trial.md"),
        "known_limitations_path": str(root / "docs" / "known_limitations.md"),
        "requires_human_review": True,
    }


def corruption_hardening_status(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    checks = [
        {"check": "invalid_config_json", "covered_by": "validate_config"},
        {"check": "unknown_config_key", "covered_by": "validate_config"},
        {"check": "invalid_timeout", "covered_by": "validate_config"},
        {"check": "malformed_industrial_artifact", "covered_by": "validate_industrial_artifacts"},
        {"check": "backup_missing_manifest", "covered_by": "inspect_backup"},
        {"check": "backup_hash_mismatch", "covered_by": "inspect_backup"},
        {"check": "unsafe_restore_path", "covered_by": "inspect_backup"},
        {"check": "atomic_config_write", "covered_by": "atomic_write_json"},
    ]
    return {
        "status": "ok",
        "workspace_root": str(paths.root),
        "checks": checks,
        "repair_policy": "Only missing directories are repaired automatically; content repair remains manual.",
        "requires_human_review": True,
    }


def mcp_readiness_status(*, root: Path | None = None) -> dict[str, Any]:
    from research_assistant.ingest.pdf_batch_policy import pdf_batch_policy_status
    from research_assistant.adapters.review_write import review_write_status

    pdf_policy_status = pdf_batch_policy_status()
    review_write_readiness = review_write_status(root=root)
    gate_status = {
        "colleague_mcp_trial": {
            "status": "blocked_external",
            "evidence": "not_recorded",
            "claim": "A real colleague MCP client setup trial is blocked until a real colleague or fresh reader completes the trial.",
            "record_template": "docs/mcp_colleague_trial_record_template.md",
            "evidence_index": "docs/validation/local_mcp_external_validation_records.md",
        },
        "explicit_id_arxiv_source_batch": {
            "status": "available_with_local_grant",
            "deterministic_scale_evidence": "mocked_25_paper_passed",
            "live_scale_evidence": "accepted_25_50_100_public_id_runs_2026_05_03",
            "review_policy": "review_material_only",
            "live_protocol": "docs/validation/local_mcp_live_arxiv_scale_protocol.md",
            "evidence_index": "docs/validation/local_mcp_external_validation_records.md",
        },
        "query_discovery": {
            "status": "offline_candidate_file_planning_available",
            "offline_candidate_file_planning": True,
            "live_query_enabled": False,
            "claim": "Pinned candidate-file planning is available; live query discovery is disabled until bounded live validation is recorded.",
            "live_protocol": "docs/validation/local_mcp_live_query_discovery_protocol.md",
            "evidence_index": "docs/validation/local_mcp_external_validation_records.md",
        },
        "pdf_batch_intake": {
            "status": "policy_checks_available_execution_disabled",
            "policy_checks_available": True,
            "execution_enabled": False,
            "policy": pdf_policy_status,
            "claim": "PDF batch download execution is disabled.",
            "preconditions": "docs/validation/local_mcp_write_surface_preconditions.md",
            "evidence_index": "docs/validation/local_mcp_external_validation_records.md",
        },
        "review_write": {
            "status": "cli_prototype_only",
            "mcp_exposed": False,
            "supported_operations": ["mark_review_status"],
            "proposal_counts": review_write_readiness.get("proposal_counts", {}),
            "claim": "Review mutation is not exposed through MCP.",
            "preconditions": "docs/validation/local_mcp_write_surface_preconditions.md",
            "evidence_index": "docs/validation/local_mcp_external_validation_records.md",
        },
        "packaging_after_mcp_gap_work": {
            "status": "manual_rebuild_recommended",
            "rebuild_commands": [
                "timeout 300 scripts/run_packaging_smoke.sh",
                "timeout 300 scripts/build_release_artifacts.sh",
            ],
            "generated_artifacts_committed": False,
        },
    }
    try:
        from research_assistant.adapters import mcp_server
        from research_assistant.adapters.mcp_permissions import mcp_permissions_status
    except Exception as exc:
        return {
            "status": "warnings",
            "optional": True,
            "mcp_sdk_available": False,
            "adapter_importable": False,
            "reason": str(exc),
            "default_mode": "read_only",
            "hosted_service": False,
            "write_tools_enabled_by_default": False,
            "gate_status": gate_status,
            "limitations": ["MCP is optional and not required for the base local CLI workflow."],
        }
    permission_status = mcp_permissions_status(root=root)
    return {
        "status": "available" if mcp_server.mcp_available() else "not_installed",
        "optional": True,
        "mcp_sdk_available": mcp_server.mcp_available(),
        "adapter_importable": True,
        "entrypoint": "ra-mcp",
        "transport": "stdio",
        "default_mode": "read_only",
        "hosted_service": False,
        "write_tools_enabled_by_default": False,
        "mcp_tools": mcp_server.available_tool_names(),
        "permission_status": permission_status,
        "gate_status": gate_status,
        "limitations": [
            "MCP is local stdio only for this milestone.",
            "ArXiv batch intake requires an explicit local grant before writes.",
            "Review mutation and destructive tools are not exposed.",
        ],
    }


def release_report(*, root: Path | None = None, output: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    release_root = _release_material_root()
    workspace = workspace_validate(root=paths.root)
    privacy = privacy_status(root=paths.root)
    doctor_report = doctor(root=paths.root, include_matrix=True)
    platform_report = platform_status(root=paths.root)
    version_report = version_consistency(release_root=release_root)
    parser_benchmark = parser_benchmark_smoke(root=release_root)
    artifact_manifest = release_artifacts_manifest(release_root=release_root)
    onboarding = onboarding_report(release_root=release_root)
    corruption = corruption_hardening_status(root=paths.root)
    mcp_readiness = mcp_readiness_status(root=paths.root)
    doc_rows = [{"path": path, "exists": (release_root / path).exists()} for path in RELEASE_DOCS]
    script_rows = [{"path": path, "exists": (release_root / path).exists(), "executable": os.access(release_root / path, os.X_OK)} for path in RELEASE_SCRIPTS]
    source_checkout_materials = (release_root / "pyproject.toml").exists() and (release_root / "docs").exists()
    blockers = []
    warnings = []
    missing_docs = [row["path"] for row in doc_rows if not row["exists"]]
    missing_scripts = [row["path"] for row in script_rows if not row["exists"]]
    non_executable_scripts = [row["path"] for row in script_rows if row["exists"] and not row["executable"]]
    if missing_docs:
        if source_checkout_materials:
            blockers.append({"code": "missing_release_docs", "paths": missing_docs})
        else:
            warnings.append({"code": "release_docs_not_available_from_installed_context", "paths": missing_docs})
    if missing_scripts:
        if source_checkout_materials:
            blockers.append({"code": "missing_release_scripts", "paths": missing_scripts})
        else:
            warnings.append({"code": "release_scripts_not_available_from_installed_context", "paths": missing_scripts})
    if non_executable_scripts:
        blockers.append({"code": "release_scripts_not_executable", "paths": non_executable_scripts})
    if workspace["status"] == "blocked":
        blockers.append({"code": "workspace_validation_blocked"})
    elif workspace["status"] == "warnings":
        warnings.append({"code": "workspace_validation_warnings"})
    if privacy["status"] != "ok":
        blockers.append({"code": "privacy_defaults_not_offline"})
    if doctor_report["status"] == "warnings":
        warnings.append({"code": "doctor_warnings", "warnings": doctor_report.get("warnings", [])})
    if version_report["status"] == "blocked":
        blockers.append({"code": "version_consistency_blocked", "issues": version_report["issues"]})
    elif version_report["status"] == "warnings":
        warnings.append({"code": "version_consistency_warnings", "issues": version_report["issues"]})
    if platform_report["status"] != "ok":
        warnings.append({"code": "platform_support_warning", "support_tier": platform_report["support_tier"]})
    if parser_benchmark["status"] == "blocked":
        blockers.append({"code": "parser_benchmark_smoke_blocked"})
    elif parser_benchmark["status"] == "warnings":
        warnings.append({"code": "parser_benchmark_smoke_warnings"})
    if artifact_manifest["status"] == "warnings":
        warnings.append({"code": "release_artifacts_not_built"})
    if onboarding["status"] == "warnings":
        warnings.append({"code": "onboarding_trial_doc_missing"})
    status = "blocked" if blockers else ("warnings" if warnings else "ready_for_release_candidate_review")
    payload = {
        "schema_version": RELEASE_REPORT_SCHEMA_VERSION,
        "status": status,
        "generated_at": utc_now_iso(),
        "version": version_payload(),
        "version_consistency": version_report,
        "workspace_validation": workspace,
        "privacy": privacy,
        "doctor": doctor_report,
        "platform": platform_report,
        "parser_benchmark_smoke": parser_benchmark,
        "release_artifacts": artifact_manifest,
        "onboarding": onboarding,
        "corruption_hardening": corruption,
        "mcp_readiness": mcp_readiness,
        "release_material_root": str(release_root),
        "release_material_mode": "source_checkout" if source_checkout_materials else "installed_package_or_workspace",
        "docs": doc_rows,
        "scripts": script_rows,
        "blockers": blockers,
        "warnings": warnings,
        "known_limitations": [
            "Individual release uses local workspace files, not shared server storage.",
            "Live LLM/provider use is disabled by default.",
            "Generated artifacts remain review material and do not certify mathematical correctness.",
            "MCP is optional, local stdio, and read-only by default.",
        ],
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload
