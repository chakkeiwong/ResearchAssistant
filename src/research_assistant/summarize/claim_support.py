from __future__ import annotations

from research_assistant.schemas.audit_record import AuditRecord


def audit_claim(claim: str, cited_papers: list[str]) -> AuditRecord:
    classification = 'insufficient_evidence'
    if cited_papers:
        classification = 'background_only'
    return AuditRecord(
        id='audit_' + str(abs(hash((claim, tuple(cited_papers)))))[:10],
        claim=claim,
        cited_papers=cited_papers,
        support_classification=classification,
        evidence_summary='Initial placeholder audit. Manual review required.',
        reviewer_note='This first version does not yet read paper bodies semantically for evidence extraction.',
    )
