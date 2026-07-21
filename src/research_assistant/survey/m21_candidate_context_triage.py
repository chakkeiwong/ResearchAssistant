from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ra-literature-survey-m21-candidate-context-v1"
EXPECTED_SEED = "2201.12220v3"
EXPECTED_PAPER_ID = "paper_arxiv_2201_1a5af737"
EXPECTED_SOURCE_SHA256 = (
    "2eb686b1f5dd9b2fa95ed5185cfe5da4d8e93a2b7d8a294902962e9dac66bd0f"
)
EXPECTED_CANDIDATE_COUNT = 62
EXPECTED_IDENTIFIER_FREE_UNITS = 195
DEFAULT_MAX_NOMINATIONS = 12

DIRECT = "SEED_CONTEXT_DIRECT_OR_COMPETING_SIGNAL"
THEORY = "SEED_CONTEXT_THEORY_OR_BACKGROUND_SIGNAL"
EMPIRICAL = "SEED_CONTEXT_EMPIRICAL_OR_IMPLEMENTATION_SIGNAL"
SURVEY = "SEED_CONTEXT_SURVEY_SIGNAL"
OTHER = "SEED_CONTEXT_OTHER_SIGNAL"
AMBIGUOUS = "CITED_CONTEXT_AMBIGUOUS"
NOT_LOCATED = "BIBLIOGRAPHY_ENTRY_NOT_LOCATED_IN_SEED_TEXT"

STATE_ORDER = (DIRECT, THEORY, EMPIRICAL, SURVEY, AMBIGUOUS, OTHER, NOT_LOCATED)
ROLE_PATTERNS = {
    SURVEY: ("survey", "overview", "we refer", "tutorial"),
    EMPIRICAL: (
        "experiment",
        "evaluation",
        "benchmark",
        "performance",
        "application",
        "fid",
        "translation",
    ),
    DIRECT: (
        "method",
        "approach",
        "algorithm",
        "compute",
        "recover",
        "procedure",
        "extension",
        "limitation",
        "prior work",
        "best performing",
    ),
    THEORY: (
        "theorem",
        "lemma",
        "duality",
        "existence",
        "convex",
        "approximation",
        "formulation",
        "wasserstein",
        "optimal transport",
    ),
}


class M21CandidateContextError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _load_object(path: Path, code: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise M21CandidateContextError(code)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M21CandidateContextError(code) from exc
    if not isinstance(value, dict):
        raise M21CandidateContextError(code)
    return value


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def _atomic_json(path: Path, value: Any) -> None:
    raw = _pretty(value)
    descriptor, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_inputs(
    candidate_path: Path,
    evidence_path: Path,
    record_path: Path,
    retained_source_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], str, dict[str, str]]:
    candidates = _load_object(candidate_path, "candidate_input_invalid")
    evidence = _load_object(evidence_path, "evidence_input_invalid")
    record = _load_object(record_path, "structured_record_invalid")
    rows = candidates.get("rows")
    backward = evidence.get("backward")
    if (
        candidates.get("candidate_count") != EXPECTED_CANDIDATE_COUNT
        or not isinstance(rows, list)
        or len(rows) != EXPECTED_CANDIDATE_COUNT
        or not isinstance(backward, dict)
        or backward.get("candidate_count") != EXPECTED_CANDIDATE_COUNT
        or backward.get("identifier_free_units") != EXPECTED_IDENTIFIER_FREE_UNITS
        or evidence.get("arxiv_seed") != f"arxiv:{EXPECTED_SEED}"
    ):
        raise M21CandidateContextError("m20_input_contract_invalid")
    ids: set[str] = set()
    keys: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise M21CandidateContextError("candidate_row_invalid")
        candidate_id = row.get("candidate_id")
        key = row.get("bibliography_key")
        if (
            not isinstance(candidate_id, str)
            or not candidate_id
            or candidate_id in ids
            or not isinstance(key, str)
            or not key
            or key in keys
            or row.get("scholarly_classification") != "NOT_CHECKED"
            or row.get("support_status") != "SOURCE_GAP_BLOCKER"
            or row.get("action") != "inspect_primary_source"
        ):
            raise M21CandidateContextError("candidate_row_invalid")
        ids.add(candidate_id)
        keys.add(key)
    if (
        record.get("paper_id") != EXPECTED_PAPER_ID
        or record.get("source_type") != "arxiv_latex"
        or record.get("status") != "available"
        or record.get("primary_for_audit") is not True
        or (record.get("provenance") or {}).get("arxiv_id") != EXPECTED_SEED
    ):
        raise M21CandidateContextError("structured_record_identity_invalid")
    original_path = Path(str(record.get("original_source_path")))
    flattened_path = Path(str(record.get("flattened_source_path")))
    if (
        retained_source_path.is_symlink()
        or not retained_source_path.is_file()
        or original_path.is_symlink()
        or not original_path.is_file()
        or flattened_path.is_symlink()
        or not flattened_path.is_file()
    ):
        raise M21CandidateContextError("source_artifact_invalid")
    source_hashes = {
        "retained_source_sha256": _sha_file(retained_source_path),
        "record_original_source_sha256": _sha_file(original_path),
    }
    if set(source_hashes.values()) != {EXPECTED_SOURCE_SHA256}:
        raise M21CandidateContextError("source_hash_mismatch")
    if retained_source_path.stat().st_size != original_path.stat().st_size:
        raise M21CandidateContextError("source_size_mismatch")
    return rows, record, flattened_path.read_text(encoding="utf-8", errors="replace"), {
        "candidate_classifications_sha256": _sha_file(candidate_path),
        "combined_evidence_sha256": _sha_file(evidence_path),
        "structured_record_sha256": _sha_file(record_path),
        "flattened_source_sha256": _sha_file(flattened_path),
        **source_hashes,
    }


