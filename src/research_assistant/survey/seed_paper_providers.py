"""Bounded metadata providers for topic-to-seed candidate discovery."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.topic_contract import plan_discovery_routes, topic_contract_sha256


PROVIDER_BUNDLE_SCHEMA = "ra-survey-seed-provider-bundle-v1"
PROVIDER_OBSERVATIONS_SCHEMA = "ra-survey-seed-provider-observations-v1"
SUPPORTED_PROVIDERS = ("crossref", "openalex", "semantic_scholar")
GOOGLE_SCHOLAR_STATUS = "unsupported_no_public_api"
_STATUSES = {"available", "empty", "capped", "not_available"}
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
    "SUPPORTED_PROVIDERS", "collect_live_provider_bundle", "normalize_arxiv",
    "normalize_doi", "normalize_provider_bundle", "validate_provider_bundle",
]
