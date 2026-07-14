from __future__ import annotations

import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from research_assistant.survey.evidence_semantics import load_v2_evidence_context
from research_assistant.survey.artifact_lineage import ArtifactStateManager
from research_assistant.survey.review_decisions import (
    COMMON_SIDECAR_KEYS,
    ReviewDecisionContext,
    common_sidecar_fields,
    decision_context_from_snapshot,
    load_bound_decision_envelope,
    normalize_required_text,
    normalize_reviewed_at,
    require_exact_keys,
    read_json_object_strict,
    utc_now_iso,
    validate_bound_decision_envelope,
    validate_exact_decisions,
    validate_sidecar_binding,
)


SURVEY_REVIEWED_OMISSION_RESULT_SCHEMA_VERSION = "ra-survey-reviewed-omission-import-result-v2"
SURVEY_REVIEWED_OMISSION_SCHEMA_VERSION = "ra-survey-reviewed-omission-risks-v2"

REVIEWED_OMISSION_NONCLAIMS = [
    "literature completeness",
    "final prose readiness",
    "live web coverage",
    "product readiness",
    "real-agent reliability",
    "scientific correctness",
]
SUPPORTED_OMISSION_DECISIONS = {"acceptable_omission", "must_inspect", "expand_scope", "blocked_pending_source", "out_of_scope"}
OPEN_OMISSION_DECISIONS = {"must_inspect", "expand_scope", "blocked_pending_source"}
V2_OMISSION_TRANSITIONS = {
    "inspect_next": {"must_inspect", "expand_scope"},
    "omit_with_reason": SUPPORTED_OMISSION_DECISIONS,
    "quarantine": {"expand_scope", "blocked_pending_source"},
    "blocked_source_or_frontier": SUPPORTED_OMISSION_DECISIONS,
}
OMISSION_DECISION_SET_IDENTITY_SCHEMA = "ra-survey-omission-decision-set-identity-v1"
OMISSION_DECISION_SET_MANIFEST_SCHEMA = "ra-survey-omission-decision-set-manifest-v1"
OMISSION_DECISION_CURRENT_SCHEMA = "ra-survey-omission-decision-current-v1"
OD_SET_RE = re.compile(r"^od-[0-9a-f]{64}$")
OD_STAGING_RE = re.compile(r"^\.staging-(od-[0-9a-f]{64})-([0-9a-f]{32})$")
OD_CURRENT_TEMP_RE = re.compile(r"^\.DECISION_CURRENT\.([0-9a-f]{32})\.tmp$")
OMISSION_COMMON_INPUT_KEYS = {"queue_item_id", "risk_id", "decision", "reason", "reviewer", "reviewed_at"}
OMISSION_SIDECAR_KEYS = COMMON_SIDECAR_KEYS | {
    "omission_risks",
    "rejected_omission_risks",
    "coverage_errors",
    "accepted_omission_count",
    "rejected_omission_count",
    "closed_omission_count",
    "open_omission_count",
    "literature_completeness_allowed",
}


@dataclass(frozen=True)
class OmissionDecisionSetSnapshot:
    decision_set_id: str
    set_dir: Path
    decisions_path: Path
    sidecar_path: Path
    manifest: dict[str, Any]
    recovery: dict[str, list[str]]


