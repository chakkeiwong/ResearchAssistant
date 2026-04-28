from __future__ import annotations

from pathlib import Path
from typing import Any
import fnmatch
import json
import shutil
import subprocess

from research_assistant.config import get_paths
from research_assistant.individual_release import (
    create_backup,
    release_report,
    workspace_validate,
)
from research_assistant.industrial.platform import build_artifact_index, build_readiness_report
from research_assistant.schemas.artifact import base_artifact, stable_id, utc_now_iso
from research_assistant.storage.file_store import FileStore


INDIVIDUAL_GIT_RELEASE_VERSION = "individual-git-release-v1"
SHAREABLE_WORKSPACE_POLICY_VERSION = "shareable-workspace-policy-v1"

FORBIDDEN_FIELD_NAMES = {
    "private_pdf",
    "private_title",
    "backup_archive",
    "provider_key",
    "credential",
    "credentials",
    "token",
    "secret",
    "api_key",
}

PRIVATE_PATH_MARKERS = (
    "/home/",
    "/Users/",
    "C:\\Users\\",
)

REBUILD_NEXT_ACTIONS = [
    "ra artifact-index build",
    "ra industrial-readiness build",
    "ra workspace validate",
    "ra repository-hygiene check",
]


DEFAULT_SHAREABLE_WORKSPACE_POLICY: dict[str, Any] = {
    "schema_version": SHAREABLE_WORKSPACE_POLICY_VERSION,
    "artifact_type": "shareable_workspace_policy",
    "release_target": "git_shared_research_release",
    "allowed_patterns": [
        "local_research/summaries/*.json",
        "local_research/metadata/*.json",
        "local_research/papers/source/records/*.json",
        "local_research/links/*.json",
        "local_research/reviews/*.json",
        "local_research/reviews/metadata/*.json",
        "local_research/analysis/derivations/*.json",
        "local_research/experiments/*.json",
        "local_research/analysis/traceability/*.json",
        "local_research/benchmarks/manifests/*.json",
        "local_research/benchmarks/runs/*.json",
        "local_research/analysis/synthesis/*.json",
        "local_research/analysis/citation_graph_reports/*.json",
        "local_research/governance/model_policies/*.json",
    ],
    "rebuildable_patterns": [
        "local_research/indices/**",
        "local_research/jobs/*.json",
        "local_research/exports/**",
        "local_research/governance/industrial_release/*.json",
        "local_research/governance/merge_reports/*.json",
        "local_research/contracts/tools/*.json",
        "local_research/benchmarks/runs/release_performance*.json",
    ],
    "forbidden_patterns": [
        ".codex",
        ".codex/**",
        ".claude/**",
        ".pytest_cache/**",
        "**/__pycache__/**",
        "build/**",
        "dist/**",
        "local_research/papers/raw/**",
        "local_research/papers/extracted/**",
        "local_research/exports/backups/**",
        "**/*.tar",
        "**/*.tar.gz",
        "**/*.tgz",
        "**/*.zip",
        "**/*.pdf",
        "**/*.tex",
        "**/.env",
    ],
    "required_metadata_fields": [
        "schema_version",
        "provenance",
        "review_status",
        "limitations",
    ],
    "trust_boundary": (
        "Generated, parser, benchmark, derivation, traceability, LLM, and readiness artifacts "
        "remain review material and must not be silently promoted to accepted conclusions."
    ),
}


def _store(root: Path | None = None) -> FileStore:
    return FileStore(get_paths(root).local_research)


def _policy_path(release_root: Path | None = None) -> Path:
    root = release_root or Path.cwd()
    return root / "docs" / "release" / "shareable_workspace_policy.json"


def load_shareable_workspace_policy(*, release_root: Path | None = None) -> dict[str, Any]:
    path = _policy_path(release_root)
    if path.exists():
        return json.loads(path.read_text())
    return DEFAULT_SHAREABLE_WORKSPACE_POLICY


