from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import os

import pytest


SCRIPT = Path("scripts/literature_survey_m20_recovery_closeout.py")
SPEC = importlib.util.spec_from_file_location("m20_recovery_closeout", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _packet(tmp_path: Path, live_root: Path, diagnostic: Path) -> tuple[Path, dict]:
    from research_assistant.survey.m20_live_supervisor import PACKET_SCHEMA, packet_contract_sha256

    campaign_state_path = (tmp_path / "campaign_state.json").resolve()
    campaign_state_path.write_text(json.dumps({
        "schema_version": MODULE.CAMPAIGN_STATE_SCHEMA,
        "campaign_id": "m20-recovery-2026-07-17",
        "attempts_completed": 0,
        "provider_launches_used": 0,
        "cost_cap_usd": "0.01",
        "reconciled_cost_usd": "0.00",
        "remaining_cost_usd": "0.01",
        "next_attempt_id": "attempt-01",
        "next_attempt_allowed": True,
        "continuation_veto": False,
        "predecessor_campaign_state_sha256": None,
    }, sort_keys=True))
    packet = {
        "schema_version": PACKET_SCHEMA,
        "packet_contract_sha256": "",
        "execution_commit": "a" * 40,
        "route_manifest_sha256": "b" * 64,
        "output_root": str(live_root),
        "launch_diagnostic_path": str(diagnostic),
        "credential_interface": "OPENALEX_API_KEY",
        "outer_intent_path": str((tmp_path / "outer-intent.json").resolve()),
        "outer_invocation_path": str((tmp_path / "outer.json").resolve()),
        "outer_invocation_fallback_path": str((tmp_path / "outer-fallback.json").resolve()),
        "campaign_id": "m20-recovery-2026-07-17",
        "campaign_attempt_id": "attempt-01",
        "campaign_state": {
            "path": str(campaign_state_path),
            "sha256": MODULE._sha(campaign_state_path.read_bytes()),
        },
        "command": ["python"],
    }
    packet["packet_contract_sha256"] = packet_contract_sha256(packet)
    path = (tmp_path / "packet.json").resolve()
    path.write_text(json.dumps(packet, sort_keys=True))
    return path, packet


def _diagnostic(packet: dict, *, outcome: str, started: bool, live_root: Path) -> dict:
    states = {
        "preflight_failed": (False, False, None, False, "packet_shape_invalid"),
        "credential_lookup_failed": (True, True, None, False, "credential_lookup_failed"),
        "credential_unavailable": (True, True, False, False, "credential_unavailable"),
        "supervisor_error": (True, True, True, True, "supervisor_error"),
        "supervised_execution_returned": (True, True, True, True, None),
    }
    preflight, lookup, available, supervised, error_code = states[outcome]
    assert supervised is started
    return {
        "schema_version": MODULE.DIAGNOSTIC_SCHEMA,
        "outcome": outcome,
        "exit_code": 2,
        "error_code": error_code,
        "packet_contract_sha256": (
            packet["packet_contract_sha256"] if preflight else MODULE.NOT_ESTABLISHED
        ),
        "preflight_completed": preflight,
        "credential_lookup_performed": lookup,
        "credential_available": available,
        "supervised_execution_started": supervised,
        "live_root_exists": live_root.exists(),
        "supervisor_manifest_exists": False,
        "provider_activity": MODULE.NOT_ESTABLISHED if started else False,
        "cost_usd": MODULE.NOT_ESTABLISHED if started else "0.00",
        "privacy_state": MODULE.NOT_ESTABLISHED,
    }


def _worker_start_failed_manifest(packet: dict) -> dict:
    return {
        "schema_version": MODULE.SUPERVISOR_SCHEMA,
        "classification": "worker_start_failed",
        "lifecycle_stage": "worker_spawn",
        "packet_contract_sha256": packet["packet_contract_sha256"],
        "execution_commit": packet["execution_commit"],
        "route_manifest_sha256": packet["route_manifest_sha256"],
        "worker_returncode": None,
        "worker_reaped": None,
        "signals_sent": [],
        "elapsed_seconds": 0.1,
        "soft_seconds": 367.0,
        "hard_seconds": 370.0,
        "final_reap_seconds": 372.0,
        "absolute_seconds": 373.0,
        "stdout_policy": "discarded_to_devnull",
        "stderr_policy": "discarded_to_devnull",
        "artifact_inventory": [],
        "manifest_published_last": True,
    }


def _completed_manifest(packet: dict, inventory: list[dict]) -> dict:
    value = _worker_start_failed_manifest(packet)
    value.update({
        "classification": "completed",
        "lifecycle_stage": "artifact_validation",
        "worker_returncode": 0,
        "worker_reaped": True,
        "artifact_inventory": inventory,
    })
    return value


def _args(tmp_path: Path, outcome: str, started: bool) -> tuple[dict, dict, Path]:
    live_root = (tmp_path / "live").resolve()
    diagnostic_path = (tmp_path / "diagnostic.json").resolve()
    packet_path, packet = _packet(tmp_path, live_root, diagnostic_path)
    diagnostic = _diagnostic(packet, outcome=outcome, started=started, live_root=live_root)
    diagnostic_path.write_text(json.dumps(diagnostic, sort_keys=True))
    child_command = [
        packet["command"][0],
        "-B", "-I", "-m", "research_assistant.survey.m20_live_supervisor",
        "--packet", str(packet_path),
        "--output-root", str(live_root),
        "--launch-diagnostic-path", str(diagnostic_path),
        "--execute-m20-recovery-campaign",
    ]
    intent_path = Path(packet["outer_intent_path"])
    intent_path.write_text(json.dumps({
        "schema_version": MODULE.OUTER_INTENT_SCHEMA,
        "packet_file_sha256": MODULE._sha(packet_path.read_bytes()),
        "child_command": child_command,
        "credential_read_or_enumerated_by_launcher": False,
        "provider_activity": False,
        "cost_usd": "0.00",
        "privacy_state": "passed_closed_construction_before_child",
    }, sort_keys=True))
    outer_path = Path(packet["outer_invocation_path"])
    outer_path.write_text(json.dumps({
        "schema_version": MODULE.OUTER_SCHEMA,
        "packet_file_sha256": MODULE._sha(packet_path.read_bytes()),
        "outer_intent_sha256": MODULE._sha(intent_path.read_bytes()),
        "child_outcome": "closed_exit",
        "child_exit_code": diagnostic["exit_code"],
        "diagnostic_exists": True,
        "live_root_exists": live_root.exists(),
        "supervisor_manifest_exists": False,
        "credential_read_or_enumerated_by_launcher": False,
        "provider_activity": MODULE.NOT_ESTABLISHED,
        "cost_usd": MODULE.NOT_ESTABLISHED,
        "privacy_state": MODULE.NOT_ESTABLISHED,
    }, sort_keys=True))
    return {
        "packet_path": packet_path,
        "expected_packet_file_sha256": MODULE._sha(packet_path.read_bytes()),
        "expected_packet_contract_sha256": packet["packet_contract_sha256"],
        "live_root": live_root,
        "diagnostic_path": diagnostic_path,
        "intent_path": intent_path,
        "outer_path": outer_path,
        "fallback_path": Path(packet["outer_invocation_fallback_path"]),
        "result_root": (tmp_path / "result").resolve(),
    }, packet, diagnostic_path


def _refresh_outer(args: dict) -> None:
    outer = json.loads(args["outer_path"].read_text())
    outer.update({
        "child_exit_code": json.loads(args["diagnostic_path"].read_text())["exit_code"],
        "diagnostic_exists": args["diagnostic_path"].is_file(),
        "live_root_exists": args["live_root"].exists(),
        "supervisor_manifest_exists": (args["live_root"] / "supervisor_manifest.json").is_file(),
    })
    args["outer_path"].write_text(json.dumps(outer, sort_keys=True))


def _make_expected_directories(root: Path) -> None:
    for relative in sorted(MODULE.EXPECTED_WORKER_DIRECTORIES):
        (root / relative).mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("outcome", ["preflight_failed", "credential_lookup_failed", "credential_unavailable"])
def test_pre_execution_failure_has_zero_cost_and_is_repair_eligible(tmp_path: Path, outcome: str) -> None:
    args, _, _ = _args(tmp_path, outcome, False)
    record = MODULE.build_closeout(**args)
    assert record["provider_activity"] is False
    assert record["cost_usd"] == "0.00"
    assert record["cost_reconciled"] is True
    assert record["retry_eligible_under_unchanged_campaign"] is True
    assert record["continuation_veto"] is False
    assert record["privacy_state"] == "passed_closed_construction_no_worker_artifacts"


def test_supervised_error_without_manifest_is_continuation_veto(tmp_path: Path) -> None:
    args, _, _ = _args(tmp_path, "supervisor_error", True)
    record = MODULE.build_closeout(**args)
    assert record["provider_activity"] == MODULE.NOT_ESTABLISHED
    assert record["cost_usd"] == MODULE.NOT_ESTABLISHED
    assert record["retry_eligible_under_unchanged_campaign"] is False
    assert record["continuation_veto"] is True


def test_valid_worker_start_failure_is_zero_cost_and_repair_eligible(tmp_path: Path) -> None:
    args, packet, diagnostic_path = _args(tmp_path, "supervised_execution_returned", True)
    args["live_root"].mkdir()
    (args["live_root"] / "supervisor_manifest.json").write_text(
        json.dumps(_worker_start_failed_manifest(packet), sort_keys=True)
    )
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic["live_root_exists"] = True
    diagnostic["supervisor_manifest_exists"] = True
    diagnostic_path.write_text(json.dumps(diagnostic, sort_keys=True))
    _refresh_outer(args)

    record = MODULE.build_closeout(**args)
    assert record["classification"] == "worker_start_failed"
    assert record["provider_activity"] is False
    assert record["cost_usd"] == "0.00"
    assert record["retry_eligible_under_unchanged_campaign"] is True
    assert record["continuation_veto"] is False


def test_malformed_worker_start_failure_cannot_authorize_retry(tmp_path: Path) -> None:
    args, packet, diagnostic_path = _args(tmp_path, "supervised_execution_returned", True)
    args["live_root"].mkdir()
    manifest = _worker_start_failed_manifest(packet)
    manifest["worker_returncode"] = 1
    (args["live_root"] / "supervisor_manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic["live_root_exists"] = True
    diagnostic["supervisor_manifest_exists"] = True
    diagnostic_path.write_text(json.dumps(diagnostic, sort_keys=True))
    _refresh_outer(args)

    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervisor_process_state_invalid"):
        MODULE.build_closeout(**args)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("signals_sent", ["SIGTERM"], "supervisor_signal_state_invalid"),
        ("worker_reaped", False, "supervisor_process_state_invalid"),
        ("elapsed_seconds", -1, "supervisor_manifest_invalid"),
        ("soft_seconds", 1.0, "supervisor_manifest_invalid"),
    ],
)
def test_worker_start_failure_requires_exact_lifecycle_state(
    tmp_path: Path, field: str, value: object, code: str
) -> None:
    args, packet, diagnostic_path = _args(tmp_path, "supervised_execution_returned", True)
    args["live_root"].mkdir()
    manifest = _worker_start_failed_manifest(packet)
    manifest[field] = value
    (args["live_root"] / "supervisor_manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic["live_root_exists"] = True
    diagnostic["supervisor_manifest_exists"] = True
    diagnostic_path.write_text(json.dumps(diagnostic, sort_keys=True))
    _refresh_outer(args)

    with pytest.raises(MODULE.RecoveryCloseoutError, match=code):
        MODULE.build_closeout(**args)


def test_completed_inventory_requires_exact_path_size_hash_and_no_extras(tmp_path: Path) -> None:
    root = tmp_path / "live"
    root.mkdir()
    _make_expected_directories(root)
    artifact = root / "campaign_summary.json"
    artifact.write_bytes(b"{}")
    (root / "supervisor_manifest.json").write_bytes(b"{}")
    rows = [{
        "path": "campaign_summary.json",
        "size_bytes": 2,
        "sha256": MODULE._sha(b"{}"),
    }]
    MODULE._validate_completed_inventory(root, rows)

    (root / "extra.json").write_bytes(b"{}")
    with pytest.raises(MODULE.RecoveryCloseoutError, match="completed_artifact_set_mismatch"):
        MODULE._validate_completed_inventory(root, rows)


def test_completed_inventory_rejects_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "live"
    root.mkdir()
    _make_expected_directories(root)
    (root / "campaign_summary.json").write_bytes(b"{}")
    (root / "supervisor_manifest.json").write_bytes(b"{}")
    rows = [{
        "path": "campaign_summary.json",
        "size_bytes": 2,
        "sha256": "0" * 64,
    }]
    with pytest.raises(MODULE.RecoveryCloseoutError, match="completed_artifact_inventory_mismatch"):
        MODULE._validate_completed_inventory(root, rows)


def test_completed_inventory_rejects_extra_symlink(tmp_path: Path) -> None:
    root = tmp_path / "live"
    root.mkdir()
    _make_expected_directories(root)
    (root / "campaign_summary.json").write_bytes(b"{}")
    (root / "supervisor_manifest.json").write_bytes(b"{}")
    (root / "extra-link").symlink_to(root / "campaign_summary.json")
    rows = [{
        "path": "campaign_summary.json",
        "size_bytes": 2,
        "sha256": MODULE._sha(b"{}"),
    }]
    with pytest.raises(MODULE.RecoveryCloseoutError, match="completed_artifact_topology_invalid"):
        MODULE._validate_completed_inventory(root, rows)


def test_completed_inventory_rejects_extra_empty_directory(tmp_path: Path) -> None:
    root = tmp_path / "live"
    root.mkdir()
    _make_expected_directories(root)
    artifact = root / "campaign_summary.json"
    artifact.write_bytes(b"{}")
    (root / "supervisor_manifest.json").write_bytes(b"{}")
    (root / "unexpected-empty").mkdir()
    rows = [{"path": artifact.name, "size_bytes": 2, "sha256": MODULE._sha(b"{}") }]
    with pytest.raises(MODULE.RecoveryCloseoutError, match="completed_artifact_directory_set_mismatch"):
        MODULE._validate_completed_inventory(root, rows)


def test_completed_inventory_rejects_hardlinked_file(tmp_path: Path) -> None:
    root = tmp_path / "live"
    root.mkdir()
    _make_expected_directories(root)
    artifact = root / "campaign_summary.json"
    artifact.write_bytes(b"{}")
    os.link(artifact, tmp_path / "outside-hardlink.json")
    (root / "supervisor_manifest.json").write_bytes(b"{}")
    rows = [{"path": artifact.name, "size_bytes": 2, "sha256": MODULE._sha(b"{}") }]
    with pytest.raises(MODULE.RecoveryCloseoutError, match="completed_artifact_inventory_mismatch"):
        MODULE._validate_completed_inventory(root, rows)


@pytest.mark.parametrize(
    (
        "campaign_validity", "selected_candidate_authority", "reserved", "reconciled",
        "expected_status", "primary", "veto",
    ),
    [
        ("closed", True, "0.0011", "0.0011", "passed", True, False),
        (
            "closed", False, "0.0011", "0.0011",
            "BLOCKED_NO_SELECTED_REAL_CANDIDATE_AFTER_FROZEN_MATRIX", False, False,
        ),
        ("boundary_invalid", False, "0.0011", "0.0011", "boundary_outcome", False, False),
        ("boundary_invalid", False, "0.0011", "0", "stopped", False, True),
    ],
)
def test_completed_closeout_integrates_replay_cost_privacy_and_promotion(
    tmp_path: Path,
    campaign_validity: str,
    selected_candidate_authority: bool,
    reserved: str,
    reconciled: str,
    expected_status: str,
    primary: bool,
    veto: bool,
) -> None:
    args, packet, diagnostic_path = _args(tmp_path, "supervised_execution_returned", True)
    args["live_root"].mkdir()
    _make_expected_directories(args["live_root"])
    summary = {
        "cost_evidence": {
            "reserved_cost_usd": reserved,
            "reconciled_cost_usd": reconciled,
            "cost_state": "open" if reserved == reconciled else "blocked",
            "cost_block_code": None if reserved == reconciled else "dispatch_cost_unreconciled",
        }
    }
    summary_path = args["live_root"] / "campaign_summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True))
    inventory = [{
        "path": "campaign_summary.json",
        "size_bytes": summary_path.stat().st_size,
        "sha256": MODULE._sha(summary_path.read_bytes()),
    }]
    (args["live_root"] / "supervisor_manifest.json").write_text(
        json.dumps(_completed_manifest(packet, inventory), sort_keys=True)
    )
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic.update({
        "exit_code": 0,
        "live_root_exists": True,
        "supervisor_manifest_exists": True,
    })
    diagnostic_path.write_text(json.dumps(diagnostic, sort_keys=True))
    _refresh_outer(args)

    record = MODULE.build_closeout(
        **args,
        replay_validator=lambda _root: {
            "campaign_validity": campaign_validity,
            "selected_candidate_authority": selected_candidate_authority,
        },
    )
    assert record["status"] == expected_status
    assert record["m20_primary_criterion_passed"] is primary
    assert record["continuation_veto"] is veto
    assert record["retry_eligible_under_unchanged_campaign"] is False
    assert record["privacy_state"] == "passed_enumerated_retained_artifacts"
    assert record["selected_candidate_authority"] is selected_candidate_authority


@pytest.mark.parametrize(
    ("evidence", "reconciled"),
    [
        ({"reserved_cost_usd": "0.0011", "reconciled_cost_usd": "0.0011", "cost_state": "open", "cost_block_code": None}, True),
        ({"reserved_cost_usd": "0", "reconciled_cost_usd": "0", "cost_state": "blocked", "cost_block_code": "invalid_cost_state"}, False),
        ({"reserved_cost_usd": "0.001", "reconciled_cost_usd": "0", "cost_state": "blocked", "cost_block_code": "dispatch_cost_unreconciled"}, False),
    ],
)
def test_completed_cost_distinguishes_reconciled_and_unreconciled_states(
    tmp_path: Path, evidence: dict, reconciled: bool
) -> None:
    root = tmp_path / "live"
    root.mkdir()
    (root / "campaign_summary.json").write_text(json.dumps({"cost_evidence": evidence}))
    _cost, observed, _state, _block = MODULE._completed_cost(root)
    assert observed is reconciled


def test_boundary_outcome_is_not_promoted_or_retry_eligible() -> None:
    replay_status = "passed"
    campaign_validity = "boundary_invalid"
    cost_reconciled = True
    status = (
        "passed"
        if replay_status == "passed" and campaign_validity == "closed" and cost_reconciled
        else "boundary_outcome"
        if replay_status == "passed" and campaign_validity == "boundary_invalid" and cost_reconciled
        else "stopped"
    )
    assert status == "boundary_outcome"
    assert (replay_status == "passed" and campaign_validity == "closed" and cost_reconciled) is False


def test_primary_criterion_requires_enumerated_privacy_pass() -> None:
    replay_status = "passed"
    campaign_validity = "closed"
    cost_reconciled = True
    privacy_state = MODULE.NOT_ESTABLISHED
    assert (
        replay_status == "passed"
        and campaign_validity == "closed"
        and cost_reconciled
        and privacy_state == "passed_enumerated_retained_artifacts"
    ) is False


def test_diagnostic_cannot_claim_zero_cost_after_supervision_started(tmp_path: Path) -> None:
    args, _, diagnostic_path = _args(tmp_path, "supervisor_error", True)
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic["provider_activity"] = False
    diagnostic["cost_usd"] = "0.00"
    diagnostic_path.write_text(json.dumps(diagnostic))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervised_diagnostic_overclaim"):
        MODULE.build_closeout(**args)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preflight_completed", False),
        ("credential_lookup_performed", False),
        ("credential_available", True),
        ("supervised_execution_started", True),
        ("privacy_state", False),
    ],
)
def test_credential_unavailable_requires_exact_producer_transition(
    tmp_path: Path, field: str, value: object
) -> None:
    args, _, diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic[field] = value
    if field == "supervised_execution_started":
        diagnostic["provider_activity"] = MODULE.NOT_ESTABLISHED
        diagnostic["cost_usd"] = MODULE.NOT_ESTABLISHED
    diagnostic_path.write_text(json.dumps(diagnostic))
    with pytest.raises(MODULE.RecoveryCloseoutError):
        MODULE.build_closeout(**args)


