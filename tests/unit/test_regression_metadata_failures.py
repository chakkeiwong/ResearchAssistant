from __future__ import annotations

import json
from pathlib import Path

from research_assistant.ingest.metadata_resolve import merge_metadata
from research_assistant.summarize.draft_summary import build_draft_summary

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_neutra_false_positive_crossref_is_quarantined() -> None:
    openalex = load_fixture('openalex_neutra.json')
    crossref = load_fixture('crossref_false_positive_neutra.json')
    metadata = merge_metadata(
        'NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport',
        openalex,
        crossref,
        {},
        openalex_candidates=[{'score': 1.0, 'title': openalex['display_name']}],
        crossref_candidates=[{'score': 0.57, 'title': crossref['title'][0]}],
    )
    assert metadata['crossref'] == {}
    assert metadata['crossref_candidate']['DOI'] == '10.1002/pamm.202200188'
    assert metadata['metadata_confidence'] == 'medium'


def test_arxiv_authors_override_bad_openalex_authors() -> None:
    metadata = merge_metadata(
        'Deep Learning Hamiltonian Monte Carlo',
        load_fixture('openalex_dlhmc_bad_authors.json'),
        {},
        load_fixture('arxiv_dlhmc.json'),
        openalex_candidates=[{'score': 1.0, 'title': 'Deep Learning Hamiltonian Monte Carlo'}],
    )
    rec = build_draft_summary('paper_dlhmc', metadata, '')
    assert rec.authors == ['Sam Foreman', 'Xiao-Yong Jin', 'James C. Osborn']
    assert rec.provenance['authors'] == 'arxiv'
    assert rec.metadata_confidence == 'high'


def test_weak_openalex_match_gets_low_confidence() -> None:
    wrong_openalex = {
        'display_name': 'Feverish Stock Price Reactions to COVID-19*',
        'publication_year': 2020,
        'authorships': [{'author': {'display_name': 'Stefano Ramelli'}}],
    }
    metadata = merge_metadata(
        'Credit Risk and the Transmission of Interest Rate Shocks Palazzo',
        wrong_openalex,
        {},
        {},
        openalex_candidates=[{'score': 0.372, 'title': wrong_openalex['display_name']}],
    )
    assert metadata['metadata_confidence'] == 'low'
    assert any('manual review recommended' in note for note in metadata['merge_notes'])
