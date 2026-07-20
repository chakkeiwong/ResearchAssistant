from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from research_assistant.config import get_paths
from research_assistant.core_utils import utc_now_iso
from research_assistant.individual_release import atomic_write_json
from research_assistant.schemas.artifact import stable_id
from research_assistant.storage.file_store import FileStore

MCP_PERMISSION_SCHEMA_VERSION = "local-mcp-permissions-v1"
ALLOWED_ARXIV_DOMAINS = {"arxiv.org", "export.arxiv.org"}
MCP_MODES = {"read_only", "arxiv_batch_intake", "review_write", "destructive"}
ARXIV_DESTINATIONS = {"source", "inbox"}
ARXIV_OPERATIONS = {"source_fetch", "pdf_inbox_download", "metadata_only"}


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class ArxivBatchIntakeGrant:
    grant_id: str
    mode: str
    operation: str
    workspace_root: str
    created_at: str
    expires_at: str
    plan_hash: str
    destination: str
    max_papers: int
    allowed_domains: list[str]
    duplicate_policy: str = "skip_existing"
    overwrite_policy: str = "no_overwrite"
    review_policy: str = "review_material_only"
    query: str | None = None
    arxiv_ids: list[str] = field(default_factory=list)
    manifest_path: str | None = None
    audit_path: str | None = None
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": MCP_PERMISSION_SCHEMA_VERSION,
            **asdict(self),
        }


def mcp_governance_root(root: Path | None = None) -> Path:
    return get_paths(root).governance / "mcp"


def mcp_grants_dir(root: Path | None = None) -> Path:
    return mcp_governance_root(root) / "grants"


def mcp_audit_dir(root: Path | None = None) -> Path:
    return mcp_governance_root(root) / "audit"


def mcp_batch_manifest_dir(root: Path | None = None) -> Path:
    return mcp_governance_root(root) / "batch_manifests"


def _store(root: Path | None = None) -> FileStore:
    return FileStore(get_paths(root).local_research)


def _grant_path(grant_id: str, *, root: Path | None = None) -> Path:
    return mcp_grants_dir(root) / f"{grant_id}.json"


def _safe_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def validate_workspace_root(root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    resolved_root = paths.root.resolve()
    resolved_local = paths.local_research.resolve()
    if not _safe_relative_to(resolved_local, resolved_root):
        return {
            "status": "blocked",
            "code": "workspace_escape",
            "workspace_root": str(resolved_root),
            "local_research": str(resolved_local),
        }
    return {"status": "ok", "workspace_root": str(resolved_root), "local_research": str(resolved_local)}


def validate_destination_path(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    resolved = path.resolve()
    if not _safe_relative_to(resolved, paths.local_research.resolve()):
        return {"status": "blocked", "code": "destination_outside_workspace", "path": str(resolved)}
    return {"status": "ok", "path": str(resolved)}


def validate_allowed_domains(urls: list[str], allowed_domains: set[str] | None = None) -> dict[str, Any]:
    allowed = allowed_domains or ALLOWED_ARXIV_DOMAINS
    blocked = []
    for url in urls:
        host = urlparse(url).netloc.lower()
        if host not in allowed:
            blocked.append({"url": url, "host": host})
    return {"status": "blocked" if blocked else "ok", "blocked": blocked, "allowed_domains": sorted(allowed)}


def arxiv_destination_path(destination: str, *, root: Path | None = None) -> Path:
    paths = get_paths(root)
    if destination == "source":
        return paths.papers_source
    if destination == "inbox":
        return paths.local_research / "inbox"
    raise ValueError(f"unsupported arXiv destination {destination}")


def create_arxiv_batch_grant(
    *,
    plan_hash: str,
    operation: Literal["source_fetch", "pdf_inbox_download", "metadata_only"] = "source_fetch",
    destination: Literal["source", "inbox"] = "source",
    max_papers: int,
    expires_hours: int = 2,
    root: Path | None = None,
    query: str | None = None,
    arxiv_ids: list[str] | None = None,
    duplicate_policy: str = "skip_existing",
) -> dict[str, Any]:
    paths = get_paths(root)
    workspace = validate_workspace_root(paths.root)
    if workspace["status"] != "ok":
        return {"status": "blocked", "issues": [workspace]}
    if operation not in ARXIV_OPERATIONS:
        return {"status": "blocked", "issues": [{"code": "unsupported_operation", "operation": operation}]}
    if destination not in ARXIV_DESTINATIONS:
        return {"status": "blocked", "issues": [{"code": "unsupported_destination", "destination": destination}]}
    if max_papers <= 0:
        return {"status": "blocked", "issues": [{"code": "invalid_max_papers", "max_papers": max_papers}]}
    if expires_hours <= 0:
        return {"status": "blocked", "issues": [{"code": "invalid_expiry", "expires_hours": expires_hours}]}
    ids = sorted(dict.fromkeys(arxiv_ids or []))
    if ids and len(ids) > max_papers:
        return {"status": "blocked", "issues": [{"code": "max_papers_exceeded", "count": len(ids), "max_papers": max_papers}]}
    dest_path = arxiv_destination_path(destination, root=paths.root)
    dest_validation = validate_destination_path(dest_path, root=paths.root)
    if dest_validation["status"] != "ok":
        return {"status": "blocked", "issues": [dest_validation]}

    created_at = utc_now_iso()
    expires_at = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=expires_hours)).isoformat()
    grant_id = stable_id("mcp_grant", paths.root, plan_hash, operation, destination, max_papers, created_at)
    manifest_path = mcp_batch_manifest_dir(paths.root) / f"{grant_id}.manifest.json"
    audit_path = mcp_audit_dir(paths.root) / f"{grant_id}.audit.jsonl"
    grant = ArxivBatchIntakeGrant(
        grant_id=grant_id,
        mode="arxiv_batch_intake",
        operation=operation,
        workspace_root=str(paths.root.resolve()),
        created_at=created_at,
        expires_at=expires_at,
        plan_hash=plan_hash,
        destination=destination,
        max_papers=max_papers,
        allowed_domains=sorted(ALLOWED_ARXIV_DOMAINS),
        duplicate_policy=duplicate_policy,
        query=query,
        arxiv_ids=ids,
        manifest_path=str(manifest_path),
        audit_path=str(audit_path),
    )
    _store(paths.root).write_json(_grant_path(grant_id, root=paths.root), grant.to_dict())
    append_mcp_audit_event(
        "grant_created",
        grant_id=grant_id,
        root=paths.root,
        detail={"operation": operation, "destination": destination, "max_papers": max_papers, "plan_hash": plan_hash},
    )
    return {"status": "created", "grant": grant.to_dict(), "grant_path": str(_grant_path(grant_id, root=paths.root))}


