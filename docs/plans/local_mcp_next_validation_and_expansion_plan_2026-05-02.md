# Local MCP Next Validation And Expansion Plan - 2026-05-02

## Purpose

This plan defines the next work after commit `28115cd Add local MCP adapter and
batch grants`.

The local MCP foundation now exists:

- `ra-mcp` local stdio server;
- optional `research-assistant[mcp]` dependency;
- read-only local inspection tools;
- plan-first explicit-ID arXiv batch planning;
- CLI-created local grants;
- grant-bound arXiv source batch execution;
- manifest/audit records;
- release-report MCP readiness.

The next goal is not to broaden into a hosted platform. The next goal is to
validate and expand this local MCP workflow carefully:

1. prove a colleague can configure and use local MCP;
2. stress explicit-ID arXiv source intake at useful batch sizes;
3. evaluate query-based arXiv discovery without network fanout;
4. design PDF inbox batch downloads before enabling them;
5. design and prototype review-write only after confirmation/audit behavior is
   strong enough.

## Motivation

The first MCP implementation solved the adapter and permission-foundation
problem. It did not yet prove that the workflow is ergonomic at real scale.

The most important hypotheses are:

- **H1:** a colleague can configure `ra-mcp` in an assistant against demo data in
  under 15 minutes.
- **H2:** explicit-ID arXiv source intake works smoothly for 25-100 papers.
- **H3:** query-based arXiv discovery can be added without uncontrolled network
  fanout or unclear grants.
- **H4:** PDF batch downloads need separate byte limits, duplicate UX, and
  overwrite rules before being enabled.
- **H5:** review-write MCP should wait until old/new value, file-hash, conflict,
  and audit confirmation behavior is implemented.

The workflow should preserve the current product posture:

- individual local use;
- file-based workspace;
- default offline/provider-disabled behavior;
- generated/source/parser/batch artifacts as review material;
- no hosted MCP server;
- no shared database;
- no silent review approval.

## Current Baseline

Relevant files:

- `src/research_assistant/adapters/mcp_server.py`
- `src/research_assistant/adapters/local_tools.py`
- `src/research_assistant/adapters/mcp_permissions.py`
- `src/research_assistant/ingest/arxiv_batch.py`
- `docs/mcp.md`
- `docs/mcp_trial_checklist.md`
- `docs/architecture/local_mcp_adapter.md`
- `docs/architecture/mcp_review_write_design.md`
- `tests/integration/test_mcp_adapter.py`
- `tests/integration/test_mcp_permissions.py`
- `tests/integration/test_arxiv_batch_intake.py`

Recent validation from the implementation pass:

- MCP/permissions/batch/individual release suite: `33 passed`.
- MCP CLI grant focused tests: `3 passed`.
- `ra-mcp --help`: passed.
- fast suite: `14 passed`.
- CLI integration file: `22 passed`.
- `git diff --check`: passed.

Known local state:

- branch is ahead of `origin/main` by 1 commit;
- `.codex` remains untracked local scratch and must not be committed.

## Non-Negotiable Rules

- Keep MCP local stdio for these phases.
- Do not add HTTP MCP, hosted server deployment, shared database, SSO/RBAC, or
  production monitoring.
- Keep base CLI usable without installing the MCP extra.
- Do not expose review mutation tools until the explicit review-write gate is
  passed.
- Do not expose destructive tools through MCP.
- Do not make live provider/LLM calls part of the default workflow.
- Do not commit raw PDFs, source package archives, extracted full text,
  downloaded corpora, batch outputs, local grants, audit logs, manifests,
  caches, `dist/`, `build/`, `.codex`, `.claude`, or private colleague
  metadata.
- Use explicit limits for any live network batch:
  - maximum paper count;
  - maximum bytes where applicable;
  - timeout;
  - allowed domains;
  - destination;
  - duplicate policy;
  - no overwrite.
- Record only non-private validation metadata.
- Use `timeout` for validation commands.
- `docs/plans/` is ignored; force-stage only intentional plan/reset memo files
  if committing.

## Required Audit Before Execution

