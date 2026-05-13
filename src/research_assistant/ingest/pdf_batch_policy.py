from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import time
import urllib.request
from urllib.parse import urlparse
from typing import Any

from research_assistant.adapters.mcp_permissions import (
    append_mcp_audit_event,
    mcp_batch_manifest_dir,
    read_mcp_grant,
    validate_arxiv_batch_grant,
)
from research_assistant.config import get_paths
from research_assistant.individual_release import atomic_write_json
from research_assistant.paths import slugify


PDF_BATCH_POLICY_SCHEMA_VERSION = "pdf-batch-policy-v1"
DEFAULT_MAX_FILES = 25
DEFAULT_MAX_TOTAL_BYTES = 250 * 1024 * 1024
DEFAULT_MAX_PER_FILE_BYTES = 25 * 1024 * 1024
DEFAULT_ALLOWED_DOMAINS = {"arxiv.org", "export.arxiv.org"}
DOWNLOAD_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class PdfBatchPolicy:
    max_files: int = DEFAULT_MAX_FILES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_per_file_bytes: int = DEFAULT_MAX_PER_FILE_BYTES
    allowed_domains: set[str] | None = None
    destination: str = "inbox"
    overwrite_policy: str = "no_overwrite"

    def allowed_domain_set(self) -> set[str]:
        return set(self.allowed_domains or DEFAULT_ALLOWED_DOMAINS)


def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def pdf_batch_policy_status(policy: PdfBatchPolicy | None = None) -> dict[str, Any]:
    policy = policy or PdfBatchPolicy()
    return {
        "schema_version": PDF_BATCH_POLICY_SCHEMA_VERSION,
        "status": "grant_bound_cli_execution_available",
        "execution_enabled": True,
        "mcp_exposed": False,
        "destination": policy.destination,
        "overwrite_policy": policy.overwrite_policy,
        "max_files": policy.max_files,
        "max_total_bytes": policy.max_total_bytes,
        "max_per_file_bytes": policy.max_per_file_bytes,
        "allowed_domains": sorted(policy.allowed_domain_set()),
        "limitations": [
            "PDF batch execution is CLI-only and requires a matching local grant.",
            "PDF batch execution is not exposed through MCP.",
            "Downloaded PDFs must remain inbox review material until later ingest/review.",
        ],
    }


def validate_pdf_batch_policy(candidates: list[dict[str, Any]], *, policy: PdfBatchPolicy | None = None) -> dict[str, Any]:
    policy = policy or PdfBatchPolicy()
    issues: list[dict[str, Any]] = []
    if policy.destination != "inbox":
        issues.append({"code": "pdf_destination_not_inbox", "destination": policy.destination})
    if policy.overwrite_policy != "no_overwrite":
        issues.append({"code": "pdf_overwrite_not_allowed", "overwrite_policy": policy.overwrite_policy})
    if policy.max_files <= 0:
        issues.append({"code": "pdf_invalid_max_files", "max_files": policy.max_files})
    if policy.max_total_bytes <= 0:
        issues.append({"code": "pdf_invalid_max_total_bytes", "max_total_bytes": policy.max_total_bytes})
    if policy.max_per_file_bytes <= 0:
        issues.append({"code": "pdf_invalid_max_per_file_bytes", "max_per_file_bytes": policy.max_per_file_bytes})
    if len(candidates) > policy.max_files:
        issues.append({"code": "pdf_max_files_exceeded", "count": len(candidates), "max_files": policy.max_files})

    total_declared = 0
    allowed_domains = policy.allowed_domain_set()
    for index, candidate in enumerate(candidates):
        url = str(candidate.get("pdf_url") or "")
        if not url:
            issues.append({"code": "pdf_candidate_missing_url", "index": index})
            continue
        domain = _domain_from_url(url)
        if domain not in allowed_domains:
            issues.append({"code": "pdf_domain_not_allowed", "index": index, "domain": domain, "allowed_domains": sorted(allowed_domains)})
        declared_bytes = candidate.get("declared_bytes")
        if declared_bytes is not None:
            try:
                byte_count = int(declared_bytes)
            except (TypeError, ValueError):
                issues.append({"code": "pdf_declared_bytes_invalid", "index": index, "declared_bytes": declared_bytes})
                continue
            if byte_count < 0:
                issues.append({"code": "pdf_declared_bytes_invalid", "index": index, "declared_bytes": declared_bytes})
                continue
            total_declared += byte_count
            if byte_count > policy.max_per_file_bytes:
                issues.append({"code": "pdf_per_file_bytes_exceeded", "index": index, "declared_bytes": byte_count, "max_per_file_bytes": policy.max_per_file_bytes})
    if total_declared > policy.max_total_bytes:
        issues.append({"code": "pdf_total_bytes_exceeded", "declared_bytes": total_declared, "max_total_bytes": policy.max_total_bytes})

    return {
        **pdf_batch_policy_status(policy),
        "status": "blocked" if issues else "ok",
        "candidate_count": len(candidates),
        "declared_total_bytes": total_declared,
        "issues": issues,
    }


