from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import test_literature_survey_m16_phase8 as phase8_fixture_module

from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.evidence_semantics import ImmutableAuthorityManager
from research_assistant.survey.claim_review import (
    CLAIM_DECISION_CONFIG,
    CLAIM_NONSUPPORT_MATRIX,
    CLAIM_REVIEW_STATUSES,
    CLAIM_SUPPORT_MATRIX,
    REVIEWED_CLAIM_NONCLAIMS,
    SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
    SURVEY_CLAIM_REVIEW_V3_SCHEMA,
    _reachable_manifest_ids,
    _validate_dependency_graph,
    _validate_v3_claim_row,
    import_reviewed_claims,
    resolve_current_reviewed_claims,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.omission_review import import_reviewed_omissions
from research_assistant.survey.reviewed_packet import compose_reviewed_final_packet
from research_assistant.survey.hostile_review import run_hostile_review_gate
import research_assistant.survey.reviewed_merge as reviewed_merge_module
from research_assistant.survey.reviewed_merge import (
    merge_reviewed_evidence,
    validate_reviewed_evidence_status,
)
from research_assistant.survey.source_safety_review import (
    REVIEWED_SOURCE_SAFETY_NONCLAIMS,
    SOURCE_CHECKS,
    SOURCE_NOTICE_TYPES,
    SOURCE_OBSERVATION_NONCLAIMS,
    SOURCE_OUTCOMES,
    SOURCE_REVIEWER_AUTHORITIES,
    SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
    SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
    SOURCE_DECISION_CONFIG,
    SOURCE_OBSERVATION_CONFIG,
    import_reviewed_source_safety,
    preview_source_observation_binding,
    resolve_current_source_safety,
)
from test_literature_survey_m16_phase8 import (
    _bound_envelope,
    _canonical_v2_mission,
    _import_complete_v2_reviews,
    _omission_envelope,
    _records,
    json_load,
)
from research_assistant.survey.source_intake import SourceCapabilityResult


AUTHORITY_CONFIGS = [SOURCE_OBSERVATION_CONFIG, SOURCE_DECISION_CONFIG, CLAIM_DECISION_CONFIG]


def _authority_crash_cases():
    cases = []
    for config in AUTHORITY_CONFIGS:
        suffixes = ["after_staging_parent_fsync"]
        for name in [*sorted(config.artifacts), config.manifest_name]:
            suffixes.extend([f"{name}:after_write", f"{name}:after_fsync"])
        suffixes.extend([
            "after_staging_fsync",
            "after_final_rename",
            "after_sets_fsync",
            "current:after_temp_write",
            "current:after_temp_fsync",
            "current:after_replace",
            "current:after_directory_fsync",
        ])
        cases.extend((config, suffix) for suffix in suffixes)
    return cases


def _authority_identity(config, *, marker: str, predecessor=None) -> dict:
    predecessor_id = predecessor.set_id if predecessor is not None else None
    predecessor_hash = (
        sha256_bytes((predecessor.set_dir / config.manifest_name).read_bytes())
        if predecessor is not None
        else None
    )
    return {
        field: (
            predecessor_id
            if field == config.predecessor_id_field
            else predecessor_hash
            if field == config.predecessor_manifest_field
            else False
            if field == "fixture_only"
            else 1
            if field.endswith("_size_bytes")
            else []
            if field in {"source_record_digests", "what_is_not_concluded"}
            else sha256_bytes(f"{field}:{marker}".encode())
            if field.endswith("sha256") or field == "mission_fingerprint"
            else marker
        )
        for field in config.identity_fields
    }


def _authority_artifacts(config, *, marker: str) -> dict[str, bytes]:
    return {
        name: pretty_json_bytes({
            "schema_version": "fixture-artifact-v1",
            "name": name,
            "marker": marker,
        })
        for name in config.artifacts
    }


def _materialize_authority_set(
    *,
    root: Path,
    config,
    set_id: str,
    manifest: dict,
    artifacts: dict[str, bytes],
) -> Path:
    directory = root / config.sets_dir_name / set_id
    directory.mkdir()
    for name, raw in artifacts.items():
        (directory / name).write_bytes(raw)
    (directory / config.manifest_name).write_bytes(canonical_json_bytes(manifest))
    return directory


def _observation_set(
    queue_path: Path,
    *,
    outcome: str = "checked_clear_for_recorded_checks",
) -> dict:
    context = load_v2_evidence_context(queue_path)
    status = context.validated_source_intake["status"]
    status_raw = context.validated_source_intake["status_bytes"]
    ledger_path = Path(status["outcome_ledger_path"])
    rows = []
    for item_id, identity in sorted(context.source_identities.items()):
        notices = [] if outcome == "checked_clear_for_recorded_checks" else [{
            "notice_type": SOURCE_NOTICE_TYPES[outcome],
            "source": "synthetic fixture status registry",
            "observed_at": "2026-07-12T04:00:00Z",
            "detail": f"Synthetic {outcome} notice for engineering state-transition tests only.",
        }]
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
            "observed_at": "2026-07-12T04:00:00Z",
            "checks_performed": SOURCE_CHECKS,
            "outcome": outcome,
            "notices": notices,
            "fixture_only": True,
            "claim_support_allowed": False,
            "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        }
        digest = sha256_bytes(canonical_json_bytes(semantic))
        rows.append({
            "observation_id": f"so-{digest}",
            "observation_sha256": digest,
            **{key: value for key, value in semantic.items() if key != "schema_version"},
        })
    return {
        "schema_version": SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
        **context.binding,
        "source_intake_status_path": str(context.mission_root / "source_intake" / "phase4_source_intake_status.json"),
        "source_intake_status_sha256": sha256_bytes(status_raw),
        "source_intake_status_size_bytes": len(status_raw),
        "source_outcome_ledger_path": str(ledger_path),
        "source_outcome_ledger_sha256": sha256_bytes(ledger_path.read_bytes()),
        "source_outcome_ledger_size_bytes": ledger_path.stat().st_size,
        "fixture_only": True,
        "observations": rows,
        "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        "predecessor_observation_set_id": None,
        "predecessor_observation_set_manifest_sha256": None,
    }


def _v3_source_envelope(
    queue_path: Path,
    output_dir: Path,
    *,
    reviewer_authority: str = "human_reviewed_status",
    decision: str = "checked_clear",
    observation_outcome: str = "checked_clear_for_recorded_checks",
) -> dict:
    context = load_v2_evidence_context(queue_path)
    observation_set = _observation_set(queue_path, outcome=observation_outcome)
    binding = preview_source_observation_binding(
        review_queue_path=queue_path,
        observation_set=observation_set,
        output_dir=output_dir,
    )
    decisions = []
    observations = {row["queue_item_id"]: row for row in observation_set["observations"]}
    for item_id, identity in sorted(context.source_identities.items()):
        observation = observations[item_id]
        row = {
            "queue_item_id": item_id,
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "observation_set_id": binding["observation_set_id"],
            "observation_set_manifest_sha256": binding["observation_set_manifest_sha256"],
            "observation_id": observation["observation_id"],
            "observation_sha256": observation["observation_sha256"],
            "source_version": identity.source_version,
            "reviewer_authority": reviewer_authority,
            "decision": decision,
            "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-12T04:01:00Z",
            "reason": "Synthetic fixture decision for engineering state-transition tests only.",
            "fixture_only": True,
        }
        if decision == "blocked":
            row["next_action"] = "Obtain an exact current human-shaped source-status decision."
        decisions.append(row)
    return {
        "schema_version": SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
        "decision_type": "source_safety",
        **context.binding,
        "observation_set": observation_set,
        "decisions": decisions,
    }


def _v3_claim_envelope(
    queue_path: Path,
    *,
    review_status: str = "human_reviewed_passed",
) -> dict:
    context = load_v2_evidence_context(queue_path)
    queue_item = next(
        row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate"
    )
    identities = sorted(context.source_identities.values(), key=lambda row: row.source_paper_id)
    dependencies = [
        {
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "canonical_identifier": identity.canonical_identifier,
            "source_version": identity.source_version,
            "source_record_sha256": identity.source_record_sha256,
            "dependency_role": "primary_technical_source",
        }
        for identity in identities
        if identity.source_paper_id in queue_item["paper_ids"]
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
    graph_projection = {
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
            "queue_item_id": queue_item["item_id"],
            "claim_id": "fixture-reviewed-technical-claim",
            "claim_text": "The exact fixture source contains the recorded Method section.",
            "claim_type": "paper_technical",
            "support_class": "primary_technical_support",
            "review_status": review_status,
            "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-12T04:03:00Z",
            "evidence_note": "Synthetic fixture review for engineering state-transition tests only.",
            "fixture_only": True,
            "source_dependencies": dependencies,
            "dependency_manifests": manifests,
            "root_dependency_manifest_id": manifest_id,
            "dependency_graph_sha256": sha256_bytes(canonical_json_bytes(graph_projection)),
            "paper_ids": queue_item["paper_ids"],
            "anchor_ids": queue_item["anchor_ids"],
        }],
    }


