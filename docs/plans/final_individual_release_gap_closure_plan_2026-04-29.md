# Final Individual Release Gap Closure Plan - 2026-04-29

## Purpose

This plan captures the remaining work before a robust final v0.1 individual
release of `research-assistant`.

It combines:

- the findings agreed with in
  `docs/proposal/release_audit_second_agent_review_request_2026-04-29.md`;
- the current gate evidence after commit
  `ee4c1d6 Record release audit gap closure checkpoint`;
- the remaining blockers observed by
  `GATE_ROOT=/tmp/research-assistant-final-gap-audit timeout 300 scripts/run_individual_git_release_gate.sh`;
- a fresh audit of release docs, helper scripts, validation protocols, support
  docs, and local state.

## Current Release Scope

The release target remains the bounded individual release:

- one researcher at a time;
- local filesystem storage;
- offline/provider-disabled defaults;
- Git-based sharing by repository checkout, hygiene checks, dry-run merge,
  explicit apply, and rebuild;
- no current shared backend, shared database, hosted UI, SSO/RBAC, real-time
  collaboration, or department operations platform;
- generated/parser/benchmark/derivation/traceability/readiness artifacts are
  review material, not accepted scientific conclusions.

Do not reframe this release as the older industrial/shared-platform vision.

## Audit Summary

### Fixed Before This Plan

The previous release audit's most concrete reproducibility blockers have been
closed:

- `scripts/run_tests.sh` is now repo-portable, exports `PYTHONPATH=src`, and
  uses `timeout`.
- `tests/integration/test_cli_commands.py` no longer depends on a personal
  Palazzo PDF path.
- `docs/release_notes_0.1.0.md` now uses the 2026-04-29 candidate date/evidence
  wording.
- `docs/release_checklist.md` now says representative performance evidence must
  run before `validation-report` and `gate-build`.
- Validation after the fixes:
  - affected integration slice: `26 passed`;
  - full `scripts/run_tests.sh`: `139 passed`;
  - individual release suite: `14 passed`;
  - fast suite: `14 passed`.

### Current Gate Result

The current release gate is healthy for limited pilot but blocked for broad
release:

- `ready_for_limited_individual_pilot: true`;
- `ready_for_git_shared_research_release: false`;
- `ready_for_broad_individual_release: false`;
- `representative_workspace_performance_status: passed`;
- `merge_fixture_rehearsal_status: passed`;
- blockers:
  - real fresh-reader onboarding not recorded;
  - real macOS validation not recorded;
  - real minimal parser-tool machine validation not recorded;
  - release-owner tag approval not recorded;
  - release-owner publication approval not recorded.

### Additional Remaining Gaps

1. Some older validation docs/scripts still mention old absolute paths or private
   local paper assumptions:
   - `scripts/run_parser_preflight.sh`;
   - `scripts/run_clean_ingest_palazzo.sh`;
   - `docs/validation_scripts.md`;
   - `docs/product_spec.md` acceptance criteria.
2. `docs/release/external_validation_protocol.md` and
   `docs/release/publication_runbook.md` still use "industrial release" wording
   even though the current release is the individual local/Git target.
3. `docs/plans/templates/` does not exist even though earlier audit material
   references reset/experiment templates.
4. The final release packet still needs a clean-candidate rerun from the exact
   intended commit after all doc/script cleanups.
5. Build artifacts are intentionally ignored, so the exact wheel hash in release
   notes must be regenerated and checked immediately before tag/publication.
6. `.codex` remains untracked and should not be committed.
7. `docs/plans/whole_codebase_release_audit_2026-04-29.md` remains an ignored
   local audit input. Decide whether to force-stage it as release history or
   leave it local; do not accidentally commit it.

## Non-Negotiable Rules

- Do not fake external validation, macOS evidence, fresh-reader evidence, tag
  approval, or publication approval.
- Do not create or push tags unless explicit release-owner approval is provided
  in the user request.
- Do not publish artifacts unless explicit release-owner publication approval is
  provided in the user request.
- Do not commit `.codex`, `.claude/`, `.pytest_cache/`, bytecode, `build/`,
  `dist/`, temporary clones, generated workspaces, backup archives, private
  papers, private datasets, credentials, provider keys, tokens, or private local
  paths.
- Use `timeout` for validation commands.
- Files under `docs/plans/` are ignored; force-stage only intentional plan/reset
  memo files.

## Execution Loop

For every phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start, intent, and
   risk.
