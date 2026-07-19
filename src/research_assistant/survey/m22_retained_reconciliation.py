"""Replay retained M20/M21 evidence into the canonical M22 review surface.

This module deliberately keeps the retained live evidence separate from the
ordinary fixture-only V2 source-intake authority.  It projects exact retained
rows into the queue/coverage interfaces while preserving machine-only status,
source gaps, and unavailable forward coverage as nonclaims.
"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.artifact_lineage import (
    ArtifactSetSnapshot,
    ArtifactStateManager,
    semantic_item,
    workflow_blocker_source_id,
)
from research_assistant.survey.evidence_semantics import EvidenceContext, SourceIdentity
from research_assistant.survey.mission_state import (
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from research_assistant.survey.review_decisions import workflow_blocker_resolution


RECONCILIATION_SCHEMA = "ra-survey-retained-evidence-reconciliation-v1"
RETAINED_SOURCE_STATUS_SCHEMA = "ra-survey-retained-source-intake-v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
M20_ROOT = REPOSITORY_ROOT / "docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000"
M21_ROOT = REPOSITORY_ROOT / "docs/validation/literature_survey_north_star_m21_seven_candidate_sources_2026-07-18"
M21_TRIAGE_ROOT = REPOSITORY_ROOT / "docs/validation/literature_survey_north_star_m21_candidate_context_triage_2026-07-18"
M21_SEED_ROOT = REPOSITORY_ROOT / "docs/validation/literature_survey_north_star_m21_retained_seed_anchors_v2_2026-07-18"
RETAINED_SEED_RECORD = Path(
    "docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/retained_evidence/sources/2201_12220v3.json"
)
PARSED_IDS = ("1506.03365", "1709.08894", "1805.07277", "1902.07197", "2003.06635", "2003.06788")
ALL_SOURCE_IDS = ("2201.12220v3", *PARSED_IDS)
SOURCE_TITLES = {
    "2201.12220v3": "Neural Optimal Transport",
    "1412.6980": "Adam: A Method for Stochastic Optimization",
    "1506.03365": "LSUN: Construction of a Large-Scale Image Dataset using Deep Learning with Humans in the Loop",
    "1709.08894": "On the regularization of Wasserstein GANs",
    "1805.07277": "XOGAN: One-to-Many Unsupervised Image-to-Image Translation",
    "1902.07197": "2-Wasserstein Approximation via Restricted Convex Potentials with Application to Improved Training for GANs",
    "2003.06635": "Large-Scale Optimal Transport via Adversarial Training with Cycle-Consistency",
    "2003.06788": "GMM-UNIT: Unsupervised Multi-Domain and Multi-Modal Image-to-Image Translation via Attribute Gaussian Mixture Modeling",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read(root: Path, relative: str) -> tuple[dict[str, Any], bytes]:
    path = root / relative
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("retained_input_invalid", f"retained input is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise MissionStateError("retained_input_invalid", f"retained input is not an object: {path}")
    return value, raw


def _sha(path: Path) -> str:
    return sha256_file(path)


def _retained_paths(repository_root: Path | None = None) -> dict[str, Path]:
    root = REPOSITORY_ROOT if repository_root is None else repository_root.resolve(strict=True)
    m20_root = root / "docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000"
    m21_root = root / "docs/validation/literature_survey_north_star_m21_seven_candidate_sources_2026-07-18"
    m21_triage_root = root / "docs/validation/literature_survey_north_star_m21_candidate_context_triage_2026-07-18"
    m21_seed_root = root / "docs/validation/literature_survey_north_star_m21_retained_seed_anchors_v2_2026-07-18"
    return {
        "m20_candidates": m20_root / "candidate_classifications.json",
        "m20_backward": m20_root / "backward_snowball.json",
        "m20_forward": m20_root / "forward_snowball.json",
        "m20_omissions": m20_root / "omitted_paper_risks.json",
        "m20_metadata": m20_root / "citation_venue_metadata.json",
        "m20_claims": m20_root / "claim_support.json",
        "m21_status": m21_root / "source_status.json",
        "m21_selection": m21_triage_root / "primary_source_selection.json",
        "m21_identifier_free": m21_triage_root / "identifier_free_risk.json",
        "m21_seed_anchors": m21_seed_root / "source_anchor_inventory.json",
    }


def _retained_input_hashes(repository_root: Path | None = None) -> dict[str, str]:
    return {
        name: _sha(path)
        for name, path in sorted(_retained_paths(repository_root).items())
    }


def _anchor_rows() -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    seed, _ = _read(M21_SEED_ROOT, "source_anchor_inventory.json")
    rows["2201.12220v3"] = [dict(row) for row in seed.get("anchors") or []]
    for arxiv_id in PARSED_IDS:
        payload, _ = _read(M21_ROOT, f"candidates/{arxiv_id.replace('.', '_')}/anchor_candidates.json")
        rows[arxiv_id] = [dict(row) for row in payload.get("anchors") or []]
    return rows


def _source_record_path(mission_root: Path, arxiv_id: str) -> tuple[Path, str]:
    if arxiv_id == "2201.12220v3":
        source = REPOSITORY_ROOT / RETAINED_SEED_RECORD
        return source, RETAINED_SEED_RECORD.as_posix()
    source = M21_ROOT / f"candidates/{arxiv_id.replace('.', '_')}/structured_source.json"
    return source, source.relative_to(REPOSITORY_ROOT).as_posix()


def _source_paper_id(arxiv_id: str) -> str:
    return "paper_arxiv_2201_1a5af737" if arxiv_id == "2201.12220v3" else f"candidate_arxiv_{arxiv_id.replace('.', '_')}"


def _normalized_source_record(
    mission_root: Path,
    arxiv_id: str,
    *,
    source_path: Path,
    original_record_path: str,
) -> dict[str, Any]:
    if arxiv_id == "2201.12220v3":
        payload, _ = _read(REPOSITORY_ROOT, original_record_path)
        return {
            "schema_version": "ra-survey-retained-source-record-v1",
            "canonical_identifier": f"arxiv:{arxiv_id}",
            "source_paper_id": _source_paper_id(arxiv_id),
            "title": SOURCE_TITLES[arxiv_id],
            "source_type": payload.get("source_type"),
            "status": payload.get("status"),
            "source_package_sha256": payload.get("source_package_sha256"),
            "original_record_sha256": _sha(source_path),
            "original_record_path": original_record_path,
            "technical_claim_support": "not_supported_until_claim_mapping_review",
        }
    payload, _ = _read(M21_ROOT, f"candidates/{arxiv_id.replace('.', '_')}/structured_source.json")
    return {
        "schema_version": "ra-survey-retained-source-record-v1",
        "canonical_identifier": f"arxiv:{arxiv_id}",
        "source_paper_id": _source_paper_id(arxiv_id),
        "title": SOURCE_TITLES[arxiv_id],
        "source_type": payload.get("source_type"),
        "status": payload.get("status"),
        "source_package_sha256": payload.get("source_package_sha256"),
        "original_record_sha256": _sha(source_path),
        "original_record_path": original_record_path,
        "technical_claim_support": "not_supported_until_claim_mapping_review",
    }


def _ensure_mission_snapshot(selected: ArtifactSetSnapshot) -> Any:
    from research_assistant.survey.mission_state import validate_generation_binding_readonly, MissionSnapshot

    binding = validate_generation_binding_readonly(
        output_dir=selected.mission_root,
        mission_id=selected.manifest["mission_id"],
        mission_fingerprint=selected.manifest["mission_fingerprint"],
        generation_id=selected.manifest["mission_anchor_generation_id"],
    )
    return MissionSnapshot(
        contract=binding["mission_contract"],
        mission_control=binding["mission_control"],
        next_action=binding["next_action"],
        current_pointer={"generation_id": binding["current_generation_id"]},
        recovery={"state": "read_only", "orphans": []},
    )


def compose_retained_packet_inputs(*, output_dir: Path) -> dict[str, Any]:
    """Create mission-local normalized records and canonical packet inputs."""
    output_dir = output_dir.absolute()
    paths = _retained_paths()
    candidates, _ = _read(M20_ROOT, "candidate_classifications.json")
    backward, _ = _read(M20_ROOT, "backward_snowball.json")
    status, _ = _read(M21_ROOT, "source_status.json")
    selection, _ = _read(M21_TRIAGE_ROOT, "primary_source_selection.json")
    identifier_free, _ = _read(M21_TRIAGE_ROOT, "identifier_free_risk.json")
    seed_anchors, _ = _read(M21_SEED_ROOT, "source_anchor_inventory.json")
    if candidates.get("candidate_count") != 62 or len(candidates.get("rows") or []) != 62:
        raise MissionStateError("retained_candidate_accounting_mismatch", "M20 candidate accounting is not exactly 62")
    if identifier_free.get("identifier_free_bibliography_units") != 195:
        raise MissionStateError("retained_identifier_free_accounting_mismatch", "identifier-free accounting is not exactly 195")
    nominated = [str(value) for value in selection.get("nominated_candidate_ids") or []]
    nominated_arxiv_ids = [value.removeprefix("arxiv:") for value in nominated]
    if nominated_arxiv_ids != list(status_row["arxiv_id"] for status_row in status.get("rows") or []):
        raise MissionStateError("retained_source_selection_mismatch", "M21 nominations and source outcomes differ")
    status_rows = {row["arxiv_id"]: row for row in status.get("rows") or []}
    anchors = _anchor_rows()
    if len(seed_anchors.get("anchors") or []) != 53 or sum(len(rows) for rows in anchors.values()) != 341:
        raise MissionStateError("retained_anchor_accounting_mismatch", "retained anchors are not exactly 341")
    normalized_anchors: dict[str, list[dict[str, Any]]] = {}
    for arxiv_id, rows in anchors.items():
        normalized_anchors[arxiv_id] = [
            {
                **{key: value for key, value in row.items() if key not in {"anchor_id", "source_record_path"}},
                "anchor_id": f"retained:{arxiv_id}:{index:04d}",
                "original_anchor_id": row["anchor_id"],
                "paper_id": _source_paper_id(arxiv_id),
                "canonical_identifier": f"arxiv:{arxiv_id}",
                "review_status": "machine_extracted_requires_human_or_model_review",
                "claim_support_status": "anchor_available_claim_not_mapped",
            }
            for index, row in enumerate(rows, start=1)
        ]
    source_rows: list[dict[str, Any]] = []
    for arxiv_id in ALL_SOURCE_IDS:
        if arxiv_id != "2201.12220v3" and status_rows[arxiv_id]["outcome"] != "accepted_and_parsed":
            raise MissionStateError("retained_source_outcome_mismatch", f"unexpected parsed outcome for {arxiv_id}")
        source_path, original_record_path = _source_record_path(output_dir, arxiv_id)
        normalized = _normalized_source_record(
            output_dir,
            arxiv_id,
            source_path=source_path,
            original_record_path=original_record_path,
        )
        normalized["anchor_ids"] = [row["anchor_id"] for row in normalized_anchors[arxiv_id]]
        normalized["anchor_count"] = len(normalized_anchors[arxiv_id])
        source_rows.append(normalized)
    source_dir = output_dir / "retained_evidence" / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_files: dict[str, Path] = {}
    for row in source_rows:
        path = source_dir / f"{row['canonical_identifier'].split(':', 1)[1].replace('.', '_')}.json"
        path.write_bytes(canonical_json_bytes(row))
        source_files[row["canonical_identifier"]] = path
    anchor_inventory = {
        "schema_version": "ra-survey-retained-anchor-inventory-v1",
        "status": "machine_extracted_requires_human_review",
        "paper_ids": [_source_paper_id(value) for value in ALL_SOURCE_IDS],
        "anchor_count": 341,
        "anchors": sorted(
            [
                {
                    **row,
                    "source_record_path": str(source_files[f"arxiv:{arxiv_id}"].relative_to(output_dir)),
                }
                for arxiv_id, rows in normalized_anchors.items()
                for row in rows
            ],
            key=lambda row: (row["paper_id"], row["anchor_id"], row.get("line", -1)),
        ),
        "what_is_not_concluded": ["technical claim support", "source safety", "literature completeness", "scientific correctness"],
    }
    (output_dir / "retained_evidence" / "anchor_inventory.json").write_bytes(canonical_json_bytes(anchor_inventory))
    candidate_rows = candidates.get("rows") or []
    candidate_ledger = {
        "schema_version": "ra-survey-retained-candidate-ledger-v1",
        "status": "retained_candidate_universe",
        "seed": "arxiv:2201.12220v3",
        "candidate_count": 62,
        "identifier_bearing_count": 62,
        "identifier_free_count": 195,
        "included": sorted(
            [
                {
                    "candidate_id": row.get("candidate_id"),
                    "identifiers": row.get("identifiers") or [],
                    "title": row.get("title"),
                    "scholarly_classification": row.get("scholarly_classification"),
                    "support_status": row.get("support_status"),
                    "nomination_status": "NOMINATED_FOR_PRIMARY_SOURCE_INSPECTION" if row.get("candidate_id") in nominated else "DEFERRED_RETAINED_AS_OMISSION_RISK",
                    "technical_claim_support": "not_supported",
                }
                for row in candidate_rows
            ],
            key=lambda row: str(row["candidate_id"]),
        ),
        "what_is_not_concluded": ["candidate relevance", "scholarly classification", "literature completeness", "scientific correctness"],
    }
    citation_map = {
        "schema_version": "ra-survey-retained-citation-map-v1",
        "status": "backward_reference_candidates_retained",
        "seed": "arxiv:2201.12220v3",
        "nodes": candidate_ledger["included"],
        "edges": [],
        "forward_coverage": {"status": "unavailable_out_of_scope", "blocking": False, "rows": []},
        "backward_coverage": backward,
        "what_is_not_concluded": ["citation completeness", "candidate relevance", "scientific correctness"],
    }
    classifications = {
        "schema_version": "ra-survey-retained-paper-classifications-v1",
        "reconciliation_schema_version": RECONCILIATION_SCHEMA,
        "status": "not_checked",
        "classifications": [
            {"canonical_identifier": row["canonical_identifier"], "paper_id": row["source_paper_id"], "classification": "NOT_CHECKED", "title": row["title"]}
            for row in source_rows
        ],
        "candidate_classifications": candidate_ledger["included"],
        "what_is_not_concluded": ["scholarly classification", "scientific correctness"],
    }
    omission_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        candidate_id = str(row["candidate_id"])
        if candidate_id in nominated:
            continue
        omission_rows.append({
            "risk_id": f"candidate:{candidate_id}",
            "severity": "high",
            "reason": "retained M20 identifier-bearing candidate not nominated in bounded M21 source campaign",
            "next_action": "human reviewer decides inspect, defer, or omit with reason",
            "machine_disposition": "blocked_source_or_frontier",
            "risk_source_type": "retained_candidate",
            "risk_source_id": candidate_id,
            "source_artifact_sha256": _sha(paths["m20_candidates"]),
        })
    omission_rows.extend([
        {
            "risk_id": "identifier_free:195",
            "severity": "high",
            "reason": "195 identifier-free bibliography units were not individually recovered",
            "next_action": "human reviewer records whether to expand source parsing or retain the bounded omission",
            "machine_disposition": "blocked_source_or_frontier",
            "risk_source_type": "identifier_free_aggregate",
            "risk_source_id": "identifier_free_units:195",
            "source_artifact_sha256": _sha(paths["m21_identifier_free"]),
            "unit_count": 195,
        },
        {
            "risk_id": "source_parse_gap:1412.6980",
            "severity": "high",
            "reason": "retained arXiv source is a 298-byte includepdf wrapper; PDF fallback is out of scope",
            "next_action": "human reviewer records blocked source-format outcome",
            "machine_disposition": "blocked_source_or_frontier",
            "risk_source_type": "retained_source_outcome",
            "risk_source_id": "1412.6980",
            "source_artifact_sha256": str(status_rows["1412.6980"]["source_sha256"]),
        },
        {
            "risk_id": "forward_coverage:unavailable_out_of_scope",
            "severity": "high",
            "reason": "forward-citation coverage is unavailable and permanently out of scope",
            "next_action": "record the nonblocking limitation; do not interpret as zero citations",
            "machine_disposition": "blocked_source_or_frontier",
            "risk_source_type": "forward_frontier",
            "risk_source_id": "forward_citation_coverage",
            "source_artifact_sha256": _sha(paths["m20_forward"]),
        },
    ])
    omitted = {
        "schema_version": "ra-survey-omitted-paper-risks-v2",
        "reconciliation_schema_version": RECONCILIATION_SCHEMA,
        "status": "omission_risks_visible",
        "topic": "Neural Optimal Transport",
        "risk_count": len(omission_rows),
        "risks": sorted(omission_rows, key=lambda row: row["risk_id"]),
        "risk_reconciliation": {"candidate_count": 62, "identifier_free_units": 195, "nominated_count": 7, "parsed_source_count": 7, "anchor_count": 341},
        "review_policy": {"complete_selected_decisions_required": True, "omission_visibility_is_not_literature_completeness": True, "reviewed_closure_is_current_scope_only": True},
        "what_is_not_concluded": ["literature completeness", "omission correctness", "zero forward citations"],
    }
    claim_support = {
        "schema_version": "ra-survey-retained-claim-support-v1",
        "status": "no_supported_claims",
        "claim_candidates": [
            {
                "claim_id": f"paper:{row['source_paper_id']}",
                "paper_ids": [row["source_paper_id"]],
                "anchor_ids": row["anchor_ids"],
                "anchor_title": row["title"],
                "anchor_role": "machine_extracted_source_anchor",
                "status": "anchor_available_claim_not_mapped",
                "support_class": "anchor_candidate_not_support",
                "next_action": "human reviewer maps or rejects a precise technical claim",
            }
            for row in source_rows
        ],
        "claims": [],
        "what_is_not_concluded": ["technical claim support", "scientific correctness"],
    }
    source_safety = {
        "schema_version": "ra-survey-retained-source-safety-v1",
        "status": "not_checked",
        "rows": [
            {
                "paper_id": row["source_paper_id"],
                "arxiv_id": row["canonical_identifier"].split(":", 1)[1],
                "retraction_or_version_status": "NOT_CHECKED",
                "original_status": row["status"],
                "next_action": "human reviewer performs bounded status/version checks",
            }
            for row in source_rows
        ],
        "what_is_not_concluded": ["complete retraction safety", "version correctness", "scientific correctness"],
    }
    build_manifest = {
        "schema_version": "ra-survey-retained-reconciliation-manifest-v1",
        "reconciliation_schema_version": RECONCILIATION_SCHEMA,
        "status": "replayed_retained_evidence",
        "input_files": [
            {"name": name, "path": str(path), "sha256": _sha(path), "size_bytes": path.stat().st_size}
            for name, path in sorted(paths.items())
        ],
        "normalized_artifacts": [
            {
                "path": str(path.relative_to(output_dir)),
                "sha256": _sha(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted([*source_files.values(), output_dir / "retained_evidence" / "anchor_inventory.json"])
        ],
        "accounting": {"m20_identifier_bearing": 62, "m20_identifier_free": 195, "m21_nominated": 7, "parsed_sources": 7, "parse_gap_sources": 1, "machine_anchors": 341, "supported_claims": 0},
        "forward_coverage": {"status": "unavailable_out_of_scope", "blocking": False},
        "nonclaims": ["human review", "claim truth", "source safety", "literature completeness", "mission success"],
    }
    packet = {
        "candidate_ledger.json": candidate_ledger,
        "citation_map.json": citation_map,
        "paper_classifications.json": classifications,
        "omission_risk.json": omitted,
        "claim_support.json": claim_support,
        "source_safety_status.json": source_safety,
        "build_manifest.json": build_manifest,
    }
    packet_dir = output_dir / "packet"
    packet_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in packet.items():
        (packet_dir / name).write_bytes(canonical_json_bytes(payload))
    (output_dir / "retained_evidence" / "reconciliation_manifest.json").write_bytes(
        canonical_json_bytes(build_manifest)
    )
    coverage = {
        "backward_snowball.json": {
            "schema_version": "ra-survey-backward-snowball-v2",
            "reconciliation_schema_version": RECONCILIATION_SCHEMA,
            "status": "retained_backward_reference_candidates",
            "topic": "Neural Optimal Transport",
            "retained_input_hashes": _retained_input_hashes(),
            "candidate_ids": sorted(row["candidate_id"] for row in candidate_ledger["included"]),
            "observations": [],
            "attempts": [],
            "what_is_not_concluded": ["candidate relevance", "literature completeness", "scientific correctness"],
        },
        "forward_snowball.json": {
            "schema_version": "ra-survey-forward-snowball-v2",
            "reconciliation_schema_version": RECONCILIATION_SCHEMA,
            "status": "unavailable_out_of_scope",
            "blocking": False,
            "reason": "forward-citation coverage is unavailable and permanently out of scope",
            "retained_input_hashes": _retained_input_hashes(),
            "observations": [],
            "attempts": [],
            "what_is_not_concluded": ["zero forward citations", "citation completeness", "literature completeness"],
        },
        "omitted_paper_risks.json": {**omitted, "retained_input_hashes": _retained_input_hashes()},
        "paper_classifications.json": {**classifications, "retained_input_hashes": _retained_input_hashes()},
        "citation_venue_metadata.json": {
            "schema_version": "ra-survey-citation-venue-metadata-v1",
            "reconciliation_schema_version": RECONCILIATION_SCHEMA,
            "status": "unavailable_out_of_scope",
            "retained_input_hashes": _retained_input_hashes(),
            "rows": [],
            "what_is_not_concluded": ["citation counts", "venue ranking", "literature completeness"],
        },
    }
    return {"packet_dir": packet_dir, "packet": packet, "coverage": coverage, "manifest": build_manifest}


def compose_retained_production_mission(
    *,
    output_dir: Path,
    now: Callable[[], str] = _utc_now,
    mission_nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
    mission_id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
    artifact_nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
) -> ArtifactSetSnapshot:
    """Compose and select one production review queue without external actions."""
    output_dir = output_dir.absolute()
    if output_dir.exists() or output_dir.is_symlink():
        raise MissionStateError("output_exists", "retained production mission output already exists")
    output_dir.mkdir(parents=True)
    manager = MissionStateManager(
        output_dir=output_dir,
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220v3"],
        confirm_public_discovery=False,
        resume=False,
        force=False,
        now=now,
        nonce_factory=mission_nonce_factory,
        mission_id_factory=mission_id_factory,
    )
    manager.begin()
    timestamp = now()
    committed = manager.commit(
        {
            "status": "blocked_at_genuine_human_review",
            "created_at": timestamp,
            "updated_at": timestamp,
            "topic": "Neural Optimal Transport",
            "seeds": ["arxiv:2201.12220v3"],
            "output_dir": str(output_dir),
        },
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "human_review_required",
            "mission_status": "blocked_at_genuine_human_review",
            "action_id": "complete_retained_evidence_human_review",
        },
    )
    composed = compose_retained_packet_inputs(output_dir=output_dir)
    original_status, _ = _read(M21_ROOT, "source_status.json")
    original_rows = {row["arxiv_id"]: row for row in original_status.get("rows") or []}
    source_rows = [
        {
            "candidate_index": 0,
            "candidate_id": "2201.12220v3",
            "identifier": "arxiv:2201.12220v3",
            "paper_id": _source_paper_id("2201.12220v3"),
            "outcome_status": "available",
            "code": None,
            "source_record_path": str(output_dir / "retained_evidence/sources/2201_12220v3.json"),
            "source_record_sha256": _sha(output_dir / "retained_evidence/sources/2201_12220v3.json"),
            "source_record_size_bytes": (output_dir / "retained_evidence/sources/2201_12220v3.json").stat().st_size,
            "provider": "retained_arxiv_source_campaign",
            "final_url": "https://arxiv.org/src/2201.12220v3",
            "title": SOURCE_TITLES["2201.12220v3"],
            "anchor_count": 53,
            "technical_claim_support": "not_supported",
        }
    ]
    for index, arxiv_id in enumerate(("1412.6980", *PARSED_IDS), start=1):
        original = original_rows[arxiv_id]
        parsed = arxiv_id in PARSED_IDS
        normalized_path = output_dir / "retained_evidence/sources" / f"{arxiv_id.replace('.', '_')}.json"
        source_rows.append({
            "candidate_index": index,
            "candidate_id": arxiv_id,
            "identifier": f"arxiv:{arxiv_id}",
            "paper_id": _source_paper_id(arxiv_id),
            "outcome_status": "available" if parsed else "unavailable",
            "code": None if parsed else "source_format_parse_gap",
            "source_record_path": str(normalized_path) if parsed else None,
            "source_record_sha256": _sha(normalized_path) if parsed else original["source_sha256"],
            "source_record_size_bytes": normalized_path.stat().st_size if parsed else original["source_bytes"],
            "provider": "retained_arxiv_source_campaign",
            "final_url": f"https://arxiv.org/src/{arxiv_id}",
            "title": SOURCE_TITLES[arxiv_id],
            "anchor_count": original["anchor_count"] if parsed else 0,
            "technical_claim_support": "not_supported",
        })
    source_intake = output_dir / "source_intake"
    source_intake.mkdir()
    ledger_path = source_intake / "source_intake_outcomes.json"
    ledger = {
        "schema_version": "ra-survey-retained-source-outcomes-v1",
        "status": "reconciled",
        "rows": source_rows,
        "counts": {"available": 7, "unavailable": 1, "total": 8},
        "what_is_not_concluded": ["source safety", "technical claim support", "literature completeness"],
    }
    ledger_path.write_bytes(canonical_json_bytes(ledger))
    status_payload = {
        "schema_version": RETAINED_SOURCE_STATUS_SCHEMA,
        "reconciliation_schema_version": RECONCILIATION_SCHEMA,
        "status": "retained_source_outcomes_reconciled",
        "outcome_ledger_path": str(ledger_path),
        "outcome_ledger_sha256": _sha(ledger_path),
        "rows": source_rows,
        "counts": ledger["counts"],
        "authoritative_correction": {
            "arxiv_id": "1412.6980",
            "outcome": "SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE",
            "original_status_sha256": _sha(M21_ROOT / "source_status.json"),
            "correction_record_sha256": _sha(REPOSITORY_ROOT / "docs/plans/literature_survey_north_star_m21_source_campaign_reconciliation_2026-07-18.md"),
        },
        "what_is_not_concluded": ["source safety", "technical claim support", "literature completeness", "scientific correctness"],
    }
    (source_intake / "phase4_source_intake_status.json").write_bytes(canonical_json_bytes(status_payload))
    queue = build_retained_review_queue(packet=composed["packet"], coverage=composed["coverage"])
    return ArtifactStateManager(
        mission_root=output_dir,
        mission_id=committed.contract["mission_id"],
        mission_fingerprint=committed.contract["mission_fingerprint"],
        mission_anchor_generation_id=committed.current_pointer["generation_id"],
        nonce_factory=artifact_nonce_factory,
    ).compose_and_select(
        packet_dir=composed["packet_dir"],
        coverage_payloads=composed["coverage"],
        review_queue_payload=queue,
    )


def build_retained_review_queue(*, packet: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    claim_rows = packet["claim_support.json"]["claim_candidates"]
    for row in claim_rows:
        items.append(semantic_item(
            queue_type="claim_candidate",
            source_id=row["claim_id"],
            semantic_fields={
                "priority": "high" if row["paper_ids"] == ["paper_arxiv_2201_1a5af737"] else "medium",
                "status": "review_required",
                "claim_support_allowed": False,
                "paper_ids": row["paper_ids"],
                "anchor_ids": row["anchor_ids"],
                "title_or_anchor": row["anchor_title"],
                "action_required": row["next_action"],
                "non_promotion_reason": "machine anchors are review pointers, not supported claims",
            },
        ))
    for row in packet["source_safety_status.json"]["rows"]:
        items.append(semantic_item(
            queue_type="source_safety",
            source_id=row["paper_id"],
            semantic_fields={
                "priority": "high",
                "status": "blocked_pending_evidence",
                "paper_id": row["paper_id"],
                "arxiv_id": row["arxiv_id"],
                "input_status": row["original_status"],
                "safety_checked_clear": False,
                "claim_support_allowed": False,
                "action_required": row["next_action"],
                "non_promotion_reason": "source availability and parser status are not safety checks",
            },
        ))
    for row in coverage["omitted_paper_risks.json"]["risks"]:
        items.append(semantic_item(
            queue_type="omission_risk",
            source_id=row["risk_id"],
            semantic_fields={
                "priority": row["severity"],
                "status": "blocked_pending_evidence",
                "risk_id": row["risk_id"],
                "severity": row["severity"],
                "reason": row["reason"],
                "action_required": row["next_action"],
                "coverage_schema_version": "ra-survey-omitted-paper-risks-v2",
                "machine_disposition": row["machine_disposition"],
                "risk_source_type": row["risk_source_type"],
                "risk_source_id": row["risk_source_id"],
                "source_artifact_sha256": row["source_artifact_sha256"],
                "literature_completeness_allowed": False,
                **({"unit_count": row["unit_count"]} if "unit_count" in row else {}),
                "non_promotion_reason": "omission visibility is not literature completeness",
            },
        ))
    workflow_reason = "no reviewed supported technical claim rows are present"
    workflow_class, workflow_type = workflow_blocker_resolution(workflow_reason)
    claim_ids = sorted(item["item_id"] for item in items if item["queue_type"] == "claim_candidate")
    items.append(semantic_item(
        queue_type="workflow_blocker",
        source_id=workflow_blocker_source_id(workflow_reason),
        semantic_fields={
            "priority": "high",
            "status": "blocked_pending_evidence",
            "reason": workflow_reason,
            "resolution_class": workflow_class,
            "required_evidence_queue_type": workflow_type,
            "required_evidence_queue_item_ids": claim_ids,
            "ready_for_prose": False,
            "action_required": "clear the underlying blocker with explicit reviewed evidence",
            "non_promotion_reason": "queue creation cannot establish supported claims",
        },
    ))
    items.sort(key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]))
    return {
        "status": "review_required",
        "topic": "Neural Optimal Transport",
        "items": items,
        "allowed_item_statuses": ["review_required", "blocked_pending_evidence"],
        "forbidden_promotions": ["machine anchors are not supported claims", "source availability is not source safety", "omission visibility is not completeness"],
        "what_is_not_concluded": ["human review", "claim truth", "source safety", "literature completeness", "mission success"],
    }


def validate_retained_selected_coverage(
    *,
    mission_root: Path,
    mission_id: str,
    mission_fingerprint: str,
    mission_anchor_generation_id: str,
    coverage_payloads: dict[str, dict[str, Any]],
    repository_root: Path | None = None,
) -> None:
    if set(coverage_payloads) != {"backward_snowball.json", "forward_snowball.json", "omitted_paper_risks.json", "paper_classifications.json", "citation_venue_metadata.json"}:
        raise MissionStateError("invalid_retained_coverage", "retained coverage file set is incomplete")
    if any(payload.get("reconciliation_schema_version") != RECONCILIATION_SCHEMA for payload in coverage_payloads.values()):
        raise MissionStateError("invalid_retained_coverage", "retained coverage schema marker is missing")
    paths = _retained_paths(repository_root)
    expected_hashes = _retained_input_hashes(repository_root)
    if any(payload.get("retained_input_hashes") != expected_hashes for payload in coverage_payloads.values()):
        raise MissionStateError("retained_input_hash_mismatch", "retained coverage does not bind the current M20/M21 evidence")
    candidates, _ = _read(paths["m20_candidates"].parent, paths["m20_candidates"].name)
    selection, _ = _read(paths["m21_selection"].parent, paths["m21_selection"].name)
    candidate_ids = sorted(str(row["candidate_id"]) for row in candidates.get("rows") or [])
    if coverage_payloads["backward_snowball.json"].get("candidate_ids") != candidate_ids:
        raise MissionStateError("retained_candidate_replay_mismatch", "retained backward candidate identities differ")
    omitted = coverage_payloads["omitted_paper_risks.json"]
    if omitted.get("risk_reconciliation") != {"candidate_count": 62, "identifier_free_units": 195, "nominated_count": 7, "parsed_source_count": 7, "anchor_count": 341}:
        raise MissionStateError("retained_coverage_replay_mismatch", "retained accounting summary differs")
    forward = coverage_payloads["forward_snowball.json"]
    if forward.get("status") != "unavailable_out_of_scope" or forward.get("blocking") is not False:
        raise MissionStateError("retained_forward_coverage_mismatch", "forward coverage must remain unavailable and nonblocking")
    risk_ids = [row.get("risk_id") for row in omitted.get("risks") or []]
    nominated = set(selection.get("nominated_candidate_ids") or [])
    expected_risk_ids = sorted(
        [f"candidate:{candidate_id}" for candidate_id in candidate_ids if candidate_id not in nominated]
        + ["identifier_free:195", "source_parse_gap:1412.6980", "forward_coverage:unavailable_out_of_scope"]
    )
    if sorted(risk_ids) != expected_risk_ids or len(risk_ids) != len(set(risk_ids)):
        raise MissionStateError("retained_omission_identity_mismatch", "retained omission IDs are invalid")


def load_retained_evidence_context(*, selected: ArtifactSetSnapshot, queue: dict[str, Any], queue_raw: bytes) -> EvidenceContext:
    status_path = selected.mission_root / "source_intake" / "phase4_source_intake_status.json"
    status, status_raw = _read(selected.mission_root, "source_intake/phase4_source_intake_status.json")
    if status.get("schema_version") != RETAINED_SOURCE_STATUS_SCHEMA:
        raise MissionStateError("invalid_retained_source_status", "retained source status marker is missing")
    binding = _ensure_mission_snapshot(selected)
    source_dir = selected.mission_root / "retained_evidence" / "sources"
    inventory, _ = _read(selected.mission_root, "retained_evidence/anchor_inventory.json")
    if inventory.get("anchor_count") != 341 or len(inventory.get("anchors") or []) != 341:
        raise MissionStateError("retained_anchor_replay_mismatch", "retained anchor inventory is not exactly 341")
    source_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "source_safety"]
    source_identities: dict[str, SourceIdentity] = {}
    components: dict[str, dict[str, Any]] = {}
    for item in source_items:
        paper_id = item.get("paper_id")
        arxiv_id = item.get("arxiv_id")
        if not isinstance(paper_id, str) or not isinstance(arxiv_id, str):
            raise MissionStateError("retained_source_queue_join_failed", "retained source queue identity is incomplete")
        normalized_path = source_dir / f"{arxiv_id.replace('.', '_')}.json"
        raw = normalized_path.read_bytes()
        payload = json.loads(raw)
        if raw != canonical_json_bytes(payload) or payload.get("source_paper_id") != paper_id:
            raise MissionStateError("retained_source_record_invalid", "retained normalized source record is stale")
        canonical_identifier = f"arxiv:{arxiv_id}"
        queue_id = item["item_id"]
        identity = SourceIdentity(
            queue_item_id=queue_id,
            stable_metadata_paper_id=paper_id,
            source_paper_id=paper_id,
            canonical_identifier=canonical_identifier,
            aliases=[canonical_identifier],
            source_version=f"record-sha256:{sha256_bytes(raw)}",
            source_record_path=str(normalized_path.relative_to(selected.mission_root)),
            source_record_sha256=sha256_bytes(raw),
            source_record_size_bytes=len(raw),
            provider="retained_arxiv_source_campaign",
            final_url=f"https://arxiv.org/src/{arxiv_id}",
        )
        source_identities[queue_id] = identity
        components[paper_id] = {"paper_id": paper_id, "canonical_identifier": canonical_identifier, "aliases": [canonical_identifier], "component_status": "eligible"}
    outcomes = [dict(row) for row in status.get("rows") or []]
    if len(outcomes) != 8 or sum(row.get("outcome_status") == "available" for row in outcomes) != 7:
        raise MissionStateError("retained_source_outcome_mismatch", "retained source outcome accounting differs")
    validated_status = {"status": {**status, "outcome_ledger_path": str(status_path)}, "status_bytes": status_raw, "outcomes": outcomes, "project_root": selected.mission_root}
    return EvidenceContext(
        mission_root=selected.mission_root,
        review_queue_path=selected.review_queue_path,
        review_queue=queue,
        review_queue_sha256=sha256_bytes(queue_raw),
        selected_artifact_set=selected,
        mission_snapshot=binding,
        validated_source_intake=validated_status,
        identity_components=components,
        source_identities=source_identities,
        unavailable_outcomes=[row for row in outcomes if row["outcome_status"] == "unavailable"],
    )


def validate_retained_claim_anchors(*, context: EvidenceContext, paper_ids: list[str], anchor_ids: list[str]) -> None:
    """Validate claim pointers against the mission-local retained inventory."""
    inventory, _ = _read(context.mission_root, "retained_evidence/anchor_inventory.json")
    rows = inventory.get("anchors")
    if not isinstance(rows, list):
        raise MissionStateError("invalid_retained_anchor_inventory", "retained anchor inventory is not a list")
    by_pair = {(row.get("paper_id"), row.get("anchor_id")): row for row in rows if isinstance(row, dict)}
    if any(not any((paper_id, anchor_id) in by_pair for anchor_id in anchor_ids) for paper_id in paper_ids):
        raise MissionStateError("missing_current_claim_anchor", "each retained primary paper must own a declared anchor")
    if any(not any((paper_id, anchor_id) in by_pair for paper_id in paper_ids) for anchor_id in anchor_ids):
        raise MissionStateError("foreign_claim_anchor", "claim anchor does not belong to a declared retained paper")


__all__ = ["RECONCILIATION_SCHEMA", "RETAINED_SOURCE_STATUS_SCHEMA", "build_retained_review_queue", "compose_retained_packet_inputs", "compose_retained_production_mission", "load_retained_evidence_context", "validate_retained_claim_anchors", "validate_retained_selected_coverage"]