def _v3_local_claim_envelope(
    queue_path: Path,
    *,
    support_class: str,
    local_artifact: Path,
) -> dict:
    context = load_v2_evidence_context(queue_path)
    queue_item = next(
        row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate"
    )
    role = {
        "project_derivation": "project_derivation_source",
        "implementation_evidence": "implementation_evidence_source",
    }[support_class]
    claim_type = {
        "project_derivation": "project_mathematical_derivation",
        "implementation_evidence": "implementation_behavior",
    }[support_class]
    dependencies = [
        {
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "canonical_identifier": identity.canonical_identifier,
            "source_version": identity.source_version,
            "source_record_sha256": identity.source_record_sha256,
            "dependency_role": role,
        }
        for identity in sorted(context.source_identities.values(), key=lambda row: row.source_paper_id)
    ]
    relative = str(local_artifact.relative_to(context.mission_root))
    manifest_projection = {
        "schema_version": SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        "evidence_kind": support_class,
        "local_artifact": relative,
        "local_artifact_sha256": sha256_bytes(local_artifact.read_bytes()),
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
    decision = {
        "queue_item_id": queue_item["item_id"],
        "claim_id": f"fixture-{support_class}",
        "claim_text": "The exact mission-local fixture records this bounded project evidence.",
        "claim_type": claim_type,
        "support_class": support_class,
        "review_status": "human_reviewed_passed",
        "reviewer": "synthetic-fixture-reviewer",
        "reviewed_at": "2026-07-12T04:03:00Z",
        "evidence_note": "Synthetic fixture review for engineering state-transition tests only.",
        "fixture_only": True,
        "source_dependencies": dependencies,
        "dependency_manifests": manifests,
        "root_dependency_manifest_id": manifest_id,
        "dependency_graph_sha256": sha256_bytes(canonical_json_bytes(graph)),
    }
    if support_class == "project_derivation":
        decision["derivation_id"] = "fixture-project-derivation"
    return {
        "schema_version": SURVEY_CLAIM_REVIEW_V3_SCHEMA,
        "decision_type": "claim_candidate",
        **context.binding,
        "decisions": [decision],
    }


def _v3_nonsupport_claim_envelope(
    queue_path: Path,
    *,
    support_class: str,
) -> dict:
    context = load_v2_evidence_context(queue_path)
    queue_item = next(
        row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate"
    )
    return {
        "schema_version": SURVEY_CLAIM_REVIEW_V3_SCHEMA,
        "decision_type": "claim_candidate",
        **context.binding,
        "decisions": [{
            "queue_item_id": queue_item["item_id"],
            "claim_id": f"fixture-{support_class}",
            "claim_text": "This fixture row remains visible without authorizing technical support.",
            "claim_type": CLAIM_NONSUPPORT_MATRIX[support_class],
            "support_class": support_class,
            "review_status": "human_reviewed_passed",
            "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-12T04:03:00Z",
            "evidence_note": "Synthetic fixture review for engineering state-transition tests only.",
            "fixture_only": True,
            "reason": "The row does not meet a supporting evidence class.",
            "next_action": "Obtain exact supporting evidence or retain the blocker.",
        }],
    }


def _dependency_manifest(
    *,
    support_class: str,
    local_artifact: str,
    local_artifact_sha256: str,
    direct_source_paper_ids: list[str],
    referenced_manifest_ids: list[str],
) -> dict:
    projection = {
        "schema_version": SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        "evidence_kind": support_class,
        "local_artifact": local_artifact,
        "local_artifact_sha256": local_artifact_sha256,
        "direct_source_paper_ids": sorted(direct_source_paper_ids),
        "referenced_manifest_ids": sorted(referenced_manifest_ids),
    }
    return {
        "manifest_id": f"dm-{sha256_bytes(canonical_json_bytes(projection))}",
        **projection,
    }


def _dependency_graph_value(
    *,
    source_dependencies: list[dict],
    dependency_manifests: list[dict],
    root_dependency_manifest_id: str,
) -> dict:
    manifests = sorted(dependency_manifests, key=lambda row: row["manifest_id"])
    dependencies = sorted(source_dependencies, key=lambda row: row["source_paper_id"])
    projection = {
        "schema_version": "ra-survey-claim-dependency-graph-v1",
        "root_dependency_manifest_id": root_dependency_manifest_id,
        "dependency_manifests": manifests,
        "source_dependencies": dependencies,
    }
    return {
        **projection,
        "dependency_graph_sha256": sha256_bytes(canonical_json_bytes(projection)),
    }


def test_v2_source_context_joins_both_paper_namespaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    context = load_v2_evidence_context(queue_path)

    assert context.mission_root == mission.absolute()
    assert len(context.source_identities) == 1
    identity = next(iter(context.source_identities.values()))
    assert identity.stable_metadata_paper_id.startswith("p_dq_")
    assert identity.source_paper_id.startswith("paper_")
    assert identity.stable_metadata_paper_id != identity.source_paper_id
    assert identity.aliases == sorted(set(identity.aliases))
    assert identity.source_version == f"record-sha256:{identity.source_record_sha256}"


def test_v2_source_context_accepts_versioned_arxiv_canonical_identifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(phase8_fixture_module, "SEED", "arxiv:2201.12220v3")
    record = deepcopy(_records()[0])
    record.update({
        "arxiv_id": "2201.12220v3",
        "providers": ["arxiv", "openalex"],
        "provider_records": [
            {
                "provider": "arxiv",
                "query_kind": "seed_resolution",
                "source_id": "2201.12220v3",
                "primary_category": "cs.LG",
                "published": "2022-01-01",
            },
            {
                **record["provider_records"][0],
                "query_kind": "topic_search",
            },
        ],
        "query_provenance": [
            {
                "provider": "arxiv",
                "query_kind": "seed_resolution",
                "normalized_seed_key": "arxiv:2201.12220v3",
                "topic_query": False,
            },
            {
                "provider": "openalex",
                "query_kind": "topic_search",
                "normalized_seed_key": None,
                "topic_query": True,
            },
        ],
    })

    def arxiv_source(request) -> SourceCapabilityResult:
        final_url = "https://arxiv.org/abs/2201.12220v3"
        source = {
            "paper_id": request.paper_id,
            "source_type": "arxiv_latex",
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
                "raw_latex": "Fixture-only versioned arXiv source.",
            }],
            "equations": [],
            "theorem_like_blocks": [],
            "labels": [],
            "references": [],
            "citations": [],
            "bibliography": [],
            "macros": [],
            "provenance": {
                "arxiv_id": "2201.12220v3",
                "identifier": request.identifier,
                "provider": "arxiv",
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
            provider="arxiv",
            final_url=final_url,
            structured_record=source,
            byte_count=len(pretty_json_bytes(source)),
        )

    _, queue_path, _ = _canonical_v2_mission(
        tmp_path,
        monkeypatch,
        fixture_records=[record],
        source_handler=arxiv_source,
    )
    identity = next(iter(load_v2_evidence_context(queue_path).source_identities.values()))

    assert identity.canonical_identifier == "arxiv:2201.12220v3"
    assert "arxiv:2201.12220" in identity.aliases
    assert identity.canonical_identifier not in identity.aliases


