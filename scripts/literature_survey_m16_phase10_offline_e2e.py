from __future__ import annotations

import argparse
import builtins
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator
from unittest.mock import patch

from research_assistant.cli import main as cli_main
import research_assistant.survey.build as survey_build
import research_assistant.survey.orchestrate as survey_orchestrate
from research_assistant.survey.artifact_lineage import COVERAGE_FILES, ArtifactStateManager, semantic_item, workflow_blocker_source_id
from research_assistant.survey.claim_review import SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA, SURVEY_CLAIM_REVIEW_V3_SCHEMA
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.mission_state import MissionStateManager, canonical_json_bytes, pretty_json_bytes, sha256_bytes
from research_assistant.survey.orchestrate import run_public_source_workflow
from research_assistant.survey.reviewed_merge import merge_reviewed_evidence
from research_assistant.survey.reviewed_packet import compose_reviewed_final_packet
from research_assistant.survey.hostile_review import run_hostile_review_gate
from research_assistant.survey.source_intake import MissionSourceCapability, SourceCapabilityResult
from research_assistant.survey.source_safety_review import (
    SOURCE_CHECKS,
    SOURCE_OBSERVATION_NONCLAIMS,
    SURVEY_SOURCE_OBSERVATION_SET_SCHEMA,
    SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA,
    preview_source_observation_binding,
)


TOPIC = "Neural Optimal Transport for generative modeling and inference"
SEED = "arxiv:2201.12220v3"
SCHEMA = "ra-literature-survey-m16-phase10-offline-e2e-v1"
NONCLAIMS = [
    "authenticated human review",
    "source safety in fact",
    "claim truth",
    "omission correctness",
    "literature completeness",
    "scientific correctness",
    "final prose quality",
    "Git reproducibility",
    "live reliability",
    "product or release readiness",
]
NEGATIVE_CASE_IDS = (
    "missing_public_confirmation",
    "changed_topic_resume",
    "changed_seed_resume",
    "open_omission_review",
    "missing_current_workflow_review",
    "noncanonical_reviewed_claim_root",
    "malformed_reviewed_merge",
    "symlinked_reviewed_packet",
    "upstream_packet_change",
    "legacy_v1_promotion",
)


@dataclass(frozen=True)
class CliResult:
    argv: list[str]
    return_code: int
    payload: dict[str, Any]
    stdout: str
    stderr: str


@dataclass
class Tripwires:
    provider_calls: int = 0
    network_calls: int = 0
    source_intake_calls: int = 0
    model_or_subprocess_calls: int = 0
    gpu_visibility_violations: int = 0
    outside_write_calls: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "provider_calls": self.provider_calls,
            "network_calls": self.network_calls,
            "source_intake_calls": self.source_intake_calls,
            "model_or_subprocess_calls": self.model_or_subprocess_calls,
            "gpu_visibility_violations": self.gpu_visibility_violations,
            "outside_write_calls": self.outside_write_calls,
        }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(payload))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> dict[str, dict[str, Any]]:
    if not root.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            result[relative] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            result[relative] = {"kind": "file", "sha256": _sha(path), "size_bytes": path.stat().st_size}
        elif path.is_dir():
            result[relative] = {"kind": "directory"}
    return result


