from __future__ import annotations

import json
from pathlib import Path

REQUIRED_FIELDS = {
    'id',
    'source_type',
    'title',
    'authors',
    'year',
    'abstract',
    'section_headings',
}


def test_all_synthetic_expected_files_have_required_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    bench = root / 'fixtures' / 'benchmark_papers' / 'synthetic'
    expected_files = list(bench.glob('*.expected.json'))
    assert len(expected_files) >= 3
    for exp in expected_files:
        data = json.loads(exp.read_text())
        assert REQUIRED_FIELDS <= data.keys()
        assert data['source_type'] == 'synthetic_latex'
        assert isinstance(data['title'], str) and data['title'].strip()
        assert isinstance(data['authors'], list)
        assert len(data['authors']) >= 1
        assert all(isinstance(author, str) and author.strip() for author in data['authors'])
        assert isinstance(data['year'], int)
        assert isinstance(data['abstract'], str) and data['abstract'].strip()
        assert isinstance(data['section_headings'], list)
