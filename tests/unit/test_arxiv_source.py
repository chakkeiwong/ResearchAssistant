from __future__ import annotations

import io
import tarfile
import urllib.error
from pathlib import Path

from research_assistant.source.arxiv_source import download_arxiv_source, fetch_arxiv_structured_source, unpack_arxiv_source


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'latex_sources' / 'multi_file'


def _source_tarball() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for path in sorted(FIXTURE.rglob('*')):
            if path.is_file():
                archive.add(path, arcname=str(path.relative_to(FIXTURE)))
    return buffer.getvalue()


class _FakeSourceResponse:
    def __init__(
        self,
        chunks: list[bytes],
        *,
        final_url: str = 'https://arxiv.org/e-print/2401.00001',
        content_length: str | None = None,
    ) -> None:
        self._chunks = list(chunks)
        self._final_url = final_url
        self.headers = {}
        if content_length is not None:
            self.headers['Content-Length'] = content_length

    def __enter__(self) -> '_FakeSourceResponse':
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._final_url

    def read(self, _size: int = -1) -> bytes:
        if not self._chunks:
            return b''
        return self._chunks.pop(0)


def test_unpack_arxiv_source_handles_tarball(tmp_path: Path) -> None:
    package = tmp_path / 'source-package'
    package.write_bytes(_source_tarball())
    unpack_dir = tmp_path / 'unpacked'

    diagnostics = unpack_arxiv_source(package, unpack_dir)

    assert (unpack_dir / 'main.tex').exists()
    assert (unpack_dir / 'sections' / 'method.tex').exists()
    assert 'main.tex' in diagnostics['unpacked_files']


def test_download_arxiv_source_enforces_stream_byte_limit(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / 'source-package'

    monkeypatch.setattr(
        'research_assistant.source.arxiv_source.urllib.request.urlopen',
        lambda *_args, **_kwargs: _FakeSourceResponse([b'abc', b'def']),
    )

    try:
        download_arxiv_source('2401.00001', target, max_bytes=4)
    except ValueError as exc:
        assert 'stream exceeded limit 4' in str(exc)
    else:
        raise AssertionError('expected source download byte limit failure')

    assert not target.exists()
    assert not list(tmp_path.glob('.*.part'))


def test_download_arxiv_source_blocks_declared_content_length(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / 'source-package'

    monkeypatch.setattr(
        'research_assistant.source.arxiv_source.urllib.request.urlopen',
        lambda *_args, **_kwargs: _FakeSourceResponse([b'abc'], content_length='5'),
    )

    try:
        download_arxiv_source('2401.00001', target, max_bytes=4)
    except ValueError as exc:
        assert 'content length 5 exceeds limit 4' in str(exc)
    else:
        raise AssertionError('expected source download declared-size failure')

    assert not target.exists()


def test_download_arxiv_source_blocks_redirect_domain(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / 'source-package'

    monkeypatch.setattr(
        'research_assistant.source.arxiv_source.urllib.request.urlopen',
        lambda *_args, **_kwargs: _FakeSourceResponse([b'abc'], final_url='https://example.com/e-print/2401.00001'),
    )

    try:
        download_arxiv_source('2401.00001', target)
    except ValueError as exc:
        assert 'redirect domain example.com is not allowed' in str(exc)
    else:
        raise AssertionError('expected source download redirect-domain failure')

    assert not target.exists()


def test_fetch_arxiv_structured_source_records_available_latex(monkeypatch, tmp_path: Path) -> None:
    def fake_download(arxiv_id: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_source_tarball())
        return destination

    monkeypatch.setattr('research_assistant.source.arxiv_source.download_arxiv_source', fake_download)

    record = fetch_arxiv_structured_source('2401.00001', root=tmp_path, paper_id='paper_source_first')

    assert record.status == 'available'
    assert record.primary_for_audit is True
    assert record.source_type == 'arxiv_latex'
    assert [section['title'] for section in record.sections] == ['Introduction', 'Method']
    assert record.equations[0]['labels'] == ['eq:target']
    assert record.theorem_like_blocks[0]['labels'] == ['thm:exact']
    assert Path(record.flattened_source_path).exists()
    stored = tmp_path / 'local_research' / 'papers' / 'source' / 'records' / 'paper_source_first.json'
    assert stored.exists()


def test_fetch_arxiv_structured_source_records_http_degradation(monkeypatch, tmp_path: Path) -> None:
    def fail_download(arxiv_id: str, destination: Path) -> Path:
        raise urllib.error.HTTPError('https://arxiv.org/e-print/2401.00001', 404, 'not found', None, None)

    monkeypatch.setattr('research_assistant.source.arxiv_source.download_arxiv_source', fail_download)

    record = fetch_arxiv_structured_source('2401.00001', root=tmp_path, paper_id='paper_missing_source')

    assert record.status == 'unavailable'
    assert record.primary_for_audit is False
    assert record.provenance['source_statuses'][0]['status'] == 'unavailable'
    assert record.provenance['source_statuses'][0]['code'] == 404
    assert record.limitations[0]['field'] == 'source'
    stored = tmp_path / 'local_research' / 'papers' / 'source' / 'records' / 'paper_missing_source.json'
    assert stored.exists()


def test_fetch_arxiv_structured_source_records_malformed_archive_failure(monkeypatch, tmp_path: Path) -> None:
    def fake_download(arxiv_id: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b'not latex')
        return destination

    monkeypatch.setattr('research_assistant.source.arxiv_source.download_arxiv_source', fake_download)

    record = fetch_arxiv_structured_source('2401.00001', root=tmp_path, paper_id='paper_bad_source')

    assert record.status == 'failed'
    assert record.primary_for_audit is False
    assert record.provenance['source_statuses'][0]['status'] == 'available'
    assert record.limitations[0]['field'] == 'latex_structure'