def test_v1_source_envelope_cannot_authorize_v2_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    item = next(row for row in queue["items"] if row["queue_type"] == "source_safety")
    decisions = tmp_path / "legacy-safety.json"
    decisions.write_bytes(pretty_json_bytes(_bound_envelope(
        queue_path,
        queue,
        "source_safety",
        [{
            "queue_item_id": item["item_id"],
            "paper_id": item["paper_id"],
            "checked_status": "checked_clear",
            "evidence_type": "public_status_check",
            "evidence_source": "free text is not V3 observation authority",
            "reviewer": "fixture-reviewer",
            "reviewed_at": "2026-07-12T04:00:00Z",
            "evidence_note": "legacy fixture",
        }],
    )))

    result = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=mission / "reviewed_source_safety",
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "legacy_source_review_cannot_authorize_v2"
    assert not (mission / "reviewed_source_safety").exists()


def test_v3_source_authority_writes_reuses_and_replays_immutable_sets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_source_safety"
    envelope = _v3_source_envelope(queue_path, output)
    decisions = tmp_path / "source-v3.json"
    decisions.write_bytes(pretty_json_bytes(envelope))

    first = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        now=lambda: "2026-07-12T04:02:00Z",
        nonce_factory=lambda: "1" * 32,
    )
    observation, decision, sidecar = resolve_current_source_safety(
        review_queue_path=queue_path,
        reviewed_source_safety_root=output,
    )
    before = {path.name: path.read_bytes() for path in decision.set_dir.iterdir()}
    pointers = {
        "observation": (output / "OBSERVATION_CURRENT").read_bytes(),
        "decision": (output / "DECISION_CURRENT").read_bytes(),
    }

    replay = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T05:00:00Z",
        nonce_factory=lambda: "2" * 32,
    )
    observation2, decision2, sidecar2 = resolve_current_source_safety(
        review_queue_path=queue_path,
        reviewed_source_safety_root=output,
    )

    assert first["status"] == replay["status"] == "reviewed_source_safety_complete"
    assert observation2.set_id == observation.set_id
    assert decision2.set_id == decision.set_id
    assert sidecar2 == sidecar
    assert sidecar["created_at"] == "2026-07-12T04:02:00Z"
    assert {path.name: path.read_bytes() for path in decision2.set_dir.iterdir()} == before
    assert (output / "OBSERVATION_CURRENT").read_bytes() == pointers["observation"]
    assert (output / "DECISION_CURRENT").read_bytes() == pointers["decision"]
    assert sidecar["what_is_not_concluded"] == REVIEWED_SOURCE_SAFETY_NONCLAIMS
    assert sidecar["source_safety"][0]["claim_support_allowed"] is True


@pytest.mark.parametrize(
    "suffix",
    [
        "reviewed_source_safety.json:after_write",
        "reviewed_source_safety.json:after_fsync",
        "decision_set_manifest.json:after_write",
        "decision_set_manifest.json:after_fsync",
        "after_staging_fsync",
    ],
)
def test_v3_source_decision_crash_retry_preserves_staged_created_at(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_source_safety"
    path = tmp_path / "source-v3-crash.json"
    path.write_bytes(pretty_json_bytes(_v3_source_envelope(queue_path, output)))
    crash_at = f"source_decision:{suffix}"

    with pytest.raises(RuntimeError, match=crash_at):
        import_reviewed_source_safety(
            review_queue_path=queue_path,
            decisions_path=path,
            output_dir=output,
            now=lambda: "2026-07-12T04:02:00Z",
            nonce_factory=lambda: "5" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
            if label == crash_at
            else None,
        )

    retry = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
        now=lambda: "2026-07-12T09:09:09Z",
        nonce_factory=lambda: "6" * 32,
    )
    _, _, sidecar = resolve_current_source_safety(
        review_queue_path=queue_path,
        reviewed_source_safety_root=output,
    )
    assert retry["status"] == "reviewed_source_safety_complete"
    assert sidecar["created_at"] == "2026-07-12T04:02:00Z"


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        (
            lambda envelope: envelope["decisions"][0].update(
                reviewer_authority="model_reviewed_advisory"
            ),
            "unauthorized_checked_clear",
        ),
        (
            lambda envelope: envelope["observation_set"]["observations"][0].update(
                evidence_class="metadata_availability"
            ),
            "invalid_source_observation_evidence",
        ),
        (
            lambda envelope: envelope["observation_set"]["observations"][0].update(
                stable_metadata_paper_id=envelope["observation_set"]["observations"][0]["source_paper_id"]
            ),
            "source_observation_identity_mismatch",
        ),
    ],
)
def test_v3_source_forbidden_promotions_create_no_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutator,
    expected_reason: str,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_source_safety"
    envelope = _v3_source_envelope(queue_path, output)
    mutator(envelope)
    decisions = tmp_path / "invalid-source-v3.json"
    decisions.write_bytes(pretty_json_bytes(envelope))

    result = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=decisions,
        output_dir=output,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == expected_reason
    assert not output.exists()


@pytest.mark.parametrize("attack", ["missing", "duplicate"])
def test_v3_source_decisions_must_exactly_cover_observation_queue_universe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_source_safety"
    envelope = _v3_source_envelope(queue_path, output)
    if attack == "missing":
        envelope["decisions"] = []
    else:
        envelope["decisions"].append(deepcopy(envelope["decisions"][0]))
    path = tmp_path / f"source-{attack}.json"
    path.write_bytes(pretty_json_bytes(envelope))

    result = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "incomplete_source_decisions"
    assert not output.exists()


