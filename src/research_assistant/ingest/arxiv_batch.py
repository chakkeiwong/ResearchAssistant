from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Literal
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from research_assistant.adapters.mcp_permissions import (
    ALLOWED_ARXIV_DOMAINS,
    append_mcp_audit_event,
    arxiv_destination_path,
    mcp_batch_manifest_dir,
    read_mcp_grant,
    validate_arxiv_batch_grant,
    validate_allowed_domains,
    validate_destination_path,
)
from research_assistant.config import get_paths
from research_assistant.individual_release import atomic_write_json
from research_assistant.ingest.source_manifest import canonical_paper_id
from research_assistant.schemas.artifact import stable_id
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.source.arxiv_source import fetch_arxiv_structured_source
from research_assistant.source.structured_source import source_record_path

ARXIV_ID_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-zA-Z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$")
MAX_CANDIDATE_FILE_BYTES = 1_000_000
MAX_CANDIDATE_FILE_IDS = 100
ARXIV_CANDIDATE_SCHEMA_VERSION = "arxiv-query-candidates-v1"
ARXIV_QUERY_ENDPOINT = "https://export.arxiv.org/api/query"
MAX_LIVE_QUERY_CANDIDATES = 50
MAX_ARXIV_QUERY_RESPONSE_BYTES = 2_000_000


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


def plan_file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atom_text(element: ET.Element, path: str, namespaces: dict[str, str]) -> str | None:
    found = element.find(path, namespaces)
    if found is None or found.text is None:
        return None
    return " ".join(found.text.split())


def _arxiv_id_from_entry(entry: ET.Element, namespaces: dict[str, str]) -> str | None:
    raw_id = _atom_text(entry, "atom:id", namespaces)
    if not raw_id:
        return None
    value = raw_id.rstrip("/").rsplit("/", 1)[-1]
    try:
        return normalize_arxiv_id(value)
    except ValueError:
        return None


