from __future__ import annotations

import tempfile
from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_frontmatter import extract_frontmatter
from research_assistant.ingest.parser_command import ParserExecutionPolicy, run_parser_command
from research_assistant.ingest.parser_preflight import check_command
from research_assistant.schemas.parsed_document import ParsedDocument


class MarkerParser(DocumentParser):
    name = 'marker'

    def __init__(self, policy: ParserExecutionPolicy | None = None) -> None:
        self.policy = policy or ParserExecutionPolicy.from_environment()

    def parse(self, pdf_path: Path) -> ParsedDocument:
        preflight = check_command(self.name, 'marker_single')
        if not preflight.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [preflight.to_dict()]}, parse_status='unavailable')
        if not pdf_path.is_file():
            return ParsedDocument(
                parser_name=self.name,
                diagnostics={'preflight': [preflight.to_dict()], 'error': f'{pdf_path} not found'},
                parse_status='failed',
            )
        with tempfile.TemporaryDirectory(prefix='marker_parse_') as tmpdir:
            outdir = Path(tmpdir)
            cmd = [
                'marker_single',
                str(pdf_path),
                '--output_dir',
                str(outdir),
                '--output_format',
                'markdown',
                '--disable_multiprocessing',
            ]
            result = run_parser_command(cmd, policy=self.policy)
            markdown_files = list(outdir.rglob('*.md'))
            text = markdown_files[0].read_text(errors='ignore') if markdown_files else ''
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            extracted = extract_frontmatter(lines)
            status = 'ok' if result.succeeded and text.strip() else 'failed'
            diagnostics = result.diagnostics()
            diagnostics['preflight'] = [preflight.to_dict()]
            if not result.succeeded:
                diagnostics['error'] = result.error or f'marker_single exited with status {result.returncode}'
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
