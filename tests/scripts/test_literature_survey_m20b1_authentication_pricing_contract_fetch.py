from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20b1_authentication_pricing_contract_fetch.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20b1_auth_pricing", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response:
    def __init__(self, body: bytes, *, url: str, content_type: str = "text/html; charset=utf-8", content_encoding: str | None = None,
                 include_content_length: bool = True) -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.url = url
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
        return self.url

    def getcode(self) -> int:
        return self.status

    def close(self) -> None:
        pass


class Opener:
    def __init__(self, responses) -> None:  # noqa: ANN001
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):  # noqa: ANN001, ANN201
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _ledger(tmp_path: Path, *, status: str = "reviewed_ready") -> tuple[Path, dict, Path]:
    path = tmp_path / "ledger.json"
    output = tmp_path / "out"
    ledger = {
        "schema_version": MODULE.SCHEMA,
        "status": status,
        "campaign_id": "literature-survey-m20b1-auth-pricing-20260714-v1",
        "script_path": str(SCRIPT),
        "script_sha256": MODULE.sha256_path(SCRIPT),
        "supervisor_path": str(MODULE.SUPERVISOR_SCRIPT),
        "supervisor_sha256": MODULE.sha256_path(MODULE.SUPERVISOR_SCRIPT),
        "base_script_path": str(MODULE.BASE_SCRIPT),
        "base_script_sha256": MODULE.sha256_path(MODULE.BASE_SCRIPT),
        "command": [MODULE.sys.executable, str(Path("scripts/literature_survey_m20b1_authentication_pricing_contract_supervisor.py").resolve()), "--ledger", str(path), "--output-root", str(output)],
        "worker_command": [MODULE.sys.executable, str(SCRIPT), "--ledger", str(path), "--output-root", str(output)],
        "transaction_cap": 2,
        "per_response_body_byte_cap": 2_000_000,
        "aggregate_body_byte_cap": 4_000_000,
        "diagnostic_overflow_byte_cap": 1,
        "timeout_seconds": 30,
        "wall_time_cap_seconds": 90,
        "redirect_policy": "automatic_redirects_disabled_any_3xx_blocks_phase",
        "proxy_policy": "explicit_empty_proxy_handler",
        "compression_policy": "no_accept_encoding_and_reject_non_identity_content_encoding",
        "requests": [dict(row) for row in MODULE.EXPECTED_REQUESTS],
    }
    for name, predecessor, digest in MODULE.PREDECESSORS:
        ledger[f"{name}_path"] = str(predecessor)
        ledger[f"{name}_sha256"] = digest
    path.write_text(json.dumps(ledger))
    return path, ledger, output


def test_exact_two_documentation_targets_and_predecessors(tmp_path: Path) -> None:
    path, raw, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    assert [row["url"] for row in ledger["requests"]] == [
        "https://developers.openalex.org/api-reference/authentication",
        "https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status",
    ]
    assert all("api.openalex.org" not in row["url"] for row in ledger["requests"])
    raw["requests"][0]["url"] = "https://api.openalex.org/works"
    path.write_text(json.dumps(raw))
    with pytest.raises(MODULE.BASE.FetchContractError):
        MODULE.validate_ledger(path, script_path=SCRIPT)


def test_review_pending_ledger_cannot_execute(tmp_path: Path) -> None:
    path, _, _ = _ledger(tmp_path, status="review_pending")
    with pytest.raises(MODULE.BASE.FetchContractError, match="status"):
        MODULE.validate_ledger(path, script_path=SCRIPT)


def test_supervisor_identity_drift_cannot_execute(tmp_path: Path) -> None:
    path, raw, _ = _ledger(tmp_path)
    raw["supervisor_sha256"] = "0" * 64
    path.write_text(json.dumps(raw))
    with pytest.raises(MODULE.BASE.FetchContractError, match="supervisor"):
        MODULE.validate_ledger(path, script_path=SCRIPT)


@pytest.mark.parametrize("name", [row[0] for row in MODULE.PREDECESSORS])
def test_every_predecessor_digest_is_bound(tmp_path: Path, name: str) -> None:
    path, raw, _ = _ledger(tmp_path)
    raw[f"{name}_sha256"] = "0" * 64
    path.write_text(json.dumps(raw))
    with pytest.raises(MODULE.BASE.FetchContractError, match="predecessor"):
        MODULE.validate_ledger(path, script_path=SCRIPT)