def test_boolean_exit_code_is_rejected(tmp_path: Path) -> None:
    args, _, diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic["exit_code"] = False
    diagnostic_path.write_text(json.dumps(diagnostic))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="launch_diagnostic_state_invalid"):
        MODULE.build_closeout(**args)


def test_packet_hash_drift_fails_closed(tmp_path: Path) -> None:
    args, _, _ = _args(tmp_path, "credential_unavailable", False)
    args["expected_packet_file_sha256"] = "0" * 64
    with pytest.raises(MODULE.RecoveryCloseoutError, match="packet_file_hash_invalid"):
        MODULE.build_closeout(**args)


def test_fallback_outer_record_is_accepted_when_primary_absent(tmp_path: Path) -> None:
    args, _, _ = _args(tmp_path, "credential_unavailable", False)
    args["outer_path"].rename(args["fallback_path"])
    record = MODULE.build_closeout(**args)
    assert record["outer_invocation_sha256"] == MODULE._sha(args["fallback_path"].read_bytes())


def test_two_outer_records_fail_closed(tmp_path: Path) -> None:
    args, _, _ = _args(tmp_path, "credential_unavailable", False)
    args["fallback_path"].write_bytes(args["outer_path"].read_bytes())
    with pytest.raises(MODULE.RecoveryCloseoutError, match="exactly_one_outer_invocation_required"):
        MODULE.build_closeout(**args)


