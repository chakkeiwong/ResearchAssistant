from __future__ import annotations

from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest

from research_assistant.survey import build as survey_build
import research_assistant.survey.artifact_lineage as artifact_lineage
from research_assistant.survey.artifact_lineage import ArtifactStateManager
from research_assistant.survey.coverage_ledgers import load_v2_frontier_context
from research_assistant.survey.discovery_quality import evaluate_discovery_quality
from research_assistant.survey.frontier_expansion import (
    ATTEMPT_STATUSES,
    OBSERVATION_DISPOSITIONS,
    build_frontier_payloads,
    validate_attempt_cardinality,
    validate_observation_disposition,
)
from research_assistant.survey.omission_review import (
    OmissionDecisionSetSnapshot,
    OmissionDecisionStateManager,
    V2_OMISSION_TRANSITIONS,
    _validate_decision as validate_omission_decision,
    import_reviewed_omissions,
    resolve_current_reviewed_omissions,
)
from research_assistant.survey.claim_review import (
    SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
    SURVEY_CLAIM_REVIEW_V3_SCHEMA,
    import_reviewed_claims,
    resolve_current_reviewed_claims,
)
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.source_safety_review import (
    SOURCE_CHECKS,
    SOURCE_OBSERVATION_NONCLAIMS,
    SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
    SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
    import_reviewed_source_safety,
    preview_source_observation_binding,
    resolve_current_source_safety,
)
from research_assistant.survey.workflow_blocker_review import import_reviewed_workflow_blockers
from research_assistant.survey.reviewed_merge import (
    merge_reviewed_evidence,
    validate_reviewed_evidence_status,
)
from research_assistant.survey.reviewed_packet import (
    compose_reviewed_final_packet,
    validate_reviewed_final_packet,
)
from research_assistant.survey.hostile_review import (
    run_hostile_review_gate,
    validate_hostile_review_result,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.review_decisions import (
    REVIEW_DECISIONS_SCHEMA,
    load_selected_decision_context,
)
from research_assistant.survey.source_intake import (
    MissionSourceCapability,
    SourceCapabilityResult,
)


TOPIC = "Neural Optimal Transport for generative modeling and inference"
SEED = "openalex:w100"
ACCESS_TIME = "2026-07-12T00:00:00+00:00"


def _provider_row(source_id: str, *, query_kind: str) -> dict:
    return {
        "provider": "openalex",
        "query_kind": query_kind,
        "source_id": source_id,
        "citation_count": 10,
        "publication_date": "2024-01-01",
        "work_type": "article",
    }


def _record(
    key: str,
    title: str,
    openalex_id: str,
    *,
    roles: list[str],
    referenced_works: list[str] | None = None,
    seed_key: str | None = None,
    query_kind: str = "topic_search",
) -> dict:
    return {
        "record_key": key,
        "title": title,
        "authors": ["Ada Example"],
        "year": 2024,
        "doi": None,
        "arxiv_id": None,
        "openalex_id": openalex_id,
        "landing_page_url": f"https://openalex.org/{openalex_id}",
        "citation_count": 10,
        "providers": ["openalex"],
        "roles": roles,
        "provider_records": [_provider_row(openalex_id, query_kind=query_kind)],
        "referenced_works": referenced_works or [],
        "query_provenance": [{
            "provider": "openalex",
            "query_kind": query_kind,
            "normalized_seed_key": seed_key,
            "topic_query": query_kind == "topic_search",
        }],
    }


def _records() -> list[dict]:
    return [
        _record(
            "seed",
            "Neural Optimal Transport",
            "W100",
            roles=["seed"],
            referenced_works=["W200", "W300", "W999"],
            seed_key=SEED,
            query_kind="seed_resolution",
        ),
        _record(
            "direct",
            "Neural Optimal Transport Direct Method",
            "W200",
            roles=["direct_method", "backward_lineage_candidate"],
        ),
        _record(
            "adjacent",
            "Generative Optimal Transport Geometry",
            "W300",
            roles=["adjacent_method", "backward_lineage_candidate"],
        ),
        _record(
            "citing",
            "Recent Neural Optimal Transport Correction",
            "W400",
            roles=["major_citing_work"],
            referenced_works=["W100"],
        ),
        _record(
            "weak",
            "Neural Filtering Competitor",
            "W500",
            roles=["adjacent_method"],
            referenced_works=["W100"],
        ),
        _record(
            "noise",
            "Unrelated Quantum Chemistry",
            "W600",
            roles=["adjacent_method"],
            referenced_works=["W100"],
        ),
    ]


def _collection(records: list[dict]) -> dict:
    return {
        "status": "metadata_collected",
        "fetched_at": ACCESS_TIME,
        "records": records,
        "provider_statuses": [
            {
                "provider": "openalex",
                "query_kind": "seed_resolution",
                "normalized_seed_key": SEED,
                "topic_query": False,
                "query_cap": 5,
                "status": "available",
                "record_count": 1,
                "raw_response_saved": False,
            },
            {
                "provider": "openalex",
                "query_kind": "topic_search",
                "normalized_seed_key": None,
                "topic_query": True,
                "query_cap": 12,
                "status": "available",
                "record_count": len(records) - 1,
                "raw_response_saved": False,
            },
        ],
        "raw_response_policy": {
            "raw_responses_saved": False,
            "privacy_scan": "not_applicable_fixture_only",
            "reason": "Phase 8 deterministic fixture",
        },
    }


def _authority(tmp_path: Path, *, records: list[dict] | None = None, max_records: int = 25) -> dict:
    records = deepcopy(records or _records())
    quality = evaluate_discovery_quality(
        topic=TOPIC,
        seeds=[SEED],
        records=records,
        max_records=max_records,
    )
    assert quality["status"] == "eligible"
    artifacts = survey_build._compose_public_metadata_v2_artifacts(
        topic=TOPIC,
        output_dir=tmp_path / "public_metadata",
        quality=quality,
        collection=_collection(records),
        providers=["openalex"],
        max_records=max_records,
    )
    digests = {
        name: sha256_bytes(canonical_json_bytes(payload))
        for name, payload in artifacts.items()
        if isinstance(payload, dict)
    }
    metadata_root = (tmp_path / "public_metadata").absolute()
    artifact_rows = [
        {
            "name": name,
            "path": str(metadata_root / name),
            "sha256": digest,
            "size_bytes": len(canonical_json_bytes(artifacts[name])),
        }
        for name, digest in sorted(digests.items())
    ]
    metadata_authority = {
        "schema_version": "test-frontier-metadata-authority-v1",
        "artifact_rows": artifact_rows,
    }
    return {
        "topic": TOPIC,
        "metadata_root": metadata_root,
        "artifact_digests": digests,
        "metadata_authority_sha256": sha256_bytes(canonical_json_bytes(metadata_authority)),
        "metadata_artifact_rows": artifact_rows,
        "mission_id": "11111111-1111-4111-8111-111111111111",
        "mission_fingerprint": "1" * 64,
        "mission_anchor_generation_id": "g00000001-1111111111111111",
        "identity_resolution": artifacts["identity_resolution.json"],
        "relevance_ranking": artifacts["relevance_ranking.json"],
        "citation_map": artifacts["citation_map.json"],
        "metadata_provenance": artifacts["metadata_provenance.json"],
        "omission_risk": artifacts["omission_risk.json"],
    }


def _build(tmp_path: Path, *, records: list[dict] | None = None, max_records: int = 25) -> dict:
    return build_frontier_payloads(**_authority(tmp_path, records=records, max_records=max_records))


def _refresh_authority_artifact(authority: dict, name: str) -> None:
    payload = {
        "identity_resolution.json": authority["identity_resolution"],
        "relevance_ranking.json": authority["relevance_ranking"],
        "citation_map.json": authority["citation_map"],
        "metadata_provenance.json": authority["metadata_provenance"],
        "omission_risk.json": authority["omission_risk"],
    }[name]
    raw = canonical_json_bytes(payload)
    digest = sha256_bytes(raw)
    authority["artifact_digests"][name] = digest
    row = next(item for item in authority["metadata_artifact_rows"] if item["name"] == name)
    row["sha256"] = digest
    row["size_bytes"] = len(raw)
    authority["metadata_authority_sha256"] = sha256_bytes(
        canonical_json_bytes({
            "schema_version": "test-frontier-metadata-authority-v1",
            "artifact_rows": authority["metadata_artifact_rows"],
        })
    )


def _attempts(payloads: dict) -> list[dict]:
    return [
        *payloads["backward_snowball.json"]["attempts"],
        *payloads["forward_snowball.json"]["attempts"],
    ]


def _observations(payloads: dict) -> list[dict]:
    return [
        *payloads["backward_snowball.json"]["observations"],
        *payloads["forward_snowball.json"]["observations"],
    ]


def _mission_collection(records: list[dict]) -> dict:
    statuses = []
    for provider in ("arxiv", "openalex"):
        statuses.extend([
            {
                "provider": provider,
                "query_kind": "seed_resolution",
                "normalized_seed_key": SEED,
                "topic_query": False,
                "query_cap": 5,
                "status": "available",
                "record_count": sum(
                    provider in row["providers"]
                    and any(
                        value.get("provider") == provider
                        and value.get("query_kind") == "seed_resolution"
                        for value in row.get("query_provenance") or []
                    )
                    for row in records
                ),
                "raw_response_saved": False,
            },
            {
                "provider": provider,
                "query_kind": "topic_search",
                "normalized_seed_key": None,
                "topic_query": True,
                "query_cap": 12,
                "status": "available",
                "record_count": sum(
                    provider in row["providers"]
                    and any(
                        value.get("provider") == provider
                        and value.get("query_kind") == "topic_search"
                        for value in row.get("query_provenance") or []
                    )
                    for row in records
                ),
                "raw_response_saved": False,
            },
        ])
    return {
        "status": "metadata_collected",
        "fetched_at": ACCESS_TIME,
        "records": records,
        "provider_statuses": statuses,
        "raw_response_policy": {
            "raw_responses_saved": False,
            "privacy_scan": "not_applicable_raw_responses_not_saved",
            "reason": "fixture-only Phase 8 mission",
        },
    }


def _fixture_source(request) -> SourceCapabilityResult:
    final_url = f"https://api.openalex.org/works/{request.identifier.split(':', 1)[1].upper()}"
    record = {
        "paper_id": request.paper_id,
        "source_type": "publisher_xml",
        "status": "available",
        "primary_for_audit": True,
        "artifact_root": None,
        "original_source_path": None,
        "flattened_source_path": None,
        "sections": [{
            "level": 1,
            "command": "section",
            "title": "Method",
            "line": 1,
            "labels": ["sec:method"],
            "raw_latex": "Fixture-only structured source.",
        }],
        "equations": [],
        "theorem_like_blocks": [],
        "labels": [],
        "references": [],
        "citations": [],
        "bibliography": [],
        "macros": [],
        "provenance": {
            "identifier": request.identifier,
            "provider": "openalex",
            "final_url": final_url,
            "fixture_only": True,
        },
        "diagnostics": {"fixture_only": True, "section_count": 1},
        "limitations": [{
            "field": "source",
            "status": "fixture_only",
            "note": "No live source transport was run.",
        }],
    }
    return SourceCapabilityResult(
        candidate_id=request.candidate_id,
        identifier=request.identifier,
        outcome_status="available",
        code="available",
        provider="openalex",
        final_url=final_url,
        structured_record=record,
        byte_count=len(pretty_json_bytes(record)),
    )


def _canonical_v2_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    seed_referenced_works: list[str] | None = None,
    fixture_records: list[dict] | None = None,
    source_handler=None,
) -> tuple[Path, Path, dict]:
    mission = tmp_path / "mission"
    first = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    if fixture_records is None:
        seed_record = deepcopy(_records()[0])
        seed_record["referenced_works"] = list(seed_referenced_works or [])
        records = [seed_record]
    else:
        records = deepcopy(fixture_records)
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: _mission_collection(records),
    )
    built = survey_build.build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission / "public_metadata",
        mode="public-metadata",
        public_metadata_providers=["arxiv", "openalex"],
        max_records=25,
    )
    assert built["status"] == "metadata_only_packet", built
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata",
        lambda **_: (_ for _ in ()).throw(AssertionError("canonical Phase 8 replay called a provider")),
    )
    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(source_handler or _fixture_source),
    )
    assert result["local_supervisor"]["status"] == "terminal_blocked_human_review"
    queue_path = Path(result["review_queue_path"])
    return mission, queue_path, json_load(queue_path)


