# Individual Release Colleague Rollout Plan — 2026-04-27

## Purpose

This plan is for the final release-to-colleagues step after the individual local-install hardening work. The codebase now has release lifecycle commands, clean-install smoke, parser/tool matrix, backup/restore hardening, release artifact build, platform status, onboarding docs, known limitations, and `ra release-report` reporting `ready_for_release_candidate_review` on the current Linux/WSL validation environment.

The remaining work is not a large implementation pass. It is release execution: verify the release on colleague-like machines, rehearse the installation and restore workflows, finalize the artifact and release notes, define the support boundary, and tag/publish only when the release candidate is honest.

This release is for **private individual local use**. It is not a shared server, shared database, production RBAC/SSO system, live collaboration tool, distributed job system, or live LLM/provider release.

## Current Baseline

Latest pushed release-hardening commits:
- `047c1f6 Close individual release hardening gaps`
- `89d6cf0 Record individual release hardening checkpoint`

Current release surfaces:
- `ra release-report`
- `ra doctor --matrix`
- `ra parser-tool-matrix`
- `ra parser-benchmark-smoke`
- `ra platform-status`
- `ra onboarding-report`
- `ra backup create/inspect/restore`
- `ra performance smoke`
- `scripts/run_clean_install_smoke.sh`
- `scripts/build_release_artifacts.sh`
- `scripts/run_release_smoke.sh`
- `scripts/run_packaging_smoke.sh`
- `scripts/run_bounded_tests.sh`

Important docs:
- `docs/installation.md`
- `docs/quickstart.md`
- `docs/onboarding_trial.md`
- `docs/known_limitations.md`
- `docs/platform_support.md`
- `docs/release_notes_template.md`
- `docs/release_checklist.md`

## Non-Negotiable Release Rules

- Do not broaden scope into a shared industrial platform.
- Do not enable live LLM/provider workflows by default.
- Do not hide parser limitations.
- Do not tag a release until clean install, demo, backup/restore, and release-report checks pass.
- Do not commit private papers, local research outputs, generated build artifacts, `.codex`, caches, or colleague feedback containing private data.
- Use `timeout` for every scripted validation run.
- Update `docs/plans/reset_memo_2026-04-26.md` after each phase with tests, platform, residual risks, and next step.
- `docs/plans/` is ignored, so force-stage intentional plan/reset memo changes with `git add -f`.

## Required Audit Before Execution

Before implementing or running rollout work, another agent must audit this plan from a release-manager perspective:

- Are all remaining release blockers process/validation blockers rather than code blockers?
- Does every phase have a clear acceptance criterion?
- Are private data and provider/network boundaries protected?
- Are generated artifacts and parser outputs still described as review material?
- Are platform claims limited to machines actually tested?
- Is the tag/release process explicit and reversible?
- Is the support boundary clear enough for colleagues?

If the audit finds issues, update this plan first, then execute the corrected plan.

## Execution Loop

For each phase:
1. Update the reset memo with phase start.
2. Run or implement the smallest necessary release action.
3. Capture command outputs in concise reset-memo summaries, not giant logs.
4. Add or update docs/tests/scripts only if a gap is found.
5. Audit the result as a different developer.
6. Tidy generated files and avoid committing build outputs.
7. Update the reset memo with validation, risks, and next safe step.
8. Commit only coherent docs/code changes.

## Phase 1 — Fresh Colleague Onboarding Trial

### Motivation

The automated clean-install smoke proves that a fresh virtual environment can install and run the demo, but a release is for humans. A colleague or independent developer needs to follow the docs without knowing the project history. This catches confusing wording, missing prerequisites, platform assumptions, and unclear recovery instructions.

### Implementation Instructions

- Select one trial user who did not implement the release hardening.
- Give them only:
  - `docs/installation.md`;
  - `docs/quickstart.md`;
  - `docs/onboarding_trial.md`;
  - the release artifact or checkout path chosen for the trial.
- Ask them to run:
  - `ra --help`;
  - `ra version`;
  - `ra --root <trial-workspace> init`;
  - `ra --root <trial-workspace> doctor`;
  - `ra --root <trial-workspace> demo setup`;
  - `ra --root <trial-workspace> demo run`;
  - `ra --root <trial-workspace> release-report`;
  - `ra --root <trial-workspace> backup create`;
  - `ra --root <trial-workspace> backup inspect --path <backup>`;
  - `ra --root <trial-workspace> privacy status`.
- Record only non-private trial metadata:
  - platform;
  - Python version;
  - install mode;
  - time-to-demo;
  - optional tools available;
  - blockers/confusions;
  - suggested documentation fixes.
- If the trial reveals doc issues, update docs immediately.
- If it reveals command failures, add focused regression tests before fixing.

### Tests And Verification

- Run `scripts/run_clean_install_smoke.sh` before and after any doc/code changes.
- Run `ra onboarding-report` and ensure the checklist still matches docs.
- Verify no private local workspace or colleague files are committed.

### Acceptance Criteria

