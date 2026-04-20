from __future__ import annotations

from pathlib import Path
from typing import Protocol

from research_assistant.schemas.parsed_document import ParsedDocument


class DocumentParser(Protocol):
    name: str

    def parse(self, pdf_path: Path) -> ParsedDocument:
        ...
