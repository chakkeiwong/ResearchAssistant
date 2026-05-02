# Local MCP Addition Plan - 2026-05-02

## Purpose

This plan adds a local Model Context Protocol (MCP) interface to
`research-assistant` after the successful colleague rollout.

The goal is not to turn the tool into a hosted service, shared database,
production API, or multi-user platform. The goal is to let local assistant
clients query and, later, perform tightly bounded intake actions against the
same individual local research workspace that the `ra` CLI already manages.

The first deliverable is a **local stdio MCP server that is read-only by
default**. The second deliverable is a **batch-scoped arXiv intake permission
model** so large literature pulls do not require approving every paper one by
one while still preserving privacy, provenance, and review boundaries.

## Motivation

The colleague rollout changes the sequencing. The local tool has now been
validated by another user and is useful enough to expose through assistant
integrations. MCP is the right next adapter because it can expose local
research lookup, source inspection, claim audit, and eventually bounded arXiv
intake to tools such as Claude Code without forcing a new web service or shared
backend.

The major design risk is permission drift. A local MCP server is simpler than a
hosted service because it avoids multi-user auth, public network exposure,
central storage, production monitoring, and deployment operations. It still
needs guardrails because an assistant connected to a local MCP server can read
private research files, write metadata, download many papers, or accidentally
promote generated material into trusted review state.

This plan resolves that tension by separating:

- read-only local retrieval, which is safe enough for the first MCP release;
- batch arXiv intake, which is useful but must be governed by bounded grants;
- review/status mutation, which should wait until the confirmation and audit
  machinery is proven;
- destructive operations, which remain out of scope.

## Current Baseline

Current relevant surfaces:

- `src/research_assistant/adapters/mcp_server.py` exists but is only a thin
  placeholder wrapper.
- `ra` is the stable user-facing contract.
- Core local lookup functions already exist in modules such as:
  - `research_assistant.query.paper_lookup`;
  - `research_assistant.query.review`;
  - `research_assistant.query.citation_graph`;
  - `research_assistant.adapters.workspace_exports`;
  - `research_assistant.source.structured_source`.
- The product specification says the release target is one local researcher
  with an inspectable file-based store.
- ADR 0006 says server deployment must wait for storage, identity/RBAC,
  operations, and job-orchestration decisions.
- The user has confirmed that colleague rollout is complete and positively
  received.

External MCP baseline:

- The Python SDK supports MCP servers exposing tools, resources, and prompts,
  with stdio and HTTP transports.
- For this project, use stdio first and keep HTTP explicitly out of scope.
- Use the Python SDK's FastMCP layer unless implementation experience reveals a
  reason to drop to the lower-level server API.

## Non-Negotiable Rules

- Keep MCP local-only for this milestone.
- Use stdio transport for the first implementation.
- Do not expose an HTTP listener, hosted server, shared database, SSO/RBAC,
  public network endpoint, or production deployment claim.
- Do not enable live LLM/provider workflows by default.
- Do not let MCP silently approve generated, parser-derived, or downloaded
  records.
- Do not expose raw private PDFs or extracted full text through broad/listing
  tools unless a user explicitly asks for a specific inspected item.
- Do not allow arbitrary filesystem reads or writes through MCP.
- Do not allow path traversal, symlink escape, or writes outside the configured
  workspace root.
- Keep destructive actions out of MCP:
  - no delete;
  - no backup restore;
  - no overwrite;
  - no bulk migration;
  - no repository cleanup.
- Batch arXiv intake must require a bounded grant before writing files.
- Every write-capable MCP action must produce an audit record.
- All generated batch manifests, grants, and audit logs must stay local and must
  not be committed unless explicitly reviewed and sanitized.
- Use `timeout` for validation scripts.
- Files under `docs/plans/` are ignored, so force-stage only intentional plan
  changes if committing.

## Permission Model

### Modes

Implement explicit modes rather than one broad "MCP can write" switch.

