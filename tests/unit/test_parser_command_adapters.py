from __future__ import annotations

from pathlib import Path

import pytest

from research_assistant.ingest.parser_command import ParserCommandResult
from research_assistant.ingest.parser_markitdown import MarkItDownParser
from research_assistant.ingest.parser_marker import MarkerParser
from research_assistant.ingest.parser_preflight import ParserPreflight


@pytest.mark.parametrize(
    ("module_name", "parser"),
    [
        ("parser_marker", MarkerParser()),
        ("parser_markitdown", MarkItDownParser()),
    ],
)
def test_command_parser_timeout_returns_failed_document(
    monkeypatch,
    tmp_path: Path,
    module_name: str,
    parser,
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf")
    module = f"research_assistant.ingest.{module_name}"
    monkeypatch.setattr(
        f"{module}.check_command",
        lambda name, command: ParserPreflight(name, True, "available", ["ok"], {"command": command}),
    )
    monkeypatch.setattr(
        f"{module}.run_parser_command",
        lambda cmd, *, policy: ParserCommandResult(
            command=cmd,
            returncode=None,
            stdout="",
            stderr="",
            timeout_seconds=policy.timeout_seconds,
            duration_seconds=policy.timeout_seconds,
            timed_out=True,
            error=f"command timed out after {policy.timeout_seconds} seconds",
        ),
    )

    result = parser.parse(pdf_path)

    assert result.parse_status == "failed"
    assert result.diagnostics["timed_out"] is True
    assert "timed out" in result.diagnostics["error"]
