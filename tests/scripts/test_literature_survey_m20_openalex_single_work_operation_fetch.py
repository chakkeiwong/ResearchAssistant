from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20_openalex_single_work_operation_fetch.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20_openalex_single_work", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response:
    def __init__(
        self,
        body: bytes,
        *,
        content_type: str = "text/html",
        content_encoding: str | None = None,
        include_content_length: bool = True,
    ) -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if include_content_length:
            self.headers["Content-Length"] = str(len(body))
        if content_encoding is not None:
            self.headers["Content-Encoding"] = content_encoding

    def read(self, size: int = -1) -> bytes:
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return MODULE.TARGET_URL

    def getcode(self) -> int:
        return self.status

    def close(self) -> None:
        pass


class Opener:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.requests = []

    def open(self, request, timeout):  # noqa: ANN001, ANN201
        self.requests.append((request, timeout))
        return self.response


def _ledger(tmp_path: Path) -> tuple[Path, dict]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "ledger.json"
    output = tmp_path / "out"
    ledger = {
        "schema_version": MODULE.SCHEMA,
        "status": "reviewed_ready",
        "script_path": str(SCRIPT),
        "script_sha256": MODULE.sha256_path(SCRIPT),
        "base_script_path": str(MODULE.BASE_SCRIPT),
        "base_script_sha256": MODULE.sha256_path(MODULE.BASE_SCRIPT),
        "prior_campaign_manifest_path": str(MODULE.PRIOR_CAMPAIGN_MANIFEST),
        "prior_campaign_manifest_sha256": MODULE.PRIOR_CAMPAIGN_SHA256,
        "prior_fetch_manifest_path": str(MODULE.PRIOR_FETCH_MANIFEST),
        "prior_fetch_manifest_sha256": MODULE.PRIOR_FETCH_SHA256,
        "prior_body_path": str(MODULE.PRIOR_BODY),
        "prior_body_sha256": MODULE.PRIOR_BODY_SHA256,
        "prior_subplan_path": str(MODULE.PRIOR_SUBPLAN),
        "prior_subplan_sha256": MODULE.PRIOR_SUBPLAN_SHA256,
        "prior_contract_extract_path": str(MODULE.PRIOR_CONTRACT_EXTRACT),
        "prior_contract_extract_sha256": MODULE.PRIOR_CONTRACT_EXTRACT_SHA256,
        "prior_route_decision_path": str(MODULE.PRIOR_ROUTE_DECISION),
        "prior_route_decision_sha256": MODULE.PRIOR_ROUTE_DECISION_SHA256,
        "prior_result_path": str(MODULE.PRIOR_RESULT),
        "prior_result_sha256": MODULE.PRIOR_RESULT_SHA256,
        "command": [MODULE.sys.executable, str(SCRIPT), "--ledger", str(path), "--output-root", str(output)],
        "prior_transaction_count": 4,
        "prior_accepted_response_body_bytes": 1_168_335,
        "campaign_transaction_cap": 6,
        "campaign_body_byte_cap": 8_000_000,
        "request": {
            "request_index": 5,
            "document_id": "openalex_single_work_operation",
            "provider": "openalex",
            "url": MODULE.TARGET_URL,
            "semantic_role": "direct_work_identifier_selection_response_and_cost_contract",
            "requirement": "indispensable",
        },
    }
    path.write_text(json.dumps(ledger))
    return path, ledger


@pytest.mark.parametrize(
    "sha_key",
    [
        "prior_campaign_manifest_sha256",
        "prior_fetch_manifest_sha256",
        "prior_body_sha256",
        "prior_subplan_sha256",
        "prior_contract_extract_sha256",
        "prior_route_decision_sha256",
        "prior_result_sha256",
    ],
)
def test_ledger_binds_all_predecessors_exact_url_and_command(tmp_path: Path, sha_key: str) -> None:
    path, raw = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    assert ledger["request"]["url"] == MODULE.TARGET_URL
    with pytest.raises(MODULE.BASE.FetchContractError, match="argv differs"):
        MODULE.validate_command(ledger, argv=["wrong"])
    raw[sha_key] = "0" * 64
    path.write_text(json.dumps(raw))
    with pytest.raises(MODULE.BASE.FetchContractError, match="predecessor bindings differ"):
        MODULE.validate_ledger(path, script_path=SCRIPT)


def test_route_decision_uses_closed_status_vocabulary(tmp_path: Path) -> None:
    path, _ = _ledger(tmp_path)
    assert MODULE.validate_ledger(path, script_path=SCRIPT)["request"]["request_index"] == 5
    decision = json.loads(MODULE.PRIOR_ROUTE_DECISION.read_text())
    assert {
        row["status"] for row in decision["decisions"].values()
    } <= {"supported", "contradicted", "ambiguous", "not_documented"}


