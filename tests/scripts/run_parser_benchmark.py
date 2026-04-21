#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def load_expected(path: Path) -> dict:
    return json.loads(path.read_text())


def score_expected_record(data: dict) -> dict:
    return {
        'id': data['id'],
        'source_type': data['source_type'],
        'expected': {
            'title': data['title'],
            'authors': data['authors'],
            'abstract': data['abstract'],
            'section_headings': data.get('section_headings', []),
        },
        'parser_runs': [],
        'status': 'expected_record_only',
        'diagnostics': ['No compiled PDF is present for this fixture yet.'],
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    bench_dir = root / 'tests' / 'fixtures' / 'benchmark_papers' / 'synthetic'
    expected_files = sorted(bench_dir.glob('*.expected.json'))
    results = [score_expected_record(load_expected(exp)) for exp in expected_files]
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