@pytest.mark.parametrize("observation_outcome", sorted(SOURCE_OUTCOMES))
@pytest.mark.parametrize("reviewer_authority", sorted(SOURCE_REVIEWER_AUTHORITIES))
@pytest.mark.parametrize("decision", ["blocked", "checked_clear", "quarantined"])
def test_v3_source_outcome_authority_decision_matrix_is_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_outcome: str,
    reviewer_authority: str,
    decision: str,
) -> None:
    assert len(SOURCE_OUTCOMES) == 7
    assert len(SOURCE_REVIEWER_AUTHORITIES) == 4
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_source_safety"
    envelope = _v3_source_envelope(
        queue_path,
        output,
        reviewer_authority=reviewer_authority,
        decision=decision,
        observation_outcome=observation_outcome,
    )
    path = tmp_path / "source-matrix.json"
    path.write_bytes(pretty_json_bytes(envelope))

    result = import_reviewed_source_safety(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
    )

    valid = (
        decision == "blocked"
        or (
            reviewer_authority == "human_reviewed_status"
            and decision == "checked_clear"
            and observation_outcome == "checked_clear_for_recorded_checks"
        )
        or (
            reviewer_authority == "human_reviewed_status"
            and decision == "quarantined"
            and observation_outcome != "checked_clear_for_recorded_checks"
        )
    )
    if valid:
        assert result["status"] == "reviewed_source_safety_complete"
        _, _, sidecar = resolve_current_source_safety(
            review_queue_path=queue_path,
            reviewed_source_safety_root=output,
        )
        row = sidecar["source_safety"][0]
        assert row["observation_outcome"] == observation_outcome
        assert row["reviewer_authority"] == reviewer_authority
        assert row["decision"] == decision
        assert row["claim_support_allowed"] is (
            decision == "checked_clear"
        )
        return

    assert result["status"] == "blocked"
    if decision == "checked_clear":
        assert result["blocked_reason"] == "unauthorized_checked_clear"
    elif decision == "quarantined":
        assert result["blocked_reason"] == "invalid_source_quarantine"
    else:  # pragma: no cover - the validity predicate accepts every blocked cell.
        raise AssertionError("unexpected invalid blocked source-decision cell")
    assert not output.exists()


def test_quarantine_closure_shaped_omission_input_is_rejected_without_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(
        tmp_path,
        monkeypatch,
        seed_referenced_works=["W999"],
    )
    envelope = _omission_envelope(queue_path, queue)
    row = next(
        value
        for value in envelope["decisions"]
        if next(
            item for item in queue["items"]
            if item["queue_type"] == "omission_risk" and item["risk_id"] == value["risk_id"]
        )["machine_disposition"] == "quarantine"
    )
    row.update({
        "decision": "acceptable_omission",
        "scope_basis": "A source decision alone cannot authorize omission.",
        "source_observation_set_id": "ss-" + "1" * 64,
        "pending_exact_source_join": True,
    })
    row.pop("next_action", None)
    path = tmp_path / "closure-shaped-omission.json"
    path.write_bytes(pretty_json_bytes(envelope))

    result = import_reviewed_omissions(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=mission / "reviewed_omissions",
    )

    assert result["status"] == "blocked_invalid_omission_decisions"
    assert result["decision_coverage_complete"] is False
    assert not (mission / "reviewed_omissions").exists()


def test_v1_claim_envelope_cannot_authorize_v2_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    item = next(row for row in queue["items"] if row["queue_type"] == "claim_candidate")
    path = tmp_path / "legacy-claim.json"
    path.write_bytes(pretty_json_bytes(_bound_envelope(
        queue_path,
        queue,
        "claim_candidate",
        [{
            "queue_item_id": item["item_id"],
            "claim_id": "legacy",
            "claim_text": "Legacy claim cannot authorize V2.",
            "review_status": "human_reviewed_passed",
            "support_class": "primary_technical_support",
            "paper_ids": item["paper_ids"],
            "anchor_ids": item["anchor_ids"],
            "reviewer": "fixture",
            "reviewed_at": "2026-07-12T04:03:00Z",
            "evidence_note": "legacy",
        }],
    )))

    result = import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=mission / "reviewed_claims",
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "legacy_claim_review_cannot_authorize_v2"
    assert not (mission / "reviewed_claims").exists()


def test_v3_claim_authority_replays_graph_anchors_and_immutable_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_claims"
    envelope = _v3_claim_envelope(queue_path)
    path = tmp_path / "claim-v3.json"
    path.write_bytes(pretty_json_bytes(envelope))

    first = import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
        now=lambda: "2026-07-12T04:04:00Z",
        nonce_factory=lambda: "3" * 32,
    )
    snapshot, sidecar = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=output,
    )
    before = {child.name: child.read_bytes() for child in snapshot.set_dir.iterdir()}
    pointer = (output / "DECISION_CURRENT").read_bytes()

    replay = import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
        force=True,
        now=lambda: "2026-07-12T05:00:00Z",
        nonce_factory=lambda: "4" * 32,
    )
    snapshot2, sidecar2 = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=output,
    )

    assert first["status"] == replay["status"] == "reviewed_claims_complete"
    assert snapshot2.set_id == snapshot.set_id
    assert sidecar2 == sidecar
    assert sidecar["created_at"] == "2026-07-12T04:04:00Z"
    assert sidecar["claims"][0]["claim_support_allowed"] is True
    assert sidecar["what_is_not_concluded"] == REVIEWED_CLAIM_NONCLAIMS
    assert {child.name: child.read_bytes() for child in snapshot2.set_dir.iterdir()} == before
    assert (output / "DECISION_CURRENT").read_bytes() == pointer


@pytest.mark.parametrize(
    "suffix",
    [
        "reviewed_claims.json:after_write",
        "reviewed_claims.json:after_fsync",
        "decision_set_manifest.json:after_write",
        "decision_set_manifest.json:after_fsync",
        "after_staging_fsync",
    ],
)
def test_v3_claim_decision_crash_retry_preserves_staged_created_at(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_claims"
    path = tmp_path / "claim-v3-crash.json"
    path.write_bytes(pretty_json_bytes(_v3_claim_envelope(queue_path)))
    crash_at = f"claim_decision:{suffix}"

    with pytest.raises(RuntimeError, match=crash_at):
        import_reviewed_claims(
            review_queue_path=queue_path,
            decisions_path=path,
            output_dir=output,
            now=lambda: "2026-07-12T04:04:00Z",
            nonce_factory=lambda: "7" * 32,
            crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
            if label == crash_at
            else None,
        )

    retry = import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
        now=lambda: "2026-07-12T09:09:09Z",
        nonce_factory=lambda: "8" * 32,
    )
    _, sidecar = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=output,
    )
    assert retry["status"] == "reviewed_claims_complete"
    assert sidecar["created_at"] == "2026-07-12T04:04:00Z"


def test_v3_model_claim_is_covered_but_never_support_allowed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_claims"
    path = tmp_path / "model-claim-v3.json"
    path.write_bytes(pretty_json_bytes(_v3_claim_envelope(
        queue_path,
        review_status="model_reviewed_advisory",
    )))

    result = import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
    )
    _, sidecar = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=output,
    )

    assert result["status"] == "reviewed_claims_complete"
    assert sidecar["decision_coverage_complete"] is True
    assert sidecar["claims"][0]["claim_support_allowed"] is False


