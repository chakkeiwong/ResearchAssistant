from __future__ import annotations

from pathlib import Path
from typing import Any
import fnmatch
import json
import os
import platform as platform_module
import re
import shutil
import subprocess
import sys
import time

from research_assistant.config import get_paths
from research_assistant.individual_release import (
    create_backup,
    parser_benchmark_smoke,
    parser_tool_matrix,
    release_report,
    workspace_validate,
)
from research_assistant.industrial.platform import build_artifact_index, build_readiness_report
from research_assistant.schemas.artifact import base_artifact, stable_id, utc_now_iso
from research_assistant.storage.file_store import FileStore


INDIVIDUAL_GIT_RELEASE_VERSION = "individual-git-release-v1"
INDIVIDUAL_GIT_VALIDATION_VERSION = "individual-git-validation-v1"
SHAREABLE_WORKSPACE_POLICY_VERSION = "shareable-workspace-policy-v1"

VALIDATION_RESULTS = {"passed", "warnings", "blocked"}
VALIDATION_SCOPES = {
    "local_machine",
    "local_fixture",
    "local_substitute",
    "real_external",
    "external_machine",
    "manual_waiver",
    "release_owner",
}

REQUIRED_VALIDATION_TYPES = [
    "linux_local",
    "linux_parser_tools",
    "merge_fixture_rehearsal",
    "representative_workspace_performance",
]

LOCAL_FIXTURE_VALIDATION_TYPES = [
    "linux_local",
    "linux_parser_tools",
    "merge_fixture_rehearsal",
    "representative_workspace_performance",
]

EXTERNAL_VALIDATION_TYPES: list[str] = []

PUBLICATION_APPROVAL_TYPES = [
    "release_owner_tag_approval",
    "publication_approval",
]

KNOWN_VALIDATION_TYPES = sorted(set(REQUIRED_VALIDATION_TYPES + PUBLICATION_APPROVAL_TYPES))

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

HIGH_RISK_SECRET_PATTERNS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "BEGIN PRIVATE KEY",
)

SUSPICIOUS_SECRET_FIELD_NAMES = {
    "api_key",
    "secret_key",
    "access_token",
    "provider_key",
    "token",
    "credential",
    "credentials",
}

HIGH_ENTROPY_SECRET_RE = re.compile(r"(?i)(sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9_/-]{32,})")

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
        "local_research/governance/individual_git_release/**",
        "local_research/governance/post_merge_readiness.json",
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


def _individual_git_governance_dir(root: Path | None = None) -> Path:
    return get_paths(root).governance / "individual_git_release"


def _validation_dir(root: Path | None = None) -> Path:
    return _individual_git_governance_dir(root) / "validation"


def _fixture_rehearsal_dir(root: Path | None = None) -> Path:
    return _individual_git_governance_dir(root) / "fixture_rehearsal"


def _performance_dir(root: Path | None = None) -> Path:
    return _individual_git_governance_dir(root) / "performance"


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
    """Classify a workspace path before Git sharing or merge/import.

    The ordering is intentional: forbidden paths win over rebuildable and
    shareable paths so a future policy edit cannot accidentally allow private
    raw papers, archives, credentials, or local generated state into exchange.
    """
    policy = policy or load_shareable_workspace_policy()
    if _match_any(rel_path, policy.get("forbidden_patterns", [])):
        return {"classification": "forbidden", "reason": "private, generated, archive, credential, or raw-paper path"}
    if _match_any(rel_path, policy.get("rebuildable_patterns", [])):
        return {"classification": "rebuildable", "reason": "generated artifact should be rebuilt after checkout or merge"}
    if _match_any(rel_path, policy.get("allowed_patterns", [])):
        return {"classification": "shareable", "reason": "policy allows this research artifact family"}
    return {"classification": "unsupported", "reason": "path is not listed as shareable for Git exchange"}


def _iter_workspace_files(root: Path, *, include_strict_roots: bool = False) -> list[Path]:
    candidates = []
    for base_name in ["local_research", ".research-assistant"]:
        base = root / base_name
        if base.exists():
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    if include_strict_roots:
        for base_name in ["build", "dist", ".pytest_cache"]:
            base = root / base_name
            if base.exists():
                candidates.extend(path for path in base.rglob("*") if path.is_file())
        env_file = root / ".env"
        if env_file.exists() and env_file.is_file():
            candidates.append(env_file)
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


