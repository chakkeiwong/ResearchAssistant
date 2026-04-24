from __future__ import annotations

import json
from pathlib import Path

from research_assistant import cli
from research_assistant.cli import main
from research_assistant.ingest import metadata_resolve
from research_assistant.ingest.parser_preflight import ParserPreflight
from research_assistant.ingest.source_manifest import canonical_paper_id
from research_assistant.schemas.parsed_document import ParsedDocument


def test_cli_find_empty_store(tmp_path: Path, capsys) -> None:
    root = tmp_path
    (root / 'local_research' / 'summaries').mkdir(parents=True)
    rc = main(['--root', str(root), 'find', '--query', 'nothing'])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ''


def test_cli_help_includes_review_inbox_export_and_citation_commands(capsys) -> None:
    try:
        main(['--help'])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert 'review-list' in captured.out
    assert 'review-show' in captured.out
    assert 'review-mark' in captured.out
    assert 'inbox-list' in captured.out
    assert 'inbox-show' in captured.out
    assert 'export-context' in captured.out
    assert 'citation-neighborhood' in captured.out


def test_cli_find_reports_review_status(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'authors': ['Berardino Palazzo'],
        'year': 2020,
        'abstract': '',
        'main_contribution': 'Credit transmission result',
        'curation_status': 'draft',
        'metadata_confidence': 'low',
        'identity_source': 'parser_consensus',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review', 'warnings': ['metadata confidence is low']},
        'requires_manual_review': True,
        'candidate_metadata_sources': {},
        'merge_notes': [],
        'provenance': {},
    }))

    rc = main(['--root', str(root), 'find', '--query', 'credit'])
    captured = capsys.readouterr()

    assert rc == 0
    assert 'paper_a\t2020\tneeds_review\tCredit Risk and the Transmission of Interest Rate Shocks' in captured.out


def test_cli_find_applies_review_author_and_year_filters(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'authors': ['Berardino Palazzo'],
        'year': 2020,
        'abstract': '',
        'main_contribution': 'Credit transmission result',
        'review_status': 'approved',
    }))
    (summaries / 'paper_b.json').write_text(json.dumps({
        'id': 'paper_b',
        'title': 'Another Credit Paper',
        'authors': ['Alice Example'],
        'year': 2021,
        'abstract': '',
        'main_contribution': 'Credit follow-up',
        'review_status': 'needs_review',
    }))

    rc = main([
        '--root', str(root), 'find', '--query', 'credit', '--review-status', 'approved', '--author', 'palazzo', '--year', '2020'
    ])
    captured = capsys.readouterr()

    assert rc == 0
    assert 'paper_a\t2020\tapproved\tCredit Risk and the Transmission of Interest Rate Shocks' in captured.out
    assert 'paper_b' not in captured.out