def test_v3_claim_type_support_class_reviewer_matrix_is_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    context = load_v2_evidence_context(queue_path)
    queue_item = next(
        row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate"
    )
    local_root = mission / "local_evidence"
    local_root.mkdir()
    local_artifacts = {}
    for support_class in ("project_derivation", "implementation_evidence"):
        artifact = local_root / f"{support_class}.txt"
        artifact.write_text("checked fixture-local evidence\n")
        local_artifacts[support_class] = artifact

    matrices = {**CLAIM_SUPPORT_MATRIX, **CLAIM_NONSUPPORT_MATRIX}
    assert len(matrices) == 6
    assert len(set(matrices.values())) == 6
    assert CLAIM_REVIEW_STATUSES == {
        "human_reviewed_passed",
        "model_reviewed_advisory",
        "rejected_or_blocked",
    }
    rows = {
        "primary_technical_support": _v3_claim_envelope(queue_path)["decisions"][0],
        "project_derivation": _v3_local_claim_envelope(
            queue_path,
            support_class="project_derivation",
            local_artifact=local_artifacts["project_derivation"],
        )["decisions"][0],
        "implementation_evidence": _v3_local_claim_envelope(
            queue_path,
            support_class="implementation_evidence",
            local_artifact=local_artifacts["implementation_evidence"],
        )["decisions"][0],
        **{
            support_class: _v3_nonsupport_claim_envelope(
                queue_path,
                support_class=support_class,
            )["decisions"][0]
            for support_class in CLAIM_NONSUPPORT_MATRIX
        },
    }

    checked_cells = 0
    for support_class, row_template in rows.items():
        for claim_type in matrices.values():
            for review_status in sorted(CLAIM_REVIEW_STATUSES):
                row = deepcopy(row_template)
                row["claim_type"] = claim_type
                row["review_status"] = review_status
                if claim_type != matrices[support_class]:
                    with pytest.raises(MissionStateError) as error:
                        _validate_v3_claim_row(
                            row,
                            queue_item=queue_item,
                            context=context,
                            index=1,
                        )
                    assert error.value.code == "invalid_claim_support_matrix"
                else:
                    normalized = _validate_v3_claim_row(
                        row,
                        queue_item=queue_item,
                        context=context,
                        index=1,
                    )
                    assert normalized["claim_support_allowed"] is (
                        support_class in CLAIM_SUPPORT_MATRIX
                        and review_status == "human_reviewed_passed"
                    )
                    assert normalized["ready_for_prose"] is False
                checked_cells += 1
    assert checked_cells == 108

    for legacy_status in ("reviewed_passed", "model_reviewed_passed"):
        row = deepcopy(rows["primary_technical_support"])
        row["review_status"] = legacy_status
        with pytest.raises(MissionStateError) as error:
            _validate_v3_claim_row(
                row,
                queue_item=queue_item,
                context=context,
                index=1,
            )
        assert error.value.code == "invalid_claim_reviewer_authority"


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (
            lambda envelope: envelope["decisions"][0].update(claim_type="implementation_behavior"),
            "invalid_claim_support_matrix",
        ),
        (
            lambda envelope: envelope["decisions"][0]["source_dependencies"][0].update(
                source_version="record-sha256:" + "0" * 64
            ),
            "stale_claim_dependency",
        ),
        (
            lambda envelope: envelope["decisions"][0].update(dependency_graph_sha256="0" * 64),
            "claim_dependency_graph_digest_mismatch",
        ),
    ],
)
def test_v3_claim_matrix_and_graph_attacks_create_no_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutator,
    reason: str,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    output = mission / "reviewed_claims"
    envelope = _v3_claim_envelope(queue_path)
    mutator(envelope)
    path = tmp_path / "bad-claim-v3.json"
    path.write_bytes(pretty_json_bytes(envelope))

    result = import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=output,
    )

    assert result["status"] == "blocked"
    assert result["blocked_reason"] == reason
    assert not output.exists()


def test_v3_dependency_graph_empty_direct_and_transitive_paths_are_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    context = load_v2_evidence_context(queue_path)
    identity = next(iter(context.source_identities.values()))
    dependency = {
        "stable_metadata_paper_id": identity.stable_metadata_paper_id,
        "source_paper_id": identity.source_paper_id,
        "canonical_identifier": identity.canonical_identifier,
        "source_version": identity.source_version,
        "source_record_sha256": identity.source_record_sha256,
        "dependency_role": "implementation_evidence_source",
    }
    evidence = mission / "local_evidence"
    evidence.mkdir()
    root_path = evidence / "root.txt"
    child_path = evidence / "child.txt"
    root_path.write_text("checked root evidence\n")
    child_path.write_text("checked child evidence\n")
    root_relative = str(root_path.relative_to(mission))
    child_relative = str(child_path.relative_to(mission))

    empty_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_relative,
        local_artifact_sha256=sha256_bytes(root_path.read_bytes()),
        direct_source_paper_ids=[],
        referenced_manifest_ids=[],
    )
    empty = _validate_dependency_graph(
        _dependency_graph_value(
            source_dependencies=[],
            dependency_manifests=[empty_root],
            root_dependency_manifest_id=empty_root["manifest_id"],
        ),
        support_class="implementation_evidence",
        context=context,
    )
    assert empty["graph_source_paper_ids"] == []

    direct_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_relative,
        local_artifact_sha256=sha256_bytes(root_path.read_bytes()),
        direct_source_paper_ids=[identity.source_paper_id],
        referenced_manifest_ids=[],
    )
    direct = _validate_dependency_graph(
        _dependency_graph_value(
            source_dependencies=[dependency],
            dependency_manifests=[direct_root],
            root_dependency_manifest_id=direct_root["manifest_id"],
        ),
        support_class="implementation_evidence",
        context=context,
    )
    assert direct["graph_source_paper_ids"] == [identity.source_paper_id]

    child = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=child_relative,
        local_artifact_sha256=sha256_bytes(child_path.read_bytes()),
        direct_source_paper_ids=[identity.source_paper_id],
        referenced_manifest_ids=[],
    )
    transitive_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_relative,
        local_artifact_sha256=sha256_bytes(root_path.read_bytes()),
        direct_source_paper_ids=[],
        referenced_manifest_ids=[child["manifest_id"]],
    )
    transitive = _validate_dependency_graph(
        _dependency_graph_value(
            source_dependencies=[dependency],
            dependency_manifests=[transitive_root, child],
            root_dependency_manifest_id=transitive_root["manifest_id"],
        ),
        support_class="implementation_evidence",
        context=context,
    )
    assert transitive["graph_source_paper_ids"] == [identity.source_paper_id]


def test_v3_dependency_graph_topology_attacks_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    context = load_v2_evidence_context(queue_path)
    identity = next(iter(context.source_identities.values()))
    dependency = {
        "stable_metadata_paper_id": identity.stable_metadata_paper_id,
        "source_paper_id": identity.source_paper_id,
        "canonical_identifier": identity.canonical_identifier,
        "source_version": identity.source_version,
        "source_record_sha256": identity.source_record_sha256,
        "dependency_role": "implementation_evidence_source",
    }
    evidence = mission / "local_evidence"
    evidence.mkdir()

    def artifact(name: str) -> tuple[str, str]:
        path = evidence / name
        path.write_text(f"checked {name}\n")
        return str(path.relative_to(mission)), sha256_bytes(path.read_bytes())

    root_path, root_sha = artifact("root.txt")
    child_path, child_sha = artifact("child.txt")
    leaf_path, leaf_sha = artifact("leaf.txt")
    leaf = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=leaf_path,
        local_artifact_sha256=leaf_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[],
    )
    child_one = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=child_path,
        local_artifact_sha256=child_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[leaf["manifest_id"]],
    )
    second_path, second_sha = artifact("second.txt")
    child_two = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=second_path,
        local_artifact_sha256=second_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[leaf["manifest_id"]],
    )
    repeated_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_path,
        local_artifact_sha256=root_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[child_one["manifest_id"], child_two["manifest_id"]],
    )

    base_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_path,
        local_artifact_sha256=root_sha,
        direct_source_paper_ids=[identity.source_paper_id],
        referenced_manifest_ids=[],
    )
    foreign = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=child_path,
        local_artifact_sha256=child_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[],
    )
    missing_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_path,
        local_artifact_sha256=root_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=["dm-" + "0" * 64],
    )
    no_source_root = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=root_path,
        local_artifact_sha256=root_sha,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[],
    )
    attacks = [
        (
            "duplicate_source_dependency",
            _dependency_graph_value(
                source_dependencies=[dependency, dependency],
                dependency_manifests=[base_root],
                root_dependency_manifest_id=base_root["manifest_id"],
            ),
            "duplicate_claim_dependency",
        ),
        (
            "missing_manifest",
            _dependency_graph_value(
                source_dependencies=[],
                dependency_manifests=[missing_root],
                root_dependency_manifest_id=missing_root["manifest_id"],
            ),
            "missing_dependency_manifest",
        ),
        (
            "foreign_manifest",
            _dependency_graph_value(
                source_dependencies=[dependency],
                dependency_manifests=[base_root, foreign],
                root_dependency_manifest_id=base_root["manifest_id"],
            ),
            "foreign_dependency_manifest",
        ),
        (
            "repeated_edge",
            _dependency_graph_value(
                source_dependencies=[],
                dependency_manifests=[repeated_root, child_one, child_two, leaf],
                root_dependency_manifest_id=repeated_root["manifest_id"],
            ),
            "duplicate_dependency_edge",
        ),
        (
            "missing_declared_source",
            _dependency_graph_value(
                source_dependencies=[dependency],
                dependency_manifests=[no_source_root],
                root_dependency_manifest_id=no_source_root["manifest_id"],
            ),
            "claim_dependency_closure_mismatch",
        ),
        (
            "undeclared_direct_source",
            _dependency_graph_value(
                source_dependencies=[],
                dependency_manifests=[base_root],
                root_dependency_manifest_id=base_root["manifest_id"],
            ),
            "claim_dependency_closure_mismatch",
        ),
    ]
    for name, graph, expected_code in attacks:
        with pytest.raises(MissionStateError) as error:
            _validate_dependency_graph(
                graph,
                support_class="implementation_evidence",
                context=context,
            )
        assert error.value.code == expected_code, name

    with pytest.raises(MissionStateError) as cycle:
        _reachable_manifest_ids(
            "root",
            {
                "root": {"referenced_manifest_ids": ["child"]},
                "child": {"referenced_manifest_ids": ["root"]},
            },
        )
    assert cycle.value.code == "cyclic_dependency_graph"


