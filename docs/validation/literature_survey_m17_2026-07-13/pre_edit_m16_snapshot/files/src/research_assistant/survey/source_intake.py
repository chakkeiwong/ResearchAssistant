from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from research_assistant.survey.build import (
    PUBLIC_METADATA_BUILD_MANIFEST_SCHEMA_VERSION,
    PUBLIC_METADATA_PACKET_FILES,
    SURVEY_BUILD_MANIFEST_SCHEMA_VERSION,
    SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION,
    SURVEY_WORKFLOW_STATE_SCHEMA_VERSION,
    validate_public_metadata_v2_bundle,
)
from research_assistant.survey.discovery_quality import PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION
from research_assistant.survey.mission_state import (
    MissionSnapshot,
    MissionStateError,
    canonical_json_bytes,
    normalize_seeds,
    pretty_json_bytes,
    sha256_bytes,
    validate_budget,
    validate_generation_binding_readonly,
)


SOURCE_INTAKE_CAPABILITY_SCHEMA = "ra-survey-mission-source-capability-v1"
SOURCE_INTAKE_OUTCOMES_SCHEMA = "ra-survey-mission-source-intake-outcomes-v2"
SOURCE_INTAKE_STATUS_SCHEMA = "ra-survey-mission-source-intake-v2"
SOURCE_INTAKE_STAGE_RESULT_SCHEMA = "ra-survey-mission-source-intake-stage-result-v1"
METADATA_AUTHORITY_SCHEMA = "ra-survey-source-intake-metadata-authority-v1"
METADATA_AUTHORITY_V2_SCHEMA = "ra-survey-source-intake-metadata-authority-v2"

OUTCOMES_FILE = "source_intake_outcomes.json"
STATUS_FILE = "phase4_source_intake_status.json"
METADATA_PACKET_FILES = {
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
    "workflow_state.json",
    "survey_packet.md",
    "build_manifest.json",
    "metadata_provenance.json",
}
PAPER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

OUTCOME_STATUSES = {
    "available",
    "metadata_only",
    "unavailable",
    "quarantined",
    "duplicate",
    "failed",
    "unsupported_identifier",
    "not_attempted_cap",
}
OUTCOME_CODES = {
    "available",
    "metadata_only",
    "unavailable",
    "quarantined",
    "duplicate_identical",
    "handler_failed",
    "invalid_capability_result",
    "unsupported_identifier",
    "source_count_cap",
    "byte_budget_exceeded",
}

STRUCTURED_RECORD_KEYS = {
    "paper_id",
    "source_type",
    "status",
    "primary_for_audit",
    "artifact_root",
    "original_source_path",
    "flattened_source_path",
    "sections",
    "equations",
    "theorem_like_blocks",
    "labels",
    "references",
    "citations",
    "bibliography",
    "macros",
    "provenance",
    "diagnostics",
    "limitations",
}
PATH_RECORD_KEYS = {"artifact_root", "original_source_path", "flattened_source_path"}
LIST_RECORD_KEYS = {
    "sections",
    "equations",
    "theorem_like_blocks",
    "labels",
    "references",
    "citations",
    "bibliography",
    "macros",
    "limitations",
}
ROW_KEYS = {
    "sections": {"level", "command", "title", "line", "labels", "raw_latex"},
    "equations": {"environment", "line", "labels", "raw_latex"},
    "theorem_like_blocks": {"environment", "line", "labels", "raw_latex"},
    "labels": {"key", "line"},
    "references": {"command", "key", "line"},
    "citations": {"command", "keys", "line"},
    "bibliography": {"type", "key", "fields", "path"},
    "macros": {"command", "name", "arguments", "definition", "line"},
    "limitations": {"field", "status", "note"},
}
ROW_REQUIRED_KEYS = {
    "sections": {"title", "line", "labels", "raw_latex"},
    "equations": {"environment", "line", "labels", "raw_latex"},
    "theorem_like_blocks": {"environment", "line", "labels", "raw_latex"},
    "labels": {"key", "line"},
    "references": {"command", "key", "line"},
    "citations": {"command", "keys", "line"},
    "bibliography": {"type", "key", "fields", "path"},
    "macros": {"command", "name", "arguments", "definition", "line"},
    "limitations": {"field", "status", "note"},
}
PROVENANCE_KEYS = {"arxiv_id", "identifier", "provider", "final_url", "fixture_only"}
DIAGNOSTIC_KEYS = {
    "source_bytes",
    "section_count",
    "equation_count",
    "theorem_like_block_count",
    "fixture_only",
}

CANDIDATE_PROJECTION_KEYS = {"candidate_id", "identifier", "roles", "providers"}
OUTCOME_KEYS = {
    "candidate_id",
    "identifier",
    "paper_id",
    "candidate_index",
    "outcome_status",
    "code",
    "cap_kind",
    "provider",
    "final_url",
    "source_record_path",
    "source_record_sha256",
    "source_record_size_bytes",
}
SOURCE_SUPPORT_KEYS = {
    "paper_id",
    "candidate_id",
    "identifier",
    "provider",
    "final_url",
    "source_record_path",
    "source_record_sha256",
    "source_record_size_bytes",
    "source_status",
    "technical_claim_support",
}
AUTHORITY_KEYS = {
    "schema_version",
    "mission_id",
    "mission_fingerprint",
    "normalized_topic_key",
    "normalized_seed_keys",
    "metadata_root",
    "candidate_ledger_path",
    "candidate_ledger_sha256",
    "candidate_ledger_size_bytes",
    "build_manifest_path",
    "build_manifest_sha256",
    "build_manifest_size_bytes",
    "candidate_set_sha256",
    "candidate_count",
}
V2_AUTHORITY_KEYS = {*AUTHORITY_KEYS, "artifact_rows"}
V2_AUTHORITY_ARTIFACT_KEYS = {"name", "path", "sha256", "size_bytes"}


@dataclass(frozen=True)
class SourceCandidateRequest:
    candidate_id: str
    identifier: str
    paper_id: str
    roles: tuple[str, ...]
    providers: tuple[str, ...]
    candidate_index: int
    allowed_providers: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    max_source_records: int
    max_bytes_per_source: int


@dataclass(frozen=True)
class SourceCapabilityResult:
    candidate_id: str
    identifier: str
    outcome_status: str
    code: str
    provider: str | None = None
    final_url: str | None = None
    structured_record: dict[str, Any] | None = None
    declared_record_sha256: str | None = None
    byte_count: int = 0


@dataclass(frozen=True)
class MissionSourceCapability:
    handler: Callable[[SourceCandidateRequest], SourceCapabilityResult]
    schema_version: str = SOURCE_INTAKE_CAPABILITY_SCHEMA
    fixture_only: bool = True


def derive_source_paper_id(identifier: str) -> str:
    if not isinstance(identifier, str):
        raise MissionStateError("unsupported_source_identifier", "source identifier must be a string")
    normalized = identifier.strip().lower()
    if not normalized or "\x00" in normalized:
        raise MissionStateError("unsupported_source_identifier", "source identifier is empty or contains NUL")
    stem = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:72]
    if not stem:
        stem = "unsupported"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    paper_id = f"paper_{stem}_{digest}"
    if PAPER_ID_RE.fullmatch(paper_id) is None:
        raise MissionStateError("unsupported_source_identifier", "derived source paper ID is invalid")
    return paper_id


def _supports_source_identifier(candidate: dict[str, Any]) -> bool:
    identifier = candidate["identifier"].strip().lower()
    providers = set(candidate["providers"])
    prefix, separator, value = identifier.partition(":")
    if not separator or not value.strip():
        return False
    if prefix == "arxiv":
        return "arxiv" in providers
    if prefix in {"doi", "openalex"}:
        return "openalex" in providers
    return False


def _shared_keys() -> set[str]:
    return {
        "mission_id",
        "mission_fingerprint",
        "creation_generation_id",
        "mission_contract_sha256",
        "mission_control_sha256",
        "next_action_sha256",
        "metadata_authority_sha256",
        "normalized_topic",
        "normalized_seed_keys",
        "public_discovery_confirmation",
        "discovery_budget",
        "metadata_authority",
        "candidates",
    }


def _ledger_keys() -> set[str]:
    return {
        "schema_version",
        "status",
        *_shared_keys(),
        "outcomes",
        "counts",
        "accepted_record_bytes",
        "privacy_policy",
        "claim_support_policy",
        "next_required_actions",
        "what_is_not_concluded",
    }


def _status_keys() -> set[str]:
    return {
        "schema_version",
        "status",
        "created_at",
        *_shared_keys(),
        "outcome_ledger_path",
        "outcome_ledger_sha256",
        "outcome_ledger_size_bytes",
        "source_support",
        "authoritative_paper_ids",
        "counts",
        "accepted_record_bytes",
        "completion_classification",
        "ready_for_claim_support",
        "privacy_policy",
        "claim_support_policy",
        "next_required_actions",
        "what_is_not_concluded",
    }


