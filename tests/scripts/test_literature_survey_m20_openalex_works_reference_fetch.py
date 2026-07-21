from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20_openalex_works_reference_fetch.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20_openalex_works", SCRIPT)
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
        "root_link_inventory_path": str(MODULE.ROOT_LINK_INVENTORY),
        "root_link_inventory_sha256": MODULE.ROOT_LINK_INVENTORY_SHA256,
        "command": [MODULE.sys.executable, str(SCRIPT), "--ledger", str(path), "--output-root", str(output)],
        "prior_transaction_count": 3,
        "prior_accepted_response_body_bytes": 448240,
        "campaign_transaction_cap": 6,
        "campaign_body_byte_cap": 8000000,
        "request": {
            "request_index": 4,
            "document_id": "openalex_works_reference",
            "provider": "openalex",
            "url": MODULE.TARGET_URL,
            "semantic_role": "works_routes_fields_authentication_and_cost",
            "requirement": "indispensable",
        },
    }
    path.write_text(json.dumps(ledger))
    return path, ledger


def test_ledger_binds_prior_evidence_exact_url_and_command(tmp_path: Path) -> None:
    path, ledger_raw = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    assert ledger["request"]["url"] == MODULE.TARGET_URL
    with pytest.raises(MODULE.BASE.FetchContractError, match="argv differs"):
        MODULE.validate_command(ledger, argv=["wrong"])
    ledger_raw["request"]["url"] += "/other"
    path.write_text(json.dumps(ledger_raw))
    with pytest.raises(MODULE.BASE.FetchContractError, match="reviewed row"):
        MODULE.validate_ledger(path, script_path=SCRIPT)


def test_success_closes_campaign_budget_and_one_dispatch(tmp_path: Path) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    body = b"<html><body>works</body></html>"
    opener = Opener(Response(body))
    result = MODULE.execute(ledger, output_root=tmp_path / "result", opener=opener)
    assert result["status"] == "fetched_pending_contract_extraction"
    assert result["campaign_attempted_transaction_count"] == 4
    assert result["campaign_transactions_remaining"] == 2
    assert result["campaign_accepted_response_body_bytes"] == 448240 + len(body)
    assert len(opener.requests) == 1


@pytest.mark.parametrize(
    ("response", "code"),
    [(Response(b"plain", content_type="text/plain"), "not_html"), (Response(b"\xff"), "invalid_utf8")],
)
def test_local_validation_failure_writes_campaign_blocker(tmp_path: Path, response: Response, code: str) -> None:
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
        (
            Response(
                b"x" * (MODULE.BASE.PER_RESPONSE_CAP + 1),
                include_content_length=False,
            ),
            "body_byte_cap_exceeded",
        ),
    ],
)
def test_inherited_blockers_close_both_manifests(
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


def test_redirect_blocker_closes_both_manifests(tmp_path: Path) -> None:
    path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    headers = Message()
    headers["Location"] = "https://developers.openalex.org/other"
    headers["Content-Type"] = "text/html"
    error = urllib.error.HTTPError(
        MODULE.TARGET_URL,
        302,
        "Found",
        headers,
        io.BytesIO(b"moved"),
    )

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
    assert (output / "campaign_manifest.json").is_file()