def test_cli_show_foregrounds_review_and_identity_validation(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    metadata_dir = root / 'local_research' / 'metadata'
    extracted_dir = root / 'local_research' / 'papers' / 'extracted'
    summaries.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    extracted_dir.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Approved Paper',
        'authors': ['Alice Example'],
        'year': 2020,
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
        'review_summary': {'status': 'approved', 'warnings': []},
        'requires_manual_review': False,
        'provenance': {'title': 'parser_consensus'},
    }))
    (metadata_dir / 'paper_a.json').write_text(json.dumps({
        'identity_validation': {'status': 'validated', 'requires_manual_review': False}
    }))

    rc = main(['--root', str(root), 'show', '--paper-id', 'paper_a'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['review']['review_status'] == 'approved'
    assert payload['review']['requires_manual_review'] is False
    assert payload['review']['provenance']['title'] == 'parser_consensus'
    assert payload['review']['identity_validation']['status'] == 'validated'
    assert payload['summary']['id'] == 'paper_a'
    assert payload['extraction']['extracted_text_available'] is False
    assert payload['extraction']['consensus_section_headings'] == []
    assert payload['extraction']['parser_reconciliation']['parse_confidence'] == 'low'
    assert payload['extraction']['limitations'][0]['field'] == 'equations'
    assert payload['extraction']['limitations'][1]['field'] == 'citations'
    assert payload['technical_audit']['transport_definition'] == ''
    assert payload['technical_audit']['claimed_results'] == []


def test_cli_show_surfaces_extraction_artifacts_and_parser_reconciliation(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    metadata_dir = root / 'local_research' / 'metadata'
    extracted_dir = root / 'local_research' / 'papers' / 'extracted'
    summaries.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    extracted_dir.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Parser First Paper',
        'authors': ['Alice Example'],
        'year': 2024,
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review', 'warnings': ['parser confidence is low']},
        'requires_manual_review': True,
        'provenance': {'title': 'parser_consensus'},
    }))
    (metadata_dir / 'paper_a.json').write_text(json.dumps({
        'identity_validation': {'status': 'validated', 'requires_manual_review': False},
        'parser_hints': {
            'consensus_section_headings': ['Introduction', 'Method', 'Experiments'],
            'parse_confidence': 'medium',
            'requires_manual_review': True,
            'parser_agreement': {'title': 'strong', 'authors': 'partial'},
            'disagreements': ['author list differs across parsers'],
            'parser_outputs': [
                {
                    'parser_name': 'pdftotext',
                    'parser_version': '1.0',
                    'parse_status': 'partial',
                    'section_headings': ['Introduction'],
                    'diagnostics': {'available': True},
                    'body_text': 'text',
                    'capabilities': {
                        'section_headings': 'partial',
                        'equations': 'unreliable',
                        'citations': 'unreliable',
                    },
                },
                {
                    'parser_name': 'marker',
                    'parser_version': '0.1',
                    'parse_status': 'success',
                    'section_headings': ['Introduction', 'Method'],
                    'diagnostics': {'available': True},
                    'body_markdown': '# Introduction',
                    'capabilities': {
                        'section_headings': 'partial',
                        'equations': 'unreliable',
                        'citations': 'unreliable',
                    },
                },
            ],
        },
    }))
    extracted_path = extracted_dir / 'paper_a.txt'
    extracted_path.write_text('Extracted text')

    rc = main(['--root', str(root), 'show', '--paper-id', 'paper_a'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['extraction']['extracted_text_available'] is True
    assert payload['extraction']['extracted_text_path'] == str(extracted_path)
    assert payload['extraction']['consensus_section_headings'] == ['Introduction', 'Method', 'Experiments']
    assert payload['extraction']['parser_reconciliation']['parse_confidence'] == 'medium'
    assert payload['extraction']['parser_reconciliation']['requires_manual_review'] is True
    assert payload['extraction']['parser_reconciliation']['parser_agreement']['title'] == 'strong'
    assert payload['extraction']['parser_reconciliation']['disagreements'] == ['author list differs across parsers']
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][0]['parser_name'] == 'pdftotext'
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][0]['capabilities']['equations'] == 'unreliable'
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][1]['parse_status'] == 'success'
    assert payload['extraction']['parser_reconciliation']['parser_outputs_used'][1]['capabilities']['citations'] == 'unreliable'
    assert payload['extraction']['warnings'] == ['author list differs across parsers']
    assert payload['extraction']['limitations'][0]['status'] == 'unreliable'
    assert payload['extraction']['limitations'][1]['status'] == 'unreliable'
    assert payload['technical_audit']['relevant_sections'] == []
    assert payload['technical_audit']['assumptions_for_reuse'] == []


def test_cli_review_commands_update_status(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Credit Risk and the Transmission of Interest Rate Shocks',
        'authors': ['Berardino Palazzo'],
        'year': 2020,
        'abstract': '',
        'main_contribution': 'Credit transmission result',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review'},
        'requires_manual_review': True,
        'candidate_metadata_sources': {},
        'merge_notes': ['manual review recommended'],
        'provenance': {'title': 'parser_consensus'},
    }))

    rc = main(['--root', str(root), 'review-list'])
    listed = capsys.readouterr()
    assert rc == 0
    assert 'paper_a\t2020\tneeds_review' in listed.out

    rc = main(['--root', str(root), 'review-show', '--paper-id', 'paper_a'])
    shown = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown['provenance']['title'] == 'parser_consensus'
    assert shown['summary']['technical_audit']['transport_definition'] == ''
    assert shown['summary']['technical_audit']['claimed_results'] == []

    rc = main(['--root', str(root), 'review-mark', '--paper-id', 'paper_a', '--status', 'approved'])
    marked = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert marked['review_status'] == 'approved'
    assert marked['requires_manual_review'] is False


