# Industrial Release Gap Closure Plan - 2026-04-27

## Purpose

This document is an explicit handoff plan for moving `research-assistant` from
a limited individual local-install pilot toward an honest industrial release for
a mathematical finance/economics research group.

The current project is **not** industrial-release-ready. The latest individual
release pass validated a private local pilot workflow, improved release scripts,
rebuilt a wheel, and recorded a limited pilot decision. Industrial release means
something stronger: repeatable external validation, production-grade storage and
service contracts, collaboration controls, parser/scientific benchmarks,
security and operations review, scalable corpus handling, and department-owned
SOPs.

This plan is written for another agent to audit first and then execute phase by
phase. It intentionally separates:

- **M0 contracts**: architecture, schemas, policies, acceptance gates, test
  contracts, and stop conditions;
- **M1 local deterministic implementation**: local backends, CLI/API behavior,
  fixtures, bounded tests, and no live services;
- **M2 governed integration**: real storage/auth/UI/orchestration/provider
  integrations after ADR and policy approval;
- **M3 production release**: deployment, monitoring, incident response,
  security review, and department signoff.

An agent may complete M0 and safe M1 work autonomously. It must mark M2/M3 items
as blocked when they require external infrastructure, credentials, policy owner
approval, security review, real users, or production deployment decisions.

## Current Baseline

Latest known validation commits:

- `929bd41 Validate final individual release pilot`
- `277665b Record final validation checkpoint`

Individual pilot status:

- version: `0.1.0`;
- decision: limited pilot release candidate;
- artifact: `research_assistant-0.1.0-py3-none-any.whl`;
- artifact SHA256:
  `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`;
- validated platform: Linux/WSL2 `x86_64`, Python `3.11.15`;
- no tag created;
- no artifact published;
- real colleague onboarding, macOS validation, and external minimal parser-tool
  validation remain incomplete.

Existing industrial foundations:

- local industrial artifact families;
- artifact validation and readiness reports;
- derivation worksheets;
- experiment plans and run evidence;
- benchmark manifests/runs;
- graph intelligence reports;
- traceability reports;
- model-provider policy records;
- collaboration scaffolds;
- artifact indices;
- service/tool contracts;
- operations/SOP scaffolds;
- bounded validation scripts.

Important existing docs and plans:

- `docs/plans/industrial_full_scale_department_platform_plan_2026-04-27.md`
- `docs/plans/industrial_scale_implementation_plan_2026-04-27.md`
- `docs/plans/industrial_gap_closure_plan_2026-04-26.md`
- `docs/plans/individual_release_final_validation_publication_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`

## Non-Negotiable Industrial Release Principles

- Do not call this an industrial release until production scope, owner, and
  acceptance gates are explicit.
- Preserve the trust boundary: generated text, parser output, derivation
  worksheets, benchmark results, traceability links, readiness reports, and LLM
  outputs are review material until a human approval workflow accepts them.
- Do not enable live LLM/provider workflows by default.
- Do not introduce network, credentials, Docker, GUI, or external service
  requirements into deterministic tests.
- Do not store secrets in plain local config.
- Do not commit private papers, local corpora, backup archives, generated
  workspaces, `.codex`, `.claude`, `build/`, or `dist/`.
- Use `timeout` for validation scripts.
- Every release claim must be backed by a recorded validation environment.
- If a phase requires department policy approval, credentials, production auth,
  deployment, or security review, mark it `blocked_for_governed_integration`.

## Required Audit Before Execution

Before executing this plan, the next agent must audit it from four perspectives:

- **Release manager:** Are acceptance criteria measurable? Are pilot,
  departmental beta, and production release clearly separated?
- **Security/ops:** Are secrets, access control, backups, logs, incident
  response, and compliance requirements explicit?
- **Research trust boundary:** Could any workflow falsely imply mathematical
  approval, parser accuracy, experiment reproducibility, or code correctness?
- **Engineering:** Are phases ordered so storage/contracts precede UI,
  orchestration, collaboration, and live providers?

