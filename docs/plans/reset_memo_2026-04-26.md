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


## Update — design document rewrite execution started

New objective:
- rewrite `proposal/research_development_assistant_design.tex` into a colleague-facing adoption proposal that is more readable, more appealing, and more persuasive while remaining faithful to the bounded individual local release.

Execution plan written to:
- `docs/plans/design_doc_rewrite_execution_plan_2026-04-29.md`

Independent plan audit result:
- The initial rewrite plan was directionally correct but too subjective for autonomous execution.
- The plan was strengthened before execution to add:
  - normative truth-source hierarchy;
  - a keep/cut/move/compress inventory phase;
  - measurable acceptance criteria;
  - command-verification checks against current docs;
  - claim-audit checks against product posture and known limitations;
  - privacy-safe example rules;
  - intermediate compile checks and PDF inspection checkpoints.

Phase 0 status:
- In progress.

Phase 0 rewrite boundary:
- The package remains an individual local, private, offline/provider-disabled default workflow with Git-based sharing.
- The proposal must not reintroduce hosted/shared-platform framing as the main story.
- The document must lead with realistic day-one value: ingest, inspect, review, discover, and export trusted context.
- Generated/parser/benchmark/derivation/traceability/governance/readiness artifacts remain review material, not scientific approval.
- Example commands must be real current CLI commands documented in `README.md`, `docs/usage.md`, or `docs/workflows/individual_research_workflow.md`.
- Example paths must stay privacy-safe (`/tmp/...`, `~/research-assistant-workspace`, generic placeholders, or public papers only).

Phase 0 current-document inventory:
- Keep with rewrite:
  - current release scope and trust-boundary language;
  - local workspace model;
  - source-first and parser-limit posture;
  - Git-sharing explanation;
  - realistic NeuTra/DSGE-style example material where it remains public and bounded.
- Compress:
  - command-manual sections;
  - validation evidence sections;
  - technical workspace inventory detail;
  - future-extension discussion.
- Move later or appendix:
  - maintainer notes;
  - release checklist summary;
  - operational release-validation packet detail;
  - any release-owner/manual-gate specifics that are not central to adoption.
- Remove or heavily demote:
  - report/manual-first framing in title and opening narrative;
  - any lingering future-extension emphasis in the title/subtitle;
  - any content that makes scaffolding/governance artifacts look like the main reason to adopt the package.

Phase 0 validation:
- Read and cross-checked:
  - `proposal/research_development_assistant_design.tex`
  - `README.md`
  - `docs/usage.md`
  - `docs/product_spec.md`
  - `docs/known_limitations.md`
  - `docs/workflows/individual_research_workflow.md`
  - `docs/support.md`
  - `docs/installation.md`
  - `docs/quickstart.md`
- No code or build test required for Phase 0.

Phase 0 audit as another developer:
- The rewrite boundary is now explicit enough to prevent accidental scope drift.
- The current document inventory preserves trust-boundary material while giving permission to demote release-ops-heavy sections.
- The main remaining execution risk is not scope confusion; it is preserving enough technical credibility while simplifying the narrative.

Phase 0 tidy result:
- No generated outputs created.
- No private paths or release artifacts introduced.

Next safe step:
- Execute Phase 1 by restructuring the LaTeX document into the new colleague-facing narrative order, then run an intermediate compile check.

## Update — design document rewrite Phase 1 completed

Phase 1 plan for the phase:
- Restructure the proposal so the top-level narrative becomes colleague-facing rather than release-report-first.
- Move practical adoption material ahead of operational release material.
- Remove maintainer-only and release-checklist-heavy chapters from the main narrative.

Phase 1 execution result:
- Rewrote `proposal/research_development_assistant_design.tex` into a new chapter flow centered on:
  - executive summary;
  - concrete workflow problem;
  - current-release package value;
  - local-first design rationale;
  - assistant-fit explanation;
  - concrete example workflows;
  - scope boundaries;
  - technical credibility;
  - practical adoption path;
  - skeptical questions;
  - bounded future extensions.
- Removed maintainer-notes and release-checklist-summary chapters from the main narrative.
- Moved Git-sharing and pilot-release maturity details into a short appendix-style operational section.
- Replaced the title/subtitle framing so it no longer foregrounds release review or future-extension planning.

Phase 1 focused validation:
- Structural source check passed:
  - executive summary present;
  - concrete workflow problem chapter present;
  - concrete examples chapter present;
  - old future-extension title framing removed;
  - maintainer-notes chapter removed;
  - release-checklist-summary chapter removed.

Phase 1 audit as another developer:
- The document now reads structurally like a colleague-facing proposal rather than a maintainer release packet.
- Future-platform material no longer dominates the opening or title.
- The main remaining risk is preserving enough technical specificity and strong examples so the new structure does not become too generic.

Phase 1 tidy result:
- No generated files created.
- No private or non-shareable paths introduced.

Next safe step:
- Execute Phase 2 by strengthening the opening pages and then audit them against `README.md`, `docs/product_spec.md`, and `docs/known_limitations.md` before compile validation.

## Update — design document rewrite Phase 2 completed

Phase 2 plan for the phase:
- Make the first pages strong enough for colleague adoption by clearly stating scope, workflow problem, value proposition, and trust boundary.
- Ensure the title/subtitle and opening sections stop sounding like a release-review manual.

Phase 2 execution result:
- Rewrote the title to `A Local-First Research Workflow For Papers, Code, and Technical Writing`.
- Recast the opening as a colleague-adoption proposal with:
  - a practical value proposition;
  - explicit local-first scope;
  - clear non-goals;
  - an upfront explanation that the package does not replace judgment.
- Moved trust-boundary and workflow-problem language into the opening chapters instead of burying them later.

Phase 2 focused validation:
- Opening-scope audit passed:
  - one-researcher-first language present;
  - local-filesystem language present;
  - Git-based-sharing language present;
  - provider-disabled/offline-default posture present;
  - review-material boundary present;
  - non-hosted/shared-backend posture still explicit.

Phase 2 audit as another developer:
- The opening is now much more persuasive for a skeptical peer because it explains what problem the package solves before listing commands.
- The title no longer over-centers release operations.
- The main remaining risk is that example quality must now carry more of the persuasion burden; strong workflow examples are therefore critical.

Phase 2 tidy result:
- No generated files created.
- No private or non-shareable paths introduced.

Next safe step:
- Execute Phase 3 by rewriting the examples, building a command-verification checklist, and keeping all examples privacy-safe and review-boundary-aware.

## Update — design document rewrite Phase 3 completed

Phase 3 plan for the phase:
- Replace weaker release-ops-heavy examples with 2–3 strong colleague-facing examples.
- Use only current documented commands, privacy-safe paths, and explicit review-boundary language.

Phase 3 execution result:
- Replaced the previous long NeuTra/DSGE showcase and release-packet-heavy example sequence with three compact primary examples:
  1. ingest a paper and inspect what is safe to trust;
  2. expand nearby literature without losing the evidence trail;
  3. export trusted context for writing or coding.
- Kept examples focused on realistic day-one value rather than governance/release scaffolding.
- Used only privacy-safe paths such as `~/research-assistant-workspace` and `/tmp/paper_context.json`.
- Kept explicit review-boundary language in every example section.

Phase 3 focused validation:
- Command-verification checklist passed for primary examples:
  - `ra --root ~/research-assistant-workspace init`
  - `ra --root ~/research-assistant-workspace ingest --pdf ~/papers/example.pdf --query "paper title"`
  - `ra --root ~/research-assistant-workspace show --paper-id paper_example`
  - `ra --root ~/research-assistant-workspace review-show --paper-id paper_example`
  - `ra --root ~/research-assistant-workspace find --query "Neural Transport HMC"`
  - `ra --root ~/research-assistant-workspace citation-neighborhood --paper-id neutra_hmc`
  - `ra --root ~/research-assistant-workspace discover --query "transport maps hmc"`
  - `ra --root ~/research-assistant-workspace inbox-list`
  - `ra --root ~/research-assistant-workspace review-mark --paper-id neutra_hmc --status approved`
  - `ra --root ~/research-assistant-workspace export-context --review-status approved --output /tmp/paper_context.json`
- All commands retained in the primary examples are real current commands documented in the repo docs.

Phase 3 audit as another developer:
- The examples are materially better for persuasion because they now reflect realistic first-use workflows instead of maintainership or release gating.
- The examples remain honest because they explain why the outputs are useful without claiming automatic correctness.
- The remaining risk is that too much operational material could still linger later in the document if not compressed further.

Phase 3 tidy result:
- No generated files created.
- No private or non-shareable paths introduced.

Next safe step:
- Execute Phase 4 by compressing or demoting remaining operational and maintainer-heavy material while preserving adoption-critical truth and technical credibility.

## Update — design document rewrite Phase 4 completed

Phase 4 plan for the phase:
- Demote remaining operational, maintainer, and release-validation-heavy material.
- Keep only a brief appendix-style operational note and a concise pilot-maturity statement.

Phase 4 execution result:
- Removed the old `Validation Evidence`, `Maintainer Notes`, and `Release Checklist Summary` chapters entirely from the main narrative.
- Collapsed remaining operational material into a short appendix-style `Operational Notes Kept Briefly` chapter.
- Kept only one bounded future-extension chapter and removed broader repeated operational framing.
- Preserved Git-sharing and pilot-maturity content only where it still supports truthful adoption decisions.

Phase 4 focused validation:
- Operational-content audit passed:
  - one concise operational appendix present;
  - no `Validation Evidence` chapter remains;
  - no `Maintainer Notes` chapter remains;
  - no `Release Checklist Summary` chapter remains;
  - exactly one `Future Extensions` chapter remains.

Phase 4 audit as another developer:
- The main body is now clearly centered on adoption rather than release operations.
- The remaining appendix content is brief enough to preserve truth without hijacking the narrative.
- The remaining risk is now mostly one of balance: the technical-credibility section must be strong enough that the document does not feel oversimplified.

Phase 4 tidy result:
- No generated files created.
- No private or non-shareable paths introduced.

Next safe step:
- Execute Phase 5 by auditing and, if needed, strengthening the technical-credibility section against the product promises and known limitations.

## Update — design document rewrite Phase 5 completed

Phase 5 plan for the phase:
- Ensure the simplified document still feels technically rigorous.
- Audit the technical-credibility section directly against product promises and known limitations.

Phase 5 execution result:
- Kept a bounded technical-credibility chapter focused on:
  - structured local artifacts and provenance;
  - source-first arXiv audit posture;
  - explicit parser limits;
  - why the package complements rather than replaces coding assistants.
- Preserved the package’s conservative trust posture instead of switching to marketing-style overclaim.

Phase 5 focused validation:
- Technical-credibility audit passed:
  - structured local artifacts and provenance section present;
  - source-first arXiv audit posture section present;
  - explicit parser limits section present;
  - assistant-complement section present;
  - source-first promise still stated;
  - conservative posture still stated;
  - provenance language still present;
  - visible remote-enrichment degradation still described;
  - no-silent-final-moves concept preserved.

Phase 5 audit as another developer:
- The document now keeps enough technical specificity to satisfy a serious reader without collapsing back into a monograph.
- The credibility section is especially strong because it explains why the design choices are trustworthy rather than merely listing features.
- The remaining risk is now mostly mechanical: perform the final readability/claim audit carefully so no contradictions or LaTeX issues survive.

Phase 5 tidy result:
- No generated files created.
- No private or non-shareable paths introduced.

Next safe step:
- Execute Phase 6 by doing the final readability pass, running the claim-audit matrix, and then performing an intermediate compile check.

## Update — design document rewrite Phase 6 completed

Phase 6 plan for the phase:
- Perform the final readability pass and run an explicit claim audit against the package posture.
- Ensure the simplified proposal still states the correct target user, trust boundary, sharing model, provider posture, and maturity boundary.

Phase 6 execution result:
- Completed the readability-focused rewrite pass already reflected in the new proposal structure and wording.
- Retained direct language about current scope, trust boundaries, and pilot maturity instead of softening those claims.
- Kept LaTeX structure simple and removed the old cluttered report/manual framing.

Phase 6 focused validation:
- Claim-audit matrix passed for the rewritten proposal:
  - target user = local researcher;
  - storage model = local filesystem;
  - sharing model = Git-based;
  - provider default posture = offline/provider-disabled by default;
  - parser trust posture = parser limits remain explicit;
  - generated artifact trust posture = review material only;
  - release maturity = pilot/manual-gate language retained;
  - platform posture = no current hosted UI/shared service story.

Phase 6 audit as another developer:
- The rewritten proposal now stays aligned with the product posture instead of drifting into a broader platform pitch.
- The wording is materially cleaner and easier to scan.
- The next remaining risk is mechanical correctness: the document still needs full LaTeX build validation and PDF inspection.

Phase 6 tidy result:
- No generated files created.
- No private or non-shareable paths introduced.

Next safe step:
- Execute Phase 7 by compiling the LaTeX document, rerunning the build if needed, and inspecting the resulting PDF against the checklist.

## Update — design document rewrite resumed plan audit completed

Resumed audit plan:
- Treat the already recorded Phases 0 through 6 as implementation evidence.
- Re-audit `docs/plans/design_doc_rewrite_execution_plan_2026-04-29.md` as another developer before completing the remaining work.
- Confirm that no missing plan point blocks autonomous completion.

Resumed independent audit result:
- The plan remains faithful to the individual local filesystem release target.
- The plan has explicit controls against overclaiming hosted, database, SSO/RBAC, real-time collaboration, parser-certification, or generated-artifact approval capabilities.
- The example strategy is adequate because it requires current CLI commands, privacy-safe paths, and review-boundary language.
- Verification coverage is adequate for a documentation/report rewrite: source claim audit, command verification, LaTeX build, rendered-PDF inspection, diff hygiene, and commit.
- One non-blocking clarification was added to the plan: if the tracked PDF changes after a validated LaTeX build, the rebuilt PDF must be reviewed and committed with the source and reset memo.

Resumed independent audit conclusion:
- No blocking plan defects remain.
- The remaining executable work is Phase 7 compile/PDF validation and Phase 8 final audit, tidy, reset memo, and commit.

Tidy result:
- No private paths, credentials, raw papers, caches, or auxiliary LaTeX files were introduced.
- Temporary build outputs remain outside the repository.

Next safe step:
- Execute Phase 7 by rebuilding `proposal/research_development_assistant_design.tex`, inspecting the rendered PDF, and replacing the tracked PDF only after validation passes.

## Update — design document rewrite Phase 7 completed

Phase 7 plan for the phase:
- Compile the rewritten LaTeX report in a temporary build directory.
- Rerun LaTeX if outlines or table of contents require it.
- Inspect the rendered PDF for title/subtitle accuracy, table-of-contents order, first-page scope fidelity, readable example sections, limitations placement, future-scope placement, and pilot-maturity language.

Phase 7 execution result:
- Ran:
  - `timeout 120 pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp/research-assistant-design-build proposal/research_development_assistant_design.tex`
  - repeated the same command after the first build requested outline/table-of-contents stabilization.
- Inspected build diagnostics with:
  - `grep -n "Warning\|Error\|Fatal\|Overfull\|Underfull\|Rerun" /tmp/research-assistant-design-build/research_development_assistant_design.log`
  - only the loaded `rerunfilecheck` package line remained; no fatal errors and no overfull/underfull layout warnings were reported.
