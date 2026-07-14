from __future__ import annotations

import json
from pathlib import Path

import pytest

import research_assistant.survey.mission_state as mission_state
from research_assistant.cli import main
from research_assistant.survey.build import build_survey_evidence_packet
from research_assistant.survey.mission_state import (
    MissionStateError,
    MissionStateManager,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.source_intake import (
    MissionSourceCapability,
    SourceCapabilityResult,
    build_source_intake_metadata_authority,
    derive_source_paper_id,
    run_mission_source_intake,
    validate_mission_source_intake,
)
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.packet import compose_public_source_evidence_packet


TOPIC = "Neural Optimal Transport"
SEED = "arxiv:2201.12220v3"


def _write_builder_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _candidate(index: int, *, identifier: str, roles: list[str], providers: list[str]) -> dict:
    return {
        "paper_key": f"p_meta_{index:03d}",
        "identifier": identifier,
        "title": f"Candidate {index}",
        "authors": ["Fixture Author"],
        "year": 2024,
        "roles": roles,
        "providers": providers,
        "citation_count": None,
        "citation_count_policy": "coverage_signal_only",
        "reason": "bounded Phase 6 fixture candidate",
        "metadata_only": True,
    }


def _write_metadata(mission: Path, identifiers: list[str]) -> Path:
    root = mission / "public_metadata"
    build = build_survey_evidence_packet(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=root,
        mode="offline-skeleton",
    )
    assert build["status"] == "created_skeleton"
    included = []
    for index, identifier in enumerate(identifiers, start=1):
        seed = index == 1
        included.append(
            _candidate(
                index,
                identifier=identifier,
                roles=["seed"] if seed else ["adjacent_method"],
                providers=["arxiv"] if identifier.startswith("arxiv:") else ["openalex"],
            )
        )
    ledger = {
        "schema_version": "ra-survey-candidate-ledger-v1",
        "status": "metadata_only_public",
        "topic": TOPIC,
        "candidate_count": len(included),
        "max_records": 25,
        "included": included,
        "excluded": [],
        "duplicates": [],
        "provider_statuses": [],
        "raw_response_policy": {
            "privacy_scan": "not_applicable_raw_responses_not_saved",
            "raw_responses_saved": False,
            "reason": "fixture metadata only",
        },
        "next_required_actions": ["inspect primary sources"],
    }
    manifest = {
        "schema_version": "ra-survey-build-manifest-v1",
        "status": "metadata_only_packet",
        "mode": "public-metadata",
        "workflow_state": {
            "schema_version": "ra-survey-workflow-state-v1",
            "state": "metadata_only_public_packet",
            "mode": "public-metadata",
            "ready_for_writer": True,
            "ready_for_prose": False,
            "safe_next_commands": [],
            "approval_required_for": [],
            "blocked_reasons": [],
            "forbidden_jumps": [],
        },
        "mission": "fixture mission",
        "topic": TOPIC,
        "providers": ["openalex", "arxiv"],
        "max_records": 25,
        "record_count": len(included),
        "provider_statuses": [],
        "artifact_paths": {
            name: str(root / name)
            for name in (
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
            )
        },
        "mission_control_path": "fixture",
        "milestones_path": "fixture",
        "next_required_actions": [],
        "forbidden_claims": [],
        "what_is_not_concluded": [],
    }
    _write_builder_json(root / "candidate_ledger.json", ledger)
    _write_builder_json(root / "build_manifest.json", manifest)
    return root


def _checkpoint_source_authority(
    mission: Path,
    *,
    identifiers: list[str] | None = None,
    confirmed: bool = True,
) -> tuple[MissionStateManager, object, Path]:
    identifiers = identifiers or [SEED, "doi:10.1000/fixture"]
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[SEED],
        confirm_public_discovery=confirmed,
        resume=False,
        force=False,
    )
    initial = manager.begin()
    metadata = _write_metadata(mission, identifiers)
    authority = build_source_intake_metadata_authority(
        mission_root=mission,
        metadata_root=metadata,
        snapshot=initial,
    )
    next_action = {
        "schema_version": "ra-survey-public-source-next-action-v1",
        "status": "ready_for_source_intake",
        "mission_status": "ready_for_local_continuation",
        "action_id": "source_intake",
        "source_intake_metadata_authority": authority,
    }
    mission_control = {
        "status": "ready_for_local_continuation",
        "topic": TOPIC,
        "seeds": [SEED],
        "output_dir": str(mission),
        "source_intake_metadata_authority": authority,
    }
    snapshot = manager.checkpoint(mission_control, next_action)
    return manager, snapshot, metadata