2. Plan the smallest safe action.
3. Execute the phase.
4. Run focused validation.
5. Audit as a second developer.
6. Tidy generated files.
7. Update the reset memo with evidence, blockers, and next step.
8. Commit coherent changes after validation.

## Phase 0 - Baseline Cleanliness And Reproducibility Check

### Motivation

Before closing final-release gaps, establish that the current committed tree is
stable and that earlier reproducibility fixes remain effective.

### Implementation Instructions

- Record current `git log --oneline -5`.
- Record `git status --short --ignored`.
- Run:

```bash
timeout 180 scripts/run_tests.sh
GATE_ROOT=/tmp/research-assistant-final-gap-audit timeout 300 scripts/run_individual_git_release_gate.sh
git diff --check
```

- Capture readiness flags and blockers from the gate.

### Acceptance Criteria

- Full test script passes.
- Gate remains limited-pilot ready and broad-release blocked only for expected
  manual/external gates.
- No tracked dirty state except intentional work for this plan.

## Phase 1 - Modernize Legacy Validation Scripts And Docs

### Motivation

The prior audit fixed the official full test runner and the integration test,
but older validation helpers still contain the same kind of release risk:
maintainer-local paths and a private Palazzo PDF assumption.

### Implementation Instructions

Update or retire these files:

- `scripts/run_parser_preflight.sh`
- `scripts/run_clean_ingest_palazzo.sh`
- `docs/validation_scripts.md`
- `docs/product_spec.md`
- `README.md` if it still presents stale validation commands.

Required behavior:

- `scripts/run_parser_preflight.sh` must derive `ROOT` from script location,
  export `PYTHONPATH=src`, use `timeout`, and run current parser diagnostics
  such as `ra doctor --matrix`, `ra parser-tool-matrix`, and
  `ra parser-benchmark-smoke`.
- `scripts/run_clean_ingest_palazzo.sh` must no longer depend on a private PDF
  under `local_research/papers/raw/`.
- Preferred options for Palazzo regression:
  - replace the script with a documented pytest invocation that uses the
    deterministic sanitized fixture path in
    `tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus`;
  - or create a repo-local synthetic PDF fixture and monkeypatched deterministic
    runner if shell-level coverage is still needed.
- `docs/validation_scripts.md` should remove hard-coded
  `/home/chakwong/research-assistant` permission examples and describe
  repo-relative script use.
- `docs/product_spec.md` acceptance criteria should reference portable validation
  commands, not a private-PDF script.

### Tests

```bash
timeout 120 scripts/run_parser_preflight.sh
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus -q
timeout 180 scripts/run_tests.sh
git diff --check
```

### Acceptance Criteria

- No active release validation script contains `/home/chakwong/research-assistant`.
- No active release validation script requires a private PDF.
- Documentation explains how to run the parser/PDF regression from a clean
  checkout.

## Phase 2 - Align External Validation And Publication Docs To Individual Release

### Motivation

Some release docs still say "industrial release." That wording is misleading for
the current v0.1 target and can make reviewers think a hosted department
platform is in scope.

### Implementation Instructions

Review and update:

- `docs/release/external_validation_protocol.md`
- `docs/release/publication_runbook.md`
- `docs/release_notes_0.1.0.md`
- `docs/release_notes_template.md`
- `docs/platform_support.md`
- `docs/support.md`
- `docs/known_limitations.md`
- `docs/maintainer_guide.md`

Required wording:

- Current release is individual local + Git sharing.
- External validation records are sanitized metadata only.
- Real fresh-reader, macOS, and minimal-parser-tool validation are required for
  broad non-pilot release.
- Tagging and publication require release-owner approval.
- Industrial/shared platform language belongs only in future-extension sections.

### Tests

```bash
rg -n "industrial release|departmental beta|industrial production" docs/release docs/release_notes_0.1.0.md docs/platform_support.md docs/support.md docs/known_limitations.md docs/maintainer_guide.md
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
git diff --check
```

If the `rg` command finds intentional future-platform references, confirm they
are clearly labeled as future/deferred.

### Acceptance Criteria

- Current release docs do not imply a live industrial/shared platform release.
- Manual validation and approval blockers remain explicit.

## Phase 3 - Add Missing Process Templates Or Remove References

### Motivation

The audit found references to `docs/plans/templates/`, but the directory does
not exist. This is not a product blocker, but it is a release-process paper cut
for future agents.

### Implementation Instructions

Either add:

- `docs/plans/templates/reset-memo-template.md`
- `docs/plans/templates/experiment-plan-template.md`
- `docs/plans/templates/experiment-result-template.md`

