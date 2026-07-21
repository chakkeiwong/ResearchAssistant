from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BASE_SCRIPT = Path(__file__).with_name("literature_survey_m20_official_provider_contract_fetch.py").resolve()
BASE_SPEC = importlib.util.spec_from_file_location("m20_official_docs_base", BASE_SCRIPT)
if BASE_SPEC is None or BASE_SPEC.loader is None:
    raise RuntimeError("cannot load the reviewed documentation fetch primitive")
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)

SCHEMA = "ra-literature-survey-m20-openalex-list-works-prefetch-v1"
MANIFEST_SCHEMA = "ra-literature-survey-m20-openalex-list-works-campaign-manifest-v1"
TARGET_URL = "https://developers.openalex.org/api-reference/works/list-works"
REPO_ROOT = Path(__file__).resolve().parents[1]
T4_ROOT = (REPO_ROOT / "docs/validation/literature_survey_m20_openalex_works_reference_2026-07-14").resolve()
T5_ROOT = (REPO_ROOT / "docs/validation/literature_survey_m20_openalex_single_work_operation_2026-07-14").resolve()
PREDECESSORS = (
    (
        "t4_body",
        T4_ROOT / "raw/01_openalex_works_reference.html",
        "40808a7e752a8701535987dcf9b0ae81d9f6bb677b5f62a015e4718b7df2a9ff",
    ),
    (
        "t5_subplan",
        REPO_ROOT / "docs/plans/literature_survey_north_star_m20a_openalex_single_work_operation_subplan_2026-07-14.md",
        "2903fb7cae2b15fd31d138911a5ef7bbb266d2735e1c836dfd3b4d5d602cd315",
    ),
    (
        "t5_prefetch_ledger",
        REPO_ROOT / "docs/plans/literature_survey_north_star_m20a_openalex_single_work_operation_prefetch_ledger_2026-07-14.json",
        "9b12d78f3cfbfa776cc786b56fc491be2ed616558d1689b077453c9c4d50be10",
    ),
    (
        "t5_script",
        REPO_ROOT / "scripts/literature_survey_m20_openalex_single_work_operation_fetch.py",
        "3b7018ba099801b55e5384a571e174936fe589e17ce0492d35e7fdba65623ea7",
    ),
    (
        "t5_tests",
        REPO_ROOT / "tests/scripts/test_literature_survey_m20_openalex_single_work_operation_fetch.py",
        "942b3da97115ea5900e42b4888c739bad223afaee1314cd03a5381e0814dba9b",
    ),
    (
        "t5_body",
        T5_ROOT / "raw/01_openalex_single_work_operation.html",
        "76e78cef081b1d4e0c14ca01637163f92a3c430faa2f353f4704b80730d91b97",
    ),
    (
        "t5_fetch_manifest",
        T5_ROOT / "fetch_manifest.json",
        "a463e5ae37a65879b6eddb11db9ac64127a3595dbefc93579773a56bf05fcd81",
    ),
    (
        "t5_campaign_manifest",
        T5_ROOT / "campaign_manifest.json",
        "8e059198d202ef77d4cb4c5d3e2f0f16debdca748bb36869b4b34f5a5fbacd4f",
    ),
    (
        "t5_contract_extract",
        T5_ROOT / "contract_extract.md",
        "168eacb97701efea1cbb52a65a2c64e84981b4a4f2b2db24045f699ab81462ca",
    ),
    (
        "t5_route_decision",
        T5_ROOT / "route_decision.json",
        "cf9cd34c206a5a4bec29b71ac974d9f24844e136a0e9ce73f6a5b86f3b4f775c",
    ),
    (
        "t5_result",
        REPO_ROOT / "docs/plans/literature_survey_north_star_m20a_openalex_single_work_operation_result_2026-07-14.md",
        "24ba8f27a39b9a02a675ec905a63d81090f9d6484d6f84429d10dc80e8423fa1",
    ),
)
PRIOR_TRANSACTION_COUNT = 5
PRIOR_ACCEPTED_BODY_BYTES = 1_817_762
CAMPAIGN_TRANSACTION_CAP = 6
CAMPAIGN_BODY_BYTE_CAP = 8_000_000
REMAINING_BODY_BYTE_CAP = CAMPAIGN_BODY_BYTE_CAP - PRIOR_ACCEPTED_BODY_BYTES


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
    try:
        t4_body = (T4_ROOT / "raw/01_openalex_works_reference.html").read_bytes()
        t5_body = (T5_ROOT / "raw/01_openalex_single_work_operation.html").read_bytes()
        campaign = json.loads((T5_ROOT / "campaign_manifest.json").read_text(encoding="utf-8"))
        fetch = json.loads((T5_ROOT / "fetch_manifest.json").read_text(encoding="utf-8"))
        route = json.loads((T5_ROOT / "route_decision.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-5 evidence is unreadable") from exc
    if b'href="/api-reference/works/list-works"' not in t4_body or b'get /works' not in t4_body:
        raise BASE.FetchContractError("prior_evidence_mismatch", "list-works operation link or binding is absent")
    if b'\\"name\\":\\"api_key\\"' not in t5_body or b'\\"required\\":true' not in t5_body:
        raise BASE.FetchContractError("prior_evidence_mismatch", "required API-key anchor is absent")
    if any(
        campaign.get(key) != value
        for key, value in {
            "status": "fetched_pending_contract_extraction",
            "campaign_attempted_transaction_count": PRIOR_TRANSACTION_COUNT,
            "campaign_transactions_remaining": 1,
            "campaign_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES,
            "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
            "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
        }.items()
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-5 campaign state differs")
    requests = fetch.get("requests")
    row = requests[0] if isinstance(requests, list) and len(requests) == 1 else None
    if not isinstance(row, dict) or any(
        row.get(key) != value
        for key, value in {
            "outcome": "retained",
            "requested_url": "https://developers.openalex.org/api-reference/works/get-a-single-work",
            "final_url": "https://developers.openalex.org/api-reference/works/get-a-single-work",
            "sha256": "76e78cef081b1d4e0c14ca01637163f92a3c430faa2f353f4704b80730d91b97",
            "retained_bytes": 649_427,
        }.items()
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-5 retained row differs")
    decisions = route.get("decisions")
    allowed = {"supported", "contradicted", "ambiguous", "not_documented"}
    if not isinstance(decisions, dict) or any(
        not isinstance(decision, dict) or decision.get("status") not in allowed for decision in decisions.values()
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-5 route decision is not closed")
    if decisions.get("anonymous_api_access", {}).get("status") != "contradicted":
        raise BASE.FetchContractError("prior_evidence_mismatch", "required API-key decision differs")


def validate_ledger(path: Path, *, script_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BASE.FetchContractError("invalid_ledger", "list-works prefetch ledger is unreadable") from exc
    predecessor_keys = {f"{name}_{suffix}" for name, _, _ in PREDECESSORS for suffix in ("path", "sha256")}
    ledger = _exact_dict(
        value,
        {
            "schema_version",
            "status",
            "script_path",
            "script_sha256",
            "base_script_path",
            "base_script_sha256",
            "command",
            "prior_transaction_count",
            "prior_accepted_response_body_bytes",
            "campaign_transaction_cap",
            "campaign_body_byte_cap",
            "request",
            *predecessor_keys,
        },
        "list-works prefetch ledger",
    )
    if ledger["schema_version"] != SCHEMA or ledger["status"] != "reviewed_ready":
        raise BASE.FetchContractError("invalid_ledger", "list-works prefetch schema or status is invalid")
    if Path(ledger["script_path"]).resolve() != script_path.resolve() or ledger["script_sha256"] != sha256_path(script_path):
        raise BASE.FetchContractError("script_mismatch", "list-works script path or SHA-256 differs")
    if Path(ledger["base_script_path"]).resolve() != BASE_SCRIPT or ledger["base_script_sha256"] != sha256_path(BASE_SCRIPT):
        raise BASE.FetchContractError("script_mismatch", "base fetch primitive path or SHA-256 differs")
    if any(
        Path(ledger[f"{name}_path"]).resolve() != path.resolve() or ledger[f"{name}_sha256"] != digest
        for name, path, digest in PREDECESSORS
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "list-works predecessor bindings differ")
    _validate_predecessors()
    fixed = {
        "prior_transaction_count": PRIOR_TRANSACTION_COUNT,
        "prior_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES,
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
    }
    if any(ledger[key] != expected for key, expected in fixed.items()):
        raise BASE.FetchContractError("invalid_ledger", "list-works campaign budget differs")
    expected_request = {
        "request_index": 6,
        "document_id": "openalex_list_works_operation",
        "provider": "openalex",
        "url": TARGET_URL,
        "semantic_role": "search_filter_sort_select_paging_response_key_and_cost_contract",
        "requirement": "indispensable",
    }
    request = _exact_dict(
        ledger["request"],
        {"request_index", "document_id", "provider", "url", "semantic_role", "requirement"},
        "list-works request",
    )
    if canonical_json_bytes(request) != canonical_json_bytes(expected_request):
        raise BASE.FetchContractError("invalid_ledger", "list-works request differs from the reviewed row")
    if not isinstance(ledger["command"], list) or not all(isinstance(item, str) for item in ledger["command"]):
        raise BASE.FetchContractError("invalid_ledger", "list-works command must be an argv list")
    if BASE.PER_RESPONSE_CAP > REMAINING_BODY_BYTE_CAP:
        raise BASE.FetchContractError("campaign_cap_mismatch", "base cap exceeds the remaining campaign allowance")
    return {**ledger, "request": request}


def validate_command(ledger: dict[str, Any], *, argv: list[str]) -> None:
    if ledger["command"] != argv:
        raise BASE.FetchContractError("command_mismatch", "executed argv differs from the reviewed command")


def execute(ledger: dict[str, Any], *, output_root: Path, opener: Any) -> dict[str, Any]:
    attempt_ledger = {"requests": [dict(ledger["request"], request_index=1)]}
    fetch = BASE.fetch_documents(attempt_ledger, output_root=output_root, opener=opener)
    local_error = None
    if fetch["status"] == "fetched_pending_contract_extraction":
        row = fetch["requests"][0]
        media_type = (row["content_type"] or "").split(";", 1)[0].strip().casefold()
        try:
            if media_type != "text/html":
                raise BASE.FetchContractError("not_html", "list-works reference is not HTML")
            retained = output_root / row["relative_path"]
            retained.read_bytes().decode("utf-8")
        except BASE.FetchContractError as exc:
            fetch["status"] = "blocked_local_validation_error"
            local_error = exc.code
        except UnicodeDecodeError:
            fetch["status"] = "blocked_local_validation_error"
            local_error = "invalid_utf8"
        except OSError:
            fetch["status"] = "blocked_local_validation_error"
            local_error = "retained_file_io_error"
    campaign = {
        "schema_version": MANIFEST_SCHEMA,
        "status": fetch["status"],
        "campaign_request_index": ledger["request"]["request_index"],
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_attempted_transaction_count": PRIOR_TRANSACTION_COUNT + fetch["attempted_transaction_count"],
        "campaign_transactions_remaining": CAMPAIGN_TRANSACTION_CAP - PRIOR_TRANSACTION_COUNT - fetch["attempted_transaction_count"],
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
        "campaign_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES + fetch["aggregate_received_response_body_bytes"],
        "campaign_diagnostic_overflow_bytes": fetch["aggregate_diagnostic_overflow_bytes"],
        "attempt_fetch_manifest": "fetch_manifest.json",
        "local_validation_error_code": local_error,
        "predecessor_sha256": {name: digest for name, _, digest in PREDECESSORS},
    }
    if campaign["campaign_accepted_response_body_bytes"] > CAMPAIGN_BODY_BYTE_CAP:
        campaign["status"] = "blocked_campaign_body_cap_exceeded"
        campaign["local_validation_error_code"] = "campaign_body_cap_exceeded"
    if campaign["campaign_attempted_transaction_count"] != CAMPAIGN_TRANSACTION_CAP:
        campaign["status"] = "blocked_campaign_transaction_closure_error"
        campaign["local_validation_error_code"] = "campaign_transaction_closure_error"
    (output_root / "campaign_manifest.json").write_bytes(pretty_json_bytes(campaign))
    return campaign


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    script_path = Path(__file__).resolve()
    ledger = validate_ledger(args.ledger, script_path=script_path)
    expected_command = [sys.executable, str(script_path), "--ledger", str(args.ledger), "--output-root", str(args.output_root)]
    validate_command(ledger, argv=expected_command)
    campaign = execute(ledger, output_root=args.output_root, opener=BASE.build_opener())
    print(json.dumps(campaign, sort_keys=True))
    return 0 if campaign["status"] == "fetched_pending_contract_extraction" else 2


if __name__ == "__main__":
    raise SystemExit(main())