def _nonclaims() -> list[str]:
    return [
        "live provider reliability",
        "source or parser correctness beyond fixtures",
        "retraction or version safety",
        "technical claim support or truth",
        "literature or survey completeness",
        "scientific correctness",
        "final prose, product, or release readiness",
    ]


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise MissionStateError("invalid_source_intake_schema", f"{label} keys are not exact")
    return value


def _string_list(value: Any, *, label: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(row, str) or not row or "\x00" in row for row in value
    ):
        raise MissionStateError("invalid_source_intake_schema", f"{label} must contain nonempty strings")
    if not allow_empty and not value:
        raise MissionStateError("invalid_source_intake_schema", f"{label} must not be empty")
    if len(set(value)) != len(value):
        raise MissionStateError("invalid_source_intake_schema", f"{label} must not contain duplicates")
    return list(value)


def _outcome_base(candidate: dict[str, Any], *, paper_id: str, index: int) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "identifier": candidate["identifier"],
        "paper_id": paper_id,
        "candidate_index": index,
    }


def _empty_outcome(
    status: str,
    code: str,
    cap_kind: str | None,
    *,
    provider: str | None = None,
    final_url: str | None = None,
) -> dict[str, Any]:
    return {
        "outcome_status": status,
        "code": code,
        "cap_kind": cap_kind,
        "provider": provider,
        "final_url": final_url,
        "source_record_path": None,
        "source_record_sha256": None,
        "source_record_size_bytes": None,
    }


def build_source_intake_metadata_authority(
    *,
    mission_root: Path,
    metadata_root: Path,
    snapshot: MissionSnapshot,
) -> dict[str, Any]:
    mission = mission_root.absolute()
    root = metadata_root.absolute()
    if root != mission / "public_metadata":
        raise MissionStateError(
            "noncanonical_source_metadata_root",
            "Phase 6 source intake requires the exact mission-local public_metadata root",
        )
    _assert_safe_directory(root, label="public metadata")
    ledger_path = _regular_file(root / "candidate_ledger.json", root=root, label="candidate ledger")
    manifest_path = _regular_file(root / "build_manifest.json", root=root, label="build manifest")
    ledger, ledger_raw = _read_builder_json(ledger_path, label="candidate ledger")
    manifest, manifest_raw = _read_builder_json(manifest_path, label="build manifest")
    child_names = {path.name for path in root.iterdir()}
    v2_discriminators = {
        "identity_resolution.json",
        "relevance_ranking.json",
    }
    if (
        ledger.get("schema_version") == PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION
        or manifest.get("schema_version") == PUBLIC_METADATA_BUILD_MANIFEST_SCHEMA_VERSION
        or bool(child_names & v2_discriminators)
    ):
        return _build_v2_source_intake_metadata_authority(
            mission=mission,
            root=root,
            snapshot=snapshot,
        )
    candidates = _validate_metadata_payloads(
        ledger=ledger,
        manifest=manifest,
        metadata_root=root,
        snapshot=snapshot,
    )
    return {
        "schema_version": METADATA_AUTHORITY_SCHEMA,
        "mission_id": snapshot.contract["mission_id"],
        "mission_fingerprint": snapshot.contract["mission_fingerprint"],
        "normalized_topic_key": snapshot.contract["normalized_topic"]["key"],
        "normalized_seed_keys": [row["key"] for row in snapshot.contract["normalized_seeds"]],
        "metadata_root": str(root),
        "candidate_ledger_path": str(ledger_path),
        "candidate_ledger_sha256": sha256_bytes(ledger_raw),
        "candidate_ledger_size_bytes": len(ledger_raw),
        "build_manifest_path": str(manifest_path),
        "build_manifest_sha256": sha256_bytes(manifest_raw),
        "build_manifest_size_bytes": len(manifest_raw),
        "candidate_set_sha256": sha256_bytes(canonical_json_bytes(candidates)),
        "candidate_count": len(candidates),
    }


def _build_v2_source_intake_metadata_authority(
    *,
    mission: Path,
    root: Path,
    snapshot: MissionSnapshot,
) -> dict[str, Any]:
    budget = validate_budget(snapshot.contract["discovery_budget"])
    validated = validate_public_metadata_v2_bundle(
        topic=snapshot.contract["normalized_topic"]["display"],
        seeds=[row["display"] for row in snapshot.contract["normalized_seeds"]],
        output_dir=root,
        providers=budget["providers"],
        max_records=budget["max_metadata_records"],
    )
    if validated["quality_status"] != "eligible":
        raise MissionStateError(
            "source_metadata_seed_resolution_blocked",
            "public metadata V2 seed-resolution gate is blocked",
        )
    candidates = _candidate_projection(validated["candidates"], allow_empty_roles=True)
    if not candidates:
        raise MissionStateError("invalid_source_metadata", "public metadata V2 has no intake candidates")
    if len({row["candidate_id"] for row in candidates}) != len(candidates):
        raise MissionStateError("duplicate_source_candidate", "candidate IDs must be unique")
    allowed_providers = set(budget["providers"])
    if any(not set(row["providers"]).issubset(allowed_providers) for row in candidates):
        raise MissionStateError(
            "source_candidate_provider_mismatch",
            "candidate providers exceed the persisted mission provider budget",
        )
    artifact_rows = validated["artifact_rows"]
    by_name = {row["name"]: row for row in artifact_rows}
    ledger_row = by_name["candidate_ledger.json"]
    manifest_row = by_name["build_manifest.json"]
    return {
        "schema_version": METADATA_AUTHORITY_V2_SCHEMA,
        "mission_id": snapshot.contract["mission_id"],
        "mission_fingerprint": snapshot.contract["mission_fingerprint"],
        "normalized_topic_key": snapshot.contract["normalized_topic"]["key"],
        "normalized_seed_keys": [row["key"] for row in snapshot.contract["normalized_seeds"]],
        "metadata_root": str(root),
        "candidate_ledger_path": ledger_row["path"],
        "candidate_ledger_sha256": ledger_row["sha256"],
        "candidate_ledger_size_bytes": ledger_row["size_bytes"],
        "build_manifest_path": manifest_row["path"],
        "build_manifest_sha256": manifest_row["sha256"],
        "build_manifest_size_bytes": manifest_row["size_bytes"],
        "candidate_set_sha256": sha256_bytes(canonical_json_bytes(candidates)),
        "candidate_count": len(candidates),
        "artifact_rows": artifact_rows,
    }