- Extracted PDF text with:
  - `pdftotext /tmp/research-assistant-design-build/research_development_assistant_design.pdf /tmp/research-assistant-design-build/research_development_assistant_design.txt`
- Inspected PDF metadata with:
  - `pdfinfo /tmp/research-assistant-design-build/research_development_assistant_design.pdf`
  - result: 21 pages, A4, unencrypted.
- Copied the validated PDF into `proposal/research_development_assistant_design.pdf`.

Phase 7 focused validation:
- Title/subtitle check passed:
  - `Research Assistant`
  - `A Local-First Research Workflow For Papers, Code, and Technical Writing`
  - `Colleague Adoption Proposal`
- Table-of-contents order check passed:
  - executive summary;
  - concrete workflow problem;
  - current package capabilities;
  - local-first rationale;
  - assistant-workflow fit;
  - concrete examples;
  - scope boundaries and non-goals;
  - technical credibility;
  - adoption path;
  - skeptical Q&A;
  - future extensions;
  - brief operational appendix.
- Example-section inspection passed:
  - three primary examples are present and readable;
  - commands use `~/ra-workspace` or `/tmp/...` paths;
  - review-boundary language remains explicit.
- Scope and limitation inspection passed:
  - one local researcher, local filesystem, offline/provider-disabled defaults, Git-based sharing, and review-material boundaries appear in the first pages;
  - hosted/database/shared-platform language appears as non-goal or future scope;
  - real fresh-reader, macOS, and minimal parser-tool validation remain manual release gates.

Phase 7 audit as another developer:
- The rebuilt PDF is acceptable for a colleague-facing adoption proposal.
- The rendered document is more persuasive than the previous skeletal report while remaining conservative about current capabilities.
- The narrow listing cleanup improved command readability without changing product claims or inventing commands.

Phase 7 tidy result:
- LaTeX auxiliary files stayed under `/tmp/research-assistant-design-build`.
- The only repository PDF update is the intentionally refreshed tracked PDF.
- No private or non-shareable files were added.

Next safe step:
- Execute Phase 8 by running final diff hygiene, staging intentional files, committing them, and recording final reset-memo status.

## Update — design document rewrite Phase 8 completed

Phase 8 plan for the phase:
- Final-audit the report as another developer.
- Confirm the rendered report stays in scope, has honest limitations, and contains strong current-release examples.
- Run final diff hygiene.
- Commit only intentional files.

Phase 8 final audit result:
- A skeptical colleague would now see a clear reason to try the package: it preserves local research continuity between papers, code, and writing without pretending to automate judgment.
- The document remains aligned with the current release target: individual local filesystem use with Git-based sharing.
- Limitations are stated honestly, including parser limits, generated-artifact review boundaries, synthetic performance evidence, and remaining manual release gates.
- The future-extension section is correctly demoted and no longer drives the opening story.
- The PDF was rebuilt from the checked source and inspected before staging.

Phase 8 validation:
- `git diff --check` passed before staging.
- `git status --short` showed only intentional tracked documentation/report changes plus known untracked local `.codex` tooling state before staging.
- The ignored plan file was force-staged intentionally because it now contains the required resumed independent audit evidence for this execution round.

Phase 8 tidy result:
- No caches, bytecode, build directories, distribution artifacts, private papers, credentials, `.claude/`, or `.codex` content were staged.
- Temporary LaTeX artifacts remain outside the repository under `/tmp/research-assistant-design-build`.

Completion status:
- The design-document rewrite execution plan has been audited.
- Phases 7 and 8 have been completed after the already recorded Phases 0 through 6.
- The proposal source and PDF are updated and validated.
- The next action is to create the requested git commit.

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


## Update - NeuTra/DSGE showcase enhancement completed

Implementation commit:
- `caa8584 Add NeuTra DSGE showcase to release report`.

What changed:
- Added `docs/plans/neutra_dsge_showcase_report_plan_2026-04-29.md`.
- Added a substantial NeuTra-seeded DSGE normalizing-flow survey showcase to `proposal/research_development_assistant_design.tex`.
- Rebuilt `proposal/research_development_assistant_design.pdf`; final PDF is 20 pages.
- Added a shorter usage-doc showcase in `docs/usage.md`.
- Added docs smoke assertions for the showcase in `tests/integration/test_individual_release_cli.py`.
- Updated this reset memo with phase-by-phase plan, execution, validation, audit, tidy notes, and blockers.

Validation:
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.68s`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.95s`.
- Two `pdflatex` passes from `proposal/`: passed.
- `pdfinfo proposal/research_development_assistant_design.pdf`: 20 pages, PDF 1.7, size `215486` bytes.
- `git diff --check`: clean before commit.

Audit:
- No code behavior changed.
- The showcase is grounded in public paper titles and existing local project notes about NeuTra validation and literature traversal.
- The text is intentionally adoption-oriented but still honest: the tool builds a reviewable evidence trail for survey writing and does not replace researcher judgment.
- Parser/generated/review artifacts remain review material.
- Current release scope remains individual local filesystem plus Git sharing.
- Multi-user database/service/SSO/RBAC/hosted UI work remains future extension.

Remaining local state:
- `.codex` remains untracked.
- `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, and `dist/` remain ignored and uncommitted.
- No tag was created and no artifact was published.

Next safe step:
- Commit this final reset memo update as the closeout checkpoint.


## Update - release-audit second-agent request execution started

New objective:
- Execute the user's requested second-agent release-audit review and gap closure.
- User referenced `release_audit_second_agent_review_request_2026-04-20.md`; no file with that date exists in the workspace.
- Available matching request: `docs/proposal/release_audit_second_agent_review_request_2026-04-29.md`.
- Available audit under review: `docs/plans/whole_codebase_release_audit_2026-04-29.md`.

Baseline:
- Latest commit before this pass: `c1cf81d Record NeuTra DSGE showcase checkpoint`.
- Working tree had only expected local state: `.codex` untracked; `.claude/`, caches, bytecode, `build/`, and `dist/` ignored; plus untracked/ignored audit-plan files.

Independent audit of the audit request:
- The audit scope is correct: current release is individual local filesystem plus Git sharing, not the future multi-user platform.
- The strongest concrete findings are valid on inspection:
  - `scripts/run_tests.sh` hard-codes `/home/chakwong/research-assistant` and does not set `PYTHONPATH=src`.
  - `tests/integration/test_cli_commands.py` uses a hard-coded personal Palazzo PDF path outside the repo.
  - `docs/release_notes_0.1.0.md` says `Date: 2026-04-28` while describing a 2026-04-29 artifact.
  - Release checklist/gate wording can better show that representative performance evidence must be run before validation report/gate-build.
- The manual validation blockers are expected release blockers, not code bugs.
- The branch-hygiene finding is partly stale: previous doc/report changes are now committed, but `.codex` remains untracked and local caches/build outputs remain ignored.

Executable plan:
- Added `docs/plans/release_audit_gap_closure_plan_2026-04-29.md`.
- Phases:
  - Phase 0: baseline and claim verification.
  - Phase 1: make `scripts/run_tests.sh` portable.
  - Phase 2: remove personal PDF dependency from the integration test.
  - Phase 3: align release notes/checklist evidence wording.
  - Phase 4: run validation, audit, tidy.
  - Phase 5: commit implementation and final memo.

Phase 0 baseline and claim verification:
- Plan: verify audit claims against current files before modifying anything.
- Execute: inspected the second-agent request, whole-codebase audit, `scripts/run_tests.sh`, `tests/integration/test_cli_commands.py`, `docs/release_notes_0.1.0.md`, and `docs/release_checklist.md`.
- Evidence:
  - `scripts/run_tests.sh` still used a hard-coded absolute root and no `PYTHONPATH`.
  - `test_cli_ingest_palazzo_uses_parser_consensus` still referenced `/home/chakwong/research-assistant/local_research/papers/raw/...pdf`.
  - Release notes still mixed 2026-04-28 document date with 2026-04-29 artifact evidence.
  - Release checklist included performance commands but did not explicitly state they are required before `validation-report`/`gate-build`.
- Audit: the audit is substantially correct and should be executed as release-gap closure, with the branch-hygiene item updated to current local state.
- Tidy: no private/generated files staged.

Phase 1 portable full test script:
- Plan: normalize `scripts/run_tests.sh` to the same repo-local pattern as other release scripts.
- Execute:
  - Derived `ROOT` from the script location.
  - Exported `PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"`.
  - Added `TIMEOUT_SECONDS` with default `300`.
  - Wrapped the full unit/integration pytest command in `timeout`.
- Focused test: deferred to Phase 4 full script execution.
- Audit: this removes the hard-coded maintainer-local path and makes the official full test script usable from a clean checkout.
- Tidy: no generated files created.

Phase 2 remove personal PDF dependency:
- Plan: preserve parser-consensus precedence coverage without depending on a private PDF outside the repo.
- Execute:
  - Replaced the hard-coded Palazzo PDF path with a temporary sanitized fixture file under `tmp_path`.
  - Monkeypatched `cli.extract_pdf_text` and `cli.parse_with_all` to provide deterministic parser-consensus evidence.
  - Kept the existing assertions that metadata and summary identity come from parser consensus and require manual review.
- Test:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus -q`: `1 passed in 0.15s`.
- Audit: the test no longer leaks or depends on private local paper storage, and still covers the intended release-critical parser-consensus behavior.
- Tidy: temporary fixture is created only inside pytest `tmp_path`.

Phase 3 release notes and checklist alignment:
- Plan: make the release evidence wording internally current and make performance evidence ordering explicit.
- Execute:
  - Updated `docs/release_notes_0.1.0.md` date to `2026-04-29`.
  - Clarified the artifact as the final local 2026-04-29 validation-pass artifact.
  - Added wording that performance commands must run before `validation-report` and `gate-build`.
  - Added the same ordering warning to `docs/release_checklist.md`.
- Audit: docs remain pilot-scoped and keep external/manual blockers visible.
- Tidy: no generated files created.

Phase 4 validation, audit, and tidy:
- Plan: run the audit-plan validation packet after the portability, test-fixture, and docs changes.
- Execute:
  - Ran affected integration coverage for `test_cli_commands.py` and `test_industrial_platform_cli.py`.
  - Ran the now-portable `scripts/run_tests.sh`.
  - Ran individual release integration tests.
  - Ran the fast test script.
  - Ran `git diff --check` and status review.
- Evidence:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_cli_commands.py tests/integration/test_industrial_platform_cli.py -q`: `26 passed in 1.92s`.
  - `timeout 180 scripts/run_tests.sh`: `139 passed in 4.72s`.
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.80s`.
  - `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.93s`.
  - `git diff --check`: clean.
- Audit:
  - The two concrete clean-checkout reproducibility blockers are fixed.
  - The rewritten review request now points to the executable plan instead of remaining a stale read-only request.
  - Release docs now consistently use the 2026-04-29 candidate date/evidence wording and make performance evidence ordering explicit.
  - Broad release remains correctly blocked on real external/manual validation and release-owner approvals.
- Tidy:
  - `.codex` remains untracked and uncommitted.
  - `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, `dist/`, and test cache directories remain ignored and uncommitted.
  - `docs/plans/release_audit_gap_closure_plan_2026-04-29.md` is ignored by pattern and must be force-staged intentionally.
  - `docs/plans/whole_codebase_release_audit_2026-04-29.md` remains an ignored local audit input and is not staged in this pass.

Next safe step:
- Commit the audit gap closure implementation packet, then add a final reset memo closeout.


## Update - release-audit second-agent request execution completed

Implementation commit:
- `8a53d77 Close release audit reproducibility gaps`.

What changed:
- Rewrote `docs/proposal/release_audit_second_agent_review_request_2026-04-29.md` from a read-only review request into a second-agent review and execution plan.
- Added `docs/plans/release_audit_gap_closure_plan_2026-04-29.md`.
- Made `scripts/run_tests.sh` repo-portable, `PYTHONPATH=src` aware, and bounded by `timeout`.
- Replaced the hard-coded personal Palazzo PDF dependency in `tests/integration/test_cli_commands.py` with a temporary sanitized fixture and deterministic monkeypatched parser/extractor output.
- Updated `docs/release_notes_0.1.0.md` to the 2026-04-29 candidate date/evidence wording.
- Updated `docs/release_checklist.md` to state that performance evidence must run before `validation-report` and `gate-build`.

Validation:
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_cli_commands.py tests/integration/test_industrial_platform_cli.py -q`: `26 passed in 1.92s`.
- `timeout 180 scripts/run_tests.sh`: `139 passed in 4.72s`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.80s`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 0.93s`.
- `git diff --check`: clean before commit.

Final audit:
- The review request's major concrete findings were correct and are now addressed locally.
- The broad release is still correctly blocked on real fresh-reader onboarding, real macOS validation, real minimal parser-tool machine validation, release-owner tag approval, and publication approval.
- `docs/plans/whole_codebase_release_audit_2026-04-29.md` remains an ignored local audit input and was not committed in this pass.
- No tag was created and no artifact was published.

Remaining local state:
- `.codex` remains untracked.
- `.claude/`, `.pytest_cache/`, bytecode caches, `build/`, `dist/`, and test cache directories remain ignored and uncommitted.

This closing reset memo update is included in the final memo checkpoint commit.


## Update - final release readiness closure started

New objective:
- Execute `docs/plans/final_release_readiness_closure_plan_2026-04-29.md` to close the remaining individual-release gaps where possible and record true blockers where human/external evidence is unavailable.

Non-negotiable boundary:
- Current release remains an individual local filesystem tool with Git-based sharing.
- Multi-user database/service/SSO/RBAC/hosted UI work remains future scope.
- Real fresh-reader onboarding, real macOS validation, real minimal-parser-tool validation, tag approval, and publication approval must not be faked.
- No tags or publication will be created without explicit release-owner approval.

Independent plan audit:
- The plan correctly separates agent-executable gaps from human/external blockers.
- The plan preserves the individual local/Git release scope and does not reframe v0.1 as the older industrial/shared-platform release.
- Tagging and publication are guarded by explicit approval requirements.
- Artifact hashes are intentionally regenerated only after final artifact build and clean-install smoke.
- Private/generated/local-only files are explicitly excluded from commits.
- Validation commands are bounded with `timeout`.
- Audit correction applied before execution:
  - Phase 0 now records that local `main` is ahead of `origin/main` but defers push until after the final release-readiness commit.
  - Phase 5 now uses the shell-safe `env WHEEL_PATH=... timeout ...` command form for clean-install smoke.

Phase 0 plan for the phase:
- Establish current commit, remote state, local ignored/untracked state, and scope lock before editing validation docs.

Phase 0 execution result:
- Current `HEAD`: `f31d986d2afd186b7590865c3d9c5a85df78fdc0`.
- Current `origin/main`: `eeb139dd6aa5e5373a9693bd7a4688404af04564`.
- Branch status: `main...origin/main [ahead 20]`.
- Remote: `origin https://github.com/chakkeiwong/ResearchAssistant`.
- Local untracked/ignored state:
  - `.codex` untracked and must not be committed;
  - `.claude/`, `.pytest_cache/`, `build/`, `dist/`, bytecode caches, and local audit inputs remain ignored.
- Scope lock checked in:
  - `docs/release_notes_0.1.0.md`;
  - `docs/known_limitations.md`;
  - `docs/proposal/individual_git_release_target.md`.

