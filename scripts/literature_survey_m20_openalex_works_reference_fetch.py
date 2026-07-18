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

SCHEMA = "ra-literature-survey-m20-openalex-works-prefetch-v1"
MANIFEST_SCHEMA = "ra-literature-survey-m20-openalex-works-campaign-manifest-v1"
TARGET_URL = "https://developers.openalex.org/api-reference/works"
REPO_ROOT = Path(__file__).resolve().parents[1]
PRIOR_CAMPAIGN_MANIFEST = (
    REPO_ROOT / "docs/validation/literature_survey_m20_openalex_documentation_root_2026-07-14/campaign_manifest.json"
).resolve()
PRIOR_CAMPAIGN_SHA256 = "ad83774a0b592c3c056308ad15ed3aa103a0f8d13f36740eb13302c5bc5a4ef3"
ROOT_LINK_INVENTORY = (
    REPO_ROOT / "docs/validation/literature_survey_m20_openalex_documentation_root_2026-07-14/link_inventory.json"
).resolve()
ROOT_LINK_INVENTORY_SHA256 = "962b9c344a374b353d6e6195fe96d08a5178811fe87eff60fffc3ad9b0bd0e67"
PRIOR_TRANSACTION_COUNT = 3
PRIOR_ACCEPTED_BODY_BYTES = 448_240
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


def validate_ledger(path: Path, *, script_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BASE.FetchContractError("invalid_ledger", "works prefetch ledger is unreadable") from exc
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
            "root_link_inventory_path",
            "root_link_inventory_sha256",
            "command",
            "prior_transaction_count",
            "prior_accepted_response_body_bytes",
            "campaign_transaction_cap",
            "campaign_body_byte_cap",
            "request",
        },
        "works prefetch ledger",
    )
    if ledger["schema_version"] != SCHEMA or ledger["status"] != "reviewed_ready":
        raise BASE.FetchContractError("invalid_ledger", "works prefetch schema or status is invalid")
    if Path(ledger["script_path"]).resolve() != script_path.resolve() or ledger["script_sha256"] != sha256_path(script_path):
        raise BASE.FetchContractError("script_mismatch", "works script path or SHA-256 differs")
    if Path(ledger["base_script_path"]).resolve() != BASE_SCRIPT or ledger["base_script_sha256"] != sha256_path(BASE_SCRIPT):
        raise BASE.FetchContractError("script_mismatch", "base fetch primitive path or SHA-256 differs")
    if (
        Path(ledger["prior_campaign_manifest_path"]).resolve() != PRIOR_CAMPAIGN_MANIFEST
        or ledger["prior_campaign_manifest_sha256"] != PRIOR_CAMPAIGN_SHA256
        or sha256_path(PRIOR_CAMPAIGN_MANIFEST) != PRIOR_CAMPAIGN_SHA256
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "root campaign manifest identity differs")
    if (
        Path(ledger["root_link_inventory_path"]).resolve() != ROOT_LINK_INVENTORY
        or ledger["root_link_inventory_sha256"] != ROOT_LINK_INVENTORY_SHA256
        or sha256_path(ROOT_LINK_INVENTORY) != ROOT_LINK_INVENTORY_SHA256
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "root link inventory identity differs")
    prior = json.loads(PRIOR_CAMPAIGN_MANIFEST.read_text(encoding="utf-8"))
    inventory = json.loads(ROOT_LINK_INVENTORY.read_text(encoding="utf-8"))
    if (
        prior.get("status") != "fetched_pending_contract_extraction"
        or prior.get("campaign_attempted_transaction_count") != PRIOR_TRANSACTION_COUNT
        or prior.get("campaign_accepted_response_body_bytes") != PRIOR_ACCEPTED_BODY_BYTES
        or prior.get("campaign_transaction_cap") != CAMPAIGN_TRANSACTION_CAP
        or prior.get("campaign_body_byte_cap") != CAMPAIGN_BODY_BYTE_CAP
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "root campaign budget/status differs")
    links = inventory.get("links")
    if not isinstance(links, list) or not any(isinstance(row, dict) and row.get("url") == TARGET_URL for row in links):
        raise BASE.FetchContractError("prior_evidence_mismatch", "works URL is absent from the retained root inventory")
    fixed = {
        "prior_transaction_count": PRIOR_TRANSACTION_COUNT,
        "prior_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES,
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
    }
    if any(ledger[key] != expected for key, expected in fixed.items()):
        raise BASE.FetchContractError("invalid_ledger", "works campaign budget differs")
    expected_request = {
        "request_index": 4,
        "document_id": "openalex_works_reference",
        "provider": "openalex",
        "url": TARGET_URL,
        "semantic_role": "works_routes_fields_authentication_and_cost",
        "requirement": "indispensable",
    }
    request = _exact_dict(
        ledger["request"],
        {"request_index", "document_id", "provider", "url", "semantic_role", "requirement"},
        "works request",
    )
    if canonical_json_bytes(request) != canonical_json_bytes(expected_request):
        raise BASE.FetchContractError("invalid_ledger", "works request differs from the reviewed row")
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
                raise BASE.FetchContractError("not_html", "works reference is not HTML")
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
        "root_link_inventory_sha256": ROOT_LINK_INVENTORY_SHA256,
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
