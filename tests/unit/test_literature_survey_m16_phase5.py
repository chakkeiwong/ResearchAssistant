from __future__ import annotations

import hashlib
import json
import socket
import time
from pathlib import Path

import pytest

import research_assistant.survey.orchestrate as orchestrate
from research_assistant.survey.anchors import ANCHOR_OUTPUT_FILES, build_source_anchor_packet
from research_assistant.survey.build import build_survey_evidence_packet
from research_assistant.survey.mission_state import (
    LOCK_SCHEMA,
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    pretty_json_bytes,
)
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.packet import PUBLIC_SOURCE_PACKET_FILES
from research_assistant.survey.reviewed_merge import (
    REVIEWED_EVIDENCE_KEYS,
    SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
)
from research_assistant.survey.supervisor import (
    classify_repairable_json,
    observation_sha256,
    preflight_mission_output,
    validate_anchor_packet,
    validate_offline_skeleton,
    validate_public_source_packet,
    validate_source_intake_authority,
    validate_supervisor_read_root,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(payload))


def _source_intake(tmp_path: Path, *, paper_id: str = "paper_arxiv_2201_1a5af737") -> tuple[Path, Path, dict]:
    record = tmp_path / "project" / "local_research" / "papers" / "source" / "records" / f"{paper_id}.json"
    payload = {
        "paper_id": paper_id,
        "source_type": "arxiv_latex",
        "status": "available",
        "sections": [],
        "equations": [],
        "theorem_like_blocks": [],
        "labels": [],
        "references": [],
        "citations": [],
        "bibliography": [],
        "macros": [],
        "provenance": {},
        "diagnostics": {},
        "limitations": [],
    }
    _write_json(record, payload)
    status = tmp_path / "mission" / "source_intake" / "phase4_source_intake_status.json"
    status_payload = {
        "schema_version": "fixture-source-intake-v1",
        "status": "completed",
        "source_support": [{
            "paper_id": paper_id,
            "source_record_path": str(record),
            "source_record_sha256": hashlib.sha256(record.read_bytes()).hexdigest(),
        }],
    }
    _write_json(status, status_payload)
    return status, record, status_payload


def _synthetic_observation(snapshot, output_dir: Path, *, action_id: str, marker: int) -> dict:
    next_action = {
        "schema_version": "ra-survey-public-source-next-action-v1",
        "action_id": action_id,
        "status": "synthetic_local_action",
        "mission_status": "ready_for_local_continuation",
        "safe_next_commands": [f"forbidden-command-{marker}"],
        "required_artifacts": [],
    }
    mission = {
        "status": "ready_for_local_continuation",
        "created_at": snapshot.contract["created_at"],
        "updated_at": snapshot.contract["updated_at"],
        "topic": snapshot.contract["normalized_topic"]["display"],
        "seeds": [row["display"] for row in snapshot.contract["normalized_seeds"]],
        "output_dir": str(output_dir),
        "phase_statuses": {},
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "public_discovery_confirmation": {},
        "actions": [],
        "next_gate": {"gate_id": "synthetic", "marker": marker},
        "next_action_path": str(output_dir / "next_action.json"),
        "next_action": next_action,
        "workflow_state": None,
        "artifact_state": {"marker": marker},
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "safe_next_commands": next_action["safe_next_commands"],
        "forbidden_actions": [],
        "what_is_not_concluded": [],
    }
    return {
        "schema_version": "ra-survey-public-source-orchestration-result-v1",
        "status": mission["status"],
        "topic": mission["topic"],
        "seed_count": len(mission["seeds"]),
        "output_dir": str(output_dir),
        "mission_control_path": str(output_dir / "mission_control.json"),
        "next_action_path": str(output_dir / "next_action.json"),
        "mission_id": snapshot.contract["mission_id"],
        "mission_fingerprint": snapshot.contract["mission_fingerprint"],
        "generation_id": snapshot.current_pointer["generation_id"] if snapshot.current_pointer else None,
        "artifact_paths": {},
        "next_gate": mission["next_gate"],
        "next_action": next_action,
        "public_discovery_confirmation": {},
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "artifact_state": mission["artifact_state"],
        "phase_statuses": {},
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "safe_next_commands": next_action["safe_next_commands"],
        "what_is_not_concluded": [],
        "_mission_control_payload": mission,
        "_next_action_payload": next_action,
    }


def _run_synthetic_supervisor(tmp_path: Path, monkeypatch, *, observations, dispatch):
    output = tmp_path / "mission"
    values = iter(observations)

    def observe(*, snapshot, output_dir, **kwargs):
        action_id, marker = next(values)
        return _synthetic_observation(snapshot, output_dir, action_id=action_id, marker=marker)

    monkeypatch.setattr(orchestrate, "_supervisor_observe", observe)
    monkeypatch.setattr(orchestrate, "_dispatch_safe_local_stage", dispatch)
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=output,
        run_safe_local=True,
    )
    return output, result