def _section_for_line(sections: list[dict[str, Any]], line: int) -> dict[str, Any] | None:
    selected = None
    for section in sorted(sections, key=lambda row: row.get("line") or 0):
        if isinstance(section.get("line"), int) and section["line"] <= line:
            selected = section
        else:
            break
    return selected


def _context_signals(
    *, line: int, section: dict[str, Any] | None, source_lines: list[str]
) -> tuple[list[str], list[str]]:
    start = max(0, line - 2)
    end = min(len(source_lines), line + 1)
    context = " ".join(source_lines[start:end]).casefold()
    section_title = str((section or {}).get("title") or "").casefold()
    searchable = f"{section_title} {context}"
    signals: list[str] = []
    matched: list[str] = []
    for state in (SURVEY, EMPIRICAL, DIRECT, THEORY):
        tokens = [token for token in ROLE_PATTERNS[state] if token in searchable]
        if tokens:
            signals.append(state)
            matched.extend(tokens)
    if not signals:
        if "related" in section_title:
            signals.append(DIRECT)
            matched.append("section:related")
        elif any(token in section_title for token in ("prelim", "theory", "approx")):
            signals.append(THEORY)
            matched.append("section:theory_or_background")
        elif any(token in section_title for token in ("experiment", "evaluation", "result")):
            signals.append(EMPIRICAL)
            matched.append("section:empirical")
        else:
            signals.append(OTHER)
    return sorted(set(signals), key=STATE_ORDER.index), sorted(set(matched))


def _candidate_state(locations: list[dict[str, Any]]) -> str:
    if not locations:
        return NOT_LOCATED
    states = {
        state
        for location in locations
        for state in location["context_role_signals"]
        if state != OTHER
    }
    if len(states) > 1:
        return AMBIGUOUS
    if len(states) == 1:
        return next(iter(states))
    return OTHER


def _triage_rows(
    candidates: list[dict[str, Any]], record: dict[str, Any], flattened_text: str
) -> list[dict[str, Any]]:
    source_lines = flattened_text.splitlines()
    sections = record.get("sections") or []
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for citation in record.get("citations") or []:
        line = citation.get("line")
        keys = citation.get("keys")
        if type(line) is not int or line <= 0 or not isinstance(keys, list):
            raise M21CandidateContextError("structured_citation_invalid")
        section = _section_for_line(sections, line)
        signals, matched = _context_signals(
            line=line, section=section, source_lines=source_lines
        )
        location = {
            "line": line,
            "citation_command": citation.get("command"),
            "section_title": (section or {}).get("title"),
            "section_labels": (section or {}).get("labels") or [],
            "context_role_signals": signals,
            "matched_signal_tokens": matched,
        }
        for key in keys:
            if isinstance(key, str) and key:
                by_key[key].append(location)

    rows = []
    for candidate in sorted(candidates, key=lambda row: row["candidate_id"]):
        locations = sorted(
            by_key.get(candidate["bibliography_key"], []),
            key=lambda row: (
                row["line"],
                str(row["citation_command"]),
                str(row["section_title"]),
            ),
        )
        rows.append({
            "candidate_id": candidate["candidate_id"],
            "identifiers": candidate.get("identifiers") or [],
            "title": candidate.get("title"),
            "bibliography_key": candidate["bibliography_key"],
            "source_member": candidate.get("source_member"),
            "citation_occurrence_count": len(locations),
            "citation_locations": locations,
            "heuristic_context_state": _candidate_state(locations),
            "scholarly_classification": "NOT_CHECKED",
            "support_status": "SOURCE_GAP_BLOCKER",
            "next_action": "inspect_primary_source_if_nominated_else_retain_omission_risk",
            "heuristic_only": True,
        })
    return rows


