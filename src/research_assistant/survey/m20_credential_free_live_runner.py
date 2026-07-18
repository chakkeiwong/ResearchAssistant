from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from research_assistant.survey.m20_credential_free_worker import (
    ARXIV_SEED,
    MAX_FORWARD_BODY_BYTES,
    MAX_SOURCE_PACKAGE_BYTES,
    OPENALEX_SEED,
    M20CredentialFreeError,
    build_credential_free_evidence,
    extract_backward_reference_candidates,
    parse_openalex_forward_candidates,
)


SCHEMA_VERSION = "ra-literature-survey-m20-credential-free-live-v1"
SOURCE_URL = f"https://arxiv.org/e-print/{ARXIV_SEED}"
OPENALEX_URL = (
    "https://api.openalex.org/works?"
    f"filter=cites%3A{OPENALEX_SEED}&per_page=10"
)
SOURCE_HOSTS = frozenset({"arxiv.org", "export.arxiv.org"})
OPENALEX_HOSTS = frozenset({"api.openalex.org"})
SOURCE_CONTENT_TYPES = frozenset({
    "application/gzip",
    "application/octet-stream",
    "application/x-eprint-tar",
    "application/x-gzip",
    "application/x-tar",
})
OPENALEX_CONTENT_TYPES = frozenset({"application/json"})
TIMEOUT_SECONDS = 60
CHUNK_BYTES = 64 * 1024
IDENTITY_PATH = Path(
    "docs/validation/literature_survey_m19_live_metadata_2026-07-14/"
    "public_metadata/identity_resolution.json"
)
CROSSWALK_PATH = Path("docs/validation/phase6_public_arxiv/public_pilot_metadata.json")
PLAN_PATH = Path(
    "docs/plans/"
    "literature_survey_north_star_m20_credential_free_repaired_attempt_plan_2026-07-18.md"
)
RAW_BODY_PREFIX = Path("accepted_bodies")