def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | None]]:
    return {
        str(path.relative_to(root)): (
            "symlink" if path.is_symlink() else "dir" if path.is_dir() else "file",
            path.read_bytes() if path.is_file() and not path.is_symlink() else None,
        )
        for path in sorted(root.rglob("*"))
    }


def test_complete_skeleton_validator_rejects_partial_extra_and_wrong_schema(tmp_path: Path) -> None:
    output = tmp_path / "mission" / "offline_skeleton"
    result = build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=output,
        mode="offline-skeleton",
    )
    assert result["status"] == "created_skeleton"
    assert validate_offline_skeleton(output)["mode"] == "offline-skeleton"

    removed = output / "claim_support.json"
    before = removed.read_bytes()
    removed.unlink()
    with pytest.raises(MissionStateError) as error:
        validate_offline_skeleton(output)
    assert error.value.code == "incomplete_stage_artifact"
    removed.write_bytes(before)

    extra = output / "unexpected.json"
    extra.write_text("{}")
    with pytest.raises(MissionStateError) as error:
        validate_offline_skeleton(output)
    assert error.value.code == "incomplete_stage_artifact"
    extra.unlink()

    manifest = json.loads((output / "build_manifest.json").read_text())
    manifest["schema_version"] = "wrong"
    _write_json(output / "build_manifest.json", manifest)
    with pytest.raises(MissionStateError) as error:
        validate_offline_skeleton(output)
    assert error.value.code == "invalid_stage_artifact"


@pytest.mark.parametrize("shape", ["malformed", "noncanonical", "wrong_schema", "wrong_keys", "symlink"])
def test_force_repair_classifier_rejects_non_replay_shapes(tmp_path: Path, shape: str) -> None:
    path = tmp_path / "reviewed_evidence_status.json"
    payload = {key: None for key in REVIEWED_EVIDENCE_KEYS}
    payload["schema_version"] = SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION
    if shape == "malformed":
        path.write_text("{")
    elif shape == "noncanonical":
        path.write_text(json.dumps(payload))
    elif shape == "wrong_schema":
        payload["schema_version"] = "wrong"
        path.write_bytes(pretty_json_bytes(payload))
    elif shape == "wrong_keys":
        payload["extra"] = True
        path.write_bytes(pretty_json_bytes(payload))
    else:
        target = tmp_path / "outside.json"
        target.write_bytes(pretty_json_bytes(payload))
        path.symlink_to(target)
    assert classify_repairable_json(
        path,
        expected_schema=SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
        expected_keys=REVIEWED_EVIDENCE_KEYS,
    ) == "terminal_invalid"


def test_force_repair_classifier_allows_only_exact_schema_canonical_replay_candidate(tmp_path: Path) -> None:
    path = tmp_path / "reviewed_evidence_status.json"
    assert classify_repairable_json(
        path,
        expected_schema=SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
        expected_keys=REVIEWED_EVIDENCE_KEYS,
    ) == "absent"
    payload = {key: None for key in REVIEWED_EVIDENCE_KEYS}
    payload["schema_version"] = SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION
    path.write_bytes(pretty_json_bytes(payload))
    assert classify_repairable_json(
        path,
        expected_schema=SURVEY_REVIEWED_EVIDENCE_STATUS_SCHEMA_VERSION,
        expected_keys=REVIEWED_EVIDENCE_KEYS,
    ) == "replay_candidate"


def test_source_intake_authority_binds_id_path_hash_and_common_root(tmp_path: Path) -> None:
    status, record, _ = _source_intake(tmp_path)
    authority = validate_source_intake_authority(status)
    assert authority["paper_ids"] == ["paper_arxiv_2201_1a5af737"]
    assert authority["project_root"] == tmp_path / "project"
    assert authority["records_root"] == record.parent

    record.write_text("{}")
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "source_record_digest_mismatch"


@pytest.mark.parametrize(
    "paper_id",
    ["", ".", "..", "UPPER", "paper.id", "paper/id", "paper\\id", "-leading", "a" * 129],
)
def test_source_intake_rejects_unsafe_paper_ids(tmp_path: Path, paper_id: str) -> None:
    status = tmp_path / "status.json"
    _write_json(status, {
        "source_support": [{
            "paper_id": paper_id,
            "source_record_path": str(tmp_path / "record.json"),
            "source_record_sha256": "0" * 64,
        }],
    })
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_paper_id"