Phase 0 validation:
- `git diff --check`: passed.
- Scope search confirmed individual local/Git posture and explicit non-goals for shared database, hosted UI, SSO/RBAC, and publication approval.

Phase 0 audit as another developer:
- Baseline is suitable for continuing local release-readiness work.
- Remote synchronization is not complete, but pushing is correctly deferred until after this execution round commits its changes.
- The release remains pilot-scoped until real external validation and approvals exist.

Phase 0 tidy result:
- No generated outputs created.
- No private/generated files staged.

Next safe step:
- Execute Phase 1 by cleaning stale validation scripts and validation docs, then run parser preflight, the deterministic Palazzo parser-consensus regression, full tests, and diff hygiene.

## Update - final release readiness closure Phase 1 completed

Phase 1 plan for the phase:
- Remove maintainer-local validation assumptions from parser preflight and clean-ingest helper scripts.
- Replace the old private-PDF Palazzo validation path with the deterministic sanitized pytest regression.
- Update validation docs and product acceptance criteria to describe portable commands.
- Run focused validation and the full deterministic suite.

Phase 1 execution result:
- Updated `scripts/run_parser_preflight.sh` to:
  - derive `ROOT` from the script location;
  - export repo-local `PYTHONPATH`;
  - use bounded `timeout` calls;
  - run repo-local CLI commands through `python -m research_assistant.cli` so the script works even when `ra` is not installed on `PATH`.
- Replaced `scripts/run_clean_ingest_palazzo.sh` with a deterministic pytest wrapper for `tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus`.
- Updated:
  - `docs/validation_scripts.md`;
  - `docs/product_spec.md`;
  - `README.md`.
- Restored a concise NeuTra/DSGE showcase in `proposal/research_development_assistant_design.tex` because the release docs smoke test correctly protects that adoption showcase.
- Hardened brittle report-source assertions in `tests/integration/test_individual_release_cli.py` so they survive LaTeX line wrapping while preserving the intended checks.

Phase 1 validation:
- Initial `timeout 120 scripts/run_parser_preflight.sh` failed because `ra` was not on `PATH`; this exposed a real clean-checkout portability issue.
- After patching the script to use `python -m research_assistant.cli`, `timeout 120 scripts/run_parser_preflight.sh` passed.
- `timeout 180 scripts/run_clean_ingest_palazzo.sh`: `1 passed in 0.05s`.
- Initial `timeout 180 scripts/run_tests.sh` failed because the report rewrite no longer contained exact source strings asserted by the docs smoke test.
- After restoring the NeuTra/DSGE showcase and making two assertions robust to case/line wrapping:
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py::test_git_sharing_walkthrough_and_gate_script_reference_current_commands -q`: `1 passed in 0.06s`;
  - `timeout 180 scripts/run_tests.sh`: `139 passed in 4.71s`.
- `git diff --check`: passed.

Phase 1 audit as another developer:
- The private-PDF release validation dependency is removed from active scripts.
- The Palazzo regression remains valuable because it now uses a sanitized temporary fixture and monkeypatched parser output.
- The parser preflight script is more robust because it no longer depends on the console script being installed.
- Remaining `Palazzo` hits are intentional test fixtures, historical audit notes, or explicit "no private PDF" documentation, not active private-path dependencies.
- Remaining `local_research/papers/raw` hits are legitimate workspace/shareability policy references, not validation requirements.

Phase 1 tidy result:
- No private PDFs, generated workspaces, caches, `build/`, or `dist/` files were staged.
- `.codex` remains untracked and excluded.

Next safe step:
- Execute Phase 2 by aligning release, publication, and external-validation docs to the individual local/Git release target.

## Update - final release readiness closure Phase 2 completed

Phase 2 plan for the phase:
- Align external-validation and publication docs to the individual local/Git release target.
- Remove misleading current-release "industrial release" wording.
- Preserve future/deferred platform references only where they are clearly non-goals.

Phase 2 execution result:
- Updated `docs/release/external_validation_protocol.md` so it now describes real target-machine evidence for the individual local/Git release, not an industrial hosted release.
- Updated `docs/release/publication_runbook.md` so publication checks use:
  - `ra release-artifacts manifest`;
  - `ra individual-git-release validation-report`;
  - `ra individual-git-release gate-build`.
- Updated clean-install smoke examples in:
  - `docs/platform_support.md`;
  - `docs/maintainer_guide.md`;
  to use the shell-safe `env WHEEL_PATH=... timeout ...` form.

Phase 2 validation:
- `rg -n "industrial release|departmental beta|industrial production|shared database|hosted UI|SSO/RBAC|industrial-release|industrial_release" ...` now reports only intentional non-goal, future/deferred, policy, or historical file-name references.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.73s`.
- `git diff --check`: passed.

Phase 2 audit as another developer:
- Current release docs now consistently point to the individual local/Git gate.
- Remaining shared database, hosted UI, SSO/RBAC, and industrial references are explicitly future/deferred or policy paths, not current-release claims.
- Manual validation and release-owner approval blockers remain visible.

Phase 2 tidy result:
- No generated outputs created.
- No private/generated files staged.

Next safe step:
- Execute Phase 3 by resolving `docs/plans/templates/` references with generic, privacy-safe templates or by removing stale references.

## Update - final release readiness closure Phase 3 completed

Phase 3 plan for the phase:
- Search for stale `docs/plans/templates/` references.
- Add short generic process templates if the directory is missing.
- Keep templates privacy-safe and useful for future autonomous release work.

Phase 3 execution result:
- Added:
  - `docs/plans/templates/reset-memo-template.md`;
  - `docs/plans/templates/phase-execution-template.md`;
  - `docs/plans/templates/external-validation-record-template.md`.
- The templates cover objective, scope, plan, execution, validation, audit, tidy, blockers, and next step.
- The external-validation template includes explicit privacy checks and a sanitized `individual-git-release validation-record` command shape.

Phase 3 validation:
- `find docs/plans/templates -maxdepth 2 -type f -print | sort` listed all three new templates.
- `rg -n "docs/plans/templates|reset-memo-template|phase-execution-template|external-validation-record-template|experiment-plan-template|experiment-result-template" docs` returned no stale references.
- `git diff --check`: passed.

Phase 3 audit as another developer:
- The new templates are generic and do not include private paths, usernames, credentials, paper content, or generated workspace state.
- Since no stale references remain, the templates are a release-process guardrail rather than a required product feature.
- Files are under ignored `docs/plans/` and must be force-staged intentionally at commit time.

Phase 3 tidy result:
- No generated outputs created.
- No private/generated files staged.

Next safe step:
- Execute Phase 4 by checking for real external validation evidence and recording unavailable fresh-reader, macOS, and minimal-parser-tool evidence as blocked/manual if no real evidence exists.

## Update - final release readiness closure Phase 4 completed

Phase 4 plan for the phase:
- Check whether real external validation records already exist.
- If no real fresh-reader, macOS, or minimal-parser-tool evidence exists, record the status as blocked/manual without creating fake records.
- Keep release notes and support docs explicit about pilot status.

Phase 4 execution result:
- Searched for existing validation evidence and found no real external validation records for:
  - `colleague_onboarding`;
  - `macos`;
  - `minimal_parser_tools`.
- Updated `docs/release_notes_0.1.0.md` with explicit current external validation status:
  - real fresh-reader onboarding: blocked/manual, not yet recorded;
  - real macOS clean-install smoke: blocked/manual, not yet recorded;
  - real minimal-parser-tool machine validation: blocked/manual, not yet recorded.
- Updated `docs/support.md` to state that the current status is a limited individual pilot candidate until those real validations are complete.

Phase 4 validation:
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/research-assistant-external-validation-status individual-git-release validation-report`: status `blocked`, `record_count: 0`, missing `colleague_onboarding`, `macos`, and `minimal_parser_tools`.
- `PYTHONPATH=src python -m research_assistant.cli --root /tmp/research-assistant-external-validation-status individual-git-release gate-build`: `ready_for_limited_individual_pilot: true`, `ready_for_broad_individual_release: false`, `ready_for_git_shared_research_release: false`.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.91s`.
- `git diff --check`: passed.

Phase 4 audit as another developer:
- The phase correctly records unavailable external validation as a blocker instead of fabricating records.
- The temporary `/tmp/research-assistant-external-validation-status` root is not committed and contains no private research data.
- Release notes and support docs are clearer about the pilot boundary.

Phase 4 tidy result:
- No external validation artifacts were staged.
- No private/generated files staged.

Next safe step:
- Execute Phase 5 by rebuilding release artifacts, running exact-wheel clean-install smoke, and synchronizing the release notes hash with the tested wheel.

## Update - final release readiness closure Phase 5 completed

Phase 5 plan for the phase:
- Run packaging smoke.
- Rebuild release artifacts.
- Run clean-install smoke against the exact rebuilt wheel.
- Synchronize release notes/platform support with the tested wheel hash and size.
- Rebuild the tracked proposal PDF because the report source changed in Phase 1.

Phase 5 execution result:
- `timeout 300 scripts/run_packaging_smoke.sh`: passed.
  - entrypoint metadata test: `1 passed in 0.07s`;
  - pip dry-run reported `Would install research-assistant-0.1.0`.
- `timeout 300 scripts/build_release_artifacts.sh`: passed.
  - removed old artifacts from `dist/`;
  - built `research_assistant-0.1.0-py3-none-any.whl`;
  - generated `dist/release_artifacts_manifest.json`.
- Manifest evidence:
  - wheel: `research_assistant-0.1.0-py3-none-any.whl`;
  - size: `435243` bytes;
  - SHA256: `d7c61cc8d4a79826a08754aee923be16065d3744bdcb316b797e74ffd71f03d6`.
- `env WHEEL_PATH=/home/chakwong/python/ResearchAssistant/dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh`: passed.
  - installed the exact wheel in a temporary venv;
  - `ra --help`, `ra version`, `ra init`, `ra doctor`, `ra demo setup`, `ra demo run`, and `ra release-report` all executed.
- Updated:
  - `docs/release_notes_0.1.0.md`;
  - `docs/platform_support.md`;
  - `tests/integration/test_individual_release_cli.py`;
  - tracked packaging metadata `src/research_assistant.egg-info/PKG-INFO`.
- Rebuilt `proposal/research_development_assistant_design.pdf` from the updated `.tex` source:
  - two `pdflatex` passes in `/tmp/research-assistant-design-build`;
  - final PDF: 23 pages, A4, unencrypted, `236513` bytes.