def _validated_frontier_input(mission: Path, queue: dict) -> dict:
    status_path = mission / "source_intake" / "phase4_source_intake_status.json"
    return {
        "status": json_load(status_path),
        "project_root": mission.absolute(),
    }


def json_load(path: Path) -> dict:
    import json

    return json.loads(path.read_bytes())


def _omission_envelope(
    queue_path: Path,
    queue: dict,
    *,
    decision_for: dict[str, str] | None = None,
) -> dict:
    import hashlib

    decision_for = decision_for or {}
    rows = []
    for item in queue["items"]:
        if item["queue_type"] != "omission_risk":
            continue
        decision = decision_for.get(item["risk_id"])
        if decision is None:
            disposition = item["machine_disposition"]
            decision = {
                "inspect_next": "must_inspect",
                "omit_with_reason": "acceptable_omission",
                "quarantine": "blocked_pending_source",
                "blocked_source_or_frontier": "must_inspect",
            }[disposition]
        row = {
            "queue_item_id": item["item_id"],
            "risk_id": item["risk_id"],
            "decision": decision,
            "reason": "Fixture review records the exact current bounded scope.",
            "reviewer": "fixture-reviewer",
            "reviewed_at": "2026-07-12T00:00:00Z",
        }
        if decision in {"must_inspect", "expand_scope", "blocked_pending_source"}:
            row["next_action"] = "Keep the exact risk open pending the recorded next action."
        else:
            row["scope_basis"] = "Closed only for the exact recorded fixture scope."
        rows.append(row)
    return {
        "schema_version": REVIEW_DECISIONS_SCHEMA,
        "decision_type": "omission_risk",
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "artifact_set_id": queue["artifact_set_id"],
        "queue_semantic_sha256": queue["queue_semantic_sha256"],
        "review_queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
        "decisions": rows,
    }


def _bound_envelope(queue_path: Path, queue: dict, decision_type: str, rows: list[dict]) -> dict:
    import hashlib

    return {
        "schema_version": REVIEW_DECISIONS_SCHEMA,
        "decision_type": decision_type,
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "artifact_set_id": queue["artifact_set_id"],
        "queue_semantic_sha256": queue["queue_semantic_sha256"],
        "review_queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
        "decisions": rows,
    }


def _v3_source_envelope(queue_path: Path, output_dir: Path) -> dict:
    context = load_v2_evidence_context(queue_path)
    status = context.validated_source_intake["status"]
    status_raw = context.validated_source_intake["status_bytes"]
    ledger_path = Path(status["outcome_ledger_path"])
    observations = []
    for item_id, identity in sorted(context.source_identities.items()):
        semantic = {
            "schema_version": "ra-survey-source-status-observation-identity-v1",
            "queue_item_id": item_id,
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "canonical_identifier": identity.canonical_identifier,
            "aliases": identity.aliases,
            "source_version": identity.source_version,
            "source_record_path": identity.source_record_path,
            "source_record_sha256": identity.source_record_sha256,
            "source_record_size_bytes": identity.source_record_size_bytes,
            "provider": identity.provider,
            "final_url": identity.final_url,
            "status_source": "synthetic fixture status registry",
            "evidence_class": "recorded_status_check",
            "observed_at": "2026-07-12T02:00:00Z",
            "checks_performed": SOURCE_CHECKS,
            "outcome": "checked_clear_for_recorded_checks",
            "notices": [],
            "fixture_only": True,
            "claim_support_allowed": False,
            "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        }
        digest = sha256_bytes(canonical_json_bytes(semantic))
        observations.append({
            "observation_id": f"so-{digest}",
            "observation_sha256": digest,
            **{key: value for key, value in semantic.items() if key != "schema_version"},
        })
    observation_set = {
        "schema_version": SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
        **context.binding,
        "source_intake_status_path": str(context.mission_root / "source_intake" / "phase4_source_intake_status.json"),
        "source_intake_status_sha256": sha256_bytes(status_raw),
        "source_intake_status_size_bytes": len(status_raw),
        "source_outcome_ledger_path": str(ledger_path),
        "source_outcome_ledger_sha256": sha256_bytes(ledger_path.read_bytes()),
        "source_outcome_ledger_size_bytes": ledger_path.stat().st_size,
        "fixture_only": True,
        "observations": observations,
        "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        "predecessor_observation_set_id": None,
        "predecessor_observation_set_manifest_sha256": None,
    }
    binding = preview_source_observation_binding(
        review_queue_path=queue_path,
        observation_set=observation_set,
        output_dir=output_dir,
    )
    by_item = {row["queue_item_id"]: row for row in observations}
    decisions = []
    for item_id, identity in sorted(context.source_identities.items()):
        observation = by_item[item_id]
        decisions.append({
            "queue_item_id": item_id,
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "observation_set_id": binding["observation_set_id"],
            "observation_set_manifest_sha256": binding["observation_set_manifest_sha256"],
            "observation_id": observation["observation_id"],
            "observation_sha256": observation["observation_sha256"],
            "source_version": identity.source_version,
            "reviewer_authority": "human_reviewed_status",
            "decision": "checked_clear",
            "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-12T02:01:00Z",
            "reason": "Synthetic fixture decision for engineering state-transition tests only.",
            "fixture_only": True,
        })
    return {
        "schema_version": SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
        "decision_type": "source_safety",
        **context.binding,
        "observation_set": observation_set,
        "decisions": decisions,
    }


def _v3_claim_envelope(queue_path: Path) -> dict:
    context = load_v2_evidence_context(queue_path)
    item = next(row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate")
    dependencies = [
        {
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "canonical_identifier": identity.canonical_identifier,
            "source_version": identity.source_version,
            "source_record_sha256": identity.source_record_sha256,
            "dependency_role": "primary_technical_source",
        }
        for identity in sorted(context.source_identities.values(), key=lambda row: row.source_paper_id)
        if identity.source_paper_id in item["paper_ids"]
    ]
    manifest_projection = {
        "schema_version": SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        "evidence_kind": "primary_technical_support",
        "local_artifact": None,
        "local_artifact_sha256": None,
        "direct_source_paper_ids": sorted(row["source_paper_id"] for row in dependencies),
        "referenced_manifest_ids": [],
    }
    manifest_id = f"dm-{sha256_bytes(canonical_json_bytes(manifest_projection))}"
    manifests = [{"manifest_id": manifest_id, **manifest_projection}]
    graph = {
        "schema_version": "ra-survey-claim-dependency-graph-v1",
        "root_dependency_manifest_id": manifest_id,
        "dependency_manifests": manifests,
        "source_dependencies": dependencies,
    }
    return {
        "schema_version": SURVEY_CLAIM_REVIEW_V3_SCHEMA,
        "decision_type": "claim_candidate",
        **context.binding,
        "decisions": [{
            "queue_item_id": item["item_id"],
            "claim_id": "fixture-reviewed-claim",
            "claim_text": "The exact fixture source contains the recorded Method section.",
            "claim_type": "paper_technical",
            "review_status": "human_reviewed_passed",
            "support_class": "primary_technical_support",
            "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-12T02:02:00Z",
            "evidence_note": "Synthetic fixture review for engineering state-transition tests only.",
            "fixture_only": True,
            "source_dependencies": dependencies,
            "dependency_manifests": manifests,
            "root_dependency_manifest_id": manifest_id,
            "dependency_graph_sha256": sha256_bytes(canonical_json_bytes(graph)),
            "paper_ids": item["paper_ids"],
            "anchor_ids": item["anchor_ids"],
        }],
    }


def _import_complete_v2_reviews(
    *,
    mission: Path,
    queue_path: Path,
    queue: dict,
    decisions_dir: Path,
) -> dict[str, Path]:
    items_by_type = {
        decision_type: [row for row in queue["items"] if row["queue_type"] == decision_type]
        for decision_type in ("claim_candidate", "source_safety", "omission_risk", "workflow_blocker")
    }
    claim_path = decisions_dir / "claims.json"
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim_path.write_bytes(pretty_json_bytes(_v3_claim_envelope(queue_path)))
    assert import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=claim_path,
        output_dir=mission / "reviewed_claims",
    )["status"] == "reviewed_claims_complete"

    safety_path = decisions_dir / "safety.json"
    safety_path.write_bytes(pretty_json_bytes(_v3_source_envelope(
        queue_path,
        mission / "reviewed_source_safety",
    )))
    assert import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=safety_path,
        output_dir=mission / "reviewed_source_safety",
    )["status"] == "reviewed_source_safety_complete"

    omission_path = decisions_dir / "omissions.json"
    omission_rows = []
    for item in items_by_type["omission_risk"]:
        decision = {
            "inspect_next": "must_inspect",
            "omit_with_reason": "acceptable_omission",
            "quarantine": "blocked_pending_source",
            "blocked_source_or_frontier": "acceptable_omission",
        }[item["machine_disposition"]]
        row = {
            "queue_item_id": item["item_id"],
            "risk_id": item["risk_id"],
            "decision": decision,
            "reason": "Exact synthetic fixture decision for the recorded scope only.",
            "reviewer": "fixture-reviewer",
            "reviewed_at": "2026-07-12T02:00:00Z",
        }
        if decision in {"must_inspect", "expand_scope", "blocked_pending_source"}:
            row["next_action"] = "Keep the exact risk open pending its recorded next action."
        else:
            row["scope_basis"] = "Closed only for the exact recorded fixture scope."
        omission_rows.append(row)
    omission_path.write_bytes(pretty_json_bytes(_bound_envelope(
        queue_path,
        queue,
        "omission_risk",
        omission_rows,
    )))
    omission_result = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=omission_path,
        output_dir=mission / "reviewed_omissions",
        now=lambda: "2026-07-12T02:00:00Z",
        nonce_factory=lambda: "a" * 32,
    )
    assert omission_result["status"] == "reviewed_omissions_complete"

    workflow_path = decisions_dir / "workflow.json"
    workflow_rows = []
    for item in items_by_type["workflow_blocker"]:
        workflow_rows.append({
            "queue_item_id": item["item_id"],
            "disposition": "resolved_by_reviewed_evidence",
            "evidence_queue_item_ids": item["required_evidence_queue_item_ids"],
            "rationale": "The exact current synthetic decision set structurally addresses this blocker.",
            "reviewer": "fixture-reviewer",
            "reviewed_at": "2026-07-12T02:00:00Z",
        })
    workflow_path.write_bytes(pretty_json_bytes(_bound_envelope(
        queue_path,
        queue,
        "workflow_blocker",
        workflow_rows,
    )))
    assert import_reviewed_workflow_blockers(
        review_queue_path=queue_path,
        decisions_path=workflow_path,
        output_dir=mission / "reviewed_workflow_blockers",
    )["status"] == "reviewed_workflow_blockers_complete"

    selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=mission / "reviewed_omissions",
    )
    assert isinstance(selected, OmissionDecisionSetSnapshot)
    claim_snapshot, _ = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=mission / "reviewed_claims",
    )
    _, source_snapshot, _ = resolve_current_source_safety(
        review_queue_path=queue_path,
        reviewed_source_safety_root=mission / "reviewed_source_safety",
    )
    return {
        "claim_candidate": claim_snapshot.artifact_paths["reviewed_claims.json"],
        "source_safety": source_snapshot.artifact_paths["reviewed_source_safety.json"],
        "omission_risk": selected.sidecar_path,
        "workflow_blocker": mission / "reviewed_workflow_blockers" / "reviewed_workflow_blockers.json",
    }


