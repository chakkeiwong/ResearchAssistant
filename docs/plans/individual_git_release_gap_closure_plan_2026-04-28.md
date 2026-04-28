# Individual Git Release Gap Closure Plan - 2026-04-28

## Purpose

This plan closes the remaining release gaps after the product target was
reframed as an industrial-quality **individual local tool** with Git-based
sharing.

The current release should not be blocked by production databases, shared
services, SSO/RBAC, real-time collaboration, or department deployment. Those are
future multi-user platform concerns. The release should instead prove that one
researcher can use the tool locally and that researchers can share work by
checking out or importing each other's Git repositories safely.

Primary target document:

- `docs/proposal/individual_git_release_target.md`

## Current Baseline

Recent relevant commits:

- `ddd2219 Add industrial release gate contracts`
- `970085a Record industrial release gate checkpoint`

Current strengths:

- local workspace lifecycle commands exist;
- individual release-report and release scripts exist;
- industrial release gate exists but still reflects a multi-user/deployment
  model;
- local artifact schemas carry provenance, review status, and limitations;
- generated artifacts are kept separate from accepted review conclusions;
- backup/restore, parser-tool diagnostics, performance smoke, and packaging
  smoke exist.

Current mismatch:

- industrial release docs and gates still treat production storage, service
  deployment, identity/RBAC, UI deployment, and department SOPs as primary
  blockers;
- the new release target is individual use with Git checkout/import sharing;
- there is no domain-aware workspace merge/import tool yet.

## Non-Negotiable Rules

- Keep the release scoped to individual local use.
- Do not introduce a database, server, SSO/RBAC, live collaboration, or
  production deployment requirement.
- Preserve the trust boundary: generated, parser, benchmark, derivation,
  traceability, LLM, and readiness artifacts are review material.
- Do not commit private papers, local corpora, backup archives, credentials,
  provider keys, `.codex`, `.claude`, caches, `build/`, `dist/`, or generated
  local workspaces.
- All merge/import behavior must default to dry-run or explicit confirmation.
- Never silently overwrite accepted human review conclusions.
- Generated indexes, dashboards, caches, and readiness reports should be
  rebuilt after merge, not merged as authoritative source records.
- Use `timeout` for validation scripts.
- Force-stage intentional files under `docs/plans/` because that directory is
  ignored.

## Required Audit Before Execution

Before implementing this plan, audit it from four perspectives:

- **Product scope:** Does every phase support the individual/Git-sharing target
  rather than drifting back into multi-user infrastructure?
- **Data safety:** Could any command copy private papers, local paths, backup
  archives, or credentials?
- **Research trust:** Could merge/import silently approve generated or
  conflicting research conclusions?
- **Engineering:** Are file formats stable, deterministic, testable, and
  Git-friendly?

If the audit finds gaps, update this plan first and record the audit in
`docs/plans/reset_memo_2026-04-26.md`.

## Execution Loop

For each phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with the phase start.
2. State the phase goal and concrete files to touch.
3. Add focused tests before or alongside implementation.
4. Implement the smallest safe behavior.
5. Run focused tests with `timeout`.
6. Audit as another developer for privacy leakage, false approval, stale docs,
   and bad merge semantics.
7. Tidy generated outputs and avoid staging private/generated files.
8. Update the reset memo with results and residual risks.
9. Commit coherent phase groups when requested.

## Phase 0 - Align Release Taxonomy With Individual Git Target

### Motivation

The current industrial release gate correctly prevents false production claims,
but it now blocks on the wrong primary goal. The next release target is not
departmental production. It is an individual local tool with Git-based sharing.

### Implementation Instructions

- Update `docs/release/industrial_release_definition.md` or add a new
  release-definition document that makes these levels primary:
  - `limited_individual_pilot`;
  - `broad_individual_release`;
  - `git_shared_research_release`;
  - `future_multi_user_platform`.
- Update `docs/release/industrial_release_gates.json` or add a successor gate
  file so database/service/RBAC/deployment/SOP gates are deferred rather than
  primary blockers.
- Update CLI gate output naming or fields if needed:
  - current target;
  - future target;
  - blockers for current target;
  - deferred multi-user blockers.
- Keep historical industrial docs if useful, but mark them as future-platform
  references.

### Tests

- Test that the release definition reports the individual/Git target.
- Test that production database/service/RBAC gates are not blockers for the
  current individual release target.