def test_source_intake_rejects_symlink_ancestor_and_mixed_roots(tmp_path: Path) -> None:
    status, record, payload = _source_intake(tmp_path)
    real_records = record.parent
    alias = tmp_path / "alias-records"
    alias.symlink_to(real_records, target_is_directory=True)
    payload["source_support"][0]["source_record_path"] = str(alias / record.name)
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_record_path"

    first_status, _, first_payload = _source_intake(tmp_path / "first", paper_id="paper_one")
    second_status, second_record, second_payload = _source_intake(tmp_path / "second", paper_id="paper_two")
    first_payload["source_support"].append(second_payload["source_support"][0])
    _write_json(first_status, first_payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(first_status)
    assert error.value.code == "mixed_source_record_roots"
    assert second_status.exists() and second_record.exists()


def test_source_intake_rejects_duplicate_id_and_never_infers_identity(tmp_path: Path) -> None:
    status, _, payload = _source_intake(tmp_path)
    payload["source_support"].append(dict(payload["source_support"][0]))
    payload["approved_candidate_ids"] = ["different-id"]
    payload["observed_candidate_ids"] = ["another-id"]
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "duplicate_source_paper_id"

    payload["source_support"] = [{
        "arxiv_id": "2201.12220",
        "source_record_path": payload["source_support"][0]["source_record_path"],
        "source_record_sha256": payload["source_support"][0]["source_record_sha256"],
    }]
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_paper_id"


@pytest.mark.parametrize("digest", [None, "ABC", "g" * 64, "0" * 63, 123])
def test_source_intake_rejects_missing_or_bad_digest(tmp_path: Path, digest) -> None:
    status, _, payload = _source_intake(tmp_path)
    if digest is None:
        payload["source_support"][0].pop("source_record_sha256")
    else:
        payload["source_support"][0]["source_record_sha256"] = digest
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_record_digest"


def test_source_intake_rejects_record_identity_and_path_paper_mismatch(tmp_path: Path) -> None:
    status, record, payload = _source_intake(tmp_path)
    record_payload = json.loads(record.read_text())
    record_payload["paper_id"] = "different_paper"
    _write_json(record, record_payload)
    payload["source_support"][0]["source_record_sha256"] = hashlib.sha256(record.read_bytes()).hexdigest()
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "source_record_identity_mismatch"

    status, record, payload = _source_intake(tmp_path / "path_mismatch")
    payload["source_support"][0]["paper_id"] = "different_paper"
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_record_path"


def test_source_intake_rejects_leaf_symlink_nonregular_and_nonnormalized_path(tmp_path: Path) -> None:
    status, record, payload = _source_intake(tmp_path / "symlink")
    outside = tmp_path / "outside-record.json"
    outside.write_bytes(record.read_bytes())
    record.unlink()
    record.symlink_to(outside)
    payload["source_support"][0]["source_record_sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_record_path"

    status, record, payload = _source_intake(tmp_path / "nonregular")
    record.unlink()
    record.mkdir()
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "unsafe_artifact_file"

    status, record, payload = _source_intake(tmp_path / "nonnormalized")
    payload["source_support"][0]["source_record_path"] = str(record.parent / ".." / "records" / record.name)
    _write_json(status, payload)
    with pytest.raises(MissionStateError) as error:
        validate_source_intake_authority(status)
    assert error.value.code == "invalid_source_record_path"


def test_canonical_output_preflight_and_observation_hash_are_fail_closed(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    mission.mkdir()
    assert preflight_mission_output(mission, mission / "source_anchors", name="source_anchors") == (
        mission / "source_anchors"
    )
    with pytest.raises(MissionStateError) as error:
        preflight_mission_output(mission, tmp_path / "outside", name="source_anchors")
    assert error.value.code == "noncanonical_supervisor_output"
    real_read_root = tmp_path / "real-read"
    real_read_root.mkdir()
    read_alias = tmp_path / "read-alias"
    read_alias.symlink_to(real_read_root, target_is_directory=True)
    with pytest.raises(MissionStateError) as error:
        validate_supervisor_read_root(read_alias, label="supplied read")
    assert error.value.code == "invalid_supervisor_read_root"

    first = {"mission_id": "m", "next_action": {"action_id": "a", "created_at": "one"}}
    second = {"mission_id": "m", "next_action": {"action_id": "a", "created_at": "two"}}
    assert observation_sha256(first) == observation_sha256(second)


def test_persisted_confirmation_safe_local_never_calls_provider_builder(tmp_path: Path, monkeypatch) -> None:
    mission = tmp_path / "mission"
    first = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        confirm_public_discovery=True,
        run_safe_local=True,
    )
    assert first["public_discovery_confirmation"]["confirmed"] is True
    assert first["local_supervisor"]["status"] == "terminal_blocked_external_or_future_phase"

    def forbidden(*args, **kwargs):
        raise AssertionError("safe-local observer called the provider-capable builder")

    monkeypatch.setattr("research_assistant.survey.orchestrate.build_survey_evidence_packet", forbidden)
    resumed = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        resume=True,
        run_safe_local=True,
    )
    assert resumed["local_supervisor"]["status"] == "terminal_blocked_external_or_future_phase"
    assert resumed["next_action"]["action_id"] == "public_metadata"


def test_safe_local_missing_source_intake_stops_at_phase6_handoff_without_transport(
    tmp_path: Path,
    monkeypatch,
) -> None:
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("missing source intake reached a product writer")

    monkeypatch.setattr(orchestrate, "build_source_anchor_packet", forbidden)
    monkeypatch.setattr(orchestrate, "compose_public_source_evidence_packet", forbidden)
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=tmp_path / "mission",
        metadata_dir=metadata,
        run_safe_local=True,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_source_intake"
    assert supervisor["terminal_action_id"] == "source_intake"
    assert [row["stage_id"] for row in supervisor["transition_history"]] == ["build_offline_skeleton"]


def test_safe_local_malformed_source_intake_blocks_before_anchor_dispatch(tmp_path: Path, monkeypatch) -> None:
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    source_status = tmp_path / "source_status"
    _write_json(source_status / "phase4_source_intake_status.json", {
        "status": "completed",
        "approved_candidate_ids": ["tempting-but-not-authoritative"],
    })

    def forbidden(*args, **kwargs):
        raise AssertionError("malformed source intake reached anchor dispatch")

    monkeypatch.setattr(orchestrate, "build_source_anchor_packet", forbidden)
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=tmp_path / "mission",
        metadata_dir=metadata,
        source_status_dir=source_status,
        run_safe_local=True,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_source_intake"
    assert supervisor["terminal_reason"] == "invalid_source_intake"
    assert all(row["stage_id"] != "source_anchors" for row in supervisor["transition_history"])


@pytest.mark.parametrize(
    ("stage", "write_order", "keep_count"),
    [
        *(('anchors', ANCHOR_OUTPUT_FILES, count) for count in range(1, len(ANCHOR_OUTPUT_FILES))),
        *(('packet', PUBLIC_SOURCE_PACKET_FILES, count) for count in range(1, len(PUBLIC_SOURCE_PACKET_FILES))),
    ],
)
def test_safe_local_partial_multifile_restart_is_terminal_invalid(
    tmp_path: Path,
    monkeypatch,
    stage: str,
    write_order: tuple[str, ...],
    keep_count: int,
) -> None:
    mission = tmp_path / "mission"
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    source_status = status.parent
    first = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        metadata_dir=metadata,
        source_status_dir=source_status,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_human_review"
    target = mission / ("source_anchors" if stage == "anchors" else "public_source_packet")
    keep = set(write_order[:keep_count])
    for path in list(target.iterdir()):
        if path.name not in keep:
            path.unlink()

    def forbidden(*args, **kwargs):
        raise AssertionError("partial output was rerun instead of rejected")

    monkeypatch.setattr(orchestrate, "build_source_anchor_packet", forbidden)
    monkeypatch.setattr(orchestrate, "compose_public_source_evidence_packet", forbidden)
    resumed = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        metadata_dir=metadata,
        source_status_dir=source_status,
        resume=True,
        run_safe_local=True,
    )
    assert resumed["local_supervisor"]["status"] == "terminal_blocked_invalid_artifact"
    assert resumed["local_supervisor"]["terminal_reason"] == "incomplete_stage_artifact"
    assert {path.name for path in target.iterdir()} == keep


