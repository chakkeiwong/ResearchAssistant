from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def portable_m20_m21_inputs(request, tmp_path: Path, monkeypatch):
    module_name = request.module.__name__

    if module_name.endswith("test_literature_survey_m21_candidate_context_triage"):
        from research_assistant.survey import m21_candidate_context_triage as triage

        root = tmp_path / "m21-context-inputs"
        source = root / "source.body"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"test-owned retained source\n")
        flattened = root / "flattened.tex"
        flattened.write_text(
            "\\section{Method}\n" + "\n".join(f"method citation {index}" for index in range(1, 9)),
            encoding="utf-8",
        )
        candidates = [
            {
                "candidate_id": f"arxiv:test-{index:02d}",
                "bibliography_key": f"key{index:02d}",
                "title": f"Test-owned candidate {index:02d}",
                "identifiers": [f"arxiv:test-{index:02d}"],
                "source_member": "references.bib",
                "scholarly_classification": "NOT_CHECKED",
                "support_status": "SOURCE_GAP_BLOCKER",
                "action": "inspect_primary_source",
            }
            for index in range(triage.EXPECTED_CANDIDATE_COUNT)
        ]
        candidate_path = _write_json(
            root / "candidate_classifications.json",
            {"candidate_count": len(candidates), "rows": candidates},
        )
        evidence_path = _write_json(
            root / "combined_evidence.json",
            {
                "arxiv_seed": f"arxiv:{triage.EXPECTED_SEED}",
                "backward": {
                    "candidate_count": len(candidates),
                    "identifier_free_units": triage.EXPECTED_IDENTIFIER_FREE_UNITS,
                },
            },
        )
        record_path = _write_json(
            root / "record.json",
            {
                "paper_id": triage.EXPECTED_PAPER_ID,
                "source_type": "arxiv_latex",
                "status": "available",
                "primary_for_audit": True,
                "provenance": {"arxiv_id": triage.EXPECTED_SEED},
                "original_source_path": str(source),
                "flattened_source_path": str(flattened),
                "sections": [{"line": 1, "title": "Method", "labels": []}],
                "citations": [
                    {"line": index + 2, "command": "cite", "keys": [f"key{index:02d}"]}
                    for index in range(7)
                ],
            },
        )
        monkeypatch.setattr(
            triage, "EXPECTED_SOURCE_SHA256", hashlib.sha256(source.read_bytes()).hexdigest()
        )
        for name, value in {
            "CANDIDATES": candidate_path,
            "EVIDENCE": evidence_path,
            "SOURCE": source,
            "RECORD": record_path,
        }.items():
            monkeypatch.setattr(request.module, name, value)

    elif module_name.endswith("test_literature_survey_m21_seven_source_campaign"):
        from research_assistant.survey import m21_seven_source_campaign as runner

        plan = Path("tests/fixtures/historical_contracts/m21_seven_source_plan.md")
        execution_paths = tuple(plan if path == runner.PLAN_PATH else path for path in runner.EXECUTION_PATHS)
        monkeypatch.setattr(runner, "PLAN_PATH", plan)
        monkeypatch.setattr(runner, "EXECUTION_PATHS", execution_paths)

    elif module_name.endswith("test_literature_survey_m20_credential_free_live_runner"):
        from research_assistant.survey import m20_credential_free_live_runner as runner

        monkeypatch.setattr(
            runner,
            "PLAN_PATH",
            Path("tests/fixtures/historical_contracts/m20_credential_free_plan.md"),
        )
