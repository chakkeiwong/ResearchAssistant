from __future__ import annotations

import gzip
import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.ingest.source_manifest import canonical_paper_id
from research_assistant.source.latex_bundle import detect_main_tex
from research_assistant.source.latex_extract import extract_latex_structure
from research_assistant.source.latex_flatten import flatten_latex_bundle
from research_assistant.source.structured_source import StructuredSourceRecord, arxiv_artifact_root, source_record_path
from research_assistant.storage.file_store import FileStore


def _status(source: str, status: str, *, reason: str | None = None, code: int | None = None, result_count: int = 0) -> dict[str, Any]:
    payload = {'source': source, 'status': status, 'result_count': result_count}
    if reason is not None:
        payload['reason'] = reason
    if code is not None:
        payload['code'] = code
    return payload


def arxiv_source_url(arxiv_id: str) -> str:
    return f'https://arxiv.org/e-print/{arxiv_id}'


def download_arxiv_source(arxiv_id: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(arxiv_source_url(arxiv_id), timeout=30) as response:
        destination.write_bytes(response.read())
    return destination


def unpack_arxiv_source(package_path: Path, unpack_dir: Path) -> dict[str, Any]:
    unpack_dir.mkdir(parents=True, exist_ok=True)
    diagnostics: dict[str, Any] = {'package_path': str(package_path), 'unpacked_files': []}
    if tarfile.is_tarfile(package_path):
        with tarfile.open(package_path) as archive:
            for member in archive.getmembers():
                target = (unpack_dir / member.name).resolve()
                if not target.is_relative_to(unpack_dir.resolve()):
                    diagnostics.setdefault('skipped_members', []).append(member.name)
                    continue
                archive.extract(member, unpack_dir)
                if member.isfile():
                    diagnostics['unpacked_files'].append(member.name)
        return diagnostics

    raw = package_path.read_bytes()
    if raw[:2] == b'\x1f\x8b':
        decompressed = gzip.decompress(raw)
        target = unpack_dir / f'{package_path.stem}.tex'
        target.write_bytes(decompressed)
        diagnostics['unpacked_files'].append(target.name)
        return diagnostics

    target = unpack_dir / 'source.tex'
    shutil.copy2(package_path, target)
    diagnostics['unpacked_files'].append(target.name)
    return diagnostics


def fetch_arxiv_structured_source(arxiv_id: str, *, root: Path | None = None, paper_id: str | None = None) -> StructuredSourceRecord:
    paths = get_paths(root)
    resolved_paper_id = paper_id or canonical_paper_id(f'arxiv:{arxiv_id}')
    artifact_root = arxiv_artifact_root(paths.papers_source, resolved_paper_id)
    original_path = artifact_root / 'original' / 'source-package'
    unpack_dir = artifact_root / 'unpacked'
    derived_dir = artifact_root / 'derived'
    source_statuses = []
    diagnostics: dict[str, Any] = {'arxiv_id': arxiv_id}

    try:
        download_arxiv_source(arxiv_id, original_path)
        source_statuses.append(_status('arxiv_source', 'available', result_count=1))
    except urllib.error.HTTPError as exc:
        source_statuses.append(_status('arxiv_source', 'unavailable', code=exc.code, reason=str(exc)))
        record = StructuredSourceRecord(
            paper_id=resolved_paper_id,
            source_type='arxiv_latex',
            status='unavailable',
            artifact_root=str(artifact_root),
            provenance={'arxiv_id': arxiv_id, 'source_statuses': source_statuses},
            diagnostics={'error': str(exc), **diagnostics},
            limitations=[{'field': 'source', 'status': 'unavailable', 'note': 'arXiv source could not be downloaded.'}],
        )
        FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, resolved_paper_id), record.to_dict())
        return record
    except Exception as exc:
        source_statuses.append(_status('arxiv_source', 'unavailable', reason=str(exc)))
        record = StructuredSourceRecord(
            paper_id=resolved_paper_id,
            source_type='arxiv_latex',
            status='unavailable',
            artifact_root=str(artifact_root),
            provenance={'arxiv_id': arxiv_id, 'source_statuses': source_statuses},
            diagnostics={'error': str(exc), **diagnostics},
            limitations=[{'field': 'source', 'status': 'unavailable', 'note': 'arXiv source could not be downloaded.'}],
        )
        FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, resolved_paper_id), record.to_dict())
        return record

    try:
        diagnostics['unpack'] = unpack_arxiv_source(original_path, unpack_dir)
        main_detection = detect_main_tex(unpack_dir)
        diagnostics['main_file_detection'] = main_detection
        main_path = Path(main_detection['main_path']) if main_detection.get('main_path') else None
        if main_path is None:
            raise ValueError('no TeX main file detected')
        flattened_path = derived_dir / 'flattened.tex'
        flatten_report = flatten_latex_bundle(main_path, unpack_dir, flattened_path)
        diagnostics['flatten'] = flatten_report
        structure = extract_latex_structure(flattened_path, source_root=unpack_dir)
        record = StructuredSourceRecord(
            paper_id=resolved_paper_id,
            source_type='arxiv_latex',
            status='available',
            primary_for_audit=True,
            artifact_root=str(artifact_root),
            original_source_path=str(original_path),
            flattened_source_path=str(flattened_path),
            sections=structure['sections'],
            equations=structure['equations'],
            theorem_like_blocks=structure['theorem_like_blocks'],
            labels=structure['labels'],
            references=structure['references'],
            citations=structure['citations'],
            bibliography=structure['bibliography'],
            macros=structure['macros'],
            provenance={'arxiv_id': arxiv_id, 'source_statuses': source_statuses, 'main_tex_path': str(main_path)},
            diagnostics=diagnostics,
            limitations=structure['limitations'],
        )
    except Exception as exc:
        record = StructuredSourceRecord(
            paper_id=resolved_paper_id,
            source_type='arxiv_latex',
            status='failed',
            artifact_root=str(artifact_root),
            original_source_path=str(original_path),
            primary_for_audit=False,
            provenance={'arxiv_id': arxiv_id, 'source_statuses': source_statuses},
            diagnostics={'error': str(exc), **diagnostics},
            limitations=[{'field': 'latex_structure', 'status': 'failed', 'note': str(exc)}],
        )

    FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, resolved_paper_id), record.to_dict())
    return record
