from __future__ import annotations

from pathlib import Path
import urllib.request

from research_assistant.config import get_paths
from research_assistant.paths import slugify
from research_assistant.storage.file_store import FileStore


class DownloadProposal:
    def __init__(self, *, title: str | None, source: str, pdf_url: str, inbox_path: Path, proposed_name: str, query: str | None = None, result: dict | None = None):
        self.title = title or 'paper'
        self.source = source
        self.pdf_url = pdf_url
        self.inbox_path = inbox_path
        self.proposed_name = proposed_name
        self.query = query
        self.result = result or {}

    def to_dict(self) -> dict:
        return {
            'schema_version': 1,
            'title': self.title,
            'source': self.source,
            'pdf_url': self.pdf_url,
            'inbox_path': str(self.inbox_path),
            'proposed_name': self.proposed_name,
            'query': self.query,
            'result': self.result,
        }


def download_to_inbox(pdf_url: str, *, filename_hint: str, root: Path | None = None) -> Path:
    paths = get_paths(root)
    inbox = paths.local_research / 'inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    filename = f"{slugify(filename_hint)}.pdf"
    target = inbox / filename
    urllib.request.urlretrieve(pdf_url, target)
    return target


def persist_download_proposal(proposal: DownloadProposal, *, root: Path | None = None) -> Path:
    paths = get_paths(root)
    metadata_dir = paths.local_research / 'inbox' / 'metadata'
    metadata_path = metadata_dir / f'{Path(proposal.proposed_name).stem}.proposal.json'
    FileStore(paths.local_research).write_json(metadata_path, proposal.to_dict())
    return metadata_path


def propose_download(result: dict, *, root: Path | None = None, query: str | None = None) -> DownloadProposal:
    title = result.get('title') or 'paper'
    pdf_url = result.get('open_access_pdf_url') or ''
    proposed_name = f"{slugify(title)}.pdf"
    inbox_path = (get_paths(root).local_research / 'inbox' / proposed_name)
    return DownloadProposal(
        title=title,
        source=result.get('source', 'unknown'),
        pdf_url=pdf_url,
        inbox_path=inbox_path,
        proposed_name=proposed_name,
        query=query,
        result=result,
    )
