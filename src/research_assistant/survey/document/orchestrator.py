from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
from typing import Any

from .contracts import STATUS_SCHEMA, DocumentInputError, load_contract, load_evidence, sha256_file, write_json
from .dynaremcp_adapter import run_dynaremcp_qa
from .planner import build_document_plan, plan_hash
from .writer import DeterministicScaffoldWriter, write_source


def draft_document(
    *,
    evidence_path: Path,
    contract_path: Path,
    output_dir: Path,
    dynaremcp_command: str | None = None,
    compile_latex: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        return {"status": "blocked", "blocked_reason": "output_exists", "output_dir": str(output_dir)}
    try:
        contract = load_contract(contract_path.expanduser().resolve())
        bundle = load_evidence(evidence_path.expanduser().resolve(), contract)
        plan = build_document_plan(bundle)
    except DocumentInputError as exc:
        return {"status": "blocked", "blocked_reason": "invalid_document_input", "errors": [str(exc)]}
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "document_contract.json", {
        "schema_version": "ra.scholarly_document_contract.v1",
        "reader": contract.reader,
        "purpose": contract.purpose,
        "motivation": contract.motivation,
        "answer_target": contract.answer_target,
        "claim_boundary": contract.claim_boundary,
        "nonclaims": list(contract.nonclaims),
    })
    write_json(output_dir / "argument_plan.json", plan.to_dict())
    writer_output = DeterministicScaffoldWriter().write(bundle, plan)
    source_path = output_dir / "draft.tex"
    write_source(source_path, writer_output)
    evidence_use = {
        "schema_version": "ra.scholarly_document_evidence_use.v1",
        "claim_ids": list(writer_output.claim_ids),
        "forbidden_claim_ids": list(plan.forbidden_claim_ids),
        "unused_paper_ids": list(plan.unused_paper_ids),
        "unused_paper_dispositions": list(plan.unused_paper_dispositions),
        "anchor_ids": sorted({anchor for claim in bundle.claims if claim.allowed for anchor in claim.anchor_ids}),
    }
    write_json(output_dir / "evidence_use_ledger.json", evidence_use)
    reader_state = {
        "schema_version": "ra.scholarly_document_reader_state.v1",
        "sections": [
            {"section_id": section.section_id, "reader_entry": section.reader_entry, "reader_exit": section.reader_exit}
            for section in plan.sections
        ],
    }
    write_json(output_dir / "reader_state_ledger.json", reader_state)
    qa = run_dynaremcp_qa(
        executable=dynaremcp_command,
        run_root=output_dir,
        source_path=source_path,
        facts=[
            {
                "subject": claim.claim_id,
                "predicate": "source_attributed_statement" if bundle.authority_class == "source_attributed" else "reviewed_claim_text",
                "value": claim.text,
                "anchor": claim.anchor_ids[0],
            }
            for claim in bundle.claims
            if claim.allowed
        ],
        promises=[
            {"promise_id": section.section_id, "payoff_ids": [section.section_id]}
            for section in plan.sections
        ],
        paid_ids=[section.section_id for section in plan.sections],
        terms=[
            {"term": section.mechanism, "definition": section.mechanism, "anchor": section.section_id}
            for section in plan.sections
        ],
    )
    write_json(output_dir / "dynaremcp_qa.json", qa)
    render = _compile_latex(source_path, output_dir) if compile_latex else {
        "status": "renderer_not_run",
        "accepted": False,
        "reason": "compile_not_requested",
    }
    write_json(output_dir / "render_result.json", render)
    manifest = {
        "schema_version": "ra.scholarly_document_run_manifest.v1",
        "evidence_path": str(evidence_path.resolve()),
        "evidence_sha256": sha256_file(evidence_path.resolve()),
        "contract_path": str(contract_path.resolve()),
        "contract_sha256": sha256_file(contract_path.resolve()),
        "plan_sha256": plan_hash(plan),
        "source_sha256": sha256_file(source_path),
        "writer": writer_output.mode,
    }
    write_json(output_dir / "run_manifest.json", manifest)
    status = {
        "schema_version": STATUS_SCHEMA,
        "status": writer_output.status,
        "accepted": True,
        "output_dir": str(output_dir),
        "writer_status": writer_output.status,
        "authority_class": bundle.authority_class,
        "render_status": render["status"],
        "dynaremcp_qa_status": qa["status"],
        "what_is_not_concluded": [
            "publication-ready prose",
            "literature completeness",
            "technical claim truth beyond imported support classes",
            "semantic PDF review or publication readiness",
        ],
    }
    if bundle.authority_class == "source_attributed" and len(bundle.papers) < 2:
        status["status"] = "insufficient_survey_evidence"
        status["accepted"] = False
        status["next_required_actions"] = [
            "inspect or acquire at least one additional topic-relevant primary source before treating this as a survey candidate",
        ]
    write_json(output_dir / "final_status.json", status)
    return status


def _compile_latex(source_path: Path, output_dir: Path) -> dict[str, Any]:
    executable = shutil.which("latexmk") or shutil.which("pdflatex")
    if executable is None:
        return {"status": "renderer_unavailable", "accepted": False, "reason": "latex_tool_not_found"}
    if os.path.islink(source_path):
        return {"status": "renderer_blocked", "accepted": False, "reason": "source_is_symlink"}
    if Path(executable).name == "latexmk":
        argv = [executable, "-pdf", "-interaction=nonstopmode", "-halt-on-error", source_path.name]
    else:
        argv = [executable, "-interaction=nonstopmode", "-halt-on-error", source_path.name]
    try:
        completed = subprocess.run(
            argv,
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "renderer_failed", "accepted": False, "reason": type(exc).__name__}
    pdf = output_dir / "draft.pdf"
    result = {
        "status": "rendered" if completed.returncode == 0 and pdf.is_file() else "renderer_failed",
        "accepted": completed.returncode == 0 and pdf.is_file(),
        "returncode": completed.returncode,
        "pdf_path": str(pdf) if pdf.is_file() else None,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }
    return result
