from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any


PDF_BATCH_POLICY_SCHEMA_VERSION = "pdf-batch-policy-v1"
DEFAULT_MAX_FILES = 25
DEFAULT_MAX_TOTAL_BYTES = 250 * 1024 * 1024
DEFAULT_MAX_PER_FILE_BYTES = 25 * 1024 * 1024
DEFAULT_ALLOWED_DOMAINS = {"arxiv.org", "export.arxiv.org"}


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
        "status": "policy_checks_available",
        "execution_enabled": False,
        "destination": policy.destination,
        "overwrite_policy": policy.overwrite_policy,
        "max_files": policy.max_files,
        "max_total_bytes": policy.max_total_bytes,
        "max_per_file_bytes": policy.max_per_file_bytes,
        "allowed_domains": sorted(policy.allowed_domain_set()),
        "limitations": [
            "Policy checks do not download PDFs.",
            "PDF batch execution remains disabled.",
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
