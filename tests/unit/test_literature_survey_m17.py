from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from research_assistant.cli import main
from research_assistant.survey import build as survey_build
from research_assistant.survey import orchestrate
from research_assistant.survey.build import build_bootstrap_effective_seed_skeleton
from research_assistant.survey.bootstrap import (
    MissionBootstrapStore,
    validate_bootstrap_outcome,
)
from research_assistant.survey.mission_state import (
    EXPLICIT_SEED_INPUT_MODE,
    GENESIS_SCHEMA,
    MISSION_CONTRACT_SCHEMA,
    MISSION_CONTROL_SCHEMA,
    TOPIC_GENESIS_SCHEMA,
    TOPIC_INPUT_MODE,
    TOPIC_MISSION_CONTRACT_SCHEMA,
    TOPIC_MISSION_CONTROL_SCHEMA,
    MissionStateError,
    MissionStateManager,
    canonical_json_bytes,
    discovery_budget,
    mission_fingerprint,
    mission_input_view,
    normalize_seeds,
    normalize_text,
    topic_mission_fingerprint,
)


TOPIC = "Neural Optimal Transport"
SEED = "arxiv:2201.12220v3"
MISSION_ID = "11111111-1111-4111-8111-111111111111"
NOW = "2026-07-13T00:00:00+00:00"
NONCE = "000102030405060708090a0b0c0d0e0f"


def _manager(
    output: Path,
    *,
    topic_mode: bool,
    confirmed: bool = False,
    resume: bool = False,
    crash_at: str | None = None,
) -> MissionStateManager:
    def crash_hook(label: str) -> None:
        if label == crash_at:
            raise RuntimeError(f"injected crash at {label}")

    return MissionStateManager(
        output_dir=output,
        topic=TOPIC,
        seeds=[] if topic_mode else [SEED],
        input_mode=TOPIC_INPUT_MODE if topic_mode else EXPLICIT_SEED_INPUT_MODE,
        confirm_public_discovery=confirmed,
        resume=resume,
        force=False,
        now=lambda: NOW,
        nonce_factory=lambda: NONCE,
        mission_id_factory=lambda: MISSION_ID,
        crash_hook=crash_hook if crash_at else None,
    )


def _topic_payload(state: str = "confirmation_required", outcome: str | None = None) -> tuple[dict, dict]:
    confirmation = {
        "schema_version": "ra-survey-public-discovery-confirmation-v1",
        "confirmed": False,
        "status": "confirmation_required",
        "confirmed_at": None,
        "confirmation_source": None,
        "question": "Do you want RA to search public web/archive sources for this idea or paper?",
        "scope": {},
        "forbidden_actions": [],
        "what_is_not_concluded": [],
    }
    next_action = {
        "schema_version": "ra-survey-public-source-next-action-v1",
        "status": "bootstrap_pending",
        "mission_status": "ready_for_local_continuation",
        "action_id": "topic_bootstrap",
    }
    mission = {
        "status": "ready_for_local_continuation",
        "created_at": NOW,
        "updated_at": NOW,
        "topic": TOPIC,
        "seeds": [],
        "input_mode": TOPIC_INPUT_MODE,
        "initial_seeds": [],
        "effective_seeds": [],
        "bootstrap_attempt_state": state,
        "bootstrap_outcome": outcome,
        "bootstrap_authority": None,
        "output_dir": "unused",
        "resume": False,
        "phase_statuses": {},
        "reviewed_artifacts": {},
        "coverage_artifacts": {},
        "final_artifacts": {},
        "source_intake_metadata_authority": None,
        "public_discovery_confirmation": confirmation,
        "actions": [],
        "next_gate": {},
        "next_action_path": "next_action.json",
        "next_action": next_action,
        "workflow_state": None,
        "artifact_state": None,
        "review_queue_path": None,
        "review_queue_counts": None,
        "review_queue_reused": None,
        "safe_next_commands": [],
        "forbidden_actions": [],
        "what_is_not_concluded": [],
        "local_supervisor": None,
    }
    return mission, next_action