def discover_arxiv_query_candidates(
    *,
    query: str,
    max_candidates: int,
    output_candidate_file: Path,
    timeout_seconds: int = 30,
    root: Path | None = None,
    endpoint_url: str = ARXIV_QUERY_ENDPOINT,
) -> dict[str, Any]:
    normalized_query = " ".join(query.split()).strip()
    issues: list[dict[str, Any]] = []
    if not normalized_query:
        issues.append({"code": "empty_query"})
    if max_candidates <= 0:
        issues.append({"code": "invalid_max_candidates", "max_candidates": max_candidates})
    if max_candidates > MAX_LIVE_QUERY_CANDIDATES:
        issues.append({"code": "max_candidates_exceeds_live_cap", "max_candidates": max_candidates, "cap": MAX_LIVE_QUERY_CANDIDATES})
    if timeout_seconds <= 0:
        issues.append({"code": "invalid_timeout_seconds", "timeout_seconds": timeout_seconds})
    endpoint_host = urllib.parse.urlparse(endpoint_url).netloc.lower()
    if endpoint_host != "export.arxiv.org":
        issues.append({"code": "endpoint_domain_not_allowed", "endpoint_url": endpoint_url, "allowed_domain": "export.arxiv.org"})
    if issues:
        return {"status": "blocked", "issues": issues, "writes_during_discovery": False}

    params = urllib.parse.urlencode({
        "search_query": f"all:{normalized_query}",
        "start": "0",
        "max_results": str(max_candidates),
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    request_url = f"{endpoint_url}?{params}"
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request_url, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            final_host = urllib.parse.urlparse(final_url).netloc.lower()
            if final_host != "export.arxiv.org":
                return {
                    "status": "blocked",
                    "issues": [{"code": "query_redirect_domain_not_allowed", "host": final_host, "allowed_domain": "export.arxiv.org"}],
                    "writes_during_discovery": False,
                }
            body = response.read(MAX_ARXIV_QUERY_RESPONSE_BYTES + 1)
            http_status = getattr(response, "status", None)
    except Exception as exc:
        return {
            "status": "blocked",
            "issues": [{"code": "query_request_failed", "message": str(exc)}],
            "writes_during_discovery": False,
        }
    elapsed = time.perf_counter() - started
    if len(body) > MAX_ARXIV_QUERY_RESPONSE_BYTES:
        return {
            "status": "blocked",
            "issues": [{"code": "query_response_too_large", "max_bytes": MAX_ARXIV_QUERY_RESPONSE_BYTES}],
            "writes_during_discovery": False,
        }

    namespaces = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        feed = ET.fromstring(body)
    except ET.ParseError as exc:
        return {
            "status": "blocked",
            "issues": [{"code": "query_response_invalid_xml", "message": str(exc)}],
            "writes_during_discovery": False,
        }

    candidates: list[dict[str, Any]] = []
    skipped_entries: list[dict[str, Any]] = []
    for index, entry in enumerate(feed.findall("atom:entry", namespaces)):
        arxiv_id = _arxiv_id_from_entry(entry, namespaces)
        if arxiv_id is None:
            skipped_entries.append({"index": index, "reason": "missing_or_invalid_arxiv_id"})
            continue
        title = _atom_text(entry, "atom:title", namespaces) or f"arXiv {arxiv_id}"
        authors = [
            name
            for author in entry.findall("atom:author", namespaces)
            if (name := _atom_text(author, "atom:name", namespaces))
        ]
        entry_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        for link in entry.findall("atom:link", namespaces):
            href = link.attrib.get("href")
            if not href:
                continue
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = href
            elif link.attrib.get("rel") == "alternate":
                entry_url = href
        primary = entry.find("arxiv:primary_category", namespaces)
        primary_category = primary.attrib.get("term") if primary is not None else None
        candidates.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "entry_url": entry_url,
            "pdf_url": pdf_url,
            "source_url": f"https://arxiv.org/e-print/{arxiv_id}",
            "primary_category": primary_category,
            "provenance_index": len(candidates),
        })
        if len(candidates) >= max_candidates:
            break

    if not candidates:
        return {
            "status": "blocked",
            "issues": [{"code": "query_returned_no_candidates", "skipped_entries": skipped_entries}],
            "writes_during_discovery": False,
        }

    created_at = _utc_now_iso()
    output_path = output_candidate_file.expanduser()
    payload = {
        "schema_version": ARXIV_CANDIDATE_SCHEMA_VERSION,
        "candidate_batch_id": stable_id("arxiv_query_candidates", normalized_query.lower(), max_candidates, created_at),
        "created_at": created_at,
        "workspace_root": str(get_paths(root).root),
        "query": query,
        "normalized_query": normalized_query.lower(),
        "endpoint_url": endpoint_url,
        "max_candidates": max_candidates,
        "request_timeout_seconds": timeout_seconds,
        "result_ordering": "api_relevance_order",
        "pagination_count": 1,
        "source_status": {
            "status": "available",
            "http_status": http_status,
            "elapsed_seconds": round(elapsed, 3),
            "skipped_entry_count": len(skipped_entries),
        },
        "candidates": candidates,
    }
    atomic_write_json(output_path, payload)
    checksum = candidate_file_checksum(output_path)
    return {
        "status": "created",
        "query": query,
        "max_candidates": max_candidates,
        "candidate_count": len(candidates),
        "candidate_file": str(output_path),
        "candidate_file_sha256": checksum,
        "ordered_arxiv_ids": [candidate["arxiv_id"] for candidate in candidates],
        "pagination_count": 1,
        "elapsed_seconds": round(elapsed, 3),
        "source_status": payload["source_status"],
        "writes_during_discovery": True,
        "written_outputs": ["candidate_file"],
        "limitations": [
            "Live discovery writes only a pinned candidate file.",
            "No source or PDF intake is performed by discovery.",
            "Live query discovery is not exposed through MCP.",
        ],
    }


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


