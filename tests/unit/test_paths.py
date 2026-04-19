from __future__ import annotations

from pathlib import Path

from research_assistant.paths import slugify
from research_assistant.ingest.source_manifest import canonical_paper_id


def test_slugify_basic() -> None:
    assert slugify('NeuTra-lizing Bad Geometry') == 'neutra_lizing_bad_geometry'


def test_canonical_paper_id_is_stable() -> None:
    a = canonical_paper_id('https://arxiv.org/abs/1903.03704')
    b = canonical_paper_id('https://arxiv.org/abs/1903.03704')
    assert a == b
    assert a.startswith('paper_')
