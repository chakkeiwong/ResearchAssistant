from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
BASELINE_COMMIT = "1b36af06efc7e1c2c086934cd8800691ae8a6da7"
PHASE10_CHANGE_MANIFEST_SHA256 = "23246fcb259140aefeb8bd4f3df865a8279ac6ea69bbebf0ee1c964b759bcd28"
PHASE10_INVENTORY_SHA256 = "9cb607f8f6c0259bdf7801437451b948cc2dc40ec4f15f130747f6651bab1337"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_pretty_bytes(value))


def _relative(path: Path) -> str:
    resolved = path.absolute()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"path escapes repository root: {path}") from exc


def _row(path: Path, *, role: str, provenance: str) -> dict[str, Any]:
    relative = _relative(path)
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        raw = path.read_bytes()
        kind = "file"
    elif stat.S_ISLNK(mode):
        raw = os.readlink(path).encode("utf-8")
        kind = "symlink"
    else:
        raise RuntimeError(f"manifest member is not a regular file or symlink: {relative}")
    return {
        "kind": kind,
        "mode_octal": f"{stat.S_IMODE(mode):04o}",
        "path": relative,
        "provenance": provenance,
        "role": role,
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
    }


def _files(root: Path) -> list[Path]:
    if not root.is_dir():
        raise RuntimeError(f"required directory is absent: {_relative(root)}")
    rows: list[Path] = []
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode) or stat.S_ISLNK(mode):
            rows.append(path)
        elif not stat.S_ISDIR(mode):
            raise RuntimeError(f"unsupported tree member: {_relative(path)}")
    return rows


def _glob_files(pattern: str) -> list[Path]:
    return [path for path in sorted(ROOT.glob(pattern)) if path.is_file()]


