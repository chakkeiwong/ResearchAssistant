from __future__ import annotations

from research_assistant.ingest.parser_orchestrator import reconcile_parsed_documents
from research_assistant.schemas.parsed_document import ParsedDocument


def test_reconcile_extracts_joined_title_and_authors() -> None:
    marker = ParsedDocument(
        parser_name='marker',
        body_markdown='''![](_page_0_Picture_0.jpeg)\n\n**20-05 | December 3, 2020**\n\n# **Credit Risk and the Transmission of Interest Rate Shocks**\n\n### **Berardino Palazzo**\n\n### **Ram Yamarthy**\n''',
        parse_status='ok',
    )
    markitdown = ParsedDocument(
        parser_name='markitdown',
        body_markdown='''20-05 | December 3, 2020\nCredit Risk and the Transmission of Interest\nRate Shocks\nBerardino Palazzo\nRam Yamarthy\n''',
        parse_status='ok',
    )
    rec = reconcile_parsed_documents([marker, markitdown])
    assert 'Credit Risk and the Transmission of Interest Rate Shocks' in (rec.consensus_title or '')
    assert 'Berardino Palazzo' in rec.consensus_authors
    assert 'Ram Yamarthy' in rec.consensus_authors
