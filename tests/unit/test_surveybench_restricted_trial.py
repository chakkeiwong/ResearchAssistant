from __future__ import annotations

import json
import os
from pathlib import Path

from research_assistant.benchmarks.restricted_trial import (
    DEFAULT_TASK_PATH,
    FIXED_FAILURE_CLASSES,
    RESTRICTED_IMPORT_CLOSURE,
    SUBJECT_TRANSPORT_CODEX_EXEC,
    STRESS_TASK_PATH,
    build_launch_enforcement_preflight,
    build_launch_approval_packet,
    build_restricted_launcher_dry_run,
    build_contract_manifest_template,
    build_restricted_child_environment,
    build_subject_binding_preflight,
    build_subject_settings_payload,
    build_subject_wrapper_command_template,
    compare_replay_call_parity,
    create_restricted_workspace,
    forbidden_tokens_in_text,
    path_allowed_for_restricted_workspace,
    path_forbidden_for_restricted_workspace,
    run_detector_negative_cases,
    run_restricted_parity_smoke,
    run_restricted_replay_call,
    runner_command_allowed,
    scan_path_escape,
    scan_forbidden_tokens,
    validate_agent_prompt_text,
    validate_launch_approval_packet,
    validate_restricted_manifest_payload,
    validate_subject_settings_payload,
)


ROOT = Path(__file__).resolve().parents[2]


def test_restricted_contract_allows_only_agent_visible_replay_artifacts() -> None:
    assert path_allowed_for_restricted_workspace(Path("pyproject.toml"))
    assert path_allowed_for_restricted_workspace(DEFAULT_TASK_PATH)
    assert path_allowed_for_restricted_workspace(DEFAULT_TASK_PATH.parent / "responses" / "search.json")

    assert not path_allowed_for_restricted_workspace(DEFAULT_TASK_PATH.parent / "scorer_packet" / "citation_map.json")
    assert not path_allowed_for_restricted_workspace(Path("docs/validation/surveybench_online_replay_phase5/example_output/citation_map.json"))
    assert not path_allowed_for_restricted_workspace(Path("docs/validation/surveybench_online_replay_phase5/score_report.json"))
    assert not path_allowed_for_restricted_workspace(Path(".git/config"))
    assert path_forbidden_for_restricted_workspace(Path("tmp/hidden_gold/answer_key.json"))


def test_forbidden_tokens_include_agent_prompt_leaks() -> None:
    text = "Run replay-score with --gold-dir tests/.../scorer_packet and expected_outputs"

    hits = forbidden_tokens_in_text(text)

    assert "--gold-dir" in hits
    assert "scorer_packet" in hits
    assert "expected_outputs" in hits


def test_child_environment_is_fixed_and_omits_sensitive_parent_values(tmp_path: Path) -> None:
    parent = {
        "PATH": "/ambient/bin",
        "PYTHONPATH": "/ambient/src",
        "OPENAI_API_KEY": "secret",
        "HTTPS_PROXY": "https://user:pass@example.invalid",
        "LANG": "C.UTF-8",
    }

    env, manifest = build_restricted_child_environment(tmp_path, parent)

    assert env["PYTHONPATH"] == str(tmp_path.resolve() / "src")
    assert "/ambient/src" not in env["PYTHONPATH"]
    assert "/ambient/bin" not in env["PATH"]
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["HOME"].startswith(str(tmp_path.resolve()))
    assert env["TMPDIR"].startswith(str(tmp_path.resolve()))
    assert "OPENAI_API_KEY" not in env
    assert "HTTPS_PROXY" not in env
    assert manifest["path_policy"] == "fixed_minimal"
    assert manifest["pythonpath_policy"] == "workspace_src_only"
    assert manifest["sensitive_omission_count"] == 2


