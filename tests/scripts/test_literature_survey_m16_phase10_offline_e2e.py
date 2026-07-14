from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath

import pytest

from research_assistant.survey.mission_state import canonical_json_bytes
from scripts.literature_survey_m16_phase10_offline_e2e import (
    NEGATIVE_CASE_IDS,
    NONCLAIMS,
    SCHEMA,
    _tripwired,
    run_validation,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_CANONICAL_PHASE10_SUFFIX = PurePosixPath(
    "docs/validation/literature_survey_m16_phase10_2026-07-13"
)
_REVIEWED_ARTIFACT_PATHS = {
    "reviewed_claims": ("cd-", "reviewed_claims.json"),
    "reviewed_source_safety": ("sd-", "reviewed_source_safety.json"),
    "reviewed_omissions": ("od-", "reviewed_omission_risks.json"),
}


def _rebase_frozen_required_path(required_path: object, output: Path, artifact: str) -> Path:
    frozen = PurePosixPath(str(required_path))
    assert frozen.is_absolute()
    marker = _CANONICAL_PHASE10_SUFFIX.parts
    output_parts = PurePosixPath(output.resolve()).parts
    if frozen.parts[:len(output_parts)] == output_parts:
        relative = frozen.parts[len(output_parts):]
    else:
        matches = [
            index
            for index in range(len(frozen.parts) - len(marker) + 1)
            if frozen.parts[index:index + len(marker)] == marker
        ]
        assert len(matches) == 1
        relative = frozen.parts[matches[0] + len(marker):]
    id_prefix, filename = _REVIEWED_ARTIFACT_PATHS[artifact]
    assert relative[:4] == ("positive", "mission", artifact, "decision_sets")
    assert len(relative) == 6 and relative[-1] == filename
    decision_id = relative[-2]
    assert decision_id.startswith(id_prefix)
    assert len(decision_id) == len(id_prefix) + 64
    int(decision_id[len(id_prefix):], 16)
    return output.joinpath(*relative)


def _selected_ids_from_cli(cli_record: dict[str, object], output: Path) -> dict[str, object]:
    payload = cli_record["payload"]
    reviewed = payload["reviewed_artifacts"]
    claims_path = _rebase_frozen_required_path(
        reviewed["reviewed_claims"]["required_path"], output, "reviewed_claims"
    )
    source_path = _rebase_frozen_required_path(
        reviewed["reviewed_source_safety"]["required_path"], output, "reviewed_source_safety"
    )
    omissions_path = _rebase_frozen_required_path(
        reviewed["reviewed_omissions"]["required_path"], output, "reviewed_omissions"
    )
    source_payload = json.loads(source_path.read_text())
    return {
        "artifact_set_id": payload["artifact_state"]["artifact_set_id"],
        "claim_decision_set_id": claims_path.parent.name,
        "source_observation_set_id": source_payload["observation_set_id"],
        "source_decision_set_id": source_path.parent.name,
        "omission_decision_set_id": omissions_path.parent.name,
    }


def _validate_persisted_candidate(output: Path) -> None:
    summary = json.loads((output / "e2e_summary.json").read_text())
    assert summary["schema_version"] == SCHEMA
    assert summary["status"] == "passed"
    assert summary["case_ids"] == ["positive", *NEGATIVE_CASE_IDS]
    assert summary["persistent_positive_count"] == 1
    assert summary["persistent_negative_count"] == 10
    assert summary["forbidden_call_count"] == 0
    assert summary["fixture_only"] is True
    assert summary["authenticated_human_review"] is False
    assert summary["what_is_not_concluded"] == NONCLAIMS

    static_audit = json.loads((output / summary["static_audit"]).read_text())
    assert static_audit["status"] == "passed"
    assert static_audit["scan_kind"] == "byte_substring_scan"
    assert bytes.fromhex(static_audit["forbidden_byte_string_hex"]) == b"/tmp/m16-phase10-"
    assert static_audit["matching_relative_paths"] == []
    assert static_audit["matching_file_count"] == 0

    inventory_ref = summary["artifact_inventory"]
    inventory_path = output / inventory_ref["path"]
    assert _sha(inventory_path) == inventory_ref["sha256"]
    inventory = json.loads(inventory_path.read_text())
    assert inventory["artifact_count"] == inventory_ref["artifact_count"]
    assert inventory["tree_sha256"] == inventory_ref["tree_sha256"]
    assert inventory["artifact_count"] == len(inventory["artifacts"])
    inventory_paths = [row["path"] for row in inventory["artifacts"]]
    assert len(inventory_paths) == len(set(inventory_paths))
    expected_paths = {
        str(path.relative_to(output)): "symlink" if path.is_symlink() else "file"
        for root in (output / "positive", output / "negative")
        for path in root.rglob("*")
        if path.is_symlink() or path.is_file()
    }
    expected_paths[summary["static_audit"]] = "file"
    assert {row["path"]: row["kind"] for row in inventory["artifacts"]} == dict(sorted(expected_paths.items()))
    for row in inventory["artifacts"]:
        path = output / row["path"]
        if row["kind"] == "symlink":
            assert set(row) == {"path", "kind", "target"}
            assert path.is_symlink()
            assert os.readlink(path) == row["target"]
        else:
            assert set(row) == {"path", "kind", "sha256", "size_bytes"}
            assert path.is_file() and not path.is_symlink()
            assert path.stat().st_size == row["size_bytes"]
            assert _sha(path) == row["sha256"]
    assert hashlib.sha256(canonical_json_bytes(inventory["artifacts"])).hexdigest() == inventory["tree_sha256"]

    positive = json.loads((output / summary["positive"]["evidence"]).read_text())
    assert positive["status"] == "passed"
    assert all(positive["checks"].values())
    assert positive["forbidden_call_count"] == 0
    assert positive["fixture_only"] is True
    assert positive["authenticated_human_review"] is False
    expected_terminal = {
        "status": "terminal_ready_for_reviewed_prose_within_recorded_scope",
        "action": "terminal_ready_for_reviewed_prose",
        "reason": "authoritative_hostile_result_is_clear_within_recorded_scope",
        "classification": "READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE",
    }
    expected_stages = ["merge_reviewed_evidence", "compose_reviewed_final_packet", "run_hostile_review"]
    assert "reviewed_evidence/reviewed_evidence_status.json" in positive["mission_tree"]
    assert "reviewed_final_packet/reviewed_final_packet.json" in positive["mission_tree"]
    assert "hostile_review/hostile_review_result.json" in positive["mission_tree"]
    assert "hostile_review/final_packet_readiness.json" in positive["mission_tree"]
    cli_records = []
    for cli_name in ("first_cli.json", "second_cli.json"):
        cli_record = json.loads((output / "positive" / cli_name).read_text())
        cli_records.append(cli_record)
        assert cli_record["return_code"] == 0
        assert cli_record["argv"][:2] == ["survey", "run-public-source-workflow"]
        supervisor = cli_record["payload"]["local_supervisor"]
        terminal = {
            "status": supervisor["status"],
            "action": supervisor["terminal_action_id"],
            "reason": supervisor["terminal_reason"],
            "classification": supervisor["readiness_classification"],
        }
        assert terminal == expected_terminal
    assert [row["stage_id"] for row in cli_records[0]["payload"]["local_supervisor"]["transition_history"]] == expected_stages
    assert cli_records[1]["payload"]["local_supervisor"]["transition_history"] == []

    mission = output / "positive" / "mission"
    pointer_ids = {
        "artifact_set_id": json.loads((mission / ".artifact_state" / "CURRENT").read_text())["artifact_set_id"],
        "claim_decision_set_id": json.loads((mission / "reviewed_claims" / "DECISION_CURRENT").read_text())["decision_set_id"],
        "source_observation_set_id": json.loads((mission / "reviewed_source_safety" / "OBSERVATION_CURRENT").read_text())["observation_set_id"],
        "source_decision_set_id": json.loads((mission / "reviewed_source_safety" / "DECISION_CURRENT").read_text())["decision_set_id"],
        "omission_decision_set_id": json.loads((mission / "reviewed_omissions" / "DECISION_CURRENT").read_text())["decision_set_id"],
    }
    assert positive["first_selected_ids"] == pointer_ids
    assert positive["second_selected_ids"] == pointer_ids
    assert _selected_ids_from_cli(cli_records[0], output) == pointer_ids
    assert _selected_ids_from_cli(cli_records[1], output) == pointer_ids

    rows = {row["case_id"]: row for row in summary["negative_cases"]}
    assert tuple(rows) == NEGATIVE_CASE_IDS
    for case_id, index in rows.items():
        assert index["status"] == "passed"
        evidence = json.loads((output / index["evidence"]).read_text())
        assert evidence["case_id"] == case_id
        assert evidence["status"] == "passed"
        assert evidence["setup_status"] == "passed"
        assert evidence["forbidden_call_count"] == 0
        assert evidence["cli_records"]
        assert all(row["argv"][0] == "survey" for row in evidence["cli_records"])
        assert all(isinstance(row["return_code"], int) for row in evidence["cli_records"])
        assert evidence["mission_mutation_contract"]["passed"] is True
        assert evidence["mission_mutation_contract"]["unexpected_changed_paths"] == []
        assert set(evidence["tripwire_counters"]) == {
            "provider_calls", "network_calls", "source_intake_calls",
            "model_or_subprocess_calls", "gpu_visibility_violations",
            "outside_write_calls",
        }

    noncanonical = json.loads((output / rows["noncanonical_reviewed_claim_root"]["evidence"]).read_text())
    assert noncanonical["observed"]["action"] == "terminal_blocked_invalid_artifact"
    legacy = json.loads((output / rows["legacy_v1_promotion"]["evidence"]).read_text())
    assert legacy["synthetic_input_unchanged"] is True
    assert legacy["mission_mutation_contract"]["changed_paths"] == []
    legacy_rows = legacy["cli_records"]
    assert len(legacy_rows) == 3
    assert len({row["evidence"] for row in legacy_rows}) == 3
    commands = [row["argv"][1] for row in legacy_rows]
    assert len(commands) == len(set(commands))
    legacy_commands = {
        row["argv"][1]: (row, output / "negative" / "legacy_v1_promotion" / row["evidence"])
        for row in legacy_rows
    }
    assert set(legacy_commands) == {
        "merge-reviewed-evidence",
        "compose-reviewed-final-packet",
        "hostile-review",
    }
    independently_observed = {}
    for command, (summary_row, path) in legacy_commands.items():
        cli_record = json.loads(path.read_text())
        assert cli_record["argv"] == summary_row["argv"]
        assert cli_record["return_code"] == summary_row["return_code"] == 1
        assert cli_record["argv"][:2] == ["survey", command]
        independently_observed[command] = cli_record["payload"]["blocked_reason"]
    assert independently_observed == {
        "merge-reviewed-evidence": "legacy_evidence_authority",
        "compose-reviewed-final-packet": "legacy_evidence_authority",
        "hostile-review": "legacy_evidence_authority",
    }
    assert legacy["observed"] == {
        "merge": "legacy_evidence_authority",
        "compose": "legacy_evidence_authority",
        "hostile": "legacy_evidence_authority",
    }


def test_phase10_offline_e2e_persists_exact_positive_and_negative_matrix(tmp_path: Path) -> None:
    output = tmp_path / "phase10"
    assert not output.exists()

    returned = run_validation(output)
    summary = json.loads((output / "e2e_summary.json").read_text())

    assert returned == summary
    _validate_persisted_candidate(output)


def test_phase10_offline_e2e_validates_frozen_canonical_candidate() -> None:
    output = Path(os.environ.get(
        "RA_M16_PHASE10_CANONICAL_ROOT",
        "docs/validation/literature_survey_m16_phase10_2026-07-13",
    ))
    _validate_persisted_candidate(output)


def test_phase10_frozen_cli_paths_rebase_without_dirty_checkout_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = Path("docs/validation/literature_survey_m16_phase10_2026-07-13")
    cli_record = json.loads((canonical / "positive" / "first_cli.json").read_text())
    reviewed = cli_record["payload"]["reviewed_artifacts"]
    source_id = Path(reviewed["reviewed_source_safety"]["required_path"]).parent.name
    output = tmp_path / "different-clone" / "phase10"
    source_path = (
        output
        / "positive"
        / "mission"
        / "reviewed_source_safety"
        / "decision_sets"
        / source_id
        / "reviewed_source_safety.json"
    )
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps({"observation_set_id": "clone-local-observation"}))

    original_read_text = Path.read_text
    dirty_root = Path.cwd().resolve()

    def reject_dirty_checkout_read(path: Path, *args: object, **kwargs: object) -> str:
        try:
            path.resolve().relative_to(dirty_root)
        except ValueError:
            return original_read_text(path, *args, **kwargs)
        raise AssertionError(f"unexpected dirty-checkout read: {path}")

    monkeypatch.setattr(Path, "read_text", reject_dirty_checkout_read)
    selected = _selected_ids_from_cli(cli_record, output)

    assert selected["source_observation_set_id"] == "clone-local-observation"
    assert selected["claim_decision_set_id"] == Path(
        reviewed["reviewed_claims"]["required_path"]
    ).parent.name
    assert selected["source_decision_set_id"] == source_id
    assert selected["omission_decision_set_id"] == Path(
        reviewed["reviewed_omissions"]["required_path"]
    ).parent.name