Phase 5 validation:
- `PYTHONPATH=src python -m research_assistant.cli release-artifacts manifest --dist-dir dist`: status `ok`, hash matches release notes.
- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.78s`.
- `git diff --check`: passed.

Phase 5 audit as another developer:
- The release notes hash now matches the exact wheel used for clean-install smoke.
- `dist/` remains ignored and must not be committed.
- The proposal PDF is synchronized with the restored NeuTra/DSGE showcase.
- `src/research_assistant.egg-info/PKG-INFO` changed only because the tracked package metadata reflects the README text; keeping it synchronized is appropriate for this repository because the egg-info file is tracked.

Phase 5 tidy result:
- Temporary clean-install workspace was removed by the smoke script.
- LaTeX auxiliary files stayed under `/tmp/research-assistant-design-build`.
- `dist/` and `build/` remain ignored and uncommitted.
- No private/generated files staged.

Next safe step:
- Execute Phase 6 by committing intentional changes, cloning the exact commit into `/tmp`, and running clean-clone validation.

## Update - final release readiness closure Phase 6 completed

Phase 6 plan for the phase:
- Validate from a clean clone of the exact release-readiness commit.
- Because a clean clone requires a real commit, create an implementation checkpoint commit first, then record clean-clone evidence in a final reset-memo closeout commit.

Implementation checkpoint commit:
- `ebb4eaf Close final release readiness gaps`.

Phase 6 execution result:
- Exact commit validated: `ebb4eafdb1e54f7e6df0c015cc058ed0150e2c56`.
- Cloned into:
  - `/tmp/research-assistant-final-clean-ebb4eaf`.
- Gate root:
  - `/tmp/research-assistant-final-clean-gate-ebb4eaf`.

Phase 6 validation:
- In clean clone:
  - `timeout 180 scripts/run_tests.sh`: `139 passed in 5.09s`.
  - `timeout 120 scripts/run_fast_tests.sh`: `14 passed in 1.04s`.
  - `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`: `14 passed in 1.90s`.
  - `GATE_ROOT=/tmp/research-assistant-final-clean-gate-ebb4eaf timeout 300 scripts/run_individual_git_release_gate.sh`: passed.
- Gate result from the clean clone:
  - `ready_for_limited_individual_pilot: true`;
  - `ready_for_broad_individual_release: false`;
  - `ready_for_git_shared_research_release: false`;
  - `local_fixture_validation_complete: true`;
  - `representative_workspace_performance_status: passed`;
  - `merge_fixture_rehearsal_status: passed`;
  - blockers remain `colleague_onboarding`, `macos`, and release-owner approval.
- Clean clone `git diff --check`: passed.
- Clean clone `git status --short --ignored`: only ignored `.pytest_cache/` and bytecode caches created by validation.

Phase 6 audit as another developer:
- Clean clone validation confirms the release-readiness commit is reproducible from a fresh checkout.
- Gate behavior is correct: local fixture evidence supports limited pilot, while real external validation and approval still block broad/Git-shared release.
- Generated gate workspaces under `/tmp` are not committed.

Phase 6 tidy result:
- `/tmp/research-assistant-final-clean-ebb4eaf` and `/tmp/research-assistant-final-clean-gate-ebb4eaf` are temporary validation artifacts and remain outside the repository.
- No private/generated files staged.

Next safe step:
- Execute Phase 7 by recording release-owner tag/publication status as blocked/manual because no explicit approval to tag or publish was provided.

## Update - final release readiness closure Phase 7 completed

Phase 7 plan for the phase:
- Summarize evidence and record tag/publication status.
- Do not tag or publish without explicit release-owner approval.

Phase 7 execution result:
- No explicit approval to create `v0.1.0` was provided.
- No explicit approval to publish artifacts was provided.
- No tag was created.
- No artifacts were published.

Phase 7 evidence summary:
- Exact validated commit: `ebb4eafdb1e54f7e6df0c015cc058ed0150e2c56`.
- Exact tested wheel:
  - `dist/research_assistant-0.1.0-py3-none-any.whl`;
  - size `435243` bytes;
  - SHA256 `d7c61cc8d4a79826a08754aee923be16065d3744bdcb316b797e74ffd71f03d6`.
- Clean clone validation passed.
- Gate remains limited-pilot ready and broad/Git-shared blocked.

Phase 7 audit as another developer:
- This correctly preserves the approval boundary.
- Prior user instructions requested execution and commit, not tag creation or artifact publication.
- Recording blocked/manual is the only truthful autonomous action for tag and publication approval.

Phase 7 tidy result:
- No tags created.
- No publication artifacts uploaded.
- `dist/` remains ignored and uncommitted.

Next safe step:
- Execute Phase 8 by committing this final reset-memo closeout and pushing normal commits to `origin/main` if credentials/network allow.

## Update - final release readiness closure Phase 8 completed

Phase 8 plan for the phase:
- Update the reset memo with complete shutdown-recovery evidence.
- Commit the final closeout packet.
- Push normal commits to `origin/main` to make the release-readiness commit available for external validators.

Phase 8 final status:
- Agent-executable gaps closed:
  - stale validation scripts/docs are portable and clean-checkout safe;
  - release/publication/external-validation docs are aligned to individual local/Git release;
  - process templates exist under `docs/plans/templates/`;
  - final artifact hash is synchronized with the exact tested wheel;
  - proposal PDF is rebuilt from the updated source;
  - clean clone validation is recorded for exact commit `ebb4eafdb1e54f7e6df0c015cc058ed0150e2c56`.
- Human/external blockers remaining:
  - real fresh-reader onboarding is not recorded;
  - real macOS validation is not recorded;
  - real minimal-parser-tool machine validation is not recorded;
  - release-owner tag approval is not recorded;
  - release-owner publication approval is not recorded.
- Current release status:
  - suitable for limited individual pilot;
  - not ready for broad non-pilot release;
  - not tagged;
  - not published.

Final local state before closeout commit:
- `.codex` remains untracked and uncommitted.
- `.claude/`, `.pytest_cache/`, `build/`, `dist/`, bytecode caches, and `/tmp` validation clones remain ignored/uncommitted.
- `docs/plans/whole_codebase_release_audit_2026-04-29.md` remains ignored local audit input and was not committed in this closeout.

Next safe step:
- Use the pushed commit for real colleague onboarding, macOS clean-install smoke, and minimal-parser-tool validation. Only after those records and explicit release-owner approval exist should a tag or publication be created.


## Update - local MCP addition execution started

New objective:
- Execute `docs/plans/local_mcp_addition_plan_2026-05-02.md` after the user
  reported that the colleague rollout is complete and positively received.

Requested execution loop:
- update this reset memo;
- audit the plan as another developer;
- execute every phase one by one;
- for each phase: plan, execute, test, audit, tidy, update reset memo;
- continue without human intervention unless the next phase is no longer
  justified;
- commit modified files after the whole plan finishes;
- update this memo again on completion.

Initial repo baseline:
- Branch: `main...origin/main`.
- Working tree before MCP edits: no tracked changes; `.codex` exists as an
  untracked local scratch file and must not be committed.
- Recent HEAD: `9a20761 Strengthen final release proposal narrative`.

Independent pre-execution audit result:
- The plan is directionally correct: local stdio MCP is an adapter milestone,
  not a hosted platform or shared database.
- Scope boundary is sound: read-only by default, no HTTP server, no provider
  calls by default, no destructive tools.
- The plan needed additional implementation constraints before coding:
  - keep the package importable without the optional MCP SDK installed;
  - test MCP by calling registered tools/resources directly rather than by
    starting a long-lived stdio process in deterministic tests;
  - bind arXiv batch grants to a stable plan hash, explicit scope, root,
    destination, limits, and duplicate policy;
  - reject path/symlink escapes server-side;
  - expose optional MCP readiness in `ra release-report` without turning MCP
    into a hard release dependency;
  - keep the first executable batch intake explicit-arXiv-ID based, with
    query-based live discovery deferred until the grant model is proven.
- The plan was updated with these audit findings before implementation.

Next safe step:
- Execute Phase 0 by adding local-MCP scope documentation, recording baseline
  evidence, and validating that the next implementation phase remains justified.

## Update - local MCP addition Phase 0 completed

Phase 0 plan for the phase:
- Lock the MCP scope as local stdio adapter work.
- Record baseline evidence from current release/privacy/doctor surfaces.
- Add architecture/product docs that prevent local MCP from being mistaken for
  hosted platform work.

Phase 0 execution result:
- Added `docs/architecture/local_mcp_adapter.md`.
- Updated `docs/usage.md`, `docs/product_spec.md`, and ADR 0006 to state:
  - local stdio MCP is allowed as an adapter;
  - read-only is the default;
  - HTTP/shared/server MCP remains out of scope;
  - write-capable arXiv intake requires bounded local grants and audit records.
- Inspected `src/research_assistant/adapters/mcp_server.py`; it was still a
  placeholder wrapper before implementation.

Phase 0 baseline evidence:
- `PYTHONPATH=src python -m research_assistant.cli release-report` completed
  with status `warnings` and no blockers. Warnings were existing workspace
  setup warnings for the repository root, not MCP blockers.
- `PYTHONPATH=src python -m research_assistant.cli privacy status` returned
  `status: ok`, `offline_mode: true`, `providers_enabled: false`, and
  `live_llm_calls_enabled: false`.
- `PYTHONPATH=src python -m research_assistant.cli doctor --matrix` completed
  with existing workspace warnings and parser matrix available.

Phase 0 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 0 audit as another developer:
- Scope docs preserve individual local use and do not claim hosted MCP,
  production API, shared database, or SSO/RBAC.
- No code paths were added that can write, download, or mutate review state.
- The architecture note makes batch intake a future bounded-grant capability,
  not an implicit write permission.

Phase 0 tidy result:
- No generated files were intentionally created in the repo.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- Phase 0 closes the scope ambiguity. Phase 1 remains justified because MCP
  still needs a shared structured tool contract layer before replacing the
  placeholder adapter.

## Update - local MCP addition Phase 1 completed

Phase 1 plan for the phase:
- Add a shared structured tool contract layer for local read-only operations.
- Keep outputs JSON-serializable and avoid CLI stdout parsing.
- Preserve review/generated/parser trust boundaries.

Phase 1 execution result:
- Added `src/research_assistant/adapters/local_tools.py`.
- The contract layer now exposes read-only helpers for:
  - workspace status;
  - paper search;
  - paper summary;
  - paper code links;
  - claim-support audit;
  - review list/show;
  - source show;
  - parser tool matrix;
  - privacy status;
  - doctor status.
- The helpers accept explicit roots or `RA_ROOT`, return structured payloads,
  and do not expose write operations.
- Added `tests/integration/test_mcp_adapter.py` with local contract tests over a
  demo workspace.

Phase 1 tests:
- `timeout 180 python -m pytest tests/integration/test_mcp_adapter.py -q`:
  `5 passed`.
- `timeout 180 python -m pytest tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands tests/integration/test_mcp_adapter.py -q`:
  `6 passed`.
- `git diff --check`: passed.

Phase 1 audit as another developer:
- The contract layer calls Python functions directly and does not parse CLI
  text output.
- No ingest, download, review mutation, backup restore, workspace apply,
  arbitrary file read/write, or destructive operation is exposed.
- The source/show helpers preserve generated/review-material language and
  missing-source behavior.

Phase 1 tidy result:
- No generated files were intentionally created.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- Phase 1 gives MCP a safe backend surface. Phase 2 remains justified because
  the placeholder MCP adapter can now be replaced with a local read-only stdio
  server over these contracts.

## Update - local MCP addition Phase 2 completed

Phase 2 plan for the phase:
- Replace the placeholder MCP adapter with a local stdio read-only server.
- Keep MCP optional so base CLI installs do not require the SDK.
- Register only safe read-only tools/resources and test direct SDK calls rather
  than managing a long-running stdio process.

Phase 2 execution result:
- Updated `pyproject.toml`:
  - added optional extra `mcp = ["mcp[cli]"]`;
  - added script entry point `ra-mcp =
    "research_assistant.adapters.mcp_server:main"`.
- Replaced `src/research_assistant/adapters/mcp_server.py` with a FastMCP-based
  local stdio server.
- Registered read-only tools:
  - `ra_workspace_status`;
  - `ra_find_paper`;
  - `ra_get_paper_summary`;
  - `ra_paper_code_links`;
  - `ra_claim_support_audit`;
  - `ra_review_list`;
  - `ra_review_show`;
  - `ra_source_show`;
  - `ra_parser_tool_matrix`;
  - `ra_privacy_status`.
- Registered read-only resources:
  - `research-assistant://workspace/status`;
  - `research-assistant://paper/{paper_id}`;
  - `research-assistant://source/{paper_id}`.
- Added tests that verify no review mutation, ingest, download, restore, or
  destructive MCP tool names are present.
- Added direct FastMCP tool/resource tests when the SDK is installed.

Phase 2 tests:
- `timeout 180 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_individual_release_cli.py::test_project_metadata_exposes_ra_entrypoint -q`:
  `8 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 5 env PYTHONPATH=src python -m research_assistant.adapters.mcp_server --help`:
  help text printed successfully.
- `git diff --check`: passed.

Phase 2 audit as another developer:
- The server uses stdio only via `server.run(transport="stdio")`; no HTTP/SSE
  listener is introduced.
- The module remains importable with optional MCP behavior isolated behind
  `mcp_available()` and `build_server()`.
- Registered tools are read-only and annotated as non-destructive.
- No write-capable tool is exposed through MCP.

Phase 2 tidy result:
- No long-running server session remains active.
- No generated files were intentionally created.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- MCP Alpha 1 now has a working server surface. Phase 3 remains justified
  because users need installation/client configuration docs and privacy
  guidance before this can be handed to colleagues.

## Update - local MCP addition Phase 3 completed

Phase 3 plan for the phase:
- Add colleague-facing MCP setup documentation.
- Make client configuration, `RA_ROOT`, optional dependency behavior, read-only
  tools, and privacy boundaries explicit.
- Cross-link from README/usage/troubleshooting/limitations.

Phase 3 execution result:
- Added `docs/mcp.md`.
- Updated `README.md` with local MCP install/start example and read-only
  boundary.
- Updated `docs/troubleshooting.md` with local MCP diagnostics.
- Updated `docs/known_limitations.md` with optional local/read-only MCP
  limitations.
- `docs/usage.md` had already been linked during Phase 0.

Phase 3 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 3 audit as another developer:
- Docs describe local stdio MCP only and do not imply hosted deployment.
- Docs warn that MCP can inspect local workspace content and paths through tool
  responses.
- Docs do not describe write-capable MCP tools as available yet.

Phase 3 tidy result:
- No generated files were intentionally created.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- MCP Alpha 1 documentation is in place. Phase 4 remains justified because
  bounded batch arXiv intake needs a tested grant/audit foundation before any
  write-capable MCP tool exists.

## Update - local MCP addition Phase 4 completed

Phase 4 plan for the phase:
- Add local MCP permission/grant/audit models before any write-capable MCP
  operation.
- Add CLI-only grant creation and inspection.
- Enforce root/path/domain/expiry/count/plan-hash checks in reusable helpers.

Phase 4 execution result:
- Added `src/research_assistant/adapters/mcp_permissions.py`.
- Added local governance paths under `local_research/governance/mcp/` for:
  - grants;
  - audit JSONL events;
  - future batch manifests.
- Added grant helpers for `arxiv_batch_intake` with:
  - `plan_hash`;
  - operation;
  - destination;
  - max papers;
  - expiry;
  - allowed arXiv domains;
  - duplicate/no-overwrite/review-material policies;
  - explicit arXiv ID scope.
- Added server-side validators for:
  - workspace root;
  - destination path under `local_research`;
  - allowed domains;
  - grant expiry;
  - plan-hash mismatch;
  - operation/destination/root mismatch;
  - max-paper overflow.
- Added CLI commands:
  - `ra mcp status`;
  - `ra mcp grant arxiv-intake ...`;
  - `ra mcp grants list`;
  - `ra mcp grants show --grant-id <id>`;
  - `ra mcp audit list [--grant-id <id>]`.
- Added focused tests in `tests/integration/test_mcp_permissions.py` and CLI
  grant tests in `tests/integration/test_cli_commands.py`.

Phase 4 tests:
- `timeout 180 python -m pytest tests/integration/test_mcp_permissions.py tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands tests/integration/test_cli_commands.py::test_cli_mcp_grant_and_audit_foundation tests/integration/test_cli_commands.py::test_cli_mcp_grant_rejects_unbounded_batch -q`:
  `7 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 4 audit as another developer:
- Grants are created by CLI, not by MCP, preserving an explicit human action
  before future writes.
- The model is local and file-based; no server auth/RBAC claim was introduced.
- Destructive and review-write modes remain disabled by status and are not
  exposed through MCP.
- Grant validation is more than prompt politeness: it checks concrete root,
  destination, plan hash, expiry, count, IDs, and domains.

Phase 4 tidy result:
- Focused tests wrote grant/audit files only under pytest temp workspaces.
- No generated files were intentionally created in the repository.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- The permission foundation is now concrete enough for planning batch arXiv
  intake. Phase 5 remains justified, with the first implementation scoped to
  explicit arXiv ID lists rather than live query discovery.

## Update - local MCP addition Phase 5 completed

Phase 5 plan for the phase:
- Add arXiv batch planning without downloads or writes.
- Scope first implementation to explicit arXiv IDs.
- Produce stable plan hashes and duplicate/readiness metadata suitable for a
  later grant-bound execution.

Phase 5 execution result:
- Added `src/research_assistant/ingest/arxiv_batch.py`.
- Added `plan_arxiv_batch_intake(...)` with:
  - arXiv ID normalization and validation;
  - explicit-ID candidate planning;
  - stable plan hash;
  - duplicate detection from summaries/source records;
  - allowed-domain/destination/duplicate/no-overwrite/review-material policies;
  - query-only blocking with `query_search_not_implemented`;
  - no writes during planning.
- Added `ra arxiv-batch plan`.
- Added read-only MCP planning tool `ra_plan_arxiv_batch_intake`.
- Added tests in `tests/integration/test_arxiv_batch_intake.py`.
- Adjusted planning duplicate detection to avoid creating `local_research/`
  during plan-only reads.

Phase 5 tests:
- First focused run found an issue: planning created `local_research/` through
  `FileStore` construction during duplicate detection.
- Fixed by reading JSON directly from existing files in the read-only duplicate
  scan.
- `timeout 180 python -m pytest tests/integration/test_arxiv_batch_intake.py tests/integration/test_mcp_adapter.py tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands -q`:
  `13 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 5 audit as another developer:
- Planning performs no paper/source/inbox writes and query-based live search is
  clearly deferred.
- The plan hash is deterministic for equivalent explicit ID lists.
- MCP planning is read-only and still requires a separate grant before
  execution.
- Duplicate detection is useful but conservative; it detects existing source
  records and summary arXiv IDs without claiming semantic deduplication.

Phase 5 tidy result:
- Focused tests wrote only pytest temp fixtures.
- No generated files were intentionally created in the repository.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- The plan-first half of batch intake is complete. Phase 6 remains justified
  because grant-bound execution can now verify a concrete plan hash and explicit
  arXiv ID scope.

## Update - local MCP addition Phase 6 completed

Phase 6 plan for the phase:
- Implement grant-bound arXiv batch source execution.
- Require grant ID, plan hash, explicit arXiv IDs, and matching source-fetch
  scope.
- Write manifest/audit records and never mark records approved.

Phase 6 execution result:
- Implemented `run_arxiv_batch_intake(...)` in
  `src/research_assistant/ingest/arxiv_batch.py`.
- Execution now:
  - loads the local grant;
  - validates expiry, root, operation, destination, plan hash, arXiv IDs,
    max-paper limit, destination path, and allowed domains;
  - recomputes the plan hash before work;
  - skips duplicates by default;
  - fetches arXiv structured source through existing source-first machinery;
  - writes a batch manifest under `local_research/governance/mcp/batch_manifests/`;
  - appends audit events for blocked/start/item/completion states;
  - returns review-material-only status.
- Added `ra arxiv-batch run --grant-id ... --plan-hash ... --ids ...`.
- Added MCP tool `ra_run_arxiv_batch_intake`, which requires a matching local
  grant.
