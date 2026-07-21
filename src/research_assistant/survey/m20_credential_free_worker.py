from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import tarfile
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from typing import Any

from research_assistant.survey.bibtex_fields import read_text_field
from research_assistant.survey.discovery_quality import (
    normalize_arxiv_id,
    normalize_doi,
    normalize_openalex_id,
)


ARXIV_SEED = "2201.12220v3"
OPENALEX_SEED = "W4226072009"
MAX_SOURCE_PACKAGE_BYTES = 20_000_000
MAX_ARCHIVE_MEMBERS = 256
MAX_MEMBER_BYTES = 2_000_000
MAX_FORWARD_BODY_BYTES = 2_000_000
MAX_REFERENCE_CANDIDATES = 100
MAX_FORWARD_CANDIDATES = 10
EXPECTED_FORWARD_COST_USD = Decimal("0.0001")
SOURCE_EXTENSIONS = frozenset({".bib", ".bbl", ".tex"})
DOI_RE = re.compile(r"(?i)\b10\.\d{4,9}/[-._;()/:A-Z0-9]+")
ARXIV_RE = re.compile(
    r"(?i)(?:arxiv\s*[:=]?\s*|https?://arxiv\.org/(?:abs|pdf)/)"
    r"([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)"
)
OPENALEX_URL_RE = re.compile(r"^https://openalex\.org/(W[0-9]+)$")


class M20CredentialFreeError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise M20CredentialFreeError("source_member_path_invalid")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise M20CredentialFreeError("source_member_path_invalid")
    return path.as_posix()


