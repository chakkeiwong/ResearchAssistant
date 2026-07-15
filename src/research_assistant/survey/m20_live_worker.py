from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.discovery_capability import (
    bind_normalized_payload,
    classify_frontier_attempt,
    classify_identity_outcome,
    compose_openalex_case_outcome,
    outcome_automaton_sha256,
    replay_accepted_body,
    validate_accepted_body_inventory,
    write_accepted_body,
)
from research_assistant.survey.discovery_quality import normalize_arxiv_id, normalize_doi
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
)
from research_assistant.survey.openalex_adapter import (
    build_openalex_direct_descriptor,
    build_openalex_forward_descriptor,
    build_openalex_topic_descriptor,
    parse_openalex_direct_response,
    parse_openalex_forward_response,
    parse_openalex_topic_response,
)
from research_assistant.survey.openalex_credential_cost import (
    CAMPAIGN_COST_CAP_USD,
    CREDENTIAL_INTERFACE,
    CREDENTIAL_SOURCE_KIND,
    ROUTE_COST_USD,
    CampaignCostBudget,
    execute_authenticated_openalex_request,
)


TOPIC = "Neural Optimal Transport for generative modeling and inference"
ARXIV_SEED = "2201.12220v3"
OPENALEX_ID = "W4387130479"
REQUEST_CAP = 5
PER_REQUEST_BODY_CAP = 2_000_000
TOTAL_BODY_CAP = 10_000_000
SOCKET_TIMEOUT_SECONDS = 30
WHOLE_ATTEMPT_SECONDS = 367
USER_AGENT = "research-assistant-m20/0.1 (bounded-live-discovery)"
ROUTE_SCHEMA = "ra-literature-survey-m20-route-manifest-v1"
LEDGER_SCHEMA = "ra-literature-survey-m20-request-ledger-v1"
SUMMARY_SCHEMA = "ra-literature-survey-m20-campaign-summary-v1"
EXECUTION_MODES = frozenset({"synthetic", "live"})
CASE_ROOTS = {
    "arxiv_topic": "cases/topic",
    "topic_list": "cases/topic",
    "arxiv_seed": "cases/arxiv_seed",
    "direct_singleton": "cases/openalex",
    "forward_list": "cases/openalex",
}


class M20WorkerError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class M20ProviderUnavailable(RuntimeError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _arxiv_descriptor(*, route_kind: str) -> dict[str, Any]:
    common = [
        ["start", "0"],
        ["sortBy", "relevance"],
        ["sortOrder", "descending"],
    ]
    if route_kind == "arxiv_topic":
        query = [
            ["search_query", f"all:{TOPIC}"],
            ["max_results", "10"],
            *common,
        ]
        role = "topic_identity"
    elif route_kind == "arxiv_seed":
        query = [
            ["id_list", ARXIV_SEED],
            ["max_results", "5"],
            *common,
        ]
        role = "explicit_identity"
    else:
        raise M20WorkerError("invalid_arxiv_route")
    return {
        "schema_version": "ra-literature-survey-m20-arxiv-descriptor-v1",
        "provider": "arxiv",
        "route_kind": route_kind,
        "method": "GET",
        "host": "export.arxiv.org",
        "path_segments": ["api", "query"],
        "ordered_query_parameters": query,
        "response_role": role,
    }


def route_manifest() -> dict[str, Any]:
    descriptors = [
        _arxiv_descriptor(route_kind="arxiv_topic"),
        build_openalex_topic_descriptor(TOPIC),
        _arxiv_descriptor(route_kind="arxiv_seed"),
        build_openalex_direct_descriptor(OPENALEX_ID),
        build_openalex_forward_descriptor(OPENALEX_ID),
    ]
    routes = []
    for index, descriptor in enumerate(descriptors, start=1):
        routes.append({
            "request_index": index,
            "request_binding_sha256": _sha(canonical_json_bytes({
                "request_index": index,
                "descriptor": descriptor,
            })),
            "descriptor": descriptor,
        })
    return {
        "schema_version": ROUTE_SCHEMA,
        "status": "frozen",
        "topic": TOPIC,
        "arxiv_seed": f"arxiv:{ARXIV_SEED}",
        "openalex_id": f"openalex:{OPENALEX_ID}",
        "request_cap": REQUEST_CAP,
        "per_request_body_cap_bytes": PER_REQUEST_BODY_CAP,
        "total_body_cap_bytes": TOTAL_BODY_CAP,
        "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
        "whole_attempt_seconds": WHOLE_ATTEMPT_SECONDS,
        "redirect_cap": 0,
        "retry_cap": 0,
        "proxy_policy": "disabled",
        "credential_interface": CREDENTIAL_INTERFACE,
        "campaign_cost_cap_usd": format(CAMPAIGN_COST_CAP_USD, "f"),
        "outcome_automaton_sha256": outcome_automaton_sha256(),
        "routes": routes,
    }


def route_manifest_sha256() -> str:
    return _sha(canonical_json_bytes(route_manifest()))


def _atomic_write(path: Path, raw: bytes) -> None:
    if not path.parent.is_dir() or path.exists():
        raise M20WorkerError("artifact_path_invalid")
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
    finally:
        if temporary.exists():
            temporary.unlink()


def _prepare_root(root: Path) -> Path:
    if not isinstance(root, Path) or not root.is_absolute() or root.exists():
        raise M20WorkerError("output_root_not_fresh")
    if not root.parent.is_dir() or root.parent.resolve(strict=True) != root.parent:
        raise M20WorkerError("output_parent_invalid")
    root.mkdir(mode=0o700)
    if root.resolve(strict=True) != root:
        raise M20WorkerError("output_root_invalid")
    cases = root / "cases"
    cases.mkdir(mode=0o700)
    for relative in sorted(set(CASE_ROOTS.values())):
        case_root = root / relative
        case_root.mkdir(mode=0o700)
        if case_root.resolve(strict=True) != case_root:
            raise M20WorkerError("case_root_invalid")
        (case_root / "accepted_bodies").mkdir(mode=0o700)
    return root


def _case_root(root: Path, route_kind: str) -> Path:
    try:
        case_root = root / CASE_ROOTS[route_kind]
    except KeyError as exc:
        raise M20WorkerError("unknown_case_root") from exc
    if not case_root.is_dir() or case_root.resolve(strict=True) != case_root:
        raise M20WorkerError("case_root_invalid")
    return case_root


def _arxiv_payload(body: bytes, *, route_kind: str) -> dict[str, Any]:
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    }
    try:
        feed = ET.fromstring(body)
    except ET.ParseError as exc:
        raise M20WorkerError("arxiv_parser_invalid") from exc
    if feed.tag != "{http://www.w3.org/2005/Atom}feed":
        raise M20WorkerError("arxiv_envelope_invalid")

    def text(element: ET.Element, path: str) -> str | None:
        found = element.find(path, namespaces)
        if found is None or found.text is None:
            return None
        value = " ".join(found.text.split())
        return value or None

    totals = feed.findall("opensearch:totalResults", namespaces)
    if len(totals) != 1 or totals[0].text is None:
        raise M20WorkerError("arxiv_total_results_invalid")
    total_text = totals[0].text.strip()
    if not total_text.isascii() or not total_text.isdigit():
        raise M20WorkerError("arxiv_total_results_invalid")
    total = int(total_text)

    entries = feed.findall("atom:entry", namespaces)
    if total < len(entries):
        raise M20WorkerError("arxiv_total_results_invalid")

    records = []
    malformed = []
    for entry in entries:
        raw_id = text(entry, "atom:id") or ""
        title = text(entry, "atom:title")
        try:
            if not raw_id.startswith(("https://arxiv.org/abs/", "http://arxiv.org/abs/")):
                raise ValueError("noncanonical arXiv entry URL")
            arxiv_id = normalize_arxiv_id(raw_id)
            doi = normalize_doi(text(entry, "arxiv:doi"))
        except Exception:
            arxiv_id = None
            doi = None
        if arxiv_id is None or not title:
            malformed.append(_sha(ET.tostring(entry, encoding="utf-8")))
            continue
        authors = [
            value
            for author in entry.findall("atom:author", namespaces)
            if (value := text(author, "atom:name"))
        ]
        published = text(entry, "atom:published")
        primary = entry.find("arxiv:primary_category", namespaces)
        primary_category = primary.attrib.get("term") if primary is not None else None
        topic_query = route_kind == "arxiv_topic"
        records.append({
            "record_key": f"arxiv:{arxiv_id.casefold()}",
            "title": title,
            "authors": authors,
            "year": int(published[:4]) if published and published[:4].isdigit() else None,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "openalex_id": None,
            "landing_page_url": f"https://arxiv.org/abs/{arxiv_id}",
            "citation_count": None,
            "providers": ["arxiv"],
            "roles": ["seed"],
            "provider_records": [{
                "provider": "arxiv",
                "query_kind": "identity_resolution",
                "source_id": arxiv_id,
                "primary_category": primary_category,
                "published": published,
            }],
            "referenced_works": [],
            "query_provenance": [{
                "provider": "arxiv",
                "query_kind": "identity_resolution",
                "normalized_seed_key": TOPIC.casefold() if topic_query else None,
                "topic_query": topic_query,
            }],
        })
    cap = 10 if route_kind == "arxiv_topic" else 5
    return {
        "identity_view_status": "observed",
        "identity_records": records[:cap],
        "malformed_row_sha256s": sorted(set(malformed)),
        "identity_envelope_complete": True,
        "identity_cap_exceeded": total > cap or len(records) > cap,
        "frontier_view_status": "not_applicable",
        "frontier_target_ids": [],
        "frontier_reported_total": None,
        "frontier_continuation_visible": False,
    }


