# Industrial Scale Implementation Plan — 2026-04-27

## Context

The industrial scaffold passes added local artifact families for derivations, experiments, benchmark manifests/runs, graph reports, synthesis proposals, governance records, traceability reports, collaboration records, artifact indices, service contracts, operations policies, and SOPs.

This pass converts those scaffolds into a stricter local operational layer. It should make the platform safer and more useful for departmental mathematical finance/economics developers working across computational econometrics, computational statistics, machine learning, LLMs, large-scale Bayesian learning, computational physics, and applied mathematics. It must not claim to be a deployed multi-user production system.

## Execution Rules

For every phase:
1. Plan the smallest enforceable local contract.
2. Execute backend, CLI, export, or script changes.
3. Test with local fixtures and bounded commands.
4. Audit the patch as if it came from another developer.
5. Tidy names and outputs.
6. Update the reset memo.

Validation must use `timeout`. Unbounded full-suite runs are not allowed in this pass.

## Phase 1 — Artifact Contract Validator

Add a validator over all industrial artifact families.

Deliverables:
- backend validation for required artifact fields, schema versions, review-boundary metadata, provenance, limitations, and JSON readability;
- validation severity counts and per-record issue lists;
- CLI command `ra industrial-validate`;
- tests covering clean and intentionally invalid local artifacts.

## Phase 2 — Artifact Index With Validation

Upgrade the artifact index from inventory-only to an operational index.

Deliverables:
- validation summary embedded in `artifact-index build`;
- paper/family query filters via `artifact-index query`;
- migration-needed flags based on schema version and validation findings;
- tests for counts, filters, and trust-boundary visibility.

## Phase 3 — Benchmark Quality Scoring

Make benchmark runs more diagnostic while staying fixture-only.

Deliverables:
- per-fixture quality score over expected title/authors/year/sections/equations/theorems/citations;
- pass/fail thresholds;
- limitation taxonomy for missing fixture, unscored fixture, missing expected fields, and insufficient score;
- tests with passing and failing fixture records.

## Phase 4 — Traceability Target Checks

Strengthen paper-to-code reports by checking local file targets.

Deliverables:
- local path existence checks for link targets and target refs;
- classification of code and test targets;
- missing-target blocker counts;
- tests using existing and missing paths.

## Phase 5 — Experiment Reproducibility Evidence

Score experiment run records for reproducibility evidence.

Deliverables:
- completeness score for environment, seed, dataset hash, model hash, diagnostics, result summary, and acceptance status;
- blockers for runs missing required evidence;
- experiment plan readiness status;
- tests proving generated evidence remains review material.

## Phase 6 — Derivation Dependency Validation

Validate derivation worksheets as review records.

Deliverables:
- known ID registry from claims, assumptions, derivation steps, unresolved gaps, and required experiments;
- unresolved dependency/comment-target findings;
- readiness status without promoting derivations into accepted `technical_audit`;
- tests for valid and invalid dependency links.

## Phase 7 — Policy Gate Report

Aggregate governance, model policy, synthesis, derivation, experiment, traceability, benchmark, and SOP signals into a local readiness report.

Deliverables:
- backend report builder and CLI command `ra industrial-readiness`;
- explicit blocker/warning counts;
- offline-safe default, live-model-call blocker, and human-review status;
- tests for blocked and ready-ish local states.

## Phase 8 — Dashboard Readiness Export

Make the dashboard export useful for UI/MCP consumers.

Deliverables:
- dashboard counts by family;
- latest validation/readiness status if available;
- blocker counts and next-actions list;
- tests for stable JSON keys.

## Phase 9 — SOP Gate Report

Make SOPs operational by mapping gate sections to current artifacts.

Deliverables:
- SOP gate report embedded in readiness;
- review gates for paper approval, derivation review, experiment evidence, benchmark gates, escalation, and onboarding;
- tests that missing SOP or missing artifact families produce warnings rather than false approval.

## Phase 10 — Bounded Validation Scripts

Add safer validation entry points for future agents.

Deliverables:
- `scripts/run_fast_tests.sh` for focused unit/integration checks;
- `scripts/run_bounded_tests.sh` for the broader deterministic subset with explicit timeout;
- scripts must fail fast, avoid live network, and print the exact command they run.

## Independent Developer Audit

Audit findings:
- The plan now has enforceable local contracts rather than only artifact creation, but it is still not a production service architecture.
- Validation must inspect existing files without rewriting user data or deleting malformed artifacts.
- Index/query features must not infer mathematical correctness from artifact presence.
- Benchmark scores should describe fixture metadata completeness, not parser correctness against a full ground truth corpus.
- Traceability target checks can prove paths exist, not that code faithfully implements a theorem or equation.
- Experiment completeness is evidence hygiene, not a scientific replication result.
- Readiness reports must use "blocked", "warnings", and "requires_human_review" language instead of "approved" unless a separate human approval path exists.
- Bounded scripts reduce stale sessions but do not replace full validation when a future checkpoint truly needs it.

Mitigations:
- Every generated report uses the shared artifact contract and defaults to `requires_human_review`.
- All tests use local files and fixtures only.
- The readiness report reports blockers and warnings separately from accepted audit conclusions.
- No live provider/model/network calls are introduced.
- Reset memo updates record tests, residual risks, and the next safe step.
