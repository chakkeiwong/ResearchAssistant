from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import re
import subprocess

from research_assistant.config import get_paths
from research_assistant.individual_release import (
    read_release_artifacts_manifest,
    version_consistency,
    version_payload,
    workspace_validate,
)
from research_assistant.release_evidence import validate_release_artifact_manifest
from research_assistant.industrial.platform import (
    build_artifact_index,
    build_readiness_report,
    validate_industrial_artifacts,
)
from research_assistant.schemas.artifact import base_artifact
from research_assistant.storage.file_store import FileStore


INDUSTRIAL_RELEASE_GATE_VERSION = "industrial-release-gates-v1"
VALIDATION_RECORD_VERSION = "industrial-external-validation-v1"


@dataclass(frozen=True)
class IndustrialReleasePhase:
    phase_id: str
    title: str
    release_gap: str
    milestone_target: str
    status: str
    motivation: str
    implementation_contracts: list[str]
    local_checks: list[str]
    external_requirements: list[str]
    acceptance_criteria: list[str]
    stop_conditions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PHASES: list[IndustrialReleasePhase] = [
    IndustrialReleasePhase(
        "phase_00_release_definition",
        "Industrial Release Definition And Gate Taxonomy",
        "release_scope",
        "M0",
        "m0_contract_complete",
        "Prevent individual-pilot readiness from being mistaken for departmental production readiness.",
        ["release level taxonomy", "machine-readable gate file", "release readiness CLI report"],
        ["gate schema loads", "missing mandatory gate blocks production"],
        ["release owner accepts release taxonomy"],
        ["current state recorded as individual_pilot", "departmental_beta and industrial_production blocked until gates pass"],
        [],
    ),
    IndustrialReleasePhase(
        "phase_01_external_validation",
        "External Validation Program",
        "external_validation",
        "M1",
        "blocked_external_validation",
        "Future industrial release needs governed environment and corpus validation beyond the local Linux tool.",
        ["sanitized validation record schema", "external validation aggregation", "privacy rejection rules"],
        ["fixture record aggregation", "forbidden field detection"],
        ["sanitized real corpus", "department environment validation"],
        ["missing external validation blocks broad release claims"],
        ["external users or machines unavailable"],
    ),
    IndustrialReleasePhase(
        "phase_02_publication",
        "Release Artifact Publication And Tagging Workflow",
        "publication",
        "M1",
        "blocked_manual_approval",
        "Artifacts need reproducible publication, hash verification, approval, tag policy, and rollback instructions.",
        ["publication runbook", "publication check", "artifact/version/notes alignment"],
        ["artifact manifest validation", "release notes checksum-source reference", "tag state inspection"],
        ["release owner approves tag and artifact upload"],
        ["publication blocked unless artifact hashes, version, notes, validation, and approval align"],
        ["manual publication approval required"],
    ),
    IndustrialReleasePhase(
        "phase_03_storage",
        "Production Storage And Migration Strategy",
        "storage",
        "M0",
        "blocked_for_governed_integration",
        "Departmental use needs transactional storage, migration, backup, restore, and corruption recovery.",
        ["ArtifactRepository contract", "JSON compatibility", "SQLite migration contract", "backup/restore contract"],
        ["artifact index builds", "workspace validation", "migration dry-run contract"],
        ["production storage ADR accepted", "migration owner approval", "restore drill"],
        ["invalid artifacts are reported, never silently dropped"],
        ["destructive migration without accepted backup/restore plan"],
    ),
    IndustrialReleasePhase(
        "phase_04_service_api",
        "Service/API Layer Contract",
        "service_api",
        "M0",
        "m0_contract_complete",
        "UI, orchestration, and collaboration need stable service contracts before network deployment.",
        ["versioned request/response contracts", "error taxonomy", "trust-boundary response fields"],
        ["tool-contract export includes local surfaces"],
        ["network service deployment decision"],
        ["service contracts are stable, versioned, and tested"],
        ["production deployment decision required"],
    ),
    IndustrialReleasePhase(
        "phase_05_identity_collaboration",
        "Identity, RBAC, And Collaboration Workflow",
        "identity_collaboration",
        "M0",
        "blocked_for_governed_integration",
        "Real departmental workflows require roles, assignments, approvals, comments, and append-only event history.",
        ["user/role/permission schema", "assignment/comment schema", "append-only event contract"],
        ["collaboration scaffold exists", "local event history remains review material"],
        ["identity ADR", "SSO/RBAC policy owner approval"],
        ["unauthorized approval impossible through public commands"],
        ["production SSO/RBAC policy required"],
    ),
    IndustrialReleasePhase(
        "phase_06_parser_benchmarks",
        "Parser And Source Benchmark Certification",
        "parser_certification",
        "M1",
        "m1_local_deterministic",
        "Parser availability is not enough; extraction quality must be measured by paper family.",
        ["gold benchmark schema", "metric taxonomy", "trend report", "regression gate"],
        ["parser benchmark smoke fixtures", "benchmark manifest/run reports"],
        ["expanded gold corpus approved for release claims"],
        ["parser quality claims backed by benchmark results"],
        [],
    ),
    IndustrialReleasePhase(
        "phase_07_derivation_approval",
        "Mathematical Review And Derivation Approval Workflow",
        "derivation_approval",
        "M1",
        "blocked_human_approval",
        "Industrial mathematical review needs explicit assumptions, proof gaps, reviewer identity, and approval.",
        ["derivation review contract", "approval request contract", "stale approval detection"],
        ["derivation dependency validation", "human-review defaults"],
        ["authorized mathematical reviewers"],
        ["no derivation can be approved with unresolved required gaps"],
        ["human mathematical approval required"],
    ),
    IndustrialReleasePhase(
        "phase_08_experiment_reproducibility",
        "Experiment Reproducibility And Execution Evidence",
        "experiment_reproducibility",
        "M1",
        "m1_local_deterministic",
        "Computational claims need environment, seed, hashes, diagnostics, results, and reproducibility gates.",
        ["experiment execution record schema", "local fixture runner contract", "reproducibility score"],
        ["experiment reproducibility evidence scoring", "fixture runs"],
        ["external execution infrastructure for real workloads"],
        ["readiness distinguishes evidence completeness from scientific approval"],
        ["external compute service required for production runs"],
    ),
    IndustrialReleasePhase(
        "phase_09_traceability",
        "Paper-To-Code Traceability Verification",
        "traceability",
        "M1",
        "m1_local_deterministic",
        "Industrial users need missing/stale code/test targets without automatic semantic certification.",
        ["traceability verification status", "stale target detection", "review states"],
        ["local target path checks", "traceability report"],
        ["repository/code owner review"],
        ["reports identify missing or stale targets without claiming correctness"],
        [],
    ),
    IndustrialReleasePhase(
        "phase_10_search_graph",
        "Search, Indexing, And Knowledge Graph",
        "search_graph",
        "M0",
        "blocked_m1_implementation",
        "Research teams need explainable queries across papers, assumptions, experiments, citations, and review states.",
        ["search/index abstraction", "graph edge taxonomy", "stale-index contract"],
        ["artifact index inventory", "full-scale search contract"],
        ["curated query relevance evaluation"],
        ["search results cite source artifacts and graph edges do not imply approval"],
        ["semantic/vector search remains policy-gated"],
    ),
    IndustrialReleasePhase(
        "phase_11_llm_governance",
        "LLM/Provider Governance",
        "llm_governance",
        "M0",
        "blocked_for_governed_integration",
        "Live providers require secrets handling, allowlists, prompt registry, audit logs, cost controls, and privacy gates.",
        ["provider policy", "secret-reference design", "dry-run provider simulation", "audit log schema"],
        ["model policy blocks live calls by default"],
        ["provider credentials", "department policy approval", "security review"],
        ["no live provider call without explicit policy approval and audit record"],
        ["live credentials or provider access required"],
    ),
    IndustrialReleasePhase(
        "phase_12_security_ops",
        "Security, Compliance, And Operations",
        "security_operations",
        "M0",
        "blocked_for_governed_integration",
        "Industrial release needs backups, retention, audit logs, incident response, dependency policy, and compliance review.",
        ["operations runbook", "security checklist", "forbidden-file staging checks", "restore drill records"],
        ["operations policy scaffold", "release gate docs/policy checks"],
        ["security/compliance owner approval", "restore drill on target environment"],
        ["industrial release blocked without security/ops checklist completion"],
        ["department security/compliance approval required"],
    ),
    IndustrialReleasePhase(
        "phase_13_scalability",
        "Scalability And Real Corpus Performance",
        "scalability",
        "M1",
        "blocked_external_validation",
        "Synthetic 1000-record smoke is useful but not enough for departmental corpora.",
        ["scalability validation protocol", "performance tiers", "metric report schema"],
        ["synthetic performance smoke", "timeout diagnostics"],
        ["sanitized real corpus", "larger target-machine stress tests"],
        ["release notes state measured corpus sizes and limits"],
        ["private real corpus unavailable"],
    ),
    IndustrialReleasePhase(
        "phase_14_ui_workbench",
        "UI And Workflow Workbench",
        "ui_workbench",
        "M0",
        "blocked_for_governed_integration",
        "Industrial reviewers need a workbench for triage, evidence, traceability, benchmarks, readiness, and governance.",
        ["UI architecture ADR", "dashboard/API contracts", "generated-vs-approved state contract"],
        ["dashboard export contract"],
        ["service/API stability", "identity/RBAC", "deployment decision"],
        ["core review workflow usable through workbench"],
        ["production deployment decision required"],
    ),
    IndustrialReleasePhase(
        "phase_15_sops",
        "Department SOPs And Approval Gates",
        "department_sops",
        "M0",
        "blocked_manual_approval",
        "Industrial release is partly organizational: SOPs need owners, reviewers, dates, and gates.",
        ["industrial research SOP", "SOP status records", "readiness blockers for missing/expired SOPs"],
        ["SOP scaffold and readiness warning"],
        ["department SOP owner approval or waiver"],
        ["departmental beta blocked unless required SOPs are approved or waived"],
        ["department policy owner approval required"],
    ),
    IndustrialReleasePhase(
        "phase_16_final_gate",
        "Industrial Release Candidate Gate",
        "release_gate",
        "M1",
        "blocked",
        "A final gate must aggregate technical, validation, operational, and governance evidence.",
        ["industrial release report", "gate status aggregation", "bounded release script"],
        ["industrial-release-gate build", "script smoke"],
        ["all target release-level gates passed or owner-waived"],
        ["production impossible to claim with incomplete M2/M3 gates"],
        ["any required upstream gate incomplete"],
    ),
]

