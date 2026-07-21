from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from research_assistant.survey.m20_arxiv_backward_worker import (
    ARXIV_SEED,
    MAX_SOURCE_PACKAGE_BYTES,
    M20ArxivBackwardError,
    build_arxiv_backward_evidence,
)


SCHEMA_VERSION = "ra-literature-survey-m20-arxiv-only-live-v1"
SOURCE_URL = f"https://arxiv.org/e-print/{ARXIV_SEED}"
SOURCE_HOSTS = frozenset({"arxiv.org", "export.arxiv.org"})
SOURCE_CONTENT_TYPES = frozenset({
    "application/gzip",
    "application/octet-stream",
    "application/x-eprint-tar",
    "application/x-gzip",
    "application/x-tar",
})
MAX_EVIDENCE_ROOT_BYTES = 500_000_000
MIN_FREE_SPACE_BYTES = 550_000_000
MIN_DERIVED_EVIDENCE_RESERVE_BYTES = 50_000_000
TIMEOUT_SECONDS = 90
CHUNK_BYTES = 1024 * 1024
PLAN_PATH = Path(
    "docs/plans/literature_survey_north_star_m20_arxiv_only_500mb_attempt_plan_2026-07-18.md"
)
MIGRATION_PATH = Path(
    "docs/plans/literature_survey_north_star_m20_arxiv_only_governance_migration_2026-07-18.md"
)
IDENTITY_PATH = Path(
    "docs/validation/literature_survey_m19_live_metadata_2026-07-14/"
    "public_metadata/identity_resolution.json"
)
BODY_RELATIVE_PATH = Path("accepted_bodies/arxiv-source.body")


class M20ArxivOnlyLiveError(RuntimeError):
    def __init__(self, code: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def _root_bytes(root: Path, *, excluding: Path | None = None) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and (excluding is None or path != excluding):
            total += path.stat().st_size
    return total


def _atomic_json(path: Path, value: Any, *, root: Path) -> None:
    raw = _pretty(value)
    if _root_bytes(root, excluding=path) + len(raw) > MAX_EVIDENCE_ROOT_BYTES:
        raise M20ArxivOnlyLiveError("evidence_root_cap_exceeded")
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_copy(source: Path, destination: Path, *, root: Path) -> dict[str, Any]:
    raw = source.read_bytes()
    if _root_bytes(root, excluding=destination) + len(raw) > MAX_EVIDENCE_ROOT_BYTES:
        raise M20ArxivOnlyLiveError("evidence_root_cap_exceeded")
    descriptor, name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "relative_path": destination.relative_to(root).as_posix(),
        "size_bytes": len(raw),
        "sha256": _sha(raw),
    }


def _load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M20ArxivOnlyLiveError(code) from exc
    if not isinstance(value, dict):
        raise M20ArxivOnlyLiveError(code)
    return value


