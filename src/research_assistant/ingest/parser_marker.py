from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_preflight import check_command
from research_assistant.schemas.parsed_document import ParsedDocument


class MarkerParser(DocumentParser):
    name = 'marker'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        preflight = check_command(self.name, 'marker_single')
        if not preflight.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [preflight.to_dict()]}, parse_status='unavailable')
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            markdown_files = list(outdir.rglob('*.md'))
            text = markdown_files[0].read_text(errors='ignore') if markdown_files else ''
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            status = 'ok' if result.returncode == 0 and text.strip() else 'failed'
            return ParsedDocument(
                parser_name=self.name,
                title_candidates=lines[:8],
                body_markdown=text,
                body_text=text,
                diagnostics={
                    'returncode': result.returncode,
                    'stdout': result.stdout[-4000:],
                    'stderr': result.stderr[-4000:],
                    'preflight': [preflight.to_dict()],
                },
                parse_status=status,
            )
