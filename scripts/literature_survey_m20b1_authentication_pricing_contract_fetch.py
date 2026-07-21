from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any


BASE_SCRIPT = Path(__file__).with_name("literature_survey_m20_official_provider_contract_fetch.py").resolve()
BASE_SPEC = importlib.util.spec_from_file_location("m20b1_official_docs_base", BASE_SCRIPT)
if BASE_SPEC is None or BASE_SPEC.loader is None:
    raise RuntimeError("cannot load the reviewed documentation fetch primitive")
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)
BASE_READ_RESPONSE_BODY = BASE._read_response_body
SUPERVISOR_SCRIPT = Path(__file__).with_name("literature_survey_m20b1_authentication_pricing_contract_supervisor.py").resolve()

SCHEMA = "ra-literature-survey-m20b1-authentication-pricing-prefetch-v1"
CAMPAIGN_SCHEMA = "ra-literature-survey-m20b1-authentication-pricing-campaign-v1"
TRANSACTION_CAP = 2
PER_RESPONSE_CAP = 2_000_000
TOTAL_CAP = 4_000_000
TIMEOUT_SECONDS = 30
WALL_TIME_CAP_SECONDS = 90
ALLOWED_HOST = "developers.openalex.org"
REPO_ROOT = Path(__file__).resolve().parents[1]
T6_ROOT = (REPO_ROOT / "docs/validation/literature_survey_m20_openalex_list_works_operation_2026-07-14").resolve()
EXPECTED_REQUESTS = [
    {
        "request_index": 1,
        "document_id": "openalex_authentication_pricing",
        "provider": "openalex",
        "url": "https://developers.openalex.org/api-reference/authentication",
        "semantic_role": "authentication_key_placement_pricing_and_credits",
        "requirement": "indispensable",
    },
    {
        "request_index": 2,
        "document_id": "openalex_rate_limit_status",
        "provider": "openalex",
        "url": "https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status",
        "semantic_role": "rate_limit_and_remaining_budget_semantics",
        "requirement": "indispensable",
    },
]
PREDECESSORS = (
    (
        "m20a_close",
        REPO_ROOT / "docs/plans/literature_survey_north_star_m20a_close_record_2026-07-14.md",
        "92c1270474b1c4b786e5232c396f131fee5675198747981a2cdec12f45efc560",
    ),
    (
        "m20b0_result",
        REPO_ROOT / "docs/plans/literature_survey_north_star_m20b0_decision_setup_result_2026-07-14.md",
        "29e22f2bb99ced3a037afcf025cfcb47a464e0560eb20ce71714ae9539549a74",
    ),
    (
        "m20b0_review",
        REPO_ROOT / "docs/reviews/literature_survey_m20b0_decision_setup_and_m20b1_draft_review_verdict_2026-07-14.md",
        "3085b45ab1c6d8f08d0c985c1e52d18a300807eb3f84d6760de4a039e9fccbc4",
    ),
    (
        "m20a_t6_body",
        T6_ROOT / "raw/01_openalex_list_works_operation.html",
        "8f9f34e2e8a3b1772c1a8159d3a3190d30213deb8ca7c95d324947ab69a4f852",
    ),
    (
        "m20a_t6_route_decision",
        T6_ROOT / "route_decision.json",
        "f836edc5ebea48b4968a3daf63200fc7fe2a0ec3380908d79f055c4f682199d8",
    ),
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_dict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise BASE.FetchContractError("invalid_ledger", f"{label} keys are not exact")
    return dict(value)


def _validate_predecessors() -> None:
    for name, path, expected_digest in PREDECESSORS:
        try:
            observed = sha256_path(path)
        except OSError as exc:
            raise BASE.FetchContractError("prior_evidence_mismatch", f"{name} is unreadable") from exc
        if observed != expected_digest or not path.is_file() or path.is_symlink():
            raise BASE.FetchContractError("prior_evidence_mismatch", f"{name} identity differs")
    body = (T6_ROOT / "raw/01_openalex_list_works_operation.html").read_bytes()
    required_anchors = (
        b'href="/api-reference/authentication"',
        b'href="/api-reference/rate-limits/check-rate-limit-status"',
    )
    if any(anchor not in body for anchor in required_anchors):
        raise BASE.FetchContractError("prior_evidence_mismatch", "official authentication/rate-limit links are absent")


def validate_ledger(path: Path, *, script_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BASE.FetchContractError("invalid_ledger", "M20B1 prefetch ledger is unreadable") from exc
    predecessor_keys = {f"{name}_{suffix}" for name, _, _ in PREDECESSORS for suffix in ("path", "sha256")}
    ledger = _exact_dict(
        value,
        {
            "schema_version",
            "status",
            "campaign_id",
            "script_path",
            "script_sha256",
            "supervisor_path",
            "supervisor_sha256",
            "base_script_path",
            "base_script_sha256",
            "command",
            "worker_command",
            "transaction_cap",
            "per_response_body_byte_cap",
            "aggregate_body_byte_cap",
            "diagnostic_overflow_byte_cap",
            "timeout_seconds",
            "wall_time_cap_seconds",
            "redirect_policy",
            "proxy_policy",
            "compression_policy",
            "requests",
            *predecessor_keys,
        },
        "M20B1 prefetch ledger",
    )
    if (
        ledger["schema_version"] != SCHEMA
        or ledger["status"] != "reviewed_ready"
        or ledger["campaign_id"] != "literature-survey-m20b1-auth-pricing-20260714-v1"
    ):
        raise BASE.FetchContractError("invalid_ledger", "M20B1 schema, status, or campaign differs")
    if Path(ledger["script_path"]).resolve() != script_path.resolve() or ledger["script_sha256"] != sha256_path(script_path):
        raise BASE.FetchContractError("script_mismatch", "M20B1 script path or SHA-256 differs")
    if Path(ledger["base_script_path"]).resolve() != BASE_SCRIPT or ledger["base_script_sha256"] != sha256_path(BASE_SCRIPT):
        raise BASE.FetchContractError("script_mismatch", "base fetch primitive path or SHA-256 differs")
    if (
        Path(ledger["supervisor_path"]).resolve() != SUPERVISOR_SCRIPT
        or ledger["supervisor_sha256"] != sha256_path(SUPERVISOR_SCRIPT)
    ):
        raise BASE.FetchContractError("script_mismatch", "M20B1 supervisor path or SHA-256 differs")
    if any(
        Path(ledger[f"{name}_path"]).resolve() != predecessor.resolve()
        or ledger[f"{name}_sha256"] != digest
        for name, predecessor, digest in PREDECESSORS
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "M20B1 predecessor bindings differ")
    _validate_predecessors()
    fixed = {
        "transaction_cap": TRANSACTION_CAP,
        "per_response_body_byte_cap": PER_RESPONSE_CAP,
        "aggregate_body_byte_cap": TOTAL_CAP,
        "diagnostic_overflow_byte_cap": 1,
        "timeout_seconds": TIMEOUT_SECONDS,
        "wall_time_cap_seconds": WALL_TIME_CAP_SECONDS,
        "redirect_policy": "automatic_redirects_disabled_any_3xx_blocks_phase",
        "proxy_policy": "explicit_empty_proxy_handler",
        "compression_policy": "no_accept_encoding_and_reject_non_identity_content_encoding",
    }
    if any(ledger[key] != expected for key, expected in fixed.items()):
        raise BASE.FetchContractError("invalid_ledger", "M20B1 caps or policies differ")
    if canonical_json_bytes(ledger["requests"]) != canonical_json_bytes(EXPECTED_REQUESTS):
        raise BASE.FetchContractError("invalid_ledger", "M20B1 requests differ from the exact two reviewed rows")
    for row in ledger["requests"]:
        if row["url"].startswith("https://api.openalex.org/"):
            raise BASE.FetchContractError("invalid_url", "provider API routes are forbidden")
    for field in ("command", "worker_command"):
        if not isinstance(ledger[field], list) or not all(isinstance(item, str) for item in ledger[field]):
            raise BASE.FetchContractError("invalid_ledger", f"M20B1 {field} must be an argv list")
    return {**ledger, "requests": [dict(row) for row in ledger["requests"]]}


def _configure_base() -> None:
    BASE.SCHEMA = SCHEMA
    BASE.ALLOWED_HOSTS = {ALLOWED_HOST}
    BASE.EXPECTED_REQUESTS = [dict(row) for row in EXPECTED_REQUESTS]
    BASE.TRANSACTION_CAP = TRANSACTION_CAP
    BASE.PER_RESPONSE_CAP = PER_RESPONSE_CAP
    BASE.TOTAL_CAP = TOTAL_CAP
    BASE.TIMEOUT_SECONDS = TIMEOUT_SECONDS
    BASE.USER_AGENT = "research-assistant-m20b1/0.1 (official-auth-pricing-snapshot)"

    def strict_read_response_body(response: Any, *, aggregate_received: int) -> tuple[bytes, int]:
        body, received = BASE_READ_RESPONSE_BODY(response, aggregate_received=aggregate_received)
        try:
            body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise BASE.FetchContractError(
                "invalid_utf8",
                "documentation response is not strict UTF-8",
                observed_body_bytes=received,
            ) from exc
        return body, received

    BASE._read_response_body = strict_read_response_body


class StrictHtmlOpener:
    def __init__(self, opener: Any) -> None:
        self.opener = opener

    def open(self, request: Any, timeout: int) -> Any:
        response = self.opener.open(request, timeout=timeout)
        content_type = response.headers.get("Content-Type")
        parts = [part.strip() for part in content_type.split(";")] if isinstance(content_type, str) else []
        media_type = parts[0].casefold() if parts else ""
        charset = None
        for parameter in parts[1:]:
            name, separator, value = parameter.partition("=")
            if separator and name.strip().casefold() == "charset":
                charset = value.strip().strip('"').casefold()
        if media_type != "text/html" or charset not in {None, "utf-8", "utf8"}:
            try:
                response.close()
            finally:
                code = "not_html" if media_type != "text/html" else "invalid_charset"
                raise BASE.FetchContractError(code, "documentation response media type or charset is invalid")
        return response


def validate_command(ledger: dict[str, Any], *, argv: list[str]) -> None:
    if ledger["worker_command"] != argv:
        raise BASE.FetchContractError("command_mismatch", "executed argv differs from the reviewed M20B1 command")


def execute(ledger: dict[str, Any], *, output_root: Path, opener: Any, clock: Any = time.monotonic) -> dict[str, Any]:
    _configure_base()
    started = clock()
    fetch = BASE.fetch_documents(ledger, output_root=output_root, opener=StrictHtmlOpener(opener), clock=clock)
    elapsed = round(max(0.0, clock() - started), 6)
    status = fetch["status"]
    local_error = None
    if elapsed > WALL_TIME_CAP_SECONDS:
        status = "blocked_wall_time_cap_exceeded"
        local_error = "wall_time_cap_exceeded"
    campaign = {
        "schema_version": CAMPAIGN_SCHEMA,
        "status": status,
        "campaign_id": ledger["campaign_id"],
        "transaction_cap": TRANSACTION_CAP,
        "attempted_transaction_count": fetch["attempted_transaction_count"],
        "transactions_remaining": TRANSACTION_CAP - fetch["attempted_transaction_count"],
        "per_response_body_byte_cap": PER_RESPONSE_CAP,
        "aggregate_body_byte_cap": TOTAL_CAP,
        "aggregate_received_response_body_bytes": fetch["aggregate_received_response_body_bytes"],
        "aggregate_diagnostic_overflow_bytes": fetch["aggregate_diagnostic_overflow_bytes"],
        "wall_time_cap_seconds": WALL_TIME_CAP_SECONDS,
        "elapsed_seconds": elapsed,
        "fetch_manifest": "fetch_manifest.json",
        "local_error_code": local_error,
        "predecessor_sha256": {name: digest for name, _, digest in PREDECESSORS},
    }
    (output_root / "campaign_manifest.json").write_bytes(pretty_json_bytes(campaign))
    return campaign


def _loads_exact(path: Path) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root is not an object")
    return value


def validate_completed_artifacts(output_root: Path, ledger: dict[str, Any]) -> None:
    fetch = _loads_exact(output_root / "fetch_manifest.json")
    campaign = _loads_exact(output_root / "campaign_manifest.json")
    fetch_keys = {
        "schema_version", "status", "transaction_cap", "attempted_transaction_count",
        "per_response_body_byte_cap", "aggregate_body_byte_cap", "diagnostic_overflow_byte_cap",
        "aggregate_received_response_body_bytes", "aggregate_diagnostic_overflow_bytes",
        "retained_document_count", "requests",
    }
    if set(fetch) != fetch_keys or any(
        fetch.get(key) != value
        for key, value in {
            "schema_version": BASE.MANIFEST_SCHEMA,
            "status": "fetched_pending_contract_extraction",
            "transaction_cap": 2,
            "attempted_transaction_count": 2,
            "per_response_body_byte_cap": 2_000_000,
            "aggregate_body_byte_cap": 4_000_000,
            "diagnostic_overflow_byte_cap": 1,
            "aggregate_diagnostic_overflow_bytes": 0,
            "retained_document_count": 2,
        }.items()
    ):
        raise ValueError("fetch manifest is not exact and complete")
    rows = fetch["requests"]
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("fetch manifest request rows are incomplete")
    row_keys = set(BASE._manifest_row_base(EXPECTED_REQUESTS[0]))
    aggregate = 0
    expected_files = []
    for index, (row, request) in enumerate(zip(rows, EXPECTED_REQUESTS, strict=True), start=1):
        if not isinstance(row, dict) or set(row) != row_keys:
            raise ValueError("fetch request row keys are not exact")
        relative = f"raw/{index:02d}_{request['document_id']}.html"
        fixed = {
            "request_index": index,
            "document_id": request["document_id"],
            "provider": "openalex",
            "requested_url": request["url"],
            "final_url": request["url"],
            "status_code": 200,
            "outcome": "retained",
            "location": None,
            "content_encoding": None,
            "diagnostic_overflow_bytes": 0,
            "relative_path": relative,
            "error_code": None,
            "cumulative_attempted_transaction_count": index,
            "cumulative_diagnostic_overflow_bytes": 0,
        }
        if any(row.get(key) != value for key, value in fixed.items()):
            raise ValueError("fetch request row differs from the exact request contract")
        content_type = row.get("content_type")
        parts = [part.strip() for part in content_type.split(";")] if isinstance(content_type, str) else []
        charset_parameters = [
            parameter.partition("=")[2].strip().strip('"').casefold()
            for parameter in parts[1:]
            if parameter.partition("=")[0].strip().casefold() == "charset"
        ]
        if (
            not parts
            or parts[0].casefold() != "text/html"
            or any(charset not in {"utf-8", "utf8"} for charset in charset_parameters)
        ):
            raise ValueError("fetch request row is not HTML")
        elapsed = row.get("elapsed_seconds")
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("fetch request elapsed time is invalid")
        timestamp = row.get("retrieval_timestamp_utc")
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            raise ValueError("fetch request timestamp is invalid")
        received = row.get("received_response_body_bytes")
        retained = row.get("retained_bytes")
        digest = row.get("sha256")
        if (
            type(received) is not int
            or not 0 < received <= 2_000_000
            or retained != received
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError("fetch request retained-body accounting is invalid")
        raw_path = output_root / relative
        raw = raw_path.read_bytes()
        raw.decode("utf-8", errors="strict")
        if len(raw) != received or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("retained documentation body differs from its manifest")
        aggregate += received
        if row.get("cumulative_received_response_body_bytes") != aggregate:
            raise ValueError("fetch request cumulative accounting differs")
        expected_files.append(raw_path.resolve())
    if fetch["aggregate_received_response_body_bytes"] != aggregate:
        raise ValueError("fetch aggregate byte accounting differs")

    campaign_keys = {
        "schema_version", "status", "campaign_id", "transaction_cap",
        "attempted_transaction_count", "transactions_remaining", "per_response_body_byte_cap",
        "aggregate_body_byte_cap", "aggregate_received_response_body_bytes",
        "aggregate_diagnostic_overflow_bytes", "wall_time_cap_seconds", "elapsed_seconds",
        "fetch_manifest", "local_error_code", "predecessor_sha256",
    }
    if set(campaign) != campaign_keys or any(
        campaign.get(key) != value
        for key, value in {
            "schema_version": CAMPAIGN_SCHEMA,
            "status": "fetched_pending_contract_extraction",
            "campaign_id": ledger["campaign_id"],
            "transaction_cap": 2,
            "attempted_transaction_count": 2,
            "transactions_remaining": 0,
            "per_response_body_byte_cap": 2_000_000,
            "aggregate_body_byte_cap": 4_000_000,
            "aggregate_received_response_body_bytes": aggregate,
            "aggregate_diagnostic_overflow_bytes": 0,
            "wall_time_cap_seconds": 90,
            "fetch_manifest": "fetch_manifest.json",
            "local_error_code": None,
            "predecessor_sha256": {name: digest for name, _, digest in PREDECESSORS},
        }.items()
    ):
        raise ValueError("campaign manifest is not exact and complete")
    elapsed = campaign["elapsed_seconds"]
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("campaign elapsed time is invalid")
    allowed = {
        (output_root / "fetch_manifest.json").resolve(),
        (output_root / "campaign_manifest.json").resolve(),
        *expected_files,
    }
    observed = {path.resolve() for path in output_root.rglob("*") if path.is_file() and not path.is_symlink()}
    if observed != allowed or any(path.is_symlink() for path in output_root.rglob("*")):
        raise ValueError("worker artifact inventory is not exact")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    script_path = Path(__file__).resolve()
    ledger = validate_ledger(args.ledger, script_path=script_path)
    expected_command = [sys.executable, str(script_path), "--ledger", str(args.ledger), "--output-root", str(args.output_root)]
    validate_command(ledger, argv=expected_command)
    _configure_base()
    campaign = execute(ledger, output_root=args.output_root, opener=BASE.build_opener())
    print(json.dumps(campaign, sort_keys=True))
    return 0 if campaign["status"] == "fetched_pending_contract_extraction" else 2


if __name__ == "__main__":
    raise SystemExit(main())
