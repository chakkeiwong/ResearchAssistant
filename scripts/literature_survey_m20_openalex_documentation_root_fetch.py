from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


BASE_SCRIPT = Path(__file__).with_name("literature_survey_m20_official_provider_contract_fetch.py").resolve()
BASE_SPEC = importlib.util.spec_from_file_location("m20_official_docs_base", BASE_SCRIPT)
if BASE_SPEC is None or BASE_SPEC.loader is None:
    raise RuntimeError("cannot load the reviewed documentation fetch primitive")
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)

SCHEMA = "ra-literature-survey-m20-openalex-doc-root-prefetch-v1"
MANIFEST_SCHEMA = "ra-literature-survey-m20-openalex-doc-root-campaign-manifest-v1"
TARGET_URL = "https://developers.openalex.org/"
PRIOR_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "docs/validation/literature_survey_m20_official_provider_contract_2026-07-14/fetch_manifest.json"
).resolve()
PRIOR_MANIFEST_SHA256 = "bd80c1fc7d4bdbe2713bb1114f1a24fe03584912088704379eadb801934d53f2"
PRIOR_TRANSACTION_COUNT = 2
PRIOR_ACCEPTED_BODY_BYTES = 160_783
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
        raise BASE.FetchContractError("invalid_ledger", "root prefetch ledger is unreadable") from exc
    ledger = _exact_dict(
        value,
        {
            "schema_version",
            "status",
            "script_path",
            "script_sha256",
            "base_script_path",
            "base_script_sha256",
            "prior_manifest_path",
            "prior_manifest_sha256",
            "command",
            "prior_transaction_count",
            "prior_accepted_response_body_bytes",
            "campaign_transaction_cap",
            "campaign_body_byte_cap",
            "request",
        },
        "root prefetch ledger",
    )
    if ledger["schema_version"] != SCHEMA or ledger["status"] != "reviewed_ready":
        raise BASE.FetchContractError("invalid_ledger", "root prefetch schema or status is invalid")
    if Path(ledger["script_path"]).resolve() != script_path.resolve() or ledger["script_sha256"] != sha256_path(script_path):
        raise BASE.FetchContractError("script_mismatch", "root script path or SHA-256 differs")
    if Path(ledger["base_script_path"]).resolve() != BASE_SCRIPT or ledger["base_script_sha256"] != sha256_path(BASE_SCRIPT):
        raise BASE.FetchContractError("script_mismatch", "base fetch primitive path or SHA-256 differs")
    prior_path = Path(ledger["prior_manifest_path"])
    if prior_path.resolve() != PRIOR_MANIFEST or ledger["prior_manifest_sha256"] != PRIOR_MANIFEST_SHA256:
        raise BASE.FetchContractError("prior_evidence_mismatch", "attempt-1 manifest identity differs")
    if sha256_path(prior_path) != PRIOR_MANIFEST_SHA256:
        raise BASE.FetchContractError("prior_evidence_mismatch", "attempt-1 manifest SHA-256 differs")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    fixed = {
        "prior_transaction_count": PRIOR_TRANSACTION_COUNT,
        "prior_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES,
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
    }
    if any(ledger[key] != expected for key, expected in fixed.items()):
        raise BASE.FetchContractError("invalid_ledger", "campaign budget differs")
    if (
        prior.get("attempted_transaction_count") != PRIOR_TRANSACTION_COUNT
        or prior.get("aggregate_received_response_body_bytes") != PRIOR_ACCEPTED_BODY_BYTES
        or prior.get("transaction_cap") != CAMPAIGN_TRANSACTION_CAP
        or prior.get("aggregate_body_byte_cap") != CAMPAIGN_BODY_BYTE_CAP
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "attempt-1 manifest budget differs")
    requests = prior.get("requests")
    redirect = requests[1] if isinstance(requests, list) and len(requests) == 2 else None
    if not isinstance(redirect, dict) or any(
        redirect.get(key) != expected
        for key, expected in {
            "request_index": 2,
            "document_id": "openalex_works",
            "provider": "openalex",
            "requested_url": "https://docs.openalex.org/api-entities/works",
            "status_code": 301,
            "outcome": "blocked_redirect",
            "error_code": "redirect_forbidden",
            "location": TARGET_URL,
        }.items()
    ):
        raise BASE.FetchContractError("prior_evidence_mismatch", "attempt-1 redirect evidence differs")
    request = _exact_dict(
        ledger["request"],
        {"request_index", "document_id", "provider", "url", "semantic_role", "requirement"},
        "root request",
    )
    expected_request = {
        "request_index": 3,
        "document_id": "openalex_documentation_root",
        "provider": "openalex",
        "url": TARGET_URL,
        "semantic_role": "current_official_documentation_link_inventory",
        "requirement": "indispensable",
    }
    if canonical_json_bytes(request) != canonical_json_bytes(expected_request):
        raise BASE.FetchContractError("invalid_ledger", "root request differs from the reviewed row")
    if BASE.PER_RESPONSE_CAP > REMAINING_BODY_BYTE_CAP:
        raise BASE.FetchContractError("campaign_cap_mismatch", "base per-response cap exceeds the remaining campaign cap")
    return {**ledger, "request": request}