If the audit finds gaps, update this plan first. Record the audit outcome in
`docs/plans/reset_memo_2026-04-26.md`.

## Audit Amendment - Autonomous Execution Boundary

Independent audit before execution found that this plan is directionally
complete, but it would be unsafe to interpret "execute every phase" as
"complete production implementation" in a no-human-intervention local agent
run. The following work requires M2/M3 governed integration and must be marked
blocked unless explicit external approval and infrastructure are available:

- real colleague and platform validation;
- publication to a release host and tag pushing;
- production storage selection and migration approval;
- production service deployment;
- production identity, SSO, RBAC, and audit-policy ownership;
- browser UI deployment for shared users;
- live LLM/provider credentials and provider policy approval;
- security/compliance signoff;
- real corpus handling where private data may be present;
- department SOP approval or waiver.

For this autonomous execution pass, "execute the phase" means:

- create or update the M0 contract and acceptance gate;
- implement safe M1 local deterministic checks where possible;
- expose a machine-readable readiness/gate report;
- add tests proving incomplete M2/M3 gates remain blocked;
- update the reset memo honestly.

An agent must not implement fake production integrations, fake approvals, fake
external validation records, or fake release tags.

## Execution Loop

For every phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with the phase start.
2. State whether the phase is M0, M1, M2, or M3.
3. Implement the smallest safe contract or behavior.
4. Add focused tests before broad tests.
5. Run bounded validation with `timeout`.
6. Audit as another developer for false approval, data loss, privacy leakage,
   security holes, stale docs, and operational ambiguity.
7. Tidy docs, scripts, and generated files.
8. Update the reset memo with tests, residual risks, and next safe step.
9. Commit coherent changes after each phase group.

Because `docs/plans/` is ignored, force-stage intentional plan/reset changes
with `git add -f`.

## Phase 0 - Industrial Release Definition And Gate Taxonomy

### Motivation

The phrase "industrial release" can mean several different things: a hardened
single-user desktop release, a departmental beta with shared services, or a
production platform with security and operations signoff. Without a taxonomy,
future agents may overclaim readiness or implement infrastructure without a
release owner.

### Implementation Instructions

- Add `docs/release/industrial_release_definition.md`.
- Define release levels:
  - `individual_pilot`;
  - `departmental_beta`;
  - `industrial_production`.
- For each level, define:
  - users and deployment model;
  - storage backend;
  - authentication/authorization;
  - collaboration model;
  - parser/scientific validation bar;
  - LLM/provider policy;
  - security/ops bar;
  - support owner;
  - rollback/incident expectations.
- Add a machine-readable gate file, for example
  `docs/release/industrial_release_gates.json`, with required gates and current
  status.
- Add a CLI/report command or extend an existing readiness command to summarize
  the industrial release level and gate status.

### Tests

- Test the gate JSON schema.
- Test that release level statuses can be loaded and rendered.
- Test that missing mandatory gates produce `blocked`.

### Usefulness Verification

- A release manager can answer: "What are we allowed to release today?" without
  reading implementation files.

### Acceptance Criteria

- The current state is clearly recorded as `individual_pilot`.
- `departmental_beta` and `industrial_production` remain blocked until their
  gates are satisfied.

## Phase 1 - External Validation Program

### Motivation

Industrial release requires validation beyond a single local machine. The
individual pilot still lacks real colleague onboarding, macOS validation,
minimal parser-tool validation, and real or sanitized corpus rehearsal.

### Implementation Instructions

- Add `docs/release/external_validation_protocol.md`.
- Define non-private validation metadata to collect:
  - platform and architecture;
  - Python version;
  - install method;
  - optional parser tools;
  - clean-install result;
  - demo result;
  - backup/restore result;
  - release-report status;
  - time to first demo;
  - blockers/confusions.
- Add validation templates:
  - colleague onboarding;
  - macOS;
  - Linux native;
  - Windows through WSL;
  - minimal parser-tool environment;
  - real/sanitized corpus rehearsal.
- Add a local aggregation command or script that reads sanitized validation
  records and produces a status report.
- Ensure validation records exclude private PDFs, titles, local paths, backup
  archives, credentials, and provider keys.

### Tests

- Fixture validation records for passing and failing environments.
- Aggregation tests showing `blocked`, `warnings`, and `passed` status.
- Privacy tests that reject records containing obvious private path patterns or
  forbidden fields.

### Usefulness Verification

- A release manager can see which external validations are complete and which
  platforms are still unvalidated.

### Acceptance Criteria

- At least one real colleague onboarding record is required for
  `departmental_beta`.
- macOS and WSL validations are explicit.
- Missing external validation blocks broad release claims.

## Phase 2 - Release Artifact Publication And Tagging Workflow

### Motivation

The project can build a wheel, but industrial release needs a repeatable
publication workflow with hashes, provenance, release notes, tag policy, and
rollback instructions.

### Implementation Instructions

- Add `docs/release/publication_runbook.md`.
- Define:
  - artifact build command;
  - manifest/hash verification;
  - release notes checklist;
  - tag creation policy;
  - artifact upload policy;
  - rollback/unpublish process;
  - who approves release publication.
- Add a `release-publication-check` command or script that verifies:
  - version consistency;
  - clean Git status except ignored generated outputs;
  - artifact manifest exists;
  - release notes include matching hash;
  - final gate validation is recorded in reset memo or release record;
  - no forbidden files are staged.
- Keep actual tag creation and upload manual unless explicitly approved.

### Tests

- Passing and failing publication-check fixtures.
- Hash mismatch test.
- Missing release notes test.
- Dirty worktree test.

### Usefulness Verification

- A maintainer can reproduce the release artifact and know whether it is safe to
  tag.

### Acceptance Criteria

- Publication is blocked unless artifact hash, version, notes, validation, and
  approval records align.

## Phase 3 - Production Storage And Migration Strategy

### Motivation

Local JSON is useful for individual pilots but insufficient for an industrial
departmental release. Industrial use needs transactionality, migration control,
 queryability, backup/restore, and corruption recovery.

### Implementation Instructions

- Define an `ArtifactRepository` interface with methods for:
  - `put`;
  - `get`;
  - `list`;
  - `query`;
  - `version`;
  - `migrate`;
  - `validate`;
  - `backup`;
  - `restore`.
- Keep local JSON as `LocalJsonArtifactRepository`.
- Add SQLite as the first M1 repository backend.
- Define migration tables and schema version records.
- Add import/export between local JSON and SQLite.
- Add repository-selection config with offline-safe defaults.
- Add dry-run migration and rollback reports.
- Add snapshot backup and restore for SQLite.

### Tests

- Repository contract tests shared by JSON and SQLite backends.
- Migration tests from current fixture workspaces.
- Corrupt-record tests.
- SQLite transaction tests for concurrent writes.
- Backup/restore round-trip tests.

### Usefulness Verification

- Load 1,000 synthetic papers/artifacts into SQLite and demonstrate faster or
  more reliable lookup than ad hoc file walking.

### Acceptance Criteria

- Existing CLI workflows can run against JSON and SQLite.
- Migrations never silently drop invalid artifacts.
- Restore is tested before non-dry-run migration is allowed.

## Phase 4 - Service/API Layer Contract

### Motivation

Industrial UI, orchestration, and collaboration require stable service
contracts. Jumping directly from CLI/local files to a web UI would create a
fragile platform.

### Implementation Instructions

- Add API contract docs under `docs/api/industrial_service_contract.md`.
- Define endpoints or command contracts for:
  - papers;
  - artifacts;
  - reviews;
  - assignments;
  - comments;
  - derivations;
  - experiments;
  - traceability;
  - benchmarks;
  - search;
  - readiness;
  - governance/policies.
- Add typed request/response schemas.
- Add a local in-process service facade before any network server.
- Add error taxonomy with `blocked`, `warnings`, `conflict`, `unauthorized`,
  `not_found`, and `validation_error`.
- Keep generated/proposed content visibly separate from approved records.

### Tests

- Contract tests for every request/response schema.
- Error taxonomy tests.
- Trust-boundary tests proving proposal fields do not mutate accepted audit
  fields.

### Usefulness Verification

- A future UI/MCP/backend agent can build against stable JSON contracts without
  reading CLI internals.

### Acceptance Criteria

- Service contracts are stable, versioned, and covered by tests.

## Phase 5 - Identity, RBAC, And Collaboration Workflow

### Motivation

Industrial departmental work requires multiple users, review assignment,
permissions, comments, approvals, and append-only audit history. The current
collaboration artifacts are scaffolds, not production collaboration.

### Implementation Instructions

- Add user, role, permission, assignment, comment, approval-request, and event
  schemas.
- Define permissions for:
  - read;
  - write;
  - assign;
  - comment;
  - approve;
  - export;
  - administer;
  - provider-policy changes.
- Add append-only event log records for all state transitions.
- Add optimistic concurrency controls.
- Add local single-user mode for M1.
- Mark SSO/production identity as M2/M3 blocked until an identity ADR is
  approved.
- Add CLI/API workflows for assignment, comments, review requests, and approval
  requests.

### Tests

- RBAC allow/deny tests.
- Append-only event-history tests.
- Concurrent edit conflict tests.
- Three-reviewer workflow tests.
- Export privacy tests.

### Usefulness Verification

- Simulate owner, derivation reviewer, experiment reviewer, and steward working
  through one paper without manual JSON edits.

### Acceptance Criteria

- Unauthorized approval is impossible through public commands.
- Event history is immutable through public commands.
- Real SSO remains blocked until governed integration.

## Phase 6 - Parser And Source Benchmark Certification

### Motivation

Industrial users need measured parser/source extraction quality, not only
availability diagnostics. Parser failures can corrupt downstream derivations,
experiments, and search.

### Implementation Instructions

- Define gold-standard benchmark schemas for:
  - title;
  - authors;
  - year;
  - abstract;
  - sections;
  - equations;
  - theorem/proof blocks;
  - citations/references;
  - labels;
  - macros;
  - figures/tables.
- Add benchmark fixture families:
  - synthetic;
  - arXiv source;
  - PDF-only;
  - degraded/scanned;
  - dense equations;
  - long author lists;
  - bibliography edge cases.
- Add metrics:
  - exact match;
  - normalized match;
  - precision/recall/F1;
  - equation-label recovery;
  - theorem recovery;
  - citation/reference consistency;
  - parser disagreement.
- Add trend history and regression gates.

### Tests

- Golden fixture tests.
- Failing parser regression tests.
- Metric calculation tests.
- Trend-history tests.

### Usefulness Verification

- Demonstrate a parser regression that lowers equation recovery and is blocked
  by the benchmark gate.

### Acceptance Criteria

- Parser quality claims are backed by benchmark results by paper family.
- Benchmark failures identify concrete fields and examples.

## Phase 7 - Mathematical Review And Derivation Approval Workflow

### Motivation

Industrial mathematical research needs traceable assumptions, notation,
derivation steps, proof gaps, reviewer comments, and explicit approval. Current
derivation worksheets are review artifacts, not an approval system.

### Implementation Instructions

- Extend derivation records with:
  - assumption IDs;
  - notation registry references;
  - claim dependencies;
  - proof-step dependencies;
  - unresolved gaps;
  - reviewer comments;
  - approval requests;
  - revision history.
- Add commands/API endpoints for derivation review and approval request.
- Require reviewer identity and permission for approval.
- Keep accepted mathematical conclusions separate from generated worksheets
  until a human approval command promotes them.
- Add audit reports for unresolved gaps and stale approvals after source
  changes.

### Tests

- Valid/invalid dependency tests.
- Approval-permission tests.
- Stale approval after source update tests.
- Trust-boundary tests preventing auto-approval.

### Usefulness Verification

- Review a fixture theorem/derivation with one deliberate missing assumption and
  show the readiness gate blocks approval.

### Acceptance Criteria

- No derivation can be approved with unresolved required gaps.
- Generated derivation content never becomes accepted audit fact automatically.

## Phase 8 - Experiment Reproducibility And Execution Evidence

### Motivation

Industrial research workflows need reproducible evidence for computational
claims: environments, datasets, seeds, model hashes, diagnostics, and result
summaries. Current experiment records are evidence scaffolds.

### Implementation Instructions

- Define experiment execution records for:
  - environment;
  - dependencies;
  - hardware;
  - random seeds;
  - dataset hashes;
  - model/code hashes;
  - command line;
  - runtime;
  - diagnostics;
  - result summary;
  - acceptance status.
- Add local fixture runner for deterministic smoke experiments.
- Add optional external runner contracts for M2/M3.
- Add reproducibility score and blocker taxonomy.
- Add result comparison against expected fixture outputs.

### Tests

- Deterministic fixture run tests.
- Missing evidence blocker tests.
- Hash mismatch tests.
- Result comparison tests.

### Usefulness Verification

- Re-run a fixture experiment and show the same seed/hash/result summary.

### Acceptance Criteria

- Readiness gates distinguish evidence completeness from scientific approval.
- External execution remains blocked until infrastructure is approved.

## Phase 9 - Paper-To-Code Traceability Verification

### Motivation

Industrial users need to know which equations/theorems/algorithms are linked to
code and tests. Path existence is not enough; the platform needs reviewable
verification status and drift detection.

### Implementation Instructions

- Extend traceability links with:
  - source artifact ID;
  - target file path;
  - target symbol or test name;
  - verification status;
  - reviewer;
  - last checked commit/hash;
  - limitations.
- Add code/test target discovery for local repositories.
- Add stale-link detection when target files or hashes change.
- Add review workflow for "verified", "needs update", and "not applicable".
- Do not claim semantic equivalence automatically.

### Tests

- Existing/missing target tests.
- Stale hash tests.
- Verification status transition tests.
- Trust-boundary tests preventing semantic-certification claims.

### Usefulness Verification

- For a fixture paper, show all equations with missing code/tests and block
  readiness until reviewed.

### Acceptance Criteria

- Traceability reports identify missing/stale targets without claiming proof of
  correctness.

## Phase 10 - Search, Indexing, And Knowledge Graph

### Motivation

Industrial research teams need to query across papers, claims, assumptions,
methods, experiments, citations, code links, and review states.

### Implementation Instructions

- Add a search/index abstraction.
- Implement local SQLite FTS as M1 backend.
- Index:
  - paper metadata;
  - abstracts;
  - source sections;
  - equations;
  - theorem blocks;
  - citations;
  - derivation steps;
  - assumptions;
  - experiment records;
  - traceability links;
  - comments/reviews.
- Add graph edge types for citations, method usage, assumptions, equations,
  experiments, implementation links, and approvals.
- Add stale-index detection and rebuild commands.
- Keep semantic/vector search behind disabled policy gates.

### Tests

- Golden query tests.
- Ranking regression tests.
- Graph consistency tests.
- Stale-index tests.

### Usefulness Verification

- Answer fixture questions like: "Which HMC papers have target-density
  assumptions but missing simulation recovery evidence?"

### Acceptance Criteria

- Search results cite source artifacts.
- Graph edges never imply approval by mere existence.

## Phase 11 - LLM/Provider Governance

### Motivation

Industrial LLM usage requires provider approval, secrets management, prompt and
response audit logs, cost controls, data-leakage safeguards, and opt-in policy.
The individual pilot intentionally disables live providers.

### Implementation Instructions

- Add `docs/governance/llm_provider_policy.md`.
- Define provider approval workflow and data classification rules.
- Add secret-reference design; do not store secrets directly in workspace JSON.
- Add live-call policy gate requiring:
  - explicit provider;
  - allowed data class;
  - approved prompt template;
  - cost budget;
  - audit logging;
  - redaction rules.
- Add dry-run provider simulation for deterministic tests.
- Add model output provenance and review status to generated artifacts.

### Tests

- Live calls blocked by default.
- Secrets-in-config rejection tests.
- Policy allow/deny tests.
- Dry-run provider simulation tests.
- Audit-log schema tests.

### Usefulness Verification

- Demonstrate that an unapproved provider call is blocked with an actionable
  policy issue.

### Acceptance Criteria

- No live provider call can occur without explicit policy approval and audit
  record.

## Phase 12 - Security, Compliance, And Operations

### Motivation

Industrial release requires operational discipline: backups, retention, logs,
access control, incident response, vulnerability handling, and compliance
review.

### Implementation Instructions

- Add `docs/ops/industrial_operations_runbook.md`.
- Add `docs/security/security_review_checklist.md`.
- Define:
  - data classification;
  - backup retention;
  - restore drills;
  - access logging;
  - audit-log retention;
  - incident response;
  - dependency update policy;
  - vulnerability disclosure;
  - deployment rollback;
  - support escalation.
- Add local operations report command that checks required docs/policies and
  latest restore drill record.
- Add forbidden-file staging checks for private data and archives.

### Tests

- Operations report tests.
- Forbidden-file checker tests.
- Backup/restore drill fixture tests.
- Missing policy blocker tests.

### Usefulness Verification

- A maintainer can run one command and know whether ops docs and latest drills
  are current.

### Acceptance Criteria

- Industrial release is blocked without security/ops checklist completion.

## Phase 13 - Scalability And Real Corpus Performance

### Motivation

The individual pilot passed a synthetic 1000-record smoke. Industrial release
needs real or sanitized corpus measurements, larger synthetic stress tests,
indexing metrics, backup metrics, and long-running workflow behavior.

### Implementation Instructions

- Add `docs/release/scalability_validation_protocol.md`.
- Define benchmark corpus tiers:
  - 1,000 synthetic;
  - 10,000 synthetic;
  - sanitized real small;
  - sanitized real medium;
  - optional large department corpus.
- Add performance command options for:
  - indexing;
  - search;
  - backup;
  - restore dry-run;
  - export;
  - validation;
  - parser benchmark smoke.
- Record metrics as local JSON reports, excluding private content.
- Add timeout and warning thresholds by tier.

### Tests

- Small deterministic performance report tests.
- Timeout diagnostic tests.
- Threshold classification tests.

### Usefulness Verification

- Demonstrate a 10,000-record synthetic index/search/backup rehearsal within
  documented thresholds or record the blocker honestly.

### Acceptance Criteria

- Industrial release notes state measured corpus sizes and limits.
- Real corpus data is never committed.

## Phase 14 - UI And Workflow Workbench

### Motivation

Industrial reviewers should not need to run dozens of CLI commands. A workbench
is needed for queue triage, evidence review, derivation gaps, experiments,
traceability, parser benchmarks, readiness blockers, and governance status.

### Implementation Instructions

- Do not start UI until service/API contracts and storage contracts are stable.
- Add UI architecture ADR.
- Build an M1 local web UI or static dashboard first, backed by deterministic
  exports or in-process service contracts.
- Required views:
  - paper queue;
  - paper detail;
  - source evidence;
  - derivation worksheet;
  - experiment evidence;
  - traceability;
  - parser benchmark;
  - readiness blockers;
  - governance/policies;
  - admin/status.
- Generated/proposed content must be visually distinct from approved content.

### Tests

- Contract tests for UI data.
- Component/page tests.
- Playwright flows for triage, assignment, review, and readiness inspection.
- Accessibility checks.

### Usefulness Verification

- A reviewer can complete a triage/review workflow without editing JSON or using
  CLI-only paths.

### Acceptance Criteria

- UI does not imply approval for generated content.
- Core review workflow is usable through the workbench.

## Phase 15 - Department SOPs And Approval Gates

### Motivation

Industrial release is partly organizational. The platform must reflect
department-approved procedures for paper intake, derivation review, experiment
evidence, parser gates, code traceability, LLM use, escalation, support, and
release governance.

### Implementation Instructions

- Add `docs/sop/industrial_research_sop.md`.
- Define SOP sections:
  - paper intake;
  - source/PDF validation;
  - derivation review;
  - experiment evidence;
  - parser benchmark gate;
  - traceability review;
  - LLM/provider use;
  - readiness approval;
  - support/escalation;
  - release approval.
- Add SOP status records with owner, reviewers, approval date, expiration, and
  review cadence.
- Add readiness blockers when SOPs are missing, expired, or unapproved.
- Keep SOP approval separate from code implementation.

### Tests

- SOP schema tests.
- Expired/missing SOP blocker tests.
- Readiness report integration tests.

### Usefulness Verification

- A steward can see exactly which SOPs block departmental beta or production.

### Acceptance Criteria

- Departmental beta is blocked unless required SOPs are approved or explicitly
  waived by owner.

## Phase 16 - Industrial Release Candidate Gate

### Motivation

After the above phases, a final industrial release gate must aggregate all
technical, validation, operational, and governance evidence. Without this,
"industrial-ready" becomes a collection of stale partial checks.

### Implementation Instructions

- Add `scripts/run_industrial_release_gate.sh`.
- The gate should run only bounded deterministic checks by default:
  - fast tests;
  - bounded tests;
  - industrial validation tests;
  - repository migration fixture tests;
  - parser benchmark fixture tests;
  - search/index fixture tests;
  - security/ops report;
  - release gate report.
- Add optional external validation record checks.
- Produce a machine-readable industrial release report with:
  - release level;
  - gate statuses;
  - blockers;
  - warnings;
  - artifact hashes;
  - platform validations;
  - corpus validations;
  - security/ops status;
  - SOP status;
  - tag/publication status.
- Refuse `industrial_production` if any M2/M3 gate is incomplete.

### Tests

- Gate report tests for blocked, beta-ready, and production-blocked states.
- Script existence/executable tests.
- Fixture validation tests.

### Usefulness Verification

- A release manager can run one command and know whether the project is
  individual pilot, departmental beta, or production-blocked.

### Acceptance Criteria

- Industrial production release is impossible to claim without all required
  gates passing or documented owner waivers.

## Suggested Execution Order

1. Phase 0: release definition/gate taxonomy.
2. Phase 1: external validation records.
3. Phase 2: publication/tagging workflow.
4. Phase 3: repository/storage abstraction.
5. Phase 4: service/API contracts.
6. Phase 5: identity/RBAC/collaboration.
7. Phase 6: parser/source benchmarks.
8. Phase 7: derivation approval workflow.
9. Phase 8: experiment reproducibility.
10. Phase 9: paper-to-code verification.
11. Phase 10: search/index/knowledge graph.
12. Phase 11: LLM governance.
13. Phase 12: security/ops.
14. Phase 13: scalability/real corpus performance.
15. Phase 14: UI/workbench.
16. Phase 15: SOP gates.
17. Phase 16: final industrial release gate.

## Final Definition Of Done

An industrial release can be considered only when:

- external validation records exist for target platforms and users;
- artifact publication and tag workflow is approved and repeatable;
- production storage/migration/backup strategy is implemented and tested;
- identity, RBAC, collaboration, and audit history are enforceable;
- parser/source quality is benchmarked by paper family;
- mathematical derivation approval is explicit and permissioned;
- experiment reproducibility evidence is recorded and gated;
- paper-to-code traceability detects missing/stale targets;
- search/index/graph queries are tested and explainable;
- live provider use is governed, audited, and disabled by default;
- security/ops runbooks and restore drills are current;
- scalability limits are measured on synthetic and sanitized real corpora;
- UI/workbench supports core reviewer workflows;
- department SOPs are approved or explicitly waived;
- the industrial release gate reports no blockers for the requested release
  level.

If any item is incomplete, the release must remain at the highest lower level
whose gates are satisfied, such as `individual_pilot` or `departmental_beta`.
