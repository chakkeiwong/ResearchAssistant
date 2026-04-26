from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import json


@dataclass
class LinkRecord:
    id: str
    paper_id: str
    target_type: str
    target: str
    relationship: str
    confidence_level: str = "medium"
    review_status: str = "draft"
    source_type: str = "paper"
    source_ref: str | None = None
    target_ref: str | None = None
    evidence_refs: list[dict[str, Any]] | None = None
    limitations: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LinkRecord":
        return cls(**data)