def _candidate_arxiv_id(candidate: dict[str, Any]) -> str:
    value = candidate.get("arxiv_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    url = str(candidate.get("pdf_url") or "")
    return url.rstrip("/").rsplit("/", 1)[-1] or "paper"


def _target_name(candidate: dict[str, Any]) -> str:
    arxiv_id = _candidate_arxiv_id(candidate)
    title = str(candidate.get("title") or arxiv_id)
    stem = slugify(f"{arxiv_id}-{title}")[:120]
    return f"{stem}.pdf"


def _download_pdf_with_limits(
    *,
    pdf_url: str,
    target: Path,
    max_bytes: int,
    timeout_seconds: int,
    allowed_domains: set[str],
) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.name}.part")
    if partial.exists():
        partial.unlink()
    sha256 = hashlib.sha256()
    bytes_written = 0
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(pdf_url, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            final_host = _domain_from_url(final_url)
            if final_host not in allowed_domains:
                raise ValueError(f"redirect domain {final_host} is not allowed")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared = int(content_length)
                except ValueError:
                    declared = None
                if declared is not None and declared > max_bytes:
                    raise ValueError(f"content length {declared} exceeds limit {max_bytes}")
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise ValueError(f"stream exceeded limit {max_bytes}")
                    sha256.update(chunk)
                    handle.write(chunk)
        partial.replace(target)
        return {
            "status": "downloaded",
            "path": str(target),
            "bytes": bytes_written,
            "sha256": sha256.hexdigest(),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "final_url": final_url,
            "final_domain": final_host,
        }
    except Exception as exc:
        if partial.exists():
            partial.unlink()
        return {
            "status": "failed",
            "reason": str(exc),
            "bytes": bytes_written,
            "partial_cleaned": not partial.exists(),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def run_pdf_batch_download(
    *,
    grant_id: str,
    plan_hash: str,
    candidates: list[dict[str, Any]],
    candidate_file: Path | None = None,
    root: Path | None = None,
    policy: PdfBatchPolicy | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    paths = get_paths(root)
    policy = policy or PdfBatchPolicy()
    validation = validate_pdf_batch_policy(candidates, policy=policy)
    if validation["status"] != "ok":
        append_mcp_audit_event("pdf_batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": validation["issues"], "plan_hash": plan_hash})
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": validation["issues"]}

    arxiv_ids = [_candidate_arxiv_id(candidate) for candidate in candidates]
    from research_assistant.ingest.arxiv_batch import plan_arxiv_batch_intake

    grant = read_mcp_grant(grant_id, root=paths.root)
    recomputed_plan = plan_arxiv_batch_intake(
        arxiv_ids=arxiv_ids,
        candidate_file=candidate_file,
        max_papers=int(grant.get("max_papers", len(arxiv_ids))),
        destination="inbox",
        operation="pdf_inbox_download",
        root=paths.root,
    )
    if recomputed_plan.get("plan_hash") != plan_hash:
        issue = {"code": "recomputed_plan_hash_mismatch", "expected": plan_hash, "actual": recomputed_plan.get("plan_hash")}
        append_mcp_audit_event("pdf_batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": [issue]})
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": [issue]}
    grant_validation = validate_arxiv_batch_grant(
        grant,
        plan_hash=plan_hash,
        operation="pdf_inbox_download",
        destination="inbox",
        root=paths.root,
        arxiv_ids=arxiv_ids,
    )
    if grant_validation["status"] != "ok":
        append_mcp_audit_event("pdf_batch_blocked", grant_id=grant_id, root=paths.root, detail={"issues": grant_validation["issues"], "plan_hash": plan_hash})
        return {"status": "blocked", "grant_id": grant_id, "plan_hash": plan_hash, "issues": grant_validation["issues"]}

    inbox = paths.local_research / "inbox"
    append_mcp_audit_event("pdf_batch_started", grant_id=grant_id, root=paths.root, detail={"plan_hash": plan_hash, "candidate_count": len(candidates)})
    results: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    total_bytes = 0
    for index, candidate in enumerate(candidates):
        target = inbox / _target_name(candidate)
        row_base = {
            "index": index,
            "arxiv_id": _candidate_arxiv_id(candidate),
            "pdf_url": candidate.get("pdf_url"),
            "target_path": str(target),
        }
        if target.exists():
            row = {**row_base, "status": "skipped_duplicate", "reason": "target_exists"}
            skipped.append(row)
            results.append(row)
            append_mcp_audit_event("pdf_batch_item_skipped", grant_id=grant_id, root=paths.root, detail=row)
            continue
        downloaded = _download_pdf_with_limits(
            pdf_url=str(candidate.get("pdf_url")),
            target=target,
            max_bytes=policy.max_per_file_bytes,
            timeout_seconds=timeout_seconds,
            allowed_domains=policy.allowed_domain_set(),
        )
        row = {**row_base, **downloaded}
        if row["status"] == "downloaded":
            total_bytes += int(row["bytes"])
            if total_bytes > policy.max_total_bytes:
                target.unlink(missing_ok=True)
                row = {**row, "status": "failed", "reason": "total_bytes_exceeded_after_download", "removed_after_total_limit": True}
                failures.append(row)
                append_mcp_audit_event("pdf_batch_item_failed", grant_id=grant_id, root=paths.root, detail=row)
            else:
                results.append(row)
                append_mcp_audit_event("pdf_batch_item_completed", grant_id=grant_id, root=paths.root, detail={key: row[key] for key in row if key != "target_path"})
                continue
        else:
            failures.append(row)
            append_mcp_audit_event("pdf_batch_item_failed", grant_id=grant_id, root=paths.root, detail=row)
        results.append(row)

    manifest = {
        "schema_version": "pdf-batch-manifest-v1",
        "status": "completed_with_failures" if failures else "completed",
        "grant_id": grant_id,
        "plan_hash": plan_hash,
        "workspace_root": str(paths.root.resolve()),
        "operation": "pdf_inbox_download",
        "destination": "inbox",
        "attempted_count": len(results),
        "downloaded_count": len([row for row in results if row.get("status") == "downloaded"]),
        "skipped_duplicates": skipped,
        "failures": failures,
        "results": results,
        "review_policy": "review_material_only",
        "limitations": [
            "PDF batch intake writes only to inbox.",
            "Downloaded PDFs remain review material and are not approved records.",
        ],
    }
    manifest_path = Path(grant.get("manifest_path") or (mcp_batch_manifest_dir(paths.root) / f"{grant_id}.pdf-manifest.json"))
    atomic_write_json(manifest_path, manifest)
    append_mcp_audit_event("pdf_batch_completed", grant_id=grant_id, root=paths.root, detail={
        "manifest_path": str(manifest_path),
        "attempted_count": manifest["attempted_count"],
        "downloaded_count": manifest["downloaded_count"],
        "failure_count": len(failures),
    })
    return {
        "status": manifest["status"],
        "grant_id": grant_id,
        "plan_hash": plan_hash,
        "attempted_count": manifest["attempted_count"],
        "downloaded_count": manifest["downloaded_count"],
        "skipped_duplicates": skipped,
        "failures": failures,
        "manifest_path": str(manifest_path),
        "audit_path": grant.get("audit_path"),
        "review_policy": "review_material_only",
    }
