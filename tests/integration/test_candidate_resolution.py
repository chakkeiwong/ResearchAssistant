from __future__ import annotations

from research_assistant.ingest import metadata_resolve
from research_assistant.ingest.metadata_resolve import choose_best_openalex_result


def test_choose_best_openalex_uses_extracted_text_signal(monkeypatch) -> None:
    monkeypatch.setattr(metadata_resolve, '_fetch_json', lambda url: {
        'results': [
            {
                'id': 'https://openalex.org/W1',
                'display_name': 'Credit Risk and the Transmission of Interest Rate Shocks',
                'publication_year': 2020,
            },
            {
                'id': 'https://openalex.org/W2',
                'display_name': 'Wrong Paper',
                'publication_year': 2019,
            },
        ]
    })
    best, candidates = choose_best_openalex_result(
        'Credit Risk and the Transmission of Interest Rate Shocks Palazzo',
        extracted_text='Credit Risk and the Transmission of Interest Rate Shocks',
    )
    assert best['display_name'] == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert isinstance(candidates, list)
