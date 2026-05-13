# Local MCP Remaining Gap Closure Plan - 2026-05-02

## Purpose

This plan closes the remaining local MCP gaps after commit
`7043acc Validate local MCP expansion gates`.

The prior pass produced a safe local MCP foundation and conservative gates. The
remaining work is to make those gates operationally visible, add deterministic
offline scaffolding where possible, and clearly separate locally closable gaps
from evidence that requires a real colleague or an explicitly approved live
network run.

## Remaining Gaps

The known gaps are:

1. Real colleague MCP setup is not yet externally validated.
2. Live arXiv source intake at 25/50/100 papers is not yet measured.
3. Query-based arXiv discovery is design-only.
4. PDF batch intake is design-only.
5. Review-write is CLI-only and not ready for MCP exposure.
6. `ra release-report` does not yet surface the query/PDF/review-write gate
   details explicitly.
7. Release artifacts were not rebuilt after the latest MCP gap work.
8. `.codex` remains untracked local scratch.

## Non-Negotiable Rules

- Keep MCP local stdio.
- Do not add HTTP MCP, hosted deployment, shared database, SSO/RBAC, or
  production monitoring.
- Do not expose review mutation through MCP in this plan.
- Do not expose PDF batch execution through MCP in this plan.
- Do not make live provider/LLM calls part of default validation.
- Do not treat mocked tests or local surrogate trials as real external
  validation.
- Do not commit raw PDFs, downloaded corpora, source archives, extracted full
  text, local grants, audit logs, batch manifests, `dist/`, `build/`, `.codex`,
  or private colleague metadata.
- Use `timeout` for validation commands.
- `docs/plans/` is ignored; force-stage only this plan and the reset memo if
  committing.

## Scope Decision

This pass can close implementation/readiness gaps:

- make release-report expose explicit local MCP gate statuses;
- create a non-private colleague trial recording template;
- create an offline query-candidate fixture path and plan-hash binding;
- create PDF batch policy helpers/tests without enabling PDF execution;
- harden CLI review-write readiness without MCP exposure;
- rebuild local release artifacts as ignored generated outputs;
- ignore `.codex` scratch.

This pass cannot honestly close external evidence gaps:

- real colleague MCP setup requires a real colleague;
- live arXiv 25/50/100 reliability requires explicit live network approval and
  bounded execution.

Those must remain manual validation items unless the user separately approves a
bounded live run and provides or arranges colleague participation.

## Required Audit Before Execution

Before implementation, audit this plan as another developer:

- **Scope:** Does any phase drift into hosted/shared MCP or platform work?
- **Evidence:** Does any phase overclaim local surrogate or mocked evidence?
- **Privacy:** Could trial templates or reports leak private papers, local
  paths, credentials, or colleague identity?
- **Permissions:** Could query/PDF/review-write code create unbounded writes or
  mutate review status without explicit confirmation?
- **Network:** Could deterministic tests perform live network calls?
- **Packaging:** Could generated release artifacts or local scratch be staged?

Patch this plan before execution if the audit finds issues.

## Execution Loop

For each phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start, intent, and
   risk.
2. Plan the smallest safe change.
3. Execute the change.
4. Run focused tests with `timeout`.
5. Audit as another developer.
6. Tidy generated outputs.
7. Update the reset memo with results, interpretation, and next-phase
   justification.
8. Continue automatically unless the next phase is no longer justified.

## Phase 0 - Baseline And Plan Audit

### Motivation

Confirm the repo is clean enough to modify and that this plan does not turn
local MCP into a broader platform project.

### Implementation Instructions

- Record current branch state and recent commits.
- Run:

```bash
timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py -q
git diff --check
```

- Audit this plan against the Required Audit checklist.
- Patch this plan if needed before continuing.

### Acceptance Criteria

- Baseline is green.
- Plan explicitly separates local closable gaps from external/live evidence.
- Next phase is justified only if no hosted/shared MCP drift is introduced.

## Phase 1 - Release-Report MCP Gate Surfacing

### Motivation

The release report currently says MCP is optional, local stdio, and read-only by
default. It should also report the state of the specific remaining gates so a
fresh reader can see what is implemented, disabled, or manual.

### Implementation Instructions

- Extend `mcp_readiness_status(...)` with a deterministic `gate_status` object.
- Treat `gate_status` as a living readiness surface during this plan: Phase 1
  adds the explicit structure, and later phases may update individual gate
  values after query-candidate planning, PDF policy checks, or review-write
  status hardening land.
- Include:
  - colleague MCP trial: manual/external required;
  - explicit-ID source batch: available with grant, mocked 25-paper local scale
    evidence, live scale pending;
  - query discovery: offline candidate-file planning if implemented in Phase 3,
    live query disabled;
  - PDF batch: policy-check only, execution disabled;
  - review-write: CLI-only prototype, MCP exposed false;
  - packaging: artifacts are generated/ignored, rebuild command documented.
