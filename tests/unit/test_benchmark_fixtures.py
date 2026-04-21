from __future__ import annotations

import json
from pathlib import Path


def test_synthetic_benchmark_fixture_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = root / 'fixtures' / 'benchmark_papers' / 'synthetic' / 'synthetic_transport_simple.expected.json'
    assert expected.exists()
    data = json.loads(expected.read_text())
    assert data['title'] == 'A Simple Test of Transport Maps for Posterior Geometry'
