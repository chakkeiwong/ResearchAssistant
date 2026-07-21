from __future__ import annotations

import json
import hashlib
import multiprocessing
import os
import socket
import time
import uuid
from pathlib import Path

import pytest

from research_assistant.cli import main
from research_assistant.survey.mission_state import (
    CURRENT_SCHEMA,
    LEGACY_MISSION_SCHEMA,
    LOCK_SCHEMA,
    MAX_METADATA_RECORDS,
    MissionLock,
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    discovery_budget,
    generation_identity,
    migrated_mission_id,
    mission_fingerprint,
    normalize_seeds,
    normalize_text,
    validate_budget,
)


TOPIC = "Neural Optimal Transport"
SEEDS = ["arxiv:2201.12220v3"]
MISSION_ID = "11111111-1111-4111-8111-111111111111"
NOW = "2026-07-11T00:00:00+00:00"
NONCE_1 = "000102030405060708090a0b0c0d0e0f"
NONCE_2 = "101112131415161718191a1b1c1d1e1f"


def _hold_lock_process(output: str, ready, release) -> None:
    lock = MissionLock(Path(output))
    lock.acquire()
    ready.set()
    release.wait(10)
    lock.release()


def _crash_with_lock_process(output: str, ready) -> None:
    lock = MissionLock(Path(output), stale_seconds=0)
    lock.acquire()
    ready.set()
    os._exit(0)


def _resume_manager_process(output: str, confirmed: bool, nonce: str, start, queue) -> None:
    start.wait(10)
    manager = _manager(Path(output), confirmed=confirmed, resume=True, nonce=nonce)
    try:
        snapshot = manager.begin()
        snapshot = manager.checkpoint_confirmation()
        mission, _ = _commit(manager)
        queue.put({
            "status": "committed",
            "confirmed": mission["mission_contract"]["public_discovery_confirmation"]["confirmed"],
            "generation": mission["mission_contract"]["generation"],
        })
    except MissionStateError as error:
        queue.put({"status": "blocked", "code": error.code})


def _held_confirm_resume_process(output: str, acquired, proceed, queue) -> None:
    manager = _manager(Path(output), confirmed=True, resume=True, nonce=NONCE_2)
    try:
        manager.begin()
        manager.checkpoint_confirmation()
        acquired.set()
        proceed.wait(10)
        mission, _ = _commit(manager)
        queue.put({
            "status": "committed",
            "confirmed": mission["mission_contract"]["public_discovery_confirmation"]["confirmed"],
        })
    except MissionStateError as error:
        queue.put({"status": "blocked", "code": error.code})


def _reclaim_lock_process(output: str, observed, proceed, acquired, release, queue) -> None:
    def hook(payload: dict) -> None:
        observed.set()
        proceed.wait(10)

    lock = MissionLock(Path(output), stale_seconds=0, reclaim_observed_hook=hook)
    try:
        lock.acquire()
        acquired.set()
        queue.put({"status": "acquired", "token": lock.owner_token})
        release.wait(10)
        lock.release()
    except MissionStateError as error:
        queue.put({"status": "blocked", "code": error.code})


def _manager(
    output: Path,
    *,
    topic: str = TOPIC,
    seeds: list[str] | None = None,
    confirmed: bool = False,
    resume: bool = False,
    force: bool = False,
    nonce: str = NONCE_1,
    crash_at: str | None = None,
) -> MissionStateManager:
    def crash_hook(label: str) -> None:
        if label == crash_at:
            raise RuntimeError(f"injected crash at {label}")

    return MissionStateManager(
        output_dir=output,
        topic=topic,
        seeds=seeds or list(SEEDS),
        confirm_public_discovery=confirmed,
        resume=resume,
        force=force,
        now=lambda: NOW,
        nonce_factory=lambda: nonce,
        mission_id_factory=lambda: MISSION_ID,
        crash_hook=crash_hook if crash_at else None,
    )


def _payloads() -> tuple[dict, dict]:
    return (
        {"schema_version": "placeholder", "status": "blocked_at_gate", "dynamic": {"value": 1}},
        {"schema_version": "ra-survey-public-source-next-action-v1", "status": "confirmation_required"},
    )


def _commit(manager: MissionStateManager) -> tuple[dict, dict]:
    mission, next_action = _payloads()
    snapshot = manager.commit(mission, next_action)
    assert snapshot.mission_control is not None
    assert snapshot.next_action is not None
    return snapshot.mission_control, snapshot.next_action


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _rewrite_selected_generation(output: Path, mutate) -> tuple[Path, dict]:
    state = output / ".mission_state"
    pointer_path = state / "CURRENT"
    pointer = _json(pointer_path)
    generation = state / "generations" / pointer["generation_id"]
    manifest_path = generation / "generation_manifest.json"
    manifest = _json(manifest_path)
    mutate(generation, manifest)
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    pointer["generation_manifest_sha256"] = manifest_digest
    pointer_path.write_bytes(canonical_json_bytes(pointer))
    transaction_path = state / "transactions" / f"{pointer['generation_id']}.json"
    transaction = _json(transaction_path)
    transaction["generation_manifest_sha256"] = manifest_digest
    transaction_path.write_bytes(canonical_json_bytes(transaction))
    return generation, manifest


