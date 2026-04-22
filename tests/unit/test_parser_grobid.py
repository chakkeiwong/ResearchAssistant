from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_grobid import GROBIDParser
from research_assistant.ingest.parser_preflight import ParserPreflight


class _FakeResponse:
    def __init__(self, body: str, status_code: int = 200) -> None:
        self._body = body.encode('utf-8')
        self._status_code = status_code

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self._status_code

    def __enter__(self) -> '_FakeResponse':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_grobid_parser_extracts_tei_fields(monkeypatch: object, tmp_path: Path) -> None:
    pdf_path = tmp_path / 'paper.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 fake pdf')

    def fake_check_http(name: str, url: str, timeout: int = 5) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'url': url})

    tei = '''
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader>
        <fileDesc>
          <sourceDesc>
            <biblStruct>
              <analytic>
                <title>Example Parsed Title</title>
                <author><persName><forename>Alice</forename><surname>Example</surname></persName></author>
                <author><persName><forename>Bob</forename><surname>Example</surname></persName></author>
              </analytic>
            </biblStruct>
          </sourceDesc>
        </fileDesc>
        <profileDesc>
          <abstract><p>Example abstract text.</p></abstract>
        </profileDesc>
      </teiHeader>
      <text>
        <body>
          <div><head>Introduction</head><p>Body paragraph one.</p></div>
          <div><head>Conclusion</head><p>Body paragraph two.</p></div>
        </body>
      </text>
    </TEI>
    '''

    def fake_urlopen(request, timeout: int = 60):
        if isinstance(request, str):
            return _FakeResponse('alive')
        return _FakeResponse(tei)

    monkeypatch.setattr('research_assistant.ingest.parser_grobid.check_http', fake_check_http)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    result = GROBIDParser().parse(pdf_path)

    assert result.parse_status == 'ok'
    assert result.title_candidates == ['Example Parsed Title']
    assert result.authors == ['Alice Example', 'Bob Example']
    assert result.abstract == 'Example abstract text.'
    assert result.section_headings == ['Introduction', 'Conclusion']
    assert 'Body paragraph one.' in result.body_text


def test_grobid_parser_handles_invalid_tei(monkeypatch: object, tmp_path: Path) -> None:
    pdf_path = tmp_path / 'paper.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 fake pdf')

    def fake_check_http(name: str, url: str, timeout: int = 5) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'url': url})

    def fake_urlopen(request, timeout: int = 60):
        if isinstance(request, str):
            return _FakeResponse('alive')
        return _FakeResponse('<not valid xml')

    monkeypatch.setattr('research_assistant.ingest.parser_grobid.check_http', fake_check_http)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    result = GROBIDParser().parse(pdf_path)

    assert result.parse_status == 'failed'
    assert 'Invalid TEI XML' in result.diagnostics['error']
    assert result.diagnostics['response_preview']
