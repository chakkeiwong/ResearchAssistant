from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey.artifact_lineage import (
    COVERAGE_FILES,
    ArtifactStateManager,
    assert_public_write_path_allowed,
    classify_review_queue_digest,
    semantic_item,
    validate_selected_coverage_dir,
    validate_selected_review_queue,
    validate_semantic_items,
    workflow_blocker_source_id,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
)


MISSION_ID = "11111111-1111-4111-8111-111111111111"
FINGERPRINT = "3e0454920753d0da938c14014a24bbd7cb616d8285e2cafcc6a2d7bd729f2433"
GENERATION_ID = "g00000001-fe75fa3a7d15b861"
NONCE_1 = "000102030405060708090a0b0c0d0e0f"
NONCE_2 = "101112131415161718191a1b1c1d1e1f"


def _manager(
    root: Path,
    *,
    nonce: str = NONCE_1,
    crash_at: str | None = None,
    mission_id: str = MISSION_ID,
    fingerprint: str = FINGERPRINT,
    generation_id: str = GENERATION_ID,
) -> ArtifactStateManager:
    def crash_hook(label: str) -> None:
        if label == crash_at:
            raise RuntimeError(f"injected crash at {label}")

    return ArtifactStateManager(
        mission_root=root,
        mission_id=mission_id,
        mission_fingerprint=fingerprint,
        mission_anchor_generation_id=generation_id,
        nonce_factory=lambda: nonce,
        crash_hook=crash_hook if crash_at else None,
    )


def _commit_mission(root: Path) -> tuple[str, str, str]:
    manager = MissionStateManager(
        output_dir=root,
        topic="Phase 2 artifact lineage fixture",
        seeds=["arxiv:0000.00001"],
        confirm_public_discovery=False,
        resume=False,
        force=False,
        now=lambda: "2026-07-11T00:00:00+00:00",
        nonce_factory=lambda: NONCE_1,
        mission_id_factory=lambda: MISSION_ID,
    )
    manager.begin()
    committed = manager.commit(
        {
            "status": "ready_for_local_continuation",
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:00:00+00:00",
            "topic": "Phase 2 artifact lineage fixture",
            "seeds": ["arxiv:0000.00001"],
            "output_dir": str(root),
        },
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "fixture",
            "mission_status": "ready_for_local_continuation",
            "action_id": "fixture",
        },
    )
    assert committed.current_pointer is not None
    return (
        committed.contract["mission_id"],
        committed.contract["mission_fingerprint"],
        committed.current_pointer["generation_id"],
    )


def _packet(root: Path) -> Path:
    packet = root / "packet"
    packet.mkdir(parents=True)
    payloads = {
        "candidate_ledger.json": {"schema_version": "candidate-v1", "included": []},
        "citation_map.json": {"schema_version": "citation-v1", "frontiers": []},
        "paper_classifications.json": {"schema_version": "classifications-v1", "classifications": []},
        "omission_risk.json": {"schema_version": "omission-v1", "risks": []},
        "claim_support.json": {"schema_version": "claims-v1", "claim_candidates": []},
        "source_safety_status.json": {"schema_version": "safety-v1", "rows": []},
        "build_manifest.json": {"schema_version": "packet-v1", "workflow_state": {"blocked_reasons": []}},
    }
    for name, payload in payloads.items():
        (packet / name).write_bytes(canonical_json_bytes(payload))
    return packet


def _coverage() -> dict[str, dict]:
    return {
        name: {
            "schema_version": f"test-{name}-v1",
            "status": "fixture",
            "rows": [],
            "what_is_not_concluded": ["literature completeness"],
        }
        for name in COVERAGE_FILES
    }


