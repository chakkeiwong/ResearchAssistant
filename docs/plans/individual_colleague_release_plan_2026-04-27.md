# Individual Colleague Release Plan — 2026-04-27

## Purpose

This plan is for an **individual-install release** of `research-assistant` for colleagues in mathematical finance and economics. Each colleague should be able to install the software on their own machine and use it as a private local research tool. There is no shared server, no shared database, no real-time collaboration requirement, no SSO/RBAC requirement, and no multi-user concurrency requirement for this release.

The goal is to make the current local-first research assistant robust, installable, documented, safe, and useful for individual researchers working on frontier projects spanning computational econometrics, computational statistics, machine learning, large language models, large-scale Bayesian learning, computational physics methods, and applied mathematics.

## Release Scope

In scope:
- local install and upgrade;
- first-run setup;
- local config;
- local artifact validation;
- bounded CLI workflows;
- parser/tool preflight;
- local backups and restore;
- demo workflow;
- individual documentation;
- release CI and install smoke tests;
- offline/privacy guarantees;
- graceful error recovery.

Out of scope for this release:
- shared server deployment;
- shared production database;
- SSO or production RBAC;
- real-time collaboration;
- distributed job workers;
- department-wide approval workflows;
- live LLM/provider usage by default.

## Release Principle

The release should feel boringly reliable. A colleague should be able to install it, initialize a local workspace, run a demo, ingest or inspect papers, create local derivation/experiment/traceability artifacts, validate the workspace, export a backup, and understand what happened when something fails.

Generated artifacts remain review material. The tool helps a researcher inspect, organize, and validate evidence; it does not certify mathematical correctness.

## Audit-Driven Correction

An independent developer audit found that the plan is correctly scoped for individual local use, but it needs one explicit implementation rule: the first release slice should implement a coherent local lifecycle rather than isolated commands. The minimum coherent lifecycle is:

1. `ra init` creates an idempotent workspace and default local config.
2. `ra doctor` confirms install, workspace, parser/tool, timeout, and offline status.
3. `ra demo setup/run` creates and exercises a safe demo workspace.
4. `ra workspace validate` and `ra backup create/inspect/restore --dry-run` protect local data.
5. `ra privacy status` proves offline/provider-disabled defaults.
6. `ra release-report` and bounded release smoke scripts summarize readiness.

The first implementation pass should prioritize these local lifecycle commands over production storage, shared collaboration, or live provider work. If a command cannot be fully implemented safely, it must produce a deterministic report explaining the remaining blocker.

## Execution Loop For Future Agents

For each phase:
1. Update the reset memo with the phase start.
2. Implement the smallest stable user-facing behavior.
3. Add unit/integration tests and, where relevant, install or CLI smoke tests.
4. Run bounded validation.
5. Audit from a colleague's perspective: would this be confusing, unsafe, slow, or silent?
6. Tidy docs and command help.
7. Update the reset memo with tests, risks, and next step.
8. Commit after a coherent release slice.

Use `timeout` for all validation. Avoid unbounded test or parser runs.

## Phase 1 — Packaging And Installation

### Motivation

Colleagues should not need to understand the repo internals to install the tool. A release is not usable until installation is predictable and testable.

### Implementation Details

- Review `pyproject.toml` and ensure package metadata is complete:
  - package name;
  - version;
  - Python version;
  - console script `ra`;
  - dependencies;
  - optional dependency groups for parser/PDF tooling if needed.
- Add package build validation:
  - `python -m build` if the project adopts `build`;
  - or a documented local packaging command using existing tooling.
- Add install smoke test script:
  - create a temporary virtual environment;
  - install the package from the repo;
  - run `ra --help`;
  - run `ra version` once implemented.
- Decide whether `pipx install .` is officially supported.
- Document install commands for:
  - local editable developer install;
  - normal user install from a release artifact;
  - optional extras.

### Tests

- Packaging metadata test.
- CLI entry point smoke test.
- Temporary virtualenv install test, marked as release or packaging tier.

### Usefulness Verification

A colleague on a clean machine can follow the install docs and get `ra --help` working within a few minutes.

### Acceptance Criteria

- Install instructions are explicit.
- `ra` console command works after install.
- Optional dependencies are documented rather than silently assumed.

## Phase 2 — First-Run Setup With `ra init`

### Motivation

New users need a safe local workspace without manually creating directories or guessing where data will live.

### Implementation Details

