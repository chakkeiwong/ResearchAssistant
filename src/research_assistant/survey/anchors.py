from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.source.structured_source import source_record_path
from research_assistant.storage.file_store import FileStore


SURVEY_ANCHOR_EXTRACTION_RESULT_SCHEMA_VERSION = "ra-survey-anchor-extraction-result-v1"
SURVEY_ANCHOR_INVENTORY_SCHEMA_VERSION = "ra-survey-source-anchor-inventory-v1"
SURVEY_ANCHOR_SOURCE_SUPPORT_SCHEMA_VERSION = "ra-survey-anchor-source-support-v1"
SURVEY_ANCHOR_CLAIM_SUPPORT_SCHEMA_VERSION = "ra-survey-anchor-claim-support-v1"
SURVEY_ANCHOR_QUARANTINE_SCHEMA_VERSION = "ra-survey-anchor-quarantine-register-v1"
SURVEY_ANCHOR_MANIFEST_SCHEMA_VERSION = "ra-survey-anchor-manifest-v1"

ANCHOR_OUTPUT_FILES = (
    "source_anchor_inventory.json",
    "source_support.json",
    "claim_support.json",
    "quarantine_register.json",
    "anchor_extraction_manifest.json",
)

TECHNICAL_CLAIM_FORBIDDEN = (
    "theorem, algorithm, method, empirical, historical priority, or literature-completeness claims "
    "until a claim row is explicitly mapped to checked source anchors and reviewed"
)