def validate_command(ledger: dict[str, Any], *, argv: list[str]) -> None:
    if ledger["command"] != argv:
        raise BASE.FetchContractError("command_mismatch", "executed argv differs from the reviewed command")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        self._href = next((value for name, value in attrs if name.casefold() == "href"), None)
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


def link_inventory(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BASE.FetchContractError("invalid_document", "documentation root is not UTF-8") from exc
    parser = LinkParser()
    parser.feed(text)
    rows: dict[str, dict[str, str]] = {}
    for href, label in parser.links:
        absolute = urllib.parse.urljoin(TARGET_URL, href)
        parsed = urllib.parse.urlsplit(absolute)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "developers.openalex.org"
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            continue
        normalized = urllib.parse.urlunsplit(("https", "developers.openalex.org", parsed.path or "/", parsed.query, ""))
        rows.setdefault(normalized, {"url": normalized, "link_text": label})
    return {
        "schema_version": "ra-literature-survey-m20-openalex-doc-link-inventory-v1",
        "source_url": TARGET_URL,
        "same_host_link_count": len(rows),
        "links": [rows[key] for key in sorted(rows)],
    }


def execute(ledger: dict[str, Any], *, output_root: Path, opener: Any) -> dict[str, Any]:
    attempt_ledger = {"requests": [dict(ledger["request"], request_index=1)]}
    fetch = BASE.fetch_documents(attempt_ledger, output_root=output_root, opener=opener)
    inventory_path = None
    inventory_error_code = None
    if fetch["status"] == "fetched_pending_contract_extraction":
        try:
            content_type = (fetch["requests"][0]["content_type"] or "").split(";", 1)[0].strip().casefold()
            if content_type != "text/html":
                raise BASE.FetchContractError("not_html", "documentation root is not HTML")
            retained = output_root / fetch["requests"][0]["relative_path"]
            inventory = link_inventory(retained.read_bytes())
            candidate_inventory_path = output_root / "link_inventory.json"
            candidate_inventory_path.write_bytes(pretty_json_bytes(inventory))
            inventory_path = candidate_inventory_path
            if inventory["same_host_link_count"] == 0:
                fetch["status"] = "blocked_no_same_host_documentation_links"
                inventory_error_code = "no_same_host_documentation_links"
        except BASE.FetchContractError as exc:
            fetch["status"] = "blocked_link_inventory_error"
            inventory_error_code = exc.code
        except OSError:
            inventory_path = None
            fetch["status"] = "blocked_link_inventory_error"
            inventory_error_code = "link_inventory_io_error"
    campaign = {
        "schema_version": MANIFEST_SCHEMA,
        "status": fetch["status"],
        "prior_manifest_sha256": ledger["prior_manifest_sha256"],
        "campaign_request_index": ledger["request"]["request_index"],
        "campaign_transaction_cap": CAMPAIGN_TRANSACTION_CAP,
        "campaign_attempted_transaction_count": PRIOR_TRANSACTION_COUNT + fetch["attempted_transaction_count"],
        "campaign_transactions_remaining": CAMPAIGN_TRANSACTION_CAP - PRIOR_TRANSACTION_COUNT - fetch["attempted_transaction_count"],
        "campaign_body_byte_cap": CAMPAIGN_BODY_BYTE_CAP,
        "campaign_accepted_response_body_bytes": PRIOR_ACCEPTED_BODY_BYTES + fetch["aggregate_received_response_body_bytes"],
        "campaign_diagnostic_overflow_bytes": fetch["aggregate_diagnostic_overflow_bytes"],
        "attempt_fetch_manifest": "fetch_manifest.json",
        "link_inventory": None if inventory_path is None else inventory_path.name,
        "link_inventory_error_code": inventory_error_code,
    }
    if campaign["campaign_accepted_response_body_bytes"] > CAMPAIGN_BODY_BYTE_CAP:
        campaign["status"] = "blocked_campaign_body_cap_exceeded"
        campaign["link_inventory"] = None
        campaign["link_inventory_error_code"] = "campaign_body_cap_exceeded"
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
