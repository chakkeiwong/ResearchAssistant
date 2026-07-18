from __future__ import annotations

import gzip
import hashlib
import io
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from research_assistant.survey.discovery_quality import normalize_arxiv_id, normalize_doi


ARXIV_SEED = "2201.12220v3"
MAX_SOURCE_PACKAGE_BYTES = 500_000_000
MAX_ARCHIVE_MEMBERS = 4_096
MAX_ARCHIVE_EXPANDED_BYTES = 1_000_000_000
MAX_RELEVANT_MEMBER_BYTES = 50_000_000
MAX_TOTAL_RELEVANT_BYTES = 200_000_000
MAX_REFERENCE_CANDIDATES = 5_000
SOURCE_EXTENSIONS = frozenset({".bib", ".bbl", ".tex"})
DOI_RE = re.compile(r"(?i)\b10\.\d{4,9}/[-._;()/:A-Z0-9]+")
ARXIV_RE = re.compile(
    r"(?i)(?:arxiv\s*[:=]?\s*|https?://arxiv\.org/(?:abs|pdf)/)"
    r"([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)"
)


class M20ArxivBackwardError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise M20ArxivBackwardError("source_member_path_invalid")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise M20ArxivBackwardError("source_member_path_invalid")
    return path.as_posix()


SourcePackage = bytes | Path


def _package_size(package: SourcePackage) -> int:
    if isinstance(package, bytes):
        return len(package)
    if not isinstance(package, Path) or package.is_symlink() or not package.is_file():
        raise M20ArxivBackwardError("source_package_invalid")
    return package.stat().st_size


def _package_sha(package: SourcePackage) -> str:
    if isinstance(package, bytes):
        return _sha(package)
    digest = hashlib.sha256()
    with package.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _package_prefix(package: SourcePackage, length: int) -> bytes:
    if isinstance(package, bytes):
        return package[:length]
    with package.open("rb") as handle:
        return handle.read(length)


def _read_plain_source(package: SourcePackage, *, limit: int) -> bytes:
    if isinstance(package, bytes):
        return package[: limit + 1]
    with package.open("rb") as handle:
        return handle.read(limit + 1)


def _read_gzip_text(package: SourcePackage, *, max_relevant_member_bytes: int) -> tuple[dict[str, bytes], dict[str, int]]:
    try:
        handle = (
            gzip.GzipFile(fileobj=io.BytesIO(package))
            if isinstance(package, bytes)
            else gzip.GzipFile(filename=str(package))
        )
        with handle:
            raw = handle.read(max_relevant_member_bytes + 1)
    except (OSError, EOFError) as exc:
        raise M20ArxivBackwardError("source_package_invalid") from exc
    if len(raw) > max_relevant_member_bytes:
        raise M20ArxivBackwardError("source_relevant_member_cap_exceeded")
    return {"source.tex": raw}, {
        "archive_member_count": 1,
        "declared_expanded_bytes": len(raw),
        "relevant_member_count": 1,
        "relevant_bytes": len(raw),
    }


def _read_source_members(
    package: SourcePackage,
    *,
    max_package_bytes: int,
    max_archive_members: int,
    max_expanded_bytes: int,
    max_relevant_member_bytes: int,
    max_total_relevant_bytes: int,
) -> tuple[dict[str, bytes], dict[str, int]]:
    package_size = _package_size(package)
    if package_size <= 0 or package_size > max_package_bytes:
        raise M20ArxivBackwardError("source_package_invalid")
    try:
        archive = (
            tarfile.open(fileobj=io.BytesIO(package), mode="r:*")
            if isinstance(package, bytes)
            else tarfile.open(name=package, mode="r:*")
        )
    except tarfile.ReadError:
        if _package_prefix(package, 2) == b"\x1f\x8b":
            return _read_gzip_text(
                package, max_relevant_member_bytes=max_relevant_member_bytes
            )
        if package_size > max_relevant_member_bytes:
            raise M20ArxivBackwardError("source_relevant_member_cap_exceeded")
        raw = _read_plain_source(package, limit=max_relevant_member_bytes)
        return {"source.tex": raw}, {
            "archive_member_count": 1,
            "declared_expanded_bytes": package_size,
            "relevant_member_count": 1,
            "relevant_bytes": package_size,
        }

    members: dict[str, bytes] = {}
    total_expanded = 0
    relevant_bytes = 0
    with archive:
        rows = archive.getmembers()
        if len(rows) > max_archive_members:
            raise M20ArxivBackwardError("source_member_count_exceeded")
        for member in rows:
            name = _safe_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise M20ArxivBackwardError("source_member_type_forbidden")
            if member.size < 0:
                raise M20ArxivBackwardError("source_member_size_invalid")
            total_expanded += member.size
            if total_expanded > max_expanded_bytes:
                raise M20ArxivBackwardError("source_package_expansion_cap_exceeded")
            if PurePosixPath(name).suffix.casefold() not in SOURCE_EXTENSIONS:
                continue
            if member.size > max_relevant_member_bytes:
                raise M20ArxivBackwardError("source_relevant_member_cap_exceeded")
            relevant_bytes += member.size
            if relevant_bytes > max_total_relevant_bytes:
                raise M20ArxivBackwardError("source_relevant_total_cap_exceeded")
            handle = archive.extractfile(member)
            if handle is None:
                raise M20ArxivBackwardError("source_member_unreadable")
            raw = handle.read(max_relevant_member_bytes + 1)
            if len(raw) != member.size or len(raw) > max_relevant_member_bytes:
                raise M20ArxivBackwardError("source_member_size_mismatch")
            if name in members:
                raise M20ArxivBackwardError("source_member_duplicate")
            members[name] = raw
    if not members:
        raise M20ArxivBackwardError("source_text_members_missing")
    return members, {
        "archive_member_count": len(rows),
        "declared_expanded_bytes": total_expanded,
        "relevant_member_count": len(members),
        "relevant_bytes": relevant_bytes,
    }


