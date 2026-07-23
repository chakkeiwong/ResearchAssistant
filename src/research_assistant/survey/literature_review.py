"""ResearchAssistant-owned topic-to-survey orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.central_papers import (
    run_central_papers_campaign,
    validate_central_papers_campaign,
)
from research_assistant.survey.mission_state import MissionStateError

from .document.contracts import DocumentInputError, load_contract, load_evidence, sha256_file, write_json
from .document.orchestrator import draft_document
from .document.projection import project_central_campaign


RESULT_SCHEMA = "ra.topic_to_survey_result.v1"
MANIFEST_SCHEMA = "ra.topic_to_survey_manifest.v1"
NONCLAIMS = [
    "literature completeness",
    "universal central-paper recall",
    "scientific correctness",
    "statistically supported paper or method ranking",
    "publication readiness",
    "autonomous expert authorship",
]


def run_literature_review(
    *,
    topic: str,
    output_dir: Path,
    confirm_public_discovery: bool = False,
    observation_bundle: Path | None = None,
    resume: bool = False,
    dynaremcp_command: str | None = None,
    compile_latex: bool = True,
) -> dict[str, Any]:
    root = output_dir.expanduser().absolute()
    assert_public_write_path_allowed(root)
    final_path = root / "literature_review_result.json"
    manifest_path = root / "literature_review_manifest.json"
    if resume and final_path.is_file() and manifest_path.is_file():
        return _validate_completed_run(root, topic)
    if not resume and root.exists() and (root.is_symlink() or not root.is_dir() or any(root.iterdir())):
        return _blocked(root, "output_exists", "fresh literature-review output must be absent or empty")
    root.mkdir(parents=True, exist_ok=True)
    central_root = root / "central_papers"
    try:
        central_report = run_central_papers_campaign(
            topic=topic,
            output_dir=central_root,
            confirm_public_discovery=confirm_public_discovery,
            resume=resume and central_root.exists(),
            observation_bundle=observation_bundle,
        )
    except MissionStateError as exc:
        return _blocked(root, exc.code, str(exc), stage="central_papers")

    projection_root = root / "document_projection"
    try:
        if projection_root.exists() and any(projection_root.iterdir()):
            if not resume:
                return _blocked(root, "projection_output_exists", "document projection already exists", stage="projection")
            projection = _validate_projection(central_root, projection_root)
        else:
            projection = project_central_campaign(
                campaign_root=central_root,
                output_dir=projection_root,
            )
    except (DocumentInputError, MissionStateError) as exc:
        return _blocked(root, "reviewed_evidence_required", str(exc), stage="projection", central_report=central_report)

    document_root = root / "document"
    if document_root.exists() and any(document_root.iterdir()):
        return _blocked(
            root,
            "partial_document_run_requires_fresh_root",
            "a nonempty incomplete document run cannot be overwritten",
            stage="document",
            central_report=central_report,
        )
    document = draft_document(
        evidence_path=Path(projection["evidence_path"]),
        contract_path=Path(projection["contract_path"]),
        output_dir=document_root,
        dynaremcp_command=dynaremcp_command,
        compile_latex=compile_latex,
    )
    if document.get("accepted") is not True and document.get("status") != "insufficient_survey_evidence":
        return _blocked(
            root,
            document.get("blocked_reason", "document_stage_failed"),
            "; ".join(document.get("errors") or ["document synthesis did not complete"]),
            stage="document",
            central_report=central_report,
        )
    result = {
        "schema_version": RESULT_SCHEMA,
        "status": document["status"],
        "accepted": document.get("accepted") is True,
        "topic": topic,
        "output_dir": str(root),
        "authority_class": document["authority_class"],
        "central_papers_status": central_report["status"],
        "central_papers_open_risks": central_report.get("open_risks") or [],
        "projection_status": projection["status"],
        "document_status": document["status"],
        "render_status": document["render_status"],
        "dynaremcp_qa_status": document["dynaremcp_qa_status"],
        "survey_tex_path": str(document_root / "draft.tex"),
        "survey_pdf_path": str(document_root / "draft.pdf") if (document_root / "draft.pdf").is_file() else None,
        "next_required_actions": _next_actions(central_report, document),
        "what_is_not_concluded": NONCLAIMS,
    }
    write_json(final_path, result)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "topic": topic,
        "artifact_sha256": {
            "central_manifest": sha256_file(central_root / "campaign_manifest.json"),
            "document_evidence": sha256_file(Path(projection["evidence_path"])),
            "document_contract": sha256_file(Path(projection["contract_path"])),
            "document_source": sha256_file(document_root / "draft.tex"),
            "document_status": sha256_file(document_root / "final_status.json"),
            "result": sha256_file(final_path),
        },
        "what_is_not_concluded": NONCLAIMS,
    }
    write_json(manifest_path, manifest)
    return result


def _validate_projection(campaign_root: Path, projection_root: Path) -> dict[str, Any]:
    validate_central_papers_campaign(campaign_root)
    evidence_path = projection_root / "document_evidence.json"
    contract_path = projection_root / "document_contract.json"
    contract = load_contract(contract_path)
    bundle = load_evidence(evidence_path, contract)
    if bundle.authority_class != "source_attributed":
        raise DocumentInputError("topic workflow projection must remain source_attributed")
    provenance = json.loads(evidence_path.read_text(encoding="utf-8")).get("provenance") or {}
    if provenance.get("campaign_root") != str(campaign_root.resolve()):
        raise DocumentInputError("document projection belongs to a different central campaign")
    return {
        "status": "central_campaign_projection_reused",
        "authority_class": bundle.authority_class,
        "evidence_path": str(evidence_path),
        "contract_path": str(contract_path),
        "claim_count": len(bundle.claims),
        "paper_count": len(bundle.papers),
        "what_is_not_concluded": list(bundle.nonclaims),
    }


def _validate_completed_run(root: Path, topic: str) -> dict[str, Any]:
    try:
        result = json.loads((root / "literature_review_result.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "literature_review_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _blocked(root, "invalid_completed_literature_review", str(exc))
    if result.get("schema_version") != RESULT_SCHEMA or result.get("topic") != topic:
        return _blocked(root, "literature_review_resume_mismatch", "completed run belongs to a different topic or schema")
    if manifest.get("schema_version") != MANIFEST_SCHEMA or manifest.get("topic") != topic:
        return _blocked(root, "invalid_completed_literature_review", "manifest topic or schema differs")
    paths = {
        "central_manifest": root / "central_papers" / "campaign_manifest.json",
        "document_evidence": root / "document_projection" / "document_evidence.json",
        "document_contract": root / "document_projection" / "document_contract.json",
        "document_source": root / "document" / "draft.tex",
        "document_status": root / "document" / "final_status.json",
        "result": root / "literature_review_result.json",
    }
    expected = manifest.get("artifact_sha256")
    if not isinstance(expected, dict) or any(not path.is_file() or sha256_file(path) != expected.get(role) for role, path in paths.items()):
        return _blocked(root, "literature_review_artifact_mismatch", "completed run artifact hashes differ")
    return {**result, "resume_status": "completed_run_replayed"}


def _next_actions(central: dict[str, Any], document: dict[str, Any]) -> list[str]:
    actions = list(central.get("next_required_actions") or [])
    actions.extend(document.get("next_required_actions") or [])
    if document.get("render_status") != "rendered":
        actions.append("install or repair the local LaTeX toolchain and rerun in a fresh output root")
    if document.get("dynaremcp_qa_status") != "external_document_qa_passed":
        actions.append("configure DynareMCP document QA or inspect its recorded findings")
    actions.append("complete reviewed claim, source-safety, and omission decisions before stronger prose promotion")
    return list(dict.fromkeys(actions))


def _blocked(
    root: Path,
    code: str,
    message: str,
    *,
    stage: str = "orchestration",
    central_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA,
        "status": "blocked",
        "accepted": False,
        "blocked_stage": stage,
        "blocked_reason": code,
        "message": message,
        "output_dir": str(root),
        "central_papers_status": None if central_report is None else central_report.get("status"),
        "what_is_not_concluded": NONCLAIMS,
    }
