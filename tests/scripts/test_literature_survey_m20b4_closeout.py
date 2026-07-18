from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20b4_closeout.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20b4_closeout", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _packet(tmp_path: Path, live_root: Path) -> tuple[Path, dict]:
    packet_path = tmp_path / "packet.json"
    packet = {
        "command": ["/installed/python", "-I", "-m", "supervisor"],
        "credential_interface": "OPENALEX_API_KEY",
        "execution_commit": "a" * 40,
        "execution_tree": "b" * 40,
        "network_scope": ["api.openalex.org:443", "export.arxiv.org:443"],
        "nonclaims": ["provider_reliability", "m20_or_north_star_completion"],
        "output_root": str(live_root),
        "packet_contract_sha256": "c" * 64,
        "route_manifest_sha256": "d" * 64,
    }
    packet_path.write_text(json.dumps(packet, sort_keys=True))
    return packet_path, packet


def _args(tmp_path: Path, live_root: Path, result_root: Path) -> dict:
    packet_path, _packet_value = _packet(tmp_path, live_root)
    return {
        "packet_path": packet_path,
        "live_root": live_root,
        "result_root": result_root,
        "launch_started_at": "2026-07-15T10:00:00+00:00",
        "launch_ended_at": "2026-07-15T10:00:03+00:00",
        "exit_code": 2,
        "outcome_indeterminate": False,
        "plan_file": tmp_path / "plan.md",
        "terminal_result_file": tmp_path / "result.md",
    }


def _packet_validator(path: Path, _live: Path) -> tuple[dict, str]:
    return MODULE._loads_closed(path.read_bytes()), MODULE._sha(path.read_bytes())


def _supervisor(packet: dict, *, classification: str, inventory: list[dict] | None = None) -> dict:
    if classification == "completed":
        returncode, reaped = 0, True
    elif classification == "worker_start_failed":
        returncode, reaped = None, None
    else:
        returncode, reaped = 2, True
    return {
        "schema_version": MODULE.SUPERVISOR_SCHEMA,
        "classification": classification,
        "packet_contract_sha256": packet["packet_contract_sha256"],
        "execution_commit": packet["execution_commit"],
        "route_manifest_sha256": packet["route_manifest_sha256"],
        "worker_returncode": returncode,
        "worker_reaped": reaped,
        "signals_sent": [],
        "elapsed_seconds": 1.0,
        "soft_seconds": 367.0,
        "hard_seconds": 370.0,
        "final_reap_seconds": 372.0,
        "absolute_seconds": 373.0,
        "stdout_policy": "discarded_to_devnull",
        "stderr_policy": "discarded_to_devnull",
        "artifact_inventory": inventory or [],
        "manifest_published_last": True,
    }


