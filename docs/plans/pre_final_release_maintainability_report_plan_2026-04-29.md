# Pre-Final Release Maintainability And Report Plan - 2026-04-29

## Purpose

This plan addresses the remaining pre-final-release gaps that are local to the
repository and should be completed before asking for final tag/publication
approval.

The release target remains the individual local research tool:

- one researcher at a time;
- local filesystem storage;
- offline-by-default workflows;
- Git-based sharing by checkout, inspection, import, and merge;
- generated/parser/benchmark/derivation/traceability/readiness artifacts are
  review material, not scientific approval;
- shared database, hosted service, SSO/RBAC, real-time collaboration, and hosted
  UI are future extensions, not current release requirements.

The specific gaps covered by this plan are:

1. Targeted behavior-preserving refactoring of the release-critical code.
2. Rewriting `proposal/research_development_assistant_design.tex` into an
   accurate final release report/manual for what has actually been built.
3. Adding targeted maintainer comments, docstrings, and programmer-facing
   documentation so another developer can maintain the code without prior
   project history.
4. Re-running the local release validation packet after the refactor/report
   work.
5. Preserving the existing manual blockers for broad release: fresh-reader
   onboarding, real macOS validation, real minimal parser-tool validation, tag
   approval, and publication approval.

## Current Baseline

Recent robust release work completed:

- explicit `WHEEL_PATH` support in `scripts/run_clean_install_smoke.sh`;
- release docs calibrated to the exact wheel hash;
- `synthetic_git_1000` performance evidence;
- clean-checkout gate evidence;
- final gate remains `blocked` for manual external validation and release-owner
  approval, while `ready_for_limited_individual_pilot` is true.

Important current files:

- `docs/proposal/individual_git_release_target.md` - primary release target.
- `docs/release_checklist.md` - release command checklist.
- `docs/release_notes_0.1.0.md` - current release notes and artifact hash.
- `docs/known_limitations.md` - release limitations and trust boundaries.
- `docs/workflows/git_sharing_walkthrough.md` - user-facing Git sharing flow.
- `proposal/research_development_assistant_design.tex` - tracked LaTeX report
  that currently reads as a broad shared-backend proposal and must be rewritten.
- `proposal/research_development_assistant_design.pdf` - tracked rendered PDF.
- `src/research_assistant/cli.py` - large CLI surface and parser definition.
- `src/research_assistant/individual_release.py` - individual workspace,
  backup, diagnostics, demo, artifact, and release-report logic.
- `src/research_assistant/individual_git_release.py` - shareable policy,
  hygiene, merge, validation, performance, fixture, and release-gate logic.
- `tests/integration/test_individual_release_cli.py` - main release regression
  coverage.

Observed maintainability hotspots:

- `src/research_assistant/cli.py` is approximately 1,600+ lines and mixes
  command handlers, parser registration, and broad feature routing.
- `src/research_assistant/individual_release.py` is approximately 1,200+ lines
  and contains several distinct concerns.
- `src/research_assistant/individual_git_release.py` is approximately 1,200+
  lines and contains policy classification, repository hygiene, merge/rebuild,
  validation records, fixture rehearsal, performance, and gate construction.
- The LaTeX report is approximately 2,000 lines and currently centers a
  multi-user/shared-backend framing that no longer matches the current release.

## Non-Negotiable Rules

- Do not change release scope from individual local + Git sharing.
- Do not make the multi-user/database/service platform the primary current
  release story.
- Do not fake fresh-reader, macOS, minimal-machine, tag, or publication
  evidence.
- Do not tag or publish artifacts without explicit release-owner approval.
- Do not commit private PDFs, TeX sources outside the tracked proposal report,
  private datasets, backup archives, generated workspaces, credentials, provider
  keys, tokens, `.codex`, `.claude`, caches, `build/`, `dist/`, or bytecode.
- Do not convert generated/review artifacts into accepted research conclusions.
- Keep refactors behavior-preserving unless a bug is found and documented.
- Prefer small commits or clearly separable staged changes; avoid sweeping
  aesthetic rewrites.
