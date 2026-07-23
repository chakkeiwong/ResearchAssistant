from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.central_papers import run_central_papers_campaign
from research_assistant.survey.document.contracts import load_contract, load_evidence
from research_assistant.survey.document.orchestrator import draft_document
from research_assistant.survey.document.projection import project_central_campaign


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "central_papers_e2e"


@pytest.mark.parametrize(
    ("case_id", "topic"),
    [
        ("federated_privacy", "Federated learning and privacy"),
        ("neural_optimal_transport", "Neural optimal transport"),
        ("particle_filtering", "Particle filtering for nonlinear state-space models"),
    ],
)
def test_central_campaign_projects_source_attributed_survey(
    tmp_path: Path, case_id: str, topic: str
) -> None:
    campaign = tmp_path / "campaign"
    run_central_papers_campaign(
        topic=topic,
        output_dir=campaign,
        observation_bundle=FIXTURES / case_id / "observations.json",
    )
    projection = project_central_campaign(campaign_root=campaign, output_dir=tmp_path / "projection")
    assert projection["authority_class"] == "source_attributed"
    contract = load_contract(Path(projection["contract_path"]))
    bundle = load_evidence(Path(projection["evidence_path"]), contract)
    assert bundle.authority_class == "source_attributed"
    assert bundle.claims
    assert all(claim.support_class == "SOURCE_ATTRIBUTED_STATEMENT" for claim in bundle.claims)
    result = draft_document(
        evidence_path=Path(projection["evidence_path"]),
        contract_path=Path(projection["contract_path"]),
        output_dir=tmp_path / "document",
    )
    expected_status = (
        "source_attributed_evidence_survey"
        if len(bundle.papers) >= 2
        else "insufficient_survey_evidence"
    )
    assert result["status"] == expected_status
    text = (tmp_path / "document" / "draft.tex").read_text()
    assert "In the checked source section" in text
    assert "Cross-mechanism synthesis" in text


def test_projection_excludes_off_topic_and_source_blocked_papers(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    run_central_papers_campaign(
        topic="Neural optimal transport",
        output_dir=campaign,
        observation_bundle=FIXTURES / "neural_optimal_transport" / "observations.json",
    )
    projection = project_central_campaign(campaign_root=campaign, output_dir=tmp_path / "projection")
    evidence = json.loads(Path(projection["evidence_path"]).read_text())
    paper_ids = {row["paper_id"] for row in evidence["papers"]}
    assert "arxiv:2201.12220" in paper_ids
    assert "arxiv:1602.05629" not in paper_ids
    assert "arxiv:2106.01954" not in paper_ids
    assert any(row.get("paper_id") == "arxiv:2106.01954" for row in evidence["omissions"])