def _git(repository_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repository_root, check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise M20ArxivOnlyLiveError("git_provenance_unavailable") from exc
    return completed.stdout.strip()


def _preflight(repository_root: Path, output_root: Path) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        raise M20ArxivOnlyLiveError("cpu_only_environment_required")
    if output_root.exists() or not output_root.parent.is_dir():
        raise M20ArxivOnlyLiveError("output_root_not_fresh")
    free = shutil.disk_usage(output_root.parent).free
    if free < MIN_FREE_SPACE_BYTES:
        raise M20ArxivOnlyLiveError(
            "insufficient_free_space",
            details={"free_bytes": free, "required_bytes": MIN_FREE_SPACE_BYTES},
        )
    identity_path = (repository_root / IDENTITY_PATH).resolve(strict=True)
    plan_path = (repository_root / PLAN_PATH).resolve(strict=True)
    migration_path = (repository_root / MIGRATION_PATH).resolve(strict=True)
    runner_path = (
        repository_root / "src/research_assistant/survey/m20_arxiv_only_live_runner.py"
    ).resolve(strict=True)
    worker_path = (
        repository_root / "src/research_assistant/survey/m20_arxiv_backward_worker.py"
    ).resolve(strict=True)
    if Path(__file__).resolve(strict=True) != runner_path:
        raise M20ArxivOnlyLiveError("runtime_runner_source_mismatch")
    identity = _load_object(identity_path, "identity_evidence_invalid")
    resolutions = identity.get("seed_resolutions")
    if not (
        identity.get("status") == "resolved"
        and identity.get("seed_gate_passed") is True
        and identity.get("normalized_seed_keys") == [f"arxiv:{ARXIV_SEED}"]
        and isinstance(resolutions, list)
        and len(resolutions) == 1
        and resolutions[0].get("selected_identifier") == f"arxiv:{ARXIV_SEED}"
    ):
        raise M20ArxivOnlyLiveError("identity_seed_mismatch")
    return {
        "repository_root": str(repository_root),
        "plan_path": str(plan_path),
        "plan_sha256": _sha_file(plan_path),
        "migration_path": str(migration_path),
        "migration_sha256": _sha_file(migration_path),
        "identity_path": str(identity_path),
        "identity_sha256": _sha_file(identity_path),
        "runner_path": str(runner_path),
        "runner_sha256": _sha_file(runner_path),
        "worker_path": str(worker_path),
        "worker_sha256": _sha_file(worker_path),
        "git_commit": _git(repository_root, "rev-parse", "HEAD"),
        "git_tree": _git(repository_root, "rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(_git(repository_root, "status", "--porcelain")),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "cpu_only": True,
        "cuda_visible_devices": "-1",
        "free_space_bytes": free,
    }


def _request() -> urllib.request.Request:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "Accept": "application/gzip, application/x-tar, application/octet-stream",
            "User-Agent": "research-assistant-m20-arxiv-only/1.0",
        },
        method="GET",
    )
    split = urlsplit(request.full_url)
    headers = {key.casefold() for key, _ in request.header_items()}
    if (
        request.get_method() != "GET"
        or split.scheme != "https"
        or split.hostname != "arxiv.org"
        or split.path != f"/e-print/{ARXIV_SEED}"
        or split.query
        or split.fragment
        or headers != {"accept", "user-agent"}
    ):
        raise M20ArxivOnlyLiveError("request_contract_invalid")
    return request


def _url_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {"url_shape": "invalid"}
    split = urlsplit(value)
    return {
        "url_shape": "parsed",
        "scheme": split.scheme,
        "hostname": split.hostname,
        "path": split.path,
        "userinfo_present": split.username is not None or split.password is not None,
        "port_present": split.port is not None,
        "query_present": bool(split.query),
        "fragment_present": bool(split.fragment),
    }


def _validate_final_url(value: str) -> None:
    observation = _url_observation(value)
    if (
        observation.get("scheme") != "https"
        or observation.get("hostname") not in SOURCE_HOSTS
        or observation.get("userinfo_present") is not False
        or observation.get("port_present") is not False
        or observation.get("fragment_present") is not False
    ):
        raise M20ArxivOnlyLiveError(
            "response_redirect_forbidden", details={"final_url": observation}
        )


def _validate_content_type(value: str | None) -> None:
    if not isinstance(value, str):
        raise M20ArxivOnlyLiveError("response_content_type_invalid")
    if value.split(";", 1)[0].strip().casefold() not in SOURCE_CONTENT_TYPES:
        raise M20ArxivOnlyLiveError("response_content_type_invalid")


def _validate_final_url_observation(value: Any, *, matches_request: Any) -> None:
    if (
        not isinstance(value, dict)
        or value.get("url_shape") != "parsed"
        or value.get("scheme") != "https"
        or value.get("hostname") not in SOURCE_HOSTS
        or not isinstance(value.get("path"), str)
        or value.get("userinfo_present") is not False
        or value.get("port_present") is not False
        or type(value.get("query_present")) is not bool
        or value.get("fragment_present") is not False
        or type(matches_request) is not bool
    ):
        raise M20ArxivOnlyLiveError("recorded_final_url_invalid")


