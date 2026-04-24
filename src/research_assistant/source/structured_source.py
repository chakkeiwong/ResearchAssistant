from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SOURCE_PRIORITY = {
    'arxiv_latex': 1,
    'publisher_xml': 2,
    'grobid_tei': 3,
    'pdf_parser': 4,
    'pdf_text': 5,
    'metadata_only': 6,
}


@dataclass
class StructuredSourceRecord:
    paper_id: str
    source_type: str
    status: str
    primary_for_audit: bool = False
    artifact_root: str | None = None
    original_source_path: str | None = None
    flattened_source_path: str | None = None
    sections: list[dict[str, Any]] = field(default_factory=list)
    equations: list[dict[str, Any]] = field(default_factory=list)
    theorem_like_blocks: list[dict[str, Any]] = field(default_factory=list)
    labels: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    bibliography: list[dict[str, Any]] = field(default_factory=list)
    macros: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    limitations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'StructuredSourceRecord':
        return cls(**data)


def source_record_path(source_root: Path, paper_id: str) -> Path:
    return source_root / 'records' / f'{paper_id}.json'


def arxiv_artifact_root(source_root: Path, paper_id: str) -> Path:
    return source_root / 'arxiv' / paper_id


def source_priority(source_type: str) -> int:
    return SOURCE_PRIORITY.get(source_type, 999)
