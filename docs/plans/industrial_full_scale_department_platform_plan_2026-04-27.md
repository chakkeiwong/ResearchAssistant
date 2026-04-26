# Industrial Full-Scale Department Platform Plan — 2026-04-27

## Purpose

This document is the implementation plan for turning `research-assistant` from a local validated research-artifact platform into a fully industrial departmental tool for mathematical finance and economics developers working across computational econometrics, computational statistics, machine learning, LLMs, large-scale Bayesian learning, computational physics, and applied mathematics.

The current codebase already has local-first artifacts, validation, readiness reports, traceability reports, experiment records, derivation worksheets, benchmark manifests/runs, governance records, SOP artifacts, and bounded validation scripts. This plan describes the remaining work required to make those capabilities durable, scalable, collaborative, secure, measurable, and useful in daily departmental research.

## Core Principles

- Preserve the trust boundary: generated content, LLM synthesis, parser output, benchmark output, derivation worksheets, and readiness reports are review material until a human approval workflow accepts them.
- Build in layers: storage and schema discipline before UI, collaboration, orchestration, or live provider integrations.
- Keep deterministic tests local-first. Live network/provider tests must be opt-in, marked separately, and blocked by policy by default.
- Every phase must include usefulness verification, not just implementation tests.
- Every phase must update the reset memo with files touched, tests run, residual risks, and the next safe step.
- Use bounded validation commands. Avoid unbounded full-suite runs.

## Audit-Driven Modification — Execution Milestones And Stop Conditions

An independent developer audit found that the original 15-point plan was directionally complete but too easy to mis-execute as one giant "production" patch. Several phases require architecture decisions, department policy ownership, credentials, deployment choices, or security review before real production implementation is honest. Therefore every phase must be executed through explicit milestones:

- M0 contract: schemas, ADRs, tool contracts, test contracts, usefulness metrics, stop conditions, and readiness gates.
- M1 local deterministic implementation: offline backend/CLI behavior, local fixtures, bounded tests, and no live services.
- M2 governed integration: real storage/auth/UI/orchestration/provider integrations only after the relevant ADR and policy records are accepted.
- M3 production deployment: monitoring, security review, operational runbooks, migration/rollback, and department approval.

This execution pass is allowed to complete M0 for all phases and M1 only where it can be done safely with local deterministic code. A phase must be marked `blocked_for_governed_integration` rather than "done" when it needs SSO, production storage selection, live LLM access, compliance policy, service deployment, or external credentials.

Plan modifications required by the audit:
- add architecture and ADR control artifacts before implementation;
- add phase contracts with dependencies, tests, usefulness checks, stop conditions, and milestone status;
- add a machine-readable registry so readiness reports and future agents can see what is complete, blocked, or policy-dependent;
- add usefulness metrics as first-class artifacts, not prose-only aspirations;
- add tests that prevent these contracts from drifting.

## Current Foundation

Relevant existing implementation points:
- Industrial backend: `src/research_assistant/industrial/platform.py`
- CLI surfaces: `src/research_assistant/cli.py`
- Workspace export adapter: `src/research_assistant/adapters/workspace_exports.py`
- Artifact schema helpers: `src/research_assistant/schemas/artifact.py`
- Domain templates: `src/research_assistant/schemas/domain_templates.py`
- Industrial integration tests: `tests/integration/test_industrial_platform_cli.py`
- Bounded validation scripts: `scripts/run_fast_tests.sh`, `scripts/run_bounded_tests.sh`

## Phase Execution Loop

For each phase:
1. Write a short phase note in the reset memo.
2. Add or update the smallest stable contract first: schema, storage interface, CLI/API contract, or UI contract.
3. Implement the behavior behind that contract.
4. Add focused unit and integration tests.
5. Add a usefulness verification fixture or workflow.
6. Run bounded validation.
7. Audit as another developer: trust boundary, data loss, concurrency, security, and false-approval risk.
8. Tidy names, docs, and exports.
9. Update reset memo with results and residual risks.

## Phase 0 — Architecture Baseline And Roadmap Control

Goal: create a durable architecture control layer so the remaining phases do not drift into incompatible implementations.

Implementation instructions:
- Add `docs/architecture/industrial_platform_architecture.md`.
- Define subsystem boundaries: storage, artifact contracts, ingestion, parser benchmarks, derivations, experiments, traceability, search/graph, LLM governance, collaboration, UI, orchestration, security, and observability.
- Add an architecture decision record directory, for example `docs/architecture/adr/`.
- Add ADR templates for storage choice, identity/RBAC, background jobs, search/indexing, LLM provider policy, and deployment model.
- Add a phase registry artifact or doc table mapping all 15 phases to owners, dependencies, test suites, and acceptance criteria.

