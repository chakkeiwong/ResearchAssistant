from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research_assistant.survey.artifact_lineage import (
    COVERAGE_FILES,
    ArtifactStateManager,
    semantic_item,
    workflow_blocker_source_id,
)
from research_assistant.survey.claim_review import (
    _apply_claim_constraints,
    _validate_decision as _validate_claim_decision,
)
from research_assistant.survey.mission_state import MissionStateError, MissionStateManager, canonical_json_bytes
from research_assistant.survey.review_decisions import (
    COMMON_SIDECAR_KEYS,
    REVIEW_DECISIONS_SCHEMA,
    atomic_write_json,
    common_sidecar_fields,
    load_bound_decision_envelope,
    load_selected_decision_context,
    normalize_optional_text,
    normalize_required_text,
    normalize_reviewed_at,
    validate_exact_decisions,
    validate_sidecar_binding,
)
from research_assistant.survey.workflow_blocker_review import (
    _validate_decision as _validate_workflow_decision,
)


MISSION_ID = "22222222-2222-4222-8222-222222222222"
NONCE_1 = "202122232425262728292a2b2c2d2e2f"
NONCE_2 = "303132333435363738393a3b3c3d3e3f"


def _selected_queue(
    tmp_path: Path,
    *,
    claim_count: int = 1,
    include_unknown_type: bool = False,
) -> tuple[Path, dict]:
    root = tmp_path / "mission"
    root.mkdir()
    mission = MissionStateManager(
        output_dir=root,
        topic="Phase 3 exact decision fixture",
        seeds=["arxiv:0000.00002"],
        confirm_public_discovery=False,
        resume=False,
        force=False,
        now=lambda: "2026-07-11T00:00:00+00:00",
        nonce_factory=lambda: NONCE_1,
        mission_id_factory=lambda: MISSION_ID,
    )
    mission.begin()
    committed = mission.commit(
        {
            "status": "ready_for_local_continuation",
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:00:00+00:00",
            "topic": "Phase 3 exact decision fixture",
            "seeds": ["arxiv:0000.00002"],
            "output_dir": str(root),
        },
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "fixture",
            "mission_status": "ready_for_local_continuation",
            "action_id": "fixture",
        },
    )
    assert committed.current_pointer is not None

    packet = root / "packet"
    packet.mkdir()
    for name, payload in {
        "candidate_ledger.json": {"schema_version": "candidate-v1", "included": []},
        "citation_map.json": {"schema_version": "citation-v1", "frontiers": []},
        "paper_classifications.json": {"schema_version": "class-v1", "classifications": []},
        "omission_risk.json": {"schema_version": "omission-v1", "risks": []},
        "claim_support.json": {"schema_version": "claims-v1", "claim_candidates": []},
        "source_safety_status.json": {"schema_version": "safety-v1", "rows": []},
        "build_manifest.json": {"schema_version": "packet-v1", "workflow_state": {"blocked_reasons": []}},
    }.items():
        (packet / name).write_bytes(canonical_json_bytes(payload))
    coverage = {
        name: {
            "schema_version": f"fixture-{name}-v1",
            "status": "fixture",
            "rows": [],
            "what_is_not_concluded": ["literature completeness"],
        }
        for name in COVERAGE_FILES
    }
    items = [
        semantic_item(
            queue_type="claim_candidate",
            source_id=f"claim-{index}",
            semantic_fields={
                "priority": "high",
                "status": "review_required",
                "claim_support_allowed": False,
                "anchor_ids": [f"anchor-{index}"],
                "paper_ids": [f"paper-{index}"],
            },
        )
        for index in range(claim_count)
    ]
    if include_unknown_type:
        items.append(semantic_item(
            queue_type="unrecognized_review_type",
            source_id="unknown-1",
            semantic_fields={
                "priority": "high",
                "status": "review_required",
            },
        ))
    items.sort(key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]))
    by_type = {"claim_candidate": claim_count}
    if include_unknown_type:
        by_type["unrecognized_review_type"] = 1
    queue = {
        "status": "review_required",
        "topic": "Phase 3 exact decision fixture",
        "items": items,
        "queue_counts": {
            "total": len(items),
            "by_type": by_type,
            "by_priority": {"high": len(items)},
            "by_status": {"review_required": len(items)},
        },
        "allowed_item_statuses": ["review_required"],
        "forbidden_promotions": ["review is not prose readiness"],
        "what_is_not_concluded": ["scientific correctness"],
    }
    selected = ArtifactStateManager(
        mission_root=root,
        mission_id=committed.contract["mission_id"],
        mission_fingerprint=committed.contract["mission_fingerprint"],
        mission_anchor_generation_id=committed.current_pointer["generation_id"],
        nonce_factory=lambda: NONCE_2,
    ).compose_and_select(
        packet_dir=packet,
        coverage_payloads=coverage,
        review_queue_payload=queue,
    )
    payload = json.loads(selected.review_queue_path.read_text())
    return selected.review_queue_path, payload


