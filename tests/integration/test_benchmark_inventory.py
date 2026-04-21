from __future__ import annotations

import json
from pathlib import Path
import subprocess


def test_benchmark_inventory_script_inputs_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    synthetic = root / 'fixtures' / 'benchmark_papers' / 'synthetic' / 'synthetic_transport_simple.expected.json'
    assert synthetic.exists()
    data = json.loads(synthetic.read_text())
    assert data['authors'] == ['Alice Example', 'Bob Example']


def test_parser_benchmark_script_reports_expected_fields() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ['python', str(root / 'tests' / 'scripts' / 'run_parser_benchmark.py')],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(result.stdout)
    assert len(rows) >= 3
    first = rows[0]
    assert 'expected' in first
    assert 'parser_runs' in first
    assert 'status' in first
