from __future__ import annotations

import json
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
    assert report["status"] == "ready_for_release_candidate_review"
    assert report["privacy"]["network_required_for_default_workflows"] is False
    assert all(row["exists"] for row in report["docs"])
    assert all(row["exists"] for row in report["scripts"])

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

    rc = main(["--root", str(tmp_path), "performance", "smoke", "--synthetic-count", "3"])
    perf = _json_out(capsys)
    assert rc == 0
    assert perf["synthetic_count"] == 3
    assert perf["created_records"] == 3
    assert perf["validation_status"] in {"ok", "warnings"}
    assert perf["requires_human_review"] is True
