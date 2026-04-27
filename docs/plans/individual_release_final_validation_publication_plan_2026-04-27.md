# Individual Release Final Validation And Publication Plan - 2026-04-27

## Purpose

This document is a handoff-ready plan for moving the `research-assistant`
individual local-install release from "pilot-ready release candidate" to an
honest broader colleague release.

The codebase already has the major local release lifecycle in place: install
smoke tests, `ra init`, `ra doctor`, parser/tool matrix reporting, demo
workflow, backup/restore, performance smoke, privacy checks, release artifacts,
release notes, support docs, and `ra release-report`.

The remaining gaps are not large feature gaps. They are release validation and
publication gaps:

- a real colleague has not completed onboarding from the docs;
- macOS has not been validated;
- native Windows remains unsupported, with WSL as the intended Windows path;
- missing optional parser tools have not been tested on a genuinely minimal
  machine;
- only a synthetic medium corpus has been rehearsed;
- the wheel has not been published as a concrete release artifact;
- no release tag has been created.

This plan is written for another agent to audit first, then execute phase by
phase. The agent must not overstate the release. If a validation environment is
unavailable, record that limitation and keep the release scoped as a limited
pilot.

## Current Baseline

Latest known pushed commit:

- `eeb139d Execute colleague rollout release gate`

Important release surfaces:

- `ra version`
- `ra init`
- `ra doctor`
- `ra doctor --matrix`
- `ra parser-tool-matrix`
- `ra parser-benchmark-smoke`
- `ra demo setup`
- `ra demo run`
- `ra backup create`
- `ra backup inspect`
- `ra backup restore`
- `ra privacy status`
- `ra platform-status`
- `ra onboarding-report`
- `ra performance smoke`
- `ra release-artifacts manifest`
- `ra release-report`

Important scripts:

- `scripts/run_fast_tests.sh`
- `scripts/run_bounded_tests.sh`
- `scripts/run_packaging_smoke.sh`
- `scripts/build_release_artifacts.sh`
- `scripts/run_clean_install_smoke.sh`
- `scripts/run_release_smoke.sh`

Important docs:

- `docs/installation.md`
- `docs/quickstart.md`
- `docs/onboarding_trial.md`
- `docs/platform_support.md`
- `docs/known_limitations.md`
- `docs/privacy.md`
- `docs/release_checklist.md`
- `docs/release_notes_0.1.0.md`
- `docs/support.md`
- `.github/ISSUE_TEMPLATE/individual_release_bug.md`

Known local validation from the previous rollout pass:

- Linux/WSL2, `x86_64`, Python `3.11.14` validated.
- Clean install from the built wheel passed in a fresh virtual environment.
- Final source-checkout `ra release-report` returned
  `ready_for_release_candidate_review`.
- Synthetic 1000-record performance smoke passed.
- Demo backup and confirmed restore rehearsal passed.
- Final wheel:
  `research_assistant-0.1.0-py3-none-any.whl`
- Final recorded SHA256:
  `3afb9c23fc19b14e856caf2aba401b7e5d9018233f88198457e8f5aa56cdf2cf`

## Non-Negotiable Release Rules

- This is an individual local-install release, not a shared server release.
- Do not introduce or imply shared database, SSO/RBAC, live collaboration,
  distributed workers, production deployment, or default live LLM/provider use.
- Generated artifacts and parser outputs remain review material. They do not
  certify mathematical correctness.
- Parser matrix and benchmark smoke report availability and fixture readiness,
  not full scientific extraction accuracy.
- Use `timeout` for all scripted validation commands.
- Do not commit private papers, colleague workspaces, backup archives,
  generated local research outputs, `.codex`, caches, `build/`, or `dist/`.
- If real external validation cannot be performed, say so plainly in docs and
  release notes.
- Tag only after final validation and only if explicitly requested by the
  release owner.

## Required Audit Before Execution

