# Local MCP H3/H4 Release Closure Plan - 2026-05-03

## Purpose

This plan closes the release-documentation loop for H3 and H4 after the live
validation commit `7c1e2c4 Accept H3 H4 live MCP validation`.

The implementation and live evidence for H3/H4 are already present. This plan
therefore does not rerun live network tests by default. Its goal is to:

- record the accepted evidence in a release-facing plan;
- update `proposal/research_development_assistant_design.tex` with the local
  MCP additions in detail;
- audit the release claims so they stay local/pilot-scoped;
- run deterministic validation and a LaTeX compile check;
- update the reset memo phase by phase;
- commit only intentional documentation changes.

## Motivation

The local MCP work changes the adoption story. Before MCP, the package was a
local CLI and file-based research workflow. With MCP, it can also serve as a
local read-only research memory layer for assistant clients while keeping risky
write paths behind CLI grants and explicit confirmations.

H3 and H4 matter because they sit at the boundary between helpful automation and
unsafe bulk action:

- H3 tests whether a live arXiv query can be converted into a bounded,
  checksum-pinned candidate file instead of uncontrolled discovery fanout.
- H4 tests whether PDF execution can be kept inbox-only, grant-bound,
  byte-limited, duplicate-safe, audited, and absent from MCP.

Closing these hypotheses supports a local colleague/pilot release only if the
release materials remain explicit that:

- live query discovery is CLI-only validation functionality, not an MCP tool;
- PDF inbox download is CLI-only and accepted only at tiny live-smoke scale;
- downloaded PDFs and source records are review material, not approved evidence;
- MCP review-write remains disabled until H5 preconditions pass;
- hosted/shared MCP, HTTP MCP, shared databases, SSO/RBAC, and department/public
  rollout remain out of scope.

## Evidence Baseline

Truth sources for this plan:

- `docs/validation/local_mcp_external_validation_records.md`;
- `docs/validation/local_mcp_live_query_discovery_protocol.md`;
- `docs/validation/local_mcp_write_surface_preconditions.md`;
- `docs/mcp.md`;
- `docs/known_limitations.md`;
- commit `7c1e2c4 Accept H3 H4 live MCP validation`.

Current hypothesis classifications:

| Hypothesis | Current Classification | Release Interpretation |
| --- | --- | --- |
| H1 external MCP setup | `accepted` | External-agent local stdio setup passed against demo data; unsafe tools and MCP review-write were absent. |
| H2 explicit-ID arXiv source intake | `accepted` | Grant-bound public-ID source intake passed at 25/50/100; this supports explicit-ID source intake, not query discovery or PDFs. |
| H3 live query discovery | `accepted` | Bounded CLI query produced a pinned candidate file; grant-bound source follow-up worked; live query remains absent from MCP. |
| H4 PDF execution | `accepted_cli_only` | Grant-bound CLI PDF inbox download passed deterministic policy tests and one-PDF live smoke; MCP PDF execution remains absent. |
| H5 MCP review-write | `preconditions_required` | CLI prototype exists; MCP mutation remains disabled. |

## Non-Negotiable Scope Rules

- Do not run additional live arXiv network commands unless separately approved.
- Do not expose live query discovery through MCP.
- Do not expose PDF download execution through MCP.
- Do not expose MCP review mutation.
- Do not commit raw PDFs, arXiv source archives, extracted text, manifests,
  audit logs, local grants, workspace archives, credentials, private titles, or
  private local paths.
- Do not claim broad/public/department release readiness from H3/H4.
- Keep all release wording scoped to a local colleague/pilot release unless
  additional platform evidence is recorded.

## Execution Loop

Each phase follows:

1. Plan for the phase.
2. Execute.
3. Test.
4. Audit as another developer.
5. Tidy generated or ignored artifacts.
6. Update `docs/plans/reset_memo_2026-04-26.md` with results,
   interpretation, and next-phase justification.
7. Continue automatically if the next phase remains justified.

## Phase 0 - Baseline And Plan Creation

### Motivation

Confirm the repo baseline and write the dedicated closeout plan before touching
the proposal. This prevents a release-facing document from overclaiming beyond
the committed H3/H4 evidence.

### Plan For The Phase

- Inspect git status and recent commits.
- Read the H3/H4 validation records and proposal document.
- Create this plan under `docs/plans`.
- Add an initial reset-memo checkpoint.

### Test

- `git status --short`;
- `git log --oneline -8`;
- manual evidence check against validation records.

### Audit As Another Developer

Questions:

- Does the plan distinguish accepted evidence from release readiness?
- Does it avoid rerunning live network tests without a new need?
- Does it keep H3/H4 absent from MCP?
- Does it keep H5 deferred?

### Acceptance Criteria

- Plan exists and is explicit enough for another developer to execute.
- Reset memo records the baseline and next justified phase.

## Phase 1 - Independent Plan Audit

### Motivation

