from __future__ import annotations

import json
import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    validate_generation_ancestor_readonly,
    validate_generation_binding_readonly,
)


ARTIFACT_GENESIS_SCHEMA = "ra-survey-artifact-state-genesis-v1"
ARTIFACT_CURRENT_SCHEMA = "ra-survey-artifact-state-current-v1"
ARTIFACT_SET_MANIFEST_SCHEMA = "ra-survey-artifact-set-manifest-v1"
ARTIFACT_SET_IDENTITY_SCHEMA = "ra-survey-artifact-set-identity-v1"
REVIEW_QUEUE_SCHEMA = "ra-survey-public-source-review-queue-v2"
COVERAGE_MANIFEST_SCHEMA = "ra-survey-coverage-ledger-manifest-v2"
WORKFLOW_BLOCKER_IDENTITY_SCHEMA = "ra-survey-workflow-blocker-identity-v1"

SET_ID_RE = re.compile(r"^s-[0-9a-f]{64}$")
GENERATION_ID_RE = re.compile(r"^g[0-9]{8}-[0-9a-f]{16}$")
GENESIS_TEMP_RE = re.compile(r"^\.GENESIS\.[0-9a-f]{32}\.tmp$")
CURRENT_TEMP_RE = re.compile(r"^\.CURRENT\.[0-9a-f]{32}\.tmp$")
STAGING_RE = re.compile(r"^\.staging-(s-[0-9a-f]{64})-([0-9a-f]{32})$")

PACKET_COVERAGE_FILES = {
    "candidate_ledger": "candidate_ledger.json",
    "citation_map": "citation_map.json",
    "paper_classifications": "paper_classifications.json",
    "omission_risk": "omission_risk.json",
}
PACKET_QUEUE_FILES = {
    "claim_support": "claim_support.json",
    "source_safety_status": "source_safety_status.json",
    "build_manifest": "build_manifest.json",
}
COVERAGE_FILES = (
    "backward_snowball.json",
    "citation_venue_metadata.json",
    "forward_snowball.json",
    "omitted_paper_risks.json",
    "paper_classifications.json",
)
IDENTITY_FIELDS = {
    "mission_id",
    "mission_fingerprint",
    "mission_anchor_generation_id",
    "artifact_set_id",
}
QUEUE_DERIVED_FIELDS = {
    *IDENTITY_FIELDS,
    "schema_version",
    "packet_input_digests",
    "coverage_semantic_digests",
    "coverage_exact_digests",
    "coverage_lineage_sha256",
    "queue_semantic_sha256",
    "queue_counts",
    "created_at",
    "updated_at",
    "source_packet_dir",
    "input_paths",
}
ITEM_DERIVED_FIELDS = {
    "item_id",
    "semantic_item_sha256",
    "queue_type",
    "source_id",
    "source_artifact",
    "source_path",
    "row_index",
    "created_at",
    "updated_at",
}


@dataclass(frozen=True)
class ArtifactSetSnapshot:
    mission_root: Path
    artifact_set_id: str
    set_dir: Path
    review_queue_path: Path
    coverage_dir: Path
    manifest: dict[str, Any]
    recovery: dict[str, Any]


def canonical_pretty_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise MissionStateError("invalid_artifact_json", str(exc)) from exc
    return (text + "\n").encode("utf-8")