def test_runner_command_allowlist_requires_absolute_python_and_workspace_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tests" / "fixtures" / "surveybench" / "online_replay" / "neural_ot_seed_replay" / "neural_ot_seed_replay.task.json"
    session = workspace / "session"
    task.parent.mkdir(parents=True)
    session.mkdir(parents=True)
    task.write_text("{}")

    allowed = [
        os.path.realpath("/usr/bin/python3"),
        "-m",
        "research_assistant.cli",
        "surveybench",
        "replay-call",
        "--task",
        str(task),
        "--endpoint",
        "search",
        "--session",
        str(session),
    ]
    disallowed_score = [*allowed]
    disallowed_score[4] = "replay-score"
    disallowed_outside = [*allowed]
    disallowed_outside[6] = str(tmp_path / "outside.task.json")

    assert runner_command_allowed(allowed, workspace)
    assert not runner_command_allowed(allowed, workspace, cwd=tmp_path)
    assert runner_command_allowed(allowed, workspace, cwd=workspace)
    assert not runner_command_allowed(disallowed_score, workspace)
    assert not runner_command_allowed(["python", *allowed[1:]], workspace)
    assert not runner_command_allowed(disallowed_outside, workspace)


def test_manifest_template_contains_failure_actions_and_negative_cases(tmp_path: Path) -> None:
    manifest = build_contract_manifest_template(tmp_path / "workspace")

    report = validate_restricted_manifest_payload(manifest)

    assert report["status"] == "passed"
    assert set(manifest["failure_classes"]) == set(FIXED_FAILURE_CLASSES)
    assert manifest["failure_classes"]["boundary_leakage"]["action"].startswith("zero_tolerance")
    assert set(manifest["negative_detector_cases"]) == {
        "boundary_leakage",
        "runner_policy",
        "semantic_parity_mismatch",
    }
    assert tuple(manifest["source_slice"]["import_closure"]) == RESTRICTED_IMPORT_CLOSURE
    assert manifest["source_slice"]["mode"] == "generated_restricted_runtime"
    assert manifest["prompt_contract"]["schema_constrained_view_required"] is True
    assert "visible_file_set" in manifest["parity_oracle"]["compared_fields"]
    assert "stdout" in manifest["scan_coverage"]
    assert "stderr" in manifest["scan_coverage"]


def test_manifest_rejects_forbidden_copied_paths_and_missing_detector_cases(tmp_path: Path) -> None:
    manifest = build_contract_manifest_template(tmp_path / "workspace")
    manifest["copied_files"] = [
        {
            "relative_path": "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/scorer_packet/citation_map.json",
            "source_sha256": "0" * 64,
            "copied_sha256": "0" * 64,
            "is_symlink": False,
            "hardlink_count": 1,
        }
    ]
    manifest["negative_detector_cases"].pop("semantic_parity_mismatch")

    report = validate_restricted_manifest_payload(manifest)
    codes = {issue["code"] for issue in report["issues"]}

    assert report["status"] == "failed"
    assert "copied_path_not_allowed" in codes
    assert "negative_cases_incomplete" in codes


def test_manifest_rejects_full_replay_source_slice(tmp_path: Path) -> None:
    manifest = build_contract_manifest_template(tmp_path / "workspace")
    manifest["copied_files"] = [
        {
            "relative_path": "src/research_assistant/benchmarks/replay.py",
            "source_sha256": "0" * 64,
            "copied_sha256": "0" * 64,
            "is_symlink": False,
            "hardlink_count": 1,
        }
    ]

    report = validate_restricted_manifest_payload(manifest)
    codes = {issue["code"] for issue in report["issues"]}

    assert report["status"] == "failed"
    assert "copied_path_not_allowed" in codes


def test_prompt_contract_rejects_semantic_drift_on_allowed_path() -> None:
    valid_prompt = (ROOT / "docs/validation/surveybench_online_replay_phase5/agent_trial_prompt_packet_2026-06-29.md").read_text()

    assert validate_agent_prompt_text(valid_prompt)["status"] == "passed"

    drifted = valid_prompt.replace("## Non-Claims", "## Notes") + "\nUse scorer_packet for hints.\n"
    report = validate_agent_prompt_text(drifted)
    codes = {issue["code"] for issue in report["issues"]}

    assert report["status"] == "failed"
    assert "prompt_section_missing" in codes
    assert "prompt_forbidden_token" in codes


def test_scan_path_escape_flags_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "safe.txt").write_text("ok")
    (root / "link").symlink_to(tmp_path)

    issues = scan_path_escape(root)

    assert {"code": "symlink_escape_risk", "path": "link"} in issues