Tests:
- Documentation contract test that required ADR files and headings exist.
- Static check that current CLI/tool contract lists new planned contract names only when implemented.

Usefulness verification:
- A new developer can read the architecture doc and identify where to implement a feature without asking.

Acceptance criteria:
- All phase dependencies are explicit.
- No implementation phase starts without a named contract and acceptance gate.

## Phase 1 — Production Storage Layer

Goal: replace ad hoc local JSON as the only durable backend with a production-ready storage abstraction while preserving local JSON compatibility.

Implementation instructions:
- Introduce a storage interface, for example `ArtifactRepository`, with methods for `put`, `get`, `list`, `query`, `version`, `migrate`, and `validate`.
- Keep current JSON `FileStore` as `LocalJsonArtifactRepository`.
- Add a SQLite-backed repository first. Use explicit migrations and schema-version tables.
- Define tables for papers, artifacts, links, reviews, jobs, events, users, comments, and search index metadata.
- Add import/export routines between local JSON and SQLite.
- Add migration reports that say what changed, what failed, and what needs manual review.
- Add backup and restore commands for repository snapshots.

Tests:
- Unit tests for repository interface behavior across JSON and SQLite implementations.
- Migration tests from current local JSON fixtures.
- Corrupt-record recovery tests.
- Concurrency tests for simultaneous reads/writes using SQLite transactions.
- Backup/restore round-trip tests.

Usefulness verification:
- Load a fixture corpus of at least 1,000 synthetic papers/artifacts and verify query latency, migration time, and recovery behavior.
- Measure time to find all artifacts for one paper before and after repository indexing.

Acceptance criteria:
- Existing CLI workflows work against both local JSON and SQLite backends.
- Migrations are reversible or produce a validated backup.
- Invalid artifacts are reported, never silently dropped.

## Phase 2 — Multi-User Collaboration Model

Goal: support real departmental review workflows with users, roles, assignments, comments, approvals, and append-only audit history.

Implementation instructions:
- Define user, role, permission, assignment, comment, and event schemas.
- Add RBAC permissions for read, write, assign, approve, administer, export, and provider-policy changes.
- Convert collaboration JSON scaffolds into repository-backed records.
- Add append-only event log entries for every state transition.
- Add optimistic concurrency controls using version numbers or ETags.
- Add CLI/API commands for user creation, assignment, comment, review request, approval request, and role management.
- Keep local single-user mode available for research notebooks and offline work.

Tests:
- RBAC allow/deny tests.
- Append-only event-history tests.
- Concurrent update conflict tests.
- Assignment and comment workflow tests.
- Export tests showing collaboration metadata without leaking secrets.

Usefulness verification:
- Simulate a three-reviewer workflow: owner assigns paper, derivation reviewer comments, experiment reviewer requests evidence, steward approves readiness after blockers clear.
- Measure whether the whole workflow can be completed without manually editing JSON.

Acceptance criteria:
- No user can approve artifacts without required permission.
- Event history is immutable through public commands.
- Conflicting edits produce a clear conflict response.

## Phase 3 — Industrial UI

Goal: provide a real browser-based workbench for triage, review, derivation, experiment evidence, traceability, readiness blockers, and dashboard workflows.

Implementation instructions:
- Build a minimal web app only after backend contracts for storage, auth, artifacts, and readiness are stable.
- Add pages for paper queue, paper detail, source evidence, derivation worksheet, experiment evidence, traceability, benchmarks, readiness, and admin policies.
- Use the existing dashboard export as the first UI contract; evolve it into typed API responses.
- Add review actions with visible provenance and human-review state.
- Show generated content in a visually distinct review/proposal state.
- Add filters for domain, owner, reviewer, readiness status, artifact type, benchmark status, and source availability.

Tests:
- Component tests for each page state.
- Playwright tests for paper triage, derivation review, experiment evidence review, and readiness blocker resolution.
- Accessibility checks for keyboard navigation and labels.
- Contract tests that UI consumes stable backend JSON.

Usefulness verification:
- Run timed workflows with at least two users: triage a new paper, find an unresolved derivation gap, assign an experiment reviewer, and export a readiness report.
- Compare CLI-only time against UI-assisted time.