def _record(request, *, raw_latex: str = "Fixture source text.") -> dict:
    return {
        "paper_id": request.paper_id,
        "source_type": "arxiv_latex",
        "status": "available",
        "primary_for_audit": True,
        "artifact_root": None,
        "original_source_path": None,
        "flattened_source_path": None,
        "sections": [
            {
                "level": 1,
                "command": "section",
                "title": "Method",
                "line": 1,
                "labels": ["sec:method"],
                "raw_latex": raw_latex,
            }
        ],
        "equations": [],
        "theorem_like_blocks": [],
        "labels": [],
        "references": [],
        "citations": [],
        "bibliography": [],
        "macros": [],
        "provenance": {
            "identifier": request.identifier,
            "provider": request.providers[0],
            "final_url": "https://arxiv.org/abs/2201.12220",
            "fixture_only": True,
        },
        "diagnostics": {"fixture_only": True, "section_count": 1},
        "limitations": [
            {
                "field": "source",
                "status": "fixture_only",
                "note": "No live source transport was run.",
            }
        ],
    }


def _available(request, *, final_url: str = "https://arxiv.org/abs/2201.12220", raw_latex: str = "Fixture source text.") -> SourceCapabilityResult:
    record = _record(request, raw_latex=raw_latex)
    return SourceCapabilityResult(
        candidate_id=request.candidate_id,
        identifier=request.identifier,
        outcome_status="available",
        code="available",
        provider=request.providers[0],
        final_url=final_url,
        structured_record=record,
        byte_count=len(pretty_json_bytes(record)),
    )


def _unavailable(request) -> SourceCapabilityResult:
    return SourceCapabilityResult(
        candidate_id=request.candidate_id,
        identifier=request.identifier,
        outcome_status="unavailable",
        code="unavailable",
        provider=request.providers[0],
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _rewrite_outcome_ledger(mission: Path, mutate) -> None:
    intake = mission / "source_intake"
    ledger_path = intake / "source_intake_outcomes.json"
    status_path = intake / "phase4_source_intake_status.json"
    ledger = _load(ledger_path)
    mutate(ledger)
    ledger_bytes = pretty_json_bytes(ledger)
    ledger_path.write_bytes(ledger_bytes)
    status = _load(status_path)
    status["outcome_ledger_sha256"] = sha256_bytes(ledger_bytes)
    status["outcome_ledger_size_bytes"] = len(ledger_bytes)
    status_path.write_bytes(pretty_json_bytes(status))


def test_fixture_intake_materializes_available_only_authority_and_replays(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission)
    calls: list[str] = []

    def handler(request):
        calls.append(request.candidate_id)
        return _available(request) if request.candidate_index == 0 else _unavailable(request)

    try:
        result = run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(handler),
        )
        validated = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()

    assert result["status"] == "completed_with_outcomes"
    assert calls == ["p_meta_001", "p_meta_002"]
    assert validated["paper_ids"] == [derive_source_paper_id(SEED)]
    assert [row["outcome_status"] for row in validated["outcomes"]] == ["available", "unavailable"]
    status = validated["status"]
    assert status["ready_for_claim_support"] is False
    assert status["source_support"][0]["technical_claim_support"] is False


def test_complete_status_is_idempotent_and_never_recalls_capability(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission)
    try:
        first = run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        before = {path: path.read_bytes() for path in map(Path, first["required_output_paths"])}

        def forbidden(request):
            raise AssertionError(f"capability recalled for {request.candidate_id}")

        second = run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(forbidden),
        )
        after = {path: path.read_bytes() for path in map(Path, second["required_output_paths"])}
    finally:
        manager.abort()
    assert second["status"] == "reused_complete_status"
    assert after == before


def test_unconfirmed_mission_blocks_before_capability_call_or_write(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, confirmed=False)
    called = False

    def forbidden(request):
        nonlocal called
        called = True
        return _available(request)

    try:
        with pytest.raises(MissionStateError) as error:
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(forbidden),
            )
    finally:
        manager.abort()
    assert error.value.code == "source_intake_confirmation_required"
    assert called is False
    assert not (mission / "source_intake").exists()


def test_exact_hostname_rejects_suffix_bypass_without_record_authority(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(
                lambda request: _available(request, final_url="https://arxiv.org.evil.example/abs/x")
            ),
        )
        validated = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert validated["paper_ids"] == []
    assert validated["outcomes"][0]["outcome_status"] == "failed"
    assert validated["outcomes"][0]["code"] == "invalid_capability_result"
    assert not (mission / "local_research" / "papers" / "source" / "records").exists()


