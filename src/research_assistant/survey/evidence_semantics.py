from __future__ import annotations

import json
import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.artifact_lineage import (
    assert_public_write_path_allowed,
    canonical_pretty_bytes,
    validate_selected_review_queue,
)
from research_assistant.survey.frontier_expansion import (
    BACKWARD_FRONTIER_SCHEMA,
    FORWARD_FRONTIER_SCHEMA,
    OMITTED_RISKS_SCHEMA,
)
from research_assistant.survey.mission_state import (
    MissionSnapshot,
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
    validate_generation_binding_readonly,
)
from research_assistant.survey.review_decisions import (
    normalize_required_text,
    normalize_reviewed_at,
    read_json_object_strict,
    require_exact_keys,
)
from research_assistant.survey.source_intake import validate_mission_source_intake


HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SET_ID_RE = re.compile(r"^[a-z]{2}-[0-9a-f]{64}$")
NONCE_RE = re.compile(r"^[0-9a-f]{32}$")

V2_FRONTIER_SCHEMAS = {
    "backward_snowball.json": BACKWARD_FRONTIER_SCHEMA,
    "forward_snowball.json": FORWARD_FRONTIER_SCHEMA,
    "omitted_paper_risks.json": OMITTED_RISKS_SCHEMA,
}


@dataclass(frozen=True)
class SourceIdentity:
    queue_item_id: str
    stable_metadata_paper_id: str
    source_paper_id: str
    canonical_identifier: str
    aliases: list[str]
    source_version: str
    source_record_path: str
    source_record_sha256: str
    source_record_size_bytes: int
    provider: str
    final_url: str


@dataclass(frozen=True)
class EvidenceContext:
    mission_root: Path
    review_queue_path: Path
    review_queue: dict[str, Any]
    review_queue_sha256: str
    selected_artifact_set: Any
    mission_snapshot: MissionSnapshot
    validated_source_intake: dict[str, Any]
    identity_components: dict[str, dict[str, Any]]
    source_identities: dict[str, SourceIdentity]
    unavailable_outcomes: list[dict[str, Any]]

    @property
    def binding(self) -> dict[str, Any]:
        return {
            "mission_id": self.review_queue["mission_id"],
            "mission_fingerprint": self.review_queue["mission_fingerprint"],
            "mission_anchor_generation_id": self.review_queue["mission_anchor_generation_id"],
            "artifact_set_id": self.review_queue["artifact_set_id"],
            "queue_semantic_sha256": self.review_queue["queue_semantic_sha256"],
            "review_queue_sha256": self.review_queue_sha256,
        }


@dataclass(frozen=True)
class AuthorityConfig:
    family: str
    id_prefix: str
    sets_dir_name: str
    current_name: str
    set_id_field: str
    current_manifest_field: str
    semantic_field: str
    manifest_name: str
    manifest_schema: str
    identity_schema: str
    current_schema: str
    predecessor_id_field: str
    predecessor_manifest_field: str
    artifacts: dict[str, str]
    identity_fields: frozenset[str]
    root_allowed_names: frozenset[str]


@dataclass(frozen=True)
class AuthoritySnapshot:
    set_id: str
    set_dir: Path
    manifest: dict[str, Any]
    artifact_paths: dict[str, Path]
    recovery: dict[str, list[str]]

    @property
    def manifest_path(self) -> Path:
        return self.set_dir / next(
            name for name in self.set_dir.iterdir() if name.name.endswith("manifest.json")
        ).name