def _validate_download_result(
    download: Any,
    *,
    body_path: Path,
    max_bytes: int,
) -> None:
    if not isinstance(download, dict):
        raise M20ArxivOnlyLiveError("download_evidence_invalid")
    size = download.get("size_bytes")
    digest = download.get("sha256")
    declared = download.get("declared_content_length")
    if (
        type(size) is not int
        or not 0 < size <= max_bytes
        or not isinstance(digest, str)
        or len(digest) != 64
        or download.get("http_status") != 200
        or (declared is not None and (type(declared) is not int or declared != size))
        or not body_path.is_file()
        or body_path.is_symlink()
        or body_path.stat().st_size != size
        or _sha_file(body_path) != digest
    ):
        raise M20ArxivOnlyLiveError("download_evidence_invalid")
    _validate_content_type(download.get("content_type"))
    _validate_final_url_observation(
        download.get("final_url_observation"),
        matches_request=download.get("final_url_matches_request"),
    )


class _BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        self.redirect_count = 0

    def redirect_request(self, request: Any, file_pointer: Any, code: int, message: str, headers: Any, new_url: str) -> Any:
        self.redirect_count += 1
        if self.redirect_count > 1:
            raise M20ArxivOnlyLiveError("redirect_limit_exceeded")
        _validate_final_url(new_url)
        redirected = super().redirect_request(request, file_pointer, code, message, headers, new_url)
        if redirected is not None:
            header_names = {key.casefold() for key, _ in redirected.header_items()}
            if redirected.get_method() != "GET" or header_names != {"accept", "user-agent"}:
                raise M20ArxivOnlyLiveError("request_headers_invalid")
        return redirected


def _real_download(request: urllib.request.Request, *, destination: Path, max_bytes: int) -> dict[str, Any]:
    temporary = destination.with_name(f".{destination.name}.part")
    bytes_written = 0
    digest = hashlib.sha256()
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _BoundedRedirectHandler()
        )
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            status = response.getcode()
            _validate_final_url(final_url)
            if status != 200:
                raise M20ArxivOnlyLiveError("response_status_invalid")
            content_type = response.headers.get("Content-Type")
            _validate_content_type(content_type)
            declared_raw = response.headers.get("Content-Length")
            declared = None
            if declared_raw is not None:
                try:
                    declared = int(declared_raw)
                except ValueError as exc:
                    raise M20ArxivOnlyLiveError("response_content_length_invalid") from exc
                if declared < 0 or declared > max_bytes:
                    raise M20ArxivOnlyLiveError(
                        "response_cap_exceeded",
                        details={"mode": "declared_length", "observed_bytes": declared, "cap_bytes": max_bytes},
                    )
            with temporary.open("xb") as handle:
                while chunk := response.read(CHUNK_BYTES):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise M20ArxivOnlyLiveError(
                            "response_cap_exceeded",
                            details={"mode": "streamed", "observed_bytes": bytes_written, "cap_bytes": max_bytes},
                        )
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if bytes_written <= 0:
                raise M20ArxivOnlyLiveError("response_body_invalid")
            temporary.replace(destination)
            return {
                "size_bytes": bytes_written,
                "sha256": digest.hexdigest(),
                "http_status": status,
                "content_type": content_type,
                "declared_content_length": declared,
                "final_url_observation": _url_observation(final_url),
                "final_url_matches_request": final_url == request.full_url,
            }
    except M20ArxivOnlyLiveError:
        raise
    except urllib.error.HTTPError as exc:
        raise M20ArxivOnlyLiveError("response_status_invalid") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise M20ArxivOnlyLiveError("transport_failed") from exc
    finally:
        if temporary.exists():
            temporary.unlink()