- Add `ra init`.
- Create local workspace directories under a chosen root:
  - `local_research/`;
  - `summaries`;
  - `metadata`;
  - `papers/raw`;
  - `papers/source`;
  - `analysis`;
  - `exports`;
  - `governance`;
  - `indices`.
- Create a default local config file, for example `.research-assistant/config.json`.
- Print a short initialization summary:
  - workspace root;
  - config path;
  - offline-by-default status;
  - next recommended command.
- Make `ra init` idempotent.
- Add `--force` only for safe config regeneration; do not delete data.

### Tests

- `ra init` creates expected directories.
- Running `ra init` twice is safe.
- Existing files are not overwritten unless explicitly safe.
- Config contains expected defaults.

### Usefulness Verification

A new user can initialize a workspace and immediately run validation or demo commands.

### Acceptance Criteria

- No manual directory setup required.
- No destructive behavior.
- Clear user-facing output.

## Phase 3 — Local Configuration Management

### Motivation

Individual users need predictable settings for root paths, timeouts, parser preferences, offline mode, and optional provider settings.

### Implementation Details

- Add config loader and writer.
- Config fields:
  - workspace root;
  - default timeout seconds;
  - offline mode;
  - parser preferences;
  - export directory;
  - optional provider config, disabled by default;
  - validation tier preferences.
- Add commands:
  - `ra config show`;
  - `ra config set KEY VALUE`;
  - `ra config validate`.
- Validate unknown keys and invalid values.
- Never store secrets in plain config without an explicit future secrets design.

### Tests

- Config round-trip tests.
- Invalid config tests.
- CLI config set/show/validate tests.
- Offline/provider defaults test.

### Usefulness Verification

A colleague can change workspace root or timeout without editing Python code.

### Acceptance Criteria

- Config is documented and validated.
- Offline mode defaults to true.
- Provider settings are inert unless explicitly configured later.

## Phase 4 — Versioning, Schema Checks, And Migrations

### Motivation

Colleagues will keep local data across releases. Upgrades must not break or silently mutate workspaces.

### Implementation Details

- Add `ra version`.
- Add workspace schema version tracking.
- Add `ra workspace validate`.
- Add `ra workspace migrate --dry-run`.
- Add migration report artifacts:
  - current version;
  - target version;
  - files affected;
  - warnings;
  - backup requirement;
  - manual review items.
- Do not perform destructive migrations without backup.

### Tests

- Version command test.
- Schema-version detection tests.
- Dry-run migration report tests.
- Unknown future schema version test.

### Usefulness Verification

An upgraded install can tell the user whether their old workspace is compatible before changing it.

### Acceptance Criteria

- Users can inspect version and schema status.
- Migrations are dry-run by default or require explicit confirmation.
- Invalid/future schemas produce clear messages.

## Phase 5 — Local Storage Reliability, Backup, And Restore

### Motivation

For individual installs, local JSON may be acceptable, but users need confidence that their research artifacts can be backed up, restored, validated, and repaired.

### Implementation Details

- Add `ra backup create`.
- Add `ra backup inspect`.
- Add `ra backup restore --dry-run`.
- Use a simple archive format such as `.tar.gz` or `.zip`.
- Include:
  - local research artifacts;
  - config, excluding secrets;
  - manifest with timestamp, schema version, file count, hashes.
- Add `ra workspace repair --dry-run` for missing directories and invalid artifact reports.
- Keep repair non-destructive unless explicitly approved.

### Tests

- Backup archive contains expected files.
- Manifest hash validation.
- Restore dry-run reports target changes.
- Repair dry-run identifies missing directories.

### Usefulness Verification

A colleague can create a backup, inspect it, and verify it can be restored before upgrading.

### Acceptance Criteria

- Backup and restore commands are documented.
- Restore never overwrites without explicit user action.
- Validation reports corrupt or missing files clearly.

## Phase 6 — Robust CLI UX And Error Handling

### Motivation

For colleagues, a good CLI is part of the product. Normal mistakes should produce helpful messages, not stack traces.

### Implementation Details

- Audit all major commands for:
  - help text;
  - required argument errors;
  - missing file errors;
  - invalid JSON errors;
  - unknown IDs;
  - unavailable optional tools.
- Add common error formatting helper.
- Add examples to help text where practical.
- Make command output consistently JSON for machine-readable commands.
- Ensure commands return non-zero only for true command failure.

### Tests

- Help output tests.
- Missing argument tests.
- Missing file tests.
- Invalid JSON tests.
- Unknown artifact ID tests.

### Usefulness Verification

A user can recover from common mistakes by reading the CLI message.

