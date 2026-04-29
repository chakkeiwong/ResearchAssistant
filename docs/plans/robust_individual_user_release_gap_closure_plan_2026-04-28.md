# Robust Individual User Release Gap Closure Plan - 2026-04-28

## Purpose

This plan closes the remaining gaps before `research-assistant` can move from a
limited individual pilot to a robust individual-user release.

The product target is still:

- one researcher at a time;
- local filesystem storage;
- offline-by-default workflows;
- Git-based sharing by checkout/import/merge;
- no shared database, hosted service, SSO/RBAC, real-time collaboration, or
  hosted UI requirement for this release.

The current target definition is:

- `docs/proposal/individual_git_release_target.md`

The current implementation baseline includes:

- `ra repository-hygiene check --strict`;
- `ra workspace merge`;
- `ra workspace rebuild-derived`;
- `ra individual-git-release validation-record`;
- `ra individual-git-release validation-report`;
- `ra individual-git-release validation-substitutes`;
- `ra individual-git-release fixture-rehearsal`;
- `ra individual-git-release performance`;
- `ra individual-git-release gate-build`;
- `scripts/run_individual_git_release_gate.sh`;
- `docs/workflows/git_sharing_walkthrough.md`.

The final gate currently reports the release as suitable for a limited
individual pilot, but blocked for broad individual/Git-shared release until
real-world validation and release-owner approval are recorded.

## Current Remaining Gaps

The remaining robust-release gaps are:

1. Real fresh-reader onboarding from docs is not recorded.
2. Real macOS validation is not recorded.
3. Real minimal parser-tool environment validation is not recorded.
4. Clean install smoke from the exact current wheel must be run in a fresh
   environment.
5. Representative performance should be extended beyond synthetic Git 100 to
   synthetic Git 1000 and, if available, one sanitized real-small workspace.
6. Final gate should be run from a fresh clean checkout so local ignored state
   cannot influence the release packet.
7. Parser-quality claims must remain conservative and explicitly limited.
8. Release-owner approval for tag creation is missing.
9. Release-owner approval for artifact publication is missing.

## Non-Negotiable Rules

- Do not introduce database, service deployment, SSO/RBAC, hosted UI, or
  real-time collaboration work into this release plan.
- Do not fake colleague, macOS, minimal-machine, tag, or publication approval.
- If a real external validation cannot be performed, record it as blocked or
  pending with a concrete reason.
- Local substitutes may support pilot readiness, but must not satisfy real
  external validation gates.
- Do not commit private PDFs, TeX sources, local corpora, backup archives,
  `.codex`, `.claude`, caches, `build/`, `dist/`, credentials, provider keys,
  tokens, generated workspaces, or private local paths.
- Generated/parser/benchmark/derivation/traceability/LLM/merge/readiness
  artifacts remain review material, not scientific approval.
- Do not tag or publish artifacts unless the release owner explicitly approves.
- Use `timeout` around validation commands.
- `docs/plans/` is ignored; force-stage this plan and reset memo updates only
  when committing them intentionally.

## Required Audit Before Execution

Before executing, another agent must audit this plan from these perspectives:

- **Product scope:** Confirms the plan remains individual local + Git sharing.
- **Release management:** Confirms evidence, version, artifact, tag, and
  publication decisions are explicit.
- **Privacy/data safety:** Confirms commands and evidence cannot leak private
  papers, private paths, backup archives, credentials, provider keys, or tokens.
- **Research trust:** Confirms the plan never implies mathematical correctness,
  parser accuracy certification, or semantic approval from generated artifacts.
- **Engineering:** Confirms validations are deterministic where local, and
  external validations are clearly separated from local substitutes.

If the audit finds a missing point, update this plan before execution and record
the audit result in `docs/plans/reset_memo_2026-04-26.md`.

### Audit Result For 2026-04-29 Autonomous Execution

Audit completed before execution. The plan is suitable for the individual
local + Git-sharing release target with two execution clarifications:

- This execution is explicitly requested with no human intervention. Therefore
  real fresh-reader onboarding, real macOS validation, real minimal parser-tool
  machine validation, release-owner tag approval, and publication approval must
  be recorded as blocked/manual when unavailable. They must not be fabricated or
  silently waived.
- The clean-install phase must install from an explicit wheel path, not merely
  "latest wheel in `dist/`". If the smoke script lacks this control, add a
  `WHEEL_PATH` override before running the phase.

