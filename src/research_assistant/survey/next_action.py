from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_next_action(
    *,
    gate: dict[str, Any],
    output_dir: Path,
    topic: str,
    seeds: list[str],
    packet_dir: Path,
    review_queue: dict[str, Any] | None,
    reviewed_artifacts: dict[str, dict[str, Any]],
    coverage_artifacts: dict[str, dict[str, Any]],
    final_artifacts: dict[str, dict[str, Any]],
    anchor_dir: Path | None,
    local_evidence_root: Path | None,
    public_discovery_confirmation: dict[str, Any],
    artifact_initialization_required: bool = False,
    created_at: str,
    schema_version: str,
    nonclaims: list[str],
    public_discovery_max_metadata_records: int,
) -> dict[str, Any]:
    base = _base_next_action(
        gate=gate,
        output_dir=output_dir,
        topic=topic,
        seeds=seeds,
        public_discovery_confirmation=public_discovery_confirmation,
        created_at=created_at,
        schema_version=schema_version,
        nonclaims=nonclaims,
        public_discovery_max_metadata_records=public_discovery_max_metadata_records,
    )
    if gate["gate_id"] != "claim_safety_omission_review":
        return _gate_next_action(base, gate)
    if artifact_initialization_required:
        return {
            **base,
            "action_id": "resume_to_initialize_artifact_state",
            "status": "ready_to_initialize_artifact_state",
            "mission_status": "ready_for_local_continuation",
            "summary": "Resume this committed mission to compose coverage before the unified review queue and atomically select the immutable artifact set.",
            "safe_next_commands": [
                "rerun run-public-source-workflow with the same mission identity and --resume; no live/API/source/PDF action is required"
            ],
            "required_artifacts": [".artifact_state/GENESIS", ".artifact_state/CURRENT"],
        }
    return _review_next_action(
        base=base,
        output_dir=output_dir,
        packet_dir=packet_dir,
        review_queue=review_queue,
        reviewed_artifacts=reviewed_artifacts,
        coverage_artifacts=coverage_artifacts,
        final_artifacts=final_artifacts,
        anchor_dir=anchor_dir,
        local_evidence_root=local_evidence_root,
    )


def _base_next_action(
    *,
    gate: dict[str, Any],
    output_dir: Path,
    topic: str,
    seeds: list[str],
    public_discovery_confirmation: dict[str, Any],
    created_at: str,
    schema_version: str,
    nonclaims: list[str],
    public_discovery_max_metadata_records: int,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "created_at": created_at,
        "gate_id": gate["gate_id"],
        "approval_required": bool(gate.get("approval_required")),
        "safe_next_commands": safe_next_commands(
            gate,
            output_dir,
            topic,
            seeds,
            max_metadata_records=public_discovery_max_metadata_records,
        ),
        "blockers": [],
        "required_artifacts": [],
        "public_discovery_confirmation": public_discovery_confirmation,
        "forbidden_actions": [
            "do not run live/API/source/PDF/download/credential actions implicitly",
            "do not run public discovery before public_discovery_confirmation.confirmed is true",
            "do not treat reviewed sidecar discovery as final prose readiness",
            "do not hide reviewed-evidence blockers",
            "do not use credentials, private databases, paid model workers, hidden evaluator material, unbounded crawling, or outputs outside the mission directory without separate explicit approval",
        ],
        "what_is_not_concluded": nonclaims,
    }


def _gate_next_action(base: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "action_id": gate["gate_id"],
        "status": gate["status"],
        "mission_status": (
            "blocked_at_gate"
            if gate["approval_required"] or gate.get("implementation_or_artifact_blocker")
            else "ready_for_local_continuation"
        ),
        "summary": gate_summary(gate),
        "required_artifacts": [gate["required_artifact"]],
    }


