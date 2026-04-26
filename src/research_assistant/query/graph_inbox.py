from __future__ import annotations

from pathlib import Path
from typing import Any

from research_assistant.query.citation_cache import show_citation_graph
from research_assistant.query.downloads import persist_download_proposal, propose_download


def propose_graph_node_download(seed_paper_id: str, node_id: str, *, root: Path | None = None) -> dict[str, Any]:
    graph = show_citation_graph(seed_paper_id, root=root)
    node = graph.get('nodes', {}).get(node_id)
    if node is None:
        raise ValueError(f'no graph node {node_id}')
    if not node.get('open_access_pdf_url'):
        raise ValueError(f'graph node {node_id} has no open access pdf url')
    result = {
        'source': node.get('source', 'citation_graph'),
        'source_id': node.get('source_id'),
        'title': node.get('title'),
        'authors': node.get('authors') or [],
        'year': node.get('year'),
        'doi': node.get('doi'),
        'url': node.get('url'),
        'open_access_pdf_url': node.get('open_access_pdf_url'),
        'provenance': {'citation_graph_seed': seed_paper_id, 'node_id': node_id},
    }
    proposal = propose_download(result, root=root, query=f'citation graph node {node_id}')
    proposal_path = persist_download_proposal(proposal, root=root)
    return {
        'seed_paper_id': seed_paper_id,
        'node_id': node_id,
        'proposal': proposal.to_dict(),
        'proposal_path': str(proposal_path),
    }