- Added tests for successful monkeypatched source fetch, plan-hash mismatch,
  and duplicate skip.

Phase 6 tests:
- `timeout 180 python -m pytest tests/integration/test_arxiv_batch_intake.py tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py -q`:
  `19 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 6 audit as another developer:
- Write execution is now possible, but only with a local grant created outside
  MCP and matching a concrete plan hash and explicit ID list.
- The implemented execution path is source-fetch only; PDF downloads and
  query-based discovery remain deferred.
- Manifest and audit writes are confined to local governance paths.
- No review mutation or mathematical approval is performed.
- Network behavior remains mocked in tests; no deterministic test requires live
  arXiv.

Phase 6 tidy result:
- Focused tests wrote source/grant/audit/manifest files only under pytest temp
  workspaces.
- No generated files were intentionally created in the repository.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- The initial batch-permission workflow is implemented at source-fetch scope.
  Phase 7 remains justified because review-write should be explicitly deferred
  and guarded by tests/design notes before users infer MCP can mutate review
  decisions.

## Update - local MCP addition Phase 7 completed

Phase 7 plan for the phase:
- Do not implement review mutation.
- Add a future review-write design gate.
- Strengthen tests that assert MCP does not expose review/audit mutation tools.

Phase 7 execution result:
- Added `docs/architecture/mcp_review_write_design.md`.
- The design note specifies future `review_write` requirements:
  - explicit mode separate from arXiv batch intake;
  - concrete confirmation payload;
  - old/new value and file-hash capture;
  - audit event;
  - conflict blocking;
  - no bulk/silent/generated approval.
- Strengthened MCP adapter tests to assert absent review/audit mutation,
  ingest, download, and backup-restore tool names.

Phase 7 tests:
- `timeout 180 python -m pytest tests/integration/test_mcp_adapter.py -q`:
  `7 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 7 audit as another developer:
- Review mutation remains deferred.
- The implemented MCP write capability is limited to grant-bound arXiv source
  intake that creates review material only.
- Future review-write requirements are now explicit enough to prevent accidental
  addition of vague `confirm=true` write tools.

Phase 7 tidy result:
- No generated files were intentionally created.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- The trust boundary around review state is preserved. Phase 8 remains
  justified because release-report/docs should surface MCP readiness and provide
  an MCP trial path.

## Update - local MCP addition Phase 8 completed

Phase 8 plan for the phase:
- Add MCP readiness to release/reporting surfaces without making MCP a hard base
  release dependency.
- Add a colleague-like MCP trial checklist.
- Validate release report and focused MCP/batch behavior.

Phase 8 execution result:
- Added `mcp_readiness_status(...)` to `src/research_assistant/individual_release.py`.
- `ra release-report` now includes `mcp_readiness` with:
  - optional status;
  - MCP SDK availability;
  - entrypoint;
  - stdio transport;
  - read-only default mode;
  - local permission status;
  - read-only tool list;
  - limitations.
- Added `docs/mcp_trial_checklist.md`.
- Updated `docs/mcp.md` with explicit-ID batch plan/grant/run commands and
  trial-checklist link.
- Added release-report assertions for MCP readiness.

Phase 8 tests:
- `timeout 180 python -m pytest tests/integration/test_individual_release_cli.py::test_missing_optional_parser_tools_do_not_block_core_workflows tests/integration/test_mcp_adapter.py tests/integration/test_arxiv_batch_intake.py -q`:
  `16 passed`.
- `PYTHONPATH=src python -m research_assistant.cli release-report`: completed
  with existing repository-root workspace warnings and no blockers; MCP
  readiness reported `status: available`, `transport: stdio`, and
  `default_mode: read_only`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 8 audit as another developer:
- MCP readiness is informational/optional and does not block the base local CLI
  release if absent.
- The trial checklist avoids private data and validates absence of write tools.
- Release report now surfaces MCP posture for maintainers without claiming
  hosted/shared/server readiness.

Phase 8 tidy result:
- `ra release-report` rewrote ignored `dist/release_artifacts_manifest.json`
  because existing ignored release artifacts are present; this remains
  generated/ignored and must not be committed.
- No generated files were intentionally staged.
- `.codex` remains untracked local scratch and must not be committed.

Interpretation and next-phase justification:
- All planned phases are implemented. Final validation and commit are now
  justified, with remaining risks limited to optional dependency packaging,
  live arXiv behavior outside deterministic tests, and future review-write
  design validation.

## Update - local MCP addition final validation completed

Final validation plan:
- Re-run focused MCP, permission, arXiv batch, individual release, and CLI
  tests.
- Re-run fast suite and diff hygiene.
- Audit implementation against the plan before staging.

Final validation results:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_individual_release_cli.py -q`:
  `33 passed`.
- `timeout 240 python -m pytest tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands tests/integration/test_cli_commands.py::test_cli_mcp_grant_and_audit_foundation tests/integration/test_cli_commands.py::test_cli_mcp_grant_rejects_unbounded_batch -q`:
  `3 passed`.
- `timeout 5 env PYTHONPATH=src python -m research_assistant.adapters.mcp_server --help`:
  printed `ra-mcp` help successfully.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 300 python -m pytest tests/integration/test_cli_commands.py -q`:
  `22 passed`.
- Final rerun after wording corrections:
  `timeout 120 scripts/run_fast_tests.sh && git diff --check`: `14 passed`,
  diff check passed.

Final implementation audit as another developer:
- Local MCP is stdio-only; no HTTP/server deployment was introduced.
- Base CLI install remains independent of the optional MCP SDK.
- MCP read-only tools expose local inspection/status/planning only.
- The single write-capable MCP operation is grant-bound arXiv source intake:
  it requires grant ID, plan hash, explicit IDs, matching root/scope, and
  writes only source/manifest/audit review material.
- Review mutation, downloads, backup restore, delete, arbitrary file access,
  and destructive operations are not exposed as MCP tools.
- Query-based arXiv search and PDF batch downloads are explicitly deferred.
- Release report surfaces MCP readiness as optional and does not turn MCP into a
  release blocker.

Final tidy/status:
- `.codex` remains untracked local scratch and must not be committed.
- Ignored generated/local paths remain uncommitted: `.claude/`,
  `.pytest_cache/`, `build/`, `dist/`, `local_research/`, bytecode caches,
  TeX aux/log outputs, `hoffman.json`, and `out.txt`.
- `docs/plans/local_mcp_addition_plan_2026-05-02.md` and this reset memo are
  under ignored `docs/plans/`; force-stage them intentionally if committing.

Completion interpretation:
- The MCP addition plan is complete through the local MCP beta boundary:
  read-only local MCP, grant/audit model, explicit-ID arXiv source batch
  planning and execution, release visibility, docs, and tests.
- Next recommended hypotheses to test:
  - H1: a colleague can configure `ra-mcp` in their assistant and use read-only
    tools against a demo workspace in under 15 minutes.
  - H2: explicit-ID arXiv batch source intake with 25-100 papers remains stable,
    skips duplicates correctly, and produces useful audit manifests.
  - H3: query-based arXiv discovery can be added without weakening grant scope
    or causing uncontrolled network fanout.
  - H4: PDF inbox batch downloads need separate byte limits, overwrite rules,
    and duplicate UX before being enabled.
  - H5: review-write MCP can be added safely only after confirmation payloads
    include old/new values, file hashes, conflict detection, and auditable
    correction paths.


## Update - local MCP follow-on validation and expansion started

New objective:
- Execute `docs/plans/local_mcp_next_validation_and_expansion_plan_2026-05-02.md`
  after commit `28115cd Add local MCP adapter and batch grants`.

Requested execution loop:
- update this reset memo;
- audit the plan as another developer;
- execute every phase one by one;
- for each phase: plan, execute, test, audit, tidy, update reset memo;
- continue without human intervention unless the next phase is not justified;
- commit modified files after the whole plan finishes;
- update this memo upon completion.

Initial repo baseline:
- Branch: `main...origin/main [ahead 1]`.
- Recent HEAD: `28115cd Add local MCP adapter and batch grants`.
- Working tree before follow-on edits: `.codex` untracked local scratch only.

Independent pre-execution audit result:
- The plan preserves local-only MCP scope and does not require hosted services.
- Corrections made before execution:
  - Phase 1 now explicitly allows a local surrogate if no real colleague is
    available, while recording H1 as external/manual rather than passed.
  - Phase 2 now separates deterministic mocked scale evidence from live arXiv
    scale evidence.
  - Query discovery remains mocked/design-gated until bounded live approval.
  - PDF batch intake remains design/policy-only until byte limits, cleanup,
    duplicate behavior, and tests exist.
  - Review-write may be CLI-prototyped but MCP review-write exposure remains out
    of scope.

Next safe step:
- Execute Phase 0 baseline and safety re-audit.

## Update - local MCP follow-on Phase 0 completed

Phase 0 plan for the phase:
- Recheck current repo state and local MCP safety posture after commit
  `28115cd`.
- Confirm release report, MCP status, `ra-mcp --help`, and focused MCP tests
  remain healthy.

Phase 0 execution result:
- `git status --short --branch`: `main...origin/main [ahead 1]` with
  `.codex` untracked local scratch.
- `git log --oneline -5` confirmed HEAD `28115cd Add local MCP adapter and
  batch grants`.
- `PYTHONPATH=src python -m research_assistant.cli release-report`: completed
  with existing repository-root workspace warnings and no blockers.
- `PYTHONPATH=src python -m research_assistant.cli mcp status`: reported
  `default_mode: read_only`, `destructive_tools_enabled: false`, and
  `review_write_enabled: false`.
- `timeout 5 env PYTHONPATH=src python -m research_assistant.adapters.mcp_server --help`:
  printed help successfully.

Phase 0 tests:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py -q`:
  `19 passed`.

Phase 0 audit as another developer:
- No HTTP/server deployment is present.
- MCP remains optional and local stdio.
- Release report surfaces MCP readiness without turning MCP into a release
  blocker.
- Exposed MCP write capability remains grant-bound arXiv source intake; no
  review mutation, PDF batch download, backup restore, delete, or destructive
  tool is exposed.

Phase 0 tidy result:
- `release-report` rewrote ignored `dist/release_artifacts_manifest.json`
  because ignored release artifacts exist; it remains generated/ignored and
  must not be committed.
- No private/generated files staged.

Interpretation and next-phase justification:
- Current MCP baseline is safe and green. Phase 1 remains justified, but only a
  local surrogate can be run in this autonomous session; H1 must remain
  external/manual until a real colleague performs the trial.

## Update - local MCP follow-on Phase 1 completed

Phase 1 plan for the phase:
- Run the colleague MCP setup checklist if a real colleague is available.
- Because no external colleague can be created in this autonomous session, run a
  local surrogate against a demo workspace and record H1 as still requiring
  external validation.

Phase 1 execution result:
- Created a demo workspace under `/tmp/ra-mcp-trial-surrogate` with:
  `PYTHONPATH=src python -m research_assistant.cli --root /tmp/ra-mcp-trial-surrogate demo setup`.
- Checked MCP entrypoint help with:
  `env PYTHONPATH=src RA_ROOT=/tmp/ra-mcp-trial-surrogate python -m research_assistant.adapters.mcp_server --help`.
- Exercised MCP tools directly through the SDK against the demo workspace:
  - `ra_workspace_status`;
  - `ra_find_paper`;
  - `ra_get_paper_summary`;
  - `ra_source_show`;
  - `ra_review_list`;
  - `ra_claim_support_audit`;
  - `ra_privacy_status`.
- Surrogate result:
  - required tools present: all seven;
  - unsafe tools present: none from `ra_review_mark`, `ra_download_paper`,
    `ra_backup_restore`, `ra_delete`;
  - demo paper found: `demo_transport_paper`;
  - source status: `available`;
  - privacy status: `ok`;
  - elapsed direct SDK exercise: `0.013` seconds.
- One initial surrogate script failed because it assumed the SDK structured
  return shape always included a `result` key; rerun with robust result decoding
  passed. This was a script issue, not a product issue.

Phase 1 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 1 audit as another developer:
- This is not real colleague evidence and must not be represented as H1 passed.
- The surrogate confirms local mechanics, tool availability, and unsafe-tool
  absence against demo data.
- No private data was used or recorded; outputs lived under `/tmp`.

Phase 1 tidy result:
- `/tmp/ra-mcp-trial-surrogate` is temporary validation output outside the repo.
- No private/generated files staged.

Interpretation and next-phase justification:
- H1 remains `external_validation_required`.
- Local MCP mechanics are healthy enough to continue to Phase 2 deterministic
  explicit-ID batch scale validation.

## Update - local MCP follow-on Phase 2 completed

Phase 2 plan for the phase:
- Validate explicit-ID arXiv source batch mechanics at useful scale without
  requiring live network.
- Add a deterministic mocked 25-paper scale test that verifies plan/grant/run,
  manifest, audit events, and no approval behavior.

Phase 2 execution result:
- Added `test_granted_arxiv_batch_run_handles_mocked_25_paper_scale` to
  `tests/integration/test_arxiv_batch_intake.py`.
- The test uses 25 sanitized synthetic arXiv IDs (`2401.00001` through
  `2401.00025`) and monkeypatches source fetch to write structured source
  records locally.
- Verified:
  - plan status is grant-ready;
  - grant binds 25 IDs and plan hash;
  - run completes with `attempted_count: 25`;
  - fetched count is 25;
  - failures are empty;
  - manifest records review-material-only policy;
  - audit JSONL has start/item/completion coverage;
  - mocked run finishes under 5 seconds.

Phase 2 tests:
- `timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q`:
  `9 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 2 audit as another developer:
- This supports H2 for deterministic local mechanics only, not live arXiv
  reliability.
- No live network was used.
- Generated records were created only under pytest temp workspaces.
- Batch records remain source review material and do not mark papers approved.

Phase 2 tidy result:
- No repository-local batch artifacts were created.
- No private/generated files staged.

Interpretation and next-phase justification:
- H2 is narrowed: local plan/grant/run mechanics work at 25-paper mocked scale.
  Live 25/50/100 arXiv source intake remains manual/bounded validation.
- Phase 3 remains justified because query discovery can now be designed around
  a known-safe explicit candidate-list and plan-hash model.

## Update - local MCP follow-on Phase 3 completed

Phase 3 plan for the phase:
- Add a design gate for query-based arXiv discovery.
- Do not enable live query discovery through MCP.
- Specify candidate-list pinning and plan-hash binding before implementation.

Phase 3 execution result:
- Added `docs/architecture/mcp_arxiv_query_discovery_design.md`.
- The design requires:
  - bounded `max_candidates`;
  - explicit endpoint domain `export.arxiv.org`;
  - pagination cap;
  - timeout;
  - deterministic candidate ordering;
  - candidate file inspection;
  - plan hash including exact ordered candidate IDs;
  - grant execution verifying candidate-list identity, not just query text.
- The design keeps live query discovery out of MCP until mocked tests and a
  bounded live smoke are approved and recorded.

