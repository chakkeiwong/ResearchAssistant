from __future__ import annotations

from research_assistant.schemas.parsed_document import ParsedDocument
from research_assistant.ingest.parser_orchestrator import reconcile_parsed_documents


def test_reconcile_single_parser_output_low_confidence() -> None:
    out = ParsedDocument(parser_name='pdftotext', title_candidates=['A Test Paper'], parse_status='ok')
    rec = reconcile_parsed_documents([out])
    assert rec.consensus_title == 'A Test Paper'
    assert rec.parse_confidence == 'low'
    assert rec.requires_manual_review is True


def test_reconcile_multiple_agreeing_outputs_high_confidence() -> None:
    outputs = [
        ParsedDocument(parser_name='a', title_candidates=['A Test Paper'], parse_status='ok'),
        ParsedDocument(parser_name='b', title_candidates=['A Test Paper'], parse_status='ok'),
        ParsedDocument(parser_name='c', title_candidates=['A Test Paper'], parse_status='ok'),
    ]
    rec = reconcile_parsed_documents(outputs)
    assert rec.consensus_title == 'A Test Paper'
    assert rec.parse_confidence == 'high'
    assert rec.requires_manual_review is False