def test_safe_local_complete_stage_paths_use_manifest_values(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        metadata_dir=metadata,
        source_status_dir=status.parent,
        run_safe_local=True,
    )
    history = {row["stage_id"]: row for row in result["local_supervisor"]["transition_history"]}
    anchor_paths = {Path(value).name for value in history["source_anchors"]["stage_result"]["required_output_paths"]}
    packet_paths = {Path(value).name for value in history["public_source_packet"]["stage_result"]["required_output_paths"]}
    assert anchor_paths == {path.name for path in (mission / "source_anchors").iterdir()}
    assert packet_paths == {path.name for path in (mission / "public_source_packet").iterdir()}
    validate_anchor_packet(
        mission / "source_anchors",
        source_status_path=status,
        expected_topic="Neural Optimal Transport",
    )
    validate_public_source_packet(
        mission / "public_source_packet",
        metadata_dir=metadata,
        source_status_dir=status.parent,
        anchor_dir=mission / "source_anchors",
    )


def test_supervisor_observer_is_byte_read_only_for_existing_and_supplied_roots(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    first = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        metadata_dir=metadata,
        source_status_dir=status.parent,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_human_review"

    manager = MissionStateManager(
        output_dir=mission,
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        confirm_public_discovery=False,
        resume=True,
        force=False,
    )
    snapshot = manager.begin()
    roots = {
        "metadata": metadata.absolute(),
        "source_status": status.parent.absolute(),
        "anchor": (mission / "source_anchors").absolute(),
        "packet": (mission / "public_source_packet").absolute(),
    }
    before = {
        root: _tree_snapshot(root)
        for root in [mission, metadata, status.parent]
    }
    observation = orchestrate._supervisor_observe(
        manager=manager,
        snapshot=snapshot,
        output_dir=mission,
        resume=True,
        roots=roots,
        supplied={"anchor": True, "packet": True},
        coverage_dir=None,
        reviewed_claims_dir=None,
        reviewed_source_safety_dir=None,
        reviewed_omissions_dir=None,
        reviewed_workflow_blockers_dir=None,
        reviewed_evidence_dir=None,
        local_evidence_root=None,
    )
    after = {
        root: _tree_snapshot(root)
        for root in [mission, metadata, status.parent]
    }
    manager.abort()
    assert observation["next_action"]["action_id"] == "import_reviewed_claims"
    assert after == before


def test_supervisor_holds_mission_lock_during_typed_stage(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "mission"
    observed_lock = False

    def dispatch(*, output_dir, **kwargs):
        nonlocal observed_lock
        contender = run_public_source_workflow(
            topic="Neural Optimal Transport",
            seeds=["arxiv:2201.12220"],
            output_dir=output_dir,
            resume=True,
            run_safe_local=True,
        )
        assert contender["status"] == "blocked"
        assert contender["blocked_reason"] == "mission_locked"
        observed_lock = True
        marker = output_dir / "synthetic-output.json"
        marker.write_text("{}")
        return {"schema_version": "synthetic-v1", "status": "success", "required_output_paths": [str(marker)]}

    _, result = _run_synthetic_supervisor(
        tmp_path,
        monkeypatch,
        observations=[("build_offline_skeleton", 0), ("build_offline_skeleton", 0)],
        dispatch=dispatch,
    )
    assert observed_lock is True
    assert result["local_supervisor"]["status"] == "terminal_blocked_no_progress"
    assert not (output / ".mission.lock").exists()


def test_supplied_missing_anchor_and_packet_roots_remain_read_only(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    missing_anchor = tmp_path / "external-anchor"
    blocked_anchor = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=tmp_path / "anchor-mission",
        metadata_dir=metadata,
        source_status_dir=status.parent,
        anchor_dir=missing_anchor,
        run_safe_local=True,
    )
    assert blocked_anchor["local_supervisor"]["status"] == "terminal_blocked_invalid_artifact"
    assert blocked_anchor["local_supervisor"]["terminal_reason"] == "supplied_anchor_root_is_read_only_and_missing"
    assert not missing_anchor.exists()

    source_mission = tmp_path / "source-mission"
    source = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=source_mission,
        metadata_dir=metadata,
        source_status_dir=status.parent,
        run_safe_local=True,
    )
    assert source["local_supervisor"]["status"] == "terminal_blocked_human_review"
    complete_anchor = source_mission / "source_anchors"
    missing_packet = tmp_path / "external-packet"
    blocked_packet = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=tmp_path / "packet-mission",
        metadata_dir=metadata,
        source_status_dir=status.parent,
        anchor_dir=complete_anchor,
        packet_dir=missing_packet,
        run_safe_local=True,
    )
    assert blocked_packet["local_supervisor"]["status"] == "terminal_blocked_invalid_artifact"
    assert blocked_packet["local_supervisor"]["terminal_reason"] == "supplied_packet_root_is_read_only_and_missing"
    assert not missing_packet.exists()


