from __future__ import annotations

import difflib
import json
import re
import urllib.error
import urllib.request
import urllib.parse
from typing import Any
import xml.etree.ElementTree as ET


TITLE_SIMILARITY_THRESHOLD = 0.88
WEAK_SIMILARITY_THRESHOLD = 0.75


def _fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def normalize_title(title: str) -> str:
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', title.lower()).split())


def title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def extract_title_candidates(source: str, extracted_text: str = '', filename_hints: dict[str, Any] | None = None, parser_hints: dict[str, Any] | None = None) -> list[str]:
    candidates = [source]
    if parser_hints:
        if parser_hints.get('consensus_title'):
            candidates.append(parser_hints['consensus_title'])
        for output in parser_hints.get('parser_outputs', []):
            candidates.extend(output.get('derived_title_candidates', [])[:3])
    if filename_hints:
        if filename_hints.get('probable_title'):
            candidates.append(filename_hints['probable_title'])
        if filename_hints.get('raw_name'):
            candidates.append(filename_hints['raw_name'])
    if extracted_text:
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        candidates.extend(lines[:8])
    seen = set()
    out = []
    for c in candidates:
        n = normalize_title(c)
        if n and n not in seen:
            seen.add(n)
            out.append(c)
    return out


def score_candidate(title: str, anchors: list[str]) -> float:
    return max((title_similarity(anchor, title) for anchor in anchors), default=0.0)


def _metadata_source_status(source: str, status: str, *, reason: str | None = None, code: int | None = None, result_count: int = 0) -> dict[str, Any]:
    payload = {
        'source': source,
        'status': status,
        'result_count': result_count,
    }
    if reason is not None:
        payload['reason'] = reason
    if code is not None:
        payload['code'] = code
    return payload