def _confirmed_topic_snapshot(output: Path):
    manager = _manager(output, topic_mode=True, confirmed=False)
    manager.begin()
    mission, next_action = _topic_payload()
    manager.commit(mission, next_action)
    resumed = _manager(output, topic_mode=True, confirmed=True, resume=True)
    snapshot = resumed.begin()
    return resumed, resumed.checkpoint_confirmation()


def _selected_outcome() -> dict:
    return {
        "schema_version": "ra-survey-topic-bootstrap-outcome-v1",
        "outcome": "selected",
        "selected_candidates": [
            {
                "paper_key": "arxiv:2201.12220v3",
                "display": "arxiv:2201.12220v3",
                "identifier_evidence": ["arxiv:2201.12220v3"],
                "title_evidence": ["Neural Optimal Transport"],
                "descriptive": {},
            }
        ],
        "candidates": [],
        "ambiguities": [],
        "reason": None,
        "cap": None,
        "observed_count": 1,
        "descriptive": {"fixture": True},
    }


@dataclass
class FixtureCapability:
    outcome: dict
    name: str = "deterministic_fixture"
    version: str = "1"
    calls: int = 0

    def run(self, request: dict) -> dict:
        self.calls += 1
        assert request["input_mode"] == TOPIC_INPUT_MODE
        return self.outcome


def test_topic_input_is_explicit_and_v2_fingerprint_vector_is_unchanged(tmp_path: Path) -> None:
    topic = normalize_text(TOPIC, field="topic")
    seeds = normalize_seeds([SEED])
    budget = discovery_budget(Path("/tmp/m16 mission"))
    assert mission_fingerprint(topic, seeds, budget) == (
        "3e0454920753d0da938c14014a24bbd7cb616d8285e2cafcc6a2d7bd729f2433"
    )
    assert topic_mission_fingerprint(topic, discovery_budget(tmp_path / "topic")) != mission_fingerprint(
        topic,
        seeds,
        discovery_budget(tmp_path / "topic"),
    )
    with pytest.raises(MissionStateError, match="at least one nonempty seed"):
        MissionStateManager(
            output_dir=tmp_path / "implicit-empty",
            topic=TOPIC,
            seeds=[],
            confirm_public_discovery=False,
            resume=False,
            force=False,
        )
    with pytest.raises(MissionStateError, match="exact empty"):
        MissionStateManager(
            output_dir=tmp_path / "topic-with-seed",
            topic=TOPIC,
            seeds=[SEED],
            input_mode=TOPIC_INPUT_MODE,
            confirm_public_discovery=False,
            resume=False,
            force=False,
        )


def test_topic_genesis_contract_and_manifest_use_exact_sibling_schemas(tmp_path: Path) -> None:
    output = tmp_path / "mission"
    manager = _manager(output, topic_mode=True)
    initial = manager.begin()
    genesis = json.loads((output / ".mission_state" / "GENESIS").read_text())
    assert genesis["schema_version"] == TOPIC_GENESIS_SCHEMA
    assert set(genesis) == {
        "schema_version", "mission_id", "mission_fingerprint", "input_mode",
        "normalized_topic", "normalized_initial_seeds", "discovery_budget",
        "public_discovery_confirmation", "created_at", "migration",
    }
    assert mission_input_view(initial.contract) == {
        "input_mode": TOPIC_INPUT_MODE,
        "normalized_topic": normalize_text(TOPIC, field="topic"),
        "normalized_initial_seed_rows": [],
    }
    mission, next_action = _topic_payload()
    committed = manager.commit(mission, next_action)
    assert committed.contract["schema_version"] == TOPIC_MISSION_CONTRACT_SCHEMA
    assert committed.mission_control["schema_version"] == TOPIC_MISSION_CONTROL_SCHEMA
    pointer = json.loads((output / ".mission_state" / "CURRENT").read_text())
    manifest = json.loads(
        (output / ".mission_state" / "generations" / pointer["generation_id"] / "generation_manifest.json").read_text()
    )
    mission_row = next(row for row in manifest["artifacts"] if row["relative_path"] == "mission_control.json")
    assert mission_row["schema_version"] == TOPIC_MISSION_CONTROL_SCHEMA

    resumed = _manager(output, topic_mode=True, resume=True)
    replay = resumed.begin()
    assert replay.contract == committed.contract
    resumed.abort()


