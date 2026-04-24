from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import shutil
import urllib.request


PARSER_CAPABILITIES = {
    'pdftotext': {
        'section_headings': 'partial',
        'equations': 'unreliable',
        'citations': 'unreliable',
    },
    'markitdown': {
        'section_headings': 'partial',
        'equations': 'unreliable',
        'citations': 'unreliable',
    },
    'marker': {
        'section_headings': 'partial',
        'equations': 'unreliable',
        'citations': 'unreliable',
    },
    'mineru': {
        'section_headings': 'partial',
        'equations': 'unreliable',
        'citations': 'unreliable',
    },
    'grobid': {
        'section_headings': 'partial',
        'equations': 'unreliable',
        'citations': 'unreliable',
    },
}


@dataclass
class ParserPreflight:
    parser_name: str
    available: bool
    status: str
    messages: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)



def parser_capabilities(name: str) -> dict[str, str]:
    return PARSER_CAPABILITIES.get(name, {
        'section_headings': 'unknown',
        'equations': 'unknown',
        'citations': 'unknown',
    })



def _with_capabilities(name: str, details: dict) -> dict:
    return {
        **details,
        'capabilities': parser_capabilities(name),
    }



def check_command(name: str, command: str) -> ParserPreflight:
    path = shutil.which(command)
    if path:
        return ParserPreflight(name, True, 'available', [f'{command} found'], _with_capabilities(name, {'path': path, 'command': command}))
    return ParserPreflight(name, False, 'unavailable', [f'{command} not found in PATH'], _with_capabilities(name, {'command': command}))



def check_file(name: str, path: Path) -> ParserPreflight:
    if path.exists():
        return ParserPreflight(name, True, 'available', [f'{path} exists'], {'path': str(path)})
    return ParserPreflight(name, False, 'misconfigured', [f'{path} not found'], {'path': str(path)})



def check_http(name: str, url: str, timeout: int = 5) -> ParserPreflight:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode('utf-8', errors='ignore')
        return ParserPreflight(name, True, 'available', [f'{url} responded'], _with_capabilities(name, {'url': url, 'body': body.strip()}))
    except Exception as exc:
        return ParserPreflight(name, False, 'unavailable', [str(exc)], _with_capabilities(name, {'url': url}))



def preflight_all() -> list[ParserPreflight]:
    pdftotext = check_command('pdftotext', 'pdftotext')
    markitdown = check_command('markitdown', 'markitdown')
    marker = check_command('marker', 'marker_single')
    mineru_cli = check_command('mineru_cli', 'magic-pdf')
    mineru_config = check_file('mineru_config', Path.home() / 'magic-pdf.json')
    grobid = check_http('grobid', 'http://localhost:8070/api/isalive')

    if marker.available:
        marker.messages.append('Run marker_single <pdf> --output_dir <dir> for direct validation.')
    else:
        marker.messages.append('Install Marker so marker_single is available on PATH.')

    if markitdown.available:
        markitdown.messages.append('Run markitdown <pdf> -o <output.md> for direct validation.')
    else:
        markitdown.messages.append('Install MarkItDown so markitdown is available on PATH.')

    if pdftotext.available:
        pdftotext.messages.append('Run pdftotext <pdf> - to inspect raw text extraction quickly.')
    else:
        pdftotext.messages.append('Install poppler-utils so pdftotext is available on PATH.')

    if mineru_cli.available and mineru_config.available:
        mineru = ParserPreflight(
            'mineru',
            True,
            'available',
            ['magic-pdf found', f"{mineru_config.details['path']} exists", 'Run magic-pdf --path <pdf> --output-dir <dir> --method auto for validation.'],
            _with_capabilities('mineru', {'cli': mineru_cli.to_dict(), 'config': mineru_config.to_dict()}),
        )
    elif mineru_cli.available:
        mineru = ParserPreflight(
            'mineru',
            False,
            'misconfigured',
            ['magic-pdf found', f"{mineru_config.details['path']} not found", 'Create the MinerU config file before running parser validation.'],
            _with_capabilities('mineru', {'cli': mineru_cli.to_dict(), 'config': mineru_config.to_dict()}),
        )
    else:
        mineru = ParserPreflight(
            'mineru',
            False,
            'unavailable',
            ['magic-pdf not found in PATH', 'Install MinerU before running parser validation.'],
            _with_capabilities('mineru', {'cli': mineru_cli.to_dict(), 'config': mineru_config.to_dict()}),
        )

    if grobid.available:
        grobid.messages.append('GROBID health endpoint is live; endpoint-specific parsing can be exercised next.')
    else:
        grobid.messages.append('Start the local GROBID service and verify /api/isalive before parser validation.')

    return [pdftotext, markitdown, marker, mineru, grobid]