def _selected_four_type_queue(
    tmp_path: Path,
    *,
    workflow_attack: str | None = None,
) -> tuple[Path, dict]:
    root = tmp_path / "mission"
    root.mkdir()
    mission = MissionStateManager(
        output_dir=root,
        topic="Phase 3 four-type coverage matrix",
        seeds=["arxiv:0000.00003"],
        confirm_public_discovery=False,
        resume=False,
        force=False,
        now=lambda: "2026-07-11T00:00:00+00:00",
        nonce_factory=lambda: NONCE_1,
        mission_id_factory=lambda: MISSION_ID,
    )
    mission.begin()
    committed = mission.commit(
        {
            "status": "ready_for_local_continuation",
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:00:00+00:00",
            "topic": "Phase 3 four-type coverage matrix",
            "seeds": ["arxiv:0000.00003"],
            "output_dir": str(root),
        },
        {
            "schema_version": "ra-survey-public-source-next-action-v1",
            "status": "fixture",
            "mission_status": "ready_for_local_continuation",
            "action_id": "fixture",
        },
    )
    assert committed.current_pointer is not None
    packet = root / "packet"
    packet.mkdir()
    for name in [
        "candidate_ledger.json",
        "citation_map.json",
        "paper_classifications.json",
        "omission_risk.json",
        "claim_support.json",
        "source_safety_status.json",
        "build_manifest.json",
    ]:
        (packet / name).write_bytes(canonical_json_bytes({"schema_version": "fixture-v1", "rows": []}))
    coverage = {
        name: {
            "schema_version": f"fixture-{name}-v1",
            "status": "fixture",
            "rows": [],
            "what_is_not_concluded": ["literature completeness"],
        }
        for name in COVERAGE_FILES
    }
    claim_count = 2 if workflow_attack == "subset" else 1
    review_items = [
        semantic_item(
            queue_type="claim_candidate",
            source_id=f"claim-{index}",
            semantic_fields={"priority": "high", "status": "review_required"},
        )
        for index in range(claim_count)
    ]
    review_items.extend([
        semantic_item(
            queue_type="source_safety",
            source_id="source-safety-source",
            semantic_fields={"priority": "high", "status": "review_required"},
        ),
        semantic_item(
            queue_type="omission_risk",
            source_id="omission-source",
            semantic_fields={"priority": "high", "status": "review_required"},
        ),
    ])
    reason = "no reviewed supported technical claim rows are present"
    claim_ids = sorted(
        item["item_id"] for item in review_items
        if item["queue_type"] == "claim_candidate"
    )
    resolution_class = "claim_review"
    evidence_type = "claim_candidate"
    evidence_ids = claim_ids
    if workflow_attack == "subset":
        evidence_ids = claim_ids[:1]
    elif workflow_attack == "wrong_class_type":
        resolution_class = "omission_review"
        evidence_type = "omission_risk"
        evidence_ids = sorted(
            item["item_id"] for item in review_items
            if item["queue_type"] == "omission_risk"
        )
    workflow_item = semantic_item(
        queue_type="workflow_blocker",
        source_id=workflow_blocker_source_id(reason),
        semantic_fields={
            "priority": "high",
            "status": "blocked_pending_evidence",
            "reason": reason,
            "resolution_class": resolution_class,
            "required_evidence_queue_type": evidence_type,
            "required_evidence_queue_item_ids": evidence_ids,
            "ready_for_prose": False,
        },
    )
    items = [*review_items, workflow_item]
    items.sort(key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]))
    by_type = {
        "claim_candidate": claim_count,
        "source_safety": 1,
        "omission_risk": 1,
        "workflow_blocker": 1,
    }
    queue = {
        "status": "review_required",
        "topic": "Phase 3 four-type coverage matrix",
        "items": items,
        "queue_counts": {
            "total": len(items),
            "by_type": by_type,
            "by_priority": {"high": len(items)},
            "by_status": {
                "blocked_pending_evidence": 1,
                "review_required": len(review_items),
            },
        },
        "allowed_item_statuses": ["review_required"],
        "forbidden_promotions": ["review is not prose readiness"],
        "what_is_not_concluded": ["scientific correctness"],
    }
    selected = ArtifactStateManager(
        mission_root=root,
        mission_id=committed.contract["mission_id"],
        mission_fingerprint=committed.contract["mission_fingerprint"],
        mission_anchor_generation_id=committed.current_pointer["generation_id"],
        nonce_factory=lambda: NONCE_2,
    ).compose_and_select(
        packet_dir=packet,
        coverage_payloads=coverage,
        review_queue_payload=queue,
    )
    return selected.review_queue_path, json.loads(selected.review_queue_path.read_text())


