from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.individual_release import atomic_write_json
from research_assistant.query.review import VALID_REVIEW_STATUSES
from research_assistant.schemas.artifact import stable_id

REVIEW_WRITE_SCHEMA_VERSION = "review-write-confirmation-v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _review_write_root(root: Path | None = None) -> Path:
    return get_paths(root).governance / "review_write"


def _proposals_dir(root: Path | None = None) -> Path:
    return _review_write_root(root) / "proposals"


def _audit_dir(root: Path | None = None) -> Path:
    return _review_write_root(root) / "audit"


def _proposal_path(confirmation_id: str, *, root: Path | None = None) -> Path:
    return _proposals_dir(root) / f"{confirmation_id}.json"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _append_audit(event_type: str, *, root: Path | None = None, detail: dict[str, Any]) -> dict[str, Any]:
    paths = get_paths(root)
    audit_dir = _audit_dir(paths.root)
    audit_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": REVIEW_WRITE_SCHEMA_VERSION,
        "event_id": stable_id("review_write_event", event_type, utc_now_iso(), detail),
        "event_type": event_type,
        "created_at": utc_now_iso(),
        "workspace_root": str(paths.root),
        "detail": detail,
    }
    path = audit_dir / "review_write.audit.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {"status": "recorded", "event": event, "audit_path": str(path)}


def propose_review_status(
    *,
    paper_id: str,
    status: str,
    root: Path | None = None,
    expires_minutes: int = 30,
) -> dict[str, Any]:
    if status not in VALID_REVIEW_STATUSES:
        return {"status": "blocked", "issues": [{"code": "invalid_review_status", "review_status": status}]}
    if expires_minutes <= 0:
        return {"status": "blocked", "issues": [{"code": "invalid_expiry", "expires_minutes": expires_minutes}]}
    paths = get_paths(root)
    summary_path = paths.summaries / f"{paper_id}.json"
    if not summary_path.exists():
        return {"status": "blocked", "issues": [{"code": "paper_summary_missing", "paper_id": paper_id, "path": str(summary_path)}]}
    data = json.loads(summary_path.read_text())
    old_status = data.get("review_status", "needs_review")
    old_hash = _file_sha256(summary_path)
    created_at = utc_now_iso()
    expires_at = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=expires_minutes)).isoformat()
    confirmation_nonce = secrets.token_hex(8)
    confirmation_id = stable_id("review_write", paths.root, paper_id, old_status, status, old_hash, created_at, confirmation_nonce)
    proposal = {
        "schema_version": REVIEW_WRITE_SCHEMA_VERSION,
        "confirmation_id": confirmation_id,
        "confirmation_nonce": confirmation_nonce,
        "operation": "mark_review_status",
        "workspace_root": str(paths.root),
        "paper_id": paper_id,
        "target_path": str(summary_path),
        "old_value": old_status,
        "new_value": status,
        "old_file_sha256": old_hash,
        "created_at": created_at,
        "expires_at": expires_at,
        "risks": [
            "Changes trusted review state.",
            "Does not certify mathematical correctness.",
            "Blocks if the summary file changed after proposal creation.",
        ],
        "requires_confirmation": True,
        "mcp_exposure": "not_exposed",
    }
    atomic_write_json(_proposal_path(confirmation_id, root=paths.root), proposal)
    _append_audit("proposal_created", root=paths.root, detail={"confirmation_id": confirmation_id, "paper_id": paper_id, "old_value": old_status, "new_value": status})
    return {"status": "proposed", "proposal": proposal, "proposal_path": str(_proposal_path(confirmation_id, root=paths.root))}


def apply_review_write(*, confirmation_id: str, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    proposal_path = _proposal_path(confirmation_id, root=paths.root)
    if not proposal_path.exists():
        return {"status": "blocked", "issues": [{"code": "proposal_missing", "confirmation_id": confirmation_id}]}
    proposal = json.loads(proposal_path.read_text())
    issues = []
    if proposal.get("operation") != "mark_review_status":
        issues.append({"code": "unsupported_operation", "operation": proposal.get("operation")})
    if Path(str(proposal.get("workspace_root"))).resolve() != paths.root.resolve():
        issues.append({"code": "workspace_root_mismatch", "expected": proposal.get("workspace_root"), "actual": str(paths.root)})
    if parse_iso(proposal["expires_at"]) <= datetime.now(timezone.utc):
        issues.append({"code": "proposal_expired", "expires_at": proposal["expires_at"]})
    target_path = Path(proposal["target_path"])
    if not target_path.exists():
        issues.append({"code": "target_missing", "target_path": str(target_path)})
    elif _file_sha256(target_path) != proposal.get("old_file_sha256"):
        issues.append({"code": "target_changed", "target_path": str(target_path)})
    if proposal.get("new_value") not in VALID_REVIEW_STATUSES:
        issues.append({"code": "invalid_review_status", "review_status": proposal.get("new_value")})
    if issues:
        _append_audit("apply_blocked", root=paths.root, detail={"confirmation_id": confirmation_id, "issues": issues})
        return {"status": "blocked", "issues": issues, "confirmation_id": confirmation_id}

    data = json.loads(target_path.read_text())
    data["review_status"] = proposal["new_value"]
    data["requires_manual_review"] = proposal["new_value"] != "approved"
    review_summary = dict(data.get("review_summary") or {})
    review_summary["status"] = proposal["new_value"]
    data["review_summary"] = review_summary
    atomic_write_json(target_path, data)
    new_hash = _file_sha256(target_path)
    _append_audit("apply_completed", root=paths.root, detail={
        "confirmation_id": confirmation_id,
        "paper_id": proposal["paper_id"],
        "old_value": proposal["old_value"],
        "new_value": proposal["new_value"],
        "old_file_sha256": proposal["old_file_sha256"],
        "new_file_sha256": new_hash,
        "target_path": str(target_path),
    })
    proposal["applied_at"] = utc_now_iso()
    proposal["new_file_sha256"] = new_hash
    proposal["status"] = "applied"
    atomic_write_json(proposal_path, proposal)
    return {
        "status": "applied",
        "confirmation_id": confirmation_id,
        "paper_id": proposal["paper_id"],
        "old_value": proposal["old_value"],
        "new_value": proposal["new_value"],
        "target_path": str(target_path),
        "old_file_sha256": proposal["old_file_sha256"],
        "new_file_sha256": new_hash,
        "mcp_exposure": "not_exposed",
    }


def review_write_status(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    return {
        "schema_version": REVIEW_WRITE_SCHEMA_VERSION,
        "status": "prototype_cli_only",
        "workspace_root": str(paths.root),
        "proposal_path": str(_proposals_dir(paths.root)),
        "audit_path": str(_audit_dir(paths.root)),
        "mcp_exposed": False,
        "supported_operations": ["mark_review_status"],
        "limitations": [
            "Review-write is a CLI-only prototype.",
            "MCP review-write tools remain disabled.",
            "Each apply verifies file hash and blocks on conflict.",
        ],
    }
