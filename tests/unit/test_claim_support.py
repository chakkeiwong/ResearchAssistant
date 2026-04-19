from __future__ import annotations

from research_assistant.summarize.claim_support import audit_claim


def test_audit_claim_placeholder() -> None:
    audit = audit_claim('test claim', ['p1'])
    assert audit.support_classification == 'background_only'
