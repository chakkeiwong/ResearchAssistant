# Individual Release Gap Closure Plan — 2026-04-27

## Purpose

This document is a handoff-ready plan for closing the remaining gaps before `research-assistant` is released to colleagues as an individual local research tool.

The previous implementation round added the coherent local lifecycle: `ra init`, `ra doctor`, config/workspace/backup/demo/privacy/release-report commands, bounded release smoke scripts, colleague-facing docs, and tests. The remaining work is release hardening: proving installability on clean machines, validating optional parser environments, protecting local data, packaging a repeatable release artifact, and making the release candidate process explicit.

This plan is **not** for a shared server or production departmental platform. Each colleague installs and uses a private local workspace. No shared database, SSO/RBAC, live collaboration, distributed workers, or default live LLM/provider calls are in scope.

## Current Baseline

Committed baseline:
- `58ca98f Add individual release lifecycle commands`
- `ec4ed1c Record individual release checkpoint`

Useful existing surfaces:
- CLI: `ra init`, `ra doctor`, `ra config`, `ra workspace`, `ra backup`, `ra demo`, `ra privacy`, `ra bounded-workflow`, `ra performance`, `ra release-report`
- Scripts: `scripts/run_fast_tests.sh`, `scripts/run_bounded_tests.sh`, `scripts/run_release_smoke.sh`, `scripts/run_packaging_smoke.sh`
- Docs: `docs/installation.md`, `docs/quickstart.md`, `docs/workflows/individual_research_workflow.md`, `docs/troubleshooting.md`, `docs/privacy.md`, `docs/release_checklist.md`
- Tests: `tests/integration/test_individual_release_cli.py`

## Non-Negotiable Release Principles

- Default workflows must remain offline and provider-disabled.
- Generated artifacts are review material and must not certify mathematical correctness.
- Every long-running validation command must use `timeout`.
- Every destructive workflow must default to dry-run and require explicit confirmation.
- Release validation must work without live network, Docker, GUI apps, external services, or private credentials.
- Plans and reset memos under `docs/plans/` are ignored by `.gitignore`; force-stage intentional plan/reset changes with `git add -f`.

## Execution Loop For The Next Agent

For each phase:
1. Update `docs/plans/reset_memo_2026-04-26.md` with the phase start.
2. Implement the smallest user-facing behavior that closes the gap.
3. Add focused tests before broad tests.
4. Run bounded validation with `timeout`.
5. Audit as a different developer: look for data loss, misleading readiness, network leakage, bad UX, stale docs, and false approval.
6. Tidy docs, help text, and scripts.
7. Update the reset memo with files touched, tests run, residual risks, and next safe step.
8. Commit after a coherent phase or group of tightly related phases.

## Audit Amendment — Phase 0 Release-Hardening Contract

An independent developer audit found that the 9 phases are complete in scope, but they need a shared reporting contract. Without one, clean-install smoke, parser matrix, restore, performance, packaging, onboarding, versioning, platform, and corruption checks could become separate commands that do not feed a single release decision.

Before Phase 1, add a Phase 0 contract:
- define a release hardening status schema with `status`, `blockers`, `warnings`, `checks`, `artifacts`, `docs`, `scripts`, `platform`, `privacy`, and `known_limitations`;
- make `ra release-report` aggregate every implemented hardening signal;
- keep all hardening signals local/offline and human-review-aware;
- add tests that release-report degrades to `blocked` or `warnings` when required docs/scripts/checks are missing or failing;
- update reset memo after every phase with the release-report status.

## Phase 1 — Clean-Machine Install Validation

### Motivation

The current packaging smoke verifies metadata and an offline `pip install --dry-run --no-build-isolation`, but that is not enough for colleagues. A release candidate must prove that a user can create a fresh environment, install the package, run `ra --help`, initialize a workspace, and run the demo without relying on the source checkout's editable state.

This closes the highest-risk release gap: "works on my repo" versus "works on a colleague's machine."

### Implementation Details

