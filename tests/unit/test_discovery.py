from __future__ import annotations

from research_assistant.query import citation_graph


def test_related_papers_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(citation_graph, 'discover_papers', lambda topic: [])
    assert isinstance(citation_graph.related_papers('transport maps hmc'), list)


def test_papers_citing_normalizes_semanticscholar_results(monkeypatch) -> None:
    def fake_fetch_json(url: str) -> dict:
        assert '/citations?' in url
        assert 'limit=1' in url
        return {
            'data': [
                {
                    'citingPaper': {
                        'paperId': 'citing-1',
                        'title': 'Citing Paper',
                        'authors': [{'name': 'Alice Example'}],
                        'year': 2025,
                        'citationCount': 3,
                        'externalIds': {'DOI': '10.1/citing'},
                        'openAccessPdf': {'url': 'https://example.com/citing.pdf'},
                        'url': 'https://semanticscholar.org/paper/citing-1',
                    }
                }
            ]
        }

    monkeypatch.setattr(citation_graph, '_fetch_json', fake_fetch_json)
    results = citation_graph.papers_citing('source-paper', limit=1)

    assert results[0]['source'] == 'semanticscholar'
    assert results[0]['source_id'] == 'citing-1'
    assert results[0]['title'] == 'Citing Paper'
    assert results[0]['authors'] == ['Alice Example']
    assert results[0]['open_access_pdf_url'] == 'https://example.com/citing.pdf'


def test_papers_cited_by_normalizes_semanticscholar_results(monkeypatch) -> None:
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
