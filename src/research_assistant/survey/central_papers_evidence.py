"""Source-grounded inference and scholarly ledgers for central-paper campaigns."""

from __future__ import annotations

import re
from typing import Any

from research_assistant.survey.centrality import assess_centrality, validate_centrality_evidence
from research_assistant.survey.discovery_quality import informative_tokens


CLASSIFIER_VERSION = "source_grounded_conservative_v1"
CORE_ROLES = {
    "COMPETITOR", "DIRECT_METHOD", "FOUNDATIONAL", "SURVEY_OR_TUTORIAL"
}
NONCLAIMS = [
    "literature completeness",
    "paper claim correctness",
    "publication readiness",
    "statistically supported paper ranking",
    "universal topic recall",
]
LEDGER_NAMES = (
    "source_support",
    "citation_venue_metadata",
    "backward_snowball",
    "forward_snowball",
    "claim_support",
    "omitted_paper_risks",
)
LEDGER_SCHEMA = "ra-survey-central-papers-ledger-v1"
_TECHNICAL_TITLE_TERMS = {
    "algorithm", "analysis", "appendix", "derivation", "evaluation",
    "experiment", "framework", "method", "model", "optimization",
    "privacy", "proof", "protocol", "result", "security", "theorem",
    "theory",
}


def _technical_sections(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for section in candidate["source"]["sections"]:
        title_tokens = set(re.findall(r"[a-z0-9]+", section["title"].casefold()))
        text = section["text"].casefold()
        structural = bool(title_tokens & _TECHNICAL_TITLE_TERMS)
        explicit = any(cue in text for cue in (
            r"\begin{algorithm", r"\begin{equation", r"\begin{theorem",
            r"\begin{lemma", r"\begin{proposition", r"\[", "$$",
        ))
        if structural or explicit:
            rows.append(section)
    return rows


def _topic_fit(
    topic_contract: dict[str, Any], technical_sections: list[dict[str, Any]]
) -> tuple[str, list[str]]:
    if not technical_sections:
        return "not_checked", []
    tokens = set(informative_tokens(" ".join(
        section["text"] for section in technical_sections
    ).casefold()))
    exclusions = [
        facet for facet in topic_contract["exclusions"]
        if set(informative_tokens(facet)) <= tokens
    ]
    if exclusions:
        return "off_topic", exclusions
    statuses = []
    for facet in topic_contract["required_facets"]:
        facet_tokens = set(informative_tokens(facet))
        statuses.append(bool(facet_tokens) and facet_tokens <= tokens)
    matched = [
        facet
        for facet, status in zip(topic_contract["required_facets"], statuses, strict=True)
        if status
    ]
    if statuses and all(statuses):
        return "direct", matched
    if any(statuses):
        return "relevant", matched
    return "off_topic", []


def _inspected_role(
    candidate: dict[str, Any], fit: str, sections: list[dict[str, Any]]
) -> list[str]:
    if fit == "off_topic":
        return ["BACKGROUND"]
    if fit == "relevant":
        return ["PERIPHERAL"]
    if fit not in {"direct", "foundational"}:
        return []
    corpus = " ".join([candidate["title"], *(section["text"] for section in sections)]).casefold()
    if any(cue in corpus for cue in ("this survey", "we survey", "we review", "open problems")):
        return ["SURVEY_OR_TUTORIAL"]
    if any(cue in corpus for cue in ("we term this", "we term our", "seminal", "foundational")):
        return ["FOUNDATIONAL"]
    if any(cue in corpus for cue in (
        "we develop", "we introduce", "we present", "we propose", "protocol", "algorithm"
    )):
        return ["DIRECT_METHOD"]
    return ["BACKGROUND"]


def _blocked_role_hypothesis(
    candidate: dict[str, Any], backward_mentions: list[str]
) -> list[str]:
    if not backward_mentions:
        return ["SOURCE_BLOCKED"]
    title = candidate["title"].casefold()
    if any(cue in title for cue in ("survey", "tutorial", "review")):
        role = "SURVEY_OR_TUTORIAL"
    elif any(cue in title for cue in ("benchmark", "comparison", "evaluation")):
        role = "COMPETITOR"
    elif any(cue in title for cue in (
        "collapse", "curse", "foundation", "fundamental", "seminal"
    )):
        role = "FOUNDATIONAL"
    else:
        return ["SOURCE_BLOCKED"]
    return sorted({role, "SOURCE_BLOCKED"})


def _backward_graph(
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], list[dict[str, Any]], list[dict[str, Any]]]:
    known = {candidate["paper_id"] for candidate in candidates}
    mentions: dict[str, set[str]] = {paper_id: set() for paper_id in known}
    edges = []
    unresolved = []
    for origin in candidates:
        for entry in origin["source"]["bibliography"]:
            target = entry["paper_id"]
            edge = {
                "origin_paper_id": origin["paper_id"],
                "target_paper_id": target,
                "target_title": entry["title"],
                "evidence_ref": entry["evidence_ref"],
                "resolution": "resolved" if target in known else "unresolved",
                "action": "classify" if target in known else "inspect_next_if_budget_allows",
            }
            edges.append(edge)
            if target in known:
                mentions[target].add(origin["paper_id"])
            else:
                unresolved.append(edge)
    edges.sort(key=lambda item: (
        item["origin_paper_id"], item["target_paper_id"] or "", item["target_title"] or ""
    ))
    return mentions, edges, unresolved


