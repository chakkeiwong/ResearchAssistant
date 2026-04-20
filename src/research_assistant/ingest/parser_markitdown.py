from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.schemas.parsed_document import ParsedDocument


class MarkItDownParser(DocumentParser):
    name = 'markitdown'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        return ParsedDocument(
            parser_name=self.name,
            diagnostics={'note': 'MarkItDown integration not yet implemented'},
            parse_status='failed',
        )
