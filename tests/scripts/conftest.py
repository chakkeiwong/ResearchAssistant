from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def _write(path: Path, value: bytes | dict) -> tuple[Path, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return path.resolve(), hashlib.sha256(raw).hexdigest()


@pytest.fixture(autouse=True)
def portable_historical_fetch_evidence(request, tmp_path: Path, monkeypatch):
    """Bind ignored historical campaign bytes to deterministic test-owned evidence."""
    module = getattr(request.module, "MODULE", None)
    if module is None:
        return
    name = request.module.__name__
    root = tmp_path / "historical-evidence"

    if name.endswith("m20_openalex_documentation_root_fetch"):
        prior, digest = _write(
            root / "prior.json",
            {
                "attempted_transaction_count": 2,
                "aggregate_received_response_body_bytes": 160_783,
                "transaction_cap": 6,
                "aggregate_body_byte_cap": 8_000_000,
                "requests": [
                    {},
                    {
                        "request_index": 2,
                        "document_id": "openalex_works",
                        "provider": "openalex",
                        "requested_url": "https://docs.openalex.org/api-entities/works",
                        "status_code": 301,
                        "outcome": "blocked_redirect",
                        "error_code": "redirect_forbidden",
                        "location": module.TARGET_URL,
                    },
                ],
            },
        )
        monkeypatch.setattr(module, "PRIOR_MANIFEST", prior)
        monkeypatch.setattr(module, "PRIOR_MANIFEST_SHA256", digest)

    elif name.endswith("m20_openalex_works_reference_fetch"):
        campaign, campaign_sha = _write(
            root / "campaign.json",
            {
                "status": "fetched_pending_contract_extraction",
                "campaign_attempted_transaction_count": 3,
                "campaign_accepted_response_body_bytes": 448_240,
                "campaign_transaction_cap": 6,
                "campaign_body_byte_cap": 8_000_000,
            },
        )
        inventory, inventory_sha = _write(
            root / "inventory.json", {"links": [{"url": module.TARGET_URL}]}
        )
        monkeypatch.setattr(module, "PRIOR_CAMPAIGN_MANIFEST", campaign)
        monkeypatch.setattr(module, "PRIOR_CAMPAIGN_SHA256", campaign_sha)
        monkeypatch.setattr(module, "ROOT_LINK_INVENTORY", inventory)
        monkeypatch.setattr(module, "ROOT_LINK_INVENTORY_SHA256", inventory_sha)

    elif name.endswith("m20_openalex_single_work_operation_fetch"):
        campaign, campaign_sha = _write(
            root / "campaign.json",
            {
                "status": "fetched_pending_contract_extraction",
                "campaign_attempted_transaction_count": 4,
                "campaign_accepted_response_body_bytes": 1_168_335,
                "campaign_transaction_cap": 6,
                "campaign_body_byte_cap": 8_000_000,
                "campaign_transactions_remaining": 2,
            },
        )
        body_raw = b'<a href="/api-reference/works/get-a-single-work">single</a> get /works/{id}'
        body, body_sha = _write(root / "works.html", body_raw)
        fetch, fetch_sha = _write(
            root / "fetch.json",
            {
                "requests": [
                    {
                        "outcome": "retained",
                        "requested_url": "https://developers.openalex.org/api-reference/works",
                        "final_url": "https://developers.openalex.org/api-reference/works",
                        "relative_path": "raw/01_openalex_works_reference.html",
                        "sha256": body_sha,
                        "retained_bytes": 720_095,
                    }
                ]
            },
        )
        subplan, subplan_sha = _write(root / "subplan.md", b"test-owned predecessor\n")
        contract, contract_sha = _write(root / "contract.md", b"test-owned contract\n")
        route, route_sha = _write(
            root / "route.json",
            {
                "schema_version": "ra-literature-survey-m20-openalex-works-route-decision-v1",
                "decisions": {
                    key: {"status": "not_documented"}
                    for key in (
                        "authentication_and_cost",
                        "backward_navigation",
                        "forward_citation_filter",
                        "list_search_filter_sort_paging_select",
                        "required_metadata_fields",
                        "single_work_by_arxiv_id",
                        "single_work_by_openalex_id",
                    )
                },
            },
        )
        result, result_sha = _write(root / "result.md", b"test-owned result\n")
        for attr, value in {
            "PRIOR_CAMPAIGN_MANIFEST": campaign,
            "PRIOR_CAMPAIGN_SHA256": campaign_sha,
            "PRIOR_FETCH_MANIFEST": fetch,
            "PRIOR_FETCH_SHA256": fetch_sha,
            "PRIOR_BODY": body,
            "PRIOR_BODY_SHA256": body_sha,
            "PRIOR_SUBPLAN": subplan,
            "PRIOR_SUBPLAN_SHA256": subplan_sha,
            "PRIOR_CONTRACT_EXTRACT": contract,
            "PRIOR_CONTRACT_EXTRACT_SHA256": contract_sha,
            "PRIOR_ROUTE_DECISION": route,
            "PRIOR_ROUTE_DECISION_SHA256": route_sha,
            "PRIOR_RESULT": result,
            "PRIOR_RESULT_SHA256": result_sha,
        }.items():
            monkeypatch.setattr(module, attr, value)

    elif name.endswith("m20_openalex_list_works_operation_fetch"):
        entries: list[tuple[str, Path, str]] = []

        def add(label: str, relative: str, value: bytes | dict) -> None:
            path, digest = _write(root / relative, value)
            entries.append((label, path, digest))

        add("t4_body", "t4.html", b'<a href="/api-reference/works/list-works">list</a> get /works')
        add("t5_subplan", "subplan.md", b"test-owned predecessor\n")
        add("t5_prefetch_ledger", "ledger.json", {})
        add("t5_script", "script.py", b"# test-owned predecessor\n")
        add("t5_tests", "test_script.py", b"# test-owned predecessor\n")
        add("t5_body", "t5.html", b'{\\"name\\":\\"api_key\\",\\"required\\":true}')
        add(
            "t5_fetch_manifest",
            "fetch.json",
            {
                "requests": [
                    {
                        "outcome": "retained",
                        "requested_url": "https://developers.openalex.org/api-reference/works/get-a-single-work",
                        "final_url": "https://developers.openalex.org/api-reference/works/get-a-single-work",
                        "sha256": "76e78cef081b1d4e0c14ca01637163f92a3c430faa2f353f4704b80730d91b97",
                        "retained_bytes": 649_427,
                    }
                ]
            },
        )
        add(
            "t5_campaign_manifest",
            "campaign.json",
            {
                "status": "fetched_pending_contract_extraction",
                "campaign_attempted_transaction_count": 5,
                "campaign_transactions_remaining": 1,
                "campaign_accepted_response_body_bytes": 1_817_762,
                "campaign_transaction_cap": 6,
                "campaign_body_byte_cap": 8_000_000,
            },
        )
        add("t5_contract_extract", "contract.md", b"test-owned contract\n")
        add(
            "t5_route_decision",
            "route.json",
            {"decisions": {"anonymous_api_access": {"status": "contradicted"}}},
        )
        add("t5_result", "result.md", b"test-owned result\n")
        monkeypatch.setattr(module, "PREDECESSORS", tuple(entries))
        monkeypatch.setattr(module, "T4_ROOT", root)
        t5_root = root / "t5-root"
        t5_root.mkdir()
        by_name = {name: path for name, path, _ in entries}
        monkeypatch.setattr(module, "T5_ROOT", t5_root)
        # The validator also reads fixed filenames under T4_ROOT/T5_ROOT.
        (root / "raw").mkdir()
        (root / "raw/01_openalex_works_reference.html").write_bytes(by_name["t4_body"].read_bytes())
        (t5_root / "raw").mkdir()
        (t5_root / "raw/01_openalex_single_work_operation.html").write_bytes(by_name["t5_body"].read_bytes())
        for source_name, target_name in (
            ("t5_fetch_manifest", "fetch_manifest.json"),
            ("t5_campaign_manifest", "campaign_manifest.json"),
            ("t5_route_decision", "route_decision.json"),
        ):
            (t5_root / target_name).write_bytes(by_name[source_name].read_bytes())

    elif name.endswith("m20b1_authentication_pricing_contract_fetch"):
        entries: list[tuple[str, Path, str]] = []
        for label in ("m20a_close", "m20b0_result", "m20b0_review"):
            path, digest = _write(root / f"{label}.md", b"test-owned predecessor\n")
            entries.append((label, path, digest))
        body, body_sha = _write(
            root / "list.html",
            b'<a href="/api-reference/authentication">auth</a>'
            b'<a href="/api-reference/rate-limits/check-rate-limit-status">rate</a>',
        )
        route, route_sha = _write(root / "route.json", {})
        entries.extend(
            (("m20a_t6_body", body, body_sha), ("m20a_t6_route_decision", route, route_sha))
        )
        monkeypatch.setattr(module, "PREDECESSORS", tuple(entries))
        t6_root = root / "t6-root"
        (t6_root / "raw").mkdir(parents=True)
        (t6_root / "raw/01_openalex_list_works_operation.html").write_bytes(body.read_bytes())
        monkeypatch.setattr(module, "T6_ROOT", t6_root)

    elif name.endswith("m20b4_closeout"):
        packet = Path(
            "docs/validation/literature_survey_m20b3_identified_integration_2026-07-15/"
            "m20b4_live_packet.json"
        ).resolve(strict=True)
        monkeypatch.setattr(module, "FROZEN_PACKET_PATH", packet)
