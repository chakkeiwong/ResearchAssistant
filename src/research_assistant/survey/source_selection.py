"""Deterministic selection of lawful source artifacts for survey evidence.

This module deliberately does not download or interpret papers.  It reconciles
metadata selection with source availability and records every substitution, so
source transport cannot silently change the survey's intended coverage.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable


SELECTION_POLICY = "available_selected_then_same_stratum_then_shared_purpose_then_rank"
VERSION_POLICY = "lawful_available_closest_publication_then_latest"
SOURCE_SELECTION_SCHEMA = "ra-survey-source-selection-reconciliation-v1"
_RELATION_RANK = {
    "published": 0,
    "version_of_record": 0,
    "accepted_manuscript": 1,
    "author_manuscript": 1,
    "author_preprint": 2,
    "repository_copy": 3,
    "repository_preprint": 3,
    "preprint": 3,
}


def _candidate_key(row: dict[str, Any]) -> str:
    for key in ("candidate_id", "paper_key", "identifier", "id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("candidate requires candidate_id, paper_key, identifier, or id")


def _stratum(row: dict[str, Any]) -> str:
    for key in ("stratum", "purpose", "category"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().casefold()
    purposes = row.get("query_purposes") or row.get("roles")
    if isinstance(purposes, (list, tuple)) and purposes:
        values = sorted(
            str(value).strip().casefold() for value in purposes if str(value).strip()
        )
        if values:
            return values[0]
    return "unspecified"


def _rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
    rank = 10**9
    for key in ("combined_nomination_rank", "nomination_rank", "citation_priority_rank"):
        value = row.get(key)
        if isinstance(value, int) and value >= 1:
            rank = value
            break
    citation = row.get("citation_count")
    if not isinstance(citation, int) or citation < 0:
        citation = -1
    return (rank, -citation, str(row.get("title", "")).casefold(), _candidate_key(row))


def _availability_map(outcomes: Any) -> dict[str, dict[str, Any]]:
    if isinstance(outcomes, dict):
        iterable: Iterable[tuple[str, Any]] = outcomes.items()
    elif isinstance(outcomes, list):
        iterable = ((_candidate_key(row), row) for row in outcomes if isinstance(row, dict))
    else:
        raise ValueError("availability outcomes must be a mapping or list")
    result: dict[str, dict[str, Any]] = {}
    for key, value in iterable:
        if isinstance(value, str):
            value = {"outcome_status": value}
        if not isinstance(value, dict):
            raise ValueError("availability outcome must be an object or status string")
        result[str(key)] = dict(value)
        for alias in ("candidate_id", "paper_key", "identifier", "id"):
            alias_value = value.get(alias)
            if isinstance(alias_value, str) and alias_value.strip():
                result[alias_value.strip()] = dict(value)
    return result


def _is_available(row: dict[str, Any] | None) -> bool:
    if row is None:
        return False
    status = row.get("outcome_status", row.get("status"))
    if status == "duplicate":
        return isinstance(row.get("source_record_path"), str) and bool(row["source_record_path"])
    return row.get("available") is True or status in {"available", "lawful_available"}


def _source_identity(row: dict[str, Any] | None, *, fallback: str) -> str:
    if row is None:
        return f"candidate:{fallback}"
    for key in (
        "source_record_sha256",
        "source_identifier",
        "source_record_path",
        "final_url",
    ):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return f"{key}:{value.strip().casefold()}"
    return f"candidate:{fallback}"


def select_available_sources(
    selected_candidates: list[dict[str, Any]],
    eligible_candidates: list[dict[str, Any]],
    availability_outcomes: dict[str, Any] | list[dict[str, Any]],
    *,
    seed_cap: int | None = None,
    versions_by_candidate: dict[str, list[dict[str, Any]]] | None = None,
    publication_dates_by_candidate: dict[str, str | int | None] | None = None,
) -> dict[str, Any]:
    """Retain available selections and deterministically fill source gaps.

    Replacements are drawn from the same stratum first. A generic fallback
    prefers shared query purposes/roles, then stable candidate ranking;
    every fallback is explicitly labelled and never changes technical support.
    """
    if not isinstance(selected_candidates, list) or not isinstance(eligible_candidates, list):
        raise ValueError("candidate inputs must be lists")
    outcomes = _availability_map(availability_outcomes)
    selected = list(selected_candidates)
    eligible_by_key = {_candidate_key(row): row for row in eligible_candidates}
    selected_keys = {_candidate_key(row) for row in selected}
    retained: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    substitutions: list[dict[str, Any]] = []
    selected_versions: dict[str, dict[str, Any]] = {}
    used = set(selected_keys)
    used_source_identities: set[str] = set()
    for row in selected:
        key = _candidate_key(row)
        availability = outcomes.get(key)
        if _is_available(availability):
            retained.append(dict(row))
            used_source_identities.add(_source_identity(availability, fallback=key))
        else:
            unavailable.append({
                "candidate": dict(row),
                "candidate_key": key,
                "availability": dict(availability or {"outcome_status": "not_observed"}),
            })

    version_inputs = versions_by_candidate or {}
    publication_dates = publication_dates_by_candidate or {}
    for row in retained:
        key = _candidate_key(row)
        versions = version_inputs.get(key)
        if versions:
            selected_versions[key] = choose_preferred_source_version(
                versions,
                publication_dates.get(key, row.get("publication_date", row.get("year"))),
            )

    pool = sorted(
        (
            row
            for key, row in eligible_by_key.items()
            if key not in used
            and _is_available(outcomes.get(key))
            and _source_identity(outcomes.get(key), fallback=key) not in used_source_identities
        ),
        key=_rank_key,
    )
    for missing in unavailable:
        source = missing["candidate"]
        source_stratum = _stratum(source)
        same = [row for row in pool if _stratum(row) == source_stratum]
        shared = [
            row for row in pool
            if set(_purpose_values(row)) & set(_purpose_values(source))
        ]
        candidates = same or shared or sorted(
            pool,
            key=_rank_key,
        )
        replacement = candidates[0] if candidates else None
        if replacement is None:
            continue
        replacement_key = _candidate_key(replacement)
        pool = [row for row in pool if _candidate_key(row) != replacement_key]
        used.add(replacement_key)
        used_source_identities.add(
            _source_identity(outcomes.get(replacement_key), fallback=replacement_key)
        )
        retained.append(dict(replacement))
        versions = version_inputs.get(replacement_key)
        if versions:
            selected_versions[replacement_key] = choose_preferred_source_version(
                versions,
                publication_dates.get(replacement_key, replacement.get("publication_date", replacement.get("year"))),
            )
        substitutions.append({
            "unavailable_candidate_key": missing["candidate_key"],
            "replacement_candidate_key": replacement_key,
            "original_stratum": source_stratum,
            "replacement_stratum": _stratum(replacement),
            "fallback": (
                "same_stratum" if same
                else "shared_purpose" if shared
                else "ranked_fallback"
            ),
            "reason": "selected_source_unavailable",
        })
        pool = [
            row
            for row in pool
            if _source_identity(
                outcomes.get(_candidate_key(row)),
                fallback=_candidate_key(row),
            ) not in used_source_identities
        ]
    retained.sort(key=_rank_key)
    if seed_cap is not None:
        if type(seed_cap) is not int or seed_cap < 0:
            raise ValueError("seed_cap must be a nonnegative integer")
        retained = retained[:seed_cap]
    return {
        "retained_selected": retained,
        "unavailable_selected": unavailable,
        "substitutions": substitutions,
        "unreplaced_unavailable": [
            row["candidate_key"]
            for row in unavailable
            if row["candidate_key"] not in {item["unavailable_candidate_key"] for item in substitutions}
        ],
        "selection_policy": SELECTION_POLICY,
        "selected_versions": selected_versions,
        "source_availability_summary": {
            "selected_count": len(selected),
            "retained_count": len(retained),
            "unavailable_selected_count": len(unavailable),
            "substitution_count": len(substitutions),
        },
    }


def _purpose_values(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("query_purposes", "roles", "purposes"):
        value = row.get(key)
        if isinstance(value, (list, tuple)):
            values.extend(str(item).strip().casefold() for item in value if str(item).strip())
    return values or [_stratum(row)]


def _parse_date(value: Any) -> date | None:
    if isinstance(value, int) and 1000 <= value <= 3000:
        return date(value, 1, 1)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    if len(text) == 4 and text.isdigit() and 1000 <= int(text) <= 3000:
        return date(int(text), 1, 1)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def choose_preferred_source_version(
    versions: list[dict[str, Any]],
    publication_date: str | int | None = None,
) -> dict[str, Any]:
    """Choose the latest lawful version closest to publication deterministically."""
    if not isinstance(versions, list) or not versions:
        raise ValueError("versions must be a nonempty list")
    publication = _parse_date(publication_date)
    eligible: list[tuple[int, int, date, tuple[str, str], dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    for version in versions:
        if not isinstance(version, dict):
            raise ValueError("each version must be an object")
        relation = str(
            version.get("version_relation", version.get("relation", "preprint"))
        ).casefold()
        status = version.get("status")
        lawful = version.get("lawful") is not False
        conflicted = version.get("metadata_conflict") is True or version.get("quarantined") is True
        available = lawful and not conflicted and (
            version.get("available") is True or status in {"available", "lawful_available"}
        )
        if not available:
            reason = "metadata_conflict_or_quarantine" if conflicted else "unavailable_or_unlawful"
            rejected.append({"version": dict(version), "reason": reason})
            continue
        version_date = _parse_date(version.get("version_date", version.get("date"))) or date.min
        distance = _RELATION_RANK.get(relation, 3)
        if publication is not None and version_date != date.min:
            distance_key = abs((version_date - publication).days)
        else:
            distance_key = 0
        eligible.append((
            distance,
            distance_key,
            version_date,
            (
                str(version.get("source_priority", "")),
                str(version.get("url", version.get("identifier", ""))),
            ),
            dict(version),
        ))
    if not eligible:
        raise ValueError("no lawful available source version")
    eligible.sort(key=lambda item: (item[0], item[1], -item[2].toordinal(), item[3]))
    _, _, selected_date, _, selected = eligible[0]
    alternates = [item[4] for item in eligible[1:]] + [item["version"] for item in rejected]
    selected["selection_reason"] = (
        "lawful available version closest to publication, latest on an equal-distance tie"
    )
    selected["publication_date"] = publication_date
    selected["version_date"] = selected.get("version_date", selected_date.isoformat() if selected_date != date.min else None)
    selected["version_relation"] = selected.get("version_relation", selected.get("relation", "preprint"))
    publication_mismatch = selected_date != date.min and publication is not None and selected_date != publication
    return {
        "selected_version": selected,
        "alternate_versions": alternates,
        "publication_date": publication_date,
        "selection_policy": VERSION_POLICY,
        "selection_reason": selected["selection_reason"],
        "publication_date_mismatch": publication_mismatch,
    }


def build_source_selection_ledger(
    *,
    topic: str,
    selected_candidates: list[dict[str, Any]],
    eligible_candidates: list[dict[str, Any]],
    availability_outcomes: dict[str, Any] | list[dict[str, Any]],
    seed_cap: int | None = None,
    versions_by_candidate: dict[str, list[dict[str, Any]]] | None = None,
    publication_dates_by_candidate: dict[str, str | int | None] | None = None,
) -> dict[str, Any]:
    """Build the persisted reconciliation payload consumed by evidence ledgers."""
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic must be a nonempty string")
    result = select_available_sources(
        selected_candidates,
        eligible_candidates,
        availability_outcomes,
        seed_cap=seed_cap,
        versions_by_candidate=versions_by_candidate,
        publication_dates_by_candidate=publication_dates_by_candidate,
    )
    return {
        "schema_version": SOURCE_SELECTION_SCHEMA,
        "status": "reconciled_with_visible_source_gaps",
        "topic": " ".join(topic.split()),
        **result,
        "source_availability_is_not_technical_claim_support": True,
        "what_is_not_concluded": [
            "technical correctness",
            "source safety or retraction status",
            "literature completeness",
            "scientific superiority",
        ],
    }


__all__ = [
    "SELECTION_POLICY",
    "PURPOSE_PRIORITY",
    "SOURCE_SELECTION_SCHEMA",
    "VERSION_POLICY",
    "build_source_selection_ledger",
    "choose_preferred_source_version",
    "select_available_sources",
]