def test_cross_family_resume_is_rejected_before_repair(tmp_path: Path) -> None:
    output = tmp_path / "explicit"
    manager = _manager(output, topic_mode=False)
    initial = manager.begin()
    assert initial.contract["schema_version"] == MISSION_CONTRACT_SCHEMA
    mission, next_action = {"status": "blocked", "next_action": {}}, {"schema_version": "ra-survey-public-source-next-action-v1"}
    committed = manager.commit(mission, next_action)
    assert committed.mission_control["schema_version"] == MISSION_CONTROL_SCHEMA
    assert json.loads((output / ".mission_state" / "GENESIS").read_text())["schema_version"] == GENESIS_SCHEMA
    with pytest.raises(MissionStateError) as error:
        _manager(output, topic_mode=True, resume=True).begin()
    assert error.value.code == "mission_identity_mismatch"


@pytest.mark.parametrize(
    ("outcome", "updates"),
    [
        ("empty", {"observed_count": 0}),
        ("unavailable", {"reason": "production_capability_unavailable", "observed_count": 0}),
        ("capped", {"reason": "candidate_cap_reached", "cap": 1, "observed_count": 2}),
        ("ambiguous", {
            "candidates": [
                {
                    "paper_key": "a",
                    "display": "a",
                    "identifier_evidence": ["a"],
                    "title_evidence": [],
                    "descriptive": {},
                },
                {
                    "paper_key": "b",
                    "display": "b",
                    "identifier_evidence": ["b"],
                    "title_evidence": [],
                    "descriptive": {},
                },
            ],
            "ambiguities": [{"kind": "incompatible_selection", "paper_keys": ["a", "b"]}],
            "observed_count": 2,
        }),
    ],
)
def test_closed_nonselected_outcomes_remain_non_authoritative(outcome: str, updates: dict) -> None:
    payload = {
        "schema_version": "ra-survey-topic-bootstrap-outcome-v1",
        "outcome": outcome,
        "selected_candidates": [],
        "candidates": [],
        "ambiguities": [],
        "reason": None,
        "cap": None,
        "observed_count": 0,
        "descriptive": {},
        **updates,
    }
    assert validate_bootstrap_outcome(payload)["outcome"] == outcome
    payload["selected_candidates"] = _selected_outcome()["selected_candidates"]
    with pytest.raises(MissionStateError):
        validate_bootstrap_outcome(payload)


def test_selected_attempt_is_hash_bound_and_replayed_without_second_call(tmp_path: Path) -> None:
    manager, snapshot = _confirmed_topic_snapshot(tmp_path / "selected")
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(manager=manager, snapshot=snapshot, now=lambda: NOW)
    selected = store.advance(capability)
    assert capability.calls == 1
    assert selected["attempt_state"] == "selected_complete"
    assert selected["outcome"] == "selected"
    assert selected["effective_seeds"] == [SEED]
    assert selected["authority"]["effective_normalized_seed_keys"] == [SEED]
    assert selected["authority"]["manifest_sha256"] == hashlib.sha256(
        (Path(selected["set_dir"]) / "manifest.json").read_bytes()
    ).hexdigest()
    manager.abort()

    resumed_manager = _manager(tmp_path / "selected", topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    replayed = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    ).advance(capability)
    assert replayed == selected
    assert capability.calls == 1
    resumed_manager.abort()