Before implementing any phase, audit this plan as another developer:

- **Scope:** Does any phase drift from local MCP into hosted/shared platform
  work?
- **Privacy:** Could a trial or batch record leak private papers, extracted
  text, local paths that should not be shared, credentials, or colleague data?
- **Permissioning:** Could a tool write, download, overwrite, or mutate review
  state without a bounded grant or confirmation?
- **Network control:** Could query discovery or PDF download fan out
  unexpectedly?
- **Research trust:** Could fetched/generated/parser records be treated as
  approved evidence?
- **Engineering:** Are changes testable offline, and are live checks optional
  and bounded?

If the audit finds gaps, update this plan before execution.

### Pre-Execution Audit Result - 2026-05-02

Audit performed as another developer before executing the plan.

Findings and corrections:

- **Human colleague dependency:** Phase 1 requires a real colleague MCP setup
  trial, which an autonomous agent cannot create. If no colleague is available
  during execution, run a local surrogate against demo data, record H1 as
  external/manual rather than passed, and continue with engineering phases.
- **Live arXiv dependency:** Phase 2 should not require live network for
  deterministic execution. Use a sanitized explicit-ID fixture and mocked source
  fetch for automated scale evidence. Record live 25/50/100 paper batches as a
  separate manual validation item unless the user explicitly approves a bounded
  live network run.
- **Query discovery enablement:** Phase 3 may add parser/contract helpers and
  mocked tests, but must not enable live query discovery through MCP without a
  later bounded live approval.
- **PDF batch intake:** Phase 4 should remain design/policy only unless byte
  limits, cleanup, duplicate behavior, and tests are implemented.
- **Review-write:** Phase 5 may implement a CLI-only proposal/apply prototype,
  but MCP review-write exposure remains out of scope until a later audit.

No blocker was found after these clarifications. The next phase is justified.

## Execution Loop

For each phase:

1. Update `docs/plans/reset_memo_2026-04-26.md` with phase start, intent, and
   risk.
2. Plan the smallest safe change.
3. Implement or run the phase.
4. Run focused tests with `timeout`.
5. Audit as another developer.
6. Tidy generated outputs.
7. Confirm no private/generated files are staged.
8. Update reset memo with results, interpretation, and whether the next phase
   remains justified.
9. Continue if no major issue; ask for direction only if the next phase is not
   justified.

## Phase 0 - Baseline And Safety Re-Audit

### Motivation

The MCP addition is new and includes one grant-bound write path. Before
expanding it, verify that the current commit is clean, reproducible, and still
within the local-only safety boundary.

### Implementation Instructions

- Record:

```bash
git status --short --branch
git log --oneline -5
ra release-report
ra mcp status
ra-mcp --help
```

- Re-run focused tests:

```bash
timeout 240 python -m pytest \
  tests/integration/test_mcp_adapter.py \
  tests/integration/test_mcp_permissions.py \
  tests/integration/test_arxiv_batch_intake.py -q
```

- Inspect MCP tool names from tests or direct SDK call and confirm:
  - no review mutation tool;
  - no PDF download batch tool;
  - no backup restore;
  - no delete/destructive operation;
  - only `ra_run_arxiv_batch_intake` is write-capable and grant-bound.

### Acceptance Criteria

- Current MCP baseline is green.
- No unexpected write/destructive tool is exposed.
- Next phase is justified only if the baseline remains local-only and
  grant-bound.

## Phase 1 - Colleague MCP Setup Trial

### Motivation

The prior colleague rollout validated the CLI workflow. MCP needs its own
human-centered validation because client configuration, server startup, and tool
discoverability are different failure modes.

### Implementation Instructions

- Use `docs/mcp_trial_checklist.md`.
- Give a colleague only:
  - installation docs;
  - `docs/mcp.md`;
  - `docs/mcp_trial_checklist.md`;
  - a checkout or artifact path.
- Ask them to run:

```bash
python -m pip install ".[mcp]"
ra --root /tmp/ra-mcp-trial demo setup
ra-mcp --root /tmp/ra-mcp-trial
```

- Ask them to configure their MCP client with stdio command:

