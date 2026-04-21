from __future__ import annotations

from research_assistant.query import citation_graph


def test_related_papers_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(citation_graph, 'discover_papers', lambda topic: [])
    assert isinstance(citation_graph.related_papers('transport maps hmc'), list)