- Use `timeout` around validation commands.
- `docs/plans/` is ignored; force-stage this plan and reset memo updates only
  when committing them intentionally.

## Required Audit Before Execution

Before executing this plan, another agent must audit it from these perspectives:

- **Product scope:** Confirms the plan keeps the current release centered on
  the individual local tool and Git sharing.
- **Engineering risk:** Confirms refactors are behavior-preserving, staged, and
  protected by characterization tests.
- **Documentation accuracy:** Confirms the LaTeX report will describe what is
  implemented, tested, limited, and deferred.
- **Maintainer value:** Confirms comments/docstrings explain non-obvious
  invariants rather than restating obvious code.
- **Release management:** Confirms external validation and release-owner
  approvals remain explicit blockers and are not silently waived.
- **Privacy/data safety:** Confirms report examples, tests, and evidence do not
  leak private papers, private paths, credentials, provider keys, or local
  corpora.

If the audit finds missing points, update this plan before execution and record
the audit result in `docs/plans/reset_memo_2026-04-26.md`.

## Execution Loop

For every phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start, intent, and
   expected risk.
2. Plan the smallest safe action for that phase.
3. Execute the phase.
4. Run focused validation.
5. Audit the result as another developer.
6. Tidy generated outputs and avoid staging private/generated files.
7. Update the reset memo with evidence, blockers, and next step.
8. Commit coherent changes only after validation.

## Phase 0 - Baseline Characterization And Refactor Boundary

### Motivation

Before refactoring, the agent must know which behaviors are release-critical.
The goal is to prevent accidental behavior drift in CLI command names, JSON
schemas, safety checks, merge semantics, and release-gate output.

### Implementation Instructions

- Read:
  - `docs/proposal/individual_git_release_target.md`;
  - `docs/release_checklist.md`;
  - `docs/release_notes_0.1.0.md`;
  - `docs/known_limitations.md`;
  - `docs/workflows/git_sharing_walkthrough.md`;
  - `tests/integration/test_individual_release_cli.py`;
  - `src/research_assistant/cli.py`;
  - `src/research_assistant/individual_release.py`;
  - `src/research_assistant/individual_git_release.py`.
- Record a short refactor boundary in the reset memo:
  - public CLI command names must remain stable;
  - JSON schema versions must remain stable unless explicitly planned;
  - release gate readiness flags must remain semantically identical;
  - backup/restore, repository hygiene, and merge confirmation safety must not
    weaken;
  - parser limitation language must remain conservative.
- Add or strengthen characterization tests before moving code if gaps are found.
  Candidate assertions:
  - `ra --help` still exposes release-critical command groups;
  - `repository-hygiene policy/classify/check` outputs stable classifications;
  - `workspace merge` remains dry-run by default and apply requires explicit
    confirmation;
  - `individual-git-release gate-build` remains blocked without external
    validation and approval;
  - clean-install docs still reference explicit `WHEEL_PATH`;
  - parser scientific accuracy is not certified.

### Tests

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Refactor boundaries are recorded.
- Characterization coverage is sufficient for the files that will be moved or
  reorganized.
- No behavior-changing refactor has started before tests are green.

## Phase 1 - Release-Critical Code Refactor

### Motivation

The current implementation has grown quickly and now has large modules that are
hard for a new maintainer to navigate. A final release should reduce this
maintenance risk without changing product behavior.

### Implementation Instructions

Refactor in small, reversible slices. Keep public imports and CLI behavior
stable.

#### 1.1 CLI organization

- Inspect `src/research_assistant/cli.py`.
- Do not rewrite every command handler.
- Prefer extracting parser-registration helpers by command family inside the
  same file first, or into a small `src/research_assistant/cli_*.py` module only
  if the resulting import graph stays simple.
- Preserve:
  - `main(argv: list[str] | None = None) -> int`;
  - existing command names;
  - existing JSON output shape;
  - integration tests that call `main(...)` directly.
- Candidate low-risk split:
  - keep `_print_json` and `main` in `cli.py`;
  - group release-related parser registration into helper functions;
  - group individual Git command dispatch into a clearly named helper;
  - avoid circular imports from backend modules into CLI modules.

