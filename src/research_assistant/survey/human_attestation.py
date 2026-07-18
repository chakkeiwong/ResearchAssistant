from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from research_assistant.survey.artifact_lineage import (
    assert_public_write_path_allowed,
    validate_selected_review_queue,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
)
from research_assistant.survey.review_decisions import (
    REVIEW_DECISIONS_SCHEMA,
    SUPPORTED_DECISION_TYPES,
    normalize_required_text,
    normalize_reviewed_at,
    read_json_object_strict,
    require_exact_keys,
    utc_now_iso,
)


HUMAN_REVIEW_PACKET_SCHEMA = "ra-survey-human-review-packet-v1"
HUMAN_ATTESTATION_SCHEMA = "ra-survey-human-self-attestation-v1"
HUMAN_ATTESTATION_RECEIPT_SCHEMA = "ra-survey-human-attestation-receipt-v1"
HUMAN_RECEIPT_ARCHIVE_SCHEMA = "ra-survey-human-receipt-archive-v1"
CLAIM_V3_SCHEMA = "ra-survey-claim-review-v3"
SOURCE_V3_SCHEMA = "ra-survey-source-safety-review-v3"
CLAIM_V4_SCHEMA = "ra-survey-claim-review-v4"
SOURCE_V4_SCHEMA = "ra-survey-source-safety-review-v4"
OMISSION_V3_SCHEMA = "ra-survey-omission-review-v3"
DECISION_TYPES = (
    "claim_candidate",
    "source_safety",
    "omission_risk",
    "workflow_blocker",
)
DECISION_SCHEMAS = {
    "claim_candidate": {REVIEW_DECISIONS_SCHEMA, CLAIM_V3_SCHEMA, CLAIM_V4_SCHEMA},
    "source_safety": {REVIEW_DECISIONS_SCHEMA, SOURCE_V3_SCHEMA, SOURCE_V4_SCHEMA},
    "omission_risk": {REVIEW_DECISIONS_SCHEMA, OMISSION_V3_SCHEMA},
    "workflow_blocker": {REVIEW_DECISIONS_SCHEMA},
}
REVIEW_ROLES = (
    "claim_review",
    "source_safety_review",
    "omission_review",
    "workflow_blocker_review",
)
ROLE_BY_DECISION_TYPE = dict(zip(DECISION_TYPES, REVIEW_ROLES, strict=True))
SUSPICIOUS_AUTHORITY = re.compile(
    r"(?:^|[^a-z])(claude|codex|chatgpt|gpt|language model|fixture|automation|automated reviewer)(?:$|[^a-z])",
    re.IGNORECASE,
)
OPAQUE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")

PACKET_KEYS = {
    "schema_version",
    "status",
    "created_at",
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
    "queue_semantic_sha256",
    "review_queue_path",
    "review_queue_sha256",
    "topic",
    "queue_counts",
    "required_decision_types",
    "required_roles",
    "items_by_type",
    "operator_contract",
    "what_is_not_concluded",
}
ATTESTATION_KEYS = {
    "schema_version",
    "status",
    "packet_sha256",
    "review_queue_sha256",
    "reviewer",
    "attested_at",
    "declarations",
}
REVIEWER_KEYS = {
    "opaque_reviewer_id",
    "display_name",
    "authority_origin",
    "is_human",
    "roles",
    "competence_statement",
    "conflict_status",
    "conflict_details",
    "privacy_notice_accepted",
    "privacy_retention_accepted",
}
DECLARATION_KEYS = {
    "decisions_are_my_own",
    "evidence_inspected",
    "model_output_is_not_human_judgment",
    "limitations_understood",
}
RECEIPT_KEYS = {
    "schema_version",
    "status",
    "receipt_id",
    "validated_at",
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
    "queue_semantic_sha256",
    "review_queue_sha256",
    "packet_sha256",
    "attestation_sha256",
    "reviewer",
    "decision_files",
    "bound_inputs",
    "decision_coverage_complete",
    "decision_semantics_status",
    "ready_for_review_import",
    "ready_for_reviewed_packet",
    "ready_for_prose",
    "what_is_not_concluded",
}

NONCLAIMS = [
    "cryptographic or legal identity proof",
    "reviewer competence in fact",
    "decision correctness",
    "claim truth",
    "source safety in fact",
    "omission correctness",
    "literature completeness",
    "mission success",
    "final prose readiness",
    "product readiness",
    "scientific correctness",
]

HUMAN_REVIEW_MATERIAL_NAMES = (
    "REVIEW_START_HERE.md",
    "claim_review_worksheet.csv",
    "source_safety_worksheet.csv",
    "omission_review_worksheet.csv",
    "workflow_blocker_worksheet.md",
    "human_attestation_worksheet.md",
)


def prepare_human_review_packet(
    *,
    review_queue_path: Path,
    output_dir: Path,
    force: bool = False,
    now: Callable[[], str] = utc_now_iso,
) -> dict[str, Any]:
    queue_path, queue, queue_raw = _selected_queue(review_queue_path)
    output_dir = output_dir.absolute()
    packet = _packet_payload(queue_path=queue_path, queue=queue, queue_raw=queue_raw, created_at=now())
    packet_raw = pretty_json_bytes(packet)
    template = _attestation_template(
        packet_sha256=_sha(packet_raw),
        review_queue_sha256=_sha(queue_raw),
    )
    _write_directory(
        output_dir,
        {
            "human_review_packet.json": packet_raw,
            "human_attestation_template.json": pretty_json_bytes(template),
        },
        force=force,
    )
    _write_human_review_materials(
        output_dir=output_dir,
        packet=packet,
        queue=queue,
        queue_path=queue_path,
        force=True,
    )
    return {
        "schema_version": "ra-survey-human-review-packet-result-v1",
        "status": "human_review_packet_prepared_unattested",
        "output_dir": str(output_dir),
        "human_review_packet_path": str(output_dir / "human_review_packet.json"),
        "human_attestation_template_path": str(output_dir / "human_attestation_template.json"),
        "review_queue_sha256": _sha(queue_raw),
        "packet_sha256": _sha(packet_raw),
        "human_attested": False,
        "ready_for_review_import": False,
        "what_is_not_concluded": NONCLAIMS,
    }


