from __future__ import annotations

from scripts.literature_survey_phase6_boundary_validation import run_validation


def test_phase6_boundary_validation_preserves_privacy_and_source_honesty() -> None:
    result = run_validation()

    assert result["schema_version"] == "ra-literature-survey-phase6-boundary-validation-v1"
    assert result["status"] == "passed"
    assert result["issues"] == []
    contract = result["boundary_contract"]
    assert contract["live_web_or_api_used"] is False
    assert contract["source_or_pdf_download_attempted"] is False
    assert contract["public_arxiv_entries_are_metadata_only"] is True
    assert contract["sanitized_local_manifest_contains_no_private_paths"] is True
    assert "product readiness" in result["what_is_not_concluded"]