@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("missing", "missing_dependency_local_artifact"),
        ("changed", "dependency_local_artifact_digest_mismatch"),
        ("traversal", "invalid_dependency_local_artifact"),
        ("absolute", "invalid_dependency_local_artifact"),
        ("leaf_symlink", "unsafe_dependency_local_artifact"),
        ("parent_symlink", "unsafe_dependency_local_artifact"),
        ("nonregular", "unsafe_dependency_local_artifact"),
        ("hidden_field", "invalid_schema"),
    ],
)
def test_v3_dependency_local_artifact_attacks_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    expected_code: str,
) -> None:
    mission, queue_path, _ = _canonical_v2_mission(tmp_path, monkeypatch)
    context = load_v2_evidence_context(queue_path)
    evidence = mission / "local_evidence"
    evidence.mkdir()
    target = evidence / "proof.txt"
    target.write_text("checked local evidence\n")
    relative = str(target.relative_to(mission))
    digest = sha256_bytes(target.read_bytes())

    if attack == "missing":
        target.unlink()
    elif attack == "changed":
        target.write_text("changed after review\n")
    elif attack == "traversal":
        relative = "../outside.txt"
    elif attack == "absolute":
        relative = str(target)
    elif attack == "leaf_symlink":
        actual = evidence / "actual.txt"
        target.rename(actual)
        target.symlink_to(actual)
    elif attack == "parent_symlink":
        actual_dir = evidence / "actual"
        actual_dir.mkdir()
        actual = actual_dir / "proof.txt"
        target.rename(actual)
        linked = evidence / "linked"
        linked.symlink_to(actual_dir, target_is_directory=True)
        relative = str((linked / "proof.txt").relative_to(mission))
    elif attack == "nonregular":
        target.unlink()
        target.mkdir()

    manifest = _dependency_manifest(
        support_class="implementation_evidence",
        local_artifact=relative,
        local_artifact_sha256=digest,
        direct_source_paper_ids=[],
        referenced_manifest_ids=[],
    )
    if attack == "hidden_field":
        manifest["hidden_dependency"] = "forbidden"
    graph = _dependency_graph_value(
        source_dependencies=[],
        dependency_manifests=[manifest],
        root_dependency_manifest_id=manifest["manifest_id"],
    )

    with pytest.raises(MissionStateError) as error:
        _validate_dependency_graph(
            graph,
            support_class="implementation_evidence",
            context=context,
        )
    assert error.value.code == expected_code


def _merge_current_reviews(
    *,
    mission: Path,
    queue_path: Path,
    sidecars: dict[str, Path],
) -> dict:
    return merge_reviewed_evidence(
        review_queue_path=queue_path,
        reviewed_claims_path=sidecars["claim_candidate"],
        reviewed_source_safety_path=sidecars["source_safety"],
        reviewed_omissions_path=sidecars["omission_risk"],
        reviewed_workflow_blockers_path=sidecars["workflow_blocker"],
        output_dir=mission / "reviewed_evidence",
        force=True,
    )


def test_v3_merge_writes_complete_source_accounting_and_replays_tamper(
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

    result = _merge_current_reviews(mission=mission, queue_path=queue_path, sidecars=sidecars)
    accounting_path = mission / "reviewed_evidence" / "reviewed_source_accounting.json"
    accounting = json_load(accounting_path)
    merge_path = mission / "reviewed_evidence" / "reviewed_evidence_status.json"
    merge = validate_reviewed_evidence_status(
        path=merge_path,
        review_queue_path=queue_path,
        sidecar_paths=sidecars,
    )

    assert result["status"] == "reviewed_evidence_complete"
    assert accounting["schema_version"] == "ra-survey-reviewed-source-accounting-v1"
    assert accounting["status"] == "source_accounting_clear"
    assert accounting["selected_source_count"] == accounting["support_dependency_count"] == 1
    assert accounting["accounted_source_count"] == 1
    assert accounting["unsafe_dependency_count"] == 0
    assert accounting["missing_dependency_count"] == 0
    assert accounting["unused_included_source_count"] == 0
    assert accounting["open_quarantine_risk_count"] == 0
    assert set(merge["merge_diagnostics"]) == {"source_accounting", "source_outcomes"}
    assert not (mission / "reviewed_evidence" / "reviewed_quarantine_closure.json").exists()

    accounting["unused_included_source_count"] = 1
    accounting_path.write_bytes(pretty_json_bytes(accounting))
    with pytest.raises(MissionStateError) as error:
        validate_reviewed_evidence_status(
            path=merge_path,
            review_queue_path=queue_path,
            sidecar_paths=sidecars,
        )
    assert error.value.code == "invalid_source_accounting_replay"


@pytest.mark.parametrize(
    "crash_after",
    [
        "reviewed_source_outcome_blockers.json",
        "reviewed_source_accounting.json",
        "reviewed_evidence_status.json",
    ],
)
def test_v3_merge_publication_order_never_authorizes_partial_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_after: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    sidecars = _import_complete_v2_reviews(
        mission=mission,
        queue_path=queue_path,
        queue=queue,
        decisions_dir=tmp_path / "decisions",
    )
    real_atomic_write = reviewed_merge_module.atomic_write_json

    def crash_after_write(path: Path, payload: dict) -> None:
        real_atomic_write(path, payload)
        if path.name == crash_after:
            raise RuntimeError(f"crash after {crash_after}")

    monkeypatch.setattr(reviewed_merge_module, "atomic_write_json", crash_after_write)
    with pytest.raises(RuntimeError, match=f"crash after {crash_after}"):
        _merge_current_reviews(mission=mission, queue_path=queue_path, sidecars=sidecars)

    merge_root = mission / "reviewed_evidence"
    status_path = merge_root / "reviewed_evidence_status.json"
    if crash_after == "reviewed_evidence_status.json":
        validated = validate_reviewed_evidence_status(
            path=status_path,
            review_queue_path=queue_path,
            sidecar_paths=sidecars,
        )
        assert validated["ready_for_reviewed_packet"] is True
    else:
        assert not status_path.exists()
        packet_result = compose_reviewed_final_packet(
            mission_root=mission,
            review_queue_path=queue_path,
            packet_dir=mission / "public_source_packet",
            anchor_dir=mission / "source_anchors",
            output_dir=mission / "reviewed_final_packet",
        )
        assert packet_result["status"] == "blocked"
        assert packet_result["blocked_reason"] == "missing_review_artifact"
        assert not (mission / "reviewed_final_packet").exists()

    monkeypatch.setattr(reviewed_merge_module, "atomic_write_json", real_atomic_write)
    repaired = _merge_current_reviews(
        mission=mission,
        queue_path=queue_path,
        sidecars=sidecars,
    )
    assert repaired["status"] == "reviewed_evidence_complete"
    assert validate_reviewed_evidence_status(
        path=status_path,
        review_queue_path=queue_path,
        sidecar_paths=sidecars,
    )["ready_for_reviewed_packet"] is True


def test_v3_merge_blocks_model_only_claim_as_unused_included_source(
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
    path = tmp_path / "model-only-claim.json"
    path.write_bytes(pretty_json_bytes(_v3_claim_envelope(
        queue_path,
        review_status="model_reviewed_advisory",
    )))
    assert import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=path,
        output_dir=mission / "reviewed_claims",
        force=True,
    )["status"] == "reviewed_claims_complete"
    snapshot, _ = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=mission / "reviewed_claims",
    )
    sidecars["claim_candidate"] = snapshot.artifact_paths["reviewed_claims.json"]

    result = _merge_current_reviews(mission=mission, queue_path=queue_path, sidecars=sidecars)
    accounting = json_load(mission / "reviewed_evidence" / "reviewed_source_accounting.json")
    merge = json_load(mission / "reviewed_evidence" / "reviewed_evidence_status.json")

    assert result["status"] == "reviewed_evidence_blocked"
    assert accounting["unused_included_source_count"] == 1
    assert accounting["unused_included_sources"][0]["blocker_code"] == "unused_included_source"
    assert any(value.startswith("unused_included_source:") for value in merge["blockers"])
    assert merge["ready_for_reviewed_packet"] is False