def _classified_candidates(evidence: dict[str, Any]) -> dict[str, Any]:
    rows = [{
        **candidate,
        "source_role": "backward_reference_candidate",
        "scholarly_classification": "NOT_CHECKED",
        "support_status": "SOURCE_GAP_BLOCKER",
        "action": "inspect_primary_source",
    } for candidate in evidence["backward"]["candidates"]]
    return {
        "schema_version": f"{SCHEMA_VERSION}-candidate-classifications",
        "status": "complete_preliminary_classification",
        "candidate_count": len(rows),
        "rows": rows,
    }


def _ledgers(evidence: dict[str, Any], classifications: dict[str, Any]) -> dict[str, Any]:
    backward = evidence["backward"]
    return {
        "source_support.json": {
            "schema_version": f"{SCHEMA_VERSION}-source-support",
            "seed": evidence["arxiv_seed"],
            "source_package_sha256": backward["source_package_sha256"],
            "source_package_bytes": backward["source_package_bytes"],
            "full_text_status": "source_package_retained_not_technically_inspected",
            "publication_status": "arxiv_v3; publication/retraction status not checked in this phase",
            "retraction_quarantine_status": "NOT_CHECKED",
            "inspected_technical_anchors": [],
            "allowed_claims": ["bounded public source intake and identifier candidate extraction passed"],
            "forbidden_claims": ["technical support", "candidate relevance", "scientific correctness", "completeness"],
        },
        "citation_venue_metadata.json": {
            "schema_version": f"{SCHEMA_VERSION}-citation-metadata",
            "status": "unavailable_out_of_scope",
            "blocking": False,
            "rows": [],
            "caveat": "citation and venue metadata are unavailable and are not represented as zero",
        },
        "backward_snowball.json": {
            "schema_version": f"{SCHEMA_VERSION}-backward-snowball",
            "seed": evidence["arxiv_seed"],
            "status": "candidate_set_requires_primary_source_triage",
            "rows": classifications["rows"],
            "identifier_free_units": backward["identifier_free_units"],
            "limitation": "identifier-only extraction does not establish relevance or complete references",
        },
        "forward_snowball.json": {
            "schema_version": f"{SCHEMA_VERSION}-forward-snowball",
            "status": "unavailable_out_of_scope",
            "blocking": False,
            "rows": [],
            "limitation": "forward-citation coverage is unavailable and no completeness claim is permitted",
        },
        "claim_support.json": {
            "schema_version": f"{SCHEMA_VERSION}-claim-support",
            "rows": [{
                "claim": "The exact seed source yielded a bounded replayable set of canonical backward-reference candidates.",
                "support_class": "IMPLEMENTATION_EVIDENCE",
                "artifact": "combined_evidence.json",
            }],
            "source_gap_blockers": ["no candidate primary technical source or seed technical anchor was inspected"],
        },
        "omitted_paper_risks.json": {
            "schema_version": f"{SCHEMA_VERSION}-omitted-paper-risks",
            "risks": [{
                "risk": "identifier-free seed references may be omitted",
                "reason": f"{backward['identifier_free_units']} bibliography units had no admitted DOI/arXiv identifier",
                "reviewer_risk": "high",
                "next_action": "inspect seed related-work and full bibliography during M21",
            }, {
                "risk": "forward-citing works are unavailable",
                "reason": "forward-citation services are outside active project scope",
                "reviewer_risk": "high",
                "next_action": "retain as non-blocking scope limitation; do not claim completeness",
            }, {
                "risk": "candidate relevance, retraction, version, and technical support are unchecked",
                "reason": "M20 performs discovery/classification state only",
                "reviewer_risk": "high",
                "next_action": "primary-source triage and safety checks in M21",
            }],
        },
    }