Acceptance criteria:
- A reviewer can complete core review workflows without using the CLI.
- Generated/proposed content is never visually confused with approved conclusions.

## Phase 4 — Search And Research Knowledge Graph

Goal: make papers, equations, theorems, assumptions, methods, experiments, code links, citations, and review states searchable and graph-queryable.

Implementation instructions:
- Add a search index abstraction with local SQLite FTS as the first backend.
- Index paper metadata, abstracts, source sections, equations, theorem-like blocks, citations, bibliography, derivation steps, assumptions, experiment records, traceability links, and comments.
- Add graph records for paper-cites-paper, paper-uses-method, claim-depends-on-assumption, equation-implemented-by-code, theorem-tested-by-test, experiment-supports-claim, and reviewer-approved-artifact.
- Add CLI/API search commands for text search, structured filters, and graph neighborhood queries.
- Add stale-index detection and rebuild commands.
- Add optional semantic index hooks behind a disabled policy gate.

Tests:
- Golden query fixtures.
- Ranking regression tests.
- Graph consistency tests for missing nodes, duplicate IDs, and invalid edge types.
- Stale-index detection tests.

Usefulness verification:
- For a fixture corpus, answer tasks such as "find all HMC papers with target-density assumptions but missing simulation recovery evidence" and "find equations linked to missing tests."
- Track precision of top-10 search results against hand-labeled expected answers.

Acceptance criteria:
- Search returns explainable results with source artifact references.
- Graph queries never infer approval from presence of an edge.

## Phase 5 — Parser And Source Benchmark System

Goal: turn parser evaluation into an industrial benchmark corpus with measurable extraction quality.

Implementation instructions:
- Define gold-standard benchmark schemas for title, authors, year, abstract, sections, equations, theorem blocks, figures, tables, citations, references, labels, macros, and source/PDF provenance.
- Build benchmark runners for LaTeX source, PDF-only, mixed source/PDF, and degraded-source cases.
- Add metrics: exact match, normalized match, precision/recall/F1, structural completeness, citation/reference consistency, equation-label recovery, theorem recovery, and parser agreement.
- Add benchmark report artifacts and trend history.
- Add regression gates for parser changes.
- Add benchmark fixtures for synthetic, arXiv LaTeX, scanned/degraded PDF, long title, author footnotes, dense equations, and bibliography edge cases.

Tests:
- Golden fixture comparison tests.
- Parser regression tests.
- Failure taxonomy tests.
- Benchmark trend-history tests.

Usefulness verification:
- Demonstrate that a parser change with worse equation recovery fails the benchmark gate.
- Publish a benchmark dashboard showing parser quality by paper family.

Acceptance criteria:
- Parser quality can be measured before and after a code change.
- Benchmark failures identify exact fields and examples, not only a global score.

## Phase 6 — Deep Mathematical Derivation System

Goal: support industrial mathematical review of claims, assumptions, notation, derivations, and proof gaps.

Implementation instructions:
- Extend derivation worksheets into typed derivation graphs.
- Add notation normalization with aliases, scopes, conflicts, and domain-specific meanings.
- Add assumption graph records with source evidence, reviewer status, and dependency edges.
- Add derivation step types: definition, lemma, theorem, proof step, approximation, numerical assumption, algorithmic implication, and unresolved gap.
- Add proof-gap severity and owner assignment.
- Add links from derivation nodes to source sections/equations/theorems and to code/tests/experiments.
- Add optional symbolic-check hooks for simple algebraic or dimensional consistency checks, clearly marked as heuristic.

Tests:
- Graph validation tests.
- Notation conflict tests.
- Missing-source-reference tests.
- Human-review boundary tests.
- Round-trip export/import tests.

Usefulness verification:
- Apply the system to a fixture paper with intentionally missing assumptions and verify reviewers can identify exact proof gaps and required experiments.
- Measure number of claims with complete source, assumption, derivation, and evidence links.

Acceptance criteria:
- No derivation node can be marked approved without required source references and reviewer action.
- The system identifies broken derivation dependencies and notation conflicts.

## Phase 7 — Experiment Execution And Reproducibility

Goal: connect claims to reproducible computational evidence, not just recorded experiment notes.

