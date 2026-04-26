from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from research_assistant.config import get_paths
from research_assistant.schemas.artifact import base_artifact
from research_assistant.storage.file_store import FileStore


PHASE_REGISTRY_VERSION = "industrial-full-scale-v1"


@dataclass(frozen=True)
class PhaseContract:
    phase_id: str
    title: str
    subsystem: str
    goal: str
    milestone_status: str
    dependencies: list[str]
    implementation_contracts: list[str]
    tests: list[str]
    usefulness_verification: list[str]
    acceptance_criteria: list[str]
    stop_conditions: list[str]
    governed_integration_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


COMMON_STOP_CONDITIONS = [
    "live credentials or provider access required",
    "production SSO/RBAC policy required",
    "external network service required",
    "production deployment decision required",
    "department security/compliance approval required",
    "destructive migration without backup/restore plan",
]


PHASE_CONTRACTS: list[PhaseContract] = [
    PhaseContract(
        phase_id="phase_00_architecture_baseline",
        title="Architecture Baseline And Roadmap Control",
        subsystem="architecture",
        goal="Create architecture docs, ADRs, phase registry, and stop conditions before implementation drift.",
        milestone_status="m0_contract_complete",
        dependencies=[],
        implementation_contracts=[
            "architecture overview document",
            "ADR template and proposed ADRs",
            "machine-readable phase registry",
            "reset memo checkpoint discipline",
        ],
        tests=[
            "documentation contract test for architecture headings",
            "phase registry schema completeness test",
            "ADR presence test",
        ],
        usefulness_verification=[
            "new developer can identify subsystem owner and required ADR from the registry",
        ],
        acceptance_criteria=[
            "all phases have dependencies, tests, usefulness checks, and stop conditions",
            "major governed integrations name an ADR before implementation",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_01_production_storage",
        title="Production Storage Layer",
        subsystem="storage",
        goal="Introduce durable repository contracts, migrations, backups, and future SQLite storage while preserving local JSON compatibility.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_00_architecture_baseline", "adr_0001_storage_backend"],
        implementation_contracts=[
            "ArtifactRepository interface",
            "LocalJsonArtifactRepository compatibility",
            "SQLite repository migration contract",
            "backup/restore contract",
            "corrupt-record recovery report",
        ],
        tests=[
            "repository contract tests",
            "migration tests",
            "backup/restore round-trip tests",
            "concurrency conflict tests",
        ],
        usefulness_verification=[
            "load 1000 synthetic artifacts and measure query/migration reliability",
        ],
        acceptance_criteria=[
            "existing CLI workflows operate against selected repository backend",
            "invalid artifacts are reported rather than dropped",
        ],
        stop_conditions=["destructive migration without backup/restore plan"],
        governed_integration_required=True,
    ),
    PhaseContract(
        phase_id="phase_02_multi_user_collaboration",
        title="Multi-User Collaboration Model",
        subsystem="collaboration",
        goal="Support users, roles, assignments, comments, approvals, and append-only audit history.",
        milestone_status="blocked_for_governed_integration",
        dependencies=["phase_01_production_storage", "adr_0002_identity_and_rbac"],
        implementation_contracts=[
            "user/role/permission schema",
            "assignment/comment schema",
            "append-only event schema",
            "optimistic concurrency contract",
        ],
        tests=[
            "RBAC allow/deny tests",
            "append-only event tests",
            "conflict tests",
            "assignment workflow tests",
        ],
        usefulness_verification=[
            "simulate owner, reviewer, steward workflow without manual JSON edits",
        ],
        acceptance_criteria=[
            "approval requires permission",
            "event history is immutable through public commands",
        ],
        stop_conditions=["production SSO/RBAC policy required"],
        governed_integration_required=True,
    ),
    PhaseContract(
        phase_id="phase_03_industrial_ui",
        title="Industrial UI",
        subsystem="ui_api",
        goal="Provide browser workflows for triage, review, derivations, experiments, traceability, and readiness.",
        milestone_status="blocked_for_governed_integration",
        dependencies=["phase_01_production_storage", "phase_02_multi_user_collaboration", "adr_0006_deployment_model"],
        implementation_contracts=[
            "dashboard/API response contracts",
            "paper queue contract",
            "review action contract",
            "generated-vs-approved visual state contract",
        ],
        tests=[
            "UI contract tests",
            "Playwright workflow tests",
            "accessibility tests",
        ],
        usefulness_verification=[
            "timed reviewer workflow comparison between CLI and UI",
        ],
        acceptance_criteria=[
            "reviewers complete core workflows without manual JSON edits",
            "generated content is visually distinct from approved conclusions",
        ],
        stop_conditions=["production deployment decision required", "production SSO/RBAC policy required"],
        governed_integration_required=True,
    ),
    PhaseContract(
        phase_id="phase_04_search_knowledge_graph",
        title="Search And Research Knowledge Graph",
        subsystem="search_graph",
        goal="Search and graph papers, equations, assumptions, methods, experiments, code links, citations, and review states.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_01_production_storage", "adr_0004_search_and_indexing"],
        implementation_contracts=[
            "search index abstraction",
            "SQLite FTS index contract",
            "research graph edge taxonomy",
            "stale-index detection contract",
        ],
        tests=[
            "golden query tests",
            "ranking regression tests",
            "graph consistency tests",
            "stale-index tests",
        ],
        usefulness_verification=[
            "answer curated research tasks and track top-10 precision",
        ],
        acceptance_criteria=[
            "search results include source artifact references",
            "graph edges do not imply approval",
        ],
        stop_conditions=["external network service required"],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_05_parser_source_benchmarks",
        title="Parser And Source Benchmark System",
        subsystem="parser_benchmarks",
        goal="Measure extraction quality against gold fixtures for PDFs, LaTeX, citations, equations, and theorem blocks.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_00_architecture_baseline"],
        implementation_contracts=[
            "gold benchmark schema",
            "metric taxonomy",
            "benchmark trend report",
            "regression gate contract",
        ],
        tests=[
            "golden fixture comparison tests",
            "parser regression tests",
            "failure taxonomy tests",
            "trend history tests",
        ],
        usefulness_verification=[
            "demonstrate that degraded equation recovery fails a benchmark gate",
        ],
        acceptance_criteria=[
            "benchmark failures identify exact fields and examples",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_06_deep_derivations",
        title="Deep Mathematical Derivation System",
        subsystem="derivations",
        goal="Support notation normalization, assumption graphs, derivation graph validation, proof gaps, and approvals.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_13_domain_expert_packs"],
        implementation_contracts=[
            "typed derivation graph schema",
            "notation scope/conflict contract",
            "assumption graph contract",
            "proof-gap severity contract",
        ],
        tests=[
            "graph validation tests",
            "notation conflict tests",
            "missing source reference tests",
            "human-review boundary tests",
        ],
        usefulness_verification=[
            "fixture paper surfaces exact proof gaps and required experiments",
        ],
        acceptance_criteria=[
            "approval requires source references and reviewer action",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_07_experiment_execution",
        title="Experiment Execution And Reproducibility",
        subsystem="experiments",
        goal="Connect claims to reproducible computational evidence, logs, diagnostics, and bundles.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_11_workflow_orchestration"],
        implementation_contracts=[
            "experiment package schema",
            "local runner contract",
            "environment/data/model hash capture",
            "reproducibility bundle contract",
        ],
        tests=[
            "deterministic fixture experiment tests",
            "timeout tests",
            "result tolerance tests",
            "bundle round-trip tests",
        ],
        usefulness_verification=[
            "run simulation recovery fixture and produce reproducibility report",
        ],
        acceptance_criteria=[
            "failed/timed-out runs are preserved as evidence",
        ],
        stop_conditions=["external compute service required"],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_08_paper_to_code_verification",
        title="Paper-To-Code Verification",
        subsystem="traceability",
        goal="Move traceability from path existence to code-aware symbol, test, and coverage checks.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_04_search_knowledge_graph"],
        implementation_contracts=[
            "code symbol index contract",
            "stale link taxonomy",
            "test coverage mapping contract",
            "multi-language extension contract",
        ],
        tests=[
            "symbol index fixture tests",
            "missing symbol tests",
            "stale path tests",
            "coverage mapping tests",
        ],
        usefulness_verification=[
            "show implemented equations, tests, and assumptions lacking tests for a fixture method",
        ],
        acceptance_criteria=[
            "reports distinguish missing path, missing symbol, missing test, stale link, and review-required states",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_09_llm_governance",
        title="LLM Governance And Evaluation",
        subsystem="llm_governance",
        goal="Permit LLM assistance only under provider policy, prompt registry, evals, privacy checks, budgets, and audit logs.",
        milestone_status="blocked_for_governed_integration",
        dependencies=["adr_0005_llm_provider_policy", "phase_10_security_compliance_operations"],
        implementation_contracts=[
            "provider allowlist policy",
            "prompt registry schema",
            "data classification check",
            "eval suite contract",
            "audit log redaction contract",
        ],
        tests=[
            "blocked-by-default tests",
            "provider allowlist tests",
            "prompt version tests",
            "privacy filter tests",
            "eval regression tests",
        ],
        usefulness_verification=[
            "mocked synthesis includes evidence references, limitations, eval status, and human-review state",
        ],
        acceptance_criteria=[
            "live provider calls require approved provider, prompt, data class, eval pass, and audit logging",
        ],
        stop_conditions=["live credentials or provider access required", "department security/compliance approval required"],
        governed_integration_required=True,
    ),
    PhaseContract(
        phase_id="phase_10_security_compliance_operations",
        title="Security, Compliance, And Operations",
        subsystem="security_operations",
        goal="Enforce data classification, secrets policy, license tracking, export policy, retention, and audit integrity.",
        milestone_status="blocked_for_governed_integration",
        dependencies=["phase_00_architecture_baseline"],
        implementation_contracts=[
            "data classification schema",
            "secret detection contract",
            "license metadata contract",
            "export policy contract",
            "retention policy contract",
        ],
        tests=[
            "secret scanning tests",
            "export allow/deny tests",
            "classification propagation tests",
            "license metadata tests",
            "audit-log integrity tests",
        ],
        usefulness_verification=[
            "confidential export request is blocked or redacted according to policy",
        ],
        acceptance_criteria=[
            "security checks are part of readiness, CI, and release gates",
        ],
        stop_conditions=["department security/compliance approval required"],
        governed_integration_required=True,
    ),
    PhaseContract(
        phase_id="phase_11_workflow_orchestration",
        title="Workflow Orchestration",
        subsystem="orchestration",
        goal="Support bounded long-running jobs with queue state, timeouts, retries, cancellation, logs, and crash recovery.",
        milestone_status="m0_contract_complete",
        dependencies=["adr_0003_background_jobs"],
        implementation_contracts=[
            "job queue abstraction",
            "job state machine",
            "timeout/cancellation contract",
            "scheduler contract",
            "crash recovery contract",
        ],
        tests=[
            "timeout tests",
            "cancellation tests",
            "retry tests",
            "log preservation tests",
            "crash recovery tests",
        ],
        usefulness_verification=[
            "batch ingest plus benchmark plus index refresh can be monitored and cancelled",
        ],
        acceptance_criteria=[
            "no production workflow depends on an unbounded foreground command",
        ],
        stop_conditions=["external network service required"],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_12_ci_cd_observability",
        title="CI/CD And Observability",
        subsystem="ci_observability",
        goal="Define safe validation tiers, logging, metrics, coverage, release reports, and performance regression checks.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_00_architecture_baseline"],
        implementation_contracts=[
            "test tier matrix",
            "structured log schema",
            "metrics schema",
            "release report contract",
            "performance gate contract",
        ],
        tests=[
            "CI workflow validation",
            "timeout enforcement tests",
            "logging schema tests",
            "metrics emission tests",
            "performance regression tests",
        ],
        usefulness_verification=[
            "deliberately hanging test is stopped by timeout",
        ],
        acceptance_criteria=[
            "slow/live tests cannot run in fast path accidentally",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_13_domain_expert_packs",
        title="Domain Expert Packs",
        subsystem="domain_packs",
        goal="Curate domain-specific concepts, notation, assumptions, diagnostics, examples, references, and review rubrics.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_00_architecture_baseline"],
        implementation_contracts=[
            "versioned domain pack schema",
            "expert owner metadata",
            "example-paper walkthrough contract",
            "rubric coverage contract",
        ],
        tests=[
            "schema completeness tests",
            "example walkthrough tests",
            "rubric coverage tests",
            "version compatibility tests",
        ],
        usefulness_verification=[
            "domain reviewer rates whether pack surfaces relevant failure modes",
        ],
        acceptance_criteria=[
            "packs guide review without claiming correctness",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
    PhaseContract(
        phase_id="phase_14_sop_enforcement",
        title="SOP Enforcement",
        subsystem="sop_enforcement",
        goal="Turn SOP documents into enforceable approval gates with evidence, roles, event history, and overrides.",
        milestone_status="blocked_for_governed_integration",
        dependencies=["phase_02_multi_user_collaboration", "phase_10_security_compliance_operations"],
        implementation_contracts=[
            "approval gate schema",
            "approval request workflow",
            "override rationale contract",
            "readiness gate integration",
        ],
        tests=[
            "cannot approve when gates fail",
            "append-only approval history tests",
            "override authorization tests",
            "reopen invalidates downstream readiness tests",
        ],
        usefulness_verification=[
            "end-to-end paper approval fixture exposes exact blockers",
        ],
        acceptance_criteria=[
            "approval state is never inferred from generated artifact presence",
        ],
        stop_conditions=["production SSO/RBAC policy required", "department security/compliance approval required"],
        governed_integration_required=True,
    ),
    PhaseContract(
        phase_id="phase_15_scalable_ingestion",
        title="Scalable Ingestion Pipeline",
        subsystem="ingestion",
        goal="Support batch ingest, duplicate detection, source priority, failed-ingest triage, and resumable corpus reports.",
        milestone_status="m0_contract_complete",
        dependencies=["phase_11_workflow_orchestration", "phase_01_production_storage"],
        implementation_contracts=[
            "batch ingest manifest schema",
            "duplicate detection taxonomy",
            "source priority contract",
            "failed-ingest triage schema",
            "corpus report contract",
        ],
        tests=[
            "batch fixture ingest tests",
            "duplicate detection tests",
            "degraded-source tests",
            "resume-after-failure tests",
            "corpus report tests",
        ],
        usefulness_verification=[
            "fixture corpus with duplicates and missing sources produces triage without data loss",
        ],
        acceptance_criteria=[
            "batch ingest is resumable, auditable, duplicate-aware, and triage-friendly",
        ],
        stop_conditions=[],
        governed_integration_required=False,
    ),
]