def test_v3_merge_keeps_unresolved_frontier_quarantine_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(
        tmp_path,
        monkeypatch,
        seed_referenced_works=["W999"],
    )
    sidecars = _import_complete_v2_reviews(
        mission=mission,
        queue_path=queue_path,
        queue=queue,
        decisions_dir=tmp_path / "decisions",
    )

    result = _merge_current_reviews(mission=mission, queue_path=queue_path, sidecars=sidecars)
    accounting = json_load(mission / "reviewed_evidence" / "reviewed_source_accounting.json")
    merge = json_load(mission / "reviewed_evidence" / "reviewed_evidence_status.json")

    assert result["status"] == "reviewed_evidence_blocked"
    assert accounting["open_quarantine_risk_count"] == 1
    risk = accounting["open_quarantine_risks"][0]
    assert risk["blocker_code"] == "open_quarantine_risk"
    assert risk["source_identity_match_count"] == 0
    assert risk["closure_authorized"] is False
    assert any(value.startswith("open_quarantine_risk:") for value in merge["blockers"])


@pytest.mark.parametrize("support_class", ["project_derivation", "implementation_evidence"])
def test_v3_local_dependency_manifest_classifies_packet_and_hostile_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    support_class: str,
) -> None:
    mission, queue_path, queue = _canonical_v2_mission(tmp_path, monkeypatch)
    sidecars = _import_complete_v2_reviews(
        mission=mission,
        queue_path=queue_path,
        queue=queue,
        decisions_dir=tmp_path / "decisions",
    )
    local_root = mission / "local_evidence"
    local_root.mkdir()
    artifact = local_root / f"{support_class}.txt"
    artifact.write_text("checked fixture-local evidence\n")
    claim_path = tmp_path / f"{support_class}.json"
    claim_path.write_bytes(pretty_json_bytes(_v3_local_claim_envelope(
        queue_path,
        support_class=support_class,
        local_artifact=artifact,
    )))
    assert import_reviewed_claims(
        review_queue_path=queue_path,
        decisions_path=claim_path,
        output_dir=mission / "reviewed_claims",
        force=True,
    )["status"] == "reviewed_claims_complete"
    snapshot, _ = resolve_current_reviewed_claims(
        review_queue_path=queue_path,
        reviewed_claims_root=mission / "reviewed_claims",
    )
    sidecars["claim_candidate"] = snapshot.artifact_paths["reviewed_claims.json"]
    assert _merge_current_reviews(
        mission=mission,
        queue_path=queue_path,
        sidecars=sidecars,
    )["status"] == "reviewed_evidence_complete"

    packet_result = compose_reviewed_final_packet(
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
        local_evidence_root=local_root,
        output_dir=mission / "reviewed_final_packet",
    )
    packet_path = mission / "reviewed_final_packet" / "reviewed_final_packet.json"
    packet = json_load(packet_path)
    classification = packet["evidence_classifications"][0]
    claim = packet["reviewed_sections"]["claims"][0]

    assert packet_result["status"] == "reviewed_final_packet_ready_for_hostile_review"
    assert classification["support_class"] == support_class
    assert classification["root_dependency_manifest_id"] == claim["root_dependency_manifest_id"]
    assert classification["bound_local_artifacts"] == [{
        "manifest_id": claim["root_dependency_manifest_id"],
        "local_artifact": str(artifact.relative_to(mission)),
        "local_artifact_sha256": sha256_bytes(artifact.read_bytes()),
    }]
    hostile = run_hostile_review_gate(
        reviewed_final_packet_path=packet_path,
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
        local_evidence_root=local_root,
        output_dir=mission / "hostile_review",
    )
    assert hostile["blocker_count"] == 0


def test_unavailable_source_outcome_vetoes_merge_and_packet_with_exact_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _records()[:2]

    def mixed_source(request):
        if request.identifier == "openalex:w200":
            return SourceCapabilityResult(
                candidate_id=request.candidate_id,
                identifier=request.identifier,
                outcome_status="unavailable",
                code="unavailable",
                provider=request.providers[0],
            )
        from test_literature_survey_m16_phase8 import _fixture_source

        return _fixture_source(request)

    mission, queue_path, queue = _canonical_v2_mission(
        tmp_path,
        monkeypatch,
        fixture_records=records,
        source_handler=mixed_source,
    )
    context = load_v2_evidence_context(queue_path)
    assert len(context.unavailable_outcomes) == 1
    assert len(context.source_identities) == 1
    sidecars = _import_complete_v2_reviews(
        mission=mission,
        queue_path=queue_path,
        queue=queue,
        decisions_dir=tmp_path / "decisions",
    )

    merge_result = _merge_current_reviews(
        mission=mission,
        queue_path=queue_path,
        sidecars=sidecars,
    )
    merge = json_load(mission / "reviewed_evidence" / "reviewed_evidence_status.json")
    source_outcomes = json_load(
        mission / "reviewed_evidence" / "reviewed_source_outcome_blockers.json"
    )
    packet_result = compose_reviewed_final_packet(
        mission_root=mission,
        review_queue_path=queue_path,
        packet_dir=mission / "public_source_packet",
        anchor_dir=mission / "source_anchors",
        output_dir=mission / "reviewed_final_packet",
    )

    assert merge_result["status"] == "reviewed_evidence_blocked_unavailable_source_outcome"
    assert source_outcomes["blockers"][0]["blocker_code"] == "unavailable_source_outcome"
    assert any(value.startswith("unavailable_source_outcome:") for value in merge["blockers"])
    assert packet_result["status"] == "blocked"
    assert packet_result["blocked_reason"] == "unavailable_source_outcome"
    assert not (mission / "reviewed_final_packet").exists()