Before running the phases, the next agent must audit this plan from a release
manager and data-safety perspective.

Audit questions:

- Does this plan still match the current code and docs?
- Are all remaining gaps validation/publication gaps rather than hidden feature
  gaps?
- Are platform claims limited to machines actually tested?
- Are parser and mathematical claims conservative enough?
- Does every validation command avoid private data by default?
- Are generated artifacts and backup archives kept out of Git?
- Is there a clear path for a pilot release if macOS, minimal parser-tool, or
  real colleague validation is unavailable?
- Is the tag decision separate from the validation decision?

If the audit finds issues, update this plan first, then execute the corrected
plan. Record the audit result in `docs/plans/reset_memo_2026-04-26.md`.

## Audit Amendment - Autonomous Execution Boundary

Independent audit before execution found that the plan is release-manager
complete, but an autonomous local agent cannot honestly complete validations
that require external people or machines. During a no-human-intervention pass:

- Phase 1 can run a local clean-install onboarding substitute, but it cannot
  count as a real colleague trial.
- Phase 2 can validate only the current machine; macOS and native Windows must
  remain unvalidated unless those machines are actually available.
- Phase 3 can add or run deterministic missing-tool simulation, but a separate
  genuinely minimal machine remains stronger evidence.
- Phase 4 can run synthetic or local non-sensitive corpus rehearsal only.
- Phase 8 must be verification-only unless the release owner explicitly
  approves tag creation and artifact publication.

If any external validation remains unavailable, the correct final decision is a
limited pilot release, even if every local command passes.

## Execution Loop

For every phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with the phase start.
2. Run the smallest validation or implementation step needed for the phase.
3. Capture concise outcomes, not full logs.
4. Update docs or tests only when the phase exposes a real gap.
5. Audit the result as a different developer.
6. Confirm no private or generated artifacts are staged.
7. Update the reset memo with tests, platform, residual risks, and next step.
8. Commit coherent docs/code changes only after a phase or tight phase group.

Because `docs/plans/` is ignored, force-stage intentional plan and reset memo
changes with `git add -f`.

## Phase 1 - Real Colleague Onboarding Trial

### Motivation

Automated clean-install smoke proves that the package can install and execute
the demo in a controlled environment. It does not prove that a colleague can
follow the docs without project history. A real onboarding trial catches missing
prerequisites, confusing install wording, unclear workspace paths, misleading
release-report language, and privacy/support instructions that are too vague.

### Implementation Instructions

- Select one trial user who did not implement the release hardening.
- Give the user only:
  - `docs/installation.md`;
  - `docs/quickstart.md`;
  - `docs/onboarding_trial.md`;
  - `docs/privacy.md`;
  - `docs/support.md`;
  - the release wheel or checkout path chosen for the trial.
- Ask the user to use a disposable workspace outside the repo.
- Ask the user to run:

```bash
ra --help
ra version
ra --root <trial-workspace> init
ra --root <trial-workspace> doctor
ra --root <trial-workspace> doctor --matrix
ra --root <trial-workspace> demo setup
ra --root <trial-workspace> demo run
ra --root <trial-workspace> release-report
ra --root <trial-workspace> backup create
ra --root <trial-workspace> backup inspect --path <backup-path>
ra --root <trial-workspace> privacy status
ra onboarding-report
```

- Record only non-private trial metadata:
  - platform and architecture;
  - Python version;
  - install method;
  - time to install;
  - time to complete demo;
  - optional parser tools reported available or missing;
  - command failures;
  - confusing docs;
  - suggested support/documentation improvements.
- Do not collect private PDFs, workspace contents, backup archives, provider
  keys, shell history, or full logs containing local paths unless the user
  explicitly sanitizes them.
- If the trial exposes documentation confusion, update docs immediately.
- If the trial exposes command failure, add a focused regression test before
  fixing code.

### Validation Commands

Run locally after any doc or code change:

```bash
timeout 120 scripts/run_clean_install_smoke.sh
timeout 120 scripts/run_release_smoke.sh
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- A fresh reader completes install, init, doctor, demo, backup inspect, privacy
  status, and release-report using docs only.
- Any confusion is fixed or recorded in `docs/known_limitations.md`.
- Reset memo records non-private trial metadata and whether the release remains
  pilot-only or can broaden.

## Phase 2 - Platform Validation And Support Matrix

### Motivation

The current validated platform is Linux/WSL2. Colleagues may use Linux, macOS,
or Windows through WSL. The release must state only what has actually been
validated. Unsupported or unvalidated platforms should be explicit so colleagues
do not mistake an optimistic install note for a support promise.

### Implementation Instructions

- Use `docs/platform_support.md` as the source of truth.
- On every available platform, run from a clean checkout or release artifact:

```bash
ra platform-status
timeout 180 scripts/run_clean_install_smoke.sh
timeout 180 scripts/run_release_smoke.sh
timeout 180 scripts/run_packaging_smoke.sh
```

- Minimum target for broader release:
  - Linux/WSL2 validation remains passing;
  - macOS is either validated or explicitly listed as unvalidated;
  - native Windows is explicitly unsupported unless a real native Windows pass
    is completed.
- Record:
  - OS name and version;
  - architecture;
  - Python version;
  - shell availability;
  - install method;
  - command outcomes;
  - warnings or blockers.
- If macOS needs special installation notes, update `docs/installation.md`.
- If a platform fails, do not patch around it blindly. First classify the issue:
  documentation, packaging, shell-script portability, dependency availability,
  or unsupported platform.

### Validation Commands

After platform doc updates:

```bash
timeout 60 python -m pytest tests/integration/test_individual_release_cli.py::test_project_metadata_exposes_ra_entrypoint -q
ra release-report
```

### Acceptance Criteria

- `docs/platform_support.md` lists tested platforms with dates and results.
- Untested platforms are not implied to be supported.
- Release notes and install docs match the platform support matrix.

## Phase 3 - Minimal Optional Parser-Tool Environment Trial

### Motivation

The previous validation machine had optional parser tools available. Many
colleagues will not. The release must prove that core local workflows remain
usable without optional parser tools and that parser/PDF workflows degrade with
clear messages rather than stack traces.

### Implementation Instructions

- Prefer a real clean environment without optional parser tools installed.
- If a real environment is unavailable, create a controlled test mode or
  monkeypatch-based regression test that simulates missing tools through the
  existing tool-detection layer.
- Run:

```bash
ra --root <tmp-workspace> init
ra --root <tmp-workspace> doctor
ra --root <tmp-workspace> doctor --matrix
ra parser-tool-matrix
ra parser-benchmark-smoke
ra --root <tmp-workspace> demo setup
ra --root <tmp-workspace> demo run
ra --root <tmp-workspace> release-report
```

- Verify:
  - `core_local_lifecycle` remains `ok`;
  - `demo_workflow` remains `ok`;
  - missing PDF/parser tools are reported as `warnings` or `blocked` only for
    the workflows that need them;
  - parser benchmark smoke remains fixture-only and offline;
  - suggested fixes are actionable.
- Update `docs/troubleshooting.md` with observed missing-tool messages.
- Update `docs/known_limitations.md` if missing tools create surprising limits.

### Validation Commands

```bash
timeout 120 scripts/run_fast_tests.sh
timeout 120 scripts/run_bounded_tests.sh
```

### Acceptance Criteria

- Missing optional tools do not block init, config, demo, backup, privacy, or
  release-report.
- Parser limitations are visible and actionable.
- Deterministic tests cover missing-tool behavior if no real minimal machine is
  available.

## Phase 4 - Real Or Representative Personal Corpus Rehearsal

### Motivation

The synthetic 1000-record performance smoke passed, which is useful. It still
does not prove behavior on real personal libraries: filenames, metadata
variation, malformed records, old artifacts, large PDFs, and user-created notes
can expose different failure modes. A release should be honest about the corpus
size and shape actually rehearsed.

### Implementation Instructions

- Prefer a non-sensitive real or representative corpus.
- If using a real corpus:
  - do not commit it;
  - do not copy it into the repo;
  - do not share private titles, PDFs, annotations, backup archives, or full
    paths in public docs;
  - record only aggregate metadata.
- Run:

```bash
ra --root <corpus-root> workspace validate
ra --root <corpus-root> release-report
ra --root <corpus-root> backup create
```

- If no real corpus is available, rerun a bounded synthetic rehearsal and state
  that it remains synthetic:

```bash
ra --root /tmp/ra-perf-1000 performance smoke \
  --synthetic-count 1000 \
  --include-industrial-artifacts \
  --include-export \
  --include-backup \
  --timeout-seconds 600