def _selection(rows: list[dict[str, Any]], max_nominations: int) -> dict[str, Any]:
    if not 0 < max_nominations <= DEFAULT_MAX_NOMINATIONS:
        raise M21CandidateContextError("nomination_cap_invalid")
    eligible_states = tuple(state for state in STATE_ORDER if state != NOT_LOCATED)
    grouped = {
        state: sorted(
            (row for row in rows if row["heuristic_context_state"] == state),
            key=lambda row: (-row["citation_occurrence_count"], row["candidate_id"]),
        )
        for state in eligible_states
    }
    selected: dict[str, list[str]] = {}
    for state in eligible_states:
        if grouped[state] and len(selected) < max_nominations:
            selected[grouped[state][0]["candidate_id"]] = [
                f"represent_seed_context_stratum:{state}"
            ]
    repeated = sorted(
        (row for row in rows if row["citation_occurrence_count"] > 1),
        key=lambda row: (-row["citation_occurrence_count"], row["candidate_id"]),
    )
    if repeated and len(selected) < max_nominations:
        row = next(
            (candidate for candidate in repeated if candidate["candidate_id"] not in selected),
            None,
        )
        if row is not None:
            selected[row["candidate_id"]] = ["repeated_seed_context_diagnostic"]

    queues = {
        state: [row for row in grouped[state] if row["candidate_id"] not in selected]
        for state in eligible_states
    }
    while len(selected) < max_nominations and any(queues.values()):
        for state in eligible_states:
            if queues[state] and len(selected) < max_nominations:
                row = queues[state].pop(0)
                selected[row["candidate_id"]] = [
                    f"stable_round_robin_within_stratum:{state}"
                ]

    selection_rows = []
    for row in rows:
        reasons = selected.get(row["candidate_id"])
        selection_rows.append({
            "candidate_id": row["candidate_id"],
            "heuristic_context_state": row["heuristic_context_state"],
            "citation_occurrence_count": row["citation_occurrence_count"],
            "nomination_status": "NOMINATED_FOR_PRIMARY_SOURCE_INSPECTION"
            if reasons
            else "DEFERRED_RETAINED_AS_OMISSION_RISK",
            "reasons": reasons
            or [
                "bibliography_entry_not_located_in_seed_text_not_a_relevance_rejection"
                if row["heuristic_context_state"] == NOT_LOCATED
                else "bounded_stratified_queue_cap_reached_not_a_relevance_rejection"
            ],
            "scholarly_classification": "NOT_CHECKED",
            "support_status": "SOURCE_GAP_BLOCKER",
        })
    nominated = [row for row in selection_rows if row["nomination_status"].startswith("NOMINATED")]
    return {
        "schema_version": f"{SCHEMA_VERSION}-primary-source-selection",
        "status": "bounded_heuristic_inspection_queue",
        "maximum_nominations": max_nominations,
        "nomination_count": len(nominated),
        "nominated_candidate_ids": [row["candidate_id"] for row in nominated],
        "selection_rows": selection_rows,
        "selection_method": "only source-located candidates are eligible; one representative per observed cited-context state, one additional repeated-context diagnostic when available, then stable round-robin across cited-context states",
        "nonclaims": [
            "candidate_relevance",
            "candidate_importance",
            "scholarly_classification",
            "primary_source_support",
            "literature_completeness",
        ],
    }


