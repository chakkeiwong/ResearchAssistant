"""Evidence-gated central-candidate assessment without proxy-score promotion."""

from __future__ import annotations

import json
from pathlib import Path
import stat
from typing import Any

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, pretty_json_bytes, sha256_bytes
from research_assistant.survey.topic_contract import topic_contract_sha256, validate_topic_contract


CENTRALITY_EVIDENCE_SCHEMA = "ra-survey-centrality-evidence-v1"
CENTRALITY_ASSESSMENT_SCHEMA = "ra-survey-centrality-assessment-v1"
CENTRALITY_MANIFEST_SCHEMA = "ra-survey-centrality-manifest-v1"
ROLES = {
    "BACKGROUND", "COMPETITOR", "DIRECT_METHOD", "EMPIRICAL_EXAMPLE",
    "FOUNDATIONAL", "IMPLEMENTATION_OR_SOFTWARE", "PERIPHERAL",
    "RETRACTED_OR_QUARANTINED", "SOURCE_BLOCKED", "SUPERSEDED",
    "SURVEY_OR_TUTORIAL",
}
CENTRAL_ROLES = {"FOUNDATIONAL", "DIRECT_METHOD", "COMPETITOR", "SURVEY_OR_TUTORIAL"}
VERDICTS = {
    "BLOCKED", "PERIPHERAL", "QUARANTINED", "REJECTED_OFF_TOPIC",
    "VALIDATED_CENTRAL", "VALIDATED_RELEVANT",
}


def _fail(message: str) -> None:
    raise MissionStateError("invalid_centrality_evidence", message)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"{field} must be nonempty text")
    return " ".join(value.split())


