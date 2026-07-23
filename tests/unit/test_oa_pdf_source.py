from __future__ import annotations

from pathlib import Path

from research_assistant.survey.oa_pdf_source import fetch_open_access_pdf


class _Response:
    def __init__(self, url: str, body: bytes = b"%PDF-fixture") -> None:
        self.url = url
        self.body = body
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        if self.offset:
            return b""
        self.offset = len(self.body)
        return self.body if size < 0 else self.body[:size]


def test_oa_pdf_source_accepts_matching_title_and_sections(monkeypatch, tmp_path: Path) -> None:
    text = """A Bounded Research Method
Author One

1 Introduction
This paper introduces the research setting.

2 Method
We propose a bounded algorithm for the research problem.
"""
    monkeypatch.setattr(
        "research_assistant.survey.oa_pdf_source.extract_pdf_text",
        lambda *_args, **_kwargs: text,
    )
    result = fetch_open_access_pdf(
        "https://example.test/paper.pdf",
        root=tmp_path,
        paper_id="doi:10.1/test",
        expected_title="A Bounded Research Method",
        max_bytes=1024,
        opener=lambda url, *, timeout: _Response(url),
    )
    assert result["status"] == "available"
    assert result["source_type"] == "oa_pdf_pdftotext"
    assert result["sections"]
    assert Path(result["local_path"]).is_file()


def test_oa_pdf_source_rejects_identity_mismatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "research_assistant.survey.oa_pdf_source.extract_pdf_text",
        lambda *_args, **_kwargs: (
            "An Unrelated Technical Study\nJane Example and John Example\n\n"
            "Method\nWe propose something else."
        ),
    )
    result = fetch_open_access_pdf(
        "https://example.test/paper.pdf",
        root=tmp_path,
        paper_id="doi:10.1/test",
        expected_title="Credit Card Recommendation with Reinforcement Learning",
        max_bytes=1024,
        opener=lambda url, *, timeout: _Response(url),
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "oa_pdf_identity_mismatch"
    assert not list(tmp_path.rglob("*.pdf"))
