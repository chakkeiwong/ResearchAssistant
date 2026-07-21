from __future__ import annotations

import json
import http.client
import socket
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from research_assistant.survey import build as survey_build
from research_assistant.survey.mission_state import MissionStateError


TOPIC = "Neural Optimal Transport for generative modeling and inference"
SEED = "arxiv:2201.12220v3"


class FakeResponse:
    def __init__(self, body: bytes, url: str, *, content_length: str | None = None) -> None:
        self.body = body
        self.url = url
        self.headers = {} if content_length is None else {"Content-Length": content_length}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int) -> bytes:
        return self.body[:size]


class FakeOpener:
    def __init__(self, responder):
        self.responder = responder
        self.requests = []

    def open(self, request, timeout: int):
        self.requests.append((request, timeout))
        return self.responder(request)


def _arxiv_body() -> bytes:
    return b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>'


def _openalex_body() -> bytes:
    return b'{"results":[]}'


def _install_fake_opener(monkeypatch: pytest.MonkeyPatch, responder):
    opener = FakeOpener(responder)
    handlers = []

    def build_opener(*values):
        handlers.extend(values)
        return opener

    monkeypatch.setattr(survey_build.urllib.request, "build_opener", build_opener)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("real socket attempted"))
    return opener, handlers


def _strict_collect(sink, *, providers=None, max_records=10, seeds=None):
    return survey_build._collect_public_metadata(
        topic=TOPIC,
        seeds=seeds or [SEED],
        providers=providers or ["arxiv", "openalex"],
        max_records=max_records,
        fetched_at="2026-07-14T00:00:00+00:00",
        _request_outcome_sink=sink,
    )


def test_exact_four_request_topology_no_proxy_and_closed_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    def responder(request):
        body = _arxiv_body() if request.full_url.startswith("https://export.arxiv.org") else _openalex_body()
        return FakeResponse(body, request.full_url)

    opener, handlers = _install_fake_opener(monkeypatch, responder)
    outcomes = []
    collection = _strict_collect(outcomes.append)

    assert len(opener.requests) == 4
    assert [row[0].full_url.split("/", 3)[2] for row in opener.requests] == [
        "export.arxiv.org", "export.arxiv.org", "api.openalex.org", "api.openalex.org"
    ]
    assert all(timeout == 30 for _, timeout in opener.requests)
    assert all(request.get_method() == "GET" for request, _ in opener.requests)
    assert all(request.get_header("User-agent") == survey_build.PUBLIC_METADATA_USER_AGENT for request, _ in opener.requests)
    assert len(outcomes) == 4
    assert [row["request_index"] for row in outcomes] == [1, 2, 3, 4]
    assert [row["status"] for row in outcomes] == ["available"] * 4
    assert [row["normalized_seed_key"] for row in outcomes] == [SEED, None, SEED, None]
    assert [row["topic_query"] for row in outcomes] == [False, True, False, True]
    assert all(row["raw_response_saved"] is False for row in outcomes)
    assert collection["records"] == []
    assert collection["provider_statuses"] == [
        {"provider": "arxiv", "query_kind": "seed_resolution", "normalized_seed_key": SEED, "topic_query": False, "query_cap": 5, "status": "available", "record_count": 0, "raw_response_saved": False},
        {"provider": "arxiv", "query_kind": "topic_search", "normalized_seed_key": None, "topic_query": True, "query_cap": 10, "status": "available", "record_count": 0, "raw_response_saved": False},
        {"provider": "openalex", "query_kind": "seed_resolution", "normalized_seed_key": SEED, "topic_query": False, "query_cap": 5, "status": "available", "record_count": 0, "raw_response_saved": False},
        {"provider": "openalex", "query_kind": "topic_search", "normalized_seed_key": None, "topic_query": True, "query_cap": 10, "status": "available", "record_count": 0, "raw_response_saved": False},
    ]
    assert any(isinstance(handler, survey_build.urllib.request.ProxyHandler) for handler in handlers)
    proxy = next(handler for handler in handlers if isinstance(handler, survey_build.urllib.request.ProxyHandler))
    assert proxy.proxies == {}


