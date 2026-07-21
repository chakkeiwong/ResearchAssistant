from __future__ import annotations

import os
import json
import copy
from pathlib import Path
import subprocess

import pytest

from research_assistant.survey import m23_operational_acceptance as acceptance


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_acceptance_matrix_has_exact_nine_cases() -> None:
    assert acceptance.CASE_IDS == (
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


def test_documentation_consistency_passes_current_operator_surface() -> None:
    report = acceptance.documentation_consistency_report(REPOSITORY_ROOT)
    assert report["status"] == "passed"
    assert all(report["checks"].values())


def test_capability_matrix_preserves_scientific_limits() -> None:
    matrix = acceptance.capability_matrix()
    by_name = {row["capability"]: row for row in matrix["rows"]}
    assert by_name["new_mission_public_scope"]["status"] == "arxiv_only"
    assert by_name["forward_citations"]["status"] == "unavailable_nonblocking"
    assert by_name["identifier_bearing_omission_frontier"]["status"] == "50_open"
    assert by_name["identifier_free_omission_frontier"]["status"] == "195_units_open"
    assert by_name["publication_or_release"]["status"] == "not_authorized"


def test_active_defaults_and_safe_next_command_are_arxiv_only() -> None:
    from research_assistant.survey import build, mission_state, orchestrate

    assert mission_state.DEFAULT_PROVIDERS == ("arxiv",)
    assert mission_state.DEFAULT_ALLOWED_DOMAINS == ("arxiv.org", "export.arxiv.org")
    assert orchestrate.PUBLIC_DISCOVERY_DEFAULT_PROVIDERS == ["arxiv"]
    assert orchestrate.PUBLIC_DISCOVERY_ALLOWED_DOMAINS == ["arxiv.org", "export.arxiv.org"]
    assert build.PUBLIC_METADATA_DEFAULT_PROVIDERS == ["arxiv"]
    commands = orchestrate._safe_next_commands(
        {"gate_id": "public_metadata"},
        Path("/tmp/mission"),
        "Neural Optimal Transport",
        ["arxiv:2201.12220v3"],
    )
    assert len(commands) == 1
    assert "--public-metadata-provider arxiv" in commands[0]
    assert "openalex" not in commands[0].casefold()


def test_acceptance_runner_has_no_network_client_or_credential_interface() -> None:
    source = Path(acceptance.__file__).read_text(encoding="utf-8").casefold()
    assert "urllib" not in source
    assert "requests." not in source
    assert "httpx" not in source
    assert "api_key" not in source
    assert "authorization" not in source
    assert "--no-index" in source
    assert "--no-deps" in source


def test_m23_generates_m22_replay_inside_fresh_acceptance_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "acceptance"
    acceptance.run_acceptance(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
    )

    generated = root / acceptance.M22_REPLAY_ROOT
    assert generated.is_dir()
    assert (generated / "case_ledger.json").is_file()
    manifest = json.loads((root / "run_manifest.json").read_text())
    assert manifest["m22_root"] == str(acceptance.M22_REPLAY_ROOT)
    assert acceptance._replay_m22_with_limitations(
        repository_root=REPOSITORY_ROOT,
        output_root=generated,
    )["status"] == "passed"


def test_offline_subprocess_environment_removes_inherited_pythonpath(monkeypatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "src:.")
    environment = acceptance._offline_subprocess_environment()

    assert "PYTHONPATH" not in environment
    assert environment["CUDA_VISIBLE_DEVICES"] == "-1"
    assert environment["PIP_NO_INDEX"] == "1"
    assert environment["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"
    assert os.environ["PYTHONPATH"] == "src:."


def test_wheel_build_uses_fresh_external_staging_and_not_repository_build(
    tmp_path: Path, monkeypatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    (repository / "README.md").write_text("readme\n", encoding="utf-8")
    package = repository / "src" / "example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    repository_build = repository / "build"
    repository_build.mkdir()
    sentinel = repository_build / "do-not-touch"
    sentinel.write_text("preserved\n", encoding="utf-8")
    dist = tmp_path / "dist"
    dist.mkdir()
    observed_build_cwds: list[Path] = []

    def fake_run(argv, *, cwd, **kwargs):
        del kwargs
        build_cwd = Path(cwd).resolve(strict=True)
        observed_build_cwds.append(build_cwd)
        assert not build_cwd.is_relative_to(repository.resolve(strict=True))
        assert (build_cwd / "pyproject.toml").read_bytes() == (
            repository / "pyproject.toml"
        ).read_bytes()
        assert (build_cwd / "README.md").read_bytes() == (
            repository / "README.md"
        ).read_bytes()
        assert (build_cwd / "src" / "example" / "__init__.py").read_bytes() == (
            package / "__init__.py"
        ).read_bytes()
        assert argv[-2:] == ["--outdir", str(dist)]
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(acceptance.subprocess, "run", fake_run)
    for _ in range(2):
        acceptance._build_wheel_from_fresh_staging(
            repository_root=repository,
            dist=dist,
            environment={"CUDA_VISIBLE_DEVICES": "-1"},
        )

    assert len(observed_build_cwds) == 2
    assert observed_build_cwds[0] != observed_build_cwds[1]
    assert sentinel.read_text(encoding="utf-8") == "preserved\n"


def test_command_cwd_boundary_rejects_repository_paths(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    external = tmp_path / "operator"
    external.mkdir()

    assert acceptance._commands_run_outside_repository(
        [{"cwd": str(external)}], repository
    )
    assert not acceptance._commands_run_outside_repository(
        [{"cwd": str(repository / "validation") }], repository
    )


def test_replay_rejects_rehashed_command_parsed_json_rewrite(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    acceptance.run_acceptance(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
    )
    ledger_path = root / "command_ledger.json"
    original = ledger_path.read_bytes()
    ledger = json.loads(original)
    ledger["commands"][0]["argv"] = ["false-command"]
    ledger_path.write_bytes(acceptance.pretty_json_bytes(ledger))

    with pytest.raises(acceptance.M23AcceptanceError, match="command_identity_replay_mismatch"):
        acceptance.replay_acceptance(
            repository_root=REPOSITORY_ROOT, output_root=root
        )

    ledger_path.write_bytes(original)
    ledger = json.loads(original)
    topic = next(row for row in ledger["commands"] if row["command_id"] == "topic_first")
    topic["parsed_json"]["status"] = "false_pass"
    ledger_path.write_bytes(acceptance.pretty_json_bytes(ledger))

    with pytest.raises(acceptance.M23AcceptanceError, match="command_parsed_json_mismatch"):
        acceptance.replay_acceptance(
            repository_root=REPOSITORY_ROOT, output_root=root
        )


def test_replay_rejects_rehashed_case_projection_rewrite(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    acceptance.run_acceptance(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
    )
    cases_path = root / "case_results.json"
    cases = json.loads(cases_path.read_text())
    cases["cases"][0]["observed"]["module_path"] = "/false/site-packages/research_assistant/__init__.py"
    cases_path.write_bytes(acceptance.pretty_json_bytes(cases))

    with pytest.raises(acceptance.M23AcceptanceError, match="acceptance_case_replay_mismatch"):
        acceptance.replay_acceptance(
            repository_root=REPOSITORY_ROOT, output_root=root
        )


def test_case_predicates_reject_round2_false_pass_mutations(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    acceptance.run_acceptance(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
    )
    ledger = json.loads((root / "command_ledger.json").read_text())
    rows = ledger["commands"]

    wrong_version = copy.deepcopy(rows)
    next(row for row in wrong_version if row["command_id"] == "version")["parsed_json"] = {
        "package": "wrong-package",
        "version": "0.1.0",
    }
    assert not acceptance._validate_cases(
        wrong_version, repository_root=REPOSITORY_ROOT, output_root=root
    )[0]["passed"]

    false_resume = copy.deepcopy(rows)
    resumed = next(row for row in false_resume if row["command_id"] == "seed_resume")["parsed_json"]
    resumed["local_supervisor"]["ready_for_prose"] = True
    resumed["local_supervisor"]["transition_count"] = 1
    assert not acceptance._validate_cases(
        false_resume, repository_root=REPOSITORY_ROOT, output_root=root
    )[4]["passed"]

    hidden_limits = copy.deepcopy(rows)
    replayed = next(row for row in hidden_limits if row["command_id"] == "m22_replay")["parsed_json"]
    replayed["open_limitations"] = {
        "forward_citations": "available",
        "identifier_bearing_rows_open": 0,
        "identifier_free_units_open": 0,
    }
    assert not acceptance._validate_cases(
        hidden_limits, repository_root=REPOSITORY_ROOT, output_root=root
    )[6]["passed"]
