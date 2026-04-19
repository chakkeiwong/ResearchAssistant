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


def build_draft_summary(paper_id: str, metadata: dict, text: str) -> PaperRecord:
    openalex = metadata.get('openalex', {})
    crossref = metadata.get('crossref', {})
    arxiv = metadata.get('arxiv', {})
    provenance = metadata.get('provenance', {})

    title_source = 'arxiv'
    title = arxiv.get('title')
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

    source_url = openalex.get('id') or metadata.get('source')
    doi = openalex.get('doi') or crossref.get('DOI')

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
        metadata_confidence=metadata.get('metadata_confidence', 'low'),
        merge_notes=metadata.get('merge_notes', []),
        provenance={
            **provenance,
            'title': title_source,
            'authors': authors_source,
            'year': year_source,
            'abstract': abstract_source if abstract else 'none',
        },
    )
    return summary
