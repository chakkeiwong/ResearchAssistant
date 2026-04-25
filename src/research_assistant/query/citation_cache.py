from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.query import citation_graph
from research_assistant.storage.file_store import FileStore


def citation_graph_path(root: Path | None, paper_id: str) -> Path:
    return get_paths(root).local_research / 'graphs' / 'citations' / f'{paper_id}.json'


def _node_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'source': row.get('source'),
        'source_id': row.get('source_id'),
        'title': row.get('title'),
        'authors': row.get('authors') or [],
        'year': row.get('year'),
        'doi': row.get('doi'),
        'url': row.get('url'),
        'open_access_pdf_url': row.get('open_access_pdf_url'),
        'ranking': row.get('ranking') or {},
        'ranking_score': row.get('ranking_score'),
    }


def _node_key(row: dict[str, Any]) -> str:
    if row.get('doi'):
        return f"doi:{str(row['doi']).lower()}"
    if row.get('source') and row.get('source_id'):
        return f"{row['source']}:{row['source_id']}"
    return f"title:{row.get('title', '')}"


def build_citation_graph(paper_id: str, *, root: Path | None = None, depth: int = 1, limit: int = 5, refresh: bool = False) -> dict[str, Any]:
    if depth != 1:
        raise ValueError('citation graph depth is currently limited to 1')
    path = citation_graph_path(root, paper_id)
    if path.exists() and not refresh:
        return FileStore(get_paths(root).local_research).read_json(path)
    neighborhood = citation_graph.citation_neighborhood(paper_id, limit=limit)
    nodes = {
        paper_id: {
            'local_paper_id': paper_id,
            'seed': True,
        }
    }
    edges = []
    for direction, endpoint, rows in [('citing', 'citations', neighborhood.get('citing') or []), ('cited', 'references', neighborhood.get('cited') or [])]:
        for row in rows:
            key = _node_key(row)
            nodes.setdefault(key, _node_from_row(row))
            if direction == 'citing':
                source, target = key, paper_id
            else:
                source, target = paper_id, key
            edges.append({
                'source': source,
                'target': target,
                'direction': direction,
                'endpoint': endpoint,
                'provenance': row.get('provenance') or {},
            })
    graph = {
        'seed_paper_id': paper_id,
        'depth': depth,
        'limit': limit,
        'status': neighborhood.get('status'),
        'status_reason': neighborhood.get('status_reason'),
        'nodes': nodes,
        'edges': edges,
        'source_statuses': neighborhood.get('source_statuses') or [],
        'diagnostics': neighborhood.get('diagnostics') or {},
        'summary': neighborhood.get('summary') or {},
    }
    FileStore(get_paths(root).local_research).write_json(path, graph)
    return graph


def show_citation_graph(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    path = citation_graph_path(root, paper_id)
    return FileStore(get_paths(root).local_research).read_json(path)


def export_citation_graph(paper_id: str, output: Path, *, root: Path | None = None) -> Path:
    source = citation_graph_path(root, paper_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    return output
