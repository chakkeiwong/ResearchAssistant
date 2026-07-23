from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.survey.anchors import (
    ANCHOR_OUTPUT_FILES,
    SURVEY_ANCHOR_CLAIM_SUPPORT_SCHEMA_VERSION,
    SURVEY_ANCHOR_INVENTORY_SCHEMA_VERSION,
    SURVEY_ANCHOR_MANIFEST_SCHEMA_VERSION,
    SURVEY_ANCHOR_QUARANTINE_SCHEMA_VERSION,
    SURVEY_ANCHOR_SOURCE_SUPPORT_SCHEMA_VERSION,
    TECHNICAL_CLAIM_FORBIDDEN,
    _extract_anchor_rows,
    _not_concluded as _anchor_not_concluded,
    _quarantine_row,
    _quarantine_row_for_record,
    _source_gap_support_row,
    _source_support_row,
)
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.build import (
    PACKET_FILES,
    SURVEY_BUILD_MANIFEST_SCHEMA_VERSION,
    SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION,
    SURVEY_CITATION_MAP_SCHEMA_VERSION,
    SURVEY_CLAIM_SUPPORT_SCHEMA_VERSION,
    SURVEY_CLASSIFICATION_SCHEMA_VERSION,
    SURVEY_OMISSION_RISK_SCHEMA_VERSION,
    SURVEY_SOURCE_SUPPORT_SCHEMA_VERSION,
    SURVEY_WORKFLOW_STATE_SCHEMA_VERSION,
)
from research_assistant.survey.discovery_quality import PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION
from research_assistant.survey.mission_state import (
    MissionSnapshot,
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
)
from research_assistant.survey.packet import (
    OPTIONAL_INPUT_FILES,
    PUBLIC_SOURCE_PACKET_FILES,
    REQUIRED_INPUT_FILES,
    SURVEY_PUBLIC_SOURCE_PACKET_MANIFEST_SCHEMA_VERSION,
    SURVEY_PUBLIC_SOURCE_READY_SCHEMA_VERSION,
    SURVEY_PUBLIC_SOURCE_SAFETY_STATUS_SCHEMA_VERSION,
    SURVEY_PUBLIC_SOURCE_WORKFLOW_STATE_SCHEMA_VERSION,
    _composed_payloads,
)
from research_assistant.survey.source_intake import (
    SOURCE_INTAKE_STATUS_SCHEMA,
    validate_mission_source_intake,
)
from research_assistant.survey.source_selection import SOURCE_SELECTION_SCHEMA


LOCAL_SUPERVISOR_SCHEMA_VERSION = "ra-survey-local-supervisor-v1"
MAX_LOCAL_TRANSITIONS = 12
PAPER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")

