"""Bounded OpenAlex/arXiv provider for central-paper campaigns."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_assistant.ingest.source_manifest import canonical_paper_id
from research_assistant.source.arxiv_source import (
    DEFAULT_MAX_SOURCE_PACKAGE_BYTES,
    fetch_arxiv_structured_source,
)
from research_assistant.survey.oa_pdf_source import fetch_open_access_pdf
from research_assistant.survey.central_papers_observations import (
    CAPABILITY_MANIFEST_SCHEMA,
    OBSERVATION_SCHEMA,
    CentralPapersCapability,
    FileObservationCapability,
    capability_manifest,
    validate_capability_manifest,
    validate_observations,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.topic_contract import topic_contract_sha256
from research_assistant.survey.topic_seed_discovery import (
    OPENALEX_SELECT,
    OpenAlexTopicBootstrapCapability,
)


_ARXIV = re.compile(r"^(?P<id>.+?)(?:v\d+)?$", re.IGNORECASE)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise MissionStateError(
            "invalid_central_papers_observations", f"{field} must be nonempty text"
        )
    return " ".join(value.split())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        raise MissionStateError("central_papers_provider_redirect", "OpenAlex request redirected")


@dataclass
class _CollectionUsage:
    metadata_requests: int = 0
    metadata_records: int = 0
    source_attempts: int = 0
    source_bytes: int = 0
    source_available: int = 0
    source_blocked: int = 0

    def budget_consumption(self) -> dict[str, int]:
        return {
            "metadata_records": self.metadata_records,
            "metadata_requests": self.metadata_requests,
            "source_attempts": self.source_attempts,
            "source_bytes": self.source_bytes,
        }


@dataclass
class OpenAlexArxivCentralPapersCapability:
    campaign_root: Path
    name: str = "openalex_arxiv_central_papers"
    network_required: bool = True

    @property
    def fingerprint(self) -> str:
        policy = {
            "version": 3,
            "discovery": OpenAlexTopicBootstrapCapability().version,
            "source": "arxiv_structured_source_v1",
            "forward_cap": 3,
            "graph_rounds": "bounded_openalex_reference_and_citing_expansion_v1",
        }
        return sha256_bytes(canonical_json_bytes(policy))

    def collect(self, topic_contract: dict[str, Any], budget: dict[str, int]) -> dict[str, Any]:
        accessed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        discovery_budget = self._discovery_budget(budget)
        outcome = OpenAlexTopicBootstrapCapability().run({
            "normalized_topic": {"display": topic_contract["topic"]},
            "discovery_budget": discovery_budget,
        })
        descriptive = outcome.get("descriptive") or {}
        consumption = descriptive.get("budget_consumption") or {}
        usage = _CollectionUsage(
            metadata_requests=int(consumption.get("metadata_requests") or 0),
            metadata_records=int(consumption.get("provider_rows") or 0),
        )
        candidates = []
        seen_paper_ids: set[str] = set()
        seen_openalex_ids: set[str] = set()
        pending: list[tuple[dict[str, Any], int, list[str], list[str]]] = [
            (selected, 0, [], [])
            for selected in outcome.get("selected_candidates") or []
        ]
        for round_index in range(budget["max_rounds"]):
            frontier = self._process_round(
                pending=pending,
                round_index=round_index,
                candidates=candidates,
                seen_paper_ids=seen_paper_ids,
                seen_openalex_ids=seen_openalex_ids,
                usage=usage,
                budget=budget,
                accessed_at=accessed_at,
            )
            pending = self._next_pending(
                frontier=frontier,
                round_index=round_index,
                candidate_count=len(candidates),
                seen_openalex_ids=seen_openalex_ids,
                usage=usage,
                budget=budget,
            )
            if not pending:
                break
        candidates.sort(key=lambda item: item["paper_id"])
        status = outcome.get("outcome")
        discovery_status = {
            "selected": "available", "empty": "empty", "unavailable": "not_available",
            "capped": "capped",
        }.get(status, "not_available")
        return validate_observations({
            "schema_version": OBSERVATION_SCHEMA,
            "topic_contract_sha256": topic_contract_sha256(topic_contract),
            "capability_fingerprint": self.fingerprint,
            "accessed_at": accessed_at,
            "discovery_status": discovery_status,
            "provider_statuses": sorted([
                {
                    "provider": "arxiv_source",
                    "status": "available" if usage.source_available else "not_available",
                    "detail": (
                        f"available={usage.source_available}; blocked_or_failed={usage.source_blocked}; "
                        f"attempts={usage.source_attempts}"
                    ),
                },
                {
                    "provider": "openalex",
                    "status": discovery_status,
                    "detail": f"topic bootstrap outcome={status}",
                },
            ], key=lambda item: item["provider"]),
            "candidates": candidates,
            "budget_consumption": usage.budget_consumption(),
            "limitations": [
                "arXiv structured source is the only autonomous full-text source adapter",
                "forward citation queries retain only the first three observed identities",
                "reference and citing expansion is bounded by the shared round, request, record, and candidate budgets",
                "source safety is limited to the OpenAlex retraction flag present in discovery metadata",
            ],
            "benchmark_labels_consumed": False,
        })

    @staticmethod
    def _discovery_budget(budget: dict[str, int]) -> dict[str, Any]:
        return {
            "providers": ["openalex"],
            "allowed_domains": ["api.openalex.org"],
            "max_metadata_requests": budget["max_metadata_requests"],
            "max_records_per_metadata_response": 25,
            "max_total_metadata_records": budget["max_metadata_records"],
            "max_unique_candidates": budget["max_candidates"],
            "max_bytes_per_metadata_response": 2_000_000,
            "max_total_metadata_bytes": 48_000_000,
            "max_total_source_bytes": budget["max_total_source_bytes"],
            "max_pages_per_query": 2,
            "max_selected_seeds": min(
                budget["max_candidates"], budget["max_source_attempts"]
            ),
        }

    def _process_round(
        self,
        *,
        pending: list[tuple[dict[str, Any], int, list[str], list[str]]],
        round_index: int,
        candidates: list[dict[str, Any]],
        seen_paper_ids: set[str],
        seen_openalex_ids: set[str],
        usage: _CollectionUsage,
        budget: dict[str, int],
        accessed_at: str,
    ) -> dict[str, dict[str, Any]]:
        frontier: dict[str, dict[str, Any]] = {}
        for selected, selected_round, origins, routes in pending:
            if selected_round != round_index or len(candidates) >= budget["max_candidates"]:
                continue
            selected = _with_discovery_routes(selected, routes)
            candidate = self._candidate(selected, accessed_at=accessed_at)
            if candidate["paper_id"] in seen_paper_ids:
                continue
            candidate["discovery_round"] = round_index
            candidate["discovery_origins"] = sorted(set(origins))
            self._acquire_source(candidate, selected=selected, usage=usage, budget=budget)
            openalex_id = candidate["identifiers"]["openalex_id"]
            if isinstance(openalex_id, str):
                seen_openalex_ids.add(openalex_id.casefold())
            forward_rows = self._collect_forward(
                candidate, openalex_id=openalex_id, usage=usage, budget=budget
            )
            candidates.append(candidate)
            seen_paper_ids.add(candidate["paper_id"])
            if round_index + 1 < budget["max_rounds"]:
                _extend_frontier(frontier, candidate, selected, forward_rows)
        return frontier

    def _acquire_source(
        self,
        candidate: dict[str, Any],
        *,
        selected: dict[str, Any],
        usage: _CollectionUsage,
        budget: dict[str, int],
    ) -> None:
        arxiv_id = candidate["identifiers"]["arxiv_id"]
        remaining_bytes = budget["max_total_source_bytes"] - usage.source_bytes
        identifier = candidate["paper_id"]
        if usage.source_attempts >= budget["max_source_attempts"] or remaining_bytes <= 0:
            return
        usage.source_attempts += 1
        if arxiv_id:
            record = fetch_arxiv_structured_source(
                arxiv_id,
                root=self.campaign_root,
                paper_id=canonical_paper_id(identifier),
                max_bytes=min(DEFAULT_MAX_SOURCE_PACKAGE_BYTES, remaining_bytes),
            ).to_dict()
        else:
            pdf_url = (selected.get("descriptive") or {}).get("open_access_pdf_url")
            if not isinstance(pdf_url, str) or not pdf_url:
                usage.source_attempts -= 1
                return
            record = fetch_open_access_pdf(
                pdf_url,
                root=self.campaign_root,
                paper_id=canonical_paper_id(identifier),
                expected_title=candidate["title"],
                max_bytes=min(DEFAULT_MAX_SOURCE_PACKAGE_BYTES, remaining_bytes),
            )
        candidate["source"] = _source_observation(record, identifier)
        if candidate["source"]["status"] == "available":
            usage.source_available += 1
        else:
            usage.source_blocked += 1
        source_path = record.get("original_source_path") or record.get("local_path")
        if isinstance(source_path, str) and Path(source_path).is_file():
            usage.source_bytes += Path(source_path).stat().st_size

    def _collect_forward(
        self,
        candidate: dict[str, Any],
        *,
        openalex_id: Any,
        usage: _CollectionUsage,
        budget: dict[str, int],
    ) -> list[dict[str, Any]]:
        if not openalex_id or usage.metadata_requests >= budget["max_metadata_requests"]:
            return []
        status, citations, rows = self._forward(openalex_id)
        usage.metadata_requests += 1
        remaining_records = budget["max_metadata_records"] - usage.metadata_records
        if len(rows) > remaining_records:
            status = "capped"
            rows = rows[:max(0, remaining_records)]
            retained = {
                f"openalex:{str((row.get('descriptive') or {}).get('openalex_id')).casefold()}"
                for row in rows
            }
            citations = [paper_id for paper_id in citations if paper_id in retained]
        usage.metadata_records += len(rows)
        candidate["forward_citation_status"] = status
        candidate["forward_citations"] = citations
        return rows

    def _next_pending(
        self,
        *,
        frontier: dict[str, dict[str, Any]],
        round_index: int,
        candidate_count: int,
        seen_openalex_ids: set[str],
        usage: _CollectionUsage,
        budget: dict[str, int],
    ) -> list[tuple[dict[str, Any], int, list[str], list[str]]]:
        pending = []
        for openalex_key in sorted(frontier):
            if candidate_count + len(pending) >= budget["max_candidates"]:
                break
            if openalex_key in seen_openalex_ids:
                continue
            row = frontier[openalex_key]
            selected = row["selected"]
            if selected is None:
                if (
                    usage.metadata_requests >= budget["max_metadata_requests"]
                    or usage.metadata_records >= budget["max_metadata_records"]
                ):
                    break
                selected = self._work(openalex_key)
                usage.metadata_requests += 1
                if selected is None:
                    continue
                usage.metadata_records += 1
            pending.append((selected, round_index + 1, row["origins"], row["routes"]))
        return pending

    def _candidate(self, selected: dict[str, Any], *, accessed_at: str) -> dict[str, Any]:
        description = selected.get("descriptive") or {}
        identifier = _canonical_identifier(selected.get("display"))
        identifier_evidence = selected.get("identifier_evidence") or []
        arxiv_alias = next(
            (
                value.split(":", 1)[1]
                for value in identifier_evidence
                if isinstance(value, str) and value.casefold().startswith("arxiv:")
            ),
            None,
        )
        arxiv_id = (
            identifier.split(":", 1)[1]
            if identifier.startswith("arxiv:")
            else arxiv_alias
        )
        openalex_id = description.get("openalex_id")
        is_retracted = description.get("is_retracted")
        if is_retracted is True:
            safety_status = "quarantined"
            safety_refs = [f"metadata:openalex:{str(openalex_id).casefold()}:is_retracted=true:{accessed_at}"]
        elif is_retracted is False:
            safety_status = "no_issue_found"
            safety_refs = [f"metadata:openalex:{str(openalex_id).casefold()}:is_retracted=false:{accessed_at}"]
        else:
            safety_status = "not_checked"
            safety_refs = []
        return {
            "paper_id": identifier,
            "title": (selected.get("title_evidence") or [identifier])[0],
            "authors": sorted(description.get("authors") or []),
            "year": description.get("year"),
            "identifiers": {
                "arxiv_id": arxiv_id,
                "doi": identifier.split(":", 1)[1] if identifier.startswith("doi:") else None,
                "openalex_id": openalex_id,
            },
            "identity_status": "conflict" if description.get("identity_conflict") else "resolved",
            "discovery_round": 0,
            "discovery_routes": sorted(description.get("query_layers") or []),
            "discovery_origins": [],
            "citation_count": description.get("citation_count"),
            "venue_metric_status": (description.get("venue_metric") or {}).get("status", "not_available"),
            "source": {
                "status": "source_blocked",
                "source_type": "not_available",
                "evidence_ref": f"metadata:openalex:{str(openalex_id).casefold()}:{accessed_at}",
                "sections": [],
                "bibliography": [],
            },
            "safety": {
                "status": safety_status,
                "evidence_refs": sorted(safety_refs),
                "limitations": ["publisher errata and expressions of concern were not comprehensively checked"],
            },
            "forward_citation_status": "not_available",
            "forward_citations": [],
            "limitations": ["metadata nomination is not topic fit or centrality evidence"],
        }

    @staticmethod
    def _forward(openalex_id: str) -> tuple[str, list[str], list[dict[str, Any]]]:
        params = urllib.parse.urlencode({
            "filter": f"cites:{openalex_id}",
            "sort": "cited_by_count:desc",
            "per-page": "3",
            "select": OPENALEX_SELECT,
        })
        url = f"https://api.openalex.org/works?{params}"
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(url, timeout=30) as response:
                if response.geturl() != url:
                    raise MissionStateError("central_papers_provider_redirect", "OpenAlex request redirected")
                raw = response.read(2_000_001)
        except MissionStateError:
            raise
        except Exception:
            return "not_available", [], []
        if len(raw) > 2_000_000:
            return "capped", [], []
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "not_available", [], []
        results = value.get("results") if isinstance(value, dict) else None
        if not isinstance(results, list):
            return "not_available", [], []
        rows = []
        selected_rows = []
        for item in results:
            raw_id = item.get("id") if isinstance(item, dict) else None
            if isinstance(raw_id, str) and raw_id.startswith("https://openalex.org/W"):
                rows.append(f"openalex:{raw_id.rsplit('/', 1)[-1].casefold()}")
                selected = _selected_from_openalex_work(item)
                if selected is not None:
                    selected_rows.append(selected)
        normalized = sorted(set(rows))
        return ("available" if normalized else "empty"), normalized, selected_rows

    @staticmethod
    def _work(openalex_id: str) -> dict[str, Any] | None:
        normalized = openalex_id.rsplit(":", 1)[-1].upper()
        params = urllib.parse.urlencode({"select": OPENALEX_SELECT})
        url = f"https://api.openalex.org/works/{normalized}?{params}"
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(url, timeout=30) as response:
                if response.geturl() != url:
                    raise MissionStateError("central_papers_provider_redirect", "OpenAlex request redirected")
                raw = response.read(2_000_001)
        except MissionStateError:
            raise
        except Exception:
            return None
        if len(raw) > 2_000_000:
            return None
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return _selected_from_openalex_work(value)


def _canonical_identifier(value: Any) -> str:
    text = _text(value, "candidate identifier").casefold()
    if text.startswith("arxiv:"):
        raw = text.split(":", 1)[1]
        match = _ARXIV.fullmatch(raw)
        return f"arxiv:{match.group('id') if match else raw}"
    return text


def _with_discovery_routes(selected: dict[str, Any], routes: list[str]) -> dict[str, Any]:
    if not routes:
        return selected
    row = dict(selected)
    descriptive = dict(row.get("descriptive") or {})
    descriptive["query_layers"] = sorted(set(descriptive.get("query_layers") or []) | set(routes))
    row["descriptive"] = descriptive
    return row


def _enqueue_openalex(
    frontier: dict[str, dict[str, Any]],
    value: Any,
    *,
    origin: str,
    route: str,
    selected: dict[str, Any] | None = None,
) -> None:
    if not isinstance(value, str) or not value.strip():
        return
    key = value.strip().casefold().rstrip("/").rsplit("/", 1)[-1]
    key = key.rsplit(":", 1)[-1]
    if not re.fullmatch(r"w\d+", key):
        return
    row = frontier.setdefault(key, {"origins": [], "routes": [], "selected": None})
    row["origins"] = sorted(set(row["origins"]) | {origin})
    row["routes"] = sorted(set(row["routes"]) | {route})
    if row["selected"] is None and selected is not None:
        row["selected"] = selected


def _extend_frontier(
    frontier: dict[str, dict[str, Any]],
    candidate: dict[str, Any],
    selected: dict[str, Any],
    forward_rows: list[dict[str, Any]],
) -> None:
    description = selected.get("descriptive") or {}
    for reference in description.get("referenced_works") or []:
        _enqueue_openalex(
            frontier,
            reference,
            origin=candidate["paper_id"],
            route="metadata_reference_graph",
        )
    for row in forward_rows:
        _enqueue_openalex(
            frontier,
            (row.get("descriptive") or {}).get("openalex_id"),
            origin=candidate["paper_id"],
            route="forward_snowball",
            selected=row,
        )


def _selected_from_openalex_work(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    raw_id = value.get("id")
    title = value.get("display_name")
    if not isinstance(raw_id, str) or not raw_id.startswith("https://openalex.org/W"):
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    openalex_id = raw_id.rstrip("/").rsplit("/", 1)[-1]
    authors = []
    for authorship in value.get("authorships") or []:
        author = authorship.get("author") if isinstance(authorship, dict) else None
        name = author.get("display_name") if isinstance(author, dict) else None
        if isinstance(name, str) and name.strip():
            authors.append(" ".join(name.split()))
    identifiers = value.get("ids") if isinstance(value.get("ids"), dict) else {}
    arxiv = identifiers.get("arxiv")
    if isinstance(arxiv, str) and arxiv.strip():
        display = f"arxiv:{arxiv.rstrip('/').rsplit('/', 1)[-1].removesuffix('.pdf').casefold()}"
    else:
        doi = value.get("doi")
        if isinstance(doi, str) and doi.strip():
            display = f"doi:{doi.strip().casefold().removeprefix('https://doi.org/')}"
        else:
            display = f"openalex:{openalex_id.casefold()}"
    references = sorted({
        item.rstrip("/").rsplit("/", 1)[-1]
        for item in value.get("referenced_works") or []
        if isinstance(item, str) and item.startswith("https://openalex.org/W")
    })
    retracted = value.get("is_retracted")
    if type(retracted) is not bool:
        retracted = None
    return {
        "paper_key": f"openalex:{openalex_id.casefold()}",
        "display": display,
        "identifier_evidence": sorted({display, f"openalex:{openalex_id.casefold()}"}),
        "title_evidence": [" ".join(title.split())],
        "descriptive": {
            "authors": sorted(set(authors)),
            "year": value.get("publication_year") if type(value.get("publication_year")) is int else None,
            "openalex_id": openalex_id,
            "query_layers": [],
            "identity_conflict": False,
            "citation_count": value.get("cited_by_count") if type(value.get("cited_by_count")) is int else None,
            "venue_metric": {"status": "not_available"},
            "referenced_works": references,
            "is_retracted": retracted,
            "metadata_only": True,
            "citation_and_venue_are_priority_signals_only": True,
        },
    }


def _source_observation(record: dict[str, Any], paper_id: str) -> dict[str, Any]:
    status = record.get("status")
    if status != "available":
        return {
            "status": "source_blocked" if status in {"unavailable", "blocked"} else "parse_failed",
            "source_type": str(record.get("source_type") or "not_available"),
            "evidence_ref": f"source-record:{paper_id}:{status}",
            "sections": [],
            "bibliography": [],
        }
    sections = []
    for index, section in enumerate(record.get("sections") or []):
        title = str(section.get("title") or "").strip()
        text = str(section.get("raw_latex") or section.get("text") or "").strip()
        if not title or not text:
            continue
        anchor_id = str(section.get("anchor_id") or _section_anchor(section, index))
        sections.append({
            "anchor_id": anchor_id,
            "title": " ".join(title.split()),
            "text": " ".join(text.split())[:100_000],
            "evidence_ref": str(
                section.get("evidence_ref") or f"source-record:{paper_id}:{anchor_id}"
            ),
        })
    bibliography_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for index, entry in enumerate(record.get("bibliography") or []):
        fields = entry.get("fields") if isinstance(entry, dict) else None
        if not isinstance(fields, dict):
            continue
        identifier = _bibliography_identifier(fields)
        title = fields.get("title")
        if identifier is None and not isinstance(title, str):
            continue
        row = {
            "paper_id": identifier,
            "title": " ".join(title.split()) if isinstance(title, str) and title.strip() else None,
            "evidence_ref": f"source-record:{paper_id}:bibliography:{index}",
        }
        key = (row["paper_id"] or "", row["title"] or "")
        bibliography_by_key.setdefault(key, row)
    bibliography = [bibliography_by_key[key] for key in sorted(bibliography_by_key)]
    return {
        "status": "available",
        "source_type": str(record.get("source_type") or "structured_source"),
        "evidence_ref": f"source-record:{paper_id}:available",
        "sections": sorted(sections, key=lambda item: item["anchor_id"]),
        "bibliography": bibliography,
    }


def _section_anchor(section: dict[str, Any], index: int) -> str:
    labels = section.get("labels") or []
    if labels and isinstance(labels[0], str):
        return f"section:{labels[0]}"
    line = section.get("line")
    return f"section:line-{line if type(line) is int else index}"


def _bibliography_identifier(fields: dict[str, Any]) -> str | None:
    doi = fields.get("doi")
    if isinstance(doi, str) and doi.strip():
        return f"doi:{doi.strip().casefold().removeprefix('https://doi.org/')}"
    for key in ("eprint", "arxiv", "arxivid"):
        value = fields.get(key)
        if isinstance(value, str) and value.strip():
            return f"arxiv:{value.strip().casefold()}"
    return None


__all__ = [
    "CAPABILITY_MANIFEST_SCHEMA", "OBSERVATION_SCHEMA", "CentralPapersCapability",
    "FileObservationCapability", "OpenAlexArxivCentralPapersCapability",
    "capability_manifest", "validate_capability_manifest", "validate_observations",
]
