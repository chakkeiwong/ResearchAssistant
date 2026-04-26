# Industrial Research Platform Architecture

## Purpose

This document defines the subsystem boundaries for evolving `research-assistant` into a departmental industrial research platform. It exists to prevent the full-scale implementation plan from turning into disconnected feature patches.

## Trust Boundary

The platform may automate extraction, indexing, validation, derivation worksheets, experiment records, synthesis proposals, traceability reports, and readiness gates. It must not silently promote generated content into accepted mathematical conclusions. Human approval workflows are required for accepted `technical_audit` conclusions, production policy changes, provider access, and release gates.

## Subsystems

### Artifact Contracts

Owns schema versions, stable IDs, provenance, review status, limitations, validation, migration reports, and generated-vs-approved boundaries.

Primary current files:
- `src/research_assistant/schemas/artifact.py`
- `src/research_assistant/industrial/platform.py`

### Storage

Owns repository abstractions, local JSON compatibility, future SQLite storage, migrations, backup/restore, transactional behavior, and corrupt-record recovery.

ADR required before governed integration:
- `docs/architecture/adr/0001-storage-backend.md`

### Ingestion

Owns raw PDF/source ingestion, source priority, duplicate detection, batch manifests, degraded-source triage, and parser provenance.

### Parser Benchmarks

Owns gold fixtures, extraction metrics, parser regression gates, benchmark history, and benchmark dashboards.

### Derivations

Owns notation registries, assumption graphs, derivation steps, proof gaps, source links, reviewer comments, and derivation approval gates.

### Experiments

Owns experiment packages, runners, environment capture, data/model hashes, result diagnostics, reproducibility bundles, and experiment evidence approval.

### Traceability

Owns equation/theorem/algorithm/claim-to-code/test/experiment links, code indexing, stale-link detection, coverage reports, and traceability approval.

### Search And Knowledge Graph

Owns full-text search, structured filters, graph edges, stale-index detection, graph consistency validation, and explainable query results.

ADR required before governed integration:
- `docs/architecture/adr/0004-search-and-indexing.md`

### LLM Governance

Owns provider policies, prompt registry, data classification checks, evaluations, audit logs, cost budgets, live-call controls, and model-version pinning.

ADR required before governed integration:
- `docs/architecture/adr/0005-llm-provider-policy.md`

### Collaboration And Identity

Owns users, roles, permissions, assignments, comments, append-only events, optimistic concurrency, and approval requests.

ADR required before governed integration:
- `docs/architecture/adr/0002-identity-and-rbac.md`

### UI And API

Owns reviewer-facing workflows, dashboard contracts, API contracts, visual distinction between generated and approved content, accessibility, and browser tests.

ADR required before governed integration:
- `docs/architecture/adr/0006-deployment-model.md`

### Orchestration

Owns job queues, bounded execution, heartbeats, retries, cancellation, logs, scheduler behavior, and crash recovery.

ADR required before governed integration:
- `docs/architecture/adr/0003-background-jobs.md`

### Security, Compliance, And Operations

Owns data classification, secret detection, export policy, license tracking, retention, audit-log integrity, incident response, monitoring, and release gates.

### Domain Expert Packs

Owns domain-specific review rubrics, notation, assumptions, method families, diagnostics, benchmark examples, canonical references, owners, and review cadence.

### SOP Enforcement

Owns approval gates, override policy, evidence requirements, event history, and readiness integration.

## Execution Milestones

- M0 contract: architecture, ADRs, schemas, phase contracts, tests, usefulness metrics, and stop conditions.
- M1 local deterministic implementation: offline behavior with local fixtures and bounded validation.
- M2 governed integration: real storage/auth/UI/orchestration/provider integrations after accepted ADRs and policy records.
- M3 production deployment: monitoring, security review, runbooks, rollback, and department approval.

## Stop Conditions

Implementation must stop and record `blocked_for_governed_integration` when a phase requires:
- live credentials or provider access;
- SSO, production identity, or department RBAC policy;
- external network services;
- production deployment or server operations;
- department security/compliance approval;
- destructive migration without backup/restore and rollback plan.

## Current Safe Execution Scope

The current safe scope is to implement M0 across all phases and M1 only for deterministic local functionality. Production claims must wait for M2/M3.
