"""Bounded arXiv source intake for the five M22 omission-frontier nominees."""

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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.m20_arxiv_backward_worker import (
    M20ArxivBackwardError,
    _read_source_members,
)
from research_assistant.survey.m20_arxiv_only_live_runner import (
    M20ArxivOnlyLiveError,
    _real_download,
    _validate_download_result,
)
from research_assistant.survey.m21_seven_source_campaign import (
    M21SevenSourceError,
    _parse_source,
)
from research_assistant.survey.omission_frontier_triage import (
    NOMINEES,
    validate_inspection_queue,
    validate_provisional_triage,
)


SCHEMA_VERSION = "ra-literature-survey-m22-omission-source-campaign-v1"
CANDIDATE_IDS = tuple(value.removeprefix("arxiv:") for value in NOMINEES)
MAX_SOURCE_BYTES = 50_000_000
MAX_ROOT_BYTES = 300_000_000
DERIVED_RESERVE_BYTES = 10_000_000
MAX_ARCHIVE_MEMBERS = 4_096
MAX_EXPANDED_BYTES = 1_000_000_000
MAX_RELEVANT_MEMBER_BYTES = 50_000_000
MAX_RELEVANT_BYTES = 200_000_000
PLAN_PATH = Path(
    "docs/plans/literature_survey_north_star_m22_omission_frontier_triage_plan_2026-07-19.md"
)
TRIAGE_ROOT = Path(
    "docs/validation/literature_survey_north_star_m22_omission_frontier_triage_2026-07-19"
)
TRIAGE_PATH = TRIAGE_ROOT / "provisional_classification.json"
QUEUE_PATH = TRIAGE_ROOT / "inspection_queue.json"
RUNNER_PATH = Path("src/research_assistant/survey/m22_omission_source_campaign.py")
EXECUTION_PATHS = (
    PLAN_PATH,
    TRIAGE_PATH,
    QUEUE_PATH,
    RUNNER_PATH,
    Path("src/research_assistant/survey/omission_frontier_triage.py"),
    Path("src/research_assistant/survey/bibtex_fields.py"),
    Path("src/research_assistant/survey/m20_arxiv_backward_worker.py"),
    Path("src/research_assistant/survey/m20_arxiv_only_live_runner.py"),
    Path("src/research_assistant/survey/m21_seven_source_campaign.py"),
    Path("src/research_assistant/survey/anchors.py"),
    Path("src/research_assistant/source/latex_bundle.py"),
    Path("src/research_assistant/source/latex_extract.py"),
    Path("src/research_assistant/source/latex_flatten.py"),
)
LEGACY_EXECUTION_PATHS = tuple(
    path for path in EXECUTION_PATHS if path.name != "bibtex_fields.py"
)
UNSAFE_SOURCE_CODES = {
    "source_member_path_invalid",
    "source_member_type_forbidden",
    "source_member_size_invalid",
    "source_member_count_exceeded",
    "source_package_expansion_cap_exceeded",
    "source_relevant_member_cap_exceeded",
    "source_relevant_total_cap_exceeded",
    "source_member_size_mismatch",
    "source_member_duplicate",
}


class M22OmissionSourceError(RuntimeError):
    def __init__(self, code: str, *, campaign_veto: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.campaign_veto = campaign_veto


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def _root_bytes(root: Path, *, excluding: Path | None = None) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and path != excluding
    )