def test_call_started_crash_is_indeterminate_and_never_retried(tmp_path: Path) -> None:
    output = tmp_path / "indeterminate"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap_call_started:after_directory_fsync",
    )
    with pytest.raises(RuntimeError, match="bootstrap_call_started"):
        store.advance(capability)
    assert capability.calls == 0
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    with pytest.raises(MissionStateError) as error:
        MissionBootstrapStore.from_snapshot(
            manager=resumed_manager,
            snapshot=resumed_snapshot,
            now=lambda: NOW,
        ).advance(capability)
    assert error.value.code == "bootstrap_call_indeterminate"
    assert capability.calls == 0
    resumed_manager.abort()


def test_prepared_before_pointer_exposes_no_authority_then_selects_without_call(tmp_path: Path) -> None:
    output = tmp_path / "prepared"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap:after_prepared",
    )
    with pytest.raises(RuntimeError, match="after_prepared"):
        store.advance(capability)
    prepared = store.observe()
    assert prepared["attempt_state"] == "prepared"
    assert prepared["outcome"] == "selected"
    assert prepared["authority"] is None
    assert prepared["effective_seeds"] == []
    assert capability.calls == 1
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    selected = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    ).advance(capability)
    assert selected["attempt_state"] == "selected_complete"
    assert selected["effective_seeds"] == [SEED]
    assert capability.calls == 1
    resumed_manager.abort()


def test_selected_outcome_rejects_unsorted_or_duplicate_effective_keys() -> None:
    payload = _selected_outcome()
    duplicate = dict(payload["selected_candidates"][0])
    payload["selected_candidates"] = [duplicate, duplicate]
    with pytest.raises(MissionStateError):
        validate_bootstrap_outcome(payload)


def test_topic_contract_canonical_bytes_exclude_selected_candidates_from_identity(tmp_path: Path) -> None:
    topic = normalize_text(" Neural\tOptimal  Transport ", field="topic")
    budget = discovery_budget(Path("/tmp/m17 topic mission"))
    fingerprint = topic_mission_fingerprint(topic, budget)
    payload = {
        "schema_version": "ra-survey-public-source-mission-fingerprint-v3",
        "input_mode": TOPIC_INPUT_MODE,
        "normalized_topic_key": topic["key"],
        "normalized_initial_seed_keys": [],
        "discovery_budget": budget,
    }
    expected_bytes = (
        b'{"discovery_budget":{"allowed_domains":["api.openalex.org","arxiv.org","export.arxiv.org"],'
        b'"max_bytes_per_source":52428800,"max_metadata_records":25,"max_source_records":5,'
        b'"providers":["arxiv","openalex"],"write_root":"/tmp/m17 topic mission"},'
        b'"input_mode":"idea_or_topic_without_initial_paper_seed","normalized_initial_seed_keys":[],'
        b'"normalized_topic_key":"neural optimal transport",'
        b'"schema_version":"ra-survey-public-source-mission-fingerprint-v3"}'
    )
    assert canonical_json_bytes(payload) == expected_bytes
    assert fingerprint == "8bfe3a7ec028e187e729a26efc5f1712e501707cface201d331271bc7e4fafc1"
    assert hashlib.sha256(expected_bytes).hexdigest() == fingerprint
    assert b"selected" not in expected_bytes


