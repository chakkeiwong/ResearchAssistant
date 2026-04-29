# Final Release Readiness Closure Plan - 2026-04-29

## Purpose

This plan addresses the remaining gaps before `research-assistant` can move from
a limited individual pilot candidate to a robust individual-user release.

The current product target is not the older multi-user or industrial platform.
The release target is:

- one individual researcher at a time;
- local filesystem storage;
- offline/provider-disabled default workflows;
- Git-based sharing by repository checkout, strict hygiene checks, dry-run
  merge, explicit apply, provenance preservation, and derived-artifact rebuild;
- generated/parser/benchmark/derivation/traceability/readiness artifacts as
  review material, not scientific approval.

The plan is written for another agent to audit and execute. It must not be used
to fake external validation, approval, tag creation, publication, or artifact
hashes.

## Current Status Summary

As of this plan:

- The codebase has passed the main local deterministic test packet in recent
  recorded runs:
  - `scripts/run_tests.sh`: `139 passed`;
  - individual release integration suite: `14 passed`;
  - fast suite: `14 passed`.
- The individual Git release gate has previously reported:
  - `ready_for_limited_individual_pilot: true`;
  - broad release blocked for expected manual/external gates.
- The proposal/report has been rewritten as a colleague-facing adoption
  document and its PDF has been rebuilt and inspected.
- Known local state includes an untracked `.codex` file that must not be
  committed.
- The local branch may be ahead of `origin/main`; remote synchronization must be
  checked before final release work is treated as shareable.

## Remaining Gaps To Close

### Agent-executable gaps

1. Stale validation documentation and helper scripts still need a final cleanup
   pass.
2. Release docs still contain some older "industrial release" wording and must
   be aligned to the individual local/Git release.
3. Missing process templates or stale references to `docs/plans/templates/`
   should be resolved.
4. A final release artifact must be rebuilt from the exact intended release
   commit and its SHA256 must be synchronized with release notes.
5. A clean clone of the exact intended commit must run the release validation
   packet.
6. Repository hygiene must confirm that `.codex`, `.claude/`, caches, bytecode,
   `build/`, `dist/`, private papers, credentials, and generated workspaces are
   not committed.
7. The release commit must be available to colleagues through Git before they
   can validate it.

### Human/external gaps

1. Real fresh-reader onboarding has not been recorded.
2. Real macOS clean-install/smoke validation has not been recorded.
3. Real minimal-parser-tool machine validation has not been recorded.
4. Release-owner tag approval has not been recorded.
5. Release-owner artifact publication approval has not been recorded.

If these external gaps remain unavailable, the release must stay pilot-scoped.
An agent may record them as blocked/manual but must not mark them passed.

## Non-Negotiable Rules

- Do not fake fresh-reader, macOS, minimal-machine, tag, publication, or
  artifact evidence.
- Do not create or push tags unless the user explicitly approves tag creation.
- Do not publish artifacts unless the user explicitly approves publication.
- Do not commit `.codex`, `.claude/`, `.pytest_cache/`, bytecode caches,
  `build/`, `dist/`, raw PDFs, private datasets, backup archives, generated
  workspaces, credentials, provider keys, tokens, or local shell history.
- Do not force-push or rewrite history.
- Build outputs under `dist/` are release artifacts, not normal Git-tracked
  source files.
- Use `timeout` for all long-running validation commands.
- Files under `docs/plans/` are ignored by default; force-stage only the exact
  plan/reset-memo files intentionally committed.

## Required Audit Before Execution

Before executing any phase, the agent must audit this plan as another developer.
The audit must answer:

1. Does the plan preserve the individual local/Git release scope?
2. Does any phase accidentally imply a hosted/shared/database release?
3. Are human/external validation gaps separated from agent-executable work?
4. Are tag and publication approvals protected from autonomous action?
5. Are artifact hashes regenerated only after the final build?
6. Are private/generated/local files excluded from commits?
7. Are validation commands bounded and reproducible from a clean checkout?

If the audit finds a gap, update this plan first, then proceed.

## Execution Loop For Every Phase

For each phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start, intent, and
   risk.
2. Plan the smallest safe change for the phase.
3. Execute the change.
4. Run focused validation.
5. Audit the result as another developer.
6. Tidy generated outputs and confirm no private/generated files are staged.
7. Update the reset memo with evidence, blockers, and next step.
8. Commit coherent changes only after validation passes.

## Phase 0 - Baseline, Remote Sync, And Scope Lock

