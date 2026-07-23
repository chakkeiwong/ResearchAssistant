from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    sha256_bytes,
)


VENUE_METRICS_SCHEMA = "ra-survey-venue-metrics-registry-v1"
VENUE_METRIC_NAME = "journal_impact_factor"
VENUE_STATUS = {"available", "not_available", "not_applicable", "ambiguous"}


def unavailable_registry() -> dict[str, Any]:
    """Return an explicit empty registry for optional metric enrichment.

    The sentinel is valid registry data, but it carries no metric values.  It
    lets ranking remain deterministic without turning missing venue data into
    a discovery blocker or a fabricated zero.
    """
    source = {"reference": "not_provided", "accessed_at": "1970-01-01T00:00:00+00:00"}
    return {
        "schema_version": VENUE_METRICS_SCHEMA,
        "registry_id": "not_available",
        "metric_name": VENUE_METRIC_NAME,
        "registry_source": source,
        "venues": [],
        "paper_venues": [],
    }


def _fail(message: str) -> None:
    raise MissionStateError("invalid_venue_metrics_registry", message)


def _text(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"{field} must be a non-empty string")
    return " ".join(value.split())


def _date(value: Any, field: str) -> str:
    text = _text(value, field)
    assert text is not None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissionStateError("invalid_venue_metrics_registry", f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        _fail(f"{field} must include a timezone")
    return text


def _source(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"reference", "accessed_at"}:
        _fail(f"{field} source fields are not exact")
    reference = _text(value["reference"], f"{field}.reference")
    accessed_at = _date(value["accessed_at"], f"{field}.accessed_at")
    assert reference is not None
    return {"reference": reference, "accessed_at": accessed_at}


def validate_registry(value: Any) -> dict[str, Any]:
    expected = {"schema_version", "registry_id", "metric_name", "registry_source", "venues", "paper_venues"}
    if not isinstance(value, dict) or set(value) != expected:
        _fail("registry fields are not exact")
    if value["schema_version"] != VENUE_METRICS_SCHEMA:
        _fail("unsupported registry schema")
    registry_id = _text(value["registry_id"], "registry_id")
    metric_name = _text(value["metric_name"], "metric_name")
    if metric_name != VENUE_METRIC_NAME:
        _fail(f"metric_name must be {VENUE_METRIC_NAME}")
    registry_source = _source(value["registry_source"], "registry_source")
    venues = value["venues"]
    if not isinstance(venues, list):
        _fail("venues must be a list")
    normalized_venues: list[dict[str, Any]] = []
    venue_keys: set[str] = set()
    for index, row in enumerate(venues):
        field = f"venues[{index}]"
        if not isinstance(row, dict) or set(row) != {
            "venue_key", "display_name", "status", "metric_value", "metric_year", "source"
        }:
            _fail(f"{field} fields are not exact")
        venue_key = _text(row["venue_key"], f"{field}.venue_key")
        display_name = _text(row["display_name"], f"{field}.display_name")
        status = _text(row["status"], f"{field}.status")
        assert venue_key is not None and display_name is not None and status is not None
        if venue_key.casefold() in venue_keys:
            _fail(f"duplicate venue_key: {venue_key}")
        venue_keys.add(venue_key.casefold())
        if status not in VENUE_STATUS:
            _fail(f"{field}.status is invalid")
        metric_value = row["metric_value"]
        metric_year = row["metric_year"]
        if status == "available":
            if isinstance(metric_value, bool) or not isinstance(metric_value, (int, float)) or metric_value <= 0:
                _fail(f"{field}.metric_value must be positive when available")
            if type(metric_year) is not int or not 1900 <= metric_year <= 3000:
                _fail(f"{field}.metric_year is invalid when available")
        elif metric_value is not None or metric_year is not None:
            _fail(f"{field} unavailable metrics must be null")
        normalized_venues.append({
            "venue_key": venue_key,
            "display_name": display_name,
            "status": status,
            "metric_value": None if metric_value is None else float(metric_value),
            "metric_year": metric_year,
            "source": _source(row["source"], f"{field}.source"),
        })
    paper_venues = value["paper_venues"]
    if not isinstance(paper_venues, list):
        _fail("paper_venues must be a list")
    normalized_paper_venues: list[dict[str, str]] = []
    paper_keys: set[str] = set()
    for index, row in enumerate(paper_venues):
        field = f"paper_venues[{index}]"
        if not isinstance(row, dict) or set(row) != {"paper_key", "venue_key"}:
            _fail(f"{field} fields are not exact")
        paper_key = _text(row["paper_key"], f"{field}.paper_key")
        venue_key = _text(row["venue_key"], f"{field}.venue_key")
        assert paper_key is not None and venue_key is not None
        if paper_key.casefold() in paper_keys:
            _fail(f"duplicate paper_key: {paper_key}")
        if venue_key.casefold() not in venue_keys:
            _fail(f"{field}.venue_key is not present in venues")
        paper_keys.add(paper_key.casefold())
        normalized_paper_venues.append({"paper_key": paper_key, "venue_key": venue_key})
    normalized_paper_venues.sort(key=lambda row: row["paper_key"].casefold())
    normalized_venues.sort(key=lambda row: row["venue_key"].casefold())
    return {
        "schema_version": VENUE_METRICS_SCHEMA,
        "registry_id": registry_id,
        "metric_name": metric_name,
        "registry_source": registry_source,
        "venues": normalized_venues,
        "paper_venues": normalized_paper_venues,
    }


def load_registry(path: Path) -> tuple[dict[str, Any], str]:
    lexical = path.expanduser()
    if lexical.is_symlink():
        _fail("registry must not be a symlink")
    path = lexical.resolve(strict=True)
    if not path.is_file():
        _fail("registry must be a regular file")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_venue_metrics_registry", "registry is not valid JSON") from exc
    canonical = canonical_json_bytes(value)
    if raw not in {canonical, canonical + b"\n"}:
        _fail("registry JSON must be canonical with at most one terminal newline")
    normalized = validate_registry(value)
    return normalized, sha256_bytes(canonical)


def metric_by_paper(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    venues = {row["venue_key"].casefold(): row for row in registry["venues"]}
    return {
        row["paper_key"]: venues[row["venue_key"].casefold()]
        for row in registry["paper_venues"]
    }


def metric_by_venue(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["venue_key"].casefold(): row for row in registry["venues"]}


__all__ = [
    "VENUE_METRICS_SCHEMA",
    "VENUE_METRIC_NAME",
    "load_registry",
    "metric_by_paper",
    "metric_by_venue",
    "validate_registry",
    "unavailable_registry",
]
