from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_assistant.survey.bootstrap import MissionBootstrapStore
from research_assistant.survey.build import build_bootstrap_effective_seed_skeleton
from research_assistant.survey.mission_state import (
    EXPLICIT_SEED_INPUT_MODE,
    TOPIC_INPUT_MODE,
    MissionStateError,
    MissionStateManager,
    pretty_json_bytes,
)
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.source_intake import run_mission_source_intake


TOPIC = "Neural Optimal Transport"
SEED = "arxiv:2201.12220v3"
FIXTURE_ROOT = Path("tests/fixtures/literature_survey_m17")


@dataclass
class FixtureCapability:
    fixture: Path
    name: str = "m17_deterministic_fixture"
    version: str = "1"
    calls: int = 0

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if request.get("input_mode") != TOPIC_INPUT_MODE:
            raise AssertionError("fixture capability received a non-topic request")
        return json.loads(self.fixture.read_text(encoding="utf-8"))


@dataclass
class TripwireCapability:
    name: str = "m17_preconfirmation_tripwire"
    version: str = "1"
    calls: int = 0

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        raise AssertionError("pre-confirmation capability call")


def _tree(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if relative in {".mission.lock", ".mission.lock.reclaim"}:
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                rows.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
            elif stat.S_ISREG(mode):
                raw = path.read_bytes()
                rows.append({
                    "path": relative,
                    "kind": "file",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size_bytes": len(raw),
                })
            elif not stat.S_ISDIR(mode):
                rows.append({"path": relative, "kind": "unsupported"})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("ascii")
    return {"artifact_count": len(rows), "tree_sha256": hashlib.sha256(raw).hexdigest(), "artifacts": rows}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(value))


def _new_manager(root: Path, *, confirmed: bool, resume: bool) -> MissionStateManager:
    return MissionStateManager(
        output_dir=root,
        topic=TOPIC,
        seeds=[],
        input_mode=TOPIC_INPUT_MODE,
        confirm_public_discovery=confirmed,
        resume=resume,
        force=False,
    )


def _run_outcome(root: Path, outcome: str) -> dict[str, Any]:
    capability = FixtureCapability(FIXTURE_ROOT / f"{outcome}.json")
    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=root,
        confirm_public_discovery=True,
        bootstrap_capability=capability,
    )
    expected_action = (
        "topic_bootstrap_selected_local_continuation"
        if outcome == "selected"
        else f"terminal_blocked_bootstrap_{outcome}"
    )
    checks = {
        "one_capability_call": capability.calls == 1,
        "outcome_matches": result.get("bootstrap_outcome") == outcome,
        "selected_complete": result.get("bootstrap_attempt_state") == "selected_complete",
        "action_matches": result.get("next_action", {}).get("action_id") == expected_action,
        "original_inputs_empty": result.get("seed_count") == 0 and result.get("initial_seeds") == [],
        "authority_shape": (
            isinstance(result.get("bootstrap_authority"), dict)
            and result.get("effective_seeds") == [SEED]
            if outcome == "selected"
            else result.get("bootstrap_authority") is None and result.get("effective_seeds") == []
        ),
        "downstream_boundary": (
            (root / "offline_skeleton" / "bootstrap_effective_seed_context.json").is_file()
            if outcome == "selected"
            else not (root / "offline_skeleton").exists()
        ),
    }
    before = _tree(root)
    replay = run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=root,
        resume=True,
        bootstrap_capability=capability,
    )
    after = _tree(root)
    checks.update({
        "resume_zero_new_calls": capability.calls == 1,
        "resume_result_stable": replay == result,
        "resume_tree_byte_identical": before == after,
    })
    payload = {
        "case": outcome,
        "result": result,
        "replay": replay,
        "tree": after,
        "checks": checks,
        "passed": all(checks.values()),
    }
    _write(root.parent / f"{root.name}_case_result.json", payload)
    return payload


def _unconfirmed(root: Path, *, case: str = "unconfirmed") -> dict[str, Any]:
    capability = TripwireCapability()
    result = run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=root,
        bootstrap_capability=capability,
    )
    checks = {
        "confirmation_required": result.get("bootstrap_attempt_state") == "confirmation_required",
        "zero_capability_calls": capability.calls == 0,
        "no_bootstrap_store": not (root / ".mission_state" / "bootstrap").exists(),
        "no_downstream": not (root / "offline_skeleton").exists() and not (root / "source_intake").exists(),
    }
    return {"case": case, "result": result, "tree": _tree(root), "checks": checks, "passed": all(checks.values())}


