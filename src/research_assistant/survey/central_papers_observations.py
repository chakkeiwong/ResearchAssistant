"""Strict observation schemas and offline capability for central-paper campaigns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from research_assistant.survey.mission_state import MissionStateError, sha256_bytes
from research_assistant.survey.topic_contract import topic_contract_sha256


OBSERVATION_SCHEMA = "ra-survey-central-papers-observations-v1"
CAPABILITY_MANIFEST_SCHEMA = "ra-survey-central-papers-capability-v1"
_HEX = set("0123456789abcdef")


def _fail(message: str) -> None:
    raise MissionStateError("invalid_central_papers_observations", message)


def _text(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"{field} must be nonempty text")
    return " ".join(value.split())


def _strings(value: Any, field: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        _fail(f"{field} must be a list")
    rows = sorted({_text(item, f"{field}[]") for item in value})
    if len(rows) != len(value) or (not allow_empty and not rows):
        _fail(f"{field} must contain unique sorted values")
    return rows


def _digest(value: Any, field: str) -> str:
    text = _text(value, field)
    if len(text) != 64 or any(character not in _HEX for character in text):
        _fail(f"{field} must be lowercase SHA-256")
    return text


def _exact(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        _fail(f"{field} fields are not exact")
    return value


class CentralPapersCapability(Protocol):
    name: str
    fingerprint: str
    network_required: bool

    def collect(self, topic_contract: dict[str, Any], budget: dict[str, int]) -> dict[str, Any]: ...


def capability_manifest(capability: CentralPapersCapability) -> dict[str, Any]:
    return validate_capability_manifest({
        "schema_version": CAPABILITY_MANIFEST_SCHEMA,
        "capability_name": _text(capability.name, "capability.name"),
        "capability_fingerprint": _digest(capability.fingerprint, "capability.fingerprint"),
        "network_required": capability.network_required,
        "observation_schema": OBSERVATION_SCHEMA,
        "benchmark_labels_consumed": False,
    })


def validate_capability_manifest(
    value: Any, *, expected_fingerprint: str | None = None
) -> dict[str, Any]:
    row = _exact(value, {
        "schema_version", "capability_name", "capability_fingerprint",
        "network_required", "observation_schema", "benchmark_labels_consumed",
    }, "capability_manifest")
    if row["schema_version"] != CAPABILITY_MANIFEST_SCHEMA:
        _fail("capability manifest schema is unsupported")
    fingerprint = _digest(row["capability_fingerprint"], "capability_fingerprint")
    if expected_fingerprint is not None and fingerprint != expected_fingerprint:
        _fail("capability manifest fingerprint differs from campaign")
    if type(row["network_required"]) is not bool:
        _fail("capability manifest network_required must be boolean")
    if row["observation_schema"] != OBSERVATION_SCHEMA:
        _fail("capability manifest observation schema differs")
    if row["benchmark_labels_consumed"] is not False:
        _fail("capability manifest reports benchmark-label consumption")
    return {
        "schema_version": CAPABILITY_MANIFEST_SCHEMA,
        "capability_name": _text(row["capability_name"], "capability_name"),
        "capability_fingerprint": fingerprint,
        "network_required": row["network_required"],
        "observation_schema": OBSERVATION_SCHEMA,
        "benchmark_labels_consumed": False,
    }


def validate_observations(
    value: Any,
    *,
    expected_topic_contract_sha256: str | None = None,
    expected_capability_fingerprint: str | None = None,
) -> dict[str, Any]:
    row = _exact(value, {
        "schema_version", "topic_contract_sha256", "capability_fingerprint",
        "accessed_at", "discovery_status", "provider_statuses", "candidates",
        "budget_consumption", "limitations", "benchmark_labels_consumed",
    }, "observations")
    if row["schema_version"] != OBSERVATION_SCHEMA:
        _fail("observation schema is unsupported")
    contract_digest = _digest(row["topic_contract_sha256"], "topic_contract_sha256")
    capability_digest = _digest(row["capability_fingerprint"], "capability_fingerprint")
    if expected_topic_contract_sha256 is not None and contract_digest != expected_topic_contract_sha256:
        _fail("observations belong to a different topic contract")
    if expected_capability_fingerprint is not None and capability_digest != expected_capability_fingerprint:
        _fail("observations belong to a different capability")
    if row["benchmark_labels_consumed"] is not False:
        _fail("capability observations report benchmark-label consumption")
    discovery_status = _status(row["discovery_status"], "discovery_status")
    candidates = row["candidates"]
    if not isinstance(candidates, list) or len(candidates) > 300:
        _fail("candidates must be a bounded list")
    normalized = [_candidate(candidate, index) for index, candidate in enumerate(candidates)]
    paper_ids = [candidate["paper_id"] for candidate in normalized]
    if paper_ids != sorted(set(paper_ids)):
        _fail("candidate paper_ids must be unique and sorted")
    for candidate in normalized:
        if any(
            entry["paper_id"] == candidate["paper_id"]
            for entry in candidate["source"]["bibliography"]
        ):
            _fail("candidate source cannot cite itself")
        if candidate["discovery_round"] > 0 and not candidate["discovery_origins"]:
            _fail("snowball candidates require discovery origins")
    providers = row["provider_statuses"]
    if not isinstance(providers, list):
        _fail("provider_statuses must be a list")
    normalized_providers = [_provider_status(item, index) for index, item in enumerate(providers)]
    if [item["provider"] for item in normalized_providers] != sorted(
        {item["provider"] for item in normalized_providers}
    ):
        _fail("provider statuses must be unique and sorted")
    consumption = _exact(
        row["budget_consumption"],
        {"metadata_records", "metadata_requests", "source_attempts", "source_bytes"},
        "budget_consumption",
    )
    normalized_consumption = {}
    for field in sorted(consumption):
        number = consumption[field]
        if type(number) is not int or number < 0:
            _fail(f"budget_consumption.{field} must be a nonnegative integer")
        normalized_consumption[field] = number
    return {
        "schema_version": OBSERVATION_SCHEMA,
        "topic_contract_sha256": contract_digest,
        "capability_fingerprint": capability_digest,
        "accessed_at": _text(row["accessed_at"], "accessed_at"),
        "discovery_status": discovery_status,
        "provider_statuses": normalized_providers,
        "candidates": normalized,
        "budget_consumption": normalized_consumption,
        "limitations": _strings(row["limitations"], "limitations", allow_empty=False),
        "benchmark_labels_consumed": False,
    }


def _status(value: Any, field: str) -> str:
    status = _text(value, field)
    if status not in {"available", "empty", "not_available", "capped"}:
        _fail(f"{field} is unsupported")
    return status


def _candidate(value: Any, index: int) -> dict[str, Any]:
    field = f"candidates[{index}]"
    row = _exact(value, {
        "paper_id", "title", "authors", "year", "identifiers",
        "identity_status", "discovery_round", "discovery_routes",
        "discovery_origins", "citation_count", "venue_metric_status",
        "source", "safety", "forward_citation_status", "forward_citations", "limitations",
    }, field)
    paper_id = _text(row["paper_id"], f"{field}.paper_id").casefold()
    identity_status = _text(row["identity_status"], f"{field}.identity_status")
    if identity_status not in {"resolved", "conflict", "unresolved"}:
        _fail(f"{field}.identity_status is unsupported")
    round_index = row["discovery_round"]
    if type(round_index) is not int or not 0 <= round_index <= 20:
        _fail(f"{field}.discovery_round is invalid")
    year = row["year"]
    if year is not None and (type(year) is not int or not 1000 <= year <= 3000):
        _fail(f"{field}.year is invalid")
    citations = row["citation_count"]
    if citations is not None and (type(citations) is not int or citations < 0):
        _fail(f"{field}.citation_count is invalid")
    venue = _text(row["venue_metric_status"], f"{field}.venue_metric_status")
    if venue not in {"available", "not_available"}:
        _fail(f"{field}.venue_metric_status is unsupported")
    identifiers = _exact(
        row["identifiers"], {"arxiv_id", "doi", "openalex_id"}, f"{field}.identifiers"
    )
    return {
        "paper_id": paper_id,
        "title": _text(row["title"], f"{field}.title"),
        "authors": _strings(row["authors"], f"{field}.authors"),
        "year": year,
        "identifiers": {
            key: (_text(identifiers[key], f"{field}.identifiers.{key}", nullable=True) or None)
            for key in sorted(identifiers)
        },
        "identity_status": identity_status,
        "discovery_round": round_index,
        "discovery_routes": _strings(row["discovery_routes"], f"{field}.discovery_routes"),
        "discovery_origins": _strings(row["discovery_origins"], f"{field}.discovery_origins"),
        "citation_count": citations,
        "venue_metric_status": venue,
        "source": _source(row["source"], field),
        "safety": _safety(row["safety"], field),
        "forward_citation_status": _status(
            row["forward_citation_status"], f"{field}.forward_citation_status"
        ),
        "forward_citations": _strings(row["forward_citations"], f"{field}.forward_citations"),
        "limitations": _strings(row["limitations"], f"{field}.limitations", allow_empty=False),
    }


def _source(value: Any, parent: str) -> dict[str, Any]:
    field = f"{parent}.source"
    row = _exact(value, {"status", "source_type", "evidence_ref", "sections", "bibliography"}, field)
    status = _text(row["status"], f"{field}.status")
    if status not in {"available", "source_blocked", "parse_failed", "not_available"}:
        _fail(f"{field}.status is unsupported")
    if not isinstance(row["sections"], list) or len(row["sections"]) > 200:
        _fail(f"{field}.sections must be bounded")
    if not isinstance(row["bibliography"], list) or len(row["bibliography"]) > 1000:
        _fail(f"{field}.bibliography must be bounded")
    sections = [_section(item, index, field) for index, item in enumerate(row["sections"])]
    bibliography = [
        _bibliography(item, index, field) for index, item in enumerate(row["bibliography"])
    ]
    if [item["anchor_id"] for item in sections] != sorted({item["anchor_id"] for item in sections}):
        _fail(f"{field}.sections must have unique sorted anchor_ids")
    keys = [(item["paper_id"] or "", item["title"] or "") for item in bibliography]
    if keys != sorted(set(keys)):
        _fail(f"{field}.bibliography must be unique and sorted")
    if status != "available" and sections:
        _fail(f"{field}.sections require an available source")
    return {
        "status": status,
        "source_type": _text(row["source_type"], f"{field}.source_type"),
        "evidence_ref": _text(row["evidence_ref"], f"{field}.evidence_ref"),
        "sections": sections,
        "bibliography": bibliography,
    }


def _section(value: Any, index: int, parent: str) -> dict[str, Any]:
    field = f"{parent}.sections[{index}]"
    row = _exact(value, {"anchor_id", "title", "text", "evidence_ref"}, field)
    text = _text(row["text"], f"{field}.text")
    if len(text.encode("utf-8")) > 100_000:
        _fail(f"{field}.text exceeds its cap")
    return {
        "anchor_id": _text(row["anchor_id"], f"{field}.anchor_id"),
        "title": _text(row["title"], f"{field}.title"),
        "text": text,
        "evidence_ref": _text(row["evidence_ref"], f"{field}.evidence_ref"),
    }


def _bibliography(value: Any, index: int, parent: str) -> dict[str, Any]:
    field = f"{parent}.bibliography[{index}]"
    row = _exact(value, {"paper_id", "title", "evidence_ref"}, field)
    paper_id = _text(row["paper_id"], f"{field}.paper_id", nullable=True)
    title = _text(row["title"], f"{field}.title", nullable=True)
    if paper_id is None and title is None:
        _fail(f"{field} requires paper_id or title")
    return {
        "paper_id": paper_id.casefold() if paper_id else None,
        "title": title,
        "evidence_ref": _text(row["evidence_ref"], f"{field}.evidence_ref"),
    }


def _safety(value: Any, parent: str) -> dict[str, Any]:
    field = f"{parent}.safety"
    row = _exact(value, {"status", "evidence_refs", "limitations"}, field)
    status = _text(row["status"], f"{field}.status")
    if status not in {"no_issue_found", "not_checked", "quarantined"}:
        _fail(f"{field}.status is unsupported")
    evidence = _strings(row["evidence_refs"], f"{field}.evidence_refs")
    if status in {"no_issue_found", "quarantined"} and not evidence:
        _fail(f"{field}.evidence_refs are required for checked status")
    return {
        "status": status,
        "evidence_refs": evidence,
        "limitations": _strings(row["limitations"], f"{field}.limitations", allow_empty=False),
    }


def _provider_status(value: Any, index: int) -> dict[str, Any]:
    field = f"provider_statuses[{index}]"
    row = _exact(value, {"provider", "status", "detail"}, field)
    return {
        "provider": _text(row["provider"], f"{field}.provider"),
        "status": _status(row["status"], f"{field}.status"),
        "detail": _text(row["detail"], f"{field}.detail"),
    }


@dataclass(frozen=True)
class FileObservationCapability:
    path: Path
    name: str = "local_observation_bundle"
    network_required: bool = False

    @property
    def fingerprint(self) -> str:
        return sha256_bytes(self.path.resolve(strict=True).read_bytes())

    def collect(self, topic_contract: dict[str, Any], budget: dict[str, int]) -> dict[str, Any]:
        del budget
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MissionStateError(
                "invalid_central_papers_observations", "observation bundle is not readable JSON"
            ) from exc
        if not isinstance(value, dict):
            _fail("observation bundle must be an object")
        value = {**value, "capability_fingerprint": self.fingerprint}
        return validate_observations(
            value,
            expected_topic_contract_sha256=topic_contract_sha256(topic_contract),
            expected_capability_fingerprint=self.fingerprint,
        )


__all__ = [
    "CAPABILITY_MANIFEST_SCHEMA", "OBSERVATION_SCHEMA", "CentralPapersCapability",
    "FileObservationCapability", "capability_manifest", "validate_capability_manifest",
    "validate_observations",
]