- Test that future multi-user gates remain visible as deferred items.

### Acceptance Criteria

- A release manager can see that the current release target is individual local
  use plus Git sharing, not multi-user production.

## Phase 1 - Define Shareable Workspace Contract

### Motivation

Git-based sharing needs a clear boundary between shareable source artifacts and
private/generated local state.

### Implementation Instructions

- Add `docs/workflows/git_sharing_workflow.md`.
- Add a machine-readable shareable workspace policy, for example
  `docs/release/shareable_workspace_policy.json`.
- Classify paths as:
  - shareable source records;
  - optionally shareable review artifacts;
  - rebuildable generated artifacts;
  - private/forbidden artifacts.
- Define metadata required on shareable artifacts:
  - schema version;
  - stable artifact ID;
  - provenance;
  - review status;
  - limitations.
- Document which files should be committed and which files must stay local.

### Tests

- Unit test the policy loader.
- Test representative allowed, skipped, rebuildable, and forbidden paths.

### Acceptance Criteria

- A researcher can know what is safe to commit before sharing a repository.

## Phase 2 - Repository Hygiene Command

### Motivation

Before a researcher shares a Git repository, the tool should detect private or
generated files that should not be committed.

### Implementation Instructions

- Add a command such as:

```bash
ra repository-hygiene check
```

- The command should inspect Git status when `.git` exists.
- It should also walk configured local paths to detect obviously forbidden
  files even before staging.
- Detect:
  - raw papers and source archives;
  - backup archives;
  - credentials and provider-key-like fields;
  - `.codex`, `.claude`, caches, bytecode, `build/`, `dist/`;
  - validation records containing private titles, local paths, or forbidden
    fields.
- Return `ok`, `warnings`, or `blocked`.
- Include remediation instructions.

### Tests

- Fixture repo with safe artifacts.
- Fixture repo with staged forbidden path.
- Fixture workspace with forbidden validation field.
- Fixture workspace with generated index that should be skipped.

### Acceptance Criteria

- A researcher cannot accidentally call a release/shareable repository clean
  when private or generated files are present in unsafe places.

## Phase 3 - Workspace Merge Dry-Run

### Motivation

Git can merge text, but it does not understand research artifacts. A dry-run
merge report is needed before any copying happens.

### Implementation Instructions

- Add command:

```bash
ra workspace merge --source /path/to/source --target /path/to/target --dry-run
```

- `--dry-run` should be the default.
- Validate source and target workspaces.
- Load the shareable workspace policy.
- Classify source files as:
  - copy candidate;
  - already present and identical;
  - conflict;
  - forbidden;
  - rebuildable/skipped;
  - unsupported.
- Compare files by normalized JSON hash where possible.
- Detect conflicts:
  - same relative path, different content;
  - same artifact ID, different content;
  - same paper ID, different summary;
  - accepted `technical_audit` values disagree;
  - same derivation/experiment/traceability artifact edited independently.
- Produce a report under target `local_research/governance/merge_reports/`.

### Tests

- Non-conflicting source artifact appears as copy candidate.
- Identical existing artifact appears as already present.
- Same artifact ID with different content appears as conflict.
- Private/forbidden files are blocked.
- Rebuildable indexes are skipped.
- Accepted audit conflict requires human resolution.

### Acceptance Criteria

- The dry-run report gives a complete, non-destructive explanation of what
  would happen.

## Phase 4 - Workspace Merge Apply Mode

### Motivation

After dry-run, a researcher needs an explicit safe apply path for
non-conflicting artifacts.

### Implementation Instructions

- Extend the command:

```bash
ra workspace merge --source /path/to/source --target /path/to/target --apply --confirm-merge
```

- Require explicit `--apply` and `--confirm-merge`.
- Create a target backup or merge snapshot before copying.
- Copy only non-conflicting shareable artifacts.
- Preserve provenance:
  - source path;
  - source Git commit when available;
  - merge timestamp;
  - merge report ID.
- Do not copy forbidden or rebuildable files.
- Do not overwrite conflicts.
- Write an applied merge report with copied/skipped/conflict counts.

### Tests

- Apply copies only safe new files.
- Apply refuses without confirmation.
- Apply creates backup/snapshot.
- Apply does not overwrite conflicts.
- Imported records include merge provenance.

### Acceptance Criteria