def choose_best_openalex_result(query: str, extracted_text: str = '', filename_hints: dict[str, Any] | None = None, parser_hints: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page=8"
    data = _fetch_json(url)
    results = data.get('results', [])
    anchors = extract_title_candidates(query, extracted_text, filename_hints, parser_hints)
    scored = []
    for r in results:
        title = r.get('display_name', '')
        best = score_candidate(title, anchors)
        scored.append({
            'id': r.get('id'),
            'title': title,
            'score': best,
            'year': r.get('publication_year'),
            'raw': r,
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    best = scored[0]['raw'] if scored else {}
    return best, scored


def resolve_crossref_by_title(title: str) -> dict[str, Any]:
    url = f"https://api.crossref.org/works?query.title={urllib.parse.quote(title)}&rows=5"
    data = _fetch_json(url)
    items = data.get('message', {}).get('items', [])
    return {'items': items}


def choose_best_crossref_result(query: str, extracted_text: str = '', filename_hints: dict[str, Any] | None = None, parser_hints: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    response = resolve_crossref_by_title(query)
    items = response.get('items', [])
    anchors = extract_title_candidates(query, extracted_text, filename_hints, parser_hints)
    scored = []
    for r in items:
        title = (r.get('title') or [''])[0]
        best = score_candidate(title, anchors)
        scored.append({
            'title': title,
            'score': best,
            'doi': r.get('DOI'),
            'raw': r,
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    best = scored[0]['raw'] if scored else {}
    return best, scored


def choose_best_semanticscholar_result(query: str, extracted_text: str = '', filename_hints: dict[str, Any] | None = None, parser_hints: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from research_assistant.query.discovery import discover_semanticscholar

    items = discover_semanticscholar(query, limit=8)
    anchors = extract_title_candidates(query, extracted_text, filename_hints, parser_hints)
    scored = []
    for r in items:
        title = r.get('title', '')
        best = score_candidate(title, anchors)
        scored.append({
            'source': 'semanticscholar',
            'source_id': r.get('source_id'),
            'title': title,
            'authors': r.get('authors', []),
            'score': best,
            'year': r.get('year'),
            'doi': r.get('doi'),
            'raw': r,
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    best = scored[0]['raw'] if scored else {}
    return best, scored


def resolve_arxiv(arxiv_id: str) -> dict[str, Any]:
    url = f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}"
    with urllib.request.urlopen(url, timeout=30) as response:
        text = response.read().decode('utf-8', errors='ignore')
    root = ET.fromstring(text)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entry = root.find('a:entry', ns)
    if entry is None:
        return {"arxiv_id": arxiv_id, "raw": text}
    title = (entry.findtext('a:title', default='', namespaces=ns) or '').strip()
    authors = [e.findtext('a:name', default='', namespaces=ns) for e in entry.findall('a:author', ns)]
    summary = (entry.findtext('a:summary', default='', namespaces=ns) or '').strip()
    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": summary,
        "raw": text,
    }


def should_merge_crossref(query: str, openalex: dict[str, Any], crossref: dict[str, Any]) -> tuple[bool, str, float]:
    crossref_title = (crossref.get('title') or [''])[0]
    anchor_title = openalex.get('display_name') or query
    if not crossref_title or not anchor_title:
        return False, 'missing title for conservative crossref merge', 0.0
    score = title_similarity(anchor_title, crossref_title)
    if score >= TITLE_SIMILARITY_THRESHOLD:
        return True, f'title similarity {score:.3f} >= {TITLE_SIMILARITY_THRESHOLD:.2f}', score
    return False, f'title similarity {score:.3f} < {TITLE_SIMILARITY_THRESHOLD:.2f}; crossref kept as unmerged candidate', score


def merge_metadata(source: str, openalex: dict[str, Any], crossref: dict[str, Any] | None = None, arxiv: dict[str, Any] | None = None, *, openalex_candidates: list[dict[str, Any]] | None = None, crossref_candidates: list[dict[str, Any]] | None = None, semanticscholar_candidates: list[dict[str, Any]] | None = None, source_statuses: list[dict[str, Any]] | None = None, filename_hints: dict[str, Any] | None = None, parser_hints: dict[str, Any] | None = None) -> dict[str, Any]:
    crossref = crossref or {}
    arxiv = arxiv or {}
    merge_notes = []
    provenance = {}

    merge_crossref = False
    crossref_score = 0.0
    if crossref:
        merge_crossref, note, crossref_score = should_merge_crossref(source, openalex or {}, crossref)
        merge_notes.append(note)

    openalex_score = (openalex_candidates or [{}])[0].get('score', 0.0) if openalex_candidates else 0.0
    metadata_confidence = 'low'
    if openalex_score >= TITLE_SIMILARITY_THRESHOLD:
        metadata_confidence = 'medium'
    if arxiv:
        metadata_confidence = 'high'
        provenance['arxiv'] = 'exact arxiv id supplied'
    if merge_crossref:
        provenance['crossref'] = 'merged by conservative title similarity'
    elif crossref:
        provenance['crossref'] = 'not merged; stored as candidate only'
    if openalex:
        provenance['openalex'] = f'best candidate score {openalex_score:.3f}'
        if openalex_score < WEAK_SIMILARITY_THRESHOLD and not arxiv:
            merge_notes.append('openalex top candidate has weak similarity; manual review recommended')
    if filename_hints:
        provenance['filename'] = 'filename-derived title and optional author/year hints available'
    if parser_hints:
        provenance['parser_consensus'] = f"parse confidence {parser_hints.get('parse_confidence', 'unknown')}"

    return {
        'source': source,
        'openalex': openalex or {},
        'openalex_candidates': openalex_candidates or [],
        'crossref': crossref if merge_crossref else {},
        'crossref_candidate': crossref if crossref and not merge_crossref else {},
        'crossref_candidates': crossref_candidates or [],
        'semanticscholar_candidates': semanticscholar_candidates or [],
        'source_statuses': source_statuses or [],
        'arxiv': arxiv,
        'filename_hints': filename_hints or {},
        'parser_hints': parser_hints or {},
        'merge_notes': merge_notes,
        'metadata_confidence': metadata_confidence,
        'provenance': provenance,
        'scores': {
            'openalex_title_similarity': openalex_score,
            'crossref_title_similarity': crossref_score,
        },
    }


def resolve_metadata(source: str, *, arxiv_id: str | None = None, extracted_text: str = '', filename_hints: dict[str, Any] | None = None, parser_hints: dict[str, Any] | None = None) -> dict[str, Any]:
    source_statuses = []
    try:
        openalex, openalex_candidates = choose_best_openalex_result(source, extracted_text=extracted_text, filename_hints=filename_hints, parser_hints=parser_hints)
        source_statuses.append(_metadata_source_status('openalex', 'available', result_count=len(openalex_candidates)))
    except urllib.error.HTTPError as exc:
        openalex, openalex_candidates = {}, []
        source_statuses.append(_metadata_source_status('openalex', 'unavailable', code=exc.code, reason=str(exc)))
    except Exception as exc:
        openalex, openalex_candidates = {}, []
        source_statuses.append(_metadata_source_status('openalex', 'unavailable', reason=str(exc)))

    try:
        crossref, crossref_candidates = choose_best_crossref_result(source, extracted_text=extracted_text, filename_hints=filename_hints, parser_hints=parser_hints)
        source_statuses.append(_metadata_source_status('crossref', 'available', result_count=len(crossref_candidates)))
    except urllib.error.HTTPError as exc:
        crossref, crossref_candidates = {}, []
        source_statuses.append(_metadata_source_status('crossref', 'unavailable', code=exc.code, reason=str(exc)))
    except Exception as exc:
        crossref, crossref_candidates = {}, []
        source_statuses.append(_metadata_source_status('crossref', 'unavailable', reason=str(exc)))

    try:
        _, semanticscholar_candidates = choose_best_semanticscholar_result(source, extracted_text=extracted_text, filename_hints=filename_hints, parser_hints=parser_hints)
        source_statuses.append(_metadata_source_status('semanticscholar', 'available', result_count=len(semanticscholar_candidates)))
    except urllib.error.HTTPError as exc:
        semanticscholar_candidates = []
        source_statuses.append(_metadata_source_status('semanticscholar', 'unavailable', code=exc.code, reason=str(exc)))
    except Exception as exc:
        semanticscholar_candidates = []
        source_statuses.append(_metadata_source_status('semanticscholar', 'unavailable', reason=str(exc)))

    try:
        arxiv = resolve_arxiv(arxiv_id) if arxiv_id else {}
        if arxiv_id:
            source_statuses.append(_metadata_source_status('arxiv', 'available', result_count=1 if arxiv else 0))
    except urllib.error.HTTPError as exc:
        arxiv = {}
        source_statuses.append(_metadata_source_status('arxiv', 'unavailable', code=exc.code, reason=str(exc)))
    except Exception as exc:
        arxiv = {}
        source_statuses.append(_metadata_source_status('arxiv', 'unavailable', reason=str(exc)))

    return merge_metadata(
        source,
        openalex,
        crossref,
        arxiv,
        openalex_candidates=openalex_candidates,
        crossref_candidates=crossref_candidates,
        semanticscholar_candidates=semanticscholar_candidates,
        source_statuses=source_statuses,
        filename_hints=filename_hints,
        parser_hints=parser_hints,
    )
