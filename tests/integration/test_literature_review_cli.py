from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from research_assistant import cli
from research_assistant.survey.literature_review import run_literature_review


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "central_papers_e2e"
PROVIDER = Path(__file__).resolve().parents[1] / "fixtures" / "dynaremcp_document_provider.py"


def _provider() -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(PROVIDER))}"


def test_topic_to_survey_cli_reports_thin_evidence_without_promotion(tmp_path: Path, capsys) -> None:
    output = tmp_path / "topic-survey"
    code = cli.main([
        "survey", "literature-review",
        "--topic", "Neural optimal transport",
        "--out", str(output),
        "--observation-bundle", str(FIXTURES / "neural_optimal_transport" / "observations.json"),
        "--dynaremcp-command", _provider(),
        "--no-compile-latex",
    ])
    assert code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "insufficient_survey_evidence"
    assert result["accepted"] is False
    assert result["authority_class"] == "source_attributed"
    assert result["central_papers_open_risks"]
    assert result["dynaremcp_qa_status"] == "external_document_qa_passed"
    assert (output / "document" / "draft.tex").is_file()
    text = (output / "document" / "draft.tex").read_text()
    assert "In the checked source section" in text
    assert "arxiv:2106.01954" in text  # visible omission risk, not body support
    body = text.split("\\section{Limitations and open evidence risks}", 1)[0]
    assert "arxiv:2106.01954" not in body
    assert "Only one mechanism is represented" in body


def test_topic_to_survey_compiles_when_requested(tmp_path: Path) -> None:
    output = tmp_path / "topic-survey-rendered"
    result = run_literature_review(
        topic="Federated learning and privacy",
        output_dir=output,
        observation_bundle=FIXTURES / "federated_privacy" / "observations.json",
        dynaremcp_command=_provider(),
        compile_latex=True,
    )
    assert result["status"] == "source_attributed_evidence_survey"
    assert result["render_status"] in {"rendered", "renderer_failed", "renderer_unavailable"}
    if result["render_status"] == "rendered":
        assert Path(result["survey_pdf_path"]).is_file()


def test_topic_to_survey_resume_replays_completed_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "topic-survey-resume"
    first = run_literature_review(
        topic="Federated learning and privacy",
        output_dir=output,
        observation_bundle=FIXTURES / "federated_privacy" / "observations.json",
        compile_latex=False,
    )
    assert first["accepted"] is True
    second = run_literature_review(
        topic="Federated learning and privacy",
        output_dir=output,
        observation_bundle=FIXTURES / "federated_privacy" / "observations.json",
        resume=True,
        compile_latex=False,
    )
    assert second["resume_status"] == "completed_run_replayed"
    assert second["status"] == first["status"]
