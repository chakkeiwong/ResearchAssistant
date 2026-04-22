from __future__ import annotations

from pathlib import Path
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from research_assistant.ingest.parser_base import DocumentParser
from research_assistant.ingest.parser_preflight import check_http
from research_assistant.schemas.parsed_document import ParsedDocument

GROBID_BASE_URL = 'http://localhost:8070'
GROBID_HEALTH_URL = f'{GROBID_BASE_URL}/api/isalive'
GROBID_FULLTEXT_URL = f'{GROBID_BASE_URL}/api/processFulltextDocument'
TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def _clean_text(value: str) -> str:
    return ' '.join(value.split()).strip()


def _extract_joined_text(element: ET.Element | None) -> str:
    if element is None:
        return ''
    text = ''.join(element.itertext())
    return _clean_text(text)


def _extract_title_candidates(root: ET.Element) -> list[str]:
    titles = []
    for xpath in (
        ".//tei:titleStmt/tei:title",
        ".//tei:sourceDesc//tei:title",
        ".//tei:teiHeader//tei:title",
    ):
        for node in root.findall(xpath, TEI_NS):
            title = _extract_joined_text(node)
            if title and title not in titles:
                titles.append(title)
    return titles


def _extract_authors(root: ET.Element) -> list[str]:
    authors = []
    for author in root.findall('.//tei:teiHeader//tei:fileDesc//tei:sourceDesc//tei:biblStruct//tei:analytic//tei:author', TEI_NS):
        pers = author.find('tei:persName', TEI_NS)
        if pers is None:
            name = _extract_joined_text(author)
        else:
            parts = []
            forename_nodes = pers.findall('tei:forename', TEI_NS)
            surname_node = pers.find('tei:surname', TEI_NS)
            parts.extend(_extract_joined_text(node) for node in forename_nodes if _extract_joined_text(node))
            surname = _extract_joined_text(surname_node)
            if surname:
                parts.append(surname)
            name = ' '.join(parts).strip() if parts else _extract_joined_text(pers)
        if name and name not in authors:
            authors.append(name)
    return authors


def _extract_abstract(root: ET.Element) -> str:
    return _extract_joined_text(root.find('.//tei:profileDesc/tei:abstract', TEI_NS))


def _extract_body_text(root: ET.Element) -> str:
    paragraphs = []
    for paragraph in root.findall('.//tei:text/tei:body//tei:p', TEI_NS):
        text = _extract_joined_text(paragraph)
        if text:
            paragraphs.append(text)
    return '\n\n'.join(paragraphs)


def _extract_section_headings(root: ET.Element) -> list[str]:
    headings = []
    for head in root.findall('.//tei:text/tei:body//tei:div/tei:head', TEI_NS):
        text = _extract_joined_text(head)
        if text and text not in headings:
            headings.append(text)
    return headings


class GROBIDParser(DocumentParser):
    name = 'grobid'

    def parse(self, pdf_path: Path) -> ParsedDocument:
        health = check_http(self.name, GROBID_HEALTH_URL)
        if not health.available:
            return ParsedDocument(parser_name=self.name, diagnostics={'preflight': [health.to_dict()]}, parse_status='unavailable')

        if not pdf_path.exists():
            return ParsedDocument(
                parser_name=self.name,
                diagnostics={'preflight': [health.to_dict()], 'error': f'{pdf_path} not found'},
                parse_status='failed',
            )

        try:
            with pdf_path.open('rb') as handle:
                pdf_bytes = handle.read()
            boundary = 'claude-grobid-boundary'
            payload = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="input"; filename="{pdf_path.name}"\r\n'
                'Content-Type: application/pdf\r\n\r\n'
            ).encode('utf-8') + pdf_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')
            request = urllib.request.Request(
                GROBID_FULLTEXT_URL,
                data=payload,
                headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
                method='POST',
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                tei_xml = response.read().decode('utf-8', errors='ignore')
                status_code = response.getcode()
        except urllib.error.URLError as exc:
            return ParsedDocument(
                parser_name=self.name,
                diagnostics={'preflight': [health.to_dict()], 'endpoint': GROBID_FULLTEXT_URL, 'error': str(exc)},
                parse_status='failed',
            )

        try:
            root = ET.fromstring(tei_xml)
        except ET.ParseError as exc:
            return ParsedDocument(
                parser_name=self.name,
                diagnostics={
                    'preflight': [health.to_dict()],
                    'endpoint': GROBID_FULLTEXT_URL,
                    'http_status': status_code,
                    'error': f'Invalid TEI XML: {exc}',
                    'response_preview': tei_xml[:500],
                },
                parse_status='failed',
            )

        title_candidates = _extract_title_candidates(root)
        authors = _extract_authors(root)
        abstract = _extract_abstract(root)
        body_text = _extract_body_text(root)
        section_headings = _extract_section_headings(root)
        parse_status = 'ok' if (title_candidates or authors or abstract or body_text) else 'failed'

        return ParsedDocument(
            parser_name=self.name,
            title_candidates=title_candidates,
            authors=authors,
            abstract=abstract,
            body_text=body_text,
            section_headings=section_headings,
            diagnostics={
                'preflight': [health.to_dict()],
                'endpoint': GROBID_FULLTEXT_URL,
                'http_status': status_code,
            },
            parse_status=parse_status,
        )