def _normalize_arxiv_ids_preserve_order(arxiv_ids: list[Any]) -> tuple[list[str], list[dict[str, Any]]]:
    normalized: list[str] = []
    issues: list[dict[str, Any]] = []
    for index, value in enumerate(arxiv_ids):
        if not isinstance(value, str) or not value.strip():
            issues.append({"code": "plan_file_invalid_arxiv_id", "index": index, "value": value})
            continue
        try:
            normalized.append(normalize_arxiv_id(value))
        except ValueError as exc:
            issues.append({"code": "plan_file_invalid_arxiv_id", "index": index, "message": str(exc)})
    if len(set(normalized)) != len(normalized):
        issues.append({"code": "plan_file_duplicate_arxiv_id"})
    return normalized, issues


def load_arxiv_plan_file(
    plan_file: Path,
    *,
    expected_plan_hash: str | None = None,
    expected_plan_file_sha256: str | None = None,
    candidate_file: Path | None = None,
    root: Path | None = None,
    operation: Literal["source_fetch", "pdf_inbox_download", "metadata_only"] = "source_fetch",
    destination: Literal["source", "inbox"] = "source",
) -> dict[str, Any]:
    path = plan_file.expanduser()
    paths = get_paths(root)
    if not path.exists():
        return {"status": "blocked", "issues": [{"code": "plan_file_missing", "path": str(path)}]}
    if not path.is_file():
        return {"status": "blocked", "issues": [{"code": "plan_file_not_file", "path": str(path)}]}
    checksum = plan_file_checksum(path)
    issues: list[dict[str, Any]] = []
    if expected_plan_file_sha256 and checksum != expected_plan_file_sha256:
        issues.append({
            "code": "plan_file_sha256_mismatch",
            "expected": expected_plan_file_sha256,
            "actual": checksum,
        })
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {
            "status": "blocked",
            "issues": [{"code": "plan_file_invalid_json", "path": str(path), "message": str(exc)}],
            "plan_file_sha256": checksum,
        }

    if payload.get("schema_version") != "arxiv-batch-plan-v1":
        issues.append({"code": "plan_file_schema_mismatch", "actual": payload.get("schema_version")})
    plan_hash = payload.get("plan_hash")
    if expected_plan_hash and plan_hash != expected_plan_hash:
        issues.append({"code": "plan_hash_mismatch", "expected": expected_plan_hash, "actual": plan_hash})
    if payload.get("status") != "ready_for_grant":
        issues.append({"code": "plan_file_status_not_ready_for_grant", "actual": payload.get("status")})
    if payload.get("operation") != operation:
        issues.append({"code": "operation_mismatch", "expected": operation, "actual": payload.get("operation")})
    if payload.get("destination") != destination:
        issues.append({"code": "destination_mismatch", "expected": destination, "actual": payload.get("destination")})
    if Path(str(payload.get("workspace_root"))).resolve() != paths.root.resolve():
        issues.append({
            "code": "workspace_root_mismatch",
            "expected": str(paths.root.resolve()),
            "actual": payload.get("workspace_root"),
        })

    plan_ids_raw = payload.get("arxiv_ids")
    if not isinstance(plan_ids_raw, list):
        plan_ids_raw = []
        issues.append({"code": "plan_file_arxiv_ids_not_list"})
    plan_ids, id_issues = _normalize_arxiv_ids_preserve_order(plan_ids_raw)
    issues.extend(id_issues)
    max_papers = payload.get("max_papers")
    if not isinstance(max_papers, int) or max_papers <= 0:
        issues.append({"code": "invalid_max_papers", "max_papers": max_papers})
    elif len(plan_ids) > max_papers:
        issues.append({"code": "max_papers_exceeded", "count": len(plan_ids), "max_papers": max_papers})

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
        issues.append({"code": "plan_file_candidates_not_list"})
    candidate_ids, candidate_id_issues = _normalize_arxiv_ids_preserve_order([
        candidate.get("arxiv_id") if isinstance(candidate, dict) else None
        for candidate in candidates
    ])
    issues.extend(candidate_id_issues)
    if candidate_ids and candidate_ids != plan_ids:
        issues.append({"code": "plan_file_candidate_ids_mismatch", "expected": plan_ids, "actual": candidate_ids})
    if candidates and len(candidates) != len(plan_ids):
        issues.append({"code": "plan_file_candidate_count_mismatch", "expected": len(plan_ids), "actual": len(candidates)})

    urls = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            issues.append({"code": "plan_file_candidate_not_object", "index": index})
            continue
        for key in ("source_url", "pdf_url"):
            url = candidate.get(key)
            if isinstance(url, str) and url:
                urls.append(url)
    domain_validation = validate_allowed_domains(urls, ALLOWED_ARXIV_DOMAINS)
    if domain_validation["status"] != "ok":
        issues.append({"code": "plan_file_domain_not_allowed", "blocked": domain_validation["blocked"]})

    destination_path = payload.get("destination_path")
    if destination_path:
        dest_validation = validate_destination_path(Path(str(destination_path)), root=paths.root)
        if dest_validation["status"] != "ok":
            issues.append(dest_validation)

    candidate_file_metadata = payload.get("candidate_file")
    candidate_file_result = None
    if candidate_file_metadata:
        if candidate_file is None:
            issues.append({"code": "candidate_file_required_for_plan_file_binding"})
        else:
            candidate_file_result = load_arxiv_candidate_file(candidate_file)
            if candidate_file_result["status"] != "ok":
                issues.extend(candidate_file_result["issues"])
            else:
                actual_metadata = candidate_file_result["metadata"]
                actual_ids = actual_metadata["ordered_arxiv_ids"]
                expected_sha = candidate_file_metadata.get("candidate_file_sha256")
                if expected_sha and actual_metadata["candidate_file_sha256"] != expected_sha:
                    issues.append({
                        "code": "candidate_file_sha256_mismatch",
                        "expected": expected_sha,
                        "actual": actual_metadata["candidate_file_sha256"],
                    })
                if actual_ids != plan_ids:
                    issues.append({"code": "candidate_file_ids_mismatch", "expected": plan_ids, "actual": actual_ids})

    metadata = {
        "plan_file": str(path),
        "plan_file_sha256": checksum,
        "plan_hash": plan_hash,
        "ordered_arxiv_ids": plan_ids,
        "candidate_count": len(plan_ids),
        "candidate_file": candidate_file_result["metadata"] if candidate_file_result and candidate_file_result["status"] == "ok" else None,
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
    hash_core = {
        key: value
        for key, value in plan_core.items()
        if key not in {"candidates"}
    }
    hash_core["candidates"] = [
        {
            "arxiv_id": candidate["arxiv_id"],
            "paper_id": candidate["paper_id"],
            "source_url": candidate["source_url"],
            "pdf_url": candidate["pdf_url"],
        }
        for candidate in candidates
    ]
    plan_hash = _stable_plan_hash(hash_core)
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
    plan_file: Path | None = None,
    plan_file_sha256: str | None = None,
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
    plan_file_binding: dict[str, Any] | None = None
    if plan_file is not None:
        plan_binding_result = load_arxiv_plan_file(
            plan_file,
            expected_plan_hash=plan_hash,
            expected_plan_file_sha256=plan_file_sha256,
            candidate_file=candidate_file,
            root=paths.root,
            operation="source_fetch",
            destination="source",
        )
        if plan_binding_result["status"] != "ok":
            append_mcp_audit_event("batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": plan_binding_result["issues"], "plan_hash": plan_hash})
            return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": plan_binding_result["issues"]}
        plan_file_binding = plan_binding_result["metadata"]
        ids = plan_file_binding["ordered_arxiv_ids"]
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
        if plan_file_binding is None:
            append_mcp_audit_event("batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": [issue]})
            return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": [issue]}

    append_mcp_audit_event("batch_started", grant_id=grant_id, root=paths.root, detail={
        "plan_hash": plan_hash,
        "arxiv_ids": ids,
        "plan_file_binding": plan_file_binding,
        "runtime_plan_hash": plan["plan_hash"],
    })
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
        "approved_plan_file": plan_file_binding,
        "runtime_plan_hash": plan["plan_hash"],
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
