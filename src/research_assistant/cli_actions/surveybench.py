from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


Report = dict[str, Any]
ActionHandler = Callable[[argparse.Namespace, "SurveybenchServices"], int]


@dataclass(frozen=True, slots=True)
class SurveybenchServices:
    print_json: Callable[[dict | list], int]
    display_path: Callable[[Path], str]
    score_survey_task: Callable[..., Report]
    validate_local_manifest: Callable[..., Report]
    replay_call: Callable[..., Report]
    validate_replay_fixture_interface: Callable[..., Report]
    build_replay_transcript: Callable[..., Report]
    score_replay_submission: Callable[..., Report]
    score_survey_prose: Callable[..., Report]
    create_restricted_workspace: Callable[..., Report]
    build_restricted_launcher_dry_run: Callable[..., Report]
    build_subject_binding_preflight: Callable[..., Report]
    build_launch_approval_packet: Callable[..., Report]
    validate_launch_approval_packet: Callable[..., Report]
    build_launch_enforcement_preflight: Callable[..., Report]
    surveybench_next_action: Callable[..., Report]
    surveybench_packet_template: Callable[..., Report]
    surveybench_packet_compose: Callable[..., Report]
    surveybench_cluster_hints: Callable[..., Report]
    surveybench_ready_for_prose: Callable[..., Report]
    surveybench_launch_record_template: Callable[..., Report]
    scan_subject_helper_payload: Callable[[Report], Report]


def execute_surveybench_action(args: argparse.Namespace, services: SurveybenchServices) -> int:
    """Execute one registered SurveyBench action through an explicit dispatch table."""
    try:
        handler = SURVEYBENCH_ACTION_HANDLERS[args.surveybench_action]
    except KeyError as exc:
        raise SystemExit(f"unknown surveybench action {args.surveybench_action}") from exc
    return handler(args, services)


def _write_report(path: str, report: Report) -> None:
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True))


def _emit_status(report: Report, services: SurveybenchServices, accepted: set[str]) -> int:
    services.print_json(report)
    return 0 if report["status"] in accepted else 1