def _review_next_action(
    *,
    base: dict[str, Any],
    output_dir: Path,
    packet_dir: Path,
    review_queue: dict[str, Any] | None,
    reviewed_artifacts: dict[str, dict[str, Any]],
    coverage_artifacts: dict[str, dict[str, Any]],
    final_artifacts: dict[str, dict[str, Any]],
    anchor_dir: Path | None,
    local_evidence_root: Path | None,
) -> dict[str, Any]:
    if not review_queue:
        return {
            **base,
            "action_id": "create_review_queue",
            "status": "blocked_missing_review_queue",
            "mission_status": "blocked_at_gate",
            "summary": "Create review_queue.json from the public-source packet before importing reviewed sidecars.",
            "required_artifacts": ["review_queue.json"],
        }

    review_queue_path = review_queue["path"]
    claims = reviewed_artifacts["reviewed_claims"]
    source_safety = reviewed_artifacts["reviewed_source_safety"]
    omissions = reviewed_artifacts["reviewed_omissions"]
    workflow_blockers = reviewed_artifacts["reviewed_workflow_blockers"]
    merged = reviewed_artifacts["reviewed_evidence"]
    coverage_complete = all(status.get("exists") is True for status in coverage_artifacts.values())

    if not coverage_complete:
        return {
            **base,
            "action_id": "repair_authoritative_coverage",
            "status": "blocked_missing_authoritative_coverage",
            "mission_status": "blocked_at_gate",
            "summary": "The selected immutable artifact set does not expose a complete validated coverage directory.",
            "required_artifacts": [status["required_path"] for status in coverage_artifacts.values()],
        }

    invalid_authorities = [
        {
            "family": family,
            "code": status.get("lineage_status"),
            "required_path": status["required_path"],
            "blockers": list(status.get("blockers") or []),
        }
        for family, status in (
            ("claim_candidate", claims),
            ("source_safety", source_safety),
            ("omission_risk", omissions),
        )
        if status.get("authority_invalid") is True
    ]
    if invalid_authorities:
        return {
            **base,
            "action_id": "invalid_reviewed_authority",
            "status": "blocked_invalid_reviewed_authority",
            "mission_status": "blocked_at_gate",
            "summary": "A selected immutable reviewed authority is missing, corrupt, stale, or otherwise invalid.",
            "safe_next_commands": [],
            "blockers": [
                blocker
                for authority in invalid_authorities
                for blocker in authority["blockers"]
            ],
            "required_artifacts": [authority["required_path"] for authority in invalid_authorities],
            "invalid_authorities": invalid_authorities,
        }

    pending_review = _pending_review_import_action(
        base=base,
        output_dir=output_dir,
        review_queue_path=review_queue_path,
        reviewed_artifacts=reviewed_artifacts,
    )
    if pending_review is not None:
        return pending_review
    if not merged["exists"]:
        command = (
            "ra survey merge-reviewed-evidence "
            f"--review-queue {review_queue_path} "
            f"--reviewed-claims {claims['required_path']} "
            f"--reviewed-source-safety {source_safety['required_path']} "
            f"--reviewed-omissions {omissions['required_path']} "
            f"--reviewed-workflow-blockers {workflow_blockers['required_path']} "
            f"--out {output_dir / 'reviewed_evidence'}"
        )
        return {
            **base,
            "action_id": "merge_reviewed_evidence",
            "status": "blocked_pending_reviewed_evidence_merge",
            "mission_status": "blocked_at_gate",
            "summary": "Merge reviewed sidecars and preserve blockers before any readiness decision.",
            "safe_next_commands": [command],
            "required_artifacts": [merged["required_path"]],
        }

    blockers = list(merged.get("blockers") or [])
    if merged.get("ready_for_reviewed_packet") is not True or blockers:
        return _review_blocker_action(
            base=base,
            summary="Resolve current reviewed-evidence outcome blockers; exact decision coverage alone is not packet or prose readiness.",
            blockers=blockers,
            review_queue_path=review_queue_path,
            output_dir=output_dir,
            reviewed_artifacts=reviewed_artifacts,
        )
    return _final_review_action(
        base=base,
        output_dir=output_dir,
        packet_dir=packet_dir,
        review_queue_path=review_queue_path,
        reviewed_evidence_path=merged["required_path"],
        final_artifacts=final_artifacts,
        anchor_dir=anchor_dir,
        local_evidence_root=local_evidence_root,
    )