```

- Record:
  - corpus type: real non-sensitive, sanitized, or synthetic;
  - record count;
  - workspace validation time;
  - artifact index time, if reported;
  - export time, if run;
  - backup time;
  - backup size;
  - warnings and blockers.
- If performance is uncomfortable, reduce the supported claim and update
  `docs/known_limitations.md`.

### Validation Commands

After any code change:

```bash
timeout 120 scripts/run_fast_tests.sh
timeout 180 scripts/run_bounded_tests.sh
```

### Acceptance Criteria

- At least one representative corpus rehearsal is recorded.
- Release notes distinguish synthetic validation from real-corpus validation.
- No private corpus data or generated backup artifacts are staged.

## Phase 5 - Release Artifact Publication Path

### Motivation

The wheel can be built locally, but colleagues need one concrete artifact and
one recommended install path. A release is confusing if users must infer whether
to install from a Git checkout, a wheel, pipx, or another packaging channel.

### Implementation Instructions

- Rebuild artifacts from a clean worktree:

```bash
timeout 180 scripts/build_release_artifacts.sh
ra release-artifacts manifest
```

- Confirm the manifest includes SHA256 hashes.
- Choose and document the primary install path:
  - recommended default: wheel attached to a GitHub release;
  - fallback: source checkout for contributors/developers;
  - optional: `pipx install <wheel>` only if actually tested.
- Update `docs/installation.md`, `docs/release_notes_0.1.0.md`, and
  `docs/release_checklist.md` with the chosen publication path and hash.
- Do not commit `dist/` or `build/` unless the project explicitly changes its
  release policy.
- If publishing to GitHub is desired, prepare the release notes and artifact
  list but do not upload or publish without explicit release-owner approval.

### Validation Commands

```bash
timeout 180 scripts/run_clean_install_smoke.sh
ra version
ra --root /tmp/ra-artifact-final-check init
ra --root /tmp/ra-artifact-final-check demo setup
ra --root /tmp/ra-artifact-final-check demo run
ra --root /tmp/ra-artifact-final-check release-report
```

### Acceptance Criteria

- One primary install path is documented.
- Wheel hash in docs matches the manifest.
- Clean install works from the chosen artifact path outside editable mode.

## Phase 6 - Release Notes, Support Boundary, And Pilot Decision

### Motivation

The release notes and support docs are part of the product. Colleagues need to
know what the tool does, what it does not do, what outputs are safe to share,
and whether the current release is a pilot or a broader release.

### Implementation Instructions

- Review:
  - `docs/release_notes_0.1.0.md`;
  - `docs/known_limitations.md`;
  - `docs/support.md`;
  - `.github/ISSUE_TEMPLATE/individual_release_bug.md`;
  - `docs/privacy.md`.
- Ensure release notes include:
  - version;
  - date;
  - artifact name and SHA256;
  - supported platforms;
  - unvalidated platforms;
  - validation command summaries;
  - privacy statement;
  - parser limitation statement;
  - backup/restore warning;
  - pilot versus broader release decision.
- Ensure support docs tell users not to share:
  - private PDFs;
  - `local_research/`;
  - backup archives;
  - provider keys;
  - `.codex`;
  - unsanitized logs or local paths.
- If real colleague, platform, or minimal parser-tool validation remains
  incomplete, mark the release as a limited pilot.

### Validation Commands

```bash
ra release-report
timeout 120 scripts/run_release_smoke.sh
```

### Acceptance Criteria

- Release notes and support docs match actual validation.
- The release decision is explicit: limited pilot or broader colleague release.
- Privacy and support boundaries are clear.

## Phase 7 - Final Release Gate

### Motivation

Before publishing or tagging, run one final ordered gate so the release decision
is based on fresh evidence instead of stale phase results.

### Implementation Instructions

Run in order from a clean worktree:

```bash
timeout 120 scripts/run_fast_tests.sh
timeout 180 scripts/run_bounded_tests.sh
timeout 180 scripts/run_packaging_smoke.sh
timeout 180 scripts/build_release_artifacts.sh
timeout 240 scripts/run_clean_install_smoke.sh
timeout 180 scripts/run_release_smoke.sh
ra --root /tmp/research-assistant-final-release init
ra --root /tmp/research-assistant-final-release release-report
git status --short --ignored
```

Then inspect:

- `ra release-report` has no unexpected blockers.
- Any warnings are either fixed or reflected in release notes.
- docs match the chosen install path and platform matrix.
- generated outputs under `build/`, `dist/`, `.pytest_cache/`, local
  workspaces, and backup archives are not staged.
- `docs/plans/reset_memo_2026-04-26.md` has the final validation summary.

### Acceptance Criteria

- Final gate passes.
- Reset memo records release decision and exact validations.
- Worktree contains only intentional docs/code changes plus ignored generated
  outputs.
- Commit all intentional changes.
- Push `main` only if requested or already authorized by release process.
- Create and push a tag only if explicitly requested.

## Phase 8 - Optional Tag And Publication

### Motivation

Tagging and publishing are irreversible enough to deserve a separate phase. They
should happen only after the release owner accepts the final validation record
and the pilot/broader-release decision.

### Implementation Instructions

- Confirm the chosen version:

```bash
ra version
```

- Confirm the release notes filename and contents.
- Confirm the final artifact manifest and SHA256.
- If the release owner approves tagging:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
```