def list_phase_contracts() -> list[dict[str, Any]]:
    return [phase.to_dict() for phase in PHASE_CONTRACTS]


def get_phase_contract(phase_id: str) -> dict[str, Any]:
    for phase in PHASE_CONTRACTS:
        if phase.phase_id == phase_id:
            return phase.to_dict()
    raise KeyError(f"unknown full-scale phase {phase_id}")


def _store(root: Path | None = None) -> FileStore:
    return FileStore(get_paths(root).local_research)


def _contract_path(root: Path | None, artifact_id: str) -> Path:
    return get_paths(root).governance / f"{artifact_id}.json"


def build_phase_registry(*, root: Path | None = None, artifact_id: str = "industrial_full_scale_phase_registry") -> dict[str, Any]:
    phases = list_phase_contracts()
    blocked = [phase for phase in phases if phase["milestone_status"] == "blocked_for_governed_integration"]
    payload = {
        **base_artifact(
            artifact_type="industrial_full_scale_phase_registry",
            artifact_id=artifact_id,
            provenance={"created_by": "ra full-scale-plan registry-build", "registry_version": PHASE_REGISTRY_VERSION},
            limitations=[
                "Registry records implementation contracts and stop conditions; it is not evidence of production completion.",
                "Governed integrations require accepted ADRs and department policy approval.",
            ],
        ),
        "registry_version": PHASE_REGISTRY_VERSION,
        "phase_count": len(phases),
        "blocked_for_governed_integration_count": len(blocked),
        "phases": phases,
        "milestone_model": ["m0_contract", "m1_local_deterministic", "m2_governed_integration", "m3_production_deployment"],
        "common_stop_conditions": COMMON_STOP_CONDITIONS,
    }
    _store(root).write_json(_contract_path(root, artifact_id), payload)
    return payload


