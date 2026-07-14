from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ra-surveybench-local-manifest-v1"
REPORT_SCHEMA_VERSION = "ra-surveybench-local-manifest-report-v1"

FORBIDDEN_ENTRY_FIELDS = {
    "raw_text",
    "extracted_text",
    "full_text",
    "pdf_path",
    "source_path",
    "local_path",
    "absolute_path",
    "transcript",
}

FORBIDDEN_PATH_TOKENS = (
    "/home/",
    "/Users/",
    "C:\\",
    "file://",
    "s3://",
    "gs://",
)

FORBIDDEN_EXTENSIONS = (
    ".pdf",
    ".tex",
    ".zip",
    ".tar",
    ".gz",
)


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: expected schema_version {SCHEMA_VERSION!r}")
    return data


def _contains_forbidden_path_token(value: str) -> bool:
    return any(token in value for token in FORBIDDEN_PATH_TOKENS)


def _looks_like_raw_artifact(value: str) -> bool:
    lower = value.lower()
    return lower.endswith(FORBIDDEN_EXTENSIONS) or any(f"{ext}#" in lower for ext in FORBIDDEN_EXTENSIONS)


def validate_local_manifest(path: Path) -> dict[str, Any]:
    path = path.resolve()
    manifest = load_manifest(path)
    issues: list[dict[str, Any]] = []
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        issues.append({"code": "entries_not_list", "message": "entries must be a list"})
        entries = []

    categories: dict[str, int] = {}
    blocked_private_only = 0
    expected_tasks: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append({"code": "entry_not_object", "index": index})
            continue
        forbidden_fields = sorted(FORBIDDEN_ENTRY_FIELDS & set(entry))
        if forbidden_fields:
            issues.append({
                "code": "forbidden_raw_field",
                "index": index,
                "fields": forbidden_fields,
            })
        redacted_id = entry.get("redacted_id")
        if not isinstance(redacted_id, str) or not redacted_id.startswith("redacted:"):
            issues.append({"code": "missing_redacted_id", "index": index})
        category = str(entry.get("category", "unknown"))
        categories[category] = categories.get(category, 0) + 1
        if entry.get("private_only"):
            blocked_private_only += 1
        for task in entry.get("expected_tasks", []):
            expected_tasks.add(str(task))
        for key, value in entry.items():
            if isinstance(value, str):
                if _contains_forbidden_path_token(value):
                    issues.append({"code": "private_path_leak", "index": index, "field": key})
                if _looks_like_raw_artifact(value):
                    issues.append({"code": "raw_artifact_reference", "index": index, "field": key})

    status = "passed" if not issues else "failed"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest_path": _display_path(path),
        "status": status,
        "entry_count": len(entries),
        "categories": dict(sorted(categories.items())),
        "expected_tasks": sorted(expected_tasks),
        "blocked_private_only_entries": blocked_private_only,
        "issues": issues,
        "what_is_not_concluded": [
            "private corpus content coverage",
            "permission to publish private manifest contents",
            "release-ready broad validation",
        ],
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return f"redacted:{path.name}"