_SKELETON_SCHEMAS = {
    "candidate_ledger.json": SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION,
    "citation_map.json": SURVEY_CITATION_MAP_SCHEMA_VERSION,
    "source_support.json": SURVEY_SOURCE_SUPPORT_SCHEMA_VERSION,
    "paper_classifications.json": SURVEY_CLASSIFICATION_SCHEMA_VERSION,
    "claim_support.json": SURVEY_CLAIM_SUPPORT_SCHEMA_VERSION,
    "omission_risk.json": SURVEY_OMISSION_RISK_SCHEMA_VERSION,
    "workflow_state.json": SURVEY_WORKFLOW_STATE_SCHEMA_VERSION,
    "build_manifest.json": SURVEY_BUILD_MANIFEST_SCHEMA_VERSION,
}
_ANCHOR_SCHEMAS = {
    "source_anchor_inventory.json": SURVEY_ANCHOR_INVENTORY_SCHEMA_VERSION,
    "source_support.json": SURVEY_ANCHOR_SOURCE_SUPPORT_SCHEMA_VERSION,
    "claim_support.json": SURVEY_ANCHOR_CLAIM_SUPPORT_SCHEMA_VERSION,
    "quarantine_register.json": SURVEY_ANCHOR_QUARANTINE_SCHEMA_VERSION,
    "anchor_extraction_manifest.json": SURVEY_ANCHOR_MANIFEST_SCHEMA_VERSION,
}
_PUBLIC_PACKET_SCHEMAS = {
    "candidate_ledger.json": "ra-survey-public-source-candidate-ledger-v1",
    "citation_map.json": "ra-survey-public-source-citation-map-v1",
    "source_support.json": "ra-survey-public-source-support-v1",
    "paper_classifications.json": "ra-survey-public-source-paper-classifications-v1",
    "claim_support.json": "ra-survey-public-source-claim-support-v1",
    "omission_risk.json": "ra-survey-public-source-omission-risk-v1",
    "source_safety_status.json": SURVEY_PUBLIC_SOURCE_SAFETY_STATUS_SCHEMA_VERSION,
    "ready_for_prose.json": SURVEY_PUBLIC_SOURCE_READY_SCHEMA_VERSION,
    "build_manifest.json": SURVEY_PUBLIC_SOURCE_PACKET_MANIFEST_SCHEMA_VERSION,
}
_SKELETON_KEYS = {
    "candidate_ledger.json": {
        "schema_version", "status", "topic", "candidate_count", "included",
        "excluded", "duplicates", "next_required_actions",
    },
    "citation_map.json": {
        "schema_version", "status", "topic", "seed_papers", "expansion_policy",
        "nodes", "edges", "clusters", "survey_packet_paths", "next_required_actions",
    },
    "source_support.json": {
        "schema_version", "status", "topic", "papers", "next_required_actions",
    },
    "paper_classifications.json": {
        "schema_version", "status", "topic", "classifications", "allowed_labels",
    },
    "claim_support.json": {
        "schema_version", "status", "topic", "claims", "claim_support_policy",
        "seed_papers_pending_anchor_review",
    },
    "omission_risk.json": {"schema_version", "status", "topic", "risks", "seed_papers"},
    "workflow_state.json": {
        "schema_version", "state", "mode", "ready_for_writer", "ready_for_prose",
        "safe_next_commands", "approval_required_for", "blocked_reasons", "forbidden_jumps",
    },
    "build_manifest.json": {
        "schema_version", "status", "mode", "workflow_state", "mission", "topic",
        "seed_papers", "artifact_paths", "mission_control_path", "milestones_path",
        "next_required_actions", "forbidden_claims", "what_is_not_concluded",
    },
}
_ANCHOR_KEYS = {
    "source_anchor_inventory.json": {
        "schema_version", "status", "topic", "paper_ids", "anchor_count", "anchors",
        "raw_text_policy", "not_concluded",
    },
    "source_support.json": {
        "schema_version", "status", "topic", "papers", "source_gap_rows", "not_concluded",
    },
    "claim_support.json": {
        "schema_version", "status", "topic", "claims", "blocked_claims",
        "claim_support_policy", "not_concluded",
    },
    "quarantine_register.json": {
        "schema_version", "status", "topic", "rows", "source_gap_rows", "not_concluded",
    },
    "anchor_extraction_manifest.json": {
        "schema_version", "status", "created_at", "topic", "paper_ids", "output_dir",
        "artifact_paths", "anchor_count", "source_gap_count", "ready_for_phase6",
        "ready_for_prose", "next_required_actions", "not_concluded",
    },
}
_PUBLIC_PACKET_KEYS = {
    "candidate_ledger.json": {
        "schema_version", "status", "topic", "candidate_count", "included", "duplicates",
        "excluded", "source_overlay_policy", "next_required_actions",
    },
    "citation_map.json": {
        "schema_version", "status", "topic", "nodes", "edges", "clusters", "frontiers",
        "source_boundary", "next_required_actions",
    },
    "source_support.json": {
        "schema_version", "status", "topic", "metadata_layer", "source_intake", "papers",
        "source_gap_rows", "claim_support_policy", "source_safety_status", "not_concluded",
    },
    "paper_classifications.json": {
        "schema_version", "status", "topic", "allowed_labels", "classifications",
        "source_record_paper_ids", "classification_policy",
    },
    "claim_support.json": {
        "schema_version", "status", "topic", "claims", "claim_candidates", "blocked_claims",
        "claim_support_policy", "not_concluded",
    },
    "omission_risk.json": {
        "schema_version", "status", "topic", "risks", "metadata_only_papers",
        "provider_statuses", "not_concluded",
    },
    "source_safety_status.json": {
        "schema_version", "status", "topic", "rows", "checked_clear_count",
        "blocking_count", "blocking_paper_ids", "safety_policy", "next_required_actions",
        "not_concluded",
    },
    "ready_for_prose.json": {
        "schema_version", "status", "topic", "packet_ready_for_writer", "ready_for_prose",
        "blockers", "allowed_writer_actions", "forbidden_writer_actions",
        "next_required_actions", "what_is_not_concluded",
    },
    "build_manifest.json": {
        "schema_version", "status", "created_at", "topic", "input_paths", "input_sha256",
        "artifact_paths", "anchor_count", "source_gap_count", "supported_claim_count",
        "blocked_claim_count", "source_safety_status", "source_safety_blocker_count",
        "ready_for_prose", "packet_ready_for_writer", "workflow_state",
        "privacy_and_raw_artifact_policy", "next_required_actions", "what_is_not_concluded",
    },
}
_PACKET_INPUT_SCHEMAS = {
    "metadata_candidate_ledger": {
        SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION,
        PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION,
    },
    "metadata_citation_map": {SURVEY_CITATION_MAP_SCHEMA_VERSION},
    "metadata_source_support": {SURVEY_SOURCE_SUPPORT_SCHEMA_VERSION},
    "metadata_paper_classifications": {SURVEY_CLASSIFICATION_SCHEMA_VERSION},
    "metadata_omission_risk": {SURVEY_OMISSION_RISK_SCHEMA_VERSION},
    "source_intake_status": {
        "fixture-source-intake-v1",
        "literature-survey-live-public-source-phase4-status-v1",
        "ra-survey-mission-source-intake-v1",
        SOURCE_INTAKE_STATUS_SCHEMA,
    },
    "anchor_inventory": {SURVEY_ANCHOR_INVENTORY_SCHEMA_VERSION},
    "anchor_source_support": {SURVEY_ANCHOR_SOURCE_SUPPORT_SCHEMA_VERSION},
    "anchor_claim_support": {SURVEY_ANCHOR_CLAIM_SUPPORT_SCHEMA_VERSION},
    "quarantine_register": {SURVEY_ANCHOR_QUARANTINE_SCHEMA_VERSION},
}
_PACKET_INPUT_KEYS = {
    "metadata_candidate_ledger": [
        _SKELETON_KEYS["candidate_ledger.json"],
        {
            "schema_version", "status", "topic", "candidate_count", "max_records", "included",
            "excluded", "duplicates", "provider_statuses", "raw_response_policy",
            "next_required_actions",
        },
        {
            "schema_version", "status", "topic", "candidate_count", "max_records", "included",
            "excluded", "duplicates", "identity_resolution_path", "relevance_ranking_path",
            "provider_statuses", "raw_response_policy", "next_required_actions",
        },
    ],
    "metadata_citation_map": [
        _SKELETON_KEYS["citation_map.json"],
        _SKELETON_KEYS["citation_map.json"] | {"frontiers"},
    ],
    "metadata_source_support": [_SKELETON_KEYS["source_support.json"]],
    "metadata_paper_classifications": [_SKELETON_KEYS["paper_classifications.json"]],
    "metadata_omission_risk": [
        _SKELETON_KEYS["omission_risk.json"],
        {
            "schema_version", "status", "topic", "risks", "provider_statuses",
            "metadata_only_papers",
        },
    ],
    "anchor_inventory": [_ANCHOR_KEYS["source_anchor_inventory.json"]],
    "anchor_source_support": [_ANCHOR_KEYS["source_support.json"]],
    "anchor_claim_support": [_ANCHOR_KEYS["claim_support.json"]],
    "quarantine_register": [_ANCHOR_KEYS["quarantine_register.json"]],
}