def test_cli_export_context_writes_filtered_payload(tmp_path: Path, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Approved Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    (summaries / 'paper_b.json').write_text(json.dumps({
        'id': 'paper_b',
        'title': 'Needs Review Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'needs_review',
    }))
    output = root / 'approved_context.json'

    rc = main(['--root', str(root), 'export-context', '--output', str(output), '--review-status', 'approved'])
    captured = capsys.readouterr()
    payload = json.loads(output.read_text())

    assert rc == 0
    assert captured.out.strip() == str(output)
    assert [paper['id'] for paper in payload['papers']] == ['paper_a']
    assert payload['papers'][0]['technical_audit']['transport_definition'] == ''
    assert payload['papers'][0]['technical_audit']['relevant_sections'] == []


def test_cli_ingest_palazzo_uses_parser_consensus(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(metadata_resolve, '_fetch_json', lambda url: {'results': [], 'message': {'items': []}})
    monkeypatch.setattr(metadata_resolve, 'choose_best_semanticscholar_result', lambda *args, **kwargs: ({}, []))

    pdf = Path('/home/chakwong/research-assistant/local_research/papers/raw/paper_credit_risk_and_the_transmission_of_interest_rate_shocks_palazzo_20_7e82ec19.pdf')
    query = 'Credit Risk and the Transmission of Interest Rate Shocks Palazzo'
    rc = main(['--root', str(tmp_path), 'ingest', '--pdf', str(pdf), '--query', query])
    captured = capsys.readouterr()
    paper_id = canonical_paper_id(str(pdf))

    assert rc == 0
    assert captured.out.strip() == paper_id

    metadata = json.loads((tmp_path / 'local_research' / 'metadata' / f'{paper_id}.json').read_text())
    summary = json.loads((tmp_path / 'local_research' / 'summaries' / f'{paper_id}.json').read_text())

    assert metadata['parser_hints']['consensus_title'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert metadata['parser_hints']['consensus_authors'] == ['Berardino Palazzo', 'Ram Yamarthy']
    assert summary['title'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert summary['authors'] == ['Berardino Palazzo', 'Ram Yamarthy']
    assert summary['identity_source'] == 'parser_consensus'
    assert summary['requires_manual_review'] is True


def test_cli_parse_pdf_reports_parser_capability_limits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'parse_with_all', lambda pdf_path: [
        ParsedDocument(
            parser_name='marker',
            parser_version='0.1',
            title_candidates=['Parser Capability Paper'],
            authors=['Alice Example'],
            section_headings=['Introduction'],
            body_markdown='Parser Capability Paper\nAlice Example',
            parse_status='ok',
        )
    ])

    rc = main(['parse-pdf', '--pdf', '/tmp/example.pdf'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['parser_outputs'][0]['parser_name'] == 'marker'
    assert payload['parser_outputs'][0]['capabilities']['section_headings'] == 'partial'
    assert payload['parser_outputs'][0]['capabilities']['equations'] == 'unreliable'
    assert payload['parser_outputs'][0]['capabilities']['citations'] == 'unreliable'


def test_cli_parser_preflight_reports_capability_limits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'preflight_all', lambda: [
        ParserPreflight(
            'pdftotext',
            False,
            'unavailable',
            ['pdftotext not found in PATH'],
            {
                'command': 'pdftotext',
                'capabilities': {
                    'section_headings': 'partial',
                    'equations': 'unreliable',
                    'citations': 'unreliable',
                },
            },
        )
    ])

    rc = main(['parser-preflight'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload[0]['parser_name'] == 'pdftotext'
    assert payload[0]['details']['capabilities']['section_headings'] == 'partial'
    assert payload[0]['details']['capabilities']['equations'] == 'unreliable'
    assert payload[0]['details']['capabilities']['citations'] == 'unreliable'


    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'empty',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })

    rc = main(['discover', '--query', 'transport maps'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['status'] == 'empty'
    assert payload['results'] == []
    assert payload['source_statuses'][0]['source'] == 'semanticscholar'
    assert payload['source_statuses'][0]['code'] == 429


def test_cli_citation_neighborhood_reports_ranked_summary(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'available',
        'citing': [],
        'cited': [],
        'citing_count': 1,
        'cited_count': 1,
        'summary': {
            'top_citing': [
                {
                    'source_id': 'citing-1',
                    'title': 'Useful Citing Paper',
                    'authors': ['Alice Example'],
                    'year': 2025,
                    'citation_count': 7,
                    'influential_citation_count': 1,
                    'open_access_pdf_url': 'https://example.com/citing.pdf',
                    'ranking_score': 20,
                }
            ],
            'top_cited': [
                {
                    'source_id': 'cited-1',
                    'title': 'Useful Cited Paper',
                    'authors': ['Bob Example'],
                    'year': 2020,
                    'citation_count': 12,
                    'influential_citation_count': 3,
                    'open_access_pdf_url': None,
                    'ranking_score': 21,
                }
            ],
        },
    })

    rc = main(['citation-neighborhood', '--paper-id', 'seed-paper'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['paper_id'] == 'seed-paper'
    assert payload['summary']['top_citing'][0]['source_id'] == 'citing-1'
    assert payload['summary']['top_cited'][0]['source_id'] == 'cited-1'

    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Downloadable Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'available',
        'results': [
            {
                'source': 'semanticscholar',
                'title': 'Downloadable Paper',
                'open_access_pdf_url': 'https://example.com/paper.pdf',
            }
        ],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'available', 'result_count': 1},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })
    monkeypatch.setattr(cli, 'download_to_inbox', lambda pdf_url, filename_hint, root=None: Path(root) / 'local_research' / 'inbox' / f'{filename_hint}.pdf')

    rc = main(['--root', str(tmp_path), 'download-paper', '--query', 'downloadable'])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload['downloaded'] is True
    assert payload['discovery']['status'] == 'available'
    assert payload['proposal']['proposed_name'] == 'downloadable_paper.pdf'
    assert payload['proposal']['schema_version'] == 1
    assert payload['proposal']['query'] == 'downloadable'
    assert payload['proposal']['duplicate_status'] == 'possible_duplicate'
    assert payload['proposal']['duplicate_candidates'][0]['paper_id'] == 'paper_a'
    proposal_path = Path(payload['proposal_path'])
    assert proposal_path.exists()
    persisted = json.loads(proposal_path.read_text())
    assert persisted['schema_version'] == 1
    assert persisted['query'] == 'downloadable'
    assert persisted['proposed_name'] == 'downloadable_paper.pdf'
    assert persisted['duplicate_status'] == 'possible_duplicate'
    assert persisted['result']['open_access_pdf_url'] == 'https://example.com/paper.pdf'


def test_cli_download_paper_reports_discovery_unavailable(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'unavailable',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'unavailable', 'result_count': 0},
        ],
    })

    rc = main(['download-paper', '--query', 'transport maps'])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload['downloaded'] is False
    assert payload['reason'] == 'discovery unavailable'
    assert payload['discovery']['status'] == 'unavailable'
    assert payload['discovery']['source_statuses'][0]['code'] == 429


def test_cli_inbox_commands_show_persisted_proposals(tmp_path: Path, monkeypatch, capsys) -> None:
    summaries = tmp_path / 'local_research' / 'summaries'
    summaries.mkdir(parents=True)
    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Downloadable Paper',
        'authors': [],
        'abstract': '',
        'main_contribution': '',
        'review_status': 'approved',
    }))
    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'available',
        'results': [
            {
                'source': 'semanticscholar',
                'title': 'Downloadable Paper',
                'open_access_pdf_url': 'https://example.com/paper.pdf',
            }
        ],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'available', 'result_count': 1},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })
    monkeypatch.setattr(cli, 'download_to_inbox', lambda pdf_url, filename_hint, root=None: Path(root) / 'local_research' / 'inbox' / f'{filename_hint}.pdf')
    main(['--root', str(tmp_path), 'download-paper', '--query', 'downloadable'])
    capsys.readouterr()

    rc = main(['--root', str(tmp_path), 'inbox-list', '--duplicate-status', 'unique'])
    listed = capsys.readouterr()
    assert rc == 0
    assert listed.out == ''

    rc = main(['--root', str(tmp_path), 'inbox-list', '--duplicate-status', 'possible_duplicate'])
    listed = capsys.readouterr()
    assert rc == 0
    assert 'downloadable_paper.pdf	possible_duplicate	1	semanticscholar	Downloadable Paper' in listed.out

    rc = main(['--root', str(tmp_path), 'inbox-show', '--proposed-name', 'downloadable_paper.pdf'])
    shown = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert shown['query'] == 'downloadable'
    assert shown['proposed_name'] == 'downloadable_paper.pdf'
    assert shown['duplicate_status'] == 'possible_duplicate'
    assert shown['duplicate_candidates'][0]['paper_id'] == 'paper_a'
    assert shown['review_summary']['duplicate_status'] == 'possible_duplicate'
    assert shown['review_summary']['duplicate_count'] == 1
    assert shown['review_summary']['matched_paper_ids'] == ['paper_a']