def read_mcp_grant(grant_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _store(root).read_json(_grant_path(grant_id, root=root))


def list_mcp_grants(*, root: Path | None = None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(mcp_grants_dir(root).glob("*.json")):
        payload = _store(root).read_json(path)
        payload["grant_path"] = str(path)
        rows.append(payload)
    return rows


def append_mcp_audit_event(event_type: str, *, grant_id: str | None = None, root: Path | None = None, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    audit_dir = mcp_audit_dir(paths.root)
    audit_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": MCP_PERMISSION_SCHEMA_VERSION,
        "event_id": stable_id("mcp_audit", event_type, grant_id or "", utc_now_iso(), json.dumps(detail or {}, sort_keys=True)),
        "event_type": event_type,
        "created_at": utc_now_iso(),
        "workspace_root": str(paths.root.resolve()),
        "grant_id": grant_id,
        "detail": detail or {},
    }
    path = audit_dir / (f"{grant_id}.audit.jsonl" if grant_id else "mcp.audit.jsonl")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {"status": "recorded", "event": event, "audit_path": str(path)}


def list_mcp_audit_events(*, root: Path | None = None, grant_id: str | None = None) -> list[dict[str, Any]]:
    audit_dir = mcp_audit_dir(root)
    pattern = f"{grant_id}.audit.jsonl" if grant_id else "*.audit.jsonl"
    events = []
    for path in sorted(audit_dir.glob(pattern)):
        for line in path.read_text().splitlines():
            if line.strip():
                event = json.loads(line)
                event["audit_path"] = str(path)
                events.append(event)
    return events


def validate_arxiv_batch_grant(
    grant: dict[str, Any],
    *,
    plan_hash: str,
    operation: str,
    destination: str,
    root: Path | None = None,
    arxiv_ids: list[str] | None = None,
) -> dict[str, Any]:
    paths = get_paths(root)
    issues = []
    if grant.get("mode") != "arxiv_batch_intake":
        issues.append({"code": "wrong_mode", "mode": grant.get("mode")})
    if grant.get("operation") != operation:
        issues.append({"code": "operation_mismatch", "expected": grant.get("operation"), "actual": operation})
    if grant.get("destination") != destination:
        issues.append({"code": "destination_mismatch", "expected": grant.get("destination"), "actual": destination})
    if grant.get("plan_hash") != plan_hash:
        issues.append({"code": "plan_hash_mismatch", "expected": grant.get("plan_hash"), "actual": plan_hash})
    if Path(str(grant.get("workspace_root"))).resolve() != paths.root.resolve():
        issues.append({"code": "workspace_root_mismatch", "expected": grant.get("workspace_root"), "actual": str(paths.root.resolve())})
    expires_at = grant.get("expires_at")
    if not expires_at:
        issues.append({"code": "expires_at_missing"})
    else:
        if parse_iso_datetime(expires_at) <= datetime.now(timezone.utc):
            issues.append({"code": "grant_expired", "expires_at": expires_at})
    if arxiv_ids is not None:
        requested = sorted(dict.fromkeys(arxiv_ids))
        granted = sorted(grant.get("arxiv_ids") or [])
        if granted and requested != granted:
            issues.append({"code": "arxiv_ids_mismatch", "expected": granted, "actual": requested})
        if len(requested) > int(grant.get("max_papers", 0)):
            issues.append({"code": "max_papers_exceeded", "count": len(requested), "max_papers": grant.get("max_papers")})
    dest_path = arxiv_destination_path(destination, root=paths.root)
    dest_validation = validate_destination_path(dest_path, root=paths.root)
    if dest_validation["status"] != "ok":
        issues.append(dest_validation)
    missing_domains = sorted(ALLOWED_ARXIV_DOMAINS - set(grant.get("allowed_domains") or []))
    if missing_domains:
        issues.append({"code": "required_domains_missing", "missing_domains": missing_domains})
    return {"status": "blocked" if issues else "ok", "issues": issues, "grant_id": grant.get("grant_id")}


def mcp_permissions_status(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    return {
        "schema_version": MCP_PERMISSION_SCHEMA_VERSION,
        "status": "ok",
        "workspace_root": str(paths.root),
        "modes": sorted(MCP_MODES),
        "default_mode": "read_only",
        "write_grants_path": str(mcp_grants_dir(paths.root)),
        "audit_path": str(mcp_audit_dir(paths.root)),
        "batch_manifest_path": str(mcp_batch_manifest_dir(paths.root)),
        "allowed_arxiv_domains": sorted(ALLOWED_ARXIV_DOMAINS),
        "destructive_tools_enabled": False,
        "review_write_enabled": False,
    }
