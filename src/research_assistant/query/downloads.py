from __future__ import annotations

from pathlib import Path
import urllib.request

from research_assistant.config import get_paths
from research_assistant.paths import slugify
from research_assistant.schemas.paper_record import PaperRecord
from research_assistant.storage.file_store import FileStore


def _proposal_metadata_dir(root: Path | None = None) -> Path:
    return get_paths(root).local_research / 'inbox' / 'metadata'


def _normalize_text(value: str | None) -> str:
    return slugify(value or '')


def _duplicate_candidates(result: dict, *, root: Path | None = None) -> list[dict]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    title_key = _normalize_text(result.get('title'))
    doi = (result.get('doi') or '').strip().lower()
    arxiv_id = (result.get('arxiv_id') or '').strip().lower()
    candidates = []
    for path in sorted(paths.summaries.glob('*.json')):
        rec = PaperRecord.from_dict(store.read_json(path))
        reasons = []
        if doi and (rec.doi or '').strip().lower() == doi:
            reasons.append('doi')
        if arxiv_id and (rec.arxiv_id or '').strip().lower() == arxiv_id:
            reasons.append('arxiv_id')
        if title_key and _normalize_text(rec.title) == title_key:
            reasons.append('title')
        if reasons:
            candidates.append({
                'paper_id': rec.id,
                'title': rec.title,
                'year': rec.year,
                'doi': rec.doi,
                'arxiv_id': rec.arxiv_id,
                'reasons': reasons,
            })
    raw_matches = []
    raw_dir = paths.papers_raw
    if raw_dir.exists() and title_key:
        for path in sorted(raw_dir.glob('*.pdf')):
            if title_key in slugify(path.stem):
                raw_matches.append(str(path))
    if raw_matches:
        candidates.append({'raw_paper_paths': raw_matches, 'reasons': ['raw_filename']})
    return candidates


class DownloadProposal:
    def __init__(self, *, title: str | None, source: str, pdf_url: str, inbox_path: Path, proposed_name: str, query: str | None = None, result: dict | None = None, duplicate_status: str = 'unique', duplicate_candidates: list[dict] | None = None):
        self.title = title or 'paper'
        self.source = source
        self.pdf_url = pdf_url
        self.inbox_path = inbox_path
        self.proposed_name = proposed_name
        self.query = query
        self.result = result or {}
        self.duplicate_status = duplicate_status
        self.duplicate_candidates = duplicate_candidates or []

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
            'duplicate_status': self.duplicate_status,
            'duplicate_candidates': self.duplicate_candidates,
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
    metadata_dir = _proposal_metadata_dir(root)
    metadata_path = metadata_dir / f'{Path(proposal.proposed_name).stem}.proposal.json'
    FileStore(paths.local_research).write_json(metadata_path, proposal.to_dict())
    return metadata_path


def list_download_proposals(*, root: Path | None = None, duplicate_status: str | None = None) -> list[dict]:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    rows = []
    for path in sorted(_proposal_metadata_dir(root).glob('*.proposal.json')):
        data = store.read_json(path)
        if duplicate_status and data.get('duplicate_status') != duplicate_status:
            continue
        data['proposal_path'] = str(path)
        data['duplicate_count'] = len(data.get('duplicate_candidates') or [])
        rows.append(data)
    return rows


def show_download_proposal(proposed_name: str, *, root: Path | None = None) -> dict:
    paths = get_paths(root)
    store = FileStore(paths.local_research)
    stem = Path(proposed_name).stem
    data = store.read_json(_proposal_metadata_dir(root) / f'{stem}.proposal.json')
    duplicate_candidates = data.get('duplicate_candidates') or []
    data['review_summary'] = {
        'duplicate_status': data.get('duplicate_status', 'unknown'),
        'duplicate_count': len(duplicate_candidates),
        'matched_paper_ids': [candidate['paper_id'] for candidate in duplicate_candidates if 'paper_id' in candidate],
        'has_raw_filename_match': any('raw_filename' in candidate.get('reasons', []) for candidate in duplicate_candidates),
    }
    return data


def propose_download(result: dict, *, root: Path | None = None, query: str | None = None) -> DownloadProposal:
    title = result.get('title') or 'paper'
    pdf_url = result.get('open_access_pdf_url') or ''
    proposed_name = f"{slugify(title)}.pdf"
    inbox_path = (get_paths(root).local_research / 'inbox' / proposed_name)
    duplicate_candidates = _duplicate_candidates(result, root=root)
    duplicate_status = 'possible_duplicate' if duplicate_candidates else 'unique'
    return DownloadProposal(
        title=title,
        source=result.get('source', 'unknown'),
        pdf_url=pdf_url,
        inbox_path=inbox_path,
        proposed_name=proposed_name,
        query=query,
        result=result,
        duplicate_status=duplicate_status,
        duplicate_candidates=duplicate_candidates,
    )