Implementation instructions:
- Define experiment package schema: code entry point, environment, dataset references, seeds, expected outputs, diagnostics, resource needs, and acceptance criteria.
- Add local runner abstraction with dry-run, smoke-run, and full-run modes.
- Capture environment hashes, dependency lockfiles, seed state, dataset/model hashes, stdout/stderr, metrics, generated artifacts, and failure logs.
- Add support for containers later, behind an operations policy gate.
- Add reproducibility bundle export.
- Add result comparison against expected metrics and tolerance bands.
- Add reviewer workflow for accepting experiment evidence.

Tests:
- Deterministic fixture experiment tests.
- Timeout and cancellation tests.
- Missing dataset/model hash tests.
- Result tolerance tests.
- Reproducibility bundle round-trip tests.

Usefulness verification:
- Run a small simulation recovery or calibration fixture and verify the platform captures enough evidence for another developer to rerun it.
- Measure time from claim to reproducibility report.

Acceptance criteria:
- Every experiment result records environment, seed, code version, data/model hashes, diagnostics, and reviewer status.
- Failed or timed-out runs are preserved as evidence, not overwritten.

## Phase 8 — Paper-To-Code Verification

Goal: move from path existence checks to code-aware traceability and test coverage for mathematical claims.

Implementation instructions:
- Add code indexer for Python first, with extension points for Julia, R, Stan, C++, and notebooks.
- Parse symbols, functions, classes, test files, docstrings, and references to paper labels where possible.
- Add traceability checks for equation-to-code, theorem-assumption-to-test, algorithm-to-implementation, and experiment-to-result relationships.
- Integrate with coverage reports for tests connected to paper claims.
- Add stale-link detection when code paths or symbols move.
- Add reviewer workflow for traceability approval.

Tests:
- Symbol index fixtures.
- Missing symbol and stale path tests.
- Test coverage mapping tests.
- Multi-language placeholder contract tests.

Usefulness verification:
- For a fixture method, show a reviewer exactly which equations are implemented, which tests exercise them, and which assumptions lack tests.
- Measure traceability coverage percentage per paper/project.

Acceptance criteria:
- Traceability report distinguishes missing path, missing symbol, missing test, stale link, and review-required states.
- Existing-code detection does not imply mathematical correctness.

## Phase 9 — LLM Governance And Evaluation

Goal: permit LLM-assisted research workflows only under explicit governance, evaluation, privacy, and audit controls.

Implementation instructions:
- Expand model policy artifacts into enforceable provider/model policy records.
- Add prompt registry with prompt IDs, versions, owners, intended use, input data class, and evaluation requirements.
- Add privacy/data-classification checks before sending any content to a provider.
- Add eval suites for summarization, citation extraction, derivation assistance, synthesis proposals, and hallucination detection.
- Add cost budgets, rate limits, provider allowlists, and model-version pinning.
- Add complete request/response audit logs with redaction support.
- Keep live model calls disabled by default.

Tests:
- Blocked-by-default tests.
- Provider allowlist tests.
- Prompt registry version tests.
- Privacy filter tests.
- Eval regression tests with fixture outputs.
- Audit-log redaction tests.

Usefulness verification:
- Run an offline mocked LLM synthesis workflow and verify the proposal includes evidence references, limitations, eval status, and human-review state.
- Before any live use, require a policy-owner approval record and passing eval threshold.

Acceptance criteria:
- No live provider call can occur without approved provider, approved prompt, allowed data class, eval pass, and audit logging.
- LLM output never writes directly into accepted `technical_audit`.

## Phase 10 — Security, Compliance, And Operations

Goal: make the system safe for departmental data, code, credentials, licenses, and exports.

Implementation instructions:
- Add data classification levels for public, internal, confidential, restricted, and provider-prohibited content.
- Add secret detection and no-secret-in-artifact validation.
- Add license tracking for papers, code, models, datasets, and generated exports.
- Add export policy checks based on user role, data class, and artifact type.
- Add retention and deletion policy records.
- Add incident-response and audit-log review procedures.
- Add deployment hardening checklist for server mode.

Tests:
- Secret scanning fixtures.
- Export allow/deny tests.
- Data classification propagation tests.
- License metadata validation tests.
- Audit-log integrity tests.

Usefulness verification:
- Simulate an export request involving confidential notes and verify the system blocks or redacts according to policy.
- Show an operations reviewer a complete audit trail for a policy-sensitive action.

Acceptance criteria:
- Sensitive data cannot be exported or sent to providers without policy approval.
- Security checks are part of readiness, CI, and release gates.

## Phase 11 — Workflow Orchestration

Goal: support long-running parsing, indexing, benchmark, experiment, and synthesis jobs safely.