def test_exact_projection_attempt_universe_and_recorded_roles(tmp_path: Path) -> None:
    payloads = _build(tmp_path)
    attempts = _attempts(payloads)
    observations = _observations(payloads)

    assert len(attempts) == 2
    assert {row["direction"] for row in attempts} == {"backward", "forward"}
    assert all(row["origin_paper_id"] == attempts[0]["origin_paper_id"] for row in attempts)
    assert all(row["query_kind"] is None and row["matched_query_provenance"] is None for row in attempts)
    assert all(row["mechanism_kind"].startswith("recorded_") for row in attempts)
    assert all(row["attempt_status"] == "observed_results" for row in attempts)

    roles = {
        role
        for observation in observations
        for role in observation["classification_signals"]["recorded_roles"]
    }
    assert {"direct_method", "adjacent_method", "major_citing_work", "backward_lineage_candidate"} <= roles
    assert not ({"foundational", "competitor", "correction", "recent"} & roles)
    assert all(observation["query_kind"] is None for observation in observations)
    assert all(observation["claim_support_allowed"] is False for observation in observations)


def test_missing_exact_relations_are_not_observed_not_empty(tmp_path: Path) -> None:
    seed_only = [_records()[0]]
    seed_only[0]["referenced_works"] = []
    payloads = _build(tmp_path, records=seed_only)

    for attempt in _attempts(payloads):
        assert attempt["attempt_status"] == "not_observed"
        assert attempt["candidate_observation_ids"] == []
        assert attempt["derived_attempt_risk_id"].startswith("or-")
        assert attempt["query_kind"] is None
        assert attempt["matched_query_provenance"] is None
        assert attempt["carrier_query_provenance"] == []
    for name in ("backward_snowball.json", "forward_snowball.json"):
        assert payloads[name]["evidence_policy"]["projection_is_not_provider_query_transcript"] is True
        assert "literature completeness" in payloads[name]["what_is_not_concluded"]


def test_unresolved_reference_is_target_bearing_quarantine_not_attempt_risk(tmp_path: Path) -> None:
    payloads = _build(tmp_path)
    unresolved = next(
        row for row in payloads["backward_snowball.json"]["observations"]
        if row["target_id"] == "openalex:w999"
    )
    backward = payloads["backward_snowball.json"]["attempts"][0]

    assert unresolved["observation_status"] == "source_blocked"
    assert unresolved["machine_disposition"] == "quarantine"
    assert backward["derived_attempt_risk_id"] is None
    risks = payloads["omitted_paper_risks.json"]["risks"]
    risk = next(row for row in risks if row["risk_source_id"] == unresolved["observation_id"])
    assert risk["risk_source_type"] == "candidate_observation"
    assert risk["machine_disposition"] == "quarantine"


