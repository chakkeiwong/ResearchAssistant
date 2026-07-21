from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_assistant.benchmarks.local_manifest import validate_local_manifest
from research_assistant.individual_release import privacy_status


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = ROOT / "docs/validation/literature_survey_automation_phase6_public_sanitized_corpus_2026-07-06"
LOCAL_MANIFEST = ROOT / "tests/fixtures/surveybench/local_manifest/redacted_manifest.valid.json"
PUBLIC_ARXIV_IDS = (
    "2201.12220v3",
    "1903.03704",
)
FORBIDDEN_RAW_SUFFIXES = (
    ".pdf",
    ".tex",
    ".zip",
    ".tar",
    ".gz",
)
FORBIDDEN_TEXT_TOKENS = (
    "/home/",
    "/Users/",
    "C:\\",
    "file://",
    "s3://",
    "gs://",
    "raw_text",
    "extracted_text",
    "full_text",
    "pdf_path",
    "source_path",
    "local_path",
    "absolute_path",
)


def run_validation() -> dict[str, Any]:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    public_manifest = _public_manifest()
    public_manifest_path = VALIDATION_DIR / "public_arxiv_blocked_source_manifest.json"
    public_manifest_path.write_text(json.dumps(public_manifest, indent=2, sort_keys=True))

    local_manifest_report = validate_local_manifest(LOCAL_MANIFEST)
    local_manifest_report_path = VALIDATION_DIR / "sanitized_local_manifest_report.json"
    local_manifest_report_path.write_text(json.dumps(local_manifest_report, indent=2, sort_keys=True))

    source_status_report = _source_status_report(public_manifest, local_manifest_report)
    source_status_report_path = VALIDATION_DIR / "source_download_status_report.json"
    source_status_report_path.write_text(json.dumps(source_status_report, indent=2, sort_keys=True))

    privacy = _phase6_privacy_report()
    privacy_report_path = VALIDATION_DIR / "privacy_boundary_report.json"
    privacy_report_path.write_text(json.dumps(privacy, indent=2, sort_keys=True))

    raw_scan = _scan_validation_dir()
    raw_scan_path = VALIDATION_DIR / "raw_artifact_scan.json"
    raw_scan_path.write_text(json.dumps(raw_scan, indent=2, sort_keys=True))

    issues = []
    if local_manifest_report["status"] != "passed":
        issues.append({"code": "local_manifest_failed"})
    if privacy["status"] != "passed":
        issues.append({"code": "privacy_boundary_failed"})
    if raw_scan["status"] != "passed":
        issues.append({"code": "raw_artifact_scan_failed"})
    if any(row["source_status"] != "source_blocked_no_live_access" for row in public_manifest["entries"]):
        issues.append({"code": "public_manifest_source_overclaim"})

    result = {
        "schema_version": "ra-literature-survey-phase6-boundary-validation-v1",
        "status": "passed" if not issues else "failed",
        "public_manifest": str(public_manifest_path.relative_to(ROOT)),
        "local_manifest_report": str(local_manifest_report_path.relative_to(ROOT)),
        "source_status_report": str(source_status_report_path.relative_to(ROOT)),
        "privacy_report": str(privacy_report_path.relative_to(ROOT)),
        "raw_artifact_scan": str(raw_scan_path.relative_to(ROOT)),
        "issues": issues,
        "boundary_contract": {
            "live_web_or_api_used": False,
            "source_or_pdf_download_attempted": False,
            "raw_private_artifacts_committed": False,
            "public_arxiv_entries_are_metadata_only": True,
            "sanitized_local_manifest_contains_no_private_paths": local_manifest_report["status"] == "passed",
        },
        "what_is_not_concluded": [
            "broad web coverage",
            "download reliability at scale",
            "source inspection completeness",
            "scientific correctness",
            "product readiness",
        ],
    }
    result_path = VALIDATION_DIR / "phase6_boundary_validation_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def _public_manifest() -> dict[str, Any]:
    return {
        "schema_version": "ra-literature-survey-public-arxiv-blocked-source-manifest-v1",
        "status": "blocked_without_live_or_download_approval",
        "topic": "Neural Optimal Transport / transport-map literature survey automation",
        "entries": [
            {
                "paper_key": f"public_arxiv_{index:03d}",
                "identifier": f"arxiv:{arxiv_id}",
                "source_status": "source_blocked_no_live_access",
                "download_status": "not_attempted",
                "reason": "Phase 6 safe lane does not fetch live metadata, source archives, or PDFs.",
                "allowed_claims": ["identifier appears in a public-manifest planning row"],
                "forbidden_claims": [
                    "source inspected",
                    "download available",
                    "technical claim support",
                    "citation coverage",
                ],
            }
            for index, arxiv_id in enumerate(PUBLIC_ARXIV_IDS, start=1)
        ],
        "what_is_not_concluded": [
            "source availability",
            "download reliability",
            "current metadata correctness",
            "technical claim support",
            "live web coverage",
        ],
    }


