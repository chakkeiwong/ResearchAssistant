from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA = "ra-literature-survey-m20-official-doc-prefetch-v1"
MANIFEST_SCHEMA = "ra-literature-survey-m20-official-doc-fetch-manifest-v1"
PER_RESPONSE_CAP = 2_000_000
TOTAL_CAP = 8_000_000
TRANSACTION_CAP = 6
TIMEOUT_SECONDS = 30
CHUNK_SIZE = 65_536
USER_AGENT = "research-assistant-m20/0.1 (official-contract-snapshot)"
ACCEPT = "text/html, text/plain;q=0.9"
ALLOWED_HOSTS = {"info.arxiv.org", "docs.openalex.org"}
EXPECTED_REQUESTS = [
    {
        "request_index": 1,
        "document_id": "arxiv_api_manual",
        "provider": "arxiv",
        "url": "https://info.arxiv.org/help/api/user-manual.html",
        "semantic_role": "query_parameters_atom_fields_and_rate_guidance",
        "requirement": "indispensable",
    },
    {
        "request_index": 2,
        "document_id": "openalex_works",
        "provider": "openalex",
        "url": "https://docs.openalex.org/api-entities/works",
        "semantic_role": "single_work_and_work_fields",
        "requirement": "indispensable",
    },
    {
        "request_index": 3,
        "document_id": "openalex_search",
        "provider": "openalex",
        "url": "https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/search-entities",
        "semantic_role": "works_search",
        "requirement": "indispensable",
    },
    {
        "request_index": 4,
        "document_id": "openalex_filter",
        "provider": "openalex",
        "url": "https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/filter-entity-lists",
        "semantic_role": "forward_cites_filter",
        "requirement": "indispensable",
    },
    {
        "request_index": 5,
        "document_id": "openalex_select",
        "provider": "openalex",
        "url": "https://docs.openalex.org/how-to-use-the-api/get-single-entities/select-fields",
        "semantic_role": "response_field_selection_optimization",
        "requirement": "optional",
    },
    {
        "request_index": 6,
        "document_id": "openalex_paging",
        "provider": "openalex",
        "url": "https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/paging",
        "semantic_role": "pagination_caps_and_continuation",
        "requirement": "indispensable",
    },
]