def test_cli_audit_workflow_stays_usable_when_citation_enrichment_is_unavailable(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path
    summaries = root / 'local_research' / 'summaries'
    metadata_dir = root / 'local_research' / 'metadata'
    extracted_dir = root / 'local_research' / 'papers' / 'extracted'
    summaries.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    extracted_dir.mkdir(parents=True)

    (summaries / 'paper_a.json').write_text(json.dumps({
        'id': 'paper_a',
        'title': 'Audit Seed Paper',
        'authors': ['Alice Example'],
        'year': 2024,
        'abstract': '',
        'main_contribution': 'A contribution worth checking carefully.',
        'review_status': 'needs_review',
        'review_summary': {'status': 'needs_review', 'warnings': ['parser confidence is low']},
        'requires_manual_review': True,
        'provenance': {'title': 'parser_consensus'},
    }))
    (metadata_dir / 'paper_a.json').write_text(json.dumps({
        'identity_validation': {
            'status': 'validated',
            'requires_manual_review': False,
            'citation_neighborhood': {'status': 'unavailable'},
        },
        'parser_hints': {
            'consensus_section_headings': ['Introduction', 'Model', 'Conclusion'],
            'parse_confidence': 'medium',
            'requires_manual_review': True,
            'parser_agreement': {'title': 'strong'},
            'disagreements': ['affiliation lines differ across parsers'],
            'parser_outputs': [
                {
                    'parser_name': 'pdftotext',
                    'parser_version': '1.0',
                    'parse_status': 'partial',
                    'section_headings': ['Introduction', 'Model'],
                    'diagnostics': {'available': True},
                }
            ],
        },
    }))
    (extracted_dir / 'paper_a.txt').write_text('Technical text for audit workflow')

    rc = main(['--root', str(root), 'show', '--paper-id', 'paper_a'])
    show_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert show_payload['review']['identity_validation']['citation_neighborhood']['status'] == 'unavailable'
    assert show_payload['extraction']['extracted_text_available'] is True
    assert show_payload['extraction']['parser_reconciliation']['disagreements'] == ['affiliation lines differ across parsers']

    monkeypatch.setattr(cli, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'empty',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'source_statuses': [
            {'endpoint': 'citations', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'endpoint': 'references', 'status': 'available', 'result_count': 0},
        ],
        'summary': {'top_citing': [], 'top_cited': []},
    })
    rc = main(['--root', str(root), 'citation-neighborhood', '--paper-id', 'paper_a'])
    citation_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert citation_payload['status'] == 'empty'
    assert citation_payload['source_statuses'][0]['endpoint'] == 'citations'
    assert citation_payload['source_statuses'][0]['code'] == 429
    assert citation_payload['summary']['top_citing'] == []
    assert citation_payload['summary']['top_cited'] == []

    monkeypatch.setattr(cli, 'discover_papers_with_status', lambda query, per_page=10: {
        'query': query,
        'status': 'empty',
        'results': [],
        'source_statuses': [
            {'source': 'semanticscholar', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'source': 'openalex', 'status': 'available', 'result_count': 0},
        ],
    })
    rc = main(['--root', str(root), 'download-paper', '--query', 'audit seed paper'])
    download_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert download_payload['downloaded'] is False
    assert download_payload['reason'] == 'no open access pdf found'
    assert download_payload['discovery']['status'] == 'empty'
    assert download_payload['discovery']['source_statuses'][0]['code'] == 429

    rc = main(['--root', str(root), 'review-mark', '--paper-id', 'paper_a', '--status', 'approved'])
    review_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert review_payload['review_status'] == 'approved'
    assert review_payload['requires_manual_review'] is False

    export_path = root / 'approved_context.json'
    rc = main(['--root', str(root), 'export-context', '--output', str(export_path), '--review-status', 'approved'])
    exported = json.loads(export_path.read_text())