def _classify_candidates(
    topic: dict[str, Any], candidates: list[dict[str, Any]], backward: dict[str, set[str]]
) -> dict[str, dict[str, Any]]:
    derived = {}
    for candidate in candidates:
        sections = _technical_sections(candidate)
        fit, matched_facets = _topic_fit(topic, sections)
        source_status = "inspected" if sections else (
            "source_blocked" if candidate["source"]["status"] != "available" else "metadata_only"
        )
        derived[candidate["paper_id"]] = {
            "candidate": candidate,
            "technical_sections": sections,
            "topic_fit": fit,
            "matched_facets": matched_facets,
            "source_status": source_status,
            "roles": _inspected_role(candidate, fit, sections),
            "backward_mentions": sorted(backward[candidate["paper_id"]]),
        }
    survey_ids = {
        paper_id for paper_id, row in derived.items()
        if "SURVEY_OR_TUTORIAL" in row["roles"] and row["source_status"] == "inspected"
    }
    for row in derived.values():
        if row["source_status"] == "source_blocked":
            row["roles"] = _blocked_role_hypothesis(
                row["candidate"], row["backward_mentions"]
            )
        row["survey_mentions"] = sorted(set(row["backward_mentions"]) & survey_ids)
    return derived


def _candidate_rows(
    row: dict[str, Any], accessed_at: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any] | None]:
    candidate = row["candidate"]
    paper_id = candidate["paper_id"]
    safety = {
        "no_issue_found": "clear",
        "not_checked": "not_checked",
        "quarantined": "quarantined",
    }[candidate["safety"]["status"]]
    inspected_refs = [section["evidence_ref"] for section in row["technical_sections"]]
    evidence_refs = sorted(set(inspected_refs + [candidate["source"]["evidence_ref"]]))
    limitations = set(candidate["limitations"] + candidate["safety"]["limitations"])
    limitations.add(
        "source-grounded topic and role classification is deterministic heuristic evidence, not expert judgment"
    )
    if row["source_status"] == "source_blocked" and len(row["roles"]) > 1:
        limitations.add(
            "scholarly role is an unverified blocked hypothesis from inspected citation context and title metadata"
        )
    if candidate["forward_citation_status"] != "available":
        limitations.add(f"forward citation coverage is {candidate['forward_citation_status']}")
    risk = "open" if (
        row["source_status"] != "inspected"
        or safety != "clear"
        or candidate["forward_citation_status"] in {"not_available", "capped"}
    ) else "partially_closed"
    evidence = {
        "paper_id": paper_id,
        "title": candidate["title"],
        "identity_status": candidate["identity_status"],
        "source_status": row["source_status"],
        "source_safety": safety,
        "topic_fit": row["topic_fit"],
        "roles": sorted(row["roles"]),
        "inspected_anchors": sorted(
            section["anchor_id"] for section in row["technical_sections"]
        ),
        "discovery_routes": candidate["discovery_routes"],
        "backward_mentions": row["backward_mentions"],
        "forward_citations": candidate["forward_citations"],
        "survey_mentions": row["survey_mentions"],
        "omission_risk_status": risk,
        "citation_count": candidate["citation_count"],
        "venue_metric_status": candidate["venue_metric_status"],
        "evidence_refs": evidence_refs,
        "source_safety_evidence": candidate["safety"]["evidence_refs"],
        "reviewer_provenance": [f"classifier:{CLASSIFIER_VERSION}"],
        "limitations": sorted(limitations),
    }
    ledger_rows = {
        "source_support": {
            "paper_id": paper_id,
            "source_status": row["source_status"],
            "source_type": candidate["source"]["source_type"],
            "source_evidence_ref": candidate["source"]["evidence_ref"],
            "inspected_technical_anchors": evidence["inspected_anchors"],
            "matched_required_facets": row["matched_facets"],
            "safety_status": safety,
            "safety_evidence_refs": candidate["safety"]["evidence_refs"],
            "allowed_support": "topic_fit_and_role_context_only" if row["source_status"] == "inspected" else "none",
            "forbidden_support": "paper_claim_correctness",
        },
        "citation_venue_metadata": {
            "paper_id": paper_id,
            "citation_count": candidate["citation_count"],
            "venue_metric_status": candidate["venue_metric_status"],
            "accessed_at": accessed_at,
            "priority_signal_only": True,
        },
        "forward_snowball": {
            "paper_id": paper_id,
            "status": candidate["forward_citation_status"],
            "citing_paper_ids": candidate["forward_citations"],
            "accessed_at": accessed_at,
            "action": "recorded" if candidate["forward_citation_status"] in {"available", "empty"} else "provider_gap",
        },
        "claim_support": {
            "paper_id": paper_id,
            "support_class": "SURVEY_CONTEXT_ONLY" if row["source_status"] == "inspected" else "SOURCE_GAP_BLOCKER",
            "supported_scope": "topic_fit_and_scholarly_role_context" if row["source_status"] == "inspected" else "none",
            "evidence_refs": evidence_refs,
            "paper_claim_correctness_supported": False,
        },
    }
    omission = None
    if risk == "open":
        omission = {
            "risk_id": f"candidate:{paper_id}",
            "paper_id": paper_id,
            "status": "open",
            "reason": "source, safety, or forward-citation coverage remains blocked",
            "next_action": "inspect the best available source or restore the unavailable provider within budget",
        }
    return evidence, ledger_rows, omission