def _source_status_report(public_manifest: dict[str, Any], local_manifest_report: dict[str, Any]) -> dict[str, Any]:
    public_rows = public_manifest["entries"]
    return {
        "schema_version": "ra-literature-survey-phase6-source-download-status-v1",
        "public_arxiv": {
            "entry_count": len(public_rows),
            "source_blocked_no_live_access": sum(
                1 for row in public_rows if row["source_status"] == "source_blocked_no_live_access"
            ),
            "downloads_attempted": 0,
            "source_inspections_claimed": 0,
        },
        "sanitized_local_manifest": {
            "status": local_manifest_report["status"],
            "entry_count": local_manifest_report["entry_count"],
            "categories": local_manifest_report["categories"],
            "blocked_private_only_entries": local_manifest_report["blocked_private_only_entries"],
        },
        "what_is_not_concluded": [
            "public source availability",
            "private corpus coverage",
            "claim support",
            "download reliability",
        ],
    }


def _phase6_privacy_report() -> dict[str, Any]:
    status = privacy_status(root=ROOT)
    raw_issues = status.get("issues", [])
    blocking_codes = {
        "private_path_leak",
        "forbidden_private_fields",
        "raw_artifact_reference",
    }
    blocking = [
        issue for issue in raw_issues
        if isinstance(issue, dict) and issue.get("code") in blocking_codes
    ]
    return {
        "schema_version": "ra-literature-survey-phase6-privacy-boundary-v1",
        "status": "passed" if not blocking else "failed",
        "underlying_privacy_status": status.get("status"),
        "blocking_issue_count": len(blocking),
        "blocking_issues": blocking,
        "privacy_status_summary": {
            "workspace_root": status.get("workspace_root"),
            "offline_default": status.get("offline_default"),
            "provider_count": len(status.get("providers", [])) if isinstance(status.get("providers"), list) else 0,
        },
        "what_is_not_concluded": [
            "absence of every possible private string in the repository",
            "permission to publish private manifest contents",
        ],
    }


def _scan_validation_dir() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    scanned_files = []
    for path in sorted(VALIDATION_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        scanned_files.append(rel)
        if path.suffix.lower() in FORBIDDEN_RAW_SUFFIXES:
            issues.append({"code": "raw_artifact_file", "path": rel})
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(errors="ignore")
        for token in FORBIDDEN_TEXT_TOKENS:
            if token in text:
                issues.append({"code": "forbidden_text_token", "path": rel, "token": token})
    return {
        "schema_version": "ra-literature-survey-phase6-raw-artifact-scan-v1",
        "status": "passed" if not issues else "failed",
        "scanned_file_count": len(scanned_files),
        "scanned_files": scanned_files,
        "issues": issues,
    }


def main() -> int:
    result = run_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
