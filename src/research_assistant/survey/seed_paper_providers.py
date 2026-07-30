"""Bounded metadata providers for topic-to-seed candidate discovery."""

from __future__ import annotations

import json
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.topic_contract import plan_discovery_routes, topic_contract_sha256


PROVIDER_BUNDLE_SCHEMA = "ra-survey-seed-provider-bundle-v1"
PROVIDER_BUNDLE_SCHEMA_V2 = "ra-survey-seed-provider-bundle-v2"
PROVIDER_OBSERVATIONS_SCHEMA = "ra-survey-seed-provider-observations-v1"
PROVIDER_OBSERVATIONS_SCHEMA_V2 = "ra-survey-seed-provider-observations-v2"
SUPPORTED_PROVIDERS = ("crossref", "openalex", "semantic_scholar")
GOOGLE_SCHOLAR_STATUS = "unsupported_no_public_api"
_STATUSES = {"available", "empty", "capped", "not_available"}
_STATUSES_V2 = {
    "available", "empty", "capped", "rate_limited", "transport_failed",
    "http_failed", "skipped_after_provider_veto", "unsupported_exact_route",
}
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")
_ARXIV_RE = re.compile(r"(?:arxiv:)?([a-z-]+(?:\.[a-z-]+)?/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?\Z", re.I)


def _fail(code: str, message: str) -> None:
    raise MissionStateError(code, message)