def test_cli_omitted_seed_unconfirmed_then_unavailable_without_provider_call(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "cli-topic"
    provider_calls = 0

    def forbidden_provider(**kwargs):
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("topic-only M17 must not enter public metadata collection")

    monkeypatch.setattr(survey_build, "_collect_public_metadata", forbidden_provider)
    first_code = main([
        "survey", "run-public-source-workflow", "--topic", TOPIC, "--out", str(output),
    ])
    first = json.loads(capsys.readouterr().out)
    assert first_code == 0
    assert first["schema_version"] == "ra-survey-public-source-orchestration-result-v3"
    assert first["bootstrap_attempt_state"] == "confirmation_required"
    assert first["seed_count"] == 0 and first["initial_seeds"] == []
    assert first["effective_seeds"] == [] and first["bootstrap_authority"] is None

    second_code = main([
        "survey", "run-public-source-workflow", "--topic", TOPIC, "--out", str(output),
        "--resume", "--confirm-public-discovery",
    ])
    second = json.loads(capsys.readouterr().out)
    assert second_code == 0
    assert second["bootstrap_attempt_state"] == "selected_complete"
    assert second["bootstrap_outcome"] == "unavailable"
    assert second["effective_seeds"] == [] and second["bootstrap_authority"] is None
    assert second["next_action"]["action_id"] == "terminal_blocked_bootstrap_unavailable"
    assert provider_calls == 0

    before = (output / ".mission_state" / "bootstrap" / "CURRENT").read_bytes()
    third_code = main([
        "survey", "run-public-source-workflow", "--topic", TOPIC, "--out", str(output), "--resume",
    ])
    third = json.loads(capsys.readouterr().out)
    assert third_code == 0
    assert third["bootstrap_outcome"] == "unavailable"
    assert (output / ".mission_state" / "bootstrap" / "CURRENT").read_bytes() == before
    assert provider_calls == 0


def test_cli_explicit_empty_seed_is_not_topic_mode(tmp_path: Path, capsys) -> None:
    code = main([
        "survey", "run-public-source-workflow", "--topic", TOPIC, "--seed", "", "--out", str(tmp_path / "empty"),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["blocked_reason"] == "invalid_normalized_text"


def test_topic_public_result_has_exact_v3_keys_and_selected_authority(tmp_path: Path) -> None:
    output = tmp_path / "selected-public"
    first = orchestrate.run_public_source_workflow(topic=TOPIC, seeds=None, output_dir=output)
    assert first["bootstrap_attempt_state"] == "confirmation_required"
    capability = FixtureCapability(_selected_outcome())
    selected = orchestrate.run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=output,
        resume=True,
        confirm_public_discovery=True,
        bootstrap_capability=capability,
    )
    assert set(selected) == {
        "schema_version", "status", "topic", "seed_count", "input_mode", "initial_seeds",
        "effective_seeds", "effective_seed_count", "bootstrap_attempt_state", "bootstrap_outcome",
        "bootstrap_authority", "output_dir", "mission_control_path", "next_action_path", "mission_id",
        "mission_fingerprint", "generation_id", "artifact_paths", "next_gate", "next_action",
        "public_discovery_confirmation", "review_queue_path", "review_queue_counts", "review_queue_reused",
        "artifact_state", "phase_statuses", "reviewed_artifacts", "coverage_artifacts", "final_artifacts",
        "safe_next_commands", "what_is_not_concluded", "local_supervisor",
    }
    assert selected["seed_count"] == 0 and selected["initial_seeds"] == []
    assert selected["effective_seeds"] == [SEED]
    assert selected["bootstrap_authority"]["effective_normalized_seed_keys"] == [SEED]
    assert capability.calls == 1


def test_selected_effective_seeds_build_only_through_replayed_authority(tmp_path: Path) -> None:
    mission = tmp_path / "selected-build"
    manager, snapshot = _confirmed_topic_snapshot(mission)
    capability = FixtureCapability(_selected_outcome())
    selected = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
    ).advance(capability)
    result = build_bootstrap_effective_seed_skeleton(
        manager=manager,
        snapshot=snapshot,
        output_dir=mission / "offline_skeleton",
        bootstrap_authority=selected["authority"],
    )
    assert result["status"] == "created_bootstrap_effective_seed_skeleton"
    context_path = Path(result["bootstrap_effective_seed_context_path"])
    context = json.loads(context_path.read_text())
    assert context["original_initial_seeds"] == []
    assert context["effective_seed_source"] == "selected_bootstrap_authority_not_original_mission_input"
    assert context["bootstrap_authority"] == selected["authority"]
    assert context["technical_claim_support_created"] is False
    candidate = json.loads((mission / "offline_skeleton" / "candidate_ledger.json").read_text())
    assert candidate["included"][0]["source"] == "selected_bootstrap_authority"
    assert candidate["included"][0]["bootstrap_set_id"] == selected["authority"]["set_id"]
    assert "supplied by user" not in json.dumps(candidate)

    reused = build_bootstrap_effective_seed_skeleton(
        manager=manager,
        snapshot=snapshot,
        output_dir=mission / "offline_skeleton",
        bootstrap_authority=selected["authority"],
    )
    assert reused["status"] == "reused_bootstrap_effective_seed_skeleton"
    stale = dict(selected["authority"])
    stale["request_sha256"] = "0" * 64
    with pytest.raises(MissionStateError) as error:
        build_bootstrap_effective_seed_skeleton(
            manager=manager,
            snapshot=snapshot,
            output_dir=mission / "offline_skeleton",
            bootstrap_authority=stale,
        )
    assert error.value.code == "stale_bootstrap_authority"
    manager.abort()


def test_bootstrap_bound_skeleton_tamper_blocks_reuse(tmp_path: Path) -> None:
    mission = tmp_path / "tampered-build"
    manager, snapshot = _confirmed_topic_snapshot(mission)
    selected = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
    ).advance(FixtureCapability(_selected_outcome()))
    output = mission / "offline_skeleton"
    build_bootstrap_effective_seed_skeleton(
        manager=manager,
        snapshot=snapshot,
        output_dir=output,
        bootstrap_authority=selected["authority"],
    )
    (output / "candidate_ledger.json").write_text("{}")
    with pytest.raises(MissionStateError) as error:
        build_bootstrap_effective_seed_skeleton(
            manager=manager,
            snapshot=snapshot,
            output_dir=output,
            bootstrap_authority=selected["authority"],
        )
    assert error.value.code == "bootstrap_skeleton_artifact_mismatch"
    manager.abort()


