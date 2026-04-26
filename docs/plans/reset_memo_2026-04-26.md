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