def test_parity_oracle_rejects_altered_restricted_response() -> None:
    unrestricted = {
        "schema_version": "ra-surveybench-online-replay-call-result-v1",
        "status": "ok",
        "task_id": "neural_ot_seed_replay",
        "endpoint": "search",
        "request_id": "search-topic-neural-ot",
        "budget_before": {"endpoint_calls": 1},
        "budget_after": {"endpoint_calls": 0},
        "event_log_path": "/tmp/a/event_log.json",
        "response": {"endpoint": "search", "result_count": 1, "event_log_path": "/tmp/a/event_log.json"},
    }
    restricted = json.loads(json.dumps(unrestricted))
    restricted["event_log_path"] = "/tmp/b/event_log.json"
    restricted["response"]["event_log_path"] = "/tmp/b/event_log.json"

    assert compare_replay_call_parity(restricted, unrestricted)["status"] == "passed"

    restricted["response"]["result_count"] = 2
    report = compare_replay_call_parity(restricted, unrestricted)

    assert report["status"] == "failed"
    assert report["mismatches"][0]["code"] == "semantic_parity_mismatch"
    assert "visible_file_set" in report["boundary_checks"]


def test_create_restricted_workspace_excludes_evaluator_artifacts_and_full_source(tmp_path: Path) -> None:
    workspace = tmp_path / "restricted_workspace"

    report = create_restricted_workspace(ROOT, workspace)

    assert report["status"] == "passed"
    assert (workspace / DEFAULT_TASK_PATH).exists()
    assert (workspace / "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/search.json").exists()
    assert (workspace / "src/research_assistant/cli.py").exists()
    assert not (workspace / "src/research_assistant/benchmarks/replay.py").exists()
    assert not (workspace / DEFAULT_TASK_PATH.parent / "scorer_packet").exists()
    assert not (workspace / "docs/validation/surveybench_online_replay_phase5/example_output").exists()
    assert not (workspace / ".git").exists()
    assert scan_path_escape(workspace) == []
    assert scan_forbidden_tokens(workspace) == []


def test_stress_profile_workspace_excludes_scorer_negative_and_expected_material(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"

    report = create_restricted_workspace(ROOT, workspace, profile="stress")

    stress_root = STRESS_TASK_PATH.parent
    assert report["status"] == "passed"
    assert report["profile_id"] == "neural_ot_seed_ambiguity_partial_frontier_replay"
    assert (workspace / STRESS_TASK_PATH).exists()
    assert (workspace / stress_root / "responses" / "citations.json").exists()
    assert (workspace / "docs/validation/surveybench_live_intake_launcher_phase3_restricted_launcher/stress_restricted_launcher_prompt_2026-07-03.md").exists()
    assert not (workspace / stress_root / "scorer_packet").exists()
    assert not (workspace / stress_root / "negative_packets").exists()
    assert not any("expected" in path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))
    assert scan_path_escape(workspace) == []
    assert scan_forbidden_tokens(workspace) == []


def test_restricted_runner_executes_generated_runtime_and_parity_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "restricted_workspace"
    create_restricted_workspace(ROOT, workspace)

    runner_report = run_restricted_replay_call(workspace, "search")

    assert runner_report["status"] == "passed"
    assert runner_report["cwd"] == str(workspace.resolve())
    assert runner_report["env_manifest"]["pythonpath_policy"] == "workspace_src_only"
    assert runner_report["payload"]["endpoint"] == "search"
    assert (workspace / "session" / "event_log.json").exists()

    parity_report = run_restricted_parity_smoke(ROOT, workspace, endpoints=("search",))
    assert parity_report["status"] == "passed"
    boundary = parity_report["reports"][0]["boundary"]
    assert "src/research_assistant/benchmarks/replay.py" not in boundary["visible_file_set"]
    assert boundary["command_shape"] == ["-m", "research_assistant.cli", "surveybench", "replay-call"]