def _pending_review_import_action(
    *,
    base: dict[str, Any],
    output_dir: Path,
    review_queue_path: str,
    reviewed_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    review_steps = (
        (
            "reviewed_claims",
            "import_reviewed_claims",
            "blocked_pending_reviewed_claims",
            "review claim_candidates, then run: ra survey import-claim-review",
            "reviewed_claim_decisions.json",
            "Import reviewed claim decisions linked to claim_candidate queue items.",
        ),
        (
            "reviewed_source_safety",
            "import_reviewed_source_safety",
            "blocked_pending_reviewed_source_safety",
            "ra survey import-source-safety-review",
            "reviewed_source_safety_decisions.json",
            "Import reviewed source-safety decisions; source availability alone is not safety evidence.",
        ),
        (
            "reviewed_omissions",
            "import_reviewed_omissions",
            "blocked_pending_reviewed_omissions",
            "ra survey import-omission-review",
            "reviewed_omission_decisions.json",
            "Import reviewed omission-risk decisions without claiming literature completeness.",
        ),
        (
            "reviewed_workflow_blockers",
            "import_reviewed_workflow_blockers",
            "blocked_pending_reviewed_workflow_blockers",
            "ra survey import-workflow-blocker-review",
            "reviewed_workflow_blocker_decisions.json",
            "Import one exact disposition for every workflow blocker; upstream-only blockers must remain open.",
        ),
    )
    for artifact_name, action_id, status, command, decisions_name, summary in review_steps:
        artifact = reviewed_artifacts[artifact_name]
        if artifact["exists"] and artifact.get("decision_coverage_complete") is True:
            continue
        command = (
            f"{command} --review-queue {review_queue_path} "
            f"--decisions <{decisions_name}> --out {output_dir / artifact_name}"
        )
        return {
            **base,
            "action_id": action_id,
            "status": status,
            "mission_status": "blocked_at_gate",
            "summary": summary,
            "safe_next_commands": [command],
            "required_artifacts": [artifact["required_path"]],
        }
    return None


def _review_blocker_action(
    *,
    base: dict[str, Any],
    summary: str,
    blockers: list[str],
    review_queue_path: str,
    output_dir: Path,
    reviewed_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    merged = reviewed_artifacts["reviewed_evidence"]
    return {
        **base,
        "action_id": "resolve_reviewed_evidence_blockers",
        "status": "blocked_by_reviewed_evidence_merge",
        "mission_status": "blocked_at_gate",
        "summary": summary,
        "safe_next_commands": reviewed_evidence_blocker_commands(
            blockers=blockers,
            review_queue_path=review_queue_path,
            output_dir=output_dir,
            claims_path=reviewed_artifacts["reviewed_claims"]["required_path"],
            source_safety_path=reviewed_artifacts["reviewed_source_safety"]["required_path"],
            omissions_path=reviewed_artifacts["reviewed_omissions"]["required_path"],
            workflow_blockers_path=reviewed_artifacts["reviewed_workflow_blockers"]["required_path"],
        ),
        "blockers": blockers,
        "required_artifacts": [merged["required_path"]],
    }


def _final_review_action(
    *,
    base: dict[str, Any],
    output_dir: Path,
    packet_dir: Path,
    review_queue_path: str,
    reviewed_evidence_path: str,
    final_artifacts: dict[str, dict[str, Any]],
    anchor_dir: Path | None,
    local_evidence_root: Path | None,
) -> dict[str, Any]:
    packet_status = final_artifacts["reviewed_final_packet"]
    hostile_status = final_artifacts["hostile_review_result"]
    readiness_status = final_artifacts["final_packet_readiness"]
    local_argument = (
        f" --local-evidence-root {local_evidence_root.absolute()}"
        if local_evidence_root is not None
        else ""
    )
    packet_command = (
        "ra survey compose-reviewed-final-packet "
        f"--mission-root {output_dir} "
        f"--review-queue {review_queue_path} "
        f"--packet-dir {packet_dir} "
        f"--anchor-dir {anchor_dir}"
        f"{local_argument} "
        f"--out {output_dir / 'reviewed_final_packet'}"
    )
    hostile_command = (
        "ra survey hostile-review "
        f"--reviewed-final-packet {packet_status['required_path']} "
        f"--mission-root {output_dir} "
        f"--review-queue {review_queue_path} "
        f"--packet-dir {packet_dir} "
        f"--anchor-dir {anchor_dir}"
        f"{local_argument} "
        f"--out {output_dir / 'hostile_review'}"
    )
    if not packet_status["exists"]:
        if packet_status["present"]:
            return {
                **base,
                "action_id": "repair_reviewed_final_packet",
                "status": "blocked_invalid_reviewed_final_packet",
                "mission_status": "blocked_at_gate",
                "summary": "The reviewed final packet exists but does not replay from current external mission authority.",
                "safe_next_commands": [f"{packet_command} --force"],
                "blockers": list(packet_status.get("blockers") or []),
                "required_artifacts": [packet_status["required_path"]],
            }
        return {
            **base,
            "action_id": "compose_reviewed_final_packet",
            "status": "ready_for_reviewed_packet_composition",
            "mission_status": "ready_for_local_continuation",
            "summary": "Exact reviewed evidence is clear; compose the immutable reviewed final packet before hostile review or prose readiness.",
            "safe_next_commands": [packet_command],
            "required_artifacts": [reviewed_evidence_path, packet_status["required_path"]],
        }
    if hostile_status["exists"]:
        safe_commands: list[str] = []
        summary = "The authoritative hostile result is current; hand off its bounded state to the Phase 5 executing supervisor."
        if not readiness_status["exists"]:
            safe_commands.append(
                "regenerate final_packet_readiness.json from the validated hostile result; this view is not authority"
            )
            summary += " The optional readiness view is missing or stale and may be regenerated without changing authority."
        return {
            **base,
            "action_id": "phase5_executing_supervisor_handoff",
            "status": "ready_for_phase5_supervisor",
            "mission_status": "ready_for_local_continuation",
            "summary": summary,
            "safe_next_commands": safe_commands,
            "ready_for_hostile_review": True,
            "ready_for_prose": hostile_status["ready_for_prose"],
            "readiness_classification": hostile_status.get("readiness_classification"),
            "blockers": list(hostile_status.get("blockers") or []),
            "required_artifacts": [packet_status["required_path"], hostile_status["required_path"]],
        }
    if hostile_status["present"]:
        return {
            **base,
            "action_id": "repair_hostile_review_result",
            "status": "blocked_invalid_hostile_review_result",
            "mission_status": "blocked_at_gate",
            "summary": "The hostile result exists but does not replay from current external mission authority.",
            "safe_next_commands": [f"{hostile_command} --force"],
            "blockers": list(hostile_status.get("blockers") or []),
            "required_artifacts": [hostile_status["required_path"]],
        }
    command = f"{hostile_command} --force" if readiness_status["present"] else hostile_command
    return {
        **base,
        "action_id": "run_hostile_review",
        "status": "ready_for_hostile_review",
        "mission_status": "ready_for_local_continuation",
        "summary": "The reviewed final packet is current; run packet-only hostile review before any prose-readiness claim.",
        "safe_next_commands": [command],
        "ready_for_hostile_review": True,
        "ready_for_prose": False,
        "required_artifacts": [packet_status["required_path"], hostile_status["required_path"]],
    }


def gate_summary(gate: dict[str, Any]) -> str:
    if gate["gate_id"] == "public_metadata":
        return "Public discovery is not confirmed yet. Ask the user once whether RA should search public web/archive sources, or provide a manifest-committed metadata bundle."
    if gate["gate_id"] == "public_metadata_resolution":
        return "The committed V2 metadata bundle has an unresolved, ambiguous, invalid, or conflicting seed; inspect identity_resolution.json before any source intake."
    if gate["gate_id"] == "source_intake":
        if gate.get("covered_by_public_discovery"):
            return (
                "Public source/status lookup is covered by the mission public-discovery confirmation, "
                "but this workflow still needs phase4_source_intake_status.json from a bounded source-status implementation or existing artifact."
            )
        return "Source-intake status is missing; prepare an exact source_fetch approval packet or provide the approved artifact."
    if gate["gate_id"] == "source_anchors":
        return "Source anchors are missing; run local anchor extraction from already-approved structured source records."
    if gate["gate_id"] == "public_source_packet":
        return "The public-source packet is missing; compose it from local metadata, source-status, and anchor artifacts."
    return "Continue the supervised workflow from the current gate."


def reviewed_evidence_blocker_commands(
    *,
    blockers: list[str],
    review_queue_path: str,
    output_dir: Path,
    claims_path: str,
    source_safety_path: str,
    omissions_path: str,
    workflow_blockers_path: str,
) -> list[str]:
    commands = []
    if any("omission" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_omission_risks.json so open omission risks are inspected, expanded, or explicitly closed for scope"
        )
    if any("source-safety" in blocker.lower() or "checked_clear" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_source_safety.json so every required source-safety row has reviewed checked_clear, blocked, or quarantine evidence"
        )
    if any("claim" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_claims.json so every supported claim row has reviewed technical support and provenance"
        )
    if any("workflow" in blocker.lower() for blocker in blockers):
        commands.append(
            "refresh reviewed_workflow_blockers.json with exact current evidence scopes or keep upstream-only blockers open"
        )
    commands.append(
        "ra survey merge-reviewed-evidence "
        f"--review-queue {review_queue_path} "
        f"--reviewed-claims {claims_path} "
        f"--reviewed-source-safety {source_safety_path} "
        f"--reviewed-omissions {omissions_path} "
        f"--reviewed-workflow-blockers {workflow_blockers_path} "
        f"--out {output_dir / 'reviewed_evidence'} --force"
    )
    return commands


def safe_next_commands(
    gate: dict[str, Any],
    output_dir: Path,
    topic: str,
    seeds: list[str],
    *,
    max_metadata_records: int,
) -> list[str]:
    quoted_topic = json.dumps(topic)
    first_seed = seeds[0] if seeds else "<seed>"
    if gate["gate_id"] == "public_metadata":
        return [
            (
                "ask once: Do you want RA to search public web/archive sources for this idea? "
                "If yes, rerun this workflow with --confirm-public-discovery. "
                f"Planned bounded metadata command: ra survey build --topic {quoted_topic} --seed {first_seed} "
                f"--out {output_dir / 'public_metadata'} --mode public-metadata "
                f"--public-metadata-provider arxiv --max-records {max_metadata_records}"
            )
        ]
    if gate["gate_id"] == "public_metadata_resolution":
        return [
            "inspect identity_resolution.json and preserve every unresolved, ambiguous, invalid, or conflicting seed choice; do not invoke source intake"
        ]
    if gate["gate_id"] == "source_intake":
        if gate.get("covered_by_public_discovery"):
            return [
                "continue within the recorded public-discovery scope by providing or implementing bounded phase4_source_intake_status.json; do not request a second ordinary public source/archive approval"
            ]
        return ["prepare an exact source_fetch approval packet from the public metadata candidate ledger"]
    if gate["gate_id"] == "source_anchors":
        return ["run ra survey anchors for the approved local structured source paper ids"]
    if gate["gate_id"] == "public_source_packet":
        return ["run ra survey packet with the metadata, source-status, and anchor directories"]
    return [
        "review claim_candidates and map only reviewed claims to source anchors",
        "run approved retraction/version/erratum checks before marking safety checked_clear",
        "resolve omission risks or record explicit omission reasons",
    ]
