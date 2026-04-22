from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_preflight import check_command, check_file
from research_assistant.schemas.parsed_document import ParsedDocument


def _select_markdown_output(outdir: Path) -> Path | None:
    markdown_files = sorted(outdir.rglob('*.md'))
    if not markdown_files:
        return None
    scored = []
    for path in markdown_files:
        try:
            text = path.read_text(errors='ignore')
        except OSError:
            text = ''
        scored.append((len(text.strip()), str(path), path))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2]


class MinerUParser(DocumentParser):
    name = 'mineru'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        cli = check_command(self.name, 'magic-pdf')
        config = check_file('mineru_config', Path.home() / 'magic-pdf.json')
        if not cli.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [cli.to_dict(), config.to_dict()]}, parse_status='unavailable')
        if not config.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [cli.to_dict(), config.to_dict()]}, parse_status='misconfigured')
        if not pdf_path.exists():
            return ParsedDocument(
                parser_name=self.name,
                diagnostics={'preflight': [cli.to_dict(), config.to_dict()], 'error': f'{pdf_path} not found'},
                parse_status='failed',
            )

        with tempfile.TemporaryDirectory(prefix='mineru_parse_') as tmpdir:
            outdir = Path(tmpdir)
            cmd = ['magic-pdf', '--path', str(pdf_path), '--output-dir', str(outdir), '--method', 'auto']
            result = subprocess.run(cmd, capture_output=True, text=True)
            markdown_path = _select_markdown_output(outdir)
            text = markdown_path.read_text(errors='ignore') if markdown_path else ''
            diagnostics = {
                'command': cmd,
                'returncode': result.returncode,
                'stdout': result.stdout[-4000:],
                'stderr': result.stderr[-4000:],
                'selected_markdown': str(markdown_path) if markdown_path else None,
                'markdown_file_count': len(sorted(outdir.rglob('*.md'))),
                'preflight': [cli.to_dict(), config.to_dict()],
            }
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            status = 'ok'
            if result.returncode != 0:
                status = 'failed'
                diagnostics['error'] = 'magic-pdf exited with a non-zero status'
            elif not text.strip():
                status = 'failed'
                diagnostics['error'] = 'magic-pdf produced no usable markdown output'
            return ParsedDocument(
                parser_name=self.name,
                title_candidates=lines[:8],
                body_markdown=text,
                body_text=text,
                diagnostics=diagnostics,
                parse_status=status,
            )
