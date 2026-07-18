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

SCHEMA = "ra-literature-survey-m20-openalex-single-work-prefetch-v1"
MANIFEST_SCHEMA = "ra-literature-survey-m20-openalex-single-work-campaign-manifest-v1"
TARGET_URL = "https://developers.openalex.org/api-reference/works/get-a-single-work"
REPO_ROOT = Path(__file__).resolve().parents[1]
PRIOR_ROOT = (REPO_ROOT / "docs/validation/literature_survey_m20_openalex_works_reference_2026-07-14").resolve()
PRIOR_CAMPAIGN_MANIFEST = (PRIOR_ROOT / "campaign_manifest.json").resolve()
PRIOR_CAMPAIGN_SHA256 = "e464d614364de7d4c96327c78827a8a3af332e7ba6121522aadb1ea86c6a3d28"
PRIOR_FETCH_MANIFEST = (PRIOR_ROOT / "fetch_manifest.json").resolve()
PRIOR_FETCH_SHA256 = "317595ec72647a013f69b591b676b5dc732afa33ed715f9d68e8ace1224cbfe2"
PRIOR_BODY = (PRIOR_ROOT / "raw/01_openalex_works_reference.html").resolve()
PRIOR_BODY_SHA256 = "40808a7e752a8701535987dcf9b0ae81d9f6bb677b5f62a015e4718b7df2a9ff"
PRIOR_SUBPLAN = (
    REPO_ROOT / "docs/plans/literature_survey_north_star_m20a_openalex_works_reference_subplan_2026-07-14.md"
).resolve()
PRIOR_SUBPLAN_SHA256 = "8503bdf84ae302d97e9c0765051637ca6a7109d04c6877210d42c43a5870cf03"
PRIOR_CONTRACT_EXTRACT = (PRIOR_ROOT / "contract_extract.md").resolve()
PRIOR_CONTRACT_EXTRACT_SHA256 = "454f54a352a537d6bba2d31231cf78efabb740c13a490f2dc3644f55ce4c8b70"
PRIOR_ROUTE_DECISION = (PRIOR_ROOT / "route_decision.json").resolve()
PRIOR_ROUTE_DECISION_SHA256 = "5650b9a9e46a53b4be3b7a25b42ebaadcdedb8c6a8055806167c1517f528e36f"
PRIOR_RESULT = (
    REPO_ROOT / "docs/plans/literature_survey_north_star_m20a_openalex_works_reference_result_2026-07-14.md"
).resolve()
PRIOR_RESULT_SHA256 = "81012acd99b145c99bfe46a9c1d06a09807d701c8e80f0bfaaad6a71cf35e764"
PRIOR_TRANSACTION_COUNT = 4
PRIOR_ACCEPTED_BODY_BYTES = 1_168_335
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


