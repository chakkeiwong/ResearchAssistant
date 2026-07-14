from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
BASELINE_COMMIT = "1b36af06efc7e1c2c086934cd8800691ae8a6da7"
M17_MANIFEST = ROOT / "docs/validation/literature_survey_m17_2026-07-13/successor_manifest.json"
M17_MANIFEST_SHA256 = "46fd3d4e444fc5fd43b9d10f05dce110980c75bd13b98b345ae459a5b4277571"
M17_PAYLOAD_SHA256 = "163f9ca026e18903d219690ed88647c1bc26ae7f45cd0752aa05a9cb891d485f"

CLI_PATH = "src/research_assistant/cli.py"
CLI_DECOUPLING_LINES = (
    "            plan_file=Path(args.plan_file) if args.plan_file else None,\n",
    "            plan_file_sha256=args.plan_file_sha256,\n",
    "    arxiv_batch_run.add_argument('--plan-file')\n",
    "    arxiv_batch_run.add_argument('--plan-file-sha256')\n",
)
PORTABLE_PHASE10_TEST_PATH = "tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py"
PORTABLE_PHASE10_M17_SHA256 = "5de6d3eb5e88e22398f85521fe9a720626f0783caaf4cf704de44f9859d42117"
PORTABLE_PHASE10_M17_SIZE_BYTES = 12473
PORTABLE_PHASE10_CANDIDATE_SHA256 = "f3ad7a6efc601266ef3c157b1c4c327ca981c20b1c901846647eb0d21536f801"
PORTABLE_PHASE10_CANDIDATE_SIZE_BYTES = 15888

EXACT_CUMULATIVE_UNIT_SUITE = (
    "tests/unit/test_literature_survey_m16.py",
    "tests/unit/test_literature_survey_m16_phase2.py",
    "tests/unit/test_literature_survey_m16_phase3.py",
    "tests/unit/test_literature_survey_m16_phase4.py",
    "tests/unit/test_literature_survey_m16_phase5.py",
    "tests/unit/test_literature_survey_m16_phase6.py",
    "tests/unit/test_literature_survey_m16_phase7.py",
    "tests/unit/test_literature_survey_m16_phase8.py",
    "tests/unit/test_literature_survey_m16_phase9.py",
    "tests/unit/test_literature_survey_m17.py",
)
EXACT_SURVEY_SCRIPT_SUITE = (
    "tests/scripts/test_literature_survey_benchmark_feedback_summary.py",
    "tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py",
    "tests/scripts/test_literature_survey_phase5_command_validation.py",
    "tests/scripts/test_literature_survey_phase6_boundary_validation.py",
    "tests/scripts/test_literature_survey_phase7_validation_harness.py",
)

FROZEN_WHITESPACE_EXCEPTIONS = (
    "docs/reviews/literature_survey_m17_terminal_implementation_review_bundle_2026-07-14.md:120: new blank line at EOF.",
    "docs/validation/surveybench_online_replay_phase5/agent_trial_prompt_packet_2026-06-29.md:64: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/README.md:43: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json:128: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/adjacent.json:27: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/citations.json:27: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/download_status.json:34: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/evidence_context.json:33: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/paper.json:82: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/references.json:22: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/search.json:107: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/source_anchors.json:33: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/responses/source_status.json:39: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/scorer_packet/candidate_ledger.json:48: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/scorer_packet/citation_map.json:129: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/scorer_packet/claim_support.json:64: new blank line at EOF.",
    "tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/scorer_packet/source_support.json:78: new blank line at EOF.",
)

# These are required by selected SurveyBench tests but were absent from the M17
# successor manifest. They are canonical test inputs, not result evidence.
DEPENDENCY_ADDITIONS = (
    "docs/validation/surveybench_agent_trial_prompt_packet_2026-06-28.md",
    "docs/validation/surveybench_online_replay_phase5/agent_trial_prompt_packet_2026-06-29.md",
    "docs/validation/surveybench_live_intake_launcher_phase3_restricted_launcher/stress_restricted_launcher_prompt_2026-07-03.md",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/build_manifest.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/candidate_ledger.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/citation_map.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/claim_support.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/omission_risk.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/paper_classifications.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/ready_for_prose.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/source_safety_status.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/source_support.json",
    "docs/validation/literature_survey_live_public_source_phase6_2026-07-07/survey_packet.md",
)

# Mutable phase controls are staged by exact path after payload review. Their
# hashes are recorded at staging time; they are deliberately outside the M17
# payload digest and do not create a self-hash cycle.
CONTROL_PATHS = (
    "docs/plans/literature_survey_automation_milestones.json",
    "docs/plans/literature_survey_m16_phase10_local_close_record_2026-07-13.md",
    "docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_result_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m18_reproducible_git_integration_subplan_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_subplan_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m20_live_discovery_and_citation_frontier_subplan_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m21_live_source_status_and_anchor_intake_subplan_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m22_human_attested_review_and_real_missions_subplan_2026-07-13.md",
    "docs/plans/literature_survey_north_star_m23_acceptance_and_operational_closeout_subplan_2026-07-13.md",
    "docs/plans/literature_survey_north_star_policy_migration_2026-07-14.md",
    "docs/plans/literature_survey_north_star_program_setup_result_2026-07-13.md",
    "docs/plans/literature_survey_north_star_program_setup_review_nonconvergence_blocker_2026-07-13.md",
    "docs/plans/literature_survey_north_star_visible_execution_ledger_2026-07-13.md",
    "docs/plans/literature_survey_north_star_visible_gated_execution_runbook_2026-07-13.md",
    "docs/plans/literature_survey_north_star_visible_stop_handoff_2026-07-13.md",
    "docs/plans/reset_memo_2026-07-10.md",
    "docs/reviews/literature_survey_north_star_gap_closure_plan_review_verdict_round3_2026-07-13.md",
    "docs/reviews/literature_survey_north_star_program_setup_governance_extra_authorized_review_verdict_2026-07-13.md",
    "docs/reviews/literature_survey_north_star_program_setup_governance_review_verdict_round5_2026-07-13.md",
    "docs/reviews/literature_survey_north_star_program_setup_m17_review_verdict_round5_2026-07-13.md",
    "docs/reviews/literature_survey_m17_terminal_implementation_review_bundle_2026-07-14.md",
    "docs/reviews/literature_survey_m17_terminal_implementation_review_verdict_2026-07-14.md",
    "docs/reviews/literature_survey_m17_artifact_closure_repair_review_bundle_2026-07-14.md",
    "docs/reviews/literature_survey_m17_artifact_closure_repair_review_verdict_2026-07-14.md",
    "docs/reviews/literature_survey_m18_plan_review_bundle_2026-07-14.md",
    "docs/reviews/literature_survey_m18_plan_review_verdict_2026-07-14.md",
    "docs/reviews/literature_survey_m18_plan_review_verdict_round2_2026-07-14.md",
    "docs/reviews/literature_survey_m18_plan_review_verdict_round3_2026-07-14.md",
    "docs/reviews/literature_survey_m18_plan_review_verdict_round4_2026-07-14.md",
    "docs/validation/literature_survey_m17_2026-07-13/decision_table.json",
    "docs/validation/literature_survey_m17_2026-07-13/post_run_red_team.json",
    "docs/validation/literature_survey_m17_2026-07-13/run_manifest.json",
    "docs/validation/literature_survey_m17_2026-07-13/static_audit.json",
    "docs/validation/literature_survey_m17_2026-07-13/successor_manifest.json",
    "docs/validation/literature_survey_m17_2026-07-13/successor_manifest_replay.json",
    "docs/validation/literature_survey_m18_2026-07-14/dependency_audit.json",
    "docs/validation/literature_survey_m18_2026-07-14/disposable_preflight_record.json",
    "docs/validation/literature_survey_m18_2026-07-14/payload_manifest.json",
    "docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py",
)

