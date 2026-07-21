from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_assistant.survey.artifact_lineage import read_packet_json
from research_assistant.survey.build import PUBLIC_METADATA_PACKET_FILES
from research_assistant.survey.frontier_expansion import (
    build_frontier_payloads,
    validate_frontier_context,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
    validate_generation_binding_readonly,
)


SURVEY_COVERAGE_LEDGER_RESULT_SCHEMA_VERSION = "ra-survey-coverage-ledger-result-v1"
SURVEY_COVERAGE_LEDGER_MANIFEST_SCHEMA_VERSION = "ra-survey-coverage-ledger-manifest-v1"
SURVEY_BACKWARD_SNOWBALL_SCHEMA_VERSION = "ra-survey-backward-snowball-v1"
SURVEY_FORWARD_SNOWBALL_SCHEMA_VERSION = "ra-survey-forward-snowball-v1"
SURVEY_CITATION_VENUE_METADATA_SCHEMA_VERSION = "ra-survey-citation-venue-metadata-v1"
SURVEY_OMITTED_PAPER_RISKS_SCHEMA_VERSION = "ra-survey-omitted-paper-risks-v1"

COVERAGE_LEDGER_NONCLAIMS = [
    "literature completeness",
    "technical claim support",
    "source safety",
    "live web coverage",
    "final prose readiness",
    "product readiness",
    "scientific correctness",
]

REQUIRED_PACKET_FILES = {
    "candidate_ledger": "candidate_ledger.json",
    "citation_map": "citation_map.json",
    "paper_classifications": "paper_classifications.json",
    "omission_risk": "omission_risk.json",
}


V2_FRONTIER_INPUT_FILES = {
    "identity_resolution.json",
    "relevance_ranking.json",
    "citation_map.json",
    "metadata_provenance.json",
    "omission_risk.json",
}


