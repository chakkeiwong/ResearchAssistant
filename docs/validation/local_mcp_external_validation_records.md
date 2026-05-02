# Local MCP External Validation Records

Use this file as the index for sanitized local MCP validation evidence. It
extends:

- `docs/plans/templates/external-validation-record-template.md`;
- `docs/mcp_colleague_trial_record_template.md`;
- `docs/plans/templates/phase-execution-template.md`.

Do not paste private papers, raw PDFs, extracted text, workspace archives,
backup archives, local grant files, audit logs, credentials, tokens, shell
history, private local paths, or colleague identity unless they explicitly opt
in.

## Current Status

| Hypothesis | Status | Evidence |
| --- | --- | --- |
| H1 real colleague MCP setup | `blocked_external` | No real colleague MCP trial recorded; user chose to record the external blocker and proceed. |
| H2 live explicit-ID arXiv source scale | `accepted` | Public explicit-ID live runs completed for 25/50/100 on 2026-05-03; duplicate rerun bug found and fixed. |
| H3-live query discovery smoke | `manual_live_approval_required` | Offline candidate-file planning exists; live query disabled. |
| H4 PDF execution readiness | `preconditions_required` | Policy checks exist; downloader disabled. |
| H5 MCP review-write readiness | `preconditions_required` | CLI prototype exists; MCP mutation disabled. |

## H1 Real Colleague MCP Setup Record

Use `docs/mcp_colleague_trial_record_template.md` for the detailed record. If
the trial is delegated to another agent or environment, send
`docs/validation/local_mcp_h1_external_agent_instructions.md` and paste back
only the sanitized result.

Current classification: `blocked_external`.

Reason: no real colleague or fresh-reader MCP client trial is available in this
autonomous run. Local surrogate evidence does not count as H1 completion.

Required evidence:

- real colleague or fresh reader;
- MCP client configuration using local stdio;
- demo workspace only or other non-private workspace;
- time-to-first-tool-call;
- required read-only tools exercised;
- unsafe tools absent;
- `ra review-write status` reports `mcp_exposed: false`;
- trial outcome: `passed`, `narrowed`, or `failed`.

Privacy exclusions:

- no private titles;
- no raw PDFs or extracted text;
- no credentials or tokens;
- no private local paths beyond generic demo/temp paths;
- no colleague name unless they explicitly opt in.

Pass criteria:

- colleague configures `ra-mcp` in an MCP client in under 15 minutes;
- required read-only tools work against demo data;
- unsafe tools are absent.

Narrow criteria:

- setup succeeds only after maintainer assistance;
- docs are confusing but correctable;
- client-specific issue requires documentation.

Fail criteria:

- setup cannot complete;
- required read-only tools fail;
- unsafe tools appear.

## H2 Live Explicit-ID ArXiv Source Scale Record

Use `docs/validation/local_mcp_live_arxiv_scale_protocol.md` for commands and
limits.

Current classification: `accepted`.

Approval:

- approving person: user;
- approval date: 2026-05-03 Asia/Hong_Kong;
- approved scope: bounded live arXiv network commands for H2;
- explicit sanitized arXiv ID source: public sequential IDs
  `2401.00001` through `2401.00100`;
- workspace roots: `/tmp/ra-live-arxiv-source-25-2026-05-03`,
  `/tmp/ra-live-arxiv-source-50-2026-05-03`, and
  `/tmp/ra-live-arxiv-source-100-2026-05-03`;
- committed evidence: sanitized summaries only.

Sanitized live results:

| Count | Timeout | Attempted | Fetched | Skipped | Failed | Elapsed | Audit events | Status mix | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 25 | 900s | 25 | 17 | 0 | 0 | 153.99s | 28 | 17 available, 7 failed structure extraction, 1 unavailable source | `accepted` |
| 50 | 1800s | 50 | 40 | 0 | 0 | 167.70s | 53 | 40 available, 9 failed structure extraction, 1 unavailable source | `accepted` |
| 100 | 3600s | 100 | 87 | 0 | 0 | 591.90s | 103 | 87 available, 12 failed structure extraction, 1 unavailable source | `accepted` |

Plan/grant identifiers:

- 25 live run: plan hash
  `d7ace3c2ad50588be98aded126fc8fb71ffc6a032d16778a9e2d3ce33960c598`,
  grant `mcp_grant_9afbf05b811c039a`;
- 50 live run: plan hash
  `75b53884465a18b20889f2fb1aac8f1fa44c3d81cb73fcb4e6e8e19d5c9b3cee`,
  grant `mcp_grant_5709d0cb72cc1371`;
- 100 live run: plan hash
  `91706256a336d8f9c4ea04cf9289482df506638555cf8aa8970e9503ac64a42e`,
  grant `mcp_grant_9e7440cbe714d6af`.

Safety and interpretation:

- all three live runs completed within the bounded timeouts;
- manifests and audit logs were created in `/tmp` workspaces;
- no raw source archives, full text, manifests, audit logs, or private paths
  are committed;
- no JSON record in the live workspaces had review status `approved`;
- source-structure failures were recorded as review-material limitations, not
  command failures;
- rerunning an old live grant after source records existed exposed plan-hash
  drift caused by mutable duplicate diagnostics;
- the plan-hash drift was fixed so duplicate diagnostics remain visible but do
  not change the grant-bound plan identity;
- a patched-checkout duplicate rerun created fresh grant
  `mcp_grant_6341ba16caf9d735` against the populated 25-paper workspace and
  completed with 25 skipped duplicates, 0 fetched, and 0 failures in 0.09s.

Required evidence:

- explicit sanitized arXiv ID list;
- approved live run size: 25, 50, then 100 only if prior run is comfortable;
- `/tmp` or ignored workspace root;
- plan hash;
- grant ID;
- attempted count;
- fetched count;
- skipped duplicate count;
- failed count;
- elapsed time;
- manifest path summary, not manifest contents;
- audit event count summary, not audit log contents.

Privacy exclusions:

- no private local workspace;
- no source archives committed;
- no raw full text copied into docs;
- no local grant/audit/manifest files committed.

Pass criteria:

- run completes within the bounded timeout;
- failures are low and explainable;
- manifest and audit records are useful;
- no paper is marked approved.

Narrow criteria:

- partial failures or throttling occur but are well reported;
- lower batch size is comfortable but larger size should remain experimental.

Fail criteria:

- unbounded runtime;
- unclear failure reporting;
- overwrite or approval behavior appears;
- generated artifacts escape the ignored workspace.

## H3-Live Query Discovery Smoke Record

Use `docs/validation/local_mcp_live_query_discovery_protocol.md`.

Required evidence:

- exact query;
- max candidate count;
- endpoint;
- pagination cap;
- timeout;
- candidate file checksum;
- ordered arXiv IDs;
- plan hash from saved candidate file;
- proof that live query discovery remains disabled until approval is recorded.

Privacy exclusions:

- no private query if it reveals sensitive research direction;
- no full abstracts unless sanitized;
- no credentials or tokens;
- no raw API response committed unless explicitly sanitized and small.

Pass criteria:

- candidate file is bounded and inspectable;
- exact ordered IDs bind into plan hash;
- source intake can run from the pinned candidate file after an explicit grant.

Narrow criteria:

- query returns noisy candidates but the bounded candidate-file flow works;
- pagination/rate-limit behavior needs tighter limits.

Fail criteria:

- uncontrolled fanout;
- candidate drift not bound to plan hash;
- live query path writes without explicit approval.

## H4 PDF Execution Precondition Record

Use `docs/validation/local_mcp_write_surface_preconditions.md`.

Required evidence before enabling any downloader:

- policy checks pass;
- checksum capture implemented;
- temporary-file cleanup tested;
- duplicate/no-overwrite behavior tested;
- manifest/audit records tested;
- tiny live smoke approved and recorded;
- docs/release-report updated;
- no automatic approval.

Current status:

- policy checks exist;
- execution is disabled.

## H5 MCP Review-Write Precondition Record

Use `docs/validation/local_mcp_write_surface_preconditions.md`.

Required evidence before MCP exposure:

- CLI UX review;
- undo or correction policy;
- audit review;
- exact MCP confirmation payload;
- stale file conflict behavior;
- no bulk approval;
- explicit tool exposure checklist.

Current status:

- CLI prototype exists;
- expired proposal cleanup exists and is dry-run by default;
- MCP mutation is disabled.
