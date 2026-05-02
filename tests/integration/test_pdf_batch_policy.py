from __future__ import annotations

import json
from pathlib import Path

from research_assistant.adapters.mcp_permissions import create_arxiv_batch_grant
from research_assistant.ingest.arxiv_batch import plan_arxiv_batch_intake
from research_assistant.ingest.pdf_batch_policy import PdfBatchPolicy, pdf_batch_policy_status, run_pdf_batch_download, validate_pdf_batch_policy


def test_pdf_batch_policy_status_keeps_execution_disabled() -> None:
    status = pdf_batch_policy_status()

    assert status["status"] == "grant_bound_cli_execution_available"
    assert status["execution_enabled"] is True
    assert status["mcp_exposed"] is False
    assert status["destination"] == "inbox"
    assert status["overwrite_policy"] == "no_overwrite"


def test_pdf_batch_policy_accepts_bounded_arxiv_candidates() -> None:
    result = validate_pdf_batch_policy([
        {"pdf_url": "https://arxiv.org/pdf/2401.00001", "declared_bytes": 1024},
        {"pdf_url": "https://export.arxiv.org/pdf/2401.00002", "declared_bytes": 2048},
    ])

    assert result["status"] == "ok"
    assert result["execution_enabled"] is True
    assert result["mcp_exposed"] is False
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


class _FakePdfResponse:
    def __init__(self, chunks: list[bytes], *, final_url: str = "https://arxiv.org/pdf/2401.00001") -> None:
        self._chunks = chunks
        self._final_url = final_url
        self.headers = {"Content-Length": str(sum(len(chunk) for chunk in chunks))}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self, _size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def geturl(self) -> str:
        return self._final_url


def _pdf_grant(tmp_path: Path, arxiv_ids: list[str]):
    plan = plan_arxiv_batch_intake(
        arxiv_ids=arxiv_ids,
        max_papers=len(arxiv_ids),
        destination="inbox",
        operation="pdf_inbox_download",
        root=tmp_path,
    )
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        operation="pdf_inbox_download",
        destination="inbox",
        max_papers=len(arxiv_ids),
        root=tmp_path,
        arxiv_ids=arxiv_ids,
    )["grant"]
    return plan, grant


def test_pdf_batch_download_requires_grant_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    plan, grant = _pdf_grant(tmp_path, ["2401.00001"])
    candidate = {
        "arxiv_id": "2401.00001",
        "title": "Tiny PDF",
        "pdf_url": "https://arxiv.org/pdf/2401.00001",
        "declared_bytes": 24,
    }

    def fake_urlopen(url: str, timeout: int):
        assert url == candidate["pdf_url"]
        assert timeout == 30
        return _FakePdfResponse([b"%PDF-1.4\n", b"tiny fixture\n"])

    monkeypatch.setattr("research_assistant.ingest.pdf_batch_policy.urllib.request.urlopen", fake_urlopen)
    result = run_pdf_batch_download(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        candidates=[candidate],
        root=tmp_path,
    )
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    inbox_files = list((tmp_path / "local_research" / "inbox").glob("*.pdf"))

    assert result["status"] == "completed"
    assert result["downloaded_count"] == 1
    assert result["review_policy"] == "review_material_only"
    assert len(inbox_files) == 1
    assert inbox_files[0].read_bytes().startswith(b"%PDF-1.4")
    assert manifest["downloaded_count"] == 1
    assert manifest["results"][0]["sha256"]
    assert not any(row.get("review_status") == "approved" for row in manifest["results"])
    assert (tmp_path / "local_research" / "governance" / "mcp" / "audit" / f"{grant['grant_id']}.audit.jsonl").exists()


def test_pdf_batch_download_skips_duplicate_without_overwrite(tmp_path: Path, monkeypatch) -> None:
    plan, grant = _pdf_grant(tmp_path, ["2401.00001"])
    target = tmp_path / "local_research" / "inbox" / "2401_00001_tiny_pdf.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("duplicate should skip before network")

    monkeypatch.setattr("research_assistant.ingest.pdf_batch_policy.urllib.request.urlopen", fail_urlopen)
    result = run_pdf_batch_download(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        candidates=[{
            "arxiv_id": "2401.00001",
            "title": "Tiny PDF",
            "pdf_url": "https://arxiv.org/pdf/2401.00001",
        }],
        root=tmp_path,
    )

    assert result["status"] == "completed"
    assert result["downloaded_count"] == 0
    assert result["skipped_duplicates"][0]["status"] == "skipped_duplicate"
    assert target.read_bytes() == b"existing"


