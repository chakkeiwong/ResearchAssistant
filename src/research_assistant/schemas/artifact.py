from __future__ import annotations

import hashlib
import json
from typing import Any

from research_assistant.core_utils import utc_now_iso

SCHEMA_VERSION = "industrial-platform-v1"
REVIEW_STATUS_REQUIRES_HUMAN = "requires_human_review"

BASE_ARTIFACT_FIELDS = {
    "schema_version",
    "artifact_id",
    "artifact_type",
    "paper_id",
    "created_at",
    "provenance",
    "review_status",
    "requires_human_review",
    "limitations",
}


def stable_id(prefix: str, *parts: Any) -> str:
    payload = json.dumps([str(part) for part in parts], sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def base_artifact(
    *,
    artifact_type: str,
    artifact_id: str,
    paper_id: str | None = None,
    provenance: dict[str, Any] | None = None,
    limitations: list[Any] | None = None,
    review_status: str = REVIEW_STATUS_REQUIRES_HUMAN,
    requires_human_review: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "paper_id": paper_id,
        "created_at": utc_now_iso(),
        "provenance": provenance or {},
        "review_status": review_status,
        "requires_human_review": requires_human_review,
        "limitations": limitations or [],
    }


def has_base_artifact_fields(payload: dict[str, Any]) -> bool:
    return BASE_ARTIFACT_FIELDS.issubset(payload)
