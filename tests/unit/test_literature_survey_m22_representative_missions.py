from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey import m22_representative_missions as runner


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPOSITORY_ROOT / runner.DEFAULT_MATRIX_PATH


def _matrix() -> dict:
    return runner.load_matrix(
        repository_root=REPOSITORY_ROOT,
        matrix_path=MATRIX_PATH,
    )


def test_active_matrix_has_exact_nine_case_migration_and_hash_bound_evidence() -> None:
    matrix = _matrix()

    assert [row["case_id"] for row in matrix["cases"]] == list(runner.CASE_IDS)
    assert [row["expected_terminal"] for row in matrix["cases"]] == [
        runner.EXPECTED_TERMINALS[case_id] for case_id in runner.CASE_IDS
    ]
    assert [tuple(row["evidence_ids"]) for row in matrix["cases"]] == [
        runner.EXPECTED_EVIDENCE_IDS[case_id] for case_id in runner.CASE_IDS
    ]
    assert matrix["historical_predecessor"]["status"] == (
        "preserved_superseded_human_gate_matrix"
    )
    assert matrix["cases"][0]["input"]["replay_kind"] == (
        "retained_production_topic_replay"
    )
    assert matrix["cases"][5]["input"] == {
        "inspected_count": 5,
        "residual_count": 50,
        "triaged_count": 55,
    }


def test_all_nine_cases_replay_with_separate_ledgers_and_visible_gaps() -> None:
    cases = runner.evaluate_matrix(repository_root=REPOSITORY_ROOT, matrix=_matrix())

    assert len(cases) == 9
    assert all(row["passed"] for row in cases)
    assert cases[0]["terminal"] == "ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE"
    assert "retained production evidence" in cases[0]["source_support"]["summary"]
    assert cases[2]["source_support"]["status"] == "SOURCE_GAP_BLOCKER"
    assert cases[3]["qualitative_interpretation"]["status"] == (
        "VISIBLE_NONBLOCKING_LIMITATION"
    )
    assert cases[4]["terminal"] == "OPEN_IDENTIFIER_FREE_OMISSION_RISK"
    assert cases[5]["terminal"] == (
        "OPEN_RESIDUAL_IDENTIFIER_BEARING_OMISSION_RISK"
    )
    assert cases[7]["terminal"] == "HARD_REJECT_NONHUMAN_AUTHORITY"
    assert cases[8]["terminal"] == (
        "HARD_REJECT_STALE_FOREIGN_PARTIAL_EVIDENCE"
    )
    assert all(row["claim_support_allowed"] is False for row in cases)
    assert all(row["ready_for_prose"] is False for row in cases)


def test_replay_uses_explicit_repository_root_for_retained_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from research_assistant.survey import m22_retained_reconciliation as retained

    missing = tmp_path / "installed-package-without-repository-data"
    monkeypatch.setattr(retained, "REPOSITORY_ROOT", missing)

    cases = runner.evaluate_matrix(repository_root=REPOSITORY_ROOT, matrix=_matrix())

    assert len(cases) == 9
    assert all(row["passed"] for row in cases)


def test_fresh_run_writes_replayable_manifest_ledgers_report_and_inventory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "m22-representative-real-missions"
    terminal = runner.run_representative_missions(
        repository_root=REPOSITORY_ROOT,
        matrix_path=MATRIX_PATH,
        output_root=root,
        now=iter(
            ["2026-07-19T10:00:00+00:00", "2026-07-19T10:00:01+00:00"]
        ).__next__,
    )

    assert terminal["classification"] == "M22_REPRESENTATIVE_REAL_MISSIONS_PASSED"
    assert terminal["primary_criterion_passed"] is True
    assert terminal["case_count"] == 9
    assert terminal["claim_support_allowed"] is False
    assert terminal["ready_for_prose"] is False
    assert runner.replay_representative_missions(
        repository_root=REPOSITORY_ROOT, output_root=root
    )["status"] == "passed"

    ledger = json.loads((root / "case_ledger.json").read_text())
    assert ledger["all_cases_passed"] is True
    assert [row["case_id"] for row in ledger["cases"]] == list(runner.CASE_IDS)
    assert (root / "engineering_ledger.json").is_file()
    assert (root / "source_support_ledger.json").is_file()
    assert (root / "qualitative_interpretation_ledger.json").is_file()
    assert "retained_production_topic_replay" in (root / "CASE_REPORT.md").read_text()
    assert json.loads((root / "run_manifest.json").read_text())["network_dispatch"] is False
    assert json.loads((root / "artifact_inventory.json").read_text())["files"]