def _atomic_bytes(path: Path, raw: bytes, *, root: Path) -> None:
    if _root_bytes(root, excluding=path) + len(raw) > MAX_ROOT_BYTES:
        raise M22OmissionSourceError("evidence_root_cap_exceeded", campaign_veto=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
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


def _atomic_json(path: Path, value: Any, *, root: Path) -> None:
    _atomic_bytes(path, _pretty(value), root=root)


def _atomic_copy(source: Path, destination: Path, *, root: Path) -> dict[str, Any]:
    raw = source.read_bytes()
    _atomic_bytes(destination, raw, root=root)
    return {
        "relative_path": destination.relative_to(root).as_posix(),
        "size_bytes": len(raw),
        "sha256": _sha(raw),
    }


def _git(repository_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repository_root, check=True,
            capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise M22OmissionSourceError("git_provenance_unavailable", campaign_veto=True) from exc
    return completed.stdout.strip()


def _validate_campaign_inputs(repository_root: Path) -> dict[str, Any]:
    triage_path = (repository_root / TRIAGE_PATH).resolve(strict=True)
    queue_path = (repository_root / QUEUE_PATH).resolve(strict=True)
    try:
        triage = json.loads(triage_path.read_text(encoding="utf-8"))
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        validate_provisional_triage(triage)
        validate_inspection_queue(queue, triage=triage)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as exc:
        raise M22OmissionSourceError("campaign_input_invalid", campaign_veto=True) from exc
    if queue.get("candidate_ids") != list(NOMINEES):
        raise M22OmissionSourceError("campaign_input_invalid", campaign_veto=True)
    return {
        "triage_path": str(triage_path),
        "triage_sha256": _sha_file(triage_path),
        "queue_path": str(queue_path),
        "queue_sha256": _sha_file(queue_path),
    }


def _request(arxiv_id: str) -> urllib.request.Request:
    request = urllib.request.Request(
        f"https://arxiv.org/e-print/{arxiv_id}",
        headers={
            "Accept": "application/gzip, application/x-tar, application/octet-stream",
            "User-Agent": "research-assistant-m22-omission-source/1.0",
        },
        method="GET",
    )
    if request.full_url != f"https://arxiv.org/e-print/{arxiv_id}":
        raise M22OmissionSourceError("request_contract_invalid", campaign_veto=True)
    return request


def _derived_artifacts(body_path: Path, *, arxiv_id: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    members, archive = _read_source_members(
        body_path,
        max_package_bytes=MAX_SOURCE_BYTES,
        max_archive_members=MAX_ARCHIVE_MEMBERS,
        max_expanded_bytes=MAX_EXPANDED_BYTES,
        max_relevant_member_bytes=MAX_RELEVANT_MEMBER_BYTES,
        max_total_relevant_bytes=MAX_RELEVANT_BYTES,
    )
    parsed = _parse_source(body_path, arxiv_id=arxiv_id)
    structured = parsed["structured_source"]
    anchors = parsed["anchor_packet"]
    structured["schema_version"] = f"{SCHEMA_VERSION}-structured-source"
    anchors["schema_version"] = f"{SCHEMA_VERSION}-anchors"
    artifacts = {
        "text_member_inventory.json": {
            "schema_version": f"{SCHEMA_VERSION}-text-members",
            "archive_diagnostics": archive,
            "members": parsed["text_member_inventory"],
        },
        "structured_source.json": structured,
        "anchor_candidates.json": anchors,
    }
    return artifacts, members


def _source_status_rows(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "arxiv_id": row["arxiv_id"],
        "source_status": (
            "AVAILABLE_MACHINE_PARSED"
            if row["status"] == "accepted_and_parsed"
            else "SOURCE_AVAILABLE_TEXT_PARSE_GAP"
            if row["status"] == "closed_source_parse_gap"
            else "SOURCE_GAP"
        ),
        "outcome": row["status"],
        "error_code": row.get("error_code"),
        "source_bytes": row.get("source_bytes"),
        "source_sha256": row.get("source_sha256"),
        "anchor_count": row.get("anchor_count", 0),
        "scholarly_classification": "NOT_CHECKED",
        "support_status": "SOURCE_GAP_BLOCKER",
    } for row in route_rows]


def _inventory(root: Path) -> dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA_VERSION}-inventory",
        "inventory_excludes_itself": True,
        "files": [{
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha_file(path),
        } for path in sorted(row for row in root.rglob("*") if row.is_file())
        if path.name != "artifact_inventory.json"],
    }