def _run(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.score_survey_task(
        Path(args.task).resolve(),
        Path(args.actual_dir).resolve() if args.actual_dir else None,
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-cli-result-v1",
            "status": report["status"],
            "task_id": report["task_id"],
            "report_path": services.display_path(Path(args.output)),
            "vetoes": report["vetoes"],
            "errors": report["errors"],
        }
    return _emit_status(report, services, {"passed"})


def _local_manifest(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.validate_local_manifest(Path(args.manifest).resolve())
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-local-manifest-cli-result-v1",
            "status": report["status"],
            "report_path": services.display_path(Path(args.output)),
            "issue_count": len(report["issues"]),
        }
    return _emit_status(report, services, {"passed"})


def _replay_call(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.replay_call(
        Path(args.task).resolve(),
        args.endpoint,
        Path(args.session).resolve(),
        request_id=args.request_id,
    )
    return _emit_status(report, services, {"ok", "simulated_rate_limit"})


def _replay_audit(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.validate_replay_fixture_interface(Path(args.task).resolve())
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-online-replay-audit-cli-result-v1",
            "status": report["status"],
            "task_id": report["task_id"],
            "report_path": services.display_path(Path(args.output)),
            "issue_count": report["issue_count"],
        }
    return _emit_status(report, services, {"passed"})


def _replay_transcript(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.build_replay_transcript(
        Path(args.task).resolve(),
        Path(args.session).resolve(),
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-online-replay-transcript-cli-result-v1",
            "status": "passed",
            "task_id": report["task_id"],
            "report_path": services.display_path(Path(args.output)),
            "event_count": report["event_count"],
            "summary": report["summary"],
        }
    services.print_json(report)
    return 0


def _replay_score(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.score_replay_submission(
        Path(args.task).resolve(),
        Path(args.actual_dir).resolve(),
        Path(args.event_log).resolve(),
        Path(args.gold_dir).resolve(),
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-online-replay-score-cli-result-v1",
            "status": report["status"],
            "task_id": report["task_id"],
            "report_path": services.display_path(Path(args.output)),
            "vetoes": report["vetoes"],
            "errors": report["errors"],
        }
    return _emit_status(report, services, {"passed"})


def _score_prose(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.score_survey_prose(
        Path(args.task).resolve(),
        Path(args.actual_dir).resolve(),
        Path(args.event_log).resolve(),
        Path(args.gold_dir).resolve(),
        Path(args.prose).resolve(),
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-survey-prose-score-cli-result-v1",
            "status": report["status"],
            "task_id": report["task_id"],
            "report_path": services.display_path(Path(args.output)),
            "hard_gate_vetoes": report["hard_gate_vetoes"],
            "errors": report["errors"],
        }
    return _emit_status(report, services, {"passed"})


def _restricted_workspace(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.create_restricted_workspace(
        Path(args.repo_root).resolve(),
        Path(args.workspace).resolve(),
        force=args.force,
        profile=args.profile,
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-restricted-workspace-cli-result-v1",
            "status": report["status"],
            "profile_id": report["profile_id"],
            "task_id": report["task_id"],
            "workspace_root": report["workspace_root"],
            "report_path": services.display_path(Path(args.output)),
            "copied_file_count": report["copied_file_count"],
        }
    return _emit_status(report, services, {"passed"})


def _restricted_launcher(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.build_restricted_launcher_dry_run(
        Path(args.workspace).resolve(),
        profile=args.profile,
        subject_agent=args.subject_agent,
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-restricted-launcher-dry-run-cli-result-v1",
            "status": report["status"],
            "dry_run": report["dry_run"],
            "subject_invoked": report["subject_invoked"],
            "profile_id": report["profile_id"],
            "task_id": report["task_id"],
            "workspace_root": report["workspace_root"],
            "report_path": services.display_path(Path(args.output)),
        }
    services.print_json(report)
    return 0 if report["status"] == "prepared_not_launched" and report["subject_invoked"] is False else 1


def _subject_binding(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.build_subject_binding_preflight(
        Path(args.workspace).resolve(),
        profile=args.profile,
        subject_agent=args.subject_agent,
        model_id=args.model_id,
        permission_mode=args.permission_mode,
        subject_transport=args.subject_transport,
        representative_endpoint=args.representative_endpoint,
    )
    if args.output:
        _write_report(args.output, report)
        report = {
            "schema_version": "ra-surveybench-subject-binding-preflight-cli-result-v1",
            "status": report["status"],
            "subject_invoked": report["subject_invoked"],
            "profile_id": report["profile_id"],
            "task_id": report["task_id"],
            "permission_mode": report["permission_mode"],
            "settings_path": report["settings_path"],
            "representative_probe_status": report["representative_probe"]["status"],
            "report_path": services.display_path(Path(args.output)),
            "issue_count": len(report["issues"]),
        }
    services.print_json(report)
    return 0 if report["status"] == "passed" and report["subject_invoked"] is False else 1


def _launch_approval_packet(args: argparse.Namespace, services: SurveybenchServices) -> int:
    dry_run = json.loads(Path(args.launcher_dry_run).read_text())
    wrapper_command = json.loads(args.wrapper_command_json) if args.wrapper_command_json else args.wrapper_command
    if not wrapper_command:
        raise SystemExit("launch-approval-packet requires --wrapper-command-json or --wrapper-command")
    subject_binding_preflight = (
        json.loads(Path(args.subject_binding_preflight).read_text())
        if args.subject_binding_preflight else None
    )
    packet = services.build_launch_approval_packet(
        dry_run,
        subject_agent=args.subject_agent,
        model_id=args.model_id,
        subject_transport=args.subject_transport or (subject_binding_preflight or {}).get("subject_transport", "claude-code"),
        wrapper_command=wrapper_command,
        budget_cap=json.loads(args.budget_cap_json),
        transcript_path=Path(args.transcript_path).resolve(),
        denied_tool_capture_path=Path(args.denied_tool_capture_path).resolve(),
        cli_version=args.cli_version,
        subject_binding_preflight=subject_binding_preflight,
    )
    preflight = services.validate_launch_approval_packet(packet)
    report = {
        "schema_version": "ra-surveybench-launch-approval-packet-cli-result-v1",
        "status": preflight["status"],
        "packet_status": packet["status"],
        "subject_invoked": packet["subject_invoked"],
        "human_approval_granted": preflight["human_approval_granted"],
        "issue_count": len(preflight["issues"]),
        "issues": preflight["issues"],
    }
    if args.output:
        _write_report(args.output, packet)
        report["report_path"] = services.display_path(Path(args.output))
    services.print_json(report)
    return 0 if preflight["status"] == "passed" and packet["subject_invoked"] is False else 1


def _launch_enforcement(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.build_launch_enforcement_preflight(Path(args.approval_packet).resolve())
    if args.output:
        _write_report(args.output, report)
        summary = {
            "schema_version": "ra-surveybench-launch-enforcement-preflight-cli-result-v1",
            "status": report["status"],
            "subject_invoked": report["subject_invoked"],
            "approval_packet_status": report["approval_packet_status"],
            "human_approval_granted": report["human_approval_granted"],
            "report_path": services.display_path(Path(args.output)),
            "issue_count": len(report["issues"]),
        }
        services.print_json(summary)
    else:
        services.print_json(report)
    return 0 if report["status"] == "passed" and report["subject_invoked"] is False else 1


def _scan_helper_report(
    report: Report,
    services: SurveybenchServices,
    *,
    accepted: set[str] | None = None,
) -> int:
    scan = services.scan_subject_helper_payload(report)
    if scan["status"] != "passed":
        report["leak_scan"] = scan
        services.print_json(report)
        return 1
    services.print_json(report)
    return 0 if accepted is None or report["status"] in accepted else 1


def _next_action(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.surveybench_next_action(
        Path(args.task).resolve(),
        Path(args.session).resolve() if args.session else None,
        Path(args.actual_dir).resolve() if args.actual_dir else None,
    )
    return _scan_helper_report(report, services)


def _packet_template(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.surveybench_packet_template(
        Path(args.task).resolve(),
        Path(args.output_dir).resolve() if args.output_dir else None,
        write_files=args.write_files,
    )
    return _scan_helper_report(report, services)


def _packet_compose(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.surveybench_packet_compose(
        Path(args.task).resolve(),
        Path(args.output_dir).resolve(),
        session_dir=Path(args.session).resolve() if args.session else None,
        responses_dir=Path(args.responses_dir).resolve() if args.responses_dir else None,
        write_files=args.write_files,
    )
    return _scan_helper_report(report, services, accepted={"ready"})


def _cluster_hints(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.surveybench_cluster_hints(
        Path(args.task).resolve(),
        Path(args.responses_dir).resolve() if args.responses_dir else None,
    )
    return _scan_helper_report(report, services, accepted={"ready"})


def _ready_for_prose(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.surveybench_ready_for_prose(
        Path(args.task).resolve(),
        Path(args.actual_dir).resolve(),
        Path(args.session).resolve() if args.session else None,
    )
    return _scan_helper_report(report, services, accepted={"ready"})


def _launch_record_template(args: argparse.Namespace, services: SurveybenchServices) -> int:
    report = services.surveybench_launch_record_template(Path(args.task).resolve())
    return _scan_helper_report(report, services)


SURVEYBENCH_ACTION_HANDLERS: Mapping[str, ActionHandler] = MappingProxyType({
    "run": _run,
    "local-manifest": _local_manifest,
    "replay-call": _replay_call,
    "replay-audit": _replay_audit,
    "replay-transcript": _replay_transcript,
    "replay-score": _replay_score,
    "score-prose": _score_prose,
    "restricted-workspace": _restricted_workspace,
    "restricted-launcher-dry-run": _restricted_launcher,
    "subject-binding-preflight": _subject_binding,
    "launch-approval-packet": _launch_approval_packet,
    "launch-enforcement-preflight": _launch_enforcement,
    "next-action": _next_action,
    "packet-template": _packet_template,
    "packet-compose": _packet_compose,
    "cluster-hints": _cluster_hints,
    "ready-for-prose": _ready_for_prose,
    "launch-record-template": _launch_record_template,
})