def _tree_changes(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> list[str]:
    return [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]


def _path_allowed(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def _mutation_contract(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    allowed_prefixes: tuple[str, ...],
) -> dict[str, Any]:
    changed = _tree_changes(before, after)
    unexpected = [path for path in changed if not _path_allowed(path, allowed_prefixes)]
    return {
        "allowed_changed_prefixes": list(allowed_prefixes),
        "changed_paths": changed,
        "unexpected_changed_paths": unexpected,
        "passed": not unexpected,
    }


def _artifact_inventory(root: Path) -> dict[str, Any]:
    rows = []
    roots = [root / "positive", root / "negative"]
    for inventory_root in roots:
        for path in sorted(inventory_root.rglob("*")):
            if path.is_symlink():
                rows.append({
                    "path": str(path.relative_to(root)),
                    "kind": "symlink",
                    "target": os.readlink(path),
                })
                continue
            if not path.is_file():
                continue
            raw = path.read_bytes()
            rows.append({
                "path": str(path.relative_to(root)),
                "kind": "file",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            })
    audit = root / "e2e_static_audit.json"
    raw = audit.read_bytes()
    rows.append({
        "path": str(audit.relative_to(root)),
        "kind": "file",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    })
    rows.sort(key=lambda row: row["path"])
    tree_digest = hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
    return {
        "schema_version": "ra-literature-survey-m16-phase10-e2e-artifact-inventory-v1",
        "hash_scope": "every regular file and symlink under positive/** and negative/** plus e2e_static_audit.json",
        "artifact_count": len(rows),
        "tree_sha256": tree_digest,
        "artifacts": rows,
    }


def _stale_path_audit(root: Path) -> dict[str, Any]:
    needle = b"/tmp/m16-phase10-"
    matches = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        scanned += 1
        raw = path.read_bytes()
        if needle in raw:
            matches.append(str(path.relative_to(root)))
    return {
        "schema_version": "ra-literature-survey-m16-phase10-static-audit-v1",
        "status": "passed" if not matches else "failed",
        "scan_kind": "byte_substring_scan",
        "forbidden_byte_string_hex": needle.hex(),
        "regular_file_count": scanned,
        "matching_relative_paths": matches,
        "matching_file_count": len(matches),
    }


def _run_cli(argv: list[str], evidence_path: Path | None = None) -> CliResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            return_code = cli_main(argv)
        except SystemExit as exc:
            return_code = int(exc.code) if isinstance(exc.code, int) else 1
    output = stdout.getvalue()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        payload = {"unparsed_stdout": output}
    result = CliResult(argv=argv, return_code=return_code, payload=payload, stdout=output, stderr=stderr.getvalue())
    if evidence_path is not None:
        _write_json(evidence_path, {
            "argv": result.argv,
            "return_code": result.return_code,
            "payload": result.payload,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
    return result


def _beneath(path: Any, root: Path) -> bool:
    try:
        candidate = Path(path).resolve(strict=False)
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    return candidate == resolved_root or resolved_root in candidate.parents


@contextlib.contextmanager
def _tripwired(allowed_write_root: Path) -> Iterator[Tripwires]:
    counters = Tripwires()
    allowed_write_root = allowed_write_root.resolve(strict=True)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        counters.gpu_visibility_violations += 1
        raise AssertionError("Phase 10 measured calls require CUDA_VISIBLE_DEVICES=-1")

    def network_forbidden(*args: Any, **kwargs: Any) -> Any:
        counters.network_calls += 1
        raise AssertionError("Phase 10 forbids network transport")

    def provider_forbidden(*args: Any, **kwargs: Any) -> Any:
        counters.provider_calls += 1
        raise AssertionError("Phase 10 forbids provider collection after fixture setup")

    def source_forbidden(*args: Any, **kwargs: Any) -> Any:
        counters.source_intake_calls += 1
        raise AssertionError("Phase 10 forbids source-intake capability after fixture setup")

    def subprocess_forbidden(*args: Any, **kwargs: Any) -> Any:
        counters.model_or_subprocess_calls += 1
        raise AssertionError("Phase 10 forbids subprocess/model launch")

    def assert_write(path: Any) -> None:
        if not _beneath(path, allowed_write_root):
            counters.outside_write_calls += 1
            raise AssertionError(f"Phase 10 write escaped case root: {path}")

    real_open = builtins.open
    real_io_open = io.open
    real_os_open = os.open
    real_os_close = os.close
    real_os_dup = os.dup
    real_os_dup2 = os.dup2
    real_os_write = os.write
    real_mkdir = os.mkdir
    real_replace = os.replace
    real_rename = os.rename
    real_unlink = os.unlink
    real_remove = os.remove
    real_rmdir = os.rmdir
    checked_write_fds: dict[int, tuple[int, int, int]] = {}

    def descriptor_identity(descriptor: int) -> tuple[int, int, int] | None:
        try:
            status = os.fstat(descriptor)
        except OSError:
            return None
        return status.st_dev, status.st_ino, status.st_mode

    def assert_file_or_checked_fd(file: Any) -> None:
        if isinstance(file, int) and not isinstance(file, bool):
            identity = descriptor_identity(file)
            if checked_write_fds.get(file) != identity:
                counters.outside_write_calls += 1
                raise AssertionError(f"Phase 10 write used an unverified descriptor: {file}")
            checked_write_fds.pop(file)
            return
        assert_write(file)

    def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in "wax+"):
            assert_file_or_checked_fd(file)
        return real_open(file, mode, *args, **kwargs)

    def guarded_io_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in "wax+"):
            assert_file_or_checked_fd(file)
        return real_io_open(file, mode, *args, **kwargs)

    def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> Any:
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if flags & write_flags:
            assert_write(path)
        descriptor = real_os_open(path, flags, *args, **kwargs)
        if flags & write_flags:
            identity = descriptor_identity(descriptor)
            if identity is None:
                real_os_close(descriptor)
                raise AssertionError("Phase 10 could not attest a writable descriptor")
            checked_write_fds[descriptor] = identity
        return descriptor

    def guarded_os_close(descriptor: int, *args: Any, **kwargs: Any) -> Any:
        checked_write_fds.pop(descriptor, None)
        return real_os_close(descriptor, *args, **kwargs)

    def guarded_os_dup(descriptor: int, *args: Any, **kwargs: Any) -> int:
        duplicate = real_os_dup(descriptor, *args, **kwargs)
        checked_write_fds.pop(duplicate, None)
        return duplicate

    def guarded_os_dup2(source: int, destination: int, *args: Any, **kwargs: Any) -> int:
        checked_write_fds.pop(destination, None)
        duplicate = real_os_dup2(source, destination, *args, **kwargs)
        checked_write_fds.pop(duplicate, None)
        return duplicate

    def guarded_os_write(descriptor: int, data: Any, *args: Any, **kwargs: Any) -> int:
        identity = descriptor_identity(descriptor)
        if checked_write_fds.get(descriptor) != identity:
            counters.outside_write_calls += 1
            raise AssertionError(f"Phase 10 direct write used an unverified descriptor: {descriptor}")
        return real_os_write(descriptor, data, *args, **kwargs)

    def guarded_mkdir(path: Any, *args: Any, **kwargs: Any) -> Any:
        assert_write(path)
        return real_mkdir(path, *args, **kwargs)

    def guarded_replace(source: Any, destination: Any, *args: Any, **kwargs: Any) -> Any:
        assert_write(source)
        assert_write(destination)
        return real_replace(source, destination, *args, **kwargs)

    def guarded_rename(source: Any, destination: Any, *args: Any, **kwargs: Any) -> Any:
        assert_write(source)
        assert_write(destination)
        return real_rename(source, destination, *args, **kwargs)

    def guarded_unlink(path: Any, *args: Any, **kwargs: Any) -> Any:
        assert_write(path)
        return real_unlink(path, *args, **kwargs)

    def guarded_remove(path: Any, *args: Any, **kwargs: Any) -> Any:
        assert_write(path)
        return real_remove(path, *args, **kwargs)

    def guarded_rmdir(path: Any, *args: Any, **kwargs: Any) -> Any:
        assert_write(path)
        return real_rmdir(path, *args, **kwargs)

    patches = (
        patch.object(urllib.request, "urlopen", network_forbidden),
        patch.object(survey_build, "_collect_public_metadata", provider_forbidden),
        patch.object(survey_build, "_fetch_public_json", provider_forbidden),
        patch.object(survey_build, "_openalex_metadata_search", provider_forbidden),
        patch.object(survey_build, "_openalex_cited_by", provider_forbidden),
        patch.object(survey_build, "_arxiv_metadata_query", provider_forbidden),
        patch.object(survey_orchestrate, "run_mission_source_intake", source_forbidden),
        patch.object(subprocess, "run", subprocess_forbidden),
        patch.object(subprocess, "Popen", subprocess_forbidden),
        patch.object(builtins, "open", guarded_open),
        patch.object(io, "open", guarded_io_open),
        patch.object(os, "open", guarded_os_open),
        patch.object(os, "close", guarded_os_close),
        patch.object(os, "dup", guarded_os_dup),
        patch.object(os, "dup2", guarded_os_dup2),
        patch.object(os, "write", guarded_os_write),
        patch.object(os, "mkdir", guarded_mkdir),
        patch.object(os, "replace", guarded_replace),
        patch.object(os, "rename", guarded_rename),
        patch.object(os, "unlink", guarded_unlink),
        patch.object(os, "remove", guarded_remove),
        patch.object(os, "rmdir", guarded_rmdir),
    )
    with contextlib.ExitStack() as stack:
        for active_patch in patches:
            stack.enter_context(active_patch)
        yield counters


def _metadata_collection(*, topic: str, seeds: list[str], providers: list[str], max_records: int, fetched_at: str) -> dict[str, Any]:
    if topic != TOPIC or seeds != [SEED] or providers != ["arxiv"] or max_records != 25:
        raise AssertionError("fixture metadata request changed")
    statuses = []
    for provider in ("arxiv",):
        statuses.extend([
            {"provider": provider, "query_kind": "seed_resolution", "normalized_seed_key": SEED, "topic_query": False, "query_cap": 5, "status": "available", "record_count": 1, "raw_response_saved": False},
            {"provider": provider, "query_kind": "topic_search", "normalized_seed_key": None, "topic_query": True, "query_cap": 12, "status": "available", "record_count": 0, "raw_response_saved": False},
        ])
    return {
        "status": "metadata_collected",
        "fetched_at": fetched_at,
        "provider_statuses": statuses,
        "raw_response_policy": {"raw_responses_saved": False, "privacy_scan": "not_applicable_raw_responses_not_saved", "reason": "Phase 10 deterministic fixture"},
        "records": [{
            "record_key": SEED,
            "title": "Neural Optimal Transport",
            "authors": ["Synthetic Fixture Author"],
            "year": 2022,
            "doi": None,
            "arxiv_id": "2201.12220v3",
            "openalex_id": None,
            "landing_page_url": "https://arxiv.org/abs/2201.12220v3",
            "citation_count": None,
            "providers": ["arxiv"],
            "roles": [],
            "provider_records": [
                {"provider": "arxiv", "query_kind": "seed_resolution", "source_id": "2201.12220v3", "primary_category": "cs.LG", "published": "2022-01-01"},
            ],
            "referenced_works": [],
            "query_provenance": [
                {"provider": "arxiv", "query_kind": "seed_resolution", "normalized_seed_key": SEED, "topic_query": False},
            ],
        }],
    }


def _fixture_source(request: Any) -> SourceCapabilityResult:
    final_url = f"https://arxiv.org/abs/{request.identifier.split(':', 1)[1]}"
    record = {
        "paper_id": request.paper_id,
        "source_type": "arxiv_latex",
        "status": "available",
        "primary_for_audit": True,
        "artifact_root": None,
        "original_source_path": None,
        "flattened_source_path": None,
        "sections": [{"level": 1, "command": "section", "title": "Method", "line": 1, "labels": ["sec-method"], "raw_latex": "Fixture-only Neural Optimal Transport method section."}],
        "equations": [], "theorem_like_blocks": [], "labels": [], "references": [], "citations": [], "bibliography": [], "macros": [],
        "provenance": {"arxiv_id": "2201.12220v3", "identifier": request.identifier, "provider": "arxiv", "final_url": final_url, "fixture_only": True},
        "diagnostics": {"source_bytes": 0, "section_count": 1, "equation_count": 0, "theorem_like_block_count": 0, "fixture_only": True},
        "limitations": [{"field": "source", "status": "fixture_only", "note": "No live source transport was run."}],
    }
    return SourceCapabilityResult(
        candidate_id=request.candidate_id,
        identifier=request.identifier,
        outcome_status="available",
        code="available",
        provider="arxiv",
        final_url=final_url,
        structured_record=record,
        byte_count=len(pretty_json_bytes(record)),
    )


def _bound_decisions(queue_path: Path, queue: dict[str, Any], decision_type: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "ra-survey-review-decisions-v2",
        "decision_type": decision_type,
        "mission_id": queue["mission_id"],
        "mission_fingerprint": queue["mission_fingerprint"],
        "artifact_set_id": queue["artifact_set_id"],
        "queue_semantic_sha256": queue["queue_semantic_sha256"],
        "review_queue_sha256": _sha(queue_path),
        "decisions": decisions,
    }


def _claim_envelope(queue_path: Path) -> dict[str, Any]:
    context = load_v2_evidence_context(queue_path)
    item = next(row for row in context.review_queue["items"] if row["queue_type"] == "claim_candidate")
    dependencies = [
        {
            "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id,
            "canonical_identifier": identity.canonical_identifier,
            "source_version": identity.source_version,
            "source_record_sha256": identity.source_record_sha256,
            "dependency_role": "primary_technical_source",
        }
        for identity in sorted(context.source_identities.values(), key=lambda row: row.source_paper_id)
        if identity.source_paper_id in item["paper_ids"]
    ]
    projection = {
        "schema_version": SURVEY_CLAIM_DEPENDENCY_MANIFEST_SCHEMA,
        "evidence_kind": "primary_technical_support",
        "local_artifact": None,
        "local_artifact_sha256": None,
        "direct_source_paper_ids": sorted(row["source_paper_id"] for row in dependencies),
        "referenced_manifest_ids": [],
    }
    manifest_id = f"dm-{sha256_bytes(canonical_json_bytes(projection))}"
    manifests = [{"manifest_id": manifest_id, **projection}]
    graph = {"schema_version": "ra-survey-claim-dependency-graph-v1", "root_dependency_manifest_id": manifest_id, "dependency_manifests": manifests, "source_dependencies": dependencies}
    return {
        "schema_version": SURVEY_CLAIM_REVIEW_V3_SCHEMA,
        "decision_type": "claim_candidate",
        **context.binding,
        "decisions": [{
            "queue_item_id": item["item_id"], "claim_id": "fixture-reviewed-technical-claim",
            "claim_text": "The exact fixture source contains the recorded Method section.",
            "claim_type": "paper_technical", "support_class": "primary_technical_support",
            "review_status": "human_reviewed_passed", "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-13T00:00:00Z", "evidence_note": "Synthetic fixture review for engineering state-transition tests only.",
            "fixture_only": True, "source_dependencies": dependencies, "dependency_manifests": manifests,
            "root_dependency_manifest_id": manifest_id, "dependency_graph_sha256": sha256_bytes(canonical_json_bytes(graph)),
            "paper_ids": item["paper_ids"], "anchor_ids": item["anchor_ids"],
        }],
    }


def _source_envelope(queue_path: Path, output_dir: Path) -> dict[str, Any]:
    context = load_v2_evidence_context(queue_path)
    status = context.validated_source_intake["status"]
    status_raw = context.validated_source_intake["status_bytes"]
    ledger_path = Path(status["outcome_ledger_path"])
    observations = []
    for item_id, identity in sorted(context.source_identities.items()):
        semantic = {
            "schema_version": "ra-survey-source-status-observation-identity-v1",
            "queue_item_id": item_id, "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id, "canonical_identifier": identity.canonical_identifier,
            "aliases": identity.aliases, "source_version": identity.source_version,
            "source_record_path": identity.source_record_path, "source_record_sha256": identity.source_record_sha256,
            "source_record_size_bytes": identity.source_record_size_bytes, "provider": identity.provider,
            "final_url": identity.final_url, "status_source": "synthetic fixture status registry",
            "evidence_class": "recorded_status_check", "observed_at": "2026-07-13T00:00:00Z",
            "checks_performed": SOURCE_CHECKS, "outcome": "checked_clear_for_recorded_checks", "notices": [],
            "fixture_only": True, "claim_support_allowed": False, "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        }
        digest = sha256_bytes(canonical_json_bytes(semantic))
        observations.append({"observation_id": f"so-{digest}", "observation_sha256": digest, **{key: value for key, value in semantic.items() if key != "schema_version"}})
    observation_set = {
        "schema_version": SURVEY_SOURCE_OBSERVATION_SET_SCHEMA, **context.binding,
        "source_intake_status_path": str(context.mission_root / "source_intake" / "phase4_source_intake_status.json"),
        "source_intake_status_sha256": sha256_bytes(status_raw), "source_intake_status_size_bytes": len(status_raw),
        "source_outcome_ledger_path": str(ledger_path), "source_outcome_ledger_sha256": _sha(ledger_path),
        "source_outcome_ledger_size_bytes": ledger_path.stat().st_size, "fixture_only": True,
        "observations": observations, "what_is_not_concluded": SOURCE_OBSERVATION_NONCLAIMS,
        "predecessor_observation_set_id": None, "predecessor_observation_set_manifest_sha256": None,
    }
    binding = preview_source_observation_binding(review_queue_path=queue_path, observation_set=observation_set, output_dir=output_dir)
    by_item = {row["queue_item_id"]: row for row in observations}
    decisions = []
    for item_id, identity in sorted(context.source_identities.items()):
        observation = by_item[item_id]
        decisions.append({
            "queue_item_id": item_id, "stable_metadata_paper_id": identity.stable_metadata_paper_id,
            "source_paper_id": identity.source_paper_id, "observation_set_id": binding["observation_set_id"],
            "observation_set_manifest_sha256": binding["observation_set_manifest_sha256"],
            "observation_id": observation["observation_id"], "observation_sha256": observation["observation_sha256"],
            "source_version": identity.source_version, "reviewer_authority": "human_reviewed_status",
            "decision": "checked_clear", "reviewer": "synthetic-fixture-reviewer",
            "reviewed_at": "2026-07-13T00:01:00Z", "reason": "Synthetic fixture decision for engineering state-transition tests only.",
            "fixture_only": True,
        })
    return {"schema_version": SURVEY_SOURCE_SAFETY_REVIEW_V3_SCHEMA, "decision_type": "source_safety", **context.binding, "observation_set": observation_set, "decisions": decisions}


def _safe_local_argv(mission: Path, *, topic: str = TOPIC, seed: str = SEED) -> list[str]:
    return [
        "survey", "run-public-source-workflow", "--topic", topic, "--seed", seed,
        "--out", str(mission), "--metadata-dir", str(mission / "public_metadata"),
        "--source-status-dir", str(mission / "source_intake"), "--anchor-dir", str(mission / "source_anchors"),
        "--packet-dir", str(mission / "public_source_packet"), "--resume", "--run-safe-local",
    ]


def _setup_reviewed_mission(case_root: Path, *, close_omissions: bool = True, include_workflow: bool = True) -> dict[str, Any]:
    mission = case_root / "mission"
    initial = run_public_source_workflow(topic=TOPIC, seeds=[SEED], output_dir=mission, run_safe_local=True)
    if initial["local_supervisor"]["status"] != "terminal_blocked_public_discovery_confirmation":
        raise AssertionError("initial mission did not stop at confirmation")
    with patch.object(survey_build, "_collect_public_metadata", _metadata_collection):
        built = survey_build.build_survey_evidence_packet(
            topic=TOPIC, seeds=[SEED], output_dir=mission / "public_metadata", mode="public-metadata",
            public_metadata_providers=["arxiv"], max_records=25,
        )
    if built["status"] != "metadata_only_packet":
        raise AssertionError("metadata fixture build failed")
    selected = run_public_source_workflow(
        topic=TOPIC, seeds=[SEED], output_dir=mission, resume=True, confirm_public_discovery=True,
        run_safe_local=True, source_capability=MissionSourceCapability(_fixture_source),
    )
    if selected["local_supervisor"]["status"] != "terminal_blocked_human_review":
        raise AssertionError("fixture source setup did not reach human review")
    queue_path = Path(selected["review_queue_path"])
    queue = json.loads(queue_path.read_text())
    decisions_dir = case_root / "decisions"
    claim_path = decisions_dir / "claims.json"
    source_path = decisions_dir / "source.json"
    omission_path = decisions_dir / "omissions.json"
    workflow_path = decisions_dir / "workflow.json"
    _write_json(claim_path, _claim_envelope(queue_path))
    _write_json(source_path, _source_envelope(queue_path, mission / "reviewed_source_safety"))
    omission_items = [row for row in queue["items"] if row["queue_type"] == "omission_risk"]
    workflow_items = [row for row in queue["items"] if row["queue_type"] == "workflow_blocker"]
    _write_json(omission_path, _bound_decisions(queue_path, queue, "omission_risk", [
        {
            "queue_item_id": item["item_id"], "risk_id": item["risk_id"],
            "decision": "acceptable_omission" if close_omissions else "must_inspect",
            "reason": "Fixture decision is explicit for the current bounded scope.",
            **({"scope_basis": "Closed only for this synthetic local fixture scope."} if close_omissions else {"next_action": "Inspect source references before final prose."}),
            "reviewer": "synthetic-fixture-reviewer", "reviewed_at": "2026-07-13T00:02:00Z",
        }
        for item in omission_items
    ]))
    _write_json(workflow_path, _bound_decisions(queue_path, queue, "workflow_blocker", [
        {
            "queue_item_id": item["item_id"],
            "disposition": "resolved_by_reviewed_evidence",
            "evidence_queue_item_ids": item["required_evidence_queue_item_ids"],
            "rationale": "The exact current fixture decisions structurally address this blocker.",
            "reviewer": "synthetic-fixture-reviewer", "reviewed_at": "2026-07-13T00:03:00Z",
        }
        if item["resolution_class"] != "upstream_repair_required" else {
            "queue_item_id": item["item_id"], "disposition": "remains_open",
            "rationale": "This blocker requires upstream repair.", "next_action": "Repair the upstream artifact.",
            "reviewer": "synthetic-fixture-reviewer", "reviewed_at": "2026-07-13T00:03:00Z",
        }
        for item in workflow_items
    ]))
    imports = []
    with _tripwired(case_root) as import_wires:
        imports.append(_run_cli(["survey", "import-claim-review", "--review-queue", str(queue_path), "--decisions", str(claim_path), "--out", str(mission / "reviewed_claims")], case_root / "claim_import.json"))
        imports.append(_run_cli(["survey", "import-source-safety-review", "--review-queue", str(queue_path), "--decisions", str(source_path), "--out", str(mission / "reviewed_source_safety")], case_root / "source_import.json"))
        imports.append(_run_cli(["survey", "import-omission-review", "--review-queue", str(queue_path), "--decisions", str(omission_path), "--out", str(mission / "reviewed_omissions")], case_root / "omission_import.json"))
        if include_workflow:
            imports.append(_run_cli(["survey", "import-workflow-blocker-review", "--review-queue", str(queue_path), "--decisions", str(workflow_path), "--out", str(mission / "reviewed_workflow_blockers")], case_root / "workflow_import.json"))
    if any(result.return_code != 0 for result in imports):
        raise AssertionError("review fixture import failed")
    if sum(import_wires.as_dict().values()) != 0:
        raise AssertionError("review fixture import reached a forbidden capability")
    setup = {
        "status": "passed", "fixture_only": True, "authenticated_human_review": False,
        "mission": str(mission), "review_queue": str(queue_path), "artifact_set_id": queue["artifact_set_id"],
        "tripwire_counters": import_wires.as_dict(),
    }
    _write_json(case_root / "setup_manifest.json", setup)
    return {
        "mission": mission,
        "queue": queue_path,
        "queue_payload": queue,
        "setup": setup,
        "setup_tripwires": import_wires,
    }


def _forbidden_descendants(mission: Path) -> dict[str, bool]:
    return {
        "reviewed_merge": (mission / "reviewed_evidence" / "reviewed_evidence_status.json").exists(),
        "reviewed_packet": (mission / "reviewed_final_packet" / "reviewed_final_packet.json").exists(),
        "hostile_result": (mission / "hostile_review" / "hostile_review_result.json").exists(),
        "readiness_view": (mission / "hostile_review" / "final_packet_readiness.json").exists(),
    }


def _authority_snapshot(mission: Path) -> dict[str, dict[str, Any]]:
    candidates = [
        mission / ".mission_state" / "CURRENT",
        mission / ".artifact_state" / "CURRENT",
        mission / "reviewed_claims" / "DECISION_CURRENT",
        mission / "reviewed_source_safety" / "OBSERVATION_CURRENT",
        mission / "reviewed_source_safety" / "DECISION_CURRENT",
        mission / "reviewed_omissions" / "DECISION_CURRENT",
        mission / "reviewed_evidence" / "reviewed_evidence_status.json",
        mission / "reviewed_final_packet" / "reviewed_final_packet.json",
        mission / "hostile_review" / "hostile_review_result.json",
        mission / "hostile_review" / "final_packet_readiness.json",
    ]
    result: dict[str, dict[str, Any]] = {}
    for path in candidates:
        relative = str(path.relative_to(mission))
        if path.is_symlink():
            result[relative] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            result[relative] = {"kind": "file", "sha256": _sha(path), "size_bytes": path.stat().st_size}
        else:
            result[relative] = {"kind": "absent"}
    return result


def _selected_authority_ids(mission: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_set_id": payload.get("artifact_state", {}).get("artifact_set_id"),
        "claim_decision_set_id": json.loads((mission / "reviewed_claims" / "DECISION_CURRENT").read_text())["decision_set_id"],
        "source_observation_set_id": json.loads((mission / "reviewed_source_safety" / "OBSERVATION_CURRENT").read_text())["observation_set_id"],
        "source_decision_set_id": json.loads((mission / "reviewed_source_safety" / "DECISION_CURRENT").read_text())["decision_set_id"],
        "omission_decision_set_id": json.loads((mission / "reviewed_omissions" / "DECISION_CURRENT").read_text())["decision_set_id"],
    }


def _supervisor_observed(result: CliResult) -> dict[str, Any]:
    return result.payload.get("local_supervisor") or {}


def _combined_tripwires(*values: Tripwires) -> dict[str, int]:
    rows = [value.as_dict() for value in values]
    return {key: sum(row[key] for row in rows) for key in rows[0]}


def _record_negative(
    case_root: Path,
    *,
    expected: dict[str, Any],
    observed: dict[str, Any],
    tripwires: Tripwires,
    passed: bool,
    setup_tripwires: Tripwires | None = None,
    authority_before: dict[str, dict[str, Any]],
    mission_tree_before: dict[str, dict[str, Any]],
    allowed_changed_prefixes: tuple[str, ...],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counters = _combined_tripwires(*([setup_tripwires] if setup_tripwires else []), tripwires)
    mission_tree_after = _tree(case_root / "mission")
    mutation = _mutation_contract(mission_tree_before, mission_tree_after, allowed_changed_prefixes)
    case_passed = passed and mutation["passed"] and sum(counters.values()) == 0
    row = {
        "case_id": case_root.name,
        "setup_status": "passed",
        "status": "passed" if case_passed else "failed",
        "expected": expected,
        "observed": observed,
        "tripwire_counters": counters,
        "forbidden_call_count": sum(counters.values()),
        "cli_records": [
            {
                "evidence": str(path.relative_to(case_root)),
                "argv": payload.get("argv"),
                "return_code": payload.get("return_code"),
            }
            for path in sorted(case_root.glob("*cli.json"))
            for payload in [json.loads(path.read_text())]
        ],
        "authoritative_before": authority_before,
        "authoritative_after": _authority_snapshot(case_root / "mission"),
        "mission_mutation_contract": mutation,
        **(extra or {}),
    }
    _write_json(case_root / "case_result.json", row)
    return row


def _case_missing_confirmation(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    mission = root / "mission"
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        result = _run_cli(["survey", "run-public-source-workflow", "--topic", TOPIC, "--seed", SEED, "--out", str(mission), "--run-safe-local"], root / "cli.json")
    supervisor = _supervisor_observed(result)
    expected = {"return_code": 0, "status": "terminal_blocked_public_discovery_confirmation", "action": "public_metadata", "reason": "provider_metadata_is_not_a_phase5_local_action"}
    observed = {"return_code": result.return_code, "status": supervisor.get("status"), "action": supervisor.get("terminal_action_id"), "reason": supervisor.get("terminal_reason")}
    descendants = _forbidden_descendants(mission)
    passed = observed == expected and not any(descendants.values()) and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".mission_state", "mission_control.json", "mission_plan.json", "next_action.json", "offline_skeleton"), passed=passed, extra={"forbidden_descendants": descendants, "mission_tree": _tree(mission)})


def _case_identity(root: Path, *, changed_topic: bool) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root)
    mission = setup["mission"]
    current = mission / ".mission_state" / "CURRENT"
    before = current.read_bytes()
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    argv = _safe_local_argv(mission, topic="Changed topic" if changed_topic else TOPIC, seed=SEED if changed_topic else "arxiv:2201.12220v4")
    with _tripwired(root) as wires:
        result = _run_cli(argv, root / "cli.json")
    expected = {"return_code": 1, "blocked_reason": "mission_identity_mismatch"}
    observed = {"return_code": result.return_code, "blocked_reason": result.payload.get("blocked_reason")}
    passed = observed == expected and current.read_bytes() == before and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(), passed=passed, extra={"current_unchanged": current.read_bytes() == before, "forbidden_descendants": _forbidden_descendants(mission)})


def _case_open_omission(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root, close_omissions=False)
    mission = setup["mission"]
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        result = _run_cli(_safe_local_argv(mission), root / "cli.json")
    supervisor = _supervisor_observed(result)
    expected = {"return_code": 0, "status": "terminal_blocked_reviewed_evidence", "action": "resolve_reviewed_evidence_blockers", "reason": "reviewed_evidence_has_open_outcomes"}
    observed = {"return_code": result.return_code, "status": supervisor.get("status"), "action": supervisor.get("terminal_action_id"), "reason": supervisor.get("terminal_reason")}
    descendants = _forbidden_descendants(mission)
    passed = observed == expected and descendants["reviewed_merge"] and not descendants["reviewed_packet"] and not descendants["hostile_result"] and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".mission_state", "mission_control.json", "mission_plan.json", "next_action.json", "reviewed_evidence"), passed=passed, extra={"forbidden_descendants": descendants})


