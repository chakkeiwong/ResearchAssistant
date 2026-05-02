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
| H2 live explicit-ID arXiv source scale | `manual_live_approval_required` | Mocked 25-paper mechanics passed; live 25/50/100 not recorded. |
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
