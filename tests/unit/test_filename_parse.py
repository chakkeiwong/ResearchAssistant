from __future__ import annotations

from research_assistant.ingest.filename_parse import parse_paper_filename


def test_parse_title_author_year_pattern() -> None:
    hints = parse_paper_filename('Credit Risk and the Transmission of Interest Rate Shocks Palazzo(20).pdf')
    assert hints.probable_title == 'Credit Risk and the Transmission of Interest Rate Shocks'
    assert hints.probable_author == 'Palazzo'
    assert hints.probable_year == 2020


def test_parse_duplicate_marker() -> None:
    hints = parse_paper_filename('rarely-switching linear bandits Lansdell(19) (1).pdf')
    assert hints.duplicate_marker == '1'
    assert hints.probable_year == 2019
