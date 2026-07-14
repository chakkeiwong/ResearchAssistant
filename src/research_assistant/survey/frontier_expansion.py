from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from research_assistant.survey.discovery_quality import (
    IDENTITY_RESOLUTION_SCHEMA_VERSION,
    RELEVANCE_RANKING_SCHEMA_VERSION,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    sha256_bytes,
)


BACKWARD_FRONTIER_SCHEMA = "ra-survey-backward-snowball-v2"
FORWARD_FRONTIER_SCHEMA = "ra-survey-forward-snowball-v2"
OMITTED_RISKS_SCHEMA = "ra-survey-omitted-paper-risks-v2"
OBSERVATION_AUTHORITY_SCHEMA = "ra-survey-frontier-observation-authority-v1"
ATTEMPT_IDENTITY_SCHEMA = "ra-survey-frontier-attempt-identity-v1"
OBSERVATION_IDENTITY_SCHEMA = "ra-survey-frontier-observation-identity-v1"
RISK_IDENTITY_SCHEMA = "ra-survey-omission-risk-identity-v1"
RISK_RECONCILIATION_SCHEMA = "ra-survey-risk-reconciliation-v1"

CITATION_MAP_SCHEMA = "ra-survey-citation-map-v1"
METADATA_PROVENANCE_SCHEMA = "ra-survey-metadata-provenance-v1"
OMISSION_RISK_SCHEMA = "ra-survey-omission-risk-v1"

ATTEMPT_STATUSES = {
    "observed_results",
    "empty_observed",
    "not_observed",
    "provider_unavailable",
    "malformed_blocked",
}
OBSERVATION_DISPOSITIONS = {
    "observed": {"include", "inspect_next", "omit_with_reason"},
    "capped": {"inspect_next"},
    "depth_excluded": {"inspect_next"},
    "identity_conflict": {"quarantine"},
    "source_blocked": {"quarantine"},
}
NONCLAIMS = [
    "claim support",
    "human review authenticity",
    "literature completeness",
    "live provider coverage",
    "omission correctness",
    "product readiness",
    "scientific correctness",
    "source safety",
]
MAX_TRAVERSAL_VALUE = 1_000_000