def test_history_only_call_started_crash_reconciles_to_indeterminate(tmp_path: Path) -> None:
    output = tmp_path / "history-lag"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap_call_started:after_history_fsync",
    )
    with pytest.raises(RuntimeError, match="after_history_fsync"):
        store.advance(capability)
    assert capability.calls == 0
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    resumed = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    )
    with pytest.raises(MissionStateError) as error:
        resumed.advance(capability)
    assert error.value.code == "bootstrap_call_indeterminate"
    assert resumed.observe()["attempt_state"] == "call_started_indeterminate"
    assert capability.calls == 0
    resumed_manager.abort()


def test_crash_after_capability_return_is_indeterminate_without_retry(tmp_path: Path) -> None:
    output = tmp_path / "return-crash"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap:after_capability_return",
    )
    with pytest.raises(MissionStateError) as error:
        store.advance(capability)
    assert error.value.code == "bootstrap_call_indeterminate"
    assert capability.calls == 1
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    with pytest.raises(MissionStateError) as resumed_error:
        MissionBootstrapStore.from_snapshot(
            manager=resumed_manager,
            snapshot=resumed_snapshot,
            now=lambda: NOW,
        ).advance(capability)
    assert resumed_error.value.code == "bootstrap_call_indeterminate"
    assert capability.calls == 1
    resumed_manager.abort()


def test_result_recorded_history_lag_recovers_without_second_call(tmp_path: Path) -> None:
    output = tmp_path / "result-history-lag"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap_result_recorded:after_history_fsync",
    )
    with pytest.raises(RuntimeError, match="after_history_fsync"):
        store.advance(capability)
    assert capability.calls == 1
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    selected = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    ).advance(capability)
    assert selected["attempt_state"] == "selected_complete"
    assert capability.calls == 1
    resumed_manager.abort()


def test_pointer_selected_history_lag_reconciles_without_second_call(tmp_path: Path) -> None:
    output = tmp_path / "selected-history-lag"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap_selected:after_history_fsync",
    )
    with pytest.raises(RuntimeError, match="after_history_fsync"):
        store.advance(capability)
    assert capability.calls == 1
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    selected = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    ).advance(capability)
    assert selected["attempt_state"] == "selected_complete"
    assert capability.calls == 1
    resumed_manager.abort()


