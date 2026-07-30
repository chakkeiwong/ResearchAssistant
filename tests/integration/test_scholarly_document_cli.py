from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from research_assistant import cli


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scholarly_document"
PROVIDER = Path(__file__).resolve().parents[1] / "fixtures" / "dynaremcp_document_provider.py"


def test_draft_document_cli_writes_bounded_scaffold(tmp_path: Path, capsys) -> None:
    output = tmp_path / "document-run"
    code = cli.main(
        [
            "survey",
            "draft-document",
            "--evidence",
            str(FIXTURE / "evidence.json"),
            "--contract",
            str(FIXTURE / "document_contract.json"),
            "--out",
            str(output),
        ]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "reviewed_survey_candidate_synthesized"
    assert (output / "argument_plan.json").is_file()
    assert (output / "draft.tex").is_file()


def test_draft_document_cli_uses_dynaremcp_through_subprocess(tmp_path: Path, capsys) -> None:
    provider = f"{shlex.quote(sys.executable)} {shlex.quote(str(PROVIDER))}"
    output = tmp_path / "document-run-provider"
    code = cli.main(
        [
            "survey",
            "draft-document",
            "--evidence",
            str(FIXTURE / "evidence.json"),
            "--contract",
            str(FIXTURE / "document_contract.json"),
            "--out",
            str(output),
            "--dynaremcp-command",
            provider,
        ]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["dynaremcp_qa_status"] == "external_document_qa_passed"
    qa = json.loads((output / "dynaremcp_qa.json").read_text())
    assert qa["provider_result"]["index"]["entry_path"] == "draft.tex"
    assert qa["provider_result"]["findings"] == []