- Add `scripts/run_clean_install_smoke.sh`.
- The script must:
  - create a temporary directory under `/tmp`;
  - create a fresh virtual environment;
  - install the project from the local repo using a deterministic mode;
  - run `ra --help`;
  - run `ra version`;
  - run `ra --root <tmp-workspace> init`;
  - run `ra --root <tmp-workspace> doctor`;
  - run `ra --root <tmp-workspace> demo setup`;
  - run `ra --root <tmp-workspace> demo run`;
  - run `ra --root <tmp-workspace> release-report`.
- Prefer an offline path first:
  - use `python -m pip install --no-build-isolation "$ROOT"` when local build dependencies are available;
  - if isolated build is required, make the script fail with a clear message explaining that network or prebuilt wheels are needed.
- Add environment variables:
  - `ROOT`;
  - `TIMEOUT_SECONDS`;
  - `KEEP_TMP=1` to preserve the temporary workspace for debugging.
- Ensure cleanup is safe:
  - remove only the script-created temp directory;
  - never remove user-selected paths.
- Add docs to `docs/installation.md` and `docs/release_checklist.md`.

### Tests

- Unit/shell test that the script exists and is executable.
- Integration test that invokes the script with a small timeout where feasible, or tests the key commands in a temporary venv if runtime is acceptable.
- Test that the script prints the exact commands it runs.
- Test that `KEEP_TMP=1` preserves the temp directory if the script supports that behavior.

### Usefulness Verification

Run the script on at least one machine/session that does not already have the package installed in editable mode. Record the result in the reset memo.

### Acceptance Criteria

- A clean virtual environment can install and run `ra`.
- Demo workflow runs from the installed console script.
- Failure messages distinguish missing build dependencies from application failures.

## Phase 2 — Optional Parser And Tool Matrix

### Motivation

Colleagues will have different local parser/PDF tooling. The current `ra doctor` reports optional tools, but release confidence needs a matrix showing which workflows work with no optional tools, which workflows improve with optional tools, and what fails gracefully when tools are absent or misconfigured.

This phase also absorbs the parser benchmark-depth gap: do not promise industrial parser quality yet, but make parser availability, parser limitations, and fixture benchmark status visible enough for release.

### Implementation Details

- Extend `ra doctor` output with a `workflow_readiness` section:
  - `core_local_lifecycle`;
  - `demo_workflow`;
  - `metadata_only_ingest`;
  - `pdf_text_ingest`;
  - `structured_source_inspection`;
  - `parser_benchmark_smoke`.
- Each workflow readiness entry should include:
  - `status`: `ok`, `warnings`, or `blocked`;
  - `required_tools`;
  - `optional_tools`;
  - `available_tools`;
  - `missing_tools`;
  - `suggested_fix`;
  - `limitations`.
- Add a parser matrix command or subcommand:
  - acceptable options: `ra doctor --matrix` or `ra parser-tool-matrix`;
  - output must be JSON and deterministic.
- Add a fixture-only parser benchmark smoke:
  - use existing synthetic benchmark fixtures;
  - report expected fixture availability and scoring status;
  - do not require TeX compilation, live GROBID, live MinerU, Docker, or network.
- Update `docs/troubleshooting.md` with tool-specific guidance.
- Update `docs/release_checklist.md` with the supported-tool matrix language.

### Tests

- Mock `shutil.which` or the tool-detection helper to simulate:
  - no optional tools;
  - only `pdftotext`;
  - all optional tools;
  - misconfigured tool placeholder, if supported.
- Tests that core lifecycle remains `ok` without optional parser tools.
- Tests that PDF/parser workflows report `warnings` or `blocked` with suggested fixes rather than stack traces.
- Fixture benchmark smoke tests with expected JSON fixtures.

### Usefulness Verification

A colleague can run one command and understand whether their machine can do PDF ingest, parser comparison, structured-source inspection, and demo workflows.

### Acceptance Criteria

- Missing optional tools do not block non-parser workflows.
- Parser/PDF limitations are explicit and actionable.
- No deterministic test requires live external services.

## Phase 3 — Non-Dry-Run Restore With Safe Confirmation

### Motivation

The current backup path can create and inspect archives, and restore dry-run reports what would be overwritten. That is good for safety but incomplete for real upgrades. Before release, a colleague should be able to restore a backup into a new empty workspace and, with explicit confirmation, into an existing workspace.

