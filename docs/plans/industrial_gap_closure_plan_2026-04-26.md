# Industrial Gap Closure Plan — 2026-04-26

## Context

The first industrial pass added local artifact families, trust-boundary metadata, and JSON CLI surfaces. The remaining work is to turn those scaffolds into operational department workflows for mathematical finance and economics developers working across computational econometrics, computational statistics, machine learning, LLMs, large-scale Bayesian learning, computational physics, and applied mathematics.

This plan closes the 12 identified gaps with scaffold-sized, deterministic phases. Each phase must preserve the rule that generated records are review material until an explicit human approval workflow promotes selected content.

## Execution Loop

For every phase:
1. Plan the smallest local-first artifact or contract needed.
2. Execute the schema/CLI/backend change.
3. Test with fixtures and no live services.
4. Audit as if reviewing another developer's patch.
5. Tidy naming, exports, and reset-memo notes.
6. Continue without human intervention unless the work would require live credentials, network, destructive filesystem operations, or a policy decision.

## Phase 1 — Real Domain Knowledge Layer

Expand domain templates beyond simple checklists into domain packs with concept taxonomies, claim taxonomies, assumption classes, notation registries, theorem/equation roles, method families, and audit rubrics.

Deliverables:
- enriched domain-template schema;
- deterministic CLI list/show coverage;
- tests that every domain pack has operational taxonomy fields.

## Phase 2 — Deep Derivation Support

Make derivation worksheets versioned review records with notation entries, step dependencies, reviewer comments, and unresolved-gap links.

Deliverables:
- derivation notation/dependency/comment actions;
- version history and dependency graph fields;
- tests proving derivation content stays separate from accepted `technical_audit`.

## Phase 3 — Experiment and Reproducibility System

Extend experiment plans into reproducibility records.

Deliverables:
- experiment run records with environment, seed, dataset/model hashes, diagnostics, result summary, and acceptance status;
- deterministic local run recording command;
- tests for result persistence and export preservation.

## Phase 4 — Robust Parser and Source Benchmarks

Upgrade benchmark output from fixture existence/counts toward scored quality records.

Deliverables:
- benchmark scoring against expected JSON where present;
- quality metrics for title/authors/year/sections and limitation taxonomy;
- tests for pass/fail scoring with fixtures.

## Phase 5 — Paper-to-Code Traceability

Add coverage reports that summarize equation/theorem/algorithm/experiment links to code/tests.

Deliverables:
- traceability report artifact;
- link coverage by relationship type;
- tests using local link fixtures.

## Phase 6 — Citation Graph Intelligence

Add deterministic graph analytics scaffolds for intent, lineage, influence, competing families, trends, and open questions.

Deliverables:
- graph analytics fields in graph reports;
- placeholder intent/lineage records requiring review;
- tests with mocked graph data.

## Phase 7 — LLM-Assisted Synthesis With Governance

Gate synthesis through explicit provider/model policy records before any live model use.

Deliverables:
- model policy artifact;
- synthesis policy-check command;
- tests proving live model calls remain disabled by default.

## Phase 8 — Department Collaboration Model

Add local collaboration records for users, roles, permissions, assignments, comments, and append-only event history.

Deliverables:
- collaboration workspace artifact;
- user/role/comment/assignment actions;
- tests for append-only history and export visibility.

## Phase 9 — Production Storage and Indexing

Create a deterministic artifact index and migration report scaffold.

Deliverables:
- artifact index over summaries, links, industrial artifacts, and docs;
- schema-version inventory and migration-needed flags;
- tests for index counts and JSON contract stability.

## Phase 10 — Service/UI/MCP Layer

Expose backend tool contracts for dashboard/MCP/UI consumers without introducing a server dependency.

Deliverables:
- tool contract export listing commands, inputs, outputs, and trust boundary notes;
- dashboard summary contract;
- tests for stable contract keys.

## Phase 11 — Security, Compliance, and Operations

Add local security/compliance/ops records.

Deliverables:
- operations policy artifact with auth/secrets/provider/license/monitoring placeholders;
- offline-safe default;
- tests confirming no provider/network authorization by default.

## Phase 12 — Department SOPs

Codify department operating procedures for paper approval, derivation review, experiment evidence, benchmark gates, escalation, and onboarding.

Deliverables:
- SOP artifact generated from current policies;
- review gates mapped to artifact families;
- tests proving SOP sections are present and require human review.

## Independent Audit of This Plan

Audit findings:
- The phases are still broad, so each implementation must remain a contract or scaffold, not a production rewrite.
- Domain packs must not claim mathematical correctness; they define review prompts and required evidence only.
- Reproducibility records must support evidence capture without running experiments.
- Indexing and UI/MCP readiness must remain local and deterministic until storage/service requirements are explicit.
- LLM policy must be introduced before any future live synthesis provider call.
- Collaboration artifacts must avoid pretending local JSON is a concurrency-safe multi-user system.
- Security/compliance records are placeholders until department policy owners approve concrete controls.

Mitigations:
- Every new artifact uses the shared industrial artifact contract.
- Every generated record defaults to `requires_human_review`.
- Tests use local fixtures only.
- Exports include new artifact families for downstream inspection.
- Reset memo records validation, residual risk, and next safe step.
