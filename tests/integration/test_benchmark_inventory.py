from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

from research_assistant.schemas.parsed_document import ParsedDocument

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_SCRIPT = ROOT / 'tests' / 'scripts' / 'run_parser_benchmark.py'
SPEC = importlib.util.spec_from_file_location('run_parser_benchmark', BENCHMARK_SCRIPT)
assert SPEC and SPEC.loader
run_parser_benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_parser_benchmark)


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


def test_parser_benchmark_scores_all_compiled_synthetic_fixtures() -> None:
    bench = Path(__file__).resolve().parents[1] / 'fixtures' / 'benchmark_papers' / 'synthetic'
    for expected_path in sorted(bench.glob('*.expected.json')):
        row = run_parser_benchmark.score_expected_record(run_parser_benchmark.load_expected(expected_path), expected_path)
        assert row['status'] == 'scored'
        assert row['pdf'].endswith(f"{expected_path.name.replace('.expected.json', '.pdf')}")
        assert len(row['parser_runs']) >= 1
        assert 'reconciled' in row
        assert 'scores' in row['reconciled']
        assert row['diagnostics'] == []


def test_parser_benchmark_scores_real_fixture_when_pdf_present() -> None:
    expected_path = Path(__file__).resolve().parents[1] / 'fixtures' / 'benchmark_papers' / 'synthetic' / 'synthetic_transport_simple.expected.json'
    row = run_parser_benchmark.score_expected_record(run_parser_benchmark.load_expected(expected_path), expected_path)
    assert row['status'] == 'scored'
    assert row['pdf'] == 'tests/fixtures/benchmark_papers/synthetic/synthetic_transport_simple.pdf'
    assert len(row['parser_runs']) >= 1
    assert 'reconciled' in row
    assert 'scores' in row['reconciled']
    assert row['diagnostics'] == []


def test_parser_benchmark_scores_parser_output_fields() -> None:
    expected = {
        'title': 'A Simple Test of Transport Maps for Posterior Geometry',
        'authors': ['Alice Example', 'Bob Example'],
        'abstract': 'Synthetic abstract',
        'section_headings': ['Introduction', 'Method', 'Conclusion'],
    }
    parsed = ParsedDocument(
        parser_name='fixture-parser',
        title_candidates=['A Simple Test of Transport Maps for Posterior Geometry'],
        authors=['Alice Example'],
        abstract='Synthetic abstract',
        section_headings=['Introduction', 'Conclusion'],
        parse_status='ok',
    )

    scores = run_parser_benchmark.score_parser_output(expected, parsed)

    assert scores['title']['exact_normalized_match'] is True
    assert scores['authors']['matched'] == 1
    assert scores['authors']['expected'] == 2
    assert scores['section_headings']['matched'] == 2
    assert scores['section_headings']['expected'] == 3
    assert scores['abstract_present'] is True


def test_benchmark_inventory_includes_long_title_and_footnote_fixtures() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ['python', str(root / 'tests' / 'scripts' / 'run_parser_benchmark.py')],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(result.stdout)
    ids = {row['id'] for row in rows}
    assert 'synthetic_long_title' in ids
    assert 'synthetic_author_footnotes' in ids