```bash
ra-mcp --root /tmp/ra-mcp-trial
```

- Ask them to exercise:
  - `ra_workspace_status`;
  - `ra_find_paper`;
  - `ra_get_paper_summary`;
  - `ra_source_show`;
  - `ra_review_list`;
  - `ra_claim_support_audit`;
  - `ra_privacy_status`.

- Record only non-private metadata:
  - platform;
  - Python version;
  - MCP client;
  - install mode;
  - time-to-first-tool-call;
  - commands/tools completed;
  - confusion points;
  - missing docs;
  - whether unsafe tools were absent.

- If docs are confusing, update docs immediately.
- If setup fails, add focused regression tests before fixing.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- A fresh reader can configure and use local MCP against demo data.
- No private data is recorded.
- Unsafe tool absence is verified.
- H1 is accepted, rejected, or narrowed with evidence.

If no fresh reader is available, run a local surrogate with the same demo
workspace and mark H1 as `external_validation_required`, not passed.

## Phase 2 - Explicit-ID ArXiv Source Batch Scale Trial

### Motivation

The current batch execution is tested with small mocked cases. The key product
question is whether explicit-ID source intake remains usable for realistic
paper batches.

### Implementation Instructions

- Build or choose a non-private explicit ID list:
  - 25 papers first;
  - then 50;
  - then 100 only if earlier runs are comfortable.
- Prefer a sanitized fixture list checked into tests if possible.
- For live runs, use a temporary local workspace:

```bash
ra --root /tmp/ra-arxiv-batch-25 arxiv-batch plan --ids <csv_ids> --max-papers 25
ra --root /tmp/ra-arxiv-batch-25 mcp grant arxiv-intake \
  --plan-hash <plan_hash> \
  --max-papers 25 \
  --ids <csv_ids> \
  --expires-hours 2 \
  --skip-duplicates
timeout 900 ra --root /tmp/ra-arxiv-batch-25 arxiv-batch run \
  --grant-id <grant_id> \
  --plan-hash <plan_hash> \
  --ids <csv_ids>
```

- Record:
  - count attempted;
  - fetched count;
  - skipped duplicates;
  - failed count;
  - elapsed time;
  - manifest size;
  - audit event count;
  - any arXiv throttling/errors.

- Add tests if any bug appears:
  - grant mismatch;
  - partial failure reporting;
  - retry-safe rerun behavior;
  - duplicate skip behavior after a partial run.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- H2 is accepted, rejected, or narrowed.
- Batch manifests are useful and bounded.
- Rerunning does not overwrite or silently approve records.
- If live arXiv behavior is flaky, document limits and keep larger batches
  experimental.

Mocked fixture scale evidence may support local mechanics only. Live arXiv
scale remains a separate validation claim.

## Phase 3 - Query-Based ArXiv Discovery Design

### Motivation

Explicit IDs are safe but not always ergonomic. Query discovery is useful only
if it can be bounded before network calls and bound to grants after planning.

### Implementation Instructions

- Design a query discovery contract before implementation:
  - query string;
  - maximum candidate count;
  - arXiv API endpoint;
  - pagination limit;
  - timeout;
  - rate-limit behavior;
  - deterministic candidate ordering;
  - duplicate detection;
  - plan hash fields;
  - provenance fields.

- Add a design doc:

```text
docs/architecture/mcp_arxiv_query_discovery_design.md
```

- Prototype with mocked arXiv API responses first.
- Do not enable live query discovery through MCP until:
  - mocked tests pass;
  - bounded live smoke is manually approved;
  - plan hash includes query and candidate list;
  - grant execution verifies candidate list, not just query text.

- Suggested future CLI shape:

```bash
ra arxiv-batch discover --query "transport maps HMC" --max-candidates 50
ra arxiv-batch plan --query "transport maps HMC" --max-papers 25 --candidate-file <file>
```

### Tests And Verification

- Mocked query response tests.
- No live network in deterministic tests.
- Test that pagination cannot exceed configured max.
- Test that plan hash changes when candidate list changes.