def test_pdf_batch_download_cleans_partial_on_stream_limit(tmp_path: Path, monkeypatch) -> None:
    plan, grant = _pdf_grant(tmp_path, ["2401.00001"])
    candidate = {
        "arxiv_id": "2401.00001",
        "title": "Tiny PDF",
        "pdf_url": "https://arxiv.org/pdf/2401.00001",
    }

    monkeypatch.setattr(
        "research_assistant.ingest.pdf_batch_policy.urllib.request.urlopen",
        lambda *_args, **_kwargs: _FakePdfResponse([b"abc", b"def"], final_url=candidate["pdf_url"]),
    )
    result = run_pdf_batch_download(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        candidates=[candidate],
        root=tmp_path,
        policy=PdfBatchPolicy(max_per_file_bytes=4),
    )
    inbox = tmp_path / "local_research" / "inbox"

    assert result["status"] == "completed_with_failures"
    assert result["failures"][0]["partial_cleaned"] is True
    assert not list(inbox.glob("*.part"))
    assert not list(inbox.glob("*.pdf"))


def test_pdf_batch_download_blocks_redirect_to_unapproved_domain(tmp_path: Path, monkeypatch) -> None:
    plan, grant = _pdf_grant(tmp_path, ["2401.00001"])
    candidate = {
        "arxiv_id": "2401.00001",
        "title": "Tiny PDF",
        "pdf_url": "https://arxiv.org/pdf/2401.00001",
    }
    monkeypatch.setattr(
        "research_assistant.ingest.pdf_batch_policy.urllib.request.urlopen",
        lambda *_args, **_kwargs: _FakePdfResponse([b"pdf"], final_url="https://example.com/pdf"),
    )
    result = run_pdf_batch_download(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        candidates=[candidate],
        root=tmp_path,
    )

    assert result["status"] == "completed_with_failures"
    assert "redirect domain example.com is not allowed" in result["failures"][0]["reason"]


def test_pdf_batch_download_accepts_candidate_file_bound_plan(tmp_path: Path, monkeypatch) -> None:
    candidate_file = tmp_path / "candidates.json"
    candidate_file.write_text(json.dumps({
        "schema_version": "arxiv-query-candidates-v1",
        "candidate_batch_id": "pdf_candidate_file_test",
        "query": "transport maps HMC",
        "normalized_query": "transport maps hmc",
        "endpoint_url": "https://export.arxiv.org/api/query",
        "max_candidates": 1,
        "request_timeout_seconds": 30,
        "result_ordering": "fixture",
        "source_status": {"status": "fixture"},
        "candidates": [{
            "arxiv_id": "2401.00001",
            "title": "Candidate Bound PDF",
            "pdf_url": "https://arxiv.org/pdf/2401.00001",
            "source_url": "https://arxiv.org/e-print/2401.00001",
            "entry_url": "https://arxiv.org/abs/2401.00001",
            "authors": ["Fixture Author"],
            "provenance_index": 0,
        }],
    }))
    plan = plan_arxiv_batch_intake(
        candidate_file=candidate_file,
        max_papers=1,
        destination="inbox",
        operation="pdf_inbox_download",
        root=tmp_path,
    )
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        operation="pdf_inbox_download",
        destination="inbox",
        max_papers=1,
        root=tmp_path,
        arxiv_ids=plan["arxiv_ids"],
    )["grant"]
    monkeypatch.setattr(
        "research_assistant.ingest.pdf_batch_policy.urllib.request.urlopen",
        lambda *_args, **_kwargs: _FakePdfResponse([b"%PDF candidate bound\n"]),
    )

    result = run_pdf_batch_download(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        candidates=json.loads(candidate_file.read_text())["candidates"],
        candidate_file=candidate_file,
        root=tmp_path,
    )

    assert result["status"] == "completed"
    assert result["downloaded_count"] == 1
