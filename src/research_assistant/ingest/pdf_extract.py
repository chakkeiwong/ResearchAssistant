from __future__ import annotations

from pathlib import Path

from research_assistant.ingest.parser_command import (
    ParserExecutionPolicy,
    run_parser_command,
)


class PdfExtractionError(RuntimeError):
    def __init__(self, message: str, diagnostics: dict[str, object]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


def extract_pdf_text(
    pdf_path: Path,
    *,
    policy: ParserExecutionPolicy | None = None,
) -> str:
    result = run_parser_command(
        ["pdftotext", str(pdf_path), "-"], policy=policy
    )
    if not result.succeeded:
        diagnostics = result.diagnostics()
        message = result.error or f"pdftotext exited with status {result.returncode}"
        raise PdfExtractionError(message, diagnostics)
    return result.stdout