def _validate_metadata_payloads(
    *,
    ledger: dict[str, Any],
    manifest: dict[str, Any],
    metadata_root: Path,
    snapshot: MissionSnapshot,
) -> list[dict[str, Any]]:
    _require_exact_keys(
        ledger,
        {
            "schema_version",
            "status",
            "topic",
            "candidate_count",
            "max_records",
            "included",
            "excluded",
            "duplicates",
            "provider_statuses",
            "raw_response_policy",
            "next_required_actions",
        },
        "candidate ledger",
    )
    if (
        ledger["schema_version"] != SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION
        or ledger["status"] != "metadata_only_public"
    ):
        raise MissionStateError("invalid_source_metadata", "candidate ledger is not public metadata")
    if ledger["topic"] != snapshot.contract["normalized_topic"]["display"]:
        raise MissionStateError("source_metadata_topic_mismatch", "candidate ledger topic differs from mission")
    included = ledger["included"]
    if not isinstance(included, list) or not included:
        raise MissionStateError("invalid_source_metadata", "candidate ledger requires included candidates")
    if (
        isinstance(ledger["candidate_count"], bool)
        or not isinstance(ledger["candidate_count"], int)
        or ledger["candidate_count"] != len(included)
    ):
        raise MissionStateError("source_candidate_count_mismatch", "candidate_count differs from included rows")
    budget = validate_budget(snapshot.contract["discovery_budget"])
    if (
        ledger["candidate_count"] > budget["max_metadata_records"]
        or ledger["max_records"] != budget["max_metadata_records"]
    ):
        raise MissionStateError("source_metadata_budget_mismatch", "metadata count/cap differs from mission budget")
    if ledger["excluded"] != [] or ledger["duplicates"] != []:
        raise MissionStateError(
            "invalid_source_metadata",
            "Phase 6 candidate authority requires all exclusions and duplicates resolved upstream",
        )
    candidates = _candidate_projection(included)
    if len({row["candidate_id"] for row in candidates}) != len(candidates):
        raise MissionStateError("duplicate_source_candidate", "candidate IDs must be unique")
    allowed_providers = set(budget["providers"])
    if any(not set(row["providers"]).issubset(allowed_providers) for row in candidates):
        raise MissionStateError(
            "source_candidate_provider_mismatch",
            "candidate providers exceed the persisted mission provider budget",
        )
    _require_exact_keys(
        manifest,
        {
            "schema_version",
            "status",
            "mode",
            "workflow_state",
            "mission",
            "topic",
            "providers",
            "max_records",
            "record_count",
            "provider_statuses",
            "artifact_paths",
            "mission_control_path",
            "milestones_path",
            "next_required_actions",
            "forbidden_claims",
            "what_is_not_concluded",
        },
        "build manifest",
    )
    if (
        manifest.get("schema_version") != SURVEY_BUILD_MANIFEST_SCHEMA_VERSION
        or manifest.get("status") != "metadata_only_packet"
        or manifest.get("mode") != "public-metadata"
    ):
        raise MissionStateError("invalid_source_metadata_manifest", "build manifest is not public metadata")
    if manifest.get("topic") != snapshot.contract["normalized_topic"]["display"]:
        raise MissionStateError("source_metadata_manifest_mismatch", "build manifest topic differs")
    if (
        isinstance(manifest.get("record_count"), bool)
        or not isinstance(manifest.get("record_count"), int)
        or manifest.get("record_count") != len(candidates)
        or manifest.get("max_records") != budget["max_metadata_records"]
    ):
        raise MissionStateError("source_metadata_manifest_mismatch", "build manifest count/cap differs")
    providers = _string_list(manifest.get("providers"), label="build manifest providers")
    if set(providers) != set(budget["providers"]):
        raise MissionStateError("source_metadata_provider_mismatch", "build manifest providers differ from mission budget")
    paths = manifest.get("artifact_paths")
    if not isinstance(paths, dict) or set(paths) != METADATA_PACKET_FILES:
        raise MissionStateError("invalid_source_metadata_manifest", "build manifest artifact_paths is invalid")
    for name in METADATA_PACKET_FILES:
        if paths[name] != str(metadata_root / name):
            raise MissionStateError("source_metadata_path_mismatch", f"build manifest path differs for {name}")
    workflow = manifest.get("workflow_state")
    _require_exact_keys(
        workflow,
        {
            "schema_version",
            "state",
            "mode",
            "ready_for_writer",
            "ready_for_prose",
            "safe_next_commands",
            "approval_required_for",
            "blocked_reasons",
            "forbidden_jumps",
        },
        "metadata workflow state",
    )
    if (
        workflow.get("schema_version") != SURVEY_WORKFLOW_STATE_SCHEMA_VERSION
        or workflow.get("state") != "metadata_only_public_packet"
        or workflow.get("mode") != "public-metadata"
        or workflow.get("ready_for_writer") is not True
        or workflow.get("ready_for_prose") is not False
    ):
        raise MissionStateError("invalid_source_metadata_workflow", "metadata workflow state is not safely metadata-only")
    for key in ("safe_next_commands", "approval_required_for", "blocked_reasons", "forbidden_jumps"):
        _string_list(workflow[key], label=f"metadata workflow {key}", allow_empty=True)
    seed_keys = {row["key"] for row in snapshot.contract["normalized_seeds"]}
    resolved_seed_keys = {
        normalize_seeds([row["identifier"]])[0]["key"]
        for row in included
        if isinstance(row, dict) and "seed" in row.get("roles", [])
    }
    if not seed_keys.issubset(resolved_seed_keys):
        raise MissionStateError(
            "source_metadata_seed_coverage_mismatch",
            "metadata does not cover every normalized mission seed",
        )
    return candidates


def _candidate_projection(
    rows: list[Any],
    *,
    allow_empty_roles: bool = False,
) -> list[dict[str, Any]]:
    expected = {
        "paper_key",
        "identifier",
        "title",
        "authors",
        "year",
        "roles",
        "providers",
        "citation_count",
        "citation_count_policy",
        "reason",
        "metadata_only",
    }
    candidates: list[dict[str, Any]] = []
    for index, value in enumerate(rows):
        row = _require_exact_keys(value, expected, f"candidate[{index}]")
        candidate_id = row["paper_key"]
        identifier = row["identifier"]
        if not isinstance(candidate_id, str) or not candidate_id or "\x00" in candidate_id:
            raise MissionStateError("invalid_source_candidate", "candidate ID must be a nonempty string")
        if not isinstance(identifier, str) or not identifier.strip() or "\x00" in identifier:
            raise MissionStateError("invalid_source_candidate", "candidate identifier must be a nonempty string")
        roles = _string_list(
            row["roles"],
            label="candidate roles",
            allow_empty=allow_empty_roles,
        )
        providers = _string_list(row["providers"], label="candidate providers")
        if row["metadata_only"] is not True or row["citation_count_policy"] != "coverage_signal_only":
            raise MissionStateError("invalid_source_candidate", "candidate is not metadata-only coverage evidence")
        candidates.append(
            {
                "candidate_id": candidate_id,
                "identifier": identifier.strip(),
                "roles": roles,
                "providers": providers,
            }
        )
    return candidates


def _validated_capability_outcome(
    *,
    request: SourceCandidateRequest,
    result: SourceCapabilityResult,
    budget: dict[str, Any],
    remaining_bytes: int,
) -> tuple[dict[str, Any], bytes | None]:
    if not isinstance(result, SourceCapabilityResult):
        raise MissionStateError("invalid_capability_result", "capability result must use the closed Phase 6 type")
    if (
        not isinstance(result.candidate_id, str)
        or not isinstance(result.identifier, str)
        or result.candidate_id != request.candidate_id
        or result.identifier != request.identifier
    ):
        raise MissionStateError("capability_identity_mismatch", "capability result identity differs from request")
    if (
        not isinstance(result.outcome_status, str)
        or not isinstance(result.code, str)
        or result.outcome_status not in OUTCOME_STATUSES
        or result.code not in OUTCOME_CODES
    ):
        raise MissionStateError("invalid_capability_result", "capability outcome status/code is not closed")
    if isinstance(result.byte_count, bool) or not isinstance(result.byte_count, int) or result.byte_count < 0:
        raise MissionStateError("source_record_byte_mismatch", "declared record byte count is invalid")
    allowed_pairs = {
        ("available", "available"),
        ("metadata_only", "metadata_only"),
        ("unavailable", "unavailable"),
        ("quarantined", "quarantined"),
        ("failed", "handler_failed"),
        ("failed", "invalid_capability_result"),
    }
    if (result.outcome_status, result.code) not in allowed_pairs:
        raise MissionStateError("invalid_capability_result", "capability outcome status/code pair is invalid")
    if result.provider is not None:
        if not isinstance(result.provider, str) or (
            result.provider not in budget["providers"] or result.provider not in request.providers
        ):
            raise MissionStateError("invalid_capability_provider", "capability result provider is not authorized")
    if result.declared_record_sha256 is not None and not isinstance(result.declared_record_sha256, str):
        raise MissionStateError("source_record_digest_mismatch", "declared record digest is not a string")
    if result.outcome_status != "available":
        if (
            result.structured_record is not None
            or result.declared_record_sha256 is not None
            or result.final_url is not None
            or result.byte_count != 0
        ):
            raise MissionStateError("invalid_capability_result", "nonavailable outcome cannot carry source authority")
        return _empty_outcome(result.outcome_status, result.code, None, provider=result.provider), None

    if result.provider is None:
        raise MissionStateError("invalid_capability_provider", "available result requires an authorized provider")
    _validate_public_url(result.final_url, budget["allowed_domains"])
    record = result.structured_record
    if not isinstance(record, dict):
        raise MissionStateError("invalid_structured_source_record", "available result requires a structured record")
    _validate_structured_record(record, paper_id=request.paper_id)
    provenance = record["provenance"]
    if (
        provenance.get("identifier") != request.identifier
        or provenance.get("provider") != result.provider
        or provenance.get("final_url") != result.final_url
        or provenance.get("fixture_only") is not True
    ):
        raise MissionStateError(
            "source_record_provenance_mismatch",
            "record provenance differs from the capability request/result",
        )
    record_bytes = pretty_json_bytes(record)
    if (
        isinstance(result.byte_count, bool)
        or not isinstance(result.byte_count, int)
        or result.byte_count != len(record_bytes)
    ):
        raise MissionStateError("source_record_byte_mismatch", "declared and adapter-measured record bytes differ")
    if result.declared_record_sha256 is not None:
        if (
            HEX64_RE.fullmatch(result.declared_record_sha256) is None
            or result.declared_record_sha256 != sha256_bytes(record_bytes)
        ):
            raise MissionStateError("source_record_digest_mismatch", "declared record digest differs")
    if len(record_bytes) > budget["max_bytes_per_source"] or len(record_bytes) > remaining_bytes:
        return (
            _empty_outcome(
                "failed",
                "byte_budget_exceeded",
                None,
                provider=result.provider,
            ),
            record_bytes,
        )
    return (
        {
            "outcome_status": "available",
            "code": "available",
            "cap_kind": None,
            "provider": result.provider,
            "final_url": result.final_url,
            "source_record_path": None,
            "source_record_sha256": None,
            "source_record_size_bytes": len(record_bytes),
        },
        record_bytes,
    )


