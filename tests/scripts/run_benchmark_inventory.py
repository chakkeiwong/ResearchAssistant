#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    bench = root / 'tests' / 'fixtures' / 'benchmark_papers'
    synthetic = sorted((bench / 'synthetic').glob('*.expected.json'))
    arxiv_pairs = sorted((bench / 'arxiv_pairs').glob('*.expected.json'))
    summary = {
        'synthetic_count': len(synthetic),
        'arxiv_pair_count': len(arxiv_pairs),
        'files': [str(p.relative_to(root)) for p in synthetic + arxiv_pairs],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