def test_stress_profile_runner_parity_smoke_and_launcher_dry_run(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"
    create_restricted_workspace(ROOT, workspace, profile="stress")

    runner_report = run_restricted_replay_call(workspace, "citations", profile="stress")
    assert runner_report["status"] == "passed"
    assert runner_report["payload"]["task_id"] == "neural_ot_seed_ambiguity_partial_frontier_replay"
    assert runner_report["payload"]["response"]["partial_frontier"]["status"] == "partial_frontier"

    parity_report = run_restricted_parity_smoke(ROOT, workspace, endpoints=("search", "citations"))
    assert parity_report["status"] == "passed"
    assert parity_report["profile_id"] == "neural_ot_seed_ambiguity_partial_frontier_replay"

    launch = build_restricted_launcher_dry_run(workspace, profile="stress", subject_agent="claude-opus-readonly-not-launched")
    assert launch["status"] == "prepared_not_launched"
    assert launch["dry_run"] is True
    assert launch["subject_invoked"] is False
    assert launch["repo_root_not_provided_to_subject"] is True
    assert launch["network_policy"] == "offline_replay_only_no_live_api_download_or_credentials"
    assert "launch a real subject process" in launch["forbidden_actions"]
    assert all("replay-call" in " ".join(command) for command in launch["allowed_command_templates"])


def test_subject_settings_bind_only_replay_call_and_deny_live_shell(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"
    create_restricted_workspace(ROOT, workspace, profile="stress")

    payload = build_subject_settings_payload(workspace, profile="stress")
    report = validate_subject_settings_payload(payload, workspace, profile="stress")

    assert report["status"] == "passed"
    allowed = payload["permissions"]["allow"]
    denied = payload["permissions"]["deny"]
    assert payload["permissions"]["defaultMode"] == "dontAsk"
    assert "Write" not in allowed
    assert any(item.startswith("Write(") and "agent_output" in item for item in allowed)
    assert any(item.startswith("Read(") and str(workspace.resolve()) in item for item in allowed)
    assert all("/responses/" not in item for item in allowed if item.startswith(("Read(", "LS(", "Glob(", "Grep(")))
    assert any("replay-call" in item and "--endpoint search" in item for item in allowed)
    assert any("replay-call" in item and "--endpoint source-anchors" in item for item in allowed)
    assert any("curl" in item for item in denied)
    assert all("replay-score" not in item for item in allowed)
    assert all("scorer_packet" not in item for item in allowed)

    drifted = json.loads(json.dumps(payload))
    drifted["permissions"]["allow"].append("Read")
    drifted["permissions"]["allow"].append("Read(/tmp/outside-hidden/scorer_packet/citation_map.json)")
    drifted["permissions"]["allow"].append(f"Read({workspace}/tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/responses/search.json)")
    drifted["permissions"]["allow"].append("Bash(PYTHONPATH=src python *)")
    drifted["permissions"]["allow"].append("Bash(curl *)")
    drifted["permissions"]["defaultMode"] = "default"
    failed = validate_subject_settings_payload(drifted, workspace, profile="stress")
    codes = {issue["code"] for issue in failed["issues"]}

    assert failed["status"] == "failed"
    assert "permission_mode_mismatch" in codes
    assert "unbounded_file_tool_allowed" in codes
    assert "file_tool_path_outside_workspace" in codes
    assert "forbidden_file_tool_path" in codes
    assert "response_file_tool_path_forbidden" in codes
    assert "broad_bash_allowed" in codes
    assert "live_or_mutating_bash_allowed" in codes


def test_subject_binding_preflight_writes_settings_and_replay_probe_without_subject(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"
    create_restricted_workspace(ROOT, workspace, profile="stress")

    report = build_subject_binding_preflight(workspace, profile="stress")

    assert report["status"] == "passed"
    assert report["subject_invoked"] is False
    assert report["permission_mode"] == "dontAsk"
    assert report["settings_validation"]["status"] == "passed"
    assert report["representative_probe"]["status"] == "passed"
    assert report["allowed_file_tool_patterns"]
    assert all(item != "Read" for item in report["allowed_file_tool_patterns"])
    assert (workspace / "governance" / "claude_subject_settings.json").exists()
    assert (workspace / "governance" / "subject_binding_preflight.json").exists()
    command = report["wrapper_command_template"]
    assert "--permission-mode" in command
    assert "dontAsk" in command
    assert "--settings" in command
    assert "--dangerously-skip-permissions" not in command
    assert "<restricted-prompt-file>" in command


def test_codex_subject_binding_preflight_and_wrapper_template(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"
    create_restricted_workspace(ROOT, workspace, profile="stress")

    report = build_subject_binding_preflight(
        workspace,
        profile="stress",
        subject_agent="codex-subject",
        model_id="gpt-5.3-codex",
        subject_transport=SUBJECT_TRANSPORT_CODEX_EXEC,
        permission_mode=None,
    )

    assert report["status"] == "passed"
    assert report["subject_transport"] == SUBJECT_TRANSPORT_CODEX_EXEC
    assert report["settings_path"] is None
    assert report["settings_sha256"] is None
    assert report["settings_validation"]["status"] == "not_applicable"
    assert report["wrapper_command_kind"] == "codex_exec"
    assert report["wrapper_command_template"][0:4] == ["codex", "--ask-for-approval", "never", "exec"]
    assert "--ask-for-approval" in report["wrapper_command_template"]
    assert "never" in report["wrapper_command_template"]
    assert "--sandbox" in report["wrapper_command_template"]
    assert "workspace-write" in report["wrapper_command_template"]

    codex_command = build_subject_wrapper_command_template(
        workspace,
        profile="stress",
        subject_transport=SUBJECT_TRANSPORT_CODEX_EXEC,
        model_id="gpt-5.3-codex",
    )
    assert codex_command[0:4] == ["codex", "--ask-for-approval", "never", "exec"]
    assert "--output-last-message" in codex_command
    assert any(part.endswith("codex_subject_last_message.md") for part in codex_command)


def test_launch_approval_packet_preflight_requires_human_gate_and_exact_runtime(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"
    create_restricted_workspace(ROOT, workspace, profile="stress")
    dry_run = build_restricted_launcher_dry_run(workspace, profile="stress", subject_agent="claude-opus-not-launched")
    binding = build_subject_binding_preflight(workspace, profile="stress")

    packet = build_launch_approval_packet(
        dry_run,
        subject_agent="claude-opus-subject",
        model_id="claude-opus-4-1",
        subject_transport="claude-code",
        wrapper_command=binding["wrapper_command_template"],
        budget_cap={"wall_time_seconds": 1800, "max_turns": 1},
        transcript_path=workspace / "governance" / "subject_transcript.jsonl",
        denied_tool_capture_path=workspace / "governance" / "denied_tools.jsonl",
        cli_version="claude-cli-test-version",
        subject_binding_preflight=binding,
    )
    report = validate_launch_approval_packet(packet)

    assert report["status"] == "passed"
    assert packet["status"] == "pending_human_approval"
    assert packet["subject_invoked"] is False
    assert packet["human_launch_approval"]["required"] is True
    assert packet["human_launch_approval"]["granted"] is False
    assert packet["preflight_status"] == "passed"
    assert packet["runtime_enforcement"]["preflight_scope"] == "packet_completeness_not_launch_readiness"
    assert packet["runtime_enforcement"]["budget_mechanically_enforced_by_packet_preflight"] is False
    assert packet["runtime_enforcement"]["subject_tool_network_mechanically_enforced_by_packet_preflight"] is True
    assert packet["runtime_enforcement"]["budget_enforcement_required_before_phase3"] is True
    assert packet["subject_binding_preflight"]["status"] == "passed"
    assert packet["subject_binding_preflight"]["permission_mode"] == "dontAsk"

    packet["model_id"] = ""
    packet["transcript_path"] = str(tmp_path / "outside_transcript.jsonl")
    packet["runtime_enforcement"]["budget_mechanically_enforced_by_packet_preflight"] = True
    packet["human_launch_approval"]["granted"] = True
    packet["subject_binding_preflight"]["permission_mode"] = "default"
    failed = validate_launch_approval_packet(packet)
    codes = {issue["code"] for issue in failed["issues"]}

    assert failed["status"] == "failed"
    assert "missing_required_field" in codes
    assert "path_outside_workspace" in codes
    assert "runtime_enforcement_overclaim" in codes
    assert "approval_prematurely_granted" in codes
    assert "subject_binding_literal_mismatch" in codes


def test_launch_enforcement_preflight_binds_hashes_and_capture_without_launch(tmp_path: Path) -> None:
    workspace = tmp_path / "stress_restricted_workspace"
    create_restricted_workspace(ROOT, workspace, profile="stress")
    dry_run = build_restricted_launcher_dry_run(workspace, profile="stress", subject_agent="claude-opus-not-launched")
    binding = build_subject_binding_preflight(workspace, profile="stress")
    packet = build_launch_approval_packet(
        dry_run,
        subject_agent="claude-opus-subject",
        model_id="claude-opus-4-1",
        subject_transport="claude-code",
        wrapper_command=binding["wrapper_command_template"],
        budget_cap={"wall_time_seconds": 1800, "max_turns": 1},
        transcript_path=workspace / "governance" / "subject_transcript.jsonl",
        denied_tool_capture_path=workspace / "governance" / "denied_tools.jsonl",
        cli_version="claude-cli-test-version",
        subject_binding_preflight=binding,
    )
    packet_path = workspace / "governance" / "launch_approval_packet.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True))

    report = build_launch_enforcement_preflight(packet_path)

    assert report["status"] == "passed"
    assert report["subject_invoked"] is False
    assert report["supervisor_execution"]["timeout_enforcement"] == "python_subprocess_timeout_on_phase3_launch"
    assert report["supervisor_execution"]["wall_time_seconds"] == 1800
    assert report["capture_contract"]["denied_tool_capture_authoritative"] is False
    assert report["no_drift"]["status"] == "passed"
    assert report["subject_task_boundary"]["subject_binding_preflight"]["status"] == "passed"
    assert "<restricted-prompt-file>" not in report["resolved_subject_command"]
    assert "--model" in report["resolved_subject_command"]
    assert "claude-opus-4-1" in report["resolved_subject_command"]
    assert "--permission-mode" in report["resolved_subject_command"]
    assert "dontAsk" in report["resolved_subject_command"]
    assert "--settings" in report["resolved_subject_command"]
    assert STRESS_TASK_PATH.as_posix() in " ".join(report["resolved_subject_command"])

    prompt_path = Path(packet["prompt_path"])
    prompt_path.write_text(prompt_path.read_text() + "\n")
    failed = build_launch_enforcement_preflight(packet_path)
    codes = {issue["code"] for issue in failed["issues"]}

    assert failed["status"] == "failed"
    assert "hash_drift" in codes

    packet["prompt_sha256"] = failed["no_drift"]["checks"]["prompt"]["actual_sha256"]
    packet["wrapper_command"] = ["claude", "-p", "<restricted-prompt-path>"]
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True))
    binding_failed = build_launch_enforcement_preflight(packet_path)
    binding_codes = {issue["code"] for issue in binding_failed["issues"]}

    assert binding_failed["status"] == "failed"
    assert "subject_model_not_bound" in binding_codes
    assert "prompt_path_used_as_prompt" in binding_codes
    assert "subject_permission_mode_not_bound" in binding_codes
    assert "subject_settings_not_bound" in binding_codes

    settings_path = Path(packet["subject_binding_preflight"]["settings_path"])
    packet["wrapper_command"] = binding["wrapper_command_template"]
    settings_path.write_text(settings_path.read_text() + "\n")
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True))
    settings_failed = build_launch_enforcement_preflight(packet_path)
    settings_codes = {issue["code"] for issue in settings_failed["issues"]}

    assert settings_failed["status"] == "failed"
    assert "subject_settings_hash_drift" in settings_codes


def test_detector_negative_cases_fire(tmp_path: Path) -> None:
    workspace = tmp_path / "restricted_workspace"
    create_restricted_workspace(ROOT, workspace)

    report = run_detector_negative_cases(workspace)

    assert report["status"] == "passed"
    assert report["cases"] == {
        "boundary_leakage": True,
        "runner_policy": True,
        "semantic_parity_mismatch": True,
    }