def test_proxy_environment_and_inactive_helpers_cannot_change_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.setenv(name, "http://credential@example.invalid:9999")
    for name in ("_resolve_openalex_seed_metadata", "_openalex_cited_by", "_fetch_public_json"):
        monkeypatch.setattr(survey_build, name, lambda *a, **k: pytest.fail(f"inactive helper called: {name}"))
    opener, handlers = _install_fake_opener(
        monkeypatch,
        lambda request: FakeResponse(
            _arxiv_body() if "arxiv" in request.full_url else _openalex_body(), request.full_url
        ),
    )
    outcomes = []
    _strict_collect(outcomes.append)
    assert len(opener.requests) == 4
    assert len(outcomes) == 4
    assert all(
        handler.proxies == {}
        for handler in handlers
        if isinstance(handler, survey_build.urllib.request.ProxyHandler)
    )


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_each_redirect_is_rejected_without_stopping_later_dispatch(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    opener, _ = _install_fake_opener(
        monkeypatch,
        lambda request: (_ for _ in ()).throw(survey_build._M19RedirectRejected(code, request.full_url)),
    )
    outcomes = []
    _strict_collect(outcomes.append)
    assert len(opener.requests) == 4
    assert [row["status"] for row in outcomes] == ["unavailable_redirect_rejected"] * 4
    assert [row["sanitized_error_code"] for row in outcomes] == [f"http_{code}"] * 4
    assert all(row["final_hostname"] in {"export.arxiv.org", "api.openalex.org"} for row in outcomes)


def test_python311_effective_wire_headers_are_closed() -> None:
    captured = []

    class WireResponse:
        reason = "OK"
        headers = {}

    class WireConnection(http.client.HTTPSConnection):
        def _send_output(self, message_body=None, encode_chunked=False):
            captured.extend(self._buffer)
            self._buffer.clear()
            self._state = http.client._CS_IDLE

        def getresponse(self):
            return WireResponse()

    request = urllib.request.Request(
        "https://api.openalex.org/works?search=x",
        headers={"Accept": "application/json", "User-Agent": survey_build.PUBLIC_METADATA_USER_AGENT},
        method="GET",
    )
    request.timeout = 30
    urllib.request.AbstractHTTPHandler().do_open(WireConnection, request)
    lines = [line.decode("latin-1") for line in captured]
    assert lines[0] == "GET /works?search=x HTTP/1.1"
    assert set(lines[1:]) == {
        "Host: api.openalex.org",
        "Accept-Encoding: identity",
        "Accept: application/json",
        f"User-Agent: {survey_build.PUBLIC_METADATA_USER_AGENT}",
        "Connection: close",
    }


@pytest.mark.parametrize(
    ("exception", "status", "error_class", "error_code"),
    [
        (socket.timeout(), "unavailable_timeout", "timeout", "socket_timeout"),
        (urllib.error.URLError(socket.gaierror()), "unavailable_transport_error", "transport", "dns_failure"),
        (urllib.error.URLError(ConnectionRefusedError()), "unavailable_transport_error", "transport", "connection_failure"),
        (urllib.error.HTTPError("https://export.arxiv.org/api/query", 429, "secret", {}, None), "unavailable_http_error", "http", "http_429"),
    ],
)
def test_transport_errors_are_closed_and_sanitized(
    monkeypatch: pytest.MonkeyPatch, exception, status: str, error_class: str, error_code: str
) -> None:
    _install_fake_opener(monkeypatch, lambda request: (_ for _ in ()).throw(exception))
    outcomes = []
    _strict_collect(outcomes.append)

    assert len(outcomes) == 4
    assert outcomes[0]["status"] == status
    assert outcomes[0]["sanitized_error_class"] == error_class
    assert outcomes[0]["sanitized_error_code"] == error_code
    serialized = json.dumps(outcomes)
    assert "secret" not in serialized
    assert TOPIC not in serialized


@pytest.mark.parametrize(
    ("body", "content_length", "status", "code", "accepted", "overflow"),
    [
        (b"x", "2000001", "unavailable_oversized", "content_length_cap_exceeded", 0, 0),
        (b"x" * 2_000_001, None, "unavailable_oversized", "stream_cap_exceeded", 0, 1),
    ],
)
def test_payload_caps_are_exact(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    content_length: str | None,
    status: str,
    code: str,
    accepted: int,
    overflow: int,
) -> None:
    _install_fake_opener(monkeypatch, lambda request: FakeResponse(body, request.full_url, content_length=content_length))
    outcomes = []
    _strict_collect(outcomes.append)
    assert all(row["status"] == status for row in outcomes)
    assert all(row["sanitized_error_code"] == code for row in outcomes)
    assert all(row["accepted_payload_bytes"] == accepted for row in outcomes)
    assert all(row["diagnostic_overflow_bytes"] == overflow for row in outcomes)


def test_malformed_responses_use_provider_compatible_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_opener(monkeypatch, lambda request: FakeResponse(b"not valid", request.full_url))
    outcomes = []
    _strict_collect(outcomes.append)
    assert [row["sanitized_error_code"] for row in outcomes] == [
        "malformed_xml", "malformed_xml", "malformed_json", "malformed_json"
    ]


def test_unexpected_parser_failure_is_boundary_error_not_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_opener(
        monkeypatch,
        lambda request: FakeResponse(_arxiv_body(), request.full_url),
    )
    monkeypatch.setattr(
        survey_build,
        "_parse_arxiv_metadata_records",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("private parser detail")),
    )
    outcomes = []

    with pytest.raises(MissionStateError, match="parser failed outside") as exc_info:
        _strict_collect(outcomes.append)

    assert exc_info.value.code == "m19_unexpected_parser_failure"
    assert "private parser detail" not in str(exc_info.value)
    assert outcomes == []


