from __future__ import annotations

from research_assistant.ingest.pdf_batch_policy import PdfBatchPolicy, pdf_batch_policy_status, validate_pdf_batch_policy


def test_pdf_batch_policy_status_keeps_execution_disabled() -> None:
    status = pdf_batch_policy_status()

    assert status["status"] == "policy_checks_available"
    assert status["execution_enabled"] is False
    assert status["destination"] == "inbox"
    assert status["overwrite_policy"] == "no_overwrite"


def test_pdf_batch_policy_accepts_bounded_arxiv_candidates() -> None:
    result = validate_pdf_batch_policy([
        {"pdf_url": "https://arxiv.org/pdf/2401.00001", "declared_bytes": 1024},
        {"pdf_url": "https://export.arxiv.org/pdf/2401.00002", "declared_bytes": 2048},
    ])

    assert result["status"] == "ok"
    assert result["execution_enabled"] is False
    assert result["declared_total_bytes"] == 3072


def test_pdf_batch_policy_rejects_count_bytes_domain_and_overwrite() -> None:
    policy = PdfBatchPolicy(
        max_files=1,
        max_total_bytes=100,
        max_per_file_bytes=80,
        destination="source",
        overwrite_policy="overwrite",
    )
    result = validate_pdf_batch_policy([
        {"pdf_url": "https://arxiv.org/pdf/2401.00001", "declared_bytes": 90},
        {"pdf_url": "https://example.com/paper.pdf", "declared_bytes": 20},
    ], policy=policy)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "blocked"
    assert "pdf_destination_not_inbox" in codes
    assert "pdf_overwrite_not_allowed" in codes
    assert "pdf_max_files_exceeded" in codes
    assert "pdf_per_file_bytes_exceeded" in codes
    assert "pdf_total_bytes_exceeded" in codes
    assert "pdf_domain_not_allowed" in codes


def test_pdf_batch_policy_rejects_missing_url_and_invalid_bytes() -> None:
    result = validate_pdf_batch_policy([
        {"title": "missing URL"},
        {"pdf_url": "https://arxiv.org/pdf/2401.00001", "declared_bytes": "large"},
    ])
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "blocked"
    assert "pdf_candidate_missing_url" in codes
    assert "pdf_declared_bytes_invalid" in codes
