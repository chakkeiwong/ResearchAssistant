# Individual Git Release Final Gap Closure Plan - 2026-04-28

## Purpose

This is the handoff plan for closing the remaining gaps before
`research-assistant` can be honestly released as an individual local research
tool with Git-based sharing.

The current target is defined in:

- `docs/proposal/individual_git_release_target.md`

The implementation baseline already includes:

- `ra repository-hygiene check/policy/classify`;
- `ra workspace merge` dry-run and explicit apply mode;
- `ra workspace rebuild-derived`;
- `ra individual-git-release gate-build`;
- shareable workspace policy;
- Git sharing workflow docs;
- conservative trust-boundary behavior.

The remaining work is not a database, shared service, SSO/RBAC, hosted UI, or
real-time collaboration project. Those are deferred future-platform concerns.
This plan focuses on release validation, realistic Git-sharing evidence,
repository hygiene hardening, docs walkthrough, release gate calibration, and
publication readiness.

## Current Known Gaps

- Real colleague onboarding from docs is not recorded.
- macOS validation is not recorded.
- Minimal parser-tool environment validation is not recorded on a real minimal
  machine.
- Linux/WSL validation exists historically but should be recorded in the
  individual Git release evidence format.
- Release-owner tag/publication approval is not recorded.
- Merge/import has focused tests, but not realistic overlapping-workspace
  fixture validation.
- Repository hygiene catches obvious unsafe files/fields but needs broader
  secret-pattern checks and release/CI integration.
- Docs mention Git sharing, but the end-to-end walkthrough has not been tested
  by a fresh reader.
- `ra individual-git-release gate-build` correctly blocks broad release, but it
  needs recorded validation evidence before it can pass.
- Synthetic performance checks exist, but merge/import performance on a
  representative individual-size workspace is not recorded.
- Parser quality is still not certified and must remain explicitly limited.

## Non-Negotiable Rules

- Keep the release scoped to individual local use plus Git-based sharing.
- Do not introduce database, service deployment, SSO/RBAC, hosted UI, or
  real-time collaboration requirements.
- Preserve the trust boundary: generated, parser, benchmark, derivation,
  traceability, LLM, merge, and readiness artifacts are review material.
- Do not commit private papers, local corpora, backup archives, `.codex`,
  `.claude`, caches, `build/`, `dist/`, credentials, provider keys, tokens, or
  generated local workspaces.
- Use sanitized fixture repositories for automated tests.
- Use `timeout` around validation commands.
- Do not create a Git tag or publish artifacts unless the user/release owner
  explicitly approves that release action.
- If external validation cannot be performed locally, record it as blocked or
  pending. Do not fake it.

## Required Audit Before Execution

Before executing this plan, another agent must audit it from five perspectives:

- **Product scope:** Does the plan stay focused on individual local use and Git
  sharing?
- **Release management:** Are validation evidence, tag decision, release notes,
  and support boundaries explicit?
- **Privacy/data safety:** Could any command or fixture leak private papers,
  local paths, backup archives, credentials, or provider keys?
- **Research trust:** Could merge/import or release gates imply mathematical
  approval, parser accuracy, or semantic correctness?
- **Engineering:** Are tests deterministic and fixture-based, with external
  validations clearly separated from local automation?

If audit finds missing points, update this plan first and record the audit
result in `docs/plans/reset_memo_2026-04-26.md`.

### Audit Result For Current Execution

Audit completed before implementation. The plan is suitable for the current
individual local + Git-sharing target, with one execution clarification:

- Real colleague onboarding, macOS validation, real minimal-machine parser-tool
  validation, release-owner tag approval, and publication approval cannot be
  completed autonomously by a local coding agent.
- Local automation may record deterministic substitutes for those checks, but
  substitutes must be labelled as such and must not satisfy real external
  validation requirements.
- The final gate may pass local fixture gates while remaining blocked for broad
  release or publication until the real manual validations and approvals exist.

## Execution Loop

For every phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start and intent.
2. Plan the smallest safe implementation or validation step.
3. Execute locally with deterministic fixtures where possible.
4. Run focused tests before broader validation.
5. Audit as another developer for privacy leakage, false approval, stale docs,
   and target-scope drift.
6. Tidy generated outputs and avoid staging private/generated files.
7. Update the reset memo with evidence, blockers, and next safe step.
8. Commit coherent phase groups only after validation.

Because `docs/plans/` is ignored, force-stage intentional plan/reset memo
changes with `git add -f`.

## Phase 1 - Validation Evidence Schema And Local Recorder

### Motivation

The current gate knows external validation is missing, but release evidence
needs a first-class local record format. Without a schema, agents will scatter
validation notes across reset memos and release notes, making the final gate
hard to audit.

### Implementation Instructions

- Add a validation evidence schema for the individual Git release, for example:
  - `individual-git-validation-v1`;
  - validation type;
  - platform;
  - Python version;
  - install method;
  - command summary;
  - result: `passed`, `warnings`, or `blocked`;
  - sanitized blockers/warnings;
  - no private paths/titles/content.