def canonical_semantic_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def require_sha256(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise MissionStateError("invalid_evidence_hash", f"{field} must be lowercase SHA-256")
    return value


def strict_string_list(value: Any, *, field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise MissionStateError("invalid_evidence_list", f"{field} must be a list")
    result = [normalize_required_text(item, field=field) for item in value]
    if result != sorted(set(result)) or (not allow_empty and not result):
        raise MissionStateError("invalid_evidence_list", f"{field} must be sorted and unique")
    return result


def load_v2_evidence_context(review_queue_path: Path) -> EvidenceContext:
    selected = validate_selected_review_queue(review_queue_path)
    queue, queue_raw = read_json_object_strict(selected.review_queue_path, label="selected review queue")
    if queue_raw != canonical_pretty_bytes(queue):
        raise MissionStateError("noncanonical_review_queue", "selected review queue is not canonical pretty JSON")
    retained_status_path = selected.mission_root / "source_intake" / "phase4_source_intake_status.json"
    try:
        retained_status, _ = read_json_object_strict(
            retained_status_path,
            label="mission source-intake status",
        )
    except MissionStateError:
        retained_status = {}
    if retained_status.get("schema_version") == "ra-survey-retained-source-intake-v1":
        from research_assistant.survey.m22_retained_reconciliation import (
            load_retained_evidence_context,
        )

        return load_retained_evidence_context(
            selected=selected,
            queue=queue,
            queue_raw=queue_raw,
        )
    schemas: dict[str, Any] = {}
    for name in V2_FRONTIER_SCHEMAS:
        payload, raw = read_json_object_strict(selected.coverage_dir / name, label=name)
        if raw != canonical_pretty_bytes(payload):
            raise MissionStateError("noncanonical_selected_coverage", f"selected {name} is not canonical")
        schemas[name] = payload.get("schema_version")
    v2_names = {name for name, schema in schemas.items() if schema == V2_FRONTIER_SCHEMAS[name]}
    if v2_names != set(V2_FRONTIER_SCHEMAS):
        if v2_names:
            raise MissionStateError("mixed_coverage_schema", "selected coverage mixes V1 and V2 frontier authority")
        raise MissionStateError("legacy_evidence_authority", "selected coverage is not canonical V2 authority")

    binding = validate_generation_binding_readonly(
        output_dir=selected.mission_root,
        mission_id=queue["mission_id"],
        mission_fingerprint=queue["mission_fingerprint"],
        generation_id=queue["mission_anchor_generation_id"],
    )
    snapshot = MissionSnapshot(
        contract=binding["mission_contract"],
        mission_control=binding["mission_control"],
        next_action=binding["next_action"],
        current_pointer={"generation_id": binding["current_generation_id"]},
        recovery={"state": "read_only", "orphans": []},
    )
    validated = validate_mission_source_intake(
        mission_root=selected.mission_root,
        snapshot=snapshot,
        status_path=selected.mission_root / "source_intake" / "phase4_source_intake_status.json",
    )
    status = validated["status"]
    authority = status["metadata_authority"]
    rows = authority.get("artifact_rows")
    if not isinstance(rows, list):
        raise MissionStateError("invalid_metadata_authority", "V2 metadata authority lacks artifact rows")
    identity_row = next((row for row in rows if row.get("name") == "identity_resolution.json"), None)
    if not isinstance(identity_row, dict):
        raise MissionStateError("invalid_metadata_authority", "V2 metadata authority lacks identity resolution")
    identity_path = _regular_file(Path(identity_row["path"]), root=selected.mission_root, label="identity resolution")
    identity_raw = identity_path.read_bytes()
    if (
        sha256_bytes(identity_raw) != identity_row.get("sha256")
        or len(identity_raw) != identity_row.get("size_bytes")
    ):
        raise MissionStateError("stale_source_metadata", "identity-resolution bytes differ from source authority")
    try:
        identity_payload = json.loads(identity_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_source_metadata", "identity resolution is not valid JSON") from exc
    if identity_raw != canonical_pretty_bytes(identity_payload):
        raise MissionStateError("noncanonical_source_metadata", "identity resolution is not canonical")
    components = identity_payload.get("components")
    if not isinstance(components, list):
        raise MissionStateError("invalid_source_metadata", "identity components must be a list")
    component_by_id: dict[str, dict[str, Any]] = {}
    for row in components:
        if not isinstance(row, dict) or row.get("component_status") != "eligible":
            continue
        stable_id = row.get("paper_id")
        if not isinstance(stable_id, str) or not stable_id or stable_id in component_by_id:
            raise MissionStateError("invalid_source_metadata", "eligible identity paper IDs are invalid")
        component_by_id[stable_id] = row

    outcomes = validated["outcomes"]
    outcome_by_paper = {
        row["paper_id"]: row
        for row in outcomes
        if row.get("outcome_status") == "available"
    }
    source_items = [item for item in queue.get("items") or [] if item.get("queue_type") == "source_safety"]
    source_identities: dict[str, SourceIdentity] = {}
    for item in source_items:
        queue_item_id = item.get("item_id")
        source_paper_id = item.get("paper_id")
        if not isinstance(queue_item_id, str) or not isinstance(source_paper_id, str):
            raise MissionStateError("invalid_source_safety_queue", "source-safety queue identity is incomplete")
        outcome = outcome_by_paper.get(source_paper_id)
        if outcome is None:
            raise MissionStateError("source_safety_queue_join_failed", "source-safety queue item lacks an available outcome")
        stable_id = outcome["candidate_id"]
        component = component_by_id.get(stable_id)
        canonical_identifier = outcome["identifier"]
        if (
            component is None
            or component.get("canonical_identifier") != canonical_identifier
        ):
            raise MissionStateError("source_identity_join_failed", "source outcome does not exactly join the V2 identity component")
        record_sha = require_sha256(outcome["source_record_sha256"], field="source_record_sha256")
        source_identities[queue_item_id] = SourceIdentity(
            queue_item_id=queue_item_id,
            stable_metadata_paper_id=stable_id,
            source_paper_id=source_paper_id,
            canonical_identifier=canonical_identifier,
            aliases=strict_string_list(component["aliases"], field="identity aliases"),
            source_version=f"record-sha256:{record_sha}",
            source_record_path=outcome["source_record_path"],
            source_record_sha256=record_sha,
            source_record_size_bytes=outcome["source_record_size_bytes"],
            provider=outcome["provider"],
            final_url=outcome["final_url"],
        )
    unavailable = sorted(
        [dict(row) for row in outcomes if row.get("outcome_status") == "unavailable"],
        key=lambda row: (int(row.get("candidate_index", -1)), str(row.get("candidate_id", ""))),
    )
    return EvidenceContext(
        mission_root=selected.mission_root,
        review_queue_path=selected.review_queue_path,
        review_queue=queue,
        review_queue_sha256=sha256_bytes(queue_raw),
        selected_artifact_set=selected,
        mission_snapshot=snapshot,
        validated_source_intake=validated,
        identity_components=component_by_id,
        source_identities=source_identities,
        unavailable_outcomes=unavailable,
    )


class ImmutableAuthorityManager:
    def __init__(
        self,
        *,
        root: Path,
        config: AuthorityConfig,
        semantic_validator: Callable[[AuthoritySnapshot], None] | None = None,
        nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
        crash_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.root = root.absolute()
        self.config = config
        self.sets_dir = self.root / config.sets_dir_name
        self.current_path = self.root / config.current_name
        self.semantic_validator = semantic_validator
        self.nonce_factory = nonce_factory
        self.crash_hook = crash_hook

    def preview(
        self,
        *,
        identity_fields: dict[str, Any],
        artifacts: dict[str, bytes],
    ) -> tuple[str, dict[str, Any]]:
        self._validate_artifact_names(artifacts)
        if set(identity_fields) != set(self.config.identity_fields):
            raise MissionStateError(
                f"invalid_{self.config.family}_identity",
                f"{self.config.family} identity fields do not match the exact schema",
            )
        identity = {"schema_version": self.config.identity_schema, **identity_fields}
        set_id = f"{self.config.id_prefix}-{sha256_bytes(canonical_json_bytes(identity))}"
        manifest = self._manifest(set_id=set_id, identity=identity, artifacts=artifacts)
        return set_id, manifest

    def compose_and_select(
        self,
        *,
        identity_fields: dict[str, Any],
        artifacts: dict[str, bytes],
        force: bool,
    ) -> AuthoritySnapshot:
        self._ensure_root()
        pointer = self._load_pointer(required=False)
        snapshots, head = self._validated_chain()
        set_id, manifest = self.preview(identity_fields=identity_fields, artifacts=artifacts)
        if head is not None and (pointer is None or pointer.set_id != head.set_id):
            if head.set_id == set_id:
                self._select(head)
                return self.load_current(required=True)
            raise MissionStateError(
                f"stale_{self.config.family}_selector",
                f"{self.config.current_name} does not name the unique chain head",
            )
        if pointer is not None and pointer.set_id == set_id:
            self._require_exact_existing(pointer, artifacts, manifest)
            return pointer
        if pointer is not None and not force:
            raise MissionStateError("output_exists", f"a different {self.config.family} set is selected")
        expected_predecessor = pointer.set_id if pointer is not None else None
        expected_predecessor_hash = (
            sha256_file(pointer.set_dir / self.config.manifest_name) if pointer is not None else None
        )
        if (
            identity_fields.get(self.config.predecessor_id_field) != expected_predecessor
            or identity_fields.get(self.config.predecessor_manifest_field) != expected_predecessor_hash
        ):
            raise MissionStateError(
                f"invalid_{self.config.family}_predecessor",
                f"{self.config.family} input does not name the current predecessor",
            )
        final_dir = self.sets_dir / set_id
        if final_dir.exists() or final_dir.is_symlink():
            snapshot = self._validate_set(final_dir, expected_id=set_id)
            self._require_exact_existing(snapshot, artifacts, manifest)
        else:
            payloads = {**artifacts, self.config.manifest_name: canonical_json_bytes(manifest)}
            self._write_set(final_dir, payloads)
            snapshot = self._validate_set(final_dir, expected_id=set_id)
        self._select(snapshot)
        return self.load_current(required=True)

    def load_current(self, *, required: bool = True) -> AuthoritySnapshot | None:
        self._validate_root(allow_absent=not required)
        pointer = self._load_pointer(required=required)
        _, head = self._validated_chain()
        if pointer is None:
            if head is not None:
                raise MissionStateError(f"missing_{self.config.family}_current", "complete authority exists without a selector")
            return None
        if head is None or pointer.set_id != head.set_id:
            raise MissionStateError(f"stale_{self.config.family}_selector", "selector does not name the unique chain head")
        return pointer

    def load_predecessor_for_update(self) -> AuthoritySnapshot | None:
        """Return the selected predecessor while tolerating one crash-complete successor."""
        self._validate_root(allow_absent=True)
        pointer = self._load_pointer(required=False)
        self._validated_chain()
        return pointer

    def preserve_staged_created_at(
        self,
        *,
        set_id: str,
        artifact_name: str,
        expected_without_created_at: dict[str, Any],
        fallback: str,
    ) -> str:
        """Reuse the timestamp already written by an exact-set crash attempt."""
        if artifact_name not in self.config.artifacts:
            raise MissionStateError(
                f"invalid_{self.config.family}_artifact",
                "created-at recovery names an unknown authority artifact",
            )
        candidates: list[Path] = []
        final_path = self.sets_dir / set_id / artifact_name
        if final_path.exists() or final_path.is_symlink():
            candidates.append(final_path)
        elif self.sets_dir.is_dir():
            pattern = re.compile(
                rf"^\.staging-{re.escape(set_id)}-[0-9a-f]{{32}}$"
            )
            for directory in sorted(self.sets_dir.iterdir(), key=lambda path: path.name):
                if pattern.fullmatch(directory.name) is None:
                    continue
                directory = _safe_directory(directory, self.sets_dir)
                candidate = directory / artifact_name
                if candidate.exists() or candidate.is_symlink():
                    candidates.append(candidate)

        timestamps: set[str] = set()
        for candidate in candidates:
            candidate = _regular_file(
                candidate,
                root=candidate.parent,
                label=f"staged {artifact_name}",
            )
            payload, raw = read_json_object_strict(
                candidate,
                label=f"staged {artifact_name}",
            )
            if raw != pretty_json_bytes(payload):
                raise MissionStateError(
                    f"noncanonical_{self.config.family}_staged_artifact",
                    "staged authority sidecar is noncanonical",
                )
            created_at = normalize_reviewed_at(payload.get("created_at"))
            without_created_at = dict(payload)
            without_created_at.pop("created_at", None)
            if without_created_at != expected_without_created_at:
                raise MissionStateError(
                    f"conflicting_{self.config.family}_staged_artifact",
                    "staged authority sidecar differs from exact input replay",
                )
            timestamps.add(created_at)
        if len(timestamps) > 1:
            raise MissionStateError(
                f"conflicting_{self.config.family}_staged_timestamp",
                "exact-set staging residues disagree on created_at",
            )
        return next(iter(timestamps), normalize_reviewed_at(fallback))

    def _manifest(
        self,
        *,
        set_id: str,
        identity: dict[str, Any],
        artifacts: dict[str, bytes],
    ) -> dict[str, Any]:
        return {
            "schema_version": self.config.manifest_schema,
            self.config.set_id_field: set_id,
            self.config.semantic_field: set_id.split("-", 1)[1],
            **{key: value for key, value in identity.items() if key != "schema_version"},
            "artifacts": [
                {
                    "name": name,
                    "role": self.config.artifacts[name],
                    "sha256": sha256_bytes(artifacts[name]),
                    "size_bytes": len(artifacts[name]),
                }
                for name in sorted(artifacts)
            ],
        }

    def _load_pointer(self, *, required: bool) -> AuthoritySnapshot | None:
        if not self.current_path.exists():
            if required:
                raise MissionStateError(f"missing_{self.config.family}_current", f"{self.config.current_name} is required")
            return None
        pointer, raw = _read_canonical(self.current_path, self.config.current_name)
        manifest_hash_field = self.config.current_manifest_field
        require_exact_keys(
            pointer,
            {"schema_version", self.config.set_id_field, manifest_hash_field},
            self.config.current_name,
        )
        set_id = pointer.get(self.config.set_id_field)
        if (
            pointer.get("schema_version") != self.config.current_schema
            or not isinstance(set_id, str)
            or not set_id.startswith(self.config.id_prefix + "-")
            or SET_ID_RE.fullmatch(set_id) is None
        ):
            raise MissionStateError(f"invalid_{self.config.family}_current", "authority selector is invalid")
        require_sha256(pointer.get(manifest_hash_field), field=manifest_hash_field)
        snapshot = self._validate_set(_safe_directory(self.sets_dir / set_id, self.sets_dir), expected_id=set_id)
        if sha256_file(snapshot.set_dir / self.config.manifest_name) != pointer[manifest_hash_field]:
            raise MissionStateError(f"corrupt_{self.config.family}_current", "selected manifest digest differs")
        if raw != canonical_json_bytes(pointer):
            raise MissionStateError(f"noncanonical_{self.config.family}_current", "authority selector is noncanonical")
        return snapshot

    def _validate_set(self, directory: Path, *, expected_id: str) -> AuthoritySnapshot:
        directory = _safe_directory(directory, self.sets_dir)
        expected_names = {*self.config.artifacts, self.config.manifest_name}
        children = list(directory.iterdir())
        if {path.name for path in children} != expected_names or any(
            path.is_symlink() or not path.is_file() for path in children
        ):
            raise MissionStateError(f"unexpected_{self.config.family}_set_path", "authority set has unexpected children")
        manifest, raw = _read_canonical(directory / self.config.manifest_name, f"{self.config.family} manifest")
        identity_fields = {
            key: value
            for key, value in manifest.items()
            if key not in {
                "schema_version",
                self.config.set_id_field,
                self.config.semantic_field,
                "artifacts",
            }
        }
        if set(identity_fields) != set(self.config.identity_fields):
            raise MissionStateError(
                f"invalid_{self.config.family}_identity",
                f"{self.config.family} manifest identity fields do not match the exact schema",
            )
        artifact_paths = {name: _regular_file(directory / name, root=directory, label=name) for name in self.config.artifacts}
        artifacts = {name: path.read_bytes() for name, path in artifact_paths.items()}
        expected_manifest = self._manifest(
            set_id=expected_id,
            identity={"schema_version": self.config.identity_schema, **identity_fields},
            artifacts=artifacts,
        )
        if (
            manifest.get("schema_version") != self.config.manifest_schema
            or manifest.get(self.config.set_id_field) != expected_id
            or manifest != expected_manifest
            or raw != canonical_json_bytes(manifest)
        ):
            raise MissionStateError(f"invalid_{self.config.family}_manifest", "authority manifest does not replay")
        identity = {"schema_version": self.config.identity_schema, **identity_fields}
        if expected_id != f"{self.config.id_prefix}-{sha256_bytes(canonical_json_bytes(identity))}":
            raise MissionStateError(f"invalid_{self.config.family}_identity", "authority set identity differs")
        snapshot = AuthoritySnapshot(
            set_id=expected_id,
            set_dir=directory,
            manifest=manifest,
            artifact_paths=artifact_paths,
            recovery=self._recovery_report(),
        )
        if self.semantic_validator is not None:
            self.semantic_validator(snapshot)
        return snapshot

    def _validated_chain(self) -> tuple[dict[str, AuthoritySnapshot], AuthoritySnapshot | None]:
        snapshots: dict[str, AuthoritySnapshot] = {}
        if self.sets_dir.is_dir():
            for path in sorted(self.sets_dir.iterdir(), key=lambda item: item.name):
                if path.name.startswith(self.config.id_prefix + "-"):
                    snapshots[path.name] = self._validate_set(path, expected_id=path.name)
        if not snapshots:
            return snapshots, None
        children = {set_id: [] for set_id in snapshots}
        roots: list[str] = []
        for set_id, snapshot in snapshots.items():
            predecessor_id = snapshot.manifest[self.config.predecessor_id_field]
            predecessor_hash = snapshot.manifest[self.config.predecessor_manifest_field]
            if (predecessor_id is None) != (predecessor_hash is None):
                raise MissionStateError(f"invalid_{self.config.family}_predecessor", "predecessor pair is partial")
            if predecessor_id is None:
                roots.append(set_id)
                continue
            predecessor = snapshots.get(predecessor_id)
            if predecessor is None:
                raise MissionStateError(f"missing_{self.config.family}_predecessor", "authority predecessor is missing")
            if sha256_file(predecessor.set_dir / self.config.manifest_name) != predecessor_hash:
                raise MissionStateError(f"stale_{self.config.family}_predecessor", "predecessor manifest hash differs")
            children[predecessor_id].append(set_id)
        if len(roots) != 1 or any(len(values) > 1 for values in children.values()):
            raise MissionStateError(f"invalid_{self.config.family}_chain", "authority sets must form one nonforking chain")
        visited: set[str] = set()
        cursor = roots[0]
        while cursor not in visited:
            visited.add(cursor)
            if not children[cursor]:
                break
            cursor = children[cursor][0]
        if len(visited) != len(snapshots):
            raise MissionStateError(f"invalid_{self.config.family}_chain", "authority chain is cyclic or disconnected")
        return snapshots, snapshots[cursor]

    def _ensure_root(self) -> None:
        assert_public_write_path_allowed(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise MissionStateError(f"unsafe_{self.config.family}_root", "authority root is unsafe")
        if not self.sets_dir.exists():
            self.sets_dir.mkdir()
            _fsync_directory(self.root)
        self._validate_root(allow_absent=False)

    def _validate_root(self, *, allow_absent: bool) -> None:
        if not self.root.exists():
            if allow_absent:
                return
            raise MissionStateError(f"missing_{self.config.family}_root", "authority root is missing")
        if self.root.is_symlink() or not self.root.is_dir():
            raise MissionStateError(f"unsafe_{self.config.family}_root", "authority root is unsafe")
        pointer_temps = {
            re.compile(rf"^\.{re.escape(name)}\.[0-9a-f]{{32}}\.tmp$")
            for name in self.config.root_allowed_names
            if name.endswith("CURRENT")
        }
        for path in self.root.iterdir():
            if path.name in self.config.root_allowed_names:
                if path.name.endswith("_sets") and (path.is_symlink() or not path.is_dir()):
                    raise MissionStateError(f"unsafe_{self.config.family}_root", f"unsafe authority root child: {path.name}")
                if path.name.endswith("CURRENT") and (path.is_symlink() or not path.is_file()):
                    raise MissionStateError(f"unsafe_{self.config.family}_root", f"unsafe authority root child: {path.name}")
            elif any(pattern.fullmatch(path.name) for pattern in pointer_temps):
                if path.is_symlink() or not path.is_file():
                    raise MissionStateError(f"unsafe_{self.config.family}_temp", "selector temp is unsafe")
            else:
                raise MissionStateError(f"unexpected_{self.config.family}_path", f"unexpected root child: {path.name}")
        if self.sets_dir.exists():
            staging = re.compile(rf"^\.staging-{self.config.id_prefix}-[0-9a-f]{{64}}-[0-9a-f]{{32}}$")
            for path in self.sets_dir.iterdir():
                if path.is_symlink() or not path.is_dir():
                    raise MissionStateError(f"unsafe_{self.config.family}_set", f"unsafe set child: {path.name}")
                if not path.name.startswith(self.config.id_prefix + "-") and staging.fullmatch(path.name) is None:
                    raise MissionStateError(f"unexpected_{self.config.family}_set_path", f"unexpected set child: {path.name}")

    def _write_set(self, final_dir: Path, payloads: dict[str, bytes]) -> None:
        nonce = self._nonce()
        staging = self.sets_dir / f".staging-{final_dir.name}-{nonce}"
        if staging.exists() or staging.is_symlink() or final_dir.exists() or final_dir.is_symlink():
            raise MissionStateError(f"{self.config.family}_set_collision", "authority staging or final path exists")
        staging.mkdir()
        _fsync_directory(self.sets_dir)
        self._crash("after_staging_parent_fsync")
        order = [*sorted(self.config.artifacts), self.config.manifest_name]
        for name in order:
            path = staging / name
            with path.open("xb") as handle:
                handle.write(payloads[name])
                self._crash(f"{name}:after_write")
                handle.flush()
                os.fsync(handle.fileno())
            self._crash(f"{name}:after_fsync")
        _fsync_directory(staging)
        self._crash("after_staging_fsync")
        os.rename(staging, final_dir)
        self._crash("after_final_rename")
        _fsync_directory(self.sets_dir)
        self._crash("after_sets_fsync")

    def _select(self, snapshot: AuthoritySnapshot) -> None:
        manifest_hash_field = self.config.current_manifest_field
        pointer = {
            "schema_version": self.config.current_schema,
            self.config.set_id_field: snapshot.set_id,
            manifest_hash_field: sha256_file(snapshot.set_dir / self.config.manifest_name),
        }
        nonce = self._nonce()
        temporary = self.root / f".{self.config.current_name}.{nonce}.tmp"
        if temporary.exists() or temporary.is_symlink():
            raise MissionStateError(f"{self.config.family}_temp_collision", "selector temp exists")
        with temporary.open("xb") as handle:
            value = canonical_json_bytes(pointer)
            handle.write(value)
            self._crash("current:after_temp_write")
            handle.flush()
            os.fsync(handle.fileno())
        self._crash("current:after_temp_fsync")
        os.replace(temporary, self.current_path)
        self._crash("current:after_replace")
        _fsync_directory(self.root)
        self._crash("current:after_directory_fsync")

    def _require_exact_existing(
        self,
        snapshot: AuthoritySnapshot,
        artifacts: dict[str, bytes],
        manifest: dict[str, Any],
    ) -> None:
        if snapshot.manifest != manifest or any(
            snapshot.artifact_paths[name].read_bytes() != value for name, value in artifacts.items()
        ):
            raise MissionStateError(f"{self.config.family}_set_collision", "existing authority bytes conflict")

    def _validate_artifact_names(self, artifacts: dict[str, bytes]) -> None:
        if set(artifacts) != set(self.config.artifacts) or any(not isinstance(value, bytes) for value in artifacts.values()):
            raise MissionStateError(f"invalid_{self.config.family}_artifacts", "authority artifact set is incomplete")

    def _nonce(self) -> str:
        value = self.nonce_factory()
        if not isinstance(value, str) or NONCE_RE.fullmatch(value) is None:
            raise MissionStateError(f"invalid_{self.config.family}_nonce", "authority nonce is invalid")
        return value

    def _crash(self, suffix: str) -> None:
        if self.crash_hook is not None:
            self.crash_hook(f"{self.config.family}:{suffix}")

    def _recovery_report(self) -> dict[str, list[str]]:
        if not self.root.is_dir():
            return {"temp_files": [], "staging_directories": []}
        temps = sorted(path.name for path in self.root.iterdir() if path.name.startswith(f".{self.config.current_name}.") )
        staging = sorted(path.name for path in self.sets_dir.iterdir() if path.name.startswith(".staging-")) if self.sets_dir.is_dir() else []
        return {"temp_files": temps, "staging_directories": staging}


def _read_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    payload, raw = read_json_object_strict(path, label=label)
    if raw != canonical_json_bytes(payload):
        raise MissionStateError("noncanonical_authority_state", f"{label} is not canonical compact JSON")
    return payload, raw


def _safe_directory(path: Path, parent: Path) -> Path:
    if path.is_symlink() or not path.is_dir() or path.resolve().parent != parent.resolve():
        raise MissionStateError("unsafe_authority_directory", f"unsafe authority directory: {path}")
    return path.resolve()


def _regular_file(path: Path, *, root: Path, label: str) -> Path:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("missing_evidence_artifact", f"{label} is missing: {path}") from exc
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise MissionStateError("unsafe_evidence_artifact", f"{label} escapes the mission root") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise MissionStateError("unsafe_evidence_artifact", f"{label} is not a regular nonsymlink file")
    return path.absolute()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "AuthorityConfig",
    "AuthoritySnapshot",
    "EvidenceContext",
    "ImmutableAuthorityManager",
    "SourceIdentity",
    "canonical_semantic_bytes",
    "load_v2_evidence_context",
    "require_sha256",
    "strict_string_list",
]
