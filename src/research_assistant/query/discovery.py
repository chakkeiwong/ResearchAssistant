from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from research_assistant.schemas.discovery_result import DiscoveryResult


SEMANTIC_SCHOLAR_FIELDS = ','.join([
    'title',
    'authors',
    'year',
    'abstract',
    'citationCount',
    'influentialCitationCount',
    'externalIds',
    'openAccessPdf',
    'url',
])


def _fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def _normalize_semanticscholar_work(work: dict[str, Any]) -> DiscoveryResult:
    external_ids = work.get('externalIds') or {}
    open_access_pdf = work.get('openAccessPdf') or {}
    return DiscoveryResult(
        source='semanticscholar',
        source_id=work.get('paperId'),
        title=work.get('title'),
        authors=[a.get('name', '') for a in work.get('authors', []) if a.get('name')],
        year=work.get('year'),
        doi=external_ids.get('DOI'),
        url=work.get('url'),
        abstract=work.get('abstract') or '',
        citation_count=work.get('citationCount') or 0,
        influential_citation_count=work.get('influentialCitationCount'),
        open_access_pdf_url=open_access_pdf.get('url'),
        provenance={'external_ids': external_ids},
    )


def _normalize_openalex_work(work: dict[str, Any]) -> DiscoveryResult:
    best_oa = work.get('best_oa_location') or {}
    return DiscoveryResult(
        source='openalex',
        source_id=work.get('id'),
        title=work.get('display_name'),
        authors=[a.get('author', {}).get('display_name', '') for a in work.get('authorships', []) if a.get('author', {}).get('display_name')],
        year=work.get('publication_year'),
        doi=work.get('doi'),
        url=work.get('id'),
        abstract='',
        citation_count=work.get('cited_by_count') or 0,
        open_access_pdf_url=(best_oa.get('pdf_url') or (best_oa.get('landing_page_url') if best_oa.get('is_oa') else None)),
        provenance={'openalex_id': work.get('id'), 'is_oa': work.get('is_oa', False)},
    )


def discover_openalex(query: str, per_page: int = 10) -> list[dict[str, Any]]:
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page={per_page}"
    data = _fetch_json(url)
    return [_normalize_openalex_work(w).to_dict() for w in data.get('results', [])]


def discover_semanticscholar(query: str, limit: int = 10) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({'query': query, 'limit': limit, 'fields': SEMANTIC_SCHOLAR_FIELDS})
    url = f'https://api.semanticscholar.org/graph/v1/paper/search?{params}'
    data = _fetch_json(url)
    return [_normalize_semanticscholar_work(w).to_dict() for w in data.get('data', [])]


def discover_papers(query: str, *, per_page: int = 10) -> list[dict[str, Any]]:
    primary = discover_semanticscholar(query, limit=per_page)
    fallback = discover_openalex(query, per_page=per_page)
    return primary + fallback