### Motivation

The final release must be tied to a concrete commit and must not depend on
unclear local state. The current branch may be ahead of `origin/main`; external
validators cannot reproduce a commit they cannot fetch.

### Implementation Instructions

- Record:

```bash
git status --short --branch
git status --short --ignored
git log --oneline -8
git remote -v
git rev-parse HEAD
git rev-parse origin/main
```

- If local `main` is ahead of `origin/main`, do not push before the current
  release-readiness changes are committed. Record the ahead count and treat
  remote synchronization as a final closeout action.

- After the final release-readiness commit is created, push normal commits only:

```bash
git push origin main
```

- If push fails because credentials or network are unavailable, record the
  blocker in the reset memo and continue only with local validation clearly
  marked as not yet shareable.
- Do not force-push.
- Confirm current release scope from:
  - `docs/release_notes_0.1.0.md`;
  - `docs/known_limitations.md`;
  - `docs/proposal/individual_git_release_target.md`.

### Validation

```bash
git status --short --branch
git diff --check
```

### Acceptance Criteria

- The exact working commit is recorded.
- Remote sync status is explicit.
- No private/generated files are staged.
- Scope remains individual local + Git sharing.

## Phase 1 - Clean Up Stale Validation Scripts And Validation Docs

### Motivation

Older validation surfaces still risk confusing a fresh maintainer or colleague
because they reference maintainer-local paths, old permission examples, or a
private Palazzo PDF workflow. These are release-process footguns even if the
core tests have already been fixed.

### Implementation Instructions

Review and update:

- `scripts/run_parser_preflight.sh`
- `scripts/run_clean_ingest_palazzo.sh`
- `docs/validation_scripts.md`
- `docs/product_spec.md`
- `README.md`

Required outcomes:

- `scripts/run_parser_preflight.sh` derives `ROOT` from the script location,
  exports `PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"`, and uses
  bounded commands.
- Parser diagnostics should include current commands:

```bash
ra doctor --matrix
ra parser-tool-matrix
ra parser-benchmark-smoke
```

- `scripts/run_clean_ingest_palazzo.sh` must not require a private PDF under a
  maintainer-specific path.
- Prefer replacing shell-level Palazzo validation with the deterministic pytest
  regression:

```bash
PYTHONPATH=src timeout 180 python -m pytest \
  tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus -q
```

- `docs/validation_scripts.md` must remove hard-coded examples such as
  `/home/chakwong/research-assistant/...`.
- `docs/product_spec.md` acceptance criteria must point to portable release
  commands, not private-paper scripts.
- If a legacy script is retired, leave a small wrapper that explains the new
  command and exits successfully only after running the replacement check.

### Validation

```bash
timeout 120 scripts/run_parser_preflight.sh
PYTHONPATH=src timeout 180 python -m pytest \
  tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus -q
timeout 180 scripts/run_tests.sh
rg -n "/home/chakwong/research-assistant|local_research/papers/raw|Palazzo" \
  scripts docs README.md tests
git diff --check
```

If `Palazzo` remains in intentional historical/test names, audit that no private
path or private PDF dependency remains.

### Acceptance Criteria

- No active validation script requires a private PDF.
- No active validation documentation instructs users to rely on maintainer-local
  absolute paths.
- Full local tests still pass.

## Phase 2 - Align Release, Publication, And External Validation Docs

### Motivation

Some release documents still use "industrial release" or department-platform
language. That wording is misleading for v0.1, where the correct target is an
individual local tool with Git-based sharing.

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
- `docs/release/industrial_release_gates.json`
- `docs/release/industrial_release_definition.md`

Required wording:

- Current release is individual local + Git sharing.
- External validation records are sanitized metadata and command statuses only.
- Real fresh-reader onboarding, real macOS validation, and real
  minimal-parser-tool validation are required for broad non-pilot release.
- Tagging and publication require explicit release-owner approval.
- Industrial/shared/multi-user platform language is allowed only as clearly
  labeled future/deferred scope.

For `docs/release/publication_runbook.md`, replace the old publication check:

```bash
ra industrial-release publication-check
```

with individual-release evidence commands, for example:

```bash
ra individual-git-release validation-report
ra individual-git-release gate-build
ra release-artifacts manifest
```

### Validation

```bash
rg -n "industrial release|departmental beta|industrial production|shared database|hosted UI|SSO/RBAC" \
  docs/release docs/release_notes_0.1.0.md docs/release_notes_template.md \
  docs/platform_support.md docs/support.md docs/known_limitations.md \
  docs/maintainer_guide.md
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
git diff --check
```

