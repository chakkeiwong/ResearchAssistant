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

from research_assistant.source.latex_bundle import detect_main_tex
from research_assistant.source.latex_extract import extract_latex_structure
from research_assistant.source.latex_flatten import flatten_latex_bundle
from research_assistant.survey.anchors import _extract_anchor_rows
from research_assistant.survey.m20_arxiv_backward_worker import (
    M20ArxivBackwardError,
    _read_source_members,
)
from research_assistant.survey.m20_arxiv_only_live_runner import (
    M20ArxivOnlyLiveError,
    _real_download,
    _validate_download_result,
)


SCHEMA_VERSION = "ra-literature-survey-m21-seven-source-v1"
CANDIDATE_IDS = (
    "1412.6980",
    "1506.03365",
    "1709.08894",
    "1805.07277",
    "1902.07197",
    "2003.06635",
    "2003.06788",
)
MAX_SOURCE_BYTES = 100_000_000
MAX_ROOT_BYTES = 500_000_000
DERIVED_RESERVE_BYTES = 20_000_000
MAX_ARCHIVE_MEMBERS = 4_096
MAX_EXPANDED_BYTES = 1_000_000_000
MAX_RELEVANT_MEMBER_BYTES = 50_000_000
MAX_RELEVANT_BYTES = 200_000_000
MAX_ANCHORS = 5_000
PLAN_PATH = Path(
    "docs/plans/literature_survey_north_star_m21_seven_candidate_arxiv_source_campaign_2026-07-18.md"
)
RUNNER_PATH = Path("src/research_assistant/survey/m21_seven_source_campaign.py")
ARCHIVE_WORKER_PATH = Path(
    "src/research_assistant/survey/m20_arxiv_backward_worker.py"
)
SELECTION_PATH = Path(
    "docs/validation/literature_survey_north_star_m21_candidate_context_triage_2026-07-18/primary_source_selection.json"
)
TRIAGE_PATH = Path(
    "docs/validation/literature_survey_north_star_m21_candidate_context_triage_2026-07-18/candidate_context_triage.json"
)
EXECUTION_PATHS = (
    PLAN_PATH,
    SELECTION_PATH,
    TRIAGE_PATH,
    RUNNER_PATH,
    ARCHIVE_WORKER_PATH,
    Path("src/research_assistant/survey/m20_arxiv_only_live_runner.py"),
    Path("src/research_assistant/survey/anchors.py"),
    Path("src/research_assistant/source/latex_bundle.py"),
    Path("src/research_assistant/source/latex_extract.py"),
    Path("src/research_assistant/source/latex_flatten.py"),
)


class M21SevenSourceError(RuntimeError):
    def __init__(self, code: str, *, campaign_veto: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.campaign_veto = campaign_veto


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def _root_bytes(root: Path, *, excluding: Path | None = None) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and path != excluding
    )


def _atomic_json(path: Path, value: Any, *, root: Path) -> None:
    raw = _pretty(value)
    if _root_bytes(root, excluding=path) + len(raw) > MAX_ROOT_BYTES:
        raise M21SevenSourceError("evidence_root_cap_exceeded", campaign_veto=True)
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


def _atomic_copy(source: Path, destination: Path, *, root: Path) -> dict[str, Any]:
    raw = source.read_bytes()
    if _root_bytes(root, excluding=destination) + len(raw) > MAX_ROOT_BYTES:
        raise M21SevenSourceError("evidence_root_cap_exceeded", campaign_veto=True)
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
        raise M21SevenSourceError("git_provenance_unavailable", campaign_veto=True) from exc
    return completed.stdout.strip()