#### 1.2 Individual release module organization

- Inspect `src/research_assistant/individual_release.py`.
- Identify separable concerns:
  - workspace config/init/validate/repair;
  - backup/restore;
  - diagnostics, parser matrix, platform status, privacy status;
  - demo setup/run/clean;
  - release artifacts and release report.
- If splitting files, keep `individual_release.py` as a compatibility facade
  that re-exports existing function names used by CLI/tests.
- Do not change backup archive structure or restore safety behavior.
- Do not weaken config validation or atomic write behavior.
- Do not hide installed-package release-report warnings; they are useful
  release context.

#### 1.3 Individual Git release module organization

- Inspect `src/research_assistant/individual_git_release.py`.
- Identify separable concerns:
  - shareable workspace policy and path classification;
  - repository hygiene and secret/private-path scanning;
  - workspace merge/import/rebuild;
  - validation record/report/substitutes;
  - fixture rehearsal and synthetic performance;
  - gate-build logic.
- If splitting files, keep `individual_git_release.py` as a compatibility
  facade or thin orchestrator exposing the existing function names used by
  CLI/tests.
- Preserve:
  - dry-run-by-default merge;
  - `--apply --confirm-merge` requirement;
  - backup creation before apply;
  - forbidden/private/generated path policy;
  - accepted-audit conflict behavior;
  - local substitute versus real external validation distinction;
  - final gate readiness flags.

#### 1.4 Shared constants and helper cleanup

- Deduplicate only when the duplicate constants create maintenance risk.
- Do not introduce an abstraction just to reduce line count.
- Prefer explicit names such as `REQUIRED_VALIDATION_TYPES` and
  `PUBLICATION_APPROVAL_TYPES` over generic registry abstractions.
- Keep schema versions near the code that emits the schema.

### Tests

Run after every meaningful slice:

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q
timeout 120 scripts/run_fast_tests.sh
timeout 180 scripts/run_bounded_tests.sh
git diff --check
```

Run the release gate after the full refactor:

```bash
GATE_ROOT=/tmp/research-assistant-refactor-gate timeout 300 scripts/run_individual_git_release_gate.sh
```

### Acceptance Criteria

- Behavior is unchanged except for intentionally documented bug fixes.
- Public CLI commands and JSON schemas remain compatible.
- Refactored modules have clearer ownership boundaries.
- Integration tests and release gate remain green or blocked only for the
  expected manual validation/approval items.

## Phase 2 - Targeted Maintainer Comments And Programmer Guide

### Motivation

Another programmer with no project history should be able to understand the
release-critical safety boundaries. The code needs comments where policy,
trust, or data-safety decisions are not obvious from the implementation.

### Implementation Instructions

- Do not blanket-comment every function.
- Add docstrings or short comments only where they explain non-obvious
  invariants, for example:
  - why generated artifacts remain review material;
  - why merge is dry-run by default;
  - why apply mode requires explicit confirmation;
  - why local substitutes do not satisfy external validation;
  - why parser-tool availability does not certify parser scientific accuracy;
  - why backup restore requires dry-run/confirmation safeguards;
  - why certain paths are forbidden or rebuildable for Git sharing.
- Add or update a maintainer document, recommended path:
  - `docs/maintainer_guide.md`
- The maintainer guide should include:
  - release target summary;
  - module map;
  - CLI/backend relationship;
  - workspace artifact layout;
  - trust-boundary rules;
  - repository hygiene and merge policy;
  - validation/gate model;
  - test commands for common changes;
  - what not to commit;
  - how to update the LaTeX report and PDF.
- Link the maintainer guide from either `README.md`, `docs/usage.md`, or
  `docs/release_checklist.md` if appropriate.

### Tests

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
git diff --check
```

### Acceptance Criteria

- Comments explain release-critical intent, not obvious syntax.
- A new maintainer can find the module map and release safety rules.
- No private or generated local state is referenced in documentation.

## Phase 3 - Rewrite The LaTeX Report Around The Actual Release