RELEASE_LEVELS = {
    "individual_pilot": {
        "description": "One user, private local workspace, no shared services.",
        "required_phase_ids": ["phase_00_release_definition", "phase_02_publication"],
    },
    "departmental_beta": {
        "description": "Limited departmental trial with explicit owners, external validation, and local deterministic gates.",
        "required_phase_ids": [
            "phase_00_release_definition",
            "phase_01_external_validation",
            "phase_02_publication",
            "phase_05_identity_collaboration",
            "phase_06_parser_benchmarks",
            "phase_12_security_ops",
            "phase_15_sops",
            "phase_16_final_gate",
        ],
    },
    "industrial_production": {
        "description": "Production departmental platform with storage, service, security, operations, SOP, and deployment signoff.",
        "required_phase_ids": [phase.phase_id for phase in PHASES],
    },
}

FORBIDDEN_VALIDATION_FIELDS = {"private_pdf", "private_title", "backup_archive", "provider_key", "credential", "token"}
PRIVATE_PATH_RE = re.compile(r"(/home/[^/\s]+/(?!tmp)|/Users/[^/\s]+/|[A-Za-z]:\\\\Users\\\\)", re.IGNORECASE)
FORBIDDEN_STAGED_PREFIXES = (
    ".codex",
    ".claude",
    "build/",
    "dist/",
    "local_research/",
)
FORBIDDEN_STAGED_SUFFIXES = (
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
)