def _identity_change(root: Path) -> dict[str, Any]:
    first = run_public_source_workflow(topic=TOPIC, seeds=None, output_dir=root)
    before = _tree(root)
    changed = run_public_source_workflow(topic="Changed Topic", seeds=None, output_dir=root, resume=True)
    after = _tree(root)
    checks = {
        "setup_unconfirmed": first.get("bootstrap_attempt_state") == "confirmation_required",
        "identity_blocked": changed.get("next_action", {}).get("blockers", [{}])[0].get("code") == "mission_identity_mismatch",
        "zero_mutation": before == after,
    }
    return {"case": "identity_change", "result": changed, "tree": after, "checks": checks, "passed": all(checks.values())}


def _stale_authority(root: Path) -> dict[str, Any]:
    capability = FixtureCapability(FIXTURE_ROOT / "selected.json")
    selected = run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=root,
        confirm_public_discovery=True,
        bootstrap_capability=capability,
    )
    manager = _new_manager(root, confirmed=False, resume=True)
    snapshot = manager.begin()
    stale = dict(selected["bootstrap_authority"])
    stale["request_sha256"] = "0" * 64
    before = _tree(root)
    code = None
    try:
        build_bootstrap_effective_seed_skeleton(
            manager=manager,
            snapshot=snapshot,
            output_dir=root / "offline_skeleton",
            bootstrap_authority=stale,
        )
    except MissionStateError as exc:
        code = exc.code
    finally:
        manager.abort()
    after = _tree(root)
    checks = {"stale_blocked": code == "stale_bootstrap_authority", "zero_mutation": before == after}
    return {"case": "stale_authority", "blocked_code": code, "tree": after, "checks": checks, "passed": all(checks.values())}


def _corrupt_pointer(root: Path) -> dict[str, Any]:
    capability = FixtureCapability(FIXTURE_ROOT / "selected.json")
    run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=root,
        confirm_public_discovery=True,
        bootstrap_capability=capability,
    )
    pointer = root / ".mission_state" / "bootstrap" / "CURRENT"
    pointer.write_text("{}", encoding="utf-8")
    before = _tree(root)
    result = run_public_source_workflow(topic=TOPIC, seeds=None, output_dir=root, resume=True, bootstrap_capability=capability)
    after = _tree(root)
    checks = {
        "corruption_blocked": result.get("next_action", {}).get("blockers", [{}])[0].get("code") in {"invalid_schema", "invalid_bootstrap_current"},
        "zero_new_calls": capability.calls == 1,
        "zero_post_corruption_mutation": before == after,
    }
    return {"case": "corrupt_pointer", "result": result, "tree": after, "checks": checks, "passed": all(checks.values())}


def _prepared_orphan(root: Path) -> dict[str, Any]:
    run_public_source_workflow(topic=TOPIC, seeds=None, output_dir=root)
    capability = FixtureCapability(FIXTURE_ROOT / "selected.json")
    manager = _new_manager(root, confirmed=True, resume=True)
    snapshot = manager.begin()
    snapshot = manager.checkpoint_confirmation()
    store = MissionBootstrapStore.from_snapshot(
        manager=manager,
        snapshot=snapshot,
        now=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        crash_at="bootstrap:after_prepared",
    )
    crashed = False
    try:
        store.advance(capability)
    except RuntimeError:
        crashed = True
    prepared = store.observe()
    manager.abort()

    resumed_manager = _new_manager(root, confirmed=False, resume=True)
    resumed_snapshot = resumed_manager.begin()
    selected = MissionBootstrapStore.from_snapshot(
        manager=resumed_manager,
        snapshot=resumed_snapshot,
        now=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    ).advance(capability)
    resumed_manager.abort()
    checks = {
        "crash_injected": crashed,
        "prepared_non_authoritative": prepared["attempt_state"] == "prepared" and prepared["authority"] is None and prepared["effective_seeds"] == [],
        "resume_selected": selected["attempt_state"] == "selected_complete" and selected["effective_seeds"] == [SEED],
        "one_capability_call": capability.calls == 1,
    }
    return {"case": "prepared_orphan", "prepared": prepared, "selected": selected, "tree": _tree(root), "checks": checks, "passed": all(checks.values())}