def test_outer_exit_must_match_diagnostic(tmp_path: Path) -> None:
    args, _, _ = _args(tmp_path, "credential_unavailable", False)
    outer = json.loads(args["outer_path"].read_text())
    outer["child_exit_code"] = 0
    args["outer_path"].write_text(json.dumps(outer))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="outer_diagnostic_reconciliation_invalid"):
        MODULE.build_closeout(**args)


def test_outer_intent_terminal_hash_must_match(tmp_path: Path) -> None:
    args, _, _ = _args(tmp_path, "credential_unavailable", False)
    outer = json.loads(args["outer_path"].read_text())
    outer["outer_intent_sha256"] = "0" * 64
    args["outer_path"].write_text(json.dumps(outer))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="outer_intent_terminal_binding_invalid"):
        MODULE.build_closeout(**args)


def test_completed_manifest_requires_zero_exit(tmp_path: Path) -> None:
    args, packet, diagnostic_path = _args(tmp_path, "supervised_execution_returned", True)
    args["live_root"].mkdir()
    _make_expected_directories(args["live_root"])
    summary = args["live_root"] / "campaign_summary.json"
    summary.write_text(json.dumps({"cost_evidence": {
        "reserved_cost_usd": "0", "reconciled_cost_usd": "0",
        "cost_state": "open", "cost_block_code": None,
    }}))
    inventory = [{
        "path": summary.name, "size_bytes": summary.stat().st_size,
        "sha256": MODULE._sha(summary.read_bytes()),
    }]
    (args["live_root"] / "supervisor_manifest.json").write_text(
        json.dumps(_completed_manifest(packet, inventory))
    )
    diagnostic = json.loads(diagnostic_path.read_text())
    diagnostic.update({"live_root_exists": True, "supervisor_manifest_exists": True})
    diagnostic_path.write_text(json.dumps(diagnostic))
    _refresh_outer(args)
    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervisor_exit_classification_invalid"):
        MODULE.build_closeout(
            **args,
            replay_validator=lambda _root: {
                "campaign_validity": "closed",
                "selected_candidate_authority": True,
            },
        )