Phase 3 tests:
- `timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q`:
  `9 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 3 audit as another developer:
- The design avoids uncontrolled network fanout by requiring max-candidate and
  pagination limits.
- It prevents query-text-only grants by requiring exact candidate-list/plan-hash
  binding.
- It does not introduce live query discovery, provider calls, or hosted MCP.

Phase 3 tidy result:
- Docs-only phase; no generated files created.
- No private/generated files staged.

Interpretation and next-phase justification:
- H3 now has a concrete bounded design but remains unimplemented/live-disabled.
- Phase 4 remains justified because PDF batch intake has distinct file-size,
  duplicate, and cleanup risks that need a separate policy before coding.

## Update - local MCP follow-on Phase 4 completed

Phase 4 plan for the phase:
- Add a PDF batch intake design/policy gate.
- Do not enable PDF batch download execution.
- Specify byte limits, destination, duplicate behavior, cleanup, and tests
  required before enablement.

Phase 4 execution result:
- Added `docs/architecture/mcp_pdf_batch_intake_design.md`.
- The policy requires:
  - inbox-only destination;
  - local expiring grant;
  - max file count;
  - max total bytes;
  - per-file byte limit;
  - allowed-domain review;
  - no overwrite;
  - duplicate checks;
  - proposal metadata;
  - checksum capture;
  - temporary-file cleanup;
  - manifest/audit events;
  - monkeypatched deterministic tests before enablement.
- Suggested initial limits:
  - 25 files;
  - 250 MB total;
  - 25 MB per file;
  - 30 seconds per file.

Phase 4 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 4 audit as another developer:
- PDF batch downloads remain disabled.
- The design separates PDF inbox proposals from trusted raw corpus ingest.
- The policy addresses file-size, cleanup, duplicate, no-overwrite, and audit
  risks before any MCP exposure.

Phase 4 tidy result:
- Docs-only phase; no generated files created.
- No private/generated files staged.

Interpretation and next-phase justification:
- H4 now has a concrete policy and remains disabled until tests/limits exist.
- Phase 5 remains justified because review-write can be prototyped safely as a
  CLI-only proposal/apply flow without exposing MCP review mutation.

## Update - local MCP follow-on Phase 5 completed

Phase 5 plan for the phase:
- Prototype review-write as a CLI-only confirmation flow.
- Do not expose review-write through MCP.
- Require old/new values, file hash, expiration, audit events, and conflict
  blocking.

Phase 5 execution result:
- Added `src/research_assistant/adapters/review_write.py`.
- Added CLI commands:
  - `ra review-write status`;
  - `ra review-write propose-status --paper-id <id> --status <status>`;
  - `ra review-write apply --confirmation-id <id>`.
- Proposal records include:
  - workspace root;
  - paper ID;
  - target path;
  - old value;
  - new value;
  - old file SHA256;
  - expiration;
  - risks;
  - `mcp_exposure: not_exposed`.
- Apply verifies:
  - confirmation exists;
  - operation is supported;
  - workspace root matches;
  - proposal has not expired;
  - target exists;
  - target file hash still matches;
  - requested status is valid.
- Apply writes old/new values and file hashes to a local audit JSONL record.
- Added integration coverage for propose/apply/conflict/status.

Phase 5 tests:
- `timeout 240 python -m pytest tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands tests/integration/test_cli_commands.py::test_cli_review_write_propose_apply_and_conflict -q`:
  `2 passed`.
- `timeout 240 python -m pytest tests/integration/test_cli_commands.py -q`:
  `23 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 5 audit as another developer:
- Review-write is CLI-only and reports `mcp_exposed: false`.
- The flow blocks stale file-hash conflicts.
- The prototype changes review status only after a concrete proposal/apply
  sequence; there is no generic `confirm=true` shortcut.
- MCP review mutation remains absent.

Phase 5 tidy result:
- Tests wrote proposal/audit files only under pytest temp workspaces.
- No private/generated files staged.

Interpretation and next-phase justification:
- H5 is narrowed: CLI confirmation mechanics are feasible, but MCP exposure
  should wait for further review, UX testing, and perhaps undo/correction
  design.
- Phase 6 remains justified to update docs and readiness notes to match the new
  query/PDF/review-write gates and CLI prototype.

## Update - local MCP follow-on Phase 6 started

Phase 6 plan for the phase:
- Update user-facing MCP and release-readiness docs so they match the current
  implementation boundary.
- Make clear that query-based arXiv discovery and PDF batch downloads are
  design-gated and disabled.
- Make clear that review-write is a CLI-only prototype with explicit
  confirmation and is not exposed through MCP.
- Avoid adding release-report fields unless they are deterministic and improve
  readiness clarity without broadening the release surface.

Phase 6 risk before execution:
- Documentation could accidentally imply hosted/shared MCP readiness, live query
  discovery, PDF batch download support, or MCP review mutation.
- Release notes could overstate the local surrogate trial as real colleague
  validation.

Phase 6 next action:
- Patch `docs/mcp_trial_checklist.md`, `docs/known_limitations.md`,
  `docs/troubleshooting.md`, and `docs/release_notes_0.1.0.md` with conservative
  local-only language.

## Update - local MCP follow-on Phase 6 completed

Phase 6 execution result:
- `docs/mcp.md` now documents deferred query discovery, PDF batch intake, and
  review-write MCP mutation as disabled/gated surfaces.
- `docs/mcp_trial_checklist.md` now asks trial reviewers to confirm review
  mutation, query discovery, PDF batch, restore, and destructive MCP tools are
  absent.
- `docs/mcp_trial_checklist.md` now records skipped live fetches separately from
  failures and points to `ra review-write status` only as a CLI-only prototype
  check.
- `docs/known_limitations.md` now records:
  - query-based arXiv discovery is not live-enabled;
  - PDF batch downloads are not enabled;
  - review-write is CLI-only and not exposed through MCP;
  - mocked 25-paper batch scale does not prove live arXiv reliability.
- `docs/troubleshooting.md` now documents how to inspect blocked batch grants and
  audit records.
- `docs/release_notes_0.1.0.md` now records real colleague MCP setup and live
  arXiv scale as manual validation items, while documenting local-only optional
  MCP support.

Phase 6 tests:
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 6 audit as another developer:
- Docs do not imply hosted/shared MCP readiness.
- Docs preserve optional MCP and local stdio framing.
- Query discovery and PDF batch are clearly design-gated and not enabled.
- Review-write is described as CLI-only; MCP mutation remains disabled.
- The docs do not claim a real colleague MCP setup trial or live arXiv scale
  validation.
- Final review-write audit found that rapid identical proposals could collide
  because IDs used second-resolution timestamps. This was fixed by adding a
  random confirmation nonce, writing proposal JSON atomically, and adding a
  repeated-proposal regression test.

Phase 6 tidy result:
- No generated docs or private artifacts were created.
- No release-report code changes were added because the existing deterministic
  readiness surface is sufficient for this phase.

Interpretation:
- Documentation now matches the implemented conservative boundary.
- All planned phases are complete enough for final validation, staging, and a
  focused commit.

## Update - local MCP follow-on final validation completed

Final validation commands:
- `timeout 240 python -m pytest tests/integration/test_cli_commands.py::test_cli_review_write_propose_apply_and_conflict tests/integration/test_cli_commands.py::test_cli_review_write_creates_distinct_repeated_proposals tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands -q`:
  `3 passed`.
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q`:
  `58 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 5 env PYTHONPATH=src python -m research_assistant.adapters.mcp_server --help`:
  passed.
- `python -m research_assistant.cli mcp status`: reported
  `default_mode: read_only`, `destructive_tools_enabled: false`, and
  `review_write_enabled: false`.
- `python -m research_assistant.cli review-write status`: reported
  `status: prototype_cli_only` and `mcp_exposed: false`.
- `git diff --check`: passed.

Final audit:
- MCP exposed tools are still the local inspection tools plus
  `ra_plan_arxiv_batch_intake` and grant-bound `ra_run_arxiv_batch_intake`; no
  review mutation, PDF batch, restore, delete, or arbitrary file tool is exposed.
- H1 remains external/manual because no real colleague performed the MCP setup
  trial in this autonomous run.
- H2 is narrowed to deterministic mocked local mechanics at 25-paper scale; live
  arXiv 25/50/100 behavior remains a bounded manual validation item.
- H3 has a design gate and remains live-disabled.
- H4 has a design gate and remains execution-disabled.
- H5 has a CLI-only confirmation prototype; MCP exposure remains deferred.
- `.codex` remains untracked local scratch and must not be committed.

## Update - local MCP remaining gap closure started

New objective:
- Execute `docs/plans/local_mcp_remaining_gap_closure_plan_2026-05-02.md` after
  commit `7043acc Validate local MCP expansion gates`.

Requested execution loop:
- create an explicit plan under `docs/plans`;
- update this reset memo;
- audit the plan as another developer;
- execute each phase one by one;
- for each phase: plan, execute, test, audit, tidy, update reset memo;
- continue without human intervention unless the next phase is not justified;
- commit modified files after the whole plan finishes;
- write a detailed summary with results, suggestions, and explicit hypotheses.

Initial repo baseline:
- Branch: `main...origin/main [ahead 2]`.
- Recent HEAD: `7043acc Validate local MCP expansion gates`.
- Working tree before this pass: `.codex` untracked local scratch only.

Initial gap interpretation:
- Real colleague MCP validation and live arXiv scale cannot be honestly
  manufactured in an autonomous local pass.
- This pass should close implementation/readiness gaps that can be tested
  offline, while keeping external/live evidence explicitly manual.

Next safe step:
- Run Phase 0 baseline and independent plan audit.

## Update - local MCP H1 external trial result accepted

New input:
- The user provided a sanitized H1 external MCP trial result from another
  environment on 2026-05-03.
- The trial runner was a Codex external agent using Linux WSL2, Python 3.11.14,
  `research-assistant==0.1.0`, and Python MCP SDK `mcp==1.26.0`.
- The trial used demo workspace `/tmp/ra-mcp-h1-trial` and no maintainer
  assistance.

Plan for this update:
- Treat the returned H1 result as direct external evidence.
- Record the sanitized result without private papers, raw PDFs, extracted text,
  credentials, or private paths.
- Update the validation index and release-report H1 gate status from
  `blocked_external` to `accepted`.
- Capture the two setup lessons: active Python environment fallback when venv
  creation is unavailable, and sandboxed stdio clients may need an
  outside-sandbox retry.
- Tidy generated packaging metadata by removing tracked `egg-info` files from
  version control while keeping `*.egg-info/` ignored.

Execution result:
- Added
  `docs/validation/local_mcp_h1_external_trial_result_2026-05-03.md`.
- Updated `docs/validation/local_mcp_external_validation_records.md`:
  - H1 is now `accepted`;
  - first successful MCP tool call took 0.305 seconds;
  - required read-only tools passed;
  - unsafe tools were absent;
  - `review-write status` reported `mcp_exposed: false`;
  - optional live batch-grant check was skipped, which is acceptable for H1.
- Updated `mcp_readiness.gate_status.colleague_mcp_trial`:
  - `status: accepted`;
  - `evidence: external_agent_stdio_trial_passed_2026_05_03`;
  - `result_record:
    docs/validation/local_mcp_h1_external_trial_result_2026-05-03.md`.
- Updated release-report assertions in
  `tests/integration/test_individual_release_cli.py`.
- Updated troubleshooting/checklist docs:
  - `docs/mcp.md`;
  - `docs/troubleshooting.md`;
  - `docs/mcp_trial_checklist.md`;
  - `docs/validation/local_mcp_h1_external_agent_instructions.md`.
- Updated release notes and known limitations to reflect:
  - H1 external setup accepted;
  - H2 live explicit-ID source intake accepted;
  - H3 query discovery, H4 PDF execution, and H5 MCP review-write still gated.
- Removed tracked generated packaging metadata under
  `src/research_assistant.egg-info/`; `*.egg-info/` is already ignored.

Validation:
- `PYTHONPATH=src timeout 240 python -m pytest tests/integration/test_individual_release_cli.py tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py -q`:
  `25 passed`.
- `PYTHONPATH=src timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `PYTHONPATH=src timeout 300 scripts/run_packaging_smoke.sh`: passed; dry-run
  install would install `research-assistant-0.1.0`.
- `PYTHONPATH=src timeout 60 python -m research_assistant.cli release-report`:
  completed with expected workspace warnings and showed H1
  `colleague_mcp_trial.status: accepted`.
- `git diff --check`: passed.

Audit as another developer:
- H1 acceptance is now backed by direct returned external evidence, not a local
  surrogate.
- The accepted H1 claim is intentionally narrow: demo-workspace local stdio MCP
  setup, read-only tool usability, and unsafe-tool absence.
- H1 does not validate H2 live arXiv execution, H3 live query discovery, H4 PDF
  download execution, or H5 MCP review mutation.
- Review-write remains absent from MCP.
- The external result reported a sandbox-specific stdio issue, but the same
  server/client succeeded outside the sandbox; this is a documentation
  follow-up, not a server blocker.
- Removing tracked `src/research_assistant.egg-info/` is appropriate because
  install/build metadata is generated and already ignored by `.gitignore`.

Tidy result:
- `UNKNOWN.egg-info/`, `dist/`, `build/`, pycache, and local workspace outputs
  remain ignored generated artifacts and are not staged.
- No raw artifacts, source archives, audit logs, manifests, PDFs, credentials,
  or private paths were introduced.

Interpretation and next-phase justification:
- H1 is accepted for local stdio MCP setup/read-only safety in a demo
  workspace.
- H2 is already accepted for grant-bound explicit-ID source intake at 25/50/100
  public IDs.
- H3-live remains `manual_live_approval_required`; it should only proceed after
  explicit approval for a bounded non-private live query smoke.
- H4 remains deferred behind PDF execution preconditions.
- H5 remains deferred behind UX/audit/undo/confirmation design evidence before
  any MCP mutation exposure.

## Update - local MCP H2 live arXiv scale validation completed

Objective:
- Use the user's explicit approval on 2026-05-03 Asia/Hong_Kong to run bounded
  live arXiv network commands for H2.

Execution plan:
- Use public sanitized arXiv IDs only.
- Use `/tmp` workspaces only.
- Run 25 first, then 50 only if 25 is comfortable, then 100 only if 50 is
  comfortable.
- Commit only sanitized summaries, not manifests, audit logs, raw source
  archives, or extracted text.

Live run results:
- 25-paper run:
  - workspace: `/tmp/ra-live-arxiv-source-25-2026-05-03`;
  - IDs: `2401.00001` through `2401.00025`;
  - plan hash:
    `d7ace3c2ad50588be98aded126fc8fb71ffc6a032d16778a9e2d3ce33960c598`;
  - grant: `mcp_grant_9afbf05b811c039a`;
  - timeout: 900s;
  - elapsed: 153.99s;
  - attempted: 25;
  - fetched/available: 17;
  - skipped duplicates: 0;
  - command failures: 0;
  - status mix: 17 available, 7 failed source-structure extraction, 1
    unavailable source;
  - audit events: 28.
- 50-paper run:
  - workspace: `/tmp/ra-live-arxiv-source-50-2026-05-03`;
  - IDs: `2401.00001` through `2401.00050`;
  - plan hash:
    `75b53884465a18b20889f2fb1aac8f1fa44c3d81cb73fcb4e6e8e19d5c9b3cee`;
  - grant: `mcp_grant_5709d0cb72cc1371`;
  - timeout: 1800s;
  - elapsed: 167.70s;
  - attempted: 50;
  - fetched/available: 40;
  - skipped duplicates: 0;
  - command failures: 0;
  - status mix: 40 available, 9 failed source-structure extraction, 1
    unavailable source;
  - audit events: 53.