def _source_guard(root: Path) -> dict[str, Any]:
    capability = FixtureCapability(FIXTURE_ROOT / "selected.json")
    run_public_source_workflow(
        topic=TOPIC,
        seeds=None,
        output_dir=root,
        confirm_public_discovery=True,
        bootstrap_capability=capability,
    )
    manager = _new_manager(root, confirmed=False, resume=True)
    snapshot = manager.begin()
    before = _tree(root)
    code = None
    try:
        run_mission_source_intake(
            mission_root=root,
            metadata_root=root / "public_metadata",
            snapshot=snapshot,
            capability=object(),  # Guard must fire before a capability is inspected or called.
        )
    except MissionStateError as exc:
        code = exc.code
    finally:
        manager.abort()
    after = _tree(root)
    checks = {
        "source_guard": code == "topic_bootstrap_metadata_authority_required",
        "zero_mutation": before == after,
        "no_source_output": not (root / "source_intake").exists(),
    }
    return {"case": "source_guard", "blocked_code": code, "tree": after, "checks": checks, "passed": all(checks.values())}


def _explicit_seed(root: Path) -> dict[str, Any]:
    result = run_public_source_workflow(topic=TOPIC, seeds=[SEED], output_dir=root)
    mission = json.loads((root / "mission_control.json").read_text(encoding="utf-8"))
    genesis = json.loads((root / ".mission_state" / "GENESIS").read_text(encoding="utf-8"))
    checks = {
        "public_schema_unchanged": result.get("schema_version") == "ra-survey-public-source-orchestration-result-v1",
        "mission_schema_unchanged": mission.get("schema_version") == "ra-survey-public-source-mission-control-v2",
        "contract_schema_unchanged": mission.get("mission_contract", {}).get("schema_version") == "ra-survey-public-source-mission-contract-v2",
        "genesis_schema_unchanged": genesis.get("schema_version") == "ra-survey-public-source-genesis-anchor-v1",
        "seed_preserved": mission.get("seeds") == [SEED],
    }
    return {"case": "explicit_seed_regression", "result": result, "tree": _tree(root), "checks": checks, "passed": all(checks.values())}


def run(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise RuntimeError(f"validation output already exists: {output}")
    output.mkdir(parents=True)
    cases_root = output / "cases"
    cases_root.mkdir()

    cases: list[dict[str, Any]] = []
    cases.append(_unconfirmed(cases_root / "unconfirmed"))
    for outcome in ("selected", "empty", "ambiguous", "unavailable", "capped"):
        cases.append(_run_outcome(cases_root / outcome, outcome))
    cases.extend([
        _identity_change(cases_root / "identity_change"),
        _stale_authority(cases_root / "stale_authority"),
        _corrupt_pointer(cases_root / "corrupt_pointer"),
        _prepared_orphan(cases_root / "prepared_orphan"),
        _unconfirmed(cases_root / "preconfirmation_tripwire", case="preconfirmation_tripwire"),
        _source_guard(cases_root / "source_guard"),
        _explicit_seed(cases_root / "explicit_seed_regression"),
    ])
    for case in cases:
        _write(output / "results" / f"{case['case']}.json", case)
    summary = {
        "schema_version": "ra-literature-survey-m17-local-validation-v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cpu_gpu_policy": {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"), "gpu_used": False},
        "fixture_root": str(FIXTURE_ROOT.resolve()),
        "case_count": len(cases),
        "passed_count": sum(case["passed"] for case in cases),
        "failed_cases": [case["case"] for case in cases if not case["passed"]],
        "cases": [{"case": case["case"], "passed": case["passed"], "checks": case["checks"]} for case in cases],
        "what_is_not_concluded": [
            "live bootstrap quality",
            "paper relevance or importance",
            "literature completeness",
            "source support",
            "scientific correctness",
            "human review",
            "product readiness",
        ],
    }
    summary["passed"] = summary["passed_count"] == summary["case_count"] and summary["cpu_gpu_policy"]["CUDA_VISIBLE_DEVICES"] == "-1"
    _write(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = run(args.output)
    except Exception:
        if args.output.exists():
            shutil.rmtree(args.output, ignore_errors=True)
        raise
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