def normalized_identity_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise MissionStateError("invalid_semantic_identity", f"{field} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise MissionStateError("invalid_semantic_identity", f"{field} must not be empty")
    return normalized


def workflow_blocker_source_id(value: Any) -> str:
    normalized = normalized_identity_text(value, field="workflow blocker")
    return sha256_bytes(canonical_json_bytes({
        "schema_version": WORKFLOW_BLOCKER_IDENTITY_SCHEMA,
        "normalized_blocker": normalized,
    }))


def semantic_item(
    *,
    queue_type: str,
    source_id: str,
    semantic_fields: dict[str, Any],
) -> dict[str, Any]:
    queue_type = normalized_identity_text(queue_type, field="queue_type")
    source_id = normalized_identity_text(source_id, field="source_id")
    projection = {
        "schema_version": "ra-survey-review-queue-item-semantic-v1",
        "queue_type": queue_type,
        "source_id": source_id,
        "semantic_fields": semantic_fields,
    }
    digest = sha256_bytes(canonical_json_bytes(projection))
    return {
        **semantic_fields,
        "item_id": f"{queue_type}-{digest[:24]}",
        "queue_type": queue_type,
        "source_id": source_id,
        "semantic_item_sha256": digest,
    }


def semantic_item_projection(item: dict[str, Any]) -> dict[str, Any]:
    queue_type = normalized_identity_text(item.get("queue_type"), field="queue_type")
    source_id = normalized_identity_text(item.get("source_id"), field="source_id")
    semantic_fields = {
        key: value
        for key, value in item.items()
        if key not in ITEM_DERIVED_FIELDS
    }
    return {
        "schema_version": "ra-survey-review-queue-item-semantic-v1",
        "queue_type": queue_type,
        "source_id": source_id,
        "semantic_fields": semantic_fields,
    }


def validate_semantic_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise MissionStateError("invalid_queue_items", "queue items must be objects")
    keys: set[tuple[str, str]] = set()
    ids: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        queue_type = normalized_identity_text(item.get("queue_type"), field="queue_type")
        source_id = normalized_identity_text(item.get("source_id"), field="source_id")
        key = (queue_type, source_id)
        if key in keys:
            raise MissionStateError("duplicate_queue_semantic_key", f"duplicate queue semantic key: {key}")
        keys.add(key)
        item_id = item.get("item_id")
        digest = item.get("semantic_item_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise MissionStateError("invalid_queue_item_digest", "semantic_item_sha256 must be lowercase SHA-256")
        expected_digest = sha256_bytes(canonical_json_bytes(semantic_item_projection(item)))
        if digest != expected_digest:
            raise MissionStateError("queue_item_digest_mismatch", "queue item semantic digest is invalid")
        if item_id != f"{queue_type}-{digest[:24]}" or item_id in ids:
            raise MissionStateError("queue_item_id_collision", "queue item ID is invalid or collides")
        ids.add(item_id)
        result.append(dict(item))
    expected = sorted(result, key=lambda row: (row["queue_type"], row["source_id"], row["semantic_item_sha256"]))
    if result != expected:
        raise MissionStateError("unsorted_queue_items", "queue items must be semantic-key sorted")
    return result


class ArtifactStateManager:
    def __init__(
        self,
        *,
        mission_root: Path,
        mission_id: str,
        mission_fingerprint: str,
        mission_anchor_generation_id: str,
        nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
        crash_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.mission_root = mission_root.resolve()
        self.mission_id = _require_string(mission_id, "mission_id")
        self.mission_fingerprint = _require_hex(mission_fingerprint, 64, "mission_fingerprint")
        if GENERATION_ID_RE.fullmatch(mission_anchor_generation_id) is None:
            raise MissionStateError("invalid_anchor_generation", "mission anchor generation ID is invalid")
        self.mission_anchor_generation_id = mission_anchor_generation_id
        self.nonce_factory = nonce_factory
        self.crash_hook = crash_hook
        self.state_dir = self.mission_root / ".artifact_state"
        self.sets_dir = self.state_dir / "sets"
        self.genesis_path = self.state_dir / "GENESIS"
        self.current_path = self.state_dir / "CURRENT"

    def ensure_genesis(self) -> dict[str, Any]:
        self._validate_root_shape(allow_absent=True)
        if self.state_dir.exists():
            if self.current_path.exists() and not self.genesis_path.exists():
                raise MissionStateError("missing_artifact_genesis", "artifact CURRENT exists without artifact GENESIS")
            if (
                not self.genesis_path.exists()
                and any(CURRENT_TEMP_RE.fullmatch(path.name) for path in self.state_dir.iterdir())
            ):
                raise MissionStateError(
                    "artifact_current_temp_without_genesis",
                    "artifact CURRENT temp residue cannot predate artifact GENESIS",
                )
            if self.current_path.exists() and not self.sets_dir.exists():
                raise MissionStateError("corrupt_selected_lineage", "CURRENT exists without the artifact sets directory")
            if self.genesis_path.exists() and not self.sets_dir.exists():
                raise MissionStateError("corrupt_artifact_state", "artifact GENESIS exists without the artifact sets directory")
            if (
                not self.genesis_path.exists()
                and self.sets_dir.is_dir()
                and any(self.sets_dir.iterdir())
            ):
                raise MissionStateError(
                    "artifact_sets_without_genesis",
                    "nonempty artifact sets cannot predate artifact-state GENESIS",
                )
        else:
            self.state_dir.mkdir()
        if not self.sets_dir.exists():
            self.sets_dir.mkdir()
        _fsync_directory(self.state_dir)
        _fsync_directory(self.mission_root)
        expected = self._genesis_payload()
        if self.genesis_path.exists() or self.genesis_path.is_symlink():
            actual, raw = _read_canonical(self.genesis_path, "artifact-state GENESIS")
            _validate_genesis_payload(actual)
            if actual != expected:
                raise MissionStateError("artifact_genesis_collision", "artifact-state GENESIS differs from mission authority")
            return actual
        self._atomic_write(self.genesis_path, canonical_json_bytes(expected), kind="GENESIS")
        return expected

    def compose_and_select(
        self,
        *,
        packet_dir: Path,
        coverage_payloads: dict[str, dict[str, Any]],
        review_queue_payload: dict[str, Any],
    ) -> ArtifactSetSnapshot:
        _validate_v2_coverage_replay(
            mission_root=self.mission_root,
            mission_id=self.mission_id,
            mission_fingerprint=self.mission_fingerprint,
            mission_anchor_generation_id=self.mission_anchor_generation_id,
            coverage_payloads=coverage_payloads,
        )
        self.ensure_genesis()
        selected = self.load_current(required=False)
        packet_dir = packet_dir.resolve()
        coverage_packet_digests = _digest_map(packet_dir, PACKET_COVERAGE_FILES)
        queue_packet_digests = _digest_map(packet_dir, PACKET_QUEUE_FILES)
        packet_digests = dict(sorted({**coverage_packet_digests, **queue_packet_digests}.items()))
        coverage_semantic_digests = _coverage_semantic_digests(
            coverage_payloads,
            packet_input_digests=coverage_packet_digests,
        )
        queue_semantic_sha256 = _queue_semantic_sha256(
            mission_id=self.mission_id,
            mission_fingerprint=self.mission_fingerprint,
            mission_anchor_generation_id=self.mission_anchor_generation_id,
            packet_input_digests=queue_packet_digests,
            coverage_semantic_digests=coverage_semantic_digests,
            queue=review_queue_payload,
        )
        identity = {
            "schema_version": ARTIFACT_SET_IDENTITY_SCHEMA,
            "mission_id": self.mission_id,
            "mission_fingerprint": self.mission_fingerprint,
            "mission_anchor_generation_id": self.mission_anchor_generation_id,
            "packet_input_digests": packet_digests,
            "coverage_semantic_digests": coverage_semantic_digests,
            "queue_semantic_sha256": queue_semantic_sha256,
        }
        semantic_digest = sha256_bytes(canonical_json_bytes(identity))
        set_id = f"s-{semantic_digest}"
        final_dir = self.sets_dir / set_id
        final_payloads = self._final_payloads(
            set_id=set_id,
            packet_digests=packet_digests,
            coverage_packet_digests=coverage_packet_digests,
            queue_packet_digests=queue_packet_digests,
            coverage_payloads=coverage_payloads,
            review_queue_payload=review_queue_payload,
            coverage_semantic_digests=coverage_semantic_digests,
            queue_semantic_sha256=queue_semantic_sha256,
            semantic_digest=semantic_digest,
        )
        if final_dir.exists() or final_dir.is_symlink():
            snapshot = self._validate_set(final_dir, expected_id=set_id)
            if snapshot.manifest["artifact_set_semantic_sha256"] != semantic_digest:
                raise MissionStateError("artifact_set_collision", "existing set does not match semantic identity")
        else:
            self._write_set(final_dir, final_payloads)
            snapshot = self._validate_set(final_dir, expected_id=set_id)
        if selected is None or selected.artifact_set_id != set_id:
            pointer = {
                "schema_version": ARTIFACT_CURRENT_SCHEMA,
                "artifact_set_id": set_id,
                "artifact_set_manifest_sha256": sha256_file(final_dir / "artifact_set_manifest.json"),
            }
            self._atomic_write(self.current_path, canonical_json_bytes(pointer), kind="CURRENT")
        return self.load_current(required=True)

    def load_current(self, *, required: bool = True) -> ArtifactSetSnapshot | None:
        self._validate_root_shape(allow_absent=not required)
        recovery = self._recovery_report()
        if not self.current_path.exists():
            if required:
                raise MissionStateError("missing_artifact_current", "artifact-state CURRENT is required")
            return None
        genesis, _ = _read_canonical(self.genesis_path, "artifact-state GENESIS")
        _validate_genesis_payload(genesis)
        if genesis != self._genesis_payload():
            raise MissionStateError("foreign_artifact_genesis", "artifact-state GENESIS does not match active mission")
        pointer, raw = _read_canonical(self.current_path, "artifact-state CURRENT")
        _require_exact_keys(pointer, {"schema_version", "artifact_set_id", "artifact_set_manifest_sha256"}, "artifact-state CURRENT")
        if pointer["schema_version"] != ARTIFACT_CURRENT_SCHEMA:
            raise MissionStateError("invalid_artifact_current", "artifact-state CURRENT schema is unsupported")
        set_id = pointer["artifact_set_id"]
        if not isinstance(set_id, str) or SET_ID_RE.fullmatch(set_id) is None:
            raise MissionStateError("invalid_artifact_set_id", "artifact set ID is invalid")
        _require_hex(pointer["artifact_set_manifest_sha256"], 64, "artifact set manifest SHA-256")
        set_dir = _safe_child_directory(self.sets_dir, set_id)
        snapshot = self._validate_set(set_dir, expected_id=set_id)
        manifest_raw = (set_dir / "artifact_set_manifest.json").read_bytes()
        if sha256_bytes(manifest_raw) != pointer["artifact_set_manifest_sha256"]:
            raise MissionStateError("corrupt_selected_lineage", "CURRENT manifest digest does not match selected set")
        if canonical_json_bytes(pointer) != raw:
            raise MissionStateError("noncanonical_artifact_current", "artifact-state CURRENT is not canonical")
        return ArtifactSetSnapshot(
            mission_root=self.mission_root,
            artifact_set_id=set_id,
            set_dir=set_dir,
            review_queue_path=set_dir / "review_queue.json",
            coverage_dir=set_dir / "coverage",
            manifest=snapshot.manifest,
            recovery=recovery,
        )

    def validate_retained_set(self, artifact_set_id: str) -> ArtifactSetSnapshot:
        """Validate an immutable historical set without making it current."""
        self._validate_root_shape(allow_absent=False)
        recovery = self._recovery_report()
        genesis, _ = _read_canonical(self.genesis_path, "artifact-state GENESIS")
        _validate_genesis_payload(genesis)
        if genesis != self._genesis_payload():
            raise MissionStateError(
                "foreign_artifact_genesis",
                "artifact-state GENESIS does not match active mission",
            )
        if not isinstance(artifact_set_id, str) or SET_ID_RE.fullmatch(artifact_set_id) is None:
            raise MissionStateError("invalid_artifact_set_id", "retained artifact set ID is invalid")
        set_dir = _safe_child_directory(self.sets_dir, artifact_set_id)
        snapshot = self._validate_set(
            set_dir,
            expected_id=artifact_set_id,
            replay_external_context=False,
        )
        retained = ArtifactSetSnapshot(
            mission_root=self.mission_root,
            artifact_set_id=artifact_set_id,
            set_dir=set_dir,
            review_queue_path=set_dir / "review_queue.json",
            coverage_dir=set_dir / "coverage",
            manifest=snapshot.manifest,
            recovery=recovery,
        )
        _validate_mission_binding(retained)
        return retained

    def validate_selected_path(self, path: Path, *, role: str) -> ArtifactSetSnapshot:
        snapshot = self.load_current(required=True)
        assert snapshot is not None
        expected = {
            "review_queue": snapshot.review_queue_path,
            "coverage_dir": snapshot.coverage_dir,
        }.get(role)
        if expected is None:
            raise MissionStateError("invalid_artifact_role", f"unsupported selected path role: {role}")
        supplied = path.absolute()
        if supplied.is_symlink() or supplied != expected.absolute() or supplied.resolve() != expected.resolve():
            raise MissionStateError("stale_lineage", f"supplied {role} is not selected by artifact-state CURRENT")
        return snapshot

    def _genesis_payload(self) -> dict[str, Any]:
        return {
            "schema_version": ARTIFACT_GENESIS_SCHEMA,
            "mission_id": self.mission_id,
            "mission_fingerprint": self.mission_fingerprint,
            "mission_anchor_generation_id": self.mission_anchor_generation_id,
        }

    def _final_payloads(
        self,
        *,
        set_id: str,
        packet_digests: dict[str, dict[str, Any]],
        coverage_packet_digests: dict[str, dict[str, Any]],
        queue_packet_digests: dict[str, dict[str, Any]],
        coverage_payloads: dict[str, dict[str, Any]],
        review_queue_payload: dict[str, Any],
        coverage_semantic_digests: dict[str, str],
        queue_semantic_sha256: str,
        semantic_digest: str,
    ) -> dict[str, bytes]:
        if set(coverage_payloads) != set(COVERAGE_FILES):
            raise MissionStateError("invalid_coverage_payloads", "coverage payload set is incomplete")
        output: dict[str, bytes] = {}
        coverage_exact: dict[str, dict[str, Any]] = {}
        for name in COVERAGE_FILES:
            payload = dict(coverage_payloads[name])
            payload.update(self._identity_fields(set_id))
            value = canonical_pretty_bytes(payload)
            output[f"coverage/{name}"] = value
            coverage_exact[name] = {"sha256": sha256_bytes(value), "size_bytes": len(value)}
        coverage_lineage_sha256 = sha256_bytes(canonical_json_bytes({
            "schema_version": "ra-survey-coverage-lineage-v2",
            "mission_id": self.mission_id,
            "mission_fingerprint": self.mission_fingerprint,
            "mission_anchor_generation_id": self.mission_anchor_generation_id,
            "packet_input_digests": coverage_packet_digests,
            "coverage_semantic_digests": coverage_semantic_digests,
        }))
        coverage_manifest = {
            "schema_version": COVERAGE_MANIFEST_SCHEMA,
            **self._identity_fields(set_id),
            "status": "coverage_ledgers_composed",
            "packet_input_digests": coverage_packet_digests,
            "coverage_semantic_digests": coverage_semantic_digests,
            "coverage_exact_digests": dict(sorted(coverage_exact.items())),
            "lineage_sha256": coverage_lineage_sha256,
            "blocked_frontiers": _blocked_frontiers(coverage_payloads),
            "ready_for_prose": False,
            "what_is_not_concluded": _coverage_nonclaims(coverage_payloads),
        }
        coverage_manifest_bytes = canonical_json_bytes(coverage_manifest)
        output["coverage/coverage_manifest.json"] = coverage_manifest_bytes
        coverage_all_exact = {
            **coverage_exact,
            "coverage_manifest.json": {
                "sha256": sha256_bytes(coverage_manifest_bytes),
                "size_bytes": len(coverage_manifest_bytes),
            },
        }
        queue = dict(review_queue_payload)
        queue_items = sorted(
            [dict(item) for item in queue.get("items") or []],
            key=lambda row: (row.get("queue_type"), row.get("source_id"), row.get("semantic_item_sha256")),
        )
        queue_items = validate_semantic_items(queue_items)
        queue["items"] = queue_items
        queue["queue_counts"] = {
            "total": len(queue_items),
            "by_type": _count_items(queue_items, "queue_type"),
            "by_priority": _count_items(queue_items, "priority"),
            "by_status": _count_items(queue_items, "status"),
        }
        queue.update(self._identity_fields(set_id))
        queue["schema_version"] = REVIEW_QUEUE_SCHEMA
        queue["packet_input_digests"] = queue_packet_digests
        queue["coverage_semantic_digests"] = coverage_semantic_digests
        queue["coverage_exact_digests"] = dict(sorted(coverage_all_exact.items()))
        queue["coverage_lineage_sha256"] = coverage_lineage_sha256
        queue["queue_semantic_sha256"] = queue_semantic_sha256
        output["review_queue.json"] = canonical_pretty_bytes(queue)
        rows = [
            {
                "relative_path": path,
                "schema_version": _schema_from_bytes(value),
                "sha256": sha256_bytes(value),
                "size_bytes": len(value),
                "role": "review_queue" if path == "review_queue.json" else "coverage_artifact",
            }
            for path, value in sorted(output.items())
        ]
        manifest = {
            "schema_version": ARTIFACT_SET_MANIFEST_SCHEMA,
            **self._identity_fields(set_id),
            "artifact_set_semantic_sha256": semantic_digest,
            "packet_input_digests": packet_digests,
            "coverage_semantic_digests": coverage_semantic_digests,
            "queue_semantic_sha256": queue_semantic_sha256,
            "artifacts": rows,
        }
        output["artifact_set_manifest.json"] = canonical_json_bytes(manifest)
        return output

    def _identity_fields(self, set_id: str) -> dict[str, str]:
        return {
            "mission_id": self.mission_id,
            "mission_fingerprint": self.mission_fingerprint,
            "mission_anchor_generation_id": self.mission_anchor_generation_id,
            "artifact_set_id": set_id,
        }

    def _write_set(self, final_dir: Path, payloads: dict[str, bytes]) -> None:
        nonce = _require_hex(self.nonce_factory(), 32, "artifact staging nonce")
        staging = self.sets_dir / f".staging-{final_dir.name}-{nonce}"
        if staging.exists() or final_dir.exists():
            raise MissionStateError("artifact_set_collision", "artifact set staging or final path already exists")
        staging.mkdir()
        _fsync_directory(self.sets_dir)
        if self.crash_hook:
            self.crash_hook("artifact_set:after_staging_parent_fsync")
        for relative, value in sorted(payloads.items(), key=lambda item: item[0] == "artifact_set_manifest.json"):
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as handle:
                handle.write(value)
                if self.crash_hook:
                    self.crash_hook(f"artifact_set:{relative}:after_write")
                handle.flush()
                os.fsync(handle.fileno())
            if self.crash_hook:
                self.crash_hook(f"artifact_set:{relative}:after_fsync")
        directories = {path.parent for path in staging.rglob("*") if path.is_file()}
        for directory in sorted(directories, key=lambda value: len(value.parts), reverse=True):
            _fsync_directory(directory)
        _fsync_directory(staging)
        if self.crash_hook:
            self.crash_hook("artifact_set:after_staging_fsync")
        os.rename(staging, final_dir)
        if self.crash_hook:
            self.crash_hook("artifact_set:after_final_rename")
        _fsync_directory(self.sets_dir)
        if self.crash_hook:
            self.crash_hook("artifact_set:after_sets_fsync")

    def _validate_set(
        self,
        directory: Path,
        *,
        expected_id: str,
        replay_external_context: bool = True,
    ) -> ArtifactSetSnapshot:
        manifest, raw = _read_canonical(directory / "artifact_set_manifest.json", "artifact set manifest")
        _require_exact_keys(
            manifest,
            {
                "schema_version", "mission_id", "mission_fingerprint",
                "mission_anchor_generation_id", "artifact_set_id",
                "artifact_set_semantic_sha256", "packet_input_digests",
                "coverage_semantic_digests", "queue_semantic_sha256", "artifacts",
            },
            "artifact set manifest",
        )
        if manifest["schema_version"] != ARTIFACT_SET_MANIFEST_SCHEMA or manifest["artifact_set_id"] != expected_id:
            raise MissionStateError("invalid_artifact_set_manifest", "artifact set manifest identity is invalid")
        for key, expected in self._identity_fields(expected_id).items():
            if manifest.get(key) != expected:
                raise MissionStateError("foreign_lineage", f"artifact set {key} differs from active mission")
        semantic_digest = _require_hex(manifest["artifact_set_semantic_sha256"], 64, "artifact set semantic digest")
        if expected_id != f"s-{semantic_digest}":
            raise MissionStateError("invalid_artifact_set_id", "artifact set ID does not match semantic digest")
        _require_hex(manifest["queue_semantic_sha256"], 64, "queue semantic digest")
        coverage_semantic_digests = _sorted_hex_map(manifest["coverage_semantic_digests"], "coverage semantic digests")
        packet_input_digests = _validate_digest_rows(manifest["packet_input_digests"], "packet input digests")
        expected_packet_roles = set(PACKET_COVERAGE_FILES) | set(PACKET_QUEUE_FILES)
        if set(packet_input_digests) != expected_packet_roles:
            raise MissionStateError("invalid_packet_digest_map", "artifact set packet digest roles are incomplete or unexpected")
        expected_semantic = sha256_bytes(canonical_json_bytes({
            "schema_version": ARTIFACT_SET_IDENTITY_SCHEMA,
            "mission_id": self.mission_id,
            "mission_fingerprint": self.mission_fingerprint,
            "mission_anchor_generation_id": self.mission_anchor_generation_id,
            "packet_input_digests": packet_input_digests,
            "coverage_semantic_digests": coverage_semantic_digests,
            "queue_semantic_sha256": manifest["queue_semantic_sha256"],
        }))
        if semantic_digest != expected_semantic:
            raise MissionStateError("artifact_set_semantic_mismatch", "artifact set semantic digest is invalid")
        rows = _validate_manifest_rows(manifest["artifacts"])
        expected_artifact_paths = {
            "review_queue.json",
            "coverage/coverage_manifest.json",
            *(f"coverage/{name}" for name in COVERAGE_FILES),
        }
        if {row["relative_path"] for row in rows} != expected_artifact_paths:
            raise MissionStateError("invalid_artifact_rows", "artifact manifest path set is incomplete or unexpected")
        actual: set[str] = {"artifact_set_manifest.json"}
        for row in rows:
            path = _regular_file_beneath(directory, row["relative_path"])
            actual.add(row["relative_path"])
            if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
                raise MissionStateError("corrupt_selected_lineage", f"artifact digest differs: {row['relative_path']}")
            expected_role = "review_queue" if row["relative_path"] == "review_queue.json" else "coverage_artifact"
            if row["role"] != expected_role or row["schema_version"] != _schema_from_bytes(path.read_bytes()):
                raise MissionStateError("invalid_artifact_row", f"artifact role or schema differs: {row['relative_path']}")
        actual_paths: set[str] = set()
        for path in directory.rglob("*"):
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise MissionStateError("unsafe_artifact_set_path", f"unsafe artifact-set path: {path}")
            if stat.S_ISREG(mode):
                actual_paths.add(path.relative_to(directory).as_posix())
        if actual_paths != actual:
            raise MissionStateError("unexpected_artifact_set_path", "artifact set contains unexpected or missing files")
        coverage_packet_digests = {
            key: packet_input_digests[key]
            for key in sorted(PACKET_COVERAGE_FILES)
        }
        queue_packet_digests = {
            key: packet_input_digests[key]
            for key in sorted(PACKET_QUEUE_FILES)
        }
        coverage_payloads: dict[str, dict[str, Any]] = {}
        for name in COVERAGE_FILES:
            payload = _read_pretty_json(directory / "coverage" / name, f"coverage artifact {name}")
            _validate_embedded_identity(payload, self._identity_fields(expected_id), f"coverage artifact {name}")
            coverage_payloads[name] = {key: value for key, value in payload.items() if key not in IDENTITY_FIELDS}
        if replay_external_context:
            _validate_v2_coverage_replay(
                mission_root=self.mission_root,
                mission_id=self.mission_id,
                mission_fingerprint=self.mission_fingerprint,
                mission_anchor_generation_id=self.mission_anchor_generation_id,
                coverage_payloads=coverage_payloads,
            )
        else:
            _validate_retained_v2_coverage_schemas(coverage_payloads)
        if _coverage_semantic_digests(
            coverage_payloads,
            packet_input_digests=coverage_packet_digests,
        ) != coverage_semantic_digests:
            raise MissionStateError("coverage_semantic_mismatch", "coverage semantic projections do not match the set manifest")
        coverage_manifest, coverage_manifest_raw = _read_canonical(
            directory / "coverage" / "coverage_manifest.json",
            "coverage manifest",
        )
        _require_exact_keys(
            coverage_manifest,
            {
                "schema_version", "mission_id", "mission_fingerprint",
                "mission_anchor_generation_id", "artifact_set_id", "status",
                "packet_input_digests", "coverage_semantic_digests",
                "coverage_exact_digests", "lineage_sha256", "blocked_frontiers",
                "ready_for_prose", "what_is_not_concluded",
            },
            "coverage manifest",
        )
        _validate_embedded_identity(coverage_manifest, self._identity_fields(expected_id), "coverage manifest")
        if coverage_manifest["schema_version"] != COVERAGE_MANIFEST_SCHEMA:
            raise MissionStateError("invalid_coverage_manifest_schema", "coverage manifest schema is unsupported")
        if _validate_digest_rows(coverage_manifest["packet_input_digests"], "coverage packet input digests") != coverage_packet_digests:
            raise MissionStateError("coverage_packet_lineage_mismatch", "coverage packet digests differ from the set manifest")
        if _sorted_hex_map(coverage_manifest["coverage_semantic_digests"], "coverage semantic digests") != coverage_semantic_digests:
            raise MissionStateError("coverage_semantic_mismatch", "coverage manifest semantic digests differ from the set manifest")
        exact_coverage = _validate_exact_digest_rows(
            coverage_manifest["coverage_exact_digests"],
            "coverage exact digests",
        )
        expected_exact_coverage = {
            name: {
                "sha256": sha256_file(directory / "coverage" / name),
                "size_bytes": (directory / "coverage" / name).stat().st_size,
            }
            for name in COVERAGE_FILES
        }
        if exact_coverage != expected_exact_coverage:
            raise MissionStateError("coverage_exact_digest_mismatch", "coverage manifest exact digests are invalid")
        expected_coverage_lineage = sha256_bytes(canonical_json_bytes({
            "schema_version": "ra-survey-coverage-lineage-v2",
            "mission_id": self.mission_id,
            "mission_fingerprint": self.mission_fingerprint,
            "mission_anchor_generation_id": self.mission_anchor_generation_id,
            "packet_input_digests": coverage_packet_digests,
            "coverage_semantic_digests": coverage_semantic_digests,
        }))
        if coverage_manifest["lineage_sha256"] != expected_coverage_lineage:
            raise MissionStateError("coverage_lineage_mismatch", "coverage manifest lineage digest is invalid")
        if (
            coverage_manifest["status"] != "coverage_ledgers_composed"
            or coverage_manifest["blocked_frontiers"] != _blocked_frontiers(coverage_payloads)
            or coverage_manifest["ready_for_prose"] is not False
            or coverage_manifest["what_is_not_concluded"] != _coverage_nonclaims(coverage_payloads)
        ):
            raise MissionStateError("coverage_derived_field_mismatch", "coverage manifest derived fields are invalid")
        if canonical_json_bytes(coverage_manifest) != coverage_manifest_raw:
            raise MissionStateError("noncanonical_coverage_manifest", "coverage manifest is not canonical")
        queue = _read_pretty_json(directory / "review_queue.json", "review queue")
        _require_exact_keys(
            queue,
            {
                "schema_version", "mission_id", "mission_fingerprint",
                "mission_anchor_generation_id", "artifact_set_id", "status", "topic",
                "queue_counts", "items", "allowed_item_statuses", "forbidden_promotions",
                "what_is_not_concluded", "packet_input_digests",
                "coverage_semantic_digests", "coverage_exact_digests",
                "coverage_lineage_sha256", "queue_semantic_sha256",
            },
            "review queue",
        )
        _validate_embedded_identity(queue, self._identity_fields(expected_id), "review queue")
        if queue.get("schema_version") != REVIEW_QUEUE_SCHEMA:
            raise MissionStateError("invalid_review_queue_schema", "review queue schema is unsupported")
        items = validate_semantic_items(list(queue.get("items") or []))
        expected_queue_counts = {
            "total": len(items),
            "by_type": _count_items(items, "queue_type"),
            "by_priority": _count_items(items, "priority"),
            "by_status": _count_items(items, "status"),
        }
        if queue.get("queue_counts") != expected_queue_counts:
            raise MissionStateError("queue_count_mismatch", "review queue counts do not match its semantic items")
        if _validate_digest_rows(queue.get("packet_input_digests"), "queue packet input digests") != queue_packet_digests:
            raise MissionStateError("queue_packet_lineage_mismatch", "queue packet digests differ from the set manifest")
        if _sorted_hex_map(queue.get("coverage_semantic_digests"), "queue coverage semantic digests") != coverage_semantic_digests:
            raise MissionStateError("queue_coverage_lineage_mismatch", "queue coverage semantic digests differ from the set manifest")
        expected_queue_coverage_exact = {
            **expected_exact_coverage,
            "coverage_manifest.json": {
                "sha256": sha256_file(directory / "coverage" / "coverage_manifest.json"),
                "size_bytes": (directory / "coverage" / "coverage_manifest.json").stat().st_size,
            },
        }
        if _validate_exact_digest_rows(queue.get("coverage_exact_digests"), "queue coverage exact digests") != expected_queue_coverage_exact:
            raise MissionStateError("queue_coverage_exact_mismatch", "queue coverage exact digests are invalid")
        if queue.get("coverage_lineage_sha256") != expected_coverage_lineage:
            raise MissionStateError("queue_coverage_lineage_mismatch", "queue coverage lineage digest is invalid")
        expected_queue_semantic = _queue_semantic_sha256(
            mission_id=self.mission_id,
            mission_fingerprint=self.mission_fingerprint,
            mission_anchor_generation_id=self.mission_anchor_generation_id,
            packet_input_digests=queue_packet_digests,
            coverage_semantic_digests=coverage_semantic_digests,
            queue=queue,
        )
        if queue.get("queue_semantic_sha256") != expected_queue_semantic or expected_queue_semantic != manifest["queue_semantic_sha256"]:
            raise MissionStateError("queue_semantic_mismatch", "review queue semantic digest is invalid")
        if canonical_json_bytes(manifest) != raw:
            raise MissionStateError("noncanonical_artifact_set_manifest", "artifact set manifest is not canonical")
        return ArtifactSetSnapshot(
            mission_root=self.mission_root,
            artifact_set_id=expected_id,
            set_dir=directory,
            review_queue_path=directory / "review_queue.json",
            coverage_dir=directory / "coverage",
            manifest=manifest,
            recovery=self._recovery_report(),
        )

    def _atomic_write(self, path: Path, value: bytes, *, kind: str) -> None:
        nonce = _require_hex(self.nonce_factory(), 32, f"{kind} nonce")
        temporary = path.parent / f".{kind}.{nonce}.tmp"
        if temporary.exists() or temporary.is_symlink():
            raise MissionStateError("artifact_temp_collision", f"artifact temp path already exists: {temporary.name}")
        with temporary.open("xb") as handle:
            handle.write(value)
            if self.crash_hook:
                self.crash_hook(f"artifact_{kind.lower()}:after_temp_write")
            handle.flush()
            os.fsync(handle.fileno())
        if self.crash_hook:
            self.crash_hook(f"artifact_{kind.lower()}:after_temp_fsync")
        if kind == "GENESIS" and path.exists():
            raise MissionStateError("artifact_genesis_collision", "artifact-state GENESIS appeared during creation")
        os.replace(temporary, path)
        if self.crash_hook:
            self.crash_hook(f"artifact_{kind.lower()}:after_replace")
        _fsync_directory(path.parent)
        if self.crash_hook:
            self.crash_hook(f"artifact_{kind.lower()}:after_directory_fsync")

    def _validate_root_shape(self, *, allow_absent: bool) -> None:
        if not self.state_dir.exists():
            if allow_absent:
                return
            raise MissionStateError("missing_artifact_state", "artifact-state directory is missing")
        if self.state_dir.is_symlink() or not self.state_dir.is_dir():
            raise MissionStateError("unsafe_artifact_state", "artifact-state root is unsafe")
        allowed = {"GENESIS", "CURRENT", "sets"}
        for path in self.state_dir.iterdir():
            if path.name in allowed:
                mode = path.lstat().st_mode
                if path.name == "sets" and (stat.S_ISLNK(mode) or not stat.S_ISDIR(mode)):
                    raise MissionStateError("unsafe_artifact_state", "artifact sets container is unsafe")
                if path.name != "sets" and not stat.S_ISREG(mode):
                    raise MissionStateError("unsafe_artifact_state", f"artifact-state file is unsafe: {path.name}")
                continue
            if GENESIS_TEMP_RE.fullmatch(path.name) or CURRENT_TEMP_RE.fullmatch(path.name):
                if not stat.S_ISREG(path.lstat().st_mode):
                    raise MissionStateError("unsafe_artifact_temp", f"artifact-state temp is unsafe: {path.name}")
                continue
            raise MissionStateError("unexpected_artifact_state_path", f"unexpected artifact-state path: {path.name}")

    def _recovery_report(self) -> dict[str, Any]:
        temp_files: list[str] = []
        staging_dirs: list[str] = []
        if self.state_dir.is_dir():
            for path in self.state_dir.iterdir():
                if (GENESIS_TEMP_RE.fullmatch(path.name) or CURRENT_TEMP_RE.fullmatch(path.name)) and path.is_file():
                    temp_files.append(path.name)
        if self.sets_dir.is_dir():
            for path in self.sets_dir.iterdir():
                if STAGING_RE.fullmatch(path.name):
                    if path.is_symlink() or not path.is_dir():
                        raise MissionStateError("unsafe_artifact_staging", f"artifact staging residue is unsafe: {path.name}")
                    _validate_staging_residue(path)
                    staging_dirs.append(path.name)
                elif path.is_symlink() or (not path.is_dir()) or SET_ID_RE.fullmatch(path.name) is None:
                    raise MissionStateError("unexpected_artifact_set_path", f"unexpected artifact sets path: {path.name}")
        return {"temp_files": sorted(temp_files), "staging_directories": sorted(staging_dirs)}


def assert_public_write_path_allowed(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.is_absolute() else absolute.parts
    for part in parts:
        current = current / part
        if current.name in {".artifact_state", ".mission_state"}:
            code = f"protected_{current.name[1:]}_write"
            raise MissionStateError(code, f"public survey writers cannot write beneath {current.name}")
        if current.exists() or current.is_symlink():
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise MissionStateError("unsafe_public_write_path", "public survey writer path contains a symlink")
            elif not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise MissionStateError("unsafe_public_write_path", f"public survey writer path is unsafe: {current}")
    resolved = _resolve_with_missing_leaf(absolute)
    for protected in (".artifact_state", ".mission_state"):
        if protected in resolved.parts:
            code = f"protected_{protected[1:]}_write"
            raise MissionStateError(code, f"public survey writer path resolves beneath {protected}")


def infer_mission_root_from_selected(path: Path) -> Path | None:
    resolved = path.resolve()
    parts = resolved.parts
    try:
        index = parts.index(".artifact_state")
    except ValueError:
        return None
    return Path(*parts[:index]) if index else Path(resolved.anchor)


def validate_selected_review_queue(path: Path) -> ArtifactSetSnapshot:
    mission_root = infer_mission_root_from_selected(path)
    if mission_root is None:
        raise MissionStateError(
            "unselected_lineage",
            "review queue is not beneath a mission artifact-state selector",
        )
    genesis, _ = _read_canonical(mission_root / ".artifact_state" / "GENESIS", "artifact-state GENESIS")
    manager = ArtifactStateManager(
        mission_root=mission_root,
        mission_id=genesis["mission_id"],
        mission_fingerprint=genesis["mission_fingerprint"],
        mission_anchor_generation_id=genesis["mission_anchor_generation_id"],
    )
    snapshot = manager.validate_selected_path(path, role="review_queue")
    _validate_mission_binding(snapshot)
    return snapshot


def validate_selected_coverage_dir(path: Path) -> ArtifactSetSnapshot:
    mission_root = infer_mission_root_from_selected(path)
    if mission_root is None:
        raise MissionStateError(
            "unselected_lineage",
            "coverage directory is not beneath a mission artifact-state selector",
        )
    genesis, _ = _read_canonical(mission_root / ".artifact_state" / "GENESIS", "artifact-state GENESIS")
    manager = ArtifactStateManager(
        mission_root=mission_root,
        mission_id=genesis["mission_id"],
        mission_fingerprint=genesis["mission_fingerprint"],
        mission_anchor_generation_id=genesis["mission_anchor_generation_id"],
    )
    snapshot = manager.validate_selected_path(path, role="coverage_dir")
    _validate_mission_binding(snapshot)
    return snapshot


def classify_review_queue_digest(selected_path: Path, digest: Any) -> str:
    snapshot = validate_selected_review_queue(selected_path)
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return "corrupt_downstream_lineage"
    if sha256_file(snapshot.review_queue_path) == digest:
        return "current_lineage"
    for candidate in sorted((snapshot.mission_root / ".artifact_state" / "sets").iterdir()):
        if candidate == snapshot.set_dir or candidate.is_symlink() or not candidate.is_dir():
            continue
        if SET_ID_RE.fullmatch(candidate.name) is None:
            continue
        queue_path = candidate / "review_queue.json"
        try:
            if sha256_file(_regular_file_beneath(candidate, "review_queue.json")) != digest:
                continue
            manager = ArtifactStateManager(
                mission_root=snapshot.mission_root,
                mission_id=snapshot.manifest["mission_id"],
                mission_fingerprint=snapshot.manifest["mission_fingerprint"],
                mission_anchor_generation_id=snapshot.manifest["mission_anchor_generation_id"],
            )
            manager._validate_set(candidate.resolve(), expected_id=candidate.name)
        except (MissionStateError, OSError):
            continue
        if queue_path.is_file():
            return "stale_lineage"
    return "corrupt_downstream_lineage"


def read_artifact_genesis(mission_root: Path) -> dict[str, Any] | None:
    path = mission_root.resolve() / ".artifact_state" / "GENESIS"
    if not path.exists() and not path.is_symlink():
        return None
    value, _ = _read_canonical(path, "artifact-state GENESIS")
    _validate_genesis_payload(value)
    return value


def read_packet_json(directory: Path, relative: str, *, label: str) -> dict[str, Any]:
    path = _regular_file_beneath(directory.resolve(), relative)
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_packet_json", f"cannot read {label}") from exc
    if not isinstance(value, dict):
        raise MissionStateError("invalid_packet_json", f"{label} must be a JSON object")
    return value


def _validate_mission_binding(snapshot: ArtifactSetSnapshot) -> None:
    validate_generation_ancestor_readonly(
        output_dir=snapshot.mission_root,
        mission_id=snapshot.manifest["mission_id"],
        mission_fingerprint=snapshot.manifest["mission_fingerprint"],
        generation_id=snapshot.manifest["mission_anchor_generation_id"],
    )


def _digest_map(directory: Path, names: dict[str, str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for role, name in sorted(names.items()):
        path = _regular_file_beneath(directory, name)
        result[role] = {"relative_path": name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
    return result


def _coverage_semantic_digests(
    payloads: dict[str, dict[str, Any]],
    *,
    packet_input_digests: dict[str, dict[str, Any]],
) -> dict[str, str]:
    if set(payloads) != set(COVERAGE_FILES) or any(not isinstance(value, dict) for value in payloads.values()):
        raise MissionStateError("invalid_coverage_payloads", "coverage semantic payload set is incomplete")
    packet_input_digests = _validate_digest_rows(packet_input_digests, "coverage packet input digests")
    return {
        name: sha256_bytes(canonical_json_bytes({
            "schema_version": "ra-survey-coverage-artifact-semantic-v2",
            "artifact_name": name,
            "packet_input_digests": packet_input_digests,
            "payload": {
                key: value
                for key, value in payloads[name].items()
                if key not in IDENTITY_FIELDS
            },
        }))
        for name in sorted(payloads)
    }


def _validate_v2_coverage_replay(
    *,
    mission_root: Path,
    mission_id: str,
    mission_fingerprint: str,
    mission_anchor_generation_id: str,
    coverage_payloads: dict[str, dict[str, Any]],
) -> None:
    from research_assistant.survey.coverage_ledgers import load_v2_frontier_context
    from research_assistant.survey.frontier_expansion import (
        BACKWARD_FRONTIER_SCHEMA,
        FORWARD_FRONTIER_SCHEMA,
        OMITTED_RISKS_SCHEMA,
        build_frontier_payloads,
    )
    from research_assistant.survey.mission_state import validate_generation_binding_readonly
    from research_assistant.survey.source_intake import (
        METADATA_AUTHORITY_SCHEMA,
        METADATA_AUTHORITY_V2_SCHEMA,
        SOURCE_INTAKE_STATUS_SCHEMA,
    )

    schema_by_name = {
        name: coverage_payloads[name].get("schema_version")
        for name in (
            "backward_snowball.json",
            "forward_snowball.json",
            "omitted_paper_risks.json",
        )
    }
    expected_v2 = {
        "backward_snowball.json": BACKWARD_FRONTIER_SCHEMA,
        "forward_snowball.json": FORWARD_FRONTIER_SCHEMA,
        "omitted_paper_risks.json": OMITTED_RISKS_SCHEMA,
    }
    v2_names = {name for name, schema in schema_by_name.items() if schema == expected_v2[name]}
    active_authority_schemas = _active_metadata_authority_schemas(
        mission_root=mission_root,
        mission_id=mission_id,
        mission_fingerprint=mission_fingerprint,
    )
    requires_v2 = METADATA_AUTHORITY_V2_SCHEMA in active_authority_schemas

    status_path = mission_root / "source_intake" / "phase4_source_intake_status.json"
    status_present = status_path.exists() or status_path.is_symlink()
    if not status_present:
        if requires_v2:
            raise MissionStateError(
                "missing_frontier_context",
                "active V2 metadata authority requires canonical source-intake status",
            )
        if not v2_names:
            return
        if v2_names != set(expected_v2):
            raise MissionStateError("mixed_coverage_schema", "selected coverage mixes V1 and V2 frontier authority")
        raise MissionStateError(
            "missing_frontier_context",
            "V2 frontier coverage requires canonical source-intake authority",
        )

    status = _read_pretty_json(status_path, "mission source-intake status")
    if (
        status.get("schema_version") != SOURCE_INTAKE_STATUS_SCHEMA
        or status.get("mission_id") != mission_id
        or status.get("mission_fingerprint") != mission_fingerprint
    ):
        raise MissionStateError("foreign_frontier_context", "source-intake status does not bind selected coverage")
    authority = status.get("metadata_authority")
    creation_generation_id = status.get("creation_generation_id")
    if not isinstance(authority, dict) or not isinstance(creation_generation_id, str):
        raise MissionStateError("invalid_frontier_context", "source-intake status lacks metadata authority binding")
    binding = validate_generation_binding_readonly(
        output_dir=mission_root,
        mission_id=mission_id,
        mission_fingerprint=mission_fingerprint,
        generation_id=creation_generation_id,
        metadata_authority=authority,
    )
    if status.get("metadata_authority_sha256") != binding.get("metadata_authority_sha256"):
        raise MissionStateError("metadata_authority_binding_mismatch", "source-intake authority digest is stale")
    authority_schema = authority.get("schema_version")
    if requires_v2 and authority_schema != METADATA_AUTHORITY_V2_SCHEMA:
        raise MissionStateError(
            "frontier_authority_schema_mismatch",
            "active V2 metadata authority differs from canonical source-intake status",
        )
    if authority_schema == METADATA_AUTHORITY_V2_SCHEMA:
        if v2_names != set(expected_v2):
            raise MissionStateError(
                "coverage_schema_downgrade",
                "anchored V2 metadata authority requires all exact V2 frontier schemas",
            )
        _validate_exact_v2_coverage_schemas(
            coverage_payloads,
            error_code="coverage_schema_downgrade",
            message="anchored V2 metadata authority requires the exact V2 coverage schema family",
        )
    elif authority_schema == METADATA_AUTHORITY_SCHEMA:
        if v2_names:
            raise MissionStateError(
                "frontier_authority_schema_mismatch",
                "anchored V1 metadata authority cannot authorize V2 frontier schemas",
            )
        return
    else:
        raise MissionStateError(
            "invalid_frontier_context",
            "source-intake metadata authority schema is unsupported",
        )
    validate_generation_ancestor_readonly(
        output_dir=mission_root,
        mission_id=mission_id,
        mission_fingerprint=mission_fingerprint,
        generation_id=mission_anchor_generation_id,
    )
    context = load_v2_frontier_context(
        topic=coverage_payloads["backward_snowball.json"].get("topic"),
        validated_source_intake={"status": status, "project_root": mission_root},
        mission_anchor_generation_id=mission_anchor_generation_id,
    )
    replayed = build_frontier_payloads(**context)
    for name in expected_v2:
        if replayed[name] != coverage_payloads[name]:
            raise MissionStateError("frontier_semantic_replay_mismatch", f"selected V2 coverage differs on {name}")


def _validate_retained_v2_coverage_schemas(
    coverage_payloads: dict[str, dict[str, Any]],
) -> None:
    _validate_exact_v2_coverage_schemas(
        coverage_payloads,
        error_code="invalid_retained_coverage_schema",
        message="retained omission authority requires the exact V2 coverage schema family",
    )


def _validate_exact_v2_coverage_schemas(
    coverage_payloads: dict[str, dict[str, Any]],
    *,
    error_code: str,
    message: str,
) -> None:
    from research_assistant.survey.coverage_ledgers import (
        SURVEY_CITATION_VENUE_METADATA_SCHEMA_VERSION,
    )
    from research_assistant.survey.frontier_expansion import (
        BACKWARD_FRONTIER_SCHEMA,
        FORWARD_FRONTIER_SCHEMA,
        OMITTED_RISKS_SCHEMA,
    )

    expected = {
        "backward_snowball.json": BACKWARD_FRONTIER_SCHEMA,
        "citation_venue_metadata.json": SURVEY_CITATION_VENUE_METADATA_SCHEMA_VERSION,
        "forward_snowball.json": FORWARD_FRONTIER_SCHEMA,
        "omitted_paper_risks.json": OMITTED_RISKS_SCHEMA,
        "paper_classifications.json": "ra-survey-public-source-paper-classifications-v1",
    }
    actual = {
        name: coverage_payloads[name].get("schema_version")
        for name in expected
    }
    if actual != expected:
        raise MissionStateError(error_code, message)


def _active_metadata_authority_schemas(
    *,
    mission_root: Path,
    mission_id: str,
    mission_fingerprint: str,
) -> set[str]:
    generations = mission_root / ".mission_state" / "generations"
    if not generations.exists() and not generations.is_symlink():
        return set()
    if generations.is_symlink() or not generations.is_dir():
        raise MissionStateError("invalid_mission_state", "mission generations root is unsafe or missing")
    schemas: set[str] = set()
    for path in sorted(generations.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_dir() or GENERATION_ID_RE.fullmatch(path.name) is None:
            raise MissionStateError("invalid_mission_state", "mission generations contain an unsafe child")
        try:
            binding = validate_generation_binding_readonly(
                output_dir=mission_root,
                mission_id=mission_id,
                mission_fingerprint=mission_fingerprint,
                generation_id=path.name,
            )
        except MissionStateError as exc:
            if exc.code == "artifact_anchor_not_ancestor":
                continue
            raise
        authority = binding.get("metadata_authority")
        if authority is None:
            continue
        if not isinstance(authority, dict) or not isinstance(authority.get("schema_version"), str):
            raise MissionStateError("invalid_frontier_context", "active metadata authority is malformed")
        schemas.add(authority["schema_version"])
    return schemas


def _blocked_frontiers(payloads: dict[str, dict[str, Any]]) -> list[str]:
    blocked = []
    for direction, name in (("backward", "backward_snowball.json"), ("forward", "forward_snowball.json")):
        if str(payloads[name].get("status") or "").startswith("blocked"):
            blocked.append(direction)
    return blocked


def _coverage_nonclaims(payloads: dict[str, dict[str, Any]]) -> list[str]:
    values: set[str] = set()
    for payload in payloads.values():
        nonclaims = payload.get("what_is_not_concluded") or []
        if not isinstance(nonclaims, list) or any(not isinstance(value, str) for value in nonclaims):
            raise MissionStateError("invalid_coverage_payloads", "coverage nonclaims must be a string list")
        values.update(value for value in nonclaims if value)
    return sorted(values)


def _queue_semantic_sha256(
    *,
    mission_id: str,
    mission_fingerprint: str,
    mission_anchor_generation_id: str,
    packet_input_digests: dict[str, dict[str, Any]],
    coverage_semantic_digests: dict[str, str],
    queue: dict[str, Any],
) -> str:
    items = validate_semantic_items(list(queue.get("items") or []))
    policy_fields = {
        key: value
        for key, value in queue.items()
        if key not in QUEUE_DERIVED_FIELDS and key != "items"
    }
    projection = {
        "schema_version": "ra-survey-review-queue-semantic-v2",
        "mission_id": mission_id,
        "mission_fingerprint": mission_fingerprint,
        "mission_anchor_generation_id": mission_anchor_generation_id,
        "packet_input_digests": _validate_digest_rows(packet_input_digests, "queue packet input digests"),
        "coverage_semantic_digests": _sorted_hex_map(coverage_semantic_digests, "queue coverage semantic digests"),
        "policy_fields": policy_fields,
        "items": [semantic_item_projection(item) for item in items],
    }
    return sha256_bytes(canonical_json_bytes(projection))


def _validate_digest_rows(value: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or not value:
        raise MissionStateError("invalid_digest_map", f"{label} must be a nonempty object")
    result: dict[str, dict[str, Any]] = {}
    for key, row in sorted(value.items()):
        _require_exact_keys(row, {"relative_path", "sha256", "size_bytes"}, f"{label}.{key}")
        relative = _safe_relative_path(row["relative_path"])
        digest = _require_hex(row["sha256"], 64, f"{label}.{key}.sha256")
        size = row["size_bytes"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise MissionStateError("invalid_digest_map", f"{label}.{key}.size_bytes must be nonnegative")
        result[str(key)] = {"relative_path": relative, "sha256": digest, "size_bytes": size}
    return result


def _validate_exact_digest_rows(value: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or not value:
        raise MissionStateError("invalid_digest_map", f"{label} must be a nonempty object")
    result: dict[str, dict[str, Any]] = {}
    for key, row in sorted(value.items()):
        _require_exact_keys(row, {"sha256", "size_bytes"}, f"{label}.{key}")
        digest = _require_hex(row["sha256"], 64, f"{label}.{key}.sha256")
        size = row["size_bytes"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise MissionStateError("invalid_digest_map", f"{label}.{key}.size_bytes must be nonnegative")
        result[str(key)] = {"sha256": digest, "size_bytes": size}
    return result


def _count_items(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _validate_genesis_payload(value: dict[str, Any]) -> None:
    _require_exact_keys(
        value,
        {"schema_version", "mission_id", "mission_fingerprint", "mission_anchor_generation_id"},
        "artifact-state GENESIS",
    )
    if value["schema_version"] != ARTIFACT_GENESIS_SCHEMA:
        raise MissionStateError("invalid_artifact_genesis", "artifact-state GENESIS schema is unsupported")
    _require_string(value["mission_id"], "artifact GENESIS mission_id")
    _require_hex(value["mission_fingerprint"], 64, "artifact GENESIS mission_fingerprint")
    if not isinstance(value["mission_anchor_generation_id"], str) or GENERATION_ID_RE.fullmatch(value["mission_anchor_generation_id"]) is None:
        raise MissionStateError("invalid_anchor_generation", "artifact GENESIS anchor generation is invalid")


def _validate_staging_residue(directory: Path) -> None:
    allowed_files = {
        "artifact_set_manifest.json",
        "review_queue.json",
        *(f"coverage/{name}" for name in (*COVERAGE_FILES, "coverage_manifest.json")),
    }
    allowed_directories = {"coverage"}
    for path in directory.rglob("*"):
        mode = path.lstat().st_mode
        relative = path.relative_to(directory).as_posix()
        if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise MissionStateError("unsafe_artifact_staging", f"unsafe artifact staging path: {relative}")
        if stat.S_ISDIR(mode) and relative not in allowed_directories:
            raise MissionStateError("unexpected_artifact_staging_path", f"unexpected staging directory: {relative}")
        if stat.S_ISREG(mode) and relative not in allowed_files:
            raise MissionStateError("unexpected_artifact_staging_path", f"unexpected staging file: {relative}")


def _read_pretty_json(path: Path, label: str) -> dict[str, Any]:
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise MissionStateError("unsafe_artifact_path", f"{label} is not a regular file")
        raw = path.read_bytes()
        value = json.loads(raw)
    except MissionStateError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_artifact_json", f"cannot read {label}") from exc
    if not isinstance(value, dict) or canonical_pretty_bytes(value) != raw:
        raise MissionStateError("noncanonical_artifact_json", f"{label} is not deterministic pretty JSON")
    return value


def _validate_embedded_identity(value: dict[str, Any], expected: dict[str, str], label: str) -> None:
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise MissionStateError("foreign_lineage", f"{label} {key} differs from the selected set")


def _validate_manifest_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise MissionStateError("invalid_artifact_rows", "artifact manifest rows must be objects")
    result: list[dict[str, Any]] = []
    paths: list[str] = []
    for row in value:
        _require_exact_keys(row, {"relative_path", "schema_version", "sha256", "size_bytes", "role"}, "artifact manifest row")
        relative = _safe_relative_path(row["relative_path"])
        paths.append(relative)
        _require_string(row["schema_version"], "artifact schema")
        _require_hex(row["sha256"], 64, "artifact SHA-256")
        if isinstance(row["size_bytes"], bool) or not isinstance(row["size_bytes"], int) or row["size_bytes"] < 0:
            raise MissionStateError("invalid_artifact_row", "artifact size must be a nonnegative integer")
        _require_string(row["role"], "artifact role")
        result.append(dict(row))
    if paths != sorted(set(paths)):
        raise MissionStateError("invalid_artifact_rows", "artifact paths must be unique and sorted")
    return result


def _regular_file_beneath(directory: Path, relative: str) -> Path:
    relative = _safe_relative_path(relative)
    root = directory.resolve()
    candidate = directory
    for index, part in enumerate(PurePosixPath(relative).parts):
        candidate = candidate / part
        try:
            mode = candidate.lstat().st_mode
        except OSError as exc:
            raise MissionStateError("missing_artifact", f"required artifact is missing: {relative}") from exc
        if stat.S_ISLNK(mode):
            raise MissionStateError("unsafe_artifact_path", f"artifact path contains a symlink: {relative}")
        if index < len(PurePosixPath(relative).parts) - 1 and not stat.S_ISDIR(mode):
            raise MissionStateError("unsafe_artifact_path", f"artifact parent is not a directory: {relative}")
        if index == len(PurePosixPath(relative).parts) - 1 and not stat.S_ISREG(mode):
            raise MissionStateError("unsafe_artifact_path", f"artifact is not a regular file: {relative}")
    try:
        candidate.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise MissionStateError("unsafe_artifact_path", f"artifact escapes declared directory: {relative}") from exc
    return candidate


def _safe_child_directory(parent: Path, name: str) -> Path:
    child = parent / name
    if child.is_symlink() or not child.is_dir() or child.resolve().parent != parent.resolve():
        raise MissionStateError("unsafe_artifact_set_path", "artifact set directory is missing or unsafe")
    return child.resolve()


def _read_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise MissionStateError("unsafe_artifact_state", f"{label} is not a regular file")
        raw = path.read_bytes()
        value = json.loads(raw)
    except MissionStateError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_artifact_state_json", f"cannot read {label}") from exc
    if not isinstance(value, dict):
        raise MissionStateError("invalid_artifact_state_json", f"{label} must be an object")
    if canonical_json_bytes(value) != raw:
        raise MissionStateError("noncanonical_artifact_state", f"{label} is not canonical")
    return value, raw


def _schema_from_bytes(value: bytes) -> str:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise MissionStateError("invalid_artifact_json", "artifact bytes are not JSON") from exc
    return _require_string(payload.get("schema_version"), "artifact schema_version")


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise MissionStateError("invalid_artifact_path", "artifact path must be a nonempty string")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise MissionStateError("invalid_artifact_path", f"unsafe artifact path: {value}")
    return value


def _sorted_hex_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise MissionStateError("invalid_digest_map", f"{label} must be a nonempty object")
    result = {str(key): _require_hex(digest, 64, f"{label}.{key}") for key, digest in value.items()}
    if list(value) != sorted(value):
        result = dict(sorted(result.items()))
    return result


def _require_exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise MissionStateError("invalid_schema", f"{label} fields do not match exact schema")


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise MissionStateError("invalid_schema", f"{label} must be a nonempty string")
    return value


def _require_hex(value: Any, length: int, label: str) -> str:
    if not isinstance(value, str) or len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise MissionStateError("invalid_schema", f"{label} must be {length} lowercase hex characters")
    return value


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _resolve_with_missing_leaf(path: Path) -> Path:
    missing: list[str] = []
    current = path
    while not current.exists() and not current.is_symlink():
        missing.append(current.name)
        parent = current.parent
        if parent == current:
            break
        current = parent
    resolved = current.resolve()
    for part in reversed(missing):
        resolved = resolved / part
    return resolved


__all__ = [
    "ARTIFACT_CURRENT_SCHEMA",
    "ARTIFACT_GENESIS_SCHEMA",
    "ARTIFACT_SET_MANIFEST_SCHEMA",
    "ArtifactSetSnapshot",
    "ArtifactStateManager",
    "COVERAGE_FILES",
    "COVERAGE_MANIFEST_SCHEMA",
    "REVIEW_QUEUE_SCHEMA",
    "assert_public_write_path_allowed",
    "canonical_pretty_bytes",
    "classify_review_queue_digest",
    "read_artifact_genesis",
    "read_packet_json",
    "semantic_item",
    "validate_selected_coverage_dir",
    "validate_selected_review_queue",
    "validate_semantic_items",
    "workflow_blocker_source_id",
]