def _validate_campaign_inputs(repository_root: Path) -> dict[str, Any]:
    selection_path = (repository_root / SELECTION_PATH).resolve(strict=True)
    triage_path = (repository_root / TRIAGE_PATH).resolve(strict=True)
    try:
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        triage = json.loads(triage_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M21SevenSourceError("campaign_input_invalid", campaign_veto=True) from exc
    expected_ids = [f"arxiv:{value}" for value in CANDIDATE_IDS]
    if (
        not isinstance(selection, dict)
        or not isinstance(triage, dict)
        or selection.get("nominated_candidate_ids") != expected_ids
        or selection.get("nomination_count") != len(CANDIDATE_IDS)
        or triage.get("candidate_count") != 62
        or sum((triage.get("state_counts") or {}).values()) != 62
        or (triage.get("state_counts") or {}).get(
            "BIBLIOGRAPHY_ENTRY_NOT_LOCATED_IN_SEED_TEXT"
        )
        != 55
    ):
        raise M21SevenSourceError("campaign_input_invalid", campaign_veto=True)
    return {
        "selection_path": str(selection_path),
        "selection_sha256": _sha_file(selection_path),
        "triage_path": str(triage_path),
        "triage_sha256": _sha_file(triage_path),
    }


def _request(arxiv_id: str) -> urllib.request.Request:
    request = urllib.request.Request(
        f"https://arxiv.org/e-print/{arxiv_id}",
        headers={
            "Accept": "application/gzip, application/x-tar, application/octet-stream",
            "User-Agent": "research-assistant-m21-seven-source/1.0",
        },
        method="GET",
    )
    if request.full_url != f"https://arxiv.org/e-print/{arxiv_id}":
        raise M21SevenSourceError("request_contract_invalid", campaign_veto=True)
    return request


def _sanitized_block(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    raw = str(row.get("raw_latex") or "").encode("utf-8")
    return {
        **{field: row.get(field) for field in fields},
        "raw_latex_sha256": _sha(raw),
        "raw_latex_bytes": len(raw),
        "raw_latex_included": False,
    }


def _parse_source(body_path: Path, *, arxiv_id: str) -> dict[str, Any]:
    try:
        members, archive = _read_source_members(
            body_path,
            max_package_bytes=MAX_SOURCE_BYTES,
            max_archive_members=MAX_ARCHIVE_MEMBERS,
            max_expanded_bytes=MAX_EXPANDED_BYTES,
            max_relevant_member_bytes=MAX_RELEVANT_MEMBER_BYTES,
            max_total_relevant_bytes=MAX_RELEVANT_BYTES,
        )
    except M20ArxivBackwardError:
        raise
    member_inventory = [
        {"path": name, "size_bytes": len(raw), "sha256": _sha(raw)}
        for name, raw in sorted(members.items())
    ]
    try:
        with tempfile.TemporaryDirectory(prefix="ra-m21-source-") as name:
            source_root = Path(name)
            for relative, raw in members.items():
                destination = source_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
            detection = detect_main_tex(source_root)
            main_value = detection.get("main_path")
            if not isinstance(main_value, str):
                raise M21SevenSourceError("main_tex_missing")
            main_path = Path(main_value)
            flattened_path = source_root / "derived" / "flattened.tex"
            flatten = flatten_latex_bundle(main_path, source_root, flattened_path)
            structure = extract_latex_structure(flattened_path, source_root=source_root)
            main_member = main_path.relative_to(source_root).as_posix()
    except M21SevenSourceError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise M21SevenSourceError("source_parse_failed") from exc
    anchors = _extract_anchor_rows(
        paper_id=f"candidate_arxiv_{arxiv_id.replace('.', '_')}",
        source_path=Path("structured_source.json"),
        record=structure,
        max_anchors=MAX_ANCHORS + 1,
    )
    if len(anchors) > MAX_ANCHORS:
        raise M21SevenSourceError("anchor_cap_exceeded")
    sections = structure.get("sections") or []
    equations = structure.get("equations") or []
    theorem_like_blocks = structure.get("theorem_like_blocks") or []
    citations = structure.get("citations") or []
    bibliography = structure.get("bibliography") or []
    technical_text_available = bool(sections or equations or theorem_like_blocks)
    main_raw = members.get(main_member, b"")
    pdf_wrapper = b"\\includepdf" in main_raw or b"\\includepdf" in main_raw.replace(
        b" ", b""
    )
    if technical_text_available:
        parse_status = "available_machine_parsed"
        parse_gap = None
    elif pdf_wrapper:
        parse_status = "source_available_text_parse_gap"
        parse_gap = "SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE"
    else:
        parse_status = "source_available_text_parse_gap"
        parse_gap = "SOURCE_AVAILABLE_TEXT_PARSE_GAP_ZERO_STRUCTURAL_YIELD"
    structured = {
        "schema_version": f"{SCHEMA_VERSION}-structured-source",
        "status": parse_status,
        "source_package_sha256": _sha_file(body_path),
        "source_package_bytes": body_path.stat().st_size,
        "arxiv_id": arxiv_id,
        "main_tex_member": main_member,
        "unresolved_include_count": len(flatten.get("unresolved_includes") or []),
        "sections": [
            _sanitized_block(row, ("level", "command", "title", "line", "labels"))
            for row in structure.get("sections") or []
        ],
        "equations": [
            _sanitized_block(row, ("environment", "line", "labels"))
            for row in structure.get("equations") or []
        ],
        "theorem_like_blocks": [
            _sanitized_block(row, ("environment", "line", "labels"))
            for row in structure.get("theorem_like_blocks") or []
        ],
        "citation_count": len(citations),
        "bibliography_count": len(bibliography),
        "limitations": structure.get("limitations") or [],
        "raw_source_included": False,
    }
    if parse_gap is not None:
        structured["parse_gap_code"] = parse_gap
    anchor_packet = {
        "schema_version": f"{SCHEMA_VERSION}-anchors",
        "status": (
            "machine_extracted_review_candidates"
            if technical_text_available
            else "source_available_text_parse_gap"
        ),
        "anchor_cap": MAX_ANCHORS,
        "anchor_count": len(anchors),
        "anchors": anchors,
        "supported_claims": [],
        "ready_for_prose": False,
        "nonclaims": [
            "technical_claim_support",
            "mathematical_correctness",
            "complete_paper_understanding",
            "retraction_or_publication_safety",
        ],
    }
    if parse_gap is not None:
        anchor_packet["parse_gap_code"] = parse_gap
        anchor_packet["next_required_action"] = "pdf_fallback_or_manual_source_review_out_of_scope"
    return {
        "archive_diagnostics": archive,
        "text_member_inventory": member_inventory,
        "structured_source": structured,
        "anchor_packet": anchor_packet,
    }


def _derived_artifacts(
    candidate_root: Path, body_path: Path, *, arxiv_id: str
) -> dict[str, Any]:
    parsed = _parse_source(body_path, arxiv_id=arxiv_id)
    return {
        "text_member_inventory.json": {
            "schema_version": f"{SCHEMA_VERSION}-text-members",
            "archive_diagnostics": parsed["archive_diagnostics"],
            "members": parsed["text_member_inventory"],
        },
        "structured_source.json": parsed["structured_source"],
        "anchor_candidates.json": parsed["anchor_packet"],
    }


def _legacy_v1_parse_gap_projection(
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    projected = json.loads(json.dumps(artifacts))
    structured = projected["structured_source.json"]
    anchors = projected["anchor_candidates.json"]
    structured["status"] = "available_machine_parsed"
    structured.pop("parse_gap_code", None)
    anchors["status"] = "machine_extracted_review_candidates"
    anchors.pop("parse_gap_code", None)
    anchors.pop("next_required_action", None)
    return projected


def _inventory(root: Path) -> dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA_VERSION}-inventory",
        "inventory_excludes_itself": True,
        "files": [
            {
                "relative_path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha_file(path),
            }
            for path in sorted(row for row in root.rglob("*") if row.is_file())
            if path.name != "artifact_inventory.json"
        ],
    }


def replay_seven_source_campaign(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    manifest = json.loads((root / "run_manifest.json").read_text())
    route = json.loads((root / "route_ledger.json").read_text())
    rows = route.get("rows")
    allowed_statuses = {
        "accepted_and_parsed",
        "closed_source_parse_gap",
        "closed_source_failure",
        "not_dispatched_root_capacity",
        "not_dispatched_campaign_veto",
    }
    preserved = manifest.get("preserved_execution_sources")
    if (
        manifest.get("candidate_ids") != list(CANDIDATE_IDS)
        or manifest.get("request_limit") != len(CANDIDATE_IDS)
        or manifest.get("retry_policy") != "none"
        or manifest.get("credential_interface") is not False
        or manifest.get("pdf_fallback") is not False
        or not isinstance(preserved, list)
        or len(preserved) != len(EXECUTION_PATHS)
    ):
        raise M21SevenSourceError("run_manifest_invalid", campaign_veto=True)
    for artifact in preserved:
        if (
            not isinstance(artifact, dict)
            or not isinstance(artifact.get("relative_path"), str)
            or not isinstance(artifact.get("size_bytes"), int)
            or not isinstance(artifact.get("sha256"), str)
        ):
            raise M21SevenSourceError("run_manifest_invalid", campaign_veto=True)
        path = (root / artifact["relative_path"]).resolve(strict=True)
        if (
            path.parent != (root / "execution_sources").resolve(strict=True)
            or path.stat().st_size != artifact["size_bytes"]
            or _sha_file(path) != artifact["sha256"]
        ):
            raise M21SevenSourceError("execution_source_tampered", campaign_veto=True)
    preserved_by_name = {
        Path(row["relative_path"]).name: row["sha256"] for row in preserved
    }
    campaign_inputs = manifest.get("campaign_inputs")
    if (
        not isinstance(campaign_inputs, dict)
        or campaign_inputs.get("selection_sha256")
        != preserved_by_name.get(SELECTION_PATH.name)
        or campaign_inputs.get("triage_sha256")
        != preserved_by_name.get(TRIAGE_PATH.name)
    ):
        raise M21SevenSourceError("campaign_input_replay_mismatch", campaign_veto=True)
    if (
        route.get("candidate_ids") != list(CANDIDATE_IDS)
        or route.get("retry_count") != 0
        or not isinstance(rows, list)
        or [row.get("arxiv_id") for row in rows] != list(CANDIDATE_IDS)
        or len(rows) != len(CANDIDATE_IDS)
        or any(
            not isinstance(row, dict)
            or row.get("status") not in allowed_statuses
            or row.get("request_url") != f"https://arxiv.org/e-print/{row.get('arxiv_id')}"
            or row.get("requests_dispatched") not in {0, 1}
            or row.get("retry_count") != 0
            for row in rows
        )
        or sum(row.get("requests_dispatched") == 1 for row in rows)
        != route.get("requests_dispatched")
    ):
        raise M21SevenSourceError("route_ledger_invalid", campaign_veto=True)
    accepted = 0
    parsed = 0
    parse_gaps = 0
    legacy_reconciliations: list[dict[str, str]] = []
    for row in rows:
        candidate_root = root / "candidates" / row["arxiv_id"].replace(".", "_")
        body_path = candidate_root / "accepted_source.body"
        if row.get("status") in {"accepted_and_parsed", "closed_source_parse_gap"}:
            accepted += 1
            if (
                not body_path.is_file()
                or body_path.is_symlink()
                or body_path.stat().st_size != row.get("source_bytes")
                or _sha_file(body_path) != row.get("source_sha256")
            ):
                raise M21SevenSourceError("accepted_source_tampered", campaign_veto=True)
            _validate_download_result(
                {
                    "size_bytes": row.get("source_bytes"),
                    "sha256": row.get("source_sha256"),
                    "http_status": row.get("http_status"),
                    "content_type": row.get("content_type"),
                    "declared_content_length": row.get("declared_content_length"),
                    "final_url_observation": row.get("final_url_observation"),
                    "final_url_matches_request": row.get("final_url_matches_request"),
                },
                body_path=body_path,
                max_bytes=row.get("effective_source_cap_bytes"),
            )
            expected = _derived_artifacts(
                candidate_root, body_path, arxiv_id=row["arxiv_id"]
            )
            expected_parse_status = expected["structured_source.json"]["status"]
            expected_outcome = (
                "accepted_and_parsed"
                if expected_parse_status == "available_machine_parsed"
                else "closed_source_parse_gap"
            )
            replay_expected = expected
            if row.get("status") != expected_outcome:
                if (
                    row.get("status") == "accepted_and_parsed"
                    and expected_outcome == "closed_source_parse_gap"
                ):
                    replay_expected = _legacy_v1_parse_gap_projection(expected)
                    legacy_reconciliations.append({
                        "arxiv_id": row["arxiv_id"],
                        "recorded_outcome": "accepted_and_parsed",
                        "reconciled_outcome": "closed_source_parse_gap",
                        "parse_gap_code": expected["structured_source.json"][
                            "parse_gap_code"
                        ],
                    })
                else:
                    raise M21SevenSourceError(
                        "route_parse_outcome_mismatch", campaign_veto=True
                    )
            for artifact, value in expected.items():
                if (candidate_root / artifact).read_bytes() != _pretty(
                    replay_expected[artifact]
                ):
                    raise M21SevenSourceError("derived_replay_mismatch", campaign_veto=True)
            if expected_outcome == "accepted_and_parsed":
                parsed += 1
            else:
                parse_gaps += 1
        elif body_path.exists():
            raise M21SevenSourceError("failed_source_body_present", campaign_veto=True)
    expected_source_rows = _source_status_rows(rows)
    if (root / "source_status.json").read_bytes() != _pretty({
        "schema_version": f"{SCHEMA_VERSION}-source-status",
        "rows": expected_source_rows,
    }):
        raise M21SevenSourceError("source_status_replay_mismatch", campaign_veto=True)
    if (root / "claim_support.json").read_bytes() != _pretty({
        "schema_version": f"{SCHEMA_VERSION}-claim-support",
        "claims": [],
        "status": "no_supported_claims_machine_anchors_only",
    }):
        raise M21SevenSourceError("claim_support_replay_mismatch", campaign_veto=True)
    if (root / "quarantine_status.json").read_bytes() != _pretty({
        "schema_version": f"{SCHEMA_VERSION}-quarantine-status",
        "rows": _quarantine_rows(rows),
    }):
        raise M21SevenSourceError("quarantine_replay_mismatch", campaign_veto=True)
    if _root_bytes(root) > MAX_ROOT_BYTES:
        raise M21SevenSourceError("evidence_root_cap_exceeded", campaign_veto=True)
    inventory_path = root / "artifact_inventory.json"
    if manifest.get("status") == "closed":
        if (
            not inventory_path.is_file()
            or inventory_path.is_symlink()
            or inventory_path.read_bytes() != _pretty(_inventory(root))
        ):
            raise M21SevenSourceError("artifact_inventory_replay_mismatch", campaign_veto=True)
    elif manifest.get("status") != "running":
        raise M21SevenSourceError("run_manifest_invalid", campaign_veto=True)
    return {
        "schema_version": f"{SCHEMA_VERSION}-replay",
        "status": "passed",
        "candidate_count": len(rows),
        "requests_dispatched": route["requests_dispatched"],
        "accepted_source_package_count": accepted,
        "accepted_and_parsed_count": parsed,
        "source_parse_gap_count": parse_gaps,
        "legacy_outcome_reconciliations": legacy_reconciliations,
        "root_bytes_before_replay_record": _root_bytes(root),
    }


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


def _quarantine_rows(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "arxiv_id": row["arxiv_id"],
        "publication_retraction_version_status": "NOT_CHECKED",
        "claim_support_allowed": False,
    } for row in route_rows]


def run_seven_source_campaign(
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
        raise M21SevenSourceError("cpu_only_environment_required", campaign_veto=True)
    if output_root.exists() or not output_root.parent.is_dir():
        raise M21SevenSourceError("output_root_not_fresh", campaign_veto=True)
    if shutil.disk_usage(output_root.parent).free < 550_000_000:
        raise M21SevenSourceError("insufficient_free_space", campaign_veto=True)
    output_root.mkdir(mode=0o700)
    (output_root / "candidates").mkdir(mode=0o700)
    execution_sources = output_root / "execution_sources"
    execution_sources.mkdir(mode=0o700)
    preserved_sources = []
    for relative in EXECUTION_PATHS:
        source = (repository_root / relative).resolve(strict=True)
        preserved_sources.append(
            _atomic_copy(source, execution_sources / source.name, root=output_root)
        )
    started = now()
    started_clock = time.monotonic()
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-manifest",
        "status": "running",
        "started_at_utc": started,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "command_argv": [
            sys.executable,
            "-m",
            "research_assistant.survey.m21_seven_source_campaign",
            "--repository-root",
            str(repository_root),
            "--output-root",
            str(output_root),
        ],
        "git_commit": _git(repository_root, "rev-parse", "HEAD"),
        "git_tree": _git(repository_root, "rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(_git(repository_root, "status", "--porcelain")),
        "environment": "project interpreter; deliberate CPU-only campaign",
        "hardware": "CPU-only; GPU devices intentionally hidden",
        "data_version": "exact seven arXiv IDs from M21 replay-valid context triage",
        "plan_path": str((repository_root / PLAN_PATH).resolve(strict=True)),
        "campaign_inputs": campaign_inputs,
        "random_seeds": "N/A (deterministic source intake and parse)",
        "cpu_only": True,
        "candidate_ids": list(CANDIDATE_IDS),
        "request_limit": len(CANDIDATE_IDS),
        "retry_policy": "none",
        "credential_interface": False,
        "pdf_fallback": False,
        "per_source_cap_bytes": MAX_SOURCE_BYTES,
        "evidence_root_cap_bytes": MAX_ROOT_BYTES,
        "derived_reserve_bytes": DERIVED_RESERVE_BYTES,
        "anchor_cap_per_source": MAX_ANCHORS,
        "preserved_execution_sources": preserved_sources,
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
            row.update(
                status="not_dispatched_campaign_veto",
                error_code=campaign_veto,
            )
            route_rows.append(row)
            break
        try:
            request = _request(arxiv_id)
            row["requests_dispatched"] = 1
            row["effective_source_cap_bytes"] = min(MAX_SOURCE_BYTES, remaining)
            download = downloader(
                request,
                destination=body_path,
                max_bytes=row["effective_source_cap_bytes"],
            )
            _validate_download_result(
                download,
                body_path=body_path,
                max_bytes=row["effective_source_cap_bytes"],
            )
            derived = _derived_artifacts(
                candidate_root, body_path, arxiv_id=arxiv_id
            )
            for artifact, value in derived.items():
                _atomic_json(candidate_root / artifact, value, root=output_root)
            parsed_status = derived["structured_source.json"]["status"]
            row.update(
                status=(
                    "accepted_and_parsed"
                    if parsed_status == "available_machine_parsed"
                    else "closed_source_parse_gap"
                ),
                source_bytes=body_path.stat().st_size,
                source_sha256=_sha_file(body_path),
                http_status=download.get("http_status"),
                content_type=download.get("content_type"),
                declared_content_length=download.get("declared_content_length"),
                final_url_observation=download.get("final_url_observation"),
                final_url_matches_request=download.get("final_url_matches_request"),
                anchor_count=derived["anchor_candidates.json"]["anchor_count"],
                error_code=derived["structured_source.json"].get("parse_gap_code"),
            )
        except (M20ArxivOnlyLiveError, M20ArxivBackwardError, M21SevenSourceError) as exc:
            error_code = getattr(exc, "code", "source_processing_failed")
            for path in candidate_root.iterdir():
                if path.is_file():
                    path.unlink()
            row.update(status="closed_source_failure", error_code=error_code)
            if isinstance(exc, M21SevenSourceError) and exc.campaign_veto:
                campaign_veto = error_code
        except Exception:
            for path in candidate_root.iterdir():
                if path.is_file():
                    path.unlink()
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
    source_rows = _source_status_rows(route_rows)
    _atomic_json(output_root / "source_status.json", {
        "schema_version": f"{SCHEMA_VERSION}-source-status",
        "rows": source_rows,
    }, root=output_root)
    _atomic_json(output_root / "claim_support.json", {
        "schema_version": f"{SCHEMA_VERSION}-claim-support",
        "claims": [],
        "status": "no_supported_claims_machine_anchors_only",
    }, root=output_root)
    _atomic_json(output_root / "quarantine_status.json", {
        "schema_version": f"{SCHEMA_VERSION}-quarantine-status",
        "rows": _quarantine_rows(route_rows),
    }, root=output_root)
    replay = None
    if campaign_veto is None:
        try:
            replay = replay_seven_source_campaign(output_root)
            _atomic_json(output_root / "offline_replay.json", replay, root=output_root)
        except M21SevenSourceError as exc:
            campaign_veto = exc.code
    passed = campaign_veto is None and len(route_rows) == len(CANDIDATE_IDS)
    result = {
        "schema_version": f"{SCHEMA_VERSION}-result",
        "classification": "M21_SEVEN_SOURCE_CAMPAIGN_PASSED" if passed else "TERMINAL_CAMPAIGN_VETO",
        "primary_criterion_passed": passed,
        "campaign_veto": campaign_veto,
        "requests_dispatched": route["requests_dispatched"],
        "retry_count": 0,
        "accepted_and_parsed_count": sum(row["status"] == "accepted_and_parsed" for row in route_rows),
        "source_gap_count": sum(row["status"] != "accepted_and_parsed" for row in route_rows),
        "offline_replay_status": replay["status"] if replay else "not_passed",
        "started_at_utc": started,
        "completed_at_utc": now(),
        "wall_time_seconds": round(time.monotonic() - started_clock, 6),
        "root_bytes_before_close": _root_bytes(output_root),
        "nonclaims": [
            "candidate_relevance",
            "technical_claim_support",
            "mathematical_correctness",
            "publication_or_retraction_safety",
            "literature_completeness",
            "provider_reliability",
        ],
    }
    manifest.update(status="closed", completed_at_utc=result["completed_at_utc"])
    _atomic_json(output_root / "run_manifest.json", manifest, root=output_root)
    _atomic_json(output_root / "terminal_result.json", result, root=output_root)
    _atomic_json(output_root / "artifact_inventory.json", _inventory(output_root), root=output_root)
    if _root_bytes(output_root) > MAX_ROOT_BYTES:
        raise M21SevenSourceError("evidence_root_cap_exceeded_after_close", campaign_veto=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the bounded seven-candidate arXiv source campaign"
    )
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_seven_source_campaign(
            repository_root=args.repository_root,
            output_root=args.output_root,
        )
    except M21SevenSourceError as exc:
        print(json.dumps({"status": "preflight_failed", "error_code": exc.code}))
        return 2
    print(json.dumps({"output_root": str(args.output_root), **result}, sort_keys=True))
    return 0 if result["primary_criterion_passed"] else 1


__all__ = [
    "CANDIDATE_IDS",
    "M21SevenSourceError",
    "replay_seven_source_campaign",
    "run_seven_source_campaign",
]


if __name__ == "__main__":
    raise SystemExit(main())