def validate_offline_skeleton(output_dir: Path) -> dict[str, Any]:
    payloads = _validate_complete_set(
        output_dir,
        expected_files=set(PACKET_FILES),
        json_schemas=_SKELETON_SCHEMAS,
        json_keys=_SKELETON_KEYS,
        label="offline skeleton",
    )
    manifest = payloads["build_manifest.json"]
    if manifest.get("mode") != "offline-skeleton" or manifest.get("status") != "created_skeleton":
        raise MissionStateError("invalid_offline_skeleton", "offline skeleton manifest has the wrong mode or status")
    _validate_artifact_paths(manifest, output_dir, set(PACKET_FILES), label="offline skeleton")
    return manifest


def validate_anchor_packet(
    output_dir: Path,
    *,
    source_status_path: Path,
    expected_topic: str,
    mission_root: Path | None = None,
    mission_snapshot: MissionSnapshot | None = None,
) -> dict[str, Any]:
    payloads = _validate_complete_set(
        output_dir,
        expected_files=set(ANCHOR_OUTPUT_FILES),
        json_schemas=_ANCHOR_SCHEMAS,
        json_keys=_ANCHOR_KEYS,
        label="source anchor packet",
    )
    manifest = payloads["anchor_extraction_manifest.json"]
    if manifest.get("status") != "created":
        raise MissionStateError("invalid_anchor_packet", "anchor manifest status is not created")
    expected_paths = {
        "source_anchor_inventory": str(output_dir.absolute() / "source_anchor_inventory.json"),
        "source_support": str(output_dir.absolute() / "source_support.json"),
        "claim_support": str(output_dir.absolute() / "claim_support.json"),
        "quarantine_register": str(output_dir.absolute() / "quarantine_register.json"),
        "anchor_extraction_manifest": str(output_dir.absolute() / "anchor_extraction_manifest.json"),
    }
    if manifest.get("artifact_paths") != expected_paths:
        raise MissionStateError("invalid_stage_manifest", "source anchor packet artifact paths differ")
    _validate_anchor_semantics(
        payloads,
        output_dir.absolute(),
        source_status_path=source_status_path,
        expected_topic=expected_topic,
        mission_root=mission_root,
        mission_snapshot=mission_snapshot,
    )
    return manifest


def validate_public_source_packet_inputs(
    *,
    metadata_dir: Path,
    source_status_dir: Path,
    anchor_dir: Path,
    mission_root: Path | None = None,
    mission_snapshot: MissionSnapshot | None = None,
) -> dict[str, Any]:
    roots = {
        "metadata_dir": validate_supervisor_read_root(metadata_dir, label="packet metadata input"),
        "source_status_dir": validate_supervisor_read_root(source_status_dir, label="packet source-status input"),
        "anchor_dir": validate_supervisor_read_root(anchor_dir, label="packet anchor input"),
    }
    source_authority = validate_source_intake_for_context(
        roots["source_status_dir"] / "phase4_source_intake_status.json",
        mission_root=mission_root,
        mission_snapshot=mission_snapshot,
    )
    payloads: dict[str, Any] = {}
    for role, (root_name, file_name) in REQUIRED_INPUT_FILES.items():
        root = roots[root_name]
        path = root / file_name
        _assert_no_symlink_chain(root, path)
        payload = _read_json_object(_regular_file(path, role), label=role)
        if payload.get("schema_version") not in _PACKET_INPUT_SCHEMAS[role]:
            raise MissionStateError(
                "invalid_packet_input_schema",
                f"public packet input has an unsupported schema: {role}",
            )
        allowed_keys = _PACKET_INPUT_KEYS.get(role)
        if allowed_keys is not None and set(payload) not in allowed_keys:
            raise MissionStateError(
                "invalid_packet_input_schema",
                f"public packet input fields differ from the exact schema: {role}",
            )
        payloads[role] = payload
    for role, (root_name, file_name) in OPTIONAL_INPUT_FILES.items():
        root = roots[root_name]
        path = root / file_name
        if not path.exists() and not path.is_symlink():
            continue
        _assert_no_symlink_chain(root, path)
        payload = _read_json_object(_regular_file(path, role), label=role)
        if payload.get("schema_version") != SOURCE_SELECTION_SCHEMA:
            raise MissionStateError(
                "invalid_packet_input_schema",
                f"public packet input has an unsupported schema: {role}",
            )
        payloads[role] = payload
    metadata_schema = payloads["metadata_candidate_ledger"].get("schema_version")
    metadata_authority = source_authority.get("metadata_authority")
    if metadata_schema == PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION:
        if (
            not isinstance(metadata_authority, dict)
            or metadata_authority.get("schema_version")
            != "ra-survey-source-intake-metadata-authority-v2"
            or metadata_authority.get("metadata_root") != str(roots["metadata_dir"])
        ):
            raise MissionStateError(
                "packet_v2_metadata_authority_mismatch",
                "V2 packet metadata root differs from the replayed V2 source-intake authority",
            )
    elif isinstance(metadata_authority, dict) and metadata_authority.get("schema_version") == "ra-survey-source-intake-metadata-authority-v2":
        raise MissionStateError(
            "packet_v2_metadata_authority_mismatch",
            "V2 source-intake authority cannot be paired with legacy metadata",
        )
    topics = {
        payload.get("topic")
        for role, payload in payloads.items()
        if role != "source_intake_status" and payload.get("topic") is not None
    }
    if len(topics) != 1:
        raise MissionStateError("packet_input_topic_mismatch", "public packet input topics differ")
    expected_topic = next(iter(topics))
    validate_anchor_packet(
        roots["anchor_dir"],
        source_status_path=roots["source_status_dir"] / "phase4_source_intake_status.json",
        expected_topic=expected_topic,
        mission_root=mission_root,
        mission_snapshot=mission_snapshot,
    )
    return payloads


