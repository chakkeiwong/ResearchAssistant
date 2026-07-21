from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_command import ParserCommandResult
from research_assistant.ingest.parser_mineru import MinerUParser, _select_markdown_output
from research_assistant.ingest.parser_preflight import ParserPreflight


def test_select_markdown_output_prefers_largest_content(tmp_path: Path) -> None:
    small = tmp_path / 'small.md'
    large = tmp_path / 'nested' / 'large.md'
    large.parent.mkdir()
    small.write_text('short')
    large.write_text('this is the larger markdown output')

    selected = _select_markdown_output(tmp_path)

    assert selected == large


def test_mineru_parser_returns_misconfigured_without_config(monkeypatch: object, tmp_path: Path) -> None:
    pdf_path = tmp_path / 'paper.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 fake pdf')

    def fake_check_command(name: str, command: str) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'command': command})

    def fake_check_file(name: str, path: Path) -> ParserPreflight:
        return ParserPreflight(name, False, 'misconfigured', ['missing config'], {'path': str(path)})

    monkeypatch.setattr('research_assistant.ingest.parser_mineru.check_command', fake_check_command)
    monkeypatch.setattr('research_assistant.ingest.parser_mineru.check_file', fake_check_file)

    result = MinerUParser().parse(pdf_path)

    assert result.parse_status == 'misconfigured'
    assert result.diagnostics['preflight'][1]['status'] == 'misconfigured'


def test_mineru_parser_handles_command_failure(monkeypatch: object, tmp_path: Path) -> None:
    pdf_path = tmp_path / 'paper.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 fake pdf')

    def fake_check_command(name: str, command: str) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'command': command})

    def fake_check_file(name: str, path: Path) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'path': str(path)})

    def fake_run(cmd, *, policy):
        return ParserCommandResult(
            command=cmd,
            returncode=1,
            stdout='',
            stderr='boom',
            timeout_seconds=policy.timeout_seconds,
            duration_seconds=0.1,
        )

    monkeypatch.setattr('research_assistant.ingest.parser_mineru.check_command', fake_check_command)
    monkeypatch.setattr('research_assistant.ingest.parser_mineru.check_file', fake_check_file)
    monkeypatch.setattr('research_assistant.ingest.parser_mineru.run_parser_command', fake_run)

    result = MinerUParser().parse(pdf_path)

    assert result.parse_status == 'failed'
    assert result.diagnostics['error'] == 'magic-pdf exited with a non-zero status'
    assert result.diagnostics['returncode'] == 1


def test_mineru_parser_handles_missing_markdown_output(monkeypatch: object, tmp_path: Path) -> None:
    pdf_path = tmp_path / 'paper.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 fake pdf')

    def fake_check_command(name: str, command: str) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'command': command})

    def fake_check_file(name: str, path: Path) -> ParserPreflight:
        return ParserPreflight(name, True, 'available', ['ok'], {'path': str(path)})

    def fake_run(cmd, *, policy):
        return ParserCommandResult(
            command=cmd,
            returncode=0,
            stdout='',
            stderr='',
            timeout_seconds=policy.timeout_seconds,
            duration_seconds=0.1,
        )

    monkeypatch.setattr('research_assistant.ingest.parser_mineru.check_command', fake_check_command)
    monkeypatch.setattr('research_assistant.ingest.parser_mineru.check_file', fake_check_file)
    monkeypatch.setattr('research_assistant.ingest.parser_mineru.run_parser_command', fake_run)

    result = MinerUParser().parse(pdf_path)

    assert result.parse_status == 'failed'
    assert result.diagnostics['error'] == 'magic-pdf produced no usable markdown output'
    assert result.diagnostics['selected_markdown'] is None


def test_mineru_parser_reports_timeout(monkeypatch: object, tmp_path: Path) -> None:
    pdf_path = tmp_path / 'paper.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 fake pdf')

    monkeypatch.setattr(
        'research_assistant.ingest.parser_mineru.check_command',
        lambda name, command: ParserPreflight(name, True, 'available', ['ok'], {'command': command}),
    )
    monkeypatch.setattr(
        'research_assistant.ingest.parser_mineru.check_file',
        lambda name, path: ParserPreflight(name, True, 'available', ['ok'], {'path': str(path)}),
    )
    monkeypatch.setattr(
        'research_assistant.ingest.parser_mineru.run_parser_command',
        lambda cmd, *, policy: ParserCommandResult(
            command=cmd,
            returncode=None,
            stdout='',
            stderr='',
            timeout_seconds=policy.timeout_seconds,
            duration_seconds=policy.timeout_seconds,
            timed_out=True,
            error=f'command timed out after {policy.timeout_seconds} seconds',
        ),
    )

    result = MinerUParser().parse(pdf_path)

    assert result.parse_status == 'failed'
    assert result.diagnostics['timed_out'] is True
    assert 'timed out' in result.diagnostics['error']