def _identity_state(
    *,
    provider: str,
    binding: str,
    status: str,
    body_record: dict[str, Any] | None,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if status == "not_dispatched_due_to_veto":
        status = "boundary_invalid"
    available = status == "available" and body_record is not None and payload is not None
    retained_body = body_record is not None
    return {
        "request_binding_sha256": binding,
        "provider": provider,
        "required": True,
        "status": status,
        "envelope_complete": payload["identity_envelope_complete"] if available else True,
        "cap_exceeded": payload["identity_cap_exceeded"] if available else False,
        "body_sha256": body_record["sha256"] if retained_body else None,
        "normalized_payload_sha256": body_record["normalized_payload_sha256"] if available else None,
        "records": payload["identity_records"] if available else [],
        "malformed_row_sha256s": payload["malformed_row_sha256s"] if available else [],
        "malformed_row_count": len(payload["malformed_row_sha256s"]) if available else 0,
    }


def _classifier_status(status: str) -> str:
    return "boundary_invalid" if status == "not_dispatched_due_to_veto" else status


def _real_arxiv_dispatch(descriptor: dict[str, Any]) -> bytes:
    query = urllib.parse.urlencode([tuple(item) for item in descriptor["ordered_query_parameters"]])
    url = urllib.parse.urlunsplit(("https", descriptor["host"], "/api/query", query, ""))
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/atom+xml", "User-Agent": USER_AGENT},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS) as response:
            if response.geturl() != url:
                raise M20WorkerError("arxiv_final_url_mismatch")
            body = response.read(PER_REQUEST_BODY_CAP + 1)
    except M20WorkerError:
        raise
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        raise M20ProviderUnavailable("arxiv_provider_unavailable") from exc
    if len(body) > PER_REQUEST_BODY_CAP:
        raise M20WorkerError("body_cap_exceeded")
    return body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        raise M20WorkerError("redirect_forbidden")

    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301
    http_error_308 = http_error_301


def _real_openalex_dispatch(request: urllib.request.Request) -> bytes:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS) as response:
        if response.geturl() != request.full_url:
            raise M20WorkerError("openalex_final_url_mismatch")
        body = response.read(PER_REQUEST_BODY_CAP + 1)
    if len(body) > PER_REQUEST_BODY_CAP:
        raise M20WorkerError("body_cap_exceeded")
    return body


def _closed_row(route: dict[str, Any], *, status: str, error_code: str | None) -> dict[str, Any]:
    return {
        "request_index": route["request_index"],
        "request_binding_sha256": route["request_binding_sha256"],
        "provider": route["descriptor"]["provider"],
        "route_kind": route["descriptor"]["route_kind"],
        "status": status,
        "error_code": error_code,
        "accepted_body": None,
        "cost_evidence": None,
    }


