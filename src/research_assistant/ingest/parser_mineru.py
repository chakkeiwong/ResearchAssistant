from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_preflight import check_command, check_file
from research_assistant.schemas.parsed_document import ParsedDocument


class MinerUParser(DocumentParser):
    name = 'mineru'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        cli = check_command(self.name, 'magic-pdf')
        config = check_file('mineru_config', Path.home() / 'magic-pdf.json')
        if not cli.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [cli.to_dict(), config.to_dict()]}, parse_status='unavailable')
        if not config.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [cli.to_dict(), config.to_dict()]}, parse_status='misconfigured')

        with tempfile.TemporaryDirectory(prefix='mineru_parse_') as tmpdir:
            outdir = Path(tmpdir)
            cmd = ['magic-pdf', '--path', str(pdf_path), '--output-dir', str(outdir), '--method', 'auto']
            result = subprocess.run(cmd, capture_output=True, text=True)
            diagnostics = {
                'returncode': result.returncode,
                'stdout': result.stdout[-4000:],
                'stderr': result.stderr[-4000:],
                'output_dir': str(outdir),
                'preflight': [cli.to_dict(), config.to_dict()],
            }
            markdown_files = list(outdir.rglob('*.md'))
            text = markdown_files[0].read_text(errors='ignore') if markdown_files else ''
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            status = 'ok' if result.returncode == 0 and text.strip() else 'failed'
            return ParsedDocument(
                parser_name=self.name,
                title_candidates=lines[:8],
                body_markdown=text,
                body_text=text,
                diagnostics=diagnostics,
                parse_status=status,
            )