def _text(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail("invalid_seed_provider_bundle", f"{field} must be nonempty text")
    return " ".join(value.split())


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        _fail("invalid_seed_provider_bundle", f"{label} fields are not exact")
    return value


def _status(value: Any, field: str) -> str:
    value = _text(value, field)
    if value not in _STATUSES:
        _fail("invalid_seed_provider_bundle", f"{field} is unsupported")
    return value


def normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().casefold()
    for prefix in _DOI_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.rstrip(" .")
    return text if text.startswith("10.") and "/" in text and " " not in text else None


def normalize_arxiv(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().casefold().removeprefix("arxiv:")
    for marker in ("arxiv.org/abs/", "arxiv.org/pdf/"):
        if marker in text:
            text = text.split(marker, 1)[1]
            break
    text = text.rstrip("/").removesuffix(".pdf")
    match = _ARXIV_RE.fullmatch(text)
    return match.group(1).casefold() if match else None


def _year(value: Any) -> int | None:
    if type(value) is int and 1000 <= value <= 3000:
        return value
    return None


def _citation(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _authors(values: Any, *, provider: str) -> list[str]:
    if not isinstance(values, list):
        return []
    rows: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        if provider == "openalex":
            author = value.get("author")
            name = author.get("display_name") if isinstance(author, dict) else None
        elif provider == "crossref":
            name = " ".join(
                part.strip() for part in (value.get("given"), value.get("family"))
                if isinstance(part, str) and part.strip()
            )
        else:
            name = value.get("name")
        if isinstance(name, str) and name.strip():
            rows.add(" ".join(name.split()))
    return sorted(rows)


def _crossref_year(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "published", "issued"):
        value = item.get(field)
        parts = value.get("date-parts") if isinstance(value, dict) else None
        if (
            isinstance(parts, list) and parts and isinstance(parts[0], list)
            and parts[0] and type(parts[0][0]) is int
        ):
            return _year(parts[0][0])
    return None


def _crossref_date(item: dict[str, Any]) -> str | None:
    for field in ("published-print", "published-online", "published", "issued"):
        value = item.get(field)
        parts = value.get("date-parts") if isinstance(value, dict) else None
        if not (isinstance(parts, list) and parts and isinstance(parts[0], list)):
            continue
        date_parts = parts[0]
        if not date_parts or _year(date_parts[0]) is None:
            continue
        year = date_parts[0]
        month = date_parts[1] if len(date_parts) > 1 else 1
        day = date_parts[2] if len(date_parts) > 2 else 1
        if (
            type(month) is int and 1 <= month <= 12
            and type(day) is int and 1 <= day <= 31
        ):
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def _first_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return " ".join(value.split())
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return " ".join(item.split())
    return None


def _concepts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: set[str] = set()
    for item in value:
        if isinstance(item, str) and item.strip():
            rows.add(" ".join(item.split()))
        elif isinstance(item, dict):
            label = item.get("display_name") or item.get("name")
            if isinstance(label, str) and label.strip():
                rows.add(" ".join(label.split()))
    return sorted(rows, key=str.casefold)


def _date_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        text = " ".join(value.split())
        return text[:32]
    return None


def _openalex_abstract(item: dict[str, Any]) -> str | None:
    value = item.get("abstract_inverted_index")
    if not isinstance(value, dict):
        return None
    tokens: list[tuple[int, str]] = []
    for word, positions in value.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if type(position) is int and position >= 0:
                tokens.append((position, word))
    if not tokens:
        return None
    return " ".join(word for _, word in sorted(tokens))


def _openalex_record(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    raw_id = item.get("id")
    title = item.get("display_name")
    if not isinstance(raw_id, str) or not raw_id.startswith("https://openalex.org/W"):
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    openalex_id = raw_id.rstrip("/").rsplit("/", 1)[-1].upper()
    ids = item.get("ids") if isinstance(item.get("ids"), dict) else {}
    location = item.get("primary_location")
    source = location.get("source") if isinstance(location, dict) else None
    venue = source.get("display_name") if isinstance(source, dict) else None
    venue_id = source.get("id") if isinstance(source, dict) else None
    is_retracted = item.get("is_retracted")
    if is_retracted is True:
        retraction = "retracted"
    elif is_retracted is False:
        retraction = "not_retracted"
    else:
        retraction = "not_checked"
    return {
        "provider": "openalex",
        "provider_id": openalex_id,
        "title": " ".join(title.split()),
        "abstract": _openalex_abstract(item),
        "concepts": _concepts(item.get("concepts")),
        "authors": _authors(item.get("authorships"), provider="openalex"),
        "year": _year(item.get("publication_year")),
        "publication_date": _date_text(item.get("publication_date")),
        "identifiers": {
            "arxiv": normalize_arxiv(ids.get("arxiv")),
            "crossref": None,
            "doi": normalize_doi(item.get("doi")),
            "openalex": openalex_id,
            "semantic_scholar": None,
        },
        "citation_count": _citation(item.get("cited_by_count")),
        "venue": _first_text(venue),
        "venue_key": _first_text(venue_id),
        "source_url": raw_id,
        "retraction_status": retraction,
    }


def _crossref_record(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    doi = normalize_doi(item.get("DOI"))
    title = _first_text(item.get("title"))
    if doi is None or title is None:
        return None
    return {
        "provider": "crossref",
        "provider_id": doi,
        "title": title,
        "abstract": _first_text(item.get("abstract")),
        "concepts": _concepts(item.get("subject")),
        "authors": _authors(item.get("author"), provider="crossref"),
        "year": _crossref_year(item),
        "publication_date": _crossref_date(item),
        "identifiers": {
            "arxiv": None,
            "crossref": doi,
            "doi": doi,
            "openalex": None,
            "semantic_scholar": None,
        },
        "citation_count": _citation(item.get("is-referenced-by-count")),
        "venue": _first_text(item.get("container-title")),
        "venue_key": None,
        "source_url": _first_text(item.get("URL")) or f"https://doi.org/{doi}",
        "retraction_status": "not_checked",
    }


def _semantic_record(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    paper_id = item.get("paperId")
    title = item.get("title")
    if not isinstance(paper_id, str) or not paper_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    external = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
    openalex = external.get("OpenAlex")
    if isinstance(openalex, str):
        openalex = openalex.rstrip("/").rsplit("/", 1)[-1].upper()
        if not openalex.startswith("W"):
            openalex = None
    else:
        openalex = None
    return {
        "provider": "semantic_scholar",
        "provider_id": paper_id,
        "title": " ".join(title.split()),
        "abstract": _first_text(item.get("abstract")),
        "concepts": _concepts(item.get("fieldsOfStudy")),
        "authors": _authors(item.get("authors"), provider="semantic_scholar"),
        "year": _year(item.get("year")),
        "publication_date": _date_text(item.get("publicationDate")),
        "identifiers": {
            "arxiv": normalize_arxiv(external.get("ArXiv")),
            "crossref": None,
            "doi": normalize_doi(external.get("DOI")),
            "openalex": openalex,
            "semantic_scholar": paper_id,
        },
        "citation_count": _citation(item.get("citationCount")),
        "venue": _first_text(item.get("venue")),
        "venue_key": None,
        "source_url": _first_text(item.get("url")) or f"https://www.semanticscholar.org/paper/{paper_id}",
        "retraction_status": "not_checked",
    }


def _parse_response(provider: str, response: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(response, dict):
        _fail("invalid_seed_provider_response", f"{provider} response must be an object")
    if provider == "openalex":
        results = response.get("results")
        meta = response.get("meta")
        total = meta.get("count") if isinstance(meta, dict) else None
        parser = _openalex_record
    elif provider == "crossref":
        message = response.get("message")
        results = message.get("items") if isinstance(message, dict) else None
        total = message.get("total-results") if isinstance(message, dict) else None
        parser = _crossref_record
    elif provider == "semantic_scholar":
        results = response.get("data")
        total = response.get("total")
        parser = _semantic_record
    else:
        _fail("invalid_seed_provider_bundle", f"unsupported provider: {provider}")
    if not isinstance(results, list) or type(total) is not int or total < len(results):
        _fail("invalid_seed_provider_response", f"{provider} response envelope is invalid")
    records = [record for item in results if (record := parser(item)) is not None]
    return records, total


def validate_provider_bundle(
    value: Any, *, expected_topic_contract_sha256: str | None = None
) -> dict[str, Any]:
    row = _exact(value, {
        "schema_version", "topic_contract_sha256", "accessed_at", "providers",
        "benchmark_labels_consumed",
    }, "provider_bundle")
    if row["schema_version"] != PROVIDER_BUNDLE_SCHEMA:
        _fail("invalid_seed_provider_bundle", "provider bundle schema is unsupported")
    digest = _text(row["topic_contract_sha256"], "topic_contract_sha256")
    if (
        len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or expected_topic_contract_sha256 not in {None, digest}
    ):
        _fail("invalid_seed_provider_bundle", "provider bundle topic binding differs")
    if row["benchmark_labels_consumed"] is not False:
        _fail("invalid_seed_provider_bundle", "provider bundle contains evaluator labels")
    providers = row["providers"]
    if not isinstance(providers, list) or len(providers) != len(SUPPORTED_PROVIDERS):
        _fail("invalid_seed_provider_bundle", "provider bundle must account for every provider")
    normalized_providers = []
    for provider_index, raw_provider in enumerate(providers):
        provider = _exact(raw_provider, {"provider", "status", "requests"}, f"providers[{provider_index}]")
        name = _text(provider["provider"], f"providers[{provider_index}].provider")
        status = _status(provider["status"], f"providers[{provider_index}].status")
        requests = provider["requests"]
        if not isinstance(requests, list) or len(requests) > 12:
            _fail("invalid_seed_provider_bundle", "provider requests must be a bounded list")
        normalized_requests = []
        for request_index, raw_request in enumerate(requests):
            field = f"providers[{provider_index}].requests[{request_index}]"
            request = _exact(raw_request, {
                "route_id", "purpose", "query", "status", "capped",
                "provider_total", "request_url", "response", "detail",
            }, field)
            request_status = _status(request["status"], f"{field}.status")
            response = request["response"]
            total = request["provider_total"]
            if request_status == "not_available":
                if response is not None or total is not None:
                    _fail("invalid_seed_provider_bundle", f"{field} unavailable request has provider data")
            else:
                _, parsed_total = _parse_response(name, response)
                if total != parsed_total:
                    _fail("invalid_seed_provider_bundle", f"{field} provider total differs from response")
            if (
                type(request["capped"]) is not bool
                or request["capped"] != (request_status == "capped")
            ):
                _fail("invalid_seed_provider_bundle", f"{field} capped state is inconsistent")
            normalized_requests.append({
                "route_id": _text(request["route_id"], f"{field}.route_id"),
                "purpose": _text(request["purpose"], f"{field}.purpose"),
                "query": _text(request["query"], f"{field}.query"),
                "status": request_status,
                "capped": request["capped"],
                "provider_total": total,
                "request_url": _text(request["request_url"], f"{field}.request_url"),
                "response": response,
                "detail": _text(request["detail"], f"{field}.detail", nullable=True),
            })
        route_ids = [request["route_id"] for request in normalized_requests]
        if route_ids != sorted(set(route_ids)):
            _fail("invalid_seed_provider_bundle", "provider request route IDs must be unique and sorted")
        request_statuses = {request["status"] for request in normalized_requests}
        if "capped" in request_statuses:
            expected_status = "capped"
        elif "available" in request_statuses:
            expected_status = "available"
        elif "empty" in request_statuses:
            expected_status = "empty"
        else:
            expected_status = "not_available"
        if status != expected_status:
            _fail(
                "invalid_seed_provider_bundle",
                f"provider {name} status differs from its request rows",
            )
        normalized_providers.append({"provider": name, "status": status, "requests": normalized_requests})
    if [provider["provider"] for provider in normalized_providers] != list(SUPPORTED_PROVIDERS):
        _fail("invalid_seed_provider_bundle", "providers must use the canonical provider order")
    return {
        "schema_version": PROVIDER_BUNDLE_SCHEMA,
        "topic_contract_sha256": digest,
        "accessed_at": _text(row["accessed_at"], "accessed_at"),
        "providers": normalized_providers,
        "benchmark_labels_consumed": False,
    }


def normalize_provider_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if bundle.get("schema_version") == PROVIDER_BUNDLE_SCHEMA_V2:
        return normalize_provider_bundle_v2(bundle)
    bundle = validate_provider_bundle(bundle)
    records: list[dict[str, Any]] = []
    statuses = []
    route_statuses = []
    request_count = 0
    observed_rows = 0
    for provider in bundle["providers"]:
        statuses.append({"provider": provider["provider"], "status": provider["status"]})
        by_id: dict[str, dict[str, Any]] = {}
        for request in provider["requests"]:
            request_count += 1
            route_statuses.append({
                "provider": provider["provider"],
                "route_id": request["route_id"],
                "purpose": request["purpose"],
                "status": request["status"],
                "capped": request["capped"],
                "provider_total": request["provider_total"],
            })
            if request["status"] == "not_available":
                continue
            parsed, _ = _parse_response(provider["provider"], request["response"])
            observed_rows += len(parsed)
            for rank, record in enumerate(parsed, start=1):
                existing = by_id.get(record["provider_id"])
                if existing is None:
                    existing = {
                        **record,
                        "route_ids": [],
                        "route_purposes": [],
                        "provider_best_rank": rank,
                    }
                    by_id[record["provider_id"]] = existing
                elif any(
                    existing[field] != record[field]
                    for field in ("title", "authors", "year", "identifiers")
                ):
                    _fail(
                        "seed_provider_identity_conflict",
                        f"{provider['provider']} repeated one provider ID with conflicting identity metadata",
                    )
                else:
                    abstracts = [
                        value for value in (existing.get("abstract"), record.get("abstract"))
                        if value
                    ]
                    existing["abstract"] = (
                        max(
                            abstracts,
                            key=lambda value: (len(value.split()), len(value), value.casefold()),
                        )
                        if abstracts else None
                    )
                    existing["concepts"] = sorted(
                        {*existing.get("concepts", []), *record.get("concepts", [])},
                        key=str.casefold,
                    )
                    for optional_field in ("publication_date", "venue", "venue_key"):
                        if existing.get(optional_field) is None and record.get(optional_field) is not None:
                            existing[optional_field] = record[optional_field]
                existing["route_ids"] = sorted({*existing["route_ids"], request["route_id"]})
                existing["route_purposes"] = sorted({
                    *existing["route_purposes"], request["purpose"]
                })
                existing["provider_best_rank"] = min(existing["provider_best_rank"], rank)
        records.extend(by_id.values())
    records.sort(key=lambda record: (record["provider"], record["provider_id"]))
    return {
        "schema_version": PROVIDER_OBSERVATIONS_SCHEMA,
        "topic_contract_sha256": bundle["topic_contract_sha256"],
        "accessed_at": bundle["accessed_at"],
        "provider_statuses": statuses,
        "route_statuses": sorted(
            route_statuses, key=lambda row: (row["provider"], row["route_id"])
        ),
        "records": records,
        "budget_consumption": {
            "metadata_requests": request_count,
            "provider_rows": observed_rows,
            "unique_provider_records": len(records),
        },
        "limitations": [
            "citation counts and ranks are provider-local prioritization signals only",
            "Google Scholar is unsupported because it has no supported public API",
            "provider coverage and metadata may be incomplete",
        ],
        "benchmark_labels_consumed": False,
    }


def _assert_provider_url(provider: str, url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    expected_host = {
        "crossref": "api.crossref.org",
        "openalex": "api.openalex.org",
        "semantic_scholar": "api.semanticscholar.org",
    }[provider]
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        _fail("seed_provider_endpoint_forbidden", "provider endpoint is outside its exact HTTPS host")


def _validated_diagnostic(status: str, value: Any, field: str) -> dict[str, Any] | None:
    if status in {"available", "empty", "capped"}:
        if value is not None:
            _fail("invalid_seed_provider_bundle", f"{field} successful route has a diagnostic")
        return None
    if not isinstance(value, dict):
        _fail("invalid_seed_provider_bundle", f"{field} failed route requires a diagnostic")
    if status == "rate_limited":
        if set(value) != {"category", "http_status", "retry_after_seconds"}:
            _fail("invalid_seed_provider_bundle", f"{field} rate-limit diagnostic fields are not exact")
        retry = value["retry_after_seconds"]
        if value["category"] != "rate_limited" or value["http_status"] != 429:
            _fail("invalid_seed_provider_bundle", f"{field} rate-limit diagnostic is inconsistent")
        if retry is not None and (type(retry) is not int or not 0 <= retry <= 86_400):
            _fail("invalid_seed_provider_bundle", f"{field} retry delay is outside the safe bound")
        return dict(value)
    expected = {
        "transport_failed": {"dns", "timeout", "tls", "connection", "proxy"},
        "http_failed": {"http_failed"},
        "skipped_after_provider_veto": {"provider_veto"},
        "unsupported_exact_route": {"unsupported_identifier_for_provider"},
    }[status]
    if set(value) != {"category", "http_status"} or value["category"] not in expected:
        _fail("invalid_seed_provider_bundle", f"{field} diagnostic is inconsistent")
    code = value["http_status"]
    if status == "http_failed":
        if type(code) is not int or not 400 <= code <= 599 or code == 429:
            _fail("invalid_seed_provider_bundle", f"{field} HTTP diagnostic is inconsistent")
    elif code is not None:
        _fail("invalid_seed_provider_bundle", f"{field} non-HTTP diagnostic has a status code")
    return dict(value)


def validate_provider_bundle_v2(
    value: Any, *, expected_topic_contract_sha256: str | None = None
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "topic_contract_sha256", "seed_authorities",
        "accessed_at", "providers", "benchmark_labels_consumed",
    }:
        _fail("invalid_seed_provider_bundle", "provider bundle v2 fields are not exact")
    if value["schema_version"] != PROVIDER_BUNDLE_SCHEMA_V2:
        _fail("invalid_seed_provider_bundle", "provider bundle v2 schema is unsupported")
    digest = value["topic_contract_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or expected_topic_contract_sha256 not in {None, digest}
    ):
        _fail("invalid_seed_provider_bundle", "provider bundle v2 topic binding differs")
    seeds = value["seed_authorities"]
    if (
        not isinstance(seeds, list)
        or any(not isinstance(seed, str) or not seed for seed in seeds)
        or seeds != sorted(set(seeds), key=str.casefold)
    ):
        _fail("invalid_seed_provider_bundle", "provider bundle v2 seeds must be unique and sorted")
    if value["benchmark_labels_consumed"] is not False:
        _fail("invalid_seed_provider_bundle", "provider bundle v2 contains evaluator labels")
    providers = value["providers"]
    if not isinstance(providers, list) or len(providers) != len(SUPPORTED_PROVIDERS):
        _fail("invalid_seed_provider_bundle", "provider bundle v2 must account for every provider")
    by_provider: dict[str, dict[str, Any]] = {}
    for provider_index, provider in enumerate(providers):
        if not isinstance(provider, dict) or set(provider) != {"provider", "status", "requests"}:
            _fail("invalid_seed_provider_bundle", f"providers[{provider_index}] fields are not exact")
        name = provider["provider"]
        status = provider["status"]
        requests = provider["requests"]
        if name not in SUPPORTED_PROVIDERS or name in by_provider:
            _fail("invalid_seed_provider_bundle", "provider bundle v2 providers are invalid")
        if status not in _STATUSES_V2:
            _fail("invalid_seed_provider_bundle", f"provider {name} status is unsupported")
        if not isinstance(requests, list) or not 1 <= len(requests) <= 36:
            _fail("invalid_seed_provider_bundle", f"provider {name} requests are not bounded")
        route_ids: set[str] = set()
        normalized_requests = []
        for request_index, request in enumerate(requests):
            field = f"providers[{provider_index}].requests[{request_index}]"
            if not isinstance(request, dict) or set(request) != {
                "route_id", "purpose", "query", "endpoint_kind", "status",
                "capped", "provider_total", "request_url", "response", "detail",
                "diagnostic",
            }:
                _fail("invalid_seed_provider_bundle", f"{field} fields are not exact")
            route_id = _text(request["route_id"], f"{field}.route_id")
            request_status = request["status"]
            endpoint_kind = request["endpoint_kind"]
            if route_id in route_ids or request_status not in _STATUSES_V2:
                _fail("invalid_seed_provider_bundle", f"{field} route or status is invalid")
            route_ids.add(route_id)
            if endpoint_kind not in {"exact_identifier", "exact_title_resolution", "broad_search"}:
                _fail("invalid_seed_provider_bundle", f"{field} endpoint kind is unsupported")
            if type(request["capped"]) is not bool or request["capped"] != (request_status == "capped"):
                _fail("invalid_seed_provider_bundle", f"{field} capped state is inconsistent")
            response = request["response"]
            total = request["provider_total"]
            if request_status in {"available", "empty", "capped"}:
                if endpoint_kind == "exact_identifier":
                    kind, _ = _seed_parts(request["query"])
                    _, parsed_total = _parse_exact_response(name, kind, response)
                else:
                    _, parsed_total = _parse_response(name, response)
                if total != parsed_total:
                    _fail("invalid_seed_provider_bundle", f"{field} provider total differs from response")
            elif response is not None or total is not None:
                _fail("invalid_seed_provider_bundle", f"{field} failed route contains provider data")
            request_url = request["request_url"]
            if request_status in {"skipped_after_provider_veto", "unsupported_exact_route"}:
                if request_url is not None:
                    _fail("invalid_seed_provider_bundle", f"{field} unsent route has a URL")
            else:
                request_url = _text(request_url, f"{field}.request_url")
                _assert_provider_url(name, request_url)
            diagnostic = _validated_diagnostic(request_status, request["diagnostic"], field)
            normalized_requests.append({
                "route_id": route_id,
                "purpose": _text(request["purpose"], f"{field}.purpose"),
                "query": _text(request["query"], f"{field}.query"),
                "endpoint_kind": endpoint_kind,
                "status": request_status,
                "capped": request["capped"],
                "provider_total": total,
                "request_url": request_url,
                "response": response,
                "detail": _text(request["detail"], f"{field}.detail", nullable=True),
                "diagnostic": diagnostic,
            })
        observed_statuses = {request["status"] for request in normalized_requests}
        if {"available", "empty", "capped"} & observed_statuses:
            expected_status = "available" if "available" in observed_statuses else (
                "capped" if "capped" in observed_statuses else "empty"
            )
        elif "rate_limited" in observed_statuses:
            expected_status = "rate_limited"
        elif "transport_failed" in observed_statuses:
            expected_status = "transport_failed"
        elif "http_failed" in observed_statuses:
            expected_status = "http_failed"
        elif "unsupported_exact_route" in observed_statuses:
            expected_status = "unsupported_exact_route"
        else:
            expected_status = "skipped_after_provider_veto"
        if status != expected_status:
            _fail("invalid_seed_provider_bundle", f"provider {name} status differs from its request rows")
        by_provider[name] = {"provider": name, "status": status, "requests": normalized_requests}
    return {
        "schema_version": PROVIDER_BUNDLE_SCHEMA_V2,
        "topic_contract_sha256": digest,
        "seed_authorities": seeds,
        "accessed_at": _text(value["accessed_at"], "accessed_at"),
        "providers": [by_provider[name] for name in SUPPORTED_PROVIDERS],
        "benchmark_labels_consumed": False,
    }


def normalize_provider_bundle_v2(bundle: dict[str, Any]) -> dict[str, Any]:
    bundle = validate_provider_bundle_v2(bundle)
    digest = bundle.get("topic_contract_sha256")
    seeds = bundle.get("seed_authorities")
    providers = bundle.get("providers")
    records: list[dict[str, Any]] = []
    statuses = []
    route_statuses = []
    request_count = 0
    observed_rows = 0
    for provider in providers:
        name = provider["provider"]
        statuses.append({"provider": name, "status": provider["status"]})
        by_id: dict[str, dict[str, Any]] = {}
        for request in provider["requests"]:
            request_count += request["status"] != "skipped_after_provider_veto"
            route_statuses.append({
                "provider": name,
                "route_id": request["route_id"],
                "purpose": request["purpose"],
                "endpoint_kind": request["endpoint_kind"],
                "status": request["status"],
                "capped": request["capped"],
                "provider_total": request["provider_total"],
                "diagnostic": request["diagnostic"],
            })
            if request["status"] not in {"available", "empty", "capped"}:
                continue
            if request["endpoint_kind"] == "exact_identifier":
                kind, _ = _seed_parts(request["query"])
                parsed, _ = _parse_exact_response(name, kind, request["response"])
            else:
                parsed, _ = _parse_response(name, request["response"])
            observed_rows += len(parsed)
            for rank, record in enumerate(parsed, start=1):
                existing = by_id.get(record["provider_id"])
                if existing is None:
                    existing = {
                        **record,
                        "route_ids": [],
                        "route_purposes": [],
                        "endpoint_kinds": [],
                        "provider_best_rank": rank,
                    }
                    by_id[record["provider_id"]] = existing
                elif any(existing[field] != record[field] for field in ("title", "authors", "year", "identifiers")):
                    _fail("seed_provider_identity_conflict", f"{name} repeated one provider ID with conflicting identity metadata")
                else:
                    abstracts = [value for value in (existing.get("abstract"), record.get("abstract")) if value]
                    existing["abstract"] = max(abstracts, key=lambda value: (len(value.split()), len(value), value.casefold())) if abstracts else None
                    existing["concepts"] = sorted({*existing.get("concepts", []), *record.get("concepts", [])}, key=str.casefold)
                existing["route_ids"] = sorted({*existing["route_ids"], request["route_id"]})
                existing["route_purposes"] = sorted({*existing["route_purposes"], request["purpose"]})
                existing["endpoint_kinds"] = sorted({*existing["endpoint_kinds"], request["endpoint_kind"]})
                existing["provider_best_rank"] = min(existing["provider_best_rank"], rank)
        records.extend(by_id.values())
    records.sort(key=lambda record: (record["provider"], record["provider_id"]))
    return {
        "schema_version": PROVIDER_OBSERVATIONS_SCHEMA_V2,
        "topic_contract_sha256": digest,
        "seed_authorities": seeds,
        "accessed_at": bundle["accessed_at"],
        "provider_statuses": statuses,
        "route_statuses": sorted(route_statuses, key=lambda row: (row["provider"], row["route_id"])),
        "records": records,
        "budget_consumption": {
            "metadata_requests": request_count,
            "provider_rows": observed_rows,
            "unique_provider_records": len(records),
        },
        "limitations": [
            "metadata nominations require primary-source inspection",
            "provider coverage and rate limits may be incomplete",
        ],
        "benchmark_labels_consumed": False,
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        _fail("seed_provider_redirect", "seed metadata provider redirected")
        return None


def _strict_json(raw: bytes, provider: str) -> dict[str, Any]:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail("invalid_seed_provider_response", f"{provider} returned a duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs_hook,
            parse_constant=lambda item: _fail(
                "invalid_seed_provider_response", f"{provider} returned non-finite JSON: {item}"
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError(
            "invalid_seed_provider_response", f"{provider} response is not UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        _fail("invalid_seed_provider_response", f"{provider} response must be an object")
    return value


def _route_query(route: dict[str, Any]) -> str:
    query_filter = route["filter"]
    for prefix in ("title.search:", "default.search:"):
        if query_filter.startswith(prefix):
            return query_filter[len(prefix):]
    _fail("invalid_seed_provider_route", "seed provider route filter is unsupported")
    raise AssertionError


def _provider_url(provider: str, query: str, *, limit: int) -> str:
    if provider == "openalex":
        params = urllib.parse.urlencode({
            "search": query,
            "sort": "cited_by_count:desc",
            "per-page": str(limit),
            "select": (
                "id,display_name,abstract_inverted_index,concepts,authorships,"
                "publication_year,publication_date,doi,cited_by_count,ids,"
                "primary_location,is_retracted"
            ),
        })
        return f"https://api.openalex.org/works?{params}"
    if provider == "crossref":
        params = urllib.parse.urlencode({
            "query.bibliographic": query,
            "rows": str(limit),
            "select": (
                "DOI,title,abstract,subject,author,published-print,published-online,"
                "published,issued,is-referenced-by-count,container-title,URL"
            ),
        })
        return f"https://api.crossref.org/works?{params}"
    if provider == "semantic_scholar":
        params = urllib.parse.urlencode({
            "query": query,
            "limit": str(limit),
            "fields": "paperId,title,abstract,authors,year,publicationDate,citationCount,externalIds,venue,fieldsOfStudy,url",
        })
        return f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    _fail("invalid_seed_provider_route", f"unsupported provider: {provider}")
    raise AssertionError


def _seed_parts(seed: str) -> tuple[str, str]:
    value = seed.strip()
    lowered = value.casefold()
    if lowered.startswith("doi:"):
        return "doi", value.split(":", 1)[1].strip().casefold()
    if lowered.startswith("arxiv:"):
        return "arxiv", value.split(":", 1)[1].strip().casefold()
    if lowered.startswith("openalex:"):
        return "openalex", value.split(":", 1)[1].strip().casefold()
    if lowered.startswith("semantic_scholar:"):
        return "semantic_scholar", value.split(":", 1)[1].strip()
    if lowered.startswith("title:"):
        return "title", value.split(":", 1)[1].strip().casefold()
    if value.startswith("10."):
        return "doi", value.casefold()
    if lowered.startswith("w"):
        return "openalex", value.casefold()
    _fail("invalid_seed_provider_route", f"unsupported exact seed authority: {seed}")
    raise AssertionError


def _exact_provider_url(provider: str, kind: str, value: str) -> str | None:
    if kind == "title":
        return _provider_url(provider, value, limit=5)
    if provider == "crossref" and kind == "doi":
        return f"https://api.crossref.org/works/{urllib.parse.quote(value, safe='')}"
    if provider == "openalex" and kind == "doi":
        params = urllib.parse.urlencode({"filter": f"doi:{value}"})
        return f"https://api.openalex.org/works?{params}"
    if provider == "openalex" and kind == "openalex":
        return f"https://api.openalex.org/works/{urllib.parse.quote(value, safe='')}"
    if provider == "openalex" and kind == "arxiv":
        return f"https://api.openalex.org/works/arxiv:{urllib.parse.quote(value, safe='')}"
    semantic_prefix = {
        "doi": "DOI",
        "arxiv": "ARXIV",
        "semantic_scholar": None,
    }.get(kind)
    if provider == "semantic_scholar" and kind in {"doi", "arxiv", "semantic_scholar"}:
        identifier = value if semantic_prefix is None else f"{semantic_prefix}:{value}"
        return (
            "https://api.semanticscholar.org/graph/v1/paper/"
            f"{urllib.parse.quote(identifier, safe=':')}?fields="
            "paperId,title,abstract,authors,year,publicationDate,citationCount,"
            "externalIds,venue,fieldsOfStudy,url"
        )
    return None


def _diagnostic_for_exception(exc: Exception) -> dict[str, Any]:
    code = getattr(exc, "code", None)
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            retry_after = None
            headers = exc.headers
            if headers is not None:
                raw = headers.get("Retry-After")
                try:
                    retry_after = int(raw) if raw is not None else None
                except (TypeError, ValueError):
                    retry_after = None
            return {
                "category": "rate_limited",
                "http_status": 429,
                "retry_after_seconds": retry_after,
            }
        return {"category": "http_failed", "http_status": code}
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, socket.gaierror) or "name resolution" in str(reason).casefold():
        category = "dns"
    elif isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in str(reason).casefold():
        category = "timeout"
    elif isinstance(reason, ssl.SSLError) or "ssl" in str(reason).casefold() or "tls" in str(reason).casefold():
        category = "tls"
    elif isinstance(exc, urllib.error.URLError):
        category = "connection"
    else:
        category = "connection"
    return {"category": category, "http_status": None}


def _v2_status_from_diagnostic(diagnostic: dict[str, Any]) -> str:
    category = diagnostic.get("category")
    if category == "rate_limited":
        return "rate_limited"
    if category in {"dns", "timeout", "tls", "connection", "proxy"}:
        return "transport_failed"
    return "http_failed"


def _parse_exact_response(provider: str, kind: str, value: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if provider == "crossref":
        message = value.get("message")
        if not isinstance(message, dict):
            _fail("invalid_seed_provider_response", "Crossref exact response has no message")
        if "items" in message:
            return _parse_response("crossref", value)
        item = dict(message)
        item.pop("total-results", None)
        return _parse_response("crossref", {"message": {"total-results": 1, "items": [item]}})
    if provider == "openalex":
        if "results" in value:
            return _parse_response("openalex", value)
        return _parse_response("openalex", {"meta": {"count": 1}, "results": [value]})
    if provider == "semantic_scholar":
        return _parse_response("semantic_scholar", {"total": 1, "data": [value]})
    _fail("invalid_seed_provider_response", f"unsupported exact provider: {provider}")
    raise AssertionError


def collect_live_provider_bundle_v2(
    topic_contract: dict[str, Any],
    *,
    seeds: list[str] | None = None,
    max_requests: int = 36,
    max_records_per_response: int = 20,
    max_total_records: int = 420,
    max_response_bytes: int = 2_000_000,
    max_total_bytes: int = 32_000_000,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Collect seeded exact identities plus bounded broad nominations."""
    budgets = (
        (max_requests, 1, 100),
        (max_records_per_response, 1, 100),
        (max_total_records, max_records_per_response, 10_000),
        (max_response_bytes, 1, 10_000_000),
        (max_total_bytes, max_response_bytes, 100_000_000),
    )
    if any(type(value) is not int or not lower <= value <= upper for value, lower, upper in budgets):
        _fail("seed_provider_budget_invalid", "seed provider v2 budgets are invalid")
    routes = plan_discovery_routes(topic_contract)["routes"]
    seeds = seeds or []
    seed_parts = [_seed_parts(seed) for seed in seeds]
    expected_requests = len(seed_parts) * len(SUPPORTED_PROVIDERS) + len(routes) * len(SUPPORTED_PROVIDERS)
    if expected_requests > max_requests:
        _fail("seed_provider_budget_exceeded", "seed and route plan exceeds request budget")
    opened = opener or urllib.request.build_opener(_NoRedirect()).open
    total_bytes = 0
    total_records = 0
    provider_rows = []
    for provider in SUPPORTED_PROVIDERS:
        request_rows = []
        provider_veto = False
        for index, (kind, value) in enumerate(seed_parts, start=1):
            route_id = f"seed_{kind}_{index}"
            url = _exact_provider_url(provider, kind, value)
            row = {
                "route_id": route_id,
                "purpose": "seed_authority",
                "query": f"{kind}:{value}",
                "endpoint_kind": "exact_title_resolution" if kind == "title" else "exact_identifier",
                "status": None,
                "capped": False,
                "provider_total": None,
                "request_url": url,
                "response": None,
                "detail": None,
                "diagnostic": None,
            }
            if url is None:
                row.update({
                    "status": "unsupported_exact_route",
                    "diagnostic": {"category": "unsupported_identifier_for_provider", "http_status": None},
                })
                request_rows.append(row)
                continue
            _assert_provider_url(provider, url)
            try:
                with opened(url, timeout=30) as response:
                    status_code = getattr(response, "status", 200)
                    if type(status_code) is not int or not 200 <= status_code <= 299:
                        raise urllib.error.HTTPError(url, status_code, "provider status", getattr(response, "headers", None), None)
                    if getattr(response, "geturl", lambda: url)() != url:
                        _fail("seed_provider_redirect", "provider request redirected")
                    raw = response.read(max_response_bytes + 1)
                if len(raw) > max_response_bytes:
                    _fail("seed_provider_budget_exceeded", "provider response exceeds byte cap")
                value_json = _strict_json(raw, provider)
                if kind == "title":
                    parsed_records, provider_total = _parse_response(provider, value_json)
                else:
                    parsed_records, provider_total = _parse_exact_response(provider, kind, value_json)
                total_bytes += len(raw)
                total_records += len(parsed_records)
                if total_bytes > max_total_bytes or total_records > max_total_records:
                    _fail("seed_provider_budget_exceeded", "aggregate provider budget exceeded")
                row.update({
                    "status": "available" if parsed_records else "empty",
                    "provider_total": provider_total,
                    "response": value_json,
                })
            except MissionStateError:
                raise
            except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                diagnostic = _diagnostic_for_exception(exc)
                row.update({"status": _v2_status_from_diagnostic(diagnostic), "diagnostic": diagnostic})
                if row["status"] == "rate_limited":
                    provider_veto = True
            request_rows.append(row)
        for route in routes:
            route_id = {
                "exact_high_citation": "broad_topic_high_citation",
                "exact_recent": "broad_topic_recent",
            }.get(route["kind"], route["kind"])
            if provider_veto:
                request_rows.append({
                    "route_id": route_id,
                    "purpose": route["purpose"],
                    "query": _route_query(route),
                    "endpoint_kind": "broad_search",
                    "status": "skipped_after_provider_veto",
                    "capped": False,
                    "provider_total": None,
                    "request_url": None,
                    "response": None,
                    "detail": None,
                    "diagnostic": {"category": "provider_veto", "http_status": None},
                })
                continue
            query = _route_query(route)
            url = _provider_url(provider, query, limit=max_records_per_response)
            _assert_provider_url(provider, url)
            row = {
                "route_id": route_id,
                "purpose": route["purpose"],
                "query": query,
                "endpoint_kind": "broad_search",
                "status": None,
                "capped": False,
                "provider_total": None,
                "request_url": url,
                "response": None,
                "detail": None,
                "diagnostic": None,
            }
            try:
                with opened(url, timeout=30) as response:
                    status_code = getattr(response, "status", 200)
                    if type(status_code) is not int or not 200 <= status_code <= 299:
                        raise urllib.error.HTTPError(url, status_code, "provider status", getattr(response, "headers", None), None)
                    if getattr(response, "geturl", lambda: url)() != url:
                        _fail("seed_provider_redirect", "provider request redirected")
                    raw = response.read(max_response_bytes + 1)
                if len(raw) > max_response_bytes:
                    _fail("seed_provider_budget_exceeded", "provider response exceeds byte cap")
                value_json = _strict_json(raw, provider)
                parsed_records, provider_total = _parse_response(provider, value_json)
                total_bytes += len(raw)
                total_records += len(parsed_records)
                if total_bytes > max_total_bytes or total_records > max_total_records:
                    _fail("seed_provider_budget_exceeded", "aggregate provider budget exceeded")
                status = "capped" if provider_total > len(parsed_records) else ("available" if parsed_records else "empty")
                row.update({"status": status, "capped": status == "capped", "provider_total": provider_total, "response": value_json})
            except MissionStateError:
                raise
            except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                diagnostic = _diagnostic_for_exception(exc)
                row.update({"status": _v2_status_from_diagnostic(diagnostic), "diagnostic": diagnostic})
                if row["status"] == "rate_limited":
                    provider_veto = True
            request_rows.append(row)
        statuses = {row["status"] for row in request_rows}
        if "available" in statuses or "empty" in statuses or "capped" in statuses:
            provider_status = "available" if "available" in statuses else ("capped" if "capped" in statuses else "empty")
        elif "rate_limited" in statuses:
            provider_status = "rate_limited"
        elif "transport_failed" in statuses:
            provider_status = "transport_failed"
        elif "http_failed" in statuses:
            provider_status = "http_failed"
        else:
            provider_status = "skipped_after_provider_veto"
        provider_rows.append({"provider": provider, "status": provider_status, "requests": request_rows})
    return validate_provider_bundle_v2({
        "schema_version": PROVIDER_BUNDLE_SCHEMA_V2,
        "topic_contract_sha256": topic_contract_sha256(topic_contract),
        "seed_authorities": sorted(set(seeds), key=str.casefold),
        "accessed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "providers": provider_rows,
        "benchmark_labels_consumed": False,
    })


def collect_live_provider_bundle(
    topic_contract: dict[str, Any],
    *,
    max_requests: int = 36,
    max_records_per_response: int = 20,
    max_total_records: int = 420,
    max_response_bytes: int = 2_000_000,
    max_total_bytes: int = 32_000_000,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Collect a bounded raw provider bundle from three public metadata APIs."""
    route_plan = plan_discovery_routes(topic_contract)
    routes = route_plan["routes"]
    if len(routes) * len(SUPPORTED_PROVIDERS) > max_requests:
        _fail("seed_provider_budget_exceeded", "provider route plan exceeds request budget")
    if not 1 <= max_records_per_response <= 100:
        _fail("seed_provider_budget_invalid", "records-per-response budget is invalid")
    opened = opener or urllib.request.build_opener(_NoRedirect()).open
    total_bytes = 0
    total_records = 0
    provider_rows = []
    for provider in SUPPORTED_PROVIDERS:
        request_rows = []
        for route in routes:
            query = _route_query(route)
            url = _provider_url(provider, query, limit=max_records_per_response)
            parsed = urllib.parse.urlparse(url)
            expected_host = {
                "crossref": "api.crossref.org",
                "openalex": "api.openalex.org",
                "semantic_scholar": "api.semanticscholar.org",
            }[provider]
            if parsed.scheme != "https" or parsed.hostname != expected_host:
                _fail("seed_provider_endpoint_forbidden", "provider endpoint is outside its exact HTTPS host")
            try:
                with opened(url, timeout=30) as response:
                    status_code = getattr(response, "status", 200)
                    if type(status_code) is not int or not 200 <= status_code <= 299:
                        raise urllib.error.HTTPError(url, status_code, "provider status", None, None)
                    if getattr(response, "geturl", lambda: url)() != url:
                        _fail("seed_provider_redirect", "provider request redirected")
                    raw = response.read(max_response_bytes + 1)
            except MissionStateError:
                raise
            except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                request_rows.append({
                    "route_id": route["kind"],
                    "purpose": route["purpose"],
                    "query": query,
                    "status": "not_available",
                    "capped": False,
                    "provider_total": None,
                    "request_url": url,
                    "response": None,
                    "detail": type(exc).__name__,
                })
                continue
            if len(raw) > max_response_bytes:
                _fail("seed_provider_budget_exceeded", "provider response exceeds byte cap")
            total_bytes += len(raw)
            if total_bytes > max_total_bytes:
                _fail("seed_provider_budget_exceeded", "aggregate provider byte budget is exceeded")
            response_value = _strict_json(raw, provider)
            parsed_records, provider_total = _parse_response(provider, response_value)
            total_records += len(parsed_records)
            if total_records > max_total_records:
                _fail("seed_provider_budget_exceeded", "aggregate provider record budget is exceeded")
            capped = provider_total > len(parsed_records)
            status = "capped" if capped else ("available" if parsed_records else "empty")
            request_rows.append({
                "route_id": route["kind"],
                "purpose": route["purpose"],
                "query": query,
                "status": status,
                "capped": capped,
                "provider_total": provider_total,
                "request_url": url,
                "response": response_value,
                "detail": None,
            })
        request_rows.sort(key=lambda row: row["route_id"])
        statuses = {row["status"] for row in request_rows}
        if "capped" in statuses:
            provider_status = "capped"
        elif "available" in statuses:
            provider_status = "available"
        elif "empty" in statuses:
            provider_status = "empty"
        else:
            provider_status = "not_available"
        provider_rows.append({
            "provider": provider,
            "status": provider_status,
            "requests": request_rows,
        })
    bundle = {
        "schema_version": PROVIDER_BUNDLE_SCHEMA,
        "topic_contract_sha256": topic_contract_sha256(topic_contract),
        "accessed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "providers": provider_rows,
        "benchmark_labels_consumed": False,
    }
    return validate_provider_bundle(
        bundle, expected_topic_contract_sha256=topic_contract_sha256(topic_contract)
    )


__all__ = [
    "GOOGLE_SCHOLAR_STATUS", "PROVIDER_BUNDLE_SCHEMA", "PROVIDER_OBSERVATIONS_SCHEMA",
    "PROVIDER_BUNDLE_SCHEMA_V2", "PROVIDER_OBSERVATIONS_SCHEMA_V2",
    "SUPPORTED_PROVIDERS", "collect_live_provider_bundle", "collect_live_provider_bundle_v2", "normalize_arxiv",
    "normalize_doi", "normalize_provider_bundle", "validate_provider_bundle",
    "validate_provider_bundle_v2",
]