def _derive_case_evidence(
    *,
    root: Path,
    rows: list[dict[str, Any]],
    bodies: list[dict[str, Any]],
    replays: list[dict[str, Any]],
    payloads: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    case_inventories = []
    for relative in sorted(set(CASE_ROOTS.values())):
        inventory = validate_accepted_body_inventory(
            root / relative,
            body_records=[
                row["accepted_body"]
                for row in rows
                if row.get("accepted_body_root") == relative
            ],
        )
        case_inventories.append({"case_root": relative, "inventory": inventory})
    by_kind = {row["route_kind"]: row for row in rows}

    topic_states = [
        _identity_state(
            provider=provider,
            binding=by_kind[kind]["request_binding_sha256"],
            status=("available" if kind in payloads else by_kind[kind]["status"]),
            body_record=by_kind[kind]["accepted_body"],
            payload=payloads.get(kind),
        )
        for provider, kind in (("arxiv", "arxiv_topic"), ("openalex", "topic_list"))
    ]
    topic_outcome = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=sorted(topic_states, key=lambda row: row["request_binding_sha256"]),
    )
    seed_row = by_kind["arxiv_seed"]
    seed_outcome = classify_identity_outcome(
        case_kind="explicit_arxiv_seed",
        expected_identifier=f"arxiv:{ARXIV_SEED}",
        topic=None,
        request_states=[_identity_state(
            provider="arxiv",
            binding=seed_row["request_binding_sha256"],
            status="available" if "arxiv_seed" in payloads else seed_row["status"],
            body_record=seed_row["accepted_body"],
            payload=payloads.get("arxiv_seed"),
        )],
    )

    direct_row = by_kind["direct_singleton"]
    forward_row = by_kind["forward_list"]
    direct_payload = payloads.get("direct_singleton")
    direct_status = _classifier_status(
        "available" if direct_payload is not None else direct_row["status"]
    )
    openalex_identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier=OPENALEX_ID,
        topic=None,
        request_states=[_identity_state(
            provider="openalex",
            binding=direct_row["request_binding_sha256"],
            status=direct_status,
            body_record=direct_row["accepted_body"],
            payload=direct_payload,
        )],
    )
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=direct_row["request_binding_sha256"],
        origin_body_sha256=(direct_row["accepted_body"] or {}).get("sha256"),
        origin_normalized_payload_sha256=(direct_row["accepted_body"] or {}).get("normalized_payload_sha256"),
        request_status=(
            "boundary_invalid"
            if direct_payload is not None and direct_payload["frontier_view_status"] == "boundary_invalid"
            else direct_status
        ),
        body_integrity_valid=direct_payload is not None,
        target_ids=direct_payload["frontier_target_ids"] if direct_payload is not None else [],
        reported_total=direct_payload["frontier_reported_total"] if direct_payload is not None else None,
        continuation_visible=direct_payload["frontier_continuation_visible"] if direct_payload is not None else False,
        origin_identity_outcome=openalex_identity["outcome"],
        derived_from_identity_request=True,
    )
    forward_payload = payloads.get("forward_list")
    forward = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=forward_row["request_binding_sha256"],
        origin_body_sha256=(forward_row["accepted_body"] or {}).get("sha256"),
        origin_normalized_payload_sha256=(forward_row["accepted_body"] or {}).get("normalized_payload_sha256"),
        request_status=_classifier_status(
            "available" if forward_payload is not None else forward_row["status"]
        ),
        body_integrity_valid=forward_payload is not None,
        target_ids=forward_payload["frontier_target_ids"] if forward_payload is not None else [],
        reported_total=forward_payload["frontier_reported_total"] if forward_payload is not None else None,
        continuation_visible=forward_payload["frontier_continuation_visible"] if forward_payload is not None else False,
        origin_identity_outcome=openalex_identity["outcome"],
        dispatched=forward_row["status"] != "not_dispatched_due_to_veto",
    )
    openalex_outcome = compose_openalex_case_outcome(
        identity=openalex_identity,
        backward=backward,
        forward=forward,
        accepted_body_root=root / CASE_ROOTS["direct_singleton"],
        accepted_body_records=[
            row
            for row in bodies
            if row["request_binding_sha256"] in {
                direct_row["request_binding_sha256"],
                forward_row["request_binding_sha256"],
            }
        ],
        replay_records=[
            row
            for row in replays
            if row["request_binding_sha256"] in {
                direct_row["request_binding_sha256"],
                forward_row["request_binding_sha256"],
            }
        ],
    )
    campaign_validity = (
        "boundary_invalid"
        if topic_outcome["outcome"] == "boundary_invalid"
        or seed_outcome["outcome"] == "boundary_invalid"
        or openalex_outcome["global_status"] == "boundary_invalid"
        else "closed"
    )
    inventory_ledger = {
        "schema_version": "ra-literature-survey-m20-case-inventory-ledger-v1",
        "status": "passed",
        "cases": case_inventories,
    }
    replay_ledger = {
        "schema_version": "ra-literature-survey-m20-replay-ledger-v1",
        "status": "passed",
        "records": sorted(replays, key=canonical_json_bytes),
    }
    identity_outcomes = {
        "schema_version": "ra-literature-survey-m20-identity-outcomes-v1",
        "topic_bootstrap": topic_outcome,
        "explicit_arxiv_seed": seed_outcome,
        "openalex_case": openalex_outcome,
    }
    return inventory_ledger, replay_ledger, identity_outcomes, campaign_validity