### Motivation

`proposal/research_development_assistant_design.tex` currently reads like a
proposal for a shared research intelligence backend. The final release now needs
a proper report/manual that describes the implemented individual local tool and
treats the multi-user version as a future extension.

### Implementation Instructions

Rewrite the tracked LaTeX report substantially. The report should be accurate,
auditable, and useful to a new user or reviewer.

Required framing:

- The current release is an individual local tool.
- Storage is local files and Git, not a maintained database.
- Git sharing is checkout/import/merge, not real-time collaboration.
- Multi-user database/service/RBAC/hosted UI is a future extension.
- Generated outputs and parser outputs are review material.
- Parser scientific accuracy is not certified.
- Broad release remains blocked until real external validations and release
  owner approvals are recorded.

Recommended report structure:

1. Executive summary for the current release.
2. What has actually been built.
3. Target user and supported workflows.
4. Installation and quickstart.
5. Local workspace and artifact model.
6. Paper/source evidence workflows.
7. Review notes, derivation worksheets, experiments, synthesis proposals, and
   traceability records.
8. Git sharing workflow:
   - repository hygiene;
   - dry-run merge;
   - explicit apply;
   - provenance preservation;
   - post-merge rebuild.
9. Release validation and tests:
   - unit/focused tests;
   - `scripts/run_fast_tests.sh`;
   - `scripts/run_bounded_tests.sh`;
   - exact wheel clean-install smoke with `WHEEL_PATH`;
   - `synthetic_git_1000` performance;
   - clean-checkout gate;
   - expected blocked external gates.
10. Nontrivial showcases:
   - initialize workspace and run demo;
   - inspect release report;
   - run parser matrix and benchmark smoke;
   - create or inspect review artifacts;
   - run repository hygiene;
   - perform workspace merge dry-run and rebuild;
   - build individual Git release gate.
11. User manual:
   - core commands;
   - safety flags;
   - what files are safe to commit;
   - backup/restore workflow;
   - privacy/offline defaults;
   - troubleshooting.
12. Known limitations.
13. Future multi-user extension:
   - shared storage;
   - service deployment;
   - SSO/RBAC;
   - hosted UI;
   - department operations;
   - stronger benchmarks and real-world validation.

Use examples that can be run from the repository and do not require private
data. Prefer commands already covered by tests, for example:

```bash
ra init
ra doctor --matrix
ra demo setup
ra demo run
ra release-report
ra repository-hygiene check --strict
ra workspace merge --source /path/to/other/repo --dry-run
ra workspace rebuild-derived
ra individual-git-release validation-report
ra individual-git-release gate-build
WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl scripts/run_clean_install_smoke.sh
```

LaTeX/PDF instructions:

- Update `proposal/research_development_assistant_design.tex`.
- If a TeX engine is available, rebuild
  `proposal/research_development_assistant_design.pdf`.
- Do not commit `.aux`, `.log`, `.out`, `.toc`, `.fdb_latexmk`,
  `.fls`, or other generated TeX intermediates.
- If no TeX engine is available, leave the PDF unchanged and record the blocker
  in the reset memo.
- If the PDF is rebuilt, inspect the diff/stat and record the build command.

### Tests

At minimum:

```bash
git diff --check
```

If TeX is available:

```bash
timeout 180 pdflatex -interaction=nonstopmode -halt-on-error research_development_assistant_design.tex
```

Run the TeX command from `proposal/` or use an equivalent local build command.
After build, remove or ignore intermediate TeX files and verify:

```bash
git status --short --ignored
```

### Acceptance Criteria

- The report describes the implemented individual release, not an aspirational
  primary multi-user platform.
- It includes practical examples, validation evidence, known limitations, and a
  user manual section.
- Multi-user work is clearly labeled as future extension.
- The PDF is rebuilt if possible, or the inability to rebuild is recorded.

## Phase 4 - Cross-Document Consistency Pass

### Motivation

After rewriting the report, release documents must tell the same story. A final
release packet is confusing if the proposal, release notes, checklist, support
docs, and known limitations disagree.