def _store(root: Path | None = None) -> FileStore:
    return FileStore(get_paths(root).local_research)


def _release_dir(root: Path | None = None) -> Path:
    return get_paths(root).governance / "industrial_release"


def _release_path(root: Path | None, artifact_id: str) -> Path:
    return _release_dir(root) / f"{artifact_id}.json"


def _publication_material_root(workspace_root: Path) -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "docs" / "release_notes_0.1.0.md").exists():
        return cwd
    if (workspace_root / "pyproject.toml").exists():
        return workspace_root
    return workspace_root


def list_release_phases() -> list[dict[str, Any]]:
    return [phase.to_dict() for phase in PHASES]


def get_release_phase(phase_id: str) -> dict[str, Any]:
    for phase in PHASES:
        if phase.phase_id == phase_id:
            return phase.to_dict()
    raise KeyError(f"unknown industrial release phase {phase_id}")


def build_release_definition(*, root: Path | None = None, artifact_id: str = "industrial_release_definition") -> dict[str, Any]:
    phase_rows = list_release_phases()
    gate_status = {
        phase["phase_id"]: {
            "title": phase["title"],
            "status": phase["status"],
            "milestone_target": phase["milestone_target"],
            "release_gap": phase["release_gap"],
            "stop_conditions": phase["stop_conditions"],
        }
        for phase in phase_rows
    }
    payload = {
        **base_artifact(
            artifact_type="industrial_release_definition",
            artifact_id=artifact_id,
            provenance={"created_by": "ra industrial-release definition-build", "gate_version": INDUSTRIAL_RELEASE_GATE_VERSION},
            limitations=[
                "Release definition is a gate contract, not production approval.",
                "M2/M3 gates require external owners and governed integration.",
            ],
        ),
        "gate_version": INDUSTRIAL_RELEASE_GATE_VERSION,
        "current_release_level": "individual_pilot",
        "release_levels": RELEASE_LEVELS,
        "phase_count": len(phase_rows),
        "phases": phase_rows,
        "gate_status": gate_status,
    }
    _store(root).write_json(_release_path(root, artifact_id), payload)
    return payload