def _envelope(queue_path: Path, queue: dict, decisions: list[dict]) -> dict:
    return {
        "schema_version": REVIEW_DECISIONS_SCHEMA,
        "decision_type": "claim_candidate",
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "artifact_set_id": queue["artifact_set_id"],
        "queue_semantic_sha256": queue["queue_semantic_sha256"],
        "review_queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
        "decisions": decisions,
    }


def _validator(row, item, index):
    if not isinstance(row, dict):
        return {}, [f"row {index} is not an object"]
    if item is None:
        return {}, []
    return {
        "queue_item_id": row["queue_item_id"],
        "reviewer": normalize_required_text(row.get("reviewer"), field="reviewer"),
        "reviewed_at": normalize_reviewed_at(row.get("reviewed_at")),
    }, []


def test_bound_envelope_and_exact_coverage_accept_current_complete_set(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    item_id = queue["items"][0]["item_id"]
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(_envelope(queue_path, queue, [{
        "queue_item_id": item_id,
        "reviewer": " Local Reviewer ",
        "reviewed_at": "2026-07-11T08:00:00+08:00",
    }])))

    context, _, rows, _ = load_bound_decision_envelope(
        review_queue_path=queue_path,
        decisions_path=decisions,
        decision_type="claim_candidate",
    )
    result = validate_exact_decisions(context=context, rows=rows, validator=_validator)

    assert result.complete is True
    assert result.required_item_ids == [item_id]
    assert result.accepted_item_ids == [item_id]
    assert result.accepted[0]["reviewer"] == "Local Reviewer"
    assert result.accepted[0]["reviewed_at"] == "2026-07-11T00:00:00Z"
    assert len(result.accepted[0]["decision_sha256"]) == 64


def test_selected_queue_with_unknown_fifth_type_fails_closed(tmp_path: Path) -> None:
    queue_path, _ = _selected_queue(tmp_path, include_unknown_type=True)

    with pytest.raises(MissionStateError) as error:
        load_selected_decision_context(
            review_queue_path=queue_path,
            decision_type="claim_candidate",
        )

    assert error.value.code == "unsupported_queue_type"


@pytest.mark.parametrize("attack", ["subset", "wrong_class_type"])
def test_selected_queue_rejects_non_normative_workflow_scope(
    tmp_path: Path,
    attack: str,
) -> None:
    queue_path, _ = _selected_four_type_queue(tmp_path, workflow_attack=attack)

    with pytest.raises(MissionStateError) as error:
        load_selected_decision_context(
            review_queue_path=queue_path,
            decision_type="workflow_blocker",
        )

    assert error.value.code == "invalid_workflow_queue_semantics"