def _list(value: Any, field: str, *, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(value, list):
        _fail(f"{field} must be a list")
    rows = sorted({_text(item, f"{field}[]") for item in value})
    if len(rows) != len(value):
        _fail(f"{field} must contain unique sorted values")
    if allowed is not None and not set(rows) <= allowed:
        _fail(f"{field} contains unsupported values")
    return rows


def validate_centrality_evidence(value: Any, *, expected_contract_sha256: str | None = None) -> dict[str, Any]:
    expected = {"schema_version", "topic_contract_sha256", "candidates", "what_is_not_concluded"}
    if not isinstance(value, dict) or set(value) != expected:
        _fail("centrality evidence fields are not exact")
    if value["schema_version"] != CENTRALITY_EVIDENCE_SCHEMA:
        _fail("centrality evidence schema is unsupported")
    digest = _text(value["topic_contract_sha256"], "topic_contract_sha256").casefold()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        _fail("topic_contract_sha256 must be lowercase SHA-256")
    if expected_contract_sha256 is not None and digest != expected_contract_sha256:
        _fail("centrality evidence is bound to a different topic contract")
    rows = value["candidates"]
    if not isinstance(rows, list) or len(rows) > 300:
        _fail("candidates must be a bounded list")
    normalized = [_candidate(row, index) for index, row in enumerate(rows)]
    ids = [row["paper_id"] for row in normalized]
    if ids != sorted(set(ids)):
        _fail("candidate paper_ids must be unique and sorted")
    return {
        "schema_version": CENTRALITY_EVIDENCE_SCHEMA,
        "topic_contract_sha256": digest,
        "candidates": normalized,
        "what_is_not_concluded": _list(value["what_is_not_concluded"], "what_is_not_concluded"),
    }


def _candidate(value: Any, index: int) -> dict[str, Any]:
    field = f"candidates[{index}]"
    expected = {
        "paper_id", "title", "identity_status", "source_status", "source_safety",
        "topic_fit", "roles", "inspected_anchors", "discovery_routes",
        "backward_mentions", "forward_citations", "survey_mentions",
        "omission_risk_status", "citation_count", "venue_metric_status",
        "evidence_refs", "source_safety_evidence", "reviewer_provenance",
        "limitations",
    }
    if not isinstance(value, dict) or set(value) != expected:
        _fail(f"{field} fields are not exact")
    identity = _text(value["identity_status"], f"{field}.identity_status")
    source = _text(value["source_status"], f"{field}.source_status")
    safety = _text(value["source_safety"], f"{field}.source_safety")
    topic_fit = _text(value["topic_fit"], f"{field}.topic_fit")
    risk = _text(value["omission_risk_status"], f"{field}.omission_risk_status")
    venue = _text(value["venue_metric_status"], f"{field}.venue_metric_status")
    if identity not in {"resolved", "conflict", "unresolved"}:
        _fail(f"{field}.identity_status is unsupported")
    if source not in {"inspected", "metadata_only", "source_blocked"}:
        _fail(f"{field}.source_status is unsupported")
    if safety not in {"clear", "not_checked", "quarantined"}:
        _fail(f"{field}.source_safety is unsupported")
    if topic_fit not in {"direct", "foundational", "relevant", "peripheral", "off_topic", "not_checked"}:
        _fail(f"{field}.topic_fit is unsupported")
    if risk not in {"closed", "none", "open", "partially_closed"}:
        _fail(f"{field}.omission_risk_status is unsupported")
    if venue not in {"available", "not_available"}:
        _fail(f"{field}.venue_metric_status is unsupported")
    citation = value["citation_count"]
    if citation is not None and (type(citation) is not int or citation < 0):
        _fail(f"{field}.citation_count is invalid")
    safety_evidence = _list(
        value["source_safety_evidence"], f"{field}.source_safety_evidence"
    )
    reviewer_provenance = _list(
        value["reviewer_provenance"], f"{field}.reviewer_provenance"
    )
    limitations = _list(value["limitations"], f"{field}.limitations")
    if safety in {"clear", "quarantined"} and not safety_evidence:
        _fail(f"{field}.source_safety_evidence is required for {safety} status")
    if not reviewer_provenance:
        _fail(f"{field}.reviewer_provenance must not be empty")
    if not limitations:
        _fail(f"{field}.limitations must not be empty")
    return {
        "paper_id": _text(value["paper_id"], f"{field}.paper_id").casefold(),
        "title": _text(value["title"], f"{field}.title"),
        "identity_status": identity,
        "source_status": source,
        "source_safety": safety,
        "topic_fit": topic_fit,
        "roles": _list(value["roles"], f"{field}.roles", allowed=ROLES),
        "inspected_anchors": _list(value["inspected_anchors"], f"{field}.inspected_anchors"),
        "discovery_routes": _list(value["discovery_routes"], f"{field}.discovery_routes"),
        "backward_mentions": _list(value["backward_mentions"], f"{field}.backward_mentions"),
        "forward_citations": _list(value["forward_citations"], f"{field}.forward_citations"),
        "survey_mentions": _list(value["survey_mentions"], f"{field}.survey_mentions"),
        "omission_risk_status": risk,
        "citation_count": citation,
        "venue_metric_status": venue,
        "evidence_refs": _list(value["evidence_refs"], f"{field}.evidence_refs"),
        "source_safety_evidence": safety_evidence,
        "reviewer_provenance": reviewer_provenance,
        "limitations": limitations,
    }


def assess_centrality(topic_contract: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    contract = validate_topic_contract(topic_contract)
    contract_digest = topic_contract_sha256(contract)
    evidence = validate_centrality_evidence(evidence, expected_contract_sha256=contract_digest)
    rows = [_assess_candidate(row) for row in evidence["candidates"]]
    return {
        "schema_version": CENTRALITY_ASSESSMENT_SCHEMA,
        "status": "centrality_assessed",
        "topic": contract["topic"],
        "topic_contract_sha256": contract_digest,
        "centrality_evidence_sha256": sha256_bytes(canonical_json_bytes(evidence)),
        "assessments": rows,
        "counts": {verdict: sum(row["verdict"] == verdict for row in rows) for verdict in sorted(VERDICTS)},
        "promotion_policy": "hard_vetoes_then_source_grounded_role_and_independent_signal",
        "metadata_priority_can_promote": False,
        "what_is_not_concluded": [
            "literature completeness", "scientific correctness", "topic recall",
            "validity of paper claims",
        ],
    }


def validate_centrality_output(
    output_dir: Path,
    *,
    expected_topic: str | None = None,
) -> dict[str, Any]:
    """Replay a persisted assessment from its bound contract and evidence."""
    root = output_dir.absolute()
    assessment_path = root / "centrality_assessment.json"
    manifest_path = root / "centrality_manifest.json"
    for path, label in (
        (assessment_path, "centrality assessment"),
        (manifest_path, "centrality manifest"),
    ):
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise MissionStateError(
                "invalid_centrality_output", f"{label} is missing"
            ) from exc
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise MissionStateError(
                "invalid_centrality_output", f"{label} must be a regular non-symlink file"
            )
    assessment = load_json(assessment_path, label="centrality assessment")
    manifest = load_json(manifest_path, label="centrality manifest")
    expected_manifest_fields = {
        "schema_version", "topic_contract_path", "topic_contract_sha256",
        "centrality_evidence_path", "centrality_evidence_sha256",
        "centrality_assessment_path", "centrality_assessment_sha256",
        "benchmark_labels_consumed",
    }
    if set(manifest) != expected_manifest_fields or manifest.get("schema_version") != CENTRALITY_MANIFEST_SCHEMA:
        raise MissionStateError(
            "invalid_centrality_output", "centrality manifest fields or schema are invalid"
        )
    if manifest.get("benchmark_labels_consumed") is not False:
        raise MissionStateError(
            "invalid_centrality_output", "centrality output reports benchmark-label consumption"
        )
    if Path(str(manifest.get("centrality_assessment_path"))).absolute() != assessment_path:
        raise MissionStateError(
            "invalid_centrality_output", "centrality assessment path binding is stale or foreign"
        )
    contract_path = Path(str(manifest.get("topic_contract_path")))
    evidence_path = Path(str(manifest.get("centrality_evidence_path")))
    for path, label in ((contract_path, "topic contract"), (evidence_path, "centrality evidence")):
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise MissionStateError(
                "invalid_centrality_output", f"bound {label} is missing"
            ) from exc
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise MissionStateError(
                "invalid_centrality_output", f"bound {label} must be a regular non-symlink file"
            )
    contract = validate_topic_contract(load_json(contract_path, label="topic contract"))
    evidence = validate_centrality_evidence(
        load_json(evidence_path, label="centrality evidence"),
        expected_contract_sha256=topic_contract_sha256(contract),
    )
    replayed = assess_centrality(contract, evidence)
    expected_hashes = {
        "topic_contract_sha256": topic_contract_sha256(contract),
        "centrality_evidence_sha256": sha256_bytes(canonical_json_bytes(evidence)),
        "centrality_assessment_sha256": sha256_bytes(canonical_json_bytes(replayed)),
    }
    for field, digest in expected_hashes.items():
        if manifest.get(field) != digest:
            raise MissionStateError(
                "invalid_centrality_output", f"centrality manifest {field} binding differs"
            )
    if assessment != replayed:
        raise MissionStateError(
            "invalid_centrality_output", "centrality assessment differs from replayed evidence"
        )
    if expected_topic is not None and assessment["topic"] != expected_topic:
        raise MissionStateError(
            "invalid_centrality_output", "centrality assessment belongs to a different topic"
        )
    return {
        "assessment": assessment,
        "manifest": manifest,
        "assessment_path": str(assessment_path),
        "manifest_path": str(manifest_path),
    }


def _assess_candidate(row: dict[str, Any]) -> dict[str, Any]:
    vetoes: list[str] = []
    if row["identity_status"] != "resolved":
        vetoes.append(f"identity_{row['identity_status']}")
    if row["source_safety"] == "quarantined" or "RETRACTED_OR_QUARANTINED" in row["roles"]:
        vetoes.append("source_quarantined")
    if row["topic_fit"] == "off_topic":
        vetoes.append("off_topic")
    if row["topic_fit"] == "peripheral" or "PERIPHERAL" in row["roles"]:
        vetoes.append("peripheral")
    if row["source_status"] != "inspected" or not row["inspected_anchors"]:
        vetoes.append("primary_source_topic_fit_not_inspected")
    if row["source_safety"] != "clear":
        vetoes.append("source_safety_not_clear")
    independent = (
        len(row["backward_mentions"]) >= 2
        or bool(row["forward_citations"])
        or bool(row["survey_mentions"])
    )
    central_role = bool(set(row["roles"]) & CENTRAL_ROLES)
    central_fit = row["topic_fit"] in {"direct", "foundational"}
    source_inspected = row["source_status"] == "inspected" and bool(row["inspected_anchors"])
    if "source_quarantined" in vetoes:
        verdict = "QUARANTINED"
    elif "off_topic" in vetoes and source_inspected:
        verdict = "REJECTED_OFF_TOPIC"
    elif "peripheral" in vetoes and source_inspected:
        verdict = "PERIPHERAL"
    elif vetoes:
        verdict = "BLOCKED"
    elif central_role and central_fit and independent:
        verdict = "VALIDATED_CENTRAL"
    else:
        verdict = "VALIDATED_RELEVANT"
    return {
        "paper_id": row["paper_id"],
        "title": row["title"],
        "verdict": verdict,
        "roles": row["roles"],
        "hard_vetoes": sorted(vetoes),
        "requirements": {
            "central_role": central_role,
            "direct_or_foundational_topic_fit": central_fit,
            "independent_centrality_signal": independent,
            "primary_source_inspected": source_inspected,
        },
        "diagnostics": {
            "citation_count": row["citation_count"],
            "venue_metric_status": row["venue_metric_status"],
            "discovery_route_count": len(row["discovery_routes"]),
            "backward_mention_count": len(row["backward_mentions"]),
            "forward_citation_count": len(row["forward_citations"]),
            "survey_mention_count": len(row["survey_mentions"]),
            "discovery_routes_are_explanatory_only": True,
        },
        "evidence_refs": row["evidence_refs"],
        "source_safety_evidence": row["source_safety_evidence"],
        "reviewer_provenance": row["reviewer_provenance"],
        "limitations": row["limitations"],
        "metadata_priority_can_promote": False,
    }


def load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_centrality_input", f"{label} is not readable JSON") from exc
    if not isinstance(value, dict):
        raise MissionStateError("invalid_centrality_input", f"{label} must be an object")
    return value


def write_centrality_assessment(
    *, topic_contract_path: Path, evidence_path: Path, output_dir: Path, force: bool = False
) -> dict[str, Any]:
    contract = validate_topic_contract(load_json(topic_contract_path, label="topic contract"))
    evidence = validate_centrality_evidence(
        load_json(evidence_path, label="centrality evidence"),
        expected_contract_sha256=topic_contract_sha256(contract),
    )
    assessment = assess_centrality(contract, evidence)
    output_dir = output_dir.resolve()
    assert_public_write_path_allowed(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assessment_path = output_dir / "centrality_assessment.json"
    manifest_path = output_dir / "centrality_manifest.json"
    if any(path.exists() for path in (assessment_path, manifest_path)) and not force:
        raise MissionStateError("output_exists", "centrality output exists; use --force or a fresh directory")
    assessment_raw = pretty_json_bytes(assessment)
    manifest = {
        "schema_version": CENTRALITY_MANIFEST_SCHEMA,
        "topic_contract_path": str(topic_contract_path.resolve()),
        "topic_contract_sha256": topic_contract_sha256(contract),
        "centrality_evidence_path": str(evidence_path.resolve()),
        "centrality_evidence_sha256": sha256_bytes(canonical_json_bytes(evidence)),
        "centrality_assessment_path": str(assessment_path),
        "centrality_assessment_sha256": sha256_bytes(canonical_json_bytes(assessment)),
        "benchmark_labels_consumed": False,
    }
    atomic_write_bytes(assessment_path, assessment_raw)
    atomic_write_bytes(manifest_path, pretty_json_bytes(manifest))
    return {
        "schema_version": CENTRALITY_ASSESSMENT_SCHEMA,
        "status": "centrality_assessment_written",
        "output_dir": str(output_dir),
        "assessment": assessment,
        "manifest": manifest,
    }


__all__ = [
    "CENTRALITY_ASSESSMENT_SCHEMA", "CENTRALITY_EVIDENCE_SCHEMA",
    "CENTRALITY_MANIFEST_SCHEMA", "CENTRAL_ROLES", "ROLES", "VERDICTS",
    "assess_centrality", "validate_centrality_evidence",
    "validate_centrality_output", "write_centrality_assessment",
]