def show_release_definition(*, root: Path | None = None, artifact_id: str = "industrial_release_definition") -> dict[str, Any]:
    return _store(root).read_json(_release_path(root, artifact_id))


def _validation_record_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    missing = [
        field
        for field in ["schema_version", "validation_type", "platform", "python_version", "result"]
        if not record.get(field)
    ]
    if missing:
        issues.append({"severity": "blocker", "code": "missing_required_fields", "fields": missing})
    if record.get("schema_version") != VALIDATION_RECORD_VERSION:
        issues.append({
            "severity": "warning",
            "code": "validation_schema_mismatch",
            "expected": VALIDATION_RECORD_VERSION,
            "found": record.get("schema_version"),
        })
    forbidden = sorted(FORBIDDEN_VALIDATION_FIELDS & set(record))
    if forbidden:
        issues.append({"severity": "blocker", "code": "forbidden_private_fields", "fields": forbidden})
    serialized = json.dumps(record, sort_keys=True)
    if PRIVATE_PATH_RE.search(serialized):
        issues.append({"severity": "warning", "code": "possible_private_path"})
    if record.get("result") not in {"passed", "warnings", "blocked"}:
        issues.append({"severity": "blocker", "code": "invalid_result", "result": record.get("result")})
    return issues


def build_external_validation_report(
    *,
    root: Path | None = None,
    validation_dir: Path | None = None,
    artifact_id: str = "industrial_external_validation_report",
) -> dict[str, Any]:
    paths = get_paths(root)
    record_dir = validation_dir or (paths.governance / "external_validation")
    records = []
    required_types = {"linux_local", "linux_parser_tools"}
    passed_types: set[str] = set()
    issues: list[dict[str, Any]] = []
    for path in sorted(record_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            records.append({"path": str(path), "status": "blocked", "issues": [{"severity": "blocker", "code": "invalid_json", "message": str(exc)}]})
            issues.append({"severity": "blocker", "code": "invalid_validation_json", "path": str(path)})
            continue
        record_issues = _validation_record_issues(record)
        validation_type = record.get("validation_type")
        if validation_type and record.get("result") == "passed" and not any(issue["severity"] == "blocker" for issue in record_issues):
            passed_types.add(validation_type)
        records.append({
            "path": str(path),
            "validation_type": validation_type,
            "result": record.get("result"),
            "issues": record_issues,
        })
        issues.extend({**issue, "path": str(path), "validation_type": validation_type} for issue in record_issues)
    missing_types = sorted(required_types - passed_types)
    for validation_type in missing_types:
        issues.append({"severity": "blocker", "code": "missing_external_validation", "validation_type": validation_type})
    blocker_count = len([issue for issue in issues if issue.get("severity") == "blocker"])
    warning_count = len([issue for issue in issues if issue.get("severity") == "warning"])
    payload = {
        **base_artifact(
            artifact_type="industrial_external_validation_report",
            artifact_id=artifact_id,
            provenance={"created_by": "ra industrial-release external-validation-build"},
            limitations=["Report accepts only sanitized validation metadata and does not collect private corpora or logs."],
        ),
        "validation_record_dir": str(record_dir),
        "required_validation_types": sorted(required_types),
        "passed_validation_types": sorted(passed_types),
        "missing_validation_types": missing_types,
        "records": records,
        "issue_counts": {"blockers": blocker_count, "warnings": warning_count},
        "status": "blocked" if blocker_count else ("warnings" if warning_count else "passed"),
    }
    _store(root).write_json(_release_path(root, artifact_id), payload)
    return payload


def _forbidden_staged_reason(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in FORBIDDEN_STAGED_PREFIXES):
        return "local scratch, generated output, or private workspace path"
    if normalized.endswith(FORBIDDEN_STAGED_SUFFIXES):
        return "archive artifacts must not be staged for source release"
    if "backup" in normalized.lower() and normalized.endswith((".json", ".log")):
        return "backup metadata/log artifacts must remain out of source release"
    return None


def _git_publication_status(project_root: Path) -> dict[str, Any]:
    if not (project_root / ".git").exists():
        return {
            "status": "unavailable",
            "clean": False,
            "issues": [{"severity": "blocker", "code": "git_metadata_missing", "path": str(project_root)}],
            "entries": [],
            "forbidden_staged_files": [],
        }
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), "status", "--porcelain=v1"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return {
            "status": "unavailable",
            "clean": False,
            "issues": [{"severity": "blocker", "code": "git_not_available"}],
            "entries": [],
            "forbidden_staged_files": [],
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "unavailable",
            "clean": False,
            "issues": [{"severity": "blocker", "code": "git_status_timeout"}],
            "entries": [],
            "forbidden_staged_files": [],
        }
    if completed.returncode != 0:
        return {
            "status": "unavailable",
            "clean": False,
            "issues": [{
                "severity": "blocker",
                "code": "git_status_failed",
                "stderr": completed.stderr.strip(),
            }],
            "entries": [],
            "forbidden_staged_files": [],
        }
    entries = []
    forbidden_staged = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entry = {
            "status": xy,
            "path": path,
            "staged": xy[0] not in {" ", "?"},
            "unstaged": xy[1] != " ",
            "untracked": xy == "??",
        }
        entries.append(entry)
        if entry["staged"]:
            reason = _forbidden_staged_reason(path)
            if reason:
                forbidden_staged.append({"path": path, "status": xy, "reason": reason})
    issues = []
    if entries:
        issues.append({"severity": "blocker", "code": "git_worktree_not_clean", "entry_count": len(entries)})
    if forbidden_staged:
        issues.append({"severity": "blocker", "code": "forbidden_staged_files", "files": forbidden_staged})
    return {
        "status": "dirty" if entries else "clean",
        "clean": not entries,
        "issues": issues,
        "entries": entries,
        "forbidden_staged_files": forbidden_staged,
    }