@pytest.mark.parametrize(
    ("config", "suffix"),
    _authority_crash_cases(),
    ids=lambda value: value.family if hasattr(value, "family") else value,
)
def test_v3_immutable_authority_crash_events_never_select_partial_bytes(
    tmp_path: Path,
    config,
    suffix: str,
) -> None:
    root = tmp_path / config.family
    artifacts = {
        name: pretty_json_bytes({"schema_version": "fixture-artifact-v1", "name": name})
        for name in config.artifacts
    }
    identity = {
        field: (
            None
            if field in {config.predecessor_id_field, config.predecessor_manifest_field}
            else False
            if field == "fixture_only"
            else 1
            if field.endswith("_size_bytes")
            else []
            if field in {"source_record_digests", "what_is_not_concluded"}
            else "a" * 64
            if field.endswith("sha256") or field == "mission_fingerprint"
            else "fixture"
        )
        for field in config.identity_fields
    }
    crash_at = f"{config.family}:{suffix}"
    manager = ImmutableAuthorityManager(
        root=root,
        config=config,
        nonce_factory=lambda: "1" * 32,
        crash_hook=lambda label: (_ for _ in ()).throw(RuntimeError(label))
        if label == crash_at
        else None,
    )

    with pytest.raises(RuntimeError, match=crash_at):
        manager.compose_and_select(identity_fields=identity, artifacts=artifacts, force=False)

    current = root / config.current_name
    pointer_replaced = suffix in {"current:after_replace", "current:after_directory_fsync"}
    if pointer_replaced:
        assert current.is_file()
        snapshot = ImmutableAuthorityManager(root=root, config=config).load_current(required=True)
        assert snapshot is not None
        assert all(path.is_file() for path in snapshot.artifact_paths.values())
    else:
        assert not current.exists()
        with pytest.raises(MissionStateError):
            ImmutableAuthorityManager(root=root, config=config).load_current(required=True)

    retry = ImmutableAuthorityManager(
        root=root,
        config=config,
        nonce_factory=lambda: "2" * 32,
    ).compose_and_select(identity_fields=identity, artifacts=artifacts, force=False)
    assert retry.set_id.startswith(config.id_prefix + "-")
    assert all(retry.artifact_paths[name].read_bytes() == value for name, value in artifacts.items())


@pytest.mark.parametrize(
    "config",
    AUTHORITY_CONFIGS,
    ids=lambda config: config.family,
)
@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("malformed_pointer", "invalid_json"),
        ("foreign_pointer", "unsafe_authority_directory"),
        ("symlink_pointer", None),
        ("symlink_set", None),
        ("symlink_artifact", None),
        ("unexpected_root_child", None),
        ("unexpected_set_child", None),
        ("partial_set", None),
        ("artifact_conflict", None),
        ("rollback", None),
        ("fork", None),
        ("disconnected_root", None),
        ("partial_predecessor", None),
    ],
)
def test_v3_authority_selector_and_chain_attack_matrix_fails_closed(
    tmp_path: Path,
    config,
    attack: str,
    expected_code: str | None,
) -> None:
    root = tmp_path / config.family
    manager = ImmutableAuthorityManager(
        root=root,
        config=config,
        nonce_factory=lambda: "1" * 32,
    )
    genesis_artifacts = _authority_artifacts(config, marker="genesis")
    genesis = manager.compose_and_select(
        identity_fields=_authority_identity(config, marker="genesis"),
        artifacts=genesis_artifacts,
        force=False,
    )
    genesis_pointer = (root / config.current_name).read_bytes()

    if attack == "malformed_pointer":
        (root / config.current_name).write_bytes(b"{")
    elif attack == "foreign_pointer":
        pointer = {
            "schema_version": config.current_schema,
            config.set_id_field: f"{config.id_prefix}-" + "f" * 64,
            config.current_manifest_field: "e" * 64,
        }
        (root / config.current_name).write_bytes(canonical_json_bytes(pointer))
    elif attack == "symlink_pointer":
        pointer = root / config.current_name
        outside = tmp_path / f"outside-{config.family}-pointer"
        outside.write_bytes(pointer.read_bytes())
        pointer.unlink()
        pointer.symlink_to(outside)
    elif attack == "symlink_set":
        outside = tmp_path / f"outside-{config.family}-set"
        genesis.set_dir.rename(outside)
        genesis.set_dir.symlink_to(outside, target_is_directory=True)
    elif attack == "symlink_artifact":
        name = sorted(config.artifacts)[0]
        artifact = genesis.artifact_paths[name]
        outside = tmp_path / f"outside-{config.family}-artifact"
        outside.write_bytes(artifact.read_bytes())
        artifact.unlink()
        artifact.symlink_to(outside)
    elif attack == "unexpected_root_child":
        (root / "unexpected.json").write_bytes(b"{}")
    elif attack == "unexpected_set_child":
        (genesis.set_dir / "unexpected.json").write_bytes(b"{}")
    elif attack == "partial_set":
        genesis.artifact_paths[sorted(config.artifacts)[0]].unlink()
    elif attack == "artifact_conflict":
        genesis.artifact_paths[sorted(config.artifacts)[0]].write_bytes(b"conflict")
    elif attack == "rollback":
        successor = ImmutableAuthorityManager(
            root=root,
            config=config,
            nonce_factory=lambda: "2" * 32,
        ).compose_and_select(
            identity_fields=_authority_identity(
                config,
                marker="successor",
                predecessor=genesis,
            ),
            artifacts=_authority_artifacts(config, marker="successor"),
            force=True,
        )
        assert successor.set_id != genesis.set_id
        (root / config.current_name).write_bytes(genesis_pointer)
    elif attack == "fork":
        for marker in ("fork-a", "fork-b"):
            artifacts = _authority_artifacts(config, marker=marker)
            identity = _authority_identity(
                config,
                marker=marker,
                predecessor=genesis,
            )
            set_id, manifest = manager.preview(
                identity_fields=identity,
                artifacts=artifacts,
            )
            _materialize_authority_set(
                root=root,
                config=config,
                set_id=set_id,
                manifest=manifest,
                artifacts=artifacts,
            )
    elif attack == "disconnected_root":
        artifacts = _authority_artifacts(config, marker="second-root")
        identity = _authority_identity(config, marker="second-root")
        set_id, manifest = manager.preview(
            identity_fields=identity,
            artifacts=artifacts,
        )
        _materialize_authority_set(
            root=root,
            config=config,
            set_id=set_id,
            manifest=manifest,
            artifacts=artifacts,
        )
    elif attack == "partial_predecessor":
        artifacts = _authority_artifacts(config, marker="partial-predecessor")
        identity = _authority_identity(
            config,
            marker="partial-predecessor",
            predecessor=genesis,
        )
        identity[config.predecessor_manifest_field] = None
        set_id, manifest = manager.preview(
            identity_fields=identity,
            artifacts=artifacts,
        )
        _materialize_authority_set(
            root=root,
            config=config,
            set_id=set_id,
            manifest=manifest,
            artifacts=artifacts,
        )
    else:  # pragma: no cover - parametrization is closed above.
        raise AssertionError(attack)

    with pytest.raises(MissionStateError) as error:
        ImmutableAuthorityManager(root=root, config=config).load_current(required=True)
    if expected_code is not None:
        assert error.value.code == expected_code
    assert error.value.code not in {"output_exists", "missing_review_artifact"}
