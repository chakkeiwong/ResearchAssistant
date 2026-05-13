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
| H1 external MCP setup | `accepted` | External-agent stdio MCP setup trial passed on 2026-05-03; first tool call completed in 0.305s; unsafe tools and MCP review-write were absent. |
| H2 live explicit-ID arXiv source scale | `accepted` | Public explicit-ID live runs completed for 25/50/100 on 2026-05-03; duplicate rerun bug found and fixed. |
| H3-live query discovery smoke | `accepted` | Approved bounded live query returned 10 candidates from one arXiv API page on 2026-05-03; pinned file drove grant-bound source intake. |
| H4 PDF execution readiness | `accepted_cli_only` | Grant-bound CLI PDF inbox download passed deterministic preconditions and a one-PDF live smoke on 2026-05-03; MCP PDF tool remains absent. |
| H5 MCP review-write readiness | `preconditions_required` | CLI prototype exists; MCP mutation disabled. |

## H1 External MCP Setup Record

Use `docs/mcp_colleague_trial_record_template.md` for a human colleague record.
If the trial is delegated to another agent or environment, send
`docs/validation/local_mcp_h1_external_agent_instructions.md` and paste back
only the sanitized result.

Current classification: `accepted`.

Detailed sanitized record:
`docs/validation/local_mcp_h1_external_trial_result_2026-05-03.md`.

Evidence summary:

- date: 2026-05-03;
- trial runner: external Codex agent in another environment;
- environment: Linux WSL2, Python 3.11.14, package
  `research-assistant==0.1.0`;
- install source: local source checkout at commit
  `0ea4a094c65b4e62da614fca768953f5db5eb6a8`;
- MCP client: Python MCP SDK stdio client, `mcp==1.26.0`;
- workspace root: `/tmp/ra-mcp-h1-trial`;
- maintainer assistance: no;
- time to first successful MCP tool call: 0.305s;
- setup completed comfortably under the 15 minute target;
- required read-only MCP tool calls passed against demo data;
- unsafe tools were absent;
- `review-write status` reported `mcp_exposed: false`;
- review mutation was not offered through MCP;
- optional live batch-grant check was skipped, which is acceptable for H1.

Tools observed:

- `ra_workspace_status`;
- `ra_find_paper`;
- `ra_get_paper_summary`;
- `ra_paper_code_links`;
- `ra_claim_support_audit`;
- `ra_review_list`;
- `ra_review_show`;
- `ra_source_show`;
- `ra_parser_tool_matrix`;
- `ra_privacy_status`;
- `ra_plan_arxiv_batch_intake`;
- `ra_run_arxiv_batch_intake`.

Interpretation:

- H1 is accepted for local stdio MCP setup against a demo workspace.
- The accepted claim is setup/read-only usability and permission-surface safety.
- H1 does not validate live arXiv execution, query discovery, PDF downloads, or
  MCP review mutation.

Privacy exclusions:

- no private titles;
- no raw PDFs or extracted text;
- no credentials or tokens;
- no private local paths beyond generic demo/temp paths;
- no colleague name unless they explicitly opt in.

Follow-up improvements:

- document that an existing Python environment is acceptable when fresh venv
  creation is unavailable;
- ask external runners to verify `ra-mcp` with `command -v ra-mcp` or
  `ra-mcp --help`;
- mention that some sandboxed stdio clients may time out even when the same
  server works outside the sandbox;
- keep generated `*.egg-info/` metadata ignored and out of commits. The
  repository no longer tracks `src/research_assistant.egg-info/`.

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

Current classification: `accepted`.

Approval:

- approving person: user;
- approval date: 2026-05-03 Asia/Hong_Kong;
- approved scope: H3 bounded live arXiv query smoke and H4 PDF execution test;
- exact query: `transport maps HMC`;
- query privacy: public/non-private;
- max candidates: 10;
- pagination cap used: 1 page;
- timeout: 30 seconds;
- candidate workspace root: `/tmp/ra-live-query-smoke-2026-05-03`;
- source-intake workspace root: `/tmp/ra-live-query-source-2026-05-03`;
- committed evidence: sanitized summaries only.

Sanitized live query result:

- endpoint: `https://export.arxiv.org/api/query`;
- candidate count: 10;
- elapsed discovery time: 1.218s;
- candidate file checksum:
  `352215ef794ba214e8c009d9a6db5c2d617f3644652cb626651039b5ecfa62a6`;
- ordered IDs:
  `2006.03435v1`, `2007.11549v3`, `0907.5491v3`, `2312.04800v1`,
  `2111.11612v1`, `2311.10663v4`, `2508.02659v1`, `2512.16839v1`,
  `2402.04976v1`, `1409.0087v1`;
