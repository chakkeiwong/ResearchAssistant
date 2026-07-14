from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from research_assistant.benchmarks.claim_guard import (
    claim_laundering_hits,
    nonclaim_rows_in_claims,
)

REPORT_SCHEMA_VERSION = "ra-surveybench-report-v1"
TASK_SCHEMA_VERSION = "ra-surveybench-task-v1"

EXPECTED_SCHEMAS = {
    "citation_map": "ra-surveybench-citation-map-v1",
    "candidate_ledger": "ra-surveybench-candidate-ledger-v1",
    "source_support": "ra-surveybench-source-support-v1",
    "claim_support": "ra-surveybench-claim-support-v1",
    "omission_risk": "ra-surveybench-omission-risk-v1",
}

FIXTURE_STATUS_VALUES = {
    "available_fixture",
    "metadata_only_fixture",
    "downloaded_fixture",
    "blocked_fixture",
    "not_attempted",
}

VETO_MISSING_CITATION_MAP = "missing_citation_map"
VETO_MISSING_REQUIRED_EDGE = "missing_required_edge"
VETO_FORBIDDEN_CLAIM = "forbidden_claim"
VETO_UNSUPPORTED_TECHNICAL_CLAIM = "unsupported_technical_claim"
VETO_MISSING_ANCHOR = "missing_anchor"


