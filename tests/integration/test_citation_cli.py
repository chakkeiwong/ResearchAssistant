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
