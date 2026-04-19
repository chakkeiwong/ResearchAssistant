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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LinkRecord":
        return cls(**data)
