from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_preflight import check_command, check_http
from research_assistant.schemas.parsed_document import ParsedDocument


class GROBIDParser(DocumentParser):
    name = 'grobid'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        # CLI check is not relevant; health endpoint is.
        health = check_http(self.name, 'http://localhost:8070/api/isalive')
        if not health.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [health.to_dict()]}, parse_status='unavailable')
        return ParsedDocument(
            parser_name=self.name,
            diagnostics={'preflight': [health.to_dict()], 'note': 'GROBID parser implementation pending endpoint-specific parsing'},
            parse_status='failed',
        )