class OmissionDecisionStateManager:
    def __init__(
        self,
        *,
        context: ReviewDecisionContext,
        output_dir: Path,
        nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
        crash_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.context = context
        self.output_dir = output_dir.absolute()
        self.sets_dir = self.output_dir / "decision_sets"
        self.current_path = self.output_dir / "DECISION_CURRENT"
        self.nonce_factory = nonce_factory
        self.crash_hook = crash_hook

    def compose_and_select(
        self,
        *,
        decisions_path: Path,
        decisions_raw: bytes,
        sidecar_payload: dict[str, Any],
        force: bool = False,
    ) -> OmissionDecisionSetSnapshot:
        self._ensure_root()
        pointer = self._load_pointer(required=False, require_current=False)
        snapshots, head = self._validated_chain()
        selected = pointer
        if head is not None and (pointer is None or pointer.decision_set_id != head.decision_set_id):
            expected_predecessor = pointer.decision_set_id if pointer is not None else None
            immediate_orphan = head.manifest["predecessor_decision_set_id"] == expected_predecessor
            same_bytes = (
                head.manifest["decisions_sha256"] == sha256_bytes(decisions_raw)
                and head.manifest["decisions_size_bytes"] == len(decisions_raw)
            )
            if not immediate_orphan:
                raise MissionStateError(
                    "stale_omission_decision_selector",
                    "DECISION_CURRENT is more than one generation behind the decision-chain head",
                )
            try:
                self._require_current_context(head)
            except MissionStateError as exc:
                if exc.code != "stale_lineage" or not force or same_bytes:
                    raise
                selected = head
            else:
                if not same_bytes:
                    raise MissionStateError(
                        "stale_omission_decision_selector",
                        "a current-lineage orphan can only be recovered by exact-byte retry",
                    )
                self._select(head)
                return self.load_current(required=True)
        if selected is not None and (
            selected.manifest["decisions_sha256"] == sha256_bytes(decisions_raw)
            and selected.manifest["decisions_size_bytes"] == len(decisions_raw)
        ):
            self._require_current_context(selected)
            return self.load_current(required=True)
        if selected is not None and not force:
            raise MissionStateError("output_exists", "a different omission decision set is already selected")
        predecessor_id = selected.decision_set_id if selected is not None else None
        predecessor_manifest_sha256 = (
            sha256_file(selected.set_dir / "decision_set_manifest.json")
            if selected is not None
            else None
        )
        identity = self._identity(
            decisions_raw,
            predecessor_id=predecessor_id,
            predecessor_manifest_sha256=predecessor_manifest_sha256,
        )
        decision_set_id = f"od-{sha256_bytes(canonical_json_bytes(identity))}"
        final_dir = self.sets_dir / decision_set_id
        if final_dir.exists() or final_dir.is_symlink():
            snapshot = self._validate_set(final_dir, expected_id=decision_set_id)
        else:
            copied_decisions = final_dir / "reviewed_omission_decisions.json"
            sidecar = dict(sidecar_payload)
            sidecar["decisions_path"] = str(copied_decisions)
            sidecar["decisions_sha256"] = sha256_bytes(decisions_raw)
            sidecar_bytes = pretty_json_bytes(sidecar)
            manifest = self._manifest(
                decision_set_id=decision_set_id,
                identity=identity,
                decisions_raw=decisions_raw,
                sidecar_bytes=sidecar_bytes,
            )
            self._write_set(
                final_dir,
                {
                    "reviewed_omission_decisions.json": decisions_raw,
                    "reviewed_omission_risks.json": sidecar_bytes,
                    "decision_set_manifest.json": canonical_json_bytes(manifest),
                },
            )
            snapshot = self._validate_set(final_dir, expected_id=decision_set_id)
        self._select(snapshot)
        return self.load_current(required=True)

    def load_current(self, *, required: bool = True) -> OmissionDecisionSetSnapshot | None:
        self._validate_root(allow_absent=not required)
        pointer = self._load_pointer(required=required, require_current=False)
        snapshots, head = self._validated_chain()
        if pointer is None:
            if head is not None:
                raise MissionStateError(
                    "missing_omission_decision_current",
                    "complete decision authority exists without DECISION_CURRENT",
                )
            return None
        if head is None or pointer.decision_set_id != head.decision_set_id:
            raise MissionStateError(
                "stale_omission_decision_selector",
                "DECISION_CURRENT does not name the unique decision-chain head",
            )
        self._require_current_context(pointer)
        return pointer

    def _load_pointer(
        self,
        *,
        required: bool,
        require_current: bool,
    ) -> OmissionDecisionSetSnapshot | None:
        recovery = self._recovery_report()
        if not self.current_path.exists():
            if required:
                raise MissionStateError("missing_omission_decision_current", "DECISION_CURRENT is required")
            return None
        pointer, pointer_raw = _read_canonical_json(self.current_path, "omission DECISION_CURRENT")
        require_exact_keys(
            pointer,
            {"schema_version", "decision_set_id", "decision_set_manifest_sha256"},
            "omission DECISION_CURRENT",
        )
        decision_set_id = pointer.get("decision_set_id")
        if (
            pointer.get("schema_version") != OMISSION_DECISION_CURRENT_SCHEMA
            or not isinstance(decision_set_id, str)
            or OD_SET_RE.fullmatch(decision_set_id) is None
            or not _is_sha256(pointer.get("decision_set_manifest_sha256"))
        ):
            raise MissionStateError("invalid_omission_decision_current", "DECISION_CURRENT is invalid")
        set_dir = _safe_child_directory(self.sets_dir, decision_set_id)
        snapshot = self._validate_set(set_dir, expected_id=decision_set_id)
        if sha256_file(set_dir / "decision_set_manifest.json") != pointer["decision_set_manifest_sha256"]:
            raise MissionStateError("corrupt_omission_decision_current", "selected manifest digest differs")
        if canonical_json_bytes(pointer) != pointer_raw:
            raise MissionStateError("noncanonical_omission_decision_current", "DECISION_CURRENT is noncanonical")
        result = OmissionDecisionSetSnapshot(
            decision_set_id=decision_set_id,
            set_dir=set_dir,
            decisions_path=set_dir / "reviewed_omission_decisions.json",
            sidecar_path=set_dir / "reviewed_omission_risks.json",
            manifest=snapshot.manifest,
            recovery=recovery,
        )
        if require_current:
            self._require_current_context(result)
        return result

    def _identity(
        self,
        decisions_raw: bytes,
        *,
        predecessor_id: str | None,
        predecessor_manifest_sha256: str | None,
    ) -> dict[str, Any]:
        queue = self.context.review_queue
        return {
            "schema_version": OMISSION_DECISION_SET_IDENTITY_SCHEMA,
            "mission_id": queue["mission_id"],
            "mission_fingerprint": queue["mission_fingerprint"],
            "mission_anchor_generation_id": queue["mission_anchor_generation_id"],
            "artifact_set_id": queue["artifact_set_id"],
            "queue_semantic_sha256": queue["queue_semantic_sha256"],
            "review_queue_sha256": self.context.review_queue_sha256,
            "predecessor_decision_set_id": predecessor_id,
            "predecessor_manifest_sha256": predecessor_manifest_sha256,
            "decisions_sha256": sha256_bytes(decisions_raw),
            "decisions_size_bytes": len(decisions_raw),
        }

    def _manifest(
        self,
        *,
        decision_set_id: str,
        identity: dict[str, Any],
        decisions_raw: bytes,
        sidecar_bytes: bytes,
    ) -> dict[str, Any]:
        return {
            "schema_version": OMISSION_DECISION_SET_MANIFEST_SCHEMA,
            "decision_set_id": decision_set_id,
            "decision_set_semantic_sha256": decision_set_id[3:],
            **{key: value for key, value in identity.items() if key != "schema_version"},
            "artifacts": [
                {
                    "name": "reviewed_omission_decisions.json",
                    "sha256": sha256_bytes(decisions_raw),
                    "size_bytes": len(decisions_raw),
                    "role": "complete_decision_envelope",
                },
                {
                    "name": "reviewed_omission_risks.json",
                    "sha256": sha256_bytes(sidecar_bytes),
                    "size_bytes": len(sidecar_bytes),
                    "role": "normalized_reviewed_omissions",
                },
            ],
        }

    def _validate_set(self, directory: Path, *, expected_id: str) -> OmissionDecisionSetSnapshot:
        directory = _safe_child_directory(self.sets_dir, expected_id)
        manifest, manifest_raw = _read_canonical_json(
            directory / "decision_set_manifest.json",
            "omission decision-set manifest",
        )
        expected_manifest_keys = {
            "schema_version",
            "decision_set_id",
            "decision_set_semantic_sha256",
            "mission_id",
            "mission_fingerprint",
            "mission_anchor_generation_id",
            "artifact_set_id",
            "queue_semantic_sha256",
            "review_queue_sha256",
            "predecessor_decision_set_id",
            "predecessor_manifest_sha256",
            "decisions_sha256",
            "decisions_size_bytes",
            "artifacts",
        }
        require_exact_keys(manifest, expected_manifest_keys, "omission decision-set manifest")
        if (
            manifest.get("schema_version") != OMISSION_DECISION_SET_MANIFEST_SCHEMA
            or manifest.get("decision_set_id") != expected_id
            or manifest.get("decision_set_semantic_sha256") != expected_id[3:]
        ):
            raise MissionStateError("invalid_omission_decision_set", "decision-set identity is invalid")
        decisions_path = _regular_child(directory, "reviewed_omission_decisions.json")
        sidecar_path = _regular_child(directory, "reviewed_omission_risks.json")
        actual_files = {
            path.name
            for path in directory.iterdir()
            if path.is_file() and not path.is_symlink()
        }
        if actual_files != {
            "reviewed_omission_decisions.json",
            "reviewed_omission_risks.json",
            "decision_set_manifest.json",
        } or any(path.is_symlink() or not path.is_file() for path in directory.iterdir()):
            raise MissionStateError("unexpected_omission_decision_set_path", "decision set has unexpected children")
        decisions_raw = decisions_path.read_bytes()
        predecessor_id = manifest.get("predecessor_decision_set_id")
        predecessor_manifest_sha256 = manifest.get("predecessor_manifest_sha256")
        if (predecessor_id is None) != (predecessor_manifest_sha256 is None):
            raise MissionStateError(
                "invalid_omission_decision_predecessor",
                "predecessor ID and manifest digest must both be null or both be present",
            )
        if predecessor_id is not None and (
            not isinstance(predecessor_id, str)
            or OD_SET_RE.fullmatch(predecessor_id) is None
            or not _is_sha256(predecessor_manifest_sha256)
        ):
            raise MissionStateError(
                "invalid_omission_decision_predecessor",
                "decision-set predecessor binding is invalid",
            )
        # Replay immutable bytes against the binding they committed. Current-queue
        # compatibility is checked separately below so obsolete authority is
        # reported as stale lineage rather than corrupt stored bytes.
        identity = {
            "schema_version": OMISSION_DECISION_SET_IDENTITY_SCHEMA,
            "mission_id": manifest["mission_id"],
            "mission_fingerprint": manifest["mission_fingerprint"],
            "mission_anchor_generation_id": manifest["mission_anchor_generation_id"],
            "artifact_set_id": manifest["artifact_set_id"],
            "queue_semantic_sha256": manifest["queue_semantic_sha256"],
            "review_queue_sha256": manifest["review_queue_sha256"],
            "predecessor_decision_set_id": predecessor_id,
            "predecessor_manifest_sha256": predecessor_manifest_sha256,
            "decisions_sha256": sha256_bytes(decisions_raw),
            "decisions_size_bytes": len(decisions_raw),
        }
        if manifest != self._manifest(
            decision_set_id=expected_id,
            identity=identity,
            decisions_raw=decisions_raw,
            sidecar_bytes=sidecar_path.read_bytes(),
        ):
            raise MissionStateError("omission_decision_manifest_mismatch", "decision-set manifest does not replay")
        if expected_id != f"od-{sha256_bytes(canonical_json_bytes(identity))}":
            raise MissionStateError("omission_decision_identity_mismatch", "decision-set semantic identity differs")
        envelope, replayed_raw = read_json_object_strict(decisions_path, label="selected omission decisions")
        if replayed_raw != decisions_raw or replayed_raw != pretty_json_bytes(envelope):
            raise MissionStateError("stale_omission_decisions", "selected decision bytes changed during replay")
        committed_context = self._committed_context(manifest)
        rows = validate_bound_decision_envelope(context=committed_context, decisions=envelope)
        result = validate_exact_decisions(context=committed_context, rows=rows, validator=_validate_decision)
        if not result.complete:
            raise MissionStateError("incomplete_omission_decision_set", "selected decision set is not complete")
        sidecar, _ = validate_sidecar_binding(
            path=sidecar_path,
            context=committed_context,
            expected_schema=SURVEY_REVIEWED_OMISSION_SCHEMA_VERSION,
            expected_keys=OMISSION_SIDECAR_KEYS,
            decisions_field="omission_risks",
            rejected_field="rejected_omission_risks",
            validator=_validate_decision,
            expected_fields=omission_sidecar_expected_fields,
        )
        if sidecar.get("decisions_path") != str(decisions_path):
            raise MissionStateError("mixed_omission_decision_set", "sidecar does not name its immutable envelope")
        if canonical_json_bytes(manifest) != manifest_raw:
            raise MissionStateError("noncanonical_omission_decision_set", "decision-set manifest is noncanonical")
        return OmissionDecisionSetSnapshot(
            decision_set_id=expected_id,
            set_dir=directory,
            decisions_path=decisions_path,
            sidecar_path=sidecar_path,
            manifest=manifest,
            recovery=self._recovery_report(),
        )

    def _committed_context(self, manifest: dict[str, Any]) -> ReviewDecisionContext:
        current_snapshot = self.context.snapshot
        artifact_set_id = manifest.get("artifact_set_id")
        if not isinstance(artifact_set_id, str):
            raise MissionStateError(
                "invalid_omission_decision_set",
                "decision set does not name an artifact set",
            )
        manager = ArtifactStateManager(
            mission_root=current_snapshot.mission_root,
            mission_id=self.context.review_queue["mission_id"],
            mission_fingerprint=self.context.review_queue["mission_fingerprint"],
            mission_anchor_generation_id=self.context.review_queue["mission_anchor_generation_id"],
        )
        try:
            snapshot = manager.validate_retained_set(artifact_set_id)
        except MissionStateError as exc:
            raise MissionStateError(
                "invalid_omission_decision_artifact_set",
                f"decision set names an invalid retained artifact set: {exc}",
            ) from exc
        context = decision_context_from_snapshot(
            snapshot=snapshot,
            decision_type="omission_risk",
        )
        self._require_manifest_context(manifest, context, current=False)
        return context

    def _require_current_context(self, snapshot: OmissionDecisionSetSnapshot) -> None:
        self._require_manifest_context(snapshot.manifest, self.context, current=True)

    @staticmethod
    def _require_manifest_context(
        manifest: dict[str, Any],
        context: ReviewDecisionContext,
        *,
        current: bool,
    ) -> None:
        expected = {
            "mission_id": context.review_queue["mission_id"],
            "mission_fingerprint": context.review_queue["mission_fingerprint"],
            "mission_anchor_generation_id": context.review_queue["mission_anchor_generation_id"],
            "artifact_set_id": context.review_queue["artifact_set_id"],
            "queue_semantic_sha256": context.review_queue["queue_semantic_sha256"],
            "review_queue_sha256": context.review_queue_sha256,
        }
        for field, value in expected.items():
            if manifest.get(field) != value:
                code = "stale_lineage" if current else "omission_decision_lineage_mismatch"
                raise MissionStateError(
                    code,
                    f"omission decision-set {field} does not match "
                    + ("the selected queue" if current else "its committed queue"),
                )

    def _validated_chain(
        self,
    ) -> tuple[dict[str, OmissionDecisionSetSnapshot], OmissionDecisionSetSnapshot | None]:
        snapshots: dict[str, OmissionDecisionSetSnapshot] = {}
        if self.sets_dir.is_dir():
            for path in sorted(self.sets_dir.iterdir(), key=lambda item: item.name):
                if OD_SET_RE.fullmatch(path.name):
                    snapshots[path.name] = self._validate_set(path, expected_id=path.name)
        if not snapshots:
            return snapshots, None
        children = {decision_set_id: [] for decision_set_id in snapshots}
        roots: list[str] = []
        for decision_set_id, snapshot in snapshots.items():
            predecessor_id = snapshot.manifest["predecessor_decision_set_id"]
            predecessor_digest = snapshot.manifest["predecessor_manifest_sha256"]
            if predecessor_id is None:
                roots.append(decision_set_id)
                continue
            predecessor = snapshots.get(predecessor_id)
            if predecessor is None:
                raise MissionStateError(
                    "missing_omission_decision_predecessor",
                    f"decision set {decision_set_id} names a missing predecessor",
                )
            if sha256_file(predecessor.set_dir / "decision_set_manifest.json") != predecessor_digest:
                raise MissionStateError(
                    "stale_omission_decision_predecessor",
                    f"decision set {decision_set_id} predecessor digest differs",
                )
            children[predecessor_id].append(decision_set_id)
        if len(roots) != 1 or any(len(values) > 1 for values in children.values()):
            raise MissionStateError(
                "invalid_omission_decision_chain",
                "decision sets must form one nonforking append-only chain",
            )
        visited: set[str] = set()
        cursor = roots[0]
        while cursor not in visited:
            visited.add(cursor)
            descendants = children[cursor]
            if not descendants:
                break
            cursor = descendants[0]
        if len(visited) != len(snapshots):
            raise MissionStateError(
                "invalid_omission_decision_chain",
                "decision-set predecessor graph is cyclic or disconnected",
            )
        return snapshots, snapshots[cursor]

    def _select(self, snapshot: OmissionDecisionSetSnapshot) -> None:
        pointer = {
            "schema_version": OMISSION_DECISION_CURRENT_SCHEMA,
            "decision_set_id": snapshot.decision_set_id,
            "decision_set_manifest_sha256": sha256_file(
                snapshot.set_dir / "decision_set_manifest.json"
            ),
        }
        self._atomic_pointer(canonical_json_bytes(pointer))

    def _ensure_root(self) -> None:
        from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed

        assert_public_write_path_allowed(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.output_dir.is_symlink() or not self.output_dir.is_dir():
            raise MissionStateError("unsafe_omission_decision_root", "reviewed omissions root is unsafe")
        if not self.sets_dir.exists():
            self.sets_dir.mkdir()
            _fsync_directory(self.output_dir)
        self._validate_root(allow_absent=False)

    def _validate_root(self, *, allow_absent: bool) -> None:
        if not self.output_dir.exists():
            if allow_absent:
                return
            raise MissionStateError("missing_omission_decision_root", "reviewed omissions root is missing")
        if self.output_dir.is_symlink() or not self.output_dir.is_dir():
            raise MissionStateError("unsafe_omission_decision_root", "reviewed omissions root is unsafe")
        allowed = {"decision_sets", "DECISION_CURRENT"}
        for path in self.output_dir.iterdir():
            mode = path.lstat().st_mode
            if path.name == "decision_sets":
                if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                    raise MissionStateError("unsafe_omission_decision_root", "decision_sets is unsafe")
            elif path.name == "DECISION_CURRENT":
                if not stat.S_ISREG(mode):
                    raise MissionStateError("unsafe_omission_decision_root", f"unsafe root child: {path.name}")
            elif OD_CURRENT_TEMP_RE.fullmatch(path.name):
                if not stat.S_ISREG(mode):
                    raise MissionStateError("unsafe_omission_decision_temp", "pointer temp is unsafe")
            elif path.name not in allowed:
                raise MissionStateError("unexpected_omission_decision_path", f"unexpected root child: {path.name}")
        if self.sets_dir.exists():
            for path in self.sets_dir.iterdir():
                if path.is_symlink() or not path.is_dir():
                    raise MissionStateError("unsafe_omission_decision_set", f"unsafe set path: {path.name}")
                if OD_SET_RE.fullmatch(path.name) is None and OD_STAGING_RE.fullmatch(path.name) is None:
                    raise MissionStateError("unexpected_omission_decision_set_path", f"unexpected set path: {path.name}")

    def _recovery_report(self) -> dict[str, list[str]]:
        temps = []
        staging = []
        if self.output_dir.is_dir():
            temps = sorted(
                path.name
                for path in self.output_dir.iterdir()
                if OD_CURRENT_TEMP_RE.fullmatch(path.name) and path.is_file() and not path.is_symlink()
            )
        if self.sets_dir.is_dir():
            staging = sorted(
                path.name
                for path in self.sets_dir.iterdir()
                if OD_STAGING_RE.fullmatch(path.name) and path.is_dir() and not path.is_symlink()
            )
            for name in staging:
                _validate_staging(self.sets_dir / name)
        return {"temp_files": temps, "staging_directories": staging}

    def _write_set(self, final_dir: Path, payloads: dict[str, bytes]) -> None:
        nonce = _nonce(self.nonce_factory())
        staging = self.sets_dir / f".staging-{final_dir.name}-{nonce}"
        if staging.exists() or staging.is_symlink() or final_dir.exists() or final_dir.is_symlink():
            raise MissionStateError("omission_decision_set_collision", "decision-set staging or final path exists")
        staging.mkdir()
        _fsync_directory(self.sets_dir)
        if self.crash_hook:
            self.crash_hook("omission_set:after_staging_parent_fsync")
        order = [
            "reviewed_omission_decisions.json",
            "reviewed_omission_risks.json",
            "decision_set_manifest.json",
        ]
        for name in order:
            path = staging / name
            with path.open("xb") as handle:
                handle.write(payloads[name])
                if self.crash_hook:
                    self.crash_hook(f"omission_set:{name}:after_write")
                handle.flush()
                os.fsync(handle.fileno())
            if self.crash_hook:
                self.crash_hook(f"omission_set:{name}:after_fsync")
        _fsync_directory(staging)
        if self.crash_hook:
            self.crash_hook("omission_set:after_staging_fsync")
        os.rename(staging, final_dir)
        if self.crash_hook:
            self.crash_hook("omission_set:after_final_rename")
        _fsync_directory(self.sets_dir)
        if self.crash_hook:
            self.crash_hook("omission_set:after_sets_fsync")

    def _atomic_pointer(self, value: bytes) -> None:
        nonce = _nonce(self.nonce_factory())
        temporary = self.output_dir / f".DECISION_CURRENT.{nonce}.tmp"
        if temporary.exists() or temporary.is_symlink():
            raise MissionStateError("omission_decision_temp_collision", "pointer temp already exists")
        with temporary.open("xb") as handle:
            handle.write(value)
            if self.crash_hook:
                self.crash_hook("omission_current:after_temp_write")
            handle.flush()
            os.fsync(handle.fileno())
        if self.crash_hook:
            self.crash_hook("omission_current:after_temp_fsync")
        os.replace(temporary, self.current_path)
        if self.crash_hook:
            self.crash_hook("omission_current:after_replace")
        _fsync_directory(self.output_dir)
        if self.crash_hook:
            self.crash_hook("omission_current:after_directory_fsync")


def import_reviewed_omissions(
    *,
    review_queue_path: Path,
    decisions_path: Path,
    output_dir: Path,
    force: bool = False,
    now: Callable[[], str] = utc_now_iso,
    nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
    crash_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    output_path = output_dir / "reviewed_omission_risks.json"
    if output_path.exists() and not force:
        return _blocked("output_exists", output_dir, ["rerun with --force or choose a new --out directory"])
    try:
        context, _, rows, decisions_raw = load_bound_decision_envelope(
            review_queue_path=review_queue_path,
            decisions_path=decisions_path,
            decision_type="omission_risk",
        )
    except MissionStateError as exc:
        return _blocked(exc.code, output_dir, [str(exc)])
    if _is_v2_omission_context(context):
        try:
            decisions_payload, _ = read_json_object_strict(decisions_path, label="V2 omission decisions")
        except MissionStateError as exc:
            return _blocked(exc.code, output_dir, [str(exc)])
        if decisions_raw != pretty_json_bytes(decisions_payload):
            return _blocked(
                "noncanonical_omission_decisions",
                output_dir,
                ["V2 omission decisions must be canonical deterministic pretty JSON"],
            )
    result = validate_exact_decisions(context=context, rows=rows, validator=_validate_decision)
    open_count = sum(row["status"] == "open" for row in result.accepted)
    closed_count = sum(row["status"] == "reviewed_closed_for_current_scope" for row in result.accepted)
    payload = {
        "schema_version": SURVEY_REVIEWED_OMISSION_SCHEMA_VERSION,
        **common_sidecar_fields(
            context=context,
            decisions_path=decisions_path,
            decisions_raw=decisions_raw,
            result=result,
            created_at=now(),
        ),
        "omission_risks": result.accepted,
        "rejected_omission_risks": result.rejected,
        "coverage_errors": result.coverage_errors,
        **omission_sidecar_expected_fields(result),
    }
    if _is_v2_omission_context(context):
        if not result.complete:
            return {
                "schema_version": SURVEY_REVIEWED_OMISSION_RESULT_SCHEMA_VERSION,
                "status": "blocked_invalid_omission_decisions",
                "output_dir": str(output_dir),
                "reviewed_omission_risks_path": None,
                "accepted_omission_count": len(result.accepted),
                "rejected_omission_count": len(result.rejected),
                "closed_omission_count": closed_count,
                "open_omission_count": open_count,
                "decision_coverage_complete": False,
                "literature_completeness_allowed": False,
                "ready_for_reviewed_packet": False,
                "ready_for_prose": False,
                "what_is_not_concluded": REVIEWED_OMISSION_NONCLAIMS,
            }
        try:
            manager = OmissionDecisionStateManager(
                context=context,
                output_dir=output_dir,
                nonce_factory=nonce_factory,
                crash_hook=crash_hook,
            )
            selected = manager.compose_and_select(
                decisions_path=decisions_path,
                decisions_raw=decisions_raw,
                sidecar_payload=payload,
                force=force,
            )
        except MissionStateError as exc:
            return _blocked(exc.code, output_dir, [str(exc)])
        output_path = selected.sidecar_path
    else:
        from research_assistant.survey.review_decisions import atomic_write_json

        atomic_write_json(output_path, payload)
    return {
        "schema_version": SURVEY_REVIEWED_OMISSION_RESULT_SCHEMA_VERSION,
        "status": "reviewed_omissions_complete" if result.complete else "blocked_invalid_omission_decisions",
        "output_dir": str(output_dir),
        "reviewed_omission_risks_path": str(output_path),
        "accepted_omission_count": len(result.accepted),
        "rejected_omission_count": len(result.rejected),
        "closed_omission_count": closed_count,
        "open_omission_count": open_count,
        "decision_coverage_complete": result.complete,
        "literature_completeness_allowed": False,
        "ready_for_reviewed_packet": False,
        "ready_for_prose": False,
        "what_is_not_concluded": REVIEWED_OMISSION_NONCLAIMS,
    }


def _validate_decision(row: Any, queue_item: dict[str, Any] | None, index: int) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(row, dict):
        return {}, [f"row {index} is not an object"]
    reasons: list[str] = []
    decision = _text(row.get("decision"), "decision", reasons).lower()
    expected = set(OMISSION_COMMON_INPUT_KEYS)
    if decision in OPEN_OMISSION_DECISIONS:
        expected.add("next_action")
    elif decision in {"acceptable_omission", "out_of_scope"}:
        expected.add("scope_basis")
    disposition = queue_item.get("machine_disposition") if queue_item else None
    try:
        require_exact_keys(row, expected, f"omission decision row {index}")
    except MissionStateError as exc:
        reasons.append(str(exc))
    risk_id = _text(row.get("risk_id"), "risk_id", reasons)
    reason = _text(row.get("reason"), "reason", reasons)
    reviewer = _text(row.get("reviewer"), "reviewer", reasons)
    reviewed_at = _time(row.get("reviewed_at"), reasons)
    if decision not in SUPPORTED_OMISSION_DECISIONS:
        reasons.append("decision must be acceptable_omission, must_inspect, expand_scope, blocked_pending_source, or out_of_scope")
    if queue_item is not None:
        queue_risk_id = str(queue_item.get("risk_id") or queue_item.get("source_id") or "")
        if risk_id != queue_risk_id:
            reasons.append("risk_id must match the referenced omission_risk queue item")
        if queue_item.get("literature_completeness_allowed") is not False:
            reasons.append("referenced omission_risk queue item must not already allow literature completeness")
        coverage_schema = queue_item.get("coverage_schema_version")
        if coverage_schema == "ra-survey-omitted-paper-risks-v2":
            disposition = queue_item.get("machine_disposition")
            allowed = V2_OMISSION_TRANSITIONS.get(disposition)
            if allowed is None:
                reasons.append("V2 omission queue item has an invalid machine disposition")
            elif decision not in allowed:
                reasons.append(
                    f"decision {decision or '<empty>'} is forbidden for machine disposition {disposition}"
                )
            for field in ("risk_source_type", "risk_source_id", "source_artifact_sha256"):
                if not isinstance(queue_item.get(field), str) or not queue_item[field]:
                    reasons.append(f"V2 omission queue item lacks exact {field}")
    open_decision = decision in OPEN_OMISSION_DECISIONS
    normalized = {
        "risk_id": risk_id,
        "decision": decision,
        "reason": reason,
        "next_action": _text(row.get("next_action"), "next_action", reasons) if open_decision else "",
        "scope_basis": _text(row.get("scope_basis"), "scope_basis", reasons) if not open_decision else "",
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "severity": queue_item.get("severity") if queue_item else None,
        "machine_disposition": queue_item.get("machine_disposition") if queue_item else None,
        "risk_source_type": queue_item.get("risk_source_type") if queue_item else None,
        "risk_source_id": queue_item.get("risk_source_id") if queue_item else None,
        "source_artifact_sha256": queue_item.get("source_artifact_sha256") if queue_item else None,
        "regeneration_required": decision == "expand_scope",
        "status": "open" if open_decision else "reviewed_closed_for_current_scope",
        "literature_completeness_allowed": False,
        "ready_for_prose": False,
    }
    return normalized, reasons


def omission_sidecar_expected_fields(result: Any) -> dict[str, Any]:
    return {
        "status": "reviewed_omissions_complete" if result.complete else "blocked_invalid_omission_decisions",
        "accepted_omission_count": len(result.accepted),
        "rejected_omission_count": len(result.rejected),
        "closed_omission_count": sum(
            row["status"] == "reviewed_closed_for_current_scope" for row in result.accepted
        ),
        "open_omission_count": sum(row["status"] == "open" for row in result.accepted),
        "literature_completeness_allowed": False,
        "what_is_not_concluded": REVIEWED_OMISSION_NONCLAIMS,
    }


def resolve_current_reviewed_omissions(
    *,
    review_queue_path: Path,
    reviewed_omissions_root: Path,
    supplied_sidecar_path: Path | None = None,
) -> OmissionDecisionSetSnapshot | Path:
    from research_assistant.survey.review_decisions import load_selected_decision_context

    context = load_selected_decision_context(
        review_queue_path=review_queue_path,
        decision_type="omission_risk",
    )
    root = reviewed_omissions_root.absolute()
    if _is_v2_omission_context(context):
        manager = OmissionDecisionStateManager(context=context, output_dir=root)
        selected = manager.load_current(required=True)
        assert selected is not None
        if supplied_sidecar_path is not None:
            supplied = supplied_sidecar_path.absolute()
            if (
                supplied.is_symlink()
                or supplied != selected.sidecar_path.absolute()
                or supplied.resolve() != selected.sidecar_path.resolve()
            ):
                raise MissionStateError(
                    "stale_omission_decision_selector",
                    "supplied omission sidecar is not selected by DECISION_CURRENT",
                )
        return selected
    legacy = root / "reviewed_omission_risks.json"
    if supplied_sidecar_path is not None and supplied_sidecar_path.absolute() != legacy:
        raise MissionStateError("stale_omission_decision_selector", "legacy omission sidecar path is noncanonical")
    return legacy


def resolve_current_omission_sidecar_path(
    *,
    review_queue_path: Path,
    sidecar_path: Path,
) -> Path:
    supplied = sidecar_path.absolute()
    if supplied.parent.parent.name == "decision_sets":
        root = supplied.parent.parent.parent
        selected = resolve_current_reviewed_omissions(
            review_queue_path=review_queue_path,
            reviewed_omissions_root=root,
            supplied_sidecar_path=supplied,
        )
    else:
        selected = resolve_current_reviewed_omissions(
            review_queue_path=review_queue_path,
            reviewed_omissions_root=supplied.parent,
            supplied_sidecar_path=supplied,
        )
    return selected.sidecar_path if isinstance(selected, OmissionDecisionSetSnapshot) else selected


def _is_v2_omission_context(context: ReviewDecisionContext) -> bool:
    items = list(context.required_items.values())
    if not items:
        return False
    v2 = [item.get("coverage_schema_version") == "ra-survey-omitted-paper-risks-v2" for item in items]
    if any(v2) and not all(v2):
        raise MissionStateError("mixed_omission_queue_schema", "omission queue mixes V1 and V2 risks")
    return all(v2)


def _read_canonical_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    payload, raw = read_json_object_strict(path, label=label)
    if raw != canonical_json_bytes(payload):
        raise MissionStateError("noncanonical_omission_decision_state", f"{label} is noncanonical")
    return payload, raw


def _safe_child_directory(parent: Path, name: str) -> Path:
    child = parent / name
    if child.is_symlink() or not child.is_dir() or child.resolve().parent != parent.resolve():
        raise MissionStateError("unsafe_omission_decision_set", "decision-set directory is unsafe")
    return child.resolve()


def _regular_child(parent: Path, name: str) -> Path:
    path = parent / name
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("missing_omission_decision_artifact", f"missing decision-set artifact: {name}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or path.resolve().parent != parent.resolve():
        raise MissionStateError("unsafe_omission_decision_artifact", f"unsafe decision-set artifact: {name}")
    return path


def _validate_staging(directory: Path) -> None:
    allowed = {
        "reviewed_omission_decisions.json",
        "reviewed_omission_risks.json",
        "decision_set_manifest.json",
    }
    for path in directory.iterdir():
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or path.name not in allowed:
            raise MissionStateError("unsafe_omission_decision_staging", "staging residue is unsafe")


def _nonce(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 32 or any(char not in "0123456789abcdef" for char in value):
        raise MissionStateError("invalid_omission_decision_nonce", "decision-set nonce is invalid")
    return value


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _text(value: Any, field: str, reasons: list[str]) -> str:
    try:
        return normalize_required_text(value, field=field)
    except MissionStateError as exc:
        reasons.append(str(exc)); return ""


def _time(value: Any, reasons: list[str]) -> str:
    try:
        return normalize_reviewed_at(value)
    except MissionStateError as exc:
        reasons.append(str(exc)); return ""


def _blocked(reason: str, output_dir: Path, next_required_actions: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SURVEY_REVIEWED_OMISSION_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "blocked_reason": reason,
        "output_dir": str(output_dir),
        "next_required_actions": next_required_actions,
        "what_is_not_concluded": REVIEWED_OMISSION_NONCLAIMS,
    }


__all__ = [
    "OMISSION_SIDECAR_KEYS",
    "OMISSION_DECISION_CURRENT_SCHEMA",
    "OMISSION_DECISION_SET_MANIFEST_SCHEMA",
    "OmissionDecisionSetSnapshot",
    "OmissionDecisionStateManager",
    "REVIEWED_OMISSION_NONCLAIMS",
    "SURVEY_REVIEWED_OMISSION_SCHEMA_VERSION",
    "_validate_decision",
    "import_reviewed_omissions",
    "omission_sidecar_expected_fields",
    "resolve_current_reviewed_omissions",
    "resolve_current_omission_sidecar_path",
]