def build_coverage_payloads(
    *,
    topic: str,
    packet_dir: Path,
    validated_source_intake: dict[str, Any] | None = None,
    mission_anchor_generation_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty")
    packet_dir = packet_dir.resolve()
    input_paths = {name: packet_dir / file_name for name, file_name in REQUIRED_PACKET_FILES.items()}
    missing = [name for name, path in input_paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing required packet artifacts: "
            + ", ".join(f"{name}={input_paths[name]}" for name in missing)
        )
    inputs = {
        name: read_packet_json(packet_dir, path.name, label=name)
        for name, path in input_paths.items()
    }
    citation_map = inputs["citation_map"]
    candidate_ledger = inputs["candidate_ledger"]
    classifications = inputs["paper_classifications"]
    omission_risk = inputs["omission_risk"]
    payloads = {
        "backward_snowball.json": _snowball_ledger(
            topic=topic,
            citation_map=citation_map,
            candidate_ledger=candidate_ledger,
            direction="backward",
        ),
        "citation_venue_metadata.json": _citation_venue_metadata(
            topic=topic,
            candidate_ledger=candidate_ledger,
            citation_map=citation_map,
        ),
        "forward_snowball.json": _snowball_ledger(
            topic=topic,
            citation_map=citation_map,
            candidate_ledger=candidate_ledger,
            direction="forward",
        ),
        "omitted_paper_risks.json": _omitted_paper_risks(
            topic=topic,
            omission_risk=omission_risk,
            citation_map=citation_map,
        ),
        "paper_classifications.json": _classification_ledger(
            topic=topic,
            classifications=classifications,
        ),
    }
    if validated_source_intake is not None:
        status = validated_source_intake.get("status")
        authority = status.get("metadata_authority") if isinstance(status, dict) else None
        authority_schema = authority.get("schema_version") if isinstance(authority, dict) else None
        if authority_schema == "ra-survey-source-intake-metadata-authority-v2":
            context = load_v2_frontier_context(
                topic=topic,
                validated_source_intake=validated_source_intake,
                mission_anchor_generation_id=mission_anchor_generation_id,
            )
            payloads.update(build_frontier_payloads(**context))
        elif authority_schema != "ra-survey-source-intake-metadata-authority-v1":
            raise MissionStateError(
                "invalid_frontier_context",
                "replayed source intake metadata authority schema is unsupported",
            )
    return payloads


def load_v2_frontier_context(
    *,
    topic: str,
    validated_source_intake: dict[str, Any],
    mission_anchor_generation_id: str | None,
) -> dict[str, Any]:
    if not isinstance(validated_source_intake, dict):
        raise MissionStateError("invalid_frontier_context", "validated source intake must be an object")
    project_root_value = validated_source_intake.get("project_root")
    if not isinstance(project_root_value, Path) or not project_root_value.is_absolute():
        raise MissionStateError("invalid_frontier_context", "validated source intake project root is invalid")
    project_root = project_root_value
    status = validated_source_intake.get("status")
    authority = status.get("metadata_authority") if isinstance(status, dict) else None
    if (
        not isinstance(authority, dict)
        or authority.get("schema_version") != "ra-survey-source-intake-metadata-authority-v2"
    ):
        raise MissionStateError(
            "frontier_v2_metadata_authority_required",
            "canonical V2 frontier construction requires replayed V2 metadata authority",
        )
    root_value = authority.get("metadata_root")
    if not isinstance(root_value, str) or not Path(root_value).is_absolute():
        raise MissionStateError("invalid_frontier_context", "metadata authority root must be absolute")
    root = Path(root_value)
    try:
        root_mode = root.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("invalid_frontier_context", "metadata authority root is missing") from exc
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.absolute() != root
        or root != project_root / "public_metadata"
    ):
        raise MissionStateError("unsafe_frontier_context", "metadata authority root is unsafe")

    mission_id = status.get("mission_id")
    mission_fingerprint = status.get("mission_fingerprint")
    source_creation_generation_id = status.get("creation_generation_id")
    metadata_authority_sha256 = status.get("metadata_authority_sha256")
    if (
        not isinstance(mission_id, str)
        or not mission_id
        or authority.get("mission_id") != mission_id
        or not isinstance(mission_fingerprint, str)
        or authority.get("mission_fingerprint") != mission_fingerprint
        or not isinstance(source_creation_generation_id, str)
        or not source_creation_generation_id
        or not isinstance(mission_anchor_generation_id, str)
        or not mission_anchor_generation_id
        or not isinstance(metadata_authority_sha256, str)
        or metadata_authority_sha256 != sha256_bytes(canonical_json_bytes(authority))
    ):
        raise MissionStateError("foreign_frontier_context", "metadata authority mission binding is invalid")
    binding = validate_generation_binding_readonly(
        output_dir=project_root,
        mission_id=mission_id,
        mission_fingerprint=mission_fingerprint,
        generation_id=source_creation_generation_id,
        metadata_authority=authority,
    )
    if binding.get("metadata_authority_sha256") != metadata_authority_sha256:
        raise MissionStateError("metadata_authority_binding_mismatch", "metadata authority differs from creation generation")

    rows = authority.get("artifact_rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise MissionStateError("invalid_frontier_context", "metadata artifact rows must be objects")
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if set(row) != {"name", "path", "sha256", "size_bytes"}:
            raise MissionStateError("invalid_frontier_context", "metadata artifact row fields are not exact")
        name = row.get("name")
        if not isinstance(name, str) or name in by_name:
            raise MissionStateError("invalid_frontier_context", "metadata artifact names are invalid or duplicated")
        by_name[name] = row
    if list(by_name) != sorted(PUBLIC_METADATA_PACKET_FILES):
        raise MissionStateError("invalid_frontier_context", "metadata artifact rows are not exact and sorted")

    payloads: dict[str, dict[str, Any]] = {}
    digests: dict[str, str] = {}
    for name in sorted(PUBLIC_METADATA_PACKET_FILES):
        row = by_name[name]
        path = root / name
        if row.get("path") != str(path):
            raise MissionStateError("foreign_frontier_context", f"metadata artifact path differs: {name}")
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise MissionStateError("invalid_frontier_context", f"metadata artifact is missing: {name}") from exc
        if path.is_symlink() or not path.is_file():
            raise MissionStateError("unsafe_frontier_context", f"metadata artifact is unsafe: {name}")
        size = row.get("size_bytes")
        digest = row.get("sha256")
        if (
            type(size) is not int
            or size < 0
            or path.stat().st_size != size
            or not isinstance(digest, str)
            or sha256_file(path) != digest
        ):
            raise MissionStateError("stale_frontier_context", f"metadata artifact digest differs: {name}")
        digests[name] = digest
        if name not in V2_FRONTIER_INPUT_FILES:
            continue
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MissionStateError("invalid_frontier_context", f"metadata artifact is not valid JSON: {name}") from exc
        if not isinstance(payload, dict) or raw != pretty_json_bytes(payload):
            raise MissionStateError("noncanonical_frontier_context", f"metadata artifact is not canonical JSON: {name}")
        payloads[name] = payload
    context = {
        "topic": topic,
        "metadata_root": root,
        "artifact_digests": digests,
        "metadata_authority_sha256": metadata_authority_sha256,
        "metadata_artifact_rows": rows,
        "mission_id": mission_id,
        "mission_fingerprint": mission_fingerprint,
        "mission_anchor_generation_id": mission_anchor_generation_id,
        "identity_resolution": payloads["identity_resolution.json"],
        "relevance_ranking": payloads["relevance_ranking.json"],
        "citation_map": payloads["citation_map.json"],
        "metadata_provenance": payloads["metadata_provenance.json"],
        "omission_risk": payloads["omission_risk.json"],
    }
    validate_frontier_context(**context)
    return context


def compose_coverage_ledgers(
    *,
    topic: str,
    packet_dir: Path,
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    topic = topic.strip()
    if not topic:
        return _blocked("empty_topic", output_dir, ["provide --topic and rerun"])

    packet_dir = packet_dir.resolve()
    output_dir = output_dir.resolve()
    output_files = [
        "backward_snowball.json",
        "forward_snowball.json",
        "citation_venue_metadata.json",
        "paper_classifications.json",
        "omitted_paper_risks.json",
        "coverage_manifest.json",
    ]
    existing = [output_dir / name for name in output_files if (output_dir / name).exists()]
    if existing and not force:
        return {
            "schema_version": SURVEY_COVERAGE_LEDGER_RESULT_SCHEMA_VERSION,
            "status": "blocked",
            "blocked_reason": "output_exists",
            "output_dir": str(output_dir),
            "existing_artifacts": [str(path) for path in existing],
            "next_required_actions": ["rerun with --force or choose a new --out directory"],
            "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
        }

    input_paths = {name: packet_dir / file_name for name, file_name in REQUIRED_PACKET_FILES.items()}
    try:
        authoritative_payloads = build_coverage_payloads(topic=topic, packet_dir=packet_dir)
    except FileNotFoundError:
        missing = [name for name, path in input_paths.items() if not path.exists()]
        return _blocked(
            "missing_required_packet_artifact",
            output_dir,
            [f"provide {name}: {input_paths[name]}" for name in missing],
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    backward = authoritative_payloads["backward_snowball.json"]
    forward = authoritative_payloads["forward_snowball.json"]
    citation_metadata = authoritative_payloads["citation_venue_metadata.json"]
    classification_copy = authoritative_payloads["paper_classifications.json"]
    omitted = authoritative_payloads["omitted_paper_risks.json"]
    manifest = _manifest(
        topic=topic,
        output_dir=output_dir,
        input_paths=input_paths,
        backward=backward,
        forward=forward,
        omitted=omitted,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "backward_snowball.json": backward,
        "forward_snowball.json": forward,
        "citation_venue_metadata.json": citation_metadata,
        "paper_classifications.json": classification_copy,
        "omitted_paper_risks.json": omitted,
        "coverage_manifest.json": manifest,
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))

    return {
        "schema_version": SURVEY_COVERAGE_LEDGER_RESULT_SCHEMA_VERSION,
        "status": "coverage_ledgers_composed",
        "topic": topic,
        "packet_dir": str(packet_dir),
        "output_dir": str(output_dir),
        "artifact_paths": {name: str(output_dir / name) for name in payloads},
        "backward_status": backward["status"],
        "forward_status": forward["status"],
        "omitted_risk_count": omitted["risk_count"],
        "requires_live_metadata_or_source_expansion": manifest["requires_live_metadata_or_source_expansion"],
        "ready_for_prose": False,
        "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
    }


def _snowball_ledger(
    *,
    topic: str,
    citation_map: dict[str, Any],
    candidate_ledger: dict[str, Any],
    direction: str,
) -> dict[str, Any]:
    frontier = _frontier(citation_map, direction)
    relation_prefix = "backward" if direction == "backward" else "forward"
    edge_relation = "backward_reference_metadata" if direction == "backward" else "forward_citation_metadata"
    candidates_by_key = {
        str(row.get("paper_key")): row
        for row in candidate_ledger.get("included") or []
        if row.get("paper_key")
    }
    members = set(frontier.get("members") or [])
    edge_members = {
        edge.get("target") if edge.get("relation") == edge_relation else None
        for edge in citation_map.get("edges") or []
    }
    members.update(str(value) for value in edge_members if value)
    rows = []
    for paper_key in sorted(members):
        candidate = candidates_by_key.get(paper_key, {})
        rows.append({
            "paper_key": paper_key,
            "title": candidate.get("title"),
            "identifier": candidate.get("identifier"),
            "classification": candidate.get("roles") or [],
            "status": "metadata_only_candidate",
            "action": "inspect source references before using for technical support",
            "claim_support_allowed": False,
            "completeness_claim_allowed": False,
        })
    status = "present_metadata_only" if rows else "blocked_or_empty"
    if frontier.get("status"):
        status = frontier["status"]
    return {
        "schema_version": (
            SURVEY_BACKWARD_SNOWBALL_SCHEMA_VERSION
            if direction == "backward"
            else SURVEY_FORWARD_SNOWBALL_SCHEMA_VERSION
        ),
        "status": status,
        "topic": topic,
        "direction": direction,
        "frontier_status": frontier.get("status") or status,
        "frontier_reason": frontier.get("reason"),
        "metadata_relation": edge_relation,
        "candidate_count": len(rows),
        "candidates": rows,
        "evidence_policy": {
            "metadata_relations_support_navigation": True,
            "metadata_relations_support_technical_claims": False,
            "metadata_relations_support_completeness_claims": False,
        },
        "next_required_actions": [
            f"expand or source-check {direction} snowball candidates before any coverage or completeness claim",
            "record explicit omission decisions for blocked or out-of-scope candidates",
        ],
        "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
    }


def _citation_venue_metadata(
    *,
    topic: str,
    candidate_ledger: dict[str, Any],
    citation_map: dict[str, Any],
) -> dict[str, Any]:
    node_by_key = {
        str(row.get("paper_key")): row
        for row in citation_map.get("nodes") or []
        if row.get("paper_key")
    }
    rows = []
    for candidate in candidate_ledger.get("included") or []:
        paper_key = str(candidate.get("paper_key") or "")
        if not paper_key:
            continue
        node = node_by_key.get(paper_key, {})
        rows.append({
            "paper_key": paper_key,
            "title": candidate.get("title"),
            "identifier": candidate.get("identifier"),
            "year": candidate.get("year"),
            "citation_count": candidate.get("citation_count", node.get("citation_count")),
            "citation_count_policy": candidate.get("citation_count_policy") or node.get("citation_count_policy") or "coverage_signal_only",
            "venue": candidate.get("venue"),
            "venue_metric": candidate.get("venue_metric"),
            "providers": candidate.get("providers") or [],
            "metadata_only": bool(candidate.get("metadata_only", True)),
            "claim_support_allowed": False,
        })
    return {
        "schema_version": SURVEY_CITATION_VENUE_METADATA_SCHEMA_VERSION,
        "status": "metadata_signals_visible",
        "topic": topic,
        "record_count": len(rows),
        "records": rows,
        "metadata_policy": {
            "citation_counts_are_coverage_signals_only": True,
            "missing_citation_count_is_not_zero": True,
            "venue_rankings_are_not_truth_evidence": True,
            "metadata_supports_technical_claims": False,
        },
        "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
    }


def _classification_ledger(*, topic: str, classifications: dict[str, Any]) -> dict[str, Any]:
    payload = dict(classifications)
    payload["topic"] = topic
    payload["coverage_policy"] = {
        "classification_rows_support_routing": True,
        "classification_rows_support_technical_claims": False,
        "classification_rows_support_completeness_claims": False,
    }
    payload["what_is_not_concluded"] = COVERAGE_LEDGER_NONCLAIMS
    return payload


def _omitted_paper_risks(
    *,
    topic: str,
    omission_risk: dict[str, Any],
    citation_map: dict[str, Any],
) -> dict[str, Any]:
    risks = []
    for row in omission_risk.get("risks") or []:
        risks.append({
            "risk_id": row.get("risk_id"),
            "severity": row.get("severity"),
            "risk": row.get("risk") or row.get("reason"),
            "expected_action": row.get("expected_action") or row.get("next_action"),
            "status": "open",
            "literature_completeness_allowed": False,
        })
    for direction in ["backward", "forward"]:
        frontier = _frontier(citation_map, direction)
        if str(frontier.get("status") or "").startswith("blocked"):
            risk_id = f"{direction}_snowball_frontier_blocked_or_empty"
            if not any(row.get("risk_id") == risk_id for row in risks):
                risks.append({
                    "risk_id": risk_id,
                    "severity": "high",
                    "risk": frontier.get("reason") or f"{direction} snowball frontier is blocked or empty.",
                    "expected_action": f"expand {direction} snowballing or record explicit boundary approval/blocker",
                    "status": "open",
                    "literature_completeness_allowed": False,
                })
    return {
        "schema_version": SURVEY_OMITTED_PAPER_RISKS_SCHEMA_VERSION,
        "status": "omission_risks_visible",
        "topic": topic,
        "risk_count": len(risks),
        "risks": risks,
        "metadata_only_papers": omission_risk.get("metadata_only_papers") or [],
        "review_policy": {
            "omission_visibility_is_not_literature_completeness": True,
            "closed_omissions_require_reviewed_rationale": True,
        },
        "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
    }


def _manifest(
    *,
    topic: str,
    output_dir: Path,
    input_paths: dict[str, Path],
    backward: dict[str, Any],
    forward: dict[str, Any],
    omitted: dict[str, Any],
) -> dict[str, Any]:
    blocked_frontiers = [
        name
        for name, ledger in [("backward", backward), ("forward", forward)]
        if str(ledger.get("status") or "").startswith("blocked")
    ]
    return {
        "schema_version": SURVEY_COVERAGE_LEDGER_MANIFEST_SCHEMA_VERSION,
        "status": "coverage_ledgers_composed",
        "created_at": _utc_now_iso(),
        "topic": topic,
        "input_paths": {name: str(path) for name, path in input_paths.items()},
        "artifact_paths": {
            "backward_snowball.json": str(output_dir / "backward_snowball.json"),
            "forward_snowball.json": str(output_dir / "forward_snowball.json"),
            "citation_venue_metadata.json": str(output_dir / "citation_venue_metadata.json"),
            "paper_classifications.json": str(output_dir / "paper_classifications.json"),
            "omitted_paper_risks.json": str(output_dir / "omitted_paper_risks.json"),
        },
        "backward_status": backward["status"],
        "forward_status": forward["status"],
        "omitted_risk_count": omitted["risk_count"],
        "blocked_frontiers": blocked_frontiers,
        "requires_live_metadata_or_source_expansion": bool(blocked_frontiers),
        "ready_for_prose": False,
        "next_required_actions": [
            "feed omitted_paper_risks.json into omission review before hostile review",
            "request explicit bounded metadata/source approval before expanding blocked snowball frontiers",
        ],
        "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
    }


def _frontier(citation_map: dict[str, Any], frontier_id: str) -> dict[str, Any]:
    for row in citation_map.get("frontiers") or []:
        if row.get("frontier_id") == frontier_id:
            return row
    return {
        "frontier_id": frontier_id,
        "status": "blocked_or_empty",
        "reason": f"{frontier_id} snowball frontier is absent from the citation map",
        "members": [],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_COVERAGE_LEDGER_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": COVERAGE_LEDGER_NONCLAIMS,
    }