- `read_only`
  - Default.
  - May inspect local records, summaries, source metadata, review queues,
    parser/readiness status, and claim-audit output.
  - May not write files, download files, mutate review state, or call providers.

- `arxiv_batch_intake`
  - Future write-capable mode for bounded paper/source intake.
  - Requires a grant created from an explicit user-approved plan.
  - May write only to inbox/source-intake locations defined by the grant.
  - May not mark papers approved or alter review state.

- `review_write`
  - Deferred.
  - May change review metadata only after the confirmation/audit model has
    already passed validation with arXiv batch intake.

- `destructive`
  - Out of scope.
  - Do not implement in this milestone.

### Batch Grants

Batch grants solve the "download tons of papers" problem without approving
every file individually.

An arXiv batch intake grant should include:

- grant ID;
- created timestamp;
- expiration timestamp;
- workspace root;
- allowed domains:
  - `arxiv.org`;
  - `export.arxiv.org`;
- allowed operation:
  - metadata-only discovery;
  - source package fetch;
  - PDF inbox download, if implemented;
- query string or explicit arXiv ID list;
- maximum number of papers;
- maximum bytes, if practical;
- destination policy:
  - `local_research/inbox/`;
  - `local_research/papers/source/`;
  - batch manifest directory;
- duplicate policy:
  - skip existing;
  - record duplicate in manifest;
- overwrite policy:
  - no overwrite by default;
- review policy:
  - do not approve;
  - do not mark trusted;
  - create review material only;
- audit-log path;
- manifest path.

The user approval should attach to the intention:

> Allow local MCP to download up to 200 arXiv papers matching this query into
> the review inbox for the next 2 hours. Skip duplicates. Do not mark anything
> approved.

The MCP server must enforce the grant rather than trusting the assistant's
prompt.

### Confirmation Behavior

For first-stage read-only MCP, confirmation is not needed because no mutation is
allowed.

For batch intake, use a two-step flow:

1. `plan_arxiv_batch_intake`
   - returns a manifest-like plan;
   - performs no writes except optional ephemeral diagnostics;
   - lists intended query/IDs, limits, destinations, domains, duplicate policy,
     and risks.

2. `create_arxiv_batch_grant` or an equivalent CLI-mediated approval step
   - records the approved bounded grant.
   - The safest first implementation is a CLI command that the human runs
     outside MCP:

```bash
ra mcp grant arxiv-intake \
  --query "transport maps HMC" \
  --max-papers 200 \
  --expires-hours 2 \
  --destination inbox \
  --skip-duplicates
```

3. `run_arxiv_batch_intake`
   - requires the grant ID;
   - validates expiry, root, limits, domains, destination, and duplicate policy;
   - writes an audit record and final batch manifest.

Do not implement a vague "confirm yes" argument. Confirmation must bind to a
specific plan, root, operation, scope, limits, and destination.

## Required Audit Before Execution

Before implementation, audit this plan from five perspectives:

- **Scope:** Does the phase preserve local-only MCP rather than drifting into a
  hosted platform?
- **Privacy:** Could the MCP server expose private PDFs, extracted text, local
  paths, credentials, caches, or provider data unexpectedly?
- **Permissioning:** Could an assistant write, download, overwrite, or mutate
  review state without an explicit grant?
- **Research trust:** Could downloaded/generated/parser records be silently
  treated as approved evidence?
- **Engineering:** Are the contracts typed, deterministic, testable, and shared
  with the CLI rather than duplicating CLI print parsing?

If the audit finds gaps, update this plan before implementation.

### Pre-Execution Audit Result - 2026-05-02

Audit performed as another developer before coding.

Findings and corrections:

- **Optional dependency fallback:** The original plan correctly said MCP should
  be optional, but implementation also needs a no-MCP-installed import path so
  base CLI tests and installs keep working. Phase 2 now requires the MCP module
  to expose contract functions even when the SDK is missing and to fail only
  when `ra-mcp` is actually started without the extra.
