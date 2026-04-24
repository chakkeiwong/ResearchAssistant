from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
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


def _normalize_text(value: str | None) -> str:
    text = (value or '').lower().strip()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _title_similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, _normalize_text(left), _normalize_text(right)).ratio()


def _candidate_key(result: dict[str, Any]) -> str:
    doi = (result.get('doi') or '').strip().lower()
    if doi:
        return f'doi:{doi}'
    return f"title:{_normalize_text(result.get('title'))}"


def _merge_group(query: str, group: list[dict[str, Any]]) -> dict[str, Any]:
    best_title = max(group, key=lambda item: len(item.get('title') or ''))
    best_abstract = max(group, key=lambda item: len(item.get('abstract') or ''))
    best_pdf = next((item.get('open_access_pdf_url') for item in group if item.get('open_access_pdf_url')), None)
    citation_count = max((item.get('citation_count') or 0) for item in group)
    influential_citation_count = max((item.get('influential_citation_count') or 0) for item in group)
    authors = []
    seen_authors = set()
    for item in group:
        for author in item.get('authors') or []:
            key = author.lower()
            if key not in seen_authors:
                seen_authors.add(key)
                authors.append(author)
    merged = {
        'source': group[0].get('source'),
        'source_id': group[0].get('source_id'),
        'title': best_title.get('title'),
        'authors': authors,
        'year': best_title.get('year'),
        'doi': best_title.get('doi') or next((item.get('doi') for item in group if item.get('doi')), None),
        'url': best_title.get('url'),
        'abstract': best_abstract.get('abstract') or '',
        'citation_count': citation_count,
        'influential_citation_count': influential_citation_count or None,
        'open_access_pdf_url': best_pdf,
        'provenance': {
            'merged_sources': [
                {
                    'source': item.get('source'),
                    'source_id': item.get('source_id'),
                    'doi': item.get('doi'),
                    'title': item.get('title'),
                    'open_access_pdf_url': item.get('open_access_pdf_url'),
                    'provenance': item.get('provenance', {}),
                }
                for item in group
            ],
        },
    }
    merged['ranking'] = {
        'title_similarity': _title_similarity(query, merged.get('title')),
        'citation_count': citation_count,
        'influential_citation_count': influential_citation_count or 0,
        'has_open_access_pdf': bool(best_pdf),
    }
    merged['ranking_score'] = (
        merged['ranking']['title_similarity'] * 100
        + min(citation_count, 500) * 0.05
        + min(influential_citation_count or 0, 100) * 0.2
        + (15 if best_pdf else 0)
    )
    return merged


def _merge_discovery_results(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        grouped.setdefault(_candidate_key(result), []).append(result)
    merged = [_merge_group(query, group) for group in grouped.values()]
    merged.sort(key=lambda item: item.get('ranking_score', 0), reverse=True)
    return merged


def _discovery_status(source_statuses: list[dict[str, Any]], results: list[dict[str, Any]]) -> str:
    if results:
        return 'available'
    if any(status['status'] == 'available' for status in source_statuses):
        return 'empty'
    return 'unavailable'


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
    return _merge_discovery_results(query, primary + fallback)


def discover_papers_with_status(query: str, *, per_page: int = 10) -> dict[str, Any]:
    source_statuses = []
    results_by_source = []
    for source_name, loader in [
        ('semanticscholar', lambda: discover_semanticscholar(query, limit=per_page)),
        ('openalex', lambda: discover_openalex(query, per_page=per_page)),
    ]:
        try:
            rows = loader()
            results_by_source.extend(rows)
            source_statuses.append({
                'source': source_name,
                'status': 'available',
                'result_count': len(rows),
            })
        except urllib.error.HTTPError as exc:
            source_statuses.append({
                'source': source_name,
                'status': 'unavailable',
                'code': exc.code,
                'reason': str(exc),
                'result_count': 0,
            })
        except Exception as exc:
            source_statuses.append({
                'source': source_name,
                'status': 'unavailable',
                'reason': str(exc),
                'result_count': 0,
            })
    merged = _merge_discovery_results(query, results_by_source)
    return {
        'query': query,
        'status': _discovery_status(source_statuses, merged),
        'results': merged,
        'source_statuses': source_statuses,
    }
