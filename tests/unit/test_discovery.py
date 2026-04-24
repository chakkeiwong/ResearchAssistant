from __future__ import annotations

import urllib.error

from research_assistant.query import citation_graph
from research_assistant.query.discovery import _merge_discovery_results, discover_papers_with_status


def test_related_papers_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(citation_graph, 'discover_papers', lambda topic: [])
    assert isinstance(citation_graph.related_papers('transport maps hmc'), list)


def test_merge_discovery_results_deduplicates_by_doi_and_keeps_provenance() -> None:
    results = [
        {
            'source': 'semanticscholar',
            'source_id': 's1',
            'title': 'A Test Paper',
            'authors': ['Alice Example'],
            'year': 2024,
            'doi': '10.123/test',
            'url': 'https://semanticscholar.org/paper/s1',
            'abstract': 'semantic abstract',
            'citation_count': 12,
            'influential_citation_count': 3,
            'open_access_pdf_url': None,
            'provenance': {'external_ids': {'DOI': '10.123/test'}},
        },
        {
            'source': 'openalex',
            'source_id': 'o1',
            'title': 'A Test Paper',
            'authors': ['Alice Example', 'Bob Example'],
            'year': 2024,
            'doi': '10.123/test',
            'url': 'https://openalex.org/W1',
            'abstract': '',
            'citation_count': 30,
            'influential_citation_count': None,
            'open_access_pdf_url': 'https://example.com/paper.pdf',
            'provenance': {'openalex_id': 'W1', 'is_oa': True},
        },
    ]

    merged = _merge_discovery_results('test paper', results)

    assert len(merged) == 1
    row = merged[0]
    assert row['doi'] == '10.123/test'
    assert row['open_access_pdf_url'] == 'https://example.com/paper.pdf'
    assert row['citation_count'] == 30
    assert row['authors'] == ['Alice Example', 'Bob Example']
    assert len(row['provenance']['merged_sources']) == 2
    assert row['ranking']['has_open_access_pdf'] is True


def test_merge_discovery_results_ranks_better_match_first() -> None:
    results = [
        {
            'source': 'semanticscholar',
            'source_id': 'low',
            'title': 'Unrelated Paper',
            'authors': [],
            'year': 2020,
            'doi': None,
            'url': None,
            'abstract': '',
            'citation_count': 500,
            'influential_citation_count': 50,
            'open_access_pdf_url': None,
            'provenance': {},
        },
        {
            'source': 'semanticscholar',
            'source_id': 'high',
            'title': 'Transport Maps for Posterior Geometry',
            'authors': [],
            'year': 2024,
            'doi': None,
            'url': None,
            'abstract': '',
            'citation_count': 10,
            'influential_citation_count': 2,
            'open_access_pdf_url': 'https://example.com/transport.pdf',
            'provenance': {},
        },
    ]

    merged = _merge_discovery_results('transport maps posterior geometry', results)

    assert merged[0]['source_id'] == 'high'
    assert merged[0]['ranking_score'] > merged[1]['ranking_score']


def test_discover_papers_with_status_reports_unavailable_sources(monkeypatch) -> None:
    def fail_semanticscholar(query: str, limit: int = 10) -> list[dict]:
        raise urllib.error.HTTPError('https://example.com', 429, 'rate limited', None, None)

    monkeypatch.setattr('research_assistant.query.discovery.discover_semanticscholar', fail_semanticscholar)
    monkeypatch.setattr('research_assistant.query.discovery.discover_openalex', lambda query, per_page=10: [])

    payload = discover_papers_with_status('transport maps', per_page=5)

    assert payload['status'] == 'empty'
    assert payload['results'] == []
    assert payload['source_statuses'][0]['source'] == 'semanticscholar'
    assert payload['source_statuses'][0]['status'] == 'unavailable'
    assert payload['source_statuses'][0]['code'] == 429
    assert payload['source_statuses'][1]['source'] == 'openalex'
    assert payload['source_statuses'][1]['status'] == 'available'


def test_discover_papers_with_status_reports_fully_unavailable(monkeypatch) -> None:
    monkeypatch.setattr('research_assistant.query.discovery.discover_semanticscholar', lambda query, limit=10: (_ for _ in ()).throw(RuntimeError('down')))
    monkeypatch.setattr('research_assistant.query.discovery.discover_openalex', lambda query, per_page=10: (_ for _ in ()).throw(RuntimeError('down too')))

    payload = discover_papers_with_status('transport maps', per_page=5)

    assert payload['status'] == 'unavailable'
    assert payload['results'] == []
    assert [row['status'] for row in payload['source_statuses']] == ['unavailable', 'unavailable']