- **Deterministic MCP testing:** Running a stdio server is a long-lived process,
  so automated tests should call registered FastMCP tools/resources directly
  when the SDK is installed and skip SDK-specific tests otherwise. Do not make
  network package installation part of the offline test suite.
- **Plan/grant binding:** Batch intake needs a stable plan hash, and execution
  must verify that the grant, plan hash, root, operation, limits, destination,
  duplicate policy, and arXiv IDs still match.
- **Root and path safety:** Grant validation must resolve symlinks and reject
  destination paths outside the configured workspace root.
- **Release visibility:** `ra release-report` should expose MCP readiness so
  maintainers can see whether the optional adapter is installed and whether the
  local-only safety posture is intact.
- **Batch execution scope:** Query-based live arXiv search can remain deferred.
  Explicit arXiv ID lists are enough for the first deterministic batch-intake
  execution because they solve the "many papers" workflow without adding a new
  discovery dependency.
- **Review-write boundary:** Tests must assert that review mutation commands
  are not registered as MCP tools in the read-only/batch milestones.

No blocker was found. The next phase remains justified after these corrections.

## Execution Loop

For each phase:

1. Record the phase start and intent in `docs/plans/reset_memo_2026-04-26.md`
   if this work is being run as part of release execution.
2. Implement the smallest safe change.
3. Add focused tests before or alongside code where behavior changes.
4. Run focused tests with `timeout`.
5. Audit as another developer for scope creep, private data leakage, write
   escape, and false review approval.
6. Tidy generated files.
7. Confirm no private/generated files are staged.
8. Update docs and reset memo with validation and residual risks.

## Phase 0 - MCP Scope Lock And Baseline Evidence

### Motivation

MCP can sound like "server platform" work. The first phase prevents that scope
mistake by recording exactly what is and is not being built.

### Implementation Instructions

- Record the current repo state:

```bash
git status --short --branch
git log --oneline -8
ra release-report
ra privacy status
ra doctor --matrix
```

- Inspect the current placeholder:

```bash
sed -n '1,160p' src/research_assistant/adapters/mcp_server.py
```

- Add or update a short MCP scope document, for example:

```text
docs/architecture/local_mcp_adapter.md
```

- The scope document must state:
  - local stdio only;
  - read-only default;
  - no HTTP/server deployment for this milestone;
  - no provider calls by default;
  - no destructive tools;
  - batch arXiv intake deferred until grants exist.

- Cross-link from:
  - `docs/usage.md`;
  - `docs/product_spec.md`;
  - `docs/architecture/adr/0006-deployment-model.md`, if useful.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- A maintainer can tell that the MCP work is a local adapter, not a hosted
  service.
- The default mode and out-of-scope write/destructive operations are explicit.

## Phase 1 - Shared Tool Contract Layer

### Motivation

The MCP server should not scrape CLI text output. It should call the same
underlying Python functions as the CLI and return structured JSON-compatible
payloads. This keeps the CLI and MCP behavior consistent and testable.

### Implementation Instructions

- Add a small contract module, for example:

```text
src/research_assistant/adapters/local_tools.py
```

- Move or wrap reusable read-only operations there:
  - `find_paper`;
  - `get_paper_summary`;
  - `paper_code_links`;
  - `claim_support_audit`;
  - review list/show helpers if needed;
  - local source inspection helpers if needed;
  - `doctor`;
  - `privacy_status`;
  - `parser_tool_matrix`.

- Every operation must:
  - accept `root: Path | None`;
  - return JSON-serializable `dict` or `list`;
  - avoid printing;
  - avoid writes;
  - expose provenance/status/limitations fields where available;
  - preserve existing parser and generated-material warnings.

- Add a helper to resolve and validate the MCP workspace root:
  - default to current project root or `RA_ROOT`;
  - resolve symlinks;
  - reject paths outside the intended workspace when a root is explicitly
    configured;
  - return a structured error rather than a traceback for invalid roots.