Implementation instructions:
- Replace job-status scaffolds with a real job queue abstraction.
- Add local queue implementation first, then leave extension point for Redis/Celery/Arq/RQ or equivalent.
- Add job states: queued, running, succeeded, failed, cancelled, timed_out, retrying.
- Add bounded execution, heartbeats, progress, logs, retry policy, cancellation, and artifact output references.
- Add scheduler for periodic index rebuilds, benchmark runs, and readiness refreshes.
- Add failure isolation so one stuck job does not block the platform.

Tests:
- Timeout tests.
- Cancellation tests.
- Retry tests.
- Job log preservation tests.
- Scheduler smoke tests.
- Crash recovery tests.

Usefulness verification:
- Run a batch ingest plus benchmark plus index rebuild workflow and verify progress can be monitored and cancelled.
- Confirm stalled jobs are timed out and reported without manual process killing.

Acceptance criteria:
- No production workflow depends on an unbounded foreground command.
- Every long-running operation has status, timeout, logs, and recovery behavior.

## Phase 12 — CI/CD And Observability

Goal: make development, validation, release, and operations predictable.

Implementation instructions:
- Define test tiers: fast, bounded, broad deterministic, slow parser/PDF, optional live-provider, performance, and security.
- Add CI workflows for fast and broad deterministic tiers.
- Add nightly or manual slow-suite workflows.
- Add coverage reporting and minimum thresholds for critical modules.
- Add structured logging for CLI/backend operations.
- Add metrics for ingest throughput, benchmark scores, readiness blockers, job durations, and error rates.
- Add release checklist and changelog discipline.

Tests:
- CI workflow validation.
- Timeout enforcement tests.
- Logging schema tests.
- Metrics emission tests.
- Performance regression tests for search/indexing and artifact validation.

Usefulness verification:
- Demonstrate that a deliberately hanging test is stopped by timeout.
- Show a release candidate report with tests, coverage, benchmark trend, and known risks.

Acceptance criteria:
- Agents and developers have safe default validation commands.
- Slow or live tests cannot accidentally run in the fast path.

## Phase 13 — Domain Expert Packs

Goal: make audits domain-aware for frontier mathematical finance/economics research.

Implementation instructions:
- Convert domain templates into versioned domain packs.
- For each domain pack, include concepts, notation, assumption classes, theorem/equation roles, method families, common failure modes, required diagnostics, benchmark examples, canonical references, and review rubrics.
- Initial packs: HMC/MCMC, SMC/particle filtering, variational inference, macro-finance structural models, state-space econometrics, stochastic control/dynamic programming, neural transport/flows, diffusion/score models, LLM/Bayesian deep learning, computational physics numerical methods, and applied mathematics PDE/optimization methods.
- Add pack compatibility with derivation, experiment, benchmark, and traceability workflows.
- Add expert-owner metadata and review cadence.

Tests:
- Schema completeness tests.
- Domain pack example-paper walkthrough tests.
- Rubric coverage tests.
- Version compatibility tests.

Usefulness verification:
- For each pack, run one fixture paper through audit prompts, derivation worksheet, experiment checklist, and readiness report.
- Have a domain reviewer rate whether the pack surfaces the right failure modes.

Acceptance criteria:
- Domain packs guide reviewers without claiming correctness.
- Every pack has owner, version, examples, and required evidence types.

## Phase 14 — SOP Enforcement

Goal: convert SOP documents into enforced approval gates.

Implementation instructions:
- Define approval gate schemas for paper approval, derivation review, experiment evidence, benchmark pass, traceability coverage, LLM synthesis, export approval, and release approval.
- Add commands/API actions for requesting approval, granting approval, rejecting approval, and reopening approval.
- Link approvals to users, roles, evidence artifacts, timestamps, and immutable event history.
- Add readiness integration so blocked gates prevent approval.
- Add override workflow requiring elevated role and written rationale.

Tests:
- Cannot approve when required gates fail.
- Approval event history is append-only.
- Override requires correct role and rationale.
- Reopening approval invalidates downstream readiness status where appropriate.

Usefulness verification:
- Run an end-to-end paper approval fixture: source evidence, derivation, experiment, benchmark, traceability, governance, final approval.
- Verify reviewers can see exactly why approval is blocked.

Acceptance criteria:
- SOP gates are enforceable, auditable, and explainable.
- Approval state is never inferred from generated artifact presence.

