from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20_official_provider_contract_fetch.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20_docs_fetch", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        url: str,
        status: int = 200,
        content_type: str = "text/html",
        content_encoding: str | None = None,
        include_content_length: bool = True,
    ) -> None:
        self._body = body
        self._offset = 0
        self._url = url
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if include_content_length:
            self.headers["Content-Length"] = str(len(body))
        if content_encoding is not None:
            self.headers["Content-Encoding"] = content_encoding

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._body) - self._offset
        chunk = self._body[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url

    def close(self) -> None:
        pass


class PartialReadResponse(FakeResponse):
    def __init__(self, body: bytes, *, url: str, error: Exception) -> None:
        super().__init__(body, url=url, include_content_length=False)
        self.error = error
        self.read_count = 0

    def read(self, size: int = -1) -> bytes:
        self.read_count += 1
        if self.read_count == 1:
            return super().read(min(size, 3))
        raise self.error


class FakeOpener:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout: int):  # noqa: ANN001, ANN201
        self.requests.append((request, timeout))
        return self.responses.pop(0)


def _requests() -> list[dict]:
    return [dict(row) for row in MODULE.EXPECTED_REQUESTS]


def _ledger(tmp_path: Path) -> tuple[Path, dict]:
    output_root = tmp_path / "out"
    ledger_path = tmp_path / "prefetch_ledger.json"
    ledger = {
        "schema_version": MODULE.SCHEMA,
        "status": "reviewed_ready",
        "script_path": str(SCRIPT),
        "script_sha256": MODULE.sha256_path(SCRIPT),
        "command": [
            MODULE.sys.executable,
            str(SCRIPT),
            "--ledger",
            str(ledger_path),
            "--output-root",
            str(output_root),
        ],
        "transaction_cap": MODULE.TRANSACTION_CAP,
        "per_response_body_byte_cap": MODULE.PER_RESPONSE_CAP,
        "aggregate_body_byte_cap": MODULE.TOTAL_CAP,
        "diagnostic_overflow_byte_cap": 1,
        "timeout_seconds": MODULE.TIMEOUT_SECONDS,
        "redirect_policy": "automatic_redirects_disabled_any_3xx_blocks_phase",
        "proxy_policy": "explicit_empty_proxy_handler",
        "compression_policy": "no_accept_encoding_and_reject_non_identity_content_encoding",
        "requests": _requests(),
    }
    ledger_path.write_text(json.dumps(ledger))
    return ledger_path, ledger


def test_validate_prefetch_ledger_rejects_url_and_script_drift(tmp_path: Path) -> None:
    ledger_path, ledger = _ledger(tmp_path)
    validated = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    assert len(validated["requests"]) == 6

    ledger["requests"][0]["url"] = "https://api.openalex.org/works"
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(MODULE.FetchContractError, match="outside"):
        MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)

    ledger["requests"] = _requests()
    ledger["requests"][0]["url"] = "https://info.arxiv.org/other.html"
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(MODULE.FetchContractError, match="six reviewed rows"):
        MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)

    ledger["requests"] = _requests()
    ledger["script_sha256"] = "0" * 64
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(MODULE.FetchContractError, match="SHA-256"):
        MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)


