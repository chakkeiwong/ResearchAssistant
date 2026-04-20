from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.pdf_extract import extract_pdf_text
from research_assistant.schemas.parsed_document import ParsedDocument


class PdftotextParser(DocumentParser):
    name = 'pdftotext'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        text = extract_pdf_text(pdf_path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title_candidates = lines[:5]
        return ParsedDocument(
            parser_name=self.name,
            title_candidates=title_candidates,
            body_text=text,
            diagnostics={'line_count': len(lines)},
            parse_status='ok' if text.strip() else 'failed',
        )