def test_inherited_risks_are_preserved_once_and_reconciled(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    payloads = build_frontier_payloads(**authority)
    inherited_input = authority["omission_risk"]["risks"]
    omitted = payloads["omitted_paper_risks.json"]
    inherited = [row for row in omitted["risks"] if row["risk_source_type"] == "inherited_metadata_risk"]
    reconciliation = omitted["risk_reconciliation"]

    assert {row["inherited_risk_id"] for row in inherited} == {
        row["risk_id"] for row in inherited_input
    }
    assert len(inherited) == len(inherited_input)
    assert all(row["machine_disposition"] == "blocked_source_or_frontier" for row in inherited)
    assert all(row["frontier_attempt_id"] is None for row in inherited)
    assert reconciliation["implicit_supersession_allowed"] is False
    assert reconciliation["complete_output_risk_ids"] == [row["risk_id"] for row in omitted["risks"]]
    assert len(reconciliation["inherited_mappings"]) == len(inherited_input)


def test_permutation_does_not_change_semantic_payloads(tmp_path: Path) -> None:
    rows = _records()
    baseline = _build(tmp_path, records=rows)
    for index, order in enumerate(permutations(rows[:3])):
        permuted = [*order, *rows[3:]]
        result = _build(tmp_path, records=permuted)
        assert canonical_json_bytes(result) == canonical_json_bytes(baseline)


def test_recursive_included_origin_is_crossed_with_both_directions(tmp_path: Path) -> None:
    records = _records()
    authority = _authority(tmp_path, records=records)
    authority["citation_map"]["expansion_policy"]["backward_depth"] = 2
    authority["citation_map"]["expansion_policy"]["forward_depth"] = 2
    _refresh_authority_artifact(authority, "citation_map.json")
    payloads = build_frontier_payloads(**authority)
    direct_id = next(
        row["paper_id"]
        for row in authority["relevance_ranking"]["rows"]
        if row.get("disposition") == "direct_topic_match"
    )
    depth_two = [row for row in _attempts(payloads) if row["depth"] == 2]

    assert {(row["origin_paper_id"], row["direction"]) for row in depth_two} >= {
        (direct_id, "backward"),
        (direct_id, "forward"),
    }


@pytest.mark.parametrize(
    ("discovery_direction", "later_direction", "target_role"),
    [
        ("backward", "forward", "direct_method"),
        ("forward", "backward", "major_citing_work"),
    ],
)
def test_asymmetric_depth_retains_included_origin_for_other_direction(
    tmp_path: Path,
    discovery_direction: str,
    later_direction: str,
    target_role: str,
) -> None:
    authority = _authority(tmp_path)
    authority["citation_map"]["expansion_policy"][f"{discovery_direction}_depth"] = 1
    authority["citation_map"]["expansion_policy"][f"{later_direction}_depth"] = 2
    _refresh_authority_artifact(authority, "citation_map.json")
    payloads = build_frontier_payloads(**authority)
    target_id = next(
        row["paper_id"]
        for row in authority["identity_resolution"]["components"]
        if target_role in row.get("roles", [])
    )
    depth_one = [
        row
        for row in _observations(payloads)
        if row["depth"] == 1
        and row["direction"] == discovery_direction
        and row["target_paper_id"] == target_id
    ]

    assert len(depth_one) == 1
    assert depth_one[0]["observation_status"] == "depth_excluded"
    assert depth_one[0]["machine_disposition"] == "inspect_next"
    assert any(
        row["depth"] == 2
        and row["direction"] == later_direction
        and row["origin_paper_id"] == target_id
        for row in _attempts(payloads)
    )


def test_production_depth_and_cap_exclusions_remain_visible_with_risks(tmp_path: Path) -> None:
    depth_payloads = _build(tmp_path / "depth")
    depth_rows = [
        row for row in _observations(depth_payloads)
        if row["observation_status"] == "depth_excluded"
    ]
    assert depth_rows
    depth_risks = depth_payloads["omitted_paper_risks.json"]["risks"]
    assert {row["observation_id"] for row in depth_rows} <= {
        row["risk_source_id"] for row in depth_risks
    }

    cap_authority = _authority(tmp_path / "cap")
    cap_authority["citation_map"]["expansion_policy"]["max_nodes"] = 1
    _refresh_authority_artifact(cap_authority, "citation_map.json")
    cap_payloads = build_frontier_payloads(**cap_authority)
    capped = [row for row in _observations(cap_payloads) if row["observation_status"] == "capped"]
    cap_risks = cap_payloads["omitted_paper_risks.json"]["risks"]
    assert capped
    assert {row["observation_id"] for row in capped} <= {row["risk_source_id"] for row in cap_risks}


def test_duplicate_relation_routes_union_without_unrelated_route(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    seed_id = authority["identity_resolution"]["seed_resolutions"][0]["selected_paper_id"]
    seed_component = next(
        row for row in authority["identity_resolution"]["components"]
        if row.get("paper_id") == seed_id
    )
    base = deepcopy(seed_component["rows"][0])
    second = deepcopy(base)
    second["record_key"] = "seed-second-carrier"
    second["source_identities"] = [["openalex", "w100", "seed-second-carrier"]]
    second["query_provenance"] = [{
        "provider": "openalex",
        "query_kind": "topic_search",
        "normalized_seed_key": None,
        "topic_query": True,
    }]
    unrelated = deepcopy(base)
    unrelated["record_key"] = "seed-unrelated-route"
    unrelated["source_identities"] = [["openalex", "w100", "seed-unrelated-route"]]
    unrelated["referenced_works"] = []
    unrelated["query_provenance"] = [{
        "provider": "openalex",
        "query_kind": "adjacent_search",
        "normalized_seed_key": None,
        "topic_query": True,
    }]
    seed_component["rows"] = [base, second, unrelated]
    _refresh_authority_artifact(authority, "identity_resolution.json")
    payloads = build_frontier_payloads(**authority)
    target = next(
        row for row in payloads["backward_snowball.json"]["observations"]
        if row["target_id"] == "openalex:w999"
    )
    kinds = {route["query_kind"] for route in target["carrier_query_provenance"]}

    assert kinds == {"seed_resolution", "topic_search"}


@pytest.mark.parametrize("value", [1_000_001, 2**63])
def test_traversal_policy_overflow_fails_closed(tmp_path: Path, value: int) -> None:
    authority = _authority(tmp_path)
    authority["citation_map"]["expansion_policy"]["max_nodes"] = value
    _refresh_authority_artifact(authority, "citation_map.json")
    with pytest.raises(MissionStateError) as error:
        build_frontier_payloads(**authority)
    assert error.value.code == "invalid_frontier_policy"


@pytest.mark.parametrize(
    ("status", "children", "risk", "mechanism", "query_kind", "matched", "carrier", "valid"),
    [
        ("observed_results", ["fo-" + "1" * 64], None, "recorded_reference_projection", None, None, [{"provider": "openalex"}], True),
        ("not_observed", [], "or-" + "2" * 64, "recorded_reference_projection", None, None, [], True),
        ("empty_observed", [], "or-" + "3" * 64, "recorded_reference_projection", None, None, [], False),
        ("provider_unavailable", [], "or-" + "4" * 64, "recorded_reverse_reference_projection", None, None, [], False),
        ("empty_observed", [], "or-" + "5" * 64, "recorded_query_observation", "backward_reference_observation", {"status": "available"}, [], True),
        ("provider_unavailable", [], "or-" + "6" * 64, "recorded_query_observation", "forward_citation_observation", {"status": "unavailable"}, [], True),
        ("malformed_blocked", [], "or-" + "7" * 64, "recorded_query_observation", "forward_citation_observation", {"status": "malformed"}, [], True),
    ],
)
def test_attempt_status_cardinality_and_mechanism_matrix(
    status: str,
    children: list[str],
    risk: str | None,
    mechanism: str,
    query_kind: str | None,
    matched: dict | None,
    carrier: list[dict],
    valid: bool,
) -> None:
    attempt = {
        "attempt_status": status,
        "candidate_observation_ids": children,
        "derived_attempt_risk_id": risk,
        "mechanism_kind": mechanism,
        "query_kind": query_kind,
        "matched_query_provenance": matched,
        "carrier_query_provenance": carrier,
    }
    if valid:
        validate_attempt_cardinality(attempt)
    else:
        with pytest.raises(MissionStateError):
            validate_attempt_cardinality(attempt)


@pytest.mark.parametrize(
    ("status", "disposition", "valid"),
    [
        (status, disposition, disposition in allowed)
        for status, allowed in sorted(OBSERVATION_DISPOSITIONS.items())
        for disposition in sorted({
            "include",
            "inspect_next",
            "omit_with_reason",
            "quarantine",
            "blocked_source_or_frontier",
        })
    ],
)
def test_observation_status_disposition_matrix(status: str, disposition: str, valid: bool) -> None:
    row = {
        "observation_id": "fo-" + "a" * 64,
        "observation_status": status,
        "machine_disposition": disposition,
    }
    if valid:
        validate_observation_disposition(row)
    else:
        with pytest.raises(MissionStateError):
            validate_observation_disposition(row)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("generic_query", "invented_frontier_query"),
        ("boolean_depth", "invalid_frontier_policy"),
        ("naive_timestamp", "invalid_frontier_input"),
        ("wrong_topic", "foreign_frontier_input"),
        ("missing_digest", "invalid_frontier_input"),
        ("duplicate_inherited", "invalid_frontier_input"),
    ],
)
def test_tampered_or_invented_authority_fails_closed(tmp_path: Path, mutation: str, code: str) -> None:
    authority = _authority(tmp_path)
    if mutation == "generic_query":
        attempt = {
            "attempt_status": "observed_results",
            "candidate_observation_ids": ["fo-" + "1" * 64],
            "derived_attempt_risk_id": None,
            "mechanism_kind": "recorded_reference_projection",
            "query_kind": "topic_search",
            "matched_query_provenance": {"query_kind": "topic_search"},
            "carrier_query_provenance": [{"provider": "openalex"}],
        }
        with pytest.raises(MissionStateError) as error:
            validate_attempt_cardinality(attempt)
        assert error.value.code == code
        return
    if mutation == "boolean_depth":
        authority["citation_map"]["expansion_policy"]["backward_depth"] = True
    elif mutation == "naive_timestamp":
        authority["metadata_provenance"]["accessed_at"] = "2026-07-12T00:00:00"
    elif mutation == "wrong_topic":
        authority["citation_map"]["topic"] = "foreign"
    elif mutation == "missing_digest":
        authority["artifact_digests"].pop("omission_risk.json")
    else:
        authority["omission_risk"]["risks"].append(deepcopy(authority["omission_risk"]["risks"][0]))
    with pytest.raises(MissionStateError) as error:
        build_frontier_payloads(**authority)
    assert error.value.code == code


def test_declared_closed_statuses_remain_complete() -> None:
    assert ATTEMPT_STATUSES == {
        "observed_results",
        "empty_observed",
        "not_observed",
        "provider_unavailable",
        "malformed_blocked",
    }
    assert set(OBSERVATION_DISPOSITIONS) == {
        "observed",
        "capped",
        "depth_excluded",
        "identity_conflict",
        "source_blocked",
    }


def test_canonical_v2_orchestration_selects_replayable_frontier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    coverage = queue_path.parent / "coverage"
    backward = json_load(coverage / "backward_snowball.json")
    forward = json_load(coverage / "forward_snowball.json")
    omitted = json_load(coverage / "omitted_paper_risks.json")

    assert backward["schema_version"] == "ra-survey-backward-snowball-v2"
    assert forward["schema_version"] == "ra-survey-forward-snowball-v2"
    assert omitted["schema_version"] == "ra-survey-omitted-paper-risks-v2"
    assert backward["source_mission_binding"]["mission_id"] == queue["mission_id"]
    assert backward["source_mission_binding"]["mission_fingerprint"] == queue["mission_fingerprint"]
    assert (
        backward["source_mission_binding"]["mission_anchor_generation_id"]
        == queue["mission_anchor_generation_id"]
    )
    assert queue["artifact_set_id"] == queue_path.parent.name
    assert not (mission / "reviewed_omissions").exists()


@pytest.mark.parametrize(
    "attack",
    [
        "missing_row",
        "unsorted_rows",
        "extra_row",
        "hash_mismatch",
        "size_mismatch",
        "symlink_child",
        "moved_root",
        "malformed_json",
        "noncanonical_json",
        "wrong_schema",
    ],
)
def test_canonical_v2_frontier_loader_attack_matrix_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    mission, _, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    validated = _validated_frontier_input(mission, queue)
    status = validated["status"]
    authority = status["metadata_authority"]
    rows = authority["artifact_rows"]
    identity = mission / "public_metadata" / "identity_resolution.json"
    outside = tmp_path / "outside_identity.json"
    if attack == "missing_row":
        rows.pop()
    elif attack == "unsorted_rows":
        rows.reverse()
    elif attack == "extra_row":
        rows.append(deepcopy(rows[0]))
        rows[-1]["name"] = "extra.json"
        rows[-1]["path"] = str(mission / "public_metadata" / "extra.json")
    elif attack == "hash_mismatch":
        next(row for row in rows if row["name"] == "identity_resolution.json")["sha256"] = "0" * 64
    elif attack == "size_mismatch":
        next(row for row in rows if row["name"] == "identity_resolution.json")["size_bytes"] += 1
    elif attack == "symlink_child":
        outside.write_bytes(identity.read_bytes())
        identity.unlink()
        identity.symlink_to(outside)
    elif attack == "moved_root":
        moved = tmp_path / "moved_metadata"
        (mission / "public_metadata").rename(moved)
        authority["metadata_root"] = str(moved)
        for row in rows:
            row["path"] = str(moved / row["name"])
    elif attack == "malformed_json":
        identity.write_bytes(b"{")
    elif attack == "noncanonical_json":
        identity.write_bytes(canonical_json_bytes(json_load(identity)))
    else:
        payload = json_load(identity)
        payload["schema_version"] = "wrong-schema"
        identity.write_bytes(pretty_json_bytes(payload))
        row = next(item for item in rows if item["name"] == "identity_resolution.json")
        row["sha256"] = sha256_bytes(identity.read_bytes())
        row["size_bytes"] = identity.stat().st_size
    if attack in {"missing_row", "unsorted_rows", "extra_row", "hash_mismatch", "size_mismatch", "moved_root", "wrong_schema"}:
        status["metadata_authority_sha256"] = sha256_bytes(canonical_json_bytes(authority))

    with pytest.raises(MissionStateError):
        load_v2_frontier_context(
            topic=TOPIC,
            validated_source_intake=validated,
            mission_anchor_generation_id=queue["mission_anchor_generation_id"],
        )