def build_source_anchor_packet(
    *,
    paper_ids: list[str],
    output_dir: Path,
    topic: str | None = None,
    force: bool = False,
    max_anchors_per_paper: int = 24,
    root: Path | None = None,
) -> dict[str, Any]:
    normalized_ids = [paper_id.strip() for paper_id in paper_ids if paper_id.strip()]
    if not normalized_ids:
        return _blocked(
            "empty_paper_ids",
            "survey anchors requires at least one --paper-id",
            output_dir,
            next_required_actions=["provide one or more Phase 4 source-record paper ids"],
        )
    if max_anchors_per_paper <= 0:
        return _blocked(
            "invalid_max_anchors_per_paper",
            "max anchors per paper must be positive",
            output_dir,
            next_required_actions=["rerun with --max-anchors-per-paper greater than zero"],
        )

    output_dir = output_dir.resolve()
    existing = [output_dir / name for name in ANCHOR_OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not force:
        return {
            "schema_version": SURVEY_ANCHOR_EXTRACTION_RESULT_SCHEMA_VERSION,
            "status": "blocked",
            "blocked_reason": "output_exists",
            "message": "output directory already contains survey anchor artifacts",
            "output_dir": str(output_dir),
            "existing_artifacts": [str(path) for path in existing],
            "next_required_actions": ["rerun with --force or choose a new --out directory"],
            "what_is_not_concluded": _not_concluded(),
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = get_paths(root)
    source_rows: list[dict[str, Any]] = []
    anchor_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    source_gap_rows: list[dict[str, Any]] = []

    for paper_id in normalized_ids:
        source_path = source_record_path(paths.papers_source, paper_id)
        if not source_path.exists():
            gap = {
                "paper_id": paper_id,
                "source_record_path": str(source_path),
                "source_status": "source_gap",
                "reason": "structured source record missing",
                "claim_support_allowed": False,
            }
            source_rows.append(_source_gap_support_row(gap))
            quarantine_rows.append(_quarantine_row(gap, status="source_gap"))
            source_gap_rows.append(gap)
            continue

        record = FileStore(paths.local_research).read_json(source_path)
        if record.get("status") != "available":
            gap = {
                "paper_id": paper_id,
                "source_record_path": str(source_path),
                "source_status": record.get("status") or "source_gap",
                "reason": "structured source record is not available",
                "claim_support_allowed": False,
            }
            source_rows.append(_source_gap_support_row(gap))
            quarantine_rows.append(_quarantine_row(gap, status="source_gap"))
            source_gap_rows.append(gap)
            continue

        paper_anchors = _extract_anchor_rows(
            paper_id=paper_id,
            source_path=source_path,
            record=record,
            max_anchors=max_anchors_per_paper,
        )
        anchor_rows.extend(paper_anchors)
        source_rows.append(_source_support_row(paper_id, source_path, record, paper_anchors))
        quarantine_rows.append(_quarantine_row_for_record(paper_id, source_path, record, paper_anchors))

    anchor_inventory = {
        "schema_version": SURVEY_ANCHOR_INVENTORY_SCHEMA_VERSION,
        "status": "anchors_extracted" if anchor_rows else "no_checked_anchors",
        "topic": topic,
        "paper_ids": normalized_ids,
        "anchor_count": len(anchor_rows),
        "anchors": anchor_rows,
        "raw_text_policy": {
            "raw_latex_included": False,
            "raw_full_text_included": False,
            "anchor_hashes_included": True,
            "reason": "Phase 5 writes review pointers and hashes; raw source remains in local_research source records.",
        },
        "not_concluded": _not_concluded(),
    }
    source_support = {
        "schema_version": SURVEY_ANCHOR_SOURCE_SUPPORT_SCHEMA_VERSION,
        "status": "source_anchors_available" if anchor_rows else "source_gaps_or_no_anchors",
        "topic": topic,
        "papers": source_rows,
        "source_gap_rows": source_gap_rows,
        "not_concluded": _not_concluded(),
    }
    claim_support = {
        "schema_version": SURVEY_ANCHOR_CLAIM_SUPPORT_SCHEMA_VERSION,
        "status": "anchors_extracted_no_supported_technical_claims",
        "topic": topic,
        "claims": [],
        "blocked_claims": [
            {
                "claim_id": "phase5_no_unmapped_technical_claims",
                "status": "blocked",
                "support_class": "source_gap_pending_claim_mapping",
                "reason": TECHNICAL_CLAIM_FORBIDDEN,
                "available_anchor_count": len(anchor_rows),
                "paper_ids": normalized_ids,
            }
        ],
        "claim_support_policy": {
            "technical_claims_require_checked_anchors": True,
            "metadata_only_support_allowed_for_technical_claims": False,
            "source_availability_support_allowed_for_technical_claims": False,
            "titles_abstracts_and_provider_snippets_do_not_support_technical_claims": True,
            "raw_anchor_text_must_be_retrieved_from_local_source_record_for_review": True,
        },
        "not_concluded": _not_concluded(),
    }
    quarantine_register = {
        "schema_version": SURVEY_ANCHOR_QUARANTINE_SCHEMA_VERSION,
        "status": "no_retraction_check_phase5_anchor_extraction_only",
        "topic": topic,
        "rows": quarantine_rows,
        "source_gap_rows": source_gap_rows,
        "not_concluded": _not_concluded(),
    }
    manifest = {
        "schema_version": SURVEY_ANCHOR_MANIFEST_SCHEMA_VERSION,
        "status": "created",
        "created_at": _utc_now_iso(),
        "topic": topic,
        "paper_ids": normalized_ids,
        "output_dir": str(output_dir),
        "artifact_paths": {
            "source_anchor_inventory": str(output_dir / "source_anchor_inventory.json"),
            "source_support": str(output_dir / "source_support.json"),
            "claim_support": str(output_dir / "claim_support.json"),
            "quarantine_register": str(output_dir / "quarantine_register.json"),
            "anchor_extraction_manifest": str(output_dir / "anchor_extraction_manifest.json"),
        },
        "anchor_count": len(anchor_rows),
        "source_gap_count": len(source_gap_rows),
        "ready_for_phase6": bool(anchor_rows),
        "ready_for_prose": False,
        "next_required_actions": [
            "compose Phase 6 evidence packet with source gaps and unchecked-claim blockers visible",
            "map any proposed technical claim to one or more anchor ids before prose drafting",
            "run retraction/version checks before using anchors as primary technical support",
        ],
        "not_concluded": _not_concluded(),
    }

    outputs = {
        "source_anchor_inventory.json": anchor_inventory,
        "source_support.json": source_support,
        "claim_support.json": claim_support,
        "quarantine_register.json": quarantine_register,
        "anchor_extraction_manifest.json": manifest,
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))

    return {
        "schema_version": SURVEY_ANCHOR_EXTRACTION_RESULT_SCHEMA_VERSION,
        "status": "anchors_extracted" if anchor_rows else "source_gaps_or_no_anchors",
        "topic": topic,
        "paper_count": len(normalized_ids),
        "anchor_count": len(anchor_rows),
        "source_gap_count": len(source_gap_rows),
        "output_dir": str(output_dir),
        "artifact_paths": manifest["artifact_paths"],
        "ready_for_phase6": bool(anchor_rows),
        "ready_for_prose": False,
        "next_required_actions": manifest["next_required_actions"],
        "what_is_not_concluded": _not_concluded(),
    }


def _extract_anchor_rows(
    *,
    paper_id: str,
    source_path: Path,
    record: dict[str, Any],
    max_anchors: int,
) -> list[dict[str, Any]]:
    sections = _candidate_sections(record)
    equations = _candidate_labeled_blocks(record, "equations", "equation")
    theorems = _candidate_labeled_blocks(record, "theorem_like_blocks", "theorem_like_block")
    combined = sections + equations + theorems
    combined.sort(key=lambda row: (row["priority"], row["line"] if row["line"] is not None else 10**9, row["anchor_id"]))
    rows = []
    for row in combined[:max_anchors]:
        row.pop("priority", None)
        row["paper_id"] = paper_id
        row["source_record_path"] = str(source_path)
        rows.append(row)
    return rows


def _candidate_sections(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for section in record.get("sections") or []:
        title = str(section.get("title") or "")
        labels = [str(label) for label in section.get("labels") or []]
        if not labels and not _important_section_title(title):
            continue
        line = _int_or_none(section.get("line"))
        raw = str(section.get("raw_latex") or "")
        rows.append({
            "anchor_id": _anchor_id("section", labels, line, title),
            "anchor_type": "section",
            "labels": labels,
            "line": line,
            "title": title,
            "role": _section_role(title),
            "raw_latex_sha256": _sha256(raw),
            "raw_latex_bytes": len(raw.encode("utf-8")),
            "raw_latex_included": False,
            "review_status": "machine_extracted_requires_human_or_model_review",
            "claim_support_status": "anchor_available_claim_not_mapped",
            "priority": _section_priority(title, labels),
        })
    return rows


def _candidate_labeled_blocks(record: dict[str, Any], key: str, anchor_type: str) -> list[dict[str, Any]]:
    rows = []
    for block in record.get(key) or []:
        labels = [str(label) for label in block.get("labels") or []]
        if not labels:
            continue
        line = _int_or_none(block.get("line"))
        raw = str(block.get("raw_latex") or "")
        section = _containing_section(record, line)
        rows.append({
            "anchor_id": _anchor_id(anchor_type, labels, line, str(block.get("environment") or anchor_type)),
            "anchor_type": anchor_type,
            "labels": labels,
            "line": line,
            "environment": block.get("environment"),
            "containing_section": _section_pointer(section),
            "role": _block_role(anchor_type, section),
            "raw_latex_sha256": _sha256(raw),
            "raw_latex_bytes": len(raw.encode("utf-8")),
            "raw_latex_included": False,
            "review_status": "machine_extracted_requires_human_or_model_review",
            "claim_support_status": "anchor_available_claim_not_mapped",
            "priority": 10 if anchor_type == "theorem_like_block" else 20,
        })
    return rows


def _source_support_row(
    paper_id: str,
    source_path: Path,
    record: dict[str, Any],
    anchors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "paper_id": paper_id,
        "arxiv_id": (record.get("provenance") or {}).get("arxiv_id"),
        "source_status": record.get("status"),
        "source_type": record.get("source_type"),
        "primary_for_audit": record.get("primary_for_audit"),
        "source_record_path": str(source_path),
        "section_count": len(record.get("sections") or []),
        "equation_count": len(record.get("equations") or []),
        "theorem_like_block_count": len(record.get("theorem_like_blocks") or []),
        "citation_count": len(record.get("citations") or []),
        "bibliography_count": len(record.get("bibliography") or []),
        "checked_anchors": [anchor["anchor_id"] for anchor in anchors],
        "checked_anchor_count": len(anchors),
        "technical_claim_support": "not_supported_until_claim_mapping_review",
        "allowed_claims": [
            "local structured source record exists",
            "listed anchor ids identify parser-extracted source blocks by label/line/hash",
        ],
        "forbidden_claims": [TECHNICAL_CLAIM_FORBIDDEN],
        "limitations": record.get("limitations") or [],
    }


def _source_gap_support_row(gap: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": gap["paper_id"],
        "source_status": gap["source_status"],
        "source_record_path": gap["source_record_path"],
        "checked_anchors": [],
        "checked_anchor_count": 0,
        "technical_claim_support": "source_gap",
        "allowed_claims": [],
        "forbidden_claims": [TECHNICAL_CLAIM_FORBIDDEN],
        "limitations": [{"field": "source", "status": "source_gap", "note": gap["reason"]}],
    }


def _quarantine_row_for_record(
    paper_id: str,
    source_path: Path,
    record: dict[str, Any],
    anchors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "paper_id": paper_id,
        "source_record_path": str(source_path),
        "source_status": record.get("status"),
        "quarantine_status": "not_quarantined_by_phase5",
        "retraction_or_version_status": "not_checked_phase5",
        "claim_support_allowed": False,
        "anchor_count": len(anchors),
        "limitations": record.get("limitations") or [],
        "next_action": "run retraction/version checks and claim-anchor review before using as technical support",
    }


def _quarantine_row(gap: dict[str, Any], *, status: str) -> dict[str, Any]:
    return {
        "paper_id": gap["paper_id"],
        "source_record_path": gap["source_record_path"],
        "source_status": gap["source_status"],
        "quarantine_status": status,
        "retraction_or_version_status": "not_checked_phase5",
        "claim_support_allowed": False,
        "anchor_count": 0,
        "limitations": [{"field": "source", "status": "source_gap", "note": gap["reason"]}],
        "next_action": "represent as source gap unless a new approved intake or source repair succeeds",
    }


def _containing_section(record: dict[str, Any], line: int | None) -> dict[str, Any] | None:
    if line is None:
        return None
    containing = None
    for section in sorted(record.get("sections") or [], key=lambda row: row.get("line") or 0):
        if (section.get("line") or 0) <= line:
            containing = section
        else:
            break
    return containing


def _section_pointer(section: dict[str, Any] | None) -> dict[str, Any] | None:
    if section is None:
        return None
    return {
        "title": section.get("title"),
        "labels": section.get("labels") or [],
        "line": section.get("line"),
    }


def _section_role(title: str) -> str:
    lowered = title.lower()
    if "related" in lowered:
        return "backward_snowball_anchor_candidate"
    if "prelim" in lowered or "background" in lowered:
        return "background_definition_anchor_candidate"
    if any(token in lowered for token in ("method", "algorithm", "optimization", "derivation", "comput")):
        return "method_anchor_candidate"
    if any(token in lowered for token in ("theory", "proof", "universal", "approx")):
        return "theory_anchor_candidate"
    if any(token in lowered for token in ("experiment", "evaluation", "result")):
        return "empirical_anchor_candidate"
    if "introduction" in lowered:
        return "scope_anchor_candidate"
    return "source_section_anchor_candidate"


def _block_role(anchor_type: str, section: dict[str, Any] | None) -> str:
    if anchor_type == "theorem_like_block":
        return "theorem_like_anchor_candidate"
    if section is None:
        return "equation_anchor_candidate"
    return _section_role(str(section.get("title") or "")).replace("_section_", "_equation_")


def _important_section_title(title: str) -> bool:
    lowered = title.lower()
    return any(
        token in lowered
        for token in (
            "introduction",
            "related",
            "prelim",
            "background",
            "method",
            "algorithm",
            "optimization",
            "derivation",
            "theory",
            "experiment",
            "evaluation",
            "result",
            "approx",
            "conclusion",
        )
    )


def _section_priority(title: str, labels: list[str]) -> int:
    role = _section_role(title)
    priority_by_role = {
        "method_anchor_candidate": 0,
        "theory_anchor_candidate": 1,
        "empirical_anchor_candidate": 2,
        "backward_snowball_anchor_candidate": 3,
        "background_definition_anchor_candidate": 4,
        "scope_anchor_candidate": 5,
    }
    return priority_by_role.get(role, 6) + (0 if labels else 3)


def _anchor_id(anchor_type: str, labels: list[str], line: int | None, fallback: str) -> str:
    if labels:
        suffix = labels[0]
    elif line is not None:
        suffix = f"line-{line}"
    else:
        suffix = _safe_token(fallback)
    return f"{anchor_type}:{suffix}"


def _safe_token(value: str) -> str:
    token = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in token.split("-") if part) or "unknown"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _blocked(reason: str, message: str, output_dir: Path, *, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_ANCHOR_EXTRACTION_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "message": message,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": _not_concluded(),
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _not_concluded() -> list[str]:
    return [
        "technical claim support",
        "mathematical correctness",
        "complete paper understanding",
        "retraction/version safety",
        "literature completeness",
        "survey prose readiness",
        "product readiness",
    ]