def _case_missing_workflow(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root, include_workflow=False)
    mission = setup["mission"]
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        result = _run_cli(_safe_local_argv(mission), root / "cli.json")
    supervisor = _supervisor_observed(result)
    expected = {"return_code": 0, "status": "terminal_blocked_human_review", "action": "import_reviewed_workflow_blockers", "reason": "explicit_review_input_is_required"}
    observed = {"return_code": result.return_code, "status": supervisor.get("status"), "action": supervisor.get("terminal_action_id"), "reason": supervisor.get("terminal_reason")}
    descendants = _forbidden_descendants(mission)
    passed = observed == expected and not any(descendants.values()) and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".mission_state", "mission_control.json", "mission_plan.json", "next_action.json"), passed=passed, extra={"forbidden_descendants": descendants})


def _case_noncanonical_root(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root)
    mission = setup["mission"]
    external = root / "external_reviewed_claims"
    external.mkdir()
    shutil.copy2(mission / "reviewed_claims" / "DECISION_CURRENT", external / "DECISION_CURRENT")
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    argv = [*_safe_local_argv(mission), "--reviewed-claims-dir", str(external)]
    with _tripwired(root) as wires:
        result = _run_cli(argv, root / "cli.json")
    supervisor = _supervisor_observed(result)
    expected = {"return_code": 0, "status": "terminal_blocked_invalid_artifact", "action": "terminal_blocked_invalid_artifact", "reason": "noncanonical_safe_local_reviewed_claims_root"}
    observed = {"return_code": result.return_code, "status": supervisor.get("status"), "action": supervisor.get("terminal_action_id"), "reason": supervisor.get("terminal_reason")}
    descendants = _forbidden_descendants(mission)
    passed = observed == expected and not any(descendants.values()) and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".mission_state", "mission_control.json", "mission_plan.json", "next_action.json"), passed=passed, extra={"forbidden_descendants": descendants, "external_tree": _tree(external)})