@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("semantic_tamper", "frontier_semantic_replay_mismatch"),
        ("schema_downgrade", "coverage_schema_downgrade"),
        ("schema_downgrade_missing_status", "missing_frontier_context"),
        ("citation_venue_schema_downgrade", "coverage_schema_downgrade"),
        ("paper_classification_schema_downgrade", "coverage_schema_downgrade"),
    ],
)
def test_rehashed_selected_v2_tamper_fails_authoritative_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    expected_code: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    current_set = queue_path.parent
    coverage_payloads = {
        name: {
            key: value
            for key, value in json_load(current_set / "coverage" / name).items()
            if key not in artifact_lineage.IDENTITY_FIELDS
        }
        for name in artifact_lineage.COVERAGE_FILES
    }
    if attack == "semantic_tamper":
        attempt = coverage_payloads["backward_snowball.json"]["attempts"][0]
        attempt["claim_support_allowed"] = True
    elif attack.startswith("schema_downgrade"):
        coverage_payloads["backward_snowball.json"]["schema_version"] = (
            "ra-survey-backward-snowball-v1"
        )
        coverage_payloads["forward_snowball.json"]["schema_version"] = (
            "ra-survey-forward-snowball-v1"
        )
        coverage_payloads["omitted_paper_risks.json"]["schema_version"] = (
            "ra-survey-omitted-paper-risks-v1"
        )
    elif attack == "citation_venue_schema_downgrade":
        coverage_payloads["citation_venue_metadata.json"]["schema_version"] = (
            "unsupported-citation-venue-metadata-schema"
        )
    else:
        coverage_payloads["paper_classifications.json"]["schema_version"] = (
            "unsupported-paper-classifications-schema"
        )
    packet_dir = mission / "public_source_packet"
    coverage_packet_digests = artifact_lineage._digest_map(
        packet_dir,
        artifact_lineage.PACKET_COVERAGE_FILES,
    )
    queue_packet_digests = artifact_lineage._digest_map(
        packet_dir,
        artifact_lineage.PACKET_QUEUE_FILES,
    )
    packet_digests = dict(sorted({**coverage_packet_digests, **queue_packet_digests}.items()))
    coverage_semantic = artifact_lineage._coverage_semantic_digests(
        coverage_payloads,
        packet_input_digests=coverage_packet_digests,
    )
    queue_payload = {
        key: value
        for key, value in queue.items()
        if key not in artifact_lineage.QUEUE_DERIVED_FIELDS
    }
    queue_semantic = artifact_lineage._queue_semantic_sha256(
        mission_id=queue["mission_id"],
        mission_fingerprint=queue["mission_fingerprint"],
        mission_anchor_generation_id=queue["mission_anchor_generation_id"],
        packet_input_digests=queue_packet_digests,
        coverage_semantic_digests=coverage_semantic,
        queue=queue_payload,
    )
    identity = {
        "schema_version": artifact_lineage.ARTIFACT_SET_IDENTITY_SCHEMA,
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "mission_anchor_generation_id": queue["mission_anchor_generation_id"],
        "packet_input_digests": packet_digests,
        "coverage_semantic_digests": coverage_semantic,
        "queue_semantic_sha256": queue_semantic,
    }
    semantic_digest = sha256_bytes(canonical_json_bytes(identity))
    set_id = f"s-{semantic_digest}"
    manager = ArtifactStateManager(
        mission_root=mission,
        mission_id=queue["mission_id"],
        mission_fingerprint=queue["mission_fingerprint"],
        mission_anchor_generation_id=queue["mission_anchor_generation_id"],
        nonce_factory=lambda: "9" * 32,
    )
    payloads = manager._final_payloads(
        set_id=set_id,
        packet_digests=packet_digests,
        coverage_packet_digests=coverage_packet_digests,
        queue_packet_digests=queue_packet_digests,
        coverage_payloads=coverage_payloads,
        review_queue_payload=queue_payload,
        coverage_semantic_digests=coverage_semantic,
        queue_semantic_sha256=queue_semantic,
        semantic_digest=semantic_digest,
    )
    final_dir = manager.sets_dir / set_id
    manager._write_set(final_dir, payloads)
    pointer = {
        "schema_version": artifact_lineage.ARTIFACT_CURRENT_SCHEMA,
        "artifact_set_id": set_id,
        "artifact_set_manifest_sha256": sha256_bytes(
            (final_dir / "artifact_set_manifest.json").read_bytes()
        ),
    }
    manager._atomic_write(manager.current_path, canonical_json_bytes(pointer), kind="CURRENT")
    if attack == "schema_downgrade_missing_status":
        (mission / "source_intake" / "phase4_source_intake_status.json").unlink()

    with pytest.raises(MissionStateError) as error:
        manager.load_current()
    assert error.value.code == expected_code


@pytest.mark.parametrize(
    ("artifact_name", "unsupported_schema"),
    [
        ("citation_venue_metadata.json", "unsupported-citation-venue-metadata-schema"),
        ("paper_classifications.json", "unsupported-paper-classifications-schema"),
    ],
)
def test_retained_rehashed_auxiliary_coverage_schema_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_name: str,
    unsupported_schema: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    current_set = queue_path.parent
    coverage_payloads = {
        name: {
            key: value
            for key, value in json_load(current_set / "coverage" / name).items()
            if key not in artifact_lineage.IDENTITY_FIELDS
        }
        for name in artifact_lineage.COVERAGE_FILES
    }
    coverage_payloads[artifact_name]["schema_version"] = unsupported_schema
    packet_dir = mission / "public_source_packet"
    coverage_packet_digests = artifact_lineage._digest_map(
        packet_dir,
        artifact_lineage.PACKET_COVERAGE_FILES,
    )
    queue_packet_digests = artifact_lineage._digest_map(
        packet_dir,
        artifact_lineage.PACKET_QUEUE_FILES,
    )
    packet_digests = dict(sorted({**coverage_packet_digests, **queue_packet_digests}.items()))
    coverage_semantic = artifact_lineage._coverage_semantic_digests(
        coverage_payloads,
        packet_input_digests=coverage_packet_digests,
    )
    queue_payload = {
        key: value
        for key, value in queue.items()
        if key not in artifact_lineage.QUEUE_DERIVED_FIELDS
    }
    queue_semantic = artifact_lineage._queue_semantic_sha256(
        mission_id=queue["mission_id"],
        mission_fingerprint=queue["mission_fingerprint"],
        mission_anchor_generation_id=queue["mission_anchor_generation_id"],
        packet_input_digests=queue_packet_digests,
        coverage_semantic_digests=coverage_semantic,
        queue=queue_payload,
    )
    identity = {
        "schema_version": artifact_lineage.ARTIFACT_SET_IDENTITY_SCHEMA,
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "mission_anchor_generation_id": queue["mission_anchor_generation_id"],
        "packet_input_digests": packet_digests,
        "coverage_semantic_digests": coverage_semantic,
        "queue_semantic_sha256": queue_semantic,
    }
    semantic_digest = sha256_bytes(canonical_json_bytes(identity))
    set_id = f"s-{semantic_digest}"
    manager = ArtifactStateManager(
        mission_root=mission,
        mission_id=queue["mission_id"],
        mission_fingerprint=queue["mission_fingerprint"],
        mission_anchor_generation_id=queue["mission_anchor_generation_id"],
        nonce_factory=lambda: "8" * 32,
    )
    payloads = manager._final_payloads(
        set_id=set_id,
        packet_digests=packet_digests,
        coverage_packet_digests=coverage_packet_digests,
        queue_packet_digests=queue_packet_digests,
        coverage_payloads=coverage_payloads,
        review_queue_payload=queue_payload,
        coverage_semantic_digests=coverage_semantic,
        queue_semantic_sha256=queue_semantic,
        semantic_digest=semantic_digest,
    )
    manager._write_set(manager.sets_dir / set_id, payloads)

    with pytest.raises(MissionStateError) as error:
        manager.validate_retained_set(set_id)
    assert error.value.code == "invalid_retained_coverage_schema"


def test_retained_artifact_validation_skips_only_external_frontier_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    manager = ArtifactStateManager(
        mission_root=mission,
        mission_id=queue["mission_id"],
        mission_fingerprint=queue["mission_fingerprint"],
        mission_anchor_generation_id=queue["mission_anchor_generation_id"],
    )

    def external_replay_forbidden(**_: object) -> None:
        raise MissionStateError("external_frontier_replay_tripwire", "active replay reached")

    monkeypatch.setattr(artifact_lineage, "_validate_v2_coverage_replay", external_replay_forbidden)
    retained = manager.validate_retained_set(queue["artifact_set_id"])
    assert retained.artifact_set_id == queue["artifact_set_id"]
    with pytest.raises(MissionStateError) as error:
        manager.load_current()
    assert error.value.code == "external_frontier_replay_tripwire"
    with pytest.raises(MissionStateError) as selected_error:
        manager.validate_selected_path(retained.review_queue_path, role="review_queue")
    assert selected_error.value.code == "external_frontier_replay_tripwire"


@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("missing_root", "missing_artifact_state"),
        ("unsafe_root", "unsafe_artifact_state"),
        ("missing_genesis", "invalid_artifact_state_json"),
        ("missing_set", "unsafe_artifact_set_path"),
        ("unsafe_set", "unexpected_artifact_set_path"),
        ("foreign_manifest_identity", "foreign_lineage"),
        ("manifest_rows", "invalid_artifact_rows"),
        ("changed_bytes", "corrupt_selected_lineage"),
        ("mixed_coverage_schema", "invalid_retained_coverage_schema"),
        ("unsupported_coverage_schema", "invalid_retained_coverage_schema"),
        ("coverage_semantic", "coverage_semantic_mismatch"),
        ("coverage_manifest", "coverage_lineage_mismatch"),
        ("queue_schema", "invalid_review_queue_schema"),
        ("queue_item", "queue_item_digest_mismatch"),
        ("queue_count", "queue_count_mismatch"),
        ("queue_semantic", "queue_semantic_mismatch"),
        ("foreign_mission", "foreign_artifact_genesis"),
        ("mission_ancestor", "retained_mission_ancestor_tripwire"),
    ],
)
def test_retained_artifact_validation_class_matrix_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    expected_code: str,
) -> None:
    mission, _, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    manager = ArtifactStateManager(
        mission_root=mission,
        mission_id=("22222222-2222-4222-8222-222222222222" if attack == "foreign_mission" else queue["mission_id"]),
        mission_fingerprint=queue["mission_fingerprint"],
        mission_anchor_generation_id=queue["mission_anchor_generation_id"],
    )
    set_id = queue["artifact_set_id"]
    set_dir = mission / ".artifact_state" / "sets" / set_id

    if attack == "missing_root":
        (mission / ".artifact_state").rename(mission / "saved-artifact-state")
    elif attack == "unsafe_root":
        state = mission / ".artifact_state"
        outside = tmp_path / "outside-artifact-state"
        state.rename(outside)
        state.symlink_to(outside, target_is_directory=True)
    elif attack == "missing_genesis":
        (mission / ".artifact_state" / "GENESIS").rename(mission / "saved-artifact-genesis")
    elif attack == "missing_set":
        set_id = "s-" + "0" * 64
    elif attack == "unsafe_set":
        outside = tmp_path / "outside-retained-set"
        set_dir.rename(outside)
        set_dir.symlink_to(outside, target_is_directory=True)
    elif attack in {"foreign_manifest_identity", "manifest_rows"}:
        original_read_canonical = artifact_lineage._read_canonical

        def altered_manifest(path: Path, label: str) -> tuple[dict, bytes]:
            payload, raw = original_read_canonical(path, label)
            if label == "artifact set manifest":
                payload = deepcopy(payload)
                if attack == "foreign_manifest_identity":
                    payload["mission_id"] = "33333333-3333-4333-8333-333333333333"
                else:
                    payload["artifacts"].append(deepcopy(payload["artifacts"][0]))
            return payload, raw

        monkeypatch.setattr(artifact_lineage, "_read_canonical", altered_manifest)
    elif attack == "changed_bytes":
        (set_dir / "review_queue.json").write_bytes(b"{}\n")
    elif attack in {
        "mixed_coverage_schema",
        "unsupported_coverage_schema",
        "queue_schema",
        "queue_item",
        "queue_count",
        "queue_semantic",
    }:
        original_read_pretty = artifact_lineage._read_pretty_json

        def altered_pretty(path: Path, label: str) -> dict:
            payload = deepcopy(original_read_pretty(path, label))
            if attack == "mixed_coverage_schema" and label == "coverage artifact backward_snowball.json":
                payload["schema_version"] = "ra-survey-backward-snowball-v1"
            elif attack == "unsupported_coverage_schema" and label.startswith("coverage artifact "):
                if label in {
                    "coverage artifact backward_snowball.json",
                    "coverage artifact forward_snowball.json",
                    "coverage artifact omitted_paper_risks.json",
                }:
                    payload["schema_version"] = "unsupported-frontier-schema"
            elif label == "review queue":
                if attack == "queue_schema":
                    payload["schema_version"] = "wrong-review-queue-schema"
                elif attack == "queue_item":
                    payload["items"][0]["semantic_item_sha256"] = "0" * 64
                elif attack == "queue_count":
                    payload["queue_counts"]["total"] += 1
                elif attack == "queue_semantic":
                    payload["queue_semantic_sha256"] = "0" * 64
            return payload

        monkeypatch.setattr(artifact_lineage, "_read_pretty_json", altered_pretty)
    elif attack == "coverage_semantic":
        original_semantics = artifact_lineage._coverage_semantic_digests

        def altered_semantics(*args: object, **kwargs: object) -> dict[str, str]:
            payload = dict(original_semantics(*args, **kwargs))
            payload[sorted(payload)[0]] = "0" * 64
            return payload

        monkeypatch.setattr(artifact_lineage, "_coverage_semantic_digests", altered_semantics)
    elif attack == "coverage_manifest":
        original_read_canonical = artifact_lineage._read_canonical

        def altered_coverage_manifest(path: Path, label: str) -> tuple[dict, bytes]:
            payload, raw = original_read_canonical(path, label)
            if label == "coverage manifest":
                payload = deepcopy(payload)
                payload["lineage_sha256"] = "0" * 64
            return payload, raw

        monkeypatch.setattr(artifact_lineage, "_read_canonical", altered_coverage_manifest)
    elif attack == "mission_ancestor":
        def mission_ancestor_tripwire(**_: object) -> None:
            raise MissionStateError("retained_mission_ancestor_tripwire", "ancestor replay reached")

        monkeypatch.setattr(
            artifact_lineage,
            "validate_generation_ancestor_readonly",
            mission_ancestor_tripwire,
        )

    with pytest.raises(MissionStateError) as error:
        manager.validate_retained_set(set_id)
    assert error.value.code == expected_code


