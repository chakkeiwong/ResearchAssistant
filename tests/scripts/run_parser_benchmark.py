#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from research_assistant.ingest.metadata_resolve import normalize_title, title_similarity
from research_assistant.ingest.parser_orchestrator import parse_with_all, reconcile_parsed_documents
from research_assistant.schemas.parsed_document import ParsedDocument, ReconciledDocument


def load_expected(path: Path) -> dict:
    return json.loads(path.read_text())


def _expected_fields(data: dict) -> dict[str, Any]:
    return {
        'title': data['title'],
        'authors': data['authors'],
        'abstract': data['abstract'],
        'section_headings': data.get('section_headings', []),
    }


def _normalize_name(name: str) -> str:
    return normalize_title(name)


def _overlap_score(expected: list[str], actual: list[str]) -> dict[str, Any]:
    expected_norm = {_normalize_name(item) for item in expected if _normalize_name(item)}
    actual_norm = {_normalize_name(item) for item in actual if _normalize_name(item)}
    matched = sorted(expected_norm & actual_norm)
    total = len(expected_norm)
    return {
        'matched': len(matched),
        'expected': total,
        'score': len(matched) / total if total else 1.0,
        'missing': sorted(expected_norm - actual_norm),
    }


def _best_title_score(expected_title: str, title_candidates: list[str]) -> dict[str, Any]:
    if not title_candidates:
        return {'score': 0.0, 'best_candidate': '', 'exact_normalized_match': False}
    scored = [(title_similarity(expected_title, candidate), candidate) for candidate in title_candidates]
    scored.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_candidate = scored[0]
    return {
        'score': best_score,
        'best_candidate': best_candidate,
        'exact_normalized_match': normalize_title(expected_title) == normalize_title(best_candidate),
    }


def score_parser_output(expected: dict, parsed: ParsedDocument) -> dict[str, Any]:
    title_candidates = list(parsed.title_candidates)
    if parsed.diagnostics.get('derived_title_candidates'):
        title_candidates.extend(parsed.diagnostics['derived_title_candidates'])
    return {
        'title': _best_title_score(expected['title'], title_candidates),
        'authors': _overlap_score(expected['authors'], parsed.authors),
        'section_headings': _overlap_score(expected.get('section_headings', []), parsed.section_headings),
        'abstract_present': bool(parsed.abstract.strip()),
    }


def score_reconciled_output(expected: dict, reconciled: ReconciledDocument) -> dict[str, Any]:
    title_candidates = [reconciled.consensus_title] if reconciled.consensus_title else []
    return {
        'title': _best_title_score(expected['title'], title_candidates),
        'authors': _overlap_score(expected['authors'], reconciled.consensus_authors),
        'section_headings': _overlap_score(expected.get('section_headings', []), reconciled.consensus_section_headings),
        'abstract_present': bool((reconciled.consensus_abstract or '').strip()),
    }


def _summarize_parser_output(expected: dict, parsed: ParsedDocument) -> dict[str, Any]:
    return {
        'parser_name': parsed.parser_name,
        'parser_version': parsed.parser_version,
        'parse_status': parsed.parse_status,
        'title_candidates': parsed.title_candidates,
        'authors': parsed.authors,
        'abstract_present': bool(parsed.abstract.strip()),
        'section_headings': parsed.section_headings,
        'scores': score_parser_output(expected, parsed),
        'diagnostics': parsed.diagnostics,
    }


def score_expected_record(data: dict, fixture_path: Path | None = None) -> dict:
    expected = _expected_fields(data)
    row = {
        'id': data['id'],
        'source_type': data['source_type'],
        'expected': expected,
        'parser_runs': [],
        'status': 'expected_record_only',
        'diagnostics': ['No compiled PDF is present for this fixture yet.'],
    }
    if fixture_path is None:
        return row

    pdf_path = fixture_path.parent / fixture_path.name.replace('.expected.json', '.pdf')
    if not pdf_path.exists():
        return row

    parser_outputs = parse_with_all(pdf_path)
    reconciled = reconcile_parsed_documents(parser_outputs)
    row.update({
        'pdf': str(pdf_path.relative_to(ROOT)),
        'parser_runs': [_summarize_parser_output(expected, parsed) for parsed in parser_outputs],
        'reconciled': {
            'consensus_title': reconciled.consensus_title,
            'consensus_authors': reconciled.consensus_authors,
            'consensus_section_headings': reconciled.consensus_section_headings,
            'consensus_abstract_present': bool((reconciled.consensus_abstract or '').strip()),
            'parse_confidence': reconciled.parse_confidence,
            'requires_manual_review': reconciled.requires_manual_review,
            'parser_agreement': reconciled.parser_agreement,
            'disagreements': reconciled.disagreements,
            'scores': score_reconciled_output(expected, reconciled),
        },
        'status': 'scored',
        'diagnostics': [],
    })
    return row


def main() -> int:
    bench_dir = ROOT / 'tests' / 'fixtures' / 'benchmark_papers' / 'synthetic'
    expected_files = sorted(bench_dir.glob('*.expected.json'))
    results = [score_expected_record(load_expected(exp), exp) for exp in expected_files]
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
