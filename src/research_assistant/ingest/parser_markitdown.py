from __future__ import annotations

import tempfile
from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_frontmatter import extract_frontmatter
from research_assistant.ingest.parser_command import ParserExecutionPolicy, run_parser_command
from research_assistant.ingest.parser_preflight import check_command
from research_assistant.schemas.parsed_document import ParsedDocument


class MarkItDownParser(DocumentParser):
    name = 'markitdown'

    def __init__(self, policy: ParserExecutionPolicy | None = None) -> None:
        self.policy = policy or ParserExecutionPolicy.from_environment()

    def parse(self, pdf_path: Path) -> ParsedDocument:
        preflight = check_command(self.name, 'markitdown')
        if not preflight.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [preflight.to_dict()]}, parse_status='unavailable')
        if not pdf_path.is_file():
            return ParsedDocument(
                parser_name=self.name,
                diagnostics={'preflight': [preflight.to_dict()], 'error': f'{pdf_path} not found'},
                parse_status='failed',
            )
        with tempfile.TemporaryDirectory(prefix='markitdown_parse_') as tmpdir:
            out = Path(tmpdir) / 'output.md'
            cmd = ['markitdown', str(pdf_path), '-o', str(out)]
            result = run_parser_command(cmd, policy=self.policy)
            text = out.read_text(errors='ignore') if out.exists() else ''
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            extracted = extract_frontmatter(lines)
            status = 'ok' if result.succeeded and text.strip() else 'failed'
            diagnostics = result.diagnostics()
            diagnostics['preflight'] = [preflight.to_dict()]
            if not result.succeeded:
                diagnostics['error'] = result.error or f'markitdown exited with status {result.returncode}'
            return ParsedDocument(
                parser_name=self.name,
                title_candidates=extracted.title_candidates,
                authors=extracted.authors,
                body_markdown=text,
                body_text=text,
                section_headings=extracted.section_headings,
                diagnostics=diagnostics,
                parse_status=status,
            )
