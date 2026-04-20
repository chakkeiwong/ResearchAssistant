from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.schemas.parsed_document import ParsedDocument


class MarkerParser(DocumentParser):
    name = 'marker'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        return ParsedDocument(
            parser_name=self.name,
            diagnostics={'note': 'Marker integration not yet implemented'},
            parse_status='failed',
        )