def _clean_identifier(value: str) -> str:
    return value.rstrip(".,;:)]}\\")


def _title(entry: str) -> str | None:
    match = re.search(r"(?is)\btitle\s*=\s*[\{\"]([^}\"]+)", entry)
    if match is None:
        return None
    value = " ".join(match.group(1).replace("\n", " ").split())
    return value[:500] or None


def _candidate_units(text: str) -> list[tuple[str | None, str]]:
    markers = list(re.finditer(r"(?im)^\s*@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", text))
    chunks: list[tuple[str | None, str]] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        chunks.append((marker.group(2), text[marker.start():end]))
    chunks.extend(
        (match.group(1).strip(), match.group(2))
        for match in re.finditer(
            r"(?is)\\bibitem(?:\[[^]]*\])?\{([^}]+)\}(.*?)(?=\\bibitem|$)",
            text,
        )
    )
    return chunks


def _candidate_row(entry: str, *, key: str | None, member: str) -> dict[str, Any] | None:
    dois = set()
    for value in DOI_RE.findall(entry):
        try:
            normalized = normalize_doi(_clean_identifier(value))
        except Exception:
            continue
        if normalized is not None:
            dois.add(normalized)
    arxiv_ids = set()
    for value in ARXIV_RE.findall(entry):
        try:
            normalized = normalize_arxiv_id(value)
        except Exception:
            continue
        if normalized is not None:
            arxiv_ids.add(normalized)
    identifiers = [
        *(f"doi:{value}" for value in sorted(dois)),
        *(f"arxiv:{value}" for value in sorted(arxiv_ids)),
    ]
    if not identifiers:
        return None
    return {
        "candidate_id": identifiers[0],
        "identifiers": identifiers,
        "bibliography_key": key,
        "title": _title(entry),
        "source_member": member,
    }


def extract_backward_reference_candidates(
    package: SourcePackage,
    *,
    max_package_bytes: int = MAX_SOURCE_PACKAGE_BYTES,
    max_archive_members: int = MAX_ARCHIVE_MEMBERS,
    max_expanded_bytes: int = MAX_ARCHIVE_EXPANDED_BYTES,
    max_relevant_member_bytes: int = MAX_RELEVANT_MEMBER_BYTES,
    max_total_relevant_bytes: int = MAX_TOTAL_RELEVANT_BYTES,
    max_candidates: int = MAX_REFERENCE_CANDIDATES,
) -> dict[str, Any]:
    package_size = _package_size(package)
    members, archive_diagnostics = _read_source_members(
        package,
        max_package_bytes=max_package_bytes,
        max_archive_members=max_archive_members,
        max_expanded_bytes=max_expanded_bytes,
        max_relevant_member_bytes=max_relevant_member_bytes,
        max_total_relevant_bytes=max_total_relevant_bytes,
    )
    candidates: dict[str, dict[str, Any]] = {}
    inventory = []
    bibliography_units_seen = 0
    identifier_bearing_units = 0
    for name, raw in sorted(members.items()):
        inventory.append({"path": name, "size_bytes": len(raw), "sha256": _sha(raw)})
        text = raw.decode("utf-8", errors="replace")
        for key, unit in _candidate_units(text):
            bibliography_units_seen += 1
            row = _candidate_row(unit, key=key, member=name)
            if row is None:
                continue
            identifier_bearing_units += 1
            candidates.setdefault(row["candidate_id"], row)
            if len(candidates) > max_candidates:
                raise M20ArxivBackwardError("backward_candidate_cap_exceeded")
    return {
        "schema_version": "ra-literature-survey-m20-arxiv-backward-v1",
        "source_package_sha256": _package_sha(package),
        "source_package_bytes": package_size,
        "source_member_inventory": inventory,
        "archive_diagnostics": archive_diagnostics,
        "bibliography_units_seen": bibliography_units_seen,
        "identifier_bearing_units": identifier_bearing_units,
        "identifier_free_units": bibliography_units_seen - identifier_bearing_units,
        "candidate_count": len(candidates),
        "candidates": [candidates[key] for key in sorted(candidates)],
    }


def build_arxiv_backward_evidence(package: SourcePackage) -> dict[str, Any]:
    backward = extract_backward_reference_candidates(package)
    if backward["candidate_count"] == 0:
        raise M20ArxivBackwardError("backward_candidates_empty")
    return {
        "schema_version": "ra-literature-survey-m20-arxiv-only-evidence-v1",
        "status": "passed",
        "arxiv_seed": f"arxiv:{ARXIV_SEED}",
        "backward": backward,
        "forward_coverage": {
            "status": "unavailable_out_of_scope",
            "blocking": False,
            "candidate_count": None,
            "reason": "forward-citation services are unavailable and outside the active mission scope",
        },
        "nonclaims": [
            "literature_completeness",
            "citation_completeness",
            "technical_claim_support",
            "candidate_relevance",
            "scientific_correctness",
        ],
    }


__all__ = [
    "M20ArxivBackwardError",
    "build_arxiv_backward_evidence",
    "extract_backward_reference_candidates",
]
