from __future__ import annotations

from research_assistant.schemas.paper_record import PaperRecord


def _authors_from_openalex(openalex: dict) -> list[str]:
    return [
        a.get('author', {}).get('display_name', '')
        for a in openalex.get('authorships', [])
        if a.get('author')
    ]


def _authors_from_crossref(crossref: dict) -> list[str]:
    out = []
    for a in crossref.get('author', []) or []:
        parts = [a.get('given', ''), a.get('family', '')]
        name = ' '.join(p for p in parts if p).strip()
        if name:
            out.append(name)
    return out


def _build_review_summary(metadata_confidence: str, parser_confidence: str, identity_validation: dict, requires_manual_review: bool) -> dict:
    validation_status = identity_validation.get('status') or 'none'
    citation_status = (identity_validation.get('citation_neighborhood') or {}).get('status') or 'none'
    status = 'ready'
    if requires_manual_review:
        status = 'needs_review'
    if validation_status in {'conflict', 'ambiguous'}:
        status = 'conflict'
    warnings = []
    if metadata_confidence == 'low':
        warnings.append('metadata confidence is low')
    if parser_confidence == 'low':
        warnings.append('parser confidence is low')
    if validation_status in {'conflict', 'ambiguous'}:
        warnings.append(f'identity validation is {validation_status}')
    if citation_status in {'skipped', 'unavailable', 'inconclusive'}:
        warnings.append(f'citation neighborhood is {citation_status}')
    return {
        'status': status,
        'metadata_confidence': metadata_confidence,
        'parser_confidence': parser_confidence,
        'identity_validation': validation_status,
        'citation_neighborhood': citation_status,
        'warnings': warnings,
    }


def _technical_audit_fields() -> dict:
    return {
        'transport_definition': '',
        'objective': '',
        'transformed_target': '',
        'claimed_results': [],
        'derived_results': [],
        'open_questions': [],
        'relevant_equations': [],
        'relevant_sections': [],
        'assumptions_for_reuse': [],
    }


def build_draft_summary(paper_id: str, metadata: dict, text: str) -> PaperRecord:
    openalex = metadata.get('openalex', {})
    crossref = metadata.get('crossref', {})
    arxiv = metadata.get('arxiv', {})
    provenance = metadata.get('provenance', {})
    parser_hints = metadata.get('parser_hints', {})
    identity_validation = metadata.get('identity_validation', {})
    metadata_confidence = metadata.get('metadata_confidence', 'low')
    parser_confidence = parser_hints.get('parse_confidence', 'low')

    parser_title = parser_hints.get('consensus_title')
    parser_authors = parser_hints.get('consensus_authors', [])

    use_parser_primary = bool(parser_title) and metadata_confidence == 'low' and parser_confidence in {'medium', 'high'}

    title_source = 'arxiv'
    title = arxiv.get('title')
    if not title and use_parser_primary:
        title = parser_title
        title_source = 'parser_consensus'
    if not title:
        title = openalex.get('display_name')
        title_source = 'openalex'
    if not title and crossref.get('title'):
        title = crossref['title'][0]
        title_source = 'crossref'
    if not title:
        title = paper_id
        title_source = 'fallback'

    year_source = 'openalex'
    year = openalex.get('publication_year')
    if not year and crossref.get('published'):
        year = crossref.get('published', {}).get('date-parts', [[None]])[0][0]
        year_source = 'crossref'

    authors_source = 'arxiv'
    authors = arxiv.get('authors', [])
    if not authors and use_parser_primary and parser_authors:
        authors = parser_authors
        authors_source = 'parser_consensus'
    if not authors:
        authors = _authors_from_openalex(openalex)
        authors_source = 'openalex'
    if not authors:
        authors = _authors_from_crossref(crossref)
        authors_source = 'crossref'

    abstract_source = 'arxiv'
    abstract = arxiv.get('abstract', '')
    inverted = openalex.get('abstract_inverted_index')
    if not abstract and inverted:
        words = []
        for word, positions in inverted.items():
            for pos in positions:
                words.append((pos, word))
        abstract = ' '.join(word for pos, word in sorted(words))
        abstract_source = 'openalex'
    if not abstract and use_parser_primary:
        parser_outputs = parser_hints.get('parser_outputs', [])
        for output in parser_outputs:
            body = output.get('body_markdown') or output.get('body_text') or ''
            if body.strip():
                abstract = body[:1500].strip()
                abstract_source = 'parser_excerpt'
                break

    source_url = openalex.get('id') or metadata.get('source')
    doi = openalex.get('doi') or crossref.get('DOI')

    identity_source = title_source if use_parser_primary else ('arxiv' if arxiv else ('openalex' if openalex else ('crossref' if crossref else 'fallback')))
    requires_manual_review = bool(use_parser_primary or metadata_confidence == 'low' or identity_validation.get('requires_manual_review'))
    merge_notes = list(metadata.get('merge_notes', []))
    validation_status = identity_validation.get('status')
    citation_status = (identity_validation.get('citation_neighborhood') or {}).get('status')
    if validation_status:
        merge_notes.append(f'identity validation: {validation_status}')
        merge_notes.extend(identity_validation.get('notes', []))
    if citation_status:
        merge_notes.append(f'citation neighborhood: {citation_status}')
    candidate_metadata_sources = {
        'semanticscholar_candidates': metadata.get('semanticscholar_candidates', []),
        'openalex_candidates': metadata.get('openalex_candidates', []),
        'crossref_candidates': metadata.get('crossref_candidates', []),
        'source_statuses': metadata.get('source_statuses', []),
    }
    review_summary = _build_review_summary(metadata_confidence, parser_confidence, identity_validation, requires_manual_review)

    summary = PaperRecord(
        id=paper_id,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        arxiv_id=arxiv.get('arxiv_id'),
        source_url=source_url,
        abstract=abstract,
        main_contribution=(abstract[:500] if abstract else text[:500]).strip(),
        confidence_level='low',
        curation_status='draft',
        metadata_confidence=metadata_confidence,
        identity_source=identity_source,
        review_status=review_summary['status'],
        review_summary=review_summary,
        requires_manual_review=requires_manual_review,
        candidate_metadata_sources=candidate_metadata_sources,
        merge_notes=merge_notes,
        technical_audit=_technical_audit_fields(),
        provenance={
            **provenance,
            'identity_validation': validation_status or 'none',
            'citation_neighborhood': citation_status or 'none',
            'title': title_source,
            'authors': authors_source,
            'year': year_source,
            'abstract': abstract_source if abstract else 'none',
        },
    )
    return summary
