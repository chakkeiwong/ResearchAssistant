from pathlib import Path


def test_release_workflow_is_explicit_and_dispatchable() -> None:
    workflow = Path(".github/workflows/python-311-release.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "concurrency:" in workflow
    assert "python-version: \"3.11\"" in workflow
    assert "python -m pip install -e \".[dev]\"" in workflow
    assert "scripts/run_static_checks.sh" in workflow
    assert "scripts/run_tests.sh" in workflow
    assert "static-checks:" in workflow
    assert "active-release-suite:" in workflow
    assert "needs: static-checks" in workflow
    assert "timeout-minutes: 10" in workflow
    assert "timeout-minutes: 45" in workflow
    assert "pull_request_target" not in workflow


def test_release_smoke_defers_pre_evidence_report_during_candidate_gate() -> None:
    smoke = Path("scripts/run_release_smoke.sh").read_text()
    assert 'RELEASE_GATE_IN_PROGRESS' in smoke
    assert 'release-report deferred until the candidate gate writes final evidence' in smoke


def test_clean_install_smoke_cannot_import_source_checkout() -> None:
    smoke = Path("scripts/run_clean_install_smoke.sh").read_text()
    assert "unset PYTHONPATH" in smoke


def test_candidate_gate_validates_the_release_smoke_workspace() -> None:
    gate = Path("scripts/run_release_candidate_gate.py").read_text()
    assert 'environment.get("WORKSPACE", "/tmp/research-assistant-release-smoke")' in gate
    assert 'final release-report: ready_for_release_candidate_review' in gate
