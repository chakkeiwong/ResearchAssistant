from __future__ import annotations

import json

from research_assistant import cli


def test_papers_citing_command_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'papers_citing', lambda paper_id, limit=10: [{'paper_id': paper_id, 'limit': limit}])

    exit_code = cli.main(['papers-citing', '--paper-id', 'paper-123', '--limit', '2'])

    assert exit_code == 0
    captured = json.loads(capsys.readouterr().out)
    assert captured == [{'paper_id': 'paper-123', 'limit': 2}]


def test_papers_cited_by_command_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, 'papers_cited_by', lambda paper_id, limit=10: [{'paper_id': paper_id, 'limit': limit}])

    exit_code = cli.main(['papers-cited-by', '--paper-id', 'paper-456'])

    assert exit_code == 0
    captured = json.loads(capsys.readouterr().out)
    assert captured == [{'paper_id': 'paper-456', 'limit': 10}]


def test_citation_neighborhood_command_prints_source_statuses(monkeypatch, capsys) -> None:
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

    exit_code = cli.main(['citation-neighborhood', '--paper-id', 'paper-789'])

    assert exit_code == 0
    captured = json.loads(capsys.readouterr().out)
    assert captured['paper_id'] == 'paper-789'
    assert captured['status'] == 'empty'
    assert captured['source_statuses'][0]['endpoint'] == 'citations'
    assert captured['source_statuses'][0]['code'] == 429