def _validate_structured_record(record: dict[str, Any], *, paper_id: str) -> None:
    _require_exact_keys(record, STRUCTURED_RECORD_KEYS, "structured source record")
    if record["paper_id"] != paper_id or record["status"] != "available":
        raise MissionStateError("source_record_identity_mismatch", "record identity/status differs from request")
    if not isinstance(record["source_type"], str) or record["source_type"] not in {
        "arxiv_latex",
        "publisher_xml",
        "grobid_tei",
        "pdf_parser",
        "pdf_text",
    }:
        raise MissionStateError("invalid_structured_source_record", "source_type is not in the closed available set")
    if not isinstance(record["primary_for_audit"], bool):
        raise MissionStateError("invalid_structured_source_record", "primary_for_audit must be boolean")
    if any(record[key] is not None for key in PATH_RECORD_KEYS):
        raise MissionStateError("capability_path_field_forbidden", "capability-returned record paths must be null")
    for key in LIST_RECORD_KEYS:
        rows = record[key]
        if not isinstance(rows, list):
            raise MissionStateError("invalid_structured_source_record", f"{key} must be a list")
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise MissionStateError("invalid_structured_source_record", f"{key}[{index}] must be an object")
            if not ROW_REQUIRED_KEYS[key].issubset(row) or not set(row).issubset(ROW_KEYS[key]):
                raise MissionStateError("invalid_structured_source_record", f"{key}[{index}] keys are not closed")
            _validate_nested_row(key, row)
    for key, allowed in (("provenance", PROVENANCE_KEYS), ("diagnostics", DIAGNOSTIC_KEYS)):
        value = record[key]
        if not isinstance(value, dict) or not set(value).issubset(allowed):
            raise MissionStateError("invalid_structured_source_record", f"{key} keys are not closed")
        _reject_path_or_private_keys(value, label=key)
        for child in value.values():
            if not isinstance(child, (str, int, bool, type(None))) or isinstance(child, float):
                raise MissionStateError("invalid_structured_source_record", f"{key} values must be closed scalars")
    arxiv_id = record["provenance"].get("arxiv_id")
    if arxiv_id is not None and not isinstance(arxiv_id, str):
        raise MissionStateError("invalid_structured_source_record", "provenance.arxiv_id must be a string or null")
    diagnostics = record["diagnostics"]
    if "fixture_only" in diagnostics and diagnostics["fixture_only"] is not True:
        raise MissionStateError("invalid_structured_source_record", "diagnostics.fixture_only must be true")
    for key in DIAGNOSTIC_KEYS - {"fixture_only"}:
        if key in diagnostics and (
            isinstance(diagnostics[key], bool)
            or not isinstance(diagnostics[key], int)
            or diagnostics[key] < 0
        ):
            raise MissionStateError("invalid_structured_source_record", f"diagnostics.{key} must be nonnegative")
    canonical_json_bytes(record)


def _validate_nested_row(kind: str, row: dict[str, Any]) -> None:
    _reject_path_or_private_keys(row, label=kind, allow_bibliography_path=kind == "bibliography")
    for key in ("level", "line"):
        if key in row and (
            isinstance(row[key], bool) or not isinstance(row[key], int) or row[key] <= 0
        ):
            raise MissionStateError("invalid_structured_source_record", f"{kind}.{key} must be positive")
    for key in ("labels", "keys"):
        if key in row:
            _string_list(row[key], label=f"{kind}.{key}", allow_empty=True)
    if kind == "bibliography":
        if row["path"] is not None:
            raise MissionStateError("capability_path_field_forbidden", "bibliography path must be null")
        fields = row["fields"]
        if not isinstance(fields, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in fields.items()
        ):
            raise MissionStateError(
                "invalid_structured_source_record",
                "bibliography fields must map strings to strings",
            )
        _reject_path_or_private_keys(fields, label="bibliography.fields")
    for key, value in row.items():
        if key not in {"level", "line", "labels", "keys", "fields", "path"} and not isinstance(value, str):
            raise MissionStateError("invalid_structured_source_record", f"{kind}.{key} must be a string")


def _validate_public_url(value: str | None, allowed_domains: list[str]) -> None:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise MissionStateError("invalid_source_url", "available source requires a public HTTPS URL")
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise MissionStateError("invalid_source_url", "source URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port is not None
        or parsed.fragment
    ):
        raise MissionStateError(
            "invalid_source_url",
            "source URL must be credential-free HTTPS without port or fragment",
        )
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        allowed = {domain.encode("idna").decode("ascii").lower() for domain in allowed_domains}
    except UnicodeError as exc:
        raise MissionStateError("invalid_source_url", "source URL hostname is not valid IDNA") from exc
    if host not in allowed:
        raise MissionStateError("source_domain_not_allowed", "source URL hostname is not an exact allowed domain")


def _reject_path_or_private_keys(
    value: dict[str, Any],
    *,
    label: str,
    allow_bibliography_path: bool = False,
) -> None:
    for key in value:
        lowered = key.lower()
        if any(fragment in lowered for fragment in ("password", "credential", "secret", "token", "api_key")):
            raise MissionStateError("private_source_field_forbidden", f"{label} contains a private field")
        if "path" in lowered and not (allow_bibliography_path and lowered == "path"):
            raise MissionStateError("capability_path_field_forbidden", f"{label} contains a path field")