def test_source_call_cap_creates_ordered_not_attempted_rows(tmp_path: Path) -> None:
    identifiers = [SEED, *(f"doi:10.1000/fixture-{index}" for index in range(1, 7))]
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=identifiers)
    calls: list[int] = []

    def handler(request):
        calls.append(request.candidate_index)
        return _unavailable(request)

    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(handler),
        )
        outcomes = validate_mission_source_intake(
            mission_root=mission,
            snapshot=snapshot,
        )["outcomes"]
    finally:
        manager.abort()
    assert calls == [0, 1, 2, 3, 4]
    assert [row["outcome_status"] for row in outcomes[5:]] == [
        "not_attempted_cap",
        "not_attempted_cap",
    ]
    assert {row["cap_kind"] for row in outcomes[5:]} == {"source_count"}


def test_unsupported_identifier_is_no_call_and_does_not_consume_call_cap(tmp_path: Path) -> None:
    identifiers = [
        SEED,
        "unsupported:fixture",
        "doi:10.1000/fixture-2",
        "doi:10.1000/fixture-3",
        "doi:10.1000/fixture-4",
        "doi:10.1000/fixture-5",
        "doi:10.1000/fixture-6",
    ]
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=identifiers)
    calls: list[int] = []

    def handler(request):
        calls.append(request.candidate_index)
        return _unavailable(request)

    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(handler),
        )
        outcomes = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)["outcomes"]
    finally:
        manager.abort()
    assert calls == [0, 2, 3, 4, 5]
    assert outcomes[1]["outcome_status"] == "unsupported_identifier"
    assert outcomes[1]["code"] == "unsupported_identifier"
    assert outcomes[6]["outcome_status"] == "not_attempted_cap"
    assert outcomes[6]["cap_kind"] == "source_count"


def test_oversize_record_exhausts_remaining_calls_without_write(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mission_state, "MAX_BYTES_PER_SOURCE", 700)
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(
        mission,
        identifiers=[SEED, "doi:10.1000/later"],
    )
    calls: list[int] = []

    def handler(request):
        calls.append(request.candidate_index)
        return _available(request, raw_latex="x" * 2_000)

    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(handler),
        )
        outcomes = validate_mission_source_intake(
            mission_root=mission,
            snapshot=snapshot,
        )["outcomes"]
    finally:
        manager.abort()
    assert calls == [0]
    assert outcomes[0]["code"] == "byte_budget_exceeded"
    assert outcomes[1]["outcome_status"] == "not_attempted_cap"
    assert outcomes[1]["cap_kind"] == "cumulative_bytes"
    assert not (mission / "local_research" / "papers" / "source" / "records").exists()


def test_identical_record_orphan_is_reused_after_pre_status_crash(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])

    def crash(point: str) -> None:
        if point == "source_record:after_directory_fsync":
            raise RuntimeError("injected pre-status crash")

    try:
        with pytest.raises(RuntimeError, match="pre-status crash"):
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(_available),
                crash_hook=crash,
            )
        record = (
            mission
            / "local_research"
            / "papers"
            / "source"
            / "records"
            / f"{derive_source_paper_id(SEED)}.json"
        )
        before = record.read_bytes()
        result = run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
    finally:
        manager.abort()
    assert result["status"] == "completed_with_outcomes"
    assert record.read_bytes() == before


def test_conflicting_record_orphan_blocks_without_overwrite(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    record = (
        mission
        / "local_research"
        / "papers"
        / "source"
        / "records"
        / f"{derive_source_paper_id(SEED)}.json"
    )
    record.parent.mkdir(parents=True)
    record.write_bytes(b"conflict")
    try:
        with pytest.raises(MissionStateError) as error:
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(_available),
            )
    finally:
        manager.abort()
    assert error.value.code == "conflicting_source_record_orphan"
    assert record.read_bytes() == b"conflict"
    assert not (mission / "source_intake").exists()


def test_nonavailable_retry_after_record_orphan_blocks_before_status_commit(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])

    def crash(point: str) -> None:
        if point == "source_record:after_directory_fsync":
            raise RuntimeError("injected pre-status crash")

    try:
        with pytest.raises(RuntimeError, match="pre-status crash"):
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(_available),
                crash_hook=crash,
            )
        with pytest.raises(MissionStateError) as error:
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(_unavailable),
            )
    finally:
        manager.abort()
    assert error.value.code == "conflicting_source_record_orphan"
    assert not (mission / "source_intake").exists()