class M20CredentialFreeLiveError(RuntimeError):
    def __init__(self, code: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def _atomic_json(path: Path, value: Any) -> None:
    if not path.parent.is_dir():
        raise M20CredentialFreeLiveError("artifact_parent_missing")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_pretty(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M20CredentialFreeLiveError(code) from exc
    if not isinstance(value, dict):
        raise M20CredentialFreeLiveError(code)
    return value


def _git(repository_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise M20CredentialFreeLiveError("git_provenance_unavailable") from exc
    return completed.stdout.strip()


def _preflight(repository_root: Path, output_root: Path) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        raise M20CredentialFreeLiveError("cpu_only_environment_required")
    if output_root.exists() or not output_root.parent.is_dir():
        raise M20CredentialFreeLiveError("output_root_not_fresh")

    identity_path = (repository_root / IDENTITY_PATH).resolve(strict=True)
    crosswalk_path = (repository_root / CROSSWALK_PATH).resolve(strict=True)
    plan_path = (repository_root / PLAN_PATH).resolve(strict=True)
    expected_runner_path = (
        repository_root / "src/research_assistant/survey/m20_credential_free_live_runner.py"
    ).resolve(strict=True)
    expected_worker_path = (
        repository_root / "src/research_assistant/survey/m20_credential_free_worker.py"
    ).resolve(strict=True)
    if Path(__file__).resolve(strict=True) != expected_runner_path:
        raise M20CredentialFreeLiveError("runtime_runner_source_mismatch")
    identity = _load_object(identity_path, "identity_evidence_invalid")
    crosswalk = _load_object(crosswalk_path, "crosswalk_evidence_invalid")

    resolutions = identity.get("seed_resolutions")
    exact_identity = (
        identity.get("status") == "resolved"
        and identity.get("seed_gate_passed") is True
        and identity.get("normalized_seed_keys") == [f"arxiv:{ARXIV_SEED}"]
        and isinstance(resolutions, list)
        and len(resolutions) == 1
        and resolutions[0].get("disposition") == "resolved_exact_identifier"
        and resolutions[0].get("selected_identifier") == f"arxiv:{ARXIV_SEED}"
    )
    seed = crosswalk.get("seed")
    exact_crosswalk = (
        isinstance(seed, dict)
        and seed.get("arxiv_id") == ARXIV_SEED
        and seed.get("title") == "Neural Optimal Transport"
        and seed.get("openalex_id") == f"https://openalex.org/{OPENALEX_SEED}"
    )
    if not exact_identity:
        raise M20CredentialFreeLiveError("identity_seed_mismatch")
    if not exact_crosswalk:
        raise M20CredentialFreeLiveError("crosswalk_seed_mismatch")

    return {
        "repository_root": str(repository_root),
        "plan_path": str(plan_path),
        "plan_sha256": _sha(plan_path.read_bytes()),
        "identity_path": str(identity_path),
        "identity_sha256": _sha(identity_path.read_bytes()),
        "crosswalk_path": str(crosswalk_path),
        "crosswalk_sha256": _sha(crosswalk_path.read_bytes()),
        "runner_path": str(expected_runner_path),
        "runner_sha256": _sha(expected_runner_path.read_bytes()),
        "worker_path": str(expected_worker_path),
        "worker_sha256": _sha(expected_worker_path.read_bytes()),
        "git_commit": _git(repository_root, "rev-parse", "HEAD"),
        "git_tree": _git(repository_root, "rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(_git(repository_root, "status", "--porcelain")),
        "cpu_only": True,
        "cuda_visible_devices": "-1",
        "python_executable": sys.executable,
        "python_version": sys.version,
    }


def _validate_request(request: urllib.request.Request, *, route: str) -> None:
    split = urlsplit(request.full_url)
    expected_url = SOURCE_URL if route == "arxiv_source" else OPENALEX_URL
    expected_host = "arxiv.org" if route == "arxiv_source" else "api.openalex.org"
    if (
        request.full_url != expected_url
        or request.get_method() != "GET"
        or split.scheme != "https"
        or split.hostname != expected_host
        or split.username is not None
        or split.password is not None
        or split.port is not None
        or split.fragment
    ):
        raise M20CredentialFreeLiveError("request_contract_invalid")
    if route == "openalex_forward":
        query = parse_qs(split.query, keep_blank_values=True)
        if query != {"filter": [f"cites:{OPENALEX_SEED}"], "per_page": ["10"]}:
            raise M20CredentialFreeLiveError("request_contract_invalid")
    _validate_request_headers(request)


def _validate_request_headers(request: urllib.request.Request) -> None:
    headers = {key.casefold(): value for key, value in request.header_items()}
    if set(headers) != {"accept", "user-agent"}:
        raise M20CredentialFreeLiveError("request_headers_invalid")
    forbidden = {"authorization", "cookie", "proxy-authorization", "x-api-key"}
    if forbidden.intersection(headers):
        raise M20CredentialFreeLiveError("credential_header_forbidden")


def _request(route: str) -> urllib.request.Request:
    url = SOURCE_URL if route == "arxiv_source" else OPENALEX_URL
    accept = "application/gzip, application/x-tar, application/octet-stream" if route == "arxiv_source" else "application/json"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "research-assistant-m20-credential-free/1.0",
        },
        method="GET",
    )
    _validate_request(request, route=route)
    return request


def _response_value(response: Any, name: str, default: Any = None) -> Any:
    value = getattr(response, name, default)
    return value() if callable(value) else value


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


def _validate_final_url(route: str, final_url: str) -> None:
    split = urlsplit(final_url) if isinstance(final_url, str) else None
    allowed_hosts = SOURCE_HOSTS if route == "arxiv_source" else OPENALEX_HOSTS
    if (
        split is None
        or split.scheme != "https"
        or split.hostname not in allowed_hosts
        or split.username is not None
        or split.password is not None
        or split.port is not None
        or split.fragment
    ):
        raise M20CredentialFreeLiveError(
            "response_redirect_forbidden",
            details={"final_url": _url_observation(final_url)},
        )
    if route == "arxiv_source":
        return
    if split.path != "/works" or parse_qs(split.query, keep_blank_values=True) != {
        "filter": [f"cites:{OPENALEX_SEED}"],
        "per_page": ["10"],
    }:
        raise M20CredentialFreeLiveError(
            "response_redirect_forbidden",
            details={"final_url": _url_observation(final_url)},
        )


def _validate_content_type(route: str, content_type: str | None) -> None:
    if not isinstance(content_type, str):
        raise M20CredentialFreeLiveError("response_content_type_invalid")
    media_type = content_type.split(";", 1)[0].strip().casefold()
    allowed = SOURCE_CONTENT_TYPES if route == "arxiv_source" else OPENALEX_CONTENT_TYPES
    if media_type not in allowed:
        raise M20CredentialFreeLiveError("response_content_type_invalid")


def _validate_url_observation(
    route: str, observation: Any, *, matches_request: Any
) -> None:
    if (
        not isinstance(observation, dict)
        or observation.get("url_shape") != "parsed"
        or observation.get("scheme") != "https"
        or observation.get("userinfo_present") is not False
        or observation.get("port_present") is not False
        or observation.get("fragment_present") is not False
        or type(observation.get("query_present")) is not bool
        or type(matches_request) is not bool
    ):
        raise M20CredentialFreeLiveError("recorded_final_url_invalid")
    allowed_hosts = SOURCE_HOSTS if route == "arxiv_source" else OPENALEX_HOSTS
    if observation.get("hostname") not in allowed_hosts:
        raise M20CredentialFreeLiveError("recorded_final_url_invalid")
    if route == "openalex_forward" and (
        matches_request is not True
        or observation.get("path") != "/works"
        or observation.get("query_present") is not True
    ):
        raise M20CredentialFreeLiveError("recorded_final_url_invalid")


class _BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, route: str) -> None:
        self.route = route
        self.redirect_count = 0

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        self.redirect_count += 1
        if self.redirect_count > 1:
            raise M20CredentialFreeLiveError("redirect_limit_exceeded")
        _validate_final_url(self.route, new_url)
        redirected = super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )
        if redirected is None:
            return None
        if redirected.get_method() != "GET":
            raise M20CredentialFreeLiveError("request_contract_invalid")
        _validate_request_headers(redirected)
        return redirected


