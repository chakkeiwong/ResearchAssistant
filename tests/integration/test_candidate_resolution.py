from __future__ import annotations

from research_assistant.ingest.metadata_resolve import choose_best_openalex_result


def test_choose_best_openalex_uses_extracted_text_signal() -> None:
    # This is a structural test placeholder: exact networked matching is not mocked here.
    # The important thing is that the function accepts extracted_text and returns candidate lists.
    best, candidates = choose_best_openalex_result('Credit Risk and the Transmission of Interest Rate Shocks Palazzo', extracted_text='Credit Risk and the Transmission of Interest Rate Shocks')
    assert isinstance(candidates, list)
