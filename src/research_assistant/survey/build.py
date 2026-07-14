from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from research_assistant.benchmarks.replay import load_json
from research_assistant.benchmarks.surveybench_helpers import surveybench_visible_replay_packet
from research_assistant.survey.discovery_quality import (
    IDENTITY_RESOLUTION_SCHEMA_VERSION,
    PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION,
    RELEVANCE_RANKING_SCHEMA_VERSION,
    evaluate_discovery_quality,
    normalize_record,
    parse_seed,
)
from research_assistant.survey.mission_state import (
    MissionSnapshot,
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    normalize_seeds,
    pretty_json_bytes,
)


SURVEY_BUILD_RESULT_SCHEMA_VERSION = "ra-survey-build-cli-result-v1"
SURVEY_BUILD_MANIFEST_SCHEMA_VERSION = "ra-survey-build-manifest-v1"
SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION = "ra-survey-candidate-ledger-v1"
SURVEY_CITATION_MAP_SCHEMA_VERSION = "ra-survey-citation-map-v1"
SURVEY_SOURCE_SUPPORT_SCHEMA_VERSION = "ra-survey-source-support-v1"
SURVEY_CLASSIFICATION_SCHEMA_VERSION = "ra-survey-paper-classifications-v1"
SURVEY_CLAIM_SUPPORT_SCHEMA_VERSION = "ra-survey-claim-support-v1"
SURVEY_OMISSION_RISK_SCHEMA_VERSION = "ra-survey-omission-risk-v1"
SURVEY_METADATA_PROVENANCE_SCHEMA_VERSION = "ra-survey-metadata-provenance-v1"
SURVEY_WORKFLOW_STATE_SCHEMA_VERSION = "ra-survey-workflow-state-v1"
PUBLIC_METADATA_BUILD_MANIFEST_SCHEMA_VERSION = "ra-survey-public-metadata-build-manifest-v2"
BOOTSTRAP_EFFECTIVE_SEED_CONTEXT_SCHEMA_VERSION = "ra-survey-bootstrap-effective-seed-context-v1"
BOOTSTRAP_EFFECTIVE_SEED_SKELETON_RESULT_SCHEMA_VERSION = "ra-survey-bootstrap-effective-seed-skeleton-result-v1"
PUBLIC_METADATA_ALLOWED_PROVIDERS = {"openalex", "arxiv"}
PUBLIC_METADATA_DEFAULT_PROVIDERS = ["openalex", "arxiv"]
PUBLIC_METADATA_MAX_RECORDS = 25
PUBLIC_METADATA_TIMEOUT_SECONDS = 30
SURVEY_CLASSIFICATION_ALLOWED_LABELS = [
    "seed",
    "foundational",
    "direct_method",
    "major_citing_work",
    "adjacent_method",
    "survey_or_tutorial",
    "competitor",
    "implementation_or_software",
    "empirical_example",
    "background",
    "peripheral",
    "duplicate",
    "false_positive",
    "superseded",
    "source_blocked",
    "retracted_or_quarantined",
]
SURVEY_BUILD_BLOCKED_NONCLAIMS = [
    "survey packet creation did not complete",
    "citation map readiness",
    "claim support correctness",
    "survey prose readiness",
    "live web coverage",
    "scientific correctness",
]

PACKET_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
    "workflow_state.json",
    "survey_packet.md",
    "build_manifest.json",
)
PUBLIC_METADATA_PACKET_FILES = (
    "candidate_ledger.json",
    "identity_resolution.json",
    "relevance_ranking.json",
    "citation_map.json",
    "source_support.json",
    "paper_classifications.json",
    "claim_support.json",
    "omission_risk.json",
    "workflow_state.json",
    "survey_packet.md",
    "metadata_provenance.json",
    "build_manifest.json",
)
ARXIV_ID_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-zA-Z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$")
ARXIV_QUERY_ENDPOINT = "https://export.arxiv.org/api/query"
OPENALEX_WORKS_ENDPOINT = "https://api.openalex.org/works"


def build_survey_evidence_packet(
    *,
    topic: str,
    seeds: list[str],
    output_dir: Path,
    mode: str = "offline-skeleton",
    force: bool = False,
    replay_task: Path | None = None,
    replay_responses_dir: Path | None = None,
    public_metadata_providers: list[str] | None = None,
    max_records: int = PUBLIC_METADATA_MAX_RECORDS,
) -> dict[str, Any]:
    """Create the first product-shaped packet for topic+seed survey automation.

    The initial mode intentionally writes a skeleton rather than pretending to
    have completed discovery, source intake, citation mapping, or claim audit.
    """

    topic = topic.strip()
    seeds = [seed.strip() for seed in seeds if seed.strip()]
    if not topic:
        return _blocked(
            "empty_topic",
            "survey build requires a non-empty topic",
            output_dir,
            next_required_actions=["provide a non-empty --topic value and rerun survey build"],
        )
    if not seeds:
        return _blocked(
            "empty_seed",
            "survey build requires at least one seed paper",
            output_dir,
            next_required_actions=["provide at least one --seed value and rerun survey build"],
        )
    if mode not in {"offline-skeleton", "offline-replay", "public-metadata"}:
        return _blocked(
            "unsupported_mode",
            f"unsupported survey build mode: {mode}",
            output_dir,
            next_required_actions=[
                "use --mode offline-skeleton, --mode offline-replay, or --mode public-metadata within approved live-source bounds"
            ],
        )

    if mode == "public-metadata":
        from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed

        lexical_output = output_dir.absolute()
        try:
            assert_public_write_path_allowed(lexical_output)
        except MissionStateError as exc:
            return _blocked(
                exc.code,
                str(exc),
                lexical_output,
                next_required_actions=["choose a regular non-symlinked metadata output root"],
            )
        output_dir = lexical_output
    else:
        output_dir = output_dir.resolve()
    expected_packet_files = PUBLIC_METADATA_PACKET_FILES if mode == "public-metadata" else PACKET_FILES
    existing = [output_dir / name for name in expected_packet_files if (output_dir / name).exists()]
    if existing and mode != "public-metadata" and not force:
        return {
            "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
            "status": "blocked",
            "blocked_reason": "output_exists",
            "message": "output directory already contains survey-build artifacts",
            "output_dir": str(output_dir),
            "existing_artifacts": [str(path) for path in existing],
            "next_required_actions": ["rerun with --force or choose a new --out directory"],
            "what_is_not_concluded": SURVEY_BUILD_BLOCKED_NONCLAIMS,
        }

    if mode == "offline-replay":
        return _build_from_visible_replay(
            topic=topic,
            seeds=seeds,
            output_dir=output_dir,
            replay_task=replay_task,
            replay_responses_dir=replay_responses_dir,
        )
    if mode == "public-metadata":
        return _build_public_metadata_packet(
            topic=topic,
            seeds=seeds,
            output_dir=output_dir,
            providers=public_metadata_providers,
            max_records=max_records,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    seed_rows = [_seed_row(index, seed) for index, seed in enumerate(seeds, start=1)]
    artifacts: dict[str, Any] = {
        "candidate_ledger.json": _candidate_ledger(topic, seed_rows),
        "citation_map.json": _citation_map(topic, seed_rows),
        "source_support.json": _source_support(topic, seed_rows),
        "paper_classifications.json": _paper_classifications(topic, seed_rows),
        "claim_support.json": _claim_support(topic, seed_rows),
        "omission_risk.json": _omission_risk(topic, seed_rows),
    }
    for name, payload in artifacts.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))

    survey_packet = _survey_packet_markdown(topic, seed_rows)
    (output_dir / "survey_packet.md").write_text(survey_packet)

    manifest = _manifest(topic, seed_rows, output_dir, mode)
    _write_workflow_state(output_dir, manifest)
    (output_dir / "build_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    return {
        "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
        "status": "created_skeleton",
        "mode": mode,
        "topic": topic,
        "seed_count": len(seed_rows),
        "output_dir": str(output_dir),
        "artifact_paths": manifest["artifact_paths"],
        "workflow_state": manifest["workflow_state"],
        "workflow_state_path": manifest["artifact_paths"]["workflow_state.json"],
        "next_required_actions": manifest["next_required_actions"],
        "what_is_not_concluded": manifest["what_is_not_concluded"],
    }


def build_bootstrap_effective_seed_skeleton(
    *,
    manager: MissionStateManager,
    snapshot: MissionSnapshot,
    output_dir: Path,
    bootstrap_authority: dict[str, Any],
) -> dict[str, Any]:
    """Write a local skeleton only after replaying selected bootstrap authority."""
    from research_assistant.survey.bootstrap import MissionBootstrapStore

    selected = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: snapshot.contract["updated_at"],
    ).validate_selected(bootstrap_authority)
    seeds = selected["effective_seeds"]
    if not seeds:
        raise MissionStateError("bootstrap_selection_required", "selected bootstrap authority has no effective seeds")
    output_dir = output_dir.resolve()
    expected_output = (manager.output_dir / "offline_skeleton").resolve()
    if output_dir != expected_output:
        raise MissionStateError(
            "noncanonical_bootstrap_skeleton_root",
            "bootstrap effective-seed skeleton must use the exact mission-local offline_skeleton root",
        )
    context_path = output_dir / "bootstrap_effective_seed_context.json"
    if context_path.exists() or context_path.is_symlink():
        existing = _read_canonical_public_metadata_json(context_path)
        _validate_bootstrap_effective_seed_context(
            existing,
            snapshot=snapshot,
            bootstrap_authority=bootstrap_authority,
            effective_seeds=seeds,
            output_dir=output_dir,
        )
        _replay_bootstrap_effective_seed_skeleton(output_dir, existing)
        return {
            "schema_version": BOOTSTRAP_EFFECTIVE_SEED_SKELETON_RESULT_SCHEMA_VERSION,
            "status": "reused_bootstrap_effective_seed_skeleton",
            "mode": "offline-skeleton",
            "topic": snapshot.contract["normalized_topic"]["display"],
            "seed_count": len(seeds),
            "output_dir": str(output_dir),
            "bootstrap_effective_seed_context_path": str(context_path),
            "bootstrap_authority": bootstrap_authority,
            "what_is_not_concluded": SURVEY_BUILD_BLOCKED_NONCLAIMS,
        }
    if output_dir.exists() and any(output_dir.iterdir()):
        raise MissionStateError("bootstrap_skeleton_output_not_empty", "bootstrap skeleton output contains unbound residue")
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = selected["selected_candidates"]
    candidate_by_display = {row["display"]: row for row in candidates}
    seed_rows = [
        {
            "paper_key": candidate_by_display[seed]["paper_key"],
            "identifier": seed,
            "roles": ["seed"],
            "source": "selected_bootstrap_authority",
            "bootstrap_set_id": bootstrap_authority["set_id"],
            "bootstrap_manifest_sha256": bootstrap_authority["manifest_sha256"],
            "bootstrap_request_sha256": bootstrap_authority["request_sha256"],
        }
        for seed in seeds
    ]
    topic_display = snapshot.contract["normalized_topic"]["display"]
    artifacts: dict[str, Any] = {
        "candidate_ledger.json": _candidate_ledger(topic_display, seed_rows),
        "citation_map.json": _citation_map(topic_display, seed_rows),
        "source_support.json": _source_support(topic_display, seed_rows),
        "paper_classifications.json": _paper_classifications(topic_display, seed_rows),
        "claim_support.json": _claim_support(topic_display, seed_rows),
        "omission_risk.json": _omission_risk(topic_display, seed_rows),
    }
    bootstrap_schemas = {
        "candidate_ledger.json": "ra-survey-bootstrap-effective-candidate-ledger-v1",
        "citation_map.json": "ra-survey-bootstrap-effective-citation-map-v1",
        "source_support.json": "ra-survey-bootstrap-effective-source-support-v1",
        "paper_classifications.json": "ra-survey-bootstrap-effective-paper-classifications-v1",
        "claim_support.json": "ra-survey-bootstrap-effective-claim-support-v1",
        "omission_risk.json": "ra-survey-bootstrap-effective-omission-risk-v1",
    }
    for name, payload in artifacts.items():
        _rewrite_bootstrap_seed_semantics(payload, bootstrap_authority)
        payload["schema_version"] = bootstrap_schemas[name]
        payload["bootstrap_authority"] = bootstrap_authority
        payload["original_initial_seeds"] = []
        payload["effective_seed_source"] = "selected_bootstrap_authority_not_original_mission_input"
        (output_dir / name).write_bytes(pretty_json_bytes(payload))
    (output_dir / "survey_packet.md").write_text(
        _survey_packet_markdown(topic_display, seed_rows).replace(
            "Seed Papers", "Bootstrap-Selected Effective Seed Papers"
        ).replace(
            "Resolve seed metadata.", "Resolve bootstrap-selected effective-seed metadata."
        )
        + "\n## Bootstrap Authority\n\n"
        + f"- Set: `{bootstrap_authority['set_id']}`\n"
        + f"- Manifest SHA-256: `{bootstrap_authority['manifest_sha256']}`\n"
        + f"- Request SHA-256: `{bootstrap_authority['request_sha256']}`\n"
        + "- Original initial seeds: none.\n"
    )
    workflow = _workflow_state(
        state="bootstrap_effective_seed_skeleton_created",
        mode="offline-skeleton",
        ready_for_writer=False,
        ready_for_prose=False,
        safe_next_commands=["validate the selected bootstrap authority before any downstream metadata action"],
        approval_required_for=["network/provider metadata", "source/PDF/full-text", "technical claim support"],
        blocked_reasons=["live metadata and source evidence are absent"],
    )
    workflow["schema_version"] = "ra-survey-bootstrap-effective-workflow-state-v1"
    workflow["bootstrap_authority"] = bootstrap_authority
    workflow["original_initial_seeds"] = []
    workflow["effective_seed_source"] = "selected_bootstrap_authority_not_original_mission_input"
    (output_dir / "workflow_state.json").write_bytes(pretty_json_bytes(workflow))
    artifact_names = sorted([*artifacts, "survey_packet.md", "workflow_state.json"])
    artifact_rows = [
        {
            "name": name,
            "sha256": hashlib.sha256((output_dir / name).read_bytes()).hexdigest(),
            "size_bytes": (output_dir / name).stat().st_size,
        }
        for name in artifact_names
    ]
    manifest = {
        "schema_version": "ra-survey-bootstrap-effective-seed-skeleton-manifest-v1",
        "status": "bootstrap_effective_seed_skeleton_created",
        "topic": topic_display,
        "original_initial_seeds": [],
        "effective_seed_rows": normalize_seeds(seeds),
        "bootstrap_authority": bootstrap_authority,
        "artifact_rows": artifact_rows,
        "workflow_state": workflow,
        "technical_claim_support_created": False,
    }
    (output_dir / "build_manifest.json").write_bytes(pretty_json_bytes(manifest))
    artifact_rows.append({
        "name": "build_manifest.json",
        "sha256": hashlib.sha256((output_dir / "build_manifest.json").read_bytes()).hexdigest(),
        "size_bytes": (output_dir / "build_manifest.json").stat().st_size,
    })
    context = {
        "schema_version": BOOTSTRAP_EFFECTIVE_SEED_CONTEXT_SCHEMA_VERSION,
        "mission_id": snapshot.contract["mission_id"],
        "mission_fingerprint": snapshot.contract["mission_fingerprint"],
        "creation_generation_id": bootstrap_authority["confirmed_generation_id"],
        "bootstrap_authority": bootstrap_authority,
        "bootstrap_authority_sha256": hashlib.sha256(canonical_json_bytes(bootstrap_authority)).hexdigest(),
        "effective_seed_rows": normalize_seeds(seeds),
        "effective_seed_source": "selected_bootstrap_authority_not_original_mission_input",
        "original_initial_seeds": [],
        "output_dir": str(output_dir),
        "artifact_rows": sorted(artifact_rows, key=lambda row: row["name"]),
        "technical_claim_support_created": False,
    }
    _validate_bootstrap_effective_seed_context(
        context,
        snapshot=snapshot,
        bootstrap_authority=bootstrap_authority,
        effective_seeds=seeds,
        output_dir=output_dir,
    )
    _install_public_metadata_v2_child(context_path, pretty_json_bytes(context))
    return {
        "schema_version": BOOTSTRAP_EFFECTIVE_SEED_SKELETON_RESULT_SCHEMA_VERSION,
        "status": "created_bootstrap_effective_seed_skeleton",
        "mode": "offline-skeleton",
        "topic": topic_display,
        "seed_count": len(seeds),
        "output_dir": str(output_dir),
        "bootstrap_effective_seed_context_path": str(context_path),
        "bootstrap_authority": bootstrap_authority,
        "what_is_not_concluded": SURVEY_BUILD_BLOCKED_NONCLAIMS,
    }


