# Industrial Mathematical Finance Research Platform Plan — 2026-04-26

## Context

`research-assistant` now supports structured-source-first ingest, source-linked audit notes, citation graph cache/proposals, and conservative literature-audit proposals. The next goal is to evolve it toward an industrial departmental tool for mathematical finance/economics developers working across computational econometrics, computational statistics, ML/LLMs, large-scale Bayesian learning, computational physics, and applied mathematics.

The plan below turns the remaining industrial gaps into executable phases. Each phase must preserve the core trust boundary: the system may automate extraction, linking, graphing, proposal generation, and tests, but it must never silently promote machine-generated content into verified mathematical conclusions.

## Phase 0 — Shared artifact contracts and recovery guardrails

Before expanding the platform, define a common contract for every new local artifact family so later phases can link records safely and survive interrupted implementation.

Deliverables:
- shared artifact fields: `schema_version`, `artifact_id`, `artifact_type`, `paper_id`, `created_at`, `provenance`, `review_status`, `requires_human_review`, and `limitations`;
- canonical local paths for derivations, experiments, benchmark manifests/runs, synthesis proposals, governance records, graph intelligence reports, and future job records;
- stable ID conventions for claims, assumptions, derivation steps, experiments, code links, and implementation checks;
- reset-memo checkpoint fields: current phase, files touched, tests run, remaining risks, and next safe step;
- tests that generated artifacts carry explicit review/trust-boundary metadata and can be loaded without network access.

Phase 0 acceptance criteria:
- no generated derivation, synthesis, graph report, benchmark result, experiment record, or governance artifact is accepted into `technical_audit` automatically;
- every artifact family is local-first and deterministic under mocked or fixture-only tests;
- path and schema helpers are shared instead of copied phase by phase.

## Phase 1 — Domain knowledge schemas

Add typed audit schemas for core departmental domains: HMC/MCMC, SMC/particle filtering, variational inference, macro-finance structural models, state-space/econometric estimators, stochastic control/dynamic programming, neural transport/flows, diffusion/score models, and LLM/Bayesian deep learning.

Deliverables:
- schema module for domain templates;
- CLI command to list/show templates;
- tests that every template has required concept/claim/checklist fields.

## Phase 2 — Derivation-aware technical audit records

Add derivation worksheet artifacts that separate paper claims, assumptions, derivation steps in project notation, unresolved gaps, and required experiments.

Deliverables:
- derivation artifact path and JSON schema;
- CLI create/show/update commands;
- tests for provenance and separation from accepted `technical_audit`.

## Phase 3 — Experiment integration

Connect paper claims to experiment plans/results and diagnostics.

Deliverables:
- claim-to-experiment links;
- experiment checklist templates for gradient checks, conservation checks, simulation recovery, posterior calibration, and likelihood sanity checks;
- tests preserving links through export.

## Phase 4 — Citation graph intelligence

Improve graph quality beyond raw edges.

Deliverables:
- graph node dedup diagnostics for DOI/arXiv/title/source ids;
- citation intent placeholders;
- cluster/trend report scaffold;
- tests with mocked graph data.

## Phase 5 — Department-scale review primitives

Add collaboration-ready metadata without requiring a server yet.

Deliverables:
- reviewer assignment, owner/steward, workstream tags, review history entries;
- CLI commands to set/list these fields;
- tests for JSON persistence and export.

## Phase 6 — Parser/source robustness benchmarks

Add benchmark manifests for paper families and extraction quality checks.

Deliverables:
- benchmark manifest schema;
- fixture benchmark runner for source/PDF extraction counts;
- tests that benchmark output records pass/fail/limitations.

## Phase 7 — LLM-assisted synthesis scaffolding

Add proposal containers for monograph expositions, method comparison tables, assumptions matrices, and implementation implications.

Deliverables:
- synthesis proposal artifact separate from accepted facts;
- CLI propose/show commands using deterministic source evidence only for now;
- tests proving evidence references and limitations are present.

## Phase 8 — Paper-to-code and experiment links

Strengthen code links into equation/theorem/algorithm implementation records.

Deliverables:
- link types for equation-to-code, theorem-assumption-to-test, algorithm-to-implementation-checklist;
- CLI commands or extension of existing link-add;
- tests for link records and export.

## Phase 9 — Evaluation/governance/security artifacts

Add quality and governance metadata.

Deliverables:
- extraction quality metrics scaffold;
- provenance hashes for local artifacts where available;
- provider/model policy metadata placeholders;
- tests for local/offline-safe operation.

## Phase 10 — Infrastructure and UI/MCP readiness

Prepare for indexed/shared infrastructure without rewriting the local-first core.

Deliverables:
- backend function boundaries for future MCP/UI;
- export formats for dashboard/indexing;
- job status artifact schema for future background workers;
- tests for JSON contract stability.

## Independent audit of this plan

Risks identified:
- Scope is large; each phase must remain a small, testable scaffold rather than a full platform rewrite.
- Human trust boundary could be violated if proposal artifacts are accepted automatically; every generated artifact must carry `requires_human_review` or equivalent.
- Department-scale features should remain local-first until storage/collaboration requirements are explicit.
- LLM synthesis should be deterministic/scaffolded first; live model calls need provider/security policy before implementation.
- Citation graph expansion and benchmark runners must avoid live network in deterministic tests.
- Artifact interoperability will break if phases invent incompatible IDs for claims, equations, assumptions, experiments, jobs, and code targets.
- Review history can become misleading unless collaboration metadata is append-only and clearly separate from approval state.
- Governance metadata must exist before LLM-oriented synthesis grows beyond deterministic scaffolds.

Mitigations:
- Each phase adds schema/CLI/tests first, not broad infrastructure.
- Full-suite validation remains required at coherent checkpoints.
- Reset memo must be updated after every phase with tests, risks, and next step.
- Phase 0 establishes common artifact fields, local paths, stable IDs, and trust-boundary defaults before Phase 1 begins.
- Synthesis and governance phases must remain offline-safe until provider/model policy is explicitly upgraded.
