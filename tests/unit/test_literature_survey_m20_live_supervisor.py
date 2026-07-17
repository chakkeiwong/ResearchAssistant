from __future__ import annotations

import hashlib
import importlib.util
import json
import secrets
import signal
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from research_assistant.survey import m20_live_supervisor as supervisor
from research_assistant.survey.m20_live_worker import route_manifest, route_manifest_sha256, run_matrix
from research_assistant.survey.mission_state import canonical_json_bytes

from test_literature_survey_m20_live_worker import ARXIV_SEED, OPENALEX_ID, _atom, _list, _work


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_modules() -> dict:
    result = {}
    for name in (
        "research_assistant.survey.discovery_capability",
        "research_assistant.survey.m20_live_supervisor",
        "research_assistant.survey.m20_live_worker",
        "research_assistant.survey.m20_recovery_launcher",
        "research_assistant.survey.openalex_adapter",
        "research_assistant.survey.openalex_credential_cost",
    ):
        spec = importlib.util.find_spec(name)
        assert spec is not None and spec.origin is not None
        origin = Path(spec.origin).resolve()
        result[name] = {"origin": str(origin), "sha256": _sha(origin)}
    return result


def _packet(tmp_path: Path, output_root: Path) -> tuple[Path, dict]:
    wheel = tmp_path / "research_assistant.whl"
    runtime_modules = _runtime_modules()
    install_root = Path("src").resolve()
    member_rows = []
    with zipfile.ZipFile(wheel, "w") as archive:
        for module in runtime_modules.values():
            origin = Path(module["origin"])
            relative = origin.relative_to(install_root).as_posix()
            raw = origin.read_bytes()
            archive.writestr(relative, raw)
            member_rows.append({
                "wheel_path": relative,
                "installed_path": str(origin),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
    members = tmp_path / "installed_members.json"
    members.write_bytes(canonical_json_bytes({
        "schema_version": "ra-literature-survey-m20b3-installed-member-manifest-v1",
        "status": "passed",
        "wheel_sha256": _sha(wheel),
        "install_root": str(install_root),
        "members": sorted(member_rows, key=lambda row: row["wheel_path"]),
    }))
    packet_path = (tmp_path / "packet.json").resolve()
    launch_diagnostic_path = (tmp_path / "launch_diagnostic.json").resolve()
    packet = {
        "schema_version": supervisor.PACKET_SCHEMA,
        "status": "candidate_pending_advisory_review_and_external_authority",
        "packet_contract_sha256": "",
        "execution_commit": "a" * 40,
        "execution_tree": "b" * 40,
        "repository_root": str(tmp_path.resolve()),
        "wheel": {"path": str(wheel.resolve()), "sha256": _sha(wheel)},
        "installed_member_manifest": {"path": str(members.resolve()), "sha256": _sha(members)},
        "runtime_modules": runtime_modules,
        "route_manifest": route_manifest(),
        "route_manifest_sha256": route_manifest_sha256(),
        "output_root": str(output_root),
        "launch_diagnostic_path": str(launch_diagnostic_path),
        "outer_intent_path": str((tmp_path / "outer-intent.json").resolve()),
        "outer_invocation_path": str((tmp_path / "outer.json").resolve()),
        "outer_invocation_fallback_path": str((tmp_path / "outer-fallback.json").resolve()),
        "campaign_id": "m20-recovery-2026-07-17",
        "campaign_attempt_id": "attempt-01",
        "campaign_state": {"path": "", "sha256": ""},
        "command": [
            sys.executable,
            "-B",
            "-I",
            "-m",
            "research_assistant.survey.m20_recovery_launcher",
            "--packet",
            str(packet_path),
            "--output-root",
            str(output_root),
            "--launch-diagnostic-path",
            str(launch_diagnostic_path),
            "--outer-intent-path",
            str((tmp_path / "outer-intent.json").resolve()),
            "--outer-invocation-path",
            str((tmp_path / "outer.json").resolve()),
            "--outer-invocation-fallback-path",
            str((tmp_path / "outer-fallback.json").resolve()),
            "--execute-m20-recovery-campaign",
        ],
        "request_budget": {
            "request_cap": 5,
            "per_request_body_cap_bytes": 2_000_000,
            "total_body_cap_bytes": 10_000_000,
            "socket_timeout_seconds": 30,
            "whole_attempt_seconds": 367,
            "campaign_cost_cap_usd": "0.01",
            "redirect_cap": 0,
            "retry_cap": 0,
            "proxy_policy": "disabled",
        },
        "credential_interface": "OPENALEX_API_KEY",
        "network_scope": ["api.openalex.org:443", "export.arxiv.org:443"],
        "one_attempt_rule": "campaign_attempt_subject_to_plan_budget_and_repair_rules",
        "nonclaims": ["provider_behavior", "m20_completion"],
        "forbidden_actions": ["source_access", "push", "release"],
    }
    state = (tmp_path / "campaign_state.json").resolve()
    state.write_bytes(canonical_json_bytes({
        "schema_version": "ra-literature-survey-m20-recovery-campaign-state-v1",
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
    }))
    packet["campaign_state"] = {"path": str(state), "sha256": _sha(state)}
    packet["packet_contract_sha256"] = supervisor.packet_contract_sha256(packet)
    packet_path.write_bytes(canonical_json_bytes(packet))
    child_command = [
        sys.executable,
        "-B",
        "-I",
        "-m",
        "research_assistant.survey.m20_live_supervisor",
        "--packet",
        str(packet_path),
        "--output-root",
        str(output_root),
        "--launch-diagnostic-path",
        str(launch_diagnostic_path),
        "--execute-m20-recovery-campaign",
    ]
    Path(packet["outer_intent_path"]).write_bytes(canonical_json_bytes({
        "schema_version": supervisor.OUTER_INTENT_SCHEMA,
        "packet_file_sha256": _sha(packet_path),
        "child_command": child_command,
        "credential_read_or_enumerated_by_launcher": False,
        "provider_activity": False,
        "cost_usd": "0.00",
        "privacy_state": "passed_closed_construction_before_child",
    }))
    return packet_path, packet


def _git_identity(_root: Path) -> tuple[str, str]:
    return "a" * 40, "b" * 40


def test_preflight_closes_packet_before_any_credential_lookup(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    assert supervisor.load_and_preflight_packet(
        packet_path,
        output_root=output_root,
        launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
        git_identity=_git_identity,
    ) == packet
    tampered = json.loads(packet_path.read_text())
    tampered["request_budget"]["request_cap"] = 6
    packet_path.write_bytes(canonical_json_bytes(tampered))
    with pytest.raises(supervisor.M20SupervisorError, match="packet_contract_hash_invalid"):
        supervisor.load_and_preflight_packet(
            packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            git_identity=_git_identity,
        )


def test_packet_only_preflight_requires_fresh_absent_intent_path(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    intent_path = Path(packet["outer_intent_path"])
    intent_path.unlink()
    assert supervisor.load_and_preflight_packet(
        packet_path,
        output_root=output_root,
        launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
        require_outer_intent=False,
        git_identity=_git_identity,
    ) == packet
    intent_path.write_text("occupied")
    with pytest.raises(supervisor.M20SupervisorError, match="packet_outer_intent_path_invalid"):
        supervisor.load_and_preflight_packet(
            packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            require_outer_intent=False,
            git_identity=_git_identity,
        )


def test_main_never_reads_credential_when_packet_preflight_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    packet_path.write_bytes(b"{}")
    monkeypatch.setattr(
        supervisor,
        "_environment_credential",
        lambda: pytest.fail("credential lookup must follow complete packet preflight"),
    )
    assert supervisor.main([
        "--packet", str(packet_path),
        "--output-root", str(output_root),
        "--launch-diagnostic-path", packet["launch_diagnostic_path"],
        "--execute-m20-recovery-campaign",
    ]) == 2
    diagnostic = json.loads(Path(packet["launch_diagnostic_path"]).read_text())
    assert diagnostic["outcome"] == "preflight_failed"
    assert diagnostic["error_code"] == "packet_shape_invalid"
    assert diagnostic["credential_lookup_performed"] is False
    assert diagnostic["provider_activity"] is False
    assert diagnostic["cost_usd"] == "0.00"


def _main_args(packet_path: Path, packet: dict) -> list[str]:
    return [
        "--packet", str(packet_path),
        "--output-root", packet["output_root"],
        "--launch-diagnostic-path", packet["launch_diagnostic_path"],
        "--execute-m20-recovery-campaign",
    ]


def test_main_records_credential_unavailable_after_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    monkeypatch.setattr(supervisor, "load_and_preflight_packet", lambda *args, **kwargs: packet)
    monkeypatch.setattr(supervisor, "_environment_credential", lambda: None)

    assert supervisor.main(_main_args(packet_path, packet)) == 2
    diagnostic = json.loads(Path(packet["launch_diagnostic_path"]).read_text())
    assert diagnostic["outcome"] == "credential_unavailable"
    assert diagnostic["preflight_completed"] is True
    assert diagnostic["credential_lookup_performed"] is True
    assert diagnostic["credential_available"] is False
    assert diagnostic["supervised_execution_started"] is False
    assert diagnostic["provider_activity"] is False
    assert diagnostic["cost_usd"] == "0.00"


def test_main_records_unexpected_preflight_error_without_exception_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    monkeypatch.setattr(
        supervisor,
        "load_and_preflight_packet",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("sensitive_preflight_detail")),
    )
    monkeypatch.setattr(
        supervisor,
        "_environment_credential",
        lambda: pytest.fail("credential lookup must follow complete packet preflight"),
    )

    assert supervisor.main(_main_args(packet_path, packet)) == 2
    diagnostic_path = Path(packet["launch_diagnostic_path"])
    diagnostic = json.loads(diagnostic_path.read_text())
    assert diagnostic["outcome"] == "preflight_failed"
    assert diagnostic["error_code"] == "preflight_unexpected_error"
    assert diagnostic["credential_lookup_performed"] is False
    assert b"sensitive_preflight_detail" not in diagnostic_path.read_bytes()


def test_main_records_credential_lookup_failure_without_exception_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    monkeypatch.setattr(supervisor, "load_and_preflight_packet", lambda *args, **kwargs: packet)
    monkeypatch.setattr(
        supervisor,
        "_environment_credential",
        lambda: (_ for _ in ()).throw(RuntimeError("sensitive_lookup_detail")),
    )

    assert supervisor.main(_main_args(packet_path, packet)) == 2
    diagnostic_path = Path(packet["launch_diagnostic_path"])
    diagnostic = json.loads(diagnostic_path.read_text())
    assert diagnostic["outcome"] == "credential_lookup_failed"
    assert diagnostic["credential_lookup_performed"] is True
    assert diagnostic["credential_available"] is None
    assert diagnostic["supervised_execution_started"] is False
    assert b"sensitive_lookup_detail" not in diagnostic_path.read_bytes()


def test_main_records_supervised_execution_return(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    canary = "M20_RECOVERY_DIAGNOSTIC_CANARY"
    monkeypatch.setattr(supervisor, "load_and_preflight_packet", lambda *args, **kwargs: packet)
    monkeypatch.setattr(supervisor, "_environment_credential", lambda: canary)

    def run(_packet_value: dict, *, credential: str) -> int:
        assert credential == canary
        output_root.mkdir()
        (output_root / "supervisor_manifest.json").write_text("{}")
        return 2

    monkeypatch.setattr(supervisor, "run_supervised", run)
    assert supervisor.main(_main_args(packet_path, packet)) == 2
    diagnostic_path = Path(packet["launch_diagnostic_path"])
    diagnostic = json.loads(diagnostic_path.read_text())
    assert diagnostic["outcome"] == "supervised_execution_returned"
    assert diagnostic["credential_available"] is True
    assert diagnostic["supervised_execution_started"] is True
    assert diagnostic["provider_activity"] == "not_established"
    assert diagnostic["cost_usd"] == "not_established"
    assert diagnostic["live_root_exists"] is True
    assert diagnostic["supervisor_manifest_exists"] is True
    assert canary.encode() not in diagnostic_path.read_bytes()


def test_main_records_bounded_supervisor_error_without_exception_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    canary = "M20_RECOVERY_ERROR_CANARY"
    monkeypatch.setattr(supervisor, "load_and_preflight_packet", lambda *args, **kwargs: packet)
    monkeypatch.setattr(supervisor, "_environment_credential", lambda: canary)

    def fail(_packet_value: dict, *, credential: str) -> int:
        assert credential == canary
        raise supervisor.M20SupervisorError("sensitive_exception_detail")

    monkeypatch.setattr(supervisor, "run_supervised", fail)
    assert supervisor.main(_main_args(packet_path, packet)) == 2
    diagnostic_path = Path(packet["launch_diagnostic_path"])
    diagnostic = json.loads(diagnostic_path.read_text())
    assert diagnostic["outcome"] == "supervisor_error"
    assert diagnostic["error_code"] == "supervisor_error"
    assert diagnostic["credential_available"] is True
    assert b"sensitive_exception_detail" not in diagnostic_path.read_bytes()
    assert canary.encode() not in diagnostic_path.read_bytes()


def test_preflight_rejects_existing_root_and_runtime_byte_drift(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    output_root.mkdir()
    with pytest.raises(supervisor.M20SupervisorError, match="output_root_not_fresh"):
        supervisor.validate_packet(
            packet,
            packet_path=packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            git_identity=_git_identity,
        )


def test_preflight_rejects_installed_member_drift(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    manifest_path = Path(packet["installed_member_manifest"]["path"])
    value = json.loads(manifest_path.read_text())
    value["members"][0]["sha256"] = "0" * 64
    manifest_path.write_bytes(canonical_json_bytes(value))
    packet["installed_member_manifest"]["sha256"] = _sha(manifest_path)
    packet["packet_contract_sha256"] = supervisor.packet_contract_sha256(packet)
    with pytest.raises(supervisor.M20SupervisorError, match="installed_member_bytes_invalid"):
        supervisor.validate_packet(
            packet,
            packet_path=packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            git_identity=_git_identity,
        )


def test_preflight_rejects_runtime_module_byte_drift(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    packet["runtime_modules"]["research_assistant.survey.m20_live_worker"]["sha256"] = "0" * 64
    packet["packet_contract_sha256"] = supervisor.packet_contract_sha256(packet)
    with pytest.raises(supervisor.M20SupervisorError, match="runtime_module_bytes_invalid"):
        supervisor.validate_packet(
            packet,
            packet_path=packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            git_identity=_git_identity,
        )


def test_preflight_rejects_campaign_continuation_veto(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    state_path = Path(packet["campaign_state"]["path"])
    state = json.loads(state_path.read_text())
    state["continuation_veto"] = True
    state["next_attempt_allowed"] = False
    state_path.write_bytes(canonical_json_bytes(state))
    packet["campaign_state"]["sha256"] = _sha(state_path)
    packet["packet_contract_sha256"] = supervisor.packet_contract_sha256(packet)
    packet_path.write_bytes(canonical_json_bytes(packet))
    with pytest.raises(supervisor.M20SupervisorError, match="packet_campaign_state_invalid"):
        supervisor.validate_packet(
            packet,
            packet_path=packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            git_identity=_git_identity,
        )


def test_attempt_two_preflight_rejects_insufficient_remaining_campaign_cost(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    state_path = Path(packet["campaign_state"]["path"])
    state = json.loads(state_path.read_text())
    state.update({
        "attempts_completed": 1,
        "provider_launches_used": 1,
        "reconciled_cost_usd": "0.0090",
        "remaining_cost_usd": "0.0010",
        "next_attempt_id": "attempt-02",
        "predecessor_campaign_state_sha256": "c" * 64,
    })
    state_path.write_bytes(canonical_json_bytes(state))
    packet["campaign_attempt_id"] = "attempt-02"
    packet["campaign_state"]["sha256"] = _sha(state_path)
    packet["packet_contract_sha256"] = supervisor.packet_contract_sha256(packet)
    packet_path.write_bytes(canonical_json_bytes(packet))
    intent_path = Path(packet["outer_intent_path"])
    intent = json.loads(intent_path.read_text())
    intent["packet_file_sha256"] = _sha(packet_path)
    intent_path.write_bytes(canonical_json_bytes(intent))
    monkeypatch.setattr(
        supervisor,
        "_environment_credential",
        lambda: pytest.fail("insufficient remaining campaign cost must fail before credential lookup"),
    )
    load_and_preflight = supervisor.load_and_preflight_packet
    monkeypatch.setattr(
        supervisor,
        "load_and_preflight_packet",
        lambda *args, **kwargs: load_and_preflight(*args, **kwargs, git_identity=_git_identity),
    )

    assert supervisor.main(_main_args(packet_path, packet)) == 2
    diagnostic = json.loads(Path(packet["launch_diagnostic_path"]).read_text())
    assert diagnostic["outcome"] == "preflight_failed"
    assert diagnostic["error_code"] == "packet_campaign_state_invalid"
    assert diagnostic["credential_lookup_performed"] is False


def test_preflight_rejects_symlinked_outer_record_parent(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    packet_path, packet = _packet(tmp_path, output_root)
    actual = tmp_path / "actual-outer"
    actual.mkdir()
    alias = tmp_path / "outer-alias"
    alias.symlink_to(actual, target_is_directory=True)
    packet["outer_invocation_path"] = str(alias / "outer.json")
    packet["command"][packet["command"].index("--outer-invocation-path") + 1] = packet[
        "outer_invocation_path"
    ]
    packet["packet_contract_sha256"] = supervisor.packet_contract_sha256(packet)
    packet_path.write_bytes(canonical_json_bytes(packet))
    intent = json.loads(Path(packet["outer_intent_path"]).read_text())
    intent["packet_file_sha256"] = _sha(packet_path)
    Path(packet["outer_intent_path"]).write_bytes(canonical_json_bytes(intent))
    with pytest.raises(supervisor.M20SupervisorError, match="packet_outer_invocation_path_invalid"):
        supervisor.validate_packet(
            packet,
            packet_path=packet_path,
            output_root=output_root,
            launch_diagnostic_path=Path(packet["launch_diagnostic_path"]),
            git_identity=_git_identity,
        )


def test_synthetic_fake_child_proves_minimal_environment_and_manifest_last(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    _packet_path, packet = _packet(tmp_path, output_root)
    canary = f"M20B3_SUPERVISOR_{secrets.token_urlsafe(24)}+/\""
    observed = {}

    class Process:
        pid = 12345
        returncode = None

        def __init__(self, command, **kwargs):
            observed["command"] = command
            observed["kwargs"] = kwargs

        def communicate(self, timeout):
            observed["timeout"] = timeout

            def openalex_dispatch(request):
                import urllib.parse

                query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
                assert query.pop("api_key") == [canary]
                if "search" in query:
                    return _list(OPENALEX_ID, cost=0.001)
                if urllib.parse.urlsplit(request.full_url).path.endswith(OPENALEX_ID):
                    return canonical_json_bytes(_work(OPENALEX_ID, lineage=["https://openalex.org/W1"]))
                return _list("W2", cost=0.0001)

            run_matrix(
                output_root=output_root,
                credential_getter=lambda name: canary,
                arxiv_dispatch=lambda descriptor: (
                    _atom(arxiv_id="9999.00001v1", title=route_manifest()["topic"])
                    if descriptor["route_kind"] == "arxiv_topic"
                    else _atom(arxiv_id=ARXIV_SEED, title="Neural Optimal Transport")
                ),
                openalex_dispatch=openalex_dispatch,
                execution_mode="live",
            )
            self.returncode = 0
            return b"", b""

        def wait(self, timeout):
            return self.returncode

        def send_signal(self, sig):
            pytest.fail(f"unexpected signal {sig}")

    assert supervisor.run_supervised(packet, credential=canary, popen_factory=Process) == 0
    assert observed["kwargs"]["env"] == {
        "OPENALEX_API_KEY": canary,
        "CUDA_VISIBLE_DEVICES": "-1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    record = json.loads((output_root / "supervisor_manifest.json").read_text())
    assert record["classification"] == "completed"
    assert record["manifest_published_last"] is True
    assert "supervisor_manifest.json" not in {row["path"] for row in record["artifact_inventory"]}
    assert not any(canary.encode() in path.read_bytes() for path in output_root.rglob("*") if path.is_file())


def test_credential_in_worker_artifact_is_closed_failure(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    _packet_path, packet = _packet(tmp_path, output_root)
    canary = "M20B3_SUPERVISOR_LEAK_CANARY"

    class Process:
        pid = 12345
        returncode = None

        def __init__(self, command, **kwargs):
            pass

        def communicate(self, timeout):
            output_root.mkdir()
            (output_root / "campaign_summary.json").write_text(canary)
            self.returncode = 0
            return b"", b""

        def wait(self, timeout):
            return self.returncode

    assert supervisor.run_supervised(packet, credential=canary, popen_factory=Process) == 2
    record = json.loads((output_root / "supervisor_manifest.json").read_text())
    assert record["classification"] == "worker_artifact_invalid"
    assert not any(canary.encode() in path.read_bytes() for path in output_root.rglob("*") if path.is_file())


def test_completed_child_with_invalid_replay_is_scrubbed_and_manifested(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    _packet_path, packet = _packet(tmp_path, output_root)
    canary = "M20B3_INVALID_REPLAY_CANARY"

    class Process:
        pid = 12345
        returncode = None

        def __init__(self, command, **kwargs):
            pass

        def communicate(self, timeout):
            def openalex_dispatch(request):
                import urllib.parse

                query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
                query.pop("api_key")
                if "search" in query:
                    return _list(OPENALEX_ID, cost=0.001)
                if urllib.parse.urlsplit(request.full_url).path.endswith(OPENALEX_ID):
                    return canonical_json_bytes(_work(OPENALEX_ID, lineage=[]))
                return _list("W2", cost=0.0001)

            run_matrix(
                output_root=output_root,
                credential_getter=lambda name: canary,
                arxiv_dispatch=lambda descriptor: (
                    _atom(arxiv_id="9999.00001v1", title=route_manifest()["topic"])
                    if descriptor["route_kind"] == "arxiv_topic"
                    else _atom(arxiv_id=ARXIV_SEED, title="Neural Optimal Transport")
                ),
                openalex_dispatch=openalex_dispatch,
                execution_mode="live",
            )
            ledger_path = output_root / "request_ledger.json"
            ledger = json.loads(ledger_path.read_text())
            ledger["accepted_body_bytes"] += 1
            ledger_path.write_bytes(canonical_json_bytes(ledger))
            self.returncode = 0
            return b"", b""

        def wait(self, timeout):
            return self.returncode

    assert supervisor.run_supervised(packet, credential=canary, popen_factory=Process) == 2
    assert {path.name for path in output_root.iterdir()} == {"supervisor_manifest.json"}
    record = json.loads((output_root / "supervisor_manifest.json").read_text())
    assert record["classification"] == "worker_artifact_invalid"


@pytest.mark.parametrize("timeout", [False, True])
def test_nonzero_or_timeout_partial_canary_is_removed_before_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timeout: bool
) -> None:
    output_root = (tmp_path / "run").resolve()
    _packet_path, packet = _packet(tmp_path, output_root)
    canary = f"M20B3_PARTIAL_{secrets.token_urlsafe(24)}"
    should_timeout = timeout
    monkeypatch.setattr(supervisor.os, "killpg", lambda pid, sig: None)

    class Process:
        pid = 12345
        returncode = None
        calls = 0

        def __init__(self, command, **kwargs):
            pass

        def communicate(self, timeout):
            self.calls += 1
            if self.calls == 1:
                output_root.mkdir()
                (output_root / "request_ledger.json").write_text(canary)
                if should_timeout:
                    raise subprocess.TimeoutExpired("worker", timeout)
                self.returncode = 1
            else:
                self.returncode = -signal.SIGTERM
            return b"", b""

        def wait(self, timeout):
            self.returncode = -signal.SIGKILL
            return self.returncode

        def send_signal(self, sig):
            pytest.fail("process group signal should succeed")

    assert supervisor.run_supervised(
        packet,
        credential=canary,
        popen_factory=Process,
    ) == 2
    assert {path.name for path in output_root.iterdir()} == {"supervisor_manifest.json"}
    assert canary.encode() not in (output_root / "supervisor_manifest.json").read_bytes()


def test_worker_replaced_root_symlink_cannot_receive_manifest(tmp_path: Path) -> None:
    output_root = (tmp_path / "run").resolve()
    outside = (tmp_path / "outside").resolve()
    outside.mkdir()
    _packet_path, packet = _packet(tmp_path, output_root)

    class Process:
        pid = 12345
        returncode = None

        def __init__(self, command, **kwargs):
            pass

        def communicate(self, timeout):
            output_root.symlink_to(outside, target_is_directory=True)
            self.returncode = 1
            return b"", b""

        def wait(self, timeout):
            return self.returncode

    with pytest.raises(supervisor.M20SupervisorError, match="output_root_invalid"):
        supervisor.run_supervised(
            packet,
            credential="M20B3_SYMLINK_CANARY",
            popen_factory=Process,
        )
    assert not (outside / "supervisor_manifest.json").exists()


def test_soft_then_hard_deadline_signals_process_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = (tmp_path / "run").resolve()
    _packet_path, packet = _packet(tmp_path, output_root)
    signals = []
    monkeypatch.setattr(supervisor.os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    class Clock:
        value = 0.0

        def __call__(self):
            self.value += 1.0
            return self.value

    class Process:
        pid = 54321
        returncode = None
        calls = 0

        def __init__(self, command, **kwargs):
            pass

        def communicate(self, timeout):
            self.calls += 1
            if self.calls <= 2:
                raise subprocess.TimeoutExpired("worker", timeout)
            self.returncode = -signal.SIGKILL
            return b"", b""

        def wait(self, timeout):
            self.returncode = -signal.SIGKILL
            return self.returncode

        def send_signal(self, sig):
            pytest.fail("process group signaling should succeed")

    assert supervisor.run_supervised(
        packet,
        credential="M20B3_DEADLINE_CANARY",
        popen_factory=Process,
        clock=Clock(),
    ) == 2
    assert signals == [(54321, signal.SIGTERM), (54321, signal.SIGKILL)]
    record = json.loads((output_root / "supervisor_manifest.json").read_text())
    assert record["classification"] == "hard_timeout"
    assert record["signals_sent"] == ["SIGTERM", "SIGKILL"]


def test_supervisor_source_uses_one_exact_environment_lookup() -> None:
    source = Path("src/research_assistant/survey/m20_live_supervisor.py").read_text()
    assert source.count("os.environ.get(CREDENTIAL_INTERFACE)") == 1
    assert "os.environ[" not in source
    assert "os.getenv" not in source
