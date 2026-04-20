from __future__ import annotations

from research_assistant.query.citation_graph import related_papers


def test_related_papers_returns_list() -> None:
    # This is a shape-level test. Network-backed ranking is validated manually.
    assert isinstance(related_papers('transport maps hmc'), list)