### Tests And Verification

- Add unit or integration tests for the contract layer:
  - empty store lookup;
  - demo store lookup;
  - invalid root handling;
  - claim audit behavior;
  - status tools remain read-only.

```bash
timeout 180 python -m pytest tests/integration/test_cli_commands.py -q
timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
```

### Acceptance Criteria

- MCP can be implemented without parsing CLI stdout.
- Read-only operations have stable structured outputs.
- Existing CLI tests still pass.

## Phase 2 - Local Read-Only Stdio MCP Server

### Motivation

This is the first user-visible MCP milestone. It should be useful immediately
for assistant workflows while staying safe enough to run against a private local
workspace.

### Implementation Instructions

- Add MCP as an optional dependency rather than a base dependency:

```toml
[project.optional-dependencies]
mcp = ["mcp[cli]"]
```

- Add a script entry point, for example:

```toml
[project.scripts]
ra = "research_assistant.cli:main"
ra-mcp = "research_assistant.adapters.mcp_server:main"
```

- Replace the placeholder in
  `src/research_assistant/adapters/mcp_server.py` with a FastMCP-based local
  stdio server.

- Default transport:

```python
mcp.run(transport="stdio")
```

- The server should load configuration from:
  - `RA_ROOT`, if set;
  - an optional `--root` argument, if the SDK/entrypoint structure makes that
    clean;
  - otherwise the current checkout root.

- Expose read-only tools first:
  - `ra_workspace_status`;
  - `ra_find_paper`;
  - `ra_get_paper_summary`;
  - `ra_paper_code_links`;
  - `ra_claim_support_audit`;
  - `ra_review_list`;
  - `ra_review_show`;
  - `ra_source_show`, if there is a clean helper;
  - `ra_parser_tool_matrix`;
  - `ra_privacy_status`.

- Prefer MCP resources for stable read-only record access, if simple:
  - `research-assistant://paper/{paper_id}`;
  - `research-assistant://source/{paper_id}`;
  - `research-assistant://workspace/status`.

- Do not expose in Phase 2:
  - `ingest`;
  - `download-paper`;
  - `source-fetch`;
  - `review-mark`;
  - `audit-note append/set/remove`;
  - `backup restore`;
  - `workspace merge --apply`;
  - any arbitrary file read/write.

- Tool descriptions must say:
  - local workspace only;
  - read-only;
  - generated/parser outputs are review material;
  - no provider calls by default.

### Tests And Verification

- Add tests that import and construct the MCP server when the optional
  dependency is available.
- Add fallback tests that the base package still imports when MCP is not
  installed.
- Add contract tests that call the underlying registered functions directly.
- Keep the module importable without the MCP SDK installed. Starting `ra-mcp`
  may return a clear error when the optional extra is missing, but importing the
  package and running the base CLI must not fail.
- In automated tests, call registered FastMCP tools/resources directly instead
  of trying to manage a long-running stdio process.
- If the MCP inspector is available locally, run a manual smoke:

```bash
timeout 60 ra-mcp
```

Use the SDK inspector only as a manual check, not as a required offline test if
it requires network package fetches.

Required automated validation:

```bash
timeout 180 python -m pytest tests/integration/test_cli_commands.py -q
timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- A local MCP client can query the workspace through stdio.
- Installing without the `mcp` extra still works.
- MCP exposes no write tools.
- No HTTP server or hosted deployment is introduced.

## Phase 3 - MCP Usage Documentation And Client Configuration

### Motivation

The feature is only useful if a colleague can wire it into an assistant without
misunderstanding its safety boundary. Documentation should prevent accidental
platform claims and make root selection explicit.

### Implementation Instructions

- Add:

```text
docs/mcp.md
```

- Document:
  - installation with optional MCP extra;
  - local stdio server command;
  - `RA_ROOT` usage;
  - expected client configuration shape;
  - safe first tools to try;
  - what MCP will not do yet;
  - troubleshooting for missing optional dependency;
  - how to stop the server;
  - privacy notes.

- Add a short section to `README.md` and `docs/usage.md` linking to
  `docs/mcp.md`.

- Include examples that query demo data:

```bash
ra --root /tmp/ra-demo demo setup
RA_ROOT=/tmp/ra-demo ra-mcp
```

- Do not include private local paths or user-specific paper titles.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
git diff --check
```