def test_replay_rejects_nonavailable_row_promoted_into_source_support(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission)
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(
                lambda request: _available(request) if request.candidate_index == 0 else _unavailable(request)
            ),
        )
        status_path = mission / "source_intake" / "phase4_source_intake_status.json"
        status = _load(status_path)
        forged = dict(status["source_support"][0])
        forged["candidate_id"] = "p_meta_002"
        status["source_support"].append(forged)
        status_path.write_bytes(pretty_json_bytes(status))
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "source_support_set_mismatch"


def test_standalone_packet_and_cli_reject_v2_before_output_write(
    tmp_path: Path,
    capsys,
) -> None:
    source_status = tmp_path / "source_intake"
    source_status.mkdir()
    (source_status / "phase4_source_intake_status.json").write_bytes(
        pretty_json_bytes(
            {
                "schema_version": "ra-survey-mission-source-intake-v2",
                "status": "plausible_but_unvalidated",
            }
        )
    )
    direct_out = tmp_path / "direct-output"
    direct = compose_public_source_evidence_packet(
        topic=TOPIC,
        output_dir=direct_out,
        metadata_dir=tmp_path / "missing-metadata",
        source_status_dir=source_status,
        anchor_dir=tmp_path / "missing-anchors",
    )
    assert direct["blocked_reason"] == "mission_v2_source_intake_requires_supervisor_authority"
    assert not direct_out.exists()

    cli_out = tmp_path / "cli-output"
    rc = main(
        [
            "survey",
            "packet",
            "--topic",
            TOPIC,
            "--out",
            str(cli_out),
            "--metadata-dir",
            str(tmp_path / "missing-metadata"),
            "--source-status-dir",
            str(source_status),
            "--anchor-dir",
            str(tmp_path / "missing-anchors"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["blocked_reason"] == "mission_v2_source_intake_requires_supervisor_authority"
    assert not cli_out.exists()


def test_safe_local_fixture_capability_continues_to_human_review_same_invocation(
    tmp_path: Path,
) -> None:
    mission = tmp_path / "mission"
    initial = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        run_safe_local=True,
    )
    assert initial["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    metadata = _write_metadata(mission, [SEED])
    calls: list[str] = []

    def handler(request):
        calls.append(request.candidate_id)
        return _available(request)

    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(handler),
    )
    assert metadata == mission / "public_metadata"
    assert calls == ["p_meta_001"]
    assert result["local_supervisor"]["status"] == "terminal_blocked_human_review"
    stages = [row["stage_id"] for row in result["local_supervisor"]["transition_history"]]
    assert stages[:3] == ["source_intake", "source_anchors", "public_source_packet"]
    assert (mission / "source_intake" / "phase4_source_intake_status.json").is_file()
    assert (mission / "source_anchors" / "source_anchor_inventory.json").is_file()
    assert (mission / "public_source_packet" / "build_manifest.json").is_file()


def test_duplicate_identifier_produces_visible_duplicate_not_duplicate_authority(
    tmp_path: Path,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(
        mission,
        identifiers=[SEED, SEED],
    )
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        validated = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert [row["outcome_status"] for row in validated["outcomes"]] == [
        "available",
        "duplicate",
    ]
    assert validated["paper_ids"] == [derive_source_paper_id(SEED)]


def test_later_generation_keeps_creation_generation_valid_on_active_ancestry(
    tmp_path: Path,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    run_mission_source_intake(
        mission_root=mission,
        metadata_root=metadata,
        snapshot=snapshot,
        capability=MissionSourceCapability(_available),
    )
    later_mission = dict(snapshot.mission_control or {})
    later_next = dict(snapshot.next_action or {})
    later_mission["status"] = "later_fixture_generation"
    later_next["status"] = "later_fixture_generation"
    later_mission["next_action"] = later_next
    later = manager.checkpoint(later_mission, later_next)
    try:
        validated = validate_mission_source_intake(mission_root=mission, snapshot=later)
    finally:
        manager.abort()
    assert validated["status"]["creation_generation_id"] == snapshot.current_pointer["generation_id"]
    assert later.current_pointer["generation_id"] != snapshot.current_pointer["generation_id"]


def test_metadata_tamper_after_intake_is_rejected_on_replay(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        ledger_path = metadata / "candidate_ledger.json"
        ledger = _load(ledger_path)
        ledger["included"][0]["title"] = "Tampered title"
        _write_builder_json(ledger_path, ledger)
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "stale_source_metadata"


def test_metadata_candidate_provider_must_be_within_persisted_budget(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[SEED],
        confirm_public_discovery=True,
        resume=False,
        force=False,
    )
    snapshot = manager.begin()
    metadata = _write_metadata(mission, [SEED])
    ledger_path = metadata / "candidate_ledger.json"
    ledger = _load(ledger_path)
    ledger["included"][0]["providers"] = ["untrusted-provider"]
    _write_builder_json(ledger_path, ledger)
    try:
        with pytest.raises(MissionStateError) as error:
            build_source_intake_metadata_authority(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
            )
    finally:
        manager.abort()
    assert error.value.code == "source_candidate_provider_mismatch"


@pytest.mark.parametrize("mutation", ["extra_manifest_field", "missing_artifact_path", "bad_workflow_mode"])
def test_metadata_manifest_schema_is_closed(tmp_path: Path, mutation: str) -> None:
    mission = tmp_path / "mission"
    manager = MissionStateManager(
        output_dir=mission,
        topic=TOPIC,
        seeds=[SEED],
        confirm_public_discovery=True,
        resume=False,
        force=False,
    )
    snapshot = manager.begin()
    metadata = _write_metadata(mission, [SEED])
    manifest_path = metadata / "build_manifest.json"
    manifest = _load(manifest_path)
    if mutation == "extra_manifest_field":
        manifest["unexpected"] = True
    elif mutation == "missing_artifact_path":
        del manifest["artifact_paths"]["workflow_state.json"]
    else:
        manifest["workflow_state"]["mode"] = "offline-skeleton"
    _write_builder_json(manifest_path, manifest)
    try:
        with pytest.raises(MissionStateError):
            build_source_intake_metadata_authority(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
            )
    finally:
        manager.abort()


@pytest.mark.parametrize(
    "case",
    [
        "provider",
        "http_url",
        "credential_url",
        "port_url",
        "fragment_url",
        "suffix_host",
        "byte_count",
        "declared_digest",
        "record_paper_id",
        "record_path",
        "record_source_type",
        "result_status_type",
        "result_code_type",
        "result_provider_type",
        "declared_digest_type",
        "byte_count_type",
        "bibliography_private_field",
        "diagnostic_type",
    ],
)
def test_invalid_available_capability_result_is_bounded_without_record_write(
    tmp_path: Path,
    case: str,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])

    def handler(request):
        result = _available(request)
        if case in {
            "result_status_type",
            "result_code_type",
            "result_provider_type",
            "declared_digest_type",
            "byte_count_type",
        }:
            return SourceCapabilityResult(
                candidate_id=request.candidate_id,
                identifier=request.identifier,
                outcome_status=[] if case == "result_status_type" else "available",
                code=[] if case == "result_code_type" else "available",
                provider=[] if case == "result_provider_type" else result.provider,
                final_url=result.final_url,
                structured_record=result.structured_record,
                declared_record_sha256=[] if case == "declared_digest_type" else None,
                byte_count=[] if case == "byte_count_type" else result.byte_count,
            )
        if case == "provider":
            return SourceCapabilityResult(
                candidate_id=request.candidate_id,
                identifier=request.identifier,
                outcome_status="available",
                code="available",
                provider="untrusted-provider",
                final_url=result.final_url,
                structured_record=result.structured_record,
                byte_count=result.byte_count,
            )
        if case.endswith("url") or case == "suffix_host":
            url = {
                "http_url": "http://arxiv.org/abs/2201.12220",
                "credential_url": "https://user:pass@arxiv.org/abs/2201.12220",
                "port_url": "https://arxiv.org:443/abs/2201.12220",
                "fragment_url": "https://arxiv.org/abs/2201.12220#source",
                "suffix_host": "https://arxiv.org.evil.example/abs/2201.12220",
            }[case]
            return SourceCapabilityResult(
                candidate_id=request.candidate_id,
                identifier=request.identifier,
                outcome_status="available",
                code="available",
                provider=result.provider,
                final_url=url,
                structured_record=result.structured_record,
                byte_count=result.byte_count,
            )
        assert result.structured_record is not None
        record = result.structured_record
        declared_digest = None
        byte_count = result.byte_count
        if case == "byte_count":
            byte_count += 1
        elif case == "declared_digest":
            declared_digest = "0" * 64
        elif case == "record_paper_id":
            record["paper_id"] = "../../escape"
            byte_count = len(pretty_json_bytes(record))
        elif case == "record_path":
            record["artifact_root"] = "/tmp/forbidden"
            byte_count = len(pretty_json_bytes(record))
        elif case == "record_source_type":
            record["source_type"] = ["arxiv_latex"]
            byte_count = len(pretty_json_bytes(record))
        elif case == "bibliography_private_field":
            record["bibliography"] = [
                {
                    "type": "article",
                    "key": "fixture",
                    "fields": {"api_token": "must-not-persist"},
                    "path": None,
                }
            ]
            byte_count = len(pretty_json_bytes(record))
        elif case == "diagnostic_type":
            record["diagnostics"]["section_count"] = True
            byte_count = len(pretty_json_bytes(record))
        return SourceCapabilityResult(
            candidate_id=request.candidate_id,
            identifier=request.identifier,
            outcome_status="available",
            code="available",
            provider=result.provider,
            final_url=result.final_url,
            structured_record=record,
            declared_record_sha256=declared_digest,
            byte_count=byte_count,
        )

    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(handler),
        )
        validated = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert validated["paper_ids"] == []
    assert validated["outcomes"][0]["outcome_status"] == "failed"
    assert validated["outcomes"][0]["code"] == "invalid_capability_result"
    assert not (mission / "local_research" / "papers" / "source" / "records").exists()


def test_unknown_nested_record_field_becomes_bounded_failed_outcome(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])

    def handler(request):
        result = _available(request)
        assert result.structured_record is not None
        result.structured_record["sections"][0]["private_token"] = "must-not-persist"
        return result

    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(handler),
        )
        validated = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert validated["outcomes"][0]["outcome_status"] == "failed"
    assert validated["outcomes"][0]["code"] == "invalid_capability_result"
    assert b"must-not-persist" not in (
        mission / "source_intake" / "phase4_source_intake_status.json"
    ).read_bytes()


def test_invalid_capability_schema_blocks_before_handler_and_outputs(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    called = False

    def handler(request):
        nonlocal called
        called = True
        return _available(request)

    try:
        with pytest.raises(MissionStateError) as error:
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(
                    handler,
                    schema_version="forged-capability-v1",
                ),
            )
    finally:
        manager.abort()
    assert error.value.code == "invalid_source_capability"
    assert called is False
    assert not (mission / "source_intake").exists()


def test_status_extra_field_is_rejected_even_when_pretty_canonical(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        status_path = mission / "source_intake" / "phase4_source_intake_status.json"
        status = _load(status_path)
        status["unexpected"] = True
        status_path.write_bytes(pretty_json_bytes(status))
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "invalid_source_intake_schema"


def test_replay_rejects_record_provenance_rewrite_with_rehashed_authority(
    tmp_path: Path,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        intake_root = mission / "source_intake"
        ledger_path = intake_root / "source_intake_outcomes.json"
        status_path = intake_root / "phase4_source_intake_status.json"
        record_path = (
            mission
            / "local_research"
            / "papers"
            / "source"
            / "records"
            / f"{derive_source_paper_id(SEED)}.json"
        )

        forged_url = "https://arxiv.org/abs/9999.99999"
        record = _load(record_path)
        record["provenance"]["final_url"] = forged_url
        record_bytes = pretty_json_bytes(record)
        record_path.write_bytes(record_bytes)

        ledger = _load(ledger_path)
        ledger["outcomes"][0]["source_record_sha256"] = sha256_bytes(record_bytes)
        ledger["outcomes"][0]["source_record_size_bytes"] = len(record_bytes)
        ledger["accepted_record_bytes"] = len(record_bytes)
        ledger_bytes = pretty_json_bytes(ledger)
        ledger_path.write_bytes(ledger_bytes)

        status = _load(status_path)
        support = status["source_support"][0]
        support["source_record_sha256"] = sha256_bytes(record_bytes)
        support["source_record_size_bytes"] = len(record_bytes)
        status["accepted_record_bytes"] = len(record_bytes)
        status["outcome_ledger_sha256"] = sha256_bytes(ledger_bytes)
        status["outcome_ledger_size_bytes"] = len(ledger_bytes)
        status_path.write_bytes(pretty_json_bytes(status))

        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "source_record_provenance_mismatch"


@pytest.mark.parametrize(
    "field",
    ["mission_contract_sha256", "mission_control_sha256", "next_action_sha256"],
)
def test_replay_rejects_wrong_creation_generation_payload_digest(
    tmp_path: Path,
    field: str,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        status_path = mission / "source_intake" / "phase4_source_intake_status.json"
        status = _load(status_path)
        status[field] = "0" * 64
        status_path.write_bytes(pretty_json_bytes(status))
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "source_intake_mission_binding_mismatch"


def test_replay_rejects_nonancestor_creation_generation(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        status_path = mission / "source_intake" / "phase4_source_intake_status.json"
        status = _load(status_path)
        status["creation_generation_id"] = "g99999999-ffffffffffffffff"
        status_path.write_bytes(pretty_json_bytes(status))
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "artifact_anchor_not_ancestor"


def test_replay_rejects_reordered_outcomes_with_rehashed_ledger(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission)
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(
                lambda request: _available(request) if request.candidate_index == 0 else _unavailable(request)
            ),
        )
        _rewrite_outcome_ledger(mission, lambda ledger: ledger["outcomes"].reverse())
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "source_outcome_identity_mismatch"


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("provider", "openalex", "invalid_source_outcomes"),
        ("final_url", "https://evil.example/abs/2201.12220", "source_domain_not_allowed"),
    ],
)
def test_replay_rejects_rehashed_outcome_authority_variant(
    tmp_path: Path,
    field: str,
    value: str,
    expected_code: str,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        _rewrite_outcome_ledger(
            mission,
            lambda ledger: ledger["outcomes"][0].__setitem__(field, value),
        )
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == expected_code


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_index", False),
        ("provider", None),
        ("source_record_path", 7),
        ("source_record_sha256", "not-a-digest"),
        ("source_record_size_bytes", True),
    ],
)
def test_replay_rejects_malformed_outcome_field_types(
    tmp_path: Path,
    field: str,
    value,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        _rewrite_outcome_ledger(
            mission,
            lambda ledger: ledger["outcomes"][0].__setitem__(field, value),
        )
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "invalid_source_outcomes"


@pytest.mark.parametrize(
    ("target", "field", "value", "expected_code"),
    [
        ("status", "outcome_ledger_path", [], "invalid_source_intake_status"),
        ("status", "outcome_ledger_size_bytes", True, "invalid_source_intake_status"),
        ("status", "accepted_record_bytes", True, "invalid_source_intake_status"),
        ("status", "counts", [], "invalid_source_intake_status"),
        ("status", "counts", {"available": True}, "invalid_source_intake_status"),
        ("ledger", "accepted_record_bytes", True, "invalid_source_outcome_schema"),
        ("ledger", "counts", [], "invalid_source_outcome_schema"),
        ("ledger", "counts", {"available": True}, "invalid_source_outcome_schema"),
    ],
)
def test_replay_rejects_malformed_top_level_authority_types(
    tmp_path: Path,
    target: str,
    field: str,
    value,
    expected_code: str,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        status_path = mission / "source_intake" / "phase4_source_intake_status.json"
        if target == "status":
            status = _load(status_path)
            status[field] = value
            status_path.write_bytes(pretty_json_bytes(status))
        else:
            _rewrite_outcome_ledger(
                mission,
                lambda ledger: ledger.__setitem__(field, value),
            )
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == expected_code


def test_replay_keeps_cumulative_exhaustion_dominant_over_unsupported_identifier(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(mission_state, "MAX_BYTES_PER_SOURCE", 700)
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(
        mission,
        identifiers=[SEED, "unsupported:fixture"],
    )
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(
                lambda request: _available(request, raw_latex="x" * 2_000)
            ),
        )
        outcomes = validate_mission_source_intake(mission_root=mission, snapshot=snapshot)["outcomes"]
    finally:
        manager.abort()
    assert outcomes[0]["code"] == "byte_budget_exceeded"
    assert outcomes[1]["outcome_status"] == "not_attempted_cap"
    assert outcomes[1]["cap_kind"] == "cumulative_bytes"


def test_replay_rejects_duplicate_semantics_changed_from_available_record(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED, SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        _rewrite_outcome_ledger(
            mission,
            lambda ledger: ledger["outcomes"][1].__setitem__(
                "final_url",
                "https://arxiv.org/abs/9999.99999",
            ),
        )
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "duplicate_source_record_mismatch"


def test_metadata_ledger_symlink_is_rejected_on_replay(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    outside = tmp_path / "moved_candidate_ledger.json"
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        ledger_path = metadata / "candidate_ledger.json"
        ledger_path.rename(outside)
        ledger_path.symlink_to(outside)
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "unsafe_source_intake_path"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("metadata_root", []),
        ("candidate_ledger_sha256", "not-a-digest"),
        ("candidate_ledger_size_bytes", True),
        ("candidate_count", True),
        ("normalized_seed_keys", [1]),
    ],
)
def test_replay_rejects_malformed_generation_metadata_authority(
    tmp_path: Path,
    field: str,
    value,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        authority = _load(mission / "source_intake" / "phase4_source_intake_status.json")[
            "metadata_authority"
        ]
        authority[field] = value
        with pytest.raises(MissionStateError) as error:
            from research_assistant.survey.source_intake import _validate_metadata_authority_types

            _validate_metadata_authority_types(authority)
    finally:
        manager.abort()
    assert error.value.code in {"invalid_metadata_authority", "invalid_source_intake_schema"}


@pytest.mark.parametrize("shape", ["malformed", "noncanonical", "symlink", "nonregular"])
def test_status_residue_shape_is_rejected(tmp_path: Path, shape: str) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    outside = tmp_path / "outside_status.json"
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        status_path = mission / "source_intake" / "phase4_source_intake_status.json"
        status = _load(status_path)
        if shape == "malformed":
            status_path.write_bytes(b"{")
        elif shape == "noncanonical":
            status_path.write_text(json.dumps(status, sort_keys=True))
        elif shape == "symlink":
            outside.write_bytes(status_path.read_bytes())
            status_path.unlink()
            status_path.symlink_to(outside)
        else:
            status_path.unlink()
            status_path.mkdir()
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code in {
        "invalid_source_intake",
        "noncanonical_source_intake",
        "unsafe_source_intake_path",
    }


@pytest.mark.parametrize("root_name", ["source_intake", "records"])
def test_preexisting_symlink_output_root_blocks_before_capability_call(
    tmp_path: Path,
    root_name: str,
) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    outside = tmp_path / f"outside_{root_name}"
    outside.mkdir()
    if root_name == "source_intake":
        target = mission / "source_intake"
    else:
        target = mission / "local_research" / "papers" / "source" / "records"
        target.parent.mkdir(parents=True)
    target.symlink_to(outside, target_is_directory=True)
    called = False

    def handler(request):
        nonlocal called
        called = True
        return _available(request)

    try:
        with pytest.raises(MissionStateError) as error:
            run_mission_source_intake(
                mission_root=mission,
                metadata_root=metadata,
                snapshot=snapshot,
                capability=MissionSourceCapability(handler),
            )
    finally:
        manager.abort()
    assert error.value.code == "unsafe_source_intake_path"
    assert called is False
    assert list(outside.iterdir()) == []


def test_unexpected_intake_child_is_rejected_on_replay(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    manager, snapshot, metadata = _checkpoint_source_authority(mission, identifiers=[SEED])
    try:
        run_mission_source_intake(
            mission_root=mission,
            metadata_root=metadata,
            snapshot=snapshot,
            capability=MissionSourceCapability(_available),
        )
        (mission / "source_intake" / "unexpected.json").write_text("{}")
        with pytest.raises(MissionStateError) as error:
            validate_mission_source_intake(mission_root=mission, snapshot=snapshot)
    finally:
        manager.abort()
    assert error.value.code == "unexpected_source_intake_child"


def test_safe_local_zero_available_stays_at_source_intake_terminal(tmp_path: Path) -> None:
    mission = tmp_path / "mission"
    first = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    _write_metadata(mission, [SEED])
    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
        source_capability=MissionSourceCapability(_unavailable),
    )
    assert result["local_supervisor"]["status"] == "terminal_blocked_source_intake"
    assert result["local_supervisor"]["terminal_reason"] == "source_intake_has_no_available_records"
    assert [row["stage_id"] for row in result["local_supervisor"]["transition_history"]] == [
        "source_intake"
    ]
    assert not (mission / "source_anchors").exists()


def test_confirmed_safe_local_without_capability_is_exact_terminal_and_no_write(
    tmp_path: Path,
) -> None:
    mission = tmp_path / "mission"
    first = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        run_safe_local=True,
    )
    assert first["local_supervisor"]["status"] == "terminal_blocked_public_discovery_confirmation"
    _write_metadata(mission, [SEED])
    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=[SEED],
        output_dir=mission,
        resume=True,
        confirm_public_discovery=True,
        run_safe_local=True,
    )
    assert result["local_supervisor"]["status"] == "terminal_blocked_source_intake"
    assert (
        result["local_supervisor"]["terminal_reason"]
        == "confirmed_external_source_capability_required"
    )
    assert not (mission / "source_intake").exists()