- candidate-file inspect status: `ok`;
- planning status from saved candidate file: `ready_for_grant`;
- candidate-file plan hash in the first workspace:
  `90e030670fe9e801521ceff6f33adea06d06c21bb2de75b95a19b9ce030da505`;
- first source-intake grant:
  `mcp_grant_5a7c5f51c1f99b85`;
- first source-intake run remained sandboxed and produced 10 unavailable source
  records because source fetch had no network. This is recorded as a sandbox
  artifact, not H3 acceptance evidence.

Sanitized live source follow-up:

- source-intake workspace root:
  `/tmp/ra-live-query-source-2026-05-03`;
- source-intake plan hash:
  `5a2b675112fb6baa6b96b3d507e6e5377afe513e77fc7823fa2c70b38a10a286`;
- grant: `mcp_grant_1e0453af422696ed`;
- attempted: 10;
- available structured sources: 7;
- source-structure failures: 3;
- command failures: 0;
- audit events: 13;
- review policy: `review_material_only`;
- no approved review records were found in the live workspaces.

Safety and interpretation:

- H3 is accepted for bounded CLI live query discovery that writes only a pinned
  candidate file.
- The saved candidate file bound exact ordered IDs and checksum into planning.
- Source intake used the existing local grant path and the saved candidate
  file.
- The query results were noisy, but bounded, inspectable, and safely usable as
  review material.
- Live query discovery remains absent from MCP.
- No raw API responses, source archives, manifests, audit logs, extracted text,
  or private paths are committed.

Required evidence:

- exact query;
- max candidate count;
- endpoint;
- pagination cap;
- timeout;
- candidate file checksum;
- ordered arXiv IDs;
- plan hash from saved candidate file;
- proof that live query discovery remains bounded and absent from MCP.

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

Current classification: `accepted_cli_only`.

Approval:

- approving person: user;
- approval date: 2026-05-03 Asia/Hong_Kong;
- approved scope: H4 grant-bound PDF execution test;
- live workspace roots:
  `/tmp/ra-live-pdf-smoke-2026-05-03` and
  `/tmp/ra-live-pdf-smoke2-2026-05-03`;
- committed evidence: sanitized summaries only.

Implementation evidence:

- PDF execution is CLI-only through `ra arxiv-batch pdf-run`;
- execution requires a matching local grant with operation
  `pdf_inbox_download`, destination `inbox`, and matching plan hash;
- downloader writes only to `local_research/inbox`;
- allowed domains are `arxiv.org` and `export.arxiv.org`;
- redirects to unapproved domains are blocked;
- max file count, per-file bytes, total bytes, destination, overwrite, missing
  URL, invalid declared bytes, and domain policy are tested;
- checksum and byte count are recorded for successful downloads;
- duplicate/no-overwrite rerun is tested;
- partial temp cleanup after stream-limit failure is tested;
- manifest/audit records are tested;
- no MCP PDF download tool is exposed.

Live smoke result:

- candidate query: `transport maps HMC`;
- max candidates: 1;
- candidate ID: `2006.03435v1`;
- candidate file checksum:
  `b29f4eb4342e2543276d2b6c25a085d2816cd990d3cb9c24a1ee5c146e9f56ea`;
- first live smoke plan hash:
  `cd5ba14263bcfb1d807ff8ca47a97a4f99fffd5f5cd90799d2b39a44c0b2f913`;
- first live smoke grant:
  `mcp_grant_f7f0d5879d3d092f`;
- first live smoke result: blocked before download because candidate-file plan
  identity was not preserved during PDF run recomputation;
- fix: `run_pdf_batch_download(...)` now accepts `candidate_file` and binds
  candidate-file metadata during plan-hash recomputation;
- patched live smoke plan hash:
  `e311b7640a1690d0b468b851b7c46620d6f0cd94e7b4c0ae88f0fe6eca1331d9`;
- patched live smoke grant:
  `mcp_grant_13187f4136c4cd5c`;
- patched live smoke result: attempted 1, downloaded 1, failures 0;
- downloaded PDF size: 2,454,305 bytes;
- downloaded PDF SHA256:
  `c5a1d48f2ccd9016be5f7744442fe41b378eb8e20997edb574cc331cb75b6f3c`;
- duplicate rerun result: attempted 1, downloaded 0, skipped duplicate 1,
  failures 0;
- audit events after live run and duplicate rerun: 7.

Safety and interpretation:

- H4 is accepted for grant-bound CLI-only PDF inbox download at tiny live-smoke
  scale.
- H4 does not approve large PDF batch defaults for routine use; broader sizes
  need separate scale evidence.
- Downloaded PDFs remain review material and are not trusted paper records.
- MCP PDF execution remains disabled/absent.
- No raw PDFs, manifests, audit logs, or local grant files are committed.

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

- grant-bound CLI execution exists;
- one-PDF live smoke passed;
- MCP PDF execution is disabled/absent.

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