def test_published_fingerprint_generation_and_migration_vectors(tmp_path: Path) -> None:
    output = Path("/tmp/m16 mission")
    topic = normalize_text(" Neural\tOptimal  Transport ", field="topic")
    seeds = normalize_seeds(SEEDS)
    budget = discovery_budget(output)

    assert mission_fingerprint(topic, seeds, budget) == (
        "a7a417b556bb6ade8f2b0cbf7a8602e13ac6c7de56cf0231a1d3c80bd836af00"
    )
    generation_id, digest = generation_identity(
        mission_id=MISSION_ID,
        fingerprint="a7a417b556bb6ade8f2b0cbf7a8602e13ac6c7de56cf0231a1d3c80bd836af00",
        generation=1,
        parent_generation_id=None,
        transaction_nonce=NONCE_1,
    )
    assert digest == "43b0fe5832e44f1c05eb8593a3e7e3880e233a4e1618ecaadcee7baa5021421e"
    assert generation_id == "g00000001-43b0fe5832e44f1c"
    assert migrated_mission_id(topic, seeds, budget) == "e040e33e-bed3-5425-982b-2c1672083bd6"


def test_normalization_and_budget_validation_are_strict(tmp_path: Path) -> None:
    assert normalize_text("Ａ  B\tC", field="topic") == {"display": "A B C", "key": "a b c"}
    assert normalize_seeds([" Seed B ", "seed a", "SEED A"]) == [
        {"display": "seed a", "key": "seed a"},
        {"display": "Seed B", "key": "seed b"},
    ]

    valid = discovery_budget(tmp_path)
    assert validate_budget(valid) == valid
    for invalid in [True, 0, -1, MAX_METADATA_RECORDS + 1]:
        row = dict(valid)
        row["max_metadata_records"] = invalid
        with pytest.raises(MissionStateError, match="max_metadata_records"):
            validate_budget(row)
    for providers in [["openalex", "arxiv"], ["arxiv", "arxiv"], ["Arxiv"]]:
        row = dict(valid)
        row["providers"] = providers
        with pytest.raises(MissionStateError):
            validate_budget(row)
    row = dict(valid)
    row["unknown"] = 1
    with pytest.raises(MissionStateError) as error:
        validate_budget(row)
    assert error.value.code == "invalid_schema"