def _repository_path(relative: Any, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise RuntimeError(f"{label} is not a nonempty repository-relative path")
    lexical = PurePosixPath(relative)
    if lexical.is_absolute() or ".." in lexical.parts or str(lexical) != relative:
        raise RuntimeError(f"{label} escapes or is not canonical: {relative!r}")
    return ROOT / relative


def _validated_json(path: Path, *, expected_sha256: str, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} is not a regular file: {_relative(path)}")
    raw = path.read_bytes()
    if _sha256(raw) != expected_sha256:
        raise RuntimeError(f"{label} hash does not match frozen authority")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _validated_phase10_inventory_paths() -> list[Path]:
    validation_root = ROOT / "docs/validation/literature_survey_m16_phase10_2026-07-13"
    inventory_path = validation_root / "e2e_artifact_inventory.json"
    inventory = _validated_json(
        inventory_path,
        expected_sha256=PHASE10_INVENTORY_SHA256,
        label="M16 Phase 10 inventory",
    )
    artifacts = inventory.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1137:
        raise RuntimeError("M16 Phase 10 inventory must contain exactly 1,137 rows")
    paths: list[Path] = []
    for expected in artifacts:
        relative = expected.get("path")
        if not isinstance(relative, str) or not relative:
            raise RuntimeError("M16 Phase 10 inventory contains an invalid path")
        path = _repository_path(
            f"docs/validation/literature_survey_m16_phase10_2026-07-13/{relative}",
            label="M16 Phase 10 inventory path",
        )
        if relative != "e2e_static_audit.json" and not relative.startswith(("positive/", "negative/")):
            raise RuntimeError(f"M16 Phase 10 inventory row is outside its declared scope: {relative}")
        mode = path.lstat().st_mode
        if expected.get("kind") == "file":
            if not stat.S_ISREG(mode):
                raise RuntimeError(f"M16 Phase 10 file row changed type: {relative}")
            raw = path.read_bytes()
            if _sha256(raw) != expected.get("sha256") or len(raw) != expected.get("size_bytes"):
                raise RuntimeError(f"M16 Phase 10 file row does not replay: {relative}")
        elif expected.get("kind") == "symlink":
            if not stat.S_ISLNK(mode) or os.readlink(path) != expected.get("target"):
                raise RuntimeError(f"M16 Phase 10 symlink row does not replay: {relative}")
        else:
            raise RuntimeError(f"M16 Phase 10 inventory has an unknown kind: {relative}")
        paths.append(path)
    return paths


def _validated_manifest_paths(
    manifest_path: Path,
    sections: tuple[str, ...],
    *,
    expected_count: int,
) -> list[Path]:
    manifest = _validated_json(
        manifest_path,
        expected_sha256=PHASE10_CHANGE_MANIFEST_SHA256,
        label="M16 Phase 10 change manifest",
    )
    paths: list[Path] = []
    for section in sections:
        rows = manifest.get(section)
        if not isinstance(rows, list):
            raise RuntimeError(f"manifest section is absent or not a list: {section}")
        for expected in rows:
            relative = expected.get("path")
            digest = expected.get("sha256")
            if not isinstance(digest, str):
                raise RuntimeError(f"manifest row lacks path/hash: {section}")
            path = _repository_path(relative, label=f"manifest path in {section}")
            if not path.is_file() or path.is_symlink() or _sha256(path.read_bytes()) != digest:
                raise RuntimeError(f"manifest row does not replay: {relative}")
            paths.append(path)
    if len(paths) != expected_count:
        raise RuntimeError(f"manifest direct-row count changed: expected {expected_count}, got {len(paths)}")
    return paths


def _validated_singleton_manifest_path(manifest_path: Path, field: str) -> Path:
    manifest = _validated_json(
        manifest_path,
        expected_sha256=PHASE10_CHANGE_MANIFEST_SHA256,
        label="M16 Phase 10 change manifest",
    )
    expected = manifest.get(field)
    if not isinstance(expected, dict) or not isinstance(expected.get("sha256"), str):
        raise RuntimeError(f"manifest singleton is absent or invalid: {field}")
    path = _repository_path(expected.get("path"), label=f"manifest singleton {field}")
    if not path.is_file() or path.is_symlink() or _sha256(path.read_bytes()) != expected["sha256"]:
        raise RuntimeError(f"manifest singleton does not replay: {expected.get('path')}")
    return path


def _add(
    table: dict[str, dict[str, Any]],
    paths: Iterable[Path],
    *,
    role: str,
    provenance: str,
) -> None:
    for path in paths:
        row = _row(path, role=role, provenance=provenance)
        previous = table.get(row["path"])
        if previous is not None and previous["sha256"] != row["sha256"]:
            raise RuntimeError(f"conflicting hashes for {row['path']}")
        if previous is None:
            table[row["path"]] = row


def _successor_manifest() -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}

    _add(
        rows,
        [ROOT / "src/research_assistant/cli.py"],
        role="public_cli",
        provenance="current_cumulative_m16_m17",
    )
    _add(
        rows,
        _glob_files("src/research_assistant/survey/*.py"),
        role="survey_runtime",
        provenance="current_cumulative_m16_m17",
    )
    _add(
        rows,
        _glob_files("src/research_assistant/benchmarks/*.py"),
        role="cli_imported_surveybench_runtime",
        provenance="current_cumulative_m16_m17",
    )

    test_paths = [
        *_glob_files("tests/unit/test_literature_survey_m16*.py"),
        ROOT / "tests/unit/test_literature_survey_m17.py",
        *_glob_files("tests/unit/test_survey*.py"),
        ROOT / "tests/integration/test_cli_commands.py",
        ROOT / "tests/integration/test_surveybench_agent_trial.py",
        ROOT / "tests/scripts/run_survey_benchmark.py",
        *_glob_files("tests/scripts/test_literature_survey*.py"),
    ]
    _add(
        rows,
        test_paths,
        role="cumulative_local_gate_test",
        provenance="current_cumulative_m16_m17",
    )

    script_paths = [
        *_glob_files("scripts/literature_survey*.py"),
        *_glob_files("scripts/surveybench_phase*.py"),
    ]
    _add(
        rows,
        script_paths,
        role="cumulative_validation_script",
        provenance="current_cumulative_m16_m17",
    )
    _add(
        rows,
        _files(ROOT / "tests/fixtures/literature_survey_m17"),
        role="m17_deterministic_fixture",
        provenance="current_m17",
    )
    _add(
        rows,
        _files(ROOT / "tests/fixtures/surveybench"),
        role="inherited_surveybench_fixture_dependency",
        provenance="current_cumulative_m16_m17",
    )

    authority_paths = [
        ROOT / "docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_subplan_2026-07-13.md",
        ROOT / "docs/plans/literature_survey_m16_phase10_offline_e2e_result_2026-07-13.md",
        ROOT / "docs/validation/literature_survey_m16_phase10_2026-07-13/change_manifest.json",
        ROOT / "docs/validation/literature_survey_m16_phase10_2026-07-13/e2e_artifact_inventory.json",
        ROOT / "docs/reviews/literature_survey_m16_phase10_implementation_review_bundle_round5_2026-07-13.md",
        ROOT / "docs/reviews/literature_survey_m16_phase10_implementation_review_verdict_round5_2026-07-13.md",
        *_glob_files("docs/validation/literature_survey_m16_phase[1-9]_2026-07-*/change_manifest.json"),
    ]
    _add(
        rows,
        authority_paths,
        role="inherited_authority",
        provenance="frozen_m16_or_reviewed_m17_entry",
    )
    _add(
        rows,
        _files(OUTPUT / "pre_edit_m16_snapshot"),
        role="immutable_pre_edit_snapshot",
        provenance="frozen_m17_entry",
    )
    _add(
        rows,
        [OUTPUT / "generate_close_artifacts.py"],
        role="successor_manifest_replay_tool",
        provenance="current_m17",
    )
    _add(
        rows,
        _validated_phase10_inventory_paths(),
        role="canonical_m16_phase10_evidence_member",
        provenance="frozen_m16_phase10_inventory",
    )
    _add(
        rows,
        _validated_manifest_paths(
            ROOT / "docs/validation/literature_survey_m16_phase10_2026-07-13/change_manifest.json",
            (
                "governing_artifacts",
                "implementation_and_test_hashes",
                "primary_e2e_evidence",
                "final_validation_evidence",
                "authoritative_logs",
                "review_history",
            ),
            expected_count=37,
        ),
        role="canonical_m16_phase10_direct_evidence",
        provenance="frozen_m16_phase10_change_manifest",
    )
    _add(
        rows,
        [
            _validated_singleton_manifest_path(
                ROOT / "docs/validation/literature_survey_m16_phase10_2026-07-13/change_manifest.json",
                "inherited_phase9_authority",
            )
        ],
        role="canonical_m16_phase10_direct_evidence",
        provenance="frozen_m16_phase10_change_manifest",
    )

    final_evidence_paths = [
        OUTPUT / "focused_final_schema_round2.xml",
        OUTPUT / "cumulative_m16_m17_unit_round1.xml",
        OUTPUT / "exact_scripts_final.xml",
        OUTPUT / "affected_non_cli_integration_final.xml",
        OUTPUT / "full_unit_retry_after_vscode_crash.xml",
        OUTPUT / "full_cli_retry_after_vscode_crash.xml",
    ]
    _add(
        rows,
        final_evidence_paths,
        role="authoritative_final_local_gate",
        provenance="current_m17",
    )
    _add(
        rows,
        _files(OUTPUT / "persistent_matrix_final2"),
        role="authoritative_persistent_matrix",
        provenance="current_m17",
    )

    ordered = [rows[path] for path in sorted(rows)]
    digest_payload = {
        "baseline_commit": BASELINE_COMMIT,
        "rows": ordered,
        "schema_version": "ra-literature-survey-m17-successor-manifest-v1",
    }
    return {
        **digest_payload,
        "artifact_count": len(ordered),
        "manifest_payload_sha256": _sha256(_canonical_bytes(digest_payload)),
        "scope": {
            "baseline": "Git HEAD supplies unchanged tracked repository bytes",
            "included": [
                "current survey and CLI-imported SurveyBench runtime",
                "cumulative M16/M17 and SurveyBench local-gate tests and fixtures",
                "exact survey validation scripts",
                "frozen M16 authority and immutable M17 entry snapshot",
                "final M17 JUnit and persistent-matrix evidence",
            ],
            "excluded": [
                "crash-interrupted and superseded diagnostic test artifacts",
                "mutable master, milestone, ledger, reset, handoff, result, and review mirrors updated after this manifest",
                "unrelated arXiv intake changes and unrelated historical validation trees",
                "caches, environments, credentials, and generated Claude gate logs",
            ],
        },
        "status": "candidate_replay_passed_pending_artifact_closure_rereview",
        "what_is_not_concluded": [
            "clean-checkout or Git reproducibility",
            "live bootstrap quality or provider reliability",
            "source support, human review, scientific validity, or product readiness",
            "north-star mission completion",
        ],
    }


