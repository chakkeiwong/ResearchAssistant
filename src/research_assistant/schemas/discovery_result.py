from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DiscoveryResult:
    source: str
    source_id: str | None = None
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str = ''
    citation_count: int = 0
    influential_citation_count: int | None = None
    open_access_pdf_url: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