def run_mission_source_intake(
    *,
    mission_root: Path,
    metadata_root: Path,
    snapshot: MissionSnapshot,
    capability: MissionSourceCapability,
    crash_hook: Callable[[str], None] | None = None,
    now: Callable[[], str] = lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
) -> dict[str, Any]:
    mission = mission_root.absolute()
    if snapshot.current_pointer is None:
        raise MissionStateError("missing_source_intake_generation", "source intake requires a committed generation")
    if snapshot.contract["public_discovery_confirmation"].get("confirmed") is not True:
        raise MissionStateError(
            "source_intake_confirmation_required",
            "persisted public-discovery confirmation is required",
        )
    if not isinstance(capability, MissionSourceCapability):
        raise MissionStateError("invalid_source_capability", "source capability must use the closed Phase 6 type")
    if capability.schema_version != SOURCE_INTAKE_CAPABILITY_SCHEMA or capability.fixture_only is not True:
        raise MissionStateError(
            "invalid_source_capability",
            "Phase 6 permits only the fixture-only capability schema",
        )

    authority = build_source_intake_metadata_authority(
        mission_root=mission,
        metadata_root=metadata_root,
        snapshot=snapshot,
    )
    generation_id = snapshot.current_pointer["generation_id"]
    binding = validate_generation_binding_readonly(
        output_dir=mission,
        mission_id=snapshot.contract["mission_id"],
        mission_fingerprint=snapshot.contract["mission_fingerprint"],
        generation_id=generation_id,
        metadata_authority=authority,
    )
    ledger, _ = _read_builder_json(Path(authority["candidate_ledger_path"]), label="candidate ledger")
    candidates = _candidate_projection(
        ledger["included"],
        allow_empty_roles=ledger.get("schema_version") == PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION,
    )
    budget = validate_budget(snapshot.contract["discovery_budget"])

    intake_root = mission / "source_intake"
    records_root = mission / "local_research" / "papers" / "source" / "records"
    _preflight_output_root(
        mission,
        intake_root,
        exact_allowed={OUTCOMES_FILE, STATUS_FILE},
        allowed_subset=None,
        label="source intake",
    )
    expected_record_names = {
        f"{derive_source_paper_id(row['identifier'])}.json"
        for row in candidates
        if _supports_source_identifier(row)
    }
    _preflight_output_root(
        mission,
        records_root,
        exact_allowed=None,
        allowed_subset=expected_record_names,
        label="source records",
    )
    status_path = intake_root / STATUS_FILE
    if status_path.exists() or status_path.is_symlink():
        validated = validate_mission_source_intake(
            mission_root=mission,
            snapshot=snapshot,
            status_path=status_path,
        )
        return {
            "schema_version": SOURCE_INTAKE_STAGE_RESULT_SCHEMA,
            "status": "reused_complete_status",
            "required_output_paths": validated["required_output_paths"],
            "source_support_count": len(validated["paper_ids"]),
            "outcome_count": len(validated["outcomes"]),
        }
    ledger_path = intake_root / OUTCOMES_FILE
    if ledger_path.exists() or ledger_path.is_symlink():
        raise MissionStateError(
            "partial_source_intake_residue",
            "outcome ledger exists without the status commit marker",
        )

    outcomes: list[dict[str, Any]] = []
    source_support: list[dict[str, Any]] = []
    accepted_bytes = 0
    exhausted_bytes = False
    max_calls = budget["max_source_records"]
    capability_calls = 0
    cumulative_cap = max_calls * budget["max_bytes_per_source"]
    seen_papers: dict[str, tuple[Path, bytes]] = {}

    for index, candidate in enumerate(candidates):
        paper_id = derive_source_paper_id(candidate["identifier"])
        base = _outcome_base(candidate, paper_id=paper_id, index=index)
        if exhausted_bytes:
            outcomes.append(
                {
                    **base,
                    **_empty_outcome(
                        "not_attempted_cap",
                        "byte_budget_exceeded",
                        "cumulative_bytes",
                    ),
                }
            )
            continue
        if capability_calls >= max_calls:
            outcomes.append(
                {
                    **base,
                    **_empty_outcome("not_attempted_cap", "source_count_cap", "source_count"),
                }
            )
            continue
        if not _supports_source_identifier(candidate):
            outcomes.append(
                {
                    **base,
                    **_empty_outcome("unsupported_identifier", "unsupported_identifier", None),
                }
            )
            continue
        capability_calls += 1
        request = SourceCandidateRequest(
            candidate_id=candidate["candidate_id"],
            identifier=candidate["identifier"],
            paper_id=paper_id,
            roles=tuple(candidate["roles"]),
            providers=tuple(candidate["providers"]),
            candidate_index=index,
            allowed_providers=tuple(budget["providers"]),
            allowed_domains=tuple(budget["allowed_domains"]),
            max_source_records=max_calls,
            max_bytes_per_source=budget["max_bytes_per_source"],
        )
        try:
            capability_result = capability.handler(request)
        except Exception:
            outcomes.append({**base, **_empty_outcome("failed", "handler_failed", None)})
            continue
        try:
            outcome, record_bytes = _validated_capability_outcome(
                request=request,
                result=capability_result,
                budget=budget,
                remaining_bytes=cumulative_cap - accepted_bytes,
            )
        except MissionStateError:
            outcomes.append({**base, **_empty_outcome("failed", "invalid_capability_result", None)})
            continue
        if outcome["outcome_status"] != "available":
            outcomes.append({**base, **outcome})
            if outcome["code"] == "byte_budget_exceeded":
                exhausted_bytes = True
            continue

        assert record_bytes is not None
        record_path = records_root / f"{paper_id}.json"
        if paper_id in seen_papers:
            prior_path, prior_bytes = seen_papers[paper_id]
            if prior_bytes != record_bytes:
                outcomes.append({**base, **_empty_outcome("failed", "invalid_capability_result", None)})
                continue
            outcomes.append(
                {
                    **base,
                    "outcome_status": "duplicate",
                    "code": "duplicate_identical",
                    "cap_kind": None,
                    "provider": capability_result.provider,
                    "final_url": capability_result.final_url,
                    "source_record_path": str(prior_path),
                    "source_record_sha256": sha256_bytes(prior_bytes),
                    "source_record_size_bytes": len(prior_bytes),
                }
            )
            continue
        _write_or_reuse_record(record_path, record_bytes, mission=mission, crash_hook=crash_hook)
        seen_papers[paper_id] = (record_path, record_bytes)
        accepted_bytes += len(record_bytes)
        row = {
            **base,
            **outcome,
            "source_record_path": str(record_path),
            "source_record_sha256": sha256_bytes(record_bytes),
            "source_record_size_bytes": len(record_bytes),
        }
        outcomes.append(row)
        source_support.append(
            {
                "paper_id": paper_id,
                "candidate_id": candidate["candidate_id"],
                "identifier": candidate["identifier"],
                "provider": capability_result.provider,
                "final_url": capability_result.final_url,
                "source_record_path": str(record_path),
                "source_record_sha256": sha256_bytes(record_bytes),
                "source_record_size_bytes": len(record_bytes),
                "source_status": "available",
                "technical_claim_support": False,
            }
        )

    if records_root.exists():
        materialized_names = {path.name for path, _ in seen_papers.values()}
        existing_names = {path.name for path in records_root.iterdir()}
        if existing_names != materialized_names:
            raise MissionStateError(
                "conflicting_source_record_orphan",
                "orphan source records differ from the current deterministic outcomes",
            )

    counts = {
        status: sum(row["outcome_status"] == status for row in outcomes)
        for status in sorted(OUTCOME_STATUSES)
    }
    shared = _shared_status_fields(
        snapshot=snapshot,
        binding=binding,
        authority=authority,
        budget=budget,
        candidates=candidates,
    )
    privacy_policy = "normalized structured fixture records only; no raw provider payload is persisted"
    claim_policy = "source availability is not technical claim support"
    next_actions = [
        "validate available records and extract anchors",
        "review source safety before technical claims",
    ]
    ledger_payload = {
        "schema_version": SOURCE_INTAKE_OUTCOMES_SCHEMA,
        "status": "completed_with_outcomes",
        **shared,
        "outcomes": outcomes,
        "counts": counts,
        "accepted_record_bytes": accepted_bytes,
        "privacy_policy": privacy_policy,
        "claim_support_policy": claim_policy,
        "next_required_actions": next_actions,
        "what_is_not_concluded": _nonclaims(),
    }
    ledger_bytes = pretty_json_bytes(ledger_payload)
    intake_root.mkdir(parents=True, exist_ok=True)
    _atomic_write(ledger_path, ledger_bytes, label="source_intake_outcomes", crash_hook=crash_hook)
    status_payload = {
        "schema_version": SOURCE_INTAKE_STATUS_SCHEMA,
        "status": "completed_with_outcomes",
        "created_at": now(),
        **shared,
        "outcome_ledger_path": str(ledger_path),
        "outcome_ledger_sha256": sha256_bytes(ledger_bytes),
        "outcome_ledger_size_bytes": len(ledger_bytes),
        "source_support": source_support,
        "authoritative_paper_ids": [row["paper_id"] for row in source_support],
        "counts": counts,
        "accepted_record_bytes": accepted_bytes,
        "completion_classification": (
            "available_records_with_visible_blockers"
            if source_support and any(row["outcome_status"] != "available" for row in outcomes)
            else "available_records"
            if source_support
            else "no_available_records"
        ),
        "ready_for_claim_support": False,
        "privacy_policy": privacy_policy,
        "claim_support_policy": claim_policy,
        "next_required_actions": next_actions,
        "what_is_not_concluded": _nonclaims(),
    }
    _atomic_write(
        status_path,
        pretty_json_bytes(status_payload),
        label="source_intake_status",
        crash_hook=crash_hook,
    )
    validated = validate_mission_source_intake(
        mission_root=mission,
        snapshot=snapshot,
        status_path=status_path,
    )
    return {
        "schema_version": SOURCE_INTAKE_STAGE_RESULT_SCHEMA,
        "status": "completed_with_outcomes",
        "required_output_paths": validated["required_output_paths"],
        "source_support_count": len(validated["paper_ids"]),
        "outcome_count": len(validated["outcomes"]),
    }


def _shared_status_fields(
    *,
    snapshot: MissionSnapshot,
    binding: dict[str, Any],
    authority: dict[str, Any],
    budget: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "mission_id": snapshot.contract["mission_id"],
        "mission_fingerprint": snapshot.contract["mission_fingerprint"],
        "creation_generation_id": binding["anchor_generation_id"],
        "mission_contract_sha256": binding["mission_contract_sha256"],
        "mission_control_sha256": binding["mission_control_sha256"],
        "next_action_sha256": binding["next_action_sha256"],
        "metadata_authority_sha256": binding["metadata_authority_sha256"],
        "normalized_topic": snapshot.contract["normalized_topic"],
        "normalized_seed_keys": [row["key"] for row in snapshot.contract["normalized_seeds"]],
        "public_discovery_confirmation": snapshot.contract["public_discovery_confirmation"],
        "discovery_budget": budget,
        "metadata_authority": authority,
        "candidates": candidates,
    }