@pytest.mark.parametrize(
    ("disposition", "decision", "valid"),
    [
        (disposition, decision, decision in allowed)
        for disposition, allowed in sorted(V2_OMISSION_TRANSITIONS.items())
        for decision in sorted({
            "acceptable_omission",
            "must_inspect",
            "expand_scope",
            "blocked_pending_source",
            "out_of_scope",
        })
    ],
)
def test_total_v2_omission_transition_matrix(
    disposition: str,
    decision: str,
    valid: bool,
) -> None:
    item = {
        "risk_id": "or-" + "1" * 64,
        "source_id": "or-" + "1" * 64,
        "severity": "high",
        "literature_completeness_allowed": False,
        "coverage_schema_version": "ra-survey-omitted-paper-risks-v2",
        "machine_disposition": disposition,
        "risk_source_type": "frontier_attempt",
        "risk_source_id": "fa-" + "2" * 64,
        "source_artifact_sha256": "3" * 64,
    }
    row = {
        "queue_item_id": "omission_risk-fixture",
        "risk_id": item["risk_id"],
        "decision": decision,
        "reason": "Exact bounded fixture reason.",
        "reviewer": "fixture-reviewer",
        "reviewed_at": "2026-07-12T00:00:00Z",
    }
    if decision in {"must_inspect", "expand_scope", "blocked_pending_source"}:
        row["next_action"] = "Keep the risk open."
    else:
        row["scope_basis"] = "Exact recorded fixture scope."
    normalized, reasons = validate_omission_decision(row, item, 1)

    assert (not reasons) is valid
    if valid:
        assert normalized["machine_disposition"] == disposition
        assert normalized["regeneration_required"] is (decision == "expand_scope")


def test_v2_omission_import_writes_and_reuses_immutable_selected_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    decisions = tmp_path / "omission_decisions.json"
    decisions.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    output = mission / "reviewed_omissions"

    first = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "1" * 32,
    )
    selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert first["status"] == "reviewed_omissions_complete"
    assert isinstance(selected, OmissionDecisionSetSnapshot)
    assert selected.decision_set_id.startswith("od-")
    assert Path(first["reviewed_omission_risks_path"]) == selected.sidecar_path
    assert not (output / "reviewed_omission_risks.json").exists()
    before = {path.name: path.read_bytes() for path in selected.set_dir.iterdir()}
    pointer_before = (output / "DECISION_CURRENT").read_bytes()

    replay = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "2" * 32,
    )
    replayed = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert replay["status"] == "reviewed_omissions_complete"
    assert isinstance(replayed, OmissionDecisionSetSnapshot)
    assert replayed.decision_set_id == selected.decision_set_id
    assert {path.name: path.read_bytes() for path in replayed.set_dir.iterdir()} == before
    assert (output / "DECISION_CURRENT").read_bytes() == pointer_before


def test_v2_omission_full_replacement_preserves_stale_sibling_and_selects_new_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    first_path = tmp_path / "first.json"
    first_path.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    first = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=first_path,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "3" * 32,
    )
    assert first["status"] == "reviewed_omissions_complete"
    first_selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert isinstance(first_selected, OmissionDecisionSetSnapshot)
    first_pointer = (output / "DECISION_CURRENT").read_bytes()

    replacement = _omission_envelope(queue_path, queue)
    replacement["decisions"][0]["reason"] = "A complete replacement records a revised fixture rationale."
    second_path = tmp_path / "second.json"
    second_path.write_bytes(pretty_json_bytes(replacement))
    second = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=second_path,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:01:00Z",
        nonce_factory=lambda: "4" * 32,
    )
    selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert second["status"] == "reviewed_omissions_complete"
    assert isinstance(selected, OmissionDecisionSetSnapshot)
    assert selected.decision_set_id != first_selected.decision_set_id
    assert first_selected.set_dir.is_dir()
    with pytest.raises(MissionStateError) as error:
        from research_assistant.survey.omission_review import resolve_current_omission_sidecar_path

        resolve_current_omission_sidecar_path(
            review_queue_path=queue_path,
            sidecar_path=first_selected.sidecar_path,
        )
    assert error.value.code == "stale_omission_decision_selector"

    (output / "DECISION_CURRENT").write_bytes(first_pointer)
    with pytest.raises(MissionStateError) as rollback_error:
        resolve_current_reviewed_omissions(
            review_queue_path=queue_path,
            reviewed_omissions_root=output,
        )
    assert rollback_error.value.code == "stale_omission_decision_selector"


def test_v2_omission_queue_transition_appends_after_intact_history_and_rejects_corruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_a_path, queue_a = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    decisions_a = tmp_path / "queue-a-omissions.json"
    decisions_a.write_bytes(pretty_json_bytes(_omission_envelope(queue_a_path, queue_a)))
    assert import_reviewed_omissions(
        review_queue_path=queue_a_path,
        decisions_path=decisions_a,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "a" * 32,
    )["status"] == "reviewed_omissions_complete"
    selected_a = resolve_current_reviewed_omissions(
        review_queue_path=queue_a_path,
        reviewed_omissions_root=output,
    )
    assert isinstance(selected_a, OmissionDecisionSetSnapshot)
    set_a_bytes = {path.name: path.read_bytes() for path in selected_a.set_dir.iterdir()}
    pointer_a = (output / "DECISION_CURRENT").read_bytes()

    claim_path = mission / "public_source_packet" / "claim_support.json"
    claim_payload = json_load(claim_path)
    claim_payload["claim_candidates"][0]["next_action"] = (
        "Review the changed claim semantics under a newly selected queue."
    )
    claim_path.write_bytes(pretty_json_bytes(claim_payload))
    changed = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        metadata_dir=mission / "public_metadata",
        source_status_dir=mission / "source_intake",
        anchor_dir=mission / "source_anchors",
        packet_dir=mission / "public_source_packet",
    )
    queue_b_path = Path(changed["review_queue_path"])
    queue_b = json_load(queue_b_path)
    assert queue_b_path != queue_a_path

    context_b = load_selected_decision_context(
        review_queue_path=queue_b_path,
        decision_type="omission_risk",
    )
    with pytest.raises(MissionStateError) as reuse_error:
        OmissionDecisionStateManager(context=context_b, output_dir=output).compose_and_select(
            decisions_path=decisions_a,
            decisions_raw=decisions_a.read_bytes(),
            sidecar_payload={},
            force=True,
        )
    assert reuse_error.value.code == "stale_lineage"
    assert (output / "DECISION_CURRENT").read_bytes() == pointer_a
    assert {path.name: path.read_bytes() for path in selected_a.set_dir.iterdir()} == set_a_bytes

    decisions_b = tmp_path / "queue-b-omissions.json"
    decisions_b.write_bytes(pretty_json_bytes(_omission_envelope(queue_b_path, queue_b)))
    imported_b = import_reviewed_omissions(
        review_queue_path=queue_b_path,
        decisions_path=decisions_b,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:01:00Z",
        nonce_factory=lambda: "b" * 32,
    )
    selected_b = resolve_current_reviewed_omissions(
        review_queue_path=queue_b_path,
        reviewed_omissions_root=output,
    )
    assert imported_b["status"] == "reviewed_omissions_complete"
    assert isinstance(selected_b, OmissionDecisionSetSnapshot)
    assert selected_b.decision_set_id != selected_a.decision_set_id
    assert selected_b.manifest["predecessor_decision_set_id"] == selected_a.decision_set_id
    assert selected_b.manifest["artifact_set_id"] == queue_b["artifact_set_id"]
    assert {path.name: path.read_bytes() for path in selected_a.set_dir.iterdir()} == set_a_bytes
    assert sorted(path.name for path in (output / "decision_sets").iterdir()) == sorted(
        [selected_a.decision_set_id, selected_b.decision_set_id]
    )

    selected_a.sidecar_path.write_bytes(selected_a.sidecar_path.read_bytes() + b"\n")
    with pytest.raises(MissionStateError) as corruption_error:
        resolve_current_reviewed_omissions(
            review_queue_path=queue_b_path,
            reviewed_omissions_root=output,
        )
    assert corruption_error.value.code == "omission_decision_manifest_mismatch"