- Do not make optional MCP absence a base-release blocker.
- Add assertions to `tests/integration/test_individual_release_cli.py`.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q
git diff --check
```

### Acceptance Criteria

- Release report is more explicit without implying hosted/shared MCP readiness.
- No manual validation item is marked passed.

### Pre-Execution Audit Result - 2026-05-02

Audit performed as another developer before execution.

Findings and corrections:

- **Sequencing:** Phase 1 originally sounded like a one-time final release-report
  update, but query-candidate planning and PDF policy helpers land later. The
  plan now treats `gate_status` as a living readiness surface that later phases
  may update.
- **External evidence:** The plan correctly refuses to mark real colleague MCP
  validation or live arXiv scale as passed.
- **Network control:** All deterministic tests are offline; packaging may need
  local build tooling but should not commit generated artifacts.
- **Permissioning:** Query work is candidate-file planning only, PDF work is
  policy-only, and review-write remains CLI-only.

No blocker was found after this clarification. Phase 1 remains justified.

## Phase 2 - Colleague Trial Evidence Template

### Motivation

A real colleague trial cannot be fabricated by automation, but the project can
make the evidence format safe and ready. A template reduces the chance that the
future record captures private data or overclaims local surrogate evidence.

### Implementation Instructions

- Add `docs/mcp_colleague_trial_record_template.md`.
- The template must include:
  - date;
  - platform;
  - Python version;
  - MCP client;
  - install mode;
  - time-to-first-tool-call;
  - tools exercised;
  - unsafe tools absent;
  - whether batch run was live or skipped;
  - confusion points;
  - docs gaps;
  - pass/narrow/fail outcome.
- The template must prohibit:
  - private paper titles;
  - raw PDFs;
  - extracted text;
  - credentials;
  - colleague names unless they explicitly opt in.
- Link it from `docs/mcp_trial_checklist.md` and release notes/limitations as
  appropriate.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Future H1 evidence can be recorded safely.
- H1 remains manual/external until a real trial record exists.

## Phase 3 - Offline Query Candidate File Planning

### Motivation

Query discovery is useful only if the candidate list is pinned before grants.
The safest next step is not live query. It is support for planning from a saved
candidate file, plus deterministic tests proving that the exact candidate list
changes the plan hash.

### Implementation Instructions

- Add helpers to load and validate a candidate file with:
  - schema version;
  - query;
  - normalized query;
  - candidate batch ID;
  - ordered candidates with arXiv IDs.
- Extend `plan_arxiv_batch_intake(...)` and `ra arxiv-batch plan` with an
  optional `--candidate-file`.
- Planning from a candidate file must:
  - not perform network calls;
  - use the candidate file's exact ordered arXiv IDs;
  - include candidate-file identity/checksum and ordered IDs in the plan hash;
  - remain read-only;
  - reject malformed, oversized, or missing-ID files;
  - still block query-only live discovery.
- Add a non-private fixture under `tests/fixtures/mcp/arxiv_candidates/`.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H3 moves from design-only to offline pinned-candidate planning.
- Live query discovery remains disabled.

## Phase 4 - PDF Batch Policy Helpers

### Motivation

PDF batch execution should remain disabled, but policy checks can be made
executable and testable now. This closes part of H4 without downloading PDFs.

### Implementation Instructions

- Add policy helper module for PDF batch intake limits.
- Validate:
  - max file count;
  - max total bytes;
  - per-file byte limit;
  - destination is inbox only;
  - overwrite policy is `no_overwrite`;
  - allowed domains are arXiv-only for now;
  - candidate count does not exceed grant/policy limits.
- Add CLI/status or release-report surfacing only if useful and deterministic.
- Do not implement PDF download execution.
- Add focused tests.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H4 has executable policy checks.
- No PDF download MCP or CLI execution path is enabled.

## Phase 5 - Review-Write Readiness Hardening

### Motivation

The CLI prototype has proposal/apply/conflict behavior. Before considering MCP
exposure later, reviewers need better status visibility and cleanup for expired
proposals.

### Implementation Instructions

- Add CLI-visible review-write readiness details:
  - pending proposal count;
  - expired proposal count;
  - applied proposal count;
  - supported operations;
  - MCP exposed false.
- Add a cleanup/dry-run command for expired proposals if low risk:
  - default dry-run;
  - real cleanup requires explicit flag;
  - only removes expired proposal records, not summary/review data.
- Add tests for invalid expiry, repeated proposal uniqueness, status counts,
  and cleanup dry-run behavior.
- Do not expose MCP review mutation.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_cli_commands.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H5 is safer for later UX review.
- MCP review mutation remains disabled.

## Phase 6 - Packaging, Scratch Hygiene, And Docs

### Motivation

The latest local MCP work should be represented in local release artifacts, but
generated artifacts should remain ignored. The untracked `.codex` scratch should
also stop appearing as a committable unknown.

### Implementation Instructions

- Add `.codex/` to `.gitignore`.
- Run packaging smoke:

```bash
timeout 300 scripts/run_packaging_smoke.sh
timeout 300 scripts/build_release_artifacts.sh
```

- Do not stage `dist/` or `build/`.
- Update docs if needed:
  - `docs/mcp.md`;
  - `docs/known_limitations.md`;
  - `docs/release_notes_0.1.0.md`;
  - `docs/troubleshooting.md`.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git status --short --ignored
git diff --check
```

### Acceptance Criteria

- Packaging commands complete or any network/build blocker is recorded.
- Generated artifacts remain uncommitted.
- `.codex` is ignored.
- Docs match current capabilities.

## Final Definition Of Done

This plan is complete when:

- release-report exposes the MCP gate statuses;
- H1 has a safe evidence template and remains manual until a real trial exists;
- H2 live scale remains manual unless separately approved, while local evidence
  is clearly reported;
- H3 supports offline pinned-candidate planning and keeps live query disabled;
- H4 has executable PDF policy checks and keeps download execution disabled;
- H5 has stronger CLI readiness/cleanup and keeps MCP mutation disabled;
- packaging/scratch hygiene are updated;
- all tests pass;
- no private/generated artifacts are committed.
