# H1 External Agent Instructions - Local MCP Setup Trial

## Purpose

Use this document to run the H1 external validation trial in another
environment.

H1 asks whether a real colleague, fresh reader, or independent agent can
configure `research-assistant` as a local stdio MCP server against demo data,
make the first successful MCP tool call in under 15 minutes, exercise the
required safe inspection tools, and confirm that unsafe MCP tools are absent.

This trial must produce sanitized evidence only. Do not use or report private
papers, private PDF contents, credentials, tokens, private local paths, or
workspace archives.

## What To Return

Return a single sanitized Markdown result using the template in
[Result Template](#result-template). The repository maintainer needs enough
evidence to classify H1 as one of:

- `passed`;
- `narrowed`;
- `failed`;
- `blocked`.

Do not return raw PDFs, raw extracted text, private paper titles, full local
audit logs, credentials, shell history, or private absolute paths. Demo paths
under `/tmp/ra-mcp-h1-trial` are okay.

## Privacy And Scope Rules

- Use only a fresh demo workspace such as `/tmp/ra-mcp-h1-trial`.
- Do not point `ra-mcp` at a private or existing research workspace.
- Do not paste private local paths except the generic demo path.
- Do not run live arXiv network fetches for the required H1 trial.
- Do not run query-based discovery, PDF batch download, backup restore, review
  mutation, delete, or arbitrary file read/write actions through MCP.
- If your MCP client exposes filesystem, shell, browser, or unrelated tools
  from other servers, ignore them and record only the tools offered by the
  `research-assistant` MCP server.

## Prerequisites

- Python 3.10 or newer.
- A source checkout, wheel, or other installable copy of `research-assistant`.
- An MCP-capable client that can start a local stdio server.
- Permission to install the optional MCP dependency in the trial environment.

Record the exact install source in the result:

- source checkout commit hash;
- wheel/package version;
- or other package source.

## Setup Commands

Run these from the `research-assistant` source checkout, unless you were given
a wheel/package instead.

```bash
python -m pip install ".[mcp]"
ra --root /tmp/ra-mcp-h1-trial demo setup
ra --root /tmp/ra-mcp-h1-trial review-write status
ra --root /tmp/ra-mcp-h1-trial mcp status
ra-mcp --help
```

Expected setup facts:

- `demo setup` reports `status: ready`.
- The demo paper id is `demo_transport_paper`.
- `review-write status` reports `mcp_exposed: false`.
- `mcp status` reports `default_mode: read_only`,
  `destructive_tools_enabled: false`, and `review_write_enabled: false`.
- `ra-mcp --help` succeeds.

## MCP Client Configuration

Configure a local stdio MCP server named `research-assistant`:

```json
{
  "mcpServers": {
    "research-assistant": {
      "command": "ra-mcp",
      "args": ["--root", "/tmp/ra-mcp-h1-trial"]
    }
  }
}
```

If `ra-mcp` is not on `PATH`, use the full executable path from the Python
environment where `research-assistant[mcp]` was installed.

Start timing when you begin MCP client configuration. Stop timing at the first
successful `research-assistant` MCP tool call. Record this as
`time_to_first_tool_call`.

## Required MCP Tool Calls

Exercise these tools through the MCP client, not by calling Python internals.
Record pass, fail, or skipped for each one.

| Tool | Arguments | Expected Result Summary |
| --- | --- | --- |
| `ra_workspace_status` | `{}` | Reports local stdio mode, non-hosted service, no destructive tools. |
| `ra_find_paper` | `{"query": "transport"}` | Finds `demo_transport_paper`. |
| `ra_get_paper_summary` | `{"paper_id": "demo_transport_paper"}` | Returns demo summary as read-only review material. |
| `ra_source_show` | `{"paper_id": "demo_transport_paper"}` | Returns fixture structured source record. |
| `ra_review_list` | `{"status": "needs_review"}` | Lists the demo review item without mutation. |
| `ra_claim_support_audit` | `{"claim": "demo transport map preserves a Gaussian target", "paper_ids": ["demo_transport_paper"]}` | Returns a summary-level read-only claim audit. |
| `ra_privacy_status` | `{}` | Reports provider-disabled/offline privacy posture and local MCP mode. |

If your MCP client cannot pass JSON arguments exactly as shown, adapt to the
client's UI but keep the same semantic arguments.

## Tool Inventory Check

Record the `research-assistant` MCP tool names visible in the client.

The following tools are expected safe inspection tools:

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
- `ra_plan_arxiv_batch_intake`.

The following grant-bound tool may be present:

- `ra_run_arxiv_batch_intake`.

If present, it must be clearly limited to explicit-ID arXiv source intake and
must require a local grant id plus matching plan hash. Do not run a live arXiv
fetch for the required H1 trial.

These unsafe tools must be absent from the `research-assistant` MCP server:

- review mutation tools, for example `ra_review_mark`,
  `ra_review_write_apply`, or `ra_audit_note_set`;
- query-based live arXiv discovery tools;
- PDF batch download tools;
- backup restore tools;
- delete/destructive file tools;
- arbitrary file read/write tools;
- shell command execution tools exposed by the `research-assistant` server;
- credential, token, or provider-key management tools.

## Optional Batch-Grant Boundary Check

This section is optional for H1. Skip it if network access is unavailable, if
the environment does not allow live arXiv requests, or if it would slow down
the setup usability trial.

Core H1 does not require downloading from arXiv. If you do run this optional
check, use only sanitized explicit ID `2401.00001` and record whether the run
was live or skipped.

Plan and create a local grant:

```bash
ra --root /tmp/ra-mcp-h1-trial arxiv-batch plan --ids 2401.00001 --max-papers 1
ra --root /tmp/ra-mcp-h1-trial mcp grant arxiv-intake --plan-hash <plan_hash> --max-papers 1 --ids 2401.00001 --skip-duplicates
```

Only if live network execution is explicitly allowed in your environment, run:

```bash
ra --root /tmp/ra-mcp-h1-trial arxiv-batch run --grant-id <grant_id> --plan-hash <plan_hash> --ids 2401.00001
ra --root /tmp/ra-mcp-h1-trial mcp audit list --grant-id <grant_id>
```

Expected boundary facts:

- execution requires the grant id and matching plan hash;
- output remains review material;
- no paper is marked approved;
- skipped live execution is not an H1 failure.

## Classification Criteria

Classify the trial as `passed` only if:

- setup and first successful MCP tool call completed in under 15 minutes;
- required MCP tool calls worked against demo data;
- unsafe `research-assistant` MCP tools were absent;
- `review-write status` reported `mcp_exposed: false`;
- no private data was used or returned.

Classify the trial as `narrowed` if:

- setup worked only after maintainer help;
- documentation was confusing but the client eventually worked;
- one required tool had a client-specific issue but the server posture remained
  safe;
- a small docs or client-configuration fix is needed before broad use.

Classify the trial as `failed` if:

- install or MCP client setup could not complete despite reasonable effort;
- first successful tool call took 15 minutes or longer;
- required safe tools failed in a way that is not client-specific;
- any unsafe `research-assistant` MCP tool appeared;
- review-write appeared exposed through MCP.

Classify the trial as `blocked` if:

- no MCP-capable client was available;
- no installable package/source checkout was available;
- the environment forbade installing the MCP dependency;
- policy prevented local stdio MCP execution.

## Result Template

Return exactly this shape, filled with sanitized values:

```markdown
# H1 External MCP Trial Result

## Classification

- Outcome: passed | narrowed | failed | blocked
- Reason:
- Date:
- Trial runner: anonymous label or opted-in name
- Maintainer assistance used: yes | no

## Environment

- Operating system:
- Python version:
- Install source:
- Source commit or package version:
- MCP client:
- MCP client version:
- Workspace root: /tmp/ra-mcp-h1-trial or equivalent demo temp path

## Timing

- Install time:
- Demo setup time:
- MCP client configuration time:
- Time to first successful MCP tool call:

## Setup Command Results

- `python -m pip install ".[mcp]"`:
- `ra --root /tmp/ra-mcp-h1-trial demo setup`:
- `ra --root /tmp/ra-mcp-h1-trial review-write status`:
- `ra --root /tmp/ra-mcp-h1-trial mcp status`:
- `ra-mcp --help`:

## MCP Tool Inventory

- Research-assistant tools listed by client:
- `ra_run_arxiv_batch_intake` present: yes | no
- If present, shown as grant-bound explicit-ID source intake: yes | no | not applicable
- Unsafe research-assistant tools absent: yes | no
- Unsafe tool details, if any:

## Required Tool Calls

| Tool | Status | Sanitized evidence summary |
| --- | --- | --- |
| `ra_workspace_status` | passed | |
| `ra_find_paper` | passed | |
| `ra_get_paper_summary` | passed | |
| `ra_source_show` | passed | |
| `ra_review_list` | passed | |
| `ra_claim_support_audit` | passed | |
| `ra_privacy_status` | passed | |

## Review-Write Boundary

- `mcp_exposed`: false | true | unavailable
- Review mutation offered by MCP client: yes | no
- Notes:

## Optional Batch-Grant Boundary Check

- Run mode: skipped | planned-only | live
- Explicit arXiv IDs used: 2401.00001 or none
- Grant creation result:
- Live run result:
- Manifest/audit summary:
- Any paper marked approved: yes | no | not checked

## Problems And Suggestions

- Confusing setup steps:
- Missing docs:
- Client-specific issues:
- Error messages to improve:
- Suggested docs/code changes:

## Privacy Confirmation

- Demo or non-private workspace only: yes | no
- No private titles included: yes | no
- No raw PDFs or extracted text included: yes | no
- No credentials/tokens included: yes | no
- No private local paths included: yes | no

## Final Notes

- Anything the maintainer should know before updating
  `docs/validation/local_mcp_external_validation_records.md`:
```

## Maintainer Use Of The Result

After receiving the sanitized result, the maintainer should update
`docs/validation/local_mcp_external_validation_records.md` and, if useful,
complete `docs/mcp_colleague_trial_record_template.md`.

Do not mark H1 as accepted, rejected, or narrowed without a real returned result
from this external trial.