def _case_malformed_merge(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root)
    mission = setup["mission"]
    merge_dir = mission / "reviewed_evidence"
    merge_dir.mkdir()
    (merge_dir / "reviewed_evidence_status.json").write_text("{")
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        result = _run_cli(_safe_local_argv(mission), root / "cli.json")
    supervisor = _supervisor_observed(result)
    expected = {"return_code": 0, "status": "terminal_blocked_invalid_artifact", "action": "merge_reviewed_evidence", "reason": "reviewed_evidence_shape_is_not_repairable"}
    observed = {"return_code": result.return_code, "status": supervisor.get("status"), "action": supervisor.get("terminal_action_id"), "reason": supervisor.get("terminal_reason")}
    descendants = _forbidden_descendants(mission)
    passed = observed == expected and not descendants["reviewed_packet"] and not descendants["hostile_result"] and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".mission_state", "mission_control.json", "mission_plan.json", "next_action.json"), passed=passed, extra={"forbidden_descendants": descendants})


def _case_symlinked_packet(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root)
    mission = setup["mission"]
    merge = merge_reviewed_evidence(
        review_queue_path=setup["queue"],
        reviewed_claims_path=next((mission / "reviewed_claims" / "decision_sets").glob("*/reviewed_claims.json")),
        reviewed_source_safety_path=next((mission / "reviewed_source_safety" / "decision_sets").glob("*/reviewed_source_safety.json")),
        reviewed_omissions_path=next((mission / "reviewed_omissions" / "decision_sets").glob("*/reviewed_omission_risks.json")),
        reviewed_workflow_blockers_path=mission / "reviewed_workflow_blockers" / "reviewed_workflow_blockers.json",
        output_dir=mission / "reviewed_evidence",
    )
    if merge.get("status") != "reviewed_evidence_complete":
        raise AssertionError("symlink case merge setup failed")
    packet_dir = mission / "reviewed_final_packet"
    packet_dir.mkdir()
    outside = root / "outside_packet.json"
    outside.write_bytes(pretty_json_bytes({"schema_version": "outside-fixture-v1"}))
    (packet_dir / "reviewed_final_packet.json").symlink_to(outside)
    before = outside.read_bytes()
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        result = _run_cli(_safe_local_argv(mission), root / "cli.json")
    supervisor = _supervisor_observed(result)
    expected = {"return_code": 0, "status": "terminal_blocked_invalid_artifact", "action": "terminal_blocked_invalid_artifact", "reason": "unsafe_artifact_file"}
    observed = {"return_code": result.return_code, "status": supervisor.get("status"), "action": supervisor.get("terminal_action_id"), "reason": supervisor.get("terminal_reason")}
    descendants = _forbidden_descendants(mission)
    passed = (
        observed == expected
        and outside.read_bytes() == before
        and not descendants["hostile_result"]
        and not descendants["readiness_view"]
        and sum(wires.as_dict().values()) == 0
    )
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".mission_state", "mission_control.json", "mission_plan.json", "next_action.json"), passed=passed, extra={"outside_unchanged": outside.read_bytes() == before, "forbidden_descendants": descendants})