def test_early_exit_writes_five_closed_not_established_artifacts(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    result_root = tmp_path / "result"
    artifacts = MODULE.build_closeout(
        **_args(tmp_path, live_root, result_root), packet_validator=_packet_validator
    )
    assert artifacts["attempt_invocation_record.json"]["status"] == "early_supervisor_exit_no_manifest"
    assert artifacts["attempt_invocation_record.json"]["attempt_consumed"] is True
    assert artifacts["offline_replay.json"]["status"] == "not_established"
    assert artifacts["cross_artifact_reconciliation.json"]["artifact_inventory"] == "not_established"
    assert artifacts["credential_surface_scan_result.json"]["worker_artifact_persisted_match_count"] == "not_established"
    assert sorted(path.name for path in result_root.iterdir()) == sorted(artifacts)


def test_manifest_noncompleted_preserves_only_closed_supervisor_fields(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(packet, classification="worker_failed")
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    assert artifacts["attempt_invocation_record.json"]["status"] == "manifest_noncompleted"
    reconciliation = artifacts["cross_artifact_reconciliation.json"]
    assert reconciliation["status"] == "closed_supervisor_only"
    assert reconciliation["supervisor_classification"] == "worker_failed"
    assert reconciliation["artifact_inventory_match"] == "not_established"
    assert artifacts["credential_surface_scan_result.json"]["status"] == "not_established"
    assert artifacts["credential_surface_scan_result.json"]["credential_value_or_digest_persisted"] == "not_established"
    assert artifacts["credential_surface_scan_result.json"]["supervisor_manifest_secret_free_by_closed_construction"] is True


def test_completed_branch_reconciles_inventory_replay_and_scan(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    body = live_root / "campaign_summary.json"
    body.write_bytes(b"{}")
    args = _args(tmp_path, live_root, tmp_path / "result")
    args["exit_code"] = 0
    _, packet = _packet(tmp_path, live_root)
    inventory = [{"path": body.name, "size_bytes": 2, "sha256": MODULE._sha(b"{}") }]
    supervisor = _supervisor(packet, classification="completed", inventory=inventory)
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(
        **args,
        replay_validator=lambda _root: {"status": "passed", "accepted_body_count": 0},
        packet_validator=_packet_validator,
    )
    assert artifacts["offline_replay.json"]["status"] == "passed"
    assert artifacts["cross_artifact_reconciliation.json"]["artifact_inventory_match"] is True
    scan = artifacts["credential_surface_scan_result.json"]
    assert scan["status"] == "established_zero_matches"
    assert scan["worker_artifact_persisted_match_count"] == 0
    assert scan["credential_value_or_digest_persisted"] is False
    assert scan["supervisor_manifest_secret_free_by_closed_construction"] is True


def test_existing_live_root_without_manifest_is_indeterminate(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    artifacts = MODULE.build_closeout(
        **_args(tmp_path, live_root, tmp_path / "result"), packet_validator=_packet_validator
    )
    assert artifacts["attempt_invocation_record.json"]["status"] == "invocation_outcome_indeterminate"
    assert artifacts["offline_replay.json"]["status"] == "not_established"


def test_indeterminate_tool_outcome_is_consumed_and_not_established(tmp_path: Path) -> None:
    args = _args(tmp_path, tmp_path / "live", tmp_path / "result")
    args["exit_code"] = None
    args["outcome_indeterminate"] = True
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    attempt = artifacts["attempt_invocation_record.json"]
    assert attempt["status"] == "invocation_outcome_indeterminate"
    assert attempt["exit_code"] == "not_established"
    assert attempt["retry_or_rerun_authority"] is False


@pytest.mark.parametrize("classification", ["completed", "worker_failed"])
def test_indeterminate_tool_outcome_takes_precedence_over_valid_manifest(
    tmp_path: Path, classification: str
) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    args["exit_code"] = None
    args["outcome_indeterminate"] = True
    _, packet = _packet(tmp_path, live_root)
    inventory = None
    if classification == "completed":
        body = live_root / "campaign_summary.json"
        body.write_bytes(b"{}")
        inventory = [{"path": body.name, "size_bytes": 2, "sha256": MODULE._sha(b"{}")}]
    (live_root / "supervisor_manifest.json").write_text(
        json.dumps(_supervisor(packet, classification=classification, inventory=inventory))
    )
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    assert artifacts["attempt_invocation_record.json"]["status"] == "invocation_outcome_indeterminate"
    assert artifacts["offline_replay.json"]["status"] == "not_established"
    assert artifacts["credential_surface_scan_result.json"]["credential_value_or_digest_persisted"] == "not_established"


def test_completed_artifact_drift_still_writes_fail_closed_set(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    body = live_root / "campaign_summary.json"
    body.write_bytes(b"changed")
    args = _args(tmp_path, live_root, tmp_path / "result")
    args["exit_code"] = 0
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(
        packet,
        classification="completed",
        inventory=[{"path": body.name, "size_bytes": 2, "sha256": MODULE._sha(b"{}")}],
    )
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(
        **args, replay_validator=lambda _root: {"status": "passed"}, packet_validator=_packet_validator
    )
    assert artifacts["attempt_invocation_record.json"]["status"] == "completed"
    assert artifacts["offline_replay.json"]["status"] == "failed_closed"
    assert artifacts["cross_artifact_reconciliation.json"]["status"] == "failed_closed"
    scan = artifacts["credential_surface_scan_result.json"]
    assert scan["credential_value_or_digest_persisted"] == "not_established"
    assert scan["supervisor_manifest_secret_free_by_closed_construction"] == "not_established"


@pytest.mark.parametrize(
    "inventory",
    [
        [{"path": "campaign_summary.json", "size_bytes": 2, "sha256": "secret-bearing-field"}],
        [{"path": "secret-bearing-path", "size_bytes": 2, "sha256": "0" * 64}],
        [{"path": "campaign_summary.json", "size_bytes": "2", "sha256": "0" * 64}],
        [
            {"path": "campaign_summary.json", "size_bytes": 2, "sha256": "0" * 64},
            {"path": "campaign_summary.json", "size_bytes": 2, "sha256": "0" * 64},
        ],
    ],
)
def test_invalid_completed_inventory_cannot_create_affirmative_privacy_claim(
    tmp_path: Path, inventory: list[dict]
) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    args["exit_code"] = 0
    _, packet = _packet(tmp_path, live_root)
    (live_root / "supervisor_manifest.json").write_text(
        json.dumps(_supervisor(packet, classification="completed", inventory=inventory))
    )
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    assert artifacts["attempt_invocation_record.json"]["status"] == "invocation_outcome_indeterminate"
    scan = artifacts["credential_surface_scan_result.json"]
    assert scan["credential_value_or_digest_persisted"] == "not_established"
    assert scan["supervisor_manifest_secret_free_by_closed_construction"] == "not_established"


@pytest.mark.parametrize(
    ("classification", "signals"),
    [
        ("soft_timeout", []),
        ("soft_timeout", ["SIGTERM"]),
        ("hard_timeout", []),
        ("hard_timeout", ["SIGTERM"]),
        ("hard_timeout", ["SIGKILL"]),
        ("hard_timeout", ["SIGTERM", "SIGKILL"]),
        ("final_reap_timeout", ["SIGTERM", "SIGKILL"]),
        ("final_reap_timeout", ["SIGTERM", "SIGKILL", "SIGKILL"]),
        ("cleanup_reap_indeterminate", ["SIGTERM", "SIGKILL"]),
        ("cleanup_reap_indeterminate", ["SIGTERM", "SIGKILL", "SIGKILL"]),
    ],
)
def test_timeout_signal_race_states_match_reachable_supervisor_records(
    tmp_path: Path, classification: str, signals: list[str]
) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(packet, classification=classification)
    if classification == "cleanup_reap_indeterminate":
        supervisor["worker_returncode"] = None
        supervisor["worker_reaped"] = False
    supervisor["signals_sent"] = signals
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    assert artifacts["attempt_invocation_record.json"]["status"] == "manifest_noncompleted"
    assert artifacts["attempt_invocation_record.json"]["supervisor_manifest_validation"] == "passed"


@pytest.mark.parametrize("signals", [[], ["SIGKILL"]])
def test_supervisor_lifecycle_error_accepts_only_reachable_cleanup_signal_states(
    tmp_path: Path, signals: list[str]
) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(packet, classification="supervisor_lifecycle_error")
    supervisor["signals_sent"] = signals
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    assert artifacts["attempt_invocation_record.json"]["status"] == "manifest_noncompleted"
    assert artifacts["attempt_invocation_record.json"]["supervisor_manifest_validation"] == "passed"


@pytest.mark.parametrize(
    "signals",
    [
        ["SIGTERM"],
        ["SIGTERM", "SIGKILL"],
        ["SIGKILL", "SIGKILL"],
        ["SIGTERM", "SIGKILL", "SIGKILL"],
    ],
)
def test_supervisor_lifecycle_error_rejects_unreachable_signal_histories(
    tmp_path: Path, signals: list[str]
) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(packet, classification="supervisor_lifecycle_error")
    supervisor["signals_sent"] = signals
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    attempt = artifacts["attempt_invocation_record.json"]
    assert attempt["status"] == "invocation_outcome_indeterminate"
    assert attempt["supervisor_manifest_validation"] == "failed_closed"
    scan = artifacts["credential_surface_scan_result.json"]
    assert scan["credential_value_or_digest_persisted"] == "not_established"
    assert scan["supervisor_manifest_secret_free_by_closed_construction"] == "not_established"


def test_unreachable_hard_timeout_third_signal_fails_closed(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(packet, classification="hard_timeout")
    supervisor["signals_sent"] = ["SIGTERM", "SIGKILL", "SIGKILL"]
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    assert artifacts["attempt_invocation_record.json"]["status"] == "invocation_outcome_indeterminate"
    assert artifacts["attempt_invocation_record.json"]["supervisor_manifest_validation"] == "failed_closed"


@pytest.mark.parametrize("defect", ["unknown_classification", "bad_signal", "bad_time", "bad_reap"])
def test_invalid_supervisor_state_fails_closed_without_affirmative_privacy_claim(
    tmp_path: Path, defect: str
) -> None:
    live_root = tmp_path / "live"
    live_root.mkdir()
    args = _args(tmp_path, live_root, tmp_path / "result")
    _, packet = _packet(tmp_path, live_root)
    supervisor = _supervisor(packet, classification="worker_failed")
    if defect == "unknown_classification":
        supervisor["classification"] = "invented_success"
    elif defect == "bad_signal":
        supervisor["signals_sent"] = ["SIGUSR1"]
    elif defect == "bad_time":
        supervisor["soft_seconds"] = 1.0
    else:
        supervisor["worker_reaped"] = False
    (live_root / "supervisor_manifest.json").write_text(json.dumps(supervisor))
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    attempt = artifacts["attempt_invocation_record.json"]
    assert attempt["status"] == "invocation_outcome_indeterminate"
    assert attempt["supervisor_manifest_validation"] == "failed_closed"
    assert attempt["exit_manifest_consistent"] == "not_established"
    scan = artifacts["credential_surface_scan_result.json"]
    assert scan["credential_value_or_digest_persisted"] == "not_established"
    assert scan["supervisor_manifest_secret_free_by_closed_construction"] == "not_established"


def test_real_packet_contract_validates_without_live_root_write() -> None:
    packet = Path(
        "docs/validation/literature_survey_m20b3_identified_integration_2026-07-15/"
        "m20b4_live_packet.json"
    ).resolve()
    live_root = Path(
        "/home/chakwong/research-assistant/docs/validation/"
        "literature_survey_m20b4_live_2026-07-15"
    )
    assert not live_root.exists()
    value, digest = MODULE._validate_packet(packet, live_root)
    assert digest == "c3e250b05e2d11ac7c0281aeaa00b467a3b9e7eb90ee1da68d729dfdbfad77ce"
    assert value["packet_contract_sha256"] == "475b15f8e3af79447608616232984744cedca53da59a90642754c5644213dfda"
    assert not live_root.exists()


def test_self_consistent_packet_tamper_is_rejected_by_frozen_file_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = MODULE.FROZEN_PACKET_PATH
    packet = MODULE._loads_closed(source.read_bytes())
    packet["nonclaims"].append("self_consistent_tamper")
    from research_assistant.survey.m20_live_supervisor import packet_contract_sha256

    packet["packet_contract_sha256"] = packet_contract_sha256(packet)
    tampered = tmp_path / "packet.json"
    tampered.write_text(json.dumps(packet, sort_keys=True))
    monkeypatch.setattr(MODULE, "FROZEN_PACKET_PATH", tampered)
    with pytest.raises(MODULE.CloseoutError, match="frozen_packet_file_hash_invalid"):
        MODULE._validate_packet(tampered, MODULE.FROZEN_LIVE_ROOT)


def test_run_manifest_uses_actual_utc_launch_date(tmp_path: Path) -> None:
    args = _args(tmp_path, tmp_path / "live", tmp_path / "result")
    args["launch_started_at"] = "2026-07-16T00:30:00+08:00"
    args["launch_ended_at"] = "2026-07-16T00:30:03+08:00"
    artifacts = MODULE.build_closeout(**args, packet_validator=_packet_validator)
    manifest = artifacts["run_manifest.json"]
    assert manifest["data_version"] == "metadata_provider_query_date_2026-07-15"
    assert manifest["packet_freeze_date"] == "2026-07-15"


def test_script_has_no_environment_network_or_live_root_write_surface() -> None:
    source = SCRIPT.read_text()
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "urlopen" not in source
    assert "requests." not in source
    assert "contains_credential_representation" not in source
    assert "write_bytes" not in source[source.index("def build_closeout"):source.index("def main")]