def validate_mission_source_intake(
    *,
    mission_root: Path,
    snapshot: MissionSnapshot,
    status_path: Path | None = None,
) -> dict[str, Any]:
    mission = mission_root.absolute()
    intake_root = mission / "source_intake"
    records_root = mission / "local_research" / "papers" / "source" / "records"
    status_file = status_path.absolute() if status_path is not None else intake_root / STATUS_FILE
    if status_file != intake_root / STATUS_FILE:
        raise MissionStateError(
            "noncanonical_source_intake_status",
            "V2 status must be the canonical mission-local status",
        )
    _preflight_output_root(
        mission,
        intake_root,
        exact_allowed={OUTCOMES_FILE, STATUS_FILE},
        allowed_subset=None,
        label="source intake",
    )
    status, status_raw = _read_phase6_json(status_file, label="source intake status")
    _require_exact_keys(status, _status_keys(), "source intake status")
    if (
        status["schema_version"] != SOURCE_INTAKE_STATUS_SCHEMA
        or status["status"] != "completed_with_outcomes"
        or status["ready_for_claim_support"] is not False
    ):
        raise MissionStateError("invalid_source_intake_status", "V2 status or claim boundary is invalid")
    try:
        created_at = datetime.fromisoformat(status["created_at"])
    except (TypeError, ValueError) as exc:
        raise MissionStateError("invalid_source_intake_status", "V2 status timestamp is invalid") from exc
    if created_at.tzinfo is None:
        raise MissionStateError("invalid_source_intake_status", "V2 status timestamp lacks a timezone")
    if (
        status["mission_id"] != snapshot.contract["mission_id"]
        or status["mission_fingerprint"] != snapshot.contract["mission_fingerprint"]
    ):
        raise MissionStateError("foreign_source_intake", "source intake belongs to another mission")
    _validate_status_authority_types(status)
    binding = validate_generation_binding_readonly(
        output_dir=mission,
        mission_id=status["mission_id"],
        mission_fingerprint=status["mission_fingerprint"],
        generation_id=status["creation_generation_id"],
    )
    authority = binding["metadata_authority"]
    if not isinstance(authority, dict):
        raise MissionStateError(
            "invalid_metadata_authority",
            "creation generation lacks exact metadata authority",
        )
    _validate_metadata_authority_types(authority)
    if (
        status["metadata_authority"] != authority
        or status["metadata_authority_sha256"] != binding["metadata_authority_sha256"]
    ):
        raise MissionStateError(
            "metadata_authority_binding_mismatch",
            "status metadata authority differs from creation generation",
        )
    _validate_shared_bindings(status, snapshot=snapshot, binding=binding)
    current_authority = build_source_intake_metadata_authority(
        mission_root=mission,
        metadata_root=Path(authority["metadata_root"]),
        snapshot=snapshot,
    )
    if current_authority != authority:
        raise MissionStateError("stale_source_metadata", "current metadata bytes differ from creation authority")

    ledger_path = Path(status["outcome_ledger_path"])
    if ledger_path != intake_root / OUTCOMES_FILE:
        raise MissionStateError("invalid_source_outcome_path", "outcome ledger path is not canonical")
    ledger, ledger_raw = _read_phase6_json(ledger_path, label="source intake outcomes")
    if (
        sha256_bytes(ledger_raw) != status["outcome_ledger_sha256"]
        or len(ledger_raw) != status["outcome_ledger_size_bytes"]
    ):
        raise MissionStateError("source_outcome_digest_mismatch", "outcome ledger digest or size differs")
    _require_exact_keys(ledger, _ledger_keys(), "source intake outcomes")
    if (
        ledger["schema_version"] != SOURCE_INTAKE_OUTCOMES_SCHEMA
        or ledger["status"] != "completed_with_outcomes"
    ):
        raise MissionStateError("invalid_source_outcome_schema", "outcome ledger schema/status is invalid")
    _validate_ledger_authority_types(ledger)
    for key in _shared_keys():
        if ledger[key] != status[key]:
            raise MissionStateError("source_outcome_binding_mismatch", f"outcome ledger differs on {key}")
    candidates = ledger["candidates"]
    outcomes = ledger["outcomes"]
    if (
        not isinstance(candidates, list)
        or not isinstance(outcomes, list)
        or len(candidates) != len(outcomes)
    ):
        raise MissionStateError(
            "invalid_source_outcomes",
            "candidate and outcome lists must have equal length",
        )
    if sha256_bytes(canonical_json_bytes(candidates)) != authority["candidate_set_sha256"]:
        raise MissionStateError("source_candidate_set_mismatch", "candidate set differs from metadata authority")
    if len(candidates) != authority["candidate_count"]:
        raise MissionStateError("source_candidate_count_mismatch", "candidate count differs from metadata authority")
    _validate_outcomes(
        candidates,
        outcomes,
        budget=validate_budget(status["discovery_budget"]),
    )
    expected_counts = {
        name: sum(row["outcome_status"] == name for row in outcomes)
        for name in sorted(OUTCOME_STATUSES)
    }
    if ledger["counts"] != expected_counts or status["counts"] != expected_counts:
        raise MissionStateError("source_outcome_count_mismatch", "derived outcome counts differ")
    privacy_policy = "normalized structured fixture records only; no raw provider payload is persisted"
    claim_policy = "source availability is not technical claim support"
    next_actions = [
        "validate available records and extract anchors",
        "review source safety before technical claims",
    ]
    for payload in (ledger, status):
        if (
            payload["privacy_policy"] != privacy_policy
            or payload["claim_support_policy"] != claim_policy
            or payload["next_required_actions"] != next_actions
            or payload["what_is_not_concluded"] != _nonclaims()
        ):
            raise MissionStateError(
                "source_intake_policy_mismatch",
                "source intake policy or nonclaim fields differ",
            )

    support = status["source_support"]
    if not isinstance(support, list):
        raise MissionStateError("invalid_source_support", "source_support must be a list")
    available = [row for row in outcomes if row["outcome_status"] == "available"]
    if [row["paper_id"] for row in available] != status["authoritative_paper_ids"]:
        raise MissionStateError(
            "source_support_set_mismatch",
            "authoritative paper IDs differ from available outcomes",
        )
    if len(support) != len(available):
        raise MissionStateError(
            "source_support_set_mismatch",
            "source_support must contain available outcomes only",
        )
    expected_completion = (
        "available_records_with_visible_blockers"
        if available and any(row["outcome_status"] != "available" for row in outcomes)
        else "available_records"
        if available
        else "no_available_records"
    )
    if status["completion_classification"] != expected_completion:
        raise MissionStateError(
            "source_intake_completion_mismatch",
            "completion classification differs from outcome semantics",
        )
    record_paths: list[Path] = []
    accepted_bytes = 0
    for index, (support_value, outcome) in enumerate(zip(support, available, strict=True)):
        support_row = _require_exact_keys(
            support_value,
            SOURCE_SUPPORT_KEYS,
            f"source_support[{index}]",
        )
        expected_support = {
            "paper_id": outcome["paper_id"],
            "candidate_id": outcome["candidate_id"],
            "identifier": outcome["identifier"],
            "provider": outcome["provider"],
            "final_url": outcome["final_url"],
            "source_record_path": outcome["source_record_path"],
            "source_record_sha256": outcome["source_record_sha256"],
            "source_record_size_bytes": outcome["source_record_size_bytes"],
            "source_status": "available",
            "technical_claim_support": False,
        }
        if support_row != expected_support:
            raise MissionStateError(
                "source_support_semantic_mismatch",
                "source_support row differs from available outcome",
            )
        path = Path(outcome["source_record_path"])
        expected_path = records_root / f"{outcome['paper_id']}.json"
        if path != expected_path:
            raise MissionStateError(
                "invalid_source_record_path",
                "source record path is not derived mission-local path",
            )
        record_path = _regular_file(path, root=mission, label="source record")
        record, raw = _read_phase6_json(record_path, label="source record")
        _validate_structured_record(record, paper_id=outcome["paper_id"])
        provenance = record["provenance"]
        if (
            provenance.get("identifier") != outcome["identifier"]
            or provenance.get("provider") != outcome["provider"]
            or provenance.get("final_url") != outcome["final_url"]
            or provenance.get("fixture_only") is not True
        ):
            raise MissionStateError(
                "source_record_provenance_mismatch",
                "record provenance differs from the authoritative outcome",
            )
        if (
            sha256_bytes(raw) != outcome["source_record_sha256"]
            or len(raw) != outcome["source_record_size_bytes"]
        ):
            raise MissionStateError("source_record_digest_mismatch", "source record bytes differ from status")
        accepted_bytes += len(raw)
        record_paths.append(record_path)
    if (
        accepted_bytes != status["accepted_record_bytes"]
        or accepted_bytes != ledger["accepted_record_bytes"]
    ):
        raise MissionStateError("source_record_byte_count_mismatch", "accepted record bytes differ")
    if records_root.exists() or records_root.is_symlink():
        _preflight_output_root(
            mission,
            records_root,
            exact_allowed={path.name for path in record_paths},
            allowed_subset=None,
            label="source records",
        )
    required_paths = [*(str(path) for path in record_paths), str(ledger_path), str(status_file)]
    return {
        "paper_ids": status["authoritative_paper_ids"],
        "project_root": mission,
        "records_root": records_root,
        "records": record_paths,
        "status": status,
        "status_bytes": status_raw,
        "outcomes": outcomes,
        "required_output_paths": required_paths,
    }


def _validate_shared_bindings(
    status: dict[str, Any],
    *,
    snapshot: MissionSnapshot,
    binding: dict[str, Any],
) -> None:
    expected = {
        "mission_contract_sha256": binding["mission_contract_sha256"],
        "mission_control_sha256": binding["mission_control_sha256"],
        "next_action_sha256": binding["next_action_sha256"],
        "normalized_topic": snapshot.contract["normalized_topic"],
        "normalized_seed_keys": [row["key"] for row in snapshot.contract["normalized_seeds"]],
        "public_discovery_confirmation": snapshot.contract["public_discovery_confirmation"],
        "discovery_budget": validate_budget(snapshot.contract["discovery_budget"]),
    }
    for key, value in expected.items():
        if status[key] != value:
            raise MissionStateError(
                "source_intake_mission_binding_mismatch",
                f"source intake differs on {key}",
            )