def _case_upstream_change(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root, close_omissions=False)
    mission = setup["mission"]
    old_queue = setup["queue"]
    retained = {
        str(path.relative_to(mission)): path.read_bytes()
        for family in ("reviewed_claims", "reviewed_source_safety", "reviewed_omissions", "reviewed_workflow_blockers")
        for path in (mission / family).rglob("*.json")
    }
    claim_path = mission / "public_source_packet" / "claim_support.json"
    claim_payload = json.loads(claim_path.read_text())
    claim_payload["claim_candidates"][0]["next_action"] = "Review the changed Phase 10 claim semantics."
    _write_json(claim_path, claim_payload)
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        result = _run_cli([value for value in _safe_local_argv(mission) if value != "--run-safe-local"], root / "cli.json")
    new_queue = Path(result.payload["review_queue_path"])
    mission_payload = json.loads((mission / "mission_control.json").read_text())
    stale = {name: mission_payload["reviewed_artifacts"][name]["lineage_status"] for name in ("reviewed_claims", "reviewed_source_safety", "reviewed_omissions", "reviewed_workflow_blockers")}
    retained_ok = all((mission / relative).read_bytes() == raw for relative, raw in retained.items())
    expected = {"return_code": 0, "next_action": "import_reviewed_claims", "queue_changed": True, "all_lineage": "stale_lineage"}
    observed = {"return_code": result.return_code, "next_action": result.payload.get("next_action", {}).get("action_id"), "queue_changed": new_queue != old_queue, "all_lineage": "stale_lineage" if set(stale.values()) == {"stale_lineage"} else stale}
    passed = observed == expected and retained_ok and not any(_forbidden_descendants(mission).values()) and sum(wires.as_dict().values()) == 0
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, setup_tripwires=setup["setup_tripwires"], authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(".artifact_state", ".mission_state", "mission_control.json", "next_action.json"), passed=passed, extra={"retained_decision_bytes": retained_ok, "old_queue": str(old_queue), "new_queue": str(new_queue), "forbidden_descendants": _forbidden_descendants(mission)})