class SurveyBenchmarkError(ValueError):
    """Raised when a SurveyBench task or output packet is structurally invalid."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SurveyBenchmarkError(f"{path}: invalid JSON: {exc}") from exc


def resolve_task_path(task_path: Path, rel_path: str) -> Path:
    return (task_path.parent / rel_path).resolve()


def load_task(task_path: Path) -> dict[str, Any]:
    task = load_json(task_path)
    if task.get("schema_version") != TASK_SCHEMA_VERSION:
        raise SurveyBenchmarkError(
            f"{task_path}: expected schema_version {TASK_SCHEMA_VERSION!r}"
        )
    required_outputs = set(task.get("required_outputs", []))
    expected_outputs = task.get("expected_outputs", {})
    missing = sorted(required_outputs - set(expected_outputs))
    if missing:
        raise SurveyBenchmarkError(
            f"{task_path}: required_outputs missing expected paths: {missing}"
        )
    return task


def load_output_packet(task: dict[str, Any], task_path: Path, actual_dir: Path | None = None) -> dict[str, Any]:
    packet: dict[str, Any] = {}
    expected_outputs = task["expected_outputs"]
    for output_name in task["required_outputs"]:
        expected_path = resolve_task_path(task_path, expected_outputs[output_name])
        actual_path = expected_path if actual_dir is None else (actual_dir / expected_path.name)
        if not actual_path.exists():
            packet[output_name] = None
            continue
        packet[output_name] = load_json(actual_path)
    return packet


def load_anchor_inventory(task: dict[str, Any], task_path: Path) -> dict[str, Any]:
    rel_path = task.get("fixture_inputs", {}).get("anchor_inventory")
    if not rel_path:
        return {
            "anchors": [],
            "schema_version": "ra-surveybench-anchor-inventory-v1",
            "task_id": task.get("task_id"),
        }
    inventory_path = resolve_task_path(task_path, rel_path)
    inventory = load_json(inventory_path)
    if inventory.get("schema_version") != "ra-surveybench-anchor-inventory-v1":
        raise SurveyBenchmarkError(
            f"{inventory_path}: expected schema_version 'ra-surveybench-anchor-inventory-v1'"
        )
    return inventory


def _to_report_values(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if isinstance(value, tuple):
            result.append(list(value))
        else:
            result.append(value)
    return result


def _score_set(expected: set[Any], actual: set[Any]) -> dict[str, Any]:
    matched = expected & actual
    missing = expected - actual
    extra = actual - expected
    return {
        "matched": len(matched),
        "expected": len(expected),
        "actual": len(actual),
        "score": len(matched) / len(expected) if expected else 1.0,
        "missing": _to_report_values(sorted(missing)),
        "extra": _to_report_values(sorted(extra)),
    }


def _edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(edge.get("source", "")),
        str(edge.get("target", "")),
        str(edge.get("edge_type", "")),
    )


def _anchor_key(anchor: dict[str, Any], default_paper_key: str | None = None) -> tuple[str, str, str]:
    return (
        str(anchor.get("paper_key") or default_paper_key or ""),
        str(anchor.get("kind", "")),
        str(anchor.get("label", "")),
    )


def _paper_key_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("paper_key")): row
        for row in rows
        if isinstance(row, dict) and row.get("paper_key")
    }


def _norm_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _matches_forbidden_claim(claim_text: str, forbidden_phrases: set[str]) -> bool:
    return any(phrase and phrase in claim_text for phrase in forbidden_phrases)


def _inventory_anchor_keys(anchor_inventory: dict[str, Any], inventory_root: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for row in anchor_inventory.get("anchors", []):
        if not isinstance(row, dict):
            continue
        key = _anchor_key(row)
        artifact_path = row.get("artifact_path")
        marker_text = row.get("marker_text")
        if not all(key) or not artifact_path:
            continue
        artifact = (inventory_root / str(artifact_path)).resolve()
        if not artifact.exists():
            continue
        if marker_text and str(marker_text) not in artifact.read_text():
            continue
        keys.add(key)
    return keys


def _score_anchor_keys(expected: set[tuple[str, str, str]], actual: set[tuple[str, str, str]]) -> dict[str, Any]:
    return _score_set(expected, actual)


def _validate_output_schema(
    output_name: str, payload: dict[str, Any] | None, task_id: str, vetoes: list[str]
) -> list[str]:
    errors: list[str] = []
    if payload is None:
        if output_name == "citation_map":
            vetoes.append(VETO_MISSING_CITATION_MAP)
        errors.append(f"{output_name}: missing output artifact")
        return errors
    expected_schema = EXPECTED_SCHEMAS.get(output_name)
    if expected_schema and payload.get("schema_version") != expected_schema:
        errors.append(
            f"{output_name}: expected schema_version {expected_schema!r}, "
            f"got {payload.get('schema_version')!r}"
        )
    if payload.get("task_id") != task_id and output_name != "fixture_citation_graph":
        errors.append(f"{output_name}: expected task_id {task_id!r}")
    return errors


def _score_citation_map(task: dict[str, Any], citation_map: dict[str, Any] | None, vetoes: list[str]) -> dict[str, Any]:
    if citation_map is None:
        return {
            "required_node_recall": _score_set(set(task.get("required_papers", [])), set()),
            "required_edge_recall": _score_set(
                {_edge_key(edge) for edge in task.get("required_edges", [])}, set()
            ),
            "required_cluster_recall": _score_set(set(task.get("required_clusters", [])), set()),
            "source_status_accuracy": {
                "matched": 0,
                "expected": len(task.get("required_papers", [])) * 2,
                "score": 0.0,
                "mismatched": sorted(task.get("required_papers", [])),
            },
        }

    actual_nodes = _paper_key_map(citation_map.get("nodes", []))
    expected_nodes = set(task.get("required_papers", []))
    actual_node_keys = set(actual_nodes)
    node_score = _score_set(expected_nodes, actual_node_keys)

    expected_edges = {_edge_key(edge) for edge in task.get("required_edges", [])}
    actual_edges = {_edge_key(edge) for edge in citation_map.get("edges", [])}
    edge_score = _score_set(expected_edges, actual_edges)
    if edge_score["missing"]:
        vetoes.append(VETO_MISSING_REQUIRED_EDGE)

    actual_clusters = {
        str(cluster.get("cluster_id"))
        for cluster in citation_map.get("clusters", [])
        if isinstance(cluster, dict) and cluster.get("cluster_id")
    }
    cluster_score = _score_set(set(task.get("required_clusters", [])), actual_clusters)

    mismatched_status: list[str] = []
    checked_status = 0
    for paper_key in sorted(expected_nodes):
        node = actual_nodes.get(paper_key)
        if not node:
            mismatched_status.append(paper_key)
            continue
        checked_status += 1
        for field in ("local_source_status", "download_status"):
            if node.get(field) not in FIXTURE_STATUS_VALUES:
                mismatched_status.append(f"{paper_key}:{field}")
    status_expected = len(expected_nodes) * 2
    status_matched = status_expected - len(mismatched_status)
    return {
        "required_node_recall": node_score,
        "required_edge_recall": edge_score,
        "required_cluster_recall": cluster_score,
        "source_status_accuracy": {
            "matched": max(status_matched, 0),
            "expected": status_expected,
            "nodes_checked": checked_status,
            "score": max(status_matched, 0) / status_expected if status_expected else 1.0,
            "mismatched": mismatched_status,
        },
    }


def _duplicate_pairs(candidate_ledger: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in candidate_ledger.get("duplicates", []):
        if not isinstance(row, dict):
            continue
        canonical_key = str(row.get("canonical_key", ""))
        for duplicate_key in row.get("duplicate_keys", []):
            if canonical_key and duplicate_key:
                pairs.add((canonical_key, str(duplicate_key)))
    return pairs


def _excluded_keys(candidate_ledger: dict[str, Any]) -> set[str]:
    return {
        str(row.get("paper_key"))
        for row in candidate_ledger.get("excluded", [])
        if isinstance(row, dict) and row.get("paper_key")
    }


def _score_candidate_ledger(
    task: dict[str, Any],
    candidate_ledger: dict[str, Any] | None,
    expected_candidate_ledger: dict[str, Any],
) -> dict[str, Any]:
    expected_papers = set(task.get("required_papers", []))
    expected_duplicates = _duplicate_pairs(expected_candidate_ledger)
    expected_excluded = _excluded_keys(expected_candidate_ledger)
    if candidate_ledger is None:
        return {
            "included_required_paper_recall": _score_set(expected_papers, set()),
            "duplicate_case_recall": _score_set(expected_duplicates, set()),
            "excluded_false_positive_recall": _score_set(expected_excluded, set()),
        }
    included = {
        str(row.get("paper_key"))
        for row in candidate_ledger.get("included", [])
        if isinstance(row, dict) and row.get("paper_key")
    }
    return {
        "included_required_paper_recall": _score_set(expected_papers, included),
        "duplicate_case_recall": _score_set(expected_duplicates, _duplicate_pairs(candidate_ledger)),
        "excluded_false_positive_recall": _score_set(expected_excluded, _excluded_keys(candidate_ledger)),
    }


def _score_source_support(
    task: dict[str, Any],
    source_support: dict[str, Any] | None,
    expected_source_support: dict[str, Any],
    anchor_keys: set[tuple[str, str, str]],
    vetoes: list[str],
) -> dict[str, Any]:
    expected_papers = set(task.get("required_papers", []))
    expected_rows = _paper_key_map(expected_source_support.get("papers", []))
    if source_support is None:
        return {
            "source_support_recall": _score_set(expected_papers, set()),
            "checked_anchor_recall": _score_anchor_keys(set(), set()),
            "fixture_status_accuracy": {
                "matched": 0,
                "expected": len(expected_papers) * 2,
                "score": 0.0,
                "mismatched": sorted(expected_papers),
            },
        }
    papers = _paper_key_map(source_support.get("papers", []))
    support_score = _score_set(expected_papers, set(papers))
    mismatched: list[str] = []
    expected_anchor_keys: set[tuple[str, str, str]] = set()
    actual_anchor_keys: set[tuple[str, str, str]] = set()
    for paper_key in sorted(expected_papers):
        paper = papers.get(paper_key)
        expected = expected_rows.get(paper_key, {})
        if not paper:
            mismatched.append(paper_key)
            continue
        for field in ("source_status", "download_status"):
            if paper.get(field) not in FIXTURE_STATUS_VALUES or paper.get(field) != expected.get(field):
                mismatched.append(f"{paper_key}:{field}")
        for anchor in expected.get("checked_anchors", []):
            if isinstance(anchor, dict):
                expected_anchor_keys.add(_anchor_key(anchor, paper_key))
        for anchor in paper.get("checked_anchors", []):
            if isinstance(anchor, dict):
                key = _anchor_key(anchor, paper_key)
                if key in anchor_keys:
                    actual_anchor_keys.add(key)
    anchor_score = _score_anchor_keys(expected_anchor_keys, actual_anchor_keys)
    if anchor_score["missing"]:
        vetoes.append(VETO_MISSING_ANCHOR)
    status_expected = len(expected_papers) * 2
    status_matched = status_expected - len(mismatched)
    return {
        "source_support_recall": support_score,
        "checked_anchor_recall": anchor_score,
        "fixture_status_accuracy": {
            "matched": max(status_matched, 0),
            "expected": status_expected,
            "score": max(status_matched, 0) / status_expected if status_expected else 1.0,
            "mismatched": mismatched,
        },
    }


def _score_claim_support(
    task: dict[str, Any],
    claim_support: dict[str, Any] | None,
    expected_claim_support: dict[str, Any],
    vetoes: list[str],
    anchor_keys: set[tuple[str, str, str]],
) -> dict[str, Any]:
    forbidden_phrases = {_norm_text(claim) for claim in task.get("forbidden_claims", [])}
    if claim_support is None:
        vetoes.append(VETO_UNSUPPORTED_TECHNICAL_CLAIM)
        return {
            "claim_count": 0,
            "supported_claim_anchor_recall": _score_anchor_keys(set(), set()),
            "forbidden_claim_hits": [],
            "forbidden_claim_flags": [],
            "unsupported_nonforbidden_claims": [],
            "nonclaim_rows_in_claims": [],
            "claim_laundering_hits": [],
        }

    forbidden_hits: list[str] = []
    forbidden_flags: list[str] = []
    unsupported: list[str] = []
    nonclaim_rows = nonclaim_rows_in_claims(claim_support.get("claims", []))
    laundering_hits = claim_laundering_hits(
        claim_support,
        expected_claim_support.get("claims", []),
    )
    expected_supported_anchor_keys = {
        _anchor_key(anchor)
        for row in expected_claim_support.get("claims", [])
        if isinstance(row, dict)
        and row.get("status") == "supported"
        and row.get("support_class") == "fixture_source_support"
        for anchor in row.get("anchors", [])
        if isinstance(anchor, dict)
    }
    actual_supported_anchor_keys: set[tuple[str, str, str]] = set()
    for row in claim_support.get("claims", []):
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("claim_id", "unknown_claim"))
        claim_text = _norm_text(str(row.get("claim", "")))
        status = str(row.get("status", ""))
        support_class = str(row.get("support_class", ""))
        if _matches_forbidden_claim(claim_text, forbidden_phrases):
            if status == "forbidden" or support_class == "unsupported":
                forbidden_flags.append(claim_id)
            else:
                forbidden_hits.append(claim_id)
        elif status == "forbidden":
            forbidden_flags.append(claim_id)
        elif support_class == "unsupported" or status in {"unsupported", "source_gap"}:
            unsupported.append(claim_id)
        elif status == "supported" and support_class == "fixture_source_support":
            row_anchor_keys = {
                _anchor_key(anchor)
                for anchor in row.get("anchors", [])
                if isinstance(anchor, dict)
            }
            actual_supported_anchor_keys.update(key for key in row_anchor_keys if key in anchor_keys)
    if forbidden_hits:
        vetoes.append(VETO_FORBIDDEN_CLAIM)
    if unsupported or nonclaim_rows or laundering_hits:
        vetoes.append(VETO_UNSUPPORTED_TECHNICAL_CLAIM)
    supported_anchor_score = _score_anchor_keys(expected_supported_anchor_keys, actual_supported_anchor_keys)
    if supported_anchor_score["missing"]:
        vetoes.append(VETO_MISSING_ANCHOR)
    return {
        "claim_count": len(claim_support.get("claims", [])),
        "supported_claim_anchor_recall": supported_anchor_score,
        "forbidden_claim_hits": sorted(forbidden_hits),
        "forbidden_claim_flags": sorted(forbidden_flags),
        "unsupported_nonforbidden_claims": sorted(unsupported),
        "nonclaim_rows_in_claims": nonclaim_rows,
        "claim_laundering_hits": laundering_hits,
    }


def _score_omission_risk(
    task: dict[str, Any], omission_risk: dict[str, Any] | None
) -> dict[str, Any]:
    expected = set(task.get("required_papers", []))
    if omission_risk is None:
        return {
            "high_severity_required_paper_recall": _score_set(expected, set()),
            "high_severity_risk_count": 0,
        }
    high_risks = {
        str(row.get("paper_key"))
        for row in omission_risk.get("risks", [])
        if isinstance(row, dict)
        and row.get("paper_key")
        and str(row.get("severity", "")).lower() == "high"
    }
    required_high_risks = {
        key
        for key in expected
        if key in {"classical_ot_foundation", "normalizing_flows_review"}
    }
    return {
        "high_severity_required_paper_recall": _score_set(required_high_risks, high_risks),
        "high_severity_risk_count": len(high_risks),
    }


def score_survey_task(
    task_path: Path,
    actual_dir: Path | None = None,
) -> dict[str, Any]:
    task = load_task(task_path)
    expected_packet = load_output_packet(task, task_path)
    packet = expected_packet if actual_dir is None else load_output_packet(task, task_path, actual_dir)
    anchor_inventory = load_anchor_inventory(task, task_path)
    inventory_root = resolve_task_path(task_path, task["fixture_inputs"]["anchor_inventory"]).parent
    anchor_keys = _inventory_anchor_keys(anchor_inventory, inventory_root)
    task_id = str(task["task_id"])
    errors: list[str] = []
    vetoes: list[str] = []

    for output_name in task.get("required_outputs", []):
        payload = packet.get(output_name)
        if payload is not None and not isinstance(payload, dict):
            errors.append(f"{output_name}: output must be a JSON object")
            continue
        errors.extend(_validate_output_schema(output_name, payload, task_id, vetoes))

    scores = {
        "citation_map": _score_citation_map(task, packet.get("citation_map"), vetoes),
        "candidate_ledger": _score_candidate_ledger(
            task,
            packet.get("candidate_ledger"),
            expected_packet["candidate_ledger"],
        ),
        "source_support": _score_source_support(
            task,
            packet.get("source_support"),
            expected_packet["source_support"],
            anchor_keys,
            vetoes,
        ),
        "claim_support": _score_claim_support(
            task,
            packet.get("claim_support"),
            expected_packet["claim_support"],
            vetoes,
            anchor_keys,
        ),
        "omission_risk": _score_omission_risk(task, packet.get("omission_risk")),
    }

    required_primary_scores = [
        scores["citation_map"]["required_node_recall"]["score"],
        scores["citation_map"]["required_edge_recall"]["score"],
        scores["citation_map"]["required_cluster_recall"]["score"],
        scores["candidate_ledger"]["included_required_paper_recall"]["score"],
        scores["candidate_ledger"]["duplicate_case_recall"]["score"],
        scores["candidate_ledger"]["excluded_false_positive_recall"]["score"],
        scores["source_support"]["source_support_recall"]["score"],
        scores["source_support"]["fixture_status_accuracy"]["score"],
        scores["source_support"]["checked_anchor_recall"]["score"],
        scores["claim_support"]["supported_claim_anchor_recall"]["score"],
        scores["omission_risk"]["high_severity_required_paper_recall"]["score"],
    ]
    primary_pass = all(score == 1.0 for score in required_primary_scores)
    veto_list = sorted(set(vetoes))
    report_status = "passed" if primary_pass and not errors and not veto_list else "failed"

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "task_id": task_id,
        "fixture": str(task_path),
        "actual_dir": str(actual_dir) if actual_dir else None,
        "status": report_status,
        "scores": scores,
        "vetoes": veto_list,
        "errors": errors,
        "diagnostics": {
            "required_output_count": len(task.get("required_outputs", [])),
            "resolved_anchor_count": len(anchor_keys),
            "scored_against": "actual_dir" if actual_dir else "expected_outputs",
            "primary_pass_requires": [
                "all required node, edge, cluster, candidate, source, anchor, and high-risk omission recall scores equal 1.0",
                "no structural errors",
                "no vetoes",
            ],
            "what_is_not_concluded": [
                "real-world citation coverage",
                "scientific influence",
                "literature survey quality",
                "web search or download capability",
                "real paper source verification",
            ],
        },
    }
