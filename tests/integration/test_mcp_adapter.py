from __future__ import annotations

import json
from pathlib import Path

from research_assistant.adapters import local_tools
from research_assistant.adapters import mcp_server
from research_assistant.individual_release import demo_setup
from research_assistant.query.paper_lookup import get_paper_summary


def _mcp_payload(result):
    content, structured = result
    if structured and "result" in structured:
        return structured["result"]
    return json.loads(content[0].text)


def test_local_tools_workspace_status_is_read_only(tmp_path: Path) -> None:
    status = local_tools.workspace_status(root=tmp_path)
    assert status["mode"] == "read_only"
    assert status["transport"] == "stdio"
    assert status["hosted_service"] is False
    assert status["write_tools_enabled"] is False
    assert status["destructive_tools_enabled"] is False


def test_local_tools_query_demo_workspace_without_writes(tmp_path: Path) -> None:
    setup = demo_setup(root=tmp_path)
    paper_id = setup["paper_id"]

    rows = local_tools.tool_find_paper("transport", root=tmp_path)
    assert rows[0]["paper_id"] == paper_id

    summary = local_tools.tool_get_paper_summary(paper_id, root=tmp_path)
    assert summary["summary"]["title"] == "Demo Transport Map Paper"
    assert summary["source_extraction"]["available"] is True
    assert any("read-only" in item for item in summary["limitations"])

    source = local_tools.tool_source_show(paper_id, root=tmp_path)
    assert source["status"] == "available"
    assert source["record_path"].endswith(f"{paper_id}.json")

    review = local_tools.tool_review_show(paper_id, root=tmp_path)
    assert review["mcp_read_only"] is True
    assert review["review_status"] == "needs_review"

    claim = local_tools.tool_claim_support_audit("demo claim", [paper_id], root=tmp_path)
    assert claim["confidence"] == "low"

    after = get_paper_summary(paper_id, root=tmp_path)
    assert after["review"]["review_status"] == "needs_review"


def test_local_tools_environment_root_resolution(tmp_path: Path, monkeypatch) -> None:
    setup = demo_setup(root=tmp_path)
    monkeypatch.setenv("RA_ROOT", str(tmp_path))

    rows = local_tools.tool_find_paper("demo")
    assert rows[0]["paper_id"] == setup["paper_id"]


def test_local_tools_source_missing_is_structured(tmp_path: Path) -> None:
    payload = local_tools.tool_source_show("missing_paper", root=tmp_path)
    assert payload["available"] is False
    assert payload["record_path"] is None
    assert payload["limitations"][0]["field"] == "source"


def test_local_tools_outputs_are_json_serializable(tmp_path: Path) -> None:
    setup = demo_setup(root=tmp_path)
    payloads = [
        local_tools.workspace_status(root=tmp_path),
        local_tools.tool_find_paper("demo", root=tmp_path),
        local_tools.tool_get_paper_summary(setup["paper_id"], root=tmp_path),
        local_tools.tool_parser_tool_matrix(root=tmp_path),
        local_tools.tool_privacy_status(root=tmp_path),
    ]
    for payload in payloads:
        json.dumps(payload, sort_keys=True)


def test_mcp_server_exposes_only_read_only_tool_names() -> None:
    names = set(mcp_server.available_tool_names())
    assert names == set(local_tools.READ_ONLY_TOOL_NAMES + local_tools.GRANT_BOUND_WRITE_TOOL_NAMES)
    assert "ra_run_arxiv_batch_intake" in names
    assert "review-mark" not in names
    assert "ra_review_mark" not in names
    assert "ra_ingest" not in names
    assert "ra_download_paper" not in names
    assert "ra_backup_restore" not in names


def test_mcp_server_direct_tool_calls_when_sdk_available(tmp_path: Path) -> None:
    if not mcp_server.mcp_available():
        return

    import asyncio

    setup = demo_setup(root=tmp_path)
    server = mcp_server.build_server(root=tmp_path)

    async def exercise() -> None:
        tools = await server.list_tools()
        names = {tool.name for tool in tools}
        assert set(local_tools.READ_ONLY_TOOL_NAMES).issubset(names)
        assert "ra_run_arxiv_batch_intake" in names
        assert "ra_review_mark" not in names
        assert "ra_audit_note_append" not in names
        assert "ra_audit_note_set" not in names
        assert "ra_download_paper" not in names
        assert "ra_ingest" not in names
        assert "ra_backup_restore" not in names

        result = await server.call_tool("ra_find_paper", {"query": "demo"})
        rows = _mcp_payload(result)
        assert rows[0]["paper_id"] == setup["paper_id"]

        status = await server.call_tool("ra_workspace_status", {})
        payload = _mcp_payload(status)
        assert payload["mode"] == "read_only"
        assert payload["hosted_service"] is False

        source = await server.read_resource(f"research-assistant://source/{setup['paper_id']}")
        source_payload = json.loads(source[0].content)
        assert source_payload["status"] == "available"

    asyncio.run(exercise())