def _legacy_fixture(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    mission = root / "mission"
    mission.mkdir()
    manager = MissionStateManager(
        output_dir=mission, topic="Phase 10 legacy fixture", seeds=["arxiv:0000.00004"],
        confirm_public_discovery=False, resume=False, force=False,
        now=lambda: "2026-07-13T00:00:00+00:00", nonce_factory=lambda: "404142434445464748494a4b4c4d4e4f",
        mission_id_factory=lambda: "44444444-4444-4444-8444-444444444444",
    )
    manager.begin()
    snapshot = manager.commit(
        {"status": "ready_for_local_continuation", "created_at": "2026-07-13T00:00:00+00:00", "updated_at": "2026-07-13T00:00:00+00:00", "topic": "Phase 10 legacy fixture", "seeds": ["arxiv:0000.00004"], "output_dir": str(mission)},
        {"schema_version": "ra-survey-public-source-next-action-v1", "status": "fixture", "mission_status": "ready_for_local_continuation", "action_id": "fixture"},
    )
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
        _write_json(packet / name, payload)
    coverage = {
        name: {"schema_version": f"legacy-{name}-v1", "status": "fixture", "rows": [], "what_is_not_concluded": ["literature completeness"]}
        for name in COVERAGE_FILES
    }
    claim = semantic_item(queue_type="claim_candidate", source_id="claim-1", semantic_fields={"priority": "high", "status": "review_required"})
    queue = {"status": "review_required", "topic": "Phase 10 legacy fixture", "items": [claim], "queue_counts": {}, "allowed_item_statuses": ["review_required"], "forbidden_promotions": ["review is not readiness"], "what_is_not_concluded": ["scientific correctness"]}
    selected = ArtifactStateManager(
        mission_root=mission, mission_id=snapshot.contract["mission_id"], mission_fingerprint=snapshot.contract["mission_fingerprint"],
        mission_anchor_generation_id=snapshot.current_pointer["generation_id"], nonce_factory=lambda: "505152535455565758595a5b5c5d5e5f",
    ).compose_and_select(packet_dir=packet, coverage_payloads=coverage, review_queue_payload=queue)
    reviewed = {}
    for name in ("reviewed_claims", "reviewed_source_safety", "reviewed_omissions", "reviewed_workflow_blockers"):
        path = mission / name / f"{name}.json"
        _write_json(path, {"schema_version": f"legacy-{name}-v1"})
        reviewed[name] = path
    return {"mission": mission, "queue": selected.review_queue_path, "packet": packet, **reviewed}


def _case_legacy(root: Path) -> dict[str, Any]:
    fixture = _legacy_fixture(root)
    mission = fixture["mission"]
    synthetic = mission / "reviewed_final_packet" / "reviewed_final_packet.json"
    _write_json(synthetic, {"schema_version": "ra-survey-reviewed-final-packet-v1", "status": "ready_for_hostile_review"})
    before = synthetic.read_bytes()
    authority_before = _authority_snapshot(mission)
    mission_tree_before = _tree(mission)
    with _tripwired(root) as wires:
        merge_cli = _run_cli([
            "survey", "merge-reviewed-evidence", "--review-queue", str(fixture["queue"]),
            "--reviewed-claims", str(fixture["reviewed_claims"]),
            "--reviewed-source-safety", str(fixture["reviewed_source_safety"]),
            "--reviewed-omissions", str(fixture["reviewed_omissions"]),
            "--reviewed-workflow-blockers", str(fixture["reviewed_workflow_blockers"]),
            "--out", str(mission / "reviewed_evidence"),
        ], root / "merge_cli.json")
        compose_cli = _run_cli([
            "survey", "compose-reviewed-final-packet", "--mission-root", str(mission),
            "--review-queue", str(fixture["queue"]), "--packet-dir", str(fixture["packet"]),
            "--anchor-dir", str(root / "anchors"), "--out", str(mission / "reviewed_final_packet"),
        ], root / "compose_cli.json")
        hostile_cli = _run_cli([
            "survey", "hostile-review", "--reviewed-final-packet", str(synthetic),
            "--mission-root", str(mission), "--review-queue", str(fixture["queue"]),
            "--packet-dir", str(fixture["packet"]), "--anchor-dir", str(root / "anchors"),
            "--out", str(mission / "hostile_review"),
        ], root / "hostile_cli.json")
    expected = {"merge": "legacy_evidence_authority", "compose": "legacy_evidence_authority", "hostile": "legacy_evidence_authority"}
    observed = {"merge": merge_cli.payload.get("blocked_reason"), "compose": compose_cli.payload.get("blocked_reason"), "hostile": hostile_cli.payload.get("blocked_reason")}
    descendants = _forbidden_descendants(mission)
    passed = observed == expected and synthetic.read_bytes() == before and not descendants["reviewed_merge"] and not descendants["hostile_result"] and not descendants["readiness_view"]
    return _record_negative(root, expected=expected, observed=observed, tripwires=wires, authority_before=authority_before, mission_tree_before=mission_tree_before, allowed_changed_prefixes=(), passed=passed, extra={"declared_synthetic_v1_packet": str(synthetic), "synthetic_input_unchanged": synthetic.read_bytes() == before, "forbidden_descendants": descendants})


def _positive(root: Path) -> dict[str, Any]:
    setup = _setup_reviewed_mission(root)
    mission = setup["mission"]
    external = [mission / name for name in ("public_metadata", "source_intake", "source_anchors", "public_source_packet")]
    external_before = {str(path.relative_to(mission)): _tree(path) for path in external}
    with _tripwired(root) as wires:
        first = _run_cli(_safe_local_argv(mission), root / "first_cli.json")
        authoritative_paths = [
            mission / "reviewed_evidence" / "reviewed_evidence_status.json",
            mission / "reviewed_final_packet" / "reviewed_final_packet.json",
            mission / "hostile_review" / "hostile_review_result.json",
            mission / "hostile_review" / "final_packet_readiness.json",
            mission / ".artifact_state" / "CURRENT",
            mission / "reviewed_claims" / "DECISION_CURRENT",
            mission / "reviewed_source_safety" / "OBSERVATION_CURRENT",
            mission / "reviewed_source_safety" / "DECISION_CURRENT",
            mission / "reviewed_omissions" / "DECISION_CURRENT",
        ]
        before = {str(path.relative_to(mission)): path.read_bytes() for path in authoritative_paths}
        first_selected_ids = _selected_authority_ids(mission, first.payload)
        second = _run_cli(_safe_local_argv(mission), root / "second_cli.json")
    after = {str(path.relative_to(mission)): path.read_bytes() for path in authoritative_paths}
    second_selected_ids = _selected_authority_ids(mission, second.payload)
    first_supervisor = _supervisor_observed(first)
    second_supervisor = _supervisor_observed(second)
    expected_stages = ["merge_reviewed_evidence", "compose_reviewed_final_packet", "run_hostile_review"]
    expected_terminal = {
        "status": "terminal_ready_for_reviewed_prose_within_recorded_scope",
        "action": "terminal_ready_for_reviewed_prose",
        "reason": "authoritative_hostile_result_is_clear_within_recorded_scope",
        "classification": "READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE",
    }
    first_terminal = {
        "status": first_supervisor.get("status"),
        "action": first_supervisor.get("terminal_action_id"),
        "reason": first_supervisor.get("terminal_reason"),
        "classification": first_supervisor.get("readiness_classification"),
    }
    second_terminal = {
        "status": second_supervisor.get("status"),
        "action": second_supervisor.get("terminal_action_id"),
        "reason": second_supervisor.get("terminal_reason"),
        "classification": second_supervisor.get("readiness_classification"),
    }
    checks = {
        "first_return_code": first.return_code == 0,
        "first_exact_terminal": first_terminal == expected_terminal,
        "first_stages": [row["stage_id"] for row in first_supervisor.get("transition_history", [])] == expected_stages,
        "second_return_code": second.return_code == 0,
        "second_exact_terminal": second_terminal == expected_terminal,
        "second_empty_history": second_supervisor.get("transition_history") == [],
        "selected_ids_identical": first_selected_ids == second_selected_ids,
        "artifact_set_matches_fixture_queue": first_selected_ids["artifact_set_id"] == setup["queue_payload"]["artifact_set_id"],
        "authoritative_bytes_identical": before == after,
        "external_roots_unchanged": external_before == {str(path.relative_to(mission)): _tree(path) for path in external},
        "zero_forbidden_calls": sum(wires.as_dict().values()) == 0,
    }
    counters = _combined_tripwires(setup["setup_tripwires"], wires)
    checks["zero_forbidden_calls"] = sum(counters.values()) == 0
    record = {
        "case_id": "positive",
        "status": "passed" if all(checks.values()) else "failed",
        "setup_status": "passed", "fixture_only": True, "authenticated_human_review": False,
        "checks": checks,
        "expected_terminal": expected_terminal,
        "first_terminal": first_terminal,
        "second_terminal": second_terminal,
        "first_selected_ids": first_selected_ids,
        "second_selected_ids": second_selected_ids,
        "authoritative_hashes": {relative: hashlib.sha256(raw).hexdigest() for relative, raw in after.items()},
        "tripwire_counters": counters, "forbidden_call_count": sum(counters.values()),
        "mission_tree": _tree(mission), "what_is_not_concluded": NONCLAIMS,
    }
    _write_json(root / "case_result.json", record)
    return record


def run_validation(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError(f"output root already exists: {output_dir}")
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()
    (output_dir / "logs").mkdir()
    positive = _positive(output_dir / "positive")
    negative_root = output_dir / "negative"
    negative_root.mkdir()
    runners: dict[str, Callable[[Path], dict[str, Any]]] = {
        "missing_public_confirmation": _case_missing_confirmation,
        "changed_topic_resume": lambda path: _case_identity(path, changed_topic=True),
        "changed_seed_resume": lambda path: _case_identity(path, changed_topic=False),
        "open_omission_review": _case_open_omission,
        "missing_current_workflow_review": _case_missing_workflow,
        "noncanonical_reviewed_claim_root": _case_noncanonical_root,
        "malformed_reviewed_merge": _case_malformed_merge,
        "symlinked_reviewed_packet": _case_symlinked_packet,
        "upstream_packet_change": _case_upstream_change,
        "legacy_v1_promotion": _case_legacy,
    }
    negatives = [runners[case_id](negative_root / case_id) for case_id in NEGATIVE_CASE_IDS]
    static_audit = _stale_path_audit(output_dir)
    _write_json(output_dir / "e2e_static_audit.json", static_audit)
    inventory = _artifact_inventory(output_dir)
    _write_json(output_dir / "e2e_artifact_inventory.json", inventory)
    forbidden_calls = positive["forbidden_call_count"] + sum(row["forbidden_call_count"] for row in negatives)
    summary = {
        "schema_version": SCHEMA,
        "status": (
            "passed"
            if positive["status"] == "passed"
            and all(row["status"] == "passed" for row in negatives)
            and forbidden_calls == 0
            and static_audit["status"] == "passed"
            else "failed"
        ),
        "case_ids": ["positive", *NEGATIVE_CASE_IDS],
        "positive": {"status": positive["status"], "evidence": "positive/case_result.json"},
        "negative_cases": [{"case_id": row["case_id"], "status": row["status"], "evidence": f"negative/{row['case_id']}/case_result.json"} for row in negatives],
        "persistent_positive_count": 1,
        "persistent_negative_count": len(negatives),
        "forbidden_call_count": forbidden_calls,
        "static_audit": "e2e_static_audit.json",
        "artifact_inventory": {
            "path": "e2e_artifact_inventory.json",
            "sha256": _sha(output_dir / "e2e_artifact_inventory.json"),
            "artifact_count": inventory["artifact_count"],
            "tree_sha256": inventory["tree_sha256"],
        },
        "fixture_only": True,
        "authenticated_human_review": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    _write_json(output_dir / "e2e_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the M16 Phase 10 deterministic offline E2E matrix.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = run_validation(args.out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
