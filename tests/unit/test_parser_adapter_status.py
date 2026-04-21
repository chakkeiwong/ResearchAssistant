from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_pdftotext import PdftotextParser
from research_assistant.ingest.parser_mineru import MinerUParser
from research_assistant.ingest.parser_grobid import GROBIDParser
from research_assistant.ingest.parser_marker import MarkerParser
from research_assistant.ingest.parser_markitdown import MarkItDownParser
from research_assistant.ingest.parser_preflight import preflight_all
from research_assistant.schemas.parsed_document import ParsedDocument


def test_parser_adapters_return_parsed_document_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / 'missing.pdf'
    for parser in [PdftotextParser(), MinerUParser(), GROBIDParser(), MarkerParser(), MarkItDownParser()]:
        try:
            result = parser.parse(missing)
        except Exception:
            assert parser.name == 'pdftotext'
            continue
        assert isinstance(result, ParsedDocument)
        assert result.parse_status in {'ok', 'partial', 'failed', 'unavailable', 'misconfigured'}


def test_preflight_outputs_match_parser_names() -> None:
    checks = {check.parser_name for check in preflight_all()}
    assert {'pdftotext', 'markitdown', 'marker', 'mineru', 'grobid'} <= checks
