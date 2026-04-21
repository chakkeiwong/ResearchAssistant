from __future__ import annotations

from research_assistant.query import discovery


def test_semanticscholar_discovery_normalizes_results(monkeypatch) -> None:
    monkeypatch.setattr(discovery, 'discover_openalex', lambda query, per_page=10: [])
    monkeypatch.setattr(discovery, '_fetch_json', lambda url: {
        'data': [
            {
                'paperId': 'abc',
                'title': 'A Paper',
                'authors': [{'name': 'Alice Example'}],
                'year': 2024,
                'abstract': 'An abstract.',
                'citationCount': 7,
                'influentialCitationCount': 2,
                'externalIds': {'DOI': '10.1/example'},
                'openAccessPdf': {'url': 'https://example.com/a.pdf'},
                'url': 'https://semanticscholar.org/paper/abc',
            }
        ]
    })
    results = discovery.discover_papers('test', per_page=1)
    assert results[0]['source'] == 'semanticscholar'
    assert results[0]['title'] == 'A Paper'
    assert results[0]['authors'] == ['Alice Example']
    assert results[0]['open_access_pdf_url'] == 'https://example.com/a.pdf'


def test_openalex_discovery_normalizes_results(monkeypatch) -> None:
    monkeypatch.setattr(discovery, '_fetch_json', lambda url: {
        'results': [
            {
                'id': 'https://openalex.org/W1',
                'display_name': 'OpenAlex Paper',
                'publication_year': 2023,
                'doi': 'https://doi.org/10.2/example',
                'cited_by_count': 4,
                'authorships': [{'author': {'display_name': 'Bob Example'}}],
                'is_oa': True,
                'best_oa_location': {'pdf_url': 'https://example.com/openalex.pdf', 'is_oa': True},
            }
        ]
    })
    results = discovery.discover_openalex('test', per_page=1)
    assert results[0]['source'] == 'openalex'
    assert results[0]['title'] == 'OpenAlex Paper'
    assert results[0]['authors'] == ['Bob Example']
    assert results[0]['open_access_pdf_url'] == 'https://example.com/openalex.pdf'