def replay_arxiv_only_evidence(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    ledger = _load_object(root / "route_ledger.json", "route_ledger_invalid")
    rows = ledger.get("routes")
    if (
        ledger.get("request_limit") != 1
        or ledger.get("requests_dispatched") != 1
        or ledger.get("retry_count") != 0
        or ledger.get("credential_interface") is not False
        or not isinstance(rows, list)
        or len(rows) != 1
    ):
        raise M20ArxivOnlyLiveError("route_ledger_invalid")
    row = rows[0]
    artifact = row.get("accepted_body") if isinstance(row, dict) else None
    if (
        row.get("route") != "arxiv_source"
        or row.get("request_url") != SOURCE_URL
        or row.get("request_headers") != ["accept", "user-agent"]
        or row.get("status") != "accepted"
        or row.get("error_code") is not None
        or not isinstance(artifact, dict)
        or artifact.get("relative_path") != BODY_RELATIVE_PATH.as_posix()
    ):
        raise M20ArxivOnlyLiveError("route_ledger_invalid")
    body_path = (root / BODY_RELATIVE_PATH).resolve(strict=True)
    if body_path.parent != (root / BODY_RELATIVE_PATH.parent).resolve(strict=True):
        raise M20ArxivOnlyLiveError("accepted_body_path_invalid")
    if body_path.stat().st_size != artifact.get("size_bytes") or _sha_file(body_path) != artifact.get("sha256"):
        raise M20ArxivOnlyLiveError("accepted_body_tampered")
    _validate_download_result(
        {
            "size_bytes": artifact.get("size_bytes"),
            "sha256": artifact.get("sha256"),
            "http_status": row.get("http_status"),
            "content_type": row.get("content_type"),
            "declared_content_length": row.get("declared_content_length"),
            "final_url_observation": row.get("final_url_observation"),
            "final_url_matches_request": row.get("final_url_matches_request"),
        },
        body_path=body_path,
        max_bytes=MAX_SOURCE_PACKAGE_BYTES,
    )
    evidence = build_arxiv_backward_evidence(body_path)
    if (root / "combined_evidence.json").read_bytes() != _pretty(evidence):
        raise M20ArxivOnlyLiveError("combined_evidence_mismatch")
    classifications = _classified_candidates(evidence)
    if (root / "candidate_classifications.json").read_bytes() != _pretty(classifications):
        raise M20ArxivOnlyLiveError("classification_mismatch")
    for name, value in _ledgers(evidence, classifications).items():
        if (root / name).read_bytes() != _pretty(value):
            raise M20ArxivOnlyLiveError("scholarly_ledger_mismatch")
    if _root_bytes(root) > MAX_EVIDENCE_ROOT_BYTES:
        raise M20ArxivOnlyLiveError("evidence_root_cap_exceeded")
    return {
        "schema_version": f"{SCHEMA_VERSION}-replay",
        "status": "passed",
        "source_package_sha256": evidence["backward"]["source_package_sha256"],
        "source_package_bytes": evidence["backward"]["source_package_bytes"],
        "candidate_count": evidence["backward"]["candidate_count"],
        "forward_coverage_status": evidence["forward_coverage"]["status"],
        "root_bytes_before_replay_record": _root_bytes(root),
    }


def _inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(row for row in root.rglob("*") if row.is_file()):
        rows.append({
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha_file(path),
        })
    return {"schema_version": f"{SCHEMA_VERSION}-inventory", "files": rows}


def run_arxiv_only_attempt(
    *,
    repository_root: Path,
    output_root: Path,
    downloader: Callable[..., dict[str, Any]] = _real_download,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    output_root = output_root.resolve(strict=False)
    preflight = _preflight(repository_root, output_root)
    output_root.mkdir(mode=0o700)
    (output_root / BODY_RELATIVE_PATH.parent).mkdir(mode=0o700)
    execution_sources = output_root / "execution_sources"
    execution_sources.mkdir(mode=0o700)
    preserved_sources = []
    for key in ("plan_path", "migration_path", "runner_path", "worker_path"):
        source = Path(preflight[key])
        copied = _atomic_copy(
            source, execution_sources / source.name, root=output_root
        )
        if copied["sha256"] != preflight[f"{key.removesuffix('_path')}_sha256"]:
            raise M20ArxivOnlyLiveError("execution_source_copy_mismatch")
        preserved_sources.append(copied)
    started_utc = now()
    started_clock = time.monotonic()
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-manifest",
        "status": "running",
        "started_at_utc": started_utc,
        "preflight": preflight,
        "command_argv": [sys.executable, "-m", "research_assistant.survey.m20_arxiv_only_live_runner", "--repository-root", str(repository_root), "--output-root", str(output_root)],
        "environment": "project interpreter; deliberate CPU-only run",
        "data_version": f"arxiv:{ARXIV_SEED};access:{started_utc[:10]}",
        "random_seeds": "N/A (deterministic source intake and parse)",
        "hardware": "CPU-only; GPU devices intentionally hidden",
        "attempt_limit": 1,
        "request_limit": 1,
        "retry_policy": "none",
        "source_body_cap_bytes": MAX_SOURCE_PACKAGE_BYTES,
        "evidence_root_cap_bytes": MAX_EVIDENCE_ROOT_BYTES,
        "forward_coverage_policy": "unavailable_out_of_scope_non_blocking",
        "preserved_execution_sources": preserved_sources,
    }
    _atomic_json(output_root / "run_manifest.json", manifest, root=output_root)
    request = _request()
    route_started = time.monotonic()
    route = {
        "route": "arxiv_source",
        "request_url": request.full_url,
        "request_method": request.get_method(),
        "request_headers": sorted(key.casefold() for key, _ in request.header_items()),
        "started_at_utc": now(),
        "started_monotonic_offset_seconds": round(route_started - started_clock, 6),
        "status": "dispatching",
        "accepted_body": None,
        "error_code": None,
        "error_details": {},
    }
    terminal_error: str | None = None
    terminal_details: dict[str, Any] = {}
    evidence: dict[str, Any] | None = None
    replay: dict[str, Any] | None = None
    try:
        body_path = output_root / BODY_RELATIVE_PATH
        download = downloader(
            request, destination=body_path, max_bytes=MAX_SOURCE_PACKAGE_BYTES
        )
        _validate_download_result(
            download, body_path=body_path, max_bytes=MAX_SOURCE_PACKAGE_BYTES
        )
        projected_minimum = _root_bytes(output_root) + MIN_DERIVED_EVIDENCE_RESERVE_BYTES
        if projected_minimum > MAX_EVIDENCE_ROOT_BYTES:
            body_bytes = body_path.stat().st_size
            body_path.unlink()
            raise M20ArxivOnlyLiveError(
                "evidence_root_cap_exceeded",
                details={
                    "source_body_bytes": body_bytes,
                    "minimum_derived_reserve_bytes": MIN_DERIVED_EVIDENCE_RESERVE_BYTES,
                    "root_cap_bytes": MAX_EVIDENCE_ROOT_BYTES,
                },
            )
        route.update({
            "status": "accepted",
            "http_status": download.get("http_status"),
            "content_type": download.get("content_type"),
            "declared_content_length": download.get("declared_content_length"),
            "final_url_observation": download.get("final_url_observation"),
            "final_url_matches_request": download.get("final_url_matches_request"),
            "accepted_body": {
                "relative_path": BODY_RELATIVE_PATH.as_posix(),
                "size_bytes": body_path.stat().st_size,
                "sha256": _sha_file(body_path),
            },
        })
        evidence = build_arxiv_backward_evidence(body_path)
        classifications = _classified_candidates(evidence)
        _atomic_json(output_root / "combined_evidence.json", evidence, root=output_root)
        _atomic_json(output_root / "candidate_classifications.json", classifications, root=output_root)
        for name, value in _ledgers(evidence, classifications).items():
            _atomic_json(output_root / name, value, root=output_root)
    except Exception as exc:
        terminal_error = exc.code if isinstance(exc, (M20ArxivOnlyLiveError, M20ArxivBackwardError)) else "unexpected_execution_error"
        terminal_details = exc.details if isinstance(exc, M20ArxivOnlyLiveError) else {}
        body_path = output_root / BODY_RELATIVE_PATH
        if body_path.exists():
            body_path.unlink()
        route.update({
            "status": "failed",
            "accepted_body": None,
            "error_code": terminal_error,
            "error_details": terminal_details,
        })
    route["completed_at_utc"] = now()
    route["completed_monotonic_offset_seconds"] = round(time.monotonic() - started_clock, 6)
    ledger = {
        "schema_version": f"{SCHEMA_VERSION}-route-ledger",
        "request_limit": 1,
        "requests_dispatched": 1,
        "retry_count": 0,
        "credential_interface": False,
        "routes": [route],
    }
    _atomic_json(output_root / "route_ledger.json", ledger, root=output_root)
    if terminal_error is None:
        try:
            replay = replay_arxiv_only_evidence(output_root)
            _atomic_json(output_root / "offline_replay.json", replay, root=output_root)
        except Exception as exc:
            terminal_error = exc.code if isinstance(exc, M20ArxivOnlyLiveError) else "unexpected_replay_error"
            terminal_details = exc.details if isinstance(exc, M20ArxivOnlyLiveError) else {}
    passed = terminal_error is None
    result = {
        "schema_version": f"{SCHEMA_VERSION}-result",
        "classification": "M20_ARXIV_ONLY_PASSED" if passed else "TERMINAL_FAILURE_NO_RETRY",
        "m20_revised_contract_passed": passed,
        "primary_criterion_passed": passed,
        "continuation_veto": not passed,
        "continuation_veto_reason": terminal_error,
        "continuation_veto_details": terminal_details,
        "requests_dispatched": 1,
        "retry_count": 0,
        "backward_candidate_count": evidence["backward"]["candidate_count"] if evidence else None,
        "forward_coverage_status": "unavailable_out_of_scope",
        "forward_coverage_blocking": False,
        "offline_replay_status": replay["status"] if replay else "not_passed",
        "root_bytes_before_close_artifacts": _root_bytes(output_root),
        "root_cap_enforced_after_close": True,
        "started_at_utc": started_utc,
        "completed_at_utc": now(),
        "wall_time_seconds": round(time.monotonic() - started_clock, 6),
        "next_justified_action": "close revised M20 and hand source/candidates to M21 planning" if passed else "inspect terminal evidence; no retry or rerun is authorized",
        "nonclaims": ["forward_citation_coverage", "literature_completeness", "candidate_relevance", "technical_claim_support", "scientific_correctness", "m21_or_north_star_completion"],
    }
    manifest.update({
        "status": "closed",
        "completed_at_utc": result["completed_at_utc"],
        "wall_time_seconds": result["wall_time_seconds"],
    })
    _atomic_json(output_root / "run_manifest.json", manifest, root=output_root)
    _atomic_json(output_root / "terminal_result.json", result, root=output_root)
    _atomic_json(output_root / "artifact_inventory.json", _inventory(output_root), root=output_root)
    if _root_bytes(output_root) > MAX_EVIDENCE_ROOT_BYTES:
        raise M20ArxivOnlyLiveError("evidence_root_cap_exceeded_after_close")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the one-attempt arXiv-only M20 backward-discovery campaign")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_arxiv_only_attempt(
            repository_root=args.repository_root, output_root=args.output_root
        )
    except M20ArxivOnlyLiveError as exc:
        print(json.dumps({"status": "preflight_failed", "error_code": exc.code, "details": exc.details}, sort_keys=True))
        return 2
    print(json.dumps({"output_root": str(args.output_root), **result}, sort_keys=True))
    return 0 if result["primary_criterion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