- 100-paper run:
  - workspace: `/tmp/ra-live-arxiv-source-100-2026-05-03`;
  - IDs: `2401.00001` through `2401.00100`;
  - plan hash:
    `91706256a336d8f9c4ea04cf9289482df506638555cf8aa8970e9503ac64a42e`;
  - grant: `mcp_grant_9e7440cbe714d6af`;
  - timeout: 3600s;
  - elapsed: 591.90s;
  - attempted: 100;
  - fetched/available: 87;
  - skipped duplicates: 0;
  - command failures: 0;
  - status mix: 87 available, 12 failed source-structure extraction, 1
    unavailable source;
  - audit events: 103.

Audit as another developer:
- All live runs completed within their bounded timeouts.
- All generated source archives, manifests, and audit logs stayed under `/tmp`
  workspaces and are not committed.
- No review status was marked `approved`.
- Source extraction failures were visible and bounded as review-material
  limitations rather than hidden command failures.
- Initial duplicate/no-overwrite rerun exposed a real plan-hash drift bug:
  duplicate diagnostics changed the recomputed plan hash after records existed.
- Fixed the plan hash to exclude mutable duplicate diagnostics while still
  binding ordered IDs, paper IDs, URLs, destination, policies, and
  candidate-file metadata.
- Added a regression test covering rerun duplicates created after grant
  creation.
- Verified patched-checkout duplicate rerun with fresh grant
  `mcp_grant_6341ba16caf9d735`: 25 attempted, 25 skipped duplicates, 0 fetched,
  0 failures, 0.09s.

Documentation and reporting updates:
- Updated `docs/validation/local_mcp_external_validation_records.md` with H2
  classification `accepted`.
- Updated `docs/validation/local_mcp_live_arxiv_scale_protocol.md` with the
  sanitized result table.
- Updated `ra release-report` H2 live evidence from
  `manual_bounded_validation_pending` to
  `accepted_25_50_100_public_id_runs_2026_05_03`.

Validation after code/docs updates:
- `PYTHONPATH=src timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q`:
  `16 passed`.
- `PYTHONPATH=src timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `PYTHONPATH=src timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Interpretation:
- H2 is accepted for public explicit-ID source intake at 25/50/100 with local
  grants, bounded timeouts, useful manifests/audits, no automatic approval, and
  duplicate/no-overwrite behavior fixed and verified.
- H2 does not validate query discovery or PDF download execution; those remain
  separate H3/H4 gates.

Next safe step:
- Commit the H2 evidence and duplicate-rerun fix.

## Update - local MCP H1 external agent handoff completed

Objective:
- Answer the H1 handoff question by writing explicit instructions for another
  agent in another environment and defining the exact sanitized result needed
  to update the evidence record.

Execution result:
- Added `docs/validation/local_mcp_h1_external_agent_instructions.md`.
- Linked it from `docs/mcp_trial_checklist.md`.
- Linked it from the H1 section of
  `docs/validation/local_mcp_external_validation_records.md`.

What the handoff asks the external agent to do:
- Install with MCP support.
- Create a fresh demo workspace under `/tmp/ra-mcp-h1-trial`.
- Configure a local stdio MCP client using `ra-mcp --root
  /tmp/ra-mcp-h1-trial`.
- Exercise required MCP tools against `demo_transport_paper`.
- Confirm unsafe `research-assistant` MCP tools are absent.
- Confirm `ra review-write status` reports `mcp_exposed: false`.
- Return a sanitized Markdown result with environment, timing, tool inventory,
  required tool-call outcomes, review-write boundary, optional batch-grant
  boundary, problems/suggestions, and privacy confirmation.

Audit as another developer:
- The handoff uses demo data only and forbids private papers, PDFs, extracted
  text, credentials, shell history, private paths, and workspace archives.
- It distinguishes required H1 setup/read-only evidence from the optional
  batch-grant boundary check.
- It does not require live arXiv execution for H1.
- It does not claim H1 is complete without the returned external result.
- It lets the runner use an anonymous label unless they explicitly opt in to
  being identified.

Validation after writing the handoff:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `git diff --check`: passed.

Interpretation:
- H1 remains `blocked_external` until a real external result is returned.
- Release-report H1 gate status is also `blocked_external`, matching the
  validation record.
- Once a result is returned, update
  `docs/validation/local_mcp_external_validation_records.md` and optionally
  fill `docs/mcp_colleague_trial_record_template.md`.

Next safe step:
- Send `docs/validation/local_mcp_h1_external_agent_instructions.md` to the
  external agent or fresh environment.

## Update - local MCP external/live validation Phase 0 completed

Phase 0 plan for the phase:
- Confirm the repo baseline remains green.
- Audit the new external/live validation plan before execution.

Phase 0 execution result:
- `git status --short --branch`: `main...origin/main [ahead 3]`.
- Recent HEAD: `1737050 Close local MCP readiness gaps`.
- `python -m research_assistant.cli release-report` still reports:
  - colleague MCP trial: `manual_external_required`;
  - explicit-ID arXiv live scale: `manual_bounded_validation_pending`;
  - live query discovery: disabled;
  - PDF batch execution: disabled;
  - review-write MCP exposure: false.

Phase 0 tests:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py -q`:
  `11 passed`.
- `git diff --check`: passed.

Phase 0 audit as another developer:
- The plan uses existing validation templates and stays local-MCP scoped.
- It does not claim a real colleague trial or live arXiv evidence.
- It does not add hosted/shared MCP work.
- It does not authorize live network execution during this autonomous pass.
- Clarified that live command snippets in this plan/protocol docs are future
  operator commands and are not executed without separate approval.

Phase 0 tidy result:
- No generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- Baseline is green and the plan is honest about external/live gates.
- Phase 1 is justified to create a sanitized validation record pack for future
  evidence.

## Update - local MCP external/live validation Phase 1 completed

Phase 1 plan for the phase:
- Create a sanitized local MCP validation record index using existing templates.
- Link it from MCP docs/checklist/limitations.
- Keep all external/live evidence statuses conservative.

Phase 1 execution result:
- Added `docs/validation/local_mcp_external_validation_records.md`.
- The record pack includes:
  - H1 real colleague MCP setup evidence requirements;
  - H2 live explicit-ID arXiv source scale record requirements;
  - H3-live query-discovery smoke record requirements;
  - H4 PDF execution precondition record;
  - H5 MCP review-write precondition record.
- Linked the record pack from:
  - `docs/mcp_trial_checklist.md`;
  - `docs/mcp.md`;
  - `docs/known_limitations.md`.

Phase 1 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 1 audit as another developer:
- The record pack explicitly prohibits private papers, raw PDFs, extracted text,
  workspace archives, grant/audit logs, credentials, tokens, shell history, and
  private colleague identity.
- H1/H2/H3 remain manual/external/live required.
- H4/H5 remain precondition-gated.

Phase 1 tidy result:
- Docs-only phase; no generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- There is now one safe index for future local MCP external/live evidence.
- Phase 2 remains justified to define the bounded live arXiv source scale
  protocol without running live network.

## Update - local MCP external/live validation Phase 2 completed

Phase 2 plan for the phase:
- Add an approval-gated live arXiv source scale protocol.
- Define 25/50/100 paper bounds, commands, metrics, and stop conditions.
- Do not run live network in this autonomous pass.

Phase 2 execution result:
- Added `docs/validation/local_mcp_live_arxiv_scale_protocol.md`.
- The protocol defines:
  - explicit approval gate;
  - `/tmp` workspace convention;
  - allowed domains;
  - 25/50/100 escalation order;
  - timeouts of 900/1800/3600 seconds;
  - plan/grant/run/audit commands;
  - metrics to record;
  - pass/narrow/fail criteria;
  - sanitized result table.
- The validation record pack points to the live scale protocol.

Phase 2 tests:
- `timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q`:
  `15 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 2 audit as another developer:
- No live network was executed.
- The protocol requires explicit approval before future live runs.
- It prohibits committing source archives, manifests, audit logs, extracted text,
  and private workspace content.
- H2 remains `manual_live_approval_required`.

Phase 2 tidy result:
- Docs-only phase; no generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- H2 now has a bounded operator protocol but no live evidence yet.
- Phase 3 remains justified to define the live query-discovery smoke protocol
  without enabling live query in code or MCP.

## Update - local MCP external/live validation Phase 3 completed

Phase 3 plan for the phase:
- Add a live query discovery pre-enablement protocol.
- Keep live query discovery disabled in code and MCP.
- Tie any future live query to pinned candidate-file planning.

Phase 3 execution result:
- Added `docs/validation/local_mcp_live_query_discovery_protocol.md`.
- The protocol defines:
  - explicit approval gate;
  - allowed endpoint `https://export.arxiv.org/api/query`;
  - initial max candidates of 10 and hard pre-approval maximum of 50;
  - pagination and timeout bounds;
  - candidate-file schema requirements;
  - safe plan/grant/run flow through a saved candidate file;
  - metrics and pass/narrow/fail criteria.

Phase 3 tests:
- `timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q`:
  `15 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 3 audit as another developer:
- Live query discovery remains disabled.
- The future command shape is documented as not implemented/enabled.
- No network was run.
- The only execution path described after discovery is the existing
  grant-bound pinned candidate-file path.

Phase 3 tidy result:
- Docs-only phase; no generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- H3-live now has a bounded approval protocol but no live evidence.
- Phase 4 remains justified to define PDF execution and MCP review-write
  preconditions without enabling either write surface.

## Update - local MCP external/live validation Phase 4 completed

Phase 4 plan for the phase:
- Add a shared PDF execution and MCP review-write precondition checklist.
- Link it from MCP and architecture docs.
- Do not enable PDF execution or MCP review mutation.

Phase 4 execution result:
- Added `docs/validation/local_mcp_write_surface_preconditions.md`.
- The document defines:
  - shared write-surface rules;
  - PDF batch execution implementation requirements;
  - PDF tests and tiny-live-smoke requirements;
  - MCP review-write implementation requirements;
  - MCP review-write tests and human review requirements;
  - stop conditions for both surfaces.
- Linked the precondition document from:
  - `docs/mcp.md`;
  - `docs/architecture/mcp_pdf_batch_intake_design.md`;
  - `docs/architecture/mcp_review_write_design.md`.

Phase 4 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 4 audit as another developer:
- No PDF downloader was added.
- No MCP review mutation was exposed.
- Preconditions explicitly forbid automatic approval and hosted/shared MCP drift.
- H4/H5 remain precondition-gated.

Phase 4 tidy result:
- Docs-only phase; no generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- H4/H5 now have concrete precondition checklists.
- Phase 5 remains justified to point release-report gate entries to the new
  validation/protocol docs while keeping statuses conservative.

## Update - local MCP external/live validation Phase 5 completed

Phase 5 plan for the phase:
- Add validation/protocol doc path references to release-report MCP gates.
- Add regression assertions.
- Keep all statuses conservative.

Phase 5 execution result:
- Updated `mcp_readiness_status(...)` gate entries with:
  - `docs/mcp_colleague_trial_record_template.md`;
  - `docs/validation/local_mcp_external_validation_records.md`;
  - `docs/validation/local_mcp_live_arxiv_scale_protocol.md`;
  - `docs/validation/local_mcp_live_query_discovery_protocol.md`;
  - `docs/validation/local_mcp_write_surface_preconditions.md`.
- Added assertions to `tests/integration/test_individual_release_cli.py`.
- `python -m research_assistant.cli release-report` now displays those protocol
  paths under `mcp_readiness.gate_status`.

Phase 5 tests:
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 5 audit as another developer:
- Release-report now points to concrete evidence/protocol docs.
- No manual/live evidence is marked passed.
- Live query remains disabled, PDF execution disabled, and MCP review mutation
  disabled.
- `release-report` rewrote ignored generated artifact metadata; it remains
  ignored and must not be committed.

Phase 5 tidy result:
- No generated/private artifacts staged.

Interpretation and next-phase justification:
- Manual gates are now discoverable from release-report.
- Phase 6 final validation and commit are justified.

## Update - local MCP external/live validation final validation completed

Final validation commands:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q`:
  `70 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 5 env PYTHONPATH=src python -m research_assistant.adapters.mcp_server --help`:
  passed.
- `python -m research_assistant.cli release-report`: completed with existing
  workspace warnings and showed protocol paths for:
  - external validation records;
  - live arXiv source scale;
  - live query discovery;
  - PDF/review-write preconditions.
- `git status --short --ignored`: only intended tracked/untracked docs/code
  changes plus ignored generated/scratch artifacts.
- `git diff --check`: passed.

Final audit:
- No real colleague trial was fabricated.
- No live arXiv network was executed.
- Live query discovery remains disabled.
- PDF batch execution remains disabled.
- MCP review mutation remains disabled.
- Generated/scratch artifacts remain ignored and must not be committed.

Final interpretation:
- The remaining external/live gaps now have explicit record/protocol documents
  and release-report references.
- The actual evidence remains pending until a real colleague trial or explicitly
  approved live run is completed.

## Update - local MCP H1-H5 full hypothesis test plan started

New objective:
- Execute `docs/plans/local_mcp_h1_h5_full_hypothesis_test_plan_2026-05-02.md`
  after commit `3dd4ab6 Document local MCP external validation gates`.

Requested execution loop:
- create a detailed plan under `docs/plans`;
- update this reset memo;
- audit the plan as another developer;
- execute every phase using plan/execute/test/audit/tidy/reset-memo updates;
- continue automatically if no major issue;
- ask for direction when the next phase is not justified;
- commit modified files;
- summarize results and next hypotheses.

Initial repo baseline:
- Branch: `main...origin/main [ahead 4]`.
- Recent HEAD: `3dd4ab6 Document local MCP external validation gates`.
- Working tree before this pass: clean.

Initial interpretation:
- Full acceptance/rejection/narrowing of H1-H3 requires external/live evidence.
- H4/H5 require explicit decisions before enabling higher-risk write surfaces.
- This pass can proceed only as far as evidence and approvals allow; otherwise
  it must record blockers rather than overclaim completion.

Next safe step:
- Run Phase 0 baseline and audit the full H1-H5 plan.

## Update - local MCP H1-H5 full hypothesis Phase 0 completed

Phase 0 plan for the phase:
- Confirm the current local MCP implementation remains green.
- Audit the full H1-H5 hypothesis plan before attempting external/live tests.

Phase 0 execution result:
- `git status --short --branch`: `main...origin/main [ahead 4]`.
- Recent HEAD: `3dd4ab6 Document local MCP external validation gates`.
- Added `docs/plans/local_mcp_h1_h5_full_hypothesis_test_plan_2026-05-02.md`.

Phase 0 tests:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q`:
  `70 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 0 audit as another developer:
- The plan correctly states that H1 needs a real colleague/fresh reader.
- The plan correctly states that H2/H3-live need explicit live network approval
  and sanitized inputs.
- The plan keeps PDF execution and MCP review-write behind safety gates.
- The plan does not add hosted/shared MCP scope.
- The evidence rule prevents marking accepted/rejected/narrowed without direct
  evidence.

Phase 0 tidy result:
- No generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- The local baseline is green.
- Phase 1 cannot be completed in this autonomous session without a real
  colleague or fresh reader. Under the plan, H1 can only be classified as
  `blocked_external` unless the user provides/arranges real colleague evidence.

## Update - local MCP H1-H5 full hypothesis Phase 1 completed