@pytest.mark.parametrize("target", ["pointer", "manifest", "history"])
def test_corrupt_selected_bootstrap_evidence_fails_closed(tmp_path: Path, target: str) -> None:
    output = tmp_path / f"corrupt-{target}"
    manager, snapshot = _confirmed_topic_snapshot(output)
    selected = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
    ).advance(FixtureCapability(_selected_outcome()))
    manager.abort()
    bootstrap_root = output / ".mission_state" / "bootstrap"
    if target == "pointer":
        (bootstrap_root / "CURRENT").write_text("{}")
    elif target == "manifest":
        (Path(selected["set_dir"]) / "manifest.json").write_text("{}")
    else:
        request = selected["request_id"]
        history = bootstrap_root / "history" / request / "prepared.json"
        history.write_text("{}")

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    with pytest.raises(MissionStateError):
        MissionBootstrapStore.from_snapshot(
            manager=resumed_manager,
            snapshot=resumed_snapshot,
            now=lambda: NOW,
        )
    resumed_manager.abort()


def test_foreign_or_nonregular_bootstrap_residue_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "foreign-residue"
    manager, snapshot = _confirmed_topic_snapshot(output)
    store = MissionBootstrapStore.from_snapshot(manager=manager, snapshot=snapshot, now=lambda: NOW)
    foreign = store.results_dir / "foreign.json"
    foreign.write_text("{}")
    with pytest.raises(MissionStateError):
        store.observe()
    foreign.unlink()
    os.symlink("missing", foreign)
    with pytest.raises(MissionStateError):
        store.observe()
    manager.abort()


def test_crash_after_result_file_fsync_is_indeterminate_without_retry(tmp_path: Path) -> None:
    output = tmp_path / "result-file-crash"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at="bootstrap_result:after_directory_fsync",
    )
    with pytest.raises(RuntimeError, match="bootstrap_result"):
        store.advance(capability)
    assert capability.calls == 1
    assert store.observe()["attempt_state"] == "call_started_indeterminate"
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    resumed_store = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    )
    with pytest.raises(MissionStateError) as error:
        resumed_store.advance(capability)
    assert error.value.code == "bootstrap_call_indeterminate"
    assert capability.calls == 1
    resumed_manager.abort()


def test_valid_journal_projection_is_rejected_when_foreign_to_active_contract(tmp_path: Path) -> None:
    output = tmp_path / "foreign-journal"
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(manager=manager, snapshot=snapshot, now=lambda: NOW)
    selected = store.advance(capability)
    bootstrap = output / ".mission_state" / "bootstrap"
    request_id = selected["request_id"]
    journal = json.loads((bootstrap / "transactions" / f"{request_id}.json").read_text())
    foreign = json.loads(json.dumps(journal))
    foreign["request"]["output_root"] = str(tmp_path / "another-mission")
    with pytest.raises(MissionStateError) as error:
        store._assert_journal_binding(foreign)
    assert error.value.code == "foreign_bootstrap_journal"
    manager.abort()


