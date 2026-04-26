from __future__ import annotations

import json
import io
import os
import tarfile
import tomllib
from pathlib import Path

from research_assistant.cli import main


def _json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_project_metadata_exposes_ra_entrypoint() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    assert pyproject["project"]["name"] == "research-assistant"
    assert pyproject["project"]["requires-python"] == ">=3.10"
    assert pyproject["project"]["scripts"]["ra"] == "research_assistant.cli:main"
    assert Path("CHANGELOG.md").exists()
    assert Path("scripts/run_clean_install_smoke.sh").exists()
    assert os.access("scripts/run_clean_install_smoke.sh", os.X_OK)
    assert Path("scripts/build_release_artifacts.sh").exists()
    assert os.access("scripts/build_release_artifacts.sh", os.X_OK)
    assert Path("docs/onboarding_trial.md").exists()
    assert Path("docs/known_limitations.md").exists()
    assert Path("docs/platform_support.md").exists()
    assert Path("docs/support.md").exists()
    assert Path("docs/release_notes_0.1.0.md").exists()
    assert Path("docs/release_notes_template.md").exists()
    assert Path(".github/ISSUE_TEMPLATE/individual_release_bug.md").exists()


def test_init_config_doctor_privacy_and_workspace_lifecycle(tmp_path: Path, capsys) -> None:
    rc = main(["--root", str(tmp_path), "init"])
    init_payload = _json_out(capsys)
    assert rc == 0
    assert init_payload["status"] == "initialized"
    assert init_payload["offline_mode"] is True
    assert (tmp_path / ".research-assistant" / "config.json").exists()
    assert (tmp_path / "local_research" / "analysis" / "derivations").is_dir()
    assert (tmp_path / "local_research" / "exports" / "backups").is_dir()

    rc = main(["--root", str(tmp_path), "init"])
    second_init = _json_out(capsys)
    assert rc == 0
    assert second_init["status"] == "already_initialized"
    assert second_init["config_written"] is False

    rc = main(["--root", str(tmp_path), "config", "show"])
    config = _json_out(capsys)
    assert rc == 0
    assert config["config"]["offline_mode"] is True
    assert config["validation"]["status"] == "ok"

    rc = main(["--root", str(tmp_path), "config", "set", "default_timeout_seconds", "42"])
    updated = _json_out(capsys)
    assert rc == 0
    assert updated["config"]["default_timeout_seconds"] == 42

    rc = main(["--root", str(tmp_path), "config", "validate"])
    validation = _json_out(capsys)
    assert rc == 0
    assert validation["status"] == "ok"

    rc = main(["--root", str(tmp_path), "workspace", "validate"])
    workspace = _json_out(capsys)
    assert rc == 0
    assert workspace["status"] == "ok"

    rc = main(["--root", str(tmp_path), "workspace", "migrate"])
    migration = _json_out(capsys)
    assert rc == 0
    assert migration["dry_run"] is True
    assert migration["migration_needed"] is False

    rc = main(["--root", str(tmp_path), "workspace", "repair"])
    repair = _json_out(capsys)
    assert rc == 0
    assert repair["dry_run"] is True
    assert repair["destructive"] is False

    rc = main(["--root", str(tmp_path), "doctor"])
    doctor = _json_out(capsys)
    assert rc == 0
    assert doctor["workspace_status"] == "ok"
    assert doctor["offline_mode"] is True
    assert doctor["providers_enabled"] is False
    assert {tool["tool"] for tool in doctor["optional_tools"]} >= {"pdftotext", "markitdown", "marker_single", "magic-pdf"}
    assert doctor["platform"]["python_executable"]
    assert doctor["workflow_readiness"]["core_local_lifecycle"]["status"] == "ok"
    assert "pdf_text_ingest" in doctor["workflow_readiness"]

    rc = main(["--root", str(tmp_path), "doctor", "--matrix"])
    doctor_matrix = _json_out(capsys)
    assert rc == 0
    assert "parser_tool_matrix" in doctor_matrix

    rc = main(["--root", str(tmp_path), "parser-tool-matrix"])
    matrix = _json_out(capsys)
    assert rc == 0
    assert matrix["workflow_readiness"]["demo_workflow"]["status"] == "ok"

    rc = main(["--root", str(tmp_path), "parser-benchmark-smoke"])
    benchmark = _json_out(capsys)
    assert rc == 0
    assert benchmark["fixture_count"] >= 1
    assert benchmark["requires_human_review"] is True

    rc = main(["--root", str(tmp_path), "privacy", "status"])
    privacy = _json_out(capsys)
    assert rc == 0
    assert privacy["status"] == "ok"
    assert privacy["network_required_for_default_workflows"] is False
    assert privacy["live_llm_calls_enabled"] is False

    rc = main(["version"])
    version = _json_out(capsys)
    assert rc == 0
    assert version["package"] == "research-assistant"
    assert version["workspace_schema_version"].startswith("individual-release-workspace")

    rc = main(["--root", str(tmp_path), "platform-status"])
    platform = _json_out(capsys)
    assert rc == 0
    assert platform["python_executable"]
    assert platform["support_tier"]
    assert "is_wsl" in platform