## Execution Loop

For every phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start and intent.
2. Plan the smallest safe action.
3. Execute locally or record the external blocker honestly.
4. Run focused validation.
5. Audit the result as another developer.
6. Tidy generated outputs and avoid staging private/generated files.
7. Update the reset memo with evidence, blockers, and next step.
8. Commit coherent changes only after validation.

## Phase 1 - Fresh-Reader Onboarding Trial

### Motivation

A robust individual release requires evidence that a new researcher can follow
the docs without knowing project history. Existing docs and commands are
available, but a real fresh-reader trial is not recorded.

### Implementation Instructions

- Recruit one real fresh reader who did not implement the release.
- Have them start from either the wheel or a fresh source checkout.
- They must follow:
  - `docs/installation.md`;
  - `docs/quickstart.md`;
  - `docs/workflows/git_sharing_walkthrough.md`;
  - `docs/onboarding_trial.md`.
- Required commands:

```bash
ra --help
ra version
ra --root /tmp/research-assistant-onboarding init
ra --root /tmp/research-assistant-onboarding doctor --matrix
ra --root /tmp/research-assistant-onboarding demo setup
ra --root /tmp/research-assistant-onboarding demo run
ra --root /tmp/research-assistant-onboarding release-report
ra --root /tmp/research-assistant-onboarding repository-hygiene check --strict
ra --root /tmp/research-assistant-onboarding backup create
ra --root /tmp/research-assistant-restore-check backup restore --path <backup-path>
```

- Record sanitized evidence:

```bash
ra --root /tmp/research-assistant-onboarding individual-git-release validation-record \
  --validation-type colleague_onboarding \
  --result passed \
  --scope real_external \
  --platform "<platform>" \
  --python-version "<python version>" \
  --install-method "<wheel or source checkout>" \
  --command-summary "fresh reader completed install/init/demo/report/hygiene/backup-restore"
```

- If no reader is available, record:

```bash
ra individual-git-release validation-record \
  --validation-type colleague_onboarding \
  --result blocked \
  --scope real_external \
  --platform "external colleague machine" \
  --python-version "unknown" \
  --install-method "unknown" \
  --command-summary "fresh reader onboarding unavailable" \
  --blocker "manual_colleague_onboarding_not_completed"
```

### Tests

- `ra individual-git-release validation-report` includes a
  `colleague_onboarding` record.
- Gate remains blocked if the record is `blocked`.
- No private titles, paths, or paper content are present in the evidence.

### Acceptance Criteria

- A fresh reader either passes onboarding with sanitized evidence, or the release
  remains explicitly blocked for this item.

## Phase 2 - macOS Validation

### Motivation

The individual release is intended to support macOS as a target platform, but
the current evidence is Linux/WSL-local. A robust release needs real macOS
validation or an honest platform limitation.

### Implementation Instructions

- On a real macOS machine with Python 3.10 or newer, run:

```bash
python -m pip install research_assistant-0.1.0-py3-none-any.whl
ra version
ra --root /tmp/research-assistant-macos init
ra --root /tmp/research-assistant-macos doctor --matrix
ra --root /tmp/research-assistant-macos demo setup
ra --root /tmp/research-assistant-macos demo run
ra --root /tmp/research-assistant-macos release-report
ra --root /tmp/research-assistant-macos repository-hygiene check --strict
```

- Record sanitized evidence:

```bash
ra --root /tmp/research-assistant-macos individual-git-release validation-record \
  --validation-type macos \
  --result passed \
  --scope external_machine \
  --platform "macOS <version>" \
  --python-version "<python version>" \
  --install-method "wheel" \
  --command-summary "macOS wheel install and demo/release/hygiene smoke passed"
```

- If macOS is unavailable, record `result blocked` with
  `manual_macos_validation_not_completed`.

### Tests

- Validation report distinguishes real `scope: external_machine` from local
  substitutes.
- Gate remains blocked for broad release when macOS is blocked or missing.

### Acceptance Criteria

- macOS support is either validated with real evidence or clearly excluded from
  robust release claims.

## Phase 3 - Real Minimal Parser-Tool Environment

### Motivation

Local substitutes show parser-tool degradation behavior, but a robust release
needs a real minimal environment where optional parser tools are absent or only
`pdftotext` is present.

### Implementation Instructions

