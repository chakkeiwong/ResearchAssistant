from __future__ import annotations

import io
import tarfile
from pathlib import Path

from research_assistant.source.arxiv_source import fetch_arxiv_structured_source, unpack_arxiv_source


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'latex_sources' / 'multi_file'


def _source_tarball() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for path in sorted(FIXTURE.rglob('*')):
            if path.is_file():
                archive.add(path, arcname=str(path.relative_to(FIXTURE)))
    return buffer.getvalue()


def test_unpack_arxiv_source_handles_tarball(tmp_path: Path) -> None:
    package = tmp_path / 'source-package'
    package.write_bytes(_source_tarball())
    unpack_dir = tmp_path / 'unpacked'

    diagnostics = unpack_arxiv_source(package, unpack_dir)

    assert (unpack_dir / 'main.tex').exists()
    assert (unpack_dir / 'sections' / 'method.tex').exists()
    assert 'main.tex' in diagnostics['unpacked_files']


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