def show_phase_registry(*, root: Path | None = None, artifact_id: str = "industrial_full_scale_phase_registry") -> dict[str, Any]:
    return _store(root).read_json(_contract_path(root, artifact_id))


def build_usefulness_metrics(*, root: Path | None = None, artifact_id: str = "industrial_full_scale_usefulness_metrics") -> dict[str, Any]:
    metrics = [
        {"metric_id": "paper_triage_time", "description": "time to triage a new paper", "target_direction": "decrease"},
        {"metric_id": "claim_context_lookup_time", "description": "time to find assumptions/equations/code/tests for a claim", "target_direction": "decrease"},
        {"metric_id": "source_evidence_coverage", "description": "percentage of papers with source evidence", "target_direction": "increase"},
        {"metric_id": "claim_evidence_coverage", "description": "percentage of claims with derivation, experiment, and traceability evidence", "target_direction": "increase"},
        {"metric_id": "parser_benchmark_score", "description": "parser benchmark score by paper family", "target_direction": "increase"},
        {"metric_id": "experiment_reproducibility_score", "description": "experiment reproducibility completeness score", "target_direction": "increase"},
        {"metric_id": "traceability_coverage", "description": "traceability coverage by relationship type", "target_direction": "increase"},
        {"metric_id": "review_queue_throughput", "description": "review queue throughput", "target_direction": "increase"},
        {"metric_id": "readiness_blocker_count", "description": "readiness blocker count and mean time to resolution", "target_direction": "decrease"},
        {"metric_id": "search_top10_precision", "description": "top-10 precision for curated search tasks", "target_direction": "increase"},
        {"metric_id": "blocked_provider_actions", "description": "live-provider actions blocked by policy", "target_direction": "monitor"},
        {"metric_id": "stale_job_timeout_count", "description": "stale jobs timed out automatically", "target_direction": "monitor"},
    ]
    payload = {
        **base_artifact(
            artifact_type="industrial_full_scale_usefulness_metrics",
            artifact_id=artifact_id,
            provenance={"created_by": "ra full-scale-plan usefulness-build"},
            limitations=["Metric definitions need departmental baselines before they can be used as performance targets."],
        ),
        "metrics": metrics,
        "requires_baseline_collection": True,
        "review_status": "requires_human_review",
    }
    _store(root).write_json(_contract_path(root, artifact_id), payload)
    return payload