def test_backup_create_inspect_and_restore_dry_run(tmp_path: Path, capsys) -> None:
    main(["--root", str(tmp_path), "init"])
    capsys.readouterr()
    note = tmp_path / "local_research" / "analysis" / "notes.json"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(json.dumps({"kind": "backup fixture"}))

    output = tmp_path / "local_research" / "exports" / "backups" / "fixture_backup.tar.gz"
    rc = main(["--root", str(tmp_path), "backup", "create", "--output", str(output)])
    backup = _json_out(capsys)
    assert rc == 0
    assert backup["status"] == "created"
    assert backup["backup_path"] == str(output)
    assert backup["manifest"]["file_count"] >= 2

    with tarfile.open(output, "r:gz") as archive:
        names = set(archive.getnames())
    assert "research_assistant_backup_manifest.json" in names
    assert "local_research/analysis/notes.json" in names
    assert "local_research/exports/backups/fixture_backup.tar.gz" not in names

    rc = main(["backup", "inspect", "--path", str(output)])
    inspected = _json_out(capsys)
    assert rc == 0
    assert inspected["status"] == "ok"
    assert inspected["manifest"]["file_count"] == backup["manifest"]["file_count"]

    rc = main(["--root", str(tmp_path), "backup", "restore", "--path", str(output)])
    restored = _json_out(capsys)
    assert rc == 0
    assert restored["status"] == "dry_run_complete"
    assert restored["dry_run"] is True
    assert restored["would_overwrite_count"] >= 1

    target = tmp_path / "restored"
    rc = main([
        "--root", str(target),
        "backup", "restore",
        "--path", str(output),
        "--no-dry-run",
        "--confirm-restore",
    ])
    restored_real = _json_out(capsys)
    assert rc == 0
    assert restored_real["status"] == "restored"
    assert restored_real["restored_file_count"] >= 2
    assert restored_real["post_restore_workspace_init"]["status"] in {"initialized", "already_initialized"}
    assert (target / "local_research" / "analysis" / "notes.json").exists()

    rc = main([
        "--root", str(target),
        "backup", "restore",
        "--path", str(output),
        "--no-dry-run",
    ])
    blocked = _json_out(capsys)
    assert rc == 0
    assert blocked["status"] == "blocked"
    assert blocked["issues"][0]["code"] == "restore_confirmation_required"

    rc = main([
        "--root", str(target),
        "backup", "restore",
        "--path", str(output),
        "--no-dry-run",
        "--confirm-restore",
    ])
    overwrite_blocked = _json_out(capsys)
    assert rc == 0
    assert overwrite_blocked["status"] == "blocked"
    assert overwrite_blocked["issues"][0]["code"] == "overwrite_not_allowed"

    rc = main([
        "--root", str(target),
        "backup", "restore",
        "--path", str(output),
        "--no-dry-run",
        "--confirm-restore",
        "--allow-overwrite",
    ])
    overwrite = _json_out(capsys)
    assert rc == 0
    assert overwrite["status"] == "restored"
    assert overwrite["safety_backup_path"]


def test_demo_setup_run_clean_and_release_report(tmp_path: Path, capsys) -> None:
    demo_root = tmp_path / "demo_workspace"
    rc = main(["--root", str(demo_root), "demo", "setup"])
    setup = _json_out(capsys)
    assert rc == 0
    assert setup["status"] == "ready"
    assert setup["paper_id"] == "demo_transport_paper"
    assert (demo_root / ".research-assistant" / "demo.json").exists()

    rc = main(["--root", str(demo_root), "demo", "run"])
    run = _json_out(capsys)
    assert rc == 0
    assert run["status"] == "completed"
    assert run["requires_human_review"] is True
    assert Path(run["backup_path"]).exists()

    rc = main(["--root", str(demo_root), "release-report"])
    report = _json_out(capsys)
    assert rc == 0
    assert report["status"] in {"ready_for_release_candidate_review", "warnings"}
    assert report["schema_version"].startswith("individual-release-report")
    assert report["privacy"]["network_required_for_default_workflows"] is False
    assert all(row["exists"] for row in report["docs"])
    assert all(row["exists"] for row in report["scripts"])
    assert report["release_material_mode"] == "source_checkout"
    assert report["version_consistency"]["status"] == "ok"
    assert report["corruption_hardening"]["status"] == "ok"

    rc = main(["--root", str(demo_root), "demo", "clean"])
    clean = _json_out(capsys)
    assert rc == 0
    assert clean["status"] == "dry_run_complete"
    assert clean["dry_run"] is True
    assert str(demo_root / "local_research") in clean["would_remove"]