def test_success_dispatches_two_gets_and_closes_manifests(tmp_path: Path) -> None:
    path, _, output = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    opener = Opener([Response(b"auth", url=ledger["requests"][0]["url"]), Response(b"rate", url=ledger["requests"][1]["url"])])
    campaign = MODULE.execute(ledger, output_root=output, opener=opener)
    assert campaign["status"] == "fetched_pending_contract_extraction"
    assert campaign["attempted_transaction_count"] == 2
    assert campaign["transactions_remaining"] == 0
    assert len(opener.requests) == 2
    assert (output / "fetch_manifest.json").is_file()
    assert (output / "campaign_manifest.json").is_file()
    MODULE.validate_completed_artifacts(output, ledger)
    for request, timeout in opener.requests:
        assert request.get_method() == "GET"
        assert request.get_header("Accept-encoding") is None
        assert "api_key" not in request.full_url
        assert timeout == 30


@pytest.mark.parametrize(
    ("response", "error_code"),
    [
        (Response(b"plain", url=MODULE.EXPECTED_REQUESTS[0]["url"], content_type="text/plain; charset=utf-8"), "not_html"),
        (Response(b"html", url=MODULE.EXPECTED_REQUESTS[0]["url"], content_type="text/html; charset=latin-1"), "invalid_charset"),
        (Response(b"\xff", url=MODULE.EXPECTED_REQUESTS[0]["url"]), "invalid_utf8"),
    ],
)
def test_media_charset_and_utf8_fail_closed(tmp_path: Path, response: Response, error_code: str) -> None:
    path, _, output = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    campaign = MODULE.execute(ledger, output_root=output, opener=Opener([response]))
    fetch = json.loads((output / "fetch_manifest.json").read_text())
    assert campaign["status"] == "blocked"
    assert fetch["requests"][0]["error_code"] == error_code
    assert fetch["retained_document_count"] == 0


@pytest.mark.parametrize("mutation", ["raw_tamper", "extra_file", "manifest_counter"])
def test_completed_artifact_validator_rejects_drift(tmp_path: Path, mutation: str) -> None:
    path, _, output = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    MODULE.execute(
        ledger,
        output_root=output,
        opener=Opener([
            Response(b"auth", url=ledger["requests"][0]["url"]),
            Response(b"rate", url=ledger["requests"][1]["url"]),
        ]),
    )
    if mutation == "raw_tamper":
        (output / "raw/01_openalex_authentication_pricing.html").write_bytes(b"changed")
    elif mutation == "extra_file":
        (output / "extra.txt").write_text("extra")
    else:
        manifest = json.loads((output / "fetch_manifest.json").read_text())
        manifest["retained_document_count"] = 1
        (output / "fetch_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        MODULE.validate_completed_artifacts(output, ledger)


@pytest.mark.parametrize(
    ("response_factory", "error_code"),
    [
        (lambda url: Response(b"compressed", url=url, content_encoding="gzip"), "compressed_response"),
        (lambda url: Response(b"x" * 2_000_001, url=url, include_content_length=False), "body_byte_cap_exceeded"),
    ],
)
def test_compression_and_streamed_cap_block_after_one_dispatch(tmp_path: Path, response_factory, error_code: str) -> None:  # noqa: ANN001
    path, _, output = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    opener = Opener([response_factory(ledger["requests"][0]["url"])])
    campaign = MODULE.execute(ledger, output_root=output, opener=opener)
    fetch = json.loads((output / "fetch_manifest.json").read_text())
    assert campaign["status"] == "blocked"
    assert campaign["attempted_transaction_count"] == 1
    assert fetch["requests"][0]["error_code"] == error_code
    assert len(opener.requests) == 1


def test_redirect_is_counted_and_never_followed(tmp_path: Path) -> None:
    path, _, output = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    headers = Message()
    headers["Location"] = "https://developers.openalex.org/other"
    headers["Content-Type"] = "text/html"
    error = urllib.error.HTTPError(ledger["requests"][0]["url"], 302, "Found", headers, io.BytesIO(b"moved"))
    opener = Opener([error])
    campaign = MODULE.execute(ledger, output_root=output, opener=opener)
    fetch = json.loads((output / "fetch_manifest.json").read_text())
    assert campaign["status"] == "blocked"
    assert campaign["aggregate_received_response_body_bytes"] == 5
    assert fetch["requests"][0]["error_code"] == "redirect_forbidden"
    assert len(opener.requests) == 1


def test_existing_output_and_command_drift_fail_before_dispatch(tmp_path: Path) -> None:
    path, raw, output = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(path, script_path=SCRIPT)
    output.mkdir()
    opener = Opener([])
    with pytest.raises(FileExistsError):
        MODULE.execute(ledger, output_root=output, opener=opener)
    assert opener.requests == []
    raw["worker_command"] = ["wrong"]
    path.write_text(json.dumps(raw))
    drifted = MODULE.validate_ledger(path, script_path=SCRIPT)
    with pytest.raises(MODULE.BASE.FetchContractError, match="argv differs"):
        expected = [MODULE.sys.executable, str(SCRIPT), "--ledger", str(path), "--output-root", str(output)]
        MODULE.validate_command(drifted, argv=expected)