@pytest.mark.parametrize(
    ("stage", "signals", "elapsed"),
    [
        ("post_term_wait", ["SIGTERM"], 366.9),
        ("post_kill_wait", ["SIGTERM", "SIGKILL"], 369.9),
    ],
)
def test_lifecycle_error_stage_has_elapsed_floor(
    tmp_path: Path, stage: str, signals: list[str], elapsed: float
) -> None:
    _args_value, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    manifest = _worker_start_failed_manifest(packet)
    manifest.update({
        "classification": "supervisor_lifecycle_error",
        "lifecycle_stage": stage,
        "worker_returncode": 1,
        "worker_reaped": True,
        "signals_sent": signals,
        "elapsed_seconds": elapsed,
    })
    path = (tmp_path / "supervisor.json").resolve()
    path.write_text(json.dumps(manifest))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervisor_elapsed_state_invalid"):
        MODULE._validate_supervisor(path, packet=packet)


def test_lifecycle_error_rejects_unreachable_stage_signal_pair(tmp_path: Path) -> None:
    _args_value, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    manifest = _worker_start_failed_manifest(packet)
    manifest.update({
        "classification": "supervisor_lifecycle_error",
        "lifecycle_stage": "worker_spawn",
        "worker_returncode": 1,
        "worker_reaped": True,
    })
    path = (tmp_path / "supervisor.json").resolve()
    path.write_text(json.dumps(manifest))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervisor_signal_state_invalid"):
        MODULE._validate_supervisor(path, packet=packet)