### Acceptance Criteria

- A colleague can configure MCP locally without needing server deployment.
- Docs make read-only behavior and privacy limits obvious.

## Phase 4 - Permission And Audit Foundation For Future Writes

### Motivation

Before adding batch downloads, the repo needs a server-enforced permission
foundation. This keeps the later arXiv intake feature from becoming a broad
"assistant can write anywhere" capability.

### Implementation Instructions

- Add permission/grant models, for example:

```text
src/research_assistant/adapters/mcp_permissions.py
```

- Define schemas for:
  - `McpPermissionMode`;
  - `McpGrant`;
  - `ArxivBatchIntakeGrant`;
  - `McpAuditEvent`;
  - `McpWriteDecision`.

- Add local storage paths under `local_research/governance/mcp/`:
  - `grants/`;
  - `audit/`;
  - `batch_manifests/`.

- Add helpers:
  - create grant;
  - read grant;
  - validate grant expiry;
  - validate workspace root;
  - validate destination path;
  - validate allowed domains;
  - append audit event;
  - deny with structured reason.

- Add CLI-only grant creation first:

```bash
ra mcp grant arxiv-intake \
  --query "transport maps HMC" \
  --max-papers 200 \
  --expires-hours 2 \
  --destination inbox \
  --skip-duplicates
```

- Add CLI inspection:

```bash
ra mcp grants list
ra mcp grants show --grant-id <id>
ra mcp audit list
```

- Do not let MCP create its own write grants in this phase unless there is a
  separate explicit human confirmation mechanism in the client.
- Include `plan_hash` in arXiv grants and treat mismatches as blockers during
  execution.

### Tests And Verification

- Tests for:
  - grant creation;
  - expired grant rejection;
  - path escape rejection;
  - symlink escape rejection if symlink fixtures are practical;
  - unsupported domain rejection;
  - max-papers limit;
  - audit append;
  - no review mutation.

```bash
timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- There is a concrete, tested grant object.
- Write-capable MCP tools can be implemented against server-side checks rather
  than prompt-level politeness.
- Grants are local, auditable, scoped, and expiring.

## Phase 5 - ArXiv Batch Intake Planning

### Motivation

Large literature work often begins with "pull many papers for review." Asking
for permission for every individual file wastes time. A plan-first batch intake
tool lets the assistant propose a bounded action that the human can approve
once.

### Implementation Instructions

- Add an arXiv batch planning module, for example:

```text
src/research_assistant/ingest/arxiv_batch.py
```

- Add planning operation:

```python
plan_arxiv_batch_intake(
    query: str | None,
    arxiv_ids: list[str] | None,
    max_papers: int,
    destination: Literal["inbox", "source"],
    root: Path | None = None,
) -> dict
```

- The planning operation must:
  - perform no writes to paper/source/inbox records;
  - normalize and validate arXiv IDs;
  - report intended domains;
  - report intended destination;
  - detect obvious duplicates from existing summaries/source records;
  - estimate candidate count;
  - include warnings about generated/review material;
  - return a stable plan hash.

- If live arXiv search is not yet implemented, support explicit arXiv ID lists
  first and record query-based search as a follow-up.
- The first executable batch path may be explicit-ID-only. Query-based discovery
  remains a separate hypothesis to test after the grant model is proven.

- Expose read-only MCP tool:

```text
ra_plan_arxiv_batch_intake
```

- Add CLI command if useful:

```bash
ra arxiv-batch plan --ids 2401.00001,2401.00002 --destination source
```

### Tests And Verification

- Tests for:
  - explicit ID list plan;
  - duplicate detection;
  - plan hash stability;
  - max-papers enforcement;
  - no writes during planning.

```bash
timeout 180 python -m pytest tests/integration/test_cli_commands.py -q
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- The assistant can produce a concrete batch intake plan before any write or
  download happens.
