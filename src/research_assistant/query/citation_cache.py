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


def _add_neighborhood(graph: dict[str, Any], center_id: str, neighborhood: dict[str, Any], *, expand: bool = False) -> list[str]:
    discovered = []
    graph['source_statuses'].extend(neighborhood.get('source_statuses') or [])
    unavailable = set(graph['diagnostics'].get('unavailable_endpoints') or [])
    available_empty = set(graph['diagnostics'].get('available_empty_endpoints') or [])
    for endpoint in (neighborhood.get('diagnostics') or {}).get('unavailable_endpoints') or []:
        unavailable.add(endpoint)
    for endpoint in (neighborhood.get('diagnostics') or {}).get('available_empty_endpoints') or []:
        available_empty.add(endpoint)
    graph['diagnostics']['unavailable_endpoints'] = sorted(unavailable)
    graph['diagnostics']['available_empty_endpoints'] = sorted(available_empty)
    graph['diagnostics'].setdefault('failure_reasons', []).extend((neighborhood.get('diagnostics') or {}).get('failure_reasons') or [])
    for direction, endpoint, rows in [('citing', 'citations', neighborhood.get('citing') or []), ('cited', 'references', neighborhood.get('cited') or [])]:
        for row in rows:
            key = _node_key(row)
            graph['nodes'].setdefault(key, _node_from_row(row))
            if direction == 'citing':
                source, target = key, center_id
            else:
                source, target = center_id, key
            edge = {
                'source': source,
                'target': target,
                'direction': direction,
                'endpoint': endpoint,
                'provenance': row.get('provenance') or {},
            }
            if edge not in graph['edges']:
                graph['edges'].append(edge)
            if expand:
                discovered.append(key)
    return discovered


def build_citation_graph(paper_id: str, *, root: Path | None = None, depth: int = 1, limit: int = 5, refresh: bool = False) -> dict[str, Any]:
    if depth not in {1, 2}:
        raise ValueError('citation graph depth is currently limited to 1 or 2')
    path = citation_graph_path(root, paper_id)
    if path.exists() and not refresh:
        return FileStore(get_paths(root).local_research).read_json(path)
    neighborhood = citation_graph.citation_neighborhood(paper_id, limit=limit)
    graph = {
        'seed_paper_id': paper_id,
        'depth': depth,
        'limit': limit,
        'status': neighborhood.get('status'),
        'status_reason': neighborhood.get('status_reason'),
        'nodes': {
            paper_id: {
                'local_paper_id': paper_id,
                'seed': True,
            }
        },
        'edges': [],
        'source_statuses': [],
        'diagnostics': {'unavailable_endpoints': [], 'available_empty_endpoints': [], 'failure_reasons': []},
        'summary': neighborhood.get('summary') or {},
    }
    frontier = _add_neighborhood(graph, paper_id, neighborhood, expand=depth > 1)
    if depth == 2:
        for node_id in frontier[:limit]:
            child = citation_graph.citation_neighborhood(node_id, limit=limit)
            _add_neighborhood(graph, node_id, child, expand=False)
    graph['diagnostics']['node_count'] = len(graph['nodes'])
    graph['diagnostics']['edge_count'] = len(graph['edges'])
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