def _validate_predecessor() -> None:
    expected = (
        (PRIOR_CAMPAIGN_MANIFEST, PRIOR_CAMPAIGN_SHA256, "campaign manifest"),
        (PRIOR_FETCH_MANIFEST, PRIOR_FETCH_SHA256, "fetch manifest"),
        (PRIOR_BODY, PRIOR_BODY_SHA256, "retained works body"),
        (PRIOR_SUBPLAN, PRIOR_SUBPLAN_SHA256, "transaction-4 subplan"),
        (PRIOR_CONTRACT_EXTRACT, PRIOR_CONTRACT_EXTRACT_SHA256, "transaction-4 contract extract"),
        (PRIOR_ROUTE_DECISION, PRIOR_ROUTE_DECISION_SHA256, "transaction-4 route decision"),
        (PRIOR_RESULT, PRIOR_RESULT_SHA256, "transaction-4 result"),
    )
    for path, digest, label in expected:
        try:
            observed = sha256_path(path)
        except OSError as exc:
            raise BASE.FetchContractError("prior_evidence_mismatch", f"{label} is unreadable") from exc
        if observed != digest or not path.is_file() or path.is_symlink():
            raise BASE.FetchContractError("prior_evidence_mismatch", f"{label} identity differs")
    try:
        campaign = json.loads(PRIOR_CAMPAIGN_MANIFEST.read_text(encoding="utf-8"))
        fetch = json.loads(PRIOR_FETCH_MANIFEST.read_text(encoding="utf-8"))
        body = PRIOR_BODY.read_bytes()
        route_decision = json.loads(PRIOR_ROUTE_DECISION.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-4 evidence is unreadable") from exc
    if any(
        campaign.get(key) != expected_value
        for key, expected_value in {
            "status": "fetched_pending_contract_extraction",
            "campaign_attempted_transaction_count": PRIOR_TRANSACTION_COUNT,
            "campaign_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES,
            "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
            "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
            "campaign_transactions_remaining": 2,
        }.items()
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-4 campaign state differs")
    requests = fetch.get("requests")
    row = requests[0] if isinstance(requests, list) and len(requests) == 1 else None
    if not isinstance(row, dict) or any(
        row.get(key) != expected_value
        for key, expected_value in {
            "outcome": "retained",
            "requested_url": "https://developers.openalex.org/api-reference/works",
            "final_url": "https://developers.openalex.org/api-reference/works",
            "relative_path": "raw/01_openalex_works_reference.html",
            "sha256": PRIOR_BODY_SHA256,
            "retained_bytes": 720_095,
        }.items()
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-4 retained row differs")
    required_anchors = (
        b'href="/api-reference/works/get-a-single-work"',
        b'get /works/{id}',
    )
    if any(anchor not in body for anchor in required_anchors):
        raise BASE.FetchContractError("prior_evidence_mismatch", "singleton operation link or binding is absent")
    decisions = route_decision.get("decisions")
    allowed_statuses = {"supported", "contradicted", "ambiguous", "not_documented"}
    if (
        route_decision.get("schema_version") != "ra-literature-survey-m20-openalex-works-route-decision-v1"
        or not isinstance(decisions, dict)
        or set(decisions) != {
            "authentication_and_cost",
            "backward_navigation",
            "forward_citation_filter",
            "list_search_filter_sort_paging_select",
            "required_metadata_fields",
            "single_work_by_arxiv_id",
            "single_work_by_openalex_id",
        }
        or any(not isinstance(row, dict) or row.get("status") not in allowed_statuses for row in decisions.values())
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "transaction-4 route decision schema or status differs")


def validate_ledger(path: Path, *, script_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BASE.FetchContractError("invalid_ledger", "single-work prefetch ledger is unreadable") from exc
    ledger = _exact_dict(
        value,
        {
            "schema_version",
            "status",
            "script_path",
            "script_sha256",
            "base_script_path",
            "base_script_sha256",
            "prior_campaign_manifest_path",
            "prior_campaign_manifest_sha256",
            "prior_fetch_manifest_path",
            "prior_fetch_manifest_sha256",
            "prior_body_path",
            "prior_body_sha256",
            "prior_subplan_path",
            "prior_subplan_sha256",
            "prior_contract_extract_path",
            "prior_contract_extract_sha256",
            "prior_route_decision_path",
            "prior_route_decision_sha256",
            "prior_result_path",
            "prior_result_sha256",
            "command",
            "prior_transaction_count",
            "prior_accepted_response_body_bytes",
            "campaign_transaction_cap",
            "campaign_body_byte_cap",
            "request",
        },
        "single-work prefetch ledger",
    )
    if ledger["schema_version"] != SCHEMA or ledger["status"] != "reviewed_ready":
        raise BASE.FetchContractError("invalid_ledger", "single-work prefetch schema or status is invalid")
    if Path(ledger["script_path"]).resolve() != script_path.resolve() or ledger["script_sha256"] != sha256_path(script_path):
        raise BASE.FetchContractError("script_mismatch", "single-work script path or SHA-256 differs")
    if Path(ledger["base_script_path"]).resolve() != BASE_SCRIPT or ledger["base_script_sha256"] != sha256_path(BASE_SCRIPT):
        raise BASE.FetchContractError("script_mismatch", "base fetch primitive path or SHA-256 differs")
    bindings = (
        ("prior_campaign_manifest_path", PRIOR_CAMPAIGN_MANIFEST, "prior_campaign_manifest_sha256", PRIOR_CAMPAIGN_SHA256),
        ("prior_fetch_manifest_path", PRIOR_FETCH_MANIFEST, "prior_fetch_manifest_sha256", PRIOR_FETCH_SHA256),
        ("prior_body_path", PRIOR_BODY, "prior_body_sha256", PRIOR_BODY_SHA256),
        ("prior_subplan_path", PRIOR_SUBPLAN, "prior_subplan_sha256", PRIOR_SUBPLAN_SHA256),
        (
            "prior_contract_extract_path",
            PRIOR_CONTRACT_EXTRACT,
            "prior_contract_extract_sha256",
            PRIOR_CONTRACT_EXTRACT_SHA256,
        ),
        ("prior_route_decision_path", PRIOR_ROUTE_DECISION, "prior_route_decision_sha256", PRIOR_ROUTE_DECISION_SHA256),
        ("prior_result_path", PRIOR_RESULT, "prior_result_sha256", PRIOR_RESULT_SHA256),
    )
    if any(Path(ledger[path_key]).resolve() != path or ledger[sha_key] != digest for path_key, path, sha_key, digest in bindings):
        raise BASE.FetchContractError("prior_evidence_mismatch", "single-work predecessor bindings differ")
    _validate_predecessor()
    fixed = {
        "prior_transaction_count": PRIOR_TRANSACTION_COUNT,
        "prior_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES,
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
    }
    if any(ledger[key] != expected for key, expected in fixed.items()):
        raise BASE.FetchContractError("invalid_ledger", "single-work campaign budget differs")
    expected_request = {
        "request_index": 5,
        "document_id": "openalex_single_work_operation",
        "provider": "openalex",
        "url": TARGET_URL,
        "semantic_role": "direct_work_identifier_selection_response_and_cost_contract",
        "requirement": "indispensable",
    }
    request = _exact_dict(
        ledger["request"],
        {"request_index", "document_id", "provider", "url", "semantic_role", "requirement"},
        "single-work request",
    )
    if canonical_json_bytes(request) != canonical_json_bytes(expected_request):
        raise BASE.FetchContractError("invalid_ledger", "single-work request differs from the reviewed row")
    if not isinstance(ledger["command"], list) or not all(isinstance(item, str) for item in ledger["command"]):
        raise BASE.FetchContractError("invalid_ledger", "single-work command must be an argv list")
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
                raise BASE.FetchContractError("not_html", "single-work reference is not HTML")
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
        "prior_campaign_manifest_sha256": PRIOR_CAMPAIGN_SHA256,
        "prior_fetch_manifest_sha256": PRIOR_FETCH_SHA256,
        "prior_body_sha256": PRIOR_BODY_SHA256,
        "prior_subplan_sha256": PRIOR_SUBPLAN_SHA256,
        "prior_contract_extract_sha256": PRIOR_CONTRACT_EXTRACT_SHA256,
        "prior_route_decision_sha256": PRIOR_ROUTE_DECISION_SHA256,
        "prior_result_sha256": PRIOR_RESULT_SHA256,
        "campaign_request_index": ledger["request"]["request_index"],
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_attempted_transaction_count": PRIOR_TRANSACTION_COUNT + fetch["attempted_transaction_count"],
        "campaign_transactions_remaining": CAMPAIGN_TRANSACTION_CAP - PRIOR_TRANSACTION_COUNT - fetch["attempted_transaction_count"],
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
        "campaign_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES + fetch["aggregate_received_response_body_bytes"],
        "campaign_diagnostic_overflow_bytes": fetch["aggregate_diagnostic_overflow_bytes"],
        "attempt_fetch_manifest": "fetch_manifest.json",
        "local_validation_error_code": local_error,
    }
    if campaign["campaign_accepted_response_body_bytes"] > CAMPAIGN_BODY_BYTE_CAP:
        campaign["status"] = "blocked_campaign_body_cap_exceeded"
        campaign["local_validation_error_code"] = "campaign_body_cap_exceeded"
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