def _replay_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[dict[str, str]] = []
    for expected in manifest["rows"]:
        path = ROOT / expected["path"]
        try:
            actual = _row(path, role=expected["role"], provenance=expected["provenance"])
        except Exception as exc:
            mismatches.append({"path": expected["path"], "reason": str(exc)})
            continue
        for key in ("kind", "mode_octal", "sha256", "size_bytes"):
            if actual[key] != expected[key]:
                mismatches.append({
                    "path": expected["path"],
                    "reason": f"{key}: expected {expected[key]!r}, got {actual[key]!r}",
                })
    digest_payload = {
        "baseline_commit": manifest["baseline_commit"],
        "rows": manifest["rows"],
        "schema_version": manifest["schema_version"],
    }
    digest = _sha256(_canonical_bytes(digest_payload))
    return {
        "artifact_count": len(manifest["rows"]),
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "expected_manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "manifest_payload_sha256": digest,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "passed": not mismatches and digest == manifest["manifest_payload_sha256"],
        "schema_version": "ra-literature-survey-m17-successor-manifest-replay-v1",
    }


def main() -> int:
    manifest = _successor_manifest()
    replay = _replay_manifest(manifest)
    if not replay["passed"]:
        raise RuntimeError(f"successor manifest replay failed: {replay['mismatches']}")
    _write_json(OUTPUT / "successor_manifest.json", manifest)
    _write_json(OUTPUT / "successor_manifest_replay.json", replay)
    print(json.dumps({
        "artifact_count": manifest["artifact_count"],
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "replay_passed": replay["passed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