def build_frontier_payloads(
    *,
    topic: str,
    metadata_root: Path,
    artifact_digests: dict[str, str],
    metadata_authority_sha256: str,
    metadata_artifact_rows: list[dict[str, Any]],
    mission_id: str,
    mission_fingerprint: str,
    mission_anchor_generation_id: str,
    identity_resolution: dict[str, Any],
    relevance_ranking: dict[str, Any],
    citation_map: dict[str, Any],
    metadata_provenance: dict[str, Any],
    omission_risk: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build deterministic metadata projections without invoking a provider."""

    context = _validate_inputs(
        topic=topic,
        metadata_root=metadata_root,
        artifact_digests=artifact_digests,
        metadata_authority_sha256=metadata_authority_sha256,
        metadata_artifact_rows=metadata_artifact_rows,
        mission_id=mission_id,
        mission_fingerprint=mission_fingerprint,
        mission_anchor_generation_id=mission_anchor_generation_id,
        identity_resolution=identity_resolution,
        relevance_ranking=relevance_ranking,
        citation_map=citation_map,
        metadata_provenance=metadata_provenance,
        omission_risk=omission_risk,
    )
    attempts, observations = _traverse(context)
    frontier_risks = _frontier_risks(context, attempts, observations)
    inherited_risks = _inherited_risks(context)
    risks = sorted([*frontier_risks, *inherited_risks], key=lambda row: row["risk_id"])
    reconciliation = _risk_reconciliation(
        context=context,
        frontier_risks=frontier_risks,
        inherited_risks=inherited_risks,
        risks=risks,
    )

    return {
        "backward_snowball.json": _frontier_ledger(
            context=context,
            direction="backward",
            attempts=attempts,
            observations=observations,
        ),
        "forward_snowball.json": _frontier_ledger(
            context=context,
            direction="forward",
            attempts=attempts,
            observations=observations,
        ),
        "omitted_paper_risks.json": {
            "schema_version": OMITTED_RISKS_SCHEMA,
            "status": "omission_risks_visible",
            "topic": context["topic"],
            "observation_authority_sha256": context["authority_sha256"],
            "risk_count": len(risks),
            "risks": risks,
            "risk_reconciliation": reconciliation,
            "metadata_only_papers": context["relevance_ranking"]["included_paper_ids"],
            "review_policy": {
                "complete_selected_decisions_required": True,
                "omission_visibility_is_not_literature_completeness": True,
                "reviewed_closure_is_current_scope_only": True,
            },
            "what_is_not_concluded": NONCLAIMS,
        },
    }


def validate_frontier_context(**kwargs: Any) -> None:
    _validate_inputs(**kwargs)


def validate_attempt_cardinality(attempt: dict[str, Any]) -> None:
    status = attempt.get("attempt_status")
    observation_ids = attempt.get("candidate_observation_ids")
    risk_id = attempt.get("derived_attempt_risk_id")
    if status not in ATTEMPT_STATUSES:
        raise MissionStateError("invalid_frontier_attempt", "attempt status is not closed")
    if not isinstance(observation_ids, list) or observation_ids != sorted(set(observation_ids)):
        raise MissionStateError("invalid_frontier_attempt", "attempt observation IDs must be sorted and unique")
    if status == "observed_results":
        if not observation_ids or risk_id is not None:
            raise MissionStateError("invalid_frontier_attempt", "observed results require children and no attempt risk")
    elif observation_ids or not _is_risk_id(risk_id):
        raise MissionStateError("invalid_frontier_attempt", "target-free attempts require exactly one risk")

    mechanism = attempt.get("mechanism_kind")
    query_kind = attempt.get("query_kind")
    matched = attempt.get("matched_query_provenance")
    carrier = attempt.get("carrier_query_provenance")
    if mechanism in {"recorded_reference_projection", "recorded_reverse_reference_projection"}:
        if query_kind is not None or matched is not None:
            raise MissionStateError("invented_frontier_query", "projection mechanisms cannot name a query transcript")
        if status in {"empty_observed", "provider_unavailable"}:
            raise MissionStateError("invented_frontier_query", "projection mechanisms cannot emit query-only status")
        if status == "observed_results" and (not isinstance(carrier, list) or not carrier):
            raise MissionStateError("invalid_frontier_attempt", "observed projections require carrier provenance")
    elif mechanism == "recorded_query_observation":
        if query_kind not in {"backward_reference_observation", "forward_citation_observation"}:
            raise MissionStateError("invalid_frontier_attempt", "query observation kind is not closed")
        if not isinstance(matched, dict) or carrier != []:
            raise MissionStateError("invalid_frontier_attempt", "query observations require one transcript and no carrier routes")
    else:
        raise MissionStateError("invalid_frontier_attempt", "frontier mechanism is not closed")


def validate_observation_disposition(observation: dict[str, Any]) -> None:
    status = observation.get("observation_status")
    disposition = observation.get("machine_disposition")
    if disposition not in OBSERVATION_DISPOSITIONS.get(status, set()):
        raise MissionStateError(
            "invalid_frontier_disposition",
            "observation status and machine disposition are incompatible",
        )
    if not _is_observation_id(observation.get("observation_id")):
        raise MissionStateError("invalid_frontier_observation", "observation ID is invalid")
    if disposition == "blocked_source_or_frontier":
        raise MissionStateError("invalid_frontier_disposition", "target observations cannot use attempt disposition")


def _validate_inputs(
    *,
    topic: str,
    metadata_root: Path,
    artifact_digests: dict[str, str],
    metadata_authority_sha256: str,
    metadata_artifact_rows: list[dict[str, Any]],
    mission_id: str,
    mission_fingerprint: str,
    mission_anchor_generation_id: str,
    identity_resolution: dict[str, Any],
    relevance_ranking: dict[str, Any],
    citation_map: dict[str, Any],
    metadata_provenance: dict[str, Any],
    omission_risk: dict[str, Any],
) -> dict[str, Any]:
    normalized_topic = " ".join(topic.split()) if isinstance(topic, str) else ""
    if not normalized_topic:
        raise MissionStateError("invalid_frontier_input", "topic must not be empty")
    if not isinstance(metadata_root, Path) or not metadata_root.is_absolute():
        raise MissionStateError("invalid_frontier_input", "metadata root must be absolute")
    root = metadata_root
    required_digests = {
        "identity_resolution.json",
        "relevance_ranking.json",
        "citation_map.json",
        "metadata_provenance.json",
        "omission_risk.json",
    }
    if not required_digests.issubset(artifact_digests):
        raise MissionStateError("invalid_frontier_input", "metadata artifact digest map is incomplete")
    if any(not _is_sha256(value) for value in artifact_digests.values()):
        raise MissionStateError("invalid_frontier_input", "metadata artifact digest is invalid")
    if not _is_sha256(metadata_authority_sha256):
        raise MissionStateError("invalid_frontier_input", "metadata authority digest is invalid")
    if not isinstance(mission_id, str) or not mission_id:
        raise MissionStateError("invalid_frontier_input", "mission ID is invalid")
    if not _is_sha256(mission_fingerprint):
        raise MissionStateError("invalid_frontier_input", "mission fingerprint is invalid")
    if not isinstance(mission_anchor_generation_id, str) or not mission_anchor_generation_id:
        raise MissionStateError("invalid_frontier_input", "mission anchor generation is invalid")
    if not isinstance(metadata_artifact_rows, list) or any(
        not isinstance(row, dict) or set(row) != {"name", "path", "sha256", "size_bytes"}
        for row in metadata_artifact_rows
    ):
        raise MissionStateError("invalid_frontier_input", "metadata artifact rows are invalid")
    row_names = [row["name"] for row in metadata_artifact_rows]
    if row_names != sorted(set(row_names)) or set(row_names) != set(artifact_digests):
        raise MissionStateError("invalid_frontier_input", "metadata artifact rows and digests differ")
    for row in metadata_artifact_rows:
        if (
            not isinstance(row["name"], str)
            or row["path"] != str(root / row["name"])
            or row["sha256"] != artifact_digests[row["name"]]
            or type(row["size_bytes"]) is not int
            or row["size_bytes"] < 0
        ):
            raise MissionStateError("invalid_frontier_input", "metadata artifact row binding is invalid")

    expected = [
        (identity_resolution, IDENTITY_RESOLUTION_SCHEMA_VERSION),
        (relevance_ranking, RELEVANCE_RANKING_SCHEMA_VERSION),
        (citation_map, CITATION_MAP_SCHEMA),
        (metadata_provenance, METADATA_PROVENANCE_SCHEMA),
        (omission_risk, OMISSION_RISK_SCHEMA),
    ]
    for payload, schema in expected:
        if not isinstance(payload, dict) or payload.get("schema_version") != schema:
            raise MissionStateError("invalid_frontier_input", f"required metadata schema differs: {schema}")
        if payload.get("topic") != normalized_topic:
            raise MissionStateError("foreign_frontier_input", "metadata topic differs from requested topic")
    if identity_resolution.get("status") != "resolved" or identity_resolution.get("seed_gate_passed") is not True:
        raise MissionStateError("blocked_frontier_seed_authority", "frontier projection requires passed seed authority")
    if relevance_ranking.get("status") != "ranked":
        raise MissionStateError("blocked_frontier_relevance_authority", "frontier projection requires ranked metadata")

    accessed_at = metadata_provenance.get("accessed_at")
    if not isinstance(accessed_at, str):
        raise MissionStateError("invalid_frontier_input", "metadata access timestamp is missing")
    try:
        parsed = datetime.fromisoformat(accessed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissionStateError("invalid_frontier_input", "metadata access timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MissionStateError("invalid_frontier_input", "metadata access timestamp lacks timezone")

    policy = _traversal_policy(citation_map.get("expansion_policy"))
    components = identity_resolution.get("components")
    seed_rows = identity_resolution.get("seed_resolutions")
    relevance_rows = relevance_ranking.get("rows")
    if not isinstance(components, list) or not isinstance(seed_rows, list) or not isinstance(relevance_rows, list):
        raise MissionStateError("invalid_frontier_input", "identity/relevance rows must be lists")
    seed_ids = sorted(
        row.get("selected_paper_id")
        for row in seed_rows
        if isinstance(row, dict) and isinstance(row.get("selected_paper_id"), str)
    )
    if not seed_ids or seed_ids != sorted(set(seed_ids)):
        raise MissionStateError("invalid_frontier_input", "selected seed paper IDs must be nonempty and unique")

    component_by_id: dict[str, dict[str, Any]] = {}
    openalex_to_component: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    for component in components:
        if not isinstance(component, dict):
            raise MissionStateError("invalid_frontier_input", "identity component must be an object")
        status = component.get("component_status")
        paper_id = component.get("paper_id")
        if status == "eligible":
            if not isinstance(paper_id, str) or paper_id in component_by_id:
                raise MissionStateError("invalid_frontier_input", "eligible component paper ID is invalid or duplicated")
            component_by_id[paper_id] = component
        elif status == "identity_conflict":
            if paper_id is not None or not isinstance(component.get("conflict_id"), str):
                raise MissionStateError("invalid_frontier_input", "identity conflict component is invalid")
            conflicts.append(component)
        else:
            raise MissionStateError("invalid_frontier_input", "identity component status is not closed")
        for alias in component.get("aliases") or []:
            if isinstance(alias, str) and alias.startswith("openalex:"):
                key = alias.split(":", 1)[1].upper()
                if key in openalex_to_component and openalex_to_component[key] is not component:
                    raise MissionStateError("invalid_frontier_input", "OpenAlex alias maps to multiple components")
                openalex_to_component[key] = component
    if any(seed_id not in component_by_id for seed_id in seed_ids):
        raise MissionStateError("invalid_frontier_input", "selected seed is absent from eligible components")

    relevance_by_id: dict[str, dict[str, Any]] = {}
    relevance_by_conflict: dict[str, dict[str, Any]] = {}
    for row in relevance_rows:
        if not isinstance(row, dict):
            raise MissionStateError("invalid_frontier_input", "relevance row must be an object")
        paper_id = row.get("paper_id")
        conflict_id = row.get("conflict_id")
        if isinstance(paper_id, str):
            if paper_id in relevance_by_id:
                raise MissionStateError("invalid_frontier_input", "relevance paper ID is duplicated")
            relevance_by_id[paper_id] = row
        elif isinstance(conflict_id, str):
            if conflict_id in relevance_by_conflict:
                raise MissionStateError("invalid_frontier_input", "relevance conflict ID is duplicated")
            relevance_by_conflict[conflict_id] = row
        else:
            raise MissionStateError("invalid_frontier_input", "relevance row lacks identity")
    if set(relevance_by_id) != set(component_by_id):
        raise MissionStateError("invalid_frontier_input", "relevance rows do not cover eligible components exactly")
    included_ids = relevance_ranking.get("included_paper_ids")
    expected_included = sorted(
        row["paper_id"] for row in relevance_rows if row.get("included") is True
    )
    if (
        not isinstance(included_ids, list)
        or any(not isinstance(value, str) for value in included_ids)
        or len(included_ids) != len(set(included_ids))
        or sorted(included_ids) != expected_included
    ):
        raise MissionStateError("invalid_frontier_input", "included relevance IDs differ from rows")

    risks = omission_risk.get("risks")
    if not isinstance(risks, list) or any(not isinstance(row, dict) for row in risks):
        raise MissionStateError("invalid_frontier_input", "inherited omission risks must be objects")
    original_risk_ids = [row.get("risk_id") for row in risks]
    if any(not isinstance(value, str) or not value for value in original_risk_ids):
        raise MissionStateError("invalid_frontier_input", "inherited risk ID is invalid")
    if len(original_risk_ids) != len(set(original_risk_ids)):
        raise MissionStateError("invalid_frontier_input", "inherited risk ID is duplicated")

    digest_projection = {name: artifact_digests[name] for name in sorted(artifact_digests)}
    authority = {
        "schema_version": OBSERVATION_AUTHORITY_SCHEMA,
        "mission_id": mission_id,
        "mission_fingerprint": mission_fingerprint,
        "mission_anchor_generation_id": mission_anchor_generation_id,
        "metadata_authority_sha256": metadata_authority_sha256,
        "metadata_root": str(root),
        "accessed_at": accessed_at,
        "artifact_rows": metadata_artifact_rows,
        "traversal_policy": policy,
    }
    return {
        "topic": normalized_topic,
        "metadata_root": root,
        "artifact_digests": digest_projection,
        "metadata_authority_sha256": metadata_authority_sha256,
        "metadata_artifact_rows": metadata_artifact_rows,
        "mission_id": mission_id,
        "mission_fingerprint": mission_fingerprint,
        "mission_anchor_generation_id": mission_anchor_generation_id,
        "identity_resolution": identity_resolution,
        "relevance_ranking": relevance_ranking,
        "citation_map": citation_map,
        "metadata_provenance": metadata_provenance,
        "omission_risk": omission_risk,
        "accessed_at": accessed_at,
        "policy": policy,
        "seed_ids": seed_ids,
        "component_by_id": component_by_id,
        "openalex_to_component": openalex_to_component,
        "relevance_by_id": relevance_by_id,
        "relevance_by_conflict": relevance_by_conflict,
        "authority_sha256": sha256_bytes(canonical_json_bytes(authority)),
    }


def _traversal_policy(value: Any) -> dict[str, int]:
    expected = {
        "backward_depth",
        "forward_depth",
        "adjacent_query_count",
        "max_nodes",
        "max_downloads",
        "download_or_source_intake_allowed",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise MissionStateError("invalid_frontier_policy", "citation expansion policy fields are not exact")
    for key in ("backward_depth", "forward_depth", "max_nodes"):
        if (
            type(value.get(key)) is not int
            or value[key] <= 0
            or value[key] > MAX_TRAVERSAL_VALUE
        ):
            raise MissionStateError("invalid_frontier_policy", f"{key} must be a positive non-Boolean integer")
    if (
        type(value.get("adjacent_query_count")) is not int
        or value["adjacent_query_count"] < 0
        or value.get("max_downloads") != 0
        or value.get("download_or_source_intake_allowed") is not False
    ):
        raise MissionStateError("invalid_frontier_policy", "citation expansion policy crosses Phase 8 boundary")
    return {
        "backward_depth": value["backward_depth"],
        "forward_depth": value["forward_depth"],
        "global_node_cap": value["max_nodes"],
        "backward_observation_cap": value["max_nodes"],
        "forward_observation_cap": value["max_nodes"],
        "global_node_cap_source": "citation_map.expansion_policy.max_nodes",
        "backward_observation_cap_source": "citation_map.expansion_policy.max_nodes",
        "forward_observation_cap_source": "citation_map.expansion_policy.max_nodes",
    }


def _traverse(context: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    origins: dict[int, set[str]] = {1: set(context["seed_ids"])}
    attempted = {
        direction: set()
        for direction in ("backward", "forward")
    }
    retained_nodes = set(context["seed_ids"])
    direction_counts = {"backward": 0, "forward": 0}
    max_depth = {
        "backward": context["policy"]["backward_depth"],
        "forward": context["policy"]["forward_depth"],
    }
    max_overall_depth = max(max_depth.values())

    for depth in range(1, max_overall_depth + 1):
        attempt_specs = []
        for direction in ("backward", "forward"):
            if depth > max_depth[direction]:
                continue
            for origin in sorted(origins.get(depth, set())):
                if origin in attempted[direction]:
                    continue
                attempted[direction].add(origin)
                attempt_specs.append((origin, direction))
        for origin, direction in sorted(attempt_specs):
            raw_targets = _projection_targets(context, origin=origin, direction=direction)
            attempt_id = _attempt_id(context, origin=origin, direction=direction, depth=depth)
            child_rows: list[dict[str, Any]] = []
            for target in raw_targets:
                direction_counts[direction] += 1
                status, disposition, signals = _classify_target(context, target)
                cap = context["policy"][f"{direction}_observation_cap"]
                stable_target = target.get("paper_id")
                retain_for_later_origin = (
                    disposition == "include"
                    and isinstance(stable_target, str)
                    and any(depth < limit for limit in max_depth.values())
                )
                if direction_counts[direction] > cap:
                    status, disposition = "capped", "inspect_next"
                    retain_for_later_origin = False
                else:
                    if retain_for_later_origin and stable_target not in retained_nodes:
                        if len(retained_nodes) >= context["policy"]["global_node_cap"]:
                            status, disposition = "capped", "inspect_next"
                            retain_for_later_origin = False
                        else:
                            retained_nodes.add(stable_target)
                    if disposition == "include" and depth >= max_depth[direction]:
                        status, disposition = "depth_excluded", "inspect_next"
                observation = _observation(
                    context=context,
                    attempt_id=attempt_id,
                    origin=origin,
                    direction=direction,
                    depth=depth,
                    target=target,
                    status=status,
                    disposition=disposition,
                    signals=signals,
                    traversal_order=len(observations) + len(child_rows) + 1,
                )
                validate_observation_disposition(observation)
                child_rows.append(observation)
                if retain_for_later_origin:
                    origins.setdefault(depth + 1, set()).add(stable_target)
            child_rows.sort(key=lambda row: (row["target_id"], row["observation_id"]))
            observations.extend(child_rows)
            carrier_routes = sorted(
                {
                    canonical_json_bytes(route): route
                    for row in child_rows
                    for route in row["carrier_query_provenance"]
                }.values(),
                key=canonical_json_bytes,
            )
            attempt = {
                "frontier_attempt_id": attempt_id,
                "direction": direction,
                "origin_paper_id": origin,
                "depth": depth,
                "provider": "openalex",
                "mechanism_kind": (
                    "recorded_reference_projection"
                    if direction == "backward"
                    else "recorded_reverse_reference_projection"
                ),
                "query_kind": None,
                "matched_query_provenance": None,
                "carrier_query_provenance": carrier_routes,
                "source_artifact_role": "identity_resolution.json",
                "source_artifact_sha256": context["artifact_digests"]["identity_resolution.json"],
                "observed_at": context["accessed_at"],
                "requested_depth": depth,
                "requested_cap": context["policy"][f"{direction}_observation_cap"],
                "attempt_status": "observed_results" if child_rows else "not_observed",
                "reason": (
                    "exact recorded metadata relations projected"
                    if child_rows
                    else "no exact recorded relation exists for the required projection tuple"
                ),
                "candidate_observation_ids": sorted(row["observation_id"] for row in child_rows),
                "derived_attempt_risk_id": None,
                "claim_support_allowed": False,
                "literature_completeness_allowed": False,
            }
            if not child_rows:
                attempt["derived_attempt_risk_id"] = _risk_id(
                    context,
                    source_type="frontier_attempt",
                    source_id=attempt_id,
                    disposition="blocked_source_or_frontier",
                )
            validate_attempt_cardinality(attempt)
            attempts.append(attempt)
    attempts.sort(key=lambda row: (row["depth"], row["origin_paper_id"], row["direction"], row["frontier_attempt_id"]))
    observations.sort(key=lambda row: (row["depth"], row["origin_paper_id"], row["direction"], row["target_id"], row["observation_id"]))
    for index, row in enumerate(observations, start=1):
        row["traversal_order"] = index
    return attempts, observations


def _projection_targets(context: dict[str, Any], *, origin: str, direction: str) -> list[dict[str, Any]]:
    if direction == "backward":
        component = context["component_by_id"].get(origin)
        if component is None:
            raise MissionStateError("invalid_frontier_origin", "backward origin is not an eligible component")
        values = [
            _target_from_openalex(context, openalex_id, carrier_component=component)
            for openalex_id in component.get("referenced_works") or []
        ]
    else:
        origin_component = context["component_by_id"].get(origin)
        if origin_component is None:
            raise MissionStateError("invalid_frontier_origin", "forward origin is not an eligible component")
        origin_aliases = {
            alias.split(":", 1)[1].upper()
            for alias in origin_component.get("aliases") or []
            if isinstance(alias, str) and alias.startswith("openalex:")
        }
        values = []
        if origin_aliases:
            for component in [
                *context["component_by_id"].values(),
                *(row for row in context["identity_resolution"]["components"] if row.get("component_status") == "identity_conflict"),
            ]:
                if origin_aliases & set(component.get("referenced_works") or []):
                    values.append(_target_from_component(
                        component,
                        carrier_reference_ids=origin_aliases,
                    ))
    unique: dict[bytes, dict[str, Any]] = {}
    for row in values:
        if row["target_id"] == origin:
            continue
        key = canonical_json_bytes({
            field: value
            for field, value in row.items()
            if field != "carrier_query_provenance"
        })
        existing = unique.get(key)
        if existing is None:
            unique[key] = {
                **row,
                "carrier_query_provenance": list(row["carrier_query_provenance"]),
            }
            continue
        routes = {
            canonical_json_bytes(route): route
            for route in [
                *existing["carrier_query_provenance"],
                *row["carrier_query_provenance"],
            ]
        }
        existing["carrier_query_provenance"] = sorted(routes.values(), key=canonical_json_bytes)
    return sorted(unique.values(), key=lambda row: (row["target_id"], canonical_json_bytes(row)))


def _target_from_openalex(
    context: dict[str, Any],
    openalex_id: str,
    *,
    carrier_component: dict[str, Any],
) -> dict[str, Any]:
    component = context["openalex_to_component"].get(str(openalex_id).upper())
    if component is None:
        return {
            "target_id": f"openalex:{str(openalex_id).casefold()}",
            "paper_id": None,
            "conflict_id": None,
            "carrier_query_provenance": _component_routes(
                carrier_component,
                carrier_reference_ids={str(openalex_id).upper()},
            ),
        }
    target = _target_from_component(component)
    target["carrier_query_provenance"] = _component_routes(
        carrier_component,
        carrier_reference_ids={str(openalex_id).upper()},
    )
    return target


def _target_from_component(
    component: dict[str, Any],
    *,
    carrier_reference_ids: set[str] | None = None,
) -> dict[str, Any]:
    paper_id = component.get("paper_id")
    conflict_id = component.get("conflict_id")
    return {
        "target_id": paper_id if isinstance(paper_id, str) else f"conflict:{conflict_id}",
        "paper_id": paper_id,
        "conflict_id": conflict_id,
        "carrier_query_provenance": _component_routes(
            component,
            carrier_reference_ids=carrier_reference_ids,
        ),
    }


def _component_routes(
    component: dict[str, Any],
    *,
    carrier_reference_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    return sorted(
        {
            canonical_json_bytes(route): route
            for row in component.get("rows") or []
            if isinstance(row, dict)
            and (
                carrier_reference_ids is None
                or carrier_reference_ids & set(row.get("referenced_works") or [])
            )
            for route in row.get("query_provenance") or []
            if isinstance(route, dict)
        }.values(),
        key=canonical_json_bytes,
    )


def _classify_target(
    context: dict[str, Any],
    target: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    paper_id = target.get("paper_id")
    conflict_id = target.get("conflict_id")
    if isinstance(conflict_id, str):
        row = context["relevance_by_conflict"].get(conflict_id, {})
        component = next(
            item
            for item in context["identity_resolution"]["components"]
            if item.get("conflict_id") == conflict_id
        )
        return "identity_conflict", "quarantine", _signals(row, component)
    if not isinstance(paper_id, str):
        return "source_blocked", "quarantine", _signals({}, None)
    row = context["relevance_by_id"][paper_id]
    component = context["component_by_id"][paper_id]
    disposition = row.get("disposition")
    if row.get("included") is True:
        return "observed", "include", _signals(row, component)
    if disposition == "excluded_by_cap_after_relevance":
        return "capped", "inspect_next", _signals(row, component)
    if disposition == "weak_match_review_required":
        return "observed", "inspect_next", _signals(row, component)
    if disposition == "irrelevant_excluded":
        return "observed", "omit_with_reason", _signals(row, component)
    return "source_blocked", "quarantine", _signals(row, component)


def _signals(row: dict[str, Any], component: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "recorded_roles": sorted(component.get("roles") or []) if component else [],
        "relevance_disposition": row.get("disposition"),
        "matched_tokens": row.get("matched_tokens") or [],
        "matched_count": row.get("matched_count", 0),
        "citation_count": row.get("citation_count"),
        "signals_are_navigation_only": True,
    }


def _observation(
    *,
    context: dict[str, Any],
    attempt_id: str,
    origin: str,
    direction: str,
    depth: int,
    target: dict[str, Any],
    status: str,
    disposition: str,
    signals: dict[str, Any],
    traversal_order: int,
) -> dict[str, Any]:
    projection = {
        "schema_version": OBSERVATION_IDENTITY_SCHEMA,
        "observation_authority_sha256": context["authority_sha256"],
        "frontier_attempt_id": attempt_id,
        "origin_paper_id": origin,
        "target_id": target["target_id"],
        "direction": direction,
        "depth": depth,
    }
    observation_id = f"fo-{sha256_bytes(canonical_json_bytes(projection))}"
    return {
        "observation_id": observation_id,
        "frontier_attempt_id": attempt_id,
        "direction": direction,
        "origin_paper_id": origin,
        "target_id": target["target_id"],
        "target_paper_id": target.get("paper_id"),
        "target_conflict_id": target.get("conflict_id"),
        "relation": "backward_reference_metadata" if direction == "backward" else "forward_citation_metadata",
        "provider": "openalex",
        "mechanism_kind": (
            "recorded_reference_projection"
            if direction == "backward"
            else "recorded_reverse_reference_projection"
        ),
        "query_kind": None,
        "matched_query_provenance": None,
        "carrier_query_provenance": target["carrier_query_provenance"],
        "source_artifact_role": "identity_resolution.json",
        "source_artifact_sha256": context["artifact_digests"]["identity_resolution.json"],
        "observed_at": context["accessed_at"],
        "depth": depth,
        "traversal_order": traversal_order,
        "cap_state": "within_cap" if status != "capped" else "capped_visible",
        "observation_status": status,
        "classification_signals": signals,
        "machine_disposition": disposition,
        "reason": f"{status}:{disposition}",
        "claim_support_allowed": False,
        "literature_completeness_allowed": False,
    }


def _attempt_id(context: dict[str, Any], *, origin: str, direction: str, depth: int) -> str:
    projection = {
        "schema_version": ATTEMPT_IDENTITY_SCHEMA,
        "observation_authority_sha256": context["authority_sha256"],
        "origin_paper_id": origin,
        "direction": direction,
        "depth": depth,
        "provider": "openalex",
        "mechanism_kind": (
            "recorded_reference_projection"
            if direction == "backward"
            else "recorded_reverse_reference_projection"
        ),
    }
    return f"fa-{sha256_bytes(canonical_json_bytes(projection))}"


def _frontier_risks(
    context: dict[str, Any],
    attempts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attempt in attempts:
        risk_id = attempt["derived_attempt_risk_id"]
        if risk_id is None:
            continue
        rows.append(_risk_row(
            risk_id=risk_id,
            source_type="frontier_attempt",
            source_id=attempt["frontier_attempt_id"],
            disposition="blocked_source_or_frontier",
            severity="high",
            reason=attempt["reason"],
            next_action=f"inspect or explicitly close the recorded {attempt['direction']} frontier scope",
            source_artifact_sha256=attempt["source_artifact_sha256"],
        ))
    for observation in observations:
        disposition = observation["machine_disposition"]
        if disposition == "include":
            continue
        rows.append(_risk_row(
            risk_id=_risk_id(
                context,
                source_type="candidate_observation",
                source_id=observation["observation_id"],
                disposition=disposition,
            ),
            source_type="candidate_observation",
            source_id=observation["observation_id"],
            disposition=disposition,
            severity="high" if disposition in {"inspect_next", "quarantine"} else "medium",
            reason=observation["reason"],
            next_action=(
                "inspect the exact candidate or keep the risk open"
                if disposition == "inspect_next"
                else "keep quarantined pending exact source evidence"
                if disposition == "quarantine"
                else "review the recorded omission rationale"
            ),
            source_artifact_sha256=observation["source_artifact_sha256"],
        ))
    if len({row["risk_id"] for row in rows}) != len(rows):
        raise MissionStateError("duplicate_frontier_risk", "frontier risks are not one-to-one")
    return sorted(rows, key=lambda row: row["risk_id"])


def _inherited_risks(context: dict[str, Any]) -> list[dict[str, Any]]:
    source_digest = context["artifact_digests"]["omission_risk.json"]
    rows = []
    for index, inherited in enumerate(context["omission_risk"]["risks"]):
        source_id = inherited["risk_id"]
        risk_id = _risk_id(
            context,
            source_type="inherited_metadata_risk",
            source_id=source_id,
            disposition="blocked_source_or_frontier",
            source_payload={"row_index": index, "row": inherited},
        )
        row = _risk_row(
            risk_id=risk_id,
            source_type="inherited_metadata_risk",
            source_id=source_id,
            disposition="blocked_source_or_frontier",
            severity=inherited.get("severity") or "high",
            reason=inherited.get("risk") or inherited.get("reason") or "inherited metadata risk",
            next_action=inherited.get("expected_action") or inherited.get("next_action") or "keep inherited risk open",
            source_artifact_sha256=source_digest,
        )
        row.update({
            "inherited_risk_id": source_id,
            "inherited_row_index": index,
            "inherited_row_sha256": sha256_bytes(canonical_json_bytes(inherited)),
            "frontier_attempt_id": None,
            "candidate_observation_id": None,
        })
        rows.append(row)
    if len({row["risk_id"] for row in rows}) != len(rows):
        raise MissionStateError("duplicate_inherited_risk", "inherited risks are not one-to-one")
    return sorted(rows, key=lambda row: row["risk_id"])


def _risk_row(
    *,
    risk_id: str,
    source_type: str,
    source_id: str,
    disposition: str,
    severity: str,
    reason: str,
    next_action: str,
    source_artifact_sha256: str,
) -> dict[str, Any]:
    return {
        "risk_id": risk_id,
        "risk_source_type": source_type,
        "risk_source_id": source_id,
        "machine_disposition": disposition,
        "severity": severity,
        "reason": reason,
        "next_action": next_action,
        "source_artifact_sha256": source_artifact_sha256,
        "status": "open",
        "claim_support_allowed": False,
        "literature_completeness_allowed": False,
    }


def _risk_reconciliation(
    *,
    context: dict[str, Any],
    frontier_risks: list[dict[str, Any]],
    inherited_risks: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> dict[str, Any]:
    preserved_by_inherited_id = {
        row["inherited_risk_id"]: row["risk_id"]
        for row in inherited_risks
    }
    input_rows = [
        {
            "inherited_risk_id": row["risk_id"],
            "inherited_row_index": index,
            "inherited_row_sha256": sha256_bytes(canonical_json_bytes(row)),
            "preserved_risk_id": preserved_by_inherited_id[row["risk_id"]],
        }
        for index, row in enumerate(context["omission_risk"]["risks"])
    ]
    all_ids = [row["risk_id"] for row in risks]
    expected_ids = sorted([
        *(row["risk_id"] for row in frontier_risks),
        *(row["risk_id"] for row in inherited_risks),
    ])
    if all_ids != expected_ids or len(all_ids) != len(set(all_ids)):
        raise MissionStateError("invalid_risk_reconciliation", "risk union is incomplete or duplicated")
    return {
        "schema_version": RISK_RECONCILIATION_SCHEMA,
        "inherited_input_sha256": context["artifact_digests"]["omission_risk.json"],
        "inherited_mappings": input_rows,
        "frontier_risk_ids": sorted(row["risk_id"] for row in frontier_risks),
        "preserved_inherited_risk_ids": sorted(row["risk_id"] for row in inherited_risks),
        "complete_output_risk_ids": all_ids,
        "implicit_supersession_allowed": False,
    }


def _risk_id(
    context: dict[str, Any],
    *,
    source_type: str,
    source_id: str,
    disposition: str,
    source_payload: dict[str, Any] | None = None,
) -> str:
    projection = {
        "schema_version": RISK_IDENTITY_SCHEMA,
        "observation_authority_sha256": context["authority_sha256"],
        "source_type": source_type,
        "source_id": source_id,
        "machine_disposition": disposition,
        "source_payload": source_payload,
    }
    return f"or-{sha256_bytes(canonical_json_bytes(projection))}"


def _frontier_ledger(
    *,
    context: dict[str, Any],
    direction: str,
    attempts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    direction_attempts = [row for row in attempts if row["direction"] == direction]
    direction_observations = [row for row in observations if row["direction"] == direction]
    blocked = any(row["attempt_status"] != "observed_results" for row in direction_attempts)
    status_counts = _counts(direction_attempts, "attempt_status")
    observation_counts = _counts(direction_observations, "observation_status")
    disposition_counts = _counts(direction_observations, "machine_disposition")
    return {
        "schema_version": BACKWARD_FRONTIER_SCHEMA if direction == "backward" else FORWARD_FRONTIER_SCHEMA,
        "status": "blocked_frontier_risks_open" if blocked else "recorded_projection_visible",
        "topic": context["topic"],
        "direction": direction,
        "observation_authority_sha256": context["authority_sha256"],
        "source_metadata_root": str(context["metadata_root"]),
        "source_mission_binding": {
            "mission_id": context["mission_id"],
            "mission_fingerprint": context["mission_fingerprint"],
            "mission_anchor_generation_id": context["mission_anchor_generation_id"],
            "metadata_authority_sha256": context["metadata_authority_sha256"],
        },
        "source_metadata_accessed_at": context["accessed_at"],
        "source_artifact_digests": context["artifact_digests"],
        "source_artifact_rows": context["metadata_artifact_rows"],
        "provider_status_projection": context["metadata_provenance"].get("provider_statuses") or [],
        "traversal_policy": context["policy"],
        "attempts": direction_attempts,
        "observations": direction_observations,
        "summary": {
            "attempt_count": len(direction_attempts),
            "observation_count": len(direction_observations),
            "attempt_status_counts": status_counts,
            "observation_status_counts": observation_counts,
            "machine_disposition_counts": disposition_counts,
        },
        "evidence_policy": {
            "metadata_relations_support_navigation": True,
            "metadata_relations_support_technical_claims": False,
            "metadata_relations_support_completeness_claims": False,
            "projection_is_not_provider_query_transcript": True,
        },
        "next_required_actions": [
            f"review every non-include {direction} observation and target-free attempt risk",
            "obtain separately authorized observation evidence before changing a not-observed frontier",
        ],
        "what_is_not_concluded": NONCLAIMS,
    }


def _counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = defaultdict(int)
    for row in rows:
        value = row.get(field)
        if not isinstance(value, str):
            raise MissionStateError("invalid_frontier_summary", f"{field} must be a string")
        result[value] += 1
    return {key: result[key] for key in sorted(result)}


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _is_risk_id(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("or-") and _is_sha256(value[3:])


def _is_observation_id(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("fo-") and _is_sha256(value[3:])


__all__ = [
    "ATTEMPT_STATUSES",
    "BACKWARD_FRONTIER_SCHEMA",
    "FORWARD_FRONTIER_SCHEMA",
    "OBSERVATION_DISPOSITIONS",
    "OMITTED_RISKS_SCHEMA",
    "build_frontier_payloads",
    "validate_frontier_context",
    "validate_attempt_cardinality",
    "validate_observation_disposition",
]