def test_duplicate_masks_missing_is_not_exact_coverage(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path, claim_count=2)
    first_id = queue["items"][0]["item_id"]
    decisions = tmp_path / "decisions.json"
    row = {"queue_item_id": first_id, "reviewer": "reviewer", "reviewed_at": "2026-07-11T00:00:00Z"}
    decisions.write_text(json.dumps(_envelope(queue_path, queue, [row, row])))
    context, _, rows, _ = load_bound_decision_envelope(
        review_queue_path=queue_path,
        decisions_path=decisions,
        decision_type="claim_candidate",
    )

    result = validate_exact_decisions(context=context, rows=rows, validator=_validator)

    assert result.complete is False
    assert any("missing queue_item_ids" in reason for reason in result.coverage_errors)
    assert any("duplicate queue_item_ids" in reason for reason in result.coverage_errors)
    assert len(result.rejected) == 2


@pytest.mark.parametrize(
    "decision_type",
    ["claim_candidate", "source_safety", "omission_risk", "workflow_blocker"],
)
@pytest.mark.parametrize(
    "attack",
    ["missing", "duplicate", "unknown", "wrong_type", "conflicting", "non_object", "surplus"],
)
def test_exact_coverage_attack_matrix_fails_for_every_type(
    tmp_path: Path,
    decision_type: str,
    attack: str,
) -> None:
    queue_path, queue = _selected_four_type_queue(tmp_path)
    context = load_selected_decision_context(
        review_queue_path=queue_path,
        decision_type=decision_type,
    )
    required_id = context.required_item_ids[0]
    other_id = next(
        item["item_id"] for item in queue["items"]
        if item["queue_type"] != decision_type
    )
    valid = {
        "queue_item_id": required_id,
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-11T00:00:00Z",
    }
    if attack == "missing":
        rows = []
    elif attack == "duplicate":
        rows = [valid, dict(valid)]
    elif attack == "unknown":
        rows = [{**valid, "queue_item_id": "unknown-" + "f" * 24}]
    elif attack == "wrong_type":
        rows = [{**valid, "queue_item_id": other_id}]
    elif attack == "conflicting":
        rows = [valid, {**valid, "reviewer": "reviewer-b"}]
    elif attack == "non_object":
        rows = ["not-an-object"]
    else:
        rows = [valid, {**valid, "queue_item_id": "surplus-" + "e" * 24}]

    result = validate_exact_decisions(context=context, rows=rows, validator=_validator)

    assert result.complete is False
    assert result.coverage_errors or result.rejected
    assert result.accepted_item_ids != result.required_item_ids or result.rejected or result.coverage_errors


@pytest.mark.parametrize("field,value,code", [
    ("artifact_set_id", "0" * 64, "stale_lineage"),
    ("mission_id", "33333333-3333-4333-8333-333333333333", "foreign_lineage"),
    ("mission_fingerprint", "0" * 64, "foreign_lineage"),
    ("queue_semantic_sha256", "0" * 64, "stale_lineage"),
    ("review_queue_sha256", "0" * 64, "stale_lineage"),
    ("decision_type", "source_safety", "wrong_decision_type"),
])
def test_bound_envelope_rejects_wrong_identity_or_type(
    tmp_path: Path,
    field: str,
    value: str,
    code: str,
) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    payload = _envelope(queue_path, queue, [])
    payload[field] = value
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload))

    with pytest.raises(MissionStateError) as error:
        load_bound_decision_envelope(
            review_queue_path=queue_path,
            decisions_path=decisions,
            decision_type="claim_candidate",
        )
    assert error.value.code == code


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("missing_schema", "invalid_schema"),
        ("wrong_schema", "invalid_decision_schema"),
        ("missing_field", "invalid_schema"),
    ],
)
def test_bound_envelope_rejects_missing_or_wrong_schema(
    tmp_path: Path,
    mutation: str,
    code: str,
) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    payload = _envelope(queue_path, queue, [])
    if mutation == "missing_schema":
        payload.pop("schema_version")
    elif mutation == "wrong_schema":
        payload["schema_version"] = "ra-survey-review-decisions-v999"
    else:
        payload.pop("review_queue_sha256")
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload))

    with pytest.raises(MissionStateError) as error:
        load_bound_decision_envelope(
            review_queue_path=queue_path,
            decisions_path=decisions,
            decision_type="claim_candidate",
        )
    assert error.value.code == code