def replay_omission_source_campaign(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    manifest = json.loads((root / "run_manifest.json").read_text())
    route = json.loads((root / "route_ledger.json").read_text())
    rows = route.get("rows")
    preserved = manifest.get("preserved_execution_sources")
    allowed_statuses = {
        "accepted_and_parsed", "closed_source_parse_gap", "closed_source_failure",
        "closed_harness_failure", "not_dispatched_campaign_veto",
    }
    if (
        manifest.get("candidate_ids") != list(CANDIDATE_IDS)
        or manifest.get("request_limit") != len(CANDIDATE_IDS)
        or manifest.get("retry_policy") != "none"
        or manifest.get("credential_interface") is not False
        or manifest.get("pdf_fallback") is not False
        or manifest.get("per_source_cap_bytes") != MAX_SOURCE_BYTES
        or manifest.get("evidence_root_cap_bytes") != MAX_ROOT_BYTES
        or not isinstance(preserved, list)
    ):
        raise M22OmissionSourceError("run_manifest_invalid", campaign_veto=True)
    preserved_names = [Path(row.get("relative_path", "")).name for row in preserved]
    current_names = [path.name for path in EXECUTION_PATHS]
    legacy_names = [path.name for path in LEGACY_EXECUTION_PATHS]
    if tuple(preserved_names) not in {tuple(current_names), tuple(legacy_names)}:
        raise M22OmissionSourceError("run_manifest_invalid", campaign_veto=True)
    for artifact in preserved:
        path = (root / artifact["relative_path"]).resolve(strict=True)
        if (
            path.parent != (root / "execution_sources").resolve(strict=True)
            or path.stat().st_size != artifact.get("size_bytes")
            or _sha_file(path) != artifact.get("sha256")
        ):
            raise M22OmissionSourceError("execution_source_tampered", campaign_veto=True)
    by_name = {Path(row["relative_path"]).name: row["sha256"] for row in preserved}
    inputs = manifest.get("campaign_inputs") or {}
    if (
        inputs.get("triage_sha256") != by_name.get(TRIAGE_PATH.name)
        or inputs.get("queue_sha256") != by_name.get(QUEUE_PATH.name)
    ):
        raise M22OmissionSourceError("campaign_input_replay_mismatch", campaign_veto=True)
    if (
        route.get("candidate_ids") != list(CANDIDATE_IDS)
        or route.get("request_limit") != len(CANDIDATE_IDS)
        or route.get("retry_count") != 0
        or not isinstance(rows, list)
        or [row.get("arxiv_id") for row in rows] != list(CANDIDATE_IDS)
        or any(
            row.get("status") not in allowed_statuses
            or row.get("request_url") != f"https://arxiv.org/e-print/{row.get('arxiv_id')}"
            or row.get("requests_dispatched") not in {0, 1}
            or row.get("retry_count") != 0
            for row in rows
        )
        or sum(row.get("requests_dispatched") == 1 for row in rows)
        != route.get("requests_dispatched")
    ):
        raise M22OmissionSourceError("route_ledger_invalid", campaign_veto=True)
    accepted = 0
    parsed_count = 0
    parse_gaps = 0
    for row in rows:
        candidate_root = root / "candidates" / row["arxiv_id"].replace(".", "_")
        body_path = candidate_root / "accepted_source.body"
        if row["status"] in {"accepted_and_parsed", "closed_source_parse_gap"}:
            accepted += 1
            _validate_download_result({
                key: row.get(key) for key in (
                    "size_bytes", "sha256", "http_status", "content_type",
                    "declared_content_length", "final_url_observation",
                    "final_url_matches_request",
                )
            }, body_path=body_path, max_bytes=row["effective_source_cap_bytes"])
            artifacts, members = _derived_artifacts(body_path, arxiv_id=row["arxiv_id"])
            expected_status = (
                "accepted_and_parsed"
                if artifacts["structured_source.json"]["status"] == "available_machine_parsed"
                else "closed_source_parse_gap"
            )
            if row["status"] != expected_status:
                raise M22OmissionSourceError("route_parse_outcome_mismatch", campaign_veto=True)
            for name, value in artifacts.items():
                if (candidate_root / name).read_bytes() != _pretty(value):
                    raise M22OmissionSourceError("derived_replay_mismatch", campaign_veto=True)
            for name, raw in members.items():
                path = (candidate_root / "source_members" / name).resolve(strict=True)
                if (
                    not path.is_file()
                    or path.is_symlink()
                    or not path.is_relative_to((candidate_root / "source_members").resolve())
                    or path.read_bytes() != raw
                ):
                    raise M22OmissionSourceError("source_member_replay_mismatch", campaign_veto=True)
            parsed_count += expected_status == "accepted_and_parsed"
            parse_gaps += expected_status == "closed_source_parse_gap"
        elif body_path.exists():
            raise M22OmissionSourceError("failed_source_body_present", campaign_veto=True)
    if (root / "source_status.json").read_bytes() != _pretty({
        "schema_version": f"{SCHEMA_VERSION}-source-status",
        "rows": _source_status_rows(rows),
    }):
        raise M22OmissionSourceError("source_status_replay_mismatch", campaign_veto=True)
    if (root / "claim_support.json").read_bytes() != _pretty({
        "schema_version": f"{SCHEMA_VERSION}-claim-support",
        "claims": [],
        "status": "no_supported_claims_machine_intake_only",
    }):
        raise M22OmissionSourceError("claim_support_replay_mismatch", campaign_veto=True)
    if _root_bytes(root) > MAX_ROOT_BYTES:
        raise M22OmissionSourceError("evidence_root_cap_exceeded", campaign_veto=True)
    inventory_path = root / "artifact_inventory.json"
    if manifest.get("status") == "closed":
        if inventory_path.read_bytes() != _pretty(_inventory(root)):
            raise M22OmissionSourceError("artifact_inventory_replay_mismatch", campaign_veto=True)
    elif manifest.get("status") != "running":
        raise M22OmissionSourceError("run_manifest_invalid", campaign_veto=True)
    return {
        "schema_version": f"{SCHEMA_VERSION}-replay",
        "status": "passed",
        "candidate_count": len(rows),
        "requests_dispatched": route["requests_dispatched"],
        "accepted_source_package_count": accepted,
        "accepted_and_parsed_count": parsed_count,
        "source_parse_gap_count": parse_gaps,
        "legacy_execution_source_gaps": (
            ["bibtex_fields.py"] if preserved_names == legacy_names else []
        ),
        "root_bytes_before_replay_record": _root_bytes(root),
    }


def run_omission_source_campaign(
    *,
    repository_root: Path,
    output_root: Path,
    downloader: Callable[..., dict[str, Any]] = _real_download,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    output_root = output_root.resolve(strict=False)
    campaign_inputs = _validate_campaign_inputs(repository_root)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        raise M22OmissionSourceError("cpu_only_environment_required", campaign_veto=True)
    if output_root.exists() or not output_root.parent.is_dir():
        raise M22OmissionSourceError("output_root_not_fresh", campaign_veto=True)
    if shutil.disk_usage(output_root.parent).free < MAX_ROOT_BYTES + 30_000_000:
        raise M22OmissionSourceError("insufficient_free_space", campaign_veto=True)
    output_root.mkdir(mode=0o700)
    (output_root / "candidates").mkdir(mode=0o700)
    execution_root = output_root / "execution_sources"
    execution_root.mkdir(mode=0o700)
    preserved = []
    for relative in EXECUTION_PATHS:
        source = (repository_root / relative).resolve(strict=True)
        preserved.append(_atomic_copy(source, execution_root / source.name, root=output_root))
    started = now()
    started_clock = time.monotonic()
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-manifest",
        "status": "running",
        "started_at_utc": started,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "command_argv": [
            sys.executable, "-m", "research_assistant.survey.m22_omission_source_campaign",
            "--repository-root", str(repository_root), "--output-root", str(output_root),
        ],
        "git_commit": _git(repository_root, "rev-parse", "HEAD"),
        "git_tree": _git(repository_root, "rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(_git(repository_root, "status", "--porcelain")),
        "environment": "project interpreter; deliberate CPU-only source intake",
        "hardware": "CPU-only; GPU devices intentionally hidden",
        "data_version": "exact five nominees from replayed 55-row M22 omission frontier",
        "plan_path": str((repository_root / PLAN_PATH).resolve(strict=True)),
        "campaign_inputs": campaign_inputs,
        "random_seeds": "N/A (deterministic source intake and parse)",
        "candidate_ids": list(CANDIDATE_IDS),
        "request_limit": len(CANDIDATE_IDS),
        "retry_policy": "none",
        "credential_interface": False,
        "pdf_fallback": False,
        "per_source_cap_bytes": MAX_SOURCE_BYTES,
        "evidence_root_cap_bytes": MAX_ROOT_BYTES,
        "derived_reserve_bytes": DERIVED_RESERVE_BYTES,
        "preserved_execution_sources": preserved,
    }
    _atomic_json(output_root / "run_manifest.json", manifest, root=output_root)
    route_rows: list[dict[str, Any]] = []
    campaign_veto: str | None = None
    for arxiv_id in CANDIDATE_IDS:
        candidate_root = output_root / "candidates" / arxiv_id.replace(".", "_")
        candidate_root.mkdir(mode=0o700)
        body_path = candidate_root / "accepted_source.body"
        row: dict[str, Any] = {
            "arxiv_id": arxiv_id,
            "request_url": f"https://arxiv.org/e-print/{arxiv_id}",
            "requests_dispatched": 0,
            "retry_count": 0,
            "status": "pending",
            "error_code": None,
        }
        remaining = MAX_ROOT_BYTES - DERIVED_RESERVE_BYTES - _root_bytes(output_root)
        if remaining <= 0:
            campaign_veto = "evidence_root_capacity_unavailable"
            row.update(status="not_dispatched_campaign_veto", error_code=campaign_veto)
            route_rows.append(row)
            break
        try:
            request = _request(arxiv_id)
            row["requests_dispatched"] = 1
            row["effective_source_cap_bytes"] = min(MAX_SOURCE_BYTES, remaining)
            download = downloader(request, destination=body_path, max_bytes=row["effective_source_cap_bytes"])
            _validate_download_result(download, body_path=body_path, max_bytes=row["effective_source_cap_bytes"])
            artifacts, members = _derived_artifacts(body_path, arxiv_id=arxiv_id)
            for name, value in artifacts.items():
                _atomic_json(candidate_root / name, value, root=output_root)
            for name, raw in members.items():
                _atomic_bytes(candidate_root / "source_members" / name, raw, root=output_root)
            parsed_status = artifacts["structured_source.json"]["status"]
            row.update(
                status=(
                    "accepted_and_parsed"
                    if parsed_status == "available_machine_parsed"
                    else "closed_source_parse_gap"
                ),
                size_bytes=body_path.stat().st_size,
                sha256=_sha_file(body_path),
                source_bytes=body_path.stat().st_size,
                source_sha256=_sha_file(body_path),
                http_status=download.get("http_status"),
                content_type=download.get("content_type"),
                declared_content_length=download.get("declared_content_length"),
                final_url_observation=download.get("final_url_observation"),
                final_url_matches_request=download.get("final_url_matches_request"),
                anchor_count=artifacts["anchor_candidates.json"]["anchor_count"],
                error_code=artifacts["structured_source.json"].get("parse_gap_code"),
            )
        except (M20ArxivOnlyLiveError, M20ArxivBackwardError, M21SevenSourceError, M22OmissionSourceError) as exc:
            error_code = getattr(exc, "code", "source_processing_failed")
            shutil.rmtree(candidate_root)
            candidate_root.mkdir(mode=0o700)
            row.update(status="closed_source_failure", error_code=error_code)
            if (
                error_code in UNSAFE_SOURCE_CODES
                or isinstance(exc, M22OmissionSourceError) and exc.campaign_veto
                or isinstance(exc, M21SevenSourceError) and exc.campaign_veto
            ):
                campaign_veto = error_code
        except Exception:
            shutil.rmtree(candidate_root)
            candidate_root.mkdir(mode=0o700)
            row.update(status="closed_harness_failure", error_code="unexpected_harness_error")
            campaign_veto = "unexpected_harness_error"
        route_rows.append(row)
        if campaign_veto is not None:
            break
    for arxiv_id in CANDIDATE_IDS[len(route_rows):]:
        route_rows.append({
            "arxiv_id": arxiv_id,
            "request_url": f"https://arxiv.org/e-print/{arxiv_id}",
            "requests_dispatched": 0,
            "retry_count": 0,
            "status": "not_dispatched_campaign_veto",
            "error_code": campaign_veto,
        })
    route = {
        "schema_version": f"{SCHEMA_VERSION}-route-ledger",
        "candidate_ids": list(CANDIDATE_IDS),
        "request_limit": len(CANDIDATE_IDS),
        "requests_dispatched": sum(row["requests_dispatched"] for row in route_rows),
        "retry_count": 0,
        "credential_interface": False,
        "rows": route_rows,
    }
    _atomic_json(output_root / "route_ledger.json", route, root=output_root)
    _atomic_json(output_root / "source_status.json", {
        "schema_version": f"{SCHEMA_VERSION}-source-status",
        "rows": _source_status_rows(route_rows),
    }, root=output_root)
    _atomic_json(output_root / "claim_support.json", {
        "schema_version": f"{SCHEMA_VERSION}-claim-support",
        "claims": [],
        "status": "no_supported_claims_machine_intake_only",
    }, root=output_root)
    replay = None
    if campaign_veto is None:
        try:
            replay = replay_omission_source_campaign(output_root)
            _atomic_json(output_root / "offline_replay.json", replay, root=output_root)
        except (M22OmissionSourceError, M20ArxivOnlyLiveError) as exc:
            campaign_veto = getattr(exc, "code", "offline_replay_failed")
    passed = campaign_veto is None and len(route_rows) == len(CANDIDATE_IDS)
    result = {
        "schema_version": f"{SCHEMA_VERSION}-result",
        "classification": "M22_OMISSION_SOURCE_INTAKE_PASSED" if passed else "TERMINAL_CAMPAIGN_VETO",
        "primary_criterion_passed": passed,
        "campaign_veto": campaign_veto,
        "requests_dispatched": route["requests_dispatched"],
        "retry_count": 0,
        "accepted_and_parsed_count": sum(row["status"] == "accepted_and_parsed" for row in route_rows),
        "source_parse_gap_count": sum(row["status"] == "closed_source_parse_gap" for row in route_rows),
        "source_failure_count": sum(row["status"] == "closed_source_failure" for row in route_rows),
        "offline_replay_status": replay["status"] if replay else "not_passed",
        "started_at_utc": started,
        "completed_at_utc": now(),
        "wall_time_seconds": round(time.monotonic() - started_clock, 6),
        "root_bytes_before_close": _root_bytes(output_root),
        "nonclaims": [
            "candidate relevance in fact", "technical claim support",
            "mathematical correctness", "publication or retraction safety",
            "importance ranking", "literature completeness",
        ],
    }
    manifest.update(status="closed", completed_at_utc=result["completed_at_utc"])
    _atomic_json(output_root / "run_manifest.json", manifest, root=output_root)
    _atomic_json(output_root / "terminal_result.json", result, root=output_root)
    _atomic_json(output_root / "artifact_inventory.json", _inventory(output_root), root=output_root)
    if _root_bytes(output_root) > MAX_ROOT_BYTES:
        raise M22OmissionSourceError("evidence_root_cap_exceeded_after_close", campaign_veto=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the bounded five-paper M22 omission source intake")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_omission_source_campaign(
            repository_root=args.repository_root, output_root=args.output_root,
        )
    except M22OmissionSourceError as exc:
        print(json.dumps({"status": "failed", "error_code": exc.code}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["primary_criterion_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CANDIDATE_IDS", "MAX_ROOT_BYTES", "MAX_SOURCE_BYTES", "M22OmissionSourceError",
    "replay_omission_source_campaign", "run_omission_source_campaign",
]