- One fresh reader can reach demo completion using docs only.
- Any confusion is either fixed or recorded in `docs/known_limitations.md`.
- Reset memo records time-to-demo and platform.

## Phase 2 — Platform Signoff

### Motivation

The current release-report is green on the current Linux/WSL environment. Colleagues may use Linux, macOS, or Windows through WSL. The release must state what is supported based on actual validation, not hope.

### Implementation Instructions

- Use `docs/platform_support.md` as the source of truth.
- Run on each available target platform:
  - `ra platform-status`;
  - `scripts/run_clean_install_smoke.sh`;
  - `scripts/run_release_smoke.sh`;
  - `scripts/run_packaging_smoke.sh`.
- Minimum required before broad release:
  - current Linux/WSL validation remains passing;
  - macOS validation is either completed or explicitly listed as unvalidated;
  - native Windows is either tested or explicitly not supported.
- Update `docs/platform_support.md` with tested date, Python version, and result summary.
- If platform-specific install instructions are needed, add them to `docs/installation.md`.

### Tests And Verification

- Run `python -m pytest tests/integration/test_individual_release_cli.py::test_project_metadata_exposes_ra_entrypoint -q`.
- Run `ra release-report` and confirm platform docs are present.
- Confirm platform claims in release notes match actual test results.

### Acceptance Criteria

- Supported platforms are explicit and conservative.
- At least one colleague-like machine passes clean install smoke.
- Untested platforms are not implied to be supported.

## Phase 3 — Optional Parser Tool Variability Trial

### Motivation

The current machine reports all optional parser tools available. Many colleagues will not have all of them. The release needs to prove that missing optional tools degrade gracefully and that core local workflows remain usable.

### Implementation Instructions

- Run `ra doctor --matrix` and `ra parser-tool-matrix` in at least one environment with missing optional parser tools.
- If a real minimal environment is unavailable, create a test mode or monkeypatch-based test that simulates missing tools.
- Verify:
  - `core_local_lifecycle` remains `ok`;
  - `demo_workflow` remains `ok`;
  - `pdf_text_ingest` reports missing required/optional tools clearly;
  - parser benchmark smoke remains fixture-only and offline.
- Update `docs/troubleshooting.md` with the observed missing-tool messages and suggested fixes.

### Tests And Verification

- Add or run tests that mock optional tool absence.
- Run:
  - `ra doctor --matrix`;
  - `ra parser-tool-matrix`;
  - `ra parser-benchmark-smoke`;
  - `scripts/run_fast_tests.sh`.

### Acceptance Criteria

- Missing optional parser tools do not block demo, backup, privacy, config, workspace validation, or release-report.
- Parser/PDF workflows clearly explain missing tools and limitations.

## Phase 4 — Realistic Personal Corpus Rehearsal

### Motivation

Synthetic smoke is useful, but colleagues may have hundreds or thousands of papers. Before release, we need bounded evidence that validation, indexing, export, and backup remain acceptable for a representative personal corpus shape.

### Implementation Instructions

- Run a synthetic medium corpus:
  - `ra --root /tmp/ra-perf-1000 performance smoke --synthetic-count 1000 --include-industrial-artifacts --include-export --include-backup --timeout-seconds 600`
- If runtime is too high, rerun at 250 or 500 and record the threshold honestly.
- If a non-sensitive real corpus is available:
  - run `ra workspace validate`;
  - run `ra backup create`;
  - run `ra release-report`;
  - do not commit corpus files or output.
- Record:
  - record count;
  - validation time;
  - index time;
  - export time;
  - backup time;
  - backup size;
  - warnings/blockers.
- Update `docs/known_limitations.md` if medium-corpus performance is not yet comfortable.

### Tests And Verification

- Run focused performance smoke with a small count after any code/doc change.
- Run `scripts/run_bounded_tests.sh`.
- Verify no generated `local_research/`, `build/`, or `dist/` outputs are staged.

### Acceptance Criteria

- A medium synthetic corpus completes within a bounded timeout or the release notes state the observed limit.
- Backup/export/validation performance is visible rather than guessed.

## Phase 5 — Backup And Restore Rehearsal

### Motivation

Backup/restore is the data-safety path. The code supports confirmed restore and overwrite guards, but release managers should rehearse the real commands on disposable workspaces before telling colleagues to rely on it.

### Implementation Instructions

- Create disposable demo workspace:
  - `ra --root /tmp/ra-restore-source demo setup`;
  - `ra --root /tmp/ra-restore-source demo run`;
  - `ra --root /tmp/ra-restore-source backup create`.
- Restore into fresh target:
  - `ra --root /tmp/ra-restore-target backup restore --path <backup> --no-dry-run --confirm-restore`.
- Validate restored target:
  - `ra --root /tmp/ra-restore-target workspace validate`;
  - `ra --root /tmp/ra-restore-target release-report`.
- Test overwrite guard on disposable data:
  - run restore again without `--allow-overwrite` and confirm it blocks;
  - run restore with `--allow-overwrite` and confirm safety backup path is reported.
- Record concise outcomes in reset memo.

### Tests And Verification