def validate_public_source_packet(
    output_dir: Path,
    *,
    metadata_dir: Path,
    source_status_dir: Path,
    anchor_dir: Path,
    mission_root: Path | None = None,
    mission_snapshot: MissionSnapshot | None = None,
) -> dict[str, Any]:
    payloads = _validate_complete_set(
        output_dir,
        expected_files=set(PUBLIC_SOURCE_PACKET_FILES),
        json_schemas=_PUBLIC_PACKET_SCHEMAS,
        json_keys=_PUBLIC_PACKET_KEYS,
        label="public source packet",
    )
    manifest = payloads["build_manifest.json"]
    if manifest.get("status") != "created":
        raise MissionStateError("invalid_public_source_packet", "public source packet manifest status is not created")
    _validate_artifact_paths(manifest, output_dir, set(PUBLIC_SOURCE_PACKET_FILES), label="public source packet")
    roots = {
        "metadata_dir": metadata_dir.absolute(),
        "source_status_dir": source_status_dir.absolute(),
        "anchor_dir": anchor_dir.absolute(),
    }
    input_payloads = validate_public_source_packet_inputs(
        metadata_dir=roots["metadata_dir"],
        source_status_dir=roots["source_status_dir"],
        anchor_dir=roots["anchor_dir"],
        mission_root=mission_root,
        mission_snapshot=mission_snapshot,
    )
    expected_inputs = {
        role: roots[root_name] / file_name
        for role, (root_name, file_name) in REQUIRED_INPUT_FILES.items()
    }
    expected_inputs.update({
        role: roots[root_name] / file_name
        for role, (root_name, file_name) in OPTIONAL_INPUT_FILES.items()
        if (roots[root_name] / file_name).is_file()
        and not (roots[root_name] / file_name).is_symlink()
    })
    expected_paths = {role: str(path) for role, path in expected_inputs.items()}
    if manifest.get("input_paths") != expected_paths:
        raise MissionStateError("stale_public_source_packet", "public source packet input paths differ from current roots")
    expected_digests = {role: _sha256_file(_regular_file(path, role)) for role, path in expected_inputs.items()}
    if manifest.get("input_sha256") != expected_digests:
        raise MissionStateError("stale_public_source_packet", "public source packet input hashes differ from current inputs")
    topic = manifest.get("topic")
    input_topics = {
        payload.get("topic")
        for role, payload in input_payloads.items()
        if role != "source_intake_status" and payload.get("topic") is not None
    }
    if input_topics != {topic}:
        raise MissionStateError("packet_input_topic_mismatch", "public packet topic differs from its inputs")
    expected_payloads = _composed_payloads(
        topic=topic,
        inputs=input_payloads,
        input_paths=expected_inputs,
        output_dir=output_dir.absolute(),
    )
    expected_payloads["build_manifest.json"]["created_at"] = manifest.get("created_at")
    for name, expected in expected_payloads.items():
        actual = payloads.get(name) if name.endswith(".json") else _regular_file(output_dir / name, name).read_text()
        if actual != expected:
            raise MissionStateError(
                "invalid_public_source_packet_replay",
                f"public source packet differs from deterministic input replay: {name}",
            )
    return manifest