```bash
timeout 240 python -m pytest tests/integration/test_arxiv_batch_intake.py -q
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- H3 has a concrete implementation design.
- No uncontrolled fanout path exists.
- Query discovery remains disabled or clearly experimental until bounded live
  evidence exists.

## Phase 4 - PDF Batch Intake Design Gate

### Motivation

PDF download is riskier than source fetch because files can be larger,
duplicates are harder, and private/local paper inboxes become cluttered quickly.
It needs a separate policy before enabling.

### Implementation Instructions

- Add design doc:

```text
docs/architecture/mcp_pdf_batch_intake_design.md
```

- Define:
  - allowed domains;
  - max file count;
  - max total bytes;
  - per-file byte limit;
  - MIME/content-type expectations;
  - checksum capture;
  - duplicate detection;
  - inbox-only destination;
  - no overwrite;
  - proposal metadata;
  - partial failure behavior;
  - cleanup policy for failed downloads.

- Decide whether PDFs should use:
  - `local_research/inbox/` only;
  - existing `download_to_inbox`;
  - separate `batch_inbox/` namespace;
  - explicit proposal records before file download.

- Do not enable PDF batch execution until the design is audited.

### Tests And Verification

- Design review only in this phase.
- Add tests only for policy/contract helpers if implemented.

### Acceptance Criteria

- H4 is documented with a concrete policy.
- PDF downloads remain disabled until byte limits, duplicate behavior, and
  cleanup semantics are testable.

## Phase 5 - Review-Write Confirmation Prototype

### Motivation

Review-write is the highest trust boundary after destructive operations. It can
save time, but only if every mutation is specific, auditable, and conflict-safe.

### Implementation Instructions

- Use `docs/architecture/mcp_review_write_design.md` as the source.
- Prototype a non-MCP CLI proposal/apply flow first:

```bash
ra review-write propose-status --paper-id <id> --status approved
ra review-write apply --confirmation-id <id>
```

- The proposal must record:
  - workspace root;
  - paper ID;
  - target file;
  - old value;
  - new value;
  - old file hash;
  - risks;
  - expiration.

- Apply must:
  - verify confirmation ID;
  - verify file hash has not changed;
  - write old/new values to audit log;
  - block on conflict;
  - not bulk-approve multiple papers.

- Do not expose MCP review-write until the CLI proposal/apply flow is tested.

### Tests And Verification

- Tests for:
  - proposal creation;
  - successful apply;
  - stale file hash conflict;
  - invalid status rejection;
  - audit event content;
  - no generated/parser content promotion.

```bash
timeout 240 python -m pytest tests/integration/test_cli_commands.py -q
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- H5 is either accepted for a future MCP tool or rejected/deferred.
- Review-write remains absent from MCP until confirmation and conflict tests
  pass.

## Phase 6 - Documentation And Release Readiness Update

### Motivation

Any expansion needs to be visible in docs and release reports so colleagues know
what is safe, what is experimental, and what remains deferred.

### Implementation Instructions

- Update:
  - `docs/mcp.md`;
  - `docs/mcp_trial_checklist.md`;
  - `docs/known_limitations.md`;
  - `docs/troubleshooting.md`;
  - `docs/release_notes_0.1.0.md` if this is release-facing.

- Update release-report only if new readiness surfaces are executable and
  deterministic.
- Keep optional MCP absence non-blocking for base release.

### Tests And Verification

```bash
timeout 240 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- Docs match implementation.
- No release docs imply hosted/shared MCP readiness.
- Experimental query/PDF/review-write items are clearly labeled.

## Final Definition Of Done

This follow-on plan is complete when:

- H1-H5 are each accepted, rejected, or narrowed with evidence.
- Colleague MCP setup trial is recorded without private data.
- Explicit-ID source batch scale limits are measured.
- Query discovery has a bounded design and mocked tests before live enablement.
- PDF batch intake has a byte/destination/duplicate policy before execution.
- Review-write has a CLI confirmation prototype before MCP exposure.
- Release docs and readiness surfaces remain conservative and local-first.
- All tests pass and no private/generated artifacts are committed.