- Create a fresh machine, container, virtual machine, or clean environment with
  no optional parser tools except the minimum intentionally installed tools.
- Run:

```bash
ra --root /tmp/research-assistant-minimal init
ra --root /tmp/research-assistant-minimal doctor --matrix
ra --root /tmp/research-assistant-minimal parser-tool-matrix
ra --root /tmp/research-assistant-minimal parser-benchmark-smoke
ra --root /tmp/research-assistant-minimal demo setup
ra --root /tmp/research-assistant-minimal demo run
```

- Verify core local lifecycle and demo workflows pass even when parser-rich
  workflows warn or block.
- Record:

```bash
ra --root /tmp/research-assistant-minimal individual-git-release validation-record \
  --validation-type minimal_parser_tools \
  --result passed \
  --scope external_machine \
  --platform "<minimal environment platform>" \
  --python-version "<python version>" \
  --install-method "<wheel or source checkout>" \
  --command-summary "minimal parser-tool environment completed doctor/matrix/benchmark/demo"
```

- If unavailable, record blocked evidence and keep parser claims conservative.

### Tests

- Existing missing-tool simulation tests remain green.
- Validation report shows whether minimal parser-tool evidence is real or a
  local substitute.

### Acceptance Criteria

- The release can honestly state what works when optional parser tools are
  missing.

## Phase 4 - Clean Install From Exact Artifact

### Motivation

The current wheel was built locally, but a robust release requires clean-install
smoke from the exact artifact intended for release.

### Implementation Instructions

- Build artifacts:

```bash
timeout 300 scripts/build_release_artifacts.sh
ra release-artifacts manifest
```

- Capture the SHA256 from `dist/release_artifacts_manifest.json`.
- Run clean install smoke from that exact wheel in a fresh environment:

```bash
WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl \
timeout 300 scripts/run_clean_install_smoke.sh
```

- If the existing script does not accept `WHEEL_PATH`, update it so the artifact
  path is explicit and recorded.
- Record validation evidence with `validation_type linux_wsl` or the relevant
  platform type only after the installed artifact, not the source tree, passes.
- Update `docs/release_notes_0.1.0.md` with the exact artifact hash.

### Tests

- `ra version` works after clean install.
- `ra --root <fresh> init`, `doctor`, `demo setup`, `demo run`, and
  `release-report` work after clean install.
- Release notes hash matches the manifest.

### Acceptance Criteria

- The release packet proves the exact artifact can be installed and used from a
  clean environment.

## Phase 5 - Representative Performance Expansion

### Motivation

Synthetic Git 100 has passed. Robust release confidence needs a larger
individual-size synthetic workspace and, if available, one sanitized real-small
workspace.

### Implementation Instructions

- Run:

```bash
timeout 600 ra --root /tmp/research-assistant-perf-1000 individual-git-release performance \
  --tier synthetic_git_1000 \
  --synthetic-count 1000 \
  --timeout-seconds 600
```

- Record:
  - elapsed seconds;
  - source/target file counts;
  - merge dry-run counts;
  - merge apply counts;
  - rebuild status;
  - backup size;
  - warnings/blockers.
- If a sanitized real-small workspace exists, run:

```bash
ra --root <sanitized-workspace> repository-hygiene check --strict
ra --root <sanitized-workspace> individual-git-release performance \
  --tier sanitized_real_small \
  --synthetic-count <small-safe-count>
```

- Do not use private papers or real private paths in committed evidence.
- Update release notes with tested size and limitations.

### Tests

- Performance command completes within timeout on `synthetic_git_1000`.
- Validation report records `representative_workspace_performance`.
- Gate reflects performance evidence.

### Acceptance Criteria

- Release notes can state the largest tested Git-sharing workspace tier without
  overstating real-world scalability.

## Phase 6 - Fresh Clean Checkout Gate

### Motivation

The final release decision should not depend on a long-lived dirty working tree
with local caches, ignored build artifacts, or scratch files.

### Implementation Instructions

- Create a clean local clone or worktree from the release commit.
- Do not copy `.codex`, `.claude`, caches, `build/`, `dist/`, or local
  workspaces into the checkout.
- In the clean checkout, run:

```bash
timeout 300 scripts/run_individual_git_release_gate.sh
git status --short --ignored
```

- Verify the script completes and the gate status is:
  - `blocked` only for missing real external validation or release-owner
    approval; or
  - `passed` only if all real validations and approvals exist.