def test_citation_neighborhood_returns_ranked_summary(monkeypatch) -> None:
    monkeypatch.setattr(citation_graph, 'papers_citing', lambda paper_id, limit=5: [
        {
            'source_id': 'citing-1',
            'title': 'High Impact Citing Paper',
            'authors': ['Alice Example', 'Bob Example', 'Carol Example', 'Dan Example'],
            'year': 2025,
            'citation_count': 10,
            'influential_citation_count': 2,
            'open_access_pdf_url': 'https://example.com/citing.pdf',
        },
        {
            'source_id': 'citing-2',
            'title': 'Lower Impact Citing Paper',
            'authors': ['Eve Example'],
            'year': 2024,
            'citation_count': 1,
            'influential_citation_count': 0,
            'open_access_pdf_url': None,
        },
    ])
    monkeypatch.setattr(citation_graph, 'papers_cited_by', lambda paper_id, limit=5: [
        {
            'source_id': 'cited-1',
            'title': 'Foundational Paper',
            'authors': ['Frank Example'],
            'year': 2018,
            'citation_count': 20,
            'influential_citation_count': 4,
            'open_access_pdf_url': None,
        }
    ])

    payload = citation_graph.citation_neighborhood('seed-paper', limit=2)

    assert payload['status'] == 'available'
    assert payload['source_statuses'][0]['endpoint'] == 'citations'
    assert payload['source_statuses'][0]['status'] == 'available'
    assert payload['summary']['top_citing'][0]['source_id'] == 'citing-1'
    assert payload['summary']['top_citing'][0]['authors'] == ['Alice Example', 'Bob Example', 'Carol Example']
    assert payload['summary']['top_cited'][0]['source_id'] == 'cited-1'
    assert payload['summary']['top_cited'][0]['ranking_score'] > 0


def test_citation_neighborhood_reports_partial_unavailability(monkeypatch) -> None:
    monkeypatch.setattr(citation_graph, 'papers_citing', lambda paper_id, limit=5: (_ for _ in ()).throw(urllib.error.HTTPError('https://example.com', 429, 'rate limited', None, None)))
    monkeypatch.setattr(citation_graph, 'papers_cited_by', lambda paper_id, limit=5: [])

    payload = citation_graph.citation_neighborhood('seed-paper', limit=2)

    assert payload['status'] == 'empty'
    assert payload['source_statuses'][0]['endpoint'] == 'citations'
    assert payload['source_statuses'][0]['status'] == 'unavailable'
    assert payload['source_statuses'][0]['code'] == 429
    assert payload['source_statuses'][1]['endpoint'] == 'references'
    assert payload['source_statuses'][1]['status'] == 'available'


def test_citation_neighborhood_reports_full_unavailability(monkeypatch) -> None:
    monkeypatch.setattr(citation_graph, 'papers_citing', lambda paper_id, limit=5: (_ for _ in ()).throw(RuntimeError('down')))
    monkeypatch.setattr(citation_graph, 'papers_cited_by', lambda paper_id, limit=5: (_ for _ in ()).throw(RuntimeError('down too')))

    payload = citation_graph.citation_neighborhood('seed-paper', limit=2)

    assert payload['status'] == 'unavailable'
    assert payload['citing'] == []
    assert payload['cited'] == []
    assert [row['status'] for row in payload['source_statuses']] == ['unavailable', 'unavailable']


def test_papers_citing_normalizes_semanticscholar_results(monkeypatch) -> None:
    def fake_fetch_json(url: str) -> dict:
        assert '/references?' in url
        return {
            'data': [
                {
                    'citedPaper': {
                        'paperId': 'cited-1',
                        'title': 'Referenced Paper',
                        'authors': [{'name': 'Bob Example'}],
                        'year': 2020,
                        'citationCount': 9,
                        'externalIds': {},
                        'url': 'https://semanticscholar.org/paper/cited-1',
                    }
                }
            ]
        }

    monkeypatch.setattr(citation_graph, '_fetch_json', fake_fetch_json)
    results = citation_graph.papers_cited_by('source-paper', limit=1)

    assert results[0]['source'] == 'semanticscholar'
    assert results[0]['source_id'] == 'cited-1'
    assert results[0]['title'] == 'Referenced Paper'
    assert results[0]['authors'] == ['Bob Example']
