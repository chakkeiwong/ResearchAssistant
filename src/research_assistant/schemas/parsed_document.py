from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import json


@dataclass
class ParsedDocument:
    parser_name: str
    parser_version: str = "unknown"
    title_candidates: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    body_text: str = ""
    body_markdown: str = ""
    section_headings: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    parse_status: str = "partial"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


@dataclass
class ReconciledDocument:
    consensus_title: str | None = None
    consensus_authors: list[str] = field(default_factory=list)
    consensus_abstract: str | None = None
    parser_agreement: dict[str, Any] = field(default_factory=dict)
    disagreements: list[str] = field(default_factory=list)
    parse_confidence: str = "low"
    requires_manual_review: bool = True
    parser_outputs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
