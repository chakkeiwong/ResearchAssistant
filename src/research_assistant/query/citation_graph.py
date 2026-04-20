from __future__ import annotations

from research_assistant.query.discovery import discover_papers


def papers_citing(paper_id: str) -> list[dict]:
    # Placeholder until a primary discovery backend is wired for citation traversal.
    return []


def papers_cited_by(paper_id: str) -> list[dict]:
    # Placeholder until a primary discovery backend is wired for citation traversal.
    return []


def related_papers(topic: str) -> list[dict]:
    return discover_papers(topic)