Each remaining hit must be explicitly future/deferred or historical and must not
describe the current release.

### Acceptance Criteria

- Release docs consistently describe v0.1 as individual local + Git sharing.
- Manual validation and approval blockers remain visible.
- No doc implies that hosted/database/SSO/RBAC capabilities are current release
  requirements or current release features.

## Phase 3 - Add Missing Process Templates Or Remove Stale References

### Motivation

Earlier audit material references `docs/plans/templates/`, but the directory may
not exist. This is not a user-facing product blocker, but it slows future agents
and weakens release audit hygiene.

### Implementation Instructions

Search for template references:

```bash
rg -n "docs/plans/templates|reset-memo-template|experiment-plan-template|experiment-result-template" docs
```

Then either add the referenced templates or remove stale references.

Preferred templates:

- `docs/plans/templates/reset-memo-template.md`
- `docs/plans/templates/phase-execution-template.md`
- `docs/plans/templates/external-validation-record-template.md`

Each template should be short and generic, with sections for:

- objective;
- scope;
- plan;
- execution;
- validation;
- audit;
- tidy;
- blockers;
- next step.

Do not include private paths, personal usernames, credentials, or real paper
titles.

### Validation

```bash
find docs/plans/templates -maxdepth 2 -type f -print
rg -n "docs/plans/templates|reset-memo-template|phase-execution-template|external-validation-record-template" docs
git diff --check
```

### Acceptance Criteria

- Template references resolve to real files or are removed.
- New templates are generic, privacy-safe, and useful for future autonomous
  release work.

## Phase 4 - External Manual Validation Packet

### Motivation

The broad release gate cannot pass without real external evidence. Local
substitutes are useful for development but must not be mislabeled as real
fresh-reader, macOS, or minimal-parser-tool validation.

### Implementation Instructions

Prepare validation instructions for three real validation types:

1. Fresh-reader onboarding.
2. macOS clean install / smoke.
3. Minimal parser-tool machine.

Use existing docs:

- `docs/onboarding_trial.md`
- `docs/platform_support.md`
- `docs/release/external_validation_protocol.md`

For each real run, record sanitized evidence with:

```bash
ra --root <validation-root> individual-git-release validation-record \
  --validation-type <colleague_onboarding|macos|minimal_parser_tools> \
  --result <passed|warnings|blocked> \
  --scope real_external \
  --platform "<platform>" \
  --python-version "<python>" \
  --install-method "<wheel or source>" \
  --command-summary "<sanitized command summary>" \
  --evidence-note "<sanitized note>"
```

If validation cannot be performed, record a blocked/manual status in the reset
memo. Do not create fake validation records.

Do not collect or store:

- private PDFs;
- private TeX source;
- paper titles from private work;
- screenshots containing private data;
- local workspace contents;
- backup archives;
- provider keys, tokens, credentials, cookies, shell history, or usernames in
  local paths.

### Validation

After records are added to the chosen validation root:

```bash
ra --root <validation-root> individual-git-release validation-report
ra --root <validation-root> individual-git-release gate-build
```

### Acceptance Criteria

- Real validation records exist for fresh-reader, macOS, and minimal-parser-tool
  validation, or each missing item is explicitly recorded as blocked/manual.
- The gate distinguishes real external records from local substitutes.
- No private validation data is committed.

## Phase 5 - Final Artifact Build And Hash Synchronization

### Motivation

Release notes currently contain an artifact hash from a prior local build. The
final release hash must come from the exact wheel used in clean-install smoke
after all source/docs changes are complete.

### Implementation Instructions

1. Confirm the tracked tree is clean except intentional release updates:

```bash
git status --short --ignored
git diff --check
```

2. Build artifacts:

```bash
timeout 300 scripts/build_release_artifacts.sh
```

3. Inspect the manifest:

```bash
ra release-artifacts manifest
```

4. Record exact artifact path, size, and SHA256 from:

```text
dist/release_artifacts_manifest.json
```

5. Run clean install smoke against the exact wheel:

```bash
env WHEEL_PATH="$(pwd)/dist/research_assistant-0.1.0-py3-none-any.whl" \
  timeout 300 scripts/run_clean_install_smoke.sh
```

6. Update:

- `docs/release_notes_0.1.0.md`;
- `docs/platform_support.md` if platform evidence changed;
- `docs/plans/reset_memo_2026-04-26.md`.

