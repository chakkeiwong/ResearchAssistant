"""Proportionate offline operational acceptance for the literature-survey workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.mission_state import (
    MissionStateError,
    pretty_json_bytes,
    validate_generation_ancestor_readonly,
)
from research_assistant.survey.m22_representative_missions import (
    DEFAULT_MATRIX_PATH as M22_MATRIX_PATH,
    load_matrix as load_m22_matrix,
    replay_representative_missions,
    run_representative_missions,
)


SCHEMA = "ra-survey-m23-operational-acceptance-v1"
CASE_IDS = (
    "install_and_command_discovery",
    "topic_confirmation_stop",
    "topic_unavailable_stop",
    "explicit_seed_local_skeleton",
    "unchanged_resume",
    "qualitative_assessment_command",
    "m22_report_replay",
    "stale_or_corrupt_rejection",
    "documentation_capability_consistency",
)
COMMAND_IDS = (
    "version",
    "survey_help",
    "assessment_help",
    "import_origin",
    "topic_first",
    "topic_confirmed",
    "seed_first",
    "seed_resume",
    "assessment",
    "m22_replay",
    "m22_tamper",
)
PLAN_PATH = Path(
    "docs/plans/literature_survey_north_star_m23_acceptance_and_operational_closeout_subplan_2026-07-13.md"
)
M22_REPLAY_ROOT = Path("operator_workspace/m22_representative_replay")
DOC_PATHS = (
    Path("README.md"),
    Path("docs/installation.md"),
    Path("docs/quickstart.md"),
    Path("docs/known_limitations.md"),
    Path("docs/support.md"),
    Path("docs/literature_survey_operator_guide.md"),
    Path("docs/plans/reset_memo_2026-07-10.md"),
    Path("docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md"),
)
NONCLAIMS = [
    "literature completeness",
    "scientific truth",
    "live topic-discovery quality",
    "provider reliability",
    "publication safety",
    "publication-ready prose",
    "autonomous expert judgment",
    "public release readiness",
    "native-Windows support",
    "general product readiness",
]


class M23AcceptanceError(RuntimeError):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M23AcceptanceError("invalid_json_artifact", str(path)) from exc
    if not isinstance(value, dict):
        raise M23AcceptanceError("invalid_json_artifact", str(path))
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(value))


def _build_wheel_from_fresh_staging(
    *, repository_root: Path, dist: Path, environment: dict[str, str]
) -> None:
    with tempfile.TemporaryDirectory(prefix="ra-m23-build-") as temporary_directory:
        build_workspace = Path(temporary_directory).resolve(strict=True)
        if build_workspace.is_relative_to(repository_root):
            raise M23AcceptanceError("wheel_build_workspace_inside_repository")
        staged_source = build_workspace / "source"
        staged_source.mkdir()
        for filename in ("pyproject.toml", "README.md"):
            shutil.copy2(repository_root / filename, staged_source / filename)
        shutil.copytree(
            repository_root / "src",
            staged_source / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(dist),
            ],
            cwd=staged_source,
            check=True,
            env=environment,
            capture_output=True,
            timeout=300,
        )


def _normalized_command_stdout(row: dict[str, Any], output_root: Path) -> str:
    raw = (output_root / row["stdout_path"]).read_text(encoding="utf-8")
    return " ".join(raw.split()).replace("- ", "-")


def _resume_lineage_and_state_valid(
    *, seed_first: dict[str, Any], seed_resume: dict[str, Any], output_root: Path
) -> bool:
    try:
        ancestry = validate_generation_ancestor_readonly(
            output_dir=output_root / "operator_workspace" / "seed_mission",
            mission_id=seed_resume["mission_id"],
            mission_fingerprint=seed_resume["mission_fingerprint"],
            generation_id=seed_first["generation_id"],
        )
    except (KeyError, MissionStateError):
        return False
    first_local = seed_first.get("local_supervisor") or {}
    resumed_local = seed_resume.get("local_supervisor") or {}
    return (
        ancestry.get("current_generation_id") == seed_resume.get("generation_id")
        and seed_resume.get("generation_id") != seed_first.get("generation_id")
        and seed_resume.get("status") == seed_first.get("status") == "blocked_at_gate"
        and seed_resume.get("next_action", {}).get("action_id")
        == seed_first.get("next_action", {}).get("action_id")
        == "public_metadata"
        and seed_resume.get("next_action", {}).get("gate_id")
        == seed_first.get("next_action", {}).get("gate_id")
        == "public_metadata"
        and seed_resume.get("phase_statuses") == seed_first.get("phase_statuses")
        and resumed_local.get("status") == first_local.get("status")
        == "terminal_blocked_public_discovery_confirmation"
        and resumed_local.get("terminal_action_id") == first_local.get("terminal_action_id")
        == "public_metadata"
        and resumed_local.get("observation_sha256") == first_local.get("observation_sha256")
        and resumed_local.get("transition_count") == 0
        and resumed_local.get("transition_history") == []
        and resumed_local.get("ready_for_prose") is False
        and seed_resume.get("next_action", {}).get("ready_for_prose") is False
    )


def _m22_open_limitations(repository_root: Path) -> dict[str, Any]:
    matrix = load_m22_matrix(
        repository_root=repository_root,
        matrix_path=repository_root / M22_MATRIX_PATH,
    )
    cases = {row["case_id"]: row for row in matrix["cases"]}
    return {
        "forward_citations": "unavailable_nonblocking",
        "identifier_bearing_rows_open": cases[
            "residual_identifier_bearing_omissions"
        ]["input"]["residual_count"],
        "identifier_free_units_open": cases["identifier_free_omissions"][
            "input"
        ]["unit_count"],
    }


def _replay_m22_with_limitations(
    *, repository_root: Path, output_root: Path
) -> dict[str, Any]:
    result = replay_representative_missions(
        repository_root=repository_root, output_root=output_root
    )
    result["open_limitations"] = _m22_open_limitations(repository_root)
    return result


def _build_and_replay_m22(
    *, repository_root: Path, output_root: Path
) -> dict[str, Any]:
    run_representative_missions(
        repository_root=repository_root,
        matrix_path=repository_root / M22_MATRIX_PATH,
        output_root=output_root,
    )
    return _replay_m22_with_limitations(
        repository_root=repository_root, output_root=output_root
    )


def _m22_replay_code(repository_root: Path, output_root: Path) -> str:
    return (
        "import json; from pathlib import Path; "
        "from research_assistant.survey.m23_operational_acceptance import "
        "_build_and_replay_m22; "
        f"repo=Path({str(repository_root)!r}); root=Path({str(output_root / M22_REPLAY_ROOT)!r}); "
        "result=_build_and_replay_m22(repository_root=repo, output_root=root); "
        "print(json.dumps(result, sort_keys=True))"
    )


def _commands_run_outside_repository(
    rows: list[dict[str, Any]], repository_root: Path
) -> bool:
    root = repository_root.resolve(strict=True)
    return bool(rows) and all(
        isinstance(row.get("cwd"), str)
        and not Path(row["cwd"]).absolute().is_relative_to(root)
        for row in rows
    )


def _offline_subprocess_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["CUDA_VISIBLE_DEVICES"] = "-1"
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return environment


def documentation_consistency_report(repository_root: Path) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    texts = {path.as_posix(): (repository_root / path).read_text(encoding="utf-8") for path in DOC_PATHS}
    operator = texts["docs/literature_survey_operator_guide.md"]
    readme = texts["README.md"]
    install = texts["docs/installation.md"]
    quickstart = texts["docs/quickstart.md"]
    limits = texts["docs/known_limitations.md"]
    support = texts["docs/support.md"]
    reset = texts["docs/plans/reset_memo_2026-07-10.md"]
    master = texts["docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md"]
    pending_close = (
        "PENDING_VERSIONED_CLEAN_CHECKOUT_CLOSE" in master
        and "PENDING_VERSIONED_CLEAN_CHECKOUT_CLOSE" in reset
        and "program is accomplished within recorded local exploratory scope"
        not in reset
    )
    completed_close = (
        "Status: `ACCOMPLISHED_WITHIN_RECORDED_LOCAL_EXPLORATORY_SCOPE`"
        in master
        and "program is accomplished within recorded local exploratory scope"
        in reset
    )
    checks = {
        "readme_documents_topic_and_seed_commands": all(
            value in readme for value in ("run-public-source-workflow", "--seed arxiv:2201.12220v3")
        ),
        "install_documents_offline_isolated_wheel": all(
            value in install for value in ("--no-index --no-deps", "env -u PYTHONPATH")
        ),
        "quickstart_documents_unavailable_topic_terminal": "terminal_blocked_bootstrap_unavailable" in quickstart,
        "operator_documents_arxiv_only_and_no_pdf_fallback": (
            "credential-free arXiv" in operator and "PDF fallback" in operator
        ),
        "operator_documents_assessed_terminal_nonclaim": (
            "ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE" in operator
            and "does not mean truth, completeness, reviewed prose" in operator
        ),
        "limitations_preserve_forward_and_omission_gaps": all(
            value in limits for value in ("Forward-citation coverage is unavailable", "50 identifier-bearing", "195")
        ),
        "support_documents_survey_issue_fields": all(
            value in support for value in ("next_action.action_id", "topic-only or explicit-seed")
        ),
        "master_and_reset_record_one_consistent_close_state": pending_close
        != completed_close,
        "active_docs_do_not_require_openalex": all(
            "OpenAlex" not in text or "not" in text or "out of" in text
            for text in (readme, install, quickstart, operator)
        ),
        "active_docs_do_not_claim_prose_ready": all(
            "ready_for_prose=true" not in text for text in (readme, quickstart, operator, limits)
        ),
    }
    return {
        "schema_version": f"{SCHEMA}-documentation",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "document_hashes": {
            path: _sha(text.encode("utf-8")) for path, text in sorted(texts.items())
        },
        "what_is_not_concluded": NONCLAIMS,
    }


def capability_matrix() -> dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA}-capabilities",
        "rows": [
            {"capability": "topic_only_mission_identity", "status": "implemented_local", "limit": "live default bootstrap unavailable"},
            {"capability": "explicit_seed_local_skeleton", "status": "implemented_local", "limit": "stops before public metadata without confirmation"},
            {"capability": "new_mission_public_scope", "status": "arxiv_only", "limit": "no OpenAlex, credentials, or PDF fallback"},
            {"capability": "qualitative_assessment", "status": "implemented_nonpromoting", "limit": "never authorizes claim or prose readiness"},
            {"capability": "representative_m22_replay", "status": "nine_cases_passed", "limit": "retained topic replay, not live topic quality"},
            {"capability": "forward_citations", "status": "unavailable_nonblocking", "limit": "not zero and not complete"},
            {"capability": "identifier_bearing_omission_frontier", "status": "50_open", "limit": "title-context-only"},
            {"capability": "identifier_free_omission_frontier", "status": "195_units_open", "limit": "unique paper count unknown"},
            {"capability": "publication_or_release", "status": "not_authorized", "limit": "separate human boundary"},
        ],
        "what_is_not_concluded": NONCLAIMS,
    }


def _run_command(
    *,
    case_id: str,
    command_id: str,
    argv: list[str],
    cwd: Path,
    output_root: Path,
    timeout: int = 120,
) -> dict[str, Any]:
    environment = _offline_subprocess_environment()
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=environment,
        capture_output=True,
        timeout=timeout,
    )
    prefix = output_root / "command_outputs" / f"{case_id}__{command_id}"
    stdout_path = prefix.with_suffix(".stdout")
    stderr_path = prefix.with_suffix(".stderr")
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    parsed: dict[str, Any] | None = None
    try:
        value = json.loads(completed.stdout)
        parsed = value if isinstance(value, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return {
        "case_id": case_id,
        "command_id": command_id,
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout_path": stdout_path.relative_to(output_root).as_posix(),
        "stdout_sha256": _sha(completed.stdout),
        "stderr_path": stderr_path.relative_to(output_root).as_posix(),
        "stderr_sha256": _sha(completed.stderr),
        "parsed_json": parsed,
        "environment": {"PYTHONPATH": "unset", "CUDA_VISIBLE_DEVICES": "-1"},
    }


def _validate_cases(rows: list[dict[str, Any]], *, repository_root: Path, output_root: Path) -> list[dict[str, Any]]:
    by_command = {row["command_id"]: row for row in rows}
    version = by_command["version"]["parsed_json"]
    survey_help = _normalized_command_stdout(by_command["survey_help"], output_root)
    assessment_help = _normalized_command_stdout(by_command["assessment_help"], output_root)
    import_payload = by_command["import_origin"]["parsed_json"]
    topic_first = by_command["topic_first"]["parsed_json"]
    topic_confirmed = by_command["topic_confirmed"]["parsed_json"]
    seed_first = by_command["seed_first"]["parsed_json"]
    seed_resume = by_command["seed_resume"]["parsed_json"]
    assessment = by_command["assessment"]["parsed_json"]
    m22_replay = by_command["m22_replay"]["parsed_json"]
    tamper = by_command["m22_tamper"]["parsed_json"]
    docs = _json(output_root / "documentation_consistency.json")
    module_path = (
        Path(import_payload["module_path"]).resolve()
        if isinstance(import_payload, dict)
        and isinstance(import_payload.get("module_path"), str)
        else None
    )
    cases = [
        {
            "case_id": CASE_IDS[0],
            "passed": all(by_command[name]["exit_code"] == 0 for name in ("version", "survey_help", "assessment_help", "import_origin"))
            and _commands_run_outside_repository(rows, repository_root)
            and version.get("package") == "research-assistant"
            and version.get("version") == "0.1.0"
            and "Topic-only mode records a mission-bound bootstrap outcome" in survey_help
            and "does not allow credentials, private databases, paid model workers" in survey_help
            and "stops before live/API/download, source transport, or human-review actions" in survey_help
            and "never clears provenance, source-safety, claim-support, or prose gates" in assessment_help
            and module_path is not None
            and module_path.is_relative_to((output_root / "venv").resolve())
            and not module_path.is_relative_to((repository_root / "src").resolve()),
            "observed": import_payload,
        },
        {
            "case_id": CASE_IDS[1],
            "passed": by_command["topic_first"]["exit_code"] == 0
            and topic_first.get("status") == "blocked_at_gate"
            and topic_first.get("input_mode") == "idea_or_topic_without_initial_paper_seed"
            and topic_first.get("initial_seeds") == []
            and topic_first.get("next_action", {}).get("action_id") == "confirm_public_discovery"
            and topic_first.get("public_discovery_confirmation", {}).get("scope", {}).get("providers") == ["arxiv"],
            "observed": topic_first,
        },
        {
            "case_id": CASE_IDS[2],
            "passed": by_command["topic_confirmed"]["exit_code"] == 0
            and topic_confirmed.get("status") == "blocked_at_gate"
            and topic_confirmed.get("bootstrap_outcome") == "unavailable"
            and topic_confirmed.get("effective_seeds") == []
            and topic_confirmed.get("next_action", {}).get("action_id") == "terminal_blocked_bootstrap_unavailable",
            "observed": topic_confirmed,
        },
        {
            "case_id": CASE_IDS[3],
            "passed": by_command["seed_first"]["exit_code"] == 0
            and seed_first.get("status") == "blocked_at_gate"
            and seed_first.get("phase_statuses", {}).get("offline_skeleton", {}).get("exists") is True
            and seed_first.get("public_discovery_confirmation", {}).get("scope", {}).get("providers") == ["arxiv"]
            and all("openalex" not in value.casefold() for value in seed_first.get("safe_next_commands", [])),
            "observed": seed_first,
        },
        {
            "case_id": CASE_IDS[4],
            "passed": by_command["seed_resume"]["exit_code"] == 0
            and seed_resume.get("mission_id") == seed_first.get("mission_id")
            and seed_resume.get("mission_fingerprint") == seed_first.get("mission_fingerprint")
            and seed_resume.get("phase_statuses", {}).get("offline_skeleton", {}).get("exists") is True
            and _resume_lineage_and_state_valid(
                seed_first=seed_first,
                seed_resume=seed_resume,
                output_root=output_root,
            ),
            "observed": seed_resume,
        },
        {
            "case_id": CASE_IDS[5],
            "passed": by_command["assessment"]["exit_code"] == 0
            and assessment.get("assessment", {}).get("claim_support_allowed") is False
            and assessment.get("assessment", {}).get("ready_for_prose") is False,
            "observed": assessment,
        },
        {
            "case_id": CASE_IDS[6],
            "passed": by_command["m22_replay"]["exit_code"] == 0
            and m22_replay.get("status") == "passed"
            and m22_replay.get("case_count") == 9
            and m22_replay.get("claim_support_allowed") is False
            and m22_replay.get("ready_for_prose") is False
            and m22_replay.get("open_limitations") == {
                "forward_citations": "unavailable_nonblocking",
                "identifier_bearing_rows_open": 50,
                "identifier_free_units_open": 195,
            },
            "observed": m22_replay,
        },
        {
            "case_id": CASE_IDS[7],
            "passed": by_command["m22_tamper"]["exit_code"] == 0
            and tamper.get("status") == "rejected"
            and tamper.get("error_code") == "derived_artifact_replay_mismatch",
            "observed": tamper,
        },
        {
            "case_id": CASE_IDS[8],
            "passed": docs.get("status") == "passed",
            "observed": docs,
        },
    ]
    if [row["case_id"] for row in cases] != list(CASE_IDS):
        raise M23AcceptanceError("acceptance_case_order_mismatch")
    return cases


def _core_inventory(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == "venv":
            continue
        if path.name == "artifact_inventory.json":
            continue
        files.append({"relative_path": relative.as_posix(), "size_bytes": path.stat().st_size, "sha256": _sha_file(path)})
    return {"schema_version": f"{SCHEMA}-inventory", "venv_excluded": True, "files": files}


def _expected_command_identities(
    *, repository_root: Path, output_root: Path
) -> list[dict[str, Any]]:
    python = output_root / "venv" / "bin" / "python"
    ra = output_root / "venv" / "bin" / "ra"
    scratch = output_root / "operator_workspace"
    topic_root = scratch / "topic_mission"
    seed_root = scratch / "seed_mission"
    assessment_path = scratch / "assessment.json"
    tamper_root = scratch / "m22_tamper_copy"
    replay_code = _m22_replay_code(repository_root, output_root)
    tamper_code = (
        "import json; from pathlib import Path; "
        "from research_assistant.survey.m22_representative_missions import replay_representative_missions, M22RepresentativeMissionError; "
        f"repo=Path({str(repository_root)!r}); root=Path({str(tamper_root)!r}); "
        "\ntry:\n replay_representative_missions(repository_root=repo, output_root=root)\n"
        "except M22RepresentativeMissionError as exc:\n print(json.dumps({'status':'rejected','error_code':exc.code}, sort_keys=True))\n"
        "else:\n raise SystemExit(3)"
    )
    commands = (
        (CASE_IDS[0], "version", [str(ra), "version"]),
        (CASE_IDS[0], "survey_help", [str(ra), "survey", "run-public-source-workflow", "--help"]),
        (CASE_IDS[0], "assessment_help", [str(ra), "survey", "qualitative-assessment", "--help"]),
        (CASE_IDS[0], "import_origin", [str(python), "-c", "import json,research_assistant; print(json.dumps({'module_path': research_assistant.__file__}))"]),
        (CASE_IDS[1], "topic_first", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--out", str(topic_root)]),
        (CASE_IDS[2], "topic_confirmed", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--out", str(topic_root), "--resume", "--confirm-public-discovery"]),
        (CASE_IDS[3], "seed_first", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--seed", "arxiv:2201.12220v3", "--out", str(seed_root), "--run-safe-local"]),
        (CASE_IDS[4], "seed_resume", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--seed", "arxiv:2201.12220v3", "--out", str(seed_root), "--run-safe-local", "--resume"]),
        (CASE_IDS[5], "assessment", [str(ra), "survey", "qualitative-assessment", "--subject-id", "arxiv:2201.12220v3", "--assessment-type", "paper", "--summary", "A bounded synthetic operator note.", "--merit", "The command preserves exact local evidence references.", "--concern", "The note does not establish claim truth.", "--uncertainty", "Forward citations remain unavailable.", "--evidence-ref", "synthetic:operator-acceptance", "--next-action", "Inspect primary technical text before drafting a claim.", "--out", str(assessment_path)]),
        (CASE_IDS[6], "m22_replay", [str(python), "-c", replay_code]),
        (CASE_IDS[7], "m22_tamper", [str(python), "-c", tamper_code]),
    )
    return [
        {"case_id": case_id, "command_id": command_id, "argv": argv}
        for case_id, command_id, argv in commands
    ]


def _replay_command_rows(
    *,
    ledger: dict[str, Any],
    manifest: dict[str, Any],
    repository_root: Path,
    output_root: Path,
) -> list[dict[str, Any]]:
    rows = ledger.get("commands")
    expected_ledger_keys = {"schema_version", "command_count", "commands"}
    if (
        set(ledger) != expected_ledger_keys
        or
        ledger.get("schema_version") != f"{SCHEMA}-commands"
        or ledger.get("command_count") != len(COMMAND_IDS)
        or not isinstance(rows, list)
        or [row.get("command_id") for row in rows] != list(COMMAND_IDS)
    ):
        raise M23AcceptanceError("command_ledger_invalid")
    expected = _expected_command_identities(
        repository_root=repository_root, output_root=output_root
    )
    if [
        {key: row.get(key) for key in ("case_id", "command_id", "argv")}
        for row in rows
    ] != expected:
        raise M23AcceptanceError("command_identity_replay_mismatch")
    operator_cwd = manifest.get("operator_cwd")
    if (
        not isinstance(operator_cwd, str)
        or not _commands_run_outside_repository(rows, repository_root)
        or any(row.get("cwd") != operator_cwd for row in rows)
    ):
        raise M23AcceptanceError("command_cwd_replay_mismatch")
    replayed = []
    for row in rows:
        expected_row_keys = {
            "case_id",
            "command_id",
            "argv",
            "cwd",
            "exit_code",
            "stdout_path",
            "stdout_sha256",
            "stderr_path",
            "stderr_sha256",
            "parsed_json",
            "environment",
        }
        if set(row) != expected_row_keys or row.get("exit_code") != 0:
            raise M23AcceptanceError("command_row_replay_mismatch", row.get("command_id"))
        prefix = Path("command_outputs") / f"{row['case_id']}__{row['command_id']}"
        if (
            row.get("stdout_path") != prefix.with_suffix(".stdout").as_posix()
            or row.get("stderr_path") != prefix.with_suffix(".stderr").as_posix()
        ):
            raise M23AcceptanceError("command_output_path_mismatch", row["command_id"])
        if row.get("environment") != {"PYTHONPATH": "unset", "CUDA_VISIBLE_DEVICES": "-1"}:
            raise M23AcceptanceError("command_environment_mismatch", row["command_id"])
        rebuilt = dict(row)
        for stream in ("stdout", "stderr"):
            path = output_root / row[f"{stream}_path"]
            raw = path.read_bytes()
            if _sha(raw) != row[f"{stream}_sha256"]:
                raise M23AcceptanceError("command_output_tampered", row["command_id"])
            if stream == "stdout":
                try:
                    parsed = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    parsed = None
                rebuilt["parsed_json"] = parsed if isinstance(parsed, dict) else None
        if rebuilt["parsed_json"] != row.get("parsed_json"):
            raise M23AcceptanceError("command_parsed_json_mismatch", row["command_id"])
        replayed.append(rebuilt)
    return replayed


def replay_acceptance(*, repository_root: Path, output_root: Path) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    output_root = output_root.resolve(strict=True)
    manifest = _json(output_root / "run_manifest.json")
    ledger = _json(output_root / "command_ledger.json")
    cases = _json(output_root / "case_results.json")
    docs = _json(output_root / "documentation_consistency.json")
    capabilities = _json(output_root / "capability_matrix.json")
    terminal = _json(output_root / "terminal_result.json")
    if (
        manifest.get("schema_version") != f"{SCHEMA}-manifest"
        or manifest.get("status") != "closed"
        or manifest.get("network_dispatch") is not False
        or manifest.get("credential_access") is not False
        or manifest.get("pdf_fallback") is not False
        or manifest.get("hardware") != "CPU-only; CUDA_VISIBLE_DEVICES=-1; no framework import"
        or manifest.get("plan_path") != str(PLAN_PATH)
        or manifest.get("m22_root") != str(M22_REPLAY_ROOT)
        or manifest.get("venv_python") != str(output_root / "venv" / "bin" / "python")
    ):
        raise M23AcceptanceError("run_manifest_replay_mismatch")
    wheel = output_root / manifest["wheel_relative_path"]
    if _sha_file(wheel) != manifest["wheel_sha256"]:
        raise M23AcceptanceError("wheel_tampered")
    replayed_rows = _replay_command_rows(
        ledger=ledger,
        manifest=manifest,
        repository_root=repository_root,
        output_root=output_root,
    )
    expected_docs = documentation_consistency_report(repository_root)
    if docs != expected_docs:
        raise M23AcceptanceError("documentation_report_stale")
    if capabilities != capability_matrix():
        raise M23AcceptanceError("capability_matrix_replay_mismatch")
    replayed_m22 = _replay_m22_with_limitations(
        repository_root=repository_root,
        output_root=output_root / M22_REPLAY_ROOT,
    )
    m22_command = next(
        row for row in replayed_rows if row["command_id"] == "m22_replay"
    )
    if m22_command.get("parsed_json") != replayed_m22:
        raise M23AcceptanceError("m22_generated_replay_mismatch")
    replayed_cases = _validate_cases(
        replayed_rows, repository_root=repository_root, output_root=output_root
    )
    expected_cases = {
        "schema_version": f"{SCHEMA}-cases",
        "case_count": len(replayed_cases),
        "all_cases_passed": all(row["passed"] for row in replayed_cases),
        "cases": replayed_cases,
        "what_is_not_concluded": NONCLAIMS,
    }
    if cases != expected_cases or expected_cases["all_cases_passed"] is not True:
        raise M23AcceptanceError("acceptance_case_replay_mismatch")
    expected_terminal = {
        "schema_version": f"{SCHEMA}-terminal",
        "classification": "M23_OPERATIONAL_ACCEPTANCE_PASSED",
        "primary_criterion_passed": True,
        "case_count": len(replayed_cases),
        "wheel_sha256": manifest["wheel_sha256"],
        "documentation_status": docs["status"],
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    if terminal != expected_terminal:
        raise M23AcceptanceError("terminal_result_replay_mismatch")
    inventory_path = output_root / "artifact_inventory.json"
    if manifest.get("status") == "closed" and inventory_path.read_bytes() != pretty_json_bytes(_core_inventory(output_root)):
        raise M23AcceptanceError("artifact_inventory_mismatch")
    replay = {
        "schema_version": f"{SCHEMA}-replay",
        "status": "passed",
        "case_count": 9,
        "all_cases_passed": True,
        "wheel_sha256": manifest["wheel_sha256"],
        "what_is_not_concluded": NONCLAIMS,
    }
    offline_replay_path = output_root / "offline_replay.json"
    if offline_replay_path.exists() and _json(offline_replay_path) != replay:
        raise M23AcceptanceError("offline_replay_mismatch")
    return replay


def run_acceptance(
    *, repository_root: Path, output_root: Path, now: Callable[[], str] = _now
) -> dict[str, Any]:
    repository_root = repository_root.resolve(strict=True)
    output_root = output_root.resolve(strict=False)
    if output_root.exists() or not output_root.parent.is_dir():
        raise M23AcceptanceError("output_root_not_fresh")
    started = now()
    start_clock = time.monotonic()
    output_root.mkdir(mode=0o700)
    dist = output_root / "dist"
    dist.mkdir()
    offline_environment = _offline_subprocess_environment()
    _build_wheel_from_fresh_staging(
        repository_root=repository_root,
        dist=dist,
        environment=offline_environment,
    )
    wheels = sorted(dist.glob("research_assistant-*.whl"))
    if len(wheels) != 1:
        raise M23AcceptanceError("wheel_build_output_invalid")
    wheel = wheels[0]
    venv = output_root / "venv"
    with tempfile.TemporaryDirectory(prefix="ra-m23-install-") as temporary_directory:
        isolated_cwd = Path(temporary_directory).resolve(strict=True)
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)],
            cwd=isolated_cwd,
            check=True,
            env=offline_environment,
            capture_output=True,
            timeout=180,
        )
        python = venv / "bin" / "python"
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--force-reinstall",
                str(wheel),
            ],
            cwd=isolated_cwd,
            check=True,
            env=offline_environment,
            capture_output=True,
            timeout=180,
        )
    ra = venv / "bin" / "ra"
    if not ra.is_file():
        raise M23AcceptanceError("installed_console_script_missing", str(ra))
    scratch = output_root / "operator_workspace"
    scratch.mkdir()
    operator_cwd_context = tempfile.TemporaryDirectory(prefix="ra-m23-operator-")
    operator_cwd = Path(operator_cwd_context.name).resolve(strict=True)
    topic_root = scratch / "topic_mission"
    seed_root = scratch / "seed_mission"
    assessment_path = scratch / "assessment.json"
    commands: list[dict[str, Any]] = []
    def run(case_id: str, command_id: str, argv: list[str]) -> dict[str, Any]:
        row = _run_command(
            case_id=case_id,
            command_id=command_id,
            argv=argv,
            cwd=operator_cwd,
            output_root=output_root,
        )
        commands.append(row)
        return row

    run(CASE_IDS[0], "version", [str(ra), "version"])
    run(CASE_IDS[0], "survey_help", [str(ra), "survey", "run-public-source-workflow", "--help"])
    run(CASE_IDS[0], "assessment_help", [str(ra), "survey", "qualitative-assessment", "--help"])
    run(CASE_IDS[0], "import_origin", [str(python), "-c", "import json,research_assistant; print(json.dumps({'module_path': research_assistant.__file__}))"])
    run(CASE_IDS[1], "topic_first", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--out", str(topic_root)])
    run(CASE_IDS[2], "topic_confirmed", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--out", str(topic_root), "--resume", "--confirm-public-discovery"])
    run(CASE_IDS[3], "seed_first", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--seed", "arxiv:2201.12220v3", "--out", str(seed_root), "--run-safe-local"])
    run(CASE_IDS[4], "seed_resume", [str(ra), "survey", "run-public-source-workflow", "--topic", "Neural Optimal Transport", "--seed", "arxiv:2201.12220v3", "--out", str(seed_root), "--run-safe-local", "--resume"])
    run(CASE_IDS[5], "assessment", [str(ra), "survey", "qualitative-assessment", "--subject-id", "arxiv:2201.12220v3", "--assessment-type", "paper", "--summary", "A bounded synthetic operator note.", "--merit", "The command preserves exact local evidence references.", "--concern", "The note does not establish claim truth.", "--uncertainty", "Forward citations remain unavailable.", "--evidence-ref", "synthetic:operator-acceptance", "--next-action", "Inspect primary technical text before drafting a claim.", "--out", str(assessment_path)])
    replay_code = _m22_replay_code(repository_root, output_root)
    run(CASE_IDS[6], "m22_replay", [str(python), "-c", replay_code])
    tamper_root = scratch / "m22_tamper_copy"
    shutil.copytree(output_root / M22_REPLAY_ROOT, tamper_root)
    tampered = _json(tamper_root / "case_ledger.json")
    tampered["cases"][0]["terminal"] = "TAMPERED"
    _write_json(tamper_root / "case_ledger.json", tampered)
    tamper_code = (
        "import json; from pathlib import Path; "
        "from research_assistant.survey.m22_representative_missions import replay_representative_missions, M22RepresentativeMissionError; "
        f"repo=Path({str(repository_root)!r}); root=Path({str(tamper_root)!r}); "
        "\ntry:\n replay_representative_missions(repository_root=repo, output_root=root)\n"
        "except M22RepresentativeMissionError as exc:\n print(json.dumps({'status':'rejected','error_code':exc.code}, sort_keys=True))\n"
        "else:\n raise SystemExit(3)"
    )
    run(CASE_IDS[7], "m22_tamper", [str(python), "-c", tamper_code])
    docs = documentation_consistency_report(repository_root)
    _write_json(output_root / "documentation_consistency.json", docs)
    _write_json(output_root / "capability_matrix.json", capability_matrix())
    cases = _validate_cases(commands, repository_root=repository_root, output_root=output_root)
    case_result = {
        "schema_version": f"{SCHEMA}-cases",
        "case_count": len(cases),
        "all_cases_passed": all(row["passed"] for row in cases),
        "cases": cases,
        "what_is_not_concluded": NONCLAIMS,
    }
    _write_json(output_root / "case_results.json", case_result)
    command_ledger = {"schema_version": f"{SCHEMA}-commands", "command_count": len(commands), "commands": commands}
    _write_json(output_root / "command_ledger.json", command_ledger)
    manifest = {
        "schema_version": f"{SCHEMA}-manifest",
        "status": "running",
        "started_at_utc": started,
        "completed_at_utc": None,
        "wall_time_seconds": None,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository_root, text=True).strip(),
        "git_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repository_root, text=True).strip(),
        "worktree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repository_root, text=True).strip()),
        "python": sys.version,
        "platform": platform.platform(),
        "hardware": "CPU-only; CUDA_VISIBLE_DEVICES=-1; no framework import",
        "network_dispatch": False,
        "credential_access": False,
        "pdf_fallback": False,
        "plan_path": str(PLAN_PATH),
        "m22_root": str(M22_REPLAY_ROOT),
        "wheel_relative_path": wheel.relative_to(output_root).as_posix(),
        "wheel_sha256": _sha_file(wheel),
        "venv_python": str(python),
        "operator_cwd": str(operator_cwd),
    }
    _write_json(output_root / "run_manifest.json", manifest)
    terminal = {
        "schema_version": f"{SCHEMA}-terminal",
        "classification": "M23_OPERATIONAL_ACCEPTANCE_PASSED" if case_result["all_cases_passed"] else "M23_OPERATIONAL_ACCEPTANCE_FAILED",
        "primary_criterion_passed": case_result["all_cases_passed"],
        "case_count": len(cases),
        "wheel_sha256": manifest["wheel_sha256"],
        "documentation_status": docs["status"],
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    _write_json(output_root / "terminal_result.json", terminal)
    manifest.update(status="closed", completed_at_utc=now(), wall_time_seconds=round(time.monotonic() - start_clock, 6))
    _write_json(output_root / "run_manifest.json", manifest)
    _write_json(output_root / "artifact_inventory.json", _core_inventory(output_root))
    replay = replay_acceptance(repository_root=repository_root, output_root=output_root)
    _write_json(output_root / "offline_replay.json", replay)
    _write_json(output_root / "artifact_inventory.json", _core_inventory(output_root))
    replay_acceptance(repository_root=repository_root, output_root=output_root)
    operator_cwd_context.cleanup()
    return terminal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_acceptance(repository_root=args.repository_root, output_root=args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if result["primary_criterion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CASE_IDS",
    "M22_REPLAY_ROOT",
    "M23AcceptanceError",
    "capability_matrix",
    "documentation_consistency_report",
    "replay_acceptance",
    "run_acceptance",
]
