from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from research_assistant.adapters.mcp_permissions import (
    ALLOWED_ARXIV_DOMAINS,
    append_mcp_audit_event,
    arxiv_destination_path,
    mcp_batch_manifest_dir,
    read_mcp_grant,
    validate_arxiv_batch_grant,
    validate_destination_path,
)
from research_assistant.config import get_paths
from research_assistant.individual_release import atomic_write_json
from research_assistant.ingest.source_manifest import canonical_paper_id
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.source.arxiv_source import fetch_arxiv_structured_source
from research_assistant.source.structured_source import source_record_path

ARXIV_ID_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-zA-Z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$")
MAX_CANDIDATE_FILE_BYTES = 1_000_000
MAX_CANDIDATE_FILE_IDS = 100
ARXIV_CANDIDATE_SCHEMA_VERSION = "arxiv-query-candidates-v1"


def normalize_arxiv_id(arxiv_id: str) -> str:
    value = arxiv_id.strip()
    if value.lower().startswith("arxiv:"):
        value = value.split(":", 1)[1].strip()
    if not ARXIV_ID_PATTERN.match(value):
        raise ValueError(f"invalid arXiv id {arxiv_id}")
    return value


def normalize_arxiv_ids(arxiv_ids: list[str] | None) -> list[str]:
    normalized = [normalize_arxiv_id(item) for item in arxiv_ids or []]
    return sorted(dict.fromkeys(normalized))


def _existing_arxiv_index(root: Path | None = None) -> dict[str, dict[str, Any]]:
    paths = get_paths(root)
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(paths.summaries.glob("*.json")):
        rec = PaperRecord.from_dict(json.loads(path.read_text()))
        if rec.arxiv_id:
            index[rec.arxiv_id.lower()] = {"paper_id": rec.id, "title": rec.title, "source": "summary"}
    for path in sorted((paths.papers_source / "records").glob("*.json")):
        payload = json.loads(path.read_text())
        arxiv_id = (payload.get("provenance") or {}).get("arxiv_id")
        if arxiv_id:
            index[str(arxiv_id).lower()] = {"paper_id": payload.get("paper_id"), "record_path": str(path), "source": "source_record"}
    return index


def _stable_plan_hash(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def candidate_file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_arxiv_candidate_file(candidate_file: Path) -> dict[str, Any]:
    path = candidate_file.expanduser()
    if not path.exists():
        return {"status": "blocked", "issues": [{"code": "candidate_file_missing", "path": str(path)}]}
    if not path.is_file():
        return {"status": "blocked", "issues": [{"code": "candidate_file_not_file", "path": str(path)}]}
    size = path.stat().st_size
    if size > MAX_CANDIDATE_FILE_BYTES:
        return {"status": "blocked", "issues": [{"code": "candidate_file_too_large", "path": str(path), "size": size, "max_bytes": MAX_CANDIDATE_FILE_BYTES}]}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"status": "blocked", "issues": [{"code": "candidate_file_invalid_json", "path": str(path), "message": str(exc)}]}

    issues: list[dict[str, Any]] = []
    schema_version = payload.get("schema_version")
    if schema_version != ARXIV_CANDIDATE_SCHEMA_VERSION:
        issues.append({"code": "candidate_file_schema_mismatch", "expected": ARXIV_CANDIDATE_SCHEMA_VERSION, "actual": schema_version})
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        issues.append({"code": "candidate_file_candidates_not_list"})
        candidates = []
    if len(candidates) > MAX_CANDIDATE_FILE_IDS:
        issues.append({"code": "candidate_file_too_many_candidates", "count": len(candidates), "max_candidates": MAX_CANDIDATE_FILE_IDS})

    ordered_ids: list[str] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            issues.append({"code": "candidate_not_object", "index": index})
            continue
        arxiv_id = candidate.get("arxiv_id")
        if not isinstance(arxiv_id, str) or not arxiv_id.strip():
            issues.append({"code": "candidate_missing_arxiv_id", "index": index})
            continue
        try:
            ordered_ids.append(normalize_arxiv_id(arxiv_id))
        except ValueError as exc:
            issues.append({"code": "candidate_invalid_arxiv_id", "index": index, "message": str(exc)})
    if len(set(ordered_ids)) != len(ordered_ids):
        issues.append({"code": "candidate_duplicate_arxiv_id"})
    if not ordered_ids:
        issues.append({"code": "candidate_file_empty"})

    metadata = {
        "schema_version": schema_version,
        "candidate_batch_id": payload.get("candidate_batch_id"),
        "query": payload.get("query"),
        "normalized_query": payload.get("normalized_query"),
        "candidate_file": str(path),
        "candidate_file_sha256": candidate_file_checksum(path),
        "ordered_arxiv_ids": ordered_ids,
        "candidate_count": len(ordered_ids),
    }
    return {
        "status": "blocked" if issues else "ok",
        "issues": issues,
        "metadata": metadata,
        "payload": payload,
    }


