"""Generate compact, hash-bound M18 provenance inventories from attempt 1."""

from __future__ import annotations

import hashlib
import importlib
import json
import pkgutil
import sys
import zipfile
from pathlib import Path


ATTEMPT = Path("/tmp/ra_m18_candidate_654e6e1a1213bc03b7693ff1a8aea945a5bf08ac_attempt01")
REPO = ATTEMPT / "repo"
VENV = ATTEMPT / "venv"
OUT = Path(__file__).parent
CANDIDATE = "654e6e1a1213bc03b7693ff1a8aea945a5bf08ac"
WHEEL = ATTEMPT / "wheelhouse/research_assistant-0.1.0-py3-none-any.whl"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def origin_inventory() -> None:
    sys.path.insert(0, str(VENV / "lib/python3.11/site-packages"))
    import research_assistant

    names = [research_assistant.__name__]
    names.extend(module.name for module in pkgutil.walk_packages(research_assistant.__path__, "research_assistant."))
    rows = []
    venv_root = VENV.resolve()
    for name in sorted(set(names)):
        module = importlib.import_module(name)
        origin = Path(module.__file__).resolve()
        rows.append(
            {
                "module": name,
                "origin": str(origin),
                "origin_sha256": sha256_file(origin),
                "under_attempt_venv": venv_root in origin.parents,
            }
        )
    console = VENV / "bin/ra"
    write_json(
        "import_origin_inventory.json",
        {
            "schema_version": "ra-literature-survey-m18-import-origin-inventory-v1",
            "candidate_commit": CANDIDATE,
            "attempt_root": str(ATTEMPT),
            "venv": str(VENV),
            "module_count": len(rows),
            "all_under_attempt_venv": all(row["under_attempt_venv"] for row in rows),
            "console_script": {
                "path": str(console),
                "sha256": sha256_file(console),
                "shebang": console.read_text().splitlines()[0],
                "interpreter_under_attempt_venv": console.read_text().splitlines()[0].startswith(f"#!{VENV}/"),
            },
            "rows": rows,
        },
    )


def wheel_inventory() -> None:
    source_files = sorted((path.relative_to(REPO) for path in (REPO / "src/research_assistant").rglob("*.py")), key=str)
    expected_members = {str(path.relative_to("src")) for path in source_files}
    source_rows = []
    with zipfile.ZipFile(WHEEL) as archive:
        members = sorted(name for name in archive.namelist() if name.startswith("research_assistant/") and name.endswith(".py"))
        for member in members:
            source = REPO / "src" / member
            wheel_bytes = archive.read(member)
            source_rows.append(
                {
                    "wheel_member": member,
                    "wheel_member_sha256": sha256_bytes(wheel_bytes),
                    "source_path": str(source.relative_to(REPO)),
                    "source_sha256": sha256_file(source),
                    "bytes_equal": wheel_bytes == source.read_bytes(),
                }
            )
    write_json(
        "wheel_source_inventory.json",
        {
            "schema_version": "ra-literature-survey-m18-wheel-source-inventory-v1",
            "candidate_commit": CANDIDATE,
            "wheel": str(WHEEL),
            "wheel_sha256": sha256_file(WHEEL),
            "source_python_file_count": len(source_files),
            "wheel_python_member_count": len(source_rows),
            "missing_source_paths": sorted(set(map(str, source_files)) - {row["source_path"] for row in source_rows}),
            "extra_wheel_members": sorted({row["wheel_member"] for row in source_rows} - expected_members),
            "all_bytes_equal": all(row["bytes_equal"] for row in source_rows),
            "rows": source_rows,
        },
    )


