from __future__ import annotations

from typing import Any

from research_assistant.ingest.metadata_resolve import TITLE_SIMILARITY_THRESHOLD, title_similarity
from research_assistant.query.citation_graph import citation_neighborhood


def _normalize_author(name: str) -> str:
    return ' '.join(part for part in name.lower().replace('.', ' ').split() if part)


def _author_overlap(parser_authors: list[str], candidate_authors: list[str]) -> float:
    parser = {_normalize_author(a) for a in parser_authors if a}
    candidate = {_normalize_author(a) for a in candidate_authors if a}
    if not parser or not candidate:
        return 0.0
    return len(parser & candidate) / len(parser)


def _candidate_score(parser_title: str, parser_authors: list[str], candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_title = candidate.get('title') or candidate.get('display_name') or ''
    candidate_authors = candidate.get('authors') or []
    title_score = title_similarity(parser_title, candidate_title) if parser_title and candidate_title else 0.0
    author_score = _author_overlap(parser_authors, candidate_authors)
    combined = (title_score * 0.8) + (author_score * 0.2)
    return {
        'source': candidate.get('source') or 'metadata',
        'source_id': candidate.get('source_id') or candidate.get('id'),
        'title': candidate_title,
        'authors': candidate_authors,
        'year': candidate.get('year') or candidate.get('publication_year'),
        'doi': candidate.get('doi'),
        'title_similarity': title_score,
        'author_overlap': author_score,
        'score': combined,
    }


def _metadata_candidates(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    candidates.extend(metadata.get('semanticscholar_candidates') or [])
    candidates.extend(metadata.get('openalex_candidates') or [])
    candidates.extend(metadata.get('crossref_candidates') or [])
    openalex = metadata.get('openalex') or {}
    if openalex:
        candidates.append({
            'source': 'openalex',
            'source_id': openalex.get('id'),
            'title': openalex.get('display_name'),
            'authors': [
                a.get('author', {}).get('display_name', '')
                for a in openalex.get('authorships', [])
                if a.get('author', {}).get('display_name')
            ],
            'year': openalex.get('publication_year'),
            'doi': openalex.get('doi'),
        })
    crossref = metadata.get('crossref') or metadata.get('crossref_candidate') or {}
    if crossref:
        candidates.append({
            'source': 'crossref',
            'title': (crossref.get('title') or [''])[0],
            'authors': [
                ' '.join(part for part in [a.get('given', ''), a.get('family', '')] if part).strip()
                for a in crossref.get('author', []) or []
            ],
            'year': (crossref.get('published') or {}).get('date-parts', [[None]])[0][0],
            'doi': crossref.get('DOI'),
        })
    return [c for c in candidates if c.get('title') or c.get('display_name')]


def _citation_validation(best: dict[str, Any]) -> dict[str, Any]:
    if best.get('source') != 'semanticscholar':
        return {
            'status': 'skipped',
            'reason': 'no Semantic Scholar candidate',
            'candidate_paper_id': best.get('source_id'),
            'citing_count': 0,
            'cited_count': 0,
            'citing_sample': [],
            'cited_sample': [],
            'notes': [],
        }
    if not best.get('source_id'):
        return {
            'status': 'skipped',
            'reason': 'Semantic Scholar candidate missing source id',
            'candidate_paper_id': None,
            'citing_count': 0,
            'cited_count': 0,
            'citing_sample': [],
            'cited_sample': [],
            'notes': [],
        }
    neighborhood = citation_neighborhood(best['source_id'])
    if neighborhood['status'] == 'unavailable':
        return {
            'status': 'unavailable',
            'reason': 'citation graph unavailable',
            'candidate_paper_id': best['source_id'],
            'citing_count': 0,
            'cited_count': 0,
            'citing_sample': [],
            'cited_sample': [],
            'notes': ['citation graph lookup failed'],
        }
    if neighborhood['status'] == 'empty':
        return {
            'status': 'inconclusive',
            'reason': 'citation neighborhood empty',
            'candidate_paper_id': best['source_id'],
            'citing_count': 0,
            'cited_count': 0,
            'citing_sample': [],
            'cited_sample': [],
            'notes': ['citation graph returned no citing or cited papers'],
        }
    return {
        'status': 'corroborated',
        'reason': 'citation neighborhood available',
        'candidate_paper_id': best['source_id'],
        'citing_count': neighborhood['citing_count'],
        'cited_count': neighborhood['cited_count'],
        'citing_sample': neighborhood['citing'],
        'cited_sample': neighborhood['cited'],
        'notes': ['citation graph returned citing/cited neighbors for validated candidate'],
    }


def validate_identity(metadata: dict[str, Any]) -> dict[str, Any]:
    parser_hints = metadata.get('parser_hints') or {}
    parser_title = parser_hints.get('consensus_title') or ''
    parser_authors = parser_hints.get('consensus_authors') or []
    parser_confidence = parser_hints.get('parse_confidence', 'low')

    result = {
        'status': 'insufficient_evidence',
        'confidence': 'low',
        'parser_title': parser_title,
        'parser_authors': parser_authors,
        'best_discovery_match': {},
        'candidate_scores': [],
        'citation_neighborhood': {},
        'notes': [],
        'requires_manual_review': False,
    }
    if not parser_title:
        result['notes'].append('no parser consensus title available')
        return result

    scored = [_candidate_score(parser_title, parser_authors, candidate) for candidate in _metadata_candidates(metadata)]
    scored.sort(key=lambda c: c['score'], reverse=True)
    result['candidate_scores'] = scored
    if not scored:
        result['notes'].append('no external metadata candidates available')
        return result

    best = scored[0]
    result['best_discovery_match'] = best
    if best['title_similarity'] >= TITLE_SIMILARITY_THRESHOLD:
        result['status'] = 'validated'
        result['confidence'] = 'medium' if parser_confidence in {'medium', 'high'} else 'low'
        result['notes'].append('external metadata title agrees with parser consensus')
        result['citation_neighborhood'] = _citation_validation(best)
    elif parser_confidence in {'medium', 'high'}:
        result['status'] = 'conflict'
        result['confidence'] = 'medium'
        result['requires_manual_review'] = True
        result['notes'].append('external metadata disagrees with parser consensus')
        result['citation_neighborhood'] = {
            'status': 'skipped',
            'reason': 'candidate not validated by title',
            'candidate_paper_id': best.get('source_id'),
            'citing_count': 0,
            'cited_count': 0,
            'citing_sample': [],
            'cited_sample': [],
            'notes': [],
        }
    else:
        result['status'] = 'ambiguous'
        result['confidence'] = 'low'
        result['requires_manual_review'] = True
        result['notes'].append('parser and external metadata are too weak to validate identity')
        result['citation_neighborhood'] = {
            'status': 'skipped',
            'reason': 'candidate not validated by title',
            'candidate_paper_id': best.get('source_id'),
            'citing_count': 0,
            'cited_count': 0,
            'citing_sample': [],
            'cited_sample': [],
            'notes': [],
        }
    return result