def _ledger(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": LEDGER_SCHEMA,
        "ledger": name,
        "rows": rows,
        "benchmark_labels_consumed": False,
        "what_is_not_concluded": NONCLAIMS,
    }


def derive_campaign_evidence(
    contract: dict[str, Any], observations: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Derive centrality evidence and all six ledgers from normalized observations."""
    candidates = observations["candidates"]
    backward, backward_edges, unresolved = _backward_graph(candidates)
    derived = _classify_candidates(contract["topic_contract"], candidates, backward)
    evidence_rows = []
    ledger_rows = {name: [] for name in LEDGER_NAMES}
    ledger_rows["backward_snowball"] = backward_edges
    omission_rows = ledger_rows["omitted_paper_risks"]
    for paper_id in sorted(derived):
        evidence, candidate_ledgers, omission = _candidate_rows(
            derived[paper_id], observations["accessed_at"]
        )
        evidence_rows.append(evidence)
        for name, row in candidate_ledgers.items():
            ledger_rows[name].append(row)
        if omission is not None:
            omission_rows.append(omission)
    evidence = validate_centrality_evidence({
        "schema_version": "ra-survey-centrality-evidence-v1",
        "topic_contract_sha256": contract["topic_contract_sha256"],
        "candidates": evidence_rows,
        "what_is_not_concluded": ["literature completeness", "paper claim correctness"],
    }, expected_contract_sha256=contract["topic_contract_sha256"])
    assessment = assess_centrality(contract["topic_contract"], evidence)
    validated_roles = {
        role
        for assessment_row in assessment["assessments"]
        if assessment_row["verdict"] == "VALIDATED_CENTRAL"
        for role in assessment_row["roles"]
    }
    for role in sorted(CORE_ROLES - validated_roles):
        omission_rows.append({
            "risk_id": f"role:{role.casefold()}",
            "paper_id": None,
            "status": "open",
            "reason": f"no validated central candidate covers {role}",
            "next_action": "run a bounded role-directed discovery and source-inspection round",
        })
    omission_rows.sort(key=lambda item: item["risk_id"])
    ledgers = {name: _ledger(name, ledger_rows[name]) for name in LEDGER_NAMES}
    diagnostics = {
        "unresolved_backward_references": unresolved,
        "validated_roles": sorted(validated_roles),
        "uncovered_roles": sorted(CORE_ROLES - validated_roles),
        "open_risk_ids": sorted(item["risk_id"] for item in omission_rows),
    }
    return ledgers, evidence, {"assessment": assessment, "diagnostics": diagnostics}


__all__ = [
    "CLASSIFIER_VERSION", "CORE_ROLES", "LEDGER_NAMES", "LEDGER_SCHEMA",
    "NONCLAIMS", "derive_campaign_evidence",
]