- Run `python -m pytest tests/integration/test_individual_release_cli.py::test_backup_create_inspect_and_restore_dry_run -q`.
- Inspect restore report JSON path from command output.

### Acceptance Criteria

- Fresh restore succeeds.
- Overwrite restore blocks unless explicitly allowed.
- Safety backup is created for overwrite restore.

## Phase 6 — Release Artifact And Install Path Decision

### Motivation

Colleagues need one recommended install path. The code can build a wheel and manifest, but a release manager must decide whether to distribute a wheel, source checkout, `pipx` command, or a GitHub release package.

### Implementation Instructions

- Run:
  - `scripts/build_release_artifacts.sh`;
  - `scripts/run_clean_install_smoke.sh`.
- Choose the official primary install path:
  - recommended default: wheel from GitHub release artifact;
  - secondary: source checkout for developers;
  - optional: `pipx install <wheel>` only if tested.
- Update `docs/installation.md` and `docs/release_notes_template.md` with the chosen path.
- Ensure `dist/release_artifacts_manifest.json` contains SHA256 hashes.
- Do not commit `dist/` artifacts unless the project explicitly decides to version release binaries in Git.

### Tests And Verification

- Fresh venv install from the chosen artifact.
- `ra version`.
- `ra --root <tmp> demo setup`.
- `ra --root <tmp> demo run`.
- `ra --root <tmp> release-report`.

### Acceptance Criteria

- One primary install path is documented.
- Artifact hashes exist.
- The install path works outside editable mode.

## Phase 7 — Release Notes, Version, And Tag Decision

### Motivation

A release needs a version, release notes, and a tag. Without this, colleagues cannot tell which code they installed or what limitations apply.

### Implementation Instructions

- Decide whether the release remains `0.1.0` or bumps to a new version.
- Run:
  - `ra version`;
  - `ra release-report`;
  - `scripts/run_clean_install_smoke.sh`;
  - `scripts/run_release_smoke.sh`.
- Fill a concrete release notes document from `docs/release_notes_template.md`.
- Include:
  - version;
  - date;
  - install artifact and SHA256;
  - supported platforms;
  - validation command summaries;
  - privacy statement;
  - known limitations;
  - backup/restore warning.
- If tagging:
  - create annotated tag only after final validation;
  - use `git tag -a vX.Y.Z -m "Release vX.Y.Z"`;
  - push tag only when explicitly requested.

### Tests And Verification

- Version consistency remains `ok` in `ra release-report`.
- `CHANGELOG.md` includes the release version.
- Release notes do not claim untested platform support or parser certification.

### Acceptance Criteria

- Version and release notes are unambiguous.
- Tagging is deliberate and documented.

## Phase 8 — Support Boundary And Issue Template

### Motivation

After colleagues install the tool, the first failures will likely be environment-specific. A small support protocol prevents private data leakage and makes bug reports actionable.

### Implementation Instructions

- Add `docs/support.md`.
- Include:
  - what commands to run before asking for help;
  - what output is safe to share;
  - what not to share, including private PDFs, `local_research/`, backup archives, `.codex`, credentials, and provider keys;
  - how to report install failures;
  - how to report parser-tool problems;
  - how to report backup/restore issues.
- Add a short issue template in `docs/support.md` or `.github/ISSUE_TEMPLATE/individual_release_bug.md` if the repo uses GitHub issue templates.
- Update `docs/quickstart.md` and `docs/troubleshooting.md` to link to support instructions.

### Tests And Verification

- Documentation existence check if tests cover required release docs.
- `ra release-report` should include support doc presence if the implementation is updated; otherwise record this as docs-only.

### Acceptance Criteria

- Colleagues know what diagnostic outputs to send.
- Support instructions protect private research data.

## Phase 9 — Final Release Gate

### Motivation

Before broad release, run one final gate so the release candidate is not a collection of stale partial checks.

### Implementation Instructions

Run in order:

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/run_packaging_smoke.sh
scripts/build_release_artifacts.sh
scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
ra --root /tmp/research-assistant-final-release init
ra --root /tmp/research-assistant-final-release release-report
```

Then manually inspect:
- `ra release-report` has no blockers;
- docs match chosen install path;
- known limitations are honest;
- platform support is not overstated;
- generated build outputs are not staged unless intentionally released elsewhere;
- reset memo contains final validation summary.

### Tests And Verification

- Record command summaries in the reset memo.
- Run `git status --short --ignored` and confirm only expected scratch/build outputs remain.

### Acceptance Criteria

- Final gate passes.
- Reset memo contains release decision.
- Commit any docs/support/release-note changes.
- Push `main` if asked.
- Tag only if explicitly requested.

## Final Release Decision

The release can be sent to colleagues when:
- at least one fresh onboarding trial succeeds;
- supported platforms are explicit;
- missing optional parser tools are tested or simulated;
- medium-corpus performance is measured or honestly limited;
- backup/restore rehearsal succeeds;
- the release artifact path is chosen and documented;
- release notes are filled;
- support instructions protect private data;
- final release gate has no blockers.

If any item is incomplete, release as a limited pilot rather than a broad colleague release.
