from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20b2_synthetic_validation.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20b2_synthetic_validation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_report_closes_required_synthetic_paths_without_canary_persistence() -> None:
    report = MODULE.build_report()
    raw = json.dumps(report, sort_keys=True)
    assert report["status"] == "passed"
    assert report["network_used"] is False
    assert report["real_credential_accessed"] is False
    assert report["canary_value_or_digest_persisted"] is False
    assert report["campaign_cost_cap_usd"] == "0.01"
    assert report["documented_route_sum_usd"] == "0.0011"
    assert report["shared_success_budget"]["dispatch_count"] == 3
    assert report["shared_success_budget"]["reserved_cost_usd"] == "0.0011"
    assert report["shared_success_budget"]["reconciled_cost_usd"] == "0.0011"
    assert "M20B2_SYNTHETIC_" not in raw
    assert {row["case_id"] for row in report["cases"]} == {
        "topic_success",
        "direct_success",
        "forward_success",
        "timeout_closed",
        "provider_http_error_closed",
        "worker_termination_closed",
        "secret_bearing_exception_closed",
        "parser_error_closed",
        "missing_credential",
        "wrong_source",
        "cost_contradiction",
    }
    for row in report["cases"]:
        assert set(row["prohibited_surface_scan"].values()) <= {"clear", "not_created"}
        assert row["authenticated_request_count"] in {0, 1}
        assert row["credential_lookup_count"] in {0, 1}
        occurrences = row["authorized_occurrence_classes"]
        if row["authenticated_request_count"] == 1:
            assert occurrences == {
                "named_source_value": 1,
                "ephemeral_authenticated_request": 1,
            }
        else:
            assert occurrences == {
                "named_source_value": 0,
                "ephemeral_authenticated_request": 0,
            }
    missing = next(row for row in report["cases"] if row["case_id"] == "missing_credential")
    assert missing["credential_lookup_count"] == 1
    wrong_source = next(row for row in report["cases"] if row["case_id"] == "wrong_source")
    assert wrong_source["credential_lookup_count"] == 0


def test_main_writes_one_secret_free_report_with_empty_streams(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    output = tmp_path / "out"
    assert MODULE.main(["--output-root", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    files = [path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()]
    assert files == ["synthetic_validation.json"]
    raw = (output / "synthetic_validation.json").read_bytes()
    assert b"M20B2_SYNTHETIC_" not in raw
    assert json.loads(raw)["status"] == "passed"


def test_existing_output_fails_before_report_write(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_text("preserve")
    with pytest.raises(FileExistsError):
        MODULE.main(["--output-root", str(output)])
    assert sentinel.read_text() == "preserve"
    assert list(output.iterdir()) == [sentinel]


def test_manifest_write_failure_leaves_no_report_or_temporary_file(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    output = tmp_path / "out"
    monkeypatch.setattr(MODULE.os, "link", lambda *args: (_ for _ in ()).throw(OSError("synthetic link failure")))
    with pytest.raises(OSError, match="synthetic link failure"):
        MODULE.main(["--output-root", str(output)])
    assert output.is_dir()
    assert list(output.iterdir()) == []


def test_script_is_synthetic_only_and_has_no_environment_or_network_lookup() -> None:
    source = SCRIPT.read_text()
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "urlopen" not in source
    assert "requests." not in source
    assert "api.openalex.org" not in source
