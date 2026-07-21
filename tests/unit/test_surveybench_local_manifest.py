from __future__ import annotations

from pathlib import Path

from research_assistant.benchmarks.local_manifest import validate_local_manifest


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "surveybench" / "local_manifest"


def test_valid_redacted_local_manifest_passes_without_private_paths() -> None:
    report = validate_local_manifest(FIXTURES / "redacted_manifest.valid.json")

    assert report["schema_version"] == "ra-surveybench-local-manifest-report-v1"
    assert report["status"] == "passed"
    assert report["entry_count"] == 3
    assert report["blocked_private_only_entries"] == 2
    assert report["issues"] == []
    assert "citation_map" in report["expected_tasks"]


def test_invalid_local_manifest_rejects_private_paths_and_raw_content() -> None:
    report = validate_local_manifest(FIXTURES / "redacted_manifest.invalid.json")
    codes = {issue["code"] for issue in report["issues"]}

    assert report["status"] == "failed"
    assert "forbidden_raw_field" in codes
    assert "private_path_leak" in codes
    assert "raw_artifact_reference" in codes
    assert "missing_redacted_id" in codes