def test_safe_local_reclaims_stale_owner_before_dispatch(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "mission"
    first = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=output,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    stale = {
        "schema_version": LOCK_SCHEMA,
        "owner_token": "a" * 32,
        "pid": 999_999_999,
        "hostname": socket.gethostname(),
        "acquired_at": "2026-07-11T00:00:00+00:00",
        "acquired_epoch": time.time() - 1000,
    }
    (output / ".mission.lock").write_bytes(canonical_json_bytes(stale))

    def forbidden(*args, **kwargs):
        raise AssertionError("stale-lock recovery reran a completed writer")

    monkeypatch.setattr(orchestrate, "build_survey_evidence_packet", forbidden)
    resumed = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=output,
        resume=True,
        run_safe_local=True,
    )
    assert resumed["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    assert resumed["local_supervisor"]["transition_history"] == []
    assert not (output / ".mission.lock").exists()


def test_complete_writer_survives_post_dispatch_observer_failure_and_restart(tmp_path: Path, monkeypatch) -> None:
    mission = tmp_path / "mission"
    original_observe = orchestrate._supervisor_observe
    observe_count = 0

    def fail_after_first_dispatch(**kwargs):
        nonlocal observe_count
        observe_count += 1
        if observe_count == 2:
            raise RuntimeError("injected post-dispatch observer failure")
        return original_observe(**kwargs)

    monkeypatch.setattr(orchestrate, "_supervisor_observe", fail_after_first_dispatch)
    interrupted = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        run_safe_local=True,
    )
    assert interrupted["status"] == "blocked"
    assert interrupted["blocked_reason"] == "supervisor_reobservation_failed"
    skeleton_before = _tree_snapshot(mission / "offline_skeleton")
    assert skeleton_before
    monkeypatch.undo()

    resumed = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        resume=True,
        run_safe_local=True,
    )
    assert resumed["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    assert resumed["local_supervisor"]["transition_history"] == []
    assert _tree_snapshot(mission / "offline_skeleton") == skeleton_before


def test_partial_writer_exception_is_reobserved_as_invalid_artifact(tmp_path: Path, monkeypatch) -> None:
    mission = tmp_path / "mission"

    def partial_writer(*, output_dir, **kwargs):
        output_dir.mkdir()
        (output_dir / "build_manifest.json").write_text("{}")
        raise RuntimeError("injected partial writer crash")

    monkeypatch.setattr(orchestrate, "build_survey_evidence_packet", partial_writer)
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        run_safe_local=True,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_invalid_artifact"
    assert supervisor["terminal_reason"] == "incomplete_stage_artifact"
    assert supervisor["transition_history"][0]["stage_result"]["exception_class"] == "RuntimeError"
    assert (mission / "offline_skeleton" / "build_manifest.json").read_text() == "{}"


def test_safe_local_builds_anchors_packet_and_selected_queue_then_stops_for_review(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission = tmp_path / "mission"
    metadata = tmp_path / "metadata"
    metadata_result = build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    assert metadata_result["status"] == "created_skeleton"
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    source_status = status.parent

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("safe-local path attempted provider collection")

    monkeypatch.setattr("research_assistant.survey.build._collect_public_metadata", forbidden_provider)
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        metadata_dir=metadata,
        source_status_dir=source_status,
        run_safe_local=True,
    )

    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_human_review"
    assert [row["stage_id"] for row in supervisor["transition_history"]] == [
        "build_offline_skeleton",
        "source_anchors",
        "public_source_packet",
        "initialize_artifact_state",
    ]
    assert result["next_action"]["action_id"] == "import_reviewed_claims"
    assert (mission / "source_anchors" / "anchor_extraction_manifest.json").is_file()
    assert (mission / "public_source_packet" / "build_manifest.json").is_file()
    assert (mission / ".artifact_state" / "CURRENT").is_file()
    assert result["review_queue_path"] is not None
    assert Path(result["review_queue_path"]).is_file()


def test_supervisor_rejects_unknown_action_without_dispatching_command_text(tmp_path: Path, monkeypatch) -> None:
    called = False

    def forbidden_dispatch(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("unknown action reached typed dispatch")

    output, result = _run_synthetic_supervisor(
        tmp_path,
        monkeypatch,
        observations=[("unknown_action", 0)],
        dispatch=forbidden_dispatch,
    )
    assert called is False
    assert result["local_supervisor"]["status"] == "terminal_blocked_external_or_future_phase"
    assert result["local_supervisor"]["transition_history"] == []
    assert result["next_action"]["safe_next_commands"] == ["forbidden-command-0"]
    assert not any(path.name.startswith("forbidden-command") for path in output.rglob("*"))


def test_supervisor_success_without_declared_output_is_stage_failure(tmp_path: Path, monkeypatch) -> None:
    def dispatch(**kwargs):
        return {"schema_version": "synthetic-v1", "status": "success", "required_output_paths": []}

    _, result = _run_synthetic_supervisor(
        tmp_path,
        monkeypatch,
        observations=[("build_offline_skeleton", 0), ("build_offline_skeleton", 0)],
        dispatch=dispatch,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_stage_failure"
    assert supervisor["terminal_reason"] == "missing_supervisor_stage_outputs"
    assert supervisor["transition_history"][0]["post_dispatch_outcome"] == "stage_failed"


def test_supervisor_detects_no_progress_after_one_dispatch(tmp_path: Path, monkeypatch) -> None:
    def dispatch(*, output_dir, **kwargs):
        marker = output_dir / "synthetic-output.json"
        marker.write_text("{}")
        return {
            "schema_version": "synthetic-v1",
            "status": "success",
            "required_output_paths": [str(marker)],
        }

    _, result = _run_synthetic_supervisor(
        tmp_path,
        monkeypatch,
        observations=[("build_offline_skeleton", 0), ("build_offline_skeleton", 0)],
        dispatch=dispatch,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_no_progress"
    assert supervisor["transition_count"] == 1
    assert supervisor["transition_history"][0]["post_dispatch_outcome"] == "no_progress"


def test_supervisor_detects_two_state_cycle(tmp_path: Path, monkeypatch) -> None:
    counter = 0

    def dispatch(*, output_dir, **kwargs):
        nonlocal counter
        counter += 1
        marker = output_dir / f"synthetic-output-{counter}.json"
        marker.write_text("{}")
        return {
            "schema_version": "synthetic-v1",
            "status": "success",
            "required_output_paths": [str(marker)],
        }

    _, result = _run_synthetic_supervisor(
        tmp_path,
        monkeypatch,
        observations=[
            ("build_offline_skeleton", 0),
            ("build_offline_skeleton", 1),
            ("build_offline_skeleton", 1),
            ("build_offline_skeleton", 0),
        ],
        dispatch=dispatch,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_cycle"
    assert supervisor["transition_count"] == 2
    assert supervisor["transition_history"][-1]["post_dispatch_outcome"] == "cycle"


def test_supervisor_stops_before_thirteenth_dispatch(tmp_path: Path, monkeypatch) -> None:
    dispatch_count = 0

    def dispatch(*, output_dir, **kwargs):
        nonlocal dispatch_count
        dispatch_count += 1
        marker = output_dir / f"synthetic-output-{dispatch_count}.json"
        marker.write_text("{}")
        return {
            "schema_version": "synthetic-v1",
            "status": "success",
            "required_output_paths": [str(marker)],
        }

    observations = [("build_offline_skeleton", 0)]
    for index in range(1, 13):
        observations.extend([
            ("build_offline_skeleton", index),
            ("build_offline_skeleton", index),
        ])
    _, result = _run_synthetic_supervisor(tmp_path, monkeypatch, observations=observations, dispatch=dispatch)
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_transition_limit"
    assert supervisor["transition_count"] == 12
    assert dispatch_count == 12
    assert [row["transition_index"] for row in supervisor["transition_history"]] == list(range(12))


def test_supervisor_stage_exception_commits_bounded_terminal_and_releases_lock(tmp_path: Path, monkeypatch) -> None:
    def dispatch(**kwargs):
        raise RuntimeError("sensitive exception text must not be persisted")

    output, result = _run_synthetic_supervisor(
        tmp_path,
        monkeypatch,
        observations=[("build_offline_skeleton", 0), ("build_offline_skeleton", 1)],
        dispatch=dispatch,
    )
    supervisor = result["local_supervisor"]
    assert supervisor["status"] == "terminal_blocked_stage_failure"
    stage = supervisor["transition_history"][0]["stage_result"]
    assert stage["exception_class"] == "RuntimeError"
    assert stage["error_code"] == "unexpected_stage_exception"
    assert "sensitive exception text" not in json.dumps(supervisor)
    assert (output / ".mission_state" / "CURRENT").is_file()
    monkeypatch.undo()
    resumed = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=output,
        resume=True,
        run_safe_local=True,
    )
    assert resumed["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"


def test_anchor_validator_rejects_extra_key_and_same_schema_count_tampering(tmp_path: Path) -> None:
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    output = tmp_path / "anchors"
    authority = validate_source_intake_authority(status)
    build_source_anchor_packet(
        paper_ids=authority["paper_ids"],
        output_dir=output,
        topic="Neural Optimal Transport",
        root=authority["project_root"],
    )
    manifest_path = output / "anchor_extraction_manifest.json"
    original = manifest_path.read_bytes()
    manifest = json.loads(original)
    manifest["extra"] = True
    _write_json(manifest_path, manifest)
    with pytest.raises(MissionStateError) as error:
        validate_anchor_packet(
            output,
            source_status_path=status,
            expected_topic="Neural Optimal Transport",
        )
    assert error.value.code == "invalid_stage_artifact"

    manifest_path.write_bytes(original)
    inventory_path = output / "source_anchor_inventory.json"
    inventory = json.loads(inventory_path.read_bytes())
    inventory["anchor_count"] += 1
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True))
    with pytest.raises(MissionStateError) as error:
        validate_anchor_packet(
            output,
            source_status_path=status,
            expected_topic="Neural Optimal Transport",
        )
    assert error.value.code == "invalid_anchor_packet"


@pytest.mark.parametrize(
    ("artifact_name", "mutate"),
    [
        ("source_anchor_inventory.json", lambda payload: payload["anchors"][0].__setitem__("raw_latex_sha256", "0" * 64)),
        ("source_anchor_inventory.json", lambda payload: payload["anchors"][0].__setitem__("role", "forged_anchor_role")),
        ("source_support.json", lambda payload: payload["papers"][0].__setitem__("section_count", 999)),
        ("quarantine_register.json", lambda payload: payload["rows"][0].__setitem__("claim_support_allowed", True)),
    ],
)
def test_anchor_validator_replays_row_semantics_from_attested_source_records(
    tmp_path: Path,
    artifact_name: str,
    mutate,
) -> None:
    status, record, status_payload = _source_intake(tmp_path / "source_fixture")
    record_payload = json.loads(record.read_bytes())
    record_payload["sections"] = [{
        "title": "Method",
        "labels": ["sec:method"],
        "line": 10,
        "raw_latex": "A bounded method anchor.",
    }]
    _write_json(record, record_payload)
    status_payload["source_support"][0]["source_record_sha256"] = hashlib.sha256(record.read_bytes()).hexdigest()
    _write_json(status, status_payload)
    authority = validate_source_intake_authority(status)
    output = tmp_path / "anchors"
    build_source_anchor_packet(
        paper_ids=authority["paper_ids"],
        output_dir=output,
        topic="Neural Optimal Transport",
        root=authority["project_root"],
    )
    validate_anchor_packet(
        output,
        source_status_path=status,
        expected_topic="Neural Optimal Transport",
    )
    path = output / artifact_name
    payload = json.loads(path.read_bytes())
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    with pytest.raises(MissionStateError) as error:
        validate_anchor_packet(
            output,
            source_status_path=status,
            expected_topic="Neural Optimal Transport",
        )
    assert error.value.code == "invalid_anchor_packet_replay"


def test_public_packet_validator_rejects_same_schema_output_tampering(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    status, _, _ = _source_intake(tmp_path / "source_fixture")
    authority = validate_source_intake_authority(status)
    anchors = tmp_path / "anchors"
    build_source_anchor_packet(
        paper_ids=authority["paper_ids"],
        output_dir=anchors,
        topic="Neural Optimal Transport",
        root=authority["project_root"],
    )
    packet = tmp_path / "packet"
    from research_assistant.survey.packet import compose_public_source_evidence_packet

    compose_public_source_evidence_packet(
        topic="Neural Optimal Transport",
        output_dir=packet,
        metadata_dir=metadata,
        source_status_dir=status.parent,
        anchor_dir=anchors,
    )
    claims_path = packet / "claim_support.json"
    claims = json.loads(claims_path.read_bytes())
    claims["status"] = "same_schema_tampered"
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True))
    with pytest.raises(MissionStateError) as error:
        validate_public_source_packet(
            packet,
            metadata_dir=metadata,
            source_status_dir=status.parent,
            anchor_dir=anchors,
        )
    assert error.value.code == "invalid_public_source_packet_replay"


@pytest.mark.parametrize("shape", ["symlink", "wrong_schema"])
def test_safe_local_packet_inputs_block_before_composer_or_output(
    tmp_path: Path,
    monkeypatch,
    shape: str,
) -> None:
    mission = tmp_path / "mission"
    initialized = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        run_safe_local=True,
    )
    assert initialized["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    metadata = mission / "public_metadata"
    build_survey_evidence_packet(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=metadata,
        mode="offline-skeleton",
    )
    status, _, _ = _source_intake(mission)
    authority = validate_source_intake_authority(status)
    anchors = mission / "source_anchors"
    build_source_anchor_packet(
        paper_ids=authority["paper_ids"],
        output_dir=anchors,
        topic="Neural Optimal Transport",
        root=authority["project_root"],
    )
    candidate = metadata / "candidate_ledger.json"
    if shape == "symlink":
        outside = tmp_path / "outside-candidate.json"
        outside.write_bytes(candidate.read_bytes())
        candidate.unlink()
        candidate.symlink_to(outside)
    else:
        payload = json.loads(candidate.read_bytes())
        payload["schema_version"] = "wrong"
        _write_json(candidate, payload)

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid packet input reached the packet composer")

    monkeypatch.setattr(orchestrate, "compose_public_source_evidence_packet", forbidden)
    result = run_public_source_workflow(
        topic="Neural Optimal Transport",
        seeds=["arxiv:2201.12220"],
        output_dir=mission,
        metadata_dir=metadata,
        source_status_dir=status.parent,
        anchor_dir=anchors,
        resume=True,
        run_safe_local=True,
    )
    assert result["local_supervisor"]["status"] == "terminal_blocked_invalid_artifact"
    assert result["local_supervisor"]["transition_history"] == []
    assert not (mission / "public_source_packet").exists()
