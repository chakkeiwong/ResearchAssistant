from __future__ import annotations

from research_assistant.ingest.metadata_resolve import should_merge_crossref


def test_should_not_merge_unrelated_crossref() -> None:
    openalex = {'display_name': 'NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport'}
    crossref = {'title': ['The General Applicability of Hamiltonian Neural Networks to Speed up HMC']}
    should_merge, note, score = should_merge_crossref('NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport', openalex, crossref)
    assert should_merge is False
    assert score < 0.88