This is the most data-sensitive phase. Safety matters more than convenience.

### Implementation Details

- Extend `ra backup restore` with non-dry-run support guarded by explicit confirmation.
- Keep default behavior as dry-run.
- Add flags:
  - `--target-root PATH` or reuse global `--root` as restore target;
  - `--confirm-restore`;
  - `--allow-overwrite`, default false;
  - `--backup-current-first`, default true for overwrite cases.
- Restore rules:
  - restoring into an empty target with `--confirm-restore` is allowed;
  - restoring into a target with existing files requires `--allow-overwrite`;
  - overwriting existing files should first create a safety backup unless explicitly disabled by a carefully named flag;
  - never restore paths outside the target root;
  - reject archives with absolute paths or `..` path traversal;
  - preserve manifest and restore report artifacts.
- Add restore report JSON:
  - archive path;
  - target root;
  - restored file count;
  - skipped file count;
  - overwritten file count;
  - safety backup path, if created;
  - hash validation results;
  - warnings.
- Update docs with restore examples:
  - dry-run;
  - restore into fresh workspace;
  - restore with overwrite confirmation.

### Tests

- Restore dry-run remains default.
- Restore into empty target succeeds only with `--confirm-restore`.
- Restore without confirmation is blocked.
- Existing file restore without `--allow-overwrite` is blocked.
- Existing file restore with `--allow-overwrite` creates a safety backup.
- Path traversal archive is rejected.
- Manifest hash mismatch is reported.
- Restored workspace passes `ra workspace validate`.

### Usefulness Verification

Create a demo workspace, back it up, restore into a fresh temp root, and run `ra workspace validate` plus `ra show` or demo artifact checks on the restored workspace.

### Acceptance Criteria

- A real restore workflow exists.
- The default remains safe.
- No restore operation can write outside the target root.

## Phase 4 — Real Personal Corpus Performance Smoke

### Motivation

The current `ra performance smoke` creates a small synthetic corpus and measures validation overhead. That is a useful start, but colleagues may have hundreds or thousands of papers. Release validation should expose whether local validation, backup, export, and artifact indexing remain responsive.

This phase should still be bounded and local. It should not require a real private corpus in tests.

### Implementation Details

- Extend `ra performance smoke` with:
  - `--synthetic-count`;
  - `--include-industrial-artifacts`;
  - `--include-backup`;
  - `--include-export`;
  - `--timeout-seconds`;
  - `--output`.
- Generate synthetic but realistic local data:
  - summaries;
  - metadata;
  - source records;
  - derivation worksheets;
  - experiment plans/runs;
  - links;
  - traceability/governance records where bounded.
- Measure:
  - workspace validation time;
  - artifact index build time;
  - export-context time;
  - backup create time;
  - backup size;
  - record counts by family.
- Add thresholds:
  - default thresholds for 100, 1,000, and 5,000 synthetic records;
  - threshold warnings, not hard failures, unless a timeout occurs.
- Add progress events so large runs are not silent.
- Write a performance report artifact under `local_research/governance/` or `local_research/jobs/`.

### Tests

- Small synthetic corpus smoke with 10 to 25 records.
- Threshold warning test using deliberately tiny threshold.
- Timeout diagnostic test.
- Report schema test.
- Test that generated synthetic data is clearly labeled and does not look like real papers.

### Usefulness Verification

Run a bounded 1,000-record synthetic smoke locally and record timings in the reset memo. If too slow, document bottlenecks instead of hiding them.

### Acceptance Criteria

- Maintainers can estimate local performance before release.
- Slow operations produce progress and warnings.
- The smoke does not require private data.

## Phase 5 — Release Artifact Packaging

### Motivation

Colleagues need a clear installation artifact and command. A source checkout may be fine for developers, but a colleague-facing release should decide whether the supported path is wheel, source distribution, `pipx`, local Git checkout, or some combination.

This phase turns installation from "possible" into "repeatable."

### Implementation Details

- Decide the official supported install modes:
  - recommended: wheel artifact plus optional source checkout for developers;
  - optional: `pipx install path/to/research_assistant.whl`.