@pytest.mark.parametrize(
    ("crash_at", "expected_state", "calls_before", "resumes_selected"),
    [
        ("bootstrap:before_intent", "not_started", 0, True),
        ("bootstrap_intent:after_history_fsync", "intent", 0, True),
        ("bootstrap_intent:after_directory_fsync", "intent", 0, True),
        ("bootstrap:after_intent", "intent", 0, True),
        ("bootstrap:before_call_started", "intent", 0, True),
        ("bootstrap_call_started:after_history_fsync", "call_started_indeterminate", 0, False),
        ("bootstrap_call_started:after_directory_fsync", "call_started_indeterminate", 0, False),
        ("bootstrap:after_call_started", "call_started_indeterminate", 0, False),
        ("bootstrap:after_capability_return", "call_started_indeterminate", 1, False),
        ("bootstrap_result:after_temp_write", "call_started_indeterminate", 1, False),
        ("bootstrap_result:after_temp_fsync", "call_started_indeterminate", 1, False),
        ("bootstrap_result:after_replace", "call_started_indeterminate", 1, False),
        ("bootstrap_result:after_directory_fsync", "call_started_indeterminate", 1, False),
        ("bootstrap_result_recorded:after_history_fsync", "result_recorded", 1, True),
        ("bootstrap_result_recorded:after_directory_fsync", "result_recorded", 1, True),
        ("bootstrap:after_result_recorded", "result_recorded", 1, True),
        ("bootstrap_set:outcome.json:before_write", "result_recorded", 1, True),
        ("bootstrap_set:outcome.json:after_write", "result_recorded", 1, True),
        ("bootstrap_set:outcome.json:after_fsync", "result_recorded", 1, True),
        ("bootstrap_set:manifest.json:before_write", "result_recorded", 1, True),
        ("bootstrap_set:manifest.json:after_write", "result_recorded", 1, True),
        ("bootstrap_set:manifest.json:after_fsync", "result_recorded", 1, True),
        ("bootstrap_set:before_staging_fsync", "result_recorded", 1, True),
        ("bootstrap_set:after_staging_fsync", "result_recorded", 1, True),
        ("bootstrap_set:before_final_rename", "result_recorded", 1, True),
        ("bootstrap_set:after_final_rename", "result_recorded", 1, True),
        ("bootstrap_set:after_parent_fsync", "result_recorded", 1, True),
        ("bootstrap_prepared:after_history_fsync", "prepared", 1, True),
        ("bootstrap_prepared:after_directory_fsync", "prepared", 1, True),
        ("bootstrap:after_prepared", "prepared", 1, True),
        ("bootstrap:before_pointer_selection", "prepared", 1, True),
        ("bootstrap_current:after_temp_write", "prepared", 1, True),
        ("bootstrap_current:after_temp_fsync", "prepared", 1, True),
        ("bootstrap_current:after_replace", "prepared", 1, True),
        ("bootstrap_current:after_directory_fsync", "prepared", 1, True),
        ("bootstrap:after_pointer_selection", "prepared", 1, True),
        ("bootstrap_selected:after_history_fsync", "selected_complete", 1, True),
        ("bootstrap_selected:after_directory_fsync", "selected_complete", 1, True),
    ],
)
def test_complete_bootstrap_crash_matrix(
    tmp_path: Path,
    crash_at: str,
    expected_state: str,
    calls_before: int,
    resumes_selected: bool,
) -> None:
    output = tmp_path / hashlib.sha256(crash_at.encode()).hexdigest()[:12]
    manager, snapshot = _confirmed_topic_snapshot(output)
    capability = FixtureCapability(_selected_outcome())
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: NOW,
        crash_at=crash_at,
    )
    if crash_at == "bootstrap:after_capability_return":
        with pytest.raises(MissionStateError) as initial_error:
            store.advance(capability)
        assert initial_error.value.code == "bootstrap_call_indeterminate"
    else:
        with pytest.raises(RuntimeError, match="injected crash"):
            store.advance(capability)
    assert capability.calls == calls_before
    manager.abort()

    resumed_manager = _manager(output, topic_mode=True, resume=True)
    resumed_snapshot = resumed_manager.begin()
    resumed_store = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: NOW,
    )
    observed = resumed_store.observe()
    assert observed["attempt_state"] == expected_state
    assert observed["authority"] is None or expected_state == "selected_complete"
    if resumes_selected:
        selected = resumed_store.advance(capability)
        assert selected["attempt_state"] == "selected_complete"
        assert selected["effective_seeds"] == [SEED]
        assert capability.calls == 1
    else:
        with pytest.raises(MissionStateError) as error:
            resumed_store.advance(capability)
        assert error.value.code == "bootstrap_call_indeterminate"
        assert capability.calls == calls_before
    resumed_manager.abort()