def test_new_commit_and_equivalent_resume_preserve_identity(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    first = _manager(output, seeds=[" Seed B ", "seed a", "SEED A"])
    initial = first.begin()
    assert initial.contract["generation"] == 0
    mission, next_action = _commit(first)

    mission_id = mission["mission_contract"]["mission_id"]
    first_generation = mission["generation_id"]
    assert mission_id == MISSION_ID
    assert _json(output / ".mission_state" / "CURRENT")["schema_version"] == CURRENT_SCHEMA
    assert _json(output / "mission_control.json") == mission
    assert _json(output / "next_action.json") == next_action

    resumed = _manager(
        output,
        topic=" neural  optimal\ttransport ",
        seeds=["SEED A", "seed b"],
        resume=True,
        nonce=NONCE_2,
    )
    snapshot = resumed.begin()
    assert snapshot.contract["mission_id"] == mission_id
    assert snapshot.contract["lineage"]["generation_id"] == first_generation
    second_mission, _ = _commit(resumed)
    assert second_mission["mission_contract"]["generation"] == 2
    assert second_mission["mission_contract"]["mission_id"] == mission_id
    assert second_mission["generation_id"] != first_generation


def test_checkpoint_persists_generation_and_retains_lock_until_commit(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    mission, next_action = _payloads()
    checkpoint = manager.checkpoint(mission, next_action)

    assert checkpoint.current_pointer is not None
    assert manager.lock._held is True
    contender = MissionLock(output)
    with pytest.raises(MissionStateError) as error:
        contender.acquire()
    assert error.value.code == "mission_locked"

    final_mission = dict(checkpoint.mission_control or {})
    final_mission["dynamic"] = {"value": 2}
    committed = manager.commit(final_mission, dict(checkpoint.next_action or {}))
    assert committed.current_pointer is not None
    assert committed.current_pointer["generation_id"] != checkpoint.current_pointer["generation_id"]
    assert manager.lock._held is False


def test_confirmation_is_monotonic_across_resume(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    first = _manager(output, confirmed=True)
    first.begin()
    mission, _ = _commit(first)
    confirmation = mission["mission_contract"]["public_discovery_confirmation"]
    assert confirmation == {"confirmed": True, "confirmed_at": NOW, "confirmation_source": "cli"}

    resumed = _manager(output, confirmed=False, resume=True, nonce=NONCE_2)
    snapshot = resumed.begin()
    assert snapshot.contract["public_discovery_confirmation"] == confirmation
    second, _ = _commit(resumed)
    assert second["mission_contract"]["public_discovery_confirmation"] == confirmation


def test_changed_identity_force_and_resume_conflicts_block_without_mutation(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    _commit(manager)
    before = (output / ".mission_state" / "CURRENT").read_bytes()

    for candidate in [
        _manager(output, topic="Different", resume=True),
        _manager(output, seeds=["different"], resume=True),
        _manager(output, force=True),
        _manager(output, resume=True, force=True),
    ]:
        with pytest.raises(MissionStateError):
            candidate.begin()
        assert (output / ".mission_state" / "CURRENT").read_bytes() == before

    with pytest.raises(MissionStateError) as error:
        _manager(tmp_path / "missing", resume=True).begin()
    assert error.value.code == "resume_missing_mission"


def test_current_generation_tamper_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    mission, _ = _commit(manager)
    generation = output / ".mission_state" / "generations" / mission["generation_id"]
    path = generation / "next_action.json"
    path.write_text(path.read_text() + " ")

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "artifact_digest_mismatch"


def test_v1_migration_is_deterministic_and_does_not_invent_confirmation(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    output.mkdir()
    legacy = {
        "schema_version": LEGACY_MISSION_SCHEMA,
        "topic": TOPIC,
        "seeds": SEEDS,
        "public_discovery_confirmation": {"confirmed": False},
        "status": "blocked_at_gate",
        "next_action": {"schema_version": "legacy-next", "status": "blocked"},
    }
    (output / "mission_control.json").write_text(json.dumps(legacy))

    manager = _manager(output, resume=True)
    snapshot = manager.begin()
    assert snapshot.contract["mission_id"] == migrated_mission_id(
        normalize_text(TOPIC, field="topic"), normalize_seeds(SEEDS), discovery_budget(output)
    )
    assert snapshot.contract["public_discovery_confirmation"]["confirmed"] is False
    mission, _ = _commit(manager)
    assert mission["mission_contract"]["migration"]["authority_invented"] is False


def test_v1_non_boolean_confirmation_blocks_and_preserves_bytes(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    output.mkdir()
    path = output / "mission_control.json"
    path.write_text(json.dumps({
        "schema_version": LEGACY_MISSION_SCHEMA,
        "topic": TOPIC,
        "seeds": SEEDS,
        "public_discovery_confirmation": {"confirmed": "yes"},
    }))
    before = path.read_bytes()
    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True).begin()
    assert error.value.code == "ambiguous_legacy_confirmation"
    assert path.read_bytes() == before


def test_v1_cli_confirmation_is_checkpointed_before_provider_and_survives_flagless_resume(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    output = tmp_path / "legacy"
    output.mkdir()
    legacy = {
        "schema_version": LEGACY_MISSION_SCHEMA,
        "topic": TOPIC,
        "seeds": SEEDS,
        "public_discovery_confirmation": {"confirmed": False},
    }
    (output / "mission_control.json").write_bytes(canonical_json_bytes(legacy))

    def provider_crash(**kwargs):
        raise RuntimeError("provider crashed after migrated confirmation checkpoint")

    monkeypatch.setattr("research_assistant.survey.orchestrate.build_survey_evidence_packet", provider_crash)
    with pytest.raises(RuntimeError, match="migrated confirmation checkpoint"):
        _run_workflow(
            capsys,
            output,
            extra=["--resume", "--confirm-public-discovery"],
        )

    genesis = _json(output / ".mission_state" / "GENESIS")
    assert genesis["public_discovery_confirmation"]["confirmed"] is False
    current = _json(output / ".mission_state" / "CURRENT")
    confirmed_generation = current["generation_id"]
    selected = _manager(output, resume=True, nonce=NONCE_2)
    snapshot = selected.begin()
    assert snapshot.contract["public_discovery_confirmation"]["confirmed"] is True
    assert snapshot.current_pointer["generation_id"] == confirmed_generation
    selected.abort()


def test_crash_after_genesis_final_rename_retries_with_fresh_generation_id(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, confirmed=True, crash_at="generation:after_final_rename")
    crashing.begin()
    with pytest.raises(RuntimeError, match="after_final_rename"):
        _commit(crashing)
    assert not (output / ".mission_state" / "CURRENT").exists()
    orphan_dirs = [path for path in (output / ".mission_state" / "generations").iterdir() if not path.name.startswith(".staging-")]
    assert len(orphan_dirs) == 1
    orphan_id = orphan_dirs[0].name

    retry = _manager(output, resume=True, nonce=NONCE_2)
    snapshot = retry.begin()
    assert snapshot.recovery["state"] == "interrupted_genesis"
    assert snapshot.contract["public_discovery_confirmation"]["confirmed"] is True
    mission, _ = _commit(retry)
    assert mission["generation_id"] != orphan_id
    assert orphan_dirs[0].exists()
    assert _json(output / ".mission_state" / "CURRENT")["generation_id"] == mission["generation_id"]


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("remove_transaction", "unjournaled_generation_state"),
        ("foreign_fingerprint", "foreign_interrupted_transaction"),
        ("manifest_digest", "orphan_manifest_hash_mismatch"),
        ("unexpected_directory", "unjournaled_generation_state"),
    ],
)
def test_interrupted_genesis_corruption_blocks_without_current(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="generation:after_final_rename")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)
    transactions = output / ".mission_state" / "transactions"
    transaction_path = next(transactions.glob("*.json"))
    generation_dir = next(path for path in (output / ".mission_state" / "generations").iterdir() if not path.name.startswith(".staging-"))

    if mutation == "remove_transaction":
        transaction_path.unlink()
    elif mutation == "foreign_fingerprint":
        row = _json(transaction_path)
        row["mission_fingerprint"] = "0" * 64
        transaction_path.write_bytes(canonical_json_bytes(row))
    elif mutation == "manifest_digest":
        row = _json(transaction_path)
        row["generation_manifest_sha256"] = "0" * 64
        transaction_path.write_bytes(canonical_json_bytes(row))
    else:
        (generation_dir.parent / "foreign").mkdir()

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == expected_code
    assert not (output / ".mission_state" / "CURRENT").exists()


@pytest.mark.parametrize("mutation", ["missing_field", "unknown_field", "noncanonical"])
def test_interrupted_genesis_prepared_manifest_rejects_malformed_bytes(
    tmp_path: Path,
    mutation: str,
) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="generation:after_final_rename")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)
    state = output / ".mission_state"
    generation = next(path for path in (state / "generations").iterdir() if not path.name.startswith(".staging-"))
    manifest_path = generation / "generation_manifest.json"
    manifest = _json(manifest_path)
    if mutation == "missing_field":
        manifest.pop("mission_id")
        manifest_bytes = canonical_json_bytes(manifest)
        expected_code = "invalid_schema"
    elif mutation == "unknown_field":
        manifest["unknown"] = True
        manifest_bytes = canonical_json_bytes(manifest)
        expected_code = "invalid_schema"
    else:
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        expected_code = "noncanonical_generation_manifest"
    manifest_path.write_bytes(manifest_bytes)
    transaction_path = next((state / "transactions").glob("*.json"))
    transaction = _json(transaction_path)
    transaction["generation_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    transaction_path.write_bytes(canonical_json_bytes(transaction))

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == expected_code
    assert not (state / "CURRENT").exists()


def test_crash_after_current_replace_selects_complete_new_generation(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="current:after_replace")
    crashing.begin()
    with pytest.raises(RuntimeError, match="current:after_replace"):
        _commit(crashing)
    assert (output / ".mission_state" / "CURRENT").exists()

    resumed = _manager(output, resume=True, nonce=NONCE_2)
    snapshot = resumed.begin()
    assert snapshot.contract["generation"] == 1
    resumed.abort()


def test_live_lock_non_owner_and_stale_lock_behavior(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    first = MissionLock(output)
    first.acquire()
    second = MissionLock(output)
    with pytest.raises(MissionStateError) as error:
        second.acquire()
    assert error.value.code == "mission_locked"

    payload = _json(first.path)
    payload["owner_token"] = "f" * 32
    first.path.write_bytes(canonical_json_bytes(payload))
    with pytest.raises(MissionStateError) as error:
        first.release()
    assert error.value.code == "mission_lock_not_owner"
    payload["owner_token"] = first.owner_token
    first.path.write_bytes(canonical_json_bytes(payload))
    first.release()

    stale = {
        "schema_version": LOCK_SCHEMA,
        "owner_token": "a" * 32,
        "pid": 999_999_999,
        "hostname": socket.gethostname(),
        "acquired_at": NOW,
        "acquired_epoch": time.time() - 1000,
    }
    output.mkdir(exist_ok=True)
    (output / ".mission.lock").write_bytes(canonical_json_bytes(stale))
    reclaimed = MissionLock(output)
    reclaimed.acquire()
    assert _json(reclaimed.path)["owner_token"] == reclaimed.owner_token
    reclaimed.release()


def _run_workflow(capsys, output: Path, *, topic: str = TOPIC, seeds: list[str] | None = None, extra: list[str] | None = None) -> tuple[int, dict]:
    command = [
        "survey",
        "run-public-source-workflow",
        "--topic",
        topic,
    ]
    for seed in seeds or SEEDS:
        command.extend(["--seed", seed])
    command.extend(["--out", str(output)])
    command.extend(extra or [])
    rc = main(command)
    return rc, json.loads(capsys.readouterr().out)


def test_cli_confirmation_survives_flagless_resume_and_mirrors_are_consistent(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    output = tmp_path / "mission"

    def fake_build(**kwargs):
        metadata = Path(kwargs["output_dir"])
        metadata.mkdir(parents=True, exist_ok=True)
        (metadata / "candidate_ledger.json").write_text("{}")
        (metadata / "build_manifest.json").write_text("{}")
        return {"status": "metadata_collected", "provider_statuses": []}

    monkeypatch.setattr("research_assistant.survey.orchestrate.build_survey_evidence_packet", fake_build)
    rc, first = _run_workflow(capsys, output, extra=["--confirm-public-discovery"])
    assert rc == 0
    assert first["public_discovery_confirmation"]["confirmed"] is True
    mission_id = first["mission_id"]
    first_generation = first["generation_id"]

    rc, resumed = _run_workflow(
        capsys,
        output,
        topic=" neural  optimal\ttransport ",
        seeds=["ARXIV:2201.12220V3"],
        extra=["--resume"],
    )
    assert rc == 0
    assert resumed["mission_id"] == mission_id
    assert resumed["generation_id"] != first_generation
    assert resumed["public_discovery_confirmation"]["confirmed"] is True
    mission = _json(output / "mission_control.json")
    next_action = _json(output / "next_action.json")
    assert mission["next_action"] == next_action
    assert mission["mission_contract"]["public_discovery_confirmation"]["confirmed"] is True
    assert _json(output / ".mission_state" / "CURRENT")["generation_id"] == resumed["generation_id"]


def test_cli_changed_topic_or_seed_blocks_without_changing_current(tmp_path: Path, capsys) -> None:
    output = tmp_path / "mission"
    rc, _ = _run_workflow(capsys, output)
    assert rc == 0
    current = (output / ".mission_state" / "CURRENT").read_bytes()

    rc, changed_topic = _run_workflow(capsys, output, topic="Different", extra=["--resume"])
    assert rc == 1
    assert changed_topic["blocked_reason"] == "mission_identity_mismatch"
    assert (output / ".mission_state" / "CURRENT").read_bytes() == current

    rc, changed_seed = _run_workflow(capsys, output, seeds=["different"], extra=["--resume"])
    assert rc == 1
    assert changed_seed["blocked_reason"] == "mission_identity_mismatch"
    assert (output / ".mission_state" / "CURRENT").read_bytes() == current


def test_cli_existing_state_requires_resume_and_force_never_overwrites(tmp_path: Path, capsys) -> None:
    output = tmp_path / "mission"
    assert _run_workflow(capsys, output)[0] == 0
    current = (output / ".mission_state" / "CURRENT").read_bytes()

    rc, existing = _run_workflow(capsys, output)
    assert rc == 1
    assert existing["blocked_reason"] == "mission_control_exists"
    rc, forced = _run_workflow(capsys, output, extra=["--force"])
    assert rc == 1
    assert forced["blocked_reason"] == "force_existing_output"
    rc, conflict = _run_workflow(capsys, output, extra=["--force", "--resume"])
    assert rc == 1
    assert conflict["blocked_reason"] == "force_resume_conflict"
    assert (output / ".mission_state" / "CURRENT").read_bytes() == current


def test_cli_corrupt_current_is_bounded_and_does_not_run_workflow(tmp_path: Path, capsys) -> None:
    output = tmp_path / "mission"
    assert _run_workflow(capsys, output)[0] == 0
    current_path = output / ".mission_state" / "CURRENT"
    current_path.write_text("not-json")

    rc, payload = _run_workflow(capsys, output, extra=["--resume"])
    assert rc == 1
    assert payload["blocked_reason"] == "invalid_json"
    assert current_path.read_text() == "not-json"


def test_confirmation_checkpoint_survives_provider_crash_then_flagless_resume(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    output = tmp_path / "mission"
    rc, initial = _run_workflow(capsys, output)
    assert rc == 0
    assert initial["public_discovery_confirmation"]["confirmed"] is False

    def provider_crash(**kwargs):
        raise RuntimeError("provider crashed after confirmation checkpoint")

    monkeypatch.setattr("research_assistant.survey.orchestrate.build_survey_evidence_packet", provider_crash)
    with pytest.raises(RuntimeError, match="provider crashed"):
        _run_workflow(capsys, output, extra=["--resume", "--confirm-public-discovery"])

    current = _json(output / ".mission_state" / "CURRENT")
    confirmed_generation = current["generation_id"]
    assert _json(output / "mission_control.json")["mission_contract"]["public_discovery_confirmation"]["confirmed"] is True

    def provider_still_crashes(**kwargs):
        raise RuntimeError("flagless resume reached provider while confirmed")

    monkeypatch.setattr("research_assistant.survey.orchestrate.build_survey_evidence_packet", provider_still_crashes)
    with pytest.raises(RuntimeError, match="flagless resume reached provider"):
        _run_workflow(capsys, output, extra=["--resume"])
    assert _json(output / ".mission_state" / "CURRENT")["generation_id"] == confirmed_generation


def test_interrupted_unconfirmed_genesis_confirmation_is_checkpointed(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="generation:after_final_rename")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)

    resumed = _manager(output, confirmed=True, resume=True, nonce=NONCE_2)
    snapshot = resumed.begin()
    assert snapshot.current_pointer is None
    checkpoint = resumed.checkpoint_confirmation()
    assert checkpoint.current_pointer is not None
    assert checkpoint.contract["public_discovery_confirmation"]["confirmed"] is True
    resumed.abort()

    flagless = _manager(output, resume=True, nonce="202122232425262728292a2b2c2d2e2f")
    recovered = flagless.begin()
    assert recovered.contract["public_discovery_confirmation"]["confirmed"] is True
    flagless.abort()


def test_multiprocess_live_lock_contention_is_bounded(tmp_path: Path) -> None:
    ctx = multiprocessing.get_context("spawn")
    output = tmp_path / "mission"
    ready = ctx.Event()
    release = ctx.Event()
    process = ctx.Process(target=_hold_lock_process, args=(str(output), ready, release))
    process.start()
    assert ready.wait(10)

    contender = MissionLock(output)
    with pytest.raises(MissionStateError) as error:
        contender.acquire()
    assert error.value.code == "mission_locked"

    release.set()
    process.join(10)
    assert process.exitcode == 0


def test_multiprocess_confirm_default_race_preserves_confirmation(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    _commit(manager)

    ctx = multiprocessing.get_context("spawn")
    acquired = ctx.Event()
    proceed = ctx.Event()
    queue = ctx.Queue()
    winner = ctx.Process(target=_held_confirm_resume_process, args=(str(output), acquired, proceed, queue))
    winner.start()
    assert acquired.wait(10)

    start = ctx.Event()
    loser = ctx.Process(target=_resume_manager_process, args=(str(output), False, "303132333435363738393a3b3c3d3e3f", start, queue))
    loser.start()
    start.set()
    loser.join(10)
    assert loser.exitcode == 0
    blocked = queue.get(timeout=5)
    assert blocked == {"status": "blocked", "code": "mission_locked"}

    proceed.set()
    winner.join(10)
    assert winner.exitcode == 0
    committed = queue.get(timeout=5)
    assert committed == {"status": "committed", "confirmed": True}

    resumed = _manager(output, resume=True, nonce="404142434445464748494a4b4c4d4e4f")
    assert resumed.begin().contract["public_discovery_confirmation"]["confirmed"] is True
    resumed.abort()


def test_multiprocess_owner_crash_is_reclaimed(tmp_path: Path) -> None:
    ctx = multiprocessing.get_context("spawn")
    output = tmp_path / "mission"
    ready = ctx.Event()
    process = ctx.Process(target=_crash_with_lock_process, args=(str(output), ready))
    process.start()
    assert ready.wait(10)
    process.join(10)
    assert process.exitcode == 0

    reclaimed = MissionLock(output, stale_seconds=0)
    reclaimed.acquire()
    assert _json(reclaimed.path)["owner_token"] == reclaimed.owner_token
    reclaimed.release()


def test_two_stale_reclaimers_cannot_unlink_new_live_owner(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    output.mkdir()
    stale = {
        "schema_version": LOCK_SCHEMA,
        "owner_token": "a" * 32,
        "pid": 999_999_999,
        "hostname": socket.gethostname(),
        "acquired_at": NOW,
        "acquired_epoch": time.time() - 1000,
    }
    (output / ".mission.lock").write_bytes(canonical_json_bytes(stale))

    ctx = multiprocessing.get_context("spawn")
    observed_a, observed_b = ctx.Event(), ctx.Event()
    proceed_a, proceed_b = ctx.Event(), ctx.Event()
    acquired_a, acquired_b = ctx.Event(), ctx.Event()
    release_a, release_b = ctx.Event(), ctx.Event()
    queue = ctx.Queue()
    first = ctx.Process(
        target=_reclaim_lock_process,
        args=(str(output), observed_a, proceed_a, acquired_a, release_a, queue),
    )
    second = ctx.Process(
        target=_reclaim_lock_process,
        args=(str(output), observed_b, proceed_b, acquired_b, release_b, queue),
    )
    first.start()
    second.start()
    assert observed_a.wait(10) and observed_b.wait(10)

    proceed_a.set()
    assert acquired_a.wait(10)
    live_token = _json(output / ".mission.lock")["owner_token"]
    proceed_b.set()
    second.join(10)
    assert second.exitcode == 0
    assert _json(output / ".mission.lock")["owner_token"] == live_token

    release_a.set()
    release_b.set()
    first.join(10)
    assert first.exitcode == 0
    results = [queue.get(timeout=5), queue.get(timeout=5)]
    assert {row["status"] for row in results} == {"acquired", "blocked"}
    assert next(row for row in results if row["status"] == "blocked")["code"] == "mission_locked"


CRASH_LABELS = [
    "transaction_intent:after_temp_write",
    "transaction_intent:after_temp_fsync",
    "transaction_intent:after_replace",
    "transaction_intent:after_directory_fsync",
    "generation:after_staging_mkdir",
    "generation:after_staging_parent_fsync",
    "generation:mission_control:after_write",
    "generation:mission_control:after_fsync",
    "generation:next_action:after_write",
    "generation:next_action:after_fsync",
    "generation:generation_manifest:after_write",
    "generation:generation_manifest:after_fsync",
    "generation:after_staging_fsync",
    "transaction_prepared:after_temp_write",
    "transaction_prepared:after_temp_fsync",
    "transaction_prepared:after_replace",
    "transaction_prepared:after_directory_fsync",
    "generation:after_final_rename",
    "generation:after_generations_fsync",
    "current:after_temp_write",
    "current:after_temp_fsync",
    "current:after_replace",
    "current:after_directory_fsync",
    "transaction_committed:after_temp_write",
    "transaction_committed:after_temp_fsync",
    "transaction_committed:after_replace",
    "transaction_committed:after_directory_fsync",
    "mission_mirror:after_temp_write",
    "mission_mirror:after_temp_fsync",
    "mission_mirror:after_replace",
    "mission_mirror:after_directory_fsync",
    "next_action_mirror:after_temp_write",
    "next_action_mirror:after_temp_fsync",
    "next_action_mirror:after_replace",
    "next_action_mirror:after_directory_fsync",
]


@pytest.mark.parametrize("crash_at", CRASH_LABELS)
def test_generation_two_crash_matrix_selects_valid_authority(tmp_path: Path, crash_at: str) -> None:
    output = tmp_path / "mission"
    first = _manager(output, confirmed=True)
    first.begin()
    initial, _ = _commit(first)
    prior_id = initial["generation_id"]

    crashing = _manager(output, resume=True, nonce=NONCE_2, crash_at=crash_at)
    crashing.begin()
    with pytest.raises(RuntimeError, match="injected crash"):
        _commit(crashing)

    resumed = _manager(output, resume=True, nonce="505152535455565758595a5b5c5d5e5f")
    snapshot = resumed.begin()
    current_id = snapshot.current_pointer["generation_id"]
    if crash_at.startswith(("current:after_replace", "current:after_directory_fsync")) or crash_at.startswith(
        ("transaction_committed:", "mission_mirror:", "next_action_mirror:")
    ):
        assert current_id != prior_id
        assert snapshot.contract["generation"] == 2
        assert snapshot.contract["public_discovery_confirmation"]["confirmed"] is True
    else:
        assert current_id == prior_id
        assert snapshot.contract["generation"] == 1
        assert snapshot.contract["public_discovery_confirmation"]["confirmed"] is True
        if crash_at in {"transaction_intent:after_temp_write", "transaction_intent:after_temp_fsync"}:
            assert snapshot.recovery["orphans"] == []
            assert snapshot.recovery["orphan_temp_files"]
        else:
            assert snapshot.recovery["orphans"]
    resumed.abort()


@pytest.mark.parametrize(
    "crash_at",
    [
        "genesis:after_temp_write",
        "genesis:after_temp_fsync",
        "genesis:after_replace",
        "genesis:after_directory_fsync",
    ],
)
def test_genesis_atomic_write_crash_recovers_without_inventing_authority(tmp_path: Path, crash_at: str) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, confirmed=True, crash_at=crash_at)
    with pytest.raises(RuntimeError, match="injected crash"):
        crashing.begin()

    retry = _manager(output, confirmed=False, resume=(output / ".mission_state" / "GENESIS").exists(), nonce=NONCE_2)
    snapshot = retry.begin()
    expected_confirmed = crash_at in {"genesis:after_replace", "genesis:after_directory_fsync"}
    assert snapshot.contract["public_discovery_confirmation"]["confirmed"] is expected_confirmed
    if crash_at in {"genesis:after_temp_write", "genesis:after_temp_fsync"}:
        assert snapshot.recovery["orphan_temp_files"]
    else:
        assert snapshot.recovery["orphan_temp_files"] == []
    retry.abort()


def test_prepared_current_journal_is_reconciled(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="current:after_directory_fsync")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)

    current_id = _json(output / ".mission_state" / "CURRENT")["generation_id"]
    transaction = output / ".mission_state" / "transactions" / f"{current_id}.json"
    assert _json(transaction)["status"] == "prepared"
    resumed = _manager(output, resume=True, nonce=NONCE_2)
    resumed.begin()
    assert _json(transaction)["status"] == "committed"
    resumed.abort()


def test_corrupt_orphan_blocks_before_prepared_current_reconciliation(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="current:after_directory_fsync")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)

    current_id = _json(output / ".mission_state" / "CURRENT")["generation_id"]
    transaction = output / ".mission_state" / "transactions" / f"{current_id}.json"
    before = transaction.read_bytes()
    assert _json(transaction)["status"] == "prepared"
    (output / ".mission_state" / "generations" / "unlogged-corrupt-state").mkdir()

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "unjournaled_generation_state"
    assert transaction.read_bytes() == before


def test_digest_valid_embedded_next_action_disagreement_blocks(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    mission, _ = _commit(manager)
    generation_id = mission["generation_id"]
    state = output / ".mission_state"
    generation = state / "generations" / generation_id
    next_action_path = generation / "next_action.json"
    altered = _json(next_action_path)
    altered["status"] = "digest_valid_but_disagrees_with_embedded_copy"
    altered_bytes = (json.dumps(altered, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()
    next_action_path.write_bytes(altered_bytes)

    manifest_path = generation / "generation_manifest.json"
    manifest = _json(manifest_path)
    row = next(row for row in manifest["artifacts"] if row["relative_path"] == "next_action.json")
    row["sha256"] = __import__("hashlib").sha256(altered_bytes).hexdigest()
    row["size_bytes"] = len(altered_bytes)
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    manifest_digest = __import__("hashlib").sha256(manifest_bytes).hexdigest()

    pointer_path = state / "CURRENT"
    pointer = _json(pointer_path)
    pointer["generation_manifest_sha256"] = manifest_digest
    pointer_path.write_bytes(canonical_json_bytes(pointer))
    transaction_path = state / "transactions" / f"{generation_id}.json"
    transaction = _json(transaction_path)
    transaction["generation_manifest_sha256"] = manifest_digest
    transaction_path.write_bytes(canonical_json_bytes(transaction))

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "next_action_mirror_mismatch"


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("foreign_transaction", "foreign_transaction"),
        ("unlogged_directory", "unjournaled_generation_state"),
        ("invalid_parent", "invalid_transaction_identity"),
        ("unexpected_staging_file", "unexpected_partial_staging_file"),
        ("intent_digest", "transaction_intent_mismatch"),
    ],
)
def test_corrupt_or_foreign_generation_two_orphan_blocks(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    output = tmp_path / "mission"
    first = _manager(output)
    first.begin()
    _commit(first)
    crash_at = "generation:after_final_rename" if mutation == "intent_digest" else "generation:after_staging_parent_fsync"
    crashing = _manager(output, resume=True, nonce=NONCE_2, crash_at=crash_at)
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)

    transaction_path = next(
        path for path in (output / ".mission_state" / "transactions").glob("*.json") if _json(path)["generation"] == 2
    )
    row = _json(transaction_path)
    staging = output / ".mission_state" / "generations" / f".staging-{row['generation_id']}"
    if mutation == "foreign_transaction":
        row["mission_fingerprint"] = "0" * 64
        transaction_path.write_bytes(canonical_json_bytes(row))
    elif mutation == "unlogged_directory":
        (output / ".mission_state" / "generations" / "foreign").mkdir()
    elif mutation == "invalid_parent":
        row["parent_generation_id"] = None
        transaction_path.write_bytes(canonical_json_bytes(row))
    elif mutation == "unexpected_staging_file":
        (staging / "unexpected").write_text("x")
    else:
        row["intent_sha256"] = "0" * 64
        transaction_path.write_bytes(canonical_json_bytes(row))

    before = (output / ".mission_state" / "CURRENT").read_bytes()
    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce="707172737475767778797a7b7c7d7e7f").begin()
    assert error.value.code == expected_code
    assert (output / ".mission_state" / "CURRENT").read_bytes() == before


def test_generation_collision_preserves_existing_transaction_bytes(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="generation:after_final_rename")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)
    transaction_path = next((output / ".mission_state" / "transactions").glob("*.json"))
    before = transaction_path.read_bytes()

    retry = _manager(output, resume=True, nonce=NONCE_1)
    retry.begin()
    with pytest.raises(MissionStateError) as error:
        _commit(retry)
    assert error.value.code == "generation_collision"
    assert transaction_path.read_bytes() == before


def test_unsafe_state_paths_and_unknown_empty_generation_directory_block(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    outside = tmp_path / "outside"
    outside.mkdir()
    output.mkdir()
    (output / ".mission_state").symlink_to(outside, target_is_directory=True)
    with pytest.raises(MissionStateError) as error:
        _manager(output).begin()
    assert error.value.code == "unsafe_mission_state_container"

    valid = tmp_path / "valid"
    manager = _manager(valid)
    manager.begin()
    _commit(manager)
    (valid / ".mission_state" / "generations" / "unknown-empty").mkdir()
    with pytest.raises(MissionStateError) as error:
        _manager(valid, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "unjournaled_generation_state"


def test_nested_artifact_symlink_parent_blocks_before_external_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    _commit(manager)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / "escaped.json"
    outside_bytes = b'{}\n'
    outside_file.write_bytes(outside_bytes)

    def mutate(generation: Path, manifest: dict) -> None:
        (generation / "nested").symlink_to(outside, target_is_directory=True)
        manifest["artifacts"].append({
            "relative_path": "nested/escaped.json",
            "schema_version": "test-v1",
            "sha256": hashlib.sha256(outside_bytes).hexdigest(),
            "size_bytes": len(outside_bytes),
            "role": "adversarial_external_artifact",
        })
        manifest["artifacts"].sort(key=lambda row: row["relative_path"])

    _rewrite_selected_generation(output, mutate)
    original_sha256_file = __import__("research_assistant.survey.mission_state", fromlist=["sha256_file"]).sha256_file

    def guarded_sha256_file(path: Path) -> str:
        if path.resolve() == outside_file.resolve():
            raise AssertionError("external artifact bytes must not be read")
        return original_sha256_file(path)

    monkeypatch.setattr("research_assistant.survey.mission_state.sha256_file", guarded_sha256_file)
    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "invalid_artifact_file"


@pytest.mark.parametrize(
    "artifact_rows,expected_code",
    [
        ([{"relative_path": "x", "schema_version": "v1", "sha256": "0" * 64, "size_bytes": 0}], "invalid_schema"),
        ([{"relative_path": "../x", "schema_version": "v1", "sha256": "0" * 64, "size_bytes": 0, "role": "x"}], "invalid_artifact_path"),
        ([
            {"relative_path": "b", "schema_version": "v1", "sha256": "0" * 64, "size_bytes": 0, "role": "x"},
            {"relative_path": "a", "schema_version": "v1", "sha256": "0" * 64, "size_bytes": 0, "role": "x"},
        ], "invalid_artifact_rows"),
    ],
)
def test_contract_lineage_artifact_rows_are_structurally_validated(
    tmp_path: Path,
    artifact_rows: list[dict],
    expected_code: str,
) -> None:
    output = tmp_path / "mission"
    manager = _manager(output)
    manager.begin()
    mission, _ = _commit(manager)

    def mutate(generation: Path, manifest: dict) -> None:
        mission_path = generation / "mission_control.json"
        payload = _json(mission_path)
        payload["mission_contract"]["lineage"]["artifacts"] = artifact_rows
        mission_bytes = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()
        mission_path.write_bytes(mission_bytes)
        row = next(row for row in manifest["artifacts"] if row["relative_path"] == "mission_control.json")
        row["sha256"] = hashlib.sha256(mission_bytes).hexdigest()
        row["size_bytes"] = len(mission_bytes)

    _rewrite_selected_generation(output, mutate)
    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == expected_code


def test_confirmed_timestamp_must_be_utc_rfc3339(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output, confirmed=True)
    manager.begin()
    manager.abort()
    genesis_path = output / ".mission_state" / "GENESIS"
    genesis = _json(genesis_path)
    genesis["public_discovery_confirmation"]["confirmed_at"] = "not-a-timestamp"
    genesis_path.write_bytes(canonical_json_bytes(genesis))

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "invalid_timestamp"


def test_v1_scope_claims_and_migrated_uuid_tamper_block(tmp_path: Path) -> None:
    output = tmp_path / "legacy"
    output.mkdir()
    legacy = {
        "schema_version": LEGACY_MISSION_SCHEMA,
        "topic": TOPIC,
        "seeds": SEEDS,
        "public_discovery_confirmation": {"confirmed": True},
        "providers": ["arxiv"],
    }
    path = output / "mission_control.json"
    path.write_bytes(canonical_json_bytes(legacy))
    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True).begin()
    assert error.value.code == "ambiguous_legacy_scope"

    migrated = tmp_path / "migrated"
    migrated.mkdir()
    legacy.pop("providers")
    (migrated / "mission_control.json").write_bytes(canonical_json_bytes(legacy))
    manager = _manager(migrated, resume=True)
    manager.begin()
    manager.abort()
    genesis_path = migrated / ".mission_state" / "GENESIS"
    genesis = _json(genesis_path)
    genesis["mission_id"] = MISSION_ID
    genesis_path.write_bytes(canonical_json_bytes(genesis))
    with pytest.raises(MissionStateError) as error:
        _manager(migrated, resume=True, nonce=NONCE_2).begin()
    assert error.value.code == "migrated_mission_id_mismatch"


@pytest.mark.parametrize(
    "extra_confirmation",
    [
        {"scope": {"providers": ["arxiv"]}},
        {"providers": ["arxiv"]},
        {"allowed_domains": ["arxiv.org"]},
        {"caps": {"max_metadata_records": 1}},
    ],
)
def test_v1_nested_confirmation_scope_blocks_without_inventing_authority(
    tmp_path: Path,
    extra_confirmation: dict,
) -> None:
    output = tmp_path / "legacy"
    output.mkdir()
    confirmation = {"confirmed": True, **extra_confirmation}
    legacy = {
        "schema_version": LEGACY_MISSION_SCHEMA,
        "topic": TOPIC,
        "seeds": SEEDS,
        "public_discovery_confirmation": confirmation,
    }
    path = output / "mission_control.json"
    path.write_bytes(canonical_json_bytes(legacy))
    before = path.read_bytes()

    with pytest.raises(MissionStateError) as error:
        _manager(output, resume=True).begin()

    assert error.value.code == "ambiguous_legacy_scope"
    assert path.read_bytes() == before
    assert not (output / ".mission_state" / "GENESIS").exists()
    assert not (output / ".mission_state" / "CURRENT").exists()


def test_confirmed_provider_write_outside_mission_root_blocks_before_call_or_commit(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    output = tmp_path / "mission"
    external = tmp_path / "external-metadata"
    provider_called = False

    def forbidden_provider(**kwargs):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("provider must not run outside the mission write root")

    monkeypatch.setattr("research_assistant.survey.orchestrate.build_survey_evidence_packet", forbidden_provider)
    rc, payload = _run_workflow(
        capsys,
        output,
        extra=["--confirm-public-discovery", "--metadata-dir", str(external)],
    )

    assert rc == 1
    assert payload["blocked_reason"] == "public_metadata_write_outside_mission_root"
    assert provider_called is False
    assert not external.exists()
    assert not (output / ".mission_state" / "CURRENT").exists()
    genesis = _json(output / ".mission_state" / "GENESIS")
    assert genesis["public_discovery_confirmation"]["confirmed"] is True


@pytest.mark.parametrize("field,value", [("generation", True), ("parent_generation_id", []), ("transaction_nonce", 7)])
def test_malformed_transaction_fields_return_bounded_errors(tmp_path: Path, field: str, value) -> None:
    output = tmp_path / "mission"
    crashing = _manager(output, crash_at="generation:after_staging_parent_fsync")
    crashing.begin()
    with pytest.raises(RuntimeError):
        _commit(crashing)
    transaction_path = next((output / ".mission_state" / "transactions").glob("*.json"))
    transaction = _json(transaction_path)
    transaction[field] = value
    transaction_path.write_bytes(canonical_json_bytes(transaction))
    with pytest.raises(MissionStateError):
        _manager(output, resume=True, nonce=NONCE_2).begin()