- The plan is specific enough to become a grant.

## Phase 6 - Granted ArXiv Batch Intake Execution

### Motivation

This phase resolves the real workflow problem: downloading many arXiv papers or
source packages with one bounded approval while still preserving review,
privacy, and audit boundaries.

### Implementation Instructions

- Add execution operation:

```python
run_arxiv_batch_intake(
    grant_id: str,
    plan_hash: str,
    root: Path | None = None,
) -> dict
```

- Execution must:
  - load the grant;
  - verify grant has not expired;
  - verify workspace root matches;
  - verify explicit arXiv ID list or query scope matches the grant;
  - verify operation and plan hash match;
  - verify max-papers limit;
  - verify domains are allowlisted;
  - verify destination is allowed;
  - skip duplicates by default;
  - avoid overwriting existing files;
  - write only to permitted inbox/source/batch-manifest paths;
  - append an audit event for start, each item result, and completion;
  - produce a final batch manifest.

- For source packages, reuse existing source-first behavior:
  - `fetch_arxiv_structured_source`;
  - source records under `local_research/papers/source/`.

- For PDFs, either:
  - reuse existing inbox proposal/download machinery if an arXiv PDF URL path is
    already clean; or
  - defer PDF downloads and implement source-package batch first.

- Expose MCP tool:

```text
ra_run_arxiv_batch_intake
```

- The tool must require `grant_id` and `plan_hash`.

- The result payload must include:
  - status;
  - grant ID;
  - plan hash;
  - attempted count;
  - downloaded/fetched count;
  - skipped duplicates;
  - failures;
  - manifest path;
  - audit path;
  - review-status warning.

### Tests And Verification

- Use monkeypatched network functions for automated tests.
- Tests for:
  - valid grant executes;
  - expired grant blocks;
  - mismatched plan hash blocks;
  - count limit blocks or truncates according to documented behavior;
  - non-arXiv domain blocks;
  - duplicate skip;
  - manifest written;
  - audit written;
  - no review approval.

```bash
timeout 180 python -m pytest tests/integration/test_cli_commands.py -q
timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- A user can approve one bounded arXiv batch and let MCP execute it without
  repeated per-file confirmations.
- The server enforces the grant.
- All results are review material with manifest/audit evidence.

## Phase 7 - Review Write Design Gate

### Motivation

Once batch intake works, users will naturally want MCP to mark records,
append notes, or accept/reject inbox items. Those are higher-trust actions
because they change the research state. They should not be bundled into the
first MCP write milestone.

### Implementation Instructions

- Do not implement review mutation yet.
- Add a design note for future `review_write`:
  - allowed fields;
  - confirmation payload;
  - audit event;
  - old/new value capture;
  - no silent overwrite;
  - conflict detection;
  - undo or correction path.

- Add tests that confirm Phase 2/6 MCP server still does not expose review
  mutation tools.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
```

### Acceptance Criteria

- Review mutation remains deferred.
- The future design is explicit enough to implement later without weakening
  the current safety boundary.

## Phase 8 - Release Gate And Colleague MCP Trial

### Motivation

MCP should be proven by a real local assistant workflow, not only unit tests.
The colleague rollout succeeded for CLI/local usage; MCP needs its own small
fresh-user validation before being treated as part of the recommended workflow.

### Implementation Instructions

- Add MCP checks to release/reporting surfaces:
  - optional dependency status;
  - MCP adapter import status;
  - local read-only tool contract status;
  - batch grant/audit path status if implemented.