def _validate_status_authority_types(status: dict[str, Any]) -> None:
    string_fields = (
        "mission_id",
        "mission_fingerprint",
        "creation_generation_id",
        "mission_contract_sha256",
        "mission_control_sha256",
        "next_action_sha256",
        "metadata_authority_sha256",
        "outcome_ledger_path",
        "outcome_ledger_sha256",
        "completion_classification",
        "privacy_policy",
        "claim_support_policy",
    )
    for key in string_fields:
        value = status[key]
        if not isinstance(value, str) or not value or "\x00" in value:
            raise MissionStateError("invalid_source_intake_status", f"V2 status {key} is invalid")
    for key in ("outcome_ledger_size_bytes", "accepted_record_bytes"):
        value = status[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MissionStateError("invalid_source_intake_status", f"V2 status {key} is invalid")
    if HEX64_RE.fullmatch(status["outcome_ledger_sha256"]) is None:
        raise MissionStateError("invalid_source_intake_status", "V2 outcome ledger digest is invalid")
    for key in (
        "mission_contract_sha256",
        "mission_control_sha256",
        "next_action_sha256",
        "metadata_authority_sha256",
    ):
        if HEX64_RE.fullmatch(status[key]) is None:
            raise MissionStateError("invalid_source_intake_status", f"V2 status {key} digest is invalid")
    if not isinstance(status["source_support"], list) or not isinstance(status["authoritative_paper_ids"], list):
        raise MissionStateError("invalid_source_intake_status", "V2 source authority lists are invalid")
    _validate_count_map(status["counts"], code="invalid_source_intake_status", label="V2 status counts")


def _validate_metadata_authority_types(authority: dict[str, Any]) -> None:
    if not isinstance(authority, dict):
        raise MissionStateError("invalid_metadata_authority", "metadata authority must be an object")
    schema = authority.get("schema_version")
    expected_keys = (
        AUTHORITY_KEYS
        if schema == METADATA_AUTHORITY_SCHEMA
        else V2_AUTHORITY_KEYS
        if schema == METADATA_AUTHORITY_V2_SCHEMA
        else None
    )
    if expected_keys is None or set(authority) != expected_keys:
        raise MissionStateError("invalid_metadata_authority", "metadata authority schema is invalid")
    string_fields = (
        "mission_id",
        "mission_fingerprint",
        "normalized_topic_key",
        "metadata_root",
        "candidate_ledger_path",
        "candidate_ledger_sha256",
        "build_manifest_path",
        "build_manifest_sha256",
        "candidate_set_sha256",
    )
    for key in string_fields:
        value = authority[key]
        if not isinstance(value, str) or not value or "\x00" in value:
            raise MissionStateError("invalid_metadata_authority", f"metadata authority {key} is invalid")
    for key in ("candidate_ledger_sha256", "build_manifest_sha256", "candidate_set_sha256"):
        if HEX64_RE.fullmatch(authority[key]) is None:
            raise MissionStateError("invalid_metadata_authority", f"metadata authority {key} is invalid")
    for key in ("candidate_ledger_size_bytes", "build_manifest_size_bytes", "candidate_count"):
        value = authority[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MissionStateError("invalid_metadata_authority", f"metadata authority {key} is invalid")
    _string_list(
        authority["normalized_seed_keys"],
        label="metadata authority normalized_seed_keys",
    )
    if schema == METADATA_AUTHORITY_V2_SCHEMA:
        rows = authority["artifact_rows"]
        if not isinstance(rows, list) or len(rows) != len(PUBLIC_METADATA_PACKET_FILES):
            raise MissionStateError("invalid_metadata_authority", "V2 artifact rows are incomplete")
        names = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != V2_AUTHORITY_ARTIFACT_KEYS:
                raise MissionStateError(
                    "invalid_metadata_authority",
                    f"V2 artifact row[{index}] keys are invalid",
                )
            name = row["name"]
            path = row["path"]
            digest = row["sha256"]
            size = row["size_bytes"]
            if (
                not isinstance(name, str)
                or name not in PUBLIC_METADATA_PACKET_FILES
                or not isinstance(path, str)
                or path != str(Path(authority["metadata_root"]) / name)
                or not isinstance(digest, str)
                or HEX64_RE.fullmatch(digest) is None
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 0
            ):
                raise MissionStateError("invalid_metadata_authority", f"V2 artifact row[{index}] is invalid")
            names.append(name)
        if names != sorted(PUBLIC_METADATA_PACKET_FILES):
            raise MissionStateError("invalid_metadata_authority", "V2 artifact rows are not exact and sorted")


def _validate_ledger_authority_types(ledger: dict[str, Any]) -> None:
    accepted = ledger["accepted_record_bytes"]
    if isinstance(accepted, bool) or not isinstance(accepted, int) or accepted < 0:
        raise MissionStateError("invalid_source_outcome_schema", "outcome ledger byte count is invalid")
    _validate_count_map(
        ledger["counts"],
        code="invalid_source_outcome_schema",
        label="outcome ledger counts",
    )


def _validate_count_map(value: Any, *, code: str, label: str) -> None:
    if not isinstance(value, dict) or set(value) != OUTCOME_STATUSES:
        raise MissionStateError(code, f"{label} keys are invalid")
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in value.values()):
        raise MissionStateError(code, f"{label} values are invalid")


def _validate_outcomes(
    candidates: list[Any],
    outcomes: list[Any],
    *,
    budget: dict[str, Any],
) -> None:
    available_by_paper: dict[str, dict[str, Any]] = {}
    cumulative_exhausted = False
    accepted_bytes = 0
    capability_calls = 0
    for index, (candidate_value, outcome_value) in enumerate(
        zip(candidates, outcomes, strict=True)
    ):
        candidate = _require_exact_keys(
            candidate_value,
            CANDIDATE_PROJECTION_KEYS,
            f"candidate[{index}]",
        )
        _string_list(candidate["roles"], label=f"candidate[{index}].roles")
        _string_list(candidate["providers"], label=f"candidate[{index}].providers")
        outcome = _require_exact_keys(outcome_value, OUTCOME_KEYS, f"outcome[{index}]")
        _validate_outcome_types(outcome, index=index)
        if (
            outcome["candidate_id"] != candidate["candidate_id"]
            or outcome["identifier"] != candidate["identifier"]
        ):
            raise MissionStateError(
                "source_outcome_identity_mismatch",
                f"outcome[{index}] differs from candidate",
            )
        if (
            outcome["candidate_index"] != index
            or outcome["paper_id"] != derive_source_paper_id(candidate["identifier"])
        ):
            raise MissionStateError(
                "source_outcome_identity_mismatch",
                f"outcome[{index}] index/paper ID differs",
            )
        if outcome["outcome_status"] not in OUTCOME_STATUSES or outcome["code"] not in OUTCOME_CODES:
            raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] status/code is invalid")
        allowed_pairs = {
            ("available", "available"),
            ("metadata_only", "metadata_only"),
            ("unavailable", "unavailable"),
            ("quarantined", "quarantined"),
            ("duplicate", "duplicate_identical"),
            ("failed", "handler_failed"),
            ("failed", "invalid_capability_result"),
            ("failed", "byte_budget_exceeded"),
            ("unsupported_identifier", "unsupported_identifier"),
            ("not_attempted_cap", "source_count_cap"),
            ("not_attempted_cap", "byte_budget_exceeded"),
        }
        if (outcome["outcome_status"], outcome["code"]) not in allowed_pairs:
            raise MissionStateError(
                "invalid_source_outcomes",
                f"outcome[{index}] status/code pair is invalid",
            )
        supported_identifier = _supports_source_identifier(candidate)
        if cumulative_exhausted:
            if not (
                outcome["outcome_status"] == "not_attempted_cap"
                and outcome["code"] == "byte_budget_exceeded"
                and outcome["cap_kind"] == "cumulative_bytes"
            ):
                raise MissionStateError(
                    "source_byte_cap_sequence_mismatch",
                    "all rows after byte exhaustion must remain unattempted",
                )
        elif capability_calls >= budget["max_source_records"]:
            if not (
                outcome["outcome_status"] == "not_attempted_cap"
                and outcome["code"] == "source_count_cap"
                and outcome["cap_kind"] == "source_count"
            ):
                raise MissionStateError(
                    "source_count_cap_sequence_mismatch",
                    "rows after the source-call cap must remain unattempted",
                )
        elif not supported_identifier:
            if not (
                outcome["outcome_status"] == "unsupported_identifier"
                and outcome["code"] == "unsupported_identifier"
                and outcome["cap_kind"] is None
            ):
                raise MissionStateError(
                    "source_identifier_outcome_mismatch",
                    "unsupported candidate must retain the exact no-call outcome",
                )
        elif outcome["outcome_status"] == "not_attempted_cap":
            raise MissionStateError(
                "source_cap_sequence_mismatch",
                "an unattempted row appears before any applicable cap",
            )
        else:
            if outcome["outcome_status"] == "unsupported_identifier":
                raise MissionStateError(
                    "source_identifier_outcome_mismatch",
                    "supported candidate cannot become an unsupported no-call outcome",
                )
            capability_calls += 1
        if outcome["provider"] is not None and (
            outcome["provider"] not in candidate["providers"]
            or outcome["provider"] not in budget["providers"]
        ):
            raise MissionStateError(
                "invalid_source_outcomes",
                f"outcome[{index}] provider is not authorized for the candidate",
            )
        provider_required = outcome["outcome_status"] in {"available", "duplicate"} or (
            outcome["outcome_status"] == "failed" and outcome["code"] == "byte_budget_exceeded"
        )
        provider_forbidden = outcome["outcome_status"] in {"not_attempted_cap", "unsupported_identifier"} or (
            outcome["outcome_status"] == "failed"
            and outcome["code"] in {"handler_failed", "invalid_capability_result"}
        )
        if provider_required and outcome["provider"] is None:
            raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] lacks required provider")
        if provider_forbidden and outcome["provider"] is not None:
            raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] carries forbidden provider")
        if outcome["outcome_status"] in {"available", "duplicate"}:
            _validate_public_url(outcome["final_url"], budget["allowed_domains"])
        elif outcome["final_url"] is not None:
            raise MissionStateError(
                "invalid_source_outcomes",
                f"outcome[{index}] nonavailable row carries a URL",
            )
        if outcome["outcome_status"] == "not_attempted_cap":
            expected_code = (
                "source_count_cap"
                if outcome["cap_kind"] == "source_count"
                else "byte_budget_exceeded"
                if outcome["cap_kind"] == "cumulative_bytes"
                else None
            )
            if outcome["code"] != expected_code:
                raise MissionStateError(
                    "invalid_source_outcomes",
                    f"outcome[{index}] cap kind/code differs",
                )
        elif outcome["cap_kind"] is not None:
            raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] has unexpected cap kind")
        authority_fields = (
            outcome["source_record_path"],
            outcome["source_record_sha256"],
            outcome["source_record_size_bytes"],
        )
        if outcome["outcome_status"] == "available":
            if any(value is None for value in authority_fields):
                raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] lacks record authority")
            if outcome["paper_id"] in available_by_paper:
                raise MissionStateError("duplicate_source_paper_id", "available paper IDs must be unique")
            size = outcome["source_record_size_bytes"]
            if (
                isinstance(size, bool)
                or not isinstance(size, int)
                or size <= 0
                or size > budget["max_bytes_per_source"]
            ):
                raise MissionStateError(
                    "source_record_byte_count_mismatch",
                    "available record size exceeds the per-record budget",
                )
            accepted_bytes += size
            if accepted_bytes > budget["max_source_records"] * budget["max_bytes_per_source"]:
                raise MissionStateError(
                    "source_record_byte_count_mismatch",
                    "available record sizes exceed the cumulative budget",
                )
            available_by_paper[outcome["paper_id"]] = outcome
        elif outcome["outcome_status"] == "duplicate":
            if any(value is None for value in authority_fields) or outcome["code"] != "duplicate_identical":
                raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] duplicate is invalid")
            prior = available_by_paper.get(outcome["paper_id"])
            if prior is None or any(
                outcome[key] != prior[key]
                for key in (
                    "identifier",
                    "provider",
                    "final_url",
                    "source_record_path",
                    "source_record_sha256",
                    "source_record_size_bytes",
                )
            ):
                raise MissionStateError(
                    "duplicate_source_record_mismatch",
                    "duplicate outcome does not bind an earlier identical available record",
                )
        elif any(value is not None for value in authority_fields):
            raise MissionStateError(
                "nonavailable_source_authority",
                f"outcome[{index}] carries record authority",
            )
        if outcome["outcome_status"] == "failed" and outcome["code"] == "byte_budget_exceeded":
            cumulative_exhausted = True


