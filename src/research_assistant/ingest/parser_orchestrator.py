from __future__ import annotations

from pathlib import Path
from collections import Counter

from research_assistant.schemas.parsed_document import ParsedDocument, ReconciledDocument
from research_assistant.ingest.parser_pdftotext import PdftotextParser
from research_assistant.ingest.parser_marker import MarkerParser
from research_assistant.ingest.parser_grobid import GROBIDParser
from research_assistant.ingest.parser_mineru import MinerUParser
from research_assistant.ingest.parser_markitdown import MarkItDownParser


def available_parsers() -> list:
    return [
        PdftotextParser(),
        MarkerParser(),
        GROBIDParser(),
        MinerUParser(),
        MarkItDownParser(),
    ]


def parse_with_all(pdf_path: Path) -> list[ParsedDocument]:
    outputs = []
    for parser in available_parsers():
        try:
            outputs.append(parser.parse(pdf_path))
        except Exception as exc:
            outputs.append(ParsedDocument(parser_name=parser.name, diagnostics={'error': str(exc)}, parse_status='failed'))
    return outputs


def reconcile_parsed_documents(outputs: list[ParsedDocument]) -> ReconciledDocument:
    title_votes = []
    for out in outputs:
        if out.title_candidates:
            title_votes.append(out.title_candidates[0].strip())
    counter = Counter(title_votes)
    consensus_title = counter.most_common(1)[0][0] if counter else None
    ok_count = sum(1 for o in outputs if o.parse_status == 'ok')
    parse_confidence = 'low'
    if ok_count >= 2:
        parse_confidence = 'medium'
    if ok_count >= 3 and consensus_title:
        parse_confidence = 'high'
    disagreements = []
    if len(set(title_votes)) > 1:
        disagreements.append('parser title candidates disagree')
    return ReconciledDocument(
        consensus_title=consensus_title,
        parser_agreement={'ok_parsers': ok_count, 'title_votes': dict(counter)},
        disagreements=disagreements,
        parse_confidence=parse_confidence,
        requires_manual_review=parse_confidence != 'high',
        parser_outputs=[o.to_dict() for o in outputs],
    )
