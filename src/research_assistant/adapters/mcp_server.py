from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from research_assistant.adapters import local_tools

try:  # Optional dependency: base CLI installs must not require MCP.
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
except Exception:  # pragma: no cover - exercised through fallback tests.
    FastMCP = None  # type: ignore[assignment]
    ToolAnnotations = None  # type: ignore[assignment]


SERVER_NAME = "research-assistant-local"
SERVER_INSTRUCTIONS = (
    "Local read-only MCP adapter for a private research-assistant workspace. "
    "This server uses stdio, does not expose HTTP, and provides read-only tools "
    "by default. Grant-bound arXiv source intake requires a local grant; "
    "download, review-mutation, backup-restore, and destructive tools are not exposed."
)


def mcp_available() -> bool:
    return FastMCP is not None and ToolAnnotations is not None


def _default_root(root: str | Path | None = None) -> str | None:
    if root is not None:
        return str(root)
    return os.environ.get("RA_ROOT")


def _read_only_annotations(title: str):
    if ToolAnnotations is None:
        return None
    return ToolAnnotations(title=title, readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


def build_server(*, root: str | Path | None = None):
    if FastMCP is None:
        raise RuntimeError("MCP SDK is not installed. Install with `python -m pip install 'research-assistant[mcp]'`.")

    configured_root = _default_root(root)
    mcp = FastMCP(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)

    @mcp.tool(
        name="ra_workspace_status",
        description="Read local workspace/MCP status. Read-only; no files are written.",
        annotations=_read_only_annotations("Research assistant workspace status"),
    )
    def ra_workspace_status() -> dict[str, Any]:
        return local_tools.workspace_status(root=configured_root)

    @mcp.tool(
        name="ra_find_paper",
        description="Search local paper summaries. Read-only; does not fetch, ingest, or mutate records.",
        annotations=_read_only_annotations("Find local papers"),
    )
    def ra_find_paper(
        query: str,
        review_status: str | None = None,
        author: str | None = None,
        year: int | None = None,
    ) -> list[dict[str, Any]]:
        return local_tools.tool_find_paper(
            query,
            root=configured_root,
            review_status=review_status,
            author=author,
            year=year,
        )

    @mcp.tool(
        name="ra_get_paper_summary",
        description="Read a local paper summary with provenance and review status. Read-only review material.",
        annotations=_read_only_annotations("Get paper summary"),
    )
    def ra_get_paper_summary(paper_id: str) -> dict[str, Any]:
        return local_tools.tool_get_paper_summary(paper_id, root=configured_root)

    @mcp.tool(
        name="ra_paper_code_links",
        description="Read local paper-to-code/document links. Read-only.",
        annotations=_read_only_annotations("Get paper links"),
    )
    def ra_paper_code_links(paper_id: str) -> list[dict[str, Any]]:
        return local_tools.tool_paper_code_links(paper_id, root=configured_root)

    @mcp.tool(
        name="ra_claim_support_audit",
        description="Run a read-only summary-level claim-support audit over local papers.",
        annotations=_read_only_annotations("Audit claim support"),
    )
    def ra_claim_support_audit(claim: str, paper_ids: list[str]) -> dict[str, Any]:
        return local_tools.tool_claim_support_audit(claim, paper_ids, root=configured_root)

    @mcp.tool(
        name="ra_review_list",
        description="List local review items. Read-only; does not mark papers approved/rejected.",
        annotations=_read_only_annotations("List review items"),
    )
    def ra_review_list(status: str | None = None) -> list[dict[str, Any]]:
        return local_tools.tool_review_list(root=configured_root, status=status)

    @mcp.tool(
        name="ra_review_show",
        description="Show one local review item. Read-only; does not mutate review status.",
        annotations=_read_only_annotations("Show review item"),
    )
    def ra_review_show(paper_id: str) -> dict[str, Any]:
        return local_tools.tool_review_show(paper_id, root=configured_root)

    @mcp.tool(
        name="ra_source_show",
        description="Read a stored structured source record. Read-only; does not fetch arXiv or mutate source artifacts.",
        annotations=_read_only_annotations("Show source record"),
    )
    def ra_source_show(paper_id: str) -> dict[str, Any]:
        return local_tools.tool_source_show(paper_id, root=configured_root)

    @mcp.tool(
        name="ra_parser_tool_matrix",
        description="Read parser/tool readiness and limitations. Read-only.",
        annotations=_read_only_annotations("Parser tool matrix"),
    )
    def ra_parser_tool_matrix() -> dict[str, Any]:
        return local_tools.tool_parser_tool_matrix(root=configured_root)

    @mcp.tool(
        name="ra_privacy_status",
        description="Read offline/provider privacy status. Read-only.",
        annotations=_read_only_annotations("Privacy status"),
    )
    def ra_privacy_status() -> dict[str, Any]:
        return local_tools.tool_privacy_status(root=configured_root)

    @mcp.tool(
        name="ra_plan_arxiv_batch_intake",
        description="Plan bounded arXiv batch intake without writing files. Requires a separate local grant before execution.",
        annotations=_read_only_annotations("Plan arXiv batch intake"),
    )
    def ra_plan_arxiv_batch_intake(
        arxiv_ids: list[str] | None = None,
        query: str | None = None,
        max_papers: int = 10,
        destination: str = "source",
        operation: str = "source_fetch",
    ) -> dict[str, Any]:
        return local_tools.tool_plan_arxiv_batch_intake(
            arxiv_ids=arxiv_ids,
            query=query,
            max_papers=max_papers,
            destination=destination,
            operation=operation,
            root=configured_root,
        )

    @mcp.tool(
        name="ra_run_arxiv_batch_intake",
        description="Run grant-bound arXiv source intake. Requires a matching local grant ID and plan hash.",
        annotations=ToolAnnotations(
            title="Run grant-bound arXiv source intake",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ) if ToolAnnotations is not None else None,
    )
    def ra_run_arxiv_batch_intake(grant_id: str, plan_hash: str, arxiv_ids: list[str]) -> dict[str, Any]:
        return local_tools.tool_run_arxiv_batch_intake(
            grant_id=grant_id,
            plan_hash=plan_hash,
            arxiv_ids=arxiv_ids,
            root=configured_root,
        )

    @mcp.resource(
        "research-assistant://workspace/status",
        name="Research Assistant Workspace Status",
        description="Local read-only workspace status.",
        mime_type="application/json",
    )
    def resource_workspace_status() -> str:
        return json.dumps(local_tools.workspace_status(root=configured_root), indent=2, sort_keys=True)

    @mcp.resource(
        "research-assistant://paper/{paper_id}",
        name="Research Assistant Paper",
        description="Local read-only paper summary resource.",
        mime_type="application/json",
    )
    def resource_paper(paper_id: str) -> str:
        return json.dumps(local_tools.tool_get_paper_summary(paper_id, root=configured_root), indent=2, sort_keys=True)

    @mcp.resource(
        "research-assistant://source/{paper_id}",
        name="Research Assistant Source",
        description="Local read-only source record resource.",
        mime_type="application/json",
    )
    def resource_source(paper_id: str) -> str:
        return json.dumps(local_tools.tool_source_show(paper_id, root=configured_root), indent=2, sort_keys=True)

    return mcp


def available_tool_names() -> list[str]:
    return list(local_tools.READ_ONLY_TOOL_NAMES + local_tools.GRANT_BOUND_WRITE_TOOL_NAMES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ra-mcp")
    parser.add_argument("--root", help="Local research-assistant workspace root. Defaults to RA_ROOT or the current checkout root.")
    args = parser.parse_args(argv)

    if not mcp_available():
        raise SystemExit("MCP SDK is not installed. Install with `python -m pip install 'research-assistant[mcp]'`.")
    server = build_server(root=args.root)
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
