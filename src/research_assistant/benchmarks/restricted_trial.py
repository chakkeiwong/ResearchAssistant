from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

RESTRICTED_TRIAL_MANIFEST_SCHEMA_VERSION = "ra-surveybench-restricted-trial-manifest-v1"
RESTRICTED_TRIAL_REPORT_SCHEMA_VERSION = "ra-surveybench-restricted-trial-report-v1"

DEFAULT_TASK_ID = "neural_ot_seed_replay"
DEFAULT_REPLAY_FIXTURE = Path("tests/fixtures/surveybench/online_replay/neural_ot_seed_replay")
DEFAULT_TASK_PATH = DEFAULT_REPLAY_FIXTURE / "neural_ot_seed_replay.task.json"
DEFAULT_PROMPT_PATH = Path("docs/validation/surveybench_online_replay_phase5/agent_trial_prompt_packet_2026-06-29.md")
STRESS_TASK_ID = "neural_ot_seed_ambiguity_partial_frontier_replay"
STRESS_REPLAY_FIXTURE = Path("tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay")
STRESS_TASK_PATH = STRESS_REPLAY_FIXTURE / "neural_ot_seed_ambiguity_partial_frontier_replay.task.json"
STRESS_PROMPT_PATH = Path(
    "docs/validation/surveybench_live_intake_launcher_phase3_restricted_launcher/stress_restricted_launcher_prompt_2026-07-03.md"
)

RESTRICTED_RUNTIME_SOURCE_FILES = (
    Path("src/research_assistant/__init__.py"),
    Path("src/research_assistant/cli.py"),
)


@dataclass(frozen=True)
class RestrictedWorkspaceProfile:
    profile_id: str
    task_id: str
    replay_fixture: Path
    task_path: Path
    prompt_path: Path

    @property
    def allowed_static_paths(self) -> tuple[Path, ...]:
        return (
            Path("pyproject.toml"),
            self.task_path,
            self.prompt_path,
            *RESTRICTED_RUNTIME_SOURCE_FILES,
        )

    @property
    def allowed_static_prefixes(self) -> tuple[Path, ...]:
        return (self.replay_fixture / "responses",)


DEFAULT_RESTRICTED_WORKSPACE_PROFILE = RestrictedWorkspaceProfile(
    profile_id=DEFAULT_TASK_ID,
    task_id=DEFAULT_TASK_ID,
    replay_fixture=DEFAULT_REPLAY_FIXTURE,
    task_path=DEFAULT_TASK_PATH,
    prompt_path=DEFAULT_PROMPT_PATH,
)
STRESS_RESTRICTED_WORKSPACE_PROFILE = RestrictedWorkspaceProfile(
    profile_id=STRESS_TASK_ID,
    task_id=STRESS_TASK_ID,
    replay_fixture=STRESS_REPLAY_FIXTURE,
    task_path=STRESS_TASK_PATH,
    prompt_path=STRESS_PROMPT_PATH,
)
RESTRICTED_WORKSPACE_PROFILES = {
    DEFAULT_TASK_ID: DEFAULT_RESTRICTED_WORKSPACE_PROFILE,
    "default": DEFAULT_RESTRICTED_WORKSPACE_PROFILE,
    STRESS_TASK_ID: STRESS_RESTRICTED_WORKSPACE_PROFILE,
    "stress": STRESS_RESTRICTED_WORKSPACE_PROFILE,
}

ALLOWED_STATIC_PATHS = DEFAULT_RESTRICTED_WORKSPACE_PROFILE.allowed_static_paths
ALLOWED_STATIC_PREFIXES = DEFAULT_RESTRICTED_WORKSPACE_PROFILE.allowed_static_prefixes

FORBIDDEN_PATH_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "scorer_packet",
    "example_output",
    "hidden_gold",
    "gold_packet",
    "negative_packets",
    "expected_outputs",
    "answer_key",
}

FORBIDDEN_PATH_SUBSTRINGS = (
    "score_report",
    "scorer_packet",
    "example_output",
    "hidden_gold",
    "gold_packet",
    "negative_packets",
    "expected_output",
    "expected_outputs",
    "answer_key",
)

FORBIDDEN_TEXT_TOKENS = (
    "scorer_packet",
    "--gold-dir",
    "hidden_gold",
    "gold_packet",
    "expected_outputs",
    "expected_output",
    "answer_key",
)

RESTRICTED_RUNNER_ARG_PREFIX = (
    "-m",
    "research_assistant.cli",
    "surveybench",
    "replay-call",
)

REQUIRED_WORKFLOW_ENDPOINTS = (
    "search",
    "references",
    "citations",
    "adjacent",
    "download-status",
    "source-anchors",
)

PROMPT_REQUIRED_SECTIONS = (
    "## Task",
    "## Allowed Commands",
    "## Required Output Files",
    "## Required Reasoning Discipline",
    "## Non-Claims",
)

PROMPT_REQUIRED_OUTPUT_FILES = (
    "candidate_ledger.json",
    "citation_map.json",
    "source_support.json",
    "claim_support.json",
    "omission_risk.json",
)

RESTRICTED_RUNTIME_SOURCE_ROLES = {
    "src/research_assistant/__init__.py": "generated_restricted_runtime",
    "src/research_assistant/cli.py": "generated_replay_call_cli",
}

RESTRICTED_IMPORT_CLOSURE = tuple(RESTRICTED_RUNTIME_SOURCE_ROLES)

WORKSPACE_MANIFEST_SCHEMA_VERSION = "ra-surveybench-restricted-workspace-visible-manifest-v1"
HARNESS_REPORT_SCHEMA_VERSION = "ra-surveybench-restricted-harness-report-v1"
RUNNER_REPORT_SCHEMA_VERSION = "ra-surveybench-restricted-runner-report-v1"
LAUNCHER_DRY_RUN_SCHEMA_VERSION = "ra-surveybench-restricted-launcher-dry-run-v1"
LAUNCH_APPROVAL_PACKET_SCHEMA_VERSION = "ra-surveybench-launch-approval-packet-v1"
LAUNCH_PREFLIGHT_SCHEMA_VERSION = "ra-surveybench-launch-preflight-v1"
LAUNCH_ENFORCEMENT_PREFLIGHT_SCHEMA_VERSION = "ra-surveybench-launch-enforcement-preflight-v1"
SUBJECT_BINDING_PREFLIGHT_SCHEMA_VERSION = "ra-surveybench-subject-binding-preflight-v1"

SUBJECT_BINDING_EXTRA_ENDPOINTS = (
    "paper",
    "source-status",
    "evidence-context",
)

SUBJECT_TRANSPORT_CLAUDE_CODE = "claude-code"
SUBJECT_TRANSPORT_CODEX_EXEC = "codex-exec"
SUPPORTED_SUBJECT_TRANSPORTS = (
    SUBJECT_TRANSPORT_CLAUDE_CODE,
    SUBJECT_TRANSPORT_CODEX_EXEC,
)

SUBJECT_BINDING_DENIED_TOOL_PATTERNS = (
    "Bash(curl *)",
    "Bash(wget *)",
    "Bash(ssh *)",
    "Bash(scp *)",
    "Bash(rsync *)",
    "Bash(git *)",
    "Bash(pip *)",
    "Bash(python -m pip *)",
    "Bash(sudo *)",
    "Bash(chmod *)",
    "Bash(chown *)",
    "Bash(rm *)",
)

FIXED_FAILURE_CLASSES: dict[str, dict[str, str]] = {
    "boundary_leakage": {"action": "zero_tolerance_stop_unless_repaired_before_handoff"},
    "runtime_escape": {"action": "zero_tolerance_stop_unless_runner_contract_repaired"},
    "environment_leakage": {"action": "zero_tolerance_stop_unless_environment_contract_repaired"},
    "semantic_parity_mismatch": {"action": "stop_unless_repaired_without_weakening_oracle"},
    "event_log_trust": {"action": "zero_tolerance_stop_unless_event_log_trust_repaired"},
    "scorer_boundary": {"action": "zero_tolerance_stop_unless_scorer_remains_outside_workspace"},
    "prompt_contamination": {"action": "zero_tolerance_stop_unless_prompt_repaired_and_rescanned"},
    "implementation_error": {"action": "bounded_local_repair"},
    "test_regression": {"action": "bounded_local_repair"},
    "external_agent_boundary": {"action": "stop_for_human_direction_without_new_reviewed_plan"},
}

SENSITIVE_ENV_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r".*TOKEN.*",
        r".*KEY.*",
        r".*SECRET.*",
        r".*CREDENTIAL.*",
        r".*PASSWORD.*",
        r".*PROXY.*",
        r"AWS_.*",
        r"GOOGLE_.*",
        r"GCLOUD_.*",
        r"GCP_.*",
        r"AZURE_.*",
        r"ANTHROPIC_.*",
        r"OPENAI_.*",
        r"GITHUB_.*",
    )
)


@dataclass(frozen=True)
class RestrictedRunnerContract:
    workspace_root: Path
    python_executable: Path = Path(sys.executable)

    @property
    def source_root(self) -> Path:
        return self.workspace_root / "src"

    @property
    def runtime_root(self) -> Path:
        return self.workspace_root / ".ra_restricted_runtime"

    @property
    def home(self) -> Path:
        return self.runtime_root / "home"

    @property
    def tmpdir(self) -> Path:
        return self.runtime_root / "tmp"

    @property
    def xdg_cache_home(self) -> Path:
        return self.runtime_root / "xdg-cache"

    @property
    def xdg_config_home(self) -> Path:
        return self.runtime_root / "xdg-config"

    @property
    def xdg_data_home(self) -> Path:
        return self.runtime_root / "xdg-data"

    def command_for_replay_call(self, *, task: Path, endpoint: str, session: Path) -> list[str]:
        return [
            str(self.python_executable.resolve()),
            *RESTRICTED_RUNNER_ARG_PREFIX,
            "--task",
            str(task),
            "--endpoint",
            endpoint,
            "--session",
            str(session),
        ]


def resolve_restricted_workspace_profile(profile: str | RestrictedWorkspaceProfile | None = None) -> RestrictedWorkspaceProfile:
    if isinstance(profile, RestrictedWorkspaceProfile):
        return profile
    key = profile or DEFAULT_TASK_ID
    try:
        return RESTRICTED_WORKSPACE_PROFILES[key]
    except KeyError as exc:
        raise ValueError(f"unknown restricted workspace profile {profile!r}") from exc


def path_allowed_for_restricted_workspace(path: Path, *, profile: str | RestrictedWorkspaceProfile | None = None) -> bool:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    normalized = _normalize_relative(path)
    if path_forbidden_for_restricted_workspace(normalized):
        return False
    if normalized in resolved_profile.allowed_static_paths:
        return True
    return any(_is_relative_to(normalized, prefix) for prefix in resolved_profile.allowed_static_prefixes)


def path_forbidden_for_restricted_workspace(path: Path) -> bool:
    normalized = _normalize_relative(path)
    parts = {part.lower() for part in normalized.parts}
    if parts & FORBIDDEN_PATH_PARTS:
        return True
    lowered = normalized.as_posix().lower()
    return any(token in lowered for token in FORBIDDEN_PATH_SUBSTRINGS)


def forbidden_tokens_in_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({token for token in FORBIDDEN_TEXT_TOKENS if token.lower() in lowered})