- Add `scripts/build_release_artifacts.sh`.
- The script should:
  - clean only build directories it owns (`build/`, `dist/`, egg-info if safe);
  - build wheel and sdist if `build` is available;
  - otherwise use `python -m pip wheel --no-build-isolation . -w dist/`;
  - compute SHA256 hashes for artifacts;
  - write `dist/release_artifacts_manifest.json`.
- Add packaging metadata checks:
  - package version matches `research_assistant.__version__`;
  - console script exists;
  - docs mention the same install path.
- Update `docs/installation.md` with:
  - install from wheel;
  - install from source checkout;
  - editable developer install;
  - optional `pipx` instructions if validated.
- Add `docs/release_notes_template.md`.

### Tests

- Metadata consistency test between `pyproject.toml` and `src/research_assistant/__init__.py`.
- Script existence/executable test.
- Build manifest schema test, if artifact build is run in CI/release tier.
- Clean install from built wheel smoke, if feasible locally.

### Usefulness Verification

Build a wheel, install it into a fresh venv, and run `ra version`, `ra doctor`, and demo setup/run.

### Acceptance Criteria

- There is a documented primary install artifact.
- Release artifacts have hashes.
- Console script works from the artifact.

## Phase 6 — Documentation Trial And Onboarding Feedback

### Motivation

Documentation is only useful if a colleague can follow it without knowing repo history. The current docs are present, but they have not been trialed by a fresh user.

This phase creates a lightweight process for finding confusing instructions before release.

### Implementation Details

- Add `docs/onboarding_trial.md`.
- Include a scriptable checklist:
  - install;
  - `ra --help`;
  - `ra version`;
  - initialize workspace;
  - run doctor;
  - run demo setup/run;
  - inspect release report;
  - create backup;
  - inspect backup;
  - privacy status;
  - optional ingest with a local PDF.
- Add expected observations and blank fields:
  - time spent;
  - platform;
  - install mode;
  - confusing step;
  - command output mismatch;
  - optional tools available;
  - release blocker yes/no.
- Add `docs/known_limitations.md` so feedback does not get buried in reset memos.
- Update `ra release-report` to include `known_limitations.md` and onboarding trial doc presence.
- Optionally add a `ra onboarding-report` command that emits the checklist as JSON.

### Tests

- Required docs existence test.
- Release report includes onboarding/known-limitations doc presence.
- Markdown command examples smoke test for selected commands, if a docs-smoke helper exists.

### Usefulness Verification

Have at least one colleague or developer not involved in the implementation follow the docs. Record their platform, install mode, time-to-demo, and blockers in the reset memo.

### Acceptance Criteria

- A fresh reader can install and run the demo from docs only.
- Known limitations are visible and not hidden in implementation notes.

## Phase 7 — Versioning, Tagging, Changelog, And Release Notes

### Motivation

A release needs a stable version and a way for colleagues to understand what changed, what is supported, and what remains limited. Without version/tag discipline, support conversations become ambiguous.

### Implementation Details

- Decide next release version:
  - current package version is `0.1.0`;
  - either keep it for the first release candidate or bump to `0.1.1`/`0.2.0` depending on scope.
- Add a version consistency helper:
  - `pyproject.toml`;
  - `src/research_assistant/__init__.py`;
  - `CHANGELOG.md`;
  - release report.
- Add `docs/release_notes_template.md` with:
  - version;
  - date;
  - installation artifact;
  - hashes;
  - supported platforms;
  - validation results;
  - known limitations;
  - privacy statement;
  - migration/backup notes.
- Add a release-candidate checklist section for Git tags:
  - `git tag -a vX.Y.Z -m "..."`
  - push tag only after final smoke.
- Do not create a tag automatically unless the user explicitly asks.

### Tests

- Version consistency test.
- Changelog has an entry for the current version.
- Release notes template required headings test.
- `ra release-report` includes package version and schema versions.

### Usefulness Verification

Generate a draft release report and release notes for the current version and confirm they contain enough information to send to colleagues.

### Acceptance Criteria

- Version is unambiguous.
- Release notes are ready before tagging.
- Tagging is documented and deliberate.

## Phase 8 — Platform Compatibility

### Motivation

