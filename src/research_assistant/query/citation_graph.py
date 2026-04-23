from __future__ import annotations

import urllib.error
import urllib.parse
from typing import Any

from research_assistant.query.discovery import SEMANTIC_SCHOLAR_FIELDS, _fetch_json, _normalize_semanticscholar_work, discover_papers


def _fetch_semanticscholar_citation_list(paper_id: str, endpoint: str, *, limit: int = 10) -> list[dict]:
    params = urllib.parse.urlencode({'fields': SEMANTIC_SCHOLAR_FIELDS, 'limit': limit})
    url = f'https://api.semanticscholar.org/graph/v1/paper/{urllib.parse.quote(paper_id, safe="")}/{endpoint}?{params}'
    try:
        data = _fetch_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    key = 'citingPaper' if endpoint == 'citations' else 'citedPaper'
    return [_normalize_semanticscholar_work(item[key]).to_dict() for item in data.get('data', []) if item.get(key)]


def papers_citing(paper_id: str, *, limit: int = 10) -> list[dict]:
    return _fetch_semanticscholar_citation_list(paper_id, 'citations', limit=limit)


def papers_cited_by(paper_id: str, *, limit: int = 10) -> list[dict]:
    return _fetch_semanticscholar_citation_list(paper_id, 'references', limit=limit)


def citation_neighborhood(paper_id: str, *, limit: int = 5) -> dict[str, Any]:
    try:
        citing = papers_citing(paper_id, limit=limit)
        cited = papers_cited_by(paper_id, limit=limit)
    except Exception:
        return {
            'paper_id': paper_id,
            'citing': [],
            'cited': [],
            'citing_count': 0,
            'cited_count': 0,
            'status': 'unavailable',
        }
    status = 'available' if citing or cited else 'empty'
    return {
        'paper_id': paper_id,
        'citing': citing,
        'cited': cited,
        'citing_count': len(citing),
        'cited_count': len(cited),
        'status': status,
    }


def related_papers(topic: str) -> list[dict]:
    return discover_papers(topic)