def test_replay_rejects_case_source_identity_and_terminal_tampering(
    tmp_path: Path,
) -> None:
    root = tmp_path / "m22-representative-real-missions"
    runner.run_representative_missions(
        repository_root=REPOSITORY_ROOT,
        matrix_path=MATRIX_PATH,
        output_root=root,
        now=iter(
            ["2026-07-19T10:00:00+00:00", "2026-07-19T10:00:01+00:00"]
        ).__next__,
    )

    case_path = root / "case_ledger.json"
    original = case_path.read_bytes()
    payload = json.loads(original)
    payload["cases"][0]["terminal"] = "FALSE_TERMINAL"
    case_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(
        runner.M22RepresentativeMissionError,
        match="derived_artifact_replay_mismatch",
    ):
        runner.replay_representative_missions(
            repository_root=REPOSITORY_ROOT, output_root=root
        )

    case_path.write_bytes(original)
    source_ledger = root / "source_support_ledger.json"
    source_original = source_ledger.read_bytes()
    payload = json.loads(source_original)
    payload["rows"][0]["status"] = "UNBOUND_SOURCE"
    source_ledger.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(
        runner.M22RepresentativeMissionError,
        match="derived_artifact_replay_mismatch",
    ):
        runner.replay_representative_missions(
            repository_root=REPOSITORY_ROOT, output_root=root
        )

    source_ledger.write_bytes(source_original)
    terminal_path = root / "terminal_result.json"
    terminal_original = terminal_path.read_bytes()
    payload = json.loads(terminal_original)
    payload["ready_for_prose"] = True
    terminal_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(
        runner.M22RepresentativeMissionError,
        match="terminal_result_mismatch",
    ):
        runner.replay_representative_missions(
            repository_root=REPOSITORY_ROOT, output_root=root
        )


def test_matrix_hash_mismatch_fails_before_case_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_sha_file = runner._sha_file
    target = (
        REPOSITORY_ROOT
        / "docs/validation/literature_survey_north_star_m22_qualitative_assessment_2026-07-19/qualitative_assessments.json"
    ).resolve()

    def stale_sha(path: Path) -> str:
        return "0" * 64 if path.resolve() == target else original_sha_file(path)

    monkeypatch.setattr(runner, "_sha_file", stale_sha)

    with pytest.raises(runner.M22RepresentativeMissionError, match="stale_matrix_evidence"):
        runner.load_matrix(repository_root=REPOSITORY_ROOT, matrix_path=MATRIX_PATH)


def test_partial_case_evidence_fails_the_active_exact_contract() -> None:
    matrix = _matrix()
    case = matrix["cases"][-1]

    with pytest.raises(
        runner.M22RepresentativeMissionError,
        match="matrix_case_evidence_mismatch",
    ):
        runner._validate_case_evidence_ids(
            case_id=case["case_id"],
            evidence_ids=[],
            known_artifacts=set(matrix["retained_artifacts"]),
        )


def test_runner_has_no_network_credential_provider_or_pdf_interface() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8").casefold()

    assert "urllib" not in source
    assert "requests." not in source
    assert "httpx" not in source
    assert "openalex" not in source
    assert "api_key" not in source
    assert "authorization" not in source
    assert "pdf_fallback\": true" not in source
