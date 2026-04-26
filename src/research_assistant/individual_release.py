from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import io
import json
import platform
import shutil
import tarfile

from research_assistant import __version__
from research_assistant.config import AppPaths, get_paths
from research_assistant.industrial.platform import (
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
        cfg_path.write_text(json.dumps(default_config(root), indent=2, sort_keys=True))
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
    path.write_text(json.dumps(cfg, indent=2, sort_keys=True))
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


def performance_smoke(*, root: Path | None = None, synthetic_count: int = 25) -> dict[str, Any]:
    paths = get_paths(root)
    init_workspace(root=paths.root)
    if synthetic_count < 0:
        raise ValueError("synthetic_count must be non-negative")
    store = FileStore(paths.local_research)
    created = 0
    for idx in range(synthetic_count):
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
            })
            created += 1
    start = datetime.now(timezone.utc)
    validation = workspace_validate(root=paths.root)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    warning_threshold_seconds = max(1.0, synthetic_count * 0.05)
    return {
        "status": "warnings" if elapsed > warning_threshold_seconds else "ok",
        "workspace_root": str(paths.root),
        "synthetic_count": synthetic_count,
        "created_records": created,
        "validation_status": validation["status"],
        "validation_elapsed_seconds": round(elapsed, 6),
        "warning_threshold_seconds": warning_threshold_seconds,
        "requires_human_review": True,
        "limitations": ["Synthetic corpus smoke checks local validation overhead, not real search/index performance."],
    }


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
        "schema_version": "individual-release-backup-v1",
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


def inspect_backup(path: Path) -> dict[str, Any]:
    with tarfile.open(path, "r:gz") as archive:
        try:
            member = archive.getmember(BACKUP_MANIFEST_NAME)
        except KeyError:
            return {"status": "blocked", "backup_path": str(path), "issues": [{"severity": "blocker", "code": "manifest_missing"}]}
        extracted = archive.extractfile(member)
        if extracted is None:
            return {"status": "blocked", "backup_path": str(path), "issues": [{"severity": "blocker", "code": "manifest_unreadable"}]}
        manifest = json.loads(extracted.read().decode("utf-8"))
    return {
        "status": "ok",
        "backup_path": str(path),
        "manifest": manifest,
    }


def restore_backup(path: Path, *, root: Path | None = None, dry_run: bool = True) -> dict[str, Any]:
    inspection = inspect_backup(path)
    if inspection["status"] != "ok":
        return inspection
    paths = get_paths(root)
    manifest = inspection["manifest"]
    would_overwrite = [
        row["path"] for row in manifest.get("files", [])
        if (paths.root / row["path"]).exists()
    ]
    return {
        "status": "dry_run_complete" if dry_run else "blocked",
        "dry_run": dry_run,
        "backup_path": str(path),
        "restore_root": str(paths.root),
        "file_count": manifest.get("file_count", 0),
        "would_overwrite_count": len(would_overwrite),
        "would_overwrite": would_overwrite[:50],
        "message": "Restore is dry-run only in this release slice." if dry_run else "Non-dry-run restore requires a future explicit confirmation workflow.",
    }


def doctor(*, root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(root=root)
    validation = workspace_validate(root=root)
    tools = [
        {"tool": "pdftotext", "available": shutil.which("pdftotext") is not None, "required": False},
        {"tool": "markitdown", "available": shutil.which("markitdown") is not None, "required": False},
        {"tool": "marker_single", "available": shutil.which("marker_single") is not None, "required": False},
        {"tool": "magic-pdf", "available": shutil.which("magic-pdf") is not None, "required": False},
    ]
    warnings = []
    if validation["status"] != "ok":
        warnings.append("workspace has validation warnings or blockers")
    if cfg.get("providers", {}).get("enabled") is True:
        warnings.append("providers are enabled; individual release defaults expect providers disabled")
    return {
        "status": "warnings" if warnings else "ok",
        "package_version": __version__,
        "python": platform.python_version(),
        "workspace_root": str(get_paths(root).root),
        "workspace_status": validation["status"],
        "default_timeout_seconds": cfg.get("default_timeout_seconds"),
        "offline_mode": cfg.get("offline_mode") is True,
        "providers_enabled": cfg.get("providers", {}).get("enabled") is True,
        "optional_tools": tools,
        "warnings": warnings,
        "suggested_next_commands": ["ra init", "ra demo setup", "ra demo run"],
    }


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


def release_report(*, root: Path | None = None, output: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    release_root = _release_material_root()
    docs = [
        "docs/installation.md",
        "docs/quickstart.md",
        "docs/workflows/individual_research_workflow.md",
        "docs/troubleshooting.md",
        "docs/privacy.md",
        "docs/release_checklist.md",
    ]
    scripts = [
        "scripts/run_fast_tests.sh",
        "scripts/run_bounded_tests.sh",
        "scripts/run_release_smoke.sh",
        "scripts/run_packaging_smoke.sh",
    ]
    workspace = workspace_validate(root=paths.root)
    privacy = privacy_status(root=paths.root)
    doctor_report = doctor(root=paths.root)
    doc_rows = [{"path": path, "exists": (release_root / path).exists()} for path in docs]
    script_rows = [{"path": path, "exists": (release_root / path).exists()} for path in scripts]
    blockers = []
    warnings = []
    missing_docs = [row["path"] for row in doc_rows if not row["exists"]]
    missing_scripts = [row["path"] for row in script_rows if not row["exists"]]
    if missing_docs:
        blockers.append({"code": "missing_release_docs", "paths": missing_docs})
    if missing_scripts:
        blockers.append({"code": "missing_release_scripts", "paths": missing_scripts})
    if workspace["status"] == "blocked":
        blockers.append({"code": "workspace_validation_blocked"})
    elif workspace["status"] == "warnings":
        warnings.append({"code": "workspace_validation_warnings"})
    if privacy["status"] != "ok":
        blockers.append({"code": "privacy_defaults_not_offline"})
    if doctor_report["status"] == "warnings":
        warnings.append({"code": "doctor_warnings", "warnings": doctor_report.get("warnings", [])})
    status = "blocked" if blockers else ("warnings" if warnings else "ready_for_release_candidate_review")
    payload = {
        "status": status,
        "generated_at": utc_now_iso(),
        "version": version_payload(),
        "workspace_validation": workspace,
        "privacy": privacy,
        "doctor": doctor_report,
        "release_material_root": str(release_root),
        "docs": doc_rows,
        "scripts": script_rows,
        "blockers": blockers,
        "warnings": warnings,
        "known_limitations": [
            "Individual release uses local workspace files, not shared server storage.",
            "Live LLM/provider use is disabled by default.",
            "Generated artifacts remain review material and do not certify mathematical correctness.",
        ],
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload
