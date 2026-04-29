# Reset Memo — 2026-04-26

## Why this memo exists

This memo captures the current handoff point for turning `research-assistant` from a structured-source-first paper inspection tool into a mostly autonomous literature-analysis workflow. It records the completed checkpoints, current working-tree state, the durable implementation plan, and the next safe execution step.

## Current state

Completed and committed recently:
- `6ec0b69 Surface degraded discovery in CLI downloads.`
  - `ra discover` and `ra download-paper` now surface degradation-aware discovery payloads.
  - `download-paper` distinguishes unavailable discovery, empty discovery, and closed-access results.
- `c93eb3c Expose citation neighborhood diagnostics.`
  - `citation-neighborhood` now returns `status_reason` and endpoint diagnostics.
  - Diagnostics include unavailable endpoints, available-empty endpoints, and failure reasons.

Validation completed:
- Full deterministic suite after discovery/download checkpoint: `113 passed in 263.14s`.
- Focused citation/CLI diagnostics tests: `29 passed in 140.85s`.
- Full deterministic suite after citation diagnostics: `113 passed in 404.04s`.
- Final focused integration/discovery tests after source-section UX and scenario updates: `29 passed in 190.69s`.

## Current uncommitted code state

There are two tracked files with uncommitted changes:
- `src/research_assistant/cli.py`
  - `source-section` now fails clearly unless `--title` or `--label` is supplied.
- `tests/integration/test_cli_commands.py`
  - the local ingest audit scenario now asserts citation `status_reason` and diagnostics;
  - the structured-source CLI test now covers missing `source-section` selector behavior.

These changes have focused validation but have not yet been committed.

## Durable project plan

The project plan has been written to:
- `docs/plans/literature_analysis_autonomous_cycle_plan_2026-04-26.md`

The plan phases are:
1. editable, source-linked `technical_audit` notes;
2. evidence-context retrieval commands;
3. cached citation graph generation and multi-hop expansion;
4. literature-analysis proposals stored separately from accepted audit facts;
5. autonomous audit/implement cycle script;
6. broad end-to-end degraded workflow scenario.

## Next safe step

1. Decide whether to commit the current two-file UX/scenario update.
2. If continuing implementation, start Phase 1 of the project plan:
   - add `ra audit-note show/set/append/link-section/link-equation`;
   - validate linked section/equation labels against structured source records;
   - keep machine evidence separate from accepted `technical_audit` conclusions.
3. Follow the phase loop:
   - write focused test first;
   - implement the smallest behavior;
   - run focused tests;
   - run `scripts/run_tests.sh` before checkpoint;
   - update this reset memo;
   - commit only when explicitly requested.

## Known constraints

- Source-derived evidence is review material, not a mathematical conclusion.
- Literature-analysis proposals must not auto-populate accepted `technical_audit` fields.
- Citation graph expansion should default to depth 1 and use local caching to avoid API fanout.
- Deterministic tests must not require live network, TeX, Docker, or MCP.


## Update — autonomous literature-analysis phases executed

Implemented after this memo was created:
- Phase 1: editable `audit-note` CLI workflow for show/set/append/link-section/link-equation.
- Phase 2: `evidence-context` CLI workflow for source labels and citation keys.
- Phase 3: local citation graph cache with build/show/export commands under `local_research/graphs/citations/`.
- Phase 4: literature-audit proposal artifacts under `local_research/analysis/literature_audit/`, explicitly marked `requires_human_review` and kept separate from accepted `technical_audit` notes.
- Phase 5: `scripts/run_literature_audit_cycle.sh` for focused workflow checks plus the deterministic suite.
- Phase 6 scenario coverage: integration tests now exercise source-linked audit notes, evidence retrieval, citation graph artifacts, literature-audit proposals, review/export preservation, and degraded citation diagnostics.

Validation completed:
- Phase 1 focused tests: `26 passed in 137.20s`.
- Phase 2 focused tests: `5 passed in 0.11s`.
- Phase 1–3 focused workflow tests: `11 passed in 0.24s`.
- Phase 4 proposal tests: `2 passed in 0.23s`.
- Broad workflow tests: `39 passed in 197.22s`.
- Citation CLI regression tests: `32 passed in 199.58s`.
- Full deterministic suite after all workflow changes: `113 passed in 252.82s`.

Current checkpoint:
- Ready to commit and push the autonomous literature-analysis workflow implementation.
- The implementation preserves the trust boundary: generated proposals and source evidence remain review material, not accepted mathematical conclusions.


## Update — gap-closure phases started

Additional implementation after autonomous workflow baseline:
- Detailed gap-closure plan written to `docs/plans/literature_analysis_gap_closure_plan_2026-04-26.md`.
- Proposal approval added via `ra literature-audit-approve`; accepted proposal content records `proposal_provenance` in `technical_audit`.
- Audit notes now support theorem/citation links and removal from list fields.
- Citation graph build now supports guarded depth 2 expansion and graph diagnostics include node/edge counts.
- Graph node download proposals can be created with `ra graph-node-download-proposal`.
- Evidence context now reports macro usages for labeled blocks.
- `scripts/run_literature_audit_cycle.sh` now accepts an optional paper id and runs show/proposal smoke checks before the full suite.

Validation completed:
- Proposal approval focused test: `1 passed in 0.19s`.
- Richer audit links focused test: `1 passed in 0.25s`.
- Phase 1–3 focused tests: `2 passed in 0.28s`.
- Graph/inbox/evidence/cycle focused tests: `1 passed in 0.22s`.
- Focused gap-closure validation: `36 passed in 146.35s`.

Remaining before checkpoint:
- Full deterministic suite passed: `113 passed in 254.76s`.
- Audit final diff and commit if requested.


## Update — industrial-scale roadmap requested

New objective: evolve `research-assistant` toward an industrial departmental research platform for mathematical finance/economics developers working across computational econometrics, computational statistics, ML/LLMs, large-scale Bayesian learning, computational physics, and applied mathematics.

A detailed phased plan and independent audit has been written to:
- `docs/plans/industrial_math_finance_research_platform_plan_2026-04-26.md`

Execution policy for this stage:
- implement small scaffolds phase by phase;
- keep generated synthesis/proposals separate from accepted human audit conclusions;
- avoid live network requirements in deterministic tests;
- update this reset memo after the phase sequence;
- commit only after full validation.


## Update — industrial implementation recovery started

Crash recovery audit:
- Tracked worktree had no partial industrial implementation from the prior crashed agent.
- Only untracked local scratch state was `.codex`, an empty file.
- Existing committed baseline is the literature-analysis workflow ending at `bdd4f1b Close literature analysis workflow gaps.`

Plan correction made before coding:
- Added Phase 0 to `docs/plans/industrial_math_finance_research_platform_plan_2026-04-26.md`.
- Phase 0 defines shared artifact metadata, local paths, stable IDs, reset-memo checkpoint fields, and trust-boundary acceptance criteria before domain-specific phases proceed.

Current phase:
- Phase 0 in progress.

Files touched so far:
- `docs/plans/industrial_math_finance_research_platform_plan_2026-04-26.md`
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this implementation sequence.

Remaining risks:
- Scope is broad; implementation must stay scaffold-sized and deterministic.
- Generated artifacts must remain separate from accepted `technical_audit` unless an explicit human approval command exists.
- No live network, TeX, Docker, GUI, or external service should be required by deterministic tests.

Next safe step:
- Implement Phase 0 shared artifact/path helpers and then execute each plan phase with the cycle: plan for phase, execute, test, audit, tidy, update reset memo.


## Update — industrial phases 0-10 scaffolded

Current phase:
- Phases 0 through 10 implemented as local-first scaffolds.

Plan for working out the phases:
- For every phase, add the smallest schema/artifact surface, expose JSON CLI commands, run focused tests, audit for trust-boundary violations, tidy, and update this memo.
- Keep all generated outputs under local `local_research/` artifact families.
- Prefer deterministic source/fixture evidence; do not add live LLM, network, TeX, Docker, GUI, or service dependencies.

Independent developer audit performed after implementation:
- Checked that all new generated artifact families carry `schema_version`, `artifact_id`, `artifact_type`, `provenance`, `review_status`, `requires_human_review`, and `limitations`.
- Checked that derivation worksheets, experiment plans, graph intelligence reports, synthesis proposals, benchmark outputs, governance records, and job records do not auto-populate accepted `technical_audit`.
- Checked that `link-add` now uses stable IDs instead of Python hash-derived IDs and marks implementation relationships as requiring review.
- Checked that exports preserve paper-scoped industrial artifacts plus library-scoped benchmark manifests/runs.

Phase completion notes:
- Phase 0: added shared artifact helpers and canonical artifact paths.
- Phase 1: added typed domain templates and `ra domain-templates list/show`.
- Phase 2: added derivation worksheet artifacts and `ra derivation create/show/append`.
- Phase 3: added experiment checklist templates, experiment plans, and claim-to-experiment links.
- Phase 4: added citation graph intelligence reports with dedup diagnostics, intent placeholders, and cluster/trend scaffold.
- Phase 5: added local department review metadata for owner/steward/reviewers/workstream tags/history.
- Phase 6: added benchmark manifest and fixture runner scaffolds.
- Phase 7: added deterministic synthesis proposal artifacts and `ra synthesis propose/show`.
- Phase 8: extended implementation links for equation/theorem/algorithm/experiment relationships.
- Phase 9: added governance records with local artifact hashes, extraction quality metrics, and provider/model policy placeholders.
- Phase 10: added dashboard export and job status artifacts for future UI/MCP/background workers.

Files touched:
- `docs/plans/industrial_math_finance_research_platform_plan_2026-04-26.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `src/research_assistant/config.py`
- `src/research_assistant/cli.py`
- `src/research_assistant/adapters/workspace_exports.py`
- `src/research_assistant/schemas/artifact.py`
- `src/research_assistant/schemas/domain_templates.py`
- `src/research_assistant/schemas/link_record.py`
- `src/research_assistant/industrial/__init__.py`
- `src/research_assistant/industrial/platform.py`
- `tests/unit/test_schemas.py`
- `tests/integration/test_cli_commands.py`
- `tests/integration/test_industrial_platform_cli.py`

Tests run:
- Focused industrial suite: `8 passed in 0.16s`.
- Full deterministic suite via `scripts/run_tests.sh`: `118 passed in 5827.51s (1:37:07)`.
- Full deterministic suite rerun via `pytest -vv`: `118 passed in 6140.09s (1:42:20)`.

Remaining risks:
- These are intentionally scaffolds, not complete industrial review workflows.
- Benchmark runner currently checks fixture availability/count scaffolds, not full parser-vs-ground-truth scoring.
- Synthesis remains deterministic and local; live provider policy is explicitly disabled until a future governance decision.

Next safe step:
- Commit the industrial scaffold implementation, then record the final commit checkpoint.


## Update — industrial 12-gap closure started

New objective:
- Close the 12 remaining gaps toward a fully industrial departmental tool: real domain knowledge, deep derivations, reproducibility, parser/source benchmarks, paper-to-code traceability, citation intelligence, LLM governance, collaboration, indexing, service/UI/MCP contracts, security/compliance/ops, and department SOPs.

Plan written to:
- `docs/plans/industrial_gap_closure_plan_2026-04-26.md`

Current phase:
- Phase 1 planning started after commit `595c4e3 Add industrial research platform scaffolds`.

Execution policy:
- Follow the loop: plan phase, execute, test, audit, tidy, update reset memo.
- Keep outputs local-first under `local_research/`.
- Keep all generated content separate from accepted `technical_audit`.
- Avoid live network, credentials, provider calls, TeX/Docker requirements, GUI actions, or destructive filesystem operations.

Tests run:
- Not yet run for this 12-gap closure sequence.

Remaining risks:
- This pass must remain scaffold-sized; full production collaboration, storage, service, and security systems require later policy and architecture decisions.
- The plan adds operational contracts but not live services or real concurrent multi-user infrastructure.

Next safe step:
- Implement the 12 gap-closure phases as deterministic schemas, CLI/backend commands, exports, and focused tests.


## Update — industrial 12-gap closure scaffolded

Current phase:
- Phases 1 through 12 of `docs/plans/industrial_gap_closure_plan_2026-04-26.md` have been implemented as deterministic scaffolds.

Phase completion notes:
- Phase 1: domain templates now include concept taxonomies, claim taxonomies, assumption classes, notation registries, theorem/equation roles, method families, and audit rubrics.
- Phase 2: derivation worksheets now support notation entries, step dependencies, reviewer comments, and version history.
- Phase 3: experiment plans now support run records with environment, seed, dataset/model hashes, diagnostics, result summary, and acceptance status.
- Phase 4: benchmark runs now score expected JSON fixture fields and preserve extraction-quality limitations.
- Phase 5: traceability reports summarize equation/theorem/algorithm/experiment implementation-link coverage.
- Phase 6: graph reports can be enriched with deterministic analytics placeholders for lineage, influence, competing families, trends, and open questions.
- Phase 7: model-provider policy records block live model calls by default and expose synthesis policy checks.
- Phase 8: collaboration workspaces record users/roles/assignments/comments with append-only event history.
- Phase 9: artifact index records inventory counts, schema versions, and migration-needed flags.
- Phase 10: tool-contract export lists backend/CLI surfaces and trust-boundary notes for future UI/MCP consumers.
- Phase 11: operations policy artifacts define offline-safe security/compliance/ops placeholders.
- Phase 12: department SOP artifacts define draft paper approval, derivation review, experiment evidence, benchmark gate, escalation, and onboarding sections.

Independent developer audit performed:
- Verified every new artifact is local-first JSON and defaults to `requires_human_review`.
- Verified no command performs live provider/model calls or authorizes network usage.
- Verified generated records remain separate from accepted `technical_audit`.
- Verified exports include the new paper-scoped and library-scoped artifact families.
- Verified collaboration and service/MCP additions are explicitly scaffolds, not production multi-user/server infrastructure.

Files touched:
- `docs/plans/industrial_gap_closure_plan_2026-04-26.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `src/research_assistant/config.py`
- `src/research_assistant/cli.py`
- `src/research_assistant/adapters/workspace_exports.py`
- `src/research_assistant/industrial/platform.py`
- `src/research_assistant/schemas/domain_templates.py`
- `tests/unit/test_schemas.py`
- `tests/integration/test_cli_commands.py`
- `tests/integration/test_industrial_platform_cli.py`

Tests run:
- Focused 12-gap suite: `7 passed in 0.38s`.
- Focused 12-gap suite after CLI discoverability update: `7 passed in 0.40s`.
- Broad deterministic non-PDF subset: `29 passed in 0.75s`.
- Attempted full deterministic suite via `scripts/run_tests.sh`; it progressed through the quiet output to at least the later test blocks but the tool session did not return a final pytest summary and was stopped with a targeted `pkill -f "scripts/run_tests.sh"`.

Remaining risks:
- These are operational contracts and scaffolds, not full production services.
- Real code inspection, parser-vs-ground-truth scoring, live collaboration, service deployment, and approved security controls remain future implementation work.
- Full suite should be rerun at the next checkpoint because this attempt did not produce a final summary, though the previous industrial scaffold checkpoint passed `118` tests twice.

Next safe step:
- Commit the 12-gap scaffold implementation, noting that focused and broad deterministic validations passed while the full-suite attempt was interrupted without a final summary.


## Update — industrial scale implementation pass started

New objective:
- Turn the committed industrial scaffolds into a stricter local operational layer for departmental mathematical finance/economics research workflows.

Execution policy for this pass:
- Start by writing an explicit industrial-scale implementation plan and an independent developer audit of that plan.
- Execute phase by phase using the loop: plan phase, execute, test, audit, tidy, update reset memo.
- Use bounded validation only. Avoid unbounded `scripts/run_tests.sh`; run focused suites with `timeout` and record any timeout honestly.
- Keep all outputs local-first, deterministic, and fixture-driven.
- Preserve the trust boundary: generated validation, synthesis, derivation, graph, benchmark, and dashboard artifacts remain review material unless an explicit human approval workflow promotes them.

Current phase:
- Planning and audit.

Files touched so far:
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this implementation pass.

Remaining risks:
- The phrase "industrial scale" can invite accidental production claims. This pass must add enforceable local contracts, validators, and readiness reports without implying live multi-user infrastructure, live LLM/provider use, or production security certification.

Next safe step:
- Write `docs/plans/industrial_scale_implementation_plan_2026-04-27.md`, audit it, then implement bounded operational phases with focused tests.


## Update — industrial scale implementation pass completed

Plan and audit:
- Wrote `docs/plans/industrial_scale_implementation_plan_2026-04-27.md`.
- Included an independent developer audit in the plan before coding.
- Reconfirmed the bounded-validation policy: no unbounded full-suite run during this pass.

Phase completion notes:
- Phase 1: added industrial artifact validation over all industrial artifact families, including required base fields, schema version, provenance, limitations, human-review defaults, JSON readability, and accepted-audit boundary checks.
- Phase 2: upgraded artifact index output with validation summaries, schema-version inventory, migration-needed flags, and `artifact-index query` filters.
- Phase 3: upgraded benchmark runs with fixture metadata quality scores, pass threshold, missing-field diagnostics, and limitation taxonomy.
- Phase 4: upgraded traceability reports with local target path existence checks, code/test target classification, and missing-target blockers.
- Phase 5: added experiment run reproducibility evidence scoring over environment, seed, dataset/model hashes, diagnostics, result summary, and acceptance status.
- Phase 6: added derivation dependency validation for worksheet IDs, step dependencies, and reviewer comment targets.
- Phase 7: added `industrial-readiness build/show` to aggregate validation, policy, derivation, experiment, benchmark, traceability, governance, and SOP gates.
- Phase 8: expanded dashboard export with validation summary, latest readiness summary, blocker/warning counts, and next actions.
- Phase 9: added SOP gate reporting inside readiness.
- Phase 10: added bounded validation scripts: `scripts/run_fast_tests.sh` and `scripts/run_bounded_tests.sh`.

Independent developer audit performed after implementation:
- Verified validation/index/readiness paths report malformed artifacts instead of deleting or rewriting them.
- Verified generated reports remain `requires_human_review` operational diagnostics and do not write accepted `technical_audit` conclusions.
- Verified benchmark scores describe expected fixture metadata completeness, not full parser correctness.
- Verified traceability checks local path existence only and do not claim code implements the math.
- Verified live model calls remain blocked by default and no network/provider call was introduced.

Files touched:
- `docs/plans/industrial_scale_implementation_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `scripts/run_fast_tests.sh`
- `scripts/run_bounded_tests.sh`
- `src/research_assistant/cli.py`
- `src/research_assistant/industrial/platform.py`
- `tests/integration/test_cli_commands.py`
- `tests/integration/test_industrial_platform_cli.py`

Tests run:
- Fast bounded tier: `8 passed in 0.48s`.
- Broad bounded tier: `28 passed in 0.47s`.

Remaining risks:
- This is a local operational layer, not a deployed multi-user service.
- Readiness reports are gates and diagnostics, not scientific approval or production certification.
- A full deterministic suite was intentionally not run because this pass adopted bounded validation after the previous stale test session.

Next safe step:
- Commit the industrial validation/readiness implementation and record the commit hash.


## Update — industrial scale implementation committed

Commit completed:
- `9fa0bdc Add industrial validation and readiness workflow`

Final checkpoint:
- The industrial-scale implementation pass is complete through local validation, readiness reporting, dashboard readiness export, bounded validation scripts, focused tests, and commit.
- Pre-existing untracked `.codex` scratch state remains untouched.

Next safe step:
- Future work can use `scripts/run_fast_tests.sh` for quick validation and `scripts/run_bounded_tests.sh` for the broader bounded deterministic subset before attempting any longer suite.


## Update — full-scale department platform plan written

New planning artifact:
- `docs/plans/industrial_full_scale_department_platform_plan_2026-04-27.md`

Purpose:
- Provides explicit implementation instructions for taking the current local industrial platform toward a fully industrial departmental tool.
- Covers Phase 0 architecture control plus 15 implementation phases: production storage, collaboration, UI, search/knowledge graph, parser benchmarks, derivations, experiment execution, paper-to-code verification, LLM governance, security/compliance/ops, orchestration, CI/CD and observability, domain expert packs, SOP enforcement, and scalable ingestion.
- Each phase includes implementation instructions, tests, usefulness verification, and acceptance criteria.

Tests run:
- Not run; this update is a planning/documentation change.

Next safe step:
- If executing this plan, start with Phase 0 architecture baseline and ADRs before selecting production storage, auth, UI, or orchestration technologies.


## Update — full-scale department platform execution started

New objective:
- Audit `docs/plans/industrial_full_scale_department_platform_plan_2026-04-27.md`, tighten it where needed, and execute every phase with a conservative local-first implementation pass.

Execution boundary:
- This pass will implement deterministic architecture docs, ADRs, phase contracts, local backend/CLI scaffolds, tests, usefulness checks, and validation gates for all phases.
- It will not claim live production deployment, real SSO/RBAC, live LLM/provider access, production secrets management, concurrent server infrastructure, or policy-owner approval where those require external decisions.
- Every generated artifact remains review material unless an explicit human approval workflow accepts it.

Current phase:
- Plan audit and modification.

Files touched so far:
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this execution pass.

Next safe step:
- Audit and modify the full-scale plan, then implement the phase-contract layer across all phases with bounded validation.


## Update — full-scale phase-contract implementation completed

Plan audit and modifications:
- Added an audit-driven section to `docs/plans/industrial_full_scale_department_platform_plan_2026-04-27.md`.
- The plan now distinguishes M0 contracts, M1 local deterministic implementation, M2 governed integration, and M3 production deployment.
- Added explicit stop conditions for phases that require production storage decisions, SSO/RBAC, live providers, deployment, credentials, or department policy approval.

Phase execution notes:
- Phase 0: added architecture baseline and ADR control documents under `docs/architecture/`.
- Phase 1: added production storage contract metadata and storage ADR; real SQLite implementation remains a governed/local implementation follow-up.
- Phase 2: added collaboration/RBAC contract metadata and identity ADR; real production identity remains blocked for governed integration.
- Phase 3: added UI/API contract metadata and deployment ADR; real UI/server deployment remains blocked for governed integration.
- Phase 4: added search/knowledge graph contract metadata and indexing ADR.
- Phase 5: added parser/source benchmark contract metadata.
- Phase 6: added deep derivation contract metadata.
- Phase 7: added experiment execution/reproducibility contract metadata.
- Phase 8: added paper-to-code verification contract metadata.
- Phase 9: added LLM governance contract metadata and provider-policy ADR; live provider calls remain blocked.
- Phase 10: added security/compliance/ops contract metadata; real policy enforcement requires department approval.
- Phase 11: added workflow orchestration contract metadata and background-jobs ADR.
- Phase 12: added CI/CD and observability contract metadata.
- Phase 13: added domain expert pack contract metadata.
- Phase 14: added SOP enforcement contract metadata; approval enforcement depends on RBAC and security policy.
- Phase 15: added scalable ingestion contract metadata.

Implementation completed:
- Added machine-readable phase contracts in `src/research_assistant/industrial/full_scale.py`.
- Added `ra full-scale-plan phases`, `phase-show`, `registry-build`, `registry-show`, `usefulness-build`, and `readiness-build`.
- Added export visibility for full-scale planning artifacts.
- Added tests for architecture docs, ADR presence, phase contract completeness, governed stop conditions, CLI surfaces, usefulness metrics, execution readiness, and export preservation.

Tests run:
- Focused full-scale contract suite: `13 passed in 0.58s`.
- Fast bounded script after script update: `13 passed in 0.59s`.
- Broad bounded script after script update: `33 passed in 0.67s`.

Remaining risks:
- This pass executes M0 for all phases and safe local planning artifacts. It does not complete M2/M3 production storage, SSO/RBAC, live LLM access, UI deployment, or department security policy approval.

Next safe step:
- Commit the full-scale phase-contract implementation, then record the commit hash.


## Update — full-scale phase-contract implementation committed

Commit completed:
- `8af01a1 Add full-scale industrial platform phase contracts`

Final checkpoint:
- Full-scale plan was audited and modified with explicit milestone boundaries and stop conditions.
- Phase 0 through Phase 15 were executed at the M0 contract level through architecture docs, ADRs, machine-readable phase contracts, CLI commands, export visibility, tests, usefulness metrics, and execution-readiness artifacts.
- Governed integrations remain intentionally blocked where they require production storage decisions, SSO/RBAC, live LLM/provider access, UI/server deployment, credentials, or department security/compliance approval.

Validation completed:
- `scripts/run_fast_tests.sh`: `13 passed in 0.59s`.
- `scripts/run_bounded_tests.sh`: `33 passed in 0.67s`.

Next safe step:
- Start M1 local deterministic implementation with Phase 1 storage repository contracts, or choose a specific phase to deepen after accepting the relevant ADR.


## Update — individual colleague release plan written

Clarified release target:
- "Industrial scale release" now means each colleague installs and uses `research-assistant` as a private individual local tool.
- Shared server deployment, shared database, SSO/RBAC, real-time collaboration, and distributed workers are out of scope for this release target.

New planning artifact:
- `docs/plans/individual_colleague_release_plan_2026-04-27.md`

Plan contents:
- Covers packaging/install, `ra init`, local config, version/schema migration checks, backup/restore, robust CLI UX, `ra doctor`, bounded workflows, golden individual workflow tests, demo mode, offline/privacy safety, colleague-facing documentation, release CI, personal-corpus performance, and release-candidate process.
- Each phase includes motivation, implementation details, tests, usefulness verification, and acceptance criteria for another agent to execute.

Tests run:
- Not run; this update is a planning/documentation change.

Next safe step:
- Execute the individual release plan starting with packaging/install and `ra init`, using bounded validation and reset-memo checkpoints.


## Update — individual colleague release implementation started

New objective:
- Execute `docs/plans/individual_colleague_release_plan_2026-04-27.md` for a local individual-install release slice.

Plan audit:
- Added an audit-driven correction to prioritize a coherent local lifecycle: `ra init`, `ra doctor`, demo setup/run, workspace validation/migration/repair, backup create/inspect/restore dry-run, privacy status, release report, documentation, and bounded release smoke.
- Confirmed shared server, SSO/RBAC, multi-user collaboration, distributed workers, and live LLM/provider use remain out of scope for this release target.

Current phase:
- Phase 1 through Phase 15 local lifecycle implementation pass.

Files touched so far:
- `docs/plans/individual_colleague_release_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this pass.

Next safe step:
- Implement local release backend/CLI commands, tests, scripts, and colleague-facing docs with bounded validation.


## Update — individual colleague release implementation completed

Implementation completed:
- Added local individual-release backend helpers in `src/research_assistant/individual_release.py`.
- Added CLI lifecycle commands: `ra init`, `ra version`, `ra config show/set/validate`, `ra workspace validate/migrate/repair`, `ra backup create/inspect/restore`, `ra doctor`, `ra demo setup/run/clean`, `ra privacy status`, `ra bounded-workflow diagnostic`, `ra performance smoke`, and `ra release-report`.
- Added idempotent workspace initialization, local config defaults, offline/provider-disabled privacy status, optional parser/tool doctor output, dry-run migration/repair/restore reports, backup manifests with hashes, demo workflow artifacts, timeout diagnostic artifacts, and a small synthetic personal-corpus performance smoke.
- Added colleague-facing docs: installation, quickstart, individual workflow, troubleshooting, privacy, release checklist, and changelog.
- Added bounded release scripts: `scripts/run_release_smoke.sh` and `scripts/run_packaging_smoke.sh`.
- Added integration coverage in `tests/integration/test_individual_release_cli.py` plus CLI discoverability coverage.

Independent developer audit performed:
- Verified the release remains local/private and does not introduce shared server, SSO/RBAC, distributed workers, or live LLM/provider calls.
- Verified demo setup refuses to mark an existing non-demo workspace as demo-cleanable.
- Verified restore is dry-run only in this release slice and backup archives exclude nested backup archives.
- Verified generated derivation, experiment, traceability, governance, readiness, timeout, and performance artifacts remain review material.
- Verified `release-report` status is conditional on docs/scripts, workspace validation, privacy defaults, and doctor warnings rather than always claiming readiness.
- Verified packaging smoke uses `--no-build-isolation` so the offline release check does not try to fetch build dependencies.

Files touched:
- `README.md`
- `CHANGELOG.md`
- `docs/installation.md`
- `docs/quickstart.md`
- `docs/workflows/individual_research_workflow.md`
- `docs/troubleshooting.md`
- `docs/privacy.md`
- `docs/release_checklist.md`
- `docs/plans/individual_colleague_release_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `scripts/run_release_smoke.sh`
- `scripts/run_packaging_smoke.sh`
- `src/research_assistant/cli.py`
- `src/research_assistant/individual_release.py`
- `tests/integration/test_cli_commands.py`
- `tests/integration/test_individual_release_cli.py`

Validation completed:
- Focused individual-release suite: `5 passed in 0.31s`.
- CLI/industrial command compatibility check: `6 passed in 0.73s`.
- Fast bounded script before bounded/performance additions: `13 passed in 0.72s`.
- Release smoke before final audit tweak: `5 passed in 0.25s`, plus demo setup/run/release-report completed.
- Packaging smoke initially failed because isolated pip dry-run tried to fetch `setuptools>=68` from the network; script was corrected to use `--no-build-isolation`.
- Packaging smoke after correction: metadata test `1 passed in 0.02s`; pip dry-run reported `Would install research-assistant-0.1.0`.
- Broad bounded script: `33 passed in 0.72s`.
- Focused post-audit release suite: `6 passed in 0.27s`.
- Final release smoke: `6 passed in 0.27s`, plus demo setup/run/release-report completed.

Remaining risks:
- This is an individual-install local release slice, not a production shared department platform.
- Non-dry-run restore remains intentionally blocked until an explicit overwrite confirmation workflow exists.
- Parser quality, real corpus performance, and optional tool installation remain environment-dependent and should be validated on colleague machines.
- Demo readiness may report industrial readiness as `blocked` because it preserves human-review gates rather than pretending generated evidence is approved.

Next safe step:
- Stage the ignored individual release plan with `git add -f`, commit the release slice, then record the commit hash here.


## Update — individual colleague release implementation committed

Commit completed:
- `58ca98f Add individual release lifecycle commands`

Final checkpoint:
- The individual-install release slice has a coherent local lifecycle: initialize, configure, validate, diagnose, demo, backup, privacy check, timeout diagnostic, personal-corpus smoke, release report, docs, and bounded validation scripts.
- `docs/plans/individual_colleague_release_plan_2026-04-27.md` was force-staged because `docs/plans/` is ignored by `.gitignore`.
- Scratch/local generated state such as `.codex`, `.pytest_cache/`, local demo workspaces, and ignored `local_research/` artifacts was not committed.

Validation state for the committed implementation:
- `tests/integration/test_individual_release_cli.py`: `6 passed in 0.27s`.
- `scripts/run_release_smoke.sh`: `6 passed in 0.27s`, plus demo setup/run/release-report completed.
- `scripts/run_packaging_smoke.sh`: metadata test `1 passed in 0.02s`; offline pip dry-run with `--no-build-isolation` reported `Would install research-assistant-0.1.0`.
- `scripts/run_bounded_tests.sh`: `33 passed in 0.72s`.

Next safe step:
- Optionally test a clean install in a fresh virtual environment on a colleague-like machine and run `ra --root /tmp/research-assistant-demo demo setup`, `ra --root /tmp/research-assistant-demo demo run`, and `ra --root /tmp/research-assistant-demo release-report`.


## Update — individual release gap closure execution started

New objective:
- Execute `docs/plans/individual_release_gap_closure_plan_2026-04-27.md` to close the remaining individual-release hardening gaps after the first lifecycle implementation.

Plan audit:
- The 9-point plan covers clean install, optional parser/tool matrix, safe restore, corpus performance, release artifacts, onboarding/docs trial, version/release notes, platform compatibility, and data-loss/corruption hardening.
- Audit modification: add a Phase 0 release-hardening contract so every phase reports into one coherent `release-report` surface rather than producing isolated scripts and docs.
- Keep scope local/private. Do not introduce shared server deployment, SSO/RBAC, live collaboration, distributed workers, or default live providers.
- All validation must remain bounded and offline-first.

Current phase:
- Phase 0 through Phase 9 local deterministic implementation pass.

Files touched so far:
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this pass.

Next safe step:
- Add the Phase 0 audit amendment to the gap-closure plan, then implement each phase with focused tests and bounded validation.


## Update — individual release gap closure implemented

Current phase:
- Phase 0 through Phase 9 implemented as local deterministic release hardening.

Phase completion notes:
- Phase 0: added release-hardening contract through `ra release-report` schema v2, aggregating docs, scripts, privacy, platform, parser matrix, parser benchmark smoke, artifact manifest, onboarding, version consistency, and corruption-hardening signals.
- Phase 1: added `scripts/run_clean_install_smoke.sh`, which creates a fresh venv, installs the package, and runs help/version/init/doctor/demo/release-report under `timeout`.
- Phase 2: added `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke` for optional-tool and fixture parser-readiness reporting.
- Phase 3: implemented confirmed non-dry-run restore with `--confirm-restore`, `--allow-overwrite`, safety backup creation, hash validation, and path traversal rejection.
- Phase 4: expanded `ra performance smoke` with synthetic metadata/source/industrial artifacts, artifact index timing, optional export/backup timing, progress events, timeout diagnostics, and JSON report output.
- Phase 5: added `scripts/build_release_artifacts.sh` and `ra release-artifacts manifest`; build outputs under `build/` and `dist/` are now ignored and regenerated by script.
- Phase 6: added onboarding and known-limitations docs plus `ra onboarding-report`.
- Phase 7: added version consistency checks against `pyproject.toml`, `__version__`, entry point, and `CHANGELOG.md`; added release notes template.
- Phase 8: added `docs/platform_support.md` and `ra platform-status`.
- Phase 9: added atomic config writes, safer backup inspection/hash checks, corruption-hardening release-report section, and tests for invalid config/unsafe backup archives.

Independent developer audit performed:
- Confirmed all new release checks remain local/offline and do not add live provider calls.
- Confirmed restore defaults to dry-run and real restore requires explicit confirmation.
- Confirmed overwrite restore requires `--allow-overwrite` and creates a safety backup by default.
- Confirmed unsafe archive paths are rejected before restore.
- Confirmed generated build outputs are ignored rather than committed; release artifacts can be regenerated with `scripts/build_release_artifacts.sh`.
- Confirmed release-report can honestly return `warnings` when artifacts have not been built and `ready_for_release_candidate_review` after artifact manifest exists.

Files touched:
- `.gitignore`
- `docs/installation.md`
- `docs/privacy.md`
- `docs/quickstart.md`
- `docs/release_checklist.md`
- `docs/troubleshooting.md`
- `docs/onboarding_trial.md`
- `docs/known_limitations.md`
- `docs/platform_support.md`
- `docs/release_notes_template.md`
- `docs/plans/individual_release_gap_closure_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `scripts/run_clean_install_smoke.sh`
- `scripts/build_release_artifacts.sh`
- `src/research_assistant/cli.py`
- `src/research_assistant/individual_release.py`
- `src/research_assistant.egg-info/PKG-INFO`
- `src/research_assistant.egg-info/SOURCES.txt`
- `tests/integration/test_cli_commands.py`
- `tests/integration/test_individual_release_cli.py`

Validation completed:
- Focused individual release suite after implementation: `8 passed in 0.49s`.
- CLI help plus individual release suite: `9 passed in 0.57s`.
- `scripts/run_fast_tests.sh`: `13 passed in 0.66s`.
- `scripts/run_release_smoke.sh`: `8 passed in 0.53s`, plus demo setup/run/release-report completed; release-report returned `warnings` before artifacts were built.
- `scripts/run_packaging_smoke.sh`: metadata test `1 passed in 0.02s`; pip dry-run reported `Would install research-assistant-0.1.0`.
- `scripts/build_release_artifacts.sh`: built `research_assistant-0.1.0-py3-none-any.whl` and wrote `dist/release_artifacts_manifest.json`.
- `scripts/run_clean_install_smoke.sh`: fresh venv install succeeded; installed `research-assistant-0.1.0`; ran `ra --help`, `ra version`, `ra init`, `ra doctor`, `ra demo setup`, `ra demo run`, and `ra release-report`; final release-report returned `ready_for_release_candidate_review`.
- `scripts/run_bounded_tests.sh`: `33 passed in 0.71s`.

Remaining risks:
- Platform validation has only been run on the current Linux/WSL environment; macOS and Windows/WSL colleague machines still need manual signoff.
- Parser matrix reports availability and fixture readiness, not full parser scientific accuracy.
- Release artifact build currently produces a wheel through local `pip wheel --no-build-isolation`; sdist support remains optional/future if `python -m build` is available.
- Onboarding trial documentation exists, but a fresh colleague has not yet completed and recorded a trial.

Next safe step:
- Commit the gap-closure implementation, then optionally push `main`.


## Update — individual release gap closure committed

Commit completed:
- `047c1f6 Close individual release hardening gaps`

Final checkpoint:
- All 9 gap-closure phases plus the audit-added Phase 0 release-hardening contract are implemented and tested.
- The release report now reaches `ready_for_release_candidate_review` after release artifacts are built locally.
- Generated outputs under `build/` and `dist/` are intentionally ignored and can be regenerated with `scripts/build_release_artifacts.sh`.
- `.codex` remains untracked local scratch and was not committed.

Validation state at commit:
- Focused individual release suite: `8 passed in 0.49s`.
- CLI help plus individual release suite: `9 passed in 0.57s`.
- `scripts/run_fast_tests.sh`: `13 passed in 0.66s`.
- `scripts/run_release_smoke.sh`: `8 passed in 0.53s`, plus demo lifecycle completed.
- `scripts/run_packaging_smoke.sh`: metadata test `1 passed in 0.02s`; pip dry-run reported `Would install research-assistant-0.1.0`.
- `scripts/build_release_artifacts.sh`: built wheel and artifact manifest.
- `scripts/run_clean_install_smoke.sh`: fresh venv install and demo lifecycle completed.
- `scripts/run_bounded_tests.sh`: `33 passed in 0.71s`.
- Final focused sanity check: `9 passed in 0.52s`.

Next safe step:
- Push `main` if remote publication is desired, then run onboarding trial on at least one colleague-like machine before tagging a release.


## Update — individual colleague rollout execution started

New objective:
- Execute `docs/plans/individual_release_colleague_rollout_plan_2026-04-27.md` with the requested release-manager loop: update reset memo, audit as another developer, execute each phase with bounded testing, tidy, commit, push, and record completion.

Plan audit as another developer:
- The plan is correctly scoped to private individual local installs, not a shared industrial platform.
- The phases cover the remaining release blockers: human onboarding, platform signoff, optional parser-tool variability, medium-corpus rehearsal, backup/restore, artifact/install decision, release notes/version/tag decision, support boundary, and final gate.
- Modification made during audit: autonomous execution on this machine cannot honestly complete a real colleague trial, macOS validation, native Windows validation, or another-machine missing-tool trial. This pass will run the strongest local substitutes, update docs/code so the release gate is conservative, and record those items as pilot-release limitations rather than broad-release claims.
- Additional audit finding: the clean-install smoke should run installed `ra` from a temporary directory after installation, so `release-report` does not see source-checkout docs/scripts by accident. The script was corrected before final validation.
- Additional audit finding: concrete support instructions and filled release notes should be part of the release gate, not only a template.

Phase execution status:
- Phase 1 started. Fresh colleague onboarding cannot be performed by an actual colleague in this autonomous environment; local clean-install and onboarding-report substitutes will be run, and the limitation will remain explicit.
- Phase 2 started. Current available platform is Linux/WSL2 with Python 3.11.14; macOS and native Windows are not validated here.
- Phase 3 started. Current machine has all optional parser tools available; a real missing-tool environment is unavailable, so the existing workflow matrix/tests will stand as local coverage and the limitation is documented.

Files touched so far:
- `src/research_assistant/individual_release.py`
- `scripts/run_clean_install_smoke.sh`
- `docs/installation.md`
- `docs/quickstart.md`
- `docs/troubleshooting.md`
- `docs/platform_support.md`
- `docs/known_limitations.md`
- `docs/onboarding_trial.md`
- `docs/release_checklist.md`
- `docs/release_notes_template.md`
- `docs/support.md`
- `docs/release_notes_0.1.0.md`
- `.github/ISSUE_TEMPLATE/individual_release_bug.md`
- `tests/integration/test_individual_release_cli.py`
- `docs/plans/reset_memo_2026-04-26.md`

Tests run for this rollout pass:
- `ra version`: package `0.1.0`, Python `3.11.14`.
- `ra platform-status`: Linux/WSL2 probe returned `status: ok` before the WSL labeling tweak.

Next safe step:
- Run focused tests and the phase validations under `timeout`, then update this memo phase by phase with concise results and limitations.


## Update — individual colleague rollout execution completed

Phase summary:
- Phase 1 Fresh Colleague Onboarding Trial:
  - Local substitute completed with clean install from the built wheel in a fresh virtual environment.
  - `scripts/run_clean_install_smoke.sh` now installs the wheel from `dist/` when present and runs installed `ra` from a temporary directory, so source-checkout files are not accidentally visible.
  - Real fresh colleague trial remains required before broad non-pilot rollout.
- Phase 2 Platform Signoff:
  - Current validation platform: Linux/WSL2, `x86_64`, Python `3.11.14`, POSIX shell scripts available.
  - `ra platform-status` now labels this environment as `tier_1_linux_wsl`.
  - macOS and native Windows were not validated in this autonomous pass.
- Phase 3 Optional Parser Tool Variability Trial:
  - Current machine reports `pdftotext`, `markitdown`, `marker_single`, and `magic-pdf` available.
  - `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke` passed locally.
  - A real missing-tool machine was not available; limitation remains documented.
- Phase 4 Realistic Personal Corpus Rehearsal:
  - `ra --root /tmp/ra-perf-1000 performance smoke --synthetic-count 1000 --include-industrial-artifacts --include-export --include-backup --timeout-seconds 600` completed with `status: ok`.
  - Timings: validation `0.104516s`, artifact index `0.281222s`, export `20.791285s`, backup `1.265738s`.
  - Backup size: `685219` bytes.
  - This remains synthetic evidence, not certification for real personal libraries.
- Phase 5 Backup And Restore Rehearsal:
  - Demo source backup produced `/tmp/ra-rollout-restore-source/local_research/exports/backups/research_assistant_backup_20260426T203608Z.tar.gz`.
  - Fresh restore into `/tmp/ra-rollout-restore-target-2038` restored 13 files and then initialized missing empty workspace directories.
  - Restored workspace validation returned `status: ok`.
  - Repeat restore without `--allow-overwrite` blocked with `overwrite_not_allowed`.
  - Repeat restore with `--allow-overwrite` succeeded and created a safety backup.
  - Implementation hardening added `post_restore_workspace_init` to successful restore reports.
- Phase 6 Release Artifact And Install Path Decision:
  - Primary colleague install path is the wheel from the release artifact; source checkout remains the developer fallback.
  - `scripts/build_release_artifacts.sh` now probes `python -m build --version` before using `python -m build`, otherwise falling back to `pip wheel --no-build-isolation`.
  - Final local artifact: `research_assistant-0.1.0-py3-none-any.whl`, SHA256 `3afb9c23fc19b14e856caf2aba401b7e5d9018233f88198457e8f5aa56cdf2cf`.
- Phase 7 Release Notes, Version, And Tag Decision:
  - Version remains `0.1.0`.
  - Concrete release notes written to `docs/release_notes_0.1.0.md`.
  - No tag was created because the user requested commit/push, not tag creation.
- Phase 8 Support Boundary And Issue Template:
  - Added `docs/support.md`.
  - Added `.github/ISSUE_TEMPLATE/individual_release_bug.md`.
  - Linked support guidance from install, quickstart, troubleshooting, onboarding, and release notes.
- Phase 9 Final Release Gate:
  - Final source-checkout release report on initialized `/tmp/research-assistant-final-release` returned `ready_for_release_candidate_review` with no warnings.
  - The final gate now initializes the disposable final root before `release-report`; the rollout plan and release checklist were corrected accordingly.

Independent developer audit after execution:
- Verified release claims remain local/private and do not imply shared-server, SSO/RBAC, live collaboration, distributed worker, or default live provider support.
- Verified generated artifacts remain review material.
- Verified installed-package `release-report` reports source docs/scripts/fixtures as warnings instead of blockers; source-checkout release gates still require docs, scripts, fixture smoke, artifact manifest, and version consistency.
- Verified restore is explicit-confirmation only, overwrite requires `--allow-overwrite`, and safety backup is reported.
- Verified build outputs under `dist/` and local workspaces under `/tmp` are not intended for Git.

Validation completed in this rollout pass:
- Focused individual release suite: `8 passed in 0.52s`.
- Backup/restore focused regression after restore hardening: `1 passed in 0.17s`.
- `scripts/run_fast_tests.sh`: `13 passed in 0.65s`.
- `scripts/run_bounded_tests.sh`: `33 passed in 0.68s`.
- `scripts/run_packaging_smoke.sh`: metadata test `1 passed in 0.02s`; pip dry-run reported `Would install research-assistant-0.1.0`.
- `scripts/build_release_artifacts.sh`: built final wheel and manifest with SHA256 `3afb9c23fc19b14e856caf2aba401b7e5d9018233f88198457e8f5aa56cdf2cf`.
- `scripts/run_clean_install_smoke.sh`: installed the built wheel in a fresh venv; help/version/init/doctor/demo setup/demo run/release-report completed.
- `scripts/run_release_smoke.sh`: release suite `8 passed in 0.49s`; demo setup/run completed; source-checkout `release-report` returned `ready_for_release_candidate_review`.
- `ra --root /tmp/research-assistant-final-release init` followed by `ra --root /tmp/research-assistant-final-release release-report`: final report returned `ready_for_release_candidate_review` with no warnings.

Files touched:
- `.github/ISSUE_TEMPLATE/individual_release_bug.md`
- `docs/installation.md`
- `docs/known_limitations.md`
- `docs/onboarding_trial.md`
- `docs/platform_support.md`
- `docs/quickstart.md`
- `docs/release_checklist.md`
- `docs/release_notes_0.1.0.md`
- `docs/release_notes_template.md`
- `docs/support.md`
- `docs/troubleshooting.md`
- `docs/plans/individual_release_colleague_rollout_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `scripts/build_release_artifacts.sh`
- `scripts/run_clean_install_smoke.sh`
- `src/research_assistant/individual_release.py`
- `tests/integration/test_individual_release_cli.py`

Remaining risks:
- A real colleague has not yet completed the onboarding trial.
- macOS has not been validated.
- Native Windows is not supported; Windows colleagues should use WSL.
- Missing optional parser-tool behavior is represented through matrix/reporting and existing tests, but this pass did not run on a genuinely minimal parser-tool environment.
- The release candidate is ready for pilot colleague rollout, not broad unqualified departmental release.

Next safe step:
- Commit these rollout hardening/docs changes, force-staging the ignored plan/reset memo files, then push `main`.


## Update — final validation/publication plan execution started

New objective:
- Execute `docs/plans/individual_release_final_validation_publication_plan_2026-04-27.md` autonomously, using the requested loop: plan for phase, execute, test, audit, tidy, update reset memo, then commit.

Current baseline:
- `main` and `origin/main` both point to `eeb139d Execute colleague rollout release gate`.
- The tracked worktree was clean at recovery.
- Pre-existing local scratch remains untracked/ignored: `.codex` and `.claude/`.

Initial audit finding:
- Several release gaps require external resources that cannot be produced by a no-human-intervention local agent run: a real colleague onboarding trial, macOS validation, native Windows validation, and a genuinely separate minimal parser-tool machine.
- This pass will execute the strongest local substitutes, add deterministic coverage where useful, and keep the release decision conservative. If those external validations remain unavailable, the release remains a limited pilot rather than a broad colleague release.

Files touched so far:
- `docs/plans/individual_release_final_validation_publication_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this final validation/publication pass.

Next safe step:
- Complete the independent audit of the plan, update the plan if audit finds missing points, then execute phases 1 through 8 with bounded validation.


## Update — final validation/publication plan audited

Independent developer audit completed before execution:
- The plan correctly targets remaining release validation/publication gaps rather than new product scope.
- Platform, parser, corpus, artifact, support, privacy, and tag boundaries are conservative and auditable.
- Missing external resources are explicit: a real colleague, macOS machine, native Windows machine, and genuinely separate minimal parser-tool environment are not available to a local no-human-intervention run.
- Added an audit amendment to the plan clarifying that this autonomous pass can only produce local substitutes for those external validations.
- Corrected stale troubleshooting text that referenced the non-existent `ra parser-preflight`; current parser diagnostics are `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke`.
- Tightened release notes to state that 0.1.0 remains a limited pilot release candidate until external validations are recorded.

Files touched:
- `docs/plans/individual_release_final_validation_publication_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `docs/release_notes_0.1.0.md`
- `docs/troubleshooting.md`

Tests run:
- Not yet run after audit edits.

Next safe step:
- Execute Phase 1 local onboarding substitute and record that it does not satisfy the real-colleague acceptance criterion.


## Update — final validation Phase 1 completed

Phase 1 plan:
- Run the strongest local onboarding substitute available without human intervention.
- Validate clean install, demo, release report, and source-checkout release smoke.
- Keep the real-colleague onboarding gap open.

Execution:
- Initial `scripts/run_clean_install_smoke.sh` failed because release scripts defaulted `ROOT` to `/home/chakwong/research-assistant`, which is not this checkout.
- Hardened all release scripts to derive `ROOT` from their own `scripts/` directory while still honoring explicit `ROOT`.
- Hardened release scripts to export `PYTHONPATH=$ROOT/src` for source-layout checkout tests.
- Hardened `scripts/run_release_smoke.sh` to call `python -m research_assistant.cli` instead of assuming `ra` is on `PATH`.

Validation:
- `timeout 120 scripts/run_clean_install_smoke.sh`: passed after script hardening; installed `research-assistant-0.1.0` in a fresh venv and ran help/version/init/doctor/demo setup/demo run/release-report.
- `timeout 120 scripts/run_fast_tests.sh`: `13 passed in 0.79s`.
- `timeout 120 scripts/run_release_smoke.sh`: `9 passed in 0.92s`, then demo setup/run/release-report completed.

Audit:
- The local installed-package `release-report` correctly returned warnings for missing source docs/scripts/fixtures in the installed context.
- Source-checkout release smoke returned only `release_artifacts_not_built` before artifact rebuild, which is expected at this phase.
- This does not satisfy the real colleague onboarding acceptance criterion.

Files touched:
- `scripts/run_clean_install_smoke.sh`
- `scripts/build_release_artifacts.sh`
- `scripts/run_packaging_smoke.sh`
- `scripts/run_fast_tests.sh`
- `scripts/run_bounded_tests.sh`
- `scripts/run_release_smoke.sh`
- `docs/plans/reset_memo_2026-04-26.md`

Remaining risk:
- A real colleague still needs to complete the onboarding checklist before broad release.

Next safe step:
- Execute Phase 2 platform validation on the current machine and keep macOS/native Windows claims conservative.


## Update — final validation Phase 2 completed

Phase 2 plan:
- Validate the currently available platform with the platform probe, packaging smoke, clean-install smoke, and metadata entry-point test.
- Keep macOS and native Windows unvalidated unless those environments are actually available.

Execution and validation:
- `PYTHONPATH=src python -m research_assistant.cli platform-status`: passed with `system: Linux`, `is_wsl: true`, `machine: x86_64`, Python `3.11.15`, `status: ok`, `support_tier: tier_1_linux_wsl`.
- `timeout 180 scripts/run_packaging_smoke.sh`: metadata test `1 passed in 0.02s`; pip dry-run reported `Would install research-assistant-0.1.0`.
- `PYTHONPATH=src timeout 60 python -m pytest tests/integration/test_individual_release_cli.py::test_project_metadata_exposes_ra_entrypoint -q`: `1 passed in 0.02s`.
- `timeout 180 scripts/run_clean_install_smoke.sh`: passed; clean venv install and demo lifecycle completed.

Audit:
- The current validated Python is `3.11.15`, so platform docs and release notes were corrected from the older `3.11.14` claim.
- macOS remains unvalidated.
- Native Windows remains unsupported; Windows colleagues should use WSL.

Files touched:
- `docs/platform_support.md`
- `docs/release_notes_0.1.0.md`
- `docs/plans/reset_memo_2026-04-26.md`

Next safe step:
- Execute Phase 3 minimal parser-tool validation using the deterministic missing-tool simulation added during this pass plus local parser diagnostics.


## Update — final validation Phase 3 completed

Phase 3 plan:
- Run local parser/tool diagnostics.
- Add deterministic missing-tool simulation because no separate minimal machine is available.
- Verify missing optional parser tools do not block core lifecycle workflows.

Execution and validation:
- Added `test_missing_optional_parser_tools_do_not_block_core_workflows`, monkeypatching tool detection so all optional tools are absent.
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-parser-phase3 init`: passed.
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-parser-phase3 doctor --matrix`: passed; local tools show `pdftotext` available and `markitdown`, `marker_single`, `magic-pdf` missing.
- `PYTHONPATH=src python -m research_assistant.cli parser-tool-matrix`: passed; core/demo/metadata workflows `ok`, PDF/parser workflows report warnings as appropriate.
- `PYTHONPATH=src python -m research_assistant.cli parser-benchmark-smoke`: passed with 3 synthetic fixtures, status `ok`.
- `PYTHONPATH=src timeout 120 python -m pytest tests/integration/test_individual_release_cli.py::test_missing_optional_parser_tools_do_not_block_core_workflows -q`: `1 passed in 0.09s`.
- `timeout 120 scripts/run_fast_tests.sh`: `13 passed in 0.83s`.
- `timeout 120 scripts/run_bounded_tests.sh`: `33 passed in 0.91s`.

Audit:
- Missing `pdftotext` blocks only `pdf_text_ingest` in the simulation; init, demo, metadata, backup/privacy/release-report paths remain usable.
- Parser benchmark smoke remains fixture-only and explicitly not parser accuracy certification.
- A real separate minimal parser-tool machine remains stronger evidence and is still a pilot validation item.

Files touched:
- `tests/integration/test_individual_release_cli.py`
- `docs/plans/reset_memo_2026-04-26.md`

Next safe step:
- Execute Phase 4 representative corpus rehearsal, using synthetic corpus if no non-sensitive real corpus is available.


## Update — final validation Phase 4 completed

Phase 4 plan:
- Prefer a non-sensitive real corpus if available.
- No real corpus was provided in this autonomous environment, so run the prescribed synthetic 1000-record rehearsal and keep the real-corpus gap open.

Execution and validation:
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-perf-final-validation performance smoke --synthetic-count 1000 --include-industrial-artifacts --include-export --include-backup --timeout-seconds 600`: passed with `status: ok`.
- Synthetic records created: `1000`.
- Validation time: `0.105838s`.
- Artifact index time: `0.33259s`.
- Export time: `22.301315s`.
- Backup time: `1.578504s`.
- Backup size: `682843` bytes.
- Warning threshold: `50.0s`; no warnings.

Audit:
- This is useful local performance evidence but remains synthetic.
- It does not certify performance on real personal libraries with varied PDFs, filenames, annotations, or historical artifacts.
- Generated `/tmp/ra-perf-final-validation` data and backup archive are not intended for Git.

Files touched:
- `docs/plans/reset_memo_2026-04-26.md`

Next safe step:
- Execute Phase 5 artifact rebuild, manifest verification, and clean install from the current artifact path.


## Update — final validation Phase 5 completed

Phase 5 plan:
- Rebuild release artifacts from the current code.
- Verify manifest SHA256 and clean install from the built wheel.
- Keep artifacts ignored and update docs with the current hash.

Execution and validation:
- `timeout 180 scripts/build_release_artifacts.sh`: passed; built `research_assistant-0.1.0-py3-none-any.whl`.
- Final wheel SHA256 after current script/code edits: `3d764c3eeb77223bbc2ae67044211aea85064e14f936aded4edc5a07f84bbd35`.
- `PYTHONPATH=src python -m research_assistant.cli release-artifacts manifest`: passed with `artifact_count: 1`, `status: ok`.
- Initial artifact clean-install smoke exposed inherited `PYTHONPATH` contamination: pip saw the checkout package and skipped installing the wheel, leaving no `ra` in the venv.
- Hardened `scripts/run_clean_install_smoke.sh` so the fresh venv install runs with empty `PYTHONPATH`.
- Rebuilt artifacts after the script change and updated `docs/release_notes_0.1.0.md` with the new SHA256.
- `timeout 180 scripts/run_clean_install_smoke.sh`: passed from the built wheel; fresh venv installed `research-assistant-0.1.0` and ran help/version/init/doctor/demo setup/demo run/release-report.
- Sequential artifact final-check workspace:
  - `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-artifact-final-check-2 init`: passed.
  - `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-artifact-final-check-2 demo setup`: passed.
  - `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-artifact-final-check-2 demo run`: passed.
  - `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-artifact-final-check-2 release-report`: returned `ready_for_release_candidate_review` with no warnings.

Audit:
- The primary install path remains the wheel artifact.
- `dist/` remains generated and ignored, not intended for Git.
- Parallel execution of artifact final-check commands accidentally exposed an atomic temp-file collision during config writes; hardened `atomic_write_text` to use unique temp names and clean up stale temp files.

Files touched:
- `scripts/run_clean_install_smoke.sh`
- `src/research_assistant/individual_release.py`
- `docs/release_notes_0.1.0.md`
- `docs/plans/reset_memo_2026-04-26.md`

Next safe step:
- Execute Phase 6 docs/support/release-note consistency review and keep the decision as limited pilot unless external validations are complete.


## Update — final validation Phase 6 completed

Phase 6 plan:
- Review release notes, known limitations, support docs, issue template, platform docs, README, and usage docs for stale or overstated claims.
- Verify release-report and release smoke after documentation cleanup.
- Keep final decision pilot-scoped unless external validations are complete.

Execution:
- Scanned docs for stale release facts and command names.
- Found stale `ra parser-preflight` references in `README.md`, `docs/usage.md`, and `docs/validation_scripts.md`; replaced them with current diagnostics: `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke`.
- Confirmed no stale hash (`3afb9c23...` or `703b1bb...`) and no stale Python `3.11.14` claim remain in release docs.
- Release notes now state the candidate remains a limited pilot until real colleague onboarding, macOS validation, and missing-parser-tool validation are recorded.

Validation:
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-phase6-report-2 init`: passed.
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-phase6-report-2 release-report`: returned `ready_for_release_candidate_review` with no warnings.
- `timeout 120 scripts/run_release_smoke.sh`: `9 passed in 0.88s`, then demo setup/run/release-report completed with source-checkout report `ready_for_release_candidate_review`.

Audit:
- Support docs still protect private PDFs, `local_research/`, backup archives, `.codex`, `.claude`, credentials, and provider keys.
- Release notes and limitations correctly avoid parser accuracy, mathematical correctness, shared-server, native Windows, and broad-release claims.
- `docs/usage.md` and `README.md` are broader project docs, but stale parser command references would confuse release users, so updating them was appropriate.

Files touched:
- `README.md`
- `docs/usage.md`
- `docs/validation_scripts.md`
- `docs/release_notes_0.1.0.md`
- `docs/platform_support.md`
- `docs/troubleshooting.md`
- `docs/plans/reset_memo_2026-04-26.md`

Next safe step:
- Execute Phase 7 final ordered release gate from the current worktree.


## Update — final validation Phase 7 completed

Phase 7 plan:
- Run the final ordered gate from the current worktree.
- Confirm release-report has no blockers or unexpected warnings.
- Confirm generated build outputs and local workspaces are not staged.

Final gate validation:
- `timeout 120 scripts/run_fast_tests.sh`: `13 passed in 0.64s`.
- `timeout 180 scripts/run_bounded_tests.sh`: `33 passed in 0.74s`.
- `timeout 180 scripts/run_packaging_smoke.sh`: metadata test `1 passed in 0.03s`; pip dry-run reported `Would install research-assistant-0.1.0`.
- `timeout 180 scripts/build_release_artifacts.sh`: passed; final wheel `research_assistant-0.1.0-py3-none-any.whl`, SHA256 `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`, size `105348` bytes.
- `timeout 240 scripts/run_clean_install_smoke.sh`: passed from the built wheel in a clean venv; installed `research-assistant-0.1.0` and ran help/version/init/doctor/demo setup/demo run/release-report.
- `timeout 180 scripts/run_release_smoke.sh`: `9 passed in 1.50s`, then demo setup/run/release-report completed with source-checkout report `ready_for_release_candidate_review`.
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/research-assistant-final-release init`: passed.
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/research-assistant-final-release release-report`: returned `ready_for_release_candidate_review` with no warnings.

Audit:
- Release notes were updated to the final gate SHA256.
- Installed-package `release-report` still reports warnings for source docs/scripts/fixtures not bundled into the installed context, which is expected and non-blocking for the wheel smoke.
- Source-checkout `release-report` is the final release gate and returned ready with no warnings.
- Generated outputs under `build/`, `dist/`, `.pytest_cache/`, `__pycache__/`, and `/tmp` are not intended for Git.
- Tracked `src/research_assistant.egg-info/PKG-INFO` changed because it mirrors the README parser-command correction; keep it in the commit so package metadata is not stale.

Files touched:
- `README.md`
- `docs/usage.md`
- `docs/validation_scripts.md`
- `docs/release_notes_0.1.0.md`
- `docs/platform_support.md`
- `docs/troubleshooting.md`
- `scripts/*.sh` release validation scripts
- `src/research_assistant/individual_release.py`
- `tests/integration/test_individual_release_cli.py`
- `src/research_assistant.egg-info/PKG-INFO`
- `docs/plans/reset_memo_2026-04-26.md`

Next safe step:
- Execute Phase 8 as verification only: confirm version/artifact/tag status, do not tag or publish without explicit release-owner approval.


## Update — final validation Phase 8 completed

Phase 8 plan:
- Verify version, artifact manifest, and tag state.
- Do not tag or publish because tag/publication requires explicit release-owner approval separate from local validation.

Execution and validation:
- `PYTHONPATH=src python -m research_assistant.cli version`: package `research-assistant`, version `0.1.0`, Python `3.11.15`.
- `PYTHONPATH=src python -m research_assistant.cli release-artifacts manifest`: `artifact_count: 1`, status `ok`, wheel SHA256 `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`.
- `git tag --list 'v0.1.0'`: no tag exists.

Audit:
- No tag was created.
- No artifact was published.
- The release decision remains limited pilot because real colleague onboarding, macOS validation, and separate minimal parser-tool machine validation are still external pending items.

Release decision:
- Version: `0.1.0`
- Decision: limited pilot release candidate
- Commit: pending final commit for this validation pass
- Tag: none
- Artifact: `research_assistant-0.1.0-py3-none-any.whl`
- SHA256: `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`
- Platforms validated: Linux/WSL2 `x86_64`
- Python versions validated: `3.11.15`
- Real colleague onboarding: not completed; local clean-install substitute passed
- Minimal parser-tool environment: deterministic missing-tool simulation added and passed; separate minimal machine not completed
- Corpus rehearsal: synthetic 1000-record rehearsal passed; no real non-sensitive corpus provided
- Final validation commands: fast tests, bounded tests, packaging smoke, artifact build, clean install smoke, release smoke, final initialized-root release-report all passed
- Remaining limitations: macOS unvalidated, native Windows unsupported, parser accuracy not certified, generated artifacts are review material
- Next action: commit this validation pass; release owner may then run real external pilot validations and decide whether to tag/publish

Files touched in this final validation/publication pass:
- `README.md`
- `docs/plans/individual_release_final_validation_publication_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `docs/platform_support.md`
- `docs/release_notes_0.1.0.md`
- `docs/troubleshooting.md`
- `docs/usage.md`
- `docs/validation_scripts.md`
- `scripts/build_release_artifacts.sh`
- `scripts/run_bounded_tests.sh`
- `scripts/run_clean_install_smoke.sh`
- `scripts/run_fast_tests.sh`
- `scripts/run_packaging_smoke.sh`
- `scripts/run_release_smoke.sh`
- `src/research_assistant.egg-info/PKG-INFO`
- `src/research_assistant/individual_release.py`
- `tests/integration/test_individual_release_cli.py`

Next safe step:
- Force-stage the ignored final validation plan and reset memo, commit the validation pass, and leave generated artifacts ignored.


## Update — final validation/publication pass committed

Commit completed:
- `929bd41 Validate final individual release pilot`

Final checkpoint:
- The final validation/publication plan was audited, amended for autonomous execution limits, executed phase by phase, and committed.
- Release scripts now derive `ROOT` from their own location, set source-layout `PYTHONPATH` where needed, and clean `PYTHONPATH` for true wheel install smoke.
- Clean install smoke now proves the built wheel installs into a fresh venv without being masked by the source checkout.
- Atomic config writes now use unique temp files to avoid same-directory concurrent init collisions.
- Missing optional parser-tool behavior has deterministic regression coverage.
- Stale `ra parser-preflight` references were removed from release-facing docs and package metadata.
- Current limited pilot artifact: `research_assistant-0.1.0-py3-none-any.whl`.
- Current artifact SHA256: `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`.
- No tag was created and no artifact was published.

Release decision:
- `0.1.0` remains a limited pilot release candidate.
- Broad release still requires real colleague onboarding, macOS validation, and external/minimal parser-tool environment validation.

Validation summary at commit:
- Fast tests: `13 passed in 0.64s`.
- Bounded tests: `33 passed in 0.74s`.
- Packaging smoke: metadata test `1 passed in 0.03s`; pip dry-run would install `research-assistant-0.1.0`.
- Artifact build: passed with wheel SHA256 `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`.
- Clean install smoke: passed from the built wheel in a fresh venv.
- Release smoke: `9 passed in 1.50s`, demo lifecycle completed, source-checkout release-report returned `ready_for_release_candidate_review`.
- Final initialized-root release-report returned `ready_for_release_candidate_review` with no warnings.

Remaining local state:
- Pre-existing `.codex` remains untracked.
- Generated `build/`, `dist/`, caches, and bytecode remain ignored and uncommitted.

Next safe step:
- Push `main` if remote publication of this validation commit is desired.
- Run real colleague onboarding and macOS/minimal-parser-tool validations before tagging or broad release.


## Update — industrial release gap closure execution started

New objective:
- Execute `docs/plans/industrial_release_gap_closure_plan_2026-04-27.md` autonomously with the requested loop: update reset memo, audit as another developer, execute every phase, test, audit, tidy, commit, and update this memo at completion.

Current baseline:
- Latest committed checkpoint: `277665b Record final validation checkpoint`.
- Tracked worktree is clean at start.
- Pre-existing local scratch/generated state remains untracked or ignored: `.codex`, `.claude/`, caches, `build/`, and `dist/`.

Execution boundary:
- The plan contains M2/M3 phases requiring production storage decisions, identity/RBAC integration, UI deployment, live providers, credentials, security review, external users, and department SOP approval.
- This autonomous pass will implement M0 contracts and safe M1 local deterministic gates for every phase.
- Anything requiring external infrastructure, credentials, production deployment, or department owner approval will be marked `blocked_for_governed_integration`, not claimed as complete.

Files touched so far:
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run for this industrial release pass.

Next safe step:
- Audit the industrial release plan, add audit amendments if needed, then implement local release gate contracts and reports for phases 0 through 16.


## Update — industrial release gap plan audited

Independent developer audit completed before execution:
- The plan correctly separates the individual pilot from departmental beta and industrial production.
- The plan covers the major remaining gaps: external validation, publication/tagging, production storage, service contracts, RBAC/collaboration, parser/source benchmarks, derivation approval, experiment reproducibility, traceability, search/graph, LLM governance, security/ops, scalability, UI, SOPs, and final release gate.
- The main risk is over-execution: a local no-human-intervention agent cannot honestly complete M2/M3 work such as real production storage approval, SSO/RBAC, UI deployment, live provider use, security signoff, SOP approval, release publication, or external colleague/platform validation.
- Added an audit amendment clarifying that this autonomous pass must implement M0 contracts and safe M1 local deterministic checks, while marking governed integrations as blocked.

Files touched:
- `docs/plans/industrial_release_gap_closure_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`

Tests run:
- Not yet run after audit amendment.

Next safe step:
- Implement an industrial release gate contract/report layer that executes all phases as auditable M0/M1 status records and prevents false production claims.


## Update — industrial release gap phases 0-16 executed

Execution summary:
- Executed the industrial release gap plan as an M0/M1 autonomous pass, not as a fake production release.
- Added an industrial release gate module and CLI surface under `ra industrial-release`.
- Added a static machine-readable release gate contract at `docs/release/industrial_release_gates.json`.
- Added release, validation, publication, service/API, LLM governance, operations, security, scalability, and SOP docs.
- Added `scripts/run_industrial_release_gate.sh` as the bounded deterministic gate runner.
- Added integration coverage proving industrial production remains blocked without external validation, human approval, and governed integrations.

Phase outcomes:
- Phase 0 release definition: M0 contract complete; current level remains `individual_pilot`.
- Phase 1 external validation: sanitized aggregation implemented; missing colleague/macOS/minimal-parser/sanitized-corpus records block broader release.
- Phase 2 publication: runbook and publication check implemented; artifact hash/version/release-note checks, Git cleanliness, final-gate evidence, and manual approval are enforced as blockers.
- Phase 3 storage: production storage remains blocked for governed integration; local artifact/workspace validation is used as deterministic evidence.
- Phase 4 service/API: contract doc and tool-contract export updated.
- Phase 5 identity/collaboration: production SSO/RBAC remains blocked; local collaboration artifacts remain review material.
- Phase 6 parser benchmarks: local deterministic parser benchmark/readiness scaffolds remain the evidence surface; expanded gold corpus remains future work.
- Phase 7 derivation approval: generated derivations remain review artifacts; human mathematical approval remains blocked.
- Phase 8 experiment reproducibility: local fixture evidence/readiness is represented; external compute remains blocked.
- Phase 9 traceability: local target checks/readiness are represented without semantic correctness claims.
- Phase 10 search/graph: contract-level gate only; semantic/vector search remains policy-gated and M1 implementation remains blocked.
- Phase 11 LLM governance: policy doc added; live calls remain disabled until provider/security approval.
- Phase 12 security/ops: runbook/checklist added; security/compliance signoff remains blocked.
- Phase 13 scalability: validation protocol added; real/sanitized corpus performance remains externally blocked.
- Phase 14 UI workbench: production UI remains blocked until storage/API/identity/deployment decisions are accepted.
- Phase 15 SOPs: SOP draft added; department owner approval or waiver remains blocked.
- Phase 16 final gate: bounded script and aggregate gate report added; industrial production release is impossible to claim while upstream blockers remain.

Validation completed:
- `PYTHONPATH=src timeout 120 python -m pytest tests/integration/test_industrial_platform_cli.py::test_industrial_release_gates_block_production_without_external_approval -q`: `1 passed in 0.15s`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q`: `6 passed in 0.79s`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.84s`.
- `timeout 180 scripts/run_bounded_tests.sh`: `34 passed in 0.87s`.
- `timeout 300 scripts/run_industrial_release_gate.sh`: fast suite `14 passed in 0.82s`, bounded suite `34 passed in 0.87s`, industrial integration suite `6 passed in 0.78s`, then `ra industrial-release gate-build` completed with status `blocked` as intended.

Independent audit after execution:
- No tag was created and no artifact was published.
- No fake external validation, fake release-owner approval, fake SOP approval, fake security signoff, fake provider credentials, or fake production deployment was introduced.
- Generated/parser/LLM/benchmark/derivation/readiness artifacts remain review material.
- The final industrial gate reports `ready_for_individual_pilot: true`, `ready_for_departmental_beta: false`, and `ready_for_industrial_production: false`.
- The strongest remaining blockers are external validation, publication approval, production storage/identity/security/deployment decisions, SOP approval, scalability on sanitized real corpora, and live-provider governance.

Files touched:
- `src/research_assistant/industrial/release.py`
- `src/research_assistant/cli.py`
- `src/research_assistant/industrial/platform.py`
- `tests/integration/test_industrial_platform_cli.py`
- `scripts/run_industrial_release_gate.sh`
- `docs/release/industrial_release_definition.md`
- `docs/release/industrial_release_gates.json`
- `docs/release/external_validation_protocol.md`
- `docs/release/publication_runbook.md`
- `docs/release/scalability_validation_protocol.md`
- `docs/api/industrial_service_contract.md`
- `docs/governance/llm_provider_policy.md`
- `docs/ops/industrial_operations_runbook.md`
- `docs/security/security_review_checklist.md`
- `docs/sop/industrial_research_sop.md`
- `docs/plans/industrial_release_gap_closure_plan_2026-04-27.md`
- `docs/plans/reset_memo_2026-04-26.md`

Current checkpoint:
- Implementation commit completed: `ddd2219 Add industrial release gate contracts`.
- The ignored `docs/plans/industrial_release_gap_closure_plan_2026-04-27.md` was force-staged intentionally.
- Pre-existing `.codex` remains untracked; generated caches, `build/`, and `dist/` remain ignored.


## Update — industrial release gate contract pass committed

Commit completed:
- `ddd2219 Add industrial release gate contracts`

Final state after this round:
- `ra industrial-release` now exposes phase listing, phase details, release definition build/show, external validation aggregation, publication checks, gate build, and artifact show.
- The final industrial gate is an honest blocker report. It preserves `individual_pilot` as the current level and blocks departmental beta/industrial production until real external validations, publication approval, governed integrations, security/ops signoff, SOP approval, and scalability evidence exist.
- Static release docs and runbooks now define the industrial release taxonomy, validation protocol, publication workflow, service contract, provider policy, operations/security expectations, scalability protocol, and SOP draft.
- `scripts/run_industrial_release_gate.sh` gives maintainers a bounded deterministic gate runner.

Validation summary for commit:
- Focused industrial release gate test: `1 passed in 0.15s`.
- Industrial integration file: `6 passed in 0.79s`.
- Fast suite: `14 passed in 0.84s`.
- Bounded suite: `34 passed in 0.87s`.
- Industrial release gate script: fast suite `14 passed in 0.82s`, bounded suite `34 passed in 0.87s`, industrial integration suite `6 passed in 0.78s`, then gate build completed with status `blocked` as intended.

Residual industrial-release gaps:
- Real colleague onboarding, macOS, minimal parser-tool, and sanitized corpus validation records are still missing.
- Tagging and artifact publication still require explicit release-owner approval.
- Production storage/migration, SSO/RBAC, service deployment, UI deployment, security/compliance signoff, SOP approval, and live-provider governance remain M2/M3 blocked.
- Parser/source quality, scalability, search/indexing, derivation approval, traceability, and experiment reproducibility still need broader real-world/gold-corpus validation before departmental claims.

Remaining local state:
- `.codex` remains untracked.
- `.claude/`, caches, bytecode, `build/`, and `dist/` remain ignored and uncommitted.


## Update — robust individual-user release gap closure started

New objective:
- Execute `docs/plans/robust_individual_user_release_gap_closure_plan_2026-04-28.md` after the 2026-04-29 request.
- Update this reset memo, audit the plan as another developer, execute every phase with the plan/execute/test/audit/tidy/memo loop, commit the modified files, and update this memo on completion.

Current baseline:
- Latest committed checkpoint before this pass: `c12f542 Record individual Git final gap checkpoint`.
- Tracked worktree is clean.
- `docs/plans/robust_individual_user_release_gap_closure_plan_2026-04-28.md` exists under ignored `docs/plans/` and must be force-staged intentionally if committed.
- `.codex` remains untracked; `.claude/`, caches, bytecode, `build/`, and `dist/` remain ignored local state.

Independent plan audit before execution:
- Product scope: plan stays focused on individual local use and Git-based sharing. Database, service deployment, SSO/RBAC, hosted UI, real-time collaboration, and department operations remain out of scope.
- Release management: validation records, clean install, artifact hash, performance tier, clean checkout gate, tag approval, and publication approval are explicit.
- Privacy/data safety: plan requires sanitized evidence and excludes private papers, paths, backup archives, credentials, provider keys, tokens, `.codex`, `.claude`, caches, `build/`, and `dist/` from commits.
- Research trust: parser and merge outputs remain review material; parser scientific accuracy is not certified.
- Engineering: local automation is deterministic; external validations and release-owner approvals are separated from local substitutes.
- Audit finding 1: because this execution has no human intervention, phases requiring a real fresh reader, real macOS machine, real minimal parser-tool machine, or release-owner approval must be recorded as blocked/manual rather than attempted or faked.
- Audit finding 2: `scripts/run_clean_install_smoke.sh` should accept an explicit `WHEEL_PATH` so the clean install evidence is tied to the exact built artifact.

Execution boundary for this pass:
- Complete all locally automatable phases.
- Record unavailable external validations and approvals as blocked/manual.
- Do not create a tag or publish artifacts.

Phase 4 implementation checkpoint:
- Updated `scripts/run_clean_install_smoke.sh` to accept explicit `WHEEL_PATH`.
- Updated release checklist and release notes to run clean install against `dist/research_assistant-0.1.0-py3-none-any.whl`.
- Added/updated docs smoke assertions for explicit wheel install and parser scientific-accuracy limitation wording.

Focused validation:
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.64s`.

Audit:
- Clean-install evidence can now be tied to a specific wheel path instead of whichever wheel happens to sort last in `dist/`.
- Parser limitation language remains conservative.

Next safe step:
- Record unavailable external validations/approvals as blocked/manual evidence, then run local artifact build, clean install smoke, performance, and clean-checkout gate.


## Update — individual Git final gap closure validation completed

Execution completed for `docs/plans/individual_git_release_final_gap_closure_plan_2026-04-28.md`.

Implemented:
- Validation evidence schema and CLI:
  - `ra individual-git-release validation-record`
  - `ra individual-git-release validation-report`
  - `ra individual-git-release validation-substitutes`
- Realistic local fixture rehearsal:
  - `ra individual-git-release fixture-rehearsal`
  - dry-run/apply/rebuild/hygiene evidence on sanitized synthetic Git-sharing workspaces.
- Strict repository hygiene:
  - `ra repository-hygiene check --strict`
  - secret-like field detection, private path detection, build/cache/private-root detection, and strict Git-state warnings.
- Representative Git workspace performance:
  - `ra individual-git-release performance`
  - synthetic tier evidence including hygiene, merge dry-run/apply, rebuild, backup size, counts, and elapsed timings.
- Gate calibration:
  - `ra individual-git-release gate-build` now reports validation evidence, strict hygiene, fixture rehearsal, performance, release notes, publication approval, and deferred future-platform items.
- Release docs:
  - `docs/workflows/git_sharing_walkthrough.md`
  - updated release notes, release checklist, quickstart, privacy, support, platform support, onboarding trial, known limitations, and release notes template.
- Final ordered gate script:
  - `scripts/run_individual_git_release_gate.sh`

Validation completed:
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 2.69s`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q`: `6 passed in 0.91s`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.97s`.
- `timeout 180 scripts/run_bounded_tests.sh`: `34 passed in 0.96s`.
- `GATE_ROOT=/tmp/research-assistant-individual-git-gate-clean timeout 300 scripts/run_individual_git_release_gate.sh`: fast suite `14 passed in 1.25s`, bounded suite `34 passed in 1.33s`, individual release integration suite `14 passed in 2.31s`, local validation substitutes recorded, fixture rehearsal passed, synthetic Git 100 performance passed, strict hygiene completed with warnings only, release report was ready for release-candidate review, validation report was blocked for manual items, and final gate completed with status `blocked` as intended.
- `timeout 300 scripts/build_release_artifacts.sh`: built `research_assistant-0.1.0-py3-none-any.whl`, SHA256 `914e0993539067bd5cb309cb645edcc49bb1338930edbfd771a096718887161d`, and regenerated `dist/release_artifacts_manifest.json`.
- `git diff --check`: clean.

Final audit before commit:
- No tag was created and no artifact was published.
- Real colleague onboarding, macOS validation, real minimal-parser-tool machine validation, release-owner tag approval, and publication approval were not faked. They are represented as blocked/manual validation records when substitutes are generated.
- Synthetic fixture and performance workspaces are removed after compact evidence records are written, so backup archives and synthetic workspaces are not left as shareable artifacts.
- Generated validation, fixture, performance, merge, parser, benchmark, derivation, traceability, LLM, and readiness artifacts remain review material.
- The gate reports `ready_for_limited_individual_pilot: true`, `ready_for_git_shared_research_release: false`, `ready_for_broad_individual_release: false`, and `future_multi_user_platform_deferred: true`.

Remaining release blockers:
- Real colleague onboarding from docs.
- Real macOS validation.
- Real minimal parser-tool environment validation.
- Explicit release-owner approval for tag creation and publication.

Current local state before commit:
- Modified tracked release code/docs/tests plus tracked `src/research_assistant.egg-info/SOURCES.txt` refreshed by the artifact build.
- New tracked-intended files: `docs/workflows/git_sharing_walkthrough.md`, `scripts/run_individual_git_release_gate.sh`.
- Ignored plan file `docs/plans/individual_git_release_final_gap_closure_plan_2026-04-28.md` must be force-staged intentionally.
- `.codex` remains untracked.
- `.claude/`, caches, bytecode, `build/`, and `dist/` remain ignored and should not be committed.


## Update — individual Git final gap closure committed

Implementation commit completed:
- `d541596 Close individual Git final release gaps`

Final state after this round:
- Individual Git release evidence is first-class, local, sanitized, and auditable.
- Strict repository hygiene checks private/generated roots and secret-like payloads before sharing.
- Deterministic fixture rehearsal and representative synthetic Git workspace performance are available through `ra individual-git-release`.
- The final ordered script `scripts/run_individual_git_release_gate.sh` produces the local validation packet.
- The release docs now target the individual local tool with Git-sharing workflow and clearly defer multi-user platform work.

Validation summary for commit:
- Individual release integration file: `14 passed in 2.69s`.
- Industrial platform integration file: `6 passed in 0.91s`.
- Fast suite: `14 passed in 0.97s`.
- Bounded suite: `34 passed in 0.96s`.
- Final individual Git release gate script: fast suite `14 passed in 1.25s`, bounded suite `34 passed in 1.33s`, individual release integration suite `14 passed in 2.31s`, local fixture evidence passed, synthetic Git 100 performance passed, release report was ready for release-candidate review, and final gate completed with status `blocked` as intended for manual external validation and approval.
- Release artifact build completed with wheel SHA256 `914e0993539067bd5cb309cb645edcc49bb1338930edbfd771a096718887161d`.

Remaining release blockers:
- Real colleague onboarding from the docs.
- Real macOS validation.
- Real minimal parser-tool machine validation.
- Explicit release-owner approval for tag creation.
- Explicit release-owner approval for artifact publication.

Remaining local state:
- `.codex` remains untracked.
- `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, and `dist/` remain ignored and uncommitted.


## Update — individual Git final gap closure started

New objective:
- Execute `docs/plans/individual_git_release_final_gap_closure_plan_2026-04-28.md` after the computer shutdown recovery.
- Update this reset memo, audit the plan as another developer, execute each phase with the plan/execute/test/audit/tidy/memo loop, commit the modified files, and record completion.

Current baseline:
- Latest committed checkpoint before this pass: `9771c27 Record individual Git release checkpoint`.
- Tracked worktree is clean.
- `docs/plans/individual_git_release_final_gap_closure_plan_2026-04-28.md` exists under ignored `docs/plans/` and must be force-staged intentionally.
- `.codex` remains untracked; `.claude/`, caches, bytecode, `build/`, and `dist/` remain ignored local state.

Independent plan audit before execution:
- Product scope: plan stays focused on individual local use and Git-based sharing. Database, service deployment, SSO/RBAC, hosted UI, real-time collaboration, and department operations remain deferred future-platform work.
- Release management: validation evidence, release notes, final gate, and tag/publication approval are explicit. Missing point corrected in execution policy: real colleague/macOS/minimal-machine validation and release-owner approval cannot be completed autonomously and must be recorded as blocked/manual, not fabricated.
- Privacy/data safety: fixtures must remain sanitized; strict hygiene must block private paths, raw papers, backup archives, generated caches, credentials, provider keys, and tokens.
- Research trust: merge/import, parser checks, performance reports, validation records, and release gates remain review/governance evidence, not mathematical approval or parser-quality certification.
- Engineering: local automation should be deterministic and fixture-based; external validation should be separately represented from local substitutes.

Phase execution policy for this pass:
- Implement local evidence schemas, fixture rehearsal, strict hygiene, performance reports, gate calibration, docs, and final gate script.
- Record locally unavailable external validations as blocked/manual records where useful.
- Run focused tests before broader validation.
- Do not create a tag or publish artifacts without explicit release-owner approval.

Phase 1-7 local implementation checkpoint:
- Added individual Git validation evidence records and reports under `local_research/governance/individual_git_release/validation/`.
- Added local substitute recording for Linux/WSL and parser-tool evidence, while recording colleague onboarding, macOS, tag approval, and publication approval as blocked/manual when no real validation or approval exists.
- Hardened repository hygiene with secret/private-path scanning and `--strict` checks for local build/cache/private roots.
- Added deterministic fixture rehearsal for Git-sharing merge/import/rebuild evidence.
- Added representative synthetic Git workspace performance evidence.
- Calibrated `ra individual-git-release gate-build` around local fixture evidence, strict hygiene, external validation, publication approval, and deferred future-platform items.

Focused validation:
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 2.69s`.

Audit after phases 1-7:
- Local fixture evidence is deterministic and sanitized.
- Real colleague/macOS/minimal-machine validation is not faked; it remains blocked/manual in validation evidence.
- Generated governance and performance reports remain review material.
- Backup archives produced during fixture/performance rehearsals are tidied from synthetic workspaces after size evidence is captured.

Next safe step:
- Update walkthrough, release docs, known limitations, privacy/release checklist, and final ordered gate script.


## Update — individual Git release gap closure started

New objective:
- Execute `docs/plans/individual_git_release_gap_closure_plan_2026-04-28.md` after reframing the release target as an individual local tool with Git-based sharing.
- Update the reset memo, audit the plan as another developer, execute every phase with the plan/execute/test/audit/tidy/memo loop, commit the modified files, and record completion.

Current baseline:
- Latest committed checkpoint: `970085a Record industrial release gate checkpoint`.
- New uncommitted docs already exist from the target reset discussion:
  - `docs/proposal/individual_git_release_target.md`
  - `docs/plans/individual_git_release_gap_closure_plan_2026-04-28.md`
- Pre-existing `.codex` remains untracked; `.claude/`, caches, `build/`, and `dist/` remain ignored.

Execution boundary:
- The current release target is individual local use plus Git checkout/import sharing.
- Production database, shared service, SSO/RBAC, real-time collaboration, hosted UI, department SOP approval, and production deployment are future-platform concerns, not blockers for this release track.
- Merge/import work must remain local, deterministic, dry-run by default, privacy-preserving, and unable to silently approve or overwrite accepted research conclusions.

Tests run:
- Not yet run for this individual Git release pass.

Next safe step:
- Audit the new plan, amend it if needed, then implement shareable workspace policy, repository hygiene, workspace merge dry-run/apply, post-merge rebuild, docs, and a revised individual Git release gate.


## Update — individual Git release phases 0-5 executed

Plan/audit:
- Audited `docs/plans/individual_git_release_gap_closure_plan_2026-04-28.md` from product-scope, data-safety, research-trust, and engineering perspectives.
- Audit finding: `workspace rebuild-derived` should be required rather than optional so post-merge rebuild is a testable release surface.
- Chose a new individual-Git release module instead of bending the existing industrial-production gate, so future multi-user platform blockers remain visible but deferred.

Execution:
- Phase 0: rewrote release definition/gate contract around `limited_individual_pilot`, `broad_individual_release`, `git_shared_research_release`, and `future_multi_user_platform`.
- Phase 1: added shareable workspace policy and Git sharing workflow docs.
- Phase 2: added `ra repository-hygiene check/policy/classify`.
- Phase 3: added `ra workspace merge` dry-run, with classification for copy candidates, already-present records, conflicts, forbidden files, rebuildable files, and unsupported files.
- Phase 4: added explicit merge apply mode requiring `--apply --confirm-merge`, creating a backup and preserving import provenance.
- Phase 5: added `ra workspace rebuild-derived` for deterministic post-merge artifact index/readiness/workspace validation.

Focused validation:
- `PYTHONPATH=src timeout 120 python -m pytest tests/integration/test_individual_release_cli.py::test_repository_hygiene_policy_and_individual_git_gate -q`: `1 passed in 0.35s`.
- `PYTHONPATH=src timeout 120 python -m pytest tests/integration/test_individual_release_cli.py::test_workspace_merge_dry_run_apply_and_rebuild -q`: `1 passed in 0.24s`.

Audit after execution:
- Merge is dry-run by default.
- Apply mode refuses without explicit confirmation.
- Forbidden private/raw/generated files block merge or repository hygiene.
- Accepted `technical_audit` conflicts are reported as blockers.
- Imported JSON artifacts record source path/commit when available, merge timestamp, and merge report ID.
- Generated indexes/reports are skipped during merge and rebuilt separately.

Next safe step:
- Execute phases 6-8: update release docs, add/revise the individual Git release gate docs/tests, run broader validation, tidy, update memo, and commit.


## Update — individual Git release phases 6-8 executed

Execution:
- Phase 6 documentation: added `docs/workflows/git_sharing_workflow.md` and updated quickstart, privacy, known limitations, release checklist, and release notes template with the Git-sharing workflow.
- Phase 7 gate revision: added `ra individual-git-release gate-build` and updated `docs/release/industrial_release_gates.json` to describe current individual/Git gates and deferred future-platform gates.
- Phase 8 local validation: ran CLI smoke for `individual-git-release gate-build` and `repository-hygiene check`; no tag or publication was attempted.

Focused/broad validation so far:
- Individual release integration file: `11 passed in 1.43s`.
- Industrial platform integration file after target-shift test update: `6 passed in 0.96s`.

Audit after execution:
- The old industrial CLI runtime gate still reports `industrial-release-gates-v1` for historical production-blocker reporting.
- The static release gate contract now reports `individual-git-release-v1` as the current release target.
- Future shared database, service deployment, SSO/RBAC, real-time collaboration, hosted UI, and department operations remain visible as deferred future-platform items rather than current release blockers.
- The individual Git gate remains blocked for broad release until real colleague/platform validation and release-owner tag/publication approval are recorded.

Next safe step:
- Run fast/bounded validation, final diff audit, force-stage ignored plan/memo files, commit, and update this memo with completion details.


## Update — individual Git release validation completed

Validation completed:
- `PYTHONPATH=src timeout 120 python -m pytest tests/integration/test_individual_release_cli.py::test_repository_hygiene_policy_and_individual_git_gate -q`: `1 passed in 0.35s`.
- `PYTHONPATH=src timeout 120 python -m pytest tests/integration/test_individual_release_cli.py::test_workspace_merge_dry_run_apply_and_rebuild -q`: `1 passed in 0.24s`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `11 passed in 1.43s`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q`: `6 passed in 0.96s`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 1.04s`.
- `timeout 180 scripts/run_bounded_tests.sh`: `34 passed in 1.07s`.
- CLI smoke: `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-individual-git-release individual-git-release gate-build` completed with status `blocked`, `ready_for_limited_individual_pilot: true`, and future database/service/RBAC/UI items deferred.
- CLI smoke: `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-individual-git-release repository-hygiene check` completed with status `ok` on an empty temp workspace.
- `git diff --check`: clean after removing a trailing blank line.

Files touched:
- `src/research_assistant/individual_git_release.py`
- `src/research_assistant/cli.py`
- `src/research_assistant/industrial/platform.py`
- `tests/integration/test_individual_release_cli.py`
- `tests/integration/test_industrial_platform_cli.py`
- `docs/proposal/individual_git_release_target.md`
- `docs/plans/individual_git_release_gap_closure_plan_2026-04-28.md`
- `docs/plans/reset_memo_2026-04-26.md`
- `docs/release/industrial_release_definition.md`
- `docs/release/industrial_release_gates.json`
- `docs/release/shareable_workspace_policy.json`
- `docs/workflows/git_sharing_workflow.md`
- `docs/quickstart.md`
- `docs/privacy.md`
- `docs/known_limitations.md`
- `docs/release_checklist.md`
- `docs/release_notes_template.md`

Residual risks:
- Real colleague/platform validation and release-owner tag/publication approval remain manual gates.
- Merge/import handles local JSON artifacts and conservative conflicts; it does not provide live collaboration or semantic research reconciliation.
- Production database, service deployment, SSO/RBAC, real-time collaboration, hosted UI, and department SOPs remain deferred future-platform items.

Current checkpoint:
- Implementation commit completed: `05dbc1f Add individual Git release workflow`.
- `docs/plans/individual_git_release_gap_closure_plan_2026-04-28.md` and this reset memo are under ignored `docs/plans/`; force-stage intentional plan/memo changes.
- Keep `.codex`, `.claude/`, caches, `build/`, and `dist/` out of the commit.


## Update — individual Git release workflow committed

Commit completed:
- `05dbc1f Add individual Git release workflow`

Final state after this round:
- The canonical release target is now documented as an individual local tool with Git-based sharing.
- `ra repository-hygiene check/policy/classify` provides the shareability and privacy-hygiene surface.
- `ra workspace merge` provides dry-run-by-default domain-aware merge reports and explicit apply mode with backup/confirmation.
- `ra workspace rebuild-derived` rebuilds local derived reports after import.
- `ra individual-git-release gate-build` answers the current release question and treats database/service/RBAC/UI as deferred future-platform items.
- Release-facing docs now explain repository hygiene, Git sharing, merge/import, post-merge rebuild, and the future-platform boundary.

Validation summary at commit:
- Focused repository hygiene/gate test: `1 passed in 0.35s`.
- Focused workspace merge/rebuild test: `1 passed in 0.24s`.
- Individual release integration file: `11 passed in 1.43s`.
- Industrial platform integration file: `6 passed in 0.96s`.
- Fast suite: `14 passed in 1.04s`.
- Bounded suite: `34 passed in 1.07s`.
- CLI individual Git gate smoke completed with status `blocked` as intended pending external validation and release-owner approval.
- CLI repository hygiene smoke completed with status `ok` on an empty temp workspace.
- `git diff --check` and staged diff check were clean before commit.

Remaining release gates:
- Real colleague/platform validation is still manual and not completed by this local pass.
- Tagging and artifact publication still require explicit release-owner approval.
- Workspace merge is conservative and local; it does not provide live collaboration or semantic reconciliation of research disagreements.
- Future multi-user platform work remains deferred: shared database, service deployment, SSO/RBAC, real-time collaboration, hosted UI, and department operations/SOPs.

Remaining local state:
- `.codex` remains untracked.
- `.claude/`, caches, bytecode, `build/`, and `dist/` remain ignored and uncommitted.


## Update - robust individual-user release local execution completed

Execution completed locally for `docs/plans/robust_individual_user_release_gap_closure_plan_2026-04-28.md`.

Phase results:
- Phases 1, 2, 3, and 8 require real external actors or release-owner approval. They were not faked. Evidence records were written as blocked/manual for fresh-reader onboarding, macOS validation, real minimal parser-tool machine validation, tag approval, and publication approval.
- Phase 4 completed: `scripts/run_clean_install_smoke.sh` now accepts explicit `WHEEL_PATH`, and the clean-install smoke was run against `dist/research_assistant-0.1.0-py3-none-any.whl`.
- Phase 5 completed locally: synthetic Git performance was expanded to `synthetic_git_1000`.
- Phase 6 was prepared for post-commit clean-checkout validation; a clean checkout should be made from the implementation commit.
- Phase 7 completed: parser wording remains conservative and says parser scientific accuracy is not certified.
- Phase 9 completed for local docs and this reset memo before commit.

Artifact and install evidence:
- `timeout 300 scripts/build_release_artifacts.sh`: built `research_assistant-0.1.0-py3-none-any.whl`.
- Wheel SHA256: `981298e1b0d7610a5e8be2c7a1a353717291d4c309fdfb016db438ab2dfd568c`.
- `WHEEL_PATH=/home/chakwong/python/ResearchAssistant/dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh`: passed twice in this pass. The installed wheel completed `ra --help`, `ra version`, `init`, `doctor`, `demo setup`, `demo run`, and `release-report`.
- Installed-package `release-report` warnings about missing repository docs/scripts/fixtures are expected in wheel-only context and were not treated as release blockers for the install smoke.

Performance and evidence workspace:
- Evidence workspace: `/tmp/research-assistant-robust-release-evidence`.
- `PYTHONPATH=src timeout 700 python -m research_assistant.cli --root /tmp/research-assistant-robust-release-evidence individual-git-release performance --tier synthetic_git_1000 --synthetic-count 1000 --timeout-seconds 600`: passed.
- Performance result: elapsed `1.050277` seconds; source files `1000`; target files `1254`; dry-run copy candidates `750`; already present `250`; conflicts/blockers `0`; apply copied `750`; backup size `152592` bytes.
- Fixture rehearsal passed in the evidence workspace.
- Strict repository hygiene in the evidence workspace produced warnings only for non-Git workspace context, rebuildable generated evidence, and `.research-assistant/config.json` being unsupported for sharing.

Validation report and gate evidence:
- `PYTHONPATH=src timeout 180 python -m research_assistant.cli --root /tmp/research-assistant-robust-release-evidence individual-git-release validation-report`: status `blocked`, record count `9`, local fixture validation complete, external validation incomplete.
- Blocked required validation: `colleague_onboarding`, `macos`, `minimal_parser_tools`.
- Publication approval: not approved.
- `PYTHONPATH=src timeout 180 python -m research_assistant.cli --root /tmp/research-assistant-robust-release-evidence individual-git-release gate-build`: status `blocked`, `ready_for_limited_individual_pilot: true`, `ready_for_git_shared_research_release: false`, `ready_for_broad_individual_release: false`.
- Fresh local gate workspace: `GATE_ROOT=/tmp/research-assistant-robust-gate-20260429 timeout 300 scripts/run_individual_git_release_gate.sh` passed the local command sequence. It produced fast suite `14 passed`, bounded suite `34 passed`, individual release integration suite `14 passed`, fixture rehearsal passed, synthetic Git 100 performance passed, validation record count `8`, and final gate status `blocked` only for manual external validation and release-owner approval.

Validation commands completed in this pass:
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.76s`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q`: `6 passed in 0.94s`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.91s`.
- `timeout 180 scripts/run_bounded_tests.sh`: `34 passed in 0.97s`.
- `timeout 300 scripts/run_individual_git_release_gate.sh`: completed with final gate status `blocked` as expected.
- `GATE_ROOT=/tmp/research-assistant-robust-gate-20260429 timeout 300 scripts/run_individual_git_release_gate.sh`: completed with final gate status `blocked` as expected from a fresh gate workspace.
- `git diff --check`: clean.

Files intentionally changed:
- `scripts/run_clean_install_smoke.sh`
- `tests/integration/test_individual_release_cli.py`
- `docs/known_limitations.md`
- `docs/platform_support.md`
- `docs/release_checklist.md`
- `docs/release_notes_0.1.0.md`
- `docs/plans/robust_individual_user_release_gap_closure_plan_2026-04-28.md`
- `docs/plans/reset_memo_2026-04-26.md`

Audit and tidy:
- No tag was created and no artifact was published.
- No private papers, private local paths, backup archives, credentials, provider keys, tokens, `.codex`, `.claude`, caches, `build/`, or `dist/` are intended for commit.
- The ignored plan file must be force-staged intentionally.
- `dist/` contains rebuilt artifacts but remains ignored and uncommitted.
- `.codex` remains untracked; `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, and `dist/` remain ignored local state.

Next safe step:
- Commit the implementation and docs changes.
- Create a clean local clone from that implementation commit, run the clean-checkout gate, then update this memo with the clean-checkout result and final commit checkpoint.


## Update - robust individual-user release checkpoint committed

Implementation commit completed:
- `5587871 Close robust individual release gaps`

Clean-checkout validation:
- Clean local clone: `/tmp/research-assistant-clean-5587871`.
- Clean clone commit: `5587871`.
- Initial `git status --short --ignored` in the clone was clean.
- `GATE_ROOT=/tmp/research-assistant-clean-5587871-gate timeout 300 scripts/run_individual_git_release_gate.sh`: completed.
- Clean-checkout gate validation included fast suite `14 passed in 1.06s`, bounded suite `34 passed in 0.95s`, and individual release integration suite `14 passed in 1.72s`.
- The clean-checkout gate recorded Linux/WSL local validation, local parser-tool substitute evidence, blocked fresh-reader onboarding, blocked macOS validation, blocked release-owner tag approval, blocked publication approval, fixture rehearsal passed, and synthetic Git 100 performance passed.
- Clean-checkout final gate status: `blocked`.
- Clean-checkout readiness flags: `ready_for_limited_individual_pilot: true`, `ready_for_git_shared_research_release: false`, `ready_for_broad_individual_release: false`.
- Clean-checkout blockers were expected: real colleague/macOS/minimal-machine validation remains manual, and release-owner tag/publication approval was not provided.
- Clean clone post-validation `git status --short --ignored` showed only ignored `.pytest_cache/` and bytecode caches.

Final state after this round:
- Explicit wheel clean-install smoke support is implemented through `WHEEL_PATH`.
- Release docs now point the clean install smoke at the exact wheel path and record SHA256 `981298e1b0d7610a5e8be2c7a1a353717291d4c309fdfb016db438ab2dfd568c`.
- Parser claims are calibrated: parser-tool checks do not certify scientific parser accuracy.
- Local robust-release evidence now includes explicit-wheel clean install, synthetic Git 1000 performance, fixture rehearsal, validation-report/gate evidence, and clean-checkout gate evidence.
- No tag was created and no artifact was published.

Remaining robust-release blockers:
- Real fresh-reader onboarding from the docs.
- Real macOS validation.
- Real minimal parser-tool machine validation.
- Explicit release-owner approval for tag creation.
- Explicit release-owner approval for artifact publication.

Remaining local state:
- `.codex` remains untracked.
- `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, and `dist/` remain ignored and uncommitted.
- This final reset memo update is included in the follow-up memo checkpoint commit.


## Update - pre-final maintainability/report execution started

New objective:
- Execute `docs/plans/pre_final_release_maintability_report_plan_2026-04-29.md` if present, otherwise `docs/plans/pre_final_release_maintainability_report_plan_2026-04-29.md`.
- Update this reset memo, audit the plan as another developer, execute every phase with the plan/execute/test/audit/tidy/memo loop, commit modified files, and update this memo on completion.

Current baseline:
- Latest committed checkpoint before this pass: `da61713 Record robust individual release checkpoint`.
- The tracked worktree has no uncommitted tracked changes.
- `docs/plans/pre_final_release_maintainability_report_plan_2026-04-29.md` exists under ignored `docs/plans/` and must be force-staged intentionally if committed.
- `.codex` remains untracked; `.claude/`, caches, bytecode, `build/`, and `dist/` remain ignored local state.

Independent plan audit before execution:
- Product scope: plan correctly keeps the current release centered on an individual local filesystem tool with Git-based sharing. Shared database, service deployment, SSO/RBAC, hosted UI, real-time collaboration, and department operations remain future extension material.
- Engineering risk: plan requires behavior-preserving refactors, compatibility facades when splitting modules, characterization tests before movement, and repeated focused/bounded validation.
- Documentation accuracy: plan requires rewriting the tracked LaTeX report around what is actually implemented, including examples, tests, current limitations, and future multi-user extension framing.
- Maintainer value: plan discourages blanket comments and asks for targeted comments/docstrings plus a maintainer guide explaining non-obvious release-critical invariants.
- Release management: plan keeps fresh-reader, macOS, minimal-parser-machine, tag approval, and publication approval as manual gates that must not be faked.
- Privacy/data safety: plan excludes private papers, private paths, credentials, provider keys, tokens, generated workspaces, backup archives, `.codex`, `.claude`, caches, `build/`, and `dist/` from commits.

Audit clarification:
- The requested plan path in this pass has the word "maintainability"; no file exists with the misspelled "maintability" variant. The existing plan file is `docs/plans/pre_final_release_maintainability_report_plan_2026-04-29.md`.

Execution boundary for this pass:
- Complete all locally automatable phases.
- Keep refactors conservative and behavior-preserving.
- Record unavailable external validations/approvals as manual blockers rather than attempting or fabricating them.
- Do not create a tag or publish artifacts.

Next safe step:
- Phase 0 baseline characterization and refactor-boundary validation.

Phase 0 baseline characterization:
- Plan: establish release-critical behavior before refactoring.
- Execute: reviewed the plan and baseline release-critical files; treated CLI command names, JSON schemas, gate readiness flags, backup/restore safety, repository hygiene, merge confirmation, and parser limitation wording as stable boundaries.
- Tests:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.62s`.
  - `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.88s`.
  - `git diff --check`: clean.
- Audit: baseline coverage is sufficient to start conservative behavior-preserving refactors; no behavior changes have been made.
- Tidy: no generated evidence or build outputs staged.

Next safe step:
- Phase 1 targeted refactor of release-critical code, starting with CLI organization and preserving command behavior.

Phase 1 targeted refactor:
- Plan: make a small behavior-preserving maintainability improvement instead of a broad pre-release module split.
- Execute:
  - Extracted repository-hygiene CLI parser registration into `_register_repository_hygiene_commands`.
  - Extracted individual Git release CLI parser registration into `_register_individual_git_release_commands`.
  - Added targeted release-safety docstrings/comments for shareable path classification, validation-report local-vs-external gates, workspace merge trust boundary, and backup restore confirmation.
- Tests:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.68s`.
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q`: `6 passed in 0.90s`.
  - `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.96s`.
  - `timeout 180 scripts/run_bounded_tests.sh`: `34 passed in 0.97s`.
  - `git diff --check`: clean.
- Audit: public CLI command names, JSON output shapes, release gate semantics, merge safeguards, and restore safeguards remain unchanged.
- Tidy: no generated artifacts staged; refactor is intentionally narrow.

Next safe step:
- Phase 2 maintainer comments and programmer guide.

Phase 2 maintainer comments and programmer guide:
- Plan: add maintainer-facing guidance without blanket-commenting obvious code.
- Execute:
  - Added `docs/maintainer_guide.md` with release target, module map, trust boundaries, Git-sharing rules, release gate model, validation commands, LaTeX report guidance, and no-commit rules.
  - Linked the maintainer guide from `docs/release_checklist.md`.
  - Phase 1 comments/docstrings cover non-obvious safety invariants in release-critical code.
- Tests:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.94s`.
  - `git diff --check`: clean.
- Audit: guide is scoped to current individual local + Git release and keeps multi-user work as future extension; comments explain safety policy rather than syntax.
- Tidy: no generated or private files staged.

Next safe step:
- Phase 3 rewrite `proposal/research_development_assistant_design.tex` around the implemented release and rebuild or record the PDF status.

Phase 3 LaTeX release report rewrite:
- Plan: replace the old shared-backend monograph framing with a concise release report/manual for the implemented individual local + Git-sharing tool.
- Execute:
  - Rewrote `proposal/research_development_assistant_design.tex` around the current release target, command manual, workspace model, Git sharing, nontrivial showcases, validation evidence, known limitations, maintainer notes, and future multi-user extension.
  - Removed optional LaTeX dependencies on `fancyhdr` and `tcolorbox` after the local TeX engine reported `fancyhdr.sty` missing.
  - Rebuilt `proposal/research_development_assistant_design.pdf` with `pdflatex`; final PDF is 18 pages.
  - Removed `.aux`, `.log`, `.out`, and `.toc` intermediates after build.
- Tests:
  - Initial `timeout 180 pdflatex -interaction=nonstopmode -halt-on-error research_development_assistant_design.tex` failed because local TinyTeX lacked `fancyhdr.sty`.
  - After dependency simplification, two `timeout 180 pdflatex -interaction=nonstopmode -halt-on-error research_development_assistant_design.tex` passes from `proposal/` completed.
  - `pdfinfo proposal/research_development_assistant_design.pdf`: 18 pages, PDF 1.7.
  - `rg` smoke confirmed the report mentions individual local release, Git sharing, future extension, parser scientific accuracy limitation, `WHEEL_PATH`, `synthetic_git_1000`, and the manual blockers.
  - `git diff --check`: clean.
- Audit: report now describes what is implemented today and moves multi-user database/service/RBAC/hosted UI into future extension scope.
- Tidy: TeX intermediates removed; only tracked `.tex` and `.pdf` remain modified.

Next safe step:
- Phase 4 cross-document consistency pass.

Phase 4 cross-document consistency:
- Plan: align release-facing docs after the LaTeX rewrite and pin the current story with docs smoke tests.
- Execute:
  - Rewrote `docs/usage.md` from old POC/v2 scaffold language to current individual local + Git-sharing release usage.
  - Added docs smoke assertions in `tests/integration/test_individual_release_cli.py` for `docs/maintainer_guide.md`, `docs/usage.md`, and `proposal/research_development_assistant_design.tex`.
  - Confirmed release-facing docs keep multi-user database/service/RBAC/hosted UI as future scope, preserve `WHEEL_PATH`, preserve parser scientific-accuracy limitation, and preserve manual blockers.
- Tests:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.87s`.
  - `git diff --check`: clean.
- Audit: docs now tell one coherent release story; no checked release doc presents the current release as a live shared service.
- Tidy: no generated or private files staged.

Next safe step:
- Phase 5 full local validation packet, including artifact build, clean install smoke, release gate, and clean-checkout gate.

Phase 5 full local validation packet:
- Plan: validate the maintainability/report changes as a release packet before committing.
- Execute:
  - Re-ran focused release, industrial CLI, fast, and bounded suites on the current tree.
  - Rebuilt release artifacts with `scripts/build_release_artifacts.sh`.
  - Ran the clean-install smoke against the exact rebuilt wheel via `WHEEL_PATH`.
  - Updated `docs/platform_support.md` and `docs/release_notes_0.1.0.md` to the smoke-tested wheel hash from this final local artifact pass.
  - Ran the individual Git release gate in `/tmp/research-assistant-maintainability-gate`.
- Tests and evidence:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.94s`.
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q`: `6 passed in 1.02s`.
  - `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 1.04s`.
  - `timeout 180 scripts/run_bounded_tests.sh`: `34 passed in 1.10s`.
  - `timeout 300 scripts/build_release_artifacts.sh`: passed; built `research_assistant-0.1.0-py3-none-any.whl`, SHA256 `6e1aa516630ad14bdcfe47b5803070b47007319a8a6600c002946cd26b364670`, size `127955` bytes.
  - `WHEEL_PATH=/home/chakwong/python/ResearchAssistant/dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh`: passed; installed wheel completed `ra --help`, `ra version`, `init`, `doctor`, `demo setup`, `demo run`, and `release-report`.
  - `GATE_ROOT=/tmp/research-assistant-maintainability-gate timeout 300 scripts/run_individual_git_release_gate.sh`: passed with expected blocked gate status.
  - Gate suites inside the release gate: fast `14 passed in 0.98s`, bounded `34 passed in 0.99s`, individual release integration `14 passed in 1.81s`.
  - Gate readiness: `ready_for_limited_individual_pilot: true`, `ready_for_git_shared_research_release: false`, `ready_for_broad_individual_release: false`.
  - Gate blockers: real colleague onboarding, real macOS validation, real minimal parser-tool validation, release-owner tag approval, and publication approval remain manual/unavailable.
  - `git diff --check`: clean.
- Audit:
  - Behavior-preserving code changes remain narrow.
  - Report and release docs describe the implemented individual local + Git-sharing tool first.
  - Generated/parser/benchmark/derivation/traceability/readiness artifacts remain review material.
  - Manual external validation and release-owner approval were not fabricated or waived.
  - The rebuilt wheel hash appears build-output sensitive; the docs now record the exact wheel used for the final local clean-install smoke in this pass.
- Tidy:
  - `dist/` and `build/` were regenerated but remain ignored and must not be committed.
  - `.codex` remains untracked and must not be committed.
  - `.claude/`, `.pytest_cache/`, bytecode caches, and generated test caches remain ignored.

Phase 6 external manual release gates:
- Plan: record non-automatable release gates explicitly.
- Execute: no tag was created and no artifact was published because no release-owner approval was provided.
- Tests: not locally automatable.
- Audit: broad release remains correctly blocked until real fresh-reader onboarding, real macOS validation, real minimal parser-tool machine validation, tag approval, and publication approval are recorded.
- Tidy: no external evidence records were invented.

Next safe step:
- Commit the implementation/docs/plan/reset-memo packet, clone the committed tree locally, run the clean-checkout gate, then update this memo with the clean-checkout evidence and final commit hash.


## Update - pre-final maintainability/report execution completed

Implementation checkpoint:
- Commit: `674cbec Prepare pre-final release maintainability packet`.
- Changed files intentionally included release-critical code comments/refactor, maintainer docs, usage/release docs, the rewritten LaTeX report and PDF, integration docs smoke coverage, this reset memo, and `docs/plans/pre_final_release_maintainability_report_plan_2026-04-29.md`.
- No private papers, private local paths, credentials, provider keys, tokens, `.codex`, `.claude`, caches, bytecode, `build/`, `dist/`, temporary clones, generated workspaces, or backup archives were committed.

Clean-checkout validation after implementation commit:
- Clean local clone: `/tmp/research-assistant-maintainability-clean-674cbec`.
- Clean clone commit: `674cbec`.
- Initial clean-clone `git status --short --ignored`: clean.
- `GATE_ROOT=/tmp/research-assistant-maintainability-clean-gate-674cbec timeout 300 scripts/run_individual_git_release_gate.sh`: completed.
- Clean-checkout gate suites:
  - fast suite: `14 passed in 1.08s`;
  - bounded suite: `34 passed in 0.95s`;
  - individual release integration: `14 passed in 1.75s`.
- Clean-checkout gate status: `blocked`, as expected.
- Clean-checkout readiness:
  - `ready_for_limited_individual_pilot: true`;
  - `ready_for_git_shared_research_release: false`;
  - `ready_for_broad_individual_release: false`.
- Clean-checkout blockers:
  - real fresh-reader onboarding was not completed;
  - real macOS validation was not completed;
  - real minimal parser-tool machine validation was not completed;
  - release-owner tag approval was not provided;
  - release-owner publication approval was not provided.
- Clean-checkout warnings:
  - `release_artifacts_not_built` appears in the clean clone because `dist/` is intentionally ignored and uncommitted;
  - repository-hygiene warnings appear for generated/rebuildable gate evidence in the temporary gate workspace and for strict hygiene outside a Git repository.
- Clean clone post-validation `git status --short --ignored` showed only ignored `.pytest_cache/` and bytecode caches.

Final local source-tree state before this memo checkpoint:
- Working tree has no tracked modifications other than this reset memo update.
- `.codex` remains untracked.
- `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, and `dist/` remain ignored local state.
- No tag was created and no artifact was published.

Final result of this pass:
- All locally automatable phases in the maintainability/report plan are complete.
- The release target remains individual local filesystem storage plus Git-based sharing.
- The multi-user database/service/SSO/RBAC/hosted UI target remains a future extension.
- The final local smoke-tested wheel evidence recorded in release docs is SHA256 `6e1aa516630ad14bdcfe47b5803070b47007319a8a6600c002946cd26b364670`.
- Broad release remains blocked on real external validation and release-owner approval.
- This closing reset memo update is included in the final memo checkpoint commit.


## Update - NeuTra/DSGE showcase enhancement started

New objective:
- Make `proposal/research_development_assistant_design.tex` less skeletal by adding a real colleague-facing showcase: using NeuTra as a seed paper for a DSGE survey chapter on normalizing-flow and neural-transport architectures.
- Update supporting docs/tests only as needed.
- Preserve the current release target: individual local filesystem tool plus Git sharing.
- Do not claim the tool automatically writes, validates, or scientifically approves the survey.

Independent audit before execution:
- Product value: a DSGE/NeuTra survey showcase is useful because local plans already identify NeuTra as a representative validation paper and identify chapter-writing/literature traversal as a real pain point.
- Accuracy: the showcase must describe evidence organization, citation traversal, review notes, architecture taxonomy, links to chapter sections/code, and exportable context; it must not claim automatic correctness.
- Scope: no multi-user server/database/hosted UI requirement should be introduced.
- Privacy: examples must use public paper titles and placeholder paths only; no private PDFs, private local paths, or unpublished notes should be exposed.
- Implementation risk: documentation-only changes are appropriate; no code behavior should change.

Execution plan:
- Phase 0: baseline/read current report and NeuTra references.
- Phase 1: add a substantial NeuTra/DSGE showcase section to the LaTeX report.
- Phase 2: add a concise usage-doc pointer and docs smoke assertions so the showcase does not regress.
- Phase 3: rebuild the PDF if local TeX succeeds; remove intermediates.
- Phase 4: run focused validation, audit, tidy, update this memo, and commit.

Phase 0 baseline:
- Plan: locate existing NeuTra/normalizing-flow references and confirm the report gap.
- Execute: reviewed `proposal/research_development_assistant_design.tex`, `docs/test_plan.md`, `docs/validation_run_log.md`, `docs/hardening_plan.md`, `README.md`, and the docs smoke test.
- Evidence:
  - `docs/test_plan.md` lists "NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport" as a directly relevant representative paper.
  - `docs/validation_run_log.md` records NeuTra query-only ingest and metadata-hardening evidence.
  - `docs/hardening_plan.md` says a NeuTra seed should support first-pass literature graph traversal for citing papers, second-order papers, criticisms, remedies, and applications.
  - The current report's "Nontrivial Showcases" chapter is mostly release mechanics.
- Audit: a real research showcase is missing and can be added without changing release scope or behavior.
- Tidy: no files changed yet for this phase.

Phase 1 report showcase:
- Plan: add a substantial real research scenario to the report's "Nontrivial Showcases" chapter.
- Execute: added "DSGE survey chapter from a NeuTra seed" to `proposal/research_development_assistant_design.tex`.
- Content added:
  - NeuTra as the seed paper for a DSGE survey chapter on normalizing-flow and neural-transport architectures.
  - Architecture taxonomy examples: transport maps, neural reparameterizations, planar/radial/autoregressive/coupling/spline/continuous normalizing flows, HMC and variational-inference relevance, criticisms, failure modes, remedies, code experiments, and derivation notes.
  - Current CLI examples for ingest, discovery, citation neighborhood, audit notes, links, derivation worksheet creation, synthesis proposal, traceability, review approval, and context export.
- Audit: the text is motivational but keeps outputs as review material and says the tool does not replace the researcher's judgment.
- Tidy: no private paths or private papers were referenced.

Phase 2 usage pointer and docs smoke:
- Plan: expose the showcase outside the PDF and protect it with focused docs assertions.
- Execute:
  - Added "Showcase: NeuTra To DSGE Survey Chapter" to `docs/usage.md`.
  - Added docs smoke assertions in `tests/integration/test_individual_release_cli.py` for the NeuTra/DSGE showcase and normalizing-flow wording.
- Audit: examples use existing CLI commands; the usage doc says the goal is a reviewable evidence trail, not automatic survey writing.
- Tidy: no generated files staged.

Phase 3 PDF rebuild:
- Plan: rebuild the tracked report PDF after the showcase addition.
- Execute:
  - Ran two `pdflatex` passes from `proposal/`.
  - Removed `.aux`, `.log`, `.out`, and `.toc` intermediates.
- Evidence:
  - `timeout 180 pdflatex -interaction=nonstopmode -halt-on-error research_development_assistant_design.tex`: passed twice.
  - `pdfinfo proposal/research_development_assistant_design.pdf`: 20 pages, PDF 1.7, size `215486` bytes.
  - LaTeX reported a non-fatal overfull hbox near `synthetic_git_1000`; this was not introduced as a release blocker.
- Audit: the PDF contains the new showcase and remains built from the tracked `.tex`.
- Tidy: TeX intermediates removed.

Phase 4 validation, audit, and tidy:
- Plan: verify the docs/report-only change and prepare a clean commit.
- Execute:
  - Ran focused individual release integration tests after fixing a brittle exact-string docs assertion caused by a line wrap in the LaTeX source.
  - Ran fast tests.
  - Ran whitespace diff checks and status review.
- Evidence:
  - Initial `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: failed once because the asserted phrase "normalizing-flow and neural-transport architectures" wrapped across a line in the report source.
  - Fixed the assertion to check `normalizing-flow` and `neural-transport architectures` separately.
  - Final `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.68s`.
  - `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.95s`.
  - `git diff --check`: clean.
- Audit:
  - No code behavior changed.
  - The added showcase is grounded in public paper titles and existing local plan/test references.
  - The report remains honest that the tool builds a reviewable evidence trail and does not replace researcher judgment.
  - Current release scope remains individual local filesystem plus Git sharing; multi-user platform work is still future extension.
- Tidy:
  - `.codex` remains untracked and uncommitted.
  - `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, and `dist/` remain ignored and uncommitted.
  - `docs/plans/neutra_dsge_showcase_report_plan_2026-04-29.md` is ignored by pattern and must be force-staged intentionally if committed.

Next safe step:
- Commit the showcase report/docs/test/reset-memo packet.
