from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from .contracts import PLAN_SCHEMA, DocumentInputError, EvidenceBundle


@dataclass(frozen=True, slots=True)
class SectionPlan:
    section_id: str
    title: str
    mechanism: str
    claim_ids: tuple[str, ...]
    anchor_ids: tuple[str, ...]
    reader_entry: str
    reader_exit: str
    necessity: str


@dataclass(frozen=True, slots=True)
class DocumentPlan:
    schema_version: str
    topic: str
    bundle_id: str
    authority_class: str
    sections: tuple[SectionPlan, ...]
    forbidden_claim_ids: tuple[str, ...]
    unused_paper_ids: tuple[str, ...]
    unused_paper_dispositions: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "topic": self.topic,
            "bundle_id": self.bundle_id,
            "authority_class": self.authority_class,
            "sections": [asdict(section) for section in self.sections],
            "forbidden_claim_ids": list(self.forbidden_claim_ids),
            "unused_paper_ids": list(self.unused_paper_ids),
            "unused_paper_dispositions": list(self.unused_paper_dispositions),
        }


def build_document_plan(bundle: EvidenceBundle) -> DocumentPlan:
    allowed = [claim for claim in bundle.claims if claim.allowed]
    blocked = [claim.claim_id for claim in bundle.claims if not claim.allowed]
    if not allowed:
        raise DocumentInputError("evidence bundle has no allowed claims for document planning")
    grouped: dict[str, list] = {}
    for claim in allowed:
        grouped.setdefault(claim.mechanism, []).append(claim)
    sections: list[SectionPlan] = []
    used_papers: set[str] = set()
    for mechanism, claims in sorted(grouped.items()):
        section_id = _section_id(mechanism)
        mechanisms = sorted({claim.mechanism for claim in claims})
        claim_ids = tuple(claim.claim_id for claim in claims)
        anchor_ids = tuple(sorted({anchor for claim in claims for anchor in claim.anchor_ids}))
        used_papers.update(paper_id for claim in claims for paper_id in claim.paper_ids)
        title = " and ".join(mechanisms)
        sections.append(
            SectionPlan(
                section_id=section_id,
                title=title,
                mechanism="; ".join(mechanisms),
                claim_ids=claim_ids,
                anchor_ids=anchor_ids,
                reader_entry="The reader has the motivating puzzle but not the mechanism comparison.",
                reader_exit=f"The reader can compare the evidence for {title} within the recorded scope.",
                necessity=f"This section is required to explain the {title} mechanism before the next section.",
            )
        )
    unused = tuple(sorted({paper.paper_id for paper in bundle.papers} - used_papers))
    omission_by_paper = {
        str(row.get("paper_id")): str(row.get("reason", "")).strip()
        for row in bundle.omissions
        if row.get("paper_id") and row.get("reason")
    }
    missing_dispositions = [paper_id for paper_id in unused if paper_id not in omission_by_paper]
    if missing_dispositions:
        raise DocumentInputError(
            "unused papers require omission dispositions: " + ", ".join(missing_dispositions)
        )
    return DocumentPlan(
        schema_version=PLAN_SCHEMA,
        topic=bundle.topic,
        bundle_id=bundle.bundle_id,
        authority_class=bundle.authority_class,
        sections=tuple(sections),
        forbidden_claim_ids=tuple(sorted(blocked)),
        unused_paper_ids=unused,
        unused_paper_dispositions=tuple(
            {"paper_id": paper_id, "reason": omission_by_paper[paper_id]}
            for paper_id in unused
        ),
    )


def _section_id(mechanism: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", mechanism.casefold()).strip("-")
    if not slug:
        raise DocumentInputError("mechanism cannot produce a stable section id")
    return f"mechanism-{slug}"


def plan_hash(plan: DocumentPlan) -> str:
    raw = json.dumps(plan.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
