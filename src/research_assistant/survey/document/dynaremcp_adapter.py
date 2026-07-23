from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .contracts import sha256_file, write_json


def _canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def run_dynaremcp_qa(
    *,
    executable: str | None,
    run_root: Path,
    source_path: Path,
    facts: list[dict[str, Any]],
    promises: list[dict[str, Any]],
    paid_ids: list[str],
    terms: list[dict[str, Any]],
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    if not executable:
        return {
            "status": "external_document_qa_not_run",
            "accepted": False,
            "reason": "provider_not_configured",
            "what_is_not_concluded": ["document structure was not checked by DynareMCP"],
        }
    request = {
        "schema_version": "dynaremcp.document_utility_request.v1",
        "request_id": "research-assistant-document",
        "operation": "structured_diagnostics",
        "request_root": str(run_root.resolve()),
        "entry_document": str(source_path.resolve().relative_to(run_root.resolve())),
        "entry_document_sha256": sha256_file(source_path),
        "facts": facts,
        "promises": promises,
        "paid_ids": paid_ids,
        "terms": terms,
    }
    request_path = run_root / "dynaremcp_request.json"
    result_path = run_root / "dynaremcp_result.json"
    write_json(request_path, request)
    argv = [*shlex.split(executable), "document-utility", "check", "--request", str(request_path), "--out", str(result_path)]
    try:
        completed = subprocess.run(
            argv,
            cwd=run_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "external_document_qa_unavailable", "accepted": False, "reason": type(exc).__name__}
    if completed.returncode != 0 or not result_path.is_file():
        return {
            "status": "external_document_qa_failed",
            "accepted": False,
            "reason": "provider_nonzero_or_missing_result",
            "returncode": completed.returncode,
            "stderr": completed.stderr[-1000:],
        }
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "external_document_qa_failed", "accepted": False, "reason": "invalid_provider_result"}
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != "dynaremcp.document_utility_result.v1"
        or result.get("request_id") != request["request_id"]
        or result.get("request_sha256") != _canonical_hash(request)
    ):
        return {"status": "external_document_qa_failed", "accepted": False, "reason": "unbound_provider_result"}
    result_hash = result.get("result_sha256")
    semantic_result = dict(result)
    semantic_result.pop("result_sha256", None)
    if result_hash != _canonical_hash(semantic_result):
        return {"status": "external_document_qa_failed", "accepted": False, "reason": "stale_provider_result"}
    findings = result.get("findings")
    if not isinstance(findings, list):
        return {"status": "external_document_qa_failed", "accepted": False, "reason": "invalid_provider_findings"}
    qa_status = (
        "external_document_qa_passed"
        if result.get("accepted") is True and not findings
        else "external_document_qa_findings"
        if result.get("accepted") is True
        else "external_document_qa_blocked"
    )
    return {
        "status": qa_status,
        "accepted": result.get("accepted") is True and not findings,
        "provider_result": result,
    }