def test_fetch_retains_six_exact_uncompressed_documents(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    responses = [FakeResponse(f"doc-{index}".encode(), url=row["url"]) for index, row in enumerate(ledger["requests"])]
    opener = FakeOpener(responses)
    timestamps = iter(f"2026-07-14T00:00:0{index}Z" for index in range(1, 7))
    manifest = MODULE.fetch_documents(
        ledger,
        output_root=tmp_path / "result",
        opener=opener,
        timestamp=lambda: next(timestamps),
    )
    assert manifest["status"] == "fetched_pending_contract_extraction"
    assert manifest["attempted_transaction_count"] == 6
    assert manifest["retained_document_count"] == 6
    assert len(opener.requests) == 6
    cumulative_bytes = 0
    for index, row in enumerate(manifest["requests"], start=1):
        cumulative_bytes += row["received_response_body_bytes"]
        assert row["retrieval_timestamp_utc"] == f"2026-07-14T00:00:0{index}Z"
        assert row["cumulative_attempted_transaction_count"] == index
        assert row["cumulative_received_response_body_bytes"] == cumulative_bytes
        assert row["cumulative_diagnostic_overflow_bytes"] == 0
    for request, timeout in opener.requests:
        assert request.get_method() == "GET"
        assert request.get_header("Accept") == MODULE.ACCEPT
        assert request.get_header("User-agent") == MODULE.USER_AGENT
        assert request.get_header("Accept-encoding") is None
        assert timeout == 30


@pytest.mark.parametrize(
    ("response", "error_code"),
    [
        (lambda url: FakeResponse(b"compressed", url=url, content_encoding="gzip"), "compressed_response"),
        (lambda url: FakeResponse(b"ok", url=url + "/redirected"), "final_url_mismatch"),
        (
            lambda url: FakeResponse(
                b"x" * (MODULE.PER_RESPONSE_CAP + 1),
                url=url,
                include_content_length=False,
            ),
            "body_byte_cap_exceeded",
        ),
    ],
)
def test_fetch_fails_closed_on_contract_drift(tmp_path: Path, response, error_code: str) -> None:  # noqa: ANN001
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    responses = [response(ledger["requests"][0]["url"])] + [
        FakeResponse(b"ok", url=row["url"])
        for row in ledger["requests"][1:]
    ]
    manifest = MODULE.fetch_documents(ledger, output_root=tmp_path / "result", opener=FakeOpener(responses))
    assert manifest["status"] == "blocked"
    assert manifest["requests"][0]["error_code"] == error_code
    assert manifest["requests"][0]["retained_bytes"] == 0
    assert manifest["attempted_transaction_count"] == 1
    if error_code == "body_byte_cap_exceeded":
        assert manifest["requests"][0]["received_response_body_bytes"] == MODULE.PER_RESPONSE_CAP
        assert manifest["requests"][0]["diagnostic_overflow_bytes"] == 1
        assert manifest["aggregate_received_response_body_bytes"] == MODULE.PER_RESPONSE_CAP


def test_no_redirect_handler_never_follows() -> None:
    handler = MODULE.NoRedirectHandler()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://example.test") is None


def test_http_redirect_body_is_counted_closed_and_stops(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    headers = Message()
    headers["Location"] = "https://example.test/moved"
    headers["Content-Type"] = "text/html"
    error = urllib.error.HTTPError(
        ledger["requests"][0]["url"],
        302,
        "Found",
        headers,
        io.BytesIO(b"moved"),
    )

    class RedirectOpener:
        def open(self, request, timeout):  # noqa: ANN001, ANN201
            raise error

    manifest = MODULE.fetch_documents(ledger, output_root=tmp_path / "result", opener=RedirectOpener())
    assert manifest["status"] == "blocked"
    assert manifest["attempted_transaction_count"] == 1
    assert manifest["aggregate_received_response_body_bytes"] == 5
    assert manifest["requests"][0]["outcome"] == "blocked_redirect"
    assert manifest["requests"][0]["location"] == "https://example.test/moved"
    assert error.fp.closed
    assert manifest["requests"][0]["cumulative_attempted_transaction_count"] == 1
    assert manifest["requests"][0]["cumulative_received_response_body_bytes"] == 5
    assert (tmp_path / "result" / "fetch_manifest.json").is_file()


@pytest.mark.parametrize(
    ("error", "error_code"),
    [(TimeoutError(), "read_timeout"), (OSError(), "read_io_error")],
)
def test_partial_read_failure_counts_bytes_and_writes_manifest(
    tmp_path: Path,
    error: Exception,
    error_code: str,
) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    response = PartialReadResponse(b"abcdef", url=ledger["requests"][0]["url"], error=error)
    manifest = MODULE.fetch_documents(
        ledger,
        output_root=tmp_path / "result",
        opener=FakeOpener([response]),
    )
    assert manifest["status"] == "blocked"
    assert manifest["aggregate_received_response_body_bytes"] == 3
    assert manifest["requests"][0]["received_response_body_bytes"] == 3
    assert manifest["requests"][0]["cumulative_received_response_body_bytes"] == 3
    assert manifest["requests"][0]["error_code"] == error_code
    assert (tmp_path / "result" / "fetch_manifest.json").is_file()


def test_aggregate_cap_exhaustion_is_counted_and_stops(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    monkeypatch.setattr(MODULE, "PER_RESPONSE_CAP", 5)
    monkeypatch.setattr(MODULE, "TOTAL_CAP", 8)
    responses = [
        FakeResponse(b"12345", url=ledger["requests"][0]["url"], include_content_length=False),
        FakeResponse(b"6789", url=ledger["requests"][1]["url"], include_content_length=False),
    ]
    manifest = MODULE.fetch_documents(
        ledger,
        output_root=tmp_path / "result",
        opener=FakeOpener(responses),
    )
    assert manifest["status"] == "blocked"
    assert manifest["attempted_transaction_count"] == 2
    assert manifest["aggregate_received_response_body_bytes"] == 8
    assert manifest["aggregate_diagnostic_overflow_bytes"] == 1
    assert manifest["requests"][1]["cumulative_attempted_transaction_count"] == 2
    assert manifest["requests"][1]["cumulative_received_response_body_bytes"] == 8
    assert manifest["requests"][1]["cumulative_diagnostic_overflow_bytes"] == 1
    assert manifest["requests"][1]["error_code"] == "body_byte_cap_exceeded"


def test_existing_output_root_fails_before_dispatch(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_prefetch_ledger(ledger_path, script_path=SCRIPT)
    output_root = tmp_path / "result"
    output_root.mkdir()
    opener = FakeOpener([])
    with pytest.raises(FileExistsError):
        MODULE.fetch_documents(ledger, output_root=output_root, opener=opener)
    assert opener.requests == []


def test_real_opener_is_built_with_empty_proxy_and_no_redirect_handlers(monkeypatch) -> None:  # noqa: ANN001
    captured = []

    def fake_build_opener(*handlers):  # noqa: ANN001, ANN202
        captured.extend(handlers)
        return object()

    monkeypatch.setattr(MODULE.urllib.request, "build_opener", fake_build_opener)
    opener = MODULE.build_opener()
    assert opener is not None
    proxy_handlers = [handler for handler in captured if type(handler) is urllib.request.ProxyHandler]
    redirect_handlers = [handler for handler in captured if isinstance(handler, MODULE.NoRedirectHandler)]
    default_redirect_handlers = [handler for handler in captured if type(handler) is urllib.request.HTTPRedirectHandler]
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}
    assert len(redirect_handlers) == 1
    assert default_redirect_handlers == []