7. Do not commit `dist/`.

### Validation

```bash
scripts/run_packaging_smoke.sh
timeout 300 scripts/build_release_artifacts.sh
env WHEEL_PATH="$(pwd)/dist/research_assistant-0.1.0-py3-none-any.whl" \
  timeout 300 scripts/run_clean_install_smoke.sh
git diff --check
git status --short --ignored
```

### Acceptance Criteria

- Release notes hash matches the exact wheel used for clean-install smoke.
- `dist/` remains ignored and uncommitted.
- The reset memo records artifact hash, size, command evidence, and commit.

## Phase 6 - Clean Clone Candidate Validation

### Motivation

The release should be reproducible from a clean checkout of the exact intended
release commit, not only from the working tree used during development.

### Implementation Instructions

1. Commit all intentional source/docs release updates.
2. Record the exact commit:

```bash
git rev-parse HEAD
```

3. Clone locally into `/tmp`:

```bash
git clone "$(pwd)" /tmp/research-assistant-final-clean-<short-sha>
```

4. In the clone, run:

```bash
timeout 180 scripts/run_tests.sh
timeout 120 scripts/run_fast_tests.sh
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
GATE_ROOT=/tmp/research-assistant-final-clean-gate-<short-sha> \
  timeout 300 scripts/run_individual_git_release_gate.sh
git status --short --ignored
```

5. Record gate readiness flags and blockers.

### Acceptance Criteria

- Clean clone validation passes.
- Gate is broad-release ready only if real external validation and approvals
  exist.
- If external validations/approvals are missing, gate remains blocked for those
  exact reasons and the release remains pilot-scoped.
- No generated clone artifacts are committed.

## Phase 7 - Release Owner Approval, Tagging, And Publication Decision

### Motivation

Tagging and publication are human release decisions. An autonomous agent can
prepare evidence but must not create tags or publish artifacts without explicit
approval.

### Implementation Instructions

Before requesting or acting on approval, summarize:

- exact commit SHA;
- final wheel path, size, and SHA256;
- clean clone validation results;
- individual Git release gate readiness flags;
- remaining manual blockers;
- known limitations;
- support boundary.

If the user explicitly approves tag creation, run:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

If the user explicitly approves artifact publication, publish only:

- intended wheel and source distribution artifacts;
- checksum/manifest files;
- release notes.

If approval is not provided, record:

- `release_owner_tag_approval`: blocked/manual;
- `publication_approval`: blocked/manual.

Do not infer approval from prior planning language.

### Validation

If tag is created:

```bash
git tag --list v0.1.0
git ls-remote --tags origin v0.1.0
```

If artifacts are published, verify uploaded checksums match local manifest.

### Acceptance Criteria

- No tag or publication occurs without explicit approval.
- Approval or blocked/manual status is recorded in the reset memo.
- Final release state is unambiguous: pilot candidate, broad individual release,
  or published release.

## Phase 8 - Final Reset Memo, Commit Hygiene, And Closeout

### Motivation

The release audit trail must be sufficient for a future maintainer to recover
after a shutdown and understand exactly what remains.

### Implementation Instructions

- Update `docs/plans/reset_memo_2026-04-26.md` with:
  - exact commit SHA;
  - remote sync status;
  - validation commands and results;
  - artifact hash and clean-install evidence;
  - external validation status;
  - tag/publication approval status;
  - remaining blockers;
  - local ignored/untracked state.
- Run:

```bash
git diff --check
git status --short --ignored
```

- Stage only intentional files. For ignored `docs/plans/` files, use `git add
  -f` only on exact plan/reset memo paths.
- Commit the final closeout packet.

### Acceptance Criteria

- Reset memo is current enough for shutdown recovery.
- Commit contains only intentional release documentation/source changes.
- `.codex`, `.claude/`, caches, `build/`, `dist/`, private data, and generated
  workspaces are not committed.
- Remaining blockers are explicit and not hidden by optimistic language.

## Final Definition Of Done

This plan is complete when:

- stale validation scripts/docs are portable and clean-checkout safe;
- release/publication/external-validation docs match the individual local/Git
  release target;
- process template references are resolved;
- real external validations are recorded or explicitly blocked/manual;
- final artifact hash is synchronized with the exact tested wheel;
- clean clone validation is recorded for the exact release commit;
- remote sync status is explicit;
- release-owner tag/publication approval decisions are recorded;
- the reset memo has a complete shutdown recovery checkpoint;
- no private/generated/local-only files are committed.
