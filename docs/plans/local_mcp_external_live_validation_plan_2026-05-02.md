# Local MCP External And Live Validation Plan - 2026-05-02

## Purpose

This plan addresses the remaining local MCP gaps after commit
`1737050 Close local MCP readiness gaps`.

The previous plans closed the implementation/readiness gaps that can be tested
offline. What remains is evidence work:

- real colleague MCP setup;
- bounded live arXiv source scale;
- bounded live query-discovery smoke before live query enablement;
- eventual PDF batch execution evidence before enabling downloads;
- later review-write MCP exposure evidence before mutation tools are offered.

This plan uses the existing templates where possible:

- `docs/plans/templates/external-validation-record-template.md`;
- `docs/plans/templates/phase-execution-template.md`;
- `docs/mcp_colleague_trial_record_template.md`.

## Motivation

The local MCP code is now deliberately conservative:

- local stdio only;
- read-only by default;
- explicit-ID source batch writes require local grants;
- pinned candidate-file planning exists without live query discovery;
- PDF batch has policy checks but no downloader;
- review-write is CLI-only and not exposed through MCP.

The remaining risk is no longer mostly code shape. It is whether real users and
live services behave as expected. Closing that risk requires repeatable
protocols, sanitized records, and clear stop/go criteria before any broader MCP
capability is enabled.

## Remaining Hypotheses

- **H1:** A real colleague can configure `ra-mcp` in an MCP client against demo
  data in under 15 minutes without unsafe tools appearing.
- **H2:** Grant-bound explicit-ID arXiv source intake works at 25, then 50, then
  100 live papers with bounded failures and useful manifests.
- **H3-live:** Live arXiv query discovery can produce a bounded candidate file
  without uncontrolled pagination, and the pinned file can drive source intake
  through the existing grant path.
- **H4-exec:** PDF batch execution should remain disabled until checksum,
  cleanup, duplicate/no-overwrite, manifest/audit, and a tiny live smoke are
  implemented and recorded.
- **H5-MCP:** Review-write should remain CLI-only until UX review, undo or
  correction policy, audit review, and explicit MCP confirmation design pass.

## Non-Negotiable Rules

- Do not fabricate external validation evidence.
- Do not run live network batches unless explicitly approved for the current
  command.
- Do not record private papers, raw PDFs, extracted text, workspace archives,
  local grants, audit logs, credentials, tokens, shell history, or private
  colleague identifiers.
- Keep MCP local stdio.
- Do not add hosted/shared MCP, HTTP transport, shared database, SSO/RBAC, or
  production monitoring.
- Do not expose MCP review mutation.
- Do not expose PDF batch download execution.
- Use `timeout` for validation commands.
- Generated live outputs must go under `/tmp` or an ignored local workspace and
  must not be committed.
- `docs/plans/` is ignored; force-stage only this plan and the reset memo if
  committing.

## Execution Policy For This Autonomous Pass

This pass can safely implement:

- sanitized validation record examples/templates;
- dry-run command protocols;
- live-run checklists with explicit approval gates;
- CLI helpers that print safe commands or summarize readiness without executing
  live network;
- documentation and release-report clarification;
- deterministic offline tests.

This pass must not claim:

- a real colleague trial was completed;
- live arXiv source scale was measured;
- live query discovery is enabled;
- PDF batch download execution is safe;
- MCP review-write is ready.

If a phase requires a real colleague or live network execution to advance, the
phase should create the protocol and stop at `manual_external_required` or
`manual_live_approval_required`, then continue to other offline phases if they
remain justified.

Any live command shown in this plan or its produced protocol documents is a
future operator command. It is not executed during this autonomous pass unless
the user separately approves that exact live run.

## Required Audit Before Execution

Audit this plan as another developer before implementation:

- **Evidence:** Could any wording imply manual/live evidence exists when it
  does not?
- **Privacy:** Could records capture private research, colleague identity, local
  usernames, credentials, or raw artifacts?
- **Network:** Could any deterministic command accidentally execute live
  network calls?
- **Permissions:** Could helper code create grants, run intake, download PDFs,
  or mutate reviews without explicit human approval?
- **Scope:** Does any phase drift from local MCP into hosted/shared platform
  work?
- **Git hygiene:** Could generated artifacts, validation workspaces, or ignored
  outputs be staged?

Patch this plan before execution if any issue is found.

## Execution Loop

Each phase follows the existing phase template:

1. Plan for the phase.
2. Execute.
3. Test.
4. Audit as another developer.
5. Tidy.
6. Update `docs/plans/reset_memo_2026-04-26.md`.
7. Continue if the next phase is still justified.

## Phase 0 - Baseline And Plan Audit

### Motivation

Verify the repo is clean and the plan is honest before creating any live/external
validation scaffolding.

### Implementation Instructions

- Record current branch and recent commits.
- Run:

```bash
timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py -q
git diff --check
```

- Audit this plan with the Required Audit checklist.

### Acceptance Criteria

- Baseline tests pass.
- Plan preserves local-only scope.
- Plan does not overclaim external/live evidence.

## Phase 1 - External Validation Record Pack

### Motivation

The colleague MCP trial template exists, but the project needs a small record
pack that ties together the generic external-validation template, the MCP
colleague template, and the exact local MCP hypotheses.