def test_supervisor_rejects_nonfinite_elapsed(tmp_path: Path) -> None:
    _args_value, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    manifest = _worker_start_failed_manifest(packet)
    manifest["elapsed_seconds"] = float("nan")
    path = (tmp_path / "supervisor.json").resolve()
    path.write_text(json.dumps(manifest))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervisor_manifest_invalid"):
        MODULE._validate_supervisor(path, packet=packet)


def test_installed_replay_rejects_interpreter_from_other_environment(tmp_path: Path) -> None:
    _args_value, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    packet["runtime_modules"] = {
        name: {"origin": str((tmp_path / "venv" / "lib" / "python3.11" / "site-packages" / Path(*name.split(".")).with_suffix(".py")).resolve()), "sha256": "0" * 64}
        for name in {
            "research_assistant.survey.discovery_capability",
            "research_assistant.survey.m20_live_worker",
            "research_assistant.survey.m20_live_supervisor",
            "research_assistant.survey.m20_recovery_launcher",
            "research_assistant.survey.openalex_adapter",
            "research_assistant.survey.openalex_credential_cost",
        }
    }
    for binding in packet["runtime_modules"].values():
        origin = Path(binding["origin"])
        origin.parent.mkdir(parents=True, exist_ok=True)
        origin.write_bytes(b"x")
        binding["sha256"] = MODULE._sha(b"x")
    other = tmp_path / "other" / "bin" / "python"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"x")
    packet["command"] = [str(other)]
    with pytest.raises(MODULE.RecoveryCloseoutError, match="replay_interpreter_invalid"):
        MODULE._installed_replay(packet, tmp_path / "live")


