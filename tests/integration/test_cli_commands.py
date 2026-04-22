from __future__ import annotations

import json
from pathlib import Path

from research_assistant import cli
from research_assistant.cli import main
from research_assistant.ingest.source_manifest import canonical_paper_id


def test_cli_find_empty_store(tmp_path: Path, capsys) -> None:
    root = tmp_path
    (root / 'local_research' / 'summaries').mkdir(parents=True)
    rc = main(['--root', str(root), 'find', '--query', 'nothing'])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ''


def test_cli_audit_claim_shape(capsys) -> None:
    rc = main(['audit-claim', '--claim', 'test claim', '--papers', 'p1'])
    captured = capsys.readouterr()
    assert rc == 0
    assert 'classification' in captured.out


def test_cli_ingest_palazzo_uses_parser_consensus(tmp_path: Path, capsys) -> None:
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


def test_cli_download_paper_downloads_first_open_access_match(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'discover_papers', lambda query, per_page=10: [
        {
            'source': 'semanticscholar',
            'title': 'Downloadable Paper',
            'open_access_pdf_url': 'https://example.com/paper.pdf',
        }
    ])
    monkeypatch.setattr(cli, 'download_to_inbox', lambda pdf_url, filename_hint, root=None: Path(root) / 'local_research' / 'inbox' / f'{filename_hint}.pdf')

    rc = main(['--root', str(tmp_path), 'download-paper', '--query', 'downloadable'])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload['downloaded'] is True
    assert payload['proposal']['proposed_name'] == 'downloadable_paper.pdf'
    assert payload['proposal']['schema_version'] == 1
    assert payload['proposal']['query'] == 'downloadable'
    proposal_path = Path(payload['proposal_path'])
    assert proposal_path.exists()
    persisted = json.loads(proposal_path.read_text())
    assert persisted['schema_version'] == 1
    assert persisted['query'] == 'downloadable'
    assert persisted['proposed_name'] == 'downloadable_paper.pdf'
    assert persisted['result']['open_access_pdf_url'] == 'https://example.com/paper.pdf'