def _queue(*, blocker: str = "Inspect unresolved frontier") -> dict:
    item = semantic_item(
        queue_type="workflow_blocker",
        source_id=workflow_blocker_source_id(blocker),
        semantic_fields={
            "reason": blocker,
            "status": "blocked_pending_evidence",
            "ready_for_prose": False,
            "action_required": "resolve the blocker",
        },
    )
    return {
        "status": "review_required",
        "topic": "fixture topic",
        "items": [item],
        "queue_counts": {
            "total": 1,
            "by_type": {"workflow_blocker": 1},
            "by_priority": {"None": 1},
            "by_status": {"blocked_pending_evidence": 1},
        },
        "allowed_item_statuses": ["blocked_pending_evidence"],
        "forbidden_promotions": ["workflow blockers cannot be cleared by queue creation"],
        "what_is_not_concluded": ["literature completeness"],
    }


def _compose(manager: ArtifactStateManager, packet: Path, *, blocker: str = "Inspect unresolved frontier"):
    return manager.compose_and_select(
        packet_dir=packet,
        coverage_payloads=_coverage(),
        review_queue_payload=_queue(blocker=blocker),
    )


def test_immutable_set_is_deterministic_and_selected_paths_validate(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    mission_id, fingerprint, generation_id = _commit_mission(root)
    packet = _packet(root)
    first = _compose(_manager(
        root,
        mission_id=mission_id,
        fingerprint=fingerprint,
        generation_id=generation_id,
    ), packet)
    pointer_before = (root / ".artifact_state" / "CURRENT").read_bytes()
    manifest_before = (first.set_dir / "artifact_set_manifest.json").read_bytes()

    resumed = _compose(_manager(
        root,
        nonce=NONCE_2,
        mission_id=mission_id,
        fingerprint=fingerprint,
        generation_id=generation_id,
    ), packet)
    assert resumed.artifact_set_id == first.artifact_set_id
    assert resumed.set_dir == first.set_dir
    assert (root / ".artifact_state" / "CURRENT").read_bytes() == pointer_before
    assert (resumed.set_dir / "artifact_set_manifest.json").read_bytes() == manifest_before
    assert validate_selected_review_queue(resumed.review_queue_path).artifact_set_id == first.artifact_set_id
    assert validate_selected_coverage_dir(resumed.coverage_dir).artifact_set_id == first.artifact_set_id


def test_packet_change_selects_new_set_and_old_queue_is_stale(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    first = _compose(_manager(root), packet)
    claim_path = packet / "claim_support.json"
    claim = json.loads(claim_path.read_text())
    claim["claim_candidates"] = [{"claim_id": "new", "status": "candidate"}]
    claim_path.write_bytes(canonical_json_bytes(claim))

    second = _compose(_manager(root, nonce=NONCE_2), packet)
    assert second.artifact_set_id != first.artifact_set_id
    assert first.set_dir.exists()
    with pytest.raises(MissionStateError) as error:
        _manager(root, nonce=NONCE_2).validate_selected_path(first.review_queue_path, role="review_queue")
    assert error.value.code == "stale_lineage"


def test_selected_member_corruption_blocks_without_moving_current(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    snapshot = _compose(_manager(root), packet)
    pointer_before = (root / ".artifact_state" / "CURRENT").read_bytes()
    snapshot.review_queue_path.write_text("{}\n")

    with pytest.raises(MissionStateError) as error:
        _manager(root, nonce=NONCE_2).load_current()
    assert error.value.code == "corrupt_selected_lineage"
    assert (root / ".artifact_state" / "CURRENT").read_bytes() == pointer_before


@pytest.mark.parametrize(
    "crash_at",
    [
        "artifact_genesis:after_temp_write",
        "artifact_genesis:after_temp_fsync",
        "artifact_genesis:after_replace",
        "artifact_genesis:after_directory_fsync",
    ],
)
def test_genesis_crash_is_absent_or_complete_and_retry_succeeds(tmp_path: Path, crash_at: str) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    with pytest.raises(RuntimeError):
        _manager(root, crash_at=crash_at).ensure_genesis()
    genesis = root / ".artifact_state" / "GENESIS"
    if genesis.exists():
        assert json.loads(genesis.read_text())["mission_id"] == MISSION_ID

    retry = _manager(root, nonce=NONCE_2)
    assert retry.ensure_genesis()["mission_id"] == MISSION_ID
    report = retry._recovery_report()
    assert all(name.startswith(".GENESIS.") for name in report["temp_files"])


def test_final_orphan_set_and_current_temp_residue_allow_retry(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    crashing = _manager(root, crash_at="artifact_set:after_final_rename")
    with pytest.raises(RuntimeError):
        _compose(crashing, packet)
    assert not (root / ".artifact_state" / "CURRENT").exists()
    final_sets = [path for path in (root / ".artifact_state" / "sets").iterdir() if not path.name.startswith(".staging-")]
    assert len(final_sets) == 1

    resumed = _compose(_manager(root, nonce=NONCE_2), packet)
    assert resumed.set_dir == final_sets[0]
    assert (root / ".artifact_state" / "CURRENT").exists()

    current_before = (root / ".artifact_state" / "CURRENT").read_bytes()
    changed = "Another blocker"
    crashing_current = _manager(root, nonce="202122232425262728292a2b2c2d2e2f", crash_at="artifact_current:after_temp_fsync")
    with pytest.raises(RuntimeError):
        _compose(crashing_current, packet, blocker=changed)
    assert (root / ".artifact_state" / "CURRENT").read_bytes() == current_before
    retried = _compose(_manager(root, nonce="303132333435363738393a3b3c3d3e3f"), packet, blocker=changed)
    assert retried.artifact_set_id != resumed.artifact_set_id
    assert any(name.startswith(".CURRENT.") for name in retried.recovery["temp_files"])


def test_semantic_item_ids_are_stable_and_collisions_block() -> None:
    first = semantic_item(queue_type="claim_candidate", source_id="claim-1", semantic_fields={"status": "review_required"})
    same = semantic_item(queue_type="claim_candidate", source_id="claim-1", semantic_fields={"status": "review_required"})
    changed = semantic_item(queue_type="claim_candidate", source_id="claim-1", semantic_fields={"status": "blocked"})
    assert first["item_id"] == same["item_id"]
    assert first["item_id"] != changed["item_id"]
    with pytest.raises(MissionStateError) as error:
        validate_semantic_items([first, same])
    assert error.value.code == "duplicate_queue_semantic_key"


@pytest.mark.parametrize(
    ("relative", "code"),
    [
        (".artifact_state", "protected_artifact_state_write"),
        (".artifact_state/sets/new", "protected_artifact_state_write"),
        (".artifact_state/missing/leaf", "protected_artifact_state_write"),
        (".mission_state", "protected_mission_state_write"),
        (".mission_state/generations/new", "protected_mission_state_write"),
        (".mission_state/missing/leaf", "protected_mission_state_write"),
    ],
)
def test_public_writer_rejects_protected_root_and_missing_descendants(
    tmp_path: Path,
    relative: str,
    code: str,
) -> None:
    root = tmp_path / "mission"
    (root / ".artifact_state" / "sets").mkdir(parents=True)
    target = root / relative
    with pytest.raises(MissionStateError) as error:
        assert_public_write_path_allowed(target)
    assert error.value.code == code
    assert not (root / relative.split("/")[0] / "missing").exists()


def test_public_writer_rejects_symlink_into_protected_root(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    state = root / ".artifact_state"
    state.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(state, target_is_directory=True)
    with pytest.raises(MissionStateError) as error:
        assert_public_write_path_allowed(alias / "new-output")
    assert error.value.code == "unsafe_public_write_path"


def test_malformed_current_temp_and_unsafe_staging_block(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    manager = _manager(root)
    manager.ensure_genesis()
    malformed = root / ".artifact_state" / ".CURRENT.BAD.tmp"
    malformed.write_text("x")
    with pytest.raises(MissionStateError) as error:
        manager.load_current(required=False)
    assert error.value.code == "unexpected_artifact_state_path"

    malformed.unlink()
    staging = root / ".artifact_state" / "sets" / f".staging-s-{'0' * 64}-{NONCE_1}"
    staging.mkdir()
    (staging / "unexpected").write_text("x")
    with pytest.raises(MissionStateError) as error:
        manager.load_current(required=False)
    assert error.value.code == "unexpected_artifact_staging_path"


SET_CRASH_BOUNDARIES = [
    "artifact_set:after_staging_parent_fsync",
    *[
        f"artifact_set:{relative}:{suffix}"
        for relative in [
            *(f"coverage/{name}" for name in COVERAGE_FILES),
            "coverage/coverage_manifest.json",
            "review_queue.json",
            "artifact_set_manifest.json",
        ]
        for suffix in ("after_write", "after_fsync")
    ],
    "artifact_set:after_staging_fsync",
    "artifact_set:after_final_rename",
    "artifact_set:after_sets_fsync",
]


@pytest.mark.parametrize("crash_at", SET_CRASH_BOUNDARIES)
def test_every_artifact_set_crash_boundary_allows_deterministic_retry(
    tmp_path: Path,
    crash_at: str,
) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    with pytest.raises(RuntimeError):
        _compose(_manager(root, crash_at=crash_at), packet)

    retry = _compose(_manager(root, nonce=NONCE_2), packet)
    assert retry.review_queue_path.is_file()
    assert retry.coverage_dir.is_dir()
    assert retry.artifact_set_id == _compose(
        _manager(root, nonce="202122232425262728292a2b2c2d2e2f"),
        packet,
    ).artifact_set_id


@pytest.mark.parametrize(
    "crash_at",
    [
        "artifact_current:after_temp_write",
        "artifact_current:after_temp_fsync",
        "artifact_current:after_replace",
        "artifact_current:after_directory_fsync",
    ],
)
def test_every_selector_crash_boundary_exposes_complete_set_and_retries(
    tmp_path: Path,
    crash_at: str,
) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    with pytest.raises(RuntimeError):
        _compose(_manager(root, crash_at=crash_at), packet)

    current = root / ".artifact_state" / "CURRENT"
    if current.exists():
        selected = _manager(root, nonce=NONCE_2).load_current()
        assert selected is not None and selected.review_queue_path.is_file()
    retry = _compose(_manager(root, nonce=NONCE_2), packet)
    assert retry.review_queue_path.is_file()
    assert retry.coverage_dir.is_dir()


def test_semantic_items_are_stable_under_reorder_after_canonical_sort() -> None:
    first = semantic_item(
        queue_type="claim_candidate",
        source_id="claim-1",
        semantic_fields={"status": "review_required", "priority": "high"},
    )
    second = semantic_item(
        queue_type="source_safety",
        source_id="paper-1",
        semantic_fields={"status": "blocked_pending_evidence", "priority": "high"},
    )
    key = lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"])
    canonical_first = validate_semantic_items(sorted([first, second], key=key))
    canonical_second = validate_semantic_items(sorted([second, first], key=key))
    assert canonical_first == canonical_second


@pytest.mark.parametrize("source_id", [None, "", "   "])
def test_missing_semantic_source_identity_blocks(source_id: object) -> None:
    with pytest.raises(MissionStateError) as error:
        semantic_item(
            queue_type="claim_candidate",
            source_id=source_id,  # type: ignore[arg-type]
            semantic_fields={"status": "review_required"},
        )
    assert error.value.code == "invalid_semantic_identity"


def test_existing_corrupt_state_is_not_repaired_before_validation(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    _compose(_manager(root), packet)
    sets_dir = root / ".artifact_state" / "sets"
    moved = root / "saved-sets"
    sets_dir.rename(moved)

    with pytest.raises(MissionStateError) as error:
        _compose(_manager(root, nonce=NONCE_2), packet)
    assert error.value.code == "corrupt_selected_lineage"
    assert not sets_dir.exists()
    assert moved.exists()


def test_selected_path_alias_is_not_accepted_as_authority(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    selected = _compose(_manager(root), packet)
    alias = root / "queue-alias.json"
    alias.symlink_to(selected.review_queue_path)

    with pytest.raises(MissionStateError) as error:
        _manager(root, nonce=NONCE_2).validate_selected_path(alias, role="review_queue")
    assert error.value.code == "stale_lineage"


def test_review_queue_digest_classifies_current_prior_and_forged(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    mission_id, fingerprint, generation_id = _commit_mission(root)
    packet = _packet(root)
    first = _compose(_manager(
        root,
        mission_id=mission_id,
        fingerprint=fingerprint,
        generation_id=generation_id,
    ), packet)
    first_digest = hashlib.sha256(first.review_queue_path.read_bytes()).hexdigest()
    second = _compose(_manager(
        root,
        nonce=NONCE_2,
        mission_id=mission_id,
        fingerprint=fingerprint,
        generation_id=generation_id,
    ), packet, blocker="Changed blocker")
    second_digest = hashlib.sha256(second.review_queue_path.read_bytes()).hexdigest()

    assert classify_review_queue_digest(second.review_queue_path, second_digest) == "current_lineage"
    assert classify_review_queue_digest(second.review_queue_path, first_digest) == "stale_lineage"
    assert classify_review_queue_digest(second.review_queue_path, "0" * 64) == "corrupt_downstream_lineage"


def test_nonempty_sets_without_genesis_block_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    sets = root / ".artifact_state" / "sets"
    sets.mkdir(parents=True)
    marker = sets / "unexpected"
    marker.mkdir()

    with pytest.raises(MissionStateError) as error:
        _manager(root).ensure_genesis()
    assert error.value.code == "artifact_sets_without_genesis"
    assert not (root / ".artifact_state" / "GENESIS").exists()
    assert marker.exists()


def test_current_without_genesis_blocks_before_anchor_creation(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    state = root / ".artifact_state"
    (state / "sets").mkdir(parents=True)
    (state / "CURRENT").write_bytes(canonical_json_bytes({
        "schema_version": "ra-survey-artifact-state-current-v1",
        "artifact_set_id": f"s-{'0' * 64}",
        "artifact_set_manifest_sha256": "0" * 64,
    }))

    with pytest.raises(MissionStateError) as error:
        _manager(root).ensure_genesis()
    assert error.value.code == "missing_artifact_genesis"
    assert not (state / "GENESIS").exists()


def test_current_temp_without_genesis_blocks_before_anchor_creation(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    state = root / ".artifact_state"
    (state / "sets").mkdir(parents=True)
    residue = state / f".CURRENT.{NONCE_1}.tmp"
    residue.write_text("residue")

    with pytest.raises(MissionStateError) as error:
        _manager(root).ensure_genesis()
    assert error.value.code == "artifact_current_temp_without_genesis"
    assert not (state / "GENESIS").exists()
    assert residue.exists()


def test_selected_reader_requires_matching_mission_state(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    selected = _compose(_manager(root), packet)

    with pytest.raises(MissionStateError) as error:
        validate_selected_review_queue(selected.review_queue_path)
    assert error.value.code == "mission_state_read_failed"


def test_artifact_manifest_rejects_extra_manifest_listed_path(tmp_path: Path) -> None:
    root = tmp_path / "mission"
    root.mkdir()
    packet = _packet(root)
    selected = _compose(_manager(root), packet)
    extra = selected.set_dir / "coverage" / "extra.json"
    extra.write_bytes(canonical_json_bytes({"schema_version": "extra-v1"}))
    manifest_path = selected.set_dir / "artifact_set_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"].append({
        "relative_path": "coverage/extra.json",
        "schema_version": "extra-v1",
        "sha256": hashlib.sha256(extra.read_bytes()).hexdigest(),
        "size_bytes": extra.stat().st_size,
        "role": "coverage_artifact",
    })
    manifest["artifacts"] = sorted(manifest["artifacts"], key=lambda row: row["relative_path"])
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    pointer_path = root / ".artifact_state" / "CURRENT"
    pointer = json.loads(pointer_path.read_text())
    pointer["artifact_set_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    pointer_path.write_bytes(canonical_json_bytes(pointer))

    with pytest.raises(MissionStateError) as error:
        _manager(root, nonce=NONCE_2).load_current()
    assert error.value.code == "invalid_artifact_rows"