def _final_gate_evidence(root: Path | None = None) -> dict[str, Any]:
    path = _release_path(root, "industrial_release_gate")
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
            "status": "missing",
            "issues": [{"severity": "blocker", "code": "final_gate_evidence_missing"}],
        }
    try:
        payload = _store(root).read_json(path)
    except json.JSONDecodeError as exc:
        return {
            "exists": True,
            "path": str(path),
            "status": "blocked",
            "issues": [{"severity": "blocker", "code": "final_gate_evidence_invalid_json", "message": str(exc)}],
        }
    gate_status = payload.get("status")
    issues = []
    if gate_status != "passed":
        issues.append({"severity": "blocker", "code": "final_gate_not_passed", "gate_status": gate_status})
    return {
        "exists": True,
        "path": str(path),
        "status": gate_status,
        "artifact_id": payload.get("artifact_id"),
        "created_at": payload.get("created_at"),
        "current_release_level": payload.get("current_release_level"),
        "requested_release_level": payload.get("requested_release_level"),
        "issues": issues,
    }


def build_publication_check(
    *,
    root: Path | None = None,
    release_notes: Path | None = None,
    artifact_id: str = "industrial_publication_check",
    require_final_gate_evidence: bool = True,
) -> dict[str, Any]:
    paths = get_paths(root)
    release_root = _publication_material_root(paths.root)
    notes_path = release_notes or (release_root / "docs" / "release_notes_0.1.0.md")
    manifest = read_release_artifacts_manifest(release_root=release_root)
    artifact_validation = validate_release_artifact_manifest(release_root)
    version = version_payload()
    version_report = version_consistency(release_root=release_root)
    git_report = _git_publication_status(release_root)
    final_gate = _final_gate_evidence(root=root) if require_final_gate_evidence else {
        "required": False,
        "status": "not_checked_during_gate_build",
        "issues": [],
    }
    issues: list[dict[str, Any]] = []
    artifacts = manifest.get("artifacts") or []
    artifact_hashes = {
        row["filename"]: row["sha256"]
        for row in artifacts
        if isinstance(row, dict) and isinstance(row.get("filename"), str) and isinstance(row.get("sha256"), str)
    }
    if manifest.get("status") != "ok":
        issues.append({"severity": "blocker", "code": "artifact_manifest_not_ready"})
    if artifact_validation["status"] != "passed":
        issues.append({"severity": "blocker", "code": "artifact_manifest_validation_failed", "details": artifact_validation})
    if not notes_path.exists():
        issues.append({"severity": "blocker", "code": "release_notes_missing", "path": str(notes_path)})
    if version_report["status"] == "blocked":
        issues.append({"severity": "blocker", "code": "version_consistency_blocked", "details": version_report["issues"]})
    elif version_report["status"] == "warnings":
        issues.append({"severity": "warning", "code": "version_consistency_warnings", "details": version_report["issues"]})
    issues.extend(git_report["issues"])
    issues.extend(final_gate["issues"])
    tag_expected = f"v{version['version']}"
    payload = {
        **base_artifact(
            artifact_type="industrial_publication_check",
            artifact_id=artifact_id,
            provenance={"created_by": "ra industrial-release publication-check"},
            limitations=["This check does not create tags or publish artifacts; release-owner approval is required."],
        ),
        "package_version": version["version"],
        "expected_tag": tag_expected,
        "tag_created": False,
        "artifact_manifest": manifest,
        "artifact_manifest_validation": artifact_validation,
        "release_material_root": str(release_root),
        "release_notes_path": str(notes_path),
        "artifact_hashes": artifact_hashes,
        "release_notes_checksum_source": "dist/release_artifacts_manifest.json",
        "version_consistency": version_report,
        "git_status": git_report,
        "final_gate_evidence": final_gate,
        "final_gate_evidence_required": require_final_gate_evidence,
        "manual_approval_required": True,
        "issues": issues,
        "status": "blocked_manual_approval" if not issues else "blocked",
    }
    _store(root).write_json(_release_path(root, artifact_id), payload)
    return payload