### Implementation Instructions

Review and update, only where necessary:

- `README.md`
- `docs/proposal/individual_git_release_target.md`
- `docs/release_notes_0.1.0.md`
- `docs/release_checklist.md`
- `docs/known_limitations.md`
- `docs/platform_support.md`
- `docs/support.md`
- `docs/usage.md`
- `docs/quickstart.md`
- `docs/workflows/git_sharing_walkthrough.md`
- `docs/workflows/git_sharing_workflow.md`
- `docs/maintainer_guide.md` if added

Consistency requirements:

- Current release target is individual local + Git sharing.
- Multi-user platform is future work.
- Parser scientific accuracy is not certified.
- Exact-wheel clean install uses `WHEEL_PATH`.
- Broad release still requires real fresh-reader, macOS, minimal parser-tool,
  tag, and publication evidence.
- Generated artifacts remain review material.
- Private/generated files must not be committed.

### Tests

Add or update docs smoke assertions in
`tests/integration/test_individual_release_cli.py` if useful. Then run:

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
git diff --check
```

### Acceptance Criteria

- A new reader sees one coherent release story across docs.
- No doc implies the current release is a shared multi-user service.
- Existing known limitations and manual blockers remain visible.

## Phase 5 - Full Local Validation Packet

### Motivation

Refactors and documentation rewrites should not weaken the release gate. The
final packet must prove that code behavior, docs smoke, artifact install, and
Git-sharing gates still work from a clean checkout.

### Implementation Instructions

Run:

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q
timeout 120 scripts/run_fast_tests.sh
timeout 180 scripts/run_bounded_tests.sh
timeout 300 scripts/build_release_artifacts.sh
WHEEL_PATH=/home/chakwong/python/ResearchAssistant/dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh
GATE_ROOT=/tmp/research-assistant-maintainability-gate timeout 300 scripts/run_individual_git_release_gate.sh
git diff --check
git status --short --ignored
```

Then create a clean local clone from the implementation commit and run:

```bash
GATE_ROOT=/tmp/research-assistant-maintainability-clean-gate timeout 300 scripts/run_individual_git_release_gate.sh
git status --short --ignored
```

Do not commit `dist/`, `build/`, caches, bytecode, temporary clone contents, or
generated workspaces.

### Acceptance Criteria

- Tests pass.
- Clean install from the exact wheel passes.
- Release gate remains reproducible from clean checkout.
- Final gate is either:
  - still blocked only for known manual external validation and approval; or
  - passed only if real evidence and approval have been recorded.

## Phase 6 - External Manual Release Gates

### Motivation

Even after maintainability and report work, broad release still depends on real
external validation and release-owner decisions.

### Implementation Instructions

Complete or record blockers for:

- real fresh-reader onboarding from docs;
- real macOS validation;
- real minimal parser-tool machine validation;
- release-owner tag approval;
- release-owner artifact publication approval.

Use the validation-record commands and protocols already documented in:

- `docs/plans/robust_individual_user_release_gap_closure_plan_2026-04-28.md`;
- `docs/release/external_validation_protocol.md`;
- `docs/release/publication_runbook.md`;
- `docs/onboarding_trial.md`;
- `docs/platform_support.md`.

Do not mark these as passed unless they actually happen.

### Acceptance Criteria

- Broad release remains blocked if any real external validation or approval is
  missing.
- Tagging and publication occur only after explicit release-owner approval.

## Final Definition Of Done

This plan is complete when:

- targeted refactors are complete and behavior-preserving;
- release-critical code paths have useful comments/docstrings;
- `docs/maintainer_guide.md` or equivalent maintainer documentation exists;
- `proposal/research_development_assistant_design.tex` is rewritten around the
  implemented individual local/Git release;
- the PDF is rebuilt or the inability to rebuild is recorded;
- release docs tell a consistent story;
- full local validation and clean-checkout gate pass;
- reset memo records the exact evidence, blockers, commit hashes, and local
  state;
- no private/generated/ignored state is committed;
- broad release still waits for real external validations and release-owner
  approval unless those have actually been completed.