class FetchContractError(RuntimeError):
    def __init__(self, code: str, message: str, *, observed_body_bytes: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.observed_body_bytes = observed_body_bytes


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_exact_dict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise FetchContractError("invalid_ledger", f"{label} keys are not exact")
    return dict(value)


def validate_prefetch_ledger(path: Path, *, script_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchContractError("invalid_ledger", "prefetch ledger is unreadable") from exc
    ledger = _require_exact_dict(
        value,
        {
            "schema_version",
            "status",
            "script_path",
            "script_sha256",
            "command",
            "transaction_cap",
            "per_response_body_byte_cap",
            "aggregate_body_byte_cap",
            "diagnostic_overflow_byte_cap",
            "timeout_seconds",
            "redirect_policy",
            "proxy_policy",
            "compression_policy",
            "requests",
        },
        "prefetch ledger",
    )
    if ledger["schema_version"] != SCHEMA or ledger["status"] != "reviewed_ready":
        raise FetchContractError("invalid_ledger", "prefetch ledger status or schema is invalid")
    expected_script = script_path.resolve()
    if Path(ledger["script_path"]).resolve() != expected_script:
        raise FetchContractError("script_mismatch", "prefetch ledger script path differs")
    if ledger["script_sha256"] != sha256_path(expected_script):
        raise FetchContractError("script_mismatch", "fetch script SHA-256 differs from the reviewed ledger")
    fixed = {
        "transaction_cap": TRANSACTION_CAP,
        "per_response_body_byte_cap": PER_RESPONSE_CAP,
        "aggregate_body_byte_cap": TOTAL_CAP,
        "diagnostic_overflow_byte_cap": 1,
        "timeout_seconds": TIMEOUT_SECONDS,
        "redirect_policy": "automatic_redirects_disabled_any_3xx_blocks_phase",
        "proxy_policy": "explicit_empty_proxy_handler",
        "compression_policy": "no_accept_encoding_and_reject_non_identity_content_encoding",
    }
    if any(ledger[key] != expected for key, expected in fixed.items()):
        raise FetchContractError("invalid_ledger", "prefetch ledger caps or policies differ")
    if not isinstance(ledger["command"], list) or not all(isinstance(item, str) for item in ledger["command"]):
        raise FetchContractError("invalid_ledger", "prefetch command must be an argv list")
    requests = ledger["requests"]
    if not isinstance(requests, list) or len(requests) != TRANSACTION_CAP:
        raise FetchContractError("invalid_ledger", "prefetch ledger must contain exactly six requests")
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, value_row in enumerate(requests, start=1):
        row = _require_exact_dict(
            value_row,
            {"request_index", "document_id", "provider", "url", "semantic_role", "requirement"},
            f"requests[{index - 1}]",
        )
        if row["request_index"] != index or row["requirement"] not in {"indispensable", "optional"}:
            raise FetchContractError("invalid_ledger", "request ordering or requirement is invalid")
        if not all(isinstance(row[key], str) and row[key] for key in ("document_id", "provider", "url", "semantic_role")):
            raise FetchContractError("invalid_ledger", "request string field is invalid")
        parsed = urllib.parse.urlsplit(row["url"])
        if (
            parsed.scheme != "https"
            or parsed.hostname not in ALLOWED_HOSTS
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise FetchContractError("invalid_url", "request URL is outside the exact documentation boundary")
        if row["document_id"] in seen_ids or row["url"] in seen_urls:
            raise FetchContractError("invalid_ledger", "request IDs and URLs must be unique")
        seen_ids.add(row["document_id"])
        seen_urls.add(row["url"])
    if canonical_json_bytes(requests) != canonical_json_bytes(EXPECTED_REQUESTS):
        raise FetchContractError("invalid_ledger", "prefetch requests differ from the six reviewed rows")
    return {**ledger, "requests": [dict(row) for row in requests]}


def build_opener() -> urllib.request.OpenerDirector:
    context = ssl.create_default_context()
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
        urllib.request.HTTPSHandler(context=context),
    )


def _response_status(response: Any) -> int:
    status = getattr(response, "status", None)
    if type(status) is not int:
        status = response.getcode()
    if type(status) is not int:
        raise FetchContractError("invalid_response", "response status is absent")
    return status


def _header(response: Any, name: str) -> str | None:
    value = response.headers.get(name)
    return value.strip() if isinstance(value, str) else None


def _read_response_body(
    response: Any,
    *,
    aggregate_received: int,
) -> tuple[bytes, int]:
    body = bytearray()
    received = 0
    while True:
        remaining_response = PER_RESPONSE_CAP - received
        remaining_total = TOTAL_CAP - aggregate_received - received
        if remaining_response < 0 or remaining_total < 0:
            raise FetchContractError("body_byte_cap_exceeded", "response-body byte cap is already exhausted")
        read_cap = min(CHUNK_SIZE, remaining_response + 1, remaining_total + 1)
        if read_cap <= 0:
            raise FetchContractError("body_byte_cap_exceeded", "response-body byte cap is exhausted")
        try:
            chunk = response.read(read_cap)
        except TimeoutError as exc:
            raise FetchContractError(
                "read_timeout",
                "response body read timed out",
                observed_body_bytes=received,
            ) from exc
        except urllib.error.URLError as exc:
            raise FetchContractError(
                "read_transport_error",
                "response body read failed",
                observed_body_bytes=received,
            ) from exc
        except OSError as exc:
            raise FetchContractError(
                "read_io_error",
                "response body read failed",
                observed_body_bytes=received,
            ) from exc
        if not chunk:
            return bytes(body), received
        if not isinstance(chunk, bytes):
            raise FetchContractError(
                "invalid_response",
                "response body is not bytes",
                observed_body_bytes=received,
            )
        received += len(chunk)
        if received > PER_RESPONSE_CAP or aggregate_received + received > TOTAL_CAP:
            raise FetchContractError(
                "body_byte_cap_exceeded",
                "response exceeded the response-body byte cap",
                observed_body_bytes=received,
            )
        body.extend(chunk)


def _manifest_row_base(request_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_index": request_row["request_index"],
        "document_id": request_row["document_id"],
        "provider": request_row["provider"],
        "requested_url": request_row["url"],
        "final_url": None,
        "status_code": None,
        "outcome": None,
        "location": None,
        "content_type": None,
        "content_encoding": None,
        "received_response_body_bytes": 0,
        "diagnostic_overflow_bytes": 0,
        "retained_bytes": 0,
        "sha256": None,
        "relative_path": None,
        "elapsed_seconds": None,
        "retrieval_timestamp_utc": None,
        "cumulative_attempted_transaction_count": None,
        "cumulative_received_response_body_bytes": None,
        "cumulative_diagnostic_overflow_bytes": None,
        "error_code": None,
    }


def _account_read_failure(row: dict[str, Any], exc: FetchContractError) -> int:
    overflow = int(exc.code == "body_byte_cap_exceeded" and exc.observed_body_bytes > 0)
    accepted = exc.observed_body_bytes - overflow
    row["received_response_body_bytes"] = accepted
    row["diagnostic_overflow_bytes"] = overflow
    return accepted


def fetch_documents(
    ledger: dict[str, Any],
    *,
    output_root: Path,
    opener: Any,
    clock: Callable[[], float] = time.monotonic,
    timestamp: Callable[[], str] = utc_timestamp,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=False)
    raw_root = output_root / "raw"
    raw_root.mkdir()
    rows: list[dict[str, Any]] = []
    aggregate_received = 0
    phase_blocked = False

    for request_row in ledger["requests"]:
        row = _manifest_row_base(request_row)
        started = clock()
        request = urllib.request.Request(
            request_row["url"],
            method="GET",
            headers={"Accept": ACCEPT, "User-Agent": USER_AGENT},
        )
        response = None
        try:
            response = opener.open(request, timeout=TIMEOUT_SECONDS)
            status = _response_status(response)
            row["status_code"] = status
            row["final_url"] = response.geturl()
            row["content_type"] = _header(response, "Content-Type")
            row["content_encoding"] = _header(response, "Content-Encoding")
            if row["final_url"] != request_row["url"]:
                raise FetchContractError("final_url_mismatch", "response final URL differs without an allowed redirect")
            if not 200 <= status < 300:
                raise FetchContractError("http_status", "documentation response is not successful")
            if row["content_encoding"] not in {None, "", "identity"}:
                raise FetchContractError("compressed_response", "compressed documentation response is forbidden")
            media_type = (row["content_type"] or "").split(";", 1)[0].strip().casefold()
            if media_type not in {"text/html", "text/plain"}:
                raise FetchContractError("unexpected_content_type", "documentation response content type is not allowed")
            content_length = _header(response, "Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise FetchContractError("invalid_content_length", "Content-Length is invalid") from exc
                if declared_length < 0 or declared_length > PER_RESPONSE_CAP or aggregate_received + declared_length > TOTAL_CAP:
                    raise FetchContractError("body_byte_cap_exceeded", "declared body length exceeds a cap")
            body, received = _read_response_body(response, aggregate_received=aggregate_received)
            aggregate_received += received
            row["received_response_body_bytes"] = received
            if not body:
                raise FetchContractError("empty_body", "documentation response body is empty")
            suffix = ".html" if "html" in (row["content_type"] or "").casefold() else ".txt"
            relative_path = Path("raw") / f"{request_row['request_index']:02d}_{request_row['document_id']}{suffix}"
            destination = output_root / relative_path
            destination.write_bytes(body)
            row["outcome"] = "retained"
            row["retained_bytes"] = len(body)
            row["sha256"] = sha256_bytes(body)
            row["relative_path"] = relative_path.as_posix()
        except urllib.error.HTTPError as exc:
            response = exc
            row["status_code"] = exc.code
            row["final_url"] = exc.geturl()
            row["location"] = exc.headers.get("Location")
            row["content_type"] = exc.headers.get("Content-Type")
            row["content_encoding"] = exc.headers.get("Content-Encoding")
            try:
                _, received = _read_response_body(exc, aggregate_received=aggregate_received)
                aggregate_received += received
                row["received_response_body_bytes"] = received
                if 300 <= exc.code < 400:
                    row["outcome"] = "blocked_redirect"
                    row["error_code"] = "redirect_forbidden"
                else:
                    row["outcome"] = "blocked_http_error"
                    row["error_code"] = f"http_{exc.code}"
            except FetchContractError as body_exc:
                aggregate_received += _account_read_failure(row, body_exc)
                row["outcome"] = "blocked_contract_error"
                row["error_code"] = body_exc.code
            phase_blocked = True
        except (urllib.error.URLError, TimeoutError) as exc:
            row["outcome"] = "blocked_transport_error"
            row["error_code"] = "timeout" if isinstance(exc, TimeoutError) else "transport_error"
            phase_blocked = True
        except FetchContractError as exc:
            aggregate_received += _account_read_failure(row, exc)
            row["outcome"] = "blocked_contract_error"
            row["error_code"] = exc.code
            phase_blocked = True
        except Exception:
            row["outcome"] = "blocked_internal_error"
            row["error_code"] = "unexpected_fetch_error"
            phase_blocked = True
        finally:
            if response is not None:
                try:
                    response.close()
                except OSError:
                    row["outcome"] = "blocked_contract_error"
                    row["error_code"] = "response_close_error"
                    phase_blocked = True
            row["elapsed_seconds"] = round(max(0.0, clock() - started), 6)
            row["retrieval_timestamp_utc"] = timestamp()
            row["cumulative_attempted_transaction_count"] = len(rows) + 1
            row["cumulative_received_response_body_bytes"] = aggregate_received
            row["cumulative_diagnostic_overflow_bytes"] = (
                sum(prior["diagnostic_overflow_bytes"] for prior in rows)
                + row["diagnostic_overflow_bytes"]
            )
            rows.append(row)
        if phase_blocked:
            break

    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "status": "blocked" if phase_blocked else "fetched_pending_contract_extraction",
        "transaction_cap": TRANSACTION_CAP,
        "attempted_transaction_count": len(rows),
        "per_response_body_byte_cap": PER_RESPONSE_CAP,
        "aggregate_body_byte_cap": TOTAL_CAP,
        "diagnostic_overflow_byte_cap": 1,
        "aggregate_received_response_body_bytes": aggregate_received,
        "aggregate_diagnostic_overflow_bytes": sum(row["diagnostic_overflow_bytes"] for row in rows),
        "retained_document_count": sum(row["outcome"] == "retained" for row in rows),
        "requests": rows,
    }
    (output_root / "fetch_manifest.json").write_bytes(pretty_json_bytes(manifest))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    script_path = Path(__file__).resolve()
    ledger = validate_prefetch_ledger(args.ledger, script_path=script_path)
    expected_command = [
        sys.executable,
        str(script_path),
        "--ledger",
        str(args.ledger),
        "--output-root",
        str(args.output_root),
    ]
    if ledger["command"] != expected_command:
        raise FetchContractError("command_mismatch", "executed argv differs from the reviewed command")
    for name in list(os.environ):
        if name.casefold() in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}:
            os.environ.pop(name, None)
    manifest = fetch_documents(ledger, output_root=args.output_root, opener=build_opener())
    print(json.dumps({
        "status": manifest["status"],
        "attempted_transaction_count": manifest["attempted_transaction_count"],
        "aggregate_received_response_body_bytes": manifest["aggregate_received_response_body_bytes"],
        "fetch_manifest": str(args.output_root / "fetch_manifest.json"),
    }, sort_keys=True))
    return 0 if manifest["status"] == "fetched_pending_contract_extraction" else 2


if __name__ == "__main__":
    raise SystemExit(main())