def build_industrial_release_gate(*, root: Path | None = None, artifact_id: str = "industrial_release_gate") -> dict[str, Any]:
    definition = build_release_definition(root=root)
    external = build_external_validation_report(root=root)
    publication = build_publication_check(root=root, require_final_gate_evidence=False)
    validation = validate_industrial_artifacts(root=root)
    index = build_artifact_index("industrial_release_gate_index", root=root)
    readiness = build_readiness_report("industrial_release_gate_readiness", root=root)
    workspace = workspace_validate(root=root)
    phase_statuses = definition["gate_status"]
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for phase in definition["phases"]:
        status = phase["status"]
        if status.startswith("blocked"):
            blockers.append({"phase_id": phase["phase_id"], "code": status, "title": phase["title"], "stop_conditions": phase["stop_conditions"]})
    if external["status"] != "passed":
        blockers.append({"phase_id": "phase_01_external_validation", "code": "external_validation_incomplete", "missing": external["missing_validation_types"]})
    if publication["status"] != "ready_to_publish":
        blockers.append({"phase_id": "phase_02_publication", "code": publication["status"], "manual_approval_required": publication["manual_approval_required"]})
    if workspace["status"] == "blocked":
        blockers.append({"phase_id": "workspace", "code": "workspace_blocked"})
    elif workspace["status"] == "warnings":
        warnings.append({"phase_id": "workspace", "code": "workspace_warnings"})
    if validation["status"] == "blocked":
        blockers.append({"phase_id": "industrial_artifacts", "code": "artifact_validation_blocked", "issue_counts": validation["issue_counts"]})
    elif validation["status"] == "warnings":
        warnings.append({"phase_id": "industrial_artifacts", "code": "artifact_validation_warnings", "issue_counts": validation["issue_counts"]})
    if readiness["status"] == "blocked":
        blockers.append({"phase_id": "industrial_readiness", "code": "local_readiness_blocked", "blocker_count": len(readiness.get("blockers") or [])})
    elif readiness["status"] == "warnings":
        warnings.append({"phase_id": "industrial_readiness", "code": "local_readiness_warnings"})
    production_blockers = [
        blocker for blocker in blockers
        if blocker.get("phase_id") not in {"phase_01_external_validation", "phase_02_publication"}
    ]
    payload = {
        **base_artifact(
            artifact_type="industrial_release_gate",
            artifact_id=artifact_id,
            provenance={"created_by": "ra industrial-release gate-build", "gate_version": INDUSTRIAL_RELEASE_GATE_VERSION},
            limitations=[
                "Gate report is local deterministic evidence and does not replace security, department, or production approval.",
                "Generated artifacts remain review material.",
            ],
        ),
        "gate_version": INDUSTRIAL_RELEASE_GATE_VERSION,
        "requested_release_level": "industrial_production",
        "current_release_level": "individual_pilot",
        "status": "blocked" if blockers else ("warnings" if warnings else "passed"),
        "phase_statuses": phase_statuses,
        "blockers": blockers,
        "warnings": warnings,
        "external_validation": external,
        "publication_check": publication,
        "workspace_validation": workspace,
        "industrial_validation_summary": {
            "status": validation["status"],
            "issue_counts": validation["issue_counts"],
        },
        "artifact_index_summary": {
            "status": index["validation_summary"]["status"],
            "migration_needed": index["migration_needed"],
        },
        "local_readiness_summary": {
            "status": readiness["status"],
            "blocker_count": len(readiness.get("blockers") or []),
            "warning_count": len(readiness.get("warnings") or []),
        },
        "ready_for_individual_pilot": True,
        "ready_for_departmental_beta": False,
        "ready_for_industrial_production": False if production_blockers or blockers else True,
        "next_actions": [
            "collect real external validation records",
            "obtain release-owner publication approval",
            "accept storage, identity, security, and deployment ADRs",
            "complete security/ops and SOP owner signoff",
            "rerun industrial release gate after governed integrations",
        ],
    }
    _store(root).write_json(_release_path(root, artifact_id), payload)
    return payload


def show_industrial_release_artifact(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _store(root).read_json(_release_path(root, artifact_id))