def build_candidate_context_triage(
    *,
    candidate_path: Path,
    evidence_path: Path,
    structured_record_path: Path,
    retained_source_path: Path,
    max_nominations: int = DEFAULT_MAX_NOMINATIONS,
) -> dict[str, dict[str, Any]]:
    candidates, record, flattened_text, hashes = _validate_inputs(
        candidate_path, evidence_path, structured_record_path, retained_source_path
    )
    rows = _triage_rows(candidates, record, flattened_text)
    state_counts = Counter(row["heuristic_context_state"] for row in rows)
    triage = {
        "schema_version": f"{SCHEMA_VERSION}-triage",
        "status": "complete_heuristic_seed_context_accounting",
        "seed": f"arxiv:{EXPECTED_SEED}",
        "candidate_count": len(rows),
        "state_counts": {state: state_counts.get(state, 0) for state in STATE_ORDER},
        "rows": rows,
        "input_hashes": hashes,
        "raw_source_included": False,
        "nonclaims": [
            "scholarly_classification",
            "candidate_relevance",
            "technical_claim_support",
            "citation_importance",
            "literature_completeness",
            "scientific_correctness",
        ],
    }
    identifier_free = {
        "schema_version": f"{SCHEMA_VERSION}-identifier-free-risk",
        "status": "open_omission_risk",
        "identifier_free_bibliography_units": EXPECTED_IDENTIFIER_FREE_UNITS,
        "forward_coverage_status": "unavailable_out_of_scope",
        "forward_coverage_blocking": False,
        "reason": "identifier-only M20 extraction cannot classify bibliography units without an admitted DOI/arXiv identifier",
        "recovery_actions": [
            "parse titles/authors/years for identifier-free units",
            "inspect seed related-work and comparison sections",
            "retain unresolved rows in the omission register",
        ],
        "nonclaims": ["irrelevance", "completeness", "zero_forward_citations"],
    }
    return {
        "candidate_context_triage.json": triage,
        "identifier_free_risk.json": identifier_free,
        "primary_source_selection.json": _selection(rows, max_nominations),
    }


def write_candidate_context_triage(
    *,
    candidate_path: Path,
    evidence_path: Path,
    structured_record_path: Path,
    retained_source_path: Path,
    output_root: Path,
    max_nominations: int = DEFAULT_MAX_NOMINATIONS,
) -> dict[str, Any]:
    output_root = output_root.resolve(strict=False)
    if output_root.exists() or not output_root.parent.is_dir():
        raise M21CandidateContextError("output_root_not_fresh")
    outputs = build_candidate_context_triage(
        candidate_path=candidate_path.resolve(strict=True),
        evidence_path=evidence_path.resolve(strict=True),
        structured_record_path=structured_record_path.resolve(strict=True),
        retained_source_path=retained_source_path.resolve(strict=True),
        max_nominations=max_nominations,
    )
    output_root.mkdir(mode=0o700)
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-manifest",
        "status": "closed",
        "network_used": False,
        "credential_interface": False,
        "seed": f"arxiv:{EXPECTED_SEED}",
        "candidate_count": EXPECTED_CANDIDATE_COUNT,
        "identifier_free_bibliography_units": EXPECTED_IDENTIFIER_FREE_UNITS,
        "max_nominations": max_nominations,
        "input_hashes": outputs["candidate_context_triage.json"]["input_hashes"],
        "nonclaims": outputs["candidate_context_triage.json"]["nonclaims"],
    }
    for name, value in {**outputs, "run_manifest.json": manifest}.items():
        _atomic_json(output_root / name, value)
    inventory_rows = []
    for path in sorted(output_root.glob("*.json")):
        inventory_rows.append({
            "relative_path": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": _sha_file(path),
        })
    _atomic_json(
        output_root / "artifact_inventory.json",
        {
            "schema_version": f"{SCHEMA_VERSION}-inventory",
            "inventory_excludes_itself": True,
            "files": inventory_rows,
        },
    )
    return {
        "status": "passed",
        "candidate_count": EXPECTED_CANDIDATE_COUNT,
        "nomination_count": outputs["primary_source_selection.json"]["nomination_count"],
        "state_counts": outputs["candidate_context_triage.json"]["state_counts"],
        "output_root": str(output_root),
    }


__all__ = [
    "M21CandidateContextError",
    "build_candidate_context_triage",
    "write_candidate_context_triage",
]