def _validate_bootstrap_effective_seed_context(
    value: Any,
    *,
    snapshot: MissionSnapshot,
    bootstrap_authority: dict[str, Any],
    effective_seeds: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    expected = {
        "schema_version", "mission_id", "mission_fingerprint", "creation_generation_id",
        "bootstrap_authority", "bootstrap_authority_sha256", "effective_seed_rows",
        "effective_seed_source", "original_initial_seeds", "output_dir", "artifact_rows", "technical_claim_support_created",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise MissionStateError("invalid_bootstrap_effective_seed_context", "bootstrap effective-seed context fields differ")
    if value["schema_version"] != BOOTSTRAP_EFFECTIVE_SEED_CONTEXT_SCHEMA_VERSION:
        raise MissionStateError("invalid_bootstrap_effective_seed_context", "bootstrap effective-seed context schema differs")
    if value["mission_id"] != snapshot.contract["mission_id"] or value["mission_fingerprint"] != snapshot.contract["mission_fingerprint"]:
        raise MissionStateError("foreign_bootstrap_effective_seed_context", "bootstrap effective-seed context belongs to another mission")
    if value["creation_generation_id"] != bootstrap_authority["confirmed_generation_id"]:
        raise MissionStateError("stale_bootstrap_effective_seed_context", "bootstrap effective-seed context generation is stale")
    if value["bootstrap_authority"] != bootstrap_authority or value["bootstrap_authority_sha256"] != hashlib.sha256(canonical_json_bytes(bootstrap_authority)).hexdigest():
        raise MissionStateError("stale_bootstrap_authority", "bootstrap effective-seed context authority differs")
    if value["effective_seed_rows"] != normalize_seeds(effective_seeds):
        raise MissionStateError("invalid_bootstrap_effective_seed_context", "effective seed rows differ from selected authority")
    if value["effective_seed_source"] != "selected_bootstrap_authority_not_original_mission_input" or value["original_initial_seeds"] != [] or value["technical_claim_support_created"] is not False:
        raise MissionStateError("invalid_bootstrap_effective_seed_context", "bootstrap effective-seed context boundary fields differ")
    if value["output_dir"] != str(output_dir.resolve()):
        raise MissionStateError("stale_bootstrap_effective_seed_context", "bootstrap skeleton output root differs")
    rows = value["artifact_rows"]
    if not isinstance(rows, list) or rows != sorted(rows, key=lambda row: row.get("name", "")):
        raise MissionStateError("invalid_bootstrap_effective_seed_context", "bootstrap artifact rows are not sorted")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "sha256", "size_bytes"}:
            raise MissionStateError("invalid_bootstrap_effective_seed_context", "bootstrap artifact row fields differ")
        if not isinstance(row["name"], str) or not row["name"] or "/" in row["name"]:
            raise MissionStateError("invalid_bootstrap_effective_seed_context", "bootstrap artifact name is invalid")
        path = output_dir / row["name"]
        if not path.is_file() or path.is_symlink() or path.stat().st_size != row["size_bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise MissionStateError("bootstrap_skeleton_artifact_mismatch", f"bootstrap skeleton artifact differs: {row['name']}")
    return dict(value)


def _rewrite_bootstrap_seed_semantics(payload: Any, authority: dict[str, Any]) -> None:
    if isinstance(payload, dict):
        for key, value in list(payload.items()):
            if isinstance(value, str) and "supplied by user" in value:
                payload[key] = value.replace(
                    "seed supplied by user",
                    "effective seed selected by hash-bound bootstrap authority",
                ).replace(
                    "Seed supplied by user",
                    "Effective seed selected by hash-bound bootstrap authority",
                )
            elif key == "source" and value == "user_seed":
                payload[key] = "selected_bootstrap_authority"
            else:
                _rewrite_bootstrap_seed_semantics(value, authority)
        if isinstance(payload.get("identifier"), str) and payload["identifier"]:
            payload["bootstrap_set_id"] = authority["set_id"]
            payload["bootstrap_manifest_sha256"] = authority["manifest_sha256"]
            payload["bootstrap_request_sha256"] = authority["request_sha256"]
    elif isinstance(payload, list):
        for row in payload:
            _rewrite_bootstrap_seed_semantics(row, authority)


def _replay_bootstrap_effective_seed_skeleton(output_dir: Path, context: dict[str, Any]) -> None:
    expected_names = {row["name"] for row in context["artifact_rows"]} | {"bootstrap_effective_seed_context.json"}
    actual_names = {path.name for path in output_dir.iterdir()}
    if actual_names != expected_names or any(path.is_symlink() or not path.is_file() for path in output_dir.iterdir()):
        raise MissionStateError("bootstrap_skeleton_artifact_mismatch", "bootstrap skeleton artifact set differs")


def _build_public_metadata_packet(
    *,
    topic: str,
    seeds: list[str],
    output_dir: Path,
    providers: list[str] | None,
    max_records: int,
) -> dict[str, Any]:
    normalized_seeds = normalize_seeds(seeds)
    seeds = [row["display"] for row in normalized_seeds]
    try:
        provider_list = _normalize_public_metadata_providers(providers)
    except MissionStateError as exc:
        return _blocked(
            exc.code,
            str(exc),
            output_dir,
            next_required_actions=["choose one or more of: openalex, arxiv"],
        )
    if not provider_list:
        return _blocked(
            "missing_public_metadata_provider",
            "public-metadata mode requires at least one approved public metadata provider",
            output_dir,
            next_required_actions=["choose one or more of: openalex, arxiv"],
        )
    if (
        type(max_records) is not int
        or max_records <= 0
        or max_records > PUBLIC_METADATA_MAX_RECORDS
    ):
        return _blocked(
            "public_metadata_max_records_out_of_bounds",
            f"public-metadata max_records must be between 1 and {PUBLIC_METADATA_MAX_RECORDS}",
            output_dir,
            next_required_actions=[f"rerun with --max-records between 1 and {PUBLIC_METADATA_MAX_RECORDS}"],
        )
    if len(seeds) > max_records:
        return _blocked(
            "seed_count_exceeds_metadata_cap",
            "seed count exceeds the public metadata record cap",
            output_dir,
            next_required_actions=[
                "use a mission metadata cap that covers every seed or reduce the seed set before discovery"
            ],
        )
    unsupported = sorted(set(provider_list) - PUBLIC_METADATA_ALLOWED_PROVIDERS)
    if unsupported:
        return _blocked(
            "unsupported_public_metadata_provider",
            f"unsupported public metadata provider(s): {', '.join(unsupported)}",
            output_dir,
            next_required_actions=["use only approved providers: openalex, arxiv"],
        )

    existing = _preflight_public_metadata_v2_root(output_dir)
    if existing == "complete":
        try:
            return _reuse_public_metadata_v2_bundle(
                topic=topic,
                seeds=seeds,
                output_dir=output_dir,
                providers=provider_list,
                max_records=max_records,
            )
        except MissionStateError as exc:
            return _blocked(
                exc.code,
                str(exc),
                output_dir,
                next_required_actions=[
                    "use a new mission root or perform a separately reviewed manual recovery"
                ],
            )
    if existing == "partial":
        return _blocked(
            "partial_public_metadata_v2_residue",
            "public metadata V2 root contains partial or conflicting residue",
            output_dir,
            next_required_actions=[
                "use a new mission root or perform a separately reviewed manual recovery"
            ],
        )

    fetched_at = _utc_now_iso()
    try:
        collection = _collect_public_metadata(
            topic=topic,
            seeds=seeds,
            providers=provider_list,
            max_records=max_records,
            fetched_at=fetched_at,
        )
        quality = evaluate_discovery_quality(
            topic=topic,
            seeds=seeds,
            records=collection["records"],
            max_records=max_records,
        )
        artifacts = _compose_public_metadata_v2_artifacts(
            topic=topic,
            output_dir=output_dir,
            quality=quality,
            collection=collection,
            providers=provider_list,
            max_records=max_records,
        )
    except MissionStateError as exc:
        return _blocked(
            exc.code,
            str(exc),
            output_dir,
            next_required_actions=[
                "inspect the closed metadata fixture/provider response and repair the reported discovery predicate"
            ],
        )

    manifest = artifacts["build_manifest.json"]
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name in PUBLIC_METADATA_PACKET_FILES:
            if name == "build_manifest.json":
                continue
            _install_public_metadata_v2_child(output_dir / name, _public_metadata_v2_bytes(name, artifacts[name]))
        expected_children = set(PUBLIC_METADATA_PACKET_FILES) - {"build_manifest.json"}
        actual_children = {path.name for path in output_dir.iterdir()}
        if actual_children != expected_children or any(
            path.is_symlink() or not path.is_file() for path in output_dir.iterdir()
        ):
            raise MissionStateError(
                "conflicting_public_metadata_v2_residue",
                "public metadata V2 root changed before manifest commit",
            )
        _install_public_metadata_v2_child(
            output_dir / "build_manifest.json",
            _public_metadata_v2_bytes("build_manifest.json", manifest),
        )
    except (MissionStateError, OSError) as exc:
        code = exc.code if isinstance(exc, MissionStateError) else "public_metadata_v2_commit_failed"
        return _blocked(
            code,
            str(exc),
            output_dir,
            next_required_actions=[
                "use a new mission root or perform a separately reviewed manual recovery"
            ],
        )

    return {
        "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
        "status": "metadata_only_packet" if quality["status"] == "eligible" else "metadata_resolution_blocked",
        "mode": "public-metadata",
        "topic": topic,
        "seed_count": len(seeds),
        "record_count": manifest["record_count"],
        "providers": provider_list,
        "max_records": max_records,
        "output_dir": str(output_dir),
        "artifact_paths": manifest["artifact_paths"],
        "workflow_state": manifest["workflow_state"],
        "workflow_state_path": manifest["artifact_paths"]["workflow_state.json"],
        "provider_statuses": collection["provider_statuses"],
        "next_required_actions": manifest["next_required_actions"],
        "what_is_not_concluded": manifest["what_is_not_concluded"],
        "reused_existing": False,
    }


def _preflight_public_metadata_v2_root(output_dir: Path) -> str:
    if not output_dir.exists() and not output_dir.is_symlink():
        return "empty"
    mode = output_dir.lstat().st_mode
    if output_dir.is_symlink() or not output_dir.is_dir():
        return "partial"
    children = list(output_dir.iterdir())
    if not children:
        return "empty"
    names = {child.name for child in children}
    if any(child.is_symlink() or not child.is_file() for child in children):
        return "partial"
    return "complete" if names == set(PUBLIC_METADATA_PACKET_FILES) else "partial"


def _install_public_metadata_v2_child(path: Path, value: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise MissionStateError(
            "conflicting_public_metadata_v2_residue",
            f"public metadata V2 child already exists: {path.name}",
        )
    descriptor, temp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError as exc:
            raise MissionStateError(
                "conflicting_public_metadata_v2_residue",
                f"public metadata V2 child appeared during commit: {path.name}",
            ) from exc
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temp_path.unlink(missing_ok=True)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def _read_canonical_public_metadata_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_public_metadata_v2", f"invalid JSON: {path.name}") from exc
    if not isinstance(payload, dict) or raw != pretty_json_bytes(payload):
        raise MissionStateError("noncanonical_public_metadata_v2", f"noncanonical JSON: {path.name}")
    return payload


def _public_metadata_v2_bytes(name: str, payload: Any) -> bytes:
    if name == "survey_packet.md":
        if not isinstance(payload, str):
            raise MissionStateError("invalid_public_metadata_v2", "survey packet must be text")
        return payload.encode("utf-8")
    if not isinstance(payload, dict):
        raise MissionStateError("invalid_public_metadata_v2", f"{name} must be a JSON object")
    return pretty_json_bytes(payload)


def _compose_public_metadata_v2_artifacts(
    *,
    topic: str,
    output_dir: Path,
    quality: dict[str, Any],
    collection: dict[str, Any],
    providers: list[str],
    max_records: int,
) -> dict[str, Any]:
    normalized_seed_keys = quality["identity_resolution"]["normalized_seed_keys"]
    provider_statuses = _validate_public_metadata_provider_statuses(
        collection.get("provider_statuses"),
        providers=providers,
        normalized_seed_keys=normalized_seed_keys,
        max_records=max_records,
        input_records=quality["identity_resolution"]["input_records"],
    )
    raw_policy = collection.get("raw_response_policy")
    if (
        not isinstance(raw_policy, dict)
        or set(raw_policy) != {"raw_responses_saved", "privacy_scan", "reason"}
        or raw_policy.get("raw_responses_saved") is not False
        or not isinstance(raw_policy.get("privacy_scan"), str)
        or not raw_policy["privacy_scan"]
        or not isinstance(raw_policy.get("reason"), str)
        or not raw_policy["reason"]
    ):
        raise MissionStateError("invalid_public_metadata_v2", "raw response policy is invalid")
    fetched_at = collection.get("fetched_at")
    try:
        accessed_at = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError) as exc:
        raise MissionStateError("invalid_public_metadata_v2", "metadata access timestamp is invalid") from exc
    if accessed_at.tzinfo is None:
        raise MissionStateError("invalid_public_metadata_v2", "metadata access timestamp lacks timezone")
    expected_collection_status = (
        "metadata_collected"
        if quality["identity_resolution"]["input_records"]
        else "metadata_empty_or_unavailable"
    )
    if collection.get("status") != expected_collection_status:
        raise MissionStateError("invalid_public_metadata_v2", "metadata collection status is invalid")
    collection = {
        "status": expected_collection_status,
        "fetched_at": fetched_at,
        "provider_statuses": provider_statuses,
        "raw_response_policy": raw_policy,
    }
    records = _project_quality_records(
        quality["selected_records"],
        seed_paper_ids={
            row["selected_paper_id"]
            for row in quality["identity_resolution"]["seed_resolutions"]
            if row["selected_paper_id"] is not None
        },
    )
    edges = _quality_edges(quality, records)
    manifest = _manifest_from_public_metadata_packet_v2(
        topic=topic,
        output_dir=output_dir,
        records=records,
        collection=collection,
        providers=providers,
        max_records=max_records,
        quality=quality,
    )
    return {
        "candidate_ledger.json": _public_metadata_candidate_ledger_v2(
            topic=topic,
            quality=quality,
            collection=collection,
            max_records=max_records,
        ),
        "identity_resolution.json": quality["identity_resolution"],
        "relevance_ranking.json": quality["relevance_ranking"],
        "citation_map.json": _public_metadata_citation_map(
            topic,
            records,
            edges,
            collection,
            max_records=max_records,
        ),
        "source_support.json": _public_metadata_source_support(topic, records),
        "paper_classifications.json": _public_metadata_paper_classifications(topic, records),
        "claim_support.json": _public_metadata_claim_support(topic, records),
        "omission_risk.json": _public_metadata_omission_risk(topic, records, collection),
        "workflow_state.json": manifest["workflow_state"],
        "survey_packet.md": _public_metadata_survey_packet_markdown(
            topic,
            records,
            collection,
            max_records=max_records,
        ),
        "metadata_provenance.json": _public_metadata_provenance(
            topic,
            records,
            collection,
            providers=providers,
            max_records=max_records,
        ),
        "build_manifest.json": manifest,
    }


def _validate_public_metadata_provider_statuses(
    value: Any,
    *,
    providers: list[str],
    normalized_seed_keys: list[str],
    max_records: int,
    input_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_public_metadata_v2", "provider statuses must be a list")
    expected_keys = {
        "provider",
        "query_kind",
        "normalized_seed_key",
        "topic_query",
        "query_cap",
        "status",
        "record_count",
        "raw_response_saved",
    }
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise MissionStateError(
                "invalid_public_metadata_v2",
                f"provider status[{index}] keys are not exact",
            )
        if row["provider"] not in PUBLIC_METADATA_ALLOWED_PROVIDERS:
            raise MissionStateError("invalid_public_metadata_v2", "provider status provider is invalid")
        if not isinstance(row["query_kind"], str) or not row["query_kind"]:
            raise MissionStateError("invalid_public_metadata_v2", "provider status query kind is invalid")
        seed_key = row["normalized_seed_key"]
        if seed_key is not None and (not isinstance(seed_key, str) or not seed_key or "\x00" in seed_key):
            raise MissionStateError("invalid_public_metadata_v2", "provider status seed key is invalid")
        if type(row["topic_query"]) is not bool or type(row["raw_response_saved"]) is not bool:
            raise MissionStateError("invalid_public_metadata_v2", "provider status flags are invalid")
        if row["raw_response_saved"] is not False:
            raise MissionStateError("invalid_public_metadata_v2", "raw provider response persistence is forbidden")
        if row["status"] not in {"available", "unavailable", "blocked_invalid_seed"}:
            raise MissionStateError("invalid_public_metadata_v2", "provider status disposition is invalid")
        if (
            type(row["query_cap"]) is not int
            or not 1 <= row["query_cap"] <= PUBLIC_METADATA_MAX_RECORDS
            or type(row["record_count"]) is not int
            or not 0 <= row["record_count"] <= row["query_cap"]
        ):
            raise MissionStateError("invalid_public_metadata_v2", "provider status count is invalid")
        if row["status"] != "available" and row["record_count"] != 0:
            raise MissionStateError("invalid_public_metadata_v2", "unavailable provider status has records")
        rows.append(row)
    expected_routes = []
    seed_cap = min(5, max_records)
    topic_cap = max(1, min(max_records, 12))
    for provider in providers:
        expected_routes.extend(
            (provider, "seed_resolution", seed_key, False, seed_cap)
            for seed_key in normalized_seed_keys
        )
        expected_routes.append((provider, "topic_search", None, True, topic_cap))
    actual_routes = [
        (
            row["provider"],
            row["query_kind"],
            row["normalized_seed_key"],
            row["topic_query"],
            row["query_cap"],
        )
        for row in rows
    ]
    if actual_routes != expected_routes:
        raise MissionStateError(
            "invalid_public_metadata_v2",
            "provider status routes differ from the exact seed/topic query topology",
        )
    expected_route_set = {route[:4] for route in expected_routes}
    record_counts = {route[:4]: 0 for route in expected_routes}
    for index, record in enumerate(input_records):
        if not isinstance(record, dict):
            raise MissionStateError("invalid_public_metadata_v2", "input record is not an object")
        seen_routes = set()
        for provenance in record.get("query_provenance", []):
            route = (
                provenance.get("provider"),
                provenance.get("query_kind"),
                provenance.get("normalized_seed_key"),
                provenance.get("topic_query"),
            )
            if route not in expected_route_set:
                raise MissionStateError(
                    "invalid_public_metadata_v2",
                    f"input record[{index}] has foreign query provenance",
                )
            if provenance["provider"] not in record.get("providers", []):
                raise MissionStateError(
                    "invalid_public_metadata_v2",
                    f"input record[{index}] query provider is absent from providers",
                )
            if not any(
                provider_row.get("provider") == provenance["provider"]
                and provider_row.get("query_kind") == provenance["query_kind"]
                for provider_row in record.get("provider_records", [])
            ):
                raise MissionStateError(
                    "invalid_public_metadata_v2",
                    f"input record[{index}] lacks matching provider-record provenance",
                )
            seen_routes.add(route)
        for route in seen_routes:
            record_counts[route] += 1
    for row, route in zip(rows, expected_routes, strict=True):
        if row["record_count"] != record_counts[route[:4]]:
            raise MissionStateError(
                "invalid_public_metadata_v2",
                "provider status count differs from exact input-row provenance",
            )
    return rows


def validate_public_metadata_v2_bundle(
    *,
    topic: str,
    seeds: list[str],
    output_dir: Path,
    providers: list[str],
    max_records: int,
) -> dict[str, Any]:
    """Replay one committed V2 bundle without writes or provider calls."""

    output_dir = output_dir.absolute()
    if _preflight_public_metadata_v2_root(output_dir) != "complete":
        raise MissionStateError(
            "incomplete_public_metadata_v2",
            "public metadata V2 requires the exact manifest-committed artifact set",
        )
    manifest = _read_canonical_public_metadata_json(output_dir / "build_manifest.json")
    identity = _read_canonical_public_metadata_json(output_dir / "identity_resolution.json")
    provenance = _read_canonical_public_metadata_json(output_dir / "metadata_provenance.json")
    provider_list = _normalize_public_metadata_providers(providers)
    expected_paths = {name: str(output_dir / name) for name in PUBLIC_METADATA_PACKET_FILES}
    if (
        set(manifest)
        != {
            "schema_version",
            "status",
            "mode",
            "bundle_status",
            "workflow_state",
            "mission",
            "topic",
            "normalized_seed_keys",
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
        }
        or manifest.get("schema_version") != PUBLIC_METADATA_BUILD_MANIFEST_SCHEMA_VERSION
        or manifest.get("topic") != topic
        or manifest.get("providers") != provider_list
        or manifest.get("max_records") != max_records
        or manifest.get("artifact_paths") != expected_paths
    ):
        raise MissionStateError("stale_public_metadata_v2", "public metadata V2 manifest differs from request")
    normalized_seed_keys = [row["key"] for row in normalize_seeds(seeds)]
    if manifest.get("normalized_seed_keys") != normalized_seed_keys:
        raise MissionStateError("stale_public_metadata_v2", "manifest seed keys differ from request")
    if not isinstance(identity.get("input_records"), list):
        raise MissionStateError("invalid_public_metadata_v2", "identity input records must be a list")
    provider_statuses = _validate_public_metadata_provider_statuses(
        manifest.get("provider_statuses"),
        providers=provider_list,
        normalized_seed_keys=normalized_seed_keys,
        max_records=max_records,
        input_records=identity["input_records"],
    )
    replay = evaluate_discovery_quality(
        topic=topic,
        seeds=seeds,
        records=identity["input_records"],
        max_records=max_records,
    )
    collection = {
        "status": provenance["status"],
        "fetched_at": provenance["accessed_at"],
        "provider_statuses": provider_statuses,
        "raw_response_policy": provenance["raw_response_policy"],
    }
    expected = _compose_public_metadata_v2_artifacts(
        topic=topic,
        output_dir=output_dir,
        quality=replay,
        collection=collection,
        providers=provider_list,
        max_records=max_records,
    )
    artifact_rows = []
    for name in PUBLIC_METADATA_PACKET_FILES:
        raw = (output_dir / name).read_bytes()
        if raw != _public_metadata_v2_bytes(name, expected[name]):
            raise MissionStateError(
                "stale_public_metadata_v2",
                f"public metadata V2 semantic replay differs: {name}",
            )
        artifact_rows.append(
            {
                "name": name,
                "path": str(output_dir / name),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    return {
        "manifest": expected["build_manifest.json"],
        "candidate_ledger": expected["candidate_ledger.json"],
        "identity_resolution": replay["identity_resolution"],
        "relevance_ranking": replay["relevance_ranking"],
        "quality_status": replay["status"],
        "candidates": expected["candidate_ledger.json"]["included"],
        "artifact_rows": sorted(artifact_rows, key=lambda row: row["name"]),
    }


def _reuse_public_metadata_v2_bundle(
    *,
    topic: str,
    seeds: list[str],
    output_dir: Path,
    providers: list[str],
    max_records: int,
) -> dict[str, Any]:
    validated = validate_public_metadata_v2_bundle(
        topic=topic,
        seeds=seeds,
        output_dir=output_dir,
        providers=providers,
        max_records=max_records,
    )
    manifest = validated["manifest"]
    candidate = validated["candidate_ledger"]
    return {
        "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
        "status": "metadata_only_packet" if validated["quality_status"] == "eligible" else "metadata_resolution_blocked",
        "mode": "public-metadata",
        "topic": topic,
        "seed_count": len(seeds),
        "record_count": candidate["candidate_count"],
        "providers": providers,
        "max_records": max_records,
        "output_dir": str(output_dir),
        "artifact_paths": manifest["artifact_paths"],
        "workflow_state": manifest["workflow_state"],
        "workflow_state_path": manifest["artifact_paths"]["workflow_state.json"],
        "provider_statuses": candidate["provider_statuses"],
        "next_required_actions": manifest["next_required_actions"],
        "what_is_not_concluded": manifest["what_is_not_concluded"],
        "reused_existing": True,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_public_metadata_providers(providers: list[str] | None) -> list[str]:
    values = PUBLIC_METADATA_DEFAULT_PROVIDERS if providers is None else providers
    if not isinstance(values, list):
        raise MissionStateError(
            "invalid_public_metadata_provider",
            "public metadata providers must be a list of provider names",
        )
    normalized = []
    seen = set()
    for provider in values:
        if not isinstance(provider, str) or "\x00" in provider:
            raise MissionStateError(
                "invalid_public_metadata_provider",
                "public metadata provider must be a NUL-free string",
            )
        value = provider.strip().lower()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return sorted(normalized)


def _collect_public_metadata(
    *,
    topic: str,
    seeds: list[str],
    providers: list[str],
    max_records: int,
    fetched_at: str,
) -> dict[str, Any]:
    if len(seeds) > max_records:
        raise MissionStateError(
            "seed_count_exceeds_metadata_cap",
            "seed count exceeds the public metadata record cap",
        )
    records: list[dict[str, Any]] = []
    provider_statuses: list[dict[str, Any]] = []

    def invoke(function: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            result = function(*args, **kwargs)
        except Exception:
            return {"records": [], "status": {"status": "unavailable"}}
        return result if isinstance(result, dict) else {"records": [], "status": {"status": "unavailable"}}

    def append_query(
        result: dict[str, Any],
        *,
        provider: str,
        query_kind: str,
        seed_key: str | None,
        topic_query: bool,
        cap: int,
        roles: list[str],
    ) -> None:
        raw_status = result.get("status") if isinstance(result, dict) else None
        rows = result.get("records") if isinstance(result, dict) else None
        rows = rows if isinstance(rows, list) else []
        status_value = raw_status.get("status") if isinstance(raw_status, dict) else "unavailable"
        if status_value not in {"available", "unavailable", "blocked_invalid_seed"}:
            status_value = "unavailable"
        normalized_rows: list[dict[str, Any]] = []
        if status_value == "available":
            try:
                for source in rows[:cap]:
                    if not isinstance(source, dict):
                        raise MissionStateError("invalid_discovery_metadata", "provider row is not an object")
                    record = dict(source)
                    record["roles"] = list(dict.fromkeys([*(record.get("roles") or []), *roles]))
                    record["query_provenance"] = [
                        {
                            "provider": provider,
                            "query_kind": query_kind,
                            "normalized_seed_key": seed_key,
                            "topic_query": topic_query,
                        }
                    ]
                    normalize_record(record)
                    normalized_rows.append(record)
            except MissionStateError:
                status_value = "unavailable"
                normalized_rows = []
        status = {
            "provider": provider,
            "query_kind": query_kind,
            "normalized_seed_key": seed_key,
            "topic_query": topic_query,
            "query_cap": cap,
            "status": status_value,
            "record_count": len(normalized_rows),
            "raw_response_saved": False,
        }
        provider_statuses.append(status)
        records.extend(normalized_rows)

    if "arxiv" in providers:
        seed_cap = min(5, max_records)
        for seed in seeds:
            parsed = parse_seed(seed)
            if parsed["kind"] == "invalid":
                append_query(
                    {"records": [], "status": {"status": "blocked_invalid_seed"}},
                    provider="arxiv",
                    query_kind="seed_resolution",
                    seed_key=parsed["key"],
                    topic_query=False,
                    cap=seed_cap,
                    roles=[],
                )
                continue
            if parsed["kind"] == "arxiv_id":
                result = invoke(
                    _arxiv_metadata_query,
                    id_list=[parsed["value"].split(":", 1)[1]],
                    max_results=seed_cap,
                    query_kind="seed_resolution",
                )
            else:
                result = invoke(
                    _arxiv_metadata_query,
                    search_query=parsed["display"],
                    max_results=seed_cap,
                    query_kind="seed_resolution",
                )
            append_query(
                result,
                provider="arxiv",
                query_kind="seed_resolution",
                seed_key=parsed["key"],
                topic_query=False,
                cap=seed_cap,
                roles=[],
            )
        topic_cap = max(1, min(max_records, 12))
        append_query(
            invoke(
                _arxiv_metadata_query,
                search_query=topic,
                max_results=topic_cap,
                query_kind="topic_search",
            ),
            provider="arxiv",
            query_kind="topic_search",
            seed_key=None,
            topic_query=True,
            cap=topic_cap,
            roles=["adjacent_method"],
        )

    if "openalex" in providers:
        seed_cap = min(5, max_records)
        for seed in seeds:
            parsed = parse_seed(seed)
            if parsed["kind"] == "invalid":
                append_query(
                    {"records": [], "status": {"status": "blocked_invalid_seed"}},
                    provider="openalex",
                    query_kind="seed_resolution",
                    seed_key=parsed["key"],
                    topic_query=False,
                    cap=seed_cap,
                    roles=[],
                )
                continue
            append_query(
                invoke(
                    _openalex_metadata_search,
                    parsed["value"],
                    per_page=seed_cap,
                    query_kind="seed_resolution",
                ),
                provider="openalex",
                query_kind="seed_resolution",
                seed_key=parsed["key"],
                topic_query=False,
                cap=seed_cap,
                roles=[],
            )
        topic_cap = max(1, min(max_records, 12))
        append_query(
            invoke(
                _openalex_metadata_search,
                topic,
                per_page=topic_cap,
                query_kind="topic_search",
            ),
            provider="openalex",
            query_kind="topic_search",
            seed_key=None,
            topic_query=True,
            cap=topic_cap,
            roles=["adjacent_method"],
        )

    return {
        "status": "metadata_collected" if records else "metadata_empty_or_unavailable",
        "fetched_at": fetched_at,
        "records": records,
        "provider_statuses": provider_statuses,
        "raw_response_policy": {
            "raw_responses_saved": False,
            "privacy_scan": "not_applicable_raw_responses_not_saved",
            "reason": "Phase 7 persists normalized closed metadata rows only.",
        },
    }


def _resolve_openalex_seed_metadata(
    seed: str,
    *,
    arxiv_seed_record: dict[str, Any] | None,
    per_page: int,
) -> dict[str, Any]:
    statuses: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    queries = [seed]
    if arxiv_seed_record and arxiv_seed_record.get("title"):
        queries.append(str(arxiv_seed_record["title"]))

    for index, query in enumerate(dict.fromkeys(queries), start=1):
        query_kind = "seed_title_resolution" if index > 1 else "seed_search"
        result = _openalex_metadata_search(query, per_page=per_page, query_kind=query_kind)
        statuses.append(result["status"])
        if result["status"].get("status") != "available":
            continue
        for candidate in result["records"]:
            match = _openalex_seed_match(candidate, seed=seed, arxiv_seed_record=arxiv_seed_record, query_kind=query_kind)
            attempts.append(match)
            if match["matched"]:
                candidate["provider_records"].append({
                    "provider": "openalex",
                    "query_kind": "seed_resolution",
                    "resolution_method": match["method"],
                    "title_similarity": match["title_similarity"],
                    "year_delta": match["year_delta"],
                    "source_seed": seed,
                })
                statuses.append({
                    "provider": "openalex",
                    "query_kind": "seed_resolution",
                    "status": "resolved",
                    "record_count": 1,
                    "raw_response_saved": False,
                    "resolution_method": match["method"],
                    "title_similarity": match["title_similarity"],
                    "year_delta": match["year_delta"],
                    "openalex_id": candidate.get("openalex_id"),
                })
                return {
                    "record": candidate,
                    "statuses": statuses,
                    "resolution": match,
                    "attempts": attempts,
                }

    statuses.append({
        "provider": "openalex",
        "query_kind": "seed_resolution",
        "status": "blocked_unresolved",
        "record_count": 0,
        "raw_response_saved": False,
        "seed": seed,
        "attempt_count": len(attempts),
        "reason": "no OpenAlex candidate matched the seed metadata with the conservative title/year rule",
    })
    return {
        "record": None,
        "statuses": statuses,
        "resolution": {
            "matched": False,
            "method": "none",
            "title_similarity": 0.0,
            "year_delta": None,
        },
        "attempts": attempts,
    }


def _openalex_seed_match(
    candidate: dict[str, Any],
    *,
    seed: str,
    arxiv_seed_record: dict[str, Any] | None,
    query_kind: str,
) -> dict[str, Any]:
    seed_arxiv_id = _arxiv_id_from_identifier(seed)
    if seed_arxiv_id and candidate.get("arxiv_id") and str(candidate["arxiv_id"]).lower() == seed_arxiv_id.lower():
        return {
            "matched": True,
            "method": "arxiv_id",
            "title_similarity": _title_similarity(candidate.get("title"), arxiv_seed_record.get("title") if arxiv_seed_record else None),
            "year_delta": _year_delta(candidate.get("year"), arxiv_seed_record.get("year") if arxiv_seed_record else None),
            "query_kind": query_kind,
        }
    title_similarity = _title_similarity(candidate.get("title"), arxiv_seed_record.get("title") if arxiv_seed_record else None)
    year_delta = _year_delta(candidate.get("year"), arxiv_seed_record.get("year") if arxiv_seed_record else None)
    matched = bool(arxiv_seed_record and title_similarity >= 0.92 and (year_delta is None or year_delta <= 1))
    return {
        "matched": matched,
        "method": "title_year_metadata" if matched else "no_match",
        "title_similarity": round(title_similarity, 4),
        "year_delta": year_delta,
        "query_kind": query_kind,
    }


def _title_similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, _normalize_title_for_key(left), _normalize_title_for_key(right)).ratio()


def _year_delta(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    return abs(int(left) - int(right))


def _fetch_public_json(url: str, *, allowed_host: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() != allowed_host:
        raise ValueError(f"public metadata endpoint host {parsed.netloc} is not allowed")
    with urllib.request.urlopen(url, timeout=PUBLIC_METADATA_TIMEOUT_SECONDS) as response:
        return json.load(response)


def _openalex_metadata_search(query: str, *, per_page: int, query_kind: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "search": query,
        "per-page": str(per_page),
        "select": "id,display_name,authorships,publication_year,doi,cited_by_count,referenced_works,ids,type,publication_date",
    })
    url = f"{OPENALEX_WORKS_ENDPOINT}?{params}"
    started = time.perf_counter()
    try:
        data = _fetch_public_json(url, allowed_host="api.openalex.org")
        records = [_normalize_openalex_metadata_record(row, query_kind=query_kind) for row in data.get("results", [])]
        return {
            "records": records,
            "status": {
                "provider": "openalex",
                "query_kind": query_kind,
                "status": "available",
                "record_count": len(records),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "raw_response_saved": False,
            },
        }
    except Exception as exc:
        return {
            "records": [],
            "status": {
                "provider": "openalex",
                "query_kind": query_kind,
                "status": "unavailable",
                "record_count": 0,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "reason": str(exc),
                "raw_response_saved": False,
            },
        }


def _openalex_cited_by(openalex_id: str, *, per_page: int, query_kind: str) -> dict[str, Any]:
    openalex_work_id = openalex_id.rstrip("/").rsplit("/", 1)[-1]
    params = urllib.parse.urlencode({
        "filter": f"cites:{openalex_work_id}",
        "per-page": str(per_page),
        "sort": "cited_by_count:desc",
        "select": "id,display_name,authorships,publication_year,doi,cited_by_count,referenced_works,ids,type,publication_date",
    })
    url = f"{OPENALEX_WORKS_ENDPOINT}?{params}"
    started = time.perf_counter()
    try:
        data = _fetch_public_json(url, allowed_host="api.openalex.org")
        records = [_normalize_openalex_metadata_record(row, query_kind=query_kind) for row in data.get("results", [])]
        return {
            "records": records,
            "status": {
                "provider": "openalex",
                "query_kind": query_kind,
                "status": "available",
                "record_count": len(records),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "raw_response_saved": False,
            },
        }
    except Exception as exc:
        return {
            "records": [],
            "status": {
                "provider": "openalex",
                "query_kind": query_kind,
                "status": "unavailable",
                "record_count": 0,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "reason": str(exc),
                "raw_response_saved": False,
            },
        }


def _normalize_openalex_metadata_record(work: dict[str, Any], *, query_kind: str) -> dict[str, Any]:
    openalex_id = work.get("id")
    ids = work.get("ids") or {}
    authors = [
        author.get("author", {}).get("display_name", "")
        for author in work.get("authorships", [])
        if author.get("author", {}).get("display_name")
    ]
    doi = _normalize_doi(work.get("doi") or ids.get("doi"))
    arxiv_id = _arxiv_id_from_identifier(ids.get("arxiv") or "")
    return {
        "record_key": _metadata_record_key(doi=doi, arxiv_id=arxiv_id, openalex_id=openalex_id, title=work.get("display_name")),
        "title": work.get("display_name"),
        "authors": authors,
        "year": work.get("publication_year"),
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": openalex_id,
        "landing_page_url": openalex_id,
        "citation_count": work.get("cited_by_count"),
        "providers": ["openalex"],
        "roles": [],
        "provider_records": [{
            "provider": "openalex",
            "query_kind": query_kind,
            "source_id": openalex_id,
            "citation_count": work.get("cited_by_count"),
            "publication_date": work.get("publication_date"),
            "work_type": work.get("type"),
        }],
        "referenced_works": [str(item) for item in work.get("referenced_works", []) if item],
    }


def _arxiv_metadata_query(
    *,
    search_query: str | None = None,
    id_list: list[str] | None = None,
    max_results: int,
    query_kind: str,
) -> dict[str, Any]:
    params: dict[str, str] = {
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    if id_list:
        params["id_list"] = ",".join(id_list)
    else:
        params["search_query"] = f"all:{' '.join((search_query or '').split())}"
    url = f"{ARXIV_QUERY_ENDPOINT}?{urllib.parse.urlencode(params)}"
    started = time.perf_counter()
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc.lower() != "export.arxiv.org":
            raise ValueError(f"public metadata endpoint host {parsed.netloc} is not allowed")
        with urllib.request.urlopen(url, timeout=PUBLIC_METADATA_TIMEOUT_SECONDS) as response:
            body = response.read(2_000_000)
        records = _parse_arxiv_metadata_records(body, query_kind=query_kind)
        return {
            "records": records[:max_results],
            "status": {
                "provider": "arxiv",
                "query_kind": query_kind,
                "status": "available",
                "record_count": min(len(records), max_results),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "raw_response_saved": False,
            },
        }
    except Exception as exc:
        return {
            "records": [],
            "status": {
                "provider": "arxiv",
                "query_kind": query_kind,
                "status": "unavailable",
                "record_count": 0,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "reason": str(exc),
                "raw_response_saved": False,
            },
        }


def _parse_arxiv_metadata_records(body: bytes, *, query_kind: str) -> list[dict[str, Any]]:
    namespaces = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    feed = ET.fromstring(body)
    records = []
    for entry in feed.findall("atom:entry", namespaces):
        raw_id = _atom_text(entry, "atom:id", namespaces)
        arxiv_id = _arxiv_id_from_identifier(raw_id or "")
        if arxiv_id is None:
            continue
        title = _atom_text(entry, "atom:title", namespaces)
        authors = [
            name
            for author in entry.findall("atom:author", namespaces)
            if (name := _atom_text(author, "atom:name", namespaces))
        ]
        published = _atom_text(entry, "atom:published", namespaces) or ""
        primary = entry.find("arxiv:primary_category", namespaces)
        primary_category = primary.attrib.get("term") if primary is not None else None
        records.append({
            "record_key": _metadata_record_key(doi=None, arxiv_id=arxiv_id, openalex_id=None, title=title),
            "title": title,
            "authors": authors,
            "year": int(published[:4]) if published[:4].isdigit() else None,
            "doi": None,
            "arxiv_id": arxiv_id,
            "openalex_id": None,
            "landing_page_url": f"https://arxiv.org/abs/{arxiv_id}",
            "citation_count": None,
            "providers": ["arxiv"],
            "roles": [],
            "provider_records": [{
                "provider": "arxiv",
                "query_kind": query_kind,
                "source_id": arxiv_id,
                "primary_category": primary_category,
                "published": published or None,
            }],
            "referenced_works": [],
        })
    return records


def _atom_text(element: ET.Element, path: str, namespaces: dict[str, str]) -> str | None:
    found = element.find(path, namespaces)
    if found is None or found.text is None:
        return None
    return " ".join(found.text.split())


def _arxiv_id_from_identifier(identifier: str) -> str | None:
    value = (identifier or "").strip()
    if not value:
        return None
    if value.lower().startswith("arxiv:"):
        value = value.split(":", 1)[1].strip()
    if "arxiv.org/abs/" in value:
        value = value.rstrip("/").rsplit("/", 1)[-1]
    if "arxiv.org/pdf/" in value:
        value = value.rstrip("/").rsplit("/", 1)[-1].removesuffix(".pdf")
    if ARXIV_ID_PATTERN.match(value):
        return value
    return None


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    if doi.lower().startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/") :]
    return doi.lower() or None


def _metadata_record_key(
    *,
    doi: str | None,
    arxiv_id: str | None,
    openalex_id: str | None,
    title: str | None,
) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    if arxiv_id:
        return f"arxiv:{arxiv_id.lower()}"
    if openalex_id:
        return _openalex_record_key(openalex_id)
    return f"title:{_normalize_title_for_key(title)}"


def _openalex_record_key(openalex_id: str) -> str:
    return f"openalex:{openalex_id.rstrip('/').rsplit('/', 1)[-1].lower()}"


def _normalize_title_for_key(title: str | None) -> str:
    text = (title or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip() or "unknown"


def _merge_public_metadata_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record["record_key"]
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                **record,
                "providers": list(dict.fromkeys(record.get("providers", []))),
                "roles": list(dict.fromkeys(record.get("roles", []))),
                "provider_records": list(record.get("provider_records", [])),
                "referenced_works": list(record.get("referenced_works", [])),
            }
            continue
        for field in ["title", "year", "doi", "arxiv_id", "openalex_id", "landing_page_url"]:
            if not existing.get(field) and record.get(field):
                existing[field] = record[field]
        if record.get("citation_count") is not None:
            counts = [value for value in [existing.get("citation_count"), record.get("citation_count")] if value is not None]
            existing["citation_count"] = max(counts) if counts else None
        existing["authors"] = list(dict.fromkeys((existing.get("authors") or []) + (record.get("authors") or [])))
        existing["providers"] = list(dict.fromkeys((existing.get("providers") or []) + (record.get("providers") or [])))
        existing["roles"] = list(dict.fromkeys((existing.get("roles") or []) + (record.get("roles") or [])))
        existing["provider_records"].extend(record.get("provider_records", []))
        existing["referenced_works"] = list(dict.fromkeys((existing.get("referenced_works") or []) + (record.get("referenced_works") or [])))
    return list(grouped.values())


def _assign_public_metadata_paper_keys(records: list[dict[str, Any]], *, max_records: int) -> list[dict[str, Any]]:
    def sort_key(record: dict[str, Any]) -> tuple[int, int, str]:
        role_priority = 0 if "seed" in record.get("roles", []) else 1
        citation_count = record.get("citation_count")
        count_sort = -(citation_count if isinstance(citation_count, int) else -1)
        return (role_priority, count_sort, str(record.get("title") or record.get("record_key")))

    assigned = []
    for index, record in enumerate(sorted(records, key=sort_key)[:max_records], start=1):
        assigned.append({**record, "paper_key": f"p_meta_{index:03d}"})
    return assigned


def _project_quality_records(
    components: list[dict[str, Any]],
    *,
    seed_paper_ids: set[str],
) -> list[dict[str, Any]]:
    records = []
    for component in components:
        records.append({
            "record_key": component["paper_id"],
            "paper_key": component["paper_id"],
            "title": component["title"],
            "authors": component["authors"],
            "year": component["years"][-1] if component["years"] else None,
            "doi": component["doi"],
            "arxiv_id": component["arxiv_ids"][-1] if component["arxiv_ids"] else None,
            "openalex_id": component["openalex_ids"][0] if component["openalex_ids"] else None,
            "landing_page_url": next(
                (row["landing_page_url"] for row in component["rows"] if row["landing_page_url"]),
                None,
            ),
            "citation_count": component["citation_count"],
            "providers": component["providers"],
            "roles": sorted(
                set(component["roles"])
                | ({"seed"} if component["paper_id"] in seed_paper_ids else set())
            ),
            "provider_records": sorted(
                [provider for row in component["rows"] for provider in row["provider_records"]],
                key=canonical_json_bytes,
            ),
            "referenced_works": component["referenced_works"],
        })
    return records


def _quality_edges(quality: dict[str, Any], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    record_key_to_paper_id = quality["record_key_to_paper_id"]
    openalex_to_paper_id = {
        openalex_id: component["paper_id"]
        for component in quality["selected_records"]
        for openalex_id in component["openalex_ids"]
    }
    seed_ids = {
        row["selected_paper_id"]
        for row in quality["identity_resolution"]["seed_resolutions"]
        if row["selected_paper_id"]
    }
    edges: list[dict[str, Any]] = []
    for record in records:
        source = record_key_to_paper_id.get(record["record_key"], record["paper_key"])
        for referenced in record["referenced_works"]:
            target = openalex_to_paper_id.get(referenced)
            if target and target != source:
                edges.append({
                    "source": source,
                    "target": target,
                    "relation": "backward_reference_metadata",
                    "evidence_class": "metadata_only_public_identifier_only",
                    "provider": "openalex",
                })
    for source in sorted(seed_ids):
        for record in records:
            target = record["paper_key"]
            if target != source and "adjacent_method" in record["roles"]:
                edges.append({
                    "source": source,
                    "target": target,
                    "relation": "adjacent_topic_candidate_metadata",
                    "evidence_class": "metadata_only_public",
                    "provider": "openalex/arxiv",
                })
    return sorted(
        {canonical_json_bytes(edge): edge for edge in edges}.values(),
        key=canonical_json_bytes,
    )


def _public_metadata_candidate_ledger_v2(
    topic: str,
    quality: dict[str, Any],
    collection: dict[str, Any],
    *,
    max_records: int,
) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_METADATA_CANDIDATE_SCHEMA_VERSION,
        "status": "metadata_only_public_v2" if quality["status"] == "eligible" else "blocked_seed_resolution",
        "topic": topic,
        "candidate_count": len(quality["included"]),
        "max_records": max_records,
        "included": quality["included"],
        "excluded": quality["excluded"],
        "duplicates": quality["duplicates"],
        "identity_resolution_path": "identity_resolution.json",
        "relevance_ranking_path": "relevance_ranking.json",
        "provider_statuses": collection["provider_statuses"],
        "raw_response_policy": collection["raw_response_policy"],
        "next_required_actions": [
            "inspect primary sources before supporting technical claims",
            "run source/download status collection only after a separate approval",
            "verify typed backward, forward, and adjacent metadata layers before prose drafting",
            "inspect sources before converting metadata relations into survey claims",
        ],
    }


def _public_metadata_candidate_ledger(
    topic: str,
    records: list[dict[str, Any]],
    collection: dict[str, Any],
    *,
    max_records: int,
) -> dict[str, Any]:
    """Legacy V1 composer retained only for exact replay compatibility tests."""
    return {
        "schema_version": SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION,
        "status": "metadata_only_public",
        "topic": topic,
        "candidate_count": len(records),
        "max_records": max_records,
        "included": [
            {
                "paper_key": row["paper_key"],
                "identifier": _public_metadata_identifier(row),
                "title": row.get("title"),
                "authors": row.get("authors", []),
                "year": row.get("year"),
                "roles": row.get("roles", []),
                "providers": row.get("providers", []),
                "citation_count": row.get("citation_count"),
                "citation_count_policy": "coverage_signal_only",
                "reason": _public_metadata_inclusion_reason(row),
                "metadata_only": True,
            }
            for row in records
        ],
        "excluded": [],
        "duplicates": [],
        "provider_statuses": collection["provider_statuses"],
        "raw_response_policy": collection["raw_response_policy"],
        "next_required_actions": ["inspect primary sources before supporting technical claims"],
    }


def _public_metadata_citation_map(
    topic: str,
    records: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    collection: dict[str, Any],
    *,
    max_records: int,
) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CITATION_MAP_SCHEMA_VERSION,
        "status": "metadata_only_public_partial",
        "topic": topic,
        "seed_papers": [row["paper_key"] for row in records if "seed" in row.get("roles", [])],
        "expansion_policy": {
            "backward_depth": 1,
            "forward_depth": 1,
            "adjacent_query_count": 1,
            "max_nodes": max_records,
            "max_downloads": 0,
            "download_or_source_intake_allowed": False,
        },
        "nodes": [
            {
                "paper_key": row["paper_key"],
                "identifier": _public_metadata_identifier(row),
                "title": row.get("title"),
                "roles": row.get("roles", []),
                "cluster": _public_metadata_cluster(row),
                "layer": _public_metadata_layer(row),
                "local_source_status": "metadata_only_public",
                "download_status": "source_not_attempted",
                "review_status": "requires_primary_source_review",
                "survey_relevance": _public_metadata_inclusion_reason(row),
                "citation_count": row.get("citation_count"),
                "citation_count_policy": "coverage_signal_only",
                "metadata_relation_status": "provider_metadata_unverified_by_source",
            }
            for row in records
        ],
        "edges": edges,
        "clusters": _public_metadata_clusters(records),
        "frontiers": _public_metadata_frontiers(records, edges, collection),
        "survey_packet_paths": {
            "candidate_ledger": "candidate_ledger.json",
            "source_support": "source_support.json",
            "paper_classifications": "paper_classifications.json",
            "claim_support": "claim_support.json",
            "omission_risk": "omission_risk.json",
            "metadata_provenance": "metadata_provenance.json",
        },
        "next_required_actions": [
            "verify citation relations against provider documentation or source references",
            "inspect seed references for true backward lineage",
            "inspect citing papers before calling them major works in prose",
            "treat blocked provider frontiers as omission risks, not as empty truth",
        ],
    }


def _public_metadata_source_support(topic: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_SOURCE_SUPPORT_SCHEMA_VERSION,
        "status": "metadata_only_no_sources_inspected",
        "topic": topic,
        "papers": [
            {
                "paper_key": row["paper_key"],
                "identifier": _public_metadata_identifier(row),
                "title": row.get("title"),
                "source_status": "metadata_only_public",
                "download_status": "source_not_attempted",
                "primary_source_type": "not_inspected",
                "checked_anchors": [],
                "allowed_claims": [],
                "forbidden_claims": [
                    "technical theorem, algorithm, or empirical claims",
                    "source availability claims",
                    "priority or lineage claims beyond provider metadata relation labels",
                    "literature completeness claims",
                ],
            }
            for row in records
        ],
        "next_required_actions": [
            "obtain separate approval before any PDF/source/full-text download",
            "record checked sections, equations, algorithms, tables, and appendix anchors before claim support",
        ],
    }


def _public_metadata_paper_classifications(topic: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CLASSIFICATION_SCHEMA_VERSION,
        "status": "metadata_only_requires_source_review",
        "topic": topic,
        "classifications": [
            {
                "paper_key": row["paper_key"],
                "identifier": _public_metadata_identifier(row),
                "title": row.get("title"),
                "labels": _public_metadata_labels(row),
                "classification_status": "metadata_only_preliminary",
                "source_status": "metadata_only_public",
                "claim_support_allowed": False,
                "metadata_layer": _public_metadata_layer(row),
            }
            for row in records
        ],
        "allowed_labels": SURVEY_CLASSIFICATION_ALLOWED_LABELS,
    }


def _public_metadata_claim_support(topic: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CLAIM_SUPPORT_SCHEMA_VERSION,
        "status": "metadata_only_no_supported_technical_claims",
        "topic": topic,
        "claims": [],
        "claim_support_policy": {
            "technical_claims_require_checked_anchors": True,
            "metadata_only_support_allowed_for_technical_claims": False,
            "citation_counts_are_coverage_signals_only": True,
            "titles_abstracts_and_provider_snippets_do_not_support_technical_claims": True,
        },
        "metadata_only_papers_pending_anchor_review": [row["paper_key"] for row in records],
    }


def _public_metadata_omission_risk(topic: str, records: list[dict[str, Any]], collection: dict[str, Any]) -> dict[str, Any]:
    risks = [
        {
            "risk_id": "source_text_not_inspected",
            "severity": "high",
            "risk": "No source text, equations, algorithms, experiments, related-work sections, or appendices were inspected.",
            "expected_action": "run source-aware audit after explicit source/download approval",
        },
        {
            "risk_id": "public_metadata_frontier_partial",
            "severity": "high",
            "risk": "OpenAlex/arXiv metadata queries are bounded by max_records and do not prove citation-map completeness.",
            "expected_action": "repeat with documented provider budgets and source checks before survey prose",
        },
        {
            "risk_id": "metadata_relations_unverified",
            "severity": "medium",
            "risk": "Backward, forward, and adjacent relations are provider metadata signals only.",
            "expected_action": "verify relations against primary sources or provider-specific citation records",
        },
    ]
    if not any("major_citing_work" in row.get("roles", []) for row in records):
        risks.append({
            "risk_id": "forward_citation_frontier_blocked_or_empty",
            "severity": "high",
            "risk": "No forward-citation metadata rows are present for the seed in the bounded packet.",
            "expected_action": "resolve seed metadata to a provider citation id or record provider-blocked frontier before prose drafting",
        })
    if not any("backward_lineage_candidate" in row.get("roles", []) for row in records):
        risks.append({
            "risk_id": "backward_lineage_frontier_blocked_or_empty",
            "severity": "high",
            "risk": "No backward-reference metadata rows are present for the seed in the bounded packet.",
            "expected_action": "inspect source references or provider reference metadata before prose drafting",
        })
    return {
        "schema_version": SURVEY_OMISSION_RISK_SCHEMA_VERSION,
        "status": "metadata_only_partial_frontier",
        "topic": topic,
        "risks": risks,
        "provider_statuses": collection["provider_statuses"],
        "metadata_only_papers": [row["paper_key"] for row in records],
    }


def _public_metadata_provenance(
    topic: str,
    records: list[dict[str, Any]],
    collection: dict[str, Any],
    *,
    providers: list[str],
    max_records: int,
) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_METADATA_PROVENANCE_SCHEMA_VERSION,
        "status": collection["status"],
        "topic": topic,
        "providers": providers,
        "accessed_at": collection["fetched_at"],
        "max_records": max_records,
        "record_count": len(records),
        "provider_statuses": collection["provider_statuses"],
        "raw_response_policy": collection["raw_response_policy"],
        "download_or_source_intake": {
            "allowed": False,
            "attempted": False,
            "pdf_downloads_attempted": False,
            "source_downloads_attempted": False,
            "credentials_used": False,
        },
        "records": [
            {
                "paper_key": row["paper_key"],
                "identifier": _public_metadata_identifier(row),
                "title": row.get("title"),
                "providers": row.get("providers", []),
                "roles": row.get("roles", []),
                "metadata_layer": _public_metadata_layer(row),
                "provider_records": row.get("provider_records", []),
                "metadata_only": True,
            }
            for row in records
        ],
    }


def _public_metadata_survey_packet_markdown(
    topic: str,
    records: list[dict[str, Any]],
    collection: dict[str, Any],
    *,
    max_records: int,
) -> str:
    seed_lines = "\n".join(
        f"- `{row['paper_key']}`: {row.get('title') or _public_metadata_identifier(row)}"
        for row in records
        if "seed" in row.get("roles", [])
    ) or "- none resolved"
    provider_lines = "\n".join(
        f"- `{row['provider']}` `{row['query_kind']}`: {row['status']} ({row.get('record_count', 0)} records)"
        for row in collection["provider_statuses"]
    ) or "- none"
    candidate_lines = "\n".join(
        f"- `{row['paper_key']}`: {row.get('title') or _public_metadata_identifier(row)}; roles: {', '.join(row.get('roles', [])) or 'metadata_candidate'}; providers: {', '.join(row.get('providers', []))}."
        for row in records
    ) or "- none"
    return f"""# Survey Evidence Packet

## Status

`METADATA_ONLY_PUBLIC_PARTIAL`

## Topic

{topic}

## Boundary

This packet used public metadata only. No PDF, source, or full-text download was attempted. Metadata can prioritize inspection and expose citation-map candidates, but it cannot support technical claims.

## Seed Papers

{seed_lines}

## Provider Status

{provider_lines}

## Candidate Metadata Rows

{candidate_lines}

## Required Artifacts

- `candidate_ledger.json`
- `citation_map.json`
- `source_support.json`
- `paper_classifications.json`
- `claim_support.json`
- `omission_risk.json`
- `metadata_provenance.json`

## Next Required Actions

1. Inspect primary sources before supporting any theorem, algorithm, empirical, or lineage claim.
2. Run approved source/download status collection before calling sources available.
3. Expand and verify backward/forward citation relations before drafting survey prose.

## What Is Not Concluded

- This packet does not prove literature completeness.
- This packet does not support technical claims.
- This packet does not establish source availability, download reliability, product readiness, or scientific correctness.
- This packet does not prove complete live web coverage beyond the bounded max-records={max_records} provider queries.
"""


def _manifest_from_public_metadata_packet(
    *,
    topic: str,
    output_dir: Path,
    records: list[dict[str, Any]],
    collection: dict[str, Any],
    providers: list[str],
    max_records: int,
) -> dict[str, Any]:
    artifact_names = PACKET_FILES + ("metadata_provenance.json",)
    return {
        "schema_version": SURVEY_BUILD_MANIFEST_SCHEMA_VERSION,
        "status": "metadata_only_packet",
        "mode": "public-metadata",
        "workflow_state": _workflow_state(
            state="metadata_only_public_packet",
            mode="public-metadata",
            ready_for_writer=True,
            ready_for_prose=False,
            safe_next_commands=[
                "inspect candidate_ledger.json, citation_map.json, source_support.json, claim_support.json, and omission_risk.json",
                "prepare a source/download intake plan and request explicit approval before source_fetch or PDF/full-text download",
                "after approved source intake and anchor extraction, run ra survey packet --metadata-dir <metadata-dir> --source-status-dir <phase4-dir> --anchor-dir <phase5-dir> --out <packet-dir>",
            ],
            approval_required_for=[
                "source_fetch, PDF download, or full-text download",
                "private or credentialed database use",
                "using metadata rows as technical claim support",
            ],
            blocked_reasons=[
                "metadata-only packet has no inspected source anchors",
                "citation relations are provider metadata signals only",
                "bounded max-records metadata does not establish completeness",
            ],
        ),
        "mission": "topic + seed paper -> citation map -> survey-ready evidence packet",
        "topic": topic,
        "providers": providers,
        "max_records": max_records,
        "record_count": len(records),
        "provider_statuses": collection["provider_statuses"],
        "artifact_paths": {name: str(output_dir / name) for name in artifact_names},
        "mission_control_path": "docs/plans/literature_survey_automation_mission_control_2026-07-06.md",
        "milestones_path": "docs/plans/literature_survey_automation_milestones.json",
        "next_required_actions": [
            "inspect primary sources before supporting technical claims",
            "run source/download status collection only after separate approval",
            "verify citation-map relations before survey prose",
            "validate packet with SurveyBench metadata-only negative checks",
        ],
        "forbidden_claims": [
            "do not claim technical source support from metadata-only output",
            "do not claim source/PDF availability because download/source intake was not attempted",
            "do not claim full literature coverage from bounded public metadata queries",
            "do not claim product readiness or scientific correctness from this pilot",
        ],
        "what_is_not_concluded": [
            "source availability",
            "technical claim support",
            "backward lineage completeness",
            "forward citation coverage completeness",
            "adjacent cluster completeness",
            "survey prose quality",
            "scientific correctness",
            "product readiness",
        ],
    }


def _manifest_from_public_metadata_packet_v2(
    *,
    topic: str,
    output_dir: Path,
    records: list[dict[str, Any]],
    collection: dict[str, Any],
    providers: list[str],
    max_records: int,
    quality: dict[str, Any],
) -> dict[str, Any]:
    eligible = quality["status"] == "eligible"
    workflow = _workflow_state(
        state="metadata_only_public_v2" if eligible else "blocked_seed_resolution",
        mode="public-metadata",
        ready_for_writer=eligible,
        ready_for_prose=False,
        safe_next_commands=(
            [
                "inspect identity_resolution.json, relevance_ranking.json, and candidate_ledger.json",
                "run capability-gated mission source intake only after current V2 replay validation",
            ]
            if eligible
            else [
                "inspect the exact blocked seed rows and candidate choices in identity_resolution.json",
                "do not run source intake until every mission seed resolves without conflict",
            ]
        ),
        approval_required_for=[
            "source_fetch, PDF download, or full-text download",
            "private or credentialed database use",
            "using metadata, identity, or relevance rows as technical claim support",
        ],
        blocked_reasons=(
            [
                "metadata-only packet has no inspected source anchors",
                "citation relations are provider metadata signals only",
                "bounded metadata and heuristic relevance do not establish completeness",
            ]
            if eligible
            else [
                "one or more mission seeds are ambiguous, unresolved, invalid, or in identity conflict",
                "source intake is forbidden while the global seed-resolution gate is blocked",
            ]
        ),
    )
    return {
        "schema_version": PUBLIC_METADATA_BUILD_MANIFEST_SCHEMA_VERSION,
        "status": "metadata_only_packet_v2" if eligible else "blocked_seed_resolution",
        "mode": "public-metadata",
        "bundle_status": quality["status"],
        "workflow_state": workflow,
        "mission": "topic and seeds to replayable identity and relevance metadata",
        "topic": topic,
        "normalized_seed_keys": quality["identity_resolution"]["normalized_seed_keys"],
        "providers": providers,
        "max_records": max_records,
        "record_count": len(records),
        "provider_statuses": collection["provider_statuses"],
        "artifact_paths": {name: str(output_dir / name) for name in PUBLIC_METADATA_PACKET_FILES},
        "mission_control_path": "docs/plans/literature_survey_automation_mission_control_2026-07-06.md",
        "milestones_path": "docs/plans/literature_survey_automation_milestones.json",
        "next_required_actions": (
            [
                "inspect primary sources before supporting technical claims",
                "continue to capability-gated source intake only through current mission V2 authority",
                "carry every exclusion, duplicate, conflict, and cap disposition into coverage review",
            ]
            if eligible
            else [
                "resolve or explicitly review every blocked seed choice before source intake",
                "preserve the blocked artifact as evidence; do not guess a paper identity",
            ]
        ),
        "forbidden_claims": [
            "metadata and relevance rows do not support technical claims",
            "identity clustering does not establish source, version, or retraction safety",
            "citation counts do not establish correctness or substantive relevance",
            "bounded metadata does not establish literature completeness",
        ],
        "what_is_not_concluded": [
            "source availability or safety",
            "technical claim support",
            "identity truth beyond the checked metadata predicates",
            "substantive relevance truth or recall",
            "backward or forward coverage completeness",
            "survey prose, scientific, product, or release readiness",
        ],
    }


def _public_metadata_identifier(row: dict[str, Any]) -> str:
    if row.get("doi"):
        return f"doi:{row['doi']}"
    if row.get("arxiv_id"):
        return f"arxiv:{row['arxiv_id']}"
    if row.get("openalex_id"):
        return str(row["openalex_id"])
    return row.get("record_key", "unknown")


def _public_metadata_inclusion_reason(row: dict[str, Any]) -> str:
    roles = set(row.get("roles", []))
    if "seed" in roles:
        return "seed supplied by user and resolved through public metadata"
    if "major_citing_work" in roles:
        return "public metadata indicates this work cites a seed candidate"
    if "backward_lineage_candidate" in roles:
        return "public metadata identifier appears in a seed candidate reference list"
    if "adjacent_method" in roles:
        return "public metadata topic search candidate"
    return "public metadata candidate"


def _public_metadata_cluster(row: dict[str, Any]) -> str:
    roles = set(row.get("roles", []))
    if "seed" in roles:
        return "seed_metadata"
    if "major_citing_work" in roles:
        return "forward_citation_metadata"
    if "backward_lineage_candidate" in roles:
        return "backward_lineage_metadata"
    return "adjacent_topic_metadata"


def _public_metadata_layer(row: dict[str, Any]) -> str:
    roles = set(row.get("roles", []))
    if "seed" in roles:
        return "seed"
    if "major_citing_work" in roles:
        return "forward"
    if "backward_lineage_candidate" in roles:
        return "backward"
    if "adjacent_method" in roles:
        return "adjacent"
    return "unclassified_metadata"


def _public_metadata_labels(row: dict[str, Any]) -> list[str]:
    labels = []
    roles = set(row.get("roles", []))
    if "seed" in roles:
        labels.append("seed")
    if "major_citing_work" in roles:
        labels.append("major_citing_work")
    if "adjacent_method" in roles:
        labels.append("adjacent_method")
    if "backward_lineage_candidate" in roles:
        labels.append("background")
    return labels or ["source_blocked"]


def _public_metadata_clusters(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters = []
    for cluster in ["seed_metadata", "forward_citation_metadata", "backward_lineage_metadata", "adjacent_topic_metadata"]:
        members = [row["paper_key"] for row in records if _public_metadata_cluster(row) == cluster]
        if members:
            clusters.append({
                "cluster_id": cluster,
                "label": cluster.replace("_", " "),
                "members": members,
                "evidence_class": "metadata_only_public",
            })
    return clusters


def _public_metadata_frontiers(
    records: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    collection: dict[str, Any],
) -> list[dict[str, Any]]:
    layers = {row["paper_key"]: _public_metadata_layer(row) for row in records}
    edge_relations = {str(row.get("relation")) for row in edges}
    statuses = collection.get("provider_statuses", [])
    seed_resolution = [
        row for row in statuses
        if isinstance(row, dict) and row.get("provider") == "openalex" and row.get("query_kind") == "seed_resolution"
    ]
    seed_resolution_status = seed_resolution[-1].get("status") if seed_resolution else "not_attempted"
    frontier_specs = [
        (
            "seed",
            "seed",
            "seed_metadata",
            "seed metadata resolved from approved public metadata provider",
            "seed metadata was not resolved",
        ),
        (
            "backward",
            "backward",
            "backward_reference_metadata",
            "backward reference metadata rows are present",
            "backward reference frontier is blocked or empty because no source references were inspected and provider references were unavailable for the resolved seed",
        ),
        (
            "forward",
            "forward",
            "forward_citation_metadata",
            "forward citation metadata rows are present",
            "forward citation frontier is blocked or empty because the seed was not resolved to a provider citation id or provider returned no citing rows",
        ),
        (
            "adjacent",
            "adjacent",
            "adjacent_topic_candidate_metadata",
            "adjacent topic metadata rows are present",
            "adjacent topic metadata frontier is blocked or empty",
        ),
    ]
    frontiers = []
    for frontier_id, layer, relation, present_reason, blocked_reason in frontier_specs:
        members = [paper_key for paper_key, row_layer in layers.items() if row_layer == layer]
        relation_count = sum(1 for edge in edges if edge.get("relation") == relation)
        status = "present_metadata_only" if members or relation in edge_relations else "blocked_or_empty"
        reason = present_reason if status == "present_metadata_only" else blocked_reason
        row = {
            "frontier_id": frontier_id,
            "status": status,
            "evidence_class": "metadata_only_public",
            "member_count": len(members),
            "edge_count": relation_count,
            "members": members,
            "reason": reason,
            "claim_support_allowed": False,
        }
        if frontier_id in {"backward", "forward"}:
            row["seed_resolution_status"] = seed_resolution_status
        frontiers.append(row)
    return frontiers


def _build_from_visible_replay(
    *,
    topic: str,
    seeds: list[str],
    output_dir: Path,
    replay_task: Path | None,
    replay_responses_dir: Path | None,
) -> dict[str, Any]:
    if replay_task is None:
        return _blocked(
            "missing_replay_task",
            "offline-replay mode requires --replay-task",
            output_dir,
            next_required_actions=["provide --replay-task for a visible replay fixture and rerun survey build"],
        )
    if replay_responses_dir is None:
        return _blocked(
            "missing_replay_responses_dir",
            "offline-replay mode requires --replay-responses-dir",
            output_dir,
            next_required_actions=["provide --replay-responses-dir for visible replay responses and rerun survey build"],
        )

    replay_task = replay_task.resolve()
    replay_responses_dir = replay_responses_dir.resolve()
    task = load_json(replay_task)
    expected_topic = str(task.get("topic", "")).strip()
    if topic != expected_topic:
        return _blocked(
            "topic_replay_task_mismatch",
            "survey build topic must match the visible replay task topic in offline-replay mode",
            output_dir,
            next_required_actions=["align --topic with the replay task topic or choose the matching replay task"],
        )
    expected_seeds = [
        str(seed.get("identifier", "")).strip()
        for seed in task.get("seed_papers", [])
        if isinstance(seed, dict) and str(seed.get("identifier", "")).strip()
    ]
    if seeds != expected_seeds:
        return _blocked(
            "seed_replay_task_mismatch",
            "survey build seeds must match the visible replay task seed identifiers in offline-replay mode",
            output_dir,
            next_required_actions=["align repeated --seed values with the replay task seed identifiers"],
        )

    replay_packet = surveybench_visible_replay_packet(
        replay_task,
        responses_dir=replay_responses_dir,
    )
    if replay_packet["status"] != "ready":
        return {
            "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
            "status": "blocked",
            "blocked_reason": "replay_packet_incomplete",
            "message": "visible replay inputs are incomplete for offline-replay survey build",
            "output_dir": str(output_dir),
            "next_required_actions": [
                "repair missing visible replay response sources before rerunning offline-replay survey build",
            ],
            "missing_response_sources": replay_packet.get("missing_response_sources", []),
            "what_is_not_concluded": SURVEY_BUILD_BLOCKED_NONCLAIMS,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    packet = replay_packet["packet"]
    for name, payload in packet.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))
    packet_issues = _visible_replay_packet_issues(packet)
    status = "offline_replay_fixture_complete" if not packet_issues else "partial"
    survey_packet = _survey_packet_markdown_from_visible_packet(topic, packet, status=status, packet_issues=packet_issues)
    (output_dir / "survey_packet.md").write_text(survey_packet)
    manifest = _manifest_from_visible_packet(
        topic=topic,
        output_dir=output_dir,
        mode="offline-replay",
        task_id=str(task.get("task_id", "unknown")),
        status=status,
        packet_issues=packet_issues,
    )
    _write_workflow_state(output_dir, manifest)
    (output_dir / "build_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return {
        "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
        "status": status,
        "mode": "offline-replay",
        "topic": topic,
        "seed_count": len(seeds),
        "output_dir": str(output_dir),
        "artifact_paths": manifest["artifact_paths"],
        "workflow_state": manifest["workflow_state"],
        "workflow_state_path": manifest["artifact_paths"]["workflow_state.json"],
        "next_required_actions": manifest["next_required_actions"],
        "what_is_not_concluded": manifest["what_is_not_concluded"],
        "packet_issues": packet_issues,
        "replay_task": str(replay_task),
        "replay_responses_dir": str(replay_responses_dir),
    }


def _blocked(
    reason: str,
    message: str,
    output_dir: Path,
    *,
    next_required_actions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_BUILD_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "message": message,
        "output_dir": str(output_dir),
        "workflow_state": _workflow_state(
            state=f"blocked_{reason}",
            mode="blocked",
            ready_for_writer=False,
            ready_for_prose=False,
            safe_next_commands=next_required_actions or [],
            approval_required_for=[
                "live source/PDF/full-text download",
                "private or credentialed database use",
                "technical claim support",
            ],
            blocked_reasons=[message],
        ),
        "next_required_actions": next_required_actions or [],
        "what_is_not_concluded": SURVEY_BUILD_BLOCKED_NONCLAIMS,
    }


def _write_workflow_state(output_dir: Path, manifest: dict[str, Any]) -> None:
    workflow_state = manifest.get("workflow_state")
    if isinstance(workflow_state, dict):
        (output_dir / "workflow_state.json").write_text(json.dumps(workflow_state, indent=2, sort_keys=True))


def _seed_row(index: int, identifier: str) -> dict[str, Any]:
    return {
        "paper_key": f"seed_{index:03d}",
        "identifier": identifier,
        "roles": ["seed"],
        "source": "user_seed",
    }


def _candidate_ledger(topic: str, seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CANDIDATE_LEDGER_SCHEMA_VERSION,
        "status": "skeleton_pending_discovery",
        "topic": topic,
        "candidate_count": len(seed_rows),
        "included": [
            {
                "paper_key": row["paper_key"],
                "identifier": row["identifier"],
                "reason": "seed supplied by user",
                "source": "user_seed",
            }
            for row in seed_rows
        ],
        "excluded": [],
        "duplicates": [],
        "next_required_actions": [
            "resolve seed metadata",
            "run topic discovery",
            "deduplicate DOI/arXiv/title variants",
            "classify false positives with explicit exclusion reasons",
        ],
    }


def _citation_map(topic: str, seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CITATION_MAP_SCHEMA_VERSION,
        "status": "skeleton_pending_citation_expansion",
        "topic": topic,
        "seed_papers": [row["paper_key"] for row in seed_rows],
        "expansion_policy": {
            "backward_depth": 1,
            "forward_depth": 1,
            "adjacent_query_count": 3,
            "max_nodes": 40,
            "max_downloads": 20,
        },
        "nodes": [
            {
                "paper_key": row["paper_key"],
                "identifier": row["identifier"],
                "roles": ["seed"],
                "cluster": "pending_classification",
                "local_source_status": "pending_lookup",
                "download_status": "not_attempted",
                "review_status": "requires_human_review",
                "survey_relevance": "central_seed_pending_metadata",
            }
            for row in seed_rows
        ],
        "edges": [],
        "clusters": [],
        "survey_packet_paths": {
            "candidate_ledger": "candidate_ledger.json",
            "source_support": "source_support.json",
            "paper_classifications": "paper_classifications.json",
            "claim_support": "claim_support.json",
            "omission_risk": "omission_risk.json",
        },
        "next_required_actions": [
            "add backward lineage from seed references",
            "add forward citations from approved metadata source or replay fixture",
            "add adjacent clusters with relevance reasons",
        ],
    }


def _source_support(topic: str, seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_SOURCE_SUPPORT_SCHEMA_VERSION,
        "status": "skeleton_pending_source_lookup",
        "topic": topic,
        "papers": [
            {
                "paper_key": row["paper_key"],
                "identifier": row["identifier"],
                "source_status": "pending_lookup",
                "download_status": "not_attempted",
                "primary_source_type": "unknown",
                "checked_anchors": [],
                "allowed_claims": [],
                "forbidden_claims": [
                    "technical claims before inspecting source anchors",
                    "lineage or priority claims before citation-map expansion",
                ],
            }
            for row in seed_rows
        ],
        "next_required_actions": [
            "resolve full-text or source availability",
            "record unavailable or blocked sources explicitly",
            "extract checked sections, equations, algorithms, tables, and appendix anchors",
        ],
    }


def _paper_classifications(topic: str, seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CLASSIFICATION_SCHEMA_VERSION,
        "status": "skeleton_pending_classification",
        "topic": topic,
        "classifications": [
            {
                "paper_key": row["paper_key"],
                "identifier": row["identifier"],
                "labels": ["seed"],
                "classification_status": "requires_metadata_and_source_review",
            }
            for row in seed_rows
        ],
        "allowed_labels": SURVEY_CLASSIFICATION_ALLOWED_LABELS,
    }


def _claim_support(topic: str, seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_CLAIM_SUPPORT_SCHEMA_VERSION,
        "status": "skeleton_no_supported_claims_yet",
        "topic": topic,
        "claims": [],
        "claim_support_policy": {
            "technical_claims_require_checked_anchors": True,
            "metadata_only_support_allowed_for_technical_claims": False,
            "citation_counts_are_coverage_signals_only": True,
        },
        "seed_papers_pending_anchor_review": [row["paper_key"] for row in seed_rows],
    }


def _omission_risk(topic: str, seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_OMISSION_RISK_SCHEMA_VERSION,
        "status": "skeleton_pending_snowballing",
        "topic": topic,
        "risks": [
            {
                "risk_id": "backward_lineage_not_yet_built",
                "severity": "high",
                "risk": "Required predecessor/foundational papers are unknown until seed references are inspected.",
                "expected_action": "run backward snowballing and classify relevant references",
            },
            {
                "risk_id": "forward_frontier_not_yet_built",
                "severity": "high",
                "risk": "Major citing works and recent follow-ups are unknown until approved metadata or replay citations are inspected.",
                "expected_action": "run forward snowballing or record metadata blocker",
            },
            {
                "risk_id": "adjacent_clusters_not_yet_built",
                "severity": "medium",
                "risk": "Adjacent method clusters are unknown until topic expansion is run.",
                "expected_action": "query adjacent candidates and record inclusion/exclusion reasons",
            },
        ],
        "seed_papers": [row["paper_key"] for row in seed_rows],
    }


def _survey_packet_markdown(topic: str, seed_rows: list[dict[str, Any]]) -> str:
    seeds = "\n".join(f"- `{row['paper_key']}`: `{row['identifier']}`" for row in seed_rows)
    return f"""# Survey Evidence Packet

## Status

`SKELETON_PENDING_DISCOVERY_AND_SOURCE_REVIEW`

## Topic

{topic}

## Seed Papers

{seeds}

## Required Artifacts

- `candidate_ledger.json`
- `citation_map.json`
- `source_support.json`
- `paper_classifications.json`
- `claim_support.json`
- `omission_risk.json`

## Next Required Actions

1. Resolve seed metadata.
2. Build backward lineage from seed references.
3. Build forward citation frontier from an approved metadata source or replay fixture.
4. Build adjacent clusters with relevance reasons.
5. Record source/download status for every selected paper.
6. Add checked source anchors before supporting technical claims.
7. Record omission risks and non-claims before drafting survey prose.

## What Is Not Concluded

- This packet does not prove literature completeness.
- This packet does not support technical claims yet.
- This packet does not establish live web coverage, download reliability, product readiness, or scientific correctness.
"""


def _survey_packet_markdown_from_visible_packet(
    topic: str,
    packet: dict[str, Any],
    *,
    status: str,
    packet_issues: list[dict[str, str]],
) -> str:
    candidate_ledger = packet["candidate_ledger.json"]
    citation_map = packet["citation_map.json"]
    source_support = packet["source_support.json"]
    claim_support = packet["claim_support.json"]
    omission_risk = packet["omission_risk.json"]
    paper_classifications = packet["paper_classifications.json"]
    issue_lines = "\n".join(
        f"- `{row['file']}` / `{row['field']}`: {row['message']}" for row in packet_issues
    ) or "- none"
    classification_lines = _classification_markdown_lines(paper_classifications)
    claim_anchor_lines = _claim_anchor_markdown_lines(claim_support)
    blocked_claim_lines = _blocked_claim_markdown_lines(claim_support)
    source_gap_lines = _source_gap_markdown_lines(source_support)
    omission_lines = _omission_risk_markdown_lines(omission_risk)
    return f"""# Survey Evidence Packet

## Status

`{status.upper()}`

## Topic

{topic}

## Artifact Summary

- Included candidates: {len(candidate_ledger.get('included', []))}
- Citation-map nodes: {len(citation_map.get('nodes', []))}
- Citation-map edges: {len(citation_map.get('edges', []))}
- Citation clusters: {len(citation_map.get('clusters', []))}
- Source-support rows: {len(source_support.get('papers', []))}
- Classification rows: {len(paper_classifications.get('classifications', []))}
- Claim-support rows: {len(claim_support.get('claims', []))}
- Omission risks: {len(omission_risk.get('risks', []))}

## Paper Classifications

{classification_lines}

## Source Gaps And Forbidden Uses

{source_gap_lines}

## Claim Support Anchors

{claim_anchor_lines}

## Blocked Or Unsupported Claims

{blocked_claim_lines}

## Omission Risks

{omission_lines}

## Next Required Actions

1. Review the typed citation-map layers and source-status honesty.
2. Preserve omission-risk caveats and partial-frontier non-claims.
3. Draft survey prose only if the packet status is `READY_FOR_PROSE`.

## Packet Issues

{issue_lines}

## What Is Not Concluded

- This packet does not prove live web coverage.
- This packet does not prove literature completeness.
- This packet does not prove product readiness or scientific correctness.
"""


def _classification_markdown_lines(paper_classifications: dict[str, Any]) -> str:
    lines = []
    for row in paper_classifications.get("classifications", []):
        if not isinstance(row, dict):
            continue
        paper_key = str(row.get("paper_key", "unknown_paper"))
        labels = ", ".join(str(label) for label in row.get("labels", []) if label) or "unclassified"
        source_status = str(row.get("source_status", "unknown_source_status"))
        classification_status = str(row.get("classification_status", "unknown_classification_status"))
        lines.append(f"- `{paper_key}`: {labels}; source `{source_status}`; classification `{classification_status}`.")
    return "\n".join(lines) or "- none"


def _source_gap_markdown_lines(source_support: dict[str, Any]) -> str:
    lines = []
    for row in source_support.get("papers", []):
        if not isinstance(row, dict):
            continue
        source_status = str(row.get("source_status", ""))
        checked_anchors = row.get("checked_anchors")
        has_checked_anchor = isinstance(checked_anchors, list) and bool(checked_anchors)
        forbidden_claims = [str(claim) for claim in row.get("forbidden_claims", []) if claim]
        if source_status == "available_fixture" and has_checked_anchor and not forbidden_claims:
            continue
        paper_key = str(row.get("paper_key", "unknown_paper"))
        forbidden = "; ".join(forbidden_claims) if forbidden_claims else "technical claims remain blocked until source review"
        lines.append(f"- `{paper_key}`: source `{source_status}`; forbidden uses: {forbidden}.")
    return "\n".join(lines) or "- none"


def _claim_anchor_markdown_lines(claim_support: dict[str, Any]) -> str:
    lines = []
    for row in claim_support.get("claims", []):
        if not isinstance(row, dict) or row.get("status") != "supported":
            continue
        anchors = []
        for anchor in row.get("anchors", []):
            if not isinstance(anchor, dict):
                continue
            paper_key = str(anchor.get("paper_key", "unknown_paper"))
            kind = str(anchor.get("kind", "unknown_anchor"))
            label = str(anchor.get("label", "unknown_label"))
            anchors.append(f"{paper_key}:{kind}:{label}")
        anchor_text = ", ".join(f"`{anchor}`" for anchor in anchors) or "`MISSING_ANCHOR`"
        claim_id = str(row.get("claim_id", "unknown_claim"))
        lines.append(f"- `{claim_id}`: {anchor_text}.")
    return "\n".join(lines) or "- none"


def _blocked_claim_markdown_lines(claim_support: dict[str, Any]) -> str:
    lines = []
    for row in claim_support.get("claims", []):
        if not isinstance(row, dict) or row.get("status") == "supported":
            continue
        claim_id = str(row.get("claim_id", "unknown_claim"))
        support_class = str(row.get("support_class", "unknown_support_class"))
        claim = str(row.get("claim", "")).strip() or "claim text unavailable"
        lines.append(f"- `{claim_id}`: `{support_class}`; {claim}")
    return "\n".join(lines) or "- none"


def _omission_risk_markdown_lines(omission_risk: dict[str, Any]) -> str:
    lines = []
    for row in omission_risk.get("risks", []):
        if not isinstance(row, dict):
            continue
        paper_key = str(row.get("paper_key", "unknown_paper"))
        severity = str(row.get("severity", "unknown"))
        risk = str(row.get("risk", "")).strip() or "omission risk not specified"
        action = str(row.get("expected_action", "")).strip() or "record decision before prose drafting"
        lines.append(f"- `{paper_key}` ({severity}): {risk}; action: {action}.")
    return "\n".join(lines) or "- none"


def _visible_replay_packet_issues(packet: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required_nonempty = {
        "candidate_ledger.json": ("included",),
        "citation_map.json": ("nodes", "edges", "clusters"),
        "source_support.json": ("papers",),
        "paper_classifications.json": ("classifications",),
        "claim_support.json": ("claims",),
        "omission_risk.json": ("risks",),
    }
    for filename, fields in required_nonempty.items():
        payload = packet.get(filename, {})
        if not isinstance(payload, dict):
            issues.append({"file": filename, "field": "payload", "message": "payload missing or invalid"})
            continue
        for field in fields:
            value = payload.get(field)
            if not isinstance(value, list) or len(value) == 0:
                issues.append({"file": filename, "field": field, "message": "required list is empty"})
    claim_payload = packet.get("claim_support.json", {})
    if isinstance(claim_payload, dict):
        for index, row in enumerate(claim_payload.get("claims", [])):
            if not isinstance(row, dict) or row.get("status") != "supported":
                continue
            anchors = row.get("anchors")
            if not isinstance(anchors, list) or not anchors:
                issues.append(
                    {
                        "file": "claim_support.json",
                        "field": f"claims[{index}].anchors",
                        "message": "supported claim is missing visible anchors",
                    }
                )
            if row.get("support_class") == "unsupported":
                issues.append(
                    {
                        "file": "claim_support.json",
                        "field": f"claims[{index}].support_class",
                        "message": "supported claim cannot use unsupported support_class",
                    }
                )
    return issues


def _manifest(topic: str, seed_rows: list[dict[str, Any]], output_dir: Path, mode: str) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_BUILD_MANIFEST_SCHEMA_VERSION,
        "status": "created_skeleton",
        "mode": mode,
        "workflow_state": _workflow_state(
            state="skeleton_created",
            mode=mode,
            ready_for_writer=False,
            ready_for_prose=False,
            safe_next_commands=[
                "ra survey build --mode public-metadata --topic <topic> --seed <seed> --out <metadata-dir>",
                "ra survey build --mode offline-replay --topic <topic> --seed <seed> --replay-task <task.json> --replay-responses-dir <responses-dir> --out <packet-dir>",
            ],
            approval_required_for=[
                "live source/PDF/full-text download",
                "private or credentialed database use",
                "technical claim support",
            ],
            blocked_reasons=[
                "citation expansion has not run",
                "source/download status has not been collected",
                "claim-support anchors are absent",
            ],
        ),
        "mission": "topic + seed paper -> citation map -> survey-ready evidence packet",
        "topic": topic,
        "seed_papers": seed_rows,
        "artifact_paths": {name: str(output_dir / name) for name in PACKET_FILES},
        "mission_control_path": "docs/plans/literature_survey_automation_mission_control_2026-07-06.md",
        "milestones_path": "docs/plans/literature_survey_automation_milestones.json",
        "next_required_actions": [
            "wire offline replay evidence into this command",
            "implement citation-map builder",
            "implement source/download status collector",
            "implement survey-ready packet composer",
            "validate command output with SurveyBench",
        ],
        "forbidden_claims": [
            "do not claim full literature coverage from skeleton output",
            "do not claim technical source support without checked anchors",
            "do not claim live web or download robustness from offline skeleton output",
        ],
        "what_is_not_concluded": [
            "backward lineage completeness",
            "forward citation coverage",
            "adjacent cluster coverage",
            "source availability",
            "claim support",
            "survey prose quality",
            "scientific correctness",
            "product readiness",
        ],
    }


def _manifest_from_visible_packet(
    *,
    topic: str,
    output_dir: Path,
    mode: str,
    task_id: str,
    status: str,
    packet_issues: list[dict[str, str]],
) -> dict[str, Any]:
    fixture_complete = status == "offline_replay_fixture_complete"
    return {
        "schema_version": SURVEY_BUILD_MANIFEST_SCHEMA_VERSION,
        "status": status,
        "mode": mode,
        "workflow_state": _workflow_state(
            state="offline_replay_diagnostic_complete" if fixture_complete else "offline_replay_partial",
            mode=mode,
            ready_for_writer=False,
            ready_for_prose=False,
            safe_next_commands=(
                [
                    "initialize or resume a canonical mission-selected artifact set from the approved local workflow",
                    "import exact reviewed claim, source-safety, omission, and workflow decisions",
                    "run reviewed merge, reviewed final packet composition, and hostile review before any prose-readiness claim",
                ]
                if fixture_complete
                else [
                    "repair packet issues listed in build_manifest.json",
                    "rerun ra survey build --mode offline-replay after repairs",
                ]
            ),
            approval_required_for=[
                "live web/API/source/PDF/full-text actions outside the replay fixture",
                "product or science claims beyond fixture validation",
            ],
            blocked_reasons=[
                f"{issue.get('file')}: {issue.get('message')}"
                for issue in packet_issues
            ],
        ),
        "mission": "topic + seed paper -> citation map -> survey-ready evidence packet",
        "topic": topic,
        "replay_task_id": task_id,
        "artifact_paths": {name: str(output_dir / name) for name in PACKET_FILES},
        "mission_control_path": "docs/plans/literature_survey_automation_mission_control_2026-07-06.md",
        "milestones_path": "docs/plans/literature_survey_automation_milestones.json",
        "next_required_actions": (
            [
                "treat this packet as a diagnostic fixture only",
                "bind current evidence through the canonical selected-artifact and review queue",
                "complete reviewed merge, final packet composition, and hostile review before prose readiness",
            ]
            if fixture_complete
            else [
                "review typed citation-map layers and source-status honesty",
                "repair unsupported or missing claim-support rows",
                "repair packet issues before prose drafting",
                "validate offline-replay command output with SurveyBench",
            ]
        ),
        "forbidden_claims": [
            "do not claim ready-for-writer or ready-for-prose status from offline replay",
            "do not claim live web coverage from visible replay output",
            "do not claim scientific completeness from partial frontier or replay metadata",
        ],
        "what_is_not_concluded": [
            "ready-for-writer status",
            "ready-for-prose status",
            "live web coverage",
            "literature completeness",
            "scientific correctness",
            "product readiness",
        ],
        "packet_issues": packet_issues,
    }


def _workflow_state(
    *,
    state: str,
    mode: str,
    ready_for_writer: bool,
    ready_for_prose: bool,
    safe_next_commands: list[str],
    approval_required_for: list[str],
    blocked_reasons: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_WORKFLOW_STATE_SCHEMA_VERSION,
        "state": state,
        "mode": mode,
        "ready_for_writer": ready_for_writer,
        "ready_for_prose": ready_for_prose,
        "safe_next_commands": safe_next_commands,
        "approval_required_for": approval_required_for,
        "blocked_reasons": blocked_reasons,
        "forbidden_jumps": [
            "do not draft final prose from metadata-only or blocked packets",
            "do not fetch source/PDF/full text without an explicit approved intake plan",
            "do not treat metadata, citation counts, or source availability as technical claim support",
        ],
    }