def test_final_url_drift_is_boundary_error_not_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_opener(monkeypatch, lambda request: FakeResponse(_arxiv_body(), "https://example.com/wrong"))
    with pytest.raises(MissionStateError, match="response URL drifted"):
        _strict_collect(lambda row: None)


def test_invalid_route_emits_blocked_row_before_boundary_error() -> None:
    rows = []
    with pytest.raises(MissionStateError, match="route contract rejected"):
        survey_build._m19_request(
            provider="openalex", query_kind="topic_search", normalized_seed_key=None,
            topic_query=True, request_index=4,
            url="http://api.openalex.org/works?search=x", path="/works",
            query_keys=["search"], request_binding_sha256="a" * 64,
            accept="application/json", parser=lambda body: [], record_cap=10,
            sink=rows.append,
        )
    assert len(rows) == 1
    assert rows[0]["status"] == "blocked_invalid_request"
    assert rows[0]["sanitized_error_code"] == "invalid_scheme"


def test_request_binding_and_query_key_drift_are_blocked_before_opener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        survey_build.urllib.request,
        "build_opener",
        lambda *args: pytest.fail("opener created for invalid request"),
    )
    rows = []
    route = {
        "request_index": 4, "provider": "openalex", "query_kind": "topic_search",
        "method": "GET", "scheme": "https", "hostname": "api.openalex.org", "port": 443,
        "path": "/works",
        "query": {"per-page": "10", "search": TOPIC, "select": survey_build.PUBLIC_METADATA_OPENALEX_SELECT},
        "headers": {"Accept": "application/json", "User-Agent": survey_build.PUBLIC_METADATA_USER_AGENT},
    }
    binding = survey_build._m19_route_binding(route)
    changed_url = (
        "https://api.openalex.org/works?per-page=10&search=changed&select="
        + survey_build.urllib.parse.quote(survey_build.PUBLIC_METADATA_OPENALEX_SELECT)
    )
    with pytest.raises(MissionStateError):
        survey_build._m19_request(
            provider="openalex", query_kind="topic_search", normalized_seed_key=None,
            topic_query=True, request_index=4, url=changed_url, path="/works",
            query_keys=list(route["query"]), request_binding_sha256=binding,
            accept="application/json", parser=lambda body: [], record_cap=10,
            sink=rows.append,
        )
    assert rows[-1]["sanitized_error_code"] == "request_binding_mismatch"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seeds": ["arxiv:9999.00001"]},
        {"providers": ["arxiv"]},
        {"providers": ["openalex", "arxiv"]},
        {"max_records": 11},
    ],
)
def test_strict_scope_rejects_topology_drift(kwargs) -> None:
    with pytest.raises(MissionStateError, match="scope is frozen"):
        _strict_collect(lambda row: None, **kwargs)


def test_sink_failure_propagates_without_unavailable_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_opener(monkeypatch, lambda request: FakeResponse(_arxiv_body(), request.full_url))

    def fail_sink(row):
        raise MissionStateError("sink_failed", "closed sink failed")

    with pytest.raises(MissionStateError, match="outcome sink failed"):
        _strict_collect(fail_sink)


def test_sink_failure_on_early_oversize_is_boundary_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_opener(
        monkeypatch,
        lambda request: FakeResponse(b"", request.full_url, content_length="2000001"),
    )

    def fail_sink(row):
        raise RuntimeError("private sink detail")

    with pytest.raises(MissionStateError, match="outcome sink failed"):
        _strict_collect(fail_sink)


def test_full_build_strict_mode_propagates_boundary_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        survey_build,
        "_collect_public_metadata_m19",
        lambda **kwargs: (_ for _ in ()).throw(MissionStateError("ledger_failed", "ledger failed")),
    )
    with pytest.raises(MissionStateError, match="ledger failed"):
        survey_build.build_survey_evidence_packet(
            topic=TOPIC,
            seeds=[SEED],
            output_dir=tmp_path / "public_metadata",
            mode="public-metadata",
            public_metadata_providers=["arxiv", "openalex"],
            max_records=10,
            _request_outcome_sink=lambda row: None,
        )