def test_cli_local_ingest_audit_scenario_preserves_trust_checkpoints(tmp_path: Path, monkeypatch, capsys) -> None:
    pdf = tmp_path / 'neural_transport_hmc.pdf'
    pdf.write_bytes(b'%PDF-1.4 synthetic')
    paper_id = canonical_paper_id(str(pdf))

    monkeypatch.setattr(cli, 'extract_pdf_text', lambda raw_path: 'Neural Transport HMC\nAlice Example\n1 Introduction\n2 Method')
    monkeypatch.setattr(cli, 'parse_with_all', lambda raw_path: [
        ParsedDocument(
            parser_name='marker',
            parser_version='0.1',
            title_candidates=['Neural Transport HMC'],
            authors=['Alice Example'],
            section_headings=['Introduction', 'Method'],
            body_markdown='Neural Transport HMC\nAlice Example\n# Introduction\n# Method',
            parse_status='ok',
        ),
        ParsedDocument(
            parser_name='pdftotext',
            parser_version='1.0',
            title_candidates=['Neural Transport HMC'],
            authors=['Alice Example'],
            section_headings=['Introduction'],
            body_text='Neural Transport HMC\nAlice Example\nIntroduction',
            parse_status='ok',
        ),
    ])

    def fake_resolve_metadata(query, *, arxiv_id=None, extracted_text='', filename_hints=None, parser_hints=None):
        return {
            'title': parser_hints['consensus_title'],
            'authors': parser_hints['consensus_authors'],
            'abstract': 'Synthetic abstract for a local-first audit scenario.',
            'year': 2024,
            'parser_hints': parser_hints,
            'provenance': {'title': 'parser_consensus', 'authors': 'parser_consensus'},
        }

    monkeypatch.setattr(cli, 'resolve_metadata', fake_resolve_metadata)
    monkeypatch.setattr(cli, 'validate_identity', lambda metadata: {'status': 'validated', 'requires_manual_review': False})

    rc = main(['--root', str(tmp_path), 'ingest', '--pdf', str(pdf), '--query', 'Neural Transport HMC'])
    assert rc == 0
    assert capsys.readouterr().out.strip() == paper_id

    rc = main(['--root', str(tmp_path), 'show', '--paper-id', paper_id])
    show_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert show_payload['extraction']['extracted_text_available'] is True
    assert show_payload['extraction']['consensus_section_headings'] == ['Introduction']
    assert show_payload['extraction']['parser_reconciliation']['parse_confidence'] == 'medium'
    assert show_payload['extraction']['parser_reconciliation']['parser_outputs_used'][0]['capabilities']['equations'] == 'unreliable'
    assert show_payload['technical_audit']['transport_definition'] == ''

    summary_path = tmp_path / 'local_research' / 'summaries' / f'{paper_id}.json'
    summary = json.loads(summary_path.read_text())
    summary['technical_audit']['transport_definition'] = 'Map z to theta before HMC proposal generation.'
    summary['technical_audit']['objective'] = 'Improve posterior geometry without changing the exact MH target.'
    summary['technical_audit']['relevant_sections'] = ['Method']
    summary_path.write_text(json.dumps(summary))

    monkeypatch.setattr(cli, 'citation_neighborhood', lambda paper_id, limit=5: {
        'paper_id': paper_id,
        'status': 'unavailable',
        'citing': [],
        'cited': [],
        'citing_count': 0,
        'cited_count': 0,
        'source_statuses': [
            {'endpoint': 'citations', 'status': 'unavailable', 'code': 429, 'result_count': 0},
            {'endpoint': 'references', 'status': 'unavailable', 'code': 429, 'result_count': 0},
        ],
        'summary': {'top_citing': [], 'top_cited': []},
    })
    rc = main(['--root', str(tmp_path), 'citation-neighborhood', '--paper-id', paper_id])
    citation_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert citation_payload['status'] == 'unavailable'
    assert [row['status'] for row in citation_payload['source_statuses']] == ['unavailable', 'unavailable']

    rc = main(['--root', str(tmp_path), 'review-mark', '--paper-id', paper_id, '--status', 'approved'])
    review_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert review_payload['review_status'] == 'approved'

    export_path = tmp_path / 'approved_context.json'
    rc = main(['--root', str(tmp_path), 'export-context', '--output', str(export_path), '--review-status', 'approved'])
    exported = json.loads(export_path.read_text())
    assert rc == 0
    assert exported['papers'][0]['id'] == paper_id
    assert exported['papers'][0]['technical_audit']['transport_definition'] == 'Map z to theta before HMC proposal generation.'
    assert exported['papers'][0]['technical_audit']['objective'] == 'Improve posterior geometry without changing the exact MH target.'
    assert exported['papers'][0]['technical_audit']['relevant_sections'] == ['Method']