def _read_artifact(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M20WorkerError("published_artifact_invalid") from exc


def _validate_published_run(root: Path, *, execution_mode: str) -> dict[str, Any]:
    if execution_mode not in EXECUTION_MODES or not root.is_absolute() or not root.is_dir():
        raise M20WorkerError("published_root_invalid")
    manifest = _read_artifact(root / "route_manifest.json")
    ledger = _read_artifact(root / "request_ledger.json")
    published_inventory = _read_artifact(root / "accepted_body_inventory.json")
    published_replay = _read_artifact(root / "replay_ledger.json")
    published_outcomes = _read_artifact(root / "identity_outcomes.json")
    summary = _read_artifact(root / "campaign_summary.json")
    if manifest != route_manifest() or not isinstance(ledger, dict):
        raise M20WorkerError("published_manifest_invalid")
    if set(ledger) != {
        "schema_version", "status", "route_manifest_sha256", "request_cap",
        "rows", "accepted_body_count", "accepted_body_bytes", "execution_mode",
        "credential_interface_lookup_count", "real_credential_accessed", "network_used",
    }:
        raise M20WorkerError("published_ledger_shape_invalid")
    exact_base_keys = {
        "request_index", "request_binding_sha256", "provider", "route_kind",
        "status", "error_code", "accepted_body", "cost_evidence",
    }
    rows = ledger.get("rows")
    routes = manifest["routes"]
    if not isinstance(rows, list) or len(rows) != REQUEST_CAP:
        raise M20WorkerError("published_ledger_invalid")
    bodies: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    allowed_statuses = {"available", "unavailable", "boundary_invalid", "not_dispatched_due_to_veto"}
    last_cost_evidence: dict[str, Any] | None = None
    prior_reserved = Decimal("0")
    prior_reconciled = Decimal("0")
    prior_dispatch_count = 0
    for row, route in zip(rows, routes):
        expected = route["descriptor"]
        has_body = row.get("accepted_body") is not None
        expected_keys = exact_base_keys | ({"accepted_body_root"} if has_body else set())
        if (
            not isinstance(row, dict)
            or set(row) != expected_keys
            or row.get("request_index") != route["request_index"]
            or row.get("request_binding_sha256") != route["request_binding_sha256"]
            or row.get("provider") != expected["provider"]
            or row.get("route_kind") != expected["route_kind"]
            or row.get("status") not in allowed_statuses
        ):
            raise M20WorkerError("published_request_row_invalid")
        if expected["provider"] == "arxiv" and row["cost_evidence"] is not None:
            raise M20WorkerError("published_cost_row_invalid")
        if row["status"] == "available" and row["error_code"] is not None:
            raise M20WorkerError("published_request_error_invalid")
        if row["status"] == "unavailable" and row["error_code"] != "arxiv_dispatch_failed":
            raise M20WorkerError("published_request_error_invalid")
        if row["status"] == "boundary_invalid" and not isinstance(row["error_code"], str):
            raise M20WorkerError("published_request_error_invalid")
        if row["status"] == "not_dispatched_due_to_veto" and row["error_code"] != "campaign_hard_stop":
            raise M20WorkerError("published_request_error_invalid")
        if expected["provider"] == "openalex" and row["status"] != "not_dispatched_due_to_veto":
            evidence = row["cost_evidence"]
            evidence_keys = {
                "schema_version", "status", "error_code", "provider", "route_kind",
                "descriptor_sha256", "credential_interface", "credential_source_kind",
                "credential_present", "credential_persisted", "authenticated_url_persisted",
                "predicted_cost_usd", "observed_cost_usd", "campaign_cost_cap_usd",
                "reserved_cost_usd", "reconciled_cost_usd", "dispatch_count", "cost_state",
                "cost_block_code", "allowance_accounting",
            }
            if not isinstance(evidence, dict) or set(evidence) != evidence_keys:
                raise M20WorkerError("published_cost_evidence_invalid")
            expected_cost_decimal = ROUTE_COST_USD[row["route_kind"]]
            expected_cost = format(expected_cost_decimal, "f")
            fixed_cost = {
                "schema_version": "ra-survey-m20b2-openalex-credential-cost-evidence-v1",
                "provider": "openalex",
                "route_kind": row["route_kind"],
                "descriptor_sha256": _sha(canonical_json_bytes(expected)),
                "credential_interface": CREDENTIAL_INTERFACE,
                "credential_source_kind": CREDENTIAL_SOURCE_KIND,
                "credential_persisted": False,
                "authenticated_url_persisted": False,
                "predicted_cost_usd": expected_cost,
                "campaign_cost_cap_usd": format(CAMPAIGN_COST_CAP_USD, "f"),
                "allowance_accounting": "usage_cost_counts_regardless_of_daily_or_prepaid_coverage",
            }
            if any(evidence.get(key) != value for key, value in fixed_cost.items()):
                raise M20WorkerError("published_cost_evidence_invalid")
            try:
                reserved = Decimal(evidence["reserved_cost_usd"])
                reconciled = Decimal(evidence["reconciled_cost_usd"])
                dispatch_count = evidence["dispatch_count"]
            except (InvalidOperation, TypeError, ValueError):
                raise M20WorkerError("published_cost_evidence_invalid") from None
            if (
                type(dispatch_count) is not int
                or not reserved.is_finite()
                or not reconciled.is_finite()
                or min(reserved, reconciled) < 0
                or reconciled > reserved
                or reserved > CAMPAIGN_COST_CAP_USD
                or evidence["cost_state"] not in {"open", "blocked"}
                or type(evidence["credential_present"]) is not bool
            ):
                raise M20WorkerError("published_cost_evidence_invalid")
            evidence_statuses = {
                "blocked_preflight",
                "blocked_before_dispatch",
                "blocked_after_dispatch",
                "completed",
            }
            if evidence["status"] not in evidence_statuses:
                raise M20WorkerError("published_cost_evidence_invalid")
            dispatched_statuses = {"completed", "blocked_after_dispatch"}
            dispatched = evidence["status"] in dispatched_statuses
            expected_reserved = prior_reserved + (expected_cost_decimal if dispatched else Decimal("0"))
            expected_dispatch_count = prior_dispatch_count + (1 if dispatched else 0)
            if reserved != expected_reserved or dispatch_count != expected_dispatch_count:
                raise M20WorkerError("published_cost_evidence_invalid")
            if evidence["status"] == "completed":
                expected_reconciled = prior_reconciled + expected_cost_decimal
                if (
                    evidence["error_code"] is not None
                    or evidence["observed_cost_usd"] != expected_cost
                    or evidence["credential_present"] is not True
                    or reconciled != expected_reconciled
                    or evidence["cost_state"] != "open"
                    or evidence["cost_block_code"] is not None
                ):
                    raise M20WorkerError("published_cost_evidence_invalid")
                allowed_row_states = {
                    ("available", None),
                    ("boundary_invalid", "openalex_parse_failed"),
                    ("boundary_invalid", "total_body_cap_exceeded"),
                }
                if (row["status"], row["error_code"]) not in allowed_row_states:
                    raise M20WorkerError("published_cost_evidence_invalid")
            elif evidence["status"] == "blocked_after_dispatch":
                error_to_block = {
                    "dispatch_failed_closed": "dispatch_cost_unreconciled",
                    "response_type_invalid": "dispatch_cost_unreconciled",
                    "credential_echoed_in_response": "credential_echoed_in_response",
                    "cost_contradiction": "cost_contradiction",
                    "response_cost_unreconciled": "response_cost_unreconciled",
                    "cost_state_changed_during_dispatch": "cost_state_changed_during_dispatch",
                    "invalid_cost_state": "invalid_cost_state",
                    "invalid_dispatch_reservation": "invalid_dispatch_reservation",
                    "campaign_cost_cap_exceeded": "campaign_cost_cap_exceeded",
                }
                null_observed_errors = {
                    "dispatch_failed_closed",
                    "response_type_invalid",
                    "credential_echoed_in_response",
                    "response_cost_unreconciled",
                }
                required_observed_errors = {
                    "cost_state_changed_during_dispatch",
                    "invalid_cost_state",
                    "invalid_dispatch_reservation",
                }
                observed_raw = evidence["observed_cost_usd"]
                observed: Decimal | None = None
                if observed_raw is not None:
                    if not isinstance(observed_raw, str):
                        raise M20WorkerError("published_cost_evidence_invalid")
                    try:
                        observed = Decimal(observed_raw)
                    except InvalidOperation:
                        raise M20WorkerError("published_cost_evidence_invalid") from None
                    if (
                        not observed.is_finite()
                        or observed < 0
                        or format(observed, "f") != observed_raw
                    ):
                        raise M20WorkerError("published_cost_evidence_invalid")
                error_code = evidence["error_code"]
                if (
                    reconciled != prior_reconciled
                    or evidence["credential_present"] is not True
                    or evidence["cost_state"] != "blocked"
                    or error_code not in error_to_block
                    or evidence["cost_block_code"] != error_to_block[error_code]
                    or (error_code in null_observed_errors and observed_raw is not None)
                    or (
                        error_code == "cost_contradiction"
                        and (observed is None or observed == expected_cost_decimal)
                    )
                    or (
                        error_code in required_observed_errors
                        and observed is None
                    )
                    or (
                        error_code == "campaign_cost_cap_exceeded"
                        and observed != expected_cost_decimal
                    )
                ):
                    raise M20WorkerError("published_cost_evidence_invalid")
            elif evidence["status"] == "blocked_preflight":
                if (
                    evidence["error_code"] != "descriptor_or_cost_preflight_invalid"
                    or evidence["credential_present"] is not False
                    or reconciled != prior_reconciled
                    or reserved != prior_reserved
                    or evidence["observed_cost_usd"] is not None
                    or evidence["cost_state"] != "open"
                    or evidence["cost_block_code"] is not None
                ):
                    raise M20WorkerError("published_cost_evidence_invalid")
            else:
                before_dispatch_states = {
                    "credential_lookup_failed": (False, "open", None),
                    "ambiguous_credential": (False, "open", None),
                    "invalid_credential": (False, "open", None),
                    "request_construction_failed": (True, "open", None),
                    "invalid_cost_state": (True, "blocked", "invalid_cost_state"),
                    "cost_state_changed_after_credential_lookup": (
                        True,
                        "blocked",
                        "cost_state_changed_after_credential_lookup",
                    ),
                }
                expected_before_state = before_dispatch_states.get(evidence["error_code"])
                if (
                    reconciled != prior_reconciled
                    or reserved != prior_reserved
                    or evidence["observed_cost_usd"] is not None
                    or expected_before_state is None
                    or (
                        evidence["credential_present"],
                        evidence["cost_state"],
                        evidence["cost_block_code"],
                    ) != expected_before_state
                ):
                    raise M20WorkerError("published_cost_evidence_invalid")
            if evidence["status"] != "completed" and row["status"] != "boundary_invalid":
                raise M20WorkerError("published_cost_evidence_invalid")
            if evidence["status"] != "completed" and row["error_code"] != evidence["error_code"]:
                raise M20WorkerError("published_cost_evidence_invalid")
            if evidence["cost_state"] == "open" and reserved != reconciled:
                raise M20WorkerError("published_cost_evidence_invalid")
            if evidence["cost_state"] == "blocked" and not isinstance(evidence["cost_block_code"], str):
                raise M20WorkerError("published_cost_evidence_invalid")
            prior_reserved = reserved
            prior_reconciled = reconciled
            prior_dispatch_count = dispatch_count
            last_cost_evidence = evidence
        elif expected["provider"] == "openalex" and row["cost_evidence"] is not None:
            raise M20WorkerError("published_cost_row_invalid")
        if row["status"] == "available" and not has_body:
            raise M20WorkerError("published_available_body_missing")
        if row["status"] in {"unavailable", "not_dispatched_due_to_veto"} and has_body:
            raise M20WorkerError("published_unavailable_body_present")
        if not has_body:
            continue
        relative = CASE_ROOTS[row["route_kind"]]
        if row.get("accepted_body_root") != relative:
            raise M20WorkerError("published_case_root_invalid")
        body_record = row["accepted_body"]
        bodies.append(body_record)
        if body_record.get("normalized_payload_sha256") is None:
            if row["status"] != "boundary_invalid":
                raise M20WorkerError("published_unbound_body_invalid")
            continue
        parser = {
            "arxiv_topic": lambda raw: _arxiv_payload(raw, route_kind="arxiv_topic"),
            "topic_list": lambda raw: parse_openalex_topic_response(raw, topic=TOPIC),
            "arxiv_seed": lambda raw: _arxiv_payload(raw, route_kind="arxiv_seed"),
            "direct_singleton": lambda raw: parse_openalex_direct_response(raw, expected_openalex_id=OPENALEX_ID),
            "forward_list": parse_openalex_forward_response,
        }[row["route_kind"]]
        replay = replay_accepted_body(root / relative, body_record=body_record, parser=parser)
        replays.append(replay)
        payloads[row["route_kind"]] = replay["normalized_payload"]
    inventory, replay_ledger, outcomes, campaign_validity = _derive_case_evidence(
        root=root,
        rows=rows,
        bodies=bodies,
        replays=replays,
        payloads=payloads,
    )
    if (
        published_inventory != inventory
        or published_replay != replay_ledger
        or published_outcomes != outcomes
    ):
        raise M20WorkerError("published_case_evidence_mismatch")
    accepted_bytes = sum(row["size_bytes"] for row in bodies)
    openalex_rows = [row for row in rows if row["provider"] == "openalex"]
    expected_lookup_count = sum(row["status"] != "not_dispatched_due_to_veto" for row in openalex_rows)
    credential_present = any(
        (row.get("cost_evidence") or {}).get("credential_present") is True
        for row in openalex_rows
    )
    if (
        ledger.get("schema_version") != LEDGER_SCHEMA
        or ledger.get("status") != "complete"
        or ledger.get("route_manifest_sha256") != route_manifest_sha256()
        or ledger.get("request_cap") != REQUEST_CAP
        or ledger.get("accepted_body_count") != len(bodies)
        or ledger.get("accepted_body_bytes") != accepted_bytes
        or accepted_bytes > TOTAL_BODY_CAP
        or ledger.get("execution_mode") != execution_mode
        or ledger.get("credential_interface_lookup_count") != expected_lookup_count
        or ledger.get("real_credential_accessed") is not (execution_mode == "live" and credential_present)
        or ledger.get("network_used") is not (execution_mode == "live")
    ):
        raise M20WorkerError("published_ledger_accounting_invalid")
    if set(summary) != {
        "schema_version", "status", "route_manifest_sha256", "request_ledger_sha256",
        "accepted_body_inventory_sha256", "replay_ledger_sha256", "identity_outcomes_sha256",
        "topic_identity_outcome", "explicit_arxiv_identity_outcome", "openalex_case",
        "campaign_validity", "cost_evidence", "accepted_body_inventory_count",
        "accepted_body_inventory_bytes", "execution_mode", "credential_interface_lookup_count",
        "network_used", "real_credential_accessed", "nonclaims",
    }:
        raise M20WorkerError("published_summary_shape_invalid")
    final_cost = {
        key: last_cost_evidence[key]
        for key in (
            "campaign_cost_cap_usd", "reserved_cost_usd", "reconciled_cost_usd",
            "dispatch_count", "cost_state", "cost_block_code", "allowance_accounting",
        )
    } if last_cost_evidence is not None else {
        "campaign_cost_cap_usd": format(CAMPAIGN_COST_CAP_USD, "f"),
        "reserved_cost_usd": "0",
        "reconciled_cost_usd": "0",
        "dispatch_count": 0,
        "cost_state": "open",
        "cost_block_code": None,
        "allowance_accounting": "usage_cost_counts_regardless_of_daily_or_prepaid_coverage",
    }
    if (
        summary.get("schema_version") != SUMMARY_SCHEMA
        or summary.get("status") != f"{execution_mode}_complete"
        or summary.get("route_manifest_sha256") != route_manifest_sha256()
        or summary.get("request_ledger_sha256") != _sha(canonical_json_bytes(ledger))
        or summary.get("accepted_body_inventory_sha256") != _sha(canonical_json_bytes(inventory))
        or summary.get("replay_ledger_sha256") != _sha(canonical_json_bytes(replay_ledger))
        or summary.get("identity_outcomes_sha256") != _sha(canonical_json_bytes(outcomes))
        or summary.get("topic_identity_outcome") != outcomes["topic_bootstrap"]["outcome"]
        or summary.get("explicit_arxiv_identity_outcome") != outcomes["explicit_arxiv_seed"]["outcome"]
        or summary.get("openalex_case") != outcomes["openalex_case"]
        or summary.get("campaign_validity") != campaign_validity
        or summary.get("cost_evidence") != final_cost
        or summary.get("accepted_body_inventory_count") != len(bodies)
        or summary.get("accepted_body_inventory_bytes") != accepted_bytes
        or summary.get("execution_mode") != execution_mode
        or summary.get("credential_interface_lookup_count") != expected_lookup_count
        or summary.get("real_credential_accessed") is not ledger.get("real_credential_accessed")
        or summary.get("network_used") is not ledger.get("network_used")
        or not isinstance(summary.get("nonclaims"), list)
        or "m20_or_north_star_completion" not in summary["nonclaims"]
    ):
        raise M20WorkerError("published_summary_invalid")
    return {
        "status": "passed",
        "campaign_validity": campaign_validity,
        "accepted_body_count": len(bodies),
        "accepted_body_bytes": accepted_bytes,
    }


def validate_published_run(root: Path, *, execution_mode: str) -> dict[str, Any]:
    try:
        return _validate_published_run(root, execution_mode=execution_mode)
    except M20WorkerError:
        raise
    except (MissionStateError, KeyError, TypeError, ValueError, OSError) as exc:
        raise M20WorkerError("published_run_replay_invalid") from exc


def run_matrix(
    *,
    output_root: Path,
    credential_getter: Callable[[str], Any],
    arxiv_dispatch: Callable[[dict[str, Any]], bytes],
    openalex_dispatch: Callable[[urllib.request.Request], bytes],
    execution_mode: str = "synthetic",
) -> dict[str, Any]:
    if execution_mode not in EXECUTION_MODES:
        raise M20WorkerError("execution_mode_invalid")
    root = _prepare_root(output_root)
    manifest = route_manifest()
    _atomic_write(root / "route_manifest.json", pretty_json_bytes(manifest))
    budget = CampaignCostBudget()
    rows: list[dict[str, Any]] = []
    bodies: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    accepted_body_bytes = 0
    started = time.monotonic()
    hard_stop = False
    credential_lookup_count = 0
    arxiv_dispatch_count = 0
    openalex_dispatch_count = 0

    def counted_credential_getter(name: str) -> Any:
        nonlocal credential_lookup_count
        credential_lookup_count += 1
        return credential_getter(name)

    def counted_arxiv_dispatch(descriptor: dict[str, Any]) -> bytes:
        nonlocal arxiv_dispatch_count
        arxiv_dispatch_count += 1
        return arxiv_dispatch(descriptor)

    def counted_openalex_dispatch(request: urllib.request.Request) -> bytes:
        nonlocal openalex_dispatch_count
        openalex_dispatch_count += 1
        return openalex_dispatch(request)

    for route in manifest["routes"]:
        descriptor = route["descriptor"]
        binding = route["request_binding_sha256"]
        case_root = _case_root(root, descriptor["route_kind"])
        if hard_stop or time.monotonic() - started > WHOLE_ATTEMPT_SECONDS:
            rows.append(_closed_row(route, status="not_dispatched_due_to_veto", error_code="campaign_hard_stop"))
            continue

        if descriptor["provider"] == "arxiv":
            try:
                body = counted_arxiv_dispatch(descriptor)
                if not isinstance(body, bytes) or len(body) > PER_REQUEST_BODY_CAP:
                    raise M20WorkerError("body_cap_exceeded")
            except M20ProviderUnavailable:
                row = _closed_row(route, status="unavailable", error_code="arxiv_dispatch_failed")
            except Exception:
                row = _closed_row(route, status="boundary_invalid", error_code="arxiv_dispatch_boundary_invalid")
            else:
                if accepted_body_bytes + len(body) > TOTAL_BODY_CAP:
                    row = _closed_row(route, status="boundary_invalid", error_code="total_body_cap_exceeded")
                    hard_stop = True
                    rows.append(row)
                    continue
                body_record = write_accepted_body(case_root, request_binding_sha256=binding, body=body)
                accepted_body_bytes += len(body)
                row = _closed_row(route, status="boundary_invalid", error_code="arxiv_parse_failed")
                row["accepted_body"] = body_record
                row["accepted_body_root"] = CASE_ROOTS[descriptor["route_kind"]]
                bodies.append(body_record)
                try:
                    payload = _arxiv_payload(body, route_kind=descriptor["route_kind"])
                    body_record = bind_normalized_payload(body_record, payload)
                    replay = replay_accepted_body(
                        case_root,
                        body_record=body_record,
                        parser=lambda raw, kind=descriptor["route_kind"]: _arxiv_payload(raw, route_kind=kind),
                    )
                except Exception:
                    pass
                else:
                    row = _closed_row(route, status="available", error_code=None)
                    row["accepted_body"] = body_record
                    row["accepted_body_root"] = CASE_ROOTS[descriptor["route_kind"]]
                    bodies[-1] = body_record
                    replays.append(replay)
                    payloads[descriptor["route_kind"]] = payload
        else:
            body, evidence = execute_authenticated_openalex_request(
                descriptor,
                credential_getter=counted_credential_getter,
                credential_source_kind=CREDENTIAL_SOURCE_KIND,
                dispatch=counted_openalex_dispatch,
                budget=budget,
            )
            row = _closed_row(
                route,
                status="available" if body is not None else "boundary_invalid",
                error_code=evidence["error_code"],
            )
            row["cost_evidence"] = evidence
            if body is not None:
                parser = {
                    "topic_list": lambda raw: parse_openalex_topic_response(raw, topic=TOPIC),
                    "direct_singleton": lambda raw: parse_openalex_direct_response(raw, expected_openalex_id=OPENALEX_ID),
                    "forward_list": parse_openalex_forward_response,
                }[descriptor["route_kind"]]
                if accepted_body_bytes + len(body) > TOTAL_BODY_CAP:
                    row["status"] = "boundary_invalid"
                    row["error_code"] = "total_body_cap_exceeded"
                    hard_stop = True
                    rows.append(row)
                    continue
                body_record = write_accepted_body(case_root, request_binding_sha256=binding, body=body)
                accepted_body_bytes += len(body)
                row["accepted_body_root"] = CASE_ROOTS[descriptor["route_kind"]]
                bodies.append(body_record)
                try:
                    payload = parser(body)
                    body_record = bind_normalized_payload(body_record, payload)
                    replay = replay_accepted_body(case_root, body_record=body_record, parser=parser)
                except Exception:
                    row["status"] = "boundary_invalid"
                    row["error_code"] = "openalex_parse_failed"
                    row["accepted_body"] = body_record
                else:
                    row["accepted_body"] = body_record
                    bodies[-1] = body_record
                    replays.append(replay)
                    payloads[descriptor["route_kind"]] = payload
                    if (
                        descriptor["route_kind"] == "direct_singleton"
                        and payload["frontier_view_status"] == "boundary_invalid"
                    ):
                        hard_stop = True
            if evidence["cost_state"] == "blocked":
                hard_stop = True
        if row["status"] == "boundary_invalid":
            hard_stop = True
        rows.append(row)

    if len(rows) != REQUEST_CAP:
        raise M20WorkerError("request_ledger_incomplete")
    case_inventories = []
    for relative in sorted(set(CASE_ROOTS.values())):
        inventory = validate_accepted_body_inventory(
            root / relative,
            body_records=[
                row["accepted_body"]
                for row in rows
                if row.get("accepted_body_root") == relative
            ],
        )
        case_inventories.append({"case_root": relative, "inventory": inventory})
    by_kind = {row["route_kind"]: row for row in rows}

    topic_states = [
        _identity_state(
            provider=provider,
            binding=by_kind[kind]["request_binding_sha256"],
            status=("available" if kind in payloads else by_kind[kind]["status"]),
            body_record=by_kind[kind]["accepted_body"],
            payload=payloads.get(kind),
        )
        for provider, kind in (("arxiv", "arxiv_topic"), ("openalex", "topic_list"))
    ]
    topic_outcome = classify_identity_outcome(
        case_kind="topic_bootstrap",
        expected_identifier=None,
        topic=TOPIC,
        request_states=sorted(topic_states, key=lambda row: row["request_binding_sha256"]),
    )
    seed_row = by_kind["arxiv_seed"]
    seed_outcome = classify_identity_outcome(
        case_kind="explicit_arxiv_seed",
        expected_identifier=f"arxiv:{ARXIV_SEED}",
        topic=None,
        request_states=[_identity_state(
            provider="arxiv",
            binding=seed_row["request_binding_sha256"],
            status="available" if "arxiv_seed" in payloads else seed_row["status"],
            body_record=seed_row["accepted_body"],
            payload=payloads.get("arxiv_seed"),
        )],
    )

    direct_row = by_kind["direct_singleton"]
    forward_row = by_kind["forward_list"]
    direct_payload = payloads.get("direct_singleton")
    direct_status = _classifier_status(
        "available" if direct_payload is not None else direct_row["status"]
    )
    openalex_identity = classify_identity_outcome(
        case_kind="explicit_openalex",
        expected_identifier=OPENALEX_ID,
        topic=None,
        request_states=[_identity_state(
            provider="openalex",
            binding=direct_row["request_binding_sha256"],
            status=direct_status,
            body_record=direct_row["accepted_body"],
            payload=direct_payload,
        )],
    )
    backward = classify_frontier_attempt(
        direction="backward",
        origin_request_binding_sha256=direct_row["request_binding_sha256"],
        origin_body_sha256=(direct_row["accepted_body"] or {}).get("sha256"),
        origin_normalized_payload_sha256=(direct_row["accepted_body"] or {}).get("normalized_payload_sha256"),
        request_status=(
            "boundary_invalid"
            if direct_payload is not None and direct_payload["frontier_view_status"] == "boundary_invalid"
            else direct_status
        ),
        body_integrity_valid=direct_payload is not None,
        target_ids=direct_payload["frontier_target_ids"] if direct_payload is not None else [],
        reported_total=direct_payload["frontier_reported_total"] if direct_payload is not None else None,
        continuation_visible=direct_payload["frontier_continuation_visible"] if direct_payload is not None else False,
        origin_identity_outcome=openalex_identity["outcome"],
        derived_from_identity_request=True,
    )
    forward_payload = payloads.get("forward_list")
    forward = classify_frontier_attempt(
        direction="forward",
        origin_request_binding_sha256=forward_row["request_binding_sha256"],
        origin_body_sha256=(forward_row["accepted_body"] or {}).get("sha256"),
        origin_normalized_payload_sha256=(forward_row["accepted_body"] or {}).get("normalized_payload_sha256"),
        request_status=_classifier_status(
            "available" if forward_payload is not None else forward_row["status"]
        ),
        body_integrity_valid=forward_payload is not None,
        target_ids=forward_payload["frontier_target_ids"] if forward_payload is not None else [],
        reported_total=forward_payload["frontier_reported_total"] if forward_payload is not None else None,
        continuation_visible=forward_payload["frontier_continuation_visible"] if forward_payload is not None else False,
        origin_identity_outcome=openalex_identity["outcome"],
        dispatched=forward_row["status"] != "not_dispatched_due_to_veto",
    )
    openalex_outcome = compose_openalex_case_outcome(
        identity=openalex_identity,
        backward=backward,
        forward=forward,
        accepted_body_root=root / CASE_ROOTS["direct_singleton"],
        accepted_body_records=[
            row
            for row in bodies
            if row["request_binding_sha256"] in {
                direct_row["request_binding_sha256"],
                forward_row["request_binding_sha256"],
            }
        ],
        replay_records=[
            row
            for row in replays
            if row["request_binding_sha256"] in {
                direct_row["request_binding_sha256"],
                forward_row["request_binding_sha256"],
            }
        ],
    )
    campaign_validity = (
        "boundary_invalid"
        if topic_outcome["outcome"] == "boundary_invalid"
        or seed_outcome["outcome"] == "boundary_invalid"
        or openalex_outcome["global_status"] == "boundary_invalid"
        else "closed"
    )
    credential_present = any(
        (row.get("cost_evidence") or {}).get("credential_present") is True
        for row in rows
    )
    inventory_ledger = {
        "schema_version": "ra-literature-survey-m20-case-inventory-ledger-v1",
        "status": "passed",
        "cases": case_inventories,
    }
    replay_ledger = {
        "schema_version": "ra-literature-survey-m20-replay-ledger-v1",
        "status": "passed",
        "records": sorted(replays, key=canonical_json_bytes),
    }
    identity_outcomes = {
        "schema_version": "ra-literature-survey-m20-identity-outcomes-v1",
        "topic_bootstrap": topic_outcome,
        "explicit_arxiv_seed": seed_outcome,
        "openalex_case": openalex_outcome,
    }
    _atomic_write(root / "accepted_body_inventory.json", pretty_json_bytes(inventory_ledger))
    _atomic_write(root / "replay_ledger.json", pretty_json_bytes(replay_ledger))
    _atomic_write(root / "identity_outcomes.json", pretty_json_bytes(identity_outcomes))
    ledger = {
        "schema_version": LEDGER_SCHEMA,
        "status": "complete",
        "route_manifest_sha256": route_manifest_sha256(),
        "request_cap": REQUEST_CAP,
        "rows": rows,
        "accepted_body_count": len(bodies),
        "accepted_body_bytes": sum(row["size_bytes"] for row in bodies),
        "execution_mode": execution_mode,
        "credential_interface_lookup_count": credential_lookup_count,
        "real_credential_accessed": execution_mode == "live" and credential_present,
        "network_used": execution_mode == "live" and (arxiv_dispatch_count + openalex_dispatch_count) > 0,
    }
    _atomic_write(root / "request_ledger.json", pretty_json_bytes(ledger))
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "status": f"{execution_mode}_complete",
        "route_manifest_sha256": route_manifest_sha256(),
        "request_ledger_sha256": _sha(canonical_json_bytes(ledger)),
        "accepted_body_inventory_sha256": _sha(canonical_json_bytes(inventory_ledger)),
        "replay_ledger_sha256": _sha(canonical_json_bytes(replay_ledger)),
        "identity_outcomes_sha256": _sha(canonical_json_bytes(identity_outcomes)),
        "topic_identity_outcome": topic_outcome["outcome"],
        "explicit_arxiv_identity_outcome": seed_outcome["outcome"],
        "openalex_case": openalex_outcome,
        "campaign_validity": campaign_validity,
        "cost_evidence": budget.evidence(),
        "accepted_body_inventory_count": len(bodies),
        "accepted_body_inventory_bytes": sum(row["size_bytes"] for row in bodies),
        "execution_mode": execution_mode,
        "credential_interface_lookup_count": credential_lookup_count,
        "network_used": execution_mode == "live" and (arxiv_dispatch_count + openalex_dispatch_count) > 0,
        "real_credential_accessed": execution_mode == "live" and credential_present,
        "nonclaims": [
            "provider_behavior_or_readiness",
            "real_key_availability_or_authority",
            "actual_account_balance_or_billing",
            "literature_completeness",
            "m20_or_north_star_completion",
        ],
    }
    _atomic_write(root / "campaign_summary.json", pretty_json_bytes(summary))
    return summary


def _environment_getter(name: str) -> str | None:
    if name != CREDENTIAL_INTERFACE:
        raise M20WorkerError("wrong_credential_interface")
    return os.environ.get(CREDENTIAL_INTERFACE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    run_matrix(
        output_root=args.output_root.resolve(strict=False),
        credential_getter=_environment_getter,
        arxiv_dispatch=_real_arxiv_dispatch,
        openalex_dispatch=_real_openalex_dispatch,
        execution_mode="live",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARXIV_SEED",
    "OPENALEX_ID",
    "REQUEST_CAP",
    "TOPIC",
    "route_manifest",
    "route_manifest_sha256",
    "run_matrix",
]