def test_decision_input_rejects_malformed_json_and_nonregular_paths(tmp_path: Path) -> None:
    queue_path, _ = _selected_queue(tmp_path)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{")

    with pytest.raises(MissionStateError) as malformed_error:
        load_bound_decision_envelope(
            review_queue_path=queue_path,
            decisions_path=malformed,
            decision_type="claim_candidate",
        )
    assert malformed_error.value.code == "invalid_json"

    nonregular = tmp_path / "decision-directory"
    nonregular.mkdir()
    with pytest.raises(MissionStateError) as nonregular_error:
        load_bound_decision_envelope(
            review_queue_path=queue_path,
            decisions_path=nonregular,
            decision_type="claim_candidate",
        )
    assert nonregular_error.value.code == "unsafe_review_artifact"


def test_sidecar_input_rejects_nonregular_path(tmp_path: Path) -> None:
    queue_path, _ = _selected_queue(tmp_path)
    context = load_selected_decision_context(
        review_queue_path=queue_path,
        decision_type="claim_candidate",
    )
    nonregular = tmp_path / "sidecar-directory"
    nonregular.mkdir()

    with pytest.raises(MissionStateError) as error:
        validate_sidecar_binding(
            path=nonregular,
            context=context,
            expected_schema="test-reviewed-claims-v2",
            expected_keys=set(),
            decisions_field="claims",
            rejected_field="rejected_claims",
            validator=_validator,
            expected_fields=lambda _: {},
        )
    assert error.value.code == "unsafe_review_artifact"


def test_text_and_time_normalization_reject_control_naive_and_nonstring_values() -> None:
    with pytest.raises(MissionStateError, match="control"):
        normalize_required_text("reviewer\x00name", field="reviewer")
    with pytest.raises(MissionStateError, match="timezone"):
        normalize_reviewed_at("2026-07-11T00:00:00")
    with pytest.raises(MissionStateError, match="string"):
        normalize_optional_text([], field="note")


def _claim_decision_row(item: dict, *, claim_id: str) -> dict:
    return {
        "queue_item_id": item["item_id"],
        "claim_id": claim_id,
        "claim_text": "A locally reviewed technical claim.",
        "paper_ids": list(item["paper_ids"]),
        "anchor_ids": list(item["anchor_ids"]),
        "review_status": "human_reviewed_passed",
        "support_class": "primary_technical_support",
        "reviewer": "local-reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
        "evidence_note": "Checked against the selected local anchor.",
    }


def test_claim_constraint_rejects_duplicate_claim_ids_across_exact_queue_rows(tmp_path: Path) -> None:
    queue_path, _ = _selected_queue(tmp_path, claim_count=2)
    context = load_selected_decision_context(
        review_queue_path=queue_path,
        decision_type="claim_candidate",
    )
    rows = [
        _claim_decision_row(item, claim_id="duplicate-claim")
        for item in context.required_items.values()
    ]

    result = _apply_claim_constraints(
        validate_exact_decisions(
            context=context,
            rows=rows,
            validator=_validate_claim_decision,
        )
    )

    assert result.complete is False
    assert result.accepted_item_ids == result.required_item_ids
    assert result.coverage_errors == ["duplicate claim_ids: duplicate-claim"]


@pytest.mark.parametrize("support_class", ["project_derivation", "implementation_evidence"])
def test_claim_validator_rejects_malformed_local_artifact_hash(
    tmp_path: Path,
    support_class: str,
) -> None:
    queue_path, _ = _selected_queue(tmp_path)
    context = load_selected_decision_context(
        review_queue_path=queue_path,
        decision_type="claim_candidate",
    )
    item = next(iter(context.required_items.values()))
    row = {
        "queue_item_id": item["item_id"],
        "claim_id": "local-evidence-claim",
        "claim_text": "A claim tied to a local project artifact.",
        "review_status": "human_reviewed_passed",
        "support_class": support_class,
        "reviewer": "local-reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
        "evidence_note": "Local evidence classification fixture.",
        "local_artifact": "docs/local-evidence.json",
        "local_artifact_sha256": "NOT-A-SHA256",
    }
    if support_class == "project_derivation":
        row.update({
            "derivation_id": "derivation-1",
            "derivation_note": "A checked local derivation would be required.",
        })

    _, reasons = _validate_claim_decision(row, item, 1)

    assert "local_artifact_sha256 must be 64 lowercase hex characters" in reasons


@pytest.mark.parametrize(
    "field,value,reason_fragment",
    [
        ("claim_text", "     ", "claim_text must not be empty"),
        ("claim_text", "invalid\x00claim", "claim_text must not contain control characters"),
        ("reviewer", "     ", "reviewer must not be empty"),
        ("reviewed_at", "not-an-instant", "reviewed_at must be an ISO-8601 instant"),
    ],
)
def test_claim_validator_rejects_invalid_text_and_timestamp_fields(
    tmp_path: Path,
    field: str,
    value: str,
    reason_fragment: str,
) -> None:
    queue_path, _ = _selected_queue(tmp_path)
    context = load_selected_decision_context(
        review_queue_path=queue_path,
        decision_type="claim_candidate",
    )
    item = next(iter(context.required_items.values()))
    row = _claim_decision_row(item, claim_id="invalid-field-claim")
    row[field] = value

    _, reasons = _validate_claim_decision(row, item, 1)

    assert reason_fragment in reasons


def test_workflow_validator_rejects_false_resolution_of_upstream_only_blocker() -> None:
    item = {
        "item_id": "workflow-blocker-" + "a" * 24,
        "resolution_class": "upstream_repair_required",
        "required_evidence_queue_type": None,
        "required_evidence_queue_item_ids": [],
    }
    row = {
        "queue_item_id": item["item_id"],
        "disposition": "resolved_by_reviewed_evidence",
        "evidence_queue_item_ids": ["claim-candidate-" + "b" * 24],
        "rationale": "A review decision cannot repair an upstream artifact.",
        "reviewer": "local-reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
    }

    _, reasons = _validate_workflow_decision(row, item, 1)

    assert "upstream_repair_required blocker cannot be resolved by review evidence" in reasons
    assert "evidence_queue_item_ids must equal the workflow blocker's exact required evidence scope" in reasons


def test_decision_input_symlink_is_rejected(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    real = tmp_path / "real.json"
    real.write_text(json.dumps(_envelope(queue_path, queue, [])))
    alias = tmp_path / "alias.json"
    alias.symlink_to(real)

    with pytest.raises(MissionStateError) as error:
        load_bound_decision_envelope(
            review_queue_path=queue_path,
            decisions_path=alias,
            decision_type="claim_candidate",
        )
    assert error.value.code == "unsafe_review_artifact"


def test_atomic_sidecar_is_canonical_and_binding_revalidates(tmp_path: Path) -> None:
    queue_path, queue = _selected_queue(tmp_path)
    item_id = queue["items"][0]["item_id"]
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(_envelope(queue_path, queue, [{
        "queue_item_id": item_id,
        "reviewer": "reviewer",
        "reviewed_at": "2026-07-11T00:00:00Z",
    }])))
    context, _, rows, decisions_raw = load_bound_decision_envelope(
        review_queue_path=queue_path,
        decisions_path=decisions,
        decision_type="claim_candidate",
    )
    result = validate_exact_decisions(context=context, rows=rows, validator=_validator)
    schema = "test-reviewed-claims-v2"
    payload = {
        "schema_version": schema,
        "status": "reviewed_claims_complete",
        **common_sidecar_fields(
            context=context,
            decisions_path=decisions,
            decisions_raw=decisions_raw,
            result=result,
            created_at="2026-07-11T00:00:00Z",
        ),
        "claims": result.accepted,
        "rejected_claims": result.rejected,
        "coverage_errors": result.coverage_errors,
        "what_is_not_concluded": ["scientific correctness"],
    }
    output = tmp_path / "out" / "reviewed_claims.json"
    atomic_write_json(output, payload)

    assert output.read_bytes().endswith(b"\n")
    validated, validated_raw = validate_sidecar_binding(
        path=output,
        context=context,
        expected_schema=schema,
        expected_keys=COMMON_SIDECAR_KEYS | {"claims", "rejected_claims", "coverage_errors"},
        decisions_field="claims",
        rejected_field="rejected_claims",
        validator=_validator,
        expected_fields=lambda replayed: {
            "status": "reviewed_claims_complete" if replayed.complete else "blocked_invalid_claim_decisions",
            "what_is_not_concluded": ["scientific correctness"],
        },
    )
    assert validated["decision_coverage_complete"] is True
    assert validated_raw == output.read_bytes()
    assert list((tmp_path / "out").glob(".*.tmp")) == []