def test_v2_omission_queue_change_supersedes_only_immediate_stale_orphan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_a_path, queue_a = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    first_path = tmp_path / "queue-a-first.json"
    first_path.write_bytes(pretty_json_bytes(_omission_envelope(queue_a_path, queue_a)))
    assert import_reviewed_omissions(
        review_queue_path=queue_a_path,
        decisions_path=first_path,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "c" * 32,
    )["status"] == "reviewed_omissions_complete"
    selected_a = resolve_current_reviewed_omissions(
        review_queue_path=queue_a_path,
        reviewed_omissions_root=output,
    )
    assert isinstance(selected_a, OmissionDecisionSetSnapshot)
    pointer_a = (output / "DECISION_CURRENT").read_bytes()

    orphan_envelope = _omission_envelope(queue_a_path, queue_a)
    orphan_envelope["decisions"][0]["reason"] = (
        "A complete queue-A successor is renamed before pointer replacement."
    )
    orphan_path = tmp_path / "queue-a-orphan.json"
    orphan_path.write_bytes(pretty_json_bytes(orphan_envelope))
    with pytest.raises(RuntimeError):
        import_reviewed_omissions(
            review_queue_path=queue_a_path,
            decisions_path=orphan_path,
            output_dir=output,
            force=True,
            now=lambda: "2026-07-12T01:01:00Z",
            nonce_factory=lambda: "d" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
            if label == "omission_set:after_final_rename"
            else None,
        )
    assert (output / "DECISION_CURRENT").read_bytes() == pointer_a
    set_dirs = sorted((output / "decision_sets").iterdir(), key=lambda path: path.name)
    assert len(set_dirs) == 2
    orphan_dir = next(path for path in set_dirs if path != selected_a.set_dir)
    orphan_before = {path.name: path.read_bytes() for path in orphan_dir.iterdir()}

    claim_path = mission / "public_source_packet" / "claim_support.json"
    claim_payload = json_load(claim_path)
    claim_payload["claim_candidates"][0]["next_action"] = (
        "Review queue B after the queue-A omission successor crash."
    )
    claim_path.write_bytes(pretty_json_bytes(claim_payload))
    changed = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        metadata_dir=mission / "public_metadata",
        source_status_dir=mission / "source_intake",
        anchor_dir=mission / "source_anchors",
        packet_dir=mission / "public_source_packet",
    )
    queue_b_path = Path(changed["review_queue_path"])
    queue_b = json_load(queue_b_path)
    decisions_b = tmp_path / "queue-b-after-orphan.json"
    decisions_b.write_bytes(pretty_json_bytes(_omission_envelope(queue_b_path, queue_b)))

    blocked = import_reviewed_omissions(
        review_queue_path=queue_b_path,
        decisions_path=decisions_b,
        output_dir=output,
        force=False,
        now=lambda: "2026-07-12T01:02:00Z",
        nonce_factory=lambda: "e" * 32,
    )
    assert blocked["status"] == "blocked"
    assert blocked["blocked_reason"] == "stale_lineage"
    assert (output / "DECISION_CURRENT").read_bytes() == pointer_a

    imported_b = import_reviewed_omissions(
        review_queue_path=queue_b_path,
        decisions_path=decisions_b,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:02:00Z",
        nonce_factory=lambda: "e" * 32,
    )
    selected_b = resolve_current_reviewed_omissions(
        review_queue_path=queue_b_path,
        reviewed_omissions_root=output,
    )
    assert imported_b["status"] == "reviewed_omissions_complete"
    assert isinstance(selected_b, OmissionDecisionSetSnapshot)
    orphan_manifest = json_load(orphan_dir / "decision_set_manifest.json")
    assert selected_b.manifest["predecessor_decision_set_id"] == orphan_manifest["decision_set_id"]
    assert selected_b.manifest["artifact_set_id"] == queue_b["artifact_set_id"]
    assert {path.name: path.read_bytes() for path in orphan_dir.iterdir()} == orphan_before
    assert len(list((output / "decision_sets").iterdir())) == 3


def test_v2_omission_stale_orphan_same_bytes_are_not_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_a_path, queue_a = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    decisions_a = tmp_path / "queue-a-orphan-same.json"
    decisions_a.write_bytes(pretty_json_bytes(_omission_envelope(queue_a_path, queue_a)))
    with pytest.raises(RuntimeError):
        import_reviewed_omissions(
            review_queue_path=queue_a_path,
            decisions_path=decisions_a,
            output_dir=output,
            now=lambda: "2026-07-12T01:00:00Z",
            nonce_factory=lambda: "f" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
            if label == "omission_set:after_final_rename"
            else None,
        )
    assert not (output / "DECISION_CURRENT").exists()

    claim_path = mission / "public_source_packet" / "claim_support.json"
    claim_payload = json_load(claim_path)
    claim_payload["claim_candidates"][0]["next_action"] = "Select queue B before retrying stale queue-A bytes."
    claim_path.write_bytes(pretty_json_bytes(claim_payload))
    changed = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        metadata_dir=mission / "public_metadata",
        source_status_dir=mission / "source_intake",
        anchor_dir=mission / "source_anchors",
        packet_dir=mission / "public_source_packet",
    )
    queue_b_path = Path(changed["review_queue_path"])
    context_b = load_selected_decision_context(
        review_queue_path=queue_b_path,
        decision_type="omission_risk",
    )
    with pytest.raises(MissionStateError) as error:
        OmissionDecisionStateManager(context=context_b, output_dir=output).compose_and_select(
            decisions_path=decisions_a,
            decisions_raw=decisions_a.read_bytes(),
            sidecar_payload={},
            force=True,
        )
    assert error.value.code == "stale_lineage"
    assert not (output / "DECISION_CURRENT").exists()


def test_v2_omission_current_orphan_cannot_be_superseded_or_skip_generations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    first_path = tmp_path / "orphan-depth-first.json"
    first_path.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    assert import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=first_path,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "1" * 32,
    )["status"] == "reviewed_omissions_complete"
    pointer_first = (output / "DECISION_CURRENT").read_bytes()

    second_envelope = _omission_envelope(queue_path, queue)
    second_envelope["decisions"][0]["reason"] = "Current-lineage orphan generation two."
    second_path = tmp_path / "orphan-depth-second.json"
    second_path.write_bytes(pretty_json_bytes(second_envelope))
    with pytest.raises(RuntimeError):
        import_reviewed_omissions(
            review_queue_path=queue_path,
            decisions_path=second_path,
            output_dir=output,
            force=True,
            now=lambda: "2026-07-12T01:01:00Z",
            nonce_factory=lambda: "2" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
            if label == "omission_set:after_final_rename"
            else None,
        )

    third_envelope = _omission_envelope(queue_path, queue)
    third_envelope["decisions"][0]["reason"] = "Different bytes cannot supersede a current orphan."
    third_path = tmp_path / "orphan-depth-third.json"
    third_path.write_bytes(pretty_json_bytes(third_envelope))
    blocked = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=third_path,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:02:00Z",
        nonce_factory=lambda: "3" * 32,
    )
    assert blocked["status"] == "blocked"
    assert blocked["blocked_reason"] == "stale_omission_decision_selector"
    assert (output / "DECISION_CURRENT").read_bytes() == pointer_first

    recovered = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=second_path,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:01:00Z",
        nonce_factory=lambda: "4" * 32,
    )
    assert recovered["status"] == "reviewed_omissions_complete"
    pointer_second = (output / "DECISION_CURRENT").read_bytes()

    with pytest.raises(RuntimeError):
        import_reviewed_omissions(
            review_queue_path=queue_path,
            decisions_path=third_path,
            output_dir=output,
            force=True,
            now=lambda: "2026-07-12T01:02:00Z",
            nonce_factory=lambda: "5" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
            if label == "omission_set:after_final_rename"
            else None,
        )
    (output / "DECISION_CURRENT").write_bytes(pointer_first)
    fourth_envelope = _omission_envelope(queue_path, queue)
    fourth_envelope["decisions"][0]["reason"] = "A deep pointer rollback cannot append generation four."
    fourth_path = tmp_path / "orphan-depth-fourth.json"
    fourth_path.write_bytes(pretty_json_bytes(fourth_envelope))
    deep = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=fourth_path,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:03:00Z",
        nonce_factory=lambda: "6" * 32,
    )
    assert deep["status"] == "blocked"
    assert deep["blocked_reason"] == "stale_omission_decision_selector"
    assert (output / "DECISION_CURRENT").read_bytes() == pointer_first
    assert pointer_second != pointer_first


def test_v2_merge_packet_and_hostile_review_require_current_omission_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    sidecars = _import_complete_v2_reviews(
        mission=mission,
        queue_path=queue_path,
        queue=queue,
        decisions_dir=tmp_path / "decisions",
    )
    merge = merge_reviewed_evidence(
        review_queue_path=queue_path,
        reviewed_claims_path=sidecars["claim_candidate"],
        reviewed_source_safety_path=sidecars["source_safety"],
        reviewed_omissions_path=sidecars["omission_risk"],
        reviewed_workflow_blockers_path=sidecars["workflow_blocker"],
        output_dir=mission / "reviewed_evidence",
    )
    merge_path = mission / "reviewed_evidence" / "reviewed_evidence_status.json"
    assert merge["status"] == "reviewed_evidence_complete"
    validated_merge = validate_reviewed_evidence_status(
        path=merge_path,
        review_queue_path=queue_path,
        sidecar_paths=sidecars,
    )
    assert validated_merge["reviewed_sidecars"]["omission_risk"]["path"] == str(
        sidecars["omission_risk"]
    )
    packet_result = compose_reviewed_final_packet(
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
        output_dir=mission / "reviewed_final_packet",
        now=lambda: "2026-07-12T03:00:00Z",
    )
    packet_path = mission / "reviewed_final_packet" / "reviewed_final_packet.json"
    assert packet_result["status"] == "reviewed_final_packet_ready_for_hostile_review"
    packet = validate_reviewed_final_packet(
        path=packet_path,
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
    )
    attempt_rows = [
        row for row in packet["omission_frontier_map"]
        if row.get("frontier_attempt_id")
    ]
    assert {row["direction"] for row in attempt_rows} == {"backward", "forward"}
    hostile_result = run_hostile_review_gate(
        reviewed_final_packet_path=packet_path,
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
        output_dir=mission / "hostile_review",
        now=lambda: "2026-07-12T03:01:00Z",
    )
    hostile_path = mission / "hostile_review" / "hostile_review_result.json"
    assert hostile_result["status"] in {
        "ready_for_reviewed_prose_within_recorded_scope",
        "blocked_for_reviewed_prose",
    }
    validate_hostile_review_result(
        path=hostile_path,
        reviewed_final_packet_path=packet_path,
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
    )

    replacement = _omission_envelope(queue_path, queue)
    for row in replacement["decisions"]:
        row["reason"] = "A complete replacement invalidates all prior descendants."
        if row["decision"] in {"must_inspect", "expand_scope", "blocked_pending_source"}:
            row["next_action"] = "Use only the new selected complete decision set."
        else:
            row["scope_basis"] = "New exact recorded fixture scope rationale."
    replacement_path = tmp_path / "replacement.json"
    replacement_path.write_bytes(pretty_json_bytes(replacement))
    assert import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=replacement_path,
        output_dir=mission / "reviewed_omissions",
        force=True,
        now=lambda: "2026-07-12T03:02:00Z",
        nonce_factory=lambda: "b" * 32,
    )["status"] == "reviewed_omissions_complete"
    with pytest.raises(MissionStateError):
        validate_reviewed_evidence_status(
            path=merge_path,
            review_queue_path=queue_path,
            sidecar_paths=sidecars,
        )
    with pytest.raises(MissionStateError):
        validate_reviewed_final_packet(
            path=packet_path,
            mission_root=mission,
            review_queue_path=queue_path,
            packet_dir=mission / "public_source_packet",
            anchor_dir=mission / "source_anchors",
        )