def plan_arxiv_batch_intake(
    *,
    query: str | None = None,
    arxiv_ids: list[str] | None = None,
    max_papers: int,
    candidate_file: Path | None = None,
    destination: Literal["source", "inbox"] = "source",
    operation: Literal["source_fetch", "pdf_inbox_download", "metadata_only"] = "source_fetch",
    root: Path | None = None,
) -> dict[str, Any]:
    paths = get_paths(root)
    issues = []
    candidate_file_metadata: dict[str, Any] | None = None
    try:
        ids = normalize_arxiv_ids(arxiv_ids)
    except ValueError as exc:
        return {"status": "blocked", "issues": [{"code": "invalid_arxiv_id", "message": str(exc)}]}
    if candidate_file is not None:
        candidate_result = load_arxiv_candidate_file(candidate_file)
        if candidate_result["status"] != "ok":
            return {
                "status": "blocked",
                "issues": candidate_result["issues"],
                "writes_during_planning": False,
                "requires_grant": True,
            }
        candidate_file_metadata = candidate_result["metadata"]
        candidate_ids = candidate_file_metadata["ordered_arxiv_ids"]
        if ids and ids != candidate_ids:
            issues.append({"code": "candidate_file_ids_mismatch", "expected": candidate_ids, "actual": ids})
        ids = candidate_ids
        query = query or candidate_file_metadata.get("query")
    if not ids and not query:
        issues.append({"code": "missing_scope", "message": "provide explicit arXiv IDs or a query"})
    if query and not ids:
        issues.append({"code": "query_search_not_implemented", "message": "query-based live arXiv discovery is deferred; provide explicit IDs"})
    if max_papers <= 0:
        issues.append({"code": "invalid_max_papers", "max_papers": max_papers})
    if len(ids) > max_papers:
        issues.append({"code": "max_papers_exceeded", "count": len(ids), "max_papers": max_papers})
    destination_path = arxiv_destination_path(destination, root=paths.root)
    dest_validation = validate_destination_path(destination_path, root=paths.root)
    if dest_validation["status"] != "ok":
        issues.append(dest_validation)

    existing = _existing_arxiv_index(paths.root)
    candidates = []
    for arxiv_id in ids:
        duplicate = existing.get(arxiv_id.lower())
        paper_id = canonical_paper_id(f"arxiv:{arxiv_id}")
        candidates.append({
            "arxiv_id": arxiv_id,
            "paper_id": paper_id,
            "duplicate_status": "possible_duplicate" if duplicate else "unique",
            "duplicate": duplicate,
            "source_url": f"https://arxiv.org/e-print/{arxiv_id}",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
        })

    plan_core = {
        "schema_version": "arxiv-batch-plan-v1",
        "workspace_root": str(paths.root.resolve()),
        "query": query,
        "arxiv_ids": ids,
        "max_papers": max_papers,
        "destination": destination,
        "destination_path": str(destination_path),
        "operation": operation,
        "candidate_file": candidate_file_metadata,
        "allowed_domains": sorted(ALLOWED_ARXIV_DOMAINS),
        "duplicate_policy": "skip_existing",
        "overwrite_policy": "no_overwrite",
        "review_policy": "review_material_only",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    plan_hash = _stable_plan_hash(plan_core)
    return {
        **plan_core,
        "plan_hash": plan_hash,
        "status": "blocked" if issues else "ready_for_grant",
        "issues": issues,
        "writes_during_planning": False,
        "requires_grant": True,
        "manifest_path": str(mcp_batch_manifest_dir(paths.root) / f"{plan_hash}.manifest.json"),
        "warnings": [
            "Batch intake creates review material only and must not mark records approved.",
            "Query-based live arXiv discovery is deferred; explicit ID lists are supported first.",
        ],
    }


def run_arxiv_batch_intake(
    *,
    grant_id: str,
    plan_hash: str,
    arxiv_ids: list[str] | None = None,
    candidate_file: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    paths = get_paths(root)
    try:
        ids = normalize_arxiv_ids(arxiv_ids)
    except ValueError as exc:
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": [{"code": "invalid_arxiv_id", "message": str(exc)}]}
    if candidate_file is not None:
        candidate_result = load_arxiv_candidate_file(candidate_file)
        if candidate_result["status"] != "ok":
            return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": candidate_result["issues"]}
        candidate_ids = candidate_result["metadata"]["ordered_arxiv_ids"]
        if ids and ids != candidate_ids:
            return {
                "status": "blocked",
                "grant_id": grant_id,
                "plan_hash": plan_hash,
                "issues": [{"code": "candidate_file_ids_mismatch", "expected": candidate_ids, "actual": ids}],
            }
        ids = candidate_ids
    if not ids:
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": [{"code": "missing_arxiv_ids"}]}
    grant = read_mcp_grant(grant_id, root=paths.root)
    validation = validate_arxiv_batch_grant(
        grant,
        plan_hash=plan_hash,
        operation="source_fetch",
        destination="source",
        root=paths.root,
        arxiv_ids=ids,
    )
    if validation["status"] != "ok":
        append_mcp_audit_event("batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": validation["issues"], "plan_hash": plan_hash})
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": validation["issues"]}

    plan = plan_arxiv_batch_intake(
        arxiv_ids=ids,
        candidate_file=candidate_file,
        max_papers=int(grant["max_papers"]),
        destination="source",
        operation="source_fetch",
        root=paths.root,
    )
    if plan["plan_hash"] != plan_hash:
        issue = {"code": "recomputed_plan_hash_mismatch", "expected": plan_hash, "actual": plan["plan_hash"]}
        append_mcp_audit_event("batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": [issue]})
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": [issue]}

    append_mcp_audit_event("batch_started", grant_id=grant_id, root=paths.root, detail={"plan_hash": plan_hash, "arxiv_ids": ids})
    results = []
    skipped = []
    failures = []
    for candidate in plan["candidates"]:
        arxiv_id = candidate["arxiv_id"]
        if candidate.get("duplicate_status") != "unique" and grant.get("duplicate_policy") == "skip_existing":
            row = {"arxiv_id": arxiv_id, "status": "skipped_duplicate", "duplicate": candidate.get("duplicate")}
            skipped.append(row)
            results.append(row)
            append_mcp_audit_event("batch_item_skipped", grant_id=grant_id, root=paths.root, detail=row)
            continue
        paper_id = candidate["paper_id"]
        try:
            record = fetch_arxiv_structured_source(arxiv_id, root=paths.root, paper_id=paper_id)
            row = {
                "arxiv_id": arxiv_id,
                "paper_id": paper_id,
                "status": record.status,
                "source_type": record.source_type,
                "primary_for_audit": record.primary_for_audit,
                "record_path": str(source_record_path(paths.papers_source, paper_id)),
                "limitations": record.limitations,
            }
            results.append(row)
            if record.status not in {"available", "unavailable", "failed"}:
                failures.append(row)
            append_mcp_audit_event("batch_item_completed", grant_id=grant_id, root=paths.root, detail=row)
        except Exception as exc:
            row = {"arxiv_id": arxiv_id, "paper_id": paper_id, "status": "failed", "reason": str(exc)}
            failures.append(row)
            results.append(row)
            append_mcp_audit_event("batch_item_failed", grant_id=grant_id, root=paths.root, detail=row)

    manifest = {
        "schema_version": "arxiv-batch-manifest-v1",
        "status": "completed_with_failures" if failures else "completed",
        "grant_id": grant_id,
        "plan_hash": plan_hash,
        "workspace_root": str(paths.root.resolve()),
        "operation": "source_fetch",
        "destination": "source",
        "attempted_count": len(results),
        "fetched_count": len([row for row in results if row.get("status") == "available"]),
        "skipped_duplicates": skipped,
        "failures": failures,
        "results": results,
        "review_policy": "review_material_only",
        "limitations": [
            "Batch source intake creates review material only.",
            "Fetched source records are not approved technical audit conclusions.",
        ],
    }
    manifest_path = Path(grant.get("manifest_path") or (mcp_batch_manifest_dir(paths.root) / f"{grant_id}.manifest.json"))
    atomic_write_json(manifest_path, manifest)
    append_mcp_audit_event("batch_completed", grant_id=grant_id, root=paths.root, detail={
        "manifest_path": str(manifest_path),
        "attempted_count": manifest["attempted_count"],
        "fetched_count": manifest["fetched_count"],
        "failure_count": len(failures),
    })
    return {
        "status": manifest["status"],
        "grant_id": grant_id,
        "plan_hash": plan_hash,
        "attempted_count": manifest["attempted_count"],
        "fetched_count": manifest["fetched_count"],
        "skipped_duplicates": skipped,
        "failures": failures,
        "manifest_path": str(manifest_path),
        "audit_path": grant.get("audit_path"),
        "review_policy": "review_material_only",
    }
