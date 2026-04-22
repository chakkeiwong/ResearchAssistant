from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_frontmatter import extract_frontmatter
from research_assistant.ingest.pdf_extract import extract_pdf_text
from research_assistant.ingest.parser_preflight import check_command
from research_assistant.schemas.parsed_document import ParsedDocument


class PdftotextParser(DocumentParser):
    name = 'pdftotext'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        preflight = check_command(self.name, 'pdftotext')
        if not preflight.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': preflight.to_dict()}, parse_status='unavailable')
        text = extract_pdf_text(pdf_path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        extracted = extract_frontmatter(lines)
        return ParsedDocument(
            parser_name=self.name,
            title_candidates=extracted.title_candidates,
            authors=extracted.authors,
            body_text=text,
            section_headings=extracted.section_headings,
            diagnostics={'line_count': len(lines), 'preflight': preflight.to_dict()},
            parse_status='ok' if text.strip() else 'failed',
        )