- Ensure release-report does not block the individual local release when the MCP
  extra is absent. MCP is optional and should report `not_installed` or
  `available`, not become a hard release dependency.

- Add a manual MCP trial script or checklist:
  - install with MCP extra;
  - create demo workspace;
  - configure local MCP client;
  - run `find_paper`;
  - run `get_paper_summary`;
  - inspect source/status;
  - run `claim_support_audit`;
  - if Phase 6 exists, run a monkeypatched or tiny real arXiv batch with a
    strict grant.

- Record only non-private metadata:
  - platform;
  - Python version;
  - MCP client;
  - install mode;
  - commands/tools exercised;
  - issues/confusions;
  - privacy observations.

- Update:
  - `docs/known_limitations.md`;
  - `docs/troubleshooting.md`;
  - `docs/mcp.md`;
  - release notes when appropriate.

### Tests And Verification

```bash
timeout 120 scripts/run_fast_tests.sh
timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
ra release-report
```

### Acceptance Criteria

- MCP read-only local usage is validated by at least one local assistant
  workflow.
- Batch intake remains explicitly gated if included.
- Release docs do not imply hosted/shared/server readiness.

## Suggested Milestone Boundaries

### MCP Alpha 1 - Safe Local Read-Only

Complete Phases 0-3.

Ship condition:

- local stdio MCP works;
- read-only tools only;
- optional dependency;
- docs complete;
- no write tools.

### MCP Alpha 2 - Permission Foundation

Complete Phase 4.

Ship condition:

- local grant/audit machinery exists;
- no MCP write execution yet;
- tests prove path/domain/expiry enforcement.

### MCP Alpha 3 - Bounded ArXiv Batch Intake

Complete Phases 5-6.

Ship condition:

- plan-first arXiv intake;
- grant-bound execution;
- manifest and audit records;
- no review approval;
- no destructive operations.

### MCP Beta - Trialed Workflow

Complete Phases 7-8.

Ship condition:

- colleague-like MCP trial;
- release report includes MCP readiness;
- limitations and troubleshooting updated.

## Files Expected To Change

Likely code files:

- `pyproject.toml`
- `src/research_assistant/adapters/mcp_server.py`
- `src/research_assistant/adapters/local_tools.py`
- `src/research_assistant/adapters/mcp_permissions.py`
- `src/research_assistant/ingest/arxiv_batch.py`
- `src/research_assistant/cli.py`
- `src/research_assistant/individual_release.py`

Likely tests:

- `tests/integration/test_mcp_adapter.py`
- `tests/integration/test_mcp_permissions.py`
- `tests/integration/test_arxiv_batch_intake.py`
- focused additions to existing CLI/release tests.

Likely docs:

- `docs/architecture/local_mcp_adapter.md`
- `docs/mcp.md`
- `docs/usage.md`
- `README.md`
- `docs/known_limitations.md`
- `docs/troubleshooting.md`
- release notes when appropriate.

## Files Explicitly Out Of Scope

- Hosted deployment manifests.
- Web UI.
- Database migration.
- SSO/RBAC implementation.
- Production monitoring.
- Live provider/LLM integration.
- Destructive workspace operations.
- Automatic mathematical or review approval.

## Final Definition Of Done

The MCP addition is complete when:

- `ra-mcp` runs as a local stdio server.
- MCP is optional and does not break base CLI installs.
- Read-only tools work against a configured local workspace root.
- The server exposes no direct write/destructive tools by default.
- ArXiv batch intake, if enabled, requires a bounded grant and writes audit
  records plus manifests.
- Batch intake never marks records approved.
- Path, domain, expiry, count, duplicate, and overwrite rules are enforced
  server-side.
- Docs explain setup, privacy, limitations, and troubleshooting.
- Automated tests cover the read-only adapter and grant enforcement.
- A colleague-like local MCP trial is recorded without private data.