def test_phase10_tripwire_rejects_symlink_ancestor_write(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    (allowed / "escape").symlink_to(outside, target_is_directory=True)
    preopened = outside / "preopened.txt"
    descriptor = os.open(preopened, os.O_WRONLY | os.O_CREAT, 0o600)
    recycled_descriptor = None

    try:
        with _tripwired(allowed) as wires:
            with pytest.raises(AssertionError, match="write escaped case root"):
                (allowed / "escape" / "forbidden.txt").write_text("blocked\n")
            with pytest.raises(AssertionError, match="unverified descriptor"):
                os.fdopen(descriptor, "wb")
            with pytest.raises(AssertionError, match="direct write used an unverified descriptor"):
                os.write(descriptor, b"blocked")

            checked = os.open(allowed / "checked.txt", os.O_WRONLY | os.O_CREAT, 0o600)
            os.close(checked)
            recycled_descriptor = os.dup2(descriptor, checked)
            with pytest.raises(AssertionError, match="unverified descriptor"):
                os.fdopen(recycled_descriptor, "wb")
    finally:
        if recycled_descriptor is not None:
            os.close(recycled_descriptor)
        os.close(descriptor)

    assert wires.outside_write_calls == 4
    assert not (outside / "forbidden.txt").exists()


@pytest.mark.parametrize("nonempty", [False, True])
def test_phase10_offline_e2e_rejects_any_existing_root_without_mutation(
    tmp_path: Path,
    nonempty: bool,
) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "marker.txt"
    if nonempty:
        marker.write_text("preserve me\n")
    before = {
        str(path.relative_to(output)): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }

    with pytest.raises(ValueError, match="output root already exists"):
        run_validation(output)

    after = {
        str(path.relative_to(output)): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert not (output / "e2e_summary.json").exists()