@pytest.mark.parametrize(
    "crash_at",
    [
        "omission_set:after_staging_parent_fsync",
        "omission_set:reviewed_omission_decisions.json:after_write",
        "omission_set:reviewed_omission_decisions.json:after_fsync",
        "omission_set:reviewed_omission_risks.json:after_write",
        "omission_set:reviewed_omission_risks.json:after_fsync",
        "omission_set:decision_set_manifest.json:after_write",
        "omission_set:decision_set_manifest.json:after_fsync",
        "omission_set:after_staging_fsync",
        "omission_set:after_final_rename",
        "omission_set:after_sets_fsync",
    ],
)
def test_v2_omission_set_crash_boundaries_retry_deterministically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_at: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    decisions = tmp_path / "decisions.json"
    decisions.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    context = load_selected_decision_context(
        review_queue_path=queue_path,
        decision_type="omission_risk",
    )
    _, raw = __import__("research_assistant.survey.review_decisions", fromlist=["read_json_object_strict"]).read_json_object_strict(
        decisions,
        label="fixture decisions",
    )
    from research_assistant.survey.review_decisions import common_sidecar_fields, validate_exact_decisions

    rows = json_load(decisions)["decisions"]
    result = validate_exact_decisions(context=context, rows=rows, validator=validate_omission_decision)
    payload = {
        "schema_version": "ra-survey-reviewed-omission-risks-v2",
        **common_sidecar_fields(
            context=context,
            decisions_path=decisions,
            decisions_raw=raw,
            result=result,
            created_at="2026-07-12T01:00:00Z",
        ),
        "omission_risks": result.accepted,
        "rejected_omission_risks": result.rejected,
        "coverage_errors": result.coverage_errors,
        "status": "reviewed_omissions_complete",
        "accepted_omission_count": len(result.accepted),
        "rejected_omission_count": 0,
        "closed_omission_count": sum(row["status"] == "reviewed_closed_for_current_scope" for row in result.accepted),
        "open_omission_count": sum(row["status"] == "open" for row in result.accepted),
        "literature_completeness_allowed": False,
        "what_is_not_concluded": [
            "literature completeness",
            "final prose readiness",
            "live web coverage",
            "product readiness",
            "real-agent reliability",
            "scientific correctness",
        ],
    }
    crashing = OmissionDecisionStateManager(
        context=context,
        output_dir=output,
        nonce_factory=lambda: "5" * 32,
        crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label)) if label == crash_at else None,
    )
    with pytest.raises(RuntimeError):
        crashing.compose_and_select(
            decisions_path=decisions,
            decisions_raw=raw,
            sidecar_payload=payload,
        )
    retry = OmissionDecisionStateManager(
        context=context,
        output_dir=output,
        nonce_factory=lambda: "6" * 32,
    ).compose_and_select(
        decisions_path=decisions,
        decisions_raw=raw,
        sidecar_payload=payload,
    )
    assert retry.sidecar_path.is_file()
    assert retry.decisions_path.is_file()


@pytest.mark.parametrize(
    "crash_at",
    [
        "omission_current:after_temp_write",
        "omission_current:after_temp_fsync",
        "omission_current:after_replace",
        "omission_current:after_directory_fsync",
    ],
)
def test_v2_omission_selector_crash_boundaries_expose_only_complete_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_at: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    decisions = tmp_path / "decisions.json"
    decisions.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    with pytest.raises(RuntimeError):
        import_reviewed_omissions(
            review_queue_path=queue_path,
            decisions_path=decisions,
            output_dir=output,
            now=lambda: "2026-07-12T01:00:00Z",
            nonce_factory=lambda: "7" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label)) if label == crash_at else None,
        )
    if crash_at in {"omission_current:after_replace", "omission_current:after_directory_fsync"}:
        selected = resolve_current_reviewed_omissions(
            review_queue_path=queue_path,
            reviewed_omissions_root=output,
        )
        assert isinstance(selected, OmissionDecisionSetSnapshot)
    else:
        retried = import_reviewed_omissions(
            review_queue_path=queue_path,
            decisions_path=decisions,
            output_dir=output,
            force=True,
            now=lambda: "2026-07-12T01:00:00Z",
            nonce_factory=lambda: "8" * 32,
        )
        assert retried["status"] == "reviewed_omissions_complete"


@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("malformed_pointer", "invalid_json"),
        ("foreign_pointer", "unsafe_omission_decision_set"),
        ("symlink_pointer", "unsafe_omission_decision_root"),
        ("symlink_set", "unsafe_omission_decision_set"),
        ("symlink_artifact", "unsafe_omission_decision_artifact"),
        ("unexpected_root_child", "unexpected_omission_decision_path"),
        ("unexpected_set_child", "unexpected_omission_decision_set_path"),
    ],
)
def test_v2_omission_selector_attack_matrix_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    expected_code: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    decisions = tmp_path / "decisions.json"
    decisions.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    assert import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "c" * 32,
    )["status"] == "reviewed_omissions_complete"
    selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert isinstance(selected, OmissionDecisionSetSnapshot)

    if attack == "malformed_pointer":
        (output / "DECISION_CURRENT").write_bytes(b"{")
    elif attack == "foreign_pointer":
        pointer = {
            "schema_version": "ra-survey-omission-decision-current-v1",
            "decision_set_id": "od-" + "f" * 64,
            "decision_set_manifest_sha256": "e" * 64,
        }
        (output / "DECISION_CURRENT").write_bytes(canonical_json_bytes(pointer))
    elif attack == "symlink_pointer":
        pointer = output / "DECISION_CURRENT"
        outside = tmp_path / "outside-pointer.json"
        outside.write_bytes(pointer.read_bytes())
        pointer.unlink()
        pointer.symlink_to(outside)
    elif attack == "symlink_set":
        outside = tmp_path / "outside-set"
        selected.set_dir.rename(outside)
        selected.set_dir.symlink_to(outside, target_is_directory=True)
    elif attack == "symlink_artifact":
        outside = tmp_path / "outside-sidecar.json"
        outside.write_bytes(selected.sidecar_path.read_bytes())
        selected.sidecar_path.unlink()
        selected.sidecar_path.symlink_to(outside)
    elif attack == "unexpected_root_child":
        (output / "unexpected.json").write_bytes(b"{}")
    elif attack == "unexpected_set_child":
        (selected.set_dir / "unexpected.json").write_bytes(b"{}")
    else:  # pragma: no cover - parametrization is closed above.
        raise AssertionError(attack)

    with pytest.raises(MissionStateError) as error:
        resolve_current_reviewed_omissions(
            review_queue_path=queue_path,
            reviewed_omissions_root=output,
        )
    assert error.value.code == expected_code


def test_v2_omission_conflicting_existing_set_bytes_are_not_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    decisions = tmp_path / "decisions.json"
    decisions.write_bytes(pretty_json_bytes(_omission_envelope(queue_path, queue)))
    assert import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "d" * 32,
    )["status"] == "reviewed_omissions_complete"
    selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert isinstance(selected, OmissionDecisionSetSnapshot)
    selected.sidecar_path.write_bytes(selected.sidecar_path.read_bytes() + b"\n")

    result = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "e" * 32,
    )
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "omission_decision_manifest_mismatch"
    with pytest.raises(MissionStateError):
        resolve_current_reviewed_omissions(
            review_queue_path=queue_path,
            reviewed_omissions_root=output,
        )


def test_incomplete_v2_omission_envelope_creates_no_selected_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_omissions"
    envelope = _omission_envelope(queue_path, queue)
    envelope["decisions"].pop()
    decisions = tmp_path / "incomplete.json"
    decisions.write_bytes(pretty_json_bytes(envelope))

    result = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "f" * 32,
    )
    assert result["status"] == "blocked_invalid_omission_decisions"
    assert result["decision_coverage_complete"] is False
    assert result["reviewed_omission_risks_path"] is None
    assert not output.exists()


def test_unchanged_expand_scope_decision_remains_open_and_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    risk = next(
        item
        for item in queue["items"]
        if item["queue_type"] == "omission_risk"
        and "expand_scope" in V2_OMISSION_TRANSITIONS[item["machine_disposition"]]
    )
    envelope = _omission_envelope(
        queue_path,
        queue,
        decision_for={risk["risk_id"]: "expand_scope"},
    )
    decisions = tmp_path / "expand-scope.json"
    decisions.write_bytes(pretty_json_bytes(envelope))
    output = mission / "reviewed_omissions"

    first = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "1" * 32,
    )
    replay = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T01:00:00Z",
        nonce_factory=lambda: "2" * 32,
    )
    selected = resolve_current_reviewed_omissions(
        review_queue_path=queue_path,
        reviewed_omissions_root=output,
    )
    assert first["reviewed_omission_risks_path"] == replay["reviewed_omission_risks_path"]
    assert isinstance(selected, OmissionDecisionSetSnapshot)
    row = next(
        item
        for item in json_load(selected.sidecar_path)["omission_risks"]
        if item["risk_id"] == risk["risk_id"]
    )
    assert row["decision"] == "expand_scope"
    assert row["status"] == "open"
    assert row["regeneration_required"] is True
    assert row["literature_completeness_allowed"] is False
    assert row["ready_for_prose"] is False
