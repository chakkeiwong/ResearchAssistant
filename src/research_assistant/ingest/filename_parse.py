from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class FilenameHints:
    raw_name: str
    probable_title: str
    probable_author: str | None = None
    probable_year: int | None = None
    duplicate_marker: str | None = None


def parse_paper_filename(path_or_name: str) -> FilenameHints:
    name = Path(path_or_name).name
    stem = Path(name).stem.strip()

    duplicate_marker = None
    duplicate_match = re.search(r"\s+\((\d+)\)$", stem)
    if duplicate_match:
        duplicate_marker = duplicate_match.group(1)
        stem = stem[: duplicate_match.start()].strip()

    year = None
    year_match = re.search(r"\((\d{2}|\d{4})\)\s*$", stem)
    if year_match:
        raw_year = year_match.group(1)
        y = int(raw_year)
        year = y if y > 100 else (2000 + y if y < 40 else 1900 + y)
        stem_without_year = stem[: year_match.start()].strip()
    else:
        stem_without_year = stem

    probable_author = None
    probable_title = stem_without_year
    tokens = stem_without_year.rsplit(" ", 1)
    if len(tokens) == 2 and re.match(r"^[A-Z][A-Za-z\-]+$", tokens[1]):
        probable_title, probable_author = tokens[0].strip(), tokens[1].strip()

    return FilenameHints(
        raw_name=name,
        probable_title=probable_title.strip(),
        probable_author=probable_author,
        probable_year=year,
        duplicate_marker=duplicate_marker,
    )