- Record the clean checkout commit SHA and command results in the reset memo.

### Tests

- The clean checkout has no unexpected tracked modifications.
- Ignored generated outputs are not committed.
- Final gate result matches the validation evidence.

### Acceptance Criteria

- A release owner can reproduce the local gate packet from a clean checkout.

## Phase 7 - Parser Claim Calibration

### Motivation

Parser availability and fixture smoke are covered, but parser scientific
accuracy is not certified. The release must not imply more than the evidence
supports.

### Implementation Instructions

- Re-read:
  - `docs/known_limitations.md`;
  - `docs/release_notes_0.1.0.md`;
  - `docs/platform_support.md`;
  - `docs/support.md`;
  - `docs/workflows/git_sharing_walkthrough.md`.
- Confirm they state:
  - parser availability/degradation is checked;
  - parser benchmark smoke is fixture-only;
  - parser scientific accuracy is not certified;
  - users should review parsed evidence before relying on it.
- If wording is too strong, revise it.
- Add a docs smoke test if needed to assert the limitation phrase remains
  present.

### Tests

- `PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q`
- `git diff --check`

### Acceptance Criteria

- Parser claims are conservative and backed by evidence.

## Phase 8 - Release Owner Go/No-Go Approval

### Motivation

The code can be ready while publication is still unauthorized. Tagging and
publishing must be explicit release-owner decisions.

### Implementation Instructions

- Assemble the go/no-go packet:
  - final commit SHA;
  - release artifact manifest and hashes;
  - validation report;
  - final gate output;
  - clean checkout status;
  - release notes;
  - remaining limitations.
- Ask the release owner explicitly for:
  - tag approval;
  - artifact publication approval.
- If approved, record:

```bash
ra individual-git-release validation-record \
  --validation-type release_owner_tag_approval \
  --result passed \
  --scope release_owner \
  --platform "manual approval" \
  --python-version "not applicable" \
  --install-method "not applicable" \
  --command-summary "release owner approved tag creation for <version>"

ra individual-git-release validation-record \
  --validation-type publication_approval \
  --result passed \
  --scope release_owner \
  --platform "manual approval" \
  --python-version "not applicable" \
  --install-method "not applicable" \
  --command-summary "release owner approved artifact publication for <version>"
```

- If not approved, record blocked evidence and do not tag or publish.
- Only after explicit approval:

```bash
git tag -a v0.1.0 -m "research-assistant 0.1.0"
```

- Publish artifacts only through the approved release channel.

### Tests

- Gate blocks when approval is missing.
- Gate can pass only when all required real validations and approvals exist.
- No tag exists unless explicit approval was recorded first.

### Acceptance Criteria

- The final release action is auditable and authorized.

## Phase 9 - Final Documentation And Reset Memo

### Motivation

After real validation and approval decisions, the release packet must be easy to
audit later.

### Implementation Instructions

- Update:
  - `docs/release_notes_0.1.0.md`;
  - `docs/platform_support.md`;
  - `docs/known_limitations.md`;
  - `docs/release_checklist.md`;
  - `docs/plans/reset_memo_2026-04-26.md`.
- Include:
  - exact artifact hash;
  - platforms validated;
  - clean install result;
  - fresh-reader outcome;
  - minimal parser-tool outcome;
  - performance tier;
  - final gate status;
  - approval/tag/publication decision.
- Run:

```bash
git diff --check
git status --short --ignored
```

### Tests

- Docs smoke tests remain green.
- Release notes and validation evidence agree.

### Acceptance Criteria

- Another maintainer can determine exactly why the release is ready, blocked, or
  intentionally pilot-only.

## Final Definition Of Done

The robust individual-user release is ready only when:

- fresh-reader onboarding is recorded from a real external user;
- macOS validation is recorded or macOS is explicitly excluded;
- real minimal parser-tool validation is recorded or the limitation is explicit;
- clean install from the exact artifact passes;
- synthetic Git 1000 performance passes or a concrete smaller limit is stated;
- optional sanitized real-small performance evidence is recorded if available;
- clean checkout gate is reproducible;
- parser claims remain conservative;
- release notes match artifact hashes and validation evidence;
- release-owner tag and publication approvals are explicit;
- final gate has no current-target blockers.

If any real validation or approval is unavailable, keep the release as a limited
individual pilot and document the exact blocker.
