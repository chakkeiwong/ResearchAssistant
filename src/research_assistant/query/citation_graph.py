from __future__ import annotations

import urllib.error
import urllib.parse
from typing import Any

from research_assistant.query.discovery import SEMANTIC_SCHOLAR_FIELDS, _fetch_json, _normalize_semanticscholar_work, discover_papers


def _citation_source_status(endpoint: str, status: str, *, reason: str | None = None, code: int | None = None, result_count: int = 0) -> dict[str, Any]:
    payload = {
        'endpoint': endpoint,
        'status': status,
        'result_count': result_count,
    }
    if reason is not None:
        payload['reason'] = reason
    if code is not None:
        payload['code'] = code
    return payload


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


def _rank_citation_rows(rows: list[dict]) -> list[dict]:
    ranked = []
    for row in rows:
        citation_count = row.get('citation_count') or 0
        influential = row.get('influential_citation_count') or 0
        has_pdf = bool(row.get('open_access_pdf_url'))
        ranking_score = citation_count + influential * 3 + (10 if has_pdf else 0)
        ranked.append({
            **row,
            'ranking': {
                'citation_count': citation_count,
                'influential_citation_count': influential,
                'has_open_access_pdf': has_pdf,
            },
            'ranking_score': ranking_score,
        })
    ranked.sort(key=lambda row: row['ranking_score'], reverse=True)
    return ranked


def _citation_summary(rows: list[dict], *, limit: int) -> list[dict]:
    summary = []
    for row in _rank_citation_rows(rows)[:limit]:
        summary.append({
            'source_id': row.get('source_id'),
            'title': row.get('title'),
            'authors': row.get('authors', [])[:3],
            'year': row.get('year'),
            'citation_count': row.get('citation_count'),
            'influential_citation_count': row.get('influential_citation_count'),
            'open_access_pdf_url': row.get('open_access_pdf_url'),
            'ranking_score': row.get('ranking_score'),
        })
    return summary


def papers_citing(paper_id: str, *, limit: int = 10) -> list[dict]:
    return _fetch_semanticscholar_citation_list(paper_id, 'citations', limit=limit)


def papers_cited_by(paper_id: str, *, limit: int = 10) -> list[dict]:
    return _fetch_semanticscholar_citation_list(paper_id, 'references', limit=limit)


def _citation_neighborhood_status(endpoint_statuses: list[dict[str, Any]], citing: list[dict], cited: list[dict]) -> tuple[str, str]:
    if citing or cited:
        return 'available', 'citation data returned from at least one endpoint'
    if any(row['status'] == 'available' for row in endpoint_statuses):
        return 'empty', 'at least one citation endpoint responded but returned no papers'
    return 'unavailable', 'all citation endpoints are unavailable'


def _citation_neighborhood_diagnostics(endpoint_statuses: list[dict[str, Any]]) -> dict[str, Any]:
    unavailable = [row for row in endpoint_statuses if row.get('status') == 'unavailable']
    available_empty = [row for row in endpoint_statuses if row.get('status') == 'available' and row.get('result_count') == 0]
    return {
        'unavailable_endpoints': [row['endpoint'] for row in unavailable],
        'available_empty_endpoints': [row['endpoint'] for row in available_empty],
        'failure_reasons': [
            {
                'endpoint': row.get('endpoint'),
                'code': row.get('code'),
                'reason': row.get('reason'),
            }
            for row in unavailable
        ],
    }


def citation_neighborhood(paper_id: str, *, limit: int = 5) -> dict[str, Any]:
    endpoint_rows: dict[str, list[dict]] = {}
    endpoint_statuses = []
    for endpoint, loader in [
        ('citations', lambda: papers_citing(paper_id, limit=limit)),
        ('references', lambda: papers_cited_by(paper_id, limit=limit)),
    ]:
        try:
            rows = loader()
            endpoint_rows[endpoint] = rows
            endpoint_statuses.append(_citation_source_status(endpoint, 'available', result_count=len(rows)))
        except urllib.error.HTTPError as exc:
            endpoint_rows[endpoint] = []
            endpoint_statuses.append(_citation_source_status(endpoint, 'unavailable', code=exc.code, reason=str(exc), result_count=0))
        except Exception as exc:
            endpoint_rows[endpoint] = []
            endpoint_statuses.append(_citation_source_status(endpoint, 'unavailable', reason=str(exc), result_count=0))
    citing = endpoint_rows['citations']
    cited = endpoint_rows['references']
    status, status_reason = _citation_neighborhood_status(endpoint_statuses, citing, cited)
    return {
        'paper_id': paper_id,
        'citing': citing,
        'cited': cited,
        'citing_count': len(citing),
        'cited_count': len(cited),
        'status': status,
        'status_reason': status_reason,
        'source_statuses': endpoint_statuses,
        'diagnostics': _citation_neighborhood_diagnostics(endpoint_statuses),
        'summary': {
            'top_citing': _citation_summary(citing, limit=limit),
            'top_cited': _citation_summary(cited, limit=limit),
        },
    }


def related_papers(topic: str) -> list[dict]:
    return discover_papers(topic)
