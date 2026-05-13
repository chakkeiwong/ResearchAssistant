from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from research_assistant.adapters import mcp_permissions


def test_mcp_permission_status_is_local_and_non_destructive(tmp_path: Path) -> None:
    status = mcp_permissions.mcp_permissions_status(root=tmp_path)
    assert status["default_mode"] == "read_only"
    assert status["destructive_tools_enabled"] is False
    assert status["review_write_enabled"] is False
    assert "arxiv.org" in status["allowed_arxiv_domains"]


def test_create_and_validate_arxiv_batch_grant(tmp_path: Path) -> None:
    created = mcp_permissions.create_arxiv_batch_grant(
        plan_hash="hash_a",
        operation="source_fetch",
        destination="source",
        max_papers=2,
        expires_hours=2,
        root=tmp_path,
        arxiv_ids=["2401.00002", "2401.00001", "2401.00001"],
    )
    assert created["status"] == "created"
    grant = created["grant"]
    assert grant["arxiv_ids"] == ["2401.00001", "2401.00002"]

    validation = mcp_permissions.validate_arxiv_batch_grant(
        grant,
        plan_hash="hash_a",
        operation="source_fetch",
        destination="source",
        root=tmp_path,
        arxiv_ids=["2401.00001", "2401.00002"],
    )
    assert validation["status"] == "ok"

    mismatch = mcp_permissions.validate_arxiv_batch_grant(
        grant,
        plan_hash="hash_b",
        operation="source_fetch",
        destination="source",
        root=tmp_path,
        arxiv_ids=["2401.00001", "2401.00002"],
    )
    assert mismatch["status"] == "blocked"
    assert mismatch["issues"][0]["code"] == "plan_hash_mismatch"


def test_expired_grant_is_rejected(tmp_path: Path) -> None:
    created = mcp_permissions.create_arxiv_batch_grant(
        plan_hash="hash_a",
        max_papers=1,
        root=tmp_path,
        arxiv_ids=["2401.00001"],
    )
    grant = dict(created["grant"])
    grant["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0).isoformat()

    validation = mcp_permissions.validate_arxiv_batch_grant(
        grant,
        plan_hash="hash_a",
        operation="source_fetch",
        destination="source",
        root=tmp_path,
        arxiv_ids=["2401.00001"],
    )
    assert validation["status"] == "blocked"
    assert any(issue["code"] == "grant_expired" for issue in validation["issues"])


def test_destination_and_domain_validation_reject_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.pdf"
    dest = mcp_permissions.validate_destination_path(outside, root=tmp_path)
    assert dest["status"] == "blocked"
    assert dest["code"] == "destination_outside_workspace"

    domains = mcp_permissions.validate_allowed_domains([
        "https://arxiv.org/e-print/2401.00001",
        "https://example.com/paper.pdf",
    ])
    assert domains["status"] == "blocked"
    assert domains["blocked"][0]["host"] == "example.com"