- Add CLI command:

```bash
ra individual-git-release validation-record --validation-type linux_wsl --result passed ...
ra individual-git-release validation-report
```

- Store records under:

```text
local_research/governance/individual_git_release/validation/
```

- Required validation types for broad release:
  - `linux_wsl`;
  - `colleague_onboarding`;
  - `macos` or explicit unavailable waiver;
  - `minimal_parser_tools`;
  - `merge_fixture_rehearsal`;
  - `representative_workspace_performance`.

- Reject forbidden fields:
  - `private_pdf`;
  - `private_title`;
  - `backup_archive`;
  - `credential`;
  - `provider_key`;
  - `token`;
  - private local paths.

### Tests

- Passing validation record fixture.
- Missing required field fixture.
- Forbidden private field fixture.
- Validation report blocks broad release when required records are absent.

### Acceptance Criteria

- A release manager can see which individual Git release validations are
  complete and which remain pending.

## Phase 2 - Realistic Git-Sharing Fixture Repositories

### Motivation

The current merge/import tests prove mechanics on small fixtures. Release
confidence needs more realistic repositories with overlapping papers, generated
artifacts, conflicts, and safe imports.

### Implementation Instructions

- Add deterministic fixture builders in tests or fixtures for:
  - source workspace with 10-25 shareable papers/artifacts;
  - target workspace with overlapping and non-overlapping papers;
  - one same-path conflict;
  - one accepted `technical_audit` conflict;
  - one rebuildable index/report;
  - one forbidden raw/private file;
  - one generated proposal artifact that remains review material.
- Add a scripted or CLI fixture rehearsal:

```bash
ra workspace merge --source <fixture-source> --target <fixture-target>
ra workspace merge --source <fixture-source> --target <fixture-target> --apply --confirm-merge
ra workspace rebuild-derived
ra repository-hygiene check
```

- Keep fixtures sanitized and small enough for deterministic tests.

### Tests

- Dry-run counts match expected copy/skipped/conflict/blocked totals.
- Apply copies only safe files.
- Merge provenance exists on imported JSON.
- Rebuild regenerates artifact index/readiness.
- Conflicts remain unresolved and are not overwritten.

### Acceptance Criteria

- The release has realistic evidence that Git checkout/import sharing works for
  individual research workspaces.

## Phase 3 - Repository Hygiene Hardening

### Motivation

`ra repository-hygiene check` catches obvious unsafe paths and fields. Before
release, it should catch common secret patterns and be usable as a release/CI
gate.

### Implementation Instructions

- Extend hygiene checks to scan text/JSON for high-risk patterns:
  - `OPENAI_API_KEY`;
  - `ANTHROPIC_API_KEY`;
  - `AWS_ACCESS_KEY_ID`;
  - `BEGIN PRIVATE KEY`;
  - common token labels such as `api_key`, `secret_key`, `access_token`;
  - provider-key-like long strings only when paired with suspicious keys, to
    avoid noisy false positives.
- Add `--strict` option if useful:

```bash
ra repository-hygiene check --strict
```

- In strict mode, untracked `.codex`, `.claude`, `build/`, `dist/`, raw papers,
  backups, or generated caches should block release sharing even if not staged.
- Add a release checklist command or script step:

```bash
ra repository-hygiene check --strict
```

- Update docs with remediation instructions.

### Tests

- Secret-looking JSON config is blocked.
- Provider-key-like field in validation record is blocked.
- Benign ordinary text is not blocked.
- Strict mode blocks untracked unsafe directories in a fixture repo.

### Acceptance Criteria

- Repository hygiene is strong enough to be used as a pre-share and pre-release
  gate.

## Phase 4 - Docs Walkthrough And Fresh-Reader Trial

### Motivation

The docs now describe Git sharing, but a release is for real users. A fresh
reader should be able to install, initialize, validate, share, import, rebuild,
and understand limitations without knowing project history.

### Implementation Instructions

- Create or update a walkthrough doc:

```text
docs/workflows/git_sharing_walkthrough.md
```

- The walkthrough should cover:
  - install or source checkout;
  - `ra init`;
  - create or inspect a small local workspace;
  - `ra repository-hygiene check`;
  - commit shareable artifacts;
  - clone another fixture repository;
  - merge dry-run;
  - apply safe imports;
  - rebuild derived reports;
  - resolve conflicts manually;
  - backup/restore safety;
  - what not to share.

- Add an onboarding evidence template for a fresh reader, stored as sanitized
  validation evidence.
- If no real fresh reader is available, mark this phase blocked for external
  validation and run only the automated fixture substitute.

### Tests

- Docs presence check.
- Command snippets are covered by existing CLI tests or a lightweight docs smoke
  fixture.

### Acceptance Criteria

- A new researcher can follow the workflow without manual JSON editing.

## Phase 5 - Gate Calibration For Current Target

### Motivation

`ra individual-git-release gate-build` currently blocks correctly. It should
become the final source of truth for the current release target by incorporating
validation evidence, hygiene strictness, merge fixture rehearsal, performance,
and publication status.

### Implementation Instructions