def render_human_review_materials(
    *, packet_path: Path, output_dir: Path | None = None, force: bool = False,
) -> dict[str, Any]:
    """Render plain-language review materials without rewriting packet JSON.

    The packet and selected queue remain the machine authority. This helper is
    deliberately additive so a reviewer-facing repair cannot silently change
    the packet digest already bound by an attestation template or result note.
    """
    packet_path = packet_path.absolute()
    packet, packet_raw = read_json_object_strict(packet_path, label="human review packet")
    queue_path, queue, queue_raw = _selected_queue(Path(packet["review_queue_path"]))
    packet, _ = _read_prepared_packet(
        packet_path,
        queue_path=queue_path,
        queue=queue,
        queue_raw=queue_raw,
    )
    target = (output_dir or packet_path.parent).absolute()
    assert_public_write_path_allowed(target)
    if target.exists() and target.is_symlink():
        raise MissionStateError("unsafe_attestation_output", "review materials output cannot be a symlink")
    target.mkdir(parents=True, exist_ok=True)
    return _write_human_review_materials(
        output_dir=target,
        packet=packet,
        queue=queue,
        queue_path=queue_path,
        force=force,
    )


def _write_human_review_materials(
    *,
    output_dir: Path,
    packet: dict[str, Any],
    queue: dict[str, Any],
    queue_path: Path,
    force: bool,
) -> dict[str, Any]:
    materials = _human_review_material_bytes(
        packet=packet,
        queue=queue,
        queue_path=queue_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, raw in materials.items():
        path = output_dir / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise MissionStateError("unsafe_attestation_output", f"review material path is unsafe: {path}")
        if path.exists() and not force:
            raise MissionStateError("output_exists", f"review material already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return {
        "status": "human_review_materials_rendered",
        "output_dir": str(output_dir),
        "files": [str(output_dir / name) for name in materials],
        "packet_sha256": _sha(pretty_json_bytes(packet)),
        "review_queue_sha256": packet["review_queue_sha256"],
        "what_is_not_concluded": NONCLAIMS,
    }


def _human_review_material_bytes(
    *, packet: dict[str, Any], queue: dict[str, Any], queue_path: Path,
) -> dict[str, bytes]:
    mission_root = queue_path.parents[3]
    anchors = _read_optional_json(
        mission_root / "retained_evidence" / "anchor_inventory.json",
    ).get("anchors", [])
    anchor_by_paper: dict[str, list[dict[str, Any]]] = {}
    for row in anchors:
        if isinstance(row, dict):
            anchor_by_paper.setdefault(str(row.get("canonical_identifier", "")), []).append(row)
    source_rows: dict[str, dict[str, Any]] = {}
    seed_row = _read_optional_json(
        mission_root / "retained_evidence" / "sources" / "2201_12220v3.json",
    )
    if seed_row:
        source_rows[str(seed_row.get("canonical_identifier"))] = seed_row
    for path in sorted((mission_root / "retained_evidence" / "sources").glob("*.json")):
        row = _read_optional_json(path)
        if row:
            source_rows[str(row.get("canonical_identifier"))] = row
    candidate_titles = {
        str(row.get("candidate_id")): str(row.get("title") or "title unavailable")
        for row in _read_optional_json(
            mission_root / "packet" / "candidate_ledger.json",
        ).get("included", [])
        if isinstance(row, dict)
    }

    source_materials: dict[str, bytes] = {}
    source_reading_paths: dict[str, str] = {}
    for identifier, source_row in sorted(source_rows.items()):
        reading_path, rendered = _source_reading_materials(
            identifier=identifier,
            source_row=source_row,
            anchor_rows=anchor_by_paper.get(identifier, []),
        )
        source_reading_paths[identifier] = reading_path
        source_materials.update(rendered)

    claims = packet["items_by_type"]["claim_candidate"]
    safety = packet["items_by_type"]["source_safety"]
    omissions = packet["items_by_type"]["omission_risk"]
    claim_rows: list[dict[str, str]] = []
    for item in claims:
        paper_id = str((item.get("paper_ids") or [""])[0])
        identifier = _identifier_for_paper_id(paper_id, source_rows)
        paper_anchors = anchor_by_paper.get(identifier, [])
        sections = _anchor_section_summary(paper_anchors)
        source_path = source_reading_paths.get(identifier) or _review_source_path(
            identifier=identifier, source_row=source_rows.get(identifier, {}),
        )
        claim_rows.append({
            "paper": str(item.get("title_or_anchor", "")),
            "identifier": identifier,
            "queue_item_id": str(item.get("item_id", "")),
            "why_selected": _claim_selection_reason(identifier),
            "machine_anchor_count": str(len(item.get("anchor_ids") or [])),
            "suggested_sections_and_anchors": sections,
            "local_source_to_inspect": source_path,
            "review_question": "Does this paper support one precise technical claim relevant to Neural Optimal Transport?",
            "decision": "",
            "claim_text_if_supported": "",
            "support_class": "",
            "anchor_ids_if_supported": "",
            "evidence_note": "",
            "next_action_if_rejected_or_blocked": "",
        })

    safety_rows: list[dict[str, str]] = []
    for item in safety:
        identifier = f"arxiv:{item.get('arxiv_id')}"
        source_row = source_rows.get(identifier, {})
        safety_rows.append({
            "paper": str(source_row.get("title") or item.get("paper_id", "")),
            "identifier": identifier,
            "queue_item_id": str(item.get("item_id", "")),
            "local_source_to_inspect": source_reading_paths.get(identifier) or _review_source_path(
                identifier=identifier, source_row=source_row,
            ),
            "checks_required": "retraction; withdrawal; expression of concern; major erratum/corrigendum; version consistency",
            "decision": "",
            "evidence_type": "",
            "evidence_source": "",
            "evidence_note": "",
            "reason_if_blocked_or_quarantined": "",
            "next_action_if_blocked_or_quarantined": "",
        })

    omission_rows: list[dict[str, str]] = []
    for item in omissions:
        omission_rows.append({
            "risk_id": str(item.get("risk_id", "")),
            "item_id": str(item.get("item_id", "")),
            "risk_kind": str(item.get("risk_source_type", "")),
            "candidate_or_limitation": str(item.get("risk_source_id", "")),
            "title_if_known": candidate_titles.get(str(item.get("risk_source_id", "")), "not applicable or unavailable"),
            "machine_reason": str(item.get("reason", "")),
            "human_choice": "",
            "reason": "",
            "next_action_if_kept_open": "",
            "scope_basis_if_closed": "",
        })

    workflow = next(iter(packet["items_by_type"]["workflow_blocker"]), {})
    workflow_md = _workflow_worksheet_markdown(workflow=workflow, claims=claims)
    attestation_md = _attestation_worksheet_markdown(packet=packet)
    guide_md = _review_start_markdown(
        packet=packet,
        queue_path=queue_path,
        claim_rows=claim_rows,
        safety_rows=safety_rows,
        omission_rows=omission_rows,
        workflow=workflow,
    )
    return {
        "REVIEW_START_HERE.md": guide_md.encode("utf-8"),
        "claim_review_worksheet.csv": _csv_bytes(claim_rows),
        "source_safety_worksheet.csv": _csv_bytes(safety_rows),
        "omission_review_worksheet.csv": _csv_bytes(omission_rows),
        "workflow_blocker_worksheet.md": workflow_md.encode("utf-8"),
        "human_attestation_worksheet.md": attestation_md.encode("utf-8"),
        **source_materials,
    }


def _read_optional_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _identifier_for_paper_id(paper_id: str, source_rows: dict[str, dict[str, Any]]) -> str:
    for identifier, row in source_rows.items():
        if row.get("source_paper_id") == paper_id:
            return identifier
    return paper_id.removeprefix("candidate_arxiv_").replace("_", ".")


def _review_source_path(*, identifier: str, source_row: dict[str, Any]) -> str:
    original = source_row.get("original_record_path")
    if isinstance(original, str) and original:
        candidate = Path(original).parent / "accepted_source.body"
        if candidate.is_file():
            return str(candidate)
        try:
            record = json.loads(Path(original).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            record = {}
        artifact_root = record.get("artifact_root") if isinstance(record, dict) else None
        if isinstance(artifact_root, str):
            for relative in ("unpacked/main.tex", "derived/flattened.tex", "original/source-package"):
                candidate = Path(artifact_root) / relative
                if candidate.is_file():
                    return str(candidate)
        return original
    return f"retained_evidence/sources/{identifier.removeprefix('arxiv:').replace('.', '_')}.json"


def _source_reading_materials(
    *,
    identifier: str,
    source_row: dict[str, Any],
    anchor_rows: list[dict[str, Any]],
) -> tuple[str, dict[str, bytes]]:
    """Expose bounded text members as reviewer-local reading copies.

    The original source archives remain immutable. Only text members needed for
    inspection are copied into the review bundle, with path traversal rejected
    and conservative per-source/total caps.
    """
    slug = identifier.removeprefix("arxiv:").replace(".", "_")
    root = PurePosixPath("source_reading") / slug
    rendered: dict[str, bytes] = {}
    title = str(source_row.get("title") or identifier)
    source_path = source_row.get("original_record_path")
    source_files: list[tuple[str, bytes]] = []
    if isinstance(source_path, str) and source_path:
        record_path = Path(source_path)
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            record = {}
        archive = record_path.parent / "accepted_source.body"
        if archive.is_file() and tarfile.is_tarfile(archive):
            try:
                with tarfile.open(archive, mode="r:*") as handle:
                    members = []
                    for member in handle.getmembers():
                        name = PurePosixPath(member.name)
                        if not member.isfile() or name.is_absolute() or ".." in name.parts:
                            continue
                        if name.suffix.casefold() not in {".tex", ".bbl", ".bib", ".md", ".json"}:
                            continue
                        if member.size > 1_000_000:
                            continue
                        members.append((name.as_posix(), member))
                    main_name = str(record.get("main_tex_member") or "")
                    members.sort(key=lambda pair: (0 if pair[0] == main_name else 1, pair[0]))
                    total = 0
                    for name, member in members:
                        extracted = handle.extractfile(member)
                        if extracted is None:
                            continue
                        raw = extracted.read(2_000_000)
                        if len(raw) != member.size or total + len(raw) > 4_000_000:
                            continue
                        source_files.append((name, raw))
                        total += len(raw)
            except (OSError, tarfile.TarError):
                source_files = []
        if not source_files:
            artifact_root = record.get("artifact_root") if isinstance(record, dict) else None
            if isinstance(artifact_root, str):
                for relative in ("unpacked/main.tex", "derived/flattened.tex", "unpacked/references.bib"):
                    candidate = Path(artifact_root) / relative
                    try:
                        raw = candidate.read_bytes()
                    except OSError:
                        continue
                    if len(raw) <= 4_000_000:
                        source_files.append((relative, raw))
    if not source_files:
        source_files.append(("source_record.json", pretty_json_bytes(source_row)))
    for name, raw in source_files:
        safe_name = PurePosixPath(name)
        if safe_name.is_absolute() or ".." in safe_name.parts:
            continue
        rendered[str(root / safe_name)] = raw
    sections = _anchor_section_summary(anchor_rows)
    readme = "\n".join([
        f"# {title}",
        "",
        f"Identifier: `{identifier}`",
        "",
        "This is a bounded text-only reading copy generated from the retained source evidence. The original source bytes and their hashes remain outside this worksheet.",
        "",
        "## Suggested anchors",
        "",
        sections,
        "",
        "## Files",
        "",
        *[f"- `{name}`" for name, _ in source_files],
        "",
        "Do not treat this copy, a title, an abstract, a parser status, or an anchor list as claim support without inspecting the technical text.",
        "",
    ])
    rendered[str(root / "README.md")] = readme.encode("utf-8")
    return str(root / "README.md"), rendered


def _anchor_section_summary(rows: list[dict[str, Any]]) -> str:
    summaries: list[str] = []
    for row in sorted(rows, key=lambda value: (int(value.get("line", 0)), str(value.get("anchor_id"))))[:8]:
        section = row.get("containing_section") or {}
        title = section.get("title") or row.get("title") or "unlabelled anchor"
        line = row.get("line", "?")
        role = row.get("role", "anchor candidate")
        labels = ", ".join(str(value) for value in row.get("labels") or [])
        suffix = f" [{labels}]" if labels else ""
        summaries.append(f"{title} (line {line}, {role}{suffix})")
    return "; ".join(summaries) or "No retained anchor summary; treat this source as blocked for technical support."


def _claim_selection_reason(identifier: str) -> str:
    return {
        "arxiv:2201.12220v3": "The explicit seed paper.",
        "arxiv:1412.6980": "Seed-cited experimental-details reference; nominated because it was source-located.",
        "arxiv:1506.03365": "Seed-cited evaluation/dataset reference; nominated because it was source-located.",
        "arxiv:1709.08894": "Seed-cited ambiguous-context reference; nominated because it was source-located.",
        "arxiv:1805.07277": "Seed-cited one-to-many translation reference; nominated because it was source-located.",
        "arxiv:1902.07197": "Seed-cited related-work reference; nominated because it was source-located.",
        "arxiv:2003.06635": "Seed-cited related-work reference; nominated because it was source-located.",
        "arxiv:2003.06788": "Seed-cited comparison reference; nominated because it was source-located.",
    }.get(identifier, "Source-located candidate in the bounded M21 queue.")


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    if not rows:
        return b"\n"
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _review_start_markdown(
    *,
    packet: dict[str, Any],
    queue_path: Path,
    claim_rows: list[dict[str, str]],
    safety_rows: list[dict[str, str]],
    omission_rows: list[dict[str, str]],
    workflow: dict[str, Any],
) -> str:
    lines = [
        "# M22B Human Review: Start Here",
        "",
        "This is the reviewer-facing guide for the selected Neural Optimal Transport evidence. The adjacent JSON files are machine interchange artifacts; you do not need to understand their schema to perform the review.",
        "",
        "## What this review is",
        "",
        f"The packet contains {len(claim_rows)} paper-level claim decisions, {len(safety_rows)} source-safety decisions, {len(omission_rows)} omission-risk decisions, and one workflow-blocker decision. The packet SHA-256 is `{_sha(pretty_json_bytes(packet))}`; the selected queue SHA-256 is `{packet['review_queue_sha256']}`. Neither is changed by this guide.",
        "",
        "Your task is to record what the retained evidence actually supports. You are not being asked to prove that the survey is complete, rank methods, or approve final prose. It is valid to reject every claim candidate and leave the workflow blocker open.",
        "",
        "## Review order",
        "",
        "1. Read `claim_review_worksheet.csv`. For each paper, open the generated `source_reading/.../README.md` named in `local_source_to_inspect`, then inspect its listed local text files and section/line pointers. Decide whether one precise technical claim is supportable. Use `rejected_or_blocked` when it is not. Do not turn an anchor title, citation count, abstract, or machine parser output into a claim.",
        "2. Read `source_safety_worksheet.csv`. For each source, check the five listed status/version questions. Choose `checked_clear` only when the checks are actually documented; otherwise choose `blocked` or `quarantined` and explain why.",
        "3. Read `omission_review_worksheet.csv`. These are not 58 separate demands to find more papers. They are risks retained so that unused bibliography entries, identifier-free references, the 1412.6980 parse gap, and unavailable forward citations cannot disappear. Choose whether each risk stays open, is omitted for this recorded scope, or requires expansion.",
        "4. Read `workflow_blocker_worksheet.md`. This is derived from the seven claim decisions; it is not a new paper review. Leave it open if no reviewed supported technical claim exists.",
        "5. Complete `human_attestation_worksheet.md` and the supplied `human_attestation_template.json`. The attestation says that the decisions are yours and that you understand the limitations; it is not legal identity proof.",
        "",
        "## Decision vocabulary",
        "",
        "- Claim support: `human_reviewed_passed` only for a precise claim tied to checked technical text and exact retained anchor IDs. Otherwise use `rejected_or_blocked` with a reason and next action.",
        "- Source safety: `checked_clear` means all five checks were performed and no notice remains. `blocked` means the checks could not be completed. `quarantined` means a retraction, withdrawal, version conflict, erratum, or other explicit safety concern was found.",
        "- Omission risk: `acceptable_omission` closes only the current bounded scope; `out_of_scope` records a deliberate scope exclusion; `must_inspect`, `expand_scope`, and `blocked_pending_source` keep work open. None means literature completeness.",
        "- Workflow blocker: `resolved_by_reviewed_evidence` is allowed only when the required claim rows genuinely provide supported claims. Otherwise use `remains_open`.",
        "",
        "## Important limitations",
        "",
        "- Forward-citation coverage is permanently unavailable and non-blocking; it is not zero citations and not complete coverage.",
        "- The 55 unused identifier-bearing bibliography entries and 195 identifier-free units are visible omission risks, not relevance rejections.",
        "- `1412.6980` has a source-format parse gap. Do not infer its contents from metadata.",
        "- The seven source rows were selected because they were source-located in the seed, not because the machine proved relevance or quality.",
        "- A completed receipt can establish that a human made decisions; it cannot establish claim truth, source safety in fact, scientific correctness, or north-star completion.",
        "",
        "## Return",
        "",
        "Fill the CSV/Markdown worksheets and return them with the completed JSON attestation template. Codex may mechanically transcribe your stated choices into the exact decision envelopes, but you must inspect the transcription before attesting. Do not edit `human_review_packet.json` or change its packet hash.",
        "",
        f"Machine queue path (for conversion only): `{queue_path}`",
        "",
    ]
    return "\n".join(lines)


def _workflow_worksheet_markdown(*, workflow: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    required = ", ".join(str(value) for value in workflow.get("required_evidence_queue_item_ids") or [])
    return "\n".join([
        "# Workflow-Blocker Review",
        "",
        f"Blocker: **{workflow.get('reason', 'No reviewed supported technical claim rows are present.')}**",
        "",
        "This row summarizes the claim review. It is not an additional scientific source. Review the seven claim rows first.",
        "",
        f"Required claim queue items: `{required}`",
        "",
        "Choose one:",
        "",
        "- `remains_open`: use this when no claim row is genuinely supported, when all claims are rejected, or when source safety prevents promotion. Add a concise next action.",
        "- `resolved_by_reviewed_evidence`: use this only when the supported claim decisions really cover every required claim queue item listed above. The exact list must be copied into `evidence_queue_item_ids`.",
        "",
        "Do not resolve this blocker merely because the packet was generated or because a paper has machine anchors.",
        "",
    ])


def _attestation_worksheet_markdown(*, packet: dict[str, Any]) -> str:
    return "\n".join([
        "# Human Attestation Worksheet",
        "",
        "Complete this only after you have made or reviewed all four decision families.",
        "",
        f"Packet SHA-256: `{_sha(pretty_json_bytes(packet))}`",
        f"Queue SHA-256: `{packet['review_queue_sha256']}`",
        "",
        "Provide these values in `human_attestation_template.json`:",
        "",
        "- your display name and an opaque reviewer ID;\n"
        "- `authority_origin`: `human_self_attested`;\n"
        "- `is_human`: `true`;\n"
        "- all four listed review roles;\n"
        "- a short competence statement for this bounded review;\n"
        "- `conflict_status`: `none_declared` or `disclosed`, with details if disclosed;\n"
        "- acceptance of the privacy notice and retention notice;\n"
        "- all four declarations set to true: decisions are yours, evidence was inspected, model output is not human judgment, and limitations are understood;\n"
        "- the attestation time after all decision rows were reviewed.",
        "",
        "This is a self-attestation of participation, not proof of identity, competence, decision correctness, or scientific correctness.",
        "",
    ])


def validate_human_attestation(
    *,
    review_queue_path: Path,
    packet_path: Path,
    attestation_path: Path,
    decision_paths: dict[str, Path],
    output_dir: Path,
    force: bool = False,
    now: Callable[[], str] = utc_now_iso,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    queue_path, queue, queue_raw = _selected_queue(review_queue_path)
    packet, packet_raw = _read_prepared_packet(
        packet_path,
        queue_path=queue_path,
        queue=queue,
        queue_raw=queue_raw,
    )
    attestation, attestation_raw = _read_attestation(
        attestation_path,
        packet_sha256=_sha(packet_raw),
        review_queue_sha256=_sha(queue_raw),
    )
    _validate_reviewer(attestation["reviewer"])
    attested_at = normalize_reviewed_at(attestation["attested_at"])
    if attestation["attested_at"] != attested_at:
        raise MissionStateError("noncanonical_human_attestation", "attested_at must be normalized UTC")
    _validate_declarations(attestation["declarations"])
    decisions = _validate_decision_files(
        queue=queue,
        queue_raw=queue_raw,
        decision_paths=decision_paths,
        reviewer_display=attestation["reviewer"]["display_name"],
        attested_at=attested_at,
    )
    bound_raw = {
        "review_queue.json": queue_raw,
        "human_review_packet.json": packet_raw,
        "human_attestation.json": attestation_raw,
        **{
            f"{decision_type}_decisions.json": decisions[decision_type]["raw"]
            for decision_type in DECISION_TYPES
        },
    }
    validated_at = normalize_reviewed_at(now())
    receipt = _receipt_payload(
        queue=queue,
        queue_raw=queue_raw,
        packet_raw=packet_raw,
        attestation=attestation,
        attestation_raw=attestation_raw,
        decisions=decisions,
        bound_raw=bound_raw,
        validated_at=validated_at,
    )
    _write_directory(
        output_dir,
        {
            **{f"bound_inputs/{name}": raw for name, raw in bound_raw.items()},
            "human_attestation_receipt.json": pretty_json_bytes(receipt),
        },
        force=force,
    )
    validate_human_attestation_receipt(output_dir / "human_attestation_receipt.json")
    return {
        "schema_version": "ra-survey-human-attestation-validation-result-v1",
        "status": "human_self_attestation_validated",
        "output_dir": str(output_dir),
        "receipt_path": str(output_dir / "human_attestation_receipt.json"),
        "receipt_id": receipt["receipt_id"],
        "decision_coverage_complete": True,
        "decision_semantics_status": "deferred_to_existing_review_importers",
        "ready_for_review_import": True,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }


def validate_human_attestation_receipt(path: Path) -> dict[str, Any]:
    receipt, raw = read_json_object_strict(path, label="human attestation receipt")
    require_exact_keys(receipt, RECEIPT_KEYS, "human attestation receipt")
    if raw != pretty_json_bytes(receipt):
        raise MissionStateError("noncanonical_attestation_receipt", "receipt must be canonical pretty JSON")
    if receipt.get("schema_version") != HUMAN_ATTESTATION_RECEIPT_SCHEMA:
        raise MissionStateError("invalid_attestation_receipt", "receipt schema is unsupported")
    root = path.absolute().parent
    bound = receipt.get("bound_inputs")
    if not isinstance(bound, list) or not bound:
        raise MissionStateError("invalid_attestation_receipt", "bound_inputs must be nonempty")
    names = [row.get("name") for row in bound if isinstance(row, dict)]
    if names != sorted(names) or len(names) != len(set(names)):
        raise MissionStateError("invalid_attestation_receipt", "bound input names must be unique and sorted")
    raw_by_name: dict[str, bytes] = {}
    for row in bound:
        require_exact_keys(row, {"name", "relative_path", "sha256", "size_bytes"}, "bound input")
        name = row["name"]
        relative = row["relative_path"]
        if not isinstance(name, str) or not isinstance(relative, str) or relative != f"bound_inputs/{name}":
            raise MissionStateError("invalid_attestation_receipt", "bound input path is invalid")
        candidate = root / relative
        if not candidate.is_file() or candidate.is_symlink() or candidate.resolve().parent != (root / "bound_inputs").resolve():
            raise MissionStateError("unsafe_attestation_input", f"bound input {name} is unsafe")
        candidate_raw = candidate.read_bytes()
        if len(candidate_raw) != row["size_bytes"] or _sha(candidate_raw) != row["sha256"]:
            raise MissionStateError("attestation_input_tampered", f"bound input {name} differs from receipt")
        raw_by_name[name] = candidate_raw
    required_names = {
        "review_queue.json",
        "human_review_packet.json",
        "human_attestation.json",
        *(f"{decision_type}_decisions.json" for decision_type in DECISION_TYPES),
    }
    if set(raw_by_name) != required_names:
        raise MissionStateError("invalid_attestation_receipt", "bound input set is incomplete")
    queue = _json_object(raw_by_name["review_queue.json"], label="bound review queue")
    packet = _json_object(raw_by_name["human_review_packet.json"], label="bound human review packet")
    attestation = _json_object(raw_by_name["human_attestation.json"], label="bound human attestation")
    if (
        _sha(raw_by_name["review_queue.json"]) != receipt["review_queue_sha256"]
        or _sha(raw_by_name["human_review_packet.json"]) != receipt["packet_sha256"]
        or _sha(raw_by_name["human_attestation.json"]) != receipt["attestation_sha256"]
    ):
        raise MissionStateError("attestation_receipt_binding_mismatch", "receipt top-level hashes differ")
    require_exact_keys(packet, PACKET_KEYS, "bound human review packet")
    if raw_by_name["human_review_packet.json"] != pretty_json_bytes(packet):
        raise MissionStateError("noncanonical_human_review_packet", "bound packet is not canonical")
    packet_queue_path = packet.get("review_queue_path")
    if not isinstance(packet_queue_path, str) or not Path(packet_queue_path).is_absolute():
        raise MissionStateError("invalid_human_review_packet", "bound packet queue path is invalid")
    expected_packet = _packet_payload(
        queue_path=Path(packet_queue_path),
        queue=queue,
        queue_raw=raw_by_name["review_queue.json"],
        created_at=packet.get("created_at"),
    )
    if packet != expected_packet:
        raise MissionStateError("stale_human_review_packet", "bound packet differs from bound queue")
    _validate_attestation_value(
        attestation,
        raw=raw_by_name["human_attestation.json"],
        packet_sha256=receipt["packet_sha256"],
        review_queue_sha256=receipt["review_queue_sha256"],
    )
    attested_at = normalize_reviewed_at(attestation["attested_at"])
    decision_values = {
        decision_type: (
            _json_object(
                raw_by_name[f"{decision_type}_decisions.json"],
                label=f"bound {decision_type} decisions",
            ),
            raw_by_name[f"{decision_type}_decisions.json"],
        )
        for decision_type in DECISION_TYPES
    }
    replayed_decisions = _validate_decision_values(
        queue=queue,
        queue_raw=raw_by_name["review_queue.json"],
        decision_values=decision_values,
        reviewer_display=attestation["reviewer"]["display_name"],
        attested_at=attested_at,
    )
    expected_receipt = _receipt_payload(
        queue=queue,
        queue_raw=raw_by_name["review_queue.json"],
        packet_raw=raw_by_name["human_review_packet.json"],
        attestation=attestation,
        attestation_raw=raw_by_name["human_attestation.json"],
        decisions=replayed_decisions,
        bound_raw=raw_by_name,
        validated_at=receipt.get("validated_at"),
    )
    if receipt != expected_receipt:
        raise MissionStateError("invalid_attestation_receipt_replay", "receipt differs from bound-input replay")
    return receipt


def export_human_receipt_archive(path: Path) -> dict[str, Any]:
    """Return a self-contained, canonicalizable copy of a validated receipt."""
    receipt_path = path.absolute()
    receipt = validate_human_attestation_receipt(receipt_path)
    root = receipt_path.parent
    bound_inputs: list[dict[str, Any]] = []
    for row in receipt["bound_inputs"]:
        name = row["name"]
        candidate = root / row["relative_path"]
        raw = candidate.read_bytes()
        bound_inputs.append({
            "name": name,
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
            "base64": base64.b64encode(raw).decode("ascii"),
        })
    return {
        "schema_version": HUMAN_RECEIPT_ARCHIVE_SCHEMA,
        "receipt": receipt,
        "bound_inputs": bound_inputs,
    }


def validate_human_receipt_archive(archive: Any) -> dict[str, Any]:
    """Validate an embedded receipt archive without trusting external paths."""
    if not isinstance(archive, dict) or set(archive) != {"schema_version", "receipt", "bound_inputs"}:
        raise MissionStateError("invalid_human_receipt_archive", "receipt archive fields are not exact")
    if archive.get("schema_version") != HUMAN_RECEIPT_ARCHIVE_SCHEMA:
        raise MissionStateError("invalid_human_receipt_archive", "receipt archive schema is unsupported")
    receipt = archive.get("receipt")
    bound = archive.get("bound_inputs")
    if not isinstance(receipt, dict) or not isinstance(bound, list):
        raise MissionStateError("invalid_human_receipt_archive", "receipt archive contents are invalid")
    required_names = {
        "review_queue.json",
        "human_review_packet.json",
        "human_attestation.json",
        *(f"{decision_type}_decisions.json" for decision_type in DECISION_TYPES),
    }
    expected_names = {row.get("name") for row in receipt.get("bound_inputs", []) if isinstance(row, dict)}
    archive_names = [row.get("name") for row in bound if isinstance(row, dict)]
    if (
        expected_names != required_names
        or archive_names != sorted(required_names)
        or len(bound) != len(required_names)
    ):
        raise MissionStateError("invalid_human_receipt_archive", "receipt archive input coverage is incomplete")
    with tempfile.TemporaryDirectory(prefix="ra-human-receipt-") as temporary:
        root = Path(temporary)
        inputs = root / "bound_inputs"
        inputs.mkdir()
        receipt_rows = {row["name"]: row for row in receipt["bound_inputs"]}
        for row in sorted(bound, key=lambda item: item.get("name", "")):
            require_exact_keys(row, {"name", "sha256", "size_bytes", "base64"}, "receipt archive input")
            expected = receipt_rows.get(row["name"])
            if expected is None or row["sha256"] != expected["sha256"] or row["size_bytes"] != expected["size_bytes"]:
                raise MissionStateError("invalid_human_receipt_archive", "receipt archive metadata differs from receipt")
            try:
                raw = base64.b64decode(row["base64"], validate=True)
            except (ValueError, TypeError) as exc:
                raise MissionStateError("invalid_human_receipt_archive", "receipt archive input is not valid base64") from exc
            (inputs / row["name"]).write_bytes(raw)
        receipt_raw = pretty_json_bytes(receipt)
        receipt_path = root / "human_attestation_receipt.json"
        receipt_path.write_bytes(receipt_raw)
        validate_human_attestation_receipt(receipt_path)
    return receipt


def validate_human_receipt_decision(
    *,
    receipt: dict[str, Any],
    decision_type: str,
    decisions_raw: bytes,
    expected_binding: dict[str, Any],
) -> dict[str, Any]:
    """Bind one imported decision envelope to an already replayed receipt."""
    for field, expected in expected_binding.items():
        if receipt.get(field) != expected:
            raise MissionStateError("stale_human_receipt", f"human receipt differs on {field}")
    matches = [row for row in receipt["decision_files"] if row.get("decision_type") == decision_type]
    if len(matches) != 1:
        raise MissionStateError("invalid_human_receipt", "human receipt lacks one exact decision family")
    row = matches[0]
    if row.get("sha256") != _sha(decisions_raw) or row.get("size_bytes") != len(decisions_raw):
        raise MissionStateError("human_receipt_decision_mismatch", "imported decisions differ from the attested bytes")
    return row


def human_receipt_archive_bound_input(
    archive: Any,
    *,
    name: str,
) -> tuple[dict[str, Any], bytes]:
    """Replay an archive and return one exact bound input."""
    receipt = validate_human_receipt_archive(archive)
    matches = [row for row in archive["bound_inputs"] if row.get("name") == name]
    if len(matches) != 1:
        raise MissionStateError("invalid_human_receipt_archive", f"receipt archive lacks {name}")
    raw = base64.b64decode(matches[0]["base64"], validate=True)
    return receipt, raw


def _selected_queue(path: Path) -> tuple[Path, dict[str, Any], bytes]:
    selected = validate_selected_review_queue(path)
    queue_path = selected.review_queue_path.absolute()
    queue, raw = read_json_object_strict(queue_path, label="selected review queue")
    required = set(SUPPORTED_DECISION_TYPES)
    item_types = {row.get("queue_type") for row in queue.get("items") or [] if isinstance(row, dict)}
    if item_types - required:
        raise MissionStateError("unsupported_queue_type", "selected queue contains an unsupported review type")
    return queue_path, queue, raw


def _packet_payload(
    *, queue_path: Path, queue: dict[str, Any], queue_raw: bytes, created_at: str
) -> dict[str, Any]:
    items = queue.get("items") or []
    by_type = {
        decision_type: [row for row in items if row.get("queue_type") == decision_type]
        for decision_type in DECISION_TYPES
    }
    return {
        "schema_version": HUMAN_REVIEW_PACKET_SCHEMA,
        "status": "human_review_required_unattested",
        "created_at": normalize_reviewed_at(created_at),
        **_queue_lineage(queue),
        "review_queue_path": str(queue_path),
        "review_queue_sha256": _sha(queue_raw),
        "topic": queue.get("topic"),
        "queue_counts": queue.get("queue_counts"),
        "required_decision_types": list(DECISION_TYPES),
        "required_roles": list(REVIEW_ROLES),
        "items_by_type": by_type,
        "operator_contract": {
            "human_attested": False,
            "model_or_fixture_may_attest": False,
            "decision_semantics_validation": "performed_later_by_existing_review_importers",
            "new_external_actions_authorized": False,
        },
        "what_is_not_concluded": NONCLAIMS,
    }


def _attestation_template(*, packet_sha256: str, review_queue_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": HUMAN_ATTESTATION_SCHEMA,
        "status": "unattested_template",
        "packet_sha256": packet_sha256,
        "review_queue_sha256": review_queue_sha256,
        "reviewer": {
            "opaque_reviewer_id": None,
            "display_name": None,
            "authority_origin": None,
            "is_human": None,
            "roles": list(REVIEW_ROLES),
            "competence_statement": None,
            "conflict_status": None,
            "conflict_details": None,
            "privacy_notice_accepted": None,
            "privacy_retention_accepted": None,
        },
        "attested_at": None,
        "declarations": {key: None for key in sorted(DECLARATION_KEYS)},
    }


def _read_prepared_packet(
    path: Path,
    *,
    queue_path: Path,
    queue: dict[str, Any],
    queue_raw: bytes,
) -> tuple[dict[str, Any], bytes]:
    packet, raw = read_json_object_strict(path, label="human review packet")
    require_exact_keys(packet, PACKET_KEYS, "human review packet")
    if raw != pretty_json_bytes(packet) or packet.get("schema_version") != HUMAN_REVIEW_PACKET_SCHEMA:
        raise MissionStateError("invalid_human_review_packet", "packet is not canonical or supported")
    expected = _packet_payload(
        queue_path=queue_path,
        queue=queue,
        queue_raw=queue_raw,
        created_at=packet.get("created_at"),
    )
    if packet != expected:
        raise MissionStateError("stale_human_review_packet", "packet differs from current selected queue")
    return packet, raw


def _read_attestation(
    path: Path, *, packet_sha256: str, review_queue_sha256: str
) -> tuple[dict[str, Any], bytes]:
    value, raw = read_json_object_strict(path, label="human self-attestation")
    _validate_attestation_value(
        value,
        raw=raw,
        packet_sha256=packet_sha256,
        review_queue_sha256=review_queue_sha256,
    )
    return value, raw


def _validate_attestation_value(
    value: dict[str, Any],
    *,
    raw: bytes,
    packet_sha256: str,
    review_queue_sha256: str,
) -> None:
    require_exact_keys(value, ATTESTATION_KEYS, "human self-attestation")
    if raw != pretty_json_bytes(value):
        raise MissionStateError("noncanonical_human_attestation", "attestation must be canonical pretty JSON")
    if value.get("schema_version") != HUMAN_ATTESTATION_SCHEMA or value.get("status") != "completed_human_self_attestation":
        raise MissionStateError("not_human_attested", "completed human self-attestation is required")
    if value.get("packet_sha256") != packet_sha256 or value.get("review_queue_sha256") != review_queue_sha256:
        raise MissionStateError("stale_human_attestation", "attestation packet or queue hash differs")
    _validate_reviewer(value.get("reviewer"))
    attested_at = normalize_reviewed_at(value.get("attested_at"))
    if value.get("attested_at") != attested_at:
        raise MissionStateError("noncanonical_human_attestation", "attested_at must be normalized UTC")
    _validate_declarations(value.get("declarations"))


def _validate_reviewer(value: Any) -> None:
    require_exact_keys(value, REVIEWER_KEYS, "human reviewer declaration")
    opaque_id = normalize_required_text(value.get("opaque_reviewer_id"), field="opaque_reviewer_id").casefold()
    display = normalize_required_text(value.get("display_name"), field="display_name")
    if OPAQUE_ID_RE.fullmatch(opaque_id) is None:
        raise MissionStateError("invalid_opaque_reviewer_id", "opaque reviewer ID has an invalid format")
    if SUSPICIOUS_AUTHORITY.search(opaque_id) or SUSPICIOUS_AUTHORITY.search(display):
        raise MissionStateError("nonhuman_reviewer_identity", "model, fixture, or automation identity cannot attest")
    if value.get("authority_origin") != "human_self_attested" or value.get("is_human") is not True:
        raise MissionStateError("nonhuman_reviewer_authority", "reviewer must explicitly self-attest as human")
    roles = value.get("roles")
    if roles != list(REVIEW_ROLES):
        raise MissionStateError("incomplete_reviewer_roles", "reviewer roles must equal the exact required role list")
    normalize_required_text(value.get("competence_statement"), field="competence_statement")
    conflict_status = value.get("conflict_status")
    conflict_details = value.get("conflict_details")
    if conflict_status == "none_declared":
        if conflict_details not in {None, ""}:
            raise MissionStateError("invalid_conflict_declaration", "none_declared requires empty conflict_details")
    elif conflict_status == "disclosed":
        normalize_required_text(conflict_details, field="conflict_details")
    else:
        raise MissionStateError("invalid_conflict_declaration", "conflict_status must be none_declared or disclosed")
    if value.get("privacy_notice_accepted") is not True or value.get("privacy_retention_accepted") is not True:
        raise MissionStateError("privacy_not_accepted", "both privacy declarations must be accepted")


def _validate_declarations(value: Any) -> None:
    require_exact_keys(value, DECLARATION_KEYS, "human attestation declarations")
    if any(value.get(key) is not True for key in DECLARATION_KEYS):
        raise MissionStateError("incomplete_human_declarations", "every human declaration must be true")


def _validate_decision_files(
    *,
    queue: dict[str, Any],
    queue_raw: bytes,
    decision_paths: dict[str, Path],
    reviewer_display: str,
    attested_at: str,
) -> dict[str, dict[str, Any]]:
    if set(decision_paths) != set(DECISION_TYPES):
        raise MissionStateError("incomplete_decision_file_set", "exactly four decision files are required")
    decision_values: dict[str, tuple[dict[str, Any], bytes]] = {}
    paths: dict[str, Path] = {}
    for decision_type in DECISION_TYPES:
        path = decision_paths[decision_type].absolute()
        if not path.is_file() or path.is_symlink():
            raise MissionStateError("unsafe_decision_file", f"{decision_type} decision file is unsafe")
        envelope, raw = read_json_object_strict(path, label=f"{decision_type} decisions")
        paths[decision_type] = path
        decision_values[decision_type] = (envelope, raw)
    result = _validate_decision_values(
        queue=queue,
        queue_raw=queue_raw,
        decision_values=decision_values,
        reviewer_display=reviewer_display,
        attested_at=attested_at,
    )
    for decision_type in DECISION_TYPES:
        result[decision_type]["path"] = paths[decision_type]
    return result


def _validate_decision_values(
    *,
    queue: dict[str, Any],
    queue_raw: bytes,
    decision_values: dict[str, tuple[dict[str, Any], bytes]],
    reviewer_display: str,
    attested_at: str,
) -> dict[str, dict[str, Any]]:
    if set(decision_values) != set(DECISION_TYPES):
        raise MissionStateError("incomplete_decision_file_set", "exactly four decision files are required")
    required = {
        decision_type: sorted(
            row["item_id"]
            for row in queue.get("items") or []
            if row.get("queue_type") == decision_type
        )
        for decision_type in DECISION_TYPES
    }
    result: dict[str, dict[str, Any]] = {}
    for decision_type in DECISION_TYPES:
        envelope, raw = decision_values[decision_type]
        schema = envelope.get("schema_version")
        if schema not in DECISION_SCHEMAS[decision_type] or envelope.get("decision_type") != decision_type:
            raise MissionStateError("invalid_attested_decision_schema", f"{decision_type} schema/type is unsupported")
        expected_binding = _queue_lineage(queue)
        for field in ("mission_id", "mission_fingerprint", "artifact_set_id", "queue_semantic_sha256"):
            if envelope.get(field) != expected_binding[field]:
                raise MissionStateError("stale_attested_decision", f"{decision_type} {field} differs")
        if envelope.get("review_queue_sha256") != _sha(queue_raw):
            raise MissionStateError("stale_attested_decision", f"{decision_type} queue hash differs")
        if "mission_anchor_generation_id" in envelope and envelope.get("mission_anchor_generation_id") != expected_binding["mission_anchor_generation_id"]:
            raise MissionStateError("stale_attested_decision", f"{decision_type} anchor generation differs")
        rows = envelope.get("decisions")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise MissionStateError("invalid_attested_decisions", f"{decision_type} decisions must be object rows")
        item_ids = [row.get("queue_item_id") for row in rows]
        if any(not isinstance(item_id, str) or not item_id for item_id in item_ids):
            raise MissionStateError("invalid_attested_decisions", f"{decision_type} queue item IDs are invalid")
        if len(item_ids) != len(set(item_ids)) or sorted(item_ids) != required[decision_type]:
            raise MissionStateError("incomplete_attested_decision_coverage", f"{decision_type} coverage is not exact")
        reviewed_at_values: list[str] = []
        for row in rows:
            reviewer = normalize_required_text(row.get("reviewer"), field=f"{decision_type} reviewer")
            if reviewer != reviewer_display:
                raise MissionStateError("attested_reviewer_mismatch", f"{decision_type} reviewer differs")
            reviewed_at = normalize_reviewed_at(row.get("reviewed_at"))
            if reviewed_at > attested_at:
                raise MissionStateError("attestation_precedes_review", f"{decision_type} review occurs after attestation")
            reviewed_at_values.append(reviewed_at)
            if row.get("fixture_only") is True:
                raise MissionStateError("fixture_cannot_be_human_attested", f"{decision_type} row is fixture-only")
            if row.get("review_status") == "model_reviewed_advisory" or row.get("reviewer_authority") == "model_reviewed_advisory":
                raise MissionStateError("model_cannot_be_human_attested", f"{decision_type} row is model advisory")
        result[decision_type] = {
            "raw": raw,
            "schema_version": schema,
            "queue_item_ids": sorted(item_ids),
            "reviewed_at_values": sorted(set(reviewed_at_values)),
        }
    return result


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_attestation_input_json", f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise MissionStateError("invalid_attestation_input_json", f"{label} must be an object")
    return value


def _receipt_payload(
    *,
    queue: dict[str, Any],
    queue_raw: bytes,
    packet_raw: bytes,
    attestation: dict[str, Any],
    attestation_raw: bytes,
    decisions: dict[str, dict[str, Any]],
    bound_raw: dict[str, bytes],
    validated_at: str,
) -> dict[str, Any]:
    decision_files = [
        {
            "decision_type": decision_type,
            "schema_version": decisions[decision_type]["schema_version"],
            "sha256": _sha(decisions[decision_type]["raw"]),
            "size_bytes": len(decisions[decision_type]["raw"]),
            "queue_item_ids": decisions[decision_type]["queue_item_ids"],
            "reviewed_at_values": decisions[decision_type]["reviewed_at_values"],
        }
        for decision_type in DECISION_TYPES
    ]
    bound_inputs = [
        {
            "name": name,
            "relative_path": f"bound_inputs/{name}",
            "sha256": _sha(raw),
            "size_bytes": len(raw),
        }
        for name, raw in sorted(bound_raw.items())
    ]
    reviewer = attestation["reviewer"]
    payload = {
        "schema_version": HUMAN_ATTESTATION_RECEIPT_SCHEMA,
        "status": "human_self_attestation_validated",
        "validated_at": validated_at,
        **_queue_lineage(queue),
        "review_queue_sha256": _sha(queue_raw),
        "packet_sha256": _sha(packet_raw),
        "attestation_sha256": _sha(attestation_raw),
        "reviewer": {
            "opaque_reviewer_id_sha256": _sha(str(reviewer["opaque_reviewer_id"]).encode()),
            "display_name": reviewer["display_name"],
            "authority_origin": reviewer["authority_origin"],
            "roles": reviewer["roles"],
            "conflict_status": reviewer["conflict_status"],
            "privacy_minimized": True,
        },
        "decision_files": decision_files,
        "bound_inputs": bound_inputs,
        "decision_coverage_complete": True,
        "decision_semantics_status": "deferred_to_existing_review_importers",
        "ready_for_review_import": True,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    identity = dict(payload)
    payload["receipt_id"] = f"ha-{_sha(canonical_json_bytes(identity))}"
    return payload


def _queue_lineage(queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "mission_id": queue.get("mission_id"),
        "mission_fingerprint": queue.get("mission_fingerprint"),
        "mission_anchor_generation_id": queue.get("mission_anchor_generation_id"),
        "artifact_set_id": queue.get("artifact_set_id"),
        "queue_semantic_sha256": queue.get("queue_semantic_sha256"),
    }


def _write_directory(output_dir: Path, files: dict[str, bytes], *, force: bool) -> None:
    if output_dir.is_symlink():
        raise MissionStateError("unsafe_attestation_output", "output directory cannot be a symlink")
    if output_dir.exists():
        if not force:
            raise MissionStateError("output_exists", "attestation output already exists")
        if not output_dir.is_dir():
            raise MissionStateError("unsafe_attestation_output", "output path is not a directory")
        shutil.rmtree(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        for relative, raw in files.items():
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        os.replace(staging, output_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "DECISION_TYPES",
    "CLAIM_V4_SCHEMA",
    "HUMAN_ATTESTATION_RECEIPT_SCHEMA",
    "HUMAN_ATTESTATION_SCHEMA",
    "HUMAN_RECEIPT_ARCHIVE_SCHEMA",
    "HUMAN_REVIEW_PACKET_SCHEMA",
    "NONCLAIMS",
    "REVIEW_ROLES",
    "SOURCE_V4_SCHEMA",
    "prepare_human_review_packet",
    "render_human_review_materials",
    "validate_human_attestation",
    "validate_human_attestation_receipt",
    "export_human_receipt_archive",
    "validate_human_receipt_archive",
    "validate_human_receipt_decision",
    "human_receipt_archive_bound_input",
]