Phase 1 plan for the phase:
- Attempt H1 real colleague MCP setup validation.
- If no real colleague/fresh-reader evidence is available, classify H1 as
  `blocked_external` rather than overclaiming.

Phase 1 execution result:
- The user chose to record H1 as blocked and proceed.
- Updated `docs/validation/local_mcp_external_validation_records.md`:
  - H1 current status is now `blocked_external`;
  - reason is no real colleague/fresh-reader MCP client trial is available in
    this autonomous run.
- Updated `mcp_readiness.gate_status.colleague_mcp_trial.status` to
  `blocked_external`.
- Updated release-report assertions accordingly.

Phase 1 tests:
- Pending focused validation after this memo update.

Phase 1 audit as another developer:
- This is honest: local surrogate evidence is not counted as H1 completion.
- No colleague identity or private metadata was recorded.
- The classification is a blocker, not acceptance/rejection/narrowing.

Interpretation and next-phase justification:
- H1 is classified as `blocked_external`.
- Phase 2 is justified only if explicit live network approval and sanitized
  arXiv ID lists are available; otherwise H2 must be classified as
  `blocked_live_approval`.

## Update - local MCP remaining gap closure Phase 0 completed

Phase 0 plan for the phase:
- Confirm baseline MCP tests remain green.
- Audit the new gap-closure plan before implementation.

Phase 0 execution result:
- `git status --short --branch`: `main...origin/main [ahead 2]` with `.codex`
  untracked before this pass.
- `git log --oneline -5`: HEAD `7043acc Validate local MCP expansion gates`.
- `python -m research_assistant.cli mcp status`: reported
  `default_mode: read_only`, `destructive_tools_enabled: false`, and
  `review_write_enabled: false`.

Phase 0 tests:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py -q`:
  `11 passed`.
- `git diff --check`: passed.

Phase 0 audit as another developer:
- The plan preserves local stdio MCP scope and does not add hosted/shared
  platform work.
- The plan explicitly separates local deterministic implementation/readiness
  work from external colleague and live arXiv evidence.
- One sequencing issue was corrected: Phase 1 release-report `gate_status` is a
  living readiness surface that later phases may update after query/PDF/review
  hardening lands.
- Query work remains offline candidate-file planning; PDF work remains
  policy-only; review-write remains CLI-only.

Phase 0 tidy result:
- No generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- Baseline is safe and green.
- Phase 1 is justified to add explicit MCP gate visibility to `ra
  release-report` without changing permissions.

## Update - local MCP remaining gap closure Phase 1 completed

Phase 1 plan for the phase:
- Add deterministic MCP gate visibility to `ra release-report`.
- Do not make optional MCP a blocker.
- Do not mark external colleague or live arXiv validation as passed.

Phase 1 execution result:
- Extended `mcp_readiness_status(...)` with `gate_status`.
- `gate_status` now reports:
  - real colleague MCP trial as `manual_external_required`;
  - explicit-ID arXiv source batch as `available_with_local_grant`;
  - deterministic mocked 25-paper local evidence and pending live scale
    evidence separately;
  - query discovery as design-gated with live query disabled;
  - PDF batch intake as design-gated with execution disabled;
  - review-write as CLI-only with `mcp_exposed: false`;
  - packaging after MCP gap work as manual rebuild recommended.
- Added release-report assertions in
  `tests/integration/test_individual_release_cli.py`.

Phase 1 tests:
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `git diff --check`: passed.
- `python -m research_assistant.cli release-report`: completed and displayed
  the new `mcp_readiness.gate_status` fields.

Phase 1 audit as another developer:
- The report is explicit without implying hosted/shared MCP readiness.
- Manual evidence items are still manual; no colleague trial or live arXiv
  scale is claimed as passed.
- Optional MCP absence remains non-blocking.
- `release-report` rewrote ignored `dist/release_artifacts_manifest.json`; it
  remains generated/ignored and must not be committed.

Phase 1 tidy result:
- No private files staged.
- Generated release artifact metadata remains ignored.

Interpretation and next-phase justification:
- MCP gate visibility is now substantially clearer.
- Phase 2 remains justified to create a safe non-private colleague trial record
  template for future H1 evidence.

## Update - local MCP remaining gap closure Phase 2 completed

Phase 2 plan for the phase:
- Add a real colleague MCP trial record template.
- Link it from trial/release docs.
- Keep H1 manual/external until a real colleague trial is recorded.

Phase 2 execution result:
- Added `docs/mcp_colleague_trial_record_template.md`.
- Updated `docs/mcp_trial_checklist.md` to point to the template and clarify
  that local surrogate runs do not count as H1 external usability evidence.
- Updated `docs/known_limitations.md` and `docs/release_notes_0.1.0.md` to
  reference the template for future real colleague MCP setup evidence.

Phase 2 tests:
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 2 audit as another developer:
- The template records only non-private metadata.
- It explicitly prohibits private titles, raw PDFs, extracted text,
  credentials, and colleague identity unless opt-in.
- It does not claim H1 is passed.

Phase 2 tidy result:
- Docs-only phase; no generated artifacts created.
- No files staged.

Interpretation and next-phase justification:
- H1 now has a safe future evidence format, but remains manual/external.
- Phase 3 remains justified to move query discovery from design-only to
  offline pinned-candidate planning without live network.

## Update - local MCP remaining gap closure Phase 3 completed

Phase 3 plan for the phase:
- Add offline arXiv candidate-file validation and planning.
- Do not enable live query discovery.
- Bind exact ordered IDs and candidate-file checksum into the plan hash.

Phase 3 execution result:
- Added candidate-file helpers in `src/research_assistant/ingest/arxiv_batch.py`.
- Added CLI support:
  - `ra arxiv-batch candidate-file inspect --path <candidate_file>`;
  - `ra arxiv-batch plan --candidate-file <candidate_file> --max-papers <n>`.
- Added fixture:
  `tests/fixtures/mcp/arxiv_candidates/query_transport_maps_hmc.json`.
- Candidate-file planning:
  - is read-only;
  - rejects malformed, oversized, duplicate, empty, or missing-ID files;
  - uses the file's ordered arXiv IDs;
  - includes candidate-file metadata/checksum in the plan core;
  - changes plan hash when candidate order/content changes.
- Updated release-report `gate_status.query_discovery` to
  `offline_candidate_file_planning_available` while keeping
  `live_query_enabled: false`.
- Updated `docs/mcp.md` and `docs/known_limitations.md`.

Phase 3 tests:
- `timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q`:
  `14 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `git diff --check`: passed.

Phase 3 audit as another developer:
- No live network path was added.
- Query-only live planning still blocks.
- Candidate-file plan hashes are bound to exact ordered candidate identity.
- Planning remains read-only and does not create local grants or downloads.

Phase 3 tidy result:
- Only a non-private JSON fixture was added.
- No generated/private artifacts staged.

Interpretation and next-phase justification:
- H3 is narrowed from design-only to offline pinned-candidate planning.
- Live query discovery remains disabled and still needs bounded live approval.
- Phase 4 remains justified to add executable PDF policy checks without
  enabling PDF download execution.

## Update - local MCP remaining gap closure Phase 4 completed

Phase 4 plan for the phase:
- Add executable PDF batch policy checks.
- Do not implement PDF download execution.
- Surface policy availability in release-report.

Phase 4 execution result:
- Added `src/research_assistant/ingest/pdf_batch_policy.py`.
- Policy checks validate:
  - max file count;
  - max total bytes;
  - max per-file bytes;
  - destination is `inbox`;
  - overwrite policy is `no_overwrite`;
  - PDF URL domains are `arxiv.org` or `export.arxiv.org`;
  - missing URLs and invalid declared byte counts.
- Added `tests/integration/test_pdf_batch_policy.py`.
- Updated `mcp_readiness.gate_status.pdf_batch_intake` to report
  `policy_checks_available: true` and `execution_enabled: false`.
- Updated `docs/mcp.md` and `docs/known_limitations.md`.

Phase 4 tests:
- `timeout 240 python -m pytest tests/integration/test_pdf_batch_policy.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_individual_release_cli.py -q`:
  `32 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `git diff --check`: passed.

Phase 4 audit as another developer:
- No downloader was added.
- No MCP PDF batch execution tool was exposed.
- Policy checks are deterministic and offline.
- PDF batch output remains disabled until checksum, cleanup, manifest/audit,
  duplicate, and live-smoke requirements are implemented and recorded.

Phase 4 tidy result:
- No generated artifacts created.
- No private files staged.

Interpretation and next-phase justification:
- H4 is narrowed from design-only to executable policy checks with execution
  disabled.
- Phase 5 remains justified to improve CLI review-write readiness while keeping
  MCP mutation disabled.

## Update - local MCP remaining gap closure Phase 5 completed

Phase 5 plan for the phase:
- Improve review-write CLI readiness/status.
- Add expired-proposal cleanup with dry-run default.
- Keep MCP review mutation disabled.

Phase 5 execution result:
- Extended `review_write_status(...)` with proposal counts:
  - total;
  - pending;
  - expired;
  - applied;
  - invalid.
- Added `cleanup_expired_proposals(...)`.
- Added CLI command:
  - `ra review-write cleanup-expired`;
  - `ra review-write cleanup-expired --apply`.
- Cleanup defaults to dry-run and only removes expired proposal records when
  `--apply` is present; it does not alter paper summaries or review state.
- Updated release-report `gate_status.review_write` with proposal counts.
- Updated `docs/mcp.md` and `docs/known_limitations.md`.

Phase 5 tests:
- `timeout 240 python -m pytest tests/integration/test_cli_commands.py -q`:
  `26 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `git diff --check`: passed.

Phase 5 audit as another developer:
- Review-write remains CLI-only and reports `mcp_exposed: false`.
- Cleanup is bounded to expired proposal JSON files and is dry-run by default.
- No MCP review mutation tool was added.
- Proposal status counts improve readiness visibility without broadening
  permission.

Phase 5 tidy result:
- Tests created proposal/audit files only under pytest temp workspaces.
- No generated/private artifacts staged.

Interpretation and next-phase justification:
- H5 is safer for later UX review but MCP exposure remains deferred.
- Phase 6 remains justified to rebuild/check packaging outputs and fix scratch
  hygiene without committing generated artifacts.

## Update - local MCP remaining gap closure Phase 6 completed

Phase 6 plan for the phase:
- Add `.codex` scratch hygiene.
- Run packaging smoke and rebuild release artifacts.
- Keep generated artifacts uncommitted.
- Update docs to reflect current MCP gap-closure state.

Phase 6 execution result:
- Added `.codex` and `.codex/` to `.gitignore`.
- Ran packaging smoke successfully:
  - metadata entrypoint test passed;
  - `python -m pip install --dry-run --no-build-isolation .` would install
    `research-assistant-0.1.0`.
- Rebuilt local release artifact successfully:
  - wheel: `research_assistant-0.1.0-py3-none-any.whl`;
  - size: `145857` bytes;
  - SHA256:
    `f9f4ae52ce7c53a5acfe3332b567347d86dce55248c0a905821fea1e2e385a0c`.
- `src/research_assistant.egg-info/` metadata was regenerated by packaging and
  now reflects the MCP extra/entrypoint and new package modules.
- `dist/` and `build/` remain ignored generated outputs.
- Updated `docs/release_notes_0.1.0.md` with rebuilt local artifact metadata and
  current MCP capability wording.
- Final audit during this phase found that candidate-file planning needed a
  matching run path. Added `candidate_file` support to
  `run_arxiv_batch_intake(...)` and `ra arxiv-batch run --candidate-file ...`,
  keeping execution grant-bound and offline-pinned.

Phase 6 tests:
- `timeout 300 scripts/run_packaging_smoke.sh`: passed.
- `timeout 300 scripts/build_release_artifacts.sh`: passed.
- `timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q`:
  `14 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q`:
  `59 passed`.
- `git status --short --ignored`: `.codex`, `dist/`, and `build/` are ignored;
  generated artifacts are visible only as ignored files.
- `git diff --check`: passed.

Phase 6 audit as another developer:
- Packaging completed without needing network escalation.
- Generated release artifacts were not staged.
- `.codex` is ignored in both file and directory forms.
- The candidate-file run path remains grant-bound and does not enable live query
  discovery.
- No PDF download execution or MCP review mutation was exposed.

Phase 6 tidy result:
- Ignored generated artifacts remain in `dist/`, `build/`, pycache, and local
  scratch locations.
- No private paper data was introduced.

Interpretation:
- Packaging and scratch hygiene gaps are closed for this local pass.
- All implementation phases are complete; final validation and commit are now
  justified.

## Update - local MCP remaining gap closure final validation completed

Final validation commands:
- `timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q`:
  `70 passed`.
- `timeout 120 scripts/run_fast_tests.sh`: `14 passed`.
- `timeout 5 env PYTHONPATH=src python -m research_assistant.adapters.mcp_server --help`:
  passed.
- `python -m research_assistant.cli mcp status`: reported
  `default_mode: read_only`, `destructive_tools_enabled: false`, and
  `review_write_enabled: false`.
- `python -m research_assistant.cli review-write status`: reported
  `status: prototype_cli_only`, `mcp_exposed: false`, and zero proposal counts
  in the repo root.
- `python -m research_assistant.cli release-report`: showed:
  - `colleague_mcp_trial.status: manual_external_required`;
  - `explicit_id_arxiv_source_batch.status: available_with_local_grant`;
  - `query_discovery.status: offline_candidate_file_planning_available`;
  - `query_discovery.live_query_enabled: false`;
  - `pdf_batch_intake.policy_checks_available: true`;
  - `pdf_batch_intake.execution_enabled: false`;
  - `review_write.mcp_exposed: false`.
- `git diff --check`: passed.

Final audit:
- External H1 evidence remains not recorded.
- Live arXiv 25/50/100 evidence remains pending/manual.
- Live query discovery remains disabled.
- PDF batch download execution remains disabled.
- MCP review mutation remains disabled.
- `dist/`, `build/`, `.codex`, `.claude`, local workspace artifacts, and
  pycache files remain ignored/generated and must not be committed.
- Tracked `src/research_assistant.egg-info/` metadata was regenerated by the
  packaging build and reflects the current package surface, including MCP
  entrypoint/extra and new modules.

Final interpretation:
- All locally closable gaps in the plan are closed or narrowed with deterministic
  evidence.
- The remaining gaps require either a real colleague or explicit bounded live
  network validation.

## Update - local MCP external/live validation plan started

New objective:
- Execute `docs/plans/local_mcp_external_live_validation_plan_2026-05-02.md`
  after commit `1737050 Close local MCP readiness gaps`.

Requested execution loop:
- write a plan under `docs/plans`, using templates where possible;
- update this reset memo;
- audit the plan as another developer;
- execute every justified phase using plan/execute/test/audit/tidy/reset-memo
  updates;
- continue automatically unless the next phase is not justified;
- commit modified files;
- summarize results and next hypotheses.

Initial repo baseline:
- Branch: `main...origin/main [ahead 3]`.
- Recent HEAD: `1737050 Close local MCP readiness gaps`.
- Working tree before this pass: clean.

Initial interpretation:
- The remaining gaps are primarily external/live evidence gates, not ordinary
  local implementation gaps.
- This pass should create sanitized evidence protocols and release-report
  references, but must not claim real colleague or live arXiv validation unless
  such evidence exists.

Next safe step:
- Run Phase 0 baseline and independent plan audit.