- A researcher can import safe artifacts from another checkout without
  corrupting or overwriting their own workspace.

## Phase 5 - Post-Merge Rebuild And Validation

### Motivation

Generated indexes and readiness reports should be rebuilt after checkout or
merge. They should not be treated as canonical shared state.

### Implementation Instructions

- Add post-merge next actions to merge reports:
  - `ra artifact-index build`;
  - `ra industrial-readiness build` or successor individual/Git readiness
    command;
  - `ra workspace validate`;
  - `ra repository-hygiene check`.
- Optionally add:

```bash
ra workspace rebuild-derived
```

- The rebuild command should run deterministic local rebuilds only.
- Do not call live providers or network by default.

### Tests

- Post-merge report includes next actions.
- Rebuild command regenerates indexes/readiness from source artifacts.
- Rebuild command does not copy private/generated files.

### Acceptance Criteria

- After importing another repository, a researcher has a clear one-command or
  short-command path back to a validated local workspace.

## Phase 6 - Documentation And User Workflow

### Motivation

The Git sharing model will only work if docs are explicit about what users
should and should not commit.

### Implementation Instructions

- Update:
  - `docs/installation.md`;
  - `docs/quickstart.md`;
  - `docs/workflows/individual_research_workflow.md`;
  - `docs/privacy.md`;
  - `docs/known_limitations.md`;
  - `docs/release_checklist.md`;
  - `docs/support.md`;
  - `docs/release_notes_template.md`.
- Add a workflow section:
  - create local workspace;
  - validate repository hygiene;
  - commit shareable artifacts;
  - clone another researcher's repository;
  - run merge dry-run;
  - apply safe imports;
  - rebuild derived artifacts;
  - resolve conflicts manually.
- State that multi-user database/server features are future work.

### Tests

- Docs presence checks if release-report tracks required docs.
- CLI help includes new commands.

### Acceptance Criteria

- A new researcher can follow docs to share and import work through Git without
  needing a database or server.

## Phase 7 - Release Gate Revision

### Motivation

The existing industrial gate is conservative but still oriented toward
multi-user production. The release gate must decide readiness for the current
target.

### Implementation Instructions

- Add or revise a command such as:

```bash
ra individual-git-release gate-build
```

or update `ra industrial-release gate-build` to report:

- current target: `git_shared_research_release`;
- current target blockers;
- future multi-user blockers;
- repository hygiene status;
- merge/import capability status;
- external validation status;
- publication approval status.

- Keep tag/upload manual.
- Keep production database/service/RBAC/UI as deferred, not blockers for the
  current target.

### Tests

- Gate is blocked before merge/import exists.
- Gate is blocked when repository hygiene fails.
- Gate is blocked when publication approval/final validation is missing.
- Gate reports future multi-user items as deferred.

### Acceptance Criteria

- The gate answers: "Can we release the individual Git-sharing tool now?"
  without incorrectly demanding a production database or SSO.

## Phase 8 - External Validation And Release Execution

### Motivation

The new target still needs real validation before release. It just needs the
right validation.

### Implementation Instructions

- Run clean install smoke from release artifact.
- Validate on Linux/WSL and any available additional target platform.
- Run parser-tool missing/degraded environment check.
- Run backup/restore rehearsal.
- Run workspace merge dry-run/apply on sanitized fixture repositories.
- Run representative synthetic corpus performance check.
- Fill release notes with:
  - current target;
  - supported install path;
  - validated platforms;
  - Git sharing workflow;
  - limitations;
  - known parser/tool limits.
- Do not tag or publish without release-owner approval.

### Tests

- Final ordered validation script.
- Release-report or revised gate returns no blockers for the current target.

### Acceptance Criteria

- Release can be honestly published as an individual local tool with Git-based
  sharing, or remains a limited pilot with specific blockers recorded.

## Final Definition Of Done

The release is ready when:

- the proposal document is accepted as the current target;
- release gates no longer treat database/service/RBAC/deployment as current
  blockers;
- repository hygiene catches unsafe files;
- workspace merge dry-run and apply mode are implemented and tested;
- merge reports preserve provenance and trust boundaries;
- generated artifacts can be rebuilt after checkout/import;
- docs explain the Git sharing workflow end to end;
- final validation passes on bounded deterministic tests;
- external validation limitations are recorded honestly;
- tag/publication is explicitly approved.