## Phase 15 — Scalable Ingestion Pipeline

Goal: make ingestion robust enough for departmental corpus growth.

Implementation instructions:
- Add batch ingest manifests for PDFs, arXiv IDs, source bundles, DOI lists, and existing folders.
- Add duplicate detection using title/author/year, DOI, arXiv ID, source hash, PDF hash, and citation graph identity.
- Add source priority rules: structured source first, then source bundle, then PDF parser, then degraded text.
- Add failed-ingest triage records with retry suggestions.
- Add resumable batch jobs through the orchestration layer.
- Add corpus-level reports for ingestion coverage, parser confidence, source availability, duplicate clusters, and review backlog.

Tests:
- Batch fixture ingest tests.
- Duplicate detection tests.
- Degraded-source tests.
- Resume-after-failure tests.
- Corpus report tests.

Usefulness verification:
- Ingest a fixture corpus with duplicates, missing sources, malformed PDFs, and source bundles; verify the system produces a triage report and does not lose records.
- Measure throughput and review backlog after ingest.

Acceptance criteria:
- Batch ingest is resumable, auditable, and duplicate-aware.
- Degraded ingestion produces useful triage instead of silent failure.

## Cross-Phase Usefulness Metrics

Track these metrics throughout implementation:
- time to triage a new paper;
- time to find all related assumptions/equations/code/tests for a claim;
- percentage of papers with source evidence;
- percentage of claims with derivation, experiment, and traceability evidence;
- parser benchmark score by paper family;
- experiment reproducibility completeness score;
- traceability coverage by relationship type;
- review queue throughput;
- readiness blocker count and mean time to resolution;
- search top-10 precision for curated tasks;
- number of live-provider actions blocked by policy;
- number of stale jobs timed out automatically.

## Verification Matrix

Every phase must include:
- unit tests for schema and pure logic;
- integration tests for CLI/API workflow;
- contract tests for exported JSON/API surfaces;
- regression tests using golden fixtures;
- negative tests for invalid, missing, malformed, or unauthorized inputs;
- usefulness verification with a realistic workflow task;
- reset memo update with bounded validation results.

## Suggested Validation Commands

Fast phase validation:

```bash
scripts/run_fast_tests.sh
```

Broader bounded validation:

```bash
scripts/run_bounded_tests.sh
```

Phase-specific validation should use explicit `timeout`, for example:

```bash
timeout 300s python -m pytest tests/integration/test_industrial_platform_cli.py -q
```

Slow parser/PDF/provider/performance tests must be separate, named, and opt-in.

## Final Industrial Acceptance Criteria

The platform can be considered industrial-scale for the department when:
- storage is transactional, versioned, backed up, and migratable;
- multi-user review, RBAC, comments, assignments, and append-only events work;
- reviewers can complete core workflows through UI or API without editing JSON;
- search and graph queries support real research discovery across papers, math, code, and experiments;
- parser/source quality is benchmarked with gold fixtures and regression gates;
- derivation review captures notation, assumptions, dependencies, proof gaps, and approvals;
- experiments are executable or reproducibility-packaged with evidence and logs;
- traceability links claims/equations/theorems/algorithms to code and tests;
- LLM usage is governed, evaluated, audited, and blocked by default;
- security, compliance, export, license, and retention controls are enforced;
- long-running jobs are bounded, cancellable, observable, and recoverable;
- CI/CD separates fast, broad, slow, live, performance, and security tiers;
- domain expert packs are curated, versioned, and useful in real reviews;
- SOP gates are enforced before approvals;
- batch ingestion is scalable, resumable, duplicate-aware, and triage-friendly.

## Independent Audit Of This Plan

Risks:
- The full plan is large enough to span multiple milestones and cannot be safely executed as one giant patch.
- Storage, UI, auth, and orchestration choices are architecture decisions; they must not be hidden inside incidental feature work.
- LLM integration and provider calls are high-risk and must remain blocked until governance, evals, privacy, and audit logs are implemented.
- Parser benchmarks can create false confidence if fixtures are too narrow.
- Traceability and derivation tools can support review but cannot prove mathematical correctness by themselves.
- Security/compliance controls require department policy owners.

Mitigations:
- Execute one phase at a time with reset-memo checkpoints.
- Start each major subsystem with an ADR.
- Keep local deterministic tests as the default validation path.
- Add usefulness verification to every phase.
- Preserve the generated-vs-approved trust boundary in every schema, CLI command, UI view, and export.
