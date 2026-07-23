from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .contracts import EvidenceBundle
from .planner import DocumentPlan


class ScholarlyWriter(Protocol):
    name: str

    def write(self, bundle: EvidenceBundle, plan: DocumentPlan) -> "WriterOutput": ...


@dataclass(frozen=True, slots=True)
class WriterOutput:
    source_text: str
    claim_ids: tuple[str, ...]
    mode: str
    status: str


def _tex(value: str) -> str:
    replacements = {
        "−": "-", "–": "-", "—": "-", "×": " x ", "÷": " / ",
        "′": "'", "″": '"', "“": '"', "”": '"', "‘": "'", "’": "'",
        "…": "...", "≤": " <= ", "≥": " >= ", "≠": " != ", "≈": " approx ",
        "∑": " sum ", "∏": " product ", "∫": " integral ", "√": " sqrt ",
        "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "λ": "lambda",
    }
    normalized = "".join(replacements.get(character, character) for character in value)
    normalized = unicodedata.normalize("NFKD", normalized).encode(
        "ascii", errors="replace"
    ).decode("ascii")
    escaped = re.sub(r"([\\{}%&#_$])", r"\\\1", normalized)
    return escaped.replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}")


class DeterministicScaffoldWriter:
    name = "deterministic-scaffold"

    def write(self, bundle: EvidenceBundle, plan: DocumentPlan) -> WriterOutput:
        lines = [
            "\\documentclass{article}",
            "\\usepackage{hyperref}",
            "\\usepackage[T1]{fontenc}",
            "\\begin{document}",
            f"\\title{{{_tex(bundle.topic)}}}",
            "\\maketitle",
            "\\begin{abstract}",
            _tex(
                f"This survey candidate organizes the checked evidence for {bundle.topic}. "
                f"{bundle.contract.claim_boundary}"
            ),
            "\\end{abstract}",
            "\\section{Scope and evidence boundary}",
            _tex(bundle.contract.motivation),
            "\\par",
            _tex(bundle.contract.answer_target),
            "\\par",
            _tex(
                "Evidence coverage: "
                f"{len(bundle.papers)} inspected papers and {len(bundle.claims)} checked source statements "
                f"grouped into {len(plan.sections)} mechanisms."
            ),
        ]
        claim_ids: list[str] = []
        by_id = {claim.claim_id: claim for claim in bundle.claims}
        anchors = {anchor.anchor_id: anchor for anchor in bundle.anchors}
        papers = {paper.paper_id: paper for paper in bundle.papers}
        for section in plan.sections:
            lines.append(f"\\section{{{_tex(section.title)}}}")
            lines.append(_tex(section.necessity))
            for claim_id in section.claim_ids:
                claim = by_id[claim_id]
                references = "; ".join(
                    f"{papers[anchors[anchor_id].paper_id].title}, {anchors[anchor_id].location}"
                    for anchor_id in claim.anchor_ids
                )
                if bundle.authority_class == "source_attributed":
                    statement = (
                        f"In the checked source section, {papers[claim.paper_ids[0]].title} reports: "
                        f"{claim.text}"
                    )
                else:
                    statement = claim.text
                lines.append(f"\\paragraph{{Evidence.}} {_tex(statement)} \\footnote{{{_tex(references)}}}")
                claim_ids.append(claim_id)
            lines.append(_tex(section.reader_exit))
        mechanisms = [section.title for section in plan.sections]
        if len(mechanisms) > 1:
            comparison = (
                "The inspected sources expose complementary mechanisms: "
                + "; ".join(mechanisms)
                + ". The current evidence supports comparison of their stated approaches, "
                "but not a common performance ranking."
            )
        else:
            comparison = (
                "Only one mechanism is represented by inspected source statements in this run. "
                "A broader comparison requires additional relevant sources and is recorded as an open evidence gap."
            )
        lines.extend([
            "\\section{Cross-mechanism synthesis}",
            _tex(comparison),
            "\\section{Limitations and open evidence risks}",
            "\\begin{itemize}",
            *[f"\\item {_tex(value)}" for value in bundle.nonclaims],
            *[
                f"\\item {_tex(str(row.get('reason') or 'Open omission risk'))}"
                + (
                    f" ({_tex(str(row.get('paper_id')))})"
                    if row.get("paper_id")
                    else ""
                )
                for row in bundle.omissions
            ],
            "\\end{itemize}",
            "\\end{document}",
        ])
        references = []
        used_anchor_ids = {anchor_id for claim in bundle.claims if claim.allowed for anchor_id in claim.anchor_ids}
        for paper in bundle.papers:
            used_anchors = [
                anchor
                for anchor in bundle.anchors
                if anchor.paper_id == paper.paper_id and anchor.anchor_id in used_anchor_ids
            ]
            if used_anchors:
                locations = "; ".join(anchor.location for anchor in used_anchors)
                references.append(f"\\item {_tex(paper.title)}. Checked locations: {_tex(locations)}.")
        lines[-1:-1] = ["\\section*{Checked source references}", "\\begin{itemize}", *references, "\\end{itemize}"]
        status = (
            "reviewed_survey_candidate_synthesized"
            if bundle.authority_class == "reviewed_primary"
            else "source_attributed_evidence_survey"
        )
        return WriterOutput("\n".join(lines) + "\n", tuple(claim_ids), self.name, status)


def write_source(path: Path, output: WriterOutput) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output.source_text, encoding="utf-8")
