"""Project authoritative survey artifacts into the document evidence contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from research_assistant.survey.central_papers import validate_central_papers_campaign

from .contracts import (
    CONTRACT_SCHEMA,
    EVIDENCE_SCHEMA,
    DocumentInputError,
    write_json,
)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise DocumentInputError(f"{label} must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DocumentInputError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise DocumentInputError(f"{label} must be a JSON object")
    return value


def _last_observations(root: Path) -> dict[str, Any]:
    rounds = sorted((root / "rounds").glob("round-*.json"))
    if not rounds:
        raise DocumentInputError("central campaign has no replay checkpoint")
    checkpoint = _load(rounds[-1], "central campaign checkpoint")
    observations = checkpoint.get("observations")
    if not isinstance(observations, dict):
        raise DocumentInputError("central campaign checkpoint has no observations")
    return observations


def _contract(topic: str) -> dict[str, Any]:
    return {
        "schema_version": CONTRACT_SCHEMA,
        "reader": "A technically literate researcher",
        "purpose": "Produce a source-attributed survey candidate from checked source sections.",
        "motivation": "Organize inspected source evidence by topic-relevant mechanisms rather than acquisition order.",
        "answer_target": "Report what the inspected sources state about the topic within the recorded scope.",
        "claim_boundary": "Statements are attributed to checked source sections and are not independent scientific validation.",
        "nonclaims": [
            "literature completeness",
            "universal centrality recall",
            "scientific correctness",
            "publication readiness",
            "independent semantic source verification",
        ],
    }


def project_central_campaign(*, campaign_root: Path, output_dir: Path) -> dict[str, Any]:
    """Project a replay-valid central-paper campaign into source-attributed evidence."""
    root = campaign_root.expanduser().resolve()
    validated = validate_central_papers_campaign(root)
    report = validated["report"]
    observations = _last_observations(root)
    evidence = _load(root / "centrality_evidence.json", "centrality evidence")
    by_id = {row.get("paper_id"): row for row in observations.get("candidates", [])}
    evidence_by_id = {row.get("paper_id"): row for row in evidence.get("candidates", [])}
    papers: list[dict[str, Any]] = []
    anchors: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    used_papers: set[str] = set()
    for paper_id, evidence_row in sorted(evidence_by_id.items()):
        candidate = by_id.get(paper_id)
        if not isinstance(candidate, dict):
            continue
        source = candidate.get("source") or {}
        if (
            evidence_row.get("topic_fit") not in {"direct", "relevant"}
            or evidence_row.get("source_status") != "inspected"
            or evidence_row.get("source_safety") != "clear"
        ):
            continue
        paper = {
            "paper_id": paper_id,
            "title": candidate.get("title", paper_id),
            "role": (evidence_row.get("roles") or ["BACKGROUND"])[0],
            "source_status": "inspected",
            "safety_status": "checked_clear",
        }
        papers.append(paper)
        anchor_ids = set(evidence_row.get("inspected_anchors") or [])
        for section in source.get("sections") or []:
            anchor_id = section.get("anchor_id")
            text = section.get("text")
            if anchor_id not in anchor_ids or not isinstance(text, str) or not text.strip():
                continue
            anchor = {
                "anchor_id": anchor_id,
                "paper_id": paper_id,
                "location": f"{section.get('title', 'checked section')} ({section.get('evidence_ref', anchor_id)})",
                "permitted_use": "source_attributed_statement",
            }
            anchors.append(anchor)
            claim_id = f"source-statement-{_digest([paper_id, anchor_id])[:16]}"
            claims.append({
                "claim_id": claim_id,
                "text": text.strip(),
                "support_class": "SOURCE_ATTRIBUTED_STATEMENT",
                "allowed": True,
                "anchor_ids": [anchor_id],
                "paper_ids": [paper_id],
                "mechanism": str(section.get("title") or "checked source mechanism"),
                "source_statement": True,
            })
            used_papers.add(paper_id)
    if not claims:
        raise DocumentInputError("central campaign has no inspected topic-relevant source statements")
    omissions = [
        {"paper_id": row.get("paper_id"), "reason": row.get("reason") or "campaign open risk", "risk_id": row.get("risk_id")}
        for row in _load(root / "ledgers" / "omitted_paper_risks.json", "omitted-paper ledger").get("rows", [])
        if isinstance(row, dict) and row.get("paper_id") not in used_papers
    ]
    payload = {
        "schema_version": EVIDENCE_SCHEMA,
        "authority_class": "source_attributed",
        "bundle_id": f"central-campaign:{_digest(report.get('campaign_contract_sha256'))[:20]}",
        "topic": report["topic"],
        "papers": papers,
        "anchors": anchors,
        "claims": claims,
        "omissions": omissions,
        "nonclaims": [
            "central-paper campaign open risks remain visible",
            *(_load(root / "campaign_contract.json", "campaign contract").get("what_is_not_concluded") or []),
        ],
        "provenance": {
            "campaign_root": str(root),
            "campaign_report_sha256": _digest(report),
            "centrality_evidence_sha256": _digest(evidence),
            "validated_dispositions": report.get("dispositions", {}),
        },
        "coverage_summary": {
            "inspected_paper_count": len(papers),
            "source_statement_count": len(claims),
            "mechanism_count": len({claim["mechanism"] for claim in claims}),
            "roles": sorted({paper["role"] for paper in papers}),
            "open_risk_count": len(report.get("open_risks") or []),
        },
    }
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "document_evidence.json"
    contract_path = output_dir / "document_contract.json"
    if evidence_path.exists() or contract_path.exists():
        raise DocumentInputError("document projection output already exists")
    write_json(evidence_path, payload)
    write_json(contract_path, _contract(report["topic"]))
    return {
        "status": "central_campaign_projected",
        "authority_class": payload["authority_class"],
        "evidence_path": str(evidence_path),
        "contract_path": str(contract_path),
        "claim_count": len(claims),
        "paper_count": len(papers),
        "open_risk_count": len(report.get("open_risks") or []),
        "what_is_not_concluded": payload["nonclaims"],
    }


def project_reviewed_packet(
    *, packet_path: Path, hostile_review_path: Path, output_dir: Path
) -> dict[str, Any]:
    """Project a hostile-review-passed packet into reviewed document evidence."""
    packet_path = packet_path.expanduser().resolve()
    hostile_review_path = hostile_review_path.expanduser().resolve()
    packet = _load(packet_path, "reviewed final packet")
    if packet.get("schema_version") != "ra-survey-reviewed-final-packet-v2":
        raise DocumentInputError("reviewed packet must use the canonical V2 schema")
    if packet.get("readiness_inputs", {}).get("ready_for_hostile_review") is not True:
        raise DocumentInputError("reviewed packet is not ready for hostile review")
    hostile = _load(hostile_review_path, "hostile review result")
    if (
        hostile.get("schema_version") != "ra-survey-hostile-review-v2"
        or hostile.get("status") != "ready_for_reviewed_prose_within_recorded_scope"
        or hostile.get("ready_for_prose") is not True
        or hostile.get("blocker_count") != 0
        or hostile.get("reviewed_final_packet_sha256") != hashlib.sha256(packet_path.read_bytes()).hexdigest()
    ):
        raise DocumentInputError("hostile review does not authorize reviewed prose for this exact packet")
    claims = packet.get("reviewed_sections", {}).get("claims")
    classifications = packet.get("evidence_classifications")
    if not isinstance(claims, list) or not claims or not isinstance(classifications, list):
        raise DocumentInputError("reviewed packet has no complete supported claim set")
    class_by_hash = {row.get("decision_sha256"): row for row in classifications if isinstance(row, dict)}
    candidate_rows = (packet.get("original_packet", {}).get("candidate_ledger") or {}).get("included", [])
    title_by_id = {
        row.get("paper_id"): row.get("title", row.get("paper_id"))
        for row in candidate_rows if isinstance(row, dict)
    }
    papers: dict[str, dict[str, Any]] = {}
    anchors: list[dict[str, Any]] = []
    projected_claims: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("claim_support_allowed") is not True or claim.get("support_class") != "primary_technical_support":
            raise DocumentInputError(f"reviewed packet claim {claim.get('claim_id')} is not primary support-allowed")
        classification = class_by_hash.get(claim.get("decision_sha256"))
        if not isinstance(classification, dict):
            raise DocumentInputError(f"reviewed packet claim {claim.get('claim_id')} lacks classification")
        paper_ids = list(claim.get("paper_ids") or [])
        anchor_ids = list(claim.get("anchor_ids") or [])
        for paper_id in paper_ids:
            papers[paper_id] = {
                "paper_id": paper_id,
                "title": title_by_id.get(paper_id, paper_id),
                "role": "REVIEWED_SOURCE",
                "source_status": "available",
                "safety_status": "checked_clear",
            }
        bound = {row.get("anchor_id"): row for row in classification.get("bound_anchors") or []}
        for anchor_id in anchor_ids:
            row = bound.get(anchor_id)
            if not isinstance(row, dict):
                raise DocumentInputError(f"reviewed packet claim {claim.get('claim_id')} lacks bound anchor {anchor_id}")
            anchors.append({
                "anchor_id": anchor_id,
                "paper_id": row.get("paper_id"),
                "location": anchor_id,
                "permitted_use": "technical_claim_support",
            })
        projected_claims.append({
            "claim_id": claim["claim_id"],
            "text": claim["claim_text"],
            "support_class": "PRIMARY_TECHNICAL_SUPPORT",
            "allowed": True,
            "anchor_ids": anchor_ids,
            "paper_ids": paper_ids,
            "mechanism": claim.get("claim_type", "reviewed technical claim"),
        })
    topic = str((packet.get("review_queue") or {}).get("topic") or "reviewed scholarly topic")
    payload = {
        "schema_version": EVIDENCE_SCHEMA,
        "authority_class": "reviewed_primary",
        "bundle_id": f"reviewed-packet:{packet.get('mission_id')}",
        "topic": topic,
        "papers": list(papers.values()),
        "anchors": anchors,
        "claims": projected_claims,
        "omissions": packet.get("reviewed_sections", {}).get("omission_risks") or [],
        "nonclaims": packet.get("what_is_not_concluded") or [],
        "provenance": {
            "reviewed_final_packet": str(packet_path),
            "hostile_review_result": str(hostile_review_path),
        },
    }
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "document_evidence.json"
    contract_path = output_dir / "document_contract.json"
    if evidence_path.exists() or contract_path.exists():
        raise DocumentInputError("document projection output already exists")
    write_json(evidence_path, payload)
    write_json(contract_path, _contract(topic) | {
        "purpose": "Produce a reviewed, source-bound survey candidate within the recorded scope.",
        "claim_boundary": "Only hostile-review-ready primary technical claims may enter body prose.",
    })
    return {
        "status": "reviewed_packet_projected",
        "authority_class": payload["authority_class"],
        "evidence_path": str(evidence_path),
        "contract_path": str(contract_path),
        "claim_count": len(projected_claims),
        "paper_count": len(papers),
        "what_is_not_concluded": payload["nonclaims"],
    }