### Acceptance Criteria

- No normal user error emits a raw traceback.
- Commands state what to try next.

## Phase 7 — Parser And Tool Preflight

### Motivation

Individual machines will have different parser/PDF tooling. Users need to know what is available before running slow ingestion workflows.

### Implementation Details

- Extend existing parser preflight if needed.
- Add `ra doctor`.
- Report:
  - Python version;
  - package version;
  - workspace status;
  - optional parser tools availability;
  - PDF extraction availability;
  - TeX/source handling status;
  - configured timeout;
  - offline/provider status.
- Categorize as `ok`, `warning`, or `blocked`.
- Include suggested fixes.

### Tests

- Doctor output schema test.
- Mock missing optional tool test.
- Offline/default provider status test.
- Workspace-not-initialized test.

### Usefulness Verification

A colleague can run `ra doctor` and know whether their setup is ready before ingesting papers.

### Acceptance Criteria

- Environment issues are visible and actionable.
- Optional tools are not treated as hard failures unless required by the selected workflow.

## Phase 8 — Bounded Long-Running Local Workflows

### Motivation

The previous two-hour stale command is exactly what this release must avoid. Individual users need progress, timeouts, logs, and failure artifacts.

### Implementation Details

- Add a local bounded execution helper.
- Add timeout settings to config.
- Apply bounded execution to:
  - ingest;
  - parser runs;
  - benchmark runs;
  - index rebuilds;
  - demo workflow if it grows.
- Create failure artifacts for timeouts and exceptions.
- Print progress for multi-step workflows.
- Add `--timeout` overrides.

### Tests

- Timeout test with a fixture slow command.
- Failure artifact test.
- Timeout override test.
- Progress event schema test.

### Usefulness Verification

A deliberately stuck fixture workflow times out and produces a clear diagnostic artifact.

### Acceptance Criteria

- No common release workflow can hang silently.
- Timeout diagnostics include command, duration, and suggested next step.

## Phase 9 — Golden Individual Workflow Tests

### Motivation

Release confidence should be based on realistic colleague workflows, not only isolated unit tests.

### Implementation Details

- Add a release workflow test using fixture data:
  1. initialize workspace;
  2. ingest or load fixture paper;
  3. inspect source evidence;
  4. create derivation worksheet;
  5. record experiment evidence;
  6. create traceability link;
  7. build readiness report;
  8. export context;
  9. create backup.
- Keep it deterministic and bounded.
- Add script `scripts/run_release_smoke.sh`.

### Tests

- End-to-end release smoke test.
- Export artifact presence checks.
- Trust-boundary checks.

### Usefulness Verification

The release smoke workflow demonstrates the core value proposition on a fixture paper.

### Acceptance Criteria

- One command can validate the release workflow.
- The workflow runs without network or live providers.

## Phase 10 — Demo Mode And Example Data

### Motivation

Colleagues should be able to try the tool before using their own papers.

### Implementation Details

- Add `ra demo setup`.
- Copy or generate a small fixture workspace.
- Add `ra demo run` to execute the golden workflow.
- Add `ra demo clean` only for demo workspace paths, with safe confirmation.
- Include examples for:
  - structured-source paper;
  - derivation worksheet;
  - experiment record;
  - traceability report;
  - readiness report.

### Tests

- Demo setup creates isolated workspace.
- Demo run completes.
- Demo clean refuses non-demo paths.

### Usefulness Verification

A colleague can run the demo and see useful outputs without supplying private data.

### Acceptance Criteria

- Demo mode is isolated from real user data.
- Demo commands are documented in quickstart.

## Phase 11 — Offline-First Privacy And Provider Safety

### Motivation

Colleagues need a clear guarantee that the tool will not send papers or notes to external services unless explicitly configured.

### Implementation Details

- Add privacy section to docs.
- Add offline default to config.
- Add `ra privacy status`.
- Ensure all provider/LLM commands are disabled unless configured.
- Add user-facing warning before any future live network/provider action.
- Add tests that release workflows do not require network.

### Tests

- Offline default test.
- Provider disabled test.
- Privacy status command test.
- Release smoke no-network test where feasible.

### Usefulness Verification

A colleague can inspect privacy status and understand whether anything can leave their machine.

### Acceptance Criteria

- No default workflow sends data externally.
- Provider/LLM access is opt-in and visibly disabled by default.

## Phase 12 — Colleague-Facing Documentation

### Motivation

The tool is not releasable if only the original developers know how to use it.

### Implementation Details