def _validate_outcome_types(outcome: dict[str, Any], *, index: int) -> None:
    for key in ("candidate_id", "identifier", "paper_id", "outcome_status", "code"):
        if not isinstance(outcome[key], str) or not outcome[key] or "\x00" in outcome[key]:
            raise MissionStateError("invalid_source_outcomes", f"outcome[{index}].{key} is invalid")
    if isinstance(outcome["candidate_index"], bool) or not isinstance(outcome["candidate_index"], int):
        raise MissionStateError("invalid_source_outcomes", f"outcome[{index}].candidate_index is invalid")
    for key in ("cap_kind", "provider", "final_url", "source_record_path", "source_record_sha256"):
        value = outcome[key]
        if value is not None and (not isinstance(value, str) or not value or "\x00" in value):
            raise MissionStateError("invalid_source_outcomes", f"outcome[{index}].{key} is invalid")
    digest = outcome["source_record_sha256"]
    if digest is not None and HEX64_RE.fullmatch(digest) is None:
        raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] record digest is invalid")
    size = outcome["source_record_size_bytes"]
    if size is not None and (isinstance(size, bool) or not isinstance(size, int) or size <= 0):
        raise MissionStateError("invalid_source_outcomes", f"outcome[{index}] record size is invalid")


def _read_builder_json(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_source_metadata", f"{label} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_source_metadata", f"{label} must be an object")
    expected = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    if raw not in {expected, expected + b"\n"}:
        raise MissionStateError(
            "noncanonical_source_metadata",
            f"{label} bytes are not canonical builder JSON",
        )
    return payload, raw


def _read_phase6_json(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    file_path = _regular_file(path, root=path.parent, label=label)
    raw = file_path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_source_intake", f"{label} is not valid JSON") from exc
    if not isinstance(payload, dict) or raw != pretty_json_bytes(payload):
        raise MissionStateError(
            "noncanonical_source_intake",
            f"{label} is not canonical pretty JSON",
        )
    return payload, raw


def _assert_safe_directory(path: Path, *, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("unsafe_source_intake_path", f"{label} directory is missing") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode) or path.resolve() != path:
        raise MissionStateError("unsafe_source_intake_path", f"{label} directory is unsafe")


def _regular_file(path: Path, *, root: Path, label: str) -> Path:
    lexical = path.absolute()
    try:
        resolved = lexical.resolve(strict=True)
        mode = lexical.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("unsafe_source_intake_path", f"{label} is missing") from exc
    if resolved != lexical or stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise MissionStateError("unsafe_source_intake_path", f"{label} is unsafe")
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise MissionStateError("source_intake_path_escape", f"{label} escapes its root") from exc
    _assert_no_symlink_chain(root, resolved)
    return resolved


def _assert_no_symlink_chain(root: Path, target: Path) -> None:
    root_abs = root.absolute()
    target_abs = target.absolute()
    try:
        relative = target_abs.relative_to(root_abs)
    except ValueError as exc:
        raise MissionStateError(
            "source_intake_path_escape",
            "source-intake path escapes mission root",
        ) from exc
    cursor = root_abs
    if cursor.exists() and stat.S_ISLNK(cursor.lstat().st_mode):
        raise MissionStateError("unsafe_source_intake_path", "source-intake root is a symlink")
    for part in relative.parts:
        cursor = cursor / part
        if not cursor.exists() and not cursor.is_symlink():
            continue
        mode = cursor.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise MissionStateError("unsafe_source_intake_path", "source-intake path contains a symlink")
        if cursor != target_abs and not stat.S_ISDIR(mode):
            raise MissionStateError(
                "unsafe_source_intake_path",
                "source-intake ancestor is not a directory",
            )


def _preflight_output_root(
    mission: Path,
    root: Path,
    *,
    exact_allowed: set[str] | None,
    allowed_subset: set[str] | None,
    label: str,
) -> None:
    _assert_no_symlink_chain(mission, root)
    if not root.exists() and not root.is_symlink():
        return
    _assert_safe_directory(root, label=label)
    children: set[str] = set()
    for child in root.iterdir():
        mode = child.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise MissionStateError("unsafe_source_intake_path", f"{label} contains an unsafe child")
        children.add(child.name)
    if exact_allowed is not None and children and children != exact_allowed:
        raise MissionStateError("unexpected_source_intake_child", f"{label} child set is not exact")
    if allowed_subset is not None and not children.issubset(allowed_subset):
        raise MissionStateError("unexpected_source_intake_child", f"{label} contains an unexpected child")


def _write_or_reuse_record(
    path: Path,
    value: bytes,
    *,
    mission: Path,
    crash_hook: Callable[[str], None] | None,
) -> None:
    _assert_no_symlink_chain(mission, path)
    if path.exists() or path.is_symlink():
        existing = _regular_file(path, root=mission, label="orphan source record").read_bytes()
        if existing != value:
            raise MissionStateError(
                "conflicting_source_record_orphan",
                "existing orphan source record bytes differ",
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, value, label="source_record", crash_hook=crash_hook)


def _atomic_write(
    path: Path,
    value: bytes,
    *,
    label: str,
    crash_hook: Callable[[str], None] | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        if crash_hook:
            crash_hook(f"{label}:after_temp_fsync")
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if crash_hook:
            crash_hook(f"{label}:after_directory_fsync")
    finally:
        if temp.exists():
            temp.unlink()


__all__ = [
    "MissionSourceCapability",
    "SOURCE_INTAKE_CAPABILITY_SCHEMA",
    "SOURCE_INTAKE_OUTCOMES_SCHEMA",
    "SOURCE_INTAKE_STATUS_SCHEMA",
    "SourceCandidateRequest",
    "SourceCapabilityResult",
    "build_source_intake_metadata_authority",
    "derive_source_paper_id",
    "run_mission_source_intake",
    "validate_mission_source_intake",
]
