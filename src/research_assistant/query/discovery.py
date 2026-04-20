from __future__ import annotations

import json
import urllib.request
import urllib.parse
from typing import Any


def _fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def discover_openalex(query: str, per_page: int = 10) -> list[dict[str, Any]]:
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page={per_page}"
    data = _fetch_json(url)
    results = []
    for w in data.get('results', []):
        results.append({
            'source': 'openalex',
            'id': w.get('id'),
            'title': w.get('display_name'),
            'year': w.get('publication_year'),
            'doi': w.get('doi'),
            'cited_by_count': w.get('cited_by_count', 0),
        })
    return results


def discover_semanticscholar(query: str) -> list[dict[str, Any]]:
    # Placeholder until full API integration is implemented.
    return []


def discover_papers(query: str, *, per_page: int = 10) -> list[dict[str, Any]]:
    results = []
    results.extend(discover_openalex(query, per_page=per_page))
    results.extend(discover_semanticscholar(query))
    return results