The plan should be audited before proposal edits because the proposal is the
user-facing release claim. The audit should behave like a skeptical maintainer
checking for missing risks and overbroad wording.

### Plan For The Phase

- Audit the plan against:
  - permission story;
  - clear confirmation behavior;
  - privacy hygiene;
  - MCP exposure boundaries;
  - release-scope boundaries;
  - evidence traceability.
- Patch the plan if any gap is found.
- Update the reset memo with the audit result.

### Test

- Manual plan audit.
- `git diff --check` after any plan patch.

### Acceptance Criteria

- No major missing point remains before proposal editing.
- Any remaining limitation is explicitly documented.

## Phase 2 - Proposal LaTeX Update

### Motivation

The proposal currently explains the local-first package but needs a detailed MCP
section that reflects the accepted H1-H4 evidence and the H5 boundary. This is
what lets a reader understand why closing H3/H4 makes the local/pilot release
stronger without implying broad platform readiness.

### Implementation Instructions

Update `proposal/research_development_assistant_design.tex` to include:

- a local MCP adapter section under assistant workflows;
- the exact permission model:
  - local stdio only;
  - read-only MCP default;
  - no hosted service;
  - no review mutation through MCP;
  - no PDF download or live query execution through MCP;
- the batch-grant model:
  - explicit-ID arXiv source intake is grant-bound;
  - live query discovery writes a bounded pinned candidate file;
  - source follow-up runs through the grant-bound candidate-file path;
  - PDF inbox download is CLI-only, grant-bound, byte-limited, duplicate-safe,
    audited, and accepted only at one-PDF live-smoke scale;
- the clear confirmation behavior:
  - write execution uses a generated plan hash plus an expiring local grant ID;
  - the grant binds operation, destination, maximum count, ordered IDs, and
    duplicate policy;
  - execution recomputes the plan identity and blocks on mismatch;
  - review-write is different from batch intake and remains MCP-disabled until
    an exact old/new value plus file-hash confirmation payload is approved;
- the release interpretation:
  - H1-H4 support local colleague/pilot readiness;
  - H5 is not included;
  - broad/public/department release still requires separate onboarding,
    platform, parser, packaging, and publication evidence.

### Test

- LaTeX compile check if `pdflatex` is available.
- `git diff --check`.

### Audit As Another Developer

Questions:

- Does the proposal make the MCP addition concrete and valuable?
- Does it avoid promising MCP writes?
- Does it avoid making one-PDF H4 look like broad PDF batch scale?
- Does it preserve the local/pilot release scope?

### Acceptance Criteria

- Proposal includes detailed MCP additions.
- Proposal wording is accurate relative to validation evidence.
- LaTeX syntax compiles or any missing local tool is documented.

## Phase 3 - Validation And Tidy

### Motivation

Even documentation-only changes should not hide a broken package state, because
the update is tied to release readiness.

### Plan For The Phase

Run deterministic release checks:

```bash
PYTHONPATH=src timeout 240 python -m pytest tests/integration/test_mcp_adapter.py tests/integration/test_mcp_permissions.py tests/integration/test_arxiv_batch_intake.py tests/integration/test_pdf_batch_policy.py tests/integration/test_cli_commands.py tests/integration/test_individual_release_cli.py -q
PYTHONPATH=src timeout 120 scripts/run_fast_tests.sh
PYTHONPATH=src timeout 60 python -m research_assistant.cli release-report
git diff --check
```

Run a LaTeX compile check into `/tmp` when possible:

```bash
pdflatex -interaction=nonstopmode -halt-on-error -output-directory /tmp/ra-proposal-tex proposal/research_development_assistant_design.tex
```

### Tidy

- Review ignored artifacts with `git status --short --ignored`.
- Keep generated artifacts ignored and uncommitted.
- Do not remove unrelated ignored user artifacts.

### Acceptance Criteria

- Deterministic checks pass.
- LaTeX compile passes or the missing tool is documented.
- No generated/private artifact is staged.

## Phase 4 - Final Reset Memo, Commit, And Release Interpretation

### Motivation

The work should finish with a durable handoff: what changed, what passed, what
is ready, and what remains outside the release.

### Plan For The Phase

- Update the reset memo with final results and interpretation.
- Stage intended files only, force-adding the plan under `docs/plans` if needed.
- Commit the documentation closeout.
- Summarize next hypotheses to test.

### Acceptance Criteria

- Commit contains only intended plan/proposal/reset-memo docs.
- Final summary states whether H3/H4 closeout supports release readiness and at
  what scope.

## Final Definition Of Done

The closeout is complete when:

- this plan is committed;
- the proposal describes the MCP addition accurately;
- the reset memo records every phase result;
- deterministic checks pass;
- no raw/generated/private artifacts are committed;
- the final interpretation is explicit:
  - ready for local colleague/pilot release after final release-owner approval;
  - not a broad/public/department platform release;
  - H5 MCP review-write remains a future gated hypothesis.