- Extend gate output with:
  - validation evidence summary;
  - required validation types and missing types;
  - repository hygiene strict status;
  - merge fixture rehearsal status;
  - representative workspace performance status;
  - release notes/version/artifact status;
  - publication/tag approval status;
  - deferred future-platform items.
- Ensure database/service/RBAC/UI remain deferred, not blockers for current
  target.
- Add machine-readable booleans:
  - `ready_for_limited_individual_pilot`;
  - `ready_for_broad_individual_release`;
  - `ready_for_git_shared_research_release`;
  - `future_multi_user_platform_deferred`.

### Tests

- Gate blocks when validation records are missing.
- Gate blocks when strict repository hygiene fails.
- Gate blocks when merge fixture rehearsal is missing.
- Gate reports future multi-user items as deferred.
- Gate can report ready for fixture-only local target when all local fixture
  records are supplied, while still marking real external validation separately
  if unavailable.

### Acceptance Criteria

- A release manager can run one command and know whether the individual
  Git-sharing release is ready, blocked, or only pilot-ready.

## Phase 6 - Representative Workspace Performance

### Motivation

Synthetic performance smoke exists, but merge/import adds new workload. The
release should record practical limits for an individual-size workspace.

### Implementation Instructions

- Add performance rehearsal for:
  - repository hygiene over a synthetic workspace;
  - merge dry-run over overlapping synthetic workspaces;
  - merge apply for safe subset;
  - rebuild-derived;
  - backup creation after merge.
- Use tiers:
  - `synthetic_git_100`;
  - `synthetic_git_1000`;
  - optional `sanitized_real_small`.
- Record:
  - elapsed seconds;
  - file counts;
  - copied/skipped/conflict counts;
  - backup size;
  - warnings/blockers.

### Tests

- Small deterministic performance report test.
- Timeout diagnostic test if threshold is exceeded.

### Acceptance Criteria

- Release notes can state tested Git-sharing workspace size and limitations.

## Phase 7 - Parser Limitation And Minimal Environment Evidence

### Motivation

The release should be honest that parser availability/degradation is tested,
but parser quality is not certified.

### Implementation Instructions

- Record minimal parser-tool environment validation evidence if a real minimal
  machine is available.
- If unavailable, run deterministic missing-tool simulation and record it as a
  local substitute, not real external validation.
- Update release notes and known limitations:
  - parser-tool availability is checked;
  - parser benchmark smoke is fixture-only;
  - parser scientific accuracy is not certified.

### Tests

- Existing missing-tool simulation tests remain green.
- Validation report distinguishes real minimal-machine record from local
  substitute.

### Acceptance Criteria

- Parser claims are conservative and backed by recorded evidence.

## Phase 8 - Publication Readiness And Release Notes

### Motivation

The code can be ready while the release is not publishable. Version, artifact,
release notes, tag approval, and support boundary must align.

### Implementation Instructions

- Update release notes for the current target:
  - individual local tool;
  - Git sharing workflow;
  - validated platforms;
  - validation evidence status;
  - tested workspace/merge size;
  - parser limitations;
  - privacy boundary;
  - support boundary;
  - known blockers.
- Run:

```bash
scripts/build_release_artifacts.sh
ra release-artifacts manifest
ra individual-git-release gate-build
ra repository-hygiene check --strict
```

- Do not create a tag or publish artifacts unless explicitly approved.
- If approval is unavailable, record publication as blocked/manual.

### Tests

- Release notes contain current target and artifact hash.
- Version consistency remains `ok`.
- Publication/gate report blocks when approval is missing.

### Acceptance Criteria

- Release owner has a concrete, auditable go/no-go packet.

## Phase 9 - Final Ordered Gate

### Motivation

The final release decision should not depend on stale partial checks.

### Implementation Instructions

- Add or update a final script:

```bash
scripts/run_individual_git_release_gate.sh
```

- The script should run:
  - fast tests;
  - bounded tests;
  - individual Git release integration tests;
  - repository hygiene strict check;
  - merge fixture rehearsal;
  - release-report;
  - individual Git release gate.

- Use bounded `timeout`.
- Script should pass as a reporting gate even if the final gate status is
  `blocked` for missing manual external validation or publication approval.

### Tests

- Script existence/executable test.
- Script smoke if bounded enough.

### Acceptance Criteria

- One command produces the final local validation packet for the current release
  target.

## Final Definition Of Done

The release can move beyond pilot only when:

- validation evidence schema/report exists;
- required validation records are recorded or explicitly blocked with reason;
- realistic Git-sharing fixture merge dry-run/apply/rebuild passes;
- repository hygiene strict mode catches secrets/private/generated files;
- docs walkthrough is validated by a fresh reader or marked externally blocked;
- performance evidence records tested workspace/merge size;
- parser limitations are explicit and conservative;
- release notes and artifact manifest align;
- final individual Git release gate has no current-target blockers except any
  consciously waived manual external validation;
- tag/publication approval is explicit.

If these conditions are incomplete, keep the release as a limited individual
pilot and document the exact remaining blockers.