PROTECTED_UNRELATED = {
    ".gitignore": "29344e75c13a1a6d4e9b1bb653d106156cafb02ee61b1c99701c9a32f5ec9074",
    "docs/benchmark_plan.md": "2395402f907a6d163979e37fa62d6975109c5e9ccfcb7322962b3a0a2e00a033",
    "src/research_assistant/ingest/arxiv_batch.py": "cda93366f622a8c52ed809570ad40b8062c309e29d8c9ab47aa8b971466152be",
    "src/research_assistant/source/arxiv_source.py": "5ae7f4bb1aea9ab7d999f8e915760f92ae0e2fffcc31af4cf3b3e4db780576d8",
    "tests/integration/test_arxiv_batch_intake.py": "bb9975537e134322449341bc1941a7582d714fc95b93fb9c86ce1beee712ce80",
    "tests/unit/test_arxiv_source.py": "21bfb200b0a75d9e4bd7b536bff2d6b953b2866fc59a17e196b368443f716f9d",
}

STAGE_RECORD_PATH = "docs/validation/literature_survey_m18_2026-07-14/stage_record.json"
REPAIR_MANIFEST_PATH = "docs/validation/literature_survey_m18_2026-07-14/repair_attempt02.json"
REPAIR_STAGE_RECORD_PATH = "docs/validation/literature_survey_m18_2026-07-14/repair_stage_record.json"
REPAIR_FAILURE_CLASSES = {
    "dependency_closure",
    "harness",
    "packaging",
    "serialization",
}
UNCHANGED_REPAIR_CONTRACT = {
    "budget_changed": False,
    "hardware_class_changed": False,
    "network_boundary_changed": False,
    "product_semantics_changed": False,
    "scientific_target_changed": False,
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _path(relative: str, *, root: Path = ROOT) -> Path:
    lexical = PurePosixPath(relative)
    if not relative or lexical.is_absolute() or ".." in lexical.parts or str(lexical) != relative:
        raise RuntimeError(f"noncanonical repository path: {relative!r}")
    return root / relative


def _reject_symlink_parents(path: Path, *, root: Path) -> None:
    relative = path.relative_to(root)
    cursor = root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RuntimeError(f"payload path traverses symlink parent: {relative.as_posix()}")


def _git(*args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, input=input_bytes)


def _require_no_git_operation() -> None:
    git_dir = Path(_git("rev-parse", "--git-dir").decode().strip())
    if not git_dir.is_absolute():
        git_dir = ROOT / git_dir
    operation_markers = (
        "BISECT_LOG",
        "CHERRY_PICK_HEAD",
        "MERGE_HEAD",
        "REVERT_HEAD",
        "rebase-apply",
        "rebase-merge",
        "sequencer",
    )
    active = [name for name in operation_markers if (git_dir / name).exists()]
    if active:
        raise RuntimeError(f"Git operation is active: {active}")


def _single_parent(commit: str) -> str:
    fields = _git("rev-list", "--parents", "-n", "1", commit).decode().strip().split()
    if len(fields) != 2 or fields[0] != commit:
        raise RuntimeError(f"commit does not have exactly one parent: {commit}")
    return fields[1]


def _candidate_cli_bytes() -> bytes:
    text = _path(CLI_PATH).read_text()
    for line in CLI_DECOUPLING_LINES:
        if text.count(line) != 1:
            raise RuntimeError(f"CLI decoupling line count changed: {line.strip()!r}")
        text = text.replace(line, "", 1)
    if "plan_file=Path(args.plan_file)" in text or "--plan-file-sha256" in text:
        raise RuntimeError("CLI still contains the excluded optional arXiv plan-file coupling")
    return text.encode()


def _git_replay_mode(kind: str, source_mode_octal: str) -> str:
    source_mode = int(source_mode_octal, 8)
    if kind == "file":
        return "0755" if source_mode & 0o111 else "0644"
    if kind == "symlink":
        return "0777"
    raise RuntimeError(f"unsupported payload kind: {kind!r}")


def _git_index_mode(row: dict[str, Any]) -> str:
    if row["kind"] == "symlink":
        return "120000"
    if row["kind"] != "file":
        raise RuntimeError(f"unsupported Git row kind: {row['kind']!r}")
    if row["mode_octal"] not in {"0644", "0755"}:
        raise RuntimeError(f"nonrepresentable Git file mode: {row['mode_octal']!r}")
    return "100755" if row["mode_octal"] == "0755" else "100644"


def _tracked_git_mode(target: Path, relative: str) -> str:
    raw = subprocess.check_output(
        ["git", "ls-files", "-s", "-z", "--", relative],
        cwd=target,
    )
    records = [record for record in raw.split(b"\0") if record]
    if len(records) != 1:
        raise RuntimeError(f"payload path has {len(records)} Git index records")
    metadata, recorded_path = records[0].split(b"\t", 1)
    if recorded_path.decode() != relative:
        raise RuntimeError("Git index path mismatch")
    mode, _oid, stage = metadata.decode().split()
    if stage != "0":
        raise RuntimeError(f"payload path has nonzero Git index stage: {stage}")
    return mode


def _current_row(relative: str, *, role: str, provenance: str) -> dict[str, Any]:
    path = _path(relative)
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        raw = path.read_bytes()
        kind = "file"
    elif stat.S_ISLNK(mode):
        raw = os.readlink(path).encode()
        kind = "symlink"
    else:
        raise RuntimeError(f"unsupported payload member: {relative}")
    source_mode_octal = f"{stat.S_IMODE(mode):04o}"
    return {
        "kind": kind,
        "mode_octal": _git_replay_mode(kind, source_mode_octal),
        "path": relative,
        "provenance": provenance,
        "role": role,
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
        "source_mode_octal": source_mode_octal,
    }


def _verify_m17_manifest() -> dict[str, Any]:
    raw = M17_MANIFEST.read_bytes()
    if _sha256(raw) != M17_MANIFEST_SHA256:
        raise RuntimeError("M17 successor manifest hash changed")
    manifest = json.loads(raw)
    if manifest.get("manifest_payload_sha256") != M17_PAYLOAD_SHA256:
        raise RuntimeError("M17 successor payload authority changed")
    if manifest.get("artifact_count") != 1671 or len(manifest.get("rows", [])) != 1671:
        raise RuntimeError("M17 successor manifest row count changed")
    return manifest


def _payload_manifest() -> dict[str, Any]:
    m17 = _verify_m17_manifest()
    rows: dict[str, dict[str, Any]] = {}
    for expected in m17["rows"]:
        relative = expected["path"]
        _path(relative)
        source_row = _current_row(
            relative,
            role=expected["role"],
            provenance=expected["provenance"],
        )
        if relative == PORTABLE_PHASE10_TEST_PATH:
            if (
                expected["sha256"] != PORTABLE_PHASE10_M17_SHA256
                or expected["size_bytes"] != PORTABLE_PHASE10_M17_SIZE_BYTES
            ):
                raise RuntimeError("M17 portable-test source authority changed")
            if (
                source_row["sha256"] != PORTABLE_PHASE10_CANDIDATE_SHA256
                or source_row["size_bytes"] != PORTABLE_PHASE10_CANDIDATE_SIZE_BYTES
            ):
                raise RuntimeError("M18 portable-test candidate bytes changed")
            source_checks = {
                "kind": source_row["kind"],
                "mode_octal": source_row["source_mode_octal"],
            }
        else:
            source_checks = {
                "kind": source_row["kind"],
                "mode_octal": source_row["source_mode_octal"],
                "sha256": source_row["sha256"],
                "size_bytes": source_row["size_bytes"],
            }
        for key, value in source_checks.items():
            if value != expected[key]:
                raise RuntimeError(f"M17 payload row changed at {relative}: {key}")
        if relative == CLI_PATH:
            raw = _candidate_cli_bytes()
            row = {
                "kind": "file",
                "mode_octal": source_row["mode_octal"],
                "path": relative,
                "provenance": "m18_remove_unintegrated_arxiv_plan_file_coupling",
                "role": expected["role"],
                "sha256": _sha256(raw),
                "size_bytes": len(raw),
                "source_mode_octal": source_row["source_mode_octal"],
            }
        elif relative == PORTABLE_PHASE10_TEST_PATH:
            row = {
                **source_row,
                "provenance": "m18_rebase_frozen_phase10_paths_to_clone_local_output",
            }
        else:
            row = source_row
        rows[relative] = row

    for relative in DEPENDENCY_ADDITIONS:
        if relative in rows:
            raise RuntimeError(f"dependency addition unexpectedly overlaps M17: {relative}")
        rows[relative] = _current_row(
            relative,
            role="clean_checkout_test_dependency",
            provenance="m18_static_dependency_audit",
        )

    ordered = [rows[path] for path in sorted(rows)]
    digest_payload = {
        "baseline_commit": BASELINE_COMMIT,
        "rows": ordered,
        "schema_version": "ra-literature-survey-m18-payload-manifest-v2",
    }
    return {
        **digest_payload,
        "artifact_count": len(ordered),
        "control_paths": list(CONTROL_PATHS),
        "dependency_addition_count": len(DEPENDENCY_ADDITIONS),
        "exact_cumulative_unit_suite": list(EXACT_CUMULATIVE_UNIT_SUITE),
        "exact_survey_script_suite": list(EXACT_SURVEY_SCRIPT_SUITE),
        "m17_successor_manifest_sha256": M17_MANIFEST_SHA256,
        "mode_semantics": {
            "mode_octal": "Canonical Git-replay permission class: 0644 or 0755 for regular files and 0777 for symlinks; replay validates Git tree mode and only the filesystem executable-bit class, not umask-dependent read/write bits",
            "source_mode_octal": "Original worktree mode validated against the M17 authority before Git normalization",
        },
        "payload_sha256": _sha256(_canonical_bytes(digest_payload)),
        "protected_unrelated_paths": PROTECTED_UNRELATED,
        "repair": {
            "path": CLI_PATH,
            "removed_line_count": 4,
            "reason": "M17 inherited optional arXiv plan-file CLI arguments whose implementation remains in excluded unrelated dirty work; remove only that coupling from the committed candidate",
            "worktree_unchanged": True,
        },
        "test_portability_repair": {
            "candidate_sha256": PORTABLE_PHASE10_CANDIDATE_SHA256,
            "m17_sha256": PORTABLE_PHASE10_M17_SHA256,
            "path": PORTABLE_PHASE10_TEST_PATH,
            "reason": "validate frozen absolute required_path suffixes while reading only from the supplied clone-local Phase 10 output root",
            "test_only": True,
        },
        "what_is_not_concluded": [
            "the payload alone is an identified commit",
            "clean-install reproducibility before M18 isolated validation",
            "live, source, human-review, scientific, product, or release readiness",
        ],
    }


def _write_plan_artifacts() -> None:
    for relative, expected in PROTECTED_UNRELATED.items():
        if _sha256(_path(relative).read_bytes()) != expected:
            raise RuntimeError(f"protected unrelated path changed: {relative}")
    manifest = _payload_manifest()
    dependency_audit = {
        "added_paths": list(DEPENDENCY_ADDITIONS),
        "baseline_commit": BASELINE_COMMIT,
        "cli_decoupling_candidate_sha256": next(
            row["sha256"] for row in manifest["rows"] if row["path"] == CLI_PATH
        ),
        "control_path_count": len(CONTROL_PATHS),
        "finding": "selected SurveyBench tests read three canonical prompt inputs, and the exact Phase 7 script test reads the 10-file canonical Phase 6 packet, outside the M17 successor manifest",
        "exact_cumulative_unit_suite": list(EXACT_CUMULATIVE_UNIT_SUITE),
        "exact_survey_script_suite": list(EXACT_SURVEY_SCRIPT_SUITE),
        "payload_artifact_count": manifest["artifact_count"],
        "protected_unrelated_count": len(PROTECTED_UNRELATED),
        "portable_phase10_test_repair": {
            "candidate_sha256": PORTABLE_PHASE10_CANDIDATE_SHA256,
            "m17_sha256": PORTABLE_PHASE10_M17_SHA256,
            "path": PORTABLE_PHASE10_TEST_PATH,
            "status": "focused_regression_passed_pending_committed_clone_trace",
        },
        "regular_file_mode_normalization": {
            "executable": "0755",
            "non_executable": "0644",
            "source_mode_preserved_as": "source_mode_octal",
        },
        "schema_version": "ra-literature-survey-m18-dependency-audit-v2",
        "status": "repaired_in_payload_manifest_pending_candidate_preflight",
    }
    (OUTPUT / "payload_manifest.json").write_bytes(_pretty_bytes(manifest))
    (OUTPUT / "dependency_audit.json").write_bytes(_pretty_bytes(dependency_audit))
    print(json.dumps({
        "artifact_count": manifest["artifact_count"],
        "control_path_count": len(CONTROL_PATHS),
        "payload_sha256": manifest["payload_sha256"],
    }, sort_keys=True))


def _reviewed_payload_manifest() -> dict[str, Any]:
    manifest_path = OUTPUT / "payload_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("reviewed M18 payload manifest is absent or nonregular")
    recomputed = _payload_manifest()
    if manifest_path.read_bytes() != _pretty_bytes(recomputed):
        raise RuntimeError("reviewed M18 payload manifest differs from canonical recomputation")
    return recomputed


def _payload_bytes(row: dict[str, Any]) -> bytes:
    if row["path"] == CLI_PATH:
        raw = _candidate_cli_bytes()
    elif row["kind"] == "symlink":
        raw = os.readlink(_path(row["path"])).encode()
    else:
        raw = _path(row["path"]).read_bytes()
    if _sha256(raw) != row["sha256"] or len(raw) != row["size_bytes"]:
        raise RuntimeError(f"payload bytes changed: {row['path']}")
    return raw


def _materialize_current_path(relative: str, *, target: Path) -> None:
    source = _path(relative)
    destination = _path(relative, root=target)
    _reject_symlink_parents(destination, root=target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            raise RuntimeError(f"materialization destination is a directory: {relative}")
        destination.unlink()
    mode = source.lstat().st_mode
    if stat.S_ISREG(mode):
        destination.write_bytes(source.read_bytes())
        destination.chmod(stat.S_IMODE(mode))
    elif stat.S_ISLNK(mode):
        destination.symlink_to(os.readlink(source))
    else:
        raise RuntimeError(f"unsupported materialization source: {relative}")


def _materialize(
    target: Path,
    *,
    stage_source: bool,
    include_controls: bool,
    include_protected_worktree: bool,
) -> None:
    target = target.resolve()
    if not (target / ".git").is_dir():
        raise RuntimeError("materialization target must be an existing local Git clone")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
    if head != BASELINE_COMMIT:
        raise RuntimeError(f"materialization target has wrong HEAD: {head}")
    manifest = _reviewed_payload_manifest()
    for row in manifest["rows"]:
        destination = _path(row["path"], root=target)
        _reject_symlink_parents(destination, root=target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                raise RuntimeError(f"payload destination is a directory: {row['path']}")
            destination.unlink()
        if stage_source and row["path"] == CLI_PATH:
            raw = _path(CLI_PATH).read_bytes()
        else:
            raw = _payload_bytes(row)
        if row["kind"] == "symlink":
            destination.symlink_to(raw.decode())
        else:
            destination.write_bytes(raw)
            mode_octal = row["source_mode_octal"] if stage_source else row["mode_octal"]
            destination.chmod(int(mode_octal, 8))
    if include_controls:
        for relative in CONTROL_PATHS:
            _materialize_current_path(relative, target=target)
    if include_protected_worktree:
        for relative in sorted(PROTECTED_UNRELATED):
            _materialize_current_path(relative, target=target)
    print(json.dumps({
        "controls_materialized": len(CONTROL_PATHS) if include_controls else 0,
        "materialized": len(manifest["rows"]),
        "protected_worktree_materialized": len(PROTECTED_UNRELATED) if include_protected_worktree else 0,
        "stage_source": stage_source,
        "target": str(target),
    }, sort_keys=True))


def _replay(target: Path) -> None:
    target = target.resolve()
    manifest_path = target / "docs/validation/literature_survey_m18_2026-07-14/payload_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("M18 payload manifest is absent or nonregular")
    manifest = json.loads(manifest_path.read_bytes())
    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != manifest.get("artifact_count"):
        raise RuntimeError("M18 payload manifest row count is invalid")
    paths = [row.get("path") for row in rows]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise RuntimeError("M18 payload paths are not unique and sorted")
    digest_payload = {
        "baseline_commit": manifest.get("baseline_commit"),
        "rows": rows,
        "schema_version": manifest.get("schema_version"),
    }
    digest = _sha256(_canonical_bytes(digest_payload))
    if digest != manifest.get("payload_sha256"):
        raise RuntimeError("M18 payload digest does not replay")
    mismatches: list[dict[str, str]] = []
    for expected in rows:
        try:
            source_mode_octal = expected["source_mode_octal"]
            normalized_mode = _git_replay_mode(expected["kind"], source_mode_octal)
            if expected["mode_octal"] != normalized_mode:
                raise RuntimeError(
                    "mode semantics mismatch: "
                    f"source {source_mode_octal!r} normalizes to {normalized_mode!r}, "
                    f"manifest has {expected['mode_octal']!r}"
                )
            path = _path(expected["path"], root=target)
            _reject_symlink_parents(path, root=target)
            mode = path.lstat().st_mode
            if expected["kind"] == "file" and stat.S_ISREG(mode):
                raw = path.read_bytes()
            elif expected["kind"] == "symlink" and stat.S_ISLNK(mode):
                raw = os.readlink(path).encode()
            else:
                raise RuntimeError("kind mismatch")
            actual = {
                "sha256": _sha256(raw),
                "size_bytes": len(raw),
            }
            git_mode = _tracked_git_mode(target, expected["path"])
            expected_git_mode = _git_index_mode(expected)
            if git_mode != expected_git_mode:
                raise RuntimeError(f"git_mode: expected {expected_git_mode!r}, got {git_mode!r}")
            if expected["kind"] == "file":
                actual_executable = bool(stat.S_IMODE(mode) & 0o111)
                expected_executable = expected["mode_octal"] == "0755"
                if actual_executable != expected_executable:
                    raise RuntimeError(
                        "filesystem executable class: "
                        f"expected {expected_executable!r}, got {actual_executable!r}"
                    )
            for key, value in actual.items():
                if value != expected[key]:
                    raise RuntimeError(f"{key}: expected {expected[key]!r}, got {value!r}")
        except Exception as exc:
            mismatches.append({"path": expected.get("path", "<invalid>"), "reason": str(exc)})
    result = {
        "artifact_count": len(rows),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "passed": not mismatches,
        "payload_sha256": digest,
        "schema_version": "ra-literature-survey-m18-payload-replay-v2",
    }
    print(json.dumps(result, sort_keys=True))
    if mismatches:
        raise RuntimeError("M18 payload replay failed")


def _stage() -> None:
    _require_no_git_operation()
    if _git("rev-parse", "HEAD").decode().strip() != BASELINE_COMMIT:
        raise RuntimeError("repository HEAD changed before staging")
    if _git("diff", "--cached", "--name-only").strip():
        raise RuntimeError("index is not clean before M18 staging")
    for relative, expected in PROTECTED_UNRELATED.items():
        if _sha256(_path(relative).read_bytes()) != expected:
            raise RuntimeError(f"protected unrelated path changed: {relative}")

    manifest = _reviewed_payload_manifest()
    rows = list(manifest["rows"])
    for relative in CONTROL_PATHS:
        path = _path(relative)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required control path is absent or nonregular: {relative}")
        rows.append(_current_row(relative, role="m18_control", provenance="reviewed_exact_control_path"))

    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        previous = by_path.get(row["path"])
        if previous is not None and previous["sha256"] != row["sha256"]:
            raise RuntimeError(f"stage-path hash conflict: {row['path']}")
        by_path[row["path"]] = row

    entries: list[tuple[str, str, str]] = []
    staged_rows: list[dict[str, Any]] = []
    for relative in sorted(by_path):
        row = by_path[relative]
        raw = _payload_bytes(row) if row["role"] != "m18_control" else _path(relative).read_bytes()
        oid = _git("hash-object", "-w", "--stdin", input_bytes=raw).decode().strip()
        mode = _git_index_mode(row)
        entries.append((mode, oid, relative))
        staged_rows.append({
            "git_mode": mode,
            "git_oid": oid,
            "path": relative,
            "sha256": _sha256(raw),
            "size_bytes": len(raw),
        })

    expected_staged = set(by_path) | {STAGE_RECORD_PATH}
    record = {
        "baseline_commit": BASELINE_COMMIT,
        "control_path_count": len(CONTROL_PATHS),
        "payload_path_count": manifest["artifact_count"],
        "protected_unrelated_paths": PROTECTED_UNRELATED,
        "schema_version": "ra-literature-survey-m18-stage-record-v1",
        "self_record_note": "stage_record.json is included in staged_paths but cannot recursively describe its own blob OID",
        "staged_path_count": len(expected_staged),
        "staged_paths": sorted(expected_staged),
        "staged_rows_excluding_self": staged_rows,
        "status": "staged_exact_pending_commit",
    }
    _path(STAGE_RECORD_PATH).write_bytes(_pretty_bytes(record))
    raw = _path(STAGE_RECORD_PATH).read_bytes()
    oid = _git("hash-object", "-w", "--stdin", input_bytes=raw).decode().strip()
    entries.append(("100644", oid, STAGE_RECORD_PATH))

    index_info = b"".join(
        f"{mode} {oid}\t{relative}".encode() + b"\0"
        for mode, oid, relative in entries
    )
    subprocess.run(
        ["git", "update-index", "-z", "--add", "--index-info"],
        cwd=ROOT,
        input=index_info,
        check=True,
    )
    staged = set(_git("diff", "--cached", "--name-only", "-z").decode().split("\0")) - {""}
    if staged != expected_staged:
        raise RuntimeError(f"staged path mismatch: missing={sorted(expected_staged-staged)}, extra={sorted(staged-expected_staged)}")
    if staged & set(PROTECTED_UNRELATED):
        raise RuntimeError("protected unrelated path entered the index")
    print(json.dumps({"staged_path_count": len(staged), "status": "staged_exact_pending_commit"}, sort_keys=True))


def _whitespace_findings(*args: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", *args, "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in {0, 2}:
        raise RuntimeError(f"Git whitespace audit failed unexpectedly: {completed.stderr.strip()}")
    raw = (completed.stdout + completed.stderr).strip()
    return tuple(sorted(line for line in raw.splitlines() if line))


def _audit_stage() -> None:
    if _git("rev-parse", "HEAD").decode().strip() != BASELINE_COMMIT:
        raise RuntimeError("repository HEAD changed before staged-candidate audit")
    for relative, expected in PROTECTED_UNRELATED.items():
        if _sha256(_path(relative).read_bytes()) != expected:
            raise RuntimeError(f"protected unrelated path changed: {relative}")
    record_path = _path(STAGE_RECORD_PATH)
    if not record_path.is_file() or record_path.is_symlink():
        raise RuntimeError("M18 stage record is absent or nonregular")
    record = json.loads(record_path.read_bytes())
    expected_staged = set(record.get("staged_paths", []))
    staged = set(_git("diff", "--cached", "--name-only", "-z").decode().split("\0")) - {""}
    if staged != expected_staged or record.get("staged_path_count") != len(staged):
        raise RuntimeError("staged candidate no longer matches its stage record")
    if staged & set(PROTECTED_UNRELATED):
        raise RuntimeError("protected unrelated path entered the staged candidate")
    staged_rows = record.get("staged_rows_excluding_self")
    if not isinstance(staged_rows, list) or len(staged_rows) != len(staged) - 1:
        raise RuntimeError("stage record row coverage is invalid")
    for expected in staged_rows:
        relative = expected["path"]
        raw = _git("show", f":{relative}")
        index_record = _git("ls-files", "-s", "--", relative).decode().strip()
        match = re.fullmatch(r"(\d{6}) ([0-9a-f]{40}) 0\t(.+)", index_record)
        if match is None:
            raise RuntimeError(f"invalid staged index record: {relative}")
        mode, oid, recorded_path = match.groups()
        actual = {
            "git_mode": mode,
            "git_oid": oid,
            "path": recorded_path,
            "sha256": _sha256(raw),
            "size_bytes": len(raw),
        }
        if actual != expected:
            raise RuntimeError(f"staged row differs from stage authority: {relative}")
    findings = _whitespace_findings("diff", "--cached")
    if findings != tuple(sorted(FROZEN_WHITESPACE_EXCEPTIONS)):
        raise RuntimeError(
            "staged whitespace findings changed: "
            f"missing={sorted(set(FROZEN_WHITESPACE_EXCEPTIONS)-set(findings))}, "
            f"extra={sorted(set(findings)-set(FROZEN_WHITESPACE_EXCEPTIONS))}"
        )
    print(json.dumps({
        "frozen_whitespace_exception_count": len(findings),
        "staged_path_count": len(staged),
        "status": "staged_candidate_audit_passed",
    }, sort_keys=True))


def _commit_row(commit: str, relative: str) -> dict[str, Any]:
    raw = _git("show", f"{commit}:{relative}")
    tree_record = _git("ls-tree", commit, "--", relative).decode().strip()
    match = re.fullmatch(r"(\d{6}) blob ([0-9a-f]{40})\t(.+)", tree_record)
    if match is None:
        raise RuntimeError(f"invalid commit tree record: {relative}")
    mode, oid, recorded_path = match.groups()
    return {
        "git_mode": mode,
        "git_oid": oid,
        "path": recorded_path,
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
    }


def _validate_initial_candidate_commit(candidate: str) -> tuple[int, int]:
    parent = _single_parent(candidate)
    if parent != BASELINE_COMMIT:
        raise RuntimeError("candidate commit is not a direct child of the M18 baseline")
    protected_delta = _git(
        "diff",
        "--name-only",
        BASELINE_COMMIT,
        candidate,
        "--",
        *sorted(PROTECTED_UNRELATED),
    ).strip()
    if protected_delta:
        raise RuntimeError("protected unrelated path entered the candidate commit")
    record_raw = _git("show", f"{candidate}:{STAGE_RECORD_PATH}")
    record = json.loads(record_raw)
    if (
        record.get("baseline_commit") != BASELINE_COMMIT
        or record.get("schema_version") != "ra-literature-survey-m18-stage-record-v1"
        or record.get("status") != "staged_exact_pending_commit"
        or record.get("payload_path_count") != 1684
        or record.get("protected_unrelated_paths") != PROTECTED_UNRELATED
    ):
        raise RuntimeError("candidate stage authority is invalid")
    committed = set(
        _git("diff", "--name-only", "-z", BASELINE_COMMIT, candidate).decode().split("\0")
    ) - {""}
    expected_paths = record.get("staged_paths")
    staged_rows = record.get("staged_rows_excluding_self")
    if (
        not isinstance(expected_paths, list)
        or expected_paths != sorted(expected_paths)
        or len(expected_paths) != len(set(expected_paths))
        or committed != set(expected_paths)
        or record.get("staged_path_count") != len(committed)
        or not isinstance(staged_rows, list)
        or len(staged_rows) != len(committed) - 1
        or {row.get("path") for row in staged_rows if isinstance(row, dict)}
        != committed - {STAGE_RECORD_PATH}
    ):
        raise RuntimeError("candidate commit path set differs from stage authority")
    if _commit_row(candidate, STAGE_RECORD_PATH)["git_mode"] != "100644":
        raise RuntimeError("candidate stage record has an invalid Git mode")
    for expected in staged_rows:
        relative = expected["path"]
        if _commit_row(candidate, relative) != expected:
            raise RuntimeError(f"candidate row differs from stage authority: {relative}")
    findings = _whitespace_findings("diff", BASELINE_COMMIT, candidate)
    if findings != tuple(sorted(FROZEN_WHITESPACE_EXCEPTIONS)):
        raise RuntimeError("candidate whitespace findings differ from the frozen exception set")
    return len(committed), len(findings)


def _audit_candidate_commit() -> None:
    candidate = _git("rev-parse", "HEAD").decode().strip()
    parent = _single_parent(candidate)
    if parent == BASELINE_COMMIT:
        committed_count, finding_count = _validate_initial_candidate_commit(candidate)
        print(json.dumps({
            "candidate_commit": candidate,
            "committed_path_count": committed_count,
            "frozen_whitespace_exception_count": finding_count,
            "status": "candidate_commit_audit_passed",
        }, sort_keys=True))
        return

    grandparent = _single_parent(parent)
    if grandparent != BASELINE_COMMIT:
        raise RuntimeError("final candidate is not an initial candidate or its single repair child")
    _original_count, finding_count = _validate_initial_candidate_commit(parent)

    protected_delta = _git(
        "diff", "--name-only", BASELINE_COMMIT, candidate, "--", *sorted(PROTECTED_UNRELATED)
    ).strip()
    if protected_delta:
        raise RuntimeError("protected unrelated path entered the repaired candidate")

    manifest_raw = _git("show", f"{candidate}:{REPAIR_MANIFEST_PATH}")
    manifest = json.loads(manifest_raw)
    repair_record_raw = _git("show", f"{candidate}:{REPAIR_STAGE_RECORD_PATH}")
    repair_record = json.loads(repair_record_raw)
    required_manifest_keys = {
        "attempt",
        "failed_candidate_commit",
        "failure_class",
        "failure_evidence",
        "focused_checks",
        "repair_rows",
        "schema_version",
        "supervisor_audit",
        "unchanged_contract",
    }
    if (
        set(manifest) != required_manifest_keys
        or manifest.get("schema_version") != "ra-literature-survey-m18-repair-attempt-v1"
        or manifest.get("attempt") != 2
        or manifest.get("failed_candidate_commit") != parent
        or manifest.get("failure_class") not in REPAIR_FAILURE_CLASSES
        or manifest.get("unchanged_contract") != UNCHANGED_REPAIR_CONTRACT
    ):
        raise RuntimeError("repair manifest does not bind the exact two-commit chain")
    failure_evidence = manifest.get("failure_evidence")
    focused_checks = manifest.get("focused_checks")
    supervisor_audit = manifest.get("supervisor_audit")
    if (
        not isinstance(failure_evidence, list)
        or not failure_evidence
        or not all(
            isinstance(value, dict)
            and set(value) == {"path", "sha256"}
            and isinstance(value["path"], str)
            and value["path"].strip()
            and _is_sha256(value["sha256"])
            for value in failure_evidence
        )
        or not isinstance(focused_checks, list)
        or not focused_checks
        or not all(
            isinstance(check, dict)
            and set(check) == {"artifact", "artifact_sha256", "command", "exit_code"}
            and isinstance(check["artifact"], str)
            and check["artifact"].strip()
            and _is_sha256(check["artifact_sha256"])
            and isinstance(check["command"], str)
            and check["command"].strip()
            and check["exit_code"] == 0
            for check in focused_checks
        )
        or not isinstance(supervisor_audit, dict)
        or set(supervisor_audit) != {"artifact", "artifact_sha256"}
        or not isinstance(supervisor_audit["artifact"], str)
        or not supervisor_audit["artifact"].strip()
        or not _is_sha256(supervisor_audit["artifact_sha256"])
    ):
        raise RuntimeError("committed repair evidence references are invalid")
    required_record_keys = {
        "attempt",
        "failed_candidate_commit",
        "failure_class",
        "repair_manifest_sha256",
        "repair_path_count",
        "schema_version",
        "self_record_note",
        "staged_path_count",
        "staged_paths",
        "staged_repair_rows",
        "status",
    }
    if (
        set(repair_record) != required_record_keys
        or repair_record.get("schema_version") != "ra-literature-survey-m18-repair-stage-record-v1"
        or repair_record.get("status") != "staged_exact_descendant_repair_pending_commit"
        or repair_record.get("attempt") != 2
        or repair_record.get("failed_candidate_commit") != parent
        or repair_record.get("failure_class") != manifest["failure_class"]
        or repair_record.get("repair_manifest_sha256") != _sha256(manifest_raw)
    ):
        raise RuntimeError("repair stage record does not bind the committed repair manifest")

    committed = set(
        _git("diff", "--name-only", "-z", parent, candidate).decode().split("\0")
    ) - {""}
    expected_paths = repair_record.get("staged_paths")
    staged_rows = repair_record.get("staged_repair_rows")
    control_paths = {REPAIR_MANIFEST_PATH, REPAIR_STAGE_RECORD_PATH}
    if (
        not isinstance(expected_paths, list)
        or expected_paths != sorted(expected_paths)
        or len(expected_paths) != len(set(expected_paths))
        or committed != set(expected_paths)
        or repair_record.get("staged_path_count") != len(committed)
        or not isinstance(staged_rows, list)
        or repair_record.get("repair_path_count") != len(staged_rows)
        or len(staged_rows) != len(committed - control_paths)
        or {row.get("path") for row in staged_rows if isinstance(row, dict)}
        != committed - control_paths
        or committed & set(PROTECTED_UNRELATED)
    ):
        raise RuntimeError("repair commit path set differs from its stage authority")

    declared_rows = manifest.get("repair_rows")
    if not isinstance(declared_rows, list) or len(declared_rows) != len(staged_rows):
        raise RuntimeError("repair manifest row coverage differs from the repair stage record")
    declared_paths = [row.get("path") for row in declared_rows if isinstance(row, dict)]
    if (
        len(declared_paths) != len(declared_rows)
        or declared_paths != sorted(declared_paths)
        or len(declared_paths) != len(set(declared_paths))
    ):
        raise RuntimeError("repair manifest paths are not unique and sorted")
    declared_by_path = {
        row.get("path"): row for row in declared_rows if isinstance(row, dict)
    }
    if len(declared_by_path) != len(declared_rows) or set(declared_by_path) != committed - control_paths:
        raise RuntimeError("repair manifest paths differ from the committed repair paths")
    for expected in staged_rows:
        relative = expected["path"]
        actual = _commit_row(candidate, relative)
        if actual != expected:
            raise RuntimeError(f"repair row differs from repair stage authority: {relative}")
        declared = declared_by_path[relative]
        if (
            set(declared) != {"kind", "mode_octal", "path", "sha256", "size_bytes"}
            or _git_index_mode(declared) != expected["git_mode"]
            or declared["sha256"] != expected["sha256"]
            or declared["size_bytes"] != expected["size_bytes"]
        ):
            raise RuntimeError(f"repair manifest row differs from repair stage authority: {relative}")
    for relative, raw in (
        (REPAIR_MANIFEST_PATH, manifest_raw),
        (REPAIR_STAGE_RECORD_PATH, repair_record_raw),
    ):
        actual = _commit_row(candidate, relative)
        if actual["git_mode"] != "100644" or actual["sha256"] != _sha256(raw):
            raise RuntimeError(f"repair control has an invalid committed tree row: {relative}")

    repair_findings = _whitespace_findings("diff", parent, candidate)
    if repair_findings:
        raise RuntimeError("repair commit introduced a whitespace finding")
    final_findings = _whitespace_findings("diff", BASELINE_COMMIT, candidate)
    if final_findings != tuple(sorted(FROZEN_WHITESPACE_EXCEPTIONS)):
        raise RuntimeError("repaired candidate whitespace findings differ from the frozen exception set")
    final_committed = set(
        _git("diff", "--name-only", "-z", BASELINE_COMMIT, candidate).decode().split("\0")
    ) - {""}
    print(json.dumps({
        "candidate_commit": candidate,
        "final_committed_path_count": len(final_committed),
        "frozen_whitespace_exception_count": finding_count,
        "original_candidate_commit": parent,
        "repair_path_count": len(staged_rows),
        "status": "repaired_candidate_commit_audit_passed",
    }, sort_keys=True))


def _repair_row(expected: dict[str, Any]) -> dict[str, Any]:
    if set(expected) != {"kind", "mode_octal", "path", "sha256", "size_bytes"}:
        raise RuntimeError("repair row must contain exactly kind/mode/path/hash/size")
    relative = expected["path"]
    path = _path(relative)
    if relative in PROTECTED_UNRELATED or relative in {STAGE_RECORD_PATH, REPAIR_MANIFEST_PATH, REPAIR_STAGE_RECORD_PATH}:
        raise RuntimeError(f"repair row targets a reserved or protected path: {relative}")
    if PurePosixPath(relative).parts[0].startswith("."):
        raise RuntimeError(f"repair row targets a hidden top-level path: {relative}")
    if not _is_sha256(expected["sha256"]):
        raise RuntimeError(f"repair row has an invalid SHA-256: {relative}")
    try:
        size_bytes = int(expected["size_bytes"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"repair row has an invalid size: {relative}") from exc
    if size_bytes < 0 or size_bytes != expected["size_bytes"]:
        raise RuntimeError(f"repair row has an invalid size: {relative}")

    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        kind = "file"
        raw = path.read_bytes()
    elif stat.S_ISLNK(mode):
        kind = "symlink"
        raw = os.readlink(path).encode()
    else:
        raise RuntimeError(f"repair path is absent or unsupported: {relative}")
    actual = {
        "kind": kind,
        "mode_octal": _git_replay_mode(kind, f"{stat.S_IMODE(mode):04o}"),
        "path": relative,
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
    }
    if actual != expected:
        raise RuntimeError(f"repair row does not match worktree bytes: {relative}")
    return {**actual, "raw": raw}


def _stage_repair() -> None:
    _require_no_git_operation()
    if _git("diff", "--cached", "--name-only").strip():
        raise RuntimeError("index is not clean before M18 repair staging")
    for relative, expected in PROTECTED_UNRELATED.items():
        if _sha256(_path(relative).read_bytes()) != expected:
            raise RuntimeError(f"protected unrelated path changed: {relative}")
    manifest_path = _path(REPAIR_MANIFEST_PATH)
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("attempt-2 repair manifest is absent or nonregular")
    manifest = json.loads(manifest_path.read_bytes())
    required_keys = {
        "attempt",
        "failed_candidate_commit",
        "failure_class",
        "failure_evidence",
        "focused_checks",
        "repair_rows",
        "schema_version",
        "supervisor_audit",
        "unchanged_contract",
    }
    if set(manifest) != required_keys:
        raise RuntimeError("attempt-2 repair manifest has unexpected fields")
    if manifest["schema_version"] != "ra-literature-survey-m18-repair-attempt-v1" or manifest["attempt"] != 2:
        raise RuntimeError("attempt-2 repair manifest schema or attempt is invalid")
    failed_candidate = manifest["failed_candidate_commit"]
    if not isinstance(failed_candidate, str) or len(failed_candidate) != 40:
        raise RuntimeError("failed candidate commit is invalid")
    try:
        int(failed_candidate, 16)
    except ValueError as exc:
        raise RuntimeError("failed candidate commit is invalid") from exc
    if _git("rev-parse", "HEAD").decode().strip() != failed_candidate:
        raise RuntimeError("HEAD is not the declared failed attempt-1 candidate")
    parent = _single_parent(failed_candidate)
    if parent != BASELINE_COMMIT:
        raise RuntimeError("failed candidate is not a direct child of the M18 baseline")
    stage_record_raw = _git("show", f"{failed_candidate}:{STAGE_RECORD_PATH}")
    stage_record = json.loads(stage_record_raw)
    if (
        stage_record.get("baseline_commit") != BASELINE_COMMIT
        or stage_record.get("status") != "staged_exact_pending_commit"
        or stage_record.get("payload_path_count") != 1684
    ):
        raise RuntimeError("failed candidate lacks the expected M18 stage authority")
    if manifest["failure_class"] not in REPAIR_FAILURE_CLASSES:
        raise RuntimeError("attempt-2 failure class is not repairable under M18")
    if manifest["unchanged_contract"] != UNCHANGED_REPAIR_CONTRACT:
        raise RuntimeError("attempt-2 changes a frozen campaign boundary")
    if not isinstance(manifest["failure_evidence"], list) or not manifest["failure_evidence"]:
        raise RuntimeError("attempt-2 failure evidence is absent")
    if not all(
        isinstance(value, dict)
        and set(value) == {"path", "sha256"}
        and isinstance(value["path"], str)
        and value["path"].strip()
        and _is_sha256(value["sha256"])
        for value in manifest["failure_evidence"]
    ):
        raise RuntimeError("attempt-2 failure evidence is invalid")
    focused_checks = manifest["focused_checks"]
    if not isinstance(focused_checks, list) or not focused_checks:
        raise RuntimeError("attempt-2 focused checks are absent")
    if not all(
        isinstance(check, dict)
        and set(check) == {"artifact", "artifact_sha256", "command", "exit_code"}
        and isinstance(check["artifact"], str)
        and check["artifact"].strip()
        and _is_sha256(check["artifact_sha256"])
        and isinstance(check["command"], str)
        and check["command"].strip()
        and check["exit_code"] == 0
        for check in focused_checks
    ):
        raise RuntimeError("attempt-2 focused-check evidence is invalid")
    attempt_root = Path("/tmp") / f"ra_m18_candidate_{failed_candidate}_attempt01"
    if not attempt_root.is_dir() or attempt_root.is_symlink():
        raise RuntimeError("preserved attempt-1 root is absent or nonregular")
    supervisor_audit = manifest["supervisor_audit"]
    if not (
        isinstance(supervisor_audit, dict)
        and set(supervisor_audit) == {"artifact", "artifact_sha256"}
        and isinstance(supervisor_audit["artifact"], str)
        and supervisor_audit["artifact"].strip()
        and _is_sha256(supervisor_audit["artifact_sha256"])
    ):
        raise RuntimeError("attempt-2 supervisor audit reference is invalid")
    evidence_rows = [
        {"path": value["path"], "sha256": value["sha256"]}
        for value in manifest["failure_evidence"]
    ] + [
        {"path": check["artifact"], "sha256": check["artifact_sha256"]}
        for check in focused_checks
    ] + [{
        "path": supervisor_audit["artifact"],
        "sha256": supervisor_audit["artifact_sha256"],
    }]
    for evidence in evidence_rows:
        evidence_path = _path(evidence["path"], root=attempt_root)
        _reject_symlink_parents(evidence_path, root=attempt_root)
        if not evidence_path.is_file() or evidence_path.is_symlink():
            raise RuntimeError(f"attempt-2 evidence is absent or nonregular: {evidence['path']}")
        if _sha256(evidence_path.read_bytes()) != evidence["sha256"]:
            raise RuntimeError(f"attempt-2 evidence hash mismatch: {evidence['path']}")
    declared_rows = manifest["repair_rows"]
    if not isinstance(declared_rows, list) or not declared_rows:
        raise RuntimeError("attempt-2 repair rows are absent")
    paths = [row.get("path") for row in declared_rows if isinstance(row, dict)]
    if len(paths) != len(declared_rows) or paths != sorted(paths) or len(paths) != len(set(paths)):
        raise RuntimeError("attempt-2 repair paths are not unique and sorted")
    audit_path = _path(supervisor_audit["artifact"], root=attempt_root)
    audit = json.loads(audit_path.read_bytes())
    expected_audit = {
        "failed_candidate_commit": failed_candidate,
        "failure_class": manifest["failure_class"],
        "repair_paths": paths,
        "schema_version": "ra-literature-survey-m18-repair-supervisor-audit-v1",
        "scope_unchanged": True,
        "status": "passed",
    }
    if audit != expected_audit:
        raise RuntimeError("attempt-2 supervisor audit does not authorize the exact repair rows")

    entries: list[tuple[str, str, str]] = []
    staged_rows: list[dict[str, Any]] = []
    for declared in declared_rows:
        row = _repair_row(declared)
        raw = row.pop("raw")
        oid = _git("hash-object", "-w", "--stdin", input_bytes=raw).decode().strip()
        mode = _git_index_mode(row)
        entries.append((mode, oid, row["path"]))
        staged_rows.append({
            "git_mode": mode,
            "git_oid": oid,
            "path": row["path"],
            "sha256": _sha256(raw),
            "size_bytes": len(raw),
        })
    manifest_oid = _git("hash-object", "-w", REPAIR_MANIFEST_PATH).decode().strip()
    entries.append(("100644", manifest_oid, REPAIR_MANIFEST_PATH))
    expected_staged = set(paths) | {REPAIR_MANIFEST_PATH, REPAIR_STAGE_RECORD_PATH}
    record = {
        "attempt": 2,
        "failed_candidate_commit": failed_candidate,
        "failure_class": manifest["failure_class"],
        "repair_manifest_sha256": _sha256(manifest_path.read_bytes()),
        "repair_path_count": len(paths),
        "schema_version": "ra-literature-survey-m18-repair-stage-record-v1",
        "self_record_note": "repair_stage_record.json is included in staged_paths but cannot recursively describe its own blob OID",
        "staged_path_count": len(expected_staged),
        "staged_paths": sorted(expected_staged),
        "staged_repair_rows": staged_rows,
        "status": "staged_exact_descendant_repair_pending_commit",
    }
    _path(REPAIR_STAGE_RECORD_PATH).write_bytes(_pretty_bytes(record))
    record_oid = _git("hash-object", "-w", REPAIR_STAGE_RECORD_PATH).decode().strip()
    entries.append(("100644", record_oid, REPAIR_STAGE_RECORD_PATH))
    index_info = b"".join(f"{mode} {oid}\t{relative}".encode() + b"\0" for mode, oid, relative in entries)
    subprocess.run(
        ["git", "update-index", "-z", "--add", "--index-info"],
        cwd=ROOT,
        input=index_info,
        check=True,
    )
    staged = set(_git("diff", "--cached", "--name-only", "-z").decode().split("\0")) - {""}
    if staged != expected_staged:
        raise RuntimeError(f"repair staged-path mismatch: missing={sorted(expected_staged-staged)}, extra={sorted(staged-expected_staged)}")
    if staged & set(PROTECTED_UNRELATED):
        raise RuntimeError("protected unrelated path entered the repair index")
    print(json.dumps({"attempt": 2, "staged_path_count": len(staged), "status": record["status"]}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("plan", "materialize", "replay", "stage", "audit-stage", "audit-candidate", "stage-repair"),
    )
    parser.add_argument("--target", type=Path)
    parser.add_argument("--stage-source", action="store_true")
    parser.add_argument("--include-controls", action="store_true")
    parser.add_argument("--include-protected-worktree", action="store_true")
    args = parser.parse_args()
    if args.action == "plan":
        _write_plan_artifacts()
    elif args.action == "materialize":
        if args.target is None:
            parser.error("materialize requires --target")
        _materialize(
            args.target,
            stage_source=args.stage_source,
            include_controls=args.include_controls,
            include_protected_worktree=args.include_protected_worktree,
        )
    elif args.action == "replay":
        if args.target is None:
            parser.error("replay requires --target")
        _replay(args.target)
    elif args.action == "stage":
        _stage()
    elif args.action == "audit-stage":
        _audit_stage()
    elif args.action == "audit-candidate":
        _audit_candidate_commit()
    else:
        _stage_repair()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