or remove/update stale references if templates are no longer part of the
workflow.

Templates should be short, generic, and free of private paths. Include:

- objective;
- scope;
- plan;
- execution log;
- validation;
- audit;
- tidy;
- blockers;
- next step.

### Tests

```bash
find docs/plans/templates -maxdepth 2 -type f -print
git diff --check
```

### Acceptance Criteria

- Template references are accurate.
- Future agents have a clear reset-memo/checkpoint skeleton.

## Phase 4 - External Manual Validation Evidence

### Motivation

The final gate cannot become broad-release ready until real people/machines run
the documented commands.

### Implementation Instructions

Complete or explicitly record blocked status for:

1. Fresh-reader onboarding:
   - give a colleague `docs/onboarding_trial.md`;
   - have them install from the exact wheel;
   - collect only sanitized metadata and command statuses.
2. macOS validation:
   - run clean install smoke on a real macOS machine;
   - record `validation_type=macos`, `scope=external_machine`.
3. Minimal parser-tool machine:
   - run on a machine with only baseline tools;
   - confirm core/demo/metadata workflows pass and optional parser workflows
     warn/degrade cleanly;
   - record `validation_type=minimal_parser_tools`,
     `scope=external_machine`.

Use:

```bash
ra --root <validation-root> individual-git-release validation-record ...
ra --root <validation-root> individual-git-release validation-report
```

Do not record private paper titles, private paths, screenshots, tokens,
credentials, local workspace contents, backup archives, or shell history.

### Tests

```bash
ra --root <validation-root> individual-git-release validation-report
ra --root <validation-root> individual-git-release gate-build
```

### Acceptance Criteria

- Real records exist for colleague onboarding, macOS, and minimal parser-tool
  validation, or the reset memo clearly says they are blocked/manual.
- No substitute/local record is mislabeled as real external validation.

## Phase 5 - Final Artifact Build And Clean Candidate Rerun

### Motivation

The final candidate should be validated from a clean clone at the exact commit
intended for release. Because wheel hashes can change between builds, release
notes must be updated only after the final build used for smoke testing.

### Implementation Instructions

1. Ensure tracked tree is clean except intentional release updates.
2. Build artifacts:

```bash
timeout 300 scripts/build_release_artifacts.sh
```

3. Record exact wheel path, size, and SHA256 from
   `dist/release_artifacts_manifest.json`.
4. Run clean install smoke against the exact wheel:

```bash
WHEEL_PATH=/absolute/path/to/dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh
```

5. Update:
   - `docs/release_notes_0.1.0.md`;
   - `docs/platform_support.md`;
   - reset memo.
6. Commit the release updates.
7. Clone the exact commit to `/tmp/research-assistant-final-clean-<sha>`.
8. In the clone, run:

```bash
timeout 180 scripts/run_tests.sh
GATE_ROOT=/tmp/research-assistant-final-clean-gate-<sha> timeout 300 scripts/run_individual_git_release_gate.sh
git status --short --ignored
```

### Acceptance Criteria

- Clean clone starts with no tracked/untracked release pollution.
- Full tests pass in the clone.
- Gate is broad-release ready only if real external validations and approvals
  are present; otherwise it remains blocked for those exact reasons.
- `dist/` remains uncommitted.

## Phase 6 - Release Owner Approval, Tagging, And Publication

### Motivation

Final publication is a human decision. Autonomous agents must not tag or publish
without explicit approval.

### Implementation Instructions

Proceed only if the user explicitly approves tag and/or publication.

Before tag/publication:

- confirm release notes hash matches the exact wheel;
- confirm final gate status and blockers;
- confirm no private/generated files are staged;
- confirm support boundary and known limitations are current.

If approved:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

Publish only intended artifacts and checksum/manifest files.

If not approved, record:

- `release_owner_tag_approval`: blocked;
- `publication_approval`: blocked.

### Acceptance Criteria

- No tag or artifact publication happens without explicit approval.
- Final reset memo records the decision, evidence, commit hash, and remaining
  blockers.

## Final Definition Of Done

This plan is complete when:

- legacy validation scripts/docs are portable and clean-checkout safe;
- external validation/publication docs are aligned to the individual release;
- missing process templates are added or references corrected;
- real external validation records are collected or explicitly blocked;
- final artifact hash is synchronized with release notes after exact-wheel smoke;
- clean candidate clone validation is recorded;
- release-owner tag/publication decisions are recorded;
- no private/generated/ignored local state is committed.