- Push the tag only after approval:

```bash
git push origin v0.1.0
```

- If publishing a GitHub release, attach:
  - the wheel;
  - the release artifact manifest;
  - the release notes;
  - any required checksum text.
- Do not attach private test workspaces, backups, logs, or local corpus data.

### Acceptance Criteria

- Tag exists only after explicit approval.
- Published artifact hash matches release notes.
- Release page repeats the local/private, parser-limited, human-review boundary.

## Final Release Decision Template

Use this template in the reset memo after Phase 7 or Phase 8:

```text
Release decision:
- Version:
- Decision: limited pilot / broader colleague release / blocked
- Commit:
- Tag:
- Artifact:
- SHA256:
- Platforms validated:
- Python versions validated:
- Real colleague onboarding:
- Minimal parser-tool environment:
- Corpus rehearsal:
- Final validation commands:
- Remaining limitations:
- Next action:
```

## Definition Of Done

The release can move beyond pilot only when:

- at least one fresh colleague onboarding trial succeeds;
- supported platforms are explicit and tested;
- untested platforms are clearly marked;
- missing optional parser-tool behavior is tested or simulated with regression
  coverage;
- a representative corpus rehearsal is recorded honestly;
- artifact publication path and SHA256 are documented;
- release notes and support docs protect private research data;
- final release gate passes from a clean worktree;
- release owner explicitly decides whether to tag and publish.

If any of the first five items remain incomplete, the correct outcome is a
limited pilot release, not a broad colleague release.