def classify_repairable_json(
    path: Path,
    *,
    expected_schema: str,
    expected_keys: set[str],
) -> str:
    """Classify an authoritative single JSON file before any force repair."""
    if not path.exists() and not path.is_symlink():
        return "absent"
    try:
        raw = _regular_file(path, path.name).read_bytes()
        payload = json.loads(raw)
    except (MissionStateError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "terminal_invalid"
    if not isinstance(payload, dict):
        return "terminal_invalid"
    try:
        canonical = pretty_json_bytes(payload)
    except MissionStateError:
        return "terminal_invalid"
    if raw != canonical or set(payload) != expected_keys or payload.get("schema_version") != expected_schema:
        return "terminal_invalid"
    return "replay_candidate"


def validate_source_intake_authority(status_path: Path) -> dict[str, Any]:
    status_file = _regular_file(status_path, "source intake status")
    try:
        payload = json.loads(status_file.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_source_intake", "source intake status is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_source_intake", "source intake status must be an object")
    rows = payload.get("source_support")
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise MissionStateError("invalid_source_intake", "source intake requires a nonempty source_support object list")
    legacy_hashes = payload.get("sha256")
    if legacy_hashes is not None and not isinstance(legacy_hashes, dict):
        raise MissionStateError("invalid_source_intake", "source intake sha256 must be an object")

    paper_ids: list[str] = []
    records: list[dict[str, Any]] = []
    project_root: Path | None = None
    records_root: Path | None = None
    seen: set[str] = set()
    for index, row in enumerate(rows):
        paper_id = row.get("paper_id")
        if not isinstance(paper_id, str) or PAPER_ID_RE.fullmatch(paper_id) is None:
            raise MissionStateError("invalid_source_paper_id", f"source_support[{index}].paper_id is not canonical")
        if paper_id in seen:
            raise MissionStateError("duplicate_source_paper_id", f"duplicate source paper ID: {paper_id}")
        seen.add(paper_id)
        path_value = row.get("source_record_path")
        if not isinstance(path_value, str) or not path_value or not Path(path_value).is_absolute():
            raise MissionStateError("invalid_source_record_path", f"source_support[{index}] lacks an absolute record path")
        lexical_path = Path(path_value)
        try:
            resolved_path = lexical_path.resolve(strict=True)
        except OSError as exc:
            raise MissionStateError("invalid_source_record_path", f"source record is missing: {paper_id}") from exc
        if str(lexical_path) != str(resolved_path):
            raise MissionStateError("invalid_source_record_path", f"source record path is not normalized: {paper_id}")
        expected_suffix = ("local_research", "papers", "source", "records", f"{paper_id}.json")
        if resolved_path.parts[-5:] != expected_suffix:
            raise MissionStateError("invalid_source_record_path", f"source record path does not match paper identity: {paper_id}")
        row_project_root = Path(*resolved_path.parts[:-5])
        row_records_root = row_project_root / "local_research" / "papers" / "source" / "records"
        _assert_no_symlink_chain(row_project_root, resolved_path)
        _regular_file(resolved_path, f"source record {paper_id}")
        if resolved_path.parent != row_records_root or get_paths(row_project_root).papers_source / "records" != row_records_root:
            raise MissionStateError("invalid_source_record_path", f"source record root cannot be reconstructed: {paper_id}")
        if project_root is None:
            project_root = row_project_root
            records_root = row_records_root
        elif row_project_root != project_root or row_records_root != records_root:
            raise MissionStateError("mixed_source_record_roots", "source records do not share one project source root")

        digest = row.get("source_record_sha256")
        if digest is None and isinstance(legacy_hashes, dict):
            digest = legacy_hashes.get(f"source_record_{paper_id}")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise MissionStateError("invalid_source_record_digest", f"source record digest is missing or invalid: {paper_id}")
        raw = resolved_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise MissionStateError("source_record_digest_mismatch", f"source record digest differs: {paper_id}")
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MissionStateError("invalid_source_record", f"source record is not valid JSON: {paper_id}") from exc
        if not isinstance(record, dict) or record.get("paper_id") != paper_id:
            raise MissionStateError("source_record_identity_mismatch", f"source record identity differs: {paper_id}")
        paper_ids.append(paper_id)
        records.append({"paper_id": paper_id, "path": resolved_path, "payload": record})

    assert project_root is not None and records_root is not None
    return {
        "paper_ids": paper_ids,
        "project_root": project_root,
        "records_root": records_root,
        "records": records,
        "status_path": status_file,
    }


def validate_source_intake_for_context(
    status_path: Path,
    *,
    mission_root: Path | None = None,
    mission_snapshot: MissionSnapshot | None = None,
) -> dict[str, Any]:
    """Route canonical V2 through mission replay while preserving external legacy input."""
    status_file = _regular_file(status_path, "source intake status")
    payload = _read_json_object(status_file, label="source intake status")
    if payload.get("schema_version") != SOURCE_INTAKE_STATUS_SCHEMA:
        if (
            mission_root is not None
            and status_file == mission_root.absolute() / "source_intake" / "phase4_source_intake_status.json"
        ):
            raise MissionStateError(
                "canonical_source_intake_requires_v2",
                "canonical mission-local source intake cannot use a legacy schema",
            )
        return validate_source_intake_authority(status_file)
    if mission_root is None or mission_snapshot is None:
        raise MissionStateError(
            "mission_v2_source_intake_requires_supervisor_authority",
            "V2 source intake requires the current lock-held mission supervisor",
        )
    validated = validate_mission_source_intake(
        mission_root=mission_root,
        snapshot=mission_snapshot,
        status_path=status_file,
    )
    records = []
    for record_path in validated["records"]:
        record = _read_json_object(record_path, label=f"source record {record_path.stem}")
        records.append({"paper_id": record["paper_id"], "path": record_path, "payload": record})
    return {
        "paper_ids": validated["paper_ids"],
        "project_root": validated["project_root"],
        "records_root": validated["records_root"],
        "records": records,
        "status_path": status_file,
        "v2_status": validated["status"],
        "metadata_authority": validated["status"]["metadata_authority"],
    }


def preflight_mission_output(mission_root: Path, output_dir: Path, *, name: str) -> Path:
    root = mission_root.absolute()
    target = output_dir.absolute()
    expected = root / name
    if target != expected:
        raise MissionStateError("noncanonical_supervisor_output", f"{name} output must be exactly {expected}")
    _assert_no_symlink_chain(root, target, allow_missing_leaf=True)
    assert_public_write_path_allowed(target)
    if target.exists() and not target.is_dir():
        raise MissionStateError("unsafe_supervisor_output", f"supervisor output is not a directory: {target}")
    return target


def validate_supervisor_artifact_root(
    directory: Path,
    *,
    allowed_files: set[str],
    label: str,
) -> set[str]:
    """Reject partial, stray, symlinked, or nonregular supervisor output roots."""
    root = directory.absolute()
    if not root.exists() and not root.is_symlink():
        return set()
    try:
        mode = root.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("invalid_supervisor_artifact_root", f"cannot inspect {label}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise MissionStateError("invalid_supervisor_artifact_root", f"{label} root is unsafe")
    actual = {path.name for path in root.iterdir()}
    if not actual or not actual.issubset(allowed_files):
        raise MissionStateError(
            "partial_supervisor_artifact",
            f"{label} contains an empty, stray, or partial artifact set",
            details={"actual": sorted(actual), "allowed": sorted(allowed_files)},
        )
    for name in sorted(actual):
        _regular_file(root / name, f"{label} {name}")
    return actual


def validate_supervisor_read_root(directory: Path, *, label: str) -> Path:
    root = directory.absolute()
    if not root.exists() and not root.is_symlink():
        return root
    try:
        mode = root.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("invalid_supervisor_read_root", f"cannot inspect {label}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode) or root.resolve(strict=True) != root:
        raise MissionStateError("invalid_supervisor_read_root", f"{label} root is unsafe")
    return root


def observation_sha256(observation: dict[str, Any]) -> str:
    projection = {
        "mission_id": observation.get("mission_id"),
        "mission_fingerprint": observation.get("mission_fingerprint"),
        "status": observation.get("status"),
        "next_gate": _without_time(observation.get("next_gate")),
        "next_action": _without_time(observation.get("next_action")),
        "artifact_state": _without_time(observation.get("artifact_state")),
        "phase_statuses": _without_time(observation.get("phase_statuses")),
        "reviewed_artifacts": _without_time(observation.get("reviewed_artifacts")),
        "coverage_artifacts": _without_time(observation.get("coverage_artifacts")),
        "final_artifacts": _without_time(observation.get("final_artifacts")),
    }
    return hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def _validate_complete_set(
    directory: Path,
    *,
    expected_files: set[str],
    json_schemas: dict[str, str],
    json_keys: dict[str, set[str]],
    label: str,
) -> dict[str, Any]:
    root = directory.absolute()
    if not root.exists() and not root.is_symlink():
        raise MissionStateError("missing_stage_artifact", f"{label} is absent")
    try:
        mode = root.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("invalid_stage_artifact", f"cannot inspect {label}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise MissionStateError("invalid_stage_artifact", f"{label} root is unsafe")
    actual = {path.name for path in root.iterdir()}
    if actual != expected_files:
        raise MissionStateError(
            "incomplete_stage_artifact",
            f"{label} files differ from the exact declared set",
            details={"missing": sorted(expected_files - actual), "extra": sorted(actual - expected_files)},
        )
    payloads: dict[str, Any] = {}
    for name in sorted(expected_files):
        path = _regular_file(root / name, f"{label} {name}")
        if name.endswith(".json"):
            try:
                raw = path.read_bytes()
                payload = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MissionStateError("invalid_stage_artifact", f"{label} contains invalid JSON: {name}") from exc
            if not isinstance(payload, dict) or payload.get("schema_version") != json_schemas.get(name):
                raise MissionStateError("invalid_stage_artifact", f"{label} has the wrong schema: {name}")
            if set(payload) != json_keys.get(name):
                raise MissionStateError("invalid_stage_artifact", f"{label} fields differ from the exact schema: {name}")
            expected_raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            if raw != expected_raw:
                raise MissionStateError("noncanonical_stage_artifact", f"{label} JSON is noncanonical: {name}")
            payloads[name] = payload
    return payloads


def _validate_anchor_semantics(
    payloads: dict[str, Any],
    output_dir: Path,
    *,
    source_status_path: Path,
    expected_topic: str,
    mission_root: Path | None = None,
    mission_snapshot: MissionSnapshot | None = None,
) -> None:
    inventory = payloads["source_anchor_inventory.json"]
    support = payloads["source_support.json"]
    claims = payloads["claim_support.json"]
    quarantine = payloads["quarantine_register.json"]
    manifest = payloads["anchor_extraction_manifest.json"]
    topics = {
        payload.get("topic")
        for payload in (inventory, support, claims, quarantine, manifest)
    }
    if topics != {expected_topic}:
        raise MissionStateError("invalid_anchor_packet", "anchor packet topics differ")
    paper_ids = inventory.get("paper_ids")
    if (
        not isinstance(paper_ids, list)
        or not paper_ids
        or any(not isinstance(value, str) or PAPER_ID_RE.fullmatch(value) is None for value in paper_ids)
        or len(set(paper_ids)) != len(paper_ids)
        or manifest.get("paper_ids") != paper_ids
    ):
        raise MissionStateError("invalid_anchor_packet", "anchor paper identities are incomplete or inconsistent")
    anchors = inventory.get("anchors")
    if not isinstance(anchors, list) or any(not isinstance(row, dict) for row in anchors):
        raise MissionStateError("invalid_anchor_packet", "anchor inventory rows are invalid")
    anchor_keys: set[tuple[str, str]] = set()
    anchors_by_paper: dict[str, list[str]] = {paper_id: [] for paper_id in paper_ids}
    for index, row in enumerate(anchors):
        paper_id = row.get("paper_id")
        anchor_id = row.get("anchor_id")
        if paper_id not in anchors_by_paper or not isinstance(anchor_id, str) or not anchor_id:
            raise MissionStateError("invalid_anchor_packet", f"anchor row {index} has invalid identity")
        key = (paper_id, anchor_id)
        if key in anchor_keys:
            raise MissionStateError("invalid_anchor_packet", "anchor identities are not unique")
        anchor_keys.add(key)
        anchors_by_paper[paper_id].append(anchor_id)
    if inventory.get("anchor_count") != len(anchors) or manifest.get("anchor_count") != len(anchors):
        raise MissionStateError("invalid_anchor_packet", "anchor counts differ across artifacts")
    if inventory.get("status") != ("anchors_extracted" if anchors else "no_checked_anchors"):
        raise MissionStateError("invalid_anchor_packet", "anchor inventory status differs from its rows")

    source_rows = support.get("papers")
    if not isinstance(source_rows, list) or any(not isinstance(row, dict) for row in source_rows):
        raise MissionStateError("invalid_anchor_packet", "anchor source-support rows are invalid")
    source_ids = [row.get("paper_id") for row in source_rows]
    if source_ids != paper_ids or len(set(source_ids)) != len(source_ids):
        raise MissionStateError("invalid_anchor_packet", "source-support identities differ from the inventory")
    for row in source_rows:
        paper_id = row["paper_id"]
        checked = row.get("checked_anchors")
        if checked != anchors_by_paper[paper_id] or row.get("checked_anchor_count") != len(checked):
            raise MissionStateError("invalid_anchor_packet", f"checked anchors differ for {paper_id}")
    gap_rows = support.get("source_gap_rows")
    quarantine_gaps = quarantine.get("source_gap_rows")
    if not isinstance(gap_rows, list) or gap_rows != quarantine_gaps:
        raise MissionStateError("invalid_anchor_packet", "anchor source-gap ledgers differ")
    if manifest.get("source_gap_count") != len(gap_rows):
        raise MissionStateError("invalid_anchor_packet", "anchor source-gap counts differ")
    if support.get("status") != ("source_anchors_available" if anchors else "source_gaps_or_no_anchors"):
        raise MissionStateError("invalid_anchor_packet", "anchor source-support status differs from its rows")
    quarantine_rows = quarantine.get("rows")
    if (
        not isinstance(quarantine_rows, list)
        or any(not isinstance(row, dict) for row in quarantine_rows)
        or [row.get("paper_id") for row in quarantine_rows] != paper_ids
    ):
        raise MissionStateError("invalid_anchor_packet", "quarantine identities differ from the inventory")
    if claims.get("claims") != [] or claims.get("status") != "anchors_extracted_no_supported_technical_claims":
        raise MissionStateError("invalid_anchor_packet", "anchor packet cannot contain supported claim rows")
    blocked = claims.get("blocked_claims")
    if not isinstance(blocked, list) or len(blocked) != 1 or blocked[0].get("paper_ids") != paper_ids:
        raise MissionStateError("invalid_anchor_packet", "anchor blocked-claim authority differs from its paper set")
    if manifest.get("output_dir") != str(output_dir):
        raise MissionStateError("invalid_anchor_packet", "anchor manifest output directory differs")
    if manifest.get("ready_for_phase6") is not bool(anchors) or manifest.get("ready_for_prose") is not False:
        raise MissionStateError("invalid_anchor_packet", "anchor readiness fields differ from packet semantics")
    _validate_anchor_replay(
        payloads,
        output_dir=output_dir,
        source_status_path=source_status_path,
        expected_topic=expected_topic,
        mission_root=mission_root,
        mission_snapshot=mission_snapshot,
    )


def _validate_anchor_replay(
    payloads: dict[str, Any],
    *,
    output_dir: Path,
    source_status_path: Path,
    expected_topic: str,
    mission_root: Path | None = None,
    mission_snapshot: MissionSnapshot | None = None,
) -> None:
    authority = validate_source_intake_for_context(
        source_status_path,
        mission_root=mission_root,
        mission_snapshot=mission_snapshot,
    )
    paper_ids = authority["paper_ids"]
    source_rows: list[dict[str, Any]] = []
    anchor_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    source_gap_rows: list[dict[str, Any]] = []
    for entry in authority["records"]:
        paper_id = entry["paper_id"]
        source_path = entry["path"]
        record = entry["payload"]
        if record.get("status") != "available":
            gap = {
                "paper_id": paper_id,
                "source_record_path": str(source_path),
                "source_status": record.get("status") or "source_gap",
                "reason": "structured source record is not available",
                "claim_support_allowed": False,
            }
            source_rows.append(_source_gap_support_row(gap))
            quarantine_rows.append(_quarantine_row(gap, status="source_gap"))
            source_gap_rows.append(gap)
            continue
        rows = _extract_anchor_rows(
            paper_id=paper_id,
            source_path=source_path,
            record=record,
            max_anchors=24,
        )
        anchor_rows.extend(rows)
        source_rows.append(_source_support_row(paper_id, source_path, record, rows))
        quarantine_rows.append(_quarantine_row_for_record(paper_id, source_path, record, rows))

    nonclaims = _anchor_not_concluded()
    expected = {
        "source_anchor_inventory.json": {
            "schema_version": SURVEY_ANCHOR_INVENTORY_SCHEMA_VERSION,
            "status": "anchors_extracted" if anchor_rows else "no_checked_anchors",
            "topic": expected_topic,
            "paper_ids": paper_ids,
            "anchor_count": len(anchor_rows),
            "anchors": anchor_rows,
            "raw_text_policy": {
                "raw_latex_included": False,
                "raw_full_text_included": False,
                "anchor_hashes_included": True,
                "reason": "Phase 5 writes review pointers and hashes; raw source remains in local_research source records.",
            },
            "not_concluded": nonclaims,
        },
        "source_support.json": {
            "schema_version": SURVEY_ANCHOR_SOURCE_SUPPORT_SCHEMA_VERSION,
            "status": "source_anchors_available" if anchor_rows else "source_gaps_or_no_anchors",
            "topic": expected_topic,
            "papers": source_rows,
            "source_gap_rows": source_gap_rows,
            "not_concluded": nonclaims,
        },
        "claim_support.json": {
            "schema_version": SURVEY_ANCHOR_CLAIM_SUPPORT_SCHEMA_VERSION,
            "status": "anchors_extracted_no_supported_technical_claims",
            "topic": expected_topic,
            "claims": [],
            "blocked_claims": [{
                "claim_id": "phase5_no_unmapped_technical_claims",
                "status": "blocked",
                "support_class": "source_gap_pending_claim_mapping",
                "reason": TECHNICAL_CLAIM_FORBIDDEN,
                "available_anchor_count": len(anchor_rows),
                "paper_ids": paper_ids,
            }],
            "claim_support_policy": {
                "technical_claims_require_checked_anchors": True,
                "metadata_only_support_allowed_for_technical_claims": False,
                "source_availability_support_allowed_for_technical_claims": False,
                "titles_abstracts_and_provider_snippets_do_not_support_technical_claims": True,
                "raw_anchor_text_must_be_retrieved_from_local_source_record_for_review": True,
            },
            "not_concluded": nonclaims,
        },
        "quarantine_register.json": {
            "schema_version": SURVEY_ANCHOR_QUARANTINE_SCHEMA_VERSION,
            "status": "no_retraction_check_phase5_anchor_extraction_only",
            "topic": expected_topic,
            "rows": quarantine_rows,
            "source_gap_rows": source_gap_rows,
            "not_concluded": nonclaims,
        },
    }
    manifest = payloads["anchor_extraction_manifest.json"]
    try:
        created_at = manifest["created_at"]
        parsed = datetime.fromisoformat(created_at)
    except (KeyError, TypeError, ValueError) as exc:
        raise MissionStateError("invalid_anchor_packet", "anchor manifest created_at is invalid") from exc
    if parsed.tzinfo is None:
        raise MissionStateError("invalid_anchor_packet", "anchor manifest created_at lacks a timezone")
    expected["anchor_extraction_manifest.json"] = {
        "schema_version": SURVEY_ANCHOR_MANIFEST_SCHEMA_VERSION,
        "status": "created",
        "created_at": created_at,
        "topic": expected_topic,
        "paper_ids": paper_ids,
        "output_dir": str(output_dir),
        "artifact_paths": {
            "source_anchor_inventory": str(output_dir / "source_anchor_inventory.json"),
            "source_support": str(output_dir / "source_support.json"),
            "claim_support": str(output_dir / "claim_support.json"),
            "quarantine_register": str(output_dir / "quarantine_register.json"),
            "anchor_extraction_manifest": str(output_dir / "anchor_extraction_manifest.json"),
        },
        "anchor_count": len(anchor_rows),
        "source_gap_count": len(source_gap_rows),
        "ready_for_phase6": bool(anchor_rows),
        "ready_for_prose": False,
        "next_required_actions": [
            "compose Phase 6 evidence packet with source gaps and unchecked-claim blockers visible",
            "map any proposed technical claim to one or more anchor ids before prose drafting",
            "run retraction/version checks before using anchors as primary technical support",
        ],
        "not_concluded": nonclaims,
    }
    for name, expected_payload in expected.items():
        if payloads[name] != expected_payload:
            raise MissionStateError(
                "invalid_anchor_packet_replay",
                f"source anchor packet differs from attested source-record replay: {name}",
            )


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_packet_input", f"{label} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_packet_input", f"{label} must be a JSON object")
    return payload


def _validate_artifact_paths(manifest: dict[str, Any], root: Path, names: set[str], *, label: str) -> None:
    expected = {name: str(root.absolute() / name) for name in names}
    if manifest.get("artifact_paths") != expected:
        raise MissionStateError("invalid_stage_manifest", f"{label} artifact paths differ from the exact output set")


def _regular_file(path: Path, label: str) -> Path:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("unsafe_artifact_file", f"{label} is missing or unreadable") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise MissionStateError("unsafe_artifact_file", f"{label} is not a regular non-symlink file")
    return path


def _assert_no_symlink_chain(root: Path, target: Path, *, allow_missing_leaf: bool = False) -> None:
    root = root.absolute()
    target = target.absolute()
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise MissionStateError("outside_supervisor_root", "path is outside the declared root") from exc
    current = root
    paths = [root]
    for part in relative.parts:
        current = current / part
        paths.append(current)
    for index, path in enumerate(paths):
        if not path.exists() and not path.is_symlink():
            if allow_missing_leaf and all(not later.exists() and not later.is_symlink() for later in paths[index:]):
                break
            raise MissionStateError("unsafe_path_chain", f"path component is missing: {path}")
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise MissionStateError("unsafe_path_chain", f"path component is a symlink: {path}")
        if index < len(paths) - 1 and not stat.S_ISDIR(mode):
            raise MissionStateError("unsafe_path_chain", f"path parent is not a directory: {path}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _without_time(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_time(child)
            for key, child in sorted(value.items())
            if key not in {"created_at", "updated_at", "confirmed_at", "last_attempt"}
        }
    if isinstance(value, list):
        return [_without_time(child) for child in value]
    return value


__all__ = [
    "LOCAL_SUPERVISOR_SCHEMA_VERSION",
    "MAX_LOCAL_TRANSITIONS",
    "classify_repairable_json",
    "observation_sha256",
    "preflight_mission_output",
    "validate_supervisor_artifact_root",
    "validate_supervisor_read_root",
    "validate_anchor_packet",
    "validate_offline_skeleton",
    "validate_public_source_packet",
    "validate_source_intake_authority",
]