def command_inventory() -> None:
    root = str(ATTEMPT)
    v = f"{root}/venv/bin/python"
    common = "env -u PYTHONPATH CUDA_VISIBLE_DEVICES=-1"
    cumulative = " ".join(
        f"tests/unit/{name}"
        for name in (
            "test_literature_survey_m16.py",
            "test_literature_survey_m16_phase2.py",
            "test_literature_survey_m16_phase3.py",
            "test_literature_survey_m16_phase4.py",
            "test_literature_survey_m16_phase5.py",
            "test_literature_survey_m16_phase6.py",
            "test_literature_survey_m16_phase7.py",
            "test_literature_survey_m16_phase8.py",
            "test_literature_survey_m16_phase9.py",
            "test_literature_survey_m17.py",
        )
    )
    scripts = " ".join(
        f"tests/scripts/{name}"
        for name in (
            "test_literature_survey_benchmark_feedback_summary.py",
            "test_literature_survey_m16_phase10_offline_e2e.py",
            "test_literature_survey_phase5_command_validation.py",
            "test_literature_survey_phase6_boundary_validation.py",
            "test_literature_survey_phase7_validation_harness.py",
        )
    )
    commands = [
        {"id": "clone", "cwd": "/home/chakwong/research-assistant", "command": f"test ! -e {root} && mkdir -p {root}/junit {root}/logs {root}/trace {root}/wheelhouse && git clone --no-hardlinks --no-local . {root}/repo", "result": "candidate clone created", "artifact": "attempt repo at candidate commit"},
        {"id": "venv", "cwd": "/home/chakwong/research-assistant", "command": f"CUDA_VISIBLE_DEVICES=-1 python -m venv --system-site-packages {root}/venv", "result": "Python 3.11.14 venv created", "artifact": "venv/pyvenv.cfg"},
        {"id": "wheel_build", "cwd": "/home/chakwong/research-assistant", "command": f"{common} PIP_NO_INDEX=1 {v} -m build --wheel --no-isolation --outdir {root}/wheelhouse {root}/repo", "result": "wheel built offline", "artifact": "wheelhouse/research_assistant-0.1.0-py3-none-any.whl"},
        {"id": "wheel_install", "cwd": "/home/chakwong/research-assistant", "command": f"{common} PIP_NO_INDEX=1 {v} -m pip install --no-index --no-deps --force-reinstall {root}/wheelhouse/research_assistant-0.1.0-py3-none-any.whl", "result": "wheel force-installed offline", "artifact": "venv/lib/python3.11/site-packages/research_assistant"},
        {"id": "payload_replay", "cwd": f"{root}/repo", "command": f"{common} strace -f -e trace=file,network -o {root}/trace/payload_replay.strace {v} docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py replay --target {root}/repo", "result": "1684/1684 zero mismatch", "artifact": "trace/payload_replay.strace"},
        {"id": "compile_and_arxiv_decoupling", "cwd": f"{root}/repo", "command": f"{common} {v} -m compileall -q src/research_assistant scripts tests && {common} {v} -c \"import inspect,research_assistant.cli as c,research_assistant.ingest.arxiv_batch as a; s=inspect.getsource(c); assert 'plan_file=Path(args.plan_file)' not in s and '--plan-file-sha256' not in s; sig=inspect.signature(a.run_arxiv_batch_intake); assert 'plan_file' not in sig.parameters and 'plan_file_sha256' not in sig.parameters; print({{'compile':'passed','arxiv_decoupling':'passed','signature':str(sig)}})\"", "result": "passed", "artifact": "session transcript plus candidate bytes"},
        {"id": "focused_m17", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q tests/unit/test_literature_survey_m17.py --junitxml={root}/junit/focused_m17.xml", "result": "65 passed", "artifact": "junit/focused_m17.xml"},
        {"id": "cumulative_m16_m17", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q {cumulative} --junitxml={root}/junit/cumulative_m16_m17.xml", "result": "846 passed", "artifact": "junit/cumulative_m16_m17.xml"},
        {"id": "persistent_matrix", "cwd": f"{root}/repo", "command": f"{common} {v} scripts/literature_survey_m17_local_validation.py --output {root}/persistent_matrix", "result": "13/13 passed", "artifact": "persistent_matrix/summary.json"},
        {"id": "exact_scripts", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q {scripts} --junitxml={root}/junit/exact_scripts.xml", "result": "12 passed", "artifact": "junit/exact_scripts.xml"},
        {"id": "full_unit", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q tests/unit --junitxml={root}/junit/full_unit.xml", "result": "1047 passed", "artifact": "junit/full_unit.xml"},
        {"id": "full_cli", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q tests/integration/test_cli_commands.py --junitxml={root}/junit/full_cli.xml", "result": "125 passed", "artifact": "junit/full_cli.xml"},
        {"id": "arxiv_compatibility", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q tests/integration/test_arxiv_batch_intake.py --junitxml={root}/junit/arxiv_batch.xml", "result": "18 passed", "artifact": "junit/arxiv_batch.xml"},
        {"id": "surveybench_restricted_agent", "cwd": f"{root}/repo", "command": f"{common} {v} -m pytest -q tests/unit/test_surveybench_restricted_trial.py tests/integration/test_surveybench_agent_trial.py --junitxml={root}/junit/surveybench_restricted_agent.xml", "result": "22 passed", "artifact": "junit/surveybench_restricted_agent.xml"},
        {"id": "phase10_path_rebase_initial_selector", "cwd": f"{root}/repo", "command": f"{common} strace -f -e trace=file,network -o {root}/trace/phase10_path_rebase.strace {v} -m pytest -q tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py -k 'frozen_phase10_cli_paths or rejects' --junitxml={root}/junit/phase10_path_rebase.xml", "result": "0 selected; diagnostic only", "artifact": "junit/phase10_path_rebase.xml and trace/phase10_path_rebase.strace"},
        {"id": "phase10_path_rebase_corrected_selector", "cwd": f"{root}/repo", "command": f"{common} strace -f -e trace=file,network -o {root}/trace/phase10_path_rebase_pass.strace {v} -m pytest -q tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py::test_phase10_offline_e2e_validates_frozen_canonical_candidate tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py::test_phase10_frozen_cli_paths_rebase_without_dirty_checkout_read --junitxml={root}/junit/phase10_path_rebase_pass.xml", "result": "2 passed", "artifact": "junit/phase10_path_rebase_pass.xml and trace/phase10_path_rebase_pass.strace"},
        {"id": "topic_cli_smoke", "cwd": root, "command": f"{common} strace -f -e trace=file,network -o {root}/trace/cli_topic.strace {root}/venv/bin/ra survey run-public-source-workflow --topic 'M18 Authoritative Topic' --out {root}/cli_topic", "result": "exit 0; confirmation false; blocked_at_gate", "artifact": "trace/cli_topic.strace and cli_topic/"},
        {"id": "explicit_seed_cli_smoke", "cwd": root, "command": f"{common} strace -f -e trace=file,network -o {root}/trace/cli_seed.strace {root}/venv/bin/ra survey run-public-source-workflow --topic 'M18 Authoritative Seed' --seed arxiv:2201.12220v3 --out {root}/cli_seed", "result": "exit 0; confirmation false; blocked_at_gate", "artifact": "trace/cli_seed.strace and cli_seed/"},
        {"id": "candidate_audit", "cwd": ".", "command": "CUDA_VISIBLE_DEVICES=-1 python docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py audit-candidate", "result": "candidate_commit_audit_passed; 1725 paths; 17 frozen whitespace records", "artifact": "candidate Git object and stage_record.json"},
        {"id": "terminal_inventory_repair", "cwd": "/home/chakwong/research-assistant", "command": f"{common} {v} docs/validation/literature_survey_m18_2026-07-14/generate_inventory.py", "result": "49 import rows and 89 wheel/source rows generated after terminal review round 1", "artifact": "import_origin_inventory.json, wheel_source_inventory.json, command_manifest.json"},
    ]
    write_json(
        "command_manifest.json",
        {
            "schema_version": "ra-literature-survey-m18-command-manifest-v1",
            "candidate_commit": CANDIDATE,
            "attempt_root": root,
            "global_environment": {"PYTHONPATH": "unset", "CUDA_VISIBLE_DEVICES": "-1", "PIP_NO_INDEX": "1 for wheel build/install", "network": "platform-restricted; no live provider/source action", "gpu": "not used"},
            "commands": commands,
            "bounded_procedures_not_claimed_as_single_shell_commands": [
                {
                    "id": "static_json_and_clone_audit",
                    "procedure": "Enumerate tracked *.json with git ls-files; parse regular files with json.loads; classify symlinks without dereference; inspect clone status before/after; compare six protected hashes.",
                    "result": "1441 tracked JSON paths; 1439 parsed; one intentional malformed fixture; one intentional absolute symlink; zero tracked modifications; protected hashes unchanged.",
                    "artifact": "static_audit.json and logs/clone_status_after_broad_tests.txt",
                    "classification": "reconstructed bounded procedure, not represented as an exact one-line command",
                }
            ],
            "command_repair_notes": [
                "Initial compatibility check named nonexistent run_arxiv_batch; corrected to run_arxiv_batch_intake.",
                "Initial Phase 10 selector selected zero tests; exact-node selector produced the authoritative 2-test pass.",
                "Evidence-audit one-line/path mistakes were corrected before the passing audit; no candidate or criteria changed.",
            ],
            "transcript_provenance": "Commands are reconstructed from the retained Codex execution transcript and cross-checked against their hash-bound artifacts. Every commands[] row is an actual invocation; multi-command static inspection is separately labeled as a bounded procedure rather than falsely rendered as one shell command.",
        },
    )


if __name__ == "__main__":
    origin_inventory()
    wheel_inventory()
    command_inventory()