### Implementation Instructions

- Add `docs/validation/local_mcp_external_validation_records.md`.
- Base its structure on:
  - `docs/plans/templates/external-validation-record-template.md`;
  - `docs/mcp_colleague_trial_record_template.md`.
- Include sections for:
  - H1 real colleague MCP setup record;
  - H2 live explicit-ID arXiv source scale record;
  - H3-live query discovery smoke record;
  - H4 PDF execution precondition record;
  - H5 review-write MCP precondition record.
- Each section must state:
  - required evidence;
  - commands or records to collect;
  - privacy exclusions;
  - pass/narrow/fail criteria;
  - current status.
- Link it from `docs/mcp_trial_checklist.md`, `docs/mcp.md`, and known
  limitations.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- There is one safe place to record external/live MCP evidence.
- No section asks for private research content or credentials.

## Phase 2 - Live ArXiv Source Scale Protocol

### Motivation

H2 requires real network evidence, but live execution must be bounded and
approval-gated. The project should make the exact commands and stop conditions
unambiguous before anyone runs 25/50/100 paper batches.

### Implementation Instructions

- Add `docs/validation/local_mcp_live_arxiv_scale_protocol.md`.
- Include:
  - explicit approval requirement;
  - `/tmp` workspace convention;
  - allowed domains;
  - max counts: 25, 50, 100;
  - timeout values;
  - duplicate policy;
  - no-overwrite policy;
  - commands for plan/grant/run/audit;
  - metrics to record;
  - stop conditions;
  - sanitized result table.
- Add deterministic helper if useful, but it must only print planned commands or
  summarize current dry-run readiness.
- Do not run live arXiv network in deterministic tests.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H2 has an executable live protocol.
- No live network evidence is claimed unless a real run is separately approved
  and recorded.

## Phase 3 - Live Query Discovery Pre-Enablement Protocol

### Motivation

Offline pinned candidate-file planning exists. Live query discovery should not
be enabled until one bounded live query smoke proves candidate generation,
pagination limits, and candidate-file pinning.

### Implementation Instructions

- Add `docs/validation/local_mcp_live_query_discovery_protocol.md`.
- Define:
  - allowed endpoint: `https://export.arxiv.org/api/query`;
  - max candidate counts;
  - pagination cap;
  - timeout;
  - candidate-file schema;
  - plan-hash checks;
  - grant/run flow using the saved candidate file;
  - pass/narrow/fail criteria.
- Make clear that live query discovery remains disabled in code and MCP.
- Add tests only if deterministic docs/code helpers are added.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H3-live has a bounded approval protocol.
- Live query discovery remains disabled.

## Phase 4 - PDF Execution And Review-Write MCP Precondition Protocol

### Motivation

H4 and H5 should not be implemented just because the first policy/prototype
exists. They need explicit preconditions and stop/go criteria.

### Implementation Instructions

- Add `docs/validation/local_mcp_write_surface_preconditions.md`.
- Include PDF batch execution preconditions:
  - checksum capture;
  - temporary-file cleanup;
  - duplicate/no-overwrite;
  - manifest/audit;
  - tiny live smoke;
  - docs/release-report update;
  - no automatic approval.
- Include review-write MCP preconditions:
  - CLI UX review;
  - undo/correction policy;
  - audit review;
  - exact confirmation payload;
  - conflict behavior;
  - no bulk approval;
  - MCP tool exposure checklist.
- Link from `docs/mcp.md`, `docs/architecture/mcp_pdf_batch_intake_design.md`,
  and `docs/architecture/mcp_review_write_design.md`.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H4/H5 next work is gated by explicit preconditions.
- No PDF execution or MCP review-write is enabled.

## Phase 5 - Release-Report Manual Gate References

### Motivation

`ra release-report` already exposes gate statuses. It should also point to the
validation record/protocol docs so the next human knows exactly where to record
evidence.

### Implementation Instructions

- Update `mcp_readiness_status(...)` gate entries with doc path references for:
  - external validation records;
  - live arXiv scale protocol;
  - live query discovery protocol;
  - PDF/review-write preconditions.
- Add tests to `tests/integration/test_individual_release_cli.py`.
- Keep statuses conservative.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Release-report points to concrete evidence/protocol docs.
- No manual/live gate is marked passed.

## Phase 6 - Final Validation And Commit

### Motivation

This pass should leave the repo in a clean, committed state with only
deterministic docs/tests/code changes.

### Implementation Instructions

- Run:

```bash
timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
python -m research_assistant.cli release-report
git status --short --ignored
git diff --check
```

- Confirm no private/generated artifacts are staged.
- Force-stage only this ignored plan and the reset memo from `docs/plans/`.
- Commit intended changes.

### Acceptance Criteria

- Final tests pass.
- Commit contains only intended docs/tests/code changes.
- Remaining hypotheses are explicit and not overclaimed.

## Final Definition Of Done

This plan is complete when:

- external/live validation record docs exist;
- live arXiv scale and live query protocols are documented and approval-gated;
- PDF execution and MCP review-write preconditions are documented;
- release-report points to those protocols;
- all deterministic tests pass;
- no live evidence is claimed without a real run;
- no generated/private artifacts are committed.