def build_restricted_child_environment(
    workspace_root: Path,
    parent_env: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    workspace_root = workspace_root.resolve()
    parent_env = dict(parent_env or os.environ)
    python_executable = Path(sys.executable).resolve()
    standard_dirs = ("/usr/local/bin", "/usr/bin", "/bin")
    path_dirs = [str(python_executable.parent), *standard_dirs]
    env = {
        "PATH": os.pathsep.join(dict.fromkeys(path_dirs)),
        "PYTHONPATH": str(workspace_root / "src"),
        "HOME": str(workspace_root / ".ra_restricted_runtime" / "home"),
        "TMPDIR": str(workspace_root / ".ra_restricted_runtime" / "tmp"),
        "XDG_CACHE_HOME": str(workspace_root / ".ra_restricted_runtime" / "xdg-cache"),
        "XDG_CONFIG_HOME": str(workspace_root / ".ra_restricted_runtime" / "xdg-config"),
        "XDG_DATA_HOME": str(workspace_root / ".ra_restricted_runtime" / "xdg-data"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": parent_env.get("LANG", "C.UTF-8"),
        "LC_ALL": parent_env.get("LC_ALL", "C.UTF-8"),
    }
    omitted = [name for name in parent_env if name not in env]
    sensitive_omitted = [name for name in omitted if env_name_is_sensitive(name)]
    manifest = {
        "schema_version": "ra-surveybench-restricted-runner-env-v1",
        "allowed_keys": sorted(env),
        "python_executable": str(python_executable),
        "path_policy": "fixed_minimal",
        "pythonpath_policy": "workspace_src_only",
        "sensitive_omission_count": len(sensitive_omitted),
        "sensitive_omission_categories": sorted({_env_category(name) for name in sensitive_omitted}),
        "omitted_key_count": len(omitted),
    }
    return env, manifest


def env_name_is_sensitive(name: str) -> bool:
    return any(pattern.fullmatch(name) for pattern in SENSITIVE_ENV_PATTERNS)


def runner_command_allowed(argv: list[str], workspace_root: Path, *, cwd: Path | None = None) -> bool:
    if len(argv) < 10:
        return False
    python_executable = Path(argv[0])
    if not python_executable.is_absolute():
        return False
    if tuple(argv[1:5]) != RESTRICTED_RUNNER_ARG_PREFIX:
        return False
    try:
        task_index = argv.index("--task")
        endpoint_index = argv.index("--endpoint")
        session_index = argv.index("--session")
    except ValueError:
        return False
    if task_index + 1 >= len(argv) or endpoint_index + 1 >= len(argv) or session_index + 1 >= len(argv):
        return False
    endpoint = argv[endpoint_index + 1]
    if endpoint not in REQUIRED_WORKFLOW_ENDPOINTS and endpoint not in {"paper", "source-status", "evidence-context"}:
        return False
    workspace_root = workspace_root.resolve()
    if cwd is not None and cwd.resolve() != workspace_root:
        return False
    return _path_resolves_inside(Path(argv[task_index + 1]), workspace_root) and _path_resolves_inside(
        Path(argv[session_index + 1]),
        workspace_root,
    )


def validate_restricted_manifest_payload(
    payload: dict[str, Any],
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    issues: list[dict[str, Any]] = []
    if payload.get("schema_version") != RESTRICTED_TRIAL_MANIFEST_SCHEMA_VERSION:
        issues.append(_issue("wrong_schema_version", "restricted trial manifest schema mismatch", "$.schema_version"))
    copied_files = payload.get("copied_files")
    if not isinstance(copied_files, list):
        issues.append(_issue("copied_files_not_list", "copied_files must be a list", "$.copied_files"))
        copied_files = []
    for index, entry in enumerate(copied_files):
        _validate_copied_entry(entry, index, issues, profile=resolved_profile)
    required_sections = (
        "forbidden_patterns",
        "runner_contract",
        "source_slice",
        "pinned_artifacts",
        "prompt_contract",
        "scan_coverage",
        "failure_classes",
        "parity_oracle",
        "negative_detector_cases",
    )
    for key in required_sections:
        if key not in payload:
            issues.append(_issue("missing_manifest_section", f"missing manifest section {key}", f"$.{key}"))
    _validate_failure_classes(payload.get("failure_classes"), issues)
    _validate_negative_cases(payload.get("negative_detector_cases"), issues)
    _validate_source_slice(payload.get("source_slice"), issues)
    _validate_prompt_contract(payload.get("prompt_contract"), issues)
    status = "passed" if not issues else "failed"
    return {
        "schema_version": RESTRICTED_TRIAL_REPORT_SCHEMA_VERSION,
        "status": status,
        "issues": issues,
    }


def scan_path_escape(root: Path) -> list[dict[str, str]]:
    root = root.resolve()
    issues: list[dict[str, str]] = []
    if not root.exists():
        return [{"code": "scan_root_missing", "path": str(root)}]
    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        if path.is_symlink():
            issues.append({"code": "symlink_escape_risk", "path": rel.as_posix()})
            continue
        try:
            resolved = path.resolve()
        except OSError:
            issues.append({"code": "path_resolve_failed", "path": rel.as_posix()})
            continue
        if not _is_relative_to(resolved, root):
            issues.append({"code": "resolved_path_escape", "path": rel.as_posix()})
        try:
            stat = path.stat()
        except OSError:
            continue
        if path.is_file() and stat.st_nlink > 1:
            issues.append({"code": "hardlink_escape_risk", "path": rel.as_posix()})
    return issues


def normalize_replay_call_for_parity(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _drop_keys(payload, {"event_log_path"})
    if isinstance(normalized.get("response"), dict):
        normalized["response"] = _drop_keys(normalized["response"], {"event_log_path"})
    return normalized


def compare_replay_call_parity(restricted: dict[str, Any], unrestricted: dict[str, Any]) -> dict[str, Any]:
    restricted_norm = normalize_replay_call_for_parity(restricted)
    unrestricted_norm = normalize_replay_call_for_parity(unrestricted)
    mismatches: list[dict[str, Any]] = []
    for key in ("schema_version", "status", "task_id", "endpoint", "request_id", "response"):
        if restricted_norm.get(key) != unrestricted_norm.get(key):
            mismatches.append({
                "code": "semantic_parity_mismatch",
                "field": key,
                "restricted": restricted_norm.get(key),
                "unrestricted": unrestricted_norm.get(key),
            })
    for budget_key in ("budget_before", "budget_after"):
        if restricted_norm.get(budget_key) != unrestricted_norm.get(budget_key):
            mismatches.append({
                "code": "semantic_parity_mismatch",
                "field": budget_key,
            })
    return {
        "schema_version": "ra-surveybench-restricted-parity-report-v1",
        "status": "passed" if not mismatches else "failed",
        "mismatches": mismatches,
        "tolerated_diffs": [
            "absolute paths under session/workspace roots",
            "timestamps if introduced later",
            "temporary run ids",
            "same-session sequence offsets",
            "JSON object key ordering",
        ],
        "boundary_checks": [
            "visible_file_set",
            "visible_env_key_set",
            "command_shape",
            "import_closure",
            "no_outside_artifact_access",
        ],
    }


def validate_agent_prompt_text(text: str, *, profile: str | RestrictedWorkspaceProfile | None = None) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    issues: list[dict[str, Any]] = []
    for section in PROMPT_REQUIRED_SECTIONS:
        if section not in text:
            issues.append(_issue("prompt_section_missing", f"missing prompt section {section}", "$"))
    for filename in PROMPT_REQUIRED_OUTPUT_FILES:
        if filename not in text:
            issues.append(_issue("prompt_output_missing", f"missing required output file {filename}", "$"))
    forbidden_tokens = forbidden_tokens_in_text(text)
    if forbidden_tokens:
        issues.append(_issue("prompt_forbidden_token", f"forbidden prompt tokens: {forbidden_tokens}", "$"))
    command_lines = [
        line.strip()
        for line in text.splitlines()
        if "research_assistant.cli surveybench" in line
    ]
    if not command_lines:
        issues.append(_issue("prompt_missing_replay_commands", "prompt must include replay-call commands", "$.commands"))
    for index, line in enumerate(command_lines):
        if " replay-call " not in f" {line} ":
            issues.append(_issue("prompt_disallowed_command", "prompt command must be replay-call only", f"$.commands[{index}]"))
        if str(resolved_profile.task_path) not in line:
            issues.append(_issue("prompt_wrong_task_path", "prompt command must use the replay task path", f"$.commands[{index}]"))
        if "replay-score" in line or "local-manifest" in line or "run " in line:
            issues.append(_issue("prompt_disallowed_command", "prompt exposes non-replay-call command", f"$.commands[{index}]"))
    return {
        "schema_version": "ra-surveybench-restricted-prompt-contract-report-v1",
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


def create_restricted_workspace(
    repo_root: Path,
    workspace_root: Path,
    *,
    force: bool = False,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    repo_root = repo_root.resolve()
    workspace_root = workspace_root.resolve()
    if workspace_root.exists():
        if not force:
            raise FileExistsError(f"restricted workspace already exists: {workspace_root}")
        if workspace_root == repo_root or repo_root in workspace_root.parents:
            raise ValueError("refusing to remove a workspace inside the source repository")
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True)

    copied_entries: list[dict[str, Any]] = []
    for rel_path in (
        Path("pyproject.toml"),
        resolved_profile.task_path,
        resolved_profile.prompt_path,
    ):
        copied_entries.append(_copy_allowed_file(repo_root, workspace_root, rel_path, profile=resolved_profile))
    responses_root = repo_root / resolved_profile.replay_fixture / "responses"
    for src_path in sorted(responses_root.glob("*.json")):
        copied_entries.append(_copy_allowed_file(repo_root, workspace_root, src_path.relative_to(repo_root), profile=resolved_profile))

    copied_entries.extend(_write_generated_runtime(workspace_root))
    _write_visible_workspace_manifest(workspace_root, copied_entries, profile=resolved_profile)

    manifest = build_contract_manifest_template(workspace_root, profile=resolved_profile)
    manifest["copied_files"] = copied_entries
    manifest["pinned_artifacts"]["task_sha256"] = file_digest(repo_root / resolved_profile.task_path)
    manifest["pinned_artifacts"]["prompt_sha256"] = file_digest(repo_root / resolved_profile.prompt_path)
    contract_report = validate_restricted_manifest_payload(manifest, profile=resolved_profile)
    prompt_report = validate_agent_prompt_text((repo_root / resolved_profile.prompt_path).read_text(), profile=resolved_profile)
    escape_issues = scan_path_escape(workspace_root)
    token_issues = scan_forbidden_tokens(workspace_root)
    report = {
        "schema_version": HARNESS_REPORT_SCHEMA_VERSION,
        "status": "passed"
        if contract_report["status"] == "passed" and prompt_report["status"] == "passed" and not escape_issues and not token_issues
        else "failed",
        "profile_id": resolved_profile.profile_id,
        "task_id": resolved_profile.task_id,
        "workspace_root": str(workspace_root),
        "task_path": str(workspace_root / resolved_profile.task_path),
        "prompt_path": str(workspace_root / resolved_profile.prompt_path),
        "visible_manifest_path": str(workspace_root / ".ra_restricted_workspace_manifest.json"),
        "copied_file_count": len(copied_entries),
        "contract_report": contract_report,
        "prompt_report": prompt_report,
        "escape_issues": escape_issues,
        "forbidden_token_issues": token_issues,
        "copied_files": copied_entries,
        "what_is_not_concluded": [
            "real agent usability",
            "adversarial sandbox isolation",
            "live web coverage",
            "evaluator scoring success",
        ],
    }
    return report


def run_restricted_replay_call(
    workspace_root: Path,
    endpoint: str,
    *,
    session_dir: Path | None = None,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    workspace_root = workspace_root.resolve()
    contract = RestrictedRunnerContract(workspace_root)
    session_dir = (workspace_root / "session") if session_dir is None else session_dir.resolve()
    task_path = workspace_root / resolved_profile.task_path
    argv = contract.command_for_replay_call(task=task_path, endpoint=endpoint, session=session_dir)
    if not runner_command_allowed(argv, workspace_root, cwd=workspace_root):
        return {
            "schema_version": RUNNER_REPORT_SCHEMA_VERSION,
            "status": "failed",
            "failure_class": "runtime_escape",
            "issues": [{"code": "runner_command_not_allowed", "message": "runner command failed allowlist"}],
        }
    for runtime_dir in (
        contract.home,
        contract.tmpdir,
        contract.xdg_cache_home,
        contract.xdg_config_home,
        contract.xdg_data_home,
        workspace_root / ".ra_restricted_runtime" / "stdout",
        workspace_root / ".ra_restricted_runtime" / "stderr",
    ):
        runtime_dir.mkdir(parents=True, exist_ok=True)
    env, env_manifest = build_restricted_child_environment(workspace_root)
    stdout_path = workspace_root / ".ra_restricted_runtime" / "stdout" / f"{endpoint}.stdout.json"
    stderr_path = workspace_root / ".ra_restricted_runtime" / "stderr" / f"{endpoint}.stderr.txt"
    completed = subprocess.run(
        argv,
        cwd=workspace_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    payload: dict[str, Any] | None = None
    parse_issue = None
    if completed.stdout.strip():
        try:
            import json

            payload = json.loads(completed.stdout)
        except ValueError as exc:
            parse_issue = str(exc)
    runner_manifest = {
        "schema_version": RUNNER_REPORT_SCHEMA_VERSION,
        "status": "passed" if completed.returncode in {0, 1} and parse_issue is None else "failed",
        "argv": argv,
        "cwd": str(workspace_root),
        "returncode": completed.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "env_manifest": env_manifest,
        "payload": payload,
        "parse_issue": parse_issue,
    }
    manifest_path = workspace_root / ".ra_restricted_runtime" / f"runner_{endpoint}.json"
    manifest_path.write_text(_json_dumps(runner_manifest))
    return runner_manifest


def run_restricted_parity_smoke(repo_root: Path, workspace_root: Path, endpoints: Iterable[str] = REQUIRED_WORKFLOW_ENDPOINTS) -> dict[str, Any]:
    from research_assistant.benchmarks.replay import replay_call

    repo_root = repo_root.resolve()
    workspace_root = workspace_root.resolve()
    profile = profile_from_restricted_workspace(workspace_root)
    reports = []
    for endpoint in endpoints:
        restricted = run_restricted_replay_call(
            workspace_root,
            endpoint,
            session_dir=workspace_root / ".ra_restricted_runtime" / "restricted_parity" / endpoint,
            profile=profile,
        )
        unrestricted_session = workspace_root / ".ra_restricted_runtime" / "unrestricted_parity" / endpoint
        unrestricted = replay_call(repo_root / profile.task_path, endpoint, unrestricted_session)
        parity = compare_replay_call_parity(restricted.get("payload") or {}, unrestricted)
        boundary = {
            "visible_file_set": _visible_file_set(workspace_root),
            "visible_env_key_set": restricted.get("env_manifest", {}).get("allowed_keys", []),
            "command_shape": restricted.get("argv", [])[1:5],
            "import_closure": list(RESTRICTED_IMPORT_CLOSURE),
            "no_outside_artifact_access": not scan_path_escape(workspace_root),
        }
        reports.append({
            "endpoint": endpoint,
            "runner_status": restricted["status"],
            "parity": parity,
            "boundary": boundary,
        })
    status = "passed" if all(row["runner_status"] == "passed" and row["parity"]["status"] == "passed" for row in reports) else "failed"
    return {
        "schema_version": "ra-surveybench-restricted-parity-smoke-report-v1",
        "status": status,
        "profile_id": profile.profile_id,
        "task_id": profile.task_id,
        "reports": reports,
    }


def build_subject_binding_allowed_bash_patterns(
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> list[str]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    workspace_root = workspace_root.resolve()
    endpoints = (*REQUIRED_WORKFLOW_ENDPOINTS, *SUBJECT_BINDING_EXTRA_ENDPOINTS)
    session_targets = (
        "trial_session",
        "trial_session/*",
        ".claude_surveybench_sessions/*",
        "./trial_session",
        "./trial_session/*",
        "./.claude_surveybench_sessions/*",
        str(workspace_root / "trial_session"),
        str(workspace_root / "trial_session" / "*"),
        str(workspace_root / ".claude_surveybench_sessions" / "*"),
    )
    patterns: list[str] = []
    for endpoint in endpoints:
        for session_target in session_targets:
            patterns.append(
                "Bash(PYTHONPATH=src python -m research_assistant.cli surveybench "
                f"replay-call --task {resolved_profile.task_path.as_posix()} "
                f"--endpoint {endpoint} --session {session_target})"
            )
    return list(dict.fromkeys(patterns))


def build_subject_wrapper_command_template(
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
    subject_transport: str = SUBJECT_TRANSPORT_CLAUDE_CODE,
    model_id: str = "claude-sonnet-4-6",
    permission_mode: str = "dontAsk",
) -> list[str]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    workspace_root = workspace_root.resolve()
    prompt_path = resolved_profile.prompt_path
    if subject_transport == SUBJECT_TRANSPORT_CLAUDE_CODE:
        return [
            "claude",
            "--bare",
            "--no-session-persistence",
            "--permission-mode",
            permission_mode,
            "--settings",
            str(workspace_root / "governance" / "claude_subject_settings.json"),
            "--setting-sources",
            "project",
            "--model",
            "<model-id>",
            "-p",
            "<restricted-prompt-file>",
        ]
    if subject_transport == SUBJECT_TRANSPORT_CODEX_EXEC:
        return [
            "codex",
            "--ask-for-approval",
            "never",
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            "workspace-write",
            "--cd",
            str(workspace_root),
            "--skip-git-repo-check",
            "--json",
            "--model",
            model_id,
            "--output-last-message",
            str(workspace_root / "governance" / "codex_subject_last_message.md"),
            "<restricted-prompt-file>",
        ]
    raise ValueError(f"unsupported subject transport {subject_transport!r}")


def build_subject_binding_file_tool_patterns(workspace_root: Path) -> list[str]:
    workspace_root = workspace_root.resolve()
    output_dir = workspace_root / "agent_output"
    governance_dir = workspace_root / "governance"
    sessions_dir = workspace_root / ".claude_surveybench_sessions"
    trial_session_dir = workspace_root / "trial_session"
    return [
        f"Read({workspace_root}/pyproject.toml)",
        f"Read({workspace_root}/docs/validation/surveybench_live_intake_launcher_phase3_restricted_launcher/stress_restricted_launcher_prompt_2026-07-03.md)",
        f"Read({workspace_root}/tests/fixtures/surveybench/online_replay/*/*.task.json)",
        f"Read({trial_session_dir}/event_log.json)",
        f"Read({sessions_dir}/*/event_log.json)",
        f"LS({workspace_root})",
        f"LS({output_dir})",
        f"LS({trial_session_dir})",
        f"LS({sessions_dir})",
        f"Glob({output_dir}/*.json)",
        f"Glob({trial_session_dir}/*.json)",
        f"Glob({sessions_dir}/*/*.json)",
        f"Grep({output_dir}/*.json)",
        f"Write({output_dir}/*.json)",
        f"Write({trial_session_dir}/*.json)",
        f"Write({sessions_dir}/*/*.json)",
        f"Write({governance_dir}/trial_record.json)",
        f"Edit({output_dir}/*.json)",
        f"MultiEdit({output_dir}/*.json)",
    ]


def build_subject_settings_payload(
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
    permission_mode: str = "dontAsk",
) -> dict[str, Any]:
    allowed = [
        *build_subject_binding_file_tool_patterns(workspace_root),
        *build_subject_binding_allowed_bash_patterns(workspace_root, profile=profile),
    ]
    return {
        "permissions": {
            "defaultMode": permission_mode,
            "allow": allowed,
            "deny": list(SUBJECT_BINDING_DENIED_TOOL_PATTERNS),
        }
    }


def validate_subject_settings_payload(
    payload: dict[str, Any],
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
    permission_mode: str = "dontAsk",
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    resolved_profile = resolve_restricted_workspace_profile(profile)
    issues: list[dict[str, Any]] = []
    permissions = payload.get("permissions")
    if not isinstance(permissions, dict):
        issues.append(_issue("permissions_missing", "settings payload must contain permissions", "$.permissions"))
        permissions = {}
    if permissions.get("defaultMode") != permission_mode:
        issues.append(_issue("permission_mode_mismatch", f"defaultMode must be {permission_mode!r}", "$.permissions.defaultMode"))
    allowed = permissions.get("allow")
    deny = permissions.get("deny")
    if not isinstance(allowed, list) or not all(isinstance(item, str) and item for item in allowed):
        issues.append(_issue("allowed_tools_invalid", "permissions.allow must be a list of strings", "$.permissions.allow"))
        allowed = []
    if not isinstance(deny, list) or not all(isinstance(item, str) and item for item in deny):
        issues.append(_issue("denied_tools_invalid", "permissions.deny must be a list of strings", "$.permissions.deny"))
        deny = []
    for tool in ("Read", "Write", "Edit", "MultiEdit", "LS", "Glob", "Grep"):
        if tool in allowed:
            issues.append(_issue("unbounded_file_tool_allowed", f"{tool} must be path-qualified", "$.permissions.allow"))
    required_file_prefixes = ("Read(", "Write(", "LS(", "Glob(")
    for prefix in required_file_prefixes:
        if not any(item.startswith(prefix) for item in allowed):
            issues.append(_issue("file_tool_pattern_missing", f"missing path-qualified {prefix[:-1]} pattern", "$.permissions.allow"))
    required_endpoint_tokens = set(REQUIRED_WORKFLOW_ENDPOINTS)
    allowed_bash = [item for item in allowed if item.startswith("Bash(")]
    allowed_file_patterns = [item for item in allowed if re.match(r"^(Read|Write|Edit|MultiEdit|LS|Glob|Grep)\(", item)]
    for item in allowed_file_patterns:
        _validate_subject_file_tool_pattern(item, workspace_root, issues)
    for endpoint in required_endpoint_tokens:
        if not any("replay-call" in item and f"--endpoint {endpoint}" in item for item in allowed_bash):
            issues.append(_issue("endpoint_not_allowed", f"missing allowed replay-call pattern for {endpoint}", "$.permissions.allow"))
    broad_shell_markers = (
        "Bash(*)",
        "Bash(python *)",
        "Bash(PYTHONPATH=src python *)",
        "Bash(bash *)",
        "Bash(sh *)",
        "Bash(*)",
    )
    for item in allowed_bash:
        if item in broad_shell_markers:
            issues.append(_issue("broad_bash_allowed", f"broad Bash allow pattern is not permitted: {item}", "$.permissions.allow"))
        if "--session *" in item:
            issues.append(_issue("unbounded_session_allowed", f"replay-call session path must be bounded to the workspace: {item}", "$.permissions.allow"))
        if "surveybench" in item and "replay-call" not in item:
            issues.append(_issue("non_replay_surveybench_allowed", f"surveybench Bash allow must be replay-call only: {item}", "$.permissions.allow"))
        if any(token in item for token in ("curl", "wget", "ssh", "scp", "rsync", "pip ", "sudo", "git ")):
            issues.append(_issue("live_or_mutating_bash_allowed", f"disallowed shell surface appears in allow: {item}", "$.permissions.allow"))
        if "replay-call" in item and resolved_profile.task_path.as_posix() not in item and str(workspace_root / resolved_profile.task_path) not in item:
            issues.append(_issue("wrong_task_in_allowed_command", "replay-call allow pattern must bind the visible task path", "$.permissions.allow"))
    denied_joined = "\n".join(deny)
    for token in ("curl", "wget", "ssh", "scp", "rsync", "pip", "sudo"):
        if token not in denied_joined:
            issues.append(_issue("missing_denied_tool", f"deny list must include {token}", "$.permissions.deny"))
    return {
        "schema_version": "ra-surveybench-subject-settings-validation-v1",
        "status": "passed" if not issues else "failed",
        "profile_id": resolved_profile.profile_id,
        "task_id": resolved_profile.task_id,
        "permission_mode": permission_mode,
        "allowed_tool_count": len(allowed),
        "denied_tool_count": len(deny),
        "issues": issues,
    }


def _validate_subject_file_tool_pattern(item: str, workspace_root: Path, issues: list[dict[str, Any]]) -> None:
    match = re.fullmatch(r"(Read|Write|Edit|MultiEdit|LS|Glob|Grep)\((.+)\)", item)
    if not match:
        issues.append(_issue("file_tool_pattern_invalid", f"invalid file tool pattern: {item}", "$.permissions.allow"))
        return
    tool = match.group(1)
    raw_pattern = match.group(2)
    lowered = raw_pattern.lower()
    if any(token in lowered for token in FORBIDDEN_PATH_SUBSTRINGS):
        issues.append(_issue("forbidden_file_tool_path", f"file tool pattern exposes forbidden path token: {item}", "$.permissions.allow"))
    if "/responses/" in lowered or lowered.endswith("/responses") or "/responses/*" in lowered:
        issues.append(_issue("response_file_tool_path_forbidden", f"file tools must not bypass replay-call responses: {item}", "$.permissions.allow"))
    concrete_prefix = raw_pattern.split("*", 1)[0]
    if concrete_prefix.endswith("/"):
        concrete_prefix = concrete_prefix[:-1]
    if concrete_prefix:
        try:
            inside = _path_resolves_inside(Path(concrete_prefix), workspace_root)
        except RuntimeError:
            inside = False
        if not inside:
            issues.append(_issue("file_tool_path_outside_workspace", f"file tool pattern must stay inside workspace: {item}", "$.permissions.allow"))
    write_roots = (
        workspace_root / "agent_output",
        workspace_root / "trial_session",
        workspace_root / ".claude_surveybench_sessions",
        workspace_root / "governance" / "trial_record.json",
    )
    if tool in {"Write", "Edit", "MultiEdit"}:
        concrete = Path(concrete_prefix)
        if not any(_path_resolves_inside(concrete, root) or concrete == root for root in write_roots):
            issues.append(_issue("write_tool_path_not_bounded", f"write/edit tool pattern must stay in output/session governance-safe paths: {item}", "$.permissions.allow"))


def build_subject_binding_preflight(
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
    subject_agent: str = "claude-code-sonnet-subject",
    model_id: str = "claude-sonnet-4-6",
    permission_mode: str = "dontAsk",
    subject_transport: str = SUBJECT_TRANSPORT_CLAUDE_CODE,
    representative_endpoint: str = "search",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    workspace_root = workspace_root.resolve()
    governance_root = workspace_root / "governance"
    governance_root.mkdir(parents=True, exist_ok=True)
    normalized_permission_mode = permission_mode
    if subject_transport == SUBJECT_TRANSPORT_CODEX_EXEC:
        normalized_permission_mode = None
    settings_path: Path | None = None
    settings_payload: dict[str, Any] | None = None
    settings_validation: dict[str, Any]
    if subject_transport == SUBJECT_TRANSPORT_CLAUDE_CODE:
        settings_path = governance_root / "claude_subject_settings.json"
        settings_payload = build_subject_settings_payload(
            workspace_root,
            profile=resolved_profile,
            permission_mode=permission_mode,
        )
        settings_path.write_text(_json_dumps(settings_payload))
        settings_validation = validate_subject_settings_payload(
            settings_payload,
            workspace_root,
            profile=resolved_profile,
            permission_mode=permission_mode,
        )
    elif subject_transport == SUBJECT_TRANSPORT_CODEX_EXEC:
        settings_validation = {
            "schema_version": "ra-surveybench-subject-settings-validation-v1",
            "status": "not_applicable",
            "profile_id": resolved_profile.profile_id,
            "task_id": resolved_profile.task_id,
            "permission_mode": None,
            "allowed_tool_count": 0,
            "denied_tool_count": 0,
            "issues": [],
        }
    else:
        settings_validation = {
            "schema_version": "ra-surveybench-subject-settings-validation-v1",
            "status": "failed",
            "profile_id": resolved_profile.profile_id,
            "task_id": resolved_profile.task_id,
            "permission_mode": normalized_permission_mode,
            "allowed_tool_count": 0,
            "denied_tool_count": 0,
            "issues": [_issue("subject_transport_unsupported", f"unsupported subject transport {subject_transport!r}", "$.subject_transport")],
        }
    output_dir = (workspace_root / "agent_output") if output_dir is None else output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    representative_session = workspace_root / ".ra_restricted_runtime" / "subject_binding_probe" / representative_endpoint
    representative_probe = run_restricted_replay_call(
        workspace_root,
        representative_endpoint,
        session_dir=representative_session,
        profile=resolved_profile,
    )
    allowed_bash_patterns = build_subject_binding_allowed_bash_patterns(
        workspace_root,
        profile=resolved_profile,
    )
    wrapper_command = build_subject_wrapper_command_template(
        workspace_root,
        profile=resolved_profile,
        subject_transport=subject_transport,
        model_id=model_id,
        permission_mode=permission_mode,
    )
    issues: list[dict[str, Any]] = []
    if settings_validation["status"] != "passed":
        issues.extend(
            _issue(f"settings_{issue['code']}", issue["message"], f"$.settings{issue['path'][1:]}")
            for issue in settings_validation["issues"]
        )
    if representative_probe.get("status") != "passed":
        issues.append(_issue("representative_probe_failed", "representative replay-call probe failed", "$.representative_probe"))
    if subject_transport not in SUPPORTED_SUBJECT_TRANSPORTS:
        issues.append(_issue("subject_transport_unsupported", f"unsupported subject transport {subject_transport!r}", "$.subject_transport"))
    preflight_filename = "subject_binding_preflight.json"
    if subject_transport == SUBJECT_TRANSPORT_CODEX_EXEC:
        preflight_filename = "codex_subject_binding_preflight.json"
    preflight_path = governance_root / preflight_filename
    payload = {
        "schema_version": SUBJECT_BINDING_PREFLIGHT_SCHEMA_VERSION,
        "status": "passed" if not issues else "failed",
        "subject_invoked": False,
        "subject_agent": subject_agent,
        "model_id": model_id,
        "subject_transport": subject_transport,
        "profile_id": resolved_profile.profile_id,
        "task_id": resolved_profile.task_id,
        "workspace_root": str(workspace_root),
        "preflight_path": str(preflight_path),
        "settings_path": str(settings_path) if settings_path is not None else None,
        "settings_sha256": file_digest(settings_path) if settings_path is not None else None,
        "settings_validation": settings_validation,
        "permission_mode": normalized_permission_mode,
        "wrapper_command_kind": "codex_exec" if subject_transport == SUBJECT_TRANSPORT_CODEX_EXEC else "claude_cli",
        "wrapper_command_template": wrapper_command,
        "allowed_file_tool_patterns": build_subject_binding_file_tool_patterns(workspace_root),
        "allowed_bash_patterns": allowed_bash_patterns,
        "denied_tool_patterns": list(SUBJECT_BINDING_DENIED_TOOL_PATTERNS),
        "representative_probe": {
            "endpoint": representative_endpoint,
            "status": representative_probe.get("status"),
            "returncode": representative_probe.get("returncode"),
            "event_log_path": representative_probe.get("payload", {}).get("event_log_path")
            if isinstance(representative_probe.get("payload"), dict)
            else None,
            "stdout_path": representative_probe.get("stdout_path"),
            "stderr_path": representative_probe.get("stderr_path"),
        },
        "issues": issues,
        "what_is_not_concluded": [
            "real subject launched",
            "future subject will complete replay workflow",
            "survey quality",
            "live web coverage",
            "scientific correctness",
        ],
    }
    preflight_path.write_text(_json_dumps(payload))
    return payload


def run_detector_negative_cases(workspace_root: Path) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    boundary_report = forbidden_tokens_in_text("This leak mentions scorer_packet.")
    env, env_manifest = build_restricted_child_environment(
        workspace_root,
        {"PATH": "/ambient/bin", "PYTHONPATH": "/ambient/src", "OPENAI_API_KEY": "secret"},
    )
    disallowed = [sys.executable, "-m", "research_assistant.cli", "surveybench", "replay-score"]
    parity = compare_replay_call_parity({"status": "ok", "response": {"result_count": 2}}, {"status": "ok", "response": {"result_count": 1}})
    cases = {
        "boundary_leakage": bool(boundary_report),
        "runner_policy": not runner_command_allowed(disallowed, workspace_root, cwd=workspace_root)
        and "OPENAI_API_KEY" not in env
        and env_manifest["sensitive_omission_count"] == 1,
        "semantic_parity_mismatch": parity["status"] == "failed",
    }
    return {
        "schema_version": "ra-surveybench-restricted-negative-detector-report-v1",
        "status": "passed" if all(cases.values()) else "failed",
        "cases": cases,
    }


def build_restricted_launcher_dry_run(
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
    subject_agent: str = "<unlaunched-subject-agent>",
    output_dir: Path | None = None,
    session_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    workspace_root = workspace_root.resolve()
    task_path = workspace_root / resolved_profile.task_path
    prompt_path = workspace_root / resolved_profile.prompt_path
    output_dir = (workspace_root / "agent_output") if output_dir is None else output_dir.resolve()
    session_dir = (workspace_root / "trial_session") if session_dir is None else session_dir.resolve()
    manifest_path = workspace_root / ".ra_restricted_workspace_manifest.json"
    env, env_manifest = build_restricted_child_environment(workspace_root)
    command_templates = [
        [
            "python",
            "-m",
            "research_assistant.cli",
            "surveybench",
            "replay-call",
            "--task",
            str(resolved_profile.task_path),
            "--endpoint",
            endpoint,
            "--session",
            "<session-dir>",
        ]
        for endpoint in (
            "search",
            "paper",
            "references",
            "citations",
            "adjacent",
            "download-status",
            "source-status",
            "source-anchors",
            "evidence-context",
        )
    ]
    stop_conditions = [
        "explicit human real-subject launch approval is absent",
        "reviewed non-interactive subject wrapper/settings are absent",
        "exact model id or CLI version cannot be recorded before launch",
        "budget cap cannot be enforced by an authoritative mechanism",
        "workspace isolation or artifact hashes are missing",
        "offline/no-network attestation is absent or false",
        "hidden evaluator material appears in subject-visible context",
        "subject needs a post-start human hint",
        "subject requests evaluator-only material",
        "live/API/download/credential use would be required",
    ]
    return {
        "schema_version": LAUNCHER_DRY_RUN_SCHEMA_VERSION,
        "status": "prepared_not_launched",
        "dry_run": True,
        "subject_invoked": False,
        "subject_agent": subject_agent,
        "profile_id": resolved_profile.profile_id,
        "task_id": resolved_profile.task_id,
        "workspace_root": str(workspace_root),
        "cwd_policy": "restricted_workspace_only",
        "repo_root_not_provided_to_subject": True,
        "task_path": str(task_path),
        "prompt_path": str(prompt_path),
        "restricted_workspace_manifest_path": str(manifest_path),
        "task_sha256": file_digest(task_path) if task_path.exists() else None,
        "prompt_sha256": file_digest(prompt_path) if prompt_path.exists() else None,
        "restricted_workspace_manifest_sha256": file_digest(manifest_path) if manifest_path.exists() else None,
        "output_packet_dir": str(output_dir),
        "event_log_path": str(session_dir / "event_log.json"),
        "allowed_command_templates": command_templates,
        "allowed_env_keys": env_manifest["allowed_keys"],
        "sensitive_env_policy": "omit_and_count_by_category",
        "sensitive_omission_count": env_manifest["sensitive_omission_count"],
        "network_policy": "offline_replay_only_no_live_api_download_or_credentials",
        "manual_hint_policy": "post_start_human_hints_forbidden",
        "stop_conditions": stop_conditions,
        "forbidden_actions": [
            "launch a real subject process",
            "run live web search",
            "download papers or source archives",
            "use credentials",
            "read scorer_packet, negative_packets, hidden_gold, expected_outputs, or answer keys",
            "run replay-score or score-prose",
        ],
        "what_is_not_concluded": [
            "launch approval",
            "real subject reliability",
            "validated blindness under execution",
            "product readiness",
            "survey-quality improvement",
            "scientific correctness",
        ],
    }


def build_launch_approval_packet(
    launcher_dry_run: dict[str, Any],
    *,
    subject_agent: str,
    model_id: str,
    subject_transport: str = SUBJECT_TRANSPORT_CLAUDE_CODE,
    wrapper_command: list[str],
    budget_cap: dict[str, int],
    transcript_path: Path,
    denied_tool_capture_path: Path,
    cli_version: str,
    subject_binding_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a concrete approval packet without launching the subject."""

    binding = subject_binding_preflight or {}
    packet = {
        "schema_version": LAUNCH_APPROVAL_PACKET_SCHEMA_VERSION,
        "status": "pending_human_approval",
        "subject_invoked": False,
        "source_launcher_schema_version": launcher_dry_run.get("schema_version"),
        "source_launcher_status": launcher_dry_run.get("status"),
        "profile_id": launcher_dry_run.get("profile_id"),
        "task_id": launcher_dry_run.get("task_id"),
        "workspace_root": launcher_dry_run.get("workspace_root"),
        "task_path": launcher_dry_run.get("task_path"),
        "prompt_path": launcher_dry_run.get("prompt_path"),
        "restricted_workspace_manifest_path": launcher_dry_run.get("restricted_workspace_manifest_path"),
        "task_sha256": launcher_dry_run.get("task_sha256"),
        "prompt_sha256": launcher_dry_run.get("prompt_sha256"),
        "restricted_workspace_manifest_sha256": launcher_dry_run.get("restricted_workspace_manifest_sha256"),
        "subject_agent": subject_agent,
        "model_id": model_id,
        "subject_transport": subject_transport,
        "wrapper_command": wrapper_command,
        "cli_version": cli_version,
        "subject_binding_preflight": {
            "schema_version": binding.get("schema_version"),
            "status": binding.get("status"),
            "subject_invoked": binding.get("subject_invoked"),
            "profile_id": binding.get("profile_id"),
            "task_id": binding.get("task_id"),
            "preflight_path": binding.get("preflight_path"),
            "settings_path": binding.get("settings_path"),
            "settings_sha256": binding.get("settings_sha256"),
            "permission_mode": binding.get("permission_mode"),
            "subject_transport": binding.get("subject_transport"),
            "representative_probe_status": (binding.get("representative_probe") or {}).get("status")
            if isinstance(binding.get("representative_probe"), dict)
            else None,
            "wrapper_command_template": binding.get("wrapper_command_template"),
            "allowed_bash_pattern_count": len(binding.get("allowed_bash_patterns") or []),
            "denied_tool_pattern_count": len(binding.get("denied_tool_patterns") or []),
        },
        "budget_cap": budget_cap,
        "runtime_enforcement": {
            "schema_version": "ra-surveybench-runtime-enforcement-v1",
            "preflight_scope": "packet_completeness_not_launch_readiness",
            "wrapper_command_role": "subject_invocation_template_only",
            "budget_cap_kind": "declared_launch_limit",
            "budget_mechanically_enforced_by_packet_preflight": False,
            "budget_mechanically_enforced_by_wrapper_command": False,
            "budget_enforcement_required_before_phase3": True,
            "subject_tool_network_policy": "offline_replay_only_no_live_api_download_or_credentials",
            "subject_tool_network_mechanically_enforced_by_packet_preflight": bool(
                binding.get("status") == "passed"
                and binding.get("subject_invoked") is False
                and (
                    (binding.get("subject_transport") == SUBJECT_TRANSPORT_CLAUDE_CODE and binding.get("permission_mode") == "dontAsk")
                    or binding.get("subject_transport") == SUBJECT_TRANSPORT_CODEX_EXEC
                )
            ),
            "subject_tool_permission_binding_required_before_phase3": True,
            "model_transport_exception": "Claude Code and Codex subject invocation may require model transport; the subject task must not use live web/API/download/credentials.",
            "capture_mechanically_enforced_by_packet_preflight": False,
            "capture_paths_declared": True,
            "phase2_required_evidence": [
                "reviewed wrapper or supervisor mechanism enforcing wall-time budget",
                "reviewed wrapper or supervisor mechanism capturing transcript",
                "reviewed wrapper or supervisor mechanism capturing denied tool attempts",
                "reviewed subject settings/profile binding allowing only offline replay-call commands",
                "local representative replay-call probe under restricted workspace",
                "no-drift check for subject, model, wrapper, workspace, prompt, task, and manifest hashes",
                "human approval that explicitly accepts the enforcement mechanism",
            ],
        },
        "transcript_path": str(transcript_path),
        "denied_tool_capture_path": str(denied_tool_capture_path),
        "output_packet_dir": launcher_dry_run.get("output_packet_dir"),
        "event_log_path": launcher_dry_run.get("event_log_path"),
        "allowed_command_templates": launcher_dry_run.get("allowed_command_templates", []),
        "allowed_env_keys": launcher_dry_run.get("allowed_env_keys", []),
        "network_policy": launcher_dry_run.get("network_policy"),
        "manual_hint_policy": launcher_dry_run.get("manual_hint_policy"),
        "human_launch_approval": {
            "required": True,
            "granted": False,
            "approval_text": "",
            "approved_packet_sha256": "",
        },
        "stop_conditions": launcher_dry_run.get("stop_conditions", []),
        "forbidden_actions": [
            *launcher_dry_run.get("forbidden_actions", []),
            "launch before human_launch_approval.granted is true",
            "change wrapper/model/workspace/budget after approval without a new packet",
        ],
        "what_is_not_concluded": [
            "launch approval",
            "real subject reliability",
            "execution-time blindness",
            "survey quality",
            "scientific correctness",
            "product readiness",
        ],
    }
    preflight = validate_launch_approval_packet(packet)
    packet["preflight_status"] = preflight["status"]
    packet["preflight_issue_count"] = len(preflight["issues"])
    return packet


def validate_launch_approval_packet(packet: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if packet.get("schema_version") != LAUNCH_APPROVAL_PACKET_SCHEMA_VERSION:
        issues.append(_issue("wrong_schema_version", "launch approval packet schema mismatch", "$.schema_version"))
    if packet.get("status") != "pending_human_approval":
        issues.append(_issue("wrong_status", "packet must remain pending_human_approval before launch", "$.status"))
    if packet.get("subject_invoked") is not False:
        issues.append(_issue("subject_invoked", "approval packet must not invoke a subject", "$.subject_invoked"))
    if packet.get("source_launcher_schema_version") != LAUNCHER_DRY_RUN_SCHEMA_VERSION:
        issues.append(_issue("launcher_schema_mismatch", "source launcher must be the restricted dry-run schema", "$.source_launcher_schema_version"))
    if packet.get("source_launcher_status") != "prepared_not_launched":
        issues.append(_issue("launcher_not_prepared", "source launcher must be prepared_not_launched", "$.source_launcher_status"))
    _require_nonempty_str(packet, "subject_agent", issues)
    _require_nonempty_str(packet, "model_id", issues)
    _require_nonempty_str(packet, "subject_transport", issues)
    if packet.get("subject_transport") not in SUPPORTED_SUBJECT_TRANSPORTS:
        issues.append(_issue("subject_transport_unsupported", f"unsupported subject transport {packet.get('subject_transport')!r}", "$.subject_transport"))
    _require_nonempty_str(packet, "cli_version", issues)
    _require_nonempty_str(packet, "workspace_root", issues)
    _require_nonempty_str(packet, "task_path", issues)
    _require_nonempty_str(packet, "prompt_path", issues)
    _require_nonempty_str(packet, "restricted_workspace_manifest_path", issues)
    _require_nonempty_str(packet, "transcript_path", issues)
    _require_nonempty_str(packet, "denied_tool_capture_path", issues)
    workspace_root = packet.get("workspace_root")
    if isinstance(workspace_root, str) and workspace_root:
        for key in (
            "task_path",
            "prompt_path",
            "restricted_workspace_manifest_path",
            "transcript_path",
            "denied_tool_capture_path",
            "output_packet_dir",
            "event_log_path",
        ):
            value = packet.get(key)
            if isinstance(value, str) and value and not _path_resolves_inside(Path(value), Path(workspace_root)):
                issues.append(_issue("path_outside_workspace", f"{key} must resolve inside workspace_root", f"$.{key}"))
    for key in ("task_sha256", "prompt_sha256", "restricted_workspace_manifest_sha256"):
        value = packet.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            issues.append(_issue("missing_sha256", f"{key} must be a sha256 hex digest", f"$.{key}"))
    wrapper_command = packet.get("wrapper_command")
    if not isinstance(wrapper_command, list) or not wrapper_command or not all(isinstance(part, str) and part for part in wrapper_command):
        issues.append(_issue("invalid_wrapper_command", "wrapper_command must be a non-empty list of strings", "$.wrapper_command"))
    else:
        joined = " ".join(wrapper_command).lower()
        transport = packet.get("subject_transport")
        if transport == SUBJECT_TRANSPORT_CLAUDE_CODE:
            if not ("claude" in joined and ("--print" in joined or " -p " in f" {joined} ")):
                issues.append(_issue("wrapper_agent_unclear", "Claude wrapper must identify the subject agent wrapper", "$.wrapper_command"))
        elif transport == SUBJECT_TRANSPORT_CODEX_EXEC:
            if "codex" not in wrapper_command or "exec" not in wrapper_command:
                issues.append(_issue("wrapper_agent_unclear", "Codex wrapper must identify the subject agent wrapper", "$.wrapper_command"))
        else:
            issues.append(_issue("wrapper_agent_unclear", "wrapper_command must identify the subject agent wrapper", "$.wrapper_command"))
    budget_cap = packet.get("budget_cap")
    if not isinstance(budget_cap, dict) or not budget_cap:
        issues.append(_issue("missing_budget_cap", "budget_cap must be a non-empty object", "$.budget_cap"))
    else:
        for key, value in budget_cap.items():
            if not isinstance(key, str) or not isinstance(value, int) or value <= 0:
                issues.append(_issue("invalid_budget_cap", "budget_cap values must be positive integers", f"$.budget_cap.{key}"))
    _validate_runtime_enforcement(packet.get("runtime_enforcement"), issues)
    _validate_subject_binding_packet(packet.get("subject_binding_preflight"), packet, issues)
    binding = packet.get("subject_binding_preflight") if isinstance(packet.get("subject_binding_preflight"), dict) else {}
    if isinstance(binding, dict) and binding.get("subject_transport") != packet.get("subject_transport"):
        issues.append(_issue("subject_transport_mismatch", "subject_binding_preflight.subject_transport must match subject_transport", "$.subject_binding_preflight.subject_transport"))
    if packet.get("network_policy") != "offline_replay_only_no_live_api_download_or_credentials":
        issues.append(_issue("network_policy_not_offline", "network policy must forbid live API/download/credential use", "$.network_policy"))
    if packet.get("manual_hint_policy") != "post_start_human_hints_forbidden":
        issues.append(_issue("manual_hint_policy_missing", "manual hint policy must forbid post-start hints", "$.manual_hint_policy"))
    approval = packet.get("human_launch_approval")
    if not isinstance(approval, dict):
        issues.append(_issue("approval_missing", "human_launch_approval object is required", "$.human_launch_approval"))
    else:
        if approval.get("required") is not True:
            issues.append(_issue("approval_not_required", "human approval must be required", "$.human_launch_approval.required"))
        if approval.get("granted") is not False:
            issues.append(_issue("approval_prematurely_granted", "packet builder cannot grant approval", "$.human_launch_approval.granted"))
    stop_conditions = packet.get("stop_conditions")
    if not isinstance(stop_conditions, list) or not stop_conditions:
        issues.append(_issue("missing_stop_conditions", "stop conditions are required", "$.stop_conditions"))
    forbidden_actions = " ".join(str(item) for item in packet.get("forbidden_actions", []))
    if "launch before human_launch_approval.granted is true" not in forbidden_actions:
        issues.append(_issue("missing_preapproval_launch_forbidden", "preapproval launch must be explicitly forbidden", "$.forbidden_actions"))
    return {
        "schema_version": LAUNCH_PREFLIGHT_SCHEMA_VERSION,
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "subject_invoked": packet.get("subject_invoked") is not False,
        "human_approval_granted": bool(isinstance(packet.get("human_launch_approval"), dict) and packet["human_launch_approval"].get("granted")),
        "what_is_not_concluded": [
            "launch approval",
            "agent reliability",
            "survey quality",
            "scientific correctness",
        ],
    }


def build_launch_enforcement_preflight(packet_path: Path) -> dict[str, Any]:
    import json

    packet_path = packet_path.resolve()
    packet = json.loads(packet_path.read_text())
    packet_report = validate_launch_approval_packet(packet)
    issues: list[dict[str, Any]] = [
        _issue(f"approval_packet_{issue['code']}", issue["message"], f"$.approval_packet{issue['path'][1:]}")
        for issue in packet_report["issues"]
    ]
    workspace_root = Path(str(packet.get("workspace_root", ""))).resolve()
    budget_cap = packet.get("budget_cap") if isinstance(packet.get("budget_cap"), dict) else {}
    wall_time_seconds = budget_cap.get("wall_time_seconds")
    wrapper_command = packet.get("wrapper_command") if isinstance(packet.get("wrapper_command"), list) else []
    resolved_subject_command = _resolve_subject_wrapper_command(wrapper_command, packet)
    if not isinstance(wall_time_seconds, int) or wall_time_seconds <= 0:
        issues.append(_issue("missing_wall_time_budget", "budget_cap.wall_time_seconds must be a positive integer", "$.budget_cap.wall_time_seconds"))
    if not resolved_subject_command:
        issues.append(_issue("missing_subject_command", "subject command could not be resolved", "$.wrapper_command"))
    _validate_subject_command_binding(resolved_subject_command, packet, issues)
    _validate_subject_binding_no_drift(packet.get("subject_binding_preflight"), workspace_root, issues)

    governance_root = workspace_root / "governance"
    transcript_path = Path(str(packet.get("transcript_path", ""))).resolve()
    denied_tool_capture_path = Path(str(packet.get("denied_tool_capture_path", ""))).resolve()
    stderr_path = governance_root / "subject_stderr.txt"
    exit_status_path = governance_root / "subject_exit_status.json"
    no_drift = _launch_packet_no_drift(packet)
    issues.extend(no_drift["issues"])
    for key, path in {
        "transcript_path": transcript_path,
        "denied_tool_capture_path": denied_tool_capture_path,
        "stderr_path": stderr_path,
        "exit_status_path": exit_status_path,
    }.items():
        if not _path_resolves_inside(path, workspace_root):
            issues.append(_issue("capture_path_outside_workspace", f"{key} must resolve inside workspace", f"$.{key}"))

    status = "passed" if not issues else "failed"
    return {
        "schema_version": LAUNCH_ENFORCEMENT_PREFLIGHT_SCHEMA_VERSION,
        "status": status,
        "subject_invoked": False,
        "approval_packet_path": str(packet_path),
        "approval_packet_sha256": file_digest(packet_path),
        "approval_packet_status": packet.get("status"),
        "human_approval_granted": bool(isinstance(packet.get("human_launch_approval"), dict) and packet["human_launch_approval"].get("granted")),
        "workspace_root": str(workspace_root),
        "subject_agent": packet.get("subject_agent"),
        "model_id": packet.get("model_id"),
        "cli_version": packet.get("cli_version"),
        "resolved_subject_command": resolved_subject_command,
        "subject_prompt_delivery": {
            "mode": "prompt_file_content_as_prompt_argument",
            "prompt_file": packet.get("prompt_path"),
            "path_string_is_not_prompt": True,
        },
        "supervisor_execution": {
            "mode": "codex_visible_supervised_subprocess",
            "launch_not_executed_by_preflight": True,
            "wall_time_seconds": wall_time_seconds,
            "timeout_enforcement": "python_subprocess_timeout_on_phase3_launch",
            "stdout_transcript_path": str(transcript_path),
            "stderr_path": str(stderr_path),
            "exit_status_path": str(exit_status_path),
        },
        "capture_contract": {
            "transcript_capture": "stdout_stream_to_transcript_path",
            "stderr_capture": "stderr_stream_to_stderr_path",
            "denied_tool_capture_path": str(denied_tool_capture_path),
            "denied_tool_capture_authoritative": False,
            "denied_tool_capture_limitation": "Claude CLI denied-tool events are not separately exposed by this preflight; Phase 3 must preserve raw transcript/stderr and classify denied attempts from captured logs if present.",
        },
        "subject_task_boundary": {
            "network_policy": packet.get("network_policy"),
            "subject_binding_preflight": packet.get("subject_binding_preflight"),
            "model_transport_exception": packet.get("runtime_enforcement", {}).get("model_transport_exception") if isinstance(packet.get("runtime_enforcement"), dict) else None,
            "live_web_api_download_credential_use_for_task": "forbidden",
            "post_start_human_hints": "forbidden",
        },
        "no_drift": no_drift,
        "issues": issues,
        "what_is_not_concluded": [
            "human launch approval",
            "subject invocation",
            "agent reliability",
            "execution-time blindness",
            "survey quality",
            "scientific correctness",
        ],
    }


def profile_from_restricted_workspace(workspace_root: Path) -> RestrictedWorkspaceProfile:
    manifest_path = workspace_root.resolve() / ".ra_restricted_workspace_manifest.json"
    if not manifest_path.exists():
        return DEFAULT_RESTRICTED_WORKSPACE_PROFILE
    try:
        import json

        payload = json.loads(manifest_path.read_text())
    except ValueError:
        return DEFAULT_RESTRICTED_WORKSPACE_PROFILE
    return resolve_restricted_workspace_profile(payload.get("profile_id") or DEFAULT_TASK_ID)


def scan_forbidden_tokens(root: Path) -> list[dict[str, str]]:
    root = root.resolve()
    issues: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == ".ra_restricted_workspace_manifest.json":
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        masked = _mask_allowed_safety_flags(text)
        hits = forbidden_tokens_in_text(masked)
        if hits:
            issues.append({"code": "forbidden_token", "path": rel, "tokens": ",".join(hits)})
    return issues


def build_contract_manifest_template(
    workspace_root: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> dict[str, Any]:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    return {
        "schema_version": RESTRICTED_TRIAL_MANIFEST_SCHEMA_VERSION,
        "profile_id": resolved_profile.profile_id,
        "task_id": resolved_profile.task_id,
        "workspace_root": str(workspace_root),
        "allowed_static_paths": [path.as_posix() for path in resolved_profile.allowed_static_paths],
        "allowed_static_prefixes": [path.as_posix() for path in resolved_profile.allowed_static_prefixes],
        "forbidden_patterns": {
            "path_parts": sorted(FORBIDDEN_PATH_PARTS),
            "path_substrings": list(FORBIDDEN_PATH_SUBSTRINGS),
            "text_tokens": list(FORBIDDEN_TEXT_TOKENS),
        },
        "runner_contract": {
            "argv_prefix": list(RESTRICTED_RUNNER_ARG_PREFIX),
            "absolute_interpreter_required": True,
            "cwd_policy": "workspace_root",
            "path_policy": "fixed_minimal",
            "pythonpath_policy": "workspace_src_only",
            "sensitive_env_policy": "omit_and_count_by_category",
        },
        "source_slice": {
            "mode": "generated_restricted_runtime",
            "import_closure": list(RESTRICTED_IMPORT_CLOSURE),
            "source_roles": RESTRICTED_RUNTIME_SOURCE_ROLES,
            "forbidden_source_paths": [
                "src/research_assistant/benchmarks/replay.py",
                "src/research_assistant/benchmarks/surveybench.py",
                "src/research_assistant/benchmarks/local_manifest.py",
            ],
        },
        "pinned_artifacts": {
            "task_path": resolved_profile.task_path.as_posix(),
            "prompt_path": resolved_profile.prompt_path.as_posix(),
            "pinning_required": True,
        },
        "prompt_contract": {
            "required_sections": list(PROMPT_REQUIRED_SECTIONS),
            "required_output_files": list(PROMPT_REQUIRED_OUTPUT_FILES),
            "allowed_command": "python -m research_assistant.cli surveybench replay-call",
            "schema_constrained_view_required": True,
        },
        "scan_coverage": [
            "copied_files",
            "redirected_home",
            "redirected_xdg",
            "tmpdir",
            "stdout",
            "stderr",
            "event_logs",
            "session_manifests",
            "replay_outputs",
            "runner_manifests",
            "temp_artifacts",
        ],
        "failure_classes": FIXED_FAILURE_CLASSES,
        "parity_oracle": {
            "compared_fields": [
                "cli_exit_status",
                "schema_version",
                "task_id",
                "endpoint",
                "status",
                "request_id_when_deterministic",
                "response_payload_without_event_log_path",
                "budget_counter_deltas",
                "event_count_increment",
                "event_endpoint_status_result_count",
                "event_log_validation_status",
                "visible_file_set",
                "visible_env_key_set",
                "command_shape",
                "import_closure",
                "no_outside_artifact_access",
            ],
            "tolerated_diffs": [
                "absolute paths under session/workspace roots",
                "timestamps if introduced later",
                "temporary run ids",
                "same-session sequence offsets",
                "JSON object key ordering",
            ],
        },
        "negative_detector_cases": {
            "boundary_leakage": "forbidden evaluator token/path",
            "runner_policy": "disallowed command or sensitive env leak",
            "semantic_parity_mismatch": "altered restricted response",
        },
        "copied_files": [],
    }


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_allowed_file(
    repo_root: Path,
    workspace_root: Path,
    rel_path: Path,
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> dict[str, Any]:
    rel_path = _normalize_relative(rel_path)
    if not path_allowed_for_restricted_workspace(rel_path, profile=profile):
        raise ValueError(f"path is not allowed in restricted workspace: {rel_path}")
    source = repo_root / rel_path
    if source.is_symlink():
        raise ValueError(f"refusing to copy symlink: {rel_path}")
    target = workspace_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    source_stat = source.stat()
    target_stat = target.stat()
    return {
        "relative_path": rel_path.as_posix(),
        "source_sha256": file_digest(source),
        "copied_sha256": file_digest(target),
        "is_symlink": target.is_symlink(),
        "hardlink_count": target_stat.st_nlink,
        "source_inode": source_stat.st_ino,
        "copied_inode": target_stat.st_ino,
        "source_kind": RESTRICTED_RUNTIME_SOURCE_ROLES.get(rel_path.as_posix(), "copied_static_artifact"),
    }


def _write_generated_runtime(workspace_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    files = {
        Path("src/research_assistant/__init__.py"): '"""Restricted SurveyBench replay-call runtime."""\n',
        Path("src/research_assistant/cli.py"): _restricted_cli_source(),
    }
    for rel_path, text in files.items():
        target = workspace_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        stat = target.stat()
        entries.append({
            "relative_path": rel_path.as_posix(),
            "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "copied_sha256": file_digest(target),
            "is_symlink": target.is_symlink(),
            "hardlink_count": stat.st_nlink,
            "source_inode": None,
            "copied_inode": stat.st_ino,
            "source_kind": RESTRICTED_RUNTIME_SOURCE_ROLES[rel_path.as_posix()],
        })
    return entries


def _write_visible_workspace_manifest(
    workspace_root: Path,
    copied_entries: list[dict[str, Any]],
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> None:
    resolved_profile = resolve_restricted_workspace_profile(profile)
    payload = {
        "schema_version": WORKSPACE_MANIFEST_SCHEMA_VERSION,
        "profile_id": resolved_profile.profile_id,
        "task_id": resolved_profile.task_id,
        "task_path": resolved_profile.task_path.as_posix(),
        "prompt_path": resolved_profile.prompt_path.as_posix(),
        "copied_files": copied_entries,
        "runtime_source_roles": RESTRICTED_RUNTIME_SOURCE_ROLES,
        "what_is_not_included": [
            "scorer packet",
            "evaluator example output",
            "score reports",
            "git metadata",
            "full replay/scorer implementation",
        ],
    }
    (workspace_root / ".ra_restricted_workspace_manifest.json").write_text(_json_dumps(payload))


def _visible_file_set(root: Path) -> list[str]:
    root = root.resolve()
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and ".ra_restricted_runtime" not in path.relative_to(root).parts
        and "__pycache__" not in path.relative_to(root).parts
    )


def _mask_allowed_safety_flags(text: str) -> str:
    text = re.sub(r'"hidden_gold_accessed"\s*:\s*false', '"safety_flag": false', text)
    text = re.sub(r'"hidden_gold_accessed"\s*:\s*False', '"safety_flag": False', text)
    text = re.sub(r"'hidden_gold_accessed'\s*:\s*False", "'safety_flag': False", text)
    return text.replace('event.get("hidden_gold_accessed") is not False', 'event.get("safety_flag") is not False')


def _json_dumps(payload: Any) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True)


def _restricted_cli_source() -> str:
    return r'''from __future__ import annotations

import argparse
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

TASK_SCHEMA = "ra-surveybench-online-replay-task-v1"
EVENT_LOG_SCHEMA = "ra-surveybench-online-replay-event-log-v1"
SESSION_SCHEMA = "ra-surveybench-online-replay-session-v1"
CALL_RESULT_SCHEMA = "ra-surveybench-online-replay-call-result-v1"
RESPONSE_SCHEMA = "ra-surveybench-online-replay-response-v1"

REQUIRED_BUDGET_COUNTERS = (
    "endpoint_calls",
    "returned_records",
    "paper_detail_calls",
    "source_anchor_calls",
    "submit_or_score_attempts",
)

ALLOWED_STATUSES = {
    "ok",
    "blocked_budget",
    "blocked_unknown_endpoint",
    "blocked_invalid_request",
    "simulated_rate_limit",
}


class ReplayCallError(ValueError):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="research_assistant.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    surveybench = sub.add_parser("surveybench")
    surveybench_sub = surveybench.add_subparsers(dest="surveybench_action", required=True)
    replay_call_parser = surveybench_sub.add_parser("replay-call")
    replay_call_parser.add_argument("--task", required=True)
    replay_call_parser.add_argument("--endpoint", required=True)
    replay_call_parser.add_argument("--session", required=True)
    replay_call_parser.add_argument("--request-id")
    args = parser.parse_args(argv)
    if args.command != "surveybench" or args.surveybench_action != "replay-call":
        raise SystemExit("restricted runtime supports only surveybench replay-call")
    result = replay_call(Path(args.task).resolve(), args.endpoint, Path(args.session).resolve(), request_id=args.request_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"ok", "simulated_rate_limit"} else 1


def replay_call(task_path: Path, endpoint: str, session_dir: Path, *, request_id: str | None = None) -> dict[str, Any]:
    task = load_json(task_path)
    validate_task(task)
    session_dir.mkdir(parents=True, exist_ok=True)
    if endpoint not in task["endpoints"]:
        return blocked_response(task_path, task, endpoint, request_id or f"{endpoint}-invalid", session_dir, "blocked_unknown_endpoint", f"unknown replay endpoint {endpoint!r}")
    response_rel = task["endpoints"][endpoint]
    if not isinstance(response_rel, str):
        raise ReplayCallError("restricted replay-call supports path-string endpoints only")
    response = load_json((task_path.parent / response_rel).resolve())
    validate_response(response, task["task_id"], endpoint)
    with event_log_lock(session_dir):
        ensure_session_manifest(task_path, task, session_dir)
        budget_before = current_budget(task, session_dir)
        cost = endpoint_cost(endpoint, response)
        if would_exceed_budget(budget_before, cost):
            return blocked_response(task_path, task, endpoint, request_id or response_request_id(response, endpoint), session_dir, "blocked_budget", "replay budget exhausted for requested endpoint", lock_held=True)
        budget_after = subtract_budget(budget_before, cost)
        event = make_event(str(task["task_id"]), endpoint, request_id or response_request_id(response, endpoint), session_dir, budget_before, budget_after, response_result_count(response), event_status(response))
        append_event(session_dir, str(task["task_id"]), event)
    return {
        "schema_version": CALL_RESULT_SCHEMA,
        "status": event["status"],
        "task_id": task["task_id"],
        "endpoint": endpoint,
        "request_id": event["request_id"],
        "budget_before": budget_before,
        "budget_after": budget_after,
        "event_log_path": str(event_log_path(session_dir)),
        "response": response,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def validate_task(task: dict[str, Any]) -> None:
    if task.get("schema_version") != TASK_SCHEMA:
        raise ReplayCallError("wrong task schema")
    if not isinstance(task.get("task_id"), str):
        raise ReplayCallError("task_id missing")
    if not isinstance(task.get("endpoints"), dict):
        raise ReplayCallError("endpoints missing")
    if not isinstance(task.get("budget"), dict):
        raise ReplayCallError("budget missing")
    for counter in REQUIRED_BUDGET_COUNTERS:
        value = task["budget"].get(counter)
        if not isinstance(value, int) or value < 0:
            raise ReplayCallError(f"invalid budget counter {counter}")


def validate_response(response: dict[str, Any], task_id: str, endpoint: str) -> None:
    if response.get("schema_version") != RESPONSE_SCHEMA:
        raise ReplayCallError("wrong response schema")
    if response.get("task_id") != task_id:
        raise ReplayCallError("response task mismatch")
    if response.get("endpoint") != endpoint:
        raise ReplayCallError("response endpoint mismatch")


def blocked_response(task_path: Path, task: dict[str, Any], endpoint: str, request_id: str, session_dir: Path, status: str, message: str, *, lock_held: bool = False) -> dict[str, Any]:
    if lock_held:
        ensure_session_manifest(task_path, task, session_dir)
        budget_before = current_budget(task, session_dir)
        event = make_event(str(task["task_id"]), endpoint, request_id, session_dir, budget_before, budget_before, 0, status)
        append_event(session_dir, str(task["task_id"]), event)
    else:
        with event_log_lock(session_dir):
            ensure_session_manifest(task_path, task, session_dir)
            budget_before = current_budget(task, session_dir)
            event = make_event(str(task["task_id"]), endpoint, request_id, session_dir, budget_before, budget_before, 0, status)
            append_event(session_dir, str(task["task_id"]), event)
    return {
        "schema_version": CALL_RESULT_SCHEMA,
        "status": status,
        "task_id": task["task_id"],
        "endpoint": endpoint,
        "request_id": request_id,
        "budget_before": budget_before,
        "budget_after": budget_before,
        "event_log_path": str(event_log_path(session_dir)),
        "response": {
            "schema_version": RESPONSE_SCHEMA,
            "task_id": task["task_id"],
            "endpoint": endpoint,
            "request_id": request_id,
            "status": status,
            "message": message,
        },
    }


def make_event(task_id: str, endpoint: str, request_id: str, session_dir: Path, budget_before: dict[str, int], budget_after: dict[str, int], result_count: int, status: str) -> dict[str, Any]:
    return {
        "sequence": next_sequence(session_dir),
        "task_id": task_id,
        "endpoint": endpoint,
        "request_id": request_id,
        "budget_before": budget_before,
        "budget_after": budget_after,
        "result_count": result_count,
        "status": status,
        "agent_visible": True,
        "hidden_gold_accessed": False,
    }


def event_log_path(session_dir: Path) -> Path:
    return session_dir / "event_log.json"


def session_manifest_path(session_dir: Path) -> Path:
    return session_dir / "session_manifest.json"


def ensure_session_manifest(task_path: Path, task: dict[str, Any], session_dir: Path) -> None:
    path = session_manifest_path(session_dir)
    manifest = {
        "schema_version": SESSION_SCHEMA,
        "task_id": task["task_id"],
        "task_sha256": sha256_file(task_path),
        "generated_by": "research_assistant.benchmarks.replay.replay_call",
    }
    if path.exists():
        existing = load_json(path)
        if existing != manifest:
            raise ReplayCallError("session manifest mismatch")
        return
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))


@contextmanager
def event_log_lock(session_dir: Path):
    session_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = session_dir / ".event_log.lock"
    deadline = time.monotonic() + 5.0
    while True:
        try:
            lock_dir.mkdir()
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise ReplayCallError(f"timed out waiting for event log lock: {lock_dir}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock_dir.rmdir()
        except FileNotFoundError:
            pass


def load_event_log(session_dir: Path, task_id: str) -> dict[str, Any]:
    path = event_log_path(session_dir)
    if not path.exists():
        return {"schema_version": EVENT_LOG_SCHEMA, "task_id": task_id, "session_manifest": "session_manifest.json", "events": []}
    payload = load_json(path)
    validate_event_log(payload, task_id)
    return payload


def validate_event_log(payload: dict[str, Any], task_id: str) -> None:
    if payload.get("schema_version") != EVENT_LOG_SCHEMA or payload.get("task_id") != task_id:
        raise ReplayCallError("event log identity mismatch")
    if payload.get("session_manifest") != "session_manifest.json":
        raise ReplayCallError("event log missing session manifest reference")
    events = payload.get("events")
    if not isinstance(events, list):
        raise ReplayCallError("event log events must be a list")
    for event in events:
        if event.get("status") not in ALLOWED_STATUSES:
            raise ReplayCallError("invalid event status")
        if event.get("agent_visible") is not True:
            raise ReplayCallError("event must be agent visible")
        if event.get("hidden_gold_accessed") is not False:
            raise ReplayCallError("event safety flag must be false")
        validate_budget(event.get("budget_before"))
        validate_budget(event.get("budget_after"))


def validate_budget(value: Any) -> None:
    if not isinstance(value, dict):
        raise ReplayCallError("budget must be an object")
    for counter in REQUIRED_BUDGET_COUNTERS:
        if not isinstance(value.get(counter), int):
            raise ReplayCallError(f"missing budget counter {counter}")


def append_event(session_dir: Path, task_id: str, event: dict[str, Any]) -> None:
    log = load_event_log(session_dir, task_id)
    log["events"].append(event)
    validate_event_log(log, task_id)
    event_log_path(session_dir).write_text(json.dumps(log, indent=2, sort_keys=True))


def next_sequence(session_dir: Path) -> int:
    path = event_log_path(session_dir)
    if not path.exists():
        return 1
    events = load_json(path).get("events", [])
    return len(events) + 1 if isinstance(events, list) else 1


def current_budget(task: dict[str, Any], session_dir: Path) -> dict[str, int]:
    budget = {counter: int(task["budget"][counter]) for counter in REQUIRED_BUDGET_COUNTERS}
    path = event_log_path(session_dir)
    if not path.exists():
        return budget
    events = load_json(path).get("events", [])
    if not events:
        return budget
    return {counter: int(events[-1]["budget_after"][counter]) for counter in REQUIRED_BUDGET_COUNTERS}


def endpoint_cost(endpoint: str, response: dict[str, Any]) -> dict[str, int]:
    cost = {counter: 0 for counter in REQUIRED_BUDGET_COUNTERS}
    cost["endpoint_calls"] = 1
    cost["returned_records"] = response_result_count(response)
    if endpoint == "paper":
        cost["paper_detail_calls"] = cost["returned_records"]
    if endpoint in {"source-anchors", "evidence-context"}:
        cost["source_anchor_calls"] = cost["returned_records"]
    return cost


def would_exceed_budget(budget: dict[str, int], cost: dict[str, int]) -> bool:
    return any(budget[counter] - cost[counter] < 0 for counter in REQUIRED_BUDGET_COUNTERS)


def subtract_budget(budget: dict[str, int], cost: dict[str, int]) -> dict[str, int]:
    return {counter: budget[counter] - cost[counter] for counter in REQUIRED_BUDGET_COUNTERS}


def response_result_count(response: dict[str, Any]) -> int:
    if isinstance(response.get("result_count"), int):
        return int(response["result_count"])
    for key in ("results", "records", "references", "citations", "adjacent_candidates", "statuses", "anchors", "contexts"):
        value = response.get(key)
        if isinstance(value, list):
            return len(value)
    return 1


def response_request_id(response: dict[str, Any], endpoint: str) -> str:
    value = response.get("request_id")
    return value if isinstance(value, str) and value else f"{endpoint}-request"


def event_status(response: dict[str, Any]) -> str:
    statuses = response.get("source_statuses")
    if isinstance(statuses, list):
        for status in statuses:
            if isinstance(status, dict) and status.get("status") == "simulated_rate_limit":
                return "simulated_rate_limit"
    return "ok"


def sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _validate_copied_entry(
    entry: Any,
    index: int,
    issues: list[dict[str, Any]],
    *,
    profile: str | RestrictedWorkspaceProfile | None = None,
) -> None:
    path = f"$.copied_files[{index}]"
    if not isinstance(entry, dict):
        issues.append(_issue("copied_entry_not_object", "copied file entry must be an object", path))
        return
    rel = entry.get("relative_path")
    if not isinstance(rel, str) or not rel:
        issues.append(_issue("missing_relative_path", "copied file entry needs relative_path", path))
        return
    rel_path = Path(rel)
    if not path_allowed_for_restricted_workspace(rel_path, profile=profile):
        issues.append(_issue("copied_path_not_allowed", f"copied path is not allowed: {rel}", f"{path}.relative_path"))
    for key in ("source_sha256", "copied_sha256"):
        value = entry.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            issues.append(_issue("missing_sha256", f"{key} must be a sha256 hex digest", f"{path}.{key}"))
    if entry.get("is_symlink") is not False:
        issues.append(_issue("symlink_not_allowed", "copied file must not be a symlink", f"{path}.is_symlink"))
    if entry.get("hardlink_count", 1) != 1:
        issues.append(_issue("hardlink_not_allowed", "copied file must not have multiple hardlinks", f"{path}.hardlink_count"))
    role = RESTRICTED_RUNTIME_SOURCE_ROLES.get(rel)
    if role and entry.get("source_kind") != role:
        issues.append(_issue("runtime_source_role_mismatch", f"{rel} must be {role}", f"{path}.source_kind"))


def _validate_failure_classes(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("failure_classes_missing", "failure_classes must be an object", "$.failure_classes"))
        return
    missing = sorted(set(FIXED_FAILURE_CLASSES) - set(value))
    if missing:
        issues.append(_issue("failure_classes_incomplete", f"missing failure classes: {missing}", "$.failure_classes"))
    for name, contract in FIXED_FAILURE_CLASSES.items():
        actual = value.get(name)
        if not isinstance(actual, dict) or actual.get("action") != contract["action"]:
            issues.append(_issue("failure_class_action_mismatch", f"wrong action for {name}", f"$.failure_classes.{name}"))


def _validate_negative_cases(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("negative_cases_missing", "negative_detector_cases must be an object", "$.negative_detector_cases"))
        return
    required = {"boundary_leakage", "runner_policy", "semantic_parity_mismatch"}
    missing = sorted(required - set(value))
    if missing:
        issues.append(_issue("negative_cases_incomplete", f"missing negative detector cases: {missing}", "$.negative_detector_cases"))


def _validate_source_slice(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("source_slice_missing", "source_slice must be an object", "$.source_slice"))
        return
    closure = value.get("import_closure")
    if tuple(closure or ()) != RESTRICTED_IMPORT_CLOSURE:
        issues.append(_issue("source_slice_import_closure_mismatch", "import closure must match restricted runtime files", "$.source_slice.import_closure"))
    roles = value.get("source_roles")
    if roles != RESTRICTED_RUNTIME_SOURCE_ROLES:
        issues.append(_issue("source_slice_roles_mismatch", "source roles must be exact", "$.source_slice.source_roles"))
    forbidden = set(value.get("forbidden_source_paths", []) if isinstance(value.get("forbidden_source_paths"), list) else [])
    if "src/research_assistant/benchmarks/replay.py" not in forbidden:
        issues.append(_issue("source_slice_forbidden_paths_incomplete", "full replay.py must be forbidden from copied source slice", "$.source_slice.forbidden_source_paths"))


def _validate_prompt_contract(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("prompt_contract_missing", "prompt_contract must be an object", "$.prompt_contract"))
        return
    if tuple(value.get("required_sections", [])) != PROMPT_REQUIRED_SECTIONS:
        issues.append(_issue("prompt_contract_sections_mismatch", "prompt required sections mismatch", "$.prompt_contract.required_sections"))
    if tuple(value.get("required_output_files", [])) != PROMPT_REQUIRED_OUTPUT_FILES:
        issues.append(_issue("prompt_contract_outputs_mismatch", "prompt required output files mismatch", "$.prompt_contract.required_output_files"))
    if value.get("schema_constrained_view_required") is not True:
        issues.append(_issue("prompt_contract_not_schema_constrained", "prompt contract must require schema-constrained view", "$.prompt_contract.schema_constrained_view_required"))


def _normalize_relative(path: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        raise ValueError(f"restricted trial paths must be relative: {path}")
    return Path(path.as_posix().lstrip("./"))


def _path_resolves_inside(path: Path, root: Path) -> bool:
    try:
        return _is_relative_to(path.resolve(), root.resolve())
    except OSError:
        return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _drop_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: _drop_keys(item, keys) for key, item in value.items() if key not in keys}
    if isinstance(value, list):
        return [_drop_keys(item, keys) for item in value]
    return value


def _env_category(name: str) -> str:
    upper = name.upper()
    for category in ("TOKEN", "KEY", "SECRET", "CREDENTIAL", "PASSWORD", "PROXY", "AWS", "GOOGLE", "GCLOUD", "GCP", "AZURE", "ANTHROPIC", "OPENAI", "GITHUB"):
        if category in upper:
            return category
    return "OTHER"


def _issue(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def _require_nonempty_str(packet: dict[str, Any], key: str, issues: list[dict[str, Any]]) -> None:
    value = packet.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(_issue("missing_required_field", f"{key} must be a non-empty string", f"$.{key}"))


def _validate_runtime_enforcement(value: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("missing_runtime_enforcement", "runtime_enforcement object is required", "$.runtime_enforcement"))
        return
    expected_literals = {
        "schema_version": "ra-surveybench-runtime-enforcement-v1",
        "preflight_scope": "packet_completeness_not_launch_readiness",
        "wrapper_command_role": "subject_invocation_template_only",
        "budget_cap_kind": "declared_launch_limit",
        "subject_tool_network_policy": "offline_replay_only_no_live_api_download_or_credentials",
    }
    for key, expected in expected_literals.items():
        if value.get(key) != expected:
            issues.append(_issue("runtime_enforcement_literal_mismatch", f"{key} must be {expected!r}", f"$.runtime_enforcement.{key}"))
    expected_false = (
        "budget_mechanically_enforced_by_packet_preflight",
        "budget_mechanically_enforced_by_wrapper_command",
        "capture_mechanically_enforced_by_packet_preflight",
    )
    for key in expected_false:
        if value.get(key) is not False:
            issues.append(_issue("runtime_enforcement_overclaim", f"{key} must be false before Phase 2 evidence", f"$.runtime_enforcement.{key}"))
    if not isinstance(value.get("subject_tool_network_mechanically_enforced_by_packet_preflight"), bool):
        issues.append(_issue(
            "runtime_enforcement_literal_mismatch",
            "subject_tool_network_mechanically_enforced_by_packet_preflight must be a boolean",
            "$.runtime_enforcement.subject_tool_network_mechanically_enforced_by_packet_preflight",
        ))
    expected_true = (
        "budget_enforcement_required_before_phase3",
        "subject_tool_permission_binding_required_before_phase3",
        "capture_paths_declared",
    )
    for key in expected_true:
        if value.get(key) is not True:
            issues.append(_issue("runtime_enforcement_missing_gate", f"{key} must be true", f"$.runtime_enforcement.{key}"))
    evidence = value.get("phase2_required_evidence")
    if not isinstance(evidence, list) or len(evidence) < 4 or not all(isinstance(item, str) and item for item in evidence):
        issues.append(_issue("runtime_enforcement_evidence_missing", "phase2_required_evidence must list required enforcement evidence", "$.runtime_enforcement.phase2_required_evidence"))


def _validate_subject_binding_packet(value: Any, packet: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append(_issue("subject_binding_missing", "subject_binding_preflight object is required", "$.subject_binding_preflight"))
        return
    transport = value.get("subject_transport")
    expected = {
        "schema_version": SUBJECT_BINDING_PREFLIGHT_SCHEMA_VERSION,
        "status": "passed",
        "subject_invoked": False,
        "representative_probe_status": "passed",
    }
    for key, literal in expected.items():
        if value.get(key) != literal:
            issues.append(_issue("subject_binding_literal_mismatch", f"{key} must be {literal!r}", f"$.subject_binding_preflight.{key}"))
    if transport == SUBJECT_TRANSPORT_CLAUDE_CODE and value.get("permission_mode") != "dontAsk":
        issues.append(_issue("subject_binding_literal_mismatch", "permission_mode must be 'dontAsk' for claude-code transport", "$.subject_binding_preflight.permission_mode"))
    if transport == SUBJECT_TRANSPORT_CODEX_EXEC and value.get("permission_mode") is not None:
        issues.append(_issue("subject_binding_literal_mismatch", "permission_mode must be null for codex-exec transport", "$.subject_binding_preflight.permission_mode"))
    for key in ("preflight_path", "settings_path"):
        item = value.get(key)
        if key == "settings_path" and transport == SUBJECT_TRANSPORT_CODEX_EXEC:
            continue
        if not isinstance(item, str) or not item:
            issues.append(_issue("subject_binding_path_missing", f"{key} must be a non-empty path", f"$.subject_binding_preflight.{key}"))
    settings_sha = value.get("settings_sha256")
    if transport == SUBJECT_TRANSPORT_CLAUDE_CODE:
        if not isinstance(settings_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", settings_sha):
            issues.append(_issue("subject_binding_settings_sha_missing", "settings_sha256 must be a sha256 hex digest", "$.subject_binding_preflight.settings_sha256"))
        if not isinstance(value.get("allowed_bash_pattern_count"), int) or value["allowed_bash_pattern_count"] < len(REQUIRED_WORKFLOW_ENDPOINTS):
            issues.append(_issue("subject_binding_allowed_commands_incomplete", "allowed bash patterns must cover required workflow endpoints", "$.subject_binding_preflight.allowed_bash_pattern_count"))
    elif transport == SUBJECT_TRANSPORT_CODEX_EXEC:
        if settings_sha is not None:
            issues.append(_issue("subject_binding_settings_sha_missing", "codex-exec transport must not bind claude settings hashes", "$.subject_binding_preflight.settings_sha256"))
    if not isinstance(value.get("denied_tool_pattern_count"), int) or value["denied_tool_pattern_count"] < 6:
        issues.append(_issue("subject_binding_denies_incomplete", "denied tool patterns must cover live/mutating shell surfaces", "$.subject_binding_preflight.denied_tool_pattern_count"))
    runtime = packet.get("runtime_enforcement")
    if isinstance(runtime, dict) and runtime.get("subject_tool_network_mechanically_enforced_by_packet_preflight") is True:
        if value.get("status") != "passed" or (transport == SUBJECT_TRANSPORT_CLAUDE_CODE and value.get("permission_mode") != "dontAsk"):
            issues.append(_issue(
                "subject_binding_overclaim",
                "mechanical subject-tool binding claim requires passed dontAsk binding preflight",
                "$.runtime_enforcement.subject_tool_network_mechanically_enforced_by_packet_preflight",
            ))


def _resolve_subject_wrapper_command(wrapper_command: list[Any], packet: dict[str, Any]) -> list[str]:
    if not wrapper_command or not all(isinstance(part, str) and part for part in wrapper_command):
        return []
    prompt_path = str(packet.get("prompt_path", ""))
    resolved: list[str] = []
    for part in wrapper_command:
        if part == "<restricted-prompt-file>":
            try:
                resolved.append(Path(prompt_path).read_text())
            except OSError:
                resolved.append("")
        elif part == "<restricted-prompt-path>":
            resolved.append(prompt_path)
        elif part == "<model-id>":
            resolved.append(str(packet.get("model_id", "")))
        else:
            resolved.append(part)
    return resolved


def _validate_subject_command_binding(command: list[str], packet: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if not command:
        return
    transport = packet.get("subject_transport")
    if transport == SUBJECT_TRANSPORT_CLAUDE_CODE:
        _validate_claude_subject_command_binding(command, packet, issues)
        return
    if transport == SUBJECT_TRANSPORT_CODEX_EXEC:
        _validate_codex_subject_command_binding(command, packet, issues)
        return
    issues.append(_issue("subject_transport_unsupported", f"unsupported subject transport {transport!r}", "$.resolved_subject_command"))


def _validate_claude_subject_command_binding(command: list[str], packet: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if "--dangerously-skip-permissions" in command or "--allow-dangerously-skip-permissions" in command:
        issues.append(_issue("subject_permissions_too_broad", "subject command must not use broad permission bypass", "$.resolved_subject_command"))
    if "--bare" not in command:
        issues.append(_issue("subject_bare_mode_missing", "subject command must use --bare to avoid ambient hooks and memory", "$.resolved_subject_command"))
    if "--no-session-persistence" not in command:
        issues.append(_issue("subject_session_persistence_not_disabled", "subject command must disable session persistence", "$.resolved_subject_command"))
    try:
        permission_index = command.index("--permission-mode")
        permission_mode = command[permission_index + 1]
    except (ValueError, IndexError):
        permission_mode = None
    if permission_mode != "dontAsk":
        issues.append(_issue("subject_permission_mode_not_bound", "subject command must use --permission-mode dontAsk", "$.resolved_subject_command"))
    try:
        settings_index = command.index("--settings")
        settings_path = command[settings_index + 1]
    except (ValueError, IndexError):
        settings_path = None
    binding = packet.get("subject_binding_preflight") if isinstance(packet.get("subject_binding_preflight"), dict) else {}
    expected_settings_path = binding.get("settings_path")
    if not isinstance(settings_path, str) or not settings_path:
        issues.append(_issue("subject_settings_not_bound", "subject command must include --settings <subject settings path>", "$.resolved_subject_command"))
    elif isinstance(expected_settings_path, str) and expected_settings_path and Path(settings_path).resolve() != Path(expected_settings_path).resolve():
        issues.append(_issue("subject_settings_path_mismatch", "subject command settings path must match subject binding preflight", "$.resolved_subject_command"))
    if "--setting-sources" not in command:
        issues.append(_issue("subject_setting_sources_missing", "subject command must bind setting sources", "$.resolved_subject_command"))
    model_id = packet.get("model_id")
    if isinstance(model_id, str) and model_id:
        has_model = any(part == model_id for part in command)
        has_model_flag = any(part in {"--model", "--model-id"} for part in command)
        if not has_model or not has_model_flag:
            issues.append(_issue("subject_model_not_bound", "resolved subject command must include --model and model_id", "$.resolved_subject_command"))
    prompt_path = packet.get("prompt_path")
    if isinstance(prompt_path, str) and prompt_path and prompt_path in command:
        issues.append(_issue("prompt_path_used_as_prompt", "resolved subject command must pass prompt file contents, not only the prompt path string", "$.resolved_subject_command"))


def _validate_codex_subject_command_binding(command: list[str], packet: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if "--dangerously-bypass-approvals-and-sandbox" in command:
        issues.append(_issue("subject_permissions_too_broad", "codex command must not bypass approvals and sandbox", "$.resolved_subject_command"))
    if not command or command[0] != "codex" or "exec" not in command:
        issues.append(_issue("subject_exec_mode_missing", "codex command must use exec mode", "$.resolved_subject_command"))
    if any(flag in command for flag in ("--settings", "--setting-sources", "--permission-mode", "--no-session-persistence", "--bare", "-p")):
        issues.append(_issue("subject_claude_only_flags_present", "codex command must not include claude-only flags", "$.resolved_subject_command"))
    if "--ignore-user-config" not in command:
        issues.append(_issue("subject_config_isolation_missing", "codex command must ignore user config", "$.resolved_subject_command"))
    if "--ignore-rules" not in command:
        issues.append(_issue("subject_rules_isolation_missing", "codex command must ignore user/project rules", "$.resolved_subject_command"))
    if "--ask-for-approval" not in command:
        issues.append(_issue("subject_approval_mode_missing", "codex command must bind approval mode", "$.resolved_subject_command"))
    else:
        try:
            approval_index = command.index("--ask-for-approval")
            approval_mode = command[approval_index + 1]
        except (ValueError, IndexError):
            approval_mode = None
        if approval_mode != "never":
            issues.append(_issue("subject_approval_mode_not_bound", "codex command must use --ask-for-approval never", "$.resolved_subject_command"))
        try:
            exec_index = command.index("exec")
        except ValueError:
            exec_index = -1
        if exec_index != -1 and approval_index > exec_index:
            issues.append(_issue("subject_approval_flag_after_exec", "codex approval mode must be bound before exec for this CLI surface", "$.resolved_subject_command"))
    if "--sandbox" not in command:
        issues.append(_issue("subject_sandbox_missing", "codex command must bind sandbox mode", "$.resolved_subject_command"))
    else:
        try:
            sandbox_index = command.index("--sandbox")
            sandbox_mode = command[sandbox_index + 1]
        except (ValueError, IndexError):
            sandbox_mode = None
        if sandbox_mode != "workspace-write":
            issues.append(_issue("subject_sandbox_mode_not_bound", "codex command must use workspace-write sandbox", "$.resolved_subject_command"))
    if "--cd" not in command:
        issues.append(_issue("subject_cwd_missing", "codex command must bind a workspace cd", "$.resolved_subject_command"))
    else:
        try:
            cd_index = command.index("--cd")
            cd_path = command[cd_index + 1]
        except (ValueError, IndexError):
            cd_path = None
        workspace_root = packet.get("workspace_root")
        if not isinstance(cd_path, str) or not cd_path:
            issues.append(_issue("subject_cwd_missing", "codex command must bind a workspace cd", "$.resolved_subject_command"))
        elif isinstance(workspace_root, str) and workspace_root and Path(cd_path).resolve() != Path(workspace_root).resolve():
            issues.append(_issue("subject_cwd_mismatch", "codex command cd path must match workspace_root", "$.resolved_subject_command"))
    if "--skip-git-repo-check" not in command:
        issues.append(_issue("subject_repo_check_not_disabled", "codex command must skip repo check for workspace lane", "$.resolved_subject_command"))
    if "--output-last-message" not in command:
        issues.append(_issue("subject_output_capture_missing", "codex command must capture the last message", "$.resolved_subject_command"))
    else:
        try:
            output_index = command.index("--output-last-message")
            output_path = command[output_index + 1]
        except (ValueError, IndexError):
            output_path = None
        workspace_root = packet.get("workspace_root")
        if not isinstance(output_path, str) or not output_path:
            issues.append(_issue("subject_output_capture_missing", "codex command must capture the last message", "$.resolved_subject_command"))
        elif isinstance(workspace_root, str) and workspace_root and not _path_resolves_inside(Path(output_path), Path(workspace_root)):
            issues.append(_issue("subject_output_capture_outside_workspace", "codex last-message output must resolve inside workspace_root", "$.resolved_subject_command"))
    if "--model" not in command and "--model-id" not in command:
        issues.append(_issue("subject_model_not_bound", "codex command must bind a model id", "$.resolved_subject_command"))
    if command and command[0] == "claude":
        issues.append(_issue("subject_transport_conflict", "codex subject command must not resolve to a claude cli invocation", "$.resolved_subject_command"))


def _validate_subject_binding_no_drift(value: Any, workspace_root: Path, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        return
    settings_path_raw = value.get("settings_path")
    expected_sha = value.get("settings_sha256")
    if isinstance(settings_path_raw, str) and settings_path_raw:
        settings_path = Path(settings_path_raw)
        if not _path_resolves_inside(settings_path, workspace_root):
            issues.append(_issue("subject_settings_path_outside_workspace", "subject settings path must resolve inside workspace", "$.subject_binding_preflight.settings_path"))
        elif not settings_path.exists():
            issues.append(_issue("subject_settings_missing", "subject settings file does not exist", "$.subject_binding_preflight.settings_path"))
        elif isinstance(expected_sha, str) and re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            actual_sha = file_digest(settings_path)
            if actual_sha != expected_sha:
                issues.append(_issue("subject_settings_hash_drift", "subject settings hash does not match packet", "$.subject_binding_preflight.settings_sha256"))
            try:
                import json

                payload = json.loads(settings_path.read_text())
                validation = validate_subject_settings_payload(payload, workspace_root, profile=value.get("profile_id") or None)
                if validation["status"] != "passed":
                    issues.append(_issue("subject_settings_validation_failed", "subject settings no longer validate", "$.subject_binding_preflight.settings_path"))
            except ValueError:
                issues.append(_issue("subject_settings_json_invalid", "subject settings file is not valid JSON", "$.subject_binding_preflight.settings_path"))
    preflight_path_raw = value.get("preflight_path")
    if isinstance(preflight_path_raw, str) and preflight_path_raw:
        preflight_path = Path(preflight_path_raw)
        if not _path_resolves_inside(preflight_path, workspace_root):
            issues.append(_issue("subject_binding_preflight_path_outside_workspace", "subject binding preflight path must resolve inside workspace", "$.subject_binding_preflight.preflight_path"))
        elif not preflight_path.exists():
            issues.append(_issue("subject_binding_preflight_missing", "subject binding preflight file does not exist", "$.subject_binding_preflight.preflight_path"))
        else:
            try:
                import json

                preflight = json.loads(preflight_path.read_text())
            except ValueError:
                issues.append(_issue("subject_binding_preflight_json_invalid", "subject binding preflight file is not valid JSON", "$.subject_binding_preflight.preflight_path"))
            else:
                if preflight.get("schema_version") != SUBJECT_BINDING_PREFLIGHT_SCHEMA_VERSION or preflight.get("status") != "passed":
                    issues.append(_issue("subject_binding_preflight_not_passed", "subject binding preflight file must be passed", "$.subject_binding_preflight.preflight_path"))
                if preflight.get("settings_sha256") != expected_sha:
                    issues.append(_issue("subject_binding_preflight_settings_mismatch", "subject binding preflight settings hash must match packet", "$.subject_binding_preflight.settings_sha256"))


def _launch_packet_no_drift(packet: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    issues: list[dict[str, Any]] = []
    for key in ("task", "prompt", "restricted_workspace_manifest"):
        path_key = f"{key}_path"
        hash_key = f"{key}_sha256"
        path_value = packet.get(path_key)
        expected = packet.get(hash_key)
        actual = None
        status = "not_checked"
        if isinstance(path_value, str) and path_value and isinstance(expected, str):
            path = Path(path_value)
            if path.exists():
                actual = file_digest(path)
                status = "passed" if actual == expected else "failed"
                if actual != expected:
                    issues.append(_issue("hash_drift", f"{hash_key} does not match current file", f"$.{hash_key}"))
            else:
                status = "failed"
                issues.append(_issue("hash_file_missing", f"{path_key} does not exist", f"$.{path_key}"))
        else:
            status = "failed"
            issues.append(_issue("hash_check_missing", f"{path_key} and {hash_key} are required", f"$.{path_key}"))
        checks[key] = {
            "path": path_value,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "status": status,
        }
    return {
        "schema_version": "ra-surveybench-launch-no-drift-v1",
        "status": "passed" if not issues else "failed",
        "checks": checks,
        "issues": issues,
    }