def test_request_or_budget_drift_fails_before_dispatch(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    path, raw = _ledger(tmp_path)
    raw["request"]["url"] += "/other"
    path.write_text(json.dumps(raw))
    with pytest.raises(MODULE.BASE.FetchContractError, match="reviewed row"):
        MODULE.validate_ledger(path, script_path=SCRIPT)
    path, _ = _ledger(tmp_path / "cap")
    monkeypatch.setattr(MODULE.BASE, "PER_RESPONSE_CAP", MODULE.REMAINING_BODY_BYTE_CAP + 1)
    with pytest.raises(MODULE.BASE.FetchContractError, match="remaining campaign allowance"):
        MODULE.validate_ledger(path, script_path=SCRIPT)


def test_success_closes_campaign_budget_and_dispatches_once(tmp_path: Path) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    body = b"<html><body>single work</body></html>"
    opener = Opener(Response(body))
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=opener)
    assert result["status"] == "fetched_pending_contract_extraction"
    assert result["campaign_attempted_transaction_count"] == 5
    assert result["campaign_transactions_remaining"] == 1
    assert result["campaign_accepted_response_body_bytes"] == 1_168_335 + len(body)
    assert len(opener.requests) == 1
    request, timeout = opener.requests[0]
    assert request.full_url == MODULE.TARGET_URL
    assert request.get_method() == "GET"
    assert timeout == MODULE.BASE.TIMEOUT_SECONDS
    assert (output / "fetch_manifest.json").is_file()
    assert (output / "campaign_manifest.json").is_file()


@pytest.mark.parametrize(
    ("response", "code"),
    [(Response(b"plain", content_type="text/plain"), "not_html"), (Response(b"\xff"), "invalid_utf8")],
)
def test_local_validation_failure_closes_manifests(tmp_path: Path, response: Response, code: str) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=Opener(response))
    assert result["status"] == "blocked_local_validation_error"
    assert result["local_validation_error_code"] == code
    assert (output / "fetch_manifest.json").is_file()
    assert (output / "campaign_manifest.json").is_file()


def test_existing_output_root_prevents_dispatch(tmp_path: Path) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    output = tmp_path / "result"
    output.mkdir()
    opener = Opener(Response(b"x"))
    with pytest.raises(FileExistsError):
        MODULE.execute(ledger, output_root=output, opener=opener)
    assert opener.requests == []


@pytest.mark.parametrize(
    ("response", "error_code"),
    [
        (Response(b"compressed", content_encoding="gzip"), "compressed_response"),
        (Response(b"x" * (2_000_001), include_content_length=False), "body_byte_cap_exceeded"),
    ],
)
def test_inherited_transport_blockers_close_manifests(
    tmp_path: Path,
    response: Response,
    error_code: str,
) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    output = tmp_path / "result"
    opener = Opener(response)
    result = MODULE.execute(ledger, output_root=output, opener=opener)
    assert result["status"] == "blocked"
    assert len(opener.requests) == 1
    fetch = json.loads((output / "fetch_manifest.json").read_text())
    assert fetch["requests"][0]["error_code"] == error_code
    assert (output / "campaign_manifest.json").is_file()


def test_redirect_blocker_closes_manifests(tmp_path: Path) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    headers = Message()
    headers["Location"] = "https://developers.openalex.org/other"
    headers["Content-Type"] = "text/html"
    error = urllib.error.HTTPError(MODULE.TARGET_URL, 302, "Found", headers, io.BytesIO(b"moved"))

    class RedirectOpener:
        def __init__(self) -> None:
            self.requests = []

        def open(self, request, timeout):  # noqa: ANN001, ANN201
            self.requests.append((request, timeout))
            raise error

    output = tmp_path / "result"
    opener = RedirectOpener()
    result = MODULE.execute(ledger, output_root=output, opener=opener)
    assert result["status"] == "blocked"
    assert len(opener.requests) == 1
    fetch = json.loads((output / "fetch_manifest.json").read_text())
    assert fetch["requests"][0]["outcome"] == "blocked_redirect"
    assert fetch["requests"][0]["error_code"] == "redirect_forbidden"


def test_campaign_postcheck_blocks_impossible_aggregate(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    monkeypatch.setattr(MODULE, "PRIOR_ACCEPTED_BODY_BYTES", MODULE.CAMPAIGN_BODY_BYTE_CAP)
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=Opener(Response(b"x")))
    assert result["status"] == "blocked_campaign_body_cap_exceeded"
    assert result["local_validation_error_code"] == "campaign_body_cap_exceeded"