def _relative_to_root(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _match_any(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def classify_shareable_path(rel_path: str, *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_shareable_workspace_policy()
    if _match_any(rel_path, policy.get("forbidden_patterns", [])):
        return {"classification": "forbidden", "reason": "private, generated, archive, credential, or raw-paper path"}
    if _match_any(rel_path, policy.get("rebuildable_patterns", [])):
        return {"classification": "rebuildable", "reason": "generated artifact should be rebuilt after checkout or merge"}
    if _match_any(rel_path, policy.get("allowed_patterns", [])):
        return {"classification": "shareable", "reason": "policy allows this research artifact family"}
    return {"classification": "unsupported", "reason": "path is not listed as shareable for Git exchange"}


def _iter_workspace_files(root: Path) -> list[Path]:
    candidates = []
    for base_name in ["local_research", ".research-assistant"]:
        base = root / base_name
        if base.exists():
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    for path in [root / ".codex", root / ".claude"]:
        if path.exists():
            if path.is_file():
                candidates.append(path)
            else:
                candidates.extend(child for child in path.rglob("*") if child.is_file())
    return sorted(candidates)


def _normalized_json_hash(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    return stable_id("json", json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _file_hash(path: Path) -> str:
    normalized = _normalized_json_hash(path)
    if normalized:
        return normalized
    return stable_id("file", path.read_bytes().hex())


def _json_payload(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _has_private_payload_fields(path: Path) -> list[dict[str, Any]]:
    payload = _json_payload(path)
    if payload is None:
        return []
    issues = []
    keys = set(payload)
    forbidden = sorted(keys & FORBIDDEN_FIELD_NAMES)
    if forbidden:
        issues.append({"code": "forbidden_private_fields", "fields": forbidden})
    serialized = json.dumps(payload, sort_keys=True)
    if any(marker in serialized for marker in PRIVATE_PATH_MARKERS):
        issues.append({"code": "possible_private_path"})
    return issues


def _git_status(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        return {"status": "not_a_git_repository", "entries": [], "issues": []}
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "entries": [], "issues": [{"severity": "warning", "code": "git_status_unavailable", "message": str(exc)}]}
    if completed.returncode != 0:
        return {"status": "unavailable", "entries": [], "issues": [{"severity": "warning", "code": "git_status_failed", "stderr": completed.stderr.strip()}]}
    entries = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append({
            "status": line[:2],
            "path": path,
            "staged": line[0] not in {" ", "?"},
            "unstaged": line[1] != " ",
            "untracked": line[:2] == "??",
        })
    return {"status": "dirty" if entries else "clean", "entries": entries, "issues": []}


def repository_hygiene_check(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    policy = load_shareable_workspace_policy()
    git_status = _git_status(paths.root)
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    scanned_files = _iter_workspace_files(paths.root)
    forbidden_files = []
    rebuildable_files = []
    unsupported_files = []
    private_payload_issues = []
    for path in scanned_files:
        rel_path = _relative_to_root(path, paths.root)
        classification = classify_shareable_path(rel_path, policy=policy)
        if classification["classification"] == "forbidden":
            forbidden_files.append({"path": rel_path, "reason": classification["reason"]})
        elif classification["classification"] == "rebuildable":
            rebuildable_files.append({"path": rel_path, "reason": classification["reason"]})
        elif classification["classification"] == "unsupported":
            unsupported_files.append({"path": rel_path, "reason": classification["reason"]})
        for payload_issue in _has_private_payload_fields(path):
            private_payload_issues.append({"path": rel_path, **payload_issue})
    for entry in git_status["entries"]:
        classification = classify_shareable_path(entry["path"], policy=policy)
        if entry["staged"] and classification["classification"] in {"forbidden", "rebuildable", "unsupported"}:
            issues.append({
                "severity": "blocker",
                "code": "unsafe_staged_file",
                "path": entry["path"],
                "classification": classification["classification"],
                "reason": classification["reason"],
            })
    if forbidden_files:
        issues.append({"severity": "blocker", "code": "forbidden_files_present", "files": forbidden_files})
    if private_payload_issues:
        issues.append({"severity": "blocker", "code": "private_payload_fields", "records": private_payload_issues})
    if rebuildable_files:
        warnings.append({"severity": "warning", "code": "rebuildable_files_present", "files": rebuildable_files[:50]})
    if unsupported_files:
        warnings.append({"severity": "warning", "code": "unsupported_files_present", "files": unsupported_files[:50]})
    issues.extend(git_status.get("issues", []))
    blocker_count = len([issue for issue in issues if issue.get("severity") == "blocker"])
    warning_count = len(warnings) + len([issue for issue in issues if issue.get("severity") == "warning"])
    return {
        "schema_version": INDIVIDUAL_GIT_RELEASE_VERSION,
        "artifact_type": "repository_hygiene_report",
        "status": "blocked" if blocker_count else ("warnings" if warning_count else "ok"),
        "workspace_root": str(paths.root),
        "policy_version": policy.get("schema_version"),
        "git_status": git_status,
        "scanned_file_count": len(scanned_files),
        "forbidden_files": forbidden_files,
        "rebuildable_files": rebuildable_files,
        "unsupported_files": unsupported_files,
        "issues": issues,
        "warnings": warnings,
        "next_actions": [
            "remove private/raw/generated files from Git before sharing",
            "commit only shareable local_research artifacts",
            "rebuild generated indexes after checkout or merge",
        ],
    }


def _artifact_key(path: Path) -> tuple[str, str] | None:
    payload = _json_payload(path)
    if not payload:
        return None
    artifact_id = payload.get("artifact_id") or payload.get("id")
    if artifact_id:
        return ("artifact", str(artifact_id))
    paper_id = payload.get("paper_id")
    if paper_id:
        return ("paper", str(paper_id))
    return None


def _accepted_audit_conflict(source: Path, target: Path) -> bool:
    source_payload = _json_payload(source)
    target_payload = _json_payload(target)
    if not source_payload or not target_payload:
        return False
    source_audit = source_payload.get("technical_audit")
    target_audit = target_payload.get("technical_audit")
    if not isinstance(source_audit, dict) or not isinstance(target_audit, dict):
        return False
    return source_audit != target_audit and bool(source_audit) and bool(target_audit)


def _merge_report_path(target_root: Path, report_id: str) -> Path:
    return target_root / "local_research" / "governance" / "merge_reports" / f"{report_id}.json"


def _source_git_commit(source_root: Path) -> str | None:
    if not (source_root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def workspace_merge(
    *,
    source: Path,
    target: Path,
    dry_run: bool = True,
    apply: bool = False,
    confirm_merge: bool = False,
) -> dict[str, Any]:
    source_root = source.resolve()
    target_root = target.resolve()
    policy = load_shareable_workspace_policy()
    source_validation = workspace_validate(root=source_root)
    target_validation = workspace_validate(root=target_root)
    rows = []
    artifact_seen: dict[tuple[str, str], str] = {}
    target_files_by_key: dict[tuple[str, str], Path] = {}
    for target_file in _iter_workspace_files(target_root):
        rel_path = _relative_to_root(target_file, target_root)
        classification = classify_shareable_path(rel_path, policy=policy)
        if classification["classification"] == "shareable":
            key = _artifact_key(target_file)
            if key:
                target_files_by_key[key] = target_file
    for source_file in _iter_workspace_files(source_root):
        rel_path = _relative_to_root(source_file, source_root)
        classification = classify_shareable_path(rel_path, policy=policy)
        target_file = target_root / rel_path
        row = {
            "path": rel_path,
            "classification": classification["classification"],
            "target_exists": target_file.exists(),
            "action": "unsupported",
            "issues": [],
        }
        if classification["classification"] == "forbidden":
            row["action"] = "blocked"
            row["issues"].append({"severity": "blocker", "code": "forbidden_source_file", "reason": classification["reason"]})
        elif classification["classification"] == "rebuildable":
            row["action"] = "skip_rebuildable"
        elif classification["classification"] == "unsupported":
            row["action"] = "skip_unsupported"
        else:
            source_hash = _file_hash(source_file)
            row["source_hash"] = source_hash
            key = _artifact_key(source_file)
            if target_file.exists():
                target_hash = _file_hash(target_file)
                row["target_hash"] = target_hash
                if source_hash == target_hash:
                    row["action"] = "already_present"
                else:
                    row["action"] = "conflict"
                    row["issues"].append({"severity": "blocker", "code": "same_path_different_content"})
                    if _accepted_audit_conflict(source_file, target_file):
                        row["issues"].append({"severity": "blocker", "code": "accepted_audit_conflict"})
            elif key and key in target_files_by_key:
                row["action"] = "conflict"
                row["issues"].append({
                    "severity": "blocker",
                    "code": "same_artifact_id_different_path",
                    "target_path": _relative_to_root(target_files_by_key[key], target_root),
                })
            elif key and key in artifact_seen:
                row["action"] = "conflict"
                row["issues"].append({"severity": "blocker", "code": "duplicate_source_artifact_id", "first_path": artifact_seen[key]})
            else:
                row["action"] = "copy_candidate"
            if key:
                artifact_seen.setdefault(key, rel_path)
            for payload_issue in _has_private_payload_fields(source_file):
                row["action"] = "blocked"
                row["issues"].append({"severity": "blocker", **payload_issue})
        rows.append(row)
    report_id = stable_id("workspace_merge", source_root, target_root, utc_now_iso())
    copy_candidates = [row for row in rows if row["action"] == "copy_candidate"]
    conflicts = [row for row in rows if row["action"] == "conflict"]
    blocked = [row for row in rows if row["action"] == "blocked"]
    applied_files = []
    backup = None
    blocked_apply_reason = None
    if apply and not confirm_merge:
        blocked_apply_reason = "merge_confirmation_required"
    if apply and confirm_merge and (conflicts or blocked):
        blocked_apply_reason = "conflicts_or_blockers_must_be_resolved"
    if apply and confirm_merge and not blocked_apply_reason:
        backup = create_backup(root=target_root)
        for row in copy_candidates:
            source_file = source_root / row["path"]
            target_file = target_root / row["path"]
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            payload = _json_payload(target_file)
            if payload is not None:
                provenance = payload.setdefault("provenance", {})
                provenance.setdefault("imported_from", []).append({
                    "source_root": str(source_root),
                    "source_git_commit": _source_git_commit(source_root),
                    "merge_report_id": report_id,
                    "merged_at": utc_now_iso(),
                })
                target_file.write_text(json.dumps(payload, indent=2, sort_keys=True))
            applied_files.append(row["path"])
            row["action"] = "copied"
    report_status = "blocked" if blocked or conflicts or blocked_apply_reason else ("applied" if apply else "dry_run_complete")
    report = {
        **base_artifact(
            artifact_type="workspace_merge_report",
            artifact_id=report_id,
            provenance={"created_by": "ra workspace merge", "source_root": str(source_root), "target_root": str(target_root)},
            limitations=[
                "Merge reports are local deterministic evidence, not research approval.",
                "Generated indexes and readiness reports should be rebuilt after merge.",
            ],
        ),
        "status": report_status,
        "dry_run": not apply,
        "applied": bool(applied_files),
        "source_root": str(source_root),
        "target_root": str(target_root),
        "source_validation_status": source_validation["status"],
        "target_validation_status": target_validation["status"],
        "counts": {
            "copy_candidates": len(copy_candidates),
            "already_present": len([row for row in rows if row["action"] == "already_present"]),
            "copied": len(applied_files),
            "conflicts": len(conflicts),
            "blocked": len(blocked),
            "skipped_rebuildable": len([row for row in rows if row["action"] == "skip_rebuildable"]),
            "skipped_unsupported": len([row for row in rows if row["action"] == "skip_unsupported"]),
        },
        "blocked_apply_reason": blocked_apply_reason,
        "backup": backup,
        "applied_files": applied_files,
        "files": rows,
        "next_actions": REBUILD_NEXT_ACTIONS,
    }
    _store(target_root).write_json(_merge_report_path(target_root, report_id), report)
    return report


def workspace_rebuild_derived(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    index = build_artifact_index("post_merge_artifact_index", root=paths.root)
    readiness = build_readiness_report("post_merge_readiness", root=paths.root)
    validation = workspace_validate(root=paths.root)
    return {
        **base_artifact(
            artifact_type="workspace_rebuild_report",
            artifact_id="workspace_rebuild_derived",
            provenance={"created_by": "ra workspace rebuild-derived"},
            limitations=["Rebuild regenerates local reports only; it does not certify research conclusions."],
        ),
        "status": "blocked" if validation["status"] == "blocked" else ("warnings" if validation["status"] == "warnings" or readiness["status"] == "warnings" else "ok"),
        "workspace_root": str(paths.root),
        "artifact_index_id": index["artifact_id"],
        "artifact_index_status": index["validation_summary"]["status"],
        "readiness_id": readiness["artifact_id"],
        "readiness_status": readiness["status"],
        "workspace_validation_status": validation["status"],
        "network_required": False,
    }


def individual_git_release_gate(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    release = release_report(root=paths.root)
    hygiene = repository_hygiene_check(root=paths.root)
    merge_supported = True
    blockers = []
    warnings = []
    if release["status"] == "blocked":
        blockers.append({"code": "individual_release_report_blocked", "details": release["blockers"]})
    elif release["status"] == "warnings":
        warnings.append({"code": "individual_release_report_warnings", "details": release["warnings"]})
    if hygiene["status"] == "blocked":
        blockers.append({"code": "repository_hygiene_blocked", "issues": hygiene["issues"]})
    elif hygiene["status"] == "warnings":
        warnings.append({"code": "repository_hygiene_warnings", "warnings": hygiene["warnings"]})
    if not merge_supported:
        blockers.append({"code": "workspace_merge_unavailable"})
    blockers.append({
        "code": "external_validation_required_for_broad_release",
        "details": "Real colleague/platform validation and release-owner tag/publication approval are still manual gates.",
    })
    return {
        **base_artifact(
            artifact_type="individual_git_release_gate",
            artifact_id="individual_git_release_gate",
            provenance={"created_by": "ra individual-git-release gate-build"},
            limitations=["Gate targets individual Git-sharing release, not multi-user production."],
        ),
        "gate_version": INDIVIDUAL_GIT_RELEASE_VERSION,
        "current_target": "git_shared_research_release",
        "future_target": "future_multi_user_platform",
        "status": "blocked" if blockers else ("warnings" if warnings else "passed"),
        "ready_for_limited_individual_pilot": True,
        "ready_for_broad_individual_release": False,
        "ready_for_git_shared_research_release": False if blockers else True,
        "release_report_status": release["status"],
        "repository_hygiene_status": hygiene["status"],
        "workspace_merge_available": merge_supported,
        "blockers": blockers,
        "warnings": warnings,
        "deferred_future_platform_items": [
            "shared database",
            "service deployment",
            "SSO/RBAC",
            "real-time collaboration",
            "hosted UI",
            "department operations and SOP approval",
        ],
        "next_actions": [
            "collect real colleague/platform validation records",
            "obtain explicit release-owner tag/publication approval",
            "run repository hygiene before sharing",
            "use workspace merge dry-run before importing another repository",
        ],
    }