def test_demo_setup_refuses_existing_non_demo_workspace(tmp_path: Path, capsys) -> None:
    summaries = tmp_path / "local_research" / "summaries"
    summaries.mkdir(parents=True)
    (summaries / "real_paper.json").write_text(json.dumps({"id": "real_paper"}))

    rc = main(["--root", str(tmp_path), "demo", "setup"])
    payload = _json_out(capsys)
    assert rc == 0
    assert payload["status"] == "blocked"
    assert "existing files" in payload["reason"]
    assert not (tmp_path / ".research-assistant" / "demo.json").exists()


def test_bounded_workflow_diagnostic_and_performance_smoke(tmp_path: Path, capsys) -> None:
    rc = main([
        "--root", str(tmp_path),
        "bounded-workflow", "diagnostic",
        "--workflow", "fixture-slow-parser",
        "--timeout-seconds", "1",
        "--elapsed-seconds", "1.25",
    ])
    diagnostic = _json_out(capsys)
    assert rc == 0
    assert diagnostic["artifact_type"] == "bounded_workflow_diagnostic"
    assert diagnostic["status"] == "timed_out"
    assert diagnostic["requires_human_review"] is True
    assert (tmp_path / "local_research" / "jobs" / f"{diagnostic['artifact_id']}.json").exists()

    output = tmp_path / "perf.json"
    rc = main([
        "--root", str(tmp_path),
        "performance", "smoke",
        "--synthetic-count", "3",
        "--include-industrial-artifacts",
        "--include-backup",
        "--include-export",
        "--output", str(output),
    ])
    perf = _json_out(capsys)
    assert rc == 0
    assert perf["synthetic_count"] == 3
    assert perf["created_records"] == 3
    assert perf["validation_status"] in {"ok", "warnings"}
    assert perf["requires_human_review"] is True
    assert perf["artifact_index_id"]
    assert perf["backup_path"]
    assert perf["export_path"]
    assert perf["report_artifact_id"]
    assert output.exists()


def test_release_artifacts_onboarding_and_corruption_checks(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    artifact = dist / "research_assistant-0.1.0-py3-none-any.whl"
    artifact.write_text("fake wheel for manifest smoke")

    rc = main(["release-artifacts", "manifest", "--dist-dir", str(dist)])
    manifest = _json_out(capsys)
    assert rc == 0
    assert manifest["status"] == "ok"
    assert manifest["artifact_count"] == 1
    assert (dist / "release_artifacts_manifest.json").exists()

    rc = main(["onboarding-report"])
    onboarding = _json_out(capsys)
    assert rc == 0
    assert onboarding["status"] == "ready_for_trial"
    assert "run demo run" in onboarding["checklist"]
    assert "restore backup dry-run" in onboarding["checklist"]

    main(["--root", str(tmp_path), "init"])
    capsys.readouterr()
    (tmp_path / ".research-assistant" / "config.json").write_text("{bad json")
    rc = main(["--root", str(tmp_path), "config", "validate"])
    config_validation = _json_out(capsys)
    assert rc == 0
    assert config_validation["status"] == "blocked"
    assert config_validation["issues"][0]["code"] == "invalid_json"


def test_backup_inspect_rejects_unsafe_archive(tmp_path: Path, capsys) -> None:
    unsafe = tmp_path / "unsafe.tar.gz"
    with tarfile.open(unsafe, "w:gz") as archive:
        info = tarfile.TarInfo("../evil.txt")
        data = b"nope"
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))

    rc = main(["backup", "inspect", "--path", str(unsafe)])
    payload = _json_out(capsys)
    assert rc == 0
    assert payload["status"] == "blocked"
    assert any(issue["code"] == "manifest_missing" for issue in payload["issues"])
    assert any(issue["code"] == "unsafe_archive_path" for issue in payload["issues"])
