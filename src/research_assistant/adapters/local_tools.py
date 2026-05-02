from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.ingest.arxiv_batch import plan_arxiv_batch_intake, run_arxiv_batch_intake
from research_assistant.individual_release import doctor, parser_tool_matrix, privacy_status
from research_assistant.query.paper_lookup import claim_support_audit, find_paper, get_paper_summary, paper_code_links
from research_assistant.query.review import list_review_items, show_review_item
from research_assistant.source.structured_source import source_record_path
from research_assistant.storage.file_store import FileStore


READ_ONLY_TOOL_NAMES = [
    "ra_workspace_status",
    "ra_find_paper",
    "ra_get_paper_summary",
    "ra_paper_code_links",
    "ra_claim_support_audit",
    "ra_review_list",
    "ra_review_show",
    "ra_source_show",
    "ra_parser_tool_matrix",
    "ra_privacy_status",
    "ra_plan_arxiv_batch_intake",
]

GRANT_BOUND_WRITE_TOOL_NAMES = [
    "ra_run_arxiv_batch_intake",
]


def resolve_workspace_root(root: str | Path | None = None) -> Path:
    value = root if root is not None else os.environ.get("RA_ROOT")
    candidate = Path(value).expanduser() if value else get_paths().root
    return candidate.resolve()


def workspace_status(*, root: str | Path | None = None) -> dict[str, Any]:
    paths = get_paths(resolve_workspace_root(root))
    local_research_exists = paths.local_research.exists()
    return {
        "status": "ok" if local_research_exists else "warnings",
        "workspace_root": str(paths.root),
        "local_research": str(paths.local_research),
        "local_research_exists": local_research_exists,
        "mode": "read_only",
        "transport": "stdio",
        "hosted_service": False,
        "write_tools_enabled": False,
        "destructive_tools_enabled": False,
        "limitations": [
            "Local MCP is an adapter over a private local workspace, not a hosted service.",
            "Read-only tools do not ingest, download, mutate review state, restore backups, or delete files.",
        ],
    }


def tool_find_paper(
    query: str,
    *,
    root: str | Path | None = None,
    review_status: str | None = None,
    author: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    return find_paper(
        query,
        root=resolve_workspace_root(root),
        review_status=review_status,
        author=author,
        year=year,
    )


def tool_get_paper_summary(paper_id: str, *, root: str | Path | None = None) -> dict[str, Any]:
    payload = get_paper_summary(paper_id, root=resolve_workspace_root(root))
    payload.setdefault("limitations", []).append(
        "MCP summary output is read-only review material; generated/parser-derived fields are not mathematical approval."
    )
    return payload


def tool_paper_code_links(paper_id: str, *, root: str | Path | None = None) -> list[dict[str, Any]]:
    return paper_code_links(paper_id, root=resolve_workspace_root(root))


def tool_claim_support_audit(claim: str, paper_ids: list[str], *, root: str | Path | None = None) -> dict[str, Any]:
    payload = claim_support_audit(claim, paper_ids, root=resolve_workspace_root(root))
    payload.setdefault("limitations", []).append("MCP claim audit is read-only and summary-level unless stronger evidence is added later.")
    return payload


def tool_review_list(*, root: str | Path | None = None, status: str | None = None) -> list[dict[str, Any]]:
    return list_review_items(root=resolve_workspace_root(root), status=status)


def tool_review_show(paper_id: str, *, root: str | Path | None = None) -> dict[str, Any]:
    payload = show_review_item(paper_id, root=resolve_workspace_root(root))
    payload["mcp_read_only"] = True
    return payload


def tool_source_show(paper_id: str, *, root: str | Path | None = None) -> dict[str, Any]:
    paths = get_paths(resolve_workspace_root(root))
    path = source_record_path(paths.papers_source, paper_id)
    if not path.exists():
        return {
            "available": False,
            "paper_id": paper_id,
            "record_path": None,
            "limitations": [
                {
                    "field": "source",
                    "status": "unavailable",
                    "note": "No structured source artifact is stored for this paper.",
                }
            ],
        }
    payload = FileStore(paths.local_research).read_json(path)
    payload["record_path"] = str(path)
    payload.setdefault("limitations", []).append(
        {"field": "mcp", "status": "read_only", "note": "Source inspection through MCP does not fetch or mutate source artifacts."}
    )
    return payload


def tool_parser_tool_matrix(*, root: str | Path | None = None) -> dict[str, Any]:
    return parser_tool_matrix(root=resolve_workspace_root(root))


def tool_privacy_status(*, root: str | Path | None = None) -> dict[str, Any]:
    payload = privacy_status(root=resolve_workspace_root(root))
    payload["mcp_default_mode"] = "read_only"
    payload["mcp_hosted_service"] = False
    return payload


def tool_doctor_status(*, root: str | Path | None = None) -> dict[str, Any]:
    return doctor(root=resolve_workspace_root(root), include_matrix=True)


def tool_plan_arxiv_batch_intake(
    *,
    arxiv_ids: list[str] | None = None,
    query: str | None = None,
    max_papers: int,
    destination: str = "source",
    operation: str = "source_fetch",
    root: str | Path | None = None,
) -> dict[str, Any]:
    if destination not in {"source", "inbox"}:
        return {"status": "blocked", "issues": [{"code": "unsupported_destination", "destination": destination}]}
    if operation not in {"source_fetch", "pdf_inbox_download", "metadata_only"}:
        return {"status": "blocked", "issues": [{"code": "unsupported_operation", "operation": operation}]}
    return plan_arxiv_batch_intake(
        query=query,
        arxiv_ids=arxiv_ids,
        max_papers=max_papers,
        destination=destination,  # type: ignore[arg-type]
        operation=operation,  # type: ignore[arg-type]
        root=resolve_workspace_root(root),
    )


def tool_run_arxiv_batch_intake(
    *,
    grant_id: str,
    plan_hash: str,
    arxiv_ids: list[str],
    root: str | Path | None = None,
) -> dict[str, Any]:
    return run_arxiv_batch_intake(
        grant_id=grant_id,
        plan_hash=plan_hash,
        arxiv_ids=arxiv_ids,
        root=resolve_workspace_root(root),
    )