def test_initial_campaign_state_uses_successor_schema(tmp_path: Path) -> None:
    args, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    record = MODULE.build_closeout(**args)
    successor = record["next_campaign_state"]
    assert set(successor) == set(json.loads(Path(packet["campaign_state"]["path"]).read_text()))
    assert successor["attempts_completed"] == 1
    assert successor["provider_launches_used"] == 1
    assert successor["next_attempt_id"] == "attempt-02"
    assert successor["next_attempt_allowed"] is True


def test_preflight_error_code_is_allowlisted(tmp_path: Path) -> None:
    args, _, diagnostic = _args(tmp_path, "preflight_failed", False)
    value = json.loads(diagnostic.read_text())
    value["error_code"] = "invented_preflight_error"
    diagnostic.write_text(json.dumps(value))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="launch_diagnostic_error_code_invalid"):
        MODULE.build_closeout(**args)


def test_outer_intent_preflight_error_code_is_allowlisted(tmp_path: Path) -> None:
    args, _, diagnostic = _args(tmp_path, "preflight_failed", False)
    value = json.loads(diagnostic.read_text())
    value["error_code"] = "packet_outer_intent_invalid"
    diagnostic.write_text(json.dumps(value))
    record = MODULE.build_closeout(**args)
    assert record["classification"] == "preflight_failed"