def build_execution_readiness(*, root: Path | None = None, artifact_id: str = "industrial_full_scale_execution_readiness") -> dict[str, Any]:
    phases = list_phase_contracts()
    blockers = [
        {
            "phase_id": phase["phase_id"],
            "title": phase["title"],
            "stop_conditions": phase["stop_conditions"],
        }
        for phase in phases
        if phase["milestone_status"] == "blocked_for_governed_integration"
    ]
    payload = {
        **base_artifact(
            artifact_type="industrial_full_scale_execution_readiness",
            artifact_id=artifact_id,
            provenance={"created_by": "ra full-scale-plan readiness-build"},
            limitations=["Execution readiness is a planning gate and does not certify production readiness."],
        ),
        "status": "blocked_for_governed_integration" if blockers else "ready_for_local_execution",
        "phase_count": len(phases),
        "blocked_phase_count": len(blockers),
        "blockers": blockers,
        "ready_for_m0_contract_execution": True,
        "ready_for_m1_local_deterministic_execution": True,
        "ready_for_m2_governed_integration": False,
        "next_actions": [
            "complete or accept required ADRs before governed integrations",
            "collect baseline usefulness metrics",
            "execute local deterministic phases with bounded validation",
        ],
    }
    _store(root).write_json(_contract_path(root, artifact_id), payload)
    return payload
