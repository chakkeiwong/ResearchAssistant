# Local MCP H1-H5 Full Hypothesis Test Plan - 2026-05-02

## Purpose

This plan defines the full evidence required to complete the H1-H5 local MCP
hypothesis tests after commit `3dd4ab6 Document local MCP external validation
gates`.

The current repo has safe implementation scaffolding and explicit protocols:

- local stdio MCP;
- read-only default MCP tools;
- grant-bound explicit-ID arXiv source intake;
- offline pinned candidate-file planning;
- PDF batch policy checks with execution disabled;
- CLI-only review-write with MCP mutation disabled;
- external/live validation record documents under `docs/validation/`.

This plan is different from the prior plans. Its goal is not more scaffolding.
Its goal is to complete the hypothesis tests with real evidence where required,
or stop honestly when the required external/live evidence is unavailable.

## Hypotheses Under Test

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

## Evidence Rule

A hypothesis is complete only when it is classified as one of:

- `accepted`;
- `rejected`;
- `narrowed`;
- `blocked_external`;
- `blocked_live_approval`;
- `deferred_by_safety_gate`.

Do not mark a hypothesis `accepted`, `rejected`, or `narrowed` without direct
evidence. If the required actor or live approval is unavailable, record the
blocking classification instead.

## Non-Negotiable Rules

- Do not fabricate colleague validation.
- Do not run live network commands unless the user explicitly approves the
  exact live run.
- Do not commit raw PDFs, source archives, extracted text, local grants, audit
  logs, manifests, candidate API responses, workspace archives, credentials,
  tokens, or private colleague metadata.
- Keep MCP local stdio.
- Do not expose hosted/shared MCP, HTTP MCP, shared database, SSO/RBAC, or
  production monitoring.
- Do not expose PDF batch execution unless H4 preconditions pass.
- Do not expose MCP review-write unless H5 preconditions pass.
- Use `timeout` for validation commands.
- Use `/tmp` or ignored workspaces for live/generated outputs.
- `docs/plans/` is ignored; force-stage only this plan and the reset memo if
  committing.

## Required Inputs To Fully Complete

Full completion needs inputs that an autonomous local agent does not possess by
default:

- H1 needs a real colleague or fresh reader using an MCP client.
- H2 needs explicit approval to run live arXiv source fetches and a sanitized ID
  list for 25/50/100 paper batches.
- H3-live needs explicit approval to perform a live query smoke against arXiv.
- H4-exec needs a decision to implement PDF downloader execution, then tiny live
  smoke approval.
- H5-MCP needs human UX/audit review and explicit approval to design or expose
  MCP mutation.

If any of these inputs is unavailable, the phase must record the blocker and
stop before claiming the hypothesis is complete.

## Execution Loop

For each phase:

1. Plan for the phase.
2. Execute.
3. Test.
4. Audit as another developer.
5. Tidy generated outputs.
6. Update `docs/plans/reset_memo_2026-04-26.md` with results,
   interpretation, and next-phase justification.
7. Continue only if the next phase remains justified.

## Phase 0 - Baseline And Plan Audit

### Motivation

Before attempting external/live hypothesis tests, confirm the current local MCP
surface is green and the plan does not overclaim.

### Implementation Instructions

- Record branch and recent commits.
- Run:

```bash
timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

- Audit this plan against:
  - evidence rule;
  - privacy;
  - network approval;
  - MCP scope;
  - generated artifact hygiene.

### Acceptance Criteria

- Baseline tests pass.
- Plan clearly separates direct evidence from blockers.
- Next phase is justified only if H1 can be run with a real colleague or can be
  honestly classified as blocked.

## Phase 1 - H1 Real Colleague MCP Setup Test

### Motivation

MCP usability cannot be proven by maintainer-machine tests. A real fresh reader
must configure a client and exercise tools.

### Required Inputs

- A real colleague or fresh reader.
- Their MCP client.
- Non-private demo workspace.
- Permission to record sanitized metadata.

### Implementation Instructions

- Give the colleague:
  - `docs/mcp.md`;
  - `docs/mcp_trial_checklist.md`;
  - `docs/mcp_colleague_trial_record_template.md`;
  - `docs/validation/local_mcp_external_validation_records.md`.
- Ask them to run:

```bash
python -m pip install ".[mcp]"
ra --root /tmp/ra-mcp-trial demo setup
ra-mcp --root /tmp/ra-mcp-trial
```

- Ask them to configure local stdio MCP:

```bash
ra-mcp --root /tmp/ra-mcp-trial
```

- Record:
  - time-to-first-tool-call;
  - tools exercised;
  - unsafe tools absent;
  - whether review-write remains absent from MCP;
  - confusion points;
  - pass/narrow/fail result.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Accept H1 only if the real colleague completes the setup in under 15 minutes
  and unsafe tools are absent.
- Narrow H1 if setup works with assistance or docs need targeted fixes.
- Reject H1 if setup fails or unsafe tools appear.
- If no real colleague is available, classify H1 as `blocked_external` and ask
  for direction before claiming completion.

## Phase 2 - H2 Live Explicit-ID ArXiv Source Scale Test

### Motivation

Mocked 25-paper mechanics prove local planning/grant/run behavior, but live
arXiv scale requires network evidence.

### Required Inputs

- User approval for live network execution.
- Sanitized explicit arXiv ID lists for 25, 50, and 100 papers.
- Agreement to use `/tmp` workspaces and commit only sanitized summaries.

### Implementation Instructions

- Follow `docs/validation/local_mcp_live_arxiv_scale_protocol.md`.
- Run 25 first.
- Run 50 only if 25 is acceptable.
- Run 100 only if 50 is acceptable.
- Record only sanitized metrics:
  - attempted;
  - fetched;
  - skipped;
  - failed;
  - elapsed;
  - timeout;
  - throttling/failure summary.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Accept H2 if all three live sizes complete within bounds with useful
  manifests and no approval/overwrite behavior.
- Narrow H2 if 25 or 50 works but larger sizes need lower limits.
- Reject H2 if live behavior is unsafe or unusable.
- If live network approval or sanitized ID lists are unavailable, classify H2 as
  `blocked_live_approval`.

## Phase 3 - H3-Live Query Discovery Smoke Test

### Motivation

Offline candidate-file planning exists. Live query discovery must prove bounded
candidate generation before any implementation is enabled.

### Required Inputs

- User approval for a live query smoke.
- Non-private query string.
- Max candidate count and timeout.

### Implementation Instructions

- Follow `docs/validation/local_mcp_live_query_discovery_protocol.md`.
- Produce a candidate file only.
- Inspect candidate file.
- Plan from candidate file.
- If approved, run source intake through existing grant-bound candidate-file
  path.
- Do not expose live query through MCP.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Accept H3-live only if query is bounded, candidate file validates, plan hash
  binds exact ordered IDs, and any source intake uses explicit grant.
- Narrow H3-live if candidate generation is safe but noisy or rate-limited.
- Reject H3-live if query fanout or candidate drift is unsafe.
- If live query approval is unavailable, classify H3-live as
  `blocked_live_approval`.

## Phase 4 - H4 PDF Batch Execution Decision

### Motivation

PDF execution is higher risk than source fetch. The hypothesis is not that PDF
execution should be enabled now; it is that enabling requires preconditions.

### Required Inputs

- Explicit decision whether to implement a downloader in this pass.
- If yes, approval for a tiny live smoke.

### Implementation Instructions

- Compare current code against
  `docs/validation/local_mcp_write_surface_preconditions.md`.
- If the user approves implementation:
  - implement inbox-only downloader;
  - enforce count/byte/domain/no-overwrite;
  - add checksum, cleanup, manifest, audit tests;
  - run only deterministic mocked network tests first;
  - request explicit approval before tiny live smoke.
- If implementation is not approved:
  - classify H4 as `deferred_by_safety_gate`;
  - record missing preconditions.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_pdf_batch_policy.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Accept H4-exec only after implementation, tests, and tiny live smoke pass.
- Narrow H4-exec if policy is clear but execution remains too risky.
- Defer H4-exec if no explicit implementation/live-smoke approval is present.

## Phase 5 - H5 MCP Review-Write Decision

### Motivation

Review mutation changes trusted local review state. MCP exposure must wait for
human UX and audit review.

### Required Inputs

- Human review of CLI proposal/apply/cleanup UX.
- Decision on undo/correction policy.
- Explicit approval to design or expose MCP mutation.

### Implementation Instructions

- Compare current CLI prototype against
  `docs/validation/local_mcp_write_surface_preconditions.md`.
- If the user approves MCP design work:
  - write exact MCP confirmation payload design;
  - add tests for absence/presence gates;
  - keep mutation disabled until final approval.
- If exposure is not approved:
  - classify H5 as `deferred_by_safety_gate`;
  - record missing UX/audit/undo evidence.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_cli_commands.py tests/integration/test_mcp_adapter.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Accept H5-MCP only if UX/audit/undo evidence and exact confirmation design
  pass and explicit approval is recorded.
- Narrow H5-MCP if CLI is useful but MCP exposure remains premature.
- Defer H5-MCP if approval or human UX/audit review is unavailable.

## Phase 6 - Final Classification, Release-Report Update, And Commit

### Motivation

The plan should finish by recording each hypothesis classification truthfully.

### Implementation Instructions

- Update evidence docs with the final H1-H5 classifications.
- Update `ra release-report` gate statuses only if direct evidence changed.
- Run final validation:

```bash
timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
python -m research_assistant.cli release-report
git status --short --ignored
git diff --check
```

- Commit intended docs/code/test changes.

### Acceptance Criteria

- Every H1-H5 hypothesis is classified truthfully.
- No external/live evidence is claimed without direct evidence.
- No generated/private artifacts are committed.

## Final Definition Of Done

This plan is complete only when:

- H1 is accepted/rejected/narrowed by real colleague evidence, or blocked as
  `blocked_external`;
- H2 is accepted/rejected/narrowed by live arXiv scale evidence, or blocked as
  `blocked_live_approval`;
- H3-live is accepted/rejected/narrowed by live query smoke evidence, or blocked
  as `blocked_live_approval`;
- H4-exec is accepted/rejected/narrowed by implementation/live-smoke evidence,
  or deferred as `deferred_by_safety_gate`;
- H5-MCP is accepted/rejected/narrowed by UX/audit/design evidence, or deferred
  as `deferred_by_safety_gate`;
- all conclusions are recorded in the reset memo and validation docs;
- tests pass;
- changes are committed.