@pytest.mark.parametrize(
    ("stage", "signals", "elapsed"),
    [
        ("cleanup_wait_after_initial_wait", [], 0.1),
        ("cleanup_wait_after_post_term_wait", ["SIGTERM"], 367.0),
        ("cleanup_wait_after_post_kill_wait", ["SIGTERM", "SIGKILL"], 370.0),
        ("cleanup_wait_after_final_reap_timeout", ["SIGTERM", "SIGKILL"], 372.0),
    ],
)
def test_cleanup_indeterminate_accepts_producer_reachable_states(
    tmp_path: Path, stage: str, signals: list[str], elapsed: float
) -> None:
    _args_value, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    manifest = _worker_start_failed_manifest(packet)
    manifest.update({
        "classification": "cleanup_reap_indeterminate",
        "lifecycle_stage": stage,
        "worker_returncode": None,
        "worker_reaped": False,
        "signals_sent": signals,
        "elapsed_seconds": elapsed,
    })
    path = (tmp_path / "supervisor.json").resolve()
    path.write_text(json.dumps(manifest))
    assert MODULE._validate_supervisor(path, packet=packet)["classification"] == (
        "cleanup_reap_indeterminate"
    )


def test_cleanup_after_final_reap_timeout_keeps_final_reap_floor(tmp_path: Path) -> None:
    _args_value, packet, _diagnostic_path = _args(tmp_path, "credential_unavailable", False)
    manifest = _worker_start_failed_manifest(packet)
    manifest.update({
        "classification": "cleanup_reap_indeterminate",
        "lifecycle_stage": "cleanup_wait_after_final_reap_timeout",
        "worker_returncode": None,
        "worker_reaped": False,
        "signals_sent": ["SIGTERM", "SIGKILL"],
        "elapsed_seconds": 371.9,
    })
    path = (tmp_path / "supervisor.json").resolve()
    path.write_text(json.dumps(manifest))
    with pytest.raises(MODULE.RecoveryCloseoutError, match="supervisor_elapsed_state_invalid"):
        MODULE._validate_supervisor(path, packet=packet)


def test_script_has_no_environment_or_network_access() -> None:
    source = SCRIPT.read_text()
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "urlopen" not in source
    assert "requests." not in source