def _read_response(response: Any, *, route: str, max_bytes: int) -> tuple[bytes, str, int, str | None]:
    final_url = _response_value(response, "geturl")
    status = _response_value(response, "status", _response_value(response, "getcode"))
    headers = getattr(response, "headers", {})
    _validate_final_url(route, final_url)
    if status != 200:
        raise M20CredentialFreeLiveError("response_status_invalid")
    declared_raw = headers.get("Content-Length") if hasattr(headers, "get") else None
    if declared_raw is not None:
        try:
            declared = int(declared_raw)
        except (TypeError, ValueError) as exc:
            raise M20CredentialFreeLiveError("response_content_length_invalid") from exc
        if declared < 0 or declared > max_bytes:
            raise M20CredentialFreeLiveError("response_cap_exceeded")
    chunks = []
    total = 0
    while True:
        chunk = response.read(CHUNK_BYTES)
        if not isinstance(chunk, bytes):
            raise M20CredentialFreeLiveError("response_body_invalid")
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise M20CredentialFreeLiveError("response_cap_exceeded")
        chunks.append(chunk)
    body = b"".join(chunks)
    if not body:
        raise M20CredentialFreeLiveError("response_body_invalid")
    content_type = headers.get("Content-Type") if hasattr(headers, "get") else None
    _validate_content_type(route, content_type)
    return body, final_url, status, content_type


def _validate_transport_result(
    *,
    route: str,
    body: bytes,
    final_url: str,
    status: int,
    content_type: str | None,
    max_bytes: int,
) -> None:
    _validate_final_url(route, final_url)
    if status != 200:
        raise M20CredentialFreeLiveError("response_status_invalid")
    if not isinstance(body, bytes) or not body or len(body) > max_bytes:
        raise M20CredentialFreeLiveError("transport_result_invalid")
    _validate_content_type(route, content_type)


def _real_transport(request: urllib.request.Request, *, route: str, max_bytes: int) -> tuple[bytes, str, int, str | None]:
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _BoundedRedirectHandler(route),
        )
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            return _read_response(response, route=route, max_bytes=max_bytes)
    except M20CredentialFreeLiveError:
        raise
    except urllib.error.HTTPError as exc:
        raise M20CredentialFreeLiveError("response_status_invalid") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise M20CredentialFreeLiveError("transport_failed") from exc


