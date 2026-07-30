from __future__ import annotations

import copy
import json
import socket
import urllib.error

import pytest

from research_assistant.survey.seed_paper_providers import (
    collect_live_provider_bundle_v2 as collect_live_provider_bundle,
    normalize_provider_bundle,
    validate_provider_bundle_v2,
)
from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.topic_contract import build_topic_contract


TOPIC = "Neural DSGE solution methods"
DOI_SEED = "doi:10.1016/j.jmoneco.2021.07.004"


class Response:
    status = 200

    def __init__(self, url: str):
        self.url = url
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self, _limit: int):
        if "openalex.org" in self.url:
            value = {"meta": {"count": 0}, "results": []}
        elif "crossref.org" in self.url:
            value = {"message": {"total-results": 0, "items": []}}
        else:
            value = {"total": 0, "data": []}
        return json.dumps(value).encode()


def test_exact_doi_routes_precede_truthfully_named_broad_routes() -> None:
    urls: list[str] = []

    def opener(url: str, *, timeout: int):
        urls.append(url)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC),
        seeds=[DOI_SEED],
        opener=opener,
        max_records_per_response=5,
    )

    for provider in bundle["providers"]:
        requests = provider["requests"]
        assert requests[0]["route_id"] == "seed_doi_1"
        assert requests[0]["endpoint_kind"] == "exact_identifier"
        assert all(not row["route_id"].startswith("exact_") for row in requests[1:])
    assert "/works/10.1016%2Fj.jmoneco.2021.07.004" in urls[0]
    assert "filter=doi%3A10.1016%2Fj.jmoneco.2021.07.004" in urls[len(urls) // 3]
    assert "/paper/DOI:10.1016%2Fj.jmoneco.2021.07.004" in urls[2 * len(urls) // 3]


def test_rate_limit_is_typed_and_skips_remaining_broad_routes() -> None:
    calls: list[str] = []

    def opener(url: str, *, timeout: int):
        calls.append(url)
        if "semanticscholar.org" in url:
            raise urllib.error.HTTPError(url, 429, "rate limited", {"Retry-After": "15"}, None)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=opener, max_records_per_response=5
    )
    semantic = bundle["providers"][2]
    assert semantic["status"] == "rate_limited"
    assert semantic["requests"][0]["status"] == "rate_limited"
    assert semantic["requests"][0]["diagnostic"] == {
        "category": "rate_limited",
        "http_status": 429,
        "retry_after_seconds": 15,
    }
    assert all(row["status"] == "skipped_after_provider_veto" for row in semantic["requests"][1:])
    assert len([url for url in calls if "semanticscholar.org" in url]) == 1


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (urllib.error.URLError(socket.gaierror(-2, "name resolution")), "dns"),
        (urllib.error.URLError(TimeoutError("timed out")), "timeout"),
    ],
)
def test_transport_failure_preserves_closed_category(error: Exception, category: str) -> None:
    def opener(url: str, *, timeout: int):
        if "crossref.org" in url:
            raise error
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=opener, max_records_per_response=5
    )
    crossref = bundle["providers"][0]
    assert crossref["status"] == "transport_failed"
    assert crossref["requests"][0]["diagnostic"]["category"] == category
    assert crossref["requests"][0]["diagnostic"]["http_status"] is None


def test_non_rate_limit_http_error_is_not_provider_absence() -> None:
    def opener(url: str, *, timeout: int):
        if "crossref.org" in url:
            raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=opener, max_records_per_response=5
    )
    request = bundle["providers"][0]["requests"][0]
    assert request["status"] == "http_failed"
    assert request["diagnostic"]["http_status"] == 503


def test_exact_success_and_broad_rate_limit_are_both_preserved() -> None:
    calls = 0

    class SemanticResponse(Response):
        def read(self, _limit: int):
            return json.dumps({
                "paperId": "maliar",
                "title": "Deep learning for solving dynamic economic models",
                "authors": [{"name": "Lilia Maliar"}],
                "year": 2021,
                "citationCount": 10,
                "externalIds": {"DOI": DOI_SEED.removeprefix("doi:")},
                "venue": "Journal of Monetary Economics",
                "url": "https://www.semanticscholar.org/paper/maliar",
            }).encode()

    def opener(url: str, *, timeout: int):
        nonlocal calls
        if "semanticscholar.org" in url:
            calls += 1
            if "/paper/DOI:" in url:
                return SemanticResponse(url)
            raise urllib.error.HTTPError(url, 429, "rate limited", {"Retry-After": "9"}, None)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC),
        seeds=[DOI_SEED],
        opener=opener,
        max_records_per_response=5,
    )
    semantic = bundle["providers"][2]
    assert semantic["status"] == "available"
    assert semantic["requests"][0]["status"] == "available"
    assert semantic["requests"][1]["status"] == "rate_limited"
    assert all(
        row["status"] == "skipped_after_provider_veto"
        for row in semantic["requests"][2:]
    )
    observations = normalize_provider_bundle(bundle)
    semantic_routes = [
        row for row in observations["route_statuses"]
        if row["provider"] == "semantic_scholar"
    ]
    assert {row["status"] for row in semantic_routes} >= {
        "available", "rate_limited", "skipped_after_provider_veto",
    }
    assert calls == 2


def test_unsupported_exact_provider_pair_is_typed_without_network_call() -> None:
    urls: list[str] = []

    def opener(url: str, *, timeout: int):
        urls.append(url)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC),
        seeds=["arxiv:2201.12220"],
        opener=opener,
        max_records_per_response=5,
    )
    crossref = bundle["providers"][0]
    assert crossref["requests"][0]["status"] == "unsupported_exact_route"
    assert crossref["requests"][0]["request_url"] is None
    assert all("crossref.org" not in url or "/works/2201.12220" not in url for url in urls)


def test_provider_order_does_not_change_normalized_observations() -> None:
    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=lambda url, timeout: Response(url),
        max_records_per_response=5,
    )
    permuted = copy.deepcopy(bundle)
    permuted["providers"].reverse()
    assert normalize_provider_bundle(permuted) == normalize_provider_bundle(bundle)


def test_v2_diagnostic_schema_and_retry_bound_fail_closed() -> None:
    def opener(url: str, *, timeout: int):
        if "semanticscholar.org" in url:
            raise urllib.error.HTTPError(url, 429, "rate limited", {"Retry-After": "15"}, None)
        return Response(url)

    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=opener, max_records_per_response=5
    )
    malformed = copy.deepcopy(bundle)
    diagnostic = malformed["providers"][2]["requests"][0]["diagnostic"]
    diagnostic["retry_after_seconds"] = 100_000
    with pytest.raises(MissionStateError, match="safe bound"):
        validate_provider_bundle_v2(malformed)

    malformed = copy.deepcopy(bundle)
    malformed["providers"][2]["requests"][0]["diagnostic"]["raw_headers"] = "secret"
    with pytest.raises(MissionStateError, match="fields are not exact"):
        validate_provider_bundle_v2(malformed)


def test_v2_provider_cannot_claim_accounting_without_request_rows() -> None:
    bundle = collect_live_provider_bundle(
        build_topic_contract(TOPIC), opener=lambda url, timeout: Response(url),
        max_records_per_response=5,
    )
    malformed = copy.deepcopy(bundle)
    malformed["providers"][0]["requests"] = []
    malformed["providers"][0]["status"] = "skipped_after_provider_veto"

    with pytest.raises(MissionStateError, match="requests are not bounded"):
        validate_provider_bundle_v2(malformed)
