from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.document.contracts import DocumentInputError, load_contract, load_evidence
from research_assistant.survey.document.orchestrator import draft_document
from research_assistant.survey.document.writer import _tex
from research_assistant.survey.document.planner import build_document_plan


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scholarly_document"


def test_tex_escape_is_ascii_safe_for_extracted_pdf_symbols() -> None:
    escaped = _tex("Ls = − n Õ i=1; α × β; x ≥ 0")
    assert escaped.isascii()
    assert "-" in escaped
    assert "alpha" in escaped


def _copy_json(path: Path, tmp_path: Path) -> Path:
    target = tmp_path / path.name
    target.write_bytes(path.read_bytes())
    return target


def test_argument_plan_is_mechanism_first_and_dispositions_are_explicit() -> None:
    contract = load_contract(FIXTURE / "document_contract.json")
    bundle = load_evidence(FIXTURE / "evidence.json", contract)
    plan = build_document_plan(bundle)
    assert [section.section_id for section in plan.sections] == [
        "mechanism-constrained-allocation",
        "mechanism-sequential-adaptation",
    ]
    assert all(section.reader_entry and section.reader_exit for section in plan.sections)
    assert plan.forbidden_claim_ids == ("claim-blocked",)
    assert plan.unused_paper_ids == ()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("support_class", "SURVEY_CONTEXT_ONLY", "does not match reviewed_primary"),
        ("anchor_ids", [], "has no source anchors"),
    ],
)
def test_allowed_claims_require_primary_anchors(tmp_path: Path, field: str, value: object, message: str) -> None:
    evidence = json.loads((FIXTURE / "evidence.json").read_text())
    evidence["claims"][0][field] = value
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    with pytest.raises(DocumentInputError, match=message):
        load_evidence(path, load_contract(FIXTURE / "document_contract.json"))


def test_allowed_claim_rejects_unsafe_source(tmp_path: Path) -> None:
    evidence = json.loads((FIXTURE / "evidence.json").read_text())
    evidence["papers"][0]["safety_status"] = "quarantined"
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    with pytest.raises(DocumentInputError, match="unsafe paper"):
        load_evidence(path, load_contract(FIXTURE / "document_contract.json"))


def test_unused_paper_requires_disposition(tmp_path: Path) -> None:
    evidence = json.loads((FIXTURE / "evidence.json").read_text())
    evidence["papers"].append(
        {
            "paper_id": "paper-unused",
            "role": "DIRECT_METHOD",
            "safety_status": "checked_clear",
            "source_status": "available",
            "title": "Unused Direct Method",
        }
    )
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    bundle = load_evidence(path, load_contract(FIXTURE / "document_contract.json"))
    with pytest.raises(DocumentInputError, match="unused papers require omission dispositions"):
        build_document_plan(bundle)


def test_offline_scaffold_has_sidecar_ids_but_reader_text_does_not(tmp_path: Path) -> None:
    result = draft_document(
        evidence_path=FIXTURE / "evidence.json",
        contract_path=FIXTURE / "document_contract.json",
        output_dir=tmp_path / "run",
    )
    assert result["status"] == "reviewed_survey_candidate_synthesized"
    assert result["dynaremcp_qa_status"] == "external_document_qa_not_run"
    text = (tmp_path / "run" / "draft.tex").read_text()
    assert "claim-a" not in text and "anchor-a" not in text
    assert "Sequential Decisions, Section 3, Algorithm 1" in text
    evidence_use = json.loads((tmp_path / "run" / "evidence_use_ledger.json").read_text())
    assert evidence_use["forbidden_claim_ids"] == ["claim-blocked"]
    assert json.loads((tmp_path / "run" / "final_status.json").read_text())["render_status"] == "renderer_not_run"


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    marker = output / "prior.txt"
    marker.write_text("preserve")
    result = draft_document(
        evidence_path=FIXTURE / "evidence.json",
        contract_path=FIXTURE / "document_contract.json",
        output_dir=output,
    )
    assert result["blocked_reason"] == "output_exists"
    assert marker.read_text() == "preserve"


def test_missing_dynaremcp_is_explicit_and_nonfatal(tmp_path: Path) -> None:
    result = draft_document(
        evidence_path=FIXTURE / "evidence.json",
        contract_path=FIXTURE / "document_contract.json",
        output_dir=tmp_path / "run",
        dynaremcp_command="definitely-not-installed-dynaremcp",
    )
    assert result["status"] == "reviewed_survey_candidate_synthesized"
    assert result["dynaremcp_qa_status"] == "external_document_qa_unavailable"
