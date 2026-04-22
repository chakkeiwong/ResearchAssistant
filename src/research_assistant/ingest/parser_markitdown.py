from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_frontmatter import extract_frontmatter
from research_assistant.ingest.parser_preflight import check_command
from research_assistant.schemas.parsed_document import ParsedDocument


class MarkItDownParser(DocumentParser):
    name = 'markitdown'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        preflight = check_command(self.name, 'markitdown')
        if not preflight.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [preflight.to_dict()]}, parse_status='unavailable')
        with tempfile.TemporaryDirectory(prefix='markitdown_parse_') as tmpdir:
            out = Path(tmpdir) / 'output.md'
            cmd = ['markitdown', str(pdf_path), '-o', str(out)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            text = out.read_text(errors='ignore') if out.exists() else ''
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            extracted = extract_frontmatter(lines)
            status = 'ok' if result.returncode == 0 and text.strip() else 'failed'
            return ParsedDocument(
                parser_name=self.name,
                title_candidates=extracted.title_candidates,
                authors=extracted.authors,
                body_markdown=text,
                body_text=text,
                section_headings=extracted.section_headings,
                diagnostics={
                    'returncode': result.returncode,
                    'stdout': result.stdout[-4000:],
                    'stderr': result.stderr[-4000:],
                    'preflight': [preflight.to_dict()],
                },
                parse_status=status,
            )
