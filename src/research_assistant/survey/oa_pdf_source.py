"""Bounded extraction of an OpenAlex-provided open-access PDF."""

from __future__ import annotations

import hashlib
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from research_assistant.ingest.parser_command import ParserExecutionPolicy
from research_assistant.ingest.parser_frontmatter import extract_frontmatter
from research_assistant.ingest.pdf_extract import PdfExtractionError, extract_pdf_text
from research_assistant.ingest.metadata_resolve import title_similarity


MAX_SECTION_BYTES = 100_000
DOWNLOAD_CHUNK_BYTES = 64 * 1024
ALLOWED_SCHEMES = {"https"}


def fetch_open_access_pdf(
    url: str,
    *,
    root: Path,
    paper_id: str,
    expected_title: str,
    max_bytes: int,
    timeout_seconds: int = 30,
    opener: Any = urllib.request.urlopen,
    parser_policy: ParserExecutionPolicy | None = None,
) -> dict[str, Any]:
    """Download and extract a caller-supplied OA PDF without broad crawling."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        return _blocked("oa_pdf_url_forbidden", "OA PDF URL must be an HTTPS URL")
    if type(max_bytes) is not int or max_bytes <= 0:
        return _blocked("oa_pdf_budget_invalid", "OA PDF byte budget is invalid")
    safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "_", paper_id).strip("._") or "paper"
    source_dir = root / "oa_pdf_sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    target = source_dir / f"{safe_id}.pdf"
    if target.exists() or target.is_symlink():
        return _blocked("oa_pdf_output_exists", "OA PDF source output already exists")
    partial = target.with_name(f".{target.name}.part")
    digest = hashlib.sha256()
    written = 0
    try:
        with opener(url, timeout=timeout_seconds) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            final = urllib.parse.urlparse(final_url)
            if final.scheme not in ALLOWED_SCHEMES or not final.netloc:
                return _blocked("oa_pdf_redirect_forbidden", "OA PDF redirect is not HTTPS")
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        return _blocked("oa_pdf_byte_budget_exceeded", "OA PDF exceeds its byte budget")
                    digest.update(chunk)
                    handle.write(chunk)
        partial.replace(target)
        try:
            text = extract_pdf_text(target, policy=parser_policy)
        except PdfExtractionError as exc:
            target.unlink(missing_ok=True)
            return _blocked("oa_pdf_parse_failed", str(exc), diagnostics=exc.diagnostics)
        frontmatter = extract_frontmatter(
            [line.strip() for line in text.splitlines() if line.strip()]
        )
        title_candidates = frontmatter.title_candidates[:8]
        title_score = max(
            (title_similarity(expected_title, candidate) for candidate in title_candidates),
            default=0.0,
        )
        if not title_candidates or title_score < 0.55:
            target.unlink(missing_ok=True)
            return _blocked(
                "oa_pdf_identity_mismatch",
                "extracted PDF title does not match the nominated paper",
                diagnostics={
                    "expected_title": expected_title,
                    "title_candidates": title_candidates,
                    "title_similarity": title_score,
                },
            )
        sections = _sections(text, paper_id)
        return {
            "status": "available",
            "source_type": "oa_pdf_pdftotext",
            "source_url": final_url,
            "local_path": str(target),
            "sha256": digest.hexdigest(),
            "bytes": written,
            "sections": sections,
            "bibliography": [],
            "parser": "pdftotext",
            "title_candidates": title_candidates,
            "title_similarity": title_score,
        }
    except Exception as exc:
        return _blocked("oa_pdf_fetch_failed", str(exc))
    finally:
        partial.unlink(missing_ok=True)


def _sections(text: str, paper_id: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines()]
    heading = re.compile(
        r"^(?:(?:\d+(?:\.\d+)*|[IVX]+)[.)]?\s+)?"
        r"(abstract|introduction|background|method(?:s|ology)?|model|algorithm|"
        r"theory|experiment(?:s)?|evaluation|results?|discussion|conclusion|appendix)\s*$",
        re.IGNORECASE,
    )
    chunks: list[tuple[str, list[str]]] = []
    current_title = "Extracted PDF text"
    current: list[str] = []
    for line in lines:
        if not line:
            continue
        match = heading.match(line)
        if match:
            if current:
                chunks.append((current_title, current))
            current_title = " ".join(line.split())
            current = []
        else:
            current.append(line)
    if current:
        chunks.append((current_title, current))
    result = []
    for index, (title, body) in enumerate(chunks):
        normalized = " ".join(body).strip()
        if not normalized:
            continue
        result.append({
            "anchor_id": f"pdf:{paper_id}:section-{index}",
            "title": title,
            "text": _utf8_prefix(normalized, MAX_SECTION_BYTES),
            "evidence_ref": f"oa-pdf:{paper_id}:section-{index}",
        })
    return result[:200]


def _utf8_prefix(value: str, max_bytes: int) -> str:
    """Truncate on a UTF-8 boundary for the observation byte contract."""
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _blocked(code: str, message: str, *, diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "blocked",
        "source_type": "oa_pdf",
        "reason": code,
        "message": message,
        "diagnostics": diagnostics or {},
        "sections": [],
        "bibliography": [],
    }


__all__ = ["fetch_open_access_pdf"]
