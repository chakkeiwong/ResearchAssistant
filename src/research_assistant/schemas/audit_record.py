from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import json


@dataclass
class AuditRecord:
    id: str
    claim: str
    cited_papers: list[str] = field(default_factory=list)
    support_classification: str = "insufficient_evidence"
    evidence_summary: str = ""
    limitations: list[str] = field(default_factory=list)
    reviewer_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditRecord":
        return cls(**data)