def _write_body(root: Path, name: str, body: bytes) -> dict[str, Any]:
    body_dir = root / RAW_BODY_PREFIX
    body_dir.mkdir(mode=0o700, exist_ok=True)
    path = body_dir / name
    if path.exists():
        raise M20CredentialFreeLiveError("accepted_body_exists")
    path.write_bytes(body)
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "size_bytes": len(body),
        "sha256": _sha(body),
    }


def replay_live_evidence(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    ledger = _load_object(root / "route_ledger.json", "route_ledger_invalid")
    rows = ledger.get("routes")
    if (
        ledger.get("request_limit") != 2
        or ledger.get("requests_dispatched") != 2
        or ledger.get("retry_count") != 0
        or ledger.get("credential_interface") is not False
        or not isinstance(rows, list)
        or len(rows) != 2
    ):
        raise M20CredentialFreeLiveError("route_ledger_invalid")
    by_route = {row.get("route"): row for row in rows if isinstance(row, dict)}
    if set(by_route) != {"arxiv_source", "openalex_forward"}:
        raise M20CredentialFreeLiveError("route_ledger_invalid")
    bodies: dict[str, bytes] = {}
    for route, expected_name in (("arxiv_source", "arxiv-source.body"), ("openalex_forward", "openalex-forward.json")):
        row = by_route[route]
        artifact = row.get("accepted_body")
        expected_url = SOURCE_URL if route == "arxiv_source" else OPENALEX_URL
        if (
            row.get("status") != "accepted"
            or row.get("request_url") != expected_url
            or row.get("request_method") != "GET"
            or row.get("request_headers") != ["accept", "user-agent"]
            or row.get("error_code") is not None
            or row.get("error_details") != {}
            or not isinstance(artifact, dict)
        ):
            raise M20CredentialFreeLiveError("route_ledger_invalid")
        relative = artifact.get("relative_path")
        expected_relative = (RAW_BODY_PREFIX / expected_name).as_posix()
        if relative != expected_relative:
            raise M20CredentialFreeLiveError("accepted_body_path_invalid")
        path = (root / relative).resolve(strict=True)
        if path.parent != (root / RAW_BODY_PREFIX).resolve(strict=True):
            raise M20CredentialFreeLiveError("accepted_body_path_invalid")
        raw = path.read_bytes()
        if len(raw) != artifact.get("size_bytes") or _sha(raw) != artifact.get("sha256"):
            raise M20CredentialFreeLiveError("accepted_body_tampered")
        _validate_url_observation(
            route,
            row.get("final_url_observation"),
            matches_request=row.get("final_url_matches_request"),
        )
        if row.get("http_status") != 200:
            raise M20CredentialFreeLiveError("response_status_invalid")
        max_bytes = MAX_SOURCE_PACKAGE_BYTES if route == "arxiv_source" else MAX_FORWARD_BODY_BYTES
        if not raw or len(raw) > max_bytes:
            raise M20CredentialFreeLiveError("transport_result_invalid")
        _validate_content_type(route, row.get("content_type"))
        bodies[route] = raw
    try:
        evidence = build_credential_free_evidence(
            bodies["arxiv_source"], bodies["openalex_forward"]
        )
    except M20CredentialFreeError as exc:
        raise M20CredentialFreeLiveError(f"replay_{exc.code}") from exc
    evidence_bytes = _pretty(evidence)
    evidence_path = root / "combined_evidence.json"
    if not evidence_path.is_file() or evidence_path.read_bytes() != evidence_bytes:
        raise M20CredentialFreeLiveError("combined_evidence_mismatch")
    return {
        "schema_version": f"{SCHEMA_VERSION}-replay",
        "status": "passed",
        "source_package_sha256": evidence["backward"]["source_package_sha256"],
        "forward_body_sha256": evidence["forward"]["body_sha256"],
        "combined_evidence_sha256": _sha(evidence_bytes),
        "backward_candidate_count": evidence["backward"]["candidate_count"],
        "forward_candidate_count": evidence["forward"]["candidate_count"],
        "cost_usd": evidence["forward"]["cost_usd"],
    }


def _scholarly_ledgers(evidence: dict[str, Any], *, access_date: str) -> dict[str, Any]:
    backward = evidence["backward"]["candidates"]
    forward = evidence["forward"]["candidates"]
    source_support = {
        "schema_version": f"{SCHEMA_VERSION}-source-support",
        "seed": f"arxiv:{ARXIV_SEED}",
        "local_full_text_status": "source_package_retained_not_technically_inspected",
        "publication_status": "arxiv_v3_and_retained_metadata_reports_ICLR_2023",
        "retraction_quarantine_status": "not_checked",
        "inspected_technical_anchors": [],
        "allowed_claims": ["public source package was safely parsed for identifier candidates"],
        "forbidden_claims": ["technical claim support", "paper correctness", "literature completeness"],
    }
    citation_metadata = {
        "schema_version": f"{SCHEMA_VERSION}-citation-metadata",
        "source": "OpenAlex anonymous works cites filter",
        "access_date": access_date,
        "seed": f"openalex:{OPENALEX_SEED}",
        "reported_total": evidence["forward"]["reported_total"],
        "reported_cost_usd": evidence["forward"]["cost_usd"],
        "rows": [{
            "candidate_id": row["candidate_id"],
            "title": row["title"],
            "year": row["year"],
            "citation_count": row["citation_count"],
            "venue": "not_available",
            "caveat": "dated descriptive metadata; not truth or relevance evidence",
        } for row in forward],
    }
    backward_ledger = {
        "schema_version": f"{SCHEMA_VERSION}-backward-snowball",
        "seed": f"arxiv:{ARXIV_SEED}",
        "status": "identifier_candidates_pending_primary_source_review",
        "rows": [{**row, "classification": "not_checked", "action": "inspect_primary_source"} for row in backward],
        "limitation": "identifier-only extraction does not establish complete or relevant references",
    }
    forward_ledger = {
        "schema_version": f"{SCHEMA_VERSION}-forward-snowball",
        "seed": f"openalex:{OPENALEX_SEED}",
        "query_source": "OpenAlex",
        "query_date": access_date,
        "status": "citing_candidates_pending_primary_source_review",
        "rows": [{**row, "classification": "not_checked", "action": "inspect_primary_source"} for row in forward],
        "limitation": "first page only; metadata edges do not establish technical relevance",
    }
    claim_support = {
        "schema_version": f"{SCHEMA_VERSION}-claim-support",
        "rows": [{
            "claim": "The retained source and forward metadata yield bounded candidate identifiers for the exact seed.",
            "support_class": "implementation_evidence",
            "artifact": "combined_evidence.json",
        }],
        "source_gap_blockers": ["no technical section, equation, theorem, algorithm, appendix, or experiment was inspected"],
    }
    omitted = {
        "schema_version": f"{SCHEMA_VERSION}-omitted-paper-risks",
        "risks": [{
            "risk": "identifier-free backward references are omitted",
            "reason": "bounded parser admits only canonical DOI/arXiv identifiers",
            "reviewer_risk": "high",
            "next_action": "inspect seed related-work and bibliography text before completeness claims",
        }, {
            "risk": "OpenAlex citing works beyond the first ten are omitted if reported_total exceeds ten",
            "reason": "authorized route is one page only",
            "reviewer_risk": "high" if evidence["forward"]["reported_total"] > 10 else "moderate",
            "next_action": "record only; another page requires a later plan and authority",
        }, {
            "risk": "retraction, erratum, version conflict, and technical relevance are unchecked for all candidates",
            "reason": "this run performs discovery, not primary-source review",
            "reviewer_risk": "high",
            "next_action": "quarantine candidates from claim support until checked",
        }],
    }
    return {
        "source_support.json": source_support,
        "citation_venue_metadata.json": citation_metadata,
        "backward_snowball.json": backward_ledger,
        "forward_snowball.json": forward_ledger,
        "claim_support.json": claim_support,
        "omitted_paper_risks.json": omitted,
    }


def _inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(row for row in root.rglob("*") if row.is_file()):
        raw = path.read_bytes()
        rows.append({
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": len(raw),
            "sha256": _sha(raw),
        })
    return {"schema_version": f"{SCHEMA_VERSION}-inventory", "files": rows}


def _assert_raw_containment(root: Path, source_body: bytes) -> None:
    source_digest = _sha(source_body)
    for path in (row for row in root.rglob("*") if row.is_file()):
        relative = path.relative_to(root)
        if relative.parts[:1] == RAW_BODY_PREFIX.parts:
            continue
        if _sha(path.read_bytes()) == source_digest:
            raise M20CredentialFreeLiveError("raw_source_leaked")


def run_live_successor(
    *,
    repository_root: Path,
    output_root: Path,
    transport: Callable[..., tuple[bytes, str, int, str | None]] = _real_transport,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    output_root = output_root.resolve(strict=False)
    preflight = _preflight(repository_root, output_root)
    output_root.mkdir(mode=0o700)
    started = now()
    started_clock = time.monotonic()
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-manifest",
        "status": "running",
        "started_at_utc": started,
        "preflight": preflight,
        "command": "python -m research_assistant.survey.m20_credential_free_live_runner --repository-root <repo> --output-root <fresh-root>",
        "command_argv": [
            sys.executable,
            "-m",
            "research_assistant.survey.m20_credential_free_live_runner",
            "--repository-root",
            str(repository_root),
            "--output-root",
            str(output_root),
        ],
        "environment": "project interpreter; deliberate CPU-only run",
        "data_version": f"arxiv:{ARXIV_SEED};openalex:{OPENALEX_SEED};access:{started[:10]}",
        "random_seeds": "N/A (deterministic fetch and parse)",
        "hardware": "CPU-only; GPU devices intentionally hidden",
        "attempt_limit": 1,
        "request_limit": 2,
        "retry_policy": "none",
        "source_body_cap_bytes": MAX_SOURCE_PACKAGE_BYTES,
        "forward_body_cap_bytes": MAX_FORWARD_BODY_BYTES,
        "cost_cap_usd": "0.0001",
    }
    _atomic_json(output_root / "run_manifest.json", manifest)
    routes = []
    dispatched = 0
    source_body: bytes | None = None
    terminal_error: str | None = None
    evidence: dict[str, Any] | None = None
    replay: dict[str, Any] | None = None
    terminal_error_details: dict[str, Any] = {}

    route_specs = (
        ("arxiv_source", "arxiv-source.body", MAX_SOURCE_PACKAGE_BYTES),
        ("openalex_forward", "openalex-forward.json", MAX_FORWARD_BODY_BYTES),
    )
    for route, name, cap in route_specs:
        request = _request(route)
        route_started = now()
        row = {
            "route": route,
            "request_url": request.full_url,
            "request_method": request.get_method(),
            "request_headers": sorted(key.casefold() for key, _ in request.header_items()),
            "started_at_utc": route_started,
            "status": "dispatching",
            "accepted_body": None,
            "error_code": None,
            "error_details": {},
        }
        routes.append(row)
        dispatched += 1
        try:
            body, final_url, status, content_type = transport(
                request, route=route, max_bytes=cap
            )
            _validate_transport_result(
                route=route,
                body=body,
                final_url=final_url,
                status=status,
                content_type=content_type,
                max_bytes=cap,
            )
            artifact = _write_body(output_root, name, body)
            row.update({
                "status": "accepted",
                "final_url_observation": _url_observation(final_url),
                "final_url_matches_request": final_url == request.full_url,
                "http_status": status,
                "content_type": content_type,
                "accepted_body": artifact,
                "completed_at_utc": now(),
            })
            if route == "arxiv_source":
                source_body = body
                backward = extract_backward_reference_candidates(body)
                if backward["candidate_count"] == 0:
                    raise M20CredentialFreeError("backward_candidates_empty")
            else:
                forward = parse_openalex_forward_candidates(body)
                if forward["candidate_count"] == 0:
                    raise M20CredentialFreeError("forward_candidates_empty")
        except Exception as exc:
            terminal_error = exc.code if isinstance(exc, (M20CredentialFreeLiveError, M20CredentialFreeError)) else "unexpected_execution_error"
            terminal_error_details = exc.details if isinstance(exc, M20CredentialFreeLiveError) else {}
            row.update({
                "status": "failed",
                "error_code": terminal_error,
                "error_details": terminal_error_details,
                "completed_at_utc": now(),
            })
            break

    ledger = {
        "schema_version": f"{SCHEMA_VERSION}-route-ledger",
        "request_limit": 2,
        "requests_dispatched": dispatched,
        "retry_count": 0,
        "credential_interface": False,
        "routes": routes,
    }
    _atomic_json(output_root / "route_ledger.json", ledger)

    if terminal_error is None:
        try:
            source_path = output_root / RAW_BODY_PREFIX / "arxiv-source.body"
            forward_path = output_root / RAW_BODY_PREFIX / "openalex-forward.json"
            evidence = build_credential_free_evidence(source_path.read_bytes(), forward_path.read_bytes())
            _atomic_json(output_root / "combined_evidence.json", evidence)
            for name, value in _scholarly_ledgers(evidence, access_date=started[:10]).items():
                _atomic_json(output_root / name, value)
            if source_body is None:
                raise M20CredentialFreeLiveError("source_body_missing")
            _assert_raw_containment(output_root, source_body)
            replay = replay_live_evidence(output_root)
            _atomic_json(output_root / "offline_replay.json", replay)
        except Exception as exc:
            terminal_error = exc.code if isinstance(exc, (M20CredentialFreeLiveError, M20CredentialFreeError)) else "unexpected_evidence_error"

    classification = "CAPABILITY_PASSED" if terminal_error is None else "TERMINAL_FAILURE_NO_RETRY"
    result = {
        "schema_version": f"{SCHEMA_VERSION}-result",
        "classification": classification,
        "primary_criterion_passed": terminal_error is None,
        "continuation_veto": terminal_error is not None,
        "continuation_veto_reason": terminal_error,
        "continuation_veto_details": terminal_error_details if terminal_error is not None else {},
        "requests_dispatched": dispatched,
        "retry_count": 0,
        "reported_cost_usd": evidence["forward"]["cost_usd"] if evidence is not None else None,
        "cost_status": "reconciled" if evidence is not None else "not_established",
        "privacy_status": "credential_free_no_auth_or_cookie_headers",
        "offline_replay_status": replay["status"] if replay is not None else "not_passed",
        "backward_candidate_count": evidence["backward"]["candidate_count"] if evidence is not None else None,
        "forward_candidate_count": evidence["forward"]["candidate_count"] if evidence is not None else None,
        "started_at_utc": started,
        "completed_at_utc": now(),
        "wall_time_seconds": round(time.monotonic() - started_clock, 6),
        "decision": "bounded credential-free candidate discovery passed" if terminal_error is None else "bounded attempt closed without retry",
        "main_uncertainty": "identifier-only backward recall and first-page forward coverage",
        "next_justified_action": "terminal artifact review and candidate primary-source triage" if terminal_error is None else "inspect the recorded local failure; any new external attempt needs new authority",
        "nonclaims": [
            "literature_completeness",
            "citation_completeness",
            "technical_claim_support",
            "candidate_relevance",
            "scientific_superiority",
            "m20_or_m21_completion",
            "north_star_mission_completion",
            "release_readiness",
        ],
    }
    manifest["status"] = "closed"
    manifest["completed_at_utc"] = result["completed_at_utc"]
    manifest["wall_time_seconds"] = result["wall_time_seconds"]
    _atomic_json(output_root / "run_manifest.json", manifest)
    _atomic_json(output_root / "terminal_result.json", result)
    _atomic_json(output_root / "artifact_inventory.json", _inventory(output_root))
    return result


def _default_output_root(repository_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return repository_root / "docs/validation" / f"literature_survey_m20_credential_free_live_2026-07-18_{stamp}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the one-attempt credential-free M20 successor")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    repository_root = args.repository_root.resolve(strict=True)
    output_root = args.output_root or _default_output_root(repository_root)
    try:
        result = run_live_successor(repository_root=repository_root, output_root=output_root)
    except M20CredentialFreeLiveError as exc:
        print(json.dumps({"status": "preflight_failed", "error_code": exc.code}, sort_keys=True))
        return 2
    print(json.dumps({"output_root": str(output_root), **result}, sort_keys=True))
    return 0 if result["primary_criterion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