The tool is local, but colleagues may use different platforms. At minimum, the release should state what is supported and what has been tested. If Windows native is not supported, say so plainly and support WSL instead.

### Implementation Details

- Add `docs/platform_support.md`.
- Define support tiers:
  - Tier 1: Linux with Python 3.10+;
  - Tier 2: macOS with Python 3.10+;
  - Tier 3: Windows via WSL, if validated;
  - unsupported or untested: Windows native, unless tested.
- Add `ra doctor` platform details:
  - OS name;
  - architecture;
  - Python executable;
  - filesystem case sensitivity warning if relevant;
  - shell/path notes where detectable.
- Add release checklist entries for each supported platform.
- Make scripts use POSIX shell only; document that `.sh` scripts are for Linux/macOS/WSL.
- If Windows native is desired later, plan PowerShell equivalents separately.

### Tests

- Doctor output includes platform fields.
- Platform support doc existence/headings test.
- Script shebang/executable tests.

### Usefulness Verification

Run clean install smoke on the Tier 1 platform and, if available, one macOS or WSL machine. Record results in reset memo or release notes.

### Acceptance Criteria

- Supported platforms are explicit.
- Unsupported platforms fail by expectation, not surprise.
- Doctor report helps identify platform-specific issues.

## Phase 9 — Data-Loss And Corruption Hardening

### Motivation

For an individual local tool, data safety is the release-critical feature. Users will trust it with notes, paper metadata, derivation worksheets, experiment records, and backups. The current implementation has validation and backup primitives, but release hardening should test corrupted config, malformed artifacts, partial backups, interrupted writes, and recovery guidance.

### Implementation Details

- Add a corruption fixture suite:
  - invalid JSON config;
  - unknown config key;
  - invalid timeout;
  - malformed artifact missing base fields;
  - future schema version;
  - backup missing manifest;
  - backup with hash mismatch;
  - partial restore target.
- Improve error reporting where needed:
  - no raw tracebacks for expected user errors;
  - JSON reports include `status`, `issues`, `suggested_next_step`;
  - commands return nonzero only for true command failure, while validation reports may return JSON with `blocked`.
- Add atomic write helper for critical JSON writes if practical:
  - write to temp file in same directory;
  - fsync or best-effort flush;
  - atomic rename.
- Apply atomic writes to config, backup manifests/reports, and key artifact writes if scope allows.
- Add `ra workspace repair --apply` or `--no-dry-run` only for safe missing-directory repair, not content repair.
- Update troubleshooting docs with corruption recovery steps.

### Tests

- Invalid config validation test.
- Malformed artifact validation test.
- Future schema warning/blocker test.
- Backup missing manifest test.
- Hash mismatch test.
- Atomic write helper test, if implemented.
- Expected user-error CLI tests avoid raw traceback.

### Usefulness Verification

Deliberately corrupt a demo workspace copy and confirm `ra workspace validate`, `ra doctor`, `ra backup inspect`, and docs tell the user what to do next.

### Acceptance Criteria

- Common corruption modes are detected and explained.
- Repair remains conservative and non-destructive.
- Backup/restore refuses unsafe archives.

## Cross-Phase Final Release Gate

Before a broad colleague release, run and record:

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/run_release_smoke.sh
scripts/run_packaging_smoke.sh
scripts/run_clean_install_smoke.sh
```

Then manually verify:
- clean install from chosen artifact;
- demo setup/run/release-report;
- backup create/inspect/restore into fresh workspace;
- `ra doctor` on a machine with missing optional parser tools;
- privacy status remains offline/provider-disabled;
- release notes and known limitations are accurate.

## Final Acceptance Criteria

The individual release is ready when:
- a clean machine or fresh venv can install and run `ra`;
- the supported install artifact is documented and hashed;
- optional parser/tool gaps are visible and non-catastrophic;
- real restore into a fresh workspace works safely;
- small and medium synthetic corpus smokes are bounded and reported;
- docs have been trialed by at least one fresh reader;
- version, changelog, release notes, and tag plan are consistent;
- supported platforms are explicit;
- corrupted local data is detected with actionable guidance;
- no default workflow sends private content to external providers;
- generated artifacts remain review material.