def _payload_safety_issues(payload: Any, *, path_label: str = "$") -> list[dict[str, Any]]:
    issues = []

    def walk(value: Any, trail: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                key_lower = key_text.lower()
                child_trail = f"{trail}.{key_text}" if trail else key_text
                if key_lower in FORBIDDEN_FIELD_NAMES:
                    issues.append({"code": "forbidden_private_fields", "field": child_trail})
                if key_lower in SUSPICIOUS_SECRET_FIELD_NAMES and child not in (None, "", []):
                    issues.append({"code": "secret_like_field", "field": child_trail})
                walk(child, child_trail)
            return
        if isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{trail}[{idx}]")
            return
        if isinstance(value, str):
            if any(marker in value for marker in PRIVATE_PATH_MARKERS):
                issues.append({"code": "possible_private_path", "field": trail})
            for pattern in HIGH_RISK_SECRET_PATTERNS:
                if pattern in value:
                    issues.append({"code": "high_risk_secret_pattern", "field": trail, "pattern": pattern})
            if HIGH_ENTROPY_SECRET_RE.search(value) and any(token in trail.lower() for token in SUSPICIOUS_SECRET_FIELD_NAMES):
                issues.append({"code": "secret_like_value", "field": trail})

    walk(payload, path_label)
    seen = set()
    deduped = []
    for issue in issues:
        key = tuple(sorted(issue.items()))
        if key not in seen:
            seen.add(key)
            deduped.append(issue)
    return deduped


def _has_private_payload_fields(path: Path) -> list[dict[str, Any]]:
    payload = _json_payload(path)
    if payload is None:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            return []
        issues = []
        for pattern in HIGH_RISK_SECRET_PATTERNS:
            if pattern in text:
                issues.append({"code": "high_risk_secret_pattern", "pattern": pattern})
        if any(marker in text for marker in PRIVATE_PATH_MARKERS):
            issues.append({"code": "possible_private_path"})
        return issues
    return _payload_safety_issues(payload)


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


def repository_hygiene_check(*, root: Path | None = None, strict: bool = False) -> dict[str, Any]:
    paths = get_paths(root)
    policy = load_shareable_workspace_policy()
    git_status = _git_status(paths.root)
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    scanned_files = _iter_workspace_files(paths.root, include_strict_roots=strict)
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
        if strict and entry["untracked"] and classification["classification"] in {"forbidden", "rebuildable", "unsupported"}:
            issues.append({
                "severity": "blocker",
                "code": "unsafe_untracked_file",
                "path": entry["path"],
                "classification": classification["classification"],
                "reason": classification["reason"],
            })
    if strict and git_status["status"] == "not_a_git_repository":
        warnings.append({
            "severity": "warning",
            "code": "strict_check_without_git_repository",
            "message": "Strict hygiene could not inspect tracked/untracked Git state outside a Git repository.",
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
        "strict": strict,
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


def _safe_validation_text(value: str) -> str:
    return str(value)


def validation_record(
    *,
    validation_type: str,
    result: str,
    platform: str = "",
    python_version: str = "",
    install_method: str = "",
    command_summary: str = "",
    scope: str = "local_machine",
    evidence_note: str = "",
    blocker: list[str] | None = None,
    warning: list[str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    if validation_type not in KNOWN_VALIDATION_TYPES:
        return {
            "schema_version": INDIVIDUAL_GIT_VALIDATION_VERSION,
            "artifact_type": "individual_git_validation_record",
            "status": "blocked",
            "validation_type": validation_type,
            "result": result,
            "issues": [{
                "severity": "blocker",
                "code": "unknown_validation_type",
                "expected": KNOWN_VALIDATION_TYPES,
            }],
        }
    if result not in VALIDATION_RESULTS:
        raise ValueError(f"validation result must be one of {sorted(VALIDATION_RESULTS)}")
    if scope not in VALIDATION_SCOPES:
        raise ValueError(f"validation scope must be one of {sorted(VALIDATION_SCOPES)}")
    blockers = [_safe_validation_text(item) for item in (blocker or [])]
    warnings = [_safe_validation_text(item) for item in (warning or [])]
    payload = {
        **base_artifact(
            artifact_type="individual_git_validation_record",
            artifact_id=stable_id("individual_git_validation", validation_type, scope, result),
            provenance={"created_by": "ra individual-git-release validation-record"},
            limitations=[
                "Validation records are sanitized release evidence, not research approval.",
                "Local validation applies only to the supported Linux/WSL single-user release contract.",
            ],
        ),
        "schema_version": INDIVIDUAL_GIT_VALIDATION_VERSION,
        "validation_type": _safe_validation_text(validation_type),
        "result": result,
        "scope": scope,
        "platform": _safe_validation_text(platform or platform_module.platform()),
        "python_version": _safe_validation_text(python_version or platform_module.python_version()),
        "install_method": _safe_validation_text(install_method),
        "command_summary": _safe_validation_text(command_summary),
        "evidence_note": _safe_validation_text(evidence_note),
        "blockers": blockers,
        "warnings": warnings,
        "recorded_at": utc_now_iso(),
        "privacy_screened": True,
        "requires_human_review": True,
    }
    safety_issues = _payload_safety_issues(payload)
    if safety_issues:
        return {
            "schema_version": INDIVIDUAL_GIT_VALIDATION_VERSION,
            "artifact_type": "individual_git_validation_record",
            "status": "blocked",
            "validation_type": validation_type,
            "result": result,
            "issues": [{"severity": "blocker", **issue} for issue in safety_issues],
        }
    out = _validation_dir(root) / f"{payload['artifact_id']}.json"
    FileStore(get_paths(root).local_research).write_json(out, payload)
    payload["status"] = "recorded"
    payload["path"] = str(out)
    return payload


def _validation_records(root: Path | None = None) -> list[dict[str, Any]]:
    rows = []
    directory = _validation_dir(root)
    if not directory.exists():
        return rows
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            rows.append({
                "schema_version": INDIVIDUAL_GIT_VALIDATION_VERSION,
                "artifact_type": "individual_git_validation_record",
                "status": "blocked",
                "validation_type": "unknown",
                "result": "blocked",
                "path": str(path),
                "issues": [{"severity": "blocker", "code": "validation_record_unreadable"}],
            })
            continue
        payload["path"] = str(path)
        rows.append(payload)
    return rows


def validation_report(*, root: Path | None = None) -> dict[str, Any]:
    records = _validation_records(root)
    record_map: dict[str, list[dict[str, Any]]] = {}
    issues = []
    for record in records:
        safety_payload = {key: value for key, value in record.items() if key != "path"}
        safety_issues = _payload_safety_issues(safety_payload)
        if safety_issues:
            issues.append({
                "severity": "blocker",
                "code": "validation_record_privacy_screen_failed",
                "path": record.get("path"),
                "issues": safety_issues,
            })
        record_map.setdefault(str(record.get("validation_type", "unknown")), []).append(record)

    def passed(validation_type: str, *, scopes: set[str] | None = None) -> bool:
        candidates = record_map.get(validation_type, [])
        if scopes is not None:
            candidates = [row for row in candidates if row.get("scope") in scopes]
        return any(row.get("result") == "passed" for row in candidates)

    required_status = []
    for validation_type in REQUIRED_VALIDATION_TYPES:
        records_for_type = record_map.get(validation_type, [])
        status = "passed" if any(row.get("result") == "passed" for row in records_for_type) else "missing"
        if records_for_type and status == "missing":
            status = "blocked" if any(row.get("result") == "blocked" for row in records_for_type) else "warnings"
        required_status.append({
            "validation_type": validation_type,
            "status": status,
            "record_count": len(records_for_type),
            "latest_result": records_for_type[-1].get("result") if records_for_type else None,
            "latest_scope": records_for_type[-1].get("scope") if records_for_type else None,
        })

    missing_required = [row["validation_type"] for row in required_status if row["status"] == "missing"]
    blocked_required = [row["validation_type"] for row in required_status if row["status"] == "blocked"]
    def non_blocked_recorded(validation_type: str) -> bool:
        return any(row.get("result") in {"passed", "warnings"} for row in record_map.get(validation_type, []))

    # This product is a single-user Linux local tool. No external machine or
    # The supported release is local-only; no external user evidence is required.
    local_fixture_complete = all(non_blocked_recorded(validation_type) for validation_type in LOCAL_FIXTURE_VALIDATION_TYPES)
    external_complete = all(passed(validation_type, scopes={"real_external", "external_machine"}) for validation_type in EXTERNAL_VALIDATION_TYPES)
    publication_approved = all(passed(validation_type, scopes={"release_owner"}) for validation_type in PUBLICATION_APPROVAL_TYPES)
    blockers = [{"code": "missing_required_validation", "validation_types": missing_required}] if missing_required else []
    blockers.extend({"code": "blocked_required_validation", "validation_type": validation_type} for validation_type in blocked_required)
    blockers.extend(issues)
    warnings = []
    return {
        "schema_version": INDIVIDUAL_GIT_VALIDATION_VERSION,
        "artifact_type": "individual_git_validation_report",
        "status": "blocked" if blockers else ("warnings" if warnings else "passed"),
        "workspace_root": str(get_paths(root).root),
        "validation_dir": str(_validation_dir(root)),
        "required_validation_types": REQUIRED_VALIDATION_TYPES,
        "local_fixture_validation_types": LOCAL_FIXTURE_VALIDATION_TYPES,
        "external_validation_types": EXTERNAL_VALIDATION_TYPES,
        "publication_approval_types": PUBLICATION_APPROVAL_TYPES,
        "required_status": required_status,
        "record_count": len(records),
        "records": records,
        "missing_required_validation": missing_required,
        "blocked_required_validation": blocked_required,
        "local_fixture_validation_complete": local_fixture_complete,
        "external_validation_complete": external_complete,
        "publication_approved": publication_approved,
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": [
            "record deterministic local Linux validations after running release checks",
            "record release-owner approval only when tagging or publication is explicitly approved",
        ],
    }


def workspace_merge(
    *,
    source: Path,
    target: Path,
    dry_run: bool = True,
    apply: bool = False,
    confirm_merge: bool = False,
) -> dict[str, Any]:
    """Merge shareable workspace artifacts without silently accepting research.

    The command is dry-run by default, refuses apply without confirmation, and
    blocks accepted-audit conflicts. Those safeguards are the trust boundary for
    Git-based sharing between individual researchers.
    """
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


def _write_fixture_summary(root: Path, paper_id: str, title: str, audit_note: str = "fixture audit") -> None:
    path = root / "local_research" / "summaries" / f"{paper_id}.json"
    payload = {
        "id": paper_id,
        "artifact_id": paper_id,
        "title": title,
        "authors": ["Synthetic Git Fixture"],
        "year": 2026,
        "abstract": "Sanitized synthetic record for Git-sharing release rehearsal.",
        "main_contribution": "Fixture only.",
        "review_status": "needs_review",
        "technical_audit": {
            "claimed_results": [audit_note],
            "derived_results": [],
            "open_questions": [],
        },
        "schema_version": "summary-v1",
        "provenance": {"fixture": "individual_git_release_rehearsal"},
        "limitations": ["Synthetic release fixture; not a real paper."],
    }
    FileStore(root / "local_research").write_json(path, payload)


def _write_fixture_generated(root: Path) -> None:
    FileStore(root / "local_research").write_json(root / "local_research" / "indices" / "fixture_generated_index.json", {
        "generated": True,
        "schema_version": "fixture-index-v1",
    })
    raw = root / "local_research" / "papers" / "raw" / "private_fixture.pdf"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("synthetic private raw fixture")


def _build_git_share_fixture_pair(base: Path, *, include_blocker: bool) -> tuple[Path, Path]:
    source = base / "source"
    target = base / "target"
    for root in [source, target]:
        (root / "local_research").mkdir(parents=True, exist_ok=True)
    for idx in range(12):
        _write_fixture_summary(source, f"fixture_source_{idx:02d}", f"Synthetic Source Paper {idx}")
    for idx in range(8):
        _write_fixture_summary(target, f"fixture_target_{idx:02d}", f"Synthetic Target Paper {idx}")
    _write_fixture_summary(source, "fixture_overlap_same", "Synthetic Overlap Same")
    _write_fixture_summary(target, "fixture_overlap_same", "Synthetic Overlap Same")
    if include_blocker:
        _write_fixture_summary(source, "fixture_conflict", "Synthetic Conflict", audit_note="source accepted audit")
        _write_fixture_summary(target, "fixture_conflict", "Synthetic Conflict", audit_note="target accepted audit")
    _write_fixture_generated(source)
    if not include_blocker:
        raw = source / "local_research" / "papers" / "raw" / "private_fixture.pdf"
        if raw.exists():
            raw.unlink()
    return source, target


def fixture_rehearsal(
    *,
    root: Path | None = None,
    fixture_root: Path | None = None,
    include_blocker: bool = True,
    apply_safe_subset: bool = True,
) -> dict[str, Any]:
    paths = get_paths(root)
    base = fixture_root or (_fixture_rehearsal_dir(paths.root) / "workspace_pair")
    source, target = _build_git_share_fixture_pair(base, include_blocker=include_blocker)
    dry_run_report = workspace_merge(source=source, target=target)
    if include_blocker and dry_run_report["status"] != "blocked":
        rehearsal_status = "blocked"
    else:
        rehearsal_status = "warnings" if include_blocker else "passed"
    applied_report = None
    rebuild_report = None
    hygiene_report = None
    if apply_safe_subset and not include_blocker:
        applied_report = workspace_merge(source=source, target=target, apply=True, confirm_merge=True)
        rebuild_report = workspace_rebuild_derived(root=target)
        backups_dir = target / "local_research" / "exports" / "backups"
        if backups_dir.exists():
            shutil.rmtree(backups_dir)
        hygiene_report = repository_hygiene_check(root=target)
        if applied_report["status"] != "applied" or rebuild_report["status"] == "blocked" or hygiene_report["status"] == "blocked":
            rehearsal_status = "blocked"
        else:
            rehearsal_status = "passed" if not applied_report["counts"]["conflicts"] else "warnings"
    payload = {
        **base_artifact(
            artifact_type="individual_git_fixture_rehearsal",
            artifact_id=stable_id("individual_git_fixture_rehearsal", include_blocker, apply_safe_subset),
            provenance={"created_by": "ra individual-git-release fixture-rehearsal"},
            limitations=[
                "Fixture rehearsal uses sanitized synthetic repositories.",
                "It validates merge mechanics, not semantic agreement between researchers.",
            ],
        ),
        "status": rehearsal_status,
        "source_root": str(source),
        "target_root": str(target),
        "include_blocker": include_blocker,
        "apply_safe_subset": apply_safe_subset,
        "dry_run_counts": dry_run_report["counts"],
        "dry_run_status": dry_run_report["status"],
        "applied_counts": applied_report["counts"] if applied_report else None,
        "applied_status": applied_report["status"] if applied_report else None,
        "rebuild_status": rebuild_report["status"] if rebuild_report else None,
        "hygiene_status": hygiene_report["status"] if hygiene_report else None,
        "expected_behavior": {
            "forbidden_raw_file_blocks_when_included": include_blocker,
            "accepted_audit_conflict_remains_unresolved": True,
            "generated_index_is_skipped_and_rebuilt": True,
            "safe_unique_records_are_copy_candidates": True,
        },
        "requires_human_review": True,
    }
    out = _fixture_rehearsal_dir(paths.root) / f"{payload['artifact_id']}.json"
    FileStore(paths.local_research).write_json(out, payload)
    workspace_pair_dir = _fixture_rehearsal_dir(paths.root) / "workspace_pair"
    if workspace_pair_dir.exists():
        shutil.rmtree(workspace_pair_dir)
    validation_result = "passed" if payload["status"] in {"passed", "warnings"} else "blocked"
    validation_record(
        validation_type="merge_fixture_rehearsal",
        result=validation_result,
        scope="local_fixture",
        platform=platform_module.platform(),
        python_version=platform_module.python_version(),
        install_method="source checkout",
        command_summary="ra individual-git-release fixture-rehearsal",
        evidence_note=f"Fixture rehearsal status: {payload['status']}",
        root=paths.root,
    )
    return payload


def representative_workspace_performance(
    *,
    root: Path | None = None,
    tier: str = "synthetic_git_100",
    synthetic_count: int = 100,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    paths = get_paths(root)
    if synthetic_count < 1:
        raise ValueError("synthetic_count must be positive")
    start = time.monotonic()
    source = _performance_dir(paths.root) / tier / "source"
    target = _performance_dir(paths.root) / tier / "target"
    source.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    for idx in range(synthetic_count):
        _write_fixture_summary(source, f"{tier}_source_{idx:04d}", f"{tier} Source {idx}")
        if idx % 4 == 0:
            _write_fixture_summary(target, f"{tier}_source_{idx:04d}", f"{tier} Source {idx}")
        if idx % 4 == 1:
            _write_fixture_summary(target, f"{tier}_target_{idx:04d}", f"{tier} Target {idx}")
        if timeout_seconds is not None and time.monotonic() - start > timeout_seconds:
            payload = {
                "schema_version": INDIVIDUAL_GIT_RELEASE_VERSION,
                "artifact_type": "individual_git_performance_report",
                "status": "blocked",
                "tier": tier,
                "synthetic_count": synthetic_count,
                "elapsed_seconds": round(time.monotonic() - start, 6),
                "blockers": [{"code": "performance_timeout", "timeout_seconds": timeout_seconds}],
            }
            FileStore(paths.local_research).write_json(_performance_dir(paths.root) / f"{tier}.json", payload)
            validation_record(
                validation_type="representative_workspace_performance",
                result="blocked",
                scope="local_fixture",
                command_summary="ra individual-git-release performance",
                evidence_note="Performance rehearsal timed out.",
                blocker=[f"timeout_seconds={timeout_seconds}"],
                root=paths.root,
            )
            return payload
    hygiene_start = time.monotonic()
    hygiene = repository_hygiene_check(root=source, strict=True)
    hygiene_elapsed = time.monotonic() - hygiene_start
    merge_dry_start = time.monotonic()
    dry_run = workspace_merge(source=source, target=target)
    merge_dry_elapsed = time.monotonic() - merge_dry_start
    merge_apply_start = time.monotonic()
    applied = workspace_merge(source=source, target=target, apply=True, confirm_merge=True)
    merge_apply_elapsed = time.monotonic() - merge_apply_start
    rebuild_start = time.monotonic()
    rebuild = workspace_rebuild_derived(root=target)
    rebuild_elapsed = time.monotonic() - rebuild_start
    backup_start = time.monotonic()
    backup = create_backup(root=target)
    backup_elapsed = time.monotonic() - backup_start
    elapsed = time.monotonic() - start
    backup_size = Path(backup["backup_path"]).stat().st_size
    backup_dir = target / "local_research" / "exports" / "backups"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    warnings = []
    if dry_run["status"] == "blocked" or applied["status"] == "blocked" or hygiene["status"] == "blocked" or rebuild["status"] == "blocked":
        warnings.append({"code": "performance_rehearsal_completed_with_blocking_substatus"})
    payload = {
        **base_artifact(
            artifact_type="individual_git_performance_report",
            artifact_id=stable_id("individual_git_performance", tier, synthetic_count),
            provenance={"created_by": "ra individual-git-release performance"},
            limitations=[
                "Synthetic Git workspace performance does not certify large real private libraries.",
                "Counts and timings are local-machine evidence only.",
            ],
        ),
        "status": "warnings" if warnings else "passed",
        "tier": tier,
        "synthetic_count": synthetic_count,
        "elapsed_seconds": round(elapsed, 6),
        "file_counts": {
            "source_files": len(_iter_workspace_files(source)),
            "target_files": len(_iter_workspace_files(target)),
        },
        "hygiene_elapsed_seconds": round(hygiene_elapsed, 6),
        "merge_dry_run_elapsed_seconds": round(merge_dry_elapsed, 6),
        "merge_apply_elapsed_seconds": round(merge_apply_elapsed, 6),
        "rebuild_elapsed_seconds": round(rebuild_elapsed, 6),
        "backup_elapsed_seconds": round(backup_elapsed, 6),
        "backup_size_bytes": backup_size,
        "dry_run_counts": dry_run["counts"],
        "applied_counts": applied["counts"],
        "hygiene_status": hygiene["status"],
        "rebuild_status": rebuild["status"],
        "warnings": warnings,
        "requires_human_review": True,
    }
    FileStore(paths.local_research).write_json(_performance_dir(paths.root) / f"{payload['artifact_id']}.json", payload)
    synthetic_dir = _performance_dir(paths.root) / tier
    if synthetic_dir.exists():
        shutil.rmtree(synthetic_dir)
    validation_record(
        validation_type="representative_workspace_performance",
        result="warnings" if warnings else "passed",
        scope="local_fixture",
        platform=platform_module.platform(),
        python_version=platform_module.python_version(),
        install_method="source checkout",
        command_summary=f"ra individual-git-release performance --tier {tier} --synthetic-count {synthetic_count}",
        evidence_note=f"{tier} completed in {round(elapsed, 6)} seconds",
        warning=[warning["code"] for warning in warnings],
        root=paths.root,
    )
    return payload


def _run_linux_parser_smoke(release_root: Path, *, timeout_seconds: float = 600) -> dict[str, Any]:
    script = release_root / "tests" / "scripts" / "run_parser_benchmark.py"
    if not script.is_file():
        return {"status": "blocked", "reason": "parser_benchmark_script_missing"}
    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = "-1"
    environment["PYTHONPATH"] = str(release_root / "src")
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=release_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "blocked", "reason": "parser_benchmark_timeout"}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "blocked", "reason": "parser_benchmark_invalid_json", "returncode": completed.returncode}
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return {"status": "blocked", "reason": "parser_benchmark_results_missing", "returncode": completed.returncode}
    successful_by_fixture = {
        str(row.get("id")): sorted({
            str(parser.get("parser_name"))
            for parser in row.get("parser_runs", [])
            if isinstance(parser, dict) and parser.get("parse_status") == "ok"
        })
        for row in results
        if isinstance(row, dict)
    }
    report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
    passed = (
        completed.returncode == 0
        and report.get("ready_for_release_gate") is True
        and bool(successful_by_fixture)
        and all(successful_by_fixture.values())
    )
    return {
        "status": "passed" if passed else "blocked",
        "returncode": completed.returncode,
        "fixture_count": report.get("fixture_count"),
        "scored_count": report.get("scored_count"),
        "successful_parsers_by_fixture": successful_by_fixture,
        "limitations": ["Synthetic parser smoke is diagnostic and does not certify scientific extraction accuracy."],
    }


def record_local_validations(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    platform_status = platform_module.platform()
    python_version = platform_module.python_version()
    records = []
    system = platform_module.system()
    linux_result = "passed" if system == "Linux" and platform_module.python_version().startswith("3.11.") else "blocked"
    records.append(validation_record(
        validation_type="linux_local",
        result=linux_result,
        scope="local_machine",
        platform=platform_status,
        python_version=python_version,
        install_method="source checkout",
        command_summary="local platform detection during individual Git release gate",
        evidence_note="Supported Linux/WSL local-machine validation.",
        blocker=[] if linux_result == "passed" else [f"local platform is {system} Python {python_version}; expected Linux Python 3.11.x"],
        root=paths.root,
    ))
    matrix = parser_tool_matrix(root=paths.root)
    missing_tools = [row["tool"] for row in matrix.get("optional_tools", []) if not row.get("available")]
    parser_smoke = _run_linux_parser_smoke(Path(__file__).resolve().parents[2])
    parser_result = "passed" if parser_smoke["status"] == "passed" else "blocked"
    records.append(validation_record(
        validation_type="linux_parser_tools",
        result=parser_result,
        scope="local_machine",
        platform=platform_status,
        python_version=python_version,
        install_method="source checkout",
        command_summary="ra parser-tool-matrix; scripts/run_external_tool_tests.sh",
        evidence_note=(
            f"Linux parser smoke status={parser_smoke['status']}; "
            f"fixtures={parser_smoke.get('fixture_count')}; scored={parser_smoke.get('scored_count')}. "
            "Diagnostic only, not scientific accuracy certification."
        ),
        blocker=[] if parser_result == "passed" else [str(parser_smoke.get("reason", "parser_smoke_failed"))],
        warning=[f"missing_optional_tools={','.join(missing_tools)}"] if missing_tools else [],
        root=paths.root,
    ))
    return {
        "schema_version": INDIVIDUAL_GIT_VALIDATION_VERSION,
        "artifact_type": "individual_git_local_validation_batch",
        "status": "recorded",
        "records": records,
        "next_actions": [
            "keep Linux local validation records synchronized with the final release gate",
            "do not tag or publish until release-owner approval records pass",
        ],
    }


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
    release_root = Path(__file__).resolve().parents[2]
    release = release_report(root=paths.root)
    hygiene = repository_hygiene_check(root=paths.root, strict=True)
    validations = validation_report(root=paths.root)
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
    if validations["status"] == "blocked":
        blockers.append({"code": "validation_evidence_blocked", "details": validations["blockers"]})
    elif validations["status"] == "warnings":
        warnings.append({"code": "validation_evidence_warnings", "warnings": validations["warnings"]})
    if not validations["local_fixture_validation_complete"]:
        blockers.append({
            "code": "local_fixture_validation_incomplete",
            "validation_types": validations["local_fixture_validation_types"],
        })
    if not validations["external_validation_complete"]:
        blockers.append({"code": "external_validation_required_for_broad_release", "details": "No external validation types are configured for the Linux local release."})
    if not merge_supported:
        blockers.append({"code": "workspace_merge_unavailable"})
    ready_for_limited_individual_pilot = (
        release["status"] != "blocked"
        and hygiene["status"] != "blocked"
        and merge_supported
    )
    ready_for_git_shared_research_release = (
        ready_for_limited_individual_pilot
        and validations["local_fixture_validation_complete"]
        and not validations["missing_required_validation"]
        and not validations["blocked_required_validation"]
    )
    ready_for_broad_individual_release = (
        ready_for_git_shared_research_release
        and validations["external_validation_complete"]
    )
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
        "ready_for_limited_individual_pilot": ready_for_limited_individual_pilot,
        "ready_for_broad_individual_release": ready_for_broad_individual_release,
        "ready_for_git_shared_research_release": ready_for_git_shared_research_release,
        "release_report_status": release["status"],
        "repository_hygiene_status": hygiene["status"],
        "repository_hygiene_strict": True,
        "workspace_merge_available": merge_supported,
        "validation_evidence_status": validations["status"],
        "validation_evidence_summary": {
            "required_validation_types": validations["required_validation_types"],
            "missing_required_validation": validations["missing_required_validation"],
            "blocked_required_validation": validations["blocked_required_validation"],
            "local_fixture_validation_complete": validations["local_fixture_validation_complete"],
            "external_validation_complete": validations["external_validation_complete"],
            "publication_approved": validations["publication_approved"],
            "record_count": validations["record_count"],
        },
        "merge_fixture_rehearsal_status": next(
            (row["status"] for row in validations["required_status"] if row["validation_type"] == "merge_fixture_rehearsal"),
            "missing",
        ),
        "representative_workspace_performance_status": next(
            (row["status"] for row in validations["required_status"] if row["validation_type"] == "representative_workspace_performance"),
            "missing",
        ),
        "release_notes_status": "present" if (release_root / "docs" / "release_notes_0.1.0.md").exists() else "missing",
        "publication_tag_approval_status": "approved" if validations["publication_approved"] else "not_requested",
        "future_multi_user_platform_deferred": True,
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
            "obtain explicit release-owner tag/publication approval only for publication",
            "run repository hygiene before sharing",
            "use workspace merge dry-run before importing another repository",
        ],
    }