def _read_gzip_text(package: bytes) -> dict[str, bytes]:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(package)) as handle:
            raw = handle.read(MAX_MEMBER_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise M20CredentialFreeError("source_package_invalid") from exc
    if len(raw) > MAX_MEMBER_BYTES:
        raise M20CredentialFreeError("source_member_cap_exceeded")
    return {"source.tex": raw}


def _read_source_members(package: bytes) -> dict[str, bytes]:
    if not isinstance(package, bytes) or not package or len(package) > MAX_SOURCE_PACKAGE_BYTES:
        raise M20CredentialFreeError("source_package_invalid")
    try:
        archive = tarfile.open(fileobj=io.BytesIO(package), mode="r:*")
    except tarfile.ReadError:
        if package.startswith(b"\x1f\x8b"):
            return _read_gzip_text(package)
        if len(package) > MAX_MEMBER_BYTES:
            raise M20CredentialFreeError("source_member_cap_exceeded")
        return {"source.tex": package}

    members: dict[str, bytes] = {}
    total_unpacked = 0
    with archive:
        rows = archive.getmembers()
        if len(rows) > MAX_ARCHIVE_MEMBERS:
            raise M20CredentialFreeError("source_member_count_exceeded")
        for member in rows:
            name = _safe_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise M20CredentialFreeError("source_member_type_forbidden")
            if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                raise M20CredentialFreeError("source_member_cap_exceeded")
            total_unpacked += member.size
            if total_unpacked > MAX_SOURCE_PACKAGE_BYTES:
                raise M20CredentialFreeError("source_package_expansion_cap_exceeded")
            handle = archive.extractfile(member)
            if handle is None:
                raise M20CredentialFreeError("source_member_unreadable")
            raw = handle.read(MAX_MEMBER_BYTES + 1)
            if len(raw) != member.size or len(raw) > MAX_MEMBER_BYTES:
                raise M20CredentialFreeError("source_member_size_mismatch")
            if PurePosixPath(name).suffix.casefold() in SOURCE_EXTENSIONS:
                if name in members:
                    raise M20CredentialFreeError("source_member_duplicate")
                members[name] = raw
    if not members:
        raise M20CredentialFreeError("source_text_members_missing")
    return members


def _clean_identifier(value: str) -> str:
    return value.rstrip(".,;:)]}\\")


def _title(entry: str) -> str | None:
    return read_text_field(entry, "title")


def _candidate_rows(text: str, *, member: str) -> list[dict[str, Any]]:
    markers = list(re.finditer(r"(?im)^\s*@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", text))
    chunks: list[tuple[str | None, str]] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        chunks.append((marker.group(2), text[marker.start():end]))
    for match in re.finditer(r"(?is)\\bibitem(?:\[[^]]*\])?\{([^}]+)\}(.*?)(?=\\bibitem|$)", text):
        chunks.append((match.group(1).strip(), match.group(2)))

    candidates = []
    for key, chunk in chunks:
        dois = set()
        for value in DOI_RE.findall(chunk):
            try:
                normalized = normalize_doi(_clean_identifier(value))
            except Exception:
                continue
            if normalized is not None:
                dois.add(normalized)
        arxiv_ids = set()
        for value in ARXIV_RE.findall(chunk):
            try:
                normalized = normalize_arxiv_id(value)
            except Exception:
                continue
            if normalized is not None:
                arxiv_ids.add(normalized)
        dois = sorted(dois)
        arxiv_ids = sorted(arxiv_ids)
        identifiers = [*(f"doi:{value}" for value in dois), *(f"arxiv:{value}" for value in arxiv_ids)]
        if not identifiers:
            continue
        candidates.append({
            "candidate_id": identifiers[0],
            "identifiers": identifiers,
            "bibliography_key": key,
            "title": _title(chunk),
            "source_member": member,
        })
    return candidates


def extract_backward_reference_candidates(package: bytes) -> dict[str, Any]:
    members = _read_source_members(package)
    candidates: dict[str, dict[str, Any]] = {}
    inventory = []
    for name, raw in sorted(members.items()):
        inventory.append({"path": name, "size_bytes": len(raw), "sha256": _sha(raw)})
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        for row in _candidate_rows(text, member=name):
            candidates.setdefault(row["candidate_id"], row)
            if len(candidates) > MAX_REFERENCE_CANDIDATES:
                raise M20CredentialFreeError("backward_candidate_cap_exceeded")
    return {
        "schema_version": "ra-literature-survey-m20-credential-free-backward-v1",
        "source_package_sha256": _sha(package),
        "source_member_inventory": inventory,
        "candidate_count": len(candidates),
        "candidates": [candidates[key] for key in sorted(candidates)],
    }


def _decode_json(body: bytes) -> Any:
    if not isinstance(body, bytes) or not body or len(body) > MAX_FORWARD_BODY_BYTES:
        raise M20CredentialFreeError("forward_body_invalid")

    def exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise M20CredentialFreeError("forward_json_duplicate_key")
            value[key] = item
        return value

    try:
        return json.loads(body.decode("utf-8"), object_pairs_hook=exact_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M20CredentialFreeError("forward_json_invalid") from exc


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise M20CredentialFreeError("forward_cost_invalid")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise M20CredentialFreeError("forward_cost_invalid") from exc
    if not result.is_finite() or result < 0:
        raise M20CredentialFreeError("forward_cost_invalid")
    return result


def parse_openalex_forward_candidates(body: bytes, *, seed_id: str = OPENALEX_SEED) -> dict[str, Any]:
    expected_seed = normalize_openalex_id(seed_id)
    if expected_seed is None:
        raise M20CredentialFreeError("forward_seed_invalid")
    value = _decode_json(body)
    if not isinstance(value, dict) or not isinstance(value.get("meta"), dict):
        raise M20CredentialFreeError("forward_envelope_invalid")
    meta = value["meta"]
    results = value.get("results")
    if not isinstance(results, list) or len(results) > MAX_FORWARD_CANDIDATES:
        raise M20CredentialFreeError("forward_results_invalid")
    if type(meta.get("count")) is not int or meta["count"] < len(results):
        raise M20CredentialFreeError("forward_count_invalid")
    if (
        type(meta.get("page")) is not int
        or meta["page"] != 1
        or type(meta.get("per_page")) is not int
        or meta["per_page"] != MAX_FORWARD_CANDIDATES
    ):
        raise M20CredentialFreeError("forward_page_invalid")
    cost = _decimal(meta.get("cost_usd"))
    if cost != EXPECTED_FORWARD_COST_USD:
        raise M20CredentialFreeError("forward_cost_contradiction")

    candidates = []
    seen_work_ids = set()
    for row in results:
        if not isinstance(row, dict):
            raise M20CredentialFreeError("forward_work_invalid")
        identifier = row.get("id")
        match = OPENALEX_URL_RE.fullmatch(identifier) if isinstance(identifier, str) else None
        title = row.get("display_name")
        references = row.get("referenced_works")
        if match is None or not isinstance(title, str) or not title.strip() or not isinstance(references, list):
            raise M20CredentialFreeError("forward_work_invalid")
        if match.group(1) in seen_work_ids:
            raise M20CredentialFreeError("forward_work_duplicate")
        seen_work_ids.add(match.group(1))
        normalized_references = []
        for reference in references:
            try:
                normalized = normalize_openalex_id(reference)
            except Exception as exc:
                raise M20CredentialFreeError("forward_reference_invalid") from exc
            if normalized is None:
                raise M20CredentialFreeError("forward_reference_invalid")
            normalized_references.append(normalized)
        if expected_seed not in normalized_references:
            raise M20CredentialFreeError("forward_edge_not_bound_to_seed")
        try:
            doi = normalize_doi(row.get("doi"))
        except Exception as exc:
            raise M20CredentialFreeError("forward_doi_invalid") from exc
        year = row.get("publication_year")
        if year is not None and (type(year) is not int or not 1000 <= year <= 3000):
            raise M20CredentialFreeError("forward_year_invalid")
        citation_count = row.get("cited_by_count")
        if citation_count is not None and (type(citation_count) is not int or citation_count < 0):
            raise M20CredentialFreeError("forward_citation_count_invalid")
        candidates.append({
            "candidate_id": f"openalex:{match.group(1).casefold()}",
            "openalex_id": match.group(1),
            "title": " ".join(title.split()),
            "doi": doi,
            "year": year,
            "citation_count": citation_count,
            "cites_seed_openalex_id": expected_seed,
        })
    return {
        "schema_version": "ra-literature-survey-m20-credential-free-forward-v1",
        "body_sha256": _sha(body),
        "reported_total": meta["count"],
        "cost_usd": format(cost, "f"),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def build_credential_free_evidence(source_package: bytes, forward_body: bytes) -> dict[str, Any]:
    backward = extract_backward_reference_candidates(source_package)
    forward = parse_openalex_forward_candidates(forward_body)
    if backward["candidate_count"] == 0:
        raise M20CredentialFreeError("backward_candidates_empty")
    if forward["candidate_count"] == 0:
        raise M20CredentialFreeError("forward_candidates_empty")
    return {
        "schema_version": "ra-literature-survey-m20-credential-free-evidence-v1",
        "status": "passed",
        "arxiv_seed": f"arxiv:{ARXIV_SEED}",
        "openalex_seed": f"openalex:{OPENALEX_SEED}",
        "backward": backward,
        "forward": forward,
        "nonclaims": [
            "literature_completeness",
            "technical_claim_support",
            "citation_completeness",
            "m20_completion",
        ],
    }


__all__ = [
    "M20CredentialFreeError",
    "build_credential_free_evidence",
    "extract_backward_reference_candidates",
    "parse_openalex_forward_candidates",
]
