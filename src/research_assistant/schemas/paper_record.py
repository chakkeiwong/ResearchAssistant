from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import json


@dataclass
class PaperRecord:
    id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    source_url: str | None = None
    abstract: str = ""
    method_family: list[str] = field(default_factory=list)
    main_contribution: str = ""
    mathematical_core: str = ""
    assumptions: list[str] = field(default_factory=list)
    exactness_status: str = "unknown"
    invertibility_mechanism: str | None = None
    jacobian_handling: str | None = None
    known_defects: list[str] = field(default_factory=list)
    known_remedies: list[str] = field(default_factory=list)
    scientific_relevance: str = ""
    domain_relevance: str = ""
    implementation_implications: list[str] = field(default_factory=list)
    technical_audit: dict[str, Any] = field(default_factory=dict)
    linked_code_files: list[str] = field(default_factory=list)
    linked_doc_sections: list[str] = field(default_factory=list)
    reviewer_objections: list[str] = field(default_factory=list)
    reviewer_responses: list[str] = field(default_factory=list)
    confidence_level: str = "low"
    curation_status: str = "draft"
    metadata_confidence: str = "low"
    identity_source: str = "unknown"
    review_status: str = "needs_review"
    review_summary: dict[str, Any] = field(default_factory=dict)
    requires_manual_review: bool = True
    candidate_metadata_sources: dict[str, Any] = field(default_factory=dict)
    merge_notes: list[str] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperRecord":
        return cls(**data)