- Add or update:
  - `README.md`;
  - `docs/installation.md`;
  - `docs/quickstart.md`;
  - `docs/workflows/individual_research_workflow.md`;
  - `docs/troubleshooting.md`;
  - `docs/privacy.md`;
  - `docs/release_checklist.md`.
- Include copy-paste commands.
- Include expected outputs for core commands.
- Explain generated-vs-reviewed trust boundary.
- Explain local workspace layout.

### Tests

- Documentation link check where possible.
- Command examples smoke test for selected docs.
- Required docs existence test.

### Usefulness Verification

A colleague unfamiliar with the repo can install, initialize, run demo, and export results using docs only.

### Acceptance Criteria

- Docs cover install, init, demo, ingest, validate, backup, troubleshooting, and privacy.
- Docs do not promise production collaboration or live LLM behavior.

## Phase 13 — Release CI And Validation Tiers

### Motivation

Individual release quality needs repeatable validation before tagging a release.

### Implementation Details

- Define scripts:
  - `scripts/run_fast_tests.sh`;
  - `scripts/run_bounded_tests.sh`;
  - `scripts/run_release_smoke.sh`;
  - optional `scripts/run_packaging_smoke.sh`.
- Add CI configuration if appropriate.
- Separate optional slow parser/PDF tests from fast release path.
- Add release checklist requiring:
  - clean install smoke;
  - release smoke;
  - docs review;
  - privacy review;
  - backup/restore smoke.

### Tests

- Script existence and executable tests.
- Script output includes timeout command.
- CI config smoke where available.

### Usefulness Verification

A maintainer can run one documented release validation sequence before tagging.

### Acceptance Criteria

- Release validation is bounded and documented.
- Slow optional tests cannot accidentally block normal release smoke.

## Phase 14 — Performance On A Personal Corpus

### Motivation

An individual colleague may have hundreds or thousands of papers. Local validation and search must remain usable.

### Implementation Details

- Add synthetic corpus generator.
- Add performance smoke command or test marker.
- Measure:
  - validation time;
  - artifact index build time;
  - search/index rebuild time once search exists;
  - export size and time;
  - backup time.
- Add warnings for very large exports or slow validation.

### Tests

- Small synthetic corpus performance smoke.
- Timeout-protected performance test.
- Large export warning test.

### Usefulness Verification

The tool remains responsive for a representative personal corpus.

### Acceptance Criteria

- Performance tests are bounded.
- Slow operations produce progress or warnings.

## Phase 15 — Release Candidate Process

### Motivation

A colleague-facing release needs a final checklist and a way to communicate limitations.

### Implementation Details

- Add `docs/release_checklist.md`.
- Add `CHANGELOG.md` if missing.
- Add `ra release-report` command or script that summarizes:
  - package version;
  - schema version;
  - test results;
  - known limitations;
  - privacy/offline defaults;
  - optional tool status;
  - migration notes.
- Add release notes template.

### Tests

- Release report schema test.
- Changelog presence test.
- Release checklist required items test.

### Usefulness Verification

A maintainer can produce a release report and send it to colleagues with clear install instructions and known limitations.

### Acceptance Criteria

- Release candidate has version, changelog, install instructions, validation results, and known limitations.
- Known gaps are explicit rather than hidden.

## Cross-Phase Release Acceptance Criteria

The individual-install release is ready when:
- a colleague can install the package and run `ra --help`;
- `ra init` creates a safe local workspace;
- `ra doctor` explains environment readiness;
- config is local, validated, and offline by default;
- release workflow smoke test passes without network;
- backup/restore dry-run works;
- parser/tool availability is visible;
- no default workflow calls live providers;
- documentation supports install through demo;
- release validation scripts are bounded;
- generated artifacts remain clearly marked as review material.

## Suggested Release Validation Sequence

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/run_release_smoke.sh
scripts/run_packaging_smoke.sh
```

If a script is not implemented yet, the responsible phase must either implement it or mark it as a release blocker.

## Independent Audit Notes

Risks:
- Installing optional parser/PDF tools can be platform-specific.
- Local JSON storage is acceptable for individual release only if backup, validation, and migration are solid.
- Demo mode must not touch real user data.
- Provider/LLM settings must stay disabled by default.
- Release docs must not imply shared-server collaboration or production approval workflows.

Mitigations:
- Keep optional tooling explicit.
- Add `ra doctor`.
- Add backup and restore before encouraging real use.
- Keep release workflows offline.
- Mark generated outputs as review material in docs and CLI output.
